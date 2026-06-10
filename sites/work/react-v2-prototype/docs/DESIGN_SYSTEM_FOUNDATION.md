# Design System Foundation

This document defines the visual system direction for the React V2 prototype.
It is a design guardrail, not a component library yet.

## Design Thesis

The site should feel like a calm learning archive:

- structured, not sterile
- readable, not decorative
- research-capable, not dashboard-like
- Hebrew-first, with real RTL/LTR direction support

The interface should help users understand where they are before it tries to impress them.

## Current Styling Decision

Use custom CSS tokens and component classes.
Do not add Bootstrap.
Do not add Tailwind yet.

Why:

- The product still needs a distinct visual voice.
- Bootstrap would make the site feel generic.
- Tailwind is useful only after repeated CSS patterns become a maintenance problem.
- The current token layer already supports color, spacing, radius, typography, focus, and shadows.

## Token Ownership

CSS tokens should own:

- page and surface colors
- text and muted text colors
- line/border color
- degree/source accent colors
- spacing scale
- card radius
- typography families
- focus ring
- shadow level

Tokens should stay small.
Do not create a token for every one-off value.

## Density Rules

The site should feel comfortable at 100% browser zoom.

Default rules:

- Shrink padding before shrinking text.
- Keep article reading text comfortably sized.
- Keep decorative surfaces compact.
- Avoid giant hero blocks.
- Avoid empty cards that consume more space than their content deserves.
- Keep the first useful content visible early.

## Radius And Cards

Cards should stay restrained.

Rules:

- Use `8px` radius or less.
- Avoid bubbly or pill-heavy page structure.
- Use cards for containment, not decoration.
- Avoid dashboard-style statistic grids inside article pages.
- Prefer quiet metadata lines over boxed metadata when the user is reading.

## Typography

Typography should support Hebrew-first reading.

Rules:

- Use display typography for page/article titles.
- Keep body text line-height generous enough for reading.
- Keep labels and metadata smaller and quieter.
- Avoid English chrome dominating Hebrew content.
- Use logical alignment so text follows document direction.

## Focus And Accessibility

Visible focus is part of the design system.

Must cover:

- brand/home link
- global search
- mode tabs
- language switcher
- degree navigation
- category filters
- topic rows
- source rows
- article back button
- article source button
- previous/next article buttons

Focus should be visible and consistent, not browser-default invisible.

## Surface Rules

### Home

- Smaller hero/home band.
- One clear primary direction.
- No oversized promotional sections.

### Degree Map

- Compact topic rows.
- Clear active filters.
- Degree navigation should feel like a map, not a sidebar menu copied from an admin app.

### Article Page

- Reading first.
- Context rail is helpful but should not overpower the article.
- Avoid boxed metadata grids.
- Source and related content should be clear but secondary unless research mode is active.

### Library

- Research-oriented rows.
- Metadata visible.
- Virtualized list remains stable.
- Do not turn sources into topic cards.

## RTL/LTR Rules

Use logical CSS wherever possible:

- `text-align: start`
- `inset-inline-start`
- `margin-inline`
- `padding-inline`

Avoid hardcoding left/right unless the visual meaning is truly physical.

When switching language:

- `html dir` must change.
- shell alignment must follow direction.
- content should remain readable even before translated content is connected.

## Component Maturity Levels

### Prototype

- Component classes can be plain CSS.
- Variants can be class modifiers.
- Visual tokens live in `styles.css`.

### Production

- Extract repeated component patterns only after they are stable.
- Consider separate CSS modules or Next.js-compatible styling only during the production scaffold.
- Do not introduce a UI library just to avoid writing small components.

## Acceptance Criteria

The design system foundation is working when:

- Pages feel comfortable at 100% zoom.
- Article pages feel like reading pages, not side panels or dashboards.
- Library feels like a research surface.
- Focus states are visible.
- RTL/LTR switching does not break alignment.
- CSS decisions remain traceable to tokens and surface rules.

## Current Non-Goals

- No Bootstrap.
- No Tailwind dependency yet.
- No shadcn/ui dependency yet.
- No full component library extraction.
- No JSON changes.
