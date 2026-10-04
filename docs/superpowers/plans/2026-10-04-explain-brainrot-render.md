# Explain brainrot — wave `brainrot-render` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `brainrot` script renders, through the unchanged `render.sh` command, a checked 1080×1920 mp4: the scene panel on top, the background (a user clip or the generated `RunnerLoop`) below, word-by-word captions on the seam, and a transcript with Format and Background rows. The explainer keeps its nine stage lines and its pixels.

**Architecture:** `Explain` stays the only composition. It switches on `timeline.format`, and `Short` lays the existing scenes into a 1080×960 panel under a `BRAINROT_BOX`. A new Python picker chooses the background after the timeline stage and writes `background` into `timeline.json`. `render.sh` gains the format → speed mapping, budgets read from the timeline, and a tenth stage line. `check_render.sh` also checks the frame size. The pure parts (caption state, runner motion, geometry, box values) are plain `.ts` modules with type-only imports, so Python tests can run them through Node 25 without a TS test runner.

**Tech Stack:** Remotion 4.0.532, React 19.2.3, TypeScript 5.9.3; Node 25.9 (it runs `.ts` files natively); Python 3 stdlib `unittest`; bash; the workspace's `remotion ffprobe` and `remotion ffmpeg`.

**Spec:** `docs/superpowers/specs/2026-10-04-explain-brainrot-design.md`: §3.1, §3.2, §4.1, §4.3, §4.4, §6, §7.3 and §7.4, plus the 30/31 s and 90/91 s boundary tests of §7.1. Wave map: `docs/superpowers/waves/2026-10-04-explain-brainrot.yaml`, wave `brainrot-render`. This includes the "Inherited from the wave-1 plans" sentence and the "Carried from the wave-1 final review" list.

## Global Constraints

- **Pinned versions do not change:** Remotion `4.0.532`, React `19.2.3`, TypeScript `5.9.3`. Never install globally; never use `npx`. Node tools run from `<ws>/app/node_modules/.bin/`.
- **Workspace:** `<ws>` is `${EXPLAIN_VIDEO_WORKSPACE:-$HOME/karpathy/video-workspace}`, and the background folder is `${EXPLAIN_BRAINROT_BACKGROUNDS:-<ws>/backgrounds}`. Nothing is downloaded for backgrounds.
- **Canvas:** brainrot 1080×1920 at 30 fps. The scene panel is 1080×960 at the top and the background is 1080×960 at the bottom. The caption band is centred on y = 960.
- **Voice:** a brainrot narration runs at `--speed 1.2`; the explainer keeps the default 1.0.
- **Background values (spec §4.4):** only `*.mp4`, `*.mov` and `*.webm` count, matched case-insensitively. Hidden files are ignored and clips are muted. The fixed seed of `RunnerLoop` is `7`.
- **Explainer unchanged:**
  - nine stage lines, byte for byte;
  - the gated landscape regression passes (0 differing pixels expected; threshold 4608);
  - the explainer FAIL texts of the timeline budget check stay byte-identical;
  - the transcript page differs only by one added CSS rule (no visible change).
- **The baseline is fixed:** never re-capture the landscape baseline, and never pass `--force`.
- **Renders:** run only under `EXPLAIN_VIDEO_E2E=1`, except the Task 4 still test, which is also gated.
- **Commits:** `git -c user.name=Vladislav -c user.email=valukin@Vladislavs-MacBook-Pro.local commit`, with the message ending in `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Current-code facts that constrain the change

- **`scripts/render.sh`**
  - Stages are shell functions run in order: `stage_script`, `clear_stale`, `stage_workspace`, `stage_narration`, `stage_timeline`, `stage_render`, `stage_checks`, `stage_transcript`.
  - `stage_timeline` checks budgets against the constants `MAX_SCENE_S=60` and `MAX_TOTAL_S=150` in inline Python. Its texts are `FAIL scene %s is %.1f s (max %g)` and `FAIL total %.1f s (max %g)`.
  - `stage_render` empties `<app>/public/audio` and copies every scene's clip into it, then runs `remotion render Explain <mp4> --props <timeline>` with cwd `<app>`.
  - `stream` prints a tool's lines indented, holding back the lines that match a prefix.
- **`scripts/video-workspace.sh`** rsyncs `video/` to `<ws>/app` with `--exclude /node_modules/ --exclude /public/`. Anything under `public/` survives a sync.
- **`video/check_render.sh`**
  - `read_timeline` prints `"<fps> <totalFrames>"`, then one still per line.
  - The container check uses `remotion ffprobe` with cwd `<app>`.
  - Its ok line is `container: ok (<s> s)`.
- **`video/verify_sync.py`** has `LEAD_TOLERANCE = 0.25` and `MIN_TAIL = 0.3`. The brainrot tail is 12 frames (0.4 s), so the headroom is about 0.1 s.
- **Remotion 4.0.532**
  - The bundler forwards a symlink in `public/` into the bundle by its realpath (`@remotion/bundler/dist/copy-dir.js`), and prints one warning to the log.
  - `OffthreadVideo` takes `trimBefore` in frames (`startFrom` is deprecated) and `muted`, and has no loop prop. Looping uses `<Loop durationInFrames>`.
- **The workspace ffmpeg** has no `lavfi` and no `rawvideo` input. `image2` with PNG frames and `libx264 -pix_fmt yuv420p` works: 30 frames at 64×64 give a 2.7 KB, 1.000 s clip.
- **`remotion ffprobe -v error -show_entries stream=codec_type:format=duration -of json <file>`** prints JSON. On a non-video file it exits 1 and prints `{}`.
- **Node 25.9** imports a `.ts` file whose imports are all `import type` (checked on `scenes/diagramGeometry.ts`).
- **`sceneBox.tsx`** exports `Size`, `SceneType`, `SceneBox`, `LANDSCAPE_BOX`, `SceneBoxProvider`, `useBox()` (which throws `useBox: no SceneBoxProvider above this scene`) and `contentRect(box)` (top = margin + titleBand + 30).
  - Placement contract: a scene draws inside its nearest positioned ancestor, which must be `box.width × box.height`. `Title` is an `AbsoluteFill`.
- **`CodeHighlights.tsx`** slices `lines` with `MAX_LINES = 14`. Its row width is `(gutter + 2)ch + 16 px` for the number plus the text, and rows clip with `overflow: hidden`.
- **`BeforeAfter.tsx`** always lays its panels side by side: `column = (contentRect(box).width - 48) / 2`.
- **The timeline (wave brainrot-timeline Produces)**
  - Top-level keys: `format`, `fps`, `width`, `height`, `totalFrames`, `maxSceneSeconds`, `maxTotalSeconds`, `engine`, `scenes`.
  - A brainrot scene has `leadFrames` 6, a tail of 12, and `captions: [{from, to, words: [{text, from, to}]}]` in frames relative to the scene start.
  - Chunks tile the scene. A chunk can be zero-length (`from == to`) for a word under about 17 ms.
- **`templates/video.html`**
  - The provenance `<dl>` carries `data-ste="skip"`.
  - `video { … aspect-ratio: 16 / 9; max-width: 1280px }` and `<video controls src="video.mp4">`.
  - `transcript.py` fills `{{marker}}` values from a dict; an unknown marker raises `KeyError`.

## Interfaces

**Consumed:** the timeline above; `narrate.sh --speed <d.d>` (wave sentence-narration); the SceneBox contract.

**Produced:**

```ts
// src/types.ts (additions)
export type Format = "explainer" | "brainrot";
export type CaptionWord = { text: string; from: number; to: number };
export type CaptionChunk = { from: number; to: number; words: CaptionWord[] };
export type Background =
  | { kind: "clip"; file: string; src: string; start: number; seconds: number; loop: boolean }
  | { kind: "generated" };
// Timeline gains: format: Format; maxSceneSeconds: number; maxTotalSeconds: number; background?: Background
// SceneTiming gains: captions?: CaptionChunk[]
```

```ts
// src/sceneBox.tsx (additions)
// SceneBox keeps its fields and gains: stackPanels: boolean
export const BRAINROT_BOX: SceneBox; // values in Task 2
// LANDSCAPE_BOX gains stackPanels: false
```

```ts
// src/short/captions.ts — pure, type-only imports
export function activeCaption(captions: CaptionChunk[], frame: number): { chunk: CaptionChunk; word: number } | null;
// src/short/runner.ts — pure, type-only imports
export type RunnerState = { stripe: number; lane: 0 | 1 | 2; hop: number; obstacles: { lane: 0 | 1 | 2; z: number }[] };
export function runnerState(frame: number, seed: number): RunnerState;
```

```sh
# video/pick_background.py <timeline.json> <remotion-cli> <app-dir> --dir <clips> [--seed <int>]
#   stdout: "background: SKIP <file> (<cause>)"* then "background: ok <name> @<start> s[ (loop)]" | "background: ok generated"
#   exit 0 ok; exit 1 "background: FAIL <cause>" (cannot read/write the timeline, cannot link); exit 2 usage
# video/check_budgets.py <timeline.json>
#   stdout: "ok <n> <total %.1f> <total %.3f>" | "FAIL scene <id> is <s %.1f> s (max <%g>)" | "FAIL total <%.1f> s (max <%g>)"
#   exit 0 (verdict printed); exit 2 unreadable timeline or no budget keys
# video/transcript.py <script.json> <output-dir> [--narrator "<t>"] [--background "<t>"]
```

The timeline gets a `background` field, written by the picker:

- `{"kind": "clip", "file": "<basename>", "src": "bg/clip<.ext lowercased>", "start": <s, 3 dp>, "seconds": <clip s, 3 dp>, "loop": <bool>}`
- or `{"kind": "generated"}`

`src` is added to the spec §4.4 shape: the link name is fixed so file names with spaces never reach `staticFile`. `seconds` is added too, because `Loop` needs it.

**Stage lines (brainrot), ten, in order:**

```
script: ok (<n> scenes)
workspace: ok <ws>
narration (<engine>): ok[ (fallback: <cause>)]
timeline (<n> scenes, <s> s): ok
background: ok <name> @<start> s[ (loop)]   |   background: ok generated
render (<s> s, <ratio> render-min/video-min)[ (limit 2.0)]: ok
container: ok (<s> s)
sync: ok
stills (<n>): ok <review-dir>
transcript: ok
```

## Invariants and named failure behaviour

- **The explainer path never reads `background`, `captions` or `BRAINROT_BOX`.** `Explain` renders the landscape stack unless `format == "brainrot"`.
- **`Short` with no `background` in its timeline** (a hand-run `remotion render`) throws `Short: timeline has no background; run render.sh`.
- **The picker never fails because clips are missing.**
  - A missing folder, an empty folder, or a folder with no good clip gives `generated`.
  - A clip that cannot be probed (`ffprobe exit <n>`, `ffprobe timed out`), has no video stream (`no video stream`) or has no positive duration (`no duration`) gives one indented SKIP line, and the picker tries the next clip.
  - The picker empties `<app>/public/bg/` on every run, so no stale link survives.
- **A clip that probes fine but fails to decode** gives the existing `render: FAIL remotion render exit <n> (log <path>)`. `rungs/brainrot.md` tells the author to remove the clip, or to point `EXPLAIN_BRAINROT_BACKGROUNDS` at an empty folder.
- **The budget check** reads its limits from the timeline. A timeline without the keys exits 2, and `render.sh` prints `timeline: FAIL cannot read <timeline>`.
- **Container size mismatch:** `container: FAIL size <w>x<h>, expected <W>x<H>`.
- **Captions:** at most one chunk shows at a time. A zero-length chunk never shows. Before the first chunk or after the last there is no caption.
- **Rollback:** brainrot is reachable only through `"format": "brainrot"`. Reverting this wave's commits restores today's renderer, and wave-1 output stays valid.

## Review Focus

1. **A clip named with spaces and upper case** (`My Run 4K.MP4`): the link is `bg/clip.mp4`, and the stage line and transcript show the original name. Pinned in Task 5.
2. **A folder with `.DS_Store`, a `notes.txt`, a symlink to a clip, and a clip exactly as long as the video:** hidden and non-video files are ignored; the symlink resolves to its realpath; equal length gives start 0 and no loop. Pinned in Task 5.
3. **A brainrot run, then an explainer run in the same workspace:** the explainer render ignores `public/bg` and its pixels match the baseline. Pinned in Task 9, which runs the landscape regression after the brainrot renders.
4. **A brainrot timeline with no `background` field:** `Short` fails loudly with the named error instead of rendering an empty half. Pinned in Task 4.
5. **Zero-length caption chunks and frames between chunks:** no flicker, no crash, no caption shown. Pinned in Task 3.

---

### Task 1: Split `tests/test_narrate.py` before it grows

**Files:**
- Create: `skills/explain/tests/test_narrate_sentences.py` (classes `SentenceText`, `Sentences`, `JoinClips`, moved verbatim)
- Modify: `skills/explain/tests/test_narrate.py` (keeps the shared doubles and helpers, plus the scene-mode classes)

**Interfaces:** Consumes: nothing. Produces: no code change.

- [ ] **Step 1: Move the three classes.** The new module imports the shared helpers (`NarrateCase`, the stub writers, `NARRATE_PY`, `run_kokoro`) from `test_narrate` with the same `sys.path` pattern the other test modules use. Assertions stay unchanged.
- [ ] **Step 2: Check the counts.**
  Run: `cd skills/explain && python3 -B -m unittest tests.test_narrate tests.test_narrate_sentences 2>&1 | tail -3`
  Expected: `Ran 67 tests` and `OK`, the same count as `tests.test_narrate` alone before the move. Then run `wc -l tests/test_narrate.py tests/test_narrate_sentences.py`. Expected: each under 800.
- [ ] **Step 3: Commit:** `test: explain: split the sentence-mode narration tests into their own module`.

### Task 2: `BRAINROT_BOX`, stacked before-after, and a geometry-derived code line guard

**Files:**
- Modify: `skills/explain/video/src/sceneBox.tsx` (`stackPanels` field, `BRAINROT_BOX`)
- Modify: `skills/explain/video/src/scenes/BeforeAfter.tsx` (stacked branch)
- Modify: `skills/explain/video/src/scenes/CodeHighlights.tsx` (remove `MAX_LINES`; slice to `Math.floor(contentRect(box).height / box.type.codeLine)`)
- Create: `skills/explain/tests/test_scene_geometry.py` (always-on; runs Node on the `.ts` modules)

**Interfaces:**
- Consumes: the SceneBox contract.
- Produces: `BRAINROT_BOX` with these values:
  - `width` 1080, `height` 960, `margin` 48, `titleSize` 56, `titleBand` 76, `stackPanels` true;
  - `type`: `heroTitle` 72, `heroSubtitle` 44, `bullet` 44, `code` 34, `codeLine` 48, `node` 280×112, `nodeLabel` 32, `nodeSub` 24, `edgeLabel` 26, `panelHeading` 38, `panelLine` 32.
  - So `contentRect(BRAINROT_BOX)` = `{ left: 48, top: 154, width: 984, height: 758 }`.
  - Code fit: 3-digit gutter plus 40 columns is 45ch + 16 px. At an advance of 0.61 em that is 45 × 0.61 × 34 + 16 = 949 ≤ 984. 14 lines × 48 = 672 ≤ 758.
  - Landscape: `stackPanels` false, and the line guard gives `floor(534 / 36) = 14`, the same as today's `MAX_LINES`.
- `BeforeAfter` stacked: `before` takes the top half of the content box, `after` the bottom half, with the existing 48 px gap. Each half is `(758 − 48) / 2 = 355` px tall. The wipe and dim motion are unchanged.
  - Spec deviation, ruled here: spec §4.2 says "stack when taller than wide", but the brainrot panel content box (984×758) is wider than tall. Two side-by-side columns would be 468 px, and 30 chars at 32 px need about 528 px. So `stackPanels` is an explicit box field.

- [ ] **Step 1: Write the always-on geometry tests.** Each test shells out to `node --input-type=module -e` importing the module by absolute path and prints JSON. Each test is skipped only when `node` is missing.
  - `test_brainrot_content_rect`: `contentRect(BRAINROT_BOX)` equals `{left:48, top:154, width:984, height:758}`.
  - `test_brainrot_code_fits_forty_columns`: `45 * 0.61 * type.code + 16 <= content width`, and `14 * codeLine <= content height`.
  - `test_landscape_box_unchanged`: `LANDSCAPE_BOX` deep-equals today's values plus `stackPanels: false`.
  - `test_portrait_cell_centres`: `cellCentre('a1', {984,758})` equals `{x:164, y:126.33…}` and `cellCentre('c3', …)` equals `{x:820, y:631.66…}`. Pairs in neighbouring cells are at least `node.width + 48` apart in x.
  - `test_portrait_segment_ends_outside_nodes`: for `a1→b2`, `segment()` returns points outside both 280×112 node boxes (plus `EDGE_GAP`) and on the centre line.
  - Note: `sceneBox.tsx` imports React. If Node cannot import it, move the box values and `contentRect` into `src/box.ts` (type-only imports), and re-export them from `sceneBox.tsx` unchanged.
- [ ] **Step 2: Run them and see them fail** (no `BRAINROT_BOX`).
  Run: `cd skills/explain && python3 -B -m unittest tests.test_scene_geometry -v`
- [ ] **Step 3: Implement the box, the stacked branch and the guard.**
- [ ] **Step 4: Typecheck, then run the regression.**
  Run: `skills/explain/scripts/video-workspace.sh --engine say && (cd "${EXPLAIN_VIDEO_WORKSPACE:-$HOME/karpathy/video-workspace}/app" && ./node_modules/.bin/tsc -p .)`
  Expected: exit 0.
  Then run: `cd skills/explain && python3 -B -m unittest tests.test_scene_geometry && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_landscape_regression`
  Expected: `OK` twice. The landscape pixels are unchanged.
- [ ] **Step 5: Commit:** `feat: explain: brainrot scene box, stacked before-after, code line guard from the box`.

### Task 3: Pure caption state and runner motion

**Files:**
- Create: `skills/explain/video/src/short/captions.ts`, `skills/explain/video/src/short/runner.ts` (type-only imports)
- Modify: `skills/explain/video/src/types.ts` (the additions of the Interfaces section)
- Create: `skills/explain/tests/test_short_logic.py` (always-on; runs Node)

**Interfaces:** Produces `activeCaption` and `runnerState`, as in the Interfaces section.

- **`activeCaption` rule:**
  - The chunk is the one with `from <= frame < to`; zero-length chunks are never chosen.
  - `word` is the index of the last word with `from <= frame` (0 when frame equals the chunk start).
  - No chunk matches → `null`.
- **`runnerState` rule:**
  - A pure function of `(frame, seed)` with a mulberry32 PRNG keyed by `seed` and the beat index.
  - `BEAT = 20` frames. `lane` changes only at a beat boundary.
  - `hop` is `sin(π · (frame mod BEAT) / BEAT)` during a lane change and 0 otherwise.
  - `stripe = (frame * 24) mod 120`.
  - Obstacles: up to 3, `z` in `[0, 1)`, advancing by `1/60` per frame, spawned per beat from the PRNG.

- [ ] **Step 1: Write the failing tests.**

```python
test_caption_inside_chunk          # frame 7 in chunk [6,21) -> chunk index 0, word = last word with from <= 7
test_caption_zero_length_chunk_skipped  # chunks [[6,6],[6,15]] at frame 6 -> the second chunk
test_caption_none_before_and_after # frame 5 (before 6) and frame >= last.to -> None
test_runner_deterministic          # runnerState(f, 7) twice for f in 0..300 -> equal JSON
test_runner_lane_changes_on_beats  # lane(f) != lane(f-1) only when f % 20 == 0
test_runner_seed_matters           # some f < 600: runnerState(f, 7) != runnerState(f, 8)
test_runner_ranges                 # lane in {0,1,2}, 0 <= hop <= 1, 0 <= stripe < 120, every z in [0,1)
```

- [ ] **Step 2: Run them and see them fail.**
  Run: `cd skills/explain && python3 -B -m unittest tests.test_short_logic -v`
- [ ] **Step 3: Implement both modules and the `types.ts` additions.** `Root.tsx`'s `EMPTY` gains `format: "explainer"` and the budgets `60` and `150`.
- [ ] **Step 4: Run:** `python3 -B -m unittest tests.test_short_logic`, then the Task 2 typecheck. Expected: `OK`, and `tsc` exits 0.
- [ ] **Step 5: Commit:** `feat: explain: caption state and runner motion for the brainrot short`.

### Task 4: The `Short` layout, caption band and backgrounds

**Files:**
- Create: `skills/explain/video/src/sceneBody.tsx` (`SceneBody` and `FadeIn` moved verbatim from `Explain.tsx`)
- Create: `skills/explain/video/src/short/Short.tsx`, `CaptionBand.tsx`, `RunnerLoop.tsx`, `Background.tsx`
- Modify: `skills/explain/video/src/Explain.tsx` (`format === "brainrot"` → `<Short {...timeline} />`; the landscape path is otherwise unchanged)
- Create: `skills/explain/tests/test_short_still.py` (gated `EXPLAIN_VIDEO_E2E=1`)

**Interfaces:**
- Consumes: `BRAINROT_BOX` (Task 2), `activeCaption` and `runnerState` (Task 3), the timeline.
- Produces the `Short(timeline: Timeline)` structure:
  1. An `AbsoluteFill` with a black background.
  2. Bottom: a positioned `div` at `left 0, top 960, 1080×960, overflow hidden`, holding `<Background>`. It sits outside the `Series`, so it runs without a break across scenes.
  3. A `Series` with one `Series.Sequence` per scene, holding:
     - the panel `div` at `left 0, top 0, 1080×960, overflow hidden`, white, containing `<SceneBoxProvider box={BRAINROT_BOX}><FadeIn><SceneBody/></FadeIn></SceneBoxProvider>`;
     - `<CaptionBand captions={scene.captions ?? []} />`;
     - the narration `Sequence` exactly as in the landscape path.
- **`CaptionBand`:**
  - A box centred at x 540 and y 960, `max-width` 1000.
  - Sans bold 76 px, white fill, black stroke 8 px (`WebkitTextStroke` with `paintOrder: "stroke fill"`), active word `#ffd400`.
  - It renders nothing when `activeCaption` is `null`.
- **`Background`:**
  - `clip` → `<OffthreadVideo src={staticFile(bg.src)} muted trimBefore={Math.round(bg.start * fps)} style={{width:1080, height:960, objectFit:"cover"}} />`. When `loop` is set, it is wrapped in `<Loop durationInFrames={Math.max(1, Math.floor(bg.seconds * fps))}>` with `trimBefore` 0.
  - `generated` → `<RunnerLoop seed={7} />`, an SVG of three perspective lanes, scrolling stripes, a 120 px rounded block at the lane x with `hop × 140` px lift, and the obstacles scaled by `z`. It draws `runnerState(frame, 7)` only.
  - No `background` → throw `Short: timeline has no background; run render.sh`.
- **Gated still test:**
  - It builds a 2-scene brainrot script with the `brainrot_script()` helper of `tests/test_video_timeline_brainrot.py`, then runs `narrate.py --engine say --speed 1.2` and `build-timeline.mjs` build mode.
  - It sets `background: {"kind": "generated"}`, copies the audio into `<app>/public/audio`, and runs `remotion still Explain <png> --props <timeline> --frame <n>` with cwd `<app>`.
  - It reads the PNGs with `tests/png_diff.read_png`.

- [ ] **Step 1: Write the gated tests.**

```python
test_short_still_is_portrait        # still at frame 20 -> width 1080, height 1920 (PNG header)
test_background_moves               # differing_pixels(frame 20, frame 40, x 0..1080, y 1000..1920, level 16) > 1000
test_caption_has_active_yellow      # still at the first word frame + 2: > 200 pixels with R>220, G>190, B<60 in y 860..1060
test_panel_is_white_above_the_seam  # row y=20 across x 0..1080 is (255,255,255) except the title text columns
test_missing_background_fails_loudly  # timeline without "background": remotion still exit != 0, output contains "Short: timeline has no background"
```

- [ ] **Step 2: Run them and see them fail.**
  Run: `cd skills/explain && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_short_still -v`
  Use the Bash timeout of 600000 ms. Expected: FAIL (there is no `Short` yet; the stills are landscape-in-portrait).
- [ ] **Step 3: Implement.** Move `SceneBody` and `FadeIn` into `sceneBody.tsx` without change and import them in both layouts.
- [ ] **Step 4: Run** the Task 2 typecheck, `test_short_still`, and the landscape regression.
  Expected: `tsc` exit 0, then `OK`, then `OK`.
- [ ] **Step 5: Look at one still** with the Read tool. Check: the title band is in the panel, the caption sits on the seam, the runner is in the bottom half, and no text overlaps. Record what you saw in the report.
- [ ] **Step 6: Commit:** `feat: explain: Short layout with caption band and generated or clip background`.

### Task 5: Background picker and the fixture clip

**Files:**
- Create: `skills/explain/video/pick_background.py`
- Create: `skills/explain/tests/make_bg_fixture.py` (stdlib PNG frames, then the workspace `remotion ffmpeg -framerate 30 -i f%02d.png -c:v libx264 -pix_fmt yuv420p -an -movflags +faststart`)
- Create: `skills/explain/tests/fixtures/bg-1s.mp4` (made by that script: 30 frames, 64×64, about 3 KB, checked in)
- Create: `skills/explain/tests/test_pick_background.py`
- Modify: `skills/explain/scripts/video-workspace.sh` (`mkdir -p "$ws/backgrounds"`)
- Modify: `skills/explain/tests/test_video_workspace.py` (one assertion: the folder exists after a run)

**Interfaces:**
- Consumes: `timeline.json` (`fps`, `totalFrames`).
- Produces: the picker CLI and the `background` field from the Interfaces section.
- **Order:** the good clips are taken as `sorted(names)` shuffled with `random.Random(seed)`. Without `--seed`, the seed comes from `EXPLAIN_BRAINROT_SEED`, else it is random.
- **Probe:** `[remotion, "ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json", <abs clip>]` with cwd `<app>`, stdin `/dev/null`, timeout 60 s.
- **Video length:** `totalFrames / fps`.
  - Clip ≥ video: `start = round(rng.uniform(0, clip − video), 3)` and `loop` false.
  - Clip < video: start 0 and `loop` true.
- **Link:** empty `<app>/public/bg/`, then symlink `clip<.ext lowercased>` → `os.path.realpath(clip)`. The timeline is rewritten in place with `indent=2`, keeping the existing keys.

- [ ] **Step 1: Write the failing tests.** A fake `remotion` script prints canned probe JSON per file name. The cases marked "real" use the workspace CLI and skip with a reason naming `video-workspace.sh` when it is missing.

```python
test_missing_folder_is_generated        # --dir /nonexistent -> "background: ok generated", timeline background == {"kind": "generated"}, public/bg empty
test_empty_folder_is_generated
test_non_video_and_hidden_files_ignored # notes.txt, .DS_Store only -> generated, no SKIP line
test_corrupt_clip_skipped_real          # bad.mp4 = b"not a video" -> stdout "background: SKIP bad.mp4 (ffprobe exit 1)" (unindented; render.sh indents it), then "background: ok generated"
test_fixture_clip_loops_real            # bg-1s.mp4, video 3 s -> "background: ok bg-1s.mp4 @0.0 s (loop)", src "bg/clip.mp4", seconds 1.0, public/bg/clip.mp4 -> realpath of fixture
test_long_clip_start_in_range           # fake duration 600, video 90 s, --seed 1..20 -> 0 <= start <= 510, loop False
test_equal_length_clip_no_loop          # fake duration == video length -> start 0.0, loop False, no "(loop)"
test_name_with_spaces_and_case          # "My Run 4K.MP4" (fake) -> stage line shows "My Run 4K.MP4", src "bg/clip.mp4"   (Review Focus 1)
test_symlinked_clip_resolves            # dir/link.mp4 -> ../real.mp4 -> public/bg/clip.mp4 points at real.mp4's realpath   (Review Focus 2)
test_no_video_stream_skipped            # fake JSON with only an audio stream -> "background: SKIP x.mp4 (no video stream)"
test_stale_link_removed                 # pre-existing public/bg/old.webm -> gone after a generated run
test_seed_is_deterministic              # same --seed twice, two clips -> same choice and start
```

- [ ] **Step 2: Run them and see them fail.**
  Run: `cd skills/explain && python3 -B -m unittest tests.test_pick_background -v`
- [ ] **Step 3: Generate the fixture.**
  Run: `python3 skills/explain/tests/make_bg_fixture.py skills/explain/tests/fixtures/bg-1s.mp4`
  Expected: one line with the output path, and a file of about 3 KB whose `remotion ffprobe` duration is `1.000000`.
- [ ] **Step 4: Implement the picker and the workspace folder.**
- [ ] **Step 5: Run:** `python3 -B -m unittest tests.test_pick_background tests.test_video_workspace`
  Expected: `OK` (the real cases run on this machine).
- [ ] **Step 6: Commit:** `feat: explain: brainrot background picker with a 1 s fixture clip`.

### Task 6: `render.sh`: speed, budgets from the timeline, the background stage

**Files:**
- Create: `skills/explain/video/check_budgets.py`
- Create: `skills/explain/tests/test_check_budgets.py`
- Modify: `skills/explain/scripts/render.sh`
  - Header: ten lines for brainrot.
  - `stage_script` reads `format` after `--check` passes.
  - `stage_narration` passes `--speed 1.2` when the format is `brainrot`, through the constant `BRAINROT_SPEED=1.2`.
  - `stage_timeline` calls `check_budgets.py`; `MAX_SCENE_S` and `MAX_TOTAL_S` are removed.
  - New `stage_background`, brainrot only, between `stage_timeline` and `stage_render`. It runs the picker through `stream "background: ok " "background: FAIL "`, so SKIP lines print indented, then prints the held ok line or fails.
- Modify: `skills/explain/tests/test_render.py` (the stage-one case for the brainrot template is in Task 8)

**Interfaces:**
- Consumes: the picker (Task 5) and `narrate.sh --speed`.
- Produces: the ten-line contract, with `--dir "${EXPLAIN_BRAINROT_BACKGROUNDS:-$ws/backgrounds}"`. The explainer prints no background line.

- [ ] **Step 1: Write the failing tests.** These are fixture timelines written by the test, with `fps` 30.

```python
test_explainer_scene_at_60_ok_and_over_fails   # 1800 frames -> "ok ..."; 1803 frames -> "FAIL scene a is 60.1 s (max 60)"
test_brainrot_scene_30_ok_31_fails             # maxSceneSeconds 30: 900 frames ok; 930 -> "FAIL scene a is 31.0 s (max 30)"
test_brainrot_total_90_ok_91_fails             # three 30 s scenes ok; total 2730 frames -> "FAIL total 91.0 s (max 90)"
test_explainer_total_text_unchanged            # 4530 frames total -> "FAIL total 151.0 s (max 150)"
test_missing_budget_keys_exit_2                # no maxSceneSeconds -> exit 2, one stderr line naming the key
```

- [ ] **Step 2: Run them and see them fail.**
  Run: `cd skills/explain && python3 -B -m unittest tests.test_check_budgets -v`
- [ ] **Step 3: Implement `check_budgets.py`, then rewire `render.sh`.**
- [ ] **Step 4: Run the always-on suite.**
  Run: `python3 -B -m unittest discover -s tests`
  Expected: `OK`. The `test_render` stage-one cases still pass.
  Then check the explainer stage lines: `EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render`
  Expected: `OK`, nine ok lines and no `background` line.
- [ ] **Step 5: Commit:** `feat: explain: render.sh reads budgets from the timeline and runs the brainrot background stage`.

### Task 7: Container size check and the transcript rows

**Files:**
- Modify: `skills/explain/video/check_render.sh`: `read_timeline` also prints `width` and `height`. `check_container` reads the video stream size through `remotion ffprobe -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x` and fails with `container: FAIL size <w>x<h>, expected <W>x<H>`. The ok line is unchanged.
- Modify: `skills/explain/video/transcript.py`: a `--background "<t>"` flag, default `pending`. A new marker `{{format_rows}}` is `""` for explainer and two `<div><dt>…</dt><dd>…</dd></div>` rows for brainrot: `Format` → `brainrot (1080×1920)`, and `Background` → the flag value. A new marker `{{video_class}}` is `""` for explainer and ` class="portrait"` for brainrot.
- Modify: `skills/explain/templates/video.html`
  - `<video{{video_class}} controls src="video.mp4">`;
  - `{{format_rows}}` after the Narrator row;
  - the CSS rule `video.portrait { aspect-ratio: 9 / 16; max-width: 405px; }`;
  - the header comment's marker list.
- Modify: `skills/explain/scripts/render.sh` `stage_transcript`: for brainrot, pass `--background`, taken from `build/timeline.json`: `<file> @ <start %.1f> s[ (loop)]` or `generated`.
- Modify: `skills/explain/tests/test_transcript.py`, `skills/explain/tests/test_check_render.py`

**Interfaces:** Consumes: the timeline `background` (Task 5). Produces: the rows of spec §6.3.

- [ ] **Step 1: Write the failing tests.**

```python
test_brainrot_rows_and_portrait_video      # brainrot script, --background "bg-1s.mp4 @ 0.0 s (loop)" -> dt Format/dd "brainrot (1080×1920)", dt Background/dd that text, <video class="portrait"
test_brainrot_background_pending_by_default  # no flag -> dd "pending"
test_explainer_page_has_no_format_row       # template script -> no "<dt>Format</dt>", "<video controls" unchanged
test_brainrot_transcript_passes_verify      # verify.sh on the brainrot page -> exit 0 (rows sit in the data-ste="skip" dl)
test_container_size_mismatch_fails          # (E2E class, reuses the fixture render) timeline width 1080, height 1920 -> "container: FAIL size 1280x720, expected 1080x1920"
```

- [ ] **Step 2: Run them and see them fail.**
  Run: `cd skills/explain && python3 -B -m unittest tests.test_transcript -v`, then `EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_check_render -v`
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the two commands of Step 2. Expected: `OK` twice. The existing container, sync and stills tests are unchanged.
- [ ] **Step 5: Commit:** `feat: explain: container size check and the brainrot transcript rows`.

### Task 8: Router, rung file and the brainrot template

**Files:**
- Modify: `skills/explain/SKILL.md`
  - `argument-hint` `[--as ste|sheet|page|video|brainrot]`; contract step 3 lists the five names.
  - A rung-table row `brainrot`: "Forced only: a vertical narrated short for a phone; never chosen from content".
  - The rule "the brainrot rung is English only, like the video rung"; the rung-files list gains `rungs/brainrot.md`.
  - All in STE.
- Create: `skills/explain/rungs/brainrot.md`, with exactly the spec §3.2 content:
  - which sections of `rungs/video.md` to read;
  - `"format": "brainrot"`;
  - the §3.4 limits table;
  - the background folder and how to force the generated loop;
  - the hook guidance;
  - the three extra still faults of §6.3;
  - the ten stage lines;
  - the narrator line at handoff;
  - the code-width command (`awk '{ gsub(/\t/, "    "); if (length($0) > 40) print NR }' <file>`).
- The output directory is `out/<stamp>-brainrot-<slug>/` (convention 5 with the rung name); the transcript keeps `<meta name="explain-rung" content="video">`, so `verify.sh` treats it as a video transcript.
- Create: `skills/explain/templates/brainrot-script.json`: 4 scenes about `scripts/verify.sh`.
  - Scene 1 is a `title` hook of 12 words or fewer.
  - One `code-with-line-highlights` scene uses a range of 14 lines or fewer, every line ≤ 40 columns.
  - One `bullets-appear` and one `before-after` scene.
  - Every text is within the brainrot limits; `provenance.root` is the relative `skills/explain`, as in the video template.
- Modify: `skills/explain/tests/test_render.py`: a brainrot stage-one case.

**Interfaces:** Consumes: `build-timeline.mjs --check`, `transcript.py`, `verify.sh`. Produces: the user-facing route `--as brainrot` and the template the E2E renders.

- [ ] **Step 1: Write the failing tests.**

```python
test_brainrot_template_checks          # build-timeline.mjs --check templates/brainrot-script.json --root skills/explain -> exit 0, no output
test_brainrot_template_passes_stage_one  # render.sh on a copy (absolute root), empty workspace path -> first line "script: ok (4 scenes)"
test_skill_md_lists_five_rungs         # SKILL.md argument-hint and contract step 3 both name brainrot
test_rung_file_lints_clean             # ste_lint.py on rungs/brainrot.md -> exit 0
```

- [ ] **Step 2: Run them and see them fail.**
  Run: `cd skills/explain && python3 -B -m unittest tests.test_render -v`
- [ ] **Step 3: Write the three files.** Choose the code range with the awk command above at 40 columns. If no 14-line range fits, use a diagram scene instead.
- [ ] **Step 4: Run** `python3 -B -m unittest discover -s tests`. Expected: `OK`.
- [ ] **Step 5: Commit:** `docs: explain: --as brainrot route, rung file and template`.

### Task 9: Gated brainrot E2E and the explainer after it

**Files:**
- Create: `skills/explain/tests/test_render_brainrot.py`. It renders `templates/brainrot-script.json` (absolute root) twice with `--engine say`, in temp output dirs, with `EXPLAIN_BRAINROT_BACKGROUNDS` set to an empty temp dir, then to a temp dir holding a copy of `fixtures/bg-1s.mp4`. Each render is cached once per process, like `video_e2e.py`. The timeout is 900 s each.
- Modify: `README.md` (Tests section: the brainrot E2E command)

**Interfaces:** Consumes everything above.

- [ ] **Step 1: Write the tests.**

```python
test_generated_ten_ok_lines         # stage names in order == the ten of the contract; "background: ok generated"
test_clip_ten_ok_lines              # "background: ok bg-1s.mp4 @0.0 s (loop)"
test_portrait_container             # remotion ffprobe width,height of video.mp4 == "1080x1920"
test_speed_in_sidecars              # every audio/*.say.txt has "speed=1.2\nmode=sentences\n"
test_transcript_rows                # index.html has Format "brainrot (1080×1920)" and the Background text of its run
test_stills_present                 # review/ holds one still-NN-<id>.png per scene plus one per cue
```

- [ ] **Step 2: Run the brainrot E2E, then the explainer E2E and the landscape regression in the same workspace** (Review Focus 3).
  Run: `cd skills/explain && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_brainrot && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render tests.test_check_render tests.test_landscape_regression`
  Use the Bash timeout of 600000 ms, or run it in the background with a log. Expected: `OK`, then `OK`.
- [ ] **Step 3: Sync headroom watch.** If `sync` fails on a brainrot scene with the tail cause, raise the brainrot `tailFrames` in `FORMATS` from 12 to 15 (0.5 s), and the spec §3.4 row with it. Re-run Step 2 and record the change in the report. If `sync` passes, change nothing.
- [ ] **Step 4: Read the stills** of the clip run with the Read tool (first scene, one cue still, the code scene). Check for the three faults of `rungs/brainrot.md` and for clipped code. Fix in the template or in `BRAINROT_BOX`, then re-run Step 2.
- [ ] **Step 5: Run the full suite:** `python3 -B -m unittest discover -s tests`. Expected: `OK`.
- [ ] **Step 6: Commit:** `test: explain: brainrot end-to-end with the generated loop and the fixture clip`.

## Acceptance (wave map)

- `cd skills/explain && python3 -B -m unittest discover -s tests` prints `OK`.
- `EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_brainrot` prints `OK`, with ten ok lines per render and 1080x1920 in each.
- `EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render tests.test_check_render tests.test_landscape_regression` prints `OK`: nine explainer lines, and the landscape pixels unchanged.
- The spec §7.3 fixture cases pass in `tests.test_pick_background`.

## Ordering and ownership

The tasks run in order 1 → 9.

- **Independent:** Tasks 1, 5 and 7, apart from 7's `render.sh` hunk, which follows 6.
- **Chain:** 2 → 4 and 3 → 4; 5 → 6 → 7.
- **Last:** 8 before 9; 9 last.
- **No parallel execution:** every task edits files under `skills/explain`, and Tasks 2, 4 and 9 share the workspace.

## Spec gaps and rulings (for the user's review)

1. **Stacking rule:** spec §4.2 stacks `before-after` "when the box is taller than wide", but the §4.3 panel content box is 984×758. The plan stacks through an explicit `SceneBox.stackPanels`. Spec §4.2 should be amended in the live-run fold-back.
2. **`background` field:** the §4.4 shape lacks a link name and the clip length. The plan adds `src` (fixed `bg/clip.<ext>`) and `seconds`.
3. **`Format` row on the explainer page:** spec §6.3 names the rows for brainrot only, so the explainer page gets no Format row and only one new CSS rule.
4. **Speed location:** spec §5.1 says `render.sh` sets the speed from the format. The plan keeps `BRAINROT_SPEED=1.2` in `render.sh`, not in `FORMATS`, so the value now lives in a second file next to the limits table.
5. **Declined:** the optional backtick-aware `--check` sentence start for brainrot is left out. A code-span cue still fails at build with a named line (wave-1 ruling).
