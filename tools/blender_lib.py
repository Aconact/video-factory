"""Shared helpers for the Blender capability probes (real Blender 4.2, Cycles on CPU).

Everything here is plain bpy: materials, lights, camera, text, a small compositor chain.
Job scripts use it with  sys.path.insert(0, <repo>/tools); from blender_lib import *
"""
import math
import os
import sys
import time

import bpy
import bmesh
from mathutils import Vector, Matrix

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FONTS = os.path.join(REPO, "jobs", "chip", "fonts")
GREEN = (0.0, 1.0, 0.53)   # #00FF87 (already the brand value; use lin() for linear)
CYAN = (0.0, 0.96, 1.0)    # #00F5FF
OUT = os.environ.get("PROBE_OUT", os.path.join(REPO, "out", "probes"))
RES_X = int(os.environ.get("RES_X", "540"))
RES_Y = int(os.environ.get("RES_Y", "960"))
SAMPLES = int(os.environ.get("SAMPLES", "48"))
FRAME = int(os.environ.get("FRAME", "1"))


def lin(c):
    """sRGB 0..1 -> scene linear so brand hex values come out exact."""
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)


def hexc(h):
    h = h.lstrip("#")
    return lin(tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)))


# --------------------------------------------------------------------------- scene setup
def start(samples=None, res=None, bg=(0.004, 0.005, 0.007), bg_strength=1.0, look="AgX - Punchy",
          fps=30, frames=(1, 60), exposure=0.0, motion_blur=False, clamp=6.0, adaptive=0.03):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = frames
    sc.render.fps = fps
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = samples or SAMPLES
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = adaptive
    cy.use_denoising = True
    cy.denoiser = "OPENIMAGEDENOISE"
    cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    cy.denoising_prefilter = "FAST"
    cy.seed = 7
    cy.use_animated_seed = False
    cy.max_bounces = 6
    cy.diffuse_bounces = 2
    cy.glossy_bounces = 4
    cy.transmission_bounces = 4
    cy.transparent_max_bounces = 8
    cy.volume_bounces = 1
    cy.sample_clamp_indirect = clamp
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    r = res or (RES_X, RES_Y)
    sc.render.resolution_x, sc.render.resolution_y = r
    sc.render.resolution_percentage = 100
    sc.render.use_motion_blur = motion_blur
    sc.render.motion_blur_shutter = 0.45
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = look
    except TypeError:
        print("look not available:", look)
    sc.view_settings.exposure = exposure
    w = bpy.data.worlds.new("World")
    sc.world = w
    w.use_nodes = True
    bgn = w.node_tree.nodes["Background"]
    bgn.inputs["Color"].default_value = (*bg, 1.0)
    bgn.inputs["Strength"].default_value = bg_strength
    os.makedirs(OUT, exist_ok=True)
    return sc


def hdri(path, strength=1.0, rot=0.0):
    """Use an equirectangular image (Blender ships a few in datafiles/studiolights/world) as the world light."""
    w = bpy.context.scene.world
    nt = w.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_WORLD":
            nt.nodes.remove(n)
    out = [n for n in nt.nodes if n.type == "OUTPUT_WORLD"][0]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, rot)
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(path)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return bg


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


# --------------------------------------------------------------------------- materials
def mat(name, base=(0.5, 0.5, 0.5), metallic=0.0, rough=0.5, emit=None, strength=0.0, coat=0.0,
        coat_rough=0.05, trans=0.0, ior=1.45, alpha=1.0, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = coat_rough
    b.inputs["Transmission Weight"].default_value = trans
    b.inputs["IOR"].default_value = ior
    b.inputs["Alpha"].default_value = alpha
    b.inputs["Specular IOR Level"].default_value = spec
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = strength
    return m


def principled(m):
    return m.node_tree.nodes["Principled BSDF"]


def bump(m, scale, stretch=1.0, strength=0.2, detail=8.0, dist=0.02):
    nt = m.node_tree
    b = principled(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale * stretch, scale, scale)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Detail"].default_value = detail
    bm = nt.nodes.new("ShaderNodeBump")
    bm.inputs["Strength"].default_value = strength
    bm.inputs["Distance"].default_value = dist
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bm.inputs["Height"])
    nt.links.new(bm.outputs["Normal"], b.inputs["Normal"])
    return nz


def image_mat(name, path, emit_strength=1.0, rough=0.2, coat=0.0, alpha_from_image=False, base_dark=0.0):
    """A material whose emission (and base) comes from an image file: screens, cards, flags, heat maps."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(path)
    img.interpolation = "Cubic"
    img.extension = "CLIP"
    b.inputs["Base Color"].default_value = (base_dark, base_dark, base_dark, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = 0.03
    nt.links.new(img.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = emit_strength
    if alpha_from_image:
        nt.links.new(img.outputs["Alpha"], b.inputs["Alpha"])
    return m, img


# --------------------------------------------------------------------------- geometry
def mesh_obj(name, bm, material=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = link(bpy.data.objects.new(name, me))
    if material is not None:
        obj.data.materials.append(material)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return obj


def box(name, size, loc, material, bevel=0.0, segs=3, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    obj = mesh_obj(name, bm, material)
    obj.location = loc
    obj.rotation_euler = rot
    if bevel > 0:
        md = obj.modifiers.new("bevel", "BEVEL")
        md.width = bevel
        md.segments = segs
        md.limit_method = "ANGLE"
    return obj


def sphere(name, r, loc, material, seg=48, rings=24, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    for v in bm.verts:
        v.co.x *= scale[0]
        v.co.y *= scale[1]
        v.co.z *= scale[2]
    obj = mesh_obj(name, bm, material)
    obj.location = loc
    return obj


def cylinder(name, r, h, loc, material, seg=48, bevel=0.0, rot=(0, 0, 0), r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=(r if r2 is None else r2), depth=h)
    obj = mesh_obj(name, bm, material)
    obj.location = loc
    obj.rotation_euler = rot
    if bevel > 0:
        md = obj.modifiers.new("bevel", "BEVEL")
        md.width = bevel
        md.segments = 3
        md.limit_method = "ANGLE"
    return obj


def plane(name, w, h, loc, material, rot=(0, 0, 0), cuts=0):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=max(1, cuts + 1), y_segments=max(1, cuts + 1), size=1.0)
    m = max(abs(v.co.x) for v in bm.verts)          # normalise to +-1, then w/h are half-extents
    for v in bm.verts:
        v.co.x = v.co.x / m * w
        v.co.y = v.co.y / m * h
    # UVs 0..1 so image textures fit exactly
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = (l.vert.co.x / w * 0.5 + 0.5, l.vert.co.y / h * 0.5 + 0.5)
    obj = mesh_obj(name, bm, material, smooth=False)
    obj.location = loc
    obj.rotation_euler = rot
    return obj


def strip(name, pts, width, z, material):
    """Flat ribbon along a polyline in XY (field markings, arrows)."""
    bm = bmesh.new()
    hw = width / 2.0
    n = len(pts)
    for i in range(n - 1):
        a = Vector((pts[i][0], pts[i][1], 0))
        b = Vector((pts[i + 1][0], pts[i + 1][1], 0))
        d = (b - a)
        if d.length < 1e-6:
            continue
        d.normalize()
        a2 = a - d * hw
        b2 = b + d * hw
        nrm = Vector((-d.y, d.x, 0)) * hw
        vs = [bm.verts.new(p + Vector((0, 0, z))) for p in (a2 - nrm, a2 + nrm, b2 + nrm, b2 - nrm)]
        bm.faces.new(vs)
    return mesh_obj(name, bm, material, smooth=False)


def curve(name, pts, radius, material, closed=False, res=3, kind="POLY", bevel_res=3):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new(kind)
    if kind == "POLY":
        sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts):
            sp.points[i].co = (p[0], p[1], p[2], 1.0)
    else:
        sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts):
            sp.points[i].co = (p[0], p[1], p[2], 1.0)
        sp.order_u = min(4, len(pts))
        sp.use_endpoint_u = True
    sp.use_cyclic_u = closed
    cu.bevel_depth = radius
    cu.bevel_resolution = bevel_res
    cu.resolution_u = res
    cu.use_fill_caps = True
    cu.materials.append(material)
    return link(bpy.data.objects.new(name, cu))


def font(name):
    p = os.path.join(FONTS, name)
    return bpy.data.fonts.load(p) if os.path.exists(p) else None


def text3d(name, body, size, material, loc, face="Inter-ExtraBold.otf", extrude=0.01, bevel=0.002,
           rot=(0, 0, 0), align="CENTER", align_y="CENTER"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body, cu.size, cu.extrude, cu.bevel_depth = body, size, extrude, bevel
    cu.bevel_resolution, cu.resolution_u = 2, 10
    cu.align_x, cu.align_y = align, align_y
    f = font(face)
    if f is not None:
        cu.font = f
    cu.materials.append(material)
    obj = link(bpy.data.objects.new(name, cu))
    obj.location = loc
    obj.rotation_euler = rot
    return obj


def empty(name, loc):
    e = link(bpy.data.objects.new(name, None))
    e.location = loc
    return e


# --------------------------------------------------------------------------- lights and camera
def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def area(name, loc, target, size, power, color=(1, 1, 1), size_y=None, shape="RECTANGLE"):
    L = bpy.data.lights.new(name, "AREA")
    L.shape = shape
    L.size = size
    if size_y is not None:
        L.size_y = size_y
    L.energy = power
    L.color = color
    o = link(bpy.data.objects.new(name, L))
    o.location = loc
    o.visible_camera = False
    look_at(o, target)
    return o


def spot(name, loc, target, power, angle=40, blend=0.4, color=(1, 1, 1), radius=0.05):
    L = bpy.data.lights.new(name, "SPOT")
    L.energy = power
    L.spot_size = math.radians(angle)
    L.spot_blend = blend
    L.shadow_soft_size = radius
    L.color = color
    o = link(bpy.data.objects.new(name, L))
    o.location = loc
    o.visible_camera = False
    look_at(o, target)
    return o


def sun(name, rot, power=3.0, color=(1, 1, 1), angle=0.5):
    L = bpy.data.lights.new(name, "SUN")
    L.energy = power
    L.angle = angle
    L.color = color
    o = link(bpy.data.objects.new(name, L))
    o.rotation_euler = rot
    return o


def camera(loc, target, lens=45, fstop=None, focus=None, sensor_h=36.0, shift_y=0.0, name="Cam"):
    c = bpy.data.cameras.new(name)
    c.lens = lens
    c.sensor_fit = "VERTICAL"
    c.sensor_height = sensor_h
    c.shift_y = shift_y
    c.clip_start, c.clip_end = 0.02, 2000
    o = link(bpy.data.objects.new(name, c))
    o.location = loc
    tgt = empty(name + "Target", target)
    tc = o.constraints.new("TRACK_TO")
    tc.target = tgt
    tc.track_axis = "TRACK_NEGATIVE_Z"
    tc.up_axis = "UP_Y"
    if fstop:
        c.dof.use_dof = True
        c.dof.aperture_fstop = fstop
        if focus is not None:
            if isinstance(focus, (int, float)):
                c.dof.focus_distance = focus
            else:
                c.dof.focus_object = focus
        else:
            c.dof.focus_object = tgt
    bpy.context.scene.camera = o
    return o, tgt


# --------------------------------------------------------------------------- compositor
def post(glow=None, glow_size=8, threshold=1.0, vignette=0.0, dispersion=0.0):
    sc = bpy.context.scene
    sc.use_nodes = True
    tree = sc.node_tree
    for n in list(tree.nodes):
        tree.nodes.remove(n)
    rl = tree.nodes.new("CompositorNodeRLayers")
    out = tree.nodes.new("CompositorNodeComposite")
    last = rl.outputs["Image"]
    L = tree.links.new
    if glow is not None:
        gl = tree.nodes.new("CompositorNodeGlare")
        gl.glare_type, gl.quality, gl.threshold, gl.size, gl.mix = "FOG_GLOW", "MEDIUM", threshold, glow_size, glow
        L(last, gl.inputs["Image"])
        last = gl.outputs["Image"]
    if dispersion > 0:
        ld = tree.nodes.new("CompositorNodeLensdist")
        ld.inputs["Distortion"].default_value = 0.0
        ld.inputs["Dispersion"].default_value = dispersion
        L(last, ld.inputs["Image"])
        last = ld.outputs["Image"]
    if vignette > 0:
        em = tree.nodes.new("CompositorNodeEllipseMask")
        em.width, em.height = 0.95, 0.95
        bl = tree.nodes.new("CompositorNodeBlur")
        bl.filter_type, bl.use_relative, bl.factor_x, bl.factor_y = "GAUSS", True, 18.0, 18.0
        ma = tree.nodes.new("CompositorNodeMath")
        ma.operation, ma.use_clamp = "MULTIPLY", False
        ma.inputs[1].default_value = vignette
        mb = tree.nodes.new("CompositorNodeMath")
        mb.operation = "ADD"
        mb.inputs[1].default_value = 1.0 - vignette
        vg = tree.nodes.new("CompositorNodeMixRGB")
        vg.blend_type = "MULTIPLY"
        vg.inputs[0].default_value = 1.0
        L(em.outputs["Mask"], bl.inputs["Image"])
        L(bl.outputs["Image"], ma.inputs[0])
        L(ma.outputs["Value"], mb.inputs[0])
        L(last, vg.inputs[1])
        L(mb.outputs["Value"], vg.inputs[2])
        last = vg.outputs["Image"]
    L(last, out.inputs["Image"])


def key_loc(obj, frame, loc, interp="BEZIER"):
    obj.location = loc
    obj.keyframe_insert("location", frame=frame)


def set_interp(obj, kind="BEZIER"):
    ad = obj.animation_data
    if ad and ad.action:
        for fc in ad.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = kind
                if kind == "BEZIER":
                    kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"


def shot(name, frame=None):
    sc = bpy.context.scene
    if frame is not None:
        sc.frame_set(frame)
    sc.render.filepath = os.path.join(OUT, name + ".png")
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name, "%dx%d" % (sc.render.resolution_x, sc.render.resolution_y), "spp", sc.cycles.samples,
          "took %.1fs" % (time.time() - t0), flush=True)
    return sc.render.filepath
