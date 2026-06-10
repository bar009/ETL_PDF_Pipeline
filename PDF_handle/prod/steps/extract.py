from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle import main as extractor_main
from PDF_handle.prod.core.io import utc_timestamp, write_text
from PDF_handle.prod.core.paths import DEFAULT_EXTRACTED_DIR, DEFAULT_PDF_DIR

# Written into a book's output dir only after extraction finishes. Its absence means a
# prior run crashed mid-extract; the dir exists but is incomplete and must be redone.
EXTRACT_COMPLETE_MARKER = ".extract_complete"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Step 1: extract PDFs into markdown, metadata, and images."
    )
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_EXTRACTED_DIR)
    parser.add_argument("--book", help="Optional PDF file name stem to process.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-extract even if the output directory already exists.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    pdf_dir = args.pdf_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_paths = sorted(pdf_dir.glob("*.pdf"))
    if args.book:
        pdf_paths = [path for path in pdf_paths if path.stem == args.book]

    if not pdf_paths:
        raise SystemExit(f"No PDF files found in {pdf_dir}")

    for pdf_path in pdf_paths:
        destination = output_dir / pdf_path.stem
        marker = destination / EXTRACT_COMPLETE_MARKER
        if marker.exists() and not args.force:
            print(f"[skip] {pdf_path.name} -> {destination}")
            continue
        if destination.exists() and not args.force:
            print(f"[redo] {pdf_path.name}: prior extraction incomplete (no completion marker)")

        print(f"[extract] {pdf_path.name}")
        extractor_main.extract_pdf_with_images(str(pdf_path), str(output_dir))
        write_text(marker, utc_timestamp() + "\n")


if __name__ == "__main__":
    main()
