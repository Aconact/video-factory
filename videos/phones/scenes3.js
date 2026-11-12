/* Scenes 9-14: software, price, iphone_bad, galaxy_bad, score, verdict */
(() => {
const { W, WE, pop, prog, easeOut, easeIn, clamp, count, mk, css, cue, phaseOpacity } = V;
const head = (k, h) => `<div class="kick">${k}</div><div class="h1">${h}</div>`;
const mkPhase = (root, html) => { const el = document.createElement('div'); el.className = 'abs ph'; el.innerHTML = html; root.appendChild(el); return el; };
const setPhase = (el, op) => { el.style.opacity = op.toFixed(3); el.style.display = op > .002 ? 'block' : 'none'; };
const $$ = (root, s) => [...root.querySelectorAll(s)];

css(`
.bad { color:var(--bad); } .warn { color:var(--warn); }
.sw-c { position:absolute; top:272px; width:840px; height:520px; border-radius:30px; border:2px solid; box-sizing:border-box; padding:34px 44px; background:linear-gradient(160deg, rgba(255,255,255,.07), rgba(255,255,255,.02)); }
.sw-t { font:700 23px JBM, monospace; letter-spacing:.2em; }
.sw-big { font-weight:800; font-size:92px; letter-spacing:-.03em; line-height:1.02; margin-top:16px; white-space:nowrap; }
.sw-sub { font:700 27px JBM, monospace; letter-spacing:.1em; margin-top:14px; color:var(--mut); }
.sw-q { position:absolute; left:44px; right:44px; bottom:34px; padding:20px 26px; border-radius:18px; border:2px solid rgba(255,181,71,.5); background:rgba(255,181,71,.07); font-weight:600; font-size:31px; line-height:1.25; }
.sw-q b { display:block; margin-bottom:8px; color:var(--warn); font:700 21px JBM, monospace; letter-spacing:.14em; }
.sw-f { position:absolute; left:44px; right:44px; bottom:34px; display:flex; flex-direction:column; gap:16px; }
.sw-fi { display:flex; align-items:baseline; gap:20px; padding:18px 26px; border-radius:18px; border:2px solid rgba(0,255,135,.45); background:rgba(0,255,135,.06); font-weight:800; font-size:38px; }
.sw-fi small { font:600 23px JBM, monospace; letter-spacing:.1em; color:var(--mut); }
.yr { position:absolute; width:136px; height:86px; border-radius:16px; box-sizing:border-box; display:flex; align-items:center; justify-content:center; font:700 22px JBM, monospace; letter-spacing:.1em; }
.yr.g { background:linear-gradient(160deg, rgba(0,255,135,.9), rgba(0,255,135,.55)); color:#04090B; }
.yr.e { background:rgba(0,245,255,.1); border:2px dashed rgba(0,245,255,.6); color:var(--c1); }
.yr.d { border:2px dashed rgba(0,245,255,.3); color:rgba(0,245,255,.7); }
.yr.n { border:2px dotted rgba(255,255,255,.2); color:var(--dim); }
.ylab { position:absolute; font:700 26px JBM, monospace; letter-spacing:.14em; }
.ybig { position:absolute; font-weight:800; font-size:36px; line-height:1.25; }
`);

/* ===================================================== software */
V.add('software', {
  build(root) {
    const T = {}; this.T = T; const w = (p, n) => W('software', p, n || 0);
    this.A = mkPhase(root, head('SOFTWARE & AI', 'Software and AI: <span class="mut">assistants and extras</span>') +
      `<div class="sw-c" style="left:80px;border-color:rgba(0,245,255,.7)"><div class="sw-t c1">iPHONE 18 PRO MAX</div><div class="sw-big c1">iOS 27</div><div class="sw-sub" id="swSiri">NEW SIRI AI · BETA</div>
        <div class="sw-q" id="swQ"><b>TOM'S GUIDE</b>Found it less capable than Google's Gemini or ChatGPT's voice mode.</div></div>
       <div class="sw-c" style="left:1000px;border-color:rgba(0,255,135,.7)"><div class="sw-t c2">GALAXY S26 ULTRA</div><div class="sw-big c2" style="font-size:78px">One UI + Gemini</div><div class="sw-sub">GEMINI BUILT IN</div>
        <div class="sw-f"><div class="sw-fi" id="swDex"><span class="c2">DeX</span><small>DESKTOP MODE</small></div><div class="sw-fi" id="swGl"><span class="c2">Good Lock</span><small>CUSTOMIZATION</small></div></div></div>
       <div class="src">SOURCES: APPLE · SAMSUNG · TOM'S GUIDE</div>`);
    this.sc = $$(this.A, '.sw-c'); this.siri = this.A.querySelector('#swSiri'); this.q = this.A.querySelector('#swQ'); this.dex = this.A.querySelector('#swDex'); this.gl = this.A.querySelector('#swGl');
    T.a = { ios: w('iOS 27') - .3, siri: w('Siri AI'), tg: w("Tom's Guide found") - .1, gal: w('The Galaxy runs') - .3, dex: w('DeX') - .1, gl: w('Good Lock') - .1 };
    // updates
    let yb = '';
    for (let i = 0; i < 7; i++) yb += `<div class="yr g" style="left:${80 + i * 150}px;top:376px;opacity:0">YEAR ${i + 1}</div>`;
    for (let i = 0; i < 7; i++) yb += `<div class="yr ${i < 5 ? 'e' : i === 5 ? 'd' : 'n'}" style="left:${80 + i * 150}px;top:626px;opacity:0">${i < 5 ? 'YEAR ' + (i + 1) : '?'}</div>`;
    this.B = mkPhase(root, head('SOFTWARE & AI', 'Updates: <span class="c2">Samsung promises the longest support</span>') +
      `<div class="ylab c2" style="left:80px;top:322px">GALAXY S26 ULTRA</div><div class="ylab c1" style="left:80px;top:572px">IPHONE 18 PRO MAX</div>` + yb +
      `<div class="ybig c2" id="yG" style="left:1180px;top:366px;width:660px">7 major Android upgrades<br>7 years of security patches</div>
       <div class="ybig c1" id="yI" style="left:1180px;top:612px;width:660px">Not published by Apple<div class="ylab warn" style="position:static;font-size:23px;margin-top:10px">BGR ESTIMATE: ABOUT 5–6 YEARS</div></div>
       <div class="src">SOURCES: SAMSUNG · APPLE · BGR (ESTIMATE) · TOM'S GUIDE</div>`);
    this.yg = $$(this.B, '.yr.g'); this.ye = $$(this.B, '.yr:not(.g)'); this.yG = this.B.querySelector('#yG'); this.yI = this.B.querySelector('#yI'); this.yl = $$(this.B, '.ylab').slice(0, 2);
    this.rd = V.round('galaxy', "TOM'S GUIDE · SOFTWARE ROUND"); this.B.append(this.rd);
    T.b = { in: w('For updates') - .3, s1: w('seven major'), s2: w('seven years'), apple: w('Apple has not'), bgr: w('BGR') - .3, round: w("Tom's Guide gave") };
    this.kh = [this.A, this.B].map(p => [p.querySelector('.kick'), p.querySelector('.h1')]);
    [T.a.ios, T.a.siri, T.a.tg, T.a.gal, T.a.dex, T.a.gl, T.b.s1, T.b.s2, T.b.apple].forEach((x, i) => cue(x, i < 6 ? 'pop' : 'tick', 'sw' + i));
    cue(T.b.round, 'stamp', 'round');
  },
  update(t) {
    const T = this.T, s = this.ts, b = T.b.in + .3;
    setPhase(this.A, phaseOpacity(t, s.start, b)); setPhase(this.B, phaseOpacity(t, b - .3));
    const starts = [s.start, b - .3];
    this.kh.forEach((k, i) => { pop(k[0], t, starts[i] + .25, {}); pop(k[1], t, starts[i] + .4, {}); });
    pop(this.sc[0], t, T.a.ios, { dx: -50, dy: 0, d: .7 }); pop(this.siri, t, T.a.siri, { dy: 10, d: .45 }); pop(this.q, t, T.a.tg, { dy: 20, d: .55 });
    pop(this.sc[1], t, T.a.gal, { dx: 50, dy: 0, d: .7 }); pop(this.dex, t, T.a.dex, { dy: 18, d: .5 }); pop(this.gl, t, T.a.gl, { dy: 18, d: .5 });
    // updates: seven blocks for the Galaxy, five estimated for the iPhone
    this.yl.forEach((e, i) => pop(e, t, i ? T.b.apple - .3 : T.b.s1 - .4, { dy: 8, d: .4 }));
    this.yg.forEach((e, i) => pop(e, t, T.b.s1 - .1 + i * .13, { dy: 12, s: .85, d: .4 }));
    pop(this.yG, t, T.b.s1, { dy: 12, d: .5 });
    this.ye.forEach((e, i) => pop(e, t, T.b.bgr + i * .1, { dy: 12, s: .9, d: .4 }));
    pop(this.yI, t, T.b.apple, { dy: 12, d: .5 });
    pop(this.rd, t, T.b.round, { dy: 12, s: .9, back: true, d: .5 });
  },
});

/* ===================================================== price */
css(`
.pr-h { position:absolute; top:266px; font:700 24px JBM, monospace; letter-spacing:.16em; }
.pr-row { position:absolute; left:80px; width:1760px; height:112px; border-radius:22px; border:2px solid rgba(255,255,255,.12); background:rgba(255,255,255,.04); box-sizing:border-box; }
.pr-s { position:absolute; left:36px; top:0; height:108px; display:flex; align-items:center; font:800 46px InterV, sans-serif; }
.pr-s small { font:600 22px JBM, monospace; letter-spacing:.14em; color:var(--mut); margin-left:14px; }
.pr-v { position:absolute; top:0; height:108px; display:flex; align-items:center; font:800 68px InterV, sans-serif; letter-spacing:-.03em; font-variant-numeric:tabular-nums; }
.pr-no { position:absolute; top:0; height:108px; display:flex; align-items:center; font:700 34px JBM, monospace; letter-spacing:.1em; color:var(--dim); }
.pr-d { position:absolute; right:26px; top:24px; padding:10px 20px; border-radius:30px; border:2px solid; font:800 27px InterV, sans-serif; background:rgba(4,9,11,.85); }
`);
V.add('price', {
  build(root) {
    const T = {}; this.T = T; const w = (p, n) => W('price', p, n || 0);
    const rows = [['256 GB', 1299, 1299.99], ['512 GB', 1499, 1499.99], ['1 TB', 1899, 1799.99], ['2 TB', 2499, null]];
    this.rows = rows;
    root.innerHTML = head('PRICE', 'Price: <span class="mut">the same start, a different top</span>') +
      `<div class="pr-h c1" style="left:520px">iPHONE 18 PRO MAX</div><div class="pr-h c2" style="left:1040px">GALAXY S26 ULTRA</div>` +
      rows.map((r, i) => `<div class="pr-row" style="top:${308 + i * 128}px"><div class="pr-s">${r[0]}</div><div class="pr-v c1" style="left:440px">$0</div>` +
        (r[2] === null ? `<div class="pr-no" style="left:960px">NOT OFFERED</div>` : `<div class="pr-v c2" style="left:960px">$0</div>`) + `</div>`).join('') +
      `<div class="pr-d" id="pd1" style="top:330px;right:106px;color:#F2FBFF;border-color:rgba(255,255,255,.45)">iPhone: +$100 vs last year</div>
       <div class="pr-d" id="pd3" style="top:586px;right:106px;color:var(--c2);border-color:var(--c2)">Galaxy: $100 cheaper</div>
       <div class="pr-d" id="pd4" style="top:714px;right:106px;color:var(--c1);border-color:var(--c1)">Only Apple sells 2 TB</div>
       <div class="chip" id="prn" style="left:80px;top:830px;font-size:25px">US LAUNCH PRICES · <span class="mut">YOUR LOCAL PRICE AND CARRIER DEALS WILL DIFFER</span></div>
       <div class="src">SOURCES: TOM'S GUIDE · 9TO5MAC · TECHRADAR</div>`;
    this.k = root.querySelector('.kick'); this.h = root.querySelector('.h1');
    this.r = $$(root, '.pr-row'); this.hs = $$(root, '.pr-h');
    this.v = this.r.map(r => $$(r, '.pr-v')); this.no = root.querySelector('.pr-no');
    this.d = ['pd1', 'pd3', 'pd4'].map(id => root.querySelector('#' + id)); this.n = root.querySelector('#prn');
    T.r = [w('Both phones start') - .1, w('At 512') - .1, w('At one terabyte') - .1, w('only Apple') - .1];
    T.d = [w('went up') - .1, w('cheaper') - .5, w('only Apple') + .2]; T.n = w('These are US');
    [...T.r, ...T.d, T.n].forEach((x, i) => cue(x, i < 4 ? 'pop' : 'tick', 'pr' + i));
  },
  update(t) {
    const T = this.T, s = this.ts;
    pop(this.k, t, s.start + .2, {}); pop(this.h, t, s.start + .35, {});
    this.hs.forEach(e => pop(e, t, T.r[0] - .2, { dy: 8, d: .4 }));
    this.r.forEach((r, i) => {
      pop(r, t, T.r[i], { dy: 18, d: .5 });
      count(this.v[i][0], this.rows[i][1], t, T.r[i] + .1, .9, { pre: '$' });
      if (this.rows[i][2] !== null) count(this.v[i][1], this.rows[i][2], t, T.r[i] + .25, .9, { pre: '$', dec: 2 });
    });
    this.d.forEach((e, i) => pop(e, t, T.d[i], { dy: 10, s: .9, back: true, d: .45 }));
    pop(this.n, t, T.n, { dy: 12, d: .5 });
  },
});

/* ===================================================== problem cards */
css(`
.pc { position:absolute; border-radius:26px; border:2px solid; box-sizing:border-box; padding:26px 30px; background:rgba(255,255,255,.045); }
.pc .tg { display:inline-block; font:700 20px JBM, monospace; letter-spacing:.14em; padding:5px 12px; border-radius:8px; border:1.5px solid; }
.pc h5 { margin:18px 0 10px; font:800 36px InterV, sans-serif; letter-spacing:-.02em; line-height:1.1; }
.pc p { margin:0; font:500 26px InterV, sans-serif; line-height:1.28; color:rgba(242,251,255,.82); }
.pc.k-bad { border-color:rgba(255,107,107,.8); background:rgba(255,107,107,.08); } .pc.k-bad .tg { color:#04090B; background:var(--bad); border-color:var(--bad); }
.pc.k-rep { border-color:rgba(255,181,71,.6); } .pc.k-rep .tg { color:var(--warn); border-color:rgba(255,181,71,.6); }
.pc.k-rev { border-color:rgba(184,196,200,.4); } .pc.k-rev .tg { color:#B8C4C8; border-color:rgba(184,196,200,.4); }
.pc.sm { padding:22px 24px; } .pc.sm .tg { font-size:17px; padding:4px 10px; } .pc.sm h5 { font-size:31px; margin:16px 0 8px; } .pc.sm p { font-size:24px; }
`);
const card = (x, y, w, h, kind, tag, title, detail, sm) => `<div class="pc k-${kind}${sm ? ' sm' : ''}" style="left:${x}px;top:${y}px;width:${w}px;height:${h}px;opacity:0"><span class="tg">${tag}</span><h5>${title}</h5><p>${detail}</p></div>`;

V.add('iphone_bad', {
  build(root) {
    const T = {}; this.T = T; const w = (p, n) => W('iphone_bad', p, n || 0);
    const X = [80, 680, 1280], Y = [262, 592];
    root.innerHTML = head('PROBLEMS · IPHONE', 'iPhone problems: <span class="bad">one confirmed</span>, others reported') +
      card(X[0], Y[0], 560, 300, 'bad', 'CONFIRMED BY APPLE · OCT 3', 'Loses AT&amp;T cellular service', 'Some iPhone 18 Pro Max units. Affected phones need a hardware replacement; a software update can only help prevent it.') +
      card(X[1], Y[0], 560, 300, 'rep', 'REPORTED · NOT CONFIRMED', 'Freezes and restarts', 'Owners of the iPhone 18 Pro link them to Face ID and touch input. Macworld could not confirm the Face ID cause.') +
      card(X[2], Y[0], 560, 300, 'rep', 'REPORTED · NOT ACKNOWLEDGED', 'Crackling audio', 'Some owners report it. Apple has not acknowledged the reports.') +
      card(X[0], Y[1], 560, 300, 'rev', 'WHAT REVIEWS SAY', 'The heaviest iPhone ever', '249 g, which is 16 g more than last year&rsquo;s Pro Max.') +
      card(X[1], Y[1], 560, 300, 'rev', 'WHAT REVIEWS SAY', '+$100, mostly incremental', '9to5Mac: iPhone 17 Pro owners have little reason to upgrade.') +
      card(X[2], Y[1], 560, 300, 'rev', 'US MODEL', 'eSIM only', 'The US version has no physical SIM.') +
      `<div class="src">SOURCES: MACWORLD · TECH ADVISOR · 9TO5MAC · NOTEBOOKCHECK · ANDROID CENTRAL · REPORTS ARE NOT CONFIRMED UNLESS MARKED</div>`;
    this.k = root.querySelector('.kick'); this.h = root.querySelector('.h1'); this.c = $$(root, '.pc');
    T.c = [w('One is confirmed') - .15, w('Some iPhone 18 Pro owners') - .15, w('some report crackling audio') - .5, w('the heaviest iPhone ever') - .3, w('a 100 dollar price increase') - .2, w('eSIM only') - .7];
    T.c.forEach((x, i) => cue(x, i === 0 ? 'impact' : 'pop', 'ib' + i));
  },
  update(t) {
    const T = this.T, s = this.ts;
    pop(this.k, t, s.start + .2, {}); pop(this.h, t, s.start + .35, {});
    this.c.forEach((c, i) => pop(c, t, T.c[i], { dy: 30, d: .6, back: i === 0 }));
  },
});

V.add('galaxy_bad', {
  build(root) {
    const T = {}; this.T = T; const w = (p, n) => W('galaxy_bad', p, n || 0);
    const X = [80, 530, 980, 1430], Y = [262, 592], CW = 410, CH = 300;
    root.innerHTML = head('PROBLEMS · GALAXY', 'Galaxy problems: <span class="warn">mostly owner reports</span>') +
      card(X[0], Y[0], CW, CH, 'rep', 'REPORTED', 'Privacy Display complaints', 'Fuzzy text, headaches and eye strain. How widespread: unclear.', 1) +
      card(X[1], Y[0], CW, CH, 'bad', 'SAMSUNG APOLOGIZED', '10-bit panel claim', 'Advertised a 10-bit panel. The display is 8-bit with 10-bit processing.', 1) +
      card(X[2], Y[0], CW, CH, 'rep', 'REPORTED · JULY', 'Red stain on screen', 'After 3 to 4 months. Samsung blamed the Privacy Display in strong light at maximum brightness, and says it can fix it.', 1) +
      card(X[3], Y[0], CW, CH, 'rep', 'REPORTED · APRIL', 'Blurry 3× telephoto photos', 'Samsung said it was investigating.', 1) +
      card(X[0], Y[1], CW, CH, 'rep', 'ANDROID AUTHORITY', 'Wireless charging dips', 'Wireless charging often drops to 10 to 15 watts.', 1) +
      card(X[1], Y[1], CW, CH, 'rep', 'TECHRADAR REVIEW', 'Gemini and the Uber booking', 'TechRadar caught Gemini claiming a booking that did not exist.', 1) +
      card(X[2], Y[1], CW, CH, 'rep', 'REPORTED · OCTOBER', 'One UI 9 setup bug', 'Some phones got stuck during setup after a factory reset.', 1) +
      card(X[3], Y[1], CW, CH, 'rev', 'WHAT REVIEWS SAY', 'Little has changed', 'The S Pen is unchanged, there are no built-in magnets, and the price.', 1) +
      `<div class="src">SOURCES: TOM'S GUIDE · ANDROID CENTRAL · ANDROID AUTHORITY · TECHRADAR · BGR · ENGADGET · MOST ITEMS ARE OWNER REPORTS</div>`;
    this.k = root.querySelector('.kick'); this.h = root.querySelector('.h1'); this.c = $$(root, '.pc');
    T.c = [w('The biggest complaint') - .25, w('Samsung also apologized') - .15, w('In July') - .15, w('In April') - .15, w('Android Authority') - .15, w('TechRadar caught') - .15, w('in October') - .2, w('Reviewers also') - .15];
    T.c.forEach((x, i) => cue(x, 'pop', 'gb' + i));
  },
  update(t) {
    const T = this.T, s = this.ts;
    pop(this.k, t, s.start + .2, {}); pop(this.h, t, s.start + .35, {});
    this.c.forEach((c, i) => pop(c, t, T.c[i], { dy: 30, d: .6 }));
  },
});

/* ===================================================== score */
css(`
.sc-row { position:absolute; left:80px; width:1000px; height:76px; display:flex; align-items:center; border-radius:18px; border:2px solid rgba(255,255,255,.1); background:rgba(255,255,255,.04); box-sizing:border-box; padding:0 24px 0 30px; }
.sc-row b { flex:1; font:700 33px InterV, sans-serif; }
.sc-w { font:800 31px InterV, sans-serif; padding:6px 24px; border-radius:30px; border:2px solid; }
.tal { position:absolute; top:268px; width:220px; height:212px; border-radius:26px; border:2px solid; box-sizing:border-box; text-align:center; padding-top:14px; background:rgba(255,255,255,.04); }
.tal .n { font:800 118px InterV, sans-serif; line-height:1; letter-spacing:-.04em; font-variant-numeric:tabular-nums; }
.tal small { display:block; font:700 19px JBM, monospace; letter-spacing:.14em; color:var(--mut); margin-top:8px; }
.sc-p { position:absolute; left:1130px; width:710px; border-radius:26px; border:2px solid rgba(255,255,255,.14); background:rgba(255,255,255,.045); box-sizing:border-box; padding:24px 32px; }
.sc-p .tt { font:700 21px JBM, monospace; letter-spacing:.16em; color:var(--mut); }
.stl { display:flex; align-items:center; height:66px; margin-top:6px; }
.stl i { width:150px; font-style:normal; font-weight:800; font-size:32px; }
.stl .st { flex:1; font-size:44px; letter-spacing:.06em; white-space:nowrap; }
.stl .sv { width:90px; text-align:right; font:700 32px JBM, monospace; }
.half { background:linear-gradient(90deg, #00FF87 50%, rgba(255,255,255,.22) 50%); -webkit-background-clip:text; background-clip:text; color:transparent; }
`);
V.add('score', {
  build(root) {
    const T = {}; this.T = T; const w = (p, n) => W('score', p, n || 0);
    const R = [['Design', 'iphone', 'Design'], ['Display', 'galaxy', 'Display'], ['Cameras', 'iphone', 'Cameras'], ['Performance', 'iphone', 'Performance'], ['Battery and charging', 'iphone', 'Battery and charging'], ['Software and AI', 'galaxy', 'Software and AI'], ['Price', 'tie', 'Price']];
    const col = { iphone: ['#00F5FF', 'iPhone'], galaxy: ['#00FF87', 'Galaxy'], tie: ['#B8C4C8', 'Tie'] };
    root.innerHTML = head('SCOREBOARD', "Tom's Guide face-off: <span class=\"c1\">iPhone 4</span>, <span class=\"c2\">Galaxy 2</span>, one tie") +
      R.map((r, i) => `<div class="sc-row" style="top:${268 + i * 90}px;opacity:0"><b>${r[0]}</b><span class="sc-w" style="color:${col[r[1]][0]};border-color:${col[r[1]][0]};opacity:0">${col[r[1]][1]}</span></div>`).join('') +
      `<div class="tal" style="left:1130px;border-color:#00F5FF"><div class="n c1">0</div><small>iPHONE ROUNDS</small></div><div class="tal" style="left:1375px;border-color:#00FF87"><div class="n c2">0</div><small>GALAXY ROUNDS</small></div><div class="tal" style="left:1620px;border-color:#B8C4C8"><div class="n" style="color:#B8C4C8">0</div><small>TIE</small></div>
       <div class="sc-p" id="tr" style="top:508px;height:242px"><div class="tt">TECHRADAR HEAD-TO-HEAD</div>
         <div class="stl"><i class="c1">iPhone</i><span class="st c1">★★★★★</span><span class="sv c1">5</span></div>
         <div class="stl"><i class="c2">Galaxy</i><span class="st c2">★★★★<span class="half">★</span></span><span class="sv c2">4.5</span></div></div>
       <div class="sc-p" id="ac" style="top:778px;height:96px;display:flex;align-items:center;justify-content:space-between"><span class="tt">ANDROID CENTRAL PICKED</span><span class="c1" style="font-weight:800;font-size:40px">iPhone</span></div>
       <div class="src">SOURCES: TOM'S GUIDE · TECHRADAR · ANDROID CENTRAL</div>`;
    this.k = root.querySelector('.kick'); this.h = root.querySelector('.h1'); this.rows = $$(root, '.sc-row'); this.win = $$(root, '.sc-w');
    this.tal = $$(root, '.tal'); this.tn = $$(root, '.tal .n'); this.tr = root.querySelector('#tr'); this.ac = root.querySelector('#ac');
    T.row = R.map(r => w(r[2]) - .1); T.win = R.map(r => WE('score', r[2]) - .05);
    T.tal = [w('four rounds') - .1, w('two to the Galaxy') - .1, w('and one tie') - .1]; T.tr = w("TechRadar's head-to-head") - .1; T.ac = w('Android Central') - .1;
    this.vals = [4, 2, 1];
    [...T.row, ...T.tal, T.tr, T.ac].forEach((x, i) => cue(x, i < 7 ? 'tick' : 'pop', 'sc' + i));
  },
  update(t) {
    const T = this.T, s = this.ts;
    pop(this.k, t, s.start + .2, {}); pop(this.h, t, s.start + .35, {});
    this.rows.forEach((r, i) => pop(r, t, T.row[i], { dy: 14, d: .45 }));
    this.win.forEach((e, i) => pop(e, t, T.win[i], { dy: 0, s: .8, back: true, d: .4 }));
    this.tal.forEach((e, i) => { pop(e, t, T.tal[i], { dy: 22, d: .5 }); count(this.tn[i], this.vals[i], t, T.tal[i] + .15, .6, {}); });
    pop(this.tr, t, T.tr, { dy: 22, d: .55 }); pop(this.ac, t, T.ac, { dy: 22, d: .55 });
  },
});

/* ===================================================== verdict */
css(`
.vd-c { position:absolute; top:258px; width:840px; height:536px; border-radius:30px; border:2px solid; box-sizing:border-box; padding:26px 34px; background:linear-gradient(160deg, rgba(255,255,255,.065), rgba(255,255,255,.02)); }
.vd-h { display:flex; align-items:center; gap:26px; height:150px; }
.vd-ph { position:relative; flex:none; height:150px; }
.vd-n { font-weight:800; font-size:48px; letter-spacing:-.025em; line-height:1.05; }
.vd-t { font:700 21px JBM, monospace; letter-spacing:.18em; margin-bottom:8px; }
.vd-l { font:700 21px JBM, monospace; letter-spacing:.16em; color:var(--mut); margin:22px 0 12px; }
.vd-w { display:flex; flex-wrap:wrap; gap:10px 12px; min-height:112px; align-content:flex-start; }
.vd-w span { font:800 27px InterV, sans-serif; padding:8px 18px; border-radius:14px; border:2px solid; }
.vd-i { font-weight:600; font-size:31px; line-height:1.28; color:rgba(242,251,255,.92); min-height:80px; }
.vd-cau { position:absolute; top:818px; height:74px; border-radius:18px; border:2px solid; box-sizing:border-box; display:flex; align-items:center; padding:0 26px; font:700 24px JBM, monospace; letter-spacing:.06em; background:rgba(4,9,11,.85); }
.en-big { position:absolute; left:0; width:1920px; top:150px; text-align:center; font-weight:800; font-size:72px; line-height:1.1; letter-spacing:-.03em; }
.en-brand { position:absolute; left:0; width:1920px; top:392px; text-align:center; font:800 62px JBM, monospace; letter-spacing:.14em; color:var(--c2); }
.en-sub { position:absolute; left:0; width:1920px; top:478px; text-align:center; font:600 30px InterV, sans-serif; color:var(--mut); }
.en-col { position:absolute; top:590px; width:540px; }
.en-col b { display:block; font:700 21px JBM, monospace; letter-spacing:.16em; color:var(--mut); margin-bottom:10px; }
.en-col span { display:block; font:600 27px InterV, sans-serif; line-height:1.42; color:rgba(242,251,255,.9); }
.en-cr { position:absolute; left:0; width:1920px; top:858px; text-align:center; font:600 21px JBM, monospace; letter-spacing:.06em; line-height:1.6; color:var(--dim); }
`);
V.add('verdict', {
  build(root) {
    const T = {}; this.T = T; const w = (p, n) => W('verdict', p, n || 0);
    const col = (x, color, tag, name, photo, wins, choose) => `<div class="vd-c" style="left:${x}px;border-color:${color};opacity:0"><div class="vd-h"><div class="vd-ph" id="${photo}"></div><div><div class="vd-t" style="color:${color}">${tag}</div><div class="vd-n" style="color:${color}">${name}</div></div></div>
      <div class="vd-l">WINS ON</div><div class="vd-w">${wins.map(x => `<span style="color:${color};border-color:${color};opacity:0">${x}</span>`).join('')}</div>
      <div class="vd-l">CHOOSE IT IF</div><div class="vd-i" style="opacity:0">${choose}</div></div>`;
    this.A = mkPhase(root, head('VERDICT', 'So which one <span class="c1">should you buy?</span>') +
      col(80, '#00F5FF', 'APPLE', 'iPhone 18 Pro Max', 'vpa', ['Speed', 'Video', 'Battery life', 'Built-in magnets'], 'You want the fastest chip and the best video.') +
      col(1000, '#00FF87', 'SAMSUNG', 'Galaxy S26 Ultra', 'vpb', ['Weight', 'Screen sharpness', 'Zoom range', 'S Pen', '7 years of updates'], 'You want a lighter phone, a stylus, and the longest update promise.') +
      `<div class="vd-cau" id="cau1" style="left:80px;width:840px;border-color:rgba(255,255,255,.35);color:#F2FBFF;opacity:0">LAST YEAR'S iPHONE PRO? LITTLE REASON TO UPGRADE</div>
       <div class="vd-cau" id="cau2" style="left:1000px;width:840px;border-color:rgba(255,181,71,.7);color:var(--warn);opacity:0">UNDER 2 MONTHS ON SALE · LONG-TERM RECORD UNKNOWN</div>
       <div class="src">SOURCES: SEE THE PREVIOUS CHAPTERS · 9TO5MAC · PHOTOS: APPLE, SAMSUNG NEWSROOMS</div>`);
    // real press photos in the two columns
    const pa = V.media({ still: 'apple_colors.jpg', h: 150, ar: 3840 / 2743, x: 0, y: 0, color: 'rgba(0,245,255,.55)' }), pb = V.media({ still: 'samsung_family.jpg', h: 150, ar: 4 / 3, x: 0, y: 0, color: 'rgba(0,255,135,.55)' });
    pa.el.style.opacity = pb.el.style.opacity = 1;
    const ha = this.A.querySelector('#vpa'), hb = this.A.querySelector('#vpb'); ha.style.width = pa.w + 'px'; hb.style.width = pb.w + 'px'; ha.append(pa.el); hb.append(pb.el);
    this.cols = $$(this.A, '.vd-c'); this.wins = this.cols.map(c => $$(c, '.vd-w span')); this.ch = this.cols.map(c => c.querySelector('.vd-i')); this.cau = [this.A.querySelector('#cau1'), this.A.querySelector('#cau2')];
    // end card
    this.B = mkPhase(root, `<div class="en-big">Every number comes from<br>the sources in the description</div><div class="en-brand">TECHPULSEREPORT</div><div class="en-sub">Follow for more tech</div>
      <div class="en-col" style="left:80px"><b>SPECS AND PRICES</b><span>Apple and Samsung spec pages</span><span>Apple and Samsung newsrooms</span><span>Notebookcheck · GSMArena</span></div>
      <div class="en-col" style="left:690px"><b>LAB TESTS AND REVIEWS</b><span>Tom's Guide · DXOMARK</span><span>Android Central · TechRadar</span><span>9to5Mac · Engadget</span></div>
      <div class="en-col" style="left:1300px"><b>PROBLEM REPORTS</b><span>Macworld · Tech Advisor</span><span>Android Authority · BGR</span><span>Android Central · TechRadar</span></div>
      <div class="en-cr">PHOTOS AND VIDEO: APPLE NEWSROOM AND SAMSUNG NEWSROOM (PRESS MATERIAL, SHOWN UNCHANGED)<br>US LAUNCH PRICES · FACTS CHECKED NOV 11, 2026</div>`);
    this.en = [...this.B.children];
    T.a = { in: w('So which') - .1, ip: w('the iPhone wins') - .3, ipw: [w('speed'), w('video'), w('battery life'), w('built-in magnets')], ga: w('The Galaxy wins') - .3, gaw: [w('weight'), w('screen sharpness'), w('zoom range'), w('S Pen'), w('seven years')],
      ci: w('Choose the iPhone') - .1, cg: w('Choose the Galaxy') - .1, c1: w('If you already own') - .1, c2: w('One more caution') - .1 };
    T.b = { in: w('Every number') - .3 };
    this.kh = [this.A.querySelector('.kick'), this.A.querySelector('.h1')];
    [T.a.ip, ...T.a.ipw, T.a.ga, ...T.a.gaw, T.a.ci, T.a.cg, T.a.c1, T.a.c2].forEach((x, i) => cue(x, 'pop', 'vd' + i));
    cue(T.b.in + .4, 'stamp', 'brand');
  },
  update(t) {
    const T = this.T, s = this.ts, b = T.b.in + .3;
    setPhase(this.A, phaseOpacity(t, s.start, b)); setPhase(this.B, phaseOpacity(t, b - .3));
    pop(this.kh[0], t, s.start + .2, {}); pop(this.kh[1], t, s.start + .35, {});
    pop(this.cols[0], t, T.a.ip, { dx: -40, dy: 0, d: .65 }); pop(this.cols[1], t, T.a.ga, { dx: 40, dy: 0, d: .65 });
    this.wins[0].forEach((e, i) => pop(e, t, T.a.ipw[i] - .1, { dy: 12, s: .9, d: .4 })); this.wins[1].forEach((e, i) => pop(e, t, T.a.gaw[i] - .1, { dy: 12, s: .9, d: .4 }));
    pop(this.ch[0], t, T.a.ci, { dy: 12, d: .5 }); pop(this.ch[1], t, T.a.cg, { dy: 12, d: .5 });
    pop(this.cau[0], t, T.a.c1, { dy: 14, d: .5 }); pop(this.cau[1], t, T.a.c2, { dy: 14, d: .5 });
    // end card
    const e = this.en, t0 = T.b.in + .1;
    pop(e[0], t, t0, { dy: 24, d: .7 }); pop(e[1], t, t0 + .5, { dy: 14, d: .6 }); pop(e[2], t, t0 + .75, { dy: 10, d: .5 });
    [3, 4, 5].forEach((k, i) => pop(e[k], t, t0 + 1.0 + i * .18, { dy: 14, d: .5 })); pop(e[6], t, t0 + 1.6, { dy: 0, d: .6 });
  },
});
})();
