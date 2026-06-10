from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import argparse
import copy
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from common import TOOLS_DIR, log, resolve_report_dir
from pipeline_utils import build_site_data_paths, read_json, safe_json_write, utc_timestamp, write_json, write_text


TOOL_NAME = "phase_k_level1_refill"
DEFAULT_MANIFEST = TOOLS_DIR / "knowledge_flow_waves" / "level1.full-production-pilot.json"
DEFAULT_BATCH_SIZE = 8
MIN_SUMMARY_CHARS = 300
MIN_LAYER_CHARS = 110
MIN_FIELD_SENTENCES = 2

CLEAN_COMPLETION_NOTE = (
    "×¢×¨×™×›×ª ×ª×•×›×Ÿ ×¤× ×™×ž×™×ª: ×”×¢×¨×š × ×•×¡×— ×ž×—×“×© ×ž×ª×•×š ×ª×›× ×™ level1 ×”×§×™×™×ž×™×, ×‘×œ×™ ×œ×”×•×¡×™×£ ×—×•×ž×¨ ×—×™×¦×•× ×™ "
    "×•×‘×œ×™ ×œ×—×¨×•×’ ×ž×’×‘×•×œ×•×ª ×”×“×¨×’×” ×”×¨××©×•× ×”."
)

TEXT_BLOCK_PATTERNS = (
    re.compile(r"<!--\s*PDF_STAGE5:.*?-->.*?<!--\s*/PDF_STAGE5:.*?-->", re.DOTALL | re.IGNORECASE),
    re.compile(r"<!--\s*PDF_STAGE5:.*?-->", re.DOTALL | re.IGNORECASE),
    re.compile(r"<!--\s*/PDF_STAGE5:.*?-->", re.DOTALL | re.IGNORECASE),
)

LINE_DROP_PATTERNS = (
    re.compile(r"^\s*###\s*×”×¢×©×¨×” ×ž×ž×•×§×“×ª ×ž×ž×§×•×¨×•×ª ×ž×™×•×‘××™×\s*$"),
    re.compile(r"^\s*×¢×¨×š ×™×¢×“:.*$"),
    re.compile(r"^\s*×ž×‘×•×¡×¡ ×¢×œ:.*$"),
    re.compile(r"^\s*Duncan'?s.*$", re.IGNORECASE),
    re.compile(r"^\s*Blue Lodge.*$", re.IGNORECASE),
    re.compile(r"^\s*The Text Book of Freemasonry.*$", re.IGNORECASE),
    re.compile(r"^\s*[A-Za-z]:\\\\.*$"),
)

SOURCE_NOTE_ARTIFACT_PATTERNS = (
    re.compile(r"[A-Za-z]:\\\\"),
    re.compile(r"\.md(?:#|$)", re.IGNORECASE),
    re.compile(r"\bsection\s+\d+\b", re.IGNORECASE),
    re.compile(r"Duncan'?s|Blue Lodge|Text Book of Freemasonry", re.IGNORECASE),
    re.compile(r"data/improvments\.txt", re.IGNORECASE),
)

FORBIDDEN_SENTENCE_PATTERNS = (
    re.compile(r"\broyal arch\b", re.IGNORECASE),
    re.compile(r"×§×©×ª ×ž×œ×›×•×ª×™×ª"),
    re.compile(r"×”×ž×™×œ×” ×”××‘×•×“×”"),
    re.compile(r"\blost word\b", re.IGNORECASE),
    re.compile(r"\bhiram\b", re.IGNORECASE),
    re.compile(r"×—×™×¨×"),
    re.compile(r"\bfellow craft\b", re.IGNORECASE),
    re.compile(r"×¢×ž×™×ª ×‘×•× ×”"),
    re.compile(r"\bmaster mason\b", re.IGNORECASE),
    re.compile(r"×¨×‘ ×‘×•× ×”"),
    re.compile(r"×¨×‘ ××ž×Ÿ"),
    re.compile(r"×“×¨×’×” ×©× ×™×™×”"),
    re.compile(r"×“×¨×’×” ×©×œ×™×©×™×ª"),
    re.compile(r"×“×¨×’×” 2"),
    re.compile(r"×“×¨×’×” 3"),
    re.compile(r"×“×¨×’×” ×”×‘××”"),
    re.compile(r"×”×“×¨×’×•×ª ×”×‘××•×ª"),
    re.compile(r"×¢×ž×™×ª ×ž×œ××›×”"),
    re.compile(r"××•×¨ × ×•×¡×£"),
    re.compile(r"×ž×“×¢×™× ×’×‘×•×”×™× ×™×•×ª×¨"),
    re.compile(r"×©×œ×•×©×ª ×©×œ×‘×™ ×—×™×™ ×”××“×"),
    re.compile(r"×¡×•×“×•×ª ×©××™×Ÿ ×œ×‘×˜××"),
    re.compile(r"\bcompletion\b", re.IGNORECASE),
    re.compile(r"\bknowledge narrative", re.IGNORECASE),
)

SUMMARY_CATEGORY_SENTENCES = {
    "gate": "×‘×ª×•×š level1 ×–×”×• ×©×¢×¨ ×©×œ ×›×•×•× ×”, ×‘×™×¨×•×¨ ×•×”×ª×™×™×¦×‘×•×ª × ×›×•× ×” ×œ×¤× ×™ ×”×”×ž×©×š.",
    "preparation": "×‘×ª×•×š ×ž×¡×’×¨×ª ×”×”×›× ×” ×”×“×’×© ××™× × ×• ×¢×œ ×“×¨×ž×” ×—×™×¦×•× ×™×ª ××œ× ×¢×œ ×¨×¦×™× ×•×ª, ×¤×©×˜×•×ª ×•×ž×•×›× ×•×ª.",
    "ritual_flow": "×‘×ª×•×š ×ž×”×œ×š ×”×˜×§×¡ ×”×¨×¢×™×•×Ÿ ×”×–×” ×ž×¡×“×¨ ××ª ×”×ž×¢×‘×¨ ×©×œ×‘ ××—×¨ ×©×œ×‘ ×‘×œ×™ ×œ×”×¤×•×š ××•×ª×• ×œ×¨×©×™×ž×ª ×¤×¨×˜×™× ×™×‘×©×”.",
    "lodge_structure": "×‘×”×§×©×¨ ×©×œ ×”×œ×©×›×”, ×”×¢×¨×š ×ž×¡×‘×™×¨ ××™×š ×¡×“×¨ ×”×ž×§×•× ×•×ª×¤×§×™×“×™ ×”×ž×¨×—×‘ ×ª×•×ž×›×™× ×‘×¨×™×›×•×– ×•×‘×”×‘× ×”.",
    "degree_board": "×‘×”×§×©×¨ ×©×œ ×œ×•×— ×”×“×¨×’×”, ×”×¢×¨×š ×¢×•×–×¨ ×œ×§×¨×•× ×¤×¨×˜ ××—×“ ×›×—×œ×§ ×ž×ª×ž×•× ×” ×¡×ž×œ×™×ª ×©×œ×ž×”.",
    "tools_and_signs": "×‘×”×§×©×¨ ×©×œ ×”×›×œ×™× ×•×”×ª× ×•×¢×•×ª, ×”×¢×¨×š ×ž×“×’×™×© ×ž×©×ž×¢×ª, ×–×™×”×•×™ × ×›×•×Ÿ ×•×”×¤× ×ž×” ×“×¨×š ×ž×¢×©×”.",
    "obligation_and_law": "×‘×”×§×©×¨ ×©×œ ×”×”×ª×—×™×™×‘×•×ª, ×”×¢×¨×š ×ž×—×‘×¨ ×‘×™×Ÿ ×’×‘×•×œ, × ××ž× ×•×ª ×•××—×¨×™×•×ª ×ž×•×“×¢×ª.",
    "inner_work": "×‘×”×§×©×¨ ×©×œ ×”×¢×‘×•×“×” ×”×¤× ×™×ž×™×ª, ×”×“×’×© ×¢×•×‘×¨ ×ž×Ÿ ×”×ž×™×“×¢ ××œ ×¢×™×¦×•×‘ ×”××•×¤×™ ×•×”×”×¨×’×œ.",
    "glossary_and_review": "×›×¢×¨×š ×¢×–×¨, ×ž×˜×¨×ª×• ×œ×™×™×¦×‘ ×©×¤×”, ×¡×“×¨ ×•×–×›×™×¨×” ×—×•×–×¨×ª ×©×œ ×¢×™×§×¨×™ ×”×“×‘×¨×™×.",
}

SYMBOLIC_CATEGORY_SENTENCES = {
    "gate": "×‘×¨×•×‘×“ ×”×¡×ž×œ×™ ×–×”×• ×ž×¢×‘×¨ ×ž×Ÿ ×”×—×•×¥ ××œ ×¢×ž×“×ª ×œ×™×ž×•×“ ×§×©×•×‘×” ×•×ž×›×•×•× ×ª.",
    "preparation": "×‘×¨×•×‘×“ ×”×¡×ž×œ×™ ×”×”×›× ×” ×ž×“×’×™×©×” ×¤×™×©×•×˜, ×›× ×•×ª ×•×ž×•×›× ×•×ª ×œ×¢×‘×•×¨ ×ž×Ÿ ×”×—×™×¦×•× ×™ ××œ ×”×¤× ×™×ž×™.",
    "ritual_flow": "×‘×¨×•×‘×“ ×”×¡×ž×œ×™ ×–×”×• ×¡×™×ž×•×Ÿ ×©×œ ×¡×“×¨ ×¤× ×™×ž×™: ×œ× ×¨×§ ×ž×” ×§×•×¨×”, ××œ× ×‘××™×–×” ××•×¤×Ÿ ×”××“× × ×›× ×¡ ××œ×™×•.",
    "lodge_structure": "×‘×¨×•×‘×“ ×”×¡×ž×œ×™ ×”×ž×¨×—×‘ ×ž×œ×ž×“ ×©×”×‘× ×” × ×‘× ×™×ª ×’× ×ž×ª×•×š ×¡×“×¨, ×ž×™×§×•× ×•×™×—×¡ × ×›×•×Ÿ ×‘×™×Ÿ ×—×œ×§×™×.",
    "degree_board": "×‘×¨×•×‘×“ ×”×¡×ž×œ×™ ×”×¤×¨×˜ ×”×–×” ×ž×›×•×•×Ÿ ××ª ×”×ž×‘×˜ ×œ×ž×¡×’×¨×ª, ×œ×ž×™×“×” ×•×œ×™×—×¡ ×‘×™×Ÿ ×—×œ×§×™ ×”×ª×ž×•× ×”.",
    "tools_and_signs": "×‘×¨×•×‘×“ ×”×¡×ž×œ×™ ×”×›×œ×™ ××• ×”×ª× ×•×¢×” ×ž×ª×¨×’×ž×™× ×¨×¢×™×•×Ÿ ×ž×•×¤×©×˜ ×œ×”×¨×’×œ ×©×œ ×ª×©×•×ž×ª ×œ×‘ ×•×©×œ×™×˜×” ×¢×¦×ž×™×ª.",
    "obligation_and_law": "×‘×¨×•×‘×“ ×”×¡×ž×œ×™ ×”×’×‘×•×œ ××™× × ×• ×¢×•× ×© ×—×™×¦×•× ×™ ××œ× ×¦×•×¨×” ×©×œ ××—×¨×™×•×ª ×ž×•×“×¢×ª.",
    "inner_work": "×‘×¨×•×‘×“ ×”×¡×ž×œ×™ ×–×”×• ×ª×¨×’×•×œ ×©×œ ×”×§×©×‘×” ×¤× ×™×ž×™×ª, ×“×™×•×§ ×•×¢×ž×™×“×” ×‘×’×‘×•×œ × ×›×•×Ÿ.",
    "glossary_and_review": "×‘×¨×•×‘×“ ×”×¡×ž×œ×™ ×¢×¦× ×”×—×–×¨×” ×ž×œ×ž×“×ª ×¢× ×•×•×” ×œ×™×ž×•×“×™×ª ×•×¨×¦×•×Ÿ ×œ×“×™×™×§.",
}

LESSON_CATEGORY_SENTENCES = {
    "gate": "×ž×‘×—×™× ×ª ×”×ž×•×¢×ž×“, ×”×œ×§×— ×”×•× ×œ× ×œ×ž×”×¨ ××œ× ×œ×‘×¨×¨ ×œ×©× ×ž×” × ×›× ×¡×™× ×•×ž×” ×ž×‘×§×©×™× ×œ×œ×ž×•×“.",
    "preparation": "×ž×‘×—×™× ×ª ×”×ž×•×¢×ž×“, ×”×œ×§×— ×”×•× ×œ×”×’×™×¢ ×¤×©×•×˜, ×›×Ÿ ×•×ž×•×›×Ÿ ×œ×¢×‘×•×“×” ×¢×¦×ž×™×ª.",
    "ritual_flow": "×ž×‘×—×™× ×ª ×”×ž×•×¢×ž×“, ×”×œ×§×— ×”×•× ×œ×”×™×©××¨ × ×•×›×— ×‘×›×œ ×©×œ×‘ ×•×œ× ×œ×”×¤×•×š ××ª ×”×“×¨×š ×œ×¨×¦×£ ××•×˜×•×ž×˜×™.",
    "lodge_structure": "×ž×‘×—×™× ×ª ×”×ž×•×¢×ž×“, ×”×œ×§×— ×”×•× ×œ×›×‘×“ ×¡×“×¨, ×ž×§×•× ×•×ª×¤×§×™×“ ×›×—×œ×§ ×ž×Ÿ ×”×œ×™×ž×•×“ ×¢×¦×ž×•.",
    "degree_board": "×ž×‘×—×™× ×ª ×”×ž×•×¢×ž×“, ×”×œ×§×— ×”×•× ×œ×”×ª×‘×•× ×Ÿ ×‘×¡×ž×œ ×œ× ×¨×§ ×›×¦×™×•×¨ ××œ× ×›×”×›×•×•× ×” ×œ×—×™×™× ×ž×“×•×™×§×™× ×™×•×ª×¨.",
    "tools_and_signs": "×ž×‘×—×™× ×ª ×”×ž×•×¢×ž×“, ×”×œ×§×— ×”×•× ×©×™×“×™×¢×” × ×›×•× ×” × ×‘×—× ×ª ×‘×“×¨×š ×”×©×§×˜×” ×•×”×ž×“×•×™×§×ª ×©×‘×” ×¤×•×¢×œ×™×.",
    "obligation_and_law": "×ž×‘×—×™× ×ª ×”×ž×•×¢×ž×“, ×”×œ×§×— ×”×•× ×œ×—×™×•×ª × ××ž× ×•×ª ×•××™×¤×•×§ ×ž×ª×•×š ×‘×—×™×¨×” ×ž×•×“×¢×ª.",
    "inner_work": "×ž×‘×—×™× ×ª ×”×ž×•×¢×ž×“, ×”×œ×§×— ×”×•× ×œ×ª×¨×’× ×”×‘× ×” ×¤× ×™×ž×™×ª ×œ×”×¨×’×œ×™×, ×œ×ž×™×“×•×ª ×•×œ×‘×—×™×¨×•×ª ×™×•×ž×™×•×ž×™×•×ª.",
    "glossary_and_review": "×ž×‘×—×™× ×ª ×”×ž×•×¢×ž×“, ×”×œ×§×— ×”×•× ×œ×—×–×•×¨, ×œ× ×¡×— ×‘×ž×™×œ×™× ×¤×©×•×˜×•×ª ×•×œ×‘×“×•×§ ×ž×” ×‘××ž×ª ×”×•×‘×Ÿ.",
}

PRACTICAL_CATEGORY_SENTENCES = {
    "gate": "×œ× ×¡×— ×‘×ž×©×¤×˜ ××—×“ ×ž×” ×ž×‘×§×©×™× ×œ×”×‘×™×Ÿ ×œ×¤× ×™ ×”×ž×¢×‘×¨ ×œ×©×œ×‘ ×”×‘×.",
    "preparation": "×œ×‘×—×•×Ÿ ×× ×”×”×›× ×” × ×ª×¤×¡×ª ×œ× ×¨×§ ×›×—×™×¦×•× ×™×ª ××œ× ×’× ×›×ª×¨×’×•×œ ×©×œ ×¨×¦×™× ×•×ª ×•×ž×•×›× ×•×ª.",
    "ritual_flow": "×œ×ª××¨ ×œ××˜ ××ª ×”×¨×¦×£ ×•×œ×©××•×œ ×ž×” ×›×œ ×©×œ×‘ ×¢×•×©×” ×œ×ª×©×•×ž×ª ×”×œ×‘ ×•×œ× ×¨×§ ×ž×” ×§×•×¨×” ×‘×•.",
    "lodge_structure": "×œ×–×”×•×ª ××™×š ×¡×“×¨ ×”×ž×§×•× ×ž×©× ×” ×¨×™×›×•×–, ×™×—×¡ ×•×ª×¤×™×¡×ª ×ª×¤×§×™×“.",
    "degree_board": "×œ×”×‘×™×˜ ×‘×¤×¨×˜ ×›×—×œ×§ ×ž×ª×ž×•× ×” ×©×œ×ž×” ×•×œ×©××•×œ ××™×–×” ×’×‘×•×œ, ×™×—×¡ ××• ×›×™×•×•×Ÿ ×”×•× ×ž×“×’×™×©.",
    "tools_and_signs": "×œ×©××•×œ ××™×š ×ª× ×•×¢×”, ×›×œ×™ ××• ×ž×—×•×•×” ×ž×©× ×™× ×“×™×•×§, ××™×¤×•×§ ×•×”×‘× ×”.",
    "obligation_and_law": "×œ×‘×“×•×§ ××™×š ×’×‘×•×œ ×ž×•×¡×¨×™ ×”×•×¤×š ×ž×”×¨×’×¢ ×”×˜×§×¡×™ ×œ×”×¨×’×œ ×ž×¢×©×™.",
    "inner_work": "×œ× ×¡×— ×›×™×¦×“ ×”×¨×¢×™×•×Ÿ ×”×–×” ×ž×©× ×” ×‘×—×™×¨×”, ×ª×’×•×‘×” ××• ×”×¨×’×œ ×‘×™×•× ×¨×’×™×œ.",
    "glossary_and_review": "×œ×‘×“×•×§ ×× ××¤×©×¨ ×œ×”×¡×‘×™×¨ ××ª ×”×ž×•×©×’ ×‘×¤×©×˜×•×ª ×‘×œ×™ ×œ××‘×“ ××ª ×”×¢×™×§×¨.",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase K content-only refill and product cleanup for level1 entries."
    )
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--apply-summary", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-entries", type=int, default=None)
    parser.add_argument("--slug", action="append", default=[])
    parser.add_argument("--quiet", action="store_true")
    return parser


def normalize_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n").replace("\r", "\n")).strip()


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    token = str(value).strip()
    return [token] if token else []


def preserve_shape(original: Any, values: list[str]) -> Any:
    if isinstance(original, list):
        return values
    if not values:
        return "" if isinstance(original, str) else values
    if isinstance(original, str):
        return values[0] if len(values) == 1 else values
    return values


def ensure_terminal_punctuation(text: str) -> str:
    value = normalize_whitespace(text)
    if not value:
        return ""
    if value[-1] in ".!?":
        return value
    return f"{value}."


def split_paragraphs(text: str) -> list[str]:
    normalized = normalize_whitespace(text)
    if not normalized:
        return []
    return [part.strip() for part in re.split(r"\n{2,}", normalized) if part.strip()]


def split_sentences(text: str) -> list[str]:
    normalized = normalize_whitespace(text)
    if not normalized:
        return []
    raw_parts = re.split(r"(?<=[.!?])\s+|\n+", normalized)
    parts = [ensure_terminal_punctuation(part) for part in raw_parts if part and part.strip()]
    return [part for part in parts if part]


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = normalize_whitespace(value)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def text_has_artifact(text: str) -> bool:
    value = str(text or "")
    if not value:
        return False
    if any(pattern.search(value) for pattern in TEXT_BLOCK_PATTERNS):
        return True
    if any(pattern.search(value) for pattern in LINE_DROP_PATTERNS):
        return True
    return any(pattern.search(value) for pattern in SOURCE_NOTE_ARTIFACT_PATTERNS)


def note_has_artifact(note: str) -> bool:
    return any(pattern.search(str(note or "")) for pattern in SOURCE_NOTE_ARTIFACT_PATTERNS)


def sentence_is_forbidden(text: str) -> bool:
    value = str(text or "")
    return any(pattern.search(value) for pattern in FORBIDDEN_SENTENCE_PATTERNS)


def category_sentence(mapping: dict[str, str], category: str) -> str:
    return mapping.get(category, mapping["inner_work"])


def clean_text_field(text: Any) -> tuple[str, list[str]]:
    value = str(text or "")
    removed: list[str] = []
    for pattern in TEXT_BLOCK_PATTERNS:
        if pattern.search(value):
            removed.append("pdf_stage5_markers")
            value = pattern.sub(" ", value)

    kept_lines: list[str] = []
    for line in value.splitlines():
        stripped = line.strip()
        if not stripped:
            kept_lines.append("")
            continue
        if any(pattern.search(stripped) for pattern in LINE_DROP_PATTERNS):
            removed.append("imported_source_lines")
            continue
        kept_lines.append(stripped)

    cleaned = normalize_whitespace("\n".join(kept_lines))
    safe_sentences: list[str] = []
    for sentence in split_sentences(cleaned):
        if len(sentence) > 220:
            removed.append("oversized_pipeline_sentence")
            continue
        if text_has_artifact(sentence):
            removed.append("raw_citation_fragment")
            continue
        if sentence_is_forbidden(sentence):
            removed.append("forbidden_degree_sentence")
            continue
        safe_sentences.append(sentence)

    return " ".join(dedupe_preserve_order(safe_sentences)).strip(), sorted(set(removed))


def clean_practical_elements(values: list[str], *, category: str) -> tuple[list[str], list[str]]:
    removed: list[str] = []
    cleaned: list[str] = []
    for value in values:
        text, field_removed = clean_text_field(value)
        removed.extend(field_removed)
        if not text or sentence_is_forbidden(text) or len(text) > 160:
            if value:
                removed.append("forbidden_practical_element")
            continue
        cleaned.append(text.rstrip("."))
    cleaned = dedupe_preserve_order(cleaned)
    if not cleaned:
        cleaned = [category_sentence(PRACTICAL_CATEGORY_SENTENCES, category)]
    return cleaned[:2], sorted(set(removed))


def clean_source_notes(value: Any) -> tuple[Any, list[str]]:
    notes = as_list(value)
    removed = ["dirty_source_note"] if any(note_has_artifact(note) or note.endswith("seed.md") for note in notes) else []
    return preserve_shape(value, [CLEAN_COMPLETION_NOTE]), removed


def maybe_prefix(sentence: str, prefix: str) -> str:
    value = normalize_whitespace(sentence)
    if not value:
        return ""
    if value.startswith(prefix):
        return ensure_terminal_punctuation(value)
    return ensure_terminal_punctuation(f"{prefix}{value}")


def compose_field(
    *,
    primary_sentences: list[str],
    backup_sentences: list[str],
    fallback_sentences: list[str],
    min_chars: int,
    min_sentences: int,
    max_sentences: int,
) -> str:
    collected = dedupe_preserve_order(primary_sentences + backup_sentences)
    for fallback in fallback_sentences:
        if len(collected) >= min_sentences and len(" ".join(collected)) > min_chars:
            break
        token = ensure_terminal_punctuation(fallback)
        if token:
            collected.append(token)
        collected = dedupe_preserve_order(collected)

    if not collected:
        collected = [ensure_terminal_punctuation("×”×¢×¨×š ×“×•×¨×© × ×™×¡×•×— ×‘×”×™×¨ ×•×ž×ž×•×§×“ ×™×•×ª×¨ ×‘×ª×•×š ×’×‘×•×œ×•×ª ×”×“×¨×’×” ×”×¨××©×•× ×”.")]

    for fallback in fallback_sentences:
        if len(collected) >= min_sentences:
            break
        token = ensure_terminal_punctuation(fallback)
        if token and token not in collected:
            collected.append(token)
    if len(collected) < min_sentences:
        collected.append(ensure_terminal_punctuation("×”× ×™×¡×•×— × ×©××¨ ×¤×©×•×˜, ×¨×’×•×¢ ×•×ž×ž×•×§×“ ×‘×ª×•×š ×’×‘×•×œ×•×ª ×”×“×¨×’×” ×”×¨××©×•× ×”."))

    if len(" ".join(collected)) <= min_chars and len(collected) < max_sentences:
        for fallback in fallback_sentences:
            token = ensure_terminal_punctuation(fallback)
            if token and token not in collected:
                collected.append(token)
            if len(collected) >= max_sentences or len(" ".join(collected)) > min_chars:
                break

    return " ".join(collected[:max_sentences]).strip()


def build_full_summary(entry: dict[str, Any], cleaned: dict[str, str]) -> str:
    category = str(entry.get("category") or "").strip()
    short_sentences = split_sentences(cleaned["short_summary"])
    full_sentences = split_sentences(cleaned["full_summary"])[:3]
    symbolic_sentences = [maybe_prefix(sentence, "×‘×¨×ž×” ×”×¡×ž×œ×™×ª, ") for sentence in split_sentences(cleaned["symbolic_meaning"])[:1]]
    lesson_sentences = [maybe_prefix(sentence, "×ž×‘×—×™× ×ª ×”×ž×•×¢×ž×“, ") for sentence in split_sentences(cleaned["candidate_lesson"])[:1]]
    fallback_sentences = [
        category_sentence(SUMMARY_CATEGORY_SENTENCES, category),
        "×”×¢×¨×š × ×©××¨ ×‘×ª×•×š ×’×‘×•×œ×•×ª level1 ×•×ž×¢×ž×™×§ ×¨×§ ××ª ×”×›×™×•×•×Ÿ ×©×›×‘×¨ ×§×™×™× ×‘×•.",
    ]
    return compose_field(
        primary_sentences=full_sentences or short_sentences,
        backup_sentences=symbolic_sentences + lesson_sentences + short_sentences,
        fallback_sentences=fallback_sentences,
        min_chars=MIN_SUMMARY_CHARS,
        min_sentences=MIN_FIELD_SENTENCES,
        max_sentences=6,
    )


def build_symbolic_meaning(entry: dict[str, Any], cleaned: dict[str, str]) -> str:
    category = str(entry.get("category") or "").strip()
    symbolic_sentences = [sentence for sentence in split_sentences(cleaned["symbolic_meaning"]) if len(sentence) <= 160][:2]
    backup_sentences = [
        "×‘×¨×•×‘×“ ×”×¡×ž×œ×™ ×”×¢×¨×š ×ž×›×•×•×Ÿ ×œ×ž×¡×’×¨×ª, ×œ×’×‘×•×œ ×•×œ×›×™×•×•×Ÿ ×©×›×‘×¨ × ×•×›×—×™× ×‘×ª×•×š ×”×“×¨×’×” ×”×¨××©×•× ×”.",
        "×›×š ×”×¡×ž×œ ×¢×•×–×¨ ×œ×§×¨×•× ××ª ×”×¨×¢×™×•×Ÿ ×œ× ×›×¤×¨×˜ ×ž×‘×•×“×“ ××œ× ×›×—×œ×§ ×ž×ª×”×œ×™×š ×œ×™×ž×•×“×™ ×©×œ×.",
    ]
    fallback_sentences = [
        category_sentence(SYMBOLIC_CATEGORY_SENTENCES, category),
        "×”×ž×©×ž×¢×•×ª ×”×¡×ž×œ×™×ª ×›××Ÿ ××™× × ×” ×ž×•×¡×™×¤×” ×¡×•×“ ×—×“×© ××œ× ×ž×—×“×“×ª ×™×—×¡ × ×›×•×Ÿ, ×’×‘×•×œ ×•×ª×©×•×ž×ª ×œ×‘.",
    ]
    return compose_field(
        primary_sentences=symbolic_sentences,
        backup_sentences=backup_sentences,
        fallback_sentences=fallback_sentences,
        min_chars=MIN_LAYER_CHARS,
        min_sentences=MIN_FIELD_SENTENCES,
        max_sentences=4,
    )


def build_candidate_lesson(entry: dict[str, Any], cleaned: dict[str, str]) -> str:
    category = str(entry.get("category") or "").strip()
    lesson_sentences = [sentence for sentence in split_sentences(cleaned["candidate_lesson"]) if len(sentence) <= 180][:2]
    backup_sentences = [
        "×”×œ×§×— × ×‘×—×Ÿ ×‘××•×¤×Ÿ ×©×‘×• ×”××“× ×¤×•×¢×œ, ×ž×’×™×‘ ×•×©×•×ž×¨ ×¢×œ ×ž×¡×’×¨×ª × ×›×•× ×” ×•×œ× ×¨×§ ×‘××•×¤×Ÿ ×©×‘×• ×”×•× ×ž×‘×™×Ÿ ×¨×¢×™×•×Ÿ.",
        "×”×œ×™×ž×•×“ ×›××Ÿ ×ž×‘×§×© ×”×ª×ž×“×”, ×¡×“×¨ ×•×™×™×©×•× ×©×§×˜ ×‘×—×™×™ ×”×™×•×Ö¾×™×•×.",
    ]
    fallback_sentences = [
        category_sentence(LESSON_CATEGORY_SENTENCES, category),
        "×”×œ×§×— × ×©××¨ ×¤×©×•×˜: ×œ×”×‘×™×Ÿ, ×œ× ×”×•×’ ×‘××™×¤×•×§ ×•×œ×”×¤×•×š ×¨×¢×™×•×Ÿ ×œ×”×¨×’×œ ×ž×¢×©×™.",
    ]
    return compose_field(
        primary_sentences=lesson_sentences,
        backup_sentences=backup_sentences,
        fallback_sentences=fallback_sentences,
        min_chars=MIN_LAYER_CHARS,
        min_sentences=MIN_FIELD_SENTENCES,
        max_sentences=4,
    )


def build_short_summary(full_summary: str, existing: str) -> str:
    sentences = split_sentences(existing) or split_sentences(full_summary)
    if not sentences:
        return "×¢×¨×š level1 ×©×ž×‘×”×™×¨ ×¨×¢×™×•×Ÿ ×§×™×™× ×‘×©×¤×” ×§×¦×¨×”, × ×§×™×™×” ×•×ž×ž×•×§×“×ª."
    return " ".join(sentences[:2]).strip()[:240].rstrip()


def detect_gap_types(entry: dict[str, Any], cleaned: dict[str, str], had_artifacts: bool) -> list[str]:
    gaps: list[str] = []
    if len(cleaned["full_summary"]) < MIN_SUMMARY_CHARS or len(split_sentences(cleaned["full_summary"])) < MIN_FIELD_SENTENCES:
        gaps.append("missing_explanation")
    if len(cleaned["symbolic_meaning"]) < MIN_LAYER_CHARS or len(split_sentences(cleaned["symbolic_meaning"])) < MIN_FIELD_SENTENCES:
        gaps.append("missing_symbolic_layer")
    if len(cleaned["candidate_lesson"]) < MIN_LAYER_CHARS or len(split_sentences(cleaned["candidate_lesson"])) < MIN_FIELD_SENTENCES:
        gaps.append("missing_moral_layer")
    if len(split_paragraphs(str(entry.get("full_summary") or ""))) > 2:
        gaps.append("fragmented_structure")
    if had_artifacts:
        gaps.append("pipeline_artifact_cleanup")
    return dedupe_preserve_order(gaps)


def refill_entry(entry: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    updated = copy.deepcopy(entry)
    cleaned_fields: dict[str, str] = {}
    artifacts_removed: list[str] = []
    for field_name in ("short_summary", "full_summary", "symbolic_meaning", "candidate_lesson"):
        cleaned_fields[field_name], removed = clean_text_field(entry.get(field_name))
        artifacts_removed.extend(removed)

    clean_practicals, practical_removed = clean_practical_elements(
        as_list(entry.get("practical_elements")),
        category=str(entry.get("category") or ""),
    )
    artifacts_removed.extend(practical_removed)
    cleaned_source_notes, source_removed = clean_source_notes(entry.get("source_notes"))
    artifacts_removed.extend(source_removed)

    had_artifacts = bool(artifacts_removed)
    gap_types = detect_gap_types(entry, cleaned_fields, had_artifacts)

    new_full_summary = build_full_summary(entry, cleaned_fields)
    new_symbolic_meaning = build_symbolic_meaning(entry, cleaned_fields)
    new_candidate_lesson = build_candidate_lesson(entry, cleaned_fields)
    new_short_summary = build_short_summary(new_full_summary, cleaned_fields["short_summary"])

    fields_modified: list[str] = []
    refill_added_chars = 0
    for field_name, new_value in (
        ("short_summary", new_short_summary),
        ("full_summary", new_full_summary),
        ("symbolic_meaning", new_symbolic_meaning),
        ("candidate_lesson", new_candidate_lesson),
    ):
        before = normalize_whitespace(str(entry.get(field_name) or ""))
        after = normalize_whitespace(str(new_value or ""))
        if before != after:
            fields_modified.append(field_name)
            refill_added_chars += max(0, len(after) - len(cleaned_fields.get(field_name, before)))
            updated[field_name] = new_value

    if as_list(entry.get("practical_elements")) != clean_practicals:
        fields_modified.append("practical_elements")
        updated["practical_elements"] = clean_practicals

    source_notes_before = json.dumps(as_list(entry.get("source_notes")), ensure_ascii=False)
    source_notes_after = json.dumps(as_list(cleaned_source_notes), ensure_ascii=False)
    if normalize_whitespace(source_notes_before) != normalize_whitespace(source_notes_after):
        fields_modified.append("source_notes")
        updated["source_notes"] = cleaned_source_notes

    report_row = {
        "entry_slug": entry["slug"],
        "fields_modified": dedupe_preserve_order(fields_modified),
        "gap_types": gap_types,
        "refill_added_chars": refill_added_chars,
        "artifacts_removed": sorted(set(artifacts_removed)),
        "validation_passed": False,
    }
    return updated, report_row


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def write_level1(site_root: Path, payload: dict[str, Any]) -> None:
    site_paths = build_site_data_paths(site_root)
    safe_json_write(site_paths["level1"], payload)


def python_command() -> list[str]:
    executable = sys.executable or "python3.11"
    return [executable]


def run_command(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(command)}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return completed


def run_audit(site_root: Path, report_dir: Path) -> dict[str, Any]:
    command = python_command() + [
        str(TOOLS_DIR / "audit_sparse_entries.py"),
        "--site-root",
        str(site_root.resolve()),
        "--report-dir",
        str(report_dir.resolve()),
        "--degrees",
        "level1",
        "--completion-mode",
        "product_clean",
        "--quiet",
    ]
    run_command(command, cwd=TOOLS_DIR.parent.parent)
    return read_json(report_dir / "audit_sparse_summary.json")


def run_f2(site_root: Path, manifest: Path, slugs: list[str], report_dir: Path) -> dict[str, Any]:
    command = python_command() + [
        str(TOOLS_DIR / "semantic_system_purity_review.py"),
        "--site-root",
        str(site_root.resolve()),
        "--manifest",
        str(manifest.resolve()),
        "--report-dir",
        str(report_dir.resolve()),
        "--provider",
        "heuristic",
        "--provider-policy",
        "heuristic_only",
        "--quiet",
    ]
    for slug in slugs:
        command.extend(["--slug", slug])
    run_command(command, cwd=TOOLS_DIR.parent.parent)
    return read_json(report_dir / "semantic_purity_summary.json")


def run_f3(site_root: Path, manifest: Path, slugs: list[str], f2_report_dir: Path, report_dir: Path) -> dict[str, Any]:
    command = python_command() + [
        str(TOOLS_DIR / "content_routing_review.py"),
        "--f2-report-dir",
        str(f2_report_dir.resolve()),
        "--site-root",
        str(site_root.resolve()),
        "--manifest",
        str(manifest.resolve()),
        "--report-dir",
        str(report_dir.resolve()),
        "--provider",
        "heuristic",
        "--provider-policy",
        "heuristic_only",
        "--quiet",
    ]
    for slug in slugs:
        command.extend(["--slug", slug])
    run_command(command, cwd=TOOLS_DIR.parent.parent)
    return read_json(report_dir / "content_routing_summary.json")


def compare_validation(before: dict[str, Any], after: dict[str, Any], keys: list[str]) -> list[str]:
    issues: list[str] = []
    for key in keys:
        before_value = float(before.get(key, 0) or 0)
        after_value = float(after.get(key, 0) or 0)
        if after_value > before_value:
            issues.append(f"{key} increased from {before_value:g} to {after_value:g}")
    return issues


def render_report(summary: dict[str, Any], batches: list[dict[str, Any]], entry_reports: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase K Level1 Refill Report",
        "",
        f"- Created at: `{summary['created_at']}`",
        f"- Site root: `{summary['site_root']}`",
        f"- Entries targeted: `{summary['entries_targeted']}`",
        f"- Entries modified: `{summary['entries_modified']}`",
        f"- Initial remaining sparse: `{summary['initial_remaining_sparse_count']}`",
        f"- Final remaining sparse: `{summary['final_remaining_sparse_count']}`",
        f"- Final audit status: `{summary['final_audit_status']}`",
        "",
        "## Batches",
        "",
    ]
    for batch in batches:
        validation = batch["validation"]
        lines.extend(
            [
                f"### Batch `{batch['batch_id']}`",
                f"- Slugs: {', '.join(batch['slugs'])}",
                f"- Audit remaining sparse: `{validation['audit_remaining_sparse_count']}`",
                f"- F2 issues: {', '.join(validation['f2_issues']) or 'none'}",
                f"- F3 issues: {', '.join(validation['f3_issues']) or 'none'}",
                f"- Validation passed: `{validation['passed']}`",
                "",
            ]
        )

    lines.extend(["## Sample Entry Reports", ""])
    for row in entry_reports[:20]:
        lines.extend(
            [
                f"### `{row['entry_slug']}`",
                f"- Fields modified: {', '.join(row['fields_modified']) or 'none'}",
                f"- Gap types: {', '.join(row['gap_types']) or 'none'}",
                f"- Added chars: `{row['refill_added_chars']}`",
                f"- Artifacts removed: {', '.join(row['artifacts_removed']) or 'none'}",
                f"- Validation passed: `{row['validation_passed']}`",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    args = build_parser().parse_args()
    site_root = args.site_root.resolve()
    audit_dir = args.audit_dir.resolve()
    apply_summary_path = args.apply_summary.resolve()
    manifest_path = args.manifest.resolve()
    report_dir = resolve_report_dir(
        tool_name=TOOL_NAME,
        report_dir=args.report_dir.resolve() if args.report_dir else None,
        site_root=site_root,
    )

    site_paths = build_site_data_paths(site_root)
    level1_data = read_json(site_paths["level1"])
    initial_audit_summary = read_json(audit_dir / "audit_sparse_summary.json")
    apply_summary = read_json(apply_summary_path)

    backup_dir = report_dir / "backups"
    write_json(backup_dir / "level1.before.json", level1_data)
    write_json(
        report_dir / "inputs.json",
        {
            "created_at": utc_timestamp(),
            "audit_dir": str(audit_dir),
            "apply_summary_path": str(apply_summary_path),
            "manifest_path": str(manifest_path),
            "initial_audit_summary": initial_audit_summary,
            "apply_summary": apply_summary,
        },
    )

    target_slugs = [entry["slug"] for entry in level1_data.get("entries", [])]
    if args.slug:
        requested = set(args.slug)
        target_slugs = [slug for slug in target_slugs if slug in requested]
    if args.max_entries is not None:
        target_slugs = target_slugs[: args.max_entries]

    slug_batches = chunked(target_slugs, args.batch_size)
    all_entry_reports: list[dict[str, Any]] = []
    batch_reports: list[dict[str, Any]] = []

    log(
        f"[start] site_root={site_root} target_entries={len(target_slugs)} batches={len(slug_batches)}",
        quiet=args.quiet,
    )

    for batch_index, slugs in enumerate(slug_batches, start=1):
        batch_id = f"batch-{batch_index:02d}"
        batch_dir = report_dir / batch_id
        before_f2_dir = batch_dir / "validation" / "f2_before"
        before_f3_dir = batch_dir / "validation" / "f3_before"
        after_f2_dir = batch_dir / "validation" / "f2_after"
        after_f3_dir = batch_dir / "validation" / "f3_after"
        audit_after_dir = batch_dir / "validation" / "audit_after"

        log(f"[batch] {batch_id} slugs={len(slugs)}", quiet=args.quiet)

        f2_before = run_f2(site_root, manifest_path, slugs, before_f2_dir)
        f3_before = run_f3(site_root, manifest_path, slugs, before_f2_dir, before_f3_dir)

        current_data = read_json(site_paths["level1"])
        slug_to_entry = {entry["slug"]: entry for entry in current_data.get("entries", [])}
        batch_entry_reports: list[dict[str, Any]] = []
        for slug in slugs:
            updated_entry, report_row = refill_entry(slug_to_entry[slug])
            batch_entry_reports.append(report_row)
            all_entry_reports.append(report_row)
            slug_to_entry[slug] = updated_entry

        current_data["entries"] = [slug_to_entry.get(entry["slug"], entry) for entry in current_data.get("entries", [])]
        write_level1(site_root, current_data)

        f2_after = run_f2(site_root, manifest_path, slugs, after_f2_dir)
        f3_after = run_f3(site_root, manifest_path, slugs, after_f2_dir, after_f3_dir)
        audit_after = run_audit(site_root, audit_after_dir)

        f2_issues = compare_validation(
            f2_before,
            f2_after,
            [
                "later_degree_leakage_detected_count",
                "cross_degree_collision_count",
                "provider_invoked_units",
                "malformed_json_count",
            ],
        )
        f3_issues = compare_validation(
            f3_before,
            f3_after,
            [
                "provider_invoked_units",
                "malformed_json_count",
                "routing_conflict_count",
            ],
        )
        passed = not f2_issues and not f3_issues
        for row in batch_entry_reports:
            row["validation_passed"] = passed

        batch_summary = {
            "batch_id": batch_id,
            "slugs": slugs,
            "entry_reports": batch_entry_reports,
            "validation": {
                "f2_before": f2_before,
                "f2_after": f2_after,
                "f3_before": f3_before,
                "f3_after": f3_after,
                "audit_after_summary": audit_after,
                "audit_remaining_sparse_count": audit_after.get("needs_refill_count", 0),
                "f2_issues": f2_issues,
                "f3_issues": f3_issues,
                "passed": passed,
            },
        }
        batch_reports.append(batch_summary)
        write_json(batch_dir / "phase_k_batch_summary.json", batch_summary)

        if not passed:
            raise SystemExit(f"Phase K validation failed in {batch_id}: {f2_issues + f3_issues}")

    final_audit_dir = report_dir / "final_audit"
    final_audit = run_audit(site_root, final_audit_dir)
    final_summary = {
        "created_at": utc_timestamp(),
        "site_root": str(site_root),
        "entries_targeted": len(target_slugs),
        "entries_modified": len([row for row in all_entry_reports if row["fields_modified"]]),
        "initial_remaining_sparse_count": initial_audit_summary.get("needs_refill_count"),
        "final_remaining_sparse_count": final_audit.get("needs_refill_count"),
        "final_audit_status": final_audit.get("status"),
        "final_artifact_entry_count": final_audit.get("artifact_entry_count"),
    }

    write_json(report_dir / "phase_k_summary.json", final_summary)
    write_json(report_dir / "phase_k_entry_reports.json", all_entry_reports)
    write_text(report_dir / "PHASE_K_REPORT.md", render_report(final_summary, batch_reports, all_entry_reports))
    write_json(report_dir / "level1.after.snapshot.json", read_json(site_paths["level1"]))

    log(
        f"[done] status={final_summary['final_audit_status']} remaining_sparse={final_summary['final_remaining_sparse_count']} report={report_dir}",
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()

