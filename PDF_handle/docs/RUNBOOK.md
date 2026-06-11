# Runbook

Operational commands for the canonical `PDF_handle/prod/` path.

Use this document when you want to run one real source end to end, validate the result,
and publish a local snapshot without touching a live root by accident.

## Rules First

- prefer `python PDF_handle/prod/cli/...` over legacy wrapper scripts
- always pass an explicit `--site-root`
- use a sandbox work root outside the repo
- do not publish if `validate_runtime.py --require-complete --strict` fails
- treat browser QA as the last verification layer, not as a substitute for data validation

## Recommended First Real Source

Use:

- `commentary_on_the_second_Degree.pdf`

Reason:

- it is book-like enough to expose real pipeline behavior
- it already has routing metadata
- it is a narrower first pilot than a larger multi-degree source

Known identifiers:

- `book`: `commentary_on_the_second_Degree`
- `work_id`: `commentary-on-the-second-degree`
- `staging_dir`: `commentary`

## Local Path Setup

Recommended PowerShell setup:

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

$overridesPath = Join-Path $workRoot "data\content.overrides.json"
if (Test-Path $overridesPath) {
  $bundle = Get-Content -Raw $overridesPath | ConvertFrom-Json
  $bundle.site_root = $workRoot
  $bundle | ConvertTo-Json -Depth 100 | Set-Content -Encoding utf8 $overridesPath
}
```

Why this layout:

- the real PDF stays in a gitignored repo intake folder
- the mutable site root stays outside the repo
- published snapshots stay outside the repo

## Step 1: Preprocess Dry Run

Purpose:

- prove Steps 1-4 wiring before provider spend

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

Expected outputs:

- `PDF_handle/extracted_books/<book>/`
- `PDF_handle/chunked_books/<book>/manifest.json`
- `PDF_handle/transformed_books/<book>/`
- `PDF_handle/consolidated_books/commentary_on_the_second_Degree.md`

## Step 2: Preprocess Real Provider Run

Purpose:

- produce the real consolidated source material

Prerequisite:

- `GEMINI_API_KEY` is set

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

## Step 3: Postmerge Into A Sandbox Work Root

Purpose:

- run Steps 5-7 against the sandbox root

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

Expected outputs:

- staged artifacts under `PDF_handle/staged_injection/`
- merge/apply reports
- QA report output under `PDF_handle/qa_reports/`

## Step 4: Runtime Validation Gate

Purpose:

- answer whether the sandbox root is publishable

Command:

```powershell
python PDF_handle/prod/cli/validate_runtime.py `
  --site-root "$workRoot" `
  --require-complete `
  --strict `
  --report "$workRoot\release_gate_report.json"
```

Rule:

- if this fails, stop and fix the failure before publishing

## Step 5: Publish A Local Snapshot

Purpose:

- freeze the validated work root into a dated local snapshot

Command:

```powershell
python PDF_handle/prod/cli/publish_snapshot.py `
  --source-site-root "$workRoot" `
  --published-root "$publishedRoot" `
  --release-id "first-real-run" `
  --label "pilot"
```

Expected outputs inside the snapshot:

- copied site root
- `release_gate_report.json`
- `run_manifest.json`

## Step 6: Optional Browser QA

Run this after Step 4 or Step 5 when you want UI proof on the generated root.

Minimal example with the currently known `level3` password:

```powershell
$env:FM_LEVEL3_PASSWORD = "3"

python PDF_handle/prod/steps/qa.py `
  --site-root "$workRoot" `
  --mode browser
```

If available later, you can also set:

- `FM_LEVEL1_PASSWORD`
- `FM_LEVEL2_PASSWORD`

Current browser QA can unlock shared access through any configured degree password, so
missing `level1`/`level2` is not a blocker for the first pilot.

## Repo Health Checks

Run these from repo root when you want confidence the code path is still healthy:

```powershell
python PDF_handle/prod/check_import_boundaries.py
python -m unittest discover -s PDF_handle/tests -v
```

## If Something Fails

Capture only the real blocker:

- exact command
- exact traceback or failing artifact
- whether the failure is deterministic
- whether the fix belongs in code, config, docs, or data

Decision rule:

1. if preprocess fails, fix the earliest structural issue and rerun the same source
2. if postmerge fails, fix the first broken step and rerun the same source
3. if validation fails, fix the gate-breaking issue before publishing
4. if publish succeeds, do not broaden scope until the pilot has been reviewed
