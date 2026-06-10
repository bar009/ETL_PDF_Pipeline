from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Any


FORBIDDEN_PATTERNS: dict[str, re.Pattern[str]] = {
    "Royal Arch": re.compile(r"Royal Arch", re.IGNORECASE),
    "Lost Word": re.compile(r"Lost Word", re.IGNORECASE),
    "hiram": re.compile(r"\u05d7\u05d9\u05e8\u05dd"),
    "third_degree": re.compile(r"\u05d3\u05e8\u05d2\u05d4 \u05e9\u05dc\u05d9\u05e9\u05d9\u05ea"),
    "completion": re.compile(r"completion", re.IGNORECASE),
    "secret": re.compile(r"secret", re.IGNORECASE),
    "standalone_sod": re.compile(r"(?<!\w)\u05e1\u05d5\u05d3(?!\w)"),
    "standalone_mila": re.compile(r"(?<!\w)\u05de\u05d9\u05dc\u05d4(?!\w)"),
}

ENTRY_TYPE_BLOCKLIST = {"category", "hub"}
CATEGORY_SIGNAL_WEIGHTS = {
    "preparation": 1.1,
    "ritual_flow": 1.15,
    "lodge_structure": 1.0,
    "degree_board": 1.1,
    "tools_and_signs": 1.0,
    "obligation_and_law": 0.95,
    "inner_work": 1.0,
    "gate": 0.75,
    "glossary_and_review": 0.55,
}
DISCOVERY_SOURCE_BASE = {
    "repeated_reference": 66,
    "co_occurrence": 62,
    "sequential_flow": 60,
    "shared_category": 56,
}
CATEGORY_TYPE_HINT = {
    "preparation": "process",
    "ritual_flow": "process",
    "inner_work": "process",
    "lodge_structure": "structure",
    "degree_board": "system",
    "tools_and_signs": "relationship",
    "obligation_and_law": "relationship",
    "gate": "structure",
    "glossary_and_review": "relationship",
}
GENERIC_SLUG_TOKENS = {
    "l1",
    "level",
    "degree",
    "harishona",
    "badraga",
    "category",
    "landing",
    "what",
    "is",
    "mahi",
    "mahu",
    "and",
    "bein",
    "shel",
    "bemerkhav",
    "halishka",
    "ritual",
    "tools",
    "tool",
    "inner",
    "work",
    "gate",
    "glossary",
    "review",
    "degree",
    "board",
    "lodge",
    "flow",
    "obligation",
    "preparation",
}
PROCESS_CATEGORIES = {"preparation", "ritual_flow", "inner_work"}


@dataclass(frozen=True)
class Candidate:
    candidate_topic: str
    candidate_title_hint: str
    based_on_entries: tuple[str, ...]
    suggested_type: str
    confidence: str
    reason: str
    discovery_sources: tuple[str, ...]
    score: int
    basis_categories: tuple[str, ...]
    overlap_with_existing_level2: dict[str, Any]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def entry_text(entry: dict[str, Any]) -> str:
    keywords = " ".join(entry.get("keywords", []))
    aliases = " ".join(entry.get("aliases", []))
    related = " ".join(
        slug
        for bucket in ("prior", "companion", "deeper")
        for slug in entry.get("related_topics", {}).get(bucket, [])
    )
    parts = [
        entry.get("title", ""),
        entry.get("short_summary", ""),
        entry.get("full_summary", ""),
        entry.get("symbolic_meaning", ""),
        entry.get("candidate_lesson", ""),
        keywords,
        aliases,
        related,
    ]
    return "\n".join(part for part in parts if part)


def has_boundary_risk(entry: dict[str, Any]) -> bool:
    text = entry_text(entry)
    return any(pattern.search(text) for pattern in FORBIDDEN_PATTERNS.values())


def is_discovery_eligible(entry: dict[str, Any]) -> bool:
    if entry.get("degree") != "level1":
        return False
    if entry.get("type") in ENTRY_TYPE_BLOCKLIST:
        return False
    if has_boundary_risk(entry):
        return False
    return True


def slug_tokens(slug: str) -> list[str]:
    tokens = [token for token in slug.split("-") if token]
    return [token for token in tokens if token not in GENERIC_SLUG_TOKENS and len(token) > 2]


def choose_label_tokens(slugs: list[str]) -> list[str]:
    counts: Counter[str] = Counter()
    for slug in slugs:
        counts.update(slug_tokens(slug))
    ranked = [token for token, _count in counts.most_common() if token not in {"entry", "topic"}]
    return ranked[:5]


def build_candidate_topic(slugs: list[str], suggested_type: str, family: str) -> str:
    tokens = choose_label_tokens(slugs)
    if not tokens:
        tokens = [family, suggested_type]
    joined = "-".join(tokens[:4])
    return f"level2-candidate-{joined}-{suggested_type}"


def build_title_hint(entry_map: dict[str, dict[str, Any]], slugs: list[str], suggested_type: str) -> str:
    titles = [entry_map[slug]["title"] for slug in slugs[:3]]
    if suggested_type == "process":
        prefix = "Process cluster"
    elif suggested_type == "structure":
        prefix = "Structure cluster"
    elif suggested_type == "system":
        prefix = "System cluster"
    else:
        prefix = "Relationship cluster"
    return f"{prefix}: {' / '.join(titles)}"


def infer_type(categories: set[str], discovery_sources: set[str]) -> str:
    if categories & PROCESS_CATEGORIES:
        return "process"
    if "lodge_structure" in categories:
        return "structure"
    if "degree_board" in categories:
        return "system"
    if "tools_and_signs" in categories and "obligation_and_law" in categories:
        return "relationship"
    if "repeated_reference" in discovery_sources and len(categories) >= 2:
        return "system"
    if len(categories) == 1:
        return CATEGORY_TYPE_HINT.get(next(iter(categories)), "structure")
    if "co_occurrence" in discovery_sources and len(categories) >= 2:
        return "relationship"
    return "structure"


def compute_overlap(
    candidate_slugs: set[str], existing_level2_links: list[tuple[str, set[str]]]
) -> dict[str, Any]:
    best_slug = None
    best_jaccard = 0.0
    best_coverage = 0.0
    for level2_slug, links in existing_level2_links:
        if not links:
            continue
        union = candidate_slugs | links
        jaccard = len(candidate_slugs & links) / len(union) if union else 0.0
        coverage = len(candidate_slugs & links) / len(candidate_slugs) if candidate_slugs else 0.0
        if (jaccard, coverage) > (best_jaccard, best_coverage):
            best_slug = level2_slug
            best_jaccard = jaccard
            best_coverage = coverage
    return {
        "closest_level2_slug": best_slug,
        "max_jaccard": round(best_jaccard, 3),
        "coverage_ratio": round(best_coverage, 3),
    }


def candidate_quality_score(
    family: str,
    slugs: list[str],
    categories: set[str],
    centrality: Counter[str],
    overlap: dict[str, Any],
) -> int:
    score = DISCOVERY_SOURCE_BASE[family]
    score += len(slugs) * 5
    score += min(12, int(sum(centrality[slug] for slug in slugs) / max(len(slugs), 1)))
    score += len(categories) * 4
    score += int(sum(CATEGORY_SIGNAL_WEIGHTS.get(category, 0.8) * 3 for category in categories))
    if overlap["coverage_ratio"] >= 0.8:
        score -= 35
    elif overlap["coverage_ratio"] >= 0.6:
        score -= 24
    elif overlap["coverage_ratio"] >= 0.4:
        score -= 12
    if categories == {"glossary_and_review"}:
        score -= 18
    if categories == {"gate"}:
        score -= 12
    return score


def confidence_from_score(score: int) -> str:
    return "high" if score >= 82 else "medium"


def build_reason(
    family: str,
    entry_map: dict[str, dict[str, Any]],
    slugs: list[str],
    categories: set[str],
    suggested_type: str,
) -> str:
    titles = [entry_map[slug]["title"] for slug in slugs[:3]]
    if family == "co_occurrence":
        opener = "Strong co-occurrence and mutual graph references"
    elif family == "shared_category":
        opener = "A dense shared-category cluster"
    elif family == "sequential_flow":
        opener = "A repeatable sequential flow across connected entries"
    else:
        opener = "A repeated reference center that organizes several entries"
    category_part = ", ".join(sorted(categories))
    title_part = " + ".join(titles)
    return (
        f"{opener} point to a Level 2 {suggested_type} topic built from {title_part}. "
        f"The cluster stays grounded in Level 1 while adding structure rather than recap. "
        f"Primary categories: {category_part}."
    )


def dedupe_key(slugs: list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(slugs)))


def build_graph(
    level1_entries: dict[str, dict[str, Any]]
) -> tuple[dict[str, Counter[str]], Counter[str], dict[str, list[tuple[str, str]]]]:
    adjacency: dict[str, Counter[str]] = defaultdict(Counter)
    inbound = Counter()
    references: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for slug, entry in level1_entries.items():
        for bucket, weight in (("prior", 2), ("companion", 3), ("deeper", 2)):
            for related_slug in entry.get("related_topics", {}).get(bucket, []):
                if related_slug not in level1_entries:
                    continue
                adjacency[slug][related_slug] += weight
                inbound[related_slug] += 1
                references[related_slug].append((slug, bucket))
    return adjacency, inbound, references


def centrality_scores(adjacency: dict[str, Counter[str]], inbound: Counter[str]) -> Counter[str]:
    scores = Counter()
    for slug, neighbors in adjacency.items():
        scores[slug] += sum(neighbors.values())
    for slug, count in inbound.items():
        scores[slug] += count * 3
    return scores


def shared_category_candidates(
    level1_entries: dict[str, dict[str, Any]],
    centrality: Counter[str],
) -> list[tuple[str, list[str]]]:
    by_category: dict[str, list[str]] = defaultdict(list)
    for slug, entry in level1_entries.items():
        by_category[entry["category"]].append(slug)

    raw: list[tuple[str, list[str]]] = []
    for category, slugs in by_category.items():
        if len(slugs) < 3:
            continue
        ranked = sorted(
            slugs,
            key=lambda slug: (
                centrality[slug],
                len(level1_entries[slug].get("related_topics", {}).get("companion", [])),
                len(level1_entries[slug].get("keywords", [])),
            ),
            reverse=True,
        )
        first = ranked[: min(4, len(ranked))]
        raw.append(("shared_category", first))
        if len(ranked) >= 6:
            second = ranked[2 : 2 + min(4, len(ranked) - 2)]
            if len(second) >= 3:
                raw.append(("shared_category", second))
    return raw


def repeated_reference_candidates(
    references: dict[str, list[tuple[str, str]]],
    centrality: Counter[str],
) -> list[tuple[str, list[str]]]:
    raw: list[tuple[str, list[str]]] = []
    for central_slug, inbound_records in sorted(
        references.items(),
        key=lambda item: (len(item[1]), centrality[item[0]]),
        reverse=True,
    ):
        referencers = [source for source, _bucket in inbound_records]
        unique_referencers = []
        for slug in referencers:
            if slug not in unique_referencers:
                unique_referencers.append(slug)
        if len(unique_referencers) < 2:
            continue
        cluster = [central_slug] + unique_referencers[:3]
        if len(cluster) >= 3:
            raw.append(("repeated_reference", cluster))
    return raw


def co_occurrence_candidates(
    adjacency: dict[str, Counter[str]],
    centrality: Counter[str],
) -> list[tuple[str, list[str]]]:
    pair_scores: list[tuple[int, str, str]] = []
    slugs = sorted(adjacency)
    for left, right in combinations(slugs, 2):
        direct = adjacency[left][right] + adjacency[right][left]
        if direct == 0:
            continue
        shared = set(adjacency[left]) & set(adjacency[right])
        score = direct * 3 + len(shared) * 2 + min(centrality[left], 8) + min(centrality[right], 8)
        pair_scores.append((score, left, right))

    raw: list[tuple[str, list[str]]] = []
    for _score, left, right in sorted(pair_scores, reverse=True)[:20]:
        shared_neighbors = sorted(
            set(adjacency[left]) & set(adjacency[right]),
            key=lambda slug: centrality[slug],
            reverse=True,
        )
        cluster = [left, right] + shared_neighbors[:2]
        deduped = []
        for slug in cluster:
            if slug not in deduped:
                deduped.append(slug)
        if len(deduped) >= 3:
            raw.append(("co_occurrence", deduped[:4]))
    return raw


def sequential_flow_candidates(
    level1_entries: dict[str, dict[str, Any]],
) -> list[tuple[str, list[str]]]:
    flow_edges: dict[str, list[str]] = defaultdict(list)
    for slug, entry in level1_entries.items():
        if entry["category"] not in PROCESS_CATEGORIES:
            continue
        for deeper_slug in entry.get("related_topics", {}).get("deeper", []):
            if deeper_slug not in level1_entries:
                continue
            if level1_entries[deeper_slug]["category"] in PROCESS_CATEGORIES:
                flow_edges[slug].append(deeper_slug)

    raw_paths: list[list[str]] = []
    for start in sorted(flow_edges):
        path = [start]
        current = start
        seen = {start}
        while flow_edges.get(current):
            next_slug = flow_edges[current][0]
            if next_slug in seen:
                break
            path.append(next_slug)
            seen.add(next_slug)
            current = next_slug
            if len(path) >= 4:
                break
        if len(path) >= 3:
            raw_paths.append(path)

    return [("sequential_flow", path) for path in raw_paths]


def build_candidates(
    level1_entries: dict[str, dict[str, Any]],
    existing_level2_links: list[tuple[str, set[str]]],
) -> tuple[list[Candidate], list[dict[str, Any]]]:
    adjacency, inbound, references = build_graph(level1_entries)
    centrality = centrality_scores(adjacency, inbound)

    raw = []
    raw.extend(shared_category_candidates(level1_entries, centrality))
    raw.extend(repeated_reference_candidates(references, centrality))
    raw.extend(co_occurrence_candidates(adjacency, centrality))
    raw.extend(sequential_flow_candidates(level1_entries))

    accepted: dict[tuple[str, ...], Candidate] = {}
    rejected: list[dict[str, Any]] = []

    for family, candidate_slugs in raw:
        unique_slugs = []
        for slug in candidate_slugs:
            if slug in level1_entries and slug not in unique_slugs:
                unique_slugs.append(slug)
        if len(unique_slugs) < 3:
            rejected.append(
                {
                    "family": family,
                    "based_on_entries": unique_slugs,
                    "reason": "Rejected because the cluster is too small; strong candidates need at least 3 linked entries.",
                }
            )
            continue

        candidate_set = set(unique_slugs)
        categories = {level1_entries[slug]["category"] for slug in unique_slugs}
        discovery_sources = {family}
        overlap = compute_overlap(candidate_set, existing_level2_links)
        if overlap["coverage_ratio"] >= 0.8:
            rejected.append(
                {
                    "family": family,
                    "based_on_entries": unique_slugs,
                    "reason": f"Rejected as near-duplicate of existing {overlap['closest_level2_slug']}.",
                }
            )
            continue

        if categories == {"gate"}:
            rejected.append(
                {
                    "family": family,
                    "based_on_entries": unique_slugs,
                    "reason": "Rejected because gate-only clusters read as Level 1 orientation recap rather than Level 2 structure.",
                }
            )
            continue

        suggested_type = infer_type(categories, discovery_sources)
        score = candidate_quality_score(family, unique_slugs, categories, centrality, overlap)
        if score < 60:
            rejected.append(
                {
                    "family": family,
                    "based_on_entries": unique_slugs,
                    "reason": "Rejected because the cluster was too weak or too abstract after scoring.",
                }
            )
            continue

        confidence = confidence_from_score(score)
        candidate = Candidate(
            candidate_topic=build_candidate_topic(unique_slugs, suggested_type, family),
            candidate_title_hint=build_title_hint(level1_entries, unique_slugs, suggested_type),
            based_on_entries=tuple(unique_slugs),
            suggested_type=suggested_type,
            confidence=confidence,
            reason=build_reason(family, level1_entries, unique_slugs, categories, suggested_type),
            discovery_sources=tuple(sorted(discovery_sources)),
            score=score,
            basis_categories=tuple(sorted(categories)),
            overlap_with_existing_level2=overlap,
        )

        key = dedupe_key(unique_slugs)
        existing = accepted.get(key)
        if existing is None or candidate.score > existing.score:
            accepted[key] = candidate

    ranked = sorted(
        accepted.values(),
        key=lambda item: (
            item.score,
            item.confidence == "high",
            -item.overlap_with_existing_level2["coverage_ratio"],
            len(item.based_on_entries),
        ),
        reverse=True,
    )

    selected: list[Candidate] = []
    selected_entry_sets: list[set[str]] = []
    family_counts: Counter[str] = Counter()
    for candidate in ranked:
        candidate_set = set(candidate.based_on_entries)
        if any(len(candidate_set & selected_set) / len(candidate_set | selected_set) > 0.65 for selected_set in selected_entry_sets):
            continue
        primary_family = candidate.discovery_sources[0]
        if family_counts[primary_family] >= 5:
            continue
        selected.append(candidate)
        selected_entry_sets.append(candidate_set)
        family_counts[primary_family] += 1
        if len(selected) >= 15:
            break

    return selected, rejected


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover controlled Level 2 topic candidates from the Level 1 graph.")
    parser.add_argument("--level1", required=True, help="Path to level1.json")
    parser.add_argument("--level2", required=True, help="Path to level2.json")
    parser.add_argument("--output", required=True, help="Path to level2_topic_candidates.json")
    parser.add_argument("--max-candidates", type=int, default=15, help="Maximum number of candidates to keep.")
    args = parser.parse_args()

    level1_payload = load_json(Path(args.level1))
    level2_payload = load_json(Path(args.level2))

    level1_entries = {
        entry["slug"]: entry
        for entry in level1_payload["entries"]
        if is_discovery_eligible(entry)
    }
    existing_level2_links = []
    for entry in level2_payload["entries"]:
        links = {
            link["slug"]
            for link in entry.get("knowledge_links", [])
            if link.get("degree") == "level1"
        }
        existing_level2_links.append((entry["slug"], links))

    candidates, rejected = build_candidates(level1_entries, existing_level2_links)
    candidates = candidates[: args.max_candidates]

    type_counts = Counter(candidate.suggested_type for candidate in candidates)
    confidence_counts = Counter(candidate.confidence for candidate in candidates)
    discovery_source_counts = Counter(candidate.discovery_sources[0] for candidate in candidates)

    output = {
        "generated_at": str(date.today()),
        "phase": "Phase M.3",
        "goal": "Discover Level 2 topic candidates from the existing Level 1 graph without inventing unsupported coverage.",
        "inputs": {
            "level1_path": str(Path(args.level1).resolve()).replace("\\", "/"),
            "level2_path": str(Path(args.level2).resolve()).replace("\\", "/"),
        },
        "summary": {
            "eligible_level1_entries": len(level1_entries),
            "existing_level2_entries": len(level2_payload["entries"]),
            "candidate_count": len(candidates),
            "type_counts": dict(sorted(type_counts.items())),
            "confidence_counts": dict(sorted(confidence_counts.items())),
            "discovery_source_counts": dict(sorted(discovery_source_counts.items())),
            "recommended_selection": [candidate.candidate_topic for candidate in candidates[:8]],
            "overall_status": "pass" if len(candidates) >= 10 else "pass-with-warnings",
        },
        "candidates": [
            {
                "rank": index,
                "candidate_topic": candidate.candidate_topic,
                "candidate_title_hint": candidate.candidate_title_hint,
                "based_on_entries": list(candidate.based_on_entries),
                "suggested_type": candidate.suggested_type,
                "confidence": candidate.confidence,
                "reason": candidate.reason,
                "score": candidate.score,
                "discovery_sources": list(candidate.discovery_sources),
                "basis_categories": list(candidate.basis_categories),
                "target_partition_role": "core_degree_content",
                "target_degree": "level2",
                "overlap_with_existing_level2": candidate.overlap_with_existing_level2,
            }
            for index, candidate in enumerate(candidates, start=1)
        ],
        "rejected_candidates": rejected[:20],
    }
    write_json(Path(args.output), output)


if __name__ == "__main__":
    main()

