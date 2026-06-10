# PDF Pipeline Prod Surface

Status: active canonical Python surface

This directory is the production-facing Python path for the current pipeline.

Its job is to give the repo one stable place for:

- canonical Python entrypoints
- orchestration ownership
- product-shaped step names
- separation between code, run evidence, and final site outputs

## Start Here

If you want the shortest path into the prod surface, read and run in this order:

1. `management/PYTHON_PIPELINE_LOGIC_V1.md`
2. `PDF_handle/prod/cli/e2e.py`
3. `PDF_handle/prod/cli/preprocess.py`
4. `PDF_handle/prod/cli/postmerge.py`
5. `PDF_handle/prod/cli/exploration_review.py`
6. `PDF_handle/prod/cli/pre_2_0_go_no_go.py`
7. `management/BATCH_EXECUTION_LOGIC_V1.md`
8. `management/JS_LANE_DECISION_V1.md`
9. `management/IMPORT_POLICY_V1.md`
10. `management/WRAPPER_RETIREMENT_PLAN_V1.md`

The prod-owned CLI modules are the preferred invocation path.
Legacy wrapper entrypoints still exist, but they are compatibility surfaces only.

Direct CLI examples:

```bash
python3.11 PDF_handle/prod/cli/e2e.py
python3.11 PDF_handle/prod/cli/preprocess.py
python3.11 PDF_handle/prod/cli/postmerge.py
python3.11 PDF_handle/prod/cli/exploration_review.py --staging-dir PDF_handle/staged_injection
python3.11 PDF_handle/prod/cli/postmerge.py --site-root sites/work/v0.4
python3.11 PDF_handle/prod/cli/postmerge.py --site-root sites/work/v0.4 --skip-exploration-review
python3.11 PDF_handle/prod/cli/pre_2_0_go_no_go.py --limited-summary PDF_handle/runs/v20r1/reports/limited_clean_rerun_validation_2026_04_22/limited_clean_20260422T160217Z/analysis/limited_clean_rerun_summary.json --strict
```

## What Lives Here

The orchestration owners now live here:

- `PDF_handle/prod/cli/e2e.py`
- `PDF_handle/prod/cli/preprocess.py`
- `PDF_handle/prod/cli/postmerge.py`
- `PDF_handle/prod/cli/exploration_review.py`
- `PDF_handle/prod/cli/pre_2_0_go_no_go.py`

Pre-rerun go/no-go note:

- `pre_2_0_go_no_go.py` is a read-only decision-support gate before expensive clean reruns.
- It consumes limited clean-rerun evidence, readiness reports, and optional browser QA reports.
- It writes `pre_2_0_go_no_go_report.json` and `pre_2_0_go_no_go_summary.md` under `PDF_handle/runs/pre_2_0_go_no_go/`.
- It does not call providers, run Step 6, mutate site roots, or publish content.
- Use `--strict` when an automation or operator script should stop on `no_go`.

Exploration lane adoption note:

- `PDF_handle/prod/cli/exploration_review.py` is a production-owned semantic review lane
- `PDF_handle/prod/cli/postmerge.py` now invokes it automatically as a report-only sidecar after Step 5 state is available
- `PDF_handle/prod/cli/e2e.py` inherits the same automatic sidecar behavior during postmerge phases
- `--skip-exploration-review` disables the sidecar for narrower runs
- the hook does not mutate live site data

The concrete orchestration implementations live here:

- `PDF_handle/prod/impl/e2e_runner.py`
- `PDF_handle/prod/impl/preprocess_runner.py`
- `PDF_handle/prod/impl/postmerge_runner.py`

The product-shaped step entrypoints live here:

- `PDF_handle/prod/steps/extract.py`
- `PDF_handle/prod/steps/chunk.py`
- `PDF_handle/prod/steps/transform.py`
- `PDF_handle/prod/steps/consolidate.py`
- `PDF_handle/prod/steps/stage.py`
- `PDF_handle/prod/steps/apply.py`
- `PDF_handle/prod/steps/qa.py`

The Step 5 stage-specific helper layer now lives here too:

- `PDF_handle/prod/steps/stage_support.py`
- `PDF_handle/prod/steps/stage_mapping.py`
- `PDF_handle/prod/steps/apply_support.py`

The shared runtime helpers now live here:

- `PDF_handle/prod/core/paths.py`
- `PDF_handle/prod/core/io.py`
- `PDF_handle/prod/core/text.py`
- `PDF_handle/prod/core/books.py`
- `PDF_handle/prod/core/runtime.py`
- `PDF_handle/prod/core/site_roots.py`
- `PDF_handle/prod/core/site_data.py`

The shared provider layer now starts here:

- `PDF_handle/prod/providers/gemini.py`

The schema-facing patch/merge layer now starts here:

- `PDF_handle/prod/schema/patches.py`
- `PDF_handle/prod/schema/overrides.py`

The explicit external operational boundary now lives here:

- `PDF_handle/prod/external/js_lane.py`
- boundary decision note:
  - `management/JS_LANE_DECISION_V1.md`

Current migration state:

- `Steps 1-7` now execute from the prod step modules directly
- `prod/core` now owns site-root resolution, run/report helpers, JSON IO, and site-data fingerprint helpers
- `prod/providers` now owns the shared Gemini transport used by `transform` and `stage`
- `prod/providers` now also owns shared Gemini text/json response handling, while intentionally step-local prompt/report semantics stay with the step
- `prod/external/js_lane.py` now owns the JS smoke/publish/finalize boundary used by the Python E2E runner
- `PDF_handle/stage5_utils.py` is now a compatibility re-export shell over `prod`, not a canonical owner of logic
- `prod/schema` now owns the shared patch/provenance plus degree normalization/serialization/validation semantics used by `stage`, `apply`, and `qa`
- `prod/schema/overrides.py` now owns canonical override normalization, identity resolution, field-level drift detection, and promotion-decision application for `content.overrides.json`
- `prod/steps/stage_support.py` now owns section extraction, lexical matching, preservation checks, and staged book/chapter helper behavior for Step 5
- `prod/steps/stage_mapping.py` now owns the Step 5 mapping prompt/schema/coercion contract used around Gemini calls
- the prod package no longer imports `pipeline_utils.py` directly
- the remaining cleanup work is mostly wrapper retirement and non-prod lane governance, not step-entrypoint ownership

## What Still Remains Outside Prod

The Python production surface is now real, but a few non-canonical slices still sit outside it:

- `PDF_handle/pipeline_utils.py`
  - no longer feeds the prod package directly, but still exists as a historical helper dependency for non-prod lanes and compat surfaces
- `PDF_handle/stage5_utils.py`
  - now exists mainly as a compatibility import surface for non-prod tools and mirrors
- JS publish/finalize/smoke tools under `PDF_handle/TOOLS/`
  - still sit outside the Python prod package, but they are now invoked through one explicit boundary module under `prod/external/`

Intentional step-local logic still remains inline where that is clearer:

- Transform prompt construction and chunk-level retry handling
- Apply report summarization that is specific to Step 6 outputs
- QA reporting logic that is specific to QA evidence shape

That means the repo is now in this state:

- `prod` owns the canonical Python control surface and runtime helpers
- `content.overrides.json` is the canonical curated layer above generated site data for a selected site root
- legacy wrappers remain compatibility only
- some deep step helpers and JS release lanes still need later migration or explicit long-term boundaries

## What Is Still Compatibility Only

The historical entrypoints still exist, but they are now compatibility wrappers:

- `PDF_handle/TOOLS/runners/run_new_material_e2e.py`
- `PDF_handle/TOOLS/runners/run_preprocess_01_04.py`
- `PDF_handle/TOOLS/runners/run_postmerge_05_07.py`
- `PDF_handle/run_steps_05_07.py`
- `PDF_handle/step_01_extract_pdfs.py`
- `PDF_handle/step_02_chunk_markdown.py`
- `PDF_handle/step_03_transform_chunks.py`
- `PDF_handle/step_04_consolidate_books.py`
- `PDF_handle/step_05_map_and_stage.py`
- `PDF_handle/step_06_apply_reviewed_merge.py`
- `PDF_handle/step_07_site_qa.py`

Use those only when an existing script or operator flow still points at them.

The current wrapper classification note lives here:

- `management/WRAPPER_CLASSIFICATION_V1.md`
- `management/TOOLS_CLASSIFICATION_V1.md`
- `management/AUTOMATION_MIRROR_MIGRATION_MAP.md`
- `management/WRAPPER_RETIREMENT_PLAN_V1.md`

## Import Guardrail

Prod code should not import historical runtime helpers, mirror code, or `TOOLS/`
modules directly.

Run the import-boundary check here:

- `python PDF_handle/prod/check_import_boundaries.py`

For new Python-facing documentation and future cleanup work, start from `PDF_handle/prod/`.

## Runs Versus Results

This production surface is intentionally separate from:

- `PDF_handle/runs/`
  - retry logs, manifests, attempt folders, batch evidence
- `sites/live/v0.4-current/`
  - the current live dataset consumed by the site
- `published_sites/`
  - finalized release snapshots

That split is the intended operating model:

- `prod` = canonical code surface
- `runs` = execution evidence
- `live` = site-consumed data
- `published_sites` = release outputs
