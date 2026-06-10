from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"

for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core import (  # noqa: E402
    DEFAULT_CHUNKED_DIR,
    DEFAULT_CONSOLIDATED_DIR,
    DEFAULT_EXTRACTED_DIR,
    DEFAULT_PDF_DIR,
    DEFAULT_PROMPTS_DIR,
    DEFAULT_TRANSFORMED_DIR,
    log,
    resolve_report_dir,
    run_subprocess,
    utc_timestamp,
    write_run_definition,
    write_run_manifest,
)


STEP_01_SCRIPT = PDF_HANDLE_ROOT / "prod" / "steps" / "extract.py"
STEP_02_SCRIPT = PDF_HANDLE_ROOT / "prod" / "steps" / "chunk.py"
STEP_03_SCRIPT = PDF_HANDLE_ROOT / "prod" / "steps" / "transform.py"
STEP_04_SCRIPT = PDF_HANDLE_ROOT / "prod" / "steps" / "consolidate.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prod preprocess runner for Steps 1-4: extract, chunk, transform, and consolidate."
    )
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--extracted-dir", type=Path, default=DEFAULT_EXTRACTED_DIR)
    parser.add_argument("--chunked-dir", type=Path, default=DEFAULT_CHUNKED_DIR)
    parser.add_argument("--transformed-dir", type=Path, default=DEFAULT_TRANSFORMED_DIR)
    parser.add_argument("--consolidated-dir", type=Path, default=DEFAULT_CONSOLIDATED_DIR)
    parser.add_argument("--prompt-file", type=Path, default=DEFAULT_PROMPTS_DIR / "archivist_system.txt")
    parser.add_argument("--book", help="Optional book/PDF stem to process across Steps 1-4.")
    parser.add_argument("--provider", choices=["gemini", "dry-run"], default="dry-run")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--api-key-env", default="GEMINI_API_KEY")
    parser.add_argument("--min-chars", type=int, default=4000)
    parser.add_argument("--max-chars", type=int, default=6000)
    parser.add_argument("--overlap", type=int, default=500)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--force-step1", action="store_true")
    parser.add_argument("--force-step2", action="store_true")
    parser.add_argument("--force-step3", action="store_true")
    parser.add_argument("--force-step4", action="store_true")
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    return parser


def step1_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(STEP_01_SCRIPT),
        "--pdf-dir",
        str(args.pdf_dir.resolve()),
        "--output-dir",
        str(args.extracted_dir.resolve()),
    ]
    if args.book:
        command.extend(["--book", args.book])
    if args.force_step1:
        command.append("--force")
    return command


def step2_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(STEP_02_SCRIPT),
        "--input-dir",
        str(args.extracted_dir.resolve()),
        "--output-dir",
        str(args.chunked_dir.resolve()),
        "--min-chars",
        str(args.min_chars),
        "--max-chars",
        str(args.max_chars),
        "--overlap",
        str(args.overlap),
    ]
    if args.book:
        command.extend(["--book", args.book])
    if args.force_step2:
        command.append("--force")
    return command


def step3_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(STEP_03_SCRIPT),
        "--input-dir",
        str(args.chunked_dir.resolve()),
        "--output-dir",
        str(args.transformed_dir.resolve()),
        "--provider",
        args.provider,
        "--model",
        args.model,
        "--prompt-file",
        str(args.prompt_file.resolve()),
        "--api-key-env",
        args.api_key_env,
        "--temperature",
        str(args.temperature),
        "--max-output-tokens",
        str(args.max_output_tokens),
        "--sleep-seconds",
        str(args.sleep_seconds),
        "--max-retries",
        str(args.max_retries),
    ]
    if args.book:
        command.extend(["--book", args.book])
    if args.force_step3:
        command.append("--force")
    return command


def step4_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(STEP_04_SCRIPT),
        "--input-dir",
        str(args.transformed_dir.resolve()),
        "--output-dir",
        str(args.consolidated_dir.resolve()),
    ]
    if args.book:
        command.extend(["--book", args.book])
    if args.force_step4:
        command.append("--force")
    return command


def main() -> None:
    args = build_parser().parse_args()
    report_dir = resolve_report_dir(tool_name="run_preprocess_01_04", report_dir=args.report_dir)
    run_definition = {
        "tool": "run_preprocess_01_04",
        "created_at": utc_timestamp(),
        "book": args.book,
        "pdf_dir": str(args.pdf_dir.resolve()),
        "extracted_dir": str(args.extracted_dir.resolve()),
        "chunked_dir": str(args.chunked_dir.resolve()),
        "transformed_dir": str(args.transformed_dir.resolve()),
        "consolidated_dir": str(args.consolidated_dir.resolve()),
        "prompt_file": str(args.prompt_file.resolve()),
        "provider": args.provider,
        "model": args.model,
        "api_key_env": args.api_key_env,
        "min_chars": args.min_chars,
        "max_chars": args.max_chars,
        "overlap": args.overlap,
        "temperature": args.temperature,
        "max_output_tokens": args.max_output_tokens,
        "sleep_seconds": args.sleep_seconds,
        "max_retries": args.max_retries,
        "force_steps": {
            "step1": args.force_step1,
            "step2": args.force_step2,
            "step3": args.force_step3,
            "step4": args.force_step4,
        },
        "report_dir": str(report_dir.resolve()),
        "quiet": args.quiet,
    }
    manifest: dict[str, Any] = {
        "created_at": utc_timestamp(),
        "tool": "run_preprocess_01_04",
        "book": args.book,
        "provider": args.provider,
        "model": args.model,
        "report_dir": str(report_dir),
        "steps": [],
        "status": "running",
    }
    write_run_definition(report_dir, run_definition)

    try:
        for step_name, command in [
            ("step_01_extract_pdfs", step1_command(args)),
            ("step_02_chunk_markdown", step2_command(args)),
            ("step_03_transform_chunks", step3_command(args)),
            ("step_04_consolidate_books", step4_command(args)),
        ]:
            log(f"[{step_name}] running", quiet=args.quiet)
            manifest["steps"].append({"step": step_name, "command": command, "status": "running"})
            run_subprocess(command, quiet=args.quiet)
            manifest["steps"][-1]["status"] = "completed"

        manifest["status"] = "completed"
        write_run_manifest(report_dir, "run_manifest.json", manifest)
        log(f"[done] preprocess completed report={report_dir}", quiet=args.quiet)
    except Exception as exc:
        if manifest["steps"]:
            manifest["steps"][-1]["status"] = "failed"
            manifest["steps"][-1]["error"] = str(exc)
        manifest["status"] = "failed"
        manifest["error"] = str(exc)
        write_run_manifest(report_dir, "run_manifest.json", manifest)
        print(f"[error] {exc}", flush=True)
        raise


if __name__ == "__main__":
    main()
