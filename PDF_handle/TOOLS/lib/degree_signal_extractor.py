from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .degree_signal_registry import normalize_degree_signal_text


STRENGTH_SCORES = {"strong": 3, "medium": 2, "weak": 1}


def _phrase_present(*, normalized_text: str, normalized_phrase: str) -> bool:
    if not normalized_text or not normalized_phrase:
        return False
    pattern = r"(?<!\S)" + re.escape(normalized_phrase).replace(r"\ ", r"\s+") + r"(?!\S)"
    return bool(re.search(pattern, normalized_text))


def extract_degree_signals(
    text: str,
    target_degree: int,
    registry: dict[str, Any],
) -> dict[str, Any]:
    normalized_text = normalize_degree_signal_text(text)
    hits: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    degree_strength_totals: Counter[str] = Counter()
    concept_type_counts: Counter[str] = Counter()
    degree_hit_counts: Counter[str] = Counter()

    for entry in registry["entries"]:
        matched_variants = [
            variant
            for variant in entry["normalized_variants"]
            if _phrase_present(normalized_text=normalized_text, normalized_phrase=variant)
        ]
        if not matched_variants:
            continue
        cooccurrence_hits = [
            phrase
            for phrase in entry.get("normalized_cooccurrence_preferred", [])
            if _phrase_present(normalized_text=normalized_text, normalized_phrase=phrase)
        ]
        hit = {
            "id": entry["id"],
            "canonical_term": entry["canonical_term"],
            "degree_hint": entry["degree_hint"],
            "strength": entry["strength"],
            "concept_type": entry["concept_type"],
            "families": list(entry["families"]),
            "matched_variants": matched_variants,
            "cooccurrence_hits": cooccurrence_hits,
            "standalone_allowed": bool(entry["standalone_allowed"]),
            "purity_weights": dict(entry["purity_weights"]),
        }
        hits.append(hit)
        degree_key = f"degree_{entry['degree_hint']}"
        degree_strength_totals[degree_key] += STRENGTH_SCORES[entry["strength"]]
        degree_hit_counts[degree_key] += 1
        concept_type_counts[entry["concept_type"]] += 1
        for family in entry["families"]:
            family_counts[family] += 1

    active_degrees = {
        hit["degree_hint"]
        for hit in hits
        if STRENGTH_SCORES[hit["strength"]] >= 2
    }
    cross_degree_collision = len(active_degrees) > 1
    weak_only_bucket = bool(hits) and all(hit["strength"] == "weak" for hit in hits)

    return {
        "target_degree": target_degree,
        "normalized_text": normalized_text,
        "hits": hits,
        "hit_count": len(hits),
        "degree_family_counts": dict(sorted(family_counts.items())),
        "degree_strength_totals": dict(sorted(degree_strength_totals.items())),
        "degree_concept_type_counts": dict(sorted(concept_type_counts.items())),
        "degree_hit_counts": dict(sorted(degree_hit_counts.items())),
        "cross_degree_collision": cross_degree_collision,
        "weak_only_bucket": weak_only_bucket,
    }


def compute_degree_purity_enrichment(
    extraction: dict[str, Any],
    target_degree: int,
) -> dict[str, Any]:
    hits = list(extraction.get("hits") or [])
    target_hits = [hit for hit in hits if hit["degree_hint"] == target_degree]
    higher_hits = [hit for hit in hits if hit["degree_hint"] != target_degree]
    target_strong_hits = [hit for hit in target_hits if hit["strength"] == "strong"]
    higher_medium_or_strong_hits = [hit for hit in higher_hits if STRENGTH_SCORES[hit["strength"]] >= 2]
    target_weak_virtues = [
        hit
        for hit in target_hits
        if hit["strength"] == "weak" and hit["concept_type"] == "virtue"
    ]
    suppressed_weak_hits = [
        hit
        for hit in target_weak_virtues
        if not hit["standalone_allowed"] and not hit["cooccurrence_hits"]
    ]

    family_counts = Counter()
    for hit in target_hits:
        for family in hit["families"]:
            family_counts[family] += 1
    family_concentration_detected = any(count >= 2 for count in family_counts.values())
    native_weight_key = f"native_degree_{target_degree}"
    foreign_weight_key = f"foreign_risk_if_target_{target_degree}"
    target_native_weight_total = sum(
        int(hit["purity_weights"].get(native_weight_key) or 0) for hit in target_hits
    )
    higher_foreign_weight_total = sum(
        int(hit["purity_weights"].get(foreign_weight_key) or 0) for hit in higher_hits
    )

    degree_reason_codes: list[str] = []
    native_boost = 0
    foreign_boost = 0
    mixedness_boost = 0
    native_suppression = 0

    strong_anchor_degrees = sorted({hit["degree_hint"] for hit in hits if hit["strength"] == "strong"})
    for degree in strong_anchor_degrees:
        degree_reason_codes.append(f"degree_{degree}_strong_anchor_detected")

    if target_strong_hits:
        native_boost += 2
    elif target_native_weight_total >= 3:
        native_boost += 1
    if family_concentration_detected and target_hits:
        native_boost += 1
        degree_reason_codes.append("degree_family_concentration_detected")

    if target_weak_virtues and len(target_weak_virtues) >= 2:
        degree_reason_codes.append("weak_moral_cluster_detected")
    if suppressed_weak_hits:
        degree_reason_codes.append("standalone_weak_term_suppressed")
        if not target_strong_hits:
            native_suppression += 1

    if higher_medium_or_strong_hits:
        foreign_boost += 2
        degree_reason_codes.append("higher_degree_contamination_detected")
    elif higher_hits:
        foreign_boost += 1
        degree_reason_codes.append("higher_degree_contamination_detected")
    if higher_foreign_weight_total >= 3:
        foreign_boost += 1

    if extraction.get("cross_degree_collision"):
        mixedness_boost += 1
        degree_reason_codes.append("cross_degree_collision_detected")

    degree_reason_codes = list(dict.fromkeys(degree_reason_codes))
    return {
        "native_boost": native_boost,
        "foreign_boost": foreign_boost,
        "mixedness_boost": mixedness_boost,
        "native_suppression": native_suppression,
        "degree_reason_codes": degree_reason_codes,
        "family_concentration_detected": family_concentration_detected,
        "weak_only_bucket": bool(extraction.get("weak_only_bucket")),
        "target_strong_anchor_detected": bool(target_strong_hits),
        "higher_degree_hit_ids": [hit["id"] for hit in higher_hits],
        "target_native_weight_total": target_native_weight_total,
        "higher_foreign_weight_total": higher_foreign_weight_total,
    }
