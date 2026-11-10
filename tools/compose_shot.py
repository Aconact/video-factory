#!/usr/bin/env python3
"""Puts a finished 3D shot together: footage + transparent label frames + sound, 1080x1920, 30 fps, H.264 + AAC.

  python3 tools/compose_shot.py --footage pkg_hq.mp4 --overlay ov/fr --audio shot.wav --out shot.mp4 \
      [--frames 150 --maxrate 6500k --crf 19 --preset slow]

The footage is the near-lossless 4:4:4 file from the render workflow, decoded to RGB; the label frames (a_00001.png ...)
are laid over it in RGB; only then is the picture converted to BT.709 limited range (4:2:0) with a little temporal grain,
so colours match what a phone shows for the original frames.
"""
import argparse
import os
import subprocess
import time

import numpy as np
from PIL import Image

W, H, FPS = 1080, 1920, 30


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--footage", required=True)
    ap.add_argument("--overlay", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", type=int, default=150)
    ap.add_argument("--preset", default="slow")
    ap.add_argument("--crf", default="19")
    ap.add_argument("--maxrate", default="6500k")
    ap.add_argument("--grain", type=int, default=3)
    args = ap.parse_args()

    dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", args.footage, "-vf", "format=rgb24", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    vf = ("scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,format=yuv420p" +
          (",noise=c0s=%d:c0f=t" % args.grain if args.grain else ""))
    tmp = args.out + ".part.mp4"                                  # renamed when ffmpeg finishes cleanly
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
           "-i", args.audio, "-vf", vf, "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf), "-profile:v", "high",
           "-maxrate", args.maxrate, "-bufsize", "%dk" % (2 * int(args.maxrate.rstrip("k"))),
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", tmp]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    size = W * H * 3
    started = time.time()
    n = 0
    try:
        for i in range(args.frames):
            raw = dec.stdout.read(size)
            if len(raw) < size:
                raise SystemExit("footage ended after %d frames (wanted %d)" % (i, args.frames))
            base = Image.frombuffer("RGB", (W, H), raw, "raw", "RGB", 0, 1).convert("RGBA")
            ov = os.path.join(args.overlay, "a_%05d.png" % (i + 1))
            if os.path.exists(ov):
                layer = Image.open(ov).convert("RGBA")
                if layer.size != (W, H):
                    raise SystemExit("overlay frame %d has size %s" % (i + 1, layer.size))
                base.alpha_composite(layer)
            enc.stdin.write(np.asarray(base.convert("RGB")).tobytes())
            n += 1
        enc.stdin.close()
        code = enc.wait()
    except BrokenPipeError:
        code = enc.wait()
    dec.kill()
    if code != 0:
        raise SystemExit("ffmpeg failed with code %s" % code)
    os.replace(tmp, args.out)
    print("%d frames in %.0fs ->" % (n, time.time() - started), args.out, os.path.getsize(args.out) // 1024, "KB", flush=True)


if __name__ == "__main__":
    main()
