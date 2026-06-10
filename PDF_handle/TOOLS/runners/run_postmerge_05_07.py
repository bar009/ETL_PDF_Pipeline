"""Compatibility wrapper.

Canonical implementation: ``PDF_handle.prod.cli.postmerge``.
Keep this file only for legacy operator and script invocation paths.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PDF_handle.prod.cli.postmerge import main


if __name__ == "__main__":
    main()
