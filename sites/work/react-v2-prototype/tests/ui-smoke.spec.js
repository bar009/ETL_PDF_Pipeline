import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

async function expectNoSeriousAccessibilityViolations(page) {
  const results = await new AxeBuilder({ page })
    .disableRules(['color-contrast'])
    .analyze();

  const seriousViolations = results.violations.filter(violation =>
    ['critical', 'serious'].includes(violation.impact)
  );

  expect(seriousViolations).toEqual([]);
}

test('topic route has no serious accessibility violations', async ({ page }) => {
  await page.goto('/degree/level1/the-lambskin-apron');
  await expectNoSeriousAccessibilityViolations(page);
});

test('home route has no serious accessibility violations', async ({ page }) => {
  await page.goto('/');
  await expectNoSeriousAccessibilityViolations(page);
});

test('home route renders as an entry surface', async ({ page }) => {
  await page.goto('/');

  await expect(page.locator('.home-surface')).toBeVisible();
  await expect(page.locator('.content-pane')).toHaveCount(0);
  await expect(page.locator('.primary-action')).toBeVisible();
});

test('degree route remains the topic map', async ({ page }) => {
  await page.goto('/degree/level1');

  await expect(page.locator('.home-surface')).toHaveCount(0);
  await expect(page.locator('.content-pane')).toBeVisible();
  await expect(page.locator('.topic-row')).toHaveCount(3);
});

test('library route has no serious accessibility violations', async ({ page }) => {
  await page.goto('/library');
  await expectNoSeriousAccessibilityViolations(page);
});

test('library source route has no serious accessibility violations', async ({ page }) => {
  await page.goto('/library/duncans-ritual-monitor-1866-book');
  await expectNoSeriousAccessibilityViolations(page);
});

test('topic route renders as a full article page', async ({ page }) => {
  await page.goto('/degree/level1/the-lambskin-apron');

  await expect(page.locator('.article-page')).toBeVisible();
  await expect(page.locator('.article-context')).toBeVisible();
  await expect(page.locator('.detail-panel')).toHaveCount(0);
  await expect(page.locator('#articleTitle')).toHaveText('The Lambskin Apron');
});

test('article route has one h1 and real outline targets', async ({ page }) => {
  await page.goto('/degree/level1/the-lambskin-apron');

  await expect(page.locator('h1')).toHaveCount(1);
  const outlineTargetsExist = await page.evaluate(() =>
    [...document.querySelectorAll('.article-outline a')].every(link => {
      const id = link.getAttribute('href')?.replace('#', '');
      return id ? Boolean(document.getElementById(id)) : false;
    })
  );

  expect(outlineTargetsExist).toBe(true);
});

test('library source route renders as a source detail page', async ({ page }) => {
  await page.goto('/library/duncans-ritual-monitor-1866-book');

  await expect(page.locator('.source-detail-page')).toBeVisible();
  await expect(page.locator('.source-detail-context')).toBeVisible();
  await expect(page.locator('.article-page')).toHaveCount(0);
  await expect(page.locator('.detail-panel')).toHaveCount(0);
  await expect(page.locator('#sourceTitle')).toHaveText(/Duncan.s Masonic Ritual and Monitor of Freemasonry/);
});

test('library source route has one h1 and real outline targets', async ({ page }) => {
  await page.goto('/library/duncans-ritual-monitor-1866-book');

  await expect(page.locator('h1')).toHaveCount(1);
  const outlineTargetsExist = await page.evaluate(() =>
    [...document.querySelectorAll('.source-outline a')].every(link => {
      const id = link.getAttribute('href')?.replace('#', '');
      return id ? Boolean(document.getElementById(id)) : false;
    })
  );

  expect(outlineTargetsExist).toBe(true);
});

test('keyboard focus reaches core shell controls', async ({ page }) => {
  await page.goto('/degree/level1/the-lambskin-apron');
  await page.keyboard.press('Tab');

  await expect(page.locator('.skip-link')).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.locator('.brand')).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.locator('.global-search input')).toBeFocused();
});

test('language switch updates document direction', async ({ page }) => {
  await page.goto('/degree/level1/the-lambskin-apron');

  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await page.getByRole('button', { name: 'English', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
});

test('language switch preserves search interaction on degree map', async ({ page }) => {
  await page.goto('/degree/level1');

  await page.getByRole('button', { name: 'English', exact: true }).click();
  await page.locator('.global-search input').fill('working');

  await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
  await expect(page.locator('.topic-row')).toHaveCount(2);
  await expect(page.getByText('The Working Tools of an Entered Apprentice')).toBeVisible();
  await expect(page.getByText('The Furniture of a Lodge')).toHaveCount(0);
});

test('article route updates page metadata', async ({ page }) => {
  await page.goto('/degree/level1/the-lambskin-apron');

  await expect(page).toHaveTitle(/The Lambskin Apron/);
  const description = page.locator('meta[name="description"]');
  await expect(description).toHaveAttribute('content', /The Lambskin Apron/);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    'href',
    'http://127.0.0.1:4174/degree/level1/the-lambskin-apron'
  );
  await expect(page.locator('meta[property="og:type"]')).toHaveAttribute('content', 'article');
  await expect(page.locator('meta[property="og:url"]')).toHaveAttribute(
    'content',
    'http://127.0.0.1:4174/degree/level1/the-lambskin-apron'
  );
});

test('library source route uses source-first metadata', async ({ page }) => {
  await page.goto('/library/duncans-ritual-monitor-1866-book');

  await expect(page).toHaveTitle(/Duncan.s Masonic Ritual and Monitor of Freemasonry/);
  await expect(page.locator('meta[name="description"]')).toHaveAttribute('content', /Book/);
  await expect(page.locator('meta[name="description"]')).toHaveAttribute('content', /1866/);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    'href',
    'http://127.0.0.1:4174/library/duncans-ritual-monitor-1866-book'
  );
  await expect(page.locator('meta[property="og:type"]')).toHaveAttribute('content', 'article');
  await expect(page.locator('meta[property="og:url"]')).toHaveAttribute(
    'content',
    'http://127.0.0.1:4174/library/duncans-ritual-monitor-1866-book'
  );
});

test('library route keeps the explicit server-side auth boundary', async ({ page }) => {
  await page.goto('/library/duncans-ritual-monitor-1866-book');

  await expect(page.locator('.access-button')).toHaveAttribute(
    'aria-label',
    'Access control requires server-side enforcement'
  );
  await expect(page.getByRole('button', { name: 'מחקר' })).toHaveAttribute('aria-pressed', 'true');
});

test('mobile layout avoids horizontal overflow', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'mobile-only layout check');

  await page.goto('/library');

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(overflow).toBe(false);
  await expect(page.locator('.source-row').first()).toBeVisible();
});

test('mobile LTR layout avoids horizontal overflow after language switch', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'mobile-only layout check');

  await page.goto('/library');
  await page.getByRole('button', { name: 'English', exact: true }).click();

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(overflow).toBe(false);
  await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
});

test('mobile article reaches the title without horizontal overflow', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'mobile-only layout check');

  await page.goto('/degree/level1/the-lambskin-apron');

  const layout = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    titleTop: document.querySelector('#articleTitle')?.getBoundingClientRect().top ?? Number.POSITIVE_INFINITY
  }));

  expect(layout.overflow).toBe(false);
  expect(layout.titleTop).toBeLessThan(320);
});

test('mobile source detail reaches the title without horizontal overflow', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'mobile-only layout check');

  await page.goto('/library/duncans-ritual-monitor-1866-book');

  const layout = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    titleTop: document.querySelector('#sourceTitle')?.getBoundingClientRect().top ?? Number.POSITIVE_INFINITY
  }));

  expect(layout.overflow).toBe(false);
  expect(layout.titleTop).toBeLessThan(320);
});

test('narrow home layout avoids horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 330, height: 720 });
  await page.goto('/');

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(overflow).toBe(false);
  await expect(page.locator('.home-surface')).toBeVisible();
});

test('invalid route falls back without a blank page', async ({ page }) => {
  await page.goto('/degree/nope');

  await expect(page).toHaveURL('/');
  await expect(page.locator('.home-surface')).toBeVisible();
});

test('locale switch updates Open Graph locale metadata', async ({ page }) => {
  await page.goto('/');

  await expect(page.locator('meta[property="og:locale"]')).toHaveAttribute('content', 'he');
  await page.getByRole('button', { name: 'English', exact: true }).click();
  await expect(page.locator('meta[property="og:locale"]')).toHaveAttribute('content', 'en');
});
