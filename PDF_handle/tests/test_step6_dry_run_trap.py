"""Step 6 must never let a failed merge look like a successful one.

Covers the two traps found in the 2026-06-11 Color-Symbolism pilot:

1. Selected degree operations linked to staged library chapters, but
   --merge-library was not passed — the merge validated late with cryptic
   missing-reference errors instead of failing early with the actionable flag.
2. In dry-run mode (no --apply-live) apply exited 0 even when validation
   failed, so the operator believed the enriched content had landed.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.steps.apply import assert_selected_ops_library_links_mergeable


def _library(slugs: list[str]) -> dict:
    return {"entries": [{"slug": slug} for slug in slugs]}


def _op(slug: str, library_links: list[str]) -> dict:
    return {
        "slug": slug,
        "changes": {
            "knowledge_links": [{"degree": "library", "slug": target} for target in library_links]
        },
    }


class TestLibraryLinkGuard(unittest.TestCase):
    def test_links_to_merged_library_pass(self) -> None:
        assert_selected_ops_library_links_mergeable(
            {"level2": [_op("topic-a", ["chapter-1"])]},
            merged_library=_library(["chapter-1"]),
            library_patch={"entries": [{"slug": "chapter-1"}]},
            merge_library_selected=True,
        )

    def test_links_to_staged_but_unmerged_library_are_blocked(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            assert_selected_ops_library_links_mergeable(
                {"level2": [_op("topic-a", ["chapter-1"])]},
                merged_library=_library([]),
                library_patch={"entries": [{"slug": "chapter-1"}]},
                merge_library_selected=False,
            )
        message = str(ctx.exception)
        self.assertIn("--merge-library", message)
        self.assertIn("level2:topic-a -> library:chapter-1", message)

    def test_links_to_slugs_unknown_to_staging_are_left_for_validation(self) -> None:
        # A dangling link that staging never produced is a data problem, not a
        # missing flag — the late validation gate owns that failure mode.
        assert_selected_ops_library_links_mergeable(
            {"level2": [_op("topic-a", ["never-staged"])]},
            merged_library=_library([]),
            library_patch={"entries": [{"slug": "chapter-1"}]},
            merge_library_selected=False,
        )

    def test_non_library_links_are_ignored(self) -> None:
        op = {
            "slug": "topic-a",
            "changes": {"knowledge_links": [{"degree": "level1", "slug": "elsewhere"}]},
        }
        assert_selected_ops_library_links_mergeable(
            {"level2": [op]},
            merged_library=_library([]),
            library_patch={"entries": [{"slug": "elsewhere"}]},
            merge_library_selected=False,
        )

    def test_operations_without_changes_are_ignored(self) -> None:
        assert_selected_ops_library_links_mergeable(
            {"level1": [{"slug": "bare-op"}], "level2": [], "level3": []},
            merged_library=_library([]),
            library_patch={"entries": []},
            merge_library_selected=False,
        )


class TestDryRunExitContract(unittest.TestCase):
    def test_main_raises_on_failed_validation_in_dry_run(self) -> None:
        # Lock the contract at the source level: the only return path of
        # main() must be guarded by a validation_ok check that raises.
        source = (REPO_ROOT / "PDF_handle" / "prod" / "steps" / "apply.py").read_text(encoding="utf-8")
        tail = source[source.index("[done] validation_ok="):]
        self.assertIn('if not validation_report["ok"]:', tail)
        self.assertIn("raise SystemExit", tail)


if __name__ == "__main__":
    unittest.main()
