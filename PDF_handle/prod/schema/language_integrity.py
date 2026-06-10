from __future__ import annotations

import re
from typing import Any

from PDF_handle.prod.companion_contract import companion_candidate_degree, companion_candidate_slug, materialize_companion_payload
from PDF_handle.prod.core.io import utc_timestamp
from PDF_handle.prod.schema.data import infer_language_contract_fields, normalize_nullable_string, normalize_text


PROTECTED_TEXT_FIELDS = ("title", "short_summary", "candidate_lesson", "symbolic_meaning")
READING_LAYER_FIELDS = ("basic", "symbolic", "advanced")
HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
LATIN_RE = re.compile(r"[A-Za-z]")


def text_script_flags(value: Any) -> dict[str, bool]:
    if isinstance(value, list):
        text = " ".join(str(item) for item in value if str(item).strip())
    else:
        text = str(value or "")
    return {
        "has_hebrew": bool(HEBREW_RE.search(text)),
        "has_latin": bool(LATIN_RE.search(text)),
        "text": text.strip(),
    }


def append_finding(findings: list[dict[str, Any]], **payload: Any) -> None:
    findings.append(payload)


def audit_dataset_entries(
    datasets: dict[str, dict[str, Any]],
    *,
    findings: list[dict[str, Any]],
) -> None:
    for degree_id, dataset in datasets.items():
        for entry in dataset.get("entries", []):
            metadata = infer_language_contract_fields(entry)
            slug = normalize_text(entry.get("slug"))
            legacy_language = normalize_nullable_string(entry.get("language"))
            parallel_entry = normalize_nullable_string(entry.get("parallel_entry"))

            if metadata["display_language"] and metadata["canonical_language"]:
                if metadata["display_language"] != metadata["canonical_language"] and not parallel_entry:
                    append_finding(
                        findings,
                        severity="warning",
                        kind="localized_primary_without_pair",
                        scope="dataset_entry",
                        degree=degree_id,
                        slug=slug,
                        field=None,
                        message=(
                            "Entry display_language differs from canonical_language but no "
                            "parallel_entry bridge exists."
                        ),
                        details={
                            "display_language": metadata["display_language"],
                            "canonical_language": metadata["canonical_language"],
                            "translation_status": metadata["translation_status"],
                            "language_integrity_status": metadata["language_integrity_status"],
                        },
                    )

            if legacy_language and metadata["display_language"] and legacy_language != metadata["display_language"]:
                append_finding(
                    findings,
                    severity="info",
                    kind="legacy_language_alias_drift",
                    scope="dataset_entry",
                    degree=degree_id,
                    slug=slug,
                    field="language",
                    message="Legacy language field no longer matches the inferred display language.",
                    details={
                        "language": legacy_language,
                        "display_language": metadata["display_language"],
                    },
                )

            for field_name in PROTECTED_TEXT_FIELDS:
                flags = text_script_flags(entry.get(field_name))
                if not flags["text"]:
                    continue
                if metadata["canonical_language"] == "en" and metadata["display_language"] == "en" and flags["has_hebrew"]:
                    append_finding(
                        findings,
                        severity="error",
                        kind="protected_field_cross_language",
                        scope="dataset_entry",
                        degree=degree_id,
                        slug=slug,
                        field=field_name,
                        message="Canonical English entry carries Hebrew text in a protected field.",
                        details={
                            "display_language": metadata["display_language"],
                            "canonical_language": metadata["canonical_language"],
                            "translation_mode": normalize_nullable_string(entry.get("translation_mode")),
                            "preview": flags["text"][:160],
                        },
                    )
                elif flags["has_hebrew"] and flags["has_latin"]:
                    append_finding(
                        findings,
                        severity="info",
                        kind="mixed_script_false_positive_candidate",
                        scope="dataset_entry",
                        degree=degree_id,
                        slug=slug,
                        field=field_name,
                        message="Protected field mixes Hebrew and Latin scripts and may need manual review.",
                        details={"preview": flags["text"][:160]},
                    )

            reading_layers = entry.get("reading_layers")
            if isinstance(reading_layers, dict):
                for layer_name in READING_LAYER_FIELDS:
                    flags = text_script_flags(reading_layers.get(layer_name))
                    if not flags["text"]:
                        continue
                    if metadata["canonical_language"] == "en" and metadata["display_language"] == "en" and flags["has_hebrew"]:
                        append_finding(
                            findings,
                            severity="error",
                            kind="protected_field_cross_language",
                            scope="dataset_entry",
                            degree=degree_id,
                            slug=slug,
                            field=f"reading_layers.{layer_name}",
                            message="Canonical English entry carries Hebrew text in a protected reading layer.",
                            details={
                                "display_language": metadata["display_language"],
                                "canonical_language": metadata["canonical_language"],
                                "preview": flags["text"][:160],
                            },
                        )


def audit_companion_candidates(
    companion_candidates: list[dict[str, Any]],
    *,
    datasets: dict[str, dict[str, Any]],
    findings: list[dict[str, Any]],
) -> None:
    for candidate in companion_candidates:
        try:
            draft_entry = materialize_companion_payload(
                candidate,
                categories_by_degree={degree: dataset["categories"] for degree, dataset in datasets.items() if degree != "library"},
                available_link_targets={
                    degree: set(dataset.get("entryBySlug", {}).keys())
                    for degree, dataset in datasets.items()
                },
            )
        except Exception:
            draft_entry = {}
        metadata = infer_language_contract_fields(draft_entry)
        display_language = metadata["display_language"]
        canonical_language = metadata["canonical_language"]
        if display_language and canonical_language and display_language != canonical_language:
            append_finding(
                findings,
                severity="warning",
                kind="companion_noncanonical_primary_candidate",
                scope="companion_candidate",
                degree=companion_candidate_degree(candidate),
                slug=companion_candidate_slug(candidate) or normalize_text(draft_entry.get("slug")),
                field=None,
                message="Companion candidate would become a non-canonical-language primary record under the current model.",
                details={
                    "work_id": normalize_nullable_string(candidate.get("work_id")),
                    "section_id": normalize_text(candidate.get("section_id")),
                    "display_language": display_language,
                    "canonical_language": canonical_language,
                    "translation_status": metadata["translation_status"],
                    "confidence_reason": normalize_text(candidate.get("confidence_reason")),
                },
            )


def audit_overrides(
    override_bundle: dict[str, Any],
    *,
    datasets: dict[str, dict[str, Any]],
    findings: list[dict[str, Any]],
) -> None:
    for record in override_bundle.get("overrides", []):
        identity = record.get("identity") if isinstance(record.get("identity"), dict) else {}
        degree = normalize_text(identity.get("degree"))
        slug = normalize_text(identity.get("slug"))
        if not degree or not slug:
            continue
        dataset = datasets.get(degree)
        target_entry = dataset.get("entryBySlug", {}).get(slug) if isinstance(dataset, dict) else None
        if not isinstance(target_entry, dict):
            continue
        target_metadata = infer_language_contract_fields(target_entry)
        for field_name, override_value in (record.get("fields") or {}).items():
            if field_name not in PROTECTED_TEXT_FIELDS and not field_name.startswith("reading_layers"):
                continue
            flags = text_script_flags(override_value)
            if not flags["text"]:
                continue
            if (
                target_metadata["canonical_language"] == "en"
                and target_metadata["display_language"] == "en"
                and flags["has_hebrew"]
            ):
                append_finding(
                    findings,
                    severity="warning",
                    kind="override_cross_language_protected_field",
                    scope="override",
                    degree=degree,
                    slug=slug,
                    field=field_name,
                    message="Override applies Hebrew protected-field content onto a canonical English entry.",
                    details={
                        "identity_language": normalize_nullable_string(identity.get("language")),
                        "display_language": target_metadata["display_language"],
                        "canonical_language": target_metadata["canonical_language"],
                        "preview": flags["text"][:160],
                    },
                )


def summarize_findings(
    findings: list[dict[str, Any]],
    *,
    site_root: str,
    staging_dir: str | None,
    companion_candidate_count: int,
) -> dict[str, Any]:
    severity_counts: dict[str, int] = {}
    kind_counts: dict[str, int] = {}
    for finding in findings:
        severity = str(finding.get("severity") or "info")
        kind = str(finding.get("kind") or "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

    status = "pass"
    if severity_counts.get("error"):
        status = "fail"
    elif severity_counts.get("warning"):
        status = "pass-with-warnings"

    return {
        "created_at": utc_timestamp(),
        "status": status,
        "site_root": site_root,
        "staging_dir": staging_dir,
        "finding_counts": {
            "total": len(findings),
            "by_severity": severity_counts,
            "by_kind": kind_counts,
        },
        "companion_candidate_count": companion_candidate_count,
        "heuristic_false_positive_kinds": ["mixed_script_false_positive_candidate"],
        "risk_notes": [
            "Legacy records rely on inferred source/canonical/display language until explicit metadata is backfilled.",
            "Script-based detection can flag mixed Hebrew/English proper nouns as review candidates.",
            "Derived canonical_entry_id is deterministic for V1 dry-run evidence, not a migration-grade identifier yet.",
        ],
    }


def build_language_integrity_report(
    *,
    datasets: dict[str, dict[str, Any]],
    override_bundle: dict[str, Any],
    companion_candidates: list[dict[str, Any]],
    site_root: str,
    staging_dir: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    audit_dataset_entries(datasets, findings=findings)
    audit_companion_candidates(companion_candidates, datasets=datasets, findings=findings)
    audit_overrides(override_bundle, datasets=datasets, findings=findings)
    summary = summarize_findings(
        findings,
        site_root=site_root,
        staging_dir=staging_dir,
        companion_candidate_count=len(companion_candidates),
    )
    return summary, findings
