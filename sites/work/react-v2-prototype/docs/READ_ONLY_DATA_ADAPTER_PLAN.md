# Read-Only Data Adapter Plan

This is a plan only.

No adapter implementation starts in this checkpoint.

## Goal

Connect existing ETL/runtime JSON to the React/Next UI without mutating canonical JSON.

The adapter is a read-only translation layer between runtime data and frontend view models.

## Source Files

Initial source surface:

- `sites/work/v2.0/data/degrees.json`
- `sites/work/v2.0/data/level1.json`
- `sites/work/v2.0/data/level2.json`
- `sites/work/v2.0/data/level3.json`
- `sites/work/v2.0/data/library.json`
- `sites/work/v2.0/data/content.schema.json`
- `sites/work/v2.0/data/content.overrides.json`
- `sites/work/v2.0/data/content.localizations.he.json`

Reserved or future source names:

- `encyclopedia.json`
- `homepage_projection.json`

These reserved files must not be introduced or assumed until the data boundary is reviewed.

## Target View Models

Interface contract:

- [`ADAPTER_INTERFACE_CONTRACT.md`](./ADAPTER_INTERFACE_CONTRACT.md)

The adapter should produce view models similar to the current demo content shape:

- `DegreeViewModel`
- `TopicEntryViewModel`
- `LibrarySourceViewModel`
- `CategoryViewModel`
- `ModeViewModel`
- `RouteMetadataViewModel`

The UI should consume prepared view models, not raw JSON records.

## Minimum Field Mapping

Degree view model:

- `id`
- `label`
- `title`
- `summary`
- `tone`
- `categories`

Topic entry view model:

- `degree`
- `title`
- `slug`
- `category`
- `categoryLabel`
- `type`
- `status`
- `summary`
- `body`
- `source`
- `related`

Library source view model:

- `degree: "library"`
- `title`
- `slug`
- `category`
- `categoryLabel`
- `type`
- `status`
- `summary`
- `body`
- `source`
- `sourceYear`
- `sourceKind`
- `coverage`
- `related`

## Missing-Field Policy

Required route fields should fail:

- missing `slug`
- missing `title`
- missing degree/source identity
- missing source file or invalid degree ownership

Optional display fields may use safe frontend fallbacks:

- missing summary: show a short unavailable-state message
- missing status: show neutral status text
- missing related links: show an empty relation list
- missing source metadata: show "not specified" display copy

Fallbacks must be display-only. They must not be written back to JSON.

## Error Policy

Adapter errors should be explicit and testable.

Use hard failures for:

- invalid JSON shape
- duplicate slugs in the same route namespace
- route collisions between degree topics and library sources
- records crossing degree/library boundaries
- protected/gated content appearing in a public-only build without policy

Use warnings or report entries for:

- optional metadata gaps
- missing related targets
- long titles that need UI truncation
- localization coverage gaps

## Localization Boundary

Canonical JSON remains source content.

Localization should be layered:

- shell chrome can stay in locale files
- translated display strings can come from a localization overlay
- canonical records should not be overwritten by translated text
- route metadata should choose localized display only when approved data exists

## Search Boundary

Search indexes may be built from adapted view models.

Search code may normalize text in memory for matching, but must not persist normalized JSON.

## Tests To Add Before Implementation

Before adapter code begins:

- keep no-JSON-mutation hash guard green
- add adapter fixture tests using copied/minimal non-runtime fixtures
- add duplicate slug tests
- add missing required field tests
- add library/source boundary tests
- add localization fallback tests
- add route parity tests for `/`, `/degree/:degreeId`, `/degree/:degreeId/:slug`, `/library`, and `/library/:slug`

## Stop Conditions

Pause adapter implementation if:

- JSON mutation appears necessary
- missing fields are too broad for safe display fallbacks
- auth/access policy is needed before route rendering
- library/topic boundaries are ambiguous
- localization would require rewriting canonical content
