# First Real Run Plan

This document defines the first real source run we should do after the systemic cleanup.

The goal is not to process everything. The goal is to run one real source end to end,
see where the pipeline hurts in practice, and strengthen only the parts that break or stay
unclear.

## Recommended Source

Use:

- `commentary_on_the_second_Degree.pdf`

Why this one:

- it is still small enough for a first real run, but it is more book-like than the FC lecture source
- it already has a routing entry in `PDF_handle/work_routing.json`
- it is scoped to `level2`, so the blast radius is still narrower than a multi-degree source
- it should expose real extraction, chunking, staging, and merge behavior without turning the
  first run into a stress test
- unlike `Deeper meaning of FC Degree.pdf`, it is not primarily an interpretive lecture / worksheet-style source

Important route behavior:

- this source is marked as `source_genre = enrichment_source` in `PDF_handle/work_routing.json`
- that means it is expected to enrich existing `level2` topics, not seed a thin root from scratch
- for this source, a richer seeded work root is required; `0.3` is too sparse and causes Step 5 to reject almost everything

Known local source path found during repo review:

- `C:\Users\bar16\OneDrive\Documents\code\.worktrees\prod-close-integration-snapshot\PDF_handle\PDF_files\commentary_on_the_second_Degree.pdf`

Routing data already exists:

- `source_book_name`: `commentary_on_the_second_Degree`
- `work_id`: `commentary-on-the-second-degree`
- `staging_dir`: `commentary`

## Local Paths For The Pilot

Use explicit local paths for the first run. Do not depend on `sites/site_roots.json` yet.

Recommended local working paths:

- PDF intake inside the clean repo, which is already gitignored:
  - `C:\Users\bar16\OneDrive\Documents\code-clean-start\PDF_handle\PDF_files\commentary_on_the_second_Degree.pdf`
- work site root outside the clean repo, to avoid committing large runtime JSON by accident:
  - `C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\work-v04-commentary`
- published snapshots outside the clean repo:
  - `C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\published`

Bootstrap the work site root by copying the richer current live root:

- source bootstrap root:
  - `C:\Users\bar16\OneDrive\Documents\code\sites\live\v0.4-current`

After copying, normalize the copied override bundle so it points to the copied sandbox root:

- update `data/content.overrides.json` inside the copy so `site_root` matches the copied path
- if you use the repo helper later, prefer `PDF_handle/prod/cli/seed_clean_rerun_root.py` over a raw Explorer copy

Reason for using an external sandbox path:

- `PDF_handle/PDF_files/` is gitignored, so the real PDF is safe there
- generated ETL artifacts under `PDF_handle/` are gitignored
- arbitrary site roots under `code-clean-start/sites/` are **not** ignored, so a local work
  root should stay outside the repo for this first run

## PowerShell Setup

```powershell
$sourcePdf = "C:\Users\bar16\OneDrive\Documents\code\.worktrees\prod-close-integration-snapshot\PDF_handle\PDF_files\commentary_on_the_second_Degree.pdf"
$repoPdfDir = "C:\Users\bar16\OneDrive\Documents\code-clean-start\PDF_handle\PDF_files"
$workRoot = "C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\work-v04-commentary"
$publishedRoot = "C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\published"
$bootstrapRoot = "C:\Users\bar16\OneDrive\Documents\code\sites\live\v0.4-current"

New-Item -ItemType Directory -Force -Path $repoPdfDir | Out-Null
New-Item -ItemType Directory -Force -Path $publishedRoot | Out-Null
Copy-Item -LiteralPath $sourcePdf -Destination $repoPdfDir -Force

if (Test-Path $workRoot) { Remove-Item -LiteralPath $workRoot -Recurse -Force }
Copy-Item -LiteralPath $bootstrapRoot -Destination $workRoot -Recurse

$overridesPath = Join-Path $workRoot "data\\content.overrides.json"
if (Test-Path $overridesPath) {
  $bundle = Get-Content -Raw $overridesPath | ConvertFrom-Json
  $bundle.site_root = $workRoot
  $bundle | ConvertTo-Json -Depth 100 | Set-Content -Encoding utf8 $overridesPath
}
```

## Execution Order

### 1. Preprocess Dry Run

Purpose:

- verify Steps 1-4 wiring, file naming, extraction flow, and artifact layout
- avoid spending provider calls before the local path assumptions are proven

Command:

```powershell
python PDF_handle/prod/cli/preprocess.py `
  --book "commentary_on_the_second_Degree" `
  --provider dry-run `
  --force-step1 `
  --force-step2 `
  --force-step3 `
  --force-step4
```

Success signals:

- a new extracted book directory exists under `PDF_handle/extracted_books/`
- chunk manifests and chunk files exist under `PDF_handle/chunked_books/`
- transformed placeholder records exist under `PDF_handle/transformed_books/`
- a consolidated markdown file exists under `PDF_handle/consolidated_books/`

If this fails, inspect first:

- `PDF_handle/extracted_books/<book>/`
- `PDF_handle/chunked_books/<book>/manifest.json`
- the CLI traceback

### 2. Preprocess Real Provider Run

Purpose:

- prove that the real source can complete Steps 1-4 with the actual provider path

Prerequisite:

- `GEMINI_API_KEY` is set in the shell

Command:

```powershell
$env:GEMINI_API_KEY = "<your-key>"

python PDF_handle/prod/cli/preprocess.py `
  --book "commentary_on_the_second_Degree" `
  --provider gemini `
  --model gemini-2.5-flash `
  --force-step3 `
  --force-step4
```

Success signals:

- transformed records are real provider outputs, not dry-run placeholders
- `PDF_handle/consolidated_books/commentary_on_the_second_Degree.md` exists and looks coherent

Primary pain points to watch:

- extraction quality
- chunk sizes too large or too small
- provider failures or malformed payloads
- consolidation duplication or seam problems

### 3. Postmerge On A Local Work Root

Purpose:

- run staging, preview merge, and QA against a sandbox work root without touching live data

Command:

```powershell
python PDF_handle/prod/cli/postmerge.py `
  --site-root "$workRoot" `
  --work-id "commentary-on-the-second-degree" `
  --provider heuristic `
  --force-step5 `
  --force-step6 `
  --force-step7 `
  --skip-exploration-review
```

Why `heuristic` first:

- it isolates ETL/data-shape issues before introducing another provider-dependent stage
- for this specific source, the important dependency is the seeded `level2` target set, not a second provider call

Success signals:

- staged files exist under `PDF_handle/staged_injection/`
- Step 6 preview files exist
- QA reports exist

Primary pain points to watch:

- work routing mismatch
- staged operations not targeting the expected degree
- merge preview drift
- relation or provenance failures in QA

### 4. Validation Gate

Purpose:

- answer one question clearly: is the sandbox work root publishable?

Command:

```powershell
python PDF_handle/prod/cli/validate_runtime.py `
  --site-root "$workRoot" `
  --require-complete `
  --strict `
  --report "$workRoot\\release_gate_report.json"
```

Interpretation:

- if this fails, do **not** publish
- the first failing category becomes the next fix target

Expected failure classes, if they appear:

- schema/data shape
- duplicate or unstable slugs
- missing relations
- missing provenance
- degree completeness issues

### 5. Publish Snapshot Only If The Gate Is Green

Purpose:

- freeze the successful work root into a local published snapshot with a gate report and run manifest

Command:

```powershell
python PDF_handle/prod/cli/publish_snapshot.py `
  --source-site-root "$workRoot" `
  --published-root "$publishedRoot" `
  --release-id "first-real-run" `
  --label "pilot"
```

Success signals:

- a new snapshot directory exists under `$publishedRoot`
- it contains `release_gate_report.json`
- it contains `run_manifest.json`

## What To Record After The Run

For the first real run, capture only real pain points. Do not turn every rough edge into a task.

Record these categories:

- extraction problems
- chunking problems
- provider problems
- staging/merge problems
- validation/gate problems
- review-state confusion
- site-root/path confusion

For each issue, capture:

- exact command
- exact failing file or artifact
- whether the failure is deterministic
- whether the fix belongs in code, config, docs, or data

## Decision Rule After The Pilot

After the run, do only one of these:

1. if the run fails early, fix the earliest structural blocker and rerun the same source
2. if the run reaches the gate but fails validation, fix the validation-causing issue and rerun
3. if the run passes and publishes cleanly, keep the pipeline as-is and move to a second source only then

Do not broaden scope during this pilot:

- no second source
- no big refactor
- no React changes unless the runtime export itself is wrong
