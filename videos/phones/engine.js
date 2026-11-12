/* Engine for the phones comparison video: timeline anchors, scenes, captions, HUD, small animation helpers.
   Everything on screen is a pure function of the time t (window.renderFrame(t)). */
(() => {
const V = window.V = { missing: [], scenes: [], CUES: [] };
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
V.clamp = clamp;
V.prog = (t, t0, d) => clamp((t - t0) / d);
V.easeOut = x => 1 - Math.pow(1 - x, 3);
V.easeOut5 = x => 1 - Math.pow(1 - x, 5);
V.easeIn = x => x * x * x;
V.easeInOut = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
V.easeOutBack = x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
V.lerp = (a, b, x) => a + (b - a) * x;
V.$ = id => document.getElementById(id);
V.fmt = (n, d = 0) => Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

V.css = (text) => { const s = document.createElement('style'); s.textContent = text; document.head.appendChild(s); };
V.mk = (html) => { const d = document.createElement('div'); d.innerHTML = html.trim(); return d.firstElementChild; };

/* ---------- anchors: time of a spoken word (or phrase) inside a scene ---------- */
const normTok = s => s.toLowerCase().replace(/[^a-z0-9]/g, '');
V.W = (sceneId, phrase, nth = 0, off = 0) => {
  const sc = V.S[sceneId];
  if (!sc) { V.missing.push(sceneId + ':' + phrase); return 0; }
  const want = phrase.split(/\s+/).map(normTok).filter(Boolean);
  const have = sc.words.map(w => normTok(w.w));
  let seen = 0;
  for (let i = 0; i + want.length <= have.length; i++) {
    let ok = true;
    for (let k = 0; k < want.length; k++) if (have[i + k] !== want[k]) { ok = false; break; }
    if (ok) { if (seen === nth) return sc.words[i].s + off; seen++; }
  }
  V.missing.push(sceneId + ':' + phrase + '#' + nth);
  return sc.speech_start + (sc.speech_end - sc.speech_start) * .5 + off;
};
/* end time of the last word of a phrase */
V.WE = (sceneId, phrase, nth = 0, off = 0) => {
  const sc = V.S[sceneId];
  const want = phrase.split(/\s+/).map(normTok).filter(Boolean);
  const have = sc.words.map(w => normTok(w.w));
  let seen = 0;
  for (let i = 0; i + want.length <= have.length; i++) {
    let ok = true;
    for (let k = 0; k < want.length; k++) if (have[i + k] !== want[k]) { ok = false; break; }
    if (ok) { if (seen === nth) return sc.words[i + want.length - 1].e + off; seen++; }
  }
  V.missing.push(sceneId + ':' + phrase + '#' + nth + ' (end)');
  return sc.speech_end;
};
V.cue = (t, k, id) => V.CUES.push({ t: Math.max(0, t), k, id: id || '' });

/* ---------- small animation helpers ---------- */
/* fade/slide one element in at t0 (and optionally out at t1); returns the eased progress */
V.pop = (el, t, t0, o = {}) => {
  const d = o.d === undefined ? .55 : o.d, dy = o.dy === undefined ? 26 : o.dy, dx = o.dx || 0, s0 = o.s === undefined ? 1 : o.s;
  const x = V.prog(t, t0, d), e = o.back ? V.easeOutBack(x) : V.easeOut(x);
  let op = clamp(x * 1.8) * (o.o === undefined ? 1 : o.o);
  if (o.t1 !== undefined) op *= 1 - V.easeIn(V.prog(t, o.t1, o.d1 || .35));
  el.style.opacity = op.toFixed(3);
  const sc = V.lerp(s0, 1, clamp(e, 0, 1.15));
  el.style.transform = `translate(${((1 - e) * dx).toFixed(2)}px,${((1 - e) * dy).toFixed(2)}px) scale(${sc.toFixed(4)})`;
  return e;
};
V.show = (el, on) => { el.style.opacity = on ? 1 : 0; };
V.setText = (el, s) => { if (el.textContent !== s) el.textContent = s; };
/* count a number up (or down) between t0 and t0+d */
V.count = (el, to, t, t0, d, o = {}) => {
  const e = V.easeOut(V.prog(t, t0, d)), v = V.lerp(o.from || 0, to, e);
  V.setText(el, (o.pre || '') + V.fmt(v, o.dec || 0) + (o.suf || ''));
  return e;
};
/* grow a bar (scaleX from the left) */
V.grow = (el, frac, t, t0, d) => { const e = V.easeOut5(V.prog(t, t0, d)); el.style.transform = `scaleX(${(clamp(frac) * e).toFixed(4)})`; return e; };

/* ---------- pair of horizontal bars (iPhone vs Galaxy) ---------- */
V.css(`
.bp { position:absolute; }
.bp-l { font: 600 25px JBM, monospace; letter-spacing:.14em; text-transform:uppercase; color:var(--mut); margin-bottom:16px; }
.bp-r { display:flex; align-items:center; height:72px; }
.bp-n { width:150px; font-weight:700; font-size:30px; }
.bp-t { position:relative; flex:1; height:44px; border-radius:12px; background:rgba(255,255,255,.06); overflow:hidden; }
.bp-f { position:absolute; left:0; top:0; bottom:0; width:100%; transform-origin:0 50%; transform:scaleX(0); border-radius:12px; }
.bp-v { width:230px; text-align:right; font: 700 42px JBM, monospace; font-variant-numeric:tabular-nums; }
.bp-d { position:absolute; right:0; top:-6px; padding:6px 18px; border-radius:30px; font: 800 34px InterV, sans-serif; border:2px solid; background:rgba(4,9,11,.8); }
.n1,.v1 { color:var(--c1); } .n2,.v2 { color:var(--c2); }
.f1 { background:linear-gradient(90deg,rgba(0,245,255,.55),#00F5FF); }
.f2 { background:linear-gradient(90deg,rgba(0,255,135,.55),#00FF87); }
`);
V.barPair = (o) => {
  const el = V.mk(`<div class="bp" style="left:${o.x}px;top:${o.y}px;width:${o.w}px">
    <div class="bp-l">${o.label}</div>
    <div class="bp-r"><div class="bp-n n1">iPhone</div><div class="bp-t"><div class="bp-f f1"></div></div><div class="bp-v v1">0</div></div>
    <div class="bp-r"><div class="bp-n n2">Galaxy</div><div class="bp-t"><div class="bp-f f2"></div></div><div class="bp-v v2">0</div></div>
    ${o.delta ? `<div class="bp-d" style="color:${o.delta.c};border-color:${o.delta.c};opacity:0">${o.delta.t}</div>` : ''}
  </div>`);
  const [l, r1, r2] = [el.querySelector('.bp-l'), el.children[1], el.children[2]];
  const f = [r1.querySelector('.bp-f'), r2.querySelector('.bp-f')], v = [r1.querySelector('.bp-v'), r2.querySelector('.bp-v')];
  const dEl = el.querySelector('.bp-d');
  const max = o.max || Math.max(o.a, o.b) * 1.08;
  const fmt = o.fmt || (x => V.fmt(x, o.dec || 0));
  return {
    el,
    /* tA / tB: when the iPhone / Galaxy bar starts; tDelta: when the +x% chip appears */
    update(t, tA, tB, d = 1.0, tDelta) {
      if (tB === undefined) tB = tA + (o.gap === undefined ? .18 : o.gap);
      const pa = V.easeOut5(V.prog(t, tA, d)), pb = V.easeOut5(V.prog(t, tB, d));
      el.style.opacity = clamp((t - Math.min(tA, tB) + .3) / .3).toFixed(3);
      f[0].style.transform = `scaleX(${(clamp(o.a / max) * pa).toFixed(4)})`;
      f[1].style.transform = `scaleX(${(clamp(o.b / max) * pb).toFixed(4)})`;
      V.setText(v[0], t < tA - .05 ? '' : (o.pre || '') + (o.time ? o.time(o.a * pa) : fmt(o.a * pa)) + (o.suf || ''));
      V.setText(v[1], t < tB - .05 ? '' : (o.pre || '') + (o.time ? o.time(o.b * pb) : fmt(o.b * pb)) + (o.suf || ''));
      if (dEl && tDelta !== undefined) V.pop(dEl, t, tDelta, { dy: 10, s: .85, back: true, d: .45 });
    },
  };
};

/* ---------- ring gauge ---------- */
V.ring = (o) => {
  const R = o.r, C = 2 * Math.PI * R, sw = o.sw || 22;
  const el = V.mk(`<div style="position:absolute;left:${o.x - R - sw}px;top:${o.y - R - sw}px;width:${2 * (R + sw)}px;height:${2 * (R + sw)}px">
    <svg width="${2 * (R + sw)}" height="${2 * (R + sw)}" viewBox="0 0 ${2 * (R + sw)} ${2 * (R + sw)}" style="position:absolute;left:0;top:0">
      <circle cx="${R + sw}" cy="${R + sw}" r="${R}" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="${sw}"/>
      <circle class="arc" cx="${R + sw}" cy="${R + sw}" r="${R}" fill="none" stroke="${o.color}" stroke-width="${sw}" stroke-linecap="round" stroke-dasharray="${C}" stroke-dashoffset="${C}" transform="rotate(-90 ${R + sw} ${R + sw})"/>
    </svg>
    <div class="rv" style="position:absolute;left:0;right:0;top:50%;margin-top:-${(o.vs || 64) * .62}px;text-align:center;font:800 ${o.vs || 64}px InterV,sans-serif;color:${o.color};font-variant-numeric:tabular-nums">0</div>
    <div class="rl" style="position:absolute;left:0;right:0;top:50%;margin-top:${(o.vs || 64) * .42}px;text-align:center;font:600 24px JBM,monospace;letter-spacing:.12em;color:var(--mut)">${o.label || ''}</div>
  </div>`);
  const arc = el.querySelector('.arc'), rv = el.querySelector('.rv');
  return {
    el,
    update(t, t0, d = 1.4) {
      const e = V.easeOut5(V.prog(t, t0, d));
      el.style.opacity = clamp((t - t0 + .2) / .3).toFixed(3);
      arc.setAttribute('stroke-dashoffset', (C * (1 - o.frac * e)).toFixed(2));
      V.setText(rv, V.fmt(o.value * e, o.dec || 0) + (o.suf || ''));
    },
  };
};

/* ---------- scenes ---------- */
V.add = (id, def) => { V.scenes.push(Object.assign({ id }, def)); };
/* a set of phases inside one scene: only one is shown at a time (soft cross-fade) */
V.phaseOpacity = (t, t0, t1, fin = .4, fout = .35) => {
  const a = V.easeOut(V.prog(t, t0, fin));
  const b = t1 === undefined ? 0 : V.easeIn(V.prog(t, t1 - fout, fout));
  return clamp(Math.min(a, 1 - b));
};

/* Tom's Guide round winner chip (bottom right of the content area) */
V.css(`
.round { position:absolute; right:90px; top:912px; display:flex; align-items:center; gap:14px; padding:10px 22px 10px 16px; border-radius:40px; border:2px solid; background:rgba(4,9,11,.85); font: 700 26px InterV, sans-serif; }
.round i { font: 600 20px JBM, monospace; letter-spacing:.14em; color:var(--mut); font-style:normal; }
`);
V.round = (who, label) => {
  const c = who === 'iphone' ? 'var(--c1)' : who === 'galaxy' ? 'var(--c2)' : '#B8C4C8';
  const name = who === 'iphone' ? 'iPhone' : who === 'galaxy' ? 'Galaxy' : 'Tie';
  return V.mk(`<div class="round" style="border-color:${c};color:${c};opacity:0"><i>${label || "TOM'S GUIDE ROUND"}</i> ${name}</div>`);
};

/* ---------- real press photos and clips: shown unaltered; every scene that uses one names its source in the source line ---------- */
V.css(`
.mc { position:absolute; overflow:hidden; border-radius:14px; border:2px solid rgba(255,255,255,.22); background:#000; box-sizing:border-box; opacity:0; }
.mc img { position:absolute; left:0; top:0; width:100%; height:100%; display:block; object-fit:contain; }
`);
V.preload = []; V.pending = [];
const MURL = 'http://app.local/media/';
/* o: { still:'file.jpg' } or { clip:'folder', n:frames, fps }; x, y, color; and either w or h together with ar (width / height) */
V.media = (o) => {
  const w = o.w || o.h * o.ar, h = o.h || o.w / o.ar;
  const el = V.mk(`<div class="mc" style="left:${o.x}px;top:${o.y}px;width:${w}px;height:${h}px;${o.color ? 'border-color:' + o.color : ''}"><img alt=""></div>`);
  const img = el.firstElementChild, m = { el, img, w, h, cur: -1 };
  const fail = (what) => V.missing.push('media ' + what);
  if (o.still) { img.src = MURL + o.still; V.preload.push(img.decode().catch(() => fail(o.still))); }
  else {
    /* load the frame for time t: the clip starts at t0 and plays from `off` seconds into the file */
    m.at = (t, t0, off = 0) => {
      const n = Math.max(1, Math.min(o.n, Math.floor((t - t0 + off) * (o.fps || 30)) + 1));
      if (n !== m.cur) { m.cur = n; img.src = MURL + o.clip + '/' + String(n).padStart(4, '0') + '.jpg'; V.pending.push(img.decode().catch(() => fail(o.clip + '/' + n))); }
    };
  }
  return m;
};

/* ---------- build everything ---------- */
V.start = async () => {
  V.TL = await (await fetch('http://app.local/timeline.json')).json();
  V.S = Object.fromEntries(V.TL.scenes.map(s => [s.id, s]));
  V.duration = V.TL.duration;
  await Promise.all([document.fonts.load('800 44px InterV'), document.fonts.load('600 24px JBM'), document.fonts.load('700 30px InterV'), document.fonts.load('400 24px InterV'), document.fonts.load('700 40px JBM')]);
  await document.fonts.ready;

  const stage = V.$('stage');
  /* background noise (static dither, same in every frame) */
  const cv = V.$('noise'), cx = cv.getContext('2d');
  const img = cx.createImageData(cv.width, cv.height);
  let seed = 20261111;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  for (let i = 0; i < img.data.length; i += 4) { const v = rnd() < .5 ? 0 : 255; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = rnd() < .5 ? 3 : 0; }
  cx.putImageData(img, 0, 0);

  const sceneRoot = V.$('scenes');
  for (const sc of V.scenes) {
    const ts = V.S[sc.id];
    if (!ts) { V.missing.push('scene ' + sc.id); continue; }
    sc.ts = ts;
    sc.root = document.createElement('div');
    sc.root.className = 'abs sc';
    sc.root.style.display = 'none';
    sceneRoot.appendChild(sc.root);
    sc.build(sc.root);
  }
  /* sound cues: a whoosh at every scene change */
  V.TL.scenes.forEach((s, i) => { if (i > 0) V.cue(s.start + .02, 'whoosh', s.id); });
  window.CUES = V.CUES.slice().sort((a, b) => a.t - b.t);

  buildCaptions();
  await Promise.all(V.preload);
  V.pending = []; V.update(0); await Promise.all(V.pending);
  window.sceneReady = true;
};

/* ---------- captions (one line, word highlight) ---------- */
let caps = [];
function buildCaptions() {
  const meas = document.createElement('span');
  meas.style.cssText = 'position:absolute;visibility:hidden;left:-9999px;top:0;white-space:pre;font-family:InterV,sans-serif;font-weight:800;font-size:44px;';
  document.body.appendChild(meas);
  const wid = w => { meas.textContent = w; return meas.getBoundingClientRect().width + 14; };
  const MAX = 1500;
  const root = V.$('caps');
  for (const sc of V.TL.scenes) {
    const words = sc.words;
    const chunks = [];
    let cur = [], w = 0;
    const flush = () => { if (cur.length) { chunks.push(cur); cur = []; w = 0; } };
    words.forEach((wd, i) => {
      const ww = wid(wd.w);
      if (cur.length && w + ww > MAX) flush();
      cur.push(i); w += ww;
      const last = /[.?!]$/.test(wd.w), soft = /[,;:]$/.test(wd.w);
      if (last || (soft && w > MAX * .55)) flush();
    });
    flush();
    for (let i = 1; i < chunks.length; i++) {          // no tiny orphans
      if (chunks[i].length <= 2) {
        const merged = chunks[i - 1].concat(chunks[i]);
        if (merged.reduce((a, k) => a + wid(words[k].w), 0) <= MAX) { chunks[i - 1] = merged; chunks.splice(i, 1); i--; }
      }
    }
    chunks.forEach((idx, n) => {
      const el = document.createElement('div');
      el.className = 'cap';
      el.innerHTML = idx.map(k => `<span class="cw">${words[k].w}</span>`).join('');
      root.appendChild(el);
      const nextStart = n + 1 < chunks.length ? words[chunks[n + 1][0]].s : sc.end;
      caps.push({ el, spans: Array.from(el.children), words: idx.map(k => words[k]),
        t0: words[idx[0]].s - .06, t1: Math.min(words[idx[idx.length - 1]].e + .35, nextStart - .02 > words[idx[idx.length - 1]].e ? nextStart - .02 : words[idx[idx.length - 1]].e + .12) });
    });
  }
  meas.remove();
}

/* ---------- the frame ---------- */
const CHAPTERS = { hook: '', meet: '01 · THE PHONES', method: '02 · HOW I COMPARED', design: '03 · DESIGN & BUILD', display: '04 · SCREEN', perf: '05 · PERFORMANCE',
  camera: '06 · CAMERAS', battery: '07 · BATTERY & CHARGING', software: '08 · SOFTWARE & AI', price: '09 · PRICE', iphone_bad: '10 · PROBLEMS · IPHONE',
  galaxy_bad: '11 · PROBLEMS · GALAXY', score: '12 · SCOREBOARD', verdict: '13 · VERDICT' };

V.update = (t) => {
  let active = null;
  for (const sc of V.scenes) {
    if (!sc.ts) continue;
    const on = t >= sc.ts.start - .001 && t < sc.ts.end + .001;
    const isLast = sc.ts.end >= V.duration - .01;
    if (on) {
      const a = Math.min(V.easeOut(V.prog(t, sc.ts.start, .45)), isLast ? 1 : 1 - V.easeIn(V.prog(t, sc.ts.end - .32, .32)));
      sc.root.style.display = 'block';
      sc.root.style.opacity = (t < .3 ? 1 : a).toFixed(3);
      sc.update(t, t - sc.ts.start);
      active = sc;
    } else sc.root.style.display = 'none';
  }
  /* HUD */
  const hud = V.$('hudR'), chap = active ? CHAPTERS[active.id] : '';
  V.setText(hud, chap);
  V.$('prog').style.transform = `scaleX(${clamp(t / V.duration).toFixed(5)})`;
  const hudOn = !active ? 0 : active.id === 'hook' ? 0 : V.easeOut(V.prog(t, active.ts.start, .6));
  V.$('hud').style.opacity = hudOn.toFixed(3);
  /* orbs drift slowly */
  V.$('orb1').style.transform = `translate(${(Math.sin(t / 9) * 60).toFixed(1)}px,${(Math.cos(t / 11) * 40).toFixed(1)}px)`;
  V.$('orb2').style.transform = `translate(${(Math.cos(t / 10) * 70).toFixed(1)}px,${(Math.sin(t / 8) * 50).toFixed(1)}px)`;
  /* captions */
  for (const c of caps) {
    const on = t >= c.t0 && t < c.t1;
    c.el.style.display = on ? 'flex' : 'none';
    if (!on) continue;
    c.spans.forEach((sp, i) => {
      const w = c.words[i], started = t >= w.s - .02, nextS = i + 1 < c.words.length ? c.words[i + 1].s : c.t1;
      const cur = started && t < nextS - .02;
      sp.className = 'cw' + (cur ? ' cur' : started ? ' done' : '');
    });
  }
};
/* returns a promise: the picture is ready once every clip frame needed at time t has been decoded */
window.renderFrame = (t) => { V.pending = []; V.update(t); return Promise.all(V.pending).then(() => true); };
})();
