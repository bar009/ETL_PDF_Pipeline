from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.books import chunk_markdown, discover_books
from PDF_handle.prod.core.io import ensure_dir, read_json, read_text, utc_timestamp, write_json, write_text
from PDF_handle.prod.core.paths import DEFAULT_CHUNKED_DIR, DEFAULT_EXTRACTED_DIR
from PDF_handle.prod.core.text import normalize_newlines, sha1_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Step 2: split extracted markdown into sliding-window chunks."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_EXTRACTED_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_CHUNKED_DIR)
    parser.add_argument("--book", help="Optional extracted book directory name.")
    parser.add_argument("--min-chars", type=int, default=4000)
    parser.add_argument("--max-chars", type=int, default=6000)
    parser.add_argument("--overlap", type=int, default=500)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild chunk manifests and chunk files even if they already exist.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    books = discover_books(args.input_dir.resolve(), args.book)
    if not books:
        raise SystemExit(f"No extracted books found in {args.input_dir}")

    for book in books:
        book_name = str(book["book_name"])
        markdown_path = Path(book["markdown_path"])
        meta_path = Path(book["meta_path"]) if book["meta_path"] else None

        output_book_dir = args.output_dir.resolve() / book_name
        manifest_path = output_book_dir / "manifest.json"
        chunks_dir = output_book_dir / "chunks"

        if manifest_path.exists() and not args.force:
            print(f"[skip] {book_name} -> {manifest_path}")
            continue

        markdown_text = normalize_newlines(read_text(markdown_path))
        chunks = chunk_markdown(
            markdown_text=markdown_text,
            min_chars=args.min_chars,
            max_chars=args.max_chars,
            overlap_chars=args.overlap,
        )

        ensure_dir(chunks_dir)
        chunk_entries = []
        for chunk in chunks:
            chunk_id = f"chunk_{chunk['chunk_index'] + 1:04d}"
            chunk_filename = f"{chunk_id}.md"
            chunk_path = chunks_dir / chunk_filename
            write_text(chunk_path, chunk["text"] + "\n")

            chunk_entries.append(
                {
                    "chunk_id": chunk_id,
                    "chunk_index": chunk["chunk_index"],
                    "filename": chunk_filename,
                    "relative_path": f"chunks/{chunk_filename}",
                    "char_start": chunk["char_start"],
                    "char_end": chunk["char_end"],
                    "char_length": chunk["char_length"],
                    "source_block_start": chunk["source_block_start"],
                    "source_block_end": chunk["source_block_end"],
                    "sha1": chunk["sha1"],
                }
            )

        manifest = {
            "book_name": book_name,
            "created_at": utc_timestamp(),
            "source_markdown_path": str(markdown_path.resolve()),
            "source_markdown_sha1": sha1_text(markdown_text),
            "source_meta_path": str(meta_path.resolve()) if meta_path else None,
            "source_meta": read_json(meta_path) if meta_path and meta_path.exists() else None,
            "chunking": {
                "strategy": "paragraph-aware sliding window",
                "min_chars": args.min_chars,
                "max_chars": args.max_chars,
                "overlap_chars": args.overlap,
            },
            "chunk_count": len(chunk_entries),
            "chunks": chunk_entries,
        }

        write_json(manifest_path, manifest)
        print(f"[chunked] {book_name}: {len(chunk_entries)} chunks")


if __name__ == "__main__":
    main()
