"""Reader-facing text must not leak machine identifiers or local paths.

Observed leak (2026-06-12): site rendered a full Windows path from work-title
provenance and a raw section marker from full_summary. The pipeline now
sanitizes provenance paths at the source, and the validation gate fails any
root whose display fields carry absolute paths or out-of-place markers.
"""

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
from PDF_handle.prod.schema.patches import build_source_note, display_source_path

RUNTIME_FIXTURE = REPO_ROOT / "data" / "fixtures" / "runtime_site_root"


class TestDisplaySourcePath(unittest.TestCase):
    def test_absolute_windows_path_reduced_to_repo_anchor(self) -> None:
        path = r"C:\Users\someone\OneDrive\Documents\code\PDF_handle\consolidated_books\duncan.md"
        self.assertEqual(display_source_path(path), "consolidated_books/duncan.md")

    def test_absolute_path_without_anchor_reduced_to_filename(self) -> None:
        self.assertEqual(display_source_path(r"D:\private\secret\book.md"), "book.md")
        self.assertEqual(display_source_path("/home/user/book.md"), "book.md")

    def test_relative_path_kept(self) -> None:
        self.assertEqual(display_source_path("sources/book.md"), "sources/book.md")

    def test_empty_input(self) -> None:
        self.assertEqual(display_source_path(""), "")

    def test_build_source_note_never_carries_absolute_path(self) -> None:
        note = build_source_note(
            work_title="Some Work",
            section_title="Chapter 1",
            source_path=r"C:\Users\someone\Documents\code\PDF_handle\consolidated_books\work.md",
            source_anchor="sec-1",
            source_order=1,
        )
        self.assertNotIn("C:", note)
        self.assertIn("consolidated_books/work.md#sec-1", note)


class GateHygieneCase(unittest.TestCase):
    def _tampered_root(self, mutate) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="hygiene_case_"))
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

    def test_clean_fixture_passes_hygiene(self) -> None:
        report = validate_runtime_site_root(RUNTIME_FIXTURE)
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["ok"])

    def test_absolute_path_in_source_notes_fails(self) -> None:
        def mutate(payload):
            payload["entries"][0]["source_notes"] = [
                r"Some Work | Page 6 | C:\Users\someone\Documents\code\book.md | section 1"
            ]
        self.assert_gate_fails(self._tampered_root(mutate), "absolute local path")

    def test_absolute_path_in_work_title_fails(self) -> None:
        def mutate(payload):
            payload["entries"][0]["work_title"] = r"Blue Lodge Guide | Page 6 | C:\Users\someone\book.md"
        self.assert_gate_fails(self._tampered_root(mutate), "absolute local path")

    def test_marker_outside_full_summary_fails(self) -> None:
        def mutate(payload):
            payload["entries"][0]["short_summary"] = (
                "Summary <!-- PDF_STAGE5:some-work:section-0004 --> trailing"
            )
        self.assert_gate_fails(self._tampered_root(mutate), "provenance marker outside full_summary")

    def test_marker_inside_full_summary_is_allowed(self) -> None:
        def mutate(payload):
            payload["entries"][0]["full_summary"] = (
                "Base text.\n\n<!-- PDF_STAGE5:some-work:section-0004 -->\nEnrichment.\n"
                "<!-- /PDF_STAGE5:some-work:section-0004 -->"
            )
        report = validate_runtime_site_root(self._tampered_root(mutate))
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["ok"])


if __name__ == "__main__":
    unittest.main()
