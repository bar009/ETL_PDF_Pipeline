const DEFAULT_DEGREE_ID = 'level1';
const LIBRARY_ID = 'library';

function cleanSlug(value = '') {
  return decodeURIComponent(value).trim();
}

function degreeExists(degrees, degreeId) {
  return degrees.some(degree => degree.id === degreeId);
}

function entryExists(entries, degreeId, slug) {
  return entries.some(entry => entry.degree === degreeId && entry.slug === slug);
}

export function degreePath(degreeId) {
  return degreeId === LIBRARY_ID ? '/library' : `/degree/${degreeId}`;
}

export function entryPath(entry) {
  return entry.degree === LIBRARY_ID
    ? `/library/${encodeURIComponent(entry.slug)}`
    : `/degree/${entry.degree}/${encodeURIComponent(entry.slug)}`;
}

export function parseRoute(pathname, { degrees, entries }) {
  const segments = pathname.split('/').filter(Boolean).map(cleanSlug);

  if (segments.length === 0) {
    return { degreeId: DEFAULT_DEGREE_ID, slug: null, canonicalPath: null };
  }

  if (segments[0] === 'library') {
    const slug = segments[1] ?? null;
    if (!slug) return { degreeId: LIBRARY_ID, slug: null, canonicalPath: null };
    if (entryExists(entries, LIBRARY_ID, slug)) return { degreeId: LIBRARY_ID, slug, canonicalPath: null };
    return { degreeId: LIBRARY_ID, slug: null, canonicalPath: '/library' };
  }

  if (segments[0] === 'degree') {
    const degreeId = segments[1] ?? DEFAULT_DEGREE_ID;
    if (!degreeExists(degrees, degreeId) || degreeId === LIBRARY_ID) {
      return { degreeId: DEFAULT_DEGREE_ID, slug: null, canonicalPath: '/' };
    }

    const slug = segments[2] ?? null;
    if (!slug) return { degreeId, slug: null, canonicalPath: null };
    if (entryExists(entries, degreeId, slug)) return { degreeId, slug, canonicalPath: null };
    return { degreeId, slug: null, canonicalPath: degreePath(degreeId) };
  }

  return { degreeId: DEFAULT_DEGREE_ID, slug: null, canonicalPath: '/' };
}
