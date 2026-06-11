from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.steps.qa import (
    build_shared_access_unlock_candidates,
    build_unlock_entry_url,
)


class BrowserQaUnlockCandidatesTest(unittest.TestCase):
    def test_returns_candidates_in_degree_order(self) -> None:
        candidates = build_shared_access_unlock_candidates("one", "two", "three")
        self.assertEqual(
            candidates,
            [("level1", "one"), ("level2", "two"), ("level3", "three")],
        )

    def test_skips_missing_passwords(self) -> None:
        candidates = build_shared_access_unlock_candidates(None, "two", "")
        self.assertEqual(candidates, [("level2", "two")])

    def test_strips_whitespace(self) -> None:
        candidates = build_shared_access_unlock_candidates("  one  ", None, "  3 ")
        self.assertEqual(candidates, [("level1", "one"), ("level3", "3")])

    def test_build_unlock_entry_url_prefers_real_slug(self) -> None:
        url = build_unlock_entry_url(
            "http://127.0.0.1:4177",
            "level3",
            {"level3_slug": "commentary-on-the-second-degree"},
        )
        self.assertEqual(
            url,
            "http://127.0.0.1:4177/index.html#level3/commentary-on-the-second-degree",
        )

    def test_build_unlock_entry_url_uses_probe_slug_when_missing(self) -> None:
        url = build_unlock_entry_url(
            "http://127.0.0.1:4177",
            "level2",
            {},
        )
        self.assertEqual(
            url,
            "http://127.0.0.1:4177/index.html#level2/__qa_unlock__",
        )


if __name__ == "__main__":
    unittest.main()
