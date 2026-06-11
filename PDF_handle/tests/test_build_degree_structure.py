"""The structure builder: hub per category, orphans adopted, idempotent."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.cli.build_degree_structure import (
    apply_structure_plan,
    build_hub_entry,
    hub_slug,
    plan_degree_structure,
)
from PDF_handle.prod.cli.validate_runtime import _check_provenance
from PDF_handle.prod.schema.data import normalize_degree_data, validate_degree_references

RUNTIME_FIXTURE_LEVEL1 = REPO_ROOT / "data" / "fixtures" / "runtime_site_root" / "data" / "level1.json"


def _dataset() -> dict:
    raw = json.loads(RUNTIME_FIXTURE_LEVEL1.read_text(encoding="utf-8"))
    # Second category so the plan has more than one hub to manage.
    raw["categories"]["symbols"] = {"id": "symbols", "title": "Symbols", "symbol": "*"}
    # An orphan topic in the second category.
    raw["entries"].append(
        {
            "title": "The Trowel",
            "slug": "the-trowel",
            "type": "topic",
            "degree": "level1",
            "category": "symbols",
            "parent_topic": None,
            "related_topics": [],
            "short_summary": "Tool entry.",
            "source_notes": ["note"],
            "status": "draft",
        }
    )
    return normalize_degree_data(raw, "level1")


class TestPlan(unittest.TestCase):
    def test_plan_creates_one_hub_per_category(self) -> None:
        plan = plan_degree_structure(_dataset(), degree="level1", hub_status="published")
        created = {hub["slug"] for hub in plan["hubs_to_create"]}
        self.assertEqual(created, {"level1-hub-foundations", "level1-hub-symbols"})

    def test_orphan_topics_adopt_category_hub(self) -> None:
        plan = plan_degree_structure(_dataset(), degree="level1", hub_status="published")
        assignments = {item["slug"]: item["to"] for item in plan["parent_topic_assignments"]}
        self.assertEqual(assignments["the-trowel"], "level1-hub-symbols")
        # fixture-degree-gate is itself type=hub — hubs stay top-level.
        self.assertNotIn("fixture-degree-gate", assignments)

    def test_existing_parent_topic_untouched(self) -> None:
        plan = plan_degree_structure(_dataset(), degree="level1", hub_status="published")
        assigned = {item["slug"] for item in plan["parent_topic_assignments"]}
        # fixture-sample-topic already has parent_topic=fixture-degree-gate
        self.assertNotIn("fixture-sample-topic", assigned)

    def test_hub_companion_lists_are_sorted_children(self) -> None:
        plan = plan_degree_structure(_dataset(), degree="level1", hub_status="published")
        updates = {item["slug"]: item["companion"] for item in plan["hub_companion_updates"]}
        self.assertEqual(updates["level1-hub-symbols"], ["the-trowel"])
        # foundations entries keep their pre-existing hierarchy under
        # fixture-degree-gate, so the new foundations hub has no children.
        self.assertNotIn("level1-hub-foundations", updates)


class TestApply(unittest.TestCase):
    def _structured(self) -> dict:
        dataset = _dataset()
        plan = plan_degree_structure(dataset, degree="level1", hub_status="published")
        return apply_structure_plan(dataset, plan)

    def test_second_run_is_noop(self) -> None:
        dataset = self._structured()
        second_plan = plan_degree_structure(dataset, degree="level1", hub_status="published")
        self.assertTrue(second_plan["noop"], second_plan)

    def test_applied_dataset_passes_reference_validation(self) -> None:
        dataset = self._structured()
        report = validate_degree_references({"level1": dataset})
        self.assertEqual(report["errors"], [])

    def test_hub_entries_pass_provenance_gate(self) -> None:
        dataset = self._structured()
        errors, warnings = _check_provenance("level1", dataset)
        hub_problems = [msg for msg in errors + warnings if "hub" in msg]
        self.assertEqual(hub_problems, [])

    def test_hub_entry_shape(self) -> None:
        hub = build_hub_entry(
            degree="level2",
            category_id="middle_chamber",
            category={"title": "Middle Chamber", "description": "The winding stairs."},
            status="published",
        )
        self.assertEqual(hub["slug"], hub_slug("level2", "middle_chamber"))
        self.assertEqual(hub["type"], "hub")
        self.assertEqual(hub["category"], "middle_chamber")
        self.assertEqual(hub["short_summary"], "The winding stairs.")


if __name__ == "__main__":
    unittest.main()
