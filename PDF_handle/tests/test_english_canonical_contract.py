from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.cli.seed_clean_rerun_root import (  # noqa: E402
    apply_english_canonical_labels,
    write_english_degrees_manifest,
)
from PDF_handle.prod.companion_contract import (  # noqa: E402
    CompanionCanonicalLanguageError,
    materialize_companion_payload,
)
from PDF_handle.prod.core.io import read_json, write_json  # noqa: E402
from PDF_handle.prod.steps.stage_mapping import coerce_mapping_payload  # noqa: E402
from PDF_handle.prod.steps.stage_support import ExtractedSection, build_discovery_record  # noqa: E402


LEVEL1_CATEGORIES = {
    "uncategorized": {
        "id": "uncategorized",
        "title": "Uncategorized",
        "symbol": "*",
        "description": "",
        "parent_category": None,
    }
}


class EnglishCanonicalContractTest(unittest.TestCase):
    def test_mapping_payload_returns_english_canonical_keys(self) -> None:
        payload = coerce_mapping_payload(
            {
                "section_summary": "A concise English summary.",
                "practical_elements": ["Working tools"],
                "symbolic_meaning": "Moral formation.",
                "candidate_lesson": "Begin with disciplined attention.",
                "keywords": ["Entered Apprentice"],
                "caution_notes": [],
                "tradition_notes": [],
                "target_entry_candidates": [],
                "knowledge_link_candidates": [],
                "new_topic_candidates": [],
            }
        )

        self.assertEqual(payload["section_summary"], "A concise English summary.")
        self.assertEqual(payload["practical_elements"], ["Working tools"])
        self.assertNotIn("section_summary_he", payload)

    def test_legacy_mapping_payload_is_read_but_normalized_to_canonical_keys(self) -> None:
        payload = coerce_mapping_payload(
            {
                "section_summary_he": "Legacy summary.",
                "practical_elements_he": ["Legacy item"],
                "symbolic_meaning_he": "Legacy symbolism.",
                "candidate_lesson_he": "Legacy lesson.",
                "keywords": [],
                "caution_notes_he": [],
                "tradition_notes_he": [],
                "target_entry_candidates": [],
                "knowledge_link_candidates": [],
                "new_topic_candidates": [],
            }
        )

        self.assertEqual(payload["section_summary"], "Legacy summary.")
        self.assertNotIn("section_summary_he", payload)

    def test_companion_payload_materializes_as_english_source_record(self) -> None:
        candidate = {
            "work_id": "basic-masonic-education-course",
            "work_title": "Basic Masonic Education Course",
            "draft_seed": {
                "slug": "basic-candidate",
                "title": "The First Lesson",
                "degree": "level1",
                "category": "uncategorized",
                "short_summary": "A first-degree learning note.",
                "full_summary": "",
            },
        }

        payload = materialize_companion_payload(
            candidate,
            categories_by_degree={"level1": LEVEL1_CATEGORIES},
        )

        self.assertEqual(payload["language"], "en")
        self.assertEqual(payload["translation_mode"], "source")
        self.assertEqual(payload["short_summary"], "A first-degree learning note.")

    def test_companion_payload_rejects_hebrew_in_protected_fields(self) -> None:
        candidate = {
            "work_id": "basic-masonic-education-course",
            "work_title": "Basic Masonic Education Course",
            "draft_seed": {
                "slug": "bad-candidate",
                "title": "שורש עברי",
                "degree": "level1",
                "category": "uncategorized",
            },
        }

        with self.assertRaises(CompanionCanonicalLanguageError):
            materialize_companion_payload(
                candidate,
                categories_by_degree={"level1": LEVEL1_CATEGORIES},
            )

    def test_seed_projection_can_scrub_titles_and_categories_to_english(self) -> None:
        payload = apply_english_canonical_labels(
            "level1",
            {
                "meta": {"degree": "level1", "title": "דרגה 1", "updated_at": "now"},
                "categories": {
                    "working_tools": {
                        "id": "working_tools",
                        "title": "כלי עבודה",
                        "symbol": "*",
                        "description": "תיאור עברי",
                        "parent_category": None,
                    }
                },
                "entries": [],
            },
        )

        self.assertEqual(payload["meta"]["title"], "Degree 1 - Entered Apprentice")
        self.assertEqual(payload["categories"]["working_tools"]["title"], "Working Tools")
        self.assertEqual(payload["categories"]["working_tools"]["description"], "")

    def test_degrees_manifest_can_be_relabelled_to_english(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "degrees.json"
            write_json(path, {"level1": {"title": "דרגה 1"}, "library": {"title": "ספרייה"}})

            write_english_degrees_manifest(path)

            payload = read_json(path)
            self.assertEqual(payload["level1"]["title"], "Degree 1 - Entered Apprentice")
            self.assertEqual(payload["library"]["title"], "Library and Sources")

    def test_out_of_route_degree_title_does_not_fallback_to_primary_degree(self) -> None:
        section = ExtractedSection(
            section_id="section-0001",
            title="THE MASTER MASON DEGREE",
            marker_type="heading",
            text="THE MASTER MASON DEGREE\n\nA short source passage.",
            source_anchor="the-master-mason-degree",
            source_order=1,
            normalized_title="THE MASTER MASON DEGREE",
            unit_kind="topic",
        )

        record = build_discovery_record(
            section=section,
            route_primary_degree="level1",
            combined_result={
                "new_topic_candidates": [{"title": "THE MASTER MASON DEGREE", "degree": "level1"}],
            },
            resolution={"strong": [], "medium": [], "rejected": []},
            allowed_degrees=["library", "level1"],
            apply_allowed_degrees=["library", "level1"],
        )

        self.assertEqual(record["decision"], "reject_or_noise")
        self.assertEqual(record["candidate_degree"], "unknown")
        self.assertIn("TITLE_DEGREE_OUT_OF_ROUTE", record["reason_codes"])


if __name__ == "__main__":
    unittest.main()
