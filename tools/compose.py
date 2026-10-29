#!/usr/bin/env python3
"""Puts the finished video together and encodes it (H.264 + AAC, 1080x1920, 30 fps).

  python3 tools/compose.py --frames html_frames --eye eye_hq.mp4 --timeline timeline.json \
      --audio mix.wav --out video.mp4 [--preset slow --crf 18]

html_frames holds what tools/render_html.js wrote: a_00001.png (transparent, drawn over the
Blender eye footage) and o_00001.jpg (opaque). The eye clip is used forwards under the opening
and backwards under the outro, so the video ends the way it began.
"""
import argparse
import glob
import json
import math
import os
import subprocess
import sys
import tempfile
import time

import numpy as np
from PIL import Image

W, H, FPS = 1080, 1920, 30


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--eye", required=True)
    ap.add_argument("--timeline", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--preset", default="slow")
    ap.add_argument("--crf", default="18")
    ap.add_argument("--limit", type=int, default=0, help="only the first N frames (for quick tests)")
    args = ap.parse_args()

    timeline = json.load(open(args.timeline))
    total = math.ceil(timeline["duration"] * FPS)
    if args.limit:
        total = min(total, args.limit)

    work = tempfile.mkdtemp(prefix="eye_")
    if os.path.isdir(args.eye):
        eye_dir = args.eye
    else:
        eye_dir = work
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", args.eye, "-vf", "format=rgb24",
                        os.path.join(work, "e_%04d.png")], check=True)
    eye_files = sorted(glob.glob(os.path.join(eye_dir, "e_*.png")))
    n_eye = len(eye_files)
    print("eye frames:", n_eye, flush=True)

    def alpha_path(i):
        return os.path.join(args.frames, "a_%05d.png" % (i + 1))

    def opaque_path(i):
        return os.path.join(args.frames, "o_%05d.jpg" % (i + 1))

    second = next(i for i in range(total * 3 // 4, total + 1) if os.path.exists(alpha_path(i)))
    print("outro footage starts at frame", second, "of", total, flush=True)

    vf = ("scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,"
          "format=yuv420p,noise=c0s=3:c0f=t")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(FPS), "-i", "-", "-i", args.audio, "-vf", vf,
           "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf), "-profile:v", "high",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", args.out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    started = time.time()
    try:
        for i in range(total):
            if os.path.exists(alpha_path(i)):
                idx = min(i, n_eye - 1) if i < second else max(n_eye - 1 - (i - second), 0)
                base = Image.open(eye_files[idx]).convert("RGBA")
                base.alpha_composite(Image.open(alpha_path(i)).convert("RGBA"))
                frame = base.convert("RGB")
            else:
                frame = Image.open(opaque_path(i)).convert("RGB")
            if frame.size != (W, H):
                raise SystemExit("frame %d has size %s" % (i, frame.size))
            enc.stdin.write(np.asarray(frame).tobytes())
            if (i + 1) % 150 == 0:
                print("frame %d/%d  %.0fs" % (i + 1, total, time.time() - started), flush=True)
        enc.stdin.close()
        code = enc.wait()
    except BrokenPipeError:
        code = enc.wait()
    if code != 0:
        raise SystemExit("ffmpeg failed with code %s" % code)
    print("done in %.0fs ->" % (time.time() - started), args.out, os.path.getsize(args.out) // 1024, "KB", flush=True)


if __name__ == "__main__":
    main()
