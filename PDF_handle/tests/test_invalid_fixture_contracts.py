"""Contract-by-failure: every committed invalid fixture must fail the gate (WS5).

A contract that only proves success is half a contract. Each file under
``data/fixtures/invalid/`` breaks exactly one rule; the validation gate must
reject it with an error naming that rule.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.cli.validate_runtime import validate_runtime_site_root

RUNTIME_FIXTURE = REPO_ROOT / "data" / "fixtures" / "runtime_site_root"
INVALID_DIR = REPO_ROOT / "data" / "fixtures" / "invalid"
STAGING_FIXTURE = REPO_ROOT / "data" / "fixtures" / "staging_minimal"

# file name -> substring the gate error must mention
EXPECTED_FAILURES = {
    "duplicate_slug.level1.json": ["duplicated in source file"],
    "missing_relation_target.level1.json": ["missing related_topics ref"],
    "illegal_status.level1.json": ["status must be one of"],
    "missing_required_fields.level1.json": ["missing a title", "missing a slug"],
}


class TestInvalidFixturesFailTheGate(unittest.TestCase):
    def _site_root_with(self, invalid_level1: Path) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="invalid_fixture_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        site_root = tmp / "site_root"
        shutil.copytree(RUNTIME_FIXTURE, site_root)
        shutil.copyfile(invalid_level1, site_root / "data" / "level1.json")
        return site_root

    def test_every_invalid_fixture_is_covered(self) -> None:
        on_disk = {p.name for p in INVALID_DIR.glob("*.level1.json")}
        self.assertEqual(
            on_disk,
            set(EXPECTED_FAILURES),
            "data/fixtures/invalid/ and EXPECTED_FAILURES must list the same cases",
        )

    def test_each_invalid_fixture_fails_for_its_own_reason(self) -> None:
        for name, needles in EXPECTED_FAILURES.items():
            with self.subTest(case=name):
                report = validate_runtime_site_root(self._site_root_with(INVALID_DIR / name))
                self.assertFalse(report["ok"], f"{name} unexpectedly passed the gate")
                for needle in needles:
                    self.assertTrue(
                        any(needle in error for error in report["errors"]),
                        f"{name}: expected an error mentioning {needle!r}; got {report['errors']}",
                    )

    def test_staging_as_runtime_fails_the_gate(self) -> None:
        report = validate_runtime_site_root(STAGING_FIXTURE)
        self.assertFalse(report["ok"])
        self.assertTrue(any("not a site root" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
