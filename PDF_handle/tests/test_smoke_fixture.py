"""The fixture smoke must pass on a clean checkout and report failures honestly."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.cli.smoke_fixture import run_smoke

EXPECTED_STEPS = [
    "site_root_contract",
    "pre_state_valid",
    "staged_operations_present",
    "operations_approved",
    "apply_is_idempotent",
    "provenance_marker_present",
    "merged_state_valid",
    "runtime_write_roundtrip",
]


class TestSmokeFixture(unittest.TestCase):
    def test_smoke_passes_on_clean_checkout(self) -> None:
        report = run_smoke()
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["ok"])

    def test_smoke_runs_the_full_step_list(self) -> None:
        report = run_smoke()
        self.assertEqual([s["name"] for s in report["steps"]], EXPECTED_STEPS)
        self.assertTrue(all(s["ok"] for s in report["steps"]))


if __name__ == "__main__":
    unittest.main()
