from __future__ import annotations

import argparse
import hashlib
import json
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture a site-data parity snapshot and optionally compare it to a previous snapshot."
    )
    parser.add_argument("--site-root", type=Path, default=get_work_site_root())
    parser.add_argument(
        "--report-root",
        type=Path,
        default=PDF_HANDLE_ROOT / "runs" / "language_integrity_parity",
    )
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--label", default="snapshot")
    parser.add_argument("--compare-to", type=Path, default=None, help="Optional earlier snapshot JSON to compare against.")
    return parser


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_snapshot(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    stats = resolved.stat()
    return {
        "path": str(resolved),
        "size": stats.st_size,
        "sha256": sha256_file(resolved),
    }


def dataset_stats(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    entries = payload.get("entries") if isinstance(payload, dict) else []
    counts: dict[str, int] = {}
    for entry in entries if isinstance(entries, list) else []:
        language = str((entry or {}).get("language") or "null")
        counts[language] = counts.get(language, 0) + 1
    return {
        "entry_count": len(entries) if isinstance(entries, list) else 0,
        "language_counts": counts,
    }


def build_snapshot(site_root: Path, *, label: str) -> dict[str, Any]:
    site_paths = build_site_data_paths(site_root.resolve())
    files = {
        "schema": file_snapshot(site_paths["schema"]),
        "library": file_snapshot(site_paths["library"]),
        "level1": file_snapshot(site_paths["level1"]),
        "level2": file_snapshot(site_paths["level2"]),
    }
    if site_paths["overrides"].exists():
        files["overrides"] = file_snapshot(site_paths["overrides"])
    if site_paths["level3"].exists():
        files["level3"] = file_snapshot(site_paths["level3"])

    stats = {
        "library": dataset_stats(site_paths["library"]),
        "level1": dataset_stats(site_paths["level1"]),
        "level2": dataset_stats(site_paths["level2"]),
    }
    if site_paths["level3"].exists():
        stats["level3"] = dataset_stats(site_paths["level3"])

    return {
        "created_at": utc_timestamp(),
        "label": label,
        "site_root": str(site_root.resolve()),
        "files": files,
        "dataset_stats": stats,
    }


def compare_snapshots(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    file_results: dict[str, dict[str, Any]] = {}
    all_file_keys = sorted(set(current.get("files", {}).keys()) | set(baseline.get("files", {}).keys()))
    for key in all_file_keys:
        current_file = current.get("files", {}).get(key)
        baseline_file = baseline.get("files", {}).get(key)
        file_results[key] = {
            "present_in_current": current_file is not None,
            "present_in_baseline": baseline_file is not None,
            "sha256_match": bool(current_file and baseline_file and current_file.get("sha256") == baseline_file.get("sha256")),
            "size_match": bool(current_file and baseline_file and current_file.get("size") == baseline_file.get("size")),
        }

    dataset_results: dict[str, dict[str, Any]] = {}
    all_dataset_keys = sorted(set(current.get("dataset_stats", {}).keys()) | set(baseline.get("dataset_stats", {}).keys()))
    for key in all_dataset_keys:
        current_stats = current.get("dataset_stats", {}).get(key, {})
        baseline_stats = baseline.get("dataset_stats", {}).get(key, {})
        dataset_results[key] = {
            "entry_count_match": current_stats.get("entry_count") == baseline_stats.get("entry_count"),
            "language_counts_match": current_stats.get("language_counts") == baseline_stats.get("language_counts"),
        }

    file_ok = all(
        item["present_in_current"] == item["present_in_baseline"]
        and (not item["present_in_current"] or item["sha256_match"])
        for item in file_results.values()
    )
    dataset_ok = all(
        item["entry_count_match"] and item["language_counts_match"]
        for item in dataset_results.values()
    )

    return {
        "ok": file_ok and dataset_ok,
        "baseline_snapshot": baseline.get("label"),
        "file_results": file_results,
        "dataset_results": dataset_results,
    }


def main() -> None:
    args = build_parser().parse_args()
    report_dir = ensure_dir(
        args.report_dir.resolve()
        if args.report_dir
        else (args.report_root.resolve() / utc_timestamp().replace(":", "-"))
    )
    snapshot = build_snapshot(args.site_root.resolve(), label=args.label)
    if args.compare_to:
        baseline = json.loads(args.compare_to.resolve().read_text(encoding="utf-8"))
        snapshot["comparison"] = compare_snapshots(snapshot, baseline)
        snapshot["compare_to"] = str(args.compare_to.resolve())

    write_json(report_dir / "site_parity_snapshot.json", snapshot)
    print(f"[done] site parity snapshot written to {report_dir / 'site_parity_snapshot.json'}", flush=True)


if __name__ == "__main__":
    main()
