from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.cli.clean_rerun_readiness import (  # noqa: E402
    SAFE_GOVERNANCE_PATHS,
    SAFE_SHELL_PATHS,
    build_seed_inventory,
    compare_slug_sets,
    summarize_root,
)
from PDF_handle.prod.core.io import ensure_dir, read_json, utc_timestamp, write_json  # noqa: E402
from PDF_handle.prod.core.site_roots import get_work_site_root  # noqa: E402
from PDF_handle.prod.schema import normalize_degree_data, serialize_degree_data, validate_against_schema, validate_degree_references  # noqa: E402
from PDF_handle.prod.schema.language_integrity import build_language_integrity_report  # noqa: E402
from PDF_handle.prod.schema.overrides import empty_override_bundle, load_override_bundle, normalize_override_bundle  # noqa: E402


CANONICAL_DATA_PATHS = (
    "data/library.json",
    "data/level1.json",
    "data/level2.json",
    "data/level3.json",
)
CANONICAL_DATASETS = ("library", "level1", "level2", "level3")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight and optionally seed a clean rerun root. The command refuses to create "
            "a new root when the chosen canonical seed still fails the current language and coverage gates, "
            "unless --allow-dirty-seed is passed explicitly."
        )
    )
    parser.add_argument("--shell-root", type=Path, default=get_work_site_root())
    parser.add_argument("--governance-root", type=Path, default=None)
    parser.add_argument("--seed-root", type=Path, required=True)
    parser.add_argument("--compare-to-root", type=Path, default=None)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument(
        "--report-root",
        type=Path,
        default=PDF_HANDLE_ROOT / "runs" / "clean_rerun_seed",
    )
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--allow-dirty-seed", action="store_true")
    parser.add_argument(
        "--seed-mode",
        choices=("full", "categories-only"),
        default="full",
        help=(
            "full copies the seed canonical JSON as-is. categories-only keeps meta/categories "
            "but clears entries so the clean root starts from an English-clean canonical baseline."
        ),
    )
    parser.add_argument("--include-overrides", action="store_true")
    parser.add_argument("--include-hebrew-bundle", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when preflight blocks launch.")
    return parser


def copy_path(src_root: Path, dst_root: Path, relative: str) -> None:
    src = (src_root / relative).resolve()
    dst = (dst_root / relative).resolve()
    if not src.exists():
        return
    ensure_dir(dst.parent)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)


def dataset_path(root: Path, degree: str) -> Path:
    return root / "data" / f"{degree}.json"


def build_projected_canonical_payloads(*, seed_root: Path, seed_mode: str) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for degree in CANONICAL_DATASETS:
        path = dataset_path(seed_root, degree)
        if not path.exists():
            continue
        normalized = normalize_degree_data(read_json(path), degree)
        if seed_mode == "full":
            payloads[degree] = serialize_degree_data(normalized)
            continue
        payloads[degree] = {
            "meta": {
                "degree": normalized["meta"]["degree"],
                "title": normalized["meta"]["title"],
                "updated_at": utc_timestamp(),
            },
            "categories": {category_id: dict(category) for category_id, category in normalized["categories"].items()},
            "entries": [],
        }
    return payloads


def normalize_projected_datasets(payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        degree: normalize_degree_data(payload, degree)
        for degree, payload in payloads.items()
    }


def build_projected_override_bundle(*, seed_root: Path, target_root: Path, include_overrides: bool) -> dict[str, Any]:
    if not include_overrides:
        return empty_override_bundle(target_root)
    return normalize_override_bundle(
        load_override_bundle(seed_root / "data" / "content.overrides.json", site_root=target_root),
        site_root=target_root,
    )


def build_language_summary_for_datasets(
    *,
    datasets: dict[str, dict[str, Any]],
    override_bundle: dict[str, Any],
    site_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return build_language_integrity_report(
        datasets=datasets,
        override_bundle=override_bundle,
        companion_candidates=[],
        site_root=str(site_root),
        staging_dir=None,
    )


def target_root_is_empty(target_root: Path) -> bool:
    if not target_root.exists():
        return True
    return not any(target_root.iterdir())


def main() -> None:
    args = build_parser().parse_args()
    shell_root = args.shell_root.resolve()
    governance_root = args.governance_root.resolve() if args.governance_root else shell_root
    seed_root = args.seed_root.resolve()
    target_root = args.target_root.resolve()
    schema_path = governance_root / "data" / "content.schema.json"
    report_dir = ensure_dir(
        args.report_dir.resolve()
        if args.report_dir
        else (args.report_root.resolve() / utc_timestamp().replace(":", "-"))
    )

    seed_summary, seed_slug_sets = summarize_root(seed_root)
    projected_payloads = build_projected_canonical_payloads(seed_root=seed_root, seed_mode=args.seed_mode)
    projected_datasets = normalize_projected_datasets(projected_payloads)
    projected_override_bundle = build_projected_override_bundle(
        seed_root=seed_root,
        target_root=target_root,
        include_overrides=bool(args.include_overrides),
    )
    projected_language_summary, projected_language_findings = build_language_summary_for_datasets(
        datasets=projected_datasets,
        override_bundle=projected_override_bundle,
        site_root=target_root,
    )
    projected_schema_reports = {
        degree: validate_against_schema(payload, schema_path)
        for degree, payload in projected_payloads.items()
    }
    projected_reference_report = validate_degree_references(projected_datasets)
    readiness_report: dict[str, Any] = {
        "created_at": utc_timestamp(),
        "shell_root": str(shell_root),
        "governance_root": str(governance_root),
        "seed_root": str(seed_root),
        "target_root": str(target_root),
        "seed_mode": args.seed_mode,
        "seed_root_summary": seed_summary,
        "shell_seed_inventory": build_seed_inventory(shell_root, SAFE_SHELL_PATHS),
        "governance_seed_inventory": build_seed_inventory(governance_root, SAFE_GOVERNANCE_PATHS),
        "projected_language_summary": projected_language_summary,
        "projected_schema_reports": projected_schema_reports,
        "projected_reference_report": projected_reference_report,
    }

    if args.compare_to_root:
        compare_root = args.compare_to_root.resolve()
        compare_summary, compare_root_slug_sets = summarize_root(compare_root)
        readiness_report["compare_to_root"] = str(compare_root)
        readiness_report["compare_root_summary"] = compare_summary
        readiness_report["coverage_comparison"] = compare_slug_sets(seed_slug_sets, compare_root_slug_sets)
        readiness_report["coverage_expected_pre_run_gap"] = args.seed_mode == "categories-only"

    seed_language_summary, seed_language_findings = build_language_summary_for_datasets(
        datasets=normalize_projected_datasets(build_projected_canonical_payloads(seed_root=seed_root, seed_mode="full")),
        override_bundle=build_projected_override_bundle(
            seed_root=seed_root,
            target_root=seed_root,
            include_overrides=bool(args.include_overrides),
        ),
        site_root=seed_root,
    )
    readiness_report["source_seed_language_summary"] = seed_language_summary

    launch_blockers: list[str] = []
    if readiness_report["shell_seed_inventory"]["missing"]:
        launch_blockers.append("shell root is missing required shell files")
    if readiness_report["governance_seed_inventory"]["missing"]:
        launch_blockers.append("governance root is missing required governance files")
    if any(not report["ok"] for report in projected_schema_reports.values()):
        launch_blockers.append("projected canonical seed payload fails schema validation")
    if not projected_reference_report["ok"]:
        launch_blockers.append("projected canonical seed payload fails reference validation")
    if projected_language_summary["status"] != "pass":
        launch_blockers.append(f"projected seed language audit is {projected_language_summary['status']}")
    if (
        args.compare_to_root
        and args.seed_mode != "categories-only"
        and not readiness_report.get("coverage_comparison", {}).get("ok", True)
    ):
        launch_blockers.append("coverage comparison shows missing slugs")
    if not target_root_is_empty(target_root):
        launch_blockers.append("target root already exists and is not empty")

    launch_allowed = not launch_blockers or args.allow_dirty_seed
    readiness_report["launch_blockers"] = launch_blockers
    readiness_report["launch_allowed"] = launch_allowed
    readiness_report["allow_dirty_seed"] = bool(args.allow_dirty_seed)

    write_json(report_dir / "clean_rerun_seed_preflight.json", readiness_report)
    write_json(report_dir / "clean_rerun_seed_source_language_findings.json", seed_language_findings)
    write_json(report_dir / "clean_rerun_seed_projected_language_findings.json", projected_language_findings)

    if not launch_allowed:
        print(f"[blocked] clean rerun seed preflight blocked launch; report written to {report_dir}", flush=True)
        if args.strict:
            raise SystemExit(1)
        return

    if not target_root_is_empty(target_root):
        raise SystemExit(f"Refusing to seed non-empty target root: {target_root}")

    ensure_dir(target_root)
    for relative in SAFE_SHELL_PATHS:
        copy_path(shell_root, target_root, relative)
    for relative in SAFE_GOVERNANCE_PATHS:
        copy_path(governance_root, target_root, relative)
    for degree, payload in projected_payloads.items():
        write_json(dataset_path(target_root, degree), payload)

    if args.include_overrides:
        write_json(target_root / "data" / "content.overrides.json", projected_override_bundle)
    else:
        write_json(target_root / "data" / "content.overrides.json", empty_override_bundle(target_root))

    if args.include_hebrew_bundle:
        copy_path(seed_root, target_root, "data/content.localizations.he.json")

    manifest = {
        "created_at": utc_timestamp(),
        "shell_root": str(shell_root),
        "governance_root": str(governance_root),
        "seed_root": str(seed_root),
        "target_root": str(target_root),
        "seed_mode": args.seed_mode,
        "include_overrides": bool(args.include_overrides),
        "include_hebrew_bundle": bool(args.include_hebrew_bundle),
        "allow_dirty_seed": bool(args.allow_dirty_seed),
        "preflight_report": str((report_dir / "clean_rerun_seed_preflight.json").resolve()),
    }
    write_json(report_dir / "clean_rerun_seed_manifest.json", manifest)
    write_json(target_root / "data" / "clean_rerun_seed_manifest.json", manifest)
    print(f"[done] clean rerun root seeded at {target_root}", flush=True)


if __name__ == "__main__":
    main()
