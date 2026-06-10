# Degree Signal Registry Step 1

## Goal

Add a degree-aware signal registry layer to `semantic_system_purity_review.py` so F2 can:

- detect strong degree anchors deterministically
- suppress over-classification from weak moral terms
- detect cross-degree contamination and collisions
- emit explainable degree-based observability

Step 1 is intentionally narrow.

It includes:

- `degree_signal_registry.py`
- `degree_signal_extractor.py`
- `data/degree_terms_registry.json` with a small seed set
- F2-only integration
- observability and micro-regression

It does not include:

- `routing_bias_registry.json`
- F3 integration
- broad coverage expansion

## Core Design

The registry is not a flat keyword list.

Each term entry carries:

- `degree_hint`
- `strength`
- `concept_type`
- `families`
- variants
- co-occurrence preferences
- standalone suppression policy
- purity weights

The system should classify through:

- anchor strength
- family concentration
- co-occurrence support
- degree collision
- weak-term suppression

Not through isolated word hits.

## Step 1 Scope

### Assets

- `PDF_handle/TOOLS/data/degree_terms_registry.json`

### New Modules

- `PDF_handle/TOOLS/degree_signal_registry.py`
- `PDF_handle/TOOLS/degree_signal_extractor.py`

### Integration Target

- `PDF_handle/TOOLS/semantic_system_purity_review.py`

### Regression Target

- strong degree-1 anchors
- weak moral-only cases
- degree-2 contamination
- degree-3 contamination
- mixed cross-degree collision

## Registry Policy

Step 1 should seed only a compact set of high-signal entries plus a few weak moral controls.

The seed should stay around `15-25` entries.

The main target is to prove the infrastructure, not to maximize coverage.

## F2 Extraction Output

Each F2 row should expose at least:

- `degree_signal_hits`
- `degree_signal_hit_count`
- `degree_family_counts`
- `degree_strength_totals`
- `degree_concept_type_counts`
- `cross_degree_collision`
- `degree_reason_codes`

Useful additional fields are allowed if they improve auditability.

## F2 Scoring Rules

### Rule A

Strong target-degree anchors boost native confidence.

### Rule B

Weak moral terms do not classify alone.

Weak virtue-only hits should be suppressed unless supported by cluster or co-occurrence.

### Rule C

Family concentration matters.

Two or more reinforcing hits in the same strong family should increase confidence.

### Rule D

Higher-degree anchors in a degree-1 target increase foreign risk.

### Rule E

Cross-degree strong/medium collisions increase mixedness.

### Rule F

Standalone weak terms with `standalone_allowed=false` should emit explicit suppression reason codes.

## Required F2 Reason Codes

- `degree_1_strong_anchor_detected`
- `degree_2_strong_anchor_detected`
- `degree_3_strong_anchor_detected`
- `degree_family_concentration_detected`
- `weak_moral_cluster_detected`
- `cross_degree_collision_detected`
- `higher_degree_contamination_detected`
- `standalone_weak_term_suppressed`

## Run-Contract Requirement

The degree registry is part of the F2 decision basis.

Registry changes must invalidate resume compatibility through run metadata and manifest compatibility.

## Micro-Regression Acceptance

Step 1 passes only if:

- strong degree-1 anchors are detected deterministically
- weak moral-only text does not get over-confident native boosting
- degree-2 and degree-3 contamination become visible in row-level outputs
- cross-degree collision is emitted on mixed anchor texts
- F2 observability is sufficient to inspect the above without manual inference

## Rollout Rule

Do not expand to F3 until Step 1 is stable in F2.

Do not expand registry coverage broadly until the seed set and regression suite pass cleanly.
