"""Compatibility wrapper.

Canonical implementation: ``PDF_handle.prod.steps.stage``.
Keep this file only for legacy invocation paths.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PDF_handle.prod.steps.stage import main


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[error] {exc}", flush=True)
        raise
