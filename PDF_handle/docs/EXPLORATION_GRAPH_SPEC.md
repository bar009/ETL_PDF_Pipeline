# Exploration Graph Spec

## Purpose

Define an additive semantic exploration lane that captures topology evidence from staged ETL outputs and optional external review inputs, without mutating canonical site JSON by default.

This lane exists to improve review quality around:

- topic to symbol relationships
- topic to ritual stage relationships
- topic to role or office relationships
- topic to space or chamber relationships
- topic to tradition/source relationships
- deeper symbolic adjacency

## Scope

In scope:

- build small semantic clusters from Step 5 staged artifacts
- normalize optional external semantic review input into a typed graph contract
- produce typed node and edge artifacts with provenance and review metadata
- produce reconciliation suggestions for operator review
- write replayable run artifacts under `PDF_handle/runs/`

Out of scope:

- replacing Step 5 or Step 6 behavior
- auto-merging into live site datasets
- treating external mind-map output as canonical truth
- adding exploration review to default E2E, preprocess, or postmerge paths

## Non-Goals

- no direct mutation of `data/library.json`, `data/level1.json`, `data/level2.json`, or `data/level3.json`
- no untyped "single giant graph"
- no external vendor lock-in in the import contract

## Canonical Location and Ownership

- code owner: `PDF_handle/prod/exploration/`
- standalone CLI: `PDF_handle/prod/cli/exploration_review.py`
- run artifacts: `PDF_handle/runs/exploration_review/<run_id>/`

## Artifact Layout

Each exploration run writes:

- `run_manifest.json`
- `clusters_index.json`
- `graph_clusters/<cluster_id>.json`
- `normalized_external_reviews.json` (when supplied)
- `reconciliation_report.json`
- `summary_report.json`

## Typed Data Model

### Node Types

- `topic`
- `candidate_topic`
- `space`
- `office_role`
- `symbol`
- `ritual_stage`
- `concept`
- `source_term`
- `tradition_reference`
- `overlay`
- `deeper_link`
- `alias`

### Edge Types

- `part_of`
- `associated_with`
- `symbolizes`
- `used_in`
- `precedes`
- `role_assigned_to`
- `alias_of`
- `deeper_than`
- `related_to`
- `appears_with`
- `supports_candidate`
- `split_from`
- `merge_candidate_with`

### Node Contract

```json
{
  "node_id": "node:candidate_topic:brotherly-love",
  "node_type": "candidate_topic",
  "label": "Brotherly Love",
  "canonical_slug": null,
  "attributes": {
    "degree_hint": "level1",
    "keywords": ["brotherhood", "charity"]
  },
  "provenance": {
    "sources": [
      {
        "source_kind": "step5_companion_candidate",
        "work_id": "duncans-ritual-monitor-1866",
        "section_id": "S12"
      }
    ]
  },
  "review": {
    "status": "pending",
    "confidence": "medium",
    "notes": []
  }
}
```

### Edge Contract

```json
{
  "edge_id": "edge:supports_candidate:topic-charity:candidate-brotherly-love",
  "edge_type": "supports_candidate",
  "source_node_id": "node:topic:charity",
  "target_node_id": "node:candidate_topic:brotherly-love",
  "weight": 0.72,
  "evidence_count": 3,
  "provenance": {
    "sources": [
      {
        "source_kind": "step5_level1_patch",
        "marker_id": "step5-source:duncans-ritual-monitor-1866:S12"
      }
    ]
  },
  "review": {
    "status": "pending",
    "notes": []
  }
}
```

### Cluster Artifact Contract

```json
{
  "cluster_id": "cluster:candidate:brotherly-love",
  "seed_topic": "Brotherly Love",
  "created_at": "2026-04-07T12:00:00Z",
  "source_inputs": ["companion_candidates.json", "link_report.json", "level1.patch.json", "level2.patch.json"],
  "nodes": [],
  "edges": [],
  "candidate_canonical_topics": [],
  "candidate_aliases": [],
  "candidate_overlays": [],
  "candidate_deeper_links": [],
  "split_suggestions": [],
  "merge_suggestions": [],
  "review_notes": [],
  "provenance": {
    "staging_dir": "PDF_handle/staged_injection",
    "generator": "prod.cli.exploration_review"
  }
}
```

### External Review Import Contract

External inputs must be normalized into this contract:

```json
{
  "source_name": "manual_notebook_review",
  "review_id": "nblm-2026-04-07-01",
  "cluster_hint": "cluster:candidate:brotherly-love",
  "node_candidates": [],
  "edge_candidates": [],
  "alias_hints": [],
  "split_hints": [],
  "merge_hints": [],
  "overlay_hints": [],
  "deeper_link_hints": [],
  "confidence": "medium",
  "conflicts": [],
  "notes": [],
  "nodes": [],
  "edges": [],
  "suggestions": {
    "candidate_topics": [],
    "aliases": [],
    "overlays": [],
    "deeper_links": [],
    "splits": [],
    "merges": []
  },
  "provenance": {
    "captured_at": "2026-04-07T12:00:00Z",
    "operator": "manual"
  }
}
```

The import contract is vendor-neutral and supports manual or semi-manual extraction.

## Cluster Formation Rules

Clusters are created when one or more seed conditions hold:

1. repeated `new_topic_candidates` signals for same normalized phrase family
2. companion candidates with weak/medium canonical match confidence
3. dense local link neighborhoods around the same candidate phrase family
4. recurring lexical families across staged sections

Cluster size constraints:

- max nodes per cluster (default): 25
- max edges per cluster (default): 60
- if limit is exceeded, split by phrase-family root

Naming:

- `cluster:candidate:<normalized-seed>`
- fallback: `cluster:work:<work_id>:<hash8>`

## Operator Flow

1. run Step 5 as usual
2. run exploration CLI against a staging directory
3. optionally include external review JSON
4. inspect generated cluster artifacts and reconciliation report
5. manually decide what, if anything, should become canonical Step 5/6 review input

Optional prod hook:

- `PDF_handle/prod/cli/postmerge.py` now runs exploration review automatically after Step 5 state exists
- `PDF_handle/prod/cli/e2e.py` inherits the same automatic sidecar behavior through postmerge phases
- `--skip-exploration-review` disables the sidecar when an operator needs a narrower run
- the hook remains report-only and never mutates live site data

## Acceptance Criteria

- standalone execution from `PDF_handle/prod/cli/exploration_review.py`
- no mutation of live site data
- all outputs under `PDF_handle/runs/`
- typed node and edge model enforced
- provenance present on generated nodes, edges, and suggestions
- deterministic replay given same inputs

## Stop Conditions

- stop if required Step 5 staged artifacts are missing
- stop if external review payload cannot normalize to typed contract
- stop if generated clusters exceed configured limits in a way that prevents reviewability

## Open Questions

- should future Step 6 review templates accept exploration suggestions as optional attachments
- should alias promotion policy differ by degree lane
- should cluster splitting thresholds become route-specific per work family
