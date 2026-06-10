"""External JS operational lane boundary.

This module is the only prod-owned Python surface that may coordinate the
Node-based smoke/publish/finalize tools.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PDF_handle.prod.core.io import ensure_dir, read_json
from PDF_handle.prod.core.paths import TOOLS_ROOT
from PDF_handle.prod.core.runtime import run_subprocess


PHASE_M7_SMOKE_SCRIPT = TOOLS_ROOT / "validation" / "run_phase_m_7_full_system_smoke.js"
PHASE_M6_PUBLISH_SCRIPT = TOOLS_ROOT / "apply" / "apply_phase_m_6_publish_site_version.js"
PHASE_M11_FINALIZE_SCRIPT = TOOLS_ROOT / "apply" / "apply_phase_m_11_finalize_site_release.js"
PHASE_M9_PLANNING_BUNDLE_SCRIPT = TOOLS_ROOT / "runners" / "run_phase_m_9_post_pdf_full_planning_bundle.ps1"


def run_work_vs_live_smoke(
    *,
    report_dir: Path,
    work_site_root: Path,
    live_site_root: Path,
    quiet: bool,
) -> dict[str, Any]:
    output_path = ensure_dir(report_dir / "phase4_live") / "phase_m_7_full_system_smoke_report_0_4.json"
    command = [
        "node",
        str(PHASE_M7_SMOKE_SCRIPT),
        "--sandbox",
        str(work_site_root.resolve() / "data"),
        "--published",
        str(live_site_root.resolve() / "data"),
        "--output",
        str(output_path),
    ]
    run_subprocess(command, quiet=quiet)
    return {
        "script": str(PHASE_M7_SMOKE_SCRIPT),
        "report_path": str(output_path),
        "report": read_json(output_path),
    }


def run_publish_work_snapshot(
    *,
    report_dir: Path,
    work_site_root: Path,
    quiet: bool,
) -> dict[str, Any]:
    report_path = report_dir / "phase5_publish_work_snapshot_report.json"
    validation_path = report_dir / "phase5_publish_work_snapshot_validation.json"
    command = [
        "node",
        str(PHASE_M6_PUBLISH_SCRIPT),
        "--sandbox-site-root",
        str(work_site_root.resolve()),
        "--report",
        str(report_path),
        "--validation",
        str(validation_path),
    ]
    run_subprocess(command, quiet=quiet)
    return {
        "script": str(PHASE_M6_PUBLISH_SCRIPT),
        "report_path": str(report_path),
        "validation_path": str(validation_path),
        "report": read_json(report_path),
        "validation": read_json(validation_path),
    }


def run_finalize_live_release(
    *,
    report_dir: Path,
    live_site_root: Path,
    quiet: bool,
) -> dict[str, Any]:
    report_path = report_dir / "phase5_finalize_live_release_report.json"
    validation_path = report_dir / "phase5_finalize_live_release_validation.json"
    smoke_path = report_dir / "phase5_finalize_expected_smoke.json"
    command = [
        "node",
        str(PHASE_M11_FINALIZE_SCRIPT),
        "--source-site-root",
        str(live_site_root.resolve()),
        "--report",
        str(report_path),
        "--validation",
        str(validation_path),
        "--smoke-report",
        str(smoke_path),
    ]
    run_subprocess(command, quiet=quiet)
    return {
        "script": str(PHASE_M11_FINALIZE_SCRIPT),
        "report_path": str(report_path),
        "validation_path": str(validation_path),
        "smoke_path": str(smoke_path),
        "report": read_json(report_path),
        "validation": read_json(validation_path),
    }


def run_post_pdf_planning_bundle(
    *,
    report_dir: Path,
    work_site_root: Path,
    live_site_root: Path,
    notebooklm_intake: Path,
    future_entry_root: Path,
    quiet: bool,
) -> dict[str, Any]:
    # This is explicit external follow-through, not canonical ETL mutation.
    # It should only run after the staged repair path has already crossed its review gate.
    bundle_dir = ensure_dir(report_dir / "phase6_post_pdf_enrichment")
    bundle_report_path = bundle_dir / "phase_m_9_post_pdf_full_planning_bundle_report.json"
    bundle_summary_path = bundle_dir / "phase_m_9_post_pdf_full_planning_bundle_summary.md"
    command = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(PHASE_M9_PLANNING_BUNDLE_SCRIPT),
        "-SandboxSiteRoot",
        str(work_site_root.resolve()),
        "-PublishedSiteRoot",
        str(live_site_root.resolve()),
        "-Level1Path",
        str((live_site_root.resolve() / "data" / "level1.json")),
        "-Level2Path",
        str((live_site_root.resolve() / "data" / "level2.json")),
        "-LibraryPath",
        str((live_site_root.resolve() / "data" / "library.json")),
        "-NotebooklmIntake",
        str(notebooklm_intake.resolve()),
        "-FutureEntryRoot",
        str(future_entry_root.resolve()),
        "-BundleDir",
        str(bundle_dir),
    ]
    run_subprocess(command, quiet=quiet)
    return {
        "script": str(PHASE_M9_PLANNING_BUNDLE_SCRIPT),
        "bundle_dir": str(bundle_dir),
        "report_path": str(bundle_report_path),
        "summary_path": str(bundle_summary_path),
        "report": read_json(bundle_report_path),
    }
