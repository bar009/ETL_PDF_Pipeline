import { readFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';

const requiredTokens = [
  '--page',
  '--surface',
  '--surface-2',
  '--ink',
  '--muted',
  '--line',
  '--focus',
  '--focus-outline',
  '--focus-ring',
  '--space-1',
  '--space-2',
  '--space-3',
  '--space-4',
  '--space-5',
  '--space-6',
  '--radius',
  '--radius-card',
  '--radius-control',
  '--shadow-card',
  '--font-ui',
  '--font-display',
  '--leading-body',
  '--leading-compact'
];

async function readStylesheet() {
  return readFile(new URL('../src/styles.css', import.meta.url), 'utf8');
}

test('design tokens required by the foundation are present', async () => {
  const css = await readStylesheet();

  for (const token of requiredTokens) {
    expect(css, `${token} should be defined in the CSS token layer`).toContain(token);
  }
});

test('visible focus styling stays tokenized', async () => {
  const css = await readStylesheet();

  expect(css).toContain('outline: var(--focus-outline)');
  expect(css).toContain('box-shadow: var(--focus-ring)');
});

test('card and control radii stay restrained', async () => {
  const css = await readStylesheet();
  const radiusMatches = [...css.matchAll(/border-radius:\s*([^;]+);/g)].map(match => match[1].trim());
  const oversized = radiusMatches.filter(value => {
    if (value.startsWith('var(--radius')) return false;
    if (!value.endsWith('px')) return false;

    const numeric = Number.parseFloat(value);
    if (numeric >= 90) return false;
    return numeric > 8;
  });

  expect(oversized, 'Use explicit comments/classes for pills, but keep cards/controls at 8px or less').toEqual([]);
});
