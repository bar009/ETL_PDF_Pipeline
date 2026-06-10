from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from PDF_handle.prod.core.io import ensure_dir, utc_timestamp, write_json
from PDF_handle.prod.core.paths import RUNS_ROOT


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

    base_dir = ensure_dir(RUNS_ROOT / tool_name)
    if site_root is not None:
        base_dir = ensure_dir(base_dir / site_label(site_root))
    return ensure_dir(base_dir / timestamp_slug())


def run_subprocess(command: list[str], *, quiet: bool) -> None:
    if not quiet:
        print("[exec] " + " ".join(command), flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {completed.returncode}: {' '.join(command)}"
        )


def write_run_artifact(report_dir: Path, filename: str, payload: dict[str, Any]) -> Path:
    path = report_dir / filename
    write_json(path, payload)
    return path


def write_run_manifest(report_dir: Path, filename: str, payload: dict[str, Any]) -> Path:
    return write_run_artifact(report_dir, filename, payload)


def write_run_definition(report_dir: Path, payload: dict[str, Any]) -> Path:
    return write_run_artifact(report_dir, "run_definition.json", payload)
