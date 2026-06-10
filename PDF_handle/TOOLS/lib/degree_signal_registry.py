from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .common import TOOLS_DIR


DEFAULT_DEGREE_REGISTRY_PATH = TOOLS_DIR / "data" / "degree_terms_registry.json"
VALID_STRENGTHS = {"strong", "medium", "weak"}
VALID_DEGREES = {1, 2, 3}


def normalize_degree_signal_text(text: str | None) -> str:
    raw = (text or "").lower()
    raw = raw.replace("\u2010", " ").replace("\u2011", " ").replace("\u2012", " ")
    raw = raw.replace("\u2013", " ").replace("\u2014", " ").replace("-", " ")
    raw = raw.replace("/", " ").replace("\\", " ")
    raw = re.sub(r"['\"`(){}\[\],.:;!?<>|+=*_~]", " ", raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def _ensure_list(value: Any, *, field_name: str, entry_id: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"Registry entry {entry_id} field {field_name} must be a list.")
    return value


def _normalize_variants(entry: dict[str, Any]) -> list[str]:
    variants: list[str] = []
    for raw_variant in (
        [entry.get("canonical_term")]
        + list(entry.get("hebrew_variants", []))
        + list(entry.get("english_variants", []))
        + list(entry.get("normalized_variants", []))
    ):
        normalized = normalize_degree_signal_text(str(raw_variant or ""))
        if normalized and normalized not in variants:
            variants.append(normalized)
    return variants


def _validate_entry(entry: dict[str, Any]) -> dict[str, Any]:
    entry_id = str(entry.get("id") or "").strip()
    if not entry_id:
        raise ValueError("Registry entry is missing id.")
    canonical_term = str(entry.get("canonical_term") or "").strip()
    if not canonical_term:
        raise ValueError(f"Registry entry {entry_id} is missing canonical_term.")
    degree_hint = entry.get("degree_hint")
    if degree_hint not in VALID_DEGREES:
        raise ValueError(f"Registry entry {entry_id} has invalid degree_hint: {degree_hint!r}")
    strength = str(entry.get("strength") or "").strip().lower()
    if strength not in VALID_STRENGTHS:
        raise ValueError(f"Registry entry {entry_id} has invalid strength: {strength!r}")
    concept_type = str(entry.get("concept_type") or "").strip()
    if not concept_type:
        raise ValueError(f"Registry entry {entry_id} is missing concept_type.")
    families = [str(item).strip() for item in _ensure_list(entry.get("families", []), field_name="families", entry_id=entry_id) if str(item).strip()]
    hebrew_variants = [str(item).strip() for item in _ensure_list(entry.get("hebrew_variants", []), field_name="hebrew_variants", entry_id=entry_id) if str(item).strip()]
    english_variants = [str(item).strip() for item in _ensure_list(entry.get("english_variants", []), field_name="english_variants", entry_id=entry_id) if str(item).strip()]
    normalized_variants = [str(item).strip() for item in _ensure_list(entry.get("normalized_variants", []), field_name="normalized_variants", entry_id=entry_id) if str(item).strip()]
    cooccurrence_preferred = [str(item).strip() for item in _ensure_list(entry.get("cooccurrence_preferred", []), field_name="cooccurrence_preferred", entry_id=entry_id) if str(item).strip()]
    standalone_allowed = bool(entry.get("standalone_allowed"))
    purity_weights = entry.get("purity_weights")
    if not isinstance(purity_weights, dict):
        raise ValueError(f"Registry entry {entry_id} is missing purity_weights.")
    for key in (
        "native_degree_1",
        "native_degree_2",
        "native_degree_3",
        "foreign_risk_if_target_1",
        "foreign_risk_if_target_2",
        "foreign_risk_if_target_3",
    ):
        if not isinstance(purity_weights.get(key), int):
            raise ValueError(f"Registry entry {entry_id} purity_weights[{key}] must be an integer.")

    validated = {
        "id": entry_id,
        "canonical_term": canonical_term,
        "degree_hint": degree_hint,
        "strength": strength,
        "concept_type": concept_type,
        "families": families,
        "hebrew_variants": hebrew_variants,
        "english_variants": english_variants,
        "normalized_variants": normalized_variants,
        "cooccurrence_preferred": cooccurrence_preferred,
        "standalone_allowed": standalone_allowed,
        "purity_weights": purity_weights,
        "notes": str(entry.get("notes") or "").strip(),
    }
    validated["normalized_variants"] = _normalize_variants(validated)
    validated["normalized_cooccurrence_preferred"] = [
        normalize_degree_signal_text(item)
        for item in cooccurrence_preferred
        if normalize_degree_signal_text(item)
    ]
    return validated


def load_degree_registry(path: Path | None = None) -> dict[str, Any]:
    registry_path = (path or DEFAULT_DEGREE_REGISTRY_PATH).resolve()
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Degree registry must be a JSON object: {registry_path}")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"Degree registry entries must be a JSON array: {registry_path}")

    normalized_entries: list[dict[str, Any]] = []
    entries_by_id: dict[str, dict[str, Any]] = {}
    variant_index: dict[str, list[dict[str, Any]]] = {}
    family_index: dict[str, list[str]] = {}
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise ValueError(f"Degree registry contains a non-object entry: {raw_entry!r}")
        entry = _validate_entry(raw_entry)
        if entry["id"] in entries_by_id:
            raise ValueError(f"Duplicate degree registry id: {entry['id']}")
        entries_by_id[entry["id"]] = entry
        normalized_entries.append(entry)
        for family in entry["families"]:
            family_index.setdefault(family, []).append(entry["id"])
        for variant in entry["normalized_variants"]:
            bucket = variant_index.setdefault(variant, [])
            if entry not in bucket:
                bucket.append(entry)

    return {
        "schema_version": str(payload.get("schema_version") or ""),
        "path": registry_path,
        "path_text": str(registry_path),
        "raw": payload,
        "entries": normalized_entries,
        "entries_by_id": entries_by_id,
        "variant_index": variant_index,
        "family_index": family_index,
    }
