"""The single validation gate for runtime/site data (systemic plan WS4).

One command answers "is this site root publishable?":

    python PDF_handle/prod/cli/validate_runtime.py --site-root <path>
    python PDF_handle/prod/cli/validate_runtime.py --site-root <path> --require-complete --strict

Checks, in order:

1. site-root contract — ``data/content.schema.json`` must exist
2. per-degree file (``library``, ``level1``, ``level2``, ``level3`` when present):
   schema validation plus the custom validator (required fields, slug pattern,
   duplicate slugs, legal status/type/scope/visibility/sensitivity)
3. cross-degree references — ``parent_topic``, ``related_topics``,
   ``parallel_entry``, ``knowledge_links``
4. minimal provenance — ``book``/``chapter`` entries must carry ``source_notes``
   or a ``work_id`` (error); published non-structural entries without
   ``source_notes`` are reported as warnings
5. work/library coverage — a degree entry that carries a ``work_id`` requires at
   least one library entry for the same work; a degree lane must never cite a
   work the library lane does not hold

Exit code 0 = publishable. ``--require-complete`` errors when a standard degree
file is missing; ``--strict`` turns warnings into failures.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import read_json, utc_timestamp, write_json
from PDF_handle.prod.core.site_roots import _looks_like_site_root
from PDF_handle.prod.schema.data import (
    VALID_STATUS,
    VALID_TYPES,
    custom_validate_degree_data,
    normalize_degree_data,
    validate_against_schema,
    validate_degree_references,
)

STANDARD_DEGREE_FILES = ("library", "level1", "level2", "level3")
REQUIRED_WHEN_COMPLETE = ("library", "level1", "level2")
PROVENANCE_REQUIRED_TYPES = {"book", "chapter"}
PROVENANCE_WARNING_EXEMPT_TYPES = {"category", "hub"}


def _check_raw_source_integrity(degree_id: str, raw: dict[str, Any]) -> list[str]:
    # Normalization silently repairs duplicate slugs (rename) and illegal
    # status/type values (coerce to defaults). A gate must reject the source
    # file instead of validating the repaired copy.
    errors: list[str] = []
    seen: set[str] = set()
    for index, entry in enumerate(raw.get("entries") or []):
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("slug") or f"entries[{index}]").strip()
        slug = str(entry.get("slug") or "").strip()
        if not slug:
            errors.append(f"{degree_id}:{label} is missing a slug in the source file")
        else:
            if slug in seen:
                errors.append(f"{degree_id}: slug is duplicated in source file: {slug}")
            seen.add(slug)
        if not str(entry.get("title") or "").strip():
            errors.append(f"{degree_id}:{label} is missing a title in the source file")
        status = entry.get("status")
        if status is not None and status not in VALID_STATUS:
            errors.append(
                f"{degree_id}:{label} status must be one of {sorted(VALID_STATUS)}, got {status!r}"
            )
        entry_type = entry.get("type")
        if entry_type is not None and entry_type not in VALID_TYPES:
            errors.append(
                f"{degree_id}:{label} type must be one of {sorted(VALID_TYPES)}, got {entry_type!r}"
            )
    return errors


def _check_provenance(degree_id: str, dataset: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for entry in dataset["entries"]:
        slug = entry["slug"]
        has_notes = bool(entry.get("source_notes"))
        has_work = bool(str(entry.get("work_id") or "").strip())
        if entry.get("type") in PROVENANCE_REQUIRED_TYPES and not (has_notes or has_work):
            errors.append(
                f"{degree_id}:{slug} is a {entry.get('type')} with no source_notes and no work_id"
            )
        elif (
            entry.get("status") == "published"
            and entry.get("type") not in PROVENANCE_WARNING_EXEMPT_TYPES
            and not has_notes
        ):
            warnings.append(f"{degree_id}:{slug} is published without source_notes")
    return errors, warnings


def _check_work_library_coverage(datasets: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    # Sources are structural: a degree entry citing a work must be backed by
    # the library lane. A merge that lands degree content without its library
    # chapters (e.g. Step 6 without --merge-library) must not pass the gate.
    errors: list[str] = []
    warnings: list[str] = []
    library = datasets.get("library")
    library_work_ids: set[str] = set()
    if library is not None:
        for entry in library["entries"]:
            work_id = str(entry.get("work_id") or "").strip()
            if work_id:
                library_work_ids.add(work_id)
    for degree_id, dataset in datasets.items():
        if degree_id == "library":
            continue
        for entry in dataset["entries"]:
            work_id = str(entry.get("work_id") or "").strip()
            if not work_id:
                continue
            if library is None:
                warnings.append(
                    f"{degree_id}:{entry['slug']} carries work_id {work_id!r} "
                    "but library.json is not present to verify coverage"
                )
            elif work_id not in library_work_ids:
                errors.append(
                    f"{degree_id}:{entry['slug']} carries work_id {work_id!r} "
                    "but the library lane has no entry for that work"
                )
    return errors, warnings


def validate_runtime_site_root(
    site_root: Path,
    *,
    require_complete: bool = False,
    strict: bool = False,
) -> dict[str, Any]:
    site_root = Path(site_root)
    report: dict[str, Any] = {
        "tool": "validate_runtime",
        "site_root": str(site_root),
        "started_at": utc_timestamp(),
        "checks": [],
        "errors": [],
        "warnings": [],
    }

    def record(name: str, errors: list[str], warnings: list[str]) -> None:
        report["checks"].append({"name": name, "ok": not errors, "error_count": len(errors)})
        report["errors"].extend(errors)
        report["warnings"].extend(warnings)

    if not _looks_like_site_root(site_root):
        record(
            "site_root_contract",
            [f"{site_root} is not a site root (missing data/content.schema.json)"],
            [],
        )
        return _finish(report, strict=strict)
    record("site_root_contract", [], [])

    data_dir = site_root / "data"
    schema_path = data_dir / "content.schema.json"
    datasets: dict[str, dict[str, Any]] = {}

    for degree_id in STANDARD_DEGREE_FILES:
        degree_path = data_dir / f"{degree_id}.json"
        if not degree_path.exists():
            missing = [f"missing required degree file: {degree_path.name}"] if (
                require_complete and degree_id in REQUIRED_WHEN_COMPLETE
            ) else []
            record(
                f"{degree_id}_present",
                missing,
                [] if missing else [f"{degree_path.name} not present; skipped"],
            )
            continue

        try:
            raw = read_json(degree_path)
            dataset = normalize_degree_data(raw, degree_id)
        except (ValueError, json.JSONDecodeError) as exc:
            record(f"{degree_id}_loads", [f"{degree_path.name}: {exc}"], [])
            continue
        datasets[degree_id] = dataset

        record(f"{degree_id}_source_integrity", _check_raw_source_integrity(degree_id, raw), [])

        schema_result = validate_against_schema(dataset, schema_path)
        record(f"{degree_id}_schema", list(schema_result["errors"]), list(schema_result["warnings"]))

        custom_result = custom_validate_degree_data(dataset)
        record(f"{degree_id}_contract", list(custom_result["errors"]), list(custom_result["warnings"]))

        prov_errors, prov_warnings = _check_provenance(degree_id, dataset)
        record(f"{degree_id}_provenance", prov_errors, prov_warnings)

    if datasets:
        refs = validate_degree_references(datasets)
        record("cross_degree_references", list(refs["errors"]), list(refs["warnings"]))
        coverage_errors, coverage_warnings = _check_work_library_coverage(datasets)
        record("work_library_coverage", coverage_errors, coverage_warnings)
    else:
        record("cross_degree_references", ["no degree files could be loaded"], [])

    return _finish(report, strict=strict)


def _finish(report: dict[str, Any], *, strict: bool) -> dict[str, Any]:
    report["finished_at"] = utc_timestamp()
    report["strict"] = strict
    report["ok"] = not report["errors"] and not (strict and report["warnings"])
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Single validation gate: is this site root publishable?"
    )
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument(
        "--require-complete", action="store_true",
        help="Error when a standard degree file (library/level1/level2) is missing.",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Treat warnings as failures.",
    )
    parser.add_argument(
        "--report", type=Path, default=None,
        help="Optional path for the JSON report.",
    )
    args = parser.parse_args()

    report = validate_runtime_site_root(
        args.site_root,
        require_complete=args.require_complete,
        strict=args.strict,
    )

    if args.report is not None:
        write_json(args.report, report)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
