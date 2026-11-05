#!/usr/bin/env python3
"""Runs small open language models on a few prompts and records everything the explainer video shows as real numbers:
tokens and token ids, the numbers a token turns into, how the last token's numbers change layer by layer, which earlier
words the last token looks at (attention), the model's score for every word in its vocabulary, and a few real generation
steps (greedy and sampled).

    python tools/model_data.py out        ->  out/data.json  out/summary.txt

Runs on a GitHub runner (CPU): see .github/workflows/model-data.yml.
"""
import json
import os
import random
import re
import sys
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
os.makedirs(OUT, exist_ok=True)
torch.set_grad_enabled(False)
torch.set_num_threads(max(1, os.cpu_count() or 2))

MODELS = [
    {"name": "Qwen/Qwen2.5-0.5B", "license": "Apache-2.0"},
    {"name": "gpt2", "license": "MIT"},
]
PROMPTS = [
    "The capital of France is",
    "The cat sat on the",
    "Once upon a",
    "The quick brown fox jumps over the lazy",
    "I'm so hungry I could eat a",
    "Artificial intelligence will",
    "The best way to learn something new is to",
    "My favorite color is",
    "Thank you very",
    "The opposite of hot is",
    "To make a cup of tea, first boil some",
    "Roses are red, violets are",
    "The largest planet in our solar system is",
    "The Eiffel Tower is located in",
]
TOPK = 10
GEN_STEPS = 10
SEEDS = [1, 2, 3, 4, 5, 6]
TEMPERATURE = 0.8
TOP_P = 0.95

LINES = []


def log(*parts):
    text = " ".join(str(p) for p in parts)
    print(text, flush=True)
    LINES.append(text)


def sig(x, n=6):
    return float(("%." + str(n) + "g") % x)


def rnd(values, n):
    return [round(float(v), n) for v in values]


def top_list(tok, probs, logits, k):
    p, idx = torch.topk(probs, k)
    return [{"id": int(i), "text": tok.decode([int(i)]), "p": sig(pp), "logit": round(float(logits[int(i)]), 3)}
            for pp, i in zip(p.tolist(), idx.tolist())]


def entropy_bits(probs):
    return float(-(probs * torch.log2(probs.clamp_min(1e-30))).sum())


def next_dist(model, ids):
    out = model(input_ids=ids)
    logits = out.logits[0, -1].float()
    return logits, torch.softmax(logits, dim=-1)


def generate(model, tok, prompt, steps, seed=None):
    """seed None -> greedy (always the most likely token); otherwise nucleus sampling at TEMPERATURE / TOP_P.
    The probabilities that are recorded are always the model's own (temperature 1) probabilities."""
    ids = tok(prompt, return_tensors="pt")["input_ids"]
    gen = torch.Generator().manual_seed(seed) if seed is not None else None
    rows = []
    for _ in range(steps):
        logits, probs = next_dist(model, ids)
        if seed is None:
            nxt = int(torch.argmax(probs))
        else:
            scaled = torch.softmax(logits / TEMPERATURE, dim=-1)
            sp, si = torch.sort(scaled, descending=True)
            keep = (torch.cumsum(sp, 0) - sp) < TOP_P
            sp = sp * keep
            sp = sp / sp.sum()
            nxt = int(si[int(torch.multinomial(sp, 1, generator=gen))])
        rows.append({
            "top5": top_list(tok, probs, logits, 5),
            "chosen": {"id": nxt, "text": tok.decode([nxt]), "p": sig(float(probs[nxt])),
                       "rank": 1 + int((probs > probs[nxt]).sum())},
            "entropy_bits": round(entropy_bits(probs), 3),
        })
        ids = torch.cat([ids, torch.tensor([[nxt]])], dim=1)
    return {"seed": seed, "text": tok.decode(ids[0]), "steps": rows}


def tail_words(tok, probs, count=16, seed=5):
    """A few ordinary English words picked at random from the vocabulary, with the score the model gave them."""
    pieces = tok.convert_ids_to_tokens(list(range(len(tok))))
    cands = [i for i, p in enumerate(pieces) if p and re.fullmatch("Ġ[a-z]{4,9}", p)]
    picked = random.Random(seed).sample(cands, count)
    return [{"id": i, "text": tok.decode([i]), "p": sig(float(probs[i])), "rank": 1 + int((probs > probs[i]).sum())}
            for i in picked]


def analyse(model, tok, prompt):
    ids = tok(prompt, return_tensors="pt")["input_ids"]
    n = ids.shape[1]
    attentions = None
    try:
        out = model(input_ids=ids, output_hidden_states=True, output_attentions=True)
        attentions = out.attentions
    except Exception as exc:  # noqa: BLE001
        log("  attentions unavailable:", exc)
        out = model(input_ids=ids, output_hidden_states=True)
    logits = out.logits[0, -1].float()
    probs = torch.softmax(logits, dim=-1)
    hs = out.hidden_states
    pieces = tok.convert_ids_to_tokens(ids[0].tolist())
    sorted_p = torch.sort(probs, descending=True).values
    mass = {str(k): sig(float(sorted_p[:k].sum())) for k in (1, 3, 5, 10, 50, 100, 1000)}
    row = {
        "prompt": prompt,
        "tokens": [{"id": int(i), "text": tok.decode([int(i)]), "piece": pc} for i, pc in zip(ids[0].tolist(), pieces)],
        "embedding": [rnd(r, 4) for r in hs[0][0].tolist()],                 # what enters layer 1: n x hidden
        "layers_last": [rnd(h[0, -1].tolist(), 3) for h in hs],              # last token after every layer
        "layer_norms": rnd([float(h[0, -1].norm()) for h in hs], 2),
        "next": {
            "top": top_list(tok, probs, logits, TOPK),
            "entropy_bits": round(entropy_bits(probs), 3),
            "mass": mass,
            "rank_curve": [sig(float(v)) for v in sorted_p[:400]],
            "above_1e-3": int((probs > 1e-3).sum()),
            "tail": tail_words(tok, probs),
        },
        "greedy": generate(model, tok, prompt, GEN_STEPS, None),
        "samples": [generate(model, tok, prompt, GEN_STEPS, s) for s in SEEDS],
    }
    if attentions is not None:
        # attention of the last token: [layer][head][position]
        row["attn_last"] = [[rnd(head, 4) for head in layer[0, :, -1, :].tolist()] for layer in attentions]
    return row


def main():
    started = time.time()
    data = {"generated_unix": int(started),
            "env": {"torch": torch.__version__, "python": sys.version.split()[0]},
            "settings": {"temperature": TEMPERATURE, "top_p": TOP_P, "seeds": SEEDS, "gen_steps": GEN_STEPS},
            "models": {}}
    try:
        import transformers
        data["env"]["transformers"] = transformers.__version__
    except Exception:  # noqa: BLE001
        pass
    for spec in MODELS:
        name = spec["name"]
        log("=" * 78)
        log("MODEL", name, spec["license"])
        t0 = time.time()
        tok = AutoTokenizer.from_pretrained(name)
        try:
            model = AutoModelForCausalLM.from_pretrained(name, attn_implementation="eager")
        except Exception as exc:  # noqa: BLE001
            log("eager attention not accepted:", exc)
            model = AutoModelForCausalLM.from_pretrained(name)
        model = model.float().eval()
        cfg = model.config
        facts = {
            "license": spec["license"],
            "params": int(sum(p.numel() for p in model.parameters())),
            "layers": int(cfg.num_hidden_layers),
            "hidden": int(cfg.hidden_size),
            "heads": int(cfg.num_attention_heads),
            "vocab_logits": int(cfg.vocab_size),
            "vocab_tokenizer": int(len(tok)),
        }
        try:
            from huggingface_hub import HfApi
            facts["revision"] = HfApi().model_info(name).sha
        except Exception as exc:  # noqa: BLE001
            facts["revision"] = "unknown (%s)" % exc
        log("loaded in %.1fs" % (time.time() - t0), json.dumps(facts))
        entry = {"facts": facts, "prompts": {}}
        for prompt in PROMPTS:
            t1 = time.time()
            row = analyse(model, tok, prompt)
            entry["prompts"][prompt] = row
            log("-" * 78)
            log("PROMPT %r  (%d tokens, %.1fs)" % (prompt, len(row["tokens"]), time.time() - t1))
            log("  tokens:", " ".join("[%s]%d" % (t["text"], t["id"]) for t in row["tokens"]))
            for t in row["next"]["top"][:6]:
                log("   %6.2f%%  %r" % (t["p"] * 100, t["text"]))
            log("  top-5 mass %.1f%%  entropy %.2f bits" % (row["next"]["mass"]["5"] * 100, row["next"]["entropy_bits"]))
            log("  greedy :", repr(row["greedy"]["text"]))
            for s in row["samples"]:
                log("  seed %d :" % s["seed"], repr(s["text"]))
        data["models"][name] = entry
        del model
    data["seconds"] = round(time.time() - started, 1)
    with open(os.path.join(OUT, "data.json"), "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(OUT, "summary.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(LINES) + "\n")
    log("done in %.0fs, data.json %d KB" % (data["seconds"], os.path.getsize(os.path.join(OUT, "data.json")) // 1024))


if __name__ == "__main__":
    main()
