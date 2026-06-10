# AGENTS.md

Guidance for human and AI contributors working in `PDF_handle/`.

## Purpose

`PDF_handle/` is the project root for the PDF knowledge pipeline.
The canonical Python code surface is `PDF_handle/prod/`.

## Read Order

Read these files before changing pipeline behavior:

1. `prod/README.md` — code homes, wrapper map, import guardrail
2. `docs/PROJECT_SCOPE.md`
3. `docs/ETL_FLOW.md`
4. `docs/DOMAIN_BOUNDARIES.md`
5. `docs/KNOWN_ISSUES.md`

When working on mapping or site mutations, also read:

1. `docs/JSON_SCHEMA_SPEC.md`
2. `docs/RELATION_RULES.md`
3. `../docs/DECISION_LOG.md`

## Source Of Truth

- Canonical pipeline logic lives under `prod/` (`prod/steps/`, `prod/cli/`, `prod/impl/`,
  `prod/core/`, `prod/providers/`, `prod/schema/`, `prod/exploration/`, `prod/external/`).
- Root-level `step_01..07.py`, `run_steps_05_07.py`, and the `TOOLS/runners/run_*.py`
  scripts are compatibility wrappers only. Their thinness is enforced by
  `tests/test_wrapper_thinness.py`.
- `pipeline_utils.py` and `stage5_utils.py` are historical/compat import surfaces;
  prod code must not import them (`prod/check_import_boundaries.py` enforces this).
- `TOOLS/` is the operations layer: wrappers, audits, validation, planning, reports —
  not product logic.
- `WORKFLOW.md` is the user-facing step overview; its `0.3` site-root references are
  historical (see Active Site Policy below).
- Repo-discovered canonical skills live in `../.agents/skills/`.

## Active Site Policy

- This repo contains no live site root. The old workspace's `0.3`, `sites/live/v0.4-current`,
  and `published_sites` roots were deliberately not migrated.
- Steps that touch a site root must receive an explicit `--site-root`, or resolve one through
  `sites/site_roots.json` (read by `prod/core/site_roots.py`).
- Do not hardcode new references to legacy roots.
- Re-baselining the legacy defaults inside `prod/core/site_roots.py` is planned Phase 2 work
  (`../docs/STRUCTURE_ROADMAP.md`).

## Engineering Rules

1. Preserve the split between `prod/` (product logic) and `TOOLS/` (operations).
2. Do not let audits silently mutate site JSON.
3. Keep staged outputs reviewable before live apply.
4. Treat `library`, `level1`, `level2`, and `preservation` as separate domains with explicit
   transfer rules.
5. Keep path changes and site-root changes documented in `../docs/DECISION_LOG.md`.
6. Prefer additive docs updates over rewriting historical notes unless asked.

## Verification Before Hand-Off

For doc-only work, check that links, paths, and commands still match the code.

For pipeline changes, verify at minimum:

1. `python -m unittest discover -s PDF_handle/tests` passes from the repo root
2. `python PDF_handle/prod/check_import_boundaries.py` passes
3. any new output path does not collide with committed data

If a full runtime validation is not performed, say so explicitly.
