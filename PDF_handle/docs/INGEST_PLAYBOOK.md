# Ingest Playbook — new file to published knowledge, end to end

The single flow to follow on a day a new PDF/source arrives. Two human
decision points are marked ⛔ — everything else is mechanical.

```
PDF → [1 intake] → [2 ⛔ routing] → [3 prep] → [4 stage] → [5 ⛔ review] → [6 merge+gates] → [7 unify+publish]
```

## 1. Intake (PDF → consolidated markdown)

Run preprocess Steps 1–4 (extract, chunk, AI transform, consolidate):

```
python PDF_handle/TOOLS/run_preprocess_01_04.py   # or the prod intake CLI once built
```

Output: `PDF_handle/consolidated_books/<Book>.md` + `<Book>_meta.json`.

> Planned: `intake_new_source.py` will wrap this plus steps 2's scaffold and a
> markdown-shape diagnosis (see BACKLOG). Until it exists, run the steps manually.

## 2. ⛔ Routing registration (human decision)

Add a work entry to `PDF_handle/work_routing.json`: `work_id`, `staging_dir`,
`work_title`, `primary_degree`, `applies_to_degrees`, sensitivity defaults.

**The one rule that keeps biting**: `applies_to_degrees` must cover every degree
whose content appears in the book — not the degree in the title. A level1
course with a Master Mason half needs level3 in the route. When unsure, route
wider; out-of-route content is blocked at apply anyway.

## 3. Source prep (markdown → semantic sections)

Follow `SOURCE_PREP_RUNBOOK.md` (or the source-markdown-prep skill): diagnose
the shape, run `restructure_page_md_to_semantic.py` with the matching recipe,
check section stats (median 1–10K chars, nothing over ~15K).

## 4. Stage

Heuristic preflight first (free), then Gemini:

```
python PDF_handle/prod/steps/stage.py --site-root <ROOT> --book <work-id> --provider heuristic
python PDF_handle/prod/steps/stage.py --site-root <ROOT> --book <work-id> --provider gemini
```

Parallel sources: separate `--staging-dir` per run, ideally separate API keys.

## 5. ⛔ Candidate review (human decision)

Review `companion_candidates.json` (degree / category / category_source per
candidate). Build an approval file — never blanket-approve a mixed or noisy
source:

```json
{ "section_ids": ["section-0002", "section-0005"] }
```

Procedural/officer content goes to the `lodge_procedure` category (operator
decision, 2026-06-12) — recategorize via `draft_seed.category` +
`category_source: "operator_override"` before apply.

## 6. Merge + structure + gates

```
python PDF_handle/prod/steps/apply.py --site-root <ROOT> [--staging-dir <dir>] \
  --approve-companions <approvals.json> --approve-level1 all --approve-level2 all \
  --approve-level3 all --merge-library --apply-live
python PDF_handle/prod/cli/build_degree_structure.py --site-root <ROOT> --apply
python PDF_handle/prod/cli/validate_runtime.py --site-root <ROOT> --require-complete --strict
python PDF_handle/prod/cli/language_integrity_audit.py --site-root <ROOT> --strict
```

Multiple staged sources merge **serially** (one apply at a time, same root).

## 7. Unification + publish (the final written product)

This is the stage that turns "merged data" into "the written knowledge the
site serves". After all sources of a batch are merged and gates are green:

1. **Cross-source unification pass** — the same concept arriving from several
   books must end as ONE entry enriched by all of them, not near-duplicates.
   Most of this happens automatically at stage time (existing_match → enrichment
   ops), but after a multi-source batch, audit for stragglers:
   - `python PDF_handle/TOOLS/audit_sparse_entries.py` — sparse/duplicate entries
   - title-similarity scan across degrees for near-duplicate topics
   - merge stragglers by hand (move relations + source_notes, delete the duplicate)
2. **Content quality review in the browser** — serve the root, read entries,
   fix weak titles/summaries, decide draft→published promotions.
3. **Snapshot** — freeze the result:
   ```
   python PDF_handle/prod/cli/publish_snapshot.py --site-root <ROOT>
   ```
   The snapshot is what the frontend consumes; live root stays the working copy.
4. **Close the loop** — update `docs/BACKLOG.md` (Done section), DECISION_LOG
   entry if any policy changed, commit + PR.

## Definition of done for a batch

- All sources merged, 0 orphan topics, both gates green.
- No near-duplicate entries across the batch's concepts.
- Snapshot published and loadable by the site.
- BACKLOG and DECISION_LOG reflect reality.
