# Repo Layout

This document describes the layout of this repo so new work lands in predictable places.
The active execution plan is `docs/STRUCTURE_ROADMAP.md`; this file is the layout reference.

The old workspace's layout and migration plan (numeric site roots, `management/`,
`paperclip`, the `TOOLS/` split proposal) stayed in the old repo. This repo starts from the
already-migrated shape.

## Top-Level Layout

```text
code-clean-start/
  AGENTS.md                 repo navigation for human and AI contributors
  README.md                 default local setup path
  MIGRATION_MANIFEST.md     what was migrated from the old repo, and what was not
  .env.example              the only committed secret/config template
  .agents/
    skills/                 canonical repo-discovered skill home
  data/
    fixtures/               small committed fixtures representing each data state
    samples/                representative sample data
    schemas/                JSON schemas and data contracts
  docs/                     enduring policy, contracts, decision log, roadmap
  PDF_handle/               the PDF knowledge pipeline (see below)
  sites/
    work/
      react-v2-prototype/   the front-end pilot
```

## `PDF_handle/` Layout

```text
PDF_handle/
  prod/                     canonical Python ETL surface — all new ETL logic goes here
    cli/                    operator-facing CLI commands
    impl/                   multi-step orchestration runners
    steps/                  Step 1–7 entrypoints and step-local helpers
    core/                   shared runtime helpers (paths, IO, text, site roots)
    providers/              LLM provider transports
    schema/                 normalization, validation, patch/merge semantics
    exploration/            semantic review lane
    external/               sanctioned boundary to non-Python tooling
    check_import_boundaries.py
    README.md               code homes, wrapper map, import guardrail
  tests/                    stdlib unittest suite (run from repo root)
  prompts/                  prompt templates
  docs/                     pipeline documentation
  run_definitions/          run definition JSON for the E2E CLI
  TOOLS/                    operational wrappers, audits, validation, specs — not product logic
  step_01..07.py            compatibility wrappers over prod (thinness enforced by tests)
  run_steps_05_07.py        compatibility wrapper over prod/cli/postmerge.py
  pipeline_utils.py         historical helper; prod must not import it
  stage5_utils.py           compat re-export shell over prod
  main.py                   marker/OCR environment shim
  WORKFLOW.md               user-facing step overview (historical site-root references)
```

The full code-homes table for new ETL work lives in `PDF_handle/prod/README.md`
("Where New Code Goes").

## Data States

Folder names should make the data state obvious (`docs/STRUCTURE_ROADMAP.md`, Phase 2):

- **source** — input PDFs; never committed
- **staging** — review material (`PDF_handle/staged_injection/`, ...); generated, gitignored
- **canonical** — approved content; not yet present in this repo
- **runtime** — site-consumed export; supplied via `--site-root` or `sites/site_roots.json`
- **evidence** — run reports and QA output (`PDF_handle/runs/`, `PDF_handle/qa_reports/`, ...);
  generated, gitignored

Committed data is limited to `data/fixtures/`, `data/samples/`, and `data/schemas/`.

## Naming Rules

- top-level folder names describe a function, not a version
- no new top-level numeric folders
- generated output never lives beside source code
- if a folder is temporary, its name should say so
- prefer lowercase descriptive names for new folders
