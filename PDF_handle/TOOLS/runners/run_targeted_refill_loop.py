from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from common import PDF_HANDLE_ROOT, log, resolve_report_dir, site_label
from pipeline_utils import read_json, utc_timestamp, write_json


TOOLS_DIR = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = TOOLS_DIR / "audit_sparse_entries.py"
REFILL_SCRIPT = TOOLS_DIR / "targeted_refill_from_audit.py"
STEP6_SCRIPT = PDF_HANDLE_ROOT / "step_06_apply_reviewed_merge.py"
STEP7_SCRIPT = PDF_HANDLE_ROOT / "step_07_site_qa.py"
DEFAULT_AUDIT_ROOT = TOOLS_DIR / "reports" / "audit_sparse_entries"
DEFAULT_REFILL_ROOT = TOOLS_DIR / "reports" / "targeted_refill_from_audit"
DEFAULT_LOOP_ROOT = TOOLS_DIR / "reports" / "run_targeted_refill_loop"
DEFAULT_BATCH_SIZE = 5
DEFAULT_CLASSIFICATION_SPEC = "seed_only,sparse"
BLOCKED_REFILL_STATUSES = {
    "manual_review",
    "insufficient_evidence",
    "missing_target",
    "skipped_existing_marker",
    "skipped_already_present",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run targeted refill in automatic batches, then merge and QA after each successful batch."
    )
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--degree", choices=["level1", "level2", "all"], default="level1")
    parser.add_argument("--classification", default=DEFAULT_CLASSIFICATION_SPEC)
    parser.add_argument("--provider", choices=["gemini", "heuristic"], default="gemini")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-batches", type=int, default=None)
    parser.add_argument("--audit-root", type=Path, default=DEFAULT_AUDIT_ROOT)
    parser.add_argument("--refill-root", type=Path, default=DEFAULT_REFILL_ROOT)
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument(
        "--include-prior-manual-review",
        action="store_true",
        help="Retry slugs that previous refill runs already marked manual_review/insufficient_evidence.",
    )
    parser.add_argument("--qa-mode", choices=["full", "data", "browser"], default="full")
    parser.add_argument("--quiet", action="store_true")
    return parser


def parse_classifications(spec: str) -> set[str]:
    return {item.strip() for item in spec.split(",") if item.strip()}


def target_key(item: dict[str, Any]) -> str:
    return f"{item['degree']}::{item['slug']}"


def run_command(command: list[str], *, quiet: bool) -> subprocess.CompletedProcess[str]:
    if not quiet:
        print("[exec] " + " ".join(command), flush=True)
    return subprocess.run(command, check=False, text=True)


def load_queue(queue_file: Path) -> list[dict[str, Any]]:
    payload = read_json(queue_file)
    if not isinstance(payload, list):
        raise RuntimeError(f"Queue file is not a JSON array: {queue_file}")
    return payload


def collect_prior_manual_review_keys(
    *,
    refill_root: Path,
    site_root: Path,
    degree_filter: str,
) -> set[str]:
    blocked: set[str] = set()
    search_roots = [
        refill_root.resolve() / site_label(site_root),
        DEFAULT_LOOP_ROOT.resolve() / site_label(site_root),
    ]
    for report_root in search_roots:
        if not report_root.exists():
            continue
        for manifest_path in report_root.rglob("refill_manifest.json"):
            try:
                manifest = read_json(manifest_path)
            except Exception:
                continue
            for row in manifest.get("targets", []):
                degree = str(row.get("degree") or "").strip()
                if degree_filter != "all" and degree != degree_filter:
                    continue
                status = str(row.get("status") or "").strip()
                if status in BLOCKED_REFILL_STATUSES:
                    blocked.add(f"{degree}::{row.get('slug')}")
    return blocked


def select_eligible_targets(
    *,
    queue: list[dict[str, Any]],
    degree_filter: str,
    classifications: set[str],
    blocked_keys: set[str],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for item in queue:
        degree = str(item.get("degree") or "").strip()
        classification = str(item.get("classification") or "").strip()
        key = f"{degree}::{item.get('slug')}"
        if degree_filter != "all" and degree != degree_filter:
            continue
        if classifications and classification not in classifications:
            continue
        if key in blocked_keys:
            continue
        selected.append(item)
    return selected


def run_audit(
    *,
    site_root: Path,
    degree_filter: str,
    audit_dir: Path,
    quiet: bool,
) -> Path:
    command = [
        sys.executable,
        str(AUDIT_SCRIPT),
        "--site-root",
        str(site_root.resolve()),
        "--degrees",
        degree_filter,
        "--report-dir",
        str(audit_dir.resolve()),
    ]
    completed = run_command(command, quiet=quiet)
    if completed.returncode != 0:
        raise RuntimeError(f"audit_sparse_entries failed with exit code {completed.returncode}")
    return audit_dir.resolve()


def build_step6_command(*, site_root: Path, batch_dir: Path) -> list[str]:
    level1_patch = read_json(batch_dir / "level1.patch.json")
    level2_patch = read_json(batch_dir / "level2.patch.json")
    level1_ops = level1_patch.get("operations", [])
    level2_ops = level2_patch.get("operations", [])
    command = [
        sys.executable,
        str(STEP6_SCRIPT),
        "--site-root",
        str(site_root.resolve()),
        "--staging-dir",
        str(batch_dir.resolve()),
        "--apply-live",
    ]
    if level1_ops:
        command.extend(["--approve-level1", "all"])
    if level2_ops:
        command.extend(["--approve-level2", "all"])
    return command


def write_loop_manifest(report_dir: Path, payload: dict[str, Any]) -> None:
    write_json(report_dir / "run_manifest.json", payload)
    latest_path = report_dir.parent / "latest.json"
    write_json(latest_path, payload)


def apply_batch_merge_and_qa(
    *,
    site_root: Path,
    batch_dir: Path,
    qa_mode: str,
    qa_root: Path,
    batch_index: int,
    quiet: bool,
) -> tuple[bool, str | None]:
    step6_command = build_step6_command(site_root=site_root, batch_dir=batch_dir)
    if len(step6_command) <= 6:
        return False, None

    step6_run = run_command(step6_command, quiet=quiet)
    if step6_run.returncode != 0:
        raise RuntimeError(f"Step 6 failed for {batch_dir}")

    qa_dir = qa_root / f"qa-after-batch-{batch_index:02d}"
    step7_command = [
        sys.executable,
        str(STEP7_SCRIPT),
        "--site-root",
        str(site_root),
        "--mode",
        qa_mode,
        "--report-dir",
        str(qa_dir.resolve()),
    ]
    step7_run = run_command(step7_command, quiet=quiet)
    if step7_run.returncode != 0:
        raise RuntimeError(f"Step 7 failed for {batch_dir}")

    return True, str((qa_dir / "qa_run_manifest.json").resolve())


def main() -> None:
    args = build_parser().parse_args()
    site_root = args.site_root.resolve()
    report_dir = resolve_report_dir(
        tool_name="run_targeted_refill_loop",
        report_dir=args.report_dir.resolve() if args.report_dir else None,
        site_root=site_root,
    )
    batch_root = report_dir / "batches"
    batch_root.mkdir(parents=True, exist_ok=True)
    audit_root = report_dir / "audits"
    audit_root.mkdir(parents=True, exist_ok=True)
    qa_root = report_dir / "qa"
    qa_root.mkdir(parents=True, exist_ok=True)

    classifications = parse_classifications(args.classification)
    blocked_keys = (
        set()
        if args.include_prior_manual_review
        else collect_prior_manual_review_keys(
            refill_root=args.refill_root.resolve(),
            site_root=site_root,
            degree_filter=args.degree,
        )
    )

    manifest: dict[str, Any] = {
        "created_at": utc_timestamp(),
        "tool": "run_targeted_refill_loop",
        "site_root": str(site_root),
        "provider": args.provider,
        "model": args.model if args.provider == "gemini" else None,
        "degree": args.degree,
        "classification": args.classification,
        "batch_size": args.batch_size,
        "max_batches": args.max_batches,
        "qa_mode": args.qa_mode,
        "include_prior_manual_review": args.include_prior_manual_review,
        "initial_blocked_count": len(blocked_keys),
        "status": "running",
        "batches": [],
        "latest_audit_dir": None,
        "remaining_eligible_count": None,
        "interrupted": None,
    }
    write_loop_manifest(report_dir, manifest)

    batch_index = 1
    current_queue: list[dict[str, Any]] = []
    while True:
        if args.max_batches is not None and batch_index > args.max_batches:
            manifest["status"] = "stopped_max_batches"
            break

        audit_dir = audit_root / f"audit-after-batch-{batch_index - 1:02d}"
        run_audit(site_root=site_root, degree_filter=args.degree, audit_dir=audit_dir, quiet=args.quiet)
        manifest["latest_audit_dir"] = str(audit_dir.resolve())
        current_queue = load_queue(audit_dir / "audit_sparse_refill_queue.json")
        eligible = select_eligible_targets(
            queue=current_queue,
            degree_filter=args.degree,
            classifications=classifications,
            blocked_keys=blocked_keys,
        )
        manifest["remaining_eligible_count"] = len(eligible)
        write_loop_manifest(report_dir, manifest)

        if not eligible:
            manifest["status"] = "completed"
            break

        batch_items = eligible[: args.batch_size]
        batch_slugs = [str(item["slug"]) for item in batch_items]
        batch_dir = batch_root / f"batch-{batch_index:02d}"
        refill_command = [
            sys.executable,
            str(REFILL_SCRIPT),
            "--site-root",
            str(site_root),
            "--audit-dir",
            str(audit_dir.resolve()),
            "--degree",
            args.degree,
            "--classification",
            args.classification,
            "--provider",
            args.provider,
            "--staging-dir",
            str(batch_dir.resolve()),
        ]
        if args.provider == "gemini":
            refill_command.extend(["--model", args.model])
        for slug in batch_slugs:
            refill_command.extend(["--slug", slug])

        log(
            f"[loop] batch {batch_index} targets={','.join(batch_slugs)}",
            quiet=args.quiet,
        )
        refill_run = run_command(refill_command, quiet=args.quiet)
        run_status_path = batch_dir / "run_status.json"
        if not run_status_path.exists():
            raise RuntimeError(f"Refill run did not produce run_status.json: {run_status_path}")
        refill_status = read_json(run_status_path)
        refill_manifest = read_json(batch_dir / "refill_manifest.json")
        target_rows = refill_manifest.get("targets", [])

        batch_record: dict[str, Any] = {
            "batch_index": batch_index,
            "staging_dir": str(batch_dir.resolve()),
            "selected_slugs": batch_slugs,
            "refill_exit_code": refill_run.returncode,
            "refill_status": refill_status.get("status"),
            "operation_count": int(refill_status.get("operation_count") or 0),
            "completed_count": int(refill_status.get("completed_count") or 0),
            "manual_review_count": int(refill_status.get("manual_review_count") or 0),
            "step6_applied": False,
            "step6_report": None,
            "qa_report": None,
        }

        for row in target_rows:
            status = str(row.get("status") or "").strip()
            if status in BLOCKED_REFILL_STATUSES:
                blocked_keys.add(target_key(row))

        if batch_record["operation_count"] > 0:
            applied, qa_report = apply_batch_merge_and_qa(
                site_root=site_root,
                batch_dir=batch_dir,
                qa_mode=args.qa_mode,
                qa_root=qa_root,
                batch_index=batch_index,
                quiet=args.quiet,
            )
            batch_record["step6_applied"] = applied
            batch_record["step6_report"] = str((batch_dir / "step6_merge_report.json").resolve()) if applied else None
            batch_record["qa_report"] = qa_report

        if str(refill_status.get("status")) == "interrupted":
            manifest["status"] = "interrupted"
            manifest["interrupted"] = refill_status.get("interrupted")
            manifest["batches"].append(batch_record)
            write_loop_manifest(report_dir, manifest)
            break

        manifest["batches"].append(batch_record)
        write_loop_manifest(report_dir, manifest)
        batch_index += 1

    write_loop_manifest(report_dir, manifest)
    log(
        f"[done] status={manifest['status']} batches={len(manifest['batches'])} remaining={manifest['remaining_eligible_count']} report_dir={report_dir}",
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()

