"""
Restructure Enrichment Blocks — hubs/mega-topics into parent + child topics.

Enrichment ops (existing_match) appended source-section blocks into hub
entries and into already-large topics. The result: hubs carrying 38K of
mixed text and topics with 100+ unrelated blocks (observed 2026-06-12 in
the level2 review). The agreed hierarchy is category -> hub -> topic ->
sub-topic, with hubs as light gateways.

Per flagged entry (hub with blocks, or topic above --mega-chars):
- Parse the PDF_STAGE5 blocks out of full_summary.
- Score each block's relevance to its host (token overlap between the
  block's source-section title/body and the host title+category).
- Relevant block -> child entry (parent_topic = host slug, same category,
  status draft, title from the block's source-section title). Each block
  (work:section) becomes a child at most once across the whole degree —
  the highest-relevance host wins; elsewhere it is just removed.
- Irrelevant or garbage-titled block -> removed. Nothing is lost: every
  block's full text lives in the library lane chapter it came from.
- Host keeps its own base text (text before the first marker).

Dry-run by default; --apply writes with backups via the structure-backup
convention.

    python PDF_handle/prod/cli/restructure_enrichment_blocks.py --site-root <ROOT> [--degree level2] [--apply]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for _candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

BLOCK_RE = re.compile(
    r"<!-- PDF_STAGE5:([^>]+?) -->\n(.*?)<!-- /PDF_STAGE5:\1 -->\n?", re.S
)
SECTION_TITLE_RE = re.compile(r"^Source section:\s*(.+)$", re.M)
WORK_HEADER_RE = re.compile(r"^### Enrichment from\s+(.+)$", re.M)

STOPWORDS = {
    "the", "and", "of", "in", "a", "an", "to", "for", "with", "on", "at",
    "from", "its", "this", "that", "section", "degree", "masonic", "masonry",
    "mason", "masons", "lodge", "freemasonry", "part", "vol", "page",
}

GARBAGE_TITLE_RE = re.compile(r"[�]|^\W*$|^\d|^[ivxlc]+\.|earlybritish", re.IGNORECASE)


def tokens(text: str) -> set[str]:
    return {
        w for w in re.findall(r"[a-z]{3,}", text.lower())
        if w not in STOPWORDS
    }


def category_words(category_id: str) -> set[str]:
    return tokens(category_id.replace("_", " "))


def parse_blocks(full_summary: str) -> tuple[str, list[dict]]:
    base = BLOCK_RE.sub("", full_summary).strip()
    blocks = []
    for m in BLOCK_RE.finditer(full_summary):
        key, body = m.group(1).strip(), m.group(2)
        title_m = SECTION_TITLE_RE.search(body)
        work_m = WORK_HEADER_RE.search(body)
        blocks.append({
            "key": key,
            "work_id": key.split(":", 1)[0],
            "raw": m.group(0),
            "section_title": (title_m.group(1).strip() if title_m else ""),
            "work_title": (work_m.group(1).strip() if work_m else key.split(":", 1)[0]),
            "body": body,
        })
    return base, blocks


def relevance(block: dict, host_title: str, host_category: str) -> int:
    host = tokens(host_title) | category_words(host_category)
    blk = tokens(block["section_title"]) | tokens(block["body"][:400])
    return len(host & blk)


def clean_title(text: str) -> str:
    text = re.sub(r"\s*\(?Part \d+\)?\.?$", "", text.strip())
    return text.strip(" .—-")


def child_slug(host_slug: str, block_key: str) -> str:
    sec = block_key.split(":", 1)[1] if ":" in block_key else block_key
    work = block_key.split(":", 1)[0]
    raw = f"{host_slug}-sub-{work[:20]}-{sec}".replace("_", "-").lower()
    return re.sub(r"-{2,}", "-", raw).strip("-")


def plan_degree(dataset: dict, *, degree: str, mega_chars: int) -> dict:
    entries = dataset["entries"]
    hosts = []
    for e in entries:
        fs = e.get("full_summary") or ""
        if "PDF_STAGE5" not in fs:
            continue
        if e.get("type") == "hub" or len(fs) >= mega_chars:
            hosts.append(e)
    # Highest-relevance host claims a block; ties -> first host in entry order.
    claims: dict[str, tuple[int, str]] = {}
    parsed: dict[str, tuple[str, list[dict]]] = {}
    for e in hosts:
        base, blocks = parse_blocks(e.get("full_summary") or "")
        parsed[e["slug"]] = (base, blocks)
        for b in blocks:
            score = relevance(b, e.get("title", ""), e.get("category", ""))
            if score > claims.get(b["key"], (-1, ""))[0]:
                claims[b["key"]] = (score, e["slug"])

    existing_slugs = {e["slug"] for e in entries}
    plan = {"degree": degree, "hosts": [], "children": [], "dropped": 0}
    for e in hosts:
        base, blocks = parsed[e["slug"]]
        kept_children, removed = [], 0
        for b in blocks:
            score, owner = claims[b["key"]]
            title = clean_title(b["section_title"])
            is_garbage = bool(GARBAGE_TITLE_RE.search(title)) or len(title) < 4
            if owner == e["slug"] and score >= 1 and not is_garbage:
                slug = child_slug(e["slug"], b["key"])
                if slug not in existing_slugs:
                    existing_slugs.add(slug)
                    kept_children.append({
                        "title": title,
                        "slug": slug,
                        "type": "topic",
                        "degree": degree,
                        "category": e.get("category"),
                        "parent_topic": e["slug"],
                        "related_topics": {},
                        "short_summary": b["body"].split("\n\n", 1)[-1].strip()[:240],
                        "full_summary": b["raw"].strip(),
                        "source_notes": [f"{b['work_title']} | {b['section_title']} | split from {e['slug']}"],
                        "status": "draft",
                        "work_id": b["work_id"],
                    })
                else:
                    removed += 1
            else:
                removed += 1
        plan["hosts"].append({
            "slug": e["slug"], "type": e.get("type"), "title": e.get("title"),
            "base_chars": len(base), "blocks": len(blocks),
            "children": len(kept_children), "removed_blocks": removed,
        })
        plan["children"].extend(kept_children)
        plan["dropped"] += removed
    return plan


def apply_plan(dataset: dict, plan: dict) -> None:
    by_slug = {e["slug"]: e for e in dataset["entries"]}
    for host in plan["hosts"]:
        e = by_slug[host["slug"]]
        base, _ = parse_blocks(e.get("full_summary") or "")
        e["full_summary"] = base
    dataset["entries"].extend(plan["children"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--degree", action="append", choices=["level1", "level2", "level3"])
    parser.add_argument("--mega-chars", type=int, default=15000)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    degrees = args.degree or ["level1", "level2", "level3"]
    data_dir = args.site_root / "data"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S+00-00")
    backup_dir = data_dir / "structure_backups" / f"block-split-{stamp}"

    for degree in degrees:
        path = data_dir / f"{degree}.json"
        dataset = json.loads(path.read_text(encoding="utf-8"))
        plan = plan_degree(dataset, degree=degree, mega_chars=args.mega_chars)
        mode = "write" if args.apply else "dry-run"
        print(f"[{mode}] {degree}: hosts={len(plan['hosts'])} new_children={len(plan['children'])} blocks_removed={plan['dropped']}")
        for h in plan["hosts"]:
            print(f"   {h['type']:5} {h['title'][:44]:46} blocks={h['blocks']:3} -> children={h['children']:2} removed={h['removed_blocks']:3} base={h['base_chars']}")
        if args.apply and plan["hosts"]:
            backup_dir.mkdir(parents=True, exist_ok=True)
            (backup_dir / f"{degree}.json").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            apply_plan(dataset, plan)
            path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.apply:
        print(f"[backup] {backup_dir}")
        print("[next] run build_degree_structure --apply, then validate_runtime --strict")


if __name__ == "__main__":
    main()
