/* Scenes 1-3: hook, meet, method */
(() => {
const { W, WE, pop, prog, easeOut, easeIn, clamp, count, mk, css, cue } = V;

/* ===================================================== hook */
css(`
.hk-card { position:absolute; top:58px; width:800px; height:616px; border-radius:34px; border:2px solid; box-sizing:border-box; background:linear-gradient(160deg, rgba(255,255,255,.075), rgba(255,255,255,.02)); }
.hk-tag { position:absolute; left:44px; top:386px; font:700 22px JBM, monospace; letter-spacing:.2em; }
.hk-name { position:absolute; left:44px; top:418px; font-weight:800; font-size:56px; letter-spacing:-.025em; line-height:1.05; color:var(--ink); white-space:nowrap; }
.hk-price { position:absolute; left:44px; top:488px; font:800 92px InterV, sans-serif; letter-spacing:-.035em; line-height:1; font-variant-numeric:tabular-nums; opacity:0; }
.hk-sub { position:absolute; right:44px; top:530px; text-align:right; font:600 22px JBM, monospace; letter-spacing:.1em; color:var(--mut); line-height:1.4; }
.hk-vs { position:absolute; left:895px; top:190px; width:130px; height:130px; border-radius:50%; background:#04090B; border:2px solid rgba(255,255,255,.28); display:flex; align-items:center; justify-content:center; font:800 46px InterV, sans-serif; letter-spacing:.02em; color:#fff; }
.hk-q { position:absolute; left:0; width:1920px; top:708px; text-align:center; font-weight:800; font-size:84px; letter-spacing:-.03em; line-height:1.05; }
.hk-q em { font-style:normal; background:linear-gradient(90deg,#00F5FF,#00FF87); -webkit-background-clip:text; background-clip:text; color:transparent; }
.hk-chips { position:absolute; left:0; width:1920px; top:842px; display:flex; justify-content:center; gap:22px; }
.hk-chip { font:700 27px JBM, monospace; letter-spacing:.12em; padding:14px 26px; border-radius:16px; border:2px solid rgba(255,255,255,.22); background:rgba(255,255,255,.05); color:var(--ink); }
.hk-chip.w { border-color:rgba(255,181,71,.6); color:var(--warn); }
.hk-clock { font:800 30px JBM, monospace; letter-spacing:.1em; padding:14px 26px; border-radius:16px; background:linear-gradient(90deg,#00F5FF,#00FF87); color:#04090B; }
`);
V.add('hook', {
  build(root) {
    root.innerHTML = `
      <div class="hk-card" id="hk1" style="left:100px;border-color:rgba(0,245,255,.7)">
        <div class="hk-tag c1">APPLE · ON SALE SEP 18</div><div class="hk-name">iPhone 18 Pro Max</div>
        <div class="hk-price c1" id="hkp1">$0</div><div class="hk-sub">US LAUNCH PRICE<br>256 GB</div></div>
      <div class="hk-vs" id="hkvs">VS</div>
      <div class="hk-card" id="hk2" style="left:1020px;border-color:rgba(0,255,135,.7)">
        <div class="hk-tag c2">SAMSUNG · ON SALE MAR 11</div><div class="hk-name">Galaxy S26 Ultra</div>
        <div class="hk-price c2" id="hkp2">$0</div><div class="hk-sub">US LAUNCH PRICE<br>256 GB</div></div>
      <div class="hk-q" id="hkq">Which one is <em>actually better?</em></div>
      <div class="hk-chips"><div class="hk-chip" id="hc1">OFFICIAL SPECS</div><div class="hk-chip" id="hc2">LAB TESTS</div><div class="hk-chip w" id="hc3">OWNER REPORTS</div><div class="hk-clock" id="hc4">ALL IN 10:00</div></div>
      <div class="src" style="left:80px;top:918px;font-size:19px">PHOTOS: APPLE NEWSROOM · SAMSUNG NEWSROOM (PRESS IMAGES, SHOWN UNCHANGED)</div>`;
    const $ = id => root.querySelector('#' + id);
    // real press photos, shown whole and unchanged
    const pa = V.media({ still: 'apple_colors.jpg', h: 340, ar: 3840 / 2743, x: 0, y: 22, color: 'rgba(0,245,255,.55)' });
    const pb = V.media({ still: 'samsung_family.jpg', h: 340, ar: 4 / 3, x: 0, y: 22, color: 'rgba(0,255,135,.55)' });
    pa.el.style.left = (800 - pa.w) / 2 - 2 + 'px'; pb.el.style.left = (800 - pb.w) / 2 - 2 + 'px'; pa.el.style.opacity = pb.el.style.opacity = 1;
    $('hk1').append(pa.el); $('hk2').append(pb.el);
    this.e = { c1: $('hk1'), c2: $('hk2'), vs: $('hkvs'), p1: $('hkp1'), p2: $('hkp2'), q: $('hkq'), ch: [$('hc1'), $('hc2'), $('hc3'), $('hc4')], src: root.querySelector('.src') };
    this.T = { c1: W('hook', 'iPhone') - .15, c2: W('hook', 'Galaxy') - .15, price: W('hook', 'start') - .1, q: W('hook', 'So') - .05,
      ch: [W('hook', 'official'), W('hook', 'lab'), W('hook', 'owners'), W('hook', 'ten') - .3] };
    cue(this.T.c1, 'pop', 'c1'); cue(this.T.c2, 'pop', 'c2'); cue(this.T.price + .2, 'impact', 'price'); cue(this.T.q, 'pop', 'q');
    this.T.ch.forEach((t, i) => cue(t, i === 3 ? 'stamp' : 'tick', 'chip' + i));
  },
  update(t) {
    const { e, T } = this;
    pop(e.c1, t, T.c1, { dx: -70, dy: 0, d: .8 });
    pop(e.c2, t, T.c2, { dx: 70, dy: 0, d: .8 });
    pop(e.vs, t, T.c2, { s: .5, back: true, d: .6, dy: 0 });
    e.p1.style.opacity = e.p2.style.opacity = t >= T.price - .02 ? 1 : 0;
    count(e.p1, 1299, t, T.price, 1.5, { pre: '$' });
    count(e.p2, 1299.99, t, T.price + .12, 1.5, { pre: '$', dec: 2 });
    pop(e.q, t, T.q, { dy: 34, d: .7 });
    e.ch.forEach((c, i) => pop(c, t, T.ch[i], { dy: 18, s: .9, back: true, d: .5 }));
    pop(e.src, t, T.c2, { dy: 0 });
  },
});

/* ===================================================== meet */
const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
css(`
.mt-card { position:absolute; top:236px; width:800px; height:372px; border-radius:30px; border:2px solid; box-sizing:border-box; padding:28px 44px; background:linear-gradient(160deg, rgba(255,255,255,.07), rgba(255,255,255,.02)); }
.mt-tag { font:700 22px JBM, monospace; letter-spacing:.2em; }
.mt-name { font-weight:800; font-size:62px; letter-spacing:-.025em; line-height:1.05; margin-top:8px; }
.mt-row { position:absolute; left:44px; right:30px; height:60px; display:flex; align-items:center; border-top:1.5px solid rgba(255,255,255,.1); }
.mt-row b { width:170px; font:600 22px JBM, monospace; letter-spacing:.14em; color:var(--mut); }
.mt-row span { font-weight:700; font-size:35px; white-space:nowrap; }
.tl-line { position:absolute; left:160px; width:1600px; top:812px; height:4px; border-radius:2px; background:rgba(255,255,255,.18); }
.tl-tick { position:absolute; top:840px; font:600 20px JBM, monospace; letter-spacing:.1em; color:var(--dim); transform:translateX(-50%); }
.tl-dot { position:absolute; width:26px; height:26px; border-radius:50%; top:802px; margin-left:-13px; }
.tl-lab { position:absolute; top:878px; font:800 30px InterV, sans-serif; white-space:nowrap; }
.tl-lab small { display:block; font:600 21px JBM, monospace; letter-spacing:.12em; color:var(--mut); margin-top:2px; }
.tl-br { position:absolute; top:746px; height:34px; border:3px solid rgba(255,255,255,.6); border-bottom:none; border-radius:10px 10px 0 0; }
.tl-brl { position:absolute; top:706px; text-align:center; font:800 36px InterV, sans-serif; letter-spacing:.02em; white-space:nowrap; transform:translateX(-50%); }
.fold { position:absolute; right:100px; top:662px; font:700 23px JBM, monospace; letter-spacing:.12em; padding:10px 18px; border-radius:12px; border:2px dashed rgba(255,255,255,.32); color:var(--mut); }
`);
const xOf = d => 160 + d / 365 * 1600;
V.add('meet', {
  build(root) {
    const card = (cls, x, color, tag, name, rows) => `<div class="mt-card ${cls}" style="left:${x}px;border-color:${color}"><div class="mt-tag" style="color:${color}">${tag}</div><div class="mt-name" style="color:${color}">${name}</div>${rows.map((r, i) => `<div class="mt-row r${i}" style="top:${138 + i * 70}px"><b>${r[0]}</b><span>${r[1]}</span></div>`).join('')}</div>`;
    root.innerHTML = `<div class="kick">THE CONTENDERS</div><div class="h1">Two flagships, <span class="mut">six months apart</span></div>` +
      card('a', 100, '#00F5FF', 'APPLE', 'iPhone 18 Pro Max', [['ON SALE', 'Sep 18, 2026'], ['CHIP', 'A20 Pro'], ['SCREEN', '6.9″ OLED · up to 120 Hz']]) +
      card('b', 1020, '#00FF87', 'SAMSUNG', 'Galaxy S26 Ultra', [['ON SALE', 'Mar 11, 2026'], ['CHIP', 'Snapdragon 8 Elite Gen 5'], ['SCREEN', '6.9″ AMOLED · up to 120 Hz']]) +
      `<div class="tl-line"></div>` + MONTHS.map((m, i) => `<div class="tl-tick" style="left:${xOf(i * 30.4 + 15)}px">${m}</div>`).join('') +
      `<div class="tl-dot" id="tdB" style="left:${xOf(70)}px;background:#00FF87"></div><div class="tl-dot" id="tdA" style="left:${xOf(261)}px;background:#00F5FF"></div>
       <div class="tl-lab c2" id="tlB" style="left:${xOf(70) - 13}px">GALAXY S26 ULTRA<small>MAR 11, 2026</small></div>
       <div class="tl-lab c1" id="tlA" style="right:${1920 - xOf(261) - 13}px;text-align:right">IPHONE 18 PRO MAX<small>SEP 18, 2026</small></div>
       <div class="tl-br" id="tlbr" style="left:${xOf(70)}px;width:${xOf(261) - xOf(70)}px"></div><div class="tl-brl" id="tlbl" style="left:${(xOf(70) + xOf(261)) / 2}px">≈ 6 MONTHS</div>
       <div class="fold" id="fold">FOLDABLES: NOT COMPARED</div>`;
    const $ = s => root.querySelector(s);
    this.e = { a: $('.mt-card.a'), b: $('.mt-card.b'), ar: [...root.querySelectorAll('.mt-card.a .mt-row')], br: [...root.querySelectorAll('.mt-card.b .mt-row')],
      dA: $('#tdA'), dB: $('#tdB'), lA: $('#tlA'), lB: $('#tlB'), br2: $('#tlbr'), bl: $('#tlbl'), fold: $('#fold'), kick: $('.kick'), h1: $('.h1') };
    this.T = { a: W('meet', 'iPhone') - .2, aSale: W('meet', 'September'), aChip: W('meet', 'A20'), b: W('meet', 'Galaxy') - .2, bChip: W('meet', 'Snapdragon'), bSale: W('meet', 'March'),
      six: W('meet', 'about six months earlier'), screens: W('meet', '6.9-inch'), fold: W('meet', 'foldables') - .2 };
    const T = this.T;
    [T.a, T.b, T.aSale, T.aChip, T.bChip, T.bSale, T.screens, T.six, T.fold].forEach((x, i) => cue(x, i < 2 ? 'pop' : 'tick', 'm' + i));
  },
  update(t) {
    const { e, T } = this;
    pop(e.kick, t, T.a - .6, {}); pop(e.h1, t, T.a - .5, {});
    pop(e.a, t, T.a, { dx: -60, dy: 0, d: .7 }); pop(e.b, t, T.b, { dx: 60, dy: 0, d: .7 });
    pop(e.ar[0], t, T.aSale, { dy: 14, d: .45 }); pop(e.ar[1], t, T.aChip, { dy: 14, d: .45 }); pop(e.ar[2], t, T.screens, { dy: 14, d: .45 });
    pop(e.br[1], t, T.bChip, { dy: 14, d: .45 }); pop(e.br[0], t, T.bSale, { dy: 14, d: .45 }); pop(e.br[2], t, T.screens + .12, { dy: 14, d: .45 });
    pop(e.dB, t, T.bSale, { dy: 0, s: .2, back: true, d: .5 }); pop(e.lB, t, T.bSale + .1, { dy: 12, d: .5 });
    pop(e.dA, t, T.six + .5, { dy: 0, s: .2, back: true, d: .5 }); pop(e.lA, t, T.six + .6, { dy: 12, d: .5 });
    pop(e.br2, t, T.six + .1, { dy: 0, d: .8 }); pop(e.bl, t, T.six + .35, { dy: 10, d: .6 });
    pop(e.fold, t, T.fold, { dy: 14, d: .5 });
    e.bl.style.transform = 'translateX(-50%) ' + e.bl.style.transform;
  },
});

/* ===================================================== method */
const ICONS = {
  doc: `<svg width="92" height="92" viewBox="0 0 92 92" fill="none" stroke="currentColor" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10h34l16 16v56H22z"/><path d="M56 10v16h16"/><path d="M32 44h30M32 56h30M32 68h20"/></svg>`,
  chart: `<svg width="92" height="92" viewBox="0 0 92 92" fill="none" stroke="currentColor" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 80h70"/><rect x="20" y="46" width="14" height="34" rx="2"/><rect x="40" y="26" width="14" height="54" rx="2"/><rect x="60" y="38" width="14" height="42" rx="2"/></svg>`,
  chat: `<svg width="92" height="92" viewBox="0 0 92 92" fill="none" stroke="currentColor" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 18h68v46H44L26 80V64H12z"/><path d="M28 36h36M28 48h22"/></svg>`,
};
css(`
.me-p { position:absolute; top:226px; width:540px; height:390px; border-radius:28px; border:2px solid rgba(255,255,255,.16); background:rgba(255,255,255,.045); box-sizing:border-box; padding:34px 38px; }
.me-p .n { font:700 22px JBM, monospace; letter-spacing:.2em; color:var(--mut); margin-top:14px; }
.me-p h3 { margin:6px 0 14px; font-weight:800; font-size:44px; letter-spacing:-.02em; line-height:1.05; }
.me-p p { margin:0; font-weight:500; font-size:28px; line-height:1.3; color:rgba(242,251,255,.82); }
.me-p.warn { border-color:rgba(255,181,71,.55); } .me-p.warn svg, .me-p.warn h3 { color:var(--warn); }
.me-note { position:absolute; left:0; width:1920px; top:636px; text-align:center; font:600 23px JBM, monospace; letter-spacing:.14em; color:var(--mut); }
.me-ch { position:absolute; left:0; width:1920px; top:762px; display:flex; justify-content:center; gap:14px; }
.me-chl { position:absolute; left:100px; top:706px; font:600 22px JBM, monospace; letter-spacing:.2em; color:var(--mut); }
.me-c { font:800 30px InterV, sans-serif; padding:14px 22px; border-radius:16px; border:2px solid rgba(255,255,255,.22); background:rgba(255,255,255,.05); white-space:nowrap; }
.me-c.bad { border-color:rgba(255,107,107,.6); color:var(--bad); }
`);
V.add('method', {
  build(root) {
    const panel = (x, ico, n, title, body, cls = '') => `<div class="me-p ${cls}" style="left:${x}px">${ICONS[ico]}<div class="n">${n}</div><h3>${title}</h3><p>${body}</p></div>`;
    const chips = ['DESIGN', 'SCREEN', 'SPEED', 'CAMERAS', 'BATTERY', 'SOFTWARE', 'PRICE', 'PROBLEMS'];
    root.innerHTML = `<div class="kick">METHOD</div><div class="h1">Three kinds of evidence, <span class="mut">kept apart</span></div>` +
      panel(100, 'doc', '1 · OFFICIAL', 'Official specs', 'Apple and Samsung spec pages. These are claims.') +
      panel(690, 'chart', '2 · MEASURED', 'Lab tests', "Tom's Guide, DXOMARK and Android Central. These are measurements.") +
      panel(1280, 'chat', '3 · REPORTED', 'Owner reports', 'Labelled as reports, not facts, unless the company confirmed them.', 'warn') +
      `<div class="me-note" id="mnote">EVERY SOURCE IS LISTED IN THE DESCRIPTION</div><div class="me-chl" id="mchl">WHAT WE WILL COVER</div>` +
      `<div class="me-ch">${chips.map((c, i) => `<div class="me-c${i === 7 ? ' bad' : ''}" id="mc${i}">${c}</div>`).join('')}</div>`;
    const $ = s => root.querySelector(s);
    this.e = { kick: $('.kick'), h1: $('.h1'), p: [...root.querySelectorAll('.me-p')], note: $('#mnote'), chl: $('#mchl'), c: chips.map((_, i) => $('#mc' + i)) };
    const k = ['design', 'screen', 'speed', 'cameras', 'battery', 'software', 'price', 'problems'];
    this.T = { p: [W('method', 'First') - .1, W('method', 'Second') - .1, W('method', 'Third') - .1], note: W('method', 'Every'), c: k.map(w => W('method', w)) };
    this.T.p.forEach((x, i) => cue(x, 'pop', 'p' + i)); this.T.c.forEach((x, i) => cue(x, 'tick', 'c' + i));
  },
  update(t) {
    const { e, T } = this;
    pop(e.kick, t, this.ts.start + .25, {}); pop(e.h1, t, this.ts.start + .4, {});
    e.p.forEach((p, i) => pop(p, t, T.p[i], { dy: 40, d: .65 }));
    pop(e.note, t, T.note, { dy: 10, d: .5 });
    pop(e.chl, t, T.c[0] - .5, { dy: 10, d: .5 });
    e.c.forEach((c, i) => pop(c, t, T.c[i] - .05, { dy: 20, s: .88, back: true, d: .5 }));
  },
});
})();
