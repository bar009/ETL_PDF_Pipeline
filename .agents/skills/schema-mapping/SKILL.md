---
name: schema-mapping
description: Work on Step 5 and Step 6 mapping, normalization, staged patch generation, and live merge behavior in PDF_handle. Use when Codex needs to modify schema-facing logic, mapping prompts, degree operations, candidate entries, relation behavior, or validation/report contracts around site JSON.
---

# Schema Mapping

Use this skill for mapping and merge work that touches site-data contracts.

## Read First

Read these files in order:

1. `PDF_handle/AGENTS.md`
2. `PDF_handle/docs/JSON_SCHEMA_SPEC.md`
3. `PDF_handle/docs/DOMAIN_BOUNDARIES.md`
4. `PDF_handle/docs/RELATION_RULES.md`
5. `PDF_handle/docs/DECISION_LOG.md`

Then read:

- `PDF_handle/step_05_map_and_stage.py`
- `PDF_handle/step_06_apply_reviewed_merge.py`
- `PDF_handle/stage5_utils.py`
- `PDF_handle/pipeline_utils.py`

## Working Rules

1. Keep Step 5 review-first.
2. Keep Step 6 explicit about live apply.
3. Preserve schema validation and cross-reference validation.
4. Keep `library`, `level1`, and `level2` roles distinct.
5. Prefer explicit path wiring over hidden defaults when expanding behavior.

## Checklist

- Does the change alter staged patch shape?
- Does the change alter live merge shape?
- Does the change alter relation semantics?
- Does the change alter source-note or provenance handling?
- Does the change require doc updates in `PDF_handle/docs/JSON_SCHEMA_SPEC.md` or `PDF_handle/docs/RELATION_RULES.md`?

## Do Not

- bypass normalization helpers for convenience
- let a tool-layer shortcut become the only definition of a schema rule
- treat companion candidates as auto-approved content
