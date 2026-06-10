# Workspace Decision Log

## 2026-06-11 (systemic plan)

### The five run-pinned one-shot CLIs are deleted (WS11)

Reason:
- `degree_root_preview/write` and the `e1/e2_*_apply_review` scripts were pinned to
  old-workspace data (`sites/work/v0.5`, `runs/v21r1-...`), crashed on any invocation in
  this repo, and their one-time jobs were already executed in the old workspace

Consequence:
- fewer entrypoints; no working operator flow is affected
- `PDF_handle/docs/WRAPPER_RETIREMENT.md` is the canonical keep/deprecated/deleted map with
  a named reason per retained wrapper
- the smoke test's one-shot exclusion list is empty and test-enforced, so a new one-shot
  script must be deliberately registered

### The frontend adapter contract names this repo and runs in npm test (WS10)

Reason:
- the adapter contract constants and the no-json-mutation Playwright spec still named
  `sites/work/v2.0/*` files (with byte hashes) from the old workspace, so the read-only
  boundary was unenforceable here and absent from CI

Consequence:
- the contract is re-baselined to v2: the runtime surface is `public/data/*.json`
- `src/lib/readOnlyBoundary.test.js` enforces the boundary inside `npm test`/CI: no
  committed runtime JSON, no reserved surfaces, no write methods or filesystem access in
  the adapter layer
- the stale Playwright no-json-mutation spec is deleted (replaced by the vitest version)

### Staged content crosses to runtime only through explicit review states (WS9)

Reason:
- nothing structural separated "the AI suggested it" from "it entered the canon"; the
  approval selectors in Step 6 are opt-in flags, not a state model

Consequence:
- `prod/schema/review_states.py` defines suggested → reviewed → approved → published with
  rejected as terminal; illegal transitions raise
- new staged operations are stamped `suggested` by `build_degree_patch_operation`
- `assert_operations_approved` is the staging→runtime door: only `approved` merges; legacy
  operations without the field need `allow_unreviewed_legacy=True` and produce warnings
- the offline smoke enforces the door; the staging fixture is committed as `approved`
- the workflow contract lives in `PDF_handle/docs/REVIEW_WORKFLOW.md`

### Every run leaves one canonical run_manifest.json (WS8)

Reason:
- run evidence was prints plus tool-specific report shapes; debugging had no single file to
  start from, and provider cost/usage was not captured uniformly

Consequence:
- `prod/core/run_manifest.py` builds the canonical shape: run_id, tool, timing, inputs,
  config, steps (with per-step counts), aggregate counts, warnings, errors, outputs, and
  provider_usage (fed by WS7 ProviderResult)
- the shape contract is committed at `data/schemas/run_manifest.schema.json`
- `smoke_fixture.py` is the first adopter — its report *is* a run manifest; new pipeline
  tools should build their run evidence through `RunManifest`
- `tests/test_run_manifest.py` keeps the builder, the schema file, and the first adopter in
  agreement without requiring the jsonschema package

### Provider calls return a uniform, non-throwing ProviderResult (WS7)

Reason:
- provider calls returned ad-hoc dicts and raised unclassified RuntimeErrors, locking
  consumers to Gemini-specific message strings and making failures untestable offline

Consequence:
- `prod/providers/result.py` defines the contract: provider/model/transport, text/payload,
  usage_metadata, duration_seconds, classified error_kind, optional raw_evidence_path
- `run_text` / `run_json` are the preferred provider entry points; the legacy `generate_*`
  shims delegate to them and re-raise the original exception types so existing retry/skip
  logic is untouched
- `MalformedProviderPayloadError` now subclasses `ProviderError` with a preset error kind
- `tests/test_provider_result.py` covers success, every failure class, and the legacy shim
  behavior with a mocked transport — no network or SDK needed

### The stage→apply path has a dedicated idempotency harness (WS6)

Reason:
- merge idempotency was guarded only at the patch layer; the fixture-driven end state
  (same input twice → same answer) had no named invariants

Consequence:
- `tests/test_idempotency_harness.py` pins, separately: normalization idempotency,
  determinism across independent runs, no duplicate marked blocks on re-apply, stable
  slugs/entry count, and byte-stable merge output
- a regression in any one invariant fails with a message naming exactly what broke

### The data contract is proven by failure too (WS5)

Reason:
- contract tests that only show good data passing cannot catch a gate that silently accepts
  bad data; the WS5 fixtures showed the gate accepted entries with no title or slug because
  normalization invents defaults for both

Consequence:
- `data/fixtures/invalid/` holds deliberately broken degree files (duplicate slug, missing
  relation target, illegal status, missing required fields); staging-as-runtime is covered
  by the staging fixture itself
- the gate's raw source-integrity check now also rejects entries missing a slug or title
- `tests/test_invalid_fixture_contracts.py` requires every invalid fixture to fail the gate
  with an error naming its specific rule, and fails if a fixture exists without coverage

### validate_runtime.py is the single publishability gate (WS4)

Reason:
- validation logic existed but was scattered across steps; nothing answered "is this site
  root publishable?" in one command
- normalization silently repairs duplicate slugs and illegal status/type values, so a gate
  that only validates normalized data passes corrupted source files

Consequence:
- `PDF_handle/prod/cli/validate_runtime.py --site-root <path>` runs: site-root contract,
  raw source integrity (duplicates/illegal enums before normalization can repair them),
  schema + contract validation per degree file, cross-degree reference checks, and minimal
  provenance (book/chapter must carry source_notes or work_id)
- `--require-complete` errors on missing standard degree files; `--strict` fails on warnings
- `tests/test_validate_runtime_gate.py` proves the gate passes the runtime fixture and fails
  each bad-data class

### There are no built-in site roots (WS3)

Reason:
- both `prod/core/site_roots.py` and `TOOLS/lib/site_roots.js` carried baked-in defaults
  naming old-workspace paths (`0.3`, `sites/live/v0.4-current`, `published_sites`, ...) that
  a clean checkout would silently search for

Consequence:
- `DEFAULT_SITE_ROOTS_CONFIG` is empty in both lanes; site roots come only from an explicit
  `--site-root` or `sites/site_roots.json`
- an unconfigured lookup fails fast with a message pointing at the committed template
  `sites/site_roots.example.json`; `sites/README.md` documents the model
- `tests/test_site_roots_config.py` pins the contract, including that the JS lane carries no
  legacy defaults

### The offline fixture smoke is the canonical "is the ETL path alive" check (WS2)

Reason:
- `--help` smoke checks prove entrypoints parse, but not that staging→apply→runtime works;
  the systemic plan requires a real minimal ETL path with no PDFs and no providers

Consequence:
- `PDF_handle/prod/cli/smoke_fixture.py` runs the real merge layer over the committed
  fixtures: site-root contract, pre-validation, patch apply, idempotent re-apply,
  provenance marker, post-validation, atomic write round-trip
- it runs in the unittest suite (`test_smoke_fixture.py`) and as a dedicated CI step after
  the unit tests
- `docs/CHECKS.md` lists it as part of the canonical check list

## 2026-06-11

### CI runs the documented check list on every pull request (Phase 6)

Reason:
- the structure is only real if it is enforced; `docs/CHECKS.md` existed but nothing ran it
  automatically

Consequence:
- `.github/workflows/checks.yml` runs the Python checks (compileall, import boundaries,
  unittest suite, ignore-rules guard) and the React checks (npm ci/build/test) on every PR
  and on pushes to `main`
- `README.md` documents the local setup path, branch hygiene (protect `main`, require the
  `checks` workflow), and a six-line new-work checklist
- the stale `pytest` instruction in `README.md` is gone — the suite is stdlib `unittest`

### Site roots resolve at call time, never at import or parser-build time (Phase 5)

Reason:
- the new `--help` smoke check exposed that `e2e.py`, 12 other prod CLIs, and the
  `stage`/`apply`/`qa` steps resolved site roots eagerly — as argparse defaults or
  module constants — so they crashed on a clean checkout even for `--help` or when an
  explicit `--site-root` was passed
- `guarded_merge_shadow.py` imported a prod module before its `sys.path` bootstrap

Consequence:
- site-root argparse defaults are `None` and resolve after parsing
- `PDF_handle/tests/test_cli_smoke.py` runs `--help` against every prod CLI and step
  wrapper, so the regression cannot return
- five one-shot scripts pinned to past runs (`degree_root_preview`, `degree_root_write`,
  `e1_new_sources_apply_review`, `e2_apply_review_rules`, `e2_new_sources_apply_review`)
  are excluded by name and flagged as retirement candidates
- `docs/CHECKS.md` is the canonical local check list; CI must run the same commands

### Legacy helpers collapse into re-export shells over prod (Phase 4)

Reason:
- `workspace_paths.py` was a byte-for-byte duplicate of `prod/core/site_roots.py`
  (including a second copy of the site-roots config defaults), and `pipeline_utils.py`
  duplicated the prod `io`/`text`/`books`/`site_data` helpers
- `pipeline_utils` resolved the live site root at import time, so every TOOLS script that
  imported it crashed on import in this repo

Consequence:
- both files are now pure re-export shells over `PDF_handle.prod` — one implementation,
  three historical import names (`stage5_utils` was already a shell)
- `pipeline_utils.DEFAULT_SITE_ROOT` is removed; site roots resolve at call time
- the historical atomic-write names map to the prod writers, which are always atomic
- `tests/test_wrapper_thinness.py` now pins all three shells: prod-only imports, no logic,
  and importable in a checkout without site data
- known pre-existing drift left in place: some `TOOLS/validation/*` scripts import `common`
  from its pre-migration location instead of `TOOLS/lib/common.py`

### The React adapter enforces its declared missing-field policy (Phase 3)

Reason:
- `adapterContract.js` declared `source` a hard-fail field and `status` display-fallback-only,
  but `contentAdapter.js` rendered blanks for both and passed array `source_notes` through as
  a non-string — the contract was documentation, not behavior

Consequence:
- `loadContent()` now drops entries with no source provenance, flattens array `source_notes`
  to display text, and falls back to the pipeline-default draft status label
- `collectRelationFindings()` implements the report-only relation policy
- `src/lib/adapterBoundary.test.js` pins missing fields, unknown routes, locale direction,
  and relation references, so `npm test` proves the boundary instead of trusting it

### Data states get committed fixtures and contract tests (Phase 2)

Reason:
- the roadmap requires that a newcomer can tell source, staging, canonical, runtime, and
  evidence apart, and that a staged artifact is never treated as site runtime

Consequence:
- `data/schemas/content.schema.json` is the committed contract home for runtime degree data
- `data/fixtures/runtime_site_root/` is the smallest valid runtime site root;
  `data/fixtures/staging_minimal/` is the smallest staged review artifact
- `PDF_handle/tests/test_data_state_contracts.py` fails if a staging dir satisfies the
  site-root contract, if the fixture schema copy drifts from the contract home, or if the
  staged fixture stops applying cleanly to the runtime fixture
- the legacy fallback defaults in `prod/core/site_roots.py` still name old-workspace roots;
  re-pointing them stays deferred until a real site root exists in this repo

### The active control surface is `docs/`, not the old repo's `management/`

Reason:
- `AGENTS.md`, `PDF_handle/AGENTS.md`, `docs/REPO_LAYOUT.md`, and other migrated guidance
  still pointed at `management/*` files and old-workspace paths (`0.3`, `paperclip-master/`)
  that deliberately stayed in the old repo, including a claim that canonical pipeline logic
  lives in the root `step_01..07.py` scripts

Consequence:
- `docs/STRUCTURE_ROADMAP.md` is the active plan; `docs/DECISION_LOG.md` records lasting
  decisions; `management/` is not recreated
- both AGENTS files and `docs/REPO_LAYOUT.md` are re-baselined to describe this repo
- `PDF_handle/WORKFLOW.md` carries a status note marking its step commands as compatibility
  wrappers and its `0.3` site-root references as historical
- known remaining stale pointers: `.agents/skills/knowledge-mode-page-design` and
  `.agents/skills/hebrew-rtl-site-redesign` still reference `management/ui_research_*`
  notes that only exist in the old repo

### Phase 0 of `docs/STRUCTURE_ROADMAP.md` is verified complete

Reason:
- `git check-ignore` confirms `.env`, raw data, generated data, and outputs are ignored
- `python PDF_handle/prod/check_import_boundaries.py` passes
- `python -m compileall -q PDF_handle/prod PDF_handle/tests` passes
- `python -m unittest discover -s PDF_handle/tests` passes

Consequence:
- Phase 1 (clarify code homes) is now the active phase, starting in `PDF_handle/prod/`

### `PDF_handle/prod/README.md` is the canonical code-homes note

Reason:
- the migrated copy still pointed at `management/*.md` files that deliberately stayed in the
  old repo, so the clean repo had no working code-homes documentation

Consequence:
- the "Where New Code Goes" table in `PDF_handle/prod/README.md` is where contributors look
  to place a new step, CLI command, helper, provider, schema, test, or prompt
- the wrapper-to-prod map lives in the same file, replacing the archived
  `management/WRAPPER_CLASSIFICATION_V1.md` family

### Wrapper thinness and prod import boundaries are enforced by tests

Reason:
- the roadmap requires boundary tests before any broad folder move, and the import check was
  only a standalone script that nothing forced anyone to run

Consequence:
- `PDF_handle/tests/test_import_boundaries.py` runs the import-boundary policy inside the
  unittest suite
- `PDF_handle/tests/test_wrapper_thinness.py` fails if a compatibility wrapper grows its own
  functions/classes or stops delegating to `PDF_handle.prod`

## 2026-04-14

### `prod/` is the canonical Python ETL execution surface

Reason:
- all business logic, schemas, step implementations, and runners now live under `PDF_handle/prod/`
- root-level `step_01..07.py` and `PDF_handle/TOOLS/` scripts are backwards-compatibility and ops wrappers only

Consequence:
- new pipeline logic must be added inside `prod/cli/`, `prod/impl/`, `prod/steps/`, or `prod/core/`
- do not add core logic to root-level step wrappers or TOOLS scripts

## 2026-03-27

### Canonicalize repo-discovered skills under `.agents/skills/`

Reason:
- the repo needed one explicit canonical skill home so duplicate copies would not keep reintroducing drift

Consequence:
- `.agents/skills/` is the canonical repo-discovered skill path
- `PDF_handle/skills/` is draft/local-copy only unless a skill is explicitly promoted

### Treat the current `PDF_handle` override map as sufficient unless new workflow divergence appears

Reason:
- the repository already contains local overrides for the main operational sub-areas, and the real problem was documentation drift rather than missing coverage

Consequence:
- no additional `AGENTS.override.md` is required right now
- new overrides should be added only when a sub-area has materially different workflow from its parent guidance

### Add a thin `management/` control surface at workspace root

Reason:
- current operational state, backlog, and approval expectations were spread across roadmap docs, guidance docs, and artifacts

Consequence:
- `management/*` now owns current operational state and active control
- `docs/*` remain the enduring architecture and policy layer
- reports and artifacts remain evidence, not control files

### Add a workspace-level AI guidance layer

Reason:
- project-level guidance alone was not enough because the main confusion starts at workspace root

Consequence:
- root `AGENTS.md`, `.codex/config.toml`, and workspace docs now act as the cross-project navigation layer

### Keep project-specific skills inside `PDF_handle/`

Reason:
- the requested skills are ETL-specific and would become duplicated or misleading if copied to workspace root

Consequence:
- root guidance stays light
- superseded by the later decision that makes `.agents/skills/` the canonical repo-discovered skill home
- `PDF_handle/skills/` remains only as a draft/local-copy area unless explicitly promoted

### Add canonical repo skills under `.agents/skills/`

Reason:
- official Codex repository discovery uses `.agents/skills/`

Consequence:
- repo-facing skills now live in the official discovery path
- `PDF_handle/skills/` should be treated as local copies or future draft material until cleaned up

### Treat `docs/REPO_LAYOUT.md` as the workspace layout source of truth

Reason:
- the folder-sprawl problem is workspace-wide, not only ETL-wide

Consequence:
- future path moves should be aligned with that layout before large refactors happen
