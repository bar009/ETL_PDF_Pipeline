from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from PDF_handle.prod.companion_contract import companion_candidate_degree, companion_candidate_title
from PDF_handle.prod.core.io import read_json, utc_timestamp
from PDF_handle.prod.exploration.graph_schema import build_edge, build_node, normalize_token


REQUIRED_STEP5_ARTIFACTS = (
    "companion_candidates.json",
    "level1.patch.json",
    "level2.patch.json",
    "work_manifest.generated.json",
)


def require_step5_artifacts(staging_dir: Path) -> dict[str, Path]:
    resolved = staging_dir.resolve()
    paths = {name: resolved / name for name in REQUIRED_STEP5_ARTIFACTS}
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing required Step 5 artifacts in {resolved}: {', '.join(missing)}"
        )
    paths["link_report.json"] = resolved / "link_report.json"
    paths["report.json"] = resolved / "report.json"
    return paths


def _topic_seed(candidate: dict[str, Any]) -> str:
    return (
        companion_candidate_title(candidate) if isinstance(candidate, dict) else ""
        or str(candidate.get("section_title") or "")
        or "unknown"
    ).strip()


def _cluster_id(seed: str) -> str:
    return f"cluster:candidate:{normalize_token(seed)}"


def _extract_targets_from_patch(patch_payload: dict[str, Any]) -> dict[str, set[str]]:
    by_marker: dict[str, set[str]] = defaultdict(set)
    for op in patch_payload.get("operations", []):
        marker = str(op.get("marker_id") or "").strip()
        slug = str(op.get("slug") or "").strip()
        if marker and slug:
            by_marker[marker].add(slug)
    return by_marker


def _tokens(text: str) -> set[str]:
    parts = re.split(r"[^0-9A-Za-z\u0590-\u05FF]+", (text or "").lower())
    return {part for part in parts if len(part) >= 3}


def _phrases(text: str) -> set[str]:
    token_list = [token for token in re.split(r"[^0-9A-Za-z\u0590-\u05FF]+", (text or "").lower()) if len(token) >= 3]
    phrases: set[str] = set(token_list)
    for i in range(len(token_list) - 1):
        phrases.add(f"{token_list[i]} {token_list[i + 1]}")
    for i in range(len(token_list) - 2):
        phrases.add(f"{token_list[i]} {token_list[i + 1]} {token_list[i + 2]}")
    return phrases


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    inter = len(left.intersection(right))
    union = len(left.union(right))
    return inter / union if union else 0.0


def _marker(work_id: str, section_id: str) -> str:
    return f"step5-source:{work_id}:{section_id}"


def _extract_local_ops(patch_payload: dict[str, Any]) -> dict[tuple[str, str], set[str]]:
    local: dict[tuple[str, str], set[str]] = defaultdict(set)
    for op in patch_payload.get("operations", []):
        work_id = str(op.get("work_id") or "").strip()
        section_id = str(op.get("section_id") or "").strip()
        slug = str(op.get("slug") or "").strip()
        if work_id and section_id and slug:
            local[(work_id, section_id)].add(slug)
    return local


def _semantic_node_type(term: str) -> str | None:
    t = (term or "").lower()
    if any(key in t for key in ("chamber", "lodge room", "temple", "altar", "middle chamber", "היכל", "לשכה", "מקדש")):
        return "space"
    if any(key in t for key in ("warden", "master", "deacon", "steward", "tyler", "officer", "פקיד", "אומן")):
        return "office_role"
    if any(key in t for key in ("apron", "gavel", "compass", "square", "trowel", "pillar", "column", "עין", "סמל")):
        return "symbol"
    if any(key in t for key in ("opening", "closing", "initiation", "raising", "degree", "stage", "שלב", "טקס")):
        return "ritual_stage"
    if any(key in t for key in ("rite", "tradition", "craft", "legacy", "מסורת", "נוסח")):
        return "tradition_reference"
    if any(key in t for key in ("chapter", "book", "source", "manuscript", "מקור", "כתב")):
        return "source_term"
    if len(t) >= 4:
        return "concept"
    return None


def _connected_components(neighbors: dict[int, set[int]], size: int) -> list[list[int]]:
    seen: set[int] = set()
    out: list[list[int]] = []
    for start in range(size):
        if start in seen:
            continue
        stack = [start]
        comp: list[int] = []
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            comp.append(node)
            for nxt in neighbors.get(node, set()):
                if nxt not in seen:
                    stack.append(nxt)
        out.append(sorted(comp))
    return out


def _candidate_record(candidate: dict[str, Any], section_order: dict[tuple[str, str], int]) -> dict[str, Any]:
    work_id = str(candidate.get("work_id") or "").strip()
    section_id = str(candidate.get("section_id") or "").strip()
    title = companion_candidate_title(candidate)
    seed = candidate.get("draft_seed") if isinstance(candidate.get("draft_seed"), dict) else {}
    payload = candidate.get("draft_entry_payload") if isinstance(candidate.get("draft_entry_payload"), dict) else {}
    keyword_source = seed if seed else payload
    keywords = keyword_source.get("keywords", []) if isinstance(keyword_source.get("keywords"), list) else []
    related = candidate.get("related_existing_slugs", []) if isinstance(candidate.get("related_existing_slugs"), list) else []
    token_bag = set()
    token_bag.update(_tokens(title))
    token_bag.update(_tokens(str(candidate.get("section_title") or "")))
    for kw in keywords[:20]:
        token_bag.update(_tokens(str(kw)))
    for slug in related[:20]:
        token_bag.update(_tokens(str(slug).replace("-", " ")))
    phrase_bag = set()
    phrase_bag.update(_phrases(title))
    phrase_bag.update(_phrases(str(candidate.get("section_title") or "")))
    for kw in keywords[:20]:
        phrase_bag.update(_phrases(str(kw)))
    source_provenance = str(candidate.get("source_provenance") or "")
    source_family = source_provenance.split("|", 1)[0].strip().lower() if source_provenance else ""
    return {
        "work_id": work_id,
        "section_id": section_id,
        "title": title,
        "suggested_degree": companion_candidate_degree(candidate),
        "suggested_category": candidate.get("suggested_category"),
        "related_existing_slugs": related[:20],
        "token_bag": sorted(token_bag),
        "phrase_bag": sorted(phrase_bag),
        "section_order": section_order.get((work_id, section_id), -1),
        "source_provenance": source_provenance,
        "source_family": source_family,
    }


def _load_link_rows(paths: dict[str, Path]) -> list[dict[str, Any]]:
    link_report = paths["link_report.json"]
    if link_report.exists():
        return read_json(link_report).get("rows", [])
    report = paths["report.json"]
    if report.exists():
        payload = read_json(report)
        candidates = payload.get("candidates", []) if isinstance(payload, dict) else []
        rows: list[dict[str, Any]] = []
        for candidate in candidates:
            rows.append(
                {
                    "work_id": "notebooklm-retroactive-backfill",
                    "section_id": str(candidate.get("seed_id") or "").strip(),
                    "knowledge_links": [
                        {"degree": "level1", "slug": slug}
                        for slug in (candidate.get("related_existing_slugs", []) if isinstance(candidate.get("related_existing_slugs"), list) else [])
                    ],
                }
            )
        return rows
    return []


def build_clusters(staging_dir: Path, *, max_nodes: int = 25, max_edges: int = 60) -> list[dict[str, Any]]:
    artifacts = require_step5_artifacts(staging_dir)
    companions = read_json(artifacts["companion_candidates.json"])
    link_rows = _load_link_rows(artifacts)
    work_manifest = read_json(artifacts["work_manifest.generated.json"]).get("works", [])
    l1_payload = read_json(artifacts["level1.patch.json"])
    l2_payload = read_json(artifacts["level2.patch.json"])
    l1_targets = _extract_targets_from_patch(l1_payload)
    l2_targets = _extract_targets_from_patch(l2_payload)
    l1_local_ops = _extract_local_ops(l1_payload)
    l2_local_ops = _extract_local_ops(l2_payload)

    section_order: dict[tuple[str, str], int] = {}
    for work in work_manifest:
        work_id = str(work.get("work_id") or "").strip()
        sections = work.get("sections", []) if isinstance(work.get("sections"), list) else []
        for idx, section in enumerate(sections):
            sid = str(section.get("section_id") or "").strip()
            if work_id and sid:
                section_order[(work_id, sid)] = idx

    candidate_records = [_candidate_record(item, section_order) for item in companions]
    neighbors: dict[int, set[int]] = defaultdict(set)
    for i, left in enumerate(candidate_records):
        left_tokens = set(left["token_bag"])
        left_phrases = set(left["phrase_bag"])
        left_related = set(left["related_existing_slugs"])
        for j in range(i + 1, len(candidate_records)):
            right = candidate_records[j]
            right_tokens = set(right["token_bag"])
            right_phrases = set(right["phrase_bag"])
            right_related = set(right["related_existing_slugs"])
            lexical = _jaccard(left_tokens, right_tokens)
            phrase_sim = _jaccard(left_phrases, right_phrases)
            shared_related = len(left_related.intersection(right_related))
            same_work_nearby = (
                left["work_id"]
                and left["work_id"] == right["work_id"]
                and left["section_order"] >= 0
                and right["section_order"] >= 0
                and abs(left["section_order"] - right["section_order"]) <= 2
            )
            if lexical >= 0.30 or phrase_sim >= 0.28 or shared_related >= 1 or same_work_nearby:
                neighbors[i].add(j)
                neighbors[j].add(i)

    grouped_indices = _connected_components(neighbors, len(candidate_records))
    grouped: dict[str, list[dict[str, Any]]] = {}
    for indices in grouped_indices:
        if not indices:
            continue
        group = [companions[idx] for idx in indices]
        seed = _topic_seed(group[0])
        grouped[f"{_cluster_id(seed)}-{normalize_token(str(indices[0]))}"] = group

    clusters: list[dict[str, Any]] = []
    for cid, group in grouped.items():
        seed = _topic_seed(group[0])
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        node_seen: set[str] = set()
        edge_seen: set[str] = set()
        local_anchor_counts: dict[str, int] = defaultdict(int)
        local_work_sections: set[tuple[str, str]] = set()
        local_candidates: list[dict[str, Any]] = []
        local_aliases: list[dict[str, Any]] = []
        local_overlays: list[dict[str, Any]] = []
        local_deeper_links: list[dict[str, Any]] = []
        local_split_signals: list[dict[str, Any]] = []
        local_merge_signals: list[dict[str, Any]] = []

        candidate_node_ids: list[dict[str, Any]] = []

        for candidate in group:
            work_id = str(candidate.get("work_id") or "").strip()
            section_id = str(candidate.get("section_id") or "").strip()
            local_work_sections.add((work_id, section_id))
            candidate_title = companion_candidate_title(candidate) or seed
            candidate_tokens = _tokens(candidate_title)
            candidate_phrases = _phrases(candidate_title)
            cand_node = build_node(
                node_type="candidate_topic",
                label=candidate_title,
                canonical_slug=None,
                attributes={
                    "suggested_degree": companion_candidate_degree(candidate),
                    "suggested_category": candidate.get("suggested_category"),
                    "related_existing_slugs": candidate.get("related_existing_slugs", []),
                },
                provenance_sources=[
                    {
                        "source_kind": "step5_companion_candidate",
                        "work_id": candidate.get("work_id"),
                        "section_id": candidate.get("section_id"),
                    }
                ],
            )
            if cand_node.node_id not in node_seen and len(nodes) < max_nodes:
                nodes.append(cand_node.as_dict())
                node_seen.add(cand_node.node_id)
            candidate_node_ids.append(
                {
                    "node_id": cand_node.node_id,
                    "title": candidate_title,
                    "tokens": candidate_tokens,
                    "phrases": candidate_phrases,
                    "work_id": work_id,
                    "section_id": section_id,
                    "anchors": set(),
                    "semantic_types": set(),
                    "suggested_degree": companion_candidate_degree(candidate),
                }
            )

            local_anchors: set[str] = set()
            local_anchors.update(str(slug).strip() for slug in candidate.get("related_existing_slugs", []) if str(slug).strip())
            for target in l1_local_ops.get((work_id, section_id), set()):
                local_anchors.add(target)
            for target in l2_local_ops.get((work_id, section_id), set()):
                local_anchors.add(target)
            row_marker = _marker(work_id, section_id)
            for op_slug in l1_targets.get(row_marker, set()):
                local_anchors.add(op_slug)
            for op_slug in l2_targets.get(row_marker, set()):
                local_anchors.add(op_slug)
            for row in link_rows:
                if str(row.get("work_id") or "").strip() == work_id and str(row.get("section_id") or "").strip() == section_id:
                    for link in row.get("knowledge_links", []):
                        if isinstance(link, dict):
                            slug = str(link.get("slug") or "").strip()
                            if slug:
                                local_anchors.add(slug)

            local_candidates.append(
                {
                    "candidate_node_id": cand_node.node_id,
                    "title": candidate_title,
                    "work_id": work_id,
                    "section_id": section_id,
                    "anchors": sorted(local_anchors),
                    "token_bag": sorted(candidate_tokens),
                    "phrase_bag": sorted(candidate_phrases),
                    "source_family": str(candidate.get("source_provenance") or "").split("|", 1)[0].strip().lower(),
                }
            )
            candidate_node_ids[-1]["anchors"] = set(local_anchors)

            for existing_slug in sorted(local_anchors)[:10]:
                local_anchor_counts[existing_slug] += 1
                topic_node = build_node(
                    node_type="topic",
                    label=existing_slug,
                    canonical_slug=existing_slug,
                    attributes={},
                    provenance_sources=[{"source_kind": "step5_related_existing_slug"}],
                )
                if topic_node.node_id not in node_seen and len(nodes) < max_nodes:
                    nodes.append(topic_node.as_dict())
                    node_seen.add(topic_node.node_id)
                edge = build_edge(
                    edge_type="supports_candidate",
                    source_node_id=topic_node.node_id,
                    target_node_id=cand_node.node_id,
                    weight=0.65,
                    evidence_count=1,
                    provenance_sources=[
                        {
                            "source_kind": "cluster_local_anchor",
                            "work_id": work_id,
                            "section_id": section_id,
                        }
                    ],
                ).as_dict()
                if edge["edge_id"] not in edge_seen and len(edges) < max_edges:
                    edges.append(edge)
                    edge_seen.add(edge["edge_id"])

            semantic_terms: set[str] = set()
            semantic_terms.update(_tokens(candidate_title))
            semantic_terms.update(_phrases(candidate_title))
            for kw in payload.get("keywords", [])[:20] if isinstance(payload.get("keywords"), list) else []:
                semantic_terms.update(_tokens(str(kw)))
                semantic_terms.update(_phrases(str(kw)))
            for term in sorted(semantic_terms):
                node_type = _semantic_node_type(term)
                if node_type is None:
                    continue
                semantic_node = build_node(
                    node_type=node_type,
                    label=term,
                    canonical_slug=None,
                    attributes={"from_candidate": cand_node.node_id},
                    provenance_sources=[
                        {
                            "source_kind": "step5_semantic_term",
                            "work_id": work_id,
                            "section_id": section_id,
                        }
                    ],
                )
                if semantic_node.node_id not in node_seen and len(nodes) < max_nodes:
                    nodes.append(semantic_node.as_dict())
                    node_seen.add(semantic_node.node_id)
                candidate_node_ids[-1]["semantic_types"].add(node_type)
                edge_type = "associated_with"
                if node_type == "symbol":
                    edge_type = "symbolizes"
                elif node_type in {"space", "ritual_stage"}:
                    edge_type = "used_in"
                elif node_type == "office_role":
                    edge_type = "role_assigned_to"
                semantic_edge = build_edge(
                    edge_type=edge_type,
                    source_node_id=semantic_node.node_id,
                    target_node_id=cand_node.node_id,
                    weight=0.55,
                    evidence_count=1,
                    provenance_sources=[{"source_kind": "semantic_term_link"}],
                ).as_dict()
                if semantic_edge["edge_id"] not in edge_seen and len(edges) < max_edges:
                    edges.append(semantic_edge)
                    edge_seen.add(semantic_edge["edge_id"])
                if node_type in {"space", "office_role", "ritual_stage", "tradition_reference", "source_term"}:
                    local_overlays.append(
                        {
                            "overlay_type": node_type,
                            "label": term,
                            "candidate_node_id": cand_node.node_id,
                            "provenance": {"work_id": work_id, "section_id": section_id},
                        }
                    )
                if node_type in {"concept", "symbol", "tradition_reference"} and any(
                    key in term for key in ("inner", "higher", "deeper", "sod", "עומק", "פנימי")
                ):
                    local_deeper_links.append(
                        {
                            "source_label": candidate_title,
                            "target_label": term,
                            "kind": node_type,
                            "provenance": {"work_id": work_id, "section_id": section_id},
                        }
                    )

        for i, left in enumerate(candidate_node_ids):
            for j in range(i + 1, len(candidate_node_ids)):
                right = candidate_node_ids[j]
                lexical_sim = _jaccard(set(left["tokens"]), set(right["tokens"]))
                phrase_sim = _jaccard(set(left["phrases"]), set(right["phrases"]))
                anchor_overlap = _jaccard(set(left["anchors"]), set(right["anchors"]))
                semantic_type_overlap = len(set(left["semantic_types"]).intersection(set(right["semantic_types"])))
                sim = max(lexical_sim, phrase_sim)
                if sim >= 0.72:
                    local_aliases.append(
                        {
                            "alias_label": right["title"],
                            "canonical_label": left["title"],
                            "similarity": round(sim, 3),
                            "provenance": {"left": left["candidate_node_id"], "right": right["candidate_node_id"]},
                        }
                    )
                    alias_edge = build_edge(
                        edge_type="alias_of",
                        source_node_id=right["candidate_node_id"],
                        target_node_id=left["candidate_node_id"],
                        weight=sim,
                        evidence_count=1,
                        provenance_sources=[{"source_kind": "lexical_similarity"}],
                    ).as_dict()
                    if alias_edge["edge_id"] not in edge_seen and len(edges) < max_edges:
                        edges.append(alias_edge)
                        edge_seen.add(alias_edge["edge_id"])
                if sim >= 0.84 and (anchor_overlap >= 0.35 or semantic_type_overlap >= 2):
                    local_merge_signals.append(
                        {
                            "left_label": left["title"],
                            "right_label": right["title"],
                            "reason": "high_similarity_with_anchor_or_semantic_overlap",
                            "score": round(sim, 3),
                            "anchor_overlap": round(anchor_overlap, 3),
                            "semantic_type_overlap": semantic_type_overlap,
                        }
                    )
                if (
                    left["work_id"] == right["work_id"]
                    and sim <= 0.22
                    and anchor_overlap <= 0.15
                    and left["suggested_degree"] != right["suggested_degree"]
                ):
                    local_split_signals.append(
                        {
                            "left_label": left["title"],
                            "right_label": right["title"],
                            "reason": "same_work_boundary_divergence",
                            "score": round(sim, 3),
                            "anchor_overlap": round(anchor_overlap, 3),
                            "left_degree": left["suggested_degree"],
                            "right_degree": right["suggested_degree"],
                        }
                    )

        candidate_canonical = [
            slug
            for slug, _count in sorted(local_anchor_counts.items(), key=lambda item: (-item[1], item[0]))[:10]
        ]
        for deeper in local_deeper_links[:8]:
            source_label = deeper["source_label"]
            target_label = deeper["target_label"]
            source_node = build_node(node_type="candidate_topic", label=source_label)
            target_node = build_node(node_type="deeper_link", label=target_label)
            if target_node.node_id not in node_seen and len(nodes) < max_nodes:
                nodes.append(target_node.as_dict())
                node_seen.add(target_node.node_id)
            deeper_edge = build_edge(
                edge_type="deeper_than",
                source_node_id=source_node.node_id,
                target_node_id=target_node.node_id,
                weight=0.5,
                evidence_count=1,
                provenance_sources=[{"source_kind": "deeper_link_signal"}],
            ).as_dict()
            if deeper_edge["edge_id"] not in edge_seen and len(edges) < max_edges:
                edges.append(deeper_edge)
                edge_seen.add(deeper_edge["edge_id"])

        clusters.append(
            {
                "cluster_id": cid,
                "seed_topic": seed,
                "created_at": utc_timestamp(),
                "source_inputs": list(REQUIRED_STEP5_ARTIFACTS),
                "nodes": nodes[:max_nodes],
                "edges": edges[:max_edges],
                "candidate_canonical_topics": candidate_canonical,
                "candidate_aliases": local_aliases[:20],
                "candidate_overlays": local_overlays[:20],
                "candidate_deeper_links": local_deeper_links[:20],
                "split_suggestions": local_split_signals[:20],
                "merge_suggestions": local_merge_signals[:20],
                "review_notes": [],
                "cluster_evidence": {
                    "candidate_count": len(local_candidates),
                    "work_section_count": len(local_work_sections),
                    "anchor_count": len(local_anchor_counts),
                    "semantic_node_count": len([node for node in nodes if node.get("node_type") not in {"candidate_topic", "topic"}]),
                },
                "candidate_records": local_candidates,
                "provenance": {
                    "staging_dir": str(staging_dir.resolve()),
                    "generator": "PDF_handle.prod.cli.exploration_review",
                },
            }
        )

    return sorted(clusters, key=lambda item: item["cluster_id"])
