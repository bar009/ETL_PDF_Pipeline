# React V2 Prototype Checkpoint - 2026-06-03

This checkpoint freezes the current React V2 prototype state before any real JSON adapter work begins.

## Scope

Prototype root:

- `sites/work/react-v2-prototype/`

Runtime data root protected from frontend mutation:

- `sites/work/v2.0/data/`

No existing runtime JSON files should be edited, formatted, normalized, patched, migrated, or auto-fixed as part of this checkpoint.

## Prototype Files Isolated

The prototype remains isolated from the active runtime site and ETL outputs:

- React source lives under `src/`
- prototype-only demo content lives under `src/data/demoContent.js`
- browser and contract tests live under `tests/`
- prototype planning docs live under `docs/`
- build output remains ignored in `dist/`
- dependencies remain under `node_modules/`

The current repo status shows `sites/work/react-v2-prototype/` as an untracked prototype folder. It should be staged as one coherent snapshot when the operator is ready.

## Data Boundary Confirmation

The checkpoint adds a no-mutation guard for `sites/work/v2.0/data`.

Guarded current files:

- `level1.json`
- `level2.json`
- `level3.json`
- `library.json`
- `degrees.json`
- `content.schema.json`
- `content.overrides.json`
- `content.localizations.he.json`
- `entry.template.json`
- `clean_rerun_seed_manifest.json`

Reserved absent files:

- `encyclopedia.json`
- `homepage_projection.json`

The absent files must not be introduced by frontend work before boundary review.

## Build And Verification

Latest checkpoint commands:

```powershell
npm.cmd run build
npm.cmd run verify:ui
```

Latest checkpoint result:

- `npm.cmd run build` passed.
- `npm.cmd run verify:ui` passed: `72 passed`, `4 skipped`.

## Clean Commit / Snapshot Preparation

Recommended snapshot scope:

```powershell
git status --short -- sites/work/react-v2-prototype sites/work/v2.0/data
git add sites/work/react-v2-prototype
git diff --cached --stat
```

Before committing, confirm:

- no files under `sites/work/v2.0/data/*.json` are staged
- no JSON files are staged except prototype package manifests if intentionally included
- `npm.cmd run build` passes
- `npm.cmd run verify:ui` passes

Suggested commit message:

```text
Add React V2 prototype checkpoint and JSON immutability guard
```

## Adapter Status

Adapter implementation is paused.

No real JSON integration, Next.js, auth, or deployment work starts from this checkpoint.
