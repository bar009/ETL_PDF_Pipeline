from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any


LIB_DIR = Path(__file__).resolve().parent
TOOLS_DIR = LIB_DIR.parent
PDF_HANDLE_ROOT = TOOLS_DIR.parent
CODE_ROOT = PDF_HANDLE_ROOT.parent
DEFAULT_TOOLS_REPORTS_ROOT = TOOLS_DIR / "reports"

if str(PDF_HANDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(PDF_HANDLE_ROOT))

from pipeline_utils import ensure_dir, read_json, utc_timestamp, write_json  # noqa: E402


def log(message: str, *, quiet: bool) -> None:
    if not quiet:
        print(message, flush=True)


def timestamp_slug() -> str:
    return utc_timestamp().replace(":", "-")


def site_label(site_root: Path | str) -> str:
    return Path(site_root).resolve().name


def resolve_report_dir(
    *,
    tool_name: str,
    report_dir: Path | None,
    site_root: Path | None = None,
) -> Path:
    if report_dir is not None:
        return ensure_dir(report_dir.resolve())

    base_dir = ensure_dir(DEFAULT_TOOLS_REPORTS_ROOT / tool_name)
    if site_root is not None:
        base_dir = ensure_dir(base_dir / site_label(site_root))
    return ensure_dir(base_dir / timestamp_slug())


def load_routing_config(path: Path) -> dict[str, Any]:
    return read_json(path.resolve())


def read_json_if_exists(path: Path) -> Any | None:
    return read_json(path.resolve()) if path.exists() else None


def run_subprocess(command: list[str], *, quiet: bool) -> None:
    if not quiet:
        print("[exec] " + " ".join(command), flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {completed.returncode}: {' '.join(command)}"
        )


def write_run_manifest(report_dir: Path, filename: str, payload: dict[str, Any]) -> Path:
    path = report_dir / filename
    write_json(path, payload)
    return path
