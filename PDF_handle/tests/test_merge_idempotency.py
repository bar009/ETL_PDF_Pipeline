"""Regression guards for the deterministic degree-patch merge contract.

These lock the behavior of schema.patches / steps.apply_support so that future
edits to the merge layer cannot silently regress idempotency or, worse, let one
work's re-merge clobber another work's contribution to a shared entry.

Three guarantees are pinned:

1. Re-applying the *same* operation is idempotent  - the provenance-marked
   ``full_summary`` block appears exactly once, and unioned fields do not grow.
2. Re-applying a *regenerated* operation (same work_id/section_id, new body)
   replaces the old marked block - stale ``full_summary`` content is purged.
3. A per-work re-merge must NOT delete a *different* work's contribution to a
   shared entry. This invariant is the reason a naive "clear the scalar fields
   on purge" fix would be incorrect: those fields are shared across works and
   carry no per-work provenance, so blind clearing would destroy sibling data.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.schema.data import refresh_degree_indexes
from PDF_handle.prod.schema.patches import (
    APPEND_MARKER_PREFIX,
    apply_degree_patches,
    build_degree_patch_operation,
)


def _degree_with_target() -> dict:
    """Minimal level dataset carrying a single empty target entry."""
    entry = {
        "title": "Target Entry",
        "slug": "target-entry",
        "aliases": [],
        "full_summary": "",
        "practical_elements": [],
        "symbolic_meaning": "",
        "candidate_lesson": "",
        "tradition_notes": [],
        "caution_notes": [],
        "source_notes": [],
        "knowledge_links": [],
    }
    return refresh_degree_indexes({"entries": [entry]})


def _op(*, work_id: str, section_id: str, work_title: str, section_summary: str, symbolic: str = "") -> dict:
    return build_degree_patch_operation(
        target_slug="target-entry",
        target_degree="level2",
        work_id=work_id,
        work_title=work_title,
        section_id=section_id,
        section_title="Section",
        chapter_slug="some-chapter",
        chapter_degree="library",
        source_notes=[f"{work_title} | Section | /tmp/{work_title}.md | section 1"],
        section_summary_he=section_summary,
        practical_elements_he=[],
        symbolic_meaning_he=symbolic,
        candidate_lesson_he="",
        tradition_notes_he=[],
        caution_notes_he=[],
    )


def _entry(degree: dict) -> dict:
    return degree["entryBySlug"]["target-entry"]


class MergeIdempotencyTest(unittest.TestCase):
    def test_same_operation_applied_twice_is_idempotent(self):
        degree = _degree_with_target()
        op = _op(work_id="wid", section_id="s1", work_title="BookA", section_summary="ALPHA body")

        apply_degree_patches(degree, [op])
        apply_degree_patches(degree, [op])

        entry = _entry(degree)
        marker_open = f"<!-- {APPEND_MARKER_PREFIX}:wid:s1 -->"
        # The marked block survives exactly once across a redundant re-apply.
        self.assertEqual(entry["full_summary"].count(marker_open), 1)
        self.assertIn("ALPHA body", entry["full_summary"])
        # Unioned provenance field does not accumulate duplicates.
        self.assertEqual(len(entry["source_notes"]), 1)

    def test_regenerated_body_replaces_stale_marked_block(self):
        degree = _degree_with_target()
        first = _op(work_id="wid", section_id="s1", work_title="BookA", section_summary="ALPHA body")
        regenerated = _op(work_id="wid", section_id="s1", work_title="BookA", section_summary="BRAVO body")

        apply_degree_patches(degree, [first])
        apply_degree_patches(degree, [regenerated])

        entry = _entry(degree)
        # Stale full_summary content is purged on re-merge; only the new body remains.
        self.assertIn("BRAVO body", entry["full_summary"])
        self.assertNotIn("ALPHA body", entry["full_summary"])
        self.assertEqual(entry["full_summary"].count(f"<!-- {APPEND_MARKER_PREFIX}:wid:s1 -->"), 1)

    def test_remerge_of_one_work_preserves_other_works_shared_field(self):
        # The safety invariant: works A and B both enrich the same entry's
        # symbolic_meaning. Re-merging A must not erase B's contribution. A naive
        # "clear scalar fields for A on purge" fix would violate this.
        degree = _degree_with_target()
        op_a = _op(work_id="widA", section_id="a1", work_title="BookA", section_summary="A body", symbolic="insight from A")
        op_b = _op(work_id="widB", section_id="b1", work_title="BookB", section_summary="B body", symbolic="insight from B")

        apply_degree_patches(degree, [op_a])
        apply_degree_patches(degree, [op_b])
        # Re-merge only work A with regenerated content.
        op_a2 = _op(work_id="widA", section_id="a1", work_title="BookA", section_summary="A body v2", symbolic="insight from A v2")
        apply_degree_patches(degree, [op_a2])

        entry = _entry(degree)
        # Work B's shared-field contribution must survive A's re-merge.
        self.assertIn("insight from B", entry["symbolic_meaning"])
        # Work A's new full_summary body landed; its stale one was purged.
        self.assertIn("A body v2", entry["full_summary"])
        self.assertNotIn("A body\n", entry["full_summary"])
        # Work B's full_summary block is untouched by A's per-work purge.
        self.assertIn("B body", entry["full_summary"])
        self.assertEqual(entry["full_summary"].count(f"<!-- {APPEND_MARKER_PREFIX}:widB:b1 -->"), 1)


if __name__ == "__main__":
    unittest.main()
