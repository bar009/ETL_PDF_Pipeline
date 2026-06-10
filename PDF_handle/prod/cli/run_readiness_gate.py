from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.discovery_artifacts import (
    iter_staged_discovery_files,
    normalize_text,
    summarize_discovery_rows,
    validate_discovery_rows,
)
from PDF_handle.prod.core.io import ensure_dir, read_json, utc_timestamp, write_json, write_text
from PDF_handle.prod.core.site_data import build_site_data_paths
from PDF_handle.prod.core.site_roots import get_work_site_root


RUN_SUBDIRS = ("x", "c", "t", "k", "s", "p", "q")
SITE_DATASETS = ("library", "level1", "level2", "level3")
LEVEL3_AUTHORITATIVE_WORK_IDS = (
    "blue-lodge-ritual-reference-guide-2021",
    "commentary-on-the-second-degree",
    "deeper-meaning-of-fc-degree",
    "duncans-ritual-monitor-1866",
    "library-of-freemasonry-volume-2",
)
LEVEL3_AUTHORITATIVE_SITE_ROOT = (REPO_ROOT / "sites" / "work" / "v0.4").resolve()
SERIOUS_LEVEL3_DECISIONS = {"new_canonical_topic", "later_degree_candidate"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a read-only readiness gate before expensive PDF pipeline runs. "
            "It checks paths, site data, staged discovery quality, and operational resume signals."
        )
    )
    parser.add_argument("--site-root", type=Path, default=None)
    parser.add_argument("--run-root", type=Path, default=None)
    parser.add_argument("--pdf-dir", type=Path, default=PDF_HANDLE_ROOT / "PDF_files")
    parser.add_argument("--routing-config", type=Path, default=PDF_HANDLE_ROOT / "work_routing.json")
    parser.add_argument("--consolidated-dir", type=Path, default=None)
    parser.add_argument("--chunked-dir", type=Path, default=None)
    parser.add_argument("--staged-runs-root", type=Path, default=None)
    parser.add_argument("--qa-reports-root", type=Path, default=None)
    parser.add_argument("--work-id", action="append", default=[], help="Optional work_id filter for staged discovery checks.")
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--budget-usd", type=float, default=None, help="Optional budget ceiling for the estimated call plan.")
    parser.add_argument("--cost-per-1000-calls-usd", type=float, default=None)
    parser.add_argument(
        "--enforce-level3-authoritative-charter",
        action="store_true",
        help="Apply the locked WP-1 corpus, publish-target, and level3 review-load gates.",
    )
    parser.add_argument("--max-serious-level3-candidates", type=int, default=50)
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--report-root", type=Path, default=PDF_HANDLE_ROOT / "runs" / "run_readiness")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when readiness status is fail.")
    return parser


def file_count(path: Path, pattern: str = "*") -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return 1
    return sum(1 for item in path.rglob(pattern) if item.is_file())


def path_summary(path: Path, *, expected_kind: str) -> dict[str, Any]:
    resolved = path.resolve()
    exists = resolved.exists()
    return {
        "path": str(resolved),
        "exists": exists,
        "is_file": resolved.is_file() if exists else False,
        "is_dir": resolved.is_dir() if exists else False,
        "expected_kind": expected_kind,
        "ok": exists and ((expected_kind == "file" and resolved.is_file()) or (expected_kind == "dir" and resolved.is_dir())),
    }


def load_entries(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    entries = payload.get("entries") if isinstance(payload, dict) else []
    return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []


def dataset_summary(path: Path, *, dataset: str) -> dict[str, Any]:
    if not path.exists():
        return {"dataset": dataset, "path": str(path.resolve()), "exists": False, "ok": False}
    entries = load_entries(path)
    slugs = [normalize_text(entry.get("slug")) for entry in entries if normalize_text(entry.get("slug"))]
    duplicate_slugs = sorted(slug for slug, count in Counter(slugs).items() if count > 1)
    language_counts = Counter(normalize_text(entry.get("language")) or "missing" for entry in entries)
    return {
        "dataset": dataset,
        "path": str(path.resolve()),
        "exists": True,
        "ok": not duplicate_slugs,
        "entry_count": len(entries),
        "slug_count": len(set(slugs)),
        "duplicate_slug_count": len(duplicate_slugs),
        "duplicate_slug_examples": duplicate_slugs[:20],
        "language_counts": dict(sorted(language_counts.items())),
    }


def summarize_site(site_root: Path) -> dict[str, Any]:
    site_paths = build_site_data_paths(site_root.resolve())
    datasets: dict[str, Any] = {}
    for dataset in SITE_DATASETS:
        path = site_paths[dataset]
        if dataset == "level3" and not path.exists():
            datasets[dataset] = {"dataset": dataset, "path": str(path.resolve()), "exists": False, "ok": True, "entry_count": 0}
        else:
            datasets[dataset] = dataset_summary(path, dataset=dataset)
    return {
        "site_root": str(site_root.resolve()),
        "data_dir": path_summary(site_paths["data_dir"], expected_kind="dir"),
        "schema": path_summary(site_paths["schema"], expected_kind="file"),
        "overrides": path_summary(site_paths["overrides"], expected_kind="file") if site_paths["overrides"].exists() else {"exists": False},
        "datasets": datasets,
    }


def summarize_pdf_dir(pdf_dir: Path) -> dict[str, Any]:
    summary = path_summary(pdf_dir, expected_kind="dir")
    summary["pdf_count"] = len(list(pdf_dir.glob("*.pdf"))) if pdf_dir.exists() else 0
    return summary


def summarize_routing_config(routing_config: Path) -> dict[str, Any]:
    summary = path_summary(routing_config, expected_kind="file")
    if not summary["ok"]:
        return summary
    try:
        payload = read_json(routing_config)
    except Exception as exc:  # noqa: BLE001 - report-only gate should surface parse errors.
        summary["ok"] = False
        summary["error"] = str(exc)
        return summary
    works = payload.get("works") if isinstance(payload, dict) else []
    summary["work_count"] = len(works) if isinstance(works, list) else 0
    summary["work_ids"] = [
        normalize_text(work.get("work_id"))
        for work in works
        if isinstance(work, dict) and normalize_text(work.get("work_id"))
    ] if isinstance(works, list) else []
    return summary


def summarize_run_root(run_root: Path | None) -> dict[str, Any]:
    if run_root is None:
        return {"provided": False}
    root = run_root.resolve()
    subdirs: dict[str, Any] = {}
    for name in RUN_SUBDIRS:
        path = root / name
        subdirs[name] = {
            "path": str(path),
            "exists": path.exists(),
            "file_count": file_count(path) if path.exists() else 0,
        }
    return {
        "provided": True,
        "path": str(root),
        "exists": root.exists(),
        "subdirs": subdirs,
    }


def summarize_provider_call_plan(args: argparse.Namespace) -> dict[str, Any]:
    chunked_dir = args.chunked_dir
    consolidated_dir = args.consolidated_dir
    staged_runs_root = args.staged_runs_root
    if args.run_root:
        run_root = args.run_root.resolve()
        chunked_dir = chunked_dir or run_root / "c"
        consolidated_dir = consolidated_dir or run_root / "k"
        staged_runs_root = staged_runs_root or run_root / "s"

    transform_chunk_calls = file_count(chunked_dir, "*.md") if chunked_dir and chunked_dir.exists() else 0
    consolidated_files = file_count(consolidated_dir, "*.json") if consolidated_dir and consolidated_dir.exists() else 0
    step5_discovery_units = 0
    selected_work_ids = {normalize_text(item) for item in args.work_id if normalize_text(item)}
    if staged_runs_root and staged_runs_root.exists():
        for discovery_path in iter_staged_discovery_files(staged_runs_root, selected_work_ids or None):
            rows = read_json(discovery_path)
            if isinstance(rows, list):
                step5_discovery_units += len([item for item in rows if isinstance(item, dict)])

    estimated_model_calls = transform_chunk_calls + step5_discovery_units
    cost_estimate: dict[str, Any] = {
        "status": "not_configured",
        "estimated_cost_usd": None,
    }
    if args.cost_per_1000_calls_usd is not None:
        estimated_cost_usd = round((estimated_model_calls / 1000) * args.cost_per_1000_calls_usd, 4)
        cost_estimate = {
            "status": "estimated",
            "cost_per_1000_calls_usd": args.cost_per_1000_calls_usd,
            "estimated_cost_usd": estimated_cost_usd,
            "budget_usd": args.budget_usd,
            "within_budget": args.budget_usd is None or estimated_cost_usd <= args.budget_usd,
        }
    elif args.budget_usd is not None:
        cost_estimate = {
            "status": "budget_without_rate",
            "estimated_cost_usd": None,
            "budget_usd": args.budget_usd,
            "within_budget": None,
        }
    return {
        "provider": args.provider,
        "model": args.model,
        "selected_work_ids": sorted(selected_work_ids),
        "transform_chunk_calls": transform_chunk_calls,
        "step5_discovery_units": step5_discovery_units,
        "consolidated_json_files": consolidated_files,
        "estimated_model_calls": estimated_model_calls,
        "cost_estimate": cost_estimate,
    }


def summarize_staged_runs(staged_runs_root: Path | None, selected_work_ids: set[str] | None = None) -> dict[str, Any]:
    if staged_runs_root is None:
        return {"provided": False}
    root = staged_runs_root.resolve()
    if not root.exists():
        return {"provided": True, "path": str(root), "exists": False, "ok": False}

    work_summaries: dict[str, Any] = {}
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    serious_level3_candidate_count = 0
    for discovery_path in iter_staged_discovery_files(root, selected_work_ids):
        staging_dir = discovery_path.parent
        rows = read_json(discovery_path)
        rows = [item for item in rows if isinstance(item, dict)] if isinstance(rows, list) else []
        serious_level3_candidate_count += len(
            [
                row for row in rows
                if normalize_text(row.get("candidate_degree")) == "level3"
                and normalize_text(row.get("decision")) in SERIOUS_LEVEL3_DECISIONS
            ]
        )
        row_blockers, row_warnings = validate_discovery_rows(rows)
        for item in row_blockers:
            item["staging_dir"] = str(staging_dir.resolve())
        for item in row_warnings:
            item["staging_dir"] = str(staging_dir.resolve())
        blockers.extend(row_blockers)
        warnings.extend(row_warnings)

        validation_path = staging_dir / "validation_report.json"
        validation_ok = None
        if validation_path.exists():
            validation_payload = read_json(validation_path)
            validation_ok = bool(validation_payload.get("ok")) if isinstance(validation_payload, dict) else False
        work_summary = summarize_discovery_rows(rows)
        work_summary["validation_report"] = {
            "path": str(validation_path.resolve()),
            "exists": validation_path.exists(),
            "ok": validation_ok,
        }
        work_summaries[staging_dir.name] = work_summary

    return {
        "provided": True,
        "path": str(root),
        "exists": True,
        "ok": not blockers,
        "work_count": len(work_summaries),
        "selected_work_ids": sorted(selected_work_ids or []),
        "serious_level3_candidate_count": serious_level3_candidate_count,
        "work_summaries": work_summaries,
        "quality_blockers": blockers,
        "quality_warnings": warnings,
    }


def summarize_qa_reports(qa_reports_root: Path | None) -> dict[str, Any]:
    if qa_reports_root is None:
        return {"provided": False}
    root = qa_reports_root.resolve()
    if not root.exists():
        return {"provided": True, "path": str(root), "exists": False, "qa_report_count": 0}
    return {
        "provided": True,
        "path": str(root),
        "exists": True,
        "qa_report_count": len(list(root.rglob("qa_report.html"))),
        "qa_manifest_count": len(list(root.rglob("*manifest*.json"))),
    }


def summarize_level3_authoritative_charter(args: argparse.Namespace, report: dict[str, Any]) -> dict[str, Any]:
    if not args.enforce_level3_authoritative_charter:
        return {"enforced": False}

    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    locked_work_ids = set(LEVEL3_AUTHORITATIVE_WORK_IDS)
    routing_work_ids = set(report["routing_config"].get("work_ids") or [])
    selected_work_ids = set(report["provider_call_plan"].get("selected_work_ids") or [])
    selected_or_default_work_ids = selected_work_ids or routing_work_ids
    site_root = Path(report["site"]["site_root"]).resolve()

    if routing_work_ids != locked_work_ids:
        blockers.append(
            {
                "code": "LEVEL3_AUTHORITATIVE_CORPUS_MISMATCH",
                "expected_work_ids": sorted(locked_work_ids),
                "actual_work_ids": sorted(routing_work_ids),
            }
        )
    if selected_or_default_work_ids != locked_work_ids:
        blockers.append(
            {
                "code": "LEVEL3_AUTHORITATIVE_SELECTED_WORK_IDS_MISMATCH",
                "expected_work_ids": sorted(locked_work_ids),
                "actual_work_ids": sorted(selected_or_default_work_ids),
            }
        )
    if site_root != LEVEL3_AUTHORITATIVE_SITE_ROOT:
        blockers.append(
            {
                "code": "LEVEL3_AUTHORITATIVE_SITE_ROOT_MISMATCH",
                "expected_site_root": str(LEVEL3_AUTHORITATIVE_SITE_ROOT),
                "actual_site_root": str(site_root),
            }
        )

    staged = report["staged_runs"]
    if staged.get("provided") and staged.get("exists"):
        serious_count = int(staged.get("serious_level3_candidate_count") or 0)
        if serious_count > args.max_serious_level3_candidates:
            blockers.append(
                {
                    "code": "LEVEL3_AUTHORITATIVE_REVIEW_LOAD_TOO_HIGH",
                    "serious_level3_candidate_count": serious_count,
                    "max_serious_level3_candidates": args.max_serious_level3_candidates,
                }
            )
    else:
        warnings.append({"code": "LEVEL3_AUTHORITATIVE_REVIEW_LOAD_NOT_ESTIMATED"})

    return {
        "enforced": True,
        "status": "fail" if blockers else "pass_with_warnings" if warnings else "pass",
        "locked_work_ids": list(LEVEL3_AUTHORITATIVE_WORK_IDS),
        "locked_site_root": str(LEVEL3_AUTHORITATIVE_SITE_ROOT),
        "max_serious_level3_candidates": args.max_serious_level3_candidates,
        "blockers": blockers,
        "warnings": warnings,
    }


def compute_status(report: dict[str, Any]) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for label in ("data_dir", "schema"):
        if not report["site"]["data_dir" if label == "data_dir" else "schema"].get("ok"):
            blockers.append({"code": "SITE_REQUIRED_PATH_MISSING", "path_label": label})

    for dataset in ("library", "level1", "level2"):
        dataset_report = report["site"]["datasets"][dataset]
        if not dataset_report.get("exists"):
            blockers.append({"code": "SITE_DATASET_MISSING", "dataset": dataset})
        elif not dataset_report.get("ok", True):
            blockers.append({"code": "SITE_DATASET_INVALID", "dataset": dataset, "details": dataset_report})

    if not report["routing_config"].get("ok"):
        blockers.append({"code": "ROUTING_CONFIG_NOT_READY", "details": report["routing_config"]})

    if not report["pdf_dir"].get("ok"):
        blockers.append({"code": "PDF_DIR_NOT_READY", "details": report["pdf_dir"]})
    elif report["pdf_dir"].get("pdf_count", 0) == 0:
        blockers.append({"code": "PDF_DIR_EMPTY", "details": report["pdf_dir"]})

    staged = report["staged_runs"]
    if staged.get("provided") and not staged.get("ok", True):
        blockers.extend(staged.get("quality_blockers", []))
    if staged.get("provided") and staged.get("exists") and staged.get("work_count", 0) == 0:
        warnings.append({"code": "STAGED_RUNS_ROOT_HAS_NO_DISCOVERY_ROWS"})
    if staged.get("provided") and staged.get("exists") and staged.get("selected_work_ids") and staged.get("work_count", 0) == 0:
        blockers.append({"code": "SELECTED_WORK_IDS_NOT_FOUND_IN_STAGED_DISCOVERY", "work_ids": staged.get("selected_work_ids")})
    warnings.extend(staged.get("quality_warnings", []))

    datasets = report["site"]["datasets"]
    library_count = int(datasets.get("library", {}).get("entry_count") or 0)
    degree_counts = [
        int(datasets.get("level1", {}).get("entry_count") or 0),
        int(datasets.get("level2", {}).get("entry_count") or 0),
        int(datasets.get("level3", {}).get("entry_count") or 0),
    ]
    if library_count and sum(degree_counts) == 0:
        warnings.append(
            {
                "code": "SITE_IS_LIBRARY_ONLY",
                "message": "Degree-learning surfaces are empty; discovery candidates still need human review and canonical publish.",
            }
        )

    if not report["qa_reports"].get("provided"):
        warnings.append({"code": "QA_REPORT_ROOT_NOT_PROVIDED"})
    elif report["qa_reports"].get("exists") and report["qa_reports"].get("qa_report_count", 0) == 0:
        warnings.append({"code": "QA_REPORT_ROOT_HAS_NO_QA_REPORTS"})

    cost_estimate = report["provider_call_plan"]["cost_estimate"]
    if cost_estimate.get("status") == "estimated" and cost_estimate.get("within_budget") is False:
        blockers.append({"code": "ESTIMATED_COST_EXCEEDS_BUDGET", "details": cost_estimate})
    elif cost_estimate.get("status") == "budget_without_rate":
        warnings.append({"code": "BUDGET_PROVIDED_WITHOUT_COST_RATE", "details": cost_estimate})

    charter = report.get("level3_authoritative_charter", {})
    if charter.get("enforced"):
        blockers.extend(charter.get("blockers", []))
        warnings.extend(charter.get("warnings", []))

    status = "pass"
    if blockers:
        status = "fail"
    elif warnings:
        status = "pass_with_warnings"

    return {
        "status": status,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": blockers,
        "warnings": warnings,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    if args.run_root:
        run_root = args.run_root.resolve()
        args.consolidated_dir = args.consolidated_dir or run_root / "k"
        args.staged_runs_root = args.staged_runs_root or run_root / "s"
        args.qa_reports_root = args.qa_reports_root or run_root / "q"
        args.chunked_dir = args.chunked_dir or run_root / "c"

    report = {
        "created_at": utc_timestamp(),
        "mode": "read_only",
        "site": summarize_site(args.site_root.resolve()),
        "routing_config": summarize_routing_config(args.routing_config.resolve()),
        "pdf_dir": summarize_pdf_dir(args.pdf_dir.resolve()),
        "run_root": summarize_run_root(args.run_root.resolve() if args.run_root else None),
        "provider_call_plan": summarize_provider_call_plan(args),
        "staged_runs": summarize_staged_runs(
            args.staged_runs_root.resolve() if args.staged_runs_root else None,
            {normalize_text(item) for item in args.work_id if normalize_text(item)} or None,
        ),
        "qa_reports": summarize_qa_reports(args.qa_reports_root.resolve() if args.qa_reports_root else None),
    }
    report["level3_authoritative_charter"] = summarize_level3_authoritative_charter(args, report)
    report["readiness"] = compute_status(report)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    readiness = report["readiness"]
    plan = report["provider_call_plan"]
    lines = [
        "# Run Readiness Gate",
        "",
        f"- Status: `{readiness['status']}`",
        f"- Blockers: `{readiness['blocker_count']}`",
        f"- Warnings: `{readiness['warning_count']}`",
        f"- Estimated model calls: `{plan['estimated_model_calls']}`",
        f"- Transform chunk calls: `{plan['transform_chunk_calls']}`",
        f"- Step 5 discovery units: `{plan['step5_discovery_units']}`",
        "",
    ]
    charter = report.get("level3_authoritative_charter", {})
    if charter.get("enforced"):
        lines.extend(
            [
                "## Level3 Authoritative Charter",
                "",
                f"- Status: `{charter['status']}`",
                f"- Locked site root: `{charter['locked_site_root']}`",
                f"- Serious level3 candidate max: `{charter['max_serious_level3_candidates']}`",
                "",
            ]
        )
    lines.extend(["## Site Data", ""])
    for dataset, summary in report["site"]["datasets"].items():
        lines.append(f"- `{dataset}`: entries `{summary.get('entry_count', 0)}`, exists `{summary.get('exists')}`")
    lines.append("")
    lines.append("## Staged Discovery")
    lines.append("")
    staged = report["staged_runs"]
    if staged.get("provided") and staged.get("exists"):
        for work_name, summary in staged.get("work_summaries", {}).items():
            lines.append(
                f"- `{work_name}`: rows `{summary['row_count']}`, promotable `{summary['promotable_count']}`, "
                f"validation `{summary['validation_report']['ok']}`"
            )
    else:
        lines.append("- No staged discovery root provided/found.")
    lines.append("")
    if readiness["blockers"]:
        lines.append("## Blockers")
        lines.append("")
        for item in readiness["blockers"]:
            lines.append(f"- `{item.get('code')}`")
        lines.append("")
    if readiness["warnings"]:
        lines.append("## Warnings")
        lines.append("")
        warning_counts = Counter(str(item.get("code") or "UNKNOWN_WARNING") for item in readiness["warnings"])
        for code, count in sorted(warning_counts.items()):
            lines.append(f"- `{code}`: {count}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = build_parser().parse_args()
    if getattr(args, "site_root", None) is None:
        args.site_root = get_work_site_root()
    output_dir = ensure_dir(
        args.report_dir.resolve()
        if args.report_dir
        else args.report_root.resolve() / utc_timestamp().replace(":", "-")
    )
    report = build_report(args)
    write_json(output_dir / "run_readiness_report.json", report)
    write_json(output_dir / "run_cost_plan.json", report["provider_call_plan"])
    write_text(output_dir / "run_readiness_summary.md", render_markdown(report))
    print(
        "[done] run readiness gate "
        f"status={report['readiness']['status']} "
        f"blockers={report['readiness']['blocker_count']} "
        f"warnings={report['readiness']['warning_count']} "
        f"report={output_dir / 'run_readiness_report.json'}",
        flush=True,
    )
    if args.strict and report["readiness"]["status"] == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
