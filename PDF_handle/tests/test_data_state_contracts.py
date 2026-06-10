"""Contract checks for the committed data-state fixtures.

Phase 2 of ``docs/STRUCTURE_ROADMAP.md`` requires that the distinct ETL data
states stay distinct, and that a staged artifact is never accepted where site
runtime data is expected. The committed fixtures under ``data/fixtures/`` give
each state a smallest useful example:

- ``data/fixtures/runtime_site_root/`` — a minimal valid *runtime* site root
  (what ``--site-root`` must point at)
- ``data/fixtures/staging_minimal/`` — a minimal *staging* artifact
  (Step 5 review material; never site runtime)

These tests pin the contract between those fixtures and the prod code that
consumes each state.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.core.site_roots import _looks_like_site_root
from PDF_handle.prod.schema.data import (
    custom_validate_degree_data,
    normalize_degree_data,
)
from PDF_handle.prod.schema.patches import apply_degree_patches

FIXTURES = REPO_ROOT / "data" / "fixtures"
RUNTIME_SITE_ROOT = FIXTURES / "runtime_site_root"
STAGING_DIR = FIXTURES / "staging_minimal"
SCHEMA_CONTRACT = REPO_ROOT / "data" / "schemas" / "content.schema.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestRuntimeSiteRootFixture(unittest.TestCase):
    def test_runtime_fixture_is_a_valid_site_root(self) -> None:
        self.assertTrue(
            _looks_like_site_root(RUNTIME_SITE_ROOT),
            f"{RUNTIME_SITE_ROOT} must satisfy the site-root contract "
            "(data/ dir containing content.schema.json)",
        )

    def test_staging_fixture_is_not_a_site_root(self) -> None:
        # The core Phase 2 invariant: staging review material must never be
        # accepted where site runtime data is expected.
        self.assertFalse(
            _looks_like_site_root(STAGING_DIR),
            "A staging directory must not satisfy the site-root contract",
        )

    def test_degree_file_normalizes_and_validates(self) -> None:
        raw = _read_json(RUNTIME_SITE_ROOT / "data" / "level1.json")
        normalized = normalize_degree_data(raw, "level1")
        result = custom_validate_degree_data(normalized)
        self.assertTrue(result["ok"], f"Fixture level1.json invalid: {result['errors']}")

    def test_degree_file_slugs_are_unique(self) -> None:
        raw = _read_json(RUNTIME_SITE_ROOT / "data" / "level1.json")
        slugs = [entry["slug"] for entry in raw["entries"]]
        self.assertEqual(len(slugs), len(set(slugs)), f"Duplicate slugs in fixture: {slugs}")

    def test_internal_references_resolve(self) -> None:
        raw = _read_json(RUNTIME_SITE_ROOT / "data" / "level1.json")
        slugs = {entry["slug"] for entry in raw["entries"]}
        for entry in raw["entries"]:
            parent = entry.get("parent_topic")
            if parent is not None:
                self.assertIn(parent, slugs, f"{entry['slug']}.parent_topic dangles: {parent}")
            related = entry.get("related_topics")
            related_slugs = (
                [s for group in related.values() for s in group]
                if isinstance(related, dict)
                else list(related or [])
            )
            for target in related_slugs:
                self.assertIn(target, slugs, f"{entry['slug']} relates to missing: {target}")


class TestSchemaContractCopiesAgree(unittest.TestCase):
    def test_fixture_schema_matches_contract_schema(self) -> None:
        # data/schemas/content.schema.json is the contract home; the runtime
        # fixture carries its own copy because a site root must be
        # self-contained. The two must never drift.
        contract = _read_json(SCHEMA_CONTRACT)
        fixture_copy = _read_json(RUNTIME_SITE_ROOT / "data" / "content.schema.json")
        self.assertEqual(
            fixture_copy,
            contract,
            "data/fixtures/runtime_site_root/data/content.schema.json has drifted from "
            "data/schemas/content.schema.json — update both together",
        )


class TestStagingPatchFixture(unittest.TestCase):
    def test_patch_file_has_staging_shape(self) -> None:
        payload = _read_json(STAGING_DIR / "level1.patch.json")
        self.assertEqual(payload["degree"], "level1")
        self.assertIsInstance(payload["operations"], list)
        self.assertGreater(len(payload["operations"]), 0)
        for op in payload["operations"]:
            for key in ("slug", "degree", "work_id", "section_id", "marker_id", "changes"):
                self.assertIn(key, op, f"staged operation missing {key}")

    def test_patch_applies_cleanly_to_runtime_fixture(self) -> None:
        # The smallest stage→apply path: the staged fixture must target the
        # runtime fixture and the merged result must still validate.
        raw = _read_json(RUNTIME_SITE_ROOT / "data" / "level1.json")
        degree_data = normalize_degree_data(raw, "level1")
        operations = _read_json(STAGING_DIR / "level1.patch.json")["operations"]

        merged = apply_degree_patches(degree_data, operations)

        target = merged["entryBySlug"][operations[0]["slug"]]
        self.assertIn(operations[0]["marker_id"], target["full_summary"])
        result = custom_validate_degree_data(merged)
        self.assertTrue(result["ok"], f"Merged fixture data invalid: {result['errors']}")


if __name__ == "__main__":
    unittest.main()
