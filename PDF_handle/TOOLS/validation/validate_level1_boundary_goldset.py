from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import argparse
from pathlib import Path
from typing import Any

from common import CODE_ROOT, log, resolve_report_dir
from pipeline_utils import read_json, write_json, write_text


DEFAULT_GOLDSET = CODE_ROOT / "PDF_handle" / "TOOLS" / "data" / "level1_boundary_goldset.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a full Phase H run against the level1 boundary goldset.")
    parser.add_argument("--phase-h-report-dir", type=Path, required=True)
    parser.add_argument("--f2-report-dir", type=Path, default=None)
    parser.add_argument("--f3-report-dir", type=Path, default=None)
    parser.add_argument("--goldset", type=Path, default=DEFAULT_GOLDSET)
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    return parser


def flatten_f2_rows(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for row in entry.get("paragraph_reviews", []):
            if isinstance(row, dict):
                review_unit_id = str(row.get("review_unit_id") or "").strip()
                if review_unit_id:
                    rows[review_unit_id] = row
    return rows


def flatten_f3_rows(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for row in entry.get("routing_reviews", []):
            if isinstance(row, dict):
                review_unit_id = str(row.get("review_unit_id") or "").strip()
                if review_unit_id:
                    rows[review_unit_id] = row
    return rows


def actual_outcome(*, f2_row: dict[str, Any] | None, f3_row: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if isinstance(f3_row, dict):
        decision = str(f3_row.get("routing_decision") or "").strip() or None
        if decision == "move_to_library":
            return decision, str(f3_row.get("library_bucket") or "").strip() or None
        if decision == "create_future_entry_candidate":
            return decision, str(f3_row.get("future_entry_label") or "").strip() or None
        return decision, None
    if isinstance(f2_row, dict):
        verdict = str(f2_row.get("final_verdict") or "").strip() or None
        return verdict, None
    return None, None


def build_findings(
    *,
    goldset_entries: list[dict[str, Any]],
    f2_rows: dict[str, dict[str, Any]],
    f3_rows: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    outcome_match_count = 0
    bucket_match_count = 0
    exact_match_count = 0
    missing_rows = 0
    keep_degree_contamination_violations = 0

    for item in goldset_entries:
        review_unit_id = str(item.get("review_unit_id") or "").strip()
        f2_row = f2_rows.get(review_unit_id)
        f3_row = f3_rows.get(review_unit_id)
        actual_decision, actual_bucket_or_label = actual_outcome(f2_row=f2_row, f3_row=f3_row)
        target_decision = str(item.get("target_outcome") or "").strip() or None
        target_bucket_or_label = item.get("target_bucket_or_label")
        outcome_match = actual_decision == target_decision
        bucket_match = target_bucket_or_label == actual_bucket_or_label
        if outcome_match:
            outcome_match_count += 1
        if bucket_match:
            bucket_match_count += 1
        if outcome_match and bucket_match:
            exact_match_count += 1
        if f2_row is None:
            missing_rows += 1
        if (
            actual_decision == "keep"
            and isinstance(f2_row, dict)
            and set(f2_row.get("degree_reason_codes") or [])
            & {
                "degree_2_strong_anchor_detected",
                "degree_3_strong_anchor_detected",
                "higher_degree_contamination_detected",
            }
        ):
            keep_degree_contamination_violations += 1
        findings.append(
            {
                "review_unit_id": review_unit_id,
                "excerpt": item.get("excerpt"),
                "scope_class": item.get("scope_class"),
                "target_outcome": target_decision,
                "target_bucket_or_label": target_bucket_or_label,
                "actual_outcome": actual_decision,
                "actual_bucket_or_label": actual_bucket_or_label,
                "outcome_match": outcome_match,
                "bucket_match": bucket_match,
                "exact_match": outcome_match and bucket_match,
                "current_f2_outcome": {
                    "final_verdict": f2_row.get("final_verdict") if isinstance(f2_row, dict) else None,
                    "recommended_preservation_action": f2_row.get("recommended_preservation_action") if isinstance(f2_row, dict) else None,
                    "recommended_destination": f2_row.get("recommended_destination") if isinstance(f2_row, dict) else None,
                },
                "current_f3_outcome": {
                    "routing_decision": f3_row.get("routing_decision") if isinstance(f3_row, dict) else None,
                    "library_bucket": f3_row.get("library_bucket") if isinstance(f3_row, dict) else None,
                    "future_entry_label": f3_row.get("future_entry_label") if isinstance(f3_row, dict) else None,
                },
                "degree_reason_codes": list(f2_row.get("degree_reason_codes") or []) if isinstance(f2_row, dict) else [],
                "routing_conflict_detected": bool(f3_row.get("routing_conflict_detected")) if isinstance(f3_row, dict) else False,
            }
        )

    summary = {
        "entry_count": len(goldset_entries),
        "exact_match_count": exact_match_count,
        "outcome_match_count": outcome_match_count,
        "bucket_match_count": bucket_match_count,
        "mismatch_count": len(goldset_entries) - exact_match_count,
        "missing_rows": missing_rows,
        "keep_degree_contamination_violations": keep_degree_contamination_violations,
        "status": "pass"
        if exact_match_count == len(goldset_entries) and keep_degree_contamination_violations == 0
        else "fail",
    }
    return findings, summary


def render_report(*, summary: dict[str, Any], findings: list[dict[str, Any]], goldset: dict[str, Any], phase_h_report_dir: Path) -> str:
    mismatches = [item for item in findings if not item["exact_match"]]
    lines = [
        "# Level1 Boundary Goldset Validation",
        "",
        f"- Phase H report dir: `{phase_h_report_dir}`",
        f"- Goldset: `{goldset.get('source_run_id', 'unknown')}`",
        f"- Entries: `{summary['entry_count']}`",
        f"- Exact matches: `{summary['exact_match_count']}`",
        f"- Mismatches: `{summary['mismatch_count']}`",
        f"- Keep contamination violations: `{summary['keep_degree_contamination_violations']}`",
        f"- Status: `{summary['status']}`",
        "",
    ]
    if mismatches:
        lines.extend(["## Mismatches", ""])
        for item in mismatches[:20]:
            lines.append(
                f"- `{item['review_unit_id']}` target=`{item['target_outcome']}`/{item['target_bucket_or_label']}` actual=`{item['actual_outcome']}`/{item['actual_bucket_or_label']}`"
            )
    else:
        lines.extend(["## Result", "", "- All goldset rows matched the target outcome and bucket/label."])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = build_parser().parse_args()
    phase_h_report_dir = args.phase_h_report_dir.resolve()
    f2_report_dir = args.f2_report_dir.resolve() if args.f2_report_dir else phase_h_report_dir / "f2"
    f3_report_dir = args.f3_report_dir.resolve() if args.f3_report_dir else phase_h_report_dir / "f3"
    goldset_path = args.goldset.resolve()
    report_dir = resolve_report_dir(tool_name="level1_boundary_validation", report_dir=args.report_dir)

    goldset = read_json(goldset_path)
    f2_entries = read_json(f2_report_dir / "semantic_purity_entries.json")
    f3_entries = read_json(f3_report_dir / "content_routing_entries.json")
    f2_rows = flatten_f2_rows(f2_entries)
    f3_rows = flatten_f3_rows(f3_entries)
    findings, summary = build_findings(
        goldset_entries=list(goldset.get("entries") or []),
        f2_rows=f2_rows,
        f3_rows=f3_rows,
    )
    payload = {
        "phase_h_report_dir": str(phase_h_report_dir),
        "f2_report_dir": str(f2_report_dir),
        "f3_report_dir": str(f3_report_dir),
        "goldset_path": str(goldset_path),
        "goldset_source_run_id": goldset.get("source_run_id"),
        **summary,
    }

    write_json(report_dir / "level1_boundary_goldset_summary.json", payload)
    write_json(report_dir / "level1_boundary_goldset_findings.json", findings)
    write_text(
        report_dir / "level1_boundary_goldset_report.md",
        render_report(summary=payload, findings=findings, goldset=goldset, phase_h_report_dir=phase_h_report_dir),
    )
    log(
        f"[done] status={payload['status']} exact_matches={payload['exact_match_count']}/{payload['entry_count']} report={report_dir}",
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()

