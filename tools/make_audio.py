#!/usr/bin/env python3
"""Sound for one video: a quiet music bed and small sound effects, mixed under the voice-over.

usage:
  python3 tools/make_audio.py --voice voice.wav --cues cues.json --duration 57.309 --out outdir

Everything is synthesised here (nothing to license). Writes into outdir:
  voice_proc.wav  the voice after EQ and light compression (48 kHz mono)
  music.wav, sfx.wav  the two stems, before ducking
  mix.wav         the final mix, 48 kHz stereo, about -14 LUFS, true peak below -1.5 dB
The cue list comes from tools/dump_cues.js (the scene says when things appear on screen).
"""
import argparse
import json
import math
import os
import re
import subprocess

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
rng = np.random.default_rng(20261029)


# ------------------------------------------------------------------ helpers
def db(x):
    return 10.0 ** (x / 20.0)


def rms_db(x):
    return 20.0 * math.log10(math.sqrt(float(np.mean(np.square(x)))) + 1e-12)


def scale_rms(x, target_db):
    return x * db(target_db - rms_db(x))


def scale_peak(x, target_db):
    return x * (db(target_db) / (float(np.max(np.abs(x))) + 1e-12))


def sos_filter(x, kind, fc, order=2):
    sos = signal.butter(order, fc, kind, fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def midi_hz(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def stereo(x, pan=0.0):
    """Mono to stereo with constant-power pan (-1 left .. 1 right)."""
    left = math.sqrt((1.0 - pan) / 2.0)
    right = math.sqrt((1.0 + pan) / 2.0)
    return np.stack([x * left, x * right], axis=1)


def put(buf, sig, t):
    i = int(round(t * SR))
    if i >= len(buf):
        return
    if i < 0:
        sig = sig[-i:]
        i = 0
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


def reverb_ir(seconds=2.0, decay=0.5, damp=5500.0):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-t / decay)[:, None]
    ir = sos_filter(ir, "low", damp)
    pre = int(0.015 * SR)
    ir[:pre] = 0.0
    ir[pre: pre + 400] *= np.linspace(0.0, 1.0, 400)[:, None]
    return ir / math.sqrt(float(np.sum(ir ** 2)) / 2.0)


IR = reverb_ir()


def reverb(x, wet):
    out = np.zeros_like(x)
    for ch in range(2):
        out[:, ch] = signal.fftconvolve(x[:, ch], IR[:, ch])[: len(x)]
    return x * (1.0 - wet) + out * wet * 0.35


# ------------------------------------------------------------------ music
BPM = None
CHORDS = {                     # pad voicing, bass note, arp notes (MIDI)
    "Am": ([57, 60, 64, 69], 33, [69, 72, 76, 81]),
    "F": ([57, 60, 65, 69], 29, [65, 69, 72, 77]),
    "C": ([55, 60, 64, 67], 36, [67, 72, 76, 79]),
    "G": ([55, 59, 62, 67], 31, [67, 71, 74, 79]),
}
PROGRESSION = ["Am", "F", "C", "G", "Am", "F", "C", "G", "F", "Am"]


def saw_voice(freq, n, detunes):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for d in detunes:
        out += signal.sawtooth(2.0 * np.pi * (freq * 2.0 ** (d / 1200.0) * t + rng.uniform()))
    return out / len(detunes)


def make_music(total):
    n = int(total * SR)
    beats_total = 8 * len(PROGRESSION)
    beat = total / beats_total
    chord_len = 8 * beat
    step = beat / 2.0
    print("music: %d chords, tempo %.1f BPM, chord %.2fs" % (len(PROGRESSION), 60.0 / beat, chord_len), flush=True)

    # ---- pad
    pad = np.zeros((n, 2))
    overlap = 1.1
    for c, name in enumerate(PROGRESSION):
        notes, _, _ = CHORDS[name]
        s = c * chord_len
        length = chord_len + overlap
        m = int(length * SR)
        seg = np.zeros((m, 2))
        for note in notes:
            f = midi_hz(note)
            seg[:, 0] += saw_voice(f, m, (-10, -3, 5))
            seg[:, 1] += saw_voice(f, m, (-5, 3, 10))
        t = np.arange(m) / SR
        fade_in = np.clip(t / overlap, 0, 1)
        fade_out = np.clip((length - t) / overlap, 0, 1)
        env = np.sin(0.5 * np.pi * fade_in) * np.sin(0.5 * np.pi * fade_out)
        put(pad, seg * env[:, None], s)
    # a slowly moving filter: three fixed low-passes blended by slow LFOs
    lows = [sos_filter(pad, "low", fc, 4) for fc in (550.0, 950.0, 1600.0)]
    tt = np.arange(n) / SR
    w = [0.5 + 0.5 * np.sin(2 * np.pi * tt / 17.0 + ph) for ph in (0.0, 2.1, 4.2)]
    norm = w[0] + w[1] + w[2]
    pad = sum(lows[i] * (w[i] / norm)[:, None] for i in range(3))
    pad *= (0.88 + 0.12 * np.sin(2 * np.pi * tt / 8.3))[:, None]
    pad = scale_rms(pad, -31.0)

    # ---- bass (mostly felt on headphones)
    bass = np.zeros(n)
    for c, name in enumerate(PROGRESSION):
        _, root, _ = CHORDS[name]
        f = midi_hz(root)
        m = int((chord_len + 0.3) * SR)
        t = np.arange(m) / SR
        tone = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
        env = np.clip(t / 0.25, 0, 1) * np.clip((chord_len + 0.3 - t) / 0.3, 0, 1)
        put(bass, tone * env, c * chord_len)
    bass = stereo(scale_rms(bass, -37.0))

    # ---- arpeggio
    arp = np.zeros((n, 2))
    pattern = [0, 1, 2, 3, 2, 1, 2, 1] * 2
    accent = [1.0, 0.55, 0.7, 0.55] * 4
    for c, name in enumerate(PROGRESSION):
        _, _, tones = CHORDS[name]
        for k in range(16):
            f = midi_hz(tones[pattern[k]])
            m = int(0.8 * SR)
            t = np.arange(m) / SR
            tone = (np.sin(2 * np.pi * f * t) + 0.32 * np.sin(2 * np.pi * 2 * f * t)
                    + 0.10 * np.sin(2 * np.pi * 3 * f * t))
            env = np.exp(-t / 0.17) * (1.0 - np.exp(-t / 0.004))
            pan = -0.35 if k % 2 == 0 else 0.35
            put(arp, stereo(tone * env * accent[k] * (0.85 + 0.3 * rng.uniform()), pan), c * chord_len + k * step)
    arp = sos_filter(arp, "low", 4200.0)
    dry = arp.copy()
    delay = int(1.5 * step * SR)                       # dotted eighth
    for rep in range(1, 5):
        shifted = np.zeros_like(dry)
        off = delay * rep
        if off < n:
            shifted[off:] = dry[: n - off]
        shifted = sos_filter(shifted, "low", 3000.0)
        if rep % 2 == 1:
            shifted = shifted[:, ::-1]                 # ping-pong
        arp += shifted * (0.4 ** rep) * 1.6
    arp = reverb(arp, 0.35)
    arp = scale_rms(arp, -35.0)

    # ---- soft kick on beats 1 and 3, quiet hats on the off-beats
    kick = np.zeros((n, 2))
    k_len = int(0.35 * SR)
    kt = np.arange(k_len) / SR
    freq = 46.0 + 70.0 * np.exp(-kt / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-kt / 0.13) * (1 - np.exp(-kt / 0.002))
    click = sos_filter(rng.standard_normal(k_len), "low", 2800.0) * np.exp(-kt / 0.006) * 0.6
    kick_sig = stereo(body + click)
    for b in range(0, beats_total, 2):
        put(kick, kick_sig, b * beat)
    kick = scale_peak(kick, -19.0)
    hats = np.zeros((n, 2))
    h_len = int(0.06 * SR)
    ht = np.arange(h_len) / SR
    hat = sos_filter(rng.standard_normal(h_len), "high", 7500.0) * np.exp(-ht / 0.014)
    for b in range(beats_total):
        put(hats, stereo(hat * (0.6 + 0.4 * rng.uniform()), 0.25), b * beat + beat / 2.0)
    hats = scale_peak(hats, -38.0)

    music = pad + bass + arp + kick + hats
    fade_in = np.clip(tt / 0.6, 0, 1)
    fade_out = np.clip((total - tt) / 1.6, 0, 1)
    music *= (np.sin(0.5 * np.pi * fade_in) * np.sin(0.5 * np.pi * fade_out))[:, None]
    return music


# ------------------------------------------------------------------ sound effects
def sfx_pop(freq):
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.14)
         + 0.35 * np.sin(2 * np.pi * freq * 2.0 * t) * np.exp(-t / 0.07)
         + 0.12 * np.sin(2 * np.pi * freq * 3.0 * t) * np.exp(-t / 0.035))
    return y * (1 - np.exp(-t / 0.0015))


def sfx_tick(freq):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.04) * (1 - np.exp(-t / 0.001))


def sfx_whoosh(dur=0.8, f0=200.0, f1=6000.0, sigma=0.75, up=True):
    n = int(dur * SR)
    out = np.zeros((n, 2))
    for ch in range(2):
        x = rng.standard_normal(n)
        f, tt, z = signal.stft(x, fs=SR, nperseg=1024, noverlap=768)
        tau = np.clip(tt / dur, 0.0, 1.0)
        if not up:
            tau = 1.0 - tau
        fc = f0 * (f1 / f0) ** tau
        lf = np.log(np.maximum(f, 20.0))[:, None]
        mask = np.exp(-0.5 * ((lf - np.log(fc)[None, :]) / sigma) ** 2)
        _, y = signal.istft(z * mask, fs=SR, nperseg=1024, noverlap=768)
        y = y[:n] if len(y) >= n else np.pad(y, (0, n - len(y)))
        out[:, ch] = y
    u = np.arange(n) / n
    env = np.sin(np.pi * u ** 0.8) ** 2
    return out * env[:, None]


def sfx_impact():
    n = int(1.8 * SR)
    t = np.arange(n) / SR
    freq = 38.0 + 110.0 * np.exp(-t / 0.09)
    boom = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.5) * (1 - np.exp(-t / 0.002))
    hit = sos_filter(rng.standard_normal(n), "low", 4500.0) * np.exp(-t / 0.12)
    return stereo(boom + 0.22 * hit)


def sfx_stamp():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    freq = 52.0 + 90.0 * np.exp(-t / 0.03)
    thud = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.11) * (1 - np.exp(-t / 0.001))
    click = sos_filter(rng.standard_normal(n), "band", [900.0, 5000.0]) if False else \
        signal.sosfilt(signal.butter(2, [900.0, 5000.0], "band", fs=SR, output="sos"), rng.standard_normal(n))
    return stereo(thud + 0.35 * click * np.exp(-t / 0.012))


def sfx_warn():
    out = np.zeros(int(0.35 * SR))
    for off in (0.0, 0.12):
        m = int(0.07 * SR)
        t = np.arange(m) / SR
        beep = np.sin(2 * np.pi * 880.0 * t) * np.sin(np.pi * t / 0.07) ** 2
        out[int(off * SR): int(off * SR) + m] += beep
    return stereo(out)


PENTA = [880.0, 1318.5, 1046.5, 1568.0, 1174.7, 880.0, 1318.5, 1046.5]
HOOK_NOTES = [880.0, 1046.5, 1174.7, 1318.5, 1568.0, 1760.0, 2093.0]


def make_sfx(cues, total):
    n = int(total * SR)
    buf = np.zeros((n, 2))
    pop_i = 0
    for cue in cues:
        t, kind = cue["t"], cue["k"]
        if kind == "pop":
            f = PENTA[pop_i % len(PENTA)]
            pop_i += 1
            put(buf, scale_peak(stereo(sfx_pop(f), 0.0), -21.0), t)
        elif kind == "tick":
            put(buf, scale_peak(stereo(sfx_tick(2093.0), 0.0), -28.0), t)
        elif kind == "hook":
            i = cue.get("n", 0)
            put(buf, scale_peak(stereo(sfx_pop(HOOK_NOTES[i % len(HOOK_NOTES)])), -22.0), t)
            if i == 0:
                put(buf, scale_peak(sfx_impact()[: int(0.9 * SR)], -16.0), t - 0.02)
        elif kind == "whoosh":
            w = scale_peak(sfx_whoosh(0.95, 180.0, 5200.0), -21.0)
            put(buf, w, t - 0.42)
        elif kind == "row":
            w = scale_peak(sfx_whoosh(0.5, 300.0, 2600.0, 0.6), -29.0)
            put(buf, w, t - 0.1)
        elif kind == "impact":
            put(buf, scale_peak(sfx_whoosh(1.0, 250.0, 7000.0, 0.9), -24.0), t - 0.95)
            put(buf, scale_peak(sfx_impact(), -9.0), t)
        elif kind == "stamp":
            put(buf, scale_peak(sfx_stamp(), -14.0), t)
        elif kind == "warn":
            put(buf, scale_peak(sfx_warn(), -26.0), t)
        elif kind == "cta":
            for j, f in enumerate((880.0, 1046.5, 1318.5, 1760.0)):
                put(buf, scale_peak(stereo(sfx_pop(f), -0.3 + 0.2 * j), -22.0), t + 0.07 * j)
            put(buf, scale_peak(sfx_whoosh(0.7, 500.0, 6000.0), -26.0), t - 0.3)
    return reverb(buf, 0.22)


# ------------------------------------------------------------------ voice and mix
def run(cmd):
    out = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return out.stderr


def duck_curve(voice, depth_db=8.0):
    """Gain for the music: dips while the voice speaks (attack 40 ms, release 450 ms)."""
    block = 240                                          # 5 ms
    nb = len(voice) // block
    env = np.sqrt(np.mean(voice[: nb * block].reshape(nb, block) ** 2, axis=1) + 1e-12)
    env_db = 20 * np.log10(env)
    target = np.clip((env_db - (-46.0)) / ((-30.0) - (-46.0)), 0.0, 1.0)
    att = math.exp(-1.0 / (0.04 / (block / SR) * 1.0))
    rel = math.exp(-1.0 / (0.45 / (block / SR) * 1.0))
    g = np.zeros(nb)
    cur = 0.0
    for i in range(nb):
        coef = att if target[i] > cur else rel
        cur = coef * cur + (1.0 - coef) * target[i]
        g[i] = cur
    gain_db = -depth_db * g
    x = (np.arange(nb) + 0.5) * block
    full = np.interp(np.arange(len(voice)), x, db(gain_db))
    return full


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", required=True)
    ap.add_argument("--cues", required=True)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    total = args.duration + 0.05
    n = int(total * SR)

    # voice: tidy EQ, light compression, 48 kHz
    vp = os.path.join(args.out, "voice_proc.wav")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", args.voice, "-af",
         "aresample=48000,highpass=f=75,equalizer=f=3200:t=q:w=1.0:g=2.0,"
         "acompressor=threshold=-24dB:ratio=3:attack=6:release=120:makeup=5dB,alimiter=limit=0.85",
         "-ac", "1", "-c:a", "pcm_s16le", vp])
    sr, voice = wavfile.read(vp)
    assert sr == SR, sr
    voice = voice.astype(np.float64) / 32768.0
    voice = np.pad(voice, (0, max(0, n - len(voice))))[:n]
    print("voice: peak %.1f dBFS, rms %.1f dBFS" % (20 * math.log10(np.max(np.abs(voice))), rms_db(voice[voice != 0])), flush=True)

    cues = json.load(open(args.cues))
    music = make_music(total)
    sfx = make_sfx(cues, total)
    wavfile.write(os.path.join(args.out, "music.wav"), SR, music.astype(np.float32))
    wavfile.write(os.path.join(args.out, "sfx.wav"), SR, sfx.astype(np.float32))

    duck = duck_curve(voice, 8.0)
    mix = stereo(voice) + music * duck[:, None] + sfx
    wavfile.write(os.path.join(args.out, "mix_raw.wav"), SR, mix.astype(np.float32))
    peak = float(np.max(np.abs(mix)))
    print("raw mix: peak %.1f dBFS" % (20 * math.log10(peak)), flush=True)

    # loudness: two-pass loudnorm to -14 LUFS, true peak -1.5 dB
    raw = os.path.join(args.out, "mix_raw.wav")
    log = run(["ffmpeg", "-hide_banner", "-nostats", "-i", raw, "-af",
               "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    stats = json.loads(re.search(r"\{[^{}]*\}", log[log.rfind("{"):], re.S).group(0))
    print("measured:", {k: stats[k] for k in ("input_i", "input_tp", "input_lra", "input_thresh")}, flush=True)
    af = ("loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:"
          "offset=%s:linear=true:print_format=summary" % (
              stats["input_i"], stats["input_tp"], stats["input_lra"], stats["input_thresh"], stats["target_offset"]))
    final = os.path.join(args.out, "mix.wav")
    log2 = run(["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", raw, "-af", af + ",aresample=48000",
                "-c:a", "pcm_s16le", final])
    print(log2[-700:], flush=True)


if __name__ == "__main__":
    main()
