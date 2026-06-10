# API Audit Table

Snapshot date: 2026-03-17

This table is the working inventory for active provider-facing code paths.

Scope notes:

* Includes current canonical scripts and active `TOOLS` entrypoints that call, configure, or orchestrate provider-backed jobs.
* Excludes `AUTOMATION_MIRROR/` duplicates so the table does not double-count mirrored code.
* Thin wrappers that only delegate to an inventoried runner are omitted unless they add their own manifest/state behavior.

## Readiness Rubric

* `8-10`: pilot-ready under the new spec, with limited hardening still pending.
* `5-7`: operational, but missing one or more required hardening layers.
* `0-4`: legacy or partial implementation that should not be treated as hardened.

## Current Inventory

| File | Purpose | Provider | Unit type | Main outputs | Schema versioning | Run manifest | Idempotency policy | Shared runtime boundary | Resume support | Hash basis coverage | Retry / stop handling | Interruption handling | Atomic writes | Summary completeness | Provenance completeness | Runtime validated | Readiness | Action needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `PDF_handle/step_03_transform_chunks.py` | Step 3 chunk transformation | Gemini / dry-run | Book chunk | `chunks/*.md`, `records/*.json`, `manifest.json` | No | No | Low; file-exists skip plus `--force`, but no explicit compatible-rerun contract | No | No; skips by file existence | Partial; prompt hashes recorded per chunk, but skip logic is not hash-aware | Partial; generic retries and sleep, no normalized runtime classes | No explicit `interrupted` state | No | Low | Medium | Operational legacy path, not yet against the matrix | 4/10 | Replace file-exists skipping with state/hash-based resume, add explicit schema versions and run manifest, then move provider logic into the shared runtime layer |
| `PDF_handle/step_05_map_and_stage.py` | Step 5 mapping and staging | Gemini / heuristic | Work section within a staged work | `work_manifest.generated.json`, `run_status.json`, patch/candidate previews | No | No; has manifest-like staged artifacts, but not a dedicated run manifest contract | Partial; `--resume` exists but rerun compatibility is only partially defined | No | Partial; `--resume` exists but is staged-work scoped | Low; no prompt/content/provider basis invalidation | Medium; retries plus 429/503 handling exist | Medium; interrupted run status exists | No | Medium | Low | Operational legacy path, not yet against the matrix | 6/10 | Add explicit schema versions, a dedicated run manifest, full rerun compatibility rules, row provenance, atomic writes, and shared provider runtime extraction |
| `PDF_handle/TOOLS/targeted_refill_from_audit.py` | Targeted refill generation from audit queues | Gemini / heuristic | Audit target entry | `refill_manifest.json`, `run_status.json`, patch/candidate files, source packets | No | Partial; manifest-like artifacts exist, but no dedicated `run_manifest.json` | Partial; resume loads staged artifacts, but compatible/incompatible reruns are not formalized | No | Partial; resume loads staged artifacts, not basis-aware unit completion | Low; prompt/provider config is not part of resume invalidation | Medium; retries plus 429/503 classification and stop behavior | Medium; interrupted summary exists in `run_status.json` | No | Medium | Medium | Used in loop runs, but not yet validated against the new matrix | 6/10 | Add schema versions, a dedicated run manifest, formal rerun rules, basis hashes, atomic writes, and shared runtime handling |
| `PDF_handle/TOOLS/run_targeted_refill_loop.py` | Batch orchestrator for repeated audit -> refill cycles | Delegates to child jobs | Batch cycle | `run_manifest.json`, `latest.json`, batch/audit directories | No | Yes | Partial; loop-level rerun behavior exists, but child compatibility is delegated | Delegated | Loop continuation only; no per-unit resume | Low / orchestration only | Medium; stops cleanly when child run is interrupted | Medium; loop manifest reflects interrupted child runs | No | Medium | Medium | Operationally used, but not matrix-validated as an orchestrator | 6/10 | Add explicit schema versions for manifests, align rerun policy wording, and switch manifest writes to atomic helpers |
| `PDF_handle/TOOLS/semantic_system_purity_review.py` | F2 paragraph-level semantic purity review | Gemini / heuristic | `review_unit_id` paragraph | `semantic_purity_summary.json`, entries, findings, failure log, resume state, reports | No; basis metadata exists, but explicit state/summary/row schema versions do not | No | Partial; `--resume` plus basis checks exist, but same-report-dir rerun rules are not yet fully formalized | No | Yes; success-only skipping with resume state | Medium-high; site root, manifest, wave, provider, model, prompt hash are enforced | High; retries plus 429/503 plus max-runtime stop | High; `interrupted` is first-class | No | Medium | Medium | Heuristic smoke plus resume-path smoke done; full live matrix still pending | 8/10 | Add explicit schema versions, `run_manifest.json`, formal rerun/idempotency rules, atomic writes, then extract shared runtime and enrich summary/row provenance |
| `PDF_handle/TOOLS/content_routing_review.py` | F3 routing and preservation review | Gemini / heuristic | Routed F2 review unit | `content_routing_summary.json`, entries, findings, queues, failure log, resume state, reports | No; basis metadata exists, but explicit state/summary/row schema versions do not | No | Partial; `--resume` plus basis checks exist, but same-report-dir rerun rules are not yet fully formalized | No | Yes; success-only skipping with resume state | Medium-high; prompt/taxonomy/provider/model basis is enforced | High; retries plus 429/503 plus max-runtime stop | High; `interrupted` is first-class | No | Medium | Medium | Syntax-checked; live runtime matrix still pending | 8/10 | Add explicit schema versions, `run_manifest.json`, formal rerun/idempotency rules, atomic writes, then extract shared runtime and enrich summary/row provenance |
| `PDF_handle/TOOLS/run_preprocess_01_04.py` | Wrapper for Steps 1-4 | Delegates to Step 3 | Pipeline step run | `run_manifest.json` | No | Yes | Partial; wrapper has force flags, but no formal compatible-rerun contract | Delegated | No | Low / wrapper only | Delegated to child steps | Low; failed vs completed only | No | Low | Low | Wrapper in use, not hardened as a long-running resumable job | 5/10 | Keep it as a thin wrapper, but add explicit schema versions to manifests and clarify rerun compatibility at the wrapper boundary |
| `PDF_handle/run_steps_05_07.py` | Unified Steps 5-7 runner | Delegates to Step 5 and downstream steps | Work-level pipeline run | `pipeline_run_manifest.json`, `latest.json`, staged/run metadata | No | Yes | Partial; can resume child Step 5 state, but provider-basis compatibility is not first-class | Delegated | Partial; can resume child Step 5 state when available | Low-medium; QA freshness fingerprints exist, but provider basis is not first-class | Delegated for provider calls; orchestrator logic is solid | Medium; work and pipeline status are explicit | No | Medium | Medium | Operational runner, but not yet aligned to the new spec | 6/10 | Add explicit schema versions to manifests, formalize rerun compatibility across child state, and convert manifests to atomic writes |

## Immediate Priority Order

1. Keep [API_RELIABILITY_PROVIDER_RUNTIME_SPEC.md](./API_RELIABILITY_PROVIDER_RUNTIME_SPEC.md) as the source of truth.
2. Use this table to track missing hardening per file.
3. Add explicit schema versions, `run_manifest.json`, and rerun/idempotency rules to the active jobs.
4. Add atomic write helpers in `PDF_handle/pipeline_utils.py`.
5. Extract a shared provider runtime boundary.
6. Connect F2/F3 to that boundary.
7. Expand summary and provenance after the runtime metadata comes from the right place.
8. Run the validation matrix before any wider pilot.

## Notes

* `PDF_handle/TOOLS/run_postmerge_05_07.py` is intentionally omitted from the table because it is a thin delegation wrapper around `PDF_handle/run_steps_05_07.py` and adds no independent state model.
* `PDF_handle/content_apply_engine.py` and other non-provider scripts are out of scope for this table unless they begin calling an external provider in the future.
