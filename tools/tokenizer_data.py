#!/usr/bin/env python3
"""Splits a few words into tokens with the real Qwen2.5-0.5B tokenizer (no model needed).

    python tools/tokenizer_data.py out    ->  out/tokens.json
"""
import json
import os
import sys

from transformers import AutoTokenizer

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
os.makedirs(OUT, exist_ok=True)
tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B")
WORDS = ["strawberry", "unbelievably", "TechPulse", "ChatGPT", "Algeria", "tokenization", "favorite", " favorite",
         "My favorite color is", "Hello world", "artificial intelligence"]
data = {"vocab": len(tok), "words": {}}
for w in WORDS:
    ids = tok(w)["input_ids"]
    data["words"][w] = [{"id": int(i), "text": tok.decode([int(i)])} for i in ids]
    print(repr(w), "->", " | ".join("%r:%d" % (t["text"], t["id"]) for t in data["words"][w]), flush=True)
json.dump(data, open(os.path.join(OUT, "tokens.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
