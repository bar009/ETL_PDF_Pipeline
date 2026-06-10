# Data Contract

This repo separates generated ETL artifacts from approved content and site runtime data.

## Data States

### Staging

Review material produced by ETL.

Examples:

- topic candidates
- proposed patches
- mapping reports
- provider output summaries

Staging data is not user-facing truth.

### Canonical

Approved records that define content identity and relationships.

Canonical records must be stable enough for repeatable exports and frontend links.

### Site Runtime

The JSON shape consumed by the frontend.

Runtime data may be derived from canonical records, overrides, localization bundles, and release packaging.

## Entry Shape

The current site contract is documented in:

- `PDF_handle/docs/JSON_SCHEMA_SPEC.md`
- `PDF_handle/docs/RELATION_RULES.md`

Every user-facing entry should have stable identity, display text, status, provenance, and validated links.

Minimal conceptual shape:

```json
{
  "id": "string",
  "slug": "string",
  "title": "string",
  "degree": "library | level1 | level2 | level3",
  "type": "string",
  "status": "draft | approved | rejected",
  "summary": "string",
  "sources": [],
  "relations": []
}
```

## Idempotency Expectations

For the same input and configuration:

- the same source should resolve to the same source identity
- the same topic should resolve to the same slug
- repeated runs should not create duplicate entries
- link validation should not depend on run order

## Test Expectations

Keep tests for:

- schema validity
- duplicate IDs and slugs
- broken relations or related-topic references
- protected import boundaries
- frontend adapter no-mutation behavior

