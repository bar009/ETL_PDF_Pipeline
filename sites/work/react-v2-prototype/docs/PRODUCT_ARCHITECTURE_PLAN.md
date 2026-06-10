# React V2 Product Architecture Plan

This plan covers the first production-facing foundation pass for the React prototype.
It intentionally does not touch existing site JSON.

## 1. Product Definition

Canonical detail: [`PRODUCT_DEFINITION.md`](./PRODUCT_DEFINITION.md).

The site is a Hebrew-first, multilingual knowledge product for degree learning and source research.
It should not feel like a generic content grid.

Primary surfaces:

- Home and degree map: helps the user understand where to start and what belongs to each degree.
- Article page: a focused reading surface that explains where the user is, what the article means, and what to open next.
- Library surface: a research-oriented source browser with rows, metadata, filtering, and source details.

## 2. Frontend Stack Direction

Canonical detail: [`FRONTEND_STACK_DECISION.md`](./FRONTEND_STACK_DECISION.md).

Current prototype:

- React + Vite for fast UI iteration.
- Custom CSS tokens for design consistency.
- Small local History API router for clean paths.

Production target:

- Migrate to Next.js only after the prototype UX stabilizes.
- Use Next.js for production routing, metadata, static generation, server boundaries, and deployment structure.
- Do not mix Vue, Angular, or Svelte into this app; they are alternative framework choices, not additive requirements.

## 3. Design System Layer

Canonical detail: [`DESIGN_SYSTEM_FOUNDATION.md`](./DESIGN_SYSTEM_FOUNDATION.md).

Keep the design system custom and small for now:

- CSS tokens own color, spacing, radius, typography, focus, and shadows.
- Cards stay restrained with radius at `8px` or less.
- Layout density should stay comfortable at 100% browser zoom.
- Bootstrap is not a fit for this product voice.
- Tailwind can be reconsidered only if repeated CSS patterns become harder to maintain than tokenized CSS.

## 4. Information Architecture

Canonical detail: [`INFORMATION_ARCHITECTURE.md`](./INFORMATION_ARCHITECTURE.md).

Current clean route model:

- `/` opens the product home entry surface.
- `/degree/:degreeId` opens a degree map/list.
- `/degree/:degreeId/:slug` opens a full article page.
- `/library` opens the research library.
- `/library/:slug` opens a source detail page.

Principles:

- List routes are maps.
- Slug routes are full reading/detail pages.
- Library remains a research surface, not another topic-card grid.
- Invalid routes should fall back to the nearest valid surface without blank pages.

## 12. Accessibility, RTL, And Multilingual Direction

Canonical detail: [`ACCESSIBILITY_MULTILINGUAL_CHECKLIST.md`](./ACCESSIBILITY_MULTILINGUAL_CHECKLIST.md).

The prototype now has an in-code locale foundation:

- Hebrew defaults to `lang="he"` and `dir="rtl"`.
- English switches to `lang="en"` and `dir="ltr"`.
- Layout alignment uses logical direction where possible.
- Shell chrome text can be localized before real content localization is connected.

Accessibility requirements:

- Visible focus states for search, tabs, navigation, rows, source buttons, language switcher, and article controls.
- Keyboard navigation must reach the core shell controls.
- Article pages must keep clear heading order and avoid side-panel-only reading.
- Mobile layout must avoid horizontal overflow.

Future multilingual data rule:

- Real multilingual content should come from a data adapter/localization layer.
- Existing JSON contracts should not be mutated during prototype UI work.

## 14. SEO And Metadata

Canonical detail: [`SEO_METADATA_MODEL.md`](./SEO_METADATA_MODEL.md).

Current prototype behavior:

- Routes update `document.title`.
- Routes update the page description meta tag.
- Routes update canonical URLs.
- Routes update Open Graph title, description, type, URL, and locale.
- Locale changes update document language and direction.

Next.js production target:

- Use route-level metadata generation for titles, descriptions, canonical URLs, and Open Graph tags.
- Generate stable metadata from the JSON adapter after the data layer is connected.
- Keep metadata language-aware without duplicating canonical content.

## 16. Migration Strategy

Canonical detail: [`MIGRATION_STRATEGY.md`](./MIGRATION_STRATEGY.md).
Component boundary detail: [`COMPONENT_BOUNDARY_CONTRACT.md`](./COMPONENT_BOUNDARY_CONTRACT.md).
Runtime data boundary: [`ETL_RUNTIME_DATA_BOUNDARY.md`](./ETL_RUNTIME_DATA_BOUNDARY.md).
Read-only adapter plan: [`READ_ONLY_DATA_ADAPTER_PLAN.md`](./READ_ONLY_DATA_ADAPTER_PLAN.md).
Adapter interface contract: [`ADAPTER_INTERFACE_CONTRACT.md`](./ADAPTER_INTERFACE_CONTRACT.md).

Recommended order:

1. Finish React prototype UX for degree maps, article pages, library, search, RTL/LTR, and accessibility.
2. Freeze the component and design-token contracts.
3. Create a Next.js production scaffold.
4. Port React components into Next.js without changing behavior.
5. Build a read-only adapter from existing site JSON into the React/Next data shape.
6. Add server-side auth/access boundaries.
7. Add production metadata, performance gates, and deployment checks.
8. Promote only after build, browser QA, accessibility smoke, route fallback, and mobile checks pass.

Non-goal for this pass:

- No existing JSON files are edited.
- No live or published roots are changed.
- No production auth is implemented yet.
