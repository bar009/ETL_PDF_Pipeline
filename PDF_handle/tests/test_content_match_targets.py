from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.steps.stage_support import select_content_match_targets


def _match(slug: str, *, provider_suggested: bool, score: float) -> dict:
    return {
        "slug": slug,
        "degree": "level2",
        "provider_suggested": provider_suggested,
        "score": score,
    }


class SelectContentMatchTargetsTest(unittest.TestCase):
    def test_keeps_only_provider_suggested(self) -> None:
        # Mirrors the empirical fan-out bug: the highest-scoring lexical match
        # ("seven-liberal-arts") is NOT the provider-named subject; only the
        # lower-scoring, provider-suggested "plumb-level-square" is correct.
        strong = [
            _match("seven-liberal-arts", provider_suggested=False, score=0.9),
            _match("five-senses", provider_suggested=False, score=0.7),
            _match("plumb-level-square", provider_suggested=True, score=0.3),
        ]
        targets = select_content_match_targets(strong)
        self.assertEqual([m["slug"] for m in targets], ["plumb-level-square"])

    def test_withholds_when_no_provider_hint(self) -> None:
        # Strong-but-lexical-only matches yield no content target; caller withholds.
        strong = [
            _match("seven-liberal-arts", provider_suggested=False, score=0.9),
            _match("five-senses", provider_suggested=False, score=0.7),
        ]
        self.assertEqual(select_content_match_targets(strong), [])

    def test_keeps_all_provider_suggested(self) -> None:
        strong = [
            _match("a", provider_suggested=True, score=0.5),
            _match("b", provider_suggested=True, score=0.4),
        ]
        targets = select_content_match_targets(strong)
        self.assertEqual([m["slug"] for m in targets], ["a", "b"])

    def test_empty_input(self) -> None:
        self.assertEqual(select_content_match_targets([]), [])

    def test_missing_flag_treated_as_not_suggested(self) -> None:
        strong = [{"slug": "x", "degree": "level1", "score": 0.6}]
        self.assertEqual(select_content_match_targets(strong), [])


if __name__ == "__main__":
    unittest.main()
