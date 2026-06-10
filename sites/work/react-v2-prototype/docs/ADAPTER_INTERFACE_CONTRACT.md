# Adapter Interface Contract

This document defines the interface for future read-only adapter work.

It is not an adapter implementation.

## Boundary

The adapter may eventually read ETL/runtime JSON, but frontend code must never mutate that JSON.

Current readiness work uses synthetic JavaScript fixtures only. It does not read `sites/work/v2.0/data`.

## Contract Module

Prototype contract file:

- `src/lib/adapterContract.js`

The module defines:

- `ADAPTER_CONTRACT_VERSION`
- `READ_ONLY_SOURCE_FILES`
- `RESERVED_SOURCE_FILES`
- `VIEW_MODEL_SHAPES`
- `MISSING_FIELD_POLICY`
- `ADAPTER_ERROR_POLICY`
- shape validation helpers for synthetic fixtures

The module does not:

- read JSON files
- import runtime data
- transform runtime records
- normalize content
- write files

## Source File Names

The planned read-only source names are:

- `sites/work/v2.0/data/degrees.json`
- `sites/work/v2.0/data/level1.json`
- `sites/work/v2.0/data/level2.json`
- `sites/work/v2.0/data/level3.json`
- `sites/work/v2.0/data/library.json`
- `sites/work/v2.0/data/content.schema.json`
- `sites/work/v2.0/data/content.overrides.json`
- `sites/work/v2.0/data/content.localizations.he.json`

Reserved pending boundary review:

- `sites/work/v2.0/data/encyclopedia.json`
- `sites/work/v2.0/data/homepage_projection.json`

## View Models

The future adapter should return prepared view models.

The UI should not consume raw runtime JSON records.

Required view-model groups:

- `DegreeViewModel`
- `TopicEntryViewModel`
- `LibrarySourceViewModel`
- `RouteMetadataViewModel`

## Missing Fields

Hard-fail fields:

- `slug`
- `title`
- `degree`
- `source`

Display-only fallback fields:

- `summary`
- `status`
- `related`
- `sourceYear`
- `sourceKind`
- `coverage`

Fallbacks must not be written back to runtime JSON.

## Error Behavior

Hard failures:

- invalid JSON shape
- duplicate route slug
- degree/library boundary crossing
- protected content without access policy

Report-only findings:

- optional metadata gap
- missing related target
- long title
- localization coverage gap

## Synthetic Fixture Tests

Contract tests live in:

- `tests/adapter-contract-fixtures.spec.js`
- `tests/fixtures/adapterContractFixtures.js`

These tests use synthetic JS objects only. They are deliberately separate from real runtime JSON.
