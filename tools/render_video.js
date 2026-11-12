// Renders a 16:9 HTML video page (window.renderFrame(t)) with Playwright.
//
//   Check shots:   node tools/render_video.js --dir videos/phones --fonts videos/fonts --times 5,12.5 --out shots [--dsf 1] [--media videos/phones/pack]
//   One chunk:     node tools/render_video.js --dir videos/phones --fonts videos/fonts --from 0 --to 899 --out chunk_000.mp4
//
// The page is laid out at 1920x1080 CSS pixels. With --dsf 2 every screenshot is a true 3840x2160 picture
// (vector text and shapes are drawn at 4K, not enlarged). In chunk mode the frames are piped straight into ffmpeg
// and one H.264 file is written for the frame range, so chunks of one video can be joined with `-c copy`.
// Every chunk uses the same size, frame rate and encoder settings.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const args = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const dir = path.resolve(args.dir);
const fontsDir = path.resolve(args.fonts);
const mediaDir = path.resolve(args.media || path.join(dir, 'pack'));   // press photos and clip frames (kept out of the repository)
const timelinePath = path.resolve(args.timeline || path.join(dir, 'timeline.json'));
const fps = parseInt(args.fps || '30', 10);
const dsf = parseFloat(args.dsf || '2');
const workers = parseInt(args.workers || '2', 10);
const quality = parseInt(args.quality || '95', 10);
const W = 1920, H = 1080;

const mime = { '.ttf': 'font/ttf', '.json': 'application/json', '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp' };
let notFound = 0;   // any file the page asked for and could not get makes the run fail
function resolveRoute(p) {
  if (p === '/') p = '/index.html';
  if (p === '/timeline.json') return timelinePath;
  if (p.startsWith('/fonts/')) {
    const full = path.normalize(path.join(fontsDir, p.slice('/fonts/'.length)));
    return full.startsWith(fontsDir + path.sep) ? full : null;
  }
  if (p.startsWith('/media/')) {
    const full = path.normalize(path.join(mediaDir, p.slice('/media/'.length)));
    return full.startsWith(mediaDir + path.sep) ? full : null;
  }
  const full = path.normalize(path.join(dir, p));
  return full.startsWith(dir + path.sep) ? full : null;
}

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: dsf });
  page.on('console', (m) => { const t = m.text(); if (!t.startsWith('Failed to load resource')) console.log('[page]', t); });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.route('http://app.local/**', async (route) => {
    const url = new URL(route.request().url());
    const file = resolveRoute(url.pathname);
    if (!file || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { console.log('[404]', url.pathname); notFound++; await route.fulfill({ status: 404, body: 'not found' }); return; }
    await route.fulfill({ status: 200, contentType: mime[path.extname(file)] || 'application/octet-stream', body: fs.readFileSync(file) });
  });
  await page.goto('http://app.local/index.html');
  await page.waitForFunction(() => window.sceneReady === true, null, { timeout: 120000 });
  const missing = await page.evaluate(() => (window.V && window.V.missing) || []);
  if (missing.length) console.log('[anchors missing]', JSON.stringify(missing));
  return page;
}

const timeline = JSON.parse(fs.readFileSync(timelinePath, 'utf8'));
const total = Math.ceil(timeline.duration * fps);

(async () => {
  const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--disable-lcd-text', '--font-render-hinting=none'] });
  const t0 = Date.now();

  if (args.cues) {                       // sound cues of the page (window.CUES) as JSON, for the audio mix
    const page = await openPage(browser);
    const cues = await page.evaluate(() => window.CUES);
    fs.writeFileSync(path.resolve(args.cues), JSON.stringify(cues, null, 1));
    console.log('cues', cues.length);
    await browser.close();
    return;
  }

  if (args.times) {
    const out = path.resolve(args.out);
    fs.mkdirSync(out, { recursive: true });
    const page = await openPage(browser);
    for (const tt of args.times.split(',').map(Number)) {
      await page.evaluate((t) => window.renderFrame(t), tt);
      const buf = await page.screenshot({ type: 'png' });
      fs.writeFileSync(path.join(out, `t_${tt.toFixed(2).padStart(7, '0')}.png`), buf);
      console.log('saved t', tt);
    }
    await browser.close();
    if (notFound) { console.error(`${notFound} file(s) were not found`); process.exit(1); }
    return;
  }

  const from = parseInt(args.from || '0', 10);
  const to = Math.min(parseInt(args.to || String(total - 1), 10), total - 1);
  const out = path.resolve(args.out);
  const tmp = out.replace(/\.mp4$/, '') + '.part.mp4';
  const vf = 'format=rgb24,scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,format=yuv420p';
  const maxrate = args.maxrate || '20M';
  const bufsize = String(parseInt(maxrate, 10) * 2) + 'M';
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-vf', vf, '-c:v', 'libx264', '-preset', args.preset || 'medium', '-crf', args.crf || '17', '-maxrate', maxrate, '-bufsize', bufsize,
    '-profile:v', 'high', '-aq-mode', '3', '-pix_fmt', 'yuv420p', '-g', '60', '-r', String(fps),
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
    '-an', '-movflags', '+faststart', tmp], { stdio: ['pipe', 'inherit', 'inherit'] });
  const ffDone = new Promise((resolve) => ff.on('close', resolve));
  ff.stdin.on('error', () => {});

  const pages = [];
  for (let k = 0; k < workers; k++) pages.push(await openPage(browser));
  let done = 0;
  for (let i = from; i <= to; i += workers) {
    const batch = [];
    for (let k = 0; k < workers && i + k <= to; k++) {
      const idx = i + k;
      batch.push((async () => {
        await pages[k].evaluate((tt) => window.renderFrame(tt), idx / fps);
        return pages[k].screenshot({ type: 'jpeg', quality });
      })());
    }
    const bufs = await Promise.all(batch);
    for (const b of bufs) {
      if (!ff.stdin.write(b)) await new Promise((r) => ff.stdin.once('drain', r));
      done++;
    }
    if (done % 60 < workers) console.log(`frames ${done}/${to - from + 1} elapsed ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  const code = await ffDone;
  await browser.close();
  if (code !== 0) { console.error('ffmpeg failed', code); process.exit(1); }
  if (notFound) { console.error(`${notFound} file(s) were not found; chunk not kept`); process.exit(1); }
  fs.renameSync(tmp, out);
  console.log(`chunk ${from}-${to}: ${done} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s -> ${out} (${(fs.statSync(out).size / 1e6).toFixed(1)} MB)`);
})();
