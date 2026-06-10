# PDF Pipeline Prod Surface

Status: active canonical Python surface

This directory is the production-facing Python path for the pipeline.

Its job is to give the repo one stable place for:

- canonical Python entrypoints
- orchestration ownership
- product-shaped step names
- separation between code, run evidence, and final site outputs

## Start Here

If you want the shortest path into the prod surface, read and run in this order:

1. `docs/STRUCTURE_ROADMAP.md` (repo root) — the current execution plan
2. `PDF_handle/docs/ETL_FLOW.md` — what the pipeline does end to end
3. `PDF_handle/prod/cli/e2e.py`
4. `PDF_handle/prod/cli/preprocess.py`
5. `PDF_handle/prod/cli/postmerge.py`
6. `PDF_handle/prod/cli/exploration_review.py`
7. `PDF_handle/docs/RUNBOOK.md` — operator procedures
8. `PDF_handle/docs/JSON_SCHEMA_SPEC.md` — the data shape contract

The prod-owned CLI modules are the preferred invocation path.
Legacy wrapper entrypoints still exist, but they are compatibility surfaces only.

Direct CLI examples:

```bash
python PDF_handle/prod/cli/e2e.py
python PDF_handle/prod/cli/preprocess.py
python PDF_handle/prod/cli/postmerge.py
python PDF_handle/prod/cli/exploration_review.py --staging-dir PDF_handle/staged_injection
python PDF_handle/prod/cli/postmerge.py --site-root <site-root> --skip-exploration-review
```

## Where New Code Goes

This table is the canonical code-homes note for new ETL work
(see `docs/STRUCTURE_ROADMAP.md`, Phase 1).

| You are adding...                         | It goes in...                                  |
|-------------------------------------------|------------------------------------------------|
| a new pipeline step entrypoint             | `PDF_handle/prod/steps/`                        |
| a new operator-facing CLI command          | `PDF_handle/prod/cli/`                          |
| multi-step orchestration logic             | `PDF_handle/prod/impl/`                         |
| a shared helper (paths, IO, text, runtime) | `PDF_handle/prod/core/`                         |
| an LLM provider or transport               | `PDF_handle/prod/providers/`                    |
| schema, validation, patch/merge semantics  | `PDF_handle/prod/schema/`                       |
| exploration/review-lane logic              | `PDF_handle/prod/exploration/`                  |
| a boundary to non-Python tooling           | `PDF_handle/prod/external/`                     |
| a test                                     | `PDF_handle/tests/` (stdlib `unittest`)         |
| a prompt template                          | `PDF_handle/prompts/`                           |
| pipeline documentation                     | `PDF_handle/docs/`                              |
| small fixtures, samples, schemas           | `data/fixtures/`, `data/samples/`, `data/schemas/` |

Do not add new logic to:

- root-level `PDF_handle/step_01..07.py` or `PDF_handle/run_steps_05_07.py` (compatibility wrappers)
- `PDF_handle/pipeline_utils.py` or `PDF_handle/stage5_utils.py` (historical/compat import surfaces)
- `PDF_handle/TOOLS/` (operational wrappers, audits, and reports — not product logic)
- new one-off scripts at the repo root

## What Lives Here

The orchestration owners:

- `PDF_handle/prod/cli/e2e.py`
- `PDF_handle/prod/cli/preprocess.py`
- `PDF_handle/prod/cli/postmerge.py`
- `PDF_handle/prod/cli/exploration_review.py`
- `PDF_handle/prod/cli/pre_2_0_go_no_go.py`

The concrete orchestration implementations:

- `PDF_handle/prod/impl/e2e_runner.py`
- `PDF_handle/prod/impl/preprocess_runner.py`
- `PDF_handle/prod/impl/postmerge_runner.py`

The product-shaped step entrypoints (Steps 1–7):

- `PDF_handle/prod/steps/extract.py`
- `PDF_handle/prod/steps/chunk.py`
- `PDF_handle/prod/steps/transform.py`
- `PDF_handle/prod/steps/consolidate.py`
- `PDF_handle/prod/steps/stage.py` (plus `stage_support.py`, `stage_mapping.py`)
- `PDF_handle/prod/steps/apply.py` (plus `apply_support.py`)
- `PDF_handle/prod/steps/qa.py`

The shared runtime helpers:

- `PDF_handle/prod/core/` — paths, IO, text, books, runtime, site roots, site data

The shared provider layer:

- `PDF_handle/prod/providers/gemini.py`

The schema-facing layer:

- `PDF_handle/prod/schema/` — degree data normalization/validation, patches, overrides, language integrity

The explicit external operational boundary:

- `PDF_handle/prod/external/js_lane.py` — the only sanctioned path from Python orchestration
  to the JS tools under `PDF_handle/TOOLS/`

Exploration lane note:

- `PDF_handle/prod/cli/exploration_review.py` is a production-owned semantic review lane
- `postmerge.py` and `e2e.py` invoke it automatically as a report-only sidecar after Step 5
  state is available; `--skip-exploration-review` disables it
- the sidecar does not mutate live site data

## Compatibility Wrappers

The historical entrypoints still exist, but they are compatibility wrappers only.
Each one delegates to a canonical prod module:

| Wrapper                                          | Canonical implementation              |
|--------------------------------------------------|----------------------------------------|
| `PDF_handle/step_01_extract_pdfs.py`              | `prod/steps/extract.py`                |
| `PDF_handle/step_02_chunk_markdown.py`            | `prod/steps/chunk.py`                  |
| `PDF_handle/step_03_transform_chunks.py`          | `prod/steps/transform.py`              |
| `PDF_handle/step_04_consolidate_books.py`         | `prod/steps/consolidate.py`            |
| `PDF_handle/step_05_map_and_stage.py`             | `prod/steps/stage.py`                  |
| `PDF_handle/step_06_apply_reviewed_merge.py`      | `prod/steps/apply.py`                  |
| `PDF_handle/step_07_site_qa.py`                   | `prod/steps/qa.py`                     |
| `PDF_handle/run_steps_05_07.py`                   | `prod/cli/postmerge.py`                |
| `PDF_handle/TOOLS/runners/run_preprocess_01_04.py`| `prod/cli/preprocess.py`               |
| `PDF_handle/TOOLS/runners/run_postmerge_05_07.py` | `prod/cli/postmerge.py`                |
| `PDF_handle/TOOLS/runners/run_new_material_e2e.py`| `prod/cli/e2e.py`                      |
| `PDF_handle/stage5_utils.py`                      | re-export shell over `prod/schema` and `prod/steps` |

Use wrappers only when an existing script or operator flow still points at them.
Wrapper thinness is enforced by `PDF_handle/tests/test_wrapper_thinness.py`:
a wrapper may set up `sys.path`, import its canonical prod module, and call `main()` —
nothing else.

Still outside prod, intentionally for now:

- `PDF_handle/pipeline_utils.py` — historical helper kept for non-prod lanes; prod does not import it
- `PDF_handle/workspace_paths.py` — historical path config helper; prod resolves site roots via
  `prod/core/site_roots.py` instead
- `PDF_handle/main.py` — marker/OCR environment shim used by extraction
- JS tools under `PDF_handle/TOOLS/` — invoked only through `prod/external/js_lane.py`

## Import Guardrail

Prod code must not import historical runtime helpers, legacy wrappers, or `TOOLS/` modules.
The policy and banned-module list live in `PDF_handle/prod/check_import_boundaries.py`.

Run the check:

```bash
python PDF_handle/prod/check_import_boundaries.py
```

The same check runs as part of the test suite (`PDF_handle/tests/test_import_boundaries.py`):

```bash
python -m unittest discover -s PDF_handle/tests
```

## Runs Versus Results

This production surface is intentionally separate from runtime data:

- `PDF_handle/runs/`, `PDF_handle/staged_injection/`, `PDF_handle/qa_reports/`, and the other
  generated ETL directories are execution evidence — all gitignored
- site roots are supplied explicitly via `--site-root` or configured in `sites/site_roots.json`
  (resolved by `prod/core/site_roots.py`)
- committed data is limited to `data/fixtures/`, `data/samples/`, and `data/schemas/`

Known re-baselining gap (Phase 2 work, see `docs/STRUCTURE_ROADMAP.md`):

- the fallback defaults in `prod/core/site_roots.py` still name legacy site roots from the old
  workspace (`sites/live/v0.4-current`, `0.3`, `published_sites`, ...) that do not exist in this
  repo; runs against a real site root must pass `--site-root` or provide `sites/site_roots.json`
  until those defaults are re-baselined
