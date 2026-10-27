"""Robotic eye hero shot, rendered with Cycles on the CPU.

Run by .github/workflows/render.yml through: blender -b -P jobs/eye/scene.py
Settings come from environment variables (see jobs/ACTIVE).
"""
import math
import os
import random
import time

import bpy
from mathutils import Vector

random.seed(7)

FPS = 30
OUT_DIR = os.environ.get("OUT_DIR", "out/frames")
PCT = int(os.environ.get("RES_PERCENT", "50"))
SAMPLES = int(os.environ.get("SAMPLES", "32"))
F_START = int(os.environ.get("FRAME_START", "1"))
F_END = int(os.environ.get("FRAME_END", "1"))
os.makedirs(OUT_DIR, exist_ok=True)

print("BLENDER", bpy.app.version_string, flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# Brand colours in linear space
CYAN = (0.0, 0.91, 1.0)
GREEN = (0.0, 1.0, 0.24)
AMBER = (1.0, 0.45, 0.0)
ICE = (0.55, 0.95, 1.0)
HALF_PI = math.pi / 2
# A primitive's +Z axis then points to -Y, toward the camera
FACE_CAMERA = (HALF_PI, 0.0, 0.0)

# ---------------------------------------------------------------- world
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
background = world.node_tree.nodes["Background"]
background.inputs["Color"].default_value = (0.0015, 0.003, 0.004, 1.0)
background.inputs["Strength"].default_value = 1.0


# ------------------------------------------------------------ materials
def new_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    return mat


def metal(name, color, roughness, metallic=1.0):
    mat = new_material(name)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def emission(name, color, strength):
    mat = new_material(name)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    em = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat, em


def glass(name, color, roughness, ior):
    mat = new_material(name)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfGlass")
    shader.inputs["Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["IOR"].default_value = ior
    links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    return mat


def finish(name, mat, smooth=True):
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    if smooth:
        bpy.ops.object.shade_smooth()
    return obj


# ------------------------------------------------------------------ eye
housing_mat = metal("Housing", (0.012, 0.014, 0.018), 0.28)
bpy.ops.mesh.primitive_torus_add(
    major_radius=1.34, minor_radius=0.26, major_segments=128, minor_segments=32,
    location=(0, 0, 0), rotation=FACE_CAMERA)
finish("Housing", housing_mat)

back_mat = metal("Back", (0.004, 0.004, 0.005), 0.5)
bpy.ops.mesh.primitive_cylinder_add(
    vertices=96, radius=1.2, depth=0.08, location=(0, 0.55, 0), rotation=FACE_CAMERA)
finish("BackPlate", back_mat, smooth=False)

ring_outer_mat, ring_outer_em = emission("RingOuter", CYAN, 14.0)
bpy.ops.mesh.primitive_torus_add(
    major_radius=1.08, minor_radius=0.022, major_segments=160, minor_segments=12,
    location=(0, -0.06, 0), rotation=FACE_CAMERA)
finish("RingOuter", ring_outer_mat)

# Iris diaphragm: overlapping blades arranged like a camera lens
blade_mat = metal("Blade", (0.02, 0.025, 0.03), 0.22)
rig = bpy.data.objects.new("BladeRig", None)
scene.collection.objects.link(rig)
BLADES = 16
for i in range(BLADES):
    ang = 2 * math.pi * i / BLADES
    radius = 0.68
    y = 0.16 + (0.006 if i % 2 else 0.0)
    bpy.ops.mesh.primitive_plane_add(
        size=1.0,
        location=(radius * math.cos(ang), y, radius * math.sin(ang)),
        rotation=(HALF_PI, -ang + 0.42, 0.0))
    blade = finish("Blade%02d" % i, blade_mat, smooth=False)
    blade.scale = (0.66, 0.34, 1.0)
    blade.parent = rig

pupil_mat = metal("Pupil", (0.0, 0.0, 0.0), 0.05, metallic=0.0)
bpy.ops.mesh.primitive_cylinder_add(
    vertices=96, radius=0.30, depth=0.12, location=(0, 0.1, 0), rotation=FACE_CAMERA)
pupil = finish("Pupil", pupil_mat)

ring_pupil_mat, ring_pupil_em = emission("RingPupil", GREEN, 22.0)
bpy.ops.mesh.primitive_torus_add(
    major_radius=0.325, minor_radius=0.016, major_segments=128, minor_segments=12,
    location=(0, 0.0, 0), rotation=FACE_CAMERA)
finish("RingPupil", ring_pupil_mat)

ring_mid_mat, ring_mid_em = emission("RingMid", CYAN, 9.0)
for ring_radius in (0.52, 0.84):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=ring_radius, minor_radius=0.007, major_segments=128, minor_segments=8,
        location=(0, -0.02, 0), rotation=FACE_CAMERA)
    finish("RingMid", ring_mid_mat)

# Glass cornea over the iris
cornea_mat = glass("Cornea", (0.9, 1.0, 1.0), 0.02, 1.45)
bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=1.12, location=(0, -0.1, 0))
cornea = finish("Cornea", cornea_mat)
cornea.scale = (1.0, 0.22, 1.0)


# --------------------------------------------------------------- lights
def add_area(name, loc, size, size_y, color, energy, target=(0, 0, 0)):
    data = bpy.data.lights.new(name, type="AREA")
    data.shape = "RECTANGLE"
    data.size = size
    data.size_y = size_y
    data.color = color
    data.energy = energy
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = loc
    direction = Vector(target) - Vector(loc)
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj


# Neon strips in front of the eye: mostly seen as reflections in the cornea and housing
add_area("StripLeft", (-3.6, -5.5, 0.8), 0.5, 5.5, CYAN, 2000)
add_area("StripRight", (3.6, -5.5, -0.4), 0.5, 5.5, GREEN, 1600)
add_area("TopRim", (0.0, -2.5, 4.2), 3.5, 0.7, ICE, 700)
add_area("BottomKick", (0.0, -3.0, -4.0), 3.0, 0.5, CYAN, 450)

# ---------------------------------------------- city lights as bokeh
bokeh_mats = [
    emission("Bokeh%d" % i, color, strength)[0]
    for i, (color, strength) in enumerate([(CYAN, 7.0), (GREEN, 7.0), (AMBER, 6.0), (ICE, 8.0)])
]
for _ in range(150):
    y = random.uniform(10.0, 42.0)
    spread_x = 0.17 * (y + 9.0)
    spread_z = 0.30 * (y + 9.0)
    x = random.uniform(-spread_x, spread_x) * 1.1
    z = random.uniform(-spread_z, spread_z) * 1.1
    r = random.uniform(0.12, 0.45) * (y / 20.0)
    bpy.ops.mesh.primitive_circle_add(
        vertices=32, radius=r, fill_type="NGON", location=(x, y, z), rotation=FACE_CAMERA)
    obj = bpy.context.active_object
    obj.name = "Bokeh"
    obj.data.materials.append(random.choice(bokeh_mats))

# --------------------------------------------------------------- camera
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 60
cam_data.sensor_fit = "VERTICAL"
cam_data.sensor_height = 36
cam_data.dof.use_dof = True
cam_data.dof.aperture_fstop = 0.7
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
cam.rotation_euler = (HALF_PI, 0.0, 0.0)
scene.camera = cam


def ease(p):
    return p * p * (3 - 2 * p)


def update(p):
    cam.location = (0.0, -9.8 + 1.4 * ease(p), 0.0)
    cam_data.dof.focus_distance = abs(cam.location.y) - 0.05
    s = 1.0 + 0.22 * math.sin(2 * math.pi * p)
    pupil.scale = (s, s, 1.0)
    rig.rotation_euler = (0.0, 0.35 * p, 0.0)
    pulse = 1.0 + 0.45 * math.sin(2 * math.pi * p + 0.6)
    ring_pupil_em.inputs["Strength"].default_value = 22.0 * pulse
    ring_outer_em.inputs["Strength"].default_value = 14.0 * (1.0 + 0.25 * math.sin(2 * math.pi * p))


# ------------------------------------------------------- render settings
scene.render.engine = "CYCLES"
cy = scene.cycles
cy.device = "CPU"
cy.samples = SAMPLES
cy.use_denoising = True
try:
    cy.denoiser = "OPENIMAGEDENOISE"
except Exception as exc:  # noqa: BLE001
    print("denoiser note:", exc)
cy.max_bounces = 8
cy.glossy_bounces = 6
cy.transmission_bounces = 8
cy.sample_clamp_indirect = 5.0

scene.render.resolution_x = 1080
scene.render.resolution_y = 1920
scene.render.resolution_percentage = PCT
scene.render.fps = FPS
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
try:
    scene.view_settings.view_transform = "Filmic"
except Exception as exc:  # noqa: BLE001
    print("view transform note:", exc)

# Soft neon glow in the compositor
scene.use_nodes = True
tree = scene.node_tree
for node in list(tree.nodes):
    tree.nodes.remove(node)
render_layers = tree.nodes.new("CompositorNodeRLayers")
glare = tree.nodes.new("CompositorNodeGlare")
glare.glare_type = "FOG_GLOW"
glare.quality = "MEDIUM"
glare.threshold = 1.2
glare.size = 8
glare.mix = -0.3
composite = tree.nodes.new("CompositorNodeComposite")
tree.links.new(render_layers.outputs["Image"], glare.inputs["Image"])
tree.links.new(glare.outputs["Image"], composite.inputs["Image"])

# ----------------------------------------------------------------- render
start = time.time()
for frame in range(F_START, F_END + 1):
    progress = 0.5 if F_END == F_START else (frame - F_START) / (F_END - F_START)
    update(progress)
    scene.frame_set(frame)
    scene.render.filepath = os.path.join(OUT_DIR, "frame_%04d.png" % frame)
    bpy.ops.render.render(write_still=True)
    print("RENDERED frame", frame, "elapsed %.1fs" % (time.time() - start), flush=True)
print("TOTAL_RENDER_SECONDS", round(time.time() - start, 1), flush=True)
