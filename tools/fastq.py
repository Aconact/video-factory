"""fastq.py - measured Cycles speed-ups that keep the same look (Blender 4.2, CPU, 1080x1920).

Use it in any scene script (jobs/<name>/scene.py), after the Cycles settings and before rendering:

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
    from fastq import apply_recipe
    apply_recipe(scene)                                   # normal scenes
    apply_recipe(scene, thin_haze=["haze"])               # scene with a thin haze volume

What it does (all measured against 128-256 spp references, same seed, OIDN denoiser):
  1. Light Tree OFF            -> 30-50 % less render time per frame at the same samples.
                                  At equal TIME the picture is cleaner (more samples fit in).
                                  Scenes with many small emitters (LED racks, glowing nodes) gain most.
  2. thin_haze (optional)      -> volume sampling DISTANCE + volume bounces 0.
                                  Another 15-20 % in scenes with a thin homogeneous haze volume
                                  (density about 0.01-0.02). Not for thick fog or smoke: look first.

Tested and NOT worth it (no gain or visible loss): persistent data, tiling, ACCURATE prefilter,
BALANCED denoise quality (no effect in this build), path guiding, fast GI, lower bounces,
blurring glossy paths, motion blur off.
Memory: the peak (~1.7 GB at 1080x1920) is mostly the OIDN denoiser (~1.2 GB). The only setting that cuts
it (denoising_quality FAST, -32 %) costs about 0.5 dB of quality, so it is left alone.
"""
import bpy


def apply_recipe(scene=None, thin_haze=()):
    """Apply the measured recipe to `scene`. `thin_haze` = names of haze materials (optional)."""
    scene = scene or bpy.context.scene
    scene.cycles.use_light_tree = False
    applied = ["light_tree=OFF"]
    if thin_haze:
        for name in thin_haze:
            mat = bpy.data.materials.get(name)
            if mat is not None:
                mat.cycles.volume_sampling = "DISTANCE"
                applied.append("%s: volume_sampling=DISTANCE" % name)
        scene.cycles.volume_bounces = 0
        applied.append("volume_bounces=0")
    print("fastq recipe:", ", ".join(applied), flush=True)
    return applied
