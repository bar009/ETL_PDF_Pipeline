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

from PDF_handle.prod.core.io import ensure_dir, read_json, utc_timestamp, write_json, write_text


DEFAULT_REPORT_ROOT = PDF_HANDLE_ROOT / "runs" / "pre_2_0_go_no_go"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a read-only go/no-go report before an expensive clean 2.0 rerun. "
            "This tool does not run providers, does not run Step 6, and does not mutate site data."
        )
    )
    parser.add_argument(
        "--limited-summary",
        type=Path,
        default=None,
        help="Path to limited_clean_rerun_summary.json. Defaults to the newest one under PDF_handle/runs.",
    )
    parser.add_argument("--run-readiness-report", type=Path, default=None)
    parser.add_argument("--clean-rerun-readiness-report", type=Path, default=None)
    parser.add_argument("--browser-qa-report", type=Path, default=None)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when verdict is no_go.")
    return parser


def latest_limited_summary() -> Path | None:
    candidates = sorted(
        PDF_HANDLE_ROOT.rglob("limited_clean_rerun_summary.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def load_optional_json(path: Path | None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if path is None:
        return None, {"provided": False}
    resolved = path.resolve()
    if not resolved.exists():
        return None, {"provided": True, "path": str(resolved), "exists": False}
    payload = read_json(resolved)
    if not isinstance(payload, dict):
        return None, {"provided": True, "path": str(resolved), "exists": True, "ok": False}
    return payload, {"provided": True, "path": str(resolved), "exists": True, "ok": True}


def add_result(
    results: list[dict[str, Any]],
    *,
    code: str,
    status: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    results.append(
        {
            "code": code,
            "status": status,
            "message": message,
            "details": details or {},
        }
    )


def bool_check(
    results: list[dict[str, Any]],
    *,
    code: str,
    ok: bool,
    fail_status: str,
    pass_message: str,
    fail_message: str,
    details: dict[str, Any] | None = None,
) -> None:
    add_result(
        results,
        code=code,
        status="pass" if ok else fail_status,
        message=pass_message if ok else fail_message,
        details=details,
    )


def check_limited_summary(summary: dict[str, Any] | None, meta: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if summary is None:
        add_result(
            results,
            code="LIMITED_CLEAN_SUMMARY_AVAILABLE",
            status="blocker",
            message="No limited clean rerun summary was found.",
            details=meta,
        )
        return results

    bool_check(
        results,
        code="LIMITED_RUN_COMPLETED",
        ok=summary.get("status") == "completed",
        fail_status="blocker",
        pass_message="Limited clean run completed.",
        fail_message="Limited clean run did not complete.",
        details={"status": summary.get("status")},
    )
    bool_check(
        results,
        code="LIMITED_RUN_DID_NOT_APPLY",
        ok=summary.get("step6_run") is False and summary.get("site_roots_written") is False,
        fail_status="blocker",
        pass_message="Limited validation stayed read-only.",
        fail_message="Limited validation appears to have run Step 6 or written site roots.",
        details={
            "step6_run": summary.get("step6_run"),
            "site_roots_written": summary.get("site_roots_written"),
        },
    )
    bool_check(
        results,
        code="NO_STAGED_CARRYOVER_SUCCESS",
        ok=summary.get("prior_staged_carryover_used_as_success_evidence") is False,
        fail_status="blocker",
        pass_message="Summary says prior staged carryover was not used as success evidence.",
        fail_message="Summary does not prove that prior staged carryover was avoided.",
        details={
            "prior_staged_carryover_used_as_success_evidence": summary.get(
                "prior_staged_carryover_used_as_success_evidence"
            )
        },
    )
    bool_check(
        results,
        code="DISCOVERY_GATE_OK",
        ok=summary.get("gate_ok") is True,
        fail_status="blocker",
        pass_message="Discovery gate reports ok=true.",
        fail_message="Discovery gate is not ok.",
        details={"gate_ok": summary.get("gate_ok")},
    )

    gate_report = summary.get("gate_report") if isinstance(summary.get("gate_report"), dict) else {}
    gates = gate_report.get("gates") if isinstance(gate_report.get("gates"), dict) else {}
    for gate_name in sorted(gates):
        gate = gates.get(gate_name) if isinstance(gates.get(gate_name), dict) else {}
        bool_check(
            results,
            code=f"GATE_{gate_name.upper()}",
            ok=gate.get("ok") is True,
            fail_status="blocker",
            pass_message=f"{gate_name} gate passed.",
            fail_message=f"{gate_name} gate failed.",
            details={"invalid_row_count": gate.get("invalid_row_count"), "examples": gate.get("examples", [])[:5]},
        )

    benchmark = summary.get("benchmark_results") if isinstance(summary.get("benchmark_results"), dict) else {}
    thresholds = summary.get("thresholds") if isinstance(summary.get("thresholds"), dict) else {}
    required_benchmarks = (
        ("tier1_level3", "tier1_level3_required_found", "Tier 1 level3 benchmark"),
        ("tier1_level1", "tier1_level1_required_found", "Tier 1 level1 benchmark"),
    )
    for benchmark_key, threshold_key, label in required_benchmarks:
        data = benchmark.get(benchmark_key) if isinstance(benchmark.get(benchmark_key), dict) else {}
        found = int(data.get("found_count") or 0)
        required = int(thresholds.get(threshold_key) or 0)
        total = int(data.get("total_count") or 0)
        bool_check(
            results,
            code=f"{benchmark_key.upper()}_THRESHOLD",
            ok=required > 0 and found >= required,
            fail_status="blocker",
            pass_message=f"{label} meets the required threshold.",
            fail_message=f"{label} is below the required threshold.",
            details={"found": found, "required": required, "total": total},
        )

    tier2 = benchmark.get("tier2_level2") if isinstance(benchmark.get("tier2_level2"), dict) else {}
    tier2_found = int(tier2.get("found_count") or 0)
    tier2_expected = int(thresholds.get("tier2_level2_expected_found") or 0)
    bool_check(
        results,
        code="TIER2_LEVEL2_EXPECTED_THRESHOLD",
        ok=tier2_expected > 0 and tier2_found >= tier2_expected,
        fail_status="warning",
        pass_message="Tier 2 level2 surfacing meets the expected threshold.",
        fail_message="Tier 2 level2 surfacing is below the expected threshold and needs a documented follow-up.",
        details={"found": tier2_found, "expected": tier2_expected, "total": int(tier2.get("total_count") or 0)},
    )

    acceptance = summary.get("acceptance_gate_metrics") if isinstance(summary.get("acceptance_gate_metrics"), dict) else {}
    bool_check(
        results,
        code="OVERALL_REJECT_RATE_LT_0_60",
        ok=acceptance.get("overall_reject_rate_target_lt_0_60") is True,
        fail_status="blocker",
        pass_message="Overall rejection rate is below the acceptance target.",
        fail_message="Overall rejection rate is above the acceptance target.",
        details={"overall_reject_rate": acceptance.get("overall_reject_rate"), "target": "<0.60"},
    )
    bool_check(
        results,
        code="DUNCAN_FRAGMENTARY_RATE_LT_0_20",
        ok=acceptance.get("duncan_fragmentary_topic_target_lt_0_20") is True,
        fail_status="blocker",
        pass_message="Duncan fragmentary-topic rate is below the acceptance target.",
        fail_message="Duncan fragmentary-topic rate is above the acceptance target.",
        details={"duncan_fragmentary_topic_rate": acceptance.get("duncan_fragmentary_topic_rate"), "target": "<0.20"},
    )
    bool_check(
        results,
        code="COMMENTARY_EXCLUDED_FROM_DISCOVERY",
        ok=acceptance.get("commentary_rows_actual", 0) == 0 and acceptance.get("commentary_candidates_actual", 0) == 0,
        fail_status="blocker",
        pass_message="Commentary-style enrichment source stayed out of discovery.",
        fail_message="Commentary-style enrichment source leaked into discovery outputs.",
        details={
            "commentary_rows_actual": acceptance.get("commentary_rows_actual"),
            "commentary_candidates_actual": acceptance.get("commentary_candidates_actual"),
        },
    )

    other_degree_risks = summary.get("other_degree_risks")
    if not isinstance(other_degree_risks, list):
        other_degree_risks = []
    bool_check(
        results,
        code="NO_OTHER_DEGREE_RISKS",
        ok=len(other_degree_risks) == 0,
        fail_status="blocker",
        pass_message="No non-MM semantic degree leakage risks were reported.",
        fail_message="Non-MM semantic degree leakage risks remain.",
        details={"risk_count": len(other_degree_risks), "examples": other_degree_risks[:8]},
    )

    duncan_misroutes = summary.get("duncan_mm_remaining_misroutes")
    if not isinstance(duncan_misroutes, list):
        duncan_misroutes = []
    bool_check(
        results,
        code="NO_DUNCAN_MM_REMAINING_MISROUTES",
        ok=len(duncan_misroutes) == 0,
        fail_status="blocker",
        pass_message="No Duncan MM section-map misroutes remain in the limited summary.",
        fail_message="Duncan MM section-map misroutes remain.",
        details={"misroute_count": len(duncan_misroutes), "examples": duncan_misroutes[:8]},
    )
    return results


def check_run_readiness(payload: dict[str, Any] | None, meta: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if payload is None:
        add_result(
            results,
            code="RUN_READINESS_REPORT_PROVIDED",
            status="warning",
            message="No run readiness report was provided for this go/no-go report.",
            details=meta,
        )
        return results
    readiness = payload.get("readiness") if isinstance(payload.get("readiness"), dict) else {}
    status = readiness.get("status")
    bool_check(
        results,
        code="RUN_READINESS_NOT_FAILING",
        ok=status in {"pass", "pass_with_warnings"},
        fail_status="blocker",
        pass_message="Run readiness report is not failing.",
        fail_message="Run readiness report is failing.",
        details={"status": status, "blockers": readiness.get("blockers", [])[:10]},
    )
    if status == "pass_with_warnings":
        add_result(
            results,
            code="RUN_READINESS_WARNINGS",
            status="warning",
            message="Run readiness has warnings.",
            details={"warnings": readiness.get("warnings", [])[:10]},
        )
    return results


def check_clean_rerun_readiness(payload: dict[str, Any] | None, meta: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if payload is None:
        add_result(
            results,
            code="CLEAN_RERUN_READINESS_REPORT_PROVIDED",
            status="warning",
            message="No clean rerun readiness report was provided for this go/no-go report.",
            details=meta,
        )
        return results
    status = payload.get("readiness_status")
    bool_check(
        results,
        code="CLEAN_RERUN_ROOT_NOT_BLOCKED",
        ok=status in {"ready", "ready_for_clean_build_but_current_root_is_not_clean"},
        fail_status="blocker",
        pass_message="Clean rerun readiness is not blocked.",
        fail_message="Clean rerun readiness is blocked.",
        details={"readiness_status": status, "readiness_reasons": payload.get("readiness_reasons", [])},
    )
    if status == "ready_for_clean_build_but_current_root_is_not_clean":
        add_result(
            results,
            code="CURRENT_ROOT_NOT_CLEAN",
            status="warning",
            message="The current root is not clean, but the clean-build path may still be usable.",
            details={"readiness_reasons": payload.get("readiness_reasons", [])},
        )
    return results


def check_browser_qa(payload: dict[str, Any] | None, meta: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if payload is None:
        add_result(
            results,
            code="BROWSER_QA_REPORT_PROVIDED",
            status="warning",
            message="No browser QA report was provided. This is acceptable before a rerun, but not for release.",
            details=meta,
        )
        return results
    bool_check(
        results,
        code="BROWSER_QA_PASSING",
        ok=payload.get("status") == "pass",
        fail_status="warning",
        pass_message="Browser QA report is passing.",
        fail_message="Browser QA report is not passing.",
        details={"status": payload.get("status")},
    )
    return results


def compute_verdict(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(result["status"] for result in results)
    if counts.get("blocker", 0):
        verdict = "no_go"
        recommendation = "Do not start the full clean rerun. Fix the blockers first, then rerun this gate."
    elif counts.get("warning", 0):
        verdict = "conditional_go"
        recommendation = "A full rerun is technically unblocked, but warnings should be reviewed before spending provider budget."
    else:
        verdict = "go"
        recommendation = "The available evidence supports starting the full clean rerun."
    return {
        "verdict": verdict,
        "blocker_count": counts.get("blocker", 0),
        "warning_count": counts.get("warning", 0),
        "pass_count": counts.get("pass", 0),
        "recommendation": recommendation,
    }


def render_markdown(report: dict[str, Any]) -> str:
    verdict = report["verdict"]
    lines = [
        "# Pre-2.0 Full Rerun Go/No-Go",
        "",
        f"- Verdict: `{verdict['verdict']}`",
        f"- Blockers: `{verdict['blocker_count']}`",
        f"- Warnings: `{verdict['warning_count']}`",
        f"- Passes: `{verdict['pass_count']}`",
        f"- Recommendation: {verdict['recommendation']}",
        "",
        "## Inputs",
        "",
    ]
    for name, meta in report["inputs"].items():
        lines.append(f"- `{name}`: `{meta.get('path', 'not provided')}`")
    lines.append("")

    grouped: dict[str, list[dict[str, Any]]] = {"blocker": [], "warning": [], "pass": []}
    for result in report["checks"]:
        grouped.setdefault(result["status"], []).append(result)

    for status, heading in (("blocker", "Blockers"), ("warning", "Warnings"), ("pass", "Passing Checks")):
        if not grouped.get(status):
            continue
        lines.append(f"## {heading}")
        lines.append("")
        for result in grouped[status]:
            lines.append(f"- `{result['code']}`: {result['message']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    limited_summary_path = args.limited_summary or latest_limited_summary()
    limited_summary, limited_meta = load_optional_json(limited_summary_path)
    run_readiness, run_readiness_meta = load_optional_json(args.run_readiness_report)
    clean_readiness, clean_readiness_meta = load_optional_json(args.clean_rerun_readiness_report)
    browser_qa, browser_qa_meta = load_optional_json(args.browser_qa_report)

    checks: list[dict[str, Any]] = []
    checks.extend(check_limited_summary(limited_summary, limited_meta))
    checks.extend(check_run_readiness(run_readiness, run_readiness_meta))
    checks.extend(check_clean_rerun_readiness(clean_readiness, clean_readiness_meta))
    checks.extend(check_browser_qa(browser_qa, browser_qa_meta))

    report = {
        "created_at": utc_timestamp(),
        "mode": "read_only",
        "purpose": "pre_2_0_full_rerun_go_no_go",
        "inputs": {
            "limited_summary": limited_meta,
            "run_readiness_report": run_readiness_meta,
            "clean_rerun_readiness_report": clean_readiness_meta,
            "browser_qa_report": browser_qa_meta,
        },
        "checks": checks,
    }
    report["verdict"] = compute_verdict(checks)
    return report


def main() -> None:
    args = build_parser().parse_args()
    output_dir = ensure_dir(
        args.report_dir.resolve()
        if args.report_dir
        else args.report_root.resolve() / utc_timestamp().replace(":", "-")
    )
    report = build_report(args)
    write_json(output_dir / "pre_2_0_go_no_go_report.json", report)
    write_text(output_dir / "pre_2_0_go_no_go_summary.md", render_markdown(report))
    print(
        "[done] pre-2.0 go/no-go "
        f"verdict={report['verdict']['verdict']} "
        f"blockers={report['verdict']['blocker_count']} "
        f"warnings={report['verdict']['warning_count']} "
        f"report={output_dir / 'pre_2_0_go_no_go_report.json'}",
        flush=True,
    )
    if args.strict and report["verdict"]["verdict"] == "no_go":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
