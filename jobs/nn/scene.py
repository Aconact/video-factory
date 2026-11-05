"""Hero shot: four tokens go in, a pulse of light climbs through the layers, one word comes out (3.9 s, 1080x1920, 30 fps).

The words are the real ones from the model run in videos/next-word/data.json (tokens in, most likely token out).
Built the way a Blender artist would: glass tiles with emissive type, a layered network of glowing nodes and edges,
photons flying along the edges, a keyframed camera (Bezier ease, pull-back with rack focus), Cycles with motion blur,
fog glow and a vignette in the compositor.

Environment (same as the other jobs):  FRAMES  RES_PERCENT  SAMPLES  OUT_DIR   (optional: DURATION, BORDER)
"""
import json
import math
import os
import random
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools"))
from blender_lib import (CYAN, GREEN, lin, mat, bump, box, plane, sphere, curve, text3d, camera, area, post,  # noqa: E402
                         principled, key_loc, set_interp, start)
from fastq import apply_recipe  # noqa: E402

FPS = 30
DURATION = float(os.environ.get("DURATION", "3.9"))
N = int(round(DURATION * FPS))
PCT = int(os.environ.get("RES_PERCENT", "50"))
SAMPLES = int(os.environ.get("SAMPLES", "32"))
OUT_DIR = os.environ.get("OUT_DIR", "out/frames")
FRAMES = [int(x) for x in os.environ.get("FRAMES", "1").split(",") if x.strip()]

DATA = json.load(open(os.path.join(REPO, "videos", "next-word", "data.json"), encoding="utf-8"))
TOKENS = [t["text"].strip() for t in DATA["tokens"]]          # My favorite color is
ANSWER = DATA["next"]["top"][0]["text"].strip()               # blue


def F(t):
    """seconds -> frame number"""
    return 1 + int(round(t * FPS))


random.seed(8)
sc = start(samples=SAMPLES, bg=(0.0012, 0.0025, 0.0035), exposure=0.2, frames=(1, N), clamp=8.0, motion_blur=True)
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.render.resolution_percentage = PCT


def key_emit(m, pairs):
    sock = principled(m).inputs["Emission Strength"]
    for f, v in pairs:
        sock.default_value = v
        sock.keyframe_insert("default_value", frame=f)


# ------------------------------------------------------------------ layout (Z is up, the camera looks along +Y)
ZT = 0.0                                   # token tiles
LAYER_Z = [1.15, 2.2, 3.25, 4.3]
LAYER_N = [5, 6, 6, 5]
LAYER_DX = [0.78, 0.66, 0.66, 0.78]
Z_OUT = 5.25
Z_WORD = 6.45
T_TOK = 0.45                               # seconds: tiles light up
T_LAYER = [0.95, 1.45, 1.95, 2.45]         # pulse reaches each layer
T_OUT = 2.85                               # output node
T_WORD = 3.0                               # the answer appears

layers = []
for n, dx, z in zip(LAYER_N, LAYER_DX, LAYER_Z):
    layers.append([((i - (n - 1) / 2) * dx, random.uniform(-0.35, 0.35), z) for i in range(n)])
out_pt = (0.0, 0.0, Z_OUT)
tile_x = [-2.1, -0.7, 0.7, 2.1]
tok_pts = [(x, 0.0, ZT + 0.3) for x in tile_x]

# ------------------------------------------------------------------ edges (one material set per gap, so the pulse can light them)
CLS_E = [(0.0075, 0.55), (0.0075, 1.5), (0.012, 3.4)]          # radius, base strength
edge_mats = []
for g in range(5):
    row = []
    for k, (r, s) in enumerate(CLS_E):
        col = lin(GREEN) if k == 2 else ((0.0, 0.9, 0.85) if k == 1 else lin(CYAN))
        row.append(mat("edge_%d_%d" % (g, k), (0, 0, 0), 0.0, 0.5, emit=col, strength=s))
    edge_mats.append(row)


def add_edge(a, b, gap):
    r = random.random()
    k = 2 if r > 0.9 else (1 if r > 0.62 else 0)
    curve("edge", [a, b], CLS_E[k][0], edge_mats[gap][k], res=1, bevel_res=2)


for p in tok_pts:
    for q in layers[0]:
        add_edge(p, q, 0)
for L in range(len(layers) - 1):
    for a in layers[L]:
        for b in layers[L + 1]:
            add_edge(a, b, L + 1)
for a in layers[-1]:
    add_edge(a, out_pt, 4)

# keyframes: every gap lights up just before the layer it feeds
GAP_T = [T_TOK + 0.2] + [T_LAYER[i] + 0.05 for i in range(3)] + [T_OUT - 0.2]
for g in range(5):
    f = F(GAP_T[g])
    for k, (r, s) in enumerate(CLS_E):
        key_emit(edge_mats[g][k], [(1, s), (max(2, f - 10), s), (f - 3, s * 3.2 + 6), (f + 14, s * 1.9), (N, s * 1.9)])

# ------------------------------------------------------------------ nodes
CLS_N = [0.9, 1.7, 2.8, 4.2]
node_mats = []
for L in range(len(layers)):
    col = [lin(CYAN), (0.0, 0.85, 0.85), (0.0, 0.95, 0.65), lin(GREEN)][L]
    row = []
    for k, s in enumerate(CLS_N):
        m = mat("node_%d_%d" % (L, k), (0.01, 0.02, 0.025), 0.0, 0.06, emit=col, strength=s, coat=1.0, coat_rough=0.02)
        f = F(T_LAYER[L])
        key_emit(m, [(1, s), (f - 4, s), (f + 2, s * 3.0 + 9), (f + 22, s * 1.6), (N, s * 1.6)])
        row.append(m)
    node_mats.append(row)
for L, pts in enumerate(layers):
    for p in pts:
        sphere("node", 0.135, p, random.choice(node_mats[L]), seg=24, rings=12)

out_mat = mat("out_node", (0.01, 0.02, 0.025), 0.0, 0.05, emit=lin(GREEN), strength=1.5, coat=1.0, coat_rough=0.02)
key_emit(out_mat, [(1, 1.5), (F(T_OUT) - 4, 1.5), (F(T_OUT) + 3, 30.0), (F(T_OUT) + 30, 7.0), (N, 7.0)])
out_node = sphere("out_node", 0.26, out_pt, out_mat, seg=32, rings=16)

# ------------------------------------------------------------------ token tiles with the real words
glass = mat("tile", (0.02, 0.03, 0.035), 0.0, 0.08, coat=1.0, coat_rough=0.03)
for x, word in zip(tile_x, TOKENS):
    box("tile_" + word, (1.22, 0.08, 0.5), (x, 0, ZT), glass, bevel=0.05, segs=4)
    tm = mat("txt_" + word, (0, 0, 0), 0.0, 0.4, emit=(0.95, 1.0, 0.98), strength=1.0)
    f = F(T_TOK)
    key_emit(tm, [(1, 0.8), (f - 6, 0.8), (f + 3, 9.0), (f + 25, 3.2), (N, 3.2)])
    text3d("tk_" + word, word, 0.25, tm, (x, -0.06, ZT), rot=(math.pi / 2, 0, 0), extrude=0.012, bevel=0.0)

# ------------------------------------------------------------------ photons flying along the edges
ph_mat = mat("photon", (0, 0, 0), 0.0, 0.4, emit=(0.8, 1.0, 0.95), strength=22.0)
for i in range(26):
    start_pt = random.choice(tok_pts)
    path = [start_pt] + [random.choice(l) for l in layers] + [out_pt]
    times = [T_TOK + 0.1] + [T_LAYER[k] - 0.07 for k in range(4)] + [T_OUT - 0.05]
    jit = random.uniform(-0.1, 0.1)
    ph = sphere("photon", random.uniform(0.04, 0.07), path[0], ph_mat, seg=10, rings=6)
    for pt, t in zip(path, times):
        f = F(max(0.0, t + jit))
        ph.location = pt
        ph.keyframe_insert("location", frame=f)
    f0, f1 = F(times[0] + jit), F(times[-1] + jit)
    for f, s in ((1, 0.0), (max(1, f0 - 1), 0.0), (f0 + 1, 1.0), (f1, 1.0), (f1 + 2, 0.0), (N, 0.0)):
        ph.scale = (s, s, s)
        ph.keyframe_insert("scale", frame=f)
    set_interp(ph, "LINEAR")

# ------------------------------------------------------------------ the answer
word_mat = mat("word", (0, 0, 0), 0.0, 0.4, emit=lin(GREEN), strength=0.0)
fw = F(T_WORD)
key_emit(word_mat, [(1, 0.0), (fw - 1, 0.0), (fw + 6, 26.0), (fw + 24, 7.0), (N, 7.0)])
word = text3d("answer", ANSWER, 1.9, word_mat, (0.0, -0.1, Z_WORD), face="Inter-ExtraBold.otf", rot=(math.pi / 2, 0, 0),
              extrude=0.06, bevel=0.012)
for f, s in ((1, 0.01), (fw - 1, 0.01), (fw + 8, 1.12), (fw + 18, 1.0), (N, 1.0)):
    word.scale = (s, s, s)
    word.keyframe_insert("scale", frame=f)

# ------------------------------------------------------------------ floor + dust + lights
fl = mat("floor", (0.003, 0.006, 0.008), 0.0, 0.3)
bump(fl, 30.0, 1.0, 0.03, 3.0, 0.01)
plane("floor", 30.0, 30.0, (0, 6, -1.0), fl)
for i in range(150):
    d = mat("dust%d" % i, (0, 0, 0), 0.0, 0.5, emit=random.choice([lin(CYAN), lin(GREEN), (0.9, 1, 1)]),
            strength=random.uniform(4, 20))
    sphere("dust", random.uniform(0.012, 0.04), (random.uniform(-5, 5), random.uniform(-4, 8), random.uniform(-1.5, 9)),
           d, seg=8, rings=4)
area("key", (-3.5, -6.0, 5.0), (0, 0, 2.5), 3.0, 600, color=(0.9, 0.96, 1.0))
area("rim_g", (4.0, 3.0, 3.0), (0, 0, 2.5), 0.8, 380, color=lin(GREEN), size_y=5.0)
area("rim_c", (-4.5, 3.0, 3.0), (0, 0, 2.5), 0.8, 380, color=lin(CYAN), size_y=5.0)

# ------------------------------------------------------------------ camera: starts low by the tiles, pulls back and rises with the pulse
cam, tgt = camera((0.5, -10.8, 0.15), (0.0, 0.0, 1.5), lens=36, fstop=3.0, focus=10.8)
key_loc(cam, 1, (0.5, -10.8, 0.15))
key_loc(cam, N, (0.1, -15.6, 3.2))
key_loc(tgt, 1, (0.0, 0.0, 1.5))
key_loc(tgt, N, (0.0, 0.0, 3.35))
set_interp(cam, "BEZIER")
set_interp(tgt, "BEZIER")
dof = cam.data.dof
for f, v in ((1, 10.8), (N, 15.6)):
    dof.focus_distance = v
    dof.keyframe_insert("focus_distance", frame=f)

post(glow=-0.15, glow_size=7, threshold=1.8, vignette=0.5, dispersion=0.006)
apply_recipe(sc)

BORDER = os.environ.get("BORDER", "")          # "x0,x1,y0,y1" (0..1, from the bottom left): render only that part
if BORDER:
    bx0, bx1, by0, by1 = [float(v) for v in BORDER.split(",")]
    sc.render.use_border = True
    sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_max_x = bx0, bx1
    sc.render.border_min_y, sc.render.border_max_y = by0, by1

os.makedirs(OUT_DIR, exist_ok=True)
t_start = time.time()
for frame in FRAMES:
    sc.frame_set(frame)
    sc.render.filepath = os.path.join(OUT_DIR, "frame_%04d.png" % frame)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print("RENDERED frame", frame, "t=%.2f" % ((frame - 1) / FPS), "size %d%% samples %d" % (PCT, sc.cycles.samples),
          "took %.1fs" % (time.time() - t0), "elapsed %.1fs" % (time.time() - t_start), flush=True)
print("TOTAL_RENDER_SECONDS", round(time.time() - t_start, 1), flush=True)
