# Checks

The local check list for this repo. A clean checkout must pass all of these without private
data. CI (Phase 6 of `docs/STRUCTURE_ROADMAP.md`) runs the same commands — keep this file
and the workflow in sync.

## Python (run from the repo root)

```powershell
python -m compileall -q PDF_handle/prod PDF_handle/tests
python PDF_handle/prod/check_import_boundaries.py
python -m unittest discover -s PDF_handle/tests
python PDF_handle/prod/cli/smoke_fixture.py
```

`smoke_fixture.py` is the offline ETL smoke: it copies the runtime fixture to a temp site
root, applies the staged fixture patch through the real merge layer, checks idempotency and
provenance, validates the merged result, and round-trips it through the atomic writer. No
PDFs, no providers, no network.

The unittest suite includes:

- import-boundary enforcement (`test_import_boundaries.py`)
- wrapper thinness and re-export shell purity (`test_wrapper_thinness.py`)
- data-state contracts over the committed fixtures (`test_data_state_contracts.py`)
- `--help` smoke checks for every prod CLI and step wrapper (`test_cli_smoke.py`)
- merge idempotency, atomic IO, postmerge skip-detection regression guards

## React pilot

```powershell
cd sites/work/react-v2-prototype
npm.cmd ci
npm.cmd run build
npm.cmd test
```

`npm test` includes the adapter boundary tests (missing fields, unknown routes, locale
direction, relation references).

## Ignore rules

```powershell
git check-ignore .env data/raw/input.pdf data/generated/out.json outputs/result.json
```

All four paths must be reported as ignored.
