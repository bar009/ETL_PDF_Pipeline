import { createHash } from 'node:crypto';
import { access, readFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

const workspaceRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');

const immutableRuntimeJsonFiles = [
  ['sites/work/v2.0/data/level1.json', '4dede9ec895c2e7d3654d092b82f5c5ebd4842d69132c0d97826341a9d9d1cca'],
  ['sites/work/v2.0/data/level2.json', '6fcffcfb36e42a4df7fc088b8fd1f9989d5bc98d83b2ae86abad49fb3677a1b4'],
  ['sites/work/v2.0/data/level3.json', 'eb7fd135d83f3c11f7535176bd2c2e32a63f0c3d80129d6995c84a250e75c498'],
  ['sites/work/v2.0/data/library.json', 'd1b395d786f78d57e288adc25f6033c5920ace894099adb5073edb752adba379'],
  ['sites/work/v2.0/data/degrees.json', '62199b36bb4fd54153910075dc41aa09876f7a5a3be8714d07fe5954ad65de73'],
  ['sites/work/v2.0/data/content.schema.json', '16515a8992ab3b1f090f0a561b1304dd4fe2d6c5c111259691f8a1a87567037f'],
  ['sites/work/v2.0/data/content.overrides.json', 'c1b6c29dba14c854e948034da127879c1b2403084caff6026915b880ea63e58d'],
  ['sites/work/v2.0/data/content.localizations.he.json', 'f40d5c58291a9689458d2aa0db26d180ae0e86dadd627cbefa90e68d3d23f49b'],
  ['sites/work/v2.0/data/entry.template.json', '8399896753fff248c25922cba3d36cc12af10db7d695043059c2d330d6bb7330'],
  ['sites/work/v2.0/data/clean_rerun_seed_manifest.json', 'a33d6acd7c7e9bdc7c26e22c03696034930178f7d48f7c4b4e5a42220db06f2b']
];

const intentionallyAbsentRuntimeJsonFiles = [
  'sites/work/v2.0/data/encyclopedia.json',
  'sites/work/v2.0/data/homepage_projection.json'
];

async function exists(path) {
  try {
    await access(path, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

async function sha256(path) {
  const bytes = await readFile(path);
  return createHash('sha256').update(bytes).digest('hex');
}

test('runtime JSON files remain byte-for-byte immutable for the React prototype', async () => {
  for (const [relativePath, expectedHash] of immutableRuntimeJsonFiles) {
    const absolutePath = resolve(workspaceRoot, relativePath);
    await expect(exists(absolutePath), `${relativePath} should exist before adapter work starts`).resolves.toBe(true);
    await expect(sha256(absolutePath), `${relativePath} changed; frontend work must not mutate ETL/runtime JSON`).resolves.toBe(expectedHash);
  }
});

test('new runtime JSON surfaces are not introduced before boundary review', async () => {
  for (const relativePath of intentionallyAbsentRuntimeJsonFiles) {
    const absolutePath = resolve(workspaceRoot, relativePath);
    await expect(exists(absolutePath), `${relativePath} should not be introduced by frontend prototype work`).resolves.toBe(false);
  }
});
