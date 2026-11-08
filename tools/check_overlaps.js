// Looks for text that lands on top of other text (or on a canvas) while a page is playing.
//
//   node tools/check_overlaps.js --html videos/x/index.html --fonts videos/fonts --timeline timeline.json [--data data.json]
//        [--from 0] [--to 47] [--min 0.2]
//
// For every frame it asks the page (window.renderFrame(t)) which pieces of text are visible, takes their real
// on-screen boxes, and reports every pair that overlaps by more than --min of the smaller box. Consecutive frames
// with the same pair are printed as one line: "12.40-12.53  'blue' x 'color'  (38%)".
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const args = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const htmlPath = path.resolve(args.html), fontsDir = path.resolve(args.fonts), timelinePath = path.resolve(args.timeline);
const dataPath = args.data ? path.resolve(args.data) : null;
const fps = 30, from = parseFloat(args.from || '0'), to = parseFloat(args.to || '1e9'), minFrac = parseFloat(args.min || '0.2');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', (e) => console.error('[pageerror]', e.message));
  await page.route('http://app.local/**', async (route) => {
    const p = new URL(route.request().url()).pathname;
    let file = null;
    if (p === '/' || p === '/index.html') file = htmlPath;
    else if (p === '/timeline.json') file = timelinePath;
    else if (p === '/data.json' && dataPath) file = dataPath;
    else if (p.startsWith('/fonts/')) file = path.join(fontsDir, p.slice(7));
    if (!file || !fs.existsSync(file)) { await route.fulfill({ status: 404, body: '' }); return; }
    const type = file.endsWith('.ttf') ? 'font/ttf' : file.endsWith('.json') ? 'application/json' : 'text/html';
    await route.fulfill({ status: 200, contentType: type, body: fs.readFileSync(file) });
  });
  await page.goto('http://app.local/index.html');
  await page.waitForFunction(() => window.sceneReady === true, null, { timeout: 60000 });
  const duration = await page.evaluate(() => window.TL.duration);
  const last = Math.min(to, duration);
  const open = new Map();   // pair key -> {start, end, frac, a, b}
  const done = [];
  const frames = Math.floor((last - from) * fps);
  for (let k = 0; k <= frames; k++) {
    const t = from + k / fps;
    const items = await page.evaluate((tt) => {
      window.renderFrame(tt);
      const out = [];
      const vis = (el) => {
        let op = 1;
        for (let e = el; e && e !== document.documentElement; e = e.parentElement) {
          const cs = getComputedStyle(e);
          if (cs.display === 'none' || cs.visibility === 'hidden') return 0;
          op *= parseFloat(cs.opacity);
        }
        return op;
      };
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = walker.nextNode())) {
        const txt = n.nodeValue.trim();
        if (!txt) continue;
        const el = n.parentElement;
        if (el.closest('script,style')) continue;
        const op = vis(el);
        if (op < 0.3) continue;
        const range = document.createRange(); range.selectNodeContents(n);
        const r = range.getBoundingClientRect();
        if (r.width < 3 || r.height < 3 || r.right < 0 || r.left > 1080 || r.bottom < 0 || r.top > 1920) continue;
        out.push({ k: 'text', txt, x: r.left, y: r.top, w: r.width, h: r.height, el: el.id || el.className || el.tagName });
      }
      for (const c of document.querySelectorAll('canvas')) {
        const op = vis(c);
        if (op < 0.3 || c.id === 'bokeh') continue;
        const r = c.getBoundingClientRect();
        if (r.width < 10) continue;
        out.push({ k: 'canvas', txt: '[' + (c.id || c.className || 'canvas') + ']', x: r.left, y: r.top, w: r.width, h: r.height, el: c.id });
      }
      return out;
    }, t);
    const seen = new Set();
    for (let i = 0; i < items.length; i++) for (let j = i + 1; j < items.length; j++) {
      const a = items[i], b = items[j];
      if (a.k === 'canvas' && b.k === 'canvas') continue;
      const ix = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x), iy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
      if (ix <= 2 || iy <= 2) continue;
      const frac = ix * iy / Math.min(a.w * a.h, b.w * b.h);
      if (frac < minFrac) continue;
      const key = a.txt + ' x ' + b.txt;
      seen.add(key);
      const o = open.get(key);
      if (o) { o.end = t; o.frac = Math.max(o.frac, frac); o.n++; }
      else open.set(key, { start: t, end: t, frac, n: 1, key });
    }
    for (const [key, o] of open) if (!seen.has(key)) { done.push(o); open.delete(key); }
  }
  for (const o of open.values()) done.push(o);
  done.sort((a, b) => a.start - b.start);
  for (const o of done) console.log(`${o.start.toFixed(2)}-${o.end.toFixed(2)}  ${o.n}f  ${o.key}  (${Math.round(o.frac * 100)}%)`);
  console.log('checked', frames + 1, 'frames;', done.length, 'overlaps');
  await browser.close();
})();
