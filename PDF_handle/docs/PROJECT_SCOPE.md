# Project Scope

## What This Project Is

`PDF_handle/` is a seven-step PDF-to-site pipeline plus an operational tools layer.
Its job is to turn source PDFs into structured site data, then audit, review, and safely apply improvements.

## What Is In Scope

- extracting PDF content
- chunking and transforming book material
- consolidating book drafts
- mapping source material into `library`, `level1`, and `level2`
- review-first live apply flows
- audits for sparsity, degree purity, routing, and knowledge flow
- preservation-first handling of material that should not remain in its source location

## What Is Not The Main Scope

- frontend app development
- generic document management outside the pipeline
- treating audit reports as automatically applied truth
- silent direct mutation of live site JSON without review artifacts

## Canonical Layers

- Canonical implementation layer:
  `step_01_extract_pdfs.py` to `step_07_site_qa.py`
- Operational tools layer:
  `TOOLS/`
- Prompt assets:
  `prompts/`
- Generated output:
  `consolidated_books/`, `staged_runs/`, `pipeline_runs/`, `qa_reports/`, `merge_backups/`

## Site Version Model

Current reality:

- many workflows still assume workspace root `0.3`
- historical and published copies exist outside a single naming system

Target model:

- one active live root
- zero or more sandbox roots
- dated published snapshots
- archived historical versions

The important future rule for `0.4` and beyond is:

- activating `0.4` should promote a single live root
- previous live data should become a frozen published or archived snapshot
- version numbers should describe releases, not act as the primary navigation system for daily work
