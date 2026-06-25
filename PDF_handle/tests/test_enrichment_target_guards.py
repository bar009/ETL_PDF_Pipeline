"""Enrichment must never target hubs or carry appendant-degree content.

Both leaks were observed in the 2026-06-12 content review: the Philosophy hub
accumulated 38K of appended blocks, and Royal Arch / Mark Master sections from
Duncan's were attached to level1-3 entries via provider-suggested matches.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.steps.stage_support import (
    build_entry_catalog,
    is_appendant_degree_title,
    resolve_target_matches,
)


def _dataset() -> dict:
    return {
        "meta": {"degree": "level2"},
        "entries": [
            {"slug": "level2-hub-working-tools", "title": "Working Tools", "type": "hub",
             "category": "working_tools", "parent_topic": None},
            {"slug": "the-square", "title": "The Square", "type": "topic",
             "category": "working_tools", "parent_topic": "level2-hub-working-tools"},
        ],
    }


class TestHubExclusion(unittest.TestCase):
    def test_hubs_are_not_match_targets(self) -> None:
        catalog = build_entry_catalog(_dataset())
        slugs = {item["slug"] for item in catalog["items"]}
        self.assertNotIn("level2-hub-working-tools", slugs)
        self.assertIn("the-square", slugs)


class TestAppendantDegreeVeto(unittest.TestCase):
    def test_appendant_titles_detected(self) -> None:
        for title in (
            "Royal Arch: Exaltation Ceremony",
            "Mark Master: Grips and the Wages Parable",
            "Most Excellent Master Lecture",
            "Past Master: Investiture and Lecture",
        ):
            self.assertTrue(is_appendant_degree_title(title), title)

    def test_craft_titles_pass(self) -> None:
        for title in (
            "The Master Mason Degree",
            "Working Tools of a Fellow Craft",
            "Raising on the Five Points of Fellowship",
        ):
            self.assertFalse(is_appendant_degree_title(title), title)

    def test_appendant_section_resolves_to_no_targets(self) -> None:
        catalog = build_entry_catalog(_dataset())
        strong_lexical = [{
            "degree": "level2", "slug": "the-square", "title": "The Square",
            "category": "working_tools", "heading_hit": True,
            "title_terms": ["square"], "body_terms": [], "supporting_terms": ["square", "tool"],
            "score": 9,
        }]
        vetoed = resolve_target_matches(
            {}, strong_lexical, catalog,
            allowed_degrees=["level2"], section_title="Royal Arch: Passing the Veils",
        )
        self.assertEqual(vetoed, {"strong": [], "medium": [], "rejected": []})
        normal = resolve_target_matches(
            {}, strong_lexical, catalog,
            allowed_degrees=["level2"], section_title="The Working Tools",
        )
        self.assertEqual(len(normal["strong"]), 1)


if __name__ == "__main__":
    unittest.main()
