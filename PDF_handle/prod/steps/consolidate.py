from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.books import merge_markdown_with_overlap
from PDF_handle.prod.core.io import ensure_dir, read_json, read_text, utc_timestamp, write_json, write_text
from PDF_handle.prod.core.paths import DEFAULT_CONSOLIDATED_DIR, DEFAULT_TRANSFORMED_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Step 4: consolidate transformed chunk markdown into a book-level draft."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_TRANSFORMED_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_CONSOLIDATED_DIR)
    parser.add_argument("--book", help="Optional transformed book directory name.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild consolidated files even if they already exist.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    input_dir = args.input_dir.resolve()
    book_dirs = sorted(path for path in input_dir.iterdir() if path.is_dir())
    if args.book:
        book_dirs = [path for path in book_dirs if path.name == args.book]
    if not book_dirs:
        raise SystemExit(f"No transformed books found in {input_dir}")

    output_dir = ensure_dir(args.output_dir.resolve())

    for book_dir in book_dirs:
        manifest_path = book_dir / "manifest.json"
        if not manifest_path.exists():
            print(f"[skip] {book_dir.name} has no manifest")
            continue

        manifest = read_json(manifest_path)
        book_name = manifest["book_name"]
        consolidated_markdown_path = output_dir / f"{book_name}.md"
        consolidated_meta_path = output_dir / f"{book_name}_meta.json"

        if consolidated_markdown_path.exists() and consolidated_meta_path.exists() and not args.force:
            print(f"[skip] {book_name} -> {consolidated_markdown_path}")
            continue

        merged_text = ""
        seam_reports = []

        for chunk in sorted(manifest["chunks"], key=lambda item: item["chunk_index"]):
            chunk_text = read_text(Path(chunk["markdown_path"])).strip()
            if not merged_text:
                merged_text = chunk_text
                continue

            merged_text, seam_report = merge_markdown_with_overlap(merged_text, chunk_text)
            seam_report["chunk_id"] = chunk["chunk_id"]
            seam_reports.append(seam_report)

        write_text(consolidated_markdown_path, merged_text.strip() + "\n")
        write_json(
            consolidated_meta_path,
            {
                "book_name": book_name,
                "created_at": utc_timestamp(),
                "source_manifest_path": str(manifest_path.resolve()),
                "consolidated_markdown_path": str(consolidated_markdown_path.resolve()),
                "chunk_count": len(manifest["chunks"]),
                "seam_reports": seam_reports,
            },
        )
        print(f"[consolidated] {book_name}")


if __name__ == "__main__":
    main()
