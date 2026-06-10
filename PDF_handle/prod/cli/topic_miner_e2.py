"""topic_miner_e2.py — Expansion Phase 2: deeper same-source topic mining.

Scans the body text of all consolidated source works for Masonic concepts that
were NOT surfaced by the E1 heading-based discovery pass.  Covers:
  1. Symbols and emblems
  2. Working tools
  3. Moral virtues and tenets
  4. Lodge structure terms
  5. Officers and roles
  6. Ritual / ceremony terms (public / non-secret)
  7. Historical figures and reference works
  8. Architectural / geometric terms
  9. Higher-degree reference terms (for encyclopedia only)
  10. Repeated named concepts inside paragraphs

Output:
  topic_mining_candidates.json   — all candidates with evidence
  topic_mining_review_template.json — fill-in review sheet

Usage:
    python PDF_handle/prod/cli/topic_miner_e2.py \
        --consolidated-dir PDF_handle/consolidated_books \
        --site-root sites/work/v0.5 \
        --e1-staging PDF_handle/runs/v21r1-e1/staging \
        --output-dir PDF_handle/runs/v21r1-e2/mining \
        --run-id v21r1-e2
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
for _cand in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(_cand) not in sys.path:
        sys.path.insert(0, str(_cand))

from PDF_handle.prod.core.io import ensure_dir, read_json, read_text, utc_timestamp, write_json, write_text
from PDF_handle.prod.core.text import canonical_match_key, canonical_normalize
from PDF_handle.prod.steps.stage_support import extract_sections, normalize_extracted_sections


# ---------------------------------------------------------------------------
# Vocabulary tables
# Each entry: pattern_key (lower) -> (proposed_lane, confidence, reason_code)
# ---------------------------------------------------------------------------

_H = "high"
_M = "medium"

VOCABULARY: list[tuple[str, str, str, str]] = [
    # (pattern_text, proposed_lane, confidence, reason_code)

    # ── 1. Symbols and emblems ──────────────────────────────────────────────
    ("blazing star",            "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("all-seeing eye",          "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("all seeing eye",          "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("eye of providence",       "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("point within a circle",   "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("sprig of acacia",         "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("mosaic pavement",         "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("tessellated border",      "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("indented tesselwork",     "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("rough ashlar",            "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("perfect ashlar",          "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("trestle-board",           "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("trestle board",           "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("lewis",                   "encyclopedia_symbols_tools", _M, "MASONIC_SYMBOL"),  # architectural clamp
    ("pot of incense",          "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("book of constitutions",   "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),
    ("sword pointing to a naked heart", "encyclopedia_symbols_tools", _H, "MASONIC_SYMBOL"),

    # ── 2. Working tools ────────────────────────────────────────────────────
    ("twenty-four inch gauge",  "encyclopedia_symbols_tools", _H, "WORKING_TOOL"),
    ("24-inch gauge",           "encyclopedia_symbols_tools", _H, "WORKING_TOOL"),
    ("24 inch gauge",           "encyclopedia_symbols_tools", _H, "WORKING_TOOL"),
    ("common gavel",            "encyclopedia_symbols_tools", _H, "WORKING_TOOL"),
    ("plumb rule",              "encyclopedia_symbols_tools", _H, "WORKING_TOOL"),
    ("plumb-rule",              "encyclopedia_symbols_tools", _H, "WORKING_TOOL"),
    ("setting maul",            "encyclopedia_symbols_tools", _H, "WORKING_TOOL"),
    ("chisel",                  "encyclopedia_symbols_tools", _M, "WORKING_TOOL"),
    ("trowel",                  "encyclopedia_symbols_tools", _H, "WORKING_TOOL"),
    ("pickaxe",                 "encyclopedia_symbols_tools", _H, "WORKING_TOOL"),
    ("skirret",                 "encyclopedia_symbols_tools", _H, "WORKING_TOOL"),

    # ── 3. Moral virtues and tenets ─────────────────────────────────────────
    ("fortitude",               "encyclopedia_foundational",  _H, "MORAL_VIRTUE"),
    ("prudence",                "encyclopedia_foundational",  _H, "MORAL_VIRTUE"),
    ("four cardinal virtues",   "encyclopedia_foundational",  _H, "MORAL_VIRTUE"),
    ("cardinal virtues",        "encyclopedia_foundational",  _H, "MORAL_VIRTUE"),
    ("great principles",        "encyclopedia_foundational",  _M, "MASONIC_TENET"),
    ("three grand principles",  "encyclopedia_foundational",  _H, "MASONIC_TENET"),
    ("tenets of freemasonry",   "encyclopedia_foundational",  _H, "MASONIC_TENET"),
    ("moral duties",            "encyclopedia_foundational",  _M, "MASONIC_TENET"),
    ("seven liberal arts",      "encyclopedia_foundational",  _H, "MASONIC_TENET"),
    ("liberal arts and sciences", "encyclopedia_foundational", _H, "MASONIC_TENET"),
    ("five orders of architecture", "encyclopedia_foundational", _H, "ARCHITECTURAL_TERM"),
    ("three ancient grand masters", "encyclopedia_foundational", _H, "MASONIC_LEGEND"),

    # ── 4. Lodge structure terms ─────────────────────────────────────────────
    ("stated communication",    "encyclopedia_glossary",      _H, "LODGE_STRUCTURE"),
    ("called communication",    "encyclopedia_glossary",      _H, "LODGE_STRUCTURE"),
    ("dispensation",            "encyclopedia_glossary",      _M, "LODGE_GOVERNANCE"),
    ("lodge of perfection",     "encyclopedia_glossary",      _H, "LODGE_STRUCTURE"),
    ("tiled lodge",             "encyclopedia_glossary",      _H, "LODGE_STRUCTURE"),
    ("due form",                "encyclopedia_glossary",      _H, "LODGE_STRUCTURE"),
    ("in ample form",           "encyclopedia_glossary",      _H, "LODGE_STRUCTURE"),
    ("regular communication",   "encyclopedia_glossary",      _H, "LODGE_STRUCTURE"),
    ("lodge of sorrow",         "encyclopedia_ritual_reference", _H, "CEREMONY_TYPE"),
    ("burial service",          "encyclopedia_ritual_reference", _H, "CEREMONY_TYPE"),
    ("installation of officers","encyclopedia_ritual_reference", _H, "CEREMONY_TYPE"),
    ("installation",            "encyclopedia_ritual_reference", _M, "CEREMONY_TYPE"),
    ("dedication of",           "encyclopedia_ritual_reference", _M, "CEREMONY_TYPE"),
    ("foundation stone",        "encyclopedia_ritual_reference", _H, "CEREMONY_TYPE"),
    ("grand visitation",        "encyclopedia_ritual_reference", _H, "CEREMONY_TYPE"),

    # ── 5. Officers and roles ────────────────────────────────────────────────
    ("worshipful master",       "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),
    ("junior warden",           "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),
    ("senior warden",           "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),
    ("junior deacon",           "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),
    ("senior deacon",           "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),
    ("tyler",                   "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),
    ("tiler",                   "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),
    ("chaplain",                "encyclopedia_officers_governance", _M, "LODGE_OFFICER"),
    ("marshal",                 "encyclopedia_officers_governance", _M, "LODGE_OFFICER"),
    ("inner guard",             "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),
    ("senior steward",          "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),
    ("junior steward",          "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),
    ("master of ceremonies",    "encyclopedia_officers_governance", _M, "LODGE_OFFICER"),
    ("grand master",            "encyclopedia_officers_governance", _M, "LODGE_OFFICER"),
    ("deputy grand master",     "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),
    ("grand lecturer",          "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),
    ("past grand master",       "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),
    ("immediate past master",   "encyclopedia_officers_governance", _H, "LODGE_OFFICER"),

    # ── 6. Ritual / ceremony reference terms (public / non-secret) ──────────
    ("circumambulation",        "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("investiture",             "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("hoodwink",                "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("cable-tow",               "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("cable tow",               "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("due guard",               "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("grand honors",            "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("three great lights",      "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("three lesser lights",     "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("the holy bible",          "encyclopedia_ritual_reference", _M, "RITUAL_TERM"),
    ("volume of the sacred law","encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("northeast corner",        "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("ceremony of initiation",  "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("ceremony of passing",     "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("ceremony of raising",     "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("entered apprentice degree","encyclopedia_ritual_reference", _H, "DEGREE_NAME"),
    ("fellow craft degree",     "encyclopedia_ritual_reference", _H, "DEGREE_NAME"),
    ("master mason degree",     "encyclopedia_ritual_reference", _H, "DEGREE_NAME"),
    ("charge at initiation",    "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("charge at passing",       "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("charge at raising",       "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("lecture",                 "encyclopedia_ritual_reference", _M, "RITUAL_TERM"),
    ("perambulation",           "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("test oath",               "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("tiler's obligation",      "encyclopedia_ritual_reference", _H, "RITUAL_TERM"),
    ("great architect of the universe", "encyclopedia_ritual_reference", _H, "MASONIC_PHRASE"),
    ("gaotu",                   "encyclopedia_ritual_reference", _H, "MASONIC_PHRASE"),
    ("grand architect",         "encyclopedia_ritual_reference", _M, "MASONIC_PHRASE"),

    # ── 7. Historical figures ────────────────────────────────────────────────
    ("hiram abiff",             "encyclopedia_history",        _H, "HISTORICAL_FIGURE"),
    ("king solomon",            "encyclopedia_history",        _H, "HISTORICAL_FIGURE"),
    ("hiram of tyre",           "encyclopedia_history",        _H, "HISTORICAL_FIGURE"),
    ("hiram, king of tyre",     "encyclopedia_history",        _H, "HISTORICAL_FIGURE"),
    ("william preston",         "encyclopedia_history",        _H, "HISTORICAL_FIGURE"),
    ("george oliver",           "encyclopedia_history",        _H, "HISTORICAL_FIGURE"),
    ("albert mackey",           "encyclopedia_history",        _H, "HISTORICAL_FIGURE"),
    ("albert pike",             "encyclopedia_history",        _H, "HISTORICAL_FIGURE"),
    ("james anderson",          "encyclopedia_history",        _M, "HISTORICAL_FIGURE"),
    ("thomas dunckerley",       "encyclopedia_history",        _H, "HISTORICAL_FIGURE"),
    ("elias ashmole",           "encyclopedia_history",        _H, "HISTORICAL_FIGURE"),
    ("john theophilus desaguliers", "encyclopedia_history",   _H, "HISTORICAL_FIGURE"),
    ("desaguliers",             "encyclopedia_history",        _H, "HISTORICAL_FIGURE"),
    ("quatuor coronati",        "encyclopedia_history",        _H, "HISTORICAL_INSTITUTION"),
    ("grand lodge of england",  "encyclopedia_history",        _H, "HISTORICAL_INSTITUTION"),
    ("premier grand lodge",     "encyclopedia_history",        _H, "HISTORICAL_INSTITUTION"),
    ("grand lodge of scotland", "encyclopedia_history",        _H, "HISTORICAL_INSTITUTION"),
    ("antients",                "encyclopedia_history",        _H, "HISTORICAL_INSTITUTION"),
    ("moderns",                 "encyclopedia_history",        _M, "HISTORICAL_INSTITUTION"),
    ("ahiman rezon",            "encyclopedia_history",        _H, "HISTORICAL_BOOK"),
    ("book of constitutions",   "encyclopedia_history",        _H, "HISTORICAL_BOOK"),
    ("anderson's constitutions","encyclopedia_history",        _H, "HISTORICAL_BOOK"),
    ("illustrations of masonry","encyclopedia_history",        _H, "HISTORICAL_BOOK"),
    ("mackey's encyclopedia",   "encyclopedia_history",        _H, "HISTORICAL_BOOK"),
    ("morals and dogma",        "encyclopedia_history",        _H, "HISTORICAL_BOOK"),
    ("schaw statutes",          "encyclopedia_history",        _H, "HISTORICAL_DOCUMENT"),
    ("st. clair charters",      "encyclopedia_history",        _H, "HISTORICAL_DOCUMENT"),

    # ── 8. Architectural / geometric terms ──────────────────────────────────
    ("boaz",                    "degree_root_candidate",       _H, "ARCHITECTURAL_TERM"),
    ("jachin",                  "degree_root_candidate",       _H, "ARCHITECTURAL_TERM"),
    ("winding staircase",       "degree_root_candidate",       _H, "ARCHITECTURAL_TERM"),
    ("winding stairs",          "degree_root_candidate",       _H, "ARCHITECTURAL_TERM"),
    ("middle chamber",          "degree_root_candidate",       _H, "ARCHITECTURAL_TERM"),
    ("sanctum sanctorum",       "degree_root_candidate",       _H, "ARCHITECTURAL_TERM"),
    ("holy of holies",          "degree_root_candidate",       _H, "ARCHITECTURAL_TERM"),
    ("forty-seventh problem",   "degree_root_candidate",       _H, "GEOMETRIC_TERM"),
    ("47th problem",            "degree_root_candidate",       _H, "GEOMETRIC_TERM"),
    ("pythagorean theorem",     "degree_root_candidate",       _H, "GEOMETRIC_TERM"),
    ("euclid",                  "degree_root_candidate",       _M, "GEOMETRIC_TERM"),
    ("the altar",               "degree_root_candidate",       _H, "LODGE_STRUCTURE"),
    ("cubic stone",             "degree_root_candidate",       _H, "ARCHITECTURAL_TERM"),
    ("pointed cubic stone",     "degree_root_candidate",       _H, "ARCHITECTURAL_TERM"),
    ("pillars of the porch",    "degree_root_candidate",       _H, "ARCHITECTURAL_TERM"),
    ("columns",                 "degree_root_candidate",       _M, "ARCHITECTURAL_TERM"),
    ("corner stone",            "degree_root_candidate",       _H, "ARCHITECTURAL_TERM"),
    ("keystone",                "degree_root_candidate",       _H, "ARCHITECTURAL_TERM"),
    ("copestone",               "degree_root_candidate",       _H, "ARCHITECTURAL_TERM"),
    ("five points of fellowship","degree_root_candidate",      _H, "RITUAL_TERM"),
    ("three steps",             "degree_root_candidate",       _M, "MASONIC_SYMBOL"),
    ("three ruffians",          "degree_root_candidate",       _H, "MASONIC_LEGEND"),

    # ── 9. Higher-degree references (encyclopedia only) ──────────────────────
    ("royal arch",              "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("mark master",             "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("past master",             "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("most excellent master",   "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("grand chapter",           "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("royal select master",     "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("council of royal",        "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("scottish rite",           "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("york rite",               "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("rose croix",              "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("knights templar",         "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("knight templar",          "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("mystic shrine",           "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("32nd degree",             "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("33rd degree",             "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("fourth degree",           "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("4th degree",              "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("18th degree",             "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("a.a.s. rite",             "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
    ("a.a.s.r.",                "encyclopedia_higher_degrees_reference", _H, "HIGHER_DEGREE"),
]


# ---------------------------------------------------------------------------
# Compile patterns
# ---------------------------------------------------------------------------

def _compile_vocab() -> list[tuple[re.Pattern[str], str, str, str, str]]:
    """Return list of (pattern, concept_display, proposed_lane, confidence, reason_code)."""
    compiled = []
    for phrase, lane, conf, reason in VOCABULARY:
        # Concept display: title-case the phrase
        display = phrase.title()
        # Pattern: word-boundary anchored, case-insensitive
        # Escape special chars, replace space with flexible whitespace
        escaped = re.escape(phrase).replace(r"\ ", r"[\s\-]+")
        pat = re.compile(r"\b" + escaped + r"\b", re.IGNORECASE)
        compiled.append((pat, display, lane, conf, reason))
    return compiled


COMPILED_VOCAB = _compile_vocab()


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

NORMALIZE_SPACE_RE = re.compile(r"\s+")


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def extract_excerpt(text: str, match: re.Match, context_chars: int = 120) -> str:
    start = max(0, match.start() - context_chars)
    end = min(len(text), match.end() + context_chars)
    raw = text[start:end].strip()
    # Collapse whitespace
    return NORMALIZE_SPACE_RE.sub(" ", raw)


def concept_key(display: str) -> str:
    """Canonical match key for dedup — strips diacritics, collapses hyphens/punctuation."""
    return canonical_match_key(display)


# ---------------------------------------------------------------------------
# Site dedup helpers
# ---------------------------------------------------------------------------


def load_existing_titles(site_root: Path) -> frozenset[str]:
    """Canonical match keys from all degree files + encyclopedia.json.

    Uses canonical_match_key so Hebrew-titled entries (e.g. 'הכוכב הזוהר')
    do not generate false match failures against ASCII candidate titles.
    Both the raw title and any English parenthetical aliases are indexed.
    """
    return frozenset(load_existing_entries_index(site_root).keys())


def load_existing_entries_index(site_root: Path) -> dict[str, dict[str, Any]]:
    """Return {canonical_match_key: {title, slug, degree, source_file}} for all site entries.

    Used for dedup reporting and current_topic_index.json generation.
    Indexes titles, parenthetical aliases, and explicit aliases fields.
    """
    import re as _re
    _paren_re = _re.compile(r"\(([^)]+)\)")
    index: dict[str, dict[str, Any]] = {}
    for fname in ("level1.json", "level2.json", "level3.json", "library.json", "encyclopedia.json"):
        path = site_root / "data" / fname
        if not path.exists():
            continue
        data = read_json(path.resolve())
        entries = data if isinstance(data, list) else data.get("entries", [])
        for e in entries:
            t = normalize_text(e.get("title"))
            slug = e.get("slug", "")
            degree = e.get("degree", "")
            if t:
                ck = canonical_match_key(t)
                index[ck] = {
                    "title": t,
                    "slug": slug,
                    "degree": degree,
                    "source_file": fname,
                }
                for m in _paren_re.finditer(t):
                    ak = canonical_match_key(m.group(1))
                    if ak not in index:
                        index[ak] = {
                            "title": m.group(1),
                            "slug": slug,
                            "degree": degree,
                            "source_file": fname,
                            "alias_of": t,
                        }
            for alias in e.get("aliases", []):
                a = normalize_text(alias)
                if a:
                    ak = canonical_match_key(a)
                    if ak not in index:
                        index[ak] = {
                            "title": a,
                            "slug": slug,
                            "degree": degree,
                            "source_file": fname,
                            "alias_of": t,
                        }
    return index


def load_e1_decisions(staging_dir: Path) -> dict[str, str]:
    """concept_key -> e1_decision for rows that E1 classified."""
    rows_path = staging_dir / "discovery_rows.json"
    if not rows_path.exists():
        return {}
    rows = read_json(rows_path.resolve())
    result: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = normalize_text(row.get("normalized_title") or row.get("source_title"))
        if title:
            result[title.lower()] = normalize_text(row.get("decision"))
    return result


# ---------------------------------------------------------------------------
# Mining pass
# ---------------------------------------------------------------------------


def mine_work(
    work_id: str,
    work_title: str,
    markdown_path: Path,
    compiled_vocab: list[tuple[re.Pattern[str], str, str, str, str]],
) -> list[dict[str, Any]]:
    """
    Return a flat list of raw hits:
    {concept_key, concept, proposed_lane, confidence, reason_code,
     work_id, section_id, section_title, excerpt}
    """
    markdown_text = read_text(markdown_path)
    sections = normalize_extracted_sections(
        extract_sections(markdown_text, max_mapping_chars=9999)
    )
    hits: list[dict[str, Any]] = []
    for section in sections:
        text = section.text or ""
        if not text.strip():
            continue
        for pat, display, lane, conf, reason in compiled_vocab:
            for match in pat.finditer(text):
                hits.append(
                    {
                        "concept_key": concept_key(display),
                        "concept": display,
                        "proposed_lane": lane,
                        "confidence": conf,
                        "reason_code": reason,
                        "work_id": work_id,
                        "section_id": section.section_id,
                        "section_title": normalize_text(section.title or section.normalized_title),
                        "excerpt": extract_excerpt(text, match),
                    }
                )
    return hits


# ---------------------------------------------------------------------------
# Aggregate hits → candidates
# ---------------------------------------------------------------------------


def aggregate_candidates(
    all_hits: list[dict[str, Any]],
    existing_titles: frozenset[str],
    e1_decisions: dict[str, str],
    max_evidence_per_concept: int = 5,
) -> list[dict[str, Any]]:
    """
    Deduplicate hits by concept_key, build evidence list, add dedup flags.
    """
    # Group hits by concept_key
    by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for hit in all_hits:
        by_concept[hit["concept_key"]].append(hit)

    candidates: list[dict[str, Any]] = []
    for ck, hits in by_concept.items():
        # Representative hit (highest confidence, then first seen)
        conf_rank = {"high": 0, "medium": 1, "low": 2}
        hits_sorted = sorted(hits, key=lambda h: conf_rank.get(h["confidence"], 9))
        rep = hits_sorted[0]

        # Lane: use the lane that appears most often (handles same concept from two lane tables)
        lane_counter: Counter[str] = Counter(h["proposed_lane"] for h in hits)
        proposed_lane = lane_counter.most_common(1)[0][0]

        # Reason codes: unique set
        reason_codes = sorted({h["reason_code"] for h in hits})

        # Evidence: deduplicate by (work_id, section_id), cap at max
        seen_sections: set[tuple[str, str]] = set()
        evidence: list[dict[str, Any]] = []
        for hit in hits_sorted:
            key = (hit["work_id"], hit["section_id"])
            if key not in seen_sections:
                seen_sections.add(key)
                evidence.append(
                    {
                        "source_work_id": hit["work_id"],
                        "section_id": hit["section_id"],
                        "section_title": hit["section_title"],
                        "excerpt": hit["excerpt"],
                    }
                )
            if len(evidence) >= max_evidence_per_concept:
                break

        # Dedup flags
        already_in_site = ck in existing_titles or rep["concept"].lower() in existing_titles
        e1_decision = e1_decisions.get(ck) or e1_decisions.get(rep["concept"].lower())
        already_in_e1_candidates = e1_decision in {
            "new_canonical_topic", "later_degree_candidate", "encyclopedia_candidate"
        }

        candidates.append(
            {
                "concept": rep["concept"],
                "concept_key": ck,
                "proposed_lane": proposed_lane,
                "confidence": rep["confidence"],
                "reason_codes": reason_codes,
                "mention_count": len(hits),
                "section_count": len(seen_sections),
                "already_in_site": already_in_site,
                "already_in_e1_candidates": already_in_e1_candidates,
                "e1_decision": e1_decision or None,
                "evidence": evidence,
            }
        )

    # Sort: new first (not in site, not in E1 candidates), then by lane, then confidence, then count desc
    def sort_key(c: dict[str, Any]) -> tuple[int, int, str, int]:
        is_new = 0 if (not c["already_in_site"] and not c["already_in_e1_candidates"]) else 1
        conf_rank = {"high": 0, "medium": 1}.get(c["confidence"], 2)
        return (is_new, conf_rank, c["proposed_lane"], -c["mention_count"])

    candidates.sort(key=sort_key)
    return candidates


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------


def lane_summary(candidates: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Count candidates per lane, split into new / already_present."""
    summary: dict[str, dict[str, int]] = defaultdict(lambda: {"new": 0, "already_in_site": 0, "already_in_e1": 0})
    for c in candidates:
        lane = c["proposed_lane"]
        if c["already_in_site"]:
            summary[lane]["already_in_site"] += 1
        elif c["already_in_e1_candidates"]:
            summary[lane]["already_in_e1"] += 1
        else:
            summary[lane]["new"] += 1
    return dict(sorted(summary.items()))


def build_review_template(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Produce a fill-in review sheet for human review."""
    return {
        "version": 1,
        "instructions": (
            "Review each candidate. Set review_action to one of: "
            "approve_encyclopedia, approve_degree_root, reject, already_captured. "
            "If approve_encyclopedia: set final_lane to the target encyclopedia lane. "
            "If approve_degree_root: set final_degree (level1 / level2 / level3). "
            "If already_captured: set note explaining where it already exists."
        ),
        "reviewer": "",
        "reviewed_at": None,
        "decisions": [
            {
                "concept": c["concept"],
                "concept_key": c["concept_key"],
                "proposed_lane": c["proposed_lane"],
                "confidence": c["confidence"],
                "reason_codes": c["reason_codes"],
                "mention_count": c["mention_count"],
                "already_in_site": c["already_in_site"],
                "already_in_e1_candidates": c["already_in_e1_candidates"],
                "e1_decision": c["e1_decision"],
                "review_action": (
                    "already_captured"
                    if (c["already_in_site"] or c["already_in_e1_candidates"])
                    else "defer"
                ),
                "final_lane": c["proposed_lane"] if c["proposed_lane"] != "degree_root_candidate" else "",
                "final_degree": "",
                "note": "",
            }
            for c in candidates
        ],
    }


# ---------------------------------------------------------------------------
# Additional output builders
# ---------------------------------------------------------------------------


def build_dedupe_report(
    all_candidates: list[dict[str, Any]],
    entries_index: dict[str, dict[str, Any]],
    run_id: str,
) -> dict[str, Any]:
    """Build topic_mining_dedupe_report.json — explains every candidate that was suppressed."""
    matched_site: list[dict[str, Any]] = []
    matched_e1: list[dict[str, Any]] = []
    genuinely_new: list[str] = []
    for c in all_candidates:
        if c["already_in_site"]:
            existing = entries_index.get(c["concept_key"]) or {}
            matched_site.append({
                "concept": c["concept"],
                "concept_key": c["concept_key"],
                "mention_count": c["mention_count"],
                "proposed_lane": c["proposed_lane"],
                "matched_to": existing,
            })
        elif c["already_in_e1_candidates"]:
            matched_e1.append({
                "concept": c["concept"],
                "concept_key": c["concept_key"],
                "mention_count": c["mention_count"],
                "proposed_lane": c["proposed_lane"],
                "e1_decision": c["e1_decision"],
            })
        else:
            genuinely_new.append(c["concept"])
    return {
        "run_id": run_id,
        "created_at": utc_timestamp(),
        "total_concepts": len(all_candidates),
        "new_to_site": len(genuinely_new),
        "matched_to_site": len(matched_site),
        "matched_to_e1": len(matched_e1),
        "site_matches": matched_site,
        "e1_matches": matched_e1,
        "new_concept_names": genuinely_new,
    }


def build_summary(
    all_candidates: list[dict[str, Any]],
    new_candidates: list[dict[str, Any]],
    all_hits_count: int,
    source_works: list[str],
    run_id: str,
    min_confidence: str,
) -> dict[str, Any]:
    """Build topic_mining_summary.json."""
    by_lane = lane_summary(all_candidates)
    new_by_lane = {
        lane: counts.get("new", 0)
        for lane, counts in by_lane.items()
        if counts.get("new", 0) > 0
    }
    top_new = [
        {
            "concept": c["concept"],
            "proposed_lane": c["proposed_lane"],
            "confidence": c["confidence"],
            "mention_count": c["mention_count"],
            "reason_codes": c["reason_codes"],
        }
        for c in new_candidates[:20]
    ]
    return {
        "run_id": run_id,
        "created_at": utc_timestamp(),
        "source_works": source_works,
        "min_confidence": min_confidence,
        "total_raw_hits": all_hits_count,
        "unique_concepts_found": len(all_candidates),
        "new_to_site": sum(1 for c in all_candidates if not c["already_in_site"] and not c["already_in_e1_candidates"]),
        "already_in_site": sum(1 for c in all_candidates if c["already_in_site"]),
        "already_in_e1": sum(1 for c in all_candidates if c["already_in_e1_candidates"]),
        "new_by_lane": new_by_lane,
        "all_by_lane": {lane: sum(counts.values()) for lane, counts in by_lane.items()},
        "top_new_candidates": top_new,
    }


def build_current_topic_index(
    entries_index: dict[str, dict[str, Any]],
    site_root: Path,
) -> dict[str, Any]:
    """Build current_topic_index.json — full canonical key index of existing site entries."""
    by_source: dict[str, int] = {}
    for v in entries_index.values():
        f = v.get("source_file", "unknown")
        by_source[f] = by_source.get(f, 0) + 1
    return {
        "generated_at": utc_timestamp(),
        "site_root": str(site_root),
        "total_indexed_keys": len(entries_index),
        "counts_by_file": by_source,
        "entries": entries_index,
    }


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="E2 topic miner: deep same-source body-text scan for unreported Masonic concepts."
    )
    parser.add_argument(
        "--consolidated-dir",
        type=Path,
        default=PDF_HANDLE_ROOT / "consolidated_books",
        help="Directory containing consolidated .md books.",
    )
    parser.add_argument(
        "--routing-config",
        type=Path,
        default=PDF_HANDLE_ROOT / "work_routing.json",
        help="work_routing.json that lists source book names and work_ids.",
    )
    parser.add_argument(
        "--site-root",
        type=Path,
        default=REPO_ROOT / "sites" / "work" / "v0.5",
        help="Site root for dedup against existing entries.",
    )
    parser.add_argument(
        "--e1-staging",
        type=Path,
        default=None,
        help="Path to E1 staging directory (contains discovery_rows.json for dedup).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PDF_HANDLE_ROOT / "runs" / "v21r1-e2" / "mining",
        help="Output directory for candidates and review template.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default="v21r1-e2",
        help="Run identifier embedded in output files.",
    )
    parser.add_argument(
        "--work-id",
        action="append",
        default=[],
        help="Optional filter: only mine this work_id. Repeatable.",
    )
    parser.add_argument(
        "--min-confidence",
        choices=["high", "medium"],
        default="medium",
        help="Minimum confidence to include a candidate.",
    )
    parser.add_argument(
        "--include-already-captured",
        action="store_true",
        help="Include candidates already in site or E1 in the output (for audit purposes).",
    )
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    consolidated_dir: Path = args.consolidated_dir.resolve()
    site_root: Path = args.site_root.resolve()
    output_dir: Path = args.output_dir.resolve()
    routing_path: Path = args.routing_config.resolve()

    ensure_dir(output_dir)

    # Load routing config
    routing = read_json(routing_path)
    works = routing.get("works", [])
    if args.work_id:
        works = [w for w in works if w["work_id"] in set(args.work_id)]
    print(f"[e2-miner] works to scan: {len(works)}")

    # Build dedup sets
    entries_index = load_existing_entries_index(site_root)
    existing_titles = frozenset(entries_index.keys())
    e1_decisions: dict[str, str] = {}
    if args.e1_staging:
        staging_dir = args.e1_staging.resolve()
        e1_decisions = load_e1_decisions(staging_dir)
        print(f"[e2-miner] E1 staging loaded: {len(e1_decisions)} title decisions")

    # Confidence filter
    conf_include = {"high"} if args.min_confidence == "high" else {"high", "medium"}

    # Mine each work
    all_hits: list[dict[str, Any]] = []
    for work in works:
        book_name = work["source_book_name"]
        work_id = work["work_id"]
        work_title = work.get("work_title", work_id)
        md_path = consolidated_dir / f"{book_name}.md"
        if not md_path.exists():
            print(f"[e2-miner] WARNING: markdown not found: {md_path}", file=sys.stderr)
            continue

        # Filter vocab by confidence
        vocab_filtered = [v for v in COMPILED_VOCAB if v[3] in conf_include]

        print(f"[e2-miner] mining {work_id} ({md_path.name}) ...")
        hits = mine_work(work_id, work_title, md_path, vocab_filtered)
        print(f"[e2-miner]   raw hits: {len(hits)}")
        all_hits.extend(hits)

    print(f"[e2-miner] total raw hits: {len(all_hits)}")

    # Aggregate — keep ALL candidates first (for dedup report)
    all_candidates = aggregate_candidates(all_hits, existing_titles, e1_decisions)
    print(f"[e2-miner] unique concepts found: {len(all_candidates)}")

    # New candidates only (for main output)
    new_candidates = [
        c for c in all_candidates
        if not c["already_in_site"] and not c["already_in_e1_candidates"]
    ]
    print(f"[e2-miner] after dedup filter: {len(new_candidates)} "
          f"(removed {len(all_candidates) - len(new_candidates)} already captured)")

    # Decide output set
    candidates = all_candidates if args.include_already_captured else new_candidates

    # Lane summary
    summary = lane_summary(all_candidates)
    new_total = sum(v.get("new", 0) for v in summary.values())

    print(f"\n[e2-miner] Results by proposed lane:")
    for lane, counts in summary.items():
        total_lane = sum(counts.values())
        print(f"  {lane:<48} new={counts.get('new', 0):>3}  "
              f"e1={counts.get('already_in_e1', 0):>3}  "
              f"site={counts.get('already_in_site', 0):>3}  total={total_lane:>3}")
    print(f"  {'TOTAL':<48} new={new_total:>3}")

    source_work_ids = [w["work_id"] for w in works]

    # ── 1. topic_mining_candidates.json ─────────────────────────────────────
    output_doc: dict[str, Any] = {
        "version": 1,
        "created_at": utc_timestamp(),
        "run_id": args.run_id,
        "source_works": source_work_ids,
        "vocabulary_entries": len(VOCABULARY),
        "min_confidence": args.min_confidence,
        "total_candidates": len(candidates),
        "new_candidates": new_total,
        "by_proposed_lane": {
            lane: counts.get("new", 0) for lane, counts in summary.items()
        },
        "candidates": candidates,
    }
    candidates_path = output_dir / "topic_mining_candidates.json"
    write_json(candidates_path, output_doc)

    # ── 2. topic_mining_review_template.json ─────────────────────────────────
    template_path = output_dir / "topic_mining_review_template.json"
    write_json(template_path, build_review_template(new_candidates))

    # ── 3. topic_mining_dedupe_report.json ───────────────────────────────────
    dedupe_report = build_dedupe_report(all_candidates, entries_index, args.run_id)
    dedupe_path = output_dir / "topic_mining_dedupe_report.json"
    write_json(dedupe_path, dedupe_report)

    # ── 4. topic_mining_summary.json ─────────────────────────────────────────
    summary_doc = build_summary(
        all_candidates, new_candidates, len(all_hits),
        source_work_ids, args.run_id, args.min_confidence,
    )
    summary_path = output_dir / "topic_mining_summary.json"
    write_json(summary_path, summary_doc)

    # ── 5. current_topic_index.json ──────────────────────────────────────────
    topic_index_doc = build_current_topic_index(entries_index, site_root)
    topic_index_path = output_dir / "current_topic_index.json"
    write_json(topic_index_path, topic_index_doc)

    print(f"\n[e2-miner] candidates:       {candidates_path}")
    print(f"[e2-miner] review template:  {template_path}")
    print(f"[e2-miner] dedupe report:    {dedupe_path}")
    print(f"[e2-miner] summary:          {summary_path}")
    print(f"[e2-miner] topic index:      {topic_index_path}")

    # Top new candidates
    if new_candidates:
        print(f"\n[e2-miner] Top new candidates:")
        for c in new_candidates[:20]:
            print(
                f"  [{c['confidence']:>6}] [{c['proposed_lane']:<42}]  "
                f"{c['concept']:<35}  mentions={c['mention_count']:>3}"
            )


if __name__ == "__main__":
    main()
