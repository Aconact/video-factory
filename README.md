# video-factory

Finished vertical videos (1080x1920, 30 fps, H.264 + AAC) made from code. Nothing here needs a paid tool.

## How one video is made (example: `videos/free-plans`)

1. **Script** - `videos/<id>/script.json` (scenes with `text` for captions and `say` for the voice) and `videos/ACTIVE`.
   Pushing them runs the `voice` workflow (Kokoro text to speech + faster-whisper word timing) and publishes
   `voice.wav` and `timeline.json` as a GitHub release.
2. **3D world (Blender)** - `jobs/world/scene.py` is one continuous Blender scene posed from the video time and the
   spoken-word cues in `timeline.json` (no keyframes). `jobs/ACTIVE` sets resolution %, samples, frame range and shards
   (at most 20). Pushing runs the `render` workflow (Cycles on parallel runners, denoised), which publishes
   `world.mp4` / `world_hq.mp4` as a release. The free-plans video: 1540 frames at 100 % and 6 samples, about 4.5
   compute-hours and 30 minutes on the clock. `python3 tools/fake_bpy.py jobs/world/scene.py --layout --frames 181,901`
   checks the script and the on-screen layout without Blender. A short hero shot (`eye.mp4`) is made the same way.
3. **Motion graphics** - `videos/<id>/index.html` exposes `window.renderFrame(t)`; it reads `timeline.json`, so every
   caption and card is tied to the spoken words. `node tools/render_html.js --html ... --fonts videos/fonts --timeline timeline.json --out frames`
   writes transparent PNG frames where the page sits over Blender footage and JPEG frames elsewhere.
   With `--overlay 1` only the text layer is drawn (captions, HUD, call to action) and every frame is transparent.
4. **Sound** - `node tools/dump_cues.js ...` lists when things appear; `python3 tools/make_audio.py --voice voice.wav --cues cues.json --duration <s> --out audio`
   synthesises a quiet music bed and small effects, ducks them under the voice and normalises to -14 LUFS.
5. **Compose** - `python3 tools/compose_world.py --overlay overlay --world world_hq.mp4 --world-start 3.0 --eye eye_hq.mp4 --timeline timeline.json --audio audio/mix.wav --out video.mp4 --preset slow --crf 20`
   puts the eye shot, the 3D world and the text layer together and encodes in one pass (about 22 MB for 57 s).
   `tools/compose.py` does the same for videos whose background is plain HTML frames.

Facts used on screen are written down with their official sources in `videos/<id>/facts.md`.
Fonts: Inter and JetBrains Mono (SIL Open Font License, see `videos/fonts`).
