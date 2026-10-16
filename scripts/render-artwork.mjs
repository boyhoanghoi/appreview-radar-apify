import { access, mkdir, readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

// Optional artwork helper. No browser is required by the Actor runtime.
const playwrightPath = process.env.PLAYWRIGHT_MODULE || 'C:/Users/ADMIN/.cache/codex-tools/browser-check/node_modules/playwright/index.mjs';
const executablePath = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
await access(playwrightPath);
await access(executablePath);
const { chromium } = await import(pathToFileURL(playwrightPath).href);
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const browser = await chromium.launch({ executablePath, headless: true });
try {
  const artworks = [
    ['assets/brand/icon.svg', 'assets/brand/icon-512.png', 512, 512],
    ['assets/launch/review-radar-preview.svg', 'assets/launch/review-radar-preview.png', 1600, 900],
  ];
  for (const [input, output, width, height] of artworks) {
    const svg = await readFile(resolve(root, input), 'utf8');
    await mkdir(dirname(resolve(root, output)), { recursive: true });
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    await page.setContent(`<html><head><meta charset="utf-8"><style>html,body{margin:0;width:${width}px;height:${height}px;background:transparent}svg{display:block;width:${width}px;height:${height}px}</style></head><body>${svg}</body></html>`);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: resolve(root, output), omitBackground: true });
    await page.close();
    console.log(`Rendered ${output} (${width} x ${height}).`);
  }
} finally {
  await browser.close();
}
