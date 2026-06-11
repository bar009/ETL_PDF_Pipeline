from __future__ import annotations

import re

from typing import Any, Iterable

from PDF_handle.prod.schema.data import (
    normalize_lookup_text,
    normalize_nullable_string,
    normalize_text,
    refresh_degree_indexes,
    unique_links,
    unique_strings,
)


STAGED_LIBRARY_CATEGORY_ID = "etl_imports"
STAGED_LIBRARY_CATEGORY_ENTRY_SLUG = "etl-imports-category"
APPEND_MARKER_PREFIX = "PDF_STAGE5"


def build_provenance_marker(work_id: str, section_id: str) -> str:
    return f"{APPEND_MARKER_PREFIX}:{work_id}:{section_id}"


def remove_marked_blocks_for_work(existing_text: str, work_id: str) -> str:
    normalized_existing = normalize_text(existing_text)
    if not normalized_existing or not work_id:
        return normalized_existing
    pattern = re.compile(
        rf"<!--\s*(?P<marker>{re.escape(APPEND_MARKER_PREFIX)}:{re.escape(work_id)}:[^>]+)\s*-->"
        rf".*?"
        rf"<!--\s*/(?P=marker)\s*-->",
        re.DOTALL,
    )
    cleaned = pattern.sub("", normalized_existing)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def source_note_work_title(source_note: str) -> str | None:
    text = normalize_text(source_note)
    if not text:
        return None
    parts = [part.strip() for part in text.split(" | ", 1)]
    if len(parts) < 2 or not parts[0]:
        return None
    return parts[0]


def remove_source_notes_for_work(existing_notes: Iterable[str], work_titles: set[str]) -> list[str]:
    if not work_titles:
        return unique_strings(existing_notes)
    filtered: list[str] = []
    for note in existing_notes:
        work_title = source_note_work_title(note)
        if work_title and work_title in work_titles:
            continue
        filtered.append(note)
    return unique_strings(filtered)


def remove_library_links_for_work(existing_links: Iterable[dict[str, str]], work_id: str) -> list[dict[str, str]]:
    if not work_id:
        return unique_links(existing_links)
    prefix = f"{work_id}-"
    filtered = [
        item
        for item in existing_links
        if not (
            normalize_nullable_string(item.get("degree")) == "library"
            and normalize_nullable_string(item.get("slug", "")).startswith(prefix)
        )
    ]
    return unique_links(filtered)


def purge_degree_work_contributions(degree_data: dict[str, Any], operations: list[dict[str, Any]]) -> dict[str, Any]:
    if not operations:
        return degree_data

    work_titles_by_work_id: dict[str, set[str]] = {}
    for operation in operations:
        work_id = normalize_nullable_string(operation.get("work_id"))
        if not work_id:
            continue
        work_titles = work_titles_by_work_id.setdefault(work_id, set())
        for source_note in operation.get("changes", {}).get("source_notes", []):
            work_title = source_note_work_title(source_note)
            if work_title:
                work_titles.add(work_title)

    for entry in degree_data["entries"]:
        for work_id, work_titles in work_titles_by_work_id.items():
            entry["full_summary"] = remove_marked_blocks_for_work(entry.get("full_summary", ""), work_id)
            entry["source_notes"] = remove_source_notes_for_work(entry.get("source_notes", []), work_titles)
            entry["knowledge_links"] = remove_library_links_for_work(entry.get("knowledge_links", []), work_id)

    return refresh_degree_indexes(degree_data)


def append_marked_block(existing_text: str, block_text: str, marker_id: str) -> str:
    if not normalize_text(block_text):
        return normalize_text(existing_text)
    marker = f"<!-- {marker_id} -->"
    closing = f"<!-- /{marker_id} -->"
    normalized_existing = normalize_text(existing_text)
    if marker in normalized_existing:
        return normalized_existing
    block = f"{marker}\n{block_text.strip()}\n{closing}"
    if not normalized_existing:
        return block
    return f"{normalized_existing}\n\n{block}"


def append_unique_paragraph(existing_text: str, new_text: str) -> str:
    existing = normalize_text(existing_text)
    incoming = normalize_text(new_text)
    if not incoming:
        return existing
    if not existing:
        return incoming
    if normalize_lookup_text(incoming) in normalize_lookup_text(existing):
        return existing
    return f"{existing}\n\n{incoming}"


def apply_degree_patch(degree_data: dict[str, Any], operation: dict[str, Any]) -> None:
    entry = degree_data["entryBySlug"].get(operation["slug"])
    if not entry:
        raise KeyError(f"Missing target entry for patch: {operation['slug']}")

    marker_id = operation["marker_id"]
    full_summary_block = normalize_text(operation["changes"].get("full_summary_block"))
    if full_summary_block:
        entry["full_summary"] = append_marked_block(entry.get("full_summary", ""), full_summary_block, marker_id)

    entry["practical_elements"] = unique_strings(
        list(entry.get("practical_elements", [])) + list(operation["changes"].get("practical_elements", []))
    )
    entry["symbolic_meaning"] = append_unique_paragraph(
        entry.get("symbolic_meaning", ""), operation["changes"].get("symbolic_meaning", "")
    )
    entry["candidate_lesson"] = append_unique_paragraph(
        entry.get("candidate_lesson", ""), operation["changes"].get("candidate_lesson", "")
    )
    entry["tradition_notes"] = unique_strings(
        list(entry.get("tradition_notes", [])) + list(operation["changes"].get("tradition_notes", []))
    )
    entry["caution_notes"] = unique_strings(
        list(entry.get("caution_notes", [])) + list(operation["changes"].get("caution_notes", []))
    )
    entry["source_notes"] = unique_strings(
        list(entry.get("source_notes", [])) + list(operation["changes"].get("source_notes", []))
    )
    entry["knowledge_links"] = unique_links(
        list(entry.get("knowledge_links", [])) + list(operation["changes"].get("knowledge_links", []))
    )


def apply_degree_patches(degree_data: dict[str, Any], operations: list[dict[str, Any]]) -> dict[str, Any]:
    degree_data = purge_degree_work_contributions(degree_data, operations)
    for operation in operations:
        apply_degree_patch(degree_data, operation)
    return refresh_degree_indexes(degree_data)


def build_degree_patch_operation(
    *,
    target_slug: str,
    target_degree: str,
    work_id: str,
    work_title: str,
    section_id: str,
    section_title: str,
    chapter_slug: str,
    chapter_degree: str,
    source_notes: list[str],
    section_summary: str | None = None,
    practical_elements: list[str] | None = None,
    symbolic_meaning: str | None = None,
    candidate_lesson: str | None = None,
    tradition_notes: list[str] | None = None,
    caution_notes: list[str] | None = None,
    section_summary_he: str | None = None,
    practical_elements_he: list[str] | None = None,
    symbolic_meaning_he: str | None = None,
    candidate_lesson_he: str | None = None,
    tradition_notes_he: list[str] | None = None,
    caution_notes_he: list[str] | None = None,
    related_degree_links: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    summary_text = normalize_text(section_summary) or normalize_text(section_summary_he)
    practical_items = unique_strings(practical_elements if practical_elements is not None else practical_elements_he or [])
    symbolic_text = normalize_text(symbolic_meaning) or normalize_text(symbolic_meaning_he)
    lesson_text = normalize_text(candidate_lesson) or normalize_text(candidate_lesson_he)
    tradition_items = unique_strings(tradition_notes if tradition_notes is not None else tradition_notes_he or [])
    caution_items = unique_strings(caution_notes if caution_notes is not None else caution_notes_he or [])
    marker_id = build_provenance_marker(work_id, section_id)
    full_summary_lines = [
        f"### Enrichment from {work_title}",
        f"Source section: {section_title}",
        "",
        summary_text,
    ]
    full_summary_block = "\n".join(line for line in full_summary_lines if line is not None).strip()
    knowledge_links = [{"slug": chapter_slug, "degree": chapter_degree}]
    knowledge_links.extend(related_degree_links or [])
    return {
        "slug": target_slug,
        "degree": target_degree,
        "work_id": work_id,
        "section_id": section_id,
        "marker_id": marker_id,
        # New staged operations are suggestions until a human review moves
        # them forward (see prod/schema/review_states.py).
        "review_state": "suggested",
        "changes": {
            "full_summary_block": full_summary_block if summary_text else "",
            "practical_elements": practical_items,
            "symbolic_meaning": symbolic_text,
            "candidate_lesson": lesson_text,
            "tradition_notes": tradition_items,
            "caution_notes": caution_items,
            "source_notes": source_notes,
            "knowledge_links": knowledge_links,
        },
    }


def build_source_note(
    *,
    work_title: str,
    section_title: str,
    source_path: str,
    source_anchor: str | None,
    source_order: int,
) -> str:
    anchor_fragment = f"#{source_anchor}" if source_anchor else ""
    return f"{work_title} | {section_title} | {source_path}{anchor_fragment} | section {source_order}"


def build_cross_degree_link(slug: str, degree: str) -> dict[str, str]:
    return {"slug": slug, "degree": degree}
