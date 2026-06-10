"""Smoke checks: every CLI entrypoint must parse ``--help`` on a clean checkout.

Phase 5 of ``docs/STRUCTURE_ROADMAP.md`` requires that a clean checkout can run
the documented checks without private data. ``--help`` is the smallest useful
proof: it fails when an entrypoint breaks at import time or resolves site
roots/run evidence eagerly (both have happened — see the decision log for
2026-06-11).

Scripts in ``ONE_SHOT_SCRIPTS`` would be pinned to past operational runs and
excluded here. The original five were retired in WS11
(see ``PDF_handle/docs/WRAPPER_RETIREMENT.md``); the list stays so a future
one-shot has a documented, test-enforced home.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF_HANDLE = REPO_ROOT / "PDF_handle"
PROD_CLI = PDF_HANDLE / "prod" / "cli"

ONE_SHOT_SCRIPTS: set[str] = set()

WRAPPER_ENTRYPOINTS = (
    PDF_HANDLE / "step_01_extract_pdfs.py",
    PDF_HANDLE / "step_02_chunk_markdown.py",
    PDF_HANDLE / "step_03_transform_chunks.py",
    PDF_HANDLE / "step_04_consolidate_books.py",
    PDF_HANDLE / "step_05_map_and_stage.py",
    PDF_HANDLE / "step_06_apply_reviewed_merge.py",
    PDF_HANDLE / "step_07_site_qa.py",
    PDF_HANDLE / "run_steps_05_07.py",
)


def _help_exit_code(script: Path) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO_ROOT),
    )
    return result.returncode, (result.stderr or result.stdout)[-500:]


class TestProdCliHelpSmoke(unittest.TestCase):
    def test_one_shot_list_matches_reality(self) -> None:
        cli_scripts = {p.name for p in PROD_CLI.glob("*.py")} - {"__init__.py"}
        unknown = ONE_SHOT_SCRIPTS - cli_scripts
        self.assertEqual(
            unknown,
            set(),
            f"ONE_SHOT_SCRIPTS names scripts that no longer exist: {unknown} — "
            "remove them from the list",
        )

    def test_every_prod_cli_parses_help(self) -> None:
        failures: list[str] = []
        for script in sorted(PROD_CLI.glob("*.py")):
            if script.name == "__init__.py" or script.name in ONE_SHOT_SCRIPTS:
                continue
            code, tail = _help_exit_code(script)
            if code != 0:
                failures.append(f"{script.name} (exit {code}): {tail}")
        self.assertEqual(failures, [], "prod CLIs failing --help:\n" + "\n".join(failures))

    def test_every_wrapper_parses_help(self) -> None:
        failures: list[str] = []
        for script in WRAPPER_ENTRYPOINTS:
            code, tail = _help_exit_code(script)
            if code != 0:
                failures.append(f"{script.name} (exit {code}): {tail}")
        self.assertEqual(failures, [], "wrappers failing --help:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
