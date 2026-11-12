#!/usr/bin/env python3
"""Plan for the phones video render: reads videos/phones/render.json (inputs of a manual run override it),
splits the frame range into shards and writes the outputs the workflow needs."""
import json
import math
import os

cfg = json.load(open("videos/phones/render.json"))
for key in ("from", "to", "shards", "release", "crf", "maxrate", "audio"):
    v = os.environ.get("IN_" + key.upper(), "").strip()
    if v:
        cfg[key] = v if key in ("release", "maxrate") else int(v)

timeline = json.load(open("videos/phones/timeline.json"))
total = math.ceil(timeline["duration"] * 30)          # frames at 30 fps
first = max(0, int(cfg.get("from", 0)))
last = int(cfg.get("to", -1))
last = total - 1 if last < 0 else min(last, total - 1)
n = last - first + 1
shards = max(1, min(int(cfg.get("shards", 20)), n))
per = math.ceil(n / shards)
include = []
for i in range(shards):
    a = first + i * per
    b = min(last, a + per - 1)
    if a > last:
        break
    include.append({"shard": i, "from": a, "to": b})
full = first == 0 and last == total - 1
out = {
    "matrix": json.dumps({"include": include}),
    "count": len(include), "total": total, "first": first, "last": last, "full": str(full).lower(),
    "release": cfg.get("release", "draft"), "crf": cfg.get("crf", 17), "maxrate": cfg.get("maxrate", "20M"),
    "media": cfg["media_release"], "audio": str(bool(cfg.get("audio", 1))).lower(),
    "astart": "%.6f" % (first / 30.0),
}
for k, v in out.items():
    print(f"{k}={v}")
