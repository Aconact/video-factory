"""Test shot: an AI accelerator package comes apart layer by layer (5 s, 1080x1920, 30 fps).

Photoreal product-render look: studio softbox lighting with real reflections, PBR materials with micro surface detail,
thin-film (rainbow) silicon, dense small parts (solder bumps, micro-bumps, SMD capacitors, layered memory stacks),
shallow depth of field, a camera that never stops (orbit + push-in) and anchors that the 2D label layer follows.

Environment:  FRAMES  RES_PERCENT  SAMPLES  OUT_DIR  [BORDER=x0,x1,y0,y1]  [ANCHORS_OUT=file.json]  [DOF_F=2.8]
"""
import json
import math
import os
import random
import time

import bpy
import bmesh
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.normpath(os.path.join(HERE, "..", "chip", "fonts"))
FPS = 30
N_FRAMES = 150
PCT = int(os.environ.get("RES_PERCENT", "50"))
SAMPLES = int(os.environ.get("SAMPLES", "32"))
OUT_DIR = os.environ.get("OUT_DIR", "out/frames")
FRAMES = [int(x) for x in os.environ.get("FRAMES", "1").split(",") if x.strip()]
ANCHORS_OUT = os.environ.get("ANCHORS_OUT", "")
BORDER = os.environ.get("BORDER", "")
DOF_F = float(os.environ.get("DOF_F", "3.6"))
WALL_S = float(os.environ.get("WALL_S", "1.3"))                                  # brightness of the reflected back wall
LIGHTS_OFF = [x for x in os.environ.get("LIGHTS_OFF", "").split(",") if x]       # debugging: switch studio lights off by name
UNIT_CM = os.environ.get("UNIT_CM", "1") == "1"      # 1 Blender unit = 1 cm, so the depth of field behaves like a macro lens

GREEN = (0.0, 1.0, 0.53)     # #00FF87
CYAN = (0.0, 0.96, 1.0)      # #00F5FF
random.seed(11)
_T0 = time.time()


def tick(label):
    print("SETUP %-14s %5.1fs" % (label, time.time() - _T0), flush=True)



bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, N_FRAMES
scene.render.fps = FPS
if UNIT_CM:
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.01


def lin(c):
    """sRGB 0..1 -> scene linear (so brand colours come out as their real hex values)."""
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)


# =========================================================================== materials
def mat(name, base, metallic=0.0, rough=0.5, coat=0.0, coat_rough=0.12, spec=0.5, ior=1.45, film=0.0, film_ior=1.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = coat_rough
    b.inputs["Specular IOR Level"].default_value = spec
    b.inputs["IOR"].default_value = ior
    if film > 0:
        b.inputs["Thin Film Thickness"].default_value = film
        b.inputs["Thin Film IOR"].default_value = film_ior
    return m


def bsdf(m):
    return m.node_tree.nodes["Principled BSDF"]


def micro(m, scale=900.0, stretch=(1, 1, 1), bump=0.1, rough=None, detail=3.0, dist=0.01, coord="Object", rot=None):
    """Micro surface: a noise drives a bump and (optionally) the roughness, so no surface is a perfect mirror."""
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale * stretch[0], scale * stretch[1], scale * stretch[2])
    if rot is not None:
        mp.inputs["Rotation"].default_value = rot
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Detail"].default_value = detail
    nt.links.new(tc.outputs[coord], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    if bump:
        bm = nt.nodes.new("ShaderNodeBump")
        bm.inputs["Strength"].default_value = bump
        bm.inputs["Distance"].default_value = dist
        nt.links.new(nz.outputs["Fac"], bm.inputs["Height"])
        nt.links.new(bm.outputs["Normal"], b.inputs["Normal"])
    if rough:
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.3, 0.7
        mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = rough
        nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return nz


# lid: nickel-plated copper, bead-blasted with faint machining scratches
M_LID = mat("lid", (0.54, 0.55, 0.58), 1.0, 0.18)
micro(M_LID, 1400.0, (1, 1, 1), 0.06, (0.07, 0.22), 3.0, 0.004)
def cloud(m, base, scale=0.35, lo=0.55, hi=1.15, seed=(0.0, 0.0, 0.0), ramp=None):
    """Large soft tonal variation (like satin metal under a softbox): multiplies the base colour by a cloudy noise."""
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale * 0.18, scale * 26.0, scale)
    mp.inputs["Location"].default_value = seed
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Detail"].default_value = 2.0
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    v = maprange(nt, nz.outputs["Fac"], 0.3, 0.7, lo, hi)
    if ramp:        # (gx, gy, lo, hi, span): a broad tone ramp across the plate, like the falloff of a big softbox on brushed metal
        sp = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sp.inputs["Vector"])
        t = mn(nt, "ADD", mn(nt, "MULTIPLY", sp.outputs["X"], ramp[0]), mn(nt, "MULTIPLY", sp.outputs["Y"], ramp[1]))
        v = mn(nt, "MULTIPLY", v, maprange(nt, t, -ramp[4], ramp[4], ramp[2], ramp[3], smooth=True))
    rgb = nt.nodes.new("ShaderNodeRGB")
    rgb.outputs[0].default_value = (*base, 1.0)
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.blend_type = "MULTIPLY"
    mx.inputs[0].default_value = 1.0
    nt.links.new(rgb.outputs[0], mx.inputs[6])
    nt.links.new(v, mx.inputs[7])
    nt.links.new(mx.outputs[2], b.inputs["Base Color"])


M_LID_RIM = mat("lid_rim", (0.52, 0.53, 0.56), 1.0, 0.20)
micro(M_LID_RIM, 900.0, (1, 1, 1), 0.04, (0.12, 0.26), 2.0, 0.004)
M_ETCH = mat("etch", (0.035, 0.037, 0.04), 0.0, 0.55)
M_TIM_PLACEHOLDER = None
# thermal interface sheet: a mirror-ish liquid-metal pad
M_TIM = mat("tim", (0.42, 0.44, 0.48), 1.0, 0.12)
micro(M_TIM, 220.0, (1, 1, 1), 0.10, (0.08, 0.20), 4.0, 0.006)
# silicon: dark, glossy, rainbow thin-film reflections
M_DIE = mat("die", (0.030, 0.034, 0.045), 0.55, 0.14, spec=0.8, film=420.0, film_ior=1.7)
M_DRAM = mat("dram", (0.095, 0.108, 0.150), 0.40, 0.22, spec=0.8, film=330.0, film_ior=1.6)
micro(M_DRAM, 400.0, (1, 1, 1), 0.04, (0.12, 0.26), 2.0, 0.003)
M_BASEDIE = mat("basedie", (0.050, 0.052, 0.058), 0.7, 0.28, film=250.0)
M_FILL = mat("underfill", (0.34, 0.20, 0.07), 0.0, 0.42, coat=0.2)
M_INTERP = mat("interposer", (0.025, 0.040, 0.060), 0.65, 0.22, film=290.0, film_ior=1.55)
micro(M_INTERP, 600.0, (1, 1, 1), 0.05, (0.16, 0.30), 3.0, 0.004)
M_SUB = mat("substrate", (0.004, 0.032, 0.018), 0.0, 0.42, coat=0.35, coat_rough=0.30, spec=0.5)
micro(M_SUB, 150.0, (1, 1, 1), 0.25, (0.34, 0.5), 5.0, 0.01)
M_RING = mat("ring", (0.075, 0.078, 0.085), 1.0, 0.34)
micro(M_RING, 800.0, (1, 0.02, 1), 0.10, (0.26, 0.42), 2.0, 0.004)
M_GOLD = mat("gold", (1.0, 0.72, 0.30), 1.0, 0.20)
M_SOLDER = mat("solder", (0.80, 0.80, 0.83), 1.0, 0.17)
M_UBUMP = mat("ubump", (0.90, 0.55, 0.28), 1.0, 0.22)
M_CAP = mat("cap_body", (0.20, 0.11, 0.045), 0.0, 0.38, coat=0.15)
M_TERM = mat("cap_term", (0.82, 0.83, 0.86), 1.0, 0.24)
M_SILK = mat("silk", (0.85, 0.88, 0.86), 0.0, 0.55)

def mn(nt, op, *args, clamp=False):
    """Math node helper: numbers become default values, sockets get linked. Returns the output socket."""
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, a_ in enumerate(args):
        if isinstance(a_, (int, float)):
            n.inputs[i].default_value = float(a_)
        else:
            nt.links.new(a_, n.inputs[i])
    return n.outputs[0]


def maprange(nt, val, lo, hi, out_lo=0.0, out_hi=1.0, smooth=False):
    n = nt.nodes.new("ShaderNodeMapRange")
    n.interpolation_type = "SMOOTHSTEP" if smooth else "LINEAR"
    n.clamp = True
    n.inputs["From Min"].default_value, n.inputs["From Max"].default_value = lo, hi
    n.inputs["To Min"].default_value, n.inputs["To Max"].default_value = out_lo, out_hi
    if isinstance(val, (int, float)):
        n.inputs["Value"].default_value = float(val)
    else:
        nt.links.new(val, n.inputs["Value"])
    return n.outputs["Result"]


def film_var(m, lo, hi, scale, offset=(0.0, 0.0, 0.0)):
    """Thin-film thickness drifts across the surface, so the rainbow reflections move over it like on a real die."""
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    mp.inputs["Location"].default_value = offset
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Detail"].default_value = 2.0
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(maprange(nt, nz.outputs["Fac"], 0.35, 0.65, lo, hi), b.inputs["Thin Film Thickness"])


cloud(M_LID, (0.54, 0.55, 0.58), 0.5, 0.74, 1.04, ramp=(0.5, 0.3, 0.55, 1.12, 3.5))
cloud(M_TIM, (0.42, 0.44, 0.48), 0.4, 0.82, 1.06, (4.0, 1.0, 0.0), ramp=(-0.5, 0.35, 0.50, 1.02, 3.0))
film_var(M_DIE, 230.0, 640.0, 0.9)
film_var(M_DRAM, 140.0, 430.0, 2.2, (3.0, 1.0, 0.0))

# die floor-plan blocks: every block is a dark glossy plate with a real-looking cell structure (rows of standard cells or an
# SRAM dot array). Once the chip "runs", regions of cells light up behind a wave front and stay faintly lit: no flat glowing slabs.
BLOCK_MATS = []      # (material, master value node, scan value node) -- animated in the bake loop


def cell_mask(nt, X, Y, kind, seed):
    """1 on a cell, 0 in the gaps between cells (SRAM: round dots on a grid; logic: staggered rows of cells)."""
    if kind == "sram":
        u = mn(nt, "ADD", mn(nt, "DIVIDE", X, 0.034), seed * 0.173)
        v = mn(nt, "ADD", mn(nt, "DIVIDE", Y, 0.034), seed * 0.291)
        fx, fy = mn(nt, "FRACT", u), mn(nt, "FRACT", v)
        d = mn(nt, "SQRT", mn(nt, "ADD", mn(nt, "POWER", mn(nt, "SUBTRACT", fx, 0.5), 2.0), mn(nt, "POWER", mn(nt, "SUBTRACT", fy, 0.5), 2.0)))
        return mn(nt, "SUBTRACT", 1.0, maprange(nt, d, 0.22, 0.34, 0.0, 1.0, smooth=True))
    u = mn(nt, "ADD", mn(nt, "DIVIDE", X, 0.070), seed * 0.173)
    v = mn(nt, "ADD", mn(nt, "DIVIDE", Y, 0.0165), seed * 0.291)
    r = mn(nt, "FLOOR", v)
    par = mn(nt, "SUBTRACT", r, mn(nt, "MULTIPLY", mn(nt, "FLOOR", mn(nt, "MULTIPLY", r, 0.5)), 2.0))
    fx = mn(nt, "FRACT", mn(nt, "ADD", u, mn(nt, "MULTIPLY", par, 0.5)))
    fy = mn(nt, "FRACT", v)
    ex = mn(nt, "MINIMUM", fx, mn(nt, "SUBTRACT", 1.0, fx))
    ey = mn(nt, "MINIMUM", fy, mn(nt, "SUBTRACT", 1.0, fy))
    return mn(nt, "MULTIPLY", maprange(nt, ex, 0.03, 0.09, 0.0, 1.0, smooth=True), maprange(nt, ey, 0.10, 0.24, 0.0, 1.0, smooth=True))


def make_block_mat(idx, w, h, kind, hue):
    m = mat("block%d" % idx, (0.016, 0.022, 0.034), 0.75, 0.18, spec=0.8, film=300.0, film_ior=1.6)
    nt = m.node_tree
    b = bsdf(m)
    vm = nt.nodes.new("ShaderNodeValue")
    vm.outputs[0].default_value = 0.0
    vs = nt.nodes.new("ShaderNodeValue")
    vs.outputs[0].default_value = -3.0
    tc = nt.nodes.new("ShaderNodeTexCoord")
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    so = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], so.inputs["Vector"])
    sl = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(oi.outputs["Location"], sl.inputs["Vector"])
    X, Y = so.outputs["X"], so.outputs["Y"]
    ed = mn(nt, "MINIMUM", mn(nt, "SUBTRACT", w / 2.0, mn(nt, "ABSOLUTE", X)), mn(nt, "SUBTRACT", h / 2.0, mn(nt, "ABSOLUTE", Y)))
    rim = mn(nt, "SUBTRACT", 1.0, maprange(nt, ed, 0.003, 0.012, 0.0, 1.0, smooth=True))      # 1 on a thin line at the block edge
    cell = cell_mask(nt, X, Y, kind, idx + 1.0)
    # surface: cells are a touch brighter and glossier than the gaps; a small bump so they catch the light
    base = nt.nodes.new("ShaderNodeMix")
    base.data_type = "RGBA"
    base.inputs[6].default_value = (0.012, 0.017, 0.027, 1.0)
    base.inputs[7].default_value = (0.034, 0.046, 0.074, 1.0)
    nt.links.new(cell, base.inputs[0])
    nt.links.new(base.outputs[2], b.inputs["Base Color"])
    nt.links.new(maprange(nt, cell, 0.0, 1.0, 0.30, 0.11), b.inputs["Roughness"])
    bm = nt.nodes.new("ShaderNodeBump")
    bm.inputs["Strength"].default_value = 0.45
    bm.inputs["Distance"].default_value = 0.0015
    nt.links.new(cell, bm.inputs["Height"])
    nt.links.new(bm.outputs["Normal"], b.inputs["Normal"])
    film_var(m, 210.0, 700.0, 1.5, (idx * 1.7, 0.0, 0.0))
    # activity: thin routing lines (horizontal and vertical metal tracks, random segments) light up behind a wave front and carry
    # moving dashes of light; the cells themselves stay dark. Looks like wiring, not like a lit-up panel.
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (idx * 3.1, idx * 1.3, 0.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 9.0
    nz.inputs["Detail"].default_value = 2.0
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nr = maprange(nt, nz.outputs["Fac"], 0.32, 0.70, 0.0, 1.0)
    behind = mn(nt, "SUBTRACT", vs.outputs[0], mn(nt, "ADD", sl.outputs["Y"], Y))              # how far behind the wave front this point is
    q = mn(nt, "SUBTRACT", behind, mn(nt, "MULTIPLY", nr, 0.9))
    act = mn(nt, "MULTIPLY", maprange(nt, q, 0.0, 0.30, 0.0, 1.0, smooth=True),
             mn(nt, "SUBTRACT", 1.0, mn(nt, "MULTIPLY", maprange(nt, q, 0.35, 1.4, 0.0, 1.0), 0.45)))

    def rnd3(a, b, c):
        cx = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(a, cx.inputs["X"])
        nt.links.new(b, cx.inputs["Y"])
        cx.inputs["Z"].default_value = c
        wn = nt.nodes.new("ShaderNodeTexWhiteNoise")
        wn.noise_dimensions = "3D"
        nt.links.new(cx.outputs[0], wn.inputs["Vector"])
        return wn.outputs["Value"]

    def tracks(along, across, seed, pitch, seglen, thick, density):
        """Bars running along `along`, stacked across `across`; each segment is on with probability `density` and carries moving dashes."""
        row = mn(nt, "ADD", mn(nt, "DIVIDE", across, pitch), seed * 0.37)
        ri = mn(nt, "FLOOR", row)
        band = mn(nt, "SUBTRACT", 1.0, maprange(nt, mn(nt, "ABSOLUTE", mn(nt, "SUBTRACT", mn(nt, "FRACT", row), 0.5)), thick, thick + 0.10, 0.0, 1.0, smooth=True))
        seg = mn(nt, "FLOOR", mn(nt, "ADD", mn(nt, "DIVIDE", along, seglen), mn(nt, "MULTIPLY", rnd3(ri, ri, seed + 0.5), 3.0)))
        r1 = rnd3(seg, ri, seed + 1.5)
        on = mn(nt, "SUBTRACT", 1.0, maprange(nt, r1, density, density + 0.02, 0.0, 1.0))        # 1 for a fraction `density` of the segments
        ph = mn(nt, "ADD", mn(nt, "MULTIPLY", along, 52.0), mn(nt, "MULTIPLY", rnd3(seg, ri, seed + 2.5), 6.283))
        ph = mn(nt, "SUBTRACT", ph, mn(nt, "MULTIPLY", vs.outputs[0], 14.0))
        dash = mn(nt, "POWER", mn(nt, "ADD", mn(nt, "MULTIPLY", mn(nt, "SINE", ph), 0.5), 0.5), 3.0)
        return mn(nt, "MULTIPLY", mn(nt, "MULTIPLY", on, band), mn(nt, "ADD", 0.10, mn(nt, "MULTIPLY", dash, 0.90))), r1

    h_val, h_r = tracks(X, Y, idx * 2.0 + 1.0, 0.042, 0.34, 0.075, 0.24)
    v_val, v_r = tracks(Y, X, idx * 2.0 + 2.0, 0.046, 0.30, 0.075, 0.21)
    lines = mn(nt, "MAXIMUM", h_val, v_val)
    glow = mn(nt, "MULTIPLY", mn(nt, "ADD", mn(nt, "MULTIPLY", lines, 8.0), mn(nt, "MULTIPLY", rim, 0.45)), act)
    nt.links.new(mn(nt, "MULTIPLY", glow, vm.outputs[0]), b.inputs["Emission Strength"])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs[6].default_value = (*lin(CYAN), 1.0)
    col.inputs[7].default_value = (*lin(GREEN), 1.0)
    nt.links.new(mn(nt, "ADD", mn(nt, "MULTIPLY", mn(nt, "MAXIMUM", mn(nt, "MULTIPLY", h_val, h_r), mn(nt, "MULTIPLY", v_val, v_r)), 1.6), hue, clamp=True), col.inputs[0])
    nt.links.new(col.outputs[2], b.inputs["Emission Color"])
    BLOCK_MATS.append((m, vm, vs))
    return m


M_SEAL = mat("seal", (0.55, 0.50, 0.42), 1.0, 0.25)


tick("materials")
# =========================================================================== geometry helpers
def link(obj, parent=None):
    scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def group(name):
    return link(bpy.data.objects.new(name, None))


G_SUB, G_INT, G_DIE, G_TIM, G_LID = (group(n) for n in ("g_sub", "g_interposer", "g_die", "g_tim", "g_lid"))


def box(name, size, loc, material, parent, bevel=0.0, segs=3):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    bm.to_mesh(mesh)
    bm.free()
    obj = link(bpy.data.objects.new(name, mesh), parent)
    obj.location = loc
    mesh.materials.append(material)
    if bevel > 0:
        md = obj.modifiers.new("bevel", "BEVEL")
        md.width = bevel
        md.segments = segs
        md.limit_method = "ANGLE"
        md.harden_normals = True
    for p in mesh.polygons:
        p.use_smooth = True
    return obj


class MB:
    """Many small parts merged into one mesh (fast to render, keeps the scene tidy)."""
    TPL = {}

    def __init__(self):
        self.bm = bmesh.new()

    def box(self, cx, cy, cz, sx, sy, sz, mi=0):
        res = bmesh.ops.create_cube(self.bm, size=1.0)
        for v in res["verts"]:
            v.co = Vector((v.co.x * sx + cx, v.co.y * sy + cy, v.co.z * sz + cz))
        for f in {f for v in res["verts"] for f in v.link_faces}:
            f.material_index = mi
        return res

    def _stamp(self, key, make, sx, sy, sz, cx, cy, cz, mi):
        """Copy a cached unit shape into the mesh (bmesh.ops.create_* slows down as the mesh grows; this stays constant-time)."""
        if key not in MB.TPL:
            tmp = bmesh.new()
            make(tmp)
            idx = {v: i for i, v in enumerate(tmp.verts)}
            MB.TPL[key] = ([tuple(v.co) for v in tmp.verts], [[idx[v] for v in f.verts] for f in tmp.faces])
            tmp.free()
        verts, faces = MB.TPL[key]
        vs = [self.bm.verts.new((v[0] * sx + cx, v[1] * sy + cy, v[2] * sz + cz)) for v in verts]
        for f in faces:
            self.bm.faces.new([vs[i] for i in f]).material_index = mi

    def cyl(self, cx, cy, cz, r, h, seg=10, mi=0):
        self._stamp(("cyl", seg), lambda b: bmesh.ops.create_cone(b, cap_ends=True, cap_tris=False, segments=seg, radius1=1.0, radius2=1.0, depth=1.0),
                    r, r, h, cx, cy, cz, mi)

    def sph(self, cx, cy, cz, r, zs=1.0, u=10, v=6, mi=0):
        self._stamp(("sph", u, v), lambda b: bmesh.ops.create_uvsphere(b, u_segments=u, v_segments=v, radius=1.0), r, r, r * zs, cx, cy, cz, mi)

    def build(self, name, mats, parent, smooth=True, bevel=0.0):
        mesh = bpy.data.meshes.new(name)
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        if bevel > 0:
            bmesh.ops.bevel(self.bm, geom=list(self.bm.edges), offset=bevel, segments=2, affect="EDGES")
        self.bm.to_mesh(mesh)
        self.bm.free()
        for m in mats:
            mesh.materials.append(m)
        for p in mesh.polygons:
            p.use_smooth = smooth
        return link(bpy.data.objects.new(name, mesh), parent)


def font(name):
    path = os.path.join(FONTS, name)
    return bpy.data.fonts.load(path) if os.path.exists(path) else None


def text(name, body, size, material, loc, parent, face="Inter-ExtraBold.otf", extrude=0.004, bevel=0.0008, rot=(0, 0, 0),
         align="CENTER"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body, cu.size, cu.extrude, cu.bevel_depth = body, size, extrude, bevel
    cu.bevel_resolution, cu.resolution_u = 1, 8
    cu.align_x, cu.align_y = align, "CENTER"
    f = font(face)
    if f is not None:
        cu.font = f
    cu.materials.append(material)
    obj = link(bpy.data.objects.new(name, cu), parent)
    obj.location = loc
    obj.rotation_euler = rot
    return obj


# =========================================================================== the package, bottom to top
# heights (z): substrate top 0 | C4 bumps 0-0.04 | interposer 0.04-0.10 | micro-bumps 0.10-0.125
#              die and memory 0.125-0.255 | TIM 0.256-0.268 | lid plate 0.268-0.338
SX, SY, ST = 6.6, 5.2, 0.14
box("substrate", (SX, SY, ST), (0, 0, -ST / 2), M_SUB, G_SUB, bevel=0.03)

# stiffener ring (holds the lid) -- four bars around the interposer
RING_H = 0.14
for nm, sz, loc in (("ring_n", (5.95, 0.25, RING_H), (0, 2.0, RING_H / 2)), ("ring_s", (5.95, 0.25, RING_H), (0, -2.0, RING_H / 2)),
                    ("ring_e", (0.25, 3.75, RING_H), (2.85, 0, RING_H / 2)), ("ring_w", (0.25, 3.75, RING_H), (-2.85, 0, RING_H / 2))):
    box(nm, sz, loc, M_RING, G_SUB, bevel=0.015)

# C4 solder bumps on the substrate (visible once the interposer lifts off)
mb = MB()
pitch = 0.17
for i in range(-15, 16):
    for j in range(-9, 10):
        x, y = i * pitch, j * pitch
        if abs(x) <= 2.5 and abs(y) <= 1.6:
            mb.sph(x, y, 0.022, 0.050, zs=0.82)
mb.build("c4_bumps", [M_SOLDER], G_SUB)
tick("c4")

# SMD capacitors around the package (silver ends on dark brown bodies), skipped at random like a real board
mb = MB()
rng = random.Random(3)
for x in [-3.18 + k * 0.22 for k in range(0, 30)]:
    for y in (-2.40, 2.40):
        if abs(x) < 3.22 and rng.random() > 0.12:
            for mi, (dx, sx_) in enumerate(((0, 0.07), (-0.065, 0.045), (0.065, 0.045))):
                pass
            mb.box(x, y, 0.035, 0.10, 0.17, 0.07, 0)
            mb.box(x, y + 0.075, 0.035, 0.10, 0.025, 0.072, 1)
            mb.box(x, y - 0.075, 0.035, 0.10, 0.025, 0.072, 1)
for y in [-2.1 + k * 0.2 for k in range(0, 22)]:
    for x in (-3.17, 3.17):
        if abs(y) < 2.15 and rng.random() > 0.12:
            mb.box(x, y, 0.035, 0.17, 0.10, 0.07, 0)
            mb.box(x + 0.075, y, 0.035, 0.025, 0.10, 0.072, 1)
            mb.box(x - 0.075, y, 0.035, 0.025, 0.10, 0.072, 1)
for k in range(46):                    # a looser scatter of small parts inside the corner areas of the margin
    x = rng.choice((-1, 1)) * rng.uniform(3.02, 3.26)
    y = rng.uniform(-2.45, 2.45)
    mb.box(x, y, 0.03, 0.06, 0.10, 0.06, 1)
mb.build("caps", [M_CAP, M_TERM], G_SUB, smooth=False, bevel=0.005)
tick("caps")

# gold fiducials and a pin-1 mark on the substrate, silkscreen text
mb = MB()
for sx_, sy_ in ((-1, -1), (1, 1), (-1, 1)):
    mb.cyl(sx_ * 3.1, sy_ * 2.5, 0.003, 0.07, 0.006, seg=18)
mb.build("fiducials", [M_GOLD], G_SUB)
tick("fiducials")
for i, (lab, x, y, r) in enumerate((("TP-1  REV B", -2.2, -2.43, 0), ("U1", 3.28, -2.43, 0), ("C 101-188", 0.6, 2.42, 0),
                                    ("GND", -3.27, 0.4, math.pi / 2), ("VDD CORE", 3.28, 0.9, math.pi / 2))):
    text("silk%d" % i, lab, 0.115, M_SILK, (x, y, 0.002), G_SUB, face="JetBrainsMono-Bold.ttf", extrude=0.0012, bevel=0.0003,
         rot=(0, 0, r))

tick("substrate")
# ---- interposer + micro-bumps
box("interposer", (5.2, 3.5, 0.06), (0, 0, 0.07), M_INTERP, G_INT, bevel=0.012)
# memory sites and the die site
HBM_X = (-1.75, 1.75)
HBM_Y = (-1.0, 0.0, 1.0)
DIE_W, DIE_D = 2.3, 2.5
mb = MB()
for i in range(-11, 12):
    for j in range(-12, 13):
        x, y = i * 0.1, j * 0.1
        if abs(x) <= 1.1 and abs(y) <= 1.2:
            mb.cyl(x, y, 0.1125, 0.028, 0.025, seg=8)
for hx in HBM_X:
    for hy in HBM_Y:
        for i in range(-4, 5):
            for j in range(-4, 5):
                mb.cyl(hx + i * 0.09, hy + j * 0.095, 0.1125, 0.026, 0.025, seg=8)
mb.build("microbumps", [M_UBUMP], G_INT)

tick("interposer")
# ---- compute die (floor-plan material) and six memory stacks
die = box("die", (DIE_W, DIE_D, 0.13), (0, 0, 0.19), M_DIE, G_DIE, bevel=0.012)


def bsp(rect, rng, depth=0, max_depth=5, min_side=0.30):
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    if depth >= max_depth or (w < 2.1 * min_side and h < 2.1 * min_side) or (depth >= 2 and rng.random() < 0.20):
        return [rect]
    split_x = (w > h) if rng.random() < 0.8 else (w <= h)
    if split_x and w < 2.1 * min_side:
        split_x = False
    if (not split_x) and h < 2.1 * min_side:
        split_x = True
    t = rng.uniform(0.38, 0.62)
    if split_x:
        xm = x0 + w * t
        return bsp((x0, y0, xm, y1), rng, depth + 1, max_depth, min_side) + bsp((xm, y0, x1, y1), rng, depth + 1, max_depth, min_side)
    ym = y0 + h * t
    return bsp((x0, y0, x1, ym), rng, depth + 1, max_depth, min_side) + bsp((x0, ym, x1, y1), rng, depth + 1, max_depth, min_side)


FP_SEED = int(os.environ.get("FP_SEED", "4"))
FLOORPLAN = bsp((-DIE_W / 2 + 0.09, -DIE_D / 2 + 0.09, DIE_W / 2 - 0.09, DIE_D / 2 - 0.09), random.Random(FP_SEED))
_by_area = sorted(range(len(FLOORPLAN)), key=lambda j: -(FLOORPLAN[j][2] - FLOORPLAN[j][0]) * (FLOORPLAN[j][3] - FLOORPLAN[j][1]))
SRAM_BLOCKS = set(_by_area[:3])          # the three biggest blocks are cache (dot arrays), the rest are logic (cell rows)
for i, (bx0, by0, bx1, by1) in enumerate(FLOORPLAN):
    gap = 0.022
    bw_, bh_ = bx1 - bx0 - gap, by1 - by0 - gap
    bmat = make_block_mat(i, bw_, bh_, "sram" if i in SRAM_BLOCKS else "logic", 0.10 + 0.13 * (i % 4))
    box("blk%d" % i, (bw_, bh_, 0.006), ((bx0 + bx1) / 2, (by0 + by1) / 2, 0.255 + 0.003), bmat, G_DIE, bevel=0.0018, segs=2)
print("floorplan blocks:", len(FLOORPLAN), flush=True)
for nm, sz, loc in (("seal_n", (DIE_W - 0.05, 0.03, 0.008), (0, DIE_D / 2 - 0.03, 0.258)), ("seal_s", (DIE_W - 0.05, 0.03, 0.008), (0, -DIE_D / 2 + 0.03, 0.258)),
                    ("seal_e", (0.03, DIE_D - 0.05, 0.008), (DIE_W / 2 - 0.03, 0, 0.258)), ("seal_w", (0.03, DIE_D - 0.05, 0.008), (-DIE_W / 2 + 0.03, 0, 0.258))):
    box(nm, sz, loc, M_SEAL, G_DIE, bevel=0.003, segs=2)
# memory stacks (HBM): a logic base die with eight DRAM dies on top. Each die has an adhesive frame under it (the tan stripes you see
# on the sides while the stack is closed) and a grid of copper TSV pads on top; the stack comes apart later in the shot, and thin
# copper columns (the through-silicon vias) grow between the dies.
LAYER_T, LAYER_P = 0.0095, 0.0135
Z_L0 = 0.1505                          # underside of the first DRAM die
HBM_GAP = 0.085                        # extra spacing per layer once the stack is open
PAD_X = [(i - 4) * 0.044 for i in range(9)]
PAD_Y = [(j - 7.5) * 0.040 for j in range(16)]
HBM_LAYERS = []                        # (object, k, rest z)
HBM_COLS = []                          # (object, rest z of the top die) -- TSV columns, scaled with the opening
HBM_TOP = {}                           # (hx, hy) -> the top die (carries the label anchor)
for hx in HBM_X:
    for hy in HBM_Y:
        base = box("hbm_base", (0.90, 0.92, 0.022), (hx, hy, 0.125 + 0.011), M_BASEDIE, G_DIE, bevel=0.004)
        mbp = MB()                     # coordinates relative to the base die centre (top face at +0.011)
        for px in PAD_X:
            for py in PAD_Y:
                mbp.cyl(px, py, 0.011 + 0.0008, 0.0105, 0.0016, seg=8)
        mbp.build("hbm_basepads", [M_UBUMP], base, smooth=False)
        col = MB()                     # TSV columns, one mesh per stack, built full height and scaled in z while the stack opens
        H_FULL = 7 * LAYER_P + 8 * HBM_GAP + 0.02
        for px in PAD_X:
            for py in PAD_Y:
                col.cyl(px, py, H_FULL / 2, 0.0042, H_FULL, seg=6)
        for i in range(13):                                    # a row of posts along each long edge...
            for sy_ in (-1, 1):
                col.cyl(-0.33 + i * (0.66 / 12), sy_ * 0.355, H_FULL / 2, 0.0085, H_FULL, seg=8)
        for j in range(1, 8):                                  # ...and along each short edge
            for sx_ in (-1, 1):
                col.cyl(sx_ * 0.335, -0.355 + j * (0.71 / 8), H_FULL / 2, 0.0085, H_FULL, seg=8)
        colobj = col.build("hbm_tsv", [M_UBUMP], G_DIE, smooth=False)
        colobj.location = (hx, hy, 0.147)
        colobj.scale = (1.0, 1.0, 0.0001)
        HBM_COLS.append((colobj, H_FULL))
        for k in range(8):
            zc = Z_L0 + k * LAYER_P + LAYER_T / 2
            lay = box("hbm_l%d" % k, (0.80, 0.84, LAYER_T), (hx, hy, zc), M_DRAM, G_DIE, bevel=0.0028, segs=2)
            mx = MB()                  # coordinates relative to the die centre
            fz, fw, fd, fb, fh = -LAYER_T / 2 - 0.002, 0.806, 0.846, 0.026, 0.0046
            mx.box(0, fd / 2 - fb / 2, fz, fw, fb, fh, 0)
            mx.box(0, -(fd / 2 - fb / 2), fz, fw, fb, fh, 0)
            mx.box(fw / 2 - fb / 2, 0, fz, fb, fd - 2 * fb, fh, 0)
            mx.box(-(fw / 2 - fb / 2), 0, fz, fb, fd - 2 * fb, fh, 0)
            if k < 7:
                for px in PAD_X:
                    for py in PAD_Y:
                        mx.cyl(px, py, LAYER_T / 2 + 0.0008, 0.0105, 0.0016, seg=8, mi=1)
            mx.build("hbm_x%d" % k, [M_FILL, M_UBUMP], lay, smooth=False)
            HBM_LAYERS.append((lay, k, zc))
            if k == 7:
                HBM_TOP[(hx, hy)] = lay

tick("die+hbm")
# ---- data buses on the interposer: copper lines plus glowing pulses that run memory -> die once the chip is running
def path_curve(name, pts, material, radius, z, parent):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, (x, y) in enumerate(pts):
        sp.points[i].co = (x, y, z, 1.0)
    cu.bevel_depth = radius
    cu.bevel_resolution = 1
    cu.use_fill_caps = True
    cu.materials.append(material)
    return link(bpy.data.objects.new(name, cu), parent)


def emissive(name, color, strength):
    m_ = bpy.data.materials.new(name)
    m_.use_nodes = True
    b_ = bsdf(m_)
    b_.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b_.inputs["Emission Color"].default_value = (*lin(color), 1.0)
    b_.inputs["Emission Strength"].default_value = strength
    return m_


M_WIRE = mat("wire", (0.50, 0.30, 0.16), 1.0, 0.30)
M_PULSE_C = emissive("pulse_c", CYAN, 9.0)
M_PULSE_G = emissive("pulse_g", GREEN, 9.0)
L_PULSE = 0.22
for hx in HBM_X:
    sgn = 1 if hx > 0 else -1
    for hi, hy in enumerate(HBM_Y):
        for k in range(6):
            y0 = hy + (k - 2.5) * 0.055
            ye = hy * 0.80 + (k - 2.5) * 0.045
            pts = [(hx, y0), (sgn * 1.28, y0), (sgn * 1.05, ye), (sgn * 0.45, ye)]
            path_curve("wire", pts, M_WIRE, 0.010, 0.1015, G_INT)
            pulse = path_curve("pulse", pts, M_PULSE_C if (k + hi) % 2 == 0 else M_PULSE_G, 0.011, 0.1285, G_INT)
            pulse.data.bevel_factor_mapping_start = "SPLINE"
            pulse.data.bevel_factor_mapping_end = "SPLINE"
            f0 = 100 + k * 2 + hi * 3 + (0 if sgn > 0 else 4)
            run = 34 + (k * 5) % 12
            for _rep in range(3):
                if f0 > N_FRAMES + 12:
                    break
                for fr, a_, b_ in ((f0, 0.0, 0.0), (f0 + 2, 0.0, L_PULSE), (f0 + run, 1.0 - L_PULSE, 1.0), (f0 + run + 2, 1.0, 1.0)):
                    pulse.data.bevel_factor_start = a_
                    pulse.data.bevel_factor_end = b_
                    pulse.data.keyframe_insert("bevel_factor_start", frame=fr)
                    pulse.data.keyframe_insert("bevel_factor_end", frame=fr)
                f0 += run + 10 + (k * 7) % 13
            if not pulse.data.animation_data:
                pulse.data.bevel_factor_start = pulse.data.bevel_factor_end = 0.0

tick("buses")
# ---- thermal interface sheet
box("tim", (4.9, 3.4, 0.012), (0, 0, 0.262), M_TIM, G_TIM, bevel=0.004)

# ---- lid (heat spreader): plate + skirt + raised rim, laser-etched marks
LX, LY = 6.1, 4.4
box("lid_plate", (LX, LY, 0.07), (0, 0, 0.268 + 0.035), M_LID, G_LID, bevel=0.03, segs=4)
SK_H = 0.268 - 0.14
for nm, sz, loc in (("sk_n", (LX, 0.14, SK_H), (0, LY / 2 - 0.07, 0.14 + SK_H / 2)), ("sk_s", (LX, 0.14, SK_H), (0, -LY / 2 + 0.07, 0.14 + SK_H / 2)),
                    ("sk_e", (0.14, LY - 0.28, SK_H), (LX / 2 - 0.07, 0, 0.14 + SK_H / 2)), ("sk_w", (0.14, LY - 0.28, SK_H), (-LX / 2 + 0.07, 0, 0.14 + SK_H / 2))):
    box(nm, sz, loc, M_LID, G_LID, bevel=0.012)
RIM_Z = 0.338 + 0.006
for nm, sz, loc in (("rim_n", (LX - 0.3, 0.1, 0.012), (0, LY / 2 - 0.2, RIM_Z)), ("rim_s", (LX - 0.3, 0.1, 0.012), (0, -LY / 2 + 0.2, RIM_Z)),
                    ("rim_e", (0.1, LY - 0.5, 0.012), (LX / 2 - 0.2, 0, RIM_Z)), ("rim_w", (0.1, LY - 0.5, 0.012), (-LX / 2 + 0.2, 0, RIM_Z))):
    box(nm, sz, loc, M_LID_RIM, G_LID, bevel=0.004)
ZE = 0.338 + 0.002
text("etch_logo", "TP-1", 0.62, M_ETCH, (-0.55, 0.35, ZE), G_LID, extrude=0.004, bevel=0.0006)
text("etch_sub", "NEURAL PROCESSING UNIT", 0.122, M_ETCH, (-0.55, -0.22, ZE), G_LID, face="JetBrainsMono-Bold.ttf", extrude=0.003, bevel=0.0004)
text("etch_l1", "TP1-A  /  8 x HBM  /  PCIe 5.0", 0.082, M_ETCH, (-0.55, -0.52, ZE), G_LID, face="JetBrainsMono-Bold.ttf", extrude=0.003, bevel=0.0004)
text("etch_l2", "LOT 2611-0427  CN  REV B", 0.082, M_ETCH, (-2.05, -1.62, ZE), G_LID, face="JetBrainsMono-Bold.ttf", extrude=0.003, bevel=0.0004, align="LEFT")
mb = MB()
rq = random.Random(5)
N_DM, CELL = 14, 0.055
for i in range(N_DM):
    for j in range(N_DM):
        on = rq.random() < 0.5
        if i == 0 or j == 0:
            on = True
        elif i == N_DM - 1:
            on = j % 2 == 0
        elif j == N_DM - 1:
            on = i % 2 == 0
        if on:
            mb.box(1.85 + i * CELL, -1.55 + j * CELL, ZE, CELL * 0.86, CELL * 0.86, 0.004)
mb.build("etch_matrix", [M_ETCH], G_LID, smooth=False)
for sx_ in (-1, 1):
    for sy_ in (-1, 1):
        box("mark", (0.26, 0.018, 0.004), (sx_ * 2.55, sy_ * 1.75, ZE), M_ETCH, G_LID)

tick("lid")
# =========================================================================== label anchors (the 2D layer follows these)
ANCHORS = {}


def anchor(name, loc, parent):
    e = link(bpy.data.objects.new("anc_" + name, None), parent)
    e.location = loc
    ANCHORS[name] = e


anchor("lid", (2.3, -1.9, 0.338), G_LID)
anchor("tim", (2.4, -1.5, 0.268), G_TIM)
anchor("die", (0.9, -1.1, 0.255), G_DIE)
anchor("hbm", (0.10, 0.0, LAYER_T / 2), HBM_TOP[(1.75, -1.0)])      # follows the top memory die while the stack opens
anchor("interposer", (-2.3, -1.4, 0.10), G_INT)
anchor("substrate", (-3.1, -2.3, 0.0), G_SUB)

tick("anchors")
# =========================================================================== world: backdrop gradient for the camera, studio ambient for reflections
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
wt = world.node_tree
wt.nodes.clear()
w_out = wt.nodes.new("ShaderNodeOutputWorld")
w_mix = wt.nodes.new("ShaderNodeMixShader")
w_cam = wt.nodes.new("ShaderNodeBackground")
w_env = wt.nodes.new("ShaderNodeBackground")
w_lp = wt.nodes.new("ShaderNodeLightPath")
w_tc = wt.nodes.new("ShaderNodeTexCoord")
w_v1 = wt.nodes.new("ShaderNodeVectorMath")
w_v1.operation = "SUBTRACT"
w_v1.inputs[1].default_value = (0.5, 0.50, 0.0)
w_v2 = wt.nodes.new("ShaderNodeVectorMath")
w_v2.operation = "MULTIPLY"
w_v2.inputs[1].default_value = (0.5625, 1.0, 0.0)
w_v3 = wt.nodes.new("ShaderNodeVectorMath")
w_v3.operation = "LENGTH"
w_ramp = wt.nodes.new("ShaderNodeValToRGB")
el = w_ramp.color_ramp.elements
el[0].position, el[0].color = 0.0, (0.030, 0.055, 0.075, 1.0)
el[1].position, el[1].color = 0.62, (0.0015, 0.0025, 0.0045, 1.0)
mid = w_ramp.color_ramp.elements.new(0.26)
mid.color = (0.010, 0.020, 0.032, 1.0)
w_env.inputs["Color"].default_value = (0.055, 0.065, 0.085, 1.0)
w_env.inputs["Strength"].default_value = 0.30
wl = wt.links.new
wl(w_tc.outputs["Window"], w_v1.inputs[0])
wl(w_v1.outputs[0], w_v2.inputs[0])
wl(w_v2.outputs[0], w_v3.inputs[0])
wl(w_v3.outputs["Value"], w_ramp.inputs["Fac"])
wl(w_ramp.outputs["Color"], w_cam.inputs["Color"])
wl(w_lp.outputs["Is Camera Ray"], w_mix.inputs["Fac"])
wl(w_env.outputs["Background"], w_mix.inputs[1])
wl(w_cam.outputs["Background"], w_mix.inputs[2])
wl(w_mix.outputs["Shader"], w_out.inputs["Surface"])


# =========================================================================== lights: a studio rig that follows the camera orbit
def area(name, loc, target, size, power, color, shape="RECTANGLE", size_y=None, parent=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = shape
    ld.size = size
    if size_y:
        ld.size_y = size_y
    ld.energy = 0.0 if name in LIGHTS_OFF else power
    ld.color = color
    ob = link(bpy.data.objects.new(name, ld), parent)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    ob.visible_camera = False
    return ob


RIG = group("light_rig")


def emit_plane(name, w, h, loc, rot, color, strength, parent, gradient=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)], [], [(0, 1, 2, 3)])
    ob = link(bpy.data.objects.new(name, me), parent)
    ob.location, ob.rotation_euler = loc, rot
    mm = bpy.data.materials.new(name)
    mm.use_nodes = True
    nt = mm.node_tree
    nt.nodes.clear()
    out_ = nt.nodes.new("ShaderNodeOutputMaterial")
    em_ = nt.nodes.new("ShaderNodeEmission")
    em_.inputs["Color"].default_value = (*color, 1.0)
    em_.inputs["Strength"].default_value = strength
    if gradient:      # brightness along the plane's local Y (0..1): (stop, value) pairs
        tc_ = nt.nodes.new("ShaderNodeTexCoord")
        sp_ = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc_.outputs["Generated"], sp_.inputs["Vector"])
        ramp_ = nt.nodes.new("ShaderNodeValToRGB")
        cr = ramp_.color_ramp
        cr.elements[0].position, cr.elements[0].color = gradient[0][0], (gradient[0][1],) * 3 + (1.0,)
        cr.elements[1].position, cr.elements[1].color = gradient[-1][0], (gradient[-1][1],) * 3 + (1.0,)
        for pos, val in gradient[1:-1]:
            e_ = cr.elements.new(pos)
            e_.color = (val, val, val, 1.0)
        nt.links.new(sp_.outputs["Y"], ramp_.inputs["Fac"])
        mx_ = nt.nodes.new("ShaderNodeMath")
        mx_.operation = "MULTIPLY"
        nt.links.new(ramp_.outputs["Color"], mx_.inputs[0])
        mx_.inputs[1].default_value = strength
        nt.links.new(mx_.outputs[0], em_.inputs["Strength"])
    nt.links.new(em_.outputs["Emission"], out_.inputs["Surface"])
    me.materials.append(mm)
    ob.visible_camera = False
    ob.visible_shadow = False
    return ob


# back wall (faces the object, bright band at mid height) and a ceiling softbox
emit_plane("wall", 70.0, 44.0, (0, 22.0, 10.0), (math.radians(90), 0, 0), (0.88, 0.95, 1.0), WALL_S, RIG,
           gradient=[(0.0, 0.012), (0.40, 0.02), (0.50, 0.22), (0.57, 1.0), (0.63, 0.16), (0.75, 0.02), (1.0, 0.012)])
emit_plane("ceiling", 60.0, 60.0, (0, 0, 28.0), (math.radians(180), 0, 0), (0.95, 0.98, 1.0), 1.6, RIG,
           gradient=[(0.0, 0.03), (0.43, 0.04), (0.48, 0.80), (0.50, 1.0), (0.52, 0.80), (0.57, 0.04), (1.0, 0.03)])
area("key", (-7.0, -8.0, 9.0), (0, 0, 2.0), 6.0, 1700, (1.0, 0.96, 0.90), "RECTANGLE", 4.0, RIG)
area("fill", (8.0, -7.0, 4.5), (0, 0, 2.0), 5.0, 650, (0.78, 0.88, 1.0), "SQUARE", None, RIG)
area("rim_l", (-8.0, 7.0, 6.0), (0, 0, 2.0), 2.4, 1500, (0.55, 0.92, 1.0), "RECTANGLE", 10.0, RIG)
area("rim_r", (8.0, 7.5, 6.0), (0, 0, 2.0), 2.4, 1500, (0.70, 1.0, 0.86), "RECTANGLE", 10.0, RIG)
area("top", (0.0, 0.5, 15.0), (0, 0, 2.0), 3.4, 900, (0.90, 0.95, 1.0), "RECTANGLE", 14.0, RIG)
area("kick", (0.0, -10.0, 0.5), (0, 0, 1.5), 9.0, 420, (1.0, 0.93, 0.85), "RECTANGLE", 3.0, RIG)
# a narrow strip that sweeps across the lid at the start (the classic product-reveal glint)
SWEEP = area("sweep", (-9.0, 5.0, 4.0), (0, 0, 0.3), 0.6, 6500, (1.0, 1.0, 1.0), "RECTANGLE", 7.0)

# =========================================================================== dust motes (bokeh)
mote_meshes = []
for k, c in enumerate((CYAN, GREEN, (1.0, 1.0, 1.0))):
    me = bpy.data.meshes.new("mote%d" % k)
    bm_ = bmesh.new()
    bmesh.ops.create_uvsphere(bm_, u_segments=10, v_segments=6, radius=1.0)
    bm_.to_mesh(me)
    bm_.free()
    mm = bpy.data.materials.new("mote%d" % k)
    mm.use_nodes = True
    mb_ = bsdf(mm)
    mb_.inputs["Base Color"].default_value = (0, 0, 0, 1)
    mb_.inputs["Emission Color"].default_value = (*lin(c), 1.0)
    mb_.inputs["Emission Strength"].default_value = 3.2
    me.materials.append(mm)
    mote_meshes.append(me)
r2 = random.Random(21)
for k in range(22):
    ob = link(bpy.data.objects.new("mote%d" % k, mote_meshes[k % 3]))
    r = r2.uniform(0.008, 0.019)
    ob.scale = (r, r, r)
    p0 = Vector((r2.uniform(-6.0, 6.0), r2.uniform(-6.0, 4.0), r2.uniform(-0.5, 9.0)))
    drift = Vector((r2.uniform(-0.25, 0.25), r2.uniform(-0.2, 0.25), r2.uniform(0.1, 0.45)))
    ob.location = p0
    ob.keyframe_insert("location", frame=1)
    ob.location = p0 + drift * (N_FRAMES / FPS)
    ob.keyframe_insert("location", frame=N_FRAMES)

tick("lights+motes")
# =========================================================================== camera: one continuous move (orbit + rise + push-in), rack focus
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 38
cam_data.sensor_fit = "VERTICAL"
cam_data.sensor_height = 36
cam_data.clip_start, cam_data.clip_end = 0.05, 200
cam = link(bpy.data.objects.new("Cam", cam_data))
scene.camera = cam
target = link(bpy.data.objects.new("CamTarget", None))
focus = link(bpy.data.objects.new("Focus", None))
trk = cam.constraints.new("TRACK_TO")
trk.target = target
trk.track_axis = "TRACK_NEGATIVE_Z"
trk.up_axis = "UP_Y"
cam_data.dof.use_dof = True
cam_data.dof.focus_object = focus
cam_data.dof.aperture_fstop = DOF_F
cam_data.dof.aperture_blades = 7


def smooth_path(keys):
    """Cardinal (Catmull-Rom) spline through (frame, values...) keys: C1 continuous, so the camera never stops at a key."""
    xs = [k[0] for k in keys]
    n = len(keys)
    dim = len(keys[0]) - 1
    tang = []
    for i in range(n):
        if i == 0:
            t = [(keys[1][c + 1] - keys[0][c + 1]) / (xs[1] - xs[0]) for c in range(dim)]
        elif i == n - 1:
            t = [(keys[-1][c + 1] - keys[-2][c + 1]) / (xs[-1] - xs[-2]) for c in range(dim)]
        else:
            t = [(keys[i + 1][c + 1] - keys[i - 1][c + 1]) / (xs[i + 1] - xs[i - 1]) for c in range(dim)]
        tang.append(t)

    def f(x):
        x = max(xs[0], min(xs[-1], x))
        i = max(j for j in range(n - 1) if xs[j] <= x)
        h = xs[i + 1] - xs[i]
        s = (x - xs[i]) / h
        h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
        return [h00 * keys[i][c + 1] + h10 * h * tang[i][c] + h01 * keys[i + 1][c + 1] + h11 * h * tang[i + 1][c] for c in range(dim)]
    return f


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * x * (x * (6 * x - 15) + 10)


# (frame, azimuth deg from the front (+ = towards +X), elevation deg, distance, target x, y, z)
CAM_KEYS = [
    (1, -55.0, 14.0, 12.5, 0.6, 0.0, 0.30),
    (34, -45.0, 19.0, 13.5, 0.2, 0.0, 0.50),
    (64, -37.0, 23.0, 19.5, 0.0, 0.0, 2.9),
    (96, -27.0, 28.0, 15.5, 0.0, 0.0, 2.9),
    (124, -14.0, 38.0, 11.0, 0.0, 0.0, 3.25),
    (150, -7.0, 44.0, 9.9, 0.0, 0.0, 3.25),
]
cam_path = smooth_path(CAM_KEYS)
FOCUS_KEYS = [(1, 0.0, 0.0, 0.34), (36, 0.0, 0.0, 0.34), (78, 0.0, 0.0, 3.25), (150, 0.0, 0.0, 3.25)]
focus_path = smooth_path(FOCUS_KEYS)


def cam_pos(f):
    a, e, d, tx, ty, tz = cam_path(f)
    a, e = math.radians(a), math.radians(e)
    return (Vector((tx, ty, tz)) + Vector((d * math.cos(e) * math.sin(a), -d * math.cos(e) * math.cos(a), d * math.sin(e))), Vector((tx, ty, tz)),
            a)


tick("camera")
# =========================================================================== exploded-view animation (groups move; every frame is keyed)
EXPLODE = {  # group: (final rise, start frame, frames, later extra rise, tilt in degrees)
    G_INT: (1.5, 40, 50, 0.0, 0.0),
    G_DIE: (3.0, 36, 52, 0.0, 0.0),
    G_TIM: (4.5, 32, 54, 6.5, -6.0),
    G_LID: (6.0, 28, 56, 8.0, 7.0),
}
HBM_T0, HBM_DUR = 92.0, 26.0           # the memory stacks come apart from this frame on (top die first)
QUICK = os.environ.get("QUICK", "0") == "1" and not ANCHORS_OUT
BAKE = sorted({min(N_FRAMES, max(1, f + d)) for f in FRAMES for d in (-1, 0, 1)}) if QUICK else list(range(1, N_FRAMES + 1))
for f in BAKE:
    scene.frame_set(f)
    for g, (rise, f0, dur, extra, tilt) in EXPLODE.items():
        k = ease((f - f0) / dur)
        z = rise * k + extra * ease((f - 78) / 44.0)
        g.location = (0, 0, z)
        g.rotation_euler = (0, 0, math.radians(tilt) * k)
        g.keyframe_insert("location", frame=f)
        g.keyframe_insert("rotation_euler", frame=f)
    pos, tgt, a = cam_pos(f)
    cam.location = pos
    cam.keyframe_insert("location", frame=f)
    target.location = tgt
    target.keyframe_insert("location", frame=f)
    fx, fy, fz = focus_path(f)
    focus.location = (fx, fy, fz + (0.0 if f > 70 else EXPLODE[G_LID][0] * ease((f - 28) / 56)))
    focus.keyframe_insert("location", frame=f)
    RIG.rotation_euler = (0, 0, a * 0.55)
    RIG.keyframe_insert("rotation_euler", frame=f)
    SWEEP.location = (-9.0 + 18.0 * ease(f / 46.0), 5.0, 4.0)
    SWEEP.keyframe_insert("location", frame=f)
    SWEEP.data.energy = 6500 * (1.0 - ease((f - 30) / 14.0))
    SWEEP.data.keyframe_insert("energy", frame=f)
    for bm_mat, vm_, vs_ in BLOCK_MATS:
        vm_.outputs[0].default_value = ease((f - 96) / 22.0)
        vm_.outputs[0].keyframe_insert("default_value", frame=f)
        vs_.outputs[0].default_value = -1.6 + 3.5 * ((f - 98) / 44.0)
        vs_.outputs[0].keyframe_insert("default_value", frame=f)
    if QUICK or 88 <= f <= 132 or f in (1, N_FRAMES):          # the memory stacks only move here; elsewhere the keys would add nothing
        top_open = 0.0
        for lay, k, zc in HBM_LAYERS:
            e_ = ease((f - (HBM_T0 + (7 - k) * 1.2)) / HBM_DUR)
            lay.location.z = zc + (k + 1) * HBM_GAP * e_
            lay.keyframe_insert("location", frame=f)
            if k == 7:
                top_open = (k + 1) * HBM_GAP * e_
        for colobj, h_full in HBM_COLS:
            colobj.scale.z = max(0.0001, ((Z_L0 + 7 * LAYER_P + top_open) - 0.147) / h_full)
            colobj.keyframe_insert("scale", frame=f)
tick("bake")
scene.frame_set(1)
for ob in bpy.data.objects:
    ad = ob.animation_data
    if ad and ad.action:
        for fc in ad.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
for cu_ in bpy.data.curves:
    ad_ = cu_.animation_data
    if ad_ and ad_.action:
        for fc in ad_.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
for dat in [SWEEP.data] + [bm_[0].node_tree for bm_ in BLOCK_MATS]:
    ad = dat.animation_data
    if ad and ad.action:
        for fc in ad.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"

# =========================================================================== label anchors -> screen positions per frame (for the 2D layer)
scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
if ANCHORS_OUT:
    out = {}
    for f in range(1, N_FRAMES + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        row = {}
        for nm, e in ANCHORS.items():
            p = world_to_camera_view(scene, cam, e.matrix_world.translation)
            row[nm] = [round(p.x * 1080, 1), round((1.0 - p.y) * 1920, 1), round(p.z, 3)]
        out[str(f)] = row
    os.makedirs(os.path.dirname(os.path.abspath(ANCHORS_OUT)), exist_ok=True)
    with open(ANCHORS_OUT, "w", encoding="utf-8") as fh:
        json.dump({"fps": FPS, "frames": N_FRAMES, "anchors": out}, fh, separators=(",", ":"))
    print("ANCHORS written", ANCHORS_OUT, flush=True)
    raise SystemExit(0)

# =========================================================================== render settings
scene.render.engine = "CYCLES"
cy = scene.cycles
cy.device = "CPU"
cy.samples = SAMPLES
cy.use_denoising = True
try:
    cy.denoiser = "OPENIMAGEDENOISE"
    cy.denoising_prefilter = "ACCURATE"
    cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.use_animated_seed = False
except Exception as exc:  # noqa: BLE001
    print("render setting note:", exc, flush=True)
cy.max_bounces = 7
cy.diffuse_bounces = 2
cy.glossy_bounces = 4
cy.transmission_bounces = 2
cy.sample_clamp_indirect = 5.0
cy.caustics_reflective = False
cy.caustics_refractive = False
cy.use_light_tree = False
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = 0.5
scene.render.resolution_percentage = PCT
if BORDER:
    bx0, bx1, by0, by1 = [float(v) for v in BORDER.split(",")]
    scene.render.use_border = True
    scene.render.use_crop_to_border = True
    scene.render.border_min_x, scene.render.border_max_x = bx0, bx1
    scene.render.border_min_y, scene.render.border_max_y = by0, by1
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception as exc:  # noqa: BLE001
    print("view transform note:", exc, flush=True)

scene.use_nodes = True
tree = scene.node_tree
for n in list(tree.nodes):
    tree.nodes.remove(n)
rl = tree.nodes.new("CompositorNodeRLayers")
gl = tree.nodes.new("CompositorNodeGlare")
gl.glare_type, gl.quality, gl.threshold, gl.size, gl.mix = "FOG_GLOW", "MEDIUM", 1.8, 7, -0.60
ld = tree.nodes.new("CompositorNodeLensdist")
ld.inputs["Distortion"].default_value = 0.0
ld.inputs["Dispersion"].default_value = 0.012
em = tree.nodes.new("CompositorNodeEllipseMask")
em.width, em.height = 0.95, 0.95
bl = tree.nodes.new("CompositorNodeBlur")
bl.filter_type, bl.use_relative, bl.factor_x, bl.factor_y = "GAUSS", True, 18.0, 18.0
ma = tree.nodes.new("CompositorNodeMath")
ma.operation, ma.use_clamp = "MULTIPLY", False
ma.inputs[1].default_value = 0.45
mbb = tree.nodes.new("CompositorNodeMath")
mbb.operation = "ADD"
mbb.inputs[1].default_value = 0.55
vg = tree.nodes.new("CompositorNodeMixRGB")
vg.blend_type = "MULTIPLY"
vg.inputs[0].default_value = 1.0
outn = tree.nodes.new("CompositorNodeComposite")
L = tree.links.new
L(rl.outputs["Image"], gl.inputs["Image"])
L(gl.outputs["Image"], ld.inputs["Image"])
L(em.outputs["Mask"], bl.inputs["Image"])
L(bl.outputs["Image"], ma.inputs[0])
L(ma.outputs["Value"], mbb.inputs[0])
L(ld.outputs["Image"], vg.inputs[1])
L(mbb.outputs["Value"], vg.inputs[2])
L(vg.outputs["Image"], outn.inputs["Image"])

os.makedirs(OUT_DIR, exist_ok=True)
start = time.time()
for frame in FRAMES:
    scene.frame_set(frame)
    scene.render.filepath = os.path.join(OUT_DIR, "frame_%04d.png" % frame)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print("RENDERED frame", frame, "t=%.2f" % ((frame - 1) / FPS), "size %d%% samples %d" % (PCT, cy.samples),
          "took %.1fs" % (time.time() - t0), "elapsed %.1fs" % (time.time() - start), flush=True)
print("TOTAL_RENDER_SECONDS", round(time.time() - start, 1), flush=True)
