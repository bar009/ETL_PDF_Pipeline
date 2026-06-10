from __future__ import annotations

import sys
from pathlib import Path

# Classification: ops-lane
# Canonical prod ETL ownership does not live here. This is an operational
# refill lane that may consume prod-owned contracts.

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import argparse
import json
import os
import re
import time
from html import escape
from pathlib import Path
from typing import Any

from audit_sparse_entries import CATEGORY_HINTS
from common import PDF_HANDLE_ROOT, log, read_json_if_exists, resolve_report_dir
from pipeline_utils import (
    build_site_data_paths,
    ensure_dir,
    read_json,
    read_text,
    sha1_text,
    utc_timestamp,
    write_json,
    write_text,
)
from stage5_utils import (
    apply_degree_patches,
    build_provenance_marker,
    build_source_note,
    deep_copy_degree,
    flatten_related_topics,
    normalize_degree_data,
    normalize_lookup_text,
    normalize_string_array,
    normalize_text,
    serialize_degree_data,
    unique_links,
    unique_strings,
    validate_against_schema,
    validate_degree_references,
)


DEFAULT_PROMPT_FILE = PDF_HANDLE_ROOT / "prompts" / "targeted_refill_mode_a_system.txt"
REFILL_WORK_ID = "targeted-refill-mode-a"
DEFAULT_CLASSIFICATIONS = {"seed_only", "sparse"}
DEFAULT_MIN_CANDIDATE_SCORE = 45
DEFAULT_MAX_SOURCES_PER_ENTRY = 3
DEFAULT_MAX_EXCERPT_CHARS_PER_SOURCE = 1400
DEFAULT_MAX_SOURCE_PACKET_CHARS = 5200
DEFAULT_MAX_OUTPUT_TOKENS = 4096

REFILL_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "property_ordering": [
        "full_summary_addition_he",
        "practical_elements_additions_he",
        "symbolic_meaning_addition_he",
        "candidate_lesson_addition_he",
        "tradition_notes_additions_he",
        "caution_notes_additions_he",
        "used_source_slugs",
        "insufficiency_note_he",
    ],
    "properties": {
        "full_summary_addition_he": {"type": "STRING"},
        "practical_elements_additions_he": {"type": "ARRAY", "items": {"type": "STRING"}},
        "symbolic_meaning_addition_he": {"type": "STRING"},
        "candidate_lesson_addition_he": {"type": "STRING"},
        "tradition_notes_additions_he": {"type": "ARRAY", "items": {"type": "STRING"}},
        "caution_notes_additions_he": {"type": "ARRAY", "items": {"type": "STRING"}},
        "used_source_slugs": {"type": "ARRAY", "items": {"type": "STRING"}},
        "insufficiency_note_he": {"type": "STRING"},
    },
    "required": [
        "full_summary_addition_he",
        "practical_elements_additions_he",
        "symbolic_meaning_addition_he",
        "candidate_lesson_addition_he",
        "tradition_notes_additions_he",
        "caution_notes_additions_he",
        "used_source_slugs",
        "insufficiency_note_he",
    ],
}

DEFAULT_USER_PROMPT_TEMPLATE = """Produce evidence-only refill additions for the existing entry.

Return JSON only.
Return a single JSON object that matches the requested schema exactly.
Do not wrap the output in markdown fences.
Do not invent facts, rituals, symbolism, names, laws, or terminology not directly supported by the source packet.
If the evidence is insufficient for a field, return an empty string or [] for that field.
Use only the provided source packet.

Target packet:
```json
{packet_json}
```
"""


class MalformedModelPayloadError(RuntimeError):
    def __init__(self, message: str, *, raw_payload_text: str | None = None) -> None:
        super().__init__(message)
        self.raw_payload_text = raw_payload_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mode A targeted refill from audit: evidence-only staged enrichment for sparse entries."
    )
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, default=None)
    parser.add_argument("--queue-file", type=Path, default=None)
    parser.add_argument("--staging-dir", type=Path, default=None)
    parser.add_argument(
        "--supplemental-library",
        type=Path,
        default=None,
        help="Optional staged library candidate JSON to use as additional source material during refill.",
    )
    parser.add_argument("--prompt-file", type=Path, default=DEFAULT_PROMPT_FILE)
    parser.add_argument("--provider", choices=["gemini", "heuristic"], default="gemini")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--api-key-env", default="GEMINI_API_KEY")
    parser.add_argument("--degree", choices=["level1", "level2", "all"], default="all")
    parser.add_argument(
        "--classification",
        default="seed_only,sparse",
        help="Comma-separated classifications to target. Default: seed_only,sparse",
    )
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--slug", action="append", default=[])
    parser.add_argument("--work-id", default=None, help="Optional candidate source work_id filter.")
    parser.add_argument("--max-entries", type=int, default=None)
    parser.add_argument("--max-sources-per-entry", type=int, default=DEFAULT_MAX_SOURCES_PER_ENTRY)
    parser.add_argument("--min-candidate-score", type=int, default=DEFAULT_MIN_CANDIDATE_SCORE)
    parser.add_argument("--max-excerpt-chars-per-source", type=int, default=DEFAULT_MAX_EXCERPT_CHARS_PER_SOURCE)
    parser.add_argument("--max-source-packet-chars", type=int, default=DEFAULT_MAX_SOURCE_PACKET_CHARS)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser


def parse_classifications(spec: str) -> set[str]:
    values = {item.strip() for item in spec.split(",") if item.strip()}
    return values or set(DEFAULT_CLASSIFICATIONS)


def build_queue_file_path(*, audit_dir: Path | None, queue_file: Path | None) -> Path:
    if bool(audit_dir) == bool(queue_file):
        raise SystemExit("Provide exactly one of --audit-dir or --queue-file.")
    if audit_dir:
        candidate = audit_dir.resolve() / "audit_sparse_refill_queue.json"
        if not candidate.exists():
            raise SystemExit(f"Queue file not found in audit dir: {candidate}")
        return candidate
    assert queue_file is not None
    if not queue_file.resolve().exists():
        raise SystemExit(f"Queue file not found: {queue_file.resolve()}")
    return queue_file.resolve()


def get_gemini_client(api_key: str | None) -> tuple[Any, Any]:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "Gemini provider requires the google-genai package. Install it with: pip install -U google-genai"
        ) from exc

    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        client = genai.Client()
    return client, types


def is_quota_exhausted_error(exc: Exception) -> bool:
    text = str(exc).upper()
    status_code = getattr(exc, "status_code", None)
    return status_code == 429 or "RESOURCE_EXHAUSTED" in text or "QUOTA EXCEEDED" in text


def is_service_unavailable_error(exc: Exception) -> bool:
    text = str(exc).upper()
    status_code = getattr(exc, "status_code", None)
    return status_code == 503 or "UNAVAILABLE" in text or "HIGH DEMAND" in text


def extract_json_payload(text: str) -> dict[str, Any]:
    raw = normalize_text(text)
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.removeprefix("json").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise MalformedModelPayloadError(
                f"Gemini returned invalid JSON: {exc}",
                raw_payload_text=raw,
            ) from exc
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError as inner_exc:
            raise MalformedModelPayloadError(
                f"Gemini returned invalid JSON: {inner_exc}",
                raw_payload_text=raw,
            ) from inner_exc


def coerce_refill_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise MalformedModelPayloadError(
            f"Gemini response parsed into {type(payload).__name__}, expected a JSON object."
        )
    return {
        "full_summary_addition_he": normalize_text(payload.get("full_summary_addition_he")),
        "practical_elements_additions_he": normalize_string_array(payload.get("practical_elements_additions_he")),
        "symbolic_meaning_addition_he": normalize_text(payload.get("symbolic_meaning_addition_he")),
        "candidate_lesson_addition_he": normalize_text(payload.get("candidate_lesson_addition_he")),
        "tradition_notes_additions_he": normalize_string_array(payload.get("tradition_notes_additions_he")),
        "caution_notes_additions_he": normalize_string_array(payload.get("caution_notes_additions_he")),
        "used_source_slugs": normalize_string_array(payload.get("used_source_slugs")),
        "insufficiency_note_he": normalize_text(payload.get("insufficiency_note_he")),
    }


def map_packet_with_gemini(
    *,
    system_prompt: str,
    model: str,
    api_key: str | None,
    temperature: float,
    max_output_tokens: int,
    user_prompt: str,
) -> dict[str, Any]:
    client, types = get_gemini_client(api_key)
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_schema=REFILL_RESPONSE_SCHEMA,
        ),
    )
    parsed_payload = getattr(response, "parsed", None)
    if isinstance(parsed_payload, dict):
        return coerce_refill_payload(parsed_payload)

    response_text = getattr(response, "text", None)
    if not response_text:
        raise MalformedModelPayloadError("Gemini returned an empty JSON response.")
    return coerce_refill_payload(extract_json_payload(response_text))


def heuristic_packet_result(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "full_summary_addition_he": "",
        "practical_elements_additions_he": [],
        "symbolic_meaning_addition_he": "",
        "candidate_lesson_addition_he": "",
        "tradition_notes_additions_he": [],
        "caution_notes_additions_he": [],
        "used_source_slugs": [item["slug"] for item in packet.get("sources", [])[:1]],
        "insufficiency_note_he": "×ž×¦×‘ heuristic ×©×ž×¨ ××ª ×—×‘×™×œ×ª ×”×¨××™×•×ª ××š ×œ× ×™×¦×¨ ×”×¢×©×¨×” ×—×“×©×”.",
    }


def ascii_term_tokens(value: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9'\\-]{2,}", value.lower())
        if len(token) >= 3
    ]


def extract_reason_terms(reasons: list[str]) -> list[str]:
    terms: list[str] = []
    for reason in reasons:
        fragment = str(reason or "")
        if ":" in fragment:
            fragment = fragment.split(":", 1)[1]
        for part in re.split(r"[,/|]", fragment):
            terms.extend(ascii_term_tokens(part))
    return list(dict.fromkeys(terms))


def split_paragraphs(text: str) -> list[str]:
    normalized = normalize_text(text).replace("\r\n", "\n").replace("\r", "\n")
    if not normalized:
        return []
    return [paragraph.strip() for paragraph in re.split(r"\n{2,}", normalized) if paragraph.strip()]


def build_target_query_terms(queue_item: dict[str, Any], entry: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    tokens.extend(ascii_term_tokens(str(queue_item.get("slug") or "")))
    tokens.extend(ascii_term_tokens(str(queue_item.get("category") or "")))
    tokens.extend(extract_reason_terms(queue_item.get("reasons", [])))
    for source in queue_item.get("candidate_library_sources", [])[:4]:
        tokens.extend(extract_reason_terms(source.get("reasons", [])))
    category = str(queue_item.get("category") or entry.get("category") or "").strip()
    tokens.extend(ascii_term_tokens(" ".join(CATEGORY_HINTS.get(category, []))))
    tokens.extend(ascii_term_tokens(str(entry.get("title") or "")))
    tokens.extend(ascii_term_tokens(" ".join(entry.get("aliases", []))))
    tokens.extend(ascii_term_tokens(" ".join(entry.get("keywords", []))))
    for related_slug in flatten_related_topics(entry.get("related_topics")):
        tokens.extend(ascii_term_tokens(related_slug))
    return list(dict.fromkeys(token for token in tokens if token))


def entry_summary_snapshot(entry: dict[str, Any], *, max_chars: int = 1800) -> dict[str, Any]:
    summary = normalize_text(entry.get("full_summary", ""))
    if len(summary) > max_chars:
        summary = summary[:max_chars].rstrip() + "..."
    return {
        "slug": entry["slug"],
        "title": entry.get("title"),
        "category": entry.get("category"),
        "parent_topic": entry.get("parent_topic"),
        "related_topics": entry.get("related_topics"),
        "short_summary": entry.get("short_summary", ""),
        "full_summary_excerpt": summary,
        "practical_elements": list(entry.get("practical_elements") or []),
        "symbolic_meaning": entry.get("symbolic_meaning", ""),
        "candidate_lesson": entry.get("candidate_lesson", ""),
        "knowledge_links": list(entry.get("knowledge_links") or []),
        "source_notes": list(entry.get("source_notes") or []),
    }


def select_candidate_sources(
    *,
    queue_item: dict[str, Any],
    library_data: dict[str, Any],
    min_candidate_score: int,
    max_sources: int,
    work_filter: str | None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for candidate in queue_item.get("candidate_library_sources", []):
        if work_filter and str(candidate.get("work_id") or "").strip() != work_filter:
            continue
        if int(candidate.get("score") or 0) < min_candidate_score:
            continue
        slug = str(candidate.get("slug") or "").strip()
        library_entry = library_data["entryBySlug"].get(slug)
        if not library_entry:
            continue
        selected.append({**candidate, "library_entry": library_entry})
        if len(selected) >= max_sources:
            break
    return selected


def merge_library_candidates(
    base_library: dict[str, Any],
    supplemental_library: dict[str, Any] | None,
) -> dict[str, Any]:
    if not supplemental_library:
        return base_library

    merged = deep_copy_degree(base_library)
    merged["categories"].update(supplemental_library.get("categories", {}))
    entry_by_slug = {entry["slug"]: entry for entry in merged["entries"]}
    for entry in supplemental_library.get("entries", []):
        entry_by_slug[entry["slug"]] = entry
    merged["entries"] = list(entry_by_slug.values())
    return normalize_degree_data(serialize_degree_data(merged), "library")


def paragraph_score(*, paragraph: str, query_terms: list[str], source_title: str, source_heading: str) -> int:
    lookup = normalize_lookup_text(paragraph)
    score = 0
    for term in query_terms:
        if term in lookup:
            score += 6 if " " in term else 3
    title_text = normalize_lookup_text(" ".join(filter(None, [source_title, source_heading])))
    if title_text and title_text in lookup:
        score += 12
    if len(paragraph) >= 180:
        score += 2
    return score


def build_excerpt_text(
    *,
    source_entry: dict[str, Any],
    query_terms: list[str],
    max_chars: int,
) -> str:
    paragraphs = split_paragraphs(str(source_entry.get("full_summary") or ""))
    if not paragraphs:
        return ""

    scored = []
    for index, paragraph in enumerate(paragraphs):
        scored.append(
            (
                paragraph_score(
                    paragraph=paragraph,
                    query_terms=query_terms,
                    source_title=str(source_entry.get("title") or ""),
                    source_heading=str(source_entry.get("source_heading") or ""),
                ),
                index,
                paragraph,
            )
        )
    scored.sort(key=lambda item: (-item[0], item[1]))

    selected_indices: list[int] = []
    for score, index, _paragraph in scored:
        if score <= 0 and selected_indices:
            continue
        selected_indices.append(index)
        if len(selected_indices) >= 3:
            break

    if not selected_indices:
        selected_indices = list(range(min(2, len(paragraphs))))

    excerpt_parts: list[str] = []
    total_chars = 0
    for index in sorted(set(selected_indices)):
        paragraph = paragraphs[index]
        projected = total_chars + len(paragraph) + (2 if excerpt_parts else 0)
        if excerpt_parts and projected > max_chars:
            break
        excerpt_parts.append(paragraph)
        total_chars = projected

    excerpt = "\n\n".join(excerpt_parts).strip()
    if not excerpt:
        excerpt = normalize_text(str(source_entry.get("full_summary") or ""))[:max_chars].strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 3].rstrip() + "..."
    return excerpt


def build_source_packet(
    *,
    queue_item: dict[str, Any],
    entry: dict[str, Any],
    selected_sources: list[dict[str, Any]],
    max_excerpt_chars_per_source: int,
    max_source_packet_chars: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    query_terms = build_target_query_terms(queue_item, entry)
    packet_sources: list[dict[str, Any]] = []
    total_chars = 0
    included_sources: list[dict[str, Any]] = []

    for source in selected_sources:
        library_entry = source["library_entry"]
        excerpt = build_excerpt_text(
            source_entry=library_entry,
            query_terms=query_terms,
            max_chars=max_excerpt_chars_per_source,
        )
        if not excerpt:
            continue
        projected = total_chars + len(excerpt)
        if packet_sources and projected > max_source_packet_chars:
            break
        total_chars = projected
        source_note = build_source_note(
            work_title=str(library_entry.get("work_title") or source.get("work_title") or ""),
            section_title=str(library_entry.get("title") or ""),
            source_path=str(library_entry.get("source_path") or ""),
            source_anchor=library_entry.get("source_anchor"),
            source_order=int(library_entry.get("source_order") or 0),
        )
        packet_sources.append(
            {
                "slug": library_entry["slug"],
                "title": library_entry.get("title"),
                "work_id": library_entry.get("work_id"),
                "work_title": library_entry.get("work_title"),
                "source_heading": library_entry.get("source_heading"),
                "source_order": library_entry.get("source_order"),
                "score": source.get("score"),
                "candidate_reasons": source.get("reasons", []),
                "source_note": source_note,
                "excerpt_markdown": excerpt,
            }
        )
        included_sources.append(source)

    packet = {
        "mode": "A",
        "policy": "evidence_only",
        "target": {
            "degree": queue_item["degree"],
            "classification": queue_item.get("classification", "custom_queue"),
            "sparsity_score": queue_item.get("sparsity_score"),
            "reasons": queue_item.get("reasons", []),
            "current_content_stats": queue_item.get("current_content_stats", {}),
            "entry_snapshot": entry_summary_snapshot(entry),
        },
        "sources": packet_sources,
    }
    return packet, included_sources


def build_refill_section_id(*, degree: str, slug: str, source_slugs: list[str]) -> str:
    suffix = sha1_text("|".join([degree, slug, *source_slugs]))[:12]
    return f"refill-{degree}-{slug}-{suffix}"


def marker_present(text: str, marker_id: str) -> bool:
    return f"<!-- {marker_id} -->" in str(text or "")


def build_full_summary_block(*, title: str, source_labels: list[str], addition: str) -> str:
    lines = [
        "### ×”×¢×©×¨×” ×ž×ž×•×§×“×ª ×ž×ž×§×•×¨×•×ª ×ž×™×•×‘××™×",
        f"×¢×¨×š ×™×¢×“: {title}",
        f"×ž×‘×•×¡×¡ ×¢×œ: {'; '.join(source_labels)}" if source_labels else "",
        "",
        addition.strip(),
    ]
    return "\n".join(line for line in lines if line is not None).strip()


def normalize_refill_result(
    *,
    result: dict[str, Any],
    entry: dict[str, Any],
    selected_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    valid_source_slugs = {
        str(source["library_entry"]["slug"]): source for source in selected_sources
    }
    used_source_slugs = [
        slug for slug in result.get("used_source_slugs", []) if slug in valid_source_slugs
    ]
    if not used_source_slugs and any(
        [
            result.get("full_summary_addition_he"),
            result.get("practical_elements_additions_he"),
            result.get("symbolic_meaning_addition_he"),
            result.get("candidate_lesson_addition_he"),
            result.get("tradition_notes_additions_he"),
            result.get("caution_notes_additions_he"),
        ]
    ):
        raise MalformedModelPayloadError("Refill output contained additions but no valid used_source_slugs.")

    existing_full = normalize_lookup_text(str(entry.get("full_summary") or ""))
    full_summary_addition = normalize_text(result.get("full_summary_addition_he"))
    if full_summary_addition and normalize_lookup_text(full_summary_addition) in existing_full:
        full_summary_addition = ""

    return {
        "full_summary_addition_he": full_summary_addition,
        "practical_elements_additions_he": unique_strings(
            [
                item
                for item in result.get("practical_elements_additions_he", [])
                if normalize_lookup_text(item) not in {
                    normalize_lookup_text(existing)
                    for existing in entry.get("practical_elements", [])
                }
            ]
        ),
        "symbolic_meaning_addition_he": normalize_text(result.get("symbolic_meaning_addition_he")),
        "candidate_lesson_addition_he": normalize_text(result.get("candidate_lesson_addition_he")),
        "tradition_notes_additions_he": unique_strings(
            [
                item
                for item in result.get("tradition_notes_additions_he", [])
                if normalize_lookup_text(item) not in {
                    normalize_lookup_text(existing)
                    for existing in entry.get("tradition_notes", [])
                }
            ]
        ),
        "caution_notes_additions_he": unique_strings(
            [
                item
                for item in result.get("caution_notes_additions_he", [])
                if normalize_lookup_text(item) not in {
                    normalize_lookup_text(existing)
                    for existing in entry.get("caution_notes", [])
                }
            ]
        ),
        "used_source_slugs": used_source_slugs,
        "insufficiency_note_he": normalize_text(result.get("insufficiency_note_he")),
    }


def build_patch_operation(
    *,
    target_degree: str,
    target_slug: str,
    target_title: str,
    section_id: str,
    normalized_result: dict[str, Any],
    selected_sources: list[dict[str, Any]],
) -> dict[str, Any] | None:
    used_source_slugs = normalized_result["used_source_slugs"]
    if not used_source_slugs:
        return None

    used_sources = [source for source in selected_sources if source["library_entry"]["slug"] in used_source_slugs]
    source_labels = [
        f"{source['library_entry'].get('work_title') or source.get('work_title')} / {source['library_entry'].get('title')}"
        for source in used_sources
    ]
    source_notes = unique_strings(
        [
            build_source_note(
                work_title=str(source["library_entry"].get("work_title") or source.get("work_title") or ""),
                section_title=str(source["library_entry"].get("title") or ""),
                source_path=str(source["library_entry"].get("source_path") or ""),
                source_anchor=source["library_entry"].get("source_anchor"),
                source_order=int(source["library_entry"].get("source_order") or 0),
            )
            for source in used_sources
        ]
    )
    knowledge_links = unique_links(
        [{"slug": source["library_entry"]["slug"], "degree": "library"} for source in used_sources]
    )
    full_summary_block = build_full_summary_block(
        title=target_title,
        source_labels=source_labels,
        addition=normalized_result["full_summary_addition_he"],
    ) if normalized_result["full_summary_addition_he"] else ""

    if not any(
        [
            full_summary_block,
            normalized_result["practical_elements_additions_he"],
            normalized_result["symbolic_meaning_addition_he"],
            normalized_result["candidate_lesson_addition_he"],
            normalized_result["tradition_notes_additions_he"],
            normalized_result["caution_notes_additions_he"],
        ]
    ):
        return None

    return {
        "slug": target_slug,
        "degree": target_degree,
        "work_id": REFILL_WORK_ID,
        "section_id": section_id,
        "marker_id": build_provenance_marker(REFILL_WORK_ID, section_id),
        "changes": {
            "full_summary_block": full_summary_block,
            "practical_elements": normalized_result["practical_elements_additions_he"],
            "symbolic_meaning": normalized_result["symbolic_meaning_addition_he"],
            "candidate_lesson": normalized_result["candidate_lesson_addition_he"],
            "tradition_notes": normalized_result["tradition_notes_additions_he"],
            "caution_notes": normalized_result["caution_notes_additions_he"],
            "source_notes": source_notes,
            "knowledge_links": knowledge_links,
        },
    }


def select_targets(
    *,
    queue: list[dict[str, Any]],
    degree_filter: str,
    classification_filter: set[str],
    categories: list[str],
    slugs: list[str],
    max_entries: int | None,
) -> list[dict[str, Any]]:
    category_set = {item.strip() for item in categories if item.strip()}
    slug_set = {item.strip() for item in slugs if item.strip()}
    selected: list[dict[str, Any]] = []
    for item in queue:
        degree = str(item.get("degree") or "").strip()
        classification = str(item.get("classification") or "").strip()
        category = str(item.get("category") or "").strip()
        slug = str(item.get("slug") or "").strip()
        if degree_filter != "all" and degree != degree_filter:
            continue
        if classification_filter and classification not in classification_filter:
            continue
        if category_set and category not in category_set:
            continue
        if slug_set and slug not in slug_set:
            continue
        selected.append(item)
        if max_entries is not None and len(selected) >= max_entries:
            break
    return selected


def upsert_target_row(
    target_rows: list[dict[str, Any]],
    target_status_by_key: dict[str, dict[str, Any]],
    row: dict[str, Any],
) -> None:
    key = f"{row['degree']}::{row['slug']}"
    existing = target_status_by_key.get(key)
    if existing in target_rows:
        target_rows[target_rows.index(existing)] = row
    else:
        target_rows.append(row)
    target_status_by_key[key] = row


def build_work_manifest_row(
    *,
    site_root: Path,
    queue_file: Path,
    target_rows: list[dict[str, Any]],
    run_status: str,
    provider: str,
) -> dict[str, Any]:
    return {
        "work_id": REFILL_WORK_ID,
        "work_title": "Targeted Refill Mode A",
        "source_book_name": queue_file.stem,
        "book_slug": f"targeted-refill-{site_root.resolve().name}",
        "partial": run_status != "completed",
        "target_count": len(target_rows),
        "completed_targets": len([row for row in target_rows if row.get("status") == "completed"]),
        "operation_count": len([row for row in target_rows if row.get("operation_written")]),
        "provider": provider,
        "site_root": str(site_root.resolve()),
        "mode": "A",
    }


def build_validation_payload(
    *,
    site_paths: dict[str, Path],
    base_library: dict[str, Any],
    base_level1: dict[str, Any],
    base_level2: dict[str, Any],
    level1_operations: list[dict[str, Any]],
    level2_operations: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate_library = deep_copy_degree(base_library)
    candidate_level1 = apply_degree_patches(deep_copy_degree(base_level1), level1_operations)
    candidate_level2 = apply_degree_patches(deep_copy_degree(base_level2), level2_operations)

    library_payload = serialize_degree_data(candidate_library)
    level1_payload = serialize_degree_data(candidate_level1)
    level2_payload = serialize_degree_data(candidate_level2)
    validation = {
        "library": validate_against_schema(library_payload, site_paths["schema"]),
        "level1": validate_against_schema(level1_payload, site_paths["schema"]),
        "level2": validate_against_schema(level2_payload, site_paths["schema"]),
    }
    reference_report = validate_degree_references(
        {
            "library": normalize_degree_data(library_payload, "library"),
            "level1": normalize_degree_data(level1_payload, "level1"),
            "level2": normalize_degree_data(level2_payload, "level2"),
        }
    )
    return library_payload, level1_payload, level2_payload, {
        "created_at": utc_timestamp(),
        "schema_path": str(site_paths["schema"]),
        "degrees": validation,
        "references": reference_report,
        "ok": all(item["ok"] for item in validation.values()) and reference_report["ok"],
    }


def render_markdown_report(summary: dict[str, Any], targets: list[dict[str, Any]]) -> str:
    lines = [
        "# Targeted Refill From Audit",
        "",
        f"- Site root: `{summary['site_root']}`",
        f"- Status: `{summary['status']}`",
        f"- Provider: `{summary['provider']}`",
        f"- Targets selected: `{summary['selected_target_count']}`",
        f"- Completed: `{summary['completed_count']}`",
        f"- Manual review: `{summary['manual_review_count']}`",
        f"- Already applied/skipped: `{summary['skipped_count']}`",
        f"- Operations written: `{summary['operation_count']}`",
        "",
        "## Targets",
        "",
    ]
    for row in targets:
        lines.extend(
            [
                f"### {row['degree']}::{row['slug']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Classification: `{row['classification']}`",
                f"- Selected sources: `{row.get('selected_source_count', 0)}`",
                f"- Used sources: `{len(row.get('used_source_slugs', []))}`",
                f"- Marker: `{row.get('marker_id', '')}`",
                f"- Note: {row.get('note') or ''}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_html_report(summary: dict[str, Any], targets: list[dict[str, Any]]) -> str:
    rows = []
    for row in targets:
        rows.append(
            "<tr>"
            f"<td>{escape(row['degree'])}</td>"
            f"<td>{escape(row['slug'])}</td>"
            f"<td>{escape(row['classification'])}</td>"
            f"<td>{escape(row['status'])}</td>"
            f"<td>{row.get('selected_source_count', 0)}</td>"
            f"<td>{len(row.get('used_source_slugs', []))}</td>"
            f"<td>{escape(row.get('note') or '')}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Targeted Refill From Audit</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 24px; color: #222; }}
    h1, h2 {{ margin-bottom: 0.3rem; }}
    .summary {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 18px 0 24px; }}
    .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 12px; background: #fafafa; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f0f0f0; }}
  </style>
</head>
<body>
  <h1>Targeted Refill From Audit</h1>
  <div class="summary">
    <div class="card"><strong>Site root</strong><br>{escape(summary['site_root'])}</div>
    <div class="card"><strong>Status</strong><br>{escape(summary['status'])}</div>
    <div class="card"><strong>Provider</strong><br>{escape(summary['provider'])}</div>
    <div class="card"><strong>Targets selected</strong><br>{summary['selected_target_count']}</div>
    <div class="card"><strong>Completed</strong><br>{summary['completed_count']}</div>
    <div class="card"><strong>Operations written</strong><br>{summary['operation_count']}</div>
  </div>
  <h2>Targets</h2>
  <table>
    <thead>
      <tr>
        <th>Degree</th>
        <th>Slug</th>
        <th>Classification</th>
        <th>Status</th>
        <th>Selected Sources</th>
        <th>Used Sources</th>
        <th>Note</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""


def persist_outputs(
    *,
    staging_dir: Path,
    work_manifest_row: dict[str, Any],
    base_library: dict[str, Any],
    base_level1: dict[str, Any],
    base_level2: dict[str, Any],
    level1_operations: list[dict[str, Any]],
    level2_operations: list[dict[str, Any]],
    target_rows: list[dict[str, Any]],
    summary: dict[str, Any],
    site_paths: dict[str, Path],
) -> None:
    library_payload, level1_payload, level2_payload, validation_report = build_validation_payload(
        site_paths=site_paths,
        base_library=base_library,
        base_level1=base_level1,
        base_level2=base_level2,
        level1_operations=level1_operations,
        level2_operations=level2_operations,
    )
    write_json(staging_dir / "work_manifest.generated.json", {"created_at": utc_timestamp(), "works": [work_manifest_row]})
    write_json(
        staging_dir / "library.patch.json",
        {"created_at": utc_timestamp(), "degree": "library", "category_added": False, "entries": []},
    )
    write_json(staging_dir / "companion_candidates.json", [])
    write_json(staging_dir / "library.candidate.json", library_payload)
    write_json(staging_dir / "level1.candidate.json", level1_payload)
    write_json(staging_dir / "level2.candidate.json", level2_payload)
    write_json(staging_dir / "level1.patch.json", {"created_at": utc_timestamp(), "degree": "level1", "operations": level1_operations})
    write_json(staging_dir / "level2.patch.json", {"created_at": utc_timestamp(), "degree": "level2", "operations": level2_operations})
    write_json(staging_dir / "refill_manifest.json", {"created_at": utc_timestamp(), "mode": "A", "targets": target_rows})
    write_json(staging_dir / "refill_review.json", summary)
    write_json(staging_dir / "run_status.json", summary)
    write_json(staging_dir / "validation_report.json", validation_report)
    write_text(staging_dir / "refill_report.md", render_markdown_report(summary, target_rows))
    write_text(staging_dir / "refill_report.html", render_html_report(summary, target_rows))


def load_existing_state(
    *,
    staging_dir: Path,
    require_existing: bool,
) -> dict[str, Any] | None:
    manifest_path = staging_dir / "refill_manifest.json"
    level1_patch_path = staging_dir / "level1.patch.json"
    level2_patch_path = staging_dir / "level2.patch.json"
    run_status_path = staging_dir / "run_status.json"

    if not manifest_path.exists():
        if require_existing:
            raise SystemExit(f"Cannot resume because refill manifest is missing: {manifest_path}")
        return None

    if require_existing and not (level1_patch_path.exists() and level2_patch_path.exists() and run_status_path.exists()):
        raise SystemExit("Cannot resume because refill staged artifacts are incomplete.")

    manifest_payload = read_json(manifest_path)
    return {
        "target_rows": manifest_payload.get("targets", []),
        "level1_operations": (read_json_if_exists(level1_patch_path) or {}).get("operations", []),
        "level2_operations": (read_json_if_exists(level2_patch_path) or {}).get("operations", []),
        "run_status": read_json_if_exists(run_status_path) or {},
    }


def main() -> None:
    args = build_parser().parse_args()
    queue_file = build_queue_file_path(audit_dir=args.audit_dir, queue_file=args.queue_file)
    site_paths = build_site_data_paths(args.site_root.resolve())
    staging_dir = resolve_report_dir(
        tool_name="targeted_refill_from_audit",
        report_dir=args.staging_dir.resolve() if args.staging_dir else None,
        site_root=site_paths["site_root"],
    )
    ensure_dir(staging_dir / "source_packets")

    log(
        f"[start] site_root={site_paths['site_root']} queue={queue_file} staging_dir={staging_dir} provider={args.provider}",
        quiet=args.quiet,
    )

    classifications = parse_classifications(args.classification)
    queue = read_json(queue_file)
    selected_targets = select_targets(
        queue=queue,
        degree_filter=args.degree,
        classification_filter=classifications,
        categories=args.category,
        slugs=args.slug,
        max_entries=args.max_entries,
    )
    if not selected_targets:
        raise SystemExit("No targets matched the selected filters.")

    base_library = normalize_degree_data(read_json(site_paths["library"]), "library")
    supplemental_library = (
        normalize_degree_data(read_json(args.supplemental_library.resolve()), "library")
        if args.supplemental_library
        else None
    )
    base_library = merge_library_candidates(base_library, supplemental_library)
    base_level1 = normalize_degree_data(read_json(site_paths["level1"]), "level1")
    base_level2 = normalize_degree_data(read_json(site_paths["level2"]), "level2")
    entry_lookup = {
        ("level1", entry["slug"]): entry for entry in base_level1["entries"]
    }
    entry_lookup.update({
        ("level2", entry["slug"]): entry for entry in base_level2["entries"]
    })

    existing_state = load_existing_state(staging_dir=staging_dir, require_existing=args.resume)
    target_rows = list(existing_state["target_rows"]) if existing_state else []
    level1_operations = list(existing_state["level1_operations"]) if existing_state else []
    level2_operations = list(existing_state["level2_operations"]) if existing_state else []

    target_status_by_key = {f"{row['degree']}::{row['slug']}": row for row in target_rows}
    existing_marker_ids = {
        str(operation.get("marker_id") or "").strip()
        for operation in level1_operations + level2_operations
        if str(operation.get("marker_id") or "").strip()
    }

    system_prompt = read_text(args.prompt_file.resolve())
    api_key = os.getenv(args.api_key_env)
    interrupted: dict[str, Any] | None = None

    for index, queue_item in enumerate(selected_targets, start=1):
        target_key = f"{queue_item['degree']}::{queue_item['slug']}"
        prior_row = target_status_by_key.get(target_key)
        if prior_row and prior_row.get("status") in {
            "completed",
            "skipped_existing_marker",
            "skipped_already_present",
            "insufficient_evidence",
        }:
            log(f"[target {index}/{len(selected_targets)}] skip existing status={prior_row['status']} {target_key}", quiet=args.quiet)
            continue

        entry = entry_lookup.get((queue_item["degree"], queue_item["slug"]))
        if not entry:
            row = {
                "degree": queue_item["degree"],
                "slug": queue_item["slug"],
                "title": queue_item.get("title"),
                "classification": queue_item.get("classification"),
                "status": "missing_target",
                "note": "Target entry not found in site data.",
            }
            upsert_target_row(target_rows, target_status_by_key, row)
            continue

        selected_sources = select_candidate_sources(
            queue_item=queue_item,
            library_data=base_library,
            min_candidate_score=args.min_candidate_score,
            max_sources=args.max_sources_per_entry,
            work_filter=args.work_id,
        )
        if not selected_sources:
            row = {
                "degree": queue_item["degree"],
                "slug": queue_item["slug"],
                "title": queue_item.get("title"),
                "classification": queue_item.get("classification"),
                "status": "insufficient_evidence",
                "note": "No candidate library sources passed the threshold.",
                "selected_source_count": 0,
                "used_source_slugs": [],
                "operation_written": False,
            }
            upsert_target_row(target_rows, target_status_by_key, row)
            continue

        packet, included_sources = build_source_packet(
            queue_item=queue_item,
            entry=entry,
            selected_sources=selected_sources,
            max_excerpt_chars_per_source=args.max_excerpt_chars_per_source,
            max_source_packet_chars=args.max_source_packet_chars,
        )
        if not packet["sources"]:
            row = {
                "degree": queue_item["degree"],
                "slug": queue_item["slug"],
                "title": queue_item.get("title"),
                "classification": queue_item.get("classification"),
                "status": "insufficient_evidence",
                "note": "Source packet could not extract usable excerpts.",
                "selected_source_count": 0,
                "used_source_slugs": [],
                "operation_written": False,
            }
            upsert_target_row(target_rows, target_status_by_key, row)
            continue

        selected_source_slugs = [source["library_entry"]["slug"] for source in included_sources]
        section_id = build_refill_section_id(
            degree=queue_item["degree"],
            slug=queue_item["slug"],
            source_slugs=selected_source_slugs,
        )
        marker_id = build_provenance_marker(REFILL_WORK_ID, section_id)
        source_packet_path = staging_dir / "source_packets" / f"{queue_item['degree']}-{queue_item['slug']}.json"
        write_json(source_packet_path, packet)

        if marker_id in existing_marker_ids:
            row = {
                "degree": queue_item["degree"],
                "slug": queue_item["slug"],
                "title": queue_item.get("title"),
                "classification": queue_item.get("classification"),
                "status": "skipped_existing_marker",
                "note": "This refill marker already exists in the staged refill run.",
                "marker_id": marker_id,
                "selected_source_count": len(selected_source_slugs),
                "used_source_slugs": selected_source_slugs,
                "source_packet_path": str(source_packet_path),
                "operation_written": False,
            }
            upsert_target_row(target_rows, target_status_by_key, row)
            continue

        if marker_present(str(entry.get("full_summary") or ""), marker_id):
            row = {
                "degree": queue_item["degree"],
                "slug": queue_item["slug"],
                "title": queue_item.get("title"),
                "classification": queue_item.get("classification"),
                "status": "skipped_already_present",
                "note": "The same refill marker is already present in live content.",
                "marker_id": marker_id,
                "selected_source_count": len(selected_source_slugs),
                "used_source_slugs": selected_source_slugs,
                "source_packet_path": str(source_packet_path),
                "operation_written": False,
            }
            upsert_target_row(target_rows, target_status_by_key, row)
            continue

        log(
            f"[target {index}/{len(selected_targets)}] {target_key} sources={len(selected_source_slugs)}",
            quiet=args.quiet,
        )

        if args.provider == "heuristic":
            result = heuristic_packet_result(packet)
        else:
            last_exception: Exception | None = None
            result = None
            user_prompt = DEFAULT_USER_PROMPT_TEMPLATE.format(
                packet_json=json.dumps(packet, ensure_ascii=False, indent=2)
            )
            for attempt in range(1, args.max_retries + 1):
                try:
                    log(
                        f"[target {index}/{len(selected_targets)}] gemini request attempt={attempt}",
                        quiet=args.quiet,
                    )
                    result = map_packet_with_gemini(
                        system_prompt=system_prompt,
                        model=args.model,
                        api_key=api_key,
                        temperature=args.temperature,
                        max_output_tokens=args.max_output_tokens,
                        user_prompt=user_prompt,
                    )
                    log(
                        f"[target {index}/{len(selected_targets)}] gemini success attempt={attempt}",
                        quiet=args.quiet,
                    )
                    break
                except Exception as exc:  # noqa: BLE001
                    last_exception = exc
                    if is_quota_exhausted_error(exc):
                        row = {
                            "degree": queue_item["degree"],
                            "slug": queue_item["slug"],
                            "title": queue_item.get("title"),
                            "classification": queue_item.get("classification"),
                            "status": "interrupted",
                            "note": f"Quota exhausted before completion: {exc}",
                            "marker_id": marker_id,
                            "section_id": section_id,
                            "selected_source_count": len(selected_source_slugs),
                            "selected_source_slugs": selected_source_slugs,
                            "used_source_slugs": [],
                            "source_packet_path": str(source_packet_path),
                            "operation_written": False,
                            "provider": args.provider,
                        }
                        upsert_target_row(target_rows, target_status_by_key, row)
                        interrupted = {
                            "status": "interrupted",
                            "reason": "quota_exhausted",
                            "message": str(exc),
                            "target_key": target_key,
                        }
                        break
                    if is_service_unavailable_error(exc):
                        if attempt >= args.max_retries:
                            row = {
                                "degree": queue_item["degree"],
                                "slug": queue_item["slug"],
                                "title": queue_item.get("title"),
                                "classification": queue_item.get("classification"),
                                "status": "interrupted",
                                "note": f"Service unavailable after retries: {exc}",
                                "marker_id": marker_id,
                                "section_id": section_id,
                                "selected_source_count": len(selected_source_slugs),
                                "selected_source_slugs": selected_source_slugs,
                                "used_source_slugs": [],
                                "source_packet_path": str(source_packet_path),
                                "operation_written": False,
                                "provider": args.provider,
                            }
                            upsert_target_row(target_rows, target_status_by_key, row)
                            interrupted = {
                                "status": "interrupted",
                                "reason": "service_unavailable",
                                "message": str(exc),
                                "target_key": target_key,
                            }
                            break
                        log(
                            f"[target {index}/{len(selected_targets)}] gemini retry {attempt}/{args.max_retries} error={exc}",
                            quiet=args.quiet,
                        )
                        time.sleep(args.sleep_seconds * attempt)
                        continue
                    if isinstance(exc, MalformedModelPayloadError):
                        if attempt >= args.max_retries:
                            result = {
                                "full_summary_addition_he": "",
                                "practical_elements_additions_he": [],
                                "symbolic_meaning_addition_he": "",
                                "candidate_lesson_addition_he": "",
                                "tradition_notes_additions_he": [],
                                "caution_notes_additions_he": [],
                                "used_source_slugs": [],
                                "insufficiency_note_he": "Gemini returned malformed JSON after retries; send this target to manual review.",
                            }
                            log(
                                f"[target {index}/{len(selected_targets)}] malformed-json manual_review",
                                quiet=args.quiet,
                            )
                            row = {
                                "degree": queue_item["degree"],
                                "slug": queue_item["slug"],
                                "title": queue_item.get("title"),
                                "classification": queue_item.get("classification"),
                                "status": "manual_review",
                                "note": result["insufficiency_note_he"],
                                "marker_id": marker_id,
                                "section_id": section_id,
                                "selected_source_count": len(selected_source_slugs),
                                "selected_source_slugs": selected_source_slugs,
                                "used_source_slugs": [],
                                "source_packet_path": str(source_packet_path),
                                "operation_written": False,
                                "provider": args.provider,
                            }
                            upsert_target_row(target_rows, target_status_by_key, row)
                            break
                        log(
                            f"[target {index}/{len(selected_targets)}] gemini retry {attempt}/{args.max_retries} error={exc}",
                            quiet=args.quiet,
                        )
                        time.sleep(args.sleep_seconds * attempt)
                        continue
                    row = {
                        "degree": queue_item["degree"],
                        "slug": queue_item["slug"],
                        "title": queue_item.get("title"),
                        "classification": queue_item.get("classification"),
                        "status": "interrupted",
                        "note": f"Model error before completion: {exc}",
                        "marker_id": marker_id,
                        "section_id": section_id,
                        "selected_source_count": len(selected_source_slugs),
                        "selected_source_slugs": selected_source_slugs,
                        "used_source_slugs": [],
                        "source_packet_path": str(source_packet_path),
                        "operation_written": False,
                        "provider": args.provider,
                    }
                    upsert_target_row(target_rows, target_status_by_key, row)
                    interrupted = {
                        "status": "interrupted",
                        "reason": "model_error",
                        "message": str(exc),
                        "target_key": target_key,
                    }
                    break

            if interrupted:
                break
            if result is None:
                raise RuntimeError(f"Gemini mapping failed for {target_key}: {last_exception}")

        normalized_result = normalize_refill_result(
            result=result,
            entry=entry,
            selected_sources=included_sources,
        )
        operation = build_patch_operation(
            target_degree=queue_item["degree"],
            target_slug=queue_item["slug"],
            target_title=str(queue_item.get("title") or entry.get("title") or ""),
            section_id=section_id,
            normalized_result=normalized_result,
            selected_sources=included_sources,
        )

        if operation:
            if queue_item["degree"] == "level1":
                level1_operations.append(operation)
            else:
                level2_operations.append(operation)
            existing_marker_ids.add(operation["marker_id"])
            status = "completed"
            note = ""
        else:
            status = "manual_review"
            note = normalized_result["insufficiency_note_he"] or "No supported additions were produced from the evidence packet."

        row = {
            "degree": queue_item["degree"],
            "slug": queue_item["slug"],
            "title": queue_item.get("title"),
            "classification": queue_item.get("classification"),
            "status": status,
            "note": note,
            "marker_id": marker_id,
            "section_id": section_id,
            "selected_source_count": len(selected_source_slugs),
            "selected_source_slugs": selected_source_slugs,
            "used_source_slugs": normalized_result["used_source_slugs"],
            "source_packet_path": str(source_packet_path),
            "operation_written": bool(operation),
            "provider": args.provider,
        }
        upsert_target_row(target_rows, target_status_by_key, row)
        if args.provider == "gemini" and args.sleep_seconds:
            time.sleep(args.sleep_seconds)

    final_status = "completed" if interrupted is None else "interrupted"
    completed_count = len([row for row in target_rows if row.get("status") == "completed"])
    skipped_count = len([row for row in target_rows if str(row.get("status") or "").startswith("skipped_")])
    manual_review_count = len([row for row in target_rows if row.get("status") in {"manual_review", "insufficient_evidence"}])
    summary = {
        "created_at": utc_timestamp(),
        "tool": "targeted_refill_from_audit",
        "mode": "A",
        "status": final_status,
        "provider": args.provider,
        "model": args.model if args.provider == "gemini" else None,
        "site_root": str(site_paths["site_root"]),
        "queue_file": str(queue_file),
        "staging_dir": str(staging_dir),
        "selected_target_count": len(selected_targets),
        "completed_count": completed_count,
        "skipped_count": skipped_count,
        "manual_review_count": manual_review_count,
        "operation_count": len(level1_operations) + len(level2_operations),
        "interrupted": interrupted,
    }

    work_manifest_row = build_work_manifest_row(
        site_root=site_paths["site_root"],
        queue_file=queue_file,
        target_rows=target_rows,
        run_status=final_status,
        provider=args.provider,
    )
    persist_outputs(
        staging_dir=staging_dir,
        work_manifest_row=work_manifest_row,
        base_library=base_library,
        base_level1=base_level1,
        base_level2=base_level2,
        level1_operations=level1_operations,
        level2_operations=level2_operations,
        target_rows=target_rows,
        summary=summary,
        site_paths=site_paths,
    )
    log(
        f"[done] status={final_status} operations={summary['operation_count']} completed={completed_count} staging_dir={staging_dir}",
        quiet=args.quiet,
    )
    if interrupted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

