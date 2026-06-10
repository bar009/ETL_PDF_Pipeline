from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parents[1]
PDF_HANDLE_ROOT = TOOLS_DIR.parent
CODE_ROOT = PDF_HANDLE_ROOT.parent
if str(PDF_HANDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(PDF_HANDLE_ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from pipeline_utils import atomic_write_text, read_json, safe_json_write, utc_timestamp
from workspace_paths import get_work_site_root

F2_SCRIPT = TOOLS_DIR / "semantic_system_purity_review.py"
F3_SCRIPT = TOOLS_DIR / "content_routing_review.py"
F4_SCRIPT = TOOLS_DIR / "content_apply_engine.py"

DEFAULT_SOURCE_SITE_ROOT = get_work_site_root()
DEFAULT_MANIFEST = TOOLS_DIR / "knowledge_flow_waves" / "level1.phase-f-wider-sandbox-pilot.json"
DEFAULT_REPORT_ROOT = TOOLS_DIR / "reports" / "phase_f_sandbox_pilot"
DEFAULT_SITE_COPY_PARENT = CODE_ROOT / "sandbox_sites"
DEFAULT_PRESERVATION_PARENT = CODE_ROOT.parent / "preservation_sandboxes" / "phase_f_sandbox_pilot"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

F2_SUMMARY_ARTIFACT = "semantic_purity_summary.json"
F2_ENTRIES_ARTIFACT = "semantic_purity_entries.json"
F3_SUMMARY_ARTIFACT = "content_routing_summary.json"
F3_ENTRIES_ARTIFACT = "content_routing_entries.json"
F4_SUMMARY_ARTIFACT = "content_apply_summary.json"
F4_ACTIONS_ARTIFACT = "content_apply_actions.json"
F4_APPLY_MANIFEST = "apply_manifest.json"
F4_BACKUP_MANIFEST = "pre_apply_backups/backup_manifest.json"

PLAN_MODE = "plan"
APPLY_SAFE_MODE = "apply-safe"


class PilotFailure(RuntimeError):
    pass


def console_status(message: str) -> None:
    print(message, flush=True)


def timestamp_slug() -> str:
    return utc_timestamp().replace(":", "-").replace("+00:00", "Z")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def truncate_text(value: Any, *, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def artifact_exists(path: Path) -> bool:
    return path.exists() and path.is_file()


def require_provider_credentials(provider: str) -> None:
    if provider != "gemini":
        return
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return
    raise PilotFailure(
        "Provider 'gemini' requires GEMINI_API_KEY or GOOGLE_API_KEY in the environment. "
        "Use --provider heuristic or export a Gemini key first."
    )


def copy_site_root(*, source: Path, destination: Path) -> None:
    resolved_source = source.resolve()
    resolved_destination = destination.resolve()
    if not resolved_source.exists():
        raise PilotFailure(f"Source site root does not exist: {resolved_source}")
    if resolved_destination.exists():
        raise PilotFailure(f"Pilot site root already exists: {resolved_destination}")
    ensure_dir(resolved_destination.parent)
    shutil.copytree(
        resolved_source,
        resolved_destination,
        ignore=shutil.ignore_patterns("__pycache__"),
    )


def run_command(
    *,
    stage_name: str,
    command: list[str],
    workdir: Path,
    log_dir: Path,
) -> None:
    console_status(f"[phase-f] starting {stage_name}...")
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(workdir),
        env=os.environ.copy(),
    )
    atomic_write_text(log_dir / f"{stage_name}.stdout.log", completed.stdout)
    atomic_write_text(log_dir / f"{stage_name}.stderr.log", completed.stderr)
    if completed.returncode != 0:
        raise PilotFailure(
            f"{stage_name} failed with exit code {completed.returncode}. "
            f"See {log_dir / f'{stage_name}.stderr.log'}"
        )
    console_status(
        f"[phase-f] completed {stage_name}. logs={log_dir / f'{stage_name}.stdout.log'}"
    )


def flatten_routing_rows(entry_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entry_rows:
        reviews = entry.get("routing_reviews")
        if not isinstance(reviews, list):
            continue
        for row in reviews:
            if isinstance(row, dict):
                rows.append(row)
    rows.sort(key=lambda item: str(item.get("review_unit_id") or ""))
    return rows


def build_routing_samples(rows: list[dict[str, Any]], *, limit: int = 10) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for row in rows:
        samples.append(
            {
                "review_unit_id": row.get("review_unit_id"),
                "entry_slug": row.get("entry_slug"),
                "field_name": row.get("field_name"),
                "routing_decision": row.get("routing_decision"),
                "routing_unit_status": row.get("routing_unit_status"),
                "final_provider_status": row.get("final_provider_status"),
                "library_bucket": row.get("library_bucket"),
                "future_entry_label": row.get("future_entry_label"),
                "target_slug": row.get("target_slug"),
                "excerpt": truncate_text(row.get("text_excerpt")),
            }
        )
        if len(samples) >= limit:
            break
    return samples


def build_action_samples(
    action_rows: list[dict[str, Any]],
    *,
    action_type: str,
    action_status: str = "applied",
    limit: int = 10,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for action in sorted(action_rows, key=lambda item: str(item.get("review_unit_id") or "")):
        if action.get("action_type") != action_type or action.get("action_status") != action_status:
            continue
        samples.append(
            {
                "review_unit_id": action.get("review_unit_id"),
                "entry_slug": action.get("source_entry_slug"),
                "field_name": action.get("field_name"),
                "routing_decision": action.get("routing_decision"),
                "library_bucket": action.get("library_bucket"),
                "future_entry_label": action.get("future_entry_label"),
                "target_slug": action.get("target_slug"),
                "preservation_path": action.get("preservation_path"),
                "source_patch_status": action.get("source_patch_status"),
                "excerpt": truncate_text(action.get("text_excerpt")),
            }
        )
        if len(samples) >= limit:
            break
    return samples


def count_json_files(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*.json") if path.is_file())


def render_key_value_rows(title: str, values: dict[str, Any]) -> list[str]:
    rows = [f"## {title}", ""]
    if not values:
        rows.append("- none")
        rows.append("")
        return rows
    for key, value in values.items():
        rows.append(f"- `{key}`: `{value}`")
    rows.append("")
    return rows


def render_sample_section(title: str, rows: list[dict[str, Any]]) -> list[str]:
    lines = [f"## {title}", ""]
    if not rows:
        lines.append("- none")
        lines.append("")
        return lines
    for row in rows:
        parts = [
            f"`{row.get('review_unit_id')}`",
            f"entry=`{row.get('entry_slug')}`",
        ]
        if row.get("field_name"):
            parts.append(f"field=`{row.get('field_name')}`")
        if row.get("routing_decision"):
            parts.append(f"decision=`{row.get('routing_decision')}`")
        if row.get("library_bucket"):
            parts.append(f"library=`{row.get('library_bucket')}`")
        if row.get("future_entry_label"):
            parts.append(f"future=`{row.get('future_entry_label')}`")
        if row.get("target_slug"):
            parts.append(f"target=`{row.get('target_slug')}`")
        if row.get("source_patch_status"):
            parts.append(f"source_patch=`{row.get('source_patch_status')}`")
        if row.get("preservation_path"):
            parts.append(f"path=`{row.get('preservation_path')}`")
        lines.append("- " + " ".join(parts))
        if row.get("excerpt"):
            lines.append(f"  excerpt=`{row['excerpt']}`")
    lines.append("")
    return lines


def build_acceptance_checks(
    *,
    provider: str,
    f2_summary: dict[str, Any],
    f3_summary: dict[str, Any],
    f4_plan_summary: dict[str, Any] | None,
    f4_apply_summary: dict[str, Any],
    library_file_count: int,
    future_file_count: int,
    backup_manifest_exists: bool,
    preserved_samples: list[dict[str, Any]],
    removal_samples: list[dict[str, Any]],
    routing_samples: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    checks: list[dict[str, Any]] = []

    no_live_root = not bool(f4_apply_summary.get("is_live_preservation_root"))
    checks.append(
        {
            "name": "Test 1",
            "label": "end-to-end run stayed off live roots",
            "passed": no_live_root,
            "details": (
                f"provider={provider}; effective_preservation_mode={f4_apply_summary.get('effective_preservation_mode')}; "
                f"is_live_preservation_root={f4_apply_summary.get('is_live_preservation_root')}"
            ),
        }
    )

    outputs_ok = (
        library_file_count > 0
        and future_file_count > 0
        and backup_manifest_exists
        and (f4_apply_summary.get("preservation_units_written", 0) > 0)
    )
    checks.append(
        {
            "name": "Test 2",
            "label": "sandbox outputs were created",
            "passed": outputs_ok,
            "details": (
                f"library_json_files={library_file_count}; future_json_files={future_file_count}; "
                f"backup_manifest_exists={backup_manifest_exists}; preservation_units_written={f4_apply_summary.get('preservation_units_written', 0)}"
            ),
        }
    )

    inspection_ok = len(preserved_samples) >= 5 and len(removal_samples) >= 5 and len(routing_samples) >= 5
    checks.append(
        {
            "name": "Test 3",
            "label": "sample inspection set is available",
            "passed": inspection_ok,
            "details": (
                f"preserved_samples={len(preserved_samples)}; removal_samples={len(removal_samples)}; "
                f"routing_samples={len(routing_samples)}"
            ),
        }
    )

    stability_ok = (
        f2_summary.get("run_status") != "interrupted"
        and f3_summary.get("run_status") != "interrupted"
        and f4_apply_summary.get("status") != "fail"
        and f4_apply_summary.get("preservation_changed_overwrite_count", 0) == 0
        and f4_apply_summary.get("preservation_path_retarget_count", 0) == 0
    )
    checks.append(
        {
            "name": "Test 4",
            "label": "no corruption, overwrite drift, or resume chaos was detected",
            "passed": stability_ok,
            "details": (
                f"f2_status={f2_summary.get('run_status')}; f3_status={f3_summary.get('run_status')}; "
                f"f4_status={f4_apply_summary.get('status')}; "
                f"changed_overwrites={f4_apply_summary.get('preservation_changed_overwrite_count', 0)}; "
                f"retargeted={f4_apply_summary.get('preservation_path_retarget_count', 0)}"
            ),
        }
    )

    if all(check["passed"] for check in checks):
        verdict = "ready for larger pilot / full level1 subset"
    else:
        verdict = "issues to fix before scaling"

    checks.append(
        {
            "name": "Test 5",
            "label": "pilot conclusion",
            "passed": all(check["passed"] for check in checks),
            "details": verdict,
        }
    )
    return checks, verdict


def render_report(
    *,
    run_id: str,
    provider: str,
    model: str | None,
    manifest_path: Path,
    source_site_root: Path,
    pilot_site_root: Path,
    report_dir: Path,
    preservation_root: Path,
    f2_report_dir: Path,
    f3_report_dir: Path,
    f4_plan_dir: Path | None,
    f4_apply_dir: Path,
    f2_summary: dict[str, Any],
    f3_summary: dict[str, Any],
    f4_plan_summary: dict[str, Any] | None,
    f4_apply_summary: dict[str, Any],
    acceptance_checks: list[dict[str, Any]],
    verdict: str,
    routing_samples: list[dict[str, Any]],
    preserved_samples: list[dict[str, Any]],
    removal_samples: list[dict[str, Any]],
    library_file_count: int,
    future_file_count: int,
    backup_manifest_exists: bool,
) -> str:
    lines = [
        "# Phase F Sandbox Pilot",
        "",
        f"- Run id: `{run_id}`",
        f"- Provider: `{provider}`",
        f"- Model: `{model or '-'}`",
        f"- Manifest: `{manifest_path.resolve()}`",
        f"- Source site root: `{source_site_root.resolve()}`",
        f"- Pilot site root: `{pilot_site_root.resolve()}`",
        f"- Report dir: `{report_dir.resolve()}`",
        f"- Preservation root: `{preservation_root.resolve()}`",
        f"- F2 report dir: `{f2_report_dir.resolve()}`",
        f"- F3 report dir: `{f3_report_dir.resolve()}`",
        f"- F4 apply-safe report dir: `{f4_apply_dir.resolve()}`",
        "",
    ]
    if f4_plan_dir is not None:
        lines.append(f"- F4 plan report dir: `{f4_plan_dir.resolve()}`")
        lines.append("")
    if provider == "heuristic":
        lines.extend(
            [
                "## Provider Note",
                "",
                "- This pilot used `heuristic` because no Gemini API key was available in the runtime environment.",
                "- The run validates end-to-end sandbox mechanics for F2/F3/F4, not live-provider behavior under Gemini.",
                "",
            ]
        )

    lines.extend(
        [
            "## Stage Results",
            "",
            f"- F2 run_status: `{f2_summary.get('run_status')}` total_units=`{f2_summary.get('total_units')}` completed=`{f2_summary.get('completed_units')}` failed=`{f2_summary.get('failed_units')}` pending=`{f2_summary.get('pending_units')}`",
            f"- F3 run_status: `{f3_summary.get('run_status')}` total_units=`{f3_summary.get('total_units')}` completed=`{f3_summary.get('completed_units')}` failed=`{f3_summary.get('failed_units')}` pending=`{f3_summary.get('pending_units')}`",
            f"- F4 apply-safe status: `{f4_apply_summary.get('status')}` actions=`{f4_apply_summary.get('eligible_action_count')}` preserved=`{f4_apply_summary.get('preservation_units_written')}` manual_followup=`{f4_apply_summary.get('manual_followup_count')}`",
            "",
        ]
    )
    if f4_plan_summary is not None:
        lines.append(
            f"- F4 plan status: `{f4_plan_summary.get('status')}` actions=`{f4_plan_summary.get('eligible_action_count')}`"
        )
        lines.append("")

    lines.extend(render_key_value_rows("F3 Routing Decisions", f3_summary.get("routing_decision_counts", {})))
    lines.extend(render_key_value_rows("F4 Action Types", f4_apply_summary.get("action_type_counts", {})))
    lines.extend(render_key_value_rows("F4 Action Statuses", f4_apply_summary.get("action_status_counts", {})))
    lines.extend(
        [
            "## Sandbox Outputs",
            "",
            f"- library json files: `{library_file_count}`",
            f"- future-entry json files: `{future_file_count}`",
            f"- backup manifest exists: `{backup_manifest_exists}`",
            f"- live preservation root used: `{f4_apply_summary.get('is_live_preservation_root')}`",
            "",
            "## Acceptance Checks",
            "",
        ]
    )
    for check in acceptance_checks:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- [{status}] `{check['name']}` {check['label']}")
        lines.append(f"  {check['details']}")
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    lines.append(f"- `{verdict}`")
    lines.append("")
    lines.extend(render_sample_section("Routing Decision Inspection Set", routing_samples))
    lines.extend(render_sample_section("Preserved Unit Inspection Set", preserved_samples))
    lines.extend(render_sample_section("Source Removal Inspection Set", removal_samples))
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the wider Phase F sandbox pilot for F2/F3/F4.")
    parser.add_argument("--source-site-root", type=Path, default=DEFAULT_SOURCE_SITE_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--provider", choices=["heuristic", "gemini"], default="heuristic")
    parser.add_argument("--model", default=DEFAULT_GEMINI_MODEL)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--site-copy-parent", type=Path, default=DEFAULT_SITE_COPY_PARENT)
    parser.add_argument("--preservation-parent", type=Path, default=DEFAULT_PRESERVATION_PARENT)
    parser.add_argument("--skip-plan", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    require_provider_credentials(args.provider)

    run_id = timestamp_slug()
    report_dir = (args.report_root.resolve() / run_id).resolve()
    stage_log_dir = ensure_dir(report_dir / "stage_logs")
    f2_report_dir = report_dir / "f2"
    f3_report_dir = report_dir / "f3"
    f4_plan_dir = None if args.skip_plan else report_dir / "f4_plan"
    f4_apply_dir = report_dir / "f4_apply_safe"
    pilot_site_root = (args.site_copy_parent.resolve() / f"phase-f-{run_id}").resolve()
    preservation_root = (args.preservation_parent.resolve() / run_id).resolve()

    ensure_dir(report_dir)
    console_status(f"[phase-f] run_id={run_id}")
    console_status(f"[phase-f] provider={args.provider} model={args.model if args.provider == 'gemini' else '-'}")
    console_status(f"[phase-f] manifest={args.manifest.resolve()}")
    console_status(f"[phase-f] report_dir={report_dir}")
    console_status(f"[phase-f] pilot_site_root={pilot_site_root}")
    console_status(f"[phase-f] preservation_root={preservation_root}")
    copy_site_root(source=args.source_site_root, destination=pilot_site_root)
    ensure_dir(preservation_root)

    f2_command = [
        sys.executable,
        str(F2_SCRIPT),
        "--site-root",
        str(pilot_site_root),
        "--manifest",
        str(args.manifest.resolve()),
        "--provider",
        args.provider,
        "--report-dir",
        str(f2_report_dir),
        "--strict",
        "--quiet",
    ]
    if args.provider == "gemini":
        f2_command.extend(["--model", args.model])
    run_command(stage_name="f2", command=f2_command, workdir=CODE_ROOT, log_dir=stage_log_dir)

    f3_command = [
        sys.executable,
        str(F3_SCRIPT),
        "--f2-report-dir",
        str(f2_report_dir),
        "--site-root",
        str(pilot_site_root),
        "--manifest",
        str(args.manifest.resolve()),
        "--provider",
        args.provider,
        "--report-dir",
        str(f3_report_dir),
        "--strict",
        "--quiet",
    ]
    if args.provider == "gemini":
        f3_command.extend(["--model", args.model])
    run_command(stage_name="f3", command=f3_command, workdir=CODE_ROOT, log_dir=stage_log_dir)

    if f4_plan_dir is not None:
        f4_plan_command = [
            sys.executable,
            str(F4_SCRIPT),
            "--f3-report-dir",
            str(f3_report_dir),
            "--site-root",
            str(pilot_site_root),
            "--manifest",
            str(args.manifest.resolve()),
            "--mode",
            PLAN_MODE,
            "--report-dir",
            str(f4_plan_dir),
            "--strict",
            "--quiet",
        ]
        run_command(stage_name="f4_plan", command=f4_plan_command, workdir=CODE_ROOT, log_dir=stage_log_dir)

    f4_apply_command = [
        sys.executable,
        str(F4_SCRIPT),
        "--f3-report-dir",
        str(f3_report_dir),
        "--site-root",
        str(pilot_site_root),
        "--manifest",
        str(args.manifest.resolve()),
        "--mode",
        APPLY_SAFE_MODE,
        "--preservation-root",
        str(preservation_root),
        "--report-dir",
        str(f4_apply_dir),
        "--strict",
        "--quiet",
    ]
    run_command(stage_name="f4_apply_safe", command=f4_apply_command, workdir=CODE_ROOT, log_dir=stage_log_dir)

    f2_summary = read_json(f2_report_dir / F2_SUMMARY_ARTIFACT)
    f3_summary = read_json(f3_report_dir / F3_SUMMARY_ARTIFACT)
    f3_entries = read_json(f3_report_dir / F3_ENTRIES_ARTIFACT)
    f4_plan_summary = read_json(f4_plan_dir / F4_SUMMARY_ARTIFACT) if f4_plan_dir is not None else None
    f4_apply_summary = read_json(f4_apply_dir / F4_SUMMARY_ARTIFACT)
    f4_action_rows = read_json(f4_apply_dir / F4_ACTIONS_ARTIFACT)

    routing_rows = flatten_routing_rows(f3_entries)
    routing_samples = build_routing_samples(routing_rows, limit=10)
    preserved_samples = build_action_samples(
        f4_action_rows,
        action_type="preserve_to_library",
        action_status="applied",
        limit=5,
    )
    preserved_samples.extend(
        build_action_samples(
            f4_action_rows,
            action_type="preserve_to_future_seed",
            action_status="applied",
            limit=max(0, 10 - len(preserved_samples)),
        )
    )
    removal_samples = build_action_samples(
        f4_action_rows,
        action_type="remove_from_source",
        action_status="applied",
        limit=10,
    )

    library_file_count = count_json_files(preservation_root / "library")
    future_file_count = count_json_files(preservation_root / "future_entries")
    backup_manifest_exists = artifact_exists(f4_apply_dir / F4_BACKUP_MANIFEST)
    acceptance_checks, verdict = build_acceptance_checks(
        provider=args.provider,
        f2_summary=f2_summary,
        f3_summary=f3_summary,
        f4_plan_summary=f4_plan_summary,
        f4_apply_summary=f4_apply_summary,
        library_file_count=library_file_count,
        future_file_count=future_file_count,
        backup_manifest_exists=backup_manifest_exists,
        preserved_samples=preserved_samples,
        removal_samples=removal_samples,
        routing_samples=routing_samples,
    )

    report_text = render_report(
        run_id=run_id,
        provider=args.provider,
        model=(args.model if args.provider == "gemini" else None),
        manifest_path=args.manifest.resolve(),
        source_site_root=args.source_site_root.resolve(),
        pilot_site_root=pilot_site_root,
        report_dir=report_dir,
        preservation_root=preservation_root,
        f2_report_dir=f2_report_dir,
        f3_report_dir=f3_report_dir,
        f4_plan_dir=f4_plan_dir,
        f4_apply_dir=f4_apply_dir,
        f2_summary=f2_summary,
        f3_summary=f3_summary,
        f4_plan_summary=f4_plan_summary,
        f4_apply_summary=f4_apply_summary,
        acceptance_checks=acceptance_checks,
        verdict=verdict,
        routing_samples=routing_samples,
        preserved_samples=preserved_samples,
        removal_samples=removal_samples,
        library_file_count=library_file_count,
        future_file_count=future_file_count,
        backup_manifest_exists=backup_manifest_exists,
    )

    safe_json_write(
        report_dir / "phase_f_sandbox_pilot_summary.json",
        {
            "run_id": run_id,
            "script_version": 1,
            "provider": args.provider,
            "model": args.model if args.provider == "gemini" else None,
            "manifest_path": str(args.manifest.resolve()),
            "source_site_root": str(args.source_site_root.resolve()),
            "pilot_site_root": str(pilot_site_root),
            "report_dir": str(report_dir),
            "preservation_root": str(preservation_root),
            "f2_report_dir": str(f2_report_dir),
            "f3_report_dir": str(f3_report_dir),
            "f4_plan_dir": str(f4_plan_dir.resolve()) if f4_plan_dir is not None else None,
            "f4_apply_dir": str(f4_apply_dir),
            "f2_summary_path": str((f2_report_dir / F2_SUMMARY_ARTIFACT).resolve()),
            "f3_summary_path": str((f3_report_dir / F3_SUMMARY_ARTIFACT).resolve()),
            "f4_summary_path": str((f4_apply_dir / F4_SUMMARY_ARTIFACT).resolve()),
            "acceptance_checks": acceptance_checks,
            "verdict": verdict,
            "library_file_count": library_file_count,
            "future_file_count": future_file_count,
            "backup_manifest_exists": backup_manifest_exists,
            "routing_samples": routing_samples,
            "preserved_samples": preserved_samples,
            "removal_samples": removal_samples,
        },
    )
    atomic_write_text(report_dir / "PHASE_F_SANDBOX_PILOT_REPORT.md", report_text)
    console_status(f"[phase-f] completed. summary={report_dir / 'phase_f_sandbox_pilot_summary.json'}")
    console_status(f"[phase-f] report={report_dir / 'PHASE_F_SANDBOX_PILOT_REPORT.md'}")


if __name__ == "__main__":
    main()
