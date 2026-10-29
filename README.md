# video-factory

Finished vertical videos (1080x1920, 30 fps, H.264 + AAC) made from code. Nothing here needs a paid tool.

## How one video is made (example: `videos/free-plans`)

1. **Script** - `videos/<id>/script.json` (scenes with `text` for captions and `say` for the voice) and `videos/ACTIVE`.
   Pushing them runs the `voice` workflow (Kokoro text to speech + faster-whisper word timing) and publishes
   `voice.wav` and `timeline.json` as a GitHub release.
2. **Hero shot (optional)** - `jobs/<name>/scene.py` is a Blender scene; `jobs/ACTIVE` says how many frames and shards.
   Pushing runs the `render` workflow (Cycles on parallel runners) and publishes `eye.mp4` / `eye_hq.mp4`.
   Keep this for short hero shots only.
3. **Motion graphics** - `videos/<id>/index.html` exposes `window.renderFrame(t)`; it reads `timeline.json`, so every
   caption and card is tied to the spoken words. `node tools/render_html.js --html ... --fonts videos/fonts --timeline timeline.json --out frames`
   writes transparent PNG frames where the page sits over Blender footage and JPEG frames elsewhere.
4. **Sound** - `node tools/dump_cues.js ...` lists when things appear; `python3 tools/make_audio.py --voice voice.wav --cues cues.json --duration <s> --out audio`
   synthesises a quiet music bed and small effects, ducks them under the voice and normalises to -14 LUFS.
5. **Compose** - `python3 tools/compose.py --frames frames --eye eye_hq.mp4 --timeline timeline.json --audio audio/mix.wav --out video.mp4`
   composites and encodes in one pass.

Facts used on screen are written down with their official sources in `videos/<id>/facts.md`.
Fonts: Inter and JetBrains Mono (SIL Open Font License, see `videos/fonts`).
