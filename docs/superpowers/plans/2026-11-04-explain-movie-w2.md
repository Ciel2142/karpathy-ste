# Explain movie, wave 2 (movie-procedure) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The `--as movie` route a user can invoke: `rungs/movie.md` with the ten steps of the spec, the three prompt templates with their fill tables, and the `movie` entries of `SKILL.md` and `README.md`, each pinned by a test.

**Architecture:** Prose only, in the shape of the course rung: `rungs/movie.md` is the orchestrator's procedure and quotes the printed lines of `scripts/movie.py` (wave 1) word for word; `movie/chapter-task.md`, `movie/review-viewer.md` and `movie/review-chapter.md` are templates filled by plain text replacement of `{name}`, as `course/lesson-task.md` and `lesson/review-script.md` are. Three test modules tie the prose to the code and to each other: a `MovieRungCase` in `test_rung_drift.py` (titles, quoted lines against the code that prints them, the `--as` lists), `test_movie_prompts.py` (placeholders against fill rows, result lines, overrides), and the existing `SkillMdCase` updated for the ninth rung.

**Tech Stack:** Markdown under the STE-80 profile (`ste_lint.py`), Python `unittest` (stdlib), the helpers of `tests/test_rung_drift.py` and `tests/test_lesson_prompts.py`.

**Spec:** `docs/superpowers/specs/2026-11-03-explain-movie-design.md`, sections 4.1, 4.7, 5, 7, 8 and decisions D10 to D12. Wave map: `docs/superpowers/waves/2026-11-03-explain-movie.yaml`, wave `movie-procedure`. Wave 1 is done: `scripts/movie.py`'s module docstring (lines 1 to 90) lists every printed line and is the source the drift test pins.

## Global Constraints

- All paths are under `skills/explain/` of the worktree `~/karpathy-wt/explain-movie` (branch `feat/explain-movie`), except `README.md` at the repo root.
- No code changes in this wave: `scripts/movie.py`, `scripts/verify.sh`, the templates and the frozen pipeline files stay as wave 1 left them. The rung quotes `movie.py`'s lines; it never redefines them.
- Every printed line the rung quotes reads exactly as `movie.py`'s docstring gives it: `plan: ok (<q> questions, <c> chapters, <lo>..<hi> s with bridges)`, `plan: <n> failures`, `bridges: ok (<n>)`, the `stitch` lines `parts:`, `concat:`, `container:`, `transcript:`, `hub:`, `length:` with their `ok` and `FAIL` forms, and the `status` lines `chapter: <id> <status>[ <reason>]`, `stray: chapters/<name>`, `state: <state>`. The failure prefixes of `check` are `schema:`, `id:`, `question <id>:`, `chapter <id>:`, `cite <question-id>#<n>:`, `prose:`, `state:`.
- The four commands of `movie.py` are the only ones (spec 6). The author edits `movie.json` fields (`state`, a chapter's `status` and `reason`, `not_covered`) with the Edit tool, one field at a time, and runs `movie.py check <movie-dir>` after each edit. No `mark` or `approve` command exists in this wave.
- The rung line is `Rung: movie (forced) — <reason> — subject: <subject> (<kind>)`; `<kind>` is `topic`, `file` or `directory`; `conversation` stops with an offer of `video` (spec 4.1). After it: `review: on|off`, then one `chapter: <id> built|failed <reason>` line per chapter as the subagents return, then the stage lines of `stitch`, then the viewer gate lines, then the handoff (spec 4.7). The handoff prints `viewer: <n> of <m> understood`.
- Limits the rung states, from `movie.py`: 3 to 5 questions, 4 to 10 chapters, a chapter answers 1 or 2 questions, `seconds` 30 to 150, the sum with bridges budgeted 240 to 900 s (8 to 15 s per bridge), each question text, answer and chapter question at most 20 words, `lang` `en` or `ru`, a URL cite has no line.
- At most 3 chapter subagents at a time (D11); `video-workspace.sh --engine <engine>` once before the fan-out (`kokoro` for `en`, `silero` for `ru`, as `course.md` "Build the lessons" says). The viewer gate is always on; two rounds at most; a question still missed after round 2 goes to `not_covered` as `viewer missed: <question>` (step 8). `--review` adds the chapter gate `movie/review-chapter.md`; a finding still open after its rounds ships and goes to `not_covered` as `disputed: <finding>`; a chapter is never dropped (D12). Both `not_covered` sentences are STE prose: `check` lints them.
- A chapter script's `provenance.root` and `lang` equal the movie's (`check` compares them); a chapter cites no `.bpmn` file (the hub draws no diagram, and `verify.sh`'s bpmn check would fail the hub). The viewer still path inside the viewer page is relative to `review/` (`still: viewer-stills/<k>-<id>.png`).
- `rungs/movie.md` and the three prompts pass `ste_lint.py` (the `lint` helper of `test_rung_drift.py`). Each prompt holds the placeholders of its fill table and no other word in braces (`PLACEHOLDER` of `test_lesson_prompts.py`).
- Sentences of `SKILL.md` that existing tests pin keep their text, except the one the ninth rung must change: `These seven rules apply to every artifact rung (\`sheet\`, \`page\`, \`video\`, \`brainrot\`, \`lesson\`, \`course\`, \`onboard\`).` gains `, \`movie\`` before the closing parenthesis, and `test_skill_md_routes_the_lesson_rung` in `test_rung_drift.py` is updated to the new text. `(sheet, page, lesson or course)` in convention 6 stays; the video half becomes `(video, brainrot or movie)`. `AS_NAMES` becomes `ste|sheet|page|video|brainrot|lesson|course|onboard|movie` and the contract step 4 lists nine names.
- The whole explain suite's known baseline: four pre-existing failures in `test_film_contract.RussianFilmContract` (3) and `test_narrate.Fallback.test_silero_uv_not_found_falls_back` (1), environment-bound, not ours. Any other failure is a regression of this wave.

## Review Focus

1. A chapter subagent that never returns: the rung must say what the author does (print the id and the movie path, stop, resume later), as `course.md` does for a lesson; a weak model otherwise waits forever or rebuilds every chapter. (Task 1)
2. `stitch` exit 1 has two shapes: `length: FAIL` alone (every artifact written; the remedy is a chapter to lengthen or shorten, named by its `seconds` against the chapters' real durations in `chapters.json`) and any other FAIL (nothing to review; fix the named part). The rung must tell them apart; a weak model otherwise runs the viewer gate on a half-stitched movie or re-renders everything over a length miss. (Task 2)
3. The viewer's `cannot answer` and a wrong answer are both `missed`; only an answer that matches the `answer` of `movie.json` in meaning is `understood`. The rung must say the author compares meaning, not words, and never asks the viewer to try again. (Task 2)
4. A resume finds a `building` chapter: it was interrupted. The rung treats it as `pending` and moves its directory aside as `chapters/<id>.stale-<n>/` before the rebuild, never deleting it; a `failed` chapter goes to `pending` too, keeping its `reason` in the reply line. (Task 2)
5. The `amendment` of a chapter brief after a viewer miss must name what the film did not show, in the author's words, and the chapter subagent must treat it as a change of the picture, not of the answer: the answers are the contract. (Task 3)

---

### Task 1: `rungs/movie.md`, sections 1 to 5, and the first half of `MovieRungCase`

**Files:**
- Create: `rungs/movie.md` (sections 1 to 5 complete; sections 6 to 12 as level-2 titles with one sentence each, which Task 2 replaces)
- Modify: `tests/test_rung_drift.py` (a `MovieRungCase` after `OnboardRungCase`, with its constants before it; `quoted_lines` gains an `order` parameter defaulting to `FILM_ORDER`)

**Interfaces:**
- Consumes: `read`, `section`, `headings`, `lint`, `quoted_lines`, `line_pattern`, `code_lines` and `Printed` of `test_rung_drift.py`; `scripts/movie.py` lines 1 to 90 (the docstring) and its code.
- Produces:
  - `MOVIE_MD = EXPLAIN / "rungs" / "movie.md"`, `MOVIE_PY = "scripts/movie.py"`
  - `MOVIE_TITLES = ("When a movie", "Write the viewer questions", "Plan the chapters", "Check and stop", "Build the chapters", "Bridges", "Stitch", "The viewer gate", "Verify and handoff", "Resume", "Output directory", "Costs")` (the twelve level-2 titles, in order)
  - `MOVIE_ORDER = ("plan", "bridges", "parts", "concat", "container", "transcript", "hub", "length", "chapter", "stray", "state")` (the line names `movie.py` prints; a quoted line starts with one of them followed by `:` or ` (`)
  - `MOVIE_PRINTED: tuple[Printed, ...]` (one entry per quoted line of `movie.md`: the quoted text, a sample as `movie.py` prints it, evidence `(MOVIE_PY, <verbatim text of the statement>)`)
  - `MOVIE_PREFIXES = ("schema:", "id:", "question <id>:", "chapter <id>:", "cite <question-id>#<n>:", "prose:", "state:")`
  - `quoted_lines(text, order=FILM_ORDER)` (the existing helper with the stage tuple as a parameter; `STAGE_START` built per call)

Section contents, in prose the implementer writes under STE:

1. **When a movie** — what a movie is (one continuous film of 4 to 15 minutes on one theme, cut into chapters by bridges; a chapter is a film of `video.md`, a bridge a generated clip); the command `/explain <subject> --as movie [--review]`; `conversation` refused with the offer of `video`; a directory holding `movie.json` is a resume; the orchestrator keeps its context small (reads result lines, never a whole chapter); the language rule (`en` or `ru`, as the course rung words it, with the offer of `video` for another language); `review: on|off` after the rung line; the rung line in a fenced block; `movie.py <command>` is short for `python3 <skill-dir>/scripts/movie.py <command>`; subagents start in the background (Agent tool in Claude Code, `task` with `general` in OpenCode).
2. **Write the viewer questions** — step 2 of the spec: three to five questions a viewer must answer after the film, each with its `answer` (one sentence, at most 20 words) and its cites (path, line, verbatim snippet of at most 12 words; a URL cite has no line); the contract sentence: a chapter exists only to make one of these answers visible; the subject is read in full first as `video.md` says; for a topic without files, cites may be URLs or the questions carry `"cites": []`.
3. **Plan the chapters** — step 3: the order of the picture, `picture` (what the chapter draws) and `ends_with` (what is on screen at its end), `answers` (1 or 2 question ids), `seconds` 30 to 150, 4 to 10 chapters, the sum with bridges 240 to 900; the shape of `movie.json` version 1 as a fenced JSON example (the fixture `tests/fixtures/movie/movie.json` is the model: copy its shape, not its text); the field rules as a list (ids, prose under STE or convention 7, `lang`, `review`, `subject`, `provenance` with `root` absolute, `commit`, `dirty`, `date`, `source`, `not_covered`, `state` `planned`, every chapter `status` `pending` with `reason` `""`); the output directory `~/karpathy/out/YYYY-MM-DD-HHMMSS-movie-<slug>/` by convention 5.
4. **Check and stop** — step 4: run `movie.py check <movie-dir>`; it prints one failure per line then `plan: ok (<q> questions, <c> chapters, <lo>..<hi> s with bridges)` or `plan: <n> failures`; the prefix table (one row per prefix of `MOVIE_PREFIXES`, with what to fix); the stop rule (3 rounds of the same lines, or a fault not in `movie.json`); then print the plan as a list (one line per question, one per chapter with its question and `seconds`) and stop for the user's approval; build nothing before it; a resume skips the stop when `state` is not `planned`.
5. **Build the chapters** — step 5: set `state` to `building` (an edit of `movie.json`, then `check`); run `<skill-dir>/scripts/video-workspace.sh --engine <engine>` once, `workspace: ok <ws>` or stop on `workspace: FAIL`; the loop: at most 3 chapter subagents at a time, one per `pending` chapter in plan order, `movie/chapter-task.md` filled (its fill table arrives in Task 3; Task 1 writes the sentence `Fill its names as the table below says.` and a placeholder table with the header row only); when a subagent returns, read only its last line, `chapter: <id> built` or `chapter: <id> failed <reason>`, print it, and record `status` and `reason` in `movie.json`; the `disputed:` lines before it go to `not_covered` (D12); a subagent that does not return: print its id and `<movie-dir>`, stop, a resume continues (Review Focus 1); a `workspace`, `narration` or `container` FAIL in a reason stops new starts, as `course.md` says; under `--review` the subagent runs the chapter gate itself (Task 5 adds the table).

- [ ] **Step 1: Write the failing tests** in `tests/test_rung_drift.py`, class `MovieRungCase`, each with a `# red:` comment naming the mutation:
  - `test_the_headings_of_movie_md`: `headings(read(MOVIE_MD), 2) == list(MOVIE_TITLES)`.
  - `test_every_quoted_line_has_one_entry`: the set of `quoted_lines(read(MOVIE_MD), MOVIE_ORDER)` equals the set of `p.quoted for p in MOVIE_PRINTED`.
  - `test_each_quoted_line_matches_its_sample`: for each entry, `line_pattern(p.quoted)` matches `p.sample`.
  - `test_each_evidence_is_code_of_movie_py`: each `p.evidence[1]` is in `code_lines(EXPLAIN / p.evidence[0])`.
  - `test_each_sample_holds_its_evidence`: the printf text of the evidence, with `%s`/`%d` fields turned into `.*`, matches the sample (as the film case does).
  - `test_when_section_holds_the_command_the_rung_line_and_the_refusals`: section "When a movie" holds `/explain <subject> --as movie [--review]`, `Rung: movie (forced)`, `(topic)`, the sentence refusing `conversation` with `video`, and `movie.json` as the resume rule.
  - `test_check_and_stop_names_every_prefix`: section "Check and stop" holds a table row `| \`<prefix>\` |` for each of `MOVIE_PREFIXES`, and the two `plan:` lines.
  - `test_build_names_the_workspace_once_and_the_cap`: section "Build the chapters" holds `video-workspace.sh --engine <engine>`, `At most 3 chapter subagents`, `chapter: <id> built`, `chapter: <id> failed <reason>`, and the sentence for a subagent that does not return (Review Focus 1).
  - `test_movie_md_lints_clean`: `lint(MOVIE_MD) == []` (the helper's shape).
- [ ] **Step 2: Run** `cd skills/explain && python3 -B -m unittest tests.test_rung_drift.MovieRungCase -v`. Expected: every test fails (no `rungs/movie.md`).
- [ ] **Step 3: Write** `rungs/movie.md` sections 1 to 5 as above, the seven stub sections, and fill `MOVIE_PRINTED` for the lines sections 4 and 5 quote (`plan: ok …`, `plan: <n> failures`, `chapter: <id> built|failed` are printed by the rung, not `movie.py`: quote them in the rung but list them in a `MOVIE_RUNG_LINES` tuple the quoted-lines test subtracts, since they have no code evidence).
- [ ] **Step 4: Run** the same command. Expected: PASS. Then `python3 -B -m unittest tests.test_rung_drift`: PASS (no other case changed).
- [ ] **Step 5: Commit** — `git add rungs/movie.md tests/test_rung_drift.py && git commit -m "docs: explain: movie rung, sections 1 to 5, with its drift case"`.

### Task 2: `rungs/movie.md`, sections 6 to 12, and the rest of `MovieRungCase`

**Files:**
- Modify: `rungs/movie.md` (replace the seven stub sections)
- Modify: `tests/test_rung_drift.py` (`MovieRungCase`, `MOVIE_PRINTED`)

**Interfaces:**
- Consumes: Task 1's constants and tests; `movie.py` docstring lines 36 to 90 (the `bridges`, `stitch` and `status` lines).
- Produces: the complete rung; `MOVIE_PRINTED` complete (every `bridges:`, `parts:`, `concat:`, `container:`, `transcript:`, `hub:`, `length:`, `stray:`, `state:` and `chapter:` line of `status` that the rung quotes); `MOVIE_RUNG_TEXTS` (sentences of the rung no code pins, listed below).

Section contents:

6. **Bridges** — step 6: run `movie.py bridges <movie-dir>`; it refuses a plan that fails `check` (prints the failures, writes nothing); else `bridges: ok (<n>)` means the bridge scripts and scenes were written, not rendered; then run `<skill-dir>/scripts/render.sh --engine <engine> <movie-dir>/bridges/<n>` on each bridge, in turn, until its eleven lines are `ok` (`video.md` "Build and check" names them); a bridge render FAIL is a fault of the tooling or of a label (a word over the clip's 45-word budget): fix `movie.json` (the 20-word cap keeps a label short) and run `bridges` again.
7. **Stitch** — step 7: run `movie.py stitch <movie-dir>`; its lines in order, each quoted with its `ok` and `FAIL` forms from the docstring; it refuses while any chapter is not `built` (`parts: FAIL chapter <id> is <status>, not built`); the two exit-1 shapes (Review Focus 2): when `length:` is the only `FAIL`, every artifact is written, so read `chapters.json`, compare each chapter's real duration (the next start minus its start, the last against the container) with its `seconds`, name the chapter to lengthen or shorten, amend its brief and rebuild it (step 5 for that chapter, then steps 6 and 7); any other `FAIL` names the part to fix, and the viewer gate does not run; a short movie that cannot grow (a 4-chapter plan at the floor) gets a fifth chapter, which is a change of plan: go to "Check and stop".
8. **The viewer gate** — step 8: always on; one fresh subagent with `movie/review-viewer.md` (its fill table arrives in Task 4; the sentence and the header-only table as in Task 1); it reads `review/viewer-transcript.html` and the stills under `review/viewer-stills/` that the page names, nothing else of the run; it writes `review/viewer-round-<k>.md`; the author compares each answer with `movie.json` for meaning, not words (Review Focus 3): `understood`, or `missed: <what the film did not show>` with the chapter that fixes it, in a `## Author` block appended to the report; `cannot answer` is `missed`; a `missed` question sends its chapter back to step 5 with `{amendment}` filled, then steps 6 to 8 run again (the bridges are rewritten and re-rendered since their labels may change; `stitch` runs again); two rounds at most; after round 2 a question still missed goes to `not_covered` as `viewer missed: <question>` (STE prose); never ask the viewer to try again in the same round; the gate line printed after the last round: `viewer: <n> of <m> understood`.
9. **Verify and handoff** — step 9 and 10: `stitch` wrote `index.html`; if `movie.json` changed after the gate (a `viewer missed` or `disputed` entry), run `movie.py stitch <movie-dir>` again (stream copy, seconds) and never fill `movie.html` by hand; run `<skill-dir>/scripts/verify.sh <movie-dir>/index.html`: the seven lines of a hub (`self-contained`, `render 1440x900`, `render 500x844`, `citations`, `prose`, `media`, `bpmn`) as `course.md` "Write the hub" lists them; set `state` to `stitched`; the handoff: print the path, `open video.mp4` only when run for the user directly, the narrator line, `viewer: <n> of <m> understood`, one line per `not_covered` entry, a desktop notification if the harness has one.
10. **Resume** — section 7 of the spec: `/explain <movie-dir> --as movie`; `--review` has no effect on a resume (print `--review: no effect on a resume`); run `movie.py status <movie-dir>` and quote its lines; a `failed` or `building` chapter goes to `pending` (edit, then `check`) and its directory moves to `chapters/<id>.stale-<n>/` (Review Focus 4; never delete); a `stray:` line names a directory that is no chapter: leave it, it is not stitched; `state: planned` goes to "Check and stop" step 4 (the approval); `state: building` with pending chapters goes to step 5, with none to step 6; `state: stitched` prints the path and the viewer line from the last `review/viewer-round-<k>.md` and stops; a `built` chapter is never rebuilt unless the viewer gate names it.
11. **Output directory** — the table of spec D9 and 4.5/4.6: `movie.json`, `chapters/<id>/` (a film output directory of `video.md`), `chapters/<id>.stale-<n>/`, `bridges/<n>/` (a clip output directory), `build/` (`concat.txt`, `video.part.mp4`, `hub-sections.html`), `video.mp4`, `chapters.json`, `index.html` (meta `movie`), `review/viewer-transcript.html`, `review/viewer-stills/<k>-<id>.png`, `review/viewer-round-<k>.md`, `chapters/<id>/review/` (the chapter's own stills and gate reports). A movie commits nothing.
12. **Costs** — the list of what wave 3 measures (lines of scene code per second of chapter, render rounds per chapter, viewer gate tokens and rounds, wall time, the word budget per chapter), each marked `not yet measured`; the pointer to `video.md` "First-run costs" for a chapter's render cost. No number in this section until the live run.

- [ ] **Step 1: Write the failing tests** (added to `MovieRungCase`):
  - extend `MOVIE_PRINTED` with every line sections 6 to 10 quote; `test_every_quoted_line_has_one_entry` and the three evidence tests then fail until the sections exist.
  - `test_stitch_section_tells_the_two_exit_shapes_apart`: section "Stitch" holds `length:` as the only `FAIL` case sentence, the words `chapters.json`, and the sentence that the viewer gate does not run on another `FAIL` (Review Focus 2).
  - `test_viewer_gate_compares_meaning_and_caps_two_rounds`: section "The viewer gate" holds `review/viewer-round-<k>.md`, `## Author`, `missed:`, `cannot answer`, `viewer missed: <question>`, `Two rounds at most` (or the sentence as written) and `viewer: <n> of <m> understood` (Review Focus 3).
  - `test_resume_reopens_building_and_failed_chapters`: section "Resume" holds `movie.py status`, `chapters/<id>.stale-<n>/`, `--review: no effect on a resume`, and the sentence that a `built` chapter is never rebuilt unless the viewer gate names it (Review Focus 4).
  - `test_verify_block_matches_the_hub_lines`: the fenced block of section "Verify and handoff" equals `SEVEN_LINES` of `test_course_prompts.py` (import it, or restate `LESSON_PASS.splitlines() + ["media: ok", "bpmn: ok"]`).
  - `test_rung_holds_its_rules`: each text of `MOVIE_RUNG_TEXTS` occurs in the rung: `Build nothing before the user approves the plan.`, `At most 3 chapter subagents`, `never fill \`movie.html\` by hand`, `A chapter is never dropped`, `disputed: <finding>`, `viewer missed: <question>`, `still: viewer-stills/<k>-<id>.png`, `A movie commits nothing.`, `not yet measured`.
  - `test_costs_holds_no_number_yet`: section "Costs" holds no digit run of two or more characters followed by ` s`, ` min` or `tokens` (the live run adds them).
- [ ] **Step 2: Run** `python3 -B -m unittest tests.test_rung_drift.MovieRungCase -v`. Expected: the new tests fail.
- [ ] **Step 3: Write** sections 6 to 12.
- [ ] **Step 4: Run** the same command, then `python3 -B -m unittest tests.test_rung_drift tests.test_course_prompts`. Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -am "docs: explain: movie rung, sections 6 to 12 (bridges, stitch, the viewer gate, handoff, resume)"`.

### Task 3: `movie/chapter-task.md` and its fill table

**Files:**
- Create: `movie/chapter-task.md`
- Modify: `rungs/movie.md` (section 5: the fill table)
- Create: `tests/test_movie_prompts.py`

**Interfaces:**
- Consumes: `PLACEHOLDER`, `fenced_blocks`, `squash` of `test_lesson_prompts.py`; `headings`, `lint`, `read`, `section` of `test_rung_drift.py`; `MOVIE_MD`.
- Produces:
  - `MOVIE_DIR = EXPLAIN / "movie"`, `CHAPTER, VIEWER, REVIEW = "chapter-task.md", "review-viewer.md", "review-chapter.md"`
  - `PLACEHOLDERS = {CHAPTER: frozenset({"skill_dir", "movie_dir", "chapter_id", "chapter_json", "questions_json", "other_chapters", "subject_json", "root", "lang", "review", "amendment"})}` (Tasks 4 and 5 add their keys)
  - `RESULT_LINES = {CHAPTER: ("chapter: {chapter_id} built", "chapter: {chapter_id} failed <reason>")}`
  - `CHAPTER_OVERRIDES: tuple[str, ...]` (the sentences below, as the prompt words them)
  - helpers `prompt(name) -> str` and `placeholders_of(text) -> set[str]`

The prompt, modeled on `course/lesson-task.md`: a header saying it is a template; "Your task" (one chapter of a movie; the chapter as JSON `{chapter_json}`; the viewer questions it answers with their answers and cites as JSON `{questions_json}`; the other chapters as `<id>: <question>` lines `{other_chapters}`; the movie's subject as JSON `{subject_json}`; `{amendment}` is `none` or the author's note after a viewer miss, which changes the picture, never the answers (Review Focus 5)); "What to read" (`{skill_dir}/SKILL.md`, `{skill_dir}/rungs/video.md` and the sections they name; this file wins where they differ); "Overrides": the output directory `{movie_dir}/chapters/{chapter_id}/` (replaces convention 5; write nothing outside it; never write `movie.json`); the script is a `film` whose first scene id is `ask` (it poses the chapter's `question`) and last is `answer` (its narration states each answer of `{questions_json}` so a cold viewer can repeat it); `title` is the chapter's `title`; `provenance.root` is `{root}`, `lang` is `{lang}`, `subject` is `{subject_json}`; the length target is `seconds` of the chapter, within a fifth either way; `picture` and `ends_with` of the chapter guide the picture; cites: copy the cites of `{questions_json}` where the narration makes that claim, read every other cited line from `{root}` first; no `.bpmn` cite; run `python3 {skill_dir}/scripts/movie.py check {movie_dir}` before the first render and fix each `chapter {chapter_id}:` line; run `render.sh` until its eleven lines are `ok`, read the stills by section 6 of `video.md`; never run `open`; the review flag `{review}`: when `on`, run the chapter gate of `{skill_dir}/movie/review-chapter.md` as the rung's section 5 says (rounds, `## Author`, verification reads, the D12 rule: an open finding ships, and the reply holds `disputed: <finding>` lines before the result line); when `off`, start no subagent; the rung line reason `movie chapter {chapter_id}`. "Result": the reply ends with `chapter: {chapter_id} built` or `chapter: {chapter_id} failed <reason>`; the `disputed:` lines come before it.

The fill table in section 5 of the rung (one row per placeholder): `{skill_dir}` the absolute skill dir; `{movie_dir}`; `{chapter_id}`; `{chapter_json}` the chapter object as JSON; `{questions_json}` the question objects of the chapter's `answers`, as a JSON list; `{other_chapters}` each other chapter as `<id>: <question>`, one per line; `{subject_json}` the `subject` object as JSON; `{root}` the absolute root (relative `root` resolved against `<movie-dir>`); `{lang}`; `{review}` `on|off`; `{amendment}` `none`, or the `missed:` text of the last `## Author` block for this chapter.

- [ ] **Step 1: Write the failing tests** in `tests/test_movie_prompts.py`, class `MoviePromptCase`:
  - `test_placeholders_are_exactly_the_named_set`: for each prompt in `PLACEHOLDERS`, `placeholders_of(prompt(name)) == PLACEHOLDERS[name]`.
  - `test_result_lines_present`: each text of `RESULT_LINES[name]` occurs in the prompt.
  - `test_chapter_task_names_the_overrides`: each text of `CHAPTER_OVERRIDES` occurs in `squash(prompt(CHAPTER))`: the output directory sentence, `first scene` … `ask`, `last` … `answer`, `provenance.root` is `{root}`, `no \`.bpmn\``, `movie.py check {movie_dir}`, `Never run \`open\`.`, `Never write \`movie.json\``, `{amendment}` … `never the answers`, `disputed: <finding>`.
  - `test_rung_names_every_placeholder`: the `{name}` set of `read(MOVIE_MD)` equals the union of `PLACEHOLDERS` values (the fill tables).
  - `test_rung_names_prompt_files_that_exist`: each `<skill-dir>/movie/<file>` the rung names is a key of `PLACEHOLDERS` and a file.
  - `test_prompts_lint_clean`: `lint(MOVIE_DIR / name) == []` for each prompt.
- [ ] **Step 2: Run** `python3 -B -m unittest tests.test_movie_prompts -v`. Expected: all fail.
- [ ] **Step 3: Write** the prompt and the fill table.
- [ ] **Step 4: Run** `python3 -B -m unittest tests.test_movie_prompts tests.test_rung_drift.MovieRungCase`. Expected: PASS.
- [ ] **Step 5: Commit** — `git add movie/chapter-task.md rungs/movie.md tests/test_movie_prompts.py && git commit -m "docs: explain: the movie chapter prompt and its fill table"`.

### Task 4: `movie/review-viewer.md` and its fill table

**Files:**
- Create: `movie/review-viewer.md`
- Modify: `rungs/movie.md` (section 8: the fill table)
- Modify: `tests/test_movie_prompts.py`

**Interfaces:**
- Consumes: Task 3's module and constants.
- Produces: `PLACEHOLDERS[VIEWER] = frozenset({"transcript", "stills_dir", "report", "movie_dir", "lang"})`, `RESULT_LINES[VIEWER] = ("viewer: done", "viewer: failed <reason>")`, `VIEWER_TEXTS`.

The prompt, modeled on `lesson/review-page.md` but for a viewer, not a reviewer: "Your task" (you are a cold viewer of one film; you did not make it; you have the transcript and one still per chapter and nothing else; your job is to answer each question at the top of the transcript from the film alone); "Inputs" (`{transcript}`, the absolute path of `review/viewer-transcript.html`; the stills it names as `still: viewer-stills/<k>-<id>.png`, under `{stills_dir}`; read no other file: not `movie.json`, no `script.json`, no chapter transcript, no other still, nothing under `{movie_dir}` beyond these, and no source file; this is an instruction, not a sandbox); "Answer" (for each question, in the language `{lang}`: your answer in your own words in at most three sentences, or `cannot answer`; then what in the film you used: the chapter title and the sentence or the still; guess nothing; a half answer is an answer, with the gap named); "Report" (write `{report}`: a numbered list, one entry per question in the order of the page, each with the question quoted, the answer or `cannot answer`, and the evidence; the last line `viewer: done`; the author appends `## Author`, you do not write it). "Result": the reply ends with `viewer: done` or `viewer: failed <reason>`.

The fill table in section 8: `{transcript}`, `{stills_dir}` (`<movie-dir>/review/viewer-stills`), `{report}` (`<movie-dir>/review/viewer-round-<k>.md`), `{movie_dir}`, `{lang}`.

- [ ] **Step 1: Write the failing tests**: add `VIEWER` to `PLACEHOLDERS` and `RESULT_LINES` (the two generic tests cover it), plus `test_viewer_reads_only_the_transcript_and_its_stills` (`VIEWER_TEXTS` in `squash(prompt(VIEWER))`: `{transcript}`, `still: viewer-stills/`, `not \`movie.json\``, `no \`script.json\``, `no other still`, `cannot answer`, `in your own words`, `guess nothing`, `viewer: done`, `## Author`).
- [ ] **Step 2: Run** `python3 -B -m unittest tests.test_movie_prompts -v`. Expected: the viewer tests fail.
- [ ] **Step 3: Write** the prompt and the table.
- [ ] **Step 4: Run** `python3 -B -m unittest tests.test_movie_prompts tests.test_rung_drift.MovieRungCase`. Expected: PASS.
- [ ] **Step 5: Commit** — `git add movie/review-viewer.md rungs/movie.md tests/test_movie_prompts.py && git commit -m "docs: explain: the movie cold-viewer prompt and its fill table"`.

### Task 5: `movie/review-chapter.md` (the `--review` gate) and its fill table

**Files:**
- Create: `movie/review-chapter.md`
- Modify: `rungs/movie.md` (section 5, under `--review`: the gate rounds and the fill table)
- Modify: `tests/test_movie_prompts.py`

**Interfaces:**
- Consumes: Tasks 3 and 4; `lesson/review-script.md` (the model), `lesson.md` section 6 (the rounds), spec D12.
- Produces: `PLACEHOLDERS[REVIEW] = frozenset({"subject", "root", "files", "chapter_id", "questions_json", "report", "previous"})`, `RESULT_LINES[REVIEW] = ("verdict: ok", "verdict: fix")`, `REVIEW_TEXTS`.

The prompt is `review-script.md` with the page section replaced by the chapter's question and answers: "Your task" (a cold reviewer of one chapter script of a movie on `{subject}`; the artifact is `chapters/{chapter_id}/script.json`); "Inputs" (`{files}`: the script, one absolute path per line; the viewer questions the chapter answers, with their answers and cites, as JSON `{questions_json}`; the root `{root}`; read no other file of the run); "Hunt" as in the model; "Checks": 1. the narration makes no claim the cited lines do not support; 2. the `answer` scene states each answer of `{questions_json}` without contradicting it (it may say less, never something different); 3. the `ask` scene poses the chapter's question; "Round 2" and "Report" as in the model (rulings `resolved`/`open`, verification reads on `-round-2.md`/`-round-3.md`, a finding needs a quoted source line, `verdict: ok|fix` last).

Section 5 of the rung, under `--review`: the chapter subagent runs the gate before its first render: round 1 with `{previous}` `none`; `## Author` appended (`fixed` / `not fixed`); round 2 when the verdict is `fix`; a verification read after a round-2 fix (`-round-3.md`, one more at most as `-round-4.md`); the reports in `chapters/<id>/review/gate-round-<k>.md`; D12: a finding still `open` after the last read ships, the chapter is `built`, and the pair (finding, the author's reason) goes to the reply as `disputed: <finding>` lines, which the orchestrator writes to `not_covered`; a chapter is never dropped. The fill table: `{subject}` the rung line's subject; `{root}`; `{files}`; `{chapter_id}`; `{questions_json}`; `{report}`; `{previous}` `none` or the last report.

- [ ] **Step 1: Write the failing tests**: add `REVIEW` to the two dicts; `test_review_chapter_checks_the_answer_scene` (`REVIEW_TEXTS` in `squash(prompt(REVIEW))`: `{questions_json}`, `\`answer\` scene`, `never something different`, `\`ask\` scene`, `verdict: ok`, `verdict: fix`, `resolved`, `open`, `-round-2.md`, `## Author`); `test_rung_review_rounds_follow_d12` (section "Build the chapters" holds `chapters/<id>/review/gate-round-<k>.md`, `disputed: <finding>`, `A chapter is never dropped`).
- [ ] **Step 2: Run** `python3 -B -m unittest tests.test_movie_prompts -v`. Expected: the new tests fail.
- [ ] **Step 3: Write** the prompt and the rung text.
- [ ] **Step 4: Run** `python3 -B -m unittest tests.test_movie_prompts tests.test_rung_drift tests.test_lesson_prompts`. Expected: PASS.
- [ ] **Step 5: Commit** — `git add movie/review-chapter.md rungs/movie.md tests/test_movie_prompts.py && git commit -m "docs: explain: the movie chapter gate prompt (--review) and its rounds"`.

### Task 6: the `movie` route in `SKILL.md` and `README.md`

**Files:**
- Modify: `SKILL.md` (front matter `argument-hint`; Contract steps 2 and 4; the rung table; the forced-rung bullets; conventions 1 (the "seven rules" sentence), 3 (the movie hub links), 5 (`rungs/movie.md` lists the contents), 6 (`open video.mp4` for a movie); Build procedure step 2; Rung files)
- Modify: `README.md` (the `--as` list in the command line, the description sentence, the Requirements row `movie`, the tree line)
- Modify: `tests/test_rung_drift.py` (`AS_NAMES`; `MOVIE_ROW`; `SkillMdCase`: the "seven rules" sentence in `test_skill_md_routes_the_lesson_rung`, a new `test_skill_md_routes_the_movie_rung`; the README tie)

**Interfaces:**
- Consumes: `SkillMdCase.bullets()`, `section`, `read`, `AS_NAMES`, `README_MD`.
- Produces: `MOVIE_ROW = "| \`movie\` (one film in chapters with bridges, directory output) | Forced only (\`--as movie\`). One theme a viewer must understand from a film alone: viewer questions first, one chapter per answer | One theme, 4 to 15 minutes |"` (word for word); `AS_NAMES = "ste|sheet|page|video|brainrot|lesson|course|onboard|movie"`.

Texts: the forced-rung bullet `The \`movie\` rung builds one film cut into chapters by bridges, with a cold viewer gate. Only \`--as movie\` selects it. The movie rung is English or Russian.`; Contract step 2 `Only the \`lesson\`, \`course\` and \`movie\` rungs have a review.`; step 4 lists nine names; convention 3 gains `For the \`movie\` rung, the hub links to other files only through \`video.mp4\` and \`chapters/<id>/index.html\`.`; convention 5 gains `For a movie, \`rungs/movie.md\` lists the contents.`; convention 6: `\`open video.mp4\` (video, brainrot or movie)`; Build step 2 gains `For a movie, the rung file replaces steps 3 to 6.`; Rung files gains the bullet `\`<skill-dir>/rungs/movie.md\`: the movie rung (the viewer questions, the plan in \`movie.json\`, the stop for approval, one subagent for each chapter, the bridges, the stitch, the viewer gate and the resume).`; README: the command line's `--as` list; a sentence `or a movie (\`--as movie\`: one theme as one film cut into chapters, with generated bridges between them and a cold-viewer gate that checks the film can be understood; it stops for your approval of the plan, and a rerun on its directory resumes)`; the Requirements row `| \`movie\` | the needs of \`lesson\` |`; the tree line adds `movie.md` to the rungs list and `movie/ (the chapter and viewer prompts)`.

- [ ] **Step 1: Write the failing tests**: update `AS_NAMES` and the "seven rules" sentence in `test_skill_md_routes_the_lesson_rung`; add `test_skill_md_routes_the_movie_rung` (the rung table has exactly `MOVIE_ROW`; the flat text holds the forced-rung bullet, the Contract sentence, the convention 3, 5 and 6 texts, the Build step sentence; the Rung files bullet holds `viewer gate` and `bridges`; `MOVIE_MD.is_file()`); extend the README tie (the `--as` list of README's command line equals `AS_NAMES` as the existing test does; `| \`movie\` | the needs of \`lesson\` |` in README).
- [ ] **Step 2: Run** `python3 -B -m unittest tests.test_rung_drift.SkillMdCase -v`. Expected: the movie test and the two updated assertions fail.
- [ ] **Step 3: Edit** `SKILL.md` and `README.md` as above.
- [ ] **Step 4: Run** `cd skills/explain && python3 -B -m unittest discover -s tests`. Expected: `OK` apart from the four baseline failures named in Global Constraints (the run prints exactly those four as FAIL/ERROR and no other).
- [ ] **Step 5: Commit** — `git add SKILL.md ../../README.md tests/test_rung_drift.py && git commit -m "docs: explain: the --as movie route in SKILL.md and README"`.

---

## Rollback and recovery

Every task adds or edits prose and tests only; a revert of a task's commit restores the previous state with nothing to clean. The rung quotes `movie.py` lines rather than defining them, so a wrong quote fails the drift test, not a run.

## Acceptance evidence

```
cd skills/explain && python3 -B -m unittest tests.test_rung_drift tests.test_movie_prompts tests.test_course_prompts tests.test_lesson_prompts
cd skills/explain && python3 -B -m unittest discover -s tests
```

Decisive lines: `OK` from the first; from the second, `FAILED (failures=3, errors=1, …)` naming only the four baseline tests of Global Constraints.
