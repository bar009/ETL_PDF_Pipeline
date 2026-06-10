from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.core.site_roots import stable_site_label


class StableSiteLabelTest(unittest.TestCase):
    def test_same_basename_different_paths_dont_collide(self):
        # Regression: backup_dir collision bug (sites/work/v0.4 vs sites/live/v0.4).
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "work" / "v0.4").mkdir(parents=True)
            (base / "live" / "v0.4").mkdir(parents=True)
            label_work = stable_site_label(base / "work" / "v0.4")
            label_live = stable_site_label(base / "live" / "v0.4")
            self.assertNotEqual(label_work, label_live)
            self.assertTrue(label_work.startswith("v0.4--"))
            self.assertTrue(label_live.startswith("v0.4--"))

    def test_same_path_is_stable(self):
        # Same absolute path → same label across calls (used as cache key).
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "v0.4"
            p.mkdir()
            self.assertEqual(stable_site_label(p), stable_site_label(p))

    def test_label_includes_basename_for_human_readability(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "v0.4-current"
            p.mkdir()
            label = stable_site_label(p)
            self.assertTrue(label.startswith("v0.4-current--"))
            # 8-char short hash suffix
            self.assertEqual(len(label) - len("v0.4-current--"), 8)


if __name__ == "__main__":
    unittest.main()
