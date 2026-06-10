"""e2_review_package.py — Build the E2 review package.

Reads from the existing E2 mining output and site data.
Produces 5 read-only review files — no writes to site data.

Outputs (all to --output-dir):
  1. topic_mining_candidates.json       — enriched full candidate list
  2. topic_mining_review_template.json  — fillable review sheet
  3. topic_mining_dedupe_report.json    — near-duplicate groups
  4. topic_mining_summary.json          — stats and quality flags
  5. current_topic_index.json           — all existing site slugs/titles

Usage:
    python PDF_handle/prod/cli/e2_review_package.py \
        --mining-dir   PDF_handle/runs/v21r1-e2/mining \
        --site-root    sites/work/v0.5 \
        --output-dir   PDF_handle/runs/v21r1-e2/review_package \
        --run-id       v21r1-e2
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for _c in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(_c) not in sys.path:
        sys.path.insert(0, str(_c))

from PDF_handle.prod.core.io import ensure_dir, read_json, utc_timestamp, write_json
from PDF_handle.prod.core.text import canonical_match_key, canonical_slug as _canonical_slug


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SLUG_RE = re.compile(r"[^a-z0-9]+")
PUNCT_NORM_RE = re.compile(r"[\-\s]+")


def normalize_text(v: Any) -> str:
    return str(v or "").strip()


def concept_slug(title: str) -> str:
    """Slug from title — uses canonical_slug for ASCII-safe, diacritic-free output."""
    return _canonical_slug(title)


def concept_norm_key(title: str) -> str:
    """Canonical match key for dedup — strips diacritics, collapses hyphens/punctuation."""
    return canonical_match_key(title)


# ---------------------------------------------------------------------------
# Load site data
# ---------------------------------------------------------------------------

SITE_FILES = {
    "level1": "level1.json",
    "level2": "level2.json",
    "level3": "level3.json",
    "encyclopedia": "encyclopedia.json",
    "library": "library.json",
}


def load_site_entries(site_root: Path) -> list[dict[str, Any]]:
    """Return a flat list of all entries from all site data files."""
    all_entries: list[dict[str, Any]] = []
    for degree_key, fname in SITE_FILES.items():
        path = site_root / "data" / fname
        if not path.exists():
            continue
        data = read_json(path.resolve())
        raw_entries = data if isinstance(data, list) else data.get("entries", [])
        for e in raw_entries:
            if not isinstance(e, dict):
                continue
            all_entries.append(
                {
                    "slug": normalize_text(e.get("slug")),
                    "title": normalize_text(e.get("title")),
                    "type": normalize_text(e.get("type")),
                    "degree": normalize_text(e.get("degree") or degree_key),
                    "source_file": fname,
                    # Library-specific source fields
                    "work_id": normalize_text(e.get("work_id")),
                    "work_title": normalize_text(e.get("work_title")),
                    "source_anchor": normalize_text(e.get("source_anchor")),
                    "source_path": normalize_text(e.get("source_path")),
                    # Encyclopedia-specific
                    "lane": normalize_text(e.get("lane")),
                    "description": normalize_text(e.get("description")),
                    # Status
                    "status": normalize_text(e.get("status")),
                }
            )
    return all_entries


# ---------------------------------------------------------------------------
# 1. topic_mining_candidates.json  (enriched)
# ---------------------------------------------------------------------------

def build_candidates(raw_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for c in raw_candidates:
        evidence = c.get("evidence", [])
        source_work_ids = list(dict.fromkeys(e["source_work_id"] for e in evidence))
        section_ids = list(dict.fromkeys(e["section_id"] for e in evidence))
        excerpts = [e["excerpt"] for e in evidence if e.get("excerpt")]

        enriched.append(
            {
                "title": c["concept"],
                "concept_key": c["concept_key"],
                "proposed_lane": c["proposed_lane"],
                "confidence": c["confidence"],
                "reason_codes": c["reason_codes"],
                "mention_count": c["mention_count"],
                "section_count": c["section_count"],
                "already_in_site": c["already_in_site"],
                "already_in_e1_candidates": c["already_in_e1_candidates"],
                "e1_decision": c.get("e1_decision"),
                "source_work_ids": source_work_ids,
                "section_ids": section_ids,
                "excerpts": excerpts,
                "evidence": evidence,
            }
        )
    return enriched


# ---------------------------------------------------------------------------
# 2. topic_mining_review_template.json  (expanded)
# ---------------------------------------------------------------------------

REVIEW_ACTIONS = (
    "approve_encyclopedia",
    "approve_degree_root",
    "already_captured",
    "reject",
    "defer",
)

INCOMPLETE_TITLE_RE = re.compile(
    r"\b(?:of|and|or|the|a|an|in|at|by|for|from|to|with)\s*$",
    re.IGNORECASE,
)


def _is_incomplete_title(title: str) -> bool:
    """True if the title ends with a preposition or article — signals a fragment."""
    return bool(INCOMPLETE_TITLE_RE.search(title.strip()))


def _default_action(c: dict[str, Any]) -> str:
    if c["already_in_site"] or c["already_in_e1_candidates"]:
        return "already_captured"
    if _is_incomplete_title(c["title"]):
        return "reject"
    return "defer"


def _default_lane(c: dict[str, Any]) -> str:
    lane = c["proposed_lane"]
    return "" if lane == "degree_root_candidate" else lane


def build_review_template(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = []
    for c in candidates:
        decisions.append(
            {
                "title": c["title"],
                "concept_key": c["concept_key"],
                "proposed_lane": c["proposed_lane"],
                "confidence": c["confidence"],
                "reason_codes": c["reason_codes"],
                "mention_count": c["mention_count"],
                "already_in_site": c["already_in_site"],
                "already_in_e1_candidates": c["already_in_e1_candidates"],
                "e1_decision": c.get("e1_decision"),
                # — reviewer fills these in —
                "review_action": _default_action(c),
                "canonical_title": c["title"],
                "canonical_slug": concept_slug(c["title"]),
                "final_lane": _default_lane(c),
                "final_degree": "",
                "merge_existing_slug": "",
                "review_reason": "",
            }
        )
    return {
        "version": 1,
        "created_at": utc_timestamp(),
        "instructions": (
            "Fill review_action with one of: "
            "approve_encyclopedia / approve_degree_root / already_captured / reject / defer. "
            "If approve_encyclopedia: set final_lane to the target encyclopedia lane. "
            "If approve_degree_root: set final_degree to level1, level2, or level3. "
            "If already_captured: set merge_existing_slug to the existing slug. "
            "Set canonical_title to override the display title. "
            "Set canonical_slug if the auto-generated slug is incorrect. "
            "Near-duplicate pairs are flagged in topic_mining_dedupe_report.json — "
            "pick one canonical entry and set the other to already_captured with merge_existing_slug."
        ),
        "reviewer": "",
        "reviewed_at": None,
        "decisions": decisions,
    }


# ---------------------------------------------------------------------------
# 3. topic_mining_dedupe_report.json
# ---------------------------------------------------------------------------

# Hand-coded semantic groups: lists of concept_keys that are the same concept
# or tightly related and likely need a single canonical entry.
SEMANTIC_GROUPS: list[dict[str, Any]] = [
    {
        "group_id": "winding_stairs",
        "group_label": "Winding Stairs / Winding Staircase",
        "recommendation": "Choose 'Winding Staircase' as canonical; mark 'Winding Stairs' as already_captured.",
        "members": ["winding staircase", "winding stairs"],
    },
    {
        "group_id": "cable_tow",
        "group_label": "Cable-Tow / Cable Tow",
        "recommendation": "Choose 'Cable-Tow' as canonical (hyphenated form is more common in ritual texts); mark 'Cable Tow' as already_captured.",
        "members": ["cable-tow", "cable tow"],
    },
    {
        "group_id": "trestle_board",
        "group_label": "Trestle Board / Trestle-Board",
        "recommendation": "Choose 'Trestle Board' as canonical; mark 'Trestle-Board' as already_captured.",
        "members": ["trestle board", "trestle-board"],
    },
    {
        "group_id": "plumb_rule",
        "group_label": "Plumb Rule / Plumb-Rule",
        "recommendation": "Choose 'Plumb Rule' as canonical; mark 'Plumb-Rule' as already_captured.",
        "members": ["plumb rule", "plumb-rule"],
    },
    {
        "group_id": "boaz_jachin",
        "group_label": "Boaz / Jachin (twin pillars)",
        "recommendation": "These are two distinct pillars often treated as a pair. Options: (a) two separate entries 'Boaz' and 'Jachin', or (b) one entry 'Boaz and Jachin'. Decide canonical form before applying.",
        "members": ["boaz", "jachin"],
    },
    {
        "group_id": "cardinal_virtues",
        "group_label": "Cardinal Virtues / Four Cardinal Virtues",
        "recommendation": "Choose 'Four Cardinal Virtues' as canonical (more specific); mark 'Cardinal Virtues' as already_captured.",
        "members": ["four cardinal virtues", "cardinal virtues"],
    },
    {
        "group_id": "desaguliers",
        "group_label": "Desaguliers / John Theophilus Desaguliers",
        "recommendation": "Choose 'John Theophilus Desaguliers' as canonical (full name); mark 'Desaguliers' as already_captured.",
        "members": ["desaguliers", "john theophilus desaguliers"],
    },
    {
        "group_id": "knight_templar",
        "group_label": "Knight Templar / Knights Templar",
        "recommendation": "Choose 'Knights Templar' (plural, standard Masonic usage); mark 'Knight Templar' as already_captured.",
        "members": ["knight templar", "knights templar"],
    },
    {
        "group_id": "liberal_arts",
        "group_label": "Seven Liberal Arts / Liberal Arts And Sciences",
        "recommendation": "Choose 'Seven Liberal Arts and Sciences' as canonical (full Masonic phrase); mark both as needing canonical_title override.",
        "members": ["seven liberal arts", "liberal arts and sciences"],
    },
    {
        "group_id": "all_seeing_eye",
        "group_label": "All Seeing Eye / All-Seeing Eye",
        "recommendation": "Choose 'All-Seeing Eye' (hyphenated, standard usage); mark 'All Seeing Eye' as already_captured.",
        "members": ["all seeing eye", "all-seeing eye"],
    },
    {
        "group_id": "book_of_constitutions",
        "group_label": "Book Of Constitutions (symbol) / Anderson's Constitutions (historical document)",
        "recommendation": "These are DIFFERENT concepts: 'Book of Constitutions' is a Masonic lodge symbol; 'Anderson's Constitutions' is the 1723 historical document. Keep both as separate entries in different lanes.",
        "members": ["book of constitutions", "anderson's constitutions"],
        "is_related_not_duplicate": True,
    },
    {
        "group_id": "hiram_tyre",
        "group_label": "Hiram, King Of Tyre / Hiram Of Tyre",
        "recommendation": "These match the same historical figure (the craftsman Hiram of Tyre, not Hiram Abiff). Choose 'Hiram of Tyre' as canonical.",
        "members": ["hiram, king of tyre", "hiram of tyre"],
    },
]


def _auto_detect_fuzzy_pairs(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Auto-detect additional pairs not in SEMANTIC_GROUPS by normalizing out hyphens/spaces
    and finding concept_keys that collapse to the same string.
    """
    norm_to_keys: dict[str, list[str]] = defaultdict(list)
    for c in candidates:
        nk = concept_norm_key(c["concept_key"])
        norm_to_keys[nk].append(c["concept_key"])

    auto_pairs: list[dict[str, Any]] = []
    # Collect concept_keys in existing semantic groups to skip them
    already_grouped: set[str] = set()
    for g in SEMANTIC_GROUPS:
        already_grouped.update(g["members"])

    for norm_key, keys in norm_to_keys.items():
        if len(keys) < 2:
            continue
        new_keys = [k for k in keys if k not in already_grouped]
        if len(new_keys) < 2:
            continue
        auto_pairs.append(
            {
                "group_id": f"auto_{concept_slug(norm_key)}",
                "group_label": f"Auto-detected variant pair: {' / '.join(new_keys)}",
                "recommendation": "Review — these concept keys normalize to the same string. Pick a canonical entry.",
                "members": new_keys,
                "auto_detected": True,
            }
        )
    return auto_pairs


def build_dedupe_report(
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    present_keys: set[str] = {c["concept_key"] for c in candidates}
    candidate_by_key: dict[str, dict[str, Any]] = {c["concept_key"]: c for c in candidates}

    groups_with_data: list[dict[str, Any]] = []
    for g in SEMANTIC_GROUPS:
        members_present = [m for m in g["members"] if m in present_keys]
        members_absent = [m for m in g["members"] if m not in present_keys]
        member_details = []
        for m in members_present:
            c = candidate_by_key[m]
            member_details.append(
                {
                    "concept_key": m,
                    "title": c["title"],
                    "mention_count": c["mention_count"],
                    "confidence": c["confidence"],
                    "proposed_lane": c["proposed_lane"],
                    "already_in_site": c["already_in_site"],
                    "status": "present_in_candidates",
                }
            )
        for m in members_absent:
            member_details.append(
                {
                    "concept_key": m,
                    "title": m.title(),
                    "mention_count": 0,
                    "status": "not_in_candidates",
                }
            )
        groups_with_data.append(
            {
                **g,
                "members_present": members_present,
                "members_absent": members_absent,
                "action_needed": len(members_present) > 1,
                "member_details": member_details,
            }
        )

    auto_pairs = _auto_detect_fuzzy_pairs(candidates)
    for ap in auto_pairs:
        members_present = [m for m in ap["members"] if m in present_keys]
        ap["member_details"] = [
            {
                "concept_key": m,
                "title": candidate_by_key[m]["title"],
                "mention_count": candidate_by_key[m]["mention_count"],
                "status": "present_in_candidates",
            }
            for m in members_present
        ]
        ap["action_needed"] = len(members_present) > 1
        groups_with_data.append(ap)

    action_needed = [g for g in groups_with_data if g.get("action_needed")]
    return {
        "created_at": utc_timestamp(),
        "total_groups": len(groups_with_data),
        "groups_needing_action": len(action_needed),
        "groups": groups_with_data,
    }


# ---------------------------------------------------------------------------
# 4. topic_mining_summary.json
# ---------------------------------------------------------------------------

INCOMPLETE_TITLE_PATTERNS = re.compile(
    r"""(?xi)
    \b(?:of|and|or|the|a|an|in|at|by|for|from|to|with)\s*$  # trailing preposition
    | ^(?:of|and|or|a|an|in|at|by|for|from|to|with)\b        # leading preposition
    """,
)


def _flag_quality_issues(c: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    title = c["title"]
    if _is_incomplete_title(title):
        flags.append("INCOMPLETE_TITLE")
    if c["confidence"] == "medium":
        flags.append("MEDIUM_CONFIDENCE")
    if c["already_in_site"]:
        flags.append("ALREADY_IN_SITE")
    if c["already_in_e1_candidates"]:
        flags.append("ALREADY_IN_E1_CANDIDATES")
    if c["mention_count"] == 1:
        flags.append("SINGLE_MENTION")
    return flags


def build_summary(
    candidates: list[dict[str, Any]],
    site_entries: list[dict[str, Any]],
    raw_doc: dict[str, Any],
) -> dict[str, Any]:
    by_lane: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in candidates:
        by_lane[c["proposed_lane"]].append(c)

    lane_counts: dict[str, dict[str, int]] = {}
    for lane, items in sorted(by_lane.items()):
        new = sum(1 for i in items if not i["already_in_site"] and not i["already_in_e1_candidates"])
        e1 = sum(1 for i in items if i["already_in_e1_candidates"])
        site = sum(1 for i in items if i["already_in_site"])
        lane_counts[lane] = {
            "total": len(items),
            "new": new,
            "already_in_e1_candidates": e1,
            "already_in_site": site,
        }

    top30 = sorted(candidates, key=lambda c: -c["mention_count"])[:30]

    quality_flagged: list[dict[str, Any]] = []
    for c in candidates:
        flags = _flag_quality_issues(c)
        if flags:
            quality_flagged.append(
                {
                    "title": c["title"],
                    "concept_key": c["concept_key"],
                    "proposed_lane": c["proposed_lane"],
                    "flags": flags,
                    "mention_count": c["mention_count"],
                }
            )

    incomplete_titles = [
        {
            "title": c["title"],
            "concept_key": c["concept_key"],
            "mention_count": c["mention_count"],
        }
        for c in candidates
        if _is_incomplete_title(c["title"])
    ]

    medium_conf = [
        {
            "title": c["title"],
            "concept_key": c["concept_key"],
            "proposed_lane": c["proposed_lane"],
            "mention_count": c["mention_count"],
            "reason_codes": c["reason_codes"],
        }
        for c in candidates
        if c["confidence"] == "medium"
    ]

    already_captured = [
        {
            "title": c["title"],
            "concept_key": c["concept_key"],
            "already_in_site": c["already_in_site"],
            "already_in_e1_candidates": c["already_in_e1_candidates"],
            "e1_decision": c.get("e1_decision"),
        }
        for c in candidates
        if c["already_in_site"] or c["already_in_e1_candidates"]
    ]

    # Site coverage summary
    site_by_source: dict[str, int] = Counter(e["source_file"] for e in site_entries)

    return {
        "created_at": utc_timestamp(),
        "run_id": raw_doc.get("run_id"),
        "source_works": raw_doc.get("source_works", []),
        "vocabulary_entries": raw_doc.get("vocabulary_entries"),
        "total_candidates": len(candidates),
        "total_new_candidates": sum(
            1 for c in candidates
            if not c["already_in_site"] and not c["already_in_e1_candidates"]
        ),
        "by_proposed_lane": lane_counts,
        "top_30_by_mention_count": [
            {
                "title": c["title"],
                "proposed_lane": c["proposed_lane"],
                "mention_count": c["mention_count"],
                "confidence": c["confidence"],
                "already_in_site": c["already_in_site"],
                "already_in_e1_candidates": c["already_in_e1_candidates"],
            }
            for c in top30
        ],
        "medium_confidence_candidates": medium_conf,
        "incomplete_title_candidates": incomplete_titles,
        "already_captured_candidates": already_captured,
        "quality_flagged_candidates": quality_flagged,
        "site_entry_counts": {
            k: site_by_source.get(v, 0) for k, v in SITE_FILES.items()
        },
    }


# ---------------------------------------------------------------------------
# 5. current_topic_index.json
# ---------------------------------------------------------------------------

def build_topic_index(site_entries: list[dict[str, Any]]) -> dict[str, Any]:
    # Sort: degree order, then title
    degree_order = {"level1": 0, "level2": 1, "level3": 2, "encyclopedia": 3, "library": 4}

    def sort_key(e: dict[str, Any]) -> tuple[int, str]:
        return (
            degree_order.get(e.get("degree", "").split(".")[0], 9),
            e.get("title", "").lower(),
        )

    sorted_entries = sorted(site_entries, key=sort_key)

    # Build lookup by normalized title
    by_title: dict[str, list[str]] = defaultdict(list)
    for e in sorted_entries:
        by_title[e["title"].lower()].append(e["slug"])

    # Mark duplicates (same title, multiple sources)
    entries_with_flags = []
    for e in sorted_entries:
        slugs_for_title = by_title[e["title"].lower()]
        flags: list[str] = []
        if len(slugs_for_title) > 1 and e["slug"] not in (slugs_for_title[:1]):
            flags.append("DUPLICATE_TITLE_ACROSS_FILES")

        entry: dict[str, Any] = {
            "slug": e["slug"],
            "title": e["title"],
            "source_file": e["source_file"],
            "degree": e["degree"],
            "type": e["type"],
        }
        # Optional enrichment fields
        if e.get("lane"):
            entry["lane"] = e["lane"]
        if e.get("description"):
            entry["description"] = e["description"]
        if e.get("work_id"):
            entry["work_id"] = e["work_id"]
        if e.get("work_title"):
            entry["work_title"] = e["work_title"]
        if e.get("source_anchor"):
            entry["source_anchor"] = e["source_anchor"]
        if flags:
            entry["flags"] = flags

        entries_with_flags.append(entry)

    by_source: dict[str, list[dict]] = defaultdict(list)
    for e in entries_with_flags:
        by_source[e["source_file"]].append(e)

    return {
        "created_at": utc_timestamp(),
        "total_entries": len(entries_with_flags),
        "by_source_file": {
            fname: {
                "count": len(by_source.get(fname, [])),
                "entries": by_source.get(fname, []),
            }
            for fname in SITE_FILES.values()
        },
        "all_entries": entries_with_flags,
    }


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the E2 review package (5 read-only files). No writes to site data."
    )
    parser.add_argument(
        "--mining-dir",
        type=Path,
        default=PDF_HANDLE_ROOT / "runs" / "v21r1-e2" / "mining",
        help="Directory containing topic_mining_candidates.json from the E2 miner.",
    )
    parser.add_argument(
        "--site-root",
        type=Path,
        default=REPO_ROOT / "sites" / "work" / "v0.5",
        help="Site root for reading current degree/encyclopedia/library data.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PDF_HANDLE_ROOT / "runs" / "v21r1-e2" / "review_package",
        help="Output directory for all 5 review files.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default="v21r1-e2",
    )
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    mining_dir: Path = args.mining_dir.resolve()
    site_root: Path = args.site_root.resolve()
    output_dir: Path = args.output_dir.resolve()

    ensure_dir(output_dir)

    # Load mining output
    candidates_path = mining_dir / "topic_mining_candidates.json"
    if not candidates_path.exists():
        print(f"[error] mining candidates not found: {candidates_path}", file=sys.stderr)
        sys.exit(1)

    raw_doc = read_json(candidates_path.resolve())
    raw_candidates: list[dict[str, Any]] = raw_doc.get("candidates", [])
    print(f"[package] loaded {len(raw_candidates)} candidates from {candidates_path}")

    # Load site data
    site_entries = load_site_entries(site_root)
    print(f"[package] loaded {len(site_entries)} site entries from {site_root}")

    # --- 1. topic_mining_candidates.json ---
    print("[package] building candidates file ...")
    candidates = build_candidates(raw_candidates)
    doc1: dict[str, Any] = {
        "version": 2,
        "created_at": utc_timestamp(),
        "run_id": args.run_id,
        "source_works": raw_doc.get("source_works", []),
        "vocabulary_entries": raw_doc.get("vocabulary_entries"),
        "min_confidence": raw_doc.get("min_confidence"),
        "total_candidates": len(candidates),
        "by_proposed_lane": dict(
            sorted(Counter(c["proposed_lane"] for c in candidates).items())
        ),
        "candidates": candidates,
    }
    p1 = output_dir / "topic_mining_candidates.json"
    write_json(p1, doc1)
    print(f"[package] written: {p1}  ({len(candidates)} candidates)")

    # --- 2. topic_mining_review_template.json ---
    print("[package] building review template ...")
    tmpl = build_review_template(candidates)
    p2 = output_dir / "topic_mining_review_template.json"
    write_json(p2, tmpl)
    print(f"[package] written: {p2}  ({len(tmpl['decisions'])} decisions)")

    # --- 3. topic_mining_dedupe_report.json ---
    print("[package] building dedupe report ...")
    dedupe = build_dedupe_report(candidates)
    p3 = output_dir / "topic_mining_dedupe_report.json"
    write_json(p3, dedupe)
    print(
        f"[package] written: {p3}  "
        f"({dedupe['total_groups']} groups, "
        f"{dedupe['groups_needing_action']} need action)"
    )

    # --- 4. topic_mining_summary.json ---
    print("[package] building summary ...")
    summary = build_summary(candidates, site_entries, raw_doc)
    p4 = output_dir / "topic_mining_summary.json"
    write_json(p4, summary)
    print(f"[package] written: {p4}")

    # --- 5. current_topic_index.json ---
    print("[package] building topic index ...")
    index = build_topic_index(site_entries)
    p5 = output_dir / "current_topic_index.json"
    write_json(p5, index)
    print(f"[package] written: {p5}  ({index['total_entries']} entries)")

    # --- Console summary ---
    print()
    print("=" * 60)
    print(f"E2 Review Package  ({args.run_id})")
    print("=" * 60)
    print(f"  Candidates:      {doc1['total_candidates']:>4}")
    new_count = sum(
        1 for c in candidates
        if not c["already_in_site"] and not c["already_in_e1_candidates"]
    )
    print(f"  New (unreviewed):{new_count:>4}")
    print()
    print("  By proposed lane:")
    for lane, count in doc1["by_proposed_lane"].items():
        print(f"    {lane:<48} {count:>3}")
    print()
    print(f"  Dedupe groups needing action: {dedupe['groups_needing_action']}")
    print(f"  Medium-confidence candidates: {len(summary['medium_confidence_candidates'])}")
    print(f"  Incomplete titles:            {len(summary['incomplete_title_candidates'])}")
    print(f"  Already captured:             {len(summary['already_captured_candidates'])}")
    print()
    print("  Site entry counts:")
    for k, count in summary["site_entry_counts"].items():
        print(f"    {k:<20} {count:>5}")
    print()
    print("  Output files:")
    for p in (p1, p2, p3, p4, p5):
        print(f"    {p.name}")
    print()
    print("  No site data was modified.")


if __name__ == "__main__":
    main()
