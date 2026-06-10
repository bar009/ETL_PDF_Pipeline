---
name: knowledge-mode-page-design
description: Design knowledge-heavy websites with distinct Learning, Encyclopedia, and Research modes. Use when the user wants each viewing mode to behave differently on the homepage and topic page, when a knowledge graph site needs mode-aware UX, or when one shared UI is making all modes feel muddled.
---

# Knowledge Mode Page Design

Use this skill when a knowledge site has multiple viewing modes and each one needs a different product behavior.

Do not treat modes like cosmetic filters.
Treat them as distinct answers to distinct user questions.

## Read First

1. the target site's render logic
2. the target site's mode switch logic
3. any mode specification notes in `management/ui_research_*`

For this repository, prefer:

- `management/ui_research_2026-04-02/01_learning_mode_spec.md`
- `management/ui_research_2026-04-02/02_encyclopedia_mode_spec.md`
- `management/ui_research_2026-04-02/03_research_mode_spec.md`
- `management/ui_research_2026-04-02/MODE_SYSTEM_SPEC.md`

For concrete before/after heuristics, read:

- `references/before-after-heuristics.md`

## Mode Definitions

### Learning

Primary question:

- what should I read now, what should I take from it, and what comes next

Homepage should feel like:

- guided start
- continue flow
- alternate gates

Topic page should feel like:

- lesson

### Encyclopedia

Primary question:

- what is this, and where does it belong

Homepage should feel like:

- map
- browse
- search-first reference surface

Topic page should feel like:

- atlas entry

### Research

Primary question:

- what supports this, what is connected to it, and what should I compare

Homepage should feel like:

- evidence map
- source-backed discovery

Topic page should feel like:

- claim plus provenance plus comparison

## Shared Rule

Keep one shared shell, but do not keep one shared page behavior.

If all three modes look almost the same, the implementation is wrong.

## Ownership Rule

Each mode must own one primary strength:

- `learning` owns guidance
- `encyclopedia` owns classification
- `research` owns provenance

If one surface tries to do two of these jobs at once, choose an owner and demote the rest in the other modes.

## Homepage Checklist By Mode

### Learning

- one recommended start
- one continue action
- one fallback browse layer
- very little source-heavy noise above the fold

### Encyclopedia

- search is central
- categories are dense but readable
- representative anchor topic is okay
- avoid path language

### Research

- source-backed items surface early
- comparison entry points surface early
- recent research path is useful
- helper copy explains evidence lens, not learning path

## Topic Page Checklist By Mode

### Learning

Use the 3-layer model near the top:

1. what to understand now
2. what to take from this
3. what to open next

### Encyclopedia

Top of page should answer:

1. what is this
2. where is it located
3. what neighboring entries matter

### Research

Top of page should answer:

1. what is the claim or object
2. what supports it
3. what should be compared next

## Typical Shared Surfaces

The same DOM areas may exist in all modes, but they should not all behave the same:

- hero
- helper strip
- category navigation
- title block
- metadata row
- topic pager
- related links
- support/provenance blocks

Use the shared shell for consistency, then vary:

- order
- density
- copy
- prominence
- visibility

## Demotion Rules

Only one mode should get a strong thing at a time.

Examples:

- `learning` gets path guidance
- `encyclopedia` gets browse density
- `research` gets provenance density

Do not leave all three strengths visible in all three modes.

## Output Standard

When finishing a mode-aware pass, report:

1. what changed in each mode
2. what stayed shared
3. where the current code still forces too much shared behavior
4. which mode still feels under-differentiated
