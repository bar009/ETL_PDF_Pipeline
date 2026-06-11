# Source Prep Runbook — from raw consolidated markdown to stage-ready

Every source must reach Step 5 as a markdown file with **semantic `##` headings**
(one heading = one knowledge unit). Raw OCR output never satisfies this. This
runbook is the repeatable, no-AI-assistant path.

## The tool

```
python PDF_handle/TOOLS/restructure_page_md_to_semantic.py INPUT.md OUTPUT.md [flags]
```

| Flag | What it does |
|------|--------------|
| `--drop-pattern REGEX` | Delete artifact lines entirely (running headers, `Page N`). Repeatable. Case-insensitive needs `(?i)`. |
| `--body-pattern REGEX` | Line can never become a heading (figure captions). Repeatable. |
| `--pause-commentary` | 'Nth Pause: / Commentary:' lecture format → pause text becomes the heading. |
| `--dedup-paragraphs` | Drop paragraphs repeated verbatim (double-OCR cleanup). |
| `--min-section-chars N` | Fold tiny sections into the previous one (shouted dialogue lines). |
| `--max-section-chars N` | Split oversized sections at paragraph/line/sentence boundaries into `(Part N)`. |

## Decision tree

1. **Look at the headings**: `grep "^## " file.md | head -30`
2. Pick the case:

### Case A — page-based OCR (`## Page N` everywhere)
```
python PDF_handle/TOOLS/restructure_page_md_to_semantic.py IN.md OUT.md \
  --drop-pattern '(?i)^page \d+$' \
  --drop-pattern '(?i)^<running header of this book>$' \
  --body-pattern '(?i)^fig\.? ?\d+' \
  --min-section-chars 600
```
Used for: Blue Lodge (177 pages → 225 sections).

### Case B — Pause/Commentary lecture
Add `--pause-commentary --dedup-paragraphs`. Used for: Commentary on the Second Degree.

### Case C — chapter book with run-on OCR lines
First split chapters (see the chapter-prefix pass in git history for
libraryoffreemas02goul), then Case A flags plus `--max-section-chars 12000`.
Used for: Library of Freemasonry Vol 2 (max section capped at 12K).

### Case D — narrative spans with no internal headings (Duncan's)
Automatic heading detection cannot title a 40-page ritual narrative. Create a
curated page→title map (see `PDF_handle/TOOLS/duncan_section_map.v2.json`),
inject `## <title>` before the mapped `#### Page N` markers, then run Case A.

## Quality bar before staging (gates)

1. Section stats: aim for median 1–10K chars, no section above ~15K
   (oversized sections get truncated at mapping and lose content from
   classification).
2. **Heuristic preflight** (free, no API key):
   ```
   python PDF_handle/prod/steps/stage.py --site-root <ROOT> --book <work-id> \
     --provider heuristic --staging-dir PDF_handle/staged_injection_preflight
   ```
   Check the `kinds:` distribution in discovery_rows.json — a healthy source is
   mostly `topic`, with `fragmentary_topic` under ~15%.
3. **Routing check** — open `PDF_handle/work_routing.json` and verify
   `applies_to_degrees` covers every degree whose content actually appears in
   the book. A source titled for one degree often contains others (this bit us
   three times: Basic Education, Blue Lodge, Duncan's all hid Master Mason
   content behind level1/level2 titles).

## Known limits (operator judgment still needed)

- Thematic titles: the automatic path titles sections from the text itself
  ("Pause 4: After the dialogue with the Junior Warden..."). Good enough for
  staging; rename weak titles during content quality review.
- Near-duplicate OCR copies (same text, different OCR errors) survive
  `--dedup-paragraphs`; Step 5's existing-match detection absorbs most of them.
- OCR word-breaks ("lod ge") are not fixed automatically; they rarely affect
  classification but should be cleaned in the published entry text.
