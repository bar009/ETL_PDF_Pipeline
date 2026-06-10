"""Validate that prod-owned Python modules do not import banned historical code.

Policy summary:
- only files under ``PDF_handle/prod/`` are checked
- direct imports of historical helpers, legacy wrappers, mirror code, and TOOLS
  are banned from prod-owned modules
- relative imports are resolved to absolute module names before checking
- ``from X import Y`` is checked both as ``X`` and as ``X.Y`` so parent-package
  imports cannot smuggle a banned child module past the guard

The human-readable policy note lives in ``PDF_handle/prod/README.md``
(section "Import Guardrail").
"""

from __future__ import annotations

import ast
from pathlib import Path


PDF_HANDLE_ROOT = Path(__file__).resolve().parent.parent
PROD_ROOT = PDF_HANDLE_ROOT / "prod"


BANNED_IMPORT_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "historical helper modules",
        (
            "pipeline_utils",
            "stage5_utils",
            "provider_runtime",
            "common",
            "workspace_paths",
        ),
    ),
    (
        "legacy step wrappers",
        (
            "run_steps_05_07",
            "step_01_extract_pdfs",
            "step_02_chunk_markdown",
            "step_03_transform_chunks",
            "step_04_consolidate_books",
            "step_05_map_and_stage",
            "step_06_apply_reviewed_merge",
            "step_07_site_qa",
        ),
    ),
    (
        "mirror and tool surfaces",
        (
            "PDF_handle.pipeline_utils",
            "PDF_handle.stage5_utils",
            "PDF_handle.provider_runtime",
            "PDF_handle.common",
            "PDF_handle.workspace_paths",
            "PDF_handle.run_steps_05_07",
            "PDF_handle.step_01_extract_pdfs",
            "PDF_handle.step_02_chunk_markdown",
            "PDF_handle.step_03_transform_chunks",
            "PDF_handle.step_04_consolidate_books",
            "PDF_handle.step_05_map_and_stage",
            "PDF_handle.step_06_apply_reviewed_merge",
            "PDF_handle.step_07_site_qa",
            "PDF_handle.AUTOMATION_MIRROR",
            "PDF_handle.TOOLS",
        ),
    ),
)

BANNED_PREFIXES = tuple(
    prefix for _, prefixes in BANNED_IMPORT_GROUPS for prefix in prefixes
)


def is_banned(module_name: str) -> bool:
    return any(
        module_name == banned or module_name.startswith(f"{banned}.")
        for banned in BANNED_PREFIXES
    )


def module_name_for_path(path: Path) -> str:
    relative = path.relative_to(PDF_HANDLE_ROOT)
    return ".".join(("PDF_handle",) + relative.with_suffix("").parts)


def resolve_from_module_name(current_module_name: str, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module or None

    current_package_parts = current_module_name.split(".")[:-1]
    if node.level > len(current_package_parts) + 1:
        return None

    base_parts = current_package_parts[: len(current_package_parts) - node.level + 1]
    if node.module:
        base_parts.extend(node.module.split("."))

    return ".".join(base_parts) if base_parts else None


def iter_import_targets(current_module_name: str, node: ast.AST) -> list[str]:
    targets: list[str] = []

    if isinstance(node, ast.Import):
        for alias in node.names:
            targets.append(alias.name)
        return targets

    if isinstance(node, ast.ImportFrom):
        resolved_module = resolve_from_module_name(current_module_name, node)
        if resolved_module:
            targets.append(resolved_module)
            for alias in node.names:
                if alias.name != "*":
                    targets.append(f"{resolved_module}.{alias.name}")
        return targets

    return targets


def collect_violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    current_module_name = module_name_for_path(path)
    relative_path = path.relative_to(PDF_HANDLE_ROOT.parent)

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for module_name in iter_import_targets(current_module_name, node):
                if is_banned(module_name):
                    if isinstance(node, ast.ImportFrom):
                        violations.append(
                            f"{relative_path}:{node.lineno} imports from banned module {module_name}"
                        )
                    else:
                        violations.append(
                            f"{relative_path}:{node.lineno} imports banned module {module_name}"
                        )
    return violations


def main() -> None:
    violations: list[str] = []
    for path in sorted(PROD_ROOT.rglob("*.py")):
        violations.extend(collect_violations(path))

    if violations:
        print("Prod import boundary violations found:")
        for violation in violations:
            print(f"- {violation}")
        raise SystemExit(1)

    print("Prod import boundaries: OK")


if __name__ == "__main__":
    main()
