# ETL Flow

## Canonical Flow

The canonical pipeline is:

1. `step_01_extract_pdfs.py`
2. `step_02_chunk_markdown.py`
3. `step_03_transform_chunks.py`
4. `step_04_consolidate_books.py`
5. `step_05_map_and_stage.py`
6. `step_06_apply_reviewed_merge.py`
7. `step_07_site_qa.py`

## Layer Responsibilities

- Steps 1 to 4 build source-derived working material.
- Step 5 creates staged candidate data and review artifacts, including the canonical optional `level3` lane when a selected site root carries `data/level3.json` and `degrees.json` declares it.
- Step 6 merges reviewed staged data into a selected site root, including optional `level3` approvals and previews when the same declared lane exists in both the selected root and the staging artifacts.
- Step 7 validates the resulting site data, including optional `level3` whenever the selected root declares that lane, and now also checks that the declared `degrees.json` access contract stays aligned with the adopted `level3` runtime policy.
- `TOOLS/` wraps, audits, validates, or plans around the canonical flow. It does not replace it.
- `prod/cli/exploration_review.py` is an additive review lane that now runs automatically inside the prod postmerge/e2e orchestration after Step 5 and before Step 6, producing typed semantic exploration artifacts under `PDF_handle/runs/` only.

## Common Operator Routes

### Full preprocess

Use when starting from new PDFs.

```bash
python3.11 PDF_handle/TOOLS/run_preprocess_01_04.py --book "<book>"
```

### Post-merge route

Use when consolidated books already exist.

```bash
python3.11 PDF_handle/TOOLS/run_postmerge_05_07.py --site-root 0.3
```

### Audit route

Use after merge to inspect sparse coverage or boundary quality.

```bash
python3.11 PDF_handle/TOOLS/audit_sparse_entries.py --site-root 0.3
python3.11 PDF_handle/TOOLS/audit_degree_classification.py --site-root 0.3 --degrees level1
python3.11 PDF_handle/TOOLS/audit_knowledge_flow.py --site-root 0.3 --manifest PDF_handle/TOOLS/knowledge_flow_waves/level1.phase1-plus-phase2.json
```

## Mutation Rules

- Steps 1 to 5 should not write directly into live site JSON.
- Step 6 is the review gate for live mutation.
- `content_apply_engine.py` is a preservation/apply layer on top of reviewed routing output and must stay explicit about mode.
- Audit scripts are diagnostic unless their contract clearly says otherwise.

## Live Root And Release Model

Current compatibility rule:

- many scripts still fall back to `0.3`, but `pipeline_utils.DEFAULT_SITE_ROOT` now resolves through `sites/site_roots.json` first

Future release rule:

1. choose one live site root
2. run sandboxes against copies, not the live root
3. publish release snapshots into a dedicated published area
4. when moving from `0.3` to `0.4`, freeze the old live root as a dated published or archived snapshot
5. the `v0.4` live/work roots are now bootstrapped and should be treated as the canonical targets for ongoing structural work
6. do not let both old and new roots look equally "active"

The long-term target is a config-driven live-root selector instead of hardcoded numeric defaults.

## `level3` Status

- The data-lifecycle contract for `level3` is now adopted: it is a canonical optional lane when a selected site root carries `data/level3.json` and `degrees.json` declares it.
- Step 5, Step 6, Step 7, and release packaging should only handle `level3` through that declared-lane contract rather than through a side mutation path.
- `degrees.json` and `level3.json` are expected to stay in sync, and declaration/file mismatches are contract issues.
- Browser QA and site runtime now have a working `level3` path, and Step 7 data QA also validates the declared `degrees.json` access contract for that lane, but scope-expansion decisions remain a separate follow-on question.
