"""encyclopedia_proposals_apply.py

Apply review decisions with review_action=encyclopedia into the site's encyclopedia.json.

Usage:
    # Preview (no writes):
    python PDF_handle/prod/cli/encyclopedia_proposals_apply.py \
        --review-file PDF_handle/runs/v21r1-e1/review_queue/candidate_review_queue.json \
        --site-root sites/work/v0.5 \
        --output-dir PDF_handle/runs/v21r1-e1/apply_reports

    # Write:
    python PDF_handle/prod/cli/encyclopedia_proposals_apply.py \
        --review-file PDF_handle/runs/v21r1-e1/review_queue/candidate_review_queue.json \
        --site-root sites/work/v0.5 \
        --output-dir PDF_handle/runs/v21r1-e1/apply_reports \
        --write
"""

from __future__ import annotations

import argparse
import copy
import re
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
from PDF_handle.prod.core.site_roots import get_work_site_root
from PDF_handle.prod.core.text import enc_canonical_slug


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SLUG_RE = re.compile(r"[^a-z0-9]+")

KNOWN_LANES = frozenset(
    {
        "encyclopedia_foundational",
        "encyclopedia_glossary",
        "encyclopedia_history",
        "encyclopedia_officers_governance",
        "encyclopedia_ritual_reference",
        "encyclopedia_symbols_tools",
        "encyclopedia_overview",
        "encyclopedia_pending",
        "encyclopedia_higher_degrees_reference",
    }
)

LANE_DESCRIPTION_TEMPLATES: dict[str, str] = {
    "encyclopedia_foundational": "{title} — Masonic moral principle",
    "encyclopedia_glossary": "{title} — Masonic definition and terminology",
    "encyclopedia_history": "{title} — historical figure or document in Masonic history",
    "encyclopedia_officers_governance": "{title} — lodge officer or governance procedure",
    "encyclopedia_ritual_reference": "{title} — lodge ritual element",
    "encyclopedia_symbols_tools": "{title} — Masonic symbol or working tool",
    "encyclopedia_overview": "{title} — overview and survey entry",
    "encyclopedia_higher_degrees_reference": "{title} — reference to higher degrees",
    "encyclopedia_pending": "{title} — pending editorial classification",
}

SOURCE_EXCERPT_LIMIT = 600


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Apply encyclopedia proposals (review_action=encyclopedia) from a review decisions file "
            "into sites/work/<version>/data/encyclopedia.json. "
            "Default mode is preview — pass --write to commit changes."
        )
    )
    parser.add_argument(
        "--review-file",
        type=Path,
        required=True,
        help=(
            "Path to the filled review decisions file. Accepts: "
            "(1) the full candidate_review_queue.json produced by candidate_review_queue_export.py, "
            "(2) a standalone review_decisions.json with a top-level 'decisions' list, "
            "or (3) a bare JSON array of decision objects."
        ),
    )
    parser.add_argument(
        "--site-root",
        type=Path,
        default=None,
        help="Root of the site directory containing data/encyclopedia.json.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Label stored in the updated encyclopedia.json run_id field. Defaults to a timestamp.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for the apply report. Defaults to <review_file_parent>/apply_reports.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the updated encyclopedia.json. Without this flag the tool runs in preview mode only.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any proposals are skipped due to errors.",
    )
    return parser


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def to_display_title(raw: str) -> str:
    """Title-case the string only if it is entirely upper-case; otherwise preserve."""
    text = raw.strip()
    if not text:
        return text
    # All-caps heuristic: every alphabetic character is uppercase
    alpha_chars = [c for c in text if c.isalpha()]
    if alpha_chars and all(c.isupper() for c in alpha_chars):
        return text.title()
    return text


def enc_slug(title: str) -> str:
    """Produce a stable 'enc-<kebab>' slug using canonical normalization."""
    return enc_canonical_slug(title)


def auto_description(title: str, lane: str) -> str:
    template = LANE_DESCRIPTION_TEMPLATES.get(lane, "{title}")
    return template.format(title=title)


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------


def load_review_decisions(path: Path) -> list[dict[str, Any]]:
    """
    Accept several review-file shapes:
      - Full candidate_review_queue.json  → review_decision_template.decisions[]
      - Bare review_decisions.json        → decisions[]
      - JSON array                        → list directly
    """
    payload = read_json(path.resolve())
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        # Full queue export
        tmpl = payload.get("review_decision_template")
        if isinstance(tmpl, dict) and "decisions" in tmpl:
            return [d for d in tmpl["decisions"] if isinstance(d, dict)]
        # Bare decisions wrapper
        if "decisions" in payload:
            decisions = payload["decisions"]
            if isinstance(decisions, list):
                return [d for d in decisions if isinstance(d, dict)]
    return []


def load_source_context_index(review_path: Path) -> dict[str, dict[str, Any]]:
    """
    Build {candidate_id: source_context} from review_queue[] in a full queue export.
    Returns empty dict if the file doesn't contain that structure.
    """
    payload = read_json(review_path.resolve())
    if not isinstance(payload, dict):
        return {}
    queue = payload.get("review_queue")
    if not isinstance(queue, list):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for entry in queue:
        if isinstance(entry, dict) and "candidate_id" in entry:
            index[entry["candidate_id"]] = entry.get("source_context") or {}
    return index


# ---------------------------------------------------------------------------
# Entry construction
# ---------------------------------------------------------------------------


def build_encyclopedia_entry(
    *,
    display_title: str,
    slug: str,
    lane: str,
    work_id: str,
    section_id: str,
    source_context: dict[str, Any],
    original_title: str = "",
) -> dict[str, Any]:
    excerpt = source_context.get("source_excerpt") or ""
    if len(excerpt) > SOURCE_EXCERPT_LIMIT:
        excerpt = excerpt[:SOURCE_EXCERPT_LIMIT] + "..."
    entry: dict[str, Any] = {
        "title": display_title,
        "slug": slug,
        "type": "topic",
        "degree": "encyclopedia",
        "status": "draft",
        "lane": lane,
        "description": auto_description(display_title, lane),
        "relations": [],
        "tags": [],
        "source_work_id": work_id,
        "source_section_id": section_id,
        "source_chapter_slug": source_context.get("chapter_slug") or "",
        "source_excerpt": excerpt,
        "body": "",
    }
    if original_title and original_title != display_title:
        entry["original_title"] = original_title
    return entry


# ---------------------------------------------------------------------------
# Lane counts helper
# ---------------------------------------------------------------------------


def lane_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for e in entries:
        counts[normalize_text(e.get("lane")) or "unknown"] += 1
    return dict(sorted(counts.items()))


# ---------------------------------------------------------------------------
# Core apply logic
# ---------------------------------------------------------------------------


def apply_proposals(
    review_decisions: list[dict[str, Any]],
    source_context_index: dict[str, dict[str, Any]],
    existing_enc: dict[str, Any],
    run_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Returns (updated_encyclopedia, report).
    Does NOT write anything — the caller decides whether to write.
    """
    enc = copy.deepcopy(existing_enc)
    entries: list[dict[str, Any]] = enc.get("entries", [])

    # Build O(1) lookup indices
    slug_index: dict[str, int] = {e["slug"]: i for i, e in enumerate(entries)}
    source_index: dict[tuple[str, str], int] = {
        (
            normalize_text(e.get("source_work_id")),
            normalize_text(e.get("source_section_id")),
        ): i
        for i, e in enumerate(entries)
        if normalize_text(e.get("source_section_id"))
    }

    added: list[dict[str, Any]] = []
    merged: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    # Filter to encyclopedia proposals only — accept both E1 "encyclopedia" and E2 "approve_encyclopedia"
    def _is_encyclopedia_proposal(d: dict) -> bool:
        ra = normalize_text(d.get("review_action", ""))
        return ra in ("encyclopedia", "approve_encyclopedia")

    proposals = [d for d in review_decisions if _is_encyclopedia_proposal(d)]

    for proposal in proposals:
        # E1 queue uses approved_title/normalized_title; E2 template uses canonical_title
        approved_title = normalize_text(
            proposal.get("canonical_title")
            or proposal.get("approved_title")
            or proposal.get("normalized_title")
        )
        if not approved_title:
            skipped.append(
                {
                    "reason": "MISSING_TITLE",
                    "candidate_id": proposal.get("candidate_id") or proposal.get("concept_key"),
                    "work_id": proposal.get("work_id"),
                    "section_id": proposal.get("section_id"),
                }
            )
            continue

        display_title = to_display_title(approved_title)
        slug = enc_slug(display_title)
        # E1 queue uses encyclopedia_lane; E2 template uses final_lane
        lane = normalize_text(proposal.get("final_lane") or proposal.get("encyclopedia_lane")) or "encyclopedia_pending"
        if lane not in KNOWN_LANES:
            skipped.append(
                {
                    "reason": "UNKNOWN_LANE",
                    "slug": slug,
                    "title": display_title,
                    "lane": lane,
                    "candidate_id": proposal.get("candidate_id"),
                }
            )
            continue

        # E2 template uses concept_key instead of candidate_id
        candidate_id = normalize_text(proposal.get("candidate_id") or proposal.get("concept_key"))
        work_id = normalize_text(proposal.get("work_id"))
        section_id = normalize_text(proposal.get("section_id"))
        source_context = source_context_index.get(candidate_id, {})

        # --- Slug collision (same title) ---
        if slug in slug_index:
            existing = entries[slug_index[slug]]
            ex_work = normalize_text(existing.get("source_work_id"))
            ex_section = normalize_text(existing.get("source_section_id"))

            if ex_work == work_id and ex_section == section_id:
                # Exactly the same source — genuinely redundant
                skipped.append(
                    {
                        "reason": "ALREADY_PRESENT_SAME_SOURCE",
                        "slug": slug,
                        "title": display_title,
                        "work_id": work_id,
                        "section_id": section_id,
                    }
                )
            else:
                # Same title, different source section — add additional source reference
                if "additional_sources" not in entries[slug_index[slug]]:
                    entries[slug_index[slug]]["additional_sources"] = []
                entries[slug_index[slug]]["additional_sources"].append(
                    {
                        "work_id": work_id,
                        "section_id": section_id,
                        "chapter_slug": source_context.get("chapter_slug") or "",
                    }
                )
                merged.append(
                    {
                        "slug": slug,
                        "title": display_title,
                        "lane": lane,
                        "existing_source": f"{ex_work}:{ex_section}",
                        "added_source": f"{work_id}:{section_id}",
                    }
                )
            continue

        # --- Source collision (same section already used under a different title/slug) ---
        src_key = (work_id, section_id)
        if src_key in source_index and work_id and section_id:
            existing = entries[source_index[src_key]]
            skipped.append(
                {
                    "reason": "SOURCE_SECTION_ALREADY_USED",
                    "slug": slug,
                    "title": display_title,
                    "existing_slug": existing.get("slug"),
                    "existing_title": existing.get("title"),
                    "work_id": work_id,
                    "section_id": section_id,
                }
            )
            continue

        # --- New entry ---
        original_title_raw = normalize_text(proposal.get("original_title") or "")
        new_entry = build_encyclopedia_entry(
            display_title=display_title,
            slug=slug,
            lane=lane,
            work_id=work_id,
            section_id=section_id,
            source_context=source_context,
            original_title=original_title_raw,
        )
        entries.append(new_entry)
        slug_index[slug] = len(entries) - 1
        if work_id and section_id:
            source_index[src_key] = len(entries) - 1
        added.append(
            {
                "slug": slug,
                "title": display_title,
                "lane": lane,
                "work_id": work_id,
                "section_id": section_id,
            }
        )

    enc["entries"] = entries
    enc["run_id"] = run_id
    enc["last_applied_at"] = utc_timestamp()

    report: dict[str, Any] = {
        "added": added,
        "merged": merged,
        "skipped": skipped,
        "summary": {
            "proposals_found": len(proposals),
            "added_count": len(added),
            "merged_count": len(merged),
            "skipped_count": len(skipped),
        },
    }
    return enc, report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "site_root", None) is None:
        args.site_root = get_work_site_root()

    review_path: Path = args.review_file.resolve()
    if not review_path.exists():
        print(f"[error] review file not found: {review_path}", file=sys.stderr)
        sys.exit(1)

    site_root: Path = args.site_root.resolve()
    enc_path: Path = site_root / "data" / "encyclopedia.json"
    if not enc_path.exists():
        print(f"[error] encyclopedia.json not found at: {enc_path}", file=sys.stderr)
        sys.exit(1)

    output_dir: Path = (
        args.output_dir.resolve()
        if args.output_dir
        else review_path.parent / "apply_reports"
    )
    run_id: str = args.run_id or utc_timestamp().replace(":", "-").replace("+", "Z")

    mode_label = "write" if args.write else "preview"

    # Load inputs
    review_decisions = load_review_decisions(review_path)
    source_context_index = load_source_context_index(review_path)
    existing_enc: dict[str, Any] = read_json(enc_path)

    if not isinstance(existing_enc, dict):
        print(f"[error] encyclopedia.json is not a JSON object: {enc_path}", file=sys.stderr)
        sys.exit(1)

    # Snapshot lane counts before
    existing_entries: list[dict[str, Any]] = existing_enc.get("entries", [])
    before_counts = lane_counts(existing_entries)

    proposals_count = sum(
        1 for d in review_decisions
        if normalize_text(d.get("review_action", "")) in ("encyclopedia", "approve_encyclopedia")
    )
    print(
        f"[{mode_label}] review decisions loaded={len(review_decisions)} "
        f"encyclopedia_proposals={proposals_count} "
        f"source_contexts={len(source_context_index)}"
    )

    # Run apply logic
    updated_enc, report = apply_proposals(
        review_decisions=review_decisions,
        source_context_index=source_context_index,
        existing_enc=existing_enc,
        run_id=run_id,
    )

    after_counts = lane_counts(updated_enc.get("entries", []))

    # Assemble full report
    full_report: dict[str, Any] = {
        "created_at": utc_timestamp(),
        "mode": mode_label,
        "run_id": run_id,
        "review_file": str(review_path),
        "encyclopedia_path": str(enc_path),
        "entries_before": len(existing_entries),
        "entries_after": len(updated_enc.get("entries", [])),
        "lane_counts_before": before_counts,
        "lane_counts_after": after_counts,
        **report,
    }

    # Print summary
    s = report["summary"]
    print(
        f"[{mode_label}] entries before={full_report['entries_before']} "
        f"after={full_report['entries_after']} "
        f"added={s['added_count']} merged={s['merged_count']} skipped={s['skipped_count']}"
    )

    if report["added"]:
        print(f"\n  Added ({s['added_count']}):")
        for item in report["added"]:
            print(f"    + [{item['lane']}] {item['title']}  ({item['work_id']}:{item['section_id']})")

    if report["merged"]:
        print(f"\n  Merged — additional source noted ({s['merged_count']}):")
        for item in report["merged"]:
            print(f"    ~ {item['slug']}  new_source={item['added_source']}")

    if report["skipped"]:
        print(f"\n  Skipped ({s['skipped_count']}):")
        for item in report["skipped"]:
            reason = item.get("reason", "?")
            title = item.get("title") or item.get("candidate_id") or "?"
            print(f"    - [{reason}] {title}")

    print("\n  Lane counts:")
    all_lanes = sorted(set(list(before_counts.keys()) + list(after_counts.keys())))
    for lane in all_lanes:
        b = before_counts.get(lane, 0)
        a = after_counts.get(lane, 0)
        delta = f" (+{a - b})" if a > b else (f" ({a - b})" if a < b else "")
        print(f"    {lane:<45} {b:>4} -> {a:>4}{delta}")
    print(f"    {'TOTAL':<45} {full_report['entries_before']:>4} -> {full_report['entries_after']:>4}")

    # Write outputs
    ensure_dir(output_dir)
    report_path = output_dir / f"encyclopedia_apply_report_{run_id}.json"
    write_json(report_path, full_report)
    print(f"\n[{mode_label}] report written: {report_path}")

    if args.write:
        write_json(enc_path, updated_enc)
        print(f"[write] encyclopedia.json updated: {enc_path}")
    else:
        print(f"[preview] encyclopedia.json NOT modified — rerun with --write to apply")

    # Exit code
    error_skips = [s for s in report["skipped"] if s.get("reason") not in {"ALREADY_PRESENT_SAME_SOURCE"}]
    if args.strict and error_skips:
        print(
            f"\n[strict] {len(error_skips)} proposals skipped for non-duplicate reasons",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
