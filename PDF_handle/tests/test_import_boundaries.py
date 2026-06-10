"""Run the prod import-boundary check as part of the regular test suite.

``PDF_handle/prod/check_import_boundaries.py`` is the policy owner; this test
just makes sure ``python -m unittest discover -s PDF_handle/tests`` fails when
prod code starts importing banned historical helpers, legacy wrappers, mirror
code, or TOOLS modules.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.check_import_boundaries import PROD_ROOT, collect_violations


class TestProdImportBoundaries(unittest.TestCase):
    def test_prod_has_no_banned_imports(self) -> None:
        violations: list[str] = []
        for path in sorted(PROD_ROOT.rglob("*.py")):
            violations.extend(collect_violations(path))

        self.assertEqual(
            violations,
            [],
            "Prod import boundary violations found:\n" + "\n".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
