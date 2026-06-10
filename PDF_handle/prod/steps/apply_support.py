from __future__ import annotations

from pathlib import Path
from typing import Any

from PDF_handle.prod.companion_contract import companion_candidate_slug
from PDF_handle.prod.core.io import read_json


ApprovalSelector = dict[str, set[str]]


def empty_approval_selector() -> ApprovalSelector:
    return {
        "marker_ids": set(),
        "slugs": set(),
        "work_ids": set(),
        "section_ids": set(),
        "candidate_slugs": set(),
    }


def normalize_approval_payload(payload: Any) -> ApprovalSelector:
    normalized = empty_approval_selector()
    if isinstance(payload, str):
        normalized["marker_ids"].add(payload)
        normalized["slugs"].add(payload)
        normalized["candidate_slugs"].add(payload)
        return normalized
    if isinstance(payload, list):
        for item in payload:
            child = normalize_approval_payload(item)
            for key, values in child.items():
                normalized[key].update(values)
        return normalized
    if not isinstance(payload, dict):
        return normalized

    for key in normalized:
        value = payload.get(key)
        if isinstance(value, list):
            normalized[key].update(str(item).strip() for item in value if str(item).strip())

    operations = payload.get("operations")
    if isinstance(operations, list):
        for item in operations:
            if not isinstance(item, dict):
                continue
            marker_id = str(item.get("marker_id") or "").strip()
            slug = str(item.get("slug") or "").strip()
            work_id = str(item.get("work_id") or "").strip()
            section_id = str(item.get("section_id") or "").strip()
            if marker_id:
                normalized["marker_ids"].add(marker_id)
            if slug:
                normalized["slugs"].add(slug)
            if work_id:
                normalized["work_ids"].add(work_id)
            if section_id:
                normalized["section_ids"].add(section_id)

    entries = payload.get("entries")
    if isinstance(entries, list):
        for item in entries:
            if not isinstance(item, dict):
                continue
            candidate_slug = str(item.get("candidate_slug") or item.get("slug") or "").strip()
            if candidate_slug:
                normalized["candidate_slugs"].add(candidate_slug)

    return normalized


def load_approval_selector(spec: str | None) -> tuple[str, ApprovalSelector]:
    if not spec:
        return "none", empty_approval_selector()
    if spec.strip().lower() == "all":
        return "all", empty_approval_selector()
    payload = read_json(Path(spec).resolve())
    return "selected", normalize_approval_payload(payload)


def operation_matches_selector(operation: dict[str, Any], mode: str, selector: ApprovalSelector) -> bool:
    if mode == "all":
        return True
    if mode == "none":
        return False
    marker_id = str(operation.get("marker_id") or "").strip()
    slug = str(operation.get("slug") or "").strip()
    work_id = str(operation.get("work_id") or "").strip()
    section_id = str(operation.get("section_id") or "").strip()
    return any(
        (
            marker_id and marker_id in selector["marker_ids"],
            slug and slug in selector["slugs"],
            work_id and work_id in selector["work_ids"],
            section_id and section_id in selector["section_ids"],
        )
    )


def companion_matches_selector(candidate: dict[str, Any], mode: str, selector: ApprovalSelector) -> bool:
    if mode == "all":
        return True
    if mode == "none":
        return False
    candidate_slug = companion_candidate_slug(candidate)
    work_id = str(candidate.get("work_id") or "").strip()
    section_id = str(candidate.get("section_id") or "").strip()
    return any(
        (
            candidate_slug and candidate_slug in selector["candidate_slugs"],
            candidate_slug and candidate_slug in selector["slugs"],
            work_id and work_id in selector["work_ids"],
            section_id and section_id in selector["section_ids"],
        )
    )
