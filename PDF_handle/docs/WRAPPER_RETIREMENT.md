# Wrapper Retirement Plan

Every retained compatibility path has a named reason to exist; everything else gets
deleted with its replacement documented here (systemic plan WS11). Status as of
2026-06-11.

## Keep — operator entrypoints (deprecated in favor of prod CLIs)

| Path | Replacement | Reason kept |
|------|-------------|-------------|
| `PDF_handle/step_01..07.py` | `prod/steps/*.py` (same flags) | operator muscle memory; docs and old scripts still name them |
| `PDF_handle/run_steps_05_07.py` | `prod/cli/postmerge.py` | same |
| `PDF_handle/TOOLS/runners/run_preprocess_01_04.py` | `prod/cli/preprocess.py` | same |
| `PDF_handle/TOOLS/runners/run_postmerge_05_07.py` | `prod/cli/postmerge.py` | same |
| `PDF_handle/TOOLS/runners/run_new_material_e2e.py` | `prod/cli/e2e.py` | same |

Thinness is enforced by `tests/test_wrapper_thinness.py`; `--help` health by
`tests/test_cli_smoke.py`. Use the prod CLI in anything new.

## Keep — re-export shells (import-compat only)

| Path | Canonical owner |
|------|-----------------|
| `PDF_handle/stage5_utils.py` | `prod/schema`, `prod/steps` |
| `PDF_handle/pipeline_utils.py` | `prod/core` |
| `PDF_handle/workspace_paths.py` | `prod/core/site_roots`, `prod/core/paths` |

Purity enforced by `tests/test_wrapper_thinness.py`. Delete only after the remaining
`TOOLS/` Python importers are migrated or retired.

## Deleted — one-shot scripts pinned to old-workspace runs (WS11)

| Path | Why deleted |
|------|-------------|
| `prod/cli/degree_root_preview.py` | hardcoded `sites/work/v0.5` job; executed in the old repo; crashed on any invocation here |
| `prod/cli/degree_root_write.py` | same |
| `prod/cli/e1_new_sources_apply_review.py` | pinned to `runs/v21r1-e1-new-sources-2026-04-24` evidence that only exists in the old repo |
| `prod/cli/e2_apply_review_rules.py` | same family |
| `prod/cli/e2_new_sources_apply_review.py` | same family |

No replacement command exists or is needed — their jobs were completed in the old
workspace. The old repo retains the source if it is ever needed for archaeology.

## Deprecated — broken until fixed or retired

| Path | Problem |
|------|---------|
| `TOOLS/validation/validate_level1_boundary_goldset.py` (and siblings importing `common`) | imports `common` from its pre-migration location instead of `TOOLS/lib/common.py` |
| other `TOOLS/` Python lanes | require a configured site root; fail fast by design since WS3 |

Decide per script when first needed again: fix the import (one line) or delete with a note
here. Do not fix speculatively.
