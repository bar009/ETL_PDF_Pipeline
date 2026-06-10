# Targeted Refill Mode A

This document defines the exact logic for the next tool:

- `PDF_handle/TOOLS/targeted_refill_from_audit.py`

Mode A means:

- evidence-only refill
- no free-form brainstorming by the model
- no site mutation during refill
- append-only staged patch generation

## Core Rule

The model is never asked:

- "write about this topic"
- "explain this symbol from general knowledge"
- "complete what seems missing"

The model is only asked:

- "given this existing entry and these approved source excerpts, produce additions only"

## Inputs

The refill tool should consume:

1. `site-root`
   - current live site data
   - usually `0.3`

2. `audit_sparse_refill_queue.json`
   - produced by `audit_sparse_entries.py`
   - contains the sparse targets and ranked candidate library sources

3. `library.json`
   - source evidence only

4. `level1.json` / `level2.json`
   - current target entries

5. `work_routing.json`
   - work metadata

## Pipeline Logic

### Part 1: Target Selection

Pick only entries that match the requested filters:

- degree
- classification
- category
- slug
- max entries

Default safe first batch:

- `level1`
- `seed_only,sparse`
- `ritual_flow,preparation,degree_board`

### Part 2: Candidate Source Gate

For each target entry:

1. read `candidate_library_sources`
2. keep only the top sources above a minimum score
3. cap the number of sources per entry

If no source passes the threshold:

- do not call Gemini
- mark the target as `manual_review`

### Part 3: Source Packet Builder

Build a compact packet per target:

1. current target entry
   - slug
   - title
   - category
   - parent topic
   - related topics
   - current summary
   - current practical elements
   - current knowledge links

2. audit context
   - classification
   - sparsity score
   - reasons

3. source excerpts
   - only from selected library chapters
   - each excerpt must include:
     - `work_id`
     - `chapter slug`
     - `source heading`
     - excerpt text

The packet must be small and evidence-focused.

### Part 4: Gemini Call

Gemini receives:

- target entry context
- audit context
- source packet only
- strict instructions:
  - additions only
  - no invented facts
  - no generic background
  - no use of prior world knowledge
  - every addition must be grounded in the provided excerpts

Required output shape:

- `full_summary_addition`
- `practical_elements_additions`
- `symbolic_meaning_addition`
- `knowledge_link_additions`
- `source_notes_additions`

### Part 5: Local Validation

Before writing anything:

1. reject empty or malformed model output
2. reject duplicate additions
3. reject additions with no usable evidence footprint
4. normalize links and source notes

If validation fails:

- do not mutate anything
- mark the target as `failed` or `manual_review`

### Part 6: Staged Patch Output

Write only staged artifacts:

- `level1.patch.json`
- `level2.patch.json`
- `refill_manifest.json`
- `run_status.json`
- `validation_report.json`
- `source_packets/`

No live merge happens here.

### Part 7: Existing Flow Reuse

After refill finishes:

1. review the staged refill patch
2. run Step 6
3. run Step 7

This keeps refill aligned with the system already built.

## Why Mode A Is Safe

Mode A prevents "random Gemini writing" because:

1. targets come from audit, not from guesses
2. sources come from ranked library evidence, not from open prompts
3. no source -> no model call
4. output is additions only
5. final result is staged, not live

## Practical Meaning

The tool should behave like:

- audit-guided
- evidence-constrained
- patch-producing
- review-first

Not like:

- topic generator
- wiki writer from memory
- direct live editor
