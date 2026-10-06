# Explain lesson — wave `clip-checks` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The guard stage reads its text floor from the timeline's `minText` (19 px for a clip, 14 px for a film), `CodeCard` ends a cut line in a visible `…`, `build-timeline.mjs --check` refuses a source range that holds no cited line, and `rungs/video.md` gives the floor as a number per format.

**Architecture:** `FilmStage.tsx` hands `faultsOf` the `minText` of its timeline props in place of the kit's `MIN_TEXT`. `render.sh` refuses a timeline that has no usable `minText` before the guard pass, so a missing floor cannot turn the size rule off. `lineSpans` of `kit/mono.ts` puts the mark in the last column of a cut line. `validate` of `build-timeline.mjs` adds one check after the source rules: each source entry whose own rules hold needs a cite on its path, inside its range, in any scene. The rung and its drift test then state and pin the per-format floor.

**Tech Stack:** TypeScript (Remotion app, kit modules that Node runs directly), Node ESM (`build-timeline.mjs`), bash (`render.sh`), Python 3 stdlib `unittest`.

Base: 6b334a100861ad2df7b6dfee0d9cdada4d176569
Test runs: scoped per task; full suite once, final task.

**Spec:** `docs/superpowers/specs/2026-10-04-explain-lesson-design.md`. This wave implements the `kit/mono.ts` and `FilmStage.tsx` rows of §6.1, all of §6.2, the `rungs/video.md` item of §6.4, and the source-cite, `test_film_guard.py` and `test_film_kit.py` items of §7.1. Wave map: `docs/superpowers/waves/2026-10-04-explain-lesson.yaml` (wave `clip-checks`, ralph wave 3, epic kp-ipy). The epic comment of 2026-10-06 05:04 (the wave-2 final review) hands over two follow-ups: Task 4 takes the first (`test_rung_drift.py` adds its own `minText` to the film row), Task 1 the second (`FilmStage.tsx` still uses `MIN_TEXT`).

## Global Constraints

- Work on this worktree's branch `explain-lesson/wave-3`. Never commit to `main`. Never stage or commit `.beads/`.
- `EXPLAIN_VIDEO_WORKSPACE` is preset to the lesson branch's own workspace. Never render into `~/karpathy/video-workspace`.
- Run every test command from `skills/explain`, as `python3 -B -m unittest ...`. Run each command that takes more than 2 minutes (a gated E2E, the full suite) with output to a log file, and poll the log with short `sleep 30` and `tail` calls until `OK` or `FAILED`. Never end a turn to wait for a notification.
- Floors, exactly: film `minText` 14 and clip `minText` 19, read from `video/formats.json`. Keep `export const MIN_TEXT = 14` in `kit/palette.ts`: it is the film's value and the author's constant.
- Texts, exactly: `FAIL source <id>: no cite on <path> inside <from>-<to>` (with no format tag); `SMALLTEXT 16.0 px "<t>"`; `guard: FAIL cannot read <out>/build/timeline.json` (the existing line, now also for a bad `minText`); the cut mark is U+2026 `…`.
- The film and brainrot behavior does not change, except for three things: the cut mark, the source-cite check, and the guard's refusal of a timeline with no usable `minText`.
- Files this wave may change: `video/src/FilmStage.tsx`, `video/src/kit/mono.ts`, `video/build-timeline.mjs`, `scripts/render.sh`, `rungs/video.md`, and the tests named in the tasks. No other rung, no `SKILL.md`, no `formats.json` value.
- Code comments follow each file's style: short plain sentences. Each test docstring or comment names the mutation that turns it red, as the test modules do now. Commits: `<type>: explain: <description>`, ending with the session's Co-Authored-By line.

## Review Focus

1. A timeline with no `minText`, or one that is not a number above 0, reaches the guard pass. In JavaScript `px < undefined` is false, so the size rule turns off with no error message. Expected: `guard: FAIL cannot read <timeline>`, and no pass. Pinned by `test_a_timeline_without_a_floor_cannot_be_read` (Task 1).
2. A cite on the first or the last line of a range is read as outside it (an off-by-one), or a cite one line outside is read as inside it. Expected: `from` and `to` are inside; `from - 1` and `to + 1` are not. Pinned by `test_the_range_ends_count` (Task 3).
3. A line that just fits the card gets a mark, or the mark goes after the last column, past the card's padding. Expected: a line of exactly `fitColumns` code points has no mark. A longer line shows `fitColumns - 1` code points and then `…`, so its `textLength` does not change. Pinned by `test_line_spans_mark_a_cut` and `test_a_long_line_ends_in_a_cut_mark` (Task 2).
4. A broken source entry, a scene that is not an object, a URL cite, or a cite whose `line` is not an integer crashes the check, or adds a second line to a fault that already has its own line. Expected: an entry that broke a rule gets no cite line, odd cites count as no cite, and the check never throws. Pinned by `test_a_broken_source_gets_no_cite_line` and `test_odd_cites_and_scenes_do_not_crash` (Task 3).
5. The live run's fold-back changes the clip `minText` in `formats.json`, and the numbers in the rung stay the same. Expected: the rung's two floor sentences are made from the rows. Pinned by `test_the_floor_per_format_matches_formats` (Task 4).

## Beyond the letter of the map (decisions made with no user present)

1. **The `sourceLines: 12` case of `test_film_kit.py`.** `--check` refuses a 13-line clip source, not the kit. Wave 2 pinned that refusal in `test_video_timeline_clip.py::test_clip_source_lines` (commit fdc0c67). `test_film_kit.py` gets the kit side of the number 12 instead: the largest source of each row, at that row's floor, fits the stage (Task 2). Cost if wrong: the done_when names a different test module than the one that holds the refusal.
2. **`render.sh` refuses a timeline with no usable `minText`.** Without this, the guard reads the floor without checking it (Review Focus 1). `render.sh` and the `GuardStageCase` and `FAKE_CHECK_FRAMES` of `test_render_film.py` are outside the map's owns. Cost if wrong: a hand-made timeline needs the key.
3. **Source-cite fixture fixes beyond `changed()`.** A scratch implementation at planning gave 7 failures. They are the two `changed()` cases, and five cases that have three causes. `film_script()` has its only in-range cite in its last scene, so `test_film_scene_count`, `test_an_invalid_format_is_validated_as_a_film` and `test_clip_scene_count` (which slice or copy scene 0) fail. The topic half of `test_film_cites_rule` deletes every cite but keeps the source. `FilmBuildCase.sourced` declares a source with no cite. The fixes are in `test_video_timeline_film.py` alone (Task 3). With them, `test_video_timeline_film`, `_clip`, `test_video_timeline` and `test_film_contract` pass (128 tests, checked in the scratch copy). The template, every fixture and the film E2E script pass as they are: only `templates/video-script.json` declares sources, and its range 138-139 holds two cites. (The spec says `templates/film-script.json`, which kp-5s0 renamed in b368635.)
4. **The cite check is `--check` only** (spec §6.2). Build mode does not run it again: `render.sh` runs `--check` first.
5. **Order and scope of the cite lines.** Only an entry whose own source rules hold gets the cite rule. The cite lines come after the own lines of every source, in entry order, and before the scene-count line. Path equality is exact string equality (`./src/app.py` is not `src/app.py`).
6. **The mark has no colour.** `mono.ts` imports no palette, so the mark is a plain run in the default text colour, and a tint that covers the last column does not colour it. When `columns` is 0 or less, nothing is drawn: there is no room for a mark.
7. **Three more edits to `rungs/video.md`.** The map lists only the floor. The rung's card rule says "with no ellipsis", which is now false. Its source rules do not name the cite rule, and its cannot-read row does not name `minText`. The author reads the rung, never the spec, so Task 4 corrects all three.
8. **One clip case in `test_video_timeline_clip.py`** (outside the owns). It shows that the check runs for every format that has `sources`.

---

### Task 1: the guard reads its floor from the timeline

**Files:**
- Modify: `skills/explain/video/src/FilmStage.tsx` (header `:11-16`, import `:20`, destructure `:70`, effect `:81-86`)
- Modify: `skills/explain/scripts/render.sh` (header `:112-115`, the read in `stage_guard` `:476-487`)
- Modify: `skills/explain/tests/test_film_guard.py` (`GuardLogicCase`, `GuardIsThePipelinesCase`, module docstring)
- Modify: `skills/explain/tests/test_render_film.py` (`GuardStageCase` setUp timeline `:513-519` and a new case after `test_a_timeline_that_cannot_be_read` `:595`; `FAKE_CHECK_FRAMES` `:633`; `GuardPlantCase` `:1096` and the module docstring)

**Interfaces:**
- Consumes: `FilmTimeline.minText: number` (`types.ts:118`, wave 2); `faultsOf(texts, canvas, minText: number): string[]` of `kit/guard.ts` (unchanged); `film_output(edit)`, `render_output(out)` and `GuardPlantCase.stops_at_the_guard(edit, added)` of `test_render_film.py`.
- Produces: FilmStage measures against the floor of its own timeline. The guard stage of `render.sh` refuses a timeline whose `minText` is absent, not a JSON number (`true` is no number), or not above 0.

- [ ] **Step 1: Write the failing tests**

- `test_film_guard.py`, `GuardLogicCase.test_a_16_px_label_passes_a_film_and_fails_a_clip`: with the film and clip `minText` read from `video/formats.json` (path `VIDEO / "formats.json"`), `faultsOf` of one label `"label"` of 16 px at `INSIDE` gives `[]` at the film value and `['SMALLTEXT 16.0 px "label"']` at the clip value. It passes at the base. Red: the clip row's `minText` is 16 or less, or the film row's is above 16.
- `test_film_guard.py`, `GuardIsThePipelinesCase.test_film_stage_hands_the_guard_the_floor_of_the_timeline`: `FilmStage.tsx` with every `//` comment removed holds no `MIN_TEXT`. It holds one `faultsOf(` call, and the third argument of that call is `minText` (taken from the timeline) or `timeline.minText`. Red: the stage passes `MIN_TEXT` or a number literal.
- `test_render_film.py`: the `GuardStageCase` setUp timeline gains `"minText": 14`. The new case `test_a_timeline_without_a_floor_cannot_be_read` has subtests for `minText` removed, `"14"`, `true`, `null`, `0` and `-1`. Each gives `(1, "guard: FAIL cannot read <timeline>\n", "")`, and `self.passes() == []`. `14.5` gives `guard (3 frames): ok`. Red: the read ignores `minText`. `FAKE_CHECK_FRAMES` gains `, minText: 14`, so that the film and clip runs of `SceneRunCase` still reach their guard pass.
- `test_render_film.py`, gated, `GuardPlantCase.test_a_clip_holds_the_example_to_its_floor`: the edit sets `"format": "clip"` in `out/script.json`; then `stops_at_the_guard(edit, added=0)`. The timeline's `minText` is 19. The last line matches `^guard: FAIL frame (\d+) \(scene ([a-z0-9-]+)\): (.+)$`, and `(frame, scene)` is an entry of the run's `checkFrames`. Split the faults on `"; "`, after you remove a ` (+<n> more)` suffix. Each fault must match `^SMALLTEXT (\d+\.\d) px ".+"$` with 14 <= px < 19: text that passes a film fails a clip. The example draws labels of 16 px (`WordBar.tsx:55`, `Film.tsx:192`) and 18 px (`Forms.tsx` `NAME_SIZE`). `FilmRenderCase` is the control: the same example as a film passes the guard. Red: FilmStage passes `MIN_TEXT` (the clip passes the guard, and the run exits 0).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_guard tests.test_render_film`
Expected: FAIL for `test_film_stage_hands_the_guard_the_floor_of_the_timeline` and `test_a_timeline_without_a_floor_cannot_be_read`. Every other case is OK or skipped (the gated classes).

- [ ] **Step 3: Implement**

`FilmStage.tsx`: take `minText` from the timeline props, pass it to `faultsOf`, add it to the dependencies of the layout effect, and stop the import of `MIN_TEXT`. The header comment says that the floor is the timeline's `minText`, from the format row (14 px for a film, 19 px for a clip). `render.sh`: the Python read of `stage_guard` also exits 1 unless `minText` is an `int` or a `float` (no `bool`) and above 0. The header text of the cannot-read line (`:114`) adds that cause.

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command, then `EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film.FilmRenderCase tests.test_render_film.GuardPlantCase` (logged and polled).
Expected: `OK` for both. The second run has no skips, and `test_a_clip_holds_the_example_to_its_floor` passes.

- [ ] **Step 5: Check the broken state**

Put `MIN_TEXT` back as the third argument of `faultsOf` (and its import). Run the gated `GuardPlantCase.test_a_clip_holds_the_example_to_its_floor` and the static case: both FAIL (render.sh exits 0 for the clip). Revert. Then remove the `minText` test from the read of `render.sh`: `test_a_timeline_without_a_floor_cannot_be_read` FAILs. Revert.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/video/src/FilmStage.tsx skills/explain/scripts/render.sh skills/explain/tests/test_film_guard.py skills/explain/tests/test_render_film.py
git commit -m "feat: explain: the guard reads its text floor from the timeline"
```

### Task 2: the code card marks a cut line

**Files:**
- Modify: `skills/explain/video/src/kit/mono.ts` (header `:1-4`, `lineSpans` and its comment `:58-75`)
- Modify: `skills/explain/tests/test_film_kit.py` (`TestMono`: `test_line_spans_cut` `:630`, `test_line_spans_count_code_points` `:654`, `test_line_spans_keep_spaces` `:670`, two new cases; `TestCodeCard`: `test_line_numbers_and_lines` `:972`, `test_a_long_line_is_cut_without_an_ellipsis` `:1011`, `test_a_tint_past_the_cut_is_clipped` `:1045`)

**Interfaces:**
- Consumes: nothing from the other tasks.
- Produces: the signature does not change:

```ts
export const lineSpans = (text: string, tints: readonly Tint[], columns: number): Span[];
```

A text of more than `columns` code points keeps its first `columns - 1` code points and ends in `…` as a run with no colour. A text that fits is unchanged. When `columns` <= 0, the result is `[]`. Neighbours of one colour stay one span, so a plain last run and the mark are one span.

- [ ] **Step 1: Write the failing tests**

- `TestMono.test_line_spans_mark_a_cut`: `"abcd"` at 4 columns gives `[{"text": "abcd"}]` (no mark); `"abcde"` at 4 gives `[{"text": "abc…"}]`; `"abcde"` at 1 gives `[{"text": "…"}]`; `"a\u{1F600}bc"` at 3 gives `[{"text": "a😀…"}]`; `"abcdef"` with a tint 0 to 6 in `A` at 4 gives `[{"text": "abc", "color": A}, {"text": "…"}]`.
- `TestMono.test_the_largest_source_at_the_floor_fits_the_stage`: for the `film` and `clip` rows of `video/formats.json`, `cardHeight({ x: 0, y: 0, width: 600, size: row.minText }, row.sourceLines)` is at most `PALETTE["STAGE"]["height"]` (film 480; clip 396.8, so compare with `assertLessEqual`). Red: a fold-back raises the clip `sourceLines` to 23 (731 px).
- Updates: in `test_line_spans_cut`, 4 columns of `"abcdef"` give `"abc…"`, the tint to 99 gives `[{"text": "ab"}, {"text": "c", "color": A}, {"text": "…"}]`, the tint past the cut gives `[{"text": "abc…"}]`, and 0, -1 and the empty text still give `[]`. Its join rule compares with the new cut text. The second case of `test_line_spans_count_code_points` gives `[{"text": "a…"}]`. The second case of `test_line_spans_keep_spaces` gives `[{"text": "  …"}]`.
- `TestCodeCard`: rename `test_a_long_line_is_cut_without_an_ellipsis` to `test_a_long_line_ends_in_a_cut_mark`. Line 49 holds `long[:40] + "…"` with `textLength` `"492"`, and no other line holds `…`. In `test_line_numbers_and_lines`, each line holds the line when it has 41 code points or fewer, else `line[:40] + "…"`. `test_a_tint_past_the_cut_is_clipped` gives `(text.text, tspan.text, tspan.tail) == (long[:38], long[38:40], "…")` with `textLength` `"492"`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_kit`
Expected: FAIL for the new mark case and every updated cut case. `test_the_largest_source_at_the_floor_fits_the_stage` passes. The `TestCodeCard` cases must run, not skip: the preset workspace has `esbuild`.

- [ ] **Step 3: Implement**

In `lineSpans`, cut to `columns - 1` code points and add the mark when the text is longer than `columns`. Then make the spans as now, with the mark in no tint. Update the comment of `lineSpans`. Add one sentence to the header: a cut line ends in `…`, which takes one column.

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command, then `python3 -B -m unittest tests.test_film_example`.
Expected: `OK` for both. The example's card fits 70 columns, and its lines 138 and 139 have 65 and 69, so the example draws no mark.

- [ ] **Step 5: Check the broken state**

Add the mark after `columns` code points (42 columns in the card): `test_a_long_line_ends_in_a_cut_mark` FAILs (`textLength` 504). Revert.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/video/src/kit/mono.ts skills/explain/tests/test_film_kit.py
git commit -m "feat: explain: the code card ends a cut line in a visible mark"
```

### Task 3: `--check` refuses a source range with no cite

**Files:**
- Modify: `skills/explain/video/build-timeline.mjs` (header: the source lines and the line order `:33-60`; `validate` `:622-650`; a new function beside `checkSources` `:582`)
- Modify: `skills/explain/tests/test_video_timeline_film.py` (`film_script` `:36-64`; `test_film_cites_rule` `:199-209`; `TestFilmSources.with_sources` and `changed` `:306-319`; `test_source_last_line_without_a_final_newline` `:444`; `test_source_with_crlf_line_ends` `:450`; `FilmBuildCase.sourced` `:775-780`; a new class `TestFilmSourceCites`)
- Modify: `skills/explain/tests/test_video_timeline_clip.py` (one case in `TestClipCheck`)

**Interfaces:**
- Consumes: `checkSources(...)` returns the declared lines of each entry, or `undefined` for an entry that broke a rule (unchanged).
- Produces, called by `validate` only, right after `checkSources`:

```js
const checkSourceCites = (sources, declared, scenes, report) => {};
// sources: the script's array; declared: checkSources' result; scenes: script.scenes (any value);
// report(where, cause): validate's reporter. Returns nothing.
```

For each entry whose `declared` value is defined, the check looks at every cite of every scene. A scene counts only when it is an object with an array `cites`. A cite counts only when it is an object, its `path` is the entry's `path` (exact string equality), and its `line` is an integer from `from` to `to`, with both ends included. When no cite counts, the check reports `source <id>` with the cause `no cite on <path> inside <from>-<to>`.

- [ ] **Step 1: Write the failing tests and fix the fixtures**

Fixture fixes in `test_video_timeline_film.py` (each passes at the base):
- `film_script()`: scene `type` cites `cite(line=3, snippet="line 3")` in place of `cite()`.
- `test_film_cites_rule`: the topic half also deletes `script["sources"]`.
- `TestFilmSources.with_sources(sources, cites=())` and `changed(cites=(), **changes)` append `cites` to the cites of scene `type`. `test_source_last_line_without_a_final_newline` passes `cite(path="src/three.py", line=3, snippet="three")`. `test_source_with_crlf_line_ends` passes the same cite for `src/crlf.py` on its passing call.
- `FilmBuildCase.sourced` appends `cite(path="src/" + name, line=1, snippet="one")` to scene `type`.

New class `TestFilmSourceCites(VideoCase)` (`assertFails` checks the exact lines):
- `test_a_source_with_no_cite_inside_fails`: every cite of `film_script()` set to line 1 gives exactly `FAIL source app: no cite on src/app.py inside 3-10`.
- `test_the_range_ends_count`: with one cite on `src/app.py` and the other cites at line 1, line 3 and line 10 pass. Line 2 and line 11 fail with that line.
- `test_a_cite_on_another_path_does_not_count`: the in-range cites get the path `src/other.py`, then `./src/app.py`. Both fail with exactly that line.
- `test_a_cite_in_any_scene_counts`: only scene `ends` keeps its cite at line 3, and the script passes.
- `test_each_source_needs_its_own_cite`: add a second entry `{"id": "late", "path": "src/app.py", "from": 20, "to": 25}`. This gives exactly `FAIL source late: no cite on src/app.py inside 20-25`. A cite at line 22 makes it pass.
- `test_a_broken_source_gets_no_cite_line`: `changed(path="src/missing.py")` gives only its cannot-read line. `changed(**{"from": 1, "to": 21})`, with every cite moved to line 30, gives only `FAIL source app: range 1-21 is 21 lines (max 20, film)`.
- `test_cite_lines_follow_the_sources`: sources `[late (20-25, no cite), app with "from": 70, "to": 73]` and scenes `[:2]` give exactly `FAIL source app: to 73 is outside src/app.py (72 lines)`, `FAIL source late: no cite on src/app.py inside 20-25`, `FAIL script: 2 scenes (needs 3 to 30, film)`. (A range over 20 lines adds a count line, so the broken entry stays at 4 lines.)
- `test_odd_cites_and_scenes_do_not_crash`: scene `type` gains a URL cite `{"path": "https://example.com/a", "snippet": "a"}`, a cite `{"path": "src/app.py", "line": "3", "snippet": "line 3"}` and a `null` cite, and `null` is a fourth scene. The run exits 1, stderr is empty, and no stdout line starts with `FAIL source`. Then move the two integer cites at line 3 to line 1: the stdout lines include `FAIL source app: no cite on src/app.py inside 3-10`, because odd cites count as no cite. Red: the check reads a key of a `null` scene or cite, and Node throws (a stack on stderr).

In `test_video_timeline_clip.py`, `TestClipCheck.test_a_clip_source_needs_a_cite`: `clip_script()` with every cite at line 1 gives exactly `FAIL source app: no cite on src/app.py inside 3-10`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_film tests.test_video_timeline_clip`
Expected: FAIL for each new case that expects a `no cite` line (no such line is printed yet): every new case except `test_a_cite_in_any_scene_counts` and `test_a_broken_source_gets_no_cite_line`, which pass. Every fixture-fixed case passes.

- [ ] **Step 3: Implement**

Add `checkSourceCites` and call it in `validate` for a film-path script that has `sources`. Use the result of `checkSources` there. Build mode stays as it is. In the header, add the cite line to the `FAIL source` causes and to the order sentence: after every source's own lines, and before the scene count. Say that build mode does not run the cite check.

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command, then `python3 -B -m unittest tests.test_video_timeline tests.test_film_contract tests.test_film_example tests.test_format_limits`, then, from `skills/explain`, `node video/build-timeline.mjs --check templates/video-script.json --root ../..` (the root is the repository).
Expected: `OK` for the two test runs. The node command prints nothing and exits 0.

- [ ] **Step 5: Check the broken state**

Let any cite on the path count, whatever its line: `test_the_range_ends_count` and `test_a_source_with_no_cite_inside_fails` FAIL. Revert. Read `c.path` before the object test: `test_odd_cites_and_scenes_do_not_crash` FAILs. Revert.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/video/build-timeline.mjs skills/explain/tests/test_video_timeline_film.py skills/explain/tests/test_video_timeline_clip.py
git commit -m "feat: explain: --check refuses a source range that holds no cited line"
```

### Task 4: the rung gives the floor per format; wave acceptance

**Files:**
- Modify: `skills/explain/rungs/video.md` (source rules `:86-94`; card cut `:238`; text on the stage `:310-313`; the guard `:353`; cannot-read row `:461`; `SMALLTEXT` bullet `:467-468`)
- Modify: `skills/explain/tests/test_rung_drift.py` (module docstring `:22-24`; `FILM_CELLS` comment `:234-235`; `test_film_limits_table_matches_formats` `:605-608`; a new `FilmRungCase` test)

**Interfaces:**
- Consumes: the behavior of Tasks 1 to 3; the `film` and `clip` rows of `video/formats.json`; `min_text()`, `section()` and `read()` of `test_rung_drift.py`.
- Produces: two sentences in `video.md`, each made from the rows (`{film}` and `{clip}` are the rows' `minText`):

```text
FLOOR_DRAW  = "Draw each text at the floor of the format or more on the canvas: {film} px for a film (`MIN_TEXT`) and {clip} px for a clip."
FLOOR_FAULT = "less than the floor of the format: {film} px for a film and {clip} px for a clip."
```

- [ ] **Step 1: Write the failing tests**

- `test_film_limits_table_matches_formats` uses the film row as it is, with its own `minText`, and asserts `row["minText"] == min_text()`. It passes at the base. Red: `formats.json` and `palette.ts` disagree on the film floor. Update the `FILM_CELLS` comment and the module docstring.
- `FilmRungCase.test_the_floor_per_format_matches_formats`: section `"Write the scene"` holds `FLOOR_DRAW` once, and section `"Build and check"` holds `FLOOR_FAULT` once, both made from `formats.json`. Red: a floor in `formats.json` changes and the rung does not.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift`
Expected: FAIL for `test_the_floor_per_format_matches_formats` only.

- [ ] **Step 3: Edit `rungs/video.md`**

- Text on the stage: the bullet "Draw each text at `MIN_TEXT` px or more on the canvas." starts with `FLOOR_DRAW` (14 and 19), and keeps its sentence about the scale. In the next bullet, "`MIN_TEXT` is the limit of the guard" becomes "The floor is the limit of the guard".
- The guard: "a text under `MIN_TEXT`" becomes "a text under the floor of the format".
- `SMALLTEXT` bullet: "less than the floor of section 3." becomes `FLOOR_FAULT`.
- Card cut (`:238`): the card cuts a line to the characters that fit `card.width`, and a cut line ends in `…`, which takes the last column.
- Source rules: add a bullet that the range must hold the `line` of at least one cite with the same `path`, in any scene. Else the cause is `no cite on <path> inside <from>-<to>`. Write it as an inline span that does not start with a stage name, so that the drift test of quoted lines does not apply to it.
- Cannot-read row (`:461`): "or it has no check frames" becomes "or it has no check frames or no text floor".

Keep every new sentence in STE.

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command.
Expected: `OK`. This includes `test_video_md_lints_clean` (`0 errors, 0 warnings`).

- [ ] **Step 5: Check the broken state**

Set the clip `minText` in `video/formats.json` to 20: `test_the_floor_per_format_matches_formats` FAILs. Revert.

- [ ] **Step 6: Run the full unit suite**

Run: `cd skills/explain && python3 -B -m unittest discover -s tests` (logged and polled).
Expected: `OK (skipped=44)`. That is 760 tests plus the cases that this wave adds (about 14; the gated clip guard case is the one new skip). Baseline at the base: `Ran 760 tests`, `OK (skipped=43)`, about 328 s. If the suite stalls, run it once more with `-v` before you diagnose anything.

- [ ] **Step 7: Run the film E2E**

Run: `cd skills/explain && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film` (logged and polled).
Expected: `OK` with no skip. `FilmRenderCase` prints eleven `ok` lines: the template passes the cite check and draws no mark. `GuardPlantCase.test_a_clip_holds_the_example_to_its_floor` passes. Record the `Ran` line of both runs in the close reason.

- [ ] **Step 8: Commit**

```bash
git add skills/explain/rungs/video.md skills/explain/tests/test_rung_drift.py
git commit -m "docs: explain: video rung gives the text floor per format, the cut mark and the cite rule"
```
