"""Shared production support modules for the PDF pipeline."""

from PDF_handle.prod.core.books import chunk_markdown, discover_books, load_chunk_manifest, merge_markdown_with_overlap
from PDF_handle.prod.core.io import ensure_dir, read_json, read_json_if_exists, utc_timestamp, write_json, write_json_group, write_text
from PDF_handle.prod.core.paths import (
    DEFAULT_CHUNKED_DIR,
    DEFAULT_CONSOLIDATED_DIR,
    DEFAULT_EXTRACTED_DIR,
    DEFAULT_PDF_DIR,
    DEFAULT_PIPELINE_RUNS_ROOT,
    DEFAULT_PROMPTS_DIR,
    DEFAULT_QA_REPORTS_ROOT,
    DEFAULT_STAGED_RUNS_ROOT,
    DEFAULT_TRANSFORMED_DIR,
    PDF_HANDLE_ROOT,
    PROD_ROOT,
    REPO_ROOT,
    RUNS_ROOT,
    TOOLS_ROOT,
)
from PDF_handle.prod.core.runtime import (
    log,
    resolve_report_dir,
    run_subprocess,
    write_run_definition,
    write_run_manifest,
)
from PDF_handle.prod.core.site_data import build_site_data_paths, build_site_data_stat_signatures
from PDF_handle.prod.core.site_roots import get_live_site_root, get_work_site_root, stable_site_label
from PDF_handle.prod.core.text import normalize_newlines, sha1_text
