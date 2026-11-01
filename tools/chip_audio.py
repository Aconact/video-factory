#!/usr/bin/env python3
"""Sound for the 6-second chip hero shot: a dark drone that swells, a riser into the power-on hit at 1.3 s,
a short chime, then quiet data ticks. Everything is synthesised (see tools/make_audio.py for the building blocks).

  python3 tools/chip_audio.py --out chip_audio.wav
"""
import argparse
import os
import subprocess
import sys

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_audio as ma  # noqa: E402

SR = ma.SR
DUR = 6.0
WAKE = 1.30


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    n = int(DUR * SR)
    t = np.arange(n) / SR
    rnd = np.random.default_rng(5)

    # drone: low sine + soft saw, swelling into the wake and fading at the end
    saw = ma.sos_filter(2.0 * ((55.0 * 2 * t) % 1.0) - 1.0, "low", 320.0)
    drone = 0.55 * np.sin(2 * np.pi * 55.0 * t) + 0.35 * saw + 0.18 * np.sin(2 * np.pi * 82.4 * t)
    env = np.interp(t, [0.0, WAKE, 2.2, 5.4, DUR], [0.0, 0.9, 0.7, 0.65, 0.0])
    drone = ma.stereo(drone * env * 0.5)

    buf = np.zeros((n, 2))
    buf += ma.scale_rms(drone, -27.0)
    ma.put(buf, ma.scale_peak(ma.sfx_whoosh(1.15, 140.0, 7000.0, 0.8), -20.0), 0.12)
    ma.put(buf, ma.scale_peak(ma.sfx_impact(), -13.0), WAKE)
    for k, f in enumerate((659.3, 987.8, 1318.5, 1975.5)):
        ma.put(buf, ma.scale_peak(ma.stereo(ma.sfx_pop(f), -0.4 + 0.27 * k), -23.0 - 1.5 * k), WAKE + 0.05 + 0.085 * k)
    scale = [523.3, 587.3, 659.3, 783.99, 880.0, 1046.5, 1174.7]
    for i in range(34):
        tt = 1.55 + i * 0.125 + rnd.uniform(-0.04, 0.04)
        if tt > 5.55:
            break
        f = scale[int(rnd.integers(0, len(scale)))] * (2 if rnd.random() < 0.3 else 1)
        ma.put(buf, ma.scale_peak(ma.stereo(ma.sfx_tick(f), float(rnd.uniform(-0.7, 0.7))), -29.0 + float(rnd.uniform(-3, 2))), tt)
    fade = np.interp(t, [0.0, 0.05, 5.55, DUR], [0.0, 1.0, 1.0, 0.0])
    buf *= fade[:, None]
    tmp = args.out + ".raw.wav"
    wavfile.write(tmp, SR, buf.astype(np.float32))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-af", "loudnorm=I=-14:TP=-1.5:LRA=7", "-ar", str(SR), args.out], check=True)
    os.remove(tmp)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
