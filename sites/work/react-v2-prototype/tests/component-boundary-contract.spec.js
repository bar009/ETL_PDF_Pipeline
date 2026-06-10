import { access, readFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { expect, test } from '@playwright/test';

const requiredComponentFiles = [
  '../src/components/ShellHeader.jsx',
  '../src/components/HomeSurface.jsx',
  '../src/components/DegreeRail.jsx',
  '../src/components/TopicCard.jsx',
  '../src/components/LibrarySurface.jsx',
  '../src/components/ArticlePage.jsx',
  '../src/components/SourceDetailPage.jsx'
];

async function fileExists(relativePath) {
  await access(new URL(relativePath, import.meta.url), constants.F_OK);
}

async function readSource(relativePath) {
  return readFile(new URL(relativePath, import.meta.url), 'utf8');
}

test('portable page-level components exist', async () => {
  for (const componentPath of requiredComponentFiles) {
    await expect(fileExists(componentPath), `${componentPath} should exist for the migration boundary`).resolves.toBeUndefined();
  }
});

test('prototype router maps page routes to distinct page components', async () => {
  const appSource = await readSource('../src/App.jsx');

  expect(appSource).toContain("import HomeSurface from './components/HomeSurface.jsx'");
  expect(appSource).toContain("import LibrarySurface from './components/LibrarySurface.jsx'");
  expect(appSource).toContain("import ArticlePage from './components/ArticlePage.jsx'");
  expect(appSource).toContain("import SourceDetailPage from './components/SourceDetailPage.jsx'");
  expect(appSource).toContain('isSourceRoute ?');
  expect(appSource).toContain('<SourceDetailPage');
  expect(appSource).toContain(': isArticleRoute ?');
  expect(appSource).toContain('<ArticlePage');
});

test('library and article surfaces stay separated', async () => {
  const librarySource = await readSource('../src/components/LibrarySurface.jsx');
  const articleSource = await readSource('../src/components/ArticlePage.jsx');
  const sourceDetailSource = await readSource('../src/components/SourceDetailPage.jsx');

  expect(librarySource).toContain('useVirtualizer');
  expect(librarySource).not.toContain('ArticlePage');
  expect(articleSource).not.toContain('source-detail-page');
  expect(sourceDetailSource).not.toContain('article-page');
});

test('prototype route helpers preserve clean URL mapping', async () => {
  const routeSource = await readSource('../src/lib/routes.js');

  expect(routeSource).toContain("return degreeId === LIBRARY_ID ? '/library' : `/degree/${degreeId}`");
  expect(routeSource).toContain('`/library/${encodeURIComponent(entry.slug)}`');
  expect(routeSource).toContain('`/degree/${entry.degree}/${encodeURIComponent(entry.slug)}`');
});
