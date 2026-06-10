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

from PDF_handle.prod.core import (  # noqa: E402
    DEFAULT_CONSOLIDATED_DIR,
    DEFAULT_PIPELINE_RUNS_ROOT,
    DEFAULT_QA_REPORTS_ROOT,
    DEFAULT_STAGED_RUNS_ROOT,
    build_site_data_paths,
    build_site_data_stat_signatures,
    ensure_dir,
    log,
    read_json,
    read_json_if_exists,
    run_subprocess,
    stable_site_label,
    utc_timestamp,
    write_json,
    write_run_definition,
    write_text,
)
from PDF_handle.prod.exploration import (  # noqa: E402
    build_clusters,
    create_run_dir,
    normalize_external_reviews,
    reconcile_clusters,
    write_exploration_reports,
)
from PDF_handle.prod.schema import APPEND_MARKER_PREFIX  # noqa: E402


DEFAULT_ROUTING_CONFIG = PDF_HANDLE_ROOT / "work_routing.json"

STEP_05_SCRIPT = PDF_HANDLE_ROOT / "prod" / "steps" / "stage.py"
STEP_06_SCRIPT = PDF_HANDLE_ROOT / "prod" / "steps" / "apply.py"
STEP_07_SCRIPT = PDF_HANDLE_ROOT / "prod" / "steps" / "qa.py"

# Outputs of prod/steps/stage.py (Step 5) that --force-step5 must wipe to give a clean rerun.
# Source of truth for these filenames lives next to the writes in stage.py — when a new file
# is added there, add it here too. clear_step5_generated_state() also globs for leftover
# .<pid>.tmp atomic-write fallout from interrupted writes.
STEP5_STATE_FILES = {
    "base_library.normalized.json",
    "base_level1.normalized.json",
    "base_level2.normalized.json",
    "base_level3.normalized.json",
    "base_validation_report.json",
    "companion_candidates.json",
    "coverage_report.json",
    "discovery_gate_report.json",
    "discovery_rows.json",
    "discovery_summary.json",
    "level1.candidate.json",
    "level1.patch.json",
    "level2.candidate.json",
    "level2.patch.json",
    "level3.candidate.json",
    "level3.patch.json",
    "library.candidate.json",
    "library.patch.json",
    "link_report.json",
    "run_status.json",
    "validation_report.json",
    "work_manifest.generated.json",
}

# Outputs of prod/steps/apply.py (Step 6). Same source-of-truth rule as STEP5_STATE_FILES.
STEP6_STATE_FILES = {
    "rollback_plan.md",
    "step6_backup_report.json",
    "step6_level1.preview.json",
    "step6_level2.preview.json",
    "step6_level3.preview.json",
    "step6_library.preview.json",
    "step6_merge_report.json",
    "step6_override_conflicts.json",
    "step6_override_resolution_report.json",
    "step6_override_review_template.json",
    "step6_overrides.preview.json",
    "step6_review_template.json",
    "step6_validation_report.json",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prod runner for Steps 5-7 with smart skip/resume and explicit site-root targeting."
    )
    parser.add_argument("--site-root", type=Path, required=True, help="Explicit target site root, for example 0.3 or 0.4.")
    parser.add_argument("--routing-config", type=Path, default=DEFAULT_ROUTING_CONFIG)
    parser.add_argument("--staged-runs-root", type=Path, default=DEFAULT_STAGED_RUNS_ROOT)
    parser.add_argument("--consolidated-dir", type=Path, default=DEFAULT_CONSOLIDATED_DIR)
    parser.add_argument("--pipeline-runs-root", type=Path, default=DEFAULT_PIPELINE_RUNS_ROOT)
    parser.add_argument("--qa-reports-root", type=Path, default=DEFAULT_QA_REPORTS_ROOT)
    parser.add_argument("--work-id", action="append", dest="work_ids", help="Optional work_id filter. Can be passed more than once.")
    parser.add_argument("--provider", choices=["gemini", "heuristic"], default="gemini")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--include-companions", action="store_true", help="Also auto-approve companion candidates during Step 6.")
    parser.add_argument("--force-step5", action="store_true")
    parser.add_argument("--force-step6", action="store_true")
    parser.add_argument("--force-step7", action="store_true")
    parser.add_argument(
        "--skip-exploration-review",
        action="store_true",
        help="Skip the additive exploration review lane. By default it runs after Step 5 state exists, writes runs-only artifacts, and never mutates live data.",
    )
    parser.add_argument(
        "--exploration-external-review-json",
        type=Path,
        default=None,
        help="Optional external semantic review JSON to include in the automatic exploration review sidecar.",
    )
    parser.add_argument("--quiet", action="store_true")
    return parser


def same_path(left: Path | str, right: Path | str) -> bool:
    return Path(left).resolve() == Path(right).resolve()


def load_routes(routing_config_path: Path, selected_work_ids: list[str] | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    routing_config = read_json(routing_config_path.resolve())
    works = list(routing_config.get("works", []))
    selected = [item.strip() for item in (selected_work_ids or []) if item and item.strip()]
    if not selected:
        return routing_config, works

    work_by_id = {str(work.get("work_id") or "").strip(): work for work in works}
    missing = [work_id for work_id in selected if work_id not in work_by_id]
    if missing:
        raise SystemExit(f"Unknown work_id value(s): {', '.join(missing)}")
    return routing_config, [work_by_id[work_id] for work_id in selected]


def staging_dir_for_route(route: dict[str, Any], staged_runs_root: Path) -> Path:
    staging_dir_name = str(route.get("staging_dir") or "").strip()
    if not staging_dir_name:
        raise RuntimeError(
            f"Route {route.get('work_id')!r} is missing staging_dir in work_routing.json. "
            "Add an explicit staging_dir so the unified runner can reuse prior state safely."
        )
    return (staged_runs_root.resolve() / staging_dir_name).resolve()


def consolidated_paths_for_route(route: dict[str, Any], consolidated_dir: Path) -> dict[str, Path]:
    book_name = str(route["source_book_name"])
    consolidated_dir = consolidated_dir.resolve()
    return {
        "markdown": consolidated_dir / f"{book_name}.md",
        "meta": consolidated_dir / f"{book_name}_meta.json",
    }


def assess_prereqs(route: dict[str, Any], consolidated_dir: Path) -> dict[str, Any]:
    paths = consolidated_paths_for_route(route, consolidated_dir)
    missing = [name for name, path in paths.items() if not path.exists()]
    return {
        "status": "ready" if not missing else "blocked",
        "missing_prereqs": missing,
        "expected_step_to_run_next": None if not missing else "step_04_consolidate_books.py",
        "paths": {name: str(path) for name, path in paths.items()},
    }


def find_work_row(work_manifest: dict[str, Any], work_id: str) -> dict[str, Any] | None:
    return next(
        (row for row in work_manifest.get("works", []) if str(row.get("work_id") or "").strip() == work_id),
        None,
    )


def assess_step5_state(staging_dir: Path, work_id: str, *, site_root: Path | None = None) -> dict[str, Any]:
    paths = {
        "run_status": staging_dir / "run_status.json",
        "validation_report": staging_dir / "validation_report.json",
        "work_manifest": staging_dir / "work_manifest.generated.json",
        "discovery_gate_report": staging_dir / "discovery_gate_report.json",
    }
    required_names = ("run_status", "validation_report", "work_manifest")
    existing = {name: path.exists() for name, path in paths.items()}
    if not any(existing[name] for name in required_names):
        return {"action": "fresh", "reason": "no staged Step 5 state exists yet", "paths": {name: str(path) for name, path in paths.items()}}
    if not all(existing[name] for name in required_names):
        raise RuntimeError(
            f"Corrupt Step 5 state in {staging_dir}: missing {', '.join(name for name in required_names if not existing[name])}"
        )

    run_status = read_json(paths["run_status"])
    validation_report = read_json(paths["validation_report"])
    work_manifest = read_json(paths["work_manifest"])
    discovery_gate_report = read_json(paths["discovery_gate_report"]) if existing["discovery_gate_report"] else None
    work_row = find_work_row(work_manifest, work_id)
    if not work_row:
        raise RuntimeError(f"Step 5 state in {staging_dir} does not contain work_id {work_id!r}.")
    if not validation_report.get("ok"):
        raise RuntimeError(f"Step 5 validation_report.json is not ok for work_id {work_id!r} in {staging_dir}.")
    if discovery_gate_report is not None and not discovery_gate_report.get("ok"):
        raise RuntimeError(f"Step 5 discovery_gate_report.json is not ok for work_id {work_id!r} in {staging_dir}.")

    stored_site_root = str(run_status.get("site_root") or "").strip()
    if site_root is not None and stored_site_root and not same_path(stored_site_root, site_root):
        return {
            "action": "fresh",
            "reason": f"staged state was built for site_root {stored_site_root!r} but current target is {str(site_root)!r}",
            "run_status": run_status,
            "paths": {name: str(path) for name, path in paths.items()},
        }

    status = str(run_status.get("status") or "").strip()
    if status == "completed":
        if work_row.get("partial"):
            raise RuntimeError(f"Step 5 state is contradictory for work_id {work_id!r}: run_status completed but manifest row is partial.")
        return {
            "action": "skip",
            "reason": "completed staged state is already available",
            "run_status": run_status,
            "validation_report": validation_report,
            "discovery_gate_report": discovery_gate_report,
            "work_row": work_row,
            "paths": {name: str(path) for name, path in paths.items()},
        }
    if status == "running":
        if work_row.get("partial"):
            return {
                "action": "resume",
                "reason": "checkpointed Step 5 state is still marked running but the target work row is partial",
                "run_status": run_status,
                "validation_report": validation_report,
                "discovery_gate_report": discovery_gate_report,
                "work_row": work_row,
                "paths": {name: str(path) for name, path in paths.items()},
            }
        return {
            "action": "skip",
            "reason": "checkpointed Step 5 state already contains a complete work row even though run_status is still running",
            "run_status": run_status,
            "validation_report": validation_report,
            "discovery_gate_report": discovery_gate_report,
            "work_row": work_row,
            "paths": {name: str(path) for name, path in paths.items()},
        }
    if status == "interrupted":
        if not work_row.get("partial"):
            raise RuntimeError(f"Step 5 state is contradictory for work_id {work_id!r}: run_status interrupted but manifest row is not partial.")
        return {
            "action": "resume",
            "reason": "interrupted staged state can be resumed",
            "run_status": run_status,
            "validation_report": validation_report,
            "discovery_gate_report": discovery_gate_report,
            "work_row": work_row,
            "paths": {name: str(path) for name, path in paths.items()},
        }
    raise RuntimeError(f"Unsupported Step 5 run_status value {status!r} in {staging_dir}.")


def clear_step5_generated_state(staging_dir: Path) -> None:
    for filename in sorted(STEP5_STATE_FILES | STEP6_STATE_FILES):
        path = staging_dir / filename
        if path.exists():
            path.unlink()
    # Sweep atomic-write fallout: prod.core.io writes via `<name>.<pid>.tmp` sibling files
    # and renames into place; an interrupted write can leave the tmp behind.
    for tmp_path in staging_dir.glob("*.tmp"):
        try:
            tmp_path.unlink()
        except OSError:
            pass


def count_work_operations(patch_path: Path, work_id: str) -> int:
    payload = read_json_if_exists(patch_path) or {}
    return len(
        [
            item
            for item in payload.get("operations", [])
            if str(item.get("work_id") or "").strip() == work_id
        ]
    )


def count_work_companions(companions_path: Path, work_id: str) -> int:
    payload = read_json_if_exists(companions_path) or []
    return len([item for item in payload if str(item.get("work_id") or "").strip() == work_id])


def live_data_contains_work(site_paths: dict[str, Path], work_id: str, source_book_name: str) -> bool:
    # Detect whether a work has already been merged into the live site. Three signals:
    #   1. Library entries carry work_id directly (set by apply.py via library patch entries).
    #   2. Level1/Level2/Level3 entries that received patches carry the
    #      `<!-- PDF_STAGE5:<work_id>:<section_id> -->` provenance marker in their
    #      full_summary (embedded by schema.patches.apply_degree_patches). This is the
    #      authoritative signal — it is built deterministically per operation.
    #   3. Fallback for entries that came through paths that do not embed the marker
    #      (e.g. library chapter entries created via upsert rather than patches):
    #      stage.py writes the consolidated source path into source_notes, and that
    #      path embeds source_book_name. work_id in work_routing.json may differ
    #      from source_book_name, so we must use source_book_name here.
    library_payload = read_json(site_paths["library"])
    if any(str(entry.get("work_id") or "").strip() == work_id for entry in library_payload.get("entries", [])):
        return True

    marker_needle = f"{APPEND_MARKER_PREFIX}:{work_id}:"
    book_name_needle = source_book_name.strip()
    for degree_key in ("level1", "level2", "level3"):
        degree_path = site_paths.get(degree_key)
        if degree_path is None or not degree_path.exists():
            continue
        payload = read_json(degree_path)
        for entry in payload.get("entries", []):
            if marker_needle in str(entry.get("full_summary") or ""):
                return True
            if book_name_needle and any(book_name_needle in str(note) for note in entry.get("source_notes", [])):
                return True
    return False


def assess_step6_state(staging_dir: Path, site_paths: dict[str, Path], work_id: str, source_book_name: str) -> dict[str, Any]:
    merge_report_path = staging_dir / "step6_merge_report.json"
    validation_path = staging_dir / "step6_validation_report.json"
    if not merge_report_path.exists() or not validation_path.exists():
        return {"action": "apply", "reason": "Step 6 reports do not exist yet", "paths": {"merge_report": str(merge_report_path), "validation_report": str(validation_path)}}

    merge_report = read_json(merge_report_path)
    validation_report = read_json(validation_path)
    selected_work_ids = [str(item).strip() for item in merge_report.get("selected_work_ids", []) if str(item).strip()]
    reported_site_root = str(merge_report.get("site_root") or "").strip()
    same_site = True if not reported_site_root else same_path(reported_site_root, site_paths["site_root"])
    live_evidence = live_data_contains_work(site_paths, work_id, source_book_name)
    current_level1_ops = count_work_operations(staging_dir / "level1.patch.json", work_id)
    current_level2_ops = count_work_operations(staging_dir / "level2.patch.json", work_id)
    current_level3_ops = count_work_operations(staging_dir / "level3.patch.json", work_id)
    reported_level1_selected = int(merge_report.get("level1", {}).get("selected_count") or 0)
    reported_level2_selected = int(merge_report.get("level2", {}).get("selected_count") or 0)
    reported_level3_selected = int(merge_report.get("level3", {}).get("selected_count") or 0)
    level_reports_are_fresh = (
        reported_level1_selected >= current_level1_ops
        and reported_level2_selected >= current_level2_ops
        and reported_level3_selected >= current_level3_ops
    )

    # live_write_completed was added later. Reports written by earlier apply.py revisions
    # don't carry the key at all. When the key is absent we fall back to the other
    # conservative gates (validation_ok, live_evidence, level_reports_are_fresh, same_site,
    # work_id in selected_work_ids), which together attest the work is materialized in live
    # data. When the key is present, require True — a recorded False means the legacy/new
    # apply explicitly failed mid-write and must re-run.
    legacy_merge_report = "live_write_completed" not in merge_report
    live_write_ok = (
        True if legacy_merge_report else merge_report.get("live_write_completed") is True
    )

    if (
        merge_report.get("apply_live") is True
        and live_write_ok
        and validation_report.get("ok") is True
        and same_site
        and work_id in selected_work_ids
        and live_evidence
        and level_reports_are_fresh
    ):
        return {
            "action": "skip",
            "reason": (
                "Step 6 already applied this work into the selected site-root "
                "(legacy merge_report: trusting validation_ok + live_evidence)"
                if legacy_merge_report
                else "Step 6 already applied this work into the selected site-root"
            ),
            "legacy_merge_report": legacy_merge_report,
            "merge_report": merge_report,
            "validation_report": validation_report,
            "paths": {"merge_report": str(merge_report_path), "validation_report": str(validation_path)},
        }

    return {
        "action": "apply",
        "reason": "Step 6 must apply or re-apply this work to the selected site-root",
        "merge_report": merge_report,
        "validation_report": validation_report,
        "paths": {"merge_report": str(merge_report_path), "validation_report": str(validation_path)},
    }


def fingerprints_match(left: dict[str, Any] | None, right: dict[str, Any]) -> bool:
    if not left:
        return False
    return left == right


def latest_qa_manifest_path(qa_reports_root: Path, site_root: Path) -> Path:
    qa_reports_root = qa_reports_root.resolve()
    candidates = (
        qa_reports_root / stable_site_label(site_root) / "latest" / "qa_run_manifest.json",
        qa_reports_root / site_root.resolve().name / "latest" / "qa_run_manifest.json",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def assess_step7_state(site_paths: dict[str, Path], qa_reports_root: Path) -> dict[str, Any]:
    current_fingerprints = build_site_data_stat_signatures(site_paths)
    manifest_path = latest_qa_manifest_path(qa_reports_root, site_paths["site_root"])
    if not manifest_path.exists():
        return {
            "action": "run",
            "reason": "No latest Step 7 QA manifest exists yet",
            "fingerprints": current_fingerprints,
            "manifest_path": str(manifest_path),
        }

    qa_manifest = read_json(manifest_path)
    data_status = str(qa_manifest.get("data_status") or "")
    browser_status = str(qa_manifest.get("browser_status") or "")
    acceptable_statuses = {"pass", "pass-with-warnings", "skip"}
    same_site = same_path(qa_manifest.get("site_root", ""), site_paths["site_root"])
    full_mode = str(qa_manifest.get("mode") or "") == "full"
    full_scope = qa_manifest.get("work_id") in (None, "")
    fresh = fingerprints_match(qa_manifest.get("fingerprints"), current_fingerprints)

    if same_site and full_mode and full_scope and fresh and data_status in acceptable_statuses and browser_status in acceptable_statuses:
        return {
            "action": "skip",
            "reason": "Latest Step 7 QA report already matches the current live data fingerprints",
            "fingerprints": current_fingerprints,
            "manifest_path": str(manifest_path),
            "qa_manifest": qa_manifest,
        }

    return {
        "action": "run",
        "reason": "Live data changed or no reusable full QA report is available",
        "fingerprints": current_fingerprints,
        "manifest_path": str(manifest_path),
        "qa_manifest": qa_manifest,
    }


def step5_command(
    *,
    site_root: Path,
    routing_config: Path,
    consolidated_dir: Path,
    staging_dir: Path,
    provider: str,
    model: str,
    work_id: str,
    resume: bool,
    quiet: bool,
) -> list[str]:
    command = [
        sys.executable,
        str(STEP_05_SCRIPT),
        "--site-root",
        str(site_root),
        "--routing-config",
        str(routing_config),
        "--input-dir",
        str(consolidated_dir),
        "--staging-dir",
        str(staging_dir),
        "--provider",
        provider,
        "--model",
        model,
        "--book",
        work_id,
    ]
    if resume:
        command.append("--resume")
    if quiet:
        command.append("--quiet")
    return command


def step6_command(
    *,
    site_root: Path,
    staging_dir: Path,
    work_id: str,
    include_companions: bool,
    level1_op_count: int,
    level2_op_count: int,
    level3_op_count: int,
    companion_count: int,
    quiet: bool,
) -> list[str]:
    command = [
        sys.executable,
        str(STEP_06_SCRIPT),
        "--site-root",
        str(site_root),
        "--staging-dir",
        str(staging_dir),
        "--work-id",
        work_id,
        "--merge-library",
        "--apply-live",
    ]
    if level1_op_count > 0:
        command.extend(["--approve-level1", "all"])
    if level2_op_count > 0:
        command.extend(["--approve-level2", "all"])
    if level3_op_count > 0:
        command.extend(["--approve-level3", "all"])
    if include_companions and companion_count > 0:
        command.extend(["--approve-companions", "all"])
    if quiet:
        command.append("--quiet")
    return command


def step7_command(*, site_root: Path, report_dir: Path, quiet: bool) -> list[str]:
    command = [
        sys.executable,
        str(STEP_07_SCRIPT),
        "--site-root",
        str(site_root),
        "--report-dir",
        str(report_dir),
        "--mode",
        "full",
    ]
    if quiet:
        command.append("--quiet")
    return command


def artifact_paths(staging_dir: Path) -> dict[str, str]:
    return {
        "run_status": str(staging_dir / "run_status.json"),
        "validation_report": str(staging_dir / "validation_report.json"),
        "discovery_gate_report": str(staging_dir / "discovery_gate_report.json"),
        "work_manifest": str(staging_dir / "work_manifest.generated.json"),
        "step6_merge_report": str(staging_dir / "step6_merge_report.json"),
        "step6_validation_report": str(staging_dir / "step6_validation_report.json"),
    }


def run_exploration_review_for_staging(
    *,
    staging_dir: Path,
    external_review_json: Path | None,
) -> dict[str, Any]:
    clusters = build_clusters(staging_dir)
    external_reviews = normalize_external_reviews(external_review_json.resolve()) if external_review_json else []
    reconciliation_report = reconcile_clusters(clusters, external_reviews)
    run_dir = create_run_dir()
    run_manifest = {
        "created_at": utc_timestamp(),
        "tool": "prod.impl.postmerge_runner",
        "trigger": "automatic_postmerge_exploration_review",
        "staging_dir": str(staging_dir),
        "external_review_json": str(external_review_json.resolve()) if external_review_json else None,
        "cluster_count": len(clusters),
        "external_review_count": len(external_reviews),
        "mutates_live_data": False,
        "intended_integration_point": "after_step5_before_step6_optional",
    }
    outputs = write_exploration_reports(
        run_dir=run_dir,
        run_manifest=run_manifest,
        clusters=clusters,
        external_reviews=external_reviews,
        reconciliation_report=reconciliation_report,
    )
    return {
        "run_dir": str(run_dir),
        "summary_report": outputs["summary_report"],
        "reconciliation_report": outputs["reconciliation_report"],
        "cluster_count": len(clusters),
        "external_review_count": len(external_reviews),
    }


def save_run_manifest(run_root: Path, latest_manifest_path: Path, payload: dict[str, Any]) -> None:
    write_json(run_root / "pipeline_run_manifest.json", payload)
    write_json(latest_manifest_path, payload)


def write_run_summary_md(run_root: Path, manifest: dict[str, Any]) -> None:
    """Write a human-readable RUN_SUMMARY.md and operator_next_action.txt to run_root."""
    status = manifest.get("status", "unknown")
    provider = manifest.get("provider", "unknown")
    model = manifest.get("model", "")
    site_root = manifest.get("site_root", "")
    created_at = manifest.get("created_at", "")
    works = manifest.get("works", [])

    lines: list[str] = [
        "# Pipeline Run Summary",
        "",
        f"**Status:** {status}",
        f"**Provider:** {provider} / {model}",
        f"**Site root:** {site_root}",
        f"**Started:** {created_at}",
        "",
        "## Works",
        "",
    ]
    for w in works:
        wid = w.get("work_id", "?")
        wstatus = w.get("status", "?")
        s5 = (w.get("step5") or {}).get("action", "-")
        s6 = (w.get("step6") or {}).get("action", "-")
        l1 = (w.get("step6") or {}).get("level1_operation_count", 0)
        l2 = (w.get("step6") or {}).get("level2_operation_count", 0)
        l3 = (w.get("step6") or {}).get("level3_operation_count", 0)
        cc = (w.get("step6") or {}).get("companion_count", 0)
        lines.append(f"- **{wid}** ({wstatus}) — step5={s5} step6={s6} ops=({l1}/{l2}/{l3}) companions={cc}")

    step7 = manifest.get("step7") or {}
    data_status = step7.get("data_status", "skip")
    browser_status = step7.get("browser_status", "skip")
    lines += [
        "",
        "## QA",
        "",
        f"- Data QA: **{data_status}**",
        f"- Browser QA: **{browser_status}**",
        "",
    ]

    error = manifest.get("error")
    if error:
        lines += ["## Error", "", f"```", error, "```", ""]

    # Operator next action
    if status == "completed" and data_status == "pass":
        next_action = "Run candidate_review_queue.py to review discovery candidates, then approved_degree_publish.py."
    elif status == "completed-with-warnings":
        next_action = "Check blocked works above. Fix missing consolidated prereqs then re-run."
    elif status == "failed":
        next_action = f"Investigate error: {error or 'see pipeline_run_manifest.json'}"
    else:
        next_action = "Check pipeline_run_manifest.json for details."

    lines += ["## Operator Next Action", "", next_action, ""]

    summary_text = "\n".join(lines)
    write_text(run_root / "RUN_SUMMARY.md", summary_text)
    write_text(run_root / "operator_next_action.txt", next_action + "\n")


def main() -> None:
    args = build_parser().parse_args()
    site_paths = build_site_data_paths(args.site_root.resolve())
    routing_config_path = args.routing_config.resolve()
    staged_runs_root = args.staged_runs_root.resolve()
    consolidated_dir = args.consolidated_dir.resolve()
    qa_reports_root = args.qa_reports_root.resolve()
    pipeline_runs_site_root = ensure_dir(args.pipeline_runs_root.resolve() / stable_site_label(site_paths["site_root"]))
    run_root = ensure_dir(pipeline_runs_site_root / utc_timestamp().replace(":", "-"))
    latest_manifest_path = pipeline_runs_site_root / "latest.json"

    routing_config, routes = load_routes(routing_config_path, args.work_ids)
    run_manifest: dict[str, Any] = {
        "created_at": utc_timestamp(),
        "site_root": str(site_paths["site_root"]),
        "provider": args.provider,
        "model": args.model,
        "routing_config": str(routing_config_path),
        "staged_runs_root": str(staged_runs_root),
        "consolidated_dir": str(consolidated_dir),
        "qa_reports_root": str(qa_reports_root),
        "run_dir": str(run_root),
        "selected_work_ids": [str(route["work_id"]) for route in routes],
        "works": [],
        "step7": {},
        "status": "running",
    }
    run_definition = {
        "tool": "run_steps_05_07",
        "created_at": utc_timestamp(),
        "site_root": str(site_paths["site_root"]),
        "routing_config": str(routing_config_path),
        "staged_runs_root": str(staged_runs_root),
        "consolidated_dir": str(consolidated_dir),
        "pipeline_runs_root": str(args.pipeline_runs_root.resolve()),
        "qa_reports_root": str(qa_reports_root),
        "selected_work_ids": [str(route["work_id"]) for route in routes],
        "provider": args.provider,
        "model": args.model,
        "include_companions": args.include_companions,
        "force_steps": {
            "step5": args.force_step5,
            "step6": args.force_step6,
            "step7": args.force_step7,
        },
        "run_exploration_review": not args.skip_exploration_review,
        "exploration_external_review_json": str(args.exploration_external_review_json.resolve()) if args.exploration_external_review_json else None,
        "quiet": args.quiet,
        "run_dir": str(run_root),
    }
    write_run_definition(run_root, run_definition)
    live_changes = False
    overall_warning = False

    try:
        for route in routes:
            work_id = str(route["work_id"])
            staging_dir = staging_dir_for_route(route, staged_runs_root)
            prereq = assess_prereqs(route, consolidated_dir)
            work_record: dict[str, Any] = {
                "work_id": work_id,
                "source_book_name": route["source_book_name"],
                "staging_dir": str(staging_dir),
                "prereq_status": prereq["status"],
                "missing_prereqs": prereq["missing_prereqs"],
                "expected_step_to_run_next": prereq["expected_step_to_run_next"],
                "prereq_paths": prereq["paths"],
                "step5": {},
                "exploration_review": {},
                "step6": {},
                "artifacts": artifact_paths(staging_dir),
                "status": "pending",
            }
            run_manifest["works"].append(work_record)

            if prereq["status"] != "ready":
                work_record["status"] = "blocked"
                overall_warning = True
                log(
                    f"[work:{work_id}] blocked: missing consolidated prerequisites ({', '.join(prereq['missing_prereqs'])})",
                    quiet=args.quiet,
                )
                continue

            if args.force_step5:
                ensure_dir(staging_dir)
                clear_step5_generated_state(staging_dir)
                step5_state = {"action": "fresh", "reason": "force-step5 requested"}
            else:
                step5_state = assess_step5_state(staging_dir, work_id, site_root=site_paths["site_root"])

            work_record["step5"] = {
                "action": step5_state["action"],
                "reason": step5_state["reason"],
                "provider": args.provider if step5_state["action"] != "skip" else (step5_state.get("run_status") or {}).get("provider"),
            }

            if step5_state["action"] in {"fresh", "resume"}:
                log(f"[work:{work_id}] Step 5 {step5_state['action']}", quiet=args.quiet)
                run_subprocess(
                    step5_command(
                        site_root=site_paths["site_root"],
                        routing_config=routing_config_path,
                        consolidated_dir=consolidated_dir,
                        staging_dir=staging_dir,
                        provider=args.provider,
                        model=args.model,
                        work_id=work_id,
                        resume=step5_state["action"] == "resume",
                        quiet=args.quiet,
                    ),
                    quiet=args.quiet,
                )
                post_step5 = assess_step5_state(staging_dir, work_id, site_root=site_paths["site_root"])
                work_record["step5"]["post_run_action"] = post_step5["action"]
                work_record["step5"]["run_status"] = (post_step5.get("run_status") or {}).get("status")
                if post_step5["action"] != "skip":
                    raise RuntimeError(
                        f"Step 5 for work_id {work_id!r} did not reach a completed staged state. "
                        f"It ended in action={post_step5['action']!r}."
                    )
            else:
                log(f"[work:{work_id}] Step 5 skipped", quiet=args.quiet)

            if not args.skip_exploration_review:
                log(f"[work:{work_id}] exploration review", quiet=args.quiet)
                exploration_result = run_exploration_review_for_staging(
                    staging_dir=staging_dir,
                    external_review_json=args.exploration_external_review_json,
                )
                work_record["exploration_review"] = exploration_result
            else:
                work_record["exploration_review"] = {
                    "action": "skip",
                    "reason": "exploration review explicitly skipped",
                }

            if args.force_step6:
                step6_state = {"action": "apply", "reason": "force-step6 requested"}
            else:
                step6_state = assess_step6_state(staging_dir, site_paths, work_id, str(route["source_book_name"]))

            level1_op_count = count_work_operations(staging_dir / "level1.patch.json", work_id)
            level2_op_count = count_work_operations(staging_dir / "level2.patch.json", work_id)
            level3_op_count = count_work_operations(staging_dir / "level3.patch.json", work_id)
            companion_count = count_work_companions(staging_dir / "companion_candidates.json", work_id)
            work_record["step6"] = {
                "action": step6_state["action"],
                "reason": step6_state["reason"],
                "level1_operation_count": level1_op_count,
                "level2_operation_count": level2_op_count,
                "level3_operation_count": level3_op_count,
                "companion_count": companion_count,
                "include_companions": args.include_companions,
            }

            if step6_state["action"] == "apply":
                log(f"[work:{work_id}] Step 6 apply-live", quiet=args.quiet)
                run_subprocess(
                    step6_command(
                        site_root=site_paths["site_root"],
                        staging_dir=staging_dir,
                        work_id=work_id,
                        include_companions=args.include_companions,
                        level1_op_count=level1_op_count,
                        level2_op_count=level2_op_count,
                        level3_op_count=level3_op_count,
                        companion_count=companion_count,
                        quiet=args.quiet,
                    ),
                    quiet=args.quiet,
                )
                post_step6 = assess_step6_state(staging_dir, site_paths, work_id, str(route["source_book_name"]))
                if post_step6["action"] != "skip":
                    raise RuntimeError(
                        f"Step 6 for work_id {work_id!r} did not reach an applied-live state for {site_paths['site_root']}."
                    )
                live_changes = True
            else:
                log(f"[work:{work_id}] Step 6 skipped", quiet=args.quiet)

            work_record["status"] = "completed"

        if args.force_step7:
            step7_state = {"action": "run", "reason": "force-step7 requested"}
        elif live_changes:
            step7_state = {"action": "run", "reason": "live data changed during this pipeline run"}
        else:
            step7_state = assess_step7_state(site_paths, qa_reports_root)

        run_manifest["step7"] = {
            "action": step7_state["action"],
            "reason": step7_state["reason"],
            "manifest_path": step7_state.get("manifest_path"),
        }

        if step7_state["action"] == "run":
            log("[step7] running full QA", quiet=args.quiet)
            step7_report_dir = ensure_dir(
                qa_reports_root / stable_site_label(site_paths["site_root"]) / utc_timestamp().replace(":", "-")
            )
            run_subprocess(
                step7_command(site_root=site_paths["site_root"], report_dir=step7_report_dir, quiet=args.quiet),
                quiet=args.quiet,
            )
            latest_qa_manifest = read_json(step7_report_dir / "qa_run_manifest.json")
            run_manifest["step7"]["manifest_path"] = str(step7_report_dir / "qa_run_manifest.json")
        else:
            log("[step7] skipped", quiet=args.quiet)
            latest_qa_manifest = read_json(Path(step7_state["manifest_path"]))

        run_manifest["step7"]["data_status"] = latest_qa_manifest.get("data_status")
        run_manifest["step7"]["browser_status"] = latest_qa_manifest.get("browser_status")
        run_manifest["step7"]["report_dir"] = latest_qa_manifest.get("report_dir")
        run_manifest["step7"]["fingerprints"] = latest_qa_manifest.get("fingerprints")

        if latest_qa_manifest.get("data_status") == "fail" or latest_qa_manifest.get("browser_status") == "fail":
            raise RuntimeError("Step 7 QA failed on the current live site.")

        run_manifest["status"] = "completed-with-warnings" if overall_warning else "completed"
        save_run_manifest(run_root, latest_manifest_path, run_manifest)
        write_run_summary_md(run_root, run_manifest)
        log(
            f"[done] status={run_manifest['status']} works={len(routes)} live_changes={'yes' if live_changes else 'no'}",
            quiet=args.quiet,
        )
        log(f"[summary] RUN_SUMMARY.md written to {run_root}", quiet=args.quiet)
    except Exception as exc:
        run_manifest["status"] = "failed"
        run_manifest["error"] = str(exc)
        save_run_manifest(run_root, latest_manifest_path, run_manifest)
        write_run_summary_md(run_root, run_manifest)
        print(f"[error] {exc}", flush=True)
        raise


if __name__ == "__main__":
    main()
