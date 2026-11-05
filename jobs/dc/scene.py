"""Hero shot: a slow push-in through an AI data-center corridor (5 s, 1080x1920, 30 fps).

Procedural rack fronts with blinking LEDs (driven by the frame time), ceiling light strips, glossy floor, thin haze,
a keyframed gimbal-style camera (Bezier ease, slight drift) with depth of field and motion blur.
In the video this clip is played backwards under the closing line, so the film ends by pulling out of the room.

Environment (same as the other jobs):  FRAMES  RES_PERCENT  SAMPLES  OUT_DIR   (optional: DURATION, HAZE)
"""
import math
import os
import random
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
from blender_lib import (GREEN, CYAN, lin, mat, bump, box, plane, camera, post, principled, key_loc,  # noqa: E402
                         set_interp, start)
from fastq import apply_recipe  # noqa: E402

FPS = 30
DURATION = float(os.environ.get("DURATION", "5.0"))
N_FRAMES = int(round(DURATION * FPS))
PCT = int(os.environ.get("RES_PERCENT", "50"))
SAMPLES = int(os.environ.get("SAMPLES", "32"))
OUT_DIR = os.environ.get("OUT_DIR", "out/frames")
FRAMES = [int(x) for x in os.environ.get("FRAMES", "1").split(",") if x.strip()]
HAZE = float(os.environ.get("HAZE", "0.010"))

random.seed(21)
sc = start(samples=SAMPLES, bg=(0.0006, 0.0012, 0.002), exposure=0.0, frames=(1, N_FRAMES), clamp=8.0,
           motion_blur=True)
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.render.resolution_percentage = PCT

CORR_W, RACK_W, RACK_D, RACK_H = 2.4, 0.8, 1.2, 2.3
N = 30
LEN = N * RACK_W
TIME_NODES = []          # one 'time in seconds' value node per rack-front material, set before every frame


def mn(nt, op, a=None, b=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n


def front_mat(name, seed):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = principled(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    rows = mn(nt, "MULTIPLY", mn(nt, "ADD", sep.outputs["Y"], 1.15).outputs[0], 1.0 / 0.0445)
    panel = mn(nt, "GREATER_THAN", mn(nt, "FRACT", rows.outputs[0]).outputs[0], 0.09)
    cmb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(mn(nt, "MULTIPLY", sep.outputs["X"], 22.5).outputs[0], cmb.inputs["X"])
    nt.links.new(rows.outputs[0], cmb.inputs["Y"])
    cmb.inputs["Z"].default_value = seed
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.voronoi_dimensions = "3D"
    vor.feature = "F1"
    vor.inputs["Scale"].default_value = 1.0
    vor.inputs["Randomness"].default_value = 0.0
    nt.links.new(cmb.outputs["Vector"], vor.inputs["Vector"])
    dot = mn(nt, "LESS_THAN", vor.outputs["Distance"], 0.24)
    sc_ = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(vor.outputs["Color"], sc_.inputs["Color"])
    on = mn(nt, "GREATER_THAN", sc_.outputs["Red"], 0.42)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*lin(GREEN), 1)
    e1 = ramp.color_ramp.elements.new(0.50)
    e1.color = (*lin(CYAN), 1)
    e2 = ramp.color_ramp.elements.new(0.84)
    e2.color = (1.0, 0.45, 0.05, 1)
    e3 = ramp.color_ramp.elements.new(0.93)
    e3.color = (0.25, 0.45, 1.0, 1)
    nt.links.new(sc_.outputs["Green"], ramp.inputs["Fac"])
    s1 = mn(nt, "MULTIPLY", dot.outputs[0], on.outputs[0])
    half = mn(nt, "LESS_THAN", sep.outputs["X"], 0.02)
    s2 = mn(nt, "MULTIPLY", mn(nt, "MULTIPLY", s1.outputs[0], panel.outputs[0]).outputs[0], half.outputs[0])
    s3 = mn(nt, "MULTIPLY", s2.outputs[0], 12.0)

    # blinking: about 45 % of the LEDs flicker (each with its own rate and phase), the rest stay on
    tnode = nt.nodes.new("ShaderNodeValue")
    tnode.label = "time_s"
    TIME_NODES.append(tnode)
    rate = mn(nt, "ADD", mn(nt, "MULTIPLY", sc_.outputs["Blue"], 2.4).outputs[0], 0.6)
    phase = mn(nt, "MULTIPLY", sc_.outputs["Red"], 7.0)
    arg = mn(nt, "MULTIPLY", mn(nt, "ADD", mn(nt, "MULTIPLY", tnode.outputs[0], rate.outputs[0]).outputs[0],
                                phase.outputs[0]).outputs[0], 2.0 * math.pi)
    wave = mn(nt, "SINE", arg.outputs[0])
    low = mn(nt, "LESS_THAN", wave.outputs[0], 0.0)
    flick = mn(nt, "GREATER_THAN", sc_.outputs["Blue"], 0.55)
    dim = mn(nt, "MULTIPLY", mn(nt, "MULTIPLY", low.outputs[0], flick.outputs[0]).outputs[0], 0.92)
    gain = mn(nt, "SUBTRACT", 1.0, dim.outputs[0])
    s4 = mn(nt, "MULTIPLY", s3.outputs[0], gain.outputs[0])

    mx = nt.nodes.new("ShaderNodeMixRGB")
    mx.inputs["Color1"].default_value = (0.003, 0.0035, 0.004, 1)
    mx.inputs["Color2"].default_value = (0.055, 0.060, 0.068, 1)
    nt.links.new(panel.outputs[0], mx.inputs["Fac"])
    nt.links.new(mx.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Emission Color"])
    nt.links.new(s4.outputs[0], b.inputs["Emission Strength"])
    b.inputs["Metallic"].default_value = 0.55
    b.inputs["Roughness"].default_value = 0.42
    return m


fronts = [front_mat("front%d" % i, random.uniform(0, 200)) for i in range(6)]
metal = mat("rack_metal", (0.012, 0.013, 0.016), 0.9, 0.38)
floor = mat("floor", (0.012, 0.014, 0.017), 0.0, 0.07)
bump(floor, 28.0, 1.0, 0.03, 3.0, 0.01)
dark = mat("ceiling", (0.008, 0.009, 0.011), 0.0, 0.7)
strip_m = mat("strip", (0, 0, 0), 0.0, 0.5, emit=(0.80, 0.95, 1.0), strength=9.0)
strip_g = mat("strip_g", (0, 0, 0), 0.0, 0.5, emit=lin(GREEN), strength=6.0)

plane("floor", CORR_W / 2 + RACK_D + 2, LEN / 2 + 4, (0, LEN / 2, 0), floor)
plane("ceiling", CORR_W / 2 + RACK_D + 2, LEN / 2 + 4, (0, LEN / 2, RACK_H + 0.9), dark, rot=(math.pi, 0, 0))

for i in range(N):
    y = i * RACK_W + RACK_W / 2
    for side in (-1, 1):
        xc = side * (CORR_W / 2 + RACK_D / 2)
        box("rack", (RACK_D, RACK_W - 0.03, RACK_H), (xc, y, RACK_H / 2), metal, bevel=0.012, segs=2)
        xf = side * (CORR_W / 2) - side * 0.002
        plane("front", (RACK_W - 0.07) / 2, 1.15, (xf, y, RACK_H / 2 + 0.0), random.choice(fronts),
              rot=(math.pi / 2, 0, -side * math.pi / 2))
    if i % 4 == 0:   # cable tray across the corridor
        box("tray", (CORR_W + 0.4, 0.25, 0.05), (0, y, RACK_H + 0.35), metal)

for sx in (-0.55, 0.55):   # long linear lights
    box("lin", (0.045, LEN, 0.025), (sx, LEN / 2, RACK_H + 0.86), strip_m if sx < 0 else strip_g)
box("endwall", (CORR_W + 2 * RACK_D, 0.3, RACK_H + 1.0), (0, LEN + 0.15, (RACK_H + 1.0) / 2), dark)
box("gate", (2.2, 0.05, 2.0), (0, LEN - 0.02, 1.0), mat("gate", (0, 0, 0), 0.0, 0.5, emit=(0.5, 1.0, 0.95), strength=3.2))

if HAZE > 0:
    vm = bpy.data.materials.new("haze")
    vm.use_nodes = True
    nt = vm.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = [n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"][0]
    vs = nt.nodes.new("ShaderNodeVolumeScatter")
    vs.inputs["Density"].default_value = HAZE
    vs.inputs["Anisotropy"].default_value = 0.35
    vs.inputs["Color"].default_value = (0.8, 0.92, 1.0, 1)
    nt.links.new(vs.outputs["Volume"], out.inputs["Volume"])
    hz = box("haze", (CORR_W + 2 * RACK_D - 0.2, LEN + 2, RACK_H + 0.8), (0, LEN / 2, (RACK_H + 0.8) / 2), vm)
    hz.display_type = "WIRE"

# ---- camera: slow push-in along the corridor, a little lateral drift, looking slightly ahead of the move
cam, tgt = camera((0.30, -1.5, 1.50), (-0.05, 12.0, 1.10), lens=26, fstop=2.4, focus=6.0)
key_loc(cam, 1, (0.30, -1.5, 1.50))
key_loc(cam, N_FRAMES, (-0.12, 7.0, 1.34))
key_loc(tgt, 1, (-0.05, 12.0, 1.10))
key_loc(tgt, N_FRAMES, (0.06, 20.0, 1.30))
set_interp(cam, "BEZIER")
set_interp(tgt, "BEZIER")

post(glow=-0.2, glow_size=7, threshold=1.5, vignette=0.45, dispersion=0.008)
apply_recipe(sc, thin_haze=["haze"] if HAZE > 0 else ())

BORDER = os.environ.get("BORDER", "")          # "x0,x1,y0,y1" (0..1, from the bottom left): render only that part
if BORDER:
    bx0, bx1, by0, by1 = [float(v) for v in BORDER.split(",")]
    sc.render.use_border = True
    sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_max_x = bx0, bx1
    sc.render.border_min_y, sc.render.border_max_y = by0, by1

os.makedirs(OUT_DIR, exist_ok=True)
start_time = time.time()
for frame in FRAMES:
    sc.frame_set(frame)
    t = (frame - 1) / FPS
    for tn in TIME_NODES:
        tn.outputs[0].default_value = t
    sc.render.filepath = os.path.join(OUT_DIR, "frame_%04d.png" % frame)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print("RENDERED frame", frame, "t=%.2f" % t, "size %d%% samples %d" % (PCT, sc.cycles.samples),
          "took %.1fs" % (time.time() - t0), "elapsed %.1fs" % (time.time() - start_time), flush=True)
print("TOTAL_RENDER_SECONDS", round(time.time() - start_time, 1), flush=True)
