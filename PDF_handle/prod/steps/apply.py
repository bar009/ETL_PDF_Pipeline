from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import ensure_dir, read_json, read_json_if_exists, read_text, utc_timestamp, write_json, write_json_group, write_text
from PDF_handle.prod.core.site_data import build_site_data_paths
from PDF_handle.prod.core.site_roots import get_live_site_root, stable_site_label
from PDF_handle.prod.companion_contract import (
    companion_candidate_category,
    companion_candidate_degree,
    companion_candidate_slug,
    companion_candidate_title,
    materialize_companion_payload,
)
from PDF_handle.prod.schema import (
    STAGED_LIBRARY_CATEGORY_ENTRY_SLUG,
    STAGED_LIBRARY_CATEGORY_ID,
    apply_active_overrides,
    apply_degree_patches,
    apply_override_review_decisions,
    build_override_review_template,
    load_override_bundle,
    normalize_degree_data,
    normalize_entry,
    normalize_override_bundle,
    reconstruct_governance_base_from_effective_datasets,
    refresh_degree_indexes,
    resolve_override_bundle,
    serialize_degree_data,
    validate_override_bundle,
    validate_against_schema,
    validate_degree_references,
)
from PDF_handle.prod.schema.data import infer_language_contract_fields, normalize_nullable_string
from PDF_handle.prod.schema.language_integrity import PROTECTED_TEXT_FIELDS, text_script_flags
from PDF_handle.prod.schema.patches import unique_links, unique_strings
from PDF_handle.prod.steps.apply_support import (
    companion_matches_selector,
    load_approval_selector,
    operation_matches_selector,
)

BASE_DIR = PDF_HANDLE_ROOT
DEFAULT_SITE_ROOT = get_live_site_root()
DEFAULT_STAGING_DIR = BASE_DIR / "staged_injection"
DEFAULT_SCHEMA_PATH = build_site_data_paths(DEFAULT_SITE_ROOT)["schema"]
DEFAULT_LIBRARY_PATH = build_site_data_paths(DEFAULT_SITE_ROOT)["library"]
DEFAULT_LEVEL1_PATH = build_site_data_paths(DEFAULT_SITE_ROOT)["level1"]
DEFAULT_LEVEL2_PATH = build_site_data_paths(DEFAULT_SITE_ROOT)["level2"]
DEFAULT_LEVEL3_PATH = build_site_data_paths(DEFAULT_SITE_ROOT)["level3"]
SANDBOX_ROOT_MARKERS = ("\\sites\\work\\", "\\sandbox_sites\\", "/sites/work/", "/sandbox_sites/")

# Recorded in the backup report when a live file did not exist before apply. Rollback
# must DELETE such a file (apply created it), not restore a misleading empty {} backup.
ABSENT_BEFORE_APPLY = "<absent-before-apply>"


def log(message: str, *, quiet: bool) -> None:
    if not quiet:
        print(message, flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Step 6: reviewed merge of staged Step 5 artifacts into live site JSON files."
    )
    parser.add_argument("--staging-dir", type=Path, default=DEFAULT_STAGING_DIR)
    parser.add_argument("--work-id", help="Optional work_id filter for staged artifacts inside the staging dir.")
    parser.add_argument(
        "--site-root",
        type=Path,
        default=DEFAULT_SITE_ROOT,
        help="Target site root. Defaults to the configured live root. Individual degree-path flags override it.",
    )
    parser.add_argument("--schema", type=Path, default=None)
    parser.add_argument("--overrides", type=Path, default=None, help="Canonical override bundle path. Defaults to <site-root>/data/content.overrides.json.")
    parser.add_argument("--library", type=Path, default=None)
    parser.add_argument("--level1", type=Path, default=None)
    parser.add_argument("--level2", type=Path, default=None)
    parser.add_argument("--level3", type=Path, default=None)
    parser.add_argument("--backup-dir", type=Path, default=None)
    parser.add_argument("--merge-library", action="store_true", help="Merge staged library entries into live library.json.")
    parser.add_argument(
        "--approve-level1",
        help='Approval spec for level1 operations. Use "all" or a JSON approval file.',
    )
    parser.add_argument(
        "--approve-level2",
        help='Approval spec for level2 operations. Use "all" or a JSON approval file.',
    )
    parser.add_argument(
        "--approve-level3",
        help='Approval spec for level3 operations. Use "all" or a JSON approval file.',
    )
    parser.add_argument(
        "--approve-companions",
        help='Approval spec for companion candidates. Use "all" or a JSON approval file.',
    )
    parser.add_argument(
        "--allow-multi-work",
        action="store_true",
        help="Allow Step 6 to operate on a staging dir that contains more than one work.",
    )
    parser.add_argument(
        "--override-review-decisions",
        type=Path,
        default=None,
        help="Optional override review-decision JSON to promote accept_base / update_override / reject_candidate actions.",
    )
    parser.add_argument("--apply-live", action="store_true", help="Write merged results into the selected site-root data files.")
    parser.add_argument(
        "--guarded-write-blocking-narrow",
        action="store_true",
        help=(
            "Enable the narrow V1 guarded write-blocking gate for sandbox/work roots only. "
            "This blocks localized companion creation and protected-field cross-language overrides."
        ),
    )
    parser.add_argument(
        "--allow-legacy-target",
        action="store_true",
        help="Allow --apply-live to write into legacy 0.2 targets. Without this flag, 0.2 is frozen.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output.")
    return parser


def is_within_path(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def ensure_staging_files(staging_dir: Path) -> dict[str, Path]:
    paths = {
        "work_manifest": staging_dir / "work_manifest.generated.json",
        "library_candidate": staging_dir / "library.candidate.json",
        "library_patch": staging_dir / "library.patch.json",
        "level1_patch": staging_dir / "level1.patch.json",
        "level2_patch": staging_dir / "level2.patch.json",
        "level3_patch": staging_dir / "level3.patch.json",
        "level3_candidate": staging_dir / "level3.candidate.json",
        "companion_candidates": staging_dir / "companion_candidates.json",
    }
    required = (
        "work_manifest",
        "library_candidate",
        "library_patch",
        "level1_patch",
        "level2_patch",
        "companion_candidates",
    )
    missing = [str(paths[name].name) for name in required if not paths[name].exists()]
    if missing:
        raise SystemExit(f"Missing staged Step 5 artifacts in {staging_dir}: {', '.join(missing)}")
    return paths


def filter_staged_payloads_for_work(
    *,
    requested_work_id: str | None,
    allow_multi_work: bool,
    work_manifest: dict[str, Any],
    library_patch: dict[str, Any],
    level1_patch: dict[str, Any],
    level2_patch: dict[str, Any],
    level3_patch: dict[str, Any],
    companion_candidates: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], list[str]]:
    manifest_work_ids = [
        str(item.get("work_id") or "").strip()
        for item in work_manifest.get("works", [])
        if str(item.get("work_id") or "").strip()
    ]
    unique_work_ids = list(dict.fromkeys(manifest_work_ids))

    if requested_work_id:
        if requested_work_id not in unique_work_ids:
            raise SystemExit(
                f"work_id {requested_work_id!r} was not found in work_manifest.generated.json. "
                f"Available work_ids: {', '.join(unique_work_ids) or '(none)'}"
            )
    elif len(unique_work_ids) > 1 and not allow_multi_work:
        raise SystemExit(
            "This staging dir contains multiple works. "
            f"Use --work-id one of: {', '.join(unique_work_ids)} "
            "or pass --allow-multi-work if you intentionally want to merge everything in this folder."
        )

    if not requested_work_id:
        return library_patch, level1_patch, level2_patch, level3_patch, companion_candidates, unique_work_ids

    filtered_library_patch = {
        **library_patch,
        "entries": [
            entry for entry in library_patch.get("entries", [])
            if str(entry.get("work_id") or "").strip() == requested_work_id
        ],
    }
    filtered_level1_patch = {
        **level1_patch,
        "operations": [
            item for item in level1_patch.get("operations", [])
            if str(item.get("work_id") or "").strip() == requested_work_id
        ],
    }
    filtered_level2_patch = {
        **level2_patch,
        "operations": [
            item for item in level2_patch.get("operations", [])
            if str(item.get("work_id") or "").strip() == requested_work_id
        ],
    }
    filtered_level3_patch = {
        **level3_patch,
        "operations": [
            item for item in level3_patch.get("operations", [])
            if str(item.get("work_id") or "").strip() == requested_work_id
        ],
    }
    filtered_companions = [
        item for item in companion_candidates
        if str(item.get("work_id") or "").strip() == requested_work_id
    ]
    return filtered_library_patch, filtered_level1_patch, filtered_level2_patch, filtered_level3_patch, filtered_companions, [requested_work_id]


def summarize_operation(operation: dict[str, Any]) -> dict[str, Any]:
    return {
        "marker_id": operation.get("marker_id"),
        "slug": operation.get("slug"),
        "degree": operation.get("degree"),
        "work_id": operation.get("work_id"),
        "section_id": operation.get("section_id"),
        "has_full_summary_block": bool(operation.get("changes", {}).get("full_summary_block")),
        "practical_count": len(operation.get("changes", {}).get("practical_elements", [])),
        "tradition_count": len(operation.get("changes", {}).get("tradition_notes", [])),
        "caution_count": len(operation.get("changes", {}).get("caution_notes", [])),
    }


def summarize_companion(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_slug": companion_candidate_slug(candidate),
        "title": companion_candidate_title(candidate),
        "degree": companion_candidate_degree(candidate),
        "category": companion_candidate_category(candidate),
        "work_id": candidate.get("work_id"),
        "section_id": candidate.get("section_id"),
        "related_existing_slugs": candidate.get("related_existing_slugs", []),
    }


def site_root_is_sandbox_like(site_root: Path) -> bool:
    normalized = str(site_root.resolve()).replace("/", "\\").lower()
    return any(marker.strip("\\").lower() in normalized for marker in SANDBOX_ROOT_MARKERS)


def classify_cross_language_text(*, target_entry: dict[str, Any], value: Any) -> dict[str, Any] | None:
    metadata = infer_language_contract_fields(target_entry)
    flags = text_script_flags(value)
    if not flags["text"]:
        return None
    if metadata["canonical_language"] == "en" and metadata["display_language"] == "en" and flags["has_hebrew"]:
        return {
            "preview": flags["text"][:160],
            "target_language_contract": {
                "language": normalize_nullable_string(target_entry.get("language")),
                "source_language": metadata["source_language"],
                "canonical_language": metadata["canonical_language"],
                "display_language": metadata["display_language"],
                "translation_mode": normalize_nullable_string(target_entry.get("translation_mode")),
            },
        }
    return None


def build_narrow_guarded_blocks(
    *,
    selected_companions: list[dict[str, Any]],
    categories_by_degree: dict[str, dict[str, Any]],
    override_bundle: dict[str, Any],
    datasets_before_overrides: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    for candidate in selected_companions:
        try:
            payload = materialize_companion_payload(candidate, categories_by_degree=categories_by_degree)
        except Exception as exc:
            blocks.append(
                {
                    "kind": "companion_materialization_failure",
                    "degree": normalize_nullable_string(companion_candidate_degree(candidate)),
                    "slug": normalize_nullable_string(companion_candidate_slug(candidate)),
                    "work_id": normalize_nullable_string(candidate.get("work_id")),
                    "section_id": normalize_nullable_string(candidate.get("section_id")),
                    "message": f"Companion materialization failed; refusing narrow-guarded merge: {exc}",
                    "details": {"error_type": type(exc).__name__},
                }
            )
            continue
        metadata = infer_language_contract_fields(payload)
        if metadata["display_language"] and metadata["canonical_language"] and metadata["display_language"] != metadata["canonical_language"]:
            blocks.append(
                {
                    "kind": "localized_companion_creation",
                    "degree": normalize_nullable_string(payload.get("degree")),
                    "slug": normalize_nullable_string(payload.get("slug")),
                    "work_id": normalize_nullable_string(candidate.get("work_id")),
                    "section_id": normalize_nullable_string(candidate.get("section_id")),
                    "message": "Localized companion creation is out of scope for narrow guarded write-blocking.",
                    "details": {
                        "display_language": metadata["display_language"],
                        "canonical_language": metadata["canonical_language"],
                        "translation_mode": normalize_nullable_string(payload.get("translation_mode")),
                    },
                }
            )

    for record in override_bundle.get("overrides", []):
        identity = record.get("identity") if isinstance(record.get("identity"), dict) else {}
        degree = normalize_nullable_string(identity.get("degree"))
        slug = normalize_nullable_string(identity.get("slug"))
        dataset = datasets_before_overrides.get(degree) if degree else None
        target_entry = dataset.get("entryBySlug", {}).get(slug) if isinstance(dataset, dict) and slug else None
        if not isinstance(target_entry, dict):
            continue
        for field_name, value in (record.get("fields") or {}).items():
            normalized_field = field_name.split(".", 1)[0]
            if normalized_field not in PROTECTED_TEXT_FIELDS and not field_name.startswith("reading_layers"):
                continue
            decision = classify_cross_language_text(target_entry=target_entry, value=value)
            if decision is None:
                continue
            blocks.append(
                {
                    "kind": "override_cross_language_protected_field",
                    "degree": degree,
                    "slug": slug,
                    "work_id": normalize_nullable_string(identity.get("work_id")),
                    "section_id": None,
                    "message": "Protected-field cross-language override would be blocked under the narrow guarded mode.",
                    "details": {
                        "field": field_name,
                        "identity_language": normalize_nullable_string(identity.get("language")),
                        "preview": decision["preview"],
                        "target_language_contract": decision["target_language_contract"],
                    },
                }
            )

    return blocks


def upsert_entry(dataset: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    slug = str(payload.get("slug") or "").strip()
    if not slug:
        raise ValueError("Cannot merge entry without a slug.")
    existing_indexes = [index for index, entry in enumerate(dataset["entries"]) if entry.get("slug") == slug]
    index = existing_indexes[0] if existing_indexes else len(dataset["entries"])
    normalized = normalize_entry(
        payload,
        degree_id=dataset["meta"]["degree"],
        index=index,
        categories=dataset["categories"],
    )
    if existing_indexes:
        # Replace every stale copy of the same slug so a prior duplicate cannot survive a rerun.
        dataset["entries"] = [entry for entry in dataset["entries"] if entry.get("slug") != slug]
        dataset["entries"].insert(index, normalized)
    else:
        dataset["entries"].append(normalized)
    return refresh_degree_indexes(dataset)["entryBySlug"][slug]


def purge_work_entries(dataset: dict[str, Any], *, selected_work_ids: list[str]) -> tuple[dict[str, Any], list[str]]:
    selected = {work_id for work_id in selected_work_ids if work_id}
    if not selected:
        return dataset, []

    removed_slugs: list[str] = []
    kept_entries: list[dict[str, Any]] = []
    for entry in dataset["entries"]:
        entry_work_id = str(entry.get("work_id") or "").strip()
        if entry_work_id and entry_work_id in selected:
            removed_slugs.append(entry["slug"])
            continue
        kept_entries.append(entry)

    dataset["entries"] = kept_entries
    refresh_degree_indexes(dataset)
    return dataset, removed_slugs


def library_entry_identity_key(entry: dict[str, Any]) -> tuple[str, str, str | None, str | None, str | None]:
    return (
        str(entry.get("work_id") or "").strip(),
        str(entry.get("type") or "").strip(),
        str(entry.get("source_anchor") or "").strip() or None,
        str(entry.get("source_order") or "").strip() or None,
        str(entry.get("source_heading") or "").strip() or None,
    )


def build_library_slug_redirects(
    *,
    live_library_before_merge: dict[str, Any],
    merged_library: dict[str, Any],
    selected_work_ids: list[str],
) -> dict[str, str]:
    selected = {work_id for work_id in selected_work_ids if work_id}
    if not selected:
        return {}

    merged_by_key = {
        library_entry_identity_key(entry): entry["slug"]
        for entry in merged_library["entries"]
        if str(entry.get("work_id") or "").strip() in selected
    }

    redirects: dict[str, str] = {}
    for entry in live_library_before_merge["entries"]:
        work_id = str(entry.get("work_id") or "").strip()
        old_slug = str(entry.get("slug") or "").strip()
        if work_id not in selected or not old_slug:
            continue
        new_slug = merged_by_key.get(library_entry_identity_key(entry))
        if new_slug and new_slug != old_slug:
            redirects[old_slug] = new_slug
    return redirects


def build_library_slug_reuse_map(
    *,
    live_library_before_merge: dict[str, Any],
    library_patch: dict[str, Any],
    selected_work_ids: list[str],
) -> dict[str, str]:
    selected = {work_id for work_id in selected_work_ids if work_id}
    if not selected:
        return {}

    live_key_counts: dict[tuple[str, str, str | None, str | None, str | None], int] = {}
    live_slug_by_key: dict[tuple[str, str, str | None, str | None, str | None], str] = {}
    for entry in live_library_before_merge["entries"]:
        work_id = str(entry.get("work_id") or "").strip()
        slug = str(entry.get("slug") or "").strip()
        if work_id not in selected or not slug:
            continue
        identity_key = library_entry_identity_key(entry)
        live_key_counts[identity_key] = live_key_counts.get(identity_key, 0) + 1
        live_slug_by_key.setdefault(identity_key, slug)

    reuse_map: dict[str, str] = {}
    for payload in library_patch.get("entries", []):
        staged_slug = str(payload.get("slug") or "").strip()
        if not staged_slug:
            continue
        identity_key = library_entry_identity_key(payload)
        if live_key_counts.get(identity_key) != 1:
            continue
        live_slug = live_slug_by_key.get(identity_key)
        if live_slug and live_slug != staged_slug:
            reuse_map[staged_slug] = live_slug
    return reuse_map


def rewrite_library_related_topics(value: Any, *, slug_map: dict[str, str]) -> Any:
    if not slug_map:
        return value
    if isinstance(value, list):
        return unique_strings(slug_map.get(str(item).strip(), str(item).strip()) for item in value if str(item).strip())
    if isinstance(value, dict):
        return {
            "prior": unique_strings(slug_map.get(str(item).strip(), str(item).strip()) for item in value.get("prior", [])),
            "companion": unique_strings(
                slug_map.get(str(item).strip(), str(item).strip()) for item in value.get("companion", [])
            ),
            "deeper": unique_strings(slug_map.get(str(item).strip(), str(item).strip()) for item in value.get("deeper", [])),
        }
    return value


def rewrite_library_knowledge_links(links: Any, *, slug_map: dict[str, str]) -> list[dict[str, str]]:
    if not isinstance(links, list) or not slug_map:
        return links if isinstance(links, list) else []
    rewritten: list[dict[str, str]] = []
    for link in links:
        if not isinstance(link, dict):
            continue
        degree = str(link.get("degree") or "").strip()
        slug = str(link.get("slug") or "").strip()
        if not degree or not slug:
            continue
        if degree == "library":
            slug = slug_map.get(slug, slug)
        rewritten.append({"degree": degree, "slug": slug})
    return unique_links(rewritten)


def rewrite_library_payload_slugs(payload: dict[str, Any], *, slug_map: dict[str, str]) -> dict[str, Any]:
    rewritten = copy.deepcopy(payload)
    if not slug_map:
        return rewritten
    slug = str(rewritten.get("slug") or "").strip()
    if slug in slug_map:
        rewritten["slug"] = slug_map[slug]
    if "related_topics" in rewritten:
        rewritten["related_topics"] = rewrite_library_related_topics(rewritten.get("related_topics"), slug_map=slug_map)
    if "knowledge_links" in rewritten:
        rewritten["knowledge_links"] = rewrite_library_knowledge_links(rewritten.get("knowledge_links"), slug_map=slug_map)
    return rewritten


def rewrite_operation_library_links(operation: dict[str, Any], *, slug_map: dict[str, str]) -> dict[str, Any]:
    rewritten = copy.deepcopy(operation)
    if not slug_map:
        return rewritten
    changes = rewritten.setdefault("changes", {})
    changes["knowledge_links"] = rewrite_library_knowledge_links(changes.get("knowledge_links"), slug_map=slug_map)
    return rewritten


def rewrite_companion_library_links(candidate: dict[str, Any], *, slug_map: dict[str, str]) -> dict[str, Any]:
    rewritten = copy.deepcopy(candidate)
    if not slug_map:
        return rewritten
    seed = rewritten.get("draft_seed")
    if isinstance(seed, dict):
        seed["knowledge_links"] = rewrite_library_knowledge_links(seed.get("knowledge_links"), slug_map=slug_map)
        rewritten["draft_seed"] = seed
    payload = rewritten.get("draft_entry_payload")
    if isinstance(payload, dict):
        rewritten["draft_entry_payload"] = rewrite_library_payload_slugs(payload, slug_map=slug_map)
    return rewritten


def retarget_library_knowledge_links(
    degree_data: dict[str, Any],
    *,
    slug_redirects: dict[str, str],
) -> tuple[dict[str, Any], int]:
    if not slug_redirects:
        return degree_data, 0

    rewritten = 0
    for entry in degree_data["entries"]:
        updated_links: list[dict[str, str]] = []
        entry_changed = False
        for link in entry.get("knowledge_links", []):
            degree = str(link.get("degree") or "").strip()
            slug = str(link.get("slug") or "").strip()
            if degree == "library" and slug in slug_redirects:
                updated_links.append({"degree": "library", "slug": slug_redirects[slug]})
                rewritten += 1
                entry_changed = True
            else:
                updated_links.append(link)
        if entry_changed:
            entry["knowledge_links"] = unique_links(updated_links)
    refresh_degree_indexes(degree_data)
    return degree_data, rewritten


def merge_library_lane(
    live_library: dict[str, Any],
    staged_library: dict[str, Any],
    library_patch: dict[str, Any],
    *,
    selected_work_ids: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    merged = live_library
    merged["meta"]["updated_at"] = staged_library["meta"].get("updated_at")
    if STAGED_LIBRARY_CATEGORY_ID in staged_library["categories"]:
        merged["categories"][STAGED_LIBRARY_CATEGORY_ID] = dict(staged_library["categories"][STAGED_LIBRARY_CATEGORY_ID])

    merged, removed_stale_slugs = purge_work_entries(merged, selected_work_ids=selected_work_ids)
    merged_slugs: list[str] = []
    if STAGED_LIBRARY_CATEGORY_ENTRY_SLUG in staged_library["entryBySlug"]:
        upsert_entry(merged, staged_library["entryBySlug"][STAGED_LIBRARY_CATEGORY_ENTRY_SLUG])
        merged_slugs.append(STAGED_LIBRARY_CATEGORY_ENTRY_SLUG)

    for payload in library_patch.get("entries", []):
        upsert_entry(merged, payload)
        merged_slugs.append(str(payload.get("slug") or ""))

    book_entries = sorted(
        [
            entry
            for entry in merged["entries"]
            if entry.get("category") == STAGED_LIBRARY_CATEGORY_ID and entry.get("type") == "book"
        ],
        key=lambda entry: (str(entry.get("title") or "").lower(), entry["slug"]),
    )
    landing_entry = merged["entryBySlug"].get(STAGED_LIBRARY_CATEGORY_ENTRY_SLUG)
    has_library_guide = "library-guide" in merged.get("entryBySlug", {})
    if landing_entry:
        landing_entry["related_topics"] = {
            "prior": [],
            "companion": unique_strings(
                [*([ "library-guide"] if has_library_guide else []), *[entry["slug"] for entry in book_entries]]
            ),
            "deeper": [],
        }
    for book in book_entries:
        siblings = [entry["slug"] for entry in book_entries if entry["slug"] != book["slug"]]
        book["related_topics"] = {
            "prior": [],
            "companion": unique_strings(
                [STAGED_LIBRARY_CATEGORY_ENTRY_SLUG, *([ "library-guide"] if has_library_guide else []), *siblings]
            ),
            "deeper": [],
        }
    refresh_degree_indexes(merged)
    return merged, {
        "merged_entry_count": len([slug for slug in merged_slugs if slug]),
        "merged_slugs": [slug for slug in merged_slugs if slug],
        "removed_stale_entry_count": len(removed_stale_slugs),
        "removed_stale_slugs": removed_stale_slugs,
        "category_id": STAGED_LIBRARY_CATEGORY_ID,
    }


def merge_companion_candidates(
    datasets: dict[str, dict[str, Any]],
    candidates: list[dict[str, Any]],
    *,
    library_dataset: dict[str, Any] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    added: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    available_link_targets = {
        degree: set(dataset.get("entryBySlug", {}).keys())
        for degree, dataset in datasets.items()
    }
    if library_dataset is not None:
        available_link_targets["library"] = set(library_dataset.get("entryBySlug", {}).keys())
    for candidate in candidates:
        payload = materialize_companion_payload(
            candidate,
            categories_by_degree={degree: dataset["categories"] for degree, dataset in datasets.items()},
            available_link_targets=available_link_targets,
        )
        degree_id = str(payload.get("degree") or "").strip()
        if degree_id not in datasets:
            skipped.append({"candidate_slug": companion_candidate_slug(candidate), "reason": f"unknown degree {degree_id}"})
            continue
        dataset = datasets[degree_id]
        slug = str(payload.get("slug") or "").strip()
        if slug in dataset["entryBySlug"]:
            skipped.append({"candidate_slug": slug, "reason": "slug already exists"})
            continue
        upsert_entry(dataset, payload)
        added.append({"candidate_slug": slug, "degree": degree_id})
    return datasets, {"added": added, "skipped": skipped}


def backup_live_files(*, backup_dir: Path, paths: dict[str, Path]) -> dict[str, str]:
    timestamp_dir = ensure_dir(backup_dir / utc_timestamp().replace(":", "-"))
    report: dict[str, str] = {}
    for label, path in paths.items():
        if path.exists():
            target = timestamp_dir / path.name
            write_text(target, read_text(path))
            report[label] = str(target)
        else:
            # No pre-apply file to back up; flag it so rollback removes the
            # apply-created file instead of restoring an empty {} stand-in.
            report[label] = ABSENT_BEFORE_APPLY
    return report


def write_rollback_plan_md(
    staging_dir: Path,
    backup_report: dict[str, str],
    live_paths: dict[str, str],
    work_id: str | None,
) -> None:
    """Write rollback_plan.md so any operator can restore the live site from backup."""
    lines: list[str] = [
        "# Rollback Plan",
        "",
        f"Generated after Step 6 apply for work_id={work_id!r}.",
        "Copy each backup file back to its live target to undo this apply.",
        "",
        "## Restore Commands (shell)",
        "",
        "```bash",
    ]
    for label, backup_path in backup_report.items():
        live_path = live_paths.get(label)
        if not live_path:
            continue
        if backup_path == ABSENT_BEFORE_APPLY:
            lines.append(f'rm -f "{live_path}"')
        else:
            lines.append(f'cp "{backup_path}" "{live_path}"')
    lines += [
        "```",
        "",
        "## Post-Rollback Validation",
        "",
        "After restoring, run Step 7 to confirm site data integrity:",
        "",
        "```bash",
        "python3 PDF_handle/prod/steps/qa.py --site-root <site-root>",
        "```",
        "",
        "## Backup Files",
        "",
    ]
    for label, backup_path in backup_report.items():
        if backup_path == ABSENT_BEFORE_APPLY:
            lines.append(f"- `{label}`: did not exist before apply — remove on rollback")
        else:
            lines.append(f"- `{label}`: `{backup_path}`")
    lines.append("")
    write_text(staging_dir / "rollback_plan.md", "\n".join(lines))


def main() -> None:
    args = build_parser().parse_args()
    site_paths = build_site_data_paths(args.site_root.resolve())
    schema_path = args.schema.resolve() if args.schema else site_paths["schema"]
    overrides_path = args.overrides.resolve() if args.overrides else site_paths["overrides"]
    library_path = args.library.resolve() if args.library else site_paths["library"]
    level1_path = args.level1.resolve() if args.level1 else site_paths["level1"]
    level2_path = args.level2.resolve() if args.level2 else site_paths["level2"]
    level3_path = args.level3.resolve() if args.level3 else site_paths["level3"]
    backup_dir = args.backup_dir.resolve() if args.backup_dir else (BASE_DIR / "merge_backups" / stable_site_label(site_paths["site_root"])).resolve()
    staging_dir = args.staging_dir.resolve()
    staged_paths = ensure_staging_files(staging_dir)

    if not any([args.merge_library, args.approve_level1, args.approve_level2, args.approve_level3, args.approve_companions]):
        raise SystemExit("Nothing selected. Use --merge-library and/or approval flags for level1/level2/level3/companions.")

    log(
        f"[start] site_root={site_paths['site_root']} staging_dir={staging_dir} apply_live={args.apply_live}",
        quiet=args.quiet,
    )
    if args.guarded_write_blocking_narrow and args.apply_live and not site_root_is_sandbox_like(site_paths["site_root"]):
        raise SystemExit(
            "Narrow guarded write-blocking is sandbox/work only. Point Step 6 at a sandbox/work root before using this gate."
        )

    work_manifest = read_json(staged_paths["work_manifest"])
    staged_library = normalize_degree_data(read_json(staged_paths["library_candidate"]), "library")
    library_patch = read_json(staged_paths["library_patch"])
    level1_patch = read_json(staged_paths["level1_patch"])
    level2_patch = read_json(staged_paths["level2_patch"])
    level3_patch = read_json(staged_paths["level3_patch"]) if staged_paths["level3_patch"].exists() else {"degree": "level3", "operations": []}
    companion_candidates = read_json(staged_paths["companion_candidates"])
    library_patch, level1_patch, level2_patch, level3_patch, companion_candidates, selected_work_ids = filter_staged_payloads_for_work(
        requested_work_id=args.work_id,
        allow_multi_work=args.allow_multi_work,
        work_manifest=work_manifest,
        library_patch=library_patch,
        level1_patch=level1_patch,
        level2_patch=level2_patch,
        level3_patch=level3_patch,
        companion_candidates=companion_candidates,
    )
    log(
        f"[scope] selected_work_ids={', '.join(selected_work_ids) or '(none)'}",
        quiet=args.quiet,
    )

    live_library = normalize_degree_data(read_json(library_path), "library")
    live_level1 = normalize_degree_data(read_json(level1_path), "level1")
    live_level2 = normalize_degree_data(read_json(level2_path), "level2")
    level3_enabled = level3_path.exists() and staged_paths["level3_candidate"].exists()
    if args.approve_level3 and not level3_enabled:
        raise SystemExit(
            "Step 6 cannot approve level3 operations because the selected site root or staging dir does not carry level3 artifacts."
        )
    live_level3 = normalize_degree_data(read_json(level3_path), "level3") if level3_enabled else None

    merged_library = live_library
    merged_level1 = live_level1
    merged_level2 = live_level2
    merged_level3 = live_level3

    library_slug_reuse_map = build_library_slug_reuse_map(
        live_library_before_merge=live_library,
        library_patch=library_patch,
        selected_work_ids=selected_work_ids,
    )
    if library_slug_reuse_map:
        library_patch = {
            **library_patch,
            "entries": [
                rewrite_library_payload_slugs(payload, slug_map=library_slug_reuse_map)
                for payload in library_patch.get("entries", [])
            ],
        }
        level1_patch = {
            **level1_patch,
            "operations": [
                rewrite_operation_library_links(operation, slug_map=library_slug_reuse_map)
                for operation in level1_patch.get("operations", [])
            ],
        }
        level2_patch = {
            **level2_patch,
            "operations": [
                rewrite_operation_library_links(operation, slug_map=library_slug_reuse_map)
                for operation in level2_patch.get("operations", [])
            ],
        }
        level3_patch = {
            **level3_patch,
            "operations": [
                rewrite_operation_library_links(operation, slug_map=library_slug_reuse_map)
                for operation in level3_patch.get("operations", [])
            ],
        }
        companion_candidates = [
            rewrite_companion_library_links(candidate, slug_map=library_slug_reuse_map)
            for candidate in companion_candidates
        ]

    library_report: dict[str, Any] = {
        "selected": args.merge_library,
        "merged_entry_count": 0,
        "merged_slugs": [],
        "reused_library_slug_count": len(library_slug_reuse_map),
        "reused_library_slugs": library_slug_reuse_map,
        "redirected_library_slug_count": 0,
        "redirected_library_slugs": {},
    }
    library_slug_redirects: dict[str, str] = {}
    if args.merge_library:
        log("[merge] applying staged library lane", quiet=args.quiet)
        live_library_before_merge = copy.deepcopy(merged_library)
        merged_library, merge_summary = merge_library_lane(
            merged_library,
            staged_library,
            library_patch,
            selected_work_ids=selected_work_ids,
        )
        library_report.update(merge_summary)
        library_slug_redirects = build_library_slug_redirects(
            live_library_before_merge=live_library_before_merge,
            merged_library=merged_library,
            selected_work_ids=selected_work_ids,
        )
        library_report["redirected_library_slug_count"] = len(library_slug_redirects)
        library_report["redirected_library_slugs"] = library_slug_redirects

    level1_mode, level1_selector = load_approval_selector(args.approve_level1)
    level2_mode, level2_selector = load_approval_selector(args.approve_level2)
    level3_mode, level3_selector = load_approval_selector(args.approve_level3)
    selected_level1_ops = [op for op in level1_patch.get("operations", []) if operation_matches_selector(op, level1_mode, level1_selector)]
    selected_level2_ops = [op for op in level2_patch.get("operations", []) if operation_matches_selector(op, level2_mode, level2_selector)]
    selected_level3_ops = [op for op in level3_patch.get("operations", []) if operation_matches_selector(op, level3_mode, level3_selector)]

    if selected_level1_ops:
        log(f"[merge] applying {len(selected_level1_ops)} level1 operation(s)", quiet=args.quiet)
        merged_level1 = apply_degree_patches(merged_level1, selected_level1_ops)
    if selected_level2_ops:
        log(f"[merge] applying {len(selected_level2_ops)} level2 operation(s)", quiet=args.quiet)
        merged_level2 = apply_degree_patches(merged_level2, selected_level2_ops)
    if selected_level3_ops:
        log(f"[merge] applying {len(selected_level3_ops)} level3 operation(s)", quiet=args.quiet)
        if merged_level3 is None:
            raise SystemExit("Step 6 selected level3 operations, but no level3 live dataset is available.")
        merged_level3 = apply_degree_patches(merged_level3, selected_level3_ops)

    companion_mode, companion_selector = load_approval_selector(args.approve_companions)
    selected_companions = [
        item for item in companion_candidates if companion_matches_selector(item, companion_mode, companion_selector)
    ]
    companion_report: dict[str, Any] = {"selected": len(selected_companions), "added": [], "skipped": []}
    if selected_companions:
        log(f"[merge] applying {len(selected_companions)} companion candidate(s)", quiet=args.quiet)
        merged_datasets, companion_report = merge_companion_candidates(
            {
                "level1": merged_level1,
                "level2": merged_level2,
                **({"level3": merged_level3} if merged_level3 is not None else {}),
            },
            selected_companions,
            library_dataset=merged_library,
        )
        merged_level1 = merged_datasets["level1"]
        merged_level2 = merged_datasets["level2"]
        if "level3" in merged_datasets:
            merged_level3 = merged_datasets["level3"]

    if library_slug_redirects:
        merged_level1, rewritten_level1_links = retarget_library_knowledge_links(
            merged_level1,
            slug_redirects=library_slug_redirects,
        )
        merged_level2, rewritten_level2_links = retarget_library_knowledge_links(
            merged_level2,
            slug_redirects=library_slug_redirects,
        )
        rewritten_level3_links = 0
        if merged_level3 is not None:
            merged_level3, rewritten_level3_links = retarget_library_knowledge_links(
                merged_level3,
                slug_redirects=library_slug_redirects,
            )
        library_report["retargeted_knowledge_link_count"] = (
            rewritten_level1_links + rewritten_level2_links + rewritten_level3_links
        )
        library_report["retargeted_knowledge_links"] = {
            "level1": rewritten_level1_links,
            "level2": rewritten_level2_links,
            "level3": rewritten_level3_links,
        }

    datasets_before_overrides = {
        "library": merged_library,
        "level1": merged_level1,
        "level2": merged_level2,
        **({"level3": merged_level3} if merged_level3 is not None else {}),
    }
    raw_override_bundle = load_override_bundle(overrides_path, site_root=site_paths["site_root"])
    override_bundle = normalize_override_bundle(raw_override_bundle, site_root=site_paths["site_root"])
    override_schema_report = validate_override_bundle(override_bundle, site_root=site_paths["site_root"])
    governance_datasets = (
        reconstruct_governance_base_from_effective_datasets(
            datasets_before_overrides,
            bundle=override_bundle,
        )
        if override_schema_report["ok"]
        else datasets_before_overrides
    )
    override_decision_report: dict[str, Any] = {"applied": [], "skipped": []}
    if override_schema_report["ok"] and args.override_review_decisions:
        override_decisions_payload = read_json_if_exists(args.override_review_decisions.resolve()) or {}
        override_bundle, override_decision_report = apply_override_review_decisions(
            override_bundle,
            datasets=governance_datasets,
            decisions_payload=override_decisions_payload,
        )
        override_schema_report = validate_override_bundle(override_bundle, site_root=site_paths["site_root"])
        governance_datasets = reconstruct_governance_base_from_effective_datasets(
            datasets_before_overrides,
            bundle=override_bundle,
        ) if override_schema_report["ok"] else datasets_before_overrides

    override_resolution_report = (
        resolve_override_bundle(override_bundle, datasets=governance_datasets)
        if override_schema_report["ok"]
        else {
            "summary": {"total": len(override_bundle.get("overrides", [])), "active": 0, "stale": 0, "orphaned": 0, "conflict": 0, "field_conflict_count": 0},
            "resolutions": [],
            "field_conflicts": [],
        }
    )
    guarded_blocks = (
        build_narrow_guarded_blocks(
            selected_companions=selected_companions,
            categories_by_degree={
                "level1": merged_level1["categories"],
                "level2": merged_level2["categories"],
                **({"level3": merged_level3["categories"]} if merged_level3 is not None else {}),
            },
            override_bundle=override_bundle,
            datasets_before_overrides=datasets_before_overrides,
        )
        if args.guarded_write_blocking_narrow
        else []
    )
    guarded_report = {
        "mode": "narrow_write_blocking" if args.guarded_write_blocking_narrow else "disabled",
        "site_root": str(site_paths["site_root"]),
        "apply_live_requested": args.apply_live,
        "block_count": len(guarded_blocks),
        "blocked": bool(guarded_blocks),
        "blocked_kinds": sorted({str(item.get("kind") or "") for item in guarded_blocks if item.get("kind")}),
        "risk_notes": [
            "This narrow gate blocks only localized companion creation and protected-field cross-language overrides.",
            "Patch operations remain in legacy behavior for now and are not blocked by this gate.",
            "Override blocks are evaluated against the current selected site-root datasets before override application.",
        ],
    }
    override_review_template = build_override_review_template(override_resolution_report)
    effective_datasets = (
        apply_active_overrides(
            copy.deepcopy(datasets_before_overrides),
            resolution_report=override_resolution_report,
            bundle=override_bundle,
        )
        if override_schema_report["ok"]
        else datasets_before_overrides
    )
    merged_library = effective_datasets["library"]
    merged_level1 = effective_datasets["level1"]
    merged_level2 = effective_datasets["level2"]
    merged_level3 = effective_datasets.get("level3")

    serialized_library = serialize_degree_data(merged_library)
    serialized_level1 = serialize_degree_data(merged_level1)
    serialized_level2 = serialize_degree_data(merged_level2)
    serialized_level3 = serialize_degree_data(merged_level3) if merged_level3 is not None else None

    validation_report = {
        "created_at": utc_timestamp(),
        "schema_path": str(schema_path),
        "overrides_path": str(overrides_path),
        "degrees": {
            "library": validate_against_schema(serialized_library, schema_path),
            "level1": validate_against_schema(serialized_level1, schema_path),
            "level2": validate_against_schema(serialized_level2, schema_path),
            **(
                {"level3": validate_against_schema(serialized_level3, schema_path)}
                if serialized_level3 is not None
                else {}
            ),
        },
        "references": validate_degree_references(
            {
                "library": merged_library,
                "level1": merged_level1,
                "level2": merged_level2,
                **({"level3": merged_level3} if merged_level3 is not None else {}),
            }
        ),
        "overrides": {
            "schema": override_schema_report,
            "resolution_summary": override_resolution_report["summary"],
            "decision_summary": {
                "applied_count": len(override_decision_report.get("applied", [])),
                "skipped_count": len(override_decision_report.get("skipped", [])),
            },
        },
    }
    validation_report["ok"] = (
        all(report["ok"] for report in validation_report["degrees"].values())
        and validation_report["references"]["ok"]
        and override_schema_report["ok"]
    )

    merge_report = {
        "created_at": utc_timestamp(),
        "staging_dir": str(staging_dir),
        "site_root": str(site_paths["site_root"]),
        "target_paths": {
            "schema": str(schema_path),
            "overrides": str(overrides_path),
            "library": str(library_path),
            "level1": str(level1_path),
            "level2": str(level2_path),
            **({"level3": str(level3_path)} if merged_level3 is not None else {}),
        },
        "selected_work_ids": selected_work_ids,
        "apply_live": args.apply_live,
        "live_write_completed": False,
        "live_write_completed_at": None,
        "library": library_report,
        "level1": {
            "selected_count": len(selected_level1_ops),
            "selected_operations": [summarize_operation(item) for item in selected_level1_ops],
            "available_count": len(level1_patch.get("operations", [])),
        },
        "level2": {
            "selected_count": len(selected_level2_ops),
            "selected_operations": [summarize_operation(item) for item in selected_level2_ops],
            "available_count": len(level2_patch.get("operations", [])),
        },
        "level3": {
            "selected_count": len(selected_level3_ops),
            "selected_operations": [summarize_operation(item) for item in selected_level3_ops],
            "available_count": len(level3_patch.get("operations", [])),
            "enabled": merged_level3 is not None,
        },
        "companions": {
            "selected_count": len(selected_companions),
            "selected_candidates": [summarize_companion(item) for item in selected_companions],
            "available_count": len(companion_candidates),
            "result": companion_report,
        },
        "overrides": {
            "bundle_count": len(override_bundle.get("overrides", [])),
            "schema_ok": override_schema_report["ok"],
            "resolution_summary": override_resolution_report["summary"],
            "field_conflict_count": len(override_resolution_report.get("field_conflicts", [])),
            "decision_applied_count": len(override_decision_report.get("applied", [])),
            "decision_skipped_count": len(override_decision_report.get("skipped", [])),
        },
        "guarded_write_blocking": guarded_report,
        "validation_ok": validation_report["ok"],
    }

    review_template = {
        "level1_available_operations": [summarize_operation(item) for item in level1_patch.get("operations", [])],
        "level2_available_operations": [summarize_operation(item) for item in level2_patch.get("operations", [])],
        "level3_available_operations": [summarize_operation(item) for item in level3_patch.get("operations", [])],
        "available_companion_candidates": [summarize_companion(item) for item in companion_candidates],
        "override_review": override_review_template,
    }

    write_json(staging_dir / "step6_review_template.json", review_template)
    write_json(staging_dir / "step6_merge_report.json", merge_report)
    write_json(staging_dir / "step6_validation_report.json", validation_report)
    write_json(staging_dir / "step6_override_resolution_report.json", override_resolution_report)
    write_json(staging_dir / "step6_override_conflicts.json", {"conflicts": override_resolution_report.get("field_conflicts", [])})
    write_json(staging_dir / "step6_override_review_template.json", override_review_template)
    write_json(staging_dir / "step6_guarded_write_blocking_report.json", guarded_report)
    write_json(staging_dir / "step6_guarded_write_blocking_blocks.json", {"blocks": guarded_blocks})
    write_json(staging_dir / "step6_overrides.preview.json", override_bundle)
    write_json(staging_dir / "step6_library.preview.json", serialized_library)
    write_json(staging_dir / "step6_level1.preview.json", serialized_level1)
    write_json(staging_dir / "step6_level2.preview.json", serialized_level2)
    if serialized_level3 is not None:
        write_json(staging_dir / "step6_level3.preview.json", serialized_level3)

    if args.guarded_write_blocking_narrow and args.apply_live and guarded_blocks:
        raise SystemExit(
            "Refusing to write live data because the narrow guarded write-blocking gate found blocked overrides or localized companion creation. "
            "Check step6_guarded_write_blocking_report.json and step6_guarded_write_blocking_blocks.json."
        )

    if args.apply_live:
        if not validation_report["ok"]:
            raise SystemExit("Refusing to write live data because Step 6 validation failed. Check step6_validation_report.json.")
        legacy_root = (BASE_DIR.parent / "0.2").resolve()
        live_paths = [library_path, level1_path, level2_path, *([level3_path] if serialized_level3 is not None else [])]
        legacy_targets = all(is_within_path(path, legacy_root) for path in live_paths)
        if legacy_targets and not args.allow_legacy_target:
            raise SystemExit(
                "Refusing to write live data into frozen 0.2 targets. "
                "Point Step 6 at 0.3 or pass --allow-legacy-target if you explicitly need 0.2."
            )
        log("[backup] writing live JSON backups", quiet=args.quiet)
        backup_report = backup_live_files(
            backup_dir=backup_dir,
            paths={
                "overrides": overrides_path,
                "library": library_path,
                "level1": level1_path,
                "level2": level2_path,
                **({"level3": level3_path} if serialized_level3 is not None else {}),
            },
        )
        write_json(staging_dir / "step6_backup_report.json", {"created_at": utc_timestamp(), "backups": backup_report})
        write_rollback_plan_md(
            staging_dir=staging_dir,
            backup_report=backup_report,
            live_paths={
                "overrides": str(overrides_path),
                "library": str(library_path),
                "level1": str(level1_path),
                "level2": str(level2_path),
                **({"level3": str(level3_path)} if serialized_level3 is not None else {}),
            },
            work_id=args.work_id,
        )
        log("[backup] rollback_plan.md written", quiet=args.quiet)
        log("[write] applying merged JSON to live data files", quiet=args.quiet)
        live_writes: list[tuple[Path, Any]] = [
            (overrides_path, override_bundle),
            (library_path, serialized_library),
            (level1_path, serialized_level1),
            (level2_path, serialized_level2),
        ]
        if serialized_level3 is not None:
            live_writes.append((level3_path, serialized_level3))
        write_json_group(live_writes)
        merge_report["live_write_completed"] = True
        merge_report["live_write_completed_at"] = utc_timestamp()
        write_json(staging_dir / "step6_merge_report.json", merge_report)

    log(
        f"[done] validation_ok={validation_report['ok']} library={library_report['merged_entry_count']} "
        f"level1_ops={len(selected_level1_ops)} level2_ops={len(selected_level2_ops)} "
        f"level3_ops={len(selected_level3_ops)} companions={len(selected_companions)}",
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()
