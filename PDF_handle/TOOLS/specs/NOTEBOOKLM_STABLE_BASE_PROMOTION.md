# NotebookLM Stable Base Promotion

## Purpose

This flow carries a reviewed NotebookLM discovery candidate into a reusable stable topic base without writing directly to live site JSON.

The stable topic base is discovery context, not canonical site truth.

## Tools

1. `PDF_handle/TOOLS/run_phase_m_8_topic_discovery.js`
2. `PDF_handle/TOOLS/build_notebooklm_stable_base_additions.js`
3. `PDF_handle/TOOLS/apply_notebooklm_stable_base_additions.js`

## Flow

### Step 1. Run M.8 discovery

Command:

```powershell
node PDF_handle/TOOLS/run_phase_m_8_topic_discovery.js
```

Outputs:

- `PDF_handle/TOOLS/data/phase_m_8_topic_discovery_queue.json`
- `PDF_handle/TOOLS/data/phase_m_8_topic_discovery_report.json`
- `PDF_handle/TOOLS/data/phase_m_8_topic_discovery_ledger.json`
- `PDF_handle/TOOLS/data/phase_m_8_topic_discovery_review_packet.json`

What happens:

- intake is validated
- invalid NotebookLM candidates stay visible
- valid candidates are deduped and triaged
- every NotebookLM candidate is recorded in the ledger
- the review packet is created for explicit human decisions

### Step 2. Review candidate outcomes

Edit:

- `PDF_handle/TOOLS/data/phase_m_8_topic_discovery_review_packet.json`

Allowed decisions:

- `promoted`
- `rejected`
- `deferred`
- `pending_review`

Important rule:

- only `promoted` candidates may become stable-base addition artifacts

### Step 3. Build stable-base addition artifacts

Command:

```powershell
node PDF_handle/TOOLS/build_notebooklm_stable_base_additions.js
```

Outputs:

- updated `PDF_handle/TOOLS/data/phase_m_8_topic_discovery_ledger.json`
- `PDF_handle/TOOLS/data/notebooklm_stable_base_additions/index.json`
- `PDF_handle/TOOLS/data/notebooklm_stable_base_additions/artifacts/*.json`
- `PDF_handle/TOOLS/data/notebooklm_stable_base_review_packet.json`

What happens:

- the ledger is updated with final candidate states
- promoted candidates are frozen into reviewable stable-base addition artifacts
- each artifact preserves provenance and approval history
- no stable topic base write happens yet

### Step 4. Review stable-base artifacts

Edit:

- `PDF_handle/TOOLS/data/notebooklm_stable_base_review_packet.json`

Allowed decisions:

- `approved`
- `deferred`
- `rejected`
- `pending_review`

Important rule:

- approved means approved for the stable topic base only
- this is not a Step 6 or live-site mutation path

### Step 5. Apply approved artifacts to the stable topic base

Command:

```powershell
node PDF_handle/TOOLS/apply_notebooklm_stable_base_additions.js
```

Outputs:

- updated artifact files with final review state
- updated `PDF_handle/TOOLS/data/notebooklm_stable_base_additions/index.json`
- `PDF_handle/TOOLS/data/notebooklm_stable_topic_base.json`
- `PDF_handle/TOOLS/data/notebooklm_stable_base_apply_report.json`

What happens:

- only approved artifacts are applied
- slug conflicts are deferred instead of overwritten
- the stable topic base becomes reusable context for future discovery

## Safety Properties

- discovery does not write live site data
- promoted does not mean applied
- approved for stable base does not mean approved for live mutation
- provenance stays attached from intake to stable-base entry
- rejected and deferred candidates remain auditable
