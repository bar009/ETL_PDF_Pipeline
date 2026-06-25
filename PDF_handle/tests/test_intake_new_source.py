"""Intake CLI: routing scaffold blocks staging, diagnosis picks the right runbook case."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.cli.intake_new_source import (
    build_routing_scaffold,
    diagnose_markdown,
    ensure_routing_entry,
    slugify,
)


class TestSlugify(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertEqual(slugify("A Basic Masonic Education Course"), "a-basic-masonic-education-course")

    def test_punctuation_collapses(self) -> None:
        self.assertEqual(slugify("Duncan's Ritual (1866) -- 3rd ed."), "duncan-s-ritual-1866-3rd-ed")


class TestRoutingScaffold(unittest.TestCase):
    def test_scaffold_blocks_staging(self) -> None:
        entry = build_routing_scaffold("New Book")
        self.assertEqual(entry["applies_to_degrees"], [])
        self.assertEqual(entry["primary_degree"], "TODO")
        self.assertEqual(entry["default_sensitivity_level"], "guarded")

    def test_ensure_creates_then_preserves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            routing = Path(tmp) / "work_routing.json"
            routing.write_text(json.dumps({"works": []}), encoding="utf-8")
            entry, created = ensure_routing_entry(routing, "New Book")
            self.assertTrue(created)
            # Second call must not overwrite (operator may have filled degrees).
            data = json.loads(routing.read_text(encoding="utf-8"))
            data["works"][0]["applies_to_degrees"] = ["library", "level1"]
            routing.write_text(json.dumps(data), encoding="utf-8")
            entry2, created2 = ensure_routing_entry(routing, "New Book")
            self.assertFalse(created2)
            self.assertEqual(entry2["applies_to_degrees"], ["library", "level1"])


class TestDiagnosis(unittest.TestCase):
    def _diagnose(self, text: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "b.md"
            p.write_text(text, encoding="utf-8")
            return diagnose_markdown(p)

    def test_page_based(self) -> None:
        text = "\n".join(f"## Page {i}\n\nsome text" for i in range(1, 20))
        self.assertTrue(self._diagnose(text)["runbook_case"].startswith("A"))

    def test_pause_commentary(self) -> None:
        text = "## Page 1\n\n" + "\n".join(
            f"{i}th Pause: after something.\nCommentary: meaning of it." for i in (4, 5, 6)
        )
        self.assertTrue(self._diagnose(text)["runbook_case"].startswith("B"))

    def test_chapter_book(self) -> None:
        text = "## Page 1\n\nCHAPTER IX. MASONS' MARKS. text\nCHAPTER X. THE QUATUOR CORONATI. text"
        self.assertTrue(self._diagnose(text)["runbook_case"].startswith("C"))

    def test_already_semantic(self) -> None:
        text = "\n".join(f"## Topic {i}\n\nreal content here" for i in range(8))
        self.assertIn("already semantic", self._diagnose(text)["runbook_case"])


if __name__ == "__main__":
    unittest.main()
