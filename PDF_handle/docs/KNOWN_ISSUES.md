# Known Issues

## Structural Issues

### `0.3` is still a path default

Impact:
- scripts may target the old live-root convention unless `--site-root` is passed explicitly

### `TOOLS/` still has a crowded transition root

Impact:
- canonical implementations are now split, but root-level shims plus shared helpers still make `TOOLS/` look busier than its real execution model

### Project root and git root are not the same

Impact:
- repo-level guidance can be ambiguous unless `PDF_handle/` is treated as the operational root

## Workflow Issues

### Reports and live data are easy to confuse

Impact:
- there are many generated JSON and markdown artifacts near real data and staging outputs

### Published, sandbox, and historical site copies do not share one naming model

Impact:
- it is harder to reason about what is current, safe to mutate, or frozen

### Shared helpers and specs are not yet split into `lib/` and `specs/`

Impact:
- the executable split is clearer now, but shared modules and markdown specs still live together at the `TOOLS/` root

## Documentation Gaps

### Schema and relation rules were implied more than centralized

Impact:
- mapping and boundary decisions take longer to reconstruct

### NotebookLM validation knowledge was spread across experiments and reports

Impact:
- it is harder to know what is reference guidance vs one-off experiment output

### Local override coverage and the docs can drift apart

Impact:
- the repo now has local overrides for the main operational sub-areas, but the docs must stay aligned so operators do not reason from stale coverage assumptions

### `TOOLS/` still has transition-era compatibility shims at root

Impact:
- the implementation split is now real, but the root folder still contains shim entrypoints until command paths and docs are fully migrated
