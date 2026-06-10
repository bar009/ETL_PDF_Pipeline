# Workspace Decision Log

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
