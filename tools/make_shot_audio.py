"""Synthesised sound design for the package test shot (5 s, 48 kHz stereo): a soft ambient bed, a rising swell while the
layers come apart, label ticks, a power-up sweep when the die lights, and tiny data chirps. Pure numpy/scipy, no samples.

    python3 tools/make_shot_audio.py out.wav
"""
import sys
import wave

import numpy as np
from scipy import signal

SR = 48000
DUR = 5.0
N = int(SR * DUR)
T = np.arange(N) / SR
rng = np.random.default_rng(5)


def db(x):
    return 10 ** (x / 20.0)


def smooth(x0, x1, t):
    k = np.clip((t - x0) / (x1 - x0), 0, 1)
    return k * k * (3 - 2 * k)


def band_noise(f_lo, f_hi, order=3):
    sos = signal.butter(order, [f_lo, f_hi], btype="bandpass", fs=SR, output="sos")
    return signal.sosfilt(sos, rng.standard_normal(N))


def swell(t_start, t_peak, t_end, f_lo, f_hi, gain_db, bands=7):
    """Filtered noise whose centre frequency glides f_lo -> f_hi across the swell (cross-faded band-pass banks)."""
    freqs = np.geomspace(f_lo, f_hi, bands)
    pos = np.linspace(t_start, t_end, bands)
    env = np.interp(T, [t_start, t_peak, t_end], [0, 1, 0], left=0, right=0) ** 1.6
    out = np.zeros(N)
    for f, p in zip(freqs, pos):
        w = np.exp(-0.5 * ((T - p) / ((t_end - t_start) / (bands * 0.9))) ** 2)
        out += band_noise(f * 0.7, min(f * 1.4, SR / 2 - 100)) * w
    return out * env * db(gain_db) / np.sqrt(bands) * 3.0


def blip(t0, f0, f1, length, gain_db, decay=0.035):
    t = T - t0
    m = (t >= 0) & (t < length)
    fr = f0 + (f1 - f0) * np.clip(t / length, 0, 1)
    ph = 2 * np.pi * np.cumsum(np.where(m, fr, 0)) / SR
    return np.where(m, np.sin(ph) * np.exp(-np.clip(t, 0, None) / decay), 0) * db(gain_db)


def thump(t0, f, length, gain_db):
    t = T - t0
    m = t >= 0
    fr = f * (1 + 1.6 * np.exp(-np.clip(t, 0, None) * 18))
    ph = 2 * np.pi * np.cumsum(np.where(m, fr, 0)) / SR
    return np.where(m, np.sin(ph) * np.exp(-np.clip(t, 0, None) / (length / 4.0)), 0) * db(gain_db)


def sweep(t0, t1, f0, f1, gain_db):
    t = np.clip(T, t0, t1)
    k = (t - t0) / (t1 - t0)
    fr = f0 * (f1 / f0) ** (k ** 1.5)
    env = smooth(t0, t0 + (t1 - t0) * 0.7, T) * (1 - smooth(t1 - 0.12, t1 + 0.35, T)) * (T >= t0)
    ph = 2 * np.pi * np.cumsum(fr * (T >= t0)) / SR
    return (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)) * env * db(gain_db)


L = np.zeros(N)
R = np.zeros(N)

# ambient bed: three slightly detuned voices (A1, A2, E3) with slow movement, lifting as the shot opens up
bed_env = 0.35 + 0.65 * smooth(0.0, 2.4, T)
for f, g, d in ((55.0, -23.0, 0.18), (110.0, -25.0, 0.25), (164.8, -29.0, 0.3), (220.0, -33.0, 0.35)):
    vib = 1 + 0.0025 * np.sin(2 * np.pi * 0.23 * T)
    L += np.sin(2 * np.pi * np.cumsum(f * (1 - d * 0.01) * vib) / SR) * db(g) * bed_env
    R += np.sin(2 * np.pi * np.cumsum(f * (1 + d * 0.01) * vib) / SR + 0.7) * db(g) * bed_env
air = band_noise(2500, 9000)
L += air * db(-50) * bed_env
R += np.roll(air, 211) * db(-50) * bed_env

# opening: a low whoosh as the camera glides in
L += swell(0.0, 0.55, 1.15, 250, 1600, -25)
R += swell(0.02, 0.57, 1.17, 250, 1600, -25)

# the layers come apart: a rising swell plus a short air burst for each layer
L += swell(0.85, 1.9, 2.9, 180, 5200, -22)
R += swell(0.87, 1.92, 2.92, 180, 5200, -22)
for t0, f_lo, f_hi, side in ((0.95, 700, 3200, 0.8), (1.08, 500, 2600, 0.5), (1.22, 380, 2000, 0.3), (1.36, 300, 1500, 0.2)):
    burst = band_noise(f_lo, f_hi) * np.exp(-np.clip(T - t0, 0, None) / 0.12) * (T >= t0) * db(-28)
    L += burst * (1 - side * 0.4)
    R += burst * (1 + side * 0.4)
thumps = thump(0.95, 52, 0.7, -17)
L += thumps
R += thumps

# label ticks (left labels on the left, right labels on the right)
for t0, side, f in ((1.95, 1, 2100), (2.20, 1, 2300), (2.45, 1, 2500), (2.70, -1, 1900), (2.95, -1, 2100), (3.20, -1, 2300)):
    b = blip(t0, f, f * 1.25, 0.14, -25, 0.04)
    L += b * (0.55 if side > 0 else 1.0)
    R += b * (1.0 if side > 0 else 0.55)

# the die lights up: sub hit, rising sweep, shimmer; then the kicker title lands
hit = thump(3.20, 46, 0.9, -15)
L += hit
R += hit
sw = sweep(3.2, 4.2, 180.0, 2400.0, -27)
L += sw
R += sw * 0.96
shim = band_noise(5000, 12000) * np.exp(-np.clip(T - 3.74, 0, None) / 0.35) * (T >= 3.74) * db(-33)
L += shim
R += np.roll(shim, 97)
k_hit = thump(3.74, 58, 0.6, -19)
L += k_hit
R += k_hit

# tiny data chirps while the pulses run across the interposer
for t0 in np.sort(rng.uniform(3.35, 4.85, 22)):
    f = float(rng.choice([2400, 3000, 3600, 4200, 4800]))
    c = blip(float(t0), f, f * 1.12, 0.05, -34, 0.014)
    pan = rng.uniform(0.3, 1.0)
    L += c * pan
    R += c * (1.3 - pan)

# gentle fade in/out so the file does not click
fade = smooth(0.0, 0.05, T) * (1 - smooth(DUR - 0.30, DUR, T))
L *= fade
R *= fade
peak = max(np.abs(L).max(), np.abs(R).max())
scale = 0.85 / peak
pcm = (np.stack([L, R], axis=1) * scale * 32767).astype("<i2")
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", sys.argv[1], "peak before scaling %.3f" % peak)
