# Release Model

How data moves from canonical content to a published snapshot, what counts as a release,
where it lives, and how to roll back (systemic plan WS12).

## The Flow

```text
staging (review material)
   |  assert_operations_approved - only `approved` operations cross
   v
canonical / work site root          sites/work/<name>/  (configured, never committed)
   |  validate_runtime.py --require-complete --strict must pass
   v
live site root                      sites/live/<name>/  (the root the site serves)
   |  publish: copy + freeze
   v
published snapshot                  sites/published/<release-id>/  (gitignored evidence)
```

Site roots are configured in `sites/site_roots.json` (template:
`sites/site_roots.example.json`). Nothing in this flow is committed to git except
fixtures, schemas, and these documents - see `docs/RULES.md`.

## What Counts As A Release

A release is a **published snapshot directory** that contains, at minimum:

1. the full site root (`data/*.json` including `content.schema.json`)
2. a passing gate report: `validate_runtime.py --site-root <snapshot> --require-complete
   --strict --report <snapshot>/release_gate_report.json`
3. a `run_manifest.json` for the publish run (shape:
   `data/schemas/run_manifest.schema.json`)

If the gate report is missing or failing, the directory is a copy, not a release.

## Naming

Snapshot directories are named `<release-id>-<label>-<YYYY-MM-DD>[-qualifier]`, e.g.
`2.0-live-2026-06-11`. The JS lane already implements this
(`buildPublishedSnapshotName` in `PDF_handle/TOOLS/lib/site_roots.js`); the Python publish
CLI uses the same scheme.

## Publish Procedure

1. run the gate on the work root:
   `python PDF_handle/prod/cli/validate_runtime.py --site-root <work-root> --require-complete --strict`
2. promote work to live through the existing flow (`prod/cli/e2e.py --promote-live
   --review-approved`, or a reviewed manual copy)
3. snapshot live to published:
   `python PDF_handle/prod/cli/publish_snapshot.py --source-site-root <live-root> --published-root <published-root> --release-id <release-id>`
4. the publish CLI runs the gate **again on the snapshot** and stores the report inside it
5. mark the merged staged operations `published` (see
   `PDF_handle/docs/REVIEW_WORKFLOW.md`)

## Rollback

Snapshots are immutable; rollback is re-pointing, not editing:

1. pick the last good snapshot under `sites/published/`
2. copy it over the live root (or re-point `live_site_root` in `sites/site_roots.json`
   at it)
3. run the gate on the restored live root
4. record the rollback in `docs/DECISION_LOG.md` with the snapshot id

Never edit a published snapshot in place - fix forward in the work root and publish a new
snapshot.

## Python Publish CLI

`prod/cli/publish_snapshot.py` performs steps 3-4 in Python. It is offline/local-first:

- it refuses to publish unless the source root passes `validate_runtime.py --require-complete --strict`
- it copies the source site root to the published snapshot directory
- it writes `release_gate_report.json` inside the snapshot
- it writes `run_manifest.json` inside the snapshot
- it refuses to overwrite an existing snapshot directory
