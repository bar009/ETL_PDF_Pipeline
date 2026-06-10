# PDF Knowledge Pipeline

This folder now contains a repeatable seven-step pipeline. Each step writes its own output directory so you can rerun one stage without redoing everything else.

## Directory Layout

```text
PDF_handle/
  main.py
  step_01_extract_pdfs.py
  step_02_chunk_markdown.py
  step_03_transform_chunks.py
  step_04_consolidate_books.py
  step_05_map_and_stage.py
  step_06_apply_reviewed_merge.py
  step_07_site_qa.py
  pipeline_utils.py
  stage5_utils.py
  work_routing.json
  prompts/
    archivist_system.txt
    degree_mapper_system.txt
  PDF_files/
  extracted_books/
  chunked_books/
  transformed_books/
  consolidated_books/
  staged_injection/
```

## TOOLS Hub

`PDF_handle/TOOLS/` is the maintenance and orchestration layer.

- `step_01_extract_pdfs.py` .. `step_07_site_qa.py` remain the canonical implementation layer.
- `PDF_handle/TOOLS/run_preprocess_01_04.py` wraps the preprocess route without replacing the underlying step scripts.
- `PDF_handle/TOOLS/run_postmerge_05_07.py` wraps the current `5 -> 7` runner.
- `PDF_handle/TOOLS/audit_sparse_entries.py` is a read-only coverage audit plus refill queue generator.

This keeps orchestration and reporting separate from ETL logic:

- `step_01..07` = source of truth
- `TOOLS/*` = wrappers, manifests, audits, reports

Audit output is diagnostic only. It is never treated as enrichment already applied to the site.

## Step 1: Extract PDFs

Purpose: Convert each PDF into Markdown, metadata, and extracted images using the existing `marker` setup.

Command:

```bash
python PDF_handle/step_01_extract_pdfs.py
```

Useful options:

```bash
python PDF_handle/step_01_extract_pdfs.py --book "commentary_on_the_second_Degree"
python PDF_handle/step_01_extract_pdfs.py --force
```

Output:

- `PDF_handle/extracted_books/<book>/<book>.md`
- `PDF_handle/extracted_books/<book>/<book>_meta.json`
- extracted images beside them

## Step 2: Chunk Markdown

Purpose: Split extracted Markdown into paragraph-aware sliding-window chunks.

Default chunk settings:

- `min_chars=4000`
- `max_chars=6000`
- `overlap=500`

Command:

```bash
python PDF_handle/step_02_chunk_markdown.py
```

Useful options:

```bash
python PDF_handle/step_02_chunk_markdown.py --book "commentary_on_the_second_Degree"
python PDF_handle/step_02_chunk_markdown.py --min-chars 4500 --max-chars 5500 --overlap 500
python PDF_handle/step_02_chunk_markdown.py --force
```

Output:

- `PDF_handle/chunked_books/<book>/manifest.json`
- `PDF_handle/chunked_books/<book>/chunks/chunk_0001.md`
- `PDF_handle/chunked_books/<book>/chunks/chunk_0002.md`

The manifest stores source paths, chunk config, and char ranges so the process is traceable.

## Step 3: Transform Chunks

Purpose: Send each chunk through an API loop and save every transformed chunk independently.

Default prompt:

- `PDF_handle/prompts/archivist_system.txt`

Dry-run mode:

```bash
python PDF_handle/step_03_transform_chunks.py --provider dry-run
```

Gemini mode:

```bash
pip install -U google-genai
set GEMINI_API_KEY=YOUR_KEY
python PDF_handle/step_03_transform_chunks.py --provider gemini --model gemini-2.5-flash
```

Useful options:

```bash
python PDF_handle/step_03_transform_chunks.py --provider gemini --book "commentary_on_the_second_Degree"
python PDF_handle/step_03_transform_chunks.py --provider gemini --sleep-seconds 2 --max-retries 5
python PDF_handle/step_03_transform_chunks.py --provider gemini --force
```

Output:

- `PDF_handle/transformed_books/<book>/manifest.json`
- `PDF_handle/transformed_books/<book>/chunks/chunk_0001.md`
- `PDF_handle/transformed_books/<book>/records/chunk_0001.json`

Each chunk is checkpointed. If one chunk fails, rerun the command and it will skip completed chunks unless `--force` is used.

## Step 4: Consolidate Book Drafts

Purpose: Merge transformed chunk files into one book-level Markdown draft.

Command:

```bash
python PDF_handle/step_04_consolidate_books.py
```

Useful options:

```bash
python PDF_handle/step_04_consolidate_books.py --book "commentary_on_the_second_Degree"
python PDF_handle/step_04_consolidate_books.py --force
```

Output:

- `PDF_handle/consolidated_books/<book>.md`
- `PDF_handle/consolidated_books/<book>_meta.json`

The consolidation step performs deterministic seam cleanup for obvious overlap duplicates. If the model rewrites overlap sections very differently, a later semantic consolidation pass may still be useful.

## Step 5: Map And Stage Into Site Schema

Purpose: Build staged `library`, `level1`, and `level2` candidate files from consolidated books without writing directly into `0.3/data/`.

What this step does:

- audits that each routed consolidated book has both `.md` and `_meta.json`
- normalizes `library.json`, `level1.json`, and legacy `level2.json`
- validates the normalized base files against `content.schema.json`
- creates preservation-first `book` and `chapter` entries for the library lane
- runs either heuristic matching or Gemini-based structured mapping for degree enrichment
- writes staged patch files, companion candidates, and full candidate JSON files

Heuristic mode:

```bash
python PDF_handle/step_05_map_and_stage.py --provider heuristic
```

Gemini mode:

```bash
pip install -U google-genai
set GEMINI_API_KEY=YOUR_KEY
python PDF_handle/step_05_map_and_stage.py --provider gemini --model gemini-2.5-flash
```

Useful options:

```bash
python PDF_handle/step_05_map_and_stage.py --provider heuristic --book "commentary_on_the_second_Degree"
python PDF_handle/step_05_map_and_stage.py --provider heuristic --mapping-max-chars 6500
python PDF_handle/step_05_map_and_stage.py --provider gemini --book "deeper-meaning-of-fc-degree"
```

Output:

- `PDF_handle/staged_injection/base_library.normalized.json`
- `PDF_handle/staged_injection/base_level1.normalized.json`
- `PDF_handle/staged_injection/base_level2.normalized.json`
- `PDF_handle/staged_injection/base_validation_report.json`
- `PDF_handle/staged_injection/work_manifest.generated.json`
- `PDF_handle/staged_injection/library.patch.json`
- `PDF_handle/staged_injection/level1.patch.json`
- `PDF_handle/staged_injection/level2.patch.json`
- `PDF_handle/staged_injection/companion_candidates.json`
- `PDF_handle/staged_injection/library.candidate.json`
- `PDF_handle/staged_injection/level1.candidate.json`
- `PDF_handle/staged_injection/level2.candidate.json`
- `PDF_handle/staged_injection/validation_report.json`
- `PDF_handle/staged_injection/link_report.json`
- `PDF_handle/staged_injection/coverage_report.json`

The Step 5 output is staged only. It is meant for review before any merge back into `0.3/data/`. `0.2` remains frozen.

## Step 6: Apply Reviewed Merge

Purpose: Merge approved Step 5 staged artifacts into the live site JSON files in `0.3/data/`.

What this step does:

- loads staged library candidate and patch files
- applies selected `level1` / `level2` patch operations
- optionally merges approved companion candidates
- writes preview JSON files and validation reports
- optionally writes live data after backup when `--apply-live` is used

Library-only preview:

```bash
python PDF_handle/step_06_apply_reviewed_merge.py --site-root 0.3 --merge-library
```

Preview library plus all staged `level1` operations:

```bash
python PDF_handle/step_06_apply_reviewed_merge.py --site-root 0.3 --merge-library --approve-level1 all
```

Preview using an approval file:

```bash
python PDF_handle/step_06_apply_reviewed_merge.py --merge-library --approve-level1 PDF_handle/approvals/level1.json
```

Apply merged results to live data after backup:

```bash
python PDF_handle/step_06_apply_reviewed_merge.py --site-root 0.3 --merge-library --approve-level1 all --apply-live
```

Output:

- `PDF_handle/staged_injection/step6_review_template.json`
- `PDF_handle/staged_injection/step6_merge_report.json`
- `PDF_handle/staged_injection/step6_validation_report.json`
- `PDF_handle/staged_injection/step6_library.preview.json`
- `PDF_handle/staged_injection/step6_level1.preview.json`
- `PDF_handle/staged_injection/step6_level2.preview.json`
- optional backups in `PDF_handle/merge_backups/0.3/<timestamp>/`

## Step 7: QA The Live Site

Purpose: Validate the live `0.3` site data and run browser smoke tests against the real site UI after Step 6.

Command:

```bash
python PDF_handle/step_07_site_qa.py --site-root 0.3 --mode full
```

Useful options:

```bash
python PDF_handle/step_07_site_qa.py --site-root 0.3 --mode data
python PDF_handle/step_07_site_qa.py --site-root 0.3 --mode browser
python PDF_handle/step_07_site_qa.py --site-root 0.3 --work-id duncans-ritual-monitor-1866
```

Output:

- `PDF_handle/qa_reports/0.3/<timestamp>/qa_data_summary.json`
- `PDF_handle/qa_reports/0.3/<timestamp>/qa_data_findings.json`
- `PDF_handle/qa_reports/0.3/<timestamp>/qa_browser_summary.json`
- `PDF_handle/qa_reports/0.3/<timestamp>/qa_report.html`

Approval file notes:

- Use `"all"` to approve all staged operations of a degree.
- Or provide a JSON file containing any of:
  - `marker_ids`
  - `slugs`
  - `work_ids`
  - `section_ids`
  - `candidate_slugs`
  - `operations`
  - `entries`

## Recommended Run Order

```bash
python PDF_handle/step_01_extract_pdfs.py
python PDF_handle/step_02_chunk_markdown.py
python PDF_handle/step_03_transform_chunks.py --provider gemini --model gemini-2.5-flash
python PDF_handle/step_04_consolidate_books.py
python PDF_handle/step_05_map_and_stage.py --provider heuristic
python PDF_handle/step_06_apply_reviewed_merge.py --site-root 0.3 --merge-library
python PDF_handle/step_07_site_qa.py --site-root 0.3 --mode full
```

## Notes

- Use `dry-run` first to verify the pipeline shape without spending API credits.
- The pipeline is resumable by default.
- Step 5 does schema staging and review artifacts; it still does not write into the live site data files.
- Step 6 defaults to `0.3` and refuses to write to frozen `0.2` unless `--allow-legacy-target` is used.
- Step 7 is the final readiness check for `0.3`.
