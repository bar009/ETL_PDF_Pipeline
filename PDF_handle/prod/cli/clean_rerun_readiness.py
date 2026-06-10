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


CANONICAL_TEXT_FIELDS = (
    "title",
    "short_summary",
    "full_summary",
    "candidate_lesson",
    "symbolic_meaning",
    "practical_application",
    "full_content",
)
SAFE_SHELL_PATHS = (
    "index.html",
    "css",
    "js",
    "favicon.svg",
    "og-image.svg",
    "README.md",
)
SAFE_GOVERNANCE_PATHS = (
    "data/content.schema.json",
    "data/degrees.json",
    "data/entry.template.json",
)
OPTIONAL_REVIEW_PATHS = (
    "data/content.overrides.json",
    "data/content.localizations.he.json",
)
REGENERATED_DATA_PATHS = (
    "data/library.json",
    "data/level1.json",
    "data/level2.json",
    "data/level3.json",
    "data/library_manifest.json",
    "data/new_content",
    "data/exports",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a read-only readiness report for building a future clean rerun root. "
            "The report separates shell/governance seed composition, topic coverage parity, "
            "and canonical language carry-over risk."
        )
    )
    parser.add_argument("--site-root", type=Path, default=None)
    parser.add_argument("--compare-to-root", type=Path, default=None)
    parser.add_argument(
        "--report-root",
        type=Path,
        default=PDF_HANDLE_ROOT / "runs" / "clean_rerun_readiness",
    )
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when coverage gaps are found.")
    return parser


def has_hebrew(text: str) -> bool:
    return any("\u0590" <= char <= "\u05FF" for char in text)


def load_entries(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    entries = payload.get("entries") if isinstance(payload, dict) else []
    return [item for item in entries if isinstance(item, dict)] if isinstance(entries, list) else []


def summarize_dataset(path: Path, *, dataset: str) -> tuple[dict[str, Any], set[str]]:
    entries = load_entries(path)
    language_counts: dict[str, int] = {}
    slug_set: set[str] = set()
    risky_examples: list[dict[str, Any]] = []
    risky_entry_count = 0
    missing_language_count = 0
    hebrew_title_count = 0
    parallel_entry_count = 0
    canonical_entry_id_count = 0

    for entry in entries:
        slug = str(entry.get("slug") or "").strip()
        if slug:
            slug_set.add(slug)
        language = str(entry.get("language") or "null")
        language_counts[language] = language_counts.get(language, 0) + 1
        if language == "null":
            missing_language_count += 1
        if entry.get("parallel_entry"):
            parallel_entry_count += 1
        if entry.get("canonical_entry_id"):
            canonical_entry_id_count += 1
        title = str(entry.get("title") or "")
        if has_hebrew(title):
            hebrew_title_count += 1

        risky_fields = [field for field in CANONICAL_TEXT_FIELDS if has_hebrew(str(entry.get(field) or ""))]
        if risky_fields:
            risky_entry_count += 1
            if len(risky_examples) < 12:
                risky_examples.append(
                    {
                        "slug": slug or None,
                        "title": title or None,
                        "fields": risky_fields,
                    }
                )

    summary = {
        "dataset": dataset,
        "entry_count": len(entries),
        "slug_count": len(slug_set),
        "language_counts": language_counts,
        "missing_language_count": missing_language_count,
        "parallel_entry_count": parallel_entry_count,
        "canonical_entry_id_count": canonical_entry_id_count,
        "hebrew_title_count": hebrew_title_count,
        "entries_with_hebrew_in_canonical_fields": risky_entry_count,
        "risk_examples": risky_examples,
    }
    return summary, slug_set


def summarize_root(site_root: Path) -> tuple[dict[str, Any], dict[str, set[str]]]:
    site_root = site_root.resolve()
    site_paths = build_site_data_paths(site_root)
    datasets: dict[str, Any] = {}
    slug_sets: dict[str, set[str]] = {}
    for dataset in ("library", "level1", "level2"):
        summary, slug_set = summarize_dataset(site_paths[dataset], dataset=dataset)
        datasets[dataset] = summary
        slug_sets[dataset] = slug_set
    if site_paths["level3"].exists():
        summary, slug_set = summarize_dataset(site_paths["level3"], dataset="level3")
        datasets["level3"] = summary
        slug_sets["level3"] = slug_set

    localization_path = site_root / "data" / "content.localizations.he.json"
    localization_summary = {"present": False, "entry_count": 0}
    if localization_path.exists():
        raw_bundle = read_json(localization_path)
        entries = raw_bundle.get("entries") if isinstance(raw_bundle, dict) else []
        localization_summary = {
            "present": True,
            "entry_count": len(entries) if isinstance(entries, list) else 0,
            "locale": raw_bundle.get("locale") if isinstance(raw_bundle, dict) else None,
        }

    root_summary = {
        "site_root": str(site_root),
        "shell_seed_inventory": build_seed_inventory(site_root, SAFE_SHELL_PATHS),
        "governance_seed_inventory": build_seed_inventory(site_root, SAFE_GOVERNANCE_PATHS),
        "optional_review_inventory": build_seed_inventory(site_root, OPTIONAL_REVIEW_PATHS),
        "regenerated_data_inventory": build_seed_inventory(site_root, REGENERATED_DATA_PATHS),
        "datasets": datasets,
        "hebrew_bundle": localization_summary,
    }
    return root_summary, slug_sets


def build_seed_inventory(site_root: Path, relative_paths: tuple[str, ...]) -> dict[str, Any]:
    present: list[str] = []
    missing: list[str] = []
    for relative in relative_paths:
        if (site_root / relative).exists():
            present.append(relative)
        else:
            missing.append(relative)
    return {
        "present": present,
        "missing": missing,
        "ok": not missing,
    }


def compare_slug_sets(current: dict[str, set[str]], baseline: dict[str, set[str]]) -> dict[str, Any]:
    datasets = sorted(set(current.keys()) | set(baseline.keys()))
    results: dict[str, Any] = {}
    overall_ok = True
    for dataset in datasets:
        current_set = current.get(dataset, set())
        baseline_set = baseline.get(dataset, set())
        missing = sorted(baseline_set - current_set)
        extra = sorted(current_set - baseline_set)
        ok = not missing
        if not ok:
            overall_ok = False
        results[dataset] = {
            "baseline_slug_count": len(baseline_set),
            "current_slug_count": len(current_set),
            "missing_slug_count": len(missing),
            "extra_slug_count": len(extra),
            "missing_slug_examples": missing[:25],
            "extra_slug_examples": extra[:25],
            "ok": ok,
        }
    return {"ok": overall_ok, "datasets": results}


def compute_readiness_status(summary: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    shell_ok = summary["root_summary"]["shell_seed_inventory"]["ok"]
    governance_ok = summary["root_summary"]["governance_seed_inventory"]["ok"]
    coverage_ok = summary.get("coverage_comparison", {}).get("ok", True)
    carry_over_count = sum(
        item["entries_with_hebrew_in_canonical_fields"]
        for item in summary["root_summary"]["datasets"].values()
    )
    if not shell_ok:
        reasons.append("shell seed files are incomplete")
    if not governance_ok:
        reasons.append("governance seed files are incomplete")
    if not coverage_ok:
        reasons.append("coverage comparison shows missing slugs")
    if carry_over_count:
        reasons.append("canonical degree data still contains Hebrew carry-over")

    if not shell_ok or not governance_ok:
        return "not_ready", reasons
    if not coverage_ok:
        return "coverage_gap", reasons
    if carry_over_count:
        return "ready_for_clean_build_but_current_root_is_not_clean", reasons
    return "ready", reasons


def main() -> None:
    args = build_parser().parse_args()
    if getattr(args, "site_root", None) is None:
        args.site_root = get_work_site_root()
    site_root = args.site_root.resolve()
    report_dir = ensure_dir(
        args.report_dir.resolve()
        if args.report_dir
        else (args.report_root.resolve() / utc_timestamp().replace(":", "-"))
    )

    root_summary, slug_sets = summarize_root(site_root)
    report: dict[str, Any] = {
        "created_at": utc_timestamp(),
        "site_root": str(site_root),
        "root_summary": root_summary,
    }

    if args.compare_to_root:
        baseline_root = args.compare_to_root.resolve()
        baseline_summary, baseline_slug_sets = summarize_root(baseline_root)
        report["compare_to_root"] = str(baseline_root)
        report["baseline_summary"] = baseline_summary
        report["coverage_comparison"] = compare_slug_sets(slug_sets, baseline_slug_sets)

    readiness_status, readiness_reasons = compute_readiness_status(report)
    report["readiness_status"] = readiness_status
    report["readiness_reasons"] = readiness_reasons

    write_json(report_dir / "clean_rerun_readiness_report.json", report)
    print(f"[done] clean rerun readiness report written to {report_dir / 'clean_rerun_readiness_report.json'}", flush=True)

    if args.strict and readiness_status in {"not_ready", "coverage_gap"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
