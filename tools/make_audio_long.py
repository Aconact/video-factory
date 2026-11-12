#!/usr/bin/env python3
"""Sound for a long video (several minutes): a quiet looping music bed and small sound effects under the voice-over.

usage:
  python3 tools/make_audio_long.py --voice voice.wav --cues cues.json --duration 605.843 --out outdir \
      [--drums 0-16.5,526.7-606]

It reuses the synthesis code of make_audio.py (everything is made here, nothing to license).
The music is one 60-second loop (80 BPM, ten chords) built so that its end runs into its start,
repeated for the whole video; kick and hats play only in the listed time ranges.
Writes voice_proc.wav, mix_raw.wav and mix.wav (48 kHz stereo, about -14 LUFS, true peak below -1.5 dB).
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys

import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import uniform_filter1d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_audio as A  # noqa: E402

SR = A.SR
LOOP = 60.0
TAIL = 6.0
BEAT = 0.75                      # 80 BPM; ten chords of eight beats = 60 s


def wrap(x, n_loop, n_tail):
    """Fold the part after the loop end back onto the start, so the loop joins without a seam."""
    out = x[:n_loop].copy()
    t = x[n_loop:n_loop + n_tail]
    out[:len(t)] += t
    return out


def loop_stems():
    rng, put, stereo, sos_filter, midi_hz = A.rng, A.put, A.stereo, A.sos_filter, A.midi_hz
    scale_rms, scale_peak, db = A.scale_rms, A.scale_peak, A.db
    N = int(LOOP * SR)
    NT = int(TAIL * SR)
    n = N + NT
    chord_len, step = 8 * BEAT, BEAT / 2.0
    prog = A.PROGRESSION
    assert abs(len(prog) * chord_len - LOOP) < 1e-6
    tt = np.arange(n) / SR

    # ---- pad
    pad = np.zeros((n, 2))
    overlap = 1.1
    for c, name in enumerate(prog):
        notes, _, _ = A.CHORDS[name]
        length = chord_len + overlap
        m = int(length * SR)
        seg = np.zeros((m, 2))
        for note in notes:
            f = midi_hz(note)
            seg[:, 0] += A.saw_voice(f, m, (-10, -3, 5))
            seg[:, 1] += A.saw_voice(f, m, (-5, 3, 10))
        t = np.arange(m) / SR
        env = np.sin(0.5 * np.pi * np.clip(t / overlap, 0, 1)) * np.sin(0.5 * np.pi * np.clip((length - t) / overlap, 0, 1))
        put(pad, seg * env[:, None], c * chord_len)
    lows = [sos_filter(pad, "low", fc, 4) for fc in (550.0, 950.0, 1600.0)]
    w = [0.5 + 0.5 * np.sin(2 * np.pi * tt / 20.0 + ph) for ph in (0.0, 2.1, 4.2)]          # periods divide the loop length
    norm = w[0] + w[1] + w[2]
    pad = sum(lows[i] * (w[i] / norm)[:, None] for i in range(3))
    pad *= (0.88 + 0.12 * np.sin(2 * np.pi * tt / 7.5))[:, None]
    del lows
    pad = scale_rms(pad, -31.0)

    # ---- bass
    bass = np.zeros(n)
    for c, name in enumerate(prog):
        _, root, _ = A.CHORDS[name]
        f = midi_hz(root)
        m = int((chord_len + 0.3) * SR)
        t = np.arange(m) / SR
        tone = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
        env = np.clip(t / 0.25, 0, 1) * np.clip((chord_len + 0.3 - t) / 0.3, 0, 1)
        put(bass, tone * env, c * chord_len)
    bass = stereo(scale_rms(bass, -37.0))

    # ---- arpeggio with a dotted-eighth echo
    arp = np.zeros((n, 2))
    pattern = [0, 1, 2, 3, 2, 1, 2, 1] * 2
    accent = [1.0, 0.55, 0.7, 0.55] * 4
    for c, name in enumerate(prog):
        _, _, tones = A.CHORDS[name]
        for k in range(16):
            f = midi_hz(tones[pattern[k]])
            m = int(0.8 * SR)
            t = np.arange(m) / SR
            tone = (np.sin(2 * np.pi * f * t) + 0.32 * np.sin(2 * np.pi * 2 * f * t) + 0.10 * np.sin(2 * np.pi * 3 * f * t))
            env = np.exp(-t / 0.17) * (1.0 - np.exp(-t / 0.004))
            pan = -0.35 if k % 2 == 0 else 0.35
            put(arp, stereo(tone * env * accent[k] * (0.85 + 0.3 * rng.uniform()), pan), c * chord_len + k * step)
    arp = sos_filter(arp, "low", 4200.0)
    dry = arp.copy()
    delay = int(1.5 * step * SR)
    for rep in range(1, 5):
        shifted = np.zeros_like(dry)
        off = delay * rep
        if off < n:
            shifted[off:] = dry[: n - off]
        shifted = sos_filter(shifted, "low", 3000.0)
        if rep % 2 == 1:
            shifted = shifted[:, ::-1]
        arp += shifted * (0.4 ** rep) * 1.6
    arp = A.reverb(arp, 0.35)
    arp = scale_rms(arp, -35.0)

    # ---- drums: soft kick on beats 1 and 3, quiet hats on the off-beats
    beats_total = int(round(LOOP / BEAT))
    kick = np.zeros((n, 2))
    k_len = int(0.35 * SR)
    kt = np.arange(k_len) / SR
    freq = 46.0 + 70.0 * np.exp(-kt / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-kt / 0.13) * (1 - np.exp(-kt / 0.002))
    click = sos_filter(rng.standard_normal(k_len), "low", 2800.0) * np.exp(-kt / 0.006) * 0.6
    kick_sig = stereo(body + click)
    for b in range(0, beats_total, 2):
        put(kick, kick_sig, b * BEAT)
    kick = scale_peak(kick, -19.0)
    hats = np.zeros((n, 2))
    h_len = int(0.06 * SR)
    ht = np.arange(h_len) / SR
    hat = sos_filter(rng.standard_normal(h_len), "high", 7500.0) * np.exp(-ht / 0.014)
    for b in range(beats_total):
        put(hats, stereo(hat * (0.6 + 0.4 * rng.uniform()), 0.25), b * BEAT + BEAT / 2.0)
    hats = scale_peak(hats, -38.0)

    stems = {"bed": pad + bass + arp, "drums": kick + hats}
    return {k: wrap(v, N, NT).astype(np.float32) for k, v in stems.items()}


def tile(x, n):
    reps = int(math.ceil(n / len(x)))
    return np.tile(x, (reps, 1))[:n]


def reverb_oa(x, wet):
    """Same as make_audio.reverb, but overlap-add so a ten-minute buffer does not need one giant FFT."""
    out = np.zeros_like(x)
    for ch in range(2):
        out[:, ch] = signal.oaconvolve(x[:, ch], A.IR[:, ch])[: len(x)]
    return x * (1.0 - wet) + out * wet * 0.35


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", required=True)
    ap.add_argument("--cues", required=True)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--drums", default="")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    total = args.duration + 0.05
    n = int(total * SR)

    vp = os.path.join(args.out, "voice_proc.wav")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", args.voice, "-af",
         "aresample=48000,highpass=f=75,equalizer=f=3200:t=q:w=1.0:g=2.0,"
         "acompressor=threshold=-24dB:ratio=3:attack=6:release=120:makeup=5dB,alimiter=limit=0.85",
         "-ac", "1", "-c:a", "pcm_s16le", vp])
    sr, voice = wavfile.read(vp)
    assert sr == SR, sr
    voice = np.pad(voice.astype(np.float32) / 32768.0, (0, max(0, n - len(voice))))[:n]
    print("voice: peak %.1f dBFS, rms %.1f dBFS" % (20 * math.log10(float(np.max(np.abs(voice)))), A.rms_db(voice[voice != 0])), flush=True)

    print("music loop ...", flush=True)
    stems = loop_stems()
    bed = tile(stems["bed"], n)
    drums = tile(stems["drums"], n)
    g = np.zeros(n, dtype=np.float32)
    for part in [p for p in args.drums.split(",") if p]:
        a, b = [float(v) for v in part.split("-")]
        g[int(a * SR): int(b * SR)] = 1.0
    g = uniform_filter1d(g, size=SR, mode="nearest")                      # one-second smoothing
    music = bed + drums * g[:, None]
    tt = np.arange(n, dtype=np.float32) / SR
    music *= (np.sin(0.5 * np.pi * np.clip(tt / 0.6, 0, 1)) * np.sin(0.5 * np.pi * np.clip((total - tt) / 2.5, 0, 1)))[:, None]
    del bed, drums, g, tt

    print("sound effects ...", flush=True)
    A.reverb = reverb_oa                                                  # make_sfx looks this name up when it runs
    sfx = A.make_sfx(json.load(open(args.cues)), total).astype(np.float32)

    print("mix ...", flush=True)
    duck = A.duck_curve(voice.astype(np.float64), 8.0).astype(np.float32)
    c = math.sqrt(0.5)
    mix = np.empty((n, 2), dtype=np.float32)
    for ch in range(2):
        mix[:, ch] = voice * c + music[:, ch] * duck + sfx[:, ch]
    raw = os.path.join(args.out, "mix_raw.wav")
    wavfile.write(raw, SR, mix)
    print("raw mix: peak %.1f dBFS" % (20 * math.log10(float(np.max(np.abs(mix))))), flush=True)
    del mix, music, sfx, duck

    log = run(["ffmpeg", "-hide_banner", "-nostats", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    stats = json.loads(re.search(r"\{[^{}]*\}", log[log.rfind("{"):], re.S).group(0))
    print("measured:", {k: stats[k] for k in ("input_i", "input_tp", "input_lra", "input_thresh")}, flush=True)
    af = ("loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true:print_format=summary"
          % (stats["input_i"], stats["input_tp"], stats["input_lra"], stats["input_thresh"], stats["target_offset"]))
    final = os.path.join(args.out, "mix.wav")
    log2 = run(["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", raw, "-af", af + ",aresample=48000", "-c:a", "pcm_s16le", final])
    print(log2[-600:], flush=True)


if __name__ == "__main__":
    main()
