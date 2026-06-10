from __future__ import annotations

from dataclasses import dataclass
from typing import Any

NODE_TYPES = {
    "topic",
    "candidate_topic",
    "space",
    "office_role",
    "symbol",
    "ritual_stage",
    "concept",
    "source_term",
    "tradition_reference",
    "overlay",
    "deeper_link",
    "alias",
}

EDGE_TYPES = {
    "part_of",
    "associated_with",
    "symbolizes",
    "used_in",
    "precedes",
    "role_assigned_to",
    "alias_of",
    "deeper_than",
    "related_to",
    "appears_with",
    "supports_candidate",
    "split_from",
    "merge_candidate_with",
}


def normalize_token(value: str) -> str:
    lowered = (value or "").strip().lower()
    out = []
    for ch in lowered:
        if ch.isalnum():
            out.append(ch)
        else:
            out.append("-")
    normalized = "".join(out).strip("-")
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    return normalized or "unknown"


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    node_type: str
    label: str
    canonical_slug: str | None
    attributes: dict[str, Any]
    provenance: dict[str, Any]
    review: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "canonical_slug": self.canonical_slug,
            "attributes": self.attributes,
            "provenance": self.provenance,
            "review": self.review,
        }


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    edge_type: str
    source_node_id: str
    target_node_id: str
    weight: float
    evidence_count: int
    provenance: dict[str, Any]
    review: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "edge_type": self.edge_type,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "weight": self.weight,
            "evidence_count": self.evidence_count,
            "provenance": self.provenance,
            "review": self.review,
        }


def build_node(
    *,
    node_type: str,
    label: str,
    canonical_slug: str | None = None,
    attributes: dict[str, Any] | None = None,
    provenance_sources: list[dict[str, Any]] | None = None,
) -> GraphNode:
    if node_type not in NODE_TYPES:
        raise ValueError(f"Unsupported node_type: {node_type}")
    norm = normalize_token(canonical_slug or label)
    return GraphNode(
        node_id=f"node:{node_type}:{norm}",
        node_type=node_type,
        label=(label or "").strip() or norm,
        canonical_slug=(canonical_slug or None),
        attributes=attributes or {},
        provenance={"sources": provenance_sources or []},
        review={"status": "pending", "confidence": "medium", "notes": []},
    )


def build_edge(
    *,
    edge_type: str,
    source_node_id: str,
    target_node_id: str,
    weight: float = 0.5,
    evidence_count: int = 1,
    provenance_sources: list[dict[str, Any]] | None = None,
) -> GraphEdge:
    if edge_type not in EDGE_TYPES:
        raise ValueError(f"Unsupported edge_type: {edge_type}")
    edge_norm = normalize_token(f"{edge_type}-{source_node_id}-{target_node_id}")
    return GraphEdge(
        edge_id=f"edge:{edge_norm}",
        edge_type=edge_type,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        weight=max(0.0, min(float(weight), 1.0)),
        evidence_count=max(1, int(evidence_count)),
        provenance={"sources": provenance_sources or []},
        review={"status": "pending", "notes": []},
    )
