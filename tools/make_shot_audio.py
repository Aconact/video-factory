"""Synthesised sound design for the package test shot (5 s, 48 kHz stereo), version 2.

Everything is generated (numpy/scipy only, no samples, no licences to worry about):
  * a soft evolving pad (A minor, lifting a chord when the die lights) plus a sub-bass bed
  * metal "slide + tick" foley (modal resonators) when the layers of the package lift apart
  * a glint whoosh for the light that sweeps across the lid
  * a rising pentatonic bell for each label, panned to the side the label appears on
  * tiny clicks as the memory stacks come apart (top die first)
  * sub hit + rising power-up sweep when the die lights, an impact on the kicker title, tiny data chirps afterwards
  * a synthetic room (decaying stereo noise impulse response) so every sound sits in the same space

    python3 tools/make_shot_audio.py out.wav [target_lufs]

The result is polished synthetic sound, not a recording: real foley or licensed music would still sound richer.
"""
import subprocess
import sys
import wave

import numpy as np
from scipy import signal

SR = 48000
DUR = 5.0
N = int(SR * DUR)
T = np.arange(N) / SR
rng = np.random.default_rng(7)


def db(x):
    return 10 ** (x / 20.0)


def smooth(a, b, t):
    k = np.clip((t - a) / (b - a), 0, 1)
    return k * k * (3 - 2 * k)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, min(hi, SR / 2 - 200)], btype="bandpass", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="lowpass", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="highpass", fs=SR, output="sos"), x)


DRY = np.zeros((2, N))
SEND = np.zeros(N)


def place(sig, t0, gain_db=0.0, pan=0.0, wet_db=-12.0):
    """Mix a short signal into the dry bus at t0 (seconds); `wet_db` is how much of it goes to the room."""
    i0 = int(round(t0 * SR))
    if i0 >= N:
        return
    n = min(len(sig), N - i0)
    s = sig[:n] * db(gain_db)
    ang = (pan + 1.0) * np.pi / 4.0
    DRY[0, i0:i0 + n] += s * np.cos(ang)
    DRY[1, i0:i0 + n] += s * np.sin(ang)
    SEND[i0:i0 + n] += s * db(wet_db)


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def modal(f0, ratios, decays, amps, dur):
    t = tt(dur)
    out = np.zeros_like(t)
    for r, d, a in zip(ratios, decays, amps):
        out += a * np.sin(2 * np.pi * f0 * r * t + rng.uniform(0, 6.28)) * np.exp(-t / d)
    return out


def tick(dur=0.02):
    """A very short filtered click (the 'contact' part of a mechanical sound)."""
    t = tt(dur)
    return hp(rng.standard_normal(len(t)), 1800) * np.exp(-t / (dur / 4.0))


def metal_slide(f0, length=0.55):
    """A plate sliding off the stack: a scrape of band-passed noise under a ringing metal tone."""
    t = tt(length)
    scrape = bp(rng.standard_normal(len(t)), 1800, 6500) * (smooth(0, 0.04, t) * (1 - smooth(0.12, 0.45, t))) * 0.35
    ring = modal(f0, (1.0, 2.76, 5.40, 8.93), (0.28, 0.17, 0.09, 0.05), (1.0, 0.55, 0.30, 0.16), length)
    return scrape + ring * 0.8 + np.pad(tick(), (0, max(0, len(t) - int(0.02 * SR))))[:len(t)] * 0.6


def bell(f, dur=0.5):
    t = tt(dur)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t / (dur * 0.30)) + 0.40 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / (dur * 0.14)) +
            0.18 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / (dur * 0.07)))


def thump(f, length, drop=1.6):
    t = tt(length)
    fr = f * (1 + drop * np.exp(-t * 18))
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / (length / 4.0)) * smooth(0, 0.004, t)


def whoosh(length, f_lo, f_hi, bands=7):
    """Band-passed noise whose centre glides from f_lo to f_hi (cross-faded filter bank), shaped like a swell."""
    t = tt(length)
    freqs = np.geomspace(f_lo, f_hi, bands)
    pos = np.linspace(0, length, bands)
    out = np.zeros_like(t)
    for f, p in zip(freqs, pos):
        w = np.exp(-0.5 * ((t - p) / (length / (bands * 0.9))) ** 2)
        out += bp(rng.standard_normal(len(t)), f * 0.7, f * 1.4) * w
    env = np.sin(np.pi * np.clip(t / length, 0, 1)) ** 1.8
    return out * env / np.sqrt(bands) * 3.0


def sweep(length, f0, f1):
    t = tt(length)
    k = t / length
    fr = f0 * (f1 / f0) ** (k ** 1.5)
    ph = 2 * np.pi * np.cumsum(fr) / SR
    env = smooth(0, length * 0.7, t) * (1 - smooth(length - 0.12, length + 0.3, t))
    return (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)) * env


# ---------------------------------------------------------------- pad + sub bed
pad_lo = np.zeros(N)
pad_hi = np.zeros(N)
for f in (110.0, 164.81, 220.0, 261.63, 329.63):
    for det in (-0.0023, 0.0023):
        saw = signal.sawtooth(2 * np.pi * np.cumsum(np.full(N, f * (1 + det))) / SR + rng.uniform(0, 6.28))
        pad_lo += lp(saw, 420)
        pad_hi += lp(saw, 2200)
open_f = smooth(0.0, 3.6, T)
pad = (pad_lo * (1 - open_f) + pad_hi * open_f) / 10.0
lift = np.zeros(N)                         # a brighter open fifth joins when the die lights up
for f in (246.94, 369.99, 493.88):
    lift += lp(signal.sawtooth(2 * np.pi * np.cumsum(np.full(N, f)) / SR), 3000) * 0.33
pad += lift * smooth(3.2, 3.8, T) * 0.55
pad *= (0.30 + 0.70 * smooth(0.0, 1.6, T)) * (1.0 + 0.10 * np.sin(2 * np.pi * 0.25 * T))
sub = np.sin(2 * np.pi * np.cumsum(np.full(N, 55.0)) / SR) * (0.4 + 0.6 * smooth(0.0, 1.0, T))
for ch, d in ((0, -0.0006), (1, 0.0006)):
    DRY[ch] += pad * db(-24.0) + sub * db(-27.0)
SEND += pad * db(-34.0)
air = bp(rng.standard_normal(N), 2800, 9500) * db(-52.0) * (0.3 + 0.7 * smooth(0.0, 2.4, T))
DRY[0] += air
DRY[1] += np.roll(air, 211)

# ---------------------------------------------------------------- opening glide and the glint on the lid
place(whoosh(0.9, 250, 1800), 0.0, -26.0, pan=-0.2, wet_db=-8.0)
place(whoosh(0.75, 600, 5200), 1.0, -25.0, pan=0.35, wet_db=-6.0)         # the light sweeping across the lid

# ---------------------------------------------------------------- the layers lift apart (lid, pad, interposer, die)
for t0, f0, pan in ((0.98, 520.0, 0.5), (1.18, 430.0, 0.2), (1.40, 360.0, -0.2), (1.62, 300.0, -0.5)):
    place(metal_slide(f0), t0, -21.0, pan, wet_db=-9.0)
place(whoosh(2.0, 180, 4800), 0.9, -28.0, pan=0.0, wet_db=-6.0)
place(thump(52.0, 0.7), 0.98, -19.0, 0.0, wet_db=-14.0)

# ---------------------------------------------------------------- label bells (right labels first, then left)
for t0, f, pan in ((1.95, 659.3, 0.55), (2.20, 784.0, 0.55), (2.45, 880.0, 0.55), (2.70, 987.8, -0.55), (2.95, 1174.7, -0.55), (3.20, 1318.5, -0.55)):
    place(bell(f), t0, -25.0, pan, wet_db=-5.0)
    place(tick(), t0, -33.0, pan, wet_db=-20.0)

# ---------------------------------------------------------------- memory stacks come apart (top die first), 8 small clicks
for k in range(8):
    t0 = (92.0 + (7 - k) * 1.2) / 30.0
    clk = modal(1500.0 + 110.0 * (7 - k), (1.0, 2.76), (0.05, 0.03), (1.0, 0.4), 0.18)
    clk[:int(0.02 * SR)] += tick() * 0.8
    place(clk, t0, -31.0, pan=rng.uniform(-0.6, 0.6), wet_db=-10.0)

# ---------------------------------------------------------------- the die lights up; the kicker lands
place(thump(46.0, 0.9), 3.18, -15.0, 0.0, wet_db=-12.0)
place(sweep(1.1, 180.0, 2500.0), 3.18, -28.0, 0.0, wet_db=-7.0)
place(bp(rng.standard_normal(int(0.9 * SR)), 5200, 12000) * np.exp(-tt(0.9) / 0.35), 3.74, -35.0, 0.0, wet_db=-6.0)
place(thump(58.0, 0.6), 3.74, -18.0, 0.0, wet_db=-14.0)
place(modal(880.0, (1.0, 2.76, 5.40), (0.40, 0.22, 0.12), (1.0, 0.5, 0.25), 0.9), 3.74, -30.0, 0.0, wet_db=-3.0)

# ---------------------------------------------------------------- data chirps while the lines carry light
for t0 in np.sort(rng.uniform(3.35, 4.80, 20)):
    f = float(rng.choice([2400, 3000, 3600, 4200, 4800]))
    t = tt(0.05)
    chirp = np.sin(2 * np.pi * np.cumsum(f + 0.12 * f * t / 0.05) / SR) * np.exp(-t / 0.014)
    place(chirp, float(t0), -36.0, pan=rng.uniform(-0.9, 0.9), wet_db=-12.0)

# ---------------------------------------------------------------- the room
ir_t = tt(1.9)
ir = np.stack([lp(hp(rng.standard_normal(len(ir_t)), 180), 9000) * np.exp(-ir_t / 0.42) * smooth(0.0, 0.012, ir_t) for _ in range(2)])
ir += np.stack([lp(rng.standard_normal(len(ir_t)), 2500) * np.exp(-ir_t / 0.75) * 0.35 for _ in range(2)])
ir = np.concatenate([np.zeros((2, int(0.014 * SR))), ir], axis=1)
ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
WET = np.stack([signal.fftconvolve(SEND, ir[c])[:N] for c in range(2)])
mix = DRY + WET * 0.55

fade = smooth(0.0, 0.05, T) * (1 - smooth(DUR - 0.35, DUR, T))
mix *= fade
mix = np.tanh(mix * 1.1) / np.tanh(1.1)                               # gentle soft limiting


def write(path, x, gain):
    pcm = (np.clip(x * gain, -1, 1).T * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def lufs(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    for line in out.splitlines()[::-1]:
        if line.strip().startswith("I:"):
            return float(line.split()[1])
    return None


out = sys.argv[1]
target = float(sys.argv[2]) if len(sys.argv) > 2 else -14.0
peak = np.abs(mix).max()
g = 0.85 / peak
write(out, mix, g)
cur = lufs(out)
if cur is not None:
    g2 = g * db(target - cur)
    if np.abs(mix).max() * g2 > 0.84:                                  # keep ~-1.5 dB true-peak headroom
        g2 = 0.84 / np.abs(mix).max()
    write(out, mix, g2)
    print("wrote %s  (%.1f LUFS before, target %.1f, final peak %.2f)" % (out, cur, target, np.abs(mix).max() * g2))
else:
    print("wrote", out, "(loudness not measured)")
