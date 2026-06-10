"""degree_root_preview.py

Preview-only: shows what two approve_degree_root entries would look like when
added to level1.json (The Altar) and level3.json (Sanctum Sanctorum).
No writes to any site file.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
sys.stdout.reconfigure(encoding="utf-8")

from PDF_handle.prod.core.io import write_json  # noqa: E402


def load_json(path: pathlib.Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    site_root = REPO_ROOT / "sites" / "work" / "v0.5" / "data"
    l1 = load_json(site_root / "level1.json")
    l3 = load_json(site_root / "level3.json")
    l1_entries = l1["entries"]
    l3_entries = l3["entries"]
    l1_slugs = {e["slug"] for e in l1_entries}
    l3_slugs = {e["slug"] for e in l3_entries}

    # ------------------------------------------------------------------
    # Proposed entry: The Altar -> level1
    # type=symbol  category=lodge_structure
    # ------------------------------------------------------------------
    altar_entry: dict = {
        "title": "The Altar",
        "slug": "the-altar",
        "type": "symbol",
        "degree": "level1",
        "applies_to_degrees": ["level1", "level2", "level3"],
        "category": "lodge_structure",
        "parent_topic": "degree-1-entered-apprentice",
        "aliases": [
            "the lodge altar",
            "masonic altar",
            "altar of obligation",
            "מזבח הלשכה",
        ],
        "keywords": [
            "altar",
            "lodge furniture",
            "obligation",
            "volume of the sacred law",
            "three great lights",
            "central lodge",
            "מזבח",
        ],
        "related_topics": {
            "prior": ["degree-1-entered-apprentice"],
            "companion": [
                "the-three-great-and-three-lesser-lights",
                "hakafot-circumambulation",
                "nesi-halishka",
            ],
            "deeper": [
                "l1-obligation-chovot-haach-badraga-harishona",
                "great-architect-of-the-universe",
            ],
        },
        "short_summary": (
            "The altar is the central piece of lodge furniture, positioned in the middle "
            "of the lodge room, on which the Three Great Lights — the Volume of the Sacred "
            "Law, the Square, and the Compasses — are displayed."
        ),
        "full_summary": (
            "The altar stands at the center of the lodge room, equidistant from East, West, "
            "and South, and serves as the focal point of all three degrees. The Volume of the "
            "Sacred Law lies open upon it, flanked by the Square and Compasses — the Three "
            "Great Lights of Freemasonry. Candidates kneel at the altar to take their "
            "obligations. Brethren advance toward it in circumambulation. In sorrow rituals, "
            "the altar is draped in mourning cloth. During dedication ceremonies, the altar "
            "marks the midpoint between the East and the lodge entrance. The altar is not "
            "merely furniture; it is the ritual center of the lodge — the point where the "
            "candidate commits, where light is received, and where the lodge's symbolic "
            "work is oriented."
        ),
        "practical_elements": [
            "The Three Great Lights (VSL, Square, Compasses) are displayed on the altar in all three degrees.",
            "Candidates kneel at the altar to take the obligation of each degree.",
            "The altar is draped in mourning cloth during a Lodge of Sorrow ceremony.",
            (
                "In dedication of a Masonic hall, the altar is placed midway between the East "
                "and the entrance before Grand Officers enter."
            ),
        ],
        "symbolic_meaning": (
            "The altar represents the meeting point between the candidate and the divine — "
            "the place of commitment, illumination, and moral responsibility."
        ),
        "candidate_lesson": (
            "What does it mean to kneel at the altar, and what is the candidate committing "
            "to in the presence of the Three Great Lights?"
        ),
        "tradition_notes": [
            (
                "Duncan's Monitor (1866) and the Blue Lodge Ritual Reference Guide both treat "
                "the altar as a fixed central element of the lodge room across all three degrees."
            ),
            (
                "141 mentions across 5 source sections confirm the altar as the "
                "highest-frequency lodge structure term not yet in the knowledge system."
            ),
        ],
        "caution_notes": [
            (
                "The altar is a lodge structure concept, not a religious altar in the "
                "conventional sense. Keep symbolic meaning distinct from religious devotion."
            )
        ],
        "source_notes": [
            "Source: Blue Lodge Ritual Reference Guide (2021) — sections 0089, 0094, 0095, 0160, 0175."
        ],
        "source_work_id": "blue-lodge-ritual-reference-guide-2021",
        "status": "draft",
    }

    # ------------------------------------------------------------------
    # Proposed entry: Sanctum Sanctorum -> level3
    # type=topic  category=lesson
    # ------------------------------------------------------------------
    sanctum_entry: dict = {
        "title": "Sanctum Sanctorum",
        "slug": "sanctum-sanctorum",
        "type": "topic",
        "degree": "level3",
        "applies_to_degrees": ["level3"],
        "category": "lesson",
        "parent_topic": "level3-gate",
        "aliases": [
            "Holy of Holies",
            "holy of holies of king solomon's temple",
            "masters lodge",
        ],
        "keywords": [
            "sanctum sanctorum",
            "holy of holies",
            "king solomon's temple",
            "master mason",
            "third degree",
            "inner chamber",
        ],
        "related_topics": {
            "prior": ["level3-gate"],
            "companion": [
                "the-legend-of-hiram-abiff-and-the-setting-maul",
                "the-trowel",
            ],
            "deeper": [],
        },
        "short_summary": (
            "The Sanctum Sanctorum — Holy of Holies of King Solomon's Temple — is the "
            "innermost and most sacred chamber of the Temple, and the symbolic destination "
            "of the Master Mason's journey."
        ),
        "full_summary": (
            "In Masonic tradition, the Sanctum Sanctorum (Latin: Holy of Holies) refers to "
            "the innermost chamber of King Solomon's Temple — the most sacred space, to "
            "which only the High Priest could enter. Masonic usage extends this concept "
            "architecturally: a Master Mason's Lodge is styled 'the Sanctum Sanctorum, or "
            "Holy of Holies of King Solomon's Temple.' Duncan's Monitor frames the term as "
            "the defining spatial metaphor for the third degree — the lodge room itself "
            "becomes the inner sanctum. Hiram Abiff enters the Sanctum Sanctorum daily at "
            "high noon; this habit is central to the legend of the third degree. The concept "
            "operates on two levels: as an architectural reference to the Temple, and as a "
            "symbolic framing of the Master Mason's lodge as the site where the deepest "
            "lessons of the craft are encountered."
        ),
        "practical_elements": [
            "A Master Mason's Lodge is formally styled 'the Sanctum Sanctorum, or Holy of Holies of King Solomon's Temple.'",
            (
                "Hiram Abiff's daily entry into the Sanctum Sanctorum at high twelve is the "
                "setting for the central event of the third degree legend."
            ),
            (
                "The term appears across the EA, FC, and MM sections of Duncan — confirming "
                "it as a cross-degree architectural anchor."
            ),
        ],
        "symbolic_meaning": (
            "The Sanctum Sanctorum represents the innermost sanctuary of knowledge and "
            "character — the aspiration of the Master Mason to reach the highest and most "
            "sacred level of the craft's teaching."
        ),
        "candidate_lesson": (
            "Why is the Master Mason's lodge called the Holy of Holies, and what does it "
            "mean to work within a space styled after the innermost chamber of Solomon's Temple?"
        ),
        "tradition_notes": [
            (
                "Duncan's Ritual and Monitor (1866) uses 'Sanctum Sanctorum' as the formal "
                "name for the Master Mason's lodge in sections 0001, 0002, 0007, 0008, and 0009."
            ),
            (
                "28 mentions across 5 consecutive sections spanning the Preface through the "
                "Hiram Abiff chapter confirm this as a central architectural concept of the third degree."
            ),
        ],
        "caution_notes": [
            (
                "Do not conflate the Sanctum Sanctorum with the Holy of Holies as a purely "
                "religious concept. In Masonic usage it is architectural and symbolic, not liturgical."
            )
        ],
        "source_notes": [
            "Source: Duncan's Masonic Ritual and Monitor (1866) — sections 0001, 0002, 0007, 0008, 0009."
        ],
        "source_work_id": "duncans-ritual-monitor-1866",
        "status": "draft",
    }

    # ------------------------------------------------------------------
    # Print preview
    # ------------------------------------------------------------------
    SEP = "=" * 70

    print(SEP)
    print("DEGREE-ROOT APPLY PREVIEW  [no writes]")
    print(SEP)

    print()
    print("ENTRY 1: The Altar  ->  sites/work/v0.5/data/level1.json")
    slug_ok = "the-altar" not in l1_slugs
    print(f"  slug collision:        {'OK — free' if slug_ok else 'COLLISION — already exists'}")
    print(f"  level1 entries before: {len(l1_entries)}")
    print(f"  level1 entries after:  {len(l1_entries) + 1}")
    print(f"  action:                APPEND")
    print()
    print("  Proposed entry JSON:")
    print(json.dumps(altar_entry, ensure_ascii=False, indent=4))

    print()
    print(SEP)
    print()
    print("ENTRY 2: Sanctum Sanctorum  ->  sites/work/v0.5/data/level3.json")
    slug_ok2 = "sanctum-sanctorum" not in l3_slugs
    print(f"  slug collision:        {'OK — free' if slug_ok2 else 'COLLISION — already exists'}")
    print(f"  level3 entries before: {len(l3_entries)}")
    print(f"  level3 entries after:  {len(l3_entries) + 1}")
    print(f"  action:                APPEND")
    print()
    print("  Proposed entry JSON:")
    print(json.dumps(sanctum_entry, ensure_ascii=False, indent=4))

    print()
    print(SEP)
    print("SUMMARY")
    print("  added:   2  (the-altar -> level1,  sanctum-sanctorum -> level3)")
    print("  merged:  0")
    print("  skipped: 0")
    print("  writes:  NONE (preview only)")
    print(SEP)

    # Write preview report
    out = REPO_ROOT / "PDF_handle" / "runs" / "v21r1-e2" / "review_package" / "apply_reports" / "degree_root_preview.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    preview_doc = {
        "preview": True,
        "run_id": "v21r1-e2-degree-root-preview",
        "summary": {"added": 2, "merged": 0, "skipped": 0},
        "entries": [
            {"file": "level1.json", "action": "add", "slug": "the-altar", "entry": altar_entry},
            {"file": "level3.json", "action": "add", "slug": "sanctum-sanctorum", "entry": sanctum_entry},
        ],
    }
    write_json(out, preview_doc)
    print(f"\n[preview] report written: {out}")


if __name__ == "__main__":
    main()
