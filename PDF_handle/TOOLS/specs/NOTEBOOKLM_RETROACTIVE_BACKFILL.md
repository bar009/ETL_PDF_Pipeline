# NotebookLM Retroactive Backfill

Purpose: turn reviewed stable-topic-base discoveries into reviewable retroactive backfill proposals for existing site content.

## What This Lane Does

This lane reads:

- `PDF_handle/TOOLS/data/notebooklm_stable_topic_base.json`
- the selected site root datasets
  - `library.json`
  - `level1.json`
  - `level2.json`
  - `level3.json`

It then produces:

- `PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/queue.json`
- `PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/review_packet.json`
- `PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/report.json`
- `PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/seed_packet.json`

## Isolation Guard

This lane requires the explicit flag:

- `--allow-isolated-backfill`

without it, the scripts should stop immediately.

That guard exists so this lane cannot be confused with canonical ETL or accidentally folded into an existing runner.

## What It Is Allowed To Do

- detect whether a stable topic already appears to exist in current site data
- suggest when an existing entry should be expanded instead of creating a new entry
- suggest when a companion-style relation candidate is more appropriate than a full new entry
- suggest when a stable topic should seed a new staged backfill item

## What It Is Not Allowed To Do

- mutate live site JSON directly
- auto-approve new entries
- bypass Step 5 or Step 6 review gates
- treat stable-base discovery as equivalent to canonical site truth

## Coverage Outcomes

Each stable-base entry is classified into one of these states:

- `already_present`
- `existing_entry_needs_enrichment`
- `adjacent_existing_entry`
- `new_backfill_seed`
- `blocked_missing_dataset`

## Recommended Actions

- `skip_existing_coverage`
- `expand_existing_entry`
- `attach_companion_relation_candidate`
- `seed_new_entry_from_stable_base`
- `defer_until_target_dataset_exists`

## Review Contract

Operators review `notebooklm_retroactive_backfill/review_packet.json` before any later backfill builder is allowed to convert proposals into staged patch material.

Approved proposals may then be converted into `notebooklm_retroactive_backfill/seed_packet.json`.

The seed packet is still not live mutation.
It is the handoff surface for a later staged-patch builder.

## Staging Bundle

The next isolated builder may convert the approved seed packet into an isolated staging bundle under:

- `PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/staging_bundle/`

That bundle may contain:

- `work_manifest.generated.json`
- `library.patch.json`
- `level1.patch.json`
- `level2.patch.json`
- `level3.patch.json`
- `companion_candidates.json`
- preview candidate datasets

This is still review-first and still outside canonical runtime defaults.

## Expansion Batches

The next discovery cycles should be prepared as explicit batches before they are run.

Recommended split:

- Batch 2: native `level2` Fellow Craft expansion
- Batch 3: ritual-context and ceremonial-placement expansion across `level1`, `level2`, and `level3`

Batch 2 should deepen the structural body of the site around:

- winding stairs
- middle chamber
- Boaz and Jachin
- five orders of architecture
- five human senses
- seven liberal arts and sciences

Batch 3 should improve explicit ritual placement and later framing around:

- apron, cable-tow, hoodwink
- ashlar, gavel, trestle-board
- Hiram Abiff, acacia, coffin, grave
- later context notes only when source-grounded

Neither batch may write live site JSON directly.
Both batches must remain review-first and feed back through the existing intake and backfill lanes.
