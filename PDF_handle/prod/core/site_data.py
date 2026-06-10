from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_site_data_paths(site_root: Path) -> dict[str, Path]:
    site_root = site_root.resolve()
    data_dir = site_root / "data"
    return {
        "site_root": site_root,
        "data_dir": data_dir,
        "schema": data_dir / "content.schema.json",
        "overrides": data_dir / "content.overrides.json",
        "library": data_dir / "library.json",
        "level1": data_dir / "level1.json",
        "level2": data_dir / "level2.json",
        "level3": data_dir / "level3.json",
    }


def describe_missing_site_data_paths(site_paths: dict[str, Path]) -> str:
    required_paths = (
        ("data_dir", site_paths["data_dir"]),
        ("schema", site_paths["schema"]),
        ("library", site_paths["library"]),
        ("level1", site_paths["level1"]),
        ("level2", site_paths["level2"]),
    )
    missing = [f"{label}={path.resolve()}" for label, path in required_paths if not path.exists()]
    if not missing:
        return ""
    return f"Site root {site_paths['site_root']} is missing required data paths: {', '.join(missing)}"


def build_file_stat_signature(path: Path) -> dict[str, Any]:
    # Path + size + mtime. NOT a content hash. Cheap to compute; sufficient for "did this
    # file change since the last run?" within a single working tree, but unreliable across
    # machines/CI runners (mtime is not stable) and trivially defeatable by `touch` or
    # mtime-preserving copies. Use a SHA-256 if real content identity is required.
    resolved = path.resolve()
    stats = resolved.stat()
    return {
        "path": str(resolved),
        "size": stats.st_size,
        "mtime": stats.st_mtime,
        "mtime_iso": datetime.fromtimestamp(stats.st_mtime, timezone.utc).replace(microsecond=0).isoformat(),
    }


def build_site_data_stat_signatures(site_paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    missing_message = describe_missing_site_data_paths(site_paths)
    if missing_message:
        raise FileNotFoundError(missing_message)
    return {
        "schema": build_file_stat_signature(site_paths["schema"]),
        "overrides": build_file_stat_signature(site_paths["overrides"]) if site_paths["overrides"].exists() else {},
        "library": build_file_stat_signature(site_paths["library"]),
        "level1": build_file_stat_signature(site_paths["level1"]),
        "level2": build_file_stat_signature(site_paths["level2"]),
        **(
            {"level3": build_file_stat_signature(site_paths["level3"])}
            if site_paths["level3"].exists()
            else {}
        ),
    }
