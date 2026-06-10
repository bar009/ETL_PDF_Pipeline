export const ADAPTER_CONTRACT_VERSION = 'react-v2-read-only-adapter-contract-v1';

export const READ_ONLY_SOURCE_FILES = Object.freeze([
  'sites/work/v2.0/data/degrees.json',
  'sites/work/v2.0/data/level1.json',
  'sites/work/v2.0/data/level2.json',
  'sites/work/v2.0/data/level3.json',
  'sites/work/v2.0/data/library.json',
  'sites/work/v2.0/data/content.schema.json',
  'sites/work/v2.0/data/content.overrides.json',
  'sites/work/v2.0/data/content.localizations.he.json'
]);

export const RESERVED_SOURCE_FILES = Object.freeze([
  'sites/work/v2.0/data/encyclopedia.json',
  'sites/work/v2.0/data/homepage_projection.json'
]);

export const VIEW_MODEL_SHAPES = Object.freeze({
  degree: Object.freeze({
    required: Object.freeze(['id', 'label', 'title', 'summary', 'tone', 'categories']),
    arrays: Object.freeze(['categories'])
  }),
  topicEntry: Object.freeze({
    required: Object.freeze([
      'degree',
      'title',
      'slug',
      'category',
      'categoryLabel',
      'type',
      'status',
      'summary',
      'body',
      'source',
      'related'
    ]),
    arrays: Object.freeze(['related'])
  }),
  librarySource: Object.freeze({
    required: Object.freeze([
      'degree',
      'title',
      'slug',
      'category',
      'categoryLabel',
      'type',
      'status',
      'summary',
      'body',
      'source',
      'sourceYear',
      'sourceKind',
      'coverage',
      'related'
    ]),
    arrays: Object.freeze(['related'])
  }),
  routeMetadata: Object.freeze({
    required: Object.freeze(['title', 'description', 'canonicalPath', 'ogType']),
    arrays: Object.freeze([])
  })
});

export const MISSING_FIELD_POLICY = Object.freeze({
  hardFail: Object.freeze(['slug', 'title', 'degree', 'source']),
  displayFallbackOnly: Object.freeze(['summary', 'status', 'related', 'sourceYear', 'sourceKind', 'coverage'])
});

export const ADAPTER_ERROR_POLICY = Object.freeze({
  hardFail: Object.freeze([
    'invalid JSON shape',
    'duplicate route slug',
    'degree/library boundary crossing',
    'protected content without access policy'
  ]),
  reportOnly: Object.freeze([
    'optional metadata gap',
    'missing related target',
    'long title',
    'localization coverage gap'
  ])
});

function isBlankString(value) {
  return typeof value !== 'string' || value.trim().length === 0;
}

export function getViewModelShape(kind) {
  const shape = VIEW_MODEL_SHAPES[kind];
  if (!shape) throw new Error(`Unknown adapter view model kind: ${kind}`);
  return shape;
}

export function validateViewModelShape(kind, value) {
  const shape = getViewModelShape(kind);
  const errors = [];

  for (const field of shape.required) {
    if (!(field in value)) {
      errors.push(`${kind}.${field} is required`);
      continue;
    }

    if (!shape.arrays.includes(field) && isBlankString(value[field])) {
      errors.push(`${kind}.${field} must be a non-empty string`);
    }
  }

  for (const field of shape.arrays) {
    if (!Array.isArray(value[field])) {
      errors.push(`${kind}.${field} must be an array`);
    }
  }

  return errors;
}

// Relation references are report-only per ADAPTER_ERROR_POLICY: a related
// item that resolves to no entry must surface as a finding, never break a page.
export function collectRelationFindings({ entries }) {
  const knownTargets = new Set();
  for (const entry of entries) {
    knownTargets.add(entry.slug);
    knownTargets.add(entry.title);
  }

  const findings = [];
  for (const entry of entries) {
    for (const target of entry.related ?? []) {
      if (!knownTargets.has(target)) {
        findings.push({
          policy: 'reportOnly',
          kind: 'missing related target',
          entry: entry.slug,
          target
        });
      }
    }
  }
  return findings;
}

export function validateAdapterFixture({ degrees, entries }) {
  const errors = [];
  const routeKeys = new Set();

  for (const degree of degrees) {
    errors.push(...validateViewModelShape('degree', degree));
  }

  for (const entry of entries) {
    const kind = entry.degree === 'library' ? 'librarySource' : 'topicEntry';
    errors.push(...validateViewModelShape(kind, entry));

    if (entry.degree === 'library' && kind !== 'librarySource') {
      errors.push(`${entry.slug} crossed the library source boundary`);
    }

    const routeKey = entry.degree === 'library'
      ? `library/${entry.slug}`
      : `degree/${entry.degree}/${entry.slug}`;
    if (routeKeys.has(routeKey)) {
      errors.push(`duplicate route slug: ${routeKey}`);
    }
    routeKeys.add(routeKey);
  }

  return errors;
}
