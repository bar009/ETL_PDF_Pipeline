from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import read_json, read_text, utc_timestamp, write_json


ALLOWED_ACTIONS = {"approve", "reject", "merge_existing", "route_later_degree", "defer"}
ALLOWED_DEGREES = {"level1", "level2", "level3", "unknown"}
LEVEL3_CATEGORIES = {"degree_structure", "hiram_and_raising", "mortality_and_memorial", "symbolic_field"}
CITE_START_RE = re.compile(r"\[cite_start\]")
JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE | re.MULTILINE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert NotebookLM JSON degree-review responses into a candidate_review_decisions file. "
            "This is report-only and does not publish or mutate site data."
        )
    )
    parser.add_argument("--template-file", type=Path, required=True)
    parser.add_argument("--response-file", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewer", default="notebooklm-assisted-review")
    parser.add_argument("--strict", action="store_true")
    return parser


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def read_notebooklm_json(path: Path) -> Any:
    raw = read_text(path.resolve())
    candidates = [
        raw,
        CITE_START_RE.sub("", raw),
        JSON_FENCE_RE.sub("", CITE_START_RE.sub("", raw)).strip(),
    ]
    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
    raise SystemExit(f"Could not parse NotebookLM JSON response {path}: {last_error}") from last_error


def load_response_items(path: Path) -> list[dict[str, Any]]:
    payload = read_notebooklm_json(path.resolve())
    if isinstance(payload, dict) and isinstance(payload.get("decisions"), list):
        payload = payload["decisions"]
    if not isinstance(payload, list):
        raise SystemExit(f"NotebookLM response must be a JSON array or {{decisions: [...]}}: {path}")
    return [item for item in payload if isinstance(item, dict)]


def coerce_action(value: Any) -> str:
    action = normalize_text(value)
    return action if action in ALLOWED_ACTIONS else "defer"


def coerce_degree(value: Any, fallback: str) -> str:
    degree = normalize_text(value)
    if degree in ALLOWED_DEGREES:
        return degree
    return fallback if fallback in ALLOWED_DEGREES else "unknown"


def coerce_level3_category(value: Any) -> str:
    category = normalize_text(value)
    return category if category in LEVEL3_CATEGORIES else ""


def build_review_reason(item: dict[str, Any]) -> str:
    parts = []
    reason = normalize_text(item.get("reason"))
    evidence = normalize_text(item.get("evidence"))
    confidence = normalize_text(item.get("confidence"))
    canonicality = normalize_text(item.get("canonicality"))
    native_vs_mentioned = normalize_text(item.get("native_vs_mentioned"))
    if reason:
        parts.append(reason)
    if evidence:
        parts.append(f"Evidence: {evidence}")
    metadata = ", ".join(
        value
        for value in (
            f"confidence={confidence}" if confidence else "",
            f"canonicality={canonicality}" if canonicality else "",
            f"native_vs_mentioned={native_vs_mentioned}" if native_vs_mentioned else "",
        )
        if value
    )
    if metadata:
        parts.append(metadata)
    return " | ".join(parts)


def main() -> None:
    args = build_parser().parse_args()
    template = read_json(args.template_file.resolve())
    decisions = template.get("decisions") if isinstance(template, dict) else []
    if not isinstance(decisions, list):
        raise SystemExit("Template file must contain a decisions array.")

    response_by_id: dict[str, dict[str, Any]] = {}
    duplicate_ids: list[str] = []
    for response_file in args.response_file:
        for item in load_response_items(response_file):
            candidate_id = normalize_text(item.get("candidate_id"))
            if not candidate_id:
                continue
            if candidate_id in response_by_id:
                duplicate_ids.append(candidate_id)
            response_by_id[candidate_id] = item

    template_ids = {normalize_text(item.get("candidate_id")) for item in decisions if isinstance(item, dict)}
    unknown_response_ids = sorted(set(response_by_id) - template_ids)
    matched_count = 0

    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        candidate_id = normalize_text(decision.get("candidate_id"))
        response = response_by_id.get(candidate_id)
        if not response:
            continue
        matched_count += 1
        action = coerce_action(response.get("recommended_action"))
        fallback_degree = normalize_text(decision.get("candidate_degree")) or "unknown"
        approved_degree = coerce_degree(response.get("recommended_degree"), fallback_degree)
        decision["review_action"] = action
        decision["approved_degree"] = approved_degree
        decision["approved_category"] = (
            coerce_level3_category(response.get("recommended_level3_category"))
            if approved_degree == "level3"
            else ""
        )
        decision["approved_title"] = normalize_text(response.get("approved_title")) or normalize_text(decision.get("approved_title"))
        decision["review_reason"] = build_review_reason(response)
        decision["notebooklm_recommendation"] = {
            "recommended_action": response.get("recommended_action"),
            "recommended_degree": response.get("recommended_degree"),
            "recommended_level3_category": response.get("recommended_level3_category"),
            "canonicality": response.get("canonicality"),
            "native_vs_mentioned": response.get("native_vs_mentioned"),
            "confidence": response.get("confidence"),
        }

    template["reviewer"] = args.reviewer
    template["reviewed_at"] = utc_timestamp()
    template["conversion_report"] = {
        "response_files": [str(path.resolve()) for path in args.response_file],
        "template_decision_count": len([item for item in decisions if isinstance(item, dict)]),
        "response_count": len(response_by_id),
        "matched_count": matched_count,
        "unknown_response_ids": unknown_response_ids,
        "duplicate_response_ids": duplicate_ids,
    }
    write_json(args.output.resolve(), template)

    print(
        "[done] notebooklm responses converted "
        f"matched={matched_count} unknown={len(unknown_response_ids)} output={args.output.resolve()}",
        flush=True,
    )
    if args.strict and (unknown_response_ids or duplicate_ids):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
