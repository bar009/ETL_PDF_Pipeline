# Information Architecture

This document defines the page and route model for the React V2 prototype.
It is a UI/navigation contract and does not change existing JSON.

## Route Thesis

Routes should explain product intent.

- List routes are maps.
- Slug routes are reading or detail pages.
- Library routes are research surfaces.
- Invalid routes recover to the nearest useful screen.

## Current Routes

### `/`

Purpose:

- Default entry into the site.
- Opens the product home surface.

Current behavior:

- Resolves to the first learning degree as the default learning context.
- Shows the shell and a compact home entry surface.
- Offers direct starts into Degree 1, library research, reading modes, and a recommended topic.

Future Next.js mapping:

- `app/page.tsx`

### `/degree/:degreeId`

Purpose:

- Degree map/list page.
- Helps users understand what belongs in one degree.

Current behavior:

- Shows degree navigation.
- Shows category filters.
- Shows topic rows.
- Search and category filters combine.

Must not:

- Render the full article body as a side panel.
- Hide active list/search context.

Future Next.js mapping:

- `app/degree/[degreeId]/page.tsx`

### `/degree/:degreeId/:slug`

Purpose:

- Full article page for one degree topic.
- Focused reading surface.

Current behavior:

- Shows article page.
- Hides degree home band.
- Shows context rail, article title/summary, article structure, source, related topics, and neighbor navigation.
- Updates metadata in the prototype.

Must not:

- Look like a modal or side detail panel.
- Use dashboard-style metadata grids.

Future Next.js mapping:

- `app/degree/[degreeId]/[slug]/page.tsx`

### `/library`

Purpose:

- Research surface for sources.

Current behavior:

- Uses library degree state.
- Forces research mode.
- Shows virtualized source rows.
- Keeps source metadata visible.

Must not:

- Reuse topic-card visual language as the primary library pattern.

Future Next.js mapping:

- `app/library/page.tsx`

### `/library/:slug`

Purpose:

- Source detail page.

Current behavior:

- Uses a dedicated source detail page.
- Keeps library mode as research.
- Emphasizes source identity, year/type/coverage, related topics, and provenance.
- Does not reuse the learning article page.

Future Next.js mapping:

- `app/library/[slug]/page.tsx`

## Navigation Rules

Degree navigation:

- Selecting a degree opens its degree map route.
- Selecting library opens `/library`.
- Selecting library also switches to research mode.

Topic/source rows:

- Selecting a topic row opens the article route.
- Selecting a source row opens the source detail route.

Mode tabs:

- Change page behavior/emphasis.
- Must not unexpectedly replace selected entry.
- Research mode is forced for library routes.

Search:

- Empty query returns category-filtered entries.
- Non-empty query uses fuzzy search.
- Search should not mutate data.
- Search on list routes filters visible rows.
- Article routes keep the selected article stable even if the current query would hide it from the list.

Back/forward:

- Browser history should restore degree, library, and selected entry.
- Invalid routes should never create blank screens.

## Invalid Route Fallbacks

Fallback principles:

- Invalid root path falls back to `/`.
- Invalid degree falls back to `/`.
- Invalid topic slug falls back to `/degree/:degreeId`.
- Invalid library slug falls back to `/library`.

Fallback behavior should use `replaceState` so bad URLs do not create noisy history loops.

## Page Types

### Home Entry Surface

Includes:

- shell header
- compact product hero
- primary degree start
- library research entry
- path and mode shortcuts

Used by:

- `/`

### Map Page

Includes:

- shell header
- optional home/degree band
- degree rail
- content toolbar
- filters
- list rows

Used by:

- `/degree/:degreeId`

### Article Page

Includes:

- shell header
- article context rail
- article hero
- quiet metadata line
- reading section
- source block
- related/neighbor navigation

Used by:

- `/degree/:degreeId/:slug`

### Library Research Page

Includes:

- shell header
- library home band
- source table/list surface
- virtualized source rows
- source metadata

Used by:

- `/library`

### Source Detail Page

Target shape:

- source identity first
- bibliographic metadata
- coverage/provenance
- linked degree topics
- source text or page anchors when available

Used by:

- `/library/:slug`

## Next.js Porting Notes

When the prototype moves to Next.js:

- Convert route parsing into filesystem routes.
- Keep invalid-route fallback behavior explicit.
- Move metadata from client effects to route metadata generation.
- Keep page types separate.
- Keep the JSON adapter read-only at first.
- Preserve route URLs so existing links do not break.

## Acceptance Criteria

The information architecture is working when:

- Users can predict what type of page a URL opens.
- Degree routes feel like maps.
- Topic slug routes feel like articles.
- Library routes feel source-first.
- Back/forward behavior is stable.
- Invalid URLs recover safely.
- The route model can port to Next.js without redesigning the product.
