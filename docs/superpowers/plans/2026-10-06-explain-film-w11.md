# Explain film — wave `explainer-removal` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The transcript reads a script without a format as a film, the Remotion project and the tests lose the landscape layout and its regression harness, the film template is `templates/video-script.json`, and no file under `skills/` names the removed format. The four conditions of spec §10 hold.

**Architecture:** Four tasks. Task 1 changes the last tool that still reads a script with no key as the old format (`transcript.py`) and moves the old template out of `templates/` as a test fixture. Task 2 removes the landscape branch of the Remotion project and the landscape harness. Task 3 gives the film template the freed name. Task 4 rewrites the refusal guards of the tests so that the grep of spec §10 prints nothing, and runs the acceptance. Every task boundary keeps the unit suite green.

**Tech Stack:** Python 3 `unittest` (stdlib), Node (`build-timeline.mjs`, `.ts` modules run by Node), TypeScript and React under the pinned Remotion 4.0.532 (type-checked by the workspace's `tsc`), bash 3.2, Markdown under the STE profile (`skills/ste/scripts/ste_lint.py`).

**Spec:** `docs/superpowers/specs/2026-10-05-explain-film-design.md`: §10 (removal, ports, done-when), §5.3 (the template's name; the old template stays as a brainrot-format test fixture), §4.2 (end-state `format` rule), §7.1 (the film row). Wave map: `docs/superpowers/waves/2026-10-05-explain-film.yaml`, wave `explainer-removal` (ralph wave 11, epic `kp-5s0`). Coverage: waived by the map.

Base: e011103198d82dc0d583c1eb0b4f80798a35554e

Test runs: scoped per task; full suite once, final task.

## Global Constraints

- Work on this wave's branch and worktree (`explain-film/wave-11`). Never commit to `main`, `feat/explain-brainrot` or directly to `feat/explain-film`. Never stage `.beads/`.
- A gated run (`EXPLAIN_VIDEO_E2E=1`) needs `EXPLAIN_VIDEO_WORKSPACE` set to the film branch's workspace (`/Users/valukin/karpathy-wt/film-workspace` at planning). Every gated command below starts with `test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE"`. If it prints nothing, do not render, and report it. Never render into `~/karpathy/video-workspace`. Never write under `~/karpathy/video-workspace/regression`: other sessions use that baseline.
- The done-when of spec §10, verbatim: `git grep -n -i explainer -- skills/ README.md` prints nothing; `git grep -n "LANDSCAPE_BOX\|test_landscape_regression\|capture_landscape_baseline" -- skills/` prints nothing; `narrate.py` has one narration mode; the unit suites pass, and so do the film and brainrot end-to-end tests (eleven and ten `ok` lines).
- Only the files named in the tasks change. Outside the map's `owns` list: `tests/test_render.py` (Tasks 1, 3, 4), `tests/test_render_film.py` (Task 3, one docstring line), `tests/test_png_diff.py` (Task 2), `video/src/sceneBody.tsx`, `video/src/kit/palette.ts` and `video/src/FilmStage.tsx` (Task 2, comments only), the guard cases of five test files (Task 4), and one line of the spec (Task 4).
- `rungs/video.md` passes `python3 skills/ste/scripts/ste_lint.py` with `0 errors, 0 warnings`. `rungs/brainrot.md` does not change, so the cite line of `tests/fixtures/brainrot-limits-script.json` (line 180) stays.
- Tests: `unittest`, run from `skills/explain`. Each case names, in a comment or docstring, the mutation that turns it red, as the files do now. Each new assertion is seen to fail before the change that makes it pass. A case that passes at once (a port) is checked by applying its named mutation, seeing it fail, and reverting.
- Baseline at the base (run at planning, with `EXPLAIN_VIDEO_WORKSPACE` set): `cd skills/explain && python3 -B -m unittest discover -s tests` gives `Ran 727 tests`, `OK (skipped=45)`.
- Commits: `<type>: explain: <description>`, ending with the attribution line of the session.

## What the closed waves left for this one

- `kp-s2m` (wave 10): the grep of spec §10 hits 12 refusal-guard lines in five test files; decide between an exemption and a rewrite (decision 1). `transcript.py` reads a script with no key as the old format, so `render.sh`'s keyless-film read is proven only with a fake `transcript.py`: prove it with the real one (Task 1). `rungs/video.md` line 38 is false once `transcript.py` changes (Task 1). Spec §7.1 still lists `wordTimed: true` for the film row (Task 4). The gated class of `test_landscape_regression.py` is red since wave 10; delete it with the film workspace's baseline (Task 2).
- `kp-o7s`: an edit of `brainrot.md` above line 180 moves the cite line of the limits fixture. This wave does not edit `brainrot.md`.
- `kp-xdd`: the header of `capture_landscape_baseline.sh` is stale; the file goes (Task 2).
- The kp-cq5 refusal: the old template has the only diagram scene among the scripts that `test_transcript.py` can read; spec §5.3 keeps it as a brainrot-format fixture (decision 3).

Left for later, by choice (no part of spec §10): splitting `test_render.py` and moving `RunHarness`, `FAKE_TSC` and the parallel-render helpers to `video_e2e.py` (kp-xdd, kp-uu1); moving the film code out of `build-timeline.mjs` (kp-sd3); a drift test across the three fixed format lists of `narrate.py`, `build-timeline.mjs` and `check_budgets.py` (kp-s2m F-c); the out-of-date `status` fields of the wave map.

## Beyond the letter of the spec

1. **The refusal guards are rewritten, not exempted.** The grep of spec §10 is literal and approved by the user. Once no file under `skills/` holds the old name, no tool can treat that name in a special way, and any other unknown name proves the fixed list `["film", "brainrot"]` with the same mutations. So the guards keep their proofs (Review Focus 2 and 5) with the unknown name `slides`, or drop the old name from a list that holds other unknown names. `test_explainer_format_is_refused` is cut: with another name it repeats `test_unknown_format_fails`. The two assertions of `test_rung_drift.py` that look for the old name in `video.md` and `brainrot.md` go: the acceptance grep covers them at this wave's head. Cost if wrong: a later edit that names the old format in a rung file is caught only by a hand-run grep.
2. **`transcript.py` does not validate the format.** A script whose `format` is `brainrot` gets the brainrot page; every other script, a script without the key among them, gets the film page, as `tagOf` of `build-timeline.mjs` tags every other value as a film. `render.sh` runs `--check` before `transcript.py`, and `--check` refuses an unknown name.
3. **The old template becomes `tests/fixtures/components-script.json`, with `"format": "brainrot"`** (spec §5.3). Its texts keep their lengths, so it fails brainrot `--check` with seven limit lines (checked at planning). Only `test_transcript.py` reads it, and `transcript.py` checks no limit. The constant that names it says so.
4. **`Explain.tsx` stays the entry of composition `Explain`** and hands every timeline to `Short`. The composition id does not change: `render.sh`, `test_render.py`, `test_render_film.py` and `test_short_still.py` name it.
5. **The type `Format` goes;** `Timeline.format` is `"brainrot"`, as `FilmTimeline.format` is `"film"`.
6. **`test_png_diff_level` is ported** to `test_png_diff.py`: `png_diff.py` stays (spec §10), and `test_short_still.py` calls `differing_pixels` with `level=16`. The drift and capture-script cases go with the harness: they test only the harness.
7. **The film workspace's `regression/landscape-baseline` is deleted** (the epic asks it), and its empty `regression` directory with it. The shared workspace's baseline stays.
8. **`README.md` does not change.** It names neither template nor the removed format (checked at planning).
9. **The template keeps `"format": "film"`,** and `video.md` keeps "Keep `"format": "film"`" (`FilmRungCase` pins both). The sentence after it changes: a script without the key is also a film.
10. **Spec §7.1 loses `wordTimed: true`** (wave 10, decision 4: no tool reads the key).

## Review Focus

1. A film author leaves out the `format` key. The script stage of `render.sh` must pass with the real `build-timeline.mjs`, `transcript.py` and `verify.sh`. Task 1: `BrainrotRouteCase.test_stage_script_reads_the_format_from_the_script`.
2. An old output directory whose script names a format that no longer exists is rendered again. The run must stop in the script stage, before any synthesis. Task 4: `StageOneCase.test_an_unknown_format_stops_at_the_script_stage`.
3. The page of a film script without the key must be the page of the same script with `"format": "film"`: id headings, no Format or Background row, no portrait class. Task 1: `FilmTest.test_a_script_without_a_format_is_a_film`.
4. A brainrot render after the landscape branch goes: composition `Explain` still lays out `Short` at 1080x1920. Task 2: the gated `test_render_brainrot` and `test_short_still`, and the type check of the app.
5. A stale checkout's `formats.json` holds a third row. Its name must not become a format. Task 4: `test_an_extra_row_does_not_make_a_format`.

---

### Task 1: the transcript reads a script without a format as a film

**Files:**
- Move: `skills/explain/templates/video-script.json` to `skills/explain/tests/fixtures/components-script.json`
- Modify: `skills/explain/video/transcript.py` (docstring 7-12; `is_brainrot` 210-211; `is_film` 214-215; `format_rows` docstring 243)
- Modify: `skills/explain/templates/video.html` (comment 13-15)
- Modify: `skills/explain/tests/test_transcript.py` (`TEMPLATE` 22; `template_script` 35-36; `OutputTest.brainrot` 334-337; `test_explainer_page_has_no_format_row` 398-412; `FilmTest`)
- Modify: `skills/explain/tests/test_render.py` (`BrainrotRouteCase.stage_script_format` 854-881; `test_stage_script_reads_the_format_from_the_script` 883-897)
- Modify: `skills/explain/rungs/video.md` (line 38)

**Interfaces:**
- Consumes: nothing new.
- Produces, declarations only:

  ```python
  # transcript.py
  def is_brainrot(script) -> bool      # script.get("format") == "brainrot"
  def is_film(script) -> bool          # not is_brainrot(script)
  # test_transcript.py
  COMPONENTS = EXPLAIN / "tests" / "fixtures" / "components-script.json"
  def components_script() -> dict      # replaces template_script()
  # test_render.py
  def stage_script_format(self, script: dict) -> subprocess.CompletedProcess   # BrainrotRouteCase; fake_page goes
  ```
  The file name `templates/video-script.json` is free after this task (Task 3 uses it).

- [ ] **Step 1: Move the old template.** Run `git mv skills/explain/templates/video-script.json skills/explain/tests/fixtures/components-script.json`. Add the top-level key `"format": "brainrot"`. Nothing else in the file changes.

  Run: `python3 -c 'import json; s = json.load(open("skills/explain/tests/fixtures/components-script.json")); print(s["format"], [x["component"] for x in s["scenes"]])'`
  Expected: `brainrot ['title', 'bullets-appear', 'diagram-with-highlight-walk', 'code-with-line-highlights', 'before-after']`

- [ ] **Step 2: Write the failing tests.**
  - `test_transcript.py`: `TEMPLATE` and `template_script()` become `COMPONENTS` and `components_script()`, at every use. The comment on `COMPONENTS`: a brainrot-format script with every component (spec §5.3); `transcript.py` checks no limit, so its texts keep lengths that brainrot `--check` refuses. `OutputTest.brainrot()` goes; its callers use `retargeted()`, which is brainrot through the fixture's key. `test_explainer_page_has_no_format_row` goes: `test_film_page_has_no_format_row_and_a_landscape_video` holds the same assertions for the page without the rows.
  - New `FilmTest.test_a_script_without_a_format_is_a_film`: `self.film()` with its `format` key deleted, and `self.film()` as it is, each generated with `--narrator say --background "x.mp4 @ 0.0 s"`. Both runs exit 0, and their `index.html` and `narration.md` are equal, byte for byte. Red: `is_film` is true only for `"format": "film"`, so the script without the key goes through `BODIES` (`KeyError 'component'`, exit 2).
  - `test_render.py`: `stage_script_format` loses `fake_page` and its fakes; it always runs the real `build-timeline.mjs`, `transcript.py` and `verify.sh`. Its docstring loses the sentences about the fakes and decision 2 of wave 10. `test_stage_script_reads_the_format_from_the_script` keeps both subcases and both expected values (`(0, ["script: ok (4 scenes)", "fmt=brainrot"])` and `(0, ["script: ok (8 scenes)", "fmt=film"])`). Its comment adds the red: `transcript.py` reads a script without the key as another format, so the script stage fails.

- [ ] **Step 3: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_transcript tests.test_render.BrainrotRouteCase`
  Expected: `FAILED (failures=2)`: `test_a_script_without_a_format_is_a_film` (exit 2) and `test_stage_script_reads_the_format_from_the_script` (the film subcase exits 1 in the script stage, in `transcript.py`). Every other case passes.

- [ ] **Step 4: Implement `transcript.py`** by decision 2 and the Interfaces block. The module docstring describes two pages: the brainrot page (Format row, Background row, portrait video) and the film page, for every other script, a script without the key among them. It names no third format. The docstring of `format_rows` says `""` for a film. In `templates/video.html`, the comment says that the format markers are empty for a film.

- [ ] **Step 5: Reword item 2 of section 3 of `video.md`** (line 38):

  ```
  2. Keep `"format": "film"`. A script without the key is also a film.
  ```

  Run: `python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/video.md`
  Expected: `0 errors, 0 warnings`

- [ ] **Step 6: Run the tests.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_transcript tests.test_render tests.test_film_example tests.test_rung_drift tests.test_render_film`
  Expected: `OK`; the gated cases are skipped. (Checked at planning in a scratch copy: with the fixture moved and its key added, only `test_explainer_page_has_no_format_row` of `test_transcript.py` fails, and this step removes it.)

- [ ] **Step 7: Commit.**

  ```bash
  git add skills/explain/video/transcript.py skills/explain/templates/video.html skills/explain/tests/fixtures/components-script.json skills/explain/tests/test_transcript.py skills/explain/tests/test_render.py skills/explain/rungs/video.md
  git commit -m "feat: explain: the transcript reads a script without a format as a film"
  ```
  The `git mv` of Step 1 stages the removal of `templates/video-script.json`. `git show --stat HEAD` lists it as a rename to `tests/fixtures/components-script.json`.

- [ ] **Step 8: Mutation check, after the commit.** Make `is_brainrot` read `script.get("format", "brainrot") == "brainrot"`. Run `cd skills/explain && python3 -B -m unittest tests.test_transcript.FilmTest`: `test_a_script_without_a_format_is_a_film` fails. Revert with `git checkout -- skills/explain/video/transcript.py`. `git status --short` prints nothing.

---

### Task 2: the Remotion project and the tests lose the landscape layout

**Files:**
- Modify: `skills/explain/video/src/Explain.tsx` (all 40 lines)
- Modify: `skills/explain/video/src/Root.tsx` (`EMPTY` 6-17)
- Modify: `skills/explain/video/src/types.ts` (`captions` comment 63; `Format` 39; `Timeline` 75-86)
- Modify: `skills/explain/video/src/box.ts` (comments 1-4 and 87-88; `LANDSCAPE_BOX` 38-59 goes)
- Modify: `skills/explain/video/src/sceneBox.tsx` (re-export 8; comment 11)
- Modify: `skills/explain/video/src/sceneBody.tsx` (comment 1-2), `src/kit/palette.ts` (comment 2-3), `src/FilmStage.tsx` (comment 3)
- Modify: `skills/explain/tests/test_scene_geometry.py` (`TestSceneBox` 70-95)
- Modify: `skills/explain/tests/test_png_diff.py` (docstring 1-2; import 12; a new case)
- Delete: `skills/explain/tests/test_landscape_regression.py`, `skills/explain/tests/capture_landscape_baseline.sh`
- Delete, outside the repository: `$EXPLAIN_VIDEO_WORKSPACE/regression/landscape-baseline`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces, declarations only:

  ```ts
  // types.ts: the type Format goes
  export type Timeline = { format: "brainrot"; engine: string; fps: number; width: number; height: number;
    totalFrames: number; maxSceneSeconds: number; maxTotalSeconds: number; background?: Background;
    scenes: TimelineScene[] };
  // Explain.tsx
  export function Explain(timeline: Timeline)   // renders <Short {...timeline} />; no return annotation, as now
  // box.ts: exports BRAINROT_BOX, codeLineLimit, contentRect (values) and Size, SceneType, SceneBox (types)
  ```
  ```python
  # test_png_diff.py
  class DifferingPixelsCase(unittest.TestCase)
  ```

- [ ] **Step 1: Write the failing tests.**
  - `test_scene_geometry.py`: new `TestSceneBox.test_box_exports_the_brainrot_box_only`. Node imports `* as box` from `box.ts` and prints the sorted names. They equal `["BRAINROT_BOX", "codeLineLimit", "contentRect"]`. Red: a second box is left in `box.ts`.
  - `test_landscape_box_unchanged` goes. `test_code_line_limit_per_box` becomes `test_code_line_limit_of_the_brainrot_box`: `codeLineLimit(BRAINROT_BOX)` is 15. Its docstring names no other box.
  - `test_png_diff.py`: new `DifferingPixelsCase.test_differing_pixels_level`, the port of `PngDiffCase.test_png_diff_level`. Two 4x1 PNGs, made with this module's `write_png(path, width, height, ink)`, differ by 20 in one channel of one pixel. `differing_pixels(a, b, 0, 4, 0, 1, level=16)` is 1 and the same call with `level=40` is 0. Red: the `level` parameter is ignored (a fixed threshold of 40 or of 16). The module docstring names `ink_extent` and `differing_pixels`.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_scene_geometry tests.test_png_diff`
  Expected: `FAILED (failures=1)`: `test_box_exports_the_brainrot_box_only` lists `LANDSCAPE_BOX`. `test_differing_pixels_level` passes at once (Step 8 checks it).

- [ ] **Step 3: Implement the Remotion project** by the Interfaces block:
  - `box.ts`: `LANDSCAPE_BOX` goes. The header comment says that the box is the panel of a brainrot scene. The comment of `codeLineLimit` gives only the brainrot figure (15 at 1080x960).
  - `sceneBox.tsx`: re-exports `BRAINROT_BOX`, `codeLineLimit` and `contentRect`. The comment at line 11 says that a scene without a provider fails, and names no other size.
  - `Explain.tsx`: no landscape stack, and no import of `theme`, `sceneBox` or `sceneBody`. Its header comment: composition `Explain` renders a brainrot timeline with `Short`.
  - `Root.tsx`: `EMPTY` has `format: "brainrot"`, `width: 1080`, `height: 1920`, `maxSceneSeconds: 30`, `maxTotalSeconds: 90` (the brainrot row of `formats.json`). The rest stays.
  - `types.ts`: the comments of `Timeline`, `background` and `captions` name brainrot as the format of this type.
  - Comments only: `sceneBody.tsx` says that it is the scene body of the brainrot layout (`Short`); `kit/palette.ts` says that `theme.ts` stays the palette of brainrot and the HTML templates; `FilmStage.tsx` line 3 says "placed as `short/Short.tsx` places a clip".

- [ ] **Step 4: Delete the landscape harness and the film workspace's baseline.**

  Run: `git rm skills/explain/tests/test_landscape_regression.py skills/explain/tests/capture_landscape_baseline.sh`

  Then, only for the film workspace:

  ```bash
  test "$EXPLAIN_VIDEO_WORKSPACE" = /Users/valukin/karpathy-wt/film-workspace && rm -rf "$EXPLAIN_VIDEO_WORKSPACE/regression/landscape-baseline" && rmdir "$EXPLAIN_VIDEO_WORKSPACE/regression" && echo removed
  ```
  Expected: `removed`. If the `test` fails, delete nothing and report it.

  Run: `ls "$EXPLAIN_VIDEO_WORKSPACE"; ls -d ~/karpathy/video-workspace/regression/landscape-baseline`
  Expected: the film workspace lists `app backgrounds bg-stage models runs` (no `regression`); the shared baseline path is printed (read only, never changed).

- [ ] **Step 5: Run the unit tests.**

  Run: `cd skills/explain && python3 -B -m unittest -v tests.test_scene_geometry tests.test_png_diff tests.test_film_kit tests.test_film_example tests.test_short_logic 2>&1 | grep -E '_compile|^Ran|^OK|^FAILED'`
  Expected: `test_the_app_and_a_scene_compile ... ok` and `test_the_app_compiles_with_the_example ... ok` (not `skipped`), then `OK`. These two cases type-check the whole `src/` with the workspace's `tsc`.

- [ ] **Step 6: Run the gated brainrot renders.**

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_brainrot tests.test_short_still`
  Expected: the workspace path, then `OK` with no skip. `ls "$EXPLAIN_VIDEO_WORKSPACE/runs"` prints nothing.

- [ ] **Step 7: Commit.**

  ```bash
  git add skills/explain/video/src/Explain.tsx skills/explain/video/src/Root.tsx skills/explain/video/src/types.ts skills/explain/video/src/box.ts skills/explain/video/src/sceneBox.tsx skills/explain/video/src/sceneBody.tsx skills/explain/video/src/kit/palette.ts skills/explain/video/src/FilmStage.tsx skills/explain/tests/test_scene_geometry.py skills/explain/tests/test_png_diff.py
  git commit -m "refactor: explain: the Remotion project and the tests lose the landscape layout and its regression harness"
  ```
  The `git rm` of Step 4 is staged already; `git show --stat HEAD` lists the two deleted files.

- [ ] **Step 8: Mutation checks, after the commit.** Each is one scratch edit, reverted with `git checkout -- <file>`:
  - `Root.tsx`: `EMPTY.format` becomes `"film"`. Run `cd skills/explain && python3 -B -m unittest tests.test_film_kit.TestKitCompiles.test_the_app_and_a_scene_compile`: it fails (`tsc` refuses the type).
  - `tests/png_diff.py`: `differing_pixels` ignores `level` and uses 40. Run `python3 -B -m unittest tests.test_png_diff`: `test_differing_pixels_level` fails.

  `git status --short` prints nothing at the end.

---

### Task 3: the film template is `templates/video-script.json`

**Files:**
- Rename: `skills/explain/templates/film-script.json` to `skills/explain/templates/video-script.json`
- Modify: `skills/explain/tests/test_film_example.py` (docstring line 2; `FILM_TEMPLATE` 31)
- Modify: `skills/explain/tests/test_rung_drift.py` (docstring line 25; `FILM_TEMPLATE` 232; `test_the_script_section_copies_the_film_template` 618-623)
- Modify: `skills/explain/tests/test_render.py` (the film template path of `test_stage_script_reads_the_format_from_the_script`, line 892 at the base)
- Modify: `skills/explain/tests/test_render_film.py` (docstring line 28)
- Modify: `skills/explain/rungs/video.md` (line 37)

**Interfaces:**
- Consumes: Task 1 (the name `templates/video-script.json` is free).
- Produces: `FILM_TEMPLATE = EXPLAIN / "templates" / "video-script.json"` in `test_film_example.py` and `test_rung_drift.py`. `test_render_film.py` and `test_render_parallel.py` read the template through `template_script()` of `test_film_example.py`, so they follow.

- [ ] **Step 1: Write the failing tests.** Both `FILM_TEMPLATE` constants and the path in `test_render.py` name `templates/video-script.json`. `test_the_script_section_copies_the_film_template`: the section "Write the script" of `video.md` holds `templates/video-script.json` and `"format": "film"`; `video.md` does not hold `film-script.json`; the template's `format` is `film`. Its comment: red, the rung names the old file name, or leaves out `"format": "film"`.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift tests.test_film_example tests.test_render.BrainrotRouteCase`
  Expected: `FAILED`: the template file is not found, and `video.md` names `film-script.json`.

- [ ] **Step 3: Rename the template and follow it.** Run `git mv skills/explain/templates/film-script.json skills/explain/templates/video-script.json`. `video.md` line 37: `1. Copy <skill-dir>/templates/video-script.json to <output-dir>/script.json.` (the paths in backticks, as now). The docstrings of `test_film_example.py` (line 2), `test_rung_drift.py` (line 25) and `test_render_film.py` (line 28) name the new file.

  Run: `git grep -n 'film-script' -- skills/ README.md; python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/video.md`
  Expected: no grep line, then `0 errors, 0 warnings`.

- [ ] **Step 4: Run the tests.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift tests.test_film_example tests.test_render tests.test_render_film tests.test_render_parallel tests.test_check_scene tests.test_film_guard`
  Expected: `OK`; the gated cases are skipped.

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/templates/video-script.json skills/explain/tests/test_film_example.py skills/explain/tests/test_rung_drift.py skills/explain/tests/test_render.py skills/explain/tests/test_render_film.py skills/explain/rungs/video.md
  git commit -m "feat: explain: the film template is templates/video-script.json"
  ```
  `git show --stat HEAD` lists the template as a rename.

---

### Task 4: no file under `skills/` names the removed format; the wave's acceptance

**Files:**
- Modify: `skills/explain/tests/test_render.py` (`StageOneCase` case at 133-142)
- Modify: `skills/explain/tests/test_video_timeline_brainrot.py` (cases at 52-57, 112-119, 233-245)
- Modify: `skills/explain/tests/test_video_timeline_film.py` (cases at 282-289 and 1081-1092)
- Modify: `skills/explain/tests/test_check_budgets.py` (case at 86-93)
- Modify: `skills/explain/tests/test_narrate_sentences.py` (case at 231-234)
- Modify: `skills/explain/tests/test_rung_drift.py` (comments at 577 and 689; assertions at 631 and 696)
- Modify: `docs/superpowers/specs/2026-10-05-explain-film-design.md` (§7.1, line 314)

**Interfaces:**
- Consumes: Tasks 1 to 3 (the acceptance greps need all of them).
- Produces: nothing new. Test names after this task: `StageOneCase.test_an_unknown_format_stops_at_the_script_stage` (`test_render.py`), `TestFilmCheck.test_an_extra_row_does_not_make_a_format` (`test_video_timeline_film.py`).

- [ ] **Step 1: Rewrite the guards** by decision 1. Each docstring or comment that spoke of "the removed row" or the old name names an unknown name instead.
  - `test_render.py`: `test_an_explainer_script_stops_at_the_script_stage` becomes `test_an_unknown_format_stops_at_the_script_stage`. The brainrot template gets `"format": "slides"`. The three assertions stay: exit 1, the stage lines are exactly `["script: FAIL script: format must be film or brainrot"]`, and `out/audio` does not exist. Comment: red, `--check` takes an unknown name as a format, or the narration runs before the check.
  - `test_video_timeline_brainrot.py`: cut `test_explainer_format_is_refused`. The value list of `test_invalid_format_values_fail_with_the_format_line` loses the old name. `test_build_mode_unknown_format_fails` runs `"vertical"` alone, with no subtest.
  - `test_video_timeline_film.py`: `test_an_explainer_row_does_not_make_a_format` becomes `test_an_extra_row_does_not_make_a_format`. The copy of the tool has the two real rows and `rows["slides"]`, a copy of the brainrot row. `film_script()` with `"format": "slides"` gets the format line alone. `test_types_refuses_a_script_that_is_not_a_film` refuses `"brainrot"` and `"slides"`.
  - `test_check_budgets.py`: `test_a_timeline_of_another_format_exits_2` runs `(None, "slides", "", 7)`.
  - `test_narrate_sentences.py`: the value list of `test_unknown_format_exit_2` loses the old name. Its docstring: an unknown format is refused, not narrated as a film.
  - `test_rung_drift.py`: the two `assertFalse` lines that look for the old name go. The comment at 577: red, `video.md` lists other `ok` lines than the eleven of a film run, or the guard comes before the timeline. The comment at 689 loses its last clause.

- [ ] **Step 2: Run them.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render tests.test_video_timeline_brainrot tests.test_video_timeline_film tests.test_check_budgets tests.test_narrate_sentences tests.test_rung_drift`
  Expected: `OK`; the gated cases are skipped. These cases pass at once; Step 5 checks them.

- [ ] **Step 3: Fold spec §7.1.** In line 314, drop `` `wordTimed: true`, `` so that the film row reads "20 source lines, and no component limits".

- [ ] **Step 4: Commit.**

  ```bash
  git add skills/explain/tests/test_render.py skills/explain/tests/test_video_timeline_brainrot.py skills/explain/tests/test_video_timeline_film.py skills/explain/tests/test_check_budgets.py skills/explain/tests/test_narrate_sentences.py skills/explain/tests/test_rung_drift.py docs/superpowers/specs/2026-10-05-explain-film-design.md
  git commit -m "test: explain: the refusal guards name an unknown format, not the removed one"
  ```

- [ ] **Step 5: Mutation checks, after the commit.** Each is one scratch edit, reverted with `git checkout -- <file>`; run the named module after each:
  - `build-timeline.mjs`: `knownFormat` reads `typeof format === "string" && has(FORMATS, format)`. `tests.test_video_timeline_film`: `test_an_extra_row_does_not_make_a_format` fails.
  - `build-timeline.mjs`: `knownFormat` is true for any string. `tests.test_render.StageOneCase`: `test_an_unknown_format_stops_at_the_script_stage` fails.
  - `check_budgets.py`: any string is a usable format. `tests.test_check_budgets`: the `"slides"` subtest of `test_a_timeline_of_another_format_exits_2` fails.

  `git status --short` prints nothing at the end.

- [ ] **Step 6: The greps of spec §10.**

  Run: `git grep -n -i explainer -- skills/ README.md; git grep -n "LANDSCAPE_BOX\|test_landscape_regression\|capture_landscape_baseline" -- skills/; git grep -l components-script.json -- skills/`
  Expected: one line only, `skills/explain/tests/test_transcript.py`.

- [ ] **Step 7: Run the full unit suites, once.**

  Run: `cd skills/explain && python3 -B -m unittest discover -s tests`
  Expected: `OK (skipped=43)`, with no failure and no error: the base's 45, less the two gated cases of the deleted harness. The test count falls by 14 with the harness and changes with the cuts and the new cases.

  Run: `cd skills/ste && python3 -B -m unittest discover -s tests`
  Expected: `OK`.

- [ ] **Step 8: Run the map's acceptance.**

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film tests.test_render_brainrot`
  Expected: the workspace path, then `OK` with no skip. The film run prints eleven `ok` lines (`FilmRenderCase`) and brainrot ten (`BrainrotRenderCase`).

- [ ] **Step 9: Check the tree.**
  - `git diff --stat e011103198d82dc0d583c1eb0b4f80798a35554e -- . ':!docs'` lists only the files of Tasks 1 to 4.
  - `git status --short` prints nothing. `ls "$EXPLAIN_VIDEO_WORKSPACE/runs"` prints nothing.

## Wave close

The four conditions of spec §10 (the map's `done_when`):
- Both greps print nothing: Task 4 Step 6 (transcript: Task 1; Remotion and harness: Task 2; template: Task 3; guards: Task 4).
- `narrate.py` has one narration mode: wave 10, Task 1 (`test_a_script_without_a_format_is_narrated_in_sentences`); this wave does not change `narrate.py`.
- The unit suites pass: Task 4 Step 7.
- The film and brainrot end-to-end tests pass with eleven and ten lines: Task 4 Step 8.

Notes for the finish stage:
- The landscape baseline caveat of the first finish summary is gone: no test reads a baseline, and the film workspace has none.
- Spec §11 (the lesson and Russian amendments) can now target the film: the old template is a test fixture, and `templates/video-script.json` is the film template.
