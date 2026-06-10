# Product Definition

This document defines what the React V2 prototype is trying to become before real JSON is connected.
It is a product guardrail, not a data contract.

## Product Thesis

The site is a multilingual, Hebrew-first knowledge product for learning degree material and researching source evidence.
It should feel calm, structured, and serious without becoming an academic database wall.

The product should answer three user questions quickly:

- Where am I in the learning path?
- What should I understand from this topic?
- What source or related topic should I open next?

## Primary Users

- Learner: wants a guided path through degree material.
- Reference reader: wants to understand what a term means and where it belongs.
- Researcher: wants source context, evidence, and comparison points.
- Operator/editor: wants the UI to expose approved content safely without blurring review status or provenance.

## Product Modes

Modes are not visual skins. Each mode should emphasize a different user job.

### Learning

Primary job:

- Guide the user through what to read now and what comes next.

Surface behavior:

- Prefer clear next steps.
- Keep source-heavy details below the main lesson.
- Make progress and degree position visible.

### Encyclopedia

Primary job:

- Explain what a topic is and where it belongs.

Surface behavior:

- Prefer concise definitions and placement.
- Make category, degree, and neighboring topics easy to scan.
- Avoid turning the page into a guided lesson when the user is browsing.

### Research

Primary job:

- Show what supports the topic and what should be compared.

Surface behavior:

- Prefer source metadata, provenance, and related evidence.
- Keep the library visually distinct from topic browsing.
- Avoid card grids for source-heavy views.

## Core Surfaces

### Home

Purpose:

- Establish the site as a learning and research map.
- Help the user choose a starting point.
- Keep the first screen understandable without forcing scroll or zoom-out.

Must show:

- The active degree or recommended start.
- Clear entry points into learning, encyclopedia, and research behavior.
- Search as a useful global action, not decoration.

Must avoid:

- Giant hero blocks.
- Repeating the same message in multiple cards.
- Treating every section like a marketing landing page.

### Degree Map

Purpose:

- Show what belongs in a degree.
- Let the user browse topic rows, filter by category, and open article pages.

Must show:

- Degree navigation.
- Category filtering.
- Compact topic rows with status and summary.
- Clear empty states.

Must avoid:

- Side-panel article reading.
- Oversized cards that make a degree feel sparse.
- Hiding whether search and category filters are both active.

### Article Page

Purpose:

- Provide a focused reading page for one topic.
- Explain where the article sits in the learning structure.
- Make the next useful action obvious.

Must show:

- Article title and summary.
- Degree/category/status context without heavy metadata boxes.
- A visible article structure or outline.
- Source block.
- Related topics or next/previous navigation.

Must avoid:

- Side detail panels as the main reading experience.
- Dashboard-style grids inside the article body.
- Provenance blocks above the main reading value unless the active mode is research.

### Library

Purpose:

- Act as a research surface for books, pages, chapters, and source anchors.

Must show:

- Source rows, not topic cards.
- Source metadata such as type, year, and coverage.
- Virtualized rendering for large lists.
- Search/filter behavior that can scale to real data later.

Must avoid:

- Looking like another degree card grid.
- Mixing source browsing with lesson progression.
- Hiding source identity behind generic summaries.

## Multilingual And Direction Behavior

The shell must support multiple languages before content localization is connected.

Current foundation:

- Hebrew defaults to `lang="he"` and `dir="rtl"`.
- English switches to `lang="en"` and `dir="ltr"`.
- Shell chrome can localize independently of real content records.
- Layout should rely on logical CSS direction whenever possible.

Future rule:

- Real translated content should come from a localization/data adapter.
- Existing JSON files should not be mutated during UI prototype work.

## SEO And Shareability

Every route should eventually be shareable and understandable outside the app.

Prototype requirements:

- Article routes update the document title.
- Article routes update the meta description.
- Locale changes update `html lang` and `html dir`.

Next.js production requirements:

- Generate metadata per route.
- Add canonical URLs.
- Add Open Graph metadata for shared article/source pages.
- Keep metadata language-aware without duplicating canonical content.

## Acceptance Criteria

The product definition is satisfied when:

- A new user can tell what the site does within the first screen.
- Degree maps feel like structured learning maps, not generic cards.
- Article pages feel like real reading pages.
- Library pages feel research-oriented and source-first.
- Hebrew and English shell direction can switch without layout breaking.
- Keyboard focus, mobile layout, route fallback, and metadata behavior are tested.

## Current Non-Goals

- Do not touch existing JSON files.
- Do not implement production auth yet.
- Do not migrate to Next.js until the React prototype shape is stable.
- Do not add Vue, Angular, Svelte, or Bootstrap.
- Do not make Tailwind a dependency unless custom CSS becomes the blocker.
