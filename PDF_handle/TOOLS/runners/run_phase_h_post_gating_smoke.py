from __future__ import annotations

import argparse
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

DEFAULT_SOURCE_SITE_ROOT = get_work_site_root()
DEFAULT_MANIFEST = TOOLS_DIR / "knowledge_flow_waves" / "level1.phase-h-post-gating-smoke.json"
DEFAULT_REPORT_ROOT = TOOLS_DIR / "reports" / "phase_h_post_gating_live_smoke"
DEFAULT_SITE_COPY_PARENT = CODE_ROOT / "sandbox_sites"
DEFAULT_BASELINE_ROOT = TOOLS_DIR / "reports" / "phase_f_sandbox_pilot_live_smoke"
DEFAULT_PROVIDER = "gemini"
DEFAULT_PROVIDER_POLICY = "provider_uncertain_only"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

F2_SUMMARY_ARTIFACT = "semantic_purity_summary.json"
F2_ENTRIES_ARTIFACT = "semantic_purity_entries.json"
F3_SUMMARY_ARTIFACT = "content_routing_summary.json"
F3_ENTRIES_ARTIFACT = "content_routing_entries.json"


class PhaseHFailure(RuntimeError):
    pass


def console_status(message: str) -> None:
    print(message, flush=True)


def timestamp_slug() -> str:
    return utc_timestamp().replace(":", "-").replace("+00:00", "Z")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def compact_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def truncate_text(value: Any, *, limit: int = 180) -> str:
    text = compact_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def require_provider_credentials(provider: str) -> None:
    if provider != "gemini":
        return
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return
    raise PhaseHFailure(
        "Provider 'gemini' requires GEMINI_API_KEY or GOOGLE_API_KEY in the environment."
    )


def copy_site_root(*, source: Path, destination: Path) -> None:
    resolved_source = source.resolve()
    resolved_destination = destination.resolve()
    if not resolved_source.exists():
        raise PhaseHFailure(f"Source site root does not exist: {resolved_source}")
    if resolved_destination.exists():
        raise PhaseHFailure(f"Sandbox site root already exists: {resolved_destination}")
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
    console_status(f"[phase-h] starting {stage_name}...")
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
        raise PhaseHFailure(
            f"{stage_name} failed with exit code {completed.returncode}. "
            f"See {log_dir / f'{stage_name}.stderr.log'}"
        )
    console_status(f"[phase-h] completed {stage_name}.")


def detect_baseline_report_dir(explicit: Path | None) -> Path | None:
    if explicit is not None:
        resolved = explicit.resolve()
        if not resolved.exists():
            raise PhaseHFailure(f"Baseline report dir does not exist: {resolved}")
        return resolved
    if not DEFAULT_BASELINE_ROOT.exists():
        return None
    candidates = [item for item in DEFAULT_BASELINE_ROOT.iterdir() if item.is_dir()]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0]


def flatten_f2_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_slug = entry.get("slug")
        for row in entry.get("paragraph_reviews", []):
            if not isinstance(row, dict):
                continue
            materialized = dict(row)
            materialized.setdefault("entry_slug", entry_slug)
            rows.append(materialized)
    return rows


def flatten_f3_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        source_slug = entry.get("slug")
        for row in entry.get("routing_reviews", []):
            if not isinstance(row, dict):
                continue
            materialized = dict(row)
            materialized.setdefault("source_entry_slug", source_slug)
            rows.append(materialized)
    return rows


def sample_rows(
    rows: list[dict[str, Any]],
    *,
    limit: int,
    predicate,
    confidence_key: str,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for row in rows:
        if not predicate(row):
            continue
        samples.append(
            {
                "review_unit_id": row.get("review_unit_id"),
                "entry_slug": row.get("entry_slug") or row.get("source_entry_slug"),
                "decision_source": row.get("decision_source"),
                "heuristic_confidence": row.get(confidence_key),
                "provider_invoked": bool(row.get("provider_invoked")),
                "provider_skipped_reason": row.get("provider_skipped_reason"),
                "final_provider_status": row.get("final_provider_status"),
                "excerpt": truncate_text(row.get("text_excerpt")),
            }
        )
        if len(samples) >= limit:
            break
    return samples


def summary_int(summary: dict[str, Any], key: str, default: int) -> int:
    value = summary.get(key)
    if value is None:
        return default
    return int(value)


def extract_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    total_units = summary_int(summary, "total_units", 0)
    provider_invoked_units = summary_int(summary, "provider_invoked_units", total_units)
    provider_eligible_units = summary_int(summary, "provider_eligible_units", total_units)
    heuristic_only_units = summary_int(
        summary,
        "heuristic_only_units",
        max(total_units - provider_invoked_units, 0),
    )
    provider_skip_count = summary_int(
        summary,
        "provider_skip_count",
        max(total_units - provider_invoked_units, 0),
    )
    malformed_json_count = summary_int(summary, "malformed_json_count", 0)
    failed_attempts = summary_int(
        summary,
        "failed_attempts",
        summary_int(summary, "gemini_failed_attempt_count", 0),
    )
    elapsed_seconds = summary.get("elapsed_seconds")
    escalation_rate = summary.get("escalation_rate")
    if escalation_rate is None:
        escalation_rate = round(provider_invoked_units / total_units, 4) if total_units else 0.0
    return {
        "total_units": total_units,
        "provider_eligible_units": provider_eligible_units,
        "provider_invoked_units": provider_invoked_units,
        "heuristic_only_units": heuristic_only_units,
        "provider_skip_count": provider_skip_count,
        "escalation_rate": float(escalation_rate or 0.0),
        "malformed_json_count": malformed_json_count,
        "failed_attempts": failed_attempts,
        "elapsed_seconds": elapsed_seconds,
        "status": summary.get("status"),
    }


def combine_metrics(*, f2_metrics: dict[str, Any], f3_metrics: dict[str, Any]) -> dict[str, Any]:
    total_units = f2_metrics["total_units"] + f3_metrics["total_units"]
    provider_eligible_units = f2_metrics["provider_eligible_units"] + f3_metrics["provider_eligible_units"]
    provider_invoked_units = f2_metrics["provider_invoked_units"] + f3_metrics["provider_invoked_units"]
    heuristic_only_units = f2_metrics["heuristic_only_units"] + f3_metrics["heuristic_only_units"]
    provider_skip_count = f2_metrics["provider_skip_count"] + f3_metrics["provider_skip_count"]
    malformed_json_count = f2_metrics["malformed_json_count"] + f3_metrics["malformed_json_count"]
    failed_attempts = f2_metrics["failed_attempts"] + f3_metrics["failed_attempts"]
    elapsed_values = [value for value in (f2_metrics["elapsed_seconds"], f3_metrics["elapsed_seconds"]) if isinstance(value, (int, float))]
    elapsed_seconds = round(sum(elapsed_values), 3) if elapsed_values else None
    escalation_rate = round(provider_invoked_units / total_units, 4) if total_units else 0.0
    return {
        "total_units": total_units,
        "provider_eligible_units": provider_eligible_units,
        "provider_invoked_units": provider_invoked_units,
        "heuristic_only_units": heuristic_only_units,
        "provider_skip_count": provider_skip_count,
        "malformed_json_count": malformed_json_count,
        "failed_attempts": failed_attempts,
        "elapsed_seconds": elapsed_seconds,
        "escalation_rate": escalation_rate,
    }


def build_acceptance_checks(
    *,
    combined_metrics: dict[str, Any],
    baseline_metrics: dict[str, Any] | None,
    sample_sets: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], str]:
    checks: list[dict[str, Any]] = []
    provider_usage_ok = (
        combined_metrics["provider_invoked_units"] < combined_metrics["total_units"]
        and combined_metrics["escalation_rate"] < 0.8
    )
    checks.append(
        {
            "name": "provider_usage",
            "label": "provider usage stayed meaningfully below total units",
            "passed": provider_usage_ok,
            "details": (
                f"provider_invoked_units={combined_metrics['provider_invoked_units']}; "
                f"total_units={combined_metrics['total_units']}; "
                f"escalation_rate={combined_metrics['escalation_rate']}"
            ),
        }
    )
    checks.append(
        {
            "name": "escalation_rate",
            "label": "escalation rate stayed well below all-units provider mode",
            "passed": combined_metrics["escalation_rate"] < 0.8,
            "details": f"escalation_rate={combined_metrics['escalation_rate']}",
        }
    )

    baseline_runtime_passed = None
    baseline_malformed_passed = None
    if baseline_metrics is not None and baseline_metrics.get("elapsed_seconds") is not None and combined_metrics.get("elapsed_seconds") is not None:
        baseline_runtime_passed = combined_metrics["elapsed_seconds"] < baseline_metrics["elapsed_seconds"]
    if baseline_metrics is not None:
        baseline_malformed_passed = (
            combined_metrics["failed_attempts"] < baseline_metrics["failed_attempts"]
            and combined_metrics["malformed_json_count"] < baseline_metrics["malformed_json_count"]
        )
    checks.append(
        {
            "name": "runtime_improvement",
            "label": "runtime improved versus the pre-gating live smoke baseline",
            "passed": baseline_runtime_passed if baseline_runtime_passed is not None else False,
            "details": (
                f"current_elapsed_seconds={combined_metrics.get('elapsed_seconds')}; "
                f"baseline_elapsed_seconds={(baseline_metrics or {}).get('elapsed_seconds')}"
            ),
        }
    )
    checks.append(
        {
            "name": "malformed_reduction",
            "label": "retries and malformed payloads were reduced versus baseline",
            "passed": baseline_malformed_passed if baseline_malformed_passed is not None else False,
            "details": (
                f"current_failed_attempts={combined_metrics['failed_attempts']}; "
                f"baseline_failed_attempts={(baseline_metrics or {}).get('failed_attempts')}; "
                f"current_malformed_json={combined_metrics['malformed_json_count']}; "
                f"baseline_malformed_json={(baseline_metrics or {}).get('malformed_json_count')}"
            ),
        }
    )
    provider_invoked_samples_required = combined_metrics["provider_invoked_units"] > 0
    samples_ok = (
        (bool(sample_sets.get("provider_invoked")) if provider_invoked_samples_required else True)
        and bool(sample_sets.get("provider_skipped"))
        and bool(sample_sets.get("routing"))
    )
    checks.append(
        {
            "name": "summary_and_samples",
            "label": "summaries were written and manual sample sets are available",
            "passed": samples_ok,
            "details": (
                f"provider_invoked_samples={len(sample_sets.get('provider_invoked', []))}; "
                f"provider_invoked_samples_required={provider_invoked_samples_required}; "
                f"provider_skipped_samples={len(sample_sets.get('provider_skipped', []))}; "
                f"routing_samples={len(sample_sets.get('routing', []))}"
            ),
        }
    )

    verdict = "ready for broader post-gating live pilot" if all(item["passed"] for item in checks) else "review gating smoke results before scaling"
    return checks, verdict


def render_sample_section(title: str, rows: list[dict[str, Any]]) -> list[str]:
    lines = ["", f"## {title}", ""]
    if not rows:
        lines.append("- none")
        return lines
    for row in rows:
        lines.append(
            (
                f"- `{row.get('review_unit_id')}` entry=`{row.get('entry_slug')}` "
                f"source=`{row.get('decision_source')}` heuristic_confidence=`{row.get('heuristic_confidence')}` "
                f"provider_invoked=`{row.get('provider_invoked')}` "
                f"provider_skipped_reason=`{row.get('provider_skipped_reason') or '-'}` "
                f"final_provider_status=`{row.get('final_provider_status') or '-'}` "
                f"excerpt=`{row.get('excerpt')}`"
            )
        )
    return lines


def render_report(
    *,
    run_id: str,
    provider: str,
    provider_policy: str,
    model: str | None,
    manifest_path: Path,
    source_site_root: Path,
    pilot_site_root: Path,
    report_dir: Path,
    baseline_report_dir: Path | None,
    f2_summary: dict[str, Any],
    f3_summary: dict[str, Any],
    combined_metrics: dict[str, Any],
    baseline_metrics: dict[str, Any] | None,
    acceptance_checks: list[dict[str, Any]],
    verdict: str,
    sample_sets: dict[str, list[dict[str, Any]]],
) -> str:
    lines = [
        "# Phase H Post-Gating Live Smoke",
        "",
        f"- Run id: `{run_id}`",
        f"- Provider: `{provider}`",
        f"- Provider policy: `{provider_policy}`",
        f"- Model: `{model or '-'}`",
        f"- Manifest: `{manifest_path.resolve()}`",
        f"- Source site root: `{source_site_root.resolve()}`",
        f"- Pilot site root: `{pilot_site_root}`",
        f"- Report dir: `{report_dir}`",
        f"- Baseline report dir: `{baseline_report_dir}`" if baseline_report_dir is not None else "- Baseline report dir: `-`",
        "",
        "## Stage Results",
        "",
        (
            f"- F2 status: `{f2_summary.get('status')}` total=`{f2_summary.get('total_units', 0)}` "
            f"provider_invoked=`{f2_summary.get('provider_invoked_units', 0)}` "
            f"escalation_rate=`{f2_summary.get('escalation_rate', 0)}` "
            f"malformed_json=`{f2_summary.get('malformed_json_count', 0)}` "
            f"failed_attempts=`{f2_summary.get('gemini_failed_attempt_count', 0)}`"
        ),
        (
            f"- F3 status: `{f3_summary.get('status')}` total=`{f3_summary.get('total_units', 0)}` "
            f"provider_invoked=`{f3_summary.get('provider_invoked_units', 0)}` "
            f"escalation_rate=`{f3_summary.get('escalation_rate', 0)}` "
            f"malformed_json=`{f3_summary.get('malformed_json_count', 0)}` "
            f"failed_attempts=`{f3_summary.get('gemini_failed_attempt_count', 0)}`"
        ),
        "",
        "## Combined Metrics",
        "",
        f"- total_units: `{combined_metrics['total_units']}`",
        f"- provider_eligible_units: `{combined_metrics['provider_eligible_units']}`",
        f"- provider_invoked_units: `{combined_metrics['provider_invoked_units']}`",
        f"- heuristic_only_units: `{combined_metrics['heuristic_only_units']}`",
        f"- provider_skip_count: `{combined_metrics['provider_skip_count']}`",
        f"- escalation_rate: `{combined_metrics['escalation_rate']}`",
        f"- malformed_json_count: `{combined_metrics['malformed_json_count']}`",
        f"- failed_attempts: `{combined_metrics['failed_attempts']}`",
        f"- elapsed_seconds: `{combined_metrics['elapsed_seconds']}`",
    ]
    if baseline_metrics is not None:
        lines.extend(
            [
                "",
                "## Baseline Comparison",
                "",
                f"- baseline_total_units: `{baseline_metrics['total_units']}`",
                f"- baseline_provider_invoked_units: `{baseline_metrics['provider_invoked_units']}`",
                f"- baseline_escalation_rate: `{baseline_metrics['escalation_rate']}`",
                f"- baseline_malformed_json_count: `{baseline_metrics['malformed_json_count']}`",
                f"- baseline_failed_attempts: `{baseline_metrics['failed_attempts']}`",
                f"- baseline_elapsed_seconds: `{baseline_metrics['elapsed_seconds']}`",
            ]
        )

    lines.extend(["", "## Acceptance Checks", ""])
    for check in acceptance_checks:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- [{status}] `{check['name']}` {check['label']}")
        lines.append(f"  {check['details']}")

    lines.extend(["", "## Verdict", "", f"- `{verdict}`"])
    lines.extend(render_sample_section("Provider-Invoked Samples", sample_sets["provider_invoked"]))
    lines.extend(render_sample_section("Provider-Skipped Samples", sample_sets["provider_skipped"]))
    lines.extend(render_sample_section("Routing Samples", sample_sets["routing"]))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase H post-gating live smoke for F2/F3.")
    parser.add_argument("--source-site-root", type=Path, default=DEFAULT_SOURCE_SITE_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--provider", choices=["gemini", "heuristic"], default=DEFAULT_PROVIDER)
    parser.add_argument("--provider-policy", choices=["heuristic_only", "provider_all", "provider_uncertain_only"], default=DEFAULT_PROVIDER_POLICY)
    parser.add_argument("--model", default=DEFAULT_GEMINI_MODEL)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--site-copy-parent", type=Path, default=DEFAULT_SITE_COPY_PARENT)
    parser.add_argument("--baseline-report-dir", type=Path, default=None)
    args = parser.parse_args()

    require_provider_credentials(args.provider)
    run_id = timestamp_slug()
    report_dir = (args.report_root.resolve() / run_id).resolve()
    stage_log_dir = ensure_dir(report_dir / "stage_logs")
    f2_report_dir = report_dir / "f2"
    f3_report_dir = report_dir / "f3"
    pilot_site_root = (args.site_copy_parent.resolve() / f"phase-h-{run_id}").resolve()
    baseline_report_dir = detect_baseline_report_dir(args.baseline_report_dir)

    ensure_dir(report_dir)
    console_status(f"[phase-h] run_id={run_id}")
    console_status(f"[phase-h] provider={args.provider} provider_policy={args.provider_policy} model={args.model if args.provider == 'gemini' else '-'}")
    console_status(f"[phase-h] manifest={args.manifest.resolve()}")
    console_status(f"[phase-h] report_dir={report_dir}")
    console_status(f"[phase-h] pilot_site_root={pilot_site_root}")
    if baseline_report_dir is not None:
        console_status(f"[phase-h] baseline_report_dir={baseline_report_dir}")

    copy_site_root(source=args.source_site_root, destination=pilot_site_root)

    f2_command = [
        sys.executable,
        str(F2_SCRIPT),
        "--site-root",
        str(pilot_site_root),
        "--manifest",
        str(args.manifest.resolve()),
        "--provider",
        args.provider,
        "--provider-policy",
        args.provider_policy,
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
        "--provider-policy",
        args.provider_policy,
        "--report-dir",
        str(f3_report_dir),
        "--strict",
        "--quiet",
    ]
    if args.provider == "gemini":
        f3_command.extend(["--model", args.model])
    run_command(stage_name="f3", command=f3_command, workdir=CODE_ROOT, log_dir=stage_log_dir)

    f2_summary = read_json(f2_report_dir / F2_SUMMARY_ARTIFACT)
    f3_summary = read_json(f3_report_dir / F3_SUMMARY_ARTIFACT)
    f2_entries = read_json(f2_report_dir / F2_ENTRIES_ARTIFACT)
    f3_entries = read_json(f3_report_dir / F3_ENTRIES_ARTIFACT)

    f2_rows = flatten_f2_rows(f2_entries)
    f3_rows = flatten_f3_rows(f3_entries)

    f2_metrics = extract_metrics(f2_summary)
    f3_metrics = extract_metrics(f3_summary)
    combined_metrics = combine_metrics(f2_metrics=f2_metrics, f3_metrics=f3_metrics)

    baseline_metrics = None
    if baseline_report_dir is not None:
        baseline_f2_summary = read_json(baseline_report_dir / "f2" / F2_SUMMARY_ARTIFACT)
        baseline_f3_summary = read_json(baseline_report_dir / "f3" / F3_SUMMARY_ARTIFACT)
        baseline_metrics = combine_metrics(
            f2_metrics=extract_metrics(baseline_f2_summary),
            f3_metrics=extract_metrics(baseline_f3_summary),
        )

    sample_sets = {
        "provider_invoked": sample_rows(
            f2_rows + f3_rows,
            limit=5,
            predicate=lambda row: bool(row.get("provider_invoked")),
            confidence_key="heuristic_confidence",
        ),
        "provider_skipped": sample_rows(
            f2_rows + f3_rows,
            limit=5,
            predicate=lambda row: not bool(row.get("provider_invoked")),
            confidence_key="heuristic_confidence",
        ),
        "routing": sample_rows(
            f3_rows,
            limit=8,
            predicate=lambda row: True,
            confidence_key="heuristic_confidence",
        ),
    }

    acceptance_checks, verdict = build_acceptance_checks(
        combined_metrics=combined_metrics,
        baseline_metrics=baseline_metrics,
        sample_sets=sample_sets,
    )
    report_text = render_report(
        run_id=run_id,
        provider=args.provider,
        provider_policy=args.provider_policy,
        model=(args.model if args.provider == "gemini" else None),
        manifest_path=args.manifest.resolve(),
        source_site_root=args.source_site_root.resolve(),
        pilot_site_root=pilot_site_root,
        report_dir=report_dir,
        baseline_report_dir=baseline_report_dir,
        f2_summary=f2_summary,
        f3_summary=f3_summary,
        combined_metrics=combined_metrics,
        baseline_metrics=baseline_metrics,
        acceptance_checks=acceptance_checks,
        verdict=verdict,
        sample_sets=sample_sets,
    )

    summary_payload = {
        "run_id": run_id,
        "script_version": 1,
        "provider": args.provider,
        "provider_policy": args.provider_policy,
        "model": args.model if args.provider == "gemini" else None,
        "manifest_path": str(args.manifest.resolve()),
        "source_site_root": str(args.source_site_root.resolve()),
        "pilot_site_root": str(pilot_site_root),
        "report_dir": str(report_dir),
        "baseline_report_dir": str(baseline_report_dir) if baseline_report_dir is not None else None,
        "f2_report_dir": str(f2_report_dir),
        "f3_report_dir": str(f3_report_dir),
        "f2_summary_path": str((f2_report_dir / F2_SUMMARY_ARTIFACT).resolve()),
        "f3_summary_path": str((f3_report_dir / F3_SUMMARY_ARTIFACT).resolve()),
        "combined_metrics": combined_metrics,
        "baseline_metrics": baseline_metrics,
        "acceptance_checks": acceptance_checks,
        "verdict": verdict,
        "sample_sets": sample_sets,
    }
    safe_json_write(report_dir / "phase_h_post_gating_smoke_summary.json", summary_payload)
    atomic_write_text(report_dir / "PHASE_H_POST_GATING_SMOKE_REPORT.md", report_text)
    console_status(f"[phase-h] completed. summary={report_dir / 'phase_h_post_gating_smoke_summary.json'}")
    console_status(f"[phase-h] report={report_dir / 'PHASE_H_POST_GATING_SMOKE_REPORT.md'}")


if __name__ == "__main__":
    main()
