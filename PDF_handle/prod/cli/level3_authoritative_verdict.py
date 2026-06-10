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

from PDF_handle.prod.core.io import ensure_dir, read_json, utc_timestamp, write_json, write_text


LEVEL3_PUBLISHABLE_CATEGORIES = (
    "degree_structure",
    "hiram_and_raising",
    "mortality_and_memorial",
    "symbolic_field",
)
SERIOUS_REVIEW_DECISIONS = {"new_canonical_topic", "later_degree_candidate"}
PUBLISH_PRODUCTIVE_MIN_TOPICS = 6
PUBLISH_PRODUCTIVE_MIN_CATEGORIES = 3
THIN_RESULT_MIN_TOPICS = 4
THIN_RESULT_MIN_CATEGORIES = 2
REVIEW_LOAD_TARGET = 40
REVIEW_LOAD_MAX = 50


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Write the final WP-1 level3 authoritative-run verdict from review and publish artifacts. "
            "This is report-only and does not mutate site data."
        )
    )
    parser.add_argument("--approved-input", type=Path, required=True)
    parser.add_argument("--review-queue", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    return parser


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def load_approved_candidates(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path.resolve())
    rows = payload.get("approved_candidates") if isinstance(payload, dict) else []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def load_review_queue(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    payload = read_json(path.resolve())
    rows = payload.get("review_queue") if isinstance(payload, dict) else []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def build_verdict(*, approved_candidates: list[dict[str, Any]], review_queue: list[dict[str, Any]]) -> dict[str, Any]:
    approved_level3 = [
        row for row in approved_candidates
        if normalize_text(row.get("approved_degree")) == "level3"
    ]
    category_counts = Counter(
        normalize_text(row.get("approved_category")) or "missing"
        for row in approved_level3
    )
    non_gate_category_count = len(
        [
            category for category in category_counts
            if category in LEVEL3_PUBLISHABLE_CATEGORIES
        ]
    )
    serious_review_count = len(
        [
            row for row in review_queue
            if normalize_text(row.get("candidate_degree")) == "level3"
            and normalize_text(row.get("decision")) in SERIOUS_REVIEW_DECISIONS
        ]
    )
    approved_count = len(approved_level3)
    publish_productive = (
        approved_count >= PUBLISH_PRODUCTIVE_MIN_TOPICS
        and non_gate_category_count >= PUBLISH_PRODUCTIVE_MIN_CATEGORIES
    )
    thin_result = (
        approved_count < THIN_RESULT_MIN_TOPICS
        or non_gate_category_count < THIN_RESULT_MIN_CATEGORIES
    )
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if any(category not in LEVEL3_PUBLISHABLE_CATEGORIES for category in category_counts):
        blockers.append(
            {
                "code": "APPROVED_LEVEL3_CATEGORY_OUTSIDE_LOCKED_SKELETON",
                "category_counts": dict(sorted(category_counts.items())),
            }
        )
    if serious_review_count > REVIEW_LOAD_MAX:
        blockers.append(
            {
                "code": "REVIEW_LOAD_ABOVE_HARD_MAX",
                "serious_review_count": serious_review_count,
                "hard_max": REVIEW_LOAD_MAX,
            }
        )
    elif serious_review_count > REVIEW_LOAD_TARGET:
        warnings.append(
            {
                "code": "REVIEW_LOAD_ABOVE_TARGET",
                "serious_review_count": serious_review_count,
                "target": REVIEW_LOAD_TARGET,
            }
        )

    if blockers:
        recommendation = "level3 still too unstable for level2 extension"
    elif publish_productive:
        recommendation = "level3 stable, extend same method to level2 next"
    elif thin_result:
        recommendation = "level3 still too unstable for level2 extension"
    else:
        recommendation = "level3 promising, but run one stabilization pass before level2"

    return {
        "created_at": utc_timestamp(),
        "status": "fail" if blockers else "pass_with_warnings" if warnings else "pass",
        "approved_level3_count": approved_count,
        "approved_level3_category_counts": dict(sorted(category_counts.items())),
        "approved_level3_non_gate_category_count": non_gate_category_count,
        "serious_level3_review_count": serious_review_count,
        "publish_productive": publish_productive,
        "thin_result": thin_result,
        "recommendation": recommendation,
        "blockers": blockers,
        "warnings": warnings,
        "thresholds": {
            "publish_productive_min_topics": PUBLISH_PRODUCTIVE_MIN_TOPICS,
            "publish_productive_min_categories": PUBLISH_PRODUCTIVE_MIN_CATEGORIES,
            "thin_result_min_topics": THIN_RESULT_MIN_TOPICS,
            "thin_result_min_categories": THIN_RESULT_MIN_CATEGORIES,
            "review_load_target": REVIEW_LOAD_TARGET,
            "review_load_max": REVIEW_LOAD_MAX,
        },
    }


def render_markdown(verdict: dict[str, Any]) -> str:
    lines = [
        "# Level3 Authoritative Run Verdict",
        "",
        f"- Status: `{verdict['status']}`",
        f"- Recommendation: `{verdict['recommendation']}`",
        f"- Approved level3 topics: `{verdict['approved_level3_count']}`",
        f"- Non-gate category count: `{verdict['approved_level3_non_gate_category_count']}`",
        f"- Serious level3 review count: `{verdict['serious_level3_review_count']}`",
        f"- Publish productive: `{verdict['publish_productive']}`",
        f"- Thin result: `{verdict['thin_result']}`",
        "",
        "## Approved Level3 By Category",
        "",
    ]
    for category, count in verdict["approved_level3_category_counts"].items():
        lines.append(f"- `{category}`: {count}")
    if verdict["blockers"]:
        lines.extend(["", "## Blockers", ""])
        for item in verdict["blockers"]:
            lines.append(f"- `{item.get('code')}`")
    if verdict["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for item in verdict["warnings"]:
            lines.append(f"- `{item.get('code')}`")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = build_parser().parse_args()
    output_dir = ensure_dir(args.output_dir.resolve())
    approved_candidates = load_approved_candidates(args.approved_input)
    review_queue = load_review_queue(args.review_queue)
    verdict = build_verdict(approved_candidates=approved_candidates, review_queue=review_queue)
    verdict["approved_input"] = str(args.approved_input.resolve())
    verdict["review_queue"] = str(args.review_queue.resolve()) if args.review_queue else None
    write_json(output_dir / "level3_authoritative_verdict.json", verdict)
    write_text(output_dir / "level3_authoritative_verdict.md", render_markdown(verdict))
    print(
        "[done] level3 authoritative verdict "
        f"status={verdict['status']} recommendation={verdict['recommendation']!r} "
        f"report={output_dir / 'level3_authoritative_verdict.json'}",
        flush=True,
    )
    if args.strict and verdict["status"] == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
