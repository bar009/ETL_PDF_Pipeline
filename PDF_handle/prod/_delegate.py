from __future__ import annotations

import runpy
import sys
from pathlib import Path


PDF_HANDLE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PDF_HANDLE_ROOT.parent
TOOLS_DIR = PDF_HANDLE_ROOT / "TOOLS"


def run_legacy_script(*relative_parts: str) -> None:
    target = PDF_HANDLE_ROOT.joinpath(*relative_parts)
    for candidate in (REPO_ROOT, PDF_HANDLE_ROOT, TOOLS_DIR, target.parent):
        if str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
    runpy.run_path(str(target), run_name="__main__")
