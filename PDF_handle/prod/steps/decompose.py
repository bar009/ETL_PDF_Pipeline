"""Step 6.5 — decompose over-merged entries into sub-topic hubs.

The staging/apply path can accumulate dozens–hundreds of `practical_elements`
into a single entry (see docs and `combine_mapping_results`/`apply_degree_patch`).
That reads as an undivided wall. This step rewrites the work site root's degree
files so any entry whose `practical_elements` exceeds a threshold becomes a
`hub` whose contents are coherent sub-topic child entries:

  - the items are AI-classified into ~ceil(N/40) groups (clamped 5–24);
  - each group becomes a `topic` child carrying its slice (no items lost);
  - the parent's prose (`symbolic_meaning` + `candidate_lesson`) moves to a
    "Concepts and Symbolism" child so the hub body is not itself a wall;
  - the parent becomes `type: hub`, its children wired via `related_topics.deeper`
    and the children's `parent_topic`.

It iterates until no entry exceeds the threshold (so oversized children split
again), and is idempotent: a re-run finds nothing over threshold and writes
nothing. Output is schema-normalized via `normalize_degree_data`, so Step 7 QA
validates it.

Usage:
    python PDF_handle/prod/steps/decompose.py --site-root <work_site_root> --threshold 40
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import ensure_dir, read_json, utc_timestamp, write_json
from PDF_handle.prod.core.site_data import build_site_data_paths
from PDF_handle.prod.providers.gemini import generate_json_content
from PDF_handle.prod.schema import (
    normalize_degree_data,
    serialize_degree_data,
    unique_strings,
)

DEGREE_IDS = ["level1", "level2", "level3"]
DEFAULT_THRESHOLD = 40
DEFAULT_MODEL = "gemini-2.5-flash"
ITEMS_PER_GROUP = 40
GROUP_MIN, GROUP_MAX = 5, 24
ASSIGN_CHUNK = 30
MAX_ITERATIONS = 6
CONCEPTS_TITLE_HE = "מושגים וסמליות"

_PROPOSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "groups": {
            "type": "ARRAY",
            "items": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}}, "required": ["title"]},
        }
    },
    "required": ["groups"],
}
_ASSIGN_SCHEMA = {
    "type": "OBJECT",
    "properties": {"assignments": {"type": "ARRAY", "items": {"type": "INTEGER"}}},
    "required": ["assignments"],
}


def log(message: str, *, quiet: bool) -> None:
    if not quiet:
        print(message, flush=True)


# --- AI classification (injectable: tests monkeypatch `classify_items`) --------


def _gemini_json(system: str, user: str, schema: dict[str, Any], *, model: str, api_key: str | None) -> dict[str, Any]:
    result = generate_json_content(
        system_prompt=system,
        user_prompt=user,
        model=model,
        temperature=0.2,
        max_output_tokens=8000,
        api_key=api_key,
        thinking_budget=0,
        response_mime_type="application/json",
        response_schema=schema,
    )
    return result.get("payload") or {}


def classify_items(
    title: str, items: list[str], *, model: str, api_key: str | None
) -> tuple[list[dict[str, Any]], list[int]]:
    """Return (groups, assignments) clustering `items` into coherent sub-topics.

    Two passes: propose group titles from the full list, then assign each item
    to a group index in small chunks (reliable for long lists).
    """
    target = max(GROUP_MIN, min(GROUP_MAX, round(len(items) / ITEMS_PER_GROUP)))
    numbered = "\n".join(f"{i}: {t}" for i, t in enumerate(items))
    groups = (
        _gemini_json(
            "You design clean, mutually-distinct topic taxonomies. Output only JSON.",
            f"The entry '{title}' has {len(items)} short detail items over-merged from many "
            f"sub-sections. Propose about {target} (range {max(2, target - 3)}-{target + 4}) "
            "coherent, evenly-sized sub-topics covering them, with concise Hebrew titles. "
            "Return JSON {groups:[{title}]}.\n\nItems:\n" + numbered,
            _PROPOSE_SCHEMA,
            model=model,
            api_key=api_key,
        ).get("groups")
        or []
    )
    groups = [g for g in groups if isinstance(g, dict) and str(g.get("title") or "").strip()]
    if not groups:
        groups = [{"title": title}]

    glist = "\n".join(f"{i}: {g['title']}" for i, g in enumerate(groups))
    assignments: list[int] = []
    for start in range(0, len(items), ASSIGN_CHUNK):
        chunk = items[start : start + ASSIGN_CHUNK]
        numbered_chunk = "\n".join(f"{i}: {t}" for i, t in enumerate(chunk))
        payload = _gemini_json(
            "You classify items into the given groups. Output only JSON.",
            f"Assign each item to the single best-fitting sub-topic by index. Return JSON "
            f"{{assignments:[int,...]}} of EXACTLY {len(chunk)} integers (0-based group index), "
            f"in item order.\n\nSub-topics:\n{glist}\n\nItems:\n{numbered_chunk}",
            _ASSIGN_SCHEMA,
            model=model,
            api_key=api_key,
        )
        chunk_assign = payload.get("assignments") or []
        if len(chunk_assign) != len(chunk):
            chunk_assign = (list(chunk_assign) + [0] * len(chunk))[: len(chunk)]
        assignments.extend(int(a) for a in chunk_assign)
    return groups, assignments


def _repair_assignments(assignments: list[int], group_count: int) -> list[int]:
    if assignments and min(assignments) >= 1 and max(assignments) == group_count:
        assignments = [a - 1 for a in assignments]  # tolerate 1-based replies
    return [min(max(a, 0), group_count - 1) for a in assignments]


# --- entry decomposition -------------------------------------------------------


def decompose_entry(
    entry: dict[str, Any],
    *,
    classify: Callable[..., tuple[list[dict[str, Any]], list[int]]],
    model: str,
    api_key: str | None,
) -> list[dict[str, Any]]:
    """Mutate `entry` into a hub and return the new child entry dicts (un-normalized)."""
    items = list(entry.get("practical_elements") or [])
    parent_slug = entry["slug"]
    degree = entry.get("degree")
    category = entry.get("category")
    status = entry.get("status") or "draft"
    applies = entry.get("applies_to_degrees") or [degree]

    groups, assignments = classify(entry.get("title") or parent_slug, items, model=model, api_key=api_key)
    assignments = _repair_assignments([int(a) for a in assignments], len(groups))
    if len(assignments) != len(items):
        assignments = (assignments + [0] * len(items))[: len(items)]

    children: list[dict[str, Any]] = []
    # Prose -> a Concepts child so the hub body is not a wall.
    if (entry.get("symbolic_meaning") or "").strip() or (entry.get("candidate_lesson") or "").strip():
        children.append(
            {
                "slug": f"{parent_slug}-concepts",
                "title": CONCEPTS_TITLE_HE,
                "type": "topic",
                "degree": degree,
                "applies_to_degrees": applies,
                "category": category,
                "parent_topic": parent_slug,
                "short_summary": "קריאה רעיונית: משמעות סמלית ולקח.",
                "symbolic_meaning": entry.get("symbolic_meaning") or "",
                "candidate_lesson": entry.get("candidate_lesson") or "",
                "status": status,
            }
        )
    for g, group in enumerate(groups):
        slice_items = [items[i] for i, a in enumerate(assignments) if a == g]
        if not slice_items:
            continue
        children.append(
            {
                "slug": f"{parent_slug}-part-{g + 1:02d}",
                "title": str(group.get("title") or f"{entry.get('title')} {g + 1}"),
                "type": "topic",
                "degree": degree,
                "applies_to_degrees": applies,
                "category": category,
                "parent_topic": parent_slug,
                "short_summary": str(group.get("title") or ""),
                "practical_elements": slice_items,
                "status": status,
            }
        )

    moved = sum(len(c.get("practical_elements") or []) for c in children)
    if moved != len(items):
        raise RuntimeError(f"item loss decomposing {parent_slug}: moved {moved} of {len(items)}")

    # Convert the parent into a hub; its detail now lives in the children.
    child_slugs = [c["slug"] for c in children]
    related = entry.get("related_topics")
    if not isinstance(related, dict):
        related = {"prior": [], "companion": [], "deeper": []}
    related["deeper"] = unique_strings(list(related.get("deeper") or []) + child_slugs)
    entry["type"] = "hub"
    entry["practical_elements"] = []
    entry["symbolic_meaning"] = ""
    entry["candidate_lesson"] = ""
    entry["related_topics"] = related
    return children


def decompose_degree(
    raw: dict[str, Any],
    degree_id: str,
    *,
    threshold: int,
    classify: Callable[..., tuple[list[dict[str, Any]], list[int]]],
    model: str,
    api_key: str | None,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Return (serialized degree data, stats). Iterates until none exceed threshold."""
    data = normalize_degree_data(raw, degree_id)
    hubs = 0
    children_total = 0
    for _ in range(MAX_ITERATIONS):
        over = [e for e in data["entries"] if len(e.get("practical_elements") or []) > threshold]
        if not over:
            break
        for entry in over:
            children = decompose_entry(entry, classify=classify, model=model, api_key=api_key)
            if not children:
                continue
            idx = data["entries"].index(entry)
            data["entries"][idx + 1 : idx + 1] = children
            hubs += 1
            children_total += len(children)
        # Re-normalize so new children get full schema defaults + fresh indexes.
        data = normalize_degree_data(serialize_degree_data(data), degree_id)
    return serialize_degree_data(data), {"hubs_created": hubs, "children_created": children_total}


# --- CLI -----------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Decompose over-merged entries into sub-topic hubs.")
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-key-env", default="GEMINI_API_KEY")
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    return parser


def run(
    *,
    site_root: Path,
    threshold: int = DEFAULT_THRESHOLD,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    classify: Callable[..., tuple[list[dict[str, Any]], list[int]]] | None = None,
    quiet: bool = False,
) -> dict[str, Any]:
    classify = classify or classify_items
    site_paths = build_site_data_paths(site_root)
    per_degree: dict[str, dict[str, int]] = {}
    for degree_id in DEGREE_IDS:
        path = site_paths[degree_id]
        if not path.exists():
            continue
        raw = read_json(path)
        serialized, stats = decompose_degree(
            raw, degree_id, threshold=threshold, classify=classify, model=model, api_key=api_key
        )
        per_degree[degree_id] = stats
        if stats["hubs_created"]:
            write_json(path, serialized)
            log(f"[{degree_id}] {stats['hubs_created']} hubs, +{stats['children_created']} children", quiet=quiet)
        else:
            log(f"[{degree_id}] nothing over threshold", quiet=quiet)
    manifest = {
        "tool": "prod.steps.decompose",
        "created_at": utc_timestamp(),
        "site_root": str(site_paths["site_root"]),
        "threshold": threshold,
        "status": "completed",
        "per_degree": per_degree,
    }
    return manifest


def main() -> None:
    args = build_parser().parse_args()
    api_key = os.getenv(args.api_key_env)
    if args.provider != "gemini" or not api_key:
        manifest = {
            "tool": "prod.steps.decompose",
            "created_at": utc_timestamp(),
            "status": "skipped",
            "reason": f"provider={args.provider!r}, api_key_env={args.api_key_env!r} not set"
            if not api_key
            else f"unsupported provider {args.provider!r}",
            "per_degree": {},
        }
        if args.report_dir is not None:
            write_json(ensure_dir(args.report_dir.resolve()) / "decompose_run_manifest.json", manifest)
        log(f"[decompose] skipped: {manifest['reason']}", quiet=args.quiet)
        return
    manifest = run(
        site_root=args.site_root.resolve(),
        threshold=args.threshold,
        model=args.model,
        api_key=api_key,
        quiet=args.quiet,
    )
    if args.report_dir is not None:
        report_dir = ensure_dir(args.report_dir.resolve())
        write_json(report_dir / "decompose_run_manifest.json", manifest)
    log(f"[done] decompose {manifest['per_degree']}", quiet=args.quiet)


if __name__ == "__main__":
    main()
