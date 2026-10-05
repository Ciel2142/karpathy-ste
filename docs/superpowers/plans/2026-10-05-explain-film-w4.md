# Explain film — wave `film-render` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `render.sh` on the film template renders the worked example of spec §5.3 into a checked `video.mp4` with nine `ok` lines; brainrot and the explainer render as before.

**Architecture:** A film timeline renders through a second composition, `Film`. Its component `FilmStage` (pipeline code) draws one SVG stage that holds the author's `Film`, then places the narration clip of each scene. The picture that the app holds is the worked example in `video/src/film/`, written against the kit and timed by marks; its words are `templates/film-script.json`. `render.sh` picks the composition by the script's format, `check_render.sh` cuts the stills of a film at the timeline's `checkFrames`, and `transcript.py` writes a film scene as its id, its narration and its cites.

**Tech Stack:** bash 3.2 (`/bin/bash` of macOS), Python 3 `unittest`, Node (v25.9.0 on this machine; it runs the kit's `.ts` files as they are), TypeScript 5.9.3, React 19.2.3, Remotion 4.0.532 with Rspack, as pinned in `video/`.

**Spec:** `docs/superpowers/specs/2026-10-05-explain-film-design.md` — this wave implements §5.1 (the stage), §5.3, §7.4, §7.5, the stale-file sentence of §7, the film cases and the two example tests of §9.1, and the first bullet of §9.2 without the `scene` and `guard` stages (nine lines, not eleven). Wave map: `docs/superpowers/waves/2026-10-05-explain-film.yaml`, wave `film-render` (ralph wave 4, epic `kp-osb`). Coverage: waived by the map.

Base: 82f0dd46c49432a0036e768d6d23e2695fc6291b

Test runs: scoped per task; full suite once, final task.

## Global Constraints

- Work on this wave's own branch and worktree. Never commit to `main`, to `feat/explain-brainrot`, or directly to `feat/explain-film`. Never stage `.beads/`.
- A gated run (`EXPLAIN_VIDEO_E2E=1`) and every `render.sh` run are allowed only with `EXPLAIN_VIDEO_WORKSPACE` set to the film branch's own workspace. Never render into `~/karpathy/video-workspace`: other sessions use it. Each such command below starts with `test -n "$EXPLAIN_VIDEO_WORKSPACE"` and prints the path; a command that ends there with no output means the variable is not set: do not render, and report it.
- No install from a test run. If a class is skipped for missing packages, run `scripts/video-workspace.sh --engine say` once, alone, in that workspace.
- Files this wave may change, under `skills/explain/`: `scripts/render.sh`, `video/check_render.sh`, `video/transcript.py`, `video/src/Root.tsx`, `video/src/types.ts`, new `video/src/FilmStage.tsx`, new `video/src/film/` (flat: `Film.tsx`, `script.gen.ts`, further `<Name>.tsx` files of the picture), new `templates/film-script.json`, `tests/test_transcript.py`, `tests/test_check_render.py`, new `tests/test_render_film.py`, new `tests/test_film_example.py`; and the docstrings only of `video/check_budgets.py` and `video/narrate.py` (decision 7 below). Nothing else: no kit file, no `build-timeline.mjs`, no `formats.json`, no rung file, no new dependency.
- Stage lines: a film run prints nine in this wave (the explainer's nine names), brainrot ten, the explainer nine. The names `STAGES`, `stage_lines`, `render_functions`, `E2E`, `E2E_REASON`, `EXPLAIN`, `RENDER_SH`, `RENDER_TIMEOUT`, `render_env`, `workspace` stay importable from where they are.
- Every pre-existing test case passes unchanged. An explainer or brainrot transcript, still list and render command are the same bytes as at the base.
- Tests: `unittest`, run from `skills/explain`. Each test names the mutation that turns it red, as the files do today. Each new assertion is seen to fail before the code exists; one that passes at once is checked by applying its named mutation, seeing the failure, and reverting.
- Baseline at the base (run at planning): `python3 -B -m unittest discover -s tests` gives `Ran 625 tests`, `OK (skipped=33)`.
- Commits: `<type>: explain: <description>`, ending with the attribution line of the session.

## What the closed waves left for this one

Read from the close notes of `kp-sd3`, `kp-fzq` and `kp-xdd`. Each is placed in a task.

- A `Source` is made with `sourceFromDisk` inside the render of `FilmStage`, memoised on the timeline, never in `Root.tsx`, `defaultProps` or `calculateMetadata`: Remotion passes those through JSON, and a copy of a `Source` makes `CodeCard` throw. `FilmStage` and the scene share one bundle, so one `kit/source` module (Task 5).
- No test feeds a timeline built by the real tool to the kit's `makeAt` (Task 4).
- The docstring of `check_budgets.py`, the comments of `render.sh` and one docstring line of `narrate.py` do not name the film (Task 3).
- The tail of a Kokoro clip against the 12-frame pause is not measured (`kp-c04`, spec §7.1); the first film render measures it (Task 5 Step 8).
- The Remotion project of a run is `$run`. This wave adds no new step with cwd `$run`: the film render is the one `exec` of `stage_render`, which `test_render_sh_waits_for_a_cli_that_outlives_the_signal` already covers.
- `video/public` never reaches a run directory. The film needs no static file: its fonts are system fonts, and the headless browser draws `MONO` in Menlo.
- A gated test renders with `env=render_env(...)` and finds the workspace with `workspace()` (Task 5).

## Beyond the letter of the spec

Decisions that the spec and the map leave open, made here so that every task builds the same thing.

1. Until the `scene` stage exists (wave `film-scene-stage`), `render.sh` draws the checked-in example for every film script. A film script with other scene ids stops in the render stage (`render: FAIL remotion render exit 1`, the `MARK scene <id>:` message in the log lines below it). Only the template is supported in this wave, and no rung file names the film yet.
2. `clear_stale` removes `build/guard.mp4` for every format. The spec asks it of a film run; no other format writes that file, so one unconditional removal is the simpler rule.
3. `check_render.sh` takes the stills of a timeline from `checkFrames` when the timeline's `format` is `film`. A film timeline without `checkFrames`, or with an entry whose scene is not in `scenes`, is unreadable (the exit 2 line that exists today).
4. A film scene without a `cites` key has no cites in the transcript: `--check` passes such a scene for a `topic` or `conversation` subject.
5. `FilmStage` paints the ground (`C.bg`) on its `<svg>`, so a scene draws no ground of its own.
6. The template's subject is the directory `skills/explain` and its `provenance.root` is `.` (the repository root; an author or a test replaces it by an absolute path). Its cite and source paths start at the repository root.
7. Docstring-only edits outside the map's `owns` list: `video/check_budgets.py` and `video/narrate.py`, which the close note of `film-timeline` hands to this wave.
8. The always-run tests of the film branch of `render.sh` live in `tests/test_render_film.py` and run single functions of the script through `render_functions` of `tests/test_render.py`. `test_render.py` itself is not changed.
9. Until `check_scene.py` exists, one test of `test_film_example.py` holds the example to the directory, import and token rules of spec §4.3 and §7.2. Wave `film-scene-stage` may replace it by the tool.
10. The example obeys the three guard rules of spec §7.3 at its checked frames although no stage measures them yet: wave `film-guard` must find the unedited example clean.

## The worked example

One film of about 40 s: how `/explain` checks an artifact before handoff. One picture for the whole film; objects stay and change; the stage is never cleared. Eight scenes, each one or two sentences, one motion for each sentence. The ids, the source and the objects are fixed here; the narration wording is the implementer's, under the prose lint.

Objects that stay on the stage once drawn: the prompt line, the three forms, the artifact card, the row of four gates, the code card.

| Scene id | The voice says | The picture changes | Cite (verified at planning) |
|---|---|---|---|
| `subject` | `/explain` gets a subject and makes an artifact that must pass four checks before handoff | The prompt `/explain <subject>` is written in mono type; the subject is yellow | `verify.sh:2` "the four checks an explain artifact must pass before handoff" |
| `forms` | The artifact is a sheet, a page or a video | The prompt moves to the top left and stays; three forms appear in a row; the page becomes blue (chosen) | `verify.sh:7` "all checks of the rung passed (sheet, page: four; video: three)" |
| `artifact` | The check script reads one file | The chosen form becomes the artifact card `index.html`; the other two forms go muted | `verify.sh:4` "verify.sh <index.html>" |
| `gates` | It prints one line for each check, in order | A line is drawn from the card through four gates: self-contained, render, citations, prose | `verify.sh:11` "stdout carries one line per check, in this order" |
| `cite` | The citations check reads the cited line of the source file | The citations gate becomes blue; the code card of source `check` opens below the gates | `cite_check.py:5` "Exit 0 when every citation holds, 1 with one failure per line" |
| `holds` | The snippet must be on that line; if one word is different, the check fails | A tint marks `_normalize(snippet)` and `lines[line_no - 1]` on line 138 and a green check is drawn; then a red band on line 139 and a red cross | `cite_check.py:138` "if _normalize(snippet) not in _normalize(lines[line_no - 1]):" and `:139` "snippet not found on that line" |
| `prose` | The prose check reads each sentence; a descriptive sentence has at most 25 words | The code card fades; the prose gate becomes blue; a bar of 25 cells fills and stops green | `skills/ste/SKILL.md:52` "Descriptive sentence: at most 25 words (6.3)." |
| `handoff` | Every check runs, also after a failure; when all pass, the artifact is ready | Each gate gets a green check in turn; the artifact card moves past the last gate and becomes green | `verify.sh:22` "Every check runs even after an earlier one failed." |

`verify.sh` and `cite_check.py` are `skills/explain/scripts/verify.sh` and `skills/explain/scripts/cite_check.py`. Spec §5.3 allows only these two files and `skills/ste/SKILL.md` in cites and sources: no wave of this feature edits them.

The one source: id `check`, path `skills/explain/scripts/cite_check.py`, from 138, to 139 (lines of 65 and 69 characters).

Rules of the picture (spec §5.1, §5.2, §6, §7.2, §7.3, §8.1):

- `Film` returns SVG elements only and reads the frame with `useCurrentFrame()`. It takes no input besides its props.
- A scene file imports only `react`, the five names of `remotion` (`useCurrentFrame`, `interpolate`, `Easing`, `spring`, `interpolateColors`), `../kit`, `./script.gen` and `./<Name>` for a file of the directory.
- Every motion starts at a mark: `at(id)`, `at(id, { sentence })`, `at(id, { word })`, `at.said(id)`, `at.end(id)`. A frame number written by hand is a length, never a position. A word mark is an estimate; a motion that needs an exact frame uses a sentence mark.
- Text is a label, a source line in the code card, or a claim under test, drawn with `Mono`, `Sans` or `CodeCard` at `MIN_TEXT` (14 px) or more. A list of sentences is a fault. Words of a source line are marked with a `Tint` or a `Band`, never with a second text on top.
- A colour has one meaning: yellow the subject, blue chosen, green pass, red fail. Colours come from `C`.
- At each checked frame (the middle of each sentence, the last frame of each scene) every text of opacity 0.1 or more is inside the canvas and does not overlap another text by more than 2 px on both axes. An object comes in with a fade or from inside the canvas, and a cross-fade ends before a checked frame: a motion of at most 20 frames from its mark ends before the middle of a sentence of 1.4 s or more.
- `tsc` runs strict with `noUnusedLocals`: an unused local fails.
- The example is also the copy an author starts from: name the objects in the film's own terms and comment each scene block with its id.

## Review Focus

Failure modes that the spec implies and that are most likely to cost a person something. Each has its test in the task named.

1. `FilmStage` starts each narration clip at the scene start and not `leadFrames` later. The `sync` stage passes (6 frames are inside its 0.25 s tolerance), and every mark is 0.2 s late against the voice. Task 5: `test_voice_starts_at_the_lead`.
2. A film scene with no `cites` key (a `topic` subject): the script passes `--check` and the transcript must still be built. Task 1: `test_film_scene_without_a_cites_key`.
3. The `end` still of the last scene is the last frame of the film; a seek past the end extracts nothing. Task 2 pins the frame; Task 5 `test_stills_are_the_check_frames` needs the file.
4. An output directory that holds the stills of an explainer run or a `build/guard.mp4` of an earlier film run. Task 3: `test_stale_guard_video_is_removed`.
5. A film timeline whose `checkFrames` names a scene that the timeline does not hold (a timeline edited by hand, or a build fault): one line and exit 2, no silent skip of a still, and the review directory keeps its files. Task 2: `test_broken_film_timeline_is_unreadable`.

Accepted, not tested: decision 1 (a film script that is not the template).

---

### Task 1: `transcript.py` writes a film scene

**Files:**
- Modify: `skills/explain/video/transcript.py` (docstring lines 2-12; `Cites.__init__` at 82-89; `render_scene` at 181-194; the nav of `render_page` at 227; `render_narration` at 247-251)
- Test: `skills/explain/tests/test_transcript.py` (new class `FilmTest(TranscriptCase)` after `OutputTest`)

**Interfaces:**
- Consumes: nothing.
- Produces, for Tasks 4 and 5:

  ```python
  def is_film(script) -> bool               # the script's own "format" is "film"
  def scene_heading(script, scene) -> str   # the scene id for a film, else scene["props"]["title"]
  ```

  and the film page: for each scene `<section id="<id>">` with `<h2><id></h2>`, one `<p>` of narration, then `<ul class="cites" data-ste="skip">`.

- [ ] **Step 1: Write the failing tests.** `FilmTest` gets a helper `film(self, kind="file")`: a film script (`"format": "film"`) rooted at `self.dir` with three scenes `type`, `forms`, `ends`, each with a narration and one cite on `src/big.txt` line 3 "alpha beta"; the header comes from `small_script`.

  - `test_film_section_is_id_narration_and_cites` — the section ids are the scene ids in order; the `<h2>` of each is its id; each holds one `<p>` whose text is the narration, with a backtick span as `<code>` and `<b> & "q"` escaped; its cites are the scene's cites; the page holds no `<figure>` and no `<ul>` other than the cite lists. Red: a film scene is sent through `BODIES` (exit 2, `KeyError 'component'`).
  - `test_film_nav_and_narration_md_use_the_id` — the text of each `<nav>` link is the scene id; the `##` lines of `narration.md` are the ids, each followed by its narration unchanged. Red: `props["title"]` is read for a film.
  - `test_film_cite_labels_come_from_the_cites_alone` — two scenes cite `a/util.py` and `b/util.py` (files made in `self.dir`): the visible labels are `a/util.py:1` and `b/util.py:1`. Red: `Cites` reads `component` of a film scene.
  - `test_film_page_has_no_format_row_and_a_landscape_video` — no `<dt>Format</dt>`, no `<dt>Background</dt>`, `<video controls src="video.mp4"></video>`, also with `--background x.mp4`; `--narrator say` gives `<dt>Narrator</dt><dd>say</dd>`. Red: a film is laid out as brainrot.
  - `test_film_scene_without_a_cites_key` — `film(kind="topic")` with `cites` deleted from one scene: exit 0, and that section has an empty cite list. Red: `scene["cites"]`.
  - `test_film_scene_without_narration_exits_two` — a scene without `narration`, and one without `id`: exit 2 and one stderr line that starts `transcript.py: script does not match the contract:`. Red: the film body reads `narration` or `id` with a default and writes a page. This case passes at the base (every film script ends in that line there): apply its mutation after Step 3.
  - `test_film_transcript_passes_verify` — `verify.sh` on the film page prints `self-contained: ok`, `citations: ok`, `prose: ok`. Red: a section without its cites, or a heading that fails the lint.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_transcript`
  Expected: `FAILED`; six `FilmTest` cases fail on `script does not match the contract: KeyError 'component'`; `test_film_scene_without_narration_exits_two` and every other case pass.

- [ ] **Step 3: Change `transcript.py`.** Contract:
  - `is_film` reads the script's own `format` key; `scene_heading` gives the heading of the section, of the nav link and of the `##` line of `narration.md`.
  - A film scene's section is the heading, the narration paragraph (`inline`), and the cite list of its own cites. `component` and `props` of a film scene are not read. An absent `cites` is no cites.
  - `Cites` builds its labels from the cites of every scene; it adds the code source path only for a scene of a script that is not a film.
  - A film page has no Format row, no Background row and no class on `<video>`; `--background` is ignored, as for the explainer.
  - A film scene without `id` or `narration` ends in the existing one-line contract error, exit 2.
  - The module docstring names the film page. Explainer and brainrot output does not change.

- [ ] **Step 4: Run the tests and see them pass; check the mutation.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_transcript`
  Expected: `OK`. Then read the narration of a film scene with a default of `""`, see `test_film_scene_without_narration_exits_two` fail, and revert.

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/video/transcript.py skills/explain/tests/test_transcript.py
  git commit -m "feat: explain: transcript.py writes a film scene as its id, narration and cites"
  ```

---

### Task 2: `check_render.sh` cuts the stills of a film at `checkFrames`

**Files:**
- Modify: `skills/explain/video/check_render.sh` (header comment lines 25-30; `read_timeline` at 80-92)
- Test: `skills/explain/tests/test_check_render.py` (`StillFramesCase` at 196-249; new class `FilmTimelineFaultCase`)

**Interfaces:**
- Consumes: the film timeline of `build-timeline.mjs`: `checkFrames: [{ frame, scene, still }]`, `still` being `s<k>` or `end` (fixture `tests/fixtures/film-timeline.json`).
- Produces, for Task 5: the still of a film entry is `still-<NN>-<scene>-<still>.png`, `<NN>` the two-digit position of the scene in `scenes` from 01, cut at the entry's `frame`.

- [ ] **Step 1: Write the failing tests.** In `StillFramesCase`, split `still_frames` so that its second half is `read_timeline_lines(self, timeline: dict) -> list`, which runs `read_timeline` on any timeline object; `still_frames` builds its object and calls it.

  - `test_film_stills_are_the_check_frames` — on the object of `fixtures/film-timeline.json` the lines are exactly `30 324 1280 720`, `43 still-01-type-s1.png`, `118 still-01-type-s2.png`, `152 still-01-type-end.png`, `196 still-02-checks-s1.png`, `271 still-02-checks-s2.png`, `323 still-02-checks-end.png`. The last frame is `totalFrames - 1`. Red: no film branch (a non-zero exit on `cueFrames`), a still numbered by its place in `checkFrames`, or a frame moved by the cue or fade offsets.
  - `test_a_timeline_that_is_not_a_film_ignores_check_frames` — the lead-6 scene object of `test_lead_6_scene_still_after_the_fade` with `"format": "brainrot"` and a `checkFrames` list added gives the lines of that test. Red: the branch is taken on the presence of `checkFrames`. This case passes at the base: apply its mutation after Step 3.

  `FilmTimelineFaultCase` runs the whole script, as `ReviewDirNameCase` does (a file named `video.mp4`, a temporary `EXPLAIN_VIDEO_WORKSPACE`), with a `review/keep.png` planted:

  - `test_broken_film_timeline_is_unreadable` — the fixture with one `checkFrames` entry renamed to scene `nope`, and the fixture without `checkFrames`: exit 2, empty stdout, one stderr line that starts `check_render.sh: cannot read timeline `, and `keep.png` is still there. Red: an unknown scene is skipped, or the review directory is emptied before the timeline is read. This case passes at the base (no film timeline is readable there): apply its mutation after Step 3.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_check_render`
  Expected: `FAILED`; `test_film_stills_are_the_check_frames` fails; `CheckRenderCase` is skipped.

- [ ] **Step 3: Change `read_timeline`.** Contract:
  - The first line does not change.
  - For a timeline whose `format` is `film`: one line for each entry of `checkFrames`, in order, `<frame> still-<NN>-<scene>-<still>.png`. An entry whose scene is not in `scenes`, or a missing `checkFrames`, makes the read fail, which gives the existing `check_render.sh: cannot read timeline <path>: <cause>` and exit 2.
  - For any other timeline the lines are those of the base.
  - The header comment says what the review directory holds for a film: one still for the middle of each sentence (`still-NN-<scene-id>-s<k>.png`) and one for the last frame of each scene (`still-NN-<scene-id>-end.png`), at the frames of `checkFrames`.

- [ ] **Step 4: Run the tests and see them pass; check the two mutations.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_check_render`
  Expected: `OK (skipped=5)`. Then, one at a time and reverted: take the film branch on the presence of `checkFrames` and see `test_a_timeline_that_is_not_a_film_ignores_check_frames` fail; make the film branch skip an unknown scene and see `test_broken_film_timeline_is_unreadable` fail.

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/video/check_render.sh skills/explain/tests/test_check_render.py
  git commit -m "feat: explain: check_render.sh cuts the stills of a film at its check frames"
  ```

---

### Task 3: `render.sh` renders a film through composition `Film`

**Files:**
- Modify: `skills/explain/scripts/render.sh` (header comment lines 2-52; the `fmt` global at 131; the comment at 227; `clear_stale` at 237-241; the CLI call of `stage_render` at 362-363)
- Modify: `skills/explain/video/check_budgets.py` (docstring lines 6-17), `skills/explain/video/narrate.py` (the docstring of `narrate`, lines 316-317): text only
- Create: `skills/explain/tests/test_render_film.py`

**Interfaces:**
- Consumes: `render_functions(names) -> str` of `tests/test_render.py` (the shell text of named functions of `render.sh`).
- Produces, for Task 5: for `fmt=film` the render command is `render Film <out>/video.mp4 --props <out>/build/timeline.json`; `clear_stale` also removes `<out>/build/guard.mp4`. In `test_render_film.py`:

  ```python
  def run_functions(tmp: Path, names: list, setup: str) -> subprocess.CompletedProcess
  ```

  It runs `/bin/bash -c`, with cwd `tmp`, on `set -eu`, then `render_functions(names)`, then the shell text `setup`.

- [ ] **Step 1: Write the failing tests.** The module docstring says that the file holds the film cases of `render.sh`: an always-run class on single functions, and (Task 5) the gated render of the template. Class `FilmFunctionCase`, in a temporary directory:

  - `test_a_film_renders_composition_film` — `stage_render` (with `fail` and `now`) runs with `RATIO_LIMIT=2.0`, `video_s=3.000`, `out`, `run` and a fake `remotion` that appends its arguments as one JSON list to a file; `out/build/timeline.json` holds one scene with `audio/s1.say.wav`, and that file exists. For `fmt=film` the arguments are `["render", "Film", "<out>/video.mp4", "--props", "<out>/build/timeline.json"]`; for `fmt=explainer` and `fmt=brainrot` the second is `Explain`. Each run prints one `render (` line that ends `: ok`. Red: the composition is the literal `Explain`.
  - `test_stale_guard_video_is_removed` — `clear_stale` on an output directory with `video.mp4`, `review/still-01-intro.png`, `build/guard.mp4` and `build/timeline.json`: the first three are gone, `review/` is an empty directory, `build/timeline.json` stays. Red: `guard.mp4` is left (the base), or all of `build/` goes.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render_film`
  Expected: `FAILED`; the film case of the first test gets `Explain`, and the second finds `build/guard.mp4`.

- [ ] **Step 3: Change `render.sh`.** Contract:
  - `stage_render` renders composition `Film` when `$fmt` is `film`, else `Explain`. Nothing else of the command changes: the `exec` in the subshell, cwd `$run`, the log.
  - `clear_stale` also removes `$out/build/guard.mp4` (decision 2).
  - No other stage changes: a film takes the default narration speed, has no background stage and passes no `--background`.
  - Comments: the header names three formats (`explainer` when absent, `film`, `brainrot`), says that a film run has the nine stages of the explainer until the `scene` and `guard` stages exist, gives the film limits (scene <= 30 s, total <= 150 s), the composition of each format, the film stills, and `build/guard.mp4` among the removed files; the comments at `fmt=` and in `stage_script` name the film.
  - `check_budgets.py`: the docstring names the film limits (30 and 150) and the tag `, film`. `narrate.py`: the leftover words file is of "an earlier brainrot or film run". No code changes in either.

- [ ] **Step 4: Run the tests and see them pass.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render_film tests.test_render tests.test_check_budgets tests.test_narrate`
  Expected: `OK`; the gated cases are skipped.

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/scripts/render.sh skills/explain/video/check_budgets.py skills/explain/video/narrate.py skills/explain/tests/test_render_film.py
  git commit -m "feat: explain: render.sh renders a film through composition Film"
  ```

---

### Task 4: the words of the worked example

**Files:**
- Create: `skills/explain/templates/film-script.json`
- Create: `skills/explain/video/src/film/script.gen.ts` (written by the tool, checked in)
- Create: `skills/explain/tests/test_film_example.py`

**Interfaces:**
- Consumes: the film page of Task 1; `build-timeline.mjs` (`--check`, `--types`, build mode) and `narrate.py` of wave `film-timeline`; `makeAt` of `video/src/kit/marks.ts`; `run_node`, `kit_url` of `tests/test_film_kit.py`; `NARRATE_PY` of `tests/test_narrate.py`.
- Produces, for Task 5: `templates/film-script.json` with the eight scene ids and the source id `check` of the storyboard, and

  ```ts
  // video/src/film/script.gen.ts
  export type SceneId = "subject" | "forms" | "artifact" | "gates" | "cite" | "holds" | "prose" | "handoff";
  export type SourceId = "check";
  export type Props = FilmProps<SceneId, SourceId>;
  ```

  In `test_film_example.py`: `REPO = EXPLAIN.parent.parent`, `FILM_TEMPLATE`, `FILM_DIR = EXPLAIN / "video" / "src" / "film"`, and `template_script() -> dict` (the template with `provenance.root` set to `str(REPO)`).

- [ ] **Step 1: Write the failing tests.** The module docstring says that the file keeps the worked example true (spec §5.3). Class `ExampleScriptCase`:

  - `test_template_passes_check` — `build-timeline.mjs --check` on `template_script()` with `--root REPO`: exit 0, empty stdout. Red: a narration over 45 words, a scene with a `component`, a source range outside the file.
  - `test_generated_names_equal_the_checked_in_file` — `build-timeline.mjs --types <template> <tmp>/script.gen.ts` writes the bytes of `FILM_DIR / "script.gen.ts"`. Red: a scene id renamed in the template only, or the checked-in file edited by hand.
  - `test_template_transcript_passes_the_cite_check` — `transcript.py` on `template_script()`, then `scripts/verify.sh` on the page: `self-contained: ok`, `citations: ok`, `prose: ok`. Then, with one word of the first cite's snippet changed, stdout holds the line `citations: FAIL 1 failure(s)`. Red: a cite that the file does not hold, a narration sentence that fails the lint, or a check that passes on a wrong cite.
  - `test_cites_and_sources_name_only_the_stable_files` — every cite path and every source path is one of `skills/ste/SKILL.md`, `skills/explain/scripts/verify.sh`, `skills/explain/scripts/cite_check.py`; the subject kind is `directory`; the format is `film`. Red: a cite on a file that a later wave edits (`skills/explain/rungs/video.md`).

  Class `ExampleTimelineCase`: `setUpClass` narrates `template_script()` with `narrate.py --engine say` into a temporary directory and builds the timeline with the real tool (`--root REPO`), as `FilmContract` of `test_film_contract.py` does.

  - `test_example_narrates_and_builds` — both exit 0; the timeline's `format` is `film`; its scene ids are the template's; `sources.check` has `from` 138 and the two lines of the file. Red: the build fails on the words files, or the source is not carried.
  - `test_example_is_about_40_s` — `totalFrames / fps` is from 30 to 50. Red: the example is cut to a stub, or grows past the length that spec §5.3 names.
  - `test_kit_marks_read_the_built_timeline` — Node imports `marks.ts` and calls `makeAt(timeline.scenes)`. For every scene: `at(id)` is `from + leadFrames`; `at(id, { sentence: k })` is `from + sentences[k - 1]` for every k; `at.said(id)` is `from + leadFrames + audioFrames`; `at.end(id)` is the `from` of the next scene, or `totalFrames`; and for every word that holds a letter or a digit, `at(id, { word, nth })` is `from` plus that word's `from`, `nth` being its count among the words of the scene that are equal after lowercasing and removing every character that is not a letter or a digit. Red: the build writes a scene key under a name that `MarkScene` does not read, so a mark is `NaN` or throws.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_film_example`
  Expected: errors: `templates/film-script.json` does not exist.

- [ ] **Step 3: Write `templates/film-script.json`.** Contract:
  - Top level: `"format": "film"`; `"title": "How explain checks an artifact"`; subject `skills/explain`, kind `directory`; `provenance` with `root` `.`, `commit` the short SHA of `HEAD`, `dirty` `no`, `date` of the day, `source` naming the three files, and a `not_covered` sentence (the rungs, the build procedure, the render check, the lint rules); `sources` with the one entry of the storyboard; `scenes`.
  - Eight scenes with the ids of the storyboard, in its order. Each has `id`, `narration` and `cites`; `pause` only where the picture needs more silence than 12 frames.
  - A narration is one or two sentences that say what its row says, at most 45 words, in the STE profile (present tense, active voice, a descriptive sentence of at most 25 words). A word that the picture will take a mark from is a whole token of the narration.
  - Each scene carries the cite of its row: `path`, `line`, `snippet` as the table gives them.

- [ ] **Step 4: Write `script.gen.ts` with the tool.**

  Run: `cd skills/explain && mkdir -p video/src/film && node video/build-timeline.mjs --types templates/film-script.json video/src/film/script.gen.ts && cat video/src/film/script.gen.ts`
  Expected: five lines; the third is `export type SceneId = "subject" | "forms" | "artifact" | "gates" | "cite" | "holds" | "prose" | "handoff";` and the fourth `export type SourceId = "check";`.

- [ ] **Step 5: Run the tests and see them pass.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_film_example tests.test_film_kit.TestKitCompiles`
  Expected: `OK`, no skip: the app still compiles with `src/film/script.gen.ts` in it. If the prose line fails, reword the sentence that `verify.sh` names and run again.

- [ ] **Step 6: Commit.**

  ```bash
  git add skills/explain/templates/film-script.json skills/explain/video/src/film/script.gen.ts skills/explain/tests/test_film_example.py
  git commit -m "feat: explain: the film template and its generated scene names"
  ```

---

### Task 5: the stage, the picture and the end-to-end render

**Files:**
- Modify: `skills/explain/video/src/types.ts` (after line 86), `skills/explain/video/src/Root.tsx`
- Create: `skills/explain/video/src/FilmStage.tsx`, `skills/explain/video/src/film/Film.tsx`, and further `skills/explain/video/src/film/<Name>.tsx` files where `Film.tsx` would pass 300 lines (one file for each group of objects)
- Test: `skills/explain/tests/test_film_example.py` (class `ExampleSceneCase`), `skills/explain/tests/test_render_film.py` (gated class `FilmRenderCase`)

**Interfaces:**
- Consumes: Tasks 1 to 4; `template_script`, `FILM_DIR` of `tests/test_film_example.py`; from the kit `makeAt` (`./kit/marks`), `sourceFromDisk` (`./kit/source`), `C`, `STAGE` and the scene surface of `./kit`; `kit_app`, `needs_kit_tools` of `tests/test_film_kit.py`; `video_size` of `tests/test_render_brainrot.py`; `differing_pixels` of `tests/png_diff.py`; `voiced_windows` of `video/verify_sync.py`; `split_sentences` of `video/narrate.py`.
- Produces:

  ```ts
  // video/src/types.ts
  export type FilmScene = { id: string; from: number; durationInFrames: number; leadFrames: number;
                            audioFrames: number; audio: string; sentences: number[];
                            words: { text: string; from: number; to: number }[] };
  export type CheckFrame = { frame: number; scene: string; still: string };
  export type FilmSource = { path: string; from: number; lines: string[] };
  export type FilmTimeline = { format: "film"; engine: string; fps: number; width: number; height: number;
                               totalFrames: number; maxSceneSeconds: number; maxTotalSeconds: number;
                               sources: Record<string, FilmSource>; checkFrames: CheckFrame[];
                               scenes: FilmScene[] };
  // video/src/FilmStage.tsx
  export function FilmStage(timeline: FilmTimeline): ReactElement;
  // video/src/film/Film.tsx
  export function Film(props: Props): ReactElement;   // Props from ./script.gen
  ```

  ```python
  # tests/test_render_film.py
  def render_film() -> tuple   # (output dir, CompletedProcess) of the one template render of this process
  ```

- [ ] **Step 1: Write the failing tests.** `ExampleSceneCase` in `test_film_example.py`:

  - `test_the_app_compiles_with_the_example` (`needs_kit_tools`) — `src/FilmStage.tsx` and `src/film/Film.tsx` are files, and `tsc` in a `kit_app()` copy gives `(0, "")`. Red: a type error in the stage or the picture, an unused local, a mark on a scene id that the script does not have (TS2345).
  - `test_the_example_follows_the_scene_rules` — `FILM_DIR` holds only files named `*.ts` or `*.tsx` (hidden files apart) and no directory; `Film.tsx` holds `export function Film(`; in every file each `from "<source>"` names an allowed source, each name imported from `remotion` is an allowed name, and no refused token appears. The lists are those of spec §5.1 and §7.2:

    ```
    sources   react | remotion | ../kit | ./script.gen | ./<Name> for a file <Name>.ts or <Name>.tsx of the directory
    remotion  useCurrentFrame interpolate Easing spring interpolateColors
    tokens    require(  import(  fetch(  foreignObject  dangerouslySetInnerHTML  clipPath  href  http://  https://
              @ts-nocheck  @ts-ignore  @ts-expect-error  as unknown  <any>
    tokens, only when the next character is not a letter or a digit:   <mask  <use  <image  as any  : any
    ```

    Red: an import of `./kit/marks` or of `Sequence`, or a `: any`. After Step 5, plant `import { Sequence } from "remotion"` in `Film.tsx`, see this test fail, and revert.

  `FilmRenderCase` in `test_render_film.py`, gated by `E2E`. `render_film()` follows `render_brainrot` of `test_render_brainrot.py`: a temporary output directory removed at exit, `template_script()` as `script.json`, `render.sh <out> --engine say` with `env=render_env()` and `RENDER_TIMEOUT`, cached for the process.

  - `test_film_prints_nine_ok_lines` — exit 0 and nine stage lines that match, in order: `script: ok (8 scenes)`, `workspace: ok /…`, `narration (say): ok`, `timeline (8 scenes, <d.d> s): ok`, the `render (…): ok` line with its ratio, `container: ok (<d.dd> s)`, `sync: ok`, `stills (<n>): ok /…`, `transcript: ok`; the scene count comes from the template. Red: a film is rendered as `Explain`, or a stage of the film path fails.
  - `test_render_used_the_callers_workspace` — the second stage line is `workspace: ok <workspace()>`. Red: the helper drops `EXPLAIN_VIDEO_WORKSPACE`.
  - `test_stills_are_the_check_frames` — the names in `review/` are, for scene n of the template with K sentences (`split_sentences` of its narration), `still-<nn>-<id>-s1.png` to `-s<K>.png` and `still-<nn>-<id>-end.png`; each file has bytes; the count of the `stills (` line is their number. The expected names come from the template, not from the render's timeline. Red: stills by scene and cue, a missing `end` still of the last scene, a lost sentence.
  - `test_container_is_landscape` — `video_size(out / "video.mp4")` is `1280x720`. Red: composition `Film` takes the size of another format.
  - `test_transcript_is_the_film_page` — the section ids of `index.html` and their `<h2>` texts are the template's scene ids; no `<dt>Format</dt>` and no `<dt>Background</dt>`; `<dt>Narrator</dt><dd>say</dd>`; `verify.sh` on the page prints its three `ok` lines. Red: the transcript stage passes `--background`, or leaves the Narrator row `pending`.
  - `test_film_speaks_at_speed_1` — `audio/` holds one `*.say.txt` for each scene, each with `\nspeed=1.0\nmode=sentences\n`. Red: `render.sh` gives a film the brainrot speed.
  - `test_voice_starts_at_the_lead` — with `voiced_windows`, for every scene: the first voiced window of `build/rendered-audio.wav` at or after the scene start (`from / fps`) lies within 0.06 s of `leadFrames / fps` plus the time of the first voiced window of the scene's own clip `audio/<id>.say.wav`. Red: Review Focus 1.
  - `test_each_scene_changes_the_picture` — for each scene after the first, its `-end` still and the `-end` still of the scene before differ in more than 500 pixels (`differing_pixels` over the whole 1280x720 frame). Red: fault 3 of spec §8.4, a scene that changes nothing.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_film_example tests.test_render_film`
  Expected: `FAILED`; both `ExampleSceneCase` tests fail (no `Film.tsx`); the eight `FilmRenderCase` cases are skipped.

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film.FilmRenderCase.test_film_prints_nine_ok_lines`
  Expected: the workspace path, then `FAILED`: the render stops at `render: FAIL remotion render exit 1` (no composition `Film`).

- [ ] **Step 3: Add the film timeline type to `types.ts`** as the Produces block gives it. `Format`, `Timeline` and every other type of the file stay as they are.

- [ ] **Step 4: Write `FilmStage.tsx` and register the composition.** Contract:
  - `FilmStage` returns, in this order: one `<svg>` with `viewBox="0 0 1280 720"` (from `STAGE`), the width and height of the timeline and the ground `C.bg`, which holds `<Film at={at} sources={sources} />`; then, for each scene in order, its narration clip: a `Sequence` with `layout="none"`, `from` = `scene.from + scene.leadFrames`, `durationInFrames` = `scene.audioFrames`, around `Html5Audio` of `staticFile(scene.audio)`, as `Explain.tsx` places a clip.
  - `at` is `makeAt<SceneId>(timeline.scenes)`. `sources` holds `sourceFromDisk(entry)` for each entry of `timeline.sources` under its id. Both are made inside the component, memoised on the timeline's `scenes` and `sources`.
  - `FilmStage` handles no error: a mark error or a source that the timeline lacks throws in `Film` and ends the render.
  - `Root.tsx` registers a second composition, id `Film`, component `FilmStage`, with default props of an empty film timeline (no scenes, no sources, no check frames, 1280x720, 30 fps) and a `calculateMetadata` that throws `Film: no scenes; render with --props <path to build/timeline.json>` for no scenes and else gives the length, fps and size of the timeline. Composition `Explain` does not change.

- [ ] **Step 5: Write the picture, `src/film/Film.tsx`,** by the storyboard and the rules of section "The worked example". It reads the code card's lines from `props.sources.check` and takes every position in time from `props.at`.

  Run: `cd skills/explain && python3 -B -m unittest tests.test_film_example`
  Expected: `OK`. Then apply the planted import of Step 1 and revert it.

- [ ] **Step 6: Render the template and read every still.**

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && out=$(mktemp -d /tmp/film-example.XXXXXX) && python3 -B -c 'import json, sys; sys.path.insert(0, "tests"); from test_film_example import template_script; json.dump(template_script(), open(sys.argv[1] + "/script.json", "w"))' "$out" && scripts/render.sh "$out" --engine say; echo "exit $? in ${out:-no output directory}"`
  Expected: the workspace path, nine stage lines that end in `ok`, the last `transcript: ok`, then `exit 0 in <dir>`. `exit 1 in no output directory` means the variable is not set (Global Constraints). On a FAIL line, read the indented lines below it (render: the log tail names a `MARK` error or a missing source), fix, run again.

  Read each PNG of `$out/review` against the narration of its scene. A still with one of these faults (spec §8.4) means a change of the picture or of the narration, then a new render, until no still has one:
  1. Text that is clipped by a shape, or that a shape covers.
  2. A picture that does not agree with the narration of its scene.
  3. An `-end` still that equals the `-end` still of the scene before it.
  4. A picture that is a list of sentences.
  5. Text that gives a false picture of the subject, a quoted line that the source does not hold among them.

  Read them also for the three guard rules of the picture: no text off the canvas, under 14 px, or over another text. When the narration changes, run Step 4 of Task 4 again and `tests.test_film_example`. Remove `$out` at the end.

- [ ] **Step 7: Run the gated film tests; prove two of them in the broken state.**

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film`
  Expected: the workspace path, then `OK` with no skip.

  Then, each as an edit that is not committed and is reverted: start the clips of `FilmStage` at `scene.from`, run `tests.test_render_film.FilmRenderCase.test_voice_starts_at_the_lead` gated, and see it fail (the render of that state still prints `sync: ok`, which is why the test exists); make `test_each_scene_changes_the_picture` compare each still with itself and see it fail.

- [ ] **Step 8: Render the template once with Kokoro and measure the tail.** Spec §7.1 gives this to the first film render: the 12-frame pause leaves 0.4 s after the speech, `verify_sync.py` asks for more than 0.3 s, and the tail of a Kokoro clip was never measured (`kp-c04`).

  Run: the command of Step 6 without `--engine say`.
  Expected: nine stage lines that end in `ok`, among them `narration (kokoro): ok` and `sync: ok`.

  - `narration (say): ok (fallback: <cause>)`: the measurement was not made. Say so, with the cause, in the close reason of the task.
  - `sync: FAIL <id>: speech runs past the scene end`: give that scene of the template a `pause` with which the stage passes, and run `tests.test_film_example` again. The default pause of the film row is not changed here: wave `film-live-run` folds it back.
  - On a pass, run `python3 video/verify_sync.py "$out/build/rendered-audio.wav" "$out/build/timeline.json"` and name in the close reason the smallest gap between the end of the speech (`<last>` of a `sync:` line) and the length of its scene (`durationInFrames / fps` of the timeline).

  Read the stills of this render once by the list of Step 6: the default engine gives the film a person sees. Remove `$out` at the end.

- [ ] **Step 9: Commit.**

  ```bash
  git add skills/explain/video/src/types.ts skills/explain/video/src/Root.tsx skills/explain/video/src/FilmStage.tsx skills/explain/video/src/film skills/explain/tests/test_film_example.py skills/explain/tests/test_render_film.py
  git commit -m "feat: explain: FilmStage, composition Film and the worked example film"
  ```

  Add `skills/explain/templates/film-script.json` and `skills/explain/video/src/film/script.gen.ts` when Step 6 or Step 8 changed the script.

- [ ] **Step 10: Run the full unit suite, once.**

  Run: `cd skills/explain && python3 -B -m unittest discover -s tests`
  Expected: `OK (skipped=41)`: the 33 of the base and the eight of `FilmRenderCase`. No failure and no error.

- [ ] **Step 11: Run the map's acceptance.**

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film tests.test_render tests.test_render_brainrot tests.test_check_render`
  Expected: the workspace path, then `OK` with no skip: the film nine lines, the explainer nine (`SayFixtureCase`), brainrot ten (`BrainrotRenderCase`). About 12 minutes.

  Then check the tree: `git status --short` prints nothing, and `git diff --stat 82f0dd46c49432a0036e768d6d23e2695fc6291b -- . ':!docs'` lists only files that Global Constraints allows.

## Wave close

The map's `done_when` is met by: Task 5 Step 7 and Step 11 (the gated film test with nine `ok` lines and a transcript that passes `verify.sh`; brainrot ten lines, the explainer nine), Task 5 Step 6 and Step 8 (the stills read with no fault of spec §8.4; the close reason of the task names the number of stills read, the number of render rounds and the Kokoro tail), Task 4 (the two always-run tests of spec §5.3), Task 1 and Task 2 (the film cases of `test_transcript.py` and `test_check_render.py`).

Inputs for the plans of later waves:

- `film-scene-stage`: `stage_render` already renders `Film` from `$run/src/film`; the `scene` stage replaces that directory before the render. `test_the_example_follows_the_scene_rules` holds the rules of `check_scene.py` as lists and can become a run of the tool on `video/src/film`. The film run then prints ten lines: `STAGES` of `test_render.py` gets `scene`, and `test_film_prints_nine_ok_lines` its new line. `ParallelRenderCase` swaps its explainer for a film (`render_film` shows how to render the template). Decision 1 ends with that wave.
- `film-guard`: the measurement goes into `FilmStage`, on the one `<svg>` it renders. `clear_stale` already removes `build/guard.mp4`. The example was written to the three guard rules but no stage has measured it.
- `film-docs`: the transcript of a film has the scene id as its heading; a film scene without `cites` is allowed for a `topic` subject; the template's root is `.`.
- `explainer-removal`: `templates/film-script.json` becomes `templates/video-script.json`; `REPO`, `FILM_TEMPLATE` and `template_script` of `tests/test_film_example.py` name it. The composition `Explain` and `EMPTY` of `Root.tsx` stay for brainrot.
