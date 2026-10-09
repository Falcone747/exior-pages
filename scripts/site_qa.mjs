// Mandatory site QA gate (runs in CI on every PR and before every deploy). Ratchet: known failures in
// scripts/qa_baseline.json may not get worse; any NEW failure blocks the merge/deploy.
import { chromium } from 'playwright';
import fs from 'node:fs';
const base = process.argv[2] || 'http://127.0.0.1:8000/';
const pages = ['/', ...fs.readdirSync('_site', { withFileTypes: true }).filter(d => d.isDirectory() && fs.existsSync(`_site/${d.name}/index.html`)).map(d => `/${d.name}/`)];
const baseline = JSON.parse(fs.readFileSync('scripts/qa_baseline.json', 'utf8'));
const browser = await chromium.launch();
const fails = [], report = [];
for (const path of pages) {
  for (const [vp, w] of [['desktop', 1440], ['mobile', 390]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
    const p = await ctx.newPage();
    const r = await p.goto(new URL(path, base).href, { waitUntil: 'load', timeout: 30000 }).catch(() => null);
    const status = r ? r.status() : 0;
    const overflow = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth).catch(() => -1);
    const key = `${path} [${vp}]`;
    report.push({ key, status, overflow });
    if (status !== 200) fails.push(`${key} HTTP ${status}`);
    const allowed = baseline.overflow_px?.[key] ?? 2;
    if (overflow > allowed) fails.push(`${key} horizontal overflow ${overflow}px (allowed ${allowed})`);
    await ctx.close();
  }
}
await browser.close();
console.log(JSON.stringify({ checked: report.length, report }, null, 1));
if (fails.length) { console.error('SITE QA FAILED:\n' + fails.join('\n')); process.exit(1); }
console.log('SITE QA PASSED');
