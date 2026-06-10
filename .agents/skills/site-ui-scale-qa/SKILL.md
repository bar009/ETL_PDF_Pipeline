---
name: site-ui-scale-qa
description: Run a UI scale and proportion pass on websites that feel too zoomed, oversized, scroll-heavy, or filled with giant cards and bubbles. Use when the user says the site feels too big at 100% zoom, they must press Ctrl-minus, the boxes are huge, the article view is too tall, or scrolling feels excessive before useful content appears.
---

# Site UI Scale QA

Use this skill when the site is technically working, but the proportions feel wrong.

This skill is about visual scale, density, and viewport economy.
It is not about changing product logic first.

## Goal

Make the site feel natural at 100% zoom.

For concrete before/after heuristics, read:

- `references/before-after-heuristics.md`

## First Checks

Audit these surfaces in order:

1. header height
2. top bar height
3. button height
4. card padding
5. border radius
6. line length and text size
7. sidebar density
8. topic-detail lead height
9. support surface size
10. first-scroll distance to useful content

## Rules

1. Prefer shrinking padding before shrinking text too aggressively.
2. Prefer shrinking decorative surfaces before shrinking core reading text.
3. Keep reading width efficient so the user scrolls less.
4. If a support box is bigger than the information inside it, compress it.
5. If cards look like bubbles, reduce:
   - padding
   - radius
   - gaps
   - top borders
   - hover lift

## Common Root Causes

Check for these before assuming the problem is only typography:

- giant base styles in `layout.css`, `cards.css`, `sidebar.css`, or `detail.css`
- theme overrides that shrink one surface but leave the underlying card system large
- sticky bars that consume too much vertical space
- a narrow reading column plus large text, which creates extra scrolling
- support cards that are visually larger than the content inside them

## Typical Surfaces To Compress

Start with these:

- `.topic-card`
- `.cards-grid`
- `.nav-sidebar`
- `.aside-panel`
- `.detail-article`
- `.detail-lead`
- `.detail-section`
- `.detail-source-card`
- `.detail-knowledge-links`
- `.detail-topic-pager`
- `.detail-learning-next-primary`

## Viewport Budget

On desktop, the combined visible stack of:

- header
- top controls
- hero or lead
- first support block

must not consume the whole screen unless that is the entire task of the page.

If the first screen already feels “full” before reading starts, compress the shell.

## Zoom Sanity Check

Use this blunt test:

- if the user feels forced to press `Ctrl-minus`, the pass is not done
- if homepage cards feel like large tiles instead of fast entry points, the pass is not done
- if the topic page still feels like a stack of bubbles before reading begins, the pass is not done

## Typical Targets

### Homepage

- smaller hero
- tighter panels
- denser category rows
- smaller main cards
- calmer sidebars

### Topic Page

- shorter sticky top bar
- smaller lead
- shorter dek
- fewer chips
- smaller support cards
- wider efficient reading column

## Browser QA

If Playwright or a live preview is available:

1. inspect homepage at 100% zoom
2. inspect one typical topic page
3. inspect one dense or worst-case topic page
4. compare how much scrolling is needed before the main reading value appears

If browser tooling fails, do a code audit and still ship a proportion pass.

## Validation Notes

When validating, compare:

1. homepage at 100% zoom
2. a typical topic page
3. a dense topic page

Record where the user reaches:

- first useful action
- first real reading block
- first continuation block

## Finish Line

The pass is successful only if all three feel true:

1. the site does not require zoom-out
2. the main surfaces no longer look oversized
3. the user reaches useful content sooner
