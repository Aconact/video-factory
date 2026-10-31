"""Reads jobs/ACTIVE and prints the render plan as key=value lines for $GITHUB_OUTPUT.

jobs/ACTIVE format (one key=value per line, '#' starts a comment):
  job      folder name under jobs/ that holds scene.py
  pct      resolution percentage of 1080x1920
  samples  Cycles samples per pixel
  fstart   first frame of the whole shot
  fend     last frame of the whole shot
  frames   optional preview list such as 1,45,90 or 1-10 (default: fstart..fend)
  shards   how many parallel jobs share the frames (default 1)
"""
import json

cfg = {}
with open("jobs/ACTIVE", encoding="utf-8") as handle:
    for line in handle:
        line = line.split("#", 1)[0].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        cfg[key.strip()] = value.strip()

job = cfg["job"]
pct = int(cfg.get("pct", "100"))
samples = int(cfg.get("samples", "48"))
fstart = int(cfg.get("fstart", "1"))
fend = int(cfg.get("fend", str(fstart)))
shards = max(1, int(cfg.get("shards", "1")))
preview = cfg.get("frames", "").strip()

frame_list = []
if preview:
    for token in preview.split(","):
        token = token.strip()
        if "-" in token:
            first, last = token.split("-", 1)
            frame_list.extend(range(int(first), int(last) + 1))
        elif token:
            frame_list.append(int(token))
else:
    frame_list = list(range(fstart, fend + 1))

shards = min(shards, len(frame_list))
base, extra = divmod(len(frame_list), shards)
include = []
index = 0
for shard in range(shards):
    # every shard takes every N-th frame, so each one gets the same mix of cheap and expensive frames
    chunk = frame_list[shard::shards]
    include.append({"shard": shard, "frames": ",".join(str(f) for f in chunk)})

print("job=%s" % job)
print("pct=%d" % pct)
print("samples=%d" % samples)
print("fstart=%d" % fstart)
print("fend=%d" % fend)
print("encode=%s" % ("true" if (not preview and fend > fstart) else "false"))
print("matrix=%s" % json.dumps({"include": include}, separators=(",", ":")))
