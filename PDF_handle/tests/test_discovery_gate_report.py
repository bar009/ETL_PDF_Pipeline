from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.steps.stage import build_discovery_gate_report


def _row(*, decision: str, source_genre: str | None = None, strong: int = 0, medium: int = 0) -> dict:
    return {
        "decision": decision,
        "candidate_degree": "level2" if decision == "existing_match" else "unknown",
        "unit_kind": "procedural_fragment" if decision == "reject_or_noise" else "topic",
        "reason_codes": ["TEST_REASON"],
        "confidence": "medium",
        "strong_match_count": strong,
        "medium_match_count": medium,
        "work_id": "wid",
        "source_genre": source_genre,
    }


class DiscoveryGateReportTest(unittest.TestCase):
    def test_non_enrichment_high_rejection_still_fails(self) -> None:
        rows = [
            *[_row(decision="reject_or_noise") for _ in range(7)],
            *[_row(decision="existing_match", strong=1) for _ in range(3)],
        ]
        report = build_discovery_gate_report(rows)
        self.assertFalse(report["ok"])
        self.assertFalse(report["gates"]["overall_rejection_rate"]["ok"])
        self.assertFalse(report["gates"]["overall_rejection_rate"]["waived_for_enrichment_source"])

    def test_enrichment_high_rejection_with_signal_is_waived(self) -> None:
        rows = [
            *[_row(decision="reject_or_noise", source_genre="enrichment_source", medium=1) for _ in range(7)],
            *[_row(decision="existing_match", source_genre="enrichment_source", strong=1) for _ in range(3)],
        ]
        report = build_discovery_gate_report(rows)
        self.assertTrue(report["ok"])
        self.assertTrue(report["gates"]["overall_rejection_rate"]["ok"])
        self.assertTrue(report["gates"]["overall_rejection_rate"]["waived_for_enrichment_source"])
        self.assertTrue(report["gates"]["enrichment_match_signal"]["applicable"])
        self.assertTrue(report["gates"]["enrichment_match_signal"]["ok"])

    def test_enrichment_high_rejection_without_signal_still_fails(self) -> None:
        rows = [_row(decision="reject_or_noise", source_genre="enrichment_source") for _ in range(10)]
        report = build_discovery_gate_report(rows)
        self.assertFalse(report["ok"])
        self.assertFalse(report["gates"]["overall_rejection_rate"]["ok"])
        self.assertFalse(report["gates"]["overall_rejection_rate"]["waived_for_enrichment_source"])
        self.assertFalse(report["gates"]["enrichment_match_signal"]["ok"])


if __name__ == "__main__":
    unittest.main()
