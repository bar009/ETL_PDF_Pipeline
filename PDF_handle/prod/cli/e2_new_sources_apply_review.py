"""e2_new_sources_apply_review.py

Fills the E2 new-sources review template with human-reviewed decisions.
Run ID: v21r1-e2-new-sources-2026-04-24

No site writes. Produces filled topic_mining_review_template_filled.json only.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
for cand in (REPO_ROOT,):
    if str(cand) not in sys.path:
        sys.path.insert(0, str(cand))

from PDF_handle.prod.core.io import write_json
from PDF_handle.prod.core.text import canonical_match_key

# ---------------------------------------------------------------------------
# Review decisions  (concept_key -> decision dict)
# Keys are canonical_match_key() of the display concept name
# ---------------------------------------------------------------------------

DECISIONS: dict[str, dict] = {

    # ── degree_root_candidate — high confidence ──────────────────────────────

    "three ruffians": {
        "review_action": "already_captured",
        "note": "Covered by the-legend-of-hiram-abiff-and-the-setting-maul (level3). "
                "Three Ruffians are agents of that legend, not a separate pedagogical unit.",
        "merge_existing_slug": "the-legend-of-hiram-abiff-and-the-setting-maul",
    },
    "middle chamber": {
        "review_action": "already_captured",
        "note": "the-middle-chamber exists in level2.json.",
        "merge_existing_slug": "the-middle-chamber",
    },
    "jachin": {
        "review_action": "already_captured",
        "note": "two-brazen-pillars-boaz-and-jachin (level2) covers both pillars.",
        "merge_existing_slug": "two-brazen-pillars-boaz-and-jachin",
    },
    "forty seventh problem": {
        "review_action": "already_captured",
        "note": "the-forty-seventh-problem-of-euclid exists in level2.json.",
        "merge_existing_slug": "the-forty-seventh-problem-of-euclid",
    },
    "boaz": {
        "review_action": "already_captured",
        "note": "two-brazen-pillars-boaz-and-jachin (level2) covers both pillars.",
        "merge_existing_slug": "two-brazen-pillars-boaz-and-jachin",
    },
    "cubic stone": {
        "review_action": "reject",
        "note": "Only 2 mentions. Rough Ashlar (even-gvil) and Perfect Ashlar (even-gazit) "
                "already cover the stone-working progression. Cubic stone is a niche variant "
                "not central to blue lodge curriculum.",
    },
    "pythagorean theorem": {
        "review_action": "already_captured",
        "note": "the-forty-seventh-problem-of-euclid (level2) IS the Pythagorean theorem "
                "in Masonic context. Same concept, different name.",
        "merge_existing_slug": "the-forty-seventh-problem-of-euclid",
    },
    "five points of fellowship": {
        "review_action": "already_captured",
        "note": "the-five-points-of-fellowship exists in level3.json.",
        "merge_existing_slug": "the-five-points-of-fellowship",
    },

    # ── encyclopedia_foundational — high confidence ──────────────────────────

    "cardinal virtues": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_foundational",
        "canonical_title": "Cardinal Virtues",
        "note": "Individual virtues exist as separate entries (Prudence in level1, "
                "Temperance and Justice in encyclopedia) but no concept entry ties "
                "them together as the Four Cardinal Virtues. Genuine foundational gap.",
    },
    "three ancient grand masters": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_foundational",
        "canonical_title": "Three Ancient Grand Masters",
        "note": "Solomon (enc-king-solomon) and Hiram of Tyre (enc-hiram-of-tyre) exist "
                "separately, but the triadic structure — the three joint holders of the "
                "Master Mason secrets — has no dedicated entry. Central to the third-degree "
                "narrative.",
    },

    # ── encyclopedia_higher_degrees_reference — high confidence ──────────────

    "rose croix": {
        "review_action": "already_captured",
        "note": "enc-rose-croix-18th-degree exists in encyclopedia.json.",
        "merge_existing_slug": "enc-rose-croix-18th-degree",
    },

    # ── encyclopedia_history — high confidence ────────────────────────────────

    "hiram abiff": {
        "review_action": "already_captured",
        "note": "the-legend-of-hiram-abiff-and-the-setting-maul and "
                "hiram-loss-and-fidelity-system both exist in level3.json. "
                "Concept is fully covered across multiple entries.",
        "merge_existing_slug": "the-legend-of-hiram-abiff-and-the-setting-maul",
    },
    "hiram king of tyre": {
        "review_action": "already_captured",
        "note": "enc-hiram-of-tyre exists in encyclopedia.json. Canonical match confirmed.",
        "merge_existing_slug": "enc-hiram-of-tyre",
    },
    "desaguliers": {
        "review_action": "already_captured",
        "note": "enc-john-theophilus-desaguliers exists in encyclopedia.json. "
                "Short-form name match.",
        "merge_existing_slug": "enc-john-theophilus-desaguliers",
    },
    "morals and dogma": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_history",
        "canonical_title": "Morals and Dogma",
        "note": "Albert Pike exists as enc-albert-pike but his foundational book has no "
                "separate entry. 2 mentions in new sources. Significant historical reference "
                "work for the Scottish Rite; encyclopedic treatment warranted.",
    },

    # ── encyclopedia_officers_governance — high confidence ───────────────────

    "junior deacon": {
        "review_action": "already_captured",
        "note": "enc-senior-and-junior-deacons exists in encyclopedia.json covering both roles.",
        "merge_existing_slug": "enc-senior-and-junior-deacons",
    },

    # ── encyclopedia_ritual_reference — high confidence ──────────────────────

    "due guard": {
        "review_action": "already_captured",
        "note": "l1-tools-siman-due-guard-vehavchana-taksit (level1) covers Due-Guard within "
                "the level 1 signs and recognition entry. Named explicitly in the slug.",
        "merge_existing_slug": "l1-tools-siman-due-guard-vehavchana-taksit",
    },
    "three great lights": {
        "review_action": "already_captured",
        "note": "the-three-great-and-three-lesser-lights exists in level1.json.",
        "merge_existing_slug": "the-three-great-and-three-lesser-lights",
    },

    # ── encyclopedia_symbols_tools — high confidence ─────────────────────────

    "sprig of acacia": {
        "review_action": "already_captured",
        "note": "acacia-grave-and-immortality-relationship (level3) covers the Sprig of Acacia "
                "within its full symbolic context of immortality.",
        "merge_existing_slug": "acacia-grave-and-immortality-relationship",
    },
    "setting maul": {
        "review_action": "already_captured",
        "note": "the-legend-of-hiram-abiff-and-the-setting-maul (level3) covers the Setting "
                "Maul as the instrument of Hiram Abiff's death.",
        "merge_existing_slug": "the-legend-of-hiram-abiff-and-the-setting-maul",
    },
    "all seeing eye": {
        "review_action": "already_captured",
        "note": "the-all-seeing-eye exists in level3.json.",
        "merge_existing_slug": "the-all-seeing-eye",
    },
    "trestle board": {
        "review_action": "already_captured",
        "note": "movable-jewels-ashlars-and-trestle-board (level1) covers the Trestle Board. "
                "luach-hadraga (level1) is the Hebrew-titled equivalent.",
        "merge_existing_slug": "movable-jewels-ashlars-and-trestle-board",
    },
    "common gavel": {
        "review_action": "already_captured",
        "note": "working-tools-24-inch-gauge-and-common-gavel (level1) covers Common Gavel "
                "together with the 24-inch gauge.",
        "merge_existing_slug": "working-tools-24-inch-gauge-and-common-gavel",
    },

    # ── degree_root_candidate — medium confidence ────────────────────────────

    "columns": {
        "review_action": "already_captured",
        "note": "two-brazen-pillars-boaz-and-jachin (level2) covers the pillars/columns. "
                "22 mentions are noise from general architectural use of the word.",
        "merge_existing_slug": "two-brazen-pillars-boaz-and-jachin",
    },
    "euclid": {
        "review_action": "already_captured",
        "note": "the-forty-seventh-problem-of-euclid (level2) subsumes Euclid — the Masonic "
                "significance of Euclid is exclusively the 47th Problem.",
        "merge_existing_slug": "the-forty-seventh-problem-of-euclid",
    },
    "three steps": {
        "review_action": "already_captured",
        "note": "the-three-steps exists in level3.json.",
        "merge_existing_slug": "the-three-steps",
    },

    # ── encyclopedia_glossary — medium confidence ────────────────────────────

    "dispensation": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_glossary",
        "canonical_title": "Dispensation",
        "note": "No existing entry. A Dispensation is formal grand lodge authority permitting "
                "a lodge to act outside normal procedures. 4 mentions across sources. "
                "Distinct governance concept not covered anywhere in the baseline.",
    },

    # ── encyclopedia_officers_governance — medium confidence ─────────────────

    "master of ceremonies": {
        "review_action": "approve_encyclopedia",
        "final_lane": "encyclopedia_officers_governance",
        "canonical_title": "Master of Ceremonies",
        "note": "No existing entry. enc-senior-and-junior-deacons, enc-inner-guard cover "
                "other officers. Master of Ceremonies is a distinct officer role not "
                "captured anywhere. 10 mentions.",
    },

    # ── encyclopedia_ritual_reference — medium confidence ────────────────────

    "installation": {
        "review_action": "already_captured",
        "note": "enc-installation-of-officers exists. 288 mentions are noise — the word "
                "appears in every description of the ceremony.",
        "merge_existing_slug": "enc-installation-of-officers",
    },
    "lecture": {
        "review_action": "reject",
        "note": "Too broad and noisy. Lecture refers to the catechism/instructional portion "
                "of each degree but is not a standalone Masonic concept. 10 mentions are "
                "distributed use across sources with no single encyclopedic scope.",
    },
    "the holy bible": {
        "review_action": "already_captured",
        "note": "enc-volume-of-the-sacred-law covers this — the VSL is the inclusive term; "
                "the Holy Bible is its primary instance. Captured at the correct abstraction level.",
        "merge_existing_slug": "enc-volume-of-the-sacred-law",
    },
    "grand architect": {
        "review_action": "already_captured",
        "note": "enc-great-architect-of-the-universe covers this. Grand Architect is a "
                "shortened form of GAOTU. 5 mentions are all references to the same concept.",
        "merge_existing_slug": "enc-great-architect-of-the-universe",
    },
}


def norm(s: str) -> str:
    return canonical_match_key(s)


def main() -> None:
    run_dir = REPO_ROOT / "PDF_handle/runs/v21r1-e2-new-sources-2026-04-24/mining"
    template_path = run_dir / "topic_mining_review_template.json"
    out_path = run_dir / "topic_mining_review_template_filled.json"

    template = json.loads(template_path.read_text("utf-8"))
    decisions = template["decisions"]

    # Pre-normalize DECISIONS keys
    normalized_decisions = {norm(k): v for k, v in DECISIONS.items()}

    filled_count = 0
    unmatched = []
    for d in decisions:
        ck = norm(d.get("concept_key", "") or d.get("concept", ""))
        override = normalized_decisions.get(ck)
        if override:
            d.update(override)
            filled_count += 1
        else:
            unmatched.append(d["concept"])

    # Summary
    counts = Counter(d["review_action"] for d in decisions)
    print(f"[e2-review] Filled {filled_count} / {len(decisions)} decisions")
    print()
    for action, n in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {action:<28} {n:>3}")
    print(f"  {'TOTAL':<28} {len(decisions):>3}")

    if unmatched:
        print(f"\n[e2-review] UNMATCHED (no decision written):")
        for c in unmatched:
            print(f"  - {c}")

    # Approved entries
    approved = [d for d in decisions if d["review_action"] == "approve_encyclopedia"]
    print(f"\n[e2-review] Net-new approve_encyclopedia ({len(approved)}):")
    for d in approved:
        print(f"  [{d['final_lane']:<42}]  {d['canonical_title']}")

    template["decisions"] = decisions
    write_json(out_path, template)
    print(f"\n[e2-review] Written: {out_path}")


if __name__ == "__main__":
    main()
