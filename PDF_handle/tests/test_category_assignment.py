"""Provider-driven category assignment at stage time (no more first-key dumping)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.schema.data import normalize_degree_data
from PDF_handle.prod.steps.stage import build_companion_candidate, choose_candidate_category
from PDF_handle.prod.steps.stage_mapping import (
    MAPPING_RESPONSE_SCHEMA,
    build_mapping_user_prompt,
    coerce_mapping_payload,
)
from PDF_handle.prod.steps.stage_support import combine_mapping_results, pick_majority_string

RUNTIME_FIXTURE_LEVEL1 = REPO_ROOT / "data" / "fixtures" / "runtime_site_root" / "data" / "level1.json"


def _dataset() -> dict:
    raw = json.loads(RUNTIME_FIXTURE_LEVEL1.read_text(encoding="utf-8"))
    raw["categories"]["symbols"] = {"id": "symbols", "title": "Symbols", "symbol": "*"}
    return normalize_degree_data(raw, "level1")


class TestCoercePayload(unittest.TestCase):
    def test_payload_carries_suggested_category(self) -> None:
        payload = coerce_mapping_payload(
            {"suggested_category": "symbols", "suggested_category_reason": "About emblems."}
        )
        self.assertEqual(payload["suggested_category"], "symbols")
        self.assertEqual(payload["suggested_category_reason"], "About emblems.")

    def test_absent_suggested_category_defaults_none(self) -> None:
        payload = coerce_mapping_payload({})
        self.assertIsNone(payload["suggested_category"])
        self.assertEqual(payload["suggested_category_reason"], "")

    def test_response_schema_requires_the_new_keys(self) -> None:
        self.assertIn("suggested_category", MAPPING_RESPONSE_SCHEMA["required"])
        self.assertIn("suggested_category", MAPPING_RESPONSE_SCHEMA["properties"])


class TestPromptCatalog(unittest.TestCase):
    def test_prompt_includes_category_catalog(self) -> None:
        prompt = build_mapping_user_prompt(
            work_id="w",
            work_title="W",
            source_book_name="W",
            section_id="s",
            section_title="S",
            source_path="p.md",
            source_anchor=None,
            allowed_degrees=["library", "level1"],
            catalog_excerpt_items=[],
            unit_text="text",
            category_catalog_items={"level1": [{"id": "symbols", "title": "Symbols", "description": ""}]},
        )
        self.assertIn("suggested_category", prompt)
        self.assertIn('"symbols"', prompt)

    def test_prompt_works_without_catalog(self) -> None:
        prompt = build_mapping_user_prompt(
            work_id="w",
            work_title="W",
            source_book_name="W",
            section_id="s",
            section_title="S",
            source_path="p.md",
            source_anchor=None,
            allowed_degrees=["library"],
            catalog_excerpt_items=[],
            unit_text="text",
        )
        self.assertIn("Allowed categories per degree", prompt)


class TestChooseCandidateCategory(unittest.TestCase):
    def test_valid_provider_choice_wins(self) -> None:
        category, source = choose_candidate_category(
            _dataset(), ["fixture-sample-topic"], provider_category="symbols"
        )
        self.assertEqual(category, "symbols")
        self.assertEqual(source, "provider")

    def test_unknown_provider_category_is_rejected(self) -> None:
        category, source = choose_candidate_category(
            _dataset(), ["fixture-sample-topic"], provider_category="invented"
        )
        self.assertEqual(category, "foundations")
        self.assertEqual(source, "related_match")

    def test_no_provider_no_matches_falls_back_to_first_key(self) -> None:
        category, source = choose_candidate_category(_dataset(), [])
        self.assertEqual(category, "foundations")
        self.assertEqual(source, "first_category_fallback")


class TestMajorityVote(unittest.TestCase):
    def test_majority_wins(self) -> None:
        self.assertEqual(pick_majority_string(["a", "b", "a"]), "a")

    def test_tie_breaks_by_first_occurrence(self) -> None:
        self.assertEqual(pick_majority_string(["b", "a", "a", "b"]), "b")

    def test_empty_and_none_are_ignored(self) -> None:
        self.assertIsNone(pick_majority_string([None, "", "  "]))

    def test_combine_results_votes_category(self) -> None:
        combined = combine_mapping_results(
            [
                {"suggested_category": "symbols", "suggested_category_reason": "emblems"},
                {"suggested_category": "symbols"},
                {"suggested_category": "gate"},
            ]
        )
        self.assertEqual(combined["suggested_category"], "symbols")
        self.assertEqual(combined["suggested_category_reason"], "emblems")


class TestCandidateRecord(unittest.TestCase):
    def test_companion_candidate_records_category_source(self) -> None:
        candidate = build_companion_candidate(
            route={"work_id": "w", "work_title": "W"},
            section_title="Some Concept",
            section_id="section-0001",
            chapter_slug="w-chapter-1",
            source_note="W | Some Concept | x | section 1",
            combined_result={
                "suggested_category": "symbols",
                "suggested_category_reason": "Discusses emblems.",
            },
            medium_matches=[],
            base_datasets={"level1": _dataset()},
            discovery={
                "candidate_degree": "level1",
                "decision": "companion",
                "normalized_title": "Some Concept",
            },
        )
        self.assertEqual(candidate["suggested_category"], "symbols")
        self.assertEqual(candidate["category_source"], "provider")
        self.assertEqual(candidate["category_reason"], "Discusses emblems.")
        self.assertEqual(candidate["draft_seed"]["category"], "symbols")


if __name__ == "__main__":
    unittest.main()
