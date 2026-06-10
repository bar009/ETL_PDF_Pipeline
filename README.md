# Code Clean Start

Curated fresh-start repo for the PDF knowledge pipeline and the React V2 site shell.

The older workspace remains the archive. This repo is meant to contain source code, contracts,
small fixtures, tests, and active documentation only.

## What Is Here

- `PDF_handle/`: production ETL code, prompts, tests, and the minimum compatibility layer needed by `prod`
- `sites/work/react-v2-prototype/`: React UI pilot for the V2 shell
- `.agents/skills/`: canonical repo skills for Codex workflows
- `docs/`: enduring project docs, data contract, and operating rules
- `data/`: samples, schemas, and fixtures only

## What Is Not Here

- raw PDFs
- generated chunks, staging outputs, backups, and run evidence
- historical site roots
- old management waves and worktree prompts
- `node_modules`, build output, caches, and local test results

## Setup

```powershell
Copy-Item .env.example .env
```

Install frontend dependencies only if working on the React prototype:

```powershell
cd sites/work/react-v2-prototype
npm.cmd install
```

## Run The React Prototype

```powershell
cd sites/work/react-v2-prototype
npm.cmd run dev
```

## Run Checks

Frontend checks:

```powershell
cd sites/work/react-v2-prototype
npm.cmd run build
npm.cmd run verify:ui
```

Python checks:

```powershell
python -m pytest PDF_handle/tests
python PDF_handle/prod/check_import_boundaries.py
```

## Data Rule

Git is not the data warehouse. Keep only small samples, schemas, and fixtures in `data/`.
Large ETL inputs and generated outputs belong outside git, or in ignored output folders.

Read:

- `docs/RULES.md`
- `docs/DATA_CONTRACT.md`
- `MIGRATION_MANIFEST.md`
