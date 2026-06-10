// Boundary tests for the read-only adapter layer (STRUCTURE_ROADMAP Phase 3).
//
// The four areas the roadmap requires adapter tests to cover:
//   1. missing fields        — hard-fail vs display-fallback policy
//   2. unknown routes        — parseRoute must always land somewhere safe
//   3. locale direction      — rtl/ltr resolution and fallback
//   4. relation references   — unresolvable relations report, never break

import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  collectRelationFindings,
  validateAdapterFixture,
  validateViewModelShape
} from './adapterContract.js';
import { loadContent } from './contentAdapter.js';
import { getLocale, getPageMeta, locales } from './locales.js';
import { parseRoute } from './routes.js';
import {
  duplicateRouteFixture,
  missingRequiredFieldFixture,
  validAdapterFixture
} from '../../tests/fixtures/adapterContractFixtures.js';

describe('missing fields', () => {
  it('accepts the valid synthetic fixture', () => {
    expect(validateAdapterFixture(validAdapterFixture)).toEqual([]);
  });

  it('rejects blank required fields on degrees and entries', () => {
    const errors = validateAdapterFixture(missingRequiredFieldFixture);
    expect(errors).toContain('degree.title is required');
    expect(errors).toContain('topicEntry.title must be a non-empty string');
  });

  it('rejects a non-array related field', () => {
    const broken = { ...validAdapterFixture.entries[0], related: 'not-an-array' };
    expect(validateViewModelShape('topicEntry', broken))
      .toContain('topicEntry.related must be an array');
  });

  it('flags duplicate route slugs as hard failures', () => {
    const errors = validateAdapterFixture(duplicateRouteFixture);
    expect(errors.some(error => error.startsWith('duplicate route slug:'))).toBe(true);
  });
});

describe('unknown routes', () => {
  const content = validAdapterFixture;

  it('sends an unknown top-level segment home', () => {
    expect(parseRoute('/nonsense', content))
      .toEqual({ degreeId: 'level1', slug: null, canonicalPath: '/' });
  });

  it('sends an unknown degree id home', () => {
    expect(parseRoute('/degree/level9', content))
      .toEqual({ degreeId: 'level1', slug: null, canonicalPath: '/' });
  });

  it('sends an unknown entry slug back to its degree list', () => {
    expect(parseRoute('/degree/level1/no-such-entry', content))
      .toEqual({ degreeId: 'level1', slug: null, canonicalPath: '/degree/level1' });
  });

  it('sends an unknown library slug back to the library', () => {
    expect(parseRoute('/library/no-such-source', content))
      .toEqual({ degreeId: 'library', slug: null, canonicalPath: '/library' });
  });

  it('refuses to treat the library as a degree', () => {
    expect(parseRoute('/degree/library', content))
      .toEqual({ degreeId: 'level1', slug: null, canonicalPath: '/' });
  });

  it('resolves a known encoded slug without a redirect', () => {
    expect(parseRoute('/degree/level1/synthetic%2Dtopic', content))
      .toEqual({ degreeId: 'level1', slug: 'synthetic-topic', canonicalPath: null });
  });
});

describe('locale direction', () => {
  it('resolves Hebrew as rtl and English as ltr', () => {
    expect(getLocale('he').dir).toBe('rtl');
    expect(getLocale('en').dir).toBe('ltr');
  });

  it('falls back to the rtl default locale for unknown ids', () => {
    expect(getLocale('fr')).toBe(locales[0]);
    expect(getLocale('fr').dir).toBe('rtl');
  });

  it('builds page metadata in either direction without reshaping content', () => {
    for (const locale of locales) {
      const meta = getPageMeta({
        currentDegree: validAdapterFixture.degrees[0],
        entry: validAdapterFixture.entries[0],
        isArticleRoute: true,
        isHomeRoute: false,
        locale,
        pathname: '/degree/level1/synthetic-topic'
      });
      expect(validateViewModelShape('routeMetadata', meta)).toEqual([]);
      expect(meta.ogType).toBe('article');
    }
  });
});

describe('relation references', () => {
  it('reports an unresolvable related target without failing the fixture', () => {
    // 'Synthetic Neighbor' resolves to no entry: report-only by policy.
    const findings = collectRelationFindings(validAdapterFixture);
    expect(findings).toEqual([
      {
        policy: 'reportOnly',
        kind: 'missing related target',
        entry: 'synthetic-topic',
        target: 'Synthetic Neighbor'
      }
    ]);
    expect(validateAdapterFixture(validAdapterFixture)).toEqual([]);
  });

  it('resolves relations by slug or title', () => {
    const entries = [
      { ...validAdapterFixture.entries[0], related: ['synthetic-source-record'] },
      { ...validAdapterFixture.entries[1], related: ['Synthetic Topic'] }
    ];
    expect(collectRelationFindings({ entries })).toEqual([]);
  });
});

describe('runtime JSON boundary (loadContent)', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function stubRuntimeData(levelOneEntries) {
    const files = {
      '/data/degrees.json': { level1: { title: 'Degree 1', color: '#8c6a24' } },
      '/data/level1.json': {
        categories: { symbols: { id: 'symbols', title: 'Symbols' } },
        entries: levelOneEntries
      },
      '/data/level2.json': { categories: {}, entries: [] },
      '/data/level3.json': { categories: {}, entries: [] },
      '/data/library.json': { categories: {}, entries: [] }
    };
    vi.stubGlobal('fetch', vi.fn(async path => ({
      ok: true,
      json: async () => files[path]
    })));
  }

  it('drops entries missing hard-fail fields instead of rendering them', async () => {
    stubRuntimeData([
      {
        slug: 'kept-entry',
        title: 'Kept Entry',
        type: 'topic',
        category: 'symbols',
        short_summary: 'kept',
        source_notes: ['Fixture Work | section 1']
      },
      { title: 'No slug — must be dropped', type: 'topic', source_notes: ['x'] },
      { slug: 'no-title-must-be-dropped', type: 'topic', source_notes: ['x'] },
      { slug: 'no-source-must-be-dropped', title: 'No Source', type: 'topic' }
    ]);

    const { entries } = await loadContent();
    expect(entries.map(entry => entry.slug)).toEqual(['kept-entry']);
  });

  it('fills display fallbacks so optional gaps never reshape the view model', async () => {
    stubRuntimeData([
      {
        slug: 'sparse-entry',
        title: 'Sparse Entry',
        type: 'topic',
        full_summary: 'Body only.',
        source_notes: ['Fixture Work | Fixture Section | section 1'],
        knowledge_links: [{ slug: 'linked-elsewhere' }]
      }
    ]);

    const { degrees, entries } = await loadContent();
    expect(validateAdapterFixture({ degrees: [degrees[0]], entries })).toEqual([]);
    expect(entries[0].summary).toBe('Body only.');
    expect(entries[0].related).toEqual(['linked-elsewhere']);
    expect(entries[0].source).toBe('Fixture Work | Fixture Section | section 1');
    expect(entries[0].status).not.toBe('');
  });
});
