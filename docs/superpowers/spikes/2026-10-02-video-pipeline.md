# Spike: video pipeline for rung `video`

Verdict: pass

- **Question** (spec §8.1): can a scripted pipeline on this Mac turn a script (narration text plus a
  scene list) into a narrated mp4 reliably enough to be a skill?
- **Run:** 2026-10-02, 16:25:33–16:45 local, about 20 minutes of the ~2 h timebox. Every step finished
  inside its budget (step 1: 3 min of 25; step 2: 5 of 30; step 3: 8 of 45; step 4: within 15).
  Nothing is inconclusive.
- **Machine:** Apple M5 Pro, 18 cores, 48 GB RAM, Darwin 25.6.0.
- **Outputs:**
  - `out/video.mp4`: Kokoro narration, 41.344 s. This is the deliverable.
  - `out/video-say.mp4`: `say` narration, 38.848 s, for in-context comparison.
  - The throwaway code is in `spike-video/` (gitignored).
- **Open for the user:** voice quality. I could not listen. Compare the six WAVs in §3 and pick the
  default narrator.

## 1. Fold-in criteria (spec §8.3)

| Criterion | Verdict | Measurement |
|---|---|---|
| One command from script to playable mp4; narration aligned to scenes; no manual step | pass | Clean run of `spike-video/make.sh`: I deleted all WAVs, `durations.json`, `build/`, `public/audio/` and `out/video.mp4`, keeping only `script.json`, the code and the models. One run then took **30.21 s** wall: it synthesized the six WAVs, built the timeline, rendered, and verified its own output. Verification found one h264 and one AAC stream, 41.344 s against 41.333 s expected. Speech in the rendered track sits inside every scene window: it starts 0.54–0.60 s after the scene starts (lead is 0.50 s; the rest is Kokoro's own leading silence) and ends 1.50–1.56 s before the scene ends. |
| Render ≤ 2 min per video-minute | pass | Final render took **12.36 s** for 41.344 s of video, so **0.30 render-minutes per video-minute** against a limit of 2.0. All four renders of the composition (`Explain`) took 11.64–12.39 s. |
| Kokoro under a uv-managed Python 3.12/3.13 in its own venv | pass | Command: `uv run --python 3.12 --with kokoro-onnx --with soundfile python3 narrate.py`. It ran in an ephemeral uv venv (`~/.cache/uv/builds-v0/.tmp*/bin/python3`) on Python 3.12.14 (the Homebrew interpreter). Resolved packages: kokoro-onnx 0.6.1, onnxruntime 1.30.0, soundfile 0.14.0, numpy 2.5.3, espeakng-loader 0.2.4 (16 packages). It worked on the first run, with no system espeak. |
| Scene code renders within two iterations | pass (2 iterations) | Iteration 1 rendered with correct motion and correct sync, but had one visual defect: edge labels collided with edges and arrowheads. Iteration 2 fixed it. The scene code was not edited again. See the iteration log in §2. |
| License | pass | The user's situation is **individual**. From `/Users/valukin/karpathy/spike-video/node_modules/remotion/LICENSE.md` (Remotion 4.0.532), lines 18–23: "You are eligible to use Remotion for free if you are: - an individual - a for-profit organization with up to 3 employees - a non-profit or not-for-profit organization - evaluating whether Remotion is a good fit, and are not yet using it in a commercial way". Line 27: "Permission is hereby granted, free of charge, to any person eligible for the "Free License", to use the software non-commercially or commercially for the purpose of creating videos and images …". Line 31 disallows selling or relicensing a derivative of Remotion itself, which is not this use. |

## 2. Measurements

| Item | Value |
|---|---|
| Node | **v25.9.0** (Homebrew default), npm 11.12.1. None of `remotion`, `@remotion/cli`, `renderer`, `bundler` or `compositor-darwin-arm64` declares `engines`. Node 25 caused no problem, so `node@22` was **not** installed. |
| Scaffold path | `npx --yes create-video@latest --yes --blank --no-tailwind remotion` ran non-interactively in 4.2 s. It only copies the template. I moved the files up into `spike-video/`, then ran `npm i --loglevel=error`: 54.5 s, 356 packages, 0 vulnerabilities. Versions: Remotion 4.0.532, React 19.2.3, TypeScript 5.9.3, Rspack bundler (template default). |
| Compositor binary | Installed: `node_modules/@remotion/compositor-darwin-arm64`, 18 MB (`remotion`, `ffmpeg`, `ffprobe`, libav* dylibs). |
| `du -sh node_modules` | **503M**, of which 193M is Chrome Headless Shell in `node_modules/.remotion/`, fetched by the first render |
| `du -sh models` | **348M**. `kokoro-v1.0.onnx` is 325,505,369 B (sha256 `beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a`). `voices-v1.0.bin` is 28,214,398 B (sha256 `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d`). Both came via `curl -L` from the `model-files-v1.1` release tag that the kokoro-onnx README links, in about 1 min. |
| uv downloads, first narration run | 16 packages; the largest are onnxruntime 20.5 MiB, espeakng-loader 9.4 MiB, numpy 5.2 MiB and soundfile 1.1 MiB |
| First render (default `MyComp`, 60 empty frames) | **26.66 s**, about 25 s of which was the one-time Chrome Headless Shell download. A warm re-render took 1.78 s. |
| First `Explain` render (iteration 1) | 12.39 s |
| Final render (clean run) | **12.36 s**; Remotion's default concurrency here is 8x |
| Full `make.sh` | 30.21 s from clean, including synthesis of 6 WAVs; 15.1 s when it reuses the WAVs |
| Video length | `out/video.mp4`: **41.344 s**. Video is h264 1280x720 at 30 fps, 1240 frames = 41.333 s; audio is AAC 48 kHz stereo, 41.344 s; 2,775,040 B. `afinfo` also reads it. `out/video-say.mp4`: 38.848 s (1165 frames), 2,674,336 B. |
| Code size | 682 lines: `src/` plus `narrate.py`, `build-timeline.mjs`, `verify_sync.py` and `make.sh` |

**Iteration log (scene code)**

| # | Start | What it fixed or found |
|---|---|---|
| pre | 16:36 | `npx tsc --noEmit` returned exit 0 on the first write, so there were no pre-render fixes. |
| 1 | 16:36:29 | First render succeeded (12.39 s). I reviewed 12 stills. The ladder highlight climbs sheet → page → video on its cues, with a token flying along each arrow. Bullets appear one per sentence. The route example walks design spec → glance? → search? → page. **Defect:** edge labels collided with edges. The `no` labels on downward edges were offset to the left but anchored `start`, so they were drawn across the line. Lit arrowheads were 42 px because SVG markers scale with strokeWidth 6, and they touched `climb`. Sync measured correct, so no sync fix was needed. |
| 2 | 16:39:23 | In `src/scenes/DiagramWalk.tsx` I gave the markers a fixed 18x18 size (`markerUnits="userSpaceOnUse"`) and set each label's `textAnchor` to `start` or `end` by its side of the line. I re-checked the four frames that showed the defect: clean. Done. |
| — | 16:40:17 | Clean reproducibility run with no code change. This is not an iteration. |
| — | 16:41:00 | `./make.sh say` variant with no code change. This is not an iteration. |

- **Glue fix, not an iteration:** the iteration-1 `make.sh` run also stopped in its own verification glue
  after the render had succeeded (§4, item 2). That fix was in the script, not the scene code.
- **Residual cosmetic detail, not fixed:** while the token flies down the `glance? → search?` edge
  (under 0.7 s), its glow brushes the `no` label. The label stays readable. A third iteration was not
  spent on it; the fix would be a larger label offset.
- **Review stills** from the final video: `spike-video/review/final-sheet-1.png` and `final-sheet-2.png`.

**Sync detail.** Cues are mapped to frames by character offset. Cues that begin a sentence land within
about 0.3 s of the real sentence start, measured from pauses in the rendered audio:

- `rules`: cues at 4.57 s and 8.40 s; speech resumes at 4.30 s and 8.48 s.
- `route`: cues at 2.70 s and 6.10 s; speech resumes at 2.84 s and 6.30 s.

## 3. Narration

The narration texts are in `spike-video/script.json` (the `narration` field of each scene).

- **Kokoro:** voice `af_heart`, speed 1.0, `lang="en-us"`, 24 kHz mono 16-bit PCM.
- **`say`:** the system default voice (no `-v`), 22.05 kHz mono 16-bit PCM.

Durations come from `afinfo` and are stored in `spike-video/durations.json`.

| Scene | `say` WAV | s | Kokoro WAV | s |
|---|---|---|---|---|
| ladder | `/Users/valukin/karpathy/spike-video/audio/ladder.say.wav` | 11.617 | `/Users/valukin/karpathy/spike-video/audio/ladder.kokoro.wav` | 13.198 |
| rules | `/Users/valukin/karpathy/spike-video/audio/rules.say.wav` | 11.933 | `/Users/valukin/karpathy/spike-video/audio/rules.kokoro.wav` | 12.403 |
| route | `/Users/valukin/karpathy/spike-video/audio/route.say.wav` | 10.139 | `/Users/valukin/karpathy/spike-video/audio/route.kokoro.wav` | 10.575 |

To compare the voices in context, play `out/video.mp4` (Kokoro) against `out/video-say.mp4` (`say`).

Kokoro install and run had no issues. The first synthesis took 10.54 s including model load; later
clips took 1.6–1.9 s each. One observation: Kokoro's output length is not bit-exact across runs.
`ladder.kokoro.wav` was 13.188 s on the first synthesis and 13.198 s on the clean re-run. This is
harmless because `narrate.py` re-reads every duration from the file after synthesis.

## 4. What broke and how it was fixed

1. **Bundled ffprobe fails when run directly:**
   `dyld[36231]: Library not loaded: libavdevice.dylib … Reason: tried: 'libavdevice.dylib' (no such file)`.
   Fix: call it as `npx remotion ffprobe` or `npx remotion ffmpeg`, which set the library path.
2. **`make.sh` verification glue** failed on the iteration-1 run, after a successful render:
   `make.sh: expected one audio and one video stream, got: 'audio video, '`. The cause is that
   `ffprobe -of csv=p=0` prints `video,` for the h264 stream. Fix: use `-of default=nw=1:nk=1`.
3. **Remotion's FFmpeg is a reduced build:** it has 50 filters and no `select`, `tile` or `fps`. The
   error was `[AVFilterGraph] No option name near 'eq(n,60)+…'` followed by `Error parsing filterchain`.
   Fix for frame review: extract one PNG per timestamp with `-ss <t> -frames:v 1`, then tile them with
   Pillow in a throwaway `uv run --with pillow` env.
4. **The iteration-1 visual defect** (edge labels against edges and arrowheads) was fixed in
   iteration 2; see §2.
5. **Not a break, but worth pinning:** `Audio` from `remotion` is marked `@deprecated This component has
   been renamed to Html5Audio`. The spike uses `Html5Audio`.
6. **Not a break:** `create-video --yes` only copies the template, so installing is a separate `npm i`.

Nothing was installed globally. npx and uv used their normal caches (`~/.npm/_npx`, `~/.cache/uv`).

## 5. Recommendation

**Fold in.** Every §8.3 criterion passed in one session, with wide margins:

- One command goes from `script.json` to a self-verified mp4 in 30 s from clean.
- Rendering runs at 0.30 of real time against a limit of 2.0.
- Kokoro works under uv Python 3.12 with no install friction.
- The scene code was done in two iterations.
- The Free License covers an individual.

What remains is the user's call on voice: listen to the six WAVs in §3 and choose the default
narrator. If neither voice is acceptable, that, not the pipeline, would be the reason to stop. The
final wave may start from `spike-video/` (spec §8.4: `skills/explain/video/`, `scripts/narrate.sh`,
`scripts/render.sh`, gitignored `~/karpathy/video-workspace/`). It should be rewritten to the plan
rather than copied. The pieces worth reusing are:

- `script.json` and its schema
- `narrate.py`
- `build-timeline.mjs`
- `verify_sync.py`
- `src/scenes/*.tsx`
- `make.sh`

What `rungs/video.md` must pin down:

1. **Exact versions.** `remotion`, `@remotion/cli` and every `@remotion/*` package at one exact version
   (the spike used 4.0.532), plus React 19.2.3. Also the Node policy: the spike ran unmodified on Node
   25.9.0.
2. **Kokoro assets:**
   - the two release URLs (`…/releases/download/model-files-v1.1/kokoro-v1.0.onnx` and
     `…/voices-v1.0.bin`);
   - the sha256 checksums in §2;
   - the location (`video-workspace/models/`) and size (~353 MB).
3. **Narrator default and fallback:** Kokoro `af_heart` (or the user's pick) versus `say`. Both produce
   16-bit PCM WAV: Kokoro at 24 kHz, `say` at 22.05 kHz.
4. **The script schema and the cue rule.**
   - Schema: `[{ id, component, props, narration, audio: { say, kokoro } }]`.
   - Cue rule: a `cue` is a substring of the narration. Its frame is the lead plus (character
     offset ÷ narration length) × clip seconds.
   - A missing cue is a hard failure.
   - Measured accuracy is about 0.3 s. If tighter sync is ever needed, per-sentence synthesis would
     give exact offsets.
5. **Timing constants:** 30 fps, 1280x720, lead 0.5 s, tail 1.2 s. Durations are always re-read from
   the WAV with `afinfo`, because Kokoro's length varies from run to run.
6. **The component set.**
   - Proven: only `diagram-with-highlight-walk` and `bullets-appear` exist.
   - Unbuilt and untested against the two-iteration rule: `title`, `code-with-line-highlights` and
     `before-after`.
   - Diagram layout rules:
     - 280x92 node boxes placed in a 1280x720 coordinate space;
     - arrow markers sized in user space;
     - labels anchored by their side of the line, offset enough to clear the token;
     - no automatic text fitting, so long labels will overflow.
7. **Assets.** Audio must be copied into Remotion's `public/` before rendering, because `staticFile`
   serves only `public/`. Use `Html5Audio`, not the deprecated `Audio`.
8. **Checks the skill runs after every render:**
   - streams and duration via `npx remotion ffprobe`;
   - speech placement, the `verify_sync.py` equivalent, which needs numpy and soundfile from the
     Kokoro venv;
   - visual review from per-timestamp stills, because the bundled FFmpeg lacks `select` and `tile`.
9. **First-run costs to tell the user about:**
   - `npm i`: ~55 s;
   - Chrome Headless Shell on the first render: ~193 MB, ~25 s;
   - uv resolve: ~30 s;
   - model download: ~1 min.
10. **When to re-check the license:** the Free License holds for an individual. It must be revisited if
    the use moves to a for-profit organization with more than 3 employees.
