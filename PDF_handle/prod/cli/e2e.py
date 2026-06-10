from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PDF_handle.prod.impl.e2e_runner import main as e2e_main


def main() -> None:
    e2e_main()


if __name__ == "__main__":
    main()
