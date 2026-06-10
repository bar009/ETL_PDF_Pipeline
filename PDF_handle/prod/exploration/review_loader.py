from __future__ import annotations

from pathlib import Path
from typing import Any

from PDF_handle.prod.core.io import read_json
from PDF_handle.prod.exploration.graph_schema import EDGE_TYPES, NODE_TYPES


def _normalize_node(node: dict[str, Any]) -> dict[str, Any]:
    ntype = str(node.get("node_type") or "").strip()
    if ntype not in NODE_TYPES:
        raise ValueError(f"Unsupported external node_type: {ntype}")
    return {
        "node_id": str(node.get("node_id") or "").strip(),
        "node_type": ntype,
        "label": str(node.get("label") or "").strip(),
        "canonical_slug": node.get("canonical_slug"),
        "attributes": node.get("attributes", {}) if isinstance(node.get("attributes"), dict) else {},
        "provenance": node.get("provenance", {}) if isinstance(node.get("provenance"), dict) else {},
        "review": node.get("review", {}) if isinstance(node.get("review"), dict) else {},
    }


def _normalize_edge(edge: dict[str, Any]) -> dict[str, Any]:
    etype = str(edge.get("edge_type") or "").strip()
    if etype not in EDGE_TYPES:
        raise ValueError(f"Unsupported external edge_type: {etype}")
    return {
        "edge_id": str(edge.get("edge_id") or "").strip(),
        "edge_type": etype,
        "source_node_id": str(edge.get("source_node_id") or "").strip(),
        "target_node_id": str(edge.get("target_node_id") or "").strip(),
        "weight": float(edge.get("weight", 0.5)),
        "evidence_count": int(edge.get("evidence_count", 1)),
        "provenance": edge.get("provenance", {}) if isinstance(edge.get("provenance"), dict) else {},
        "review": edge.get("review", {}) if isinstance(edge.get("review"), dict) else {},
    }


def normalize_external_reviews(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path.resolve())
    items = payload if isinstance(payload, list) else [payload]
    normalized: list[dict[str, Any]] = []

    for item in items:
        if not isinstance(item, dict):
            raise ValueError("External review payload must contain JSON objects.")
        nodes = item.get("nodes", [])
        edges = item.get("edges", [])
        suggestions = item.get("suggestions", {})
        confidence = item.get("confidence")
        conflicts = item.get("conflicts", [])
        notes = item.get("notes", [])
        node_candidates = item.get("node_candidates", [])
        edge_candidates = item.get("edge_candidates", [])
        alias_hints = item.get("alias_hints", [])
        split_hints = item.get("split_hints", [])
        merge_hints = item.get("merge_hints", [])
        overlay_hints = item.get("overlay_hints", [])
        deeper_link_hints = item.get("deeper_link_hints", [])
        normalized.append(
            {
                "source_name": str(item.get("source_name") or "external_review").strip(),
                "review_id": str(item.get("review_id") or "").strip(),
                "cluster_hint": str(item.get("cluster_hint") or "").strip() or None,
                "nodes": [_normalize_node(node) for node in nodes if isinstance(node, dict)],
                "edges": [_normalize_edge(edge) for edge in edges if isinstance(edge, dict)],
                "node_candidates": [_normalize_node(node) for node in node_candidates if isinstance(node, dict)],
                "edge_candidates": [_normalize_edge(edge) for edge in edge_candidates if isinstance(edge, dict)],
                "alias_hints": alias_hints if isinstance(alias_hints, list) else [],
                "split_hints": split_hints if isinstance(split_hints, list) else [],
                "merge_hints": merge_hints if isinstance(merge_hints, list) else [],
                "overlay_hints": overlay_hints if isinstance(overlay_hints, list) else [],
                "deeper_link_hints": deeper_link_hints if isinstance(deeper_link_hints, list) else [],
                "confidence": confidence if isinstance(confidence, (int, float, str)) else None,
                "conflicts": conflicts if isinstance(conflicts, list) else [],
                "notes": notes if isinstance(notes, list) else [],
                "suggestions": {
                    "candidate_topics": suggestions.get("candidate_topics", []) if isinstance(suggestions, dict) else [],
                    "aliases": suggestions.get("aliases", []) if isinstance(suggestions, dict) else [],
                    "overlays": suggestions.get("overlays", []) if isinstance(suggestions, dict) else [],
                    "deeper_links": suggestions.get("deeper_links", []) if isinstance(suggestions, dict) else [],
                    "splits": suggestions.get("splits", []) if isinstance(suggestions, dict) else [],
                    "merges": suggestions.get("merges", []) if isinstance(suggestions, dict) else [],
                },
                "provenance": item.get("provenance", {}) if isinstance(item.get("provenance"), dict) else {},
            }
        )
    return normalized
