import { describe, expect, it } from 'vitest';
import { legalRefinements, resolveMode } from './modeResolver.js';

const libraryRoute = { degreeId: 'library', slug: null };
const libraryEntryRoute = { degreeId: 'library', slug: 'some-source' };
const level1Route = { degreeId: 'level1', slug: 'some-topic' };
const level2Route = { degreeId: 'level2', slug: 'another-topic' };

describe('legalRefinements', () => {
  it('returns no refinements on library routes', () => {
    expect(legalRefinements('library')).toEqual([]);
  });

  it('returns learning+encyclopedia on degree-of-study routes', () => {
    expect(legalRefinements('level1')).toEqual(['learning', 'encyclopedia']);
    expect(legalRefinements('level2')).toEqual(['learning', 'encyclopedia']);
    expect(legalRefinements('level3')).toEqual(['learning', 'encyclopedia']);
  });

  it('never exposes research as a refinement on degree-of-study routes', () => {
    expect(legalRefinements('level1')).not.toContain('research');
  });
});

describe('resolveMode — acceptance criteria from spec', () => {
  // Criterion 1: library always forces research
  it('forces research on /library regardless of source or refinement', () => {
    expect(resolveMode({ route: libraryRoute, source: 'path-load' })).toBe('research');
    expect(resolveMode({ route: libraryEntryRoute, source: 'internal-link', fromDegreeId: 'level1' })).toBe('research');
    expect(resolveMode({
      route: libraryRoute,
      source: 'mode-tab-refinement',
      refinement: 'learning',
      prevResolved: 'research'
    })).toBe('research');
  });

  // Criterion 2: degree tab/tile → learning, entries inside same degree → learning
  it('resolves degree-tab and degree-tile clicks to learning', () => {
    expect(resolveMode({ route: level1Route, source: 'degree-tab' })).toBe('learning');
    expect(resolveMode({ route: level1Route, source: 'degree-tile' })).toBe('learning');
  });

  it('preserves prevResolved on same-degree internal-link (does not reset to learning)', () => {
    // If the user refined to Encyclopedia and then clicks another topic in the same degree,
    // they expect to stay in Encyclopedia, not get reset to Learning.
    expect(resolveMode({
      route: level1Route,
      source: 'internal-link',
      fromDegreeId: 'level1',
      prevResolved: 'encyclopedia'
    })).toBe('encyclopedia');

    expect(resolveMode({
      route: level1Route,
      source: 'internal-link',
      fromDegreeId: 'level1',
      prevResolved: 'learning'
    })).toBe('learning');
  });

  // Criterion 3: pasted/refreshed URL → encyclopedia (never learning)
  it('resolves path-load on degree-of-study routes to encyclopedia, not learning', () => {
    expect(resolveMode({ route: level1Route, source: 'path-load' })).toBe('encyclopedia');
    expect(resolveMode({ route: level2Route, source: 'path-load' })).toBe('encyclopedia');
  });

  // Criterion 4 & 5: mode-tab-refinement clamps to legal set, never changes route
  it('honors legal refinements (learning↔encyclopedia on degree routes)', () => {
    expect(resolveMode({
      route: level1Route,
      source: 'mode-tab-refinement',
      refinement: 'learning',
      prevResolved: 'encyclopedia'
    })).toBe('learning');

    expect(resolveMode({
      route: level1Route,
      source: 'mode-tab-refinement',
      refinement: 'encyclopedia',
      prevResolved: 'learning'
    })).toBe('encyclopedia');
  });

  // Criterion 6: research is never a refinement on degree-of-study routes
  it('falls back to prevResolved when refinement is illegal on degree route', () => {
    expect(resolveMode({
      route: level1Route,
      source: 'mode-tab-refinement',
      refinement: 'research',
      prevResolved: 'learning'
    })).toBe('learning');
  });

  // Criterion 7: home-mode-pick honors the user's chosen mode
  it('honors home-mode-pick refinements', () => {
    expect(resolveMode({
      route: level1Route,
      source: 'home-mode-pick',
      refinement: 'learning'
    })).toBe('learning');

    expect(resolveMode({
      route: level1Route,
      source: 'home-mode-pick',
      refinement: 'encyclopedia'
    })).toBe('encyclopedia');

    expect(resolveMode({
      route: libraryRoute,
      source: 'home-mode-pick',
      refinement: 'research'
    })).toBe('research');
  });
});

describe('resolveMode — additional rules', () => {
  it('resolves cross-degree internal-link to encyclopedia', () => {
    expect(resolveMode({
      route: level2Route,
      source: 'internal-link',
      fromDegreeId: 'level1'
    })).toBe('encyclopedia');
  });

  it('resolves search-result to encyclopedia even inside a degree', () => {
    expect(resolveMode({
      route: level1Route,
      source: 'search-result'
    })).toBe('encyclopedia');
  });

  it('falls back to encyclopedia for unknown sources', () => {
    expect(resolveMode({ route: level1Route, source: 'unknown' })).toBe('encyclopedia');
    expect(resolveMode({ route: level1Route })).toBe('encyclopedia');
  });

  it('handles missing fromDegreeId on internal-link as cross-degree', () => {
    expect(resolveMode({
      route: level1Route,
      source: 'internal-link',
      prevResolved: 'learning'
    })).toBe('encyclopedia');
  });

  it('falls back to encyclopedia when home-mode-pick refinement is invalid', () => {
    expect(resolveMode({
      route: level1Route,
      source: 'home-mode-pick',
      refinement: 'bogus'
    })).toBe('encyclopedia');
  });
});
