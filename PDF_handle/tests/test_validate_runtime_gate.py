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

    def _level1_only_root(self, mutate) -> Path:
        return self._tampered_root(mutate)

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

    def test_structural_published_entries_do_not_warn_without_source_notes(self) -> None:
        report = validate_runtime_site_root(RUNTIME_FIXTURE, strict=True)
        self.assertFalse(
            any("published without source_notes" in warning for warning in report["warnings"])
        )


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

    def test_strict_mode_fails_on_published_content_without_source_notes(self) -> None:
        def mutate(payload):
            payload["entries"][1]["type"] = "topic"
            payload["entries"][1]["status"] = "published"
            payload["entries"][1]["source_notes"] = []
            payload["entries"][1]["work_id"] = None

        report = validate_runtime_site_root(self._level1_only_root(mutate), strict=True)
        self.assertFalse(report["ok"])
        self.assertTrue(any("published without source_notes" in warning for warning in report["warnings"]))


class TestWorkLibraryCoverage(GateCase):
    """A degree lane must never cite a work the library lane does not hold.

    This is the hybrid-sandbox gap from the 2026-06-11 pilot: level2 carried
    work_id=color-symbolism while library.json was empty, and the gate passed.
    """

    def _library_payload(self, entries: list[dict]) -> dict:
        return {
            "meta": {
                "degree": "library",
                "title": "Library fixture",
                "updated_at": "2026-06-11T00:00:00Z",
            },
            "categories": {"sources": {"title": "Sources", "symbol": "*"}},
            "entries": entries,
        }

    def _root_with_work_id(self, library_entries: list[dict] | None) -> Path:
        def mutate(payload):
            payload["entries"][1]["work_id"] = "ghost-work"
            payload["entries"][1]["source_notes"] = ["Ghost Work | section 1"]

        site_root = self._tampered_root(mutate)
        if library_entries is not None:
            library_path = site_root / "data" / "library.json"
            library_path.write_text(
                json.dumps(self._library_payload(library_entries), ensure_ascii=False),
                encoding="utf-8",
            )
        return site_root

    def test_work_id_without_library_entry_fails(self) -> None:
        site_root = self._root_with_work_id(library_entries=[])
        self.assert_gate_fails(site_root, "library lane has no entry for that work")

    def test_work_id_with_library_chapter_passes(self) -> None:
        chapter = {
            "title": "Ghost Work, Chapter 1",
            "slug": "ghost-work-chapter-1",
            "type": "chapter",
            "degree": "library",
            "applies_to_degrees": ["library"],
            "category": "sources",
            "parent_topic": None,
            "related_topics": [],
            "short_summary": "Fixture chapter.",
            "source_notes": ["Ghost Work | chapter 1"],
            "work_id": "ghost-work",
            "status": "draft",
        }
        report = validate_runtime_site_root(self._root_with_work_id(library_entries=[chapter]))
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["ok"])

    def test_work_id_without_library_file_warns(self) -> None:
        report = validate_runtime_site_root(self._root_with_work_id(library_entries=None))
        self.assertEqual(report["errors"], [])
        self.assertTrue(
            any("library.json is not present to verify coverage" in w for w in report["warnings"])
        )


if __name__ == "__main__":
    unittest.main()
