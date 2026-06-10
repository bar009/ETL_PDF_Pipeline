# Frontend Stack Decision

This document records the stack direction for the React V2 prototype and future production app.
It intentionally does not change runtime code or existing site JSON.

## Decision

Use React now.
Move to Next.js later only when production needs require it.
Do not add Vue, Angular, Svelte, Bootstrap, or Tailwind by default.

## Current Prototype Stack

- React for component structure.
- Vite for fast local iteration.
- Custom CSS tokens for visual system and density.
- Local History API router for clean route behavior.
- Fuse for prototype fuzzy search.
- TanStack Virtual for large research/library lists.
- Playwright and Axe for route, mobile, and accessibility smoke checks.

Why this is right now:

- We are still shaping the product.
- Vite keeps iteration fast and low-friction.
- React components can move to Next.js later with less waste than rebuilding the whole UI.
- The prototype can prove routes, layouts, language direction, search, article pages, and library behavior before real data is connected.

## Production Target

Use Next.js when the app needs production-grade framework features:

- Route-level metadata and SEO.
- Static generation or server rendering for article/source pages.
- Server-side auth and access enforcement.
- Deployment conventions.
- Production data loading boundaries.
- Canonical URL and locale-aware metadata generation.

Next.js should be treated as the production React framework, not as a replacement for the current prototype process.

## Migration Triggers

Move from Vite React to Next.js only after these are true:

- Product definition is stable.
- Core surfaces are accepted: home, degree map, article page, library.
- Design tokens and component boundaries are stable enough to port.
- Clean route behavior is stable.
- RTL/LTR shell behavior is tested.
- Search and virtualized library behavior are accepted.
- We are ready to build a read-only adapter from existing site JSON.
- We need production metadata, auth, or deployment behavior.

## Non-Triggers

Do not move to Next.js just because:

- Someone says a site “needs Next.js.”
- The prototype has a visual bug.
- We want the site to look more modern.
- We have not yet connected real JSON.
- We are still changing the article or homepage product shape.

Those are prototype and design-system problems, not framework problems.

## Rejected Stack Additions

### Vue

Rejected for this project because it is an alternative to React, not an addition.
Using both would split the component model.

### Angular

Rejected for this project because it adds a heavy framework model that does not fit the current prototype or migration path.

### Svelte

Rejected for this project because it is another alternative component model.
It would require rebuilding rather than evolving the current React work.

### Bootstrap

Rejected for the product voice.
It would make the Hebrew-first knowledge site feel too generic and dashboard-like.

### Tailwind

Deferred, not rejected forever.
Use only if custom tokenized CSS becomes harder to maintain than utility classes.
Do not add it while the visual language is still being shaped.

## Dependency Rule

Add dependencies only when they solve a concrete product or engineering problem:

- Search quality: allowed when search behavior needs it.
- Virtualization: allowed for large library/source lists.
- Accessibility testing: allowed for release gates.
- Styling frameworks: defer unless current CSS becomes a measurable maintenance blocker.

Every dependency should have a reason, a surface, and a validation check.

## Porting Rules For Next.js

When migration starts:

- Keep component names and visual behavior stable.
- Move routing from the local History API into Next.js routes.
- Move metadata from client-side `document.title` updates into route metadata.
- Keep the JSON adapter read-only at first.
- Add auth/access enforcement server-side before protected content is shipped.
- Re-run the same browser, mobile, route fallback, direction, and accessibility checks after porting.

## Acceptance Criteria

This stack decision remains valid while:

- The React prototype can iterate quickly.
- The prototype proves product behavior without mutating JSON.
- No production SEO/auth/deployment requirement is blocked by Vite yet.
- The future Next.js migration path stays clear and low-risk.

Revisit this decision when:

- Real JSON integration is ready.
- Production auth is in scope.
- Deployment target is chosen.
- Route-level SEO becomes release-critical.
