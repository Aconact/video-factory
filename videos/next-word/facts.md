# How AI predicts the next word - every number on screen comes from one real model run

Run: GitHub Actions (ubuntu-latest, CPU), workflow `model-data`, release `data-1`, 5 Nov 2026. Code: `tools/model_data.py`.
Trimmed copy used by the video: `videos/next-word/data.json`.

## Model
- Qwen2.5-0.5B (base model, Alibaba Qwen team), licence Apache-2.0, Hugging Face revision 060db6499f32faf8b98477b0a26969ef7d8b9987.
- 494,032,768 parameters, 24 layers, 896 numbers per token, 14 attention heads per layer (336 heads in all).
- Tokenizer: 151,665 tokens; the output layer scores 151,936 entries.
- torch 2.15.0 (CPU), transformers 5.22.1, float32.

## Prompt: "My favorite color is" (4 tokens)
- Tokens and IDs: My 5050, favorite 6930, color 1894, is 374 (the three last tokens include the leading space).
- Next-token probabilities (softmax of the model's scores): blue 19.65 %, red 9.87 %, green 6.90 %, purple 6.13 %, pink 4.42 %, yellow 4.08 %.
- The 5 most likely tokens hold 47.0 % of the probability, the top 10 hold 63.8 %; 64 tokens are above 0.1 %.
- Entropy 5.70 bits.
- Greedy continuation (always the most likely token): "My favorite color is blue. I like to wear it when I go".
  Step probabilities: blue 19.7 %, "." 55.1 %, I 18.1 %, like 16.6 %, to 38.2 %, wear 37.1 %, it 69.1 %, when 20.7 %, I 84.1 %, go 21.7 %.
- Other runs (sampling, temperature 0.8, top-p 0.95): seed 2 gives "red", seed 4 gives "white" (1.6 %, rank 14).

## Attention (the last token " is" looking back; real weights)
- Layer 2, head 4: 90 % on " favorite". Layer 9, head 7: 94 % on " color". Layer 19, head 11: 92 % on " color".
- Averaged over all heads, most layers put most of their weight on the first token ("My"), which is normal for this kind of model.
- The video shows three hand-picked heads (of 336) and says so.

## What is simplified
- "Tokens" are word pieces, not always whole words. A real chatbot also adds instructions and chat history before the model reads anything.
- ChatGPT's model is much larger and tuned to follow instructions, but it generates text the same way: one token at a time.
- The picture of 896 numbers per token is the real first-layer vector; the layer-by-layer picture is the real state of the last token after each layer (each row scaled to its own range).
