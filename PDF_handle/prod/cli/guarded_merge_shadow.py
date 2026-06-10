from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PDF_handle.prod.companion_contract import companion_candidate_degree, companion_candidate_slug, materialize_companion_payload
REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import ensure_dir, read_json, utc_timestamp, write_json
from PDF_handle.prod.core.site_data import build_site_data_paths
from PDF_handle.prod.core.site_roots import get_work_site_root
from PDF_handle.prod.schema.data import infer_language_contract_fields, normalize_degree_data, normalize_nullable_string
from PDF_handle.prod.schema.language_integrity import PROTECTED_TEXT_FIELDS, text_script_flags
from PDF_handle.prod.schema.overrides import load_override_bundle, normalize_override_bundle


PROTECTED_PATCH_FIELDS = {
    "symbolic_meaning": "block",
    "candidate_lesson": "block",
    "full_summary_block": "review",
}
SECONDARY_PATCH_FIELDS = {
    "practical_elements": "review",
    "tradition_notes": "review",
    "caution_notes": "review",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a shadow/block-only guarded-merge simulation against staged Step 5 artifacts "
            "and the current override layer. The simulation writes reports only and never mutates site data."
        )
    )
    parser.add_argument("--site-root", type=Path, default=get_work_site_root())
    parser.add_argument(
        "--staging-dir",
        type=Path,
        action="append",
        default=[],
        help="Repeat for each staged Step 5 directory to simulate.",
    )
    parser.add_argument(
        "--report-root",
        type=Path,
        default=PDF_HANDLE_ROOT / "runs" / "guarded_merge_shadow",
    )
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any block decisions are produced.")
    return parser


def load_datasets(site_root: Path) -> dict[str, dict[str, Any]]:
    site_paths = build_site_data_paths(site_root.resolve())
    datasets = {
        "library": normalize_degree_data(read_json(site_paths["library"]), "library"),
        "level1": normalize_degree_data(read_json(site_paths["level1"]), "level1"),
        "level2": normalize_degree_data(read_json(site_paths["level2"]), "level2"),
    }
    if site_paths["level3"].exists():
        datasets["level3"] = normalize_degree_data(read_json(site_paths["level3"]), "level3")
    return datasets


def load_patch_operations(staging_dir: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {"level1": [], "level2": [], "level3": [], "companions": []}
    for degree in ("level1", "level2", "level3"):
        patch_path = staging_dir / f"{degree}.patch.json"
        if not patch_path.exists():
            continue
        payload = read_json(patch_path)
        if isinstance(payload, dict):
            result[degree] = payload.get("operations", [])
    companion_path = staging_dir / "companion_candidates.json"
    if companion_path.exists():
        payload = read_json(companion_path)
        if isinstance(payload, list):
            result["companions"] = payload
    return result


def classify_script_decision(
    *,
    target_metadata: dict[str, Any],
    value: Any,
    severity_hint: str,
) -> dict[str, Any] | None:
    flags = text_script_flags(value)
    if not flags["text"]:
        return None
    if target_metadata["canonical_language"] == "en" and target_metadata["display_language"] == "en" and flags["has_hebrew"]:
        return {
            "action": severity_hint,
            "preview": flags["text"][:160],
            "has_hebrew": flags["has_hebrew"],
            "has_latin": flags["has_latin"],
        }
    return None


def simulate_patch_operation(
    *,
    operation: dict[str, Any],
    target_entry: dict[str, Any],
) -> dict[str, Any]:
    target_metadata = infer_language_contract_fields(target_entry)
    decisions: list[dict[str, Any]] = []
    changes = operation.get("changes") if isinstance(operation.get("changes"), dict) else {}

    for field_name, severity in PROTECTED_PATCH_FIELDS.items():
        decision = classify_script_decision(
            target_metadata=target_metadata,
            value=changes.get(field_name),
            severity_hint=severity,
        )
        if decision:
            decisions.append(
                {
                    "field": field_name,
                    "action": decision["action"],
                    "reason": "Cross-language protected patch content targets a canonical English entry.",
                    "preview": decision["preview"],
                }
            )

    for field_name, severity in SECONDARY_PATCH_FIELDS.items():
        decision = classify_script_decision(
            target_metadata=target_metadata,
            value=changes.get(field_name),
            severity_hint=severity,
        )
        if decision:
            decisions.append(
                {
                    "field": field_name,
                    "action": decision["action"],
                    "reason": "Cross-language secondary patch content would need operator review.",
                    "preview": decision["preview"],
                }
            )

    final_action = "allow"
    if any(item["action"] == "block" for item in decisions):
        final_action = "block"
    elif any(item["action"] == "review" for item in decisions):
        final_action = "review"

    return {
        "kind": "patch_operation",
        "degree": normalize_nullable_string(operation.get("degree")) or normalize_nullable_string(target_entry.get("degree")),
        "slug": normalize_nullable_string(operation.get("slug")),
        "work_id": normalize_nullable_string(operation.get("work_id")),
        "section_id": normalize_nullable_string(operation.get("section_id")),
        "action": final_action,
        "target_language_contract": {
            "language": normalize_nullable_string(target_entry.get("language")),
            "source_language": target_metadata["source_language"],
            "canonical_language": target_metadata["canonical_language"],
            "display_language": target_metadata["display_language"],
            "translation_mode": normalize_nullable_string(target_entry.get("translation_mode")),
        },
        "reasons": decisions,
    }


def simulate_companion_candidate(candidate: dict[str, Any], *, datasets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    try:
        draft = materialize_companion_payload(
            candidate,
            categories_by_degree={degree: dataset["categories"] for degree, dataset in datasets.items() if degree != "library"},
            available_link_targets={
                degree: set(dataset.get("entryBySlug", {}).keys())
                for degree, dataset in datasets.items()
            },
        )
    except Exception:
        draft = {}
    metadata = infer_language_contract_fields(draft)
    action = "allow"
    reasons: list[dict[str, Any]] = []
    if metadata["display_language"] and metadata["canonical_language"] and metadata["display_language"] != metadata["canonical_language"]:
        action = "block"
        reasons.append(
            {
                "field": None,
                "action": "block",
                "reason": "Localized primary record creation is out of scope for guarded V1 and would be blocked.",
                "preview": None,
            }
        )
    return {
        "kind": "companion_candidate",
        "degree": companion_candidate_degree(candidate) or normalize_nullable_string(draft.get("degree")),
        "slug": companion_candidate_slug(candidate) or normalize_nullable_string(draft.get("slug")),
        "work_id": normalize_nullable_string(candidate.get("work_id")),
        "section_id": normalize_nullable_string(candidate.get("section_id")),
        "action": action,
        "target_language_contract": {
            "language": normalize_nullable_string(draft.get("language")),
            "source_language": metadata["source_language"],
            "canonical_language": metadata["canonical_language"],
            "display_language": metadata["display_language"],
            "translation_mode": normalize_nullable_string(draft.get("translation_mode")),
        },
        "reasons": reasons,
    }


def simulate_override_record(
    *,
    record: dict[str, Any],
    target_entry: dict[str, Any],
) -> dict[str, Any]:
    target_metadata = infer_language_contract_fields(target_entry)
    reasons: list[dict[str, Any]] = []
    for field_name, value in (record.get("fields") or {}).items():
        normalized_field = field_name.split(".", 1)[0]
        if normalized_field not in PROTECTED_TEXT_FIELDS and not field_name.startswith("reading_layers"):
            continue
        decision = classify_script_decision(
            target_metadata=target_metadata,
            value=value,
            severity_hint="block",
        )
        if decision:
            reasons.append(
                {
                    "field": field_name,
                    "action": "block",
                    "reason": "Override applies cross-language protected content onto a canonical English entry.",
                    "preview": decision["preview"],
                }
            )

    action = "block" if reasons else "allow"
    identity = record.get("identity") if isinstance(record.get("identity"), dict) else {}
    return {
        "kind": "override",
        "degree": normalize_nullable_string(identity.get("degree")),
        "slug": normalize_nullable_string(identity.get("slug")),
        "work_id": normalize_nullable_string(identity.get("work_id")),
        "section_id": None,
        "action": action,
        "target_language_contract": {
            "language": normalize_nullable_string(target_entry.get("language")),
            "source_language": target_metadata["source_language"],
            "canonical_language": target_metadata["canonical_language"],
            "display_language": target_metadata["display_language"],
            "translation_mode": normalize_nullable_string(target_entry.get("translation_mode")),
        },
        "identity_language": normalize_nullable_string(identity.get("language")),
        "reasons": reasons,
    }


def summarize_decisions(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    by_action: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for item in decisions:
        action = str(item.get("action") or "allow")
        kind = str(item.get("kind") or "unknown")
        by_action[action] = by_action.get(action, 0) + 1
        by_kind[kind] = by_kind.get(kind, 0) + 1
    status = "shadow-pass"
    if by_action.get("block"):
        status = "shadow-block"
    elif by_action.get("review"):
        status = "shadow-review"
    return {
        "status": status,
        "total": len(decisions),
        "by_action": by_action,
        "by_kind": by_kind,
    }


def main() -> None:
    args = build_parser().parse_args()
    site_root = args.site_root.resolve()
    site_paths = build_site_data_paths(site_root)
    report_dir = ensure_dir(
        args.report_dir.resolve()
        if args.report_dir
        else (args.report_root.resolve() / utc_timestamp().replace(":", "-"))
    )

    datasets = load_datasets(site_root)
    override_bundle = normalize_override_bundle(
        load_override_bundle(site_paths["overrides"], site_root=site_root),
        site_root=site_root,
    )

    decisions: list[dict[str, Any]] = []
    staging_summaries: list[dict[str, Any]] = []

    for raw_staging_dir in args.staging_dir:
        staging_dir = raw_staging_dir.resolve()
        payloads = load_patch_operations(staging_dir)
        staging_decisions_before = len(decisions)

        for degree in ("level1", "level2", "level3"):
            dataset = datasets.get(degree)
            if not dataset:
                continue
            for operation in payloads.get(degree, []):
                slug = normalize_nullable_string(operation.get("slug"))
                target_entry = dataset.get("entryBySlug", {}).get(slug) if slug else None
                if not isinstance(target_entry, dict):
                    decisions.append(
                        {
                            "kind": "patch_operation",
                            "degree": degree,
                            "slug": slug,
                            "work_id": normalize_nullable_string(operation.get("work_id")),
                            "section_id": normalize_nullable_string(operation.get("section_id")),
                            "action": "review",
                            "target_language_contract": None,
                            "reasons": [
                                {
                                    "field": None,
                                    "action": "review",
                                    "reason": "Target entry is missing in the current site root; guarded mode would require operator review.",
                                    "preview": None,
                                }
                            ],
                        }
                    )
                    continue
                decisions.append(simulate_patch_operation(operation=operation, target_entry=target_entry))

        for candidate in payloads.get("companions", []):
            decisions.append(simulate_companion_candidate(candidate, datasets=datasets))

        staging_slice = decisions[staging_decisions_before:]
        staging_summaries.append(
            {
                "staging_dir": str(staging_dir),
                "summary": summarize_decisions(staging_slice),
            }
        )

    override_decisions_before = len(decisions)
    for record in override_bundle.get("overrides", []):
        identity = record.get("identity") if isinstance(record.get("identity"), dict) else {}
        degree = normalize_nullable_string(identity.get("degree"))
        slug = normalize_nullable_string(identity.get("slug"))
        dataset = datasets.get(degree) if degree else None
        target_entry = dataset.get("entryBySlug", {}).get(slug) if isinstance(dataset, dict) and slug else None
        if not isinstance(target_entry, dict):
            decisions.append(
                {
                    "kind": "override",
                    "degree": degree,
                    "slug": slug,
                    "work_id": normalize_nullable_string(identity.get("work_id")),
                    "section_id": None,
                    "action": "review",
                    "target_language_contract": None,
                    "identity_language": normalize_nullable_string(identity.get("language")),
                    "reasons": [
                        {
                            "field": None,
                            "action": "review",
                            "reason": "Override target entry is missing in the current site root; guarded mode would require operator review.",
                            "preview": None,
                        }
                    ],
                }
            )
            continue
        decisions.append(simulate_override_record(record=record, target_entry=target_entry))

    overall_summary = summarize_decisions(decisions)
    override_summary = summarize_decisions(decisions[override_decisions_before:])
    report = {
        "created_at": utc_timestamp(),
        "mode": "shadow_block_only",
        "site_root": str(site_root),
        "staging_dirs": [str(path.resolve()) for path in args.staging_dir],
        "overall_summary": overall_summary,
        "staging_summaries": staging_summaries,
        "override_summary": override_summary,
        "risk_notes": [
            "This simulation only classifies allow/review/block decisions; it does not rewrite staged payloads or site data.",
            "Patch-operation blocking is currently scoped to protected fields already named in the V1 plan plus review-only summary/list fields.",
            "Missing targets are treated as review rather than block because this lane does not yet model slug-reuse or approval selectors end to end.",
        ],
    }
    examples = {
        "blocked": [item for item in decisions if item.get("action") == "block"][:25],
        "review": [item for item in decisions if item.get("action") == "review"][:25],
        "allow": [item for item in decisions if item.get("action") == "allow"][:10],
    }

    write_json(report_dir / "guarded_merge_shadow_summary.json", report)
    write_json(report_dir / "guarded_merge_shadow_decisions.json", decisions)
    write_json(report_dir / "guarded_merge_shadow_examples.json", examples)
    print(json.dumps(report["overall_summary"], ensure_ascii=False), flush=True)
    print(f"[done] guarded merge shadow report written to {report_dir}", flush=True)

    if args.strict and overall_summary["by_action"].get("block", 0):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
