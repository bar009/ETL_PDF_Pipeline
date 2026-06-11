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

## Proven E2E Runbook (2026-06-11, Color-Symbolism)

This exact sequence ran green end to end: fresh root → staged Gemini content →
live merge → both gates. It is the canonical template for the next source.

Preconditions:

- `GEMINI_API_KEY` is set in the environment. If it lives in `.env`, the value
  must not be wrapped in quotes — the providers read it verbatim and Google
  rejects a quoted key as `API_KEY_INVALID`.
- The consolidated markdown for the book has **semantic headings** (one `##`
  per concept). Marker/OCR output sectioned as `## Page N` produces
  `fragmentary_topic` sections and zero degree content; restructure the
  consolidated file first.
- The source has a routing row in `work_routing.json`; candidates are only
  created for degrees in `applies_to_degrees`.

```powershell
# 0) Fresh sandbox root (rename the old root away first; never reuse a hybrid root).
#    --categories-template installs the versioned 9-category taxonomy per degree.
python PDF_handle/prod/cli/seed_clean_rerun_root.py `
  --shell-root  "<seed shell root>" --governance-root "<seed shell root>" `
  --seed-root   "<seed shell root>" `
  --target-root "<sandbox root>" `
  --seed-mode categories-only --canonical-language en `
  --categories-template "PDF_handle\prod\templates\degree_categories.v1.json" `
  --allow-dirty-seed --strict

# 1) Gate the empty root
python PDF_handle/prod/cli/validate_runtime.py --site-root "<sandbox root>" --require-complete --strict
python PDF_handle/prod/cli/language_integrity_audit.py --site-root "<sandbox root>" --strict

# 2) Preprocess (Steps 1-4) with Gemini, then restructure the consolidated md if needed
python PDF_handle/prod/cli/preprocess.py --book "<Book>" --provider gemini --force-step3 --force-step4

# 3) Stage (Step 5) with Gemini against the fresh root — fills short_summary,
#    symbolic_meaning, candidate_lesson on every candidate
python PDF_handle/prod/steps/stage.py `
  --site-root "<sandbox root>" --book "<Book>" --provider gemini `
  --staging-dir "PDF_handle\staged_runs\<book>-e2e" --max-sections-per-work 30

# 4) Review companion_candidates.json, then merge — library lane and approved
#    candidates must land together, and only --apply-live writes the site root
python PDF_handle/prod/steps/apply.py `
  --site-root "<sandbox root>" --staging-dir "PDF_handle\staged_runs\<book>-e2e" `
  --merge-library --approve-companions all --apply-live

# 5) Structure: one hub per category, orphan topics adopted under their hub.
#    Dry-run first (no --apply) to inspect the plan; idempotent on re-run.
python PDF_handle/prod/cli/build_degree_structure.py --site-root "<sandbox root>" --apply

# 6) Gates on the merged root
python PDF_handle/prod/cli/validate_runtime.py --site-root "<sandbox root>" --require-complete --strict
python PDF_handle/prod/cli/language_integrity_audit.py --site-root "<sandbox root>" `
  --staging-dir "PDF_handle\staged_runs\<book>-e2e" --strict
```

Result on Color-Symbolism: 8 `level2` entries (status `draft`, real English
summaries/symbolic meaning/lessons, `knowledge_links` wired to their library
chapters), 11 library entries, zero dangling links, both gates green.

Step 6 traps this runbook closes (enforced in code since the same date):

- selected operations that link to staged library chapters fail early unless
  `--merge-library` is part of the same merge
- without `--apply-live` nothing is written to the site root; the run logs
  `mode=preview-only` and a failed validation exits non-zero

## Second Source Confirmed: Allegories of Hiram Abiff (level3)

The same runbook ran green on the level3 source on the same day, on top of the
Color-Symbolism root. Two source-specific notes:

- the raw consolidated markdown carried whole pages translated into Hebrew and
  Arabic by the transform step, plus duplicated English passages — the
  restructured semantic markdown keeps English only, or the language gate fails
- all 11 content sections were classified `later_degree_candidate` → `level3`,
  matching the routing row (`applies_to_degrees: [library, level3]`); the
  References section was rejected as noise

Final pilot root state: `level2` 8 entries, `level3` 11 entries, `library` 24
entries, `validate_runtime --require-complete --strict` green (19 checks
including `work_library_coverage`), language audit green. The root was then
published as a frozen snapshot via `publish_snapshot.py`
(`english-pilot-sandbox-2026-06-11`), which wrote `release_gate_report.json`
and `run_manifest.json` inside the snapshot and refuses to overwrite it.

## One-Command Orchestrator Path

`prod/cli/postmerge.py` runs Steps 5→6→7 (including QA with a browser smoke)
in one command and produces the same result as the manual runbook:

```powershell
python PDF_handle/prod/cli/postmerge.py `
  --site-root "<sandbox root>" --work-id <work-id> `
  --provider gemini --include-companions
```

The orchestrated Step 6 always passes `--merge-library --apply-live` and the
approval flags derived from the staged counts. Use the orchestrator for
sandbox/work roots; live publishes stay manual so the review door is a human
decision.
