# ETL Runtime Data Boundary

This document defines the data boundary for the React V2 prototype and future adapter work.

## Rule

Existing site JSON files are ETL/runtime outputs.

They are immutable canonical artifacts for frontend work.

Frontend work must not:

- edit JSON content
- normalize JSON formatting
- patch missing fields
- rewrite arrays or object keys
- migrate schema shape
- auto-fix invalid or incomplete records
- create replacement runtime JSON files

## Protected Runtime Files

The current protected adapter target surface is `sites/work/v2.0/data/`.

The guard includes:

- `level1.json`
- `level2.json`
- `level3.json`
- `library.json`
- `degrees.json`
- `content.schema.json`
- `content.overrides.json`
- `content.localizations.he.json`
- `entry.template.json`
- `clean_rerun_seed_manifest.json`

The guard also reserves these expected runtime names before adapter review:

- `encyclopedia.json`
- `homepage_projection.json`

If those files become part of the selected data surface later, update this boundary intentionally before adapter implementation.

## Ownership

Content fixes belong to the ETL pipeline.

If frontend work discovers bad content, missing fields, broken Hebrew, duplicate titles, bad slugs, or schema mismatch:

- do not fix the JSON by hand
- record the issue as adapter/ETL evidence
- route the correction through the ETL review and promotion process
- rerun or patch through approved ETL tooling only

## Frontend Responsibility

The React/Next frontend may:

- read JSON through a read-only adapter
- validate required fields
- fail loudly on missing required fields
- use safe display fallbacks for optional fields
- keep localization overlays separate from canonical JSON

The frontend may not become a silent data repair layer.

## Guardrail

`tests/no-json-mutation-contract.spec.js` checks protected runtime files by SHA-256 hash.

Any byte-level change fails the React prototype test suite. This is deliberate: formatting-only changes are still mutations.

To intentionally change a protected JSON file, pause frontend work and use the approved ETL workflow.
