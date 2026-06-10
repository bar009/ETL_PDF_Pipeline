"""Guard that compatibility wrappers stay thin.

The repo keeps legacy entrypoints (root ``step_01..07``, ``run_steps_05_07``,
``TOOLS/runners/run_*``) only as delegation shells over ``PDF_handle/prod``.
Phase 1 of ``docs/STRUCTURE_ROADMAP.md`` requires that no new core logic lands
in these files. This test pins the contract:

- a wrapper defines no functions or classes of its own
- a wrapper imports at least one ``PDF_handle.prod`` module
- ``stage5_utils.py`` (the re-export shell) imports only from ``PDF_handle.prod``
  and ``__future__``

If a wrapper legitimately needs more behavior, the behavior belongs in prod and
the wrapper should keep delegating.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF_HANDLE = REPO_ROOT / "PDF_handle"
for _p in (str(REPO_ROOT), str(PDF_HANDLE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ENTRYPOINT_WRAPPERS = (
    PDF_HANDLE / "step_01_extract_pdfs.py",
    PDF_HANDLE / "step_02_chunk_markdown.py",
    PDF_HANDLE / "step_03_transform_chunks.py",
    PDF_HANDLE / "step_04_consolidate_books.py",
    PDF_HANDLE / "step_05_map_and_stage.py",
    PDF_HANDLE / "step_06_apply_reviewed_merge.py",
    PDF_HANDLE / "step_07_site_qa.py",
    PDF_HANDLE / "run_steps_05_07.py",
    PDF_HANDLE / "TOOLS" / "runners" / "run_preprocess_01_04.py",
    PDF_HANDLE / "TOOLS" / "runners" / "run_postmerge_05_07.py",
    PDF_HANDLE / "TOOLS" / "runners" / "run_new_material_e2e.py",
)

REEXPORT_SHELL = PDF_HANDLE / "stage5_utils.py"


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_modules(tree: ast.Module) -> list[str]:
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


class TestEntrypointWrappersStayThin(unittest.TestCase):
    def test_all_expected_wrappers_exist(self) -> None:
        missing = [str(p) for p in ENTRYPOINT_WRAPPERS if not p.is_file()]
        self.assertEqual(missing, [], f"Expected compatibility wrappers are missing: {missing}")

    def test_wrappers_define_no_logic(self) -> None:
        for path in ENTRYPOINT_WRAPPERS:
            tree = _parse(path)
            offenders = [
                f"{path.name}:{node.lineno} defines {type(node).__name__}"
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            ]
            self.assertEqual(
                offenders,
                [],
                "Compatibility wrappers must not define functions or classes; "
                "move the logic into PDF_handle/prod instead:\n" + "\n".join(offenders),
            )

    def test_wrappers_delegate_to_prod(self) -> None:
        for path in ENTRYPOINT_WRAPPERS:
            modules = _imported_modules(_parse(path))
            self.assertTrue(
                any(m.startswith("PDF_handle.prod") for m in modules),
                f"{path.name} does not import a PDF_handle.prod module; "
                f"imports found: {modules}",
            )


class TestStage5UtilsIsPureReexport(unittest.TestCase):
    def test_imports_only_from_prod(self) -> None:
        tree = _parse(REEXPORT_SHELL)
        bad: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                bad.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module != "__future__" and not module.startswith("PDF_handle.prod"):
                    bad.append(module)
        self.assertEqual(
            bad,
            [],
            f"stage5_utils.py must only re-export from PDF_handle.prod; found: {bad}",
        )

    def test_defines_no_logic(self) -> None:
        tree = _parse(REEXPORT_SHELL)
        offenders = [
            f"stage5_utils.py:{node.lineno} defines {type(node).__name__}"
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        self.assertEqual(offenders, [], "\n".join(offenders))


if __name__ == "__main__":
    unittest.main()
