# Backlog

Working agreement: one line per item — short imperative title (origin date).
Items graduate Now → Done; anything stale in Next for 2 sessions moves to Later.
Decisions that block items link to `DECISION_LOG.md`.

## Now

- [ ] Sparse-metadata noise filter in Step 5 — title-page/author sections must not become candidates (2026-06-11)
- [ ] Degree categories template (`prod/templates/degree_categories.v1.json`) + seeder `--categories-template` (2026-06-11)
- [ ] Provider-driven category assignment at stage time (`suggested_category` from the mapping call) (2026-06-11)
- [ ] Structure builder CLI: hub per category, orphan topics adopt `parent_topic` (2026-06-11)
- [ ] Source prep for the full run — semantic-heading consolidated markdown per source (2026-06-11)

## Next

- [ ] level1 via Basic Masonic Education Course — *selective* approval only; the source mixes Master Mason content (2026-06-11)
- [ ] Content quality review of draft entries in the browser before any draft→published promotion (2026-06-11)
- [ ] Re-run Color-Symbolism + Allegories of Hiram Abiff on the new taxonomy (fresh seeded root) (2026-06-11)
- [ ] Duncan's Ritual source prep — reuse `prod/cli/duncan_section_map_apply.py`, then manual cleanup; giant book, own work item (2026-06-11)
- [ ] Library of Freemasonry Vol 2 source prep — chapter-by-chapter restructure; giant book, own work item (2026-06-11)
- [ ] Blue Lodge Ritual Reference Guide source prep — expect heavy procedural filtering (2026-06-11)
- [ ] Deeper meaning of FC Degree source prep — copy consolidated from old run `v21r1-e1-new-sources-2026-04-24`, restructure (2026-06-11)

## Later / Icebox

- [ ] Hebrew lane: `parallel_entry` translation pairs; start from `prod/cli/hebrew_localization_bundle.py` — wait until the English canon is 50+ entries the operator is happy with (2026-06-11)
- [ ] Frontend v2 (React/Next prototypes) consuming published snapshots through the adapter contract (2026-06-11)
- [ ] Commentary on the Second Degree: "Nth Pause / Commentary" parser to recover conceptual content from procedural anchors (deferred from pilot) (2026-06-11)
- [ ] Surface `category_source` / `category_reason` columns in `candidate_review_queue_export.py` (2026-06-11)
- [ ] `candidate_review_queue.py` integration with review states (check whether it needs `review_state` awareness) (2026-06-11)

## Decisions needed

- [ ] draft→published promotion criteria per entry (who reviews, what bar) — see DECISION_LOG.md review-door entries (2026-06-11)
- [ ] Hub entry status policy long-term: `published` scaffolding vs `draft` until first content review (current default: published) (2026-06-11)

## User-side (only the operator can do)

- [ ] Remove the quotes around `GEMINI_API_KEY` in `.env` — providers read the value verbatim and Google rejects a quoted key as `API_KEY_INVALID` (2026-06-11)

## Done (recent)

- [x] Review door enforced in Step 6 for operations and companions (2026-06-11, PR #16/#18)
- [x] Step 6 dry-run trap closed: early library-link guard, `mode=` in done line, non-zero exit on failed validation (2026-06-11, PR #22)
- [x] `work_library_coverage` gate check: degree work_id must exist in the library lane (2026-06-11, PR #24)
- [x] Orchestrator NameError fix in exploration cluster builder (2026-06-11, PR #25)
- [x] Proven E2E runbook: Color-Symbolism (level2) + Hiram Abiff (level3), both gates green, snapshot published (2026-06-11, PR #23)
