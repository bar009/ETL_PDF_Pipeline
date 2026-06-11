# English Degree Content Pilot

Purpose: prove that the pipeline can generate canonical English content for `level1`, `level2`, and `level3` from a clean root, without Hebrew carry-over and without publishing unreviewed candidates.

## Clean Root

Create a local sandbox root outside the repo:

```powershell
python PDF_handle/prod/cli/seed_clean_rerun_root.py `
  --shell-root "C:\Users\bar16\OneDrive\Documents\code\sites\live\v0.4-current" `
  --governance-root "C:\Users\bar16\OneDrive\Documents\code\sites\live\v0.4-current" `
  --seed-root "C:\Users\bar16\OneDrive\Documents\code\sites\live\v0.4-current" `
  --target-root "C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\work-english-degree-pilot" `
  --seed-mode categories-only `
  --canonical-language en `
  --strict
```

Then verify:

```powershell
python PDF_handle/prod/cli/language_integrity_audit.py `
  --site-root "C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\work-english-degree-pilot" `
  --strict

python PDF_handle/prod/cli/validate_runtime.py `
  --site-root "C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\work-english-degree-pilot" `
  --require-complete `
  --strict
```

## Source Order

Run one source at a time.

1. `Basic Masonic Education Course.pdf` for the first probe, but do not publish automatically. The local pilot showed this file contains substantial Master Mason material despite its general title.
2. `Color-Symbolism.pdf` for a level2-focused symbolic source.
3. `Allegories_of_Hiram_Abiff.pdf` for a level3-focused source.

## First Probe Commands

Copy only the selected source into `PDF_handle/PDF_files`, then run:

```powershell
python PDF_handle/prod/cli/preprocess.py `
  --book "Basic Masonic Education Course" `
  --provider dry-run `
  --force-step1 `
  --force-step2 `
  --force-step3 `
  --force-step4

python PDF_handle/prod/steps/stage.py `
  --site-root "C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\work-english-degree-pilot" `
  --book "Basic Masonic Education Course" `
  --provider heuristic `
  --staging-dir "PDF_handle\staged_runs\basic-education-pilot-guarded" `
  --max-sections-per-work 20
```

Audit the staged output:

```powershell
python PDF_handle/prod/cli/language_integrity_audit.py `
  --site-root "C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\work-english-degree-pilot" `
  --staging-dir "PDF_handle\staged_runs\basic-education-pilot-guarded" `
  --strict
```

## Acceptance Criteria

- `language_integrity_audit.py --strict` passes before and after Step 5.
- `companion_candidates.json` uses canonical English fields such as `short_summary`, `full_summary`, and `candidate_lesson`.
- No new canonical candidate contains Hebrew script in protected fields.
- A source may only create candidates for degrees explicitly listed in `work_routing.json`.
- Publish happens only after review/approval, never directly from heuristic or raw Gemini output.
- Step 6 enforces this structurally: selected operations and companion candidates pass
  through `approve_operator_selection` and the `assert_operations_approved` door; staged
  items without `review_state` are blocked unless `--allow-unreviewed-legacy` is passed.
  Staging dirs created before 2026-06-11 (e.g. `basic-education-pilot*`) carry companions
  without `review_state` — regenerate them with a fresh Step 5 run rather than using the
  legacy flag.

## Current Pilot Finding

The first dry-run created 14 chunks and 19 Step 5 sections. After the out-of-route title guard, Step 5 produced 5 `level1` companion candidates and blocked obvious `level3` headings such as `THE MASTER MASON DEGREE`, `THE LION OF THE TRIBE OF JUDAH`, and `Questions for the Master Mason`.

Do not publish this source as level1 content without manual review. The next useful run is a cleaner level2 symbolic source (`Color-Symbolism.pdf`) or a true level1 source if one is selected.
