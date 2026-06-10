from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from PDF_handle.prod.core.io import read_json


PROMOTABLE_DECISIONS = ("new_canonical_topic", "later_degree_candidate")
ENCYCLOPEDIA_DECISIONS = ("encyclopedia_candidate",)
DISCOVERY_DECISIONS = (
    "existing_match",
    "new_canonical_topic",
    "later_degree_candidate",
    "reject_or_noise",
    "encyclopedia_candidate",
)
DEGREE_ORDER = ("library", "level1", "level2", "level3", "unknown")
REQUIRED_DISCOVERY_FIELDS = (
    "work_id",
    "section_id",
    "decision",
    "candidate_degree",
    "unit_kind",
    "confidence",
    "reason_codes",
)


PAGE_TITLE_RE = re.compile(r"^page\s+\d+[a-z]?$", re.IGNORECASE)


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_reason_codes(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [normalize_text(item) for item in value if normalize_text(item)]


def contains_hebrew(value: Any) -> bool:
    if isinstance(value, list):
        return any(contains_hebrew(item) for item in value)
    return any("\u0590" <= char <= "\u05FF" for char in normalize_text(value))


def is_page_title(value: Any) -> bool:
    return bool(PAGE_TITLE_RE.fullmatch(normalize_text(value)))


def parse_section_number(section_id: Any) -> int:
    text = normalize_text(section_id)
    match = re.search(r"(\d+)$", text)
    return int(match.group(1)) if match else 0


def iter_staged_discovery_files(staged_runs_root: Path, selected_work_ids: set[str] | None = None) -> Iterable[Path]:
    root = staged_runs_root.resolve()
    for discovery_path in sorted(root.glob("*/discovery_rows.json")):
        rows = load_discovery_rows(discovery_path)
        if selected_work_ids:
            work_ids = {normalize_text(row.get("work_id")) for row in rows}
            if not (work_ids & selected_work_ids):
                continue
        yield discovery_path


def load_discovery_rows(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path.resolve())
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def stable_candidate_id(row: dict[str, Any], *, staging_name: str) -> str:
    parts = [
        staging_name,
        normalize_text(row.get("work_id")),
        normalize_text(row.get("section_id")),
        normalize_text(row.get("decision")),
        normalize_text(row.get("candidate_degree")),
        normalize_text(row.get("normalized_title")),
    ]
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]
    section = normalize_text(row.get("section_id")) or "section"
    decision = normalize_text(row.get("decision")) or "decision"
    degree = normalize_text(row.get("candidate_degree")) or "unknown"
    return f"{staging_name}:{section}:{decision}:{degree}:{digest}"


def degree_sort_key(degree: Any) -> tuple[int, str]:
    text = normalize_text(degree) or "unknown"
    try:
        return (DEGREE_ORDER.index(text), text)
    except ValueError:
        return (len(DEGREE_ORDER), text)


def discovery_row_sort_key(row: dict[str, Any], *, staging_name: str) -> tuple[Any, ...]:
    return (
        degree_sort_key(row.get("candidate_degree")),
        normalize_text(row.get("decision")),
        normalize_text(row.get("work_id")) or staging_name,
        parse_section_number(row.get("section_id")),
        normalize_text(row.get("normalized_title")),
    )


def summarize_discovery_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = Counter(normalize_text(row.get("decision")) or "missing" for row in rows)
    degrees = Counter(normalize_text(row.get("candidate_degree")) or "missing" for row in rows)
    unit_kinds = Counter(normalize_text(row.get("unit_kind")) or "missing" for row in rows)
    promotable_rows = [row for row in rows if row.get("decision") in PROMOTABLE_DECISIONS]
    return {
        "row_count": len(rows),
        "decision_counts": dict(sorted(decisions.items())),
        "candidate_degree_counts": dict(sorted(degrees.items())),
        "unit_kind_counts": dict(sorted(unit_kinds.items())),
        "promotable_count": len(promotable_rows),
        "promotable_unit_kind_counts": dict(
            sorted(Counter(normalize_text(row.get("unit_kind")) or "missing" for row in promotable_rows).items())
        ),
    }


def validate_discovery_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        missing_fields = [
            field_name
            for field_name in REQUIRED_DISCOVERY_FIELDS
            if field_name not in row or normalize_text(row.get(field_name)) == ""
        ]
        if missing_fields:
            blockers.append(
                {
                    "code": "DISCOVERY_ROW_MISSING_REQUIRED_FIELDS",
                    "row_index": index,
                    "section_id": row.get("section_id"),
                    "missing_fields": missing_fields,
                }
            )

        decision = normalize_text(row.get("decision"))
        if decision and decision not in DISCOVERY_DECISIONS:
            blockers.append(
                {
                    "code": "UNKNOWN_DISCOVERY_DECISION",
                    "row_index": index,
                    "section_id": row.get("section_id"),
                    "decision": decision,
                }
            )

        if decision in PROMOTABLE_DECISIONS:
            if row.get("is_noise_candidate") is True:
                blockers.append(
                    {
                        "code": "PROMOTABLE_ROW_MARKED_NOISE",
                        "row_index": index,
                        "section_id": row.get("section_id"),
                        "decision": decision,
                    }
                )
            if normalize_text(row.get("unit_kind")) != "topic":
                blockers.append(
                    {
                        "code": "PROMOTABLE_ROW_NOT_TOPIC_UNIT",
                        "row_index": index,
                        "section_id": row.get("section_id"),
                        "decision": decision,
                        "unit_kind": row.get("unit_kind"),
                    }
                )
            if is_page_title(row.get("normalized_title")):
                blockers.append(
                    {
                        "code": "PROMOTABLE_ROW_HAS_PAGE_TITLE",
                        "row_index": index,
                        "section_id": row.get("section_id"),
                        "decision": decision,
                        "normalized_title": row.get("normalized_title"),
                    }
                )
            if normalize_text(row.get("candidate_degree")) in {"", "missing"}:
                blockers.append(
                    {
                        "code": "PROMOTABLE_ROW_MISSING_CANDIDATE_DEGREE",
                        "row_index": index,
                        "section_id": row.get("section_id"),
                        "decision": decision,
                    }
                )
            if not normalize_reason_codes(row.get("reason_codes")):
                blockers.append(
                    {
                        "code": "PROMOTABLE_ROW_MISSING_REASON_CODES",
                        "row_index": index,
                        "section_id": row.get("section_id"),
                        "decision": decision,
                    }
                )
            if row.get("source_title") and is_page_title(row.get("source_title")):
                warnings.append(
                    {
                        "code": "PROMOTABLE_ROW_SOURCE_TITLE_IS_PAGE_LABEL",
                        "row_index": index,
                        "section_id": row.get("section_id"),
                        "decision": decision,
                        "source_title": row.get("source_title"),
                        "normalized_title": row.get("normalized_title"),
                    }
                )
            if contains_hebrew(row.get("new_topic_hints")):
                warnings.append(
                    {
                        "code": "PROMOTABLE_ROW_HINTS_CONTAIN_HEBREW",
                        "row_index": index,
                        "section_id": row.get("section_id"),
                        "decision": decision,
                    }
                )
    return blockers, warnings
