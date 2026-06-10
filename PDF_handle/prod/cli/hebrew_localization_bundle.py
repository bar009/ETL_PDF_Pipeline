from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import ensure_dir, read_json, utc_timestamp, write_json
from PDF_handle.prod.core.site_data import build_site_data_paths
from PDF_handle.prod.core.site_roots import get_work_site_root
from PDF_handle.prod.providers import MalformedProviderPayloadError, generate_json_content
from PDF_handle.prod.schema import normalize_string_array, normalize_text


LOCALIZATION_BUNDLE_VERSION = 1
AUTODRAFT_TEXT_FIELDS = (
    "title",
    "short_summary",
    "candidate_lesson",
    "symbolic_meaning",
)
APPROVED_REVIEW_STATUS = "approved"
PENDING_AUTODRAFT_STATUS = "pending_auto_draft"
TEXT_FIELDS = (
    "title",
    "short_summary",
    "candidate_lesson",
    "symbolic_meaning",
    "why_now",
    "takeaway",
    "definition_line",
    "placement_note",
    "provenance_note",
    "uncertainty_note",
)
LIST_FIELDS = (
    "tradition_notes",
    "caution_notes",
    "source_notes",
)
READING_LAYER_FIELDS = ("basic", "symbolic", "advanced")
HEBREW_CHAR_RE = re.compile(r"[\u0590-\u05FF]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or compile the post-canonical Hebrew localization bundle."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    template = subparsers.add_parser("template", help="Generate a Hebrew localization review template.")
    template.add_argument("--site-root", type=Path, default=None)
    template.add_argument("--report-root", type=Path, default=PDF_HANDLE_ROOT / "runs" / "post_canonical_localization")
    template.add_argument("--report-dir", type=Path, default=None)
    template.add_argument("--degree", action="append", default=[])
    template.add_argument("--slug", action="append", default=[])

    autodraft = subparsers.add_parser(
        "autodraft",
        help="Generate Hebrew localization drafts into review artifacts only.",
    )
    autodraft.add_argument("--site-root", type=Path, default=None)
    autodraft.add_argument("--report-root", type=Path, default=PDF_HANDLE_ROOT / "runs" / "post_canonical_localization")
    autodraft.add_argument("--report-dir", type=Path, default=None)
    autodraft.add_argument("--bundle", type=Path, default=None)
    autodraft.add_argument("--degree", action="append", default=[])
    autodraft.add_argument("--slug", action="append", default=[])
    autodraft.add_argument("--provider", choices=["gemini"], default="gemini")
    autodraft.add_argument("--model", default="gemini-2.5-flash")
    autodraft.add_argument("--api-key-env", default="GEMINI_API_KEY")
    autodraft.add_argument("--thinking-budget", type=int, default=0)
    autodraft.add_argument("--temperature", type=float, default=0.2)
    autodraft.add_argument("--max-output-tokens", type=int, default=1000)

    compile_parser = subparsers.add_parser("compile", help="Compile a reviewed template into a localization bundle.")
    compile_parser.add_argument("--review-file", type=Path, required=True)
    compile_parser.add_argument("--output", type=Path, required=True)

    return parser


def contains_hebrew_text(value: Any) -> bool:
    return bool(HEBREW_CHAR_RE.search(normalize_text(value)))


def build_canonical_key(*, canonical_entry_id: Any, degree: Any, slug: Any) -> str:
    canonical_id = normalize_text(canonical_entry_id)
    if canonical_id:
        return canonical_id
    degree_text = normalize_text(degree)
    slug_text = normalize_text(slug)
    if degree_text and slug_text:
        return f"{degree_text}:{slug_text}"
    return ""


def build_canonical_aliases(*, canonical_entry_id: Any, degree: Any, slug: Any) -> list[str]:
    aliases: list[str] = []
    canonical_id = normalize_text(canonical_entry_id)
    if canonical_id:
        aliases.append(canonical_id)
    degree_text = normalize_text(degree)
    slug_text = normalize_text(slug)
    if degree_text and slug_text:
        aliases.append(f"{degree_text}:{slug_text}")
    return list(dict.fromkeys(alias for alias in aliases if alias))


def build_empty_bundle(site_root: Path) -> dict[str, Any]:
    return {
        "version": LOCALIZATION_BUNDLE_VERSION,
        "locale": "he",
        "site_root": str(site_root.resolve()),
        "created_at": None,
        "updated_at": None,
        "entries": [],
    }


def build_localization_bundle_path(site_root: Path) -> Path:
    return site_root.resolve() / "data" / "content.localizations.he.json"


def iter_site_entries(site_root: Path, selected_degrees: set[str], selected_slugs: set[str]) -> list[dict[str, Any]]:
    site_paths = build_site_data_paths(site_root.resolve())
    results: list[dict[str, Any]] = []
    for degree_id in ("library", "level1", "level2", "level3"):
        degree_path = site_paths.get(degree_id)
        if not degree_path or not degree_path.exists():
            continue
        if selected_degrees and degree_id not in selected_degrees:
            continue
        payload = read_json(degree_path)
        entries = payload.get("entries") if isinstance(payload, dict) else []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            slug = normalize_text(entry.get("slug"))
            if selected_slugs and slug not in selected_slugs:
                continue
            results.append({"degree": degree_id, "entry": entry})
    return results


def build_base_fields(entry: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for field_name in TEXT_FIELDS:
        fields[field_name] = normalize_text(entry.get(field_name))
    for field_name in LIST_FIELDS:
        fields[field_name] = normalize_string_array(entry.get(field_name))
    reading_layers = entry.get("reading_layers") if isinstance(entry.get("reading_layers"), dict) else {}
    fields["reading_layers"] = {
        layer_name: normalize_text(reading_layers.get(layer_name))
        for layer_name in READING_LAYER_FIELDS
    }
    return fields


def build_autodraft_response_schema(field_names: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {field_name: {"type": "string"} for field_name in field_names},
    }


def build_autodraft_system_prompt() -> str:
    return (
        "You create Hebrew localization drafts for a post-canonical display layer. "
        "Translate from finalized English display text into natural, concise Hebrew. "
        "Do not invent facts. Do not add new claims. Preserve meaning and tone. "
        "Keep proper nouns or book titles in English only when that is the clearest display choice. "
        "Return a JSON object only."
    )


def build_autodraft_user_prompt(*, canonical_key: str, degree: str, slug: str, fields: dict[str, str]) -> str:
    lines = [
        "Generate Hebrew localization drafts for the following canonical entry.",
        f"canonical_key: {canonical_key}",
        f"degree: {degree}",
        f"slug: {slug}",
        "",
        "Translate only the provided fields. Omit missing fields. Return JSON only.",
        "",
    ]
    for field_name, value in fields.items():
        lines.append(f"{field_name}: {value}")
    return "\n".join(lines)


def load_existing_localization_fields(bundle_path: Path) -> dict[str, dict[str, Any]]:
    if not bundle_path.exists():
        return {}
    payload = read_json(bundle_path)
    entries = payload.get("entries") if isinstance(payload, dict) else []
    results: dict[str, dict[str, Any]] = {}
    for item in entries if isinstance(entries, list) else []:
        if not isinstance(item, dict):
            continue
        if not is_localization_entry_approved(item):
            continue
        aliases = build_canonical_aliases(
            canonical_entry_id=item.get("canonical_entry_id"),
            degree=item.get("degree"),
            slug=item.get("slug"),
        )
        canonical_key = normalize_text(item.get("canonical_key"))
        if canonical_key:
            aliases = [canonical_key, *aliases]
        aliases = list(dict.fromkeys(alias for alias in aliases if alias))
        if not aliases:
            continue
        normalized_fields = normalize_localized_fields(item.get("fields"))
        for alias in aliases:
            results[alias] = normalized_fields
    return results


def normalize_review_status(value: Any) -> str:
    return normalize_text(value).strip().lower()


def is_localization_entry_approved(item: Any) -> bool:
    provenance = item.get("provenance") if isinstance(item, dict) else {}
    if not isinstance(provenance, dict):
        return False
    return normalize_review_status(provenance.get("review_status")) == APPROVED_REVIEW_STATUS


def classify_autodraft_source_entry(entry: dict[str, Any]) -> str | None:
    if normalize_review_status(entry.get("language")) != "en":
        return "non_english_language"
    if normalize_text(entry.get("translation_mode")):
        return "translation_mode"
    for field_name in AUTODRAFT_TEXT_FIELDS:
        if contains_hebrew_text(entry.get(field_name)):
            return "mixed_language_source"
    return None


def build_autodraft_field_reviews(
    *,
    base_fields: dict[str, Any],
    drafted_fields: dict[str, str],
    generated_at: str,
) -> dict[str, Any]:
    field_reviews: dict[str, Any] = {}
    for field_name, draft_value in drafted_fields.items():
        if not draft_value:
            continue
        field_reviews[field_name] = {
            "base_value": normalize_text(base_fields.get(field_name)),
            "draft_value": draft_value,
            "status": PENDING_AUTODRAFT_STATUS,
            "review_note": "",
            "generated_at": generated_at,
        }
    return field_reviews


def extract_approved_field_reviews(payload: Any) -> dict[str, Any]:
    field_reviews = payload if isinstance(payload, dict) else {}
    approved: dict[str, Any] = {}
    for field_name, review in field_reviews.items():
        if not isinstance(review, dict):
            continue
        if normalize_review_status(review.get("status")) != APPROVED_REVIEW_STATUS:
            continue
        value = (
            normalize_text(review.get("final_value"))
            or normalize_text(review.get("reviewed_value"))
            or normalize_text(review.get("draft_value"))
        )
        if value:
            approved[field_name] = value
    return approved


def build_template_entry(*, degree: str, entry: dict[str, Any]) -> dict[str, Any]:
    canonical_key = build_canonical_key(
        canonical_entry_id=entry.get("canonical_entry_id"),
        degree=degree,
        slug=entry.get("slug"),
    )
    return {
        "canonical_key": canonical_key,
        "canonical_entry_id": normalize_text(entry.get("canonical_entry_id")) or None,
        "degree": degree,
        "slug": normalize_text(entry.get("slug")),
        "base_fields": build_base_fields(entry),
        "localized_fields": {},
        "review": {
            "status": "pending",
            "note": "",
        },
    }


def command_template(args: argparse.Namespace) -> None:
    site_root = args.site_root.resolve()
    report_dir = ensure_dir(
        args.report_dir.resolve()
        if args.report_dir
        else (args.report_root.resolve() / utc_timestamp().replace(":", "-"))
    )
    selected_degrees = {normalize_text(value) for value in args.degree if normalize_text(value)}
    selected_slugs = {normalize_text(value) for value in args.slug if normalize_text(value)}
    entries = [
        build_template_entry(degree=item["degree"], entry=item["entry"])
        for item in iter_site_entries(site_root, selected_degrees, selected_slugs)
    ]
    payload = {
        "version": LOCALIZATION_BUNDLE_VERSION,
        "locale": "he",
        "site_root": str(site_root),
        "generated_at": utc_timestamp(),
        "localizable_fields": {
            "text": list(TEXT_FIELDS),
            "list": list(LIST_FIELDS),
            "reading_layers": list(READING_LAYER_FIELDS),
        },
        "entries": entries,
    }
    write_json(report_dir / "hebrew_localization_review_template.json", payload)
    print(f"[done] localization review template written to {report_dir}", flush=True)


def command_autodraft(args: argparse.Namespace) -> None:
    site_root = args.site_root.resolve()
    report_dir = ensure_dir(
        args.report_dir.resolve()
        if args.report_dir
        else (args.report_root.resolve() / utc_timestamp().replace(":", "-"))
    )
    selected_degrees = {normalize_text(value) for value in args.degree if normalize_text(value)}
    selected_slugs = {normalize_text(value) for value in args.slug if normalize_text(value)}
    bundle_path = args.bundle.resolve() if args.bundle else build_localization_bundle_path(site_root)
    existing_fields_by_key = load_existing_localization_fields(bundle_path)
    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise SystemExit(f"Autodraft requires {args.api_key_env} to be set.")

    generated_at = utc_timestamp()
    review_entries: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "version": LOCALIZATION_BUNDLE_VERSION,
        "locale": "he",
        "generated_at": generated_at,
        "site_root": str(site_root),
        "bundle_path": str(bundle_path),
        "provider": args.provider,
        "model": args.model,
        "autodraft_fields": list(AUTODRAFT_TEXT_FIELDS),
        "selected_degrees": sorted(selected_degrees),
        "selected_slugs": sorted(selected_slugs),
        "counts": {
            "entries_seen": 0,
            "entries_drafted": 0,
            "entries_skipped_non_english": 0,
            "entries_skipped_translation_mode": 0,
            "entries_skipped_mixed_language": 0,
            "entries_skipped_existing": 0,
            "entries_failed": 0,
            "fields_requested": 0,
            "fields_drafted": 0,
        },
        "failures": [],
    }

    for item in iter_site_entries(site_root, selected_degrees, selected_slugs):
        degree = item["degree"]
        entry = item["entry"]
        summary["counts"]["entries_seen"] += 1
        skip_reason = classify_autodraft_source_entry(entry)
        if skip_reason == "non_english_language":
            summary["counts"]["entries_skipped_non_english"] += 1
            continue
        if skip_reason == "translation_mode":
            summary["counts"]["entries_skipped_translation_mode"] += 1
            continue
        if skip_reason == "mixed_language_source":
            summary["counts"]["entries_skipped_mixed_language"] += 1
            continue

        template_entry = build_template_entry(degree=degree, entry=entry)
        canonical_key = template_entry["canonical_key"]
        if not canonical_key:
            summary["counts"]["entries_failed"] += 1
            summary["failures"].append(
                {
                    "degree": degree,
                    "slug": template_entry["slug"],
                    "reason": "missing_canonical_key",
                }
            )
            continue

        existing_fields: dict[str, Any] = {}
        for alias in build_canonical_aliases(
            canonical_entry_id=template_entry["canonical_entry_id"],
            degree=degree,
            slug=template_entry["slug"],
        ):
            existing_fields = existing_fields_by_key.get(alias, {})
            if existing_fields:
                break
        fields_to_translate = {
            field_name: template_entry["base_fields"].get(field_name, "")
            for field_name in AUTODRAFT_TEXT_FIELDS
            if normalize_text(template_entry["base_fields"].get(field_name))
            and not normalize_text(existing_fields.get(field_name))
        }
        if not fields_to_translate:
            summary["counts"]["entries_skipped_existing"] += 1
            continue

        summary["counts"]["fields_requested"] += len(fields_to_translate)
        try:
            result = generate_json_content(
                system_prompt=build_autodraft_system_prompt(),
                user_prompt=build_autodraft_user_prompt(
                    canonical_key=canonical_key,
                    degree=degree,
                    slug=template_entry["slug"],
                    fields=fields_to_translate,
                ),
                model=args.model,
                temperature=args.temperature,
                max_output_tokens=args.max_output_tokens,
                api_key=api_key,
                thinking_budget=args.thinking_budget,
                response_mime_type="application/json",
                response_schema=build_autodraft_response_schema(tuple(fields_to_translate.keys())),
            )
        except (RuntimeError, MalformedProviderPayloadError) as exc:
            summary["counts"]["entries_failed"] += 1
            summary["failures"].append(
                {
                    "canonical_key": canonical_key,
                    "degree": degree,
                    "slug": template_entry["slug"],
                    "reason": str(exc),
                }
            )
            continue

        drafted_fields = {
            field_name: normalize_text((result.get("payload") or {}).get(field_name))
            for field_name in fields_to_translate
        }
        drafted_fields = {field_name: value for field_name, value in drafted_fields.items() if value}
        if not drafted_fields:
            summary["counts"]["entries_failed"] += 1
            summary["failures"].append(
                {
                    "canonical_key": canonical_key,
                    "degree": degree,
                    "slug": template_entry["slug"],
                    "reason": "provider_returned_no_draft_fields",
                }
            )
            continue

        summary["counts"]["entries_drafted"] += 1
        summary["counts"]["fields_drafted"] += len(drafted_fields)
        review_entries.append(
            {
                **template_entry,
                "localized_fields": {},
                "localized_fields_draft": drafted_fields,
                "field_reviews": build_autodraft_field_reviews(
                    base_fields=template_entry["base_fields"],
                    drafted_fields=drafted_fields,
                    generated_at=generated_at,
                ),
                "existing_localized_fields": existing_fields,
                "review": {
                    "status": PENDING_AUTODRAFT_STATUS,
                    "note": "Auto-generated Hebrew draft. Review and approve fields individually before compile.",
                },
                "autodraft": {
                    "provider": args.provider,
                    "model": args.model,
                    "transport": result.get("transport"),
                    "usage_metadata": result.get("usage_metadata"),
                    "generated_at": generated_at,
                    "requested_fields": list(fields_to_translate.keys()),
                },
            }
        )

    review_payload = {
        "version": LOCALIZATION_BUNDLE_VERSION,
        "locale": "he",
        "site_root": str(site_root),
        "generated_at": generated_at,
        "autodraft_fields": list(AUTODRAFT_TEXT_FIELDS),
        "entries": review_entries,
    }
    write_json(report_dir / "hebrew_localization_autodraft_review.json", review_payload)
    write_json(report_dir / "hebrew_localization_autodraft_summary.json", summary)
    print(f"[done] localization autodraft artifacts written to {report_dir}", flush=True)


def normalize_localized_fields(payload: Any) -> dict[str, Any]:
    fields_payload = payload if isinstance(payload, dict) else {}
    normalized: dict[str, Any] = {}
    for field_name in TEXT_FIELDS:
        if field_name in fields_payload:
            text = normalize_text(fields_payload.get(field_name))
            if text:
                normalized[field_name] = text
    for field_name in LIST_FIELDS:
        if field_name in fields_payload:
            values = normalize_string_array(fields_payload.get(field_name))
            if values:
                normalized[field_name] = values
    reading_layers_payload = fields_payload.get("reading_layers") if isinstance(fields_payload.get("reading_layers"), dict) else {}
    reading_layers = {
        layer_name: normalize_text(reading_layers_payload.get(layer_name))
        for layer_name in READING_LAYER_FIELDS
        if normalize_text(reading_layers_payload.get(layer_name))
    }
    if reading_layers:
        normalized["reading_layers"] = reading_layers
    return normalized


def command_compile(args: argparse.Namespace) -> None:
    review_payload = read_json(args.review_file.resolve())
    entries = review_payload.get("entries") if isinstance(review_payload, dict) else []
    site_root = Path(review_payload.get("site_root") or get_work_site_root()).resolve()
    bundle = build_empty_bundle(site_root)
    bundle["created_at"] = utc_timestamp()
    bundle["updated_at"] = bundle["created_at"]

    compiled_entries: list[dict[str, Any]] = []
    for item in entries if isinstance(entries, list) else []:
        if not isinstance(item, dict):
            continue
        canonical_key = normalize_text(item.get("canonical_key"))
        degree = normalize_text(item.get("degree"))
        slug = normalize_text(item.get("slug"))
        canonical_entry_id = normalize_text(item.get("canonical_entry_id")) or None
        if not canonical_key:
            canonical_key = build_canonical_key(
                canonical_entry_id=canonical_entry_id,
                degree=degree,
                slug=slug,
            )
        if not canonical_key:
            continue
        review = item.get("review") if isinstance(item.get("review"), dict) else {}
        review_status = normalize_review_status(review.get("status"))
        fields = extract_approved_field_reviews(item.get("field_reviews"))
        if not fields:
            if review_status != APPROVED_REVIEW_STATUS:
                continue
            fields = normalize_localized_fields(item.get("localized_fields"))
        if not fields:
            continue
        compiled_entries.append(
            {
                "canonical_key": canonical_key,
                "canonical_entry_id": canonical_entry_id,
                "degree": degree or None,
                "slug": slug or None,
                "fields": fields,
                "provenance": {
                    "source": "reviewed_template",
                    "review_status": APPROVED_REVIEW_STATUS,
                    "note": normalize_text(review.get("note")) or None,
                    "compiled_at": bundle["updated_at"],
                },
            }
        )

    bundle["entries"] = compiled_entries
    write_json(args.output.resolve(), bundle)
    print(f"[done] localization bundle written to {args.output.resolve()}", flush=True)


def main() -> None:
    args = build_parser().parse_args()
    if getattr(args, "site_root", None) is None:
        args.site_root = get_work_site_root()
    if args.command == "template":
        command_template(args)
        return
    if args.command == "autodraft":
        command_autodraft(args)
        return
    if args.command == "compile":
        command_compile(args)
        return
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
