// Renders an HTML scene (window.renderFrame(t)) to numbered frames with Playwright.
//
//   node tools/render_html.js --html videos/x/index.html --fonts videos/fonts \
//        --timeline timeline.json --out frames [--times 1,2.5] [--workers 2] [--overlay 1]
//
// Frames inside the "alpha windows" (where the page sits on top of Blender footage) are saved as
// PNG with transparency (a_00001.png); all other frames are saved as JPEG (o_00001.jpg).
// With --times, only those moments are saved (as t_<seconds>.png, always with transparency).
// With --overlay 1 the page is opened as index.html?overlay=1 (text layer only, no background) and
// every frame is saved as a transparent PNG (a_00001.png) to be laid over separately rendered footage.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const args = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const htmlPath = path.resolve(args.html);
const fontsDir = path.resolve(args.fonts);
const timelinePath = path.resolve(args.timeline);
const outDir = path.resolve(args.out);
const fps = parseInt(args.fps || '30', 10);
const workers = parseInt(args.workers || '2', 10);
const W = 1080, H = 1920;
fs.mkdirSync(outDir, { recursive: true });

const timeline = JSON.parse(fs.readFileSync(timelinePath, 'utf8'));
const byId = Object.fromEntries(timeline.scenes.map((s) => [s.id, s]));
const alphaWindows = [
  [0, byId.hook.end + 0.45],
  [byId.cta.start - 0.2, timeline.duration + 1],
];
const overlayOnly = args.overlay === '1';
const isAlpha = (t) => overlayOnly || alphaWindows.some(([a, b]) => t >= a && t < b);

const mime = { '.ttf': 'font/ttf', '.json': 'application/json', '.html': 'text/html' };
function resolveRoute(p) {
  if (p === '/' || p === '/index.html') return htmlPath;
  if (p === '/timeline.json') return timelinePath;
  if (p.startsWith('/fonts/')) {
    const full = path.normalize(path.join(fontsDir, p.slice('/fonts/'.length)));
    return full.startsWith(fontsDir + path.sep) ? full : null;
  }
  return null;
}

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on('console', (m) => { const t = m.text(); if (!t.startsWith('Failed to load resource')) console.log('[page]', t); });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.route('http://app.local/**', async (route) => {
    const url = new URL(route.request().url());
    const file = resolveRoute(url.pathname);
    if (!file || !fs.existsSync(file)) { console.log('[404]', url.pathname); await route.fulfill({ status: 404, body: 'not found' }); return; }
    await route.fulfill({ status: 200, contentType: mime[path.extname(file)] || 'application/octet-stream', body: fs.readFileSync(file) });
  });
  await page.goto('http://app.local/index.html' + (overlayOnly ? '?overlay=1' : ''));
  await page.waitForFunction(() => window.sceneReady === true, null, { timeout: 60000 });
  return page;
}

(async () => {
  const browser = await chromium.launch();
  const t0 = Date.now();
  if (args.times) {
    const page = await openPage(browser);
    for (const tt of args.times.split(',').map(Number)) {
      await page.evaluate((t) => window.renderFrame(t), tt);
      const buf = await page.screenshot({ type: 'png', omitBackground: true });
      fs.writeFileSync(path.join(outDir, `t_${tt.toFixed(2)}.png`), buf);
      console.log('saved t', tt);
    }
    await browser.close();
    return;
  }

  const total = Math.ceil(timeline.duration * fps);
  const from = parseInt(args.from || '0', 10);
  const to = Math.min(parseInt(args.to || String(total - 1), 10), total - 1);
  const jobs = Array.from({ length: workers }, () => []);
  for (let i = from; i <= to; i++) jobs[i % workers].push(i);
  let done = 0;
  await Promise.all(jobs.map(async (list) => {
    const page = await openPage(browser);
    for (const i of list) {
      const t = i / fps;
      await page.evaluate((tt) => window.renderFrame(tt), t);
      const name = String(i + 1).padStart(5, '0');
      if (isAlpha(t)) {
        fs.writeFileSync(path.join(outDir, `a_${name}.png`), await page.screenshot({ type: 'png', omitBackground: true }));
      } else {
        fs.writeFileSync(path.join(outDir, `o_${name}.jpg`), await page.screenshot({ type: 'jpeg', quality: 95 }));
      }
      done++;
      if (done % 60 === 0) console.log(`frames ${done}/${to - from + 1} elapsed ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
  }));
  console.log(`rendered ${done} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s; alpha windows`, JSON.stringify(alphaWindows));
  await browser.close();
})();
