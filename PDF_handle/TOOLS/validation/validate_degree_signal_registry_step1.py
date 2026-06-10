from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import argparse
import json
from typing import Any

from degree_signal_registry import load_degree_registry
from semantic_system_purity_review import classify_semantic_content


def evaluate_case(*, text: str) -> dict[str, Any]:
    registry = load_degree_registry()
    result = classify_semantic_content(
        field_name="candidate_lesson",
        paragraph=text,
        lexical_overlay={"matched_families": []},
        lexical_detection=None,
        is_framed=False,
        degree_registry=registry,
    )
    return {
        "content_class": result["content_class"],
        "signal_strength": result["signal_strength"],
        "later_degree_leakage_detected": result["later_degree_leakage_detected"],
        "foreign_system_contamination_detected": result["foreign_system_contamination_detected"],
        "mixedness_detected": result["mixedness_detected"],
        "degree_signal_hit_count": result["degree_signal_hit_count"],
        "degree_reason_codes": result["degree_reason_codes"],
        "degree_family_counts": result["degree_family_counts"],
        "cross_degree_collision": result["cross_degree_collision"],
        "degree_weak_only_bucket": result["degree_weak_only_bucket"],
        "degree_target_strong_anchor_detected": result["degree_target_strong_anchor_detected"],
        "degree_native_boost": result["degree_native_boost"],
        "degree_native_suppression": result["degree_native_suppression"],
        "degree_foreign_boost": result["degree_foreign_boost"],
        "degree_mixedness_boost": result["degree_mixedness_boost"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cases = {
        "degree1_strong_anchor": {
            "text": "×ª×œ×ž×™×“ ×‘×•× ×” ×œ×•×‘×© ×¡×™× ×¨ ×œ×‘×Ÿ ×•×”×—×‘×œ ×”×˜×§×¡×™ ×ž×¡×ž×Ÿ ×ž×©×ž×¢×ª ×•×”×›×•×•× ×”.",
            "checks": [
                lambda r: r["degree_target_strong_anchor_detected"],
                lambda r: "degree_1_strong_anchor_detected" in r["degree_reason_codes"],
                lambda r: not r["later_degree_leakage_detected"],
                lambda r: not r["cross_degree_collision"],
            ],
        },
        "weak_moral_only": {
            "text": "××ž×ª ×¦×“×§ ×•××”×‘×ª ××—×™× ×”× ×¢×¨×›×™× ×—×©×•×‘×™× ×œ××“×.",
            "checks": [
                lambda r: r["degree_weak_only_bucket"],
                lambda r: "standalone_weak_term_suppressed" in r["degree_reason_codes"],
                lambda r: not r["degree_target_strong_anchor_detected"],
                lambda r: r["degree_native_suppression"] >= 1,
            ],
        },
        "degree2_contamination": {
            "text": "×”×ž×“×¨×’×•×ª ×”×œ×•×œ×™×™× ×™×•×ª ×ž×•×‘×™×œ×•×ª ××œ ×”××•×œ× ×”×ª×™×›×•×Ÿ, ×•×©×™×‘×•×œ×ª × ×©×ž×¨×ª ×›×¡×™×ž×Ÿ ×©×œ ××•×ž×Ÿ ×—×‘×¨.",
            "checks": [
                lambda r: "degree_2_strong_anchor_detected" in r["degree_reason_codes"],
                lambda r: "higher_degree_contamination_detected" in r["degree_reason_codes"],
                lambda r: r["degree_foreign_boost"] >= 2,
                lambda r: r["later_degree_leakage_detected"],
            ],
        },
        "degree3_contamination": {
            "text": "×—×™×¨× ××‘×™×£ ×•×”×ž×™×œ×” ×”××‘×•×“×” ×ž×¨×ž×–×™× ×›××Ÿ ×¢×œ ×¨×•×‘×“ ×©××™× ×• ×©×™×™×š ×œ×“×¨×’×” ×”×¨××©×•× ×”.",
            "checks": [
                lambda r: "degree_3_strong_anchor_detected" in r["degree_reason_codes"],
                lambda r: "higher_degree_contamination_detected" in r["degree_reason_codes"],
                lambda r: r["degree_foreign_boost"] >= 2,
                lambda r: r["later_degree_leakage_detected"],
            ],
        },
        "cross_degree_collision": {
            "text": "×ª×œ×ž×™×“ ×‘×•× ×” ×¢× ×¡×™× ×¨ ×œ×‘×Ÿ, ××š ×‘×”×ž×©×š ×ž×•×–×›×¨×™× ×”××•×œ× ×”×ª×™×›×•×Ÿ ×•×”×ž×“×¨×’×•×ª ×”×œ×•×œ×™×™× ×™×•×ª.",
            "checks": [
                lambda r: r["cross_degree_collision"],
                lambda r: "cross_degree_collision_detected" in r["degree_reason_codes"],
                lambda r: r["degree_mixedness_boost"] >= 1,
                lambda r: r["mixedness_detected"],
            ],
        },
    }

    results: dict[str, Any] = {}
    failures: list[str] = []
    for case_name, case in cases.items():
        result = evaluate_case(text=case["text"])
        passed = True
        for check in case["checks"]:
            if not check(result):
                passed = False
                break
        results[case_name] = {"passed": passed, "result": result}
        if not passed:
            failures.append(case_name)

    if args.json:
        print(json.dumps({"failures": failures, "results": results}, ensure_ascii=False, indent=2))
        if failures:
            raise SystemExit(1)
        return

    for case_name, payload in results.items():
        status = "PASS" if payload["passed"] else "FAIL"
        print(f"[{status}] {case_name}")
        print(json.dumps(payload["result"], ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

