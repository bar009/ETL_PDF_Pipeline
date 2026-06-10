# Phase M.8 Topic Discovery

## Intent

Phase M.8 is the discovery layer that sits before F2/F3.

It does not write canonical degree entries.
It builds a controlled queue of candidate topics from four lanes:

- Level 2 graph reuse
- Level 3 native library seeds
- blocked higher-degree preservation queues
- NotebookLM mindmap intake

NotebookLM intake is strictly validated before any candidate can become actionable.
Malformed NotebookLM candidates stay visible as reviewable artifacts with explicit reasons, but they do not enter the actionable queue.
It also defines the closed-loop lifecycle for discovery candidates:

- `promoted`
- `rejected`
- `deferred`

Those states belong to discovery and review metadata, not direct site mutation.
## Why it exists

Without a separate discovery phase, every new idea immediately turns into content pressure.
That creates chaos:

- too many candidate topics at once
- duplicates that differ only in wording
- Royal Arch or appendant material leaking into Level 3
- NotebookLM outputs getting treated like finished truth

M.8 prevents that by forcing every candidate into a queue with:

- one degree hint
- one topic identity
- one core question
- one next gate
- one review state

## Lanes

### 1. Level 2 graph candidates

Source:

- `level2_topic_candidates.json`
- `phase_m_4_topic_frames.json`
- current `level1.json`
- current `level2.json`

Purpose:

- show what is already built
- show what moved to Level 1
- show which candidates are still open

### 2. Level 3 native candidates

Source:

- `library.json`

Purpose:

- build native third-degree discovery from library evidence
- avoid using Royal Arch queues as fake Level 3 seeds

### 3. Blocked higher-degree candidates

Source:

- `PDF_handle/preservation/future_entries/...`

Purpose:

- preserve higher-degree or research material
- keep it out of native Level 2 and Level 3 until boundaries exist

### 4. NotebookLM intake

Source:

- `experiments/notebooklm_validation/discovery_mindmap_intake.json`

Purpose:

- normalize mindmap/manual discovery into the same queue format
- force dedupe and triage before framing
- keep provenance, evidence, and review state attached to each item

## Non-negotiable gates

1. NotebookLM discovery does not go straight into site data.
2. Royal Arch stays outside native Level 3.
3. Level 3 stays discovery-only until:
   - scope spec exists
   - category set exists
   - runtime lane exists
4. If Level 2 open candidates pile up, stop discovery and triage first.
5. NotebookLM intake must validate against the strict discovery contract before any candidate is marked actionable.
6. Malformed NotebookLM candidates must remain visible as explicit non-actionable review artifacts.
7. Every NotebookLM candidate must end in exactly one lifecycle state:
   - `promoted`
   - `rejected`
   - `deferred`
8. Every terminal state must keep a reason and provenance record.
9. Rejected or deferred candidates stay visible as evidence instead of disappearing silently.

## Default outputs

- `PDF_handle/TOOLS/data/phase_m_8_topic_discovery_queue.json`
- `PDF_handle/TOOLS/data/phase_m_8_topic_discovery_report.json`
- `PDF_handle/TOOLS/data/phase_m_8_topic_discovery_ledger.json`
- `PDF_handle/TOOLS/data/phase_m_8_topic_discovery_review_packet.json`

## NotebookLM usage

Use NotebookLM here for candidate discovery, not verdict-only review.

The safe sequence is:

1. Generate mindmap or chapter clusters in NotebookLM.
2. Normalize them into `discovery_mindmap_intake.json` using the strict candidate contract.
3. Run M.8.
4. Validate each candidate, retain malformed items as explicit review artifacts, and dedupe/triage only the valid actionable candidates.
5. Write a ledger and review packet for NotebookLM candidates.
6. Promote, reject, or defer only through the review packet.
7. Build stable-base addition artifacts only from candidates that end as `promoted`.
8. Review stable-base artifacts before any reusable base write happens.
9. Apply only approved artifacts into the stable topic base.
10. Let future M.8 runs reuse the stable topic base as extra dedupe context.

## NotebookLM intake behavior

The NotebookLM lane now has three outcomes for each candidate:

- `valid` and actionable enough to enter the queue
- `valid` but not actionable yet, so it stays as a reviewable discovery artifact
- `invalid`, which means the candidate failed strict intake validation and stays visible with explicit reasons

Only the first class may flow into the merged actionable queue.
The other two remain in the lane outputs so operators can inspect what was proposed and why it was or was not accepted.

## Promotion And Rejection Ledger

The ledger is the durable record of what happened to each candidate.

It must record:

- candidate identity
- source provenance
- current lifecycle state
- review gate reached
- reason for promotion, rejection, or deferral
- reviewer or gate owner
- timestamp

The ledger is an audit artifact, not a mutation tool.

NotebookLM can feed it.
M.8 can normalize it.
Review can update it.
The ledger itself must not write site data.

## Stable Base Interaction

If `PDF_handle/TOOLS/data/notebooklm_stable_topic_base.json` exists, M.8 may read it as additional catalog context for dedupe and novelty checks.

This does not make the stable topic base canonical site data.

It only lets future discovery avoid rediscovering already approved topic foundations.
