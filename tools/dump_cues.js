// Prints the sound cues (window.CUES) of a scene as JSON:  node tools/dump_cues.js --html x/index.html --fonts fonts --timeline timeline.json
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const args = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const htmlPath = path.resolve(args.html), fontsDir = path.resolve(args.fonts), timelinePath = path.resolve(args.timeline);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', (e) => console.error('[pageerror]', e.message));
  await page.route('http://app.local/**', async (route) => {
    const p = new URL(route.request().url()).pathname;
    let file = null;
    if (p === '/' || p === '/index.html') file = htmlPath;
    else if (p === '/timeline.json') file = timelinePath;
    else if (p.startsWith('/fonts/')) file = path.join(fontsDir, p.slice(7));
    if (!file || !fs.existsSync(file)) { await route.fulfill({ status: 404, body: '' }); return; }
    const type = file.endsWith('.ttf') ? 'font/ttf' : file.endsWith('.json') ? 'application/json' : 'text/html';
    await route.fulfill({ status: 200, contentType: type, body: fs.readFileSync(file) });
  });
  await page.goto('http://app.local/index.html');
  await page.waitForFunction(() => window.sceneReady === true, null, { timeout: 60000 });
  const cues = await page.evaluate(() => window.CUES);
  fs.writeFileSync(path.resolve(args.out), JSON.stringify(cues, null, 1));
  console.log('cues', cues.length);
  await browser.close();
})();
