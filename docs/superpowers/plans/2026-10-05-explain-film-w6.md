# Explain film — wave `film-guard` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The `guard` stage measures the text of a film in the browser at its `checkFrames` and fails a film whose text is off the canvas, too small or overlapping; a film run prints eleven `ok` lines.

**Architecture:** `FilmStage` measures every `<text>` of the stage in a layout effect when the current frame is a check frame. It hands the measures to `kit/guard.ts`, which is pure logic and imports nothing, and ends the pass through `cancelRender` with the stage's FAIL line as the message. A new function of `render.sh`, `stage_guard`, runs for a film after the timeline: it renders composition `Film` at the check frames only, in the run directory, and reads the stage line from the log of that pass.

**Tech Stack:** bash 3.2 (`/bin/bash` of macOS), Python 3 `unittest`, Node (v25.9.0 on this machine), TypeScript 5.9.3, React, Remotion 4.0.532, as pinned in `video/`.

**Spec:** `docs/superpowers/specs/2026-10-05-explain-film-design.md`. This wave implements §7.3, the `guard` line of §7, the guard-logic bullet of §9.1, and the planted film and the mark plant of §9.2. Wave map: `docs/superpowers/waves/2026-10-05-explain-film.yaml`, wave `film-guard` (ralph wave 6, epic `kp-vv0`). Coverage: waived by the map.

Base: 55581725bff7bb566138283dd2a6fb7342eec728

Test runs: scoped per task; full suite once, final task.

## Global Constraints

- Work on this wave's own branch and worktree. Never commit to `main`, to `feat/explain-brainrot`, or directly to `feat/explain-film`. Never stage `.beads/`.
- A gated run (`EXPLAIN_VIDEO_E2E=1`) and every `render.sh` run are allowed only when `EXPLAIN_VIDEO_WORKSPACE` is set to the film branch's own workspace. Never render into `~/karpathy/video-workspace`: other sessions use it. Each such command below starts with `test -n "$EXPLAIN_VIDEO_WORKSPACE"` and prints the path. A command that ends there with no output means the variable is not set: do not render, and report it.
- No install from a test run. If a class is skipped for missing packages, run `scripts/video-workspace.sh --engine say` once, alone, in that workspace.
- No edit, not even one that is reverted, may make a real render write under `<ws>/app`.
- Files this wave may change, under `skills/explain/`: new `video/src/kit/guard.ts`, `video/src/FilmStage.tsx`, `scripts/render.sh`, new `tests/test_film_guard.py`, `tests/test_render_film.py`. The closed waves hand over two more (decision 12): `tests/test_render.py` (`FILM_STAGES`) and `tests/test_render_parallel.py` (one docstring line). The example's scene files `video/src/film/*.tsx` change only under decision 11, and the map only under the stop rule of Task 1. Nothing else: no `kit/index.ts`, no `build-timeline.mjs`, no rung file, no new dependency.
- Stage lines: a film run prints eleven, brainrot ten, the explainer nine. `STAGES` keeps its ten brainrot names (ruling 5 of `kp-uu1`). These names stay importable from where they are: `STAGES`, `FILM_STAGES`, `STAGE_LINE`, `stage_lines`, `render_functions`, `RUN_FAKES`, `RunHarness`, `names`, `ORDER`, `SCENE_FILES`, `film_output`, `render_output`, `render_film`, `FAKE_TSC`, `SCENE_RUN_FAKES`, `run_functions`.
- Every pre-existing test case passes unchanged, except the three that Task 1 names. An explainer or brainrot run prints the same lines as at the base.
- A tool that runs with cwd `$run` is run as `(cd "$run" && exec <tool>)`, so that `render.sh` waits for it. No recursive command may run on a path of `$run` (close note of `kp-xdd`).
- Tests: `unittest`, run from `skills/explain`. Each test names the mutation that turns it red, as the files do today. Each new assertion is seen to fail before the code exists. One that passes at once is checked by applying its named mutation, seeing the failure, and reverting.
- Baseline at the base (run at planning): `python3 -B -m unittest discover -s tests` gives `Ran 692 tests`, `OK (skipped=45)`.
- Commits: `<type>: explain: <description>`, ending with the attribution line of the session.

## What the closed waves left for this one

Read from the close notes of `kp-fzq`, `kp-xdd`, `kp-osb` and `kp-uu1`. Each is placed in a task.

- `guard` goes into `FILM_STAGES` of `tests/test_render.py`, never into `STAGES`: the always-run brainrot test compares a brainrot run with `STAGES` (Task 1).
- The guard pass is one more tool with cwd `$run`: `exec` in a subshell, with its own always-run test of a CLI that outlives the signal. `FAKE_CLI` of `RUN_FAKES` serves both passes (Tasks 1 and 3).
- The film's `ORDER` gets an eleventh pattern (Task 1). The header of `render.sh` loses "does not exist yet" (Task 3).
- The cwd of the guard pass is pinned by a test of its own; `test_a_film_renders_composition_film` does not pin it (Task 3).
- `clear_stale` already removes `build/guard.mp4` for every format (wave 4, decision 2); this wave does not change it.
- Three readers saw no text off the canvas, under 14 px or over another text in the stills of the example, but no stage has measured it yet. The code card's rows (24 px boxes on a 32 px pitch) and its gutter were measured not to overlap. `Mark` at opacity 0 draws strokes and no text. Films render in Menlo in the headless shell (Task 1, control render).

## Beyond the letter of the spec

The spec and the map leave these points open. They are decided here, so that every task builds the same thing. Points 1, 2 and 5 rest on reads and probes of Remotion 4.0.532 made at planning, in a throwaway project linked to the film workspace's packages.

1. **One-frame ranges, not a comma list.** In the pinned CLI, `--frames=12,47,89` makes an image sequence, and an output named `*.mp4` fails at once with `The output directory of the image sequence cannot have an extension. Got: mp4` (`@remotion/cli/dist/get-cli-options.js`, probed). `--frames=12-12,47-47,89-89` renders an mp4 of exactly those frames (probed). The pass is therefore `remotion render Film <out>/build/guard.mp4 --frames=<f1>-<f1>,<f2>-<f2>,... --concurrency=1 --muted --props <out>/build/timeline.json`.
2. **The marker is the line itself.** The message given to `cancelRender` is the stage line, `guard: FAIL frame <f> (scene <id>): ...`, built by `guardLine` of `guard.ts`. A mark error keeps the message of `marks.ts`, `MARK scene <id>: <cause>`. In the log the message is the line ` Error  <message>`, and the line `An error occurred while rendering frame <f>:` comes before it, for a cancel and for a mark error. A code frame of the source can follow and repeat text of the source. The log has no ANSI escapes. All of this was probed. `render.sh` takes the first log line that holds `guard: FAIL frame ` or `MARK scene `. From a frame line it prints the text from the marker to the end of the line. From a mark line it prints `guard: FAIL mark: ` and then the text after `MARK `.
3. **A marker fails the stage whatever the exit code of the pass.** A cancel that the CLI reads late, or never, cannot pass the guard. In the probe, a cancel at the last frame of the list still exited 1.
4. Nothing follows the frame line and the mark line: the log stays in `<out>/build/guard.log`. The third line, `guard: FAIL remotion render exit <n> (log <out>/build/guard.log)`, has the last 40 log lines below it, indented by two spaces, as the render stage does.
5. **The pass needs no narration clip.** It runs before the render stage copies the clips, with `--muted`. `Html5Audio` without `loop` puts no `<audio>` tag in the page while it renders (`remotion/dist/cjs/audio/AudioForRendering.js`, read).
6. `<n>` of `guard (<n> frames): ok` is the number of entries of `checkFrames`. If the timeline cannot be read, or holds no `checkFrames`, or a frame that is not an integer of 0 or more, the line is `guard: FAIL cannot read <out>/build/timeline.json` and no pass runs.
7. **What is measured, exactly.** These are the `<text>` elements under the stage `<svg>`, in document order. The text is `textContent`. The opacity is the product of the computed `opacity` of the element and of each ancestor up to and including the stage `<svg>`. The box is `getBoundingClientRect()`, moved by the `left` and `top` of the stage `<svg>`'s own rect, so that it is in canvas pixels. `px` is the smallest computed `font-size` of the element and of its `<tspan>` descendants, times `Math.hypot(c, d)` of the element's `getScreenCTM()`. A text whose `getScreenCTM()` is `null` is not drawn and is not measured.
8. **Faults: the order and the text.** The faults come text by text, in document order. For each text: its `OFFCANVAS`, then its `SMALLTEXT`, then one `OVERLAP` with each later text that it overlaps, in document order. The line holds the first five faults, joined by `; `. When there are more, ` (+<n> more)` follows. `<px>` is written with `toFixed(1)`. `<text>` is the content with each run of white space made one space, then trimmed, then cut to its first 24 code points, with no ellipsis.
9. `guard.ts` is the pipeline's, as `makeAt` is. `FilmStage` imports it as `./kit/guard`. It is not exported from `kit/index.ts`, whose surface `TestKitCompiles` pins.
10. **The proof comes first (spec §7.3, map `done_when`).** Task 1 is the first task that touches the guard. It proves the measurement with the planted film of §9.2 in three runs in a row. It also proves it with a fault shown only at the last check frame, the case where a late measurement would pass unseen. If the proof fails, the stop rule of Task 1 applies.
11. If the unedited example fails the guard, the fault is fixed in the example's scene files by one of the honest fixes of spec §7.3. That is the only reason this wave changes `video/src/film/`. The scene ids, the template and `script.gen.ts` stay as they are. A guard rule or a threshold is never changed to make the example pass.
12. Two test files outside the map's `owns` list change. `tests/test_render.py`: `FILM_STAGES` gets `guard`, as the close note of `kp-uu1` asks. `tests/test_render_parallel.py`: its docstring says "ten" for the film's lines and becomes "eleven".
13. The plants are edits of a `film_output()` copy, as the stage plants are: the test writes a component file into `scene/` and draws it in `Film.tsx`. Nothing of them is committed under `video/src/film/`. The example has no scene `type`, so the mark plant of §9.2 uses scene `subject`.

## Review Focus

1. A fault at the last check frame passes, because the pass ends before anything reads the cancel. Task 1: `test_a_fault_at_the_last_check_frame_fails`. Task 3: `test_a_marker_fails_even_after_exit_0`.
2. The author gets a line of source text, or two lines, in place of the fault: a code frame below the error repeats the marker. Task 3: `test_a_frame_fault_is_the_stage_line`.
3. The guard measures the wrong tree: it skips a visible text (it misses a scaled group, or it reads the size of the `<text>` and not that of a smaller `<tspan>`), or it raises a false alarm on a text at opacity 0. Task 1: the planted film (`half scale`, `hidden`). Task 2: `test_faint_and_blank_texts_are_not_measured`, `test_smalltext_is_below_min_text`.
4. A signal during the guard pass leaves the run directory, or a CLI that still writes into it. Task 3: `test_render_sh_waits_for_a_guard_pass_that_outlives_the_signal`.
5. An explainer or brainrot run gets a guard pass, which costs a render and adds a line. Task 3: `test_another_format_has_no_guard_stage`. The always-run `test_a_brainrot_run_prints_exactly_the_stages_of_STAGES` stays green.

Accepted, not tested: a mark error in a branch of the scene code that no check frame reaches is not caught by the guard. It ends the render stage with `render: FAIL remotion render exit 1`, and the log holds the `MARK` line. This goes to `film-docs` (Wave close).

---

### Task 1: the measurement, proven on a planted film

**Files:**
- Create: `skills/explain/video/src/kit/guard.ts`
- Modify: `skills/explain/video/src/FilmStage.tsx` (the measurement; the header comment)
- Modify: `skills/explain/scripts/render.sh` (new function `stage_guard` after `stage_timeline` at 397-408; its call after `stage_timeline` at 496)
- Modify: `skills/explain/tests/test_render_film.py` (docstring; `ORDER` at 122-133; `SCENE_RUN_FAKES` at 436-444; `SceneRunCase` at 486-527; `test_film_prints_ten_ok_lines` at 587; new gated class `GuardPlantCase`)
- Modify: `skills/explain/tests/test_render.py` (`FILM_STAGES` and its comment at 44-47)
- Modify: `skills/explain/tests/test_render_parallel.py` (docstring line 10)

**Interfaces:**
- Consumes: `checkFrames` of the film timeline (`{ frame, scene, still }[]`, `video/src/types.ts`); `STAGE`, `MIN_TEXT` of `kit/palette.ts`; `film_output`, `render_output`, `ORDER`, `split_sentences`, `TEMPLATE_SCENES`, `stage_lines` (already in `test_render_film.py`).
- Produces, for Tasks 2 to 4:

  ```ts
  // video/src/kit/guard.ts: imports nothing; not exported from kit/index.ts
  export type Box = { left: number; top: number; right: number; bottom: number };
  export type Measured = { text: string; opacity: number; px: number; box: Box };
  export const shortText: (text: string) => string;
  export const faultsOf: (texts: readonly Measured[], canvas: { width: number; height: number },
                          minText: number) => string[];
  export const guardLine: (frame: number, scene: string, faults: readonly string[]) => string;
  ```

  ```bash
  stage_guard()   # reads fmt, out, run, remotion; calls fail
  ```

  ```
  guard (<n> frames): ok
  guard: FAIL frame <f> (scene <id>): <fault>[; <fault> ...][ (+<n> more)]
  guard: FAIL remotion render exit <n> (log <out>/build/guard.log)     the last 40 log lines follow, indented
  guard: FAIL cannot read <out>/build/timeline.json
  ```

  ```python
  # tests/test_render_film.py
  CHECK_FRAMES: int   # the check frames of the template: for each scene, its sentences (split_sentences) and one
  def add_to_film(test, out, name, text, element) -> None   # writes scene/<name>.tsx; Film.tsx imports <name> and draws element
  class GuardPlantCase(unittest.TestCase)                    # gated by E2E
  ```

- [ ] **Step 1: Write the failing tests.**

  Always run:
  - `FILM_STAGES` of `test_render.py` becomes `("scene", "guard")`, and its comment names both.
  - In `SCENE_RUN_FAKES`, the timeline that the fake `build-timeline.mjs` writes also holds `checkFrames`: frame 3 of scene `s1` (still `s1`) and frame 89 of scene `s1` (still `end`). The other calls of the fake stay as they are.
  - `test_a_film_run_prints_ten_stage_lines` becomes `test_a_film_run_prints_eleven_stage_lines`. The names are those of the base with `guard` after `timeline`. The sixth line is `guard (2 frames): ok`. For `explainer` and `brainrot`, no line starts with `guard`, and `cli_calls()` holds one call. Red: the stage is not called, or it is called for every format.
  - `test_the_render_draws_the_copied_scene`: `cli_calls()` holds two calls. The first is the guard pass: its `argv` is `render`, `Film`, `<out>/build/guard.mp4`, `--frames=3-3,89-89`, `--concurrency=1`, `--muted`, `--props`, `<out>/build/timeline.json`. The second is the render, as before. Both have the cwd of `tsc`. Red: the pass runs in the app, or with a comma list.

  Gated (`E2E`): `ORDER` gets `r"guard \(%d frames\): ok" % CHECK_FRAMES` after the timeline pattern. `test_film_prints_ten_ok_lines` becomes `test_film_prints_eleven_ok_lines`, with the same body. `add_to_film(test, out, name, text, element)` writes `out/scene/<name>.tsx` with `text`. It puts `import { <name> } from "./<name>";` on the line after `import type { Props } from "./script.gen";`, and the line `      <element>` before the line that starts `      <Prompt subject=` in `out/scene/Film.tsx`. The test fails if one of the two anchors is not there.

  `GuardPlantCase` renders `film_output(edit)` with `render_output`. A helper `stops_at_the_guard(edit)` asserts these things and returns `(out, last stage line, checkFrames of out/build/timeline.json)`: exit 1; the first five stage lines match `ORDER[:5]`; there are exactly six stage lines; no stage line starts with `render`; `out/video.mp4` does not exist; `out/build/guard.log` exists. `FilmRenderCase` is the control: the same output without the edit.

  - `test_the_planted_film_fails_at_its_first_check_frame`: the edit is `add_to_film(..., "Plant", ..., "<Plant />")`. `Plant` returns one `<g>` with these labels, in this order, each a kit `Sans`:

    | Text | Size | x, y | Wrapped in | Expected fault |
    |---|---|---|---|---|
    | `off canvas` | 20 | 1400, 700 | | `OFFCANVAS "off canvas"` |
    | `ten px` | 10 | 40, 700 | | `SMALLTEXT 10.0 px "ten px"` |
    | `half scale` | 20 | 400, 1400 | `<g transform="scale(0.5)">` | `SMALLTEXT 10.0 px "half scale"` |
    | `twin one` | 20 | 600, 700 | | `OVERLAP "twin one" \| "twin two"` |
    | `twin two` | 20 | 600, 700 | | (named with `twin one`) |
    | `hidden` | 20 | 1400, 660 | `<g opacity={0}>` | none |

    The test renders this film three times, each into its own output directory. After each render it calls `stops_at_the_guard`, so a run that exits 0 stops the test at once. Each last line must equal `guard: FAIL frame <f> (scene subject): OFFCANVAS "off canvas"; SMALLTEXT 10.0 px "ten px"; SMALLTEXT 10.0 px "half scale"; OVERLAP "twin one" | "twin two"`, where `<f>` is the `frame` of the first entry of that run's `checkFrames`. The three lines must also be equal to each other. Red: no guard stage (the run exits 0), a measure that ignores the scale or the opacity of a group, or faults in another order.
  - `test_a_fault_at_the_last_check_frame_fails`: the edit is `add_to_film(..., "Late", ..., '<Late last={at.end("handoff") - 1} />')`. `Late` takes `{ last: number }` and draws the kit `Sans` `late`, size 20, at 1400, 700, only when `useCurrentFrame()` equals `last`. The last entry of `checkFrames` is scene `handoff`, and its frame is the timeline's `totalFrames - 1`. The last stage line is `guard: FAIL frame <that frame> (scene handoff): OFFCANVAS "late"`. Red: the pass ends before the cancel of its last frame is read.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render_film.SceneRunCase tests.test_render`
  Expected: `FAILED`. The eleven-line test fails (ten lines, no `guard`), and the copied-scene test fails (one CLI call).

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film.GuardPlantCase`
  Expected: the workspace path, then `FAILED`. Both cases fail on exit 0 after their first render. About 6 minutes.

- [ ] **Step 3: Write `kit/guard.ts`.** It holds the signatures of the Produces block and imports nothing. Contract:
  - `shortText`: decision 8.
  - `faultsOf` measures a text when its `text` holds a character that is not white space and its `opacity` is 0.1 or more. The others take part in no rule.
  - `OFFCANVAS "<t>"` when `left < -1`, `top < -1`, `right > canvas.width + 1` or `bottom > canvas.height + 1`.
  - `SMALLTEXT <px> px "<t>"` when `px < minText`.
  - `OVERLAP "<a>" | "<b>"` for two measured texts whose boxes overlap by more than 2 on both axes. The overlap on an axis is the smaller end minus the larger start.
  - The order of decision 8.
  - `guardLine` returns `guard: FAIL frame <frame> (scene <scene>): ` followed by the faults as decision 8 joins them.
  - The file's comment says what the guard does not see (spec §7.3, the paragraph "What the guard does not see").

- [ ] **Step 4: Measure in `FilmStage`.** Contract:
  - `FilmStage` reads `useCurrentFrame()` and holds a ref to the stage `<svg>`.
  - A `useLayoutEffect` on the frame and on `checkFrames` finds the entry of `checkFrames` whose `frame` is the current frame. With none, it does nothing.
  - With one, it measures by decision 7 and calls `faultsOf(measured, STAGE, MIN_TEXT)`. When there are faults, it calls `cancelRender(new Error(guardLine(frame, entry.scene, faults)))`.
  - The measurement runs in every render of composition `Film`: the guard pass, and the render stage, where the frames have passed (spec §7.4).
  - The header comment says that the stage measures the text at each check frame and ends the render with the guard's line, and why in a layout effect: the measured tree is the tree that ships.

- [ ] **Step 5: Write `stage_guard` and call it.** Contract:
  - For a format that is not `film` it returns at once.
  - It reads the frames with `python3` from `$out/build/timeline.json`, as `stage_render` reads the clips. Decision 6 applies.
  - The pass is the command of decision 1, run as `(cd "$run" && exec "$remotion" render Film ...) > "$out/build/guard.log" 2>&1 < /dev/null`, as the CLI call of `stage_render` is. A comment gives the same reason as there.
  - On a non-zero exit: the frame line of decision 2 when the log holds the marker `guard: FAIL frame `; else the exit line of decision 4. Each is followed by `exit 1`. (Task 3 makes the marker count after exit 0 too; Task 4 adds the mark line.)
  - Then `guard (<n> frames): ok`.
  - It is called after `stage_timeline` and before `stage_background`.
  - The comment above the function says what the pass renders and where, and why it needs no clip (decision 5).

- [ ] **Step 6: Run the always-run tests and see them pass.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render_film tests.test_render tests.test_film_kit tests.test_film_example`
  Expected: `OK`; the gated cases are skipped.

- [ ] **Step 7: The proof, then the control.**

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film.GuardPlantCase tests.test_render_film.FilmRenderCase`
  Expected: the workspace path, then `OK` with no skip. The planted film gives its line three times; the late plant gives its line; the example prints eleven `ok` lines. About 12 minutes.

  If `FilmRenderCase` alone fails with a `guard: FAIL frame` line, apply decision 11, then run the command again.

  **Stop rule.** You may make at most two fix rounds that keep the design: the measurement is a layout effect of `FilmStage` that ends the pass through `cancelRender`, and the pass is the CLI call of Step 5. If after them `GuardPlantCase` still fails, the measurement cannot be made to work. Then:
  - commit what was tried as `wip: explain: guard measurement attempt, blocked`;
  - add a comment on this task's issue with the stage lines of the three planted runs and the late run, and the tail of each `guard.log`, and leave the issue open;
  - set `status: blocked` on wave `film-guard` in the map, with a one-line comment that gives the reason, and commit only the map;
  - run no later task. The design goes back to the user (spec §7.3).

- [ ] **Step 8: Commit.**

  ```bash
  git add skills/explain/video/src/kit/guard.ts skills/explain/video/src/FilmStage.tsx skills/explain/scripts/render.sh skills/explain/tests/test_render_film.py skills/explain/tests/test_render.py skills/explain/tests/test_render_parallel.py
  git commit -m "feat: explain: the guard stage measures film text at the check frames; proven on a planted film"
  ```

  Add the example's scene files by name if decision 11 changed them.

---

### Task 2: the guard logic, in Node

**Files:**
- Create: `skills/explain/tests/test_film_guard.py`

**Interfaces:**
- Consumes: the exports of `kit/guard.ts` (Task 1); `EvaluatesJs`, `kit_url`, `NODE`, `NO_NODE_REASON`, `KIT` of `tests/test_film_kit.py`.
- Produces: `tests.test_film_guard`, the map's first acceptance command. Nothing that a later task calls.

- [ ] **Step 1: Write the tests.** `GuardLogicCase(EvaluatesJs)`, skipped without Node. Its `PRELUDE` imports `shortText`, `faultsOf` and `guardLine` from `kit_url("guard.ts")`. The canvas is `{ width: 1280, height: 720 }` and `minText` is 14. A helper of the test builds a measured text: text, opacity 1, px 20 and a box, unless the test sets them. The docstring says that the cases are those of spec §9.1, on made-up boxes.
  - `test_offcanvas_is_more_than_one_px_past_an_edge`: a box 2 px past each edge in turn gives `['OFFCANVAS "a"']`. The same box 1 px past gives `[]`. Red: `>=` for `>`, or one edge left out.
  - `test_smalltext_is_below_min_text`: px 13.9 gives `['SMALLTEXT 13.9 px "a"']`; px 14 gives `[]`; px 10 gives `['SMALLTEXT 10.0 px "a"']`. Red: `<=` for `<`, or the px written without its decimal.
  - `test_overlap_is_more_than_two_px_on_both_axes`: an overlap of 3 px on both axes gives `['OVERLAP "a" | "b"']`. 2 px on x and 10 on y gives `[]`, and so do 10 on x and 2 on y. Red: one axis is enough, or `>=` for `>`.
  - `test_faint_and_blank_texts_are_not_measured`: a text off the canvas at opacity 0.09 gives `[]`, and at opacity 0.1 one fault. A text of white space only off the canvas gives `[]`. A text at opacity 0.09 over a measured text gives no `OVERLAP`. Red: no opacity floor, `>` for `>=`, or a blank text measured.
  - `test_faults_come_in_document_order`: three texts. A is off the canvas, small, and over C. B is small. C is plain. The result is exactly `OFFCANVAS "A"`, `SMALLTEXT ... "A"`, `OVERLAP "A" | "C"`, `SMALLTEXT ... "B"`. Red: the faults are grouped by kind, or an overlap is placed at its second text.
  - `test_short_text`: `"  two\n  words  "` gives `two words`. A text of 30 letters gives its first 24. A text of 23 letters and one emoji outside the BMP gives all 24 code points. Red: no collapse, or a cut by UTF-16 units.
  - `test_guard_line`: one fault gives `guard: FAIL frame 47 (scene b): X`. Five faults are joined by `; ` with no suffix. Six give the first five, then ` (+1 more)`. Red: six shown, or no suffix.
  - `test_guard_imports_nothing_and_is_not_a_scene_name`: `guard.ts` holds no line that starts with `import`, and `kit/index.ts` does not hold the word `guard`. Red: `guard.ts` imports `MIN_TEXT` from the palette, or the index exports it.

- [ ] **Step 2: Run them.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_film_guard`
  Expected: `OK`, no skip. `guard.ts` exists since Task 1, so each case passes at once.

- [ ] **Step 3: Check each case by its named mutation.** For each case, apply the first mutation that its comment names to `guard.ts` (to `kit/index.ts` for the last case). Run the case and see it fail, then revert with `git checkout -- skills/explain/video/src/kit/`.

- [ ] **Step 4: Commit.**

  ```bash
  git add skills/explain/tests/test_film_guard.py
  git commit -m "test: explain: the guard's rules on made-up boxes, in Node"
  ```

---

### Task 3: the guard stage on fakes

**Files:**
- Modify: `skills/explain/scripts/render.sh` (`stage_guard`: a marker counts after exit 0; the header comment at 1-110)
- Modify: `skills/explain/tests/test_render_film.py` (docstring; new `FAKE_PASS` and class `GuardStageCase` after `SceneStageCase`; a new case of `SceneRunCase`)

**Interfaces:**
- Consumes: `stage_guard` and its lines (Task 1); `run_functions`, `SceneRunCase` and its helpers, `RunHarness.wait_for_cli`, `cli_calls`, `names` (already in the modules).
- Produces, for Task 4:

  ```python
  # tests/test_render_film.py
  FAKE_PASS: str   # a fake remotion (Python). It appends {"argv", "cwd" (real path)} as one JSON line to
                   # $FAKE_DIR/pass.jsonl, prints the file $FAKE_PASS_LOG when set, and exits $FAKE_PASS_EXIT
                   # (default 0)
  class GuardStageCase(unittest.TestCase)
      def guard(self, fmt="film", log=None, code=0) -> subprocess.CompletedProcess   # log: the text the fake prints
      def passes(self) -> list                                                       # the calls of the fake
  ```

- [ ] **Step 1: Write the tests.** `GuardStageCase` runs `stage_guard` alone, through `run_functions(tmp, ["fail", "stage_guard"], setup)`. `setUp` makes `out/build/timeline.json`, with `checkFrames` at frames 12 (scene `a`), 47 (scene `b`) and 89 (scene `b`, still `end`). It also makes `run/` and an executable `remotion` with the text `FAKE_PASS`. `guard` sets `fmt`, `out`, `run` and `remotion`, exports `FAKE_DIR`, `FAKE_PASS_EXIT` and, when `log` is given, `FAKE_PASS_LOG`, then calls `stage_guard`.
  - `test_the_pass_renders_the_check_frames_in_the_run_directory`: exit 0, stdout `guard (3 frames): ok`. There is one call: `argv` is `render`, `Film`, `<out>/build/guard.mp4`, `--frames=12-12,47-47,89-89`, `--concurrency=1`, `--muted`, `--props`, `<out>/build/timeline.json`, and `cwd` is the real path of `run`. Red: a comma list (decision 1), the cwd of the caller, or no `--concurrency=1`.
  - `test_another_format_has_no_guard_stage`: `explainer` and `brainrot` give exit 0, no output and no call. Red: the pass runs for every format.
  - `test_a_frame_fault_is_the_stage_line`: the log has these lines: `Rendered 1/3`, `An error occurred while rendering frame 47:`, ` Error  guard: FAIL frame 47 (scene b): OFFCANVAS "x"`, `at src/FilmStage.tsx:40`, `40 │   cancelRender(new Error(guardLine(frame, "guard: FAIL frame 1 (scene z): y", faults)));`. Code 1 gives exit 1 and stdout exactly `guard: FAIL frame 47 (scene b): OFFCANVAS "x"`. Red: the last marker line wins, ` Error  ` is kept, or log lines follow.
  - `test_a_marker_fails_even_after_exit_0`: the same log with code 0 gives exit 1 and the same one line. Red: the log is read only after a non-zero exit (the code of Task 1).
  - `test_any_other_failure_shows_the_log_tail`: a log of 50 lines `line 1` to `line 50` with code 3 gives `guard: FAIL remotion render exit 3 (log <out>/build/guard.log)`, then `  line 11` to `  line 50`. Red: no tail, the head, or no exit code.
  - `test_a_timeline_that_cannot_be_read`: five sub-tests: no `timeline.json`; text that is not JSON; no `checkFrames`; `checkFrames` empty; a frame of `-1`. Each gives exit 1, the one line `guard: FAIL cannot read <out>/build/timeline.json`, and no call. Red: a pass with `--frames=` empty, or a traceback.

  `SceneRunCase`, `test_render_sh_waits_for_a_guard_pass_that_outlives_the_signal`: for TERM and for HUP, `start("film", FAKE_REMOTION_SLEEP="30", FAKE_REMOTION_OUTLIVE="1")`. After `wait_for_cli` the signal goes to the process group. Then `finish(proc, timeout=10)` gives exit 1 and no line with `FAIL`. `remotion.end` exists within 10 s. `cli_calls()` is one call whose `argv` holds `--frames=3-3,89-89`. `names(self.runs)` is `[]`, and `sentinel.txt` is still in the shared packages. Red: the pass is run in a subshell without `exec`. Then `render.sh` exits first, and the late write of the CLI makes the run directory again.

- [ ] **Step 2: Run them and see the new rule fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render_film.GuardStageCase tests.test_render_film.SceneRunCase`
  Expected: `FAILED`, and only `test_a_marker_fails_even_after_exit_0` fails: the run exits 0 and prints `guard (3 frames): ok`.

- [ ] **Step 3: Read the marker whatever the exit code; write the header.** Contract:
  - In `stage_guard`, the log is read for the marker after every pass (decision 3). The exit line comes only after a non-zero exit with no marker.
  - The header comment of `render.sh` says that a film run has eleven stages and brainrot ten. It drops "does not exist yet". The stage list gets the line `guard (<n> frames): ok`, which says: film only; composition `Film` at the check frames of the timeline, into `build/guard.mp4`, log `build/guard.log`; `FilmStage` measures the text at each frame. A section names the FAIL lines of the stage as decisions 2, 4 and 6 give them. The paragraph on the run directory says that the guard pass runs there, as the render does, and that `render.sh` waits for it.

- [ ] **Step 4: Run the tests and see them pass.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render_film tests.test_render`
  Expected: `OK`; the gated cases are skipped.

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/scripts/render.sh skills/explain/tests/test_render_film.py
  git commit -m "feat: explain: a guard marker fails the stage whatever the exit; the stage's lines and the pass's signals pinned"
  ```

- [ ] **Step 6: Check the cases that passed at once.** After the commit, so that a revert loses nothing: for each case that passed in Step 2, apply its first named mutation to `stage_guard`. For the signal case, that is the pass in a subshell without `exec`. Run the case and see it fail, then revert with `git checkout -- skills/explain/scripts/render.sh`. `git status --short` prints nothing at the end.

---

### Task 4: the mark line, and the wave's acceptance

**Files:**
- Modify: `skills/explain/scripts/render.sh` (`stage_guard`: the mark line; the header's FAIL lines)
- Modify: `skills/explain/tests/test_render_film.py` (docstring; a case of `GuardStageCase`; a case of `GuardPlantCase`)

**Interfaces:**
- Consumes: `GuardStageCase.guard` (Task 3); `GuardPlantCase.stops_at_the_guard` (Task 1).
- Produces: `guard: FAIL mark: scene <id>: <cause>`, the second line of spec §7.3.

- [ ] **Step 1: Write the failing tests.**
  - `GuardStageCase.test_a_mark_error_is_the_stage_line`: the log has `An error occurred while rendering frame 12:`, then ` Error  MARK scene b: word "zebra" is not in the narration`, then a code-frame line `5 │ throw markError(scene.id, "MARK scene");`. Code 1 gives exit 1 and stdout exactly `guard: FAIL mark: scene b: word "zebra" is not in the narration`. Red: the exit line of decision 4, or `MARK` kept in the line.
  - `GuardPlantCase.test_a_word_that_is_not_said_stops_at_the_guard`: the edit writes the first `at("subject", { word: "subject" })` of `scene/Film.tsx` as `at("subject", { word: "zebra" })`, and fails if that text is not there. `stops_at_the_guard` holds, and the last stage line is `guard: FAIL mark: scene subject: word "zebra" is not in the narration`. Red: the mark error ends the pass as `guard: FAIL remotion render exit 1`.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render_film.GuardStageCase`
  Expected: `FAILED`; only the mark case fails, on the exit line.

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film.GuardPlantCase.test_a_word_that_is_not_said_stops_at_the_guard`
  Expected: the workspace path, then `FAILED`, on `guard: FAIL remotion render exit 1 (log ...)`.

- [ ] **Step 3: Write the mark line.** In `stage_guard` the first log line that holds either marker gives the stage line, by decision 2. In the header, the stage's FAIL lines get the mark line and say when it comes: a mark error of spec §6 thrown at a check frame.

- [ ] **Step 4: Run the tests and see them pass.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render_film tests.test_render`
  Expected: `OK`; the gated cases are skipped.

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film.GuardPlantCase`
  Expected: the workspace path, then `OK` with no skip: the planted film three times, the late plant and the mark plant. About 8 minutes.

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/scripts/render.sh skills/explain/tests/test_render_film.py
  git commit -m "feat: explain: a mark error at a check frame is the guard's mark line"
  ```

- [ ] **Step 6: Run the full unit suite, once.**

  Run: `cd skills/explain && python3 -B -m unittest discover -s tests`
  Expected: `OK (skipped=48)`. That is the 45 of the base and the three cases of `GuardPlantCase`. No failure and no error. The test count is the base's 692 plus this wave's new cases.

- [ ] **Step 7: Run the map's acceptance.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_film_guard`
  Expected: `OK`, no skip.

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film tests.test_render tests.test_render_brainrot tests.test_render_parallel`
  Expected: the workspace path, then `OK` with no skip. The film prints eleven lines, the explainer nine (`SayFixtureCase`) and brainrot ten (`BrainrotRenderCase`, and the pair of `ParallelRenderCase`). The planted film gives the same guard line in three runs (`GuardPlantCase`). About 25 minutes.

  Then check the tree. `git status --short` prints nothing. `git diff --stat 55581725bff7bb566138283dd2a6fb7342eec728 -- . ':!docs'` lists only files that the Global Constraints allow. `ls "$EXPLAIN_VIDEO_WORKSPACE/runs"` prints nothing.

## Wave close

The map's `done_when` is met as follows:
- Task 1 Step 7 proves the measurement first: the planted film gives one `guard: FAIL frame` line, the same in three runs, that names the four planted faults and not the label of opacity 0. A fault at the last check frame is caught.
- Task 2 runs the guard-logic cases of spec §9.1 in Node.
- Task 4 Step 4 shows the mark plant's `guard: FAIL mark:` line with the word.
- Task 1 Step 7 and Task 4 Step 7 show the unedited example with eleven `ok` lines.

Inputs for the plans of later waves:

- `film-docs`: quote the four FAIL lines of the stage from the header of `render.sh`. The guard measures only at the check frames. A mark error in code that no check frame reaches ends the render stage with `render: FAIL remotion render exit 1`, and its `MARK` line is in `build/render.log`. The guard pass costs one more bundle and one frame per check frame. `--frames` is a list of one-frame ranges (decision 1). The rung file gives the three honest fixes of spec §7.3, and what the guard does not see.
- `film-live-run`: count each guard fault that had no honest fix, for D6. The 14 px floor is `MIN_TEXT`, and `guard.ts` takes it as an argument, so a fold-back changes only the palette.
- `explainer-removal`: `GuardStageCase` and `FAKE_PASS` can move to `tests/video_e2e.py` with the other helpers.
