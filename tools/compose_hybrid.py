#!/usr/bin/env python3
"""Puts the hybrid video together and encodes it (H.264 + AAC, 1080x1920, 30 fps).

  python3 tools/compose_hybrid.py --frames html_frames --open nn_hq.mp4 --close dc_hq.mp4 \
      --timeline timeline.json --audio mix.wav --out video.mp4 [--preset slow --crf 18]

html_frames holds what tools/render_html.js wrote: a_00001.png (transparent, drawn over 3D footage) and
o_00001.jpg (opaque, the 2D explainer scenes).
  --open   3D clip played forwards under the opening (first alpha window)
  --close  3D clip played backwards under the outro (second alpha window), slowed a little so that it fills the
           whole window and never freezes; the backwards camera move ends the way the opening began.
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


def extract(clip, name):
    folder = tempfile.mkdtemp(prefix=name + "_")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", clip, "-vf", "format=rgb24",
                    os.path.join(folder, "e_%04d.png")], check=True)
    files = sorted(glob.glob(os.path.join(folder, "e_*.png")))
    print("%s: %d frames" % (name, len(files)), flush=True)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--open", required=True)
    ap.add_argument("--close", required=True)
    ap.add_argument("--timeline", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--preset", default="slow")
    ap.add_argument("--crf", default="18")
    ap.add_argument("--maxrate", default="", help="e.g. 4800k: caps the bit rate (keeps the file under an upload limit)")
    ap.add_argument("--limit", type=int, default=0, help="only the first N frames (for quick tests)")
    ap.add_argument("--start", type=int, default=0, help="first frame (for quick tests; audio is cut to match)")
    args = ap.parse_args()

    timeline = json.load(open(args.timeline))
    total = math.ceil(timeline["duration"] * FPS)
    end = min(total, args.start + args.limit) if args.limit else total

    open_files = extract(args.open, "open")
    close_files = extract(args.close, "close")
    n_open, n_close = len(open_files), len(close_files)

    def alpha_path(i):
        return os.path.join(args.frames, "a_%05d.png" % (i + 1))

    def opaque_path(i):
        return os.path.join(args.frames, "o_%05d.jpg" % (i + 1))

    second = next(i for i in range(total * 3 // 4, total + 1) if os.path.exists(alpha_path(i)))
    n_out = total - second
    print("outro footage starts at frame %d of %d (%d frames, %d footage frames)" % (second, total, n_out, n_close), flush=True)

    cache = {}

    def footage(path):
        if path not in cache:
            if len(cache) > 6:
                cache.pop(next(iter(cache)))
            cache[path] = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
        return cache[path]

    def base_frame(i):
        if i < second:
            return Image.open(open_files[min(i, n_open - 1)]).convert("RGBA")
        k = i - second
        pos = (n_close - 1) * (1.0 - k / max(1, n_out - 1))      # float index, runs from the last footage frame to the first
        lo = int(math.floor(pos))
        frac = pos - lo
        if frac < 1e-3 or lo + 1 >= n_close:
            return Image.open(close_files[min(lo, n_close - 1)]).convert("RGBA")
        mix = footage(close_files[lo]) * (1 - frac) + footage(close_files[lo + 1]) * frac
        return Image.fromarray(np.clip(mix + .5, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    vf = ("scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,"
          "format=yuv420p,noise=c0s=3:c0f=t")
    audio_in = ["-i", args.audio]
    if args.start:
        audio_in = ["-ss", "%.4f" % (args.start / FPS), "-i", args.audio]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(FPS), "-i", "-"] + audio_in + ["-vf", vf,
           "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf), "-profile:v", "high"] + (
               ["-maxrate", args.maxrate, "-bufsize", "%dk" % (2 * int(args.maxrate.rstrip("k")))] if args.maxrate else []) + [
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", args.out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    started = time.time()
    try:
        for i in range(args.start, end):
            if os.path.exists(alpha_path(i)):
                base = base_frame(i)
                base.alpha_composite(Image.open(alpha_path(i)).convert("RGBA"))
                frame = base.convert("RGB")
            else:
                frame = Image.open(opaque_path(i)).convert("RGB")
            if frame.size != (W, H):
                raise SystemExit("frame %d has size %s" % (i, frame.size))
            enc.stdin.write(np.asarray(frame).tobytes())
            if (i + 1) % 150 == 0:
                print("frame %d/%d  %.0fs" % (i + 1, end, time.time() - started), flush=True)
        enc.stdin.close()
        code = enc.wait()
    except BrokenPipeError:
        code = enc.wait()
    if code != 0:
        raise SystemExit("ffmpeg failed with code %s" % code)
    print("done in %.0fs ->" % (time.time() - started), args.out, os.path.getsize(args.out) // 1024, "KB", flush=True)


if __name__ == "__main__":
    main()
