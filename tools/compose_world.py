#!/usr/bin/env python3
"""Puts the Blender-world video together and encodes it (H.264 + AAC, 1080x1920, 30 fps).

  python3 tools/compose_world.py --overlay overlay_frames --world world_hq.mp4 --world-start 3.0 \
      --eye eye_hq.mp4 --timeline timeline.json --audio mix.wav --out video.mp4 [--crf 22 --preset slow]

Layers, bottom to top:
  base     the eye footage forwards for the hook, a cross-fade into the 3D world, the 3D world,
           a cross-fade back into the eye footage played backwards for the outro
  overlay  transparent PNGs (a_00001.png ...) from `node tools/render_html.js --overlay 1`:
           captions, hook title, HUD, call to action and the sources line

--world-start is the video time (seconds) of the first frame of the world clip.
"""
import argparse
import glob
import json
import math
import os
import subprocess
import tempfile
import time

import numpy as np
from PIL import Image

W, H, FPS = 1080, 1920, 30


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overlay", required=True)
    ap.add_argument("--world", required=True)
    ap.add_argument("--world-start", type=float, default=3.0)
    ap.add_argument("--eye", required=True)
    ap.add_argument("--timeline", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--preset", default="slow")
    ap.add_argument("--crf", default="22")
    ap.add_argument("--x264", default="", help="extra x264 parameters, e.g. aq-mode=3:aq-strength=0.9")
    ap.add_argument("--grain", type=int, default=3, help="strength of the temporal dither noise (0 = none)")
    ap.add_argument("--limit", type=int, default=0, help="only the first N frames (quick test)")
    ap.add_argument("--start", type=int, default=0, help="first frame to write (quick test)")
    args = ap.parse_args()

    timeline = json.load(open(args.timeline))
    by_id = {s["id"]: s for s in timeline["scenes"]}
    total = math.ceil(timeline["duration"] * FPS)
    last = total if not args.limit else min(total, args.start + args.limit)

    x_in = (by_id["hook"]["end"] - 0.35, by_id["hook"]["end"] + 0.40)       # eye -> world
    x_out = (by_id["cta"]["start"] - 0.20, by_id["cta"]["start"] + 0.18)    # world -> eye (backwards); short, so the last 3D words do not ghost behind "FOLLOW"
    print("cross-fades: in %.2f-%.2f s, out %.2f-%.2f s" % (x_in + x_out), flush=True)

    work = tempfile.mkdtemp(prefix="eye_")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", args.eye, "-vf", "format=rgb24",
                    os.path.join(work, "e_%04d.png")], check=True)
    eye_files = sorted(glob.glob(os.path.join(work, "e_*.png")))
    n_eye = len(eye_files)
    print("eye frames:", n_eye, flush=True)

    # the outro plays the eye backwards from the moment the world starts fading out
    out_first = int(round(x_out[0] * FPS))

    def eye_index(i):
        if i < out_first:
            return min(i, n_eye - 1)
        return max(n_eye - 1 - (i - out_first), 0)

    def eye_frame(i):
        return Image.open(eye_files[eye_index(i)]).convert("RGB")

    world_offset = int(round(args.world_start * FPS))
    reader = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", args.world, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                              stdout=subprocess.PIPE)
    frame_bytes = W * H * 3
    state = {"last": None, "next_index": 0}

    def world_frame(i):
        """The world clip is read in order; asking for frame i returns the clip frame for that moment."""
        want = i - world_offset
        if want < 0:
            return None
        while state["next_index"] <= want:
            data = reader.stdout.read(frame_bytes)
            if len(data) < frame_bytes:
                break
            state["last"] = Image.frombuffer("RGB", (W, H), data, "raw", "RGB", 0, 1)
            state["next_index"] += 1
        return state["last"]

    vf = ("scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,"
          "format=yuv420p" + (",noise=c0s=%d:c0f=t" % args.grain if args.grain > 0 else ""))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(FPS), "-i", "-", "-i", args.audio, "-vf", vf,
           "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf), "-profile:v", "high",
           *(["-x264-params", args.x264] if args.x264 else []),
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", args.out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    started = time.time()
    code = 0
    try:
        # frames before --start are only read to keep the world clip in step
        for i in range(0, last):
            t = i / FPS
            w_img = world_frame(i) if (t >= x_in[0] - 0.05 and t < x_out[1] + 0.3) else None
            if i < args.start and w_img is None:
                continue
            if t < x_in[0]:
                base = eye_frame(i)
            elif t < x_in[1]:
                base = Image.blend(eye_frame(i), w_img, smooth((t - x_in[0]) / (x_in[1] - x_in[0])))
            elif t < x_out[0]:
                base = w_img
            elif t < x_out[1]:
                base = Image.blend(w_img, eye_frame(i), smooth((t - x_out[0]) / (x_out[1] - x_out[0])))
            else:
                base = eye_frame(i)
            if i < args.start:
                continue
            frame = base.convert("RGBA")
            overlay_path = os.path.join(args.overlay, "a_%05d.png" % (i + 1))
            if os.path.exists(overlay_path):
                frame.alpha_composite(Image.open(overlay_path).convert("RGBA"))
            enc.stdin.write(np.asarray(frame.convert("RGB")).tobytes())
            if (i + 1) % 150 == 0:
                print("frame %d/%d  %.0fs" % (i + 1, total, time.time() - started), flush=True)
        enc.stdin.close()
        code = enc.wait()
    except BrokenPipeError:
        code = enc.wait()
    finally:
        reader.kill()
    if code != 0:
        raise SystemExit("ffmpeg failed with code %s" % code)
    print("done in %.0fs ->" % (time.time() - started), args.out, os.path.getsize(args.out) // 1024, "KB", flush=True)


if __name__ == "__main__":
    main()
