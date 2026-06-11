from __future__ import annotations

import json
from typing import Any, Iterable

from PDF_handle.prod.providers import MalformedProviderPayloadError, generate_json_content
from PDF_handle.prod.schema import normalize_nullable_string, normalize_string_array, normalize_text


DEFAULT_USER_PROMPT_TEMPLATE = """Map the following source unit into structured English canonical enrichment JSON.

Return JSON only.
Return a single JSON object that matches the requested schema exactly.
Do not wrap the output in markdown fences.
Do not omit keys.
Use an empty string for missing text fields.
Use [] for missing list fields.
Write every canonical text field in English.

Work metadata:
- work_id: {work_id}
- work_title: {work_title}
- source_book_name: {source_book_name}
- section_id: {section_id}
- section_title: {section_title}
- source_path: {source_path}
- source_anchor: {source_anchor}

Allowed target degrees: {allowed_degrees}

Allowed categories per degree (choose suggested_category from the ids of the degree you target; use "" if unsure):
{category_catalog}

Known existing entries in scope:
{catalog_excerpt}

Source unit:
```markdown
{unit_text}
```
"""

MAPPING_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "property_ordering": [
        "section_summary",
        "practical_elements",
        "symbolic_meaning",
        "candidate_lesson",
        "keywords",
        "caution_notes",
        "tradition_notes",
        "suggested_category",
        "suggested_category_reason",
        "target_entry_candidates",
        "knowledge_link_candidates",
        "new_topic_candidates",
    ],
    "properties": {
        "section_summary": {"type": "STRING"},
        "suggested_category": {"type": "STRING"},
        "suggested_category_reason": {"type": "STRING"},
        "practical_elements": {"type": "ARRAY", "items": {"type": "STRING"}},
        "symbolic_meaning": {"type": "STRING"},
        "candidate_lesson": {"type": "STRING"},
        "keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
        "caution_notes": {"type": "ARRAY", "items": {"type": "STRING"}},
        "tradition_notes": {"type": "ARRAY", "items": {"type": "STRING"}},
        "target_entry_candidates": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "property_ordering": ["slug", "degree", "title", "reason"],
                "properties": {
                    "slug": {"type": "STRING"},
                    "degree": {"type": "STRING"},
                    "title": {"type": "STRING"},
                    "reason": {"type": "STRING"},
                },
                "required": ["slug", "degree", "title", "reason"],
            },
        },
        "knowledge_link_candidates": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "property_ordering": ["slug", "degree", "title", "reason"],
                "properties": {
                    "slug": {"type": "STRING"},
                    "degree": {"type": "STRING"},
                    "title": {"type": "STRING"},
                    "reason": {"type": "STRING"},
                },
                "required": ["slug", "degree", "title", "reason"],
            },
        },
        "new_topic_candidates": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "property_ordering": ["title", "degree", "reason"],
                "properties": {
                    "title": {"type": "STRING"},
                    "degree": {"type": "STRING"},
                    "reason": {"type": "STRING"},
                },
                "required": ["title", "degree", "reason"],
            },
        },
    },
    "required": [
        "section_summary",
        "practical_elements",
        "symbolic_meaning",
        "candidate_lesson",
        "keywords",
        "caution_notes",
        "tradition_notes",
        "suggested_category",
        "suggested_category_reason",
        "target_entry_candidates",
        "knowledge_link_candidates",
        "new_topic_candidates",
    ],
}


def _normalize_candidate_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "slug": normalize_nullable_string(item.get("slug")),
                "degree": normalize_nullable_string(item.get("degree")),
                "title": normalize_text(item.get("title")),
                "reason": normalize_text(item.get("reason")),
            }
        )
    return normalized


def coerce_mapping_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise MalformedProviderPayloadError(
            f"Gemini response parsed into {type(payload).__name__}, expected a JSON object."
        )

    def first_present(canonical_key: str, legacy_key: str) -> Any:
        if canonical_key in payload:
            return payload.get(canonical_key)
        return payload.get(legacy_key)

    return {
        "section_summary": normalize_text(first_present("section_summary", "section_summary_he")),
        "practical_elements": normalize_string_array(first_present("practical_elements", "practical_elements_he")),
        "symbolic_meaning": normalize_text(first_present("symbolic_meaning", "symbolic_meaning_he")),
        "candidate_lesson": normalize_text(first_present("candidate_lesson", "candidate_lesson_he")),
        "keywords": normalize_string_array(payload.get("keywords")),
        "suggested_category": normalize_nullable_string(payload.get("suggested_category")),
        "suggested_category_reason": normalize_text(payload.get("suggested_category_reason")),
        "caution_notes": normalize_string_array(first_present("caution_notes", "caution_notes_he")),
        "tradition_notes": normalize_string_array(first_present("tradition_notes", "tradition_notes_he")),
        "target_entry_candidates": _normalize_candidate_list(payload.get("target_entry_candidates")),
        "knowledge_link_candidates": _normalize_candidate_list(payload.get("knowledge_link_candidates")),
        "new_topic_candidates": [
            {
                "title": normalize_text(item.get("title")),
                "degree": normalize_nullable_string(item.get("degree")),
                "reason": normalize_text(item.get("reason")),
            }
            for item in payload.get("new_topic_candidates", [])
            if isinstance(item, dict)
        ]
        if isinstance(payload.get("new_topic_candidates"), list)
        else [],
    }


def build_mapping_user_prompt(
    *,
    work_id: str,
    work_title: str,
    source_book_name: str,
    section_id: str,
    section_title: str,
    source_path: str,
    source_anchor: str | None,
    allowed_degrees: Iterable[str],
    catalog_excerpt_items: list[dict[str, Any]],
    unit_text: str,
    category_catalog_items: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    catalog_excerpt = json.dumps(catalog_excerpt_items, ensure_ascii=False, indent=2)
    category_catalog = json.dumps(category_catalog_items or {}, ensure_ascii=False, indent=2)
    return DEFAULT_USER_PROMPT_TEMPLATE.format(
        work_id=work_id,
        work_title=work_title,
        source_book_name=source_book_name,
        section_id=section_id,
        section_title=section_title,
        source_path=source_path,
        source_anchor=source_anchor,
        allowed_degrees=", ".join(allowed_degrees) or "none",
        category_catalog=category_catalog,
        catalog_excerpt=catalog_excerpt,
        unit_text=unit_text,
    )


def map_unit_with_gemini(
    *,
    system_prompt: str,
    model: str,
    api_key: str | None,
    temperature: float,
    max_output_tokens: int,
    user_prompt: str,
) -> dict[str, Any]:
    result = generate_json_content(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        api_key=api_key,
        response_mime_type="application/json",
        response_schema=MAPPING_RESPONSE_SCHEMA,
    )
    return coerce_mapping_payload(result["payload"])
