"""The review workflow boundary (WS9): suggestion never equals canon."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.schema.patches import build_degree_patch_operation
from PDF_handle.prod.schema.review_states import (
    ALLOWED_TRANSITIONS,
    REVIEW_STATES,
    ReviewBoundaryError,
    approve_operator_selection,
    assert_operations_approved,
    transition,
    validate_transition,
)

STAGING_PATCH = REPO_ROOT / "data" / "fixtures" / "staging_minimal" / "level1.patch.json"


def _operation(state: str | None) -> dict:
    op = {"slug": "some-entry", "marker_id": "PDF_STAGE5:w:s"}
    if state is not None:
        op["review_state"] = state
    return op


class TestTransitionMatrix(unittest.TestCase):
    def test_the_happy_path(self) -> None:
        op = _operation("suggested")
        for target in ("reviewed", "approved", "published"):
            transition(op, target)
        self.assertEqual(op["review_state"], "published")

    def test_every_forbidden_transition_raises(self) -> None:
        for current in REVIEW_STATES:
            for target in REVIEW_STATES:
                if target in ALLOWED_TRANSITIONS[current]:
                    continue
                with self.subTest(current=current, target=target):
                    with self.assertRaises(ReviewBoundaryError):
                        validate_transition(current, target)

    def test_terminal_states_have_no_exits(self) -> None:
        self.assertEqual(ALLOWED_TRANSITIONS["published"], frozenset())
        self.assertEqual(ALLOWED_TRANSITIONS["rejected"], frozenset())

    def test_unknown_states_are_rejected(self) -> None:
        with self.assertRaises(ReviewBoundaryError):
            validate_transition("suggested", "shipped")
        with self.assertRaises(ReviewBoundaryError):
            validate_transition("draft", "approved")


class TestStagingToRuntimeDoor(unittest.TestCase):
    def test_approved_operations_pass(self) -> None:
        self.assertEqual(assert_operations_approved([_operation("approved")]), [])

    def test_every_non_approved_state_is_blocked(self) -> None:
        for state in ("suggested", "reviewed", "rejected", "published", "nonsense"):
            with self.subTest(state=state):
                with self.assertRaises(ReviewBoundaryError):
                    assert_operations_approved([_operation(state)])

    def test_legacy_operations_need_the_explicit_flag(self) -> None:
        legacy = _operation(None)
        with self.assertRaises(ReviewBoundaryError):
            assert_operations_approved([legacy])
        warnings = assert_operations_approved([legacy], allow_unreviewed_legacy=True)
        self.assertEqual(len(warnings), 1)
        self.assertIn("legacy", warnings[0])

    def test_one_blocked_operation_blocks_the_batch(self) -> None:
        batch = [_operation("approved"), _operation("suggested")]
        with self.assertRaises(ReviewBoundaryError):
            assert_operations_approved(batch)


class TestOperatorSelectionApproval(unittest.TestCase):
    """Step 6's approval selectors become explicit review-state transitions."""

    def test_suggested_items_become_approved(self) -> None:
        item = _operation("suggested")
        warnings = approve_operator_selection([item])
        self.assertEqual(warnings, [])
        self.assertEqual(item["review_state"], "approved")
        self.assertEqual(assert_operations_approved([item]), [])

    def test_reviewed_items_become_approved(self) -> None:
        item = _operation("reviewed")
        approve_operator_selection([item])
        self.assertEqual(item["review_state"], "approved")

    def test_approved_items_are_untouched(self) -> None:
        item = _operation("approved")
        self.assertEqual(approve_operator_selection([item]), [])
        self.assertEqual(item["review_state"], "approved")

    def test_rejected_and_published_cannot_be_selected(self) -> None:
        for state in ("rejected", "published"):
            with self.subTest(state=state):
                with self.assertRaises(ReviewBoundaryError):
                    approve_operator_selection([_operation(state)])

    def test_legacy_items_require_the_explicit_flag(self) -> None:
        legacy = _operation(None)
        with self.assertRaises(ReviewBoundaryError):
            approve_operator_selection([legacy])
        warnings = approve_operator_selection([legacy], allow_unreviewed_legacy=True)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(legacy["review_state"], "approved")

    def test_companion_candidates_are_labeled_by_candidate_slug(self) -> None:
        companion = {"candidate_slug": "level1-candidate-x", "review_state": "rejected"}
        with self.assertRaises(ReviewBoundaryError) as ctx:
            approve_operator_selection([companion])
        self.assertIn("level1-candidate-x", str(ctx.exception))


class TestStateStamping(unittest.TestCase):
    def test_new_staged_operations_are_suggestions(self) -> None:
        op = build_degree_patch_operation(
            target_slug="t",
            target_degree="level1",
            work_id="w",
            work_title="W",
            section_id="s",
            section_title="S",
            chapter_slug="c",
            chapter_degree="library",
            source_notes=["note"],
            section_summary="Content",
            practical_elements=[],
            symbolic_meaning="",
            candidate_lesson="",
            tradition_notes=[],
            caution_notes=[],
        )
        self.assertEqual(op["review_state"], "suggested")

    def test_the_committed_staging_fixture_is_approved(self) -> None:
        payload = json.loads(STAGING_PATCH.read_text(encoding="utf-8"))
        for op in payload["operations"]:
            self.assertEqual(op["review_state"], "approved")

    def test_new_companion_candidates_are_suggestions(self) -> None:
        from PDF_handle.prod.schema.data import normalize_degree_data
        from PDF_handle.prod.steps.stage import build_companion_candidate

        raw = json.loads(
            (REPO_ROOT / "data" / "fixtures" / "runtime_site_root" / "data" / "level1.json")
            .read_text(encoding="utf-8")
        )
        candidate = build_companion_candidate(
            route={"work_id": "w", "work_title": "W"},
            section_title="Some Concept",
            section_id="section-0001",
            chapter_slug="w-chapter-1",
            source_note="W | Some Concept | x | section 1",
            combined_result={},
            medium_matches=[],
            base_datasets={"level1": normalize_degree_data(raw, "level1")},
            discovery={
                "candidate_degree": "level1",
                "decision": "companion",
                "normalized_title": "Some Concept",
            },
        )
        self.assertEqual(candidate["review_state"], "suggested")


if __name__ == "__main__":
    unittest.main()
