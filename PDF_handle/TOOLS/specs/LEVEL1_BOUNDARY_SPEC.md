# Level1 Boundary Spec

## Product Model

`level1` is closed under a `Hybrid Core+Frame` model.

- `keep`: strict level1 core only
- `keep_here_framed`: short explanatory Blue Lodge framing that directly clarifies level1
- `move_to_library`: valid supporting knowledge preserved outside the core
- `create_future_entry_candidate`: coherent later-degree or external themes that deserve their own downstream entry
- `drop`: low-value dump/noise
- `manual_review`: true edge cases only

The closure target is `Applied Level1`, not just a clean pipeline rerun.

## Core Rules

### `keep`

Rows may stay `keep` only when they are one of:

- explicit Degree 1 or Entered Apprentice core instruction
- gate/orientation material that remains inside level1 framing
- symbolic or moral explanation that stays inside level1 scope

Rows may not remain `keep` when they contain explicit Degree 2/3 anchors or higher-degree contamination.

### `keep_here_framed`

Rows may become `keep_here_framed` only when they are:

- short
- explanatory rather than procedural
- useful for understanding a level1 concept
- still inside Blue Lodge framing

`keep_here_framed` is not a spillover path for later-degree procedural transfer.

### `move_to_library`

The library is for preserved, valid, non-core knowledge, especially:

- `comparative_rituals`
- `historical_research`
- `biblical_symbolic_expansion`
- explanatory synthesis that does not belong in strict core
- advanced Blue Lodge rows that should not remain in `keep`

### `create_future_entry_candidate`

Future-entry preservation is the default for:

- Royal Arch or appendant material
- coherent later-degree themes
- coherent external symbolic themes with entry-worthy scope

Future-entry closure means a valid preserved artifact with a canonical label, not a fully authored final entry.

## Precedence Rules

These rules override weaker native/default handling:

1. `degree_2_strong_anchor_detected` or `degree_3_strong_anchor_detected` may not finish as `keep`.
2. Explicit higher-degree contamination may not be finalized under weak/native suppression.
3. Degree 2/3 Blue Lodge rows may at most become `keep_here_framed` when they are short, explanatory, and non-procedural. Otherwise they must leave the core.
4. `royal_arch_or_appendant` material may never remain `keep` or `keep_here_framed`.
5. When both `future_entry_royal_arch` and `library_biblical_expansion` apply, `create_future_entry_candidate` wins if the row is coherent and entry-viable. `move_to_library` is the fallback only when the later-degree thread is not coherent enough for entry preservation.
6. Known `manual_review -> library` clusters should route deterministically to library when the row is medium-confidence, taxonomy-matched, non-foreign, and already preserving outside the core.

## Goldset Gate

The boundary goldset is stored in:

- `PDF_handle/TOOLS/data/level1_boundary_goldset.json`

The goldset is a binding adjudication set. The validator compares a new full Phase H run against:

- `target_outcome`
- `target_bucket_or_label`

Acceptance expectations:

- 100% outcome match
- 100% bucket/label match for library and future-entry rows
- 0 rows with Degree 2/3 contamination left as `keep`
- 0 repeated routing conflicts for the known Royal Arch vs biblical-library cluster

## Closure Gate

`level1` is considered closed only after:

1. a full Phase H rerun on the full level1 manifest
2. goldset validation
3. `content_apply_engine.py --mode plan`
4. `content_apply_engine.py --mode apply-safe`
5. `audit_sparse_entries.py`
6. `audit_knowledge_flow.py`
7. a final closure bundle under `PDF_handle/TOOLS/reports/level1_product_closure/<run_id>/`
