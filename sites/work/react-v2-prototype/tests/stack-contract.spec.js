import { readFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';

const requiredDependencies = [
  'react',
  'react-dom',
  'vite',
  '@vitejs/plugin-react',
  'fuse.js',
  '@tanstack/react-virtual',
  '@playwright/test',
  '@axe-core/playwright'
];

const rejectedDependencies = [
  'vue',
  '@vue',
  'angular',
  '@angular',
  'svelte',
  'bootstrap',
  'tailwindcss',
  '@tailwindcss',
  'next'
];

async function readPackageManifest() {
  const raw = await readFile(new URL('../package.json', import.meta.url), 'utf8');
  return JSON.parse(raw);
}

function getAllDependencyNames(manifest) {
  return new Set([
    ...Object.keys(manifest.dependencies ?? {}),
    ...Object.keys(manifest.devDependencies ?? {}),
    ...Object.keys(manifest.peerDependencies ?? {}),
    ...Object.keys(manifest.optionalDependencies ?? {})
  ]);
}

test('frontend stack matches the current prototype decision', async () => {
  const manifest = await readPackageManifest();
  const dependencies = getAllDependencyNames(manifest);

  for (const dependency of requiredDependencies) {
    expect(dependencies.has(dependency), `${dependency} should stay present in the prototype stack`).toBe(true);
  }
});

test('frontend stack avoids rejected framework additions', async () => {
  const manifest = await readPackageManifest();
  const dependencies = [...getAllDependencyNames(manifest)];
  const rejectedMatches = dependencies.filter(dependency =>
    rejectedDependencies.some(rejected =>
      dependency === rejected || dependency.startsWith(`${rejected}/`)
    )
  );

  expect(
    rejectedMatches,
    'Revisit docs/FRONTEND_STACK_DECISION.md before adding rejected stack dependencies'
  ).toEqual([]);
});
