# Accessibility And Multilingual Checklist

This checklist defines accessibility, RTL/LTR, and multilingual behavior for the React V2 prototype.
It does not change existing JSON.

## Goal

The site should be usable in Hebrew-first RTL mode and remain structurally sound when the shell switches to LTR.
Accessibility should be treated as a release gate, not final polish.

## Current Prototype Coverage

Already covered by the UI smoke suite:

- Serious Axe accessibility violations on a representative article route.
- Keyboard focus reaches skip link, brand, and global search.
- Article route renders as a full page, not a side panel.
- Language switch updates `html dir` from `rtl` to `ltr`.
- Language switch updates `html lang` from `he` to `en`.
- Article route updates document title and description.
- Mobile library route avoids horizontal overflow.
- Invalid route fallback avoids blank pages.

## Keyboard Requirements

Must be keyboard reachable:

- skip link
- brand/home link
- global search input
- mode tabs
- language switcher
- access indicator
- degree navigation
- category filters
- topic rows
- source rows
- article back button
- article outline links
- article source button
- previous/next article buttons

Rules:

- Focus order should follow visual and reading order.
- Focus should never disappear behind sticky UI.
- Disabled buttons must be visibly disabled and skipped by action checks.
- Interactive rows must use button or link semantics, not clickable divs.

Future release-gate checks:

- Add keyboard tab-path checks for degree map, library, and article controls.
- Add Enter/Space activation checks for rows and tabs.
- Add skip-link target validation after navigation.

## Focus Requirements

Visible focus must exist for:

- links
- buttons
- search inputs
- tabs
- row buttons
- language buttons
- source buttons

Rules:

- Focus state should be high contrast.
- Focus state should not rely only on color.
- Focus state should remain visible in RTL and LTR.

Current implementation:

- Shared focus ring is defined in CSS.
- Language switcher participates in focus styling.

## Heading And Landmark Requirements

Map pages:

- Use one primary page heading inside the home/degree band.
- Content pane should be reachable from skip link.
- Degree navigation should have an accessible label.

Article pages:

- Use one article `h1`.
- Article sections should use ordered headings.
- Article outline should link to real sections.
- Source and related sections should be secondary to the main reading section.

Library pages:

- Library surface should have a research heading.
- Source list should expose list/listitem semantics or a clear equivalent.

Future release-gate checks:

- Add heading-order assertions for article and library routes.
- Add landmark coverage for navigation, main content, and article.

## RTL/LTR Requirements

Hebrew mode:

- `html lang="he"`.
- `html dir="rtl"`.
- Shell chrome is Hebrew.
- Text alignment follows RTL.

English mode:

- `html lang="en"`.
- `html dir="ltr"`.
- Shell chrome is English.
- Text alignment follows LTR.

CSS rules:

- Prefer `text-align: start`.
- Prefer logical properties such as `inset-inline-start`, `margin-inline`, and `padding-inline`.
- Avoid physical `left`/`right` unless the visual meaning is truly physical.

Future release-gate checks:

- Add visual/mobile smoke for both RTL and LTR.
- Add overflow checks after switching language.
- Add search/filter interaction checks after switching language.

## Multilingual Content Boundary

Current scope:

- Shell chrome can switch language.
- Document language and direction can switch.
- Metadata suffix and shell labels can switch.
- Demo content remains whatever the in-code content currently provides.

Future data scope:

- Real localized content should come from a localization/data adapter.
- Existing site JSON should remain untouched during prototype UI work.
- Canonical content and localized display content should stay separable.

Rules:

- Do not fake full translation by mutating demo data into mixed-language content.
- Do not bake Hebrew-specific layout assumptions into article components.
- Do not let language switching change route identity.

## Mobile Requirements

Must hold for both directions:

- No horizontal overflow.
- Header controls remain reachable.
- Article context stack does not hide the article.
- Library rows remain readable.
- Search input remains usable.

Future release-gate checks:

- Add mobile article screenshot checks in RTL and LTR.
- Add mobile library screenshot checks in RTL and LTR.
- Add mobile search/filter checks.

## Accessibility Release Gate

Before external preview, require:

- Build passes.
- Playwright UI suite passes.
- Axe serious/critical checks pass on home, article, and library routes.
- Keyboard tab-path checks pass on map, article, and library.
- Mobile overflow checks pass in RTL and LTR.
- Language switch checks pass.
- Invalid-route fallback checks pass.

## Known Prototype Gaps

- Color contrast rule is currently disabled in Axe smoke and should be revisited before release.
- Heading-order assertions are not yet automated.
- Full keyboard interaction coverage is not yet automated.
- Real localized content is not connected yet.
- Production auth/access is not implemented yet.
