from __future__ import annotations

import argparse
import sys
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
from PDF_handle.prod.schema import (
    extract_override_bundle_from_diff,
    normalize_degree_data,
    normalize_override_bundle,
    validate_override_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract a candidate content.overrides.json bundle by diffing a current site root "
            "against a clean base-only comparison root."
        )
    )
    parser.add_argument(
        "--current-site-root",
        type=Path,
        default=get_work_site_root(),
        help="Current curated site root that still contains manual edits.",
    )
    parser.add_argument(
        "--base-site-root",
        type=Path,
        required=True,
        help="Clean base-only comparison site root produced without manual curated edits.",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        default=PDF_HANDLE_ROOT / "runs" / "override_migration",
        help="Artifact root for migration reports.",
    )
    parser.add_argument(
        "--output-overrides",
        type=Path,
        default=None,
        help="Optional explicit path for the candidate override bundle. Defaults inside the run dir.",
    )
    return parser


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


def build_diff_report(current_datasets: dict[str, dict[str, Any]], base_datasets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    unmatched_current: dict[str, list[str]] = {}
    unmatched_base: dict[str, list[str]] = {}
    for degree_id, current_dataset in current_datasets.items():
        base_dataset = base_datasets.get(degree_id)
        if not base_dataset:
            unmatched_current[degree_id] = sorted(current_dataset["entryBySlug"].keys())
            continue
        current_slugs = set(current_dataset["entryBySlug"].keys())
        base_slugs = set(base_dataset["entryBySlug"].keys())
        unmatched_current[degree_id] = sorted(current_slugs - base_slugs)
        unmatched_base[degree_id] = sorted(base_slugs - current_slugs)
    for degree_id, base_dataset in base_datasets.items():
        if degree_id not in current_datasets:
            unmatched_base[degree_id] = sorted(base_dataset["entryBySlug"].keys())
    return {
        "current_only_counts": {degree_id: len(slugs) for degree_id, slugs in unmatched_current.items()},
        "base_only_counts": {degree_id: len(slugs) for degree_id, slugs in unmatched_base.items()},
        "current_only_examples": {degree_id: slugs[:20] for degree_id, slugs in unmatched_current.items() if slugs},
        "base_only_examples": {degree_id: slugs[:20] for degree_id, slugs in unmatched_base.items() if slugs},
    }


def main() -> None:
    args = build_parser().parse_args()
    current_site_root = args.current_site_root.resolve()
    base_site_root = args.base_site_root.resolve()
    run_dir = ensure_dir(args.run_root.resolve() / utc_timestamp().replace(":", "-"))
    output_overrides = args.output_overrides.resolve() if args.output_overrides else (run_dir / "content.overrides.candidate.json")

    current_datasets = load_datasets(current_site_root)
    base_datasets = load_datasets(base_site_root)
    candidate_bundle = extract_override_bundle_from_diff(
        current_datasets=current_datasets,
        base_datasets=base_datasets,
        site_root=current_site_root,
    )
    candidate_bundle = normalize_override_bundle(candidate_bundle, site_root=current_site_root)
    schema_report = validate_override_bundle(candidate_bundle, site_root=current_site_root)
    diff_report = build_diff_report(current_datasets, base_datasets)
    migration_report = {
        "created_at": utc_timestamp(),
        "current_site_root": str(current_site_root),
        "base_site_root": str(base_site_root),
        "output_overrides": str(output_overrides),
        "override_count": len(candidate_bundle.get("overrides", [])),
        "schema_report": schema_report,
        "diff_report": diff_report,
    }

    write_json(output_overrides, candidate_bundle)
    write_json(run_dir / "override_migration_report.json", migration_report)
    print(f"[done] override migration candidate written to {output_overrides}", flush=True)
    print(f"[report] {run_dir / 'override_migration_report.json'}", flush=True)


if __name__ == "__main__":
    main()
