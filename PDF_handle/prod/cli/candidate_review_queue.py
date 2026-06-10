from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.discovery_artifacts import (
    ENCYCLOPEDIA_DECISIONS,
    PROMOTABLE_DECISIONS,
    contains_hebrew,
    discovery_row_sort_key,
    iter_staged_discovery_files,
    normalize_reason_codes,
    normalize_text,
    stable_candidate_id,
    summarize_discovery_rows,
    validate_discovery_rows,
)
from PDF_handle.prod.core.io import ensure_dir, read_json, utc_timestamp, write_json, write_text
from PDF_handle.prod.core.text import canonical_normalize


REVIEW_ACTIONS = ("approve", "reject", "route_later_degree", "merge_existing", "defer", "encyclopedia")
LEVEL3_CATEGORIES = (
    "degree_structure",
    "hiram_and_raising",
    "mortality_and_memorial",
    "symbolic_field",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic human-review queue from staged discovery rows. "
            "This is report-only: it does not modify canonical site data or staged artifacts."
        )
    )
    parser.add_argument("--staged-runs-root", type=Path, default=None)
    parser.add_argument("--discovery-root", type=Path, default=None, help="Alias for --staged-runs-root.")
    parser.add_argument("--site-root", type=Path, default=None, help="Accepted for command compatibility; not read in V1.")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--report-root",
        type=Path,
        default=PDF_HANDLE_ROOT / "runs" / "candidate_review_queue",
    )
    parser.add_argument("--work-id", action="append", default=[], help="Optional work_id filter.")
    parser.add_argument(
        "--decision",
        action="append",
        default=[],
        help="Optional decision filter. Defaults to new_canonical_topic and later_degree_candidate.",
    )
    parser.add_argument(
        "--review-file",
        type=Path,
        default=None,
        help="Optional filled reviewer decisions file. Approved rows are compiled into approved_degree_publish_input.json.",
    )
    parser.add_argument("--include-rejects", action="store_true", help="Include reject_or_noise rows in the queue.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when quality blockers are found.")
    return parser


def count_by(items: list[dict[str, Any]], field_name: str) -> dict[str, int]:
    return dict(sorted(Counter(normalize_text(item.get(field_name)) or "missing" for item in items).items()))


def load_validation_status(staging_dir: Path) -> dict[str, Any]:
    validation_path = staging_dir / "validation_report.json"
    if not validation_path.exists():
        return {"present": False, "ok": None}
    payload = read_json(validation_path)
    return {
        "present": True,
        "ok": bool(payload.get("ok")) if isinstance(payload, dict) else False,
        "path": str(validation_path.resolve()),
    }


def truncate_text(value: Any, *, max_chars: int = 1200) -> str:
    text = " ".join(normalize_text(value).split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."


def build_source_context_index(staging_dir: Path) -> dict[str, dict[str, Any]]:
    manifest_path = staging_dir / "work_manifest.generated.json"
    library_path = staging_dir / "library.candidate.json"
    if not manifest_path.exists() or not library_path.exists():
        return {}

    manifest = read_json(manifest_path)
    library = read_json(library_path)
    entries = library.get("entries") if isinstance(library, dict) else []
    entries_by_slug = {
        normalize_text(entry.get("slug")): entry
        for entry in entries
        if isinstance(entry, dict) and normalize_text(entry.get("slug"))
    }

    index: dict[str, dict[str, Any]] = {}
    works = manifest.get("works") if isinstance(manifest, dict) else []
    for work in works if isinstance(works, list) else []:
        sections = work.get("sections") if isinstance(work, dict) else []
        for section in sections if isinstance(sections, list) else []:
            if not isinstance(section, dict):
                continue
            section_id = normalize_text(section.get("section_id"))
            chapter_slug = normalize_text(section.get("chapter_slug"))
            library_entry = entries_by_slug.get(chapter_slug, {})
            full_summary = library_entry.get("full_summary") if isinstance(library_entry, dict) else ""
            index[section_id] = {
                "chapter_slug": chapter_slug or None,
                "source_order": section.get("source_order"),
                "source_anchor": section.get("source_anchor"),
                "text_char_length": section.get("text_char_length"),
                "source_excerpt": truncate_text(full_summary, max_chars=1200),
                "source_notes": library_entry.get("source_notes", []) if isinstance(library_entry, dict) else [],
            }
    return index


def build_queue_entry(
    row: dict[str, Any],
    *,
    staging_name: str,
    discovery_path: Path,
    source_context_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_context = source_context_index.get(normalize_text(row.get("section_id")), {})
    language_warnings = []
    if contains_hebrew(row.get("new_topic_hints")):
        language_warnings.append("NEW_TOPIC_HINTS_CONTAIN_HEBREW")
    return {
        "candidate_id": stable_candidate_id(row, staging_name=staging_name),
        "review_status": "pending",
        "allowed_review_actions": list(REVIEW_ACTIONS),
        "decision": normalize_text(row.get("decision")),
        "candidate_degree": normalize_text(row.get("candidate_degree")) or "unknown",
        "degree_confidence": normalize_text(row.get("degree_confidence")) or "unknown",
        "confidence": normalize_text(row.get("confidence")) or "unknown",
        "unit_kind": normalize_text(row.get("unit_kind")) or "unknown",
        "work_id": normalize_text(row.get("work_id")),
        "work_title": normalize_text(row.get("work_title")),
        "section_id": normalize_text(row.get("section_id")),
        "source_title": normalize_text(row.get("source_title")),
        # canonical_normalize: strips diacritics, normalises dashes/quotes, trims whitespace.
        # original_title preserves the raw source text for audit purposes.
        "original_title": normalize_text(row.get("normalized_title") or row.get("source_title")),
        "normalized_title": canonical_normalize(normalize_text(row.get("normalized_title") or row.get("source_title"))),
        "reason_codes": normalize_reason_codes(row.get("reason_codes")),
        "strong_match_count": int(row.get("strong_match_count") or 0),
        "medium_match_count": int(row.get("medium_match_count") or 0),
        "rejected_match_count": int(row.get("rejected_match_count") or 0),
        "new_topic_hints": [
            normalize_text(item)
            for item in row.get("new_topic_hints", [])
            if normalize_text(item)
        ]
        if isinstance(row.get("new_topic_hints"), list)
        else [],
        "language_warnings": language_warnings,
        "top_strong_matches": row.get("top_strong_matches", []) if isinstance(row.get("top_strong_matches"), list) else [],
        "top_medium_matches": row.get("top_medium_matches", []) if isinstance(row.get("top_medium_matches"), list) else [],
        "encyclopedia_lane": normalize_text(row.get("encyclopedia_lane")),
        "source_context": source_context,
        "source_artifact": str(discovery_path.resolve()),
    }


def build_review_decision_template(queue_entries: list[dict[str, Any]]) -> dict[str, Any]:
    def _default_action(entry: dict[str, Any]) -> str:
        # encyclopedia_candidate entries are pre-routed; default to "encyclopedia"
        # so reviewers only need to override if they disagree.
        return "encyclopedia" if entry.get("decision") == "encyclopedia_candidate" else "defer"

    return {
        "version": 1,
        "instructions": (
            "Fill review_action with one of approve, reject, route_later_degree, merge_existing, defer, or encyclopedia. "
            "Only rows with review_action=approve are compiled into approved_degree_publish_input.json. "
            "For approved_degree=level3, approved_category is required and must be one of "
            "degree_structure, hiram_and_raising, mortality_and_memorial, or symbolic_field. "
            "Rows with review_action=encyclopedia are compiled into encyclopedia_proposals.json. "
            "Semantic review mapping: approve = canonical_new_topic, merge_existing = merge_existing, "
            "reject plus a review_reason noting alias_only or relation_only keeps the candidate non-publish, "
            "defer = defer, and route_later_degree remains a separate cross-degree routing action."
        ),
        "allowed_level3_categories": list(LEVEL3_CATEGORIES),
        "reviewer": "",
        "reviewed_at": None,
        "decisions": [
            {
                "candidate_id": entry["candidate_id"],
                "work_id": entry["work_id"],
                "section_id": entry["section_id"],
                "normalized_title": entry["normalized_title"],
                "candidate_degree": entry["candidate_degree"],
                "encyclopedia_lane": entry.get("encyclopedia_lane") or "",
                "review_action": _default_action(entry),
                "approved_degree": entry["candidate_degree"],
                "approved_category": "",
                "approved_title": entry["normalized_title"],
                "merge_existing_slug": "",
                "review_reason": "",
            }
            for entry in queue_entries
        ],
    }


def load_review_decisions(review_file: Path | None) -> dict[str, dict[str, Any]]:
    if review_file is None:
        return {}
    payload = read_json(review_file.resolve())
    decisions = payload.get("decisions") if isinstance(payload, dict) else []
    by_id: dict[str, dict[str, Any]] = {}
    for decision in decisions if isinstance(decisions, list) else []:
        if not isinstance(decision, dict):
            continue
        candidate_id = normalize_text(decision.get("candidate_id"))
        if candidate_id:
            by_id[candidate_id] = decision
    return by_id


def build_approved_publish_input(
    queue_entries: list[dict[str, Any]],
    *,
    review_file: Path | None,
) -> dict[str, Any]:
    decisions_by_id = load_review_decisions(review_file)
    candidate_ids = {entry["candidate_id"] for entry in queue_entries}
    unknown_decision_ids = sorted(set(decisions_by_id) - candidate_ids)
    approved_candidates: list[dict[str, Any]] = []

    for entry in queue_entries:
        review_decision = decisions_by_id.get(entry["candidate_id"], {})
        if normalize_text(review_decision.get("review_action")) != "approve":
            continue
        approved_degree = normalize_text(review_decision.get("approved_degree")) or entry["candidate_degree"]
        approved_category = normalize_text(review_decision.get("approved_category"))
        source_context = entry.get("source_context", {})
        approved_candidates.append(
            {
                "candidate_id": entry["candidate_id"],
                "work_id": entry["work_id"],
                "section_id": entry["section_id"],
                "source_chapter_slug": source_context.get("chapter_slug"),
                "approved_degree": approved_degree,
                "approved_category": approved_category,
                "approved_title": normalize_text(review_decision.get("approved_title")) or entry["normalized_title"],
                "review_reason": normalize_text(review_decision.get("review_reason")),
                "source_excerpt": source_context.get("source_excerpt", ""),
                "source_notes": source_context.get("source_notes", []),
                "decision_evidence": {
                    "original_decision": entry["decision"],
                    "candidate_degree": entry["candidate_degree"],
                    "confidence": entry["confidence"],
                    "degree_confidence": entry["degree_confidence"],
                    "reason_codes": entry["reason_codes"],
                    "language_warnings": entry["language_warnings"],
                },
            }
        )

    return {
        "version": 1,
        "status": "ready" if approved_candidates else "empty_no_approved_candidates",
        "review_file": str(review_file.resolve()) if review_file else None,
        "approved_count": len(approved_candidates),
        "unknown_decision_ids": unknown_decision_ids,
        "approved_candidates": approved_candidates,
    }


def build_queue(args: argparse.Namespace) -> dict[str, Any]:
    staged_runs_root = args.staged_runs_root or args.discovery_root
    if staged_runs_root is None:
        raise SystemExit("--staged-runs-root or --discovery-root is required")
    selected_work_ids = {normalize_text(item) for item in args.work_id if normalize_text(item)}
    selected_decisions = {normalize_text(item) for item in args.decision if normalize_text(item)}
    if not selected_decisions:
        selected_decisions = set(PROMOTABLE_DECISIONS) | set(ENCYCLOPEDIA_DECISIONS)
    if args.include_rejects:
        selected_decisions.add("reject_or_noise")

    work_summaries: dict[str, Any] = {}
    queue_entries: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for discovery_path in iter_staged_discovery_files(staged_runs_root, selected_work_ids or None):
        staging_dir = discovery_path.parent
        staging_name = staging_dir.name
        source_context_index = build_source_context_index(staging_dir)
        rows = read_json(discovery_path)
        rows = [item for item in rows if isinstance(item, dict)] if isinstance(rows, list) else []
        row_blockers, row_warnings = validate_discovery_rows(rows)
        for item in row_blockers:
            item["staging_dir"] = str(staging_dir.resolve())
        for item in row_warnings:
            item["staging_dir"] = str(staging_dir.resolve())
        blockers.extend(row_blockers)
        warnings.extend(row_warnings)

        selected_rows = [row for row in rows if normalize_text(row.get("decision")) in selected_decisions]
        selected_rows.sort(key=lambda row: discovery_row_sort_key(row, staging_name=staging_name))
        queue_entries.extend(
            build_queue_entry(
                row,
                staging_name=staging_name,
                discovery_path=discovery_path,
                source_context_index=source_context_index,
            )
            for row in selected_rows
        )

        summary = summarize_discovery_rows(rows)
        summary["selected_queue_count"] = len(selected_rows)
        summary["validation"] = load_validation_status(staging_dir)
        summary["discovery_path"] = str(discovery_path.resolve())
        work_summaries[staging_name] = summary

    queue_entries.sort(
        key=lambda item: (
            item["candidate_degree"],
            item["decision"],
            item["work_id"],
            item["section_id"],
            item["normalized_title"],
        )
    )

    status = "pass"
    if blockers:
        status = "fail"
    elif warnings:
        status = "pass_with_warnings"

    return {
        "created_at": utc_timestamp(),
        "staged_runs_root": str(staged_runs_root.resolve()),
        "site_root": str(args.site_root.resolve()) if args.site_root else None,
        "selected_decisions": sorted(selected_decisions),
        "selected_work_ids": sorted(selected_work_ids),
        "status": status,
        "summary": {
            "queue_entry_count": len(queue_entries),
            "by_decision": count_by(queue_entries, "decision"),
            "by_candidate_degree": count_by(queue_entries, "candidate_degree"),
            "by_work_id": count_by(queue_entries, "work_id"),
            "quality_blocker_count": len(blockers),
            "quality_warning_count": len(warnings),
        },
        "work_summaries": work_summaries,
        "quality_blockers": blockers,
        "quality_warnings": warnings,
        "review_queue": queue_entries,
        "review_decision_template": build_review_decision_template(queue_entries),
        "approved_publish_input": build_approved_publish_input(queue_entries, review_file=args.review_file),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    summary = report["summary"]
    lines.append("# Candidate Review Queue")
    lines.append("")
    lines.append(f"- Status: `{report['status']}`")
    lines.append(f"- Queue entries: `{summary['queue_entry_count']}`")
    lines.append(f"- Quality blockers: `{summary['quality_blocker_count']}`")
    lines.append(f"- Quality warnings: `{summary['quality_warning_count']}`")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    for label, counts in (
        ("Decision", summary["by_decision"]),
        ("Candidate degree", summary["by_candidate_degree"]),
        ("Work", summary["by_work_id"]),
    ):
        lines.append(f"### {label}")
        lines.append("")
        for key, count in counts.items():
            lines.append(f"- `{key}`: {count}")
        lines.append("")

    current_group: tuple[str, str] | None = None
    for entry in report["review_queue"]:
        group = (entry["candidate_degree"], entry["decision"])
        if group != current_group:
            current_group = group
            lines.append(f"## {entry['candidate_degree']} / {entry['decision']}")
            lines.append("")
        title = entry["normalized_title"] or entry["source_title"] or entry["section_id"]
        reason_codes = ", ".join(f"`{code}`" for code in entry["reason_codes"]) or "`none`"
        hints = "; ".join(entry["new_topic_hints"]) if entry["new_topic_hints"] else ""
        lines.append(f"### {title}")
        lines.append("")
        lines.append(f"- Candidate ID: `{entry['candidate_id']}`")
        lines.append(f"- Work: `{entry['work_id']}`")
        lines.append(f"- Section: `{entry['section_id']}`")
        lines.append(f"- Confidence: `{entry['confidence']}` / degree `{entry['degree_confidence']}`")
        lines.append(f"- Unit kind: `{entry['unit_kind']}`")
        lines.append(f"- Reason codes: {reason_codes}")
        if entry["language_warnings"]:
            lines.append(f"- Language warnings: {', '.join(f'`{item}`' for item in entry['language_warnings'])}")
        source_context = entry.get("source_context", {})
        if source_context.get("source_excerpt"):
            lines.append(f"- Source excerpt: {source_context['source_excerpt']}")
        if hints:
            lines.append(f"- New-topic hints: {hints}")
        lines.append("- Review status: `pending`")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = build_parser().parse_args()
    output_dir = ensure_dir(
        args.output_dir.resolve()
        if args.output_dir
        else args.report_root.resolve() / utc_timestamp().replace(":", "-")
    )
    report = build_queue(args)
    write_json(output_dir / "candidate_review_queue.json", report)
    write_json(output_dir / "candidate_review_decisions_template.json", report["review_decision_template"])
    write_json(output_dir / "approved_degree_publish_input.json", report["approved_publish_input"])
    write_text(output_dir / "candidate_review_queue.md", render_markdown(report))
    print(
        "[done] candidate review queue "
        f"status={report['status']} entries={report['summary']['queue_entry_count']} "
        f"report={output_dir / 'candidate_review_queue.json'}",
        flush=True,
    )
    if args.strict and report["status"] == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
