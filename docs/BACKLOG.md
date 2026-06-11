# Backlog

Working agreement: one line per item — short imperative title (origin date).
Items graduate Now → Done; anything stale in Next for 2 sessions moves to Later.
Decisions that block items link to `DECISION_LOG.md`.

## Now

- [ ] Blue Lodge Ritual Reference Guide source prep + run — expect heavy procedural filtering (2026-06-11)
- [ ] Content quality review of 122 entries in the browser before further growth (2026-06-11)

## Next

- [ ] intake_new_source.py CLI — wrap preprocess Steps 1-4, scaffold a routing entry with EMPTY applies_to_degrees (blocks staging until the operator fills it), print markdown-shape diagnosis (2026-06-12)
- [ ] Cross-source unification pass after the current batch — near-duplicate scan across degrees, merge stragglers, then publish_snapshot (see INGEST_PLAYBOOK.md step 7) (2026-06-12)
- [ ] Recover 4 rejected Commentary sections (Prayer, Password origins, Obligation dress, Investiture) from library into level2 entries during quality review (2026-06-12)

- [ ] Duncan's Ritual source prep — reuse `prod/cli/duncan_section_map_apply.py`, then manual cleanup; giant book, own work item (2026-06-11)
- [ ] Library of Freemasonry Vol 2 source prep — chapter-by-chapter restructure; giant book, own work item (2026-06-11)
- [ ] Fragmentary-title false positive: long headings with colons (e.g. "The Letter G and the Five-Pointed Star") get skipped as fragmentary_topic; loosen the detector (2026-06-11)

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

- [x] ~~Remove the quotes around `GEMINI_API_KEY` in `.env`~~ — done by operator (2026-06-11)

## Done (recent)

- [x] Basic Masonic Education Course merged as multi (level1+level3) with selective companion approval via JSON approval file; routing fixed in work_routing.json (2026-06-11)
- [x] Pilot root at 122 entries across 4 sources; 0 orphans; gates 19/19 strict + language audit clean (2026-06-11)
- [x] Sparse-metadata noise filter, taxonomy template, provider category assignment, structure builder CLI — all landed and proven on the pilot root (2026-06-11)
- [x] Deeper Meaning of FC Degree merged (level2, 4 enrichment ops + 3 companions) (2026-06-11)
- [x] GEMINI_API_KEY quotes removed from `.env` by operator (2026-06-11)

- [x] Review door enforced in Step 6 for operations and companions (2026-06-11, PR #16/#18)
- [x] Step 6 dry-run trap closed: early library-link guard, `mode=` in done line, non-zero exit on failed validation (2026-06-11, PR #22)
- [x] `work_library_coverage` gate check: degree work_id must exist in the library lane (2026-06-11, PR #24)
- [x] Orchestrator NameError fix in exploration cluster builder (2026-06-11, PR #25)
- [x] Proven E2E runbook: Color-Symbolism (level2) + Hiram Abiff (level3), both gates green, snapshot published (2026-06-11, PR #23)
