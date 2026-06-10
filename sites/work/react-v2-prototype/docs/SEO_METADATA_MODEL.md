# SEO And Metadata Model

This document defines how routes should expose metadata in the React V2 prototype and later Next.js app.
It does not connect real JSON and does not mutate existing data files.

## Goal

Every meaningful route should be understandable when opened directly, shared, indexed, or previewed.
Metadata should reflect the product surface: degree map, article, library, or source detail.

## Current Prototype Behavior

The prototype currently updates:

- `document.title`
- `meta[name="description"]`
- `link[rel="canonical"]`
- Open Graph title, description, type, URL, and locale
- `html lang`
- `html dir`

This is enough for prototype validation, but not final production SEO.

## Metadata Ownership

Prototype:

- `src/lib/locales.js` owns small locale-aware metadata helpers.
- `App.jsx` applies metadata with client-side effects.

Future Next.js app:

- Route files should own metadata generation.
- Data adapter should provide read-only metadata inputs.
- Auth/access rules must run before protected metadata reveals protected content.

## Route Metadata Requirements

### `/`

Title:

- Site name plus default degree/home label.

Description:

- Short explanation of the learning/research product and recommended starting point.

Indexing target:

- Yes, if public preview is approved.

### `/degree/:degreeId`

Title:

- Degree title plus site name.

Description:

- Degree summary and browse purpose.

Metadata fields:

- degree id
- degree label
- degree title
- degree summary
- active locale

Indexing target:

- Yes, if the degree is public and access policy allows it.

### `/degree/:degreeId/:slug`

Title:

- Article title plus site name.

Description:

- Article summary plus degree context.

Metadata fields:

- topic slug
- topic title
- topic summary
- degree id
- degree label
- category
- status
- active locale
- canonical URL

Indexing target:

- Yes for public articles.
- No or restricted for gated material.

### `/library`

Title:

- Library/research surface title plus site name.

Description:

- Source archive and research browsing summary.

Metadata fields:

- library title
- library summary
- active locale

Indexing target:

- Yes if source browsing is public.

### `/library/:slug`

Title:

- Source title plus site name.

Description:

- Source summary plus source type/year/coverage when available.

Metadata fields:

- source slug
- source title
- source summary
- source kind
- source year
- source coverage
- canonical URL
- active locale

Indexing target:

- Depends on source access rights and trust/disclosure decisions.

## Locale-Aware Metadata

Rules:

- `html lang` must match active shell locale.
- `html dir` must match active shell direction.
- Metadata title suffix should localize.
- Description should use localized display content when approved/localized content exists.
- When localized content is missing, metadata may fall back to canonical content.

Future data adapter rule:

- Metadata should never require mutating canonical JSON.
- Localized metadata should come from the localization layer or approved display adapter.

## Canonical URLs

Prototype:

- Clean paths are stable.
- Canonical tags are updated client-side for every route in the prototype.

Future Next.js:

- Add canonical URLs for every public route.
- Keep route identity stable across locale changes unless a deliberate locale-prefixed URL model is adopted.
- If locale-prefixed URLs are adopted later, define redirects and alternate links before rollout.

## Open Graph And Social Preview

The prototype now includes:

- `og:title`
- `og:description`
- `og:type`
- `og:url`
- `og:locale`

Future Next.js route metadata may add:

- optional preview image if a visual asset lane is approved

Surface-specific type:

- Article routes: `article`
- Degree/library pages: `website`
- Source detail pages: `article` or `book`-like structured data only if policy supports it

## Structured Data

Defer structured data until real data is connected.

Potential future shapes:

- `Article` for topic pages.
- `Book` or `CreativeWork` for source details.
- `BreadcrumbList` for degree/article hierarchy.

Do not add structured data until field quality and trust/disclosure rules are reviewed.

## Access And Trust Rules

Metadata must not leak protected content.

Rules:

- Public pages may expose title and summary.
- Gated pages must use safe public metadata or noindex.
- Source claims/provenance should not be overstated.
- Trust/disclosure copy should be decided before external preview.

## Acceptance Criteria

The metadata model is working when:

- Each route has a clear title.
- Each route has a meaningful description.
- Article metadata includes article and degree context.
- Library/source metadata is source-first.
- Locale changes update `lang`, `dir`, and title suffix.
- Future Next.js migration can move metadata from client effects to route metadata without redesign.

## Current Prototype Gaps

- Structured data is not implemented.
- Metadata still uses demo content, not real JSON.
- Access-aware metadata is not implemented.
