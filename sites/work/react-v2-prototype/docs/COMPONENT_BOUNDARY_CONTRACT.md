# Component Boundary Contract

This document defines the portable component boundaries for the React V2 prototype.
It does not connect real JSON and does not change existing site data files.

## Goal

Keep the accepted React page model easy to move into Next.js without redesigning the product.

The prototype can still evolve visually, but page ownership should stay stable:

- `App.jsx` owns prototype-only routing, route recovery, metadata application, and global shell state.
- `ShellHeader.jsx` owns brand, global search, reading-mode tabs, language switching, and access display.
- `HomeSurface.jsx` owns the `/` entry surface.
- `DegreeRail.jsx` owns degree/library navigation.
- `TopicCard.jsx` owns topic rows on degree map pages.
- `LibrarySurface.jsx` owns the virtualized library/source list.
- `ArticlePage.jsx` owns degree topic reading pages.
- `SourceDetailPage.jsx` owns library source detail pages.

## Route To Component Mapping

Current Vite prototype:

- `/` -> `HomeSurface`
- `/degree/:degreeId` -> `DegreeRail` + `TopicCard`
- `/degree/:degreeId/:slug` -> `ArticlePage`
- `/library` -> `DegreeRail` + `LibrarySurface`
- `/library/:slug` -> `SourceDetailPage`

Future Next.js mapping:

- `app/page.tsx` should compose `HomeSurface`
- `app/degree/[degreeId]/page.tsx` should compose degree map components
- `app/degree/[degreeId]/[slug]/page.tsx` should compose `ArticlePage`
- `app/library/page.tsx` should compose `LibrarySurface`
- `app/library/[slug]/page.tsx` should compose `SourceDetailPage`

## Boundary Rules

- Page components should receive prepared view-model props, not read JSON directly.
- The local History API router should stay in `App.jsx` and should not leak into page components.
- Search and route helpers should stay in `src/lib/`.
- `ArticlePage` must not render library source records.
- `SourceDetailPage` must not render learning article structure.
- `LibrarySurface` must remain row/source oriented and virtualized.
- Auth/access display may appear in the shell, but real enforcement belongs to the future server boundary.

## Prototype-Only Shortcuts

These are allowed for now:

- In-code demo content in `src/data/demoContent.js`.
- Client-side metadata effects in `App.jsx`.
- In-code shell localization in `src/lib/locales.js`.
- Local History API routing in `src/lib/routes.js` and `App.jsx`.

These must be replaced or moved during the Next.js/data phase:

- Demo content becomes a read-only adapter over existing JSON.
- Client metadata effects become route metadata.
- Frontend access display becomes server-enforced access.
- Local routing becomes filesystem routes.

## Acceptance Criteria

The boundary is stable when:

- Each route maps to a distinct page/component responsibility.
- Source detail and topic article pages cannot accidentally collapse into one shared detail surface.
- The component tree can be ported into Next.js routes without changing URLs.
- Tests guard the route/component contract.
