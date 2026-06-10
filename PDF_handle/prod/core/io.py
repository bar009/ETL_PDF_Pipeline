from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text(path: Path) -> str:
    # Accept UTF-8 files with or without BOM so staged/live JSON can be read consistently.
    return path.read_text(encoding="utf-8-sig")


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    # tmp file lives next to the target so os.replace stays on one filesystem and is atomic.
    # Suffix includes PID to avoid collisions when two writers target the same path in one run.
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_bytes(payload)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    _atomic_write_bytes(path, content.encode("utf-8"))


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def read_json_if_exists(path: Path) -> Any | None:
    return read_json(path.resolve()) if path.exists() else None


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _atomic_write_bytes(path, payload)


def write_json_group(items: list[tuple[Path, Any]]) -> None:
    # Commit several JSON files as a near-atomic group: serialize + stage every
    # temp file first (the slow, failure-prone phase), then os.replace them all
    # back-to-back (fast metadata ops). If serialization of any file fails, no
    # live target is touched. The only residual window is an interruption mid-
    # rename, which is microseconds wide versus serializing N payloads — callers
    # still gate on a completion flag for the partial-rename case.
    staged: list[tuple[Path, Path]] = []
    try:
        for path, data in items:
            ensure_dir(path.parent)
            payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
            tmp.write_bytes(payload)
            staged.append((tmp, path))
        for tmp, path in staged:
            os.replace(tmp, path)
    finally:
        for tmp, _ in staged:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
