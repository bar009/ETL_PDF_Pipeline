from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PDF_handle.prod.core.io import read_json_if_exists, utc_timestamp
from PDF_handle.prod.schema.data import (
    normalize_nullable_number,
    normalize_nullable_string,
    normalize_text,
    refresh_degree_indexes,
    unique_strings,
)


OVERRIDE_SCHEMA_VERSION = 1
OVERRIDE_STATUSES = {"active", "stale", "orphaned", "conflict"}
OVERRIDABLE_FIELDS = {
    "title",
    "short_summary",
    "candidate_lesson",
    "symbolic_meaning",
    "tradition_notes",
    "caution_notes",
    "source_notes",
    "work_title",
    "source_kind",
    "source_path",
    "source_anchor",
    "source_heading",
    "source_order",
    "parallel_entry",
    "translation_mode",
    # v0.5 mode hooks — Learning
    "why_now",
    "takeaway",
    "next_step_ids",
    "prerequisite_ids",
    # v0.5 mode hooks — Encyclopedia
    "definition_line",
    "placement_note",
    # v0.5 mode hooks — Research
    "provenance_note",
    "comparison_ids",
    "uncertainty_note",
    "source_strength",
}
TEXT_OVERRIDE_FIELDS = {
    "title",
    "short_summary",
    "candidate_lesson",
    "symbolic_meaning",
    "work_title",
    "source_kind",
    "source_path",
    "source_anchor",
    "source_heading",
    "parallel_entry",
    "translation_mode",
    # v0.5 mode hooks — text fields
    "why_now",
    "takeaway",
    "definition_line",
    "placement_note",
    "provenance_note",
    "uncertainty_note",
    "source_strength",
}
LIST_OVERRIDE_FIELDS = {
    "tradition_notes",
    "caution_notes",
    "source_notes",
    # v0.5 mode hooks — list fields
    "next_step_ids",
    "prerequisite_ids",
    "comparison_ids",
}
NUMBER_OVERRIDE_FIELDS = {"source_order"}
OVERRIDE_FIELD_GROUPS = {
    "title": "title",
    "short_summary": "short_summary",
    "candidate_lesson": "candidate_lesson",
    "symbolic_meaning": "symbolic_meaning",
    "tradition_notes": "tradition_notes",
    "caution_notes": "caution_notes",
    "source_notes": "source_notes",
    "work_title": "provenance",
    "source_kind": "provenance",
    "source_path": "provenance",
    "source_anchor": "provenance",
    "source_heading": "provenance",
    "source_order": "provenance",
    "parallel_entry": "linking",
    "translation_mode": "linking",
    # v0.5 mode hooks
    "why_now": "mode_hooks",
    "takeaway": "mode_hooks",
    "next_step_ids": "mode_hooks",
    "prerequisite_ids": "mode_hooks",
    "definition_line": "mode_hooks",
    "placement_note": "mode_hooks",
    "provenance_note": "mode_hooks",
    "comparison_ids": "mode_hooks",
    "uncertainty_note": "mode_hooks",
    "source_strength": "mode_hooks",
}
REVIEW_ACTIONS = ("accept_base", "update_override", "reject_candidate")
REVIEWABLE_OVERRIDE_STATUSES = {"stale", "orphaned", "conflict"}


@dataclass(frozen=True)
class OverrideIdentity:
    site_root: str
    degree: str
    slug: str
    language: str | None

    def key(self) -> tuple[str, str, str, str | None]:
        return (self.site_root, self.degree, self.slug, self.language)


def normalize_override_field_value(field: str, value: Any) -> Any:
    if field in LIST_OVERRIDE_FIELDS:
        return unique_strings(value if isinstance(value, list) else [])
    if field in NUMBER_OVERRIDE_FIELDS:
        return normalize_nullable_number(value)
    if field in TEXT_OVERRIDE_FIELDS:
        if field in {"source_kind", "source_path", "source_anchor", "source_heading", "parallel_entry", "translation_mode", "source_strength"}:
            return normalize_nullable_string(value)
        return normalize_text(value)
    raise KeyError(f"Unsupported override field: {field}")


def current_entry_field_value(entry: dict[str, Any], field: str) -> Any:
    return normalize_override_field_value(field, entry.get(field))


def normalize_identity_locator_value(field: str, value: Any) -> Any:
    if field in {"work_id", "source_anchor", "source_heading"}:
        return normalize_nullable_string(value)
    if field == "source_order":
        return normalize_nullable_number(value)
    raise KeyError(f"Unsupported identity locator field: {field}")


def empty_override_bundle(site_root: Path | str) -> dict[str, Any]:
    resolved_site_root = str(Path(site_root).resolve())
    return {
        "version": OVERRIDE_SCHEMA_VERSION,
        "site_root": resolved_site_root,
        "created_at": None,
        "updated_at": None,
        "overrides": [],
    }


def load_override_bundle(path: Path, *, site_root: Path) -> dict[str, Any]:
    payload = read_json_if_exists(path.resolve())
    if payload is None:
        return empty_override_bundle(site_root)
    if isinstance(payload, dict):
        return payload
    return {"version": OVERRIDE_SCHEMA_VERSION, "site_root": str(site_root.resolve()), "overrides": []}


def normalize_override_identity(payload: dict[str, Any], *, default_site_root: Path) -> dict[str, Any]:
    return {
        "site_root": str(Path(payload.get("site_root") or default_site_root).resolve()),
        "degree": normalize_text(payload.get("degree")),
        "slug": normalize_text(payload.get("slug")),
        "language": normalize_nullable_string(payload.get("language")),
        "work_id": normalize_nullable_string(payload.get("work_id")),
        "source_anchor": normalize_nullable_string(payload.get("source_anchor")),
        "source_order": normalize_nullable_number(payload.get("source_order")),
        "source_heading": normalize_nullable_string(payload.get("source_heading")),
    }


def normalize_override_record(payload: dict[str, Any], *, default_site_root: Path) -> dict[str, Any]:
    fields_payload = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
    snapshot_payload = payload.get("base_snapshot") if isinstance(payload.get("base_snapshot"), dict) else {}
    normalized_fields: dict[str, Any] = {}
    normalized_snapshot: dict[str, Any] = {}
    for field, value in fields_payload.items():
        if field not in OVERRIDABLE_FIELDS:
            continue
        normalized_fields[field] = normalize_override_field_value(field, value)
        normalized_snapshot[field] = normalize_override_field_value(field, snapshot_payload.get(field))

    provenance_payload = payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    return {
        "identity": normalize_override_identity(payload.get("identity") if isinstance(payload.get("identity"), dict) else {}, default_site_root=default_site_root),
        "fields": normalized_fields,
        "base_snapshot": normalized_snapshot,
        "provenance": {
            "created_at": normalize_nullable_string(provenance_payload.get("created_at")),
            "updated_at": normalize_nullable_string(provenance_payload.get("updated_at")),
            "source": normalize_nullable_string(provenance_payload.get("source")) or "manual",
            "note": normalize_nullable_string(provenance_payload.get("note")),
            "last_review": provenance_payload.get("last_review") if isinstance(provenance_payload.get("last_review"), dict) else {},
        },
    }


def normalize_override_bundle(payload: dict[str, Any], *, site_root: Path) -> dict[str, Any]:
    normalized = empty_override_bundle(site_root)
    normalized["version"] = int(payload.get("version") or OVERRIDE_SCHEMA_VERSION)
    normalized["site_root"] = str(Path(payload.get("site_root") or site_root).resolve())
    normalized["created_at"] = normalize_nullable_string(payload.get("created_at"))
    normalized["updated_at"] = normalize_nullable_string(payload.get("updated_at"))
    raw_overrides = payload.get("overrides") if isinstance(payload.get("overrides"), list) else []
    normalized["overrides"] = [
        normalize_override_record(item, default_site_root=site_root)
        for item in raw_overrides
        if isinstance(item, dict)
    ]
    return normalized


def validate_override_bundle(bundle: dict[str, Any], *, site_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    expected_site_root = str(site_root.resolve())
    if int(bundle.get("version") or 0) != OVERRIDE_SCHEMA_VERSION:
        errors.append(f"Override bundle version must be {OVERRIDE_SCHEMA_VERSION}.")
    if str(bundle.get("site_root") or "").strip() != expected_site_root:
        errors.append(
            f"Override bundle site_root must match the selected site root: expected {expected_site_root}"
        )

    seen: set[tuple[str, str, str, str | None]] = set()
    for index, record in enumerate(bundle.get("overrides", [])):
        prefix = f"overrides[{index}]"
        identity = record.get("identity") if isinstance(record.get("identity"), dict) else {}
        degree = normalize_text(identity.get("degree"))
        slug = normalize_text(identity.get("slug"))
        if not degree:
            errors.append(f"{prefix}.identity.degree is required.")
        if not slug:
            errors.append(f"{prefix}.identity.slug is required.")
        key = (
            str(identity.get("site_root") or "").strip(),
            degree,
            slug,
            normalize_nullable_string(identity.get("language")),
        )
        if all(key[:3]):
            if key in seen:
                errors.append(f"{prefix} duplicates an existing override identity.")
            seen.add(key)

        fields = record.get("fields") if isinstance(record.get("fields"), dict) else {}
        snapshot = record.get("base_snapshot") if isinstance(record.get("base_snapshot"), dict) else {}
        if not fields:
            errors.append(f"{prefix}.fields must contain at least one overridden field.")
            continue
        if set(fields.keys()) != set(snapshot.keys()):
            errors.append(f"{prefix}.base_snapshot keys must match fields exactly.")
        for field in fields:
            if field not in OVERRIDABLE_FIELDS:
                errors.append(f"{prefix}.fields.{field} is not an allowed override field.")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def override_identity_from_record(record: dict[str, Any]) -> OverrideIdentity:
    identity = record["identity"]
    return OverrideIdentity(
        site_root=str(Path(identity["site_root"]).resolve()),
        degree=str(identity["degree"]),
        slug=str(identity["slug"]),
        language=normalize_nullable_string(identity.get("language")),
    )


def build_override_entry_lookup(datasets: dict[str, dict[str, Any]], identity: OverrideIdentity) -> dict[str, Any] | None:
    dataset = datasets.get(identity.degree)
    if not dataset:
        return None
    entry = dataset["entryBySlug"].get(identity.slug)
    if not entry:
        return None
    return entry


def classify_override_record(record: dict[str, Any], *, datasets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    identity = override_identity_from_record(record)
    entry = build_override_entry_lookup(datasets, identity)
    if entry is None:
        return {
            "identity": record["identity"],
            "status": "orphaned",
            "locator_drift": [],
            "field_results": {},
            "current_entry": None,
            "applied_fields": [],
        }

    locator_drift: list[dict[str, Any]] = []
    identity_language = normalize_nullable_string(record["identity"].get("language"))
    current_language = normalize_nullable_string(entry.get("language"))
    if identity_language != current_language:
        locator_drift.append(
            {
                "field": "language",
                "expected": identity_language,
                "current": current_language,
            }
        )
    for locator_field in ("work_id", "source_anchor", "source_order", "source_heading"):
        expected = normalize_identity_locator_value(locator_field, record["identity"].get(locator_field)) if record["identity"].get(locator_field) is not None else None
        if expected is None:
            continue
        current = normalize_identity_locator_value(locator_field, entry.get(locator_field))
        if current != expected:
            locator_drift.append({"field": locator_field, "expected": expected, "current": current})

    field_results: dict[str, Any] = {}
    conflict_fields: list[str] = []
    applied_fields: list[str] = []
    for field, override_value in record["fields"].items():
        accepted_base = record["base_snapshot"].get(field)
        current_base = current_entry_field_value(entry, field)
        conflict = current_base != accepted_base
        result = {
            "group": OVERRIDE_FIELD_GROUPS[field],
            "accepted_base": accepted_base,
            "current_base": current_base,
            "override_value": override_value,
            "conflict": conflict,
            "required_review_actions": list(REVIEW_ACTIONS) if conflict else [],
        }
        if conflict:
            conflict_fields.append(field)
        else:
            applied_fields.append(field)
        field_results[field] = result

    if conflict_fields:
        status = "conflict"
    elif locator_drift:
        status = "stale"
    else:
        status = "active"
    return {
        "identity": record["identity"],
        "status": status,
        "locator_drift": locator_drift,
        "field_results": field_results,
        "current_entry": {
            "degree": identity.degree,
            "slug": identity.slug,
            "language": current_language,
            "work_id": normalize_nullable_string(entry.get("work_id")),
            "source_anchor": normalize_nullable_string(entry.get("source_anchor")),
            "source_order": normalize_nullable_number(entry.get("source_order")),
            "source_heading": normalize_nullable_string(entry.get("source_heading")),
        },
        "applied_fields": applied_fields if status == "active" else [],
    }


def resolve_override_bundle(bundle: dict[str, Any], *, datasets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    resolutions = [classify_override_record(record, datasets=datasets) for record in bundle.get("overrides", [])]
    summary = {
        "total": len(resolutions),
        "active": len([item for item in resolutions if item["status"] == "active"]),
        "stale": len([item for item in resolutions if item["status"] == "stale"]),
        "orphaned": len([item for item in resolutions if item["status"] == "orphaned"]),
        "conflict": len([item for item in resolutions if item["status"] == "conflict"]),
        "field_conflict_count": sum(
            1
            for item in resolutions
            for field_result in item.get("field_results", {}).values()
            if field_result.get("conflict")
        ),
    }
    conflict_fields = [
        {
            "identity": item["identity"],
            "field": field,
            **field_result,
        }
        for item in resolutions
        for field, field_result in item.get("field_results", {}).items()
        if field_result.get("conflict")
    ]
    return {
        "summary": summary,
        "resolutions": resolutions,
        "field_conflicts": conflict_fields,
    }


def apply_active_overrides(
    datasets: dict[str, dict[str, Any]],
    *,
    resolution_report: dict[str, Any],
    bundle: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    records_by_key = {
        override_identity_from_record(record).key(): record
        for record in bundle.get("overrides", [])
    }
    updated = datasets
    touched_degrees: set[str] = set()
    for resolution in resolution_report.get("resolutions", []):
        if resolution.get("status") != "active":
            continue
        identity = override_identity_from_record({"identity": resolution["identity"]})
        dataset = updated.get(identity.degree)
        if not dataset:
            continue
        entry = dataset["entryBySlug"].get(identity.slug)
        if not entry:
            continue
        record = records_by_key.get(identity.key())
        if not record:
            continue
        for field in resolution.get("applied_fields", []):
            entry[field] = copy.deepcopy(record["fields"][field])
        touched_degrees.add(identity.degree)
    for degree_id in touched_degrees:
        refresh_degree_indexes(updated[degree_id])
    return updated


def reconstruct_base_context_from_overrides(
    datasets: dict[str, dict[str, Any]],
    *,
    bundle: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    reconstructed = copy.deepcopy(datasets)
    touched_degrees: set[str] = set()
    for record in bundle.get("overrides", []):
        identity = override_identity_from_record(record)
        dataset = reconstructed.get(identity.degree)
        if not dataset:
            continue
        entry = dataset["entryBySlug"].get(identity.slug)
        if not entry:
            continue
        for field, base_value in record.get("base_snapshot", {}).items():
            entry[field] = copy.deepcopy(base_value)
        touched_degrees.add(identity.degree)
    for degree_id in touched_degrees:
        refresh_degree_indexes(reconstructed[degree_id])
    return reconstructed


def reconstruct_governance_base_from_effective_datasets(
    datasets: dict[str, dict[str, Any]],
    *,
    bundle: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    reconstructed = copy.deepcopy(datasets)
    touched_degrees: set[str] = set()
    for record in bundle.get("overrides", []):
        identity = override_identity_from_record(record)
        dataset = reconstructed.get(identity.degree)
        if not dataset:
            continue
        entry = dataset["entryBySlug"].get(identity.slug)
        if not entry:
            continue
        for field, accepted_base in record.get("base_snapshot", {}).items():
            current_value = current_entry_field_value(entry, field)
            override_value = record.get("fields", {}).get(field)
            if current_value == override_value:
                entry[field] = copy.deepcopy(accepted_base)
                continue
            if field in LIST_OVERRIDE_FIELDS:
                current_list = current_value if isinstance(current_value, list) else []
                override_list = override_value if isinstance(override_value, list) else []
                accepted_list = accepted_base if isinstance(accepted_base, list) else []
                extras = [item for item in current_list if item not in override_list]
                entry[field] = unique_strings(list(accepted_list) + extras)
                continue
            # For scalar fields with drift beyond the stored override value, preserve the
            # current effective value so governance still sees a real candidate change.
            entry[field] = copy.deepcopy(current_value)
        touched_degrees.add(identity.degree)
    for degree_id in touched_degrees:
        refresh_degree_indexes(reconstructed[degree_id])
    return reconstructed


def normalize_override_review_decisions(payload: Any) -> dict[tuple[str, str, str, str | None], dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    items = payload.get("decisions")
    if not isinstance(items, list):
        return {}
    normalized: dict[tuple[str, str, str, str | None], dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        identity = item.get("identity") if isinstance(item.get("identity"), dict) else {}
        key = (
            str(Path(identity.get("site_root") or "").resolve()) if identity.get("site_root") else "",
            normalize_text(identity.get("degree")),
            normalize_text(identity.get("slug")),
            normalize_nullable_string(identity.get("language")),
        )
        if not all(key[:3]):
            continue
        field_actions = item.get("field_actions") if isinstance(item.get("field_actions"), dict) else {}
        normalized[key] = {
            "field_actions": field_actions,
            "note": normalize_nullable_string(item.get("note")),
        }
    return normalized


def apply_override_review_decisions(
    bundle: dict[str, Any],
    *,
    datasets: dict[str, dict[str, Any]],
    decisions_payload: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    decisions = normalize_override_review_decisions(decisions_payload)
    updated = copy.deepcopy(bundle)
    decision_report = {"applied": [], "skipped": []}
    kept_records: list[dict[str, Any]] = []

    for record in updated.get("overrides", []):
        identity = override_identity_from_record(record)
        decision = decisions.get(identity.key())
        if not decision:
            kept_records.append(record)
            continue
        entry = build_override_entry_lookup(datasets, identity)
        if entry is None:
            decision_report["skipped"].append(
                {"identity": record["identity"], "reason": "entry missing after base apply"}
            )
            kept_records.append(record)
            continue
        field_actions = decision.get("field_actions", {})
        for field, action_payload in list(field_actions.items()):
            if field not in record["fields"]:
                decision_report["skipped"].append(
                    {"identity": record["identity"], "field": field, "reason": "field not present in override"}
                )
                continue
            if not isinstance(action_payload, dict):
                decision_report["skipped"].append(
                    {"identity": record["identity"], "field": field, "reason": "field action must be an object"}
                )
                continue
            action = normalize_text(action_payload.get("action"))
            if action not in REVIEW_ACTIONS:
                decision_report["skipped"].append(
                    {"identity": record["identity"], "field": field, "reason": f"unsupported action {action!r}"}
                )
                continue
            current_base_value = current_entry_field_value(entry, field)
            review_note = normalize_nullable_string(action_payload.get("note"))
            record["provenance"].setdefault("last_review", {})
            record["provenance"]["last_review"][field] = {
                "action": action,
                "reviewed_at": utc_timestamp(),
                "note": review_note,
            }
            record["provenance"]["updated_at"] = utc_timestamp()
            if action == "accept_base":
                record["fields"].pop(field, None)
                record["base_snapshot"].pop(field, None)
            elif action == "update_override":
                if "value" not in action_payload:
                    decision_report["skipped"].append(
                        {"identity": record["identity"], "field": field, "reason": "update_override requires value"}
                    )
                    continue
                record["fields"][field] = normalize_override_field_value(field, action_payload.get("value"))
                record["base_snapshot"][field] = current_base_value
            elif action == "reject_candidate":
                record["base_snapshot"][field] = current_base_value
            decision_report["applied"].append({"identity": record["identity"], "field": field, "action": action})
        if record["fields"]:
            kept_records.append(record)
    updated["overrides"] = kept_records
    updated["updated_at"] = utc_timestamp()
    return updated, decision_report


def build_override_review_template(resolution_report: dict[str, Any]) -> dict[str, Any]:
    decisions: list[dict[str, Any]] = []
    for resolution in resolution_report.get("resolutions", []):
        if resolution.get("status") not in REVIEWABLE_OVERRIDE_STATUSES:
            continue
        field_actions = {
            field: {"action": "", "value": None, "note": ""}
            for field, field_result in resolution.get("field_results", {}).items()
            if field_result.get("conflict")
        }
        decisions.append(
            {
                "identity": resolution["identity"],
                "status": resolution["status"],
                "locator_drift": resolution.get("locator_drift", []),
                "field_actions": field_actions,
                "note": "",
            }
        )
    return {"decisions": decisions}


def extract_override_bundle_from_diff(
    *,
    current_datasets: dict[str, dict[str, Any]],
    base_datasets: dict[str, dict[str, Any]],
    site_root: Path,
) -> dict[str, Any]:
    bundle = empty_override_bundle(site_root)
    bundle["created_at"] = utc_timestamp()
    bundle["updated_at"] = bundle["created_at"]
    overrides: list[dict[str, Any]] = []

    for degree_id, current_dataset in current_datasets.items():
        base_dataset = base_datasets.get(degree_id)
        if not base_dataset:
            continue
        for slug, current_entry in current_dataset["entryBySlug"].items():
            base_entry = base_dataset["entryBySlug"].get(slug)
            if not base_entry:
                continue
            fields: dict[str, Any] = {}
            snapshot: dict[str, Any] = {}
            for field in OVERRIDABLE_FIELDS:
                current_value = current_entry_field_value(current_entry, field)
                base_value = current_entry_field_value(base_entry, field)
                if current_value != base_value:
                    fields[field] = current_value
                    snapshot[field] = base_value
            if not fields:
                continue
            overrides.append(
                {
                    "identity": {
                        "site_root": str(site_root.resolve()),
                        "degree": degree_id,
                        "slug": slug,
                        "language": normalize_nullable_string(current_entry.get("language")),
                        "work_id": normalize_nullable_string(current_entry.get("work_id")),
                        "source_anchor": normalize_nullable_string(current_entry.get("source_anchor")),
                        "source_order": normalize_nullable_number(current_entry.get("source_order")),
                        "source_heading": normalize_nullable_string(current_entry.get("source_heading")),
                    },
                    "fields": fields,
                    "base_snapshot": snapshot,
                    "provenance": {
                        "created_at": bundle["created_at"],
                        "updated_at": bundle["created_at"],
                        "source": "migration",
                        "note": "Extracted from current site root vs clean base comparison.",
                        "last_review": {},
                    },
                }
            )

    bundle["overrides"] = overrides
    return bundle
