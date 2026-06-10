---
name: hebrew-rtl-site-redesign
description: Redesign Hebrew and RTL websites with clearer homepage flow, better topic/detail reading, restrained chrome, and stronger first-view hierarchy. Use when the user asks to redesign a site UI, improve a Hebrew website, fix homepage vs detail-page structure, make a knowledge-heavy site feel lighter and more intentional, or says the site still feels clunky, unclear, or not fun to read.
---

# Hebrew RTL Site Redesign

Use this skill when the real problem is not one broken component, but the overall feel of a Hebrew/RTL site.

Focus on hierarchy, not decoration.
The goal is to make the site feel obvious, calm, and useful at normal browser zoom.

## Read First

1. `AGENTS.md`
2. `management/CURRENT_PLAN.md`
3. the target site's `index.html`
4. the target site's main render file
5. the target site's main theme CSS

If this repo contains `management/ui_research_*` notes for the target site, read those before changing layout.

For concrete pattern checks, read:

- `references/before-after-heuristics.md`

## Core Rules

1. Design for Hebrew-first scanning.
2. The right side matters first in overview flows.
3. Do not let English chrome dominate Hebrew content.
4. Prefer one clear primary action per viewport.
5. Do not keep adding helper strips, pills, and cards that repeat the same message.
6. Default to fewer boxes, less padding, and less ornamental framing.
7. If the user must zoom out to 90% or 80%, the proportions are wrong.

## Working Model

Before editing, write three short statements for yourself:

- visual thesis: what should the site feel like
- navigation thesis: what should the user understand in 3 seconds
- reading thesis: what should happen before the first major scroll

## Homepage Workflow

1. Define the homepage job:
   - entry gate
   - index
   - research map
   - guided start
2. Decide what gets primary emphasis.
3. Remove or demote everything else.
4. Keep the first viewport readable without scrolling.
5. Make the main CTA and fallback CTA unmistakable.

## Topic Detail Workflow

Treat the topic page as a reading surface, not a giant modal full of metadata.

Prioritize this order:

1. where am I
2. what is this
3. what should I understand first
4. what should I open next

Demote these unless the mode truly needs them:

- full metadata
- long tag clusters
- dense related lists
- provenance blocks above the main reading block

## RTL Heuristics

- Breadcrumbs and context should be short and scannable.
- Avoid left-anchored visual habits that feel translated from LTR.
- In overview screens, right rail and category logic should feel intentional, not mirrored by accident.
- Keep Hebrew labels short and operational.

## Typical Touch Points

In this repository, the most likely files are:

- `index.html`
- `js/render.js`
- `css/reference-theme.css`

If the proportions or layout still feel wrong after theme overrides, also inspect:

- `css/layout.css`
- `css/cards.css`
- `css/sidebar.css`
- `css/detail.css`

## Hard Red Flags

If any of these are true, stop polishing and compress the layout:

- the first viewport feels like stacked boxes
- cards are taller than they need to be
- support surfaces compete with the core action
- the detail page spends too much height on chrome before content
- the user still needs browser zoom-out to feel comfortable

## Default Fix Order

1. first viewport hierarchy
2. search / CTA clarity
3. topic reading lead
4. box density and padding
5. typography scale
6. support surfaces below the fold

## Acceptance Checks

Do not call the pass successful unless these feel true:

1. the homepage answers "what do I do here" within one screen
2. the first viewport has one clear primary action and one clear fallback
3. the topic page reaches its core idea before the page feels crowded
4. Hebrew labels feel authored for RTL, not translated from LTR
5. the site feels comfortable at 100% zoom

## Output Standard

When you finish, report:

1. what was simplified
2. what was resized
3. what became easier to do
4. what still needs a structural redesign instead of more CSS
