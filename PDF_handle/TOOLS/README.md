# PDF_handle/TOOLS

`TOOLS` is the maintenance and entrypoint hub for the PDF knowledge pipeline.

## Current Layout

Canonical implementations are now split by role:

- `PDF_handle/TOOLS/runners/`
- `PDF_handle/TOOLS/audits/`
- `PDF_handle/TOOLS/validation/`
- `PDF_handle/TOOLS/apply/`
- `PDF_handle/TOOLS/lib/`
- `PDF_handle/TOOLS/specs/`

Legacy root-level script paths are kept as compatibility shims so existing commands do not break immediately.

Root-level executable files should now be treated as transition wrappers unless they are shared helper modules.

## Source of Truth

- `PDF_handle/step_01_extract_pdfs.py` .. `PDF_handle/step_07_site_qa.py`
  - canonical pipeline logic
- `PDF_handle/TOOLS/*`
  - wrappers, audits, manifests, and operational reports
- `PDF_handle/TOOLS/specs/API_RELIABILITY_PROVIDER_RUNTIME_SPEC.md`
  - source of truth for provider-facing reliability, resume, interruption, summary, provenance, and runtime-boundary rules
- `PDF_handle/TOOLS/specs/API_AUDIT_TABLE.md`
  - active inventory of provider-facing scripts and their current hardening gaps
- `PDF_handle/TOOLS/specs/PHASE_H1_SCHEMA_CONTRACTION_REPAIR_HARDENING.md`
  - focused structured-output hardening spec for shrinking F2/F3 provider schemas and removing over-aggressive repair before calibration
- `PDF_handle/TOOLS/specs/PHASE_I1_I2_F2_GATING_CALIBRATION.md`
  - source of truth for Hebrew-aware F2 gating calibration, mixed-content handling, separated leakage axes, and reason-code observability
- `PDF_handle/TOOLS/specs/DEGREE_SIGNAL_REGISTRY_STEP1_SPEC.md`
  - source of truth for the Step 1 degree-aware signal registry infrastructure, F2-only integration, and degree-based observability
- `PDF_handle/TOOLS/lib/site_roots.js`
  - shared JS resolver for `sites/site_roots.json`, used by the main smoke, discovery, publish, level3-build, and finalize scripts

`TOOLS` does not replace the step scripts. It organizes and orchestrates them.

## Main Tools

### `run_preprocess_01_04.py`

Wrapper for Steps `1 -> 4`.

Use it when you have a new source PDF and want one entrypoint for:
- extraction
- chunking
- chunk transformation
- consolidation

Example:

```bash
python3.11 PDF_handle/TOOLS/run_preprocess_01_04.py --book "commentary_on_the_second_Degree" --provider gemini --model gemini-2.5-flash
```

### `run_postmerge_05_07.py`

Wrapper for the existing unified runner of Steps `5 -> 7`.

Use it when Steps `1 -> 4` are already done and you want:
- staged mapping
- reviewed merge to a selected site root
- final QA

Example:

```bash
python3.11 PDF_handle/TOOLS/run_postmerge_05_07.py --site-root 0.3
```

### `audit_sparse_entries.py`

Read-only coverage audit for:
- `level1`
- `level2`
- `library` as the evidence layer

It identifies sparse entries, explains why they stayed sparse, and creates a ranked refill queue from existing library material.

Example:

```bash
python3.11 PDF_handle/TOOLS/audit_sparse_entries.py --site-root 0.3
```

### `audit_degree_classification.py`

Read-only audit for the new degree-classification model.

It checks:
- `knowledge_type`
- `content_scope`
- `reading_layers`
- cross-degree leakage into `level1`
- ritual entries that incorrectly span multiple degrees

With `--system-purity`, it also checks:
- rite / system-family purity for `level1`
- framed vs unframed foreign-system material in `reading_layers.advanced`
- `symbolic_meaning` and `candidate_lesson` for foreign-system contamination
- preservation guidance such as `keep_here_framed` vs `move_to_library_or_research`

Use `--manifest` to audit only a migrated subset, such as the combined Wave 1 + Wave 2 core block.

Phase F1 policy is documented in:
- `PDF_handle/TOOLS/specs/PHASE_F1_RITE_SYSTEM_PURITY.md`

Example:

```bash
python3.11 PDF_handle/TOOLS/audit_degree_classification.py --site-root 0.3 --degrees level1
```

Subset example:

```bash
python3.11 PDF_handle/TOOLS/audit_degree_classification.py --site-root 0.3 --manifest PDF_handle/TOOLS/knowledge_flow_waves/level1.phase1-plus-phase2.json
```

System-purity subset example:

```bash
python3.11 PDF_handle/TOOLS/audit_degree_classification.py --site-root 0.3 --manifest PDF_handle/TOOLS/knowledge_flow_waves/level1.phase1-plus-phase2.json --system-purity
```

### `semantic_system_purity_review.py`

Read-only paragraph-level semantic review layered on top of the F1 system-purity baseline.

  It:
  - validates a `level1` subset manifest
  - runs embedded F1 into `f1_baseline/`
  - reviews paragraph units across the teaching fields
  - records lexical overlay, semantic verdict, final verdict, and decision source
  - supports `--provider-policy heuristic_only|provider_all|provider_uncertain_only` with `provider_uncertain_only` as the Gemini default
  - never mutates site JSON files

Phase F2 policy is documented in:
- `PDF_handle/TOOLS/specs/PHASE_F2_SEMANTIC_SYSTEM_PURITY.md`

Heuristic smoke example:

```bash
python3.11 PDF_handle/TOOLS/semantic_system_purity_review.py --site-root 0.3 --provider heuristic
```

Subset Gemini example:

```bash
python3.11 PDF_handle/TOOLS/semantic_system_purity_review.py --site-root 0.3 --slug cable-tow --provider gemini --model gemini-2.5-flash
```

Windowed run example:

```bash
python3.11 PDF_handle/TOOLS/semantic_system_purity_review.py --site-root 0.3 --slug cable-tow --provider gemini --model gemini-2.5-flash --report-dir PDF_handle/TOOLS/reports/semantic_system_purity_review/0.3/cable-tow-resume --max-runtime-seconds 1800
```

Resume rerun example:

```bash
python3.11 PDF_handle/TOOLS/semantic_system_purity_review.py --site-root 0.3 --slug cable-tow --provider gemini --model gemini-2.5-flash --report-dir PDF_handle/TOOLS/reports/semantic_system_purity_review/0.3/cable-tow-resume --resume
```

Degree signal registry Step 1 regression example:

```bash
python3.11 PDF_handle/TOOLS/validate_degree_signal_registry_step1.py
```

### `content_routing_review.py`

Read-only routing and preservation planning layered on top of an existing F2 report.

  It:
  - consumes `semantic_purity_*` artifacts from an existing F2 run
  - routes flagged review units to keep-here-framed, existing-entry, library, future-entry-candidate, or drop
  - records `routing_unit_status` and `taxonomy_match_reason`
  - supports `--provider-policy heuristic_only|provider_all|provider_uncertain_only` with `provider_uncertain_only` as the Gemini default
  - never mutates site JSON files

Phase F3 policy is documented in:
- `PDF_handle/TOOLS/specs/PHASE_F3_CONTENT_ROUTING.md`

Heuristic example:

```bash
python3.11 PDF_handle/TOOLS/content_routing_review.py --f2-report-dir PDF_handle/TOOLS/reports/semantic_system_purity_review/0.3/<timestamp> --provider heuristic
```

Subset Gemini example:

```bash
python3.11 PDF_handle/TOOLS/content_routing_review.py --f2-report-dir PDF_handle/TOOLS/reports/semantic_system_purity_review/0.3/<timestamp> --slug cable-tow --provider gemini --model gemini-2.5-flash
```

Windowed run example:

```bash
python3.11 PDF_handle/TOOLS/content_routing_review.py --f2-report-dir PDF_handle/TOOLS/reports/semantic_system_purity_review/0.3/<timestamp> --slug cable-tow --provider gemini --model gemini-2.5-flash --report-dir PDF_handle/TOOLS/reports/content_routing_review/0.3/cable-tow-resume --max-runtime-seconds 1800
```

Resume rerun example:

```bash
python3.11 PDF_handle/TOOLS/content_routing_review.py --f2-report-dir PDF_handle/TOOLS/reports/semantic_system_purity_review/0.3/<timestamp> --slug cable-tow --provider gemini --model gemini-2.5-flash --report-dir PDF_handle/TOOLS/reports/content_routing_review/0.3/cable-tow-resume --resume
```

### `content_apply_engine.py`

Apply/preservation engine layered on top of an existing F3 report.

It:
- consumes `content_routing_*` artifacts from an existing F3 run
- expands routed review units into preservation/removal/transfer actions
- supports `plan` preview mode and `apply-safe` mutation mode
- keeps `plan` preview-only under the run report
- uses the fixed live preservation root `PDF_handle/preservation` unless `--preservation-root` is supplied in `apply-safe`
- preserves research/future material before any source cleanup
- never auto-injects content into other entries in v1

Phase F4 policy is documented in:
- `PDF_handle/TOOLS/specs/PHASE_F4_APPLY_PRESERVATION_ENGINE.md`

Plan preview example:

```bash
python3.11 PDF_handle/TOOLS/content_apply_engine.py --f3-report-dir PDF_handle/TOOLS/reports/content_routing_review/0.3/<timestamp> --mode plan
```

Apply-safe example:

```bash
python3.11 PDF_handle/TOOLS/content_apply_engine.py --f3-report-dir PDF_handle/TOOLS/reports/content_routing_review/0.3/<timestamp> --mode apply-safe
```

Apply-safe with isolated preservation root:

```bash
python3.11 PDF_handle/TOOLS/content_apply_engine.py --f3-report-dir PDF_handle/TOOLS/reports/content_routing_review/0.3/<timestamp> --mode apply-safe --preservation-root C:/preservation_sandboxes/f4-test-001
```

### `run_phase_f_sandbox_pilot.py`

Wider sandbox pilot runner for F2 -> F3 -> F4.

It:
- creates a fresh site copy under `sandbox_sites/`
- runs F2 and F3 on the Phase F pilot manifest
- runs F4 in sandbox-safe mode with an isolated override preservation root
- writes a consolidated pilot report with acceptance checks and sample inspection sets

Heuristic example:

```bash
python3.11 PDF_handle/TOOLS/run_phase_f_sandbox_pilot.py --provider heuristic
```

Gemini example:

```bash
python3.11 PDF_handle/TOOLS/run_phase_f_sandbox_pilot.py --provider gemini --model gemini-2.5-flash
```

### `run_phase_h_post_gating_smoke.py`

Post-gating live smoke runner for F2 -> F3 only.

It:
- creates a fresh sandbox site copy
- runs F2 and F3 with `--provider-policy provider_uncertain_only` or another selected policy
- compares the new smoke against the latest pre-gating live smoke baseline when available
- writes a consolidated report with provider usage, runtime, malformed/retry metrics, and sample inspection sets

Gemini example:

```bash
python3.11 PDF_handle/TOOLS/run_phase_h_post_gating_smoke.py --provider gemini --provider-policy provider_uncertain_only
```

### `audit_knowledge_flow.py`

Warn-first audit for `level1` instructional flow.

It uses a wave manifest to decide which entries are core, then checks:
- `flow_role`
- required `prior|companion|deeper` buckets
- `knowledge_type`
- `content_scope`
- flow quality problems such as structure-only links, duplicate links, and cross-degree `prior`
- route branching for Wave 2 style manifests
- concrete `prior` ratio against hubs/categories
- inbound link gravity, top inbound nodes, and future candidate anchors

Example:

```bash
python3.11 PDF_handle/TOOLS/audit_knowledge_flow.py --site-root 0.3 --manifest PDF_handle/TOOLS/knowledge_flow_waves/level1.phase1-plus-phase2.json
```

### `targeted_refill_from_audit.py`

Mode A targeted refill for sparse entries:

- reads `audit_sparse_refill_queue.json`
- selects only sparse targets that pass your filters
- builds compact evidence packets from existing `library` material
- calls Gemini only when enough evidence exists
- writes staged patch artifacts only

Example:

```bash
python3.11 PDF_handle/TOOLS/targeted_refill_from_audit.py --site-root 0.3 --audit-dir PDF_handle/TOOLS/reports/audit_sparse_entries/0.3/<timestamp> --degree level1 --classification seed_only,sparse --category ritual_flow --max-entries 10
```

### `run_targeted_refill_loop.py`

Automatic loop for targeted refill batches.

Use it when you want the remaining sparse entries to move in small batches through:
- targeted refill
- Step 6 apply-live
- Step 7 QA

It re-runs the audit between batches, skips prior `manual_review` items by default, and stops cleanly on quota or interruption.

Example:

```bash
python3.11 PDF_handle/TOOLS/run_targeted_refill_loop.py --site-root 0.3 --degree level1 --classification seed_only,sparse --batch-size 5 --provider gemini
```

## Reports

All TOOLS-generated reports go under:

```text
PDF_handle/TOOLS/reports/
```

This keeps maintenance output separate from:
- staged ETL state in `PDF_handle/staged_runs/`
- merge backups in `PDF_handle/merge_backups/`
- QA reports in `PDF_handle/qa_reports/`

## Recommended Workflow

### Full preprocess route

```bash
python3.11 PDF_handle/TOOLS/run_preprocess_01_04.py --book "<book>" --provider gemini --model gemini-2.5-flash
```

### Full postmerge route

```bash
python3.11 PDF_handle/TOOLS/run_postmerge_05_07.py --site-root 0.3
```

### Coverage audit after merge

```bash
python3.11 PDF_handle/TOOLS/audit_sparse_entries.py --site-root 0.3
```

### Degree-classification audit

```bash
python3.11 PDF_handle/TOOLS/audit_degree_classification.py --site-root 0.3 --degrees level1
```

### Knowledge-flow audit

```bash
python3.11 PDF_handle/TOOLS/audit_knowledge_flow.py --site-root 0.3 --manifest PDF_handle/TOOLS/knowledge_flow_waves/level1.phase1-plus-phase2.json
```

### Semantic system-purity review

```bash
python3.11 PDF_handle/TOOLS/semantic_system_purity_review.py --site-root 0.3 --provider heuristic
```

### Content routing review

```bash
python3.11 PDF_handle/TOOLS/content_routing_review.py --f2-report-dir PDF_handle/TOOLS/reports/semantic_system_purity_review/0.3/<timestamp> --provider heuristic
```

### Targeted refill from the audit queue

```bash
python3.11 PDF_handle/TOOLS/targeted_refill_from_audit.py --site-root 0.3 --audit-dir PDF_handle/TOOLS/reports/audit_sparse_entries/0.3/<timestamp>
```

### Automatic refill loop

```bash
python3.11 PDF_handle/TOOLS/run_targeted_refill_loop.py --site-root 0.3 --degree level1 --classification seed_only,sparse --batch-size 5 --provider gemini
```

## Important Rule

Audit reports are diagnostic only.

They are not enrichment and do not modify site JSON files.

Knowledge-flow manifests live under:

```text
PDF_handle/TOOLS/knowledge_flow_waves/
```

They control Phase 1 core inclusion and `flow_role`, but they do not override the dataset itself.

Current pattern:
- `level1.phase1-core.json`
  - Phase 1 pilot baseline
- `level1.phase2-expansion.json`
  - Wave 2 expansion set
- `level1.phase1-plus-phase2.json`
  - combined audit target for the current `level1` graph
