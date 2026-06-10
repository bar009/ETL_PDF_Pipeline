from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"

for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core import (  # noqa: E402
    DEFAULT_CONSOLIDATED_DIR,
    DEFAULT_PDF_DIR,
    DEFAULT_PIPELINE_RUNS_ROOT,
    DEFAULT_QA_REPORTS_ROOT,
    DEFAULT_STAGED_RUNS_ROOT,
    PDF_HANDLE_ROOT as PROD_PDF_HANDLE_ROOT,
    REPO_ROOT as PROD_REPO_ROOT,
    ensure_dir,
    get_live_site_root,
    get_work_site_root,
    log,
    read_json,
    resolve_report_dir,
    run_subprocess,
    stable_site_label,
    utc_timestamp,
    write_json,
    write_run_definition,
    write_run_manifest,
    write_text,
)
from PDF_handle.prod.external import (  # noqa: E402
    run_finalize_live_release,
    run_post_pdf_planning_bundle,
    run_publish_work_snapshot,
    run_work_vs_live_smoke,
)

RUN_PREPROCESS_SCRIPT = PDF_HANDLE_ROOT / "prod" / "cli" / "preprocess.py"
RUN_POSTMERGE_SCRIPT = PDF_HANDLE_ROOT / "prod" / "cli" / "postmerge.py"

DEFAULT_ROUTING_CONFIG = PDF_HANDLE_ROOT / "work_routing.json"
DEFAULT_NOTEBOOKLM_INTAKE = PROD_REPO_ROOT / "experiments" / "notebooklm_validation" / "discovery_mindmap_intake.json"
DEFAULT_FUTURE_ENTRY_ROOT = PDF_HANDLE_ROOT / "preservation" / "future_entries"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execution-grade runner for one source work from PDF intake through work/live/publish gates."
    )
    parser.add_argument("--run-definition", type=Path, default=None, help="Optional JSON run definition file.")
    parser.add_argument("--source-book-name", default="", help="PDF stem and consolidated-book stem.")
    parser.add_argument("--work-id", default="", help="Optional explicit work_id override. Must match routing if provided.")
    parser.add_argument("--staging-dir", default="", help="Optional explicit staging_dir override. Must match routing if provided.")
    parser.add_argument("--routing-config", type=Path, default=DEFAULT_ROUTING_CONFIG)
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--consolidated-dir", type=Path, default=DEFAULT_CONSOLIDATED_DIR)
    parser.add_argument("--staged-runs-root", type=Path, default=DEFAULT_STAGED_RUNS_ROOT)
    parser.add_argument("--pipeline-runs-root", type=Path, default=DEFAULT_PIPELINE_RUNS_ROOT)
    parser.add_argument("--qa-reports-root", type=Path, default=DEFAULT_QA_REPORTS_ROOT)
    parser.add_argument("--report-dir", type=Path, default=None, help="Optional explicit run report directory.")
    parser.add_argument("--work-site-root", type=Path, default=get_work_site_root())
    parser.add_argument("--live-site-root", type=Path, default=get_live_site_root())
    parser.add_argument("--provider-01-04", choices=["gemini", "dry-run"], default="gemini")
    parser.add_argument("--provider-05-07", choices=["gemini", "heuristic"], default="heuristic")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--api-key-env", default="GEMINI_API_KEY")
    parser.add_argument("--skip-phase1", action="store_true", help="Reuse existing Step 4 artifacts instead of rerunning Steps 1-4.")
    parser.add_argument("--allow-dry-run-preprocess", action="store_true", help="Allow Phase 1 with provider=dry-run.")
    parser.add_argument("--promote-live", action="store_true", help="After work-root success, also run the same work into the live root.")
    parser.add_argument(
        "--review-approved",
        action="store_true",
        help="Explicitly acknowledge the Phase 3 review gate before continuing the same invocation into live promotion.",
    )
    parser.add_argument("--publish-work-snapshot", action="store_true", help="After live success, create an M6 published work snapshot.")
    parser.add_argument("--finalize-live-release", action="store_true", help="After live success, create an M11 finalized release snapshot.")
    parser.add_argument("--run-post-pdf-enrichment", action="store_true", help="After live success, run the M9 post-PDF planning bundle.")
    parser.add_argument("--notebooklm-intake", type=Path, default=DEFAULT_NOTEBOOKLM_INTAKE)
    parser.add_argument("--future-entry-root", type=Path, default=DEFAULT_FUTURE_ENTRY_ROOT)
    parser.add_argument("--include-companions", action="store_true")
    parser.add_argument("--force-step1", action="store_true")
    parser.add_argument("--force-step2", action="store_true")
    parser.add_argument("--force-step3", action="store_true")
    parser.add_argument("--force-step4", action="store_true")
    parser.add_argument("--force-step5", action="store_true")
    parser.add_argument("--force-step6", action="store_true")
    parser.add_argument("--force-step7", action="store_true")
    parser.add_argument(
        "--skip-exploration-review",
        action="store_true",
        help="Skip the default exploration review sidecar during postmerge phases.",
    )
    parser.add_argument(
        "--exploration-external-review-json",
        type=Path,
        default=None,
        help="Optional external semantic review JSON to pass into the automatic exploration review sidecar.",
    )
    parser.add_argument("--quiet", action="store_true")
    return parser


def load_run_definition_defaults(argv: list[str]) -> tuple[dict[str, Any], Path | None, dict[str, Any] | None]:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--run-definition", type=Path, default=None)
    pre_args, _ = pre_parser.parse_known_args(argv)
    if pre_args.run_definition is None:
        return {}, None, None

    run_definition_path = pre_args.run_definition.resolve()
    payload = read_json(run_definition_path)
    force_steps = payload.get("force_steps") or {}
    defaults = {
        "source_book_name": str(payload.get("source_book_name") or ""),
        "work_id": str(payload.get("work_id") or ""),
        "staging_dir": str(payload.get("staging_dir") or ""),
        "routing_config": Path(payload["routing_config"]).resolve() if payload.get("routing_config") else None,
        "pdf_dir": Path(payload["pdf_dir"]).resolve() if payload.get("pdf_dir") else None,
        "consolidated_dir": Path(payload["consolidated_dir"]).resolve() if payload.get("consolidated_dir") else None,
        "staged_runs_root": Path(payload["staged_runs_root"]).resolve() if payload.get("staged_runs_root") else None,
        "pipeline_runs_root": Path(payload["pipeline_runs_root"]).resolve() if payload.get("pipeline_runs_root") else None,
        "qa_reports_root": Path(payload["qa_reports_root"]).resolve() if payload.get("qa_reports_root") else None,
        "report_dir": Path(payload["report_dir"]).resolve() if payload.get("report_dir") else None,
        "work_site_root": Path(payload["work_site_root"]).resolve() if payload.get("work_site_root") else None,
        "live_site_root": Path(payload["live_site_root"]).resolve() if payload.get("live_site_root") else None,
        "provider_01_04": payload.get("provider_01_04"),
        "provider_05_07": payload.get("provider_05_07"),
        "model": payload.get("model"),
        "api_key_env": payload.get("api_key_env"),
        "skip_phase1": bool(payload.get("skip_phase1", False)),
        "allow_dry_run_preprocess": bool(payload.get("allow_dry_run_preprocess", False)),
        "promote_live": bool(payload.get("promote_live", False)),
        "review_approved": bool(payload.get("review_approved", False)),
        "publish_work_snapshot": bool(payload.get("publish_work_snapshot", False)),
        "finalize_live_release": bool(payload.get("finalize_live_release", False)),
        "run_post_pdf_enrichment": bool(payload.get("run_post_pdf_enrichment", False)),
        "notebooklm_intake": Path(payload["notebooklm_intake"]).resolve() if payload.get("notebooklm_intake") else None,
        "future_entry_root": Path(payload["future_entry_root"]).resolve() if payload.get("future_entry_root") else None,
        "include_companions": bool(payload.get("include_companions", False)),
        "force_step1": bool(force_steps.get("step1", payload.get("force_step1", False))),
        "force_step2": bool(force_steps.get("step2", payload.get("force_step2", False))),
        "force_step3": bool(force_steps.get("step3", payload.get("force_step3", False))),
        "force_step4": bool(force_steps.get("step4", payload.get("force_step4", False))),
        "force_step5": bool(force_steps.get("step5", payload.get("force_step5", False))),
        "force_step6": bool(force_steps.get("step6", payload.get("force_step6", False))),
        "force_step7": bool(force_steps.get("step7", payload.get("force_step7", False))),
        "skip_exploration_review": bool(payload.get("skip_exploration_review", False)),
        "exploration_external_review_json": Path(payload["exploration_external_review_json"]).resolve() if payload.get("exploration_external_review_json") else None,
        "quiet": bool(payload.get("quiet", False)),
    }
    cleaned_defaults = {key: value for key, value in defaults.items() if value is not None}
    return cleaned_defaults, run_definition_path, payload


def build_resolved_run_definition(
    args: argparse.Namespace,
    *,
    report_dir: Path,
    run_definition_path: Path | None,
    input_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "tool": "run_new_material_e2e",
        "created_at": utc_timestamp(),
        "input_run_definition_path": str(run_definition_path) if run_definition_path else None,
        "source_book_name": args.source_book_name.strip(),
        "work_id": args.work_id.strip() or None,
        "staging_dir": args.staging_dir.strip() or None,
        "routing_config": str(args.routing_config.resolve()),
        "pdf_dir": str(args.pdf_dir.resolve()),
        "consolidated_dir": str(args.consolidated_dir.resolve()),
        "staged_runs_root": str(args.staged_runs_root.resolve()),
        "pipeline_runs_root": str(args.pipeline_runs_root.resolve()),
        "qa_reports_root": str(args.qa_reports_root.resolve()),
        "report_dir": str(report_dir.resolve()),
        "work_site_root": str(args.work_site_root.resolve()),
        "live_site_root": str(args.live_site_root.resolve()),
        "provider_01_04": args.provider_01_04,
        "provider_05_07": args.provider_05_07,
        "model": args.model,
        "api_key_env": args.api_key_env,
        "skip_phase1": args.skip_phase1,
        "allow_dry_run_preprocess": args.allow_dry_run_preprocess,
        "promote_live": args.promote_live,
        "review_approved": args.review_approved,
        "publish_work_snapshot": args.publish_work_snapshot,
        "finalize_live_release": args.finalize_live_release,
        "run_post_pdf_enrichment": args.run_post_pdf_enrichment,
        "notebooklm_intake": str(args.notebooklm_intake.resolve()),
        "future_entry_root": str(args.future_entry_root.resolve()),
        "include_companions": args.include_companions,
        "force_steps": {
            "step1": args.force_step1,
            "step2": args.force_step2,
            "step3": args.force_step3,
            "step4": args.force_step4,
            "step5": args.force_step5,
            "step6": args.force_step6,
            "step7": args.force_step7,
        },
        "skip_exploration_review": args.skip_exploration_review,
        "exploration_external_review_json": str(args.exploration_external_review_json.resolve()) if args.exploration_external_review_json else None,
        "quiet": args.quiet,
        "notes": (input_payload or {}).get("notes"),
        "reason": (input_payload or {}).get("reason"),
        "parent_run_id": (input_payload or {}).get("parent_run_id"),
        "mode": (input_payload or {}).get("mode"),
    }


def read_json_if_exists(path: Path) -> Any | None:
    return read_json(path) if path.exists() else None


def normalize_pathish(value: Any) -> Path | None:
    if not value:
        return None
    return Path(str(value)).resolve()


def same_path(left: Path | str, right: Path | str) -> bool:
    return Path(left).resolve() == Path(right).resolve()


def load_routing_entry(routing_config_path: Path, source_book_name: str) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    payload = read_json(routing_config_path.resolve())
    works = list(payload.get("works", []))
    matches = [row for row in works if str(row.get("source_book_name") or "").strip() == source_book_name]
    if not matches:
        raise RuntimeError(
            f"Phase 0 failed: no routing entry exists for source_book_name={source_book_name!r} in {routing_config_path}."
        )
    if len(matches) > 1:
        raise RuntimeError(
            f"Phase 0 failed: source_book_name={source_book_name!r} is not unique in {routing_config_path}."
        )
    return payload, works, matches[0]


def validate_uniqueness(works: list[dict[str, Any]], *, source_book_name: str, work_id: str, staging_dir: str) -> None:
    if sum(1 for row in works if str(row.get("source_book_name") or "").strip() == source_book_name) != 1:
        raise RuntimeError(f"Phase 0 failed: source_book_name={source_book_name!r} is not unique in routing.")
    if sum(1 for row in works if str(row.get("work_id") or "").strip() == work_id) != 1:
        raise RuntimeError(f"Phase 0 failed: work_id={work_id!r} is not unique in routing.")
    if sum(1 for row in works if str(row.get("staging_dir") or "").strip() == staging_dir) != 1:
        raise RuntimeError(f"Phase 0 failed: staging_dir={staging_dir!r} is not unique in routing.")


def consolidated_paths(consolidated_dir: Path, source_book_name: str) -> dict[str, Path]:
    return {
        "markdown": consolidated_dir.resolve() / f"{source_book_name}.md",
        "meta": consolidated_dir.resolve() / f"{source_book_name}_meta.json",
    }


def latest_pipeline_manifest(pipeline_runs_root: Path, site_root: Path) -> Path:
    return pipeline_runs_root.resolve() / stable_site_label(site_root) / "latest.json"


def latest_qa_manifest(qa_reports_root: Path, site_root: Path) -> Path:
    qa_reports_root = qa_reports_root.resolve()
    candidates = (
        qa_reports_root / stable_site_label(site_root) / "latest" / "qa_run_manifest.json",
        qa_reports_root / site_root.resolve().name / "latest" / "qa_run_manifest.json",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def resolve_qa_manifest_path(qa_reports_root: Path, site_root: Path, pipeline_manifest: dict[str, Any]) -> Path:
    latest_candidate = latest_qa_manifest(qa_reports_root, site_root)
    if latest_candidate.exists():
        return latest_candidate

    step7_manifest_path = normalize_pathish(pipeline_manifest.get("step7", {}).get("manifest_path"))
    if step7_manifest_path and step7_manifest_path.exists():
        return step7_manifest_path

    step7_report_dir = normalize_pathish(pipeline_manifest.get("step7", {}).get("report_dir"))
    if step7_report_dir:
        candidate = step7_report_dir / "qa_run_manifest.json"
        if candidate.exists():
            return candidate

    return latest_candidate


def staging_dir_for_route(staged_runs_root: Path, route: dict[str, Any]) -> Path:
    return staged_runs_root.resolve() / str(route["staging_dir"])


def require_phase1_prereqs(
    args: argparse.Namespace,
    *,
    source_book_name: str,
) -> None:
    if args.provider_01_04 == "dry-run" and not args.allow_dry_run_preprocess:
        raise RuntimeError(
            "Phase 1 refused to run with provider=dry-run without --allow-dry-run-preprocess."
        )
    if args.provider_01_04 != "gemini" or os.environ.get(args.api_key_env):
        return

    force_requested = any(
        (
            args.force_step1,
            args.force_step2,
            args.force_step3,
            args.force_step4,
        )
    )
    artifact_paths = consolidated_paths(args.consolidated_dir, source_book_name)
    consolidated_ready = all(path.exists() for path in artifact_paths.values())
    if consolidated_ready and not force_requested:
        return

    if not os.environ.get(args.api_key_env):
        raise RuntimeError(
            f"Phase 1 cannot run: env var {args.api_key_env} is not set for provider=gemini."
        )


def phase0(payload: dict[str, Any], works: list[dict[str, Any]], route: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    source_book_name = args.source_book_name.strip()
    route_work_id = str(route.get("work_id") or "").strip()
    route_staging_dir = str(route.get("staging_dir") or "").strip()
    if not route_work_id or not route_staging_dir:
        raise RuntimeError(
            f"Phase 0 failed: routing entry for {source_book_name!r} is missing work_id or staging_dir."
        )

    explicit_work_id = args.work_id.strip()
    if explicit_work_id and explicit_work_id != route_work_id:
        raise RuntimeError(
            f"Phase 0 failed: explicit --work-id={explicit_work_id!r} does not match routing work_id={route_work_id!r}."
        )
    explicit_staging_dir = args.staging_dir.strip()
    if explicit_staging_dir and explicit_staging_dir != route_staging_dir:
        raise RuntimeError(
            f"Phase 0 failed: explicit --staging-dir={explicit_staging_dir!r} does not match routing staging_dir={route_staging_dir!r}."
        )

    pdf_path = args.pdf_dir.resolve() / f"{source_book_name}.pdf"
    if not pdf_path.exists():
        raise RuntimeError(f"Phase 0 failed: source PDF not found: {pdf_path}")

    validate_uniqueness(
        works,
        source_book_name=source_book_name,
        work_id=route_work_id,
        staging_dir=route_staging_dir,
    )

    return {
        "status": "pass",
        "pdf_path": str(pdf_path),
        "routing_config": str(args.routing_config.resolve()),
        "work_id": route_work_id,
        "staging_dir": route_staging_dir,
        "route": route,
        "routing_entry_count": len(payload.get("works", [])),
    }


def phase1(report_dir: Path, args: argparse.Namespace, *, source_book_name: str) -> dict[str, Any]:
    artifact_paths = consolidated_paths(args.consolidated_dir, source_book_name)
    if args.skip_phase1:
        missing = [name for name, path in artifact_paths.items() if not path.exists()]
        if missing:
            raise RuntimeError(
                f"Phase 1 skip requested but Step 4 artifacts are missing: {', '.join(missing)}"
            )
        return {
            "status": "skipped",
            "reason": "skip-phase1 requested; existing Step 4 artifacts reused",
            "artifacts": {name: str(path) for name, path in artifact_paths.items()},
        }

    require_phase1_prereqs(args, source_book_name=source_book_name)
    phase_dir = ensure_dir(report_dir / "phase1_preprocess")
    extracted_dir = ensure_dir(phase_dir / "extracted_books")
    chunked_dir = ensure_dir(phase_dir / "chunked_books")
    transformed_dir = ensure_dir(phase_dir / "transformed_books")
    command = [
        sys.executable,
        str(RUN_PREPROCESS_SCRIPT),
        "--book",
        source_book_name,
        "--pdf-dir",
        str(args.pdf_dir.resolve()),
        "--extracted-dir",
        str(extracted_dir.resolve()),
        "--chunked-dir",
        str(chunked_dir.resolve()),
        "--transformed-dir",
        str(transformed_dir.resolve()),
        "--consolidated-dir",
        str(args.consolidated_dir.resolve()),
        "--provider",
        args.provider_01_04,
        "--model",
        args.model,
        "--api-key-env",
        args.api_key_env,
        "--report-dir",
        str(phase_dir),
    ]
    if args.force_step1:
        command.append("--force-step1")
    if args.force_step2:
        command.append("--force-step2")
    if args.force_step3:
        command.append("--force-step3")
    if args.force_step4:
        command.append("--force-step4")
    if args.quiet:
        command.append("--quiet")

    run_subprocess(command, quiet=args.quiet)

    manifest_path = phase_dir / "run_manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(f"Phase 1 failed: expected preprocess manifest not found: {manifest_path}")
    manifest = read_json(manifest_path)
    if str(manifest.get("status") or "") != "completed":
        raise RuntimeError(f"Phase 1 failed: preprocess manifest status is {manifest.get('status')!r}.")

    missing = [name for name, path in artifact_paths.items() if not path.exists()]
    if missing:
        raise RuntimeError(
            f"Phase 1 failed: consolidated artifacts missing after preprocess: {', '.join(missing)}"
        )

    return {
        "status": "pass",
        "report_dir": str(phase_dir),
        "manifest_path": str(manifest_path),
        "provider": args.provider_01_04,
        "artifacts": {name: str(path) for name, path in artifact_paths.items()},
    }


def validate_postmerge_outputs(pipeline_manifest_path: Path, qa_manifest_path: Path, *, phase_label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not pipeline_manifest_path.exists():
        raise RuntimeError(f"{phase_label} failed: pipeline manifest not found: {pipeline_manifest_path}")
    if not qa_manifest_path.exists():
        raise RuntimeError(f"{phase_label} failed: QA manifest not found: {qa_manifest_path}")

    pipeline_manifest = read_json(pipeline_manifest_path)
    qa_manifest = read_json(qa_manifest_path)

    if str(pipeline_manifest.get("status") or "") not in {"completed", "completed-with-warnings"}:
        raise RuntimeError(
            f"{phase_label} failed: pipeline status is {pipeline_manifest.get('status')!r}."
        )
    if str(qa_manifest.get("data_status") or "") == "fail":
        raise RuntimeError(f"{phase_label} failed: data QA status is fail.")
    if str(qa_manifest.get("browser_status") or "") == "fail":
        raise RuntimeError(f"{phase_label} failed: browser QA status is fail.")

    return pipeline_manifest, qa_manifest


def phase2_or_4(
    report_dir: Path,
    args: argparse.Namespace,
    *,
    phase_name: str,
    phase_label: str,
    site_root: Path,
    work_id: str,
) -> dict[str, Any]:
    phase_dir = ensure_dir(report_dir / phase_name)
    command = [
        sys.executable,
        str(RUN_POSTMERGE_SCRIPT),
        "--site-root",
        str(site_root.resolve()),
        "--routing-config",
        str(args.routing_config.resolve()),
        "--consolidated-dir",
        str(args.consolidated_dir.resolve()),
        "--staged-runs-root",
        str(args.staged_runs_root.resolve()),
        "--pipeline-runs-root",
        str(args.pipeline_runs_root.resolve()),
        "--qa-reports-root",
        str(args.qa_reports_root.resolve()),
        "--provider",
        args.provider_05_07,
        "--model",
        args.model,
        "--work-id",
        work_id,
    ]
    if args.include_companions:
        command.append("--include-companions")
    if args.force_step5:
        command.append("--force-step5")
    if args.force_step6:
        command.append("--force-step6")
    if args.force_step7:
        command.append("--force-step7")
    if args.skip_exploration_review:
        command.append("--skip-exploration-review")
    if args.exploration_external_review_json:
        command.extend(["--exploration-external-review-json", str(args.exploration_external_review_json.resolve())])
    if args.quiet:
        command.append("--quiet")

    run_subprocess(command, quiet=args.quiet)

    pipeline_manifest_path = latest_pipeline_manifest(args.pipeline_runs_root, site_root)
    if not pipeline_manifest_path.exists():
        raise RuntimeError(f"{phase_label} failed: pipeline manifest not found: {pipeline_manifest_path}")
    pipeline_manifest = read_json(pipeline_manifest_path)
    qa_manifest_path = resolve_qa_manifest_path(args.qa_reports_root, site_root, pipeline_manifest)
    pipeline_manifest, qa_manifest = validate_postmerge_outputs(
        pipeline_manifest_path,
        qa_manifest_path,
        phase_label=phase_label,
    )

    return {
        "status": "pass",
        "site_root": str(site_root.resolve()),
        "pipeline_manifest_path": str(pipeline_manifest_path),
        "qa_manifest_path": str(qa_manifest_path),
        "pipeline_status": pipeline_manifest.get("status"),
        "data_status": qa_manifest.get("data_status"),
        "browser_status": qa_manifest.get("browser_status"),
        "qa_report_dir": qa_manifest.get("report_dir"),
        "provider": args.provider_05_07,
        "phase_dir": str(phase_dir),
    }


def phase3(report_dir: Path, args: argparse.Namespace, *, route: dict[str, Any], phase2_record: dict[str, Any]) -> dict[str, Any]:
    staging_dir = staging_dir_for_route(args.staged_runs_root, route)
    qa_report_dir = Path(str(phase2_record["qa_report_dir"])).resolve() if phase2_record.get("qa_report_dir") else None
    required = {
        "validation_report": staging_dir / "validation_report.json",
        "coverage_report": staging_dir / "coverage_report.json",
        "link_report": staging_dir / "link_report.json",
        "step6_library_preview": staging_dir / "step6_library.preview.json",
        "qa_report_html": (qa_report_dir / "qa_report.html") if qa_report_dir else None,
    }
    missing = [name for name, path in required.items() if path is None or not path.exists()]
    if missing:
        raise RuntimeError(
            f"Phase 3 failed: required work-root review artifacts are missing: {', '.join(missing)}"
        )

    phase3_note = report_dir / "phase3_review_gate.txt"
    write_text(
        phase3_note,
        "Work-root review artifacts exist. Human review is still required before live promotion.\n",
    )
    return {
        "status": "pass",
        "review_required": True,
        "note_path": str(phase3_note),
        "artifacts": {name: str(path) for name, path in required.items() if path is not None},
    }


def _normalize_for_compare(value: Any) -> Any:
    if isinstance(value, list):
        return [_normalize_for_compare(item) for item in value]
    if not isinstance(value, dict):
        return value
    return {key: _normalize_for_compare(value[key]) for key in sorted(value)}


def _diff_top_level_keys(work_entry: dict[str, Any], live_entry: dict[str, Any]) -> list[str]:
    # Reports which top-level keys differ after recursive sort-normalization.
    # Lets operators see *what* changed when Phase 4 parity fails instead of just *that* it changed.
    differing: list[str] = []
    for key in sorted(set(work_entry) | set(live_entry)):
        if _normalize_for_compare(work_entry.get(key)) != _normalize_for_compare(live_entry.get(key)):
            differing.append(key)
    return differing


def _load_site_datasets(site_root: Path) -> dict[str, dict[str, Any]]:
    data_root = site_root.resolve() / "data"
    datasets: dict[str, dict[str, Any]] = {}
    for dataset_name in ("library", "level1", "level2", "level3"):
        dataset_path = data_root / f"{dataset_name}.json"
        if dataset_path.exists():
            datasets[dataset_name] = read_json(dataset_path)
    return datasets


def _collect_selected_targets(step6_merge_report: dict[str, Any]) -> dict[str, list[str]]:
    targets: dict[str, set[str]] = {
        "library": set(str(slug) for slug in step6_merge_report.get("library", {}).get("merged_slugs", []) if slug),
        "level1": set(),
        "level2": set(),
        "level3": set(),
    }
    for dataset_name in ("level1", "level2", "level3"):
        for operation in step6_merge_report.get(dataset_name, {}).get("selected_operations", []) or []:
            if not isinstance(operation, dict):
                continue
            slug = operation.get("slug") or operation.get("entry_slug")
            if slug:
                targets[dataset_name].add(str(slug))
    return {dataset_name: sorted(slugs) for dataset_name, slugs in targets.items() if slugs}


def _compare_selected_targets(
    *,
    work_site_root: Path,
    live_site_root: Path,
    selected_targets: dict[str, list[str]],
) -> dict[str, Any]:
    work_datasets = _load_site_datasets(work_site_root)
    live_datasets = _load_site_datasets(live_site_root)
    datasets: dict[str, Any] = {}
    failures: list[dict[str, Any]] = []

    for dataset_name, slugs in selected_targets.items():
        work_entries = {
            str(entry.get("slug")): entry for entry in work_datasets.get(dataset_name, {}).get("entries", []) if entry.get("slug")
        }
        live_entries = {
            str(entry.get("slug")): entry for entry in live_datasets.get(dataset_name, {}).get("entries", []) if entry.get("slug")
        }
        dataset_issues = {
            "missing_in_work": [],
            "missing_in_live": [],
            "changed_entries": [],
        }

        for slug in slugs:
            work_entry = work_entries.get(slug)
            live_entry = live_entries.get(slug)
            if work_entry is None:
                dataset_issues["missing_in_work"].append(slug)
                failures.append({"dataset": dataset_name, "slug": slug, "issue": "missing_in_work"})
                continue
            if live_entry is None:
                dataset_issues["missing_in_live"].append(slug)
                failures.append({"dataset": dataset_name, "slug": slug, "issue": "missing_in_live"})
                continue
            if _normalize_for_compare(work_entry) != _normalize_for_compare(live_entry):
                differing_keys = _diff_top_level_keys(work_entry, live_entry)
                dataset_issues["changed_entries"].append({"slug": slug, "differing_keys": differing_keys})
                failures.append({"dataset": dataset_name, "slug": slug, "issue": "changed_entry", "differing_keys": differing_keys})

        datasets[dataset_name] = {
            "selected_slugs": slugs,
            **dataset_issues,
        }

    return {
        "pass": len(failures) == 0,
        "datasets": datasets,
        "failures": failures,
    }


def _summarize_selected_parity_failure(selected_parity: dict[str, Any]) -> list[str]:
    failure_lines: list[str] = []
    for dataset_name, dataset_report in selected_parity.get("datasets", {}).items():
        missing_in_work = len(dataset_report.get("missing_in_work", []) or [])
        missing_in_live = len(dataset_report.get("missing_in_live", []) or [])
        changed_entries = len(dataset_report.get("changed_entries", []) or [])
        if missing_in_work or missing_in_live or changed_entries:
            failure_lines.append(
                f"{dataset_name}: missing_in_work={missing_in_work}, "
                f"missing_in_live={missing_in_live}, changed_entries={changed_entries}"
            )
    if not failure_lines and selected_parity.get("failures"):
        failure_lines.append(f"unclassified_failures={len(selected_parity['failures'])}")
    return failure_lines


def phase4_smoke(report_dir: Path, args: argparse.Namespace, *, route: dict[str, Any]) -> dict[str, Any]:
    smoke_result = run_work_vs_live_smoke(
        report_dir=report_dir,
        work_site_root=args.work_site_root,
        live_site_root=args.live_site_root,
        quiet=args.quiet,
    )
    output_path = Path(smoke_result["report_path"])
    smoke_report = smoke_result["report"]
    if smoke_report.get("path_adaptations"):
        raise RuntimeError("Phase 4 failed: work-vs-live smoke still reports path adaptations.")

    staging_dir = staging_dir_for_route(args.staged_runs_root, route)
    step6_merge_report_path = staging_dir / "step6_merge_report.json"
    if not step6_merge_report_path.exists():
        raise RuntimeError(f"Phase 4 failed: Step 6 merge report not found: {step6_merge_report_path}")
    step6_merge_report = read_json(step6_merge_report_path)
    selected_targets = _collect_selected_targets(step6_merge_report)
    selected_parity = _compare_selected_targets(
        work_site_root=args.work_site_root,
        live_site_root=args.live_site_root,
        selected_targets=selected_targets,
    )
    selected_parity_report_path = report_dir / "phase4_selected_work_parity_report.json"
    selected_parity_report = {
        "created_at": utc_timestamp(),
        "phase": "phase4_selected_work_parity",
        "route_staging_dir": str(route["staging_dir"]),
        "step6_merge_report_path": str(step6_merge_report_path),
        "work_site_root": str(args.work_site_root.resolve()),
        "live_site_root": str(args.live_site_root.resolve()),
        "selected_targets": selected_targets,
        "selected_parity": selected_parity,
        "full_root_smoke_status": smoke_report.get("overall_status"),
    }
    write_json(selected_parity_report_path, selected_parity_report)
    if not selected_parity["pass"]:
        summary = "; ".join(_summarize_selected_parity_failure(selected_parity)) or "no detailed dataset summary available"
        raise RuntimeError(
            "Phase 4 failed: selected-work parity between work and live is not pass. "
            f"Selected parity report: {selected_parity_report_path}. {summary}"
        )

    full_root_status = str(smoke_report.get("overall_status") or "")
    if full_root_status != "pass":
        log(
            "[phase4] full-root smoke found pre-existing drift outside the selected work; selected-work parity passed",
            quiet=args.quiet,
        )
    return {
        "status": "pass",
        "report_path": str(output_path),
        "overall_status": "pass",
        "full_root_smoke_status": smoke_report.get("overall_status"),
        "error_count": smoke_report.get("error_count"),
        "critical_failures": smoke_report.get("critical_failures"),
        "selected_work_parity": selected_parity,
        "selected_work_parity_report_path": str(selected_parity_report_path),
        "selected_targets_source": str(step6_merge_report_path),
        "external_lane": {"script": smoke_result["script"], "kind": "js-smoke"},
    }


def phase5_publish(report_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    result = run_publish_work_snapshot(
        report_dir=report_dir,
        work_site_root=args.work_site_root,
        quiet=args.quiet,
    )
    report = result["report"]
    validation = result["validation"]
    if str(report.get("overall_status") or "") != "pass":
        raise RuntimeError("Phase 5.1 failed: M6 publish report overall_status is not pass.")
    if str(validation.get("overall_status") or "") != "pass":
        raise RuntimeError("Phase 5.1 failed: M6 publish validation overall_status is not pass.")
    return {
        "status": "pass",
        "report_path": result["report_path"],
        "validation_path": result["validation_path"],
        "target_site_root": report.get("outputs", {}).get("new_published_site_root"),
        "external_lane": {"script": result["script"], "kind": "js-publish"},
    }


def phase5_finalize(report_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    result = run_finalize_live_release(
        report_dir=report_dir,
        live_site_root=args.live_site_root,
        quiet=args.quiet,
    )
    report = result["report"]
    validation = result["validation"]
    if str(report.get("overall_status") or "") != "pass":
        raise RuntimeError("Phase 5.2 failed: M11 finalize report overall_status is not pass.")
    if str(validation.get("overall_status") or "") != "pass":
        raise RuntimeError("Phase 5.2 failed: M11 finalize validation overall_status is not pass.")
    return {
        "status": "pass",
        "report_path": result["report_path"],
        "validation_path": result["validation_path"],
        "target_site_root": report.get("outputs", {}).get("release_site_root"),
        "external_lane": {"script": result["script"], "kind": "js-finalize"},
    }


def phase6_post_pdf_enrichment(report_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    result = run_post_pdf_planning_bundle(
        report_dir=report_dir,
        work_site_root=args.work_site_root,
        live_site_root=args.live_site_root,
        notebooklm_intake=args.notebooklm_intake,
        future_entry_root=args.future_entry_root,
        quiet=args.quiet,
    )
    report = result["report"]
    overall_status = str(report.get("overall_status") or "")
    if overall_status not in {"pass", "pass-with-warnings"}:
        raise RuntimeError("Phase 6 failed: post-PDF enrichment bundle overall_status is not pass.")
    return {
        "status": "pass" if overall_status == "pass" else "pass-with-warnings",
        "report_path": result["report_path"],
        "summary_path": result["summary_path"],
        "bundle_dir": result["bundle_dir"],
        "overall_status": overall_status,
        "external_lane": {"script": result["script"], "kind": "ps-m9-planning-bundle"},
    }


def main() -> None:
    argv = sys.argv[1:]
    parser = build_parser()
    definition_defaults, run_definition_path, input_run_definition = load_run_definition_defaults(argv)
    if definition_defaults:
        parser.set_defaults(**definition_defaults)
    args = parser.parse_args(argv)
    if not args.source_book_name.strip():
        parser.error("--source-book-name is required unless provided by --run-definition")
    if (args.publish_work_snapshot or args.finalize_live_release) and not args.promote_live:
        raise SystemExit(
            "Publishing/finalizing requires --promote-live because Phase 5 is only valid after live promotion."
        )
    if args.promote_live and not args.review_approved:
        raise SystemExit(
            "Promote-live requires --review-approved because Phase 3 review must be explicitly acknowledged before live promotion."
        )
    report_dir = resolve_report_dir(tool_name="run_new_material_e2e", report_dir=args.report_dir)
    source_book_name = args.source_book_name.strip()
    run_definition = build_resolved_run_definition(
        args,
        report_dir=report_dir,
        run_definition_path=run_definition_path,
        input_payload=input_run_definition,
    )

    manifest: dict[str, Any] = {
        "created_at": utc_timestamp(),
        "tool": "run_new_material_e2e",
        "source_book_name": source_book_name,
        "requested_work_id": args.work_id.strip() or None,
        "requested_staging_dir": args.staging_dir.strip() or None,
        "report_dir": str(report_dir),
        "inputs": {
            "provider_01_04": args.provider_01_04,
            "provider_05_07": args.provider_05_07,
            "model": args.model,
            "explicit_report_dir": str(args.report_dir.resolve()) if args.report_dir else None,
            "skip_phase1": args.skip_phase1,
            "promote_live": args.promote_live,
            "review_approved": args.review_approved,
            "publish_work_snapshot": args.publish_work_snapshot,
            "finalize_live_release": args.finalize_live_release,
            "run_post_pdf_enrichment": args.run_post_pdf_enrichment,
        },
        "phases": {},
        "status": "running",
    }
    write_run_definition(report_dir, run_definition)

    try:
        routing_payload, works, route = load_routing_entry(args.routing_config, source_book_name)
        work_id = str(route["work_id"]).strip()
        manifest["resolved_work_id"] = work_id
        manifest["resolved_staging_dir"] = str(route["staging_dir"]).strip()

        log("[phase0] validating intake and routing", quiet=args.quiet)
        manifest["phases"]["phase0"] = phase0(routing_payload, works, route, args)

        log("[phase1] preparing Step 1-4 state", quiet=args.quiet)
        manifest["phases"]["phase1"] = phase1(report_dir, args, source_book_name=source_book_name)

        log("[phase2] running work-root pipeline", quiet=args.quiet)
        manifest["phases"]["phase2"] = phase2_or_4(
            report_dir,
            args,
            phase_name="phase2_work_root",
            phase_label="Phase 2",
            site_root=args.work_site_root,
            work_id=work_id,
        )

        log("[phase3] verifying review artifacts", quiet=args.quiet)
        manifest["phases"]["phase3"] = phase3(report_dir, args, route=route, phase2_record=manifest["phases"]["phase2"])

        if not args.promote_live:
            manifest["status"] = "awaiting-review"
            manifest["next_action"] = "Review the work-root artifacts, then rerun with --promote-live to continue."
            write_run_manifest(report_dir, "run_manifest.json", manifest)
            log("[done] stopped at work-root review gate", quiet=args.quiet)
            return

        log("[phase4] promoting the same work into the live root", quiet=args.quiet)
        manifest["phases"]["phase4_live"] = phase2_or_4(
            report_dir,
            args,
            phase_name="phase4_live_root",
            phase_label="Phase 4",
            site_root=args.live_site_root,
            work_id=work_id,
        )
        log("[phase4] running work-vs-live smoke", quiet=args.quiet)
        manifest["phases"]["phase4_smoke"] = phase4_smoke(report_dir, args, route=route)

        if args.publish_work_snapshot:
            log("[phase5.1] creating work snapshot publish artifact", quiet=args.quiet)
            manifest["phases"]["phase5_publish"] = phase5_publish(report_dir, args)

        if args.finalize_live_release:
            log("[phase5.2] creating finalized live release artifact", quiet=args.quiet)
            manifest["phases"]["phase5_finalize"] = phase5_finalize(report_dir, args)

        if args.run_post_pdf_enrichment:
            log("[phase6] running post-PDF enrichment bundle", quiet=args.quiet)
            manifest["phases"]["phase6_post_pdf_enrichment"] = phase6_post_pdf_enrichment(report_dir, args)

        manifest["status"] = "completed"
        write_run_manifest(report_dir, "run_manifest.json", manifest)
        log("[done] full requested E2E path completed", quiet=args.quiet)
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["error"] = str(exc)
        write_run_manifest(report_dir, "run_manifest.json", manifest)
        print(f"[error] {exc}", flush=True)
        raise


if __name__ == "__main__":
    main()
