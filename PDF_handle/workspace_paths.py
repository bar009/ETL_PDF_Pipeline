"""Compatibility re-export shell over ``PDF_handle.prod.core.site_roots``.

This module used to own a duplicate copy of the site-roots config and
resolution logic. The canonical owner is ``PDF_handle/prod/core/site_roots.py``;
this shell remains only so older tools that import ``workspace_paths`` keep
resolving the same answers as prod. Do not add logic here.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from PDF_handle.prod.core.paths import (
    PDF_HANDLE_ROOT,
    REPO_ROOT as WORKSPACE_ROOT,
    SITE_ROOTS_CONFIG_PATH,
)
from PDF_handle.prod.core.site_roots import (
    DEFAULT_SITE_ROOTS_CONFIG,
    get_legacy_sites_archive_root,
    get_live_site_root,
    get_published_sites_root,
    get_sandbox_sites_root,
    get_work_site_root,
    load_site_roots_config,
    resolve_workspace_path,
)
