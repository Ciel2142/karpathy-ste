# Explain movie, wave 1 (movie-tooling) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The mechanical floor of a movie: `movie.py` (`check`, `bridges`, `stitch`, `status`), the bridge scene template, the hub template, and the `movie` rung in `verify.sh`, proven by a gated end-to-end stitch of two tiny chapters and one bridge.

**Architecture:** One stdlib Python script beside `course.py`, reading one file `movie.json` and the chapter and bridge directories under it. A chapter is a `film` and a bridge a `clip` of the unchanged render pipeline; `stitch` concatenates their `video.mp4` files with the ffmpeg of the Remotion CLI in the workspace, then writes the hub and the cold-viewer transcript from the chapters' own transcripts. The hub is a page of the `page.html` family with a `<video>` and a chapter list that seeks it.

**Tech Stack:** Python 3 stdlib, bash (`verify.sh`), TypeScript and React against `video/src/kit` for the bridge scene, the Remotion CLI's bundled `ffmpeg` and `ffprobe` (no system ffmpeg).

**Spec:** `docs/superpowers/specs/2026-11-03-explain-movie-design.md`. Wave map: `docs/superpowers/waves/2026-11-03-explain-movie.yaml`, wave `movie-tooling`.

## Global Constraints

- Frozen, never edited in this wave: `video/formats.json`, `video/build-timeline.mjs`, `video/narrate.py`, `video/check_budgets.py`, `video/transcript.py`, `scripts/render.sh`, `video/check_render.sh` (spec section 1). `git diff --quiet "$(git merge-base main HEAD)" -- <those paths>` must stay true.
- `verify.sh` changes in two places only: the rung `case` and the media check (spec section 1, D9).
- All paths below are under `skills/explain/` of the worktree `~/karpathy-wt/explain-movie`.
- Scripts are stdlib only, exit 0 on all ok, 1 on a `FAIL` or a refused change, 2 on usage or unreadable JSON (spec section 6). Every write of `movie.json` goes through an atomic `save` (temp file, `os.replace`), as `course.py` does.
- Printed lines are `<name>: ok …` or `<name>: FAIL <cause>`; wave 2's drift test pins their exact text, so write them as this plan quotes them.
- Ids match `[a-z0-9][a-z0-9-]*`. A movie has 3 to 5 questions and 4 to 10 chapters; a chapter answers 1 or 2 questions and has `seconds` from 30 to 150; the sum of `seconds` is 240 to 900 (spec 4.2, D7).
- The workspace is `$EXPLAIN_VIDEO_WORKSPACE`, else `~/karpathy/video-workspace`; the Remotion CLI is `<ws>/app/node_modules/.bin/remotion`, run with cwd `<ws>/app` and stdin from `/dev/null` (as `check_render.sh` does).
- Prose fields of `movie.json` pass `ste_lint.py` (found as `course.py` finds it), or convention 7 for `ru`.

## Review Focus

1. A chapter marked `built` whose `video.mp4` is missing: `stitch` must print `parts: FAIL chapters/<id>/video.mp4 missing` and write nothing, not crash in ffmpeg. (Task 4)
2. A path with a single quote or a space in the concat list: the ffmpeg concat format needs `file '<path>'` with `'` written as `'\''`; a wrong escape silently drops the part. (Task 4)
3. `seconds` given as a string or a float: `check` must say `chapter <id>: seconds must be an integer from 30 to 150`, not raise. (Task 1)
4. A chapter directory under `chapters/` whose name is no chapter id: `status` must list it as `stray`, since a renamed chapter would otherwise be stitched twice or never. (Task 2)
5. A chapter transcript whose `ask` or `answer` section is missing: the viewer transcript must then `FAIL` by name, not silently include the answer. (Task 5)

---

### Task 1: `movie.json` load, save and plan check

**Files:**
- Create: `scripts/movie.py`
- Create: `tests/fixtures/movie/movie.json` (a good plan: 3 questions, 4 chapters, `seconds` 60 each, `lang` `en`, `root` `.`, `subject.kind` `topic`, no cites)
- Create: `tests/test_movie.py`

**Interfaces:**
- Consumes: `cite_check.fact_problems` and the `ste_lint` lookup of `course.py` (`_find_ste_lint`), reused by import, not copied.
- Produces:
  - `load(movie_dir: str) -> dict` (exit-2 style `ReadError(Exception)` on missing or invalid JSON)
  - `save(movie_dir: str, movie: dict) -> None` (atomic)
  - `resolve_root(movie_dir: str, root: str) -> str` (absolute, or relative to `movie_dir` as `course.py` does)
  - `check(movie_dir: str, movie: dict) -> list[str]` (the failure lines; empty when ok)
  - `main(argv: list[str]) -> int`
  - Constants `MOVIE_FILE = "movie.json"`, `VERSION = 1`, `MIN_QUESTIONS, MAX_QUESTIONS = 3, 5`, `MIN_CHAPTERS, MAX_CHAPTERS = 4, 10`, `MIN_SECONDS, MAX_SECONDS = 30, 150`, `MIN_TOTAL, MAX_TOTAL = 240, 900`, `MAX_ANSWERS = 2`, `STATES = ("planned", "building", "stitched")`, `STATUSES = ("pending", "built", "failed")`.

Failure prefixes, fixed here for the drift test of wave 2: `schema: <key> …` (a missing or wrongly typed top-level key, `version` not 1), `id: <id> is used twice`, `question <id>: …`, `chapter <id>: …`, `cite <question-id>#<n>: …` (from `cite_check`), `prose: …` (an `ste_lint` error line, as `course.py` formats it), `state: …`.

- [ ] **Step 1: Write the failing tests** in `tests/test_movie.py`, one private fixture copy per test as `test_course.py` does, with a `run_cli(*argv)` helper that captures stdout and stderr of `movie.main`:
  - `test_good_plan_prints_plan_ok`: `check` on the fixture exits 0 and its last line is `plan: ok (3 questions, 4 chapters, 240 s target)`.
  - `test_a_question_no_chapter_answers`: remove the question's id from every `answers`; expect `question q-3: no chapter answers it`.
  - `test_a_chapter_with_three_answers`: expect `chapter <id>: answers has 3 entries (max 2)`.
  - `test_an_unknown_answer_id`: expect `chapter <id>: answers names q-nope, not a question`.
  - `test_too_few_chapters`: delete one chapter; expect `schema: chapters has 3 entries (min 4, max 10)`.
  - `test_seconds_sum_out_of_range`: set every `seconds` to 30; expect `schema: seconds sum 120 (min 240, max 900)`.
  - `test_seconds_not_an_integer`: set one to `"60"`; expect `chapter <id>: seconds must be an integer from 30 to 150`.
  - `test_a_duplicate_id`: give a chapter a question's id; expect `id: <id> is used twice`.
  - `test_a_file_subject_needs_a_cite_per_question`: `subject.kind` `file` and `cites: []`; expect `question <id>: a file or directory subject needs at least one cite`.
  - `test_a_bad_cite_is_reported`: a cite whose snippet is not on its line under `root`; expect a line that starts with `cite <id>#1:`.
  - `test_invalid_json_exits_2`: a `movie.json` that is not JSON; `main` returns 2 and stderr holds one line.
  - `test_save_is_atomic`: after `save`, the directory holds `movie.json` and no `*.tmp*` file, and `load` round-trips.
- [ ] **Step 2: Run them** — `cd skills/explain && python3 -B -m unittest tests.test_movie -v`. Expected: every test errors with `ModuleNotFoundError: movie` or fails.
- [ ] **Step 3: Implement** `movie.py` with the signatures above, a `USAGE` string that names the four commands, and the `check` command that prints each failure line then `plan: ok (…)` or `plan: <n> failures`. The prose check covers `title`, `question`, each question's `text` and `answer`, each chapter's `title`, `question`, `picture` and `ends_with`, and `not_covered`, by the `_check_prose` approach of `course.py`.
- [ ] **Step 4: Run the tests** — same command. Expected: all PASS.
- [ ] **Step 5: Commit** — `git add scripts/movie.py tests/test_movie.py tests/fixtures/movie/ && git commit -m "feat: explain: movie.py check validates movie.json"`.

### Task 2: chapter script check and `status`

**Files:**
- Modify: `scripts/movie.py`
- Create: `tests/fixtures/movie/chapters/members/script.json` (a film script with scenes `ask`, `body`, `answer`, title equal to the fixture chapter's title)
- Test: `tests/test_movie.py`

**Interfaces:**
- Consumes: `load`, `check`, the fixture of Task 1.
- Produces:
  - `check_chapter_script(movie_dir: str, chapter: dict) -> list[str]` (empty when no `chapters/<id>/script.json` exists; else the 4.3 rules)
  - `status(movie_dir: str, movie: dict) -> list[str]` (one line per chapter `chapter: <id> <status>[ <reason>]`, one `stray: chapters/<name>` per directory that is no chapter id, then `state: <state>`)
  - `check` now appends the `check_chapter_script` lines of every chapter.

- [ ] **Step 1: Write the failing tests**:
  - `test_a_chapter_script_with_ask_and_answer_passes`: with the fixture chapter in place, `check` still prints `plan: ok (…)`.
  - `test_first_scene_must_be_ask`: rename the first scene id; expect `chapter members: first scene is intro, not ask`.
  - `test_last_scene_must_be_answer`: expect `chapter members: last scene is body, not answer`.
  - `test_script_title_must_match`: expect `chapter members: script title "X" differs from "The members"`.
  - `test_script_format_must_be_film`: set `"format": "clip"`; expect `chapter members: format is clip, not film`.
  - `test_status_lists_each_chapter_and_strays`: make `chapters/old/`; `status` prints `chapter: members pending`, …, `stray: chapters/old`, `state: planned`, exit 0.
- [ ] **Step 2: Run** `python3 -B -m unittest tests.test_movie -v`. Expected: the six new tests fail.
- [ ] **Step 3: Implement** the two functions and the `status` command.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -am "feat: explain: movie.py checks chapter scripts and prints status"` (add the new fixture first).

### Task 3: the bridge template and `bridges`

**Files:**
- Create: `video/src/bridge/Film.tsx` (the generated scene; placeholders `{{done}}`, `{{next}}` for the two labels)
- Create: `templates/movie-bridge-script.json` (`"format": "clip"`, `lang` placeholder, three scenes `done`, `sofar`, `next`, placeholders `{{done_question}}`, `{{answer}}`, `{{next_question}}` in the narrations, `provenance` placeholders `{{root}}`, `{{date}}`, `not_covered` `none`)
- Modify: `scripts/movie.py`
- Test: `tests/test_movie.py`

**Interfaces:**
- Consumes: the kit of `video.md` section 4 (`Sans`, `Mark`, `p`, `C`, `STAGE`), `video/check_scene.py` (static check of a scene directory; invoked by the test through `subprocess` as `test_check_scene.py` does).
- Produces:
  - `bridges(movie_dir: str, movie: dict) -> list[str]` (the bridge ids written, `"1"` … `"<n-1>"`; prints `bridges: ok (<n>)`)
  - `BRIDGE_TEMPLATE_SCENE = <skill>/video/src/bridge`, `BRIDGE_TEMPLATE_SCRIPT = <skill>/templates/movie-bridge-script.json`.

The bridge picture: the answered question as a `Sans` label at the top third with a green `Mark` that draws at `at("done")`, the one-sentence answer as a second label that fades in at `at("sofar")`, and the next question in `C.yellow` that rises into the lower third at `at("next")` while the first two fade to `C.muted`. All text at 24 px or more (clip floor 19 px). Labels are typed into the scene by placeholder substitution; a `"` or a backslash in a label is JSON-escaped into the TypeScript string literal.

- [ ] **Step 1: Write the failing tests**:
  - `test_bridges_writes_one_per_gap`: on the 4-chapter fixture, `bridges` returns `["1", "2", "3"]` and `bridges/2/script.json` has `format` `clip`, scene ids `["done", "sofar", "next"]`, no `cites` key, `title` `Bridge 2`, and its `done` narration holds the `question` of chapter 2 and its `next` narration the `question` of chapter 3.
  - `test_bridges_copies_pronounce_for_ru`: with `lang` `ru` and a `pronounce` map, each bridge script has `lang` `ru` and the same `pronounce`; with `en`, no `pronounce` key.
  - `test_bridges_is_idempotent`: a second run leaves every file byte-identical.
  - `test_bridge_scene_passes_check_scene`: `python3 video/check_scene.py bridges/1/scene` exits 0.
  - `test_bridge_label_escapes_quotes`: a question with `"` in it yields a `Film.tsx` that `check_scene.py` accepts and that holds the escaped text.
- [ ] **Step 2: Run** `python3 -B -m unittest tests.test_movie -v`. Expected: the five new tests fail.
- [ ] **Step 3: Implement** the two template files and `bridges`. The narration of `sofar` is the `answer` of the first question in the chapter's `answers`.
- [ ] **Step 4: Run** the tests. Expected: PASS. Also run `python3 video/check_scene.py video/src/bridge` by hand: exit 0 with the placeholders in place.
- [ ] **Step 5: Commit** — `git add video/src/bridge templates/movie-bridge-script.json scripts/movie.py tests/test_movie.py && git commit -m "feat: explain: movie.py bridges generates the clip between two chapters"`.

### Task 4: `stitch`, part one: parts, concat, container, length, `chapters.json`

**Files:**
- Modify: `scripts/movie.py`
- Create: `tests/fixtures/movie/probe/` (two small text files that stand in for ffprobe outputs in the mocked tests)
- Test: `tests/test_movie.py`

**Interfaces:**
- Consumes: `load`, `save`, `status`; the Remotion CLI path rule of Global Constraints.
- Produces:
  - `remotion_cli(workspace: str) -> list[str]` (the argv prefix; `FileNotFoundError` with the message `no Remotion CLI at <path>` when missing)
  - `probe(cli: list[str], mp4: str) -> dict` with keys `vcodec`, `acodec`, `width`, `height`, `fps`, `rate`, `duration` (floats and ints; `ffprobe exit <n>` in a `StitchError`)
  - `parts(movie_dir: str, movie: dict) -> list[str]` (the ordered part paths: chapter, bridge, chapter, …; `StitchError` names the first missing `video.mp4` or a chapter not `built`)
  - `concat_list(paths: list[str]) -> str` (the text of `build/concat.txt`, with the quote escape of Review Focus 2)
  - `stitch(movie_dir: str, movie: dict, workspace: str) -> int` (prints the lines below, writes `build/concat.txt`, `build/video.part.mp4` then `os.replace` to `video.mp4`, `chapters.json`; returns the exit code)
  - `chapters.json` shape: `[{"id": …, "title": …, "start": <float seconds>}]`, the start of each chapter as the sum of the durations of the parts before it.

Printed lines, in order; the first `FAIL` stops the command (exit 1) except `length`, which is last and only sets the exit code: `parts: ok (<n>)` | `parts: FAIL <part> <what> differs` | `parts: FAIL <part> missing` | `parts: FAIL chapter <id> is <status>, not built`; `concat: ok (<s> s)` | `concat: FAIL ffmpeg exit <n>`; `container: ok (<s> s)` | `container: FAIL <cause>` (not one video and one audio stream, or a length not within 0.5 s of the sum); `length: ok (<s> s)` | `length: FAIL <s> s (min 240, max 900)`. `<s>` is printed with one decimal.

- [ ] **Step 1: Write the failing tests** (ffmpeg and ffprobe mocked through `unittest.mock.patch("movie.run")`, where `run(argv) -> (code, stdout)` is the one subprocess seam of the module):
  - `test_concat_list_escapes_a_quote`: `concat_list(["/a/it's.mp4"])` is `file '/a/it'\''s.mp4'\n`.
  - `test_parts_order_is_chapter_bridge_chapter`: on a fixture where every chapter is `built` and every `video.mp4` exists as an empty file, `parts` returns `chapters/c1, bridges/1, chapters/c2, …`.
  - `test_parts_refuses_a_missing_mp4`: delete one; `stitch` prints `parts: FAIL chapters/<id>/video.mp4 missing` and exits 1.
  - `test_parts_refuses_a_pending_chapter`: expect `parts: FAIL chapter <id> is pending, not built`.
  - `test_parts_refuses_a_rate_mismatch`: mocked probes give 48000 and 22050; expect `parts: FAIL bridges/1/video.mp4 audio rate differs`.
  - `test_stitch_writes_chapters_json_starts`: with mocked durations 60, 10, 60, 10, 60, 10, 60, `chapters.json` starts are 0, 70, 140, 210 and `length:` reads `length: ok (270.0 s)`.
  - `test_stitch_reports_a_short_movie`: durations summing to 35.0; `length: FAIL 35.0 s (min 240, max 900)`, exit 1, and `video.mp4` still exists.
  - `test_no_cli_is_a_usage_error`: a workspace without the CLI gives exit 2 and the stderr line `no Remotion CLI at <path>`.
- [ ] **Step 2: Run** the tests. Expected: the eight new tests fail.
- [ ] **Step 3: Implement**. ffmpeg argv: `ffmpeg -v error -y -f concat -safe 0 -i build/concat.txt -c copy build/video.part.mp4`. ffprobe argv as in `check_render.sh` (`-show_entries stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate` and `format=duration`, `-of csv=p=0`).
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat: explain: movie.py stitch concatenates chapters and bridges"`.

### Task 5: `stitch`, part two: the viewer transcript and the hub sections

**Files:**
- Modify: `scripts/movie.py`
- Create: `tests/fixtures/movie/chapters/members/index.html` (a film transcript as `transcript.py` writes it: sections `ask`, `body`, `answer`, each with `<h2>`, one `<p>` and a `div.cites` on `body`)
- Test: `tests/test_movie.py`

**Interfaces:**
- Consumes: the transcript markup of `transcript.py` (`<section id="<scene>">`, `<h2><scene></h2>`, `<p>narration</p>`, optional `<div class="cites" data-ste="skip">…</div>`).
- Produces:
  - `chapter_sections(movie_dir: str, chapter: dict) -> dict[str, str]` (scene id to the section's inner HTML without its `<h2>`; `StitchError("chapter <id>: transcript has no section <ask|answer>")`)
  - `hub_section(chapter: dict, sections: dict[str, str]) -> str` (`<section id="ch-<id>"><h2><title></h2>` then every scene's `<p>` and cites in order, `</section>`)
  - `viewer_section(chapter: dict, sections: dict[str, str]) -> str` (the same without `ask` and `answer`)
  - `stitch` now also writes `build/hub-sections.html` and `review/viewer-transcript.html`, before the `length:` line, and prints `transcript: ok (<n> chapters)` between `container:` and `length:`.

`review/viewer-transcript.html` is a self-contained page: the title, the list of question texts (no answers), one `viewer_section` per chapter, no provenance, no cites blocks (cites name the sources the viewer must not open). The viewer never sees `movie.json`.

- [ ] **Step 1: Write the failing tests**:
  - `test_chapter_sections_keys_are_the_scene_ids`: on the fixture transcript, keys are `["ask", "body", "answer"]` and the `body` value holds `class="cites"`.
  - `test_hub_section_keeps_every_scene`: the output holds the three `<p>` texts and `<h2>The members</h2>`, and no `<h2>ask</h2>`.
  - `test_viewer_section_drops_ask_and_answer`: holds the `body` text only, and no `class="cites"`.
  - `test_viewer_transcript_fails_without_an_answer_section`: remove the `answer` section; `stitch` prints `transcript: FAIL chapter members: transcript has no section answer`.
  - `test_viewer_transcript_lists_questions_without_answers`: the file holds each question's `text` and none of the `answer` strings.
- [ ] **Step 2: Run** the tests. Expected: the five new tests fail.
- [ ] **Step 3: Implement** with `html.parser` or the section regex `transcript.py`'s own tests use; pick one and note it in the module docstring.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat: explain: movie.py stitch writes the viewer transcript and the hub sections"`.

### Task 6: the hub template, `index.html`, and the `movie` rung in `verify.sh`

**Files:**
- Create: `templates/movie.html`
- Modify: `scripts/movie.py` (`stitch` writes `index.html`)
- Modify: `scripts/verify.sh:321-328` (the rung `case`) and `scripts/verify.sh:150-245, 405-415` (the media check)
- Create: `tests/fixtures/verify-movie.html`
- Test: `tests/test_verify.py`, `tests/test_movie.py`

**Interfaces:**
- Consumes: `page.html` (its `<style>`, nav, footer provenance block and `.cites` rule are copied, the steps player and diagram parts are not), `hub_section`, `chapters.json`.
- Produces:
  - `templates/movie.html` with placeholders `{{title}}`, `{{question}}`, `{{lang}}`, `{{questions}}` (a `<dl>` of text and answer, each answer followed by its cites block), `{{chapters}}` (the `<ol id="chapters">` of `<li><a href="#ch-<id>" data-start="<s>">`), `{{sections}}`, `{{root}}`, `{{kind}}`, `{{subject}}`, `{{source}}`, `{{date}}`, `{{commit}}`, `{{dirty}}`, `{{not_covered}}`; `<meta name="explain-rung" content="movie">`; a `<video id="movie" controls src="video.mp4">`; a script that, on a click of a chapter link, sets `movie.currentTime` to `data-start` and plays; each `<section>` ends with `<a href="chapters/<id>/index.html" data-ste="skip">transcript</a>`.
  - `hub(movie_dir: str, movie: dict, starts: list[float]) -> str` and `stitch` writes it to `index.html`, then prints `hub: ok index.html` before `length:`.
  - `verify.sh`: `rung=movie) viewports="1440x900 500x844"` ; the error text becomes `(expected sheet, page, video, lesson, course, onboard or movie)`; the media check runs for `movie` too and counts `<a href>` into `chapters/` and `bridges/` as it counts `clips/`.

- [ ] **Step 1: Write the failing tests**:
  - in `test_verify.py`: `test_movie_rung_renders_the_page_viewports` (a copy of the lesson test on `verify-movie.html`, expecting the seven lines with `media: ok`), `test_movie_missing_chapter_transcript_fails_media` (`media: FAIL 1 missing` with the detail line `a href=chapters/members/index.html`), and the two existing "expected …" assertions updated to the new list.
  - in `test_movie.py`: `test_hub_holds_the_chapter_list_and_sections` (the string holds `data-start="70.0"` for the second chapter, `<h2>The members</h2>`, `content="movie"` and `data-root="<root>"`), `test_stitch_writes_index_html` (the file exists after a mocked stitch and holds the title).
- [ ] **Step 2: Run** `python3 -B -m unittest tests.test_verify tests.test_movie`. Expected: the new tests fail; the two "expected" assertions fail on the old list.
- [ ] **Step 3: Implement** the template, `hub`, and the `verify.sh` edits.
- [ ] **Step 4: Run** the same command. Expected: PASS. Then `python3 -B -m unittest tests.test_rung_drift`: still PASS (no rung file names `movie` yet).
- [ ] **Step 5: Commit** — `git add templates/movie.html scripts/movie.py scripts/verify.sh tests/ && git commit -m "feat: explain: movie hub page and the movie rung in verify.sh"`.

### Task 7: the gated end-to-end stitch

**Files:**
- Create: `tests/test_movie_e2e.py`
- Create: `tests/fixtures/movie-e2e/movie.json` (2 chapters, both `built`, `seconds` 30; this fixture is for the render only and is not a valid plan, which `test_movie_e2e` says in its docstring)

**Interfaces:**
- Consumes: `tests/fixtures/lesson-e2e/` (a 3-scene clip of the film template with scenes `subject`, `gates`, `handoff`), `video_e2e.E2E`, `render_env`, `RENDER_SH`, `RENDER_TIMEOUT`; `bridges`, `stitch`, `verify.sh`.
- Produces: the evidence of the wave's `done_when`.

A chapter of the fixture is the lesson-e2e clip with `format` set to `film`, its first scene id renamed `subject` to `ask` and its last `handoff` to `answer`, in `script.json` and in every `at("subject"…)` and `at("handoff"…)` of `scene/*.tsx` (a `sed`-style replace in the test helper `chapter_from_clip(out, chapter_id)`), and `title` set to the chapter's title.

- [ ] **Step 1: Write the test module** with `@unittest.skipUnless(E2E, E2E_REASON)` on the render case:
  - `test_the_fixture_chapters_pass_check_chapter_script` (not gated): `check_chapter_script` returns `[]` for both.
  - `test_two_chapters_and_a_bridge_stitch` (gated): render both chapters and `bridges/1` with `render.sh --engine say` (eleven `ok` lines each, by `stage_lines` of `test_render`); then `movie.main(["stitch", out])` prints `parts: ok (3)`, `concat: ok (<s> s)`, `container: ok`, `transcript: ok (2 chapters)`, `hub: ok index.html`, and `length: FAIL <s> s (min 240, max 900)` with exit 1; `video.mp4` probes (through `probe`) to the sum of the three part durations within 0.5 s; `chapters.json` has two entries and the second start equals the first two durations summed; `review/viewer-transcript.html` holds the `gates` narration and neither the `ask` nor the `answer` narration; `verify.sh index.html` exits 0 with `media: ok`.
- [ ] **Step 2: Run ungated** — `python3 -B -m unittest tests.test_movie_e2e -v`. Expected: the first test passes, the second skips.
- [ ] **Step 3: Run gated** — `EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_movie_e2e -v`. Expected: PASS within the render timeout (three `say` renders of about 20 s each plus the stitch).
- [ ] **Step 4: Run the wave acceptance** — the four commands of the wave map. Expected: all pass; the git diff on the frozen files is empty.
- [ ] **Step 5: Commit** — `git add tests/test_movie_e2e.py tests/fixtures/movie-e2e && git commit -m "test: explain: gated end-to-end stitch of two chapters and a bridge"`.

---

## Rollback and recovery

`stitch` writes `video.mp4` by `os.replace` from `build/video.part.mp4`, so a failed concat leaves the previous `video.mp4` untouched. `movie.json` is written only by `save`. A chapter is re-rendered by `render.sh` in its own directory and never touched by `movie.py`. Nothing in this wave writes outside the movie directory.

## Acceptance evidence

```
cd skills/explain && python3 -B -m unittest discover -s tests -p "test_movie*.py"
cd skills/explain && python3 -B -m unittest tests.test_verify
cd skills/explain && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_movie_e2e
git diff --quiet "$(git merge-base main HEAD)" -- skills/explain/video/formats.json skills/explain/video/build-timeline.mjs skills/explain/video/narrate.py skills/explain/video/check_budgets.py skills/explain/video/transcript.py skills/explain/scripts/render.sh skills/explain/video/check_render.sh
```

Decisive lines: `OK` from each unittest run; no output and exit 0 from the diff.
