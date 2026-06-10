# AGENTS.md

Guidance for human and AI contributors working in `PDF_handle/`.

## Purpose

`PDF_handle/` is the operational project root for the PDF knowledge pipeline.
The git root is currently one level above, but day-to-day pipeline work should treat `PDF_handle/` as the repo boundary.

## Read Order

Read these files before changing pipeline behavior:

1. `../management/CURRENT_PLAN.md`
2. `../management/RUN_QUEUE.md`
3. `../management/BACKLOG.md`
4. `../management/APPROVAL_LEVELS.md`
5. `docs/PROJECT_SCOPE.md`
6. `docs/ETL_FLOW.md`
7. `docs/DOMAIN_BOUNDARIES.md`
8. `docs/KNOWN_ISSUES.md`
9. `WORKFLOW.md`

When working on mapping or site mutations, also read:

1. `docs/JSON_SCHEMA_SPEC.md`
2. `docs/RELATION_RULES.md`
3. `docs/DECISION_LOG.md`

## Source Of Truth

- `../management/` is the active control surface for current operational state and approval boundaries.
- Canonical pipeline logic lives in `step_01_extract_pdfs.py` through `step_07_site_qa.py`.
- Shared path and IO helpers live in `pipeline_utils.py`.
- Step 5 and Step 6 merge behavior depend on `stage5_utils.py`.
- `TOOLS/` is the operations layer: wrappers, audits, validation, planning, reports.
- `WORKFLOW.md` is the user-facing process overview.
- repo-discovered canonical skills live in `../.agents/skills/`.
- `skills/` under `PDF_handle/` is draft/local-copy only unless explicitly promoted.

## Active Site Policy

- Current compatibility default is still workspace root `0.3`.
- New code should prefer explicit `--site-root` instead of relying on the default.
- Do not hardcode new references to `0.3` unless required for backward compatibility.
- The target model is one active live root and dated published snapshots.
- When `0.4` becomes active, the previous live root should become a frozen published or archived snapshot, not an ambiguous duplicate.

## Engineering Rules

1. Preserve the split between canonical pipeline steps and `TOOLS/`.
2. Do not let audits silently mutate site JSON.
3. Keep staged outputs reviewable before live apply.
4. Treat `library`, `level1`, `level2`, and `preservation` as separate domains with explicit transfer rules.
5. Keep path changes and site-root changes documented in `docs/DECISION_LOG.md`.
6. Prefer additive docs updates over rewriting historical notes unless asked.

## Non-Trivial Tasks

For any non-trivial pipeline task:

1. read `../management/CURRENT_PLAN.md`
2. read `../management/RUN_QUEUE.md` when the user wants continuous bounded follow-through
3. confirm the task fits `../management/APPROVAL_LEVELS.md`
4. if it is missing from `../management/BACKLOG.md` or conflicts with the current plan, stop and map it first

## Verification Before Hand-Off

For doc-only work, check that links, paths, and commands still match the code.

For pipeline changes, verify at minimum:

1. the changed script still parses
2. any path default still matches `pipeline_utils.py`
3. any new output path does not collide with live data unexpectedly

If a full runtime validation is not performed, say so explicitly.
