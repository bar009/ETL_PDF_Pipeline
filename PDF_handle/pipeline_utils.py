"""Compatibility re-export shell over ``PDF_handle.prod.core``.

This module used to own duplicate copies of the IO, text, book-discovery,
chunking, and site-data helpers. The canonical owners now live under
``PDF_handle/prod/core/`` (``io``, ``text``, ``books``, ``site_data``,
``paths``). This shell remains only so older tools that import
``pipeline_utils`` keep working. Do not add logic here.

Intentional differences from the historical module:

- ``DEFAULT_SITE_ROOT`` is gone. It resolved the live site root at import
  time and crashed every importer in a checkout without a live site root.
  Resolve roots at call time via ``PDF_handle.prod.core.site_roots`` instead.
- ``atomic_write_text`` / ``atomic_write_json`` / ``safe_json_write`` map to
  the prod writers, which are always atomic.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from PDF_handle.prod.core.books import (
    chunk_markdown,
    discover_books,
    extract_blocks,
    load_chunk_manifest,
    merge_markdown_with_overlap,
    normalize_for_comparison,
    split_paragraphs,
)
from PDF_handle.prod.core.io import (
    ensure_dir,
    read_json,
    read_text,
    utc_timestamp,
    write_json,
    write_text,
)
from PDF_handle.prod.core.paths import (
    DEFAULT_CHUNKED_DIR,
    DEFAULT_CONSOLIDATED_DIR,
    DEFAULT_EXTRACTED_DIR,
    DEFAULT_PDF_DIR,
    DEFAULT_PROMPTS_DIR,
    DEFAULT_TRANSFORMED_DIR,
    PDF_HANDLE_ROOT as BASE_DIR,
)
from PDF_handle.prod.core.site_data import (
    build_file_stat_signature as build_file_fingerprint,
    build_site_data_stat_signatures as build_site_data_fingerprints,
    build_site_data_paths,
    describe_missing_site_data_paths,
)
from PDF_handle.prod.core.text import (
    normalize_newlines,
    sha1_text,
)

# Historical names for the atomic writers; prod writers are always atomic.
atomic_write_text = write_text
atomic_write_json = write_json
safe_json_write = write_json
