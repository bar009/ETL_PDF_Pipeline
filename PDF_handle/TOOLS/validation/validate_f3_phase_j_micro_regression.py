from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parents[1]
PDF_HANDLE_ROOT = TOOLS_DIR.parent
CODE_ROOT = PDF_HANDLE_ROOT.parent
if str(PDF_HANDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(PDF_HANDLE_ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import content_routing_review as f3


DEFAULT_F2_REPORT_DIR = (
    TOOLS_DIR
    / "reports"
    / "phase_h_post_gating_live_smoke"
    / "2026-03-19T00-53-28+00-00"
    / "f2"
)

TARGET_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "cable-tow::reading_layers.advanced::p1": {
        "needs_provider_review": False,
        "routing_decision_any_of": {"keep_here_framed"},
    },
    "cable-tow::symbolic_meaning::p2": {
        "needs_provider_review": False,
        "routing_decision_any_of": {"create_future_entry_candidate", "move_to_library"},
    },
    "cable-tow::symbolic_meaning::p3": {
        "needs_provider_review": False,
        "routing_decision_any_of": {"move_to_library"},
    },
    "cable-tow::symbolic_meaning::p5": {
        "needs_provider_review": False,
        "routing_decision_any_of": {"create_future_entry_candidate", "move_to_library"},
    },
    "cable-tow::symbolic_meaning::p6": {
        "needs_provider_review": False,
        "routing_decision_any_of": {"create_future_entry_candidate", "move_to_library"},
    },
    "cable-tow::candidate_lesson::p7": {
        "needs_provider_review": False,
        "routing_decision_any_of": {"create_future_entry_candidate", "move_to_library"},
    },
    "cable-tow::candidate_lesson::p2": {
        "needs_provider_review": False,
        "routing_decision_any_of": {"move_to_library"},
    },
    "cable-tow::candidate_lesson::p5": {
        "needs_provider_review": False,
        "routing_decision_any_of": {"move_to_library"},
    },
    "l1-obligation-chovot-haach-badraga-harishona::symbolic_meaning::p2": {
        "needs_provider_review": False,
        "routing_decision_any_of": {"keep_here_framed"},
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate F3 Phase J micro-regression cases.")
    parser.add_argument("--f2-report-dir", type=Path, default=DEFAULT_F2_REPORT_DIR)
    parser.add_argument("--review-unit-id", action="append", dest="review_unit_ids", default=[])
    parser.add_argument("--json", action="store_true", help="Emit full JSON results.")
    return parser.parse_args()


def load_row_index(entry_rows: list[dict[str, Any]]) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    index: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for entry in entry_rows:
        slug = f3.normalize_text(entry.get("slug"))
        if not slug:
            continue
        for row in entry.get("paragraph_reviews", []):
            review_unit_id = f3.normalize_text(row.get("review_unit_id"))
            if review_unit_id:
                index[review_unit_id] = (entry, row)
    return index


def evaluate_case(
    *,
    review_unit_id: str,
    source_entry: dict[str, Any],
    row: dict[str, Any],
    slug_map: dict[str, dict[str, Any]],
    by_category: dict[str, list[str]],
    taxonomy: dict[str, Any],
) -> dict[str, Any]:
    existing_shortlist = f3.build_existing_entry_shortlist(
        source_entry=source_entry,
        slug_map=slug_map,
        by_category=by_category,
    )
    heuristic_route = f3.build_heuristic_route(
        row=row,
        source_entry=source_entry,
        existing_shortlist=existing_shortlist,
        slug_map=slug_map,
        taxonomy=taxonomy,
    )
    annotated_route = f3.annotate_heuristic_route(
        row=row,
        source_entry=source_entry,
        heuristic_route=heuristic_route,
        existing_shortlist=existing_shortlist,
        slug_map=slug_map,
        taxonomy=taxonomy,
    )
    preclassification = f3.build_routing_preclassification(row=row, heuristic_route=annotated_route)
    return {
        "review_unit_id": review_unit_id,
        "field_name": row.get("field_name"),
        "heuristic_decision_before_promotion": heuristic_route.get("routing_decision"),
        "heuristic_confidence_before_promotion": heuristic_route.get("routing_confidence"),
        "routing_decision": annotated_route.get("routing_decision"),
        "routing_confidence": annotated_route.get("routing_confidence"),
        "target_slug": annotated_route.get("target_slug"),
        "future_entry_label": annotated_route.get("future_entry_label"),
        "library_bucket": annotated_route.get("library_bucket"),
        "taxonomy_match_reason": annotated_route.get("taxonomy_match_reason"),
        "needs_provider_review": preclassification.get("needs_provider_review"),
        "provider_skip_reason": preclassification.get("provider_skip_reason"),
        "routing_signal_families": annotated_route.get("routing_signal_families", []),
        "routing_reason_codes": annotated_route.get("routing_reason_codes", []),
        "routing_rule_families": annotated_route.get("routing_rule_families", []),
        "routing_clusters": annotated_route.get("routing_clusters", []),
        "routing_conflict_detected": annotated_route.get("routing_conflict_detected"),
        "routing_conflict_reasons": annotated_route.get("routing_conflict_reasons", []),
        "promotion_skip_reason": annotated_route.get("promotion_skip_reason"),
        "force_provider_review": annotated_route.get("force_provider_review"),
        "f2_final_verdict": row.get("final_verdict"),
        "f2_detection_confidence": row.get("detection_confidence"),
        "f2_recommended_preservation_action": row.get("recommended_preservation_action"),
        "f2_promoted_rule_families": row.get("promoted_rule_families", []),
        "f2_promotion_clusters": row.get("promotion_clusters", []),
    }


def assert_expectations(result: dict[str, Any], expectation: dict[str, Any]) -> None:
    expected_needs_provider_review = expectation.get("needs_provider_review")
    if expected_needs_provider_review is not None and result["needs_provider_review"] != expected_needs_provider_review:
        raise AssertionError(
            f"{result['review_unit_id']}: needs_provider_review expected {expected_needs_provider_review} "
            f"got {result['needs_provider_review']}"
        )
    allowed_decisions = expectation.get("routing_decision_any_of")
    if allowed_decisions and result["routing_decision"] not in allowed_decisions:
        raise AssertionError(
            f"{result['review_unit_id']}: routing_decision expected one of {sorted(allowed_decisions)} "
            f"got {result['routing_decision']}"
        )


def main() -> None:
    args = parse_args()
    f2_artifacts = f3.load_f2_artifacts(args.f2_report_dir)
    site_root, _manifest_path = f3.resolve_runtime_context(
        f2_artifacts=f2_artifacts,
        site_root_arg=None,
        manifest_arg=None,
    )
    taxonomy = f3.load_taxonomy(f3.DEFAULT_TAXONOMY_FILE)
    _dataset, slug_map, by_category = f3.load_level1_context(site_root)
    row_index = load_row_index(f2_artifacts["entry_rows"])

    target_ids = args.review_unit_ids or list(TARGET_EXPECTATIONS.keys())
    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for review_unit_id in target_ids:
        if review_unit_id not in row_index:
            failures.append(f"{review_unit_id}: missing from F2 report rows")
            continue
        source_entry, row = row_index[review_unit_id]
        result = evaluate_case(
            review_unit_id=review_unit_id,
            source_entry=source_entry,
            row=row,
            slug_map=slug_map,
            by_category=by_category,
            taxonomy=taxonomy,
        )
        results.append(result)
        expectation = TARGET_EXPECTATIONS.get(review_unit_id)
        if expectation:
            try:
                assert_expectations(result, expectation)
            except AssertionError as exc:
                failures.append(str(exc))

    payload = {
        "f2_report_dir": str(args.f2_report_dir.resolve()),
        "case_count": len(results),
        "passed": not failures,
        "results": results,
        "failures": failures,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for result in results:
            print(
                f"{result['review_unit_id']}: "
                f"decision={result['routing_decision']} "
                f"confidence={result['routing_confidence']} "
                f"needs_provider_review={result['needs_provider_review']} "
                f"skip={result['provider_skip_reason'] or '-'}"
            )
        if failures:
            print("")
            print("FAILURES:")
            for failure in failures:
                print(f"- {failure}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
