#!/usr/bin/env python3
"""Runs a Blender scene script WITHOUT Blender, on a stand-in for bpy / bmesh / mathutils.

It checks what can be checked without rendering:
  * Python mistakes in the scene script (typos, wrong arguments, missing node or font names)
  * attribute names, node socket names and operator keywords that Blender 4.2 would reject
  * the layout: where every visible text object lands in the 1080x1920 picture, whether it
    leaves the safe area (the caption band starts at y=1280) and whether two texts overlap.

It does NOT check how the picture looks (light, colour, noise). Use real renders for that.

  python3 tools/fake_bpy.py jobs/world/scene.py --frames 181,265,379 [--layout]

Environment variables of the scene (OUT_DIR, SAMPLES, ...) are passed through as they are.
"""
import argparse
import math
import os
import runpy
import sys
import types

import numpy as np

W, H = 1080, 1920
SAFE_X = (60, 1020)
SAFE_Y = (170, 1285)


# ------------------------------------------------------------------ strict base
class Strict:
    _allowed = set()

    def __setattr__(self, key, value):
        if key.startswith("_") or key in type(self)._allowed:
            object.__setattr__(self, key, value)
        else:
            raise AttributeError("%s has no property '%s' (stand-in for Blender 4.2)" % (type(self).__name__, key))


class Vector:
    def __init__(self, v=(0.0, 0.0, 0.0)):
        self.v = [float(x) for x in v]

    def __getitem__(self, i):
        return self.v[i]

    def __iter__(self):
        return iter(self.v)

    def __len__(self):
        return len(self.v)

    def __sub__(self, o):
        return Vector([a - b for a, b in zip(self.v, o.v)])

    def __add__(self, o):
        return Vector([a + b for a, b in zip(self.v, o.v)])

    @property
    def length(self):
        return math.sqrt(sum(x * x for x in self.v))

    x = property(lambda s: s.v[0], lambda s, val: s.v.__setitem__(0, float(val)))
    y = property(lambda s: s.v[1], lambda s, val: s.v.__setitem__(1, float(val)))
    z = property(lambda s: s.v[2], lambda s, val: s.v.__setitem__(2, float(val)))

    def to_track_quat(self, track, up):
        assert (track, up) == ("-Z", "Y"), "only the camera/light convention is supported here"
        f = np.array(self.v, dtype=float)
        f = f / np.linalg.norm(f)
        right = np.cross(f, [0.0, 0.0, 1.0])
        if np.linalg.norm(right) < 1e-6:
            right = np.array([1.0, 0.0, 0.0])
        right /= np.linalg.norm(right)
        upv = np.cross(right, f)
        m = np.stack([right, upv, -f], axis=1)
        return Quat(m)


class Quat:
    def __init__(self, m):
        self.m = m

    def to_euler(self):
        m = self.m
        beta = -math.asin(max(-1.0, min(1.0, m[2, 0])))
        alpha = math.atan2(m[2, 1], m[2, 2])
        gamma = math.atan2(m[1, 0], m[0, 0])
        return (alpha, beta, gamma)


class Euler(tuple):
    def __new__(cls, v=(0, 0, 0), order="XYZ"):
        return tuple.__new__(cls, v)


# ------------------------------------------------------------------ collections of data blocks
REGISTRY = {"objects": [], "collections": []}


class Registry:
    def __init__(self, kind, factory):
        self.kind = kind
        self.factory = factory
        self.items = []

    def new(self, name, *args, **kw):
        item = self.factory(name, *args, **kw)
        self.items.append(item)
        return item

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)


class CollObjects:
    def __init__(self, owner):
        self.owner = owner
        self.items = []

    def link(self, obj):
        if obj in self.items:
            raise RuntimeError("Object '%s' already in collection '%s'" % (obj.name, self.owner.name))
        self.items.append(obj)
        obj.users_collection.append(self.owner)

    def unlink(self, obj):
        self.items.remove(obj)
        obj.users_collection.remove(self.owner)


class CollChildren:
    def __init__(self, owner):
        self.owner = owner
        self.items = []

    def link(self, coll):
        self.items.append(coll)


class Collection(Strict):
    _allowed = {"name", "hide_render", "hide_viewport"}

    def __init__(self, name):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "hide_render", False)
        object.__setattr__(self, "objects", CollObjects(self))
        object.__setattr__(self, "children", CollChildren(self))


class Mod(Strict):
    _allowed = {"width", "segments", "limit_method", "name"}


class Mods:
    def new(self, name, kind):
        assert kind in ("BEVEL",), kind
        return Mod()


class Poly(Strict):
    _allowed = {"use_smooth"}


class Mesh(Strict):
    _allowed = {"name"}

    def __init__(self, name):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "polygons", [Poly() for _ in range(6)])
        object.__setattr__(self, "materials", [])


class CurvePoint(Strict):
    _allowed = {"co"}


class CurvePoints:
    def __init__(self):
        self.pts = [CurvePoint()]

    def add(self, n):
        self.pts.extend(CurvePoint() for _ in range(n))

    def __getitem__(self, i):
        return self.pts[i]

    def __len__(self):
        return len(self.pts)


class Spline(Strict):
    _allowed = {"use_cyclic_u", "order_u"}

    def __init__(self):
        object.__setattr__(self, "points", CurvePoints())


class Splines:
    def __init__(self):
        self.items = []

    def new(self, kind):
        assert kind in ("POLY", "NURBS", "BEZIER"), kind
        sp = Spline()
        self.items.append(sp)
        return sp


class Font(Strict):
    _allowed = set()


class Curve(Strict):
    _allowed = {"name", "dimensions", "bevel_depth", "bevel_resolution", "use_fill_caps", "bevel_factor_start", "bevel_factor_end",
                "resolution_u", "extrude", "body", "size", "font", "align_x", "align_y", "space_character", "space_word", "space_line"}

    def __init__(self, name, kind="CURVE"):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "materials", [])
        object.__setattr__(self, "splines", Splines())
        object.__setattr__(self, "body", "")
        object.__setattr__(self, "size", 1.0)
        object.__setattr__(self, "space_character", 1.0)


class MatCycles(Strict):
    _allowed = {"emission_sampling", "sample_as_light"}


class Material(Strict):
    _allowed = {"name", "use_nodes", "diffuse_color"}

    def __init__(self, name):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "node_tree", None)
        object.__setattr__(self, "cycles", MatCycles())

    def __setattr__(self, key, value):
        Strict.__setattr__(self, key, value)
        if key == "use_nodes" and value and self.node_tree is None:
            nt = NodeTree()
            nt.new("ShaderNodeOutputMaterial", "Material Output")
            nt.new("ShaderNodeBsdfPrincipled", "Principled BSDF")
            object.__setattr__(self, "node_tree", nt)


class World(Strict):
    _allowed = {"name", "use_nodes"}

    def __init__(self, name):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "node_tree", None)

    def __setattr__(self, key, value):
        Strict.__setattr__(self, key, value)
        if key == "use_nodes" and value and self.node_tree is None:
            nt = NodeTree()
            nt.new("ShaderNodeBackground", "Background")
            nt.new("ShaderNodeOutputWorld", "World Output")
            object.__setattr__(self, "node_tree", nt)


class Light(Strict):
    _allowed = {"name", "shape", "size", "size_y", "color", "energy", "type"}

    def __init__(self, name, type="POINT"):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "type", type)


class DOF(Strict):
    _allowed = {"use_dof", "aperture_fstop", "focus_distance", "focus_object"}


class CamData(Strict):
    _allowed = {"name", "lens", "sensor_fit", "sensor_height", "sensor_width", "shift_x", "shift_y", "clip_end", "clip_start"}

    def __init__(self, name):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "dof", DOF())
        object.__setattr__(self, "lens", 50.0)
        object.__setattr__(self, "sensor_height", 24.0)
        object.__setattr__(self, "shift_y", 0.0)
        object.__setattr__(self, "clip_end", 100.0)


class Obj(Strict):
    _allowed = {"name", "data", "location", "rotation_euler", "scale", "parent", "hide_render", "dimensions"}

    def __init__(self, name, data):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "location", (0.0, 0.0, 0.0))
        object.__setattr__(self, "rotation_euler", (0.0, 0.0, 0.0))
        object.__setattr__(self, "scale", (1.0, 1.0, 1.0))
        object.__setattr__(self, "parent", None)
        object.__setattr__(self, "hide_render", False)
        object.__setattr__(self, "users_collection", [])
        object.__setattr__(self, "modifiers", Mods())
        object.__setattr__(self, "props", {})
        REGISTRY["objects"].append(self)

    def __setattr__(self, key, value):
        if key in ("location", "rotation_euler", "scale"):
            if len(tuple(value)) != 3:
                raise ValueError("%s needs 3 numbers" % key)
            value = tuple(float(x) for x in value)
        Strict.__setattr__(self, key, value)

    def __getitem__(self, key):
        return self.props[key]

    def __setitem__(self, key, value):
        self.props[key] = value

    def get(self, key, default=None):
        return self.props.get(key, default)

    @property
    def children_recursive(self):
        out = []
        for other in REGISTRY["objects"]:
            p = other.parent
            while p is not None:
                if p is self:
                    out.append(other)
                    break
                p = p.parent
        return out

    @property
    def dimensions(self):
        if isinstance(self.data, Curve) and self.data.kind == "FONT":
            return Vector((0.62 * self.data.size * max(len(self.data.body), 1) * self.data.space_character * 0.9, self.data.size, 0.1))
        return Vector((1.0, 1.0, 1.0))


# ------------------------------------------------------------------ nodes
SOCKETS = {
    "ShaderNodeOutputMaterial": (["Surface", "Volume", "Displacement"], []),
    "ShaderNodeOutputWorld": (["Surface", "Volume"], []),
    "ShaderNodeBackground": (["Color", "Strength"], ["Background"]),
    "ShaderNodeBsdfPrincipled": (
        ["Base Color", "Metallic", "Roughness", "IOR", "Alpha", "Normal", "Weight", "Subsurface Weight", "Subsurface Radius",
         "Subsurface Scale", "Subsurface IOR", "Subsurface Anisotropy", "Specular IOR Level", "Specular Tint", "Anisotropic",
         "Anisotropic Rotation", "Tangent", "Transmission Weight", "Coat Weight", "Coat Roughness", "Coat IOR", "Coat Tint",
         "Coat Normal", "Sheen Weight", "Sheen Roughness", "Sheen Tint", "Emission Color", "Emission Strength",
         "Thin Film Thickness", "Thin Film IOR"], ["BSDF"]),
    "ShaderNodeEmission": (["Color", "Strength", "Weight"], ["Emission"]),
    "ShaderNodeBsdfTransparent": (["Color", "Weight"], ["BSDF"]),
    "ShaderNodeMixShader": (["Fac", "Shader", "Shader"], ["Shader"]),
    "ShaderNodeLayerWeight": (["Blend", "Normal"], ["Fresnel", "Facing"]),
    "ShaderNodeTexNoise": (["Vector", "W", "Scale", "Detail", "Roughness", "Lacunarity", "Offset", "Gain", "Distortion"], ["Fac", "Color"]),
    "ShaderNodeBump": (["Strength", "Distance", "Height", "Normal"], ["Normal"]),
    "ShaderNodeTexCoord": ([], ["Generated", "Normal", "UV", "Object", "Camera", "Window", "Reflection"]),
    "ShaderNodeTexGradient": (["Vector"], ["Color", "Fac"]),
    "ShaderNodeMath": (["Value", "Value", "Value"], ["Value"]),
    "CompositorNodeRLayers": ([], ["Image", "Alpha", "Depth", "Noisy Image"]),
    "CompositorNodeGlare": (["Image"], ["Image"]),
    "CompositorNodeComposite": (["Image", "Alpha"], []),
}


class Socket(Strict):
    _allowed = {"default_value"}

    def __init__(self, name):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "default_value", None)


class SocketList:
    def __init__(self, names, owner):
        self.sockets = [Socket(n) for n in names]
        self.owner = owner

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.sockets[key]
        for s in self.sockets:
            if s.name == key:
                return s
        raise KeyError("socket '%s' not found on node type %s" % (key, self.owner))


class Node(Strict):
    _allowed = {"name", "gradient_type", "operation", "glare_type", "quality", "threshold", "size", "mix", "location", "label"}

    def __init__(self, kind, name):
        if kind not in SOCKETS:
            raise RuntimeError("unknown node type " + kind)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "name", name)
        ins, outs = SOCKETS[kind]
        object.__setattr__(self, "inputs", SocketList(ins, kind))
        object.__setattr__(self, "outputs", SocketList(outs, kind))


class Links:
    def new(self, a, b):
        assert isinstance(a, Socket) and isinstance(b, Socket), "links connect sockets"


class NodeTree:
    """Nodes are looked up by their current name, like in Blender (renaming a node renames its key)."""

    def __init__(self):
        self.items = []
        self.links = Links()

    def new(self, kind, name=None):
        node = Node(kind, name or kind)
        base = node.name
        n = 1
        while any(other.name == node.name for other in self.items):
            node.name = "%s.%03d" % (base, n)
            n += 1
        self.items.append(node)
        return node

    @property
    def nodes(self):
        return self

    def __getitem__(self, key):
        for node in self.items:
            if node.name == key:
                return node
        raise KeyError("Node '%s' not found" % key)

    def __contains__(self, key):
        return any(node.name == key for node in self.items)

    def __iter__(self):
        return iter(list(self.items))

    def clear(self):
        self.items.clear()

    def remove(self, node):
        self.items.remove(node)


# ------------------------------------------------------------------ scene
class ImageSettings(Strict):
    _allowed = {"file_format", "color_mode"}


class Render(Strict):
    _allowed = {"engine", "resolution_x", "resolution_y", "resolution_percentage", "fps", "filepath"}

    def __init__(self):
        object.__setattr__(self, "image_settings", ImageSettings())


class Cycles(Strict):
    _allowed = {"device", "samples", "denoiser", "use_denoising", "use_adaptive_sampling", "adaptive_threshold", "use_animated_seed",
                "max_bounces", "diffuse_bounces", "glossy_bounces", "transmission_bounces", "volume_bounces", "transparent_max_bounces",
                "caustics_reflective", "caustics_refractive", "sample_clamp_indirect", "sample_clamp_direct",
                "denoising_prefilter", "denoising_quality", "denoising_input_passes", "adaptive_min_samples"}


class ViewSettings(Strict):
    _allowed = {"view_transform", "look", "exposure", "gamma"}


class Scene(Strict):
    _allowed = {"camera", "world", "use_nodes", "frame_current"}

    def __init__(self):
        object.__setattr__(self, "collection", Collection("Scene Collection"))
        object.__setattr__(self, "render", Render())
        object.__setattr__(self, "cycles", Cycles())
        object.__setattr__(self, "view_settings", ViewSettings())
        object.__setattr__(self, "node_tree", NodeTree())
        object.__setattr__(self, "camera", None)

    def frame_set(self, frame):
        object.__setattr__(self, "frame_current", frame)


class ViewLayer:
    def update(self):
        pass


# ------------------------------------------------------------------ operators
OPS_KW = {
    "primitive_uv_sphere_add": {"segments", "ring_count", "radius", "calc_uvs", "enter_editmode", "align", "location", "rotation", "scale"},
    "primitive_ico_sphere_add": {"subdivisions", "radius", "calc_uvs", "enter_editmode", "align", "location", "rotation", "scale"},
    "primitive_cylinder_add": {"vertices", "radius", "depth", "end_fill_type", "calc_uvs", "enter_editmode", "align", "location", "rotation", "scale"},
    "primitive_cone_add": {"vertices", "radius1", "radius2", "depth", "end_fill_type", "calc_uvs", "enter_editmode", "align", "location", "rotation", "scale"},
    "primitive_torus_add": {"align", "location", "rotation", "major_segments", "minor_segments", "mode", "major_radius", "minor_radius",
                            "abso_major_rad", "abso_minor_rad", "generate_uvs"},
    "primitive_circle_add": {"vertices", "radius", "fill_type", "calc_uvs", "enter_editmode", "align", "location", "rotation", "scale"},
    "primitive_plane_add": {"size", "calc_uvs", "enter_editmode", "align", "location", "rotation", "scale"},
}


class MeshOps:
    def __getattr__(self, name):
        if name not in OPS_KW:
            raise AttributeError("bpy.ops.mesh has no operator '%s' here" % name)

        def op(**kw):
            bad = set(kw) - OPS_KW[name]
            if bad:
                raise TypeError("bpy.ops.mesh.%s() got unexpected keywords %s" % (name, sorted(bad)))
            mesh = DATA.meshes.new(name)
            obj = DATA.objects.new(name, mesh)
            ACTIVE_COLLECTION.objects.link(obj)
            if "rotation" in kw:
                obj.rotation_euler = tuple(kw["rotation"])
            CONTEXT.active_object = obj
            return {"FINISHED"}

        return op


class WmOps:
    def read_factory_settings(self, use_empty=False):
        assert use_empty is True
        return {"FINISHED"}


class RenderOps:
    def render(self, write_still=False, **kw):
        if HOOKS.get("render"):
            HOOKS["render"]()
        return {"FINISHED"}


class Ops:
    mesh = MeshOps()
    wm = WmOps()
    render = RenderOps()


class FontsReg:
    def load(self, path):
        if not os.path.exists(path):
            raise RuntimeError("Error: Cannot read font '%s'" % path)
        return Font()


class Data:
    def __init__(self):
        self.objects = Registry("objects", lambda n, d: Obj(n, d))
        self.meshes = Registry("meshes", lambda n: Mesh(n))
        self.curves = Registry("curves", lambda n, k: Curve(n, k))
        self.materials = Registry("materials", lambda n: Material(n))
        self.lights = Registry("lights", lambda n, type="POINT": Light(n, type))
        self.cameras = Registry("cameras", lambda n: CamData(n))
        self.worlds = Registry("worlds", lambda n: World(n))
        self.collections = Registry("collections", lambda n: Collection(n))
        self.fonts = FontsReg()


class Context:
    active_object = None


HOOKS = {}
DATA = Data()
SCENE = Scene()
VIEW_LAYER = ViewLayer()
CONTEXT = Context()
CONTEXT.scene = SCENE
CONTEXT.view_layer = VIEW_LAYER
ACTIVE_COLLECTION = SCENE.collection

# objects().new for text needs the data type: curves.new(name, "FONT") -> Curve kind FONT
bpy = types.ModuleType("bpy")
bpy.data = DATA
bpy.context = CONTEXT
bpy.ops = Ops()
bpy.app = types.SimpleNamespace(version_string="4.2.0 (stand-in)")
bpy.types = types.SimpleNamespace()

bmesh = types.ModuleType("bmesh")


class BMVert:
    def __init__(self):
        self.co = Vector((0.0, 0.0, 0.0))


class BM:
    def __init__(self):
        self.verts = [BMVert() for _ in range(8)]

    def to_mesh(self, me):
        pass

    def free(self):
        pass


class _BMOps:
    @staticmethod
    def create_cube(bm, size=1.0):
        assert size == 1.0


bmesh.new = lambda: BM()
bmesh.ops = _BMOps()

mathutils = types.ModuleType("mathutils")
mathutils.Vector = Vector
mathutils.Euler = Euler

for _name, _mod in (("bpy", bpy), ("bmesh", bmesh), ("mathutils", mathutils)):
    sys.modules[_name] = _mod


# ------------------------------------------------------------------ layout report
def euler_matrix(e):
    a, b, c = e
    rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return rz @ ry @ rx


def world_matrix(obj):
    m = np.eye(4)
    r = euler_matrix(obj.rotation_euler)
    s = np.diag(obj.scale)
    m[:3, :3] = r @ s
    m[:3, 3] = obj.location
    if obj.parent is not None:
        return world_matrix(obj.parent) @ m
    return m


def project(cam, point):
    cd = cam.data
    r = euler_matrix(cam.rotation_euler)
    local = r.T @ (np.array(point) - np.array(cam.location))
    depth = -local[2]
    if depth <= 0.1:
        return None
    half_v = (cd.sensor_height / 2.0) / cd.lens
    ndc_y = (local[1] / depth) / half_v
    ndc_x = (local[0] / depth) / (half_v * W / H)
    px = W / 2.0 + ndc_x * W / 2.0
    py = H / 2.0 - ndc_y * H / 2.0 + cd.shift_y * H
    return px, py, depth


def visible(obj):
    if obj.hide_render:
        return False
    return not any(c.hide_render for c in obj.users_collection)


def layout_report(frame, t):
    cam = SCENE.camera
    rows = []
    n_vis = 0
    for obj in REGISTRY["objects"]:
        if obj is cam or not isinstance(obj.data, (Curve, Mesh)) or not visible(obj):
            continue
        n_vis += 1
        if not (isinstance(obj.data, Curve) and obj.data.kind == "FONT"):
            continue
        m = world_matrix(obj)
        sc = np.linalg.norm(m[:3, 0])
        if sc < 0.05:
            continue
        dims = obj.dimensions
        w, h = dims.x * sc, obj.data.size * sc
        c = m[:3, 3]
        right = m[:3, 0] / sc
        up = m[:3, 1] / np.linalg.norm(m[:3, 1])
        pts = [c + right * w * 0.5 * sx + up * h * 0.5 * sy for sx in (-1, 1) for sy in (-1, 1)]
        proj = [project(cam, p) for p in pts]
        if any(p is None for p in proj):
            continue
        xs = [p[0] for p in proj]
        ys = [p[1] for p in proj]
        box = (min(xs), min(ys), max(xs), max(ys))
        rows.append((obj.data.body, box, sc))
    flags = []
    print("frame %d  t=%.2fs  camera at (%.1f, %.1f, %.1f)  %d visible objects, %d texts on screen" % (
        frame, t, cam.location[0], cam.location[1], cam.location[2], n_vis, len(rows)))
    for body, box, sc in sorted(rows, key=lambda r: (r[1][1], r[1][0])):
        x0, y0, x1, y1 = box
        onscreen = x1 > 0 and x0 < W and y1 > 0 and y0 < H
        if not onscreen:
            continue
        bad = []
        if x0 < SAFE_X[0] or x1 > SAFE_X[1]:
            bad.append("SIDE")
        if y0 < SAFE_Y[0]:
            bad.append("TOP")
        if y1 > SAFE_Y[1]:
            bad.append("LOW")
        print("   %-26s x %4d-%4d  y %4d-%4d  h %3dpx %s" % (body[:26], x0, x1, y0, y1, y1 - y0, " ".join(bad)))
    onscreen_rows = [(b, bx) for b, bx, s in rows if bx[2] > 0 and bx[0] < W and bx[3] > 0 and bx[1] < H]
    for i in range(len(onscreen_rows)):
        for j in range(i + 1, len(onscreen_rows)):
            a, b = onscreen_rows[i][1], onscreen_rows[j][1]
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            if ox > 6 and oy > 6:
                print("   OVERLAP: '%s' and '%s' (%d x %d px)" % (onscreen_rows[i][0], onscreen_rows[j][0], ox, oy))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--frames", default="")
    ap.add_argument("--layout", action="store_true")
    args = ap.parse_args()
    if args.frames:
        os.environ["FRAMES"] = args.frames
    os.environ.setdefault("OUT_DIR", "/tmp/fake_bpy_out")

    def on_render():
        frame = SCENE.frame_current
        if args.layout:
            layout_report(frame, (frame - 1) / 30.0)

    HOOKS["render"] = on_render
    sys.argv = [args.script]
    runpy.run_path(args.script, run_name="__main__")
    print("stand-in run finished: no Python errors")


if __name__ == "__main__":
    main()
