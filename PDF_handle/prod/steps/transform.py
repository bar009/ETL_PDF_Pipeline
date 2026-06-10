from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.books import load_chunk_manifest
from PDF_handle.prod.core.io import ensure_dir, read_text, utc_timestamp, write_json, write_text
from PDF_handle.prod.core.paths import DEFAULT_CHUNKED_DIR, DEFAULT_PROMPTS_DIR, DEFAULT_TRANSFORMED_DIR
from PDF_handle.prod.core.text import sha1_text
from PDF_handle.prod.providers import generate_text_content


DEFAULT_USER_PROMPT_TEMPLATE = """Convert the following extracted book chunk into display-ready markdown.

Requirements:
- Preserve all factual content from the source chunk.
- Do not summarize.
- Keep names, dates, examples, lists, and quoted language.
- Preserve the original sequence of ideas.
- Do not add new facts.
- If the chunk begins or ends mid-topic, do not add artificial introductions or conclusions.

Chunk metadata:
- Book: {book_name}
- Chunk: {chunk_id}
- Source markdown path: {source_markdown_path}
- Character span: {char_start}..{char_end}

Source chunk:
```markdown
{chunk_text}
```"""

TRANSFORM_THINKING_BUDGET = 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Step 3: transform chunks with an LLM and persist per-chunk outputs."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_CHUNKED_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_TRANSFORMED_DIR)
    parser.add_argument("--book", help="Optional book directory name from chunked_books.")
    parser.add_argument(
        "--provider",
        choices=["gemini", "dry-run"],
        default="dry-run",
        help="Use dry-run for pipeline testing without API calls.",
    )
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--prompt-file", type=Path, default=DEFAULT_PROMPTS_DIR / "archivist_system.txt")
    parser.add_argument("--api-key-env", default="GEMINI_API_KEY")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument(
        "--retry-max-delay",
        type=float,
        default=90.0,
        help="Upper bound for backoff delay between retries.",
    )
    parser.add_argument(
        "--retry-forever",
        action="store_true",
        help="Keep retrying transient provider failures instead of aborting the full run.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run chunk transformations even if output files already exist.",
    )
    return parser


def is_transient_transform_error(exc: Exception) -> bool:
    message = str(exc).lower()
    transient_markers = (
        "http 429",
        "http 500",
        "http 502",
        "http 503",
        "http 504",
        "status\": \"unavailable\"",
        "temporarily unavailable",
        "network error",
        "timed out",
        "timeout",
        "connection reset",
    )
    return any(marker in message for marker in transient_markers)


def compute_retry_delay(*, base_delay: float, attempt: int, retryable: bool, max_delay: float) -> float:
    if retryable:
        delay = base_delay * (2 ** max(attempt - 1, 0))
    else:
        delay = base_delay * max(attempt, 1)
    return min(delay, max_delay)


def transform_with_gemini(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
    api_key: str | None,
) -> dict[str, Any]:
    return generate_text_content(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        api_key=api_key,
        thinking_budget=TRANSFORM_THINKING_BUDGET,
    )


def transform_with_dry_run(*, chunk_text: str) -> dict[str, Any]:
    return {
        "response_text": chunk_text.strip(),
        "usage_metadata": None,
        "transport": "dry-run",
    }


def main() -> None:
    args = build_parser().parse_args()
    prompt_path = args.prompt_file.resolve()
    system_prompt = read_text(prompt_path).strip()
    api_key = os.getenv(args.api_key_env)

    input_dir = args.input_dir.resolve()
    book_dirs = sorted(path for path in input_dir.iterdir() if path.is_dir())
    if args.book:
        book_dirs = [path for path in book_dirs if path.name == args.book]
    if not book_dirs:
        raise SystemExit(f"No chunk manifests found in {input_dir}")

    for book_dir in book_dirs:
        manifest = load_chunk_manifest(book_dir)
        book_name = manifest["book_name"]
        output_book_dir = args.output_dir.resolve() / book_name
        transformed_chunks_dir = ensure_dir(output_book_dir / "chunks")
        records_dir = ensure_dir(output_book_dir / "records")

        transformed_chunks: list[dict[str, Any]] = []

        last_chunk_index = len(manifest["chunks"]) - 1
        for loop_index, chunk in enumerate(manifest["chunks"]):
            chunk_id = chunk["chunk_id"]
            source_chunk_path = book_dir / chunk["relative_path"]
            output_chunk_path = transformed_chunks_dir / f"{chunk_id}.md"
            record_path = records_dir / f"{chunk_id}.json"

            if output_chunk_path.exists() and record_path.exists() and not args.force:
                print(f"[skip] {book_name}/{chunk_id}")
                transformed_chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "chunk_index": chunk["chunk_index"],
                        "markdown_path": str(output_chunk_path.resolve()),
                        "record_path": str(record_path.resolve()),
                    }
                )
                continue

            chunk_text = read_text(source_chunk_path).strip()
            user_prompt = DEFAULT_USER_PROMPT_TEMPLATE.format(
                book_name=book_name,
                chunk_id=chunk_id,
                source_markdown_path=manifest["source_markdown_path"],
                char_start=chunk["char_start"],
                char_end=chunk["char_end"],
                chunk_text=chunk_text,
            )

            result = None
            attempt = 0
            while True:
                attempt += 1
                try:
                    if args.provider == "gemini":
                        result = transform_with_gemini(
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            model=args.model,
                            temperature=args.temperature,
                            max_output_tokens=args.max_output_tokens,
                            api_key=api_key,
                        )
                    else:
                        result = transform_with_dry_run(chunk_text=chunk_text)
                    break
                except Exception as exc:
                    retryable = is_transient_transform_error(exc)
                    exhausted = attempt >= args.max_retries and not (retryable and args.retry_forever)
                    if exhausted:
                        raise RuntimeError(f"Failed on {book_name}/{chunk_id}: {exc}") from exc
                    delay = compute_retry_delay(
                        base_delay=args.sleep_seconds,
                        attempt=attempt,
                        retryable=retryable,
                        max_delay=args.retry_max_delay,
                    )
                    retry_label = "retry-forever" if retryable and args.retry_forever else "retry"
                    print(f"[{retry_label}] {book_name}/{chunk_id} attempt {attempt} failed: {exc}")
                    time.sleep(delay)

            transformed_markdown = result["response_text"].strip() + "\n"
            write_text(output_chunk_path, transformed_markdown)

            record = {
                "book_name": book_name,
                "chunk_id": chunk_id,
                "chunk_index": chunk["chunk_index"],
                "provider": args.provider,
                "model": args.model if args.provider == "gemini" else "dry-run",
                "created_at": utc_timestamp(),
                "system_prompt_path": str(prompt_path),
                "system_prompt_sha1": sha1_text(system_prompt),
                "user_prompt_sha1": sha1_text(user_prompt),
                "source_chunk_path": str(source_chunk_path.resolve()),
                "output_chunk_path": str(output_chunk_path.resolve()),
                "char_start": chunk["char_start"],
                "char_end": chunk["char_end"],
                "usage_metadata": result["usage_metadata"],
                "transport": result.get("transport"),
                "thinking_budget": TRANSFORM_THINKING_BUDGET if args.provider == "gemini" else None,
            }
            write_json(record_path, record)

            transformed_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "chunk_index": chunk["chunk_index"],
                    "markdown_path": str(output_chunk_path.resolve()),
                    "record_path": str(record_path.resolve()),
                }
            )

            print(f"[transformed] {book_name}/{chunk_id}")
            if loop_index < last_chunk_index:
                time.sleep(args.sleep_seconds)

        output_manifest = {
            "book_name": book_name,
            "created_at": utc_timestamp(),
            "provider": args.provider,
            "model": args.model if args.provider == "gemini" else "dry-run",
            "source_manifest_path": str((book_dir / "manifest.json").resolve()),
            "transformed_chunk_count": len(transformed_chunks),
            "chunks": sorted(transformed_chunks, key=lambda item: item["chunk_index"]),
        }
        write_json(output_book_dir / "manifest.json", output_manifest)


if __name__ == "__main__":
    main()
