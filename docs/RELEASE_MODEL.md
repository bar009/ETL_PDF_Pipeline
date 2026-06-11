# Release Model

How data moves from reviewed staging into a validated snapshot.

## The Flow

```text
staging / review artifacts
   |  only approved operations cross
   v
work site root
   |  validate_runtime.py --require-complete --strict
   v
live site root (optional operational promotion)
   |  copy + freeze
   v
published snapshot
```

Site roots are configured explicitly or passed via `--site-root`. Runtime roots and
published snapshots are not committed to git.

## What Counts As A Release

A release is a published snapshot directory that contains:

1. the full copied site root
2. a passing `release_gate_report.json`
3. a `run_manifest.json`

If the gate report is missing or failing, the directory is only a copy.

## Naming

Snapshots use:

- `<release-id>-<label>-<YYYY-MM-DD>`
- optional qualifier at the end if needed

Example:

- `first-real-run-pilot-2026-06-11`

## Publish Procedure

### Publish directly from a validated work root

```powershell
python PDF_handle/prod/cli/validate_runtime.py `
  --site-root "<work-root>" `
  --require-complete `
  --strict `
  --report "<work-root>\release_gate_report.json"

python PDF_handle/prod/cli/publish_snapshot.py `
  --source-site-root "<work-root>" `
  --published-root "<published-root>" `
  --release-id "<release-id>" `
  --label "<label>"
```

### Promote through a live root first

Use this only when you intentionally maintain a separate live root:

1. validate the work root
2. promote work to live through the reviewed flow
3. run `publish_snapshot.py` against the live root

## Guarantees From `publish_snapshot.py`

The Python publish CLI is offline/local-first:

- it refuses to publish if the source root fails strict runtime validation
- it copies the source site root into a new dated snapshot directory
- it writes `release_gate_report.json` inside the snapshot
- it writes `run_manifest.json` inside the snapshot
- it refuses to overwrite an existing snapshot directory

## Rollback

Snapshots are immutable. Rollback means re-pointing or restoring a known-good snapshot:

1. pick the last good snapshot
2. copy it over the live root or re-point the configured live root
3. rerun the validation gate
4. record the rollback in `docs/DECISION_LOG.md`

Never edit a published snapshot in place.
