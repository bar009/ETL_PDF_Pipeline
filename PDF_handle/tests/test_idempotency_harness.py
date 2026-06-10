"""Idempotency harness for the stage→apply path (systemic plan WS6).

Same input, run twice, must give the same answer. These invariants are pinned
separately so a regression names exactly what broke:

- normalization is idempotent (normalize∘serialize∘normalize == normalize)
- the whole pipeline function is deterministic across independent runs
- re-applying the same staged operations introduces no duplicates
- slugs and entry count never change on re-apply
- the merged result is byte-stable

``test_merge_idempotency.py`` pins the patch-layer semantics (marker blocks,
regeneration, cross-work safety); this file pins the fixture-driven end state.
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

from PDF_handle.prod.schema.data import (
    normalize_degree_data,
    serialize_degree_data,
)
from PDF_handle.prod.schema.patches import apply_degree_patches

RUNTIME_LEVEL1 = REPO_ROOT / "data" / "fixtures" / "runtime_site_root" / "data" / "level1.json"
STAGING_PATCH = REPO_ROOT / "data" / "fixtures" / "staging_minimal" / "level1.patch.json"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _stable_dump(degree_data: dict) -> str:
    return json.dumps(serialize_degree_data(degree_data), ensure_ascii=False, sort_keys=True)


def _merged_once() -> dict:
    degree = normalize_degree_data(_read(RUNTIME_LEVEL1), "level1")
    return apply_degree_patches(degree, _read(STAGING_PATCH)["operations"])


class TestNormalizationIdempotency(unittest.TestCase):
    def test_normalize_twice_equals_normalize_once(self) -> None:
        once = normalize_degree_data(_read(RUNTIME_LEVEL1), "level1")
        twice = normalize_degree_data(serialize_degree_data(once), "level1")
        self.assertEqual(_stable_dump(once), _stable_dump(twice))


class TestApplyIdempotency(unittest.TestCase):
    def test_independent_runs_are_deterministic(self) -> None:
        self.assertEqual(_stable_dump(_merged_once()), _stable_dump(_merged_once()))

    def test_reapply_introduces_no_duplicates(self) -> None:
        # The marked block legitimately mentions the marker more than once
        # (open/close comments), so the invariant is: the count after a
        # re-apply equals the count after a single apply.
        operations = _read(STAGING_PATCH)["operations"]
        marker = operations[0]["marker_id"]
        slug = operations[0]["slug"]

        once = _merged_once()
        count_once = once["entryBySlug"][slug]["full_summary"].count(marker)
        self.assertGreater(count_once, 0, "single apply did not write the marked block")

        twice = apply_degree_patches(once, operations)
        count_twice = twice["entryBySlug"][slug]["full_summary"].count(marker)
        self.assertEqual(count_twice, count_once, "re-apply duplicated the provenance-marked block")

    def test_reapply_preserves_slugs_and_count(self) -> None:
        operations = _read(STAGING_PATCH)["operations"]
        first = _merged_once()
        first_slugs = [entry["slug"] for entry in first["entries"]]

        second = apply_degree_patches(first, operations)
        second_slugs = [entry["slug"] for entry in second["entries"]]

        self.assertEqual(first_slugs, second_slugs, "re-apply changed slugs or entry order")
        self.assertEqual(len(second_slugs), len(set(second_slugs)), "re-apply created duplicate slugs")

    def test_reapply_is_byte_stable(self) -> None:
        operations = _read(STAGING_PATCH)["operations"]
        first = _merged_once()
        first_dump = _stable_dump(first)
        second_dump = _stable_dump(apply_degree_patches(first, operations))
        self.assertEqual(first_dump, second_dump)


if __name__ == "__main__":
    unittest.main()
