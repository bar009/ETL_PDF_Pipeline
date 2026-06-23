from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import read_json, write_json
from PDF_handle.prod.schema import normalize_degree_data, validate_degree_references
from PDF_handle.prod.steps import decompose

PARENT_SLUG = "fixture-over-merged"
THRESHOLD = 40
ITEM_COUNT = 45


def _fake_classify(title, items, *, model, api_key):
    """Deterministic, offline: contiguous groups of 20 items each."""
    groups = [{"title": f"sub topic {i + 1}"} for i in range((len(items) + 19) // 20)]
    assignments = [i // 20 for i in range(len(items))]
    return groups, assignments


def _write_degree(site_root: Path) -> Path:
    data_dir = site_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "level1.json"
    write_json(
        path,
        {
            "meta": {"degree": "level1", "title": "t", "updated_at": None},
            "categories": {"foundations": {"title": "יסודות", "symbol": "△"}},
            "entries": [
                {
                    "title": "ערך מנופח",
                    "slug": PARENT_SLUG,
                    "type": "topic",
                    "degree": "level1",
                    "applies_to_degrees": ["level1"],
                    "category": "foundations",
                    "parent_topic": None,
                    "related_topics": {"prior": [], "companion": [], "deeper": []},
                    "short_summary": "תקציר",
                    "full_summary": "גוף",
                    "practical_elements": [f"פריט {i}" for i in range(ITEM_COUNT)],
                    "symbolic_meaning": "משמעות סמלית",
                    "candidate_lesson": "לקח",
                    "tradition_scope": "variant",
                    "status": "draft",
                }
            ],
        },
    )
    return path


class DecomposeStepTest(unittest.TestCase):
    def test_over_merged_entry_becomes_hub_with_children(self):
        with tempfile.TemporaryDirectory() as td:
            site_root = Path(td) / "site"
            path = _write_degree(site_root)

            manifest = decompose.run(
                site_root=site_root, threshold=THRESHOLD, classify=_fake_classify, quiet=True
            )
            self.assertEqual(manifest["per_degree"]["level1"]["hubs_created"], 1)

            data = read_json(path)
            by_slug = {e["slug"]: e for e in data["entries"]}
            parent = by_slug[PARENT_SLUG]

            # Parent is now a hub with no body wall.
            self.assertEqual(parent["type"], "hub")
            self.assertEqual(parent["practical_elements"], [])
            self.assertEqual(parent["symbolic_meaning"], "")

            children = [e for e in data["entries"] if e.get("parent_topic") == PARENT_SLUG]
            self.assertGreaterEqual(len(children), 3)

            # No items lost; every child is within threshold.
            moved = sum(len(e.get("practical_elements") or []) for e in children)
            self.assertEqual(moved, ITEM_COUNT)
            for child in children:
                self.assertLessEqual(len(child.get("practical_elements") or []), THRESHOLD)

            # Concepts child carries the prose.
            concepts = by_slug.get(f"{PARENT_SLUG}-concepts")
            self.assertIsNotNone(concepts)
            self.assertEqual(concepts["symbolic_meaning"], "משמעות סמלית")

            # Children are wired into the hub and reference it back.
            child_slugs = {c["slug"] for c in children}
            self.assertTrue(child_slugs.issubset(set(parent["related_topics"]["deeper"])))

            # Schema-normalizes and references resolve.
            normalized = normalize_degree_data(data, "level1")
            refs = validate_degree_references({"level1": normalized})
            self.assertEqual(refs.get("errors", []), [])

    def test_idempotent_second_run_no_change(self):
        with tempfile.TemporaryDirectory() as td:
            site_root = Path(td) / "site"
            path = _write_degree(site_root)
            decompose.run(site_root=site_root, threshold=THRESHOLD, classify=_fake_classify, quiet=True)
            after_first = path.read_bytes()

            manifest = decompose.run(
                site_root=site_root, threshold=THRESHOLD, classify=_fake_classify, quiet=True
            )
            self.assertEqual(manifest["per_degree"]["level1"]["hubs_created"], 0)
            self.assertEqual(path.read_bytes(), after_first)


if __name__ == "__main__":
    unittest.main()
