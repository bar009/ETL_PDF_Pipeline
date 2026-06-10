"""e2_apply_review_rules.py

Apply the user-specified review rules to topic_mining_review_template.json
and write an updated template.  Read-only with respect to site data.

Rules applied:
  1. approve_degree_root for the 2 approved entries (The Altar L1, Sanctum Sanctorum L3).
     The other 4 user-listed entries are already in the site → already_captured.
  2. Dedupe: follow dedupe_report recommendations strictly.
  3. approve_encyclopedia for all high-confidence terms in the 5 approved lanes.
  4. reject: incomplete phrases + generic terms.
  5. already_captured: anything already present in site under a different slug.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for _c in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(_c) not in sys.path:
        sys.path.insert(0, str(_c))

from PDF_handle.prod.core.io import read_json, utc_timestamp, write_json


# ---------------------------------------------------------------------------
# Decision map  (concept_key -> decision dict)
# Keys that do not appear here keep their default "defer" action.
# ---------------------------------------------------------------------------

# Format:
#   "concept_key": {
#       "review_action":   one of approve_degree_root / approve_encyclopedia /
#                          already_captured / reject / defer,
#       "canonical_title": override display title  (optional),
#       "canonical_slug":  override auto-slug       (optional),
#       "final_degree":    level1/level2/level3     (approve_degree_root only),
#       "final_lane":      encyclopedia lane        (approve_encyclopedia only),
#       "merge_existing_slug": slug of canonical    (already_captured only),
#       "review_reason":   human-readable note,
#   }

DECISIONS: dict[str, dict[str, str]] = {

    # =========================================================================
    # RULE 1 – approve_degree_root (only 2 are genuinely new)
    # =========================================================================

    "the altar": {
        "review_action": "approve_degree_root",
        "final_degree": "level1",
        "canonical_title": "The Altar",
        "review_reason": "Rule 1: user-approved degree_root. Central lodge furniture; level1.",
    },
    "sanctum sanctorum": {
        "review_action": "approve_degree_root",
        "final_degree": "level3",
        "canonical_title": "Sanctum Sanctorum",
        "review_reason": "Rule 1: user-approved degree_root. Master Mason architectural concept; level3.",
    },

    # The other 4 user-listed entries are already in the site
    "middle chamber": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-middle-chamber",
        "review_reason": "Rule 1/5: user-listed degree_root, already in level2 (the-middle-chamber).",
    },
    "winding staircase": {
        "review_action": "already_captured",
        "merge_existing_slug": "flight-of-winding-stairs",
        "review_reason": "Rule 1/5: user-listed degree_root, already in level2 (flight-of-winding-stairs).",
    },
    "five points of fellowship": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-five-points-of-fellowship",
        "review_reason": "Rule 1/5: user-listed degree_root, already in level3 (the-five-points-of-fellowship).",
    },
    # Boaz + Jachin: user wanted one combined entry, but it already exists
    "boaz": {
        "review_action": "already_captured",
        "merge_existing_slug": "two-brazen-pillars-boaz-and-jachin",
        "review_reason": "Rule 1/5: user-listed as Boaz and Jachin combined; already in level2 (two-brazen-pillars-boaz-and-jachin).",
    },
    "jachin": {
        "review_action": "already_captured",
        "merge_existing_slug": "two-brazen-pillars-boaz-and-jachin",
        "review_reason": "Rule 2/5: dedupe — Jachin is the other pillar; already in level2 as two-brazen-pillars-boaz-and-jachin.",
    },

    # =========================================================================
    # RULE 2 – dedupe (within-candidate pairs)
    # =========================================================================

    # Winding Stairs → Winding Staircase (both already in site)
    "winding stairs": {
        "review_action": "already_captured",
        "merge_existing_slug": "flight-of-winding-stairs",
        "review_reason": "Rule 2/5: dedupe + already in level2. Canonical form: Winding Staircase (flight-of-winding-stairs).",
    },

    # Cable Tow → Cable-Tow (both already in site)
    "cable tow": {
        "review_action": "already_captured",
        "merge_existing_slug": "cable-tow",
        "review_reason": "Rule 2/5: dedupe (Cable-Tow is canonical) + already in level1 (cable-tow).",
    },
    "cable-tow": {
        "review_action": "already_captured",
        "merge_existing_slug": "cable-tow",
        "review_reason": "Rule 5: already in level1 (cable-tow).",
    },

    # Trestle-Board → Trestle Board (both already in site)
    "trestle-board": {
        "review_action": "already_captured",
        "merge_existing_slug": "movable-jewels-ashlars-and-trestle-board",
        "review_reason": "Rule 2/5: dedupe (Trestle Board is canonical) + already in level1 (movable-jewels-ashlars-and-trestle-board).",
    },
    "trestle board": {
        "review_action": "already_captured",
        "merge_existing_slug": "movable-jewels-ashlars-and-trestle-board",
        "review_reason": "Rule 5: already in level1 (movable-jewels-ashlars-and-trestle-board).",
    },

    # Plumb-Rule → Plumb Rule (both already in site as plumb-level-and-square)
    "plumb-rule": {
        "review_action": "already_captured",
        "merge_existing_slug": "plumb-level-and-square",
        "review_reason": "Rule 2/5: dedupe (Plumb Rule is canonical) + already in level2 (plumb-level-and-square).",
    },
    "plumb rule": {
        "review_action": "already_captured",
        "merge_existing_slug": "plumb-level-and-square",
        "review_reason": "Rule 5: already in level2 (plumb-level-and-square).",
    },

    # Cardinal Virtues → Four Cardinal Virtues
    "cardinal virtues": {
        "review_action": "already_captured",
        "merge_existing_slug": "four-cardinal-virtues",
        "review_reason": "Rule 2: dedupe — Four Cardinal Virtues is the canonical (more specific) form.",
    },

    # Desaguliers → John Theophilus Desaguliers
    "desaguliers": {
        "review_action": "already_captured",
        "merge_existing_slug": "john-theophilus-desaguliers",
        "review_reason": "Rule 2: dedupe — John Theophilus Desaguliers is the canonical full-name entry.",
    },

    # Knight Templar → Knights Templar
    "knight templar": {
        "review_action": "already_captured",
        "merge_existing_slug": "knights-templar",
        "review_reason": "Rule 2: dedupe — Knights Templar (plural) is the canonical Masonic usage.",
    },

    # Seven Liberal Arts → Liberal Arts And Sciences  (both already in level2)
    "seven liberal arts": {
        "review_action": "already_captured",
        "merge_existing_slug": "seven-liberal-arts-and-sciences",
        "review_reason": "Rule 2/5: dedupe + already in level2 (seven-liberal-arts-and-sciences).",
    },
    "liberal arts and sciences": {
        "review_action": "already_captured",
        "merge_existing_slug": "seven-liberal-arts-and-sciences",
        "review_reason": "Rule 5: already in level2 (seven-liberal-arts-and-sciences).",
    },

    # All Seeing Eye → The All-Seeing Eye (already in level3)
    "all seeing eye": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-all-seeing-eye",
        "canonical_title": "All-Seeing Eye",
        "review_reason": "Rule 2/5: dedupe (All-Seeing Eye is canonical) + already in level3 (the-all-seeing-eye).",
    },

    # Holy Of Holies → Sanctum Sanctorum (the new approved entry)
    "holy of holies": {
        "review_action": "already_captured",
        "merge_existing_slug": "sanctum-sanctorum",
        "review_reason": "Rule 2: dedupe — Holy of Holies is the Hebrew synonym; Sanctum Sanctorum is the approved canonical entry.",
    },

    # Hiram, King Of Tyre → Hiram of Tyre (title fix, not a dedupe of Hiram Abiff)
    "hiram, king of tyre": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Hiram of Tyre",
        "canonical_slug": "hiram-of-tyre",
        "review_reason": "Rule 3: approve_encyclopedia/history. Title corrected: Hiram of Tyre (the Tyrian craftsman, distinct from Hiram Abiff).",
    },

    # Anderson'S Constitutions title fix (Python .title() artefact)
    "anderson's constitutions": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Anderson's Constitutions",
        "canonical_slug": "andersons-constitutions",
        "review_reason": "Rule 3: approve_encyclopedia/history. Title corrected: Anderson's Constitutions (1723 historical document).",
    },

    # Book Of Constitutions: DIFFERENT from Anderson's Constitutions
    "book of constitutions": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_symbols_tools",
        "canonical_title": "Book of Constitutions",
        "review_reason": "Rule 3: approve_encyclopedia/symbols_tools. Lodge symbol (Book of Constitutions guarded by the Tiler's Sword). Distinct from Anderson's Constitutions.",
    },

    # Gaotu → already_captured pointing to Great Architect of the Universe
    "gaotu": {
        "review_action": "already_captured",
        "merge_existing_slug": "great-architect-of-the-universe",
        "review_reason": "Rule 2: GAOTU is the abbreviation; Great Architect of the Universe is the canonical entry.",
    },

    # =========================================================================
    # RULE 3 – approve_encyclopedia (high confidence, approved lanes only)
    # =========================================================================

    # — encyclopedia_symbols_tools (high conf, new in site) —
    "pot of incense": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_symbols_tools",
        "canonical_title": "Pot of Incense",
        "review_reason": "Rule 3: approve_encyclopedia/symbols_tools. Masonic emblem of purity.",
    },
    "sword pointing to a naked heart": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_symbols_tools",
        "canonical_title": "Sword Pointing to a Naked Heart",
        "review_reason": "Rule 3: approve_encyclopedia/symbols_tools. Lodge symbol representing justice.",
    },
    "pickaxe": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_symbols_tools",
        "canonical_title": "Pickaxe",
        "review_reason": "Rule 3: approve_encyclopedia/symbols_tools. Working tool of the third degree.",
    },

    # — encyclopedia_ritual_reference (high conf, new in site) —
    "foundation stone": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Foundation Stone Ceremony",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. Ceremonial laying of foundation stones.",
    },
    "fellow craft degree": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Fellow Craft Degree",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. Degree name and ritual overview.",
    },
    "lodge of sorrow": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Lodge of Sorrow",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. Memorial ceremony for deceased Masons.",
    },
    "entered apprentice degree": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Entered Apprentice Degree",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. Degree name and ritual overview.",
    },
    "grand honors": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Grand Honors",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. Ritual salute performed in lodge.",
    },
    "investiture": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Investiture",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. Formal clothing of a candidate.",
    },
    "ceremony of initiation": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Ceremony of Initiation",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. First degree initiation ceremony.",
    },
    "installation of officers": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Installation of Officers",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. Annual ceremony installing lodge officers.",
    },
    "great architect of the universe": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Great Architect of the Universe",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. Central Masonic invocation of the divine.",
    },
    "volume of the sacred law": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Volume of the Sacred Law",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. One of the Three Great Lights; the holy book on the altar.",
    },
    "test oath": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Test Oath",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. Tiler's oath confirming lodge is properly tiled.",
    },
    "charge at initiation": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Charge at Initiation",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. Ritual address after initiation.",
    },
    "charge at passing": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Charge at Passing",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. Ritual address after passing.",
    },
    "three lesser lights": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-three-great-and-three-lesser-lights",
        "review_reason": "Rule 5: already in level1 (the-three-great-and-three-lesser-lights).",
    },
    "ceremony of passing": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Ceremony of Passing",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. Second degree ceremony.",
    },
    "charge at raising": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_ritual_reference",
        "canonical_title": "Charge at Raising",
        "review_reason": "Rule 3: approve_encyclopedia/ritual_reference. Ritual address after raising.",
    },
    "perambulation": {
        "review_action": "already_captured",
        "merge_existing_slug": "hakafot-circumambulation",
        "review_reason": "Rule 5: perambulation and circumambulation are synonymous in lodge ritual; already in level1 (hakafot-circumambulation).",
    },

    # — encyclopedia_officers_governance (high conf, new in site) —
    "deputy grand master": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_officers_governance",
        "canonical_title": "Deputy Grand Master",
        "review_reason": "Rule 3: approve_encyclopedia/officers_governance.",
    },
    "grand lecturer": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_officers_governance",
        "canonical_title": "Grand Lecturer",
        "review_reason": "Rule 3: approve_encyclopedia/officers_governance.",
    },
    "past grand master": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_officers_governance",
        "canonical_title": "Past Grand Master",
        "review_reason": "Rule 3: approve_encyclopedia/officers_governance.",
    },
    "inner guard": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_officers_governance",
        "canonical_title": "Inner Guard",
        "review_reason": "Rule 3: approve_encyclopedia/officers_governance. British lodge officer equivalent to Junior Deacon.",
    },

    # — encyclopedia_history (high conf, new in site) —
    "king solomon": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "King Solomon",
        "review_reason": "Rule 3: approve_encyclopedia/history. Central figure in Masonic tradition and legend.",
    },
    "grand lodge of scotland": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Grand Lodge of Scotland",
        "review_reason": "Rule 3: approve_encyclopedia/history. Historical Masonic institution founded 1736.",
    },
    "elias ashmole": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Elias Ashmole",
        "review_reason": "Rule 3: approve_encyclopedia/history. Seventeenth-century antiquary; one of the earliest recorded Freemasons (1646).",
    },
    "quatuor coronati": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Quatuor Coronati Lodge",
        "canonical_slug": "quatuor-coronati-lodge",
        "review_reason": "Rule 3: approve_encyclopedia/history. Premier Masonic research lodge (Lodge No. 2076, London, est. 1884).",
    },
    "grand lodge of england": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Grand Lodge of England",
        "review_reason": "Rule 3: approve_encyclopedia/history. Premier Grand Lodge, founded 1717; the Mother Grand Lodge.",
    },
    "illustrations of masonry": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Illustrations of Masonry",
        "review_reason": "Rule 3: approve_encyclopedia/history. Influential 18th-century Masonic work by William Preston.",
    },
    "schaw statutes": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Schaw Statutes",
        "review_reason": "Rule 3: approve_encyclopedia/history. 1598–1599 regulatory documents by William Schaw; foundational to operative Masonic history.",
    },
    "ahiman rezon": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Ahiman Rezon",
        "review_reason": "Rule 3: approve_encyclopedia/history. Book of Constitutions of the Antient Grand Lodge; compiled by Laurence Dermott.",
    },
    "st. clair charters": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "St. Clair Charters",
        "review_reason": "Rule 3: approve_encyclopedia/history. Scottish historical Masonic documents relating to the St. Clair family.",
    },
    "premier grand lodge": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Premier Grand Lodge",
        "review_reason": "Rule 3: approve_encyclopedia/history. The original Grand Lodge of England (Moderns), founded 1717.",
    },
    "william preston": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "William Preston",
        "review_reason": "Rule 3: approve_encyclopedia/history. 18th-century Masonic author and educator; creator of the Preston lecture system.",
    },
    "george oliver": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "George Oliver",
        "review_reason": "Rule 3: approve_encyclopedia/history. 19th-century English Masonic historian and author.",
    },
    "albert pike": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Albert Pike",
        "review_reason": "Rule 3: approve_encyclopedia/history. Author of Morals and Dogma; key figure in the Scottish Rite.",
    },
    "john theophilus desaguliers": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "John Theophilus Desaguliers",
        "review_reason": "Rule 3: approve_encyclopedia/history. Third Grand Master of the Premier Grand Lodge; instrumental in Masonic expansion.",
    },
    "antients": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Antients (Grand Lodge)",
        "canonical_slug": "antients-grand-lodge",
        "review_reason": "Rule 3: approve_encyclopedia/history. Rival Grand Lodge (1751–1813), formally 'Ancient Grand Lodge of England'.",
    },

    # — encyclopedia_higher_degrees_reference (high conf, new in site) —
    "royal arch": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_higher_degrees_reference",
        "canonical_title": "Royal Arch",
        "review_reason": "Rule 3: approve_encyclopedia/higher_degrees_reference. Seventh degree in the York Rite; the 'completion of the third degree'.",
    },
    "mark master": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_higher_degrees_reference",
        "canonical_title": "Mark Master",
        "review_reason": "Rule 3: approve_encyclopedia/higher_degrees_reference. Fourth degree in the York Rite.",
    },
    "past master": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_higher_degrees_reference",
        "canonical_title": "Past Master (Virtual)",
        "canonical_slug": "past-master-virtual",
        "review_reason": "Rule 3: approve_encyclopedia/higher_degrees_reference. Fifth degree in the York Rite (Virtual Past Master).",
    },
    "most excellent master": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_higher_degrees_reference",
        "canonical_title": "Most Excellent Master",
        "review_reason": "Rule 3: approve_encyclopedia/higher_degrees_reference. Sixth degree in the York Rite.",
    },
    "knights templar": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_higher_degrees_reference",
        "canonical_title": "Knights Templar",
        "review_reason": "Rule 3: approve_encyclopedia/higher_degrees_reference. Chivalric order within the York Rite.",
    },
    "scottish rite": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_higher_degrees_reference",
        "canonical_title": "Scottish Rite",
        "review_reason": "Rule 3: approve_encyclopedia/higher_degrees_reference. Appendant body with 4th–33rd degrees.",
    },
    "fourth degree": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_higher_degrees_reference",
        "canonical_title": "Fourth Degree (Mark Master)",
        "canonical_slug": "fourth-degree-mark-master",
        "review_reason": "Rule 3: approve_encyclopedia/higher_degrees_reference. Fourth degree = Mark Master in the York Rite.",
    },
    "grand chapter": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_higher_degrees_reference",
        "canonical_title": "Grand Chapter",
        "review_reason": "Rule 3: approve_encyclopedia/higher_degrees_reference. Governing body of the Royal Arch.",
    },
    "rose croix": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_higher_degrees_reference",
        "canonical_title": "Rose Croix (18th Degree)",
        "canonical_slug": "rose-croix-18th-degree",
        "review_reason": "Rule 3: approve_encyclopedia/higher_degrees_reference. 18th degree of the Scottish Rite.",
    },
    "york rite": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_higher_degrees_reference",
        "canonical_title": "York Rite",
        "review_reason": "Rule 3: approve_encyclopedia/higher_degrees_reference. Appendant body comprising Chapter, Council, and Commandery.",
    },
    "mystic shrine": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_higher_degrees_reference",
        "canonical_title": "Mystic Shrine (Shriners)",
        "canonical_slug": "mystic-shrine-shriners",
        "review_reason": "Rule 3: approve_encyclopedia/higher_degrees_reference. Fraternal body requiring Master Mason membership.",
    },
    "a.a.s. rite": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_higher_degrees_reference",
        "canonical_title": "A.A.S. Rite (Ancient Accepted Scottish Rite)",
        "canonical_slug": "aasr-ancient-accepted-scottish-rite",
        "review_reason": "Rule 3: approve_encyclopedia/higher_degrees_reference.",
    },

    # =========================================================================
    # RULE 4 – reject
    # =========================================================================

    "dedication of": {
        "review_action": "reject",
        "review_reason": "Rule 4: incomplete phrase — trailing preposition captures sentence fragments, not a named concept.",
    },
    "lecture": {
        "review_action": "reject",
        "review_reason": "Rule 4: too generic — 'lecture' appears in many non-Masonic contexts; no single Masonic referent.",
    },
    "installation": {
        "review_action": "reject",
        "review_reason": "Rule 4: too generic — specific form 'Installation of Officers' is approved separately.",
    },
    "the holy bible": {
        "review_action": "reject",
        "review_reason": "Rule 4: too generic — the Bible as a Masonic object is covered by 'Volume of the Sacred Law'.",
    },
    "grand architect": {
        "review_action": "reject",
        "review_reason": "Rule 4: generic fragment — the canonical form 'Great Architect of the Universe' is approved separately.",
    },
    "moral duties": {
        "review_action": "reject",
        "review_reason": "Rule 4: too generic — not a named Masonic concept; medium confidence.",
    },
    "great principles": {
        "review_action": "reject",
        "review_reason": "Rule 4: too generic — 'three great principles' (high conf) is approved separately in foundational.",
    },
    "columns": {
        "review_action": "reject",
        "review_reason": "Rule 4: too generic — architectural term without a specific Masonic referent at this level.",
    },
    "chisel": {
        "review_action": "reject",
        "review_reason": "Rule 4: medium confidence, generic carpentry term. The specific working-tool pair (gavel + chisel) is covered by makevet-ve-izmel in level1.",
    },

    # =========================================================================
    # RULE 5 – already_captured (site entries missed by the miner's title check)
    # =========================================================================

    "worshipful master": {
        "review_action": "already_captured",
        "merge_existing_slug": "nesi-halishka",
        "review_reason": "Rule 5: already in level1 as nesi-halishka (נשיא הלשכה).",
    },
    "senior warden": {
        "review_action": "already_captured",
        "merge_existing_slug": "mefakeach-rishon",
        "review_reason": "Rule 5: already in level1 as mefakeach-rishon (מפקח ראשון).",
    },
    "junior warden": {
        "review_action": "already_captured",
        "merge_existing_slug": "mefakeach-sheni",
        "review_reason": "Rule 5: already in level1 as mefakeach-sheni (מפקח שני).",
    },
    "tyler": {
        "review_action": "already_captured",
        "merge_existing_slug": "shoer-tyler",
        "review_reason": "Rule 5: already in level1 as shoer-tyler (שוער).",
    },
    "tiler": {
        "review_action": "already_captured",
        "merge_existing_slug": "shoer-tyler",
        "review_reason": "Rule 2/5: dedupe (Tyler is canonical) + already in level1 as shoer-tyler.",
    },
    "hoodwink": {
        "review_action": "already_captured",
        "merge_existing_slug": "preparation-hoodwink-and-cable-tow",
        "review_reason": "Rule 5: already in level1 (preparation-hoodwink-and-cable-tow).",
    },
    "northeast corner": {
        "review_action": "already_captured",
        "merge_existing_slug": "placement-in-the-northeast-corner",
        "review_reason": "Rule 5: already in level1 (placement-in-the-northeast-corner).",
    },
    "three great lights": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-three-great-and-three-lesser-lights",
        "review_reason": "Rule 5: already in level1 (the-three-great-and-three-lesser-lights).",
    },
    "rough ashlar": {
        "review_action": "already_captured",
        "merge_existing_slug": "even-gvil",
        "review_reason": "Rule 5: already in level1 as even-gvil (אבן גוויל).",
    },
    "perfect ashlar": {
        "review_action": "already_captured",
        "merge_existing_slug": "even-gazit",
        "review_reason": "Rule 5: already in level1 as even-gazit (אבן גזית).",
    },
    "mosaic pavement": {
        "review_action": "already_captured",
        "merge_existing_slug": "ritzpat-hapsifas",
        "review_reason": "Rule 5: already in level1 as ritzpat-hapsifas (רצפת הפסיפס).",
    },
    "blazing star": {
        "review_action": "already_captured",
        "merge_existing_slug": "hakochav-hazohar",
        "review_reason": "Rule 5: already in level1 as hakochav-hazohar (הכוכב הזוהר).",
    },
    "tessellated border": {
        "review_action": "already_captured",
        "merge_existing_slug": "misgeret-meshunenet",
        "review_reason": "Rule 5: already in level1 as misgeret-meshunenet (המסגרת המשוננת).",
    },
    "point within a circle": {
        "review_action": "already_captured",
        "merge_existing_slug": "nekuda-betoch-igul",
        "review_reason": "Rule 5: already in level1 as nekuda-betoch-igul (נקודה בתוך עיגול).",
    },
    "lewis": {
        "review_action": "already_captured",
        "merge_existing_slug": "lewis",
        "review_reason": "Rule 5: already in level1 as lewis (לואיס).",
    },
    "twenty-four inch gauge": {
        "review_action": "already_captured",
        "merge_existing_slug": "working-tools-24-inch-gauge-and-common-gavel",
        "review_reason": "Rule 5: already in level1 (working-tools-24-inch-gauge-and-common-gavel).",
    },
    "common gavel": {
        "review_action": "already_captured",
        "merge_existing_slug": "working-tools-24-inch-gauge-and-common-gavel",
        "review_reason": "Rule 5: already in level1 (working-tools-24-inch-gauge-and-common-gavel).",
    },
    "circumambulation": {
        "review_action": "already_captured",
        "merge_existing_slug": "hakafot-circumambulation",
        "review_reason": "Rule 5: already in level1 as hakafot-circumambulation (הקפות).",
    },
    "due guard": {
        "review_action": "already_captured",
        "merge_existing_slug": "l1-tools-siman-due-guard-vehavchana-taksit",
        "review_reason": "Rule 5: already in level1 (l1-tools-siman-due-guard-vehavchana-taksit).",
    },
    "forty-seventh problem": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-forty-seventh-problem-of-euclid",
        "review_reason": "Rule 5: already in level2 (the-forty-seventh-problem-of-euclid).",
    },
    "euclid": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-forty-seventh-problem-of-euclid",
        "review_reason": "Rule 5: Euclid is referenced through the Forty-Seventh Problem entry in level2.",
    },
    "five orders of architecture": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-five-orders-of-architecture",
        "review_reason": "Rule 5: already in level2 (the-five-orders-of-architecture).",
    },
    "hiram abiff": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-legend-of-hiram-abiff-and-the-setting-maul",
        "review_reason": "Rule 5: already in level3 (the-legend-of-hiram-abiff-and-the-setting-maul).",
    },
    "setting maul": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-legend-of-hiram-abiff-and-the-setting-maul",
        "review_reason": "Rule 5: already in level3 (the-legend-of-hiram-abiff-and-the-setting-maul).",
    },
    "trowel": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-trowel",
        "review_reason": "Rule 5: already in level3 (the-trowel).",
    },
    "three steps": {
        "review_action": "already_captured",
        "merge_existing_slug": "the-three-steps",
        "review_reason": "Rule 5: already in level3 (the-three-steps).",
    },
    "sprig of acacia": {
        "review_action": "already_captured",
        "merge_existing_slug": "acacia-grave-and-immortality-relationship",
        "review_reason": "Rule 5: already in level3 (acacia-grave-and-immortality-relationship).",
    },
    "senior deacon": {
        "review_action": "already_captured",
        "merge_existing_slug": "enc-senior-and-junior-deacons",
        "review_reason": "Rule 5: already in encyclopedia as enc-senior-and-junior-deacons.",
    },
    "junior deacon": {
        "review_action": "already_captured",
        "merge_existing_slug": "enc-senior-and-junior-deacons",
        "review_reason": "Rule 5: already in encyclopedia as enc-senior-and-junior-deacons.",
    },
}


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def apply_decisions(
    template: dict[str, Any],
    decisions: dict[str, dict[str, str]],
) -> tuple[dict[str, Any], dict[str, list[str]]]:
    """
    Returns (updated_template, action_summary).
    Mutates a deep-copy of the decisions list.
    """
    import copy
    tmpl = copy.deepcopy(template)

    action_counts: dict[str, list[str]] = {
        "approve_encyclopedia": [],
        "approve_degree_root": [],
        "already_captured": [],
        "reject": [],
        "defer": [],
        "unchanged": [],
    }

    for d in tmpl["decisions"]:
        ck = d["concept_key"]
        override = decisions.get(ck)
        if override is None:
            action_counts["unchanged"].append(ck)
            continue
        for field, value in override.items():
            d[field] = value
        action_counts.setdefault(d["review_action"], []).append(ck)

    tmpl["reviewer"] = "automated — rule application v1"
    tmpl["reviewed_at"] = utc_timestamp()
    tmpl["version"] = 2

    return tmpl, action_counts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    review_dir = PDF_HANDLE_ROOT / "runs" / "v21r1-e2" / "review_package"
    template_in = review_dir / "topic_mining_review_template.json"
    template_out = review_dir / "topic_mining_review_template_filled.json"

    if not template_in.exists():
        print(f"[error] template not found: {template_in}", file=sys.stderr)
        sys.exit(1)

    template = read_json(template_in.resolve())
    filled, summary = apply_decisions(template, DECISIONS)

    # Validate coverage
    all_keys = {d["concept_key"] for d in filled["decisions"]}
    declared_keys = set(DECISIONS.keys())
    unmapped = declared_keys - all_keys
    if unmapped:
        print(f"[warn] declared decision keys not found in template: {unmapped}", file=sys.stderr)

    write_json(template_out, filled)

    # Print summary
    total = sum(len(v) for v in summary.values())
    print(f"\nDecision summary ({total} decisions):")
    for action in ("approve_degree_root", "approve_encyclopedia", "already_captured", "reject", "defer", "unchanged"):
        items = summary.get(action, [])
        if items:
            print(f"  {action:<24} {len(items):>3}")
    print()

    print(f"approve_degree_root ({len(summary['approve_degree_root'])}):")
    for ck in summary["approve_degree_root"]:
        d = next(x for x in filled["decisions"] if x["concept_key"] == ck)
        print(f"  {d['canonical_title']:<40} -> {d['final_degree']}")

    print(f"\napprove_encyclopedia ({len(summary['approve_encyclopedia'])}):")
    by_lane: dict[str, list[str]] = {}
    for ck in summary["approve_encyclopedia"]:
        d = next(x for x in filled["decisions"] if x["concept_key"] == ck)
        by_lane.setdefault(d["final_lane"], []).append(d["canonical_title"])
    for lane in sorted(by_lane):
        print(f"  [{lane}]")
        for t in by_lane[lane]:
            print(f"    {t}")

    print(f"\nalready_captured ({len(summary['already_captured'])}):")
    for ck in summary["already_captured"]:
        d = next(x for x in filled["decisions"] if x["concept_key"] == ck)
        print(f"  {d['title']:<40} -> {d['merge_existing_slug']}")

    print(f"\nreject ({len(summary['reject'])}):")
    for ck in summary["reject"]:
        d = next(x for x in filled["decisions"] if x["concept_key"] == ck)
        print(f"  {d['title']}")

    print(f"\ndefer ({len(summary['defer'])}) [unchanged from template]:")
    for ck in summary.get("unchanged", []):
        d = next(x for x in filled["decisions"] if x["concept_key"] == ck)
        if d["review_action"] == "defer":
            print(f"  {d['title']:<40} [{d['proposed_lane']}]")

    print(f"\n[output] {template_out}")


if __name__ == "__main__":
    main()
