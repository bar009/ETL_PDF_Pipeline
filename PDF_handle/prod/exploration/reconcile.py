from __future__ import annotations

import re
from typing import Any


def _tokens(text: str) -> set[str]:
    parts = re.split(r"[^0-9A-Za-z\u0590-\u05FF]+", (text or "").lower())
    return {part for part in parts if len(part) >= 3}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / len(left.union(right))


def _extract_hint_labels(hints: list[Any]) -> set[str]:
    labels: set[str] = set()
    for item in hints:
        if isinstance(item, str) and item.strip():
            labels.add(item.strip().lower())
        elif isinstance(item, dict):
            for key in ("label", "candidate_label", "left_label", "right_label", "alias_label", "canonical_label"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    labels.add(value.strip().lower())
    return labels


def _confidence_score(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(float(value), 1.0))
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"high", "strong"}:
            return 0.9
        if lowered in {"medium", "moderate"}:
            return 0.6
        if lowered in {"low", "weak"}:
            return 0.3
        try:
            return max(0.0, min(float(lowered), 1.0))
        except ValueError:
            return 0.5
    return 0.5


def _external_by_cluster(external_reviews: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for review in external_reviews:
        cid = str(review.get("cluster_hint") or "").strip()
        if not cid:
            continue
        rec = out.setdefault(
            cid,
            {
                "review_count": 0,
                "source_names": set(),
                "alias_labels": set(),
                "split_labels": set(),
                "merge_labels": set(),
                "overlay_labels": set(),
                "deeper_labels": set(),
                "notes": [],
                "conflicts": [],
                "node_candidate_count": 0,
                "edge_candidate_count": 0,
                "node_candidates": [],
                "edge_candidates": [],
                "candidate_topics": [],
                "suggested_aliases": [],
                "suggested_overlays": [],
                "suggested_deeper": [],
                "confidence_scores": [],
            },
        )
        rec["review_count"] += 1
        rec["source_names"].add(str(review.get("source_name") or "external_review"))
        rec["alias_labels"].update(_extract_hint_labels(review.get("alias_hints", [])))
        rec["split_labels"].update(_extract_hint_labels(review.get("split_hints", [])))
        rec["merge_labels"].update(_extract_hint_labels(review.get("merge_hints", [])))
        rec["overlay_labels"].update(_extract_hint_labels(review.get("overlay_hints", [])))
        rec["deeper_labels"].update(_extract_hint_labels(review.get("deeper_link_hints", [])))
        rec["notes"].extend(review.get("notes", []) if isinstance(review.get("notes"), list) else [])
        rec["conflicts"].extend(review.get("conflicts", []) if isinstance(review.get("conflicts"), list) else [])
        rec["node_candidate_count"] += len(review.get("node_candidates", []))
        rec["edge_candidate_count"] += len(review.get("edge_candidates", []))
        rec["node_candidates"].extend(review.get("node_candidates", []))
        rec["edge_candidates"].extend(review.get("edge_candidates", []))
        suggestions = review.get("suggestions", {}) if isinstance(review.get("suggestions"), dict) else {}
        rec["candidate_topics"].extend(suggestions.get("candidate_topics", []) if isinstance(suggestions.get("candidate_topics"), list) else [])
        rec["suggested_aliases"].extend(suggestions.get("aliases", []) if isinstance(suggestions.get("aliases"), list) else [])
        rec["suggested_overlays"].extend(suggestions.get("overlays", []) if isinstance(suggestions.get("overlays"), list) else [])
        rec["suggested_deeper"].extend(suggestions.get("deeper_links", []) if isinstance(suggestions.get("deeper_links"), list) else [])
        rec["confidence_scores"].append(_confidence_score(review.get("confidence")))
    return out


def reconcile_clusters(clusters: list[dict[str, Any]], external_reviews: list[dict[str, Any]]) -> dict[str, Any]:
    by_cluster = _external_by_cluster(external_reviews)
    cluster_reports: list[dict[str, Any]] = []
    aggregate_counts = {
        "promote_canonical_topic_candidate": 0,
        "alias_only": 0,
        "overlay_dimension": 0,
        "deeper_research_link": 0,
        "recommend_split": 0,
        "recommend_merge": 0,
        "no_action_insufficient_evidence": 0,
    }

    for cluster in clusters:
        cid = cluster["cluster_id"]
        ext = by_cluster.get(cid, {})
        alias_labels = {str(item.get("alias_label") or "").lower() for item in cluster.get("candidate_aliases", []) if isinstance(item, dict)}
        alias_labels.update(ext.get("alias_labels", set()))
        split_labels = ext.get("split_labels", set()).copy()
        merge_labels = ext.get("merge_labels", set()).copy()
        for item in cluster.get("split_suggestions", []):
            if isinstance(item, dict):
                split_labels.add(str(item.get("left_label") or "").lower())
                split_labels.add(str(item.get("right_label") or "").lower())
        for item in cluster.get("merge_suggestions", []):
            if isinstance(item, dict):
                merge_labels.add(str(item.get("left_label") or "").lower())
                merge_labels.add(str(item.get("right_label") or "").lower())
        overlay_labels = {str(item.get("label") or "").lower() for item in cluster.get("candidate_overlays", []) if isinstance(item, dict)}
        overlay_labels.update(ext.get("overlay_labels", set()))
        overlay_labels.update(_extract_hint_labels(ext.get("suggested_overlays", [])))
        deeper_labels = {str(item.get("target_label") or "").lower() for item in cluster.get("candidate_deeper_links", []) if isinstance(item, dict)}
        deeper_labels.update(ext.get("deeper_labels", set()))
        deeper_labels.update(_extract_hint_labels(ext.get("suggested_deeper", [])))

        candidate_records = cluster.get("candidate_records", [])
        candidate_record_by_node = {
            item.get("candidate_node_id"): item
            for item in candidate_records
            if isinstance(item, dict) and item.get("candidate_node_id")
        }
        anchor_tokens = [_tokens(str(topic).replace("-", " ")) for topic in cluster.get("candidate_canonical_topics", [])]
        external_node_labels = {
            str(item.get("label") or "").lower()
            for item in ext.get("node_candidates", [])
            if isinstance(item, dict)
        }
        external_alias_labels = _extract_hint_labels(ext.get("suggested_aliases", []))
        external_candidate_topic_labels = {
            str(item.get("label") or "").lower()
            for item in ext.get("candidate_topics", [])
            if isinstance(item, dict)
        }
        external_candidate_topic_labels.update(_extract_hint_labels(ext.get("candidate_topics", [])))
        external_edge_by_node: dict[str, int] = {}
        for edge in ext.get("edge_candidates", []):
            if not isinstance(edge, dict):
                continue
            for node_key in ("source_node_id", "target_node_id"):
                node_id = str(edge.get(node_key) or "").strip()
                if node_id:
                    external_edge_by_node[node_id] = external_edge_by_node.get(node_id, 0) + 1
        suggestions: list[dict[str, Any]] = []

        for node in cluster.get("nodes", []):
            if node.get("node_type") != "candidate_topic":
                continue
            node_id = node.get("node_id")
            label = str(node.get("label") or "").strip()
            lower_label = label.lower()
            record = candidate_record_by_node.get(node_id, {})
            label_tokens = _tokens(label)
            edge_evidence = [
                edge for edge in cluster.get("edges", [])
                if edge.get("target_node_id") == node_id or edge.get("source_node_id") == node_id
            ]
            support_edges = [edge for edge in edge_evidence if edge.get("edge_type") in {"supports_candidate", "associated_with", "related_to"}]
            typed_edges = [edge for edge in edge_evidence if edge.get("edge_type") in {"symbolizes", "used_in", "role_assigned_to", "deeper_than"}]
            evidence_count = len(edge_evidence) + len(node.get("provenance", {}).get("sources", []))
            recurrence_sources: set[str] = set()
            if isinstance(record, dict):
                work_id = str(record.get("work_id") or "").strip()
                section_id = str(record.get("section_id") or "").strip()
                source_family = str(record.get("source_family") or "").strip()
                if work_id:
                    recurrence_sources.add(f"work:{work_id}")
                if section_id:
                    recurrence_sources.add(f"section:{section_id}")
                if source_family:
                    recurrence_sources.add(f"source_family:{source_family}")
            for peer in candidate_records:
                if not isinstance(peer, dict) or peer.get("candidate_node_id") == node_id:
                    continue
                peer_tokens = _tokens(str(peer.get("title") or ""))
                if _jaccard(label_tokens, peer_tokens) >= 0.30:
                    recurrence_sources.add(f"work:{peer.get('work_id')}")
                    recurrence_sources.add(f"source_family:{peer.get('source_family')}")
            source_count = len({item for item in recurrence_sources if item and not item.endswith(":")})
            source_count += int(ext.get("review_count", 0))
            external_confidence = max(ext.get("confidence_scores", [0.0]) or [0.0])
            anchor_count = len(record.get("anchors", [])) if isinstance(record, dict) else 0
            max_anchor_similarity = 0.0
            for tokens in anchor_tokens:
                max_anchor_similarity = max(max_anchor_similarity, _jaccard(label_tokens, tokens))

            distinct_identity = max_anchor_similarity < 0.74 and lower_label not in alias_labels and lower_label not in external_alias_labels
            boundary_clarity = "clear"
            if anchor_count == 0 or len(cluster.get("candidate_canonical_topics", [])) > 8:
                boundary_clarity = "unclear"
            retrieval_value = "high" if (anchor_count >= 2 and evidence_count >= 4) else ("medium" if evidence_count >= 2 else "low")
            product_usefulness = "high" if (len(typed_edges) >= 1 and anchor_count >= 1) else ("medium" if len(support_edges) >= 2 else "low")
            conflict_flags: list[str] = []
            if ext.get("conflicts"):
                conflict_flags.append("external_conflicts_present")
            if boundary_clarity == "unclear":
                conflict_flags.append("boundary_ambiguity")
            if not distinct_identity:
                conflict_flags.append("identity_overlap")

            is_split = lower_label in split_labels
            is_merge = lower_label in merge_labels
            is_alias = lower_label in alias_labels or lower_label in external_alias_labels or max_anchor_similarity >= 0.80
            node_overlay_hits = [
                item for item in cluster.get("candidate_overlays", [])
                if isinstance(item, dict) and item.get("candidate_node_id") == node_id
            ]
            node_deeper_hits = [
                item for item in cluster.get("candidate_deeper_links", [])
                if isinstance(item, dict)
                and (
                    str(item.get("source_label") or "").strip().lower() == lower_label
                    or item.get("candidate_node_id") == node_id
                )
            ]
            external_support = (
                lower_label in external_node_labels
                or lower_label in external_candidate_topic_labels
                or ext.get("review_count", 0) > 0 and external_edge_by_node.get(str(node_id), 0) > 0
            )
            is_overlay = lower_label in overlay_labels or len(node_overlay_hits) > 0
            is_deeper = lower_label in deeper_labels or len(node_deeper_hits) > 0

            classification = "no_action_insufficient_evidence"
            if is_split:
                classification = "recommend_split"
            elif is_merge:
                classification = "recommend_merge"
            elif is_alias:
                classification = "alias_only"
            elif is_overlay and not distinct_identity:
                classification = "overlay_dimension"
            elif is_deeper and (evidence_count >= 2 or external_confidence >= 0.6):
                classification = "deeper_research_link"
            elif (
                distinct_identity
                and boundary_clarity == "clear"
                and retrieval_value in {"high", "medium"}
                and product_usefulness in {"high", "medium"}
                and source_count >= 2
                and anchor_count >= 1
            ):
                classification = "promote_canonical_topic_candidate"
            if classification == "no_action_insufficient_evidence" and external_support and (evidence_count >= 2 or external_confidence >= 0.75):
                classification = "deeper_research_link"

            aggregate_counts[classification] += 1
            suggestions.append(
                {
                    "suggestion_id": f"sug:{cid}:{node_id}",
                    "label": label,
                    "classification": classification,
                    "evidence": {
                        "evidence_count": evidence_count,
                        "source_count": source_count,
                        "boundary_clarity": boundary_clarity,
                        "retrieval_value": retrieval_value,
                        "product_usefulness": product_usefulness,
                        "conflict_flags": conflict_flags,
                        "external_support": bool(external_support),
                        "external_confidence": external_confidence,
                    },
                    "provenance": {
                        "cluster_id": cid,
                        "node_ids": [node_id],
                        "edge_ids": [edge.get("edge_id") for edge in edge_evidence],
                        "candidate_record": record,
                    },
                    "operator_action_required": True,
                }
            )

        cluster_level_actions: list[dict[str, Any]] = []
        for item in cluster.get("split_suggestions", []):
            if isinstance(item, dict):
                aggregate_counts["recommend_split"] += 1
                cluster_level_actions.append(
                    {"kind": "split", "classification": "recommend_split", "payload": item, "operator_action_required": True}
                )
        for item in cluster.get("merge_suggestions", []):
            if isinstance(item, dict):
                aggregate_counts["recommend_merge"] += 1
                cluster_level_actions.append(
                    {"kind": "merge", "classification": "recommend_merge", "payload": item, "operator_action_required": True}
                )

        cluster_reports.append(
            {
                "cluster_id": cid,
                "suggestions": suggestions,
                "cluster_level_actions": cluster_level_actions,
                "external_review_count": int(ext.get("review_count", 0)),
                "external_review_sources": sorted(ext.get("source_names", set())),
                "external_notes": ext.get("notes", []),
                "external_conflicts": ext.get("conflicts", []),
                "external_node_candidate_count": int(ext.get("node_candidate_count", 0)),
                "external_edge_candidate_count": int(ext.get("edge_candidate_count", 0)),
                "external_confidence_max": max(ext.get("confidence_scores", [0.0]) or [0.0]),
            }
        )

    return {"cluster_reports": cluster_reports, "aggregate_counts": aggregate_counts}
