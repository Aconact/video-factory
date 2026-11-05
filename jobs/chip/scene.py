"""Hero shot: an AI chip waking up on its board (6 s, 1080x1920, 30 fps).

Built the way a Blender artist would: modelled geometry with bevels, procedural PBR materials,
a studio lighting rig, a camera on a Track-To target with a rack focus, and real keyframes
(Bezier-eased curves) for the camera, the glow and the data pulses.

Environment (same as the world job):  FRAMES  RES_PERCENT  SAMPLES  OUT_DIR
"""
import math
import os
import random
import time

import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
DURATION = 6.0
PCT = int(os.environ.get("RES_PERCENT", "50"))
SAMPLES = int(os.environ.get("SAMPLES", "32"))
OUT_DIR = os.environ.get("OUT_DIR", "out/frames")
FRAMES = [int(x) for x in os.environ.get("FRAMES", "1").split(",") if x.strip()]
N_FRAMES = int(DURATION * FPS)

GREEN = (0.0, 1.0, 0.53)     # #00FF87
CYAN = (0.0, 0.96, 1.0)      # #00F5FF
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, N_FRAMES
scene.render.fps = FPS


def linear(c):
    """sRGB 0..1 -> scene linear (so the brand colours come out as the real hex values)."""
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)


# --------------------------------------------------------------------------- materials
def new_mat(name, base=(0.5, 0.5, 0.5), metallic=0.0, rough=0.5, emit=None, strength=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = strength
    return m


def add_bump(m, scale, stretch, strength, detail=8.0):
    """Procedural micro-surface: a noise bump (stretch > 1 along X gives a brushed look)."""
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale * stretch, scale, scale)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Detail"].default_value = detail
    bm = nt.nodes.new("ShaderNodeBump")
    bm.inputs["Strength"].default_value = strength
    bm.inputs["Distance"].default_value = 0.02
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bm.inputs["Height"])
    nt.links.new(bm.outputs["Normal"], b.inputs["Normal"])
    return nz


M_PCB = new_mat("pcb", (0.003, 0.012, 0.011), 0.0, 0.5, coat=0.35)
M_PCB.node_tree.nodes["Principled BSDF"].inputs["Coat Roughness"].default_value = 0.4
add_bump(M_PCB, 60.0, 1.0, 0.25)
M_METAL = new_mat("lid", (0.62, 0.64, 0.68), 1.0, 0.30)
add_bump(M_METAL, 1500.0, 0.012, 0.16, 3.0)
M_COPPER = new_mat("copper", (0.80, 0.42, 0.20), 1.0, 0.28)
M_GOLD = new_mat("gold", (1.0, 0.70, 0.26), 1.0, 0.22)
M_SUB = new_mat("substrate", (0.012, 0.02, 0.03), 0.0, 0.5, coat=0.3)
add_bump(M_SUB, 140.0, 1.0, 0.2)
M_CAP = new_mat("cap_body", (0.30, 0.17, 0.07), 0.0, 0.45)
M_TERM = new_mat("cap_term", (0.85, 0.86, 0.9), 1.0, 0.25)
M_SILK = new_mat("silk", (0.8, 0.85, 0.85), 0.0, 0.7)
M_LOGO = new_mat("logo", (0.0, 0.0, 0.0), 0.0, 0.3, linear(CYAN), 0.0)
M_LOGO2 = new_mat("logo_sub", (0.0, 0.0, 0.0), 0.0, 0.3, linear(CYAN), 0.0)


# --------------------------------------------------------------------------- geometry helpers
def link(obj):
    scene.collection.objects.link(obj)
    return obj


def box(name, size, loc, mat, bevel=0.0, segs=3):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    bm.to_mesh(mesh)
    bm.free()
    obj = link(bpy.data.objects.new(name, mesh))
    obj.location = loc
    obj.data.materials.append(mat)
    if bevel > 0:
        md = obj.modifiers.new("bevel", "BEVEL")
        md.width = bevel
        md.segments = segs
        md.limit_method = "ANGLE"
    for p in mesh.polygons:
        p.use_smooth = True
    return obj


def font(name):
    path = os.path.join(HERE, "fonts", name)
    return bpy.data.fonts.load(path) if os.path.exists(path) else None


def text(name, body, size, mat, loc, face="Inter-ExtraBold.otf", extrude=0.01, bevel=0.002, rot=(0, 0, 0), align="CENTER"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body, cu.size, cu.extrude, cu.bevel_depth = body, size, extrude, bevel
    cu.bevel_resolution, cu.resolution_u = 2, 10
    cu.align_x, cu.align_y = align, "CENTER"
    f = font(face)
    if f is not None:
        cu.font = f
    cu.materials.append(mat)
    obj = link(bpy.data.objects.new(name, cu))
    obj.location = loc
    obj.rotation_euler = rot
    return obj


def path_curve(name, pts, mat, radius, z, closed=False, res=2):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, (x, y) in enumerate(pts):
        sp.points[i].co = (x, y, z, 1.0)
    sp.use_cyclic_u = closed
    cu.bevel_depth = radius
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    cu.materials.append(mat)
    return link(bpy.data.objects.new(name, cu))


# --------------------------------------------------------------------------- the board and the package
BOARD = 18.0
board = box("board", (BOARD, BOARD, 0.16), (0, 0, -0.08), M_PCB, bevel=0.03)
P = 1.45                                   # half size of the package
box("substrate", (2 * P, 2 * P, 0.09), (0, 0, 0.045), M_SUB, bevel=0.025)
box("frame", (2.35, 2.35, 0.05), (0, 0, 0.115), M_GOLD, bevel=0.012)
LID = 1.0                                  # half size of the lid
lid = box("lid", (2 * LID, 2 * LID, 0.16), (0, 0, 0.2), M_METAL, bevel=0.035, segs=4)
box("logo_plate", (1.3, 0.78, 0.012), (0, 0, 0.281), M_SUB, bevel=0.01)
logo = text("logo", "TP-1", 0.40, M_LOGO, (0, 0.06, 0.296), extrude=0.018, bevel=0.003)
sub_logo = text("logo_sub", "NEURAL PROCESSING UNIT", 0.074, M_LOGO2, (0, -0.2, 0.291), face="JetBrainsMono-Bold.ttf",
                extrude=0.004, bevel=0.0008)
for sx in (-1, 1):                          # corner marks on the lid
    for sy in (-1, 1):
        box("mark", (0.12, 0.012, 0.004), (sx * 0.78, sy * 0.80, 0.282), M_GOLD)

# BGA balls along the substrate edge
bm = bmesh.new()
for side in range(4):
    for i in range(22):
        u = (i - 10.5) * 0.115
        for row in range(2):
            d = P - 0.07 - row * 0.1
            x, y = (u, d) if side == 0 else (u, -d) if side == 1 else (d, u) if side == 2 else (-d, u)
            bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.034,
                                      matrix=__import__("mathutils").Matrix.Translation((x, y, 0.095)))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
m = bpy.data.meshes.new("bga")
bm.to_mesh(m)
bm.free()
bga = link(bpy.data.objects.new("bga", m))
bga.data.materials.append(M_GOLD)
for p in m.polygons:
    p.use_smooth = True

# capacitors around the package
bm = bmesh.new()
cap_faces = []
rng = random.Random(3)
for ring, (half, step) in enumerate(((1.9, 0.30), (2.35, 0.42))):
    n = int(2 * half / step)
    for side in range(4):
        for i in range(n):
            u = -half + (i + 0.5) * step
            if rng.random() < 0.12:
                continue
            x, y = (u, half) if side == 0 else (u, -half) if side == 1 else (half, u) if side == 2 else (-half, u)
            horiz = side in (0, 1)
            sx, sy = (0.17, 0.09) if horiz else (0.09, 0.17)
            res = bmesh.ops.create_cube(bm, size=1.0)
            for v in res["verts"]:
                v.co.x = v.co.x * sx + x
                v.co.y = v.co.y * sy + y
                v.co.z = v.co.z * 0.075 + 0.0375
            faces = {f for v in res["verts"] for f in v.link_faces}
            # the two end faces become the silver terminals
            for f in faces:
                nrm = f.normal
                if (horiz and abs(nrm.x) > 0.9) or (not horiz and abs(nrm.y) > 0.9):
                    cap_faces.append(f.index)
bm.faces.ensure_lookup_table()
for f in bm.faces:
    f.material_index = 1 if f.index in cap_faces else 0
bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.006, segments=2, affect="EDGES")
m = bpy.data.meshes.new("caps")
bm.to_mesh(m)
bm.free()
caps = link(bpy.data.objects.new("caps", m))
caps.data.materials.append(M_CAP)
caps.data.materials.append(M_TERM)

# silkscreen labels
for i, (lab, x, y, r) in enumerate((("U1", -2.9, 2.9, 0), ("C12", 2.0, -2.9, 0), ("R7", -3.4, -1.2, math.pi / 2), ("VDD", 3.3, 1.7, 0),
                                    ("NPU-CORE", 0.0, -3.35, 0), ("REV 2.1", -2.2, -3.6, 0), ("GND", 3.6, -1.3, math.pi / 2))):
    text("silk%d" % i, lab, 0.14, M_SILK, (x, y, 0.003), face="JetBrainsMono-Bold.ttf", extrude=0.0015, bevel=0.0004, rot=(0, 0, r))

# --------------------------------------------------------------------------- traces and data pulses
TRACE_R = 0.018
N_LANES = 14
PITCH = 0.085
traces = []          # (curve object, pulse object, length-weight, side, lane)
anim_jobs = []


def lane_points(i, side):
    x0 = (i - (N_LANES - 1) / 2) * PITCH
    fan = 2.3
    y0 = P + 0.02
    y1 = P + 0.30 + (N_LANES / 2 - abs(i - (N_LANES - 1) / 2)) * 0.075
    x1 = x0 * fan
    y2 = y1 + abs(x1 - x0)
    y3 = 8.2
    pts = [(x0, y0), (x0, y1), (x1, y2), (x1, y3)]
    c, s = math.cos(side * math.pi / 2), math.sin(side * math.pi / 2)
    return [(c * x - s * y, s * x + c * y) for x, y in pts]


M_BASEGLOW = []
for side in range(4):
    for i in range(N_LANES):
        pts = lane_points(i, side)
        cu = path_curve("trace_%d_%d" % (side, i), pts, M_COPPER, TRACE_R, 0.012)
        col = CYAN if (i + side) % 2 == 0 else GREEN
        gm = new_mat("pulse_%d_%d" % (side, i), (0, 0, 0), 0.0, 0.4, linear(col), 0.0)
        pulse = path_curve("pulse_%d_%d" % (side, i), pts, gm, TRACE_R * 1.55, 0.02)
        pulse.data.bevel_factor_mapping_start = "SPLINE"
        pulse.data.bevel_factor_mapping_end = "SPLINE"
        pulse.data.bevel_factor_start = 0.0
        pulse.data.bevel_factor_end = 0.0
        traces.append((cu, pulse, gm, side, i))
        # via at the far end
        box("via", (0.07, 0.07, 0.01), (pts[-1][0], pts[-1][1], 0.006), M_GOLD, bevel=0.02)

# --------------------------------------------------------------------------- world and lights
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.002, 0.003, 0.005, 1.0)
bg.inputs["Strength"].default_value = 1.0


def area(name, loc, target, size, power, color, shape="RECTANGLE", size_y=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = shape
    ld.size = size
    if size_y:
        ld.size_y = size_y
    ld.energy = power
    ld.color = color
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


area("top_soft", (0.5, -1.0, 7.0), (0, 0, 0), 6.0, 210, (0.9, 0.95, 1.0), "SQUARE")
area("key_cyan", (-5.5, -3.0, 2.6), (0, 0, 0.2), 2.5, 520, (0.2, 0.9, 1.0), "RECTANGLE", 5.0)
area("rim_green", (5.5, 3.5, 2.2), (0, 0, 0.2), 2.5, 700, (0.2, 1.0, 0.55), "RECTANGLE", 5.0)
area("kick_front", (0.0, -6.0, 0.8), (0, 0, 0.1), 3.0, 150, (1.0, 0.95, 0.9), "SQUARE")

# --------------------------------------------------------------------------- dust motes (bokeh)
mote_meshes = []
for k, c in enumerate((CYAN, GREEN, (1.0, 1.0, 1.0))):
    me = bpy.data.meshes.new("mote%d" % k)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(new_mat("mote%d" % k, (0, 0, 0), 0.0, 0.5, linear(c), 7.0))
    mote_meshes.append(me)
rng2 = random.Random(21)
for k in range(110):
    ob = link(bpy.data.objects.new("mote%d" % k, mote_meshes[k % 3]))
    r = rng2.uniform(0.010, 0.032)
    ob.scale = (r, r, r)
    p0 = Vector((rng2.uniform(-4.5, 4.5), rng2.uniform(-5.5, 3.5), rng2.uniform(0.15, 3.2)))
    drift = Vector((rng2.uniform(-0.3, 0.3), rng2.uniform(-0.2, 0.3), rng2.uniform(0.05, 0.4)))
    ob.location = p0
    ob.keyframe_insert("location", frame=1)
    ob.location = p0 + drift * DURATION
    ob.keyframe_insert("location", frame=N_FRAMES)

# --------------------------------------------------------------------------- camera (Track-To target, rack focus)
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 45
cam_data.sensor_fit = "VERTICAL"
cam_data.sensor_height = 36
cam_data.shift_y = -0.10
cam_data.clip_start, cam_data.clip_end = 0.05, 100
cam = link(bpy.data.objects.new("Cam", cam_data))
scene.camera = cam
target = link(bpy.data.objects.new("CamTarget", None))
trk = cam.constraints.new("TRACK_TO")
trk.target = target
trk.track_axis = "TRACK_NEGATIVE_Z"
trk.up_axis = "UP_Y"
cam_data.dof.use_dof = True
cam_data.dof.focus_object = target
cam_data.dof.aperture_fstop = 1.6
cam_data.dof.aperture_blades = 7


def key(obj, prop, frame, value, index=-1):
    setattr(obj, prop, value) if index < 0 else None
    obj.keyframe_insert(prop, frame=frame)


def ease_all(obj):
    ad = obj.animation_data
    if ad and ad.action:
        for fc in ad.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"


# camera: low and close along a lane, then a long rising dolly to a 3/4 hero angle
CAM_KEYS = [  # frame, camera position, target position
    (1, (-2.1, -4.3, 0.36), (-0.35, -1.9, 0.05)),
    (55, (-1.3, -4.0, 0.95), (0.0, -1.2, 0.12)),
    (120, (1.2, -3.5, 2.0), (0.0, 0.0, 0.2)),
    (180, (2.0, -3.0, 3.1), (0.0, 0.05, 0.24)),
]
for f, p, t in CAM_KEYS:
    cam.location = p
    cam.keyframe_insert("location", frame=f)
    target.location = t
    target.keyframe_insert("location", frame=f)
ease_all(cam)
ease_all(target)

# --------------------------------------------------------------------------- the chip wakes up: glow and data pulses
WAKE = 40                                    # frame where the logo lights up
b_logo = M_LOGO.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
for f, v in ((1, 0.0), (WAKE - 4, 0.15), (WAKE + 18, 9.0), (WAKE + 34, 4.5), (150, 5.5), (180, 7.0)):
    b_logo.default_value = v
    b_logo.keyframe_insert("default_value", frame=f)
b_sub = M_LOGO2.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
for f, v in ((1, 0.0), (WAKE + 4, 0.2), (WAKE + 30, 2.2), (180, 2.6)):
    b_sub.default_value = v
    b_sub.keyframe_insert("default_value", frame=f)

for cu, pulse, gm, side, i in traces:
    em = gm.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    delay = WAKE + 6 + 1.6 * abs(i - (N_LANES - 1) / 2) + 2.5 * side
    run = 46 + 10 * ((i * 5 + side * 3) % 4)             # frames a pulse needs to cross the board
    em.default_value = 0.0
    em.keyframe_insert("default_value", frame=1)
    em.default_value = 9.0
    em.keyframe_insert("default_value", frame=int(delay))
    L = 0.13
    f0 = int(delay)
    runs = 0
    while f0 < N_FRAMES + 20 and runs < 4:
        pulse.data.bevel_factor_start = 0.0
        pulse.data.bevel_factor_end = 0.0
        pulse.data.keyframe_insert("bevel_factor_start", frame=f0)
        pulse.data.keyframe_insert("bevel_factor_end", frame=f0)
        pulse.data.bevel_factor_start = 0.0
        pulse.data.bevel_factor_end = L
        pulse.data.keyframe_insert("bevel_factor_start", frame=f0 + 2)
        pulse.data.keyframe_insert("bevel_factor_end", frame=f0 + 2)
        pulse.data.bevel_factor_start = 1.0 - L
        pulse.data.bevel_factor_end = 1.0
        pulse.data.keyframe_insert("bevel_factor_start", frame=f0 + run)
        pulse.data.keyframe_insert("bevel_factor_end", frame=f0 + run)
        pulse.data.bevel_factor_start = 1.0
        pulse.data.bevel_factor_end = 1.0
        pulse.data.keyframe_insert("bevel_factor_start", frame=f0 + run + 2)
        pulse.data.keyframe_insert("bevel_factor_end", frame=f0 + run + 2)
        f0 += run + 14 + (i * 7 + side) % 17
        runs += 1

for obj in bpy.data.curves:
    ad = obj.animation_data
    if ad and ad.action:
        for fc in ad.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"

# --------------------------------------------------------------------------- render settings
scene.render.engine = "CYCLES"
cy = scene.cycles
cy.device = "CPU"
cy.samples = SAMPLES
cy.use_denoising = True
try:
    cy.denoiser = "OPENIMAGEDENOISE"
    cy.denoising_prefilter = "FAST"
    cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.03
    cy.use_animated_seed = False
except Exception as exc:  # noqa: BLE001
    print("render setting note:", exc, flush=True)
cy.max_bounces = 6
cy.diffuse_bounces = 2
cy.glossy_bounces = 4
cy.transmission_bounces = 2
cy.sample_clamp_indirect = 6.0
cy.caustics_reflective = False
cy.caustics_refractive = False
cy.use_light_tree = False       # measured: 41 % less time per frame at the same samples (tools/fastq.py)
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = 0.45
scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
scene.render.resolution_percentage = PCT
BORDER = os.environ.get("BORDER", "")          # "x0,x1,y0,y1" (0..1, from the bottom left): render only that part, for quick tests
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
    scene.view_settings.look = "AgX - Punchy"
except Exception as exc:  # noqa: BLE001
    print("view transform note:", exc, flush=True)

scene.use_nodes = True
tree = scene.node_tree
for n in list(tree.nodes):
    tree.nodes.remove(n)
rl = tree.nodes.new("CompositorNodeRLayers")
gl = tree.nodes.new("CompositorNodeGlare")
gl.glare_type, gl.quality, gl.threshold, gl.size, gl.mix = "FOG_GLOW", "MEDIUM", 1.0, 8, -0.2
ld = tree.nodes.new("CompositorNodeLensdist")
ld.inputs["Distortion"].default_value = 0.0
ld.inputs["Dispersion"].default_value = 0.02
em = tree.nodes.new("CompositorNodeEllipseMask")
em.width, em.height = 0.95, 0.95
bl = tree.nodes.new("CompositorNodeBlur")
bl.filter_type, bl.use_relative, bl.factor_x, bl.factor_y = "GAUSS", True, 18.0, 18.0
ma = tree.nodes.new("CompositorNodeMath")
ma.operation, ma.use_clamp = "MULTIPLY", False
ma.inputs[1].default_value = 0.62
mb = tree.nodes.new("CompositorNodeMath")
mb.operation = "ADD"
mb.inputs[1].default_value = 0.38
vg = tree.nodes.new("CompositorNodeMixRGB")
vg.blend_type = "MULTIPLY"
vg.inputs[0].default_value = 1.0
out = tree.nodes.new("CompositorNodeComposite")
L = tree.links.new
L(rl.outputs["Image"], gl.inputs["Image"])
L(gl.outputs["Image"], ld.inputs["Image"])
L(em.outputs["Mask"], bl.inputs["Image"])
L(bl.outputs["Image"], ma.inputs[0])
L(ma.outputs["Value"], mb.inputs[0])
L(ld.outputs["Image"], vg.inputs[1])
L(mb.outputs["Value"], vg.inputs[2])
L(vg.outputs["Image"], out.inputs["Image"])

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
