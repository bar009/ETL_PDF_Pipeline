# JSON Schema Spec

This file is a working guide to the site-data contract.
The executable schema source of truth remains `data/content.schema.json` in the selected site root.

## Core Files

- `content.schema.json`
- `content.overrides.json`
- `library.json`
- `level1.json`
- `level2.json`
- optional `level3.json`

These paths are resolved through `pipeline_utils.build_site_data_paths()`.

## Dataset Expectations

### `library.json`

Use for preservation-first and reference-oriented material.
Book and chapter entries created by Step 5 land here first.

### `level1.json`

Use for first-degree instructional content.
Boundary-sensitive material should be reviewed carefully before being placed here.

### `level2.json`

Use for second-degree or deeper structured instructional content that should not remain in `level1`.

## Operational Contract

- Step 5 produces staged candidate files and operations.
- Step 6 applies approved operations into live degree datasets, then applies the canonical override layer for the selected site root.
- Validation must succeed across both per-file schema checks and cross-dataset reference checks.

## Override Contract

- `content.overrides.json` is the durable curated layer above generated base site data.
- It is keyed primarily by:
  - `site_root`
  - `degree`
  - `slug`
  - `language`
- Secondary locators such as `work_id`, `source_anchor`, `source_order`, and `source_heading` are stability aids only.
- Override records carry:
  - `identity`
  - `fields`
  - `base_snapshot`
  - `provenance`
- Override status (`active`, `stale`, `orphaned`, `conflict`) is generated in Step 6 / Step 7 reports, not stored as canonical authoring truth.

## Mapping Expectations

Step 5 structured mapping expects normalized fields such as:

- summary fields
- practical elements
- symbolic meaning
- candidate lesson
- caution notes
- tradition notes
- target entry candidates
- knowledge link candidates
- new topic candidates

The exact request/response contract is implemented in `step_05_map_and_stage.py`.

## Important Rule

This doc explains the contract.
It does not replace the schema file or the normalization logic in `stage5_utils.py`.
