from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import ensure_dir, read_json, utc_timestamp, write_json
from PDF_handle.prod.core.site_data import build_site_data_paths
from PDF_handle.prod.core.site_roots import get_work_site_root
from PDF_handle.prod.schema.data import infer_language_contract_fields, normalize_degree_data, normalize_nullable_string
from PDF_handle.prod.schema.language_integrity import PROTECTED_TEXT_FIELDS, text_script_flags
from PDF_handle.prod.schema.overrides import (
    apply_override_review_decisions,
    load_override_bundle,
    normalize_override_bundle,
    resolve_override_bundle,
    validate_override_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a preview-only remediation bundle for protected-field cross-language "
            "override violations without mutating the live override file."
        )
    )
    parser.add_argument("--site-root", type=Path, default=None)
    parser.add_argument(
        "--report-root",
        type=Path,
        default=PDF_HANDLE_ROOT / "runs" / "override_language_remediation",
    )
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument(
        "--output-preview-overrides",
        type=Path,
        default=None,
        help="Optional explicit path for the cleaned preview override bundle.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if violating fields remain after preview remediation.")
    return parser


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_datasets(site_root: Path) -> dict[str, dict[str, Any]]:
    site_paths = build_site_data_paths(site_root.resolve())
    datasets = {
        "library": normalize_degree_data(read_json(site_paths["library"]), "library"),
        "level1": normalize_degree_data(read_json(site_paths["level1"]), "level1"),
        "level2": normalize_degree_data(read_json(site_paths["level2"]), "level2"),
    }
    if site_paths["level3"].exists():
        datasets["level3"] = normalize_degree_data(read_json(site_paths["level3"]), "level3")
    return datasets


def collect_override_language_violations(
    *,
    override_bundle: dict[str, Any],
    datasets: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    fields: list[dict[str, Any]] = []

    for record in override_bundle.get("overrides", []):
        identity = record.get("identity") if isinstance(record.get("identity"), dict) else {}
        degree = normalize_nullable_string(identity.get("degree"))
        slug = normalize_nullable_string(identity.get("slug"))
        if not degree or not slug:
            continue
        dataset = datasets.get(degree)
        target_entry = dataset.get("entryBySlug", {}).get(slug) if isinstance(dataset, dict) else None
        if not isinstance(target_entry, dict):
            continue
        target_metadata = infer_language_contract_fields(target_entry)

        for field_name, value in (record.get("fields") or {}).items():
            normalized_field = field_name.split(".", 1)[0]
            if normalized_field not in PROTECTED_TEXT_FIELDS and not field_name.startswith("reading_layers"):
                continue
            flags = text_script_flags(value)
            if not flags["text"]:
                continue
            if not (
                target_metadata["canonical_language"] == "en"
                and target_metadata["display_language"] == "en"
                and flags["has_hebrew"]
            ):
                continue

            key = (degree, slug)
            grouped.setdefault(
                key,
                {
                    "identity": identity,
                    "degree": degree,
                    "slug": slug,
                    "work_id": normalize_nullable_string(identity.get("work_id")),
                    "identity_language": normalize_nullable_string(identity.get("language")),
                    "target_language_contract": {
                        "language": normalize_nullable_string(target_entry.get("language")),
                        "source_language": target_metadata["source_language"],
                        "canonical_language": target_metadata["canonical_language"],
                        "display_language": target_metadata["display_language"],
                        "translation_mode": normalize_nullable_string(target_entry.get("translation_mode")),
                    },
                    "fields": [],
                },
            )
            field_payload = {
                "field": field_name,
                "preview": flags["text"][:160],
                "suggested_action": "accept_base",
                "reason": "Protected-field cross-language override on a canonical English entry.",
            }
            grouped[key]["fields"].append(field_payload)
            fields.append(
                {
                    "identity": identity,
                    "degree": degree,
                    "slug": slug,
                    "work_id": normalize_nullable_string(identity.get("work_id")),
                    "field": field_name,
                    "preview": field_payload["preview"],
                    "suggested_action": "accept_base",
                    "target_language_contract": grouped[key]["target_language_contract"],
                }
            )

    grouped_entries = sorted(grouped.values(), key=lambda item: (item["degree"], item["slug"]))
    return grouped_entries, fields


def build_decisions_payload(grouped_entries: list[dict[str, Any]]) -> dict[str, Any]:
    decisions: list[dict[str, Any]] = []
    for entry in grouped_entries:
        field_actions = {
            item["field"]: {
                "action": item["suggested_action"],
                "note": "Preview-only V1 override language remediation: revert protected cross-language field to base.",
            }
            for item in entry.get("fields", [])
        }
        decisions.append(
            {
                "identity": entry["identity"],
                "status": "language_violation",
                "field_actions": field_actions,
                "note": "Preview-only remediation bundle generated from guarded write-blocking findings.",
            }
        )
    return {"decisions": decisions}


def summarize_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "override_count": len(bundle.get("overrides", [])),
        "field_count": sum(len((record.get("fields") or {}).keys()) for record in bundle.get("overrides", [])),
    }


def main() -> None:
    args = build_parser().parse_args()
    if getattr(args, "site_root", None) is None:
        args.site_root = get_work_site_root()
    site_root = args.site_root.resolve()
    site_paths = build_site_data_paths(site_root)
    report_dir = ensure_dir(
        args.report_dir.resolve()
        if args.report_dir
        else (args.report_root.resolve() / utc_timestamp().replace(":", "-"))
    )
    preview_overrides_path = (
        args.output_preview_overrides.resolve()
        if args.output_preview_overrides
        else (report_dir / "content.overrides.remediated.preview.json")
    )

    datasets = load_datasets(site_root)
    original_bundle = normalize_override_bundle(
        load_override_bundle(site_paths["overrides"], site_root=site_root),
        site_root=site_root,
    )
    original_summary = summarize_bundle(original_bundle)
    original_schema_report = validate_override_bundle(original_bundle, site_root=site_root)

    grouped_entries, field_violations = collect_override_language_violations(
        override_bundle=original_bundle,
        datasets=datasets,
    )
    decisions_payload = build_decisions_payload(grouped_entries)
    remediated_bundle, decision_report = apply_override_review_decisions(
        original_bundle,
        datasets=datasets,
        decisions_payload=decisions_payload,
    )
    remediated_bundle = normalize_override_bundle(remediated_bundle, site_root=site_root)
    remediated_summary = summarize_bundle(remediated_bundle)
    remediated_schema_report = validate_override_bundle(remediated_bundle, site_root=site_root)
    remaining_grouped_entries, remaining_field_violations = collect_override_language_violations(
        override_bundle=remediated_bundle,
        datasets=datasets,
    )
    remediated_resolution_report = (
        resolve_override_bundle(remediated_bundle, datasets=datasets)
        if remediated_schema_report["ok"]
        else {"summary": {}, "resolutions": [], "field_conflicts": []}
    )

    manifest = {
        "created_at": utc_timestamp(),
        "site_root": str(site_root),
        "source_overrides_path": str(site_paths["overrides"]),
        "source_overrides_sha256": sha256_file(site_paths["overrides"]) if site_paths["overrides"].exists() else None,
        "preview_overrides_path": str(preview_overrides_path),
        "violating_entry_count": len(grouped_entries),
        "violating_field_count": len(field_violations),
        "remaining_entry_count": len(remaining_grouped_entries),
        "remaining_field_count": len(remaining_field_violations),
        "decision_count": len(decisions_payload.get("decisions", [])),
    }
    summary = {
        "created_at": utc_timestamp(),
        "status": "preview-clean" if not remaining_field_violations else "preview-incomplete",
        "site_root": str(site_root),
        "source_overrides_path": str(site_paths["overrides"]),
        "source_bundle": {
            **original_summary,
            "schema_report": original_schema_report,
        },
        "violations": {
            "entry_count": len(grouped_entries),
            "field_count": len(field_violations),
        },
        "preview_bundle": {
            **remediated_summary,
            "schema_report": remediated_schema_report,
            "resolution_summary": remediated_resolution_report.get("summary", {}),
        },
        "preview_effect": {
            "removed_override_records": original_summary["override_count"] - remediated_summary["override_count"],
            "removed_override_fields": original_summary["field_count"] - remediated_summary["field_count"],
            "remaining_violating_entries": len(remaining_grouped_entries),
            "remaining_violating_fields": len(remaining_field_violations),
            "decision_applied_count": len(decision_report.get("applied", [])),
            "decision_skipped_count": len(decision_report.get("skipped", [])),
        },
        "risk_notes": [
            "This lane builds a preview cleaned override bundle only; it does not mutate the live override file.",
            "Suggested actions default to accept_base for the narrow V1 protected-field language violations only.",
            "Patch-lane behavior and frontend behavior remain intentionally out of scope.",
        ],
    }

    write_json(report_dir / "override_language_remediation_summary.json", summary)
    write_json(report_dir / "override_language_remediation_entries.json", grouped_entries)
    write_json(report_dir / "override_language_remediation_fields.json", field_violations)
    write_json(report_dir / "override_language_remediation_decisions.json", decisions_payload)
    write_json(report_dir / "override_language_remediation_apply_report.json", decision_report)
    write_json(report_dir / "override_language_remediation_remaining.json", remaining_grouped_entries)
    write_json(report_dir / "override_language_remediation_manifest.json", manifest)
    write_json(preview_overrides_path, remediated_bundle)
    print(json.dumps(summary["preview_effect"], ensure_ascii=False), flush=True)
    print(f"[done] override language remediation artifacts written to {report_dir}", flush=True)

    if args.strict and remaining_field_violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
