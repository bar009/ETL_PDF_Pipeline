import { readFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';

const protectedRuntimeFiles = [
  'level1.json',
  'level2.json',
  'level3.json',
  'library.json',
  'degrees.json',
  'content.schema.json',
  'content.overrides.json',
  'content.localizations.he.json',
  'entry.template.json',
  'clean_rerun_seed_manifest.json'
];

const reservedRuntimeFiles = [
  'encyclopedia.json',
  'homepage_projection.json'
];

const forbiddenFrontendMutations = [
  'edit JSON content',
  'normalize JSON formatting',
  'patch missing fields',
  'rewrite arrays or object keys',
  'migrate schema shape',
  'auto-fix invalid or incomplete records',
  'create replacement runtime JSON files'
];

async function readDoc(relativePath) {
  return readFile(new URL(relativePath, import.meta.url), 'utf8');
}

test('ETL runtime data boundary documents every guarded runtime file', async () => {
  const boundaryDoc = await readDoc('../docs/ETL_RUNTIME_DATA_BOUNDARY.md');

  expect(boundaryDoc).toContain('sites/work/v2.0/data/');
  for (const fileName of protectedRuntimeFiles) {
    expect(boundaryDoc, `${fileName} should be documented as protected`).toContain(fileName);
  }
  for (const fileName of reservedRuntimeFiles) {
    expect(boundaryDoc, `${fileName} should be documented as reserved`).toContain(fileName);
  }
});

test('ETL runtime data boundary documents forbidden frontend mutations', async () => {
  const boundaryDoc = await readDoc('../docs/ETL_RUNTIME_DATA_BOUNDARY.md');

  for (const phrase of forbiddenFrontendMutations) {
    expect(boundaryDoc, `${phrase} should stay explicitly forbidden`).toContain(phrase);
  }
  expect(boundaryDoc).toContain('Content fixes belong to the ETL pipeline');
});

test('read-only adapter plan remains a plan and not implementation', async () => {
  const adapterPlan = await readDoc('../docs/READ_ONLY_DATA_ADAPTER_PLAN.md');

  expect(adapterPlan).toContain('This is a plan only.');
  expect(adapterPlan).toContain('No adapter implementation starts in this checkpoint.');
  expect(adapterPlan).toContain('ADAPTER_INTERFACE_CONTRACT.md');
  expect(adapterPlan).toContain('read-only translation layer');
  expect(adapterPlan).toContain('Fallbacks must be display-only. They must not be written back to JSON.');
});

test('adapter interface contract documents synthetic-only readiness work', async () => {
  const interfaceContract = await readDoc('../docs/ADAPTER_INTERFACE_CONTRACT.md');

  expect(interfaceContract).toContain('It is not an adapter implementation.');
  expect(interfaceContract).toContain('synthetic JavaScript fixtures only');
  expect(interfaceContract).toContain('It does not read `sites/work/v2.0/data`');
  expect(interfaceContract).toContain('The UI should not consume raw runtime JSON records.');
});

test('checkpoint documents clean snapshot commands and adapter pause', async () => {
  const checkpoint = await readDoc('../docs/REACT_V2_PROTOTYPE_CHECKPOINT_2026_06_03.md');

  expect(checkpoint).toContain('git add sites/work/react-v2-prototype');
  expect(checkpoint).toContain('no files under `sites/work/v2.0/data/*.json` are staged');
  expect(checkpoint).toContain('Adapter implementation is paused.');
});
