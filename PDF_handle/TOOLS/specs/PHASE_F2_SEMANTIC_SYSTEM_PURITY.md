# Phase F2: Semantic System Purity Review

Phase F2 adds a semantic layer on top of the existing F1 system-purity audit.

- F1 detects explicit or strongly lexical foreign-system signals.
- F2 reviews each paragraph as a bounded semantic unit.
- F2 never mutates site data.

## Scope

v1 is limited to:

- `level1`
- the manifest subset `level1.phase1-plus-phase2.json`
- paragraph review for:
  - `reading_layers.basic`
  - `reading_layers.symbolic`
  - `reading_layers.advanced`
  - `symbolic_meaning`
  - `candidate_lesson`
  - `full_summary`

Out of scope in v1:

- `short_summary`
- site schema changes
- cleanup automation
- writing back to `level1.json`

## Core Flow

Each run:

1. validates the manifest as `level1`
2. runs embedded F1 into `f1_baseline/`
3. reviews each paragraph in the selected subset
4. emits F2 JSON, Markdown, and HTML artifacts

The run fails only for structural/runtime reasons such as:

- invalid manifest
- embedded F1 failure
- unrecoverable runtime failure

Paragraph-level `flag_error` is a content diagnosis, not a run-level failure trigger.

## Decision Layers

Each paragraph carries three decision layers:

- `lexical_overlay`
  - deterministic marker-based signal reused from F1 helpers
- `semantic_verdict`
  - bounded semantic classification from Gemini or heuristic fallback
- `final_verdict`
  - local policy decision used by reports and status logic

This separation is intentional so false positives and disagreements stay inspectable.

## Stable Review Units

Each paragraph review uses:

- `review_unit_id = <entry_slug>::<field_name>::p<paragraph_index>`

This supports:

- diffing between runs
- manual triage
- future cleanup mapping

## Destination Rules

`recommended_destination` is hard-bounded to:

- `null`
- `"library/research"`
- a valid whitelisted slug

Free-text destinations are not allowed.

## Provider Tracking

Each paragraph also records:

- `provider_status`
  - `ok`
  - `retry_recovered`
  - `fallback_heuristic`
  - `validation_failed`
  - `skipped`
- `decision_source`
  - `gemini`
  - `heuristic`
  - `hybrid`
  - `fallback_heuristic`

This makes later calibration and audit-quality analysis possible.
