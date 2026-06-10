# AGENTS.override.md

Local override for `PDF_handle/TOOLS/`.

## Purpose

`TOOLS/` is the operational layer around the canonical seven-step pipeline.
It contains wrappers, audits, validation helpers, phase runners, specs, and generated report trees.

Primary subfolders now include:

- `runners/`
- `audits/`
- `validation/`
- `apply/`
- `lib/`
- `specs/`

Root-level files in `TOOLS/` should now be limited to:

- compatibility shims that preserve old command paths
- import wrappers for shared runtime modules now implemented under `lib/`
- top-level operator entry docs such as `README.md` plus manifests and generated-data folders

## Parent Context

Read parent guidance first:

1. `PDF_handle/AGENTS.md`
2. `PDF_handle/docs/ETL_FLOW.md`
3. `PDF_handle/docs/DOMAIN_BOUNDARIES.md`

Then use this file for tool-layer rules.

## Rules

1. Do not redefine the canonical ETL contract here if the real change belongs in `step_01` to `step_07`.
2. Prefer wrappers and audits to remain explicit about whether they mutate live data or not.
3. Keep path defaults reviewable and avoid adding fresh hardcoded roots without documenting them.
4. Treat `README.md` and the phase/spec markdown files as operational references, not executable truth.
5. If you add a new tool, be explicit whether it is:
   - runner
   - audit
   - validation
   - apply
   - phase-specific
6. Prefer placing new implementations in the role-based subfolders and keep root files only as compatibility shims when needed.
7. Do not add new executable implementations directly at the root of `TOOLS/` unless they are shared helpers or a deliberate compatibility wrapper.

## Mutation Policy

- Audit tools should be read-only unless their contract clearly says otherwise.
- Apply tools must state exactly what they mutate and under which mode.
- New tools should prefer writing reports under `TOOLS/reports/` rather than beside source logic.

## Validation Focus

When modifying `TOOLS/`:

1. verify the command-line interface still matches the docs
2. verify report paths are still correct
3. verify whether the tool should remain read-only
4. update `PDF_handle/docs/RUNBOOK.md` or relevant specs if operator behavior changed
5. if you moved an executable, verify both the canonical subfolder path and the legacy root shim path
