---
name: preview-playwright-ui-verification
description: Verify website UI changes against a live local preview using Playwright and fallback code audits. Use when the user asks to check the real UI, compare homepage and topic pages, validate whether changes are visible in a preview, or confirm that proportions, hierarchy, and scrolling improved in practice.
---

# Preview Playwright UI Verification

Use this skill when UI work needs real preview validation instead of code-only confidence.

The goal is to confirm that the user can actually see the change in a local preview and that the page feels better at normal zoom.

## Read First

1. `AGENTS.md`
2. the target preview path
3. the target site's `index.html`
4. the target site's main render file
5. the target site's main theme CSS

For concrete checks, read:

- `references/checklist.md`

## Preferred Workflow

1. confirm which preview path is being served
2. confirm the local URL responds
3. open the homepage
4. inspect one representative topic page
5. inspect one dense or worst-case topic page
6. verify that the preview files match the source files

## Browser Workflow

If Playwright works:

1. go to the local preview URL
2. snapshot homepage
3. snapshot one topic page
4. compare visible hierarchy, scroll burden, and scale

If the `@playwright/cli` session layer is flaky but Playwright itself is available, use:

- `scripts/playwright_probe.js`

This helper launches Chrome through `playwright-core`, opens the target URL, and saves a full-page screenshot.
It also accepts optional storage-state JSON so you can unlock a preview or set a viewing mode without mutating site code.

If Playwright fails:

1. say so clearly
2. verify the server responds
3. verify preview files match source files
4. continue with a code-audit-based UI review

## What To Verify

- the user is looking at the right preview
- the homepage first viewport changed in a visible way
- the topic page lead changed in a visible way
- the scale feels natural at 100% zoom
- the user reaches useful reading sooner

## Hard Rule

Do not claim “the preview is updated” unless either:

1. browser verification succeeded
2. file sync was verified directly

## Output Standard

Report:

1. what was verified in browser
2. what was verified by file sync
3. what still remains uncertain if tooling failed
