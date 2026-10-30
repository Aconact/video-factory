"""World: the whole free-plans video as one continuous 3D set, rendered with Cycles on the CPU.

Run by .github/workflows/render.yml through: blender -b -P jobs/world/scene.py
Environment (see jobs/ACTIVE and .github/scripts/plan.py):
  FRAMES       comma list of frames to render, ranges allowed ("1-5,9"); frame f shows t = (f - 1) / 30 s
  RES_PERCENT  percentage of 1080x1920
  SAMPLES      Cycles samples per pixel
  OUT_DIR      where the PNG frames go
  SETS         optional, which sets to build: models,limits,features,catch,verdict (default all)
  TIMELINE     optional path to timeline.json (default videos/free-plans/timeline.json)

Every object is posed from the video time t by plain functions (no keyframes), so any frame can be
rendered on its own and the shards of one video agree with each other. The camera flies from set to
set; each set explains one idea with real 3D objects. Words on the objects are real extruded text.
"""
import json
import math
import os
import random
import sys
import time
import traceback

import bmesh
import bpy
from mathutils import Euler, Vector

random.seed(11)
FPS = 30
OUT_DIR = os.environ.get("OUT_DIR", "out/frames")
PCT = int(os.environ.get("RES_PERCENT", "50"))
SAMPLES = int(os.environ.get("SAMPLES", "24"))
SETS = [s for s in os.environ.get("SETS", "models,limits,features,catch,verdict").split(",") if s]
TIMELINE = os.environ.get("TIMELINE", "videos/free-plans/timeline.json")
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "jobs", "world")


def parse_frames(text):
    frames = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            a, b = token.split("-", 1)
            frames.extend(range(int(a), int(b) + 1))
        else:
            frames.append(int(token))
    return frames


FRAMES = parse_frames(os.environ.get("FRAMES", "")) or [200]
os.makedirs(OUT_DIR, exist_ok=True)
print("BLENDER", bpy.app.version_string, "frames", FRAMES[0], "to", FRAMES[-1], "count", len(FRAMES), "sets", SETS, flush=True)

# ------------------------------------------------------------------ timeline
with open(TIMELINE, encoding="utf-8") as handle:
    TL = json.load(handle)
S = {sc["id"]: sc for sc in TL["scenes"]}


def nz(text):
    return "".join(ch for ch in text.lower() if ch.isalnum())


def cue(sid, key, nth=0):
    """Start time of the nth spoken word of scene sid that begins with key."""
    k = nz(key)
    n = 0
    for w in S[sid]["words"]:
        if nz(w["w"]).startswith(k):
            if n == nth:
                return w["s"]
            n += 1
    print("cue not found", sid, key, flush=True)
    return S[sid]["start"]


# ------------------------------------------------------------------ small maths
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, a, d):
    return clamp((t - a) / d)


def ease_out(x):
    return 1.0 - (1.0 - x) ** 3


def ease_in(x):
    return x ** 3


def smooth(x):
    x = clamp(x)
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def back(x):
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (x - 1.0) ** 3 + c1 * (x - 1.0) ** 2


def lerp3(a, b, u):
    return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u)


def add3(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


# ------------------------------------------------------------------ scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
view_layer = bpy.context.view_layer

CYAN = (0.0, 0.91, 1.0)
GREEN = (0.0, 1.0, 0.24)
AMBER = (1.0, 0.45, 0.0)
ICE = (0.55, 0.95, 1.0)
WHITE = (1.0, 1.0, 1.0)
GREY = (0.62, 0.74, 0.78)
HALF_PI = math.pi / 2
FACE = (HALF_PI, 0.0, 0.0)           # a primitive's +Z then points to -Y, toward the camera
FLOOR_Z = -3.4

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0015, 0.003, 0.004, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

COLL = {}
CUR = scene.collection


def make_collection(name):
    coll = bpy.data.collections.new(name)
    scene.collection.children.link(coll)
    COLL[name] = coll
    return coll


def put_in(obj):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    CUR.objects.link(obj)
    return obj


def new_obj(name, data):
    obj = bpy.data.objects.new(name, data)
    CUR.objects.link(obj)
    return obj


def empty(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    obj = new_obj(name, None)
    obj.location = loc
    obj.rotation_euler = rot
    obj.scale = scale
    if parent is not None:
        obj.parent = parent
    return obj


def place(obj, parent, loc, rot, scale):
    obj.location = loc
    obj.rotation_euler = rot
    obj.scale = scale
    if parent is not None:
        obj.parent = parent
    return obj


# ------------------------------------------------------------------ materials
def set_input(node, name, value):
    try:
        node.inputs[name].default_value = value
    except Exception as exc:  # noqa: BLE001
        print("material input", name, "failed:", exc, flush=True)


def M_emit(name, color, strength):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.name = "EM"
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def glow(mat, strength):
    """Change how brightly a material glows (works for M_emit / M_rim and for M_body with emission)."""
    nodes = mat.node_tree.nodes
    if "EM" in nodes:
        nodes["EM"].inputs["Strength"].default_value = strength
    else:
        set_input(nodes["Principled BSDF"], "Emission Strength", strength)


def M_body(name, base=(0.03, 0.04, 0.05), metallic=0.8, rough=0.3, emit=None, emit_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    set_input(bsdf, "Base Color", (*base, 1.0))
    set_input(bsdf, "Metallic", metallic)
    set_input(bsdf, "Roughness", rough)
    if emit is not None:
        set_input(bsdf, "Emission Color", (*emit, 1.0))
        set_input(bsdf, "Emission Strength", emit_strength)
    return mat


def M_text(name, color, strength):
    """Lit white-ish text that also glows a little, so the bevel and depth still read."""
    return M_body(name, base=color, metallic=0.0, rough=0.35, emit=color, emit_strength=strength)


def M_rim(name, base, rim, rim_strength=3.0, rough=0.4, metallic=0.2, bump=0.0, bump_scale=7.0):
    """Dark surface with a bright fresnel rim; optional noise bump (craters)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    out = nt.nodes["Material Output"]
    set_input(bsdf, "Base Color", (*base, 1.0))
    set_input(bsdf, "Roughness", rough)
    set_input(bsdf, "Metallic", metallic)
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    set_input(lw, "Blend", 0.3)
    em = nt.nodes.new("ShaderNodeEmission")
    em.name = "EM"
    em.inputs["Color"].default_value = (*rim, 1.0)
    em.inputs["Strength"].default_value = rim_strength
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lw.outputs["Fresnel"], mix.inputs[0])
    nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
    nt.links.new(em.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    if bump > 0:
        noise = nt.nodes.new("ShaderNodeTexNoise")
        set_input(noise, "Scale", bump_scale)
        set_input(noise, "Detail", 6.0)
        set_input(noise, "Roughness", 0.65)
        bmp = nt.nodes.new("ShaderNodeBump")
        set_input(bmp, "Strength", bump)
        set_input(bmp, "Distance", 0.06)
        nt.links.new(noise.outputs["Fac"], bmp.inputs["Height"])
        nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# ------------------------------------------------------------------ geometry helpers
def box_mesh(name, w, d, h):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= w
        v.co.y *= d
        v.co.z *= h
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    return me


def rbox(name, w, h, d, r, mat, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), seg=4):
    """Rounded slab: w wide (x), h tall (z), d deep (y)."""
    obj = new_obj(name, box_mesh(name, w, d, h))
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = min(r, min(w, h, d) * 0.45)
    mod.segments = seg
    try:
        mod.limit_method = "NONE"
    except Exception:  # noqa: BLE001
        pass
    obj.data.materials.append(mat)
    return place(obj, parent, loc, rot, scale)


def prim(kind, mat, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), smooth=True, **kw):
    ops = bpy.ops.mesh
    if kind == "sphere":
        ops.primitive_uv_sphere_add(segments=kw.get("seg", 48), ring_count=kw.get("rings", 24), radius=kw.get("r", 1.0))
    elif kind == "ico":
        ops.primitive_ico_sphere_add(subdivisions=kw.get("sub", 1), radius=kw.get("r", 1.0))
    elif kind == "cyl":
        ops.primitive_cylinder_add(vertices=kw.get("v", 64), radius=kw.get("r", 1.0), depth=kw.get("d", 1.0))
    elif kind == "cone":
        ops.primitive_cone_add(vertices=kw.get("v", 48), radius1=kw.get("r1", 1.0), radius2=kw.get("r2", 0.0), depth=kw.get("d", 1.0))
    elif kind == "torus":
        ops.primitive_torus_add(major_radius=kw.get("R", 1.0), minor_radius=kw.get("r", 0.05),
                                major_segments=kw.get("ms", 96), minor_segments=kw.get("ns", 10))
    elif kind == "disc":
        ops.primitive_circle_add(vertices=kw.get("v", 48), radius=kw.get("r", 1.0), fill_type="NGON")
    elif kind == "plane":
        ops.primitive_plane_add(size=1.0)
    else:
        raise ValueError(kind)
    obj = put_in(bpy.context.active_object)
    if smooth:
        for poly in obj.data.polygons:
            poly.use_smooth = True
    if mat is not None:
        obj.data.materials.append(mat)
    return place(obj, parent, loc, rot, scale)


def tube(name, pts, mat, radius=0.04, closed=False, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    """A glowing tube along a polyline. pts are (x, z) pairs in the plane that faces the camera."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        if len(p) == 2:
            sp.points[i].co = (p[0], 0.0, p[1], 1.0)
        else:
            sp.points[i].co = (p[0], p[1], p[2], 1.0)
    sp.use_cyclic_u = closed
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    cu.materials.append(mat)
    obj = new_obj(name, cu)
    return place(obj, parent, loc, rot, scale)


def reveal(obj, f0, f1):
    """Show only the part f0..f1 (0..1) of a tube's length."""
    cu = obj.data
    cu.bevel_factor_start = clamp(f0)
    cu.bevel_factor_end = clamp(f1)


FONTS = {}


def font(name):
    if name not in FONTS:
        path = os.path.join(HERE, "fonts", name)
        FONTS[name] = bpy.data.fonts.load(path) if os.path.exists(path) else None
        if FONTS[name] is None:
            print("font missing", path, flush=True)
    return FONTS[name]


def text3d(name, body, size, mat, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), face="Inter-ExtraBold.ttf",
           depth=0.05, bevel=0.01, maxw=None, spacing=1.0, align="CENTER"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    fnt = font(face)
    if fnt is not None:
        cu.font = fnt
    cu.extrude = depth
    cu.bevel_depth = bevel
    cu.bevel_resolution = 2
    cu.resolution_u = 3
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.space_character = spacing
    cu.materials.append(mat)
    obj = new_obj(name, cu)
    scale = (1, 1, 1)
    if maxw:
        view_layer.update()
        width = obj.dimensions.x
        if width > maxw:
            k = maxw / width
            scale = (k, k, k)
    place(obj, parent, loc, (HALF_PI + rot[0], rot[1], rot[2]), scale)
    obj["bs"] = scale[0]
    return obj


def hide(obj, flag):
    """Hide (or show) an object together with everything parented under it."""
    obj.hide_render = flag
    for child in obj.children_recursive:
        child.hide_render = flag


def popup(obj, t, t0, dur=0.55, overshoot=True):
    """Grow an object from nothing to its own base scale (obj['bs'], default 1) starting at t0.
    Call parents before children: showing a parent shows its whole subtree again."""
    p = clamp((t - t0) / dur)
    e = back(p) if overshoot else ease_out(p)
    s = max(e, 0.001) * obj.get("bs", 1.0)
    obj.scale = (s, s, s)
    hide(obj, p <= 0.0)
    return p


# ------------------------------------------------------------------ camera, lights, floor, bokeh
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 40
cam_data.sensor_fit = "VERTICAL"
cam_data.sensor_height = 36
cam_data.shift_y = -0.10                      # subject sits above the middle; captions use the lower part
cam_data.dof.use_dof = True
cam_data.dof.aperture_fstop = 1.4
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_target = Vector((0, 0, 0))

floor_mat = M_body("Floor", base=(0.008, 0.011, 0.014), metallic=0.0, rough=0.09)
bpy.ops.mesh.primitive_plane_add(size=1.0)
floor = put_in(bpy.context.active_object)
floor.scale = (500.0, 500.0, 1.0)
floor.location = (0.0, 150.0, FLOOR_Z)
floor.data.materials.append(floor_mat)


def add_area(name, size, size_y, color, energy):
    data = bpy.data.lights.new(name, type="AREA")
    data.shape = "RECTANGLE"
    data.size = size
    data.size_y = size_y
    data.color = color
    data.energy = energy
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    return obj


LIGHT_K = float(os.environ.get("LIGHT_K", "1.0"))     # one knob to brighten or dim every light
LIGHTS = [
    (add_area("StripLeft", 0.5, 5.5, CYAN, 600 * LIGHT_K), (-3.6, -5.5, 0.8)),
    (add_area("StripRight", 0.5, 5.5, GREEN, 480 * LIGHT_K), (3.6, -5.5, -0.4)),
    (add_area("TopRim", 3.5, 0.7, ICE, 220 * LIGHT_K), (0.0, -2.5, 4.2)),
    (add_area("BottomKick", 3.0, 0.5, CYAN, 140 * LIGHT_K), (0.0, -3.0, -3.0)),
    (add_area("Fill", 6.0, 6.0, (0.85, 0.95, 1.0), 120 * LIGHT_K), (0.0, -9.0, 2.0)),
]

def M_soft(name, color, strength):
    """A soft round glow: bright in the middle, fading to see-through at the rim (looks like an out-of-focus light)."""
    try:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        grad = nt.nodes.new("ShaderNodeTexGradient")
        grad.gradient_type = "SPHERICAL"
        pw = nt.nodes.new("ShaderNodeMath")
        pw.operation = "POWER"
        pw.inputs[1].default_value = 1.5
        em = nt.nodes.new("ShaderNodeEmission")
        em.name = "EM"
        em.inputs["Color"].default_value = (*color, 1.0)
        em.inputs["Strength"].default_value = strength
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(tc.outputs["Object"], grad.inputs["Vector"])
        nt.links.new(grad.outputs["Fac"], pw.inputs[0])
        nt.links.new(pw.outputs["Value"], mix.inputs[0])
        nt.links.new(tr.outputs["BSDF"], mix.inputs[1])
        nt.links.new(em.outputs["Emission"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
        return mat
    except Exception as exc:  # noqa: BLE001
        print("soft material failed, using a flat one:", exc, flush=True)
        return M_emit(name, color, strength * 0.5)


bokeh_mats = [M_soft("Bokeh%d" % i, c, s) for i, (c, s) in enumerate(
    [(CYAN, 5.0), (CYAN, 4.0), (GREEN, 4.5), (AMBER, 4.0), (ICE, 5.0)])]
BOKEH = []
CUR = scene.collection
for n in range(80):
    fy = random.uniform(16.0, 48.0)
    x = random.uniform(-0.27, 0.27) * fy * 1.15
    z = random.uniform(-0.1, 0.5) * fy * 1.15
    big = n % 8 == 0
    r = random.uniform(0.05, 0.16) * (fy / 20.0) * (2.6 if big else 1.0)
    bpy.ops.mesh.primitive_circle_add(vertices=32, radius=1.0, fill_type="NGON", rotation=FACE)
    obj = put_in(bpy.context.active_object)
    obj.scale = (r, r, r)
    obj.data.materials.append(random.choice(bokeh_mats))
    BOKEH.append((obj, x, fy, z, random.uniform(0.1, 0.5)))

# ------------------------------------------------------------------ the sets
UPDATES = []        # (name, t_from, t_to, collection, update(t))


def begin_set(name):
    global CUR
    CUR = make_collection("S_" + name)
    return CUR


def label(name, body, color, parent, loc, size=0.3, spacing=1.5, strength=2.6):
    return text3d(name, body, size, M_text(name, color, strength), parent=parent, loc=loc,
                  face="JetBrainsMono-Bold.ttf", depth=0.03, bevel=0.006, spacing=spacing)


def big_text(name, body, size, color, parent, loc, strength=1.2, maxw=None, face="Inter-ExtraBold.ttf", depth=0.07):
    return text3d(name, body, size, M_text(name, color, strength), parent=parent, loc=loc,
                  face=face, depth=depth, bevel=0.012, maxw=maxw)


def emblem_chatgpt(name, parent, loc, k=1.0):
    root = empty(name, parent, loc, scale=(k, k, k))
    moon_mat = M_rim(name + "Moon", (0.03, 0.07, 0.05), GREEN, 2.4, rough=0.6, metallic=0.0, bump=0.55, bump_scale=6.0)
    moon = prim("sphere", moon_mat, root, (0, 0, 0), r=1.0, seg=64, rings=32)
    ring_mat = M_emit(name + "Ring", GREEN, 6.0)
    ring = prim("torus", ring_mat, root, (0, 0, 0), (1.25, 0.0, 0.3), R=1.55, r=0.03, ms=128, ns=8)
    ring2 = prim("torus", M_emit(name + "Ring2", CYAN, 2.5), root, (0, 0, 0), (0.55, 0.0, -0.5), R=1.9, r=0.015, ms=128, ns=8)
    return root, moon, ring, ring2


def emblem_claude(name, parent, loc, k=1.0):
    root = empty(name, parent, loc, scale=(k, k, k))
    big_mat = M_rim(name + "Big", (0.5, 0.2, 0.02), AMBER, 3.2, rough=0.28, metallic=0.9)
    big = prim("sphere", big_mat, root, (0, 0, 0), r=0.9, seg=64, rings=32)
    orbit = empty(name + "Orbit", root, (0, 0, 0), (0.9, 0.0, 0.25))
    small_mat = M_rim(name + "Small", (0.7, 0.35, 0.05), (1.0, 0.8, 0.3), 3.0, rough=0.25, metallic=0.9)
    small = prim("sphere", small_mat, orbit, (1.6, 0, 0), r=0.42, seg=48, rings=24)
    track = prim("torus", M_emit(name + "Track", AMBER, 1.6), orbit, (0, 0, 0), (0, 0, 0), R=1.6, r=0.012, ms=128, ns=6)
    return root, big, orbit, small, track


def emblem_gemini(name, parent, loc, k=1.0):
    root = empty(name, parent, loc, scale=(k, k, k))
    gem_mat = M_rim(name + "Gem", (0.0, 0.18, 0.22), CYAN, 4.0, rough=0.15, metallic=0.6)
    gem = prim("ico", gem_mat, root, (0, 0, 0), (0.0, 0.0, 0.0), smooth=False, r=1.05, sub=1)
    core = prim("ico", M_emit(name + "Core", ICE, 4.0), root, (0, 0, 0), smooth=False, r=0.42, sub=1)
    halo = prim("torus", M_emit(name + "Halo", CYAN, 3.0), root, (0, 0, 0), (1.45, 0.0, 0.0), R=1.55, r=0.018, ms=128, ns=6)
    return root, gem, core, halo


# ---------------------------------------------------------------- set 1: the models
def build_models():
    begin_set("models")
    O = (0.0, 0.0, 0.0)
    root = empty("models", None, O)
    # ChatGPT: a moon (GPT-6 Luna) with orbit rings
    A = empty("A", root, (0, 0, 0))
    a_lab = label("a_lab", "CHATGPT", GREEN, A, (0, 0, 2.15))
    a_emb, a_moon, a_ring, a_ring2 = emblem_chatgpt("a_emb", A, (0, 0, 0.55))
    a_name = big_text("a_name", "GPT-6 Luna", 0.58, WHITE, A, (0, 0, -1.05), maxw=3.9)
    a_sub = text3d("a_sub", "default for Free and Go", 0.2, M_text("a_sub", GREY, 0.9), parent=A, loc=(0, 0, -1.62),
                   face="Inter-SemiBold.ttf", depth=0.02, bevel=0.004)
    # Claude: two models (Sonnet and Haiku) orbiting
    B = empty("B", root, (5.5, 8.0, 0))
    b_lab = label("b_lab", "CLAUDE", AMBER, B, (0, 0, 2.15))
    b_emb, b_big, b_orbit, b_small, b_track = emblem_claude("b_emb", B, (0, 0, 0.55))
    b_name = big_text("b_name", "Sonnet + Haiku", 0.52, WHITE, B, (0, 0, -1.05), maxw=3.9)
    # Gemini: a gem (Flash-Lite), a staircase (Auto steps up) to a locked monolith (Argon)
    C = empty("C", root, (-5.5, 16.0, 0))
    c_lab = label("c_lab", "GEMINI", CYAN, C, (0, 0, 2.15))
    c_emb, c_gem, c_core, c_halo = emblem_gemini("c_emb", C, (0, 0, 0.55))
    c_name = big_text("c_name", "Flash-Lite", 0.58, WHITE, C, (0, 0, -1.05), maxw=3.9)
    c_auto = label("c_auto", "AUTO", CYAN, root, (-3.7, 20.0, 0.6), size=0.34, spacing=1.8)
    steps = []
    n_steps = 6
    for i in range(n_steps):
        u = i / (n_steps - 1)
        pos = lerp3((-4.4, 19.8, -1.2), (-0.9, 26.6, 1.5), u)
        yaw = math.atan2(26.6 - 19.8, -0.9 + 4.4) - HALF_PI
        mat = M_body("step%d" % i, base=(0.02, 0.07, 0.09), metallic=0.5, rough=0.3, emit=CYAN, emit_strength=0.2)
        stp = rbox("step%d" % i, 1.6, 0.16, 1.0, 0.05, mat, root, pos, (0, 0, yaw))
        steps.append((stp, mat))
    # Argon: a big dark crystal behind a padlock
    D = empty("D", root, (0.0, 30.0, 2.4))
    d_mat = M_rim("argon", (0.02, 0.03, 0.04), CYAN, 0.5, rough=0.2, metallic=0.9)
    d_gem = prim("ico", d_mat, D, (0, 0, 0.6), smooth=False, r=1.55, sub=1)
    d_name = big_text("d_name", "ARGON", 0.72, (0.55, 0.62, 0.66), D, (0, 0, -1.0), strength=0.5, maxw=3.6)
    lock = empty("lock", D, (0, -1.9, 0.3))
    lock_body = rbox("lock_body", 0.9, 0.7, 0.34, 0.1, M_body("lockb", base=(0.9, 0.35, 0.02), metallic=0.9, rough=0.25,
                                                       emit=AMBER, emit_strength=0.5), lock, (0, 0, -0.2))
    arc = [(0.3 * math.cos(math.pi * i / 24), 0.0, 0.3 * math.sin(math.pi * i / 24)) for i in range(25)]
    lock_arc = tube("lock_arc", arc, M_body("locka", base=(0.9, 0.35, 0.02), metallic=0.9, rough=0.25), 0.07, False, lock, (0, 0, 0.1))
    d_badge = label("d_badge", "PAID ONLY", AMBER, D, (0, 0, -1.75), size=0.34, spacing=1.6)

    t_a, t_b, t_c, t_d = cue("models", "gpt6"), cue("models", "sonnet"), cue("models", "flashlite"), cue("models", "argon")
    t_auto, t_paid = cue("models", "auto"), cue("models", "paid")

    def update(t):
        # ChatGPT
        popup(A, t, 3.2, 0.8)
        popup(a_lab, t, cue("models", "chatgpt"), 0.5)
        popup(a_name, t, t_a - 0.05, 0.55)
        popup(a_sub, t, cue("models", "luna") - 0.2, 0.5, overshoot=False)
        a_ring.rotation_euler = (1.25, 0.0, 0.3 + 0.35 * t)
        a_ring2.rotation_euler = (0.55, 0.0, -0.5 - 0.22 * t)
        a_moon.rotation_euler = (0.0, 0.0, 0.12 * t)
        # Claude
        popup(B, t, 7.0, 0.8)
        popup(b_lab, t, cue("models", "claude"), 0.5)
        popup(b_name, t, t_b - 0.05, 0.55)
        b_orbit.rotation_euler = (0.9, 0.0, 0.25 + 0.9 * t)
        b_small.scale = tuple([max(back(prog(t, cue("models", "haiku") - 0.1, 0.6)), 0.001)] * 3)
        # Gemini
        popup(C, t, 9.5, 0.8)
        popup(c_lab, t, cue("models", "gemini"), 0.5)
        popup(c_name, t, t_c - 0.05, 0.55)
        c_gem.rotation_euler = (0.0, 0.0, 0.25 * t)
        c_halo.rotation_euler = (1.45, 0.0, -0.4 * t)
        popup(c_auto, t, t_auto - 0.1, 0.5)
        k_i = clamp((t - (t_auto + 0.15)) / 0.3, 0.0, n_steps - 1.0)
        c_auto.location = add3(lerp3((-4.4, 19.8, -1.2), (-0.9, 26.6, 1.5), k_i / (n_steps - 1.0)), (-0.2, -0.2, 1.0))
        for i, (stp, mat) in enumerate(steps):
            on = ease_out(prog(t, t_auto + 0.15 + i * 0.3, 0.4))
            glow(mat, 0.2 + 4.0 * on)
            stp.hide_render = t < 9.5
        # Argon
        popup(D, t, 14.0, 0.9)
        popup(d_name, t, t_d - 0.05, 0.55)
        d_gem.rotation_euler = (0.0, 0.0, -0.15 * t)
        flare = ease_out(prog(t, t_d, 0.6)) * (1.0 - 0.8 * ease_out(prog(t, t_d + 0.6, 0.8)))
        glow(d_mat, 0.5 + 5.0 * flare)
        lp = prog(t, t_paid - 0.1, 0.45)
        lock.scale = tuple([max(back(lp), 0.001) * (1.0 + 1.5 * (1 - ease_out(lp)))] * 3)
        hide(lock, lp <= 0)
        popup(d_badge, t, cue("models", "only") - 0.1, 0.45)

    UPDATES.append(("models", 2.5, 17.5, COLL["S_models"], update))


# ---------------------------------------------------------------- set 2: the limits
def lemniscate(a, n=180):
    pts = []
    for i in range(n):
        u = 2 * math.pi * i / n
        den = 1 + math.sin(u) ** 2
        pts.append((a * math.cos(u) / den, 0.0, a * math.sin(u) * math.cos(u) / den))
    return pts


def lemni_at(a, u):
    den = 1 + math.sin(u) ** 2
    return (a * math.cos(u) / den, 0.0, a * math.sin(u) * math.cos(u) / den)


def ring_pts(R, n=120):
    pts = []
    for i in range(n):
        th = HALF_PI - 2 * math.pi * i / n
        pts.append((R * math.cos(th), 0.0, R * math.sin(th)))
    return pts


def build_limits():
    begin_set("limits")
    root = empty("limits", None, (0.0, 44.0, 0.0))
    # --- ChatGPT: an endless stream of chat bubbles, then three capped doors
    L1 = empty("L1", root, (0, 0, 0))
    inf_mat = M_emit("inf", GREEN, 5.0)
    inf = tube("inf", lemniscate(1.55), inf_mat, 0.055, True, L1, (0, 0, 1.45))
    bubbles = []
    for i in range(14):
        user = i % 2 == 0
        mat = M_body("bub%d" % i, base=(0.02, 0.2, 0.08) if user else (0.2, 0.25, 0.28), metallic=0.3, rough=0.35,
                     emit=GREEN if user else GREY, emit_strength=1.4 if user else 0.5)
        b = rbox("bub%d" % i, 0.46 if user else 0.58, 0.26, 0.09, 0.07, mat, L1, (0, 0, 1.45))
        bubbles.append((b, i / 14.0))
    unl = big_text("unl", "UNLIMITED", 0.64, WHITE, L1, (0, 0, -0.2), strength=1.4, maxw=3.9)
    txt = text3d("txt", "text chats", 0.3, M_text("txt", GREY, 1.0), parent=L1, loc=(0, 0, -0.78),
                 face="Inter-SemiBold.ttf", depth=0.02, bevel=0.004)
    gates = []
    gate_names = ["FILES", "IMAGES", "VOICE"]
    gate_cues = [cue("limits", "files"), cue("limits", "images"), cue("limits", "voice")]
    for i, nm in enumerate(gate_names):
        x = (i - 1) * 1.5
        g = empty("gate" + nm, L1, (x, 0, -1.65))
        rbox("slab" + nm, 1.28, 0.7, 0.12, 0.08, M_body("slab" + nm, base=(0.03, 0.05, 0.06), metallic=0.6, rough=0.3,
                                                         emit=ICE, emit_strength=0.1), g, (0, 0, 0))
        tube("frame" + nm, [(-0.62, -0.32), (0.62, -0.32), (0.62, 0.32), (-0.62, 0.32)], M_emit("fr" + nm, ICE, 1.6), 0.014, True, g, (0, -0.08, 0))
        label("lab" + nm, nm, WHITE, g, (0, -0.1, 0.0), size=0.2, spacing=1.3, strength=2.4)
        bar_mat = M_emit("bar" + nm, AMBER, 3.6)
        bar = rbox("bar" + nm, 1.4, 0.13, 0.16, 0.04, bar_mat, g, (0, -0.16, 0.5))
        gates.append((g, bar))
    stamp = empty("stamp", L1, (0, 0, -2.3), (0, 0, 0.0))
    stamp_txt = label("stamp_t", "STILL CAPPED", AMBER, stamp, (0, 0, 0), size=0.32, spacing=1.5, strength=3.2)
    stamp_box = tube("stamp_b", [(-1.55, -0.28), (1.55, -0.28), (1.55, 0.28), (-1.55, 0.28)], M_emit("stampb", AMBER, 3.0), 0.02, True, stamp, (0, 0.0, 0))

    # --- Claude and Gemini: five-hour rings; Gemini adds a weekly cap
    L2 = empty("L2", root, (0, 12.0, 0))
    rings = {}
    for key, x, color, name in (("claude", -1.5, AMBER, "CLAUDE"), ("gemini", 1.5, CYAN, "GEMINI")):
        g = empty("ring_" + key, L2, (x, 0, 0.55))
        label("rl_" + key, name, color, g, (0, 0, 1.85), size=0.28, spacing=1.7)
        track = tube("track_" + key, ring_pts(1.05), M_emit("tr_" + key, color, 0.5), 0.06, True, g, (0, 0, 0))
        arc_mat = M_emit("arc_" + key, color, 5.0)
        arc = tube("arc_" + key, ring_pts(1.05), arc_mat, 0.11, True, g, (0, -0.03, 0))
        for k in range(5):
            th = HALF_PI - 2 * math.pi * k / 5
            tick = rbox("tick%d_%s" % (k, key), 0.06, 0.26, 0.06, 0.02, M_emit("tk%d%s" % (k, key), WHITE, 2.0), g,
                        (1.32 * math.cos(th), 0, 1.32 * math.sin(th)), (0, 0, th - HALF_PI))
        five = big_text("five_" + key, "5H", 0.62, WHITE, g, (0, -0.05, 0.02), strength=1.5)
        sub = text3d("rs_" + key, "reset", 0.24, M_text("rs_" + key, GREY, 1.0), parent=g, loc=(0, 0, -1.62),
                     face="Inter-SemiBold.ttf", depth=0.02, bevel=0.004)
        rings[key] = (g, arc, arc_mat, five)
    week = []
    wk_root = empty("week", L2, (1.5, 0, -1.12))
    label("wk_lab", "WEEKLY CAP", AMBER, wk_root, (0, 0, -0.5), size=0.2, spacing=1.5, strength=2.4)
    for i in range(7):
        last = i == 6
        mat = M_emit("wk%d" % i, AMBER if last else CYAN, 0.2)
        b = rbox("wk%d" % i, 0.27, 0.27, 0.1, 0.05, mat, wk_root, ((i - 3) * 0.36, 0, 0.0))
        week.append((b, mat, last))

    t_inf = cue("limits", "chatgpt")
    t_unl, t_txt = cue("limits", "unlimited"), cue("limits", "text")
    t_cap = cue("limits", "capped")
    t_cl, t_ge = cue("limits", "claude"), cue("limits", "gemini")
    t_week = cue("limits", "weekly")

    def update(t):
        popup(L1, t, 16.0, 0.6)
        draw = ease_out(prog(t, t_inf, 1.5))
        reveal(inf, 0.0, draw)
        inf.hide_render = draw <= 0
        for b, phase in bubbles:
            vis = ease_out(prog(t, t_inf + 0.5 + phase * 1.8, 0.4))
            u = 2 * math.pi * ((phase + 0.11 * t) % 1.0)
            x, y, z = lemni_at(1.55, u)
            b.location = (x, -0.1, z + 1.45)
            b.scale = (vis, vis, vis)
            b.hide_render = vis <= 0.001
        popup(unl, t, t_unl - 0.05, 0.5)
        popup(txt, t, t_txt - 0.05, 0.5, overshoot=False)
        for (g, bar), tc in zip(gates, gate_cues):
            popup(g, t, tc - 0.1, 0.45)
        for i, (g, bar) in enumerate(gates):
            drop = ease_out(prog(t, t_cap + 0.1 * i, 0.4))
            bar.location = (0, -0.16, 0.5 - 0.5 * drop)
            bar.hide_render = drop <= 0.01
        popup(stamp, t, t_cap + 0.15, 0.4)
        # rings
        for key, tc in (("claude", t_cl), ("gemini", t_ge)):
            g, arc, arc_mat, five = rings[key]
            popup(g, t, tc - 0.1, 0.55)
            fill = ease_out(prog(t, cue("limits", "reset") - 0.2, 1.7))
            reveal(arc, 0.0, max(fill, 0.02))
            pulse = ease_out(prog(t, cue("limits", "hours") - 0.05, 0.25)) * (1 - ease_out(prog(t, cue("limits", "hours") + 0.2, 0.6)))
            glow(arc_mat, 5.0 + 9.0 * pulse)
            g.rotation_euler = (0.0, 0.0, 0.0)
        popup(wk_root, t, t_week - 0.2, 0.4)
        for i, (b, mat, last) in enumerate(week):
            on = ease_out(prog(t, t_week - 0.05 + 0.09 * i, 0.25))
            glow(mat, 0.2 + (5.0 if last else 3.2) * on)

    UPDATES.append(("limits", 15.5, 31.5, COLL["S_limits"], update))


# ---------------------------------------------------------------- set 3: the features (neon icons)
def arc_pts(cx, cz, r, a0, a1, n=24):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def icon_paths(kind):
    """Polylines of a line icon in a [-1, 1] box: list of (points, closed)."""
    if kind == "mic":
        cap = [(0.28, 0.2)] + arc_pts(0, 0.62, 0.28, 0, 180, 16)[0:] + [(-0.28, 0.2)] + arc_pts(0, 0.2, 0.28, 180, 360, 16)
        return [(cap, True), (arc_pts(0, 0.2, 0.52, 195, 345, 20), False), ([(0, -0.32), (0, -0.78)], False), ([(-0.3, -0.78), (0.3, -0.78)], False)]
    if kind == "think":
        return [([(0, 0.95), (0.2, 0.2), (0.95, 0), (0.2, -0.2), (0, -0.95), (-0.2, -0.2), (-0.95, 0), (-0.2, 0.2)], True)]
    if kind == "clock":
        return [(arc_pts(0, 0, 0.85, 0, 360, 40)[:-1], True), ([(0, 0.5), (0, 0), (0.38, -0.22)], False)]
    if kind == "cube":
        return [([(0, 0.9), (0.78, 0.45), (0.78, -0.45), (0, -0.9), (-0.78, -0.45), (-0.78, 0.45)], True),
                ([(-0.78, 0.45), (0, 0), (0.78, 0.45)], False), ([(0, 0), (0, -0.9)], False)]
    if kind == "folder":
        return [([(-0.9, 0.55), (-0.3, 0.55), (-0.1, 0.3), (0.9, 0.3), (0.9, -0.6), (-0.9, -0.6)], True)]
    if kind == "chip":
        paths = [([(-0.5, 0.5), (0.5, 0.5), (0.5, -0.5), (-0.5, -0.5)], True), ([(-0.2, 0.2), (0.2, 0.2), (0.2, -0.2), (-0.2, -0.2)], True)]
        for k in (-0.3, 0.0, 0.3):
            paths += [([(k, 0.5), (k, 0.82)], False), ([(k, -0.5), (k, -0.82)], False),
                      ([(0.5, k), (0.82, k)], False), ([(-0.5, k), (-0.82, k)], False)]
        return paths
    if kind == "search":
        return [(arc_pts(-0.15, 0.15, 0.58, 0, 360, 36)[:-1], True), ([(0.27, -0.27), (0.85, -0.85)], False), ([(-0.4, 0.15), (0.1, 0.15)], False)]
    if kind == "image":
        return [([(-0.85, -0.65), (0.85, -0.65), (0.85, 0.65), (-0.85, 0.65)], True), (arc_pts(-0.4, 0.27, 0.15, 0, 360, 16)[:-1], True),
                ([(-0.85, -0.45), (-0.3, 0.0), (0.1, -0.3), (0.42, -0.05), (0.85, -0.45)], False)]
    raise ValueError(kind)


def make_icon(name, kind, color, parent, loc, size=0.62, strength=4.5):
    root = empty(name, parent, loc)
    mat = M_emit(name + "_m", color, strength)
    for i, (pts, closed) in enumerate(icon_paths(kind)):
        scaled = [(p[0] * size, p[1] * size) for p in pts]
        tube("%s_%d" % (name, i), scaled, mat, 0.036, closed, root, (0, 0, 0))
    return root, mat


def build_features():
    begin_set("features")
    root = empty("features", None, (0.0, 70.0, 0.0))
    clusters = [
        ("chatgpt", "CHATGPT", GREEN, (0.0, 0.0, 0.0), [("voice", "mic", "Voice"), ("think", "think", "Think button"), ("scheduled", "clock", "Scheduled tasks")]),
        ("claude", "CLAUDE", AMBER, (5.5, 9.0, 0.0), [("artifacts", "cube", "Artifacts"), ("projects", "folder", "Projects"), ("memory", "chip", "Memory")]),
        ("gemini", "GEMINI", CYAN, (-5.5, 18.0, 0.0), [("deep", "search", "Deep Research"), ("image", "image", "Image generation")]),
    ]
    items = []
    cluster_roots = []
    for key, name, color, pos, feats in clusters:
        c = empty("c_" + key, root, pos)
        lab = label("cl_" + key, name, color, c, (0, 0, 2.1), size=0.3, spacing=1.7)
        n = len(feats)
        xs = [(i - (n - 1) / 2.0) * (1.5 if n == 3 else 1.75) for i in range(n)]
        for (cue_key, kind, text), x in zip(feats, xs):
            g = empty("f_" + cue_key, c, (x, 0, 0.0))
            ped = prim("cyl", M_body("ped_" + cue_key, base=(0.02, 0.03, 0.04), metallic=0.8, rough=0.25), g, (0, 0, -0.78), FACE, r=0.58, d=0.09, v=64)
            prim("torus", M_emit("pr_" + cue_key, color, 3.0), g, (0, -0.02, -0.78), FACE, R=0.58, r=0.014, ms=96, ns=6)
            icon, mat = make_icon("ic_" + cue_key, kind, color, g, (0, 0, 0.1))
            tx = big_text("tx_" + cue_key, text, 0.27 if len(text) < 12 else 0.23, WHITE, g, (0, 0, -1.3), strength=1.2, maxw=1.5 if n == 3 else 1.7)
            items.append((cue_key, g, icon, mat, tx, color))
        cluster_roots.append((key, c, lab, name))
    t_feat = {"voice": cue("features", "voice"), "think": cue("features", "think"), "scheduled": cue("features", "scheduled"),
              "artifacts": cue("features", "artifacts"), "projects": cue("features", "projects"), "memory": cue("features", "memory"),
              "deep": cue("features", "deep"), "image": cue("features", "image")}
    t_cluster = {"chatgpt": 30.0, "claude": cue("features", "claude") - 0.6, "gemini": cue("features", "gemini") - 0.6}

    def update(t):
        for key, c, lab, name in cluster_roots:
            popup(c, t, t_cluster[key], 0.6)
        for cue_key, g, icon, mat, tx, color in items:
            p = popup(g, t, t_feat[cue_key] - 0.1, 0.6)
            icon.rotation_euler = (0.0, 0.0, 0.5 * math.sin(1.1 * t + len(cue_key)))
            glow(mat, 4.5 + 3.0 * (1 - ease_out(prog(t, t_feat[cue_key], 0.7))))

    UPDATES.append(("features", 29.5, 43.5, COLL["S_features"], update))


# ---------------------------------------------------------------- set 4: the catch (ads)
def build_catch():
    begin_set("catch")
    root = empty("catch", None, (0.0, 104.0, 0.0))
    tri = [(0, 0.5), (0.5, -0.38), (-0.5, -0.38)]
    warn = empty("warn", root, (-1.75, 0, 2.2))
    tube("warn_t", tri, M_emit("warn", AMBER, 4.0), 0.035, True, warn)
    tube("warn_b", [(0, 0.2), (0, -0.08)], M_emit("warn2", AMBER, 4.0), 0.035, False, warn)
    tag = label("tag", "ONE CATCH", AMBER, root, (0.4, 0, 2.2), size=0.34, spacing=1.7, strength=3.2)
    ads = big_text("ads", "ADS", 1.9, AMBER, root, (0, 0, 1.1), strength=2.2, maxw=3.9, depth=0.16)
    sub = text3d("csub", "ChatGPT Free tier", 0.36, M_text("csub", WHITE, 1.0), parent=root, loc=(0, 0, 0.0),
                 face="Inter-SemiBold.ttf", depth=0.02, bevel=0.004)
    small = label("csub2", "ROLLING OUT IN SOME COUNTRIES", GREY, root, (0, 0, -0.42), size=0.19, spacing=1.3, strength=1.6)
    shock_mat = M_emit("shock", AMBER, 6.0)
    shock = prim("torus", shock_mat, root, (0, 0.5, 1.1), FACE, R=1.0, r=0.03, ms=128, ns=8)
    # a tiny chat: a question, an answer, then an ad that pushes in
    chat = empty("chat", root, (0, 0, -1.3))
    u = rbox("bu", 1.7, 0.3, 0.1, 0.09, M_body("bu", base=(0.02, 0.2, 0.08), metallic=0.3, rough=0.35, emit=GREEN, emit_strength=1.3), chat, (0.95, 0, 0.5))
    a = rbox("ba", 2.5, 0.3, 0.1, 0.09, M_body("ba", base=(0.2, 0.25, 0.28), metallic=0.3, rough=0.35, emit=GREY, emit_strength=0.5), chat, (-0.65, 0, 0.1))
    adc = empty("adc", chat, (0, 0, -0.55))
    dash = []
    w, h = 3.2, 0.62
    perim = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    for i in range(4):
        p0, p1 = perim[i], perim[(i + 1) % 4]
        n = 9 if i % 2 == 0 else 2
        for k in range(n):
            a0 = (k + 0.15) / n
            a1 = (k + 0.75) / n
            tube("dash%d_%d" % (i, k), [(p0[0] + (p1[0] - p0[0]) * a0, p0[1] + (p1[1] - p0[1]) * a0),
                                        (p0[0] + (p1[0] - p0[0]) * a1, p0[1] + (p1[1] - p0[1]) * a1)],
                 M_emit("dash%d_%d" % (i, k), AMBER, 3.0), 0.02, False, adc, (0, 0, 0))
    ad_badge = label("adtxt", "AD", (0.04, 0.03, 0.0), adc, (1.35, -0.1, 0.0), size=0.26, spacing=1.2, strength=0.0)
    badge_bg = rbox("adbg", 0.5, 0.3, 0.06, 0.05, M_emit("adbg", AMBER, 3.0), adc, (1.35, -0.05, 0.0))
    for i, y in enumerate((0.1, 0.0)):
        rbox("adl%d" % i, 1.6 if i == 0 else 1.0, 0.09, 0.05, 0.03, M_emit("adl%d" % i, GREY, 1.0), adc, (-0.65 + (0 if i == 0 else -0.3), -0.04, 0.1 - 0.2 * i))

    t_tag, t_ads, t_ct = cue("catch", "catch"), cue("catch", "ads"), cue("catch", "countries")
    t_sub = cue("catch", "chatgpt")

    def update(t):
        popup(warn, t, t_tag - 0.1, 0.4)
        popup(tag, t, t_tag - 0.05, 0.45)
        popup(sub, t, t_sub, 0.5, overshoot=False)
        popup(small, t, t_sub + 0.3, 0.5, overshoot=False)
        p = clamp((t - (t_ads - 0.05)) / 0.5)
        k = 1.0 + 1.6 * (1 - ease_out(p))
        sc_ads = max(p, 0.001) * k * ads.get("bs", 1.0)
        ads.scale = (sc_ads, sc_ads, sc_ads)
        ads.hide_render = p <= 0
        sp = prog(t, t_ads, 0.9)
        shock.scale = (0.4 + 5.0 * ease_out(sp),) * 3
        glow(shock_mat, 7.0 * (1 - sp))
        shock.hide_render = sp <= 0 or sp >= 1
        popup(chat, t, t_sub + 0.9, 0.5)
        p_ad = prog(t, t_ct - 0.9, 0.6)
        adc.location = (0, 0, -0.55 + 0.5 * (1 - ease_out(p_ad)))
        hide(adc, p_ad <= 0)

    UPDATES.append(("catch", 41.0, 48.5, COLL["S_catch"], update))


# ---------------------------------------------------------------- set 5: our take (podiums)
def build_verdict():
    begin_set("verdict")
    root = empty("verdict", None, (0.0, 120.0, 0.0))
    pods = []
    defs = [
        ("chatgpt", GREEN, (-4.2, 0.0, 0.0), "Chatting all day?", "ChatGPT", cue("verdict", "chatting"), cue("verdict", "chatgpt")),
        ("claude", AMBER, (0.0, 6.5, 0.0), "Building things?", "Claude", cue("verdict", "building"), cue("verdict", "claude")),
        ("gemini", CYAN, (4.2, 13.0, 0.0), "Research and images?", "Gemini", cue("verdict", "research"), cue("verdict", "gemini")),
    ]
    for key, color, pos, question, answer, t_q, t_a in defs:
        g = empty("p_" + key, root, pos)
        base = prim("cyl", M_body("pb_" + key, base=(0.02, 0.03, 0.04), metallic=0.8, rough=0.22), g, (0, 0, -1.55), FACE, r=1.15, d=0.75, v=72)
        top_mat = M_emit("pt_" + key, color, 0.4)
        top = prim("cyl", top_mat, g, (0, -0.4, -1.55), FACE, r=1.0, d=0.03, v=72)
        ring_mat = M_emit("pr_" + key, color, 0.6)
        ring = prim("torus", ring_mat, g, (0, -0.4, -1.55), FACE, R=1.15, r=0.025, ms=96, ns=6)
        if key == "chatgpt":
            em = emblem_chatgpt("e_" + key, g, (0, -0.2, 0.05), 0.55)
        elif key == "claude":
            em = emblem_claude("e_" + key, g, (0, -0.2, 0.05), 0.55)
        else:
            em = emblem_gemini("e_" + key, g, (0, -0.2, 0.05), 0.55)
        q = text3d("q_" + key, question, 0.32, M_text("q_" + key, GREY, 1.0), parent=g, loc=(0, 0, 1.5), face="Inter-SemiBold.ttf",
                   depth=0.02, bevel=0.004, maxw=2.9)
        a = big_text("a_" + key, answer, 0.6, color, g, (0, 0, 0.95), strength=2.0, maxw=2.9)
        pods.append((key, g, em, top_mat, ring_mat, q, a, t_q, t_a))

    def update(t):
        for key, g, em, top_mat, ring_mat, q, a, t_q, t_a in pods:
            popup(g, t, 46.8, 0.8)
            on = ease_out(prog(t, t_q, 0.6))
            glow(top_mat, 0.4 + 5.0 * on)
            glow(ring_mat, 0.6 + 5.0 * on)
            popup(q, t, t_q - 0.05, 0.5, overshoot=False)
            popup(a, t, t_a - 0.05, 0.55)
            em[0].rotation_euler = (0.0, 0.0, 0.0)
            em[0].location = (0, -0.2, 0.05 + 0.08 * math.sin(1.5 * t + len(key)))

    UPDATES.append(("verdict", 46.0, 55.0, COLL["S_verdict"], update))


BUILDERS = {"models": build_models, "limits": build_limits, "features": build_features, "catch": build_catch, "verdict": build_verdict}
for name in SETS:
    try:
        BUILDERS[name]()
        print("built set", name, flush=True)
    except Exception:  # noqa: BLE001
        print("SET FAILED", name, flush=True)
        traceback.print_exc()
        sys.stdout.flush()

# ------------------------------------------------------------------ camera path
# The camera rests at "stations" (one per idea) and flies between them. A station is
#   (hold start, hold end, point looked at at the start, point at the end, height offset,
#    distance at the start, distance at the end, sideways offset at the start, at the end).
# During a flight the two neighbouring stations are blended with a smooth ease, so the camera
# never stops dead: its slow push-in carries on into the move and out of it again.
def ST(h0, h1, o0, o1=None, dz=0.35, d0=10.6, d1=10.0, dx0=0.0, dx1=0.0):
    return {"h0": h0, "h1": h1, "o0": o0, "o1": o1 or o0, "dz": dz, "d0": d0, "d1": d1, "dx0": dx0, "dx1": dx1}


def dist3(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


A0, B0, C0, D0 = (0.0, 0.0, 0.0), (5.5, 8.0, 0.0), (-5.5, 16.0, 0.0), (0.0, 30.0, 2.4)
L1, L2, G2 = (0.0, 44.0, 0.0), (0.0, 56.0, 0.45), (1.5, 56.0, -0.5)
F1, F2, F3 = (0.0, 70.0, 0.0), (5.5, 79.0, 0.0), (-5.5, 88.0, 0.0)
CA = (0.0, 104.0, 0.0)
V1, V2, V3 = (-4.2, 120.0, 0.0), (0.0, 126.5, 0.0), (4.2, 133.0, 0.0)
STEPS_A, STEPS_B = (-3.8, 21.0, -0.5), (-1.4, 25.6, 1.0)

STATIONS = [
    ST(2.8, 7.1, A0, d0=12.0, d1=10.0, dx1=0.4),
    ST(7.9, 9.7, B0, d0=10.8, d1=10.0, dx0=-0.3, dx1=0.3),
    ST(10.5, 11.7, C0, d0=10.8, d1=10.0, dx0=0.3, dx1=-0.2),
    ST(12.3, 13.9, STEPS_A, STEPS_B, dz=0.2, d0=9.2, d1=8.6, dx0=1.0, dx1=0.5),
    ST(14.4, 16.5, D0, d0=11.0, d1=10.0, dx0=0.5, dx1=0.2),
    ST(17.9, 24.7, L1, dz=-0.25, d0=10.8, d1=10.0),
    ST(25.5, 28.6, L2, dz=0.1, d0=13.0, d1=12.2),
    ST(29.3, 30.4, G2, dz=0.6, d0=9.8, d1=9.4),
    ST(31.2, 35.4, F1, d0=10.8, d1=10.2, dx1=0.3),
    ST(36.0, 38.8, F2, d0=10.8, d1=10.2, dx0=0.3, dx1=-0.3),
    ST(39.4, 41.9, F3, d0=10.8, d1=10.2),
    ST(43.0, 47.2, CA, dz=0.0, d0=10.8, d1=10.0, dx1=0.2),
    ST(48.3, 49.9, V1, dz=0.0, d0=9.8, d1=9.2),
    ST(50.5, 51.5, V2, dz=0.0, d0=9.8, d1=9.2),
    ST(52.3, 54.6, V3, dz=0.0, d0=9.8, d1=9.0),
]


def station_pose(s, t):
    """Camera position and look-at point of station s at time t (carried on a little outside its hold)."""
    span = max(s["h1"] - s["h0"], 0.001)
    u = clamp((t - s["h0"]) / span, -0.8, 1.8)
    o = lerp3(s["o0"], s["o1"], u)
    d = s["d0"] + (s["d1"] - s["d0"]) * u
    dx = s["dx0"] + (s["dx1"] - s["dx0"]) * u
    tgt = (o[0], o[1], o[2] + s["dz"])
    pos = (o[0] + dx, o[1] - d, o[2] + s["dz"] + 0.3)
    return pos, tgt


def cam_at(t):
    if t <= STATIONS[0]["h0"]:
        return station_pose(STATIONS[0], t)
    for i, s in enumerate(STATIONS):
        if t <= s["h1"]:
            return station_pose(s, t)
        if i + 1 < len(STATIONS) and t < STATIONS[i + 1]["h0"]:
            n = STATIONS[i + 1]
            u = smooth((t - s["h1"]) / (n["h0"] - s["h1"]))
            p0, q0 = station_pose(s, t)
            p1, q1 = station_pose(n, t)
            p = lerp3(p0, p1, u)
            q = lerp3(q0, q1, u)
            sway = math.sin(math.pi * u) * (1.0 if i % 2 == 0 else -1.0) * min(1.6, 0.12 * dist3(p0, p1))
            return (p[0] + sway, p[1], p[2] + 0.35 * abs(sway)), q
    return station_pose(STATIONS[-1], t)


def pose_camera(t):
    p, q = cam_at(t)
    drift = (0.14 * math.sin(0.8 * t), 0.0, 0.09 * math.sin(0.55 * t + 1.0))
    p = add3(p, drift)
    shake = 0.0
    if "catch" in SETS:
        ts = cue("catch", "ads")
        if ts <= t < ts + 0.7:
            shake = 0.2 * math.exp(-(t - ts) * 6.0)
    p = add3(p, (shake * math.sin(t * 61.0), 0.0, shake * math.cos(t * 53.0)))
    cam.location = p
    look = Vector(q) - Vector(p)
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    cam_data.dof.focus_distance = max(look.length, 1.0)
    return p, q


def pose_lights(q):
    for obj, off in LIGHTS:
        obj.location = (q[0] + off[0], q[1] + off[1], q[2] + off[2])
        look = Vector(q) - Vector(obj.location)
        obj.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()


def pose_bokeh(p, t):
    for obj, x, fy, z, vz in BOKEH:
        zz = (z + vz * t) % 20.0 - 4.0
        obj.location = (p[0] + x, p[1] + fy, p[2] + zz)


def update_all(t):
    p, q = pose_camera(t)
    pose_lights(q)
    pose_bokeh(p, t)
    for name, t0, t1, coll, upd in UPDATES:
        live = t0 <= t <= t1
        coll.hide_render = not live
        if live:
            try:
                upd(t)
            except Exception:  # noqa: BLE001 - one broken set must not stop the others
                print("UPDATE FAILED in set", name, "at t=%.2f" % t, flush=True)
                traceback.print_exc()
                sys.stdout.flush()
    view_layer.update()


# ------------------------------------------------------------------ render settings
scene.render.engine = "CYCLES"
cy = scene.cycles
cy.device = "CPU"
cy.samples = SAMPLES


def setp(obj, name, value):
    try:
        setattr(obj, name, value)
    except Exception as exc:  # noqa: BLE001
        print("setting", name, "failed:", exc, flush=True)


denoise_ok = True
try:
    cy.denoiser = "OPENIMAGEDENOISE"
except Exception as exc:  # noqa: BLE001
    denoise_ok = False
    print("denoiser unavailable:", exc, flush=True)
cy.use_denoising = denoise_ok
if not denoise_ok:
    cy.samples = max(SAMPLES * 4, 96)
setp(cy, "use_adaptive_sampling", True)
setp(cy, "adaptive_threshold", 0.02)
setp(cy, "use_animated_seed", True)
cy.max_bounces = 5
cy.diffuse_bounces = 2
cy.glossy_bounces = 4
cy.transmission_bounces = 2
setp(cy, "volume_bounces", 0)
setp(cy, "caustics_reflective", False)
setp(cy, "caustics_refractive", False)
cy.sample_clamp_indirect = 4.0
scene.render.resolution_x = 1080
scene.render.resolution_y = 1920
scene.render.resolution_percentage = PCT
scene.render.fps = FPS
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
try:
    scene.view_settings.view_transform = "Filmic"
except Exception as exc:  # noqa: BLE001
    print("view transform note:", exc, flush=True)

scene.use_nodes = True
tree = scene.node_tree
for node in list(tree.nodes):
    tree.nodes.remove(node)
rl = tree.nodes.new("CompositorNodeRLayers")
glare = tree.nodes.new("CompositorNodeGlare")
glare.glare_type = "FOG_GLOW"
glare.quality = "MEDIUM"
glare.threshold = 1.2
glare.size = 8
glare.mix = -0.3
comp = tree.nodes.new("CompositorNodeComposite")
tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
tree.links.new(glare.outputs["Image"], comp.inputs["Image"])

# ------------------------------------------------------------------ render
start = time.time()
for frame in FRAMES:
    t = (frame - 1) / FPS
    try:
        update_all(t)
    except Exception:  # noqa: BLE001
        print("UPDATE FAILED at frame", frame, flush=True)
        traceback.print_exc()
        sys.stdout.flush()
    scene.frame_set(frame)
    scene.render.filepath = os.path.join(OUT_DIR, "frame_%04d.png" % frame)
    t_frame = time.time()
    bpy.ops.render.render(write_still=True)
    print("RENDERED frame", frame, "t=%.2f" % t, "took %.1fs" % (time.time() - t_frame), "elapsed %.1fs" % (time.time() - start), flush=True)
print("TOTAL_RENDER_SECONDS", round(time.time() - start, 1), flush=True)
