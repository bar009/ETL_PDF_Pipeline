# Migration Strategy

This document defines how to move from the React V2 prototype to a production-ready app without touching existing JSON too early.

## Migration Thesis

Prototype the product in React first.
Move to Next.js after the page model is stable.
Connect real JSON last through a read-only adapter.

The migration should reduce risk, not create framework churn.

## Phase 1: React Prototype Stabilization

Goal:

- Prove the product shape before production framework work.

Scope:

- Home and degree map.
- Full article page.
- Library research surface.
- Search and category filtering.
- Clean route behavior.
- RTL/LTR shell direction.
- Accessibility smoke checks.
- Metadata prototype behavior.

Exit criteria:

- Product definition is accepted.
- Stack decision is accepted.
- Design system foundation is accepted.
- Information architecture is accepted.
- Accessibility/multilingual checklist exists.
- SEO metadata model exists.
- UI smoke suite passes.

Do not:

- Connect real JSON yet.
- Implement production auth.
- Start a public deployment.

## Phase 2: Component Boundary Freeze

Goal:

- Make the React component model portable.

Scope:

- Freeze page-level component names and responsibilities.
- Keep shell, degree map, article page, library, search, and locale concerns separated.
- Remove or document prototype-only shortcuts.
- Confirm design tokens are stable enough to port.

Canonical boundary:

- [`COMPONENT_BOUNDARY_CONTRACT.md`](./COMPONENT_BOUNDARY_CONTRACT.md)

Exit criteria:

- Components have clear ownership.
- Page types map cleanly to routes.
- Styling does not depend on Vite-specific behavior.
- Tests cover route/page expectations.
- Component boundary tests pass.

## Phase 3: Next.js Scaffold

Goal:

- Create the production framework shell without changing product behavior.

Scope:

- Create Next.js app structure.
- Add filesystem routes matching current clean paths.
- Add shared layout.
- Add route-level metadata placeholders.
- Add test/build scripts.

Route mapping:

- `/` -> `app/page.tsx`
- `/degree/:degreeId` -> `app/degree/[degreeId]/page.tsx`
- `/degree/:degreeId/:slug` -> `app/degree/[degreeId]/[slug]/page.tsx`
- `/library` -> `app/library/page.tsx`
- `/library/:slug` -> `app/library/[slug]/page.tsx`

Exit criteria:

- Next app builds.
- Static/demo route parity exists.
- No JSON mutation.
- No production auth yet.

## Phase 4: Component Port

Goal:

- Move accepted React prototype components into Next.js.

Scope:

- Port shell header.
- Port locale/direction behavior.
- Port degree map.
- Port article page.
- Port library surface and virtualization.
- Port search behavior.
- Port design tokens.

Rules:

- Preserve route URLs.
- Preserve visual behavior first.
- Avoid redesign during port.
- Move client-only interactivity behind client components where needed.

Exit criteria:

- Next app visually matches accepted prototype behavior.
- Browser QA passes on route set.
- RTL/LTR switch still works.
- Metadata is route-owned where possible.

## Phase 5: Read-Only JSON Adapter

Goal:

- Connect existing site JSON without changing the JSON files.

Adapter planning only:

- [`ETL_RUNTIME_DATA_BOUNDARY.md`](./ETL_RUNTIME_DATA_BOUNDARY.md)
- [`READ_ONLY_DATA_ADAPTER_PLAN.md`](./READ_ONLY_DATA_ADAPTER_PLAN.md)

Scope:

- Build adapter that maps current JSON records into the UI model.
- Validate required fields.
- Handle missing fields with safe fallbacks.
- Keep localization layer separate from canonical records.
- Keep library/source and degree/topic boundaries explicit.

Rules:

- Adapter reads JSON.
- Adapter does not mutate JSON.
- Adapter does not silently invent canonical content.
- Adapter errors should be visible during build/test.

Exit criteria:

- Degree maps render from real data.
- Article pages render from real data.
- Library surface renders from real data.
- Search index builds from adapted records.
- Existing JSON files remain untouched.

## Phase 6: Auth And Access Boundary

Goal:

- Move access control out of frontend-only display state.

Scope:

- Define public/gated route behavior.
- Enforce protected content server-side.
- Ensure metadata does not leak protected content.
- Keep frontend access indicators as display only.

Exit criteria:

- Protected content is not delivered before authorization.
- Public metadata is safe.
- Auth behavior is tested.
- Access model aligns with product/release policy.

## Phase 7: Production Metadata And SEO

Goal:

- Replace prototype metadata effects with production route metadata.

Scope:

- Route titles.
- Route descriptions.
- Canonical URLs.
- Open Graph tags.
- Locale-aware metadata.
- Optional structured data after trust review.

Exit criteria:

- Metadata is generated from adapter data.
- Public routes have stable canonical URLs.
- Gated routes do not leak protected content.
- SEO model tests pass.

## Phase 8: Release Gate And Deployment

Goal:

- Make external preview safe.

Required gates:

- Build passes.
- Browser QA passes.
- Axe serious/critical checks pass.
- Keyboard checks pass.
- Mobile overflow checks pass in RTL and LTR.
- Route fallback checks pass.
- Search/filter checks pass.
- Auth/access checks pass if gated content is enabled.
- Trust/disclosure review passes.

Exit criteria:

- Deployment target is selected.
- Release checklist is green.
- Rollback posture is documented.
- External preview scope is explicitly approved.

## Stop Conditions

Pause migration if:

- JSON shape changes become necessary.
- Auth needs are unclear.
- Next.js port causes product redesign churn.
- Library/detail surfaces lose their product distinction.
- RTL/LTR behavior regresses.
- Browser QA cannot prove the same route behavior.

## Current Non-Goals

- No existing JSON edits.
- No live/published root mutation.
- No production auth implementation inside the prototype.
- No framework mixing.
- No public deployment until release gates exist.
