# Phase F4: Apply / Preservation Engine

`content_apply_engine.py` is the execution layer on top of F3.

It consumes an existing `content_routing_review` report and turns routed review units into:

- patch plans
- preservation outputs
- transfer-candidate artifacts
- safe source cleanup in `apply-safe`

## v1 Principles

- F4 consumes F3 only. It does not auto-run F1, F2, or F3.
- `plan` is the default mode and is report-only.
- `apply-safe` preserves first, then removes from source only for approved safe cases.
- the live preservation root is fixed to `PDF_handle/preservation`
- `--preservation-root` is available only for `apply-safe` and redirects preservation writes away from the live root
- v1 never auto-injects text into another existing entry.
- v1 never auto-creates new site entries.
- v1 never rewrites surviving source paragraphs.

## Preservation Destination Rules

- `plan` writes preview preservation only under `report_dir/preview_preservation/`
- `plan` never creates backups and never writes outside the run report
- `apply-safe` without `--preservation-root` writes to:
  - `PDF_handle/preservation/library/`
  - `PDF_handle/preservation/future_entries/`
- `apply-safe` with `--preservation-root` writes to:
  - `<override-root>/library/`
  - `<override-root>/future_entries/`
- override roots are validated on resolved paths and must not overlap the site root, the data dir, TOOLS reports, the live preservation root, or the repository root

## Preservation Records

Preserved unit JSONs are identical across preview, live, and override runs.

Each preserved unit includes:

- `review_unit_id`
- `entry_slug`
- `field_name`
- `paragraph_index`
- `content`
- `text_excerpt`
- `routing_decision`
- `library_bucket` or `future_entry_label`
- `preservation_payload_hash`
- `preserved_at`
- `source_run_id`
- `source_report_dir`

`preservation_payload_hash` is computed as canonical `sha256` over the content payload only, excluding volatile metadata such as timestamps, run ids, and path-dependent fields.

## Supported v1 Routing Decisions

### `move_to_library`

- preserve the paragraph into `PDF_handle/preservation/library/<library_bucket>/` in `apply-safe`
- preview the same structure under the F4 report dir in `plan`
- remove from the source field only in `apply-safe`

### `create_future_entry_candidate`

- preserve the paragraph into `PDF_handle/preservation/future_entries/<future_entry_label>/` in `apply-safe`
- preview the same structure under the F4 report dir in `plan`
- remove from the source field only in `apply-safe`

### `keep_here_framed`

- emit `no_op`
- keep manual follow-up visible
- do not rewrite automatically in v1

### `move_to_existing_entry`

- create transfer-candidate artifacts only
- do not inject into the target entry in v1
- do not remove from source in v1

### `drop`

- remove from source only when F3 marked it as `drop`, `preservation_value=low`, and no preservation destination exists
- always keep trace in action artifacts

## Safety Model

Before `apply-safe`, F4 validates:

- source entry exists
- field exists and is string-backed
- paragraph index is still valid
- current paragraph excerpt still matches the F3 row
- current source field hash still matches the planned hash
- current paragraph hash still matches the planned hash
- manifest and site context still match the F3 run

If any of these checks fail:

- the relevant action becomes `blocked`
- no mutation is applied for that action

## Backups

In `apply-safe`, F4 writes:

- `pre_apply_backups/`
- `pre_apply_backups/backup_manifest.json`

The backup manifest records:

- backed-up files
- source file hash before apply
- backup timestamp
- action ids touching that file

## Key Artifacts

F4 writes:

- `content_apply_summary.json`
- `content_apply_actions.json`
- `source_patch_plan.json`
- `library_preservation_applied.json`
- `future_entry_seed_applied.json`
- `existing_entry_transfer_candidates.json`
- `apply_manifest.json`
- Markdown and HTML reports

## Mental Model

- F1: is this contaminated?
- F2: where exactly is the contamination?
- F3: what should happen to it?
- F4: preserve it safely, then apply the approved cleanup
