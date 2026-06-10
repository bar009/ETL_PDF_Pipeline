from __future__ import annotations

import argparse
import contextlib
import os
import re
import shutil
import sys
import threading
import webbrowser
from functools import partial
from html import escape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import quote


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import ensure_dir, read_json, utc_timestamp, write_json, write_text
from PDF_handle.prod.core.site_data import build_site_data_paths, build_site_data_stat_signatures
from PDF_handle.prod.core.site_roots import get_live_site_root
from PDF_handle.prod.schema import (
    APPEND_MARKER_PREFIX,
    load_override_bundle,
    normalize_degree_data,
    normalize_override_bundle,
    normalize_string_array,
    normalize_text,
    reconstruct_base_context_from_overrides,
    resolve_override_bundle,
    serialize_degree_data,
    validate_override_bundle,
    validate_against_schema,
    validate_degree_references,
)

BASE_DIR = PDF_HANDLE_ROOT
DEFAULT_REPORT_ROOT = BASE_DIR / "qa_reports"
DEFAULT_SITE_ROOT = get_live_site_root()
DEFAULT_SITE_PORT = 4177
MARKER_RE = re.compile(rf"<!--\s*({re.escape(APPEND_MARKER_PREFIX)}:[^>\s]+)\s*-->")
ALLOWED_ACCESS_MODES = {"open", "password", "shared"}
LOCALIZATION_TEXT_FIELDS = (
    "title",
    "short_summary",
    "candidate_lesson",
    "symbolic_meaning",
    "why_now",
    "takeaway",
    "definition_line",
    "placement_note",
    "provenance_note",
    "uncertainty_note",
)
LOCALIZATION_LIST_FIELDS = (
    "tradition_notes",
    "caution_notes",
    "source_notes",
)
LOCALIZATION_READING_LAYER_FIELDS = ("basic", "symbolic", "advanced")
LOCALIZATION_APPROVED_REVIEW_STATUS = "approved"


def log(message: str, *, quiet: bool) -> None:
    if not quiet:
        print(message, flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Step 7: QA live site data and browser flows for a selected site root."
    )
    parser.add_argument("--site-root", type=Path, default=DEFAULT_SITE_ROOT)
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--mode", choices=["full", "data", "browser"], default="full")
    parser.add_argument("--base-url", default=None, help="Optional base URL. If omitted, Step 7 starts a local server.")
    parser.add_argument("--server-port", type=int, default=DEFAULT_SITE_PORT)
    parser.add_argument("--work-id", default=None, help="Optional imported work_id to focus the QA report.")
    parser.add_argument("--level1-password-env", default="FM_LEVEL1_PASSWORD")
    parser.add_argument("--level2-password-env", default="FM_LEVEL2_PASSWORD")
    parser.add_argument("--level3-password-env", default="FM_LEVEL3_PASSWORD")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on validation or browser failures.")
    parser.add_argument("--open-report", action="store_true", help="Open the HTML report after generation.")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output.")
    return parser


def timestamp_for_path() -> str:
    return utc_timestamp().replace(":", "-")


def raw_duplicate_slugs(raw_data: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in raw_data.get("entries", []):
        slug = str(entry.get("slug") or "").strip()
        if not slug:
            continue
        counts[slug] = counts.get(slug, 0) + 1
    return {slug: count for slug, count in counts.items() if count > 1}


def entry_matches_work(entry: dict[str, Any], work_id: str | None, source_book_name: str | None = None) -> bool:
    # Three signals (same shape as postmerge_runner.live_data_contains_work):
    #   1. entry.work_id matches (library entries).
    #   2. PDF_STAGE5:<work_id>:... marker embedded in full_summary by schema.patches.
    #   3. source_book_name substring in source_notes (work_id may differ from
    #      source_book_name; substring on work_id produces false negatives).
    if work_id:
        if str(entry.get("work_id") or "").strip() == work_id:
            return True
        if f"{APPEND_MARKER_PREFIX}:{work_id}:" in str(entry.get("full_summary") or ""):
            return True
        if source_book_name:
            return any(source_book_name in str(note) for note in entry.get("source_notes", []))
        return False

    if str(entry.get("work_id") or "").strip():
        return True
    if APPEND_MARKER_PREFIX in str(entry.get("full_summary") or ""):
        return True
    return False


def marker_duplicates(entries: list[dict[str, Any]], work_id: str | None = None) -> list[dict[str, Any]]:
    duplicates: list[dict[str, Any]] = []
    for entry in entries:
        if work_id and not entry_matches_work(entry, work_id):
            continue
        markers = MARKER_RE.findall(str(entry.get("full_summary") or ""))
        counts: dict[str, int] = {}
        for marker in markers:
            counts[marker] = counts.get(marker, 0) + 1
        for marker, count in counts.items():
            if count > 1:
                duplicates.append({"slug": entry["slug"], "marker_id": marker, "count": count})
    return duplicates


def degree_stats(dataset: dict[str, Any], work_id: str | None = None) -> dict[str, Any]:
    entries = list(dataset["entries"])
    if work_id:
        focused = [entry for entry in entries if entry_matches_work(entry, work_id)]
    else:
        focused = entries

    return {
        "degree": dataset["meta"]["degree"],
        "title": dataset["meta"]["title"],
        "entry_count": len(entries),
        "focused_entry_count": len(focused),
        "book_count": len([entry for entry in entries if entry.get("type") == "book"]),
        "chapter_count": len([entry for entry in entries if entry.get("type") == "chapter"]),
        "focused_book_count": len([entry for entry in focused if entry.get("type") == "book"]),
        "focused_chapter_count": len([entry for entry in focused if entry.get("type") == "chapter"]),
        "updated_at": dataset["meta"].get("updated_at"),
    }


def normalize_review_status(value: Any) -> str:
    return normalize_text(value).lower()


def build_localization_key(*, canonical_entry_id: Any, degree: Any, slug: Any) -> str:
    canonical_id = normalize_text(canonical_entry_id)
    if canonical_id:
        return canonical_id
    degree_text = normalize_text(degree)
    slug_text = normalize_text(slug)
    if degree_text and slug_text:
        return f"{degree_text}:{slug_text}"
    return ""


def build_localization_aliases(*, canonical_entry_id: Any, degree: Any, slug: Any, canonical_key: Any = None) -> list[str]:
    aliases: list[str] = []
    explicit_key = normalize_text(canonical_key)
    if explicit_key:
        aliases.append(explicit_key)
    canonical_id = normalize_text(canonical_entry_id)
    if canonical_id:
        aliases.append(canonical_id)
    degree_text = normalize_text(degree)
    slug_text = normalize_text(slug)
    if degree_text and slug_text:
        aliases.append(f"{degree_text}:{slug_text}")
    return list(dict.fromkeys(alias for alias in aliases if alias))


def build_canonical_localization_fields(entry: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for field_name in LOCALIZATION_TEXT_FIELDS:
        text = normalize_text(entry.get(field_name))
        if text:
            fields[field_name] = text
    for field_name in LOCALIZATION_LIST_FIELDS:
        values = normalize_string_array(entry.get(field_name))
        if values:
            fields[field_name] = values
    reading_layers = entry.get("reading_layers") if isinstance(entry.get("reading_layers"), dict) else {}
    normalized_layers = {
        layer_name: normalize_text(reading_layers.get(layer_name))
        for layer_name in LOCALIZATION_READING_LAYER_FIELDS
        if normalize_text(reading_layers.get(layer_name))
    }
    if normalized_layers:
        fields["reading_layers"] = normalized_layers
    return fields


def normalize_localized_fields(payload: Any) -> dict[str, Any]:
    fields_payload = payload if isinstance(payload, dict) else {}
    normalized: dict[str, Any] = {}
    for field_name in LOCALIZATION_TEXT_FIELDS:
        text = normalize_text(fields_payload.get(field_name))
        if text:
            normalized[field_name] = text
    for field_name in LOCALIZATION_LIST_FIELDS:
        values = normalize_string_array(fields_payload.get(field_name))
        if values:
            normalized[field_name] = values
    reading_layers_payload = fields_payload.get("reading_layers") if isinstance(fields_payload.get("reading_layers"), dict) else {}
    reading_layers = {
        layer_name: normalize_text(reading_layers_payload.get(layer_name))
        for layer_name in LOCALIZATION_READING_LAYER_FIELDS
        if normalize_text(reading_layers_payload.get(layer_name))
    }
    if reading_layers:
        normalized["reading_layers"] = reading_layers
    return normalized


def iter_localizable_field_paths(fields: dict[str, Any]) -> Iterator[tuple[str, Any]]:
    for field_name in LOCALIZATION_TEXT_FIELDS:
        if field_name in fields:
            yield field_name, fields[field_name]
    for field_name in LOCALIZATION_LIST_FIELDS:
        if field_name in fields:
            yield field_name, fields[field_name]
    reading_layers = fields.get("reading_layers") if isinstance(fields.get("reading_layers"), dict) else {}
    for layer_name in LOCALIZATION_READING_LAYER_FIELDS:
        if layer_name in reading_layers:
            yield f"reading_layers.{layer_name}", reading_layers[layer_name]


def validate_hebrew_localization_bundle(
    *,
    site_root: Path,
    datasets: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bundle_path = site_root / "data" / "content.localizations.he.json"
    if not bundle_path.exists():
        return {
            "status": "missing",
            "path": str(bundle_path),
            "entry_count": 0,
            "resolved_entry_count": 0,
            "localized_field_count": 0,
            "fallback_field_count": 0,
            "missing_bundle_fields": [],
            "fallback_examples": [],
        }, []

    raw_bundle = read_json(bundle_path)
    findings: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "status": "ok",
        "path": str(bundle_path),
        "version": raw_bundle.get("version") if isinstance(raw_bundle, dict) else None,
        "locale": raw_bundle.get("locale") if isinstance(raw_bundle, dict) else None,
        "entry_count": 0,
        "resolved_entry_count": 0,
        "localized_field_count": 0,
        "fallback_field_count": 0,
        "missing_bundle_fields": [],
        "fallback_examples": [],
    }
    if not isinstance(raw_bundle, dict):
        findings.append(
            {
                "severity": "error",
                "scope": "localizations",
                "message": "content.localizations.he.json must contain an object.",
                "details": {"path": str(bundle_path)},
            }
        )
        summary["status"] = "invalid"
        return summary, findings

    if normalize_text(raw_bundle.get("locale")).lower() != "he":
        findings.append(
            {
                "severity": "error",
                "scope": "localizations",
                "message": "content.localizations.he.json must declare locale=he.",
                "details": {"path": str(bundle_path), "locale": raw_bundle.get("locale")},
            }
        )

    entries = raw_bundle.get("entries") if isinstance(raw_bundle.get("entries"), list) else []
    summary["entry_count"] = len(entries)

    canonical_entry_by_key: dict[str, dict[str, Any]] = {}
    for degree_id, dataset in datasets.items():
        for entry in dataset.get("entries", []):
            if not isinstance(entry, dict):
                continue
            for canonical_key in build_localization_aliases(
                canonical_entry_id=entry.get("canonical_entry_id"),
                degree=degree_id,
                slug=entry.get("slug"),
            ):
                canonical_entry_by_key[canonical_key] = entry

    seen_keys: set[str] = set()
    fallback_examples: list[dict[str, Any]] = []
    missing_bundle_fields: set[str] = set()

    for item in entries:
        if not isinstance(item, dict):
            findings.append(
                {
                    "severity": "error",
                    "scope": "localizations",
                    "message": "Localization bundle entries must be objects.",
                    "details": {"entry": item},
                }
            )
            continue

        aliases = build_localization_aliases(
            canonical_key=item.get("canonical_key"),
            canonical_entry_id=item.get("canonical_entry_id"),
            degree=item.get("degree"),
            slug=item.get("slug"),
        )
        if not aliases:
            findings.append(
                {
                    "severity": "error",
                    "scope": "localizations",
                    "message": "A localization bundle entry is missing canonical identity.",
                    "details": {"entry": item},
                }
            )
            continue
        canonical_key = aliases[0]
        if canonical_key in seen_keys:
            findings.append(
                {
                    "severity": "error",
                    "scope": "localizations",
                    "message": "Duplicate canonical_key found in content.localizations.he.json.",
                    "details": {"canonical_key": canonical_key},
                }
            )
            continue
        seen_keys.add(canonical_key)

        provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
        if normalize_review_status(provenance.get("review_status")) != LOCALIZATION_APPROVED_REVIEW_STATUS:
            findings.append(
                {
                    "severity": "error",
                    "scope": "localizations",
                    "message": "Localization bundle entries must remain approved-only.",
                    "details": {
                        "canonical_key": canonical_key,
                        "review_status": provenance.get("review_status"),
                    },
                }
            )
            continue

        canonical_entry = next((canonical_entry_by_key.get(alias) for alias in aliases if canonical_entry_by_key.get(alias)), None)
        if canonical_entry is None:
            findings.append(
                {
                    "severity": "error",
                    "scope": "localizations",
                    "message": "A localization bundle entry no longer resolves to canonical site data.",
                    "details": {"canonical_key": canonical_key},
                }
            )
            continue

        fields = normalize_localized_fields(item.get("fields"))
        if not fields:
            findings.append(
                {
                    "severity": "error",
                    "scope": "localizations",
                    "message": "A localization bundle entry has no usable localized fields.",
                    "details": {"canonical_key": canonical_key},
                }
            )
            continue

        summary["resolved_entry_count"] += 1
        localized_paths = {path for path, _value in iter_localizable_field_paths(fields)}
        summary["localized_field_count"] += len(localized_paths)
        canonical_fields = build_canonical_localization_fields(canonical_entry)
        for field_path, field_value in iter_localizable_field_paths(canonical_fields):
            if field_path in localized_paths:
                continue
            summary["fallback_field_count"] += 1
            missing_bundle_fields.add(field_path)
            if len(fallback_examples) < 8:
                fallback_examples.append(
                    {
                        "canonical_key": canonical_key,
                        "field": field_path,
                        "fallback_value": field_value,
                    }
                )

    summary["missing_bundle_fields"] = sorted(missing_bundle_fields)
    summary["fallback_examples"] = fallback_examples
    if any(item["severity"] == "error" for item in findings):
        summary["status"] = "invalid"
    return summary, findings


def validate_degrees_manifest_contract(
    raw_degrees: Any,
    *,
    level3_declared: bool,
    level3_present: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    if not isinstance(raw_degrees, dict):
        finding = {
            "severity": "error",
            "scope": "degrees.json",
            "message": "degrees.json must contain an object keyed by degree id.",
            "details": {"type": type(raw_degrees).__name__},
        }
        return {"ok": False, "issues": [finding], "required_keys_present": False}, [finding]

    def add_issue(severity: str, degree_id: str, message: str, details: dict[str, Any]) -> None:
        issue = {
            "severity": severity,
            "degree": degree_id,
            "message": message,
            "details": details,
        }
        issues.append(issue)
        findings.append(
            {
                "severity": severity,
                "scope": f"degrees.json:{degree_id}",
                "message": message,
                "details": details,
            }
        )

    required_keys = ("level1", "level2", "library")
    required_keys_present = all(key in raw_degrees for key in required_keys)

    for key in required_keys:
        if key not in raw_degrees:
            add_issue(
                "error",
                key,
                "degrees.json is missing a required degree declaration.",
                {"required_degree": key},
            )

    declared_keys = [key for key in required_keys if key in raw_degrees]
    if level3_declared:
        declared_keys.append("level3")

    for degree_id in declared_keys:
        manifest = raw_degrees.get(degree_id)
        if not isinstance(manifest, dict):
            add_issue(
                "error",
                degree_id,
                "The degree declaration must be an object.",
                {"value_type": type(manifest).__name__},
            )
            continue

        access_mode = str(manifest.get("access_mode") or "").strip()
        if not access_mode:
            add_issue(
                "error",
                degree_id,
                "The degree declaration is missing access_mode.",
                {"declared_keys": sorted(manifest.keys())},
            )
            continue
        if access_mode not in ALLOWED_ACCESS_MODES:
            add_issue(
                "error",
                degree_id,
                "The degree declaration uses an unsupported access_mode.",
                {"access_mode": access_mode, "allowed": sorted(ALLOWED_ACCESS_MODES)},
            )
            continue

        password_hash = str(manifest.get("passwordHash") or "").strip()
        if access_mode == "password" and not password_hash:
            add_issue(
                "error",
                degree_id,
                "Password-gated degrees must declare passwordHash.",
                {"access_mode": access_mode},
            )

    library_manifest = raw_degrees.get("library")
    if isinstance(library_manifest, dict):
        library_access = str(library_manifest.get("access_mode") or "").strip()
        if library_access and library_access != "shared":
            add_issue(
                "error",
                "library",
                "library must remain the shared lane in the adopted runtime contract.",
                {"access_mode": library_access, "expected": "shared"},
            )

    if level3_declared and level3_present:
        level3_manifest = raw_degrees.get("level3")
        if isinstance(level3_manifest, dict):
            level3_access = str(level3_manifest.get("access_mode") or "").strip()
            if level3_access != "password":
                add_issue(
                    "error",
                    "level3",
                    "Declared level3 must remain password-gated in the adopted access contract.",
                    {"access_mode": level3_access or None, "expected": "password"},
                )

    return {
        "ok": not any(item["severity"] == "error" for item in issues),
        "issues": issues,
        "required_keys_present": required_keys_present,
        "level3_declared": level3_declared,
        "level3_present": level3_present,
    }, findings


def find_focus_targets(datasets: dict[str, dict[str, Any]], work_id: str | None) -> dict[str, Any]:
    library_entries = datasets["library"]["entries"]
    level1_entries = datasets["level1"]["entries"]
    level2_entries = datasets["level2"]["entries"]
    level3_entries = datasets.get("level3", {}).get("entries", [])

    library_books = [
        entry for entry in library_entries if entry.get("type") == "book" and entry_matches_work(entry, work_id)
    ]
    library_chapters = [
        entry for entry in library_entries if entry.get("type") == "chapter" and entry_matches_work(entry, work_id)
    ]
    enriched_level1 = [
        entry for entry in level1_entries if entry_matches_work(entry, work_id)
    ]
    enriched_level2 = [
        entry for entry in level2_entries if entry_matches_work(entry, work_id)
    ]
    enriched_level3 = [
        entry for entry in level3_entries if entry_matches_work(entry, work_id)
    ]

    imported_work_ids = sorted(
        {
            str(entry.get("work_id") or "").strip()
            for entry in library_entries
            if str(entry.get("work_id") or "").strip()
        }
    )

    return {
        "imported_work_ids": imported_work_ids,
        "library_book_slug": library_books[0]["slug"] if library_books else None,
        "library_book_title": library_books[0]["title"] if library_books else None,
        "library_chapter_slug": library_chapters[0]["slug"] if library_chapters else None,
        "library_chapter_title": library_chapters[0]["title"] if library_chapters else None,
        "level1_slug": enriched_level1[0]["slug"] if enriched_level1 else None,
        "level1_title": enriched_level1[0]["title"] if enriched_level1 else None,
        "level2_slug": enriched_level2[0]["slug"] if enriched_level2 else None,
        "level2_title": enriched_level2[0]["title"] if enriched_level2 else None,
        "level3_slug": enriched_level3[0]["slug"] if enriched_level3 else None,
        "level3_title": enriched_level3[0]["title"] if enriched_level3 else None,
    }


def collect_findings(
    *,
    raw_duplicates: dict[str, dict[str, int]],
    schema_reports: dict[str, dict[str, Any]],
    reference_report: dict[str, Any],
    marker_dupe_rows: list[dict[str, Any]],
    focus: dict[str, Any],
    work_id: str | None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for degree, duplicates in raw_duplicates.items():
        if duplicates:
            findings.append(
                {
                    "severity": "error",
                    "scope": degree,
                    "message": f"Duplicate slugs found in raw {degree}.json.",
                    "details": duplicates,
                }
            )

    for degree, report in schema_reports.items():
        if not report.get("ok"):
            findings.append(
                {
                    "severity": "error",
                    "scope": degree,
                    "message": f"{degree} failed schema validation.",
                    "details": report,
                }
            )

    if not reference_report.get("ok"):
        findings.append(
            {
                "severity": "error",
                "scope": "references",
                "message": "Broken references were found across the live datasets.",
                "details": reference_report,
            }
        )
    for warning in reference_report.get("warnings", []):
        findings.append(
            {
                "severity": "warning",
                "scope": "references",
                "message": warning,
                "details": {},
            }
        )

    if marker_dupe_rows:
        findings.append(
            {
                "severity": "warning",
                "scope": "level-enrichment",
                "message": "Duplicate Step 5 provenance markers were found in full_summary blocks.",
                "details": marker_dupe_rows,
            }
        )

    if work_id and not focus.get("library_book_slug"):
        findings.append(
            {
                "severity": "warning",
                "scope": "focus",
                "message": f"No imported library book was found for work_id={work_id}.",
                "details": focus,
            }
        )

    return findings


def summarize_status(findings: list[dict[str, Any]]) -> str:
    if any(item["severity"] == "error" for item in findings):
        return "fail"
    if findings:
        return "pass-with-warnings"
    return "pass"


def run_data_qa(
    *,
    site_paths: dict[str, Path],
    work_id: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    raw_degrees = read_json(site_paths["data_dir"] / "degrees.json")
    raw_library = read_json(site_paths["library"])
    raw_level1 = read_json(site_paths["level1"])
    raw_level2 = read_json(site_paths["level2"])
    level3_declared = "level3" in raw_degrees
    level3_present = site_paths["level3"].exists()
    raw_level3 = read_json(site_paths["level3"]) if level3_present else None

    datasets = {
        "library": normalize_degree_data(raw_library, "library"),
        "level1": normalize_degree_data(raw_level1, "level1"),
        "level2": normalize_degree_data(raw_level2, "level2"),
    }
    if raw_level3 is not None:
        datasets["level3"] = normalize_degree_data(raw_level3, "level3")

    schema_reports = {
        "library": validate_against_schema(serialize_degree_data(datasets["library"]), site_paths["schema"]),
        "level1": validate_against_schema(serialize_degree_data(datasets["level1"]), site_paths["schema"]),
        "level2": validate_against_schema(serialize_degree_data(datasets["level2"]), site_paths["schema"]),
    }
    if "level3" in datasets:
        schema_reports["level3"] = validate_against_schema(
            serialize_degree_data(datasets["level3"]),
            site_paths["schema"],
        )
    degrees_manifest_report, manifest_findings = validate_degrees_manifest_contract(
        raw_degrees,
        level3_declared=level3_declared,
        level3_present=level3_present,
    )
    reference_report = validate_degree_references(datasets)
    localization_bundle_summary, localization_findings = validate_hebrew_localization_bundle(
        site_root=site_paths["site_root"],
        datasets=datasets,
    )
    overrides_path = site_paths["overrides"]
    override_bundle = normalize_override_bundle(
        load_override_bundle(overrides_path, site_root=site_paths["site_root"]),
        site_root=site_paths["site_root"],
    )
    override_schema_report = validate_override_bundle(override_bundle, site_root=site_paths["site_root"])
    governance_datasets = (
        reconstruct_base_context_from_overrides(datasets, bundle=override_bundle)
        if override_schema_report["ok"]
        else datasets
    )
    override_resolution_report = (
        resolve_override_bundle(override_bundle, datasets=governance_datasets)
        if override_schema_report["ok"]
        else {
            "summary": {"total": len(override_bundle.get("overrides", [])), "active": 0, "stale": 0, "orphaned": 0, "conflict": 0, "field_conflict_count": 0},
            "resolutions": [],
            "field_conflicts": [],
        }
    )
    raw_duplicates = {
        "library": raw_duplicate_slugs(raw_library),
        "level1": raw_duplicate_slugs(raw_level1),
        "level2": raw_duplicate_slugs(raw_level2),
    }
    if raw_level3 is not None:
        raw_duplicates["level3"] = raw_duplicate_slugs(raw_level3)
    marker_dupe_rows = (
        marker_duplicates(datasets["level1"]["entries"], work_id)
        + marker_duplicates(datasets["level2"]["entries"], work_id)
        + (
            marker_duplicates(datasets["level3"]["entries"], work_id)
            if "level3" in datasets
            else []
        )
    )
    focus = find_focus_targets(datasets, work_id)
    findings = collect_findings(
        raw_duplicates=raw_duplicates,
        schema_reports=schema_reports,
        reference_report=reference_report,
        marker_dupe_rows=marker_dupe_rows,
        focus=focus,
        work_id=work_id,
    )
    findings.extend(manifest_findings)
    findings.extend(localization_findings)
    if not override_schema_report["ok"]:
        findings.append(
            {
                "severity": "error",
                "scope": "overrides",
                "message": "content.overrides.json failed override schema validation.",
                "details": override_schema_report,
            }
        )
    for resolution in override_resolution_report.get("resolutions", []):
        status = resolution.get("status")
        if status == "orphaned":
            findings.append(
                {
                    "severity": "warning",
                    "scope": "overrides",
                    "message": "An override no longer resolves after base data normalization.",
                    "details": resolution,
                }
            )
        elif status == "stale":
            findings.append(
                {
                    "severity": "warning",
                    "scope": "overrides",
                    "message": "An override resolved by slug but has locator drift.",
                    "details": resolution,
                }
            )
        elif status == "conflict":
            findings.append(
                {
                    "severity": "warning",
                    "scope": "overrides",
                    "message": "An override has field-level base drift and needs review.",
                    "details": resolution,
                }
            )
    if level3_declared and not level3_present:
        findings.append(
            {
                "severity": "error",
                "scope": "level3",
                "message": "degrees.json declares level3, but level3.json is missing from the selected site root.",
                "details": {
                    "level3_path": str(site_paths["level3"]),
                    "declared_in_degrees_json": True,
                    "file_present": False,
                },
            }
        )
    elif level3_present and not level3_declared:
        findings.append(
            {
                "severity": "warning",
                "scope": "level3",
                "message": "level3.json exists, but degrees.json does not declare level3.",
                "details": {
                    "level3_path": str(site_paths["level3"]),
                    "declared_in_degrees_json": False,
                    "file_present": True,
                },
            }
        )

    summary = {
        "status": summarize_status(findings),
        "site_root": str(site_paths["site_root"]),
        "schema_path": str(site_paths["schema"]),
        "degrees_json_ok": all(key in raw_degrees for key in ("level1", "level2", "library")) and (not level3_declared or level3_present),
        "degrees_manifest_report": degrees_manifest_report,
        "level3_declared": level3_declared,
        "level3_present": level3_present,
        "dataset_stats": {
            degree_id: degree_stats(dataset, work_id)
            for degree_id, dataset in datasets.items()
        },
        "schema_reports": schema_reports,
        "reference_report": reference_report,
        "localization_bundle": localization_bundle_summary,
        "overrides_path": str(overrides_path),
        "override_schema_report": override_schema_report,
        "override_governance_context": "base_snapshot_reconstructed",
        "override_resolution_summary": override_resolution_report["summary"],
        "raw_duplicate_slugs": raw_duplicates,
        "marker_duplicate_count": len(marker_dupe_rows),
        "imported_work_ids": focus["imported_work_ids"],
        "focused_work_id": work_id,
        "focus_targets": focus,
    }
    return summary, findings, focus


@contextlib.contextmanager
def local_site_server(site_root: Path, port: int) -> Iterator[str]:
    handler = partial(SimpleHTTPRequestHandler, directory=str(site_root))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


def derive_search_term(focus: dict[str, Any]) -> str:
    title = str(focus.get("library_book_title") or focus.get("level1_title") or "ritual").strip()
    for token in re.split(r"[^A-Za-z0-9]+", title):
        token = token.strip()
        if len(token) >= 4:
            return token
    return "ritual"


def browser_check(status: str, name: str, detail: str, screenshot: str | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "name": name,
        "detail": detail,
        "screenshot": screenshot,
    }


def check_failed(checks: list[dict[str, Any]]) -> bool:
    return any(item["status"] == "fail" for item in checks)


def summarize_browser_status(checks: list[dict[str, Any]], console_errors: list[Any], page_errors: list[Any], failed_requests: list[Any]) -> str:
    if check_failed(checks):
        return "fail"
    if checks and all(item["status"] == "skip" for item in checks):
        return "skip"
    if console_errors or page_errors or failed_requests or any(item["status"] == "warning" for item in checks):
        return "pass-with-warnings"
    return "pass"


def run_browser_qa(
    *,
    site_root: Path,
    base_url: str | None,
    server_port: int,
    focus: dict[str, Any],
    level1_password: str | None,
    level2_password: str | None,
    level3_password: str | None,
    screenshot_dir: Path,
    quiet: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        summary = {
            "status": "skip",
            "reason": "Playwright for Python is not installed. Install it to enable browser QA.",
            "checks": [browser_check("skip", "browser-runtime", "Playwright is missing.")],
        }
        return summary, [], [], []

    screenshot_dir = ensure_dir(screenshot_dir)
    console_errors: list[dict[str, Any]] = []
    page_errors: list[dict[str, Any]] = []
    failed_requests: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    def attach_page_listeners(page: Any) -> None:
        page.on(
            "console",
            lambda message: console_errors.append(
                {"type": message.type, "text": message.text}
            )
            if message.type == "error"
            else None
        )
        page.on("pageerror", lambda error: page_errors.append({"message": str(error)}))
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                {
                    "url": request.url,
                    "method": request.method,
                    "failure": request.failure or {},
                }
            ),
        )

    def take_screenshot(page: Any, name: str) -> str:
        path = screenshot_dir / f"{len(checks) + 1:02d}_{name}.png"
        page.screenshot(path=str(path), full_page=True)
        return str(path)

    def run_flow(index_url: str) -> None:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1024})
            attach_page_listeners(page)

            log("[browser] opening site root", quiet=quiet)
            page.goto(f"{index_url}/index.html", wait_until="domcontentloaded", timeout=90000)
            page.wait_for_selector("#loginOverlay", timeout=90000)
            checks.append(browser_check("pass", "load-home", "The site loaded and login overlay is visible.", take_screenshot(page, "load-home")))

            if level1_password:
                try:
                    log("[browser] unlocking level1", quiet=quiet)
                    page.locator("#password").fill(level1_password)
                    page.locator("#loginBtn").click()
                    page.wait_for_selector("#loginOverlay", state="hidden", timeout=90000)
                    page.wait_for_selector("#degreeTabs .degree-btn", timeout=90000)
                    checks.append(browser_check("pass", "unlock-level1", "level1 unlocked successfully.", take_screenshot(page, "unlock-level1")))
                except Exception as exc:
                    checks.append(browser_check("fail", "unlock-level1", f"Failed to unlock level1: {exc}", take_screenshot(page, "unlock-level1-fail")))
                    browser.close()
                    return
            else:
                checks.append(browser_check("skip", "unlock-level1", "FM_LEVEL1_PASSWORD is not set."))
                browser.close()
                return

            try:
                search_term = derive_search_term(focus)
                log("[browser] switching to library and searching", quiet=quiet)
                page.locator('button[data-degree="library"]').click()
                page.wait_for_timeout(1200)
                page.locator("#searchInput").fill(search_term)
                page.wait_for_timeout(600)
                checks.append(browser_check("pass", "library-search", f"Search executed with term {search_term!r}.", take_screenshot(page, "library-search")))
            except Exception as exc:
                checks.append(browser_check("warning", "library-search", f"Library search did not complete cleanly: {exc}", take_screenshot(page, "library-search-warning")))

            book_slug = focus.get("library_book_slug")
            if book_slug:
                try:
                    page.goto(f"{index_url}/index.html#library/{quote(book_slug)}", wait_until="domcontentloaded", timeout=90000)
                    page.wait_for_selector("#detailTitle", timeout=90000)
                    detail_title = page.locator("#detailTitle").inner_text(timeout=90000).strip()
                    checks.append(browser_check("pass", "open-book-detail", f"Opened imported book detail: {detail_title}.", take_screenshot(page, "book-detail")))
                except Exception as exc:
                    checks.append(browser_check("fail", "open-book-detail", f"Failed to open imported book detail: {exc}", take_screenshot(page, "book-detail-fail")))

            chapter_slug = focus.get("library_chapter_slug")
            if chapter_slug:
                try:
                    page.goto(f"{index_url}/index.html#library/{quote(chapter_slug)}", wait_until="domcontentloaded", timeout=90000)
                    page.wait_for_selector("#detailBody", timeout=90000)
                    checks.append(browser_check("pass", "open-chapter-detail", "Opened an imported chapter detail view.", take_screenshot(page, "chapter-detail")))
                except Exception as exc:
                    checks.append(browser_check("warning", "open-chapter-detail", f"Failed to open imported chapter detail: {exc}", take_screenshot(page, "chapter-detail-warning")))

            level1_slug = focus.get("level1_slug")
            if level1_slug:
                try:
                    page.goto(f"{index_url}/index.html#level1/{quote(level1_slug)}", wait_until="domcontentloaded", timeout=90000)
                    page.wait_for_selector("#detailBody", timeout=90000)
                    checks.append(browser_check("pass", "open-level1-enrichment", "Opened an enriched level1 entry.", take_screenshot(page, "level1-detail")))
                except Exception as exc:
                    checks.append(browser_check("warning", "open-level1-enrichment", f"Failed to open enriched level1 entry: {exc}", take_screenshot(page, "level1-detail-warning")))

            if level2_password:
                try:
                    log("[browser] unlocking level2", quiet=quiet)
                    page.goto(f"{index_url}/index.html", wait_until="domcontentloaded", timeout=90000)
                    page.wait_for_selector("#loginOverlay", state="hidden", timeout=30000)
                    page.locator('button[data-degree="level2"]').click()
                    page.wait_for_selector("#loginOverlay", state="visible", timeout=30000)
                    page.locator("#password").fill(level2_password)
                    page.locator("#loginBtn").click()
                    page.wait_for_selector("#loginOverlay", state="hidden", timeout=90000)
                    checks.append(browser_check("pass", "unlock-level2", "level2 unlocked successfully.", take_screenshot(page, "unlock-level2")))
                except Exception as exc:
                    checks.append(browser_check("warning", "unlock-level2", f"level2 unlock did not complete cleanly: {exc}", take_screenshot(page, "unlock-level2-warning")))
            else:
                checks.append(browser_check("skip", "unlock-level2", "FM_LEVEL2_PASSWORD is not set."))

            level3_slug = focus.get("level3_slug")
            if level3_slug:
                if level3_password:
                    try:
                        log("[browser] unlocking level3", quiet=quiet)
                        page.goto(f"{index_url}/index.html", wait_until="domcontentloaded", timeout=90000)
                        page.wait_for_selector("#loginOverlay", state="hidden", timeout=30000)
                        page.locator('button[data-degree="level3"]').click()
                        page.wait_for_selector("#loginOverlay", state="visible", timeout=30000)
                        page.locator("#password").fill(level3_password)
                        page.locator("#loginBtn").click()
                        page.wait_for_selector("#loginOverlay", state="hidden", timeout=90000)
                        checks.append(browser_check("pass", "unlock-level3", "level3 unlocked successfully.", take_screenshot(page, "unlock-level3")))
                    except Exception as exc:
                        checks.append(browser_check("warning", "unlock-level3", f"level3 unlock did not complete cleanly: {exc}", take_screenshot(page, "unlock-level3-warning")))
                try:
                    page.goto(f"{index_url}/index.html#level3/{quote(level3_slug)}", wait_until="domcontentloaded", timeout=90000)
                    page.wait_for_selector("#detailBody", timeout=90000)
                    checks.append(browser_check("pass", "open-level3-enrichment", "Opened an enriched level3 entry.", take_screenshot(page, "level3-detail")))
                except Exception as exc:
                    checks.append(browser_check("warning", "open-level3-enrichment", f"Failed to open enriched level3 entry: {exc}", take_screenshot(page, "level3-detail-warning")))

            browser.close()

    if base_url:
        run_flow(base_url.rstrip("/"))
    else:
        with local_site_server(site_root, server_port) as derived_base_url:
            run_flow(derived_base_url.rstrip("/"))
            base_url = derived_base_url

    summary = {
        "status": summarize_browser_status(checks, console_errors, page_errors, failed_requests),
        "base_url": base_url,
        "checks": checks,
        "console_error_count": len(console_errors),
        "page_error_count": len(page_errors),
        "network_failure_count": len(failed_requests),
    }
    return summary, console_errors, page_errors, failed_requests


def render_html_report(
    *,
    site_root: Path,
    work_id: str | None,
    data_summary: dict[str, Any] | None,
    data_findings: list[dict[str, Any]] | None,
    browser_summary: dict[str, Any] | None,
) -> str:
    overall_statuses = [item for item in [data_summary.get("status") if data_summary else None, browser_summary.get("status") if browser_summary else None] if item]
    if "fail" in overall_statuses:
        overall = "fail"
    elif any(item in {"skip", "pass-with-warnings"} for item in overall_statuses):
        overall = "pass-with-warnings"
    else:
        overall = "pass"

    findings_html = ""
    for finding in data_findings or []:
        findings_html += (
            "<article class='finding'>"
            f"<h3>{escape(finding['severity'].upper())} · {escape(finding['scope'])}</h3>"
            f"<p>{escape(finding['message'])}</p>"
            f"<pre>{escape(str(finding['details']))}</pre>"
            "</article>"
        )

    browser_checks_html = ""
    for check in (browser_summary or {}).get("checks", []):
        browser_checks_html += (
            "<tr>"
            f"<td>{escape(check['status'])}</td>"
            f"<td>{escape(check['name'])}</td>"
            f"<td>{escape(check['detail'])}</td>"
            f"<td>{escape(check.get('screenshot') or '')}</td>"
            "</tr>"
        )

    dataset_rows = ""
    if data_summary:
        for degree, stats in data_summary.get("dataset_stats", {}).items():
            dataset_rows += (
                "<tr>"
                f"<td>{escape(degree)}</td>"
                f"<td>{stats['entry_count']}</td>"
                f"<td>{stats['focused_entry_count']}</td>"
                f"<td>{stats['book_count']}</td>"
                f"<td>{stats['chapter_count']}</td>"
                "</tr>"
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Step 7 QA Report</title>
  <style>
    :root {{
      --bg: #09121d;
      --panel: #122133;
      --panel-soft: #182c43;
      --ink: #eaf2fb;
      --muted: #9db1c7;
      --gold: #e2c172;
      --line: rgba(255,255,255,0.12);
      --good: #8fd3b5;
      --warn: #f4c16d;
      --bad: #ef8f8f;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: linear-gradient(180deg, #09121d, #13253a); color: var(--ink); }}
    main {{ width: min(1100px, calc(100% - 32px)); margin: 24px auto 56px; }}
    .hero, .panel {{ background: rgba(10,18,29,0.88); border: 1px solid var(--line); border-radius: 18px; padding: 20px; margin-bottom: 18px; }}
    .eyebrow {{ color: var(--gold); font-size: 0.9rem; }}
    h1, h2, h3 {{ margin: 0 0 10px; }}
    p {{ color: var(--muted); }}
    .status {{ display: inline-block; margin-top: 12px; padding: 8px 12px; border-radius: 999px; background: rgba(255,255,255,0.06); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ color: var(--gold); }}
    pre {{ white-space: pre-wrap; background: rgba(255,255,255,0.04); padding: 12px; border-radius: 12px; border: 1px solid var(--line); overflow-wrap: anywhere; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }}
    .finding {{ padding: 14px; border-radius: 14px; border: 1px solid var(--line); background: rgba(255,255,255,0.03); margin-bottom: 12px; }}
    .status-pass {{ color: var(--good); }}
    .status-pass-with-warnings, .status-skip {{ color: var(--warn); }}
    .status-fail {{ color: var(--bad); }}
    @media (max-width: 840px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="eyebrow">Step 7 · Site QA</div>
      <h1>QA report for {escape(str(site_root))}</h1>
      <p>Focused work: {escape(work_id or "all imported works")}</p>
      <div class="status status-{escape(overall)}">Overall status: {escape(overall)}</div>
    </section>

    <section class="panel">
      <h2>Data QA</h2>
      <p>Status: <strong class="status-{escape((data_summary or {}).get('status', 'skip'))}">{escape((data_summary or {}).get('status', 'skip'))}</strong></p>
      <table>
        <thead>
          <tr><th>Degree</th><th>Entries</th><th>Focused</th><th>Books</th><th>Chapters</th></tr>
        </thead>
        <tbody>
          {dataset_rows or "<tr><td colspan='5'>Data QA was not run.</td></tr>"}
        </tbody>
      </table>
    </section>

    <section class="grid">
      <section class="panel">
        <h2>Data Findings</h2>
        {findings_html or "<p>No data findings were recorded.</p>"}
      </section>
      <section class="panel">
        <h2>Browser QA</h2>
        <p>Status: <strong class="status-{escape((browser_summary or {}).get('status', 'skip'))}">{escape((browser_summary or {}).get('status', 'skip'))}</strong></p>
        <table>
          <thead>
            <tr><th>Status</th><th>Check</th><th>Detail</th><th>Screenshot</th></tr>
          </thead>
          <tbody>
            {browser_checks_html or "<tr><td colspan='4'>Browser QA was not run.</td></tr>"}
          </tbody>
        </table>
      </section>
    </section>
  </main>
</body>
</html>
"""


def overall_exit_code(*, strict: bool, data_summary: dict[str, Any] | None, browser_summary: dict[str, Any] | None) -> int:
    if not strict:
        return 0
    statuses = [item for item in [data_summary.get("status") if data_summary else None, browser_summary.get("status") if browser_summary else None] if item]
    return 1 if "fail" in statuses else 0


def maybe_open_report(path: Path) -> None:
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            webbrowser.open(path.resolve().as_uri())
    except Exception:
        return


def sync_latest_report(report_dir: Path, latest_dir: Path) -> None:
    report_dir = report_dir.resolve()
    latest_dir = latest_dir.resolve()
    if report_dir == latest_dir:
        return
    ensure_dir(latest_dir)
    for source_path in report_dir.rglob("*"):
        relative_path = source_path.relative_to(report_dir)
        target_path = latest_dir / relative_path
        if source_path.is_dir():
            ensure_dir(target_path)
            continue
        ensure_dir(target_path.parent)
        shutil.copy2(source_path, target_path)


def main() -> None:
    args = build_parser().parse_args()
    site_paths = build_site_data_paths(args.site_root.resolve())
    site_report_root = ensure_dir((DEFAULT_REPORT_ROOT / site_paths["site_root"].name).resolve())
    report_dir = ensure_dir(
        args.report_dir.resolve()
        if args.report_dir
        else (site_report_root / timestamp_for_path()).resolve()
    )
    screenshot_dir = ensure_dir(report_dir / "screenshots")
    latest_dir = site_report_root / "latest"
    try:
        data_fingerprints = build_site_data_stat_signatures(site_paths)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc))

    log(f"[start] mode={args.mode} site_root={site_paths['site_root']} report_dir={report_dir}", quiet=args.quiet)

    data_summary: dict[str, Any] | None = None
    data_findings: list[dict[str, Any]] | None = None
    focus: dict[str, Any] = {}
    if args.mode in {"full", "data"}:
        log("[data] running live data QA", quiet=args.quiet)
        data_summary, data_findings, focus = run_data_qa(site_paths=site_paths, work_id=args.work_id)
        write_json(report_dir / "qa_data_summary.json", data_summary)
        write_json(report_dir / "qa_data_findings.json", data_findings)

    browser_summary: dict[str, Any] | None = None
    console_errors: list[dict[str, Any]] = []
    page_errors: list[dict[str, Any]] = []
    failed_requests: list[dict[str, Any]] = []
    if args.mode in {"full", "browser"}:
        if not focus:
            _, _, focus = run_data_qa(site_paths=site_paths, work_id=args.work_id)
        log("[browser] running browser smoke QA", quiet=args.quiet)
        browser_summary, console_errors, page_errors, failed_requests = run_browser_qa(
            site_root=site_paths["site_root"],
            base_url=args.base_url,
            server_port=args.server_port,
            focus=focus,
            level1_password=os.getenv(args.level1_password_env),
            level2_password=os.getenv(args.level2_password_env),
            level3_password=os.getenv(args.level3_password_env),
            screenshot_dir=screenshot_dir,
            quiet=args.quiet,
        )
        write_json(report_dir / "qa_browser_summary.json", browser_summary)
        write_json(report_dir / "console_errors.json", console_errors)
        write_json(report_dir / "page_errors.json", page_errors)
        write_json(report_dir / "network_failures.json", failed_requests)

    html_report = render_html_report(
        site_root=site_paths["site_root"],
        work_id=args.work_id,
        data_summary=data_summary,
        data_findings=data_findings,
        browser_summary=browser_summary,
    )
    write_text(report_dir / "qa_report.html", html_report)

    run_manifest = {
        "created_at": utc_timestamp(),
        "mode": args.mode,
        "site_root": str(site_paths["site_root"]),
        "report_dir": str(report_dir),
        "latest_dir": str(latest_dir),
        "work_id": args.work_id,
        "strict": args.strict,
        "data_status": (data_summary or {}).get("status", "skip"),
        "browser_status": (browser_summary or {}).get("status", "skip"),
        "fingerprints": data_fingerprints,
        "artifacts": {
            "qa_data_summary": str(report_dir / "qa_data_summary.json") if data_summary is not None else None,
            "qa_data_findings": str(report_dir / "qa_data_findings.json") if data_findings is not None else None,
            "qa_browser_summary": str(report_dir / "qa_browser_summary.json") if browser_summary is not None else None,
            "qa_report_html": str(report_dir / "qa_report.html"),
        },
    }
    write_json(report_dir / "qa_run_manifest.json", run_manifest)
    sync_latest_report(report_dir, latest_dir)

    if args.open_report:
        maybe_open_report(report_dir / "qa_report.html")

    log(
        f"[done] data_status={(data_summary or {}).get('status', 'skip')} "
        f"browser_status={(browser_summary or {}).get('status', 'skip')} report={report_dir / 'qa_report.html'}",
        quiet=args.quiet,
    )

    raise SystemExit(
        overall_exit_code(
            strict=args.strict,
            data_summary=data_summary,
            browser_summary=browser_summary,
        )
    )


if __name__ == "__main__":
    main()
