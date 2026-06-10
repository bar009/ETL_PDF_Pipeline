"""e1_new_sources_apply_review.py

Apply E1 review decisions for v21r1-e1-new-sources-2026-04-24 (127 candidates).
Reads candidate_review_queue.json, writes topic_mining_review_template_filled.json.
No site writes. No apply.
"""
from __future__ import annotations

import copy
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

sys.stdout.reconfigure(encoding="utf-8")

from PDF_handle.prod.core.io import write_json  # noqa: E402

from PDF_handle.prod.core.text import canonical_match_key

RUN_DIR = REPO_ROOT / "PDF_handle" / "runs" / "v21r1-e1-new-sources-2026-04-24"
QUEUE_PATH = RUN_DIR / "review_queue" / "candidate_review_queue.json"
OUT_PATH = RUN_DIR / "review_queue" / "candidate_review_template_filled.json"

# ---------------------------------------------------------------------------
# Decision map: normalized_title (lowercased) -> override dict
# ---------------------------------------------------------------------------
# Actions: approve_encyclopedia | already_captured | reject | defer
# Keys per action:
#   approve_encyclopedia : final_lane, canonical_title, review_reason
#   already_captured     : merge_existing_slug, review_reason
#   reject               : review_reason

DECISIONS: dict[str, dict] = {

    # -----------------------------------------------------------------------
    # DEGREE ROOT CANDIDATE (1) → reject
    # -----------------------------------------------------------------------
    "questions for the master mason": {
        "review_action": "reject",
        "review_reason": "Q&A study-guide section heading, not a named Masonic concept. Questions reference concepts already in the system.",
    },

    # -----------------------------------------------------------------------
    # encyclopedia_foundational (5) → all reject
    # -----------------------------------------------------------------------
    "barbara de poli": {
        "review_action": "reject",
        "review_reason": "Rule 1: person name (author credit), no standalone Masonic concept value.",
    },
    "concerning god and religion": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic chapter heading, 1 mention, not a named Masonic concept.",
    },
    "evolution of the egyptian myth in modern masonry": {
        "review_action": "reject",
        "review_reason": "Rule 1: academic essay section title, 1 mention, too niche for encyclopedia.",
    },
    "the temple and eternity": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic chapter heading, 2 mentions, not a named Masonic concept.",
    },
    "עמוד 5": {
        "review_action": "reject",
        "review_reason": "Rule 1: page label noise (Hebrew 'Page 5').",
    },

    # -----------------------------------------------------------------------
    # encyclopedia_glossary (12)
    # -----------------------------------------------------------------------
    "christ type": {
        "review_action": "reject",
        "review_reason": "Rule 3: theological comparison, 1 mention, not a standard Masonic term.",
    },
    "chronicles 2:11-14": {
        "review_action": "reject",
        "review_reason": "Rule 1: raw scripture reference.",
    },
    "chronicles 4:16": {
        "review_action": "reject",
        "review_reason": "Rule 1: raw scripture reference.",
    },
    "definitions of under-age, dotage and fool": {
        "review_action": "reject",
        "review_reason": "Rule 1: jurisdiction-specific (Ohio) legal definition, not a universal Masonic concept.",
    },
    "hieroglyphic emblems": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_symbols_tools",
        "canonical_title": "Hieroglyphic Emblems",
        "review_reason": "Rule 2: recognized Masonic symbolic category — the Three Pillars (Wisdom, Strength, Beauty) and other emblems as hieroglyphic symbols. Named concept in degree symbolism.",
    },
    "low twelve": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Low Twelve",
        "review_reason": "Rule 2: specific named time-marker in the Third Degree (midnight). 'Low Twelve' is a named ritual term central to the Hiramic legend.",
    },
    "significance of the degree": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic section heading, not a named Masonic concept.",
    },
    "the lion of the tribe of judah": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_symbols_tools",
        "canonical_title": "Lion of the Tribe of Judah",
        "review_reason": "Rule 2: named Masonic symbol. The Lion of the Tribe of Judah is a significant emblem in Third Degree and Royal Arch symbolism, representing the divine name.",
    },
    "the setting maul": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-legend-of-hiram-abiff-and-the-setting-maul",
        "review_reason": "Already in level3.json as part of the Hiram Abiff entry.",
    },
    "the sprig of acacia": {
        "review_action": "already_captured",
        "merge_existing_slug": "acacia-grave-and-immortality-relationship",
        "review_reason": "Already in level3.json.",
    },
    "the three ruffians": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-legend-of-hiram-abiff-and-the-setting-maul",
        "review_reason": "Sub-element of the Hiram Abiff legend; already_captured per E2 decision.",
    },
    "الصفحة 5": {
        "review_action": "reject",
        "review_reason": "Rule 1: page label noise (Arabic 'Page 5').",
    },

    # -----------------------------------------------------------------------
    # encyclopedia_higher_degrees_reference (1) → reject
    # -----------------------------------------------------------------------
    "grand inspectorate of south africa": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body, jurisdiction-specific, not a core encyclopedic concept.",
    },

    # -----------------------------------------------------------------------
    # encyclopedia_history (74)
    # -----------------------------------------------------------------------
    "a biblical history of king solomon's temple": {
        "review_action": "reject",
        "review_reason": "Rule 1: book title, not a Masonic concept entry.",
    },
    "antiquarians and freemasons": {
        "review_action": "reject",
        "review_reason": "Rule 3: 1 mention, section heading, too thin for an encyclopedia entry.",
    },
    "architecture of the temple": {
        "review_action": "reject",
        "review_reason": "Rule 1: section heading, 1 mention, not a named Masonic concept.",
    },
    "aspects of freemasonry in zimbabwe": {
        "review_action": "reject",
        "review_reason": "Rule 1: country/regional entry, not a universal Masonic concept.",
    },
    "aspects of masonry in south africa": {
        "review_action": "reject",
        "review_reason": "Rule 1: country/regional entry.",
    },
    "aspects of masonry in zimbabwe": {
        "review_action": "reject",
        "review_reason": "Rule 1: country/regional entry.",
    },
    "b equitorial grand rite of the gabon": {
        "review_action": "reject",
        "review_reason": "Rule 1: obscure regional obedience, 1 mention.",
    },
    "congo formerly zaïre": {
        "review_action": "reject",
        "review_reason": "Rule 1: country entry, geographic gazetteer material.",
    },
    "factor 1: security": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic section heading fragment.",
    },
    "factor 3: ethnography": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic section heading fragment.",
    },
    "freemasonry in africa": {
        "review_action": "reject",
        "review_reason": "Rule 1: broad geographic survey heading, 1 mention, not a named Masonic concept.",
    },
    "freemasonry in algeria": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in angola": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in botswana": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in cameroon": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in chad": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in comoros": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in congo brazzaville": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in djibouti": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in egypt": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in ethiopia": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in gabon": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in ghana": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in guinea": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in ivory coast": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in kenya": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in lesotho": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in liberia": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in libya": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in mauritania": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in morocco": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in namibia": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in niger": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in st helena": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in sudan": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in swaziland": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in tanzania": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in the gambia": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in togo": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in uganda": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "freemasonry in zambia": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific entry.",
    },
    "grand superintendent of east africa sc": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative position, 1 mention.",
    },
    "illustration 12: solomon, king of israel": {
        "review_action": "reject",
        "review_reason": "Rule 1: illustration label, not a concept entry.",
    },
    "illustration 16: the chambers round about the temple": {
        "review_action": "reject",
        "review_reason": "Rule 1: illustration label.",
    },
    "illustration 18: the most holy place": {
        "review_action": "reject",
        "review_reason": "Rule 1: illustration label.",
    },
    "illustration 19: the bible and the temple": {
        "review_action": "reject",
        "review_reason": "Rule 1: illustration label.",
    },
    "industrial revolution and modern masonry": {
        "review_action": "reject",
        "review_reason": "Rule 1: section heading, 1 mention, too thin.",
    },
    "king solomon's temple and citadel": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic chapter heading; King Solomon already in encyclopedia.",
    },
    "location of the temple": {
        "review_action": "reject",
        "review_reason": "Rule 1: section heading, 1 mention.",
    },
    "lodges of special interest": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic heading, South Africa-specific.",
    },
    "lodges under the grand east of the netherlands": {
        "review_action": "reject",
        "review_reason": "Rule 1: administrative list heading.",
    },
    "loge masina graal 5 holy grail —emulation": {
        "review_action": "reject",
        "review_reason": "Rule 1: specific lodge name, 1 mention.",
    },
    "mauritius île maurice": {
        "review_action": "reject",
        "review_reason": "Rule 1: island/country entry.",
    },
    "medieval history and legend": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic section heading.",
    },
    "medieval masonry": {
        "review_action": "reject",
        "review_reason": "Rule 3: 1 mention, section heading. Too thin; Operative Masonry covers this period adequately.",
    },
    "models of the temple": {
        "review_action": "reject",
        "review_reason": "Rule 3: 2 mentions but section heading; scholarly detail without direct ritual value.",
    },
    "operative to speculative": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Operative to Speculative Masonry",
        "review_reason": "Rule 2: the historical transition from operative craft guilds to speculative Freemasonry is a foundational named concept in Masonic history.",
    },
    "prince hall masonry": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Prince Hall Masonry",
        "review_reason": "Rule 2: major named strand of Masonic history — African American lodges founded 1784, significant institutional history.",
    },
    "rosicrucian temple legend": {
        "review_action": "reject",
        "review_reason": "Rule 3: 1 mention, niche scholarly connection (Rudolf Steiner lecture), not a mainstream Masonic concept.",
    },
    "réunion": {
        "review_action": "reject",
        "review_reason": "Rule 1: island/country entry.",
    },
    "solomon, king of israel": {
        "review_action": "already_captured",
        "merge_existing_slug": "enc-king-solomon",
        "review_reason": "Already in encyclopedia.json as King Solomon.",
    },
    "sénégal": {
        "review_action": "reject",
        "review_reason": "Rule 1: country entry.",
    },
    "the banquet hall in the palace": {
        "review_action": "reject",
        "review_reason": "Rule 1: architectural detail of Solomon's palace, not a Masonic ritual concept.",
    },
    "the bible and the temple": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic chapter heading, 1 mention.",
    },
    "the church and the bible": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic chapter heading, 1 mention.",
    },
    "the house of the forest of lebanon": {
        "review_action": "reject",
        "review_reason": "Rule 3: 1 mention, architectural detail of Solomon's palace complex, no direct Masonic ritual value.",
    },
    "the inner court of the temple": {
        "review_action": "reject",
        "review_reason": "Rule 1: section heading, 1 mention, architectural detail.",
    },
    "the most holy place": {
        "review_action": "already_captured",
        "merge_existing_slug": "sanctum-sanctorum",
        "review_reason": "Synonym for Sanctum Sanctorum, now in level3.json.",
    },
    "the palace of the queen": {
        "review_action": "reject",
        "review_reason": "Rule 1: architectural section heading, not a Masonic concept.",
    },
    "the sanctuary in the tabernacle": {
        "review_action": "reject",
        "review_reason": "Rule 1: architectural section heading, 1 mention.",
    },
    "the temple and early masonry": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic section heading, 1 mention.",
    },
    "the treasure room": {
        "review_action": "reject",
        "review_reason": "Rule 3: 2 mentions, architectural detail of the Temple without direct Masonic ritual connection.",
    },
    "tradition harmonie lumière 1207": {
        "review_action": "reject",
        "review_reason": "Rule 1: specific lodge name, Cameroon.",
    },
    "© 1998, 2000, 2016 kent william henderson & anthony ronald francis pope": {
        "review_action": "reject",
        "review_reason": "Rule 1: copyright notice, pure noise.",
    },

    # -----------------------------------------------------------------------
    # encyclopedia_officers_governance (23)
    # -----------------------------------------------------------------------
    "a grand lodge of the ivory coast": {
        "review_action": "reject",
        "review_reason": "Rule 1: country-specific grand lodge.",
    },
    "b united grand orient and grand lodge of cameroun": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional obedience, 1 mention.",
    },
    "district grand lodge of east africa ec": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body.",
    },
    "district grand lodge of ghana ec": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body.",
    },
    "district grand lodge of ghana sc": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body.",
    },
    "district grand lodge of natal": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body.",
    },
    "district grand lodge of nigeria sc": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body.",
    },
    "district grand lodge of the eastern province of the cape of good hope": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body.",
    },
    "district grand lodge of the western province of the cape of good hope": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body.",
    },
    "district grand lodge of transvaal, orange free state and northern cape": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body.",
    },
    "grand lodge masonry": {
        "review_action": "reject",
        "review_reason": "Rule 3: variant heading for Grand Lodge concept; covered by the GRAND LODGES entry being approved.",
    },
    "grand lodges": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_officers_governance",
        "canonical_title": "Grand Lodges",
        "review_reason": "Rule 2: the Grand Lodge system (supreme authority over one jurisdiction) is a fundamental governance concept. 2 mentions from basic education course.",
    },
    "lodges under the grand lodge of scotland": {
        "review_action": "reject",
        "review_reason": "Rule 1: administrative list heading, Africa-specific.",
    },
    "other lodges and grand lodges": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic section heading.",
    },
    "provincial grand lodge of ghana ic": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body.",
    },
    "provincial grand lodge of natal": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body.",
    },
    "provincial grand lodge of nigeria ic": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body.",
    },
    "provincial grand lodge of south africa, northern": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body.",
    },
    "provincial grand lodge of southern cape province": {
        "review_action": "reject",
        "review_reason": "Rule 1: regional administrative body.",
    },
    "the grand lodge and you": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic section heading.",
    },
    "the grand master": {
        "review_action": "already_captured",
        "merge_existing_slug": "enc-grand-master",
        "review_reason": "Already in encyclopedia.json as Grand Master (E2 apply).",
    },
    "the grand secretary": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_officers_governance",
        "canonical_title": "Grand Secretary",
        "review_reason": "Rule 2: chief administrative officer of a Grand Lodge. Named role, 2 mentions from basic education course.",
    },
    "vouchers on petitioners": {
        "review_action": "reject",
        "review_reason": "Rule 3: jurisdiction-specific procedural requirement (Ohio), 1 mention.",
    },

    # -----------------------------------------------------------------------
    # encyclopedia_ritual_reference (6)
    # -----------------------------------------------------------------------
    "lodge after-proceedings in general": {
        "review_action": "reject",
        "review_reason": "Rule 3: South Africa-specific social customs after lodge meetings, 2 mentions.",
    },
    "nights of installation": {
        "review_action": "reject",
        "review_reason": "Rule 3: South Africa-specific, 1 mention.",
    },
    "solomon's temple spiritualized": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Solomon's Temple Spiritualized",
        "review_reason": "Rule 2: the philosophical reading of Solomon's Temple as a spiritual allegory of the human body and soul — a central interpretive framework in speculative Masonry.",
    },
    "the master mason degree": {
        "review_action": "reject",
        "review_reason": "Rule 1: generic heading, 1 mention.",
    },
    "visiting in general, and nights of installation": {
        "review_action": "reject",
        "review_reason": "Rule 3: South Africa-specific lodge visiting customs, 2 mentions.",
    },
    "who was hiram abiff?": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-legend-of-hiram-abiff-and-the-setting-maul",
        "review_reason": "Already in level3.json.",
    },

    # -----------------------------------------------------------------------
    # encyclopedia_symbols_tools (5)
    # -----------------------------------------------------------------------
    "illustration 7: the table of shewbread": {
        "review_action": "reject",
        "review_reason": "Rule 1: illustration label.",
    },
    "illustration 8: the ark of the covenant": {
        "review_action": "reject",
        "review_reason": "Rule 1: illustration label.",
    },
    "regalia": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_symbols_tools",
        "canonical_title": "Regalia",
        "review_reason": "Rule 2: Masonic regalia (aprons, jewels, collars) is a named and significant symbolic category. 2 mentions.",
    },
    "the molten sea": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_symbols_tools",
        "canonical_title": "The Molten Sea",
        "review_reason": "Rule 2: the Molten Sea (Brazen Sea) is a named bronze basin at Solomon's Temple — a significant Temple artifact with Masonic historical relevance. 2 mentions.",
    },
    "the porch of judgment": {
        "review_action": "reject",
        "review_reason": "Rule 3: architectural detail of Solomon's palace, 2 mentions, no direct Masonic ritual connection.",
    },
}


def norm(s: str) -> str:
    """Canonical match key — strips diacritics, collapses hyphens/punctuation, lowercases."""
    return canonical_match_key(s)


def utc_timestamp() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def main() -> None:
    with open(QUEUE_PATH, encoding="utf-8") as f:
        queue = json.load(f)

    candidates = queue.get("candidates", [])

    # Pre-normalize DECISIONS keys through the same canonical_match_key transform
    # so keys written as "solomon, king of israel" match candidates arriving as
    # "SOLOMON, KING OF ISRAEL" → canonical_match_key → "solomon king of israel".
    NORMALIZED_DECISIONS = {norm(k): v for k, v in DECISIONS.items()}

    # Build template decisions from candidates
    template_decisions = []
    for c in candidates:
        title = c.get("title", "")
        key = norm(title)
        override = NORMALIZED_DECISIONS.get(key)

        d: dict = {
            "title": title,
            "candidate_id": c.get("candidate_id"),
            "normalized_title": c.get("normalized_title", title),
            "concept_key": key,
            "proposed_classification": c.get("proposed_classification"),
            "proposed_lane": c.get("proposed_lane"),
            "confidence": c.get("confidence"),
            "source_work_id": c.get("source_work_id"),
            "section_id": c.get("section_id"),
            "mention_count": c.get("mention_count"),
            "unit_kind": c.get("unit_kind"),
            # decision fields (filled or default)
            "review_action": "defer",
            "canonical_title": title,
            "canonical_slug": "",
            "final_lane": c.get("proposed_lane") or "",
            "merge_existing_slug": "",
            "review_reason": "",
        }

        if override:
            for field, value in override.items():
                d[field] = value
        else:
            # Flag anything without a decision
            d["review_action"] = "defer"
            d["review_reason"] = "No decision mapped — needs manual review."

        template_decisions.append(d)

    # Count outcomes
    from collections import defaultdict
    action_counts: dict[str, list] = defaultdict(list)
    for d in template_decisions:
        action_counts[d["review_action"]].append(d["canonical_title"])

    unmapped = action_counts.get("defer", [])

    # Build output
    filled = {
        "version": 1,
        "run_id": queue.get("run_id"),
        "reviewed_at": utc_timestamp(),
        "reviewer": "automated — rule application v1 (new sources E1)",
        "total": len(template_decisions),
        "decisions": template_decisions,
    }

    write_json(OUT_PATH, filled)

    # Print summary
    print("=" * 60)
    print("E1 NEW SOURCES REVIEW — DECISION SUMMARY")
    print("=" * 60)
    print(f"  Total candidates:       {len(template_decisions)}")
    print()
    for action in ("approve_encyclopedia", "already_captured", "reject", "defer"):
        items = action_counts.get(action, [])
        print(f"  {action:25s}: {len(items)}")
    print()

    if action_counts.get("approve_encyclopedia"):
        from collections import Counter
        by_lane: dict[str, list] = defaultdict(list)
        for d in template_decisions:
            if d["review_action"] == "approve_encyclopedia":
                by_lane[d["final_lane"]].append(d["canonical_title"])
        print("  approve_encyclopedia by lane:")
        for lane, titles in sorted(by_lane.items()):
            print(f"    [{lane}] ({len(titles)})")
            for t in titles:
                print(f"      - {t}")
        print()

    if action_counts.get("already_captured"):
        print("  already_captured:")
        for d in template_decisions:
            if d["review_action"] == "already_captured":
                print(f"    {d['canonical_title']:45s} -> {d['merge_existing_slug']}")
        print()

    if unmapped:
        print(f"  UNMAPPED (defer) — need manual decision:")
        for t in unmapped:
            print(f"    {t}")
        print()

    print(f"  Output: {OUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
