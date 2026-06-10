# Workspace Domain Boundaries

## Workspace Domains

### `PDF_handle/`

Owns ETL logic, prompts, reports, staging, and preservation workflows for the PDF knowledge pipeline.

### `paperclip-master/`

Owns the Paperclip codebase and its nested repository state.

### site roots

- `0.1`
- `0.2`
- `0.3`
- `0.3-copy`
- `sites/`
- `published_sites/`
- `sandbox_sites/`

These represent content state, release state, or migration leftovers, not application code.

### `docs/`

Owns cross-workspace guidance such as layout, scope, boundaries, and decisions.

### `archive/`

Owns frozen or legacy material that should not be treated as active development state.

### `experiments/`

Owns one-off or exploratory work that should not quietly become production convention.

## Boundary Rules

1. Do not mix project-specific logic into workspace docs unless it affects multiple areas.
2. Do not let historical or published site roots look like active sources of truth.
3. Do not treat duplicated project folders as equivalent roots.
4. Keep migration docs at root and implementation docs inside the relevant project.
