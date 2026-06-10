from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from common import CODE_ROOT, DEFAULT_TOOLS_REPORTS_ROOT, log, timestamp_slug
from pipeline_utils import ensure_dir, read_json, write_json, write_text
from workspace_paths import get_work_site_root


TOOLS_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = TOOLS_DIR / "knowledge_flow_waves" / "level1.full-production-pilot.json"
DEFAULT_REPORT_ROOT = DEFAULT_TOOLS_REPORTS_ROOT / "level1_product_closure"
DEFAULT_GOLDSET = TOOLS_DIR / "data" / "level1_boundary_goldset.json"
PHASE_H_SCRIPT = TOOLS_DIR / "run_phase_h_post_gating_smoke.py"
GOLDSET_VALIDATOR = TOOLS_DIR / "validate_level1_boundary_goldset.py"
APPLY_ENGINE = TOOLS_DIR / "content_apply_engine.py"
AUDIT_SPARSE = TOOLS_DIR / "audit_sparse_entries.py"
AUDIT_FLOW = TOOLS_DIR / "audit_knowledge_flow.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the full level1 product-closure workflow.")
    parser.add_argument("--source-site-root", type=Path, default=get_work_site_root())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--provider", choices=["gemini", "heuristic"], default="gemini")
    parser.add_argument("--provider-policy", choices=["heuristic_only", "provider_all", "provider_uncertain_only"], default="provider_uncertain_only")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--goldset", type=Path, default=DEFAULT_GOLDSET)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--quiet", action="store_true")
    return parser


def run_command(*, command: list[str], quiet: bool) -> None:
    log("[exec] " + " ".join(command), quiet=quiet)
    completed = subprocess.run(command, cwd=CODE_ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {' '.join(command)}")


def newest_report_dir(root: Path) -> Path:
    candidates = [item for item in root.iterdir() if item.is_dir()]
    if not candidates:
        raise RuntimeError(f"No report directories were created under {root}")
    return sorted(candidates)[-1]


def copy_artifact(path: Path, target_dir: Path) -> None:
    if path.exists():
        shutil.copy2(path, target_dir / path.name)


def render_final_report(
    *,
    closure_dir: Path,
    phase_h_summary: dict[str, Any],
    f2_summary: dict[str, Any],
    f3_summary: dict[str, Any],
    goldset_summary: dict[str, Any],
    apply_plan_summary: dict[str, Any],
    apply_safe_summary: dict[str, Any],
    sparse_summary: dict[str, Any],
    flow_summary: dict[str, Any],
) -> str:
    lines = [
        "# Level1 Product Closure Report",
        "",
        f"- Closure dir: `{closure_dir}`",
        f"- Phase H verdict: `{phase_h_summary.get('verdict')}`",
        f"- Goldset status: `{goldset_summary.get('status')}`",
        f"- Goldset exact matches: `{goldset_summary.get('exact_match_count')}/{goldset_summary.get('entry_count')}`",
        f"- F2 provider_invoked_units: `{f2_summary.get('provider_invoked_units')}`",
        f"- F2 malformed_json_count: `{f2_summary.get('malformed_json_count')}`",
        f"- F3 provider_invoked_units: `{f3_summary.get('provider_invoked_units')}`",
        f"- F3 routing_conflict_count: `{f3_summary.get('routing_conflict_count')}`",
        f"- Apply plan status: `{apply_plan_summary.get('status')}`",
        f"- Apply-safe status: `{apply_safe_summary.get('status')}`",
        f"- Sparse audit status: `{sparse_summary.get('status')}`",
        f"- Knowledge-flow audit status: `{flow_summary.get('status')}`",
        "",
        "## Key Outputs",
        "",
        f"- [phase_h_post_gating_smoke_summary.json]({closure_dir / 'phase_h_post_gating_smoke_summary.json'})",
        f"- [semantic_purity_summary.json]({closure_dir / 'semantic_purity_summary.json'})",
        f"- [content_routing_summary.json]({closure_dir / 'content_routing_summary.json'})",
        f"- [level1_boundary_goldset_summary.json]({closure_dir / 'level1_boundary_goldset_summary.json'})",
        f"- [content_apply_plan_summary.json]({closure_dir / 'content_apply_plan_summary.json'})",
        f"- [content_apply_safe_summary.json]({closure_dir / 'content_apply_safe_summary.json'})",
        f"- [audit_sparse_summary.json]({closure_dir / 'audit_sparse_summary.json'})",
        f"- [knowledge_flow_summary.json]({closure_dir / 'knowledge_flow_summary.json'})",
        "",
    ]
    return "\n".join(str(line) for line in lines)


def main() -> None:
    args = build_parser().parse_args()
    run_id = timestamp_slug()
    closure_dir = ensure_dir(args.report_root.resolve() / run_id)
    phase_h_root = ensure_dir(closure_dir / "phase_h_runs")

    phase_h_command = [
        sys.executable,
        str(PHASE_H_SCRIPT),
        "--source-site-root",
        str(args.source_site_root.resolve()),
        "--manifest",
        str(args.manifest.resolve()),
        "--provider",
        args.provider,
        "--provider-policy",
        args.provider_policy,
        "--report-root",
        str(phase_h_root),
    ]
    if args.provider == "gemini":
        phase_h_command.extend(["--model", args.model])
    run_command(command=phase_h_command, quiet=args.quiet)

    phase_h_report_dir = newest_report_dir(phase_h_root)
    phase_h_summary = read_json(phase_h_report_dir / "phase_h_post_gating_smoke_summary.json")
    f2_summary = read_json(phase_h_report_dir / "f2" / "semantic_purity_summary.json")
    f3_summary = read_json(phase_h_report_dir / "f3" / "content_routing_summary.json")

    copy_artifact(phase_h_report_dir / "phase_h_post_gating_smoke_summary.json", closure_dir)
    copy_artifact(phase_h_report_dir / "f2" / "semantic_purity_summary.json", closure_dir)
    copy_artifact(phase_h_report_dir / "f3" / "content_routing_summary.json", closure_dir)

    goldset_report_dir = ensure_dir(closure_dir / "boundary_validation")
    run_command(
        command=[
            sys.executable,
            str(GOLDSET_VALIDATOR),
            "--phase-h-report-dir",
            str(phase_h_report_dir),
            "--goldset",
            str(args.goldset.resolve()),
            "--report-dir",
            str(goldset_report_dir),
        ],
        quiet=args.quiet,
    )
    goldset_summary = read_json(goldset_report_dir / "level1_boundary_goldset_summary.json")
    copy_artifact(goldset_report_dir / "level1_boundary_goldset_summary.json", closure_dir)
    copy_artifact(goldset_report_dir / "level1_boundary_goldset_findings.json", closure_dir)
    copy_artifact(goldset_report_dir / "level1_boundary_goldset_report.md", closure_dir)

    apply_plan_dir = ensure_dir(closure_dir / "content_apply_plan")
    run_command(
        command=[
            sys.executable,
            str(APPLY_ENGINE),
            "--f3-report-dir",
            str((phase_h_report_dir / "f3").resolve()),
            "--mode",
            "plan",
            "--report-dir",
            str(apply_plan_dir),
        ],
        quiet=args.quiet,
    )
    apply_plan_summary = read_json(apply_plan_dir / "content_apply_summary.json")
    if (apply_plan_dir / "content_apply_report.md").exists():
        shutil.copy2(apply_plan_dir / "content_apply_report.md", closure_dir / "content_apply_plan_report.md")
    shutil.copy2(apply_plan_dir / "content_apply_summary.json", closure_dir / "content_apply_plan_summary.json")

    apply_safe_dir = ensure_dir(closure_dir / "content_apply_safe")
    run_command(
        command=[
            sys.executable,
            str(APPLY_ENGINE),
            "--f3-report-dir",
            str((phase_h_report_dir / "f3").resolve()),
            "--mode",
            "apply-safe",
            "--report-dir",
            str(apply_safe_dir),
        ],
        quiet=args.quiet,
    )
    apply_safe_summary = read_json(apply_safe_dir / "content_apply_summary.json")
    shutil.copy2(apply_safe_dir / "content_apply_summary.json", closure_dir / "content_apply_safe_summary.json")
    if (apply_safe_dir / "content_apply_report.md").exists():
        shutil.copy2(apply_safe_dir / "content_apply_report.md", closure_dir / "content_apply_safe_report.md")

    site_root = Path(str(apply_safe_summary.get("site_root") or f3_summary.get("site_root") or "")).resolve()
    sparse_dir = ensure_dir(closure_dir / "audit_sparse")
    run_command(
        command=[
            sys.executable,
            str(AUDIT_SPARSE),
            "--site-root",
            str(site_root),
            "--degrees",
            "level1",
            "--report-dir",
            str(sparse_dir),
        ],
        quiet=args.quiet,
    )
    sparse_summary = read_json(sparse_dir / "audit_sparse_summary.json")
    shutil.copy2(sparse_dir / "audit_sparse_summary.json", closure_dir / "audit_sparse_summary.json")
    if (sparse_dir / "audit_sparse_report.md").exists():
        shutil.copy2(sparse_dir / "audit_sparse_report.md", closure_dir / "audit_sparse_report.md")

    flow_dir = ensure_dir(closure_dir / "audit_knowledge_flow")
    run_command(
        command=[
            sys.executable,
            str(AUDIT_FLOW),
            "--site-root",
            str(site_root),
            "--manifest",
            str(args.manifest.resolve()),
            "--report-dir",
            str(flow_dir),
        ],
        quiet=args.quiet,
    )
    flow_summary = read_json(flow_dir / "knowledge_flow_summary.json")
    shutil.copy2(flow_dir / "knowledge_flow_summary.json", closure_dir / "knowledge_flow_summary.json")
    if (flow_dir / "knowledge_flow_report.md").exists():
        shutil.copy2(flow_dir / "knowledge_flow_report.md", closure_dir / "knowledge_flow_report.md")

    final_summary = {
        "closure_dir": str(closure_dir),
        "phase_h_report_dir": str(phase_h_report_dir),
        "phase_h_verdict": phase_h_summary.get("verdict"),
        "goldset_status": goldset_summary.get("status"),
        "goldset_exact_match_count": goldset_summary.get("exact_match_count"),
        "goldset_entry_count": goldset_summary.get("entry_count"),
        "f2_provider_invoked_units": f2_summary.get("provider_invoked_units"),
        "f3_provider_invoked_units": f3_summary.get("provider_invoked_units"),
        "routing_conflict_count": f3_summary.get("routing_conflict_count"),
        "apply_plan_status": apply_plan_summary.get("status"),
        "apply_safe_status": apply_safe_summary.get("status"),
        "audit_sparse_status": sparse_summary.get("status"),
        "audit_knowledge_flow_status": flow_summary.get("status"),
    }
    write_json(closure_dir / "level1_product_closure_summary.json", final_summary)
    write_text(
        closure_dir / "LEVEL1_PRODUCT_CLOSURE_REPORT.md",
        render_final_report(
            closure_dir=closure_dir,
            phase_h_summary=phase_h_summary,
            f2_summary=f2_summary,
            f3_summary=f3_summary,
            goldset_summary=goldset_summary,
            apply_plan_summary=apply_plan_summary,
            apply_safe_summary=apply_safe_summary,
            sparse_summary=sparse_summary,
            flow_summary=flow_summary,
        ),
    )
    log(f"[done] closure_dir={closure_dir}", quiet=args.quiet)


if __name__ == "__main__":
    main()

