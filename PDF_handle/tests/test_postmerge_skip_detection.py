from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.core.io import write_json
from PDF_handle.prod.core.site_data import build_site_data_paths
from PDF_handle.prod.impl.postmerge_runner import (
    assess_step5_state,
    assess_step6_state,
    live_data_contains_work,
)


def _make_site(td: Path) -> dict:
    """Build a minimal site root that satisfies build_site_data_paths()."""
    site_root = td / "site"
    data_dir = site_root / "data"
    data_dir.mkdir(parents=True)
    write_json(data_dir / "content.schema.json", {})
    return build_site_data_paths(site_root)


def _write_empty_levels(site_paths: dict, include_level3: bool = False) -> None:
    write_json(site_paths["library"], {"entries": []})
    write_json(site_paths["level1"], {"entries": []})
    write_json(site_paths["level2"], {"entries": []})
    if include_level3:
        write_json(site_paths["level3"], {"entries": []})


class LiveDataContainsWorkTest(unittest.TestCase):
    def test_library_work_id_match(self):
        with tempfile.TemporaryDirectory() as td:
            sp = _make_site(Path(td))
            write_json(sp["library"], {"entries": [{"slug": "x", "work_id": "wid"}]})
            write_json(sp["level1"], {"entries": []})
            write_json(sp["level2"], {"entries": []})
            self.assertTrue(live_data_contains_work(sp, "wid", "any-book"))

    def test_marker_in_level3_is_detected(self):
        # Regression: pre-fix, level3 was never iterated.
        with tempfile.TemporaryDirectory() as td:
            sp = _make_site(Path(td))
            _write_empty_levels(sp)
            write_json(
                sp["level3"],
                {
                    "entries": [
                        {
                            "slug": "deep",
                            "full_summary": "<!-- PDF_STAGE5:wid:s1 -->payload<!-- /PDF_STAGE5:wid:s1 -->",
                        }
                    ]
                },
            )
            self.assertTrue(live_data_contains_work(sp, "wid", "any-book"))

    def test_marker_in_level1(self):
        with tempfile.TemporaryDirectory() as td:
            sp = _make_site(Path(td))
            _write_empty_levels(sp)
            write_json(
                sp["level1"],
                {"entries": [{"slug": "e", "full_summary": "<!-- PDF_STAGE5:wid:s2 -->X<!-- /PDF_STAGE5:wid:s2 -->"}]},
            )
            self.assertTrue(live_data_contains_work(sp, "wid", "any-book"))

    def test_source_book_name_fallback_matches(self):
        # Regression: pre-fix used `work_id in note` and missed entries where
        # work_id != source_book_name.
        with tempfile.TemporaryDirectory() as td:
            sp = _make_site(Path(td))
            _write_empty_levels(sp)
            write_json(
                sp["level1"],
                {
                    "entries": [
                        {
                            "slug": "e",
                            "source_notes": ["Staged from consolidated markdown: /tmp/MyBook.md"],
                        }
                    ]
                },
            )
            # work_id and source_book_name deliberately differ.
            self.assertTrue(live_data_contains_work(sp, "completely-different-work-id", "MyBook"))

    def test_no_signals_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            sp = _make_site(Path(td))
            _write_empty_levels(sp)
            self.assertFalse(live_data_contains_work(sp, "wid", "book"))

    def test_level3_optional_does_not_crash(self):
        # level3.json doesn't have to exist; the iteration must guard with path.exists().
        with tempfile.TemporaryDirectory() as td:
            sp = _make_site(Path(td))
            write_json(sp["library"], {"entries": []})
            write_json(sp["level1"], {"entries": []})
            write_json(sp["level2"], {"entries": []})
            # level3.json deliberately absent.
            self.assertFalse(live_data_contains_work(sp, "wid", "book"))


def _write_minimal_merge_report(staging: Path, site_root: Path, *, extra: dict) -> None:
    base = {
        "apply_live": True,
        "site_root": str(site_root.resolve()),
        "selected_work_ids": ["wid"],
        "level1": {"selected_count": 0},
        "level2": {"selected_count": 0},
        "level3": {"selected_count": 0},
    }
    base.update(extra)
    write_json(staging / "step6_merge_report.json", base)
    write_json(staging / "step6_validation_report.json", {"ok": True})


class AssessStep6StateTest(unittest.TestCase):
    def test_no_reports_returns_apply(self):
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "staging"
            staging.mkdir()
            sp = _make_site(Path(td))
            _write_empty_levels(sp)
            d = assess_step6_state(staging, sp, "wid", "book")
            self.assertEqual(d["action"], "apply")

    def test_legacy_merge_report_skips(self):
        # New behavior: legacy reports (missing live_write_completed) skip when
        # the other gates pass.
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "staging"
            staging.mkdir()
            sp = _make_site(Path(td))
            write_json(sp["library"], {"entries": [{"slug": "x", "work_id": "wid"}]})
            write_json(sp["level1"], {"entries": []})
            write_json(sp["level2"], {"entries": []})
            _write_minimal_merge_report(staging, sp["site_root"], extra={})
            d = assess_step6_state(staging, sp, "wid", "book")
            self.assertEqual(d["action"], "skip")
            self.assertTrue(d.get("legacy_merge_report"))

    def test_modern_completed_skips(self):
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "staging"
            staging.mkdir()
            sp = _make_site(Path(td))
            write_json(sp["library"], {"entries": [{"slug": "x", "work_id": "wid"}]})
            write_json(sp["level1"], {"entries": []})
            write_json(sp["level2"], {"entries": []})
            _write_minimal_merge_report(
                staging, sp["site_root"], extra={"live_write_completed": True}
            )
            d = assess_step6_state(staging, sp, "wid", "book")
            self.assertEqual(d["action"], "skip")
            self.assertFalse(d.get("legacy_merge_report"))

    def test_modern_explicit_false_forces_apply(self):
        # live_write_completed=False is an explicit "apply failed mid-write" signal.
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "staging"
            staging.mkdir()
            sp = _make_site(Path(td))
            write_json(sp["library"], {"entries": [{"slug": "x", "work_id": "wid"}]})
            write_json(sp["level1"], {"entries": []})
            write_json(sp["level2"], {"entries": []})
            _write_minimal_merge_report(
                staging, sp["site_root"], extra={"live_write_completed": False}
            )
            d = assess_step6_state(staging, sp, "wid", "book")
            self.assertEqual(d["action"], "apply")

    def test_patches_diverged_forces_apply(self):
        # level_reports_are_fresh: 0 selected_count < 2 ops in patch → apply.
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "staging"
            staging.mkdir()
            sp = _make_site(Path(td))
            write_json(sp["library"], {"entries": [{"slug": "x", "work_id": "wid"}]})
            write_json(sp["level1"], {"entries": []})
            write_json(sp["level2"], {"entries": []})
            _write_minimal_merge_report(
                staging, sp["site_root"], extra={"live_write_completed": True}
            )
            write_json(
                staging / "level1.patch.json",
                {"operations": [{"work_id": "wid", "slug": "a"}, {"work_id": "wid", "slug": "b"}]},
            )
            d = assess_step6_state(staging, sp, "wid", "book")
            self.assertEqual(d["action"], "apply")

    def test_different_site_root_forces_apply(self):
        # merge_report.site_root != queried site_root → apply.
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "staging"
            staging.mkdir()
            sp = _make_site(Path(td))
            write_json(sp["library"], {"entries": [{"slug": "x", "work_id": "wid"}]})
            write_json(sp["level1"], {"entries": []})
            write_json(sp["level2"], {"entries": []})
            # merge_report claims it was applied to a different site root.
            other_root = Path(td) / "other-site"
            other_root.mkdir()
            _write_minimal_merge_report(
                staging, other_root, extra={"live_write_completed": True}
            )
            d = assess_step6_state(staging, sp, "wid", "book")
            self.assertEqual(d["action"], "apply")


def _write_step5_state(staging: Path, *, site_root: str, work_id: str = "wid", status: str = "completed", partial: bool = False) -> None:
    """Minimal completed Step 5 staging state that assess_step5_state can read."""
    write_json(staging / "run_status.json", {"status": status, "site_root": site_root})
    write_json(staging / "validation_report.json", {"ok": True})
    write_json(staging / "work_manifest.generated.json", {"works": [{"work_id": work_id, "partial": partial}]})


class AssessStep5StateTest(unittest.TestCase):
    def test_no_state_returns_fresh(self):
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "staging"
            staging.mkdir()
            d = assess_step5_state(staging, "wid", site_root=Path(td) / "site")
            self.assertEqual(d["action"], "fresh")

    def test_matching_site_root_skips(self):
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "staging"
            staging.mkdir()
            site_root = Path(td) / "site-a"
            site_root.mkdir()
            _write_step5_state(staging, site_root=str(site_root))
            d = assess_step5_state(staging, "wid", site_root=site_root)
            self.assertEqual(d["action"], "skip")

    def test_different_site_root_forces_fresh(self):
        # Gap 3 regression: Step 5 state staged for site A must not be reused when
        # the current target is site B (work vs live roots in one e2e session).
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "staging"
            staging.mkdir()
            site_a = Path(td) / "site-a"
            site_b = Path(td) / "site-b"
            site_a.mkdir()
            site_b.mkdir()
            _write_step5_state(staging, site_root=str(site_a))
            d = assess_step5_state(staging, "wid", site_root=site_b)
            self.assertEqual(d["action"], "fresh")
            self.assertIn("site_root", d["reason"])

    def test_no_site_root_arg_preserves_legacy_skip(self):
        # Back-compat: when no site_root is passed the site-root gate is bypassed
        # and a completed state still skips.
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "staging"
            staging.mkdir()
            _write_step5_state(staging, site_root=str(Path(td) / "site-a"))
            d = assess_step5_state(staging, "wid")
            self.assertEqual(d["action"], "skip")


if __name__ == "__main__":
    unittest.main()
