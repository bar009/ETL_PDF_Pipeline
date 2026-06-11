from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import ensure_dir, read_json, read_text, utc_timestamp, write_json
from PDF_handle.prod.core.paths import DEFAULT_CONSOLIDATED_DIR, DEFAULT_PROMPTS_DIR
from PDF_handle.prod.core.site_roots import get_live_site_root
from PDF_handle.prod.core.site_data import build_site_data_paths
from PDF_handle.prod.steps.stage_mapping import build_mapping_user_prompt, map_unit_with_gemini
from PDF_handle.prod.steps.stage_support import (
    build_discovery_record,
    build_entry_catalog,
    claim_unique_slug,
    clean_heading_text,
    combine_mapping_results,
    deep_copy_degree,
    extract_sections,
    find_catalog_matches,
    heuristic_extract_mapping,
    normalize_extracted_sections,
    preservation_report,
    render_library_book_summary,
    render_short_summary,
    resolve_target_matches,
    select_candidate_degree,
    select_content_match_targets,
    slugify,
)
from PDF_handle.prod.schema import (
    STAGED_LIBRARY_CATEGORY_ENTRY_SLUG,
    STAGED_LIBRARY_CATEGORY_ID,
    apply_degree_patches,
    build_cross_degree_link,
    build_degree_patch_operation,
    build_source_note,
    normalize_degree_data,
    normalize_entry,
    normalize_nullable_string,
    normalize_string_array,
    normalize_text,
    refresh_degree_indexes,
    serialize_degree_data,
    serialize_entry,
    validate_against_schema,
    validate_degree_references,
)
from PDF_handle.prod.schema.patches import unique_links, unique_strings
from PDF_handle.prod.providers import MalformedProviderPayloadError

BASE_DIR = PDF_HANDLE_ROOT
DEFAULT_STAGING_DIR = BASE_DIR / "staged_injection"
DEFAULT_ROUTING_CONFIG = BASE_DIR / "work_routing.json"
DUNCAN_MM_SECTION_MAP_DEGREE_BLOCKER = "DUNCAN_MM_SECTION_MAP_DEGREE_MISROUTE"
DUNCAN_MM_SECTION_MAP_LEVEL3_TITLES = {
    "master mason: opening, obligation, overview",
    "hiram abiff: legend, murder, burial, and discovery",
    "grand hailing sign: five points of fellowship",
    "monument and weeping virgin: historical account",
    "mm monitor emblems: three steps, beehive, anchor, ark",
}


def today_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def log(message: str, *, quiet: bool) -> None:
    if not quiet:
        encoding = sys.stdout.encoding or "utf-8"
        safe_message = message.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe_message, flush=True)


class QuotaExhaustedError(RuntimeError):
    pass


class RunLimitReachedError(RuntimeError):
    pass


class ServiceUnavailableError(RuntimeError):
    pass


class MappingInterruptedError(RuntimeError):
    pass


def is_quota_exhausted_error(exc: Exception) -> bool:
    text = str(exc).upper()
    status_code = getattr(exc, "status_code", None)
    return status_code == 429 or "RESOURCE_EXHAUSTED" in text or "QUOTA EXCEEDED" in text


def is_service_unavailable_error(exc: Exception) -> bool:
    text = str(exc).upper()
    status_code = getattr(exc, "status_code", None)
    return status_code == 503 or "UNAVAILABLE" in text or "HIGH DEMAND" in text


def build_provider_metrics(
    discovery_rows: list[dict[str, Any]],
    processed_units_total: int,
    gemini_fallback_count: int,
    provider: str,
) -> dict[str, Any]:
    fallback_rows = [row for row in discovery_rows if row.get("provider_fallback") == "heuristic"]
    return {
        "created_at": utc_timestamp(),
        "provider": provider,
        "total_sections": len(discovery_rows),
        "total_units_processed": processed_units_total,
        "gemini_fallback_count": gemini_fallback_count,
        "fallback_section_count": len(fallback_rows),
        "fallback_section_ids": [row.get("section_id") for row in fallback_rows],
    }


def persist_staged_outputs(
    *,
    staging_dir: Path,
    schema_path: Path,
    category_added: bool,
    candidate_library: dict[str, Any],
    base_level1: dict[str, Any],
    base_level2: dict[str, Any],
    base_level3: dict[str, Any] | None,
    library_new_entries: list[dict[str, Any]],
    level1_operations: list[dict[str, Any]],
    level2_operations: list[dict[str, Any]],
    level3_operations: list[dict[str, Any]],
    companion_candidates: list[dict[str, Any]],
    discovery_rows: list[dict[str, Any]],
    work_manifest_rows: list[dict[str, Any]],
    link_rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
    run_status: dict[str, Any],
    provider_metrics: dict[str, Any] | None = None,
) -> None:
    candidate_level1 = apply_degree_patches(deep_copy_degree(base_level1), level1_operations)
    candidate_level2 = apply_degree_patches(deep_copy_degree(base_level2), level2_operations)
    candidate_level3 = apply_degree_patches(deep_copy_degree(base_level3), level3_operations) if base_level3 is not None else None

    library_candidate_payload = serialize_degree_data(candidate_library)
    level1_candidate_payload = serialize_degree_data(candidate_level1)
    level2_candidate_payload = serialize_degree_data(candidate_level2)
    level3_candidate_payload = serialize_degree_data(candidate_level3) if candidate_level3 is not None else None

    write_json(staging_dir / "work_manifest.generated.json", {"created_at": utc_timestamp(), "works": work_manifest_rows})
    write_json(
        staging_dir / "library.patch.json",
        {
            "created_at": utc_timestamp(),
            "degree": "library",
            "category_added": category_added,
            "entries": [
                serialize_entry(candidate_library["entryBySlug"].get(entry["slug"], entry))
                for entry in library_new_entries
            ],
        },
    )
    write_json(staging_dir / "level1.patch.json", {"created_at": utc_timestamp(), "degree": "level1", "operations": level1_operations})
    write_json(staging_dir / "level2.patch.json", {"created_at": utc_timestamp(), "degree": "level2", "operations": level2_operations})
    if base_level3 is not None:
        write_json(staging_dir / "level3.patch.json", {"created_at": utc_timestamp(), "degree": "level3", "operations": level3_operations})
    write_json(staging_dir / "companion_candidates.json", companion_candidates)
    write_json(staging_dir / "discovery_rows.json", discovery_rows)
    write_json(staging_dir / "library.candidate.json", library_candidate_payload)
    write_json(staging_dir / "level1.candidate.json", level1_candidate_payload)
    write_json(staging_dir / "level2.candidate.json", level2_candidate_payload)
    if level3_candidate_payload is not None:
        write_json(staging_dir / "level3.candidate.json", level3_candidate_payload)

    final_reports = {
        "library": validate_against_schema(library_candidate_payload, schema_path),
        "level1": validate_against_schema(level1_candidate_payload, schema_path),
        "level2": validate_against_schema(level2_candidate_payload, schema_path),
    }
    if level3_candidate_payload is not None:
        final_reports["level3"] = validate_against_schema(level3_candidate_payload, schema_path)
    final_reference_report = validate_degree_references(
        {
            "library": normalize_degree_data(library_candidate_payload, "library"),
            "level1": normalize_degree_data(level1_candidate_payload, "level1"),
            "level2": normalize_degree_data(level2_candidate_payload, "level2"),
            **(
                {"level3": normalize_degree_data(level3_candidate_payload, "level3")}
                if level3_candidate_payload is not None
                else {}
            ),
        }
    )

    write_json(
        staging_dir / "validation_report.json",
        {
            "created_at": utc_timestamp(),
            "schema_path": str(schema_path),
            "degrees": final_reports,
            "references": final_reference_report,
            "ok": all(report["ok"] for report in final_reports.values()) and final_reference_report["ok"],
        },
    )
    write_json(staging_dir / "discovery_summary.json", build_discovery_summary(discovery_rows))
    write_json(staging_dir / "discovery_gate_report.json", build_discovery_gate_report(discovery_rows))
    write_json(staging_dir / "link_report.json", {"created_at": utc_timestamp(), "rows": link_rows})
    write_json(staging_dir / "coverage_report.json", {"created_at": utc_timestamp(), "works": coverage_rows})
    if provider_metrics is not None:
        write_json(staging_dir / "provider_metrics.json", provider_metrics)
    write_json(staging_dir / "run_status.json", run_status)


def load_resume_state(
    *,
    staging_dir: Path,
    base_library: dict[str, Any],
) -> dict[str, Any]:
    required_paths = {
        "run_status": staging_dir / "run_status.json",
        "work_manifest": staging_dir / "work_manifest.generated.json",
        "library_candidate": staging_dir / "library.candidate.json",
        "library_patch": staging_dir / "library.patch.json",
        "level1_patch": staging_dir / "level1.patch.json",
        "level2_patch": staging_dir / "level2.patch.json",
        "level3_patch": staging_dir / "level3.patch.json",
        "companion_candidates": staging_dir / "companion_candidates.json",
        "discovery_rows": staging_dir / "discovery_rows.json",
        "link_report": staging_dir / "link_report.json",
        "coverage_report": staging_dir / "coverage_report.json",
    }
    required_names = (
        "run_status",
        "work_manifest",
        "library_candidate",
        "library_patch",
        "level1_patch",
        "level2_patch",
        "companion_candidates",
        "link_report",
        "coverage_report",
    )
    missing = [name for name in required_names if not required_paths[name].exists()]
    if missing:
        raise SystemExit(
            "Cannot resume because staged artifacts are missing: " + ", ".join(missing)
        )

    library_candidate = normalize_degree_data(read_json(required_paths["library_candidate"]), "library")
    library_patch_payload = read_json(required_paths["library_patch"])
    library_new_entries = [
        library_candidate["entryBySlug"][entry["slug"]]
        for entry in library_patch_payload.get("entries", [])
        if entry.get("slug") in library_candidate["entryBySlug"]
    ]
    work_manifest_payload = read_json(required_paths["work_manifest"])
    coverage_payload = read_json(required_paths["coverage_report"])
    link_payload = read_json(required_paths["link_report"])
    run_status = read_json(required_paths["run_status"])

    return {
        "candidate_library": library_candidate,
        "category_added": bool(library_patch_payload.get("category_added")),
        "library_new_entries": library_new_entries,
        "level1_operations": read_json(required_paths["level1_patch"]).get("operations", []),
        "level2_operations": read_json(required_paths["level2_patch"]).get("operations", []),
        "level3_operations": read_json(required_paths["level3_patch"]).get("operations", []) if required_paths["level3_patch"].exists() else [],
        "companion_candidates": read_json(required_paths["companion_candidates"]),
        "discovery_rows": read_json(required_paths["discovery_rows"]) if required_paths["discovery_rows"].exists() else [],
        "work_manifest_rows": work_manifest_payload.get("works", []),
        "coverage_rows": coverage_payload.get("works", []),
        "link_rows": link_payload.get("rows", []),
        "run_status": run_status,
        "completed_work_ids": list(run_status.get("completed_work_ids", [])),
        "processed_units_total": int(run_status.get("processed_units_total", 0)),
        "staged_book_slugs": [
            row["book_slug"]
            for row in work_manifest_payload.get("works", [])
            if row.get("book_slug")
        ],
        "has_partial_work": any(bool(row.get("partial")) for row in work_manifest_payload.get("works", [])),
        "base_library_categories": base_library["categories"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Step 5: map consolidated books into staged library and degree candidate files."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_CONSOLIDATED_DIR)
    parser.add_argument("--staging-dir", type=Path, default=DEFAULT_STAGING_DIR)
    parser.add_argument(
        "--site-root",
        type=Path,
        default=None,
        help="Target site root. Defaults to the configured live root. Individual degree-path flags override it.",
    )
    parser.add_argument("--schema", type=Path, default=None)
    parser.add_argument("--library", type=Path, default=None)
    parser.add_argument("--level1", type=Path, default=None)
    parser.add_argument("--level2", type=Path, default=None)
    parser.add_argument("--level3", type=Path, default=None)
    parser.add_argument("--routing-config", type=Path, default=DEFAULT_ROUTING_CONFIG)
    parser.add_argument("--prompt-file", type=Path, default=DEFAULT_PROMPTS_DIR / "degree_mapper_system.txt")
    parser.add_argument("--provider", choices=["heuristic", "gemini"], default="heuristic")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--api-key-env", default="GEMINI_API_KEY")
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument(
        "--retry-max-delay",
        type=float,
        default=90.0,
        help="Upper bound for exponential backoff delay between retries (seconds).",
    )
    parser.add_argument(
        "--max-fallback-count",
        type=int,
        default=None,
        help="Abort if gemini-to-heuristic fallbacks reach this threshold. None = unlimited.",
    )
    parser.add_argument("--mapping-max-chars", type=int, default=7000)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument("--book", help="Optional source_book_name or work_id.")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a partially completed staged run from existing staged_injection artifacts.",
    )
    parser.add_argument(
        "--max-sections-per-work",
        type=int,
        default=None,
        help="Optional cap for sections processed per work. Useful for smoke tests or low quotas.",
    )
    parser.add_argument(
        "--max-units-total",
        type=int,
        default=None,
        help="Optional cap for total mapping units processed across the run.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output.")
    return parser
def choose_routes(routing_config: dict[str, Any], book_filter: str | None) -> list[dict[str, Any]]:
    works = routing_config.get("works", [])
    if not book_filter:
        return works
    return [
        work
        for work in works
        if work.get("source_book_name") == book_filter or work.get("work_id") == book_filter
    ]


def audit_inputs(input_dir: Path, routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    audited: list[dict[str, Any]] = []
    missing: list[str] = []
    for route in routes:
        book_name = route["source_book_name"]
        markdown_path = input_dir / f"{book_name}.md"
        meta_path = input_dir / f"{book_name}_meta.json"
        if not markdown_path.exists() or not meta_path.exists():
            missing.append(book_name)
            continue
        audited.append(
            {
                "route": route,
                "markdown_path": markdown_path.resolve(),
                "meta_path": meta_path.resolve(),
                "meta": read_json(meta_path),
            }
        )
    if missing:
        raise SystemExit(f"Missing consolidated .md/_meta.json pairs for: {', '.join(missing)}")
    return audited


def ensure_library_import_lane(
    library_data: dict[str, Any],
    routing_config: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    category_cfg = routing_config["library_category"]
    category_added = False
    if STAGED_LIBRARY_CATEGORY_ID not in library_data["categories"]:
        library_data["categories"][STAGED_LIBRARY_CATEGORY_ID] = {
            "id": STAGED_LIBRARY_CATEGORY_ID,
            "title": category_cfg["title"],
            "symbol": category_cfg["symbol"],
            "description": category_cfg.get("description", ""),
            "parent_category": None,
        }
        category_added = True

    if STAGED_LIBRARY_CATEGORY_ENTRY_SLUG not in library_data["entryBySlug"]:
        entry = normalize_entry(
            {
                "title": category_cfg["title"],
                "slug": STAGED_LIBRARY_CATEGORY_ENTRY_SLUG,
                "type": "category",
                "degree": "library",
                "applies_to_degrees": ["library"],
                "category": STAGED_LIBRARY_CATEGORY_ID,
                "parent_topic": None,
                "aliases": [],
                "keywords": ["etl", "pdf", "imports", "library"],
                "related_topics": {"prior": [], "companion": library_companion_targets(library_data), "deeper": []},
                "short_summary": "Landing page for staged ETL imports from consolidated PDF source books.",
                "full_summary": "This staged lane preserves imported source works and their chapter-level archival entries before manual review and merge.",
                "practical_elements": [],
                "symbolic_meaning": "",
                "candidate_lesson": "",
                "tradition_notes": [],
                "caution_notes": [],
                "source_notes": [],
                "language": "en",
                "work_id": None,
                "work_title": "",
                "source_kind": "etl-import-lane",
                "source_path": None,
                "source_anchor": None,
                "source_heading": None,
                "source_order": 1,
                "parallel_entry": None,
                "translation_mode": None,
                "knowledge_links": [],
                "chapter_toc": [],
                "visibility_level": "internal",
                "sensitivity_level": "standard",
                "tradition_scope": "interpretive",
                "status": "draft",
            },
            degree_id="library",
            index=len(library_data["entries"]),
            categories=library_data["categories"],
        )
        library_data["entries"].append(entry)
        refresh_degree_indexes(library_data)
    return library_data, category_added


def library_companion_targets(library_data: dict[str, Any], *extra_slugs: str | None) -> list[str]:
    guide_targets = ["library-guide"] if "library-guide" in library_data.get("entryBySlug", {}) else []
    requested_targets = [slug for slug in extra_slugs if slug]
    return unique_strings([*requested_targets, *guide_targets])


def create_staged_entry(
    dataset: dict[str, Any],
    slug_pool: set[str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    local_payload = dict(payload)
    local_payload["slug"] = claim_unique_slug(local_payload["slug"], slug_pool)
    return normalize_entry(
        local_payload,
        degree_id=dataset["meta"]["degree"],
        index=len(dataset["entries"]),
        categories=dataset["categories"],
    )


def build_discovery_summary(discovery_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_decision: dict[str, int] = {}
    by_unit_kind: dict[str, int] = {}
    by_candidate_degree: dict[str, int] = {}
    for row in discovery_rows:
        decision = str(row.get("decision") or "unknown")
        unit_kind = str(row.get("unit_kind") or "unknown")
        candidate_degree = str(row.get("candidate_degree") or "unknown")
        by_decision[decision] = by_decision.get(decision, 0) + 1
        by_unit_kind[unit_kind] = by_unit_kind.get(unit_kind, 0) + 1
        by_candidate_degree[candidate_degree] = by_candidate_degree.get(candidate_degree, 0) + 1
    return {
        "created_at": utc_timestamp(),
        "total_rows": len(discovery_rows),
        "by_decision": dict(sorted(by_decision.items())),
        "by_unit_kind": dict(sorted(by_unit_kind.items())),
        "by_candidate_degree": dict(sorted(by_candidate_degree.items())),
    }


def build_discovery_gate_report(discovery_rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid_decisions = {"existing_match", "new_canonical_topic", "later_degree_candidate", "reject_or_noise", "encyclopedia_candidate"}

    # Acceptance-health metrics
    total_rows = len(discovery_rows)
    rejected_rows = [row for row in discovery_rows if row.get("decision") == "reject_or_noise"]
    overall_rejection_rate = len(rejected_rows) / max(1, total_rows)
    overall_rejection_rate_fail = total_rows > 0 and overall_rejection_rate >= 0.60
    source_genres = {
        normalize_nullable_string(row.get("source_genre"))
        for row in discovery_rows
        if normalize_nullable_string(row.get("source_genre"))
    }
    enrichment_only_run = bool(source_genres) and source_genres == {"enrichment_source"}
    rows_with_any_match_signal = [
        row
        for row in discovery_rows
        if int(row.get("strong_match_count") or 0) > 0 or int(row.get("medium_match_count") or 0) > 0
    ]
    enrichment_match_signal_rate = len(rows_with_any_match_signal) / max(1, total_rows)
    enrichment_match_signal_ok = (
        enrichment_only_run
        and total_rows > 0
        and enrichment_match_signal_rate >= 0.30
    )
    effective_overall_rejection_rate_fail = overall_rejection_rate_fail and not enrichment_match_signal_ok

    duncan_rows = [row for row in discovery_rows if row.get("work_id") == "duncans-ritual-monitor-1866"]
    duncan_fragmentary_rows = [
        row for row in duncan_rows
        if row.get("unit_kind") in {"fragmentary_topic", "procedural_fragment"}
        and row.get("decision") == "reject_or_noise"
    ]
    duncan_fragmentary_ratio = len(duncan_fragmentary_rows) / max(1, len(duncan_rows))
    duncan_fragmentary_ratio_fail = len(duncan_rows) > 0 and duncan_fragmentary_ratio >= 0.20

    duncan_mm_degree_misroute_rows = [
        {
            **row,
            "blocker_code": DUNCAN_MM_SECTION_MAP_DEGREE_BLOCKER,
            "expected_decision": "later_degree_candidate",
            "expected_candidate_degree": "level3",
            "expected_reason_code": "LATER_DEGREE_SIGNAL",
        }
        for row in discovery_rows
        if row.get("work_id") == "duncans-ritual-monitor-1866"
        and normalize_text(row.get("normalized_title")).lower() in DUNCAN_MM_SECTION_MAP_LEVEL3_TITLES
        and (
            row.get("decision") != "later_degree_candidate"
            or row.get("candidate_degree") != "level3"
            or "LATER_DEGREE_SIGNAL" not in set(row.get("reason_codes") or [])
        )
    ]
    invalid_topic_rows = [
        row for row in discovery_rows
        if row.get("decision") in {"new_canonical_topic", "later_degree_candidate"}
        and row.get("unit_kind") in {"toc", "front_matter", "officer_list", "page_fragment"}
    ]
    invalid_canonical_promotion_rows = [
        row for row in discovery_rows
        if row.get("decision") in {"new_canonical_topic", "later_degree_candidate"}
        and (
            row.get("unit_kind") in {"procedural_fragment", "fragmentary_topic"}
            or bool(
                set(row.get("reason_codes") or []).intersection(
                    {
                        "PROCEDURAL_LEAD",
                        "DIALOGUE_CONTINUATION",
                        "TRUNCATED_TITLE",
                        "SENTENCE_FRAGMENT",
                        "INLINE_CLAUSE_TITLE",
                        "PROCEDURAL_CANONICAL_BLOCK",
                        "FRAGMENTARY_CANONICAL_BLOCK",
                    }
                )
            )
        )
    ]
    invalid_decision_rows = [row for row in discovery_rows if str(row.get("decision") or "") not in valid_decisions]
    invalid_degree_rows = [
        row for row in discovery_rows
        if row.get("decision") not in {"reject_or_noise", "encyclopedia_candidate"}
        and str(row.get("candidate_degree") or "").strip() not in {"level1", "level2", "level3", "unknown"}
    ]
    missing_explainability_rows = [
        row for row in discovery_rows
        if not row.get("reason_codes") or not str(row.get("confidence") or "").strip()
    ]
    return {
        "created_at": utc_timestamp(),
        "ok": not any(
            [
                invalid_topic_rows,
                invalid_canonical_promotion_rows,
                invalid_decision_rows,
                invalid_degree_rows,
                duncan_mm_degree_misroute_rows,
                missing_explainability_rows,
                effective_overall_rejection_rate_fail,
                duncan_fragmentary_ratio_fail,
            ]
        ),
        "gates": {
            "topic_validity": {
                "ok": not invalid_topic_rows,
                "invalid_row_count": len(invalid_topic_rows),
                "examples": invalid_topic_rows[:12],
            },
            "canonical_promotion_validity": {
                "ok": not invalid_canonical_promotion_rows,
                "invalid_row_count": len(invalid_canonical_promotion_rows),
                "examples": invalid_canonical_promotion_rows[:12],
            },
            "decision_validity": {
                "ok": not invalid_decision_rows,
                "invalid_row_count": len(invalid_decision_rows),
                "examples": invalid_decision_rows[:12],
            },
            "degree_validity": {
                "ok": not invalid_degree_rows,
                "invalid_row_count": len(invalid_degree_rows),
                "examples": invalid_degree_rows[:12],
            },
            "duncan_mm_section_map_degree": {
                "ok": not duncan_mm_degree_misroute_rows,
                "invalid_row_count": len(duncan_mm_degree_misroute_rows),
                "blocker_code": DUNCAN_MM_SECTION_MAP_DEGREE_BLOCKER,
                "examples": duncan_mm_degree_misroute_rows[:12],
            },
            "explainability": {
                "ok": not missing_explainability_rows,
                "invalid_row_count": len(missing_explainability_rows),
                "examples": missing_explainability_rows[:12],
            },
            "overall_rejection_rate": {
                "ok": not effective_overall_rejection_rate_fail,
                "rate": round(overall_rejection_rate, 4),
                "threshold": 0.60,
                "total_rows": total_rows,
                "rejected_row_count": len(rejected_rows),
                "waived_for_enrichment_source": enrichment_match_signal_ok,
            },
            "enrichment_match_signal": {
                "applicable": enrichment_only_run,
                "ok": (not enrichment_only_run) or enrichment_match_signal_ok,
                "rate": round(enrichment_match_signal_rate, 4),
                "threshold": 0.30,
                "total_rows": total_rows,
                "rows_with_any_match_signal": len(rows_with_any_match_signal),
            },
            "duncan_fragmentary_ratio": {
                "ok": not duncan_fragmentary_ratio_fail,
                "ratio": round(duncan_fragmentary_ratio, 4),
                "threshold": 0.20,
                "duncan_total_rows": len(duncan_rows),
                "duncan_fragmentary_rows": len(duncan_fragmentary_rows),
            },
        },
    }


def purge_library_entries_for_work(
    dataset: dict[str, Any],
    *,
    work_id: str,
) -> tuple[dict[str, Any], list[str]]:
    normalized_work_id = normalize_nullable_string(work_id)
    if not normalized_work_id:
        return dataset, []

    removed_slugs: list[str] = []
    kept_entries: list[dict[str, Any]] = []
    for entry in dataset["entries"]:
        if normalize_nullable_string(entry.get("work_id")) == normalized_work_id:
            removed_slugs.append(entry["slug"])
            continue
        kept_entries.append(entry)

    if removed_slugs:
        dataset["entries"] = kept_entries
        refresh_degree_indexes(dataset)
    return dataset, removed_slugs


def choose_candidate_category(dataset: dict[str, Any], related_slugs: list[str]) -> str:
    for slug in related_slugs:
        entry = dataset["entryBySlug"].get(slug)
        if entry:
            return entry["category"]
    return next(iter(dataset["categories"].keys()))


def build_companion_candidate(
    *,
    route: dict[str, Any],
    section_title: str,
    section_id: str,
    chapter_slug: str,
    source_note: str,
    combined_result: dict[str, Any],
    medium_matches: list[dict[str, Any]],
    base_datasets: dict[str, dict[str, Any]],
    discovery: dict[str, Any],
) -> dict[str, Any]:
    degree = normalize_nullable_string(discovery.get("candidate_degree")) or select_candidate_degree(
        primary_degree=route.get("primary_degree"),
        medium_matches=medium_matches,
        available_degrees=set(base_datasets),
    )
    dataset = base_datasets[degree]
    related_slugs = unique_strings(match["slug"] for match in medium_matches if match["degree"] == degree)
    suggested_title = clean_heading_text(discovery.get("normalized_title") or section_title)
    candidate_slug = slugify(f"{degree}-{route['work_id']}-{section_id}-{suggested_title}", prefix=f"{degree}-candidate")
    draft_seed = {
        "slug": candidate_slug,
        "title": suggested_title,
        "degree": degree,
        "applies_to_degrees": [degree],
        "category": choose_candidate_category(dataset, related_slugs),
        "parent_topic": None,
        "aliases": [],
        "keywords": combined_result.get("keywords", [])[:12],
        "related_topics": {"prior": [], "companion": related_slugs[:8], "deeper": []},
        "short_summary": combined_result.get("section_summary") or f"Draft entry from {route['work_title']}.",
        "full_summary": combined_result.get("section_summary", ""),
        "practical_elements": combined_result.get("practical_elements", []),
        "symbolic_meaning": combined_result.get("symbolic_meaning", ""),
        "candidate_lesson": combined_result.get("candidate_lesson", ""),
        "tradition_notes": combined_result.get("tradition_notes", []),
        "caution_notes": combined_result.get("caution_notes", []),
        "source_notes": [source_note],
        "work_id": route["work_id"],
        "work_title": route["work_title"],
        "source_kind": route.get("source_kind"),
        "source_path": None,
        "source_anchor": None,
        "source_heading": section_title,
        "source_order": None,
        "parallel_entry": None,
        "knowledge_links": [],
        "source_library_slug": chapter_slug,
        "chapter_toc": [],
        "visibility_level": route.get("default_visibility_level", "internal"),
        "sensitivity_level": route.get("default_sensitivity_level", "standard"),
        "tradition_scope": route.get("default_tradition_scope", "interpretive"),
        "status": "draft",
    }
    return {
        "work_id": route["work_id"],
        "work_title": route["work_title"],
        "section_id": section_id,
        "section_title": section_title,
        "candidate_slug": candidate_slug,
        # Companion candidates are suggestions until an operator approves them
        # (see prod/schema/review_states.py).
        "review_state": "suggested",
        "suggested_title": suggested_title,
        "suggested_degree": degree,
        "suggested_category": draft_seed["category"],
        "related_existing_slugs": related_slugs[:12],
        "source_provenance": source_note,
        "confidence_reason": "No strong local match; staged for manual review as a companion candidate.",
        "decision": discovery.get("decision"),
        "candidate_degree": discovery.get("candidate_degree"),
        "degree_confidence": discovery.get("degree_confidence"),
        "reason_codes": discovery.get("reason_codes", []),
        "unit_kind": discovery.get("unit_kind"),
        "normalized_title": discovery.get("normalized_title"),
        "draft_seed": draft_seed,
    }


def main() -> None:
    args = build_parser().parse_args()
    if args.site_root is None:
        args.site_root = get_live_site_root()
    site_paths = build_site_data_paths(args.site_root.resolve())
    schema_path = args.schema.resolve() if args.schema else site_paths["schema"]
    library_path = args.library.resolve() if args.library else site_paths["library"]
    level1_path = args.level1.resolve() if args.level1 else site_paths["level1"]
    level2_path = args.level2.resolve() if args.level2 else site_paths["level2"]
    level3_path = args.level3.resolve() if args.level3 else site_paths["level3"]
    staging_dir = ensure_dir(args.staging_dir.resolve())
    log(
        f"[start] provider={args.provider} model={args.model} site_root={site_paths['site_root']} "
        f"input_dir={args.input_dir.resolve()} staging_dir={staging_dir}",
        quiet=args.quiet,
    )
    routing_config = read_json(args.routing_config.resolve())
    routes = choose_routes(routing_config, args.book)
    if not routes:
        raise SystemExit("No work routes matched the requested filter.")
    log(f"[routing] matched {len(routes)} work(s)", quiet=args.quiet)

    log("[audit] checking consolidated markdown and metadata pairs", quiet=args.quiet)
    audited_works = audit_inputs(args.input_dir.resolve(), routes)
    log(f"[audit] found {len(audited_works)} complete work(s)", quiet=args.quiet)

    level3_enabled = level3_path.exists()
    log(
        "[preflight] loading and normalizing library, level1, level2"
        + (", and level3" if level3_enabled else ""),
        quiet=args.quiet,
    )
    base_library = normalize_degree_data(read_json(library_path), "library")
    base_level1 = normalize_degree_data(read_json(level1_path), "level1")
    base_level2 = normalize_degree_data(read_json(level2_path), "level2")
    base_level3 = normalize_degree_data(read_json(level3_path), "level3") if level3_enabled else None

    for dataset in (base_library, base_level1, base_level2, base_level3):
        if dataset is None:
            continue
        dataset["meta"]["updated_at"] = dataset["meta"].get("updated_at") or today_date()

    base_reports = {
        "library": validate_against_schema(serialize_degree_data(base_library), schema_path),
        "level1": validate_against_schema(serialize_degree_data(base_level1), schema_path),
        "level2": validate_against_schema(serialize_degree_data(base_level2), schema_path),
    }
    if base_level3 is not None:
        base_reports["level3"] = validate_against_schema(serialize_degree_data(base_level3), schema_path)
    base_reference_report = validate_degree_references(
        {
            "library": base_library,
            "level1": base_level1,
            "level2": base_level2,
            **({"level3": base_level3} if base_level3 is not None else {}),
        }
    )
    preflight_summary = (
        "[preflight] validation "
        f"library={'ok' if base_reports['library']['ok'] else 'fail'} "
        f"level1={'ok' if base_reports['level1']['ok'] else 'fail'} "
        f"level2={'ok' if base_reports['level2']['ok'] else 'fail'} "
    )
    if "level3" in base_reports:
        preflight_summary += f"level3={'ok' if base_reports['level3']['ok'] else 'fail'} "
    preflight_summary += f"refs={'ok' if base_reference_report['ok'] else 'fail'}"
    log(preflight_summary, quiet=args.quiet)

    write_json(staging_dir / "base_library.normalized.json", serialize_degree_data(base_library))
    write_json(staging_dir / "base_level1.normalized.json", serialize_degree_data(base_level1))
    write_json(staging_dir / "base_level2.normalized.json", serialize_degree_data(base_level2))
    if base_level3 is not None:
        write_json(staging_dir / "base_level3.normalized.json", serialize_degree_data(base_level3))
    write_json(
        staging_dir / "base_validation_report.json",
        {
            "created_at": utc_timestamp(),
            "schema_path": str(schema_path),
            "degrees": base_reports,
            "references": base_reference_report,
            "ok": all(report["ok"] for report in base_reports.values()) and base_reference_report["ok"],
        },
    )

    candidate_library = deep_copy_degree(base_library)
    candidate_library["meta"]["updated_at"] = today_date()
    candidate_library, category_added = ensure_library_import_lane(candidate_library, routing_config)
    library_new_entries: list[dict[str, Any]] = []
    level1_operations: list[dict[str, Any]] = []
    level2_operations: list[dict[str, Any]] = []
    level3_operations: list[dict[str, Any]] = []
    companion_candidates: list[dict[str, Any]] = []
    discovery_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    work_manifest_rows: list[dict[str, Any]] = []
    link_rows: list[dict[str, Any]] = []
    staged_book_slugs: list[str] = []
    processed_units_total = 0
    gemini_fallback_count = 0
    completed_work_ids: list[str] = []
    interrupted_reason: str | None = None
    interrupted_context: dict[str, Any] | None = None

    if args.resume:
        if not args.book:
            raise SystemExit("--resume currently requires --book so the script knows which work to continue.")
        resume_state = load_resume_state(staging_dir=staging_dir, base_library=base_library)
        candidate_library = resume_state["candidate_library"]
        category_added = resume_state["category_added"]
        library_new_entries = resume_state["library_new_entries"]
        level1_operations = resume_state["level1_operations"]
        level2_operations = resume_state["level2_operations"]
        level3_operations = resume_state["level3_operations"]
        companion_candidates = resume_state["companion_candidates"]
        discovery_rows = resume_state["discovery_rows"]
        coverage_rows = resume_state["coverage_rows"]
        work_manifest_rows = resume_state["work_manifest_rows"]
        link_rows = resume_state["link_rows"]
        staged_book_slugs = resume_state["staged_book_slugs"]
        processed_units_total = resume_state["processed_units_total"]
        completed_work_ids = resume_state["completed_work_ids"]
        log(
            f"[resume] loaded staged state works={len(work_manifest_rows)} processed_units_total={processed_units_total}",
            quiet=args.quiet,
        )

    library_slug_pool = {entry["slug"] for entry in candidate_library["entries"]}
    catalog = build_entry_catalog(
        base_level1,
        base_level2,
        *([base_level3] if base_level3 is not None else []),
    )
    base_datasets = {
        "level1": base_level1,
        "level2": base_level2,
        **({"level3": base_level3} if base_level3 is not None else {}),
    }

    system_prompt = read_text(args.prompt_file.resolve()).strip() if args.provider == "gemini" else ""
    api_key = os.getenv(args.api_key_env) if args.provider == "gemini" else None
    if args.provider == "gemini" and not api_key:
        raise SystemExit(f"Gemini provider requires {args.api_key_env} to be set.")

    # Package B: local discovery preflight — audit unit kinds before any provider calls
    if args.provider == "gemini" and not args.resume:
        preflight_unit_kinds: dict[str, int] = {}
        preflight_total = 0
        for audited in audited_works:
            sections = normalize_extracted_sections(
                extract_sections(read_text(audited["markdown_path"]), max_mapping_chars=args.mapping_max_chars)
            )
            for section in sections:
                preflight_unit_kinds[section.unit_kind] = preflight_unit_kinds.get(section.unit_kind, 0) + 1
                preflight_total += 1

        noisy_kinds = {"toc", "front_matter", "officer_list", "page_fragment"}
        noisy_count = sum(preflight_unit_kinds.get(k, 0) for k in noisy_kinds)
        noisy_ratio = noisy_count / max(1, preflight_total)
        preflight_report = {
            "created_at": utc_timestamp(),
            "total_sections": preflight_total,
            "by_unit_kind": dict(sorted(preflight_unit_kinds.items())),
            "noisy_section_count": noisy_count,
            "noisy_ratio": round(noisy_ratio, 4),
            "provider_call_estimate": preflight_total - noisy_count,
        }
        write_json(staging_dir / "preflight_report.json", preflight_report)
        log(
            f"[preflight] total_sections={preflight_total} noisy={noisy_count} ({noisy_ratio:.1%}) "
            f"provider_call_estimate={preflight_report['provider_call_estimate']}",
            quiet=args.quiet,
        )
        if noisy_ratio >= 0.50:
            raise SystemExit(
                f"[preflight] BLOCKED: {noisy_ratio:.1%} of sections are noisy unit kinds "
                f"({noisy_count}/{preflight_total}). Fix source PDF extraction before provider calls."
            )

    for work_index, audited in enumerate(audited_works, start=1):
        route = audited["route"]
        if args.resume and route["work_id"] in completed_work_ids:
            log(f"[resume] skipping completed work {route['work_id']}", quiet=args.quiet)
            continue

        existing_work_row = next((row for row in work_manifest_rows if row.get("work_id") == route["work_id"]), None)
        if args.resume and args.book and route["work_id"] == args.book and not existing_work_row:
            raise SystemExit(
                f"No resumable staged state found for {route['work_id']} in {staging_dir}. "
                "Run once without --resume first."
            )

        source_path = str(audited["markdown_path"])
        apply_allowed_degrees = [degree for degree in route.get("applies_to_degrees", []) if degree in base_datasets]
        discovery_allowed_degrees = list(apply_allowed_degrees)
        if "level3" in base_datasets and route.get("primary_degree") in {"level2", "multi"} and "level3" not in discovery_allowed_degrees:
            discovery_allowed_degrees.append("level3")
        log(
            f"[work {work_index}/{len(audited_works)}] {route['work_id']} reading {audited['markdown_path'].name}",
            quiet=args.quiet,
        )
        all_sections = normalize_extracted_sections(
            extract_sections(read_text(audited["markdown_path"]), max_mapping_chars=args.mapping_max_chars)
        )
        source_section_count = len(all_sections)
        resume_section_offset = int(existing_work_row.get("section_count", 0)) if existing_work_row else 0
        if args.resume and resume_section_offset:
            log(
                f"[resume] {route['work_id']} continuing from section {resume_section_offset + 1} of {source_section_count}",
                quiet=args.quiet,
            )
        sections = all_sections[resume_section_offset:]
        if args.max_sections_per_work is not None:
            sections = sections[: args.max_sections_per_work]
            log(
                f"[work {work_index}/{len(audited_works)}] limited to {len(sections)} section(s) by --max-sections-per-work",
                quiet=args.quiet,
            )
        log(
            f"[work {work_index}/{len(audited_works)}] extracted {source_section_count} total section(s) and "
            f"{sum(len(section.mapping_units) for section in sections)} pending mapping unit(s)",
            quiet=args.quiet,
        )

        if not args.resume:
            candidate_library, removed_existing_work_slugs = purge_library_entries_for_work(
                candidate_library,
                work_id=route["work_id"],
            )
            if removed_existing_work_slugs:
                library_slug_pool.difference_update(removed_existing_work_slugs)
                log(
                    f"[work {work_index}/{len(audited_works)}] cleared {len(removed_existing_work_slugs)} existing "
                    f"library entr{'y' if len(removed_existing_work_slugs) == 1 else 'ies'} for rerun of {route['work_id']}",
                    quiet=args.quiet,
                )

        if args.resume and existing_work_row and existing_work_row.get("book_slug") in candidate_library["entryBySlug"]:
            book_entry = candidate_library["entryBySlug"][existing_work_row["book_slug"]]
            book_entry["full_summary"] = render_library_book_summary(route["work_title"], all_sections)
            book_entry["chapter_toc"] = [section.title for section in all_sections[:60]]
            chapter_entries = [
                candidate_library["entryBySlug"][section_row["chapter_slug"]]
                for section_row in existing_work_row.get("sections", [])
                if section_row.get("chapter_slug") in candidate_library["entryBySlug"]
            ]
            section_records = list(existing_work_row.get("sections", []))
        else:
            book_entry = create_staged_entry(
                candidate_library,
                library_slug_pool,
                {
                    "title": route["work_title"],
                    "slug": f"{route['work_id']}-book",
                    "type": "book",
                    "degree": "library",
                    "applies_to_degrees": route.get("applies_to_degrees", ["library"]),
                    "category": STAGED_LIBRARY_CATEGORY_ID,
                    "parent_topic": STAGED_LIBRARY_CATEGORY_ENTRY_SLUG,
                    "aliases": [route["source_book_name"]],
                    "keywords": unique_strings([route["work_id"], route.get("source_kind", ""), route.get("primary_degree", "")]),
                    "related_topics": {
                        "prior": [],
                        "companion": library_companion_targets(candidate_library, STAGED_LIBRARY_CATEGORY_ENTRY_SLUG),
                        "deeper": [],
                    },
                    "short_summary": render_short_summary(route["work_title"], fallback=route["work_title"]),
                    "full_summary": render_library_book_summary(route["work_title"], all_sections),
                    "practical_elements": [],
                    "symbolic_meaning": "",
                    "candidate_lesson": "",
                    "tradition_notes": [],
                    "caution_notes": [],
                    "source_notes": [f"Staged from consolidated markdown: {source_path}"],
                    "language": route.get("language"),
                    "work_id": route["work_id"],
                    "work_title": route["work_title"],
                    "source_kind": route.get("source_kind"),
                    "source_path": source_path,
                    "source_anchor": None,
                    "source_heading": None,
                    "source_order": 1,
                    "parallel_entry": None,
                    "translation_mode": None,
                    "knowledge_links": [],
                    "chapter_toc": [section.title for section in all_sections[:60]],
                    "visibility_level": route.get("default_visibility_level", "internal"),
                    "sensitivity_level": route.get("default_sensitivity_level", "standard"),
                    "tradition_scope": route.get("default_tradition_scope", "interpretive"),
                    "status": "draft",
                },
            )
            if book_entry["slug"] not in staged_book_slugs:
                staged_book_slugs.append(book_entry["slug"])
            chapter_entries = []
            section_records = []

        if args.resume and existing_work_row and not sections:
            log(f"[resume] no pending sections remain for {route['work_id']}", quiet=args.quiet)
            if route["work_id"] not in completed_work_ids:
                completed_work_ids.append(route["work_id"])
            continue

        promoted_discovery_titles = {
            normalize_text((row.get("discovery", {}) or {}).get("normalized_title") or "").lower(): row.get("section_id")
            for row in section_records
            if (row.get("discovery", {}) or {}).get("decision") in {"new_canonical_topic", "later_degree_candidate"}
            and normalize_text((row.get("discovery", {}) or {}).get("normalized_title") or "")
        }
        work_persisted = False

        def finalize_work(*, partial: bool, stop_reason: str | None = None) -> None:
            nonlocal work_persisted
            if work_persisted:
                return

            for index, chapter in enumerate(chapter_entries):
                previous_slug = chapter_entries[index - 1]["slug"] if index > 0 else None
                next_slug = chapter_entries[index + 1]["slug"] if index + 1 < len(chapter_entries) else None
                chapter["related_topics"] = {
                    "prior": [value for value in [previous_slug] if value],
                    "companion": library_companion_targets(
                        candidate_library,
                        book_entry["slug"],
                        next_slug,
                    ),
                    "deeper": [],
                }

            existing_manifest_index = next(
                (index for index, row in enumerate(work_manifest_rows) if row.get("work_id") == route["work_id"]),
                None,
            )
            existing_coverage_index = next(
                (index for index, row in enumerate(coverage_rows) if row.get("work_id") == route["work_id"]),
                None,
            )

            if existing_work_row and existing_work_row.get("book_slug") in candidate_library["entryBySlug"]:
                existing_chapter_slugs = {
                    section_row["chapter_slug"]
                    for section_row in existing_work_row.get("sections", [])
                    if section_row.get("chapter_slug")
                }
                new_entries = [chapter for chapter in chapter_entries if chapter["slug"] not in existing_chapter_slugs]
                if new_entries:
                    candidate_library["entries"].extend(new_entries)
                    library_new_entries.extend(new_entries)
            else:
                candidate_library["entries"].append(book_entry)
                candidate_library["entries"].extend(chapter_entries)
                library_new_entries.append(book_entry)
                library_new_entries.extend(chapter_entries)

            refresh_degree_indexes(candidate_library)

            manifest_row = {
                "work_id": route["work_id"],
                "work_title": route["work_title"],
                "source_book_name": route["source_book_name"],
                "source_path": source_path,
                "book_slug": book_entry["slug"],
                "section_count": len(section_records),
                "source_section_count": source_section_count,
                "chapter_count": len(chapter_entries),
                "partial": partial,
                "stop_reason": stop_reason,
                "sections": section_records,
            }
            coverage_row = {
                "work_id": route["work_id"],
                "section_count": len(section_records),
                "source_section_count": source_section_count,
                "chapter_count": len(chapter_entries),
                "mapping_unit_count": sum(len(item["mapping_units"]) for item in section_records),
                "strong_match_count": sum(len(item["strong_matches"]) for item in section_records),
                "medium_match_count": sum(len(item["medium_matches"]) for item in section_records),
                "preservation_ok": all(item["preservation"]["normalized_equal"] for item in section_records) if section_records else True,
                "partial": partial,
                "stop_reason": stop_reason,
            }
            if existing_manifest_index is None:
                work_manifest_rows.append(manifest_row)
            else:
                work_manifest_rows[existing_manifest_index] = manifest_row
            if existing_coverage_index is None:
                coverage_rows.append(coverage_row)
            else:
                coverage_rows[existing_coverage_index] = coverage_row
            work_persisted = True

        try:
            for section_index, section in enumerate(sections, start=1):
                section_title_for_routing = section.normalized_title or section.title
                log(
                    f"[section {work_index}/{len(audited_works)}:{section_index}/{len(sections)}] "
                    f"{route['work_id']}::{section.section_id} title={section.title!r} normalized={section_title_for_routing!r} "
                    f"kind={section.unit_kind} units={len(section.mapping_units)}",
                    quiet=args.quiet,
                )
                chapter_entry = create_staged_entry(
                    candidate_library,
                    library_slug_pool,
                    {
                        "title": section.title,
                        "slug": f"{route['work_id']}-{section.section_id}-{slugify(section.title, prefix='chapter')}",
                        "type": "chapter",
                        "degree": "library",
                        "applies_to_degrees": route.get("applies_to_degrees", ["library"]),
                        "category": STAGED_LIBRARY_CATEGORY_ID,
                        "parent_topic": book_entry["slug"],
                        "aliases": [],
                        "keywords": [],
                        "related_topics": {
                            "prior": [],
                            "companion": library_companion_targets(candidate_library, book_entry["slug"]),
                            "deeper": [],
                        },
                        "short_summary": render_short_summary(section.text, fallback=section.title),
                        "full_summary": section.text,
                        "practical_elements": [],
                        "symbolic_meaning": "",
                        "candidate_lesson": "",
                        "tradition_notes": [],
                        "caution_notes": [],
                        "source_notes": [],
                        "language": route.get("language"),
                        "work_id": route["work_id"],
                        "work_title": route["work_title"],
                        "source_kind": route.get("source_kind"),
                        "source_path": source_path,
                        "source_anchor": section.source_anchor,
                        "source_heading": section.title,
                        "source_order": section.source_order,
                        "parallel_entry": None,
                        "translation_mode": None,
                        "knowledge_links": [],
                        "chapter_toc": list(section.chapter_toc),
                        "visibility_level": route.get("default_visibility_level", "internal"),
                        "sensitivity_level": route.get("default_sensitivity_level", "standard"),
                        "tradition_scope": route.get("default_tradition_scope", "interpretive"),
                        "status": "draft",
                    },
                )
                source_note = build_source_note(
                    work_title=route["work_title"],
                    section_title=section.title,
                    source_path=source_path,
                    source_anchor=section.source_anchor,
                    source_order=section.source_order,
                )
                chapter_entry["source_notes"] = [source_note]

                unit_results: list[dict[str, Any]] = []
                section_used_fallback = False
                lexical_matches = find_catalog_matches(
                    section_title_for_routing,
                    section.text,
                    catalog,
                    allowed_degrees=discovery_allowed_degrees,
                )

                for unit_index, unit in enumerate(section.mapping_units, start=1):
                    if args.max_units_total is not None and processed_units_total >= args.max_units_total:
                        raise RunLimitReachedError(
                            f"Reached --max-units-total={args.max_units_total} at {route['work_id']} {section.section_id}"
                        )

                    if section.unit_kind in {
                        "toc",
                        "front_matter",
                        "officer_list",
                        "page_fragment",
                        "procedural_fragment",
                        "fragmentary_topic",
                    }:
                        log(
                            f"[unit {work_index}/{len(audited_works)}:{section_index}/{len(sections)}:{unit_index}/{len(section.mapping_units)}] "
                            f"skip provider for {section.unit_kind}",
                            quiet=args.quiet,
                        )
                        unit_results.append(
                            {
                                "section_summary": "",
                                "practical_elements": [],
                                "symbolic_meaning": "",
                                "candidate_lesson": "",
                                "keywords": [],
                                "caution_notes": [],
                                "tradition_notes": [],
                                "target_entry_candidates": [],
                                "knowledge_link_candidates": [],
                                "new_topic_candidates": [],
                                "_lexical_matches": [],
                            }
                        )
                        processed_units_total += 1
                        continue

                    if args.provider == "gemini":
                        log(
                            f"[unit {work_index}/{len(audited_works)}:{section_index}/{len(sections)}:{unit_index}/{len(section.mapping_units)}] "
                            f"gemini request chars={unit.char_length}",
                            quiet=args.quiet,
                        )
                        user_prompt = build_mapping_user_prompt(
                            work_id=route["work_id"],
                            work_title=route["work_title"],
                            source_book_name=route["source_book_name"],
                            section_id=section.section_id,
                            section_title=section_title_for_routing,
                            source_path=source_path,
                            source_anchor=section.source_anchor,
                            allowed_degrees=discovery_allowed_degrees,
                            catalog_excerpt_items=[
                                {
                                    "degree": match["degree"],
                                    "slug": match["slug"],
                                    "title": match["title"],
                                    "supporting_terms": match["supporting_terms"][:4],
                                }
                                for match in lexical_matches[:20]
                            ],
                            unit_text=unit.text,
                        )
                        result = None
                        for attempt in range(1, args.max_retries + 1):
                            try:
                                result = map_unit_with_gemini(
                                    system_prompt=system_prompt,
                                    model=args.model,
                                    api_key=api_key,
                                    temperature=args.temperature,
                                    max_output_tokens=args.max_output_tokens,
                                    user_prompt=user_prompt,
                                )
                                log(
                                    f"[unit {work_index}/{len(audited_works)}:{section_index}/{len(sections)}:{unit_index}/{len(section.mapping_units)}] "
                                    f"gemini success attempt={attempt}",
                                    quiet=args.quiet,
                                )
                                break
                            except Exception as exc:
                                log(
                                    f"[unit {work_index}/{len(audited_works)}:{section_index}/{len(sections)}:{unit_index}/{len(section.mapping_units)}] "
                                    f"gemini retry {attempt}/{args.max_retries} error={exc}",
                                    quiet=args.quiet,
                                )
                                if is_quota_exhausted_error(exc):
                                    raise QuotaExhaustedError(
                                        f"Quota exhausted at {route['work_id']} {section.section_id}: {exc}"
                                    ) from exc
                                if attempt == args.max_retries:
                                    if isinstance(exc, MalformedProviderPayloadError) or is_service_unavailable_error(exc):
                                        fallback_reason = (
                                            "malformed-json"
                                            if isinstance(exc, MalformedProviderPayloadError)
                                            else "service-unavailable"
                                        )
                                        log(
                                            f"[unit {work_index}/{len(audited_works)}:{section_index}/{len(sections)}:{unit_index}/{len(section.mapping_units)}] "
                                            f"gemini {fallback_reason} fallback=heuristic",
                                            quiet=args.quiet,
                                        )
                                        result = heuristic_extract_mapping(
                                            section_title_for_routing,
                                            unit.text,
                                            catalog,
                                            allowed_degrees=discovery_allowed_degrees,
                                        )
                                        section_used_fallback = True
                                        gemini_fallback_count += 1
                                        if args.max_fallback_count is not None and gemini_fallback_count >= args.max_fallback_count:
                                            raise ServiceUnavailableError(
                                                f"Gemini fallback threshold reached ({gemini_fallback_count}/{args.max_fallback_count}) "
                                                f"at {route['work_id']} {section.section_id} — possible provider outage."
                                            )
                                        break
                                    raise MappingInterruptedError(
                                        f"Mapping failed after retries at {route['work_id']} {section.section_id}: {exc}"
                                    ) from exc
                                retry_delay = min(args.sleep_seconds * (2 ** attempt), args.retry_max_delay)
                                time.sleep(retry_delay)
                        unit_results.append(result)
                        processed_units_total += 1
                        time.sleep(args.sleep_seconds)
                    else:
                        log(
                            f"[unit {work_index}/{len(audited_works)}:{section_index}/{len(sections)}:{unit_index}/{len(section.mapping_units)}] "
                            f"heuristic mapping chars={unit.char_length}",
                            quiet=args.quiet,
                        )
                        unit_results.append(
                            heuristic_extract_mapping(
                                section_title_for_routing,
                                unit.text,
                                catalog,
                                allowed_degrees=discovery_allowed_degrees,
                            )
                        )
                        processed_units_total += 1

                combined = combine_mapping_results(unit_results)
                discovery_resolution = resolve_target_matches(
                    combined,
                    lexical_matches,
                    catalog,
                    allowed_degrees=discovery_allowed_degrees,
                )
                resolution = resolve_target_matches(
                    combined,
                    lexical_matches,
                    catalog,
                    allowed_degrees=apply_allowed_degrees,
                )
                discovery = build_discovery_record(
                    section=section,
                    route_primary_degree=route.get("primary_degree"),
                    combined_result=combined,
                    resolution=discovery_resolution,
                    allowed_degrees=discovery_allowed_degrees,
                    apply_allowed_degrees=apply_allowed_degrees,
                )
                # Enrichment-source works never produce standalone topic candidates;
                # their content enriches existing entries only. Override any
                # new_canonical_topic / later_degree_candidate decisions to
                # reject_or_noise with ENRICHMENT_SOURCE reason code.
                if route.get("source_genre") == "enrichment_source" and discovery["decision"] in {
                    "new_canonical_topic",
                    "later_degree_candidate",
                }:
                    discovery = {
                        **discovery,
                        "decision": "reject_or_noise",
                        "candidate_degree": "unknown",
                        "degree_confidence": "low",
                        "reason_codes": unique_strings(
                            [*discovery.get("reason_codes", []), "ENRICHMENT_SOURCE", "ENRICHMENT_ONLY_ROUTE"]
                        ),
                    }
                duplicate_title_key = normalize_text(discovery.get("normalized_title") or "").lower()
                if (
                    duplicate_title_key
                    and duplicate_title_key in promoted_discovery_titles
                    and (
                        discovery["decision"] == "encyclopedia_candidate"
                        or (
                            discovery["decision"] in {"new_canonical_topic", "later_degree_candidate"}
                            and (
                                discovery.get("confidence") == "low"
                                or discovery.get("unit_kind") in {"procedural_fragment", "fragmentary_topic"}
                            )
                        )
                    )
                ):
                    discovery = {
                        **discovery,
                        "decision": "reject_or_noise",
                        "candidate_degree": "unknown",
                        "degree_confidence": "low",
                        "confidence": "medium",
                        "reason_codes": unique_strings(
                            [*discovery.get("reason_codes", []), "DUPLICATE_DISCOVERY_TITLE", "REJECTED_AS_DUPLICATE"]
                        ),
                    }
                elif discovery["decision"] in {"new_canonical_topic", "later_degree_candidate", "encyclopedia_candidate"} and duplicate_title_key:
                    promoted_discovery_titles[duplicate_title_key] = section.section_id
                discovery_rows.append(
                    {
                        "work_id": route["work_id"],
                        "work_title": route["work_title"],
                        "source_genre": route.get("source_genre"),
                        "provider_fallback": "heuristic" if section_used_fallback else None,
                        **discovery,
                    }
                )
                log(
                    f"[section {work_index}/{len(audited_works)}:{section_index}/{len(sections)}] "
                    f"strong={len(resolution['strong'])} medium={len(resolution['medium'])} rejected={len(resolution['rejected'])} "
                    f"decision={discovery['decision']} degree={discovery['candidate_degree']}",
                    quiet=args.quiet,
                )
                chapter_entry["knowledge_links"] = unique_links(
                    [build_cross_degree_link(match["slug"], match["degree"]) for match in resolution["strong"]]
                )
                chapter_entries.append(chapter_entry)
                link_rows.append(
                    {
                        "work_id": route["work_id"],
                        "section_id": section.section_id,
                        "chapter_slug": chapter_entry["slug"],
                        "knowledge_links": list(chapter_entry["knowledge_links"]),
                    }
                )

                content_targets = select_content_match_targets(resolution["strong"])
                for match in content_targets:
                    operation = build_degree_patch_operation(
                        target_slug=match["slug"],
                        target_degree=match["degree"],
                        work_id=route["work_id"],
                        work_title=route["work_title"],
                        section_id=section.section_id,
                        section_title=section.title,
                        chapter_slug=chapter_entry["slug"],
                        chapter_degree="library",
                        source_notes=[source_note],
                        section_summary=combined.get("section_summary", ""),
                        practical_elements=combined.get("practical_elements", []),
                        symbolic_meaning=combined.get("symbolic_meaning", ""),
                        candidate_lesson=combined.get("candidate_lesson", ""),
                        tradition_notes=combined.get("tradition_notes", []),
                        caution_notes=combined.get("caution_notes", []),
                    )
                    if match["degree"] == "level1":
                        level1_operations.append(operation)
                    elif match["degree"] == "level2":
                        level2_operations.append(operation)
                    else:
                        level3_operations.append(operation)

                if discovery["decision"] in {"new_canonical_topic", "later_degree_candidate"}:
                    companion_candidates.append(
                        build_companion_candidate(
                            route=route,
                            section_title=section_title_for_routing,
                            section_id=section.section_id,
                            chapter_slug=chapter_entry["slug"],
                            source_note=source_note,
                            combined_result=combined,
                            medium_matches=discovery_resolution["medium"],
                            base_datasets=base_datasets,
                            discovery=discovery,
                        )
                    )

                section_records.append(
                    {
                        **section.as_manifest_dict(),
                        "chapter_slug": chapter_entry["slug"],
                        "preservation": preservation_report(section.text, chapter_entry["full_summary"]),
                        "discovery": discovery,
                        "strong_matches": [build_cross_degree_link(match["slug"], match["degree"]) for match in resolution["strong"]],
                        "medium_matches": [build_cross_degree_link(match["slug"], match["degree"]) for match in resolution["medium"]],
                        "rejected_matches": resolution["rejected"],
                        "content_routing": {
                            "applied_targets": [build_cross_degree_link(match["slug"], match["degree"]) for match in content_targets],
                            "withheld_for_review": bool(resolution["strong"]) and not content_targets,
                        },
                    }
                )

            finalize_work(partial=False)
            completed_work_ids.append(route["work_id"])
            log(
                f"[work {work_index}/{len(audited_works)}] completed chapters={len(chapter_entries)} "
                f"strong_matches={sum(len(item['strong_matches']) for item in section_records)} "
                f"medium_matches={sum(len(item['medium_matches']) for item in section_records)}",
                quiet=args.quiet,
            )
            checkpoint_status = {
                "created_at": utc_timestamp(),
                "status": "running",
                "site_root": str(site_paths["site_root"]),
                "provider": args.provider,
                "model": args.model,
                "completed_work_ids": completed_work_ids,
                "processed_units_total": processed_units_total,
                "interrupted_reason": None,
                "interrupted_context": None,
            }
            persist_staged_outputs(
                staging_dir=staging_dir,
                schema_path=schema_path,
                category_added=category_added,
                candidate_library=candidate_library,
                base_level1=base_level1,
                base_level2=base_level2,
                base_level3=base_level3,
                library_new_entries=library_new_entries,
                level1_operations=level1_operations,
                level2_operations=level2_operations,
                level3_operations=level3_operations,
                companion_candidates=companion_candidates,
                discovery_rows=discovery_rows,
                work_manifest_rows=work_manifest_rows,
                link_rows=link_rows,
                coverage_rows=coverage_rows,
                run_status=checkpoint_status,
            )
            log(f"[checkpoint] saved staged artifacts after work {route['work_id']}", quiet=args.quiet)
        except (QuotaExhaustedError, RunLimitReachedError, ServiceUnavailableError, MappingInterruptedError) as exc:
            interrupted_reason = str(exc)
            interrupted_context = {
                "work_id": route["work_id"],
                "book_slug": book_entry["slug"],
                "processed_sections": len(section_records),
                "processed_units_total": processed_units_total,
            }
            finalize_work(partial=True, stop_reason=interrupted_reason)
            log(f"[stop] {interrupted_reason}", quiet=args.quiet)
            break

    landing_entry = candidate_library["entryBySlug"][STAGED_LIBRARY_CATEGORY_ENTRY_SLUG]
    landing_entry["related_topics"] = {
        "prior": [],
        "companion": library_companion_targets(candidate_library, *staged_book_slugs),
        "deeper": [],
    }
    for book_slug in staged_book_slugs:
        entry = candidate_library["entryBySlug"][book_slug]
        siblings = [slug for slug in staged_book_slugs if slug != book_slug]
        entry["related_topics"] = {
            "prior": [],
            "companion": library_companion_targets(candidate_library, STAGED_LIBRARY_CATEGORY_ENTRY_SLUG, *siblings),
            "deeper": [],
        }

    log(
        f"[patch] library_entries={len(library_new_entries)} level1_ops={len(level1_operations)} "
        f"level2_ops={len(level2_operations)} level3_ops={len(level3_operations)} "
        f"companion_candidates={len(companion_candidates)}",
        quiet=args.quiet,
    )
    log("[write] writing staged artifacts", quiet=args.quiet)
    final_status = {
        "created_at": utc_timestamp(),
        "status": "interrupted" if interrupted_reason else "completed",
        "site_root": str(site_paths["site_root"]),
        "provider": args.provider,
        "model": args.model,
        "completed_work_ids": completed_work_ids,
        "processed_units_total": processed_units_total,
        "interrupted_reason": interrupted_reason,
        "interrupted_context": interrupted_context,
    }
    final_provider_metrics = build_provider_metrics(
        discovery_rows=discovery_rows,
        processed_units_total=processed_units_total,
        gemini_fallback_count=gemini_fallback_count,
        provider=args.provider,
    )
    persist_staged_outputs(
        staging_dir=staging_dir,
        schema_path=schema_path,
        category_added=category_added,
        candidate_library=candidate_library,
        base_level1=base_level1,
        base_level2=base_level2,
        base_level3=base_level3,
        library_new_entries=library_new_entries,
        level1_operations=level1_operations,
        level2_operations=level2_operations,
        level3_operations=level3_operations,
        companion_candidates=companion_candidates,
        discovery_rows=discovery_rows,
        work_manifest_rows=work_manifest_rows,
        link_rows=link_rows,
        coverage_rows=coverage_rows,
        run_status=final_status,
        provider_metrics=final_provider_metrics,
    )
    log(
        f"[validate] final status={final_status['status']} completed_works={len(completed_work_ids)} "
        f"processed_units_total={processed_units_total} gemini_fallbacks={gemini_fallback_count}",
        quiet=args.quiet,
    )
    log(f"[done] staged artifacts written to {staging_dir}", quiet=args.quiet)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[error] {exc}", flush=True)
        raise
