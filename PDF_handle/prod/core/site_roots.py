from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PDF_handle.prod.core.paths import REPO_ROOT, SITE_ROOTS_CONFIG_PATH


DEFAULT_SITE_ROOTS_CONFIG: dict[str, str] = {
    "live_site_root": "sites/live/v0.4-current",
    "legacy_live_site_root": "0.3",
    "work_site_root": "sites/work/v0.4",
    "legacy_work_site_root": "0.3-copy",
    "sandbox_sites_root": "sandbox_sites",
    "published_sites_root": "published_sites",
    "legacy_sites_archive_root": "archive/legacy_sites",
}


def load_site_roots_config() -> dict[str, str]:
    if not SITE_ROOTS_CONFIG_PATH.exists():
        return dict(DEFAULT_SITE_ROOTS_CONFIG)

    payload = json.loads(SITE_ROOTS_CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Site-roots config must be an object: {SITE_ROOTS_CONFIG_PATH}")

    merged = dict(DEFAULT_SITE_ROOTS_CONFIG)
    for key, value in payload.items():
        if isinstance(value, str) and value.strip():
            merged[key] = value.strip()
    return merged


def resolve_workspace_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def _configured_path(key: str) -> Path:
    config = load_site_roots_config()
    return resolve_workspace_path(config[key])


def _looks_like_site_root(path: Path) -> bool:
    data_dir = path / "data"
    return data_dir.is_dir() and (data_dir / "content.schema.json").exists()


def _require_site_root(key: str, *, label: str) -> Path:
    preferred = _configured_path(key)
    if _looks_like_site_root(preferred):
        return preferred
    raise FileNotFoundError(
        f"Configured {label} site root is unavailable or invalid: {preferred}"
    )


def get_live_site_root() -> Path:
    return _require_site_root("live_site_root", label="live")


def get_work_site_root() -> Path:
    return _require_site_root("work_site_root", label="work")


def get_sandbox_sites_root() -> Path:
    return _configured_path("sandbox_sites_root")


def get_published_sites_root() -> Path:
    return _configured_path("published_sites_root")


def get_legacy_sites_archive_root() -> Path:
    return _configured_path("legacy_sites_archive_root")


def stable_site_label(site_root: Path) -> str:
    # Site-root-scoped key used for manifests, QA report dirs, and merge backup dirs.
    # Basename alone collides when two roots share a leaf name (e.g. sites/work/v0.4 vs sites/live/v0.4).
    resolved = str(site_root.resolve())
    short_hash = hashlib.sha256(resolved.encode()).hexdigest()[:8]
    return f"{site_root.resolve().name}--{short_hash}"
