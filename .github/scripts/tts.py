"""Voice-over for one video: Kokoro text to speech, then word timings with faster-whisper.

usage: python tts.py videos/<id>/script.json out_dir

Writes out_dir/voice.wav (all scenes joined) and out_dir/timeline.json:
  scenes[i] = {id, text, start, end, words: [{w, s, e}]}   (all times in seconds, global)
"""
import difflib
import json
import os
import re
import sys
import time

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

SR = 24000


def norm(word):
    return re.sub(r"[^a-z0-9]", "", word.lower())


def trim(samples, threshold=0.012, pad=0.05):
    loud = np.where(np.abs(samples) > threshold)[0]
    if len(loud) == 0:
        return samples
    first = max(int(loud[0]) - int(pad * SR), 0)
    last = min(int(loud[-1]) + int(pad * SR), len(samples))
    return samples[first:last]


def align(script_words, asr_words, speech_len):
    """Give every script word a (start, end) using the recognised words as anchors."""
    a = [norm(w) for w in script_words]
    b = [norm(w[0]) for w in asr_words]
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    times = [None] * len(script_words)
    matched = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                times[i1 + k] = (asr_words[j1 + k][1], asr_words[j1 + k][2])
                matched += 1
    ratio = matched / max(len(script_words), 1)

    # Fill the gaps between anchors in proportion to word length
    n = len(script_words)
    i = 0
    while i < n:
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < n and times[j] is None:
            j += 1
        left = times[i - 1][1] if i > 0 else 0.0
        right = times[j][0] if j < n else speech_len
        right = max(right, left + 0.05 * (j - i))
        weights = [max(len(norm(script_words[k])), 1) for k in range(i, j)]
        total = float(sum(weights))
        cursor = left
        for k, weight in zip(range(i, j), weights):
            span = (right - left) * weight / total
            times[k] = (cursor, cursor + span)
            cursor += span
        i = j
    return times, ratio


def main():
    script_path, out_dir = sys.argv[1], sys.argv[2]
    cfg = json.load(open(script_path, encoding="utf-8"))
    os.makedirs(out_dir, exist_ok=True)

    from faster_whisper import WhisperModel

    kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
    whisper = WhisperModel("base.en", device="cpu", compute_type="int8")

    lead = float(cfg.get("lead", 0.12))
    tail = float(cfg.get("tail", 0.3))
    pieces = []
    timeline = {"id": cfg["id"], "sample_rate": SR, "scenes": []}
    cursor = 0.0
    for scene in cfg["scenes"]:
        t0 = time.time()
        samples, sr = kokoro.create(
            scene["say"], voice=cfg.get("voice", "af_heart"),
            speed=float(cfg.get("speed", 1.0)), lang="en-us")
        assert sr == SR, sr
        samples = trim(np.asarray(samples, dtype=np.float32))
        speech_len = len(samples) / SR

        scene_lead = float(scene.get("lead", lead))
        scene_tail = float(scene.get("tail", tail))
        pieces.append(np.zeros(int(scene_lead * SR), dtype=np.float32))
        pieces.append(samples)
        pieces.append(np.zeros(int(scene_tail * SR), dtype=np.float32))

        # Word timings from a recognition pass over exactly this audio
        tmp = os.path.join(out_dir, "_scene.wav")
        sf.write(tmp, samples, SR)
        segments, _ = whisper.transcribe(tmp, language="en", word_timestamps=True, beam_size=5)
        asr_words = []
        for segment in segments:
            for word in segment.words or []:
                asr_words.append((word.word.strip(), float(word.start), float(word.end)))
        script_words = scene["text"].split()
        times, ratio = align(script_words, asr_words, speech_len)
        if ratio < 0.5:
            # Too little agreement with the recogniser: spread words evenly over the speech
            weights = [max(len(norm(w)), 1) for w in script_words]
            total = float(sum(weights))
            acc = 0.0
            times = []
            for weight in weights:
                span = speech_len * weight / total
                times.append((acc, acc + span))
                acc += span

        duration = scene_lead + speech_len + scene_tail
        words = [
            {"w": w, "s": round(cursor + scene_lead + s, 3), "e": round(cursor + scene_lead + e, 3)}
            for w, (s, e) in zip(script_words, times)
        ]
        timeline["scenes"].append({
            "id": scene["id"],
            "text": scene["text"],
            "start": round(cursor, 3),
            "end": round(cursor + duration, 3),
            "speech_start": round(cursor + scene_lead, 3),
            "speech_end": round(cursor + scene_lead + speech_len, 3),
            "match_ratio": round(ratio, 2),
            "words": words,
        })
        print("scene %-9s speech %.2fs total %.2fs words %d match %.2f (%.1fs to make)" % (
            scene["id"], speech_len, duration, len(script_words), ratio, time.time() - t0), flush=True)
        cursor += duration

    voice = np.concatenate(pieces)
    peak = float(np.max(np.abs(voice))) or 1.0
    voice = voice * (0.9 / peak)
    sf.write(os.path.join(out_dir, "voice.wav"), voice, SR, subtype="PCM_16")
    timeline["duration"] = round(cursor, 3)
    with open(os.path.join(out_dir, "timeline.json"), "w", encoding="utf-8") as handle:
        json.dump(timeline, handle, indent=1)
    os.remove(os.path.join(out_dir, "_scene.wav"))
    print("TOTAL_DURATION", round(cursor, 2), flush=True)


if __name__ == "__main__":
    main()
