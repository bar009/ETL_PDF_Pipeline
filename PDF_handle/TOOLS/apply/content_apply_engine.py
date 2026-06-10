from __future__ import annotations

import sys
from pathlib import Path

# Classification: ops-lane
# This is a downstream apply/preservation lane, not canonical prod ETL
# ownership.

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import argparse
import hashlib
import json
import os
import shutil
from collections import Counter, defaultdict
from html import escape
from pathlib import Path
from typing import Any
from uuid import uuid4

from audit_degree_classification import get_nested_value, load_subset_manifest, split_paragraphs
from common import DEFAULT_TOOLS_REPORTS_ROOT, log, resolve_report_dir
from pipeline_utils import (
    build_site_data_paths,
    ensure_dir,
    normalize_newlines,
    read_json,
    utc_timestamp,
    write_json,
    write_text,
)
from stage5_utils import normalize_text


TOOL_NAME = "content_apply_engine"
F3_REQUIRED_FILES = (
    "content_routing_summary.json",
    "content_routing_entries.json",
    "content_routing_findings.json",
    "future_entry_candidates.json",
    "library_preservation_queue.json",
)
ACTION_TYPES = {
    "remove_from_source",
    "preserve_to_library",
    "preserve_to_future_seed",
    "prepare_transfer_candidate",
    "no_op",
}
ACTION_STATUSES = {"planned", "applied", "skipped", "blocked", "failed"}
SOURCE_PATCH_STATUSES = {"not_needed", "planned", "applied", "blocked"}
PLAN_MODE = "plan"
APPLY_SAFE_MODE = "apply-safe"
REMOVE_ACTION_TYPES = {"remove_from_source"}
PRESERVE_ACTION_TYPES = {"preserve_to_library", "preserve_to_future_seed"}


class ContentApplyFailure(RuntimeError):
    pass


def find_repository_root(current_file: Path) -> Path:
    resolved = current_file.resolve()
    start_dir = resolved.parent if resolved.is_file() else resolved
    for candidate in [start_dir, *start_dir.parents]:
        if (candidate / "PDF_handle").is_dir():
            return candidate
    raise ContentApplyFailure(f"Could not determine repository root from {resolved}")


REPOSITORY_ROOT = find_repository_root(Path(__file__))
LIVE_PRESERVATION_ROOT = (REPOSITORY_ROOT / "PDF_handle" / "preservation").resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply/preservation engine layered on top of an existing F3 content-routing report."
    )
    parser.add_argument("--f3-report-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=[PLAN_MODE, APPLY_SAFE_MODE], default=PLAN_MODE)
    parser.add_argument("--site-root", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--preservation-root", default=None)
    parser.add_argument("--slug", action="append", default=[])
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser


def compact_text(value: Any) -> str:
    return " ".join(normalize_text(value).split())


def truncate_compact_text(value: Any, *, limit: int = 200) -> str:
    text = compact_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def normalize_hash_text(value: Any) -> str:
    return normalize_newlines(str(value or ""))


def sha256_text(value: Any) -> str:
    return hashlib.sha256(normalize_hash_text(value).encode("utf-8")).hexdigest()


def canonical_json_bytes(data: Any) -> bytes:
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_canonical_json(data: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(data)).hexdigest()


def sanitize_filename(value: str) -> str:
    cleaned = []
    for char in value:
        if char.isalnum() or char in {"-", "_", "."}:
            cleaned.append(char)
        else:
            cleaned.append("_")
    result = "".join(cleaned).strip("._")
    return result or "item"


def build_action_id(review_unit_id: str, action_type: str) -> str:
    return f"{review_unit_id}::{action_type}"


def build_run_id(run_started_at: str) -> str:
    timestamp_slug = run_started_at.replace(":", "-").replace("+00:00", "Z")
    return f"{timestamp_slug}-{uuid4().hex[:8]}"


def clean_slug_filters(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        slug = normalize_text(value)
        if slug and slug not in cleaned:
            cleaned.append(slug)
    return cleaned


def resolve_cli_preservation_root(raw_value: str | None) -> Path | None:
    if raw_value is None:
        return None
    if not str(raw_value).strip():
        return None
    candidate = Path(raw_value)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    return candidate.resolve()


def is_filesystem_root(path: Path) -> bool:
    return path == Path(path.anchor)


def path_depth_below_anchor(path: Path) -> int:
    anchor = Path(path.anchor)
    return len(path.relative_to(anchor).parts)


def path_is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False


def paths_overlap(path_a: Path, path_b: Path) -> bool:
    return path_is_relative_to(path_a, path_b) or path_is_relative_to(path_b, path_a)


def nearest_existing_parent(path: Path) -> Path:
    current = path
    while not current.exists():
        parent = current.parent
        if parent == current:
            return current
        current = parent
    return current


def validate_override_root(*, override_root: Path, site_root: Path, report_dir: Path) -> None:
    resolved_override = override_root.resolve()
    if is_filesystem_root(resolved_override):
        raise ContentApplyFailure(f"Override preservation root cannot be a filesystem root: {resolved_override}")
    if path_depth_below_anchor(resolved_override) < 2:
        raise ContentApplyFailure(
            f"Override preservation root is too shallow and must be at least two levels below the filesystem root: "
            f"{resolved_override}"
        )
    if resolved_override.exists() and not resolved_override.is_dir():
        raise ContentApplyFailure(f"Override preservation root exists but is not a directory: {resolved_override}")

    forbidden_roots = [
        site_root.resolve(),
        (site_root.resolve() / "data").resolve(),
        report_dir.resolve(),
        DEFAULT_TOOLS_REPORTS_ROOT.resolve(),
        LIVE_PRESERVATION_ROOT,
        REPOSITORY_ROOT.resolve(),
    ]
    for forbidden_root in forbidden_roots:
        if paths_overlap(resolved_override, forbidden_root):
            raise ContentApplyFailure(
                f"Override preservation root overlaps a forbidden path: {resolved_override} vs {forbidden_root}"
            )

    writable_probe = resolved_override if resolved_override.exists() else nearest_existing_parent(resolved_override)
    if not writable_probe.exists():
        raise ContentApplyFailure(f"Could not find an existing parent to validate override root: {resolved_override}")
    if not os.access(writable_probe, os.W_OK):
        raise ContentApplyFailure(f"Override preservation root is not writable: {resolved_override}")


def resolve_preservation_context(
    *,
    mode: str,
    preservation_root_arg: str | None,
    report_dir: Path,
    site_root: Path,
) -> dict[str, Any]:
    live_root = LIVE_PRESERVATION_ROOT
    preview_root = (report_dir / "preview_preservation").resolve()
    requested_root = resolve_cli_preservation_root(preservation_root_arg)
    note = None

    if mode == PLAN_MODE:
        if preservation_root_arg is not None and str(preservation_root_arg).strip():
            note = "preservation-root ignored in plan mode"
        return {
            "preservation_root": preview_root,
            "live_preservation_root": live_root,
            "effective_preservation_mode": "preview_only",
            "is_live_preservation_root": False,
            "preview_preservation_only": True,
            "preservation_root_note": note,
            "preservation_write_status": "preview",
        }

    if requested_root is None:
        return {
            "preservation_root": live_root,
            "live_preservation_root": live_root,
            "effective_preservation_mode": "live_root",
            "is_live_preservation_root": True,
            "preview_preservation_only": False,
            "preservation_root_note": None,
            "preservation_write_status": "live",
        }

    validate_override_root(
        override_root=requested_root,
        site_root=site_root,
        report_dir=report_dir,
    )
    return {
        "preservation_root": requested_root,
        "live_preservation_root": live_root,
        "effective_preservation_mode": "override_root",
        "is_live_preservation_root": False,
        "preview_preservation_only": False,
        "preservation_root_note": None,
        "preservation_write_status": "override",
    }


def set_nested_value(entry: dict[str, Any], dotted_path: str, value: Any) -> None:
    keys = dotted_path.split(".")
    current = entry
    for key in keys[:-1]:
        child = current.get(key)
        if not isinstance(child, dict):
            child = {}
            current[key] = child
        current = child
    current[keys[-1]] = value


def summarize_paragraphs(paragraphs: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "paragraph_index": index,
            "text_excerpt": truncate_compact_text(paragraph),
            "paragraph_hash": sha256_text(paragraph),
        }
        for index, paragraph in enumerate(paragraphs, start=1)
    ]


def build_preview_after_paragraphs(paragraphs: list[str], removal_indices: list[int]) -> list[str]:
    removal_index_set = {index for index in removal_indices if index >= 1}
    return [paragraph for index, paragraph in enumerate(paragraphs, start=1) if index not in removal_index_set]


def load_f3_artifacts(report_dir: Path) -> dict[str, Any]:
    resolved = report_dir.resolve()
    if not resolved.exists():
        raise ContentApplyFailure(f"F3 report dir not found: {resolved}")

    for filename in F3_REQUIRED_FILES:
        candidate = resolved / filename
        if not candidate.exists():
            raise ContentApplyFailure(f"F3 report dir is missing required artifact: {candidate}")

    summary = read_json(resolved / "content_routing_summary.json")
    entry_rows = read_json(resolved / "content_routing_entries.json")
    findings = read_json(resolved / "content_routing_findings.json")
    future_entry_candidates = read_json(resolved / "future_entry_candidates.json")
    library_preservation_queue = read_json(resolved / "library_preservation_queue.json")

    if not isinstance(summary, dict):
        raise ContentApplyFailure("F3 summary must be a JSON object.")
    if not isinstance(entry_rows, list):
        raise ContentApplyFailure("F3 entries artifact must be a JSON array.")
    if not isinstance(findings, dict):
        raise ContentApplyFailure("F3 findings artifact must be a JSON object.")
    if not isinstance(future_entry_candidates, list):
        raise ContentApplyFailure("future_entry_candidates.json must be a JSON array.")
    if not isinstance(library_preservation_queue, list):
        raise ContentApplyFailure("library_preservation_queue.json must be a JSON array.")

    site_root = normalize_text(summary.get("site_root"))
    manifest_path = normalize_text(summary.get("manifest_path"))
    wave_id = normalize_text(summary.get("wave_id"))
    if not site_root or not manifest_path:
        raise ContentApplyFailure("F3 summary must include site_root and manifest_path.")

    return {
        "report_dir": resolved,
        "summary": summary,
        "entry_rows": entry_rows,
        "findings": findings,
        "future_entry_candidates": future_entry_candidates,
        "library_preservation_queue": library_preservation_queue,
        "site_root": Path(site_root).resolve(),
        "manifest_path": Path(manifest_path).resolve(),
        "wave_id": wave_id,
    }


def resolve_runtime_context(
    *,
    f3_artifacts: dict[str, Any],
    site_root_arg: Path | None,
    manifest_arg: Path | None,
) -> tuple[Path, Path]:
    summary_site_root = f3_artifacts["site_root"]
    summary_manifest = f3_artifacts["manifest_path"]

    if site_root_arg is not None and site_root_arg.resolve() != summary_site_root:
        raise ContentApplyFailure(
            f"--site-root does not match the F3 summary. expected={summary_site_root} got={site_root_arg.resolve()}"
        )
    if manifest_arg is not None and manifest_arg.resolve() != summary_manifest:
        raise ContentApplyFailure(
            f"--manifest does not match the F3 summary. expected={summary_manifest} got={manifest_arg.resolve()}"
        )
    return (
        site_root_arg.resolve() if site_root_arg is not None else summary_site_root,
        manifest_arg.resolve() if manifest_arg is not None else summary_manifest,
    )


def load_level1_context(site_root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    site_paths = build_site_data_paths(site_root)
    dataset = read_json(site_paths["level1"])
    entries = dataset.get("entries")
    if not isinstance(entries, list):
        raise ContentApplyFailure("level1 dataset entries must be a list.")

    slug_map: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        slug = normalize_text(entry.get("slug"))
        if not slug:
            continue
        slug_map[slug] = entry
    return dataset, slug_map


def validate_manifest(manifest_path: Path) -> tuple[str, str, list[str]]:
    lane, wave_id, slugs = load_subset_manifest(manifest_path.resolve())
    if lane != "level1":
        raise ContentApplyFailure(f"F4 v1 supports only level1 manifests. got={lane}")
    return lane, wave_id, slugs


def select_entry_rows(entry_rows: list[dict[str, Any]], slug_filters: list[str]) -> list[dict[str, Any]]:
    available_slugs = [
        normalize_text(entry.get("slug"))
        for entry in entry_rows
        if isinstance(entry, dict) and normalize_text(entry.get("slug"))
    ]
    if slug_filters:
        unknown_filters = [slug for slug in slug_filters if slug not in available_slugs]
        if unknown_filters:
            raise ContentApplyFailure(
                f"Requested slug filters are not present in the F3 report: {', '.join(unknown_filters)}"
            )

    selected: list[dict[str, Any]] = []
    for entry in entry_rows:
        if not isinstance(entry, dict):
            continue
        slug = normalize_text(entry.get("slug"))
        if not slug:
            continue
        if slug_filters and slug not in slug_filters:
            continue
        selected.append(entry)
    return selected


def build_source_context(source_entry: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    field_name = normalize_text(row.get("field_name"))
    paragraph_index = int(row.get("paragraph_index") or 0)
    field_value = get_nested_value(source_entry, field_name)
    if not field_name:
        return {"blocked_reason": "Missing field_name on routing row."}
    if not isinstance(field_value, str):
        return {"blocked_reason": f"Source field is missing or non-string: {field_name}"}

    paragraphs = split_paragraphs(field_value)
    if paragraph_index < 1 or paragraph_index > len(paragraphs):
        return {
            "blocked_reason": (
                f"Paragraph index {paragraph_index} is out of range for {source_entry.get('slug')}::{field_name} "
                f"(paragraph_count={len(paragraphs)})"
            )
        }

    paragraph_text = paragraphs[paragraph_index - 1]
    expected_excerpt = normalize_text(row.get("text_excerpt"))
    actual_excerpt = truncate_compact_text(paragraph_text)
    if expected_excerpt and expected_excerpt != actual_excerpt:
        return {
            "blocked_reason": (
                f"Source excerpt drift detected for {source_entry.get('slug')}::{field_name}::p{paragraph_index}. "
                "The current paragraph no longer matches the F3 review excerpt."
            )
        }

    return {
        "field_value": field_value,
        "paragraphs": paragraphs,
        "paragraph_text": paragraph_text,
        "field_hash_before": sha256_text(field_value),
        "paragraph_hash": sha256_text(paragraph_text),
        "paragraph_count_before": len(paragraphs),
        "before_paragraphs": summarize_paragraphs(paragraphs),
    }


def append_explanation(message: str, addition: str) -> str:
    message = normalize_text(message)
    addition = normalize_text(addition)
    if not message:
        return addition
    if not addition:
        return message
    return f"{message} {addition}"


def build_base_action(
    *,
    row: dict[str, Any],
    action_type: str,
    apply_mode: str,
    explanation: str,
    source_context: dict[str, Any] | None,
    manual_followup_required: bool,
) -> dict[str, Any]:
    action = {
        "action_id": build_action_id(normalize_text(row.get("review_unit_id")), action_type),
        "review_unit_id": normalize_text(row.get("review_unit_id")),
        "source_entry_slug": normalize_text(row.get("source_entry_slug") or row.get("slug")),
        "field_name": normalize_text(row.get("field_name")),
        "paragraph_index": int(row.get("paragraph_index") or 0),
        "routing_decision": normalize_text(row.get("routing_decision")),
        "target_kind": normalize_text(row.get("target_kind")) or None,
        "target_slug": normalize_text(row.get("target_slug")) or None,
        "future_entry_label": normalize_text(row.get("future_entry_label")) or None,
        "library_bucket": normalize_text(row.get("library_bucket")) or None,
        "apply_mode": apply_mode,
        "action_type": action_type,
        "action_status": "planned",
        "preservation_path": None,
        "preservation_root_used": None,
        "is_live_preservation_write": False,
        "preservation_write_status": None,
        "preservation_payload_hash": None,
        "preservation_previous_payload_hash": None,
        "preservation_changed_overwrite": False,
        "preservation_retargeted": False,
        "previous_preservation_destination": None,
        "source_patch_status": "planned" if action_type in REMOVE_ACTION_TYPES else "not_needed",
        "rewrite_required": bool(row.get("rewrite_needed")),
        "manual_followup_required": manual_followup_required,
        "explanation": explanation,
        "source_field_hash_before": None,
        "source_paragraph_hash": None,
        "source_paragraph_count_before": None,
        "source_field_hash_after": None,
    }
    if source_context is not None and "blocked_reason" not in source_context:
        action["source_field_hash_before"] = source_context["field_hash_before"]
        action["source_paragraph_hash"] = source_context["paragraph_hash"]
        action["source_paragraph_count_before"] = source_context["paragraph_count_before"]
    return action


def mark_action_blocked(action: dict[str, Any], reason: str) -> None:
    action["action_status"] = "blocked"
    if action["action_type"] in REMOVE_ACTION_TYPES:
        action["source_patch_status"] = "blocked"
    action["manual_followup_required"] = True
    action["explanation"] = append_explanation(action.get("explanation", ""), reason)


def expand_row_actions(
    *,
    row: dict[str, Any],
    apply_mode: str,
    source_context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    routing_decision = normalize_text(row.get("routing_decision"))
    actions: list[dict[str, Any]] = []
    explanation = normalize_text(row.get("explanation"))

    if routing_decision == "move_to_library":
        actions.append(
            build_base_action(
                row=row,
                action_type="preserve_to_library",
                apply_mode=apply_mode,
                explanation=explanation,
                source_context=source_context,
                manual_followup_required=bool(row.get("rewrite_needed")),
            )
        )
        actions.append(
            build_base_action(
                row=row,
                action_type="remove_from_source",
                apply_mode=apply_mode,
                explanation=append_explanation(explanation, "Planned source cleanup after preservation."),
                source_context=source_context,
                manual_followup_required=False,
            )
        )
    elif routing_decision == "create_future_entry_candidate":
        actions.append(
            build_base_action(
                row=row,
                action_type="preserve_to_future_seed",
                apply_mode=apply_mode,
                explanation=explanation,
                source_context=source_context,
                manual_followup_required=True,
            )
        )
        actions.append(
            build_base_action(
                row=row,
                action_type="remove_from_source",
                apply_mode=apply_mode,
                explanation=append_explanation(explanation, "Planned source cleanup after future-seed preservation."),
                source_context=source_context,
                manual_followup_required=False,
            )
        )
    elif routing_decision == "move_to_existing_entry":
        actions.append(
            build_base_action(
                row=row,
                action_type="prepare_transfer_candidate",
                apply_mode=apply_mode,
                explanation=append_explanation(explanation, "Manual transfer candidate only in v1."),
                source_context=source_context,
                manual_followup_required=True,
            )
        )
    elif routing_decision == "keep_here_framed":
        actions.append(
            build_base_action(
                row=row,
                action_type="no_op",
                apply_mode=apply_mode,
                explanation=append_explanation(explanation, "No automatic rewrite or removal in v1."),
                source_context=source_context,
                manual_followup_required=True,
            )
        )
    elif routing_decision == "drop":
        actions.append(
            build_base_action(
                row=row,
                action_type="remove_from_source",
                apply_mode=apply_mode,
                explanation=append_explanation(explanation, "Drop action remains traced and non-regex."),
                source_context=source_context,
                manual_followup_required=False,
            )
        )
    else:
        raise ContentApplyFailure(f"Unsupported routing decision in F3 row: {routing_decision}")

    if source_context is not None and source_context.get("blocked_reason"):
        for action in actions:
            if action["action_type"] != "no_op":
                mark_action_blocked(action, source_context["blocked_reason"])

    for action in actions:
        if action["action_type"] == "remove_from_source" and routing_decision == "drop":
            is_safe_drop = (
                normalize_text(row.get("preservation_value")) == "low"
                and normalize_text(row.get("target_kind")) == "discard"
                and not normalize_text(row.get("target_slug"))
                and not normalize_text(row.get("future_entry_label"))
                and not normalize_text(row.get("library_bucket"))
            )
            if not is_safe_drop:
                mark_action_blocked(
                    action,
                    "Drop routing is not auto-removable in v1 unless preservation_value=low and no destination exists.",
                )
    return actions


def build_preservation_record(
    *,
    row: dict[str, Any],
    source_context: dict[str, Any],
    preserved_at: str,
    source_run_id: str,
    source_report_dir: Path,
) -> dict[str, Any]:
    entry_slug = normalize_text(row.get("source_entry_slug") or row.get("slug"))
    record = {
        "review_unit_id": normalize_text(row.get("review_unit_id")),
        "entry_slug": entry_slug,
        "source_entry_slug": entry_slug,
        "field_name": normalize_text(row.get("field_name")),
        "paragraph_index": int(row.get("paragraph_index") or 0),
        "content": source_context["paragraph_text"],
        "original_text": source_context["paragraph_text"],
        "text_excerpt": truncate_compact_text(source_context["paragraph_text"]),
        "detected_system_family": normalize_text(row.get("current_system_family")) or None,
        "routing_decision": normalize_text(row.get("routing_decision")),
        "preservation_value": normalize_text(row.get("preservation_value")) or None,
        "future_entry_label": normalize_text(row.get("future_entry_label")) or None,
        "library_bucket": normalize_text(row.get("library_bucket")) or None,
        "f2_provenance": {
            "f2_final_verdict": row.get("f2_final_verdict"),
            "f2_recommended_preservation_action": row.get("f2_recommended_preservation_action"),
            "f2_recommended_destination": row.get("f2_recommended_destination"),
            "f2_manual_review_reason": row.get("f2_manual_review_reason"),
            "f2_decision_source": row.get("f2_decision_source"),
            "f2_provider_status": row.get("f2_provider_status"),
        },
        "f3_provenance": {
            "routing_decision": row.get("routing_decision"),
            "routing_confidence": row.get("routing_confidence"),
            "target_kind": row.get("target_kind"),
            "target_slug": row.get("target_slug"),
            "future_entry_label": row.get("future_entry_label"),
            "library_bucket": row.get("library_bucket"),
            "taxonomy_match_reason": row.get("taxonomy_match_reason"),
            "routing_unit_status": row.get("routing_unit_status"),
            "explanation": row.get("explanation"),
        },
        "hash_bundle": {
            "source_field_hash_before": source_context["field_hash_before"],
            "source_paragraph_hash": source_context["paragraph_hash"],
            "source_paragraph_count_before": source_context["paragraph_count_before"],
        },
        "preserved_at": preserved_at,
        "source_run_id": source_run_id,
        "source_report_dir": str(source_report_dir.resolve()),
    }
    record["preservation_payload_hash"] = extract_preservation_payload_hash(record)
    return record


def build_preservation_hash_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_unit_id": normalize_text(record.get("review_unit_id")),
        "entry_slug": normalize_text(record.get("entry_slug") or record.get("source_entry_slug")),
        "field_name": normalize_text(record.get("field_name")),
        "paragraph_index": int(record.get("paragraph_index") or 0),
        "routing_decision": normalize_text(record.get("routing_decision")),
        "library_bucket": normalize_text(record.get("library_bucket")) or None,
        "future_entry_label": normalize_text(record.get("future_entry_label")) or None,
        "content": record.get("content") if isinstance(record.get("content"), str) else str(record.get("content") or ""),
        "text_excerpt": normalize_text(record.get("text_excerpt")),
        "detected_system_family": normalize_text(record.get("detected_system_family")) or None,
        "preservation_value": normalize_text(record.get("preservation_value")) or None,
    }


def extract_preservation_payload_hash(record: dict[str, Any]) -> str:
    existing_hash = normalize_text(record.get("preservation_payload_hash"))
    if existing_hash:
        return existing_hash
    return sha256_canonical_json(build_preservation_hash_payload(record))


def find_existing_preservation_records(*, preservation_root: Path, filename: str) -> list[Path]:
    candidates: list[Path] = []
    for category in ("library", "future_entries"):
        category_root = preservation_root / category
        if not category_root.exists():
            continue
        candidates.extend(path.resolve() for path in sorted(category_root.glob(f"*/{filename}")) if path.is_file())
    return candidates


def describe_preservation_destination(*, preservation_root: Path, path: Path) -> dict[str, Any] | None:
    try:
        relative_parts = path.resolve().relative_to(preservation_root.resolve()).parts
    except ValueError:
        return None
    if len(relative_parts) < 3:
        return None
    category, destination_name = relative_parts[0], relative_parts[1]
    return {
        "path": str(path.resolve()),
        "category": category,
        "library_bucket": destination_name if category == "library" else None,
        "future_entry_label": destination_name if category == "future_entries" else None,
    }


def write_preservation_record(
    *,
    preservation_root: Path,
    category_name: str,
    destination_name: str,
    review_unit_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    filename = sanitize_filename(review_unit_id) + ".json"
    target_dir = ensure_dir(preservation_root / category_name / destination_name)
    target_path = target_dir / filename
    existing_paths = find_existing_preservation_records(preservation_root=preservation_root, filename=filename)
    previous_payload_hash = None
    changed_overwrite = False
    previous_destination = None

    if target_path.exists():
        existing_payload = read_json(target_path)
        if isinstance(existing_payload, dict):
            previous_payload_hash = extract_preservation_payload_hash(existing_payload)
        else:
            previous_payload_hash = sha256_text(target_path.read_text(encoding="utf-8"))
        changed_overwrite = previous_payload_hash != payload["preservation_payload_hash"]

    retarget_candidates = [path for path in existing_paths if path.resolve() != target_path.resolve()]
    if retarget_candidates:
        previous_destination = describe_preservation_destination(
            preservation_root=preservation_root,
            path=retarget_candidates[0],
        )

    write_json(target_path, payload)
    return {
        "path": target_path.resolve(),
        "previous_payload_hash": previous_payload_hash,
        "changed_overwrite": changed_overwrite,
        "previous_destination": previous_destination,
    }


def write_transfer_candidate_record(
    *,
    root: Path,
    review_unit_id: str,
    payload: dict[str, Any],
) -> Path:
    filename = sanitize_filename(review_unit_id) + ".json"
    target_dir = ensure_dir(root)
    target_path = target_dir / filename
    write_json(target_path, payload)
    return target_path


def apply_preservation_write_result(
    *,
    action: dict[str, Any],
    preservation_context: dict[str, Any],
    write_result: dict[str, Any],
    payload_hash: str,
) -> None:
    action["preservation_path"] = str(write_result["path"])
    action["preservation_root_used"] = str(preservation_context["preservation_root"])
    action["is_live_preservation_write"] = bool(preservation_context["is_live_preservation_root"])
    action["preservation_write_status"] = preservation_context["preservation_write_status"]
    action["preservation_payload_hash"] = payload_hash
    action["preservation_previous_payload_hash"] = write_result.get("previous_payload_hash")
    action["preservation_changed_overwrite"] = bool(write_result.get("changed_overwrite"))
    action["previous_preservation_destination"] = write_result.get("previous_destination")
    action["preservation_retargeted"] = bool(write_result.get("previous_destination"))

    if action["preservation_changed_overwrite"]:
        action["explanation"] = append_explanation(
            action["explanation"],
            "Existing preserved unit changed on rerun and was overwritten deterministically.",
        )
    if action["preservation_retargeted"]:
        previous_destination = action["previous_preservation_destination"] or {}
        previous_label = (
            previous_destination.get("library_bucket")
            or previous_destination.get("future_entry_label")
            or previous_destination.get("category")
            or "unknown"
        )
        current_label = action.get("library_bucket") or action.get("future_entry_label") or "unknown"
        action["explanation"] = append_explanation(
            action["explanation"],
            f"Preservation destination retargeted from `{previous_label}` to `{current_label}`.",
        )


def backup_source_files(
    *,
    report_dir: Path,
    site_paths: dict[str, Path],
    action_rows: list[dict[str, Any]],
    created_at: str,
    manifest_path: Path,
    mode: str,
) -> dict[str, Any]:
    backup_dir = ensure_dir(report_dir / "pre_apply_backups")
    level1_path = site_paths["level1"].resolve()
    removal_action_ids = [
        action["action_id"]
        for action in action_rows
        if action["action_type"] in REMOVE_ACTION_TYPES and action["action_status"] != "blocked"
    ]
    backups: list[dict[str, Any]] = []
    if removal_action_ids:
        backup_path = backup_dir / level1_path.name
        shutil.copy2(level1_path, backup_path)
        backups.append(
            {
                "source_file": str(level1_path),
                "backup_file": str(backup_path.resolve()),
                "source_file_hash_before_apply": sha256_text(level1_path.read_text(encoding="utf-8")),
                "backed_up_at": created_at,
                "action_ids": removal_action_ids,
            }
        )

    manifest = {
        "created_at": created_at,
        "site_root": str(site_paths["site_root"]),
        "manifest_path": str(manifest_path),
        "mode": mode,
        "backups": backups,
    }
    write_json(backup_dir / "backup_manifest.json", manifest)
    return manifest


def build_group_key(action: dict[str, Any]) -> tuple[str, str]:
    return normalize_text(action.get("source_entry_slug")), normalize_text(action.get("field_name"))


def validate_group_ready(
    *,
    entry: dict[str, Any],
    field_name: str,
    expected_field_hash: str,
    expected_paragraph_count: int,
) -> str | None:
    field_value = get_nested_value(entry, field_name)
    if not isinstance(field_value, str):
        return f"Source field is missing or non-string at apply time: {field_name}"
    paragraphs = split_paragraphs(field_value)
    if sha256_text(field_value) != expected_field_hash:
        return "Source field hash drifted after planning."
    if len(paragraphs) != expected_paragraph_count:
        return "Source paragraph count drifted after planning."
    return None


def execute_apply_safe(
    *,
    dataset: dict[str, Any],
    slug_map: dict[str, dict[str, Any]],
    site_paths: dict[str, Path],
    action_rows: list[dict[str, Any]],
    action_meta: dict[str, dict[str, Any]],
    report_dir: Path,
    manifest_path: Path,
    run_id: str,
    run_started_at: str,
    preservation_context: dict[str, Any],
    quiet: bool,
) -> dict[str, Any]:
    backup_manifest = backup_source_files(
        report_dir=report_dir,
        site_paths=site_paths,
        action_rows=action_rows,
        created_at=run_started_at,
        manifest_path=manifest_path,
        mode=APPLY_SAFE_MODE,
    )

    preservation_root = preservation_context["preservation_root"]
    transfer_root: Path | None = None

    for action in action_rows:
        meta = action_meta[action["action_id"]]
        row = meta["row"]
        source_context = meta.get("source_context")

        if action["action_status"] == "blocked":
            continue

        if action["action_type"] == "preserve_to_library":
            bucket = normalize_text(action.get("library_bucket"))
            if not bucket:
                mark_action_blocked(action, "Missing library_bucket for preserve_to_library.")
                continue
            try:
                payload = build_preservation_record(
                    row=row,
                    source_context=source_context,
                    preserved_at=run_started_at,
                    source_run_id=run_id,
                    source_report_dir=report_dir,
                )
                write_result = write_preservation_record(
                    preservation_root=preservation_root,
                    category_name="library",
                    destination_name=bucket,
                    review_unit_id=action["review_unit_id"],
                    payload=payload,
                )
                apply_preservation_write_result(
                    action=action,
                    preservation_context=preservation_context,
                    write_result=write_result,
                    payload_hash=payload["preservation_payload_hash"],
                )
                action["action_status"] = "applied"
            except Exception as exc:
                action["action_status"] = "failed"
                action["manual_followup_required"] = True
                action["explanation"] = append_explanation(action["explanation"], f"Library preservation failed: {exc}")
        elif action["action_type"] == "preserve_to_future_seed":
            label = normalize_text(action.get("future_entry_label"))
            if not label:
                mark_action_blocked(action, "Missing future_entry_label for preserve_to_future_seed.")
                continue
            try:
                payload = build_preservation_record(
                    row=row,
                    source_context=source_context,
                    preserved_at=run_started_at,
                    source_run_id=run_id,
                    source_report_dir=report_dir,
                )
                write_result = write_preservation_record(
                    preservation_root=preservation_root,
                    category_name="future_entries",
                    destination_name=label,
                    review_unit_id=action["review_unit_id"],
                    payload=payload,
                )
                apply_preservation_write_result(
                    action=action,
                    preservation_context=preservation_context,
                    write_result=write_result,
                    payload_hash=payload["preservation_payload_hash"],
                )
                action["action_status"] = "applied"
            except Exception as exc:
                action["action_status"] = "failed"
                action["manual_followup_required"] = True
                action["explanation"] = append_explanation(
                    action["explanation"], f"Future-entry preservation failed: {exc}"
                )
        elif action["action_type"] == "prepare_transfer_candidate":
            if source_context is None or source_context.get("blocked_reason"):
                mark_action_blocked(action, "Transfer candidate could not be prepared because source context is invalid.")
                continue
            payload = build_preservation_record(
                row=row,
                source_context=source_context,
                preserved_at=run_started_at,
                source_run_id=run_id,
                source_report_dir=report_dir,
            )
            payload["target_slug"] = action.get("target_slug")
            try:
                if transfer_root is None:
                    transfer_root = ensure_dir(report_dir / "transfer_candidates")
                path = write_transfer_candidate_record(
                    root=transfer_root,
                    review_unit_id=action["review_unit_id"],
                    payload=payload,
                )
                action["preservation_path"] = str(path.resolve())
                action["action_status"] = "applied"
            except Exception as exc:
                action["action_status"] = "failed"
                action["manual_followup_required"] = True
                action["explanation"] = append_explanation(
                    action["explanation"], f"Transfer candidate artifact failed: {exc}"
                )
        elif action["action_type"] == "no_op":
            action["action_status"] = "skipped"

    review_preserve_status: dict[str, str] = {}
    for action in action_rows:
        if action["action_type"] in PRESERVE_ACTION_TYPES:
            review_preserve_status[action["review_unit_id"]] = action["action_status"]

    grouped_removals: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for action in action_rows:
        if action["action_type"] != "remove_from_source":
            continue
        if action["action_status"] == "blocked":
            continue

        routing_decision = action["routing_decision"]
        if routing_decision in {"move_to_library", "create_future_entry_candidate"}:
            preserve_status = review_preserve_status.get(action["review_unit_id"])
            if preserve_status != "applied":
                mark_action_blocked(action, "Source removal was blocked because preservation did not complete.")
                continue
        grouped_removals[build_group_key(action)].append(action)

    for (source_slug, field_name), group_actions in grouped_removals.items():
        source_entry = slug_map.get(source_slug)
        if source_entry is None:
            for action in group_actions:
                mark_action_blocked(action, f"Source entry is missing at apply time: {source_slug}")
            continue

        meta = action_meta[group_actions[0]["action_id"]]
        source_context = meta.get("source_context")
        validation_error = validate_group_ready(
            entry=source_entry,
            field_name=field_name,
            expected_field_hash=source_context["field_hash_before"],
            expected_paragraph_count=source_context["paragraph_count_before"],
        )
        if validation_error:
            for action in group_actions:
                mark_action_blocked(action, validation_error)
            continue

        for action in sorted(group_actions, key=lambda item: int(item["paragraph_index"]), reverse=True):
            current_field = get_nested_value(source_entry, field_name)
            current_paragraphs = split_paragraphs(current_field) if isinstance(current_field, str) else []
            paragraph_index = int(action["paragraph_index"])
            meta = action_meta[action["action_id"]]
            expected_paragraph_hash = meta["source_context"]["paragraph_hash"]
            if paragraph_index < 1 or paragraph_index > len(current_paragraphs):
                mark_action_blocked(action, "Paragraph index drifted before removal.")
                continue
            if sha256_text(current_paragraphs[paragraph_index - 1]) != expected_paragraph_hash:
                mark_action_blocked(action, "Paragraph hash drifted before removal.")
                continue

            del current_paragraphs[paragraph_index - 1]
            new_field_value = "\n\n".join(current_paragraphs)
            set_nested_value(source_entry, field_name, new_field_value)
            action["action_status"] = "applied"
            action["source_patch_status"] = "applied"
            action["source_field_hash_after"] = sha256_text(new_field_value)

    log("[apply] writing updated level1.json", quiet=quiet)
    write_json(site_paths["level1"], dataset)
    return backup_manifest


def execute_plan_preview(
    *,
    action_rows: list[dict[str, Any]],
    action_meta: dict[str, dict[str, Any]],
    report_dir: Path,
    run_id: str,
    run_started_at: str,
    preservation_context: dict[str, Any],
    quiet: bool,
) -> None:
    preview_root = preservation_context["preservation_root"]
    transfer_root: Path | None = None

    for action in action_rows:
        meta = action_meta[action["action_id"]]
        row = meta["row"]
        source_context = meta.get("source_context")

        if action["action_status"] == "blocked":
            continue

        if action["action_type"] == "preserve_to_library":
            bucket = normalize_text(action.get("library_bucket"))
            if not bucket:
                mark_action_blocked(action, "Missing library_bucket for preserve_to_library.")
                continue
            payload = build_preservation_record(
                row=row,
                source_context=source_context,
                preserved_at=run_started_at,
                source_run_id=run_id,
                source_report_dir=report_dir,
            )
            write_result = write_preservation_record(
                preservation_root=preview_root,
                category_name="library",
                destination_name=bucket,
                review_unit_id=action["review_unit_id"],
                payload=payload,
            )
            apply_preservation_write_result(
                action=action,
                preservation_context=preservation_context,
                write_result=write_result,
                payload_hash=payload["preservation_payload_hash"],
            )
        elif action["action_type"] == "preserve_to_future_seed":
            label = normalize_text(action.get("future_entry_label"))
            if not label:
                mark_action_blocked(action, "Missing future_entry_label for preserve_to_future_seed.")
                continue
            payload = build_preservation_record(
                row=row,
                source_context=source_context,
                preserved_at=run_started_at,
                source_run_id=run_id,
                source_report_dir=report_dir,
            )
            write_result = write_preservation_record(
                preservation_root=preview_root,
                category_name="future_entries",
                destination_name=label,
                review_unit_id=action["review_unit_id"],
                payload=payload,
            )
            apply_preservation_write_result(
                action=action,
                preservation_context=preservation_context,
                write_result=write_result,
                payload_hash=payload["preservation_payload_hash"],
            )
        elif action["action_type"] == "prepare_transfer_candidate":
            if source_context is None or source_context.get("blocked_reason"):
                mark_action_blocked(action, "Transfer candidate could not be prepared because source context is invalid.")
                continue
            payload = build_preservation_record(
                row=row,
                source_context=source_context,
                preserved_at=run_started_at,
                source_run_id=run_id,
                source_report_dir=report_dir,
            )
            payload["target_slug"] = action.get("target_slug")
            if transfer_root is None:
                transfer_root = ensure_dir(report_dir / "transfer_candidates")
            path = write_transfer_candidate_record(
                root=transfer_root,
                review_unit_id=action["review_unit_id"],
                payload=payload,
            )
            action["preservation_path"] = str(path.resolve())
        elif action["action_type"] == "no_op":
            continue

    log("[plan] preview artifacts written", quiet=quiet)


def build_source_patch_plan(
    *,
    action_rows: list[dict[str, Any]],
    action_meta: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for action in action_rows:
        if action["action_type"] == "remove_from_source":
            grouped[build_group_key(action)].append(action)

    plans: list[dict[str, Any]] = []
    for (source_slug, field_name), group_actions in sorted(grouped.items()):
        first_meta = action_meta[group_actions[0]["action_id"]]
        source_context = first_meta.get("source_context")
        before_paragraphs = None
        after_paragraphs = None
        source_field_hash_before = None
        source_field_hash_after = None
        patch_status = "blocked" if any(action["source_patch_status"] == "blocked" for action in group_actions) else None

        if source_context is not None and "blocked_reason" not in source_context:
            before_paragraphs = source_context["before_paragraphs"]
            source_field_hash_before = source_context["field_hash_before"]
            removable_indices = [
                int(action["paragraph_index"])
                for action in group_actions
                if action["source_patch_status"] != "blocked"
            ]
            preview_paragraphs = build_preview_after_paragraphs(source_context["paragraphs"], removable_indices)
            after_paragraphs = summarize_paragraphs(preview_paragraphs)
            if any(action["source_patch_status"] == "applied" for action in group_actions):
                applied_after_hashes = [
                    action.get("source_field_hash_after")
                    for action in group_actions
                    if action.get("source_field_hash_after")
                ]
                source_field_hash_after = applied_after_hashes[-1] if applied_after_hashes else None
            if patch_status is None:
                patch_status = (
                    "applied"
                    if any(action["source_patch_status"] == "applied" for action in group_actions)
                    else "planned"
                )
        else:
            patch_status = "blocked"

        plans.append(
            {
                "source_entry_slug": source_slug,
                "field_name": field_name,
                "action_ids": [action["action_id"] for action in group_actions],
                "before_paragraphs": before_paragraphs,
                "after_paragraphs": after_paragraphs,
                "source_field_hash_before": source_field_hash_before,
                "source_field_hash_after": source_field_hash_after,
                "source_patch_status": patch_status,
            }
        )
    return plans


def build_grouped_artifact(
    *,
    action_rows: list[dict[str, Any]],
    action_type: str,
    group_field: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for action in action_rows:
        if action["action_type"] != action_type:
            continue
        key = normalize_text(action.get(group_field)) or "unassigned"
        grouped[key].append(action)

    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        items = sorted(grouped[key], key=lambda item: (item["source_entry_slug"], item["field_name"], item["paragraph_index"]))
        rows.append(
            {
                group_field: None if key == "unassigned" else key,
                "count": len(items),
                "actions": items,
            }
        )
    return rows


def build_summary(
    *,
    f3_artifacts: dict[str, Any],
    selected_entry_rows: list[dict[str, Any]],
    action_rows: list[dict[str, Any]],
    mode: str,
    strict: bool,
    run_id: str,
    run_started_at: str,
    run_completed_at: str,
    preservation_context: dict[str, Any],
) -> dict[str, Any]:
    action_type_counts = Counter(action["action_type"] for action in action_rows)
    action_status_counts = Counter(action["action_status"] for action in action_rows)
    library_bucket_counts = Counter(
        normalize_text(action.get("library_bucket"))
        for action in action_rows
        if action["action_type"] == "preserve_to_library" and normalize_text(action.get("library_bucket"))
    )
    future_entry_label_counts = Counter(
        normalize_text(action.get("future_entry_label"))
        for action in action_rows
        if action["action_type"] == "preserve_to_future_seed" and normalize_text(action.get("future_entry_label"))
    )
    source_patch_status_counts = Counter(
        action["source_patch_status"] for action in action_rows if action["action_type"] == "remove_from_source"
    )
    manual_followup_count = sum(1 for action in action_rows if action["manual_followup_required"])
    preservation_write_status_counts = Counter(
        normalize_text(action.get("preservation_write_status"))
        for action in action_rows
        if action["action_type"] in PRESERVE_ACTION_TYPES and normalize_text(action.get("preservation_write_status"))
    )
    preserved_units_total = sum(1 for action in action_rows if action["action_type"] in PRESERVE_ACTION_TYPES)
    preservation_units_written = sum(
        1
        for action in action_rows
        if action["action_type"] in PRESERVE_ACTION_TYPES and action.get("preservation_path")
    )
    preservation_changed_overwrite_count = sum(
        1 for action in action_rows if bool(action.get("preservation_changed_overwrite"))
    )
    preservation_path_retarget_count = sum(
        1 for action in action_rows if bool(action.get("preservation_retargeted"))
    )

    any_failed = bool(action_status_counts.get("failed"))
    any_blocked = bool(action_status_counts.get("blocked"))
    any_planned = bool(action_status_counts.get("planned"))
    any_skipped = bool(action_status_counts.get("skipped"))
    if strict and any_failed:
        status = "fail"
    elif any_failed or any_blocked:
        status = "pass-with-warnings"
    elif any_planned or any_skipped or manual_followup_count:
        status = "pass-with-notes"
    else:
        status = "pass"

    return {
        "created_at": run_completed_at,
        "run_id": run_id,
        "run_started_at": run_started_at,
        "run_completed_at": run_completed_at,
        "site_root": str(f3_artifacts["site_root"]),
        "site_label": f3_artifacts["site_root"].name,
        "f3_report_dir": str(f3_artifacts["report_dir"]),
        "manifest_path": str(f3_artifacts["manifest_path"]),
        "wave_id": f3_artifacts["wave_id"],
        "entry_count": len(selected_entry_rows),
        "eligible_action_count": len(action_rows),
        "apply_mode": mode,
        "action_type_counts": dict(sorted(action_type_counts.items())),
        "action_status_counts": dict(sorted(action_status_counts.items())),
        "library_bucket_counts": dict(sorted(library_bucket_counts.items())),
        "future_entry_label_counts": dict(sorted(future_entry_label_counts.items())),
        "source_patch_status_counts": dict(sorted(source_patch_status_counts.items())),
        "preservation_root": str(preservation_context["preservation_root"]),
        "live_preservation_root": str(preservation_context["live_preservation_root"]),
        "effective_preservation_mode": preservation_context["effective_preservation_mode"],
        "is_live_preservation_root": preservation_context["is_live_preservation_root"],
        "preview_preservation_only": preservation_context["preview_preservation_only"],
        "preservation_root_note": preservation_context.get("preservation_root_note"),
        "preservation_write_status_counts": dict(sorted(preservation_write_status_counts.items())),
        "preserved_units_total": preserved_units_total,
        "preservation_units_written": preservation_units_written,
        "preservation_changed_overwrite_count": preservation_changed_overwrite_count,
        "preservation_path_retarget_count": preservation_path_retarget_count,
        "manual_followup_count": manual_followup_count,
        "status": status,
    }


def build_findings(action_rows: list[dict[str, Any]]) -> dict[str, Any]:
    blocked_actions = [action for action in action_rows if action["action_status"] == "blocked"]
    failed_actions = [action for action in action_rows if action["action_status"] == "failed"]
    removed_actions = [
        action for action in action_rows if action["action_type"] == "remove_from_source" and action["action_status"] == "applied"
    ]
    library_actions = [action for action in action_rows if action["action_type"] == "preserve_to_library"]
    future_actions = [action for action in action_rows if action["action_type"] == "preserve_to_future_seed"]
    transfer_actions = [action for action in action_rows if action["action_type"] == "prepare_transfer_candidate"]
    drop_actions = [action for action in action_rows if action["routing_decision"] == "drop"]
    drift_actions = [
        action
        for action in blocked_actions
        if "drift" in normalize_text(action.get("explanation")).lower()
            or "excerpt drift" in normalize_text(action.get("explanation")).lower()
    ]
    changed_overwrite_actions = [
        action for action in action_rows if action["action_type"] in PRESERVE_ACTION_TYPES and action.get("preservation_changed_overwrite")
    ]
    retargeted_actions = [
        action for action in action_rows if action["action_type"] in PRESERVE_ACTION_TYPES and action.get("preservation_retargeted")
    ]
    return {
        "removed_actions": removed_actions,
        "library_actions": library_actions,
        "future_actions": future_actions,
        "transfer_actions": transfer_actions,
        "drop_actions": drop_actions,
        "blocked_actions": blocked_actions,
        "failed_actions": failed_actions,
        "drift_actions": drift_actions,
        "changed_overwrite_actions": changed_overwrite_actions,
        "retargeted_actions": retargeted_actions,
    }


def render_markdown_report(*, summary: dict[str, Any], findings: dict[str, Any]) -> str:
    preservation_status_parts = [
        f"{key}={value}" for key, value in sorted(summary.get("preservation_write_status_counts", {}).items())
    ]
    lines = [
        "# Content Apply Engine Report",
        "",
        f"- Status: `{summary['status']}`",
        f"- Mode: `{summary['apply_mode']}`",
        f"- Eligible actions: `{summary['eligible_action_count']}`",
        f"- Entry count: `{summary['entry_count']}`",
        f"- Manual follow-up count: `{summary['manual_followup_count']}`",
        "",
        "## Preservation Destination",
        f"- Effective mode: `{summary.get('effective_preservation_mode')}`",
        f"- Preservation root: `{summary.get('preservation_root')}`",
        f"- Live preservation root: `{summary.get('live_preservation_root')}`",
        f"- Is live preservation root: `{summary.get('is_live_preservation_root')}`",
        f"- Preview only: `{summary.get('preview_preservation_only')}`",
        f"- Preservation write statuses: `{', '.join(preservation_status_parts) or 'none'}`",
        f"- Preserved units total: `{summary.get('preserved_units_total', 0)}`",
        f"- Preservation units written: `{summary.get('preservation_units_written', 0)}`",
        f"- Changed overwrites: `{summary.get('preservation_changed_overwrite_count', 0)}`",
        f"- Retargeted units: `{summary.get('preservation_path_retarget_count', 0)}`",
        "",
    ]
    if summary.get("preservation_root_note"):
        lines.append(f"- Note: {summary['preservation_root_note']}")
        lines.append("")

    lines.extend([
        "## Source Paragraphs Removed",
    ])
    removed = findings["removed_actions"]
    if removed:
        for action in removed[:20]:
            lines.append(
                f"- `{action['review_unit_id']}` from `{action['field_name']}` "
                f"(after hash `{action.get('source_field_hash_after')}`)"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Library Preservation Applied"])
    if findings["library_actions"]:
        for action in findings["library_actions"][:20]:
            lines.append(f"- `{action['review_unit_id']}` -> `{action.get('library_bucket')}` (`{action['action_status']}`)")
    else:
        lines.append("- None")

    lines.extend(["", "## Future Entry Seeds Created"])
    if findings["future_actions"]:
        for action in findings["future_actions"][:20]:
            lines.append(
                f"- `{action['review_unit_id']}` -> `{action.get('future_entry_label')}` (`{action['action_status']}`)"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Transfer Candidates Needing Manual Follow-up"])
    if findings["transfer_actions"]:
        for action in findings["transfer_actions"][:20]:
            lines.append(
                f"- `{action['review_unit_id']}` -> `{action.get('target_slug') or 'unassigned'}` (`{action['action_status']}`)"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Drop Actions"])
    if findings["drop_actions"]:
        for action in findings["drop_actions"][:20]:
            lines.append(f"- `{action['review_unit_id']}` (`{action['action_status']}`)")
    else:
        lines.append("- None")

    lines.extend(["", "## Blocked Actions"])
    if findings["blocked_actions"]:
        for action in findings["blocked_actions"][:20]:
            lines.append(f"- `{action['review_unit_id']}`: {action['explanation']}")
    else:
        lines.append("- None")

    lines.extend(["", "## High-risk Source Drift"])
    if findings["drift_actions"]:
        for action in findings["drift_actions"][:20]:
            lines.append(f"- `{action['review_unit_id']}`: {action['explanation']}")
    else:
        lines.append("- None")

    lines.extend(["", "## Changed Preservation Overwrites"])
    if findings["changed_overwrite_actions"]:
        for action in findings["changed_overwrite_actions"][:20]:
            lines.append(
                f"- `{action['review_unit_id']}` at `{action.get('preservation_path')}` "
                f"(previous hash `{action.get('preservation_previous_payload_hash')}`, new hash `{action.get('preservation_payload_hash')}`)"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Retargeted Preservation Units"])
    if findings["retargeted_actions"]:
        for action in findings["retargeted_actions"][:20]:
            previous = action.get("previous_preservation_destination") or {}
            old_label = previous.get("library_bucket") or previous.get("future_entry_label") or "unknown"
            new_label = action.get("library_bucket") or action.get("future_entry_label") or "unknown"
            lines.append(
                f"- `{action['review_unit_id']}`: `{old_label}` -> `{new_label}`"
            )
    else:
        lines.append("- None")

    lines.append("")
    return "\n".join(lines)


def render_html_report(*, summary: dict[str, Any], findings: dict[str, Any]) -> str:
    def render_list(items: list[str]) -> str:
        if not items:
            return "<li>None</li>"
        return "".join(f"<li>{escape(item)}</li>" for item in items)

    removed_items = [
        f"{action['review_unit_id']} from {action['field_name']} (after hash {action.get('source_field_hash_after')})"
        for action in findings["removed_actions"][:20]
    ]
    library_items = [
        f"{action['review_unit_id']} -> {action.get('library_bucket')} ({action['action_status']})"
        for action in findings["library_actions"][:20]
    ]
    future_items = [
        f"{action['review_unit_id']} -> {action.get('future_entry_label')} ({action['action_status']})"
        for action in findings["future_actions"][:20]
    ]
    transfer_items = [
        f"{action['review_unit_id']} -> {action.get('target_slug') or 'unassigned'} ({action['action_status']})"
        for action in findings["transfer_actions"][:20]
    ]
    drop_items = [f"{action['review_unit_id']} ({action['action_status']})" for action in findings["drop_actions"][:20]]
    blocked_items = [f"{action['review_unit_id']}: {action['explanation']}" for action in findings["blocked_actions"][:20]]
    drift_items = [f"{action['review_unit_id']}: {action['explanation']}" for action in findings["drift_actions"][:20]]
    changed_overwrite_items = [
        (
            f"{action['review_unit_id']} at {action.get('preservation_path')} "
            f"(previous hash {action.get('preservation_previous_payload_hash')}, new hash {action.get('preservation_payload_hash')})"
        )
        for action in findings["changed_overwrite_actions"][:20]
    ]
    retarget_items = [
        (
            f"{action['review_unit_id']}: "
            f"{(action.get('previous_preservation_destination') or {}).get('library_bucket') or (action.get('previous_preservation_destination') or {}).get('future_entry_label') or 'unknown'} "
            f"-> {action.get('library_bucket') or action.get('future_entry_label') or 'unknown'}"
        )
        for action in findings["retargeted_actions"][:20]
    ]
    preservation_status_counts = ", ".join(
        f"{key}={value}" for key, value in sorted(summary.get("preservation_write_status_counts", {}).items())
    ) or "none"
    preservation_root_note = (
        f"<p>Note: {escape(summary['preservation_root_note'])}</p>" if summary.get("preservation_root_note") else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Content Apply Engine Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2933; }}
    h1, h2 {{ color: #102a43; }}
    code {{ background: #f0f4f8; padding: 2px 4px; border-radius: 4px; }}
    ul {{ line-height: 1.5; }}
  </style>
</head>
<body>
  <h1>Content Apply Engine Report</h1>
  <p>Status: <code>{escape(summary['status'])}</code></p>
  <p>Mode: <code>{escape(summary['apply_mode'])}</code></p>
  <p>Eligible actions: <code>{summary['eligible_action_count']}</code></p>
  <p>Entry count: <code>{summary['entry_count']}</code></p>
  <p>Manual follow-up count: <code>{summary['manual_followup_count']}</code></p>
  <h2>Preservation Destination</h2>
  <p>Effective mode: <code>{escape(str(summary.get('effective_preservation_mode')))}</code></p>
  <p>Preservation root: <code>{escape(str(summary.get('preservation_root')))}</code></p>
  <p>Live preservation root: <code>{escape(str(summary.get('live_preservation_root')))}</code></p>
  <p>Is live preservation root: <code>{escape(str(summary.get('is_live_preservation_root')))}</code></p>
  <p>Preview only: <code>{escape(str(summary.get('preview_preservation_only')))}</code></p>
  <p>Preservation write statuses: <code>{escape(preservation_status_counts)}</code></p>
  <p>Preserved units total: <code>{summary.get('preserved_units_total', 0)}</code></p>
  <p>Preservation units written: <code>{summary.get('preservation_units_written', 0)}</code></p>
  <p>Changed overwrites: <code>{summary.get('preservation_changed_overwrite_count', 0)}</code></p>
  <p>Retargeted units: <code>{summary.get('preservation_path_retarget_count', 0)}</code></p>
  {preservation_root_note}
  <h2>Source Paragraphs Removed</h2>
  <ul>{render_list(removed_items)}</ul>
  <h2>Library Preservation Applied</h2>
  <ul>{render_list(library_items)}</ul>
  <h2>Future Entry Seeds Created</h2>
  <ul>{render_list(future_items)}</ul>
  <h2>Transfer Candidates Needing Manual Follow-up</h2>
  <ul>{render_list(transfer_items)}</ul>
  <h2>Drop Actions</h2>
  <ul>{render_list(drop_items)}</ul>
  <h2>Blocked Actions</h2>
  <ul>{render_list(blocked_items)}</ul>
  <h2>High-risk Source Drift</h2>
  <ul>{render_list(drift_items)}</ul>
  <h2>Changed Preservation Overwrites</h2>
  <ul>{render_list(changed_overwrite_items)}</ul>
  <h2>Retargeted Preservation Units</h2>
  <ul>{render_list(retarget_items)}</ul>
</body>
</html>
"""


def build_failure_artifacts(
    *,
    report_dir: Path,
    site_root: Path,
    manifest_path: Path,
    f3_report_dir: Path,
    mode: str,
    message: str,
) -> None:
    failed_at = utc_timestamp()
    summary = {
        "created_at": failed_at,
        "run_id": None,
        "run_started_at": failed_at,
        "run_completed_at": failed_at,
        "site_root": str(site_root),
        "site_label": site_root.name,
        "f3_report_dir": str(f3_report_dir),
        "manifest_path": str(manifest_path),
        "wave_id": "",
        "entry_count": 0,
        "eligible_action_count": 0,
        "apply_mode": mode,
        "action_type_counts": {},
        "action_status_counts": {},
        "library_bucket_counts": {},
        "future_entry_label_counts": {},
        "source_patch_status_counts": {},
        "preservation_root": None,
        "live_preservation_root": str(LIVE_PRESERVATION_ROOT),
        "effective_preservation_mode": None,
        "is_live_preservation_root": False,
        "preview_preservation_only": mode == PLAN_MODE,
        "preservation_root_note": None,
        "preservation_write_status_counts": {},
        "preserved_units_total": 0,
        "preservation_units_written": 0,
        "preservation_changed_overwrite_count": 0,
        "preservation_path_retarget_count": 0,
        "manual_followup_count": 0,
        "status": "fail",
        "failure_message": message,
    }
    write_json(report_dir / "content_apply_summary.json", summary)
    write_json(report_dir / "content_apply_actions.json", [])
    write_json(report_dir / "source_patch_plan.json", [])
    write_json(report_dir / "library_preservation_applied.json", [])
    write_json(report_dir / "future_entry_seed_applied.json", [])
    write_json(report_dir / "existing_entry_transfer_candidates.json", [])
    write_json(report_dir / "apply_manifest.json", {"status": "fail", "message": message})
    write_text(report_dir / "content_apply_report.md", f"# Content Apply Engine Report\n\n- Status: `fail`\n- Error: {message}\n")
    write_text(
        report_dir / "content_apply_report.html",
        f"<html><body><h1>Content Apply Engine Report</h1><p>Status: <code>fail</code></p><p>{escape(message)}</p></body></html>",
    )


def run_engine(
    *,
    f3_artifacts: dict[str, Any],
    site_root: Path,
    manifest_path: Path,
    slug_filters: list[str],
    mode: str,
    report_dir: Path,
    preservation_root_arg: str | None,
    quiet: bool,
    strict: bool,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    _, manifest_wave_id, manifest_slugs = validate_manifest(manifest_path)
    if f3_artifacts["wave_id"] and manifest_wave_id and manifest_wave_id != f3_artifacts["wave_id"]:
        raise ContentApplyFailure(
            f"Manifest wave_id does not match the F3 summary. expected={f3_artifacts['wave_id']} got={manifest_wave_id}"
        )

    dataset, slug_map = load_level1_context(site_root)
    site_paths = build_site_data_paths(site_root)
    selected_entry_rows = select_entry_rows(f3_artifacts["entry_rows"], slug_filters)
    for entry in selected_entry_rows:
        slug = normalize_text(entry.get("slug"))
        if slug not in manifest_slugs:
            raise ContentApplyFailure(f"Entry slug from F3 is not present in the selected manifest: {slug}")

    run_started_at = utc_timestamp()
    run_id = build_run_id(run_started_at)
    action_rows: list[dict[str, Any]] = []
    action_meta: dict[str, dict[str, Any]] = {}

    for entry in selected_entry_rows:
        source_slug = normalize_text(entry.get("slug"))
        source_entry = slug_map.get(source_slug)
        if source_entry is None:
            raise ContentApplyFailure(f"Entry slug from F3 is missing in current level1.json: {source_slug}")

        log(f"[apply] entry={source_slug} mode={mode}", quiet=quiet)
        for row in entry.get("routing_reviews", []):
            if not isinstance(row, dict):
                continue
            source_context = build_source_context(source_entry, row)
            expanded_actions = expand_row_actions(row=row, apply_mode=mode, source_context=source_context)
            for action in expanded_actions:
                action_rows.append(action)
                action_meta[action["action_id"]] = {
                    "row": row,
                    "source_context": source_context if "blocked_reason" not in source_context else source_context,
                }

    preservation_context = resolve_preservation_context(
        mode=mode,
        preservation_root_arg=preservation_root_arg,
        report_dir=report_dir,
        site_root=site_root,
    )

    if mode == PLAN_MODE:
        execute_plan_preview(
            action_rows=action_rows,
            action_meta=action_meta,
            report_dir=report_dir,
            run_id=run_id,
            run_started_at=run_started_at,
            preservation_context=preservation_context,
            quiet=quiet,
        )
        backup_manifest = {
            "created_at": run_started_at,
            "site_root": str(site_root),
            "manifest_path": str(manifest_path),
            "mode": mode,
            "backups": [],
        }
    else:
        backup_manifest = execute_apply_safe(
            dataset=dataset,
            slug_map=slug_map,
            site_paths=site_paths,
            action_rows=action_rows,
            action_meta=action_meta,
            report_dir=report_dir,
            manifest_path=manifest_path,
            run_id=run_id,
            run_started_at=run_started_at,
            preservation_context=preservation_context,
            quiet=quiet,
        )

    run_completed_at = utc_timestamp()
    source_patch_plan = build_source_patch_plan(action_rows=action_rows, action_meta=action_meta)
    library_artifact = build_grouped_artifact(
        action_rows=action_rows,
        action_type="preserve_to_library",
        group_field="library_bucket",
    )
    future_artifact = build_grouped_artifact(
        action_rows=action_rows,
        action_type="preserve_to_future_seed",
        group_field="future_entry_label",
    )
    transfer_artifact = build_grouped_artifact(
        action_rows=action_rows,
        action_type="prepare_transfer_candidate",
        group_field="target_slug",
    )
    summary = build_summary(
        f3_artifacts=f3_artifacts,
        selected_entry_rows=selected_entry_rows,
        action_rows=action_rows,
        mode=mode,
        strict=strict,
        run_id=run_id,
        run_started_at=run_started_at,
        run_completed_at=run_completed_at,
        preservation_context=preservation_context,
    )
    findings = build_findings(action_rows)
    apply_manifest = {
        "created_at": run_completed_at,
        "run_id": run_id,
        "run_started_at": run_started_at,
        "run_completed_at": run_completed_at,
        "mode": mode,
        "site_root": str(site_root),
        "manifest_path": str(manifest_path),
        "wave_id": f3_artifacts["wave_id"],
        "f3_report_dir": str(f3_artifacts["report_dir"]),
        "preservation_root": str(preservation_context["preservation_root"]),
        "live_preservation_root": str(preservation_context["live_preservation_root"]),
        "effective_preservation_mode": preservation_context["effective_preservation_mode"],
        "action_ids_in_order": [action["action_id"] for action in action_rows],
        "actions": action_rows,
        "backup_manifest_path": str((report_dir / "pre_apply_backups" / "backup_manifest.json").resolve())
        if mode == APPLY_SAFE_MODE
        else None,
    }
    return (
        summary,
        action_rows,
        source_patch_plan,
        library_artifact,
        future_artifact,
        transfer_artifact,
        apply_manifest,
        backup_manifest,
        findings,
    )


def write_artifacts(
    *,
    report_dir: Path,
    summary: dict[str, Any],
    action_rows: list[dict[str, Any]],
    source_patch_plan: list[dict[str, Any]],
    library_artifact: list[dict[str, Any]],
    future_artifact: list[dict[str, Any]],
    transfer_artifact: list[dict[str, Any]],
    apply_manifest: dict[str, Any],
    backup_manifest: dict[str, Any],
    findings: dict[str, Any],
) -> None:
    write_json(report_dir / "content_apply_summary.json", summary)
    write_json(report_dir / "content_apply_actions.json", action_rows)
    write_json(report_dir / "source_patch_plan.json", source_patch_plan)
    write_json(report_dir / "library_preservation_applied.json", library_artifact)
    write_json(report_dir / "future_entry_seed_applied.json", future_artifact)
    write_json(report_dir / "existing_entry_transfer_candidates.json", transfer_artifact)
    write_json(report_dir / "apply_manifest.json", apply_manifest)
    if backup_manifest.get("mode") == APPLY_SAFE_MODE:
        write_json(report_dir / "pre_apply_backups" / "backup_manifest.json", backup_manifest)
    write_text(report_dir / "content_apply_report.md", render_markdown_report(summary=summary, findings=findings))
    write_text(report_dir / "content_apply_report.html", render_html_report(summary=summary, findings=findings))


def main() -> None:
    args = build_parser().parse_args()
    slug_filters = clean_slug_filters(args.slug)
    failure_context: dict[str, Any] | None = None

    try:
        f3_artifacts = load_f3_artifacts(args.f3_report_dir)
        site_root, manifest_path = resolve_runtime_context(
            f3_artifacts=f3_artifacts,
            site_root_arg=args.site_root,
            manifest_arg=args.manifest,
        )
        report_dir = resolve_report_dir(
            tool_name=TOOL_NAME,
            report_dir=args.report_dir.resolve() if args.report_dir else None,
            site_root=site_root,
        )
        failure_context = {
            "site_root": site_root,
            "manifest_path": manifest_path,
            "f3_report_dir": f3_artifacts["report_dir"],
            "report_dir": report_dir,
        }
        (
            summary,
            action_rows,
            source_patch_plan,
            library_artifact,
            future_artifact,
            transfer_artifact,
            apply_manifest,
            backup_manifest,
            findings,
        ) = run_engine(
            f3_artifacts=f3_artifacts,
            site_root=site_root,
            manifest_path=manifest_path,
            slug_filters=slug_filters,
            mode=args.mode,
            report_dir=report_dir,
            preservation_root_arg=args.preservation_root,
            quiet=args.quiet,
            strict=args.strict,
        )
        write_artifacts(
            report_dir=report_dir,
            summary=summary,
            action_rows=action_rows,
            source_patch_plan=source_patch_plan,
            library_artifact=library_artifact,
            future_artifact=future_artifact,
            transfer_artifact=transfer_artifact,
            apply_manifest=apply_manifest,
            backup_manifest=backup_manifest,
            findings=findings,
        )
        log(
            f"[done] status={summary['status']} mode={summary['apply_mode']} actions={summary['eligible_action_count']} report={report_dir}",
            quiet=args.quiet,
        )
        if args.strict and summary["status"] == "fail":
            raise SystemExit(1)
    except ContentApplyFailure as exc:
        if failure_context is not None:
            build_failure_artifacts(
                report_dir=failure_context["report_dir"],
                site_root=failure_context["site_root"],
                manifest_path=failure_context["manifest_path"],
                f3_report_dir=failure_context["f3_report_dir"],
                mode=args.mode,
                message=str(exc),
            )
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()

