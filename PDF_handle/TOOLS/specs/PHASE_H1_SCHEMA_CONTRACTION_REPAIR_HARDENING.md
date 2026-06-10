# Phase H.1: Schema Contraction & Repair Hardening

Phase H.1 is a focused hardening pass for the shared provider runtime and the F2/F3 structured-output contracts.

Its goal is to reduce:

- `malformed_json`
- `gemini_failed_attempt_count`
- retry overhead
- parse/repair noise
- false recoveries caused by over-aggressive repair

without changing:

- gating policy
- provider policy
- model selection
- threshold calibration
- wider business logic

## Core Principle

Phase H.1 does not attempt to "improve the model" directly.

It reduces the provider error surface by:

- shrinking provider-facing response schemas
- moving derivable fields into deterministic local logic
- hardening repair so real provider failures remain visible

This is a constrained structured-output phase, not a prompt-rewrite phase and not a calibration phase.

## Scope

In scope:

- `semantic_system_purity_review.py`
- `content_routing_review.py`
- `provider_runtime.py`
- the F2/F3 prompt templates that define the structured provider contract
- schema/version markers needed for resume safety

Out of scope:

- gating calibration
- provider-policy changes
- model upgrades
- large prompt rewrites
- runtime-boundary redesign
- summary/provenance redesign beyond required compatibility bumps

## Semantic Schema Minimization

`semantic_system_purity_review.py` should keep only the provider fields that are actually required for bounded semantic judgment.

The provider response schema should be reduced to:

- `detected_system_family`
- `detection_confidence`
- `semantic_verdict`
- `recommended_destination`
- `explanation`

The provider should not be asked to emit fields that can be derived locally after a valid payload is received.

## Local Derivation for F2

The following F2 fields should be derived locally rather than returned by the provider:

- `is_comparative`
- `is_framed`
- `framing_source`
- `recommended_preservation_action`

The rule is simple:

- if a field can be computed deterministically from the validated payload and local policy, it should not live in the provider schema

## Routing Schema Minimization

`content_routing_review.py` should keep only the provider fields that are required for bounded routing judgment.

The provider response schema should be reduced to:

- `routing_decision`
- `routing_confidence`
- `target_slug`
- `future_entry_label`
- `library_bucket`
- `explanation`

No additional provider fields should be retained in Phase H.1 unless they are strictly necessary for routing correctness.

## Local Derivation for F3

The following F3 fields should be derived locally:

- `target_kind`
- `preservation_value`
- `rewrite_needed`
- `cleanup_priority`

Additionally:

- `taxonomy_match_reason` should be derived locally only if it can be computed deterministically and reliably from the checked-in routing taxonomy and local helpers

## Repair Hardening

`provider_runtime.py` should keep repair behavior minimal.

Allowed repair:

- stripping markdown fences
- minimal normalization that does not invent or reconstruct payload structure

Disallowed repair:

- substring rescue from the first `{` to the last `}`
- aggressive JSON reconstruction
- salvage heuristics
- guessed closing or restructuring of broken objects
- any repair path that obscures the true provider failure mode

If strict parse still fails after fence stripping:

- the runtime should classify the result as a structured failure
- the caller should not attempt additional repair

## Few-Shot Anchoring

The F2 and F3 templates should add only a small few-shot anchor set:

- one clean example
- one ambiguous example

Constraints:

- examples must be short
- examples must match the contracted schema exactly
- examples must not turn the prompt into a large prompt-rewrite exercise

## Versioning and Resume Safety

Because Phase H.1 changes provider-facing schemas and local derivation responsibilities, version/schema markers must be bumped so resume remains safe.

At minimum, update the relevant markers for:

- row schema compatibility
- summary compatibility if affected
- state compatibility if affected
- script/runtime contract version if needed

Old report dirs that were produced under the previous structured-output contract must not be treated as silently resume-compatible.

## Engineering Rationale

Phase H.1 is intentionally conservative.

It is based on three engineering rules:

1. Smaller schemas are usually more stable than larger schemas.
2. Deterministic local derivation is preferable to statistical inference whenever the field does not require real model judgment.
3. Over-repair produces misleading success signals and hides the provider's real quality profile.

The goal is not prettier metrics.
The goal is truer metrics and a smaller provider error surface.

## What Not To Change In This Phase

Do not combine Phase H.1 with:

- threshold tuning
- provider-policy changes
- model switches
- broad prompt rewriting
- routing-policy redesign
- simultaneous business-logic rewrites

Phase H.1 should remain a clean structured-output hardening pass.

## Recommended Execution Order

1. Contract `SEMANTIC_RESPONSE_SCHEMA`.
2. Contract `ROUTING_RESPONSE_SCHEMA`.
3. Add local derivation for removed provider fields.
4. Harden `_repair_json_text(...)` to minimal repair only.
5. Add a small few-shot anchor set to the relevant templates.
6. Bump compatibility/version markers.
7. Re-run `run_phase_h_post_gating_smoke.py`.
8. Compare the results against the pre-H.1 Phase H smoke.

## Expected Outcomes

If the implementation is correct, the next post-gating smoke should show:

- lower `malformed_json_count`
- lower `gemini_failed_attempt_count`
- fewer retries
- less repair activity
- a more honest picture of provider quality

It is acceptable if some failures become more explicit in the short term.

That is not regression.
It is the removal of cosmetic recovery paths that previously blurred real provider behavior.

## Success Criteria

Phase H.1 is successful only if:

- semantic provider schema is reduced to the required minimal fields
- routing provider schema is reduced to the required minimal fields
- removed provider fields are derived locally without breaking downstream logic
- aggressive repair paths are removed
- few-shot anchors are added without materially bloating the prompts
- compatibility/version markers are bumped correctly
- the post-H gating smoke runs successfully
- `malformed_json_count` decreases
- provider failed attempts decrease
- runtime does not materially worsen
- output quality remains acceptable in manual sample inspection
- gating, resume, summaries, and run-contract behavior remain intact
