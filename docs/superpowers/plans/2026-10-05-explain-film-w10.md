# Explain film — wave `explainer-default` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A script without a `format` key is a film for the narration, the validator and `render.sh`. The name `explainer` is refused. The unit cases and the gated harness that used the explainer run on the brainrot format or on the film.

**Architecture:** The ports go first. Tasks 2 and 3 move test fixtures to brainrot, and the tests pass at the base before and after. The flips follow: Task 1 changes the narration, Task 4 the validator and its row, Task 5 the default of `render.sh`. Each task ends with the unit suite and the gated suite green (one known exception: decision 1). No product file of wave `explainer-removal` changes: `transcript.py`, the Remotion project, the templates, `video.md` and `README.md` stay as they are.

**Tech Stack:** Python 3 `unittest` (stdlib), Node (`build-timeline.mjs`), bash 3.2 (`/bin/bash` of macOS), Markdown under the STE profile (`skills/ste/scripts/ste_lint.py`).

**Spec:** `docs/superpowers/specs/2026-10-05-explain-film-design.md`: §10 (the default flips, `explainer` is refused, the ports), §4.2 (the end-state `format` rule), §7.1 (`tagOf` and `format_tag` tag every format). Wave map: `docs/superpowers/waves/2026-10-05-explain-film.yaml`, wave `explainer-default` (ralph wave 10, epic `kp-s2m`). Coverage: waived by the map.

Base: 3454017974bacb45ed446a34cfde81f9472305b6

Test runs: scoped per task; full suite once, final task.

## Global Constraints

- Work on this wave's branch and worktree. Never commit to `main`, `feat/explain-brainrot` or directly to `feat/explain-film`. Never stage `.beads/`.
- A gated run (`EXPLAIN_VIDEO_E2E=1`) needs `EXPLAIN_VIDEO_WORKSPACE` set to the film branch's workspace (`/Users/valukin/karpathy-wt/film-workspace` at planning). Every gated command below starts with `test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE"`. If it prints nothing, do not render, and report it. Never render into `~/karpathy/video-workspace`. Never touch any `regression/landscape-baseline`.
- The refusal text is verbatim spec §4.2: `format must be film or brainrot`. The three tools print it as `FAIL script: format must be film or brainrot` (`build-timeline.mjs`), `narration: FAIL script <path>: format must be film or brainrot` (`narrate.py`) and `script: FAIL format must be film or brainrot` (the script stage of `render.sh`).
- Only the files named in the tasks change. Outside the map's `owns` list, only one changes: `tests/test_render_brainrot.py`, one docstring sentence (Task 3).
- `rungs/brainrot.md` passes `python3 skills/ste/scripts/ste_lint.py` with `0 errors, 0 warnings`. It does not hold the word `explainer` (`test_rung_drift.py` pins this). Its line 180 stays the line that `tests/fixtures/brainrot-limits-script.json` cites (`To force the generated loop, set`).
- Tests: `unittest`, run from `skills/explain`. Each case names, in a comment or docstring, the mutation that turns it red, as the files do now. Each new assertion is seen to fail before the change that makes it pass. A case that passes at once (a port) is checked by applying its named mutation, seeing it fail, and reverting.
- After this wave, these files do not hold the word `explainer` in any case: `video/narrate.py`, `video/build-timeline.mjs`, `video/check_budgets.py`, `video/check_render.sh`, `video/formats.json`, `scripts/render.sh`, `rungs/brainrot.md`, and the tests `test_narrate.py`, `test_narrate_sentences.py`, `test_video_timeline.py`, `test_video_timeline_brainrot.py`, `test_video_timeline_film.py`, `test_check_budgets.py`, `test_format_limits.py`, `test_render.py`, `test_render_film.py`, `test_render_parallel.py`, `test_check_render.py`, `video_e2e.py`, `test_render_brainrot.py`.
- Baseline at the base (run at planning): `python3 -B -m unittest discover -s tests` gives `Ran 737 tests`, `OK (skipped=49)`.
- Commits: `<type>: explain: <description>`, ending with the attribution line of the session.

## What the closed waves left for this one

- `kp-osb`: film speed and "no `--background`" are pinned only by gated tests. Port the always-run explainer cases of `test_render.py` (the case with no speed) to the film (Task 5).
- `kp-o7s`: the brainrot sentence "Without the key, `render.sh` makes a 16:9 video, not a short." is false after the flip. An edit above line 180 of `brainrot.md` moves the cite of the limits fixture (Task 4).
- `kp-vv0`: the FAIL and SIGTERM cases of `ParallelRenderCase` still render the explainer fixture (Task 3; the FAIL case already renders brainrot).
- `kp-sd3`: `COMPONENT_FORMATS` is hardcoded beside `formats.json` (Task 4 removes it).
- The kp-cq5 refusal: the explainer cases outside the old `owns` list (`test_video_timeline_brainrot.py`, `_film.py`, `test_narrate_sentences.py`, `test_render_film.py`, `test_check_budgets.py`, `test_format_limits.py`, `test_render_parallel.py`) are in scope here.

Left for later, by choice (no explainer case is in them): moving the film code out of `build-timeline.mjs` (kp-sd3); moving `RunHarness` and `FAKE_TSC` to `video_e2e.py` (kp-vv0); splitting `test_render.py` (kp-xdd).

## Beyond the letter of the spec

1. **Order and the known red.** Tasks 2 and 3 are ports that pass at the base. From Task 4 on, the gated render class of `tests/test_landscape_regression.py` fails: it renders `templates/video-script.json`, which is now refused. Wave `explainer-removal` deletes that harness, so this wave leaves it alone. The map's acceptance does not run it.
2. **A film with no key fails in `transcript.py` until the next wave.** `render.sh` runs `transcript.py` in its script stage. That file is the next wave's, and today it reads a script with no key as an explainer (`KeyError 'component'`, exit 2, checked at planning). So in this wave, a film script with no `format` key stops at the script stage. Task 5 proves the format read of `render.sh` with a fake `transcript.py`. The next wave must prove it with the real one.
3. **`knownFormat` is a fixed list, `["film", "brainrot"]`, not "any row of `formats.json`".** A stale `formats.json` with an `explainer` row must not make the name valid again.
4. **The `wordTimed` key goes from both rows of `formats.json`.** After the character-offset cue frame goes (spec §10), nothing reads it: brainrot always reads words files, and the film did so before. Spec §7.1 still lists `wordTimed: true` for the film row. The wave-close note records this.
5. **The sidecar keeps its `mode=sentences` line, on every clip.** Clips that earlier brainrot and film runs cached stay valid. A clip from an older whole-scene run has no mode line, so it is made again.
6. **`check_budgets.py` refuses a timeline whose `format` is not `film` or `brainrot`.** It exits 2 with one stderr line, `check_budgets.py: <path>: no usable format`, as for the other keys it needs. `build-timeline.mjs` always writes the key.
7. **`render.sh` gets no guard of its own.** Its script stage runs `--check`, and `--check` refuses the name. After that, every branch of `render.sh` is film or brainrot.
8. **The gated `CheckRenderCase` renders brainrot** through `render_brainrot("generated")` of `test_render_brainrot.py`. That render is cached for each process, so the run is shared when both modules run together. The motion case moves to the `checks` scene of the brainrot template (Task 3).
9. **`video_e2e.TEMPLATE` stays until Task 4.** The case that reads it last is rewritten there.
10. **A ported case that only repeats an existing case is cut.** The rule: an existing case of the same file family makes the same mutation and asserts the same FAIL lines. The other ports stay.
11. **kp-5a2** (sentence synthesis for the explainer) is closed as superseded, after the acceptance of Task 5.

## Review Focus

1. A brainrot author drops `"format": "brainrot"`. The script is now validated as a film, and each component scene fails. Task 4: `test_a_brainrot_script_without_the_key_is_a_film`. `brainrot.md` says so (Task 4, Step 6).
2. An old output directory has `"format": "explainer"` and is rendered again. The run must stop in the script stage, before any synthesis. Task 4: `StageOneCase.test_an_explainer_script_stops_at_the_script_stage`. Task 1: `test_unknown_format_exit_2`.
3. An audio directory holds whole-scene clips from an earlier run. A film run must make them again, not reuse them without words. Task 1: `test_a_whole_scene_clip_is_remade`.
4. A stale checkout's `formats.json` still has an `explainer` row. Task 4: `test_an_explainer_row_does_not_make_a_format`.
5. A timeline from an older run (`"format": "explainer"`, or no key) is given to `check_budgets.py`. It must not be judged with untagged limits. Task 4: `test_a_timeline_of_another_format_exits_2`.

---

### Task 1: narration has one mode

**Files:**
- Modify: `skills/explain/video/narrate.py` (docstring 14-20; `FORMATS` at 53; `sidecar_text`, `sidecar_matches` at 103-114; `narrate` at 290-345; `load_script` at 354-364; `main` at 394-407)
- Modify: `skills/explain/tests/test_narrate.py` (`TEMPLATE` at 19; the sidecar assertions)
- Modify: `skills/explain/tests/test_narrate_sentences.py` (cases at 183-233 and 342-357)

**Interfaces:**
- Consumes: nothing new.
- Produces (narrate.py), declarations only:

  ```python
  NARRATED_FORMATS = ("film", "brainrot")
  def sidecar_text(engine, text) -> str
  def sidecar_matches(sidecar, engine, text) -> bool
  def narrate(scenes, engine, audio_dir) -> dict
  def load_script(path) -> list
  ```
  `NARRATE_PY`, `ONE`, `TWO`, `NarrateCase` and `scene` of `test_narrate.py` keep their names. Five other test modules import them.

- [ ] **Step 1: Write the failing tests** in `test_narrate_sentences.py`:
  - `test_a_script_without_a_format_is_narrated_in_sentences`: replaces `test_explainer_writes_no_words_json`. The brainrot helper's script with its `format` key deleted gives exit 0, a `one.say.words.json`, and a sidecar whose fourth line is `mode=sentences`. Red: a script with no key is narrated whole (no words file), or is refused.
  - `test_a_whole_scene_clip_is_remade`: replaces `test_mode_change_resynthesizes`. Plant `one.say.wav` (from a first run) and the sidecar `engine=say\nvoice=say-default\nspeed=1.0\n` + `ONE`, with no mode line, and delete the words file. A run prints `(synthesized)` for `one` and writes the words file and the mode line. Red: the reuse check ignores the mode line.
  - `test_unknown_format_exit_2`: the values get `"explainer"`, and the expected line becomes `narration: FAIL script <path>: format must be film or brainrot`. The rest stays (exit 2, no audio directory). Its docstring says that an unknown format is narrated as a film, not as an explainer.
  - Cut `test_explainer_run_removes_a_words_json_left_by_a_brainrot_run`: it tests scene mode only. Reword the docstring of `test_film_is_narrated_in_sentences` so that it does not name a whole-scene mode.

  In `test_narrate.py`: `TEMPLATE` becomes `templates/brainrot-script.json` (spec §10: the ported scripts get `"format": "brainrot"`). Each sidecar that a case asserts gets `mode=sentences\n` after its speed line. A case that reads the text given to the engine now gets one sentence at a time. `ONE` and `TWO` are one sentence each, so most logs do not change. All 28 cases stay. None tests scene mode alone.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_narrate tests.test_narrate_sentences`
  Expected: `FAILED`. The case with no key finds no words file. The `explainer` subtest of `test_unknown_format_exit_2` exits 0. The `test_narrate.py` sidecar cases fail on their missing mode line. `test_a_whole_scene_clip_is_remade` passes at the base (Step 5 checks it).

- [ ] **Step 3: Implement.** In `narrate.py`, `load_script` reads `format`. When the key is absent it is `"film"`. A value that is not in `NARRATED_FORMATS` (`"explainer"`, `""`, `"Brainrot"`, a number, `null`, a list) prints the line above and exits 2 before any clip is made. Every scene goes through `synth_sentences`. Every sidecar has the mode line, and a reused clip needs a matching sidecar and a words file that matches. The whole-scene path goes, and so does the removal of a words file beside a reused whole clip. The docstring describes one mode and does not name the explainer.

- [ ] **Step 4: Run the tests.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_narrate tests.test_narrate_sentences tests.test_brainrot_contract tests.test_film_contract tests.test_film_example`
  Expected: `OK`.

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/video/narrate.py skills/explain/tests/test_narrate.py skills/explain/tests/test_narrate_sentences.py
  git commit -m "feat: explain: narrate.py narrates every script by sentence; a script without a format is a film"
  ```

- [ ] **Step 6: Mutation check, after the commit.** Make `sidecar_matches` compare the sidecar without its mode line: `test_a_whole_scene_clip_is_remade` fails. Revert with `git checkout -- skills/explain/video/narrate.py`. `git status --short` prints nothing.

---

### Task 2: the component cases of the validator and the script stage run on brainrot

Tests only. Every case passes at the base before and after.

**Files:**
- Modify: `skills/explain/tests/test_video_timeline.py` (`TEMPLATE` at 14; `base_script` at 25; `VideoCase` at 93-145; `TestCheck`; `TestBuild` at 514-611)
- Modify: `skills/explain/tests/test_video_timeline_brainrot.py` (`words_for` and `BrainrotBuildCase` at 24-58; cases at 268-274 and 443-446)
- Modify: `skills/explain/tests/test_video_timeline_film.py` (case at 250-257)
- Modify: `skills/explain/tests/test_render.py` (`StageOneCase` at 56-180)

**Interfaces:**
- Consumes: `BRAINROT_TEMPLATE` of `test_render.py` (line 36).
- Produces, in `test_video_timeline.py`, for Task 4 and for the modules that import them:

  ```python
  def base_script() -> dict            # now holds "format": "brainrot"
  def words_for(narration: str, seconds_per_word: float = 0.3, pause: float = 0.15) -> dict
  class VideoCase:
      def write_words(self, scene_id: str, engine: str, words_json: dict) -> str
      def build_brainrot(self, script: dict, seconds: dict, engine: str = "say") -> tuple
  ```
  `words_for`, `write_words` and `build_brainrot` move unchanged from `test_video_timeline_brainrot.py`. That module imports `words_for` back, so `from test_video_timeline_brainrot import words_for` (`test_video_timeline_film.py`) still works. `BrainrotBuildCase` keeps `two_scene_brainrot` and inherits the rest. `brainrot_script()` stays.

- [ ] **Step 1: Port `test_video_timeline.py`.**
  - `base_script()` gets `"format": "brainrot"` (its fixture already fits every brainrot limit). Its docstring says so.
  - In `TestCheck`, each FAIL line that names a limit ends with `, brainrot` inside the parentheses. A limit in a fixture or a case name takes the brainrot row's value: bullet text 28, scenes 3 to 6, code columns 40. Rename the cases whose names hold the old value (`..._36_chars_...`, `..._3_to_8_...`, `..._72_columns_...`).
  - In `TestBuild`, each build goes through `build_brainrot`, with a words file for each scene. Expected frames use lead 6 and tail 12.
  - Cut `test_cue_frame_is_proportional`: it pins the character-offset cue frame, which only the explainer has (spec §10). Cut `test_template_script_passes_check` and `TEMPLATE`: they validate the explainer template. `test_brainrot_template_checks` (`test_render.py`) and `test_film_example.py` check the two live templates.
  - Apply decision 10 against `test_video_timeline_brainrot.py`. Compare at least `bullets` over the limit, code columns, code lines, narration words, the 15-frame cue gap, lead and tail frames, and the top-level values. Cut a port only when both hold: the same mutation and the same FAIL lines (or timeline values).
  - The module docstring says that its scripts are brainrot scripts.

- [ ] **Step 2: Port the cases that relied on a keyless `base_script()`.** In `test_video_timeline_brainrot.py`, cut `test_explainer_scenes_have_no_captions` and `test_explainer_build_reads_no_words_file`. Both pinned the explainer build, which spec §10 removes, through `base_script()` with no key. In `test_video_timeline_film.py`, cut `test_explainer_refuses_the_film_keys`. Now that `base_script()` is brainrot, it repeats `test_brainrot_refuses_the_film_keys`. The cases that set `"format": "explainer"` themselves stay until Task 4.

- [ ] **Step 3: Port `StageOneCase`.** `write_script` defaults to `template=BRAINROT_TEMPLATE`. `test_bad_cue_fails_at_script_stage` sets the cue of `bullets[0]` of scene `checks` to `looks for remote links`. That phrase is in the scene's narration, but not at a sentence start. The case asserts `cue "looks for remote links" is not at a sentence start` in the one stage line. `test_prose_error_fails_at_script_stage` appends `It doesn't skip a check.` to the narration of scene 0 (its cue stays first) and keeps its three assertions. `test_stale_artifacts_removed_once_the_script_stage_passes` expects `script: ok (4 scenes)`. No `StageOneCase` reads `TEMPLATE` any more. The import stays for `BrainrotRouteCase` until Task 4.

- [ ] **Step 4: Run the ports.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline tests.test_video_timeline_brainrot tests.test_video_timeline_film tests.test_brainrot_contract tests.test_film_contract tests.test_format_limits tests.test_short_still tests.test_render`
  Expected: `OK`; the gated cases are skipped.

- [ ] **Step 5: Mutation checks** (the ports pass at once). In a scratch edit of `build-timeline.mjs`, make `tagOf` return `""`: the ported limit cases of `TestCheck` fail. In `formats.json`, set brainrot `leadFrames` to 7: a ported `TestBuild` frame case fails. In `StageOneCase`, drop the `--check` call of `stage_script`: `test_bad_cue_fails_at_script_stage` fails. Revert each. `git status --short` lists only the four test files.

- [ ] **Step 6: Commit.**

  ```bash
  git add skills/explain/tests/test_video_timeline.py skills/explain/tests/test_video_timeline_brainrot.py skills/explain/tests/test_video_timeline_film.py skills/explain/tests/test_render.py
  git commit -m "test: explain: the component cases of the validator and the script stage run on the brainrot format"
  ```

---

### Task 3: the gated harness renders brainrot and film only

Tests only, plus one comment of `check_render.sh`. Every case passes at the base.

**Files:**
- Modify: `skills/explain/tests/video_e2e.py` (docstring; `FIXTURE_COMPONENTS`, `_cache`, `fixture_script`, `render_fixture` and their imports go)
- Modify: `skills/explain/tests/test_render.py` (import at 33-34; `ORDER` and `SayFixtureCase` at 902-950; module docstring, the sentence about the end-to-end class)
- Modify: `skills/explain/tests/test_check_render.py` (import at 23; `StillFramesCase.test_lead_15_scene_still_unchanged` at 239-245; `CheckRenderCase` at 309-394)
- Modify: `skills/explain/tests/test_render_parallel.py` (import at 39; docstring 12-15; `test_no_run_directory_is_left_after_sigterm` at 279)
- Modify: `skills/explain/tests/test_render_brainrot.py` (docstring, the sentence at 13-14 only)
- Modify: `skills/explain/video/check_render.sh` (the `FADE_FRAMES` comment at 38-40)

**Interfaces:**
- Consumes: `render_brainrot(kind: str, script=BRAINROT_TEMPLATE) -> tuple` of `test_render_brainrot.py`, which returns `(out: Path, run: CompletedProcess)` and is cached for each process; `brainrot_script()` of `test_render_parallel.py`.
- Produces: `video_e2e.py` exports `E2E`, `E2E_REASON`, `EXPLAIN`, `RENDER_SH`, `RENDER_TIMEOUT`, `BACKGROUND_SETTINGS`, `workspace()`, `render_env()` and, until Task 4, `TEMPLATE`. These names stay importable (spec §9.2).

- [ ] **Step 1: Port the cases.**
  - `CheckRenderCase.setUpClass`: `cls.out, cls.result = render_brainrot("generated")`.
  - `test_container_size_mismatch_fails`: the copy of the timeline names width 1280 and height 720. The expected stdout is `container: FAIL size 1080x1920, expected 1280x720\n`. The comment names the brainrot render.
  - `test_still_at_cue_plus_15_shows_motion`: scene `checks` (`bullets-appear`, scene 2). Compare `still-02-checks-2.png` with `still-02-checks-3.png` inside the row band of the third bullet, x 48 to 1032 (the panel's content box). `differing_pixels(a, b, x0, x1, y0, y1)` must count more than 500. Write the band's y bounds as constants. Derive them from the bullet layout of `src/layout.tsx` at the 1080x1920 canvas, and put that derivation in a comment, as the base does for the landscape box. The build keeps cues at least 15 frames apart, so at cue 2 + 15 the third bullet has not started. The case must fail when `STILL_AFTER_CUE` of `check_render.sh` is 0 (Step 3).
  - `test_duration_mismatch_is_container_fail`, `test_shifted_speech_is_sync_fail` and `test_stills_named_per_scene_and_cue_and_review_cleared`: unchanged assertions on the brainrot render.
  - `test_lead_15_scene_still_unchanged` becomes `test_a_lead_longer_than_the_fade_places_the_still_at_the_lead`. It keeps the same timeline and lines. Its comment states the rule `from + max(leadFrames, FADE_FRAMES)` and names no format.
  - The `FADE_FRAMES` comment of `check_render.sh`: a lead longer than the fade puts the scene still at the lead. It names no format.
  - `test_no_run_directory_is_left_after_sigterm`: `Render(self.addCleanup, brainrot_script())`. The empty clip folder of `Render` gives the generated background. The rest is unchanged. The docstring names a brainrot render.
  - `test_render.py`: `ORDER` and `SayFixtureCase` go. That is the explainer's nine-line render (spec §10). `FilmRenderCase` and `BrainrotRenderCase` hold the eleven and ten lines. Drop `render_fixture` from the import.
  - `test_render_brainrot.py`: the sentence "The explainer E2E and the landscape regression run after this module ..." goes.
  - `video_e2e.py`: its docstring describes the shared helpers of the gated renders.

- [ ] **Step 2: Run the unit side.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render tests.test_check_render tests.test_render_parallel tests.test_render_brainrot`
  Expected: `OK`; the gated cases are skipped.

- [ ] **Step 3: Run the gated side.**

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_brainrot tests.test_check_render tests.test_render_parallel`
  Expected: the workspace path, then `OK` with no skip.

  The mutation of the motion case comes after the commit (Step 5): `check_render.sh` is a file of this task.

- [ ] **Step 4: Commit.**

  ```bash
  git add skills/explain/tests/video_e2e.py skills/explain/tests/test_render.py skills/explain/tests/test_check_render.py skills/explain/tests/test_render_parallel.py skills/explain/tests/test_render_brainrot.py skills/explain/video/check_render.sh
  git commit -m "test: explain: the gated harness renders brainrot and film only"
  ```

- [ ] **Step 5: Mutation check, after the commit.** Set `STILL_AFTER_CUE=0` in `check_render.sh`. Run `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_check_render.CheckRenderCase.test_still_at_cue_plus_15_shows_motion`: `FAILED`. Revert with `git checkout -- skills/explain/video/check_render.sh`. `git status --short` and `ls "$EXPLAIN_VIDEO_WORKSPACE/runs"` print nothing.

---

### Task 4: the validator refuses the explainer; a script without a format is a film

**Files:**
- Modify: `skills/explain/video/build-timeline.mjs` (header 1-125; `loadFormats` 128-148; format helpers 242-255; `checkHeader` 571-590; `validate` 600-610; `captionChunks` 716-720; `buildScenes` 762-826; `main` 995-1002)
- Modify: `skills/explain/video/formats.json` (the `explainer` row; `wordTimed` of both rows)
- Modify: `skills/explain/video/check_budgets.py` (docstring; `format_tag`; `verdict`)
- Modify: `skills/explain/rungs/brainrot.md` (item 2 of section 3, lines 44-45)
- Modify: `skills/explain/tests/test_video_timeline_brainrot.py`, `test_video_timeline_film.py`, `test_check_budgets.py`, `test_format_limits.py`, `test_render.py` (`StageOneCase`, `BrainrotRouteCase`), `video_e2e.py` (`TEMPLATE` goes)

**Interfaces:**
- Consumes: `base_script()`, `words_for`, `VideoCase.build_brainrot` (Task 2); `film_script()` of `test_video_timeline_film.py`.
- Produces, declarations only:

  ```js
  const FORMAT_NAMES = ["film", "brainrot"];
  const formatOf = (script) => /* "film" when the key is absent, else the raw value */;
  const knownFormat = (format) => /* boolean: a string in FORMAT_NAMES */;
  const tagOf = (format) => /* ", brainrot" for brainrot, ", film" for any other value */;
  const SHAPES = shapesFor(FORMATS.brainrot);
  ```
  ```python
  def format_tag(timeline) -> str          # ", <format>" of a film or brainrot timeline
  ```
  `formats.json` has exactly two rows, `film` and `brainrot`, and neither has `wordTimed`.

Behavior, `--check`: a script with no key is validated as a film (film rules, film row, `, film` tags, `sources` allowed). `"explainer"` or any other value gives `FAIL script: format must be film or brainrot`, and the rest of the script is validated as a film. So each component scene adds `FAIL scene <id>: a film scene has no component or props`. Brainrot is unchanged. `loadFormats` without a film row or a brainrot row prints `FAIL script: cannot read formats.json: expected an object with a film and a brainrot row` and exits 1.
Behavior, build mode: a script with no key (or JSON that is not an object) builds as a film. Any other unknown value gives `FAIL script: format must be film or brainrot`, exit 1, and no file. A brainrot build reads the words file of every scene. Each cue frame is its sentence's start. The character-offset formula, the `wordTimed` switch, `COMPONENT_FORMATS`, `limitsFor`, `shapesOf` and the `null` caption cap go.
Behavior, `--types`: a script with no key is a film and gets its names. `brainrot`, `explainer`, other values and non-objects give `FAIL script: --types needs a film script`.
Behavior, `check_budgets.py`: film and brainrot timelines as today. A `format` that is absent, `"explainer"`, `""` or `7` gives exit 2, no stdout, and one stderr line `check_budgets.py: <path>: no usable format`. The format is checked before the numbers.

- [ ] **Step 1: Write the failing tests.**
  - `test_video_timeline_brainrot.py`:
    - `test_explicit_explainer_format_passes` becomes `test_explainer_format_is_refused`. The format line, then the three `a film scene has no component or props` lines (intro, flow, code).
    - New `test_a_brainrot_script_without_the_key_is_a_film`: `base_script()` without `format` gives exactly the three component lines.
    - `test_unknown_format_fails` and `test_invalid_format_values_fail_with_the_format_line` (values plus `"explainer"`): the new format line and the three component lines.
    - `test_build_mode_unknown_format_fails`: the new line, with an `"explainer"` subtest.
    - Cut `test_explainer_lines_carry_no_tag_when_format_is_explicit`, `test_unknown_format_with_nine_scenes_keeps_the_untagged_explainer_count_line` and `test_explainer_limits_unchanged_under_explicit_format`: they test the untagged explainer lines (spec §10).
    - Each docstring that names the explainer's values names "another row" in their place.
  - `test_video_timeline_film.py`:
    - `test_slides_format_is_refused`: the format line is the only line (`sources` is now allowed).
    - New `test_an_invalid_format_is_validated_as_a_film`: `film_script()` with `"vertical"` and 31 scenes (renamed copies) gives the format line, then `FAIL script: 31 scenes (needs 3 to 30, film)`.
    - New `test_a_script_without_the_key_is_a_film`: `film_script()` without `format` passes `--check` (exit 0, no output). Its build writes `"format": "film"` and `checkFrames`.
    - New `test_an_explainer_row_does_not_make_a_format`: a copy of the tool, as `test_formats_file_without_the_film_row_fails_cleanly` makes it, beside the real two rows plus `"explainer"` (a copy of the brainrot row). A script with `"format": "explainer"` still gets the format line.
    - `test_formats_file_without_the_film_row_fails_cleanly`: the cause text of the behavior above.
    - `test_types_refuses_a_script_that_is_not_a_film`: the `"explainer by default"` and `"no format key"` subtests go, and an `"explainer"` subtest comes in.
    - New `test_types_takes_a_script_without_the_key`: the same five lines as for `"format": "film"`.
    - `FILM_ROW` loses `wordTimed`. Each docstring that names the explainer is reworded.
  - `test_check_budgets.py`:
    - `write_timeline` defaults to `fmt="film"`. `fmt=None` still writes no key.
    - Cut `test_explainer_scene_at_60_ok_and_over_fails` and `test_explainer_total_text_unchanged`: the film and brainrot cases pin the same rules with their tags.
    - New `test_a_timeline_of_another_format_exits_2`: the four values of the behavior above.
    - Neither the docstring nor a comment names the explainer. The comment of `test_brainrot_scene_30_ok_31_fails` names "a fixed constant" in place of "the explainer constants".
  - `test_format_limits.py`:
    - New `test_formats_has_the_film_and_brainrot_rows_only`: `sorted(load_formats()) == ["brainrot", "film"]`.
    - `test_formats_file_without_both_rows_fails_cleanly`: its texts become `{"film": {}}`, `{"brainrot": {}}` and `{"film": {}, "brainrot": 7}`, with `null` and `[]`.
    - The docstrings of the module and of `fill` do not name the explainer.
  - `test_render.py`:
    - New `StageOneCase.test_an_explainer_script_stops_at_the_script_stage`: the brainrot template with `"format": "explainer"` exits 1. Its stage lines are exactly `["script: FAIL format must be film or brainrot"]`, and `out/audio` does not exist.
    - `BrainrotRouteCase.test_stage_script_reads_the_format_from_the_script` keeps only its brainrot subcase (Task 5 adds the film). Drop `TEMPLATE` from the import. In `video_e2e.py`, `TEMPLATE` goes.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_brainrot tests.test_video_timeline_film tests.test_check_budgets tests.test_format_limits tests.test_render`
  Expected: `FAILED`. Each new or changed case fails on the base's format rules.

- [ ] **Step 3: Implement `build-timeline.mjs` and `formats.json`** by the behavior above. The header comment describes the two formats, the default and the refusal, and does not name the explainer. Its `--types` paragraph says that a film script has `"format": "film"` or no key.

- [ ] **Step 4: Implement `check_budgets.py`** by the behavior above. `format_tag` returns `", %s" % format`. The docstring lists `format` among the keys whose absence is exit 2, and names the limits of the two formats.

- [ ] **Step 5: Run the tests.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline tests.test_video_timeline_brainrot tests.test_video_timeline_film tests.test_film_contract tests.test_brainrot_contract tests.test_check_budgets tests.test_format_limits tests.test_render tests.test_render_film tests.test_film_example tests.test_short_logic tests.test_short_still tests.test_rung_drift`
  Expected: `OK`; the gated cases are skipped.

- [ ] **Step 6: Reword item 2 of section 3 of `brainrot.md`.** Lines 44-45 become two lines, so that line 180 does not move:

  ```
  2. Keep `"format": "brainrot"` as a top-level key of `script.json`. Without the key, the script is
     a film, and the `script` stage refuses each scene that has a component.
  ```

  Run: `python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/brainrot.md && sed -n 180p skills/explain/rungs/brainrot.md`
  Expected: `0 errors, 0 warnings`, then the line that starts `- To force the generated loop, set`.

- [ ] **Step 7: Commit.**

  ```bash
  git add skills/explain/video/build-timeline.mjs skills/explain/video/formats.json skills/explain/video/check_budgets.py skills/explain/rungs/brainrot.md skills/explain/tests/test_video_timeline_brainrot.py skills/explain/tests/test_video_timeline_film.py skills/explain/tests/test_check_budgets.py skills/explain/tests/test_format_limits.py skills/explain/tests/test_render.py skills/explain/tests/video_e2e.py
  git commit -m "feat: explain: the validator refuses the explainer and validates a script without a format as a film"
  ```

- [ ] **Step 8: Mutation check, after the commit.** Make `knownFormat` read `has(FORMATS, format)` again: `test_an_explainer_row_does_not_make_a_format` fails. Revert with `git checkout -- skills/explain/video/build-timeline.mjs`. `git status --short` prints nothing.

---

### Task 5: `render.sh` reads a script without a format as a film; the wave's acceptance

**Files:**
- Modify: `skills/explain/scripts/render.sh` (header 12-14, 22-23, 35-38, 54-55; `BRAINROT_SPEED` comment at 155; `fmt` at 210; `stage_script` at 306-309)
- Modify: `skills/explain/tests/test_render.py` (module docstring; comment at 41-45; `StageFunctionCase` cases at 264-280 and 397-406; `RunHarness.start` at 537; `RunDirectoryCase` at 647; `BrainrotRouteCase.stage_script_format` and its case)
- Modify: `skills/explain/tests/test_render_film.py` (comments at 139, 246, 374, 685-686, 842; subtests at 254, 378, 550, 697; `SceneRunCase.start` at 663)

**Interfaces:**
- Consumes: the always-run helpers of `test_render.py` (`render_functions`, `RunHarness`, `RUN_FAKES`, `stage_lines`).
- Produces: `RunHarness.start(self, fmt="brainrot", **env)`; `SceneRunCase.start(self, fmt="brainrot", **env)`; `BrainrotRouteCase.stage_script_format(self, script: dict, fake_page: bool = False) -> subprocess.CompletedProcess`.

- [ ] **Step 1: Write the failing tests.**
  - In `StageFunctionCase`, the three explainer cases become film cases (kp-osb):
    - `test_film_narration_has_no_speed`: `stage_narration` with `film` calls `narrate.sh` with exactly `<out>/script.json <out>/audio --engine say`. Red: `--speed` for every format.
    - `test_film_runs_no_background_stage`: `stage_background` with `film` prints nothing and does not call the picker. Red: the picker runs for every format.
    - `test_film_transcript_has_no_background_flag`: `stage_transcript` with `film`, for both background subtests, calls `transcript.py` without `--background`. Red: `--background` for every format.
  - `stage_script_format` takes a script dict and returns the run. Its shell text starts with `fmt=unset`, so that only `stage_script` can set it. With `fake_page`, `video` is a temp directory with a link to the real `build-timeline.mjs` (Node follows the link to the real `formats.json`) and an empty `transcript.py`, and `scripts` is a temp directory whose `verify.sh` exits 0 (decision 2).
  - `test_stage_script_reads_the_format_from_the_script`: the brainrot template (root `EXPLAIN`) gives exit 0, `script: ok (4 scenes)` and `fmt=brainrot`, with the real tools. `templates/film-script.json` with its `format` key deleted (root: the repository, `EXPLAIN.parent.parent`), with `fake_page`, gives exit 0, `script: ok (8 scenes)` and `fmt=film`. Red: the format read of `stage_script` keeps another default.
  - `RunHarness.start` and `SceneRunCase.start` default to `brainrot`. The `explainer` entry of the fail case of `RunDirectoryCase` (line 647) becomes `brainrot`. A brainrot run under `RUN_FAKES` renders composition `Explain`, and its run directory's `public` holds only `audio` (the fake picker stages nothing). So the assertions stay.
  - `test_render_film.py`: the composition table of `test_a_film_renders_composition_film` is `(film, Film)` and `(brainrot, Explain)`. The other-format loops at 378, 550 and 697 run `brainrot` only. The comments name brainrot where they named the explainer.
  - The module docstring of `test_render.py`: a film run has eleven stages, a brainrot run ten. The comment of `test_stage_script_reads_the_format_from_the_script` names the film default, not explainer speed.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render tests.test_render_film`
  Expected: `FAILED`. Only the subcase with no key fails (`fmt=explainer`). The three film cases of `StageFunctionCase` pass at once (Step 6 checks them).

- [ ] **Step 3: Implement `render.sh`.** `fmt` starts as `film`. `stage_script` reads `.get("format", "film")`. Its comment says that `--check` has accepted the format, so it is film or brainrot. The header says:
  - the format is `film` when the key is absent, or `brainrot`;
  - any other value stops the script stage with `script: FAIL format must be film or brainrot`;
  - a film run has eleven stages, a brainrot run ten;
  - the timeline limits are film 30 s and 150 s, brainrot 30 s and 90 s;
  - the render stage renders composition `Film` for a film and `Explain` for brainrot.

  The `BRAINROT_SPEED` comment: a film keeps the default speed of `narrate.sh`. No line names the explainer.

- [ ] **Step 4: Run the tests.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render tests.test_render_film`
  Expected: `OK`; the gated cases are skipped.

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/scripts/render.sh skills/explain/tests/test_render.py skills/explain/tests/test_render_film.py
  git commit -m "feat: explain: render.sh reads a script without a format as a film"
  ```

- [ ] **Step 6: Mutation checks, after the commit.** Each check is one edit of `render.sh`. Run `cd skills/explain && python3 -B -m unittest tests.test_render.StageFunctionCase` after each edit, then revert it with `git checkout -- skills/explain/scripts/render.sh`:
  - Drop the `brainrot` test of the speed arguments, so that every format gets `--speed 1.2`: `test_film_narration_has_no_speed` fails.
  - Drop the first line of `stage_background`: `test_film_runs_no_background_stage` fails.
  - Make `stage_transcript` pass `--background` for every format: `test_film_transcript_has_no_background_flag` fails.

  `git status --short` prints nothing at the end.

- [ ] **Step 7: Run the full unit suite, once.**

  Run: `cd skills/explain && python3 -B -m unittest discover -s tests`
  Expected: `OK (skipped=45)`, with no failure and no error: the base's 49, less the four gated cases of `SayFixtureCase` (Task 3). The test count changes with the cuts and the new cases of Tasks 1 to 5.

- [ ] **Step 8: Run the map's acceptance, then the other gated modules this wave changed.**

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film tests.test_render_brainrot`
  Expected: the workspace path, then `OK` with no skip. The film run prints eleven `ok` lines (`FilmRenderCase`) and brainrot ten (`BrainrotRenderCase`, the limits script among them).

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render tests.test_check_render tests.test_render_parallel tests.test_short_still`
  Expected: the workspace path, then `OK` with no skip.

- [ ] **Step 9: Check the tree.**
  - The grep of the Global Constraints, `git grep -n -i explainer -- <the files listed there>`, prints nothing.
  - `git grep -l 'video-script.json' -- skills/explain/tests` prints exactly `skills/explain/tests/capture_landscape_baseline.sh`, `skills/explain/tests/test_rung_drift.py` and `skills/explain/tests/test_transcript.py`. These are next wave's.
  - `git diff --stat 3454017974bacb45ed446a34cfde81f9472305b6 -- . ':!docs'` lists only the files of the five tasks.
  - `git status --short` prints nothing. `ls "$EXPLAIN_VIDEO_WORKSPACE/runs"` prints nothing.

- [ ] **Step 10: Close kp-5a2.** Run `br close kp-5a2 --reason "Superseded by the explain-film removal (spec 2026-10-05-explain-film-design section 10): the explainer format is refused (wave explainer-default, kp-s2m); narrate.py has one narration mode, by sentence."`. Then `br show kp-5a2` shows it closed.

## Wave close

The map's `done_when` is met as follows:
- `narrate.py` has one narration mode: Task 1 (`test_a_script_without_a_format_is_narrated_in_sentences`, `test_a_whole_scene_clip_is_remade`).
- `formats.json` has no `explainer` row, and `build-timeline.mjs`, `check_budgets.py` and `render.sh` refuse the name: `test_formats_has_the_film_and_brainrot_rows_only`, `test_explainer_format_is_refused`, `test_a_timeline_of_another_format_exits_2` and `StageOneCase.test_an_explainer_script_stops_at_the_script_stage` (Task 4).
- No test renders or validates an explainer script, except the landscape harness that the next wave deletes (decision 1): Tasks 2 to 4, and the grep of Task 5 Step 9.
- The unit suites pass, and the film and brainrot end-to-end tests pass with eleven and ten lines: Task 5 Steps 7 and 8.
- kp-5a2 is closed as superseded: Task 5 Step 10.

Inputs for wave `explainer-removal`:
- `transcript.py` still reads a script with no key as an explainer (`KeyError 'component'`). So a film with no `format` key stops in the script stage of `render.sh`. `test_render.py` proves the format read with a fake `transcript.py`. Prove it with the real one when `transcript.py` changes. Until the template is renamed, `rungs/video.md` and `templates/film-script.json` keep `"format": "film"`.
- `templates/video-script.json` (the old explainer template) fails `--check` from Task 4 on. `tests/test_transcript.py` (its `TEMPLATE`) and `capture_landscape_baseline.sh` still read it. `test_landscape_regression.py`'s gated render class fails from Task 4 on. Delete the film workspace's `regression/landscape-baseline` with the harness, and not the shared one.
- Spec §7.1 lists `wordTimed: true` for the film row. This wave removed the key (decision 4), so fold that into the spec.
- Still named `explainer` in files this wave did not own: `transcript.py`, `src/Explain.tsx`, `Root.tsx`, `types.ts`, `box.ts`, `templates/video.html`, `test_scene_geometry.py`, `test_transcript.py`, `test_rung_drift.py` (comments).
