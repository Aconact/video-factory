// Renders a transparent text/graphics layer (window.renderFrame(t)) for a Blender shot to numbered PNG frames.
//
//   node tools/render_overlay.js --html videos/pkg-test/index.html --fonts videos/fonts --data anchors.json \
//        --out frames [--frames 150] [--fps 30] [--from 1] [--to 150] [--workers 2]
//
// The page is served at http://app.local/index.html; /anchors.json is the file given with --data (screen positions of
// points on the 3D model, exported by the Blender job with ANCHORS_OUT=...), /fonts/* comes from --fonts.
// Frame i (1-based) is drawn at t = (i - 1) / fps and saved as a_<i>.png with a transparent background.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const args = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const htmlPath = path.resolve(args.html);
const fontsDir = path.resolve(args.fonts);
const dataPath = args.data ? path.resolve(args.data) : null;
const outDir = path.resolve(args.out);
const fps = parseInt(args.fps || '30', 10);
const total = parseInt(args.frames || '150', 10);
const from = parseInt(args.from || '1', 10);
const to = Math.min(parseInt(args.to || String(total), 10), total);
const workers = parseInt(args.workers || '2', 10);
const W = 1080, H = 1920;
fs.mkdirSync(outDir, { recursive: true });

const mime = { '.ttf': 'font/ttf', '.json': 'application/json', '.html': 'text/html' };
function resolveRoute(p) {
  if (p === '/' || p === '/index.html') return htmlPath;
  if (p === '/anchors.json' && dataPath) return dataPath;
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
  await page.goto('http://app.local/index.html');
  await page.waitForFunction(() => window.sceneReady === true, null, { timeout: 60000 });
  return page;
}

(async () => {
  const browser = await chromium.launch();
  const t0 = Date.now();
  const list = [];
  if (args.only) for (const v of args.only.split(',')) list.push(parseInt(v, 10));
  else for (let i = from; i <= to; i++) list.push(i);
  const jobs = Array.from({ length: workers }, () => []);
  list.forEach((f, k) => jobs[k % workers].push(f));
  let done = 0;
  await Promise.all(jobs.map(async (mine) => {
    const page = await openPage(browser);
    for (const i of mine) {
      await page.evaluate((tt) => window.renderFrame(tt), (i - 1) / fps);
      fs.writeFileSync(path.join(outDir, `a_${String(i).padStart(5, '0')}.png`), await page.screenshot({ type: 'png', omitBackground: true }));
      done++;
      if (done % 50 === 0) console.log(`frames ${done}/${list.length} elapsed ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
  }));
  console.log(`rendered ${done} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  await browser.close();
})();
