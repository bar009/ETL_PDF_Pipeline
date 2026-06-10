import Fuse from 'fuse.js';

const fuseOptions = {
  includeScore: true,
  threshold: 0.36,
  ignoreLocation: true,
  keys: [
    { name: 'title', weight: 0.34 },
    { name: 'summary', weight: 0.2 },
    { name: 'body', weight: 0.16 },
    { name: 'source', weight: 0.1 },
    { name: 'categoryLabel', weight: 0.08 },
    { name: 'status', weight: 0.06 },
    { name: 'related', weight: 0.06 }
  ]
};

export function filterEntries(entries, { categoryId = 'all', query = '' } = {}) {
  const categoryFiltered = categoryId === 'all'
    ? entries
    : entries.filter(entry => entry.category === categoryId);

  const normalizedQuery = query.trim();
  if (!normalizedQuery) return categoryFiltered;

  return new Fuse(categoryFiltered, fuseOptions)
    .search(normalizedQuery)
    .map(result => result.item);
}
