"""The repo-committed degree category taxonomy and its seeder integration."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.cli.seed_clean_rerun_root import build_projected_canonical_payloads

TEMPLATE_PATH = REPO_ROOT / "PDF_handle" / "prod" / "templates" / "degree_categories.v1.json"
RUNTIME_FIXTURE = REPO_ROOT / "data" / "fixtures" / "runtime_site_root"

CATEGORY_ID_RE = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")
CANONICAL_LEVEL1_IDS = {
    "gate",
    "preparation",
    "ritual_flow",
    "lodge_structure",
    "degree_board",
    "tools_and_signs",
    "obligation_and_law",
    "inner_work",
    "glossary_and_review",
}


def _load_template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


class TestTemplateFile(unittest.TestCase):
    def test_template_covers_all_three_degrees(self) -> None:
        template = _load_template()
        self.assertEqual(set(template.keys()), {"level1", "level2", "level3"})

    def test_category_ids_are_well_formed(self) -> None:
        template = _load_template()
        for degree, categories in template.items():
            self.assertGreaterEqual(len(categories), 2, degree)
            for category_id, category in categories.items():
                with self.subTest(degree=degree, category=category_id):
                    self.assertRegex(category_id, CATEGORY_ID_RE)
                    self.assertEqual(category["id"], category_id)
                    self.assertTrue(str(category.get("title") or "").strip())
                    self.assertTrue(str(category.get("symbol") or "").strip())
                    self.assertIsNone(category.get("parent_category"))

    def test_level1_preserves_the_canonical_nine(self) -> None:
        template = _load_template()
        self.assertEqual(set(template["level1"].keys()), CANONICAL_LEVEL1_IDS)

    def test_level2_and_level3_have_nine_categories(self) -> None:
        template = _load_template()
        self.assertEqual(len(template["level2"]), 9)
        self.assertEqual(len(template["level3"]), 9)


class TestSeederIntegration(unittest.TestCase):
    def test_categories_only_seed_uses_template_categories(self) -> None:
        template = _load_template()
        payloads = build_projected_canonical_payloads(
            seed_root=RUNTIME_FIXTURE,
            seed_mode="categories-only",
            canonical_language="en",
            categories_template=template,
        )
        # The fixture only carries level1.json; its categories must be replaced.
        self.assertEqual(set(payloads["level1"]["categories"].keys()), CANONICAL_LEVEL1_IDS)
        self.assertEqual(payloads["level1"]["entries"], [])

    def test_degrees_missing_from_template_keep_seed_categories(self) -> None:
        payloads = build_projected_canonical_payloads(
            seed_root=RUNTIME_FIXTURE,
            seed_mode="categories-only",
            canonical_language="en",
            categories_template={"level2": {"x": {"id": "x", "title": "X", "symbol": "*"}}},
        )
        self.assertIn("foundations", payloads["level1"]["categories"])

    def test_full_seed_mode_rejects_template(self) -> None:
        with self.assertRaises(ValueError):
            build_projected_canonical_payloads(
                seed_root=RUNTIME_FIXTURE,
                seed_mode="full",
                categories_template=_load_template(),
            )


if __name__ == "__main__":
    unittest.main()
