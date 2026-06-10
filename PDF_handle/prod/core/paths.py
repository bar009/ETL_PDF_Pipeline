from __future__ import annotations

from pathlib import Path


PDF_HANDLE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PDF_HANDLE_ROOT.parent
PROD_ROOT = PDF_HANDLE_ROOT / "prod"
RUNS_ROOT = PDF_HANDLE_ROOT / "runs"
TOOLS_ROOT = PDF_HANDLE_ROOT / "TOOLS"
SITE_ROOTS_CONFIG_PATH = REPO_ROOT / "sites" / "site_roots.json"

DEFAULT_PDF_DIR = PDF_HANDLE_ROOT / "PDF_files"
DEFAULT_EXTRACTED_DIR = PDF_HANDLE_ROOT / "extracted_books"
DEFAULT_CHUNKED_DIR = PDF_HANDLE_ROOT / "chunked_books"
DEFAULT_TRANSFORMED_DIR = PDF_HANDLE_ROOT / "transformed_books"
DEFAULT_CONSOLIDATED_DIR = PDF_HANDLE_ROOT / "consolidated_books"
DEFAULT_PROMPTS_DIR = PDF_HANDLE_ROOT / "prompts"
DEFAULT_STAGED_RUNS_ROOT = PDF_HANDLE_ROOT / "staged_runs"
DEFAULT_PIPELINE_RUNS_ROOT = PDF_HANDLE_ROOT / "pipeline_runs"
DEFAULT_QA_REPORTS_ROOT = PDF_HANDLE_ROOT / "qa_reports"
