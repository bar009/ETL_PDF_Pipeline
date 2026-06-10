# Degree Architecture Spec

## Purpose

Phase L defines the post-Level1 product architecture for multi-degree knowledge.
It does not build new Level2 or Level3 content.
It does not change F2, F3, provider policy, taxonomy routing, or the Level1 boundary spec.

The goal is to make the current state explicit:

- what is truly built today
- what is partial
- what is placeholder
- how future Level2 and Level3 work must be partitioned

## Current Built State

### Built today

- `data/level1.json` is a real product lane.
  - `79` entries
  - `9` categories
  - all entries have non-empty `short_summary`, `full_summary`, `symbolic_meaning`, and `candidate_lesson`
- `data/library.json` is a real research/archive lane.
  - `359` entries
  - `4` site categories
- `PDF_handle/preservation/future_entries/*` is a real preservation queue.
  - `199` preserved future-entry seeds across `4` labels

### Partial today

- `data/level2.json` exists, but it is not a complete content product.
  - `3` draft entries
  - `2` categories
  - `0` populated `symbolic_meaning`
  - `0` populated `candidate_lesson`
  - current slugs are generic shell slugs: `level2-t101`, `level2-t102`, `level2-t103`

### Not built today

- there is no `data/level3.json`
- there is no `level3` record in `data/degrees.json`
- runtime file lookup in `pipeline_utils.build_site_data_paths()` supports `level1`, `level2`, and `library`, but not `level3`

## Product Scope

### Level1

Level1 is already closed as a `Hybrid Core+Frame` product.

- `core_degree_content`: strict Entered Apprentice content only
- `framed_cross_degree_reference`: allowed only when short, explanatory, non-procedural, and safe inside Level1 framing
- no Royal Arch or appendant material in core or frame

### Level2

Level2 is the intended Fellow Craft product lane, but it is not built yet.

Its target scope is:

- native second-degree content only
- degree-2 symbols, working ideas, moral/intellectual development, and degree-native structure
- framed references to shared lodge roles only when explanatory and non-procedural

Its exclusions are:

- degree-3 core content
- Royal Arch
- appendant systems
- imported future-entry material that has not been promoted into a Level2 product spec

Today, Level2 should be treated as a partial shell, not as a finished learning lane.

### Level3

Level3 is not a built product today.

Its future target scope is:

- native third-degree core content only
- degree-3 ritual meaning, obligation framing, continuity, mortality/resolution themes, and degree-native symbols

Its exclusions are:

- Royal Arch
- appendant systems
- anything that belongs in library research rather than a core degree lane

No current artifact should claim that Level3 is a shipped content product.

### Library

Library is a separate product lane, not a spare bucket for rejected degree content.

Its scope includes:

- archival material
- comparative material
- historical material
- explanatory research that is valid but not core to a degree lane

Library remains real and built today, but its current public site taxonomy is broader and older than the newer preservation buckets produced by Phase H.

### Future Entry

`future_entry` is not a product lane.
It is a preservation and build queue.

A future-entry item is valid when it has:

- one canonical label
- preserved payload
- provenance back to source rows
- enough coherence to become a real entry later

It does not count as shipped product coverage until it is promoted into a real degree or library artifact.

## Category Architecture

### Shared categories

These are categories or category-slots that are allowed to span degrees without implying that all degrees are fully built.

#### `lodge_structure`

- current state: seeded and partially shared
- evidence: `4` Level1 entries already use `applies_to_degrees = [level1, level2, level3]`
- role: shared officer and lodge-role reference material
- rule: shared reference only; not a shortcut for importing degree-specific ritual content

#### `glossary_and_review`

- current state: Level1-only implementation today
- architecture status: shared-capable slot, not a shared product lane yet
- rule: glossary/reference material can become shared later, but current Level1 content remains Level1-owned

### Degree-specific categories

#### Level1

Built today:

- `gate`
- `preparation`
- `ritual_flow`
- `degree_board`
- `tools_and_signs`
- `obligation_and_law`
- `inner_work`
- `glossary_and_review`

Mixed/shared use today:

- `lodge_structure`

#### Level2

Current shell categories:

- `philosophy`
- `practice`

These are seed categories only.
They do not prove that the final Level2 taxonomy is complete.

#### Level3

No Level3 category set is approved yet.
Level3 category naming should be decided during the dedicated Level3 discovery/build pass, not pre-claimed now.

### Library-only categories

#### Current site-facing library categories

- `library_intro`
- `first_degree_work`
- `textbook_work`
- `etl_imports`

#### Current preservation-only research buckets

- `comparative_rituals`
- `historical_research`
- `biblical_symbolic_expansion`
- `higher_degree_material`
- `unassigned_research`

These preservation buckets are real backend partitions, but they are not yet a first-class site taxonomy.

## Content Partition Model

### `core_degree_content`

- residence: `data/level1.json`, `data/level2.json`, or future `data/level3.json`
- ownership: one degree lane
- metadata expectation:
  - `degree` = lane owner
  - `applies_to_degrees` usually contains one degree
  - `partition_role = core_degree_content` in future metadata

### `framed_cross_degree_reference`

- residence: inside the nearest safe degree lane
- ownership: one degree lane, but explicitly framed for more than one degree
- allowed only when explanatory, non-procedural, and safe
- current realization:
  - four Level1 `lodge_structure` entries use `applies_to_degrees = [level1, level2, level3]`
- this is a reference overlay, not a hidden transfer of later-degree content

### `library_content`

- residence: `data/library.json` or backend preservation material awaiting promotion
- ownership: library lane
- includes comparative, historical, symbolic-expansion, and archival material

### `future_entry`

- residence: preservation queue under `PDF_handle/preservation/future_entries/<label>/`
- ownership: queued for later productization
- not counted as built coverage

## File and Data Architecture

### Built runtime files

- `data/degrees.json`
- `data/content.schema.json`
- `data/entry.template.json`
- `data/level1.json`
- `data/level2.json`
- `data/library.json`

### Missing runtime file

- `data/level3.json`

### Backend preservation stores

- `PDF_handle/preservation/library/<bucket>/`
- `PDF_handle/preservation/future_entries/<label>/`

### Architecture rule

There is no dedicated shared-reference file today.
Shared/reference material must therefore remain attached to a concrete lane and be marked with explicit metadata rather than floating in an undefined shared space.

## Required Metadata

### Already available in the current schema

- `degree`
- `applies_to_degrees`
- `category`
- `content_scope`
- `status`
- `knowledge_links`
- `parallel_entry`
- `visibility_level`
- `sensitivity_level`

### Required for future multi-degree builds

These fields are architecture requirements for future Level2 and Level3 work.
They are not implemented as required schema fields today.

#### `partition_role`

Allowed values:

- `core_degree_content`
- `framed_cross_degree_reference`
- `library_content`
- `future_entry`

#### `product_state`

Allowed values:

- `built`
- `partial`
- `placeholder`
- `queued`

#### `degree_owner`

Allowed values:

- `level1`
- `level2`
- `level3`
- `library`

#### `placeholder_kind`

Allowed values:

- `lane_shell`
- `category_shell`
- `entry_stub`
- `none`

#### `source_queue_ref`

Pointer to the preservation bucket or future-entry label from which an item was promoted.

## Placeholder Policy

### What counts as a placeholder

A placeholder is any lane, category, or entry that exists only to reserve structure without providing enough content to claim product coverage.

### Rules

1. Placeholder content does not count as built product coverage.
2. Placeholder entries must remain `draft`.
3. A placeholder lane must never be described as complete because a file exists.
4. Placeholder slugs and shell categories are acceptable during build planning, but they must be labeled as partial or placeholder in readiness reporting.
5. A future Level3 file, if created before real build work, must still be marked as placeholder rather than shipped product.

### Current application

- Level1: built product
- Level2: partial shell
- Level3: not built
- Future-entry queue: queued preservation, not placeholder content

## Promotion Rules

### Promote from future-entry to product only when

- one canonical theme exists
- the target degree or library owner is explicit
- the content fits that lane's boundary spec
- the promoted artifact receives a final category and partition role

### Promote from preservation-library bucket to site library only when

- the target library category is explicit
- the content is cleaned for product use
- it is no longer only an internal preservation seed

## Definition of Truth for Phase L

The architecture must be truthful before it is ambitious.

- Level1 is a built product lane
- Library is a built research lane
- Level2 exists only as a partial shell
- Level3 does not exist as a product lane yet
- Future-entry is a queue, not coverage
