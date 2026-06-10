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
from PDF_handle.prod.schema.data import normalize_degree_data
from PDF_handle.prod.schema.language_integrity import build_language_integrity_report
from PDF_handle.prod.schema.overrides import load_override_bundle, normalize_override_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the V1 dry-run language integrity audit against a selected site root "
            "and optional staged Step 5 artifacts."
        )
    )
    parser.add_argument("--site-root", type=Path, default=get_work_site_root())
    parser.add_argument("--staging-dir", type=Path, default=None, help="Optional staged Step 5 artifact directory.")
    parser.add_argument(
        "--report-root",
        type=Path,
        default=PDF_HANDLE_ROOT / "runs" / "language_integrity",
        help="Root directory for dry-run audit artifacts.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Optional explicit output directory. Defaults under report-root/timestamp.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if the audit finds errors or warnings.")
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


def load_companion_candidates(staging_dir: Path | None) -> list[dict[str, Any]]:
    if staging_dir is None:
        return []
    companion_path = staging_dir.resolve() / "companion_candidates.json"
    if not companion_path.exists():
        return []
    payload = read_json(companion_path)
    return payload if isinstance(payload, list) else []


def main() -> None:
    args = build_parser().parse_args()
    site_root = args.site_root.resolve()
    site_paths = build_site_data_paths(site_root)
    report_dir = ensure_dir(
        args.report_dir.resolve()
        if args.report_dir
        else (args.report_root.resolve() / utc_timestamp().replace(":", "-"))
    )
    staging_dir = args.staging_dir.resolve() if args.staging_dir else None
    datasets = load_datasets(site_root)
    override_bundle = normalize_override_bundle(
        load_override_bundle(site_paths["overrides"], site_root=site_root),
        site_root=site_root,
    )
    companion_candidates = load_companion_candidates(staging_dir)

    summary, findings = build_language_integrity_report(
        datasets=datasets,
        override_bundle=override_bundle,
        companion_candidates=companion_candidates,
        site_root=str(site_root),
        staging_dir=str(staging_dir) if staging_dir else None,
    )
    manifest = {
        "created_at": utc_timestamp(),
        "site_root": str(site_root),
        "staging_dir": str(staging_dir) if staging_dir else None,
        "summary_path": str(report_dir / "language_integrity_summary.json"),
        "entries_path": str(report_dir / "language_integrity_entries.json"),
        "status": summary["status"],
    }

    write_json(report_dir / "language_integrity_summary.json", summary)
    write_json(report_dir / "language_integrity_entries.json", findings)
    write_json(report_dir / "language_integrity_manifest.json", manifest)
    print(f"[done] language integrity audit written to {report_dir}", flush=True)

    if args.strict and summary["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
