from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from PDF_handle.prod.core.io import read_json
from PDF_handle.prod.core.text import normalize_newlines, sha1_text


def discover_books(extracted_dir: Path, book_filter: str | None = None) -> list[dict[str, Path | str | None]]:
    books: list[dict[str, Path | str | None]] = []

    for book_dir in sorted(path for path in extracted_dir.iterdir() if path.is_dir()):
        book_name = book_dir.name
        if book_filter and book_name != book_filter:
            continue

        markdown_path = book_dir / f"{book_name}.md"
        if not markdown_path.exists():
            candidates = sorted(book_dir.glob("*.md"))
            if not candidates:
                continue
            markdown_path = candidates[0]

        meta_path = book_dir / f"{book_name}_meta.json"
        if not meta_path.exists():
            meta_candidates = sorted(book_dir.glob("*_meta.json"))
            meta_path = meta_candidates[0] if meta_candidates else None

        books.append(
            {
                "book_name": book_name,
                "book_dir": book_dir,
                "markdown_path": markdown_path,
                "meta_path": meta_path,
            }
        )

    return books


def extract_blocks(markdown_text: str) -> list[dict[str, Any]]:
    text = normalize_newlines(markdown_text)
    if not text:
        return []

    blocks: list[dict[str, Any]] = []
    for match in re.finditer(r".+?(?=\n{2,}|\Z)", text, re.DOTALL):
        raw_block = match.group(0)
        block_text = raw_block.strip()
        if not block_text:
            continue
        blocks.append(
            {
                "text": block_text,
                "start": match.start(),
                "end": match.end(),
            }
        )

    return blocks


def chunk_markdown(
    markdown_text: str,
    min_chars: int,
    max_chars: int,
    overlap_chars: int,
) -> list[dict[str, Any]]:
    if min_chars <= 0 or max_chars <= 0:
        raise ValueError("Chunk sizes must be positive integers.")
    if min_chars > max_chars:
        raise ValueError("min_chars cannot be greater than max_chars.")
    if overlap_chars < 0:
        raise ValueError("overlap_chars cannot be negative.")

    blocks = extract_blocks(markdown_text)
    if not blocks:
        return []

    chunks: list[dict[str, Any]] = []
    index = 0

    while index < len(blocks):
        start_index = index
        current_blocks: list[dict[str, Any]] = []
        current_length = 0

        while index < len(blocks):
            block_text = blocks[index]["text"]
            projected = current_length + len(block_text) + (2 if current_blocks else 0)

            if current_blocks and projected > max_chars and current_length >= min_chars:
                break

            current_blocks.append(blocks[index])
            current_length = projected
            index += 1

            if current_length >= max_chars:
                break

        if not current_blocks:
            current_blocks.append(blocks[index])
            index += 1

        end_index = index - 1
        chunk_text = "\n\n".join(block["text"] for block in current_blocks).strip()
        chunk_start = current_blocks[0]["start"]
        chunk_end = current_blocks[-1]["end"]

        chunks.append(
            {
                "chunk_index": len(chunks),
                "text": chunk_text,
                "char_start": chunk_start,
                "char_end": chunk_end,
                "source_block_start": start_index,
                "source_block_end": end_index,
                "char_length": len(chunk_text),
                "sha1": sha1_text(chunk_text),
            }
        )

        if index >= len(blocks):
            break

        overlap_index = end_index
        overlap_total = len(blocks[overlap_index]["text"])
        while overlap_index > start_index and overlap_total < overlap_chars:
            overlap_index -= 1
            overlap_total += len(blocks[overlap_index]["text"]) + 2

        index = max(overlap_index, start_index + 1)

    return chunks


def load_chunk_manifest(book_dir: Path) -> dict[str, Any]:
    manifest_path = book_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Chunk manifest not found: {manifest_path}")
    return read_json(manifest_path)


def normalize_for_comparison(text: str) -> str:
    normalized = normalize_newlines(text).lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def split_paragraphs(text: str) -> list[str]:
    normalized = normalize_newlines(text)
    if not normalized:
        return []
    return [paragraph.strip() for paragraph in re.split(r"\n{2,}", normalized) if paragraph.strip()]


def merge_markdown_with_overlap(previous_text: str, next_text: str) -> tuple[str, dict[str, Any]]:
    previous_paragraphs = split_paragraphs(previous_text)
    next_paragraphs = split_paragraphs(next_text)

    max_paragraphs = min(len(previous_paragraphs), len(next_paragraphs), 12)
    matched_paragraphs = 0

    for size in range(max_paragraphs, 0, -1):
        previous_slice = previous_paragraphs[-size:]
        next_slice = next_paragraphs[:size]
        if [normalize_for_comparison(item) for item in previous_slice] == [
            normalize_for_comparison(item) for item in next_slice
        ]:
            matched_paragraphs = size
            break

    if matched_paragraphs:
        trimmed_next = "\n\n".join(next_paragraphs[matched_paragraphs:]).strip()
        merged = previous_text.strip()
        if trimmed_next:
            merged = f"{merged}\n\n{trimmed_next}"
        return merged, {"matched_paragraphs": matched_paragraphs, "matched_characters": None}

    previous_clean = normalize_newlines(previous_text)
    next_clean = normalize_newlines(next_text)
    window = min(len(previous_clean), len(next_clean), 2000)

    matched_chars = 0
    for size in range(window, 79, -1):
        if previous_clean[-size:] == next_clean[:size]:
            matched_chars = size
            break

    if matched_chars:
        merged = previous_clean + next_clean[matched_chars:]
        return merged.strip(), {"matched_paragraphs": 0, "matched_characters": matched_chars}

    merged = previous_clean
    if next_clean:
        merged = f"{merged}\n\n{next_clean}"
    return merged.strip(), {"matched_paragraphs": 0, "matched_characters": 0}
