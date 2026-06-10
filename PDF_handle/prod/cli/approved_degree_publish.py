from __future__ import annotations

import argparse
import copy
import hashlib
import re
import shutil
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
from PDF_handle.prod.core.site_data import build_site_data_paths, build_site_data_stat_signatures
from PDF_handle.prod.core.site_roots import get_work_site_root
from PDF_handle.prod.schema.data import (
    normalize_degree_data,
    serialize_degree_data,
    validate_against_schema,
    validate_degree_references,
)


DEGREES = ("library", "level1", "level2", "level3")
PUBLISHABLE_DEGREES = ("level1", "level2", "level3")
SLUG_RE = re.compile(r"[^a-z0-9]+")
COMPOUND_TITLE_RE = re.compile(r"\b(and|,)\b", re.IGNORECASE)
CITATION_TOKEN_RE = re.compile(r"\[(?:cite|citation)[^\]]*\]", re.IGNORECASE)
LEVEL3_PUBLISHABLE_CATEGORIES = (
    "degree_structure",
    "hiram_and_raising",
    "mortality_and_memorial",
    "symbolic_field",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build, preview, or apply approved-only degree entries from approved_degree_publish_input.json. "
            "This never reads rejected candidates and can only apply to an explicit work root."
        )
    )
    parser.add_argument("--approved-input", type=Path, required=True)
    parser.add_argument("--site-root", type=Path, default=get_work_site_root())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=["sanity", "preview", "apply"], default="sanity")
    parser.add_argument("--allow-non-empty-degree-files", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def clean_user_facing_text(value: Any) -> str:
    text = CITATION_TOKEN_RE.sub("", normalize_text(value))
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def slugify(value: Any) -> str:
    text = normalize_text(value).lower()
    text = text.replace("&", " and ")
    text = SLUG_RE.sub("-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "approved-topic"


def short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]


def unique_slug(base_slug: str, used_slugs: set[str], stable_key: str) -> str:
    slug = base_slug
    if slug not in used_slugs:
        used_slugs.add(slug)
        return slug
    slug = f"{base_slug}-{short_hash(stable_key)}"
    counter = 2
    while slug in used_slugs:
        slug = f"{base_slug}-{short_hash(stable_key)}-{counter}"
        counter += 1
    used_slugs.add(slug)
    return slug


def load_site_datasets(site_root: Path) -> dict[str, dict[str, Any]]:
    site_paths = build_site_data_paths(site_root.resolve())
    datasets: dict[str, dict[str, Any]] = {}
    for degree in DEGREES:
        path = site_paths.get(degree)
        if not path or not path.exists():
            continue
        datasets[degree] = normalize_degree_data(read_json(path), degree)
    return datasets


def load_approved_candidates(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path.resolve())
    candidates = payload.get("approved_candidates") if isinstance(payload, dict) else []
    return [item for item in candidates if isinstance(item, dict)] if isinstance(candidates, list) else []


def source_library_index(library_dataset: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["slug"]: entry for entry in library_dataset.get("entries", []) if normalize_text(entry.get("slug"))}


def choose_category(degree: str, title: str, categories: dict[str, Any], approved_category: str = "") -> str:
    title_l = title.lower()
    if degree == "level1":
        if any(token in title_l for token in ("working tools", "lambskin", "apron")):
            return "tools_and_signs" if "tools_and_signs" in categories else next(iter(categories))
        if any(token in title_l for token in ("furniture", "ornaments", "jewels", "covering", "lodge")):
            return "degree_board" if "degree_board" in categories else next(iter(categories))
        if any(token in title_l for token in ("prudence", "charge", "chalk", "charcoal", "clay")):
            return "inner_work" if "inner_work" in categories else next(iter(categories))
        return "inner_work" if "inner_work" in categories else next(iter(categories))
    if degree == "level2":
        return "philosophy" if "philosophy" in categories else next(iter(categories))
    if degree == "level3":
        if approved_category in LEVEL3_PUBLISHABLE_CATEGORIES and approved_category in categories:
            return approved_category
        for category in LEVEL3_PUBLISHABLE_CATEGORIES:
            if category in categories:
                return category
        return next(iter(categories))
    return next(iter(categories))


def build_short_summary(candidate: dict[str, Any]) -> str:
    evidence = normalize_text(candidate.get("decision_evidence", {}).get("confidence"))
    reason = normalize_text(candidate.get("review_reason"))
    if reason:
        return clean_user_facing_text(reason.split("|")[0])[:280]
    if evidence:
        return f"Review-approved degree topic with {evidence} confidence."
    return "Review-approved degree topic from the v20r1 discovery lane."


def build_full_summary(candidate: dict[str, Any], source_entry: dict[str, Any] | None) -> str:
    title = normalize_text(candidate.get("approved_title"))
    degree = normalize_text(candidate.get("approved_degree"))
    review_reason = normalize_text(candidate.get("review_reason"))
    source_excerpt = normalize_text(candidate.get("source_excerpt"))
    source_slug = normalize_text(candidate.get("source_chapter_slug"))
    lines = [
        f"# {title}",
        "",
        f"NotebookLM-assisted review approved this as a `{degree}` teaching topic.",
    ]
    if review_reason:
        lines.extend(["", "Review reason:", review_reason])
    if source_slug:
        lines.extend(["", f"Source library chapter: `{source_slug}`"])
    if source_entry:
        lines.extend(["", f"Source work: {normalize_text(source_entry.get('work_title')) or normalize_text(candidate.get('work_id'))}"])
    if source_excerpt:
        lines.extend(["", "Source excerpt:", source_excerpt])
    return "\n".join(lines).strip()


def build_degree_entry(
    candidate: dict[str, Any],
    *,
    datasets: dict[str, dict[str, Any]],
    source_entries: dict[str, dict[str, Any]],
    used_slugs: set[str],
) -> dict[str, Any]:
    degree = normalize_text(candidate.get("approved_degree"))
    approved_category = normalize_text(candidate.get("approved_category"))
    title = normalize_text(candidate.get("approved_title"))
    source_slug = normalize_text(candidate.get("source_chapter_slug"))
    source_entry = source_entries.get(source_slug)
    slug = unique_slug(slugify(title), used_slugs, normalize_text(candidate.get("candidate_id")))
    category = choose_category(degree, title, datasets[degree]["categories"], approved_category)
    source_notes = []
    for note in candidate.get("source_notes", []):
        text = normalize_text(note)
        if text:
            source_notes.append(text)
    source_notes.append(f"Review candidate: {candidate.get('candidate_id')}")
    if source_slug:
        source_notes.append(f"Source library chapter: {source_slug}")

    entry = {
        "title": title,
        "slug": slug,
        "type": "topic",
        "degree": degree,
        "applies_to_degrees": [degree],
        "category": category,
        "parent_topic": None,
        "aliases": [],
        "keywords": [slugify(part) for part in re.split(r"\s+and\s+|,\s*", title.lower()) if slugify(part)][:8],
        "related_topics": {"prior": [], "companion": [], "deeper": []},
        "short_summary": build_short_summary(candidate),
        "full_summary": build_full_summary(candidate, source_entry),
        "practical_elements": [],
        "symbolic_meaning": "",
        "candidate_lesson": "Read this topic through the linked source excerpt before treating it as final instruction.",
        "tradition_notes": [],
        "caution_notes": [
            "NotebookLM-assisted placement; keep source-grounded review visible before public release.",
        ],
        "source_notes": source_notes,
        "language": "en",
        "work_id": normalize_text(candidate.get("work_id")) or None,
        "work_title": normalize_text(source_entry.get("work_title")) if source_entry else "",
        "source_kind": normalize_text(source_entry.get("source_kind")) if source_entry else "review-approved-topic",
        "source_path": source_entry.get("source_path") if source_entry else None,
        "source_anchor": source_entry.get("source_anchor") if source_entry else None,
        "source_heading": normalize_text(source_entry.get("source_heading")) if source_entry else None,
        "source_order": source_entry.get("source_order") if source_entry else None,
        "parallel_entry": None,
        "translation_mode": None,
        "canonical_entry_id": f"{degree}:{slug}",
        "source_language": "en",
        "canonical_language": "en",
        "display_language": "en",
        "localization_group_id": f"{degree}:{slug}",
        "available_locales": ["en"],
        "translation_status": "source",
        "language_integrity_status": "legacy",
        "knowledge_links": [{"degree": "library", "slug": source_slug}] if source_slug else [],
        "chapter_toc": [],
        "visibility_level": "internal",
        "sensitivity_level": "guarded",
        "tradition_scope": "variant",
        "status": "reviewed",
        "review_metadata": {
            "candidate_id": candidate.get("candidate_id"),
            "review_reason": candidate.get("review_reason"),
            "decision_evidence": candidate.get("decision_evidence", {}),
        },
    }
    return entry


def build_sanity_report(
    *,
    candidates: list[dict[str, Any]],
    datasets: dict[str, dict[str, Any]],
    source_entries: dict[str, dict[str, Any]],
    allow_non_empty_degree_files: bool,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    titles_by_degree: Counter[tuple[str, str]] = Counter()
    slugs_by_degree: Counter[tuple[str, str]] = Counter()

    for degree in PUBLISHABLE_DEGREES:
        if degree not in datasets:
            blockers.append({"code": "MISSING_TARGET_DEGREE_DATASET", "degree": degree})
            continue
        entry_count = len(datasets[degree].get("entries", []))
        if entry_count and not allow_non_empty_degree_files:
            blockers.append({"code": "TARGET_DEGREE_DATASET_NOT_EMPTY", "degree": degree, "entry_count": entry_count})

    for candidate in candidates:
        candidate_id = normalize_text(candidate.get("candidate_id"))
        title = normalize_text(candidate.get("approved_title"))
        degree = normalize_text(candidate.get("approved_degree"))
        approved_category = normalize_text(candidate.get("approved_category"))
        source_slug = normalize_text(candidate.get("source_chapter_slug"))
        if not candidate_id:
            blockers.append({"code": "APPROVED_CANDIDATE_MISSING_ID", "candidate": candidate})
        if degree not in PUBLISHABLE_DEGREES:
            blockers.append({"code": "APPROVED_CANDIDATE_BAD_DEGREE", "candidate_id": candidate_id, "degree": degree})
        elif degree == "level3":
            categories = datasets.get("level3", {}).get("categories", {})
            if not approved_category:
                blockers.append({"code": "APPROVED_LEVEL3_CANDIDATE_MISSING_CATEGORY", "candidate_id": candidate_id})
            elif approved_category == "gate":
                blockers.append({"code": "APPROVED_LEVEL3_CANDIDATE_USES_GATE_CATEGORY", "candidate_id": candidate_id})
            elif approved_category not in LEVEL3_PUBLISHABLE_CATEGORIES:
                blockers.append(
                    {
                        "code": "APPROVED_LEVEL3_CANDIDATE_BAD_CATEGORY",
                        "candidate_id": candidate_id,
                        "approved_category": approved_category,
                        "allowed_categories": list(LEVEL3_PUBLISHABLE_CATEGORIES),
                    }
                )
            elif approved_category not in categories:
                blockers.append(
                    {
                        "code": "APPROVED_LEVEL3_CATEGORY_NOT_IN_TARGET_DATASET",
                        "candidate_id": candidate_id,
                        "approved_category": approved_category,
                    }
                )
        if not title:
            blockers.append({"code": "APPROVED_CANDIDATE_MISSING_TITLE", "candidate_id": candidate_id})
        if not source_slug or source_slug not in source_entries:
            blockers.append({"code": "APPROVED_CANDIDATE_SOURCE_NOT_FOUND", "candidate_id": candidate_id, "source_slug": source_slug})
        if not normalize_text(candidate.get("source_excerpt")):
            blockers.append({"code": "APPROVED_CANDIDATE_MISSING_EXCERPT", "candidate_id": candidate_id})
        if COMPOUND_TITLE_RE.search(title) and len(title.split()) > 4:
            warnings.append({"code": "APPROVED_TITLE_MAY_BE_COMPOUND", "candidate_id": candidate_id, "title": title})
        if title:
            titles_by_degree[(degree, title.lower())] += 1
            slugs_by_degree[(degree, slugify(title))] += 1

    for (degree, title), count in titles_by_degree.items():
        if count > 1:
            blockers.append({"code": "DUPLICATE_APPROVED_TITLE", "degree": degree, "title": title, "count": count})
    for (degree, slug), count in slugs_by_degree.items():
        if count > 1:
            warnings.append({"code": "DUPLICATE_GENERATED_BASE_SLUG_WILL_BE_HASHED", "degree": degree, "slug": slug, "count": count})

    return {
        "status": "fail" if blockers else "pass_with_warnings" if warnings else "pass",
        "approved_count": len(candidates),
        "approved_by_degree": dict(sorted(Counter(normalize_text(item.get("approved_degree")) for item in candidates).items())),
        "approved_level3_by_category": dict(
            sorted(
                Counter(
                    normalize_text(item.get("approved_category")) or "missing"
                    for item in candidates
                    if normalize_text(item.get("approved_degree")) == "level3"
                ).items()
            )
        ),
        "blockers": blockers,
        "warnings": warnings,
    }


def build_preview(
    *,
    candidates: list[dict[str, Any]],
    datasets: dict[str, dict[str, Any]],
    source_entries: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    preview = {degree: copy.deepcopy(dataset) for degree, dataset in datasets.items()}
    created_entries: list[dict[str, Any]] = []
    used_slugs_by_degree = {
        degree: {entry["slug"] for entry in preview[degree].get("entries", [])}
        for degree in PUBLISHABLE_DEGREES
        if degree in preview
    }
    for candidate in candidates:
        degree = normalize_text(candidate.get("approved_degree"))
        if degree not in PUBLISHABLE_DEGREES:
            continue
        entry = build_degree_entry(
            candidate,
            datasets=preview,
            source_entries=source_entries,
            used_slugs=used_slugs_by_degree[degree],
        )
        preview[degree]["entries"].append(entry)
        preview[degree] = normalize_degree_data(serialize_degree_data(preview[degree]), degree)
        created_entries.append(entry)
    return preview, created_entries


def validate_preview(preview: dict[str, dict[str, Any]], schema_path: Path) -> dict[str, Any]:
    degree_results = {
        degree: validate_against_schema(serialize_degree_data(preview[degree]), schema_path)
        for degree in PUBLISHABLE_DEGREES
        if degree in preview
    }
    reference_result = validate_degree_references({degree: preview[degree] for degree in DEGREES if degree in preview})
    ok = all(result["ok"] for result in degree_results.values()) and reference_result["ok"]
    return {
        "ok": ok,
        "degrees": degree_results,
        "references": reference_result,
    }


def write_preview_outputs(output_dir: Path, preview: dict[str, dict[str, Any]], created_entries: list[dict[str, Any]]) -> None:
    preview_dir = ensure_dir(output_dir / "preview")
    for degree in PUBLISHABLE_DEGREES:
        if degree in preview:
            write_json(preview_dir / f"{degree}.preview.json", serialize_degree_data(preview[degree]))
    write_json(output_dir / "approved_degree_entries.generated.json", created_entries)


def apply_preview(site_root: Path, output_dir: Path, preview: dict[str, dict[str, Any]]) -> dict[str, Any]:
    site_paths = build_site_data_paths(site_root.resolve())
    backup_dir = ensure_dir(output_dir / "backups")
    backup_paths: dict[str, str] = {}
    for degree in PUBLISHABLE_DEGREES:
        source_path = site_paths[degree]
        backup_path = backup_dir / f"{degree}.before-approved-publish.json"
        shutil.copy2(source_path, backup_path)
        backup_paths[degree] = str(backup_path)
    for degree in PUBLISHABLE_DEGREES:
        write_json(site_paths[degree], serialize_degree_data(preview[degree]))
    return {
        "site_root": str(site_root.resolve()),
        "backup_paths": backup_paths,
        "written_degrees": list(PUBLISHABLE_DEGREES),
    }


def render_summary(report: dict[str, Any]) -> str:
    lines = [
        "# Approved Degree Publish Report",
        "",
        f"- Mode: `{report['mode']}`",
        f"- Status: `{report['status']}`",
        f"- Approved candidates: `{report['sanity']['approved_count']}`",
        f"- Blockers: `{len(report['sanity']['blockers'])}`",
        f"- Warnings: `{len(report['sanity']['warnings'])}`",
        "",
        "## Approved By Degree",
        "",
    ]
    for degree, count in report["sanity"]["approved_by_degree"].items():
        lines.append(f"- `{degree}`: {count}")
    if report["sanity"].get("approved_level3_by_category"):
        lines.extend(["", "## Approved Level3 By Category", ""])
        for category, count in report["sanity"]["approved_level3_by_category"].items():
            lines.append(f"- `{category}`: {count}")
    if report["sanity"]["blockers"]:
        lines.extend(["", "## Blockers", ""])
        for item in report["sanity"]["blockers"]:
            lines.append(f"- `{item.get('code')}` {item}")
    if report["sanity"]["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for item in report["sanity"]["warnings"]:
            lines.append(f"- `{item.get('code')}` {item}")
    if report.get("created_entries"):
        lines.extend(["", "## Created Entries", ""])
        for entry in report["created_entries"]:
            lines.append(f"- `{entry['degree']}` / `{entry['slug']}`: {entry['title']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = build_parser().parse_args()
    site_root = args.site_root.resolve()
    output_dir = ensure_dir(args.output_dir.resolve())
    site_paths = build_site_data_paths(site_root)
    datasets = load_site_datasets(site_root)
    candidates = load_approved_candidates(args.approved_input)
    source_entries = source_library_index(datasets["library"])

    sanity = build_sanity_report(
        candidates=candidates,
        datasets=datasets,
        source_entries=source_entries,
        allow_non_empty_degree_files=args.allow_non_empty_degree_files,
    )
    preview, created_entries = build_preview(candidates=candidates, datasets=datasets, source_entries=source_entries)
    validation = validate_preview(preview, site_paths["schema"])
    if not validation["ok"]:
        sanity["blockers"].append({"code": "PREVIEW_VALIDATION_FAILED", "validation": validation})
        sanity["status"] = "fail"

    report = {
        "created_at": utc_timestamp(),
        "mode": args.mode,
        "site_root": str(site_root),
        "approved_input": str(args.approved_input.resolve()),
        "fingerprints_before": build_site_data_stat_signatures(site_paths),
        "sanity": sanity,
        "validation": validation,
        "status": sanity["status"],
        "created_entries": [
            {"degree": entry["degree"], "category": entry.get("category"), "slug": entry["slug"], "title": entry["title"]}
            for entry in created_entries
        ],
    }

    write_preview_outputs(output_dir, preview, created_entries)

    if args.mode == "apply":
        if sanity["status"] == "fail":
            report["apply"] = {"ok": False, "reason": "sanity_failed"}
        elif not str(site_root).startswith(str(REPO_ROOT / "sites" / "work")):
            report["apply"] = {"ok": False, "reason": "target_site_root_not_v2_work"}
            report["status"] = "fail"
        else:
            report["apply"] = apply_preview(site_root, output_dir, preview)
            report["fingerprints_after"] = build_site_data_stat_signatures(site_paths)

    write_json(output_dir / "approved_degree_publish_report.json", report)
    write_text(output_dir / "approved_degree_publish_summary.md", render_summary(report))
    print(
        "[done] approved degree publish "
        f"mode={args.mode} status={report['status']} approved={sanity['approved_count']} "
        f"report={output_dir / 'approved_degree_publish_report.json'}",
        flush=True,
    )
    if args.strict and report["status"] == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
