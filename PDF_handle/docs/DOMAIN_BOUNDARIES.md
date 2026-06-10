# Domain Boundaries

## Primary Domains

### Source ingestion

- `PDF_files/`
- `extracted_books/`
- `chunked_books/`
- `transformed_books/`
- `consolidated_books/`

These folders represent source-derived processing state.

### Site data

- target site root `data/content.schema.json`
- `data/library.json`
- `data/level1.json`
- `data/level2.json`
- optional `data/level3.json`

This is the publishable content model.

### Staged change sets

- `staged_injection/`
- `staged_runs/`
- Step 5 and targeted refill reports

These hold candidate changes before live apply.

### Preservation

- `preservation/`

This is where material goes when it should be retained outside its original entry or lane.

### Reporting and audits

- `pipeline_runs/`
- `qa_reports/`
- `merge_backups/`
- `TOOLS/reports/`

These are evidence and operator artifacts, not source truth.

## Boundary Rules

1. Do not treat reports as data sources unless the workflow explicitly consumes them.
2. Do not let audit output overwrite live JSON by accident.
3. Do not skip staging when content is intended for live site data.
4. Do not mix `library` preservation material with `level1` and `level2` teaching content without an explicit routing decision.
5. Keep backups and snapshots outside canonical live paths.

## Tooling Boundaries

- `pipeline_utils.py` owns shared path and IO helpers.
- `stage5_utils.py` owns Step 5 and Step 6 merge/mapping helpers.
- `TOOLS/` scripts may orchestrate and inspect, but should not silently redefine core step contracts.

## Version Boundaries

- numeric release labels such as `0.3` and `0.4` are release identities
- live, sandbox, published, and archived are operational states
- do not confuse release identity with operational state in folder naming
