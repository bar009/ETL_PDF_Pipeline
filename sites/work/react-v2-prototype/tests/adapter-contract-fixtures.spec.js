import { expect, test } from '@playwright/test';
import {
  ADAPTER_CONTRACT_VERSION,
  ADAPTER_ERROR_POLICY,
  MISSING_FIELD_POLICY,
  READ_ONLY_SOURCE_FILES,
  RESERVED_SOURCE_FILES,
  VIEW_MODEL_SHAPES,
  validateAdapterFixture,
  validateViewModelShape
} from '../src/lib/adapterContract.js';
import {
  duplicateRouteFixture,
  missingRequiredFieldFixture,
  validAdapterFixture
} from './fixtures/adapterContractFixtures.js';

test('adapter contract defines source names without reading runtime JSON', () => {
  expect(ADAPTER_CONTRACT_VERSION).toBe('react-v2-read-only-adapter-contract-v2');
  expect(READ_ONLY_SOURCE_FILES).toEqual([
    'public/data/degrees.json',
    'public/data/level1.json',
    'public/data/level2.json',
    'public/data/level3.json',
    'public/data/library.json'
  ]);
  expect(RESERVED_SOURCE_FILES).toContain('public/data/encyclopedia.json');
  expect(RESERVED_SOURCE_FILES).toContain('public/data/homepage_projection.json');
});

test('adapter contract defines required view-model fields', () => {
  expect(VIEW_MODEL_SHAPES.degree.required).toEqual([
    'id',
    'label',
    'title',
    'summary',
    'tone',
    'categories'
  ]);
  expect(VIEW_MODEL_SHAPES.topicEntry.required).toContain('slug');
  expect(VIEW_MODEL_SHAPES.topicEntry.required).toContain('source');
  expect(VIEW_MODEL_SHAPES.librarySource.required).toContain('sourceYear');
  expect(VIEW_MODEL_SHAPES.librarySource.required).toContain('sourceKind');
  expect(VIEW_MODEL_SHAPES.librarySource.required).toContain('coverage');
  expect(VIEW_MODEL_SHAPES.routeMetadata.required).toEqual(['title', 'description', 'canonicalPath', 'ogType']);
});

test('valid synthetic adapter fixture satisfies the view-model contract', () => {
  expect(validateAdapterFixture(validAdapterFixture)).toEqual([]);
});

test('synthetic missing required fields produce explicit contract errors', () => {
  const errors = validateAdapterFixture(missingRequiredFieldFixture);

  expect(errors).toContain('degree.title is required');
  expect(errors).toContain('topicEntry.title must be a non-empty string');
});

test('synthetic duplicate routes produce explicit contract errors', () => {
  const errors = validateAdapterFixture(duplicateRouteFixture);

  expect(errors).toContain('duplicate route slug: degree/level1/synthetic-topic');
});

test('shape validator rejects array fields that are not arrays', () => {
  const errors = validateViewModelShape('topicEntry', {
    ...validAdapterFixture.entries[0],
    related: 'not an array'
  });

  expect(errors).toContain('topicEntry.related must be an array');
});

test('missing-field and error policies keep frontend behavior display-only', () => {
  expect(MISSING_FIELD_POLICY.hardFail).toEqual(['slug', 'title', 'degree', 'source']);
  expect(MISSING_FIELD_POLICY.displayFallbackOnly).toContain('summary');
  expect(MISSING_FIELD_POLICY.displayFallbackOnly).toContain('sourceKind');
  expect(ADAPTER_ERROR_POLICY.hardFail).toContain('invalid JSON shape');
  expect(ADAPTER_ERROR_POLICY.hardFail).toContain('degree/library boundary crossing');
  expect(ADAPTER_ERROR_POLICY.reportOnly).toContain('localization coverage gap');
});
