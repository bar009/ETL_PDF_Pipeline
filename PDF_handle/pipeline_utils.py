from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workspace_paths import get_live_site_root


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SITE_ROOT = get_live_site_root()
DEFAULT_PDF_DIR = BASE_DIR / "PDF_files"
DEFAULT_EXTRACTED_DIR = BASE_DIR / "extracted_books"
DEFAULT_CHUNKED_DIR = BASE_DIR / "chunked_books"
DEFAULT_TRANSFORMED_DIR = BASE_DIR / "transformed_books"
DEFAULT_CONSOLIDATED_DIR = BASE_DIR / "consolidated_books"
DEFAULT_PROMPTS_DIR = BASE_DIR / "prompts"
ATOMIC_REPLACE_ATTEMPTS = 5
ATOMIC_REPLACE_RETRY_SECONDS = 0.1


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_site_data_paths(site_root: Path) -> dict[str, Path]:
    site_root = site_root.resolve()
    data_dir = site_root / "data"
    return {
        "site_root": site_root,
        "data_dir": data_dir,
        "schema": data_dir / "content.schema.json",
        "library": data_dir / "library.json",
        "level1": data_dir / "level1.json",
        "level2": data_dir / "level2.json",
        "level3": data_dir / "level3.json",
    }


def describe_missing_site_data_paths(site_paths: dict[str, Path]) -> str:
    required_paths = (
        ("data_dir", site_paths["data_dir"]),
        ("schema", site_paths["schema"]),
        ("library", site_paths["library"]),
        ("level1", site_paths["level1"]),
        ("level2", site_paths["level2"]),
    )
    missing = [f"{label}={path.resolve()}" for label, path in required_paths if not path.exists()]
    if not missing:
        return ""
    return f"Site root {site_paths['site_root']} is missing required data paths: {', '.join(missing)}"


def build_file_fingerprint(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    stats = resolved.stat()
    return {
        "path": str(resolved),
        "size": stats.st_size,
        "mtime": stats.st_mtime,
        "mtime_iso": datetime.fromtimestamp(stats.st_mtime, timezone.utc).replace(microsecond=0).isoformat(),
    }


def build_site_data_fingerprints(site_paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    missing_message = describe_missing_site_data_paths(site_paths)
    if missing_message:
        raise FileNotFoundError(missing_message)
    return {
        "schema": build_file_fingerprint(site_paths["schema"]),
        "library": build_file_fingerprint(site_paths["library"]),
        "level1": build_file_fingerprint(site_paths["level1"]),
        "level2": build_file_fingerprint(site_paths["level2"]),
        **(
            {"level3": build_file_fingerprint(site_paths["level3"])}
            if site_paths["level3"].exists()
            else {}
        ),
    }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text_direct(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def atomic_write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    temp_path: Path | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
        temp_path = Path(temp_name)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(ATOMIC_REPLACE_ATTEMPTS):
            try:
                os.replace(temp_path, path)
                temp_path = None
                break
            except PermissionError:
                if attempt >= ATOMIC_REPLACE_ATTEMPTS - 1:
                    _write_text_direct(path, content)
                    temp_path.unlink(missing_ok=True)
                    temp_path = None
                    break
                time.sleep(ATOMIC_REPLACE_RETRY_SECONDS * (attempt + 1))
    except Exception:
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def atomic_write_json(path: Path, data: Any) -> None:
    try:
        serialized = json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ) + "\n"
    except TypeError as exc:
        raise TypeError(f"JSON payload for {path} is not serializable: {exc}") from exc
    except ValueError as exc:
        raise ValueError(f"JSON payload for {path} is invalid: {exc}") from exc
    atomic_write_text(path, serialized)


def safe_json_write(path: Path, data: Any) -> None:
    atomic_write_json(path, data)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def normalize_newlines(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.strip()


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
