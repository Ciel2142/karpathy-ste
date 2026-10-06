# Explain lesson — wave `clip-format` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `"format": "clip"` script passes every stage of the film pipeline as a film of at most 60 s: a `clip` row in `formats.json`, `clip` in every format list, the film path for every format that is not brainrot, and `minText` carried from the row into the timeline.

**Architecture:** `video/formats.json` gains the `clip` row (the film row with three values changed) and a `minText` key in both film-path rows. `build-timeline.mjs` knows three names: `--check` takes its limits and tag from the script's own row, build mode and `--types` treat a clip as a film, and a film-path timeline carries `minText`. `narrate.py` and `check_budgets.py` add `clip` to their fixed lists; `render.sh` and `check_render.sh` stop testing `== film` and test `!= brainrot` (the kp-5s0 constraint); `transcript.py` already does. Nothing reads `minText` yet: the guard reads it in wave `clip-checks`.

**Tech Stack:** Node ESM (`build-timeline.mjs`), Python 3 stdlib tools and `unittest`, bash (`render.sh`, `check_render.sh`), TypeScript types of the Remotion app (`tsc` of the workspace).

Base: dc5d5cfb549bc78c46176da6243960500a3d0247
Test runs: scoped per task; full suite once, final task.

**Spec:** `docs/superpowers/specs/2026-10-04-explain-lesson-design.md` — this wave implements the `clip` rows of §6.1 (not the `kit/mono.ts` cut mark and not the `FilmStage.tsx` floor: wave `clip-checks`), the format and budget items of §7.1, and the "`clip` takes the film path" item of §7.1. Wave map: `docs/superpowers/waves/2026-10-04-explain-lesson.yaml` (wave `clip-format`, ralph wave 2, epic kp-7ft). Read `br comments list kp-5s0` for the film feature's last rulings.

## Global Constraints

- Work on this worktree's branch `explain-lesson/wave-2`. Never commit to `main`. Never stage or commit `.beads/`.
- `EXPLAIN_VIDEO_WORKSPACE` is preset to the lesson branch's own workspace. Never render into `~/karpathy/video-workspace`.
- Run every test command from `skills/explain`, as `python3 -B -m unittest ...`.
- Row values, exactly: film row gains `"minText": 14`; `clip` row = the film row with `"maxTotalSeconds": 60`, `"sourceLines": 12`, `"minText": 19` (so 1280×720, 3 to 30 scenes, 30 s per scene, 45 words, lead 6, pause 12).
- Texts, exactly: `FAIL script: format must be film, brainrot or clip` (build-timeline `--check` and build mode); `narration: FAIL script <path>: format must be film, brainrot or clip` (narrate.py, exit 2); `FAIL total 61.0 s (max 60, clip)` (check_budgets.py); a limit line of a clip ends `, clip)`; formats.json loader cause `expected an object with a film, a brainrot and a clip row`.
- Film-path rule (spec §6.5, kp-5s0 note): where code asks for the format, film behavior holds for every format that is not `brainrot`. Never add a test `== "film"` or a new list `("film", "clip")` outside the three fixed tool lists (`FORMAT_NAMES`, `NARRATED_FORMATS`, `check_budgets.FORMATS`).
- A refused format keeps today's handling: `--check` prints the format line, then validates the rest with the film rules, the film row and the tag `, film`.
- The film and brainrot behavior does not change, except that a film timeline gains `minText`. A brainrot timeline gains no key.
- Files this wave may change: `video/formats.json`, `video/build-timeline.mjs`, `video/narrate.py`, `video/check_budgets.py`, `video/transcript.py` (docstring), `video/check_render.sh`, `video/src/types.ts`, `video/src/Root.tsx`, `scripts/render.sh`, and the tests named in the tasks. No rung or skill doc (`rungs/video.md` is wave 3, `rungs/lesson.md` wave 4).
- Code comments follow each file's style: short plain sentences. Commits: `<type>: explain: <description>`, ending with the session's Co-Authored-By line.

## Review Focus

1. A clip that runs 61 s passes `--check` (it does not measure time) and must fail at the `timeline` stage with `FAIL total 61.0 s (max 60, clip)`. Expected: the built clip timeline carries `maxTotalSeconds: 60` (Task 2) and `check_budgets.py` judges it with the clip tag (Task 3).
2. One tool knows `clip` and another refuses it: the render then stops at a later stage with a misleading line. Expected: the three fixed lists and the rows of `formats.json` hold the same names. Pinned by `test_every_format_list_names_the_rows` (Task 3; it closes parked item F-c of kp-s2m).
3. `minText` hard-coded per format in build-timeline instead of read from the row: a later tuning of the clip row (the live run folds back into `formats.json`) would change nothing. Expected: the timeline value is the row value. Pinned by `test_min_text_comes_from_the_row` (Task 2).
4. A clip whose code card declares 13 lines passes because `--check` reads the film row (20 lines). Expected: `FAIL source app: range 3-15 is 13 lines (max 12, clip)`. Pinned by `test_clip_source_lines` (Task 1).
5. A clip rendered with the brainrot path in one place (no `scene` stage, no `guard`, composition `Explain`, cue stills): the video renders but skips the film checks. Expected: eleven stage lines and composition `Film` for a clip. Pinned in Task 4 (`test_a_clip_run_prints_eleven_stage_lines`, the composition loop, `test_clip_stills_are_the_check_frames`).

## Beyond the letter of the map (decisions made with no user present)

1. `test_render_film.py` and `test_check_render.py` are not in the map's owns, but the film-path cases of `render.sh` and `check_render.sh` live there; Task 4 adds clip cases to them. Cost if wrong: two test files touched outside the list.
2. `check_render.sh` branches on `format != "brainrot"`, so a timeline with no `format` key now takes the film branch (and is unreadable without `checkFrames`). build-timeline always writes the key. The `still_frames` helper of `test_check_render.py` writes `"format": "brainrot"` (its timelines are cue timelines). Cost if wrong: a hand-made timeline without the key fails as unreadable.
3. `test_video_timeline_film.py` changes beyond its message asserts: `FILM_ROW` gains `minText: 14` (Task 1) and the key set of `test_film_top_level_values` gains `minText` (Task 2). Both are forced by the row and timeline change.
4. Only film-path timelines carry `minText`; the brainrot row has none and its timeline keeps its key set (`test_video_timeline.py:535`).
5. The `--types` refusal text stays `--types needs a film script`: a clip is a film.
6. No committed gated clip render: wave `lesson-rung` adds the gated lesson E2E with a clip. Task 4 runs one clip render by hand as evidence and records its lines in the close reason.
7. `transcript.py` needs no code change (every script that is not brainrot is a film page); Task 4 adds a lock-in test that passes at the base and a docstring word.

---

### Task 1: the clip row and the validator

**Files:**
- Modify: `skills/explain/video/formats.json`
- Modify: `skills/explain/video/build-timeline.mjs` (header `:14-19`, `:25-27`; `FORMAT_NAMES` and `loadFormats` `:133-152`; `knownFormat`/`filmRules`/`tagOf` `:250-256`; `checkHeader` `:594`; `validate` `:618-623`)
- Create: `skills/explain/tests/test_video_timeline_clip.py`
- Modify: `skills/explain/tests/test_video_timeline_film.py` (`FILM_ROW` `:20-31`, `FORMAT_LINE` `:32`, loader message `:278`), `skills/explain/tests/test_video_timeline_brainrot.py` (`FORMAT_LINE` `:41`), `skills/explain/tests/test_format_limits.py` (`TestFormatsRows`, `test_formats_file_without_both_rows_fails_cleanly`)

**Interfaces:**
- Consumes: `film_script()`, `FILM_ROW` of `test_video_timeline_film.py`; `VideoCase`, `cite` of `test_video_timeline.py`.
- Produces: in `test_video_timeline_clip.py`: `FORMAT_LINE = "FAIL script: format must be film, brainrot or clip"`, `CLIP_ROW` (dict), `clip_script() -> dict` (film_script() with `"format": "clip"`). In build-timeline: `FORMAT_NAMES = ["film", "brainrot", "clip"]`; `tagOf(format)` returns `, clip` for a clip.

Import helpers only into the new module, never a class that holds tests (unittest would run it twice); `VideoCase` and `FilmBuildCase` hold none.

- [ ] **Step 1: Write the failing tests**

`test_video_timeline_clip.py`, class `TestClipCheck(VideoCase)`; each docstring names its red mutation, as the film module does:
- `test_clip_fixture_passes`: `self.check(clip_script())` gives `(0, "")`.
- `test_clip_row_values`: `rows["clip"] == CLIP_ROW`, where `CLIP_ROW = dict(FILM_ROW, maxTotalSeconds=60, sourceLines=12, minText=19)`.
- `test_clip_source_lines`: `sources` `3-14` passes; `3-15` fails with `FAIL source app: range 3-15 is 13 lines (max 12, clip)` alone.
- `test_clip_scene_count`: 2 scenes fail with `FAIL script: 2 scenes (needs 3 to 30, clip)`; 31 with `FAIL script: 31 scenes (needs 3 to 30, clip)`.
- `test_another_format_names_three_formats`: `"format": "other"` fails with `FORMAT_LINE` alone.

Edits: `FILM_ROW` gains `"minText": 14`; both `FORMAT_LINE` constants become the three-name text; the loader message at film `:278` becomes `expected an object with a film, a brainrot and a clip row`. In `test_format_limits.py`: `test_formats_has_the_film_and_brainrot_rows_only` becomes `test_formats_has_the_three_rows` (`sorted(load_formats()) == ["brainrot", "clip", "film"]`); `test_formats_file_without_both_rows_fails_cleanly` gains the case `'{"film": {}, "brainrot": {}}'` (no clip row: clean fail).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_clip tests.test_video_timeline_film tests.test_video_timeline_brainrot tests.test_format_limits`
Expected: FAIL — every clip case (the format line), `test_clip_row_values` (KeyError), the three-name and loader message asserts, `test_film_row_values`, `test_formats_has_the_three_rows`, the new loader subtest.

- [ ] **Step 3: Implement**

`formats.json`: the film row gains `"minText": 14`; add the `clip` row with the film row's keys in the film row's order and the three values of Global Constraints. `build-timeline.mjs`: `clip` joins `FORMAT_NAMES`; the loader cause and both refusal literals take the texts of Global Constraints; `--check` reads the row of the script's own format (a refused format: the film row); `tagOf` gives `, <format>` for a known format and `, film` for a refused one. Update the header comment (the format sentence, the refusal line, the tag sentence) to name `clip` and say that a clip is a film with its own row.

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command, then `python3 -B -m unittest tests.test_video_timeline tests.test_film_example`
Expected: `OK` (skips only where the workspace tools are missing) for both.

- [ ] **Step 5: Check the broken state**

Make `--check` read `FORMATS.film` for every film-path format; run `tests.test_video_timeline_clip`: `test_clip_source_lines` FAILs (13 lines pass under the film's 20). Revert; it passes.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/video/formats.json skills/explain/video/build-timeline.mjs skills/explain/tests/test_video_timeline_clip.py skills/explain/tests/test_video_timeline_film.py skills/explain/tests/test_video_timeline_brainrot.py skills/explain/tests/test_format_limits.py
git commit -m "feat: explain: clip format row and the validator knows three formats"
```

### Task 2: the clip timeline and `--types`

**Files:**
- Modify: `skills/explain/video/build-timeline.mjs` (`typesOf` `:917-920`; build mode in `main` `:1005-1022`; header `:83-110`)
- Modify: `skills/explain/video/src/types.ts` (`FilmTimeline` `:107-120`), `skills/explain/video/src/Root.tsx` (`EMPTY_FILM` `:32-44`)
- Modify: `skills/explain/tests/test_video_timeline_clip.py`, `skills/explain/tests/test_video_timeline_film.py` (`test_film_top_level_values` key set `:568-575`)

**Interfaces:**
- Consumes: `clip_script()` (Task 1); `FilmBuildCase`, `types_text`, `film_script` of the film module.
- Produces: a film-path timeline (format `film` or `clip`) holds `"minText": <row minText>` (film 14, clip 19); `"format"` is the script's format. TypeScript:

```ts
export type FilmTimeline = { format: "film" | "clip"; /* ...existing keys... */ minText: number; };
```

`--types` writes the names of a clip script exactly as of a film script.

- [ ] **Step 1: Write the failing tests**

In `test_video_timeline_clip.py`, class `TestClipBuild(FilmBuildCase)`:
- `test_clip_top_level_values`: built `clip_script()`: `(format, width, height) == ("clip", 1280, 720)`, `(maxSceneSeconds, maxTotalSeconds, minText) == (30, 60, 19)`, and `sorted(timeline)` is the film key set plus `minText`.
- `test_clip_builds_the_film_scenes`: the clip timeline and the `film_script()` timeline, each without `format`, `maxTotalSeconds` and `minText`, are equal (same scenes, sources, checkFrames, totalFrames).
- `test_film_timeline_carries_min_text_14`: built `film_script()` has `minText == 14`.
- `test_min_text_comes_from_the_row`: a copy of the tool beside a `formats.json` whose clip row has `minText: 21` builds `clip_script()` into a timeline with `minText == 21`.

Class `TestClipTypes(VideoCase)`: `test_types_takes_a_clip_script`: `--types` on `clip_script()` exits 0, prints nothing, and writes `types_text('"type" | "forms" | "ends"', '"app"')`.

In the film module, `test_film_top_level_values` adds `"minText"` to its key list and asserts `timeline["minText"] == 14`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_clip tests.test_video_timeline_film`
Expected: FAIL — the clip build has no sources or checkFrames (built as brainrot), no `minText` key anywhere, `--types needs a film script` for the clip.

- [ ] **Step 3: Implement**

Build mode treats every known format but brainrot as a film (the existing `filmRules`), and a film-path timeline adds `minText` from its row. `typesOf` accepts a known format that is not brainrot; the refusal text stays. `types.ts`: `FilmTimeline.format` is `"film" | "clip"` and gains `minText: number` with a comment (the guard's text floor in px, from the format row). `Root.tsx`: `EMPTY_FILM` gains `minText: 14`. Header comment: the film timeline section names `minText`; the `--types` lines accept `"format": "clip"`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command, then `python3 -B -m unittest tests.test_video_timeline tests.test_film_example tests.test_film_kit`
Expected: `OK` for both; `ExampleSceneCase.test_the_app_compiles_with_the_example` runs (not skipped) and passes, so `tsc` accepts `types.ts` and `Root.tsx`.

- [ ] **Step 5: Check the broken state**

Replace the row read with `minText: format === "clip" ? 19 : 14`; `test_min_text_comes_from_the_row` FAILs and the other cases pass. Revert.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/video/build-timeline.mjs skills/explain/video/src/types.ts skills/explain/video/src/Root.tsx skills/explain/tests/test_video_timeline_clip.py skills/explain/tests/test_video_timeline_film.py
git commit -m "feat: explain: a clip builds a film timeline with minText from its row"
```

### Task 3: narration and budgets know the clip; one drift test over the format lists

**Files:**
- Modify: `skills/explain/video/narrate.py` (docstring `:19`, `NARRATED_FORMATS` `:54`, `load_script` `:346-355`)
- Modify: `skills/explain/video/check_budgets.py` (docstring `:1-21`, `FORMATS` `:29`, `format_tag` docstring `:46`)
- Modify: `skills/explain/tests/test_narrate_sentences.py` (`test_unknown_format_exit_2` `:231-241`), `skills/explain/tests/test_check_budgets.py`, `skills/explain/tests/test_format_limits.py`

**Interfaces:**
- Consumes: `FORMAT_NAMES` of `build-timeline.mjs` with three names (Task 1).
- Produces: `NARRATED_FORMATS == ("film", "brainrot", "clip")`; `check_budgets.FORMATS == ("film", "brainrot", "clip")`.

- [ ] **Step 1: Write the failing tests**

- `test_narrate_sentences.py`: `test_unknown_format_exit_2` expects `narration: FAIL script {script}: format must be film, brainrot or clip` and adds `"Clip"` to its refused values. New `test_a_clip_is_narrated_in_sentences`: the one-scene script with `"format": "clip"` through `self.shell(..., "--engine", "say")` exits 0, writes `one.say.words.json`, and line 4 of `one.say.txt` is `mode=sentences`.
- `test_check_budgets.py`: `test_clip_total_60_ok_61_fails`: `write_timeline([900, 900], 30, 60, fmt="clip")` prints `ok 2 60.0 60.000`; `[900, 900, 30]` prints `FAIL total 61.0 s (max 60, clip)`; both exit 0.
- `test_format_limits.py`: `test_every_format_list_names_the_rows`: `sorted(narrate.NARRATED_FORMATS)`, `sorted(check_budgets.FORMATS)`, the sorted JSON array of the line `const FORMAT_NAMES = [...];` of `build-timeline.mjs`, and `sorted(load_formats())` all equal `["brainrot", "clip", "film"]`. Load the two Python tools with `importlib` from `video/`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_narrate_sentences tests.test_check_budgets tests.test_format_limits`
Expected: FAIL — the clip narration exits 2, the clip timeline exits 2 `no usable format`, the message text, the drift test (two lists lack `clip`).

- [ ] **Step 3: Implement**

Add `"clip"` to both lists; the narrate.py refusal takes the three-name text. Docstrings: narrate.py names the three formats; check_budgets.py gives the clip limits (30 s and 60 s), the tag `, clip`, and the three usable formats.

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command. Expected: `OK`.

- [ ] **Step 5: Check the broken state**

Drop `"clip"` from `check_budgets.FORMATS` only: `test_clip_total_60_ok_61_fails` and `test_every_format_list_names_the_rows` FAIL. Revert.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/video/narrate.py skills/explain/video/check_budgets.py skills/explain/tests/test_narrate_sentences.py skills/explain/tests/test_check_budgets.py skills/explain/tests/test_format_limits.py
git commit -m "feat: explain: narration and budgets accept the clip format"
```

### Task 4: a clip takes the film path in render.sh, check_render.sh and the transcript; wave acceptance

**Files:**
- Modify: `skills/explain/scripts/render.sh` (header `:12-15`, `:23-24`, `:36-38`, `:53`; `fmt` comment `:209`; `:305`; `stage_scene` `:376`; `stage_guard` `:473`; `stage_render` `:534`)
- Modify: `skills/explain/video/check_render.sh` (header `:28`; `read_timeline` `:90`), `skills/explain/video/transcript.py` (docstring `:7-9`)
- Modify: `skills/explain/tests/test_render.py` (`:140`; `test_stage_script_reads_the_format_from_the_script` `:874-886`), `skills/explain/tests/test_render_film.py` (`test_a_film_renders_composition_film` `:247-270`, `SceneStageCase`, `SceneRunCase`), `skills/explain/tests/test_check_render.py` (`StillFramesCase.still_frames` `:207-211`), `skills/explain/tests/test_transcript.py` (`FilmTest`)

**Interfaces:**
- Consumes: `--check` and `--types` accept a clip (Tasks 1, 2); narrate.py and check_budgets.py accept it (Task 3).
- Produces: `render.sh` runs `scene` and `guard` and renders composition `Film` for every format but brainrot; `check_render.sh` cuts the checkFrames stills for every timeline format but brainrot.

- [ ] **Step 1: Write the failing tests**

- `test_render.py`: `:140` expects `script: FAIL script: format must be film, brainrot or clip`. `test_stage_script_reads_the_format_from_the_script` gains a third case: `templates/video-script.json` with `"format": "clip"` and the repository root gives `(0, ["script: ok (8 scenes)", "fmt=clip"])`.
- `test_render_film.py`: the loop of `test_a_film_renders_composition_film` gains `("clip", "Film")`. New `SceneStageCase.test_a_clip_has_the_scene_stage`: `script.json` is `template_script()` with `"format": "clip"`; `self.stage("clip")` gives `(0, "scene: ok (2 files)\n")` and one tsc call (the real `--types` wrote `script.gen.ts`). New `SceneRunCase.test_a_clip_run_prints_eleven_stage_lines`: `self.start("clip")` prints the eleven stage names of the film case, `scene: ok (2 files)`, `guard (2 frames): ok`, and both CLI calls (guard pass, render) name composition `Film`.
- `test_check_render.py`: `still_frames` writes `"format": "brainrot"` into its timeline. New `test_clip_stills_are_the_check_frames`: the film fixture with `"format": "clip"` prints the same seven lines as `test_film_stills_are_the_check_frames`.
- `test_transcript.py`: `FilmTest.test_a_clip_is_a_film_page`: `index.html` and `narration.md` of `self.film()` with `"format": "clip"` are byte-equal to those of `self.film()`. It passes at the base; its red mutation is `is_film` true only for `"film"` (the clip then goes through the component bodies: KeyError, exit 2).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_render tests.test_render_film tests.test_check_render tests.test_transcript`
Expected: FAIL — the clip composition is `Explain`, the clip scene stage prints nothing, the clip run prints nine stage lines, the clip stills are cue stills (KeyError `cueFrames`: exit 1), the message text. `test_a_clip_is_a_film_page` passes.

- [ ] **Step 3: Implement**

`render.sh`: `stage_scene` and `stage_guard` return early for brainrot only; `stage_render` picks `Explain` for brainrot and `Film` for every other format. Header: the format is `film` (no key), `brainrot` or `clip`; the refusal line takes the three-name text; a clip run is a film run (eleven stages, `scene` and `guard`, composition `Film`, the film stills); the timeline line lists `clip 30 s and 60 s`. `check_render.sh`: the checkFrames branch holds for every format but brainrot; the header sentence says so. `transcript.py` docstring: every other script is a film page, a clip and a script without the key among them.

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command, then `python3 -B -m unittest tests.test_rung_drift`
Expected: `OK` for both.

- [ ] **Step 5: Check the broken state**

Put back `[ "$fmt" = "film" ] || return 0` in `stage_guard` only: `test_a_clip_run_prints_eleven_stage_lines` FAILs (ten lines, one CLI call). Revert.

- [ ] **Step 6: Run the full unit suite**

Run: `cd skills/explain && python3 -B -m unittest discover -s tests`
Expected: `OK (skipped=43)`, with 743 tests plus the cases this wave adds (about 17). Baseline at the base (run at planning): `Ran 743 tests in 325.182s`, `OK (skipped=43)`. One earlier run at the base stalled after 694 tests for 20 minutes and the rerun passed; if the suite stalls, rerun it once with `-v` before you diagnose anything.

- [ ] **Step 7: Run the film E2E**

Run: `cd skills/explain && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film`
Expected: `OK` with no skip (FilmRenderCase still prints eleven `ok` lines: a film timeline that gains `minText` renders as before).

- [ ] **Step 8: Render one clip by hand**

```bash
cd skills/explain && python3 -B -c '
import json, sys; sys.path.insert(0, "tests")
from test_render_film import film_output, render_output
def clip(out):
    s = json.loads((out / "script.json").read_text()); s["format"] = "clip"
    (out / "script.json").write_text(json.dumps(s))
out = film_output(clip); run = render_output(out); print(run.stdout)
t = json.loads((out / "build" / "timeline.json").read_text()); print(t["format"], t["maxTotalSeconds"], t["minText"])'
```
Expected: eleven stage lines, each `ok`, in the film order; the last line `clip 60 19`. Record the stage lines in the close reason.

- [ ] **Step 9: Commit**

```bash
git add skills/explain/scripts/render.sh skills/explain/video/check_render.sh skills/explain/video/transcript.py skills/explain/tests/test_render.py skills/explain/tests/test_render_film.py skills/explain/tests/test_check_render.py skills/explain/tests/test_transcript.py
git commit -m "feat: explain: a clip takes the film path in render.sh and check_render.sh"
```
