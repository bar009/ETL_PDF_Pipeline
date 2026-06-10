from __future__ import annotations

import copy
from typing import Any

from PDF_handle.prod.schema import normalize_entry, serialize_entry
from PDF_handle.prod.schema.data import normalize_nullable_string, normalize_string_array, normalize_text
from PDF_handle.prod.schema.patches import unique_links, unique_strings


def companion_candidate_slug(candidate: dict[str, Any]) -> str:
    slug = normalize_nullable_string(candidate.get("candidate_slug"))
    if slug:
        return slug
    seed = candidate.get("draft_seed")
    if isinstance(seed, dict):
        slug = normalize_nullable_string(seed.get("slug"))
        if slug:
            return slug
    payload = candidate.get("draft_entry_payload")
    if isinstance(payload, dict):
        return normalize_nullable_string(payload.get("slug")) or ""
    return ""


def companion_candidate_title(candidate: dict[str, Any]) -> str:
    title = normalize_text(candidate.get("suggested_title"))
    if title:
        return title
    seed = candidate.get("draft_seed")
    if isinstance(seed, dict):
        title = normalize_text(seed.get("title"))
        if title:
            return title
    payload = candidate.get("draft_entry_payload")
    if isinstance(payload, dict):
        title = normalize_text(payload.get("title"))
        if title:
            return title
    return normalize_text(candidate.get("normalized_title")) or normalize_text(candidate.get("section_title"))


def companion_candidate_degree(candidate: dict[str, Any]) -> str:
    degree = normalize_nullable_string(candidate.get("suggested_degree"))
    if degree:
        return degree
    seed = candidate.get("draft_seed")
    if isinstance(seed, dict):
        degree = normalize_nullable_string(seed.get("degree"))
        if degree:
            return degree
    payload = candidate.get("draft_entry_payload")
    if isinstance(payload, dict):
        return normalize_nullable_string(payload.get("degree")) or ""
    return normalize_nullable_string(candidate.get("candidate_degree")) or ""


def companion_candidate_category(candidate: dict[str, Any]) -> str:
    category = normalize_nullable_string(candidate.get("suggested_category"))
    if category:
        return category
    seed = candidate.get("draft_seed")
    if isinstance(seed, dict):
        category = normalize_nullable_string(seed.get("category"))
        if category:
            return category
    payload = candidate.get("draft_entry_payload")
    if isinstance(payload, dict):
        return normalize_nullable_string(payload.get("category")) or ""
    return ""


def companion_candidate_seed(candidate: dict[str, Any]) -> dict[str, Any]:
    seed = candidate.get("draft_seed")
    if isinstance(seed, dict):
        return copy.deepcopy(seed)
    payload = candidate.get("draft_entry_payload")
    if isinstance(payload, dict):
        payload_library_link = None
        for link in payload.get("knowledge_links", []):
            if isinstance(link, dict) and normalize_nullable_string(link.get("degree")) == "library":
                payload_library_link = normalize_nullable_string(link.get("slug"))
                if payload_library_link:
                    break
        return {
            "slug": payload.get("slug"),
            "title": payload.get("title"),
            "degree": payload.get("degree"),
            "applies_to_degrees": payload.get("applies_to_degrees", []),
            "category": payload.get("category"),
            "parent_topic": payload.get("parent_topic"),
            "aliases": payload.get("aliases", []),
            "keywords": payload.get("keywords", []),
            "related_topics": payload.get("related_topics", {}),
            "short_summary_he": payload.get("short_summary", ""),
            "full_summary_he": payload.get("full_summary", ""),
            "practical_elements_he": payload.get("practical_elements", []),
            "symbolic_meaning_he": payload.get("symbolic_meaning", ""),
            "candidate_lesson_he": payload.get("candidate_lesson", ""),
            "tradition_notes_he": payload.get("tradition_notes", []),
            "caution_notes_he": payload.get("caution_notes", []),
            "source_notes": payload.get("source_notes", []),
            "work_id": payload.get("work_id"),
            "work_title": payload.get("work_title"),
            "source_kind": payload.get("source_kind"),
            "source_path": payload.get("source_path"),
            "source_anchor": payload.get("source_anchor"),
            "source_heading": payload.get("source_heading"),
            "source_order": payload.get("source_order"),
            "parallel_entry": payload.get("parallel_entry"),
            "knowledge_links": payload.get("knowledge_links", []),
            "source_library_slug": payload_library_link,
            "chapter_toc": payload.get("chapter_toc", []),
            "visibility_level": payload.get("visibility_level"),
            "sensitivity_level": payload.get("sensitivity_level"),
            "tradition_scope": payload.get("tradition_scope"),
            "status": payload.get("status"),
        }
    return {}


def materialize_companion_payload(
    candidate: dict[str, Any],
    *,
    categories_by_degree: dict[str, dict[str, Any]],
    available_link_targets: dict[str, set[str]] | None = None,
) -> dict[str, Any]:
    legacy_payload = candidate.get("draft_entry_payload")
    if isinstance(legacy_payload, dict) and legacy_payload:
        payload = copy.deepcopy(legacy_payload)
        if available_link_targets is not None:
            filtered_links: list[dict[str, str]] = []
            for link in payload.get("knowledge_links", []):
                degree_id = normalize_nullable_string(link.get("degree"))
                slug = normalize_nullable_string(link.get("slug"))
                if not degree_id or not slug:
                    continue
                available_slugs = available_link_targets.get(degree_id)
                if available_slugs is None or slug in available_slugs:
                    filtered_links.append({"degree": degree_id, "slug": slug})
            payload["knowledge_links"] = unique_links(filtered_links)
        return payload

    seed = companion_candidate_seed(candidate)
    degree = normalize_nullable_string(seed.get("degree")) or companion_candidate_degree(candidate)
    if not degree:
        raise ValueError("Companion candidate is missing a degree.")
    categories = categories_by_degree.get(degree)
    if not categories:
        raise ValueError(f"Companion candidate references unknown degree {degree!r}.")

    title = normalize_text(seed.get("title")) or companion_candidate_title(candidate) or "Untitled Candidate"
    slug = normalize_nullable_string(seed.get("slug")) or companion_candidate_slug(candidate)
    if not slug:
        raise ValueError("Companion candidate is missing a slug.")

    raw_links = unique_links(seed.get("knowledge_links") if isinstance(seed.get("knowledge_links"), list) else [])
    source_library_slug = normalize_nullable_string(seed.get("source_library_slug"))
    if source_library_slug:
        raw_links = unique_links([*raw_links, {"degree": "library", "slug": source_library_slug}])

    if available_link_targets is not None:
        filtered_links: list[dict[str, str]] = []
        for link in raw_links:
            degree_id = normalize_nullable_string(link.get("degree"))
            slug = normalize_nullable_string(link.get("slug"))
            if not degree_id or not slug:
                continue
            available_slugs = available_link_targets.get(degree_id)
            if available_slugs is None or slug in available_slugs:
                filtered_links.append({"degree": degree_id, "slug": slug})
        raw_links = unique_links(filtered_links)

    payload = {
        "title": title,
        "slug": slug,
        "type": "topic",
        "degree": degree,
        "applies_to_degrees": normalize_string_array(seed.get("applies_to_degrees")) or [degree],
        "category": normalize_nullable_string(seed.get("category")) or companion_candidate_category(candidate),
        "parent_topic": normalize_nullable_string(seed.get("parent_topic")),
        "aliases": normalize_string_array(seed.get("aliases")),
        "keywords": normalize_string_array(seed.get("keywords"))[:12],
        "related_topics": seed.get("related_topics") or {
            "prior": [],
            "companion": normalize_string_array(candidate.get("related_existing_slugs"))[:8],
            "deeper": [],
        },
        "short_summary": normalize_text(seed.get("short_summary_he"))
        or f"טיוטת ערך מ־{normalize_text(seed.get('work_title')) or normalize_text(candidate.get('work_title')) or 'מקור ללא שם'}.",
        "full_summary": normalize_text(seed.get("full_summary_he")),
        "practical_elements": normalize_string_array(seed.get("practical_elements_he")),
        "symbolic_meaning": normalize_text(seed.get("symbolic_meaning_he")),
        "candidate_lesson": normalize_text(seed.get("candidate_lesson_he")),
        "tradition_notes": normalize_string_array(seed.get("tradition_notes_he")),
        "caution_notes": normalize_string_array(seed.get("caution_notes_he")),
        "source_notes": normalize_string_array(seed.get("source_notes")),
        "language": "he",
        "work_id": normalize_nullable_string(seed.get("work_id")) or normalize_nullable_string(candidate.get("work_id")),
        "work_title": normalize_text(seed.get("work_title")) or normalize_text(candidate.get("work_title")),
        "source_kind": normalize_nullable_string(seed.get("source_kind")),
        "source_path": normalize_nullable_string(seed.get("source_path")),
        "source_anchor": normalize_nullable_string(seed.get("source_anchor")),
        "source_heading": normalize_text(seed.get("source_heading")) or normalize_text(candidate.get("section_title")),
        "source_order": seed.get("source_order"),
        "parallel_entry": normalize_nullable_string(seed.get("parallel_entry")),
        "translation_mode": "archivist-hebrew",
        "knowledge_links": raw_links,
        "chapter_toc": normalize_string_array(seed.get("chapter_toc")),
        "visibility_level": normalize_nullable_string(seed.get("visibility_level")) or "internal",
        "sensitivity_level": normalize_nullable_string(seed.get("sensitivity_level")) or "standard",
        "tradition_scope": normalize_nullable_string(seed.get("tradition_scope")) or "interpretive",
        "status": normalize_nullable_string(seed.get("status")) or "draft",
    }

    if not payload["full_summary"]:
        payload["full_summary"] = payload["short_summary"]
    payload["related_topics"] = {
        "prior": unique_strings((payload["related_topics"] or {}).get("prior", [])),
        "companion": unique_strings((payload["related_topics"] or {}).get("companion", [])),
        "deeper": unique_strings((payload["related_topics"] or {}).get("deeper", [])),
    }

    return serialize_entry(
        normalize_entry(
            payload,
            degree_id=degree,
            index=0,
            categories=categories,
        )
    )
