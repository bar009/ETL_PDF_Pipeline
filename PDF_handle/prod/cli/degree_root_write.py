"""degree_root_write.py

Write the two approve_degree_root entries from E2 review:
  - The Altar       -> sites/work/v0.5/data/level1.json
  - Sanctum Sanctorum -> sites/work/v0.5/data/level3.json

Appends only. Does not touch any existing entry.
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

SITE = REPO_ROOT / "sites" / "work" / "v0.5" / "data"

ALTAR_ENTRY: dict = {
    "title": "The Altar",
    "slug": "the-altar",
    "type": "symbol",
    "degree": "level1",
    "applies_to_degrees": ["level1", "level2", "level3"],
    "category": "lodge_structure",
    "parent_topic": "degree-1-entered-apprentice",
    "aliases": ["the lodge altar", "masonic altar", "altar of obligation", "מזבח הלשכה"],
    "keywords": [
        "altar", "lodge furniture", "obligation",
        "volume of the sacred law", "three great lights", "central lodge", "מזבח",
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

SANCTUM_ENTRY: dict = {
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
        "sanctum sanctorum", "holy of holies", "king solomon's temple",
        "master mason", "third degree", "inner chamber",
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


def load(path: pathlib.Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path: pathlib.Path, data: dict) -> None:
    write_json(path, data)


def qa_check(entries: list[dict], new_slug: str, all_slugs: set[str]) -> list[str]:
    issues = []
    entry = next(e for e in entries if e["slug"] == new_slug)
    # Slug uniqueness already enforced by assertion before append
    # Check related_topic slugs exist in known universe
    rt = entry.get("related_topics", {})
    for rel_type, slugs in rt.items():
        for s in slugs:
            if s not in all_slugs:
                issues.append(f"related_topics.{rel_type}: '{s}' not found in any site file")
    if entry.get("parent_topic") and entry["parent_topic"] not in all_slugs:
        issues.append(f"parent_topic: '{entry['parent_topic']}' not found in any site file")
    return issues


def main() -> None:
    # Load all data files to build a complete slug universe for QA
    data_files = {
        "level1.json": SITE / "level1.json",
        "level2.json": SITE / "level2.json",
        "level3.json": SITE / "level3.json",
        "encyclopedia.json": SITE / "encyclopedia.json",
        "library.json": SITE / "library.json",
    }
    all_slugs: set[str] = set()
    file_data: dict[str, dict] = {}
    for fname, fpath in data_files.items():
        d = load(fpath)
        file_data[fname] = d
        entries = d if isinstance(d, list) else d.get("entries", d.get("items", []))
        for e in entries:
            if e.get("slug"):
                all_slugs.add(e["slug"])

    l1 = file_data["level1.json"]
    l3 = file_data["level3.json"]
    l1_entries: list[dict] = l1["entries"]
    l3_entries: list[dict] = l3["entries"]

    before_l1 = len(l1_entries)
    before_l3 = len(l3_entries)

    # Guard
    assert "the-altar" not in {e["slug"] for e in l1_entries}, "ABORT: the-altar already exists in level1"
    assert "sanctum-sanctorum" not in {e["slug"] for e in l3_entries}, "ABORT: sanctum-sanctorum already exists in level3"

    # Append
    l1_entries.append(ALTAR_ENTRY)
    l3_entries.append(SANCTUM_ENTRY)
    all_slugs.add("the-altar")
    all_slugs.add("sanctum-sanctorum")

    # Write
    save(SITE / "level1.json", l1)
    save(SITE / "level3.json", l3)

    after_l1 = len(l1_entries)
    after_l3 = len(l3_entries)

    # QA
    qa_altar = qa_check(l1_entries, "the-altar", all_slugs)
    qa_sanctum = qa_check(l3_entries, "sanctum-sanctorum", all_slugs)

    print("[write] level1.json  the-altar written")
    print("[write] level3.json  sanctum-sanctorum written")
    print()
    print("=== COUNTS ===")
    print(f"  level1.json  {before_l1} -> {after_l1}  (+1)")
    print(f"  level3.json  {before_l3} -> {after_l3}  (+1)")
    print(f"  added:   2")
    print(f"  merged:  0")
    print(f"  skipped: 0")
    print()
    print("=== QA ===")
    print(f"  the-altar         slug collision: NONE")
    if qa_altar:
        for issue in qa_altar:
            print(f"  the-altar         BROKEN LINK: {issue}")
    else:
        print(f"  the-altar         related_topics: all slugs resolve OK")

    print(f"  sanctum-sanctorum slug collision: NONE")
    if qa_sanctum:
        for issue in qa_sanctum:
            print(f"  sanctum-sanctorum BROKEN LINK: {issue}")
    else:
        print(f"  sanctum-sanctorum related_topics: all slugs resolve OK")

    qa_pass = not qa_altar and not qa_sanctum
    print()
    print(f"  QA status: {'PASS' if qa_pass else 'ISSUES FOUND'}")


if __name__ == "__main__":
    main()
