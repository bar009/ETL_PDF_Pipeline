---
name: etl-source-ingest
description: Run a new book/source through the Masonic ETL pipeline end to end — routing check, markdown prep, heuristic preflight, Gemini stage, candidate review, selective approval, live merge, structure builder, and gates. Use this whenever the user wants to ingest, stage, run, or merge a source/book/PDF into the knowledge vault (repo code-clean-start), mentions a work_id from work_routing.json, asks to "run the pipeline" on new content, or wants to review/approve companion candidates. Also use when staging multiple sources in parallel with several Gemini API keys.
---

# ETL Source Ingest — one source, end to end

Repo: `C:\Users\bar16\OneDrive\Documents\code-clean-start`. Live pilot root:
`C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\work-english-degree-pilot`
(confirm with the user if a different root is in play).

The pipeline is review-doored: **nothing reaches live data without explicit
approval flags.** Stage is always safe to run; apply is the guarded step.

## The sequence

### 1. Routing check — do this FIRST, every time

Open `PDF_handle/work_routing.json` and find the work entry. Verify
`applies_to_degrees` covers every degree whose content actually appears in the
book, not just the degree in the title. This is the single most common failure:
a "level1 education course" whose second half is Master Mason content gets its
MM sections force-routed to level1 or silently rejected when level3 is missing
from the route. It happened with three different sources (Basic Education,
Blue Lodge, Duncan's). When in doubt, open the degree — out-of-route content
is blocked at apply anyway, so a wider route is the safer error.

Multi-degree books should also have `"primary_degree": "multi"`.

### 2. Source prep

The consolidated markdown must have semantic `##` headings (one heading = one
knowledge unit). If it still has `## Page N` headings, run the source-markdown-prep
skill / `PDF_handle/docs/SOURCE_PREP_RUNBOOK.md` decision tree first.
Both the `.md` and its `_meta.json` must sit in `PDF_handle/consolidated_books/`.

### 3. Heuristic preflight (free, no API key)

```
python PDF_handle/prod/steps/stage.py --site-root <ROOT> --book <work-id> --provider heuristic
```

Then check `PDF_handle/staged_injection/discovery_rows.json`: count `unit_kind`
values. Healthy = mostly `topic`, `fragmentary_topic` under ~15%. A fragmentary
flood means the markdown prep is wrong — fix headings before spending Gemini calls.

### 4. Gemini stage

```
python PDF_handle/prod/steps/stage.py --site-root <ROOT> --book <work-id> --provider gemini
```

- `GEMINI_API_KEY` must be in the environment. The project `.env` is written in
  PowerShell syntax (`$env:GEMINI_API_KEY = "..."`), so from bash extract it:
  `export GEMINI_API_KEY="$(sed -E 's/.*"([^"]+)".*/\1/' .env | tr -d '\r\n ')"`.
  The key must reach the provider unquoted — a quoted value returns API_KEY_INVALID.
- Long runs: launch in the background; ~3-6s per unit.
- **Parallel staging**: multiple sources can stage simultaneously if each run
  gets its own `--staging-dir` (e.g. `PDF_handle/staged_injection_<name>`) and
  ideally its own API key (keys share rate limits). Apply stays serial.

### 5. Candidate review — the operator decision point

List the candidates for the user (this exact surface has worked well):

```python
# from companion_candidates.json in the staging dir, print per candidate:
# section_id | draft_seed.degree | draft_seed.category (category_source) | section_title
```

Build a recommendation table: approve / reject / borderline, with one-line
reasons. Patterns learned:
- Title pages, author names, jurisdiction-specific administrivia → reject.
- Procedural/officer content (installations, charges, circuits) → approve into
  the `lodge_procedure` category (operator decision from 2026-06-12: it gets
  its own category, NOT just the library lane). To recategorize, edit the
  candidate's `draft_seed.category` in companion_candidates.json and set
  `category_source: "operator_override"` before apply.
- Misrouted degree (MM emblem in level1) → reject and note; fix routing if systemic.
- Near-duplicates of existing entries usually arrive as `existing_match` ops,
  not candidates — that's the dedup working.

**The user decides.** Present the table, wait for their call (they often
approve the recommendation as-is, but procedural/borderline calls are theirs).

### 6. Apply (selective)

`--approve-companions` accepts `"all"` or a path to a JSON approval file:

```json
{ "section_ids": ["section-0002", "section-0005"] }
```

```
python PDF_handle/prod/steps/apply.py --site-root <ROOT> \
  [--staging-dir <dir-if-not-default>] \
  --approve-companions <approvals.json | all> \
  --approve-level1 all --approve-level2 all --approve-level3 all \
  --merge-library --apply-live
```

Never use `--approve-companions all` for a source known to mix degrees or
contain noise — that is what the approval file is for. Unapproved candidates
stay `suggested` and are not merged. Apply writes backups + rollback_plan.md
automatically.

### 7. Structure builder + gates

```
python PDF_handle/prod/cli/build_degree_structure.py --site-root <ROOT> --apply
python PDF_handle/prod/cli/validate_runtime.py --site-root <ROOT> --require-complete --strict
python PDF_handle/prod/cli/language_integrity_audit.py --site-root <ROOT> --strict
```

Builder creates hubs for any new category and adopts orphan topics. Gates must
both pass (validate_runtime: all checks ok, strict). Then report final counts:

```python
# per level1/2/3/library: total | hubs | topics | orphans | topics-per-category
```

### 8. Close out

Update `docs/BACKLOG.md` (move item to Done), commit routing/tool changes on a
feature branch, push, and give the user the GitHub compare URL (gh CLI is
usually not authenticated; portable gh lives at %LOCALAPPDATA%\gh-cli\bin\gh.exe).
Consolidated markdown and staging dirs are gitignored by design — only code,
routing, templates, and docs are committed.

## Failure modes seen in practice

| Symptom | Cause / fix |
|---|---|
| All sections `fragmentary_topic`, 0 candidates | Page-based headings — restructure the markdown |
| Candidates all in one category (`first_category_fallback`) | Provider category assignment missing the catalog — check stage version |
| MM/FC content routed to wrong degree or rejected | `applies_to_degrees` too narrow — step 1 |
| `validation_ok=False` on apply | Usually staged-but-unselected library chapters — add `--merge-library` |
| `API_KEY_INVALID` | Quoted key; strip quotes/whitespace |
| `unrecognized arguments` on approve flags | They take ONE value: `all` or a JSON file path, not a list of ids |
