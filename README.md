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

The canonical check list lives in `docs/CHECKS.md`. Quick version, from the repo root:

```powershell
python -m compileall -q PDF_handle/prod PDF_handle/tests
python PDF_handle/prod/check_import_boundaries.py
python -m unittest discover -s PDF_handle/tests
```

The test suite uses stdlib `unittest` — no pytest required.

Frontend checks:

```powershell
cd sites/work/react-v2-prototype
npm.cmd run build
npm.cmd test
```

CI (`.github/workflows/checks.yml`) runs the same commands on every pull request.

## Branch Hygiene

- `main` is the clean source of truth; work lands through pull requests
- protect `main` on GitHub: require the `checks` workflow to pass before merging,
  and disallow force pushes
- one phase or one path family per branch, small enough to review from `git diff --stat`

## New Work Checklist

1. Read `docs/STRUCTURE_ROADMAP.md` and confirm the change fits the active phase.
2. Find the code home first: `PDF_handle/prod/README.md` ("Where New Code Goes") for ETL,
   `src/lib/` adapters for the React pilot.
3. No new logic in compatibility wrappers, `TOOLS/`, or repo-root scripts.
4. Keep generated data out of git; committed data only under `data/`.
5. Run the checks above before pushing.
6. Record lasting path/ownership decisions in `docs/DECISION_LOG.md`.

## Data Rule

Git is not the data warehouse. Keep only small samples, schemas, and fixtures in `data/`.
Large ETL inputs and generated outputs belong outside git, or in ignored output folders.

Read:

- `docs/RULES.md`
- `docs/DATA_CONTRACT.md`
- `docs/STRUCTURE_ROADMAP.md`
- `MIGRATION_MANIFEST.md`
