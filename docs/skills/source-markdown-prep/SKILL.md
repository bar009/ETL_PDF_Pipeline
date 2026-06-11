---
name: source-markdown-prep
description: Convert raw OCR/page-based consolidated book markdown into stage-ready semantic sections for the Masonic ETL pipeline, using PDF_handle/TOOLS/restructure_page_md_to_semantic.py. Use whenever a consolidated_books/*.md file has "## Page N" headings, the user asks to prepare/restructure/clean a book or PDF markdown for the pipeline, Step 5 produces a flood of fragmentary_topic sections, or a new source needs heading curation (pause/commentary lectures, chapter books, ritual narratives). Trigger before any Gemini staging of a new source.
---

# Source Markdown Prep

Goal: a markdown file in `PDF_handle/consolidated_books/` where every `##`
heading is one knowledge unit. Step 5 splits on `##` — page headings produce
micro-sections that all classify `fragmentary_topic` and die.

Full decision tree with worked examples:
`C:\Users\bar16\OneDrive\Documents\code-clean-start\PDF_handle\docs\SOURCE_PREP_RUNBOOK.md`
— read it before working on a new source shape.

## Quick path

1. Diagnose: `grep "^## " file.md | head -30` and `wc -l file.md`.
2. Match the shape to a case:

| Shape | Recipe |
|---|---|
| `## Page N` everywhere | drop page/running-header patterns, `--min-section-chars 600` |
| "Nth Pause: / Commentary:" lecture | add `--pause-commentary --dedup-paragraphs` |
| Chapter book, run-on OCR lines | chapter-prefix pre-pass, then `--max-section-chars 12000` |
| Long ritual narrative, no internal headings | curated page→title map injected before `#### Page N` markers (see `PDF_handle/TOOLS/duncan_section_map.v2.json`), then the standard pass |

3. Validate the output before staging:
   - Section stats: median 1–10K chars, nothing above ~15K (oversized sections
     get truncated at mapping time and lose classification signal).
   - Free heuristic preflight; `fragmentary_topic` should be under ~15% of kinds.

## Tool flags (restructure_page_md_to_semantic.py)

- `--drop-pattern REGEX` — delete artifact lines (use `(?i)`; running headers are
  often ALL-CAPS in the source, a case-sensitive pattern silently misses them).
- `--body-pattern REGEX` — never promote to heading (figure captions: `'(?i)^fig\.? ?\d+'`).
- `--min-section-chars N` — fold tiny sections (ritual dialogue caps lines) into the previous one.
- `--max-section-chars N` — split oversized sections; falls back paragraph → line →
  sentence → hard slice, so even sentence-less OCR garbage gets capped.
- `--pause-commentary` — pause description becomes the heading, commentary the body.
- `--dedup-paragraphs` — exact-repeat removal for double-OCR sources. Near-duplicates
  with different OCR errors survive; Step 5's existing-match absorbs them.

## Judgment calls the tool cannot make

- Thematic titles. The automatic path titles from the text ("Pause 4: After the
  dialogue with the Junior Warden..."). Functional but ugly — flag weak titles
  for the content quality review rather than blocking on them.
- Heading curation for narratives (the Duncan's case): pick split pages from a
  page worksheet (first meaningful line per `#### Page N`), write the title map
  by hand. ~40 pages of unlabeled story needs a human-chosen arc of titles.
- Keep the original file: prepped output overwrites the clean-start copy
  (gitignored), but the raw original should stay untouched in the old workspace
  (`code\PDF_handle\consolidated_books`) as the source of truth.
- Preserve content verbatim where possible. Fixing OCR breaks ("lod ge") is
  fine; rephrasing substance is not — if something must be paraphrased (e.g.
  masked ritual words), tell the user explicitly and get their call.
