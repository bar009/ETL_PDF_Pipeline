# Knowledge Flow Architecture

Phase 1 defines `level1` as a learning graph, not just a content list.

## Scope

- no new UI in this phase
- no new lane for `glossary`
- no schema field for core inclusion
- `level1` only

## Sources of Truth

- `0.3/data/level1.json`
  - entry content and structural metadata
- `PDF_handle/TOOLS/knowledge_flow_waves/*.json`
  - Phase 1 core inclusion and `flow_role`
- `related_topics.prior|companion|deeper`
  - instructional flow
- `knowledge_links`
  - research / library bridges

`manifest.category` is validation-only. It never overrides the dataset.

## Flow Semantics

- `prior`
  - what should be read first in order to understand the entry
- `companion`
  - what sits beside the entry at the same layer of understanding
- `deeper`
  - what deepens the reader from the current node onward

Flow links are directional.

They are not required to be symmetric. The audit only reports missing soft reciprocity as a `note` or `warning`.

## Flow Roles

- `gateway_hub`
- `instructional_topic`
- `symbol_node`
- `ritual_node`

These roles come from the wave manifest, not from `type` alone.

## Quality Targets

These are quality targets, not existence requirements.

- `gateway_hub`
  - target: `prior 0-1`, `companion 2+`, `deeper 2+`
  - required buckets: `companion`, `deeper`
- `instructional_topic`
  - target: `prior 1-2`, `companion 2+`, `deeper 1+`
  - required buckets: `prior`, `companion`, `deeper`
- `symbol_node`
  - target: `prior 1+`, `companion 2+`, `deeper 1+`
  - required buckets: `prior`, `companion`, `deeper`
- `ritual_node`
  - target: `prior 1+`, `companion 2+`, `deeper 1+`
  - required buckets: `prior`, `companion`, `deeper`

Supporting entries in this phase:

- `category`
- `connector`
- `glossary`
- `book`
- `chapter`

They do not receive hard flow minimums.

## Severity Policy

- `Error`
  - broken structure
  - invalid dataset assumptions
  - missing required flow bucket entirely
- `Warning`
  - valid but weak instructional flow
  - links too general
  - role target not fully met
- `Note`
  - editorial improvement opportunity

## Quality Heuristics

The audit highlights:

- self-links
- duplicate slugs across flow buckets
- `prior` links that point to later-degree content
- `book/chapter` inside `related_topics`
- entries connected only to `category` / `hub` structure
- entries where more than half the flow links point only to general structure
- `deeper` buckets that never reach a concrete topic / symbol / ceremony / concept
- `companion` buckets that lack category or type diversity

If all flow links of an entry lead only to `category` or `hub`, the entry is connected to structure but not to knowledge, and the audit raises a strong warning.

## Pilot Wave

Phase 1 starts with ten `level1` anchors:

- `degree-1-entered-apprentice`
- `heder-hahirhurim`
- `l1-ritual-hakhnisa-harishona-lalishka`
- `hakafot-circumambulation`
- `l1-obligation-chovot-haach-badraga-harishona`
- `luach-hadraga`
- `l1-tools-mashmaut-meshulevet-klei-hatalmid`
- `cable-tow`
- `chasifat-haguf`
- `l1-inner-work-mahi-haavoda-badraga-harishona`

Each pilot entry should end Phase 1 with:

- explicit `flow_role`
- valid `knowledge_type`
- valid `content_scope`
- non-empty required flow buckets

The audit is the primary acceptance gate for this phase.
