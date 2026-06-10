# Degree Classification System

This document defines the semantic classification model for degree-based knowledge entries.

## Core Rule

One entry equals one topic.

The topic may appear in several degrees, but the base explanation of the entry must belong to the degree of the entry itself.

That means:
- a `level1` entry explains the `level1` understanding first
- cross-degree comparison belongs only in the advanced layer

## Structural Type vs. Knowledge Type

The site already uses `type` for structural navigation:
- `topic`
- `symbol`
- `ceremony`
- `hub`
- `book`
- `chapter`

That field stays in place.

The semantic classification model therefore uses a second field:
- `knowledge_type`

Allowed values:
- `ritual`
- `symbol`
- `lodge_structure`
- `moral_philosophy`
- `historical_research`

## Content Scope

`content_scope` defines how broad the explanation is allowed to be.

Allowed values:
- `degree_specific`
- `cross_degree`
- `symbolic`
- `historical`

Recommended usage:
- `degree_specific`: the entry should stay inside one degree
- `cross_degree`: the advanced layer may compare across degrees
- `symbolic`: the main focus is symbolic interpretation
- `historical`: the main focus is research or historical framing

## Reading Layers

Entries that use the layered reading model should define:

- `reading_layers.basic`
- `reading_layers.symbolic`
- `reading_layers.advanced`

Rules:
- `basic` explains what the current degree needs to understand now
- `symbolic` connects the topic to the symbolic language of the same degree
- `advanced` may include research, comparisons, and wider framing, but only in a clearly marked way

## Content Rules by Knowledge Type

### `ritual`

Use for:
- candidate preparation
- lodge entry
- circumambulation
- obligation

Rules:
- should normally belong to one degree only
- must explain what happens in the ritual and what it means in that degree
- must not casually mix higher-degree material into the basic layer

### `symbol`

Use for:
- apron
- tracing board
- working tools
- rough ashlar

Rules:
- the same symbol may appear in multiple degrees
- the entry still explains the current degree first
- cross-degree comparison belongs only in the advanced layer

### `lodge_structure`

Use for:
- officers
- orientation
- pillars
- mosaic pavement

Rules:
- may span more than one degree
- should stay focused on stable structure rather than ritual sequence

### `moral_philosophy`

Use for:
- self-mastery
- brotherhood
- virtues
- inner work

Rules:
- may connect to more than one degree
- should not become abstract research too early

### `historical_research`

Use for:
- ritual monitors
- constitutions
- development of the rite

Rules:
- historical comparison is allowed
- advanced layer may be broader than degree-specific entries

## Automatic Audit Rules

The classification audit currently enforces these checks:

1. Missing semantic fields:
   - `knowledge_type`
   - `content_scope`
   - complete `reading_layers`

2. Ritual scope:
   - if `knowledge_type = ritual` and `applies_to_degrees` has more than one degree, flag it

3. Cross-degree leakage in `level1`:
   - terms such as `Fellow Craft`, `Second Degree`, `Master Mason`, `Royal Arch`
   - and their common Hebrew equivalents
   - are flagged when they appear in `level1`

Severity policy:
- `basic` and `symbolic` leakage is treated as an error
- `advanced` and `full_summary` leakage is treated as a warning unless the entry is explicitly scoped as `cross_degree` or `historical`

## Editorial Workflow

Do not try to fix the whole site at once.

Work in waves:

1. gate entries
2. ritual entries
3. symbol entries
4. research and history

Pilot entries should be completed first, then the schema and audits can expand to the rest of the site.
