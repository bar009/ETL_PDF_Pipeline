// The read-only boundary, runnable in `npm test` (systemic plan WS10).
//
// Frontend iteration must never mutate or commit runtime JSON. This replaces
// the old Playwright no-json-mutation spec, which pinned byte hashes of
// old-workspace files that do not exist in this repo.

import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { READ_ONLY_SOURCE_FILES, RESERVED_SOURCE_FILES } from './adapterContract.js';

const prototypeRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const publicData = join(prototypeRoot, 'public', 'data');
const libDir = join(prototypeRoot, 'src', 'lib');

describe('runtime JSON stays out of git', () => {
  it('public/data contains no committed JSON', () => {
    const jsonFiles = readdirSync(publicData).filter(name => name.endsWith('.json'));
    expect(jsonFiles).toEqual([]);
  });

  it('reserved runtime surfaces are not introduced before boundary review', () => {
    for (const relativePath of RESERVED_SOURCE_FILES) {
      expect(existsSync(join(prototypeRoot, relativePath)), relativePath).toBe(false);
    }
  });
});

describe('the contract names this repo, not the old workspace', () => {
  it('all source files live under public/data', () => {
    for (const path of [...READ_ONLY_SOURCE_FILES, ...RESERVED_SOURCE_FILES]) {
      expect(path.startsWith('public/data/'), path).toBe(true);
      expect(path.includes('v2.0'), path).toBe(false);
    }
  });
});

describe('the adapter layer is read-only', () => {
  const libSources = readdirSync(libDir)
    .filter(name => name.endsWith('.js') && !name.endsWith('.test.js'))
    .map(name => [name, readFileSync(join(libDir, name), 'utf8')]);

  it('never writes through fetch', () => {
    for (const [name, source] of libSources) {
      expect(/method:\s*['"](POST|PUT|PATCH|DELETE)['"]/i.test(source), name).toBe(false);
    }
  });

  it('never touches the filesystem', () => {
    for (const [name, source] of libSources) {
      expect(/from\s+['"]node:fs/.test(source), name).toBe(false);
      expect(/require\(\s*['"]fs['"]\s*\)/.test(source), name).toBe(false);
    }
  });
});
