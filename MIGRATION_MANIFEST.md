# Migration Manifest

## Keep First

- `AGENTS.md`
- `.agents/skills/`
- `.env.example`
- `docs/PROJECT_SCOPE.md`
- `docs/REPO_LAYOUT.md`
- `docs/DOMAIN_BOUNDARIES.md`
- `docs/DECISION_LOG.md`
- `docs/CODEX_GUIDANCE_HARDENING.md`
- `docs/RULES.md`
- `docs/DATA_CONTRACT.md`
- `PDF_handle/AGENTS.md`
- `PDF_handle/WORKFLOW.md`
- `PDF_handle/prod/`
- selected `PDF_handle/docs/`

## Keep If Frontend Scope Includes React Pilot

- `sites/work/react-v2-prototype/`
- exclude `sites/work/react-v2-prototype/public/data/*.json` unless the files are deliberately reduced to fixtures

## Keep Only As Data Contract Input If Needed

- selected files from `sites/work/v2.0/`
- small fixtures under `data/fixtures/`
- small samples under `data/samples/`
- schema files under `data/schemas/`

## Archive Only In Old Repo

- `management/*` except any small set explicitly re-baselined later
- `docs/releases/*`
- `docs/pipeline/CTL_*`
- `docs/ideas/*`
- `experiments/*`
- `PDF_handle/AUTOMATION_MIRROR/*`
- `PDF_handle/runs/*`
- historical site roots and snapshots

## Do Not Carry Into New Active Repo

- `PDF_handle/skills/`
- `CLAUDE.md`
- `output/`
- `test-results/`
- `published_sites/`
- `sandbox_sites/`
- `*.zip`
- generated ETL outputs and backups
- raw PDFs
- large JSON/JSONL exports
- local databases

## Structural Rules Adopted From The Fresh-Start Review

- code lives in source folders, not in output folders
- `data/` is only for samples, schemas, and fixtures
- staging JSON, canonical JSON, and site-consumed JSON are separate concepts
- ETL runs should be idempotent for the same inputs
- paths should be resolved from shared path/config helpers
- secrets live in `.env`, with only `.env.example` committed
- basic schema, uniqueness, and link validation tests should stay in the repo

## Pending Decision

Choose the active site/app scope for the new repo:

1. `PDF_handle/prod` only
2. `PDF_handle/prod` + `sites/work/react-v2-prototype`
3. `PDF_handle/prod` + React pilot + selected `v2.0` data contract files

Default migration assumption if no override is given:

- option `3`

Initial clean-start application:

- React prototype source is included
- large copied `public/data/*.json` files were removed
- `public/data/README.md` documents the expected runtime filenames

## Roadmap For The Next Pass

The structural execution plan now lives in:

- `docs/STRUCTURE_ROADMAP.md`

Use that document to decide the next refactor order before moving folders or changing ownership
again.
