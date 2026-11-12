/* Scenes 4-8: design, display, perf, camera, battery */
(() => {
const { W, WE, pop, prog, easeOut, easeIn, clamp, count, mk, css, cue, phaseOpacity } = V;
const head = (k, h) => `<div class="kick">${k}</div><div class="h1">${h}</div>`;
const mkPhase = (root, html) => { const el = document.createElement('div'); el.className = 'abs ph'; el.innerHTML = html; root.appendChild(el); return el; };
const setPhase = (el, op) => { el.style.opacity = op.toFixed(3); el.style.display = op > .002 ? 'block' : 'none'; };
const $$ = (root, s) => [...root.querySelectorAll(s)];

css(`
.tb { position:absolute; left:1010px; top:262px; width:830px; }
.tb-h { display:flex; height:54px; align-items:center; font:800 30px InterV, sans-serif; }
.tb-h b { width:330px; } .tb-h i { width:170px; }
.tb-r { display:flex; align-items:center; min-height:106px; border-top:1.5px solid var(--line); }
.tb-r .k { width:170px; font:600 22px JBM, monospace; letter-spacing:.14em; color:var(--mut); }
.tb-r .a, .tb-r .b { width:330px; padding-right:16px; box-sizing:border-box; font-weight:700; font-size:30px; line-height:1.14; }
.tb-r .no { color:var(--dim); font-weight:600; }
.note { position:absolute; font:600 26px InterV, sans-serif; color:var(--mut); }
.note b { color:var(--ink); }
`);

/* ===================================================== design */
V.add('design', {
  build(root) {
    root.innerHTML = head('DESIGN & BUILD', 'Same screen size. <span class="c1">The iPhone</span> is the heavier phone.');
    this.w = V.barPair({ label: 'WEIGHT', a: 249, b: 214, max: 270, x: 80, y: 262, w: 900, suf: ' g', delta: { t: '+35 g', c: '#F2FBFF' } });
    this.th = V.barPair({ label: 'THICKNESS', a: 8.75, b: 7.9, max: 10, x: 80, y: 540, w: 900, suf: ' mm', fmt: x => x.toFixed(2).replace(/0$/, ''), delta: { t: '+0.85 mm', c: '#F2FBFF' } });
    root.append(this.w.el, this.th.el);
    this.last = mk(`<div class="note" style="left:80px;top:468px">↳ <b>16 g more</b> than last year's Pro Max (233 g)</div>`);
    root.append(this.last);
    const rows = [['SCREEN', '6.9″', '6.9″'], ['WATER', 'IP68<span class="x"> · 6 m</span>', 'IP68<span class="x"> · 1.5 m</span>'], ['FRAME', 'Aluminum, Ceramic Shield 2 glass', 'Armor Aluminum'],
      ['MAGNETS', 'Built in (MagSafe)', '<span class="no">None built in</span>'], ['STYLUS', '<span class="no">None</span>', 'S Pen built in']];
    this.tb = mk(`<div class="tb"><div class="tb-h"><i></i><b class="c1">iPhone</b><b class="c2">Galaxy</b></div>${rows.map(r => `<div class="tb-r"><div class="k">${r[0]}</div><div class="a">${r[1]}</div><div class="b">${r[2]}</div></div>`).join('')}</div>`);
    root.append(this.tb);
    this.rows = $$(this.tb, '.tb-r'); this.xs = $$(this.tb, '.x'); this.head = this.tb.querySelector('.tb-h');
    this.src = mk(`<div class="src">SOURCES: APPLE · SAMSUNG · 9TO5MAC · TECHRADAR · GSMARENA · PHOTOS: PRESS KITS</div>`); root.append(this.src);
    // real press photos (shown whole and unchanged) while the body is introduced
    this.ph = [V.media({ still: 'apple_2up.jpg', h: 400, ar: 2160 / 3024, x: 80, y: 270, color: 'rgba(0,245,255,.55)' }), V.media({ still: 'samsung_buds.jpg', h: 400, ar: 4 / 3, x: 80 + 400 * 2160 / 3024 + 34, y: 270, color: 'rgba(0,255,135,.55)' })];
    root.append(this.ph[0].el, this.ph[1].el);
    this.rd = V.round('iphone', "TOM'S GUIDE · DESIGN ROUND"); root.append(this.rd);
    this.k = this.el = root.querySelector('.kick'); this.h = root.querySelector('.h1');
    const w = (p, n) => W('design', p, n || 0);
    this.T = { w1: w('249'), w2: w('214'), th1: w('8.75'), th2: w('7.9'), last: w('16'), rows: [w('Both'), w('IP68'), w('frames'), w('magnets'), w('S Pen')], six: w('six'), one: w('one'), tr: w('TechRadar'),
      round: this.ts.end - 6 };
    const T = this.T;
    [T.w1, T.w2, T.th1, T.th2, T.last, ...T.rows, T.six, T.one].forEach((x, i) => cue(x, 'tick', 'd' + i));
    cue(T.w2 + 1.0, 'pop', 'dw'); cue(T.th2 + 1.0, 'pop', 'dt'); cue(T.round, 'stamp', 'round');
  },
  update(t) {
    const T = this.T;
    pop(this.k, t, this.ts.start + .2, {}); pop(this.h, t, this.ts.start + .35, {});
    this.w.update(t, T.w1 - .2, T.w2 - .2, 1.0, T.w2 + 1.0);
    this.th.update(t, T.th1 - .2, T.th2 - .2, 1.0, T.th2 + 1.0);
    pop(this.last, t, T.last, { dy: 12, d: .5 });
    pop(this.head, t, T.rows[0] - .3, { dy: 10, d: .4 });
    this.rows.forEach((r, i) => pop(r, t, T.rows[i], { dy: 16, d: .5 }));
    pop(this.xs[0], t, T.six, { dy: 0, d: .4 }); pop(this.xs[1], t, T.one, { dy: 0, d: .4 });
    pop(this.src, t, this.ts.start + 3, { dy: 0, o: 1 });
    this.ph.forEach((m, i) => pop(m.el, t, this.ts.start + .9 + i * .15, { dy: 20, d: .7, t1: T.w1 - .6, d1: .35 }));
    pop(this.rd, t, T.round, { dy: 12, s: .9, back: true, d: .5 });
  },
});

/* ===================================================== display */
css(`
.scr { position:absolute; border-radius:34px; border:3px solid; box-sizing:border-box; display:flex; align-items:center; justify-content:center; background:linear-gradient(160deg, rgba(255,255,255,.09), rgba(255,255,255,.02)); }
.scr .res { font:700 42px JBM, monospace; letter-spacing:-.01em; }
.scr .sz { position:absolute; left:22px; top:16px; font:700 22px JBM, monospace; letter-spacing:.12em; color:var(--mut); }
.ppi { position:absolute; text-align:center; width:700px; font:800 120px InterV, sans-serif; letter-spacing:-.03em; line-height:1; font-variant-numeric:tabular-nums; }
.ppi small { display:block; font:600 24px JBM, monospace; letter-spacing:.18em; color:var(--mut); margin-top:10px; }
.pv-l { position:absolute; font:700 24px JBM, monospace; letter-spacing:.12em; }
.cost { position:absolute; left:1090px; width:700px; display:flex; align-items:center; gap:22px; padding:18px 26px; border-radius:20px; border:2px solid rgba(255,107,107,.55); background:rgba(255,107,107,.07); font-weight:800; font-size:38px; }
.cost i { font:700 24px JBM, monospace; letter-spacing:.14em; color:var(--bad); font-style:normal; }
`);
V.add('display', {
  build(root) {
    const T = {}; this.T = T;
    const w = (p, n) => W('display', p, n || 0);
    // ---------- A: pixels
    this.A = mkPhase(root, head('SCREEN', 'Same size, <span class="c2">more pixels</span> on the Galaxy') +
      `<div class="scr" id="sA" style="left:193px;top:330px;width:574px;height:264px;border-color:#00F5FF"><div class="sz">6.9″ · 120 Hz</div><div class="res c1" id="rA">2,868 × 1,320</div></div>
       <div class="scr" id="sB" style="left:1128px;top:318px;width:624px;height:288px;border-color:#00FF87"><div class="sz">6.9″ · 120 Hz</div><div class="res c2" id="rB">3,120 × 1,440</div></div>
       <div class="ppi c1" id="pA" style="left:130px;top:660px">460<small>PIXELS PER INCH</small></div>
       <div class="ppi c2" id="pB" style="left:1090px;top:660px">~500<small>PIXELS PER INCH</small></div>
       <div class="src">SOURCES: APPLE SPEC PAGE · SAMSUNG · TECHRADAR</div>`);
    T.A = { scr: w('Both') - .1, rB: w('3,120') - .1, pB: w('500') - .2, rA: w('2,868') - .1, pA: w('460') - .2 };
    // ---------- B: brightness
    this.B = mkPhase(root, head('SCREEN', 'Brightness: <span class="c1">the iPhone leads</span>, on paper and in the lab'));
    this.b1 = V.barPair({ label: 'PEAK BRIGHTNESS, MANUFACTURER CLAIM (NITS)', a: 3000, b: 2600, max: 3300, x: 80, y: 290, w: 1760 });
    this.b2 = V.barPair({ label: "PEAK BRIGHTNESS, MEASURED IN TOM'S GUIDE LAB (NITS)", a: 2326, b: 1806, max: 3300, x: 80, y: 570, w: 1760 });
    this.B.append(this.b1.el, this.b2.el);
    this.B.append(mk(`<div class="src">LAB TEST MODE IS NOT STATED BY THE ARTICLE · SOURCES: APPLE · SAMSUNG · TOM'S GUIDE</div>`));
    T.B = { in: w('brightness') - .3, a1: w('3,000'), b1: w('2,600.'), a2: w('2,300'), b2: w('1,800.') };
    // ---------- C: privacy display
    this.C = mkPhase(root, head('SCREEN', '<span class="c2">Privacy Display</span>: only on the Galaxy') +
      `
       <div class="pv-l mut" id="pvc" style="left:1090px;top:290px">THE TRADE-OFF · ANDROID CENTRAL</div>
       <div class="cost" id="cs1" style="top:344px"><i>LOWER</i>effective resolution</div>
       <div class="cost" id="cs2" style="top:464px"><i>LOWER</i>brightness</div>
       <div class="cost" id="cs3" style="top:584px"><i>LOWER</i>contrast</div>
       <div class="src">SOURCES: SAMSUNG · ANDROID CENTRAL · TOM'S GUIDE · VIDEO: SAMSUNG NEWSROOM</div>`);
    this.vid = V.media({ clip: 'privacy', n: 502, x: 80, y: 290, w: 900, ar: 16 / 9, color: 'rgba(0,255,135,.6)' }); this.C.append(this.vid.el);
    T.C = { in: w('But') - .3, svg: w('Privacy') - .2, cost: w('Android') - .1, c1: w('resolution,'), c2: w('brightness', 1), c3: w('contrast.'), round: w("Tom's", 1) };
    this.rd = V.round('galaxy', "TOM'S GUIDE · DISPLAY ROUND"); this.C.append(this.rd);
    this.sA = $$(this.A, '.scr'); this.ppA = $$(this.A, '.ppi'); this.rA = $$(this.A, '.res');
    this.csts = $$(this.C, '.cost'); this.pvc = this.C.querySelector('#pvc');
    this.kh = [$$(this.A, '.kick')[0], $$(this.A, '.h1')[0]];
    const a = T.A; [a.scr, a.rB, a.pB, a.rA, a.pA, T.B.a1, T.B.b1, T.B.a2, T.B.b2, T.C.svg, T.C.c1, T.C.c2, T.C.c3].forEach((x, i) => cue(x, 'tick', 'dp' + i));
    cue(T.C.round, 'stamp', 'round');
  },
  update(t) {
    const T = this.T, s = this.ts;
    const tB = T.B.in + .3, tC = T.C.in + .3;
    setPhase(this.A, phaseOpacity(t, s.start, tB)); setPhase(this.B, phaseOpacity(t, tB - .3, tC)); setPhase(this.C, phaseOpacity(t, tC - .3));
    // A
    pop(this.kh[0], t, s.start + .2, {}); pop(this.kh[1], t, s.start + .35, {});
    pop(this.sA[0], t, T.A.scr, { dy: 24, d: .6 }); pop(this.sA[1], t, T.A.scr + .12, { dy: 24, d: .6 });
    pop(this.rA[1], t, T.A.rB, { dy: 10, d: .45 }); pop(this.ppA[1], t, T.A.pB, { dy: 18, d: .55 });
    pop(this.rA[0], t, T.A.rA, { dy: 10, d: .45 }); pop(this.ppA[0], t, T.A.pA, { dy: 18, d: .55 });
    // B
    this.b1.update(t, T.B.a1 - .1, T.B.b1 - .1, 1.1); this.b2.update(t, T.B.a2 - .1, T.B.b2 - .1, 1.1);
    // C
    pop(this.vid.el, t, T.C.svg, { dy: 16, d: .7 }); if (t > T.C.svg - .5) this.vid.at(t, T.C.svg, 0); pop(this.pvc, t, T.C.cost, { dy: 10, d: .4 });
    pop(this.csts[0], t, T.C.c1 - .2, { dx: 40, dy: 0, d: .5 }); pop(this.csts[1], t, T.C.c2 - .2, { dx: 40, dy: 0, d: .5 }); pop(this.csts[2], t, T.C.c3 - .2, { dx: 40, dy: 0, d: .5 });
    pop(this.rd, t, T.C.round, { dy: 12, s: .9, back: true, d: .5 });
  },
});

/* ===================================================== perf */
css(`
.gl { position:absolute; width:800px; height:440px; border-radius:26px; border:2px solid; box-sizing:border-box; padding:26px 34px; background:rgba(255,255,255,.04); }
.gl h4 { margin:0; font:700 24px JBM, monospace; letter-spacing:.14em; text-transform:uppercase; }
.gl .sub { font:600 21px JBM, monospace; letter-spacing:.08em; color:var(--mut); margin-top:6px; }
.gr { display:flex; align-items:center; height:84px; margin-top:12px; }
.gr .n { width:180px; font:700 28px JBM, monospace; letter-spacing:.06em; color:var(--mut); }
.gr .t { position:relative; flex:1; height:42px; border-radius:12px; background:rgba(255,255,255,.07); overflow:hidden; }
.gr .f { position:absolute; left:0; top:0; bottom:0; width:100%; transform-origin:0 50%; transform:scaleX(0); border-radius:12px; }
.gr .v { width:250px; text-align:right; white-space:nowrap; font:800 38px InterV, sans-serif; font-variant-numeric:tabular-nums; }
.chip { position:absolute; padding:12px 24px; border-radius:16px; border:2px solid rgba(255,255,255,.3); background:rgba(255,255,255,.06); font:700 27px InterV, sans-serif; }
`);
V.add('perf', {
  build(root) {
    const T = {}; this.T = T; const w = (p, n) => W('perf', p, n || 0);
    // ---- P1 geekbench
    this.P1 = mkPhase(root, head('PERFORMANCE', 'Geekbench 6: <span class="c1">the iPhone is ahead</span>'));
    this.g1 = V.barPair({ label: 'GEEKBENCH 6 · SINGLE-CORE', a: 4741, b: 3785, max: 5200, x: 80, y: 270, w: 1760, delta: { t: '+25%', c: '#00F5FF' } });
    this.g2 = V.barPair({ label: 'GEEKBENCH 6 · MULTI-CORE', a: 12789, b: 11563, max: 14000, x: 80, y: 560, w: 1760, delta: { t: '+11%', c: '#00F5FF' } });
    this.P1.append(this.g1.el, this.g2.el, mk(`<div class="src">SOURCE: TOM'S GUIDE LAB TESTS (iPHONE 18 PRO MAX, GALAXY S26 ULTRA)</div>`));
    T.p1 = { s1: w('4,741'), m1: w('12,789'), s2: w('3,785'), m2: w('11,563'), d1: w('25'), d2: w('11') };
    // ---- P2 graphics + stress
    this.P2 = mkPhase(root, head('PERFORMANCE', 'Graphics and heat: <span class="c1">the gap grows</span>'));
    this.s3 = V.barPair({ label: '3DMARK SOLAR BAY · FRAMES PER SECOND', a: 67.9, b: 49.4, max: 75, x: 80, y: 290, w: 860, dec: 1, delta: { t: '+37%', c: '#00F5FF' } });
    this.P2.append(this.s3.el);
    this.r1 = V.ring({ x: 1210, y: 560, r: 128, sw: 24, frac: .794, value: 79.4, dec: 0, suf: '%', color: '#00F5FF', label: 'iPHONE' });
    this.r2 = V.ring({ x: 1610, y: 560, r: 128, sw: 24, frac: .539, value: 53.9, dec: 0, suf: '%', color: '#00FF87', label: 'GALAXY' });
    this.P2.append(this.r1.el, this.r2.el, mk(`<div class="pv-l mut" style="left:1040px;top:296px;font-size:23px">STRESS TEST · SPEED KEPT WHEN HOT</div>`));
    this.vc = mk(`<div class="chip" style="left:1040px;top:766px;width:800px;box-sizing:border-box;font-size:26px;line-height:1.25">Apple: the new vapor chamber has <span class="c1">3×</span> the surface area of the 17 Pro's</div>`); this.P2.append(this.vc);
    this.vap = V.media({ clip: 'vapor', n: 420, x: 80, y: 516, w: 680, ar: 16 / 9, color: 'rgba(0,245,255,.55)' }); this.P2.append(this.vap.el);
    this.P2.append(mk(`<div class="src">SOURCES: TOM'S GUIDE LAB TESTS · APPLE (VIA 9TO5MAC) · VIDEO: APPLE NEWSROOM</div>`));
    T.p2 = { in: w('3DMark') - .3, a: w('68'), b: w('49.'), st: w('stress') - .4, r1: w('79'), r2: w('54.'), vc: w('Apple', 0), d: w('49.') + 1.1 };
    // ---- P3 gains vs last year
    this.P3 = mkPhase(root, head('PERFORMANCE', 'Both chips are <span class="c1">big jumps</span> over last year'));
    const col = (x, color, title, sub, rows) => `<div class="gl" style="left:${x}px;top:290px;border-color:${color}"><h4 style="color:${color}">${title}</h4><div class="sub">${sub}</div>${rows.map(r => `<div class="gr"><div class="n">${r[0]}</div><div class="t"><div class="f" style="background:${color}"></div></div><div class="v" style="color:${color}">${r[1]}</div></div>`).join('')}</div>`;
    this.P3.insertAdjacentHTML('beforeend', col(80, '#00F5FF', 'A20 Pro vs A19 Pro', 'MEASURED BY 9TO5MAC (IPHONE 18 PRO)', [['CPU', '+22–27%'], ['GPU', '+40–45%']]) +
      col(1020, '#00FF87', 'Snapdragon 8 Elite Gen 5 vs S25 Ultra', 'SAMSUNG\'S OWN CLAIMS', [['CPU', '+19%'], ['GPU', '+24%'], ['AI ENGINE', '+39%']]));
    this.gl = $$(this.P3, '.gl'); this.gr = $$(this.P3, '.gr');
    this.grF = this.gr.map(r => r.querySelector('.f')); this.grV = this.gr.map(r => r.querySelector('.v'));
    this.grFrac = [.245 / .5, .425 / .5, .19 / .5, .24 / .5, .39 / .5];
    this.P3.append(mk(`<div class="src">SOURCES: 9TO5MAC (MEASURED) · SAMSUNG NEWSROOM (CLAIMED) · BARS ARE NOT COMPARABLE ACROSS PHONES</div>`));
    T.p3 = { in: w('Both') - .3, rows: [w('22'), w('40'), w('19'), w('24'), w('39')], g1: w('9to5Mac'), g2: w('Samsung', 0) };
    // ---- P4 AI
    this.P4 = mkPhase(root, head('PERFORMANCE', 'Geekbench AI: <span class="c2">the Galaxy wins</span>'));
    this.ai = V.barPair({ label: 'GEEKBENCH AI 1.7 · SCORE', a: 71974, b: 83047, max: 90000, x: 80, y: 340, w: 1760, delta: { t: '+15%', c: '#00FF87' } });
    this.P4.append(this.ai.el, mk(`<div class="src">SOURCE: TOM'S GUIDE LAB TESTS</div>`));
    T.p4 = { in: w('The', 5) - .4 };
    // The Galaxy wins one test -> find the 'The Galaxy wins' phrase
    T.p4.in = w('The Galaxy wins') - .4; T.p4.t = w('Geekbench', 1); T.p4.d = w('15');
    T.p3.out = T.p4.in + .1;
    this.rd = V.round('iphone', "TOM'S GUIDE · PERFORMANCE ROUND"); this.P4.append(this.rd);
    T.round = this.ts.end - 4;
    this.kh = [1, 2, 3, 4].map(i => [this['P' + i].querySelector('.kick'), this['P' + i].querySelector('.h1')]);
    [T.p1.s1, T.p1.m1, T.p1.s2, T.p1.m2, T.p1.d1, T.p1.d2, T.p2.a, T.p2.b, T.p2.r1, T.p2.r2, T.p2.vc, ...T.p3.rows, T.p4.t, T.p4.d].forEach((x, i) => cue(x, 'tick', 'pf' + i));
    cue(T.round, 'stamp', 'round');
  },
  update(t) {
    const T = this.T, s = this.ts;
    const b2 = T.p2.in + .3, b3 = T.p3.in + .3, b4 = T.p4.in + .3;
    setPhase(this.P1, phaseOpacity(t, s.start, b2)); setPhase(this.P2, phaseOpacity(t, b2 - .3, b3)); setPhase(this.P3, phaseOpacity(t, b3 - .3, b4)); setPhase(this.P4, phaseOpacity(t, b4 - .3));
    const starts = [s.start, b2 - .3, b3 - .3, b4 - .3];
    this.kh.forEach((k, i) => { pop(k[0], t, starts[i] + .25, {}); pop(k[1], t, starts[i] + .4, {}); });
    const P = T.p1;
    this.g1.update(t, P.s1 - .1, P.s2 - .1, 1.0, P.d1 + .5); this.g2.update(t, P.m1 - .1, P.m2 - .1, 1.0, P.d2 + .5);
    this.s3.update(t, T.p2.a - .1, T.p2.b - .1, 1.0, T.p2.d);
    this.r1.update(t, T.p2.r1 - .2, 1.3); this.r2.update(t, T.p2.r2 - .2, 1.3);
    pop(this.vc, t, T.p2.vc, { dy: 14, d: .5 });
    pop(this.vap.el, t, T.p2.vc - .5, { dy: 16, d: .6, t1: T.p3.in - .1, d1: .3 }); if (t > T.p2.vc - 1) this.vap.at(t, T.p2.vc - .5, 0);
    this.gl.forEach((g, i) => pop(g, t, i === 0 ? T.p3.g1 - .2 : T.p3.g2 - .2, { dy: 24, d: .6 }));
    this.grF.forEach((f, i) => { const e = V.grow(f, this.grFrac[i], t, T.p3.rows[i], .9); });
    this.grV.forEach((v, i) => pop(v, t, T.p3.rows[i] + .2, { dy: 0, d: .4 }));
    this.gr.forEach((r, i) => pop(r, t, T.p3.rows[i] - .15, { dy: 8, d: .4 }));
    this.ai.update(t, T.p4.t - .1, T.p4.t + .15, 1.1, T.p4.d);
    pop(this.rd, t, T.round, { dy: 12, s: .9, back: true, d: .5 });
  },
});

/* ===================================================== camera */
css(`
.lens { position:absolute; width:470px; height:236px; border-radius:24px; border:2px solid; box-sizing:border-box; padding:20px 28px; background:rgba(255,255,255,.04); }
.lens .l { font:700 21px JBM, monospace; letter-spacing:.16em; color:var(--mut); }
.lens .mp { font:800 88px InterV, sans-serif; letter-spacing:-.03em; line-height:1; margin-top:8px; font-variant-numeric:tabular-nums; }
.lens .mp small { font:700 32px JBM, monospace; letter-spacing:.04em; margin-left:10px; opacity:.85; }
.lens .sp { font:600 25px InterV, sans-serif; color:rgba(242,251,255,.85); margin-top:8px; line-height:1.2; }
.row-l { position:absolute; left:80px; width:200px; text-align:left; font:800 34px InterV, sans-serif; }
.col-l { position:absolute; top:284px; width:470px; text-align:center; font:700 24px JBM, monospace; letter-spacing:.2em; color:var(--mut); }
.fcard { position:absolute; top:296px; width:560px; height:400px; border-radius:30px; border:2px solid; box-sizing:border-box; padding:36px 40px; background:rgba(255,255,255,.045); }
.fcard .l { font:700 23px JBM, monospace; letter-spacing:.16em; color:var(--mut); }
.fcard .w { font:800 74px InterV, sans-serif; letter-spacing:-.03em; margin-top:26px; line-height:1.05; }
.fcard .d { font:600 28px InterV, sans-serif; color:rgba(242,251,255,.8); margin-top:18px; line-height:1.25; }
`);
V.add('camera', {
  build(root) {
    const T = {}; this.T = T; const w = (p, n) => W('camera', p, n || 0);
    // ---- P1 lens grid
    const cell = (cls, x, y, color, label, mp, sp) => `<div class="lens ${cls}" style="left:${x}px;top:${y}px;border-color:${color}"><div class="l">${label}</div><div class="mp" style="color:${color}">${mp}<small>MP</small></div><div class="sp">${sp}</div></div>`;
    const X = [330, 830, 1330];
    this.P1 = mkPhase(root, head('CAMERAS', 'Three 48 MP lenses, <span class="c2">or a 200 MP main</span>') +
      `<div class="col-l" style="left:${X[0]}px">ULTRAWIDE</div><div class="col-l" style="left:${X[1]}px">MAIN</div><div class="col-l" style="left:${X[2]}px">TELEPHOTO</div>
       <div class="row-l c1" style="top:395px">iPhone</div><div class="row-l c2" style="top:660px">Galaxy</div>` +
      cell('i0', X[0], 330, '#00F5FF', 'ULTRAWIDE', '48', 'f/2.2') + cell('i1', X[1], 330, '#00F5FF', 'MAIN · VARIABLE APERTURE', '48', 'f/1.48 to f/4.0') + cell('i2', X[2], 330, '#00F5FF', 'TELEPHOTO · 4×', '48', 'f/2.8') +
      cell('g0', X[0], 596, '#00FF87', 'ULTRAWIDE', '50', 'f/1.9') + cell('g1', X[1], 596, '#00FF87', 'MAIN', '200', 'f/1.4') +
      `<div class="lens g2" style="left:${X[2]}px;top:596px;border-color:#00FF87"><div class="l">TWO TELEPHOTOS</div><div class="mp" style="color:#00FF87;font-size:62px">3× · 5×</div><div class="sp">10 MP f/2.4 · 50 MP f/2.9</div></div>
       <div class="chip" id="cFront" style="left:80px;top:850px;font-size:25px">FRONT: <span class="c1">18 MP</span> vs <span class="c2">12 MP</span></div>
       <div class="chip" id="cZoom" style="left:620px;top:850px;font-size:25px">MAX DIGITAL ZOOM: <span class="c1">40×</span> vs <span class="c2">100×</span></div>
       <div class="src" style="left:1160px;top:866px;font-size:17px">SOURCES: APPLE · SAMSUNG · GSMARENA · VIDEO: APPLE NEWSROOM</div>`);
    T.p1 = { i: [w('main', 0) - .2, w('ultrawide,') - .2, w('4x') - .3], g: [w('ultrawide,', 1) - .2, w('200') - .2, w('two') - .1], front: w('front,'), zoom: w('100x') - .2, ap: w('aperture,') };
    // reorder: [ultrawide, main, tele] for each phone
    T.p1.iT = [T.p1.i[1], T.p1.i[0], T.p1.i[2]]; T.p1.gT = [T.p1.g[0], T.p1.g[1], T.p1.g[2]];
    this.l = ['i0', 'i1', 'i2', 'g0', 'g1', 'g2'].map(c => this.P1.querySelector('.' + c));
    this.colL = $$(this.P1, '.col-l, .row-l'); this.cF = this.P1.querySelector('#cFront'); this.cZ = this.P1.querySelector('#cZoom');
    this.apBd = mk(`<div style="position:absolute;left:0;top:214px;width:1920px;height:700px;background:rgba(4,9,11,.96);opacity:0"></div>`);
    this.ap = V.media({ clip: 'camera', n: 288, x: 500, y: 238, w: 920, ar: 16 / 9, color: 'rgba(0,245,255,.6)' });
    this.apL = mk(`<div class="chip" style="left:500px;top:782px;width:920px;box-sizing:border-box;text-align:center;font-size:30px;border-color:rgba(0,245,255,.6);opacity:0">iPHONE MAIN CAMERA · APERTURE <span class="c1">f/1.48 to f/4.0</span></div>`);
    this.P1.append(this.apBd, this.ap.el, this.apL);
    T.p1.ap2 = w('can change') - .25;
    // ---- P2 Tom's Guide tests
    const fc = (x, color, label, big, desc) => `<div class="fcard" style="left:${x}px;border-color:${color}"><div class="l">${label}</div><div class="w" style="color:${color}">${big}</div><div class="d">${desc}</div></div>`;
    this.P2 = mkPhase(root, head('CAMERAS', "Hands-on tests: <span class=\"mut\">it depends on the shot</span>") +
      fc(80, '#00F5FF', 'LOW LIGHT', 'iPhone', 'A sharper picture in dim conditions.') + fc(680, '#00FF87', 'SMALL TEXT AT 40× ZOOM', 'Galaxy', 'Reads small text better, though it smooths surrounding textures.') +
      fc(1280, '#B8C4C8', '10× ZOOM', 'Similar', 'Detail is remarkably similar on both phones.') + `<div class="src">SOURCE: TOM'S GUIDE HEAD-TO-HEAD PHOTO TESTS</div>`);
    this.fc = $$(this.P2, '.fcard');
    T.p2 = { in: w("Tom's") - .3, c: [w('low'), w('40x', 1), w('10x,')] };
    // ---- P3 DXOMARK
    this.P3 = mkPhase(root, head('CAMERAS', 'DXOMARK: <span class="c1">iPhone ahead</span> by 15 points overall'));
    this.dx1 = V.barPair({ label: 'DXOMARK · OVERALL CAMERA SCORE', a: 172, b: 157, max: 190, x: 80, y: 290, w: 1760, delta: { t: '+15', c: '#00F5FF' } });
    this.dx2 = V.barPair({ label: 'DXOMARK · VIDEO SCORE', a: 176, b: 153, max: 190, x: 80, y: 560, w: 1760, delta: { t: '+23', c: '#00F5FF' } });
    this.P3.append(this.dx1.el, this.dx2.el, mk(`<div class="note" style="left:80px;top:826px;font-size:24px">DXOMARK tested the <b>iPhone 18 Pro</b> (same cameras as the Pro Max). Photo score: <b class="c1">171</b> vs <b class="c2">160</b>.</div>`),
      mk(`<div class="src">SOURCE: DXOMARK CAMERA TESTS</div>`));
    T.p3 = { in: w('Then') - .3, o1: w('172'), v1: w('176'), o2: w('157'), v2: w('153'), n: w('One') };
    this.note3 = this.P3.querySelector('.note');
    this.rd = V.round('iphone', "TOM'S GUIDE · CAMERAS ROUND"); this.P3.append(this.rd);
    T.round = this.ts.end - 3.5;
    this.kh = [1, 2, 3].map(i => [this['P' + i].querySelector('.kick'), this['P' + i].querySelector('.h1')]);
    [...T.p1.iT, ...T.p1.gT, T.p1.front, T.p1.zoom, ...T.p2.c, T.p3.o1, T.p3.v1, T.p3.o2, T.p3.v2].forEach((x, i) => cue(x, 'tick', 'cm' + i));
    cue(T.round, 'stamp', 'round');
  },
  update(t) {
    const T = this.T, s = this.ts;
    const b2 = T.p2.in + .3, b3 = T.p3.in + .3;
    setPhase(this.P1, phaseOpacity(t, s.start, b2)); setPhase(this.P2, phaseOpacity(t, b2 - .3, b3)); setPhase(this.P3, phaseOpacity(t, b3 - .3));
    const starts = [s.start, b2 - .3, b3 - .3];
    this.kh.forEach((k, i) => { pop(k[0], t, starts[i] + .25, {}); pop(k[1], t, starts[i] + .4, {}); });
    const P = T.p1;
    pop(this.l[0], t, P.iT[0], { dy: 20, d: .5 }); pop(this.l[1], t, P.iT[1], { dy: 20, d: .5 }); pop(this.l[2], t, P.iT[2], { dy: 20, d: .5 });
    pop(this.l[3], t, P.gT[0], { dy: 20, d: .5 }); pop(this.l[4], t, P.gT[1], { dy: 20, d: .5 }); pop(this.l[5], t, P.gT[2], { dy: 20, d: .5 });
    this.colL.forEach(e => pop(e, t, s.start + .6, { dy: 0, d: .6 }));
    const a0 = P.ap2, a1 = T.p2.in - .55;
    [this.apBd, this.ap.el, this.apL].forEach((e, i) => pop(e, t, a0 + i * .12, { dy: i ? 18 : 0, d: .5, t1: a1, d1: .35 }));
    if (t > a0 - .5 && t < a1 + .6) this.ap.at(t, a0, 0);
    pop(this.cF, t, P.front - .1, { dy: 12, d: .5 }); pop(this.cZ, t, P.zoom, { dy: 12, d: .5 });
    const ring = V.easeOut(V.prog(t, P.ap, .3)) * (1 - V.easeIn(V.prog(t, P.ap + 2.6, .4)));
    this.l[1].style.boxShadow = `0 0 0 ${(ring * 6).toFixed(1)}px rgba(0,245,255,${(.35 * ring).toFixed(3)})`;
    this.fc.forEach((c, i) => pop(c, t, T.p2.c[i] - .2, { dy: 28, d: .6 }));
    this.dx1.update(t, T.p3.o1 - .1, T.p3.o2 - .1, 1.0, T.p3.o2 + 1.0); this.dx2.update(t, T.p3.v1 - .1, T.p3.v2 - .1, 1.0, T.p3.v2 + 1.0);
    pop(this.note3, t, T.p3.n - .2, { dy: 10, d: .5 });
    pop(this.rd, t, T.round, { dy: 12, s: .9, back: true, d: .5 });
  },
});

/* ===================================================== battery */
V.add('battery', {
  build(root) {
    const T = {}; this.T = T; const w = (p, n) => W('battery', p, n || 0);
    const mmss = m => { const mm = Math.round(m); return Math.floor(mm / 60) + ':' + String(mm % 60).padStart(2, '0'); };
    // ---- P1
    this.P1 = mkPhase(root, head('BATTERY & CHARGING', 'iPhone: <span class="c1">bigger battery, longer test</span>'));
    this.cap = V.barPair({ label: 'BATTERY CAPACITY (mAh)', a: 5391, b: 5000, max: 6000, x: 80, y: 280, w: 1760 });
    this.run = V.barPair({ label: "BATTERY TEST · HOURS:MINUTES · TOM'S GUIDE", a: 1107, b: 1000, max: 1250, x: 80, y: 560, w: 1760, time: mmss, delta: { t: '+1 h 47 min', c: '#00F5FF' } });
    this.P1.append(this.cap.el, this.run.el, mk(`<div class="note" id="capn" style="left:80px;top:482px;font-size:24px">Apple does not publish the capacity. <b>5,391 mAh</b> is the figure reviewers list.</div>`),
      mk(`<div class="src">SOURCES: NOTEBOOKCHECK · TECHRADAR · TOM'S GUIDE</div>`));
    T.p1 = { cap1: w('5,391'), cap2: w('5,000'), note: w('Apple') - .1, r1: w('18'), r2: w('16'), d: w('40.') + .4 };
    this.capn = this.P1.querySelector('#capn');
    // ---- P2 charging
    const pair = (x, title) => `<div class="pv-l mut" style="left:${x}px;top:288px;width:760px;font-size:23px;text-align:center">${title}</div>`;
    this.P2 = mkPhase(root, head('BATTERY & CHARGING', 'Charging: <span class="c1">slightly faster</span> on the iPhone') + pair(80, 'AFTER 15 MINUTES · ANDROID CENTRAL') + pair(1000, "AFTER 30 MINUTES · TOM'S GUIDE"));
    this.q = [V.ring({ x: 270, y: 560, r: 118, sw: 22, frac: .5, value: 50, suf: '%', color: '#00F5FF', label: 'iPHONE' }), V.ring({ x: 650, y: 560, r: 118, sw: 22, frac: .41, value: 41, suf: '%', color: '#00FF87', label: 'GALAXY' }),
      V.ring({ x: 1190, y: 560, r: 118, sw: 22, frac: .8, value: 80, suf: '%', color: '#00F5FF', label: 'iPHONE' }), V.ring({ x: 1570, y: 560, r: 118, sw: 22, frac: .77, value: 77, suf: '%', color: '#00FF87', label: 'GALAXY' })];
    this.P2.append(...this.q.map(r => r.el));
    this.w60 = mk(`<div class="chip" style="left:80px;top:790px;font-size:26px">BOTH: <span class="mut">RATED</span> 60 W WIRED · 25 W WIRELESS</div>`);
    this.mag = mk(`<div class="chip" style="left:1000px;top:790px;font-size:26px;border-color:rgba(0,245,255,.6)">MAGNETS BUILT IN: <span class="c1">iPhone YES</span> · <span class="c2">Galaxy NO</span></div>`);
    this.P2.append(this.w60, this.mag, mk(`<div class="src">SOURCES: ANDROID CENTRAL · TOM'S GUIDE · APPLE · SAMSUNG</div>`));
    T.p2 = { in: w('Charging') - .3, w60: w('Both'), q: [w('50'), w('41'), w('80'), w('77.')], mag: w('only') };
    this.rd = V.round('iphone', "TOM'S GUIDE · BATTERY ROUND"); this.P2.append(this.rd);
    T.round = this.ts.end - 3.2;
    this.kh = [1, 2].map(i => [this['P' + i].querySelector('.kick'), this['P' + i].querySelector('.h1')]);
    [T.p1.cap1, T.p1.cap2, T.p1.r1, T.p1.r2, T.p2.w60, ...T.p2.q, T.p2.mag].forEach((x, i) => cue(x, 'tick', 'bt' + i));
    cue(T.round, 'stamp', 'round');
  },
  update(t) {
    const T = this.T, s = this.ts, b2 = T.p2.in + .3;
    setPhase(this.P1, phaseOpacity(t, s.start, b2)); setPhase(this.P2, phaseOpacity(t, b2 - .3));
    const starts = [s.start, b2 - .3];
    this.kh.forEach((k, i) => { pop(k[0], t, starts[i] + .25, {}); pop(k[1], t, starts[i] + .4, {}); });
    const P = T.p1;
    this.cap.update(t, P.cap1 - .1, P.cap2 - .1, 1.0); pop(this.capn, t, P.note, { dy: 10, d: .5 });
    this.run.update(t, P.r1 - .1, P.r2 - .1, 1.1, P.d);
    this.q.forEach((r, i) => r.update(t, T.p2.q[i] - .2, 1.2));
    pop(this.w60, t, T.p2.w60, { dy: 12, d: .5 }); pop(this.mag, t, T.p2.mag, { dy: 12, d: .5 });
    pop(this.rd, t, T.round, { dy: 12, s: .9, back: true, d: .5 });
  },
});
})();
