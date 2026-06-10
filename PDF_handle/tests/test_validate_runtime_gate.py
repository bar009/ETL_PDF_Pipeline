"""The validation gate must pass good data and fail each bad-data class (WS4)."""

from __future__ import annotations

import json
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
STAGING_FIXTURE = REPO_ROOT / "data" / "fixtures" / "staging_minimal"


class GateCase(unittest.TestCase):
    def _tampered_root(self, mutate) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="gate_case_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        site_root = tmp / "site_root"
        shutil.copytree(RUNTIME_FIXTURE, site_root)
        level1_path = site_root / "data" / "level1.json"
        payload = json.loads(level1_path.read_text(encoding="utf-8"))
        mutate(payload)
        level1_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return site_root

    def assert_gate_fails(self, site_root: Path, needle: str) -> None:
        report = validate_runtime_site_root(site_root)
        self.assertFalse(report["ok"], "gate unexpectedly passed")
        self.assertTrue(
            any(needle in error for error in report["errors"]),
            f"expected an error mentioning {needle!r}; got: {report['errors']}",
        )


class TestGatePassesGoodData(unittest.TestCase):
    def test_runtime_fixture_is_publishable(self) -> None:
        report = validate_runtime_site_root(RUNTIME_FIXTURE)
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["ok"])

    def test_require_complete_flags_missing_degree_files(self) -> None:
        # The minimal fixture has only level1.json — completeness is opt-in.
        report = validate_runtime_site_root(RUNTIME_FIXTURE, require_complete=True)
        self.assertFalse(report["ok"])
        self.assertTrue(any("missing required degree file" in e for e in report["errors"]))


class TestGateFailsBadData(GateCase):
    def test_staging_dir_is_not_publishable(self) -> None:
        self.assert_gate_fails(STAGING_FIXTURE, "not a site root")

    def test_duplicate_slug(self) -> None:
        def mutate(payload):
            payload["entries"].append(dict(payload["entries"][0]))
        self.assert_gate_fails(self._tampered_root(mutate), "duplicated")

    def test_broken_relation_target(self) -> None:
        def mutate(payload):
            payload["entries"][1]["related_topics"] = {"prior": ["no-such-entry"]}
        self.assert_gate_fails(self._tampered_root(mutate), "missing related_topics ref")

    def test_illegal_status(self) -> None:
        def mutate(payload):
            payload["entries"][0]["status"] = "totally-not-a-status"
        self.assert_gate_fails(self._tampered_root(mutate), "status must be one of")

    def test_book_without_provenance(self) -> None:
        def mutate(payload):
            entry = dict(payload["entries"][1])
            entry.update(
                slug="orphan-book",
                title="ספר ללא מקור",
                type="book",
                source_notes=[],
                related_topics=[],
                parent_topic=None,
            )
            payload["entries"].append(entry)
        self.assert_gate_fails(self._tampered_root(mutate), "no source_notes and no work_id")

    def test_strict_mode_fails_on_warnings(self) -> None:
        # The fixture's published gate entry has no source_notes -> warning.
        report = validate_runtime_site_root(RUNTIME_FIXTURE, strict=True)
        self.assertFalse(report["ok"])
        self.assertTrue(report["warnings"])


if __name__ == "__main__":
    unittest.main()
