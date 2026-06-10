const fs = require('fs');
const path = require('path');

function findPlaywrightCore() {
  if (process.env.PLAYWRIGHT_CORE_PATH && fs.existsSync(process.env.PLAYWRIGHT_CORE_PATH)) {
    return process.env.PLAYWRIGHT_CORE_PATH;
  }

  const localAppData = process.env.LOCALAPPDATA;
  if (!localAppData) {
    throw new Error('LOCALAPPDATA is not set');
  }

  const npxRoot = path.join(localAppData, 'npm-cache', '_npx');
  if (!fs.existsSync(npxRoot)) {
    throw new Error(`Could not find npx cache root at ${npxRoot}`);
  }

  const candidates = fs
    .readdirSync(npxRoot)
    .map(dir => path.join(npxRoot, dir, 'node_modules', 'playwright-core'))
    .filter(candidate => fs.existsSync(candidate))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);

  if (!candidates.length) {
    throw new Error('Could not find a cached playwright-core package');
  }

  return candidates[0];
}

async function main() {
  const [, , url, outputPath, storageStateJson, captureMode] = process.argv;
  if (!url || !outputPath) {
    throw new Error('Usage: node playwright_probe.js <url> <outputPath> [storageStateJson] [captureMode]');
  }

  const playwrightCorePath = findPlaywrightCore();
  const { chromium } = require(playwrightCorePath);

  const browser = await chromium.launch({
    channel: 'chrome',
    headless: true,
  });

  try {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1100 },
      locale: 'he-IL',
    });

    if (storageStateJson) {
      const rawStorageState = storageStateJson.startsWith('@')
        ? await fs.promises.readFile(storageStateJson.slice(1), 'utf8')
        : storageStateJson;
      const storageState = JSON.parse(rawStorageState);
      await context.addInitScript((state) => {
        Object.entries(state.localStorage || {}).forEach(([key, value]) => {
          localStorage.setItem(key, value);
        });
        Object.entries(state.sessionStorage || {}).forEach(([key, value]) => {
          sessionStorage.setItem(key, value);
        });
      }, storageState);
    }

    const page = await context.newPage();
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await fs.promises.mkdir(path.dirname(outputPath), { recursive: true });
    await page.screenshot({ path: outputPath, fullPage: captureMode !== 'viewport' });

    const result = {
      url: page.url(),
      title: await page.title(),
      outputPath,
    };

    console.log(JSON.stringify(result, null, 2));
    await context.close();
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
