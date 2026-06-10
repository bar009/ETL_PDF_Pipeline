# Repo Layout

This document defines a concrete target layout for the workspace so new work lands in predictable places and the current folder sprawl stops growing.

## Goals

- one clear home for active projects
- one clear home for site versions and generated copies
- one clear home for the PDF pipeline
- no more numeric top-level folders as the primary way to understand state
- no more flat `TOOLS/` directory that mixes runners, audits, validators, specs, and phase experiments

## Naming Rules

- top-level folder names should describe a function, not a version
- version numbers belong under `releases/`, `archive/`, or named site folders
- generated output should never live beside source code unless the tool absolutely requires it
- if a folder is temporary, its name should say so
- prefer lowercase descriptive names for new folders

## Target Workspace Layout

```text
code/
  archive/
    legacy_sites/
    snapshots/
    backups/
  docs/
    ideas/
    pipeline/
    releases/
    specs/
  management/
  experiments/
    notebooklm_validation/
  projects/
    paperclip/
  scripts/
  sites/
    live/
      current/
    published/
    sandbox/
    work/
  PDF_handle/
    core/
    inputs/
    prompts/
    outputs/
    tools/
```

## Top-Level Migration Map

- `paperclip-master/paperclip-master/paperclip` -> `projects/paperclip/`
- `paperclip-master/paperclip-master` -> remove after the real repo is moved and verified
- `0.1` -> `archive/legacy_sites/v0.1/`
- `0.2` -> `archive/legacy_sites/v0.2/`
- `0.3` -> `sites/live/current/`
- `0.3-copy` -> `sites/work/v0.3-copy/` or delete if it is only a throwaway duplicate
- `published_sites/*` -> `sites/published/*`
- `sandbox_sites/*` -> `sites/sandbox/*`
- `site/` -> merge into `sites/` or remove if obsolete
- `sites/` -> keep as the only site container

## Why This Is Better

- the top level stops encoding workflow state through cryptic names
- the workspace gets one thin control surface for current operational state without turning `docs/` into a live status board
- active work, published copies, and historical versions are separated
- `paperclip` becomes a normal project folder instead of a nested `paperclip-master/.../paperclip` path
- the PDF pipeline remains together, but its code, inputs, outputs, and tools become easier to navigate

## Concrete `sites/` Layout

```text
sites/
  live/
    current/
      css/
      data/
      js/
      index.html
  published/
    2026-03-27-v0.3/
  sandbox/
    qa-smoke-2026-03-27/
  work/
    v0.3-copy/
```

Rules:

- `sites/live/current/` is the only active root used by the pipeline
- publishable snapshots get date-based folders under `sites/published/`
- disposable test copies go under `sites/sandbox/`
- manual working copies go under `sites/work/`

If scripts still require `0.3`, keep a compatibility phase where `0.3` remains in place until path defaults are made config-driven.

## Concrete `PDF_handle/` Layout

```text
PDF_handle/
  core/
    main.py
    pipeline_utils.py
    stage5_utils.py
    work_routing.json
    step_01_extract_pdfs.py
    step_02_chunk_markdown.py
    step_03_transform_chunks.py
    step_04_consolidate_books.py
    step_05_map_and_stage.py
    step_06_apply_reviewed_merge.py
    step_07_site_qa.py
  inputs/
    pdf_files/
  prompts/
  outputs/
    artifacts/
    consolidated_books/
    merge_backups/
    pipeline_runs/
    preservation/
    qa_reports/
    staged_injection/
    staged_runs/
  tools/
    apply/
    audits/
    data/
    diagrams/
    knowledge_flow_waves/
    lib/
    phases/
      phase_f/
      phase_h/
      phase_k/
      phase_m/
    reports/
    routing_taxonomies/
    runners/
    specs/
    validation/
  WORKFLOW.md
```

## Concrete `PDF_handle/tools/` Layout

The current `PDF_handle/TOOLS/` directory is documented, but it is too flat. The problem is not that the scripts are wrong. The problem is that different script roles are mixed together in one place.

Use this target structure:

```text
PDF_handle/tools/
  README.md
  tool_manifest.json
  apply/
    content_apply_engine.py
    apply_phase_m_5_2_decision_apply.js
    apply_phase_m_5_3_fc_tool_rewrite.js
    apply_phase_m_6_publish_site_version.js
    apply_phase_m_10_level3_build.js
    apply_phase_m_11_finalize_site_release.js
    apply_phase_m_12_post_refill_cleanup.js
    apply_phase_m_15_wave1_fill.js
    apply_phase_m_16_wave2_fill.js
    apply_phase_m_17_wave3_fill.js
    apply_phase_m_18_wave4_fill.js
  audits/
    audit_degree_classification.py
    audit_degree_readiness.js
    audit_knowledge_flow.py
    audit_pdf_pipeline_coverage.js
    audit_sparse_entries.py
    semantic_system_purity_review.py
    content_routing_review.py
  lib/
    common.py
    provider_runtime.py
    degree_signal_extractor.py
    degree_signal_registry.py
  phases/
    phase_f/
      run_phase_f_sandbox_pilot.py
    phase_h/
      run_phase_h_post_gating_smoke.py
    phase_k/
      phase_k_level1_refill.py
    phase_m/
      build_phase_m_13_breadth_backlog.js
      run_phase_m_4_controlled_fill.js
      run_phase_m_5_post_fill_audit.js
      run_phase_m_5_4_mini_post_rewrite_validation.js
      run_phase_m_7_full_system_smoke.js
      run_phase_m_8_1_seed_specs.js
      run_phase_m_8_topic_discovery.js
      run_phase_m_9_post_pdf_full_planning_bundle.js
      run_phase_m_9_post_pdf_full_planning_bundle.ps1
      validate_phase_m_4_topic_frames.js
  reports/
  runners/
    run_preprocess_01_04.py
    run_postmerge_05_07.py
    run_level1_product_closure.py
    run_targeted_refill_loop.py
    targeted_refill_from_audit.py
  specs/
    API_AUDIT_TABLE.md
    API_RELIABILITY_PROVIDER_RUNTIME_SPEC.md
    DEGREE_ARCHITECTURE_SPEC.md
    DEGREE_BUILD_PLAN.md
    DEGREE_CLASSIFICATION_SYSTEM.md
    DEGREE_SIGNAL_REGISTRY_STEP1_SPEC.md
    KNOWLEDGE_FLOW_ARCHITECTURE.md
    LEVEL1_BOUNDARY_SPEC.md
    PHASE_F1_RITE_SYSTEM_PURITY.md
    PHASE_F2_SEMANTIC_SYSTEM_PURITY.md
    PHASE_F3_CONTENT_ROUTING.md
    PHASE_F4_APPLY_PRESERVATION_ENGINE.md
    PHASE_H1_SCHEMA_CONTRACTION_REPAIR_HARDENING.md
    PHASE_I1_I2_F2_GATING_CALIBRATION.md
    PHASE_M8_TOPIC_DISCOVERY.md
    READING_LAYERS_AUTHORING.md
    TARGETED_REFILL_MODE_A.md
  validation/
    build_level1_boundary_goldset.py
    build_notebooklm_coverage_map.js
    build_refill_queue_from_step5_staging.js
    discover_level2_topic_candidates.js
    discover_level2_topic_candidates.py
    validate_degree_signal_registry_step1.py
    validate_f2_f3_runtime.py
    validate_f3_phase_j_micro_regression.py
    validate_level1_boundary_goldset.py
```

## Current `TOOLS/` To Target Mapping

- `run_*` scripts -> `tools/runners/`
- `audit_*` scripts -> `tools/audits/`
- `validate_*` scripts -> `tools/validation/`
- `apply_*` scripts -> `tools/apply/`
- `phase_*` and `run_phase_*` scripts -> `tools/phases/<phase>/`
- `PHASE_*` markdown docs -> `tools/specs/`
- `DEGREE_*`, `KNOWLEDGE_*`, `LEVEL1_*` markdown docs -> `tools/specs/`
- shared helpers like `common.py` and `provider_runtime.py` -> `tools/lib/`
- `README.md` and `tool_manifest.json` stay at `tools/` root
- `reports/`, `data/`, `diagrams/`, `routing_taxonomies/`, `knowledge_flow_waves/` stay as subfolders under `tools/`

## Safe Transition Plan

Do not rename everything at once. Use this order:

1. Freeze the target names in documentation.
2. Stop creating new root-level version folders.
3. Move old versions into `archive/legacy_sites/`.
4. Make the pipeline accept a configurable live site path instead of assuming `0.3`.
5. Move the active site into `sites/live/current/`.
6. Split `PDF_handle/TOOLS/` by role while keeping small compatibility wrappers if needed.
7. Move the real Paperclip repo into `projects/paperclip/`.
8. Remove the extra outer `paperclip-master/paperclip-master` shell once verified.

## Immediate Rules For New Work

- do not create new top-level numeric folders
- do not create new top-level site copies outside `sites/`
- do not add new scripts directly to `PDF_handle/TOOLS/`
- place new docs in `docs/` or `PDF_handle/tools/specs/`
- treat `PDF_handle/TOOLS/README.md` as operational docs, but treat this file as the target layout source of truth
