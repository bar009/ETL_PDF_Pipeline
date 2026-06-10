# Exploration Reconciliation Policy

## Purpose

Define how exploration graph outputs are classified into reviewable recommendation categories without automatically mutating canonical site data.

The policy enforces the distinction between:

- semantic adjacency
- ontology typing
- product-level canonical decisions

## Decision Categories

Each suggestion must map to exactly one category:

- `promote_canonical_topic_candidate`
- `alias_only`
- `overlay_dimension`
- `deeper_research_link`
- `recommend_split`
- `recommend_merge`
- `no_action_insufficient_evidence`

## Evidence Model

Each suggestion carries:

- `evidence_count`
- `source_count`
- `boundary_clarity` (`clear` / `unclear`)
- `retrieval_value` (`high` / `medium` / `low`)
- `product_usefulness` (`high` / `medium` / `low`)
- `conflict_flags` (array)

## Promotion Heuristics

A suggestion qualifies for `promote_canonical_topic_candidate` only when all conditions pass:

1. distinct identity from existing canonical topics
2. retrieval usefulness is at least `medium`
3. source support is multi-source (`source_count >= 2`) or has strong direct evidence (`evidence_count >= 3`)
4. boundary clarity is `clear`
5. product usefulness is at least `medium`

If any condition fails, classification must fall back to a non-canonical category.

## Alias Rules

Classify as `alias_only` when:

- concept appears synonymous to existing canonical node
- differentiation signal is weak
- evidence supports naming/lookup expansion more than taxonomy expansion

## Overlay Rules

Classify as `overlay_dimension` when:

- signal behaves as a cross-cutting facet (role, chamber, symbol frame, ritual stage context)
- forcing canonical topic status would flatten ontology boundaries

## Deeper Link Rules

Classify as `deeper_research_link` when:

- relation is meaningful but exploratory or speculative
- evidence is present but insufficient for canonical promotion
- keeping it as typed adjacency provides discovery value

## Split Rules

Classify as `recommend_split` when:

- one candidate or canonical topic spans multiple semantically distinct clusters
- graph structure shows persistent branching with low shared core

## Merge Rules

Classify as `recommend_merge` when:

- near-duplicate candidates show high overlap in evidence and neighborhood
- distinctions are mostly lexical, not conceptual

## No-Action Rules

Classify as `no_action_insufficient_evidence` when:

- evidence is sparse, contradictory, or low-quality
- boundary clarity remains uncertain after normalization
- suggestion would introduce taxonomy noise

## Operational Guardrails

- exploration reconciliation never writes live site data by default
- Step 6 remains canonical mutation gate
- external review is evidence only, not authority
- all reconciliations must be traceable to source artifacts
- external review confidence may increase or dampen exploratory classifications, but never overrides mutation policy

## Required Output Shape

```json
{
  "cluster_id": "cluster:candidate:brotherly-love",
  "suggestions": [
    {
      "suggestion_id": "sug:brotherly-love",
      "label": "Brotherly Love",
      "classification": "promote_canonical_topic_candidate",
      "evidence": {
        "evidence_count": 4,
        "source_count": 2,
        "boundary_clarity": "clear",
        "retrieval_value": "high",
        "product_usefulness": "high",
        "conflict_flags": []
      },
      "provenance": {
        "node_ids": ["node:candidate_topic:brotherly-love"],
        "edge_ids": ["edge:supports_candidate:topic-charity:candidate-brotherly-love"]
      },
      "operator_action_required": true
    }
  ]
}
```

## Manual Adoption Boundary

The first implementation produces only:

- typed graph artifacts
- normalized external review evidence
- reconciliation recommendations

It intentionally does not automate:

- approval creation for Step 6
- direct patch generation for live degrees
- mutation of canonical datasets
