from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from PDF_handle.prod.core.io import read_json


ENTRY_DEFAULTS: dict[str, Any] = {
    "title": "",
    "slug": "",
    "type": "topic",
    "degree": "",
    "applies_to_degrees": [],
    "category": "",
    "parent_topic": None,
    "aliases": [],
    "keywords": [],
    "related_topics": [],
    "short_summary": "",
    "full_summary": "",
    "practical_elements": [],
    "symbolic_meaning": "",
    "candidate_lesson": "",
    "tradition_notes": [],
    "caution_notes": [],
    "source_notes": [],
    "language": None,
    "work_id": None,
    "work_title": "",
    "source_kind": None,
    "source_path": None,
    "source_anchor": None,
    "source_heading": None,
    "source_order": None,
    "parallel_entry": None,
    "translation_mode": None,
    "canonical_entry_id": None,
    "source_language": None,
    "canonical_language": None,
    "display_language": None,
    "localization_group_id": None,
    "available_locales": [],
    "translation_status": None,
    "language_integrity_status": None,
    "knowledge_links": [],
    "chapter_toc": [],
    "visibility_level": "internal",
    "sensitivity_level": "standard",
    "tradition_scope": "variant",
    "status": "draft",
}

REQUIRED_ENTRY_FIELDS = [
    "title",
    "slug",
    "type",
    "degree",
    "applies_to_degrees",
    "category",
    "parent_topic",
    "aliases",
    "keywords",
    "related_topics",
    "short_summary",
    "full_summary",
    "practical_elements",
    "symbolic_meaning",
    "candidate_lesson",
    "tradition_notes",
    "caution_notes",
    "source_notes",
    "tradition_scope",
    "status",
]

VALID_TYPES = {
    "topic",
    "concept",
    "category",
    "glossary",
    "hub",
    "symbol",
    "ceremony",
    "connector",
    "book",
    "chapter",
}
VALID_STATUS = {"draft", "reviewed", "published"}
VALID_TRADITION_SCOPE = {"universal", "common", "variant", "interpretive"}
VALID_VISIBILITY_LEVEL = {"internal", "restricted", "editorial"}
VALID_SENSITIVITY_LEVEL = {"standard", "guarded", "sensitive"}
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_string_array(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_nullable_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_lookup_text(text: str) -> str:
    normalized = normalize_text(text).lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def normalize_nullable_number(value: Any) -> int | float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return number


def normalize_locale_list(value: Any) -> list[str]:
    locales = [item for item in normalize_string_array(value) if item in {"en", "he"}]
    return unique_strings(locales)


def unique_strings(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        text = normalize_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


def derive_canonical_entry_id(entry: dict[str, Any]) -> str | None:
    explicit = normalize_nullable_string(entry.get("canonical_entry_id"))
    if explicit:
        return explicit
    degree = normalize_nullable_string(entry.get("degree")) or "entry"
    work_id = normalize_nullable_string(entry.get("work_id"))
    slug = normalize_nullable_string(entry.get("slug"))
    parallel_entry = normalize_nullable_string(entry.get("parallel_entry"))
    if parallel_entry and slug:
        pair = sorted([slug, parallel_entry])
        pair_token = "::".join(pair)
        if work_id:
            return f"{degree}:{work_id}:{pair_token}"
        return f"{degree}:{pair_token}"
    if work_id and slug:
        return f"{degree}:{work_id}:{slug}"
    if slug:
        return f"{degree}:{slug}"
    return None


def infer_language_contract_fields(entry: dict[str, Any]) -> dict[str, Any]:
    legacy_language = normalize_nullable_string(entry.get("language"))
    translation_mode = normalize_nullable_string(entry.get("translation_mode"))
    source_language = normalize_nullable_string(entry.get("source_language"))
    canonical_language = normalize_nullable_string(entry.get("canonical_language"))
    display_language = normalize_nullable_string(entry.get("display_language")) or legacy_language
    canonical_entry_id = derive_canonical_entry_id(entry)

    if translation_mode == "archivist-hebrew":
        display_language = display_language or "he"
        source_language = source_language or "en"
        canonical_language = canonical_language or "en"
    else:
        source_language = source_language or display_language or legacy_language
        canonical_language = canonical_language or source_language or display_language or legacy_language

    display_language = display_language or canonical_language or source_language
    localization_group_id = normalize_nullable_string(entry.get("localization_group_id")) or canonical_entry_id

    available_locales = normalize_locale_list(entry.get("available_locales"))
    if not available_locales and display_language:
        available_locales = [display_language]
    if display_language and display_language not in available_locales:
        available_locales = unique_strings([display_language, *available_locales])

    translation_status = normalize_nullable_string(entry.get("translation_status"))
    if not translation_status:
        if display_language and canonical_language and display_language != canonical_language:
            translation_status = "localized"
        elif translation_mode:
            translation_status = "translated"
        else:
            translation_status = "source"

    language_integrity_status = normalize_nullable_string(entry.get("language_integrity_status"))
    if not language_integrity_status:
        if display_language and canonical_language and display_language != canonical_language:
            language_integrity_status = "review_required"
        elif not display_language or not canonical_language or not source_language:
            language_integrity_status = "incomplete"
        else:
            language_integrity_status = "legacy"

    return {
        "canonical_entry_id": canonical_entry_id,
        "source_language": source_language,
        "canonical_language": canonical_language,
        "display_language": display_language,
        "localization_group_id": localization_group_id,
        "available_locales": available_locales,
        "translation_status": translation_status,
        "language_integrity_status": language_integrity_status,
    }


def unique_links(items: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    for item in items:
        slug = normalize_nullable_string(item.get("slug"))
        degree = normalize_nullable_string(item.get("degree"))
        if not slug or not degree:
            continue
        key = (degree, slug)
        if key in seen:
            continue
        seen.add(key)
        unique.append({"slug": slug, "degree": degree})
    return unique


def normalize_related_topics(value: Any) -> dict[str, list[str]]:
    if isinstance(value, list):
        return {"prior": [], "companion": normalize_string_array(value), "deeper": []}
    if isinstance(value, dict):
        return {
            "prior": normalize_string_array(value.get("prior")),
            "companion": normalize_string_array(value.get("companion")),
            "deeper": normalize_string_array(value.get("deeper")),
        }
    return {"prior": [], "companion": [], "deeper": []}


def flatten_related_topics(value: Any) -> list[str]:
    related = normalize_related_topics(value)
    return unique_strings(related["prior"] + related["companion"] + related["deeper"])


def normalize_knowledge_links(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    links: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        slug = normalize_nullable_string(item.get("slug"))
        degree = normalize_nullable_string(item.get("degree"))
        if slug and degree:
            links.append({"slug": slug, "degree": degree})
    return unique_links(links)


def normalize_categories(raw_categories: Any) -> dict[str, dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    if isinstance(raw_categories, dict):
        for category_id, raw_category in raw_categories.items():
            normalized[str(category_id)] = {
                "id": str(category_id),
                "title": str((raw_category or {}).get("title") or category_id),
                "symbol": str((raw_category or {}).get("symbol") or "•"),
                "description": normalize_text((raw_category or {}).get("description")),
                "parent_category": normalize_nullable_string((raw_category or {}).get("parent_category")),
            }

    if normalized:
        return normalized

    return {
        "uncategorized": {
            "id": "uncategorized",
            "title": "Uncategorized",
            "symbol": "•",
            "description": "",
            "parent_category": None,
        }
    }


def normalize_entry(
    entry: dict[str, Any],
    *,
    degree_id: str,
    index: int,
    categories: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    normalized = dict(ENTRY_DEFAULTS)
    normalized.update(entry)
    normalized["title"] = str(normalized.get("title") or f"Untitled {index + 1}").strip()
    normalized["slug"] = str(normalized.get("slug") or f"{degree_id}-entry-{index + 1}").strip()
    normalized["type"] = normalized["type"] if normalized.get("type") in VALID_TYPES else "topic"
    normalized["degree"] = str(normalized.get("degree") or degree_id).strip()
    normalized["applies_to_degrees"] = normalize_string_array(normalized.get("applies_to_degrees"))
    if not normalized["applies_to_degrees"]:
        normalized["applies_to_degrees"] = [normalized["degree"]]

    category = normalize_nullable_string(normalized.get("category"))
    normalized["category"] = category if category in categories else next(iter(categories.keys()))
    normalized["parent_topic"] = normalize_nullable_string(normalized.get("parent_topic"))
    normalized["aliases"] = normalize_string_array(normalized.get("aliases"))
    normalized["keywords"] = normalize_string_array(normalized.get("keywords"))
    normalized["related_topics"] = normalize_related_topics(normalized.get("related_topics"))
    normalized["short_summary"] = normalize_text(normalized.get("short_summary"))
    normalized["full_summary"] = normalize_text(normalized.get("full_summary"))
    normalized["practical_elements"] = normalize_string_array(normalized.get("practical_elements"))
    normalized["symbolic_meaning"] = normalize_text(normalized.get("symbolic_meaning"))
    normalized["candidate_lesson"] = normalize_text(normalized.get("candidate_lesson"))
    normalized["tradition_notes"] = normalize_string_array(normalized.get("tradition_notes"))
    normalized["caution_notes"] = normalize_string_array(normalized.get("caution_notes"))
    normalized["source_notes"] = normalize_string_array(normalized.get("source_notes"))
    normalized["language"] = normalize_nullable_string(normalized.get("language"))
    normalized["work_id"] = normalize_nullable_string(normalized.get("work_id"))
    normalized["work_title"] = normalize_text(normalized.get("work_title"))
    normalized["source_kind"] = normalize_nullable_string(normalized.get("source_kind"))
    normalized["source_path"] = normalize_nullable_string(normalized.get("source_path"))
    normalized["source_anchor"] = normalize_nullable_string(normalized.get("source_anchor"))
    normalized["source_heading"] = normalize_nullable_string(normalized.get("source_heading"))
    normalized["source_order"] = normalize_nullable_number(normalized.get("source_order"))
    normalized["parallel_entry"] = normalize_nullable_string(normalized.get("parallel_entry"))
    normalized["translation_mode"] = normalize_nullable_string(normalized.get("translation_mode"))
    normalized.update(infer_language_contract_fields(normalized))
    normalized["knowledge_links"] = normalize_knowledge_links(normalized.get("knowledge_links"))
    normalized["chapter_toc"] = normalize_string_array(normalized.get("chapter_toc"))
    normalized["visibility_level"] = (
        normalized["visibility_level"]
        if normalized.get("visibility_level") in VALID_VISIBILITY_LEVEL
        else "internal"
    )
    normalized["sensitivity_level"] = (
        normalized["sensitivity_level"]
        if normalized.get("sensitivity_level") in VALID_SENSITIVITY_LEVEL
        else "standard"
    )
    normalized["tradition_scope"] = (
        normalized["tradition_scope"]
        if normalized.get("tradition_scope") in VALID_TRADITION_SCOPE
        else "variant"
    )
    normalized["status"] = normalized["status"] if normalized.get("status") in VALID_STATUS else "draft"
    normalized["_order"] = index
    return normalized


def ensure_unique_slugs(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, int] = {}
    unique_entries: list[dict[str, Any]] = []
    for entry in entries:
        candidate = dict(entry)
        base_slug = candidate["slug"]
        count = seen.get(base_slug, 0)
        seen[base_slug] = count + 1
        if count:
            candidate["slug"] = f"{base_slug}-{count + 1}"
        unique_entries.append(candidate)
    return unique_entries


def build_indexes(entries: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    entry_by_slug: dict[str, dict[str, Any]] = {}
    alias_to_slug: dict[str, str] = {}

    for entry in entries:
        entry_by_slug[entry["slug"]] = entry
        for alias in unique_strings([entry["title"], entry["slug"], *entry["aliases"]]):
            key = normalize_lookup_text(alias)
            if key and key not in alias_to_slug:
                alias_to_slug[key] = entry["slug"]

    return entry_by_slug, alias_to_slug


def refresh_degree_indexes(data: dict[str, Any]) -> dict[str, Any]:
    entry_by_slug, alias_to_slug = build_indexes(data["entries"])
    data["entryBySlug"] = entry_by_slug
    data["aliasToSlug"] = alias_to_slug
    return data


def normalize_knowledge_degree(raw: dict[str, Any], degree_id: str) -> dict[str, Any]:
    categories = normalize_categories(raw.get("categories"))
    entries = ensure_unique_slugs(
        [
            normalize_entry(entry, degree_id=degree_id, index=index, categories=categories)
            for index, entry in enumerate(raw.get("entries") or [])
        ]
    )
    normalized = {
        "meta": {
            "degree": raw.get("meta", {}).get("degree") or degree_id,
            "title": raw.get("meta", {}).get("title") or degree_id,
            "updated_at": raw.get("meta", {}).get("updated_at"),
        },
        "categories": categories,
        "entries": entries,
    }
    return refresh_degree_indexes(normalized)


def normalize_legacy_degree(raw: dict[str, Any], degree_id: str) -> dict[str, Any]:
    categories = normalize_categories(raw.get("categories"))
    entries: list[dict[str, Any]] = []
    row = 0
    for category_id, category in (raw.get("categories") or {}).items():
        for topic in (category or {}).get("topics") or []:
            entries.append(
                normalize_entry(
                    {
                        "title": topic.get("title"),
                        "slug": f"{degree_id}-{topic.get('id') or f'topic-{row + 1}'}",
                        "type": "topic",
                        "degree": degree_id,
                        "applies_to_degrees": [degree_id],
                        "category": category_id,
                        "parent_topic": None,
                        "aliases": [],
                        "keywords": normalize_string_array(topic.get("tags")),
                        "related_topics": [f"{degree_id}-{item}" for item in normalize_string_array(topic.get("prerequisites"))],
                        "short_summary": topic.get("summary") or "",
                        "full_summary": topic.get("body") or "",
                        "practical_elements": [],
                        "symbolic_meaning": "",
                        "candidate_lesson": "",
                        "tradition_notes": [],
                        "caution_notes": [],
                        "source_notes": [],
                        "tradition_scope": "variant",
                        "status": "draft",
                        "legacy": {
                            "id": topic.get("id"),
                            "read_time": topic.get("readTime"),
                            "progress": topic.get("progress", 0),
                        },
                    },
                    degree_id=degree_id,
                    index=row,
                    categories=categories,
                )
            )
            row += 1

    normalized = {
        "meta": {
            "degree": raw.get("meta", {}).get("degree") or degree_id,
            "title": raw.get("meta", {}).get("title") or degree_id,
            "updated_at": raw.get("meta", {}).get("updated_at"),
        },
        "categories": categories,
        "entries": ensure_unique_slugs(entries),
    }
    return refresh_degree_indexes(normalized)


def normalize_degree_data(raw: dict[str, Any], degree_id: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid degree JSON for {degree_id}")
    if isinstance(raw.get("entries"), list):
        return normalize_knowledge_degree(raw, degree_id)
    if isinstance(raw.get("categories"), dict):
        return normalize_legacy_degree(raw, degree_id)
    raise ValueError(f"Unsupported degree JSON format for {degree_id}")


def serialize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in entry.items() if key not in {"_order"}}


def serialize_degree_data(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "meta": {
            "degree": data["meta"]["degree"],
            "title": data["meta"]["title"],
            "updated_at": data["meta"].get("updated_at"),
        },
        "categories": {category_id: dict(category) for category_id, category in data["categories"].items()},
        "entries": [serialize_entry(entry) for entry in data["entries"]],
    }


def make_error_path(parts: Iterable[Any]) -> str:
    path = ""
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            if path:
                path += "."
            path += str(part)
    return path or "$"


def custom_validate_degree_data(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return {"ok": False, "validator": "custom", "errors": ["Root value must be an object."], "warnings": warnings}

    meta = data.get("meta")
    categories = data.get("categories")
    entries = data.get("entries")

    if not isinstance(meta, dict):
        errors.append("meta must be an object.")
    else:
        if not normalize_text(meta.get("degree")):
            errors.append("meta.degree is required.")
        if not normalize_text(meta.get("title")):
            errors.append("meta.title is required.")

    if not isinstance(categories, dict):
        errors.append("categories must be an object.")
    else:
        for category_id, category in categories.items():
            if not isinstance(category, dict):
                errors.append(f"categories.{category_id} must be an object.")
                continue
            if not normalize_text(category.get("title")):
                errors.append(f"categories.{category_id}.title is required.")
            if not normalize_text(category.get("symbol")):
                errors.append(f"categories.{category_id}.symbol is required.")

    if not isinstance(entries, list):
        errors.append("entries must be an array.")
    else:
        seen_slugs: set[str] = set()
        for index, entry in enumerate(entries):
            prefix = f"entries[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{prefix} must be an object.")
                continue
            for field_name in REQUIRED_ENTRY_FIELDS:
                if field_name not in entry:
                    errors.append(f"{prefix}.{field_name} is required.")

            slug = normalize_text(entry.get("slug"))
            if not slug:
                errors.append(f"{prefix}.slug is required.")
            elif not SLUG_PATTERN.match(slug):
                errors.append(f"{prefix}.slug is not a valid slug: {slug}")
            elif slug in seen_slugs:
                errors.append(f"{prefix}.slug is duplicated: {slug}")
            else:
                seen_slugs.add(slug)

            if entry.get("type") not in VALID_TYPES:
                errors.append(f"{prefix}.type must be one of {sorted(VALID_TYPES)}.")
            if entry.get("tradition_scope") not in VALID_TRADITION_SCOPE:
                errors.append(f"{prefix}.tradition_scope must be one of {sorted(VALID_TRADITION_SCOPE)}.")
            if entry.get("status") not in VALID_STATUS:
                errors.append(f"{prefix}.status must be one of {sorted(VALID_STATUS)}.")
            if entry.get("visibility_level") not in VALID_VISIBILITY_LEVEL:
                errors.append(f"{prefix}.visibility_level must be one of {sorted(VALID_VISIBILITY_LEVEL)}.")
            if entry.get("sensitivity_level") not in VALID_SENSITIVITY_LEVEL:
                errors.append(f"{prefix}.sensitivity_level must be one of {sorted(VALID_SENSITIVITY_LEVEL)}.")

            for field_name in (
                "applies_to_degrees",
                "aliases",
                "keywords",
                "practical_elements",
                "tradition_notes",
                "caution_notes",
                "source_notes",
                "chapter_toc",
            ):
                if not isinstance(entry.get(field_name), list):
                    errors.append(f"{prefix}.{field_name} must be an array.")

            if not isinstance(entry.get("knowledge_links"), list):
                errors.append(f"{prefix}.knowledge_links must be an array.")
            else:
                for link_index, link in enumerate(entry["knowledge_links"]):
                    if not isinstance(link, dict):
                        errors.append(f"{prefix}.knowledge_links[{link_index}] must be an object.")
                        continue
                    if not normalize_text(link.get("slug")):
                        errors.append(f"{prefix}.knowledge_links[{link_index}].slug is required.")
                    if not normalize_text(link.get("degree")):
                        errors.append(f"{prefix}.knowledge_links[{link_index}].degree is required.")

            related = entry.get("related_topics")
            if not isinstance(related, (list, dict)):
                errors.append(f"{prefix}.related_topics must be an array or object.")
            elif isinstance(related, dict):
                for key in related:
                    if key not in {"prior", "companion", "deeper"}:
                        errors.append(f"{prefix}.related_topics.{key} is not allowed.")
                    elif not isinstance(related[key], list):
                        errors.append(f"{prefix}.related_topics.{key} must be an array.")

            if entry.get("parent_topic") is not None and not isinstance(entry.get("parent_topic"), str):
                errors.append(f"{prefix}.parent_topic must be a string or null.")

    return {"ok": not errors, "validator": "custom", "errors": errors, "warnings": warnings}


def validate_against_schema(data: dict[str, Any], schema_path: Path) -> dict[str, Any]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        result = custom_validate_degree_data(data)
        result["schema_path"] = str(schema_path)
        result["schema_mode"] = "custom-fallback"
        return result

    schema = read_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    return {
        "ok": not errors,
        "validator": "jsonschema",
        "schema_path": str(schema_path),
        "schema_mode": "jsonschema",
        "errors": [f"{make_error_path(error.path)}: {error.message}" for error in errors],
        "warnings": [],
    }


def validate_degree_references(datasets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    global_index = {
        degree_id: {entry["slug"] for entry in dataset["entries"]}
        for degree_id, dataset in datasets.items()
    }

    for degree_id, dataset in datasets.items():
        local_index = global_index.get(degree_id, set())
        for entry in dataset["entries"]:
            slug = entry["slug"]
            if entry.get("parent_topic") and entry["parent_topic"] not in local_index:
                errors.append(f"{degree_id}:{slug} has missing parent_topic -> {entry['parent_topic']}")
            for related_slug in flatten_related_topics(entry.get("related_topics")):
                if related_slug not in local_index:
                    errors.append(f"{degree_id}:{slug} has missing related_topics ref -> {related_slug}")
            parallel_entry = normalize_nullable_string(entry.get("parallel_entry"))
            if parallel_entry and parallel_entry not in local_index:
                errors.append(f"{degree_id}:{slug} has missing parallel_entry -> {parallel_entry}")
            elif parallel_entry:
                parallel_target = dataset["entryBySlug"][parallel_entry]
                if parallel_target["slug"] == slug:
                    errors.append(f"{degree_id}:{slug} parallel_entry cannot point to itself.")
                reverse_parallel = normalize_nullable_string(parallel_target.get("parallel_entry"))
                if reverse_parallel != slug:
                    errors.append(
                        f"{degree_id}:{slug} parallel_entry must be bidirectional -> {parallel_entry} does not point back."
                    )
                entry_language = normalize_nullable_string(entry.get("language"))
                target_language = normalize_nullable_string(parallel_target.get("language"))
                if entry_language and target_language and entry_language == target_language:
                    errors.append(
                        f"{degree_id}:{slug} parallel_entry pair must not share the same language -> {entry_language}."
                    )
                elif not entry_language or not target_language:
                    warnings.append(
                        f"{degree_id}:{slug} parallel_entry pair is missing language metadata for full validation."
                    )
                entry_work_id = normalize_nullable_string(entry.get("work_id"))
                target_work_id = normalize_nullable_string(parallel_target.get("work_id"))
                if entry_work_id and target_work_id and entry_work_id != target_work_id:
                    errors.append(
                        f"{degree_id}:{slug} parallel_entry pair must stay in the same work family -> {entry_work_id} != {target_work_id}."
                    )
            for link in entry.get("knowledge_links", []):
                target_degree = normalize_nullable_string(link.get("degree"))
                target_slug = normalize_nullable_string(link.get("slug"))
                if not target_degree or not target_slug:
                    continue
                if target_degree not in global_index or target_slug not in global_index[target_degree]:
                    errors.append(f"{degree_id}:{slug} has missing knowledge_links ref -> {target_degree}:{target_slug}")

    return {"ok": not errors, "errors": errors, "warnings": warnings}
