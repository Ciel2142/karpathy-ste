# Explain film — wave `film-docs` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The rung files describe the film. `rungs/video.md` is rewritten for the film format, `rungs/brainrot.md` holds its own rules and points at `video.md` only by title and only for five shared sections, `SKILL.md` and `README.md` follow, and a drift test ties each stage line and FAIL line that `video.md` quotes to the code that prints it.

**Architecture:** A documentation wave: no code of the pipeline changes. One new always-run test module, `tests/test_rung_drift.py`, holds the drift checks. A table of entries ties each line that `video.md` quotes to one printed sample and to verbatim text of the statement that prints it, which the test finds in a code line of that file. The film limits table of `video.md` is tied to the `film` row of `video/formats.json` and to `MIN_TEXT`, the kit block to `kit/index.ts`, and the pointers of `brainrot.md` to the titles of `video.md`. `tests/test_format_limits.py` loses the explainer column with the rung's table.

**Tech Stack:** Markdown under the STE profile (`skills/ste/scripts/ste_lint.py`), Python 3 `unittest`, bash 3.2 (`/bin/bash` of macOS) for the gated brainrot render.

**Spec:** `docs/superpowers/specs/2026-10-05-explain-film-design.md`. This wave implements §8.1, §8.2 and §8.3, and §8.4 as the text of `video.md`. Wave map: `docs/superpowers/waves/2026-10-05-explain-film.yaml`, wave `film-docs` (ralph wave 7, epic `kp-o7s`). Coverage: waived by the map.

Base: cf29321a9ecea0b52e7ee026976466ccb1784763

Test runs: scoped per task; full suite once, final task.

## Global Constraints

- Work on this wave's own branch and worktree. Never commit to `main`, to `feat/explain-brainrot`, or directly to `feat/explain-film`. Never stage `.beads/`.
- A gated run (`EXPLAIN_VIDEO_E2E=1`) is allowed only when `EXPLAIN_VIDEO_WORKSPACE` is set to the film branch's own workspace. Never render into `~/karpathy/video-workspace`: other sessions use it. Each gated command below starts with `test -n "$EXPLAIN_VIDEO_WORKSPACE"` and prints the path. A command that ends there with no output means the variable is not set: do not render, and report it.
- Only these files change: `skills/explain/rungs/video.md`, `skills/explain/rungs/brainrot.md`, `skills/explain/SKILL.md`, `README.md`, `skills/explain/tests/test_rung_drift.py` (new) and `skills/explain/tests/test_format_limits.py` (Task 3). Nothing under `scripts/`, `video/` or `templates/` changes. Where the code and the spec differ, the rung follows the code at the base, and the difference goes into the wave-close note.
- The two rung files and `SKILL.md` follow the STE profile: `python3 skills/ste/scripts/ste_lint.py <file>` prints `0 errors, 0 warnings` for each (`test_render.py` already pins this for `brainrot.md` and `SKILL.md`). They speak to the author in the imperative, as today. `README.md` is not linted.
- After this wave, none of the four documentation files holds the word `explainer` in any case. A rung file never names a test, a wave or the spec.
- Every pre-existing test case passes unchanged, except those of `test_format_limits.py` that Task 3 names.
- Tests: `unittest`, run from `skills/explain`. Each test names, in a comment, the mutation that turns it red, as the files do today. Each new assertion is seen to fail before the change that makes it pass. One that passes at once is checked by applying its named mutation, seeing the failure, and reverting.
- Baseline at the base (run at planning): `python3 -B -m unittest discover -s tests` gives `Ran 715 tests`, `OK (skipped=49)`.
- Commits: `<type>: explain: <description>`, ending with the attribution line of the session.

## What the closed waves left for this one

Read from the close notes of `kp-sd3`, `kp-fzq`, `kp-xdd`, `kp-osb`, `kp-uu1` and `kp-vv0`. Each is placed in a task.

- Quote the stage lines and the FAIL lines from the header of `render.sh` at the base. The guard stage has five FAIL lines, not the three of spec §7.3: frame, mark, `remotion render exit`, `cannot read` and `cannot copy`. The scene stage has five (Task 1).
- `workspace: FAIL cannot make a run directory in <ws>/runs` is a new line. A signal gives exit 1 and no FAIL line; TERM and HUP wait for the Remotion CLI, `tsc` or the guard pass to end (Task 1).
- `video.md` still says that `app/` holds the sources. Now it holds the installed packages and the two package files, and each render has its own directory in `<ws>/runs` (Task 1).
- A mark error in code that no check frame reaches ends the render stage with `render: FAIL remotion render exit 1`, and the `MARK` line is in `build/render.log` (Task 1, Task 2).
- Films render in Menlo: `ui-monospace` and `"SF Mono"` do not resolve in the renderer, and Menlo's 0.6 em holds the grid within 0.05 px. A wide glyph (emoji, CJK) is not drawn squeezed as spec §5.2 says: it keeps its width, the shortfall is spread over the gaps, and characters drift off `colX`, up to about 14 px (Task 2).
- `marks.ts` has one more error than spec §6 lists: `a mark is a sentence or a word, not both` (Task 2).
- The scene check refuses more than the spec's letter: a comment inside a remotion import clause; two remotion imports on one line; a string alias or a non-ASCII alias in a remotion clause; a string that ends in the word `from` or `import` (cause `import from "<the text up to the next quote, 40 characters>"`); `@ts-nocheck` in any case. A `from "<x>"` in a comment counts. A hidden directory is ignored. The first cause is printed twice. Only `src/film/` is written `scene/` in the `tsc` lines (Task 2, Task 1).
- The guard does not see more than spec §7.3 lists: a text hidden by `display: none` or `visibility: hidden` is measured as visible, and a text that a scene draws after the frame is committed (a state change in an effect) is not measured (Task 2).
- A film scene without cites is allowed for a `topic` or a `conversation` subject. The heading of a film scene in the transcript is its id. The template's `provenance.root` is `.`. In the example's scene `gates`, the mid-sentence still shows one label by design: labels wait for their spoken word (Task 2).
- Measured with the template (8 scenes, 16 sentences, 121 words): 49.0 s with Kokoro, 43.4 s with `say`. That is about 2.8 words each second of speech with Kokoro (Task 2).

## Beyond the letter of the spec

The spec and the map leave these points open. They are decided here, so that every task builds the same thing.

1. **What the drift test reads.** A *quoted line* is the text of an inline code span of `video.md`, or a line of one of its fenced blocks with the outer white space stripped, that starts with one of the eleven stage names of a film run followed directly by `:` or ` (`. Each one, in a table, a list or a paragraph, counts. So a bare `scene: FAIL` is a quoted line with no printed form: write "a FAIL line of the scene stage" in plain text instead.
2. **What "printed" means.** A unit test cannot render. Each quoted line has one entry in `PRINTED`: the line, one sample of it as the pipeline prints it, and evidence, which is verbatim text of the statement that prints it, in the file that holds the statement. The test finds each evidence text in a code line of its file, matches the quoted line against the sample, and finds each evidence text in the sample. Two functions of `render.sh` print `<stage>: FAIL ` for a stage they are given: `run_tool` (before a tool's `FAIL <cause>`, without its `FAIL `) and `copy_clips`. A line that one of them prints gives the call, `run_tool <stage> ` or `copy_clips <stage>`, as the evidence of its prefix.
3. **The lines `video.md` must quote** are `REQUIRED` of Task 1: the eleven `ok` lines, the fallback line and the FAIL lines of a film that an author meets. `video.md` may quote more lines, and each one gets its entry.
4. **The headings of `video.md` are fixed.** Its `##` titles are, in order: `When a video`, `The grammar of a film`, `Write the script`, `Write the scene`, `Build and check`, `Read the stills`, `Handoff, output directory and pinned versions`, numbered `1.` to `7.` Section 5 holds the `###` sections `The FAIL lines`, `First-run costs`, `Narration fallback`, `Render ratio` and `A stopped run`. Section 7 holds `Handoff`, `Output directory` and `Pinned versions and environment`. The five shared titles are `First-run costs`, `Narration fallback`, `Render ratio`, `Handoff` and `Pinned versions and environment`. `brainrot.md` points at them and at nothing else.
5. **The five shared sections hold no film value.** No canvas size, no limit, no voice speed and no word `film`. The film's values are in the limits table of section 3 of `video.md`, and the voice speed is stated by each rung with its narration.
6. **Template and format.** Until the removal wave, `video.md` tells the author to copy `templates/film-script.json` and to keep `"format": "film"` (spec D7). The removal wave owns these two items of `video.md`.
7. **The default-format sentence of `brainrot.md`** is "Without the key, `render.sh` makes a 16:9 video, not a short." Spec §8.2's "is a film" is false until the removal wave, and this sentence is true before and after it.
8. **`tests/test_format_limits.py` changes** (outside the map's `owns` list). Spec §8.2 removes the explainer column of the brainrot limits table, and this test parses that table.
9. **The landscape commands of `README.md` are replaced** by the film's end-to-end command (spec §8.3). The landscape harness stays in `tests/` until the removal wave deletes it, and its own files document its use. The removal wave owns `README.md` only for the template name and the default format, so nobody else removes these lines.
10. **Two pins beyond the map's `done_when`.** The film limits table of `video.md` is tied to the `film` row of `formats.json` and to `MIN_TEXT` of `kit/palette.ts`, and the kit block is tied to `kit/index.ts`. Wave `film-live-run` folds measured values back into those files, so the rung cannot stay behind them.
11. **The length guidance is the measured figures of the template** (last item of the section above). They are estimates for the author, and the `timeline` stage line shows the real length. Wave `film-live-run` folds back better ones.
12. **`SKILL.md`'s line for `brainrot.md` changes too.** Spec §8.3 names only the line for `video.md`, but the contents of `brainrot.md` change.
13. **`video.md` does not quote the command of the guard pass.** Spec §7.3 shows a comma list for `--frames`, and the stage uses one-frame ranges.

## Review Focus

1. A cold author copies the old template, or leaves out `"format": "film"`, and the run builds the wrong video or stops in the `script` stage. Task 2: `test_the_script_section_copies_the_film_template`.
2. The rung names a kit export that does not exist, or leaves one out, and the author's first `tsc` fails. Task 2: `test_the_kit_block_is_the_kit_index`. The shape of each signature is checked against the kit files in the review of Task 2.
3. The author meets a FAIL line that `video.md` does not explain, such as `guard: FAIL cannot copy <out>/<clip>` or the run-directory line. Task 1: `test_every_film_fail_line_is_quoted`.
4. A brainrot author loses the components, the cue rule or the stills faults when they leave `video.md`. Task 3: `test_brainrot_holds_its_own_rules`.
5. A brainrot author reads a film value through a shared section, such as the 1280×720 canvas or speed 1.0. Task 3: `test_the_shared_sections_hold_no_film_value`.

---

### Task 1: the drift test, and sections 5 and 7 of `video.md`

**Files:**
- Create: `skills/explain/tests/test_rung_drift.py`
- Modify: `skills/explain/rungs/video.md` (sections 3 to 6 of the base, lines 108-200, become sections 5 and 7)

**Interfaces:**
- Consumes: the header of `scripts/render.sh` (lines 22-149) and the code of `render.sh`, `scripts/narrate.sh`, `scripts/video-workspace.sh`, `video/check_scene.py`, `video/build-timeline.mjs`, `video/check_budgets.py`, `video/check_render.sh`, `video/verify_sync.py`, `video/src/kit/guard.ts`, `video/src/kit/marks.ts`.
- Produces, for Tasks 2 to 4:

  ```python
  # tests/test_rung_drift.py
  EXPLAIN: Path                      # skills/explain
  VIDEO_MD: Path; BRAINROT_MD: Path; SKILL_MD: Path
  FILM_ORDER: tuple[str, ...]        # the eleven stage names of a film run, in order
  SHARED_TITLES: tuple[str, ...]     # the five titles of decision 4
  class Printed(NamedTuple):
      quoted: str                                  # the line exactly as video.md quotes it
      sample: str                                  # one line as the pipeline prints it
      evidence: tuple[tuple[str, str], ...]        # (path under skills/explain, verbatim text of a code line)
  PRINTED: tuple[Printed, ...]
  REQUIRED: tuple[str, ...]
  def read(path: Path) -> str                     # the text of a file, UTF-8
  def quoted_lines(text: str) -> list[str]
  def line_pattern(quoted: str) -> re.Pattern
  def code_lines(path: Path) -> list[str]
  def headings(text: str) -> list[tuple[int, str]]   # (level, title), "<n>. " removed, in order
  def section(text: str, title: str) -> str          # the body under the one heading with that title
  def lint(path: Path) -> subprocess.CompletedProcess
  ```

  `FILM_ORDER` is `("script", "workspace", "scene", "narration", "timeline", "guard", "render", "container", "sync", "stills", "transcript")`. `SHARED_TITLES` is `("First-run costs", "Narration fallback", "Render ratio", "Handoff", "Pinned versions and environment")`. `REQUIRED` holds these lines, in this order:

  ```
  script: ok (<n> scenes)
  workspace: ok <ws>
  scene: ok (<n> files)
  narration (<engine>): ok[ (fallback: <cause>)]
  timeline (<n> scenes, <s> s): ok
  guard (<n> frames): ok
  render (<s> s, <ratio> render-min/video-min)[ (limit 2.0)]: ok
  container: ok (<s> s)
  sync: ok
  stills (<n>): ok <review-dir>
  transcript: ok
  narration: FALLBACK say (<cause>)
  script: FAIL provenance.root must be an absolute path
  script: FAIL scene <id>: a film scene has no component or props
  script: FAIL scene <id>: pause <v> must be an integer from 12 to 90
  script: FAIL source <id>: <cause>
  workspace: FAIL cannot make a run directory in <ws>/runs
  scene: FAIL no scene directory: <path>
  scene: FAIL no Film.tsx
  scene: FAIL <name> is a directory
  scene: FAIL <name> is not a .ts or .tsx file
  scene: FAIL Film.tsx has no "export function Film("
  scene: FAIL <file>:<line>: import from "<source>"
  scene: FAIL <file>:<line>: "<name>" from remotion
  scene: FAIL <file>:<line>: token "<token>"
  scene: FAIL cannot copy the scene to <path>
  scene: FAIL types: <cause>
  scene: FAIL tsc: <first error line>
  timeline: FAIL scene <id> is <s> s (max <max>, film)
  timeline: FAIL total <s> s (max <max>, film)
  guard: FAIL frame <f> (scene <id>): <fault>[; <fault> ...]
  guard: FAIL mark: scene <id>: <cause>
  guard: FAIL remotion render exit <n> (log <path>)
  guard: FAIL cannot read <out>/build/timeline.json
  guard: FAIL cannot copy <out>/<clip>
  render: FAIL remotion render exit <n> (log <path>)
  ```

- [ ] **Step 1: Write the helpers and their tests.** Contracts:
  - `quoted_lines`: decision 1. It returns the lines in the order of the text, repeats included. A span on a line inside a fenced block is not an inline span. A fenced line is stripped of its outer white space.
  - `line_pattern`: a `<`, then characters other than `>`, then `>` is a placeholder that matches one or more characters. A `[` that is directly followed by a space or a `;` opens an optional part, which its matching `]` closes. Every other character matches itself, a `[` among them. The pattern matches the whole line (`fullmatch`).
  - `code_lines`: for a `.sh` file, each line whose first character that is not white space is not `#`. For a `.py` file, the same, after the last line of the module docstring. For a `.ts`, `.tsx` or `.mjs` file, each line whose stripped text does not start with `//`, `/*` or `*`.
  - `headings`: every line that starts with one to six `#` and a space, outside fenced blocks. A leading `<digits>. ` is removed from the title.
  - `section`: the lines after the one heading with that title, up to the next heading of the same level or a higher one (fewer `#`). It raises `AssertionError` when the title is not exactly one heading.
  - `lint`: `python3 skills/ste/scripts/ste_lint.py <path>`, run from the repository root.

  Class `HelperCase(unittest.TestCase)`:
  - `test_quoted_lines_reads_spans_and_fenced_lines`: a made-up text with `script: ok (<n> scenes)` in a table cell, a fenced block that holds the line `  guard (<n> frames): ok`, and the spans `script.json`, `render.sh`, `scene/` and `scripts: x` gives exactly `["script: ok (<n> scenes)", "guard (<n> frames): ok"]`. Red: fenced lines skipped, or `script.json` taken.
  - `test_line_pattern`: `narration (<engine>): ok[ (fallback: <cause>)]` matches `narration (say): ok` and `narration (say): ok (fallback: no uv)`, and does not match `narration (say): ok (fallback`. `FAIL source #<n>: id must match [a-z0-9-]` matches `FAIL source #2: id must match [a-z0-9-]`. `a <x> b` does not match `a  b`. Red: every `[` made optional, or a placeholder that matches nothing.
  - `test_code_lines_drop_comments`: in temporary files, a `.sh` line `# FAIL a` is dropped and `echo "FAIL a"` is kept; a `.py` file whose module docstring holds `FAIL a` keeps only its line `print("FAIL a")`; in a `.ts` file the lines `// a`, `/* a` and ` * a` are dropped and `const a = 1;` is kept. Red: the docstring is kept, or a comment line is kept.
  - `test_section_and_headings`: on a made-up text, `headings` drops `1. ` from `## 1. Title`, and `section` stops at the next heading of the same level and not at a deeper one. A title of two headings raises. Red: the body runs to the end of the file.

- [ ] **Step 2: Write the drift tests.** Class `StageLineDriftCase(unittest.TestCase)`:
  - `test_every_quoted_line_has_one_entry`: the set of `quoted_lines(read(VIDEO_MD))` equals the set of `quoted` of `PRINTED`, and no two entries share a `quoted`. Red: `video.md` quotes a line with no entry, or an entry stays for a line that `video.md` no longer quotes.
  - `test_each_quoted_line_matches_its_sample`: `line_pattern(quoted)` matches `sample`, for each entry. Red: a quoted line reworded so that it no longer describes what is printed.
  - `test_each_evidence_is_code_of_its_file`: each evidence text occurs in one line of `code_lines(EXPLAIN / path)`. An evidence that is not a call (decision 2) has at least 4 characters and holds none of `"`, `'`, `$`, `%`, `{`, `}`. Red: `render.sh` or a tool rewords the statement, or the evidence is taken from a comment.
  - `test_each_sample_holds_its_evidence`: each evidence text that is not a call occurs in `sample`. A call requires that `sample` starts with `<stage>: FAIL `, for the stage that it names. Each entry has one evidence that gives its stage: a text that starts with the stage name of its quoted line followed by `:` or ` (`, or a call that names that stage. Red: an entry whose evidence belongs to another line.
  - `test_the_ok_lines_are_the_eleven_of_a_film_run`: the quoted lines that hold `: ok`, without repeats, in the order of their first appearance in `video.md`, have the stage names `FILM_ORDER`. Red: `video.md` lists the explainer's nine lines, or the guard comes before the timeline.
  - `test_every_film_fail_line_is_quoted`: each line of `REQUIRED` is in `quoted_lines(read(VIDEO_MD))`. Red: a FAIL line of the scene or guard stage is not in the rung.
  - `test_video_md_lints_clean`: `lint(VIDEO_MD)` exits 0 and prints exactly `0 errors, 0 warnings`. Red: a rung line breaks the STE profile.

  `PRINTED` starts empty in this step. Each of the three tests that loop over the entries first asserts that `PRINTED` is not empty, so that none passes on an empty table. Each test's comment names its red mutation, and the module docstring says what the module ties to what (decisions 1 and 2).

- [ ] **Step 3: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift`
  Expected: `FAILED`. `HelperCase` and `test_video_md_lints_clean` pass. The four entry tests fail: the base's quoted lines have no entry, and `PRINTED` is empty. The `ok` lines test fails (nine names, no `scene`, no `guard`). The required test fails on the first `scene: FAIL` line.

- [ ] **Step 4: Rewrite sections 3 to 6 of the base as sections 5 and 7 of `video.md`.** Sections 1 and 2 of the base stay until Task 2, so the numbers jump for one task. The text quotes each line of `REQUIRED` exactly as written above. The meaning of each line comes from the header of `render.sh`. The text names no limit value: it points at the limits table of section 3, which Task 2 writes. Contract:
  - `## 5. Build and check`: the command `<skill-dir>/scripts/render.sh <output-dir>`, and `--engine say` only when the user asks in words for the macOS voice. The command prints one line for each stage, in order. It stops at the first `FAIL` line, which names the cause, and the tool's output follows it, indented. A table `| Stage line | Meaning |` gives the eleven `ok` lines in the order of `FILM_ORDER`: what each stage checked or made, which file it wrote (`build/timeline.json` with the marks and the check frames, `build/guard.log`, `video.mp4` and `build/render.log`, `review/`, `index.html`), and that the `scene` and `guard` stages come before the costly steps, so that a fault costs no synthesis or no full render. The narration speaks at speed 1.0. The section ends by sending the author to section 6 to read the stills.
  - `### The FAIL lines`: each FAIL line of `REQUIRED`, grouped by stage, with its cause and what to do. These facts must be in it. `provenance.root` must be absolute, and the template's root is `.`. The seven scene causes are those of `check_scene.py`. Every cause of the check follows the stage line, indented, so the first cause is printed twice. The `tsc` lines name the files `scene/<file>`. The frame line names the faults `OFFCANVAS`, `SMALLTEXT` and `OVERLAP`, and their fixes are the three honest fixes of section 4. The mark line names the scene and the cause of `marks.ts`. For `remotion render exit`, read the log, where the error line is near its top. A `render: FAIL remotion render exit 1` whose `build/render.log` holds a `MARK scene` line is a mark error at a frame that the guard did not check. Never edit a file in `build/`: run `render.sh` again.
  - `### First-run costs`: the text of the base (lines 131-140). `### Narration fallback`: the text of the base (lines 142-146). `### Render ratio`: the text of the base (lines 148-149). Each says "the run", not "a film run" (decision 5).
  - `### A stopped run`: HUP, INT or TERM ends the run with exit 1 and no FAIL line. TERM or HUP during `tsc`, the guard pass or the render waits for that tool to end, which can take minutes in a long render. Ctrl-C stops the tool at once. The run directory goes in each case, and a later run removes one that a killed run left, after a day.
  - `## 7. Handoff, output directory and pinned versions` with `### Handoff`: the steps of the base (lines 167-170). `### Output directory`: a table of `script.json`, `scene/` (the picture that you wrote; a `script.gen.ts` there is ignored and overwritten), `index.html` (the transcript: the narration and the cites of each scene, under a heading that is the scene id), `video.mp4`, `narration.md`, `audio/` (`<id>.<engine>.wav`, its sidecar `<id>.<engine>.txt` and `<id>.<engine>.words.json` for each scene, and `durations.json`), `build/` (`timeline.json`, `guard.log`, `guard.mp4`, `render.log`, `rendered-audio.wav`) and `review/` (`still-NN-<id>-s<k>.png`, `still-NN-<id>-end.png`). `### Pinned versions and environment`: the bullets of the base (lines 186-200), with these changes. The voice bullet keeps the voice and the sample rates and drops the speed. The workspace bullet says that `app/` holds the installed packages and the two package files (`package.json`, `package-lock.json`), that `runs/` holds one directory for each render, removed when the render stops, so that two renders can run at the same time, and that `models/` holds the Kokoro files. The Constants bullet goes.

- [ ] **Step 5: Write the entries.** One `Printed` for each quoted line of the new text, `REQUIRED` and any other. Take the sample from the header of `render.sh`, from the header of the tool, or from an assertion of an existing test, with each placeholder filled in. Take the evidence from the code: the longest piece of printed text of the statement that holds no interpolation and no quote mark. For a line that `run_tool` or `copy_clips` composes, take the call in `render.sh` (`run_tool scene `, `copy_clips guard`) and the text of the tool's line. The sample of the frame line holds one fault.

- [ ] **Step 6: Run them and see them pass.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift tests.test_render`
  Expected: `OK`; the gated cases are skipped.

  Run: `python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/video.md`
  Expected: `0 errors, 0 warnings`.

- [ ] **Step 7: Commit.**

  ```bash
  git add skills/explain/tests/test_rung_drift.py skills/explain/rungs/video.md
  git commit -m "docs: explain: video.md builds and checks a film; a drift test ties each quoted line to the code that prints it"
  ```

- [ ] **Step 8: Check the cases that passed at once.** After the commit, so that a revert loses nothing. For each case of `HelperCase`, and for `test_video_md_lints_clean`, apply its first named mutation (to the helper, or a contraction in a sentence of `video.md`), run the case, see it fail, and revert with `git checkout -- skills/explain/`. Then check the drift itself twice, each time reverting after. Change `scene: FAIL tsc: ` in a code line of `render.sh` to `scene: FAIL typecheck: `, and see `test_each_evidence_is_code_of_its_file` fail. Change the quoted `guard (<n> frames): ok` of `video.md` to `guard (<n> checks): ok`, and see `test_every_quoted_line_has_one_entry` fail. Then two edits of the table: the sample of `sync: ok` written `sync: okay` makes `test_each_quoted_line_matches_its_sample` fail, and the evidence of the `guard: FAIL frame` entry given to the `scene: FAIL tsc:` entry makes `test_each_sample_holds_its_evidence` fail. `git status --short` prints nothing at the end.

---

### Task 2: sections 1 to 4 and 6 of `video.md`: the grammar, the script, the scene, the stills

**Files:**
- Modify: `skills/explain/rungs/video.md` (sections 1 and 2 of the base become sections 1 to 4; a new section 6)
- Modify: `skills/explain/tests/test_rung_drift.py` (new class `FilmRungCase`; entries for any new quoted line)

**Interfaces:**
- Consumes: `VIDEO_MD`, `read`, `quoted_lines`, `headings`, `section`, `PRINTED` (Task 1); `fill(template, row)` of `tests/test_format_limits.py`; the `film` row of `video/formats.json`; `MIN_TEXT` of `video/src/kit/palette.ts`; the exports of `video/src/kit/index.ts`; `templates/film-script.json`.
- Produces: the final headings of `video.md` (decision 4), for Task 3. In the test module:

  ```python
  FILM_CELLS: tuple[tuple[str, str], ...]   # (row label, template); fill() makes the cell from the film row and minText
  def film_limits_table() -> dict[str, str]  # label -> cell of the one table of video.md headed "| Limit | film |"
  def kit_exports() -> set[str]              # the names that video/src/kit/index.ts exports
  def rung_kit_names() -> set[str]           # the names declared by the export lines of the ts blocks of section "Write the scene"
  ```

  `FILM_CELLS`, in this order:

  ```
  ("canvas", "{width}×{height}")
  ("scenes", "{minScenes}–{maxScenes}")
  ("max scene length", "{maxSceneSeconds} s")
  ("max total length", "{maxTotalSeconds} s")
  ("narration words per scene", "{maxNarrationWords}")
  ("lead / default pause frames", "{leadFrames} / {pauseFrames}")
  ("source lines", "{sourceLines}")
  ("smallest text", "{minText} px")
  ```

  `minText` is the integer of the line `export const MIN_TEXT = <n>;` of `palette.ts`. `kit_exports` reads the names of each `export { ... } from` and `export type { ... } from` clause of `index.ts`, and each name that `export type <Name>` declares there. That is 25 names at the base. `rung_kit_names` reads each line of a fenced `ts` block of section `Write the scene` that starts with `export`, and takes the one name that the line declares (`export const <Name>`, `export function <Name>`, `export type <Name>`).

- [ ] **Step 1: Write the failing tests.** Class `FilmRungCase(unittest.TestCase)`:
  - `test_the_headings_of_video_md`: the level-2 titles of `headings(read(VIDEO_MD))` are, in order, those of decision 4. Red: a section is missing, or two are swapped.
  - `test_film_limits_table_matches_formats`: `film_limits_table()` equals, label by label, `FILM_CELLS` filled by `fill` from the `film` row with the key `minText` added. Red: a value changed in `formats.json` or `palette.ts` and not in the rung, or a row on one side only.
  - `test_the_kit_block_is_the_kit_index`: `rung_kit_names() == kit_exports()`. Red: a kit export missing from the rung, or a rung name that the kit does not export (`MonoRun`, `makeAt`).
  - `test_the_script_section_copies_the_film_template`: section `Write the script` holds `templates/film-script.json` and `"format": "film"`, and `video.md` does not hold `video-script.json`. The format of the template file is `film`. Red: the rung names the old template.
  - `test_video_md_has_no_components`: `video.md` holds none of `bullets-appear`, `diagram-with-highlight-walk`, `code-with-line-highlights`, `before-after` and `cue rule`, and not `explainer` in any case. Red: a row of the old components table is left in.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift.FilmRungCase`
  Expected: `FAILED`; each of the five cases fails on the base's sections 1 and 2.

- [ ] **Step 3: Write sections 1 to 4 and 6.** Contract:
  - `## 1. When a video`: the text of the base (lines 4-14), where "A video has at most 8 scenes" becomes a pointer at the scene limit of the table in section 3, with no number.
  - `## 2. The grammar of a film`: the five rules of spec §8.1 item 2, as rules to the author. One picture for the whole film: objects stay and change, and the stage is never cleared between scenes. Each scene changes the picture while the voice speaks; a scene is one or two sentences, with one motion for each sentence. Decide the picture first, then write the narration that fits it. Text on the stage is a label, a source line in a code card, or a claim under test; a list of sentences is a fault. A colour has one meaning: yellow the subject, blue chosen, green pass, red fail (`C.yellow`, `C.blue`, `C.green`, `C.red`).
  - `## 3. Write the script`: copy `<skill-dir>/templates/film-script.json` to `<output-dir>/script.json` and keep `"format": "film"`. The template is the worked example, about how `/explain` checks an artifact. Replace every value, and replace the root `.` with the absolute path of the repository root. The provenance recipe of `rungs/sheet.md` section 4. A table of the top-level keys of spec §4.2 (`title`, `subject`, `provenance` with `not_covered`, `format`, `sources`, `scenes`). A table of the scene keys (`id`, `narration`, `cites`, `pause`), each with its rule from spec §4.2: a scene without cites is allowed only for a `topic` or a `conversation` subject, and a film scene has no `component`, `props` or cue. The rules for each scene from lines 37-54 of the base, but the prose lint reads only the narration and `provenance.not_covered` of a film, never the labels of the scene. `sources`: each entry `{ "id", "path", "from", "to" }`, a range in a file under the root, the only text that the code card can show, tabs as 4 spaces; a file with a NUL byte fails. A table headed `| Limit | film |` whose rows are `FILM_CELLS` with their values, in that order. The length guidance from the measured figures (decision 11): the narrator speaks about 2.8 words each second, each scene adds 0.6 s of lead and pause, and each sentence after the first adds 0.15 s. The example has 8 scenes, 121 words and 49 s. A safe total for the longest film is about 350 words. The `timeline` stage line shows the real length.
  - `## 4. Write the scene`: copy `<skill-dir>/video/src/film/` to `<output-dir>/scene/`, and the rules of spec §4.3. The stage of spec §5.1: one SVG of 1280×720 holds `Film`, at 30 fps; `Film` returns SVG elements only and reads the frame with `useCurrentFrame()`; its props are `Props` of `./script.gen`, with the scene and source ids as types. The kit: one fenced `ts` block with each export of `kit/index.ts` on its own `export` line. Its signature is copied from the kit file that defines it at the base: `palette.ts`, `motion.ts`, `marks.ts`, `source.ts`, `text.tsx`, `draw.tsx`, `mono.ts`, `code.tsx`, and `index.ts` for `FilmProps`. Then the behaviours of spec §5.2. The Mono rule: `x + index * 0.6 * size` is the position of a character; films render in Menlo; a wide glyph drifts off `colX` (the closed waves' fact), so keep a code card and Mono text to characters of one column. Marks: every rule of spec §6, and every error of `marks.ts` with its text, the mixed-mark error among them. Time every motion from a mark: a number in scene code is a length in frames, never a position in time. A word mark is about when the word is said, and a motion that needs an exact frame uses a sentence mark. End a motion that starts at a sentence mark before the middle of that sentence, where the guard measures and the still is cut. The floor of `MIN_TEXT` px at the drawn size, with a scale included. The import and token rules of spec §7.2, then the refusals beyond them (the closed waves' list), then: a token or a `from "<x>"` in a comment counts; the type check is strict, and an unused local or import fails `tsc`. The three honest fixes of spec §7.3, and that no fault is exempt. What the guard does not see: spec §7.3's list, the two additions of the closed waves, and a mark error at a frame that is not checked.
  - `## 6. Read the stills`: read each file in `review/` with the Read tool, and never read `video.mp4`. `still-NN-<id>-s<k>.png` is the middle of sentence k of scene NN, and `still-NN-<id>-end.png` is the scene's last frame. These are the frames that the guard measured. The five faults of spec §8.4. A still in the middle of a sentence shows that moment: a label that waits for a later word is not there yet, and that is not a fault. Fix each fault in `script.json` or in `scene/`, and run `render.sh` again in the same output directory. The run keeps the WAV file of a scene whose narration did not change. Repeat until all eleven lines show `ok` and the stills are clean.

- [ ] **Step 4: Run the tests and the lint.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift`
  Expected: `OK`. A line that sections 1 to 4 and 6 quote with no entry fails `test_every_quoted_line_has_one_entry`; add its entry as in Task 1 Step 5, then run again.

  Run: `python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/video.md`
  Expected: `0 errors, 0 warnings`.

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/rungs/video.md skills/explain/tests/test_rung_drift.py
  git commit -m "docs: explain: video.md teaches the film: grammar, script, scene and kit, marks, stills"
  ```

---

### Task 3: `brainrot.md` holds its own rules

**Files:**
- Modify: `skills/explain/rungs/brainrot.md` (all)
- Modify: `skills/explain/tests/test_format_limits.py` (module docstring; `TABLE_HEADER` at 24; `CELL_TEMPLATES` at 28-45; `expected_cells` at 62-67; `rung_limits_table` at 74-87)
- Modify: `skills/explain/tests/test_rung_drift.py` (new class `BrainrotRungCase`)

**Interfaces:**
- Consumes: `VIDEO_MD`, `BRAINROT_MD`, `SHARED_TITLES`, `read`, `headings`, `section` (Task 1), and the titles of `video.md` that Task 1 writes; the text of the base's `video.md` from `git show cf29321a9ecea0b52e7ee026976466ccb1784763:skills/explain/rungs/video.md`.
- Produces: in the test module, `def blocks(text: str) -> list[str]`: the text split at blank lines, outside fenced blocks, with each heading line a block of its own. In `test_format_limits.py`: `CELL_TEMPLATES` becomes `(label, brainrot template)` pairs, and `expected_cells` and `rung_limits_table` return `label -> brainrot cell`.

- [ ] **Step 1: Write the failing tests.** Class `BrainrotRungCase(unittest.TestCase)`. A *pointer block* is a block of `brainrot.md` that holds `video.md` and is not a heading.
  - `test_brainrot_points_at_the_five_shared_titles`: each pointer block holds at least one of `SHARED_TITLES` in double quotes (`"First-run costs"`). A heading title of `video.md` that a pointer block holds in double quotes is one of `SHARED_TITLES`. Each of the five is held in double quotes by some pointer block. Red: a pointer by number, a pointer to another section of `video.md`, or a shared section that `brainrot.md` never names.
  - `test_brainrot_names_no_section_of_video_md_by_number`: no pointer block holds `section` or `Section` followed by a space and a digit. Red: "as in section 3 of `video.md`".
  - `test_each_shared_title_is_one_heading_of_video_md`: each of `SHARED_TITLES` is the title of exactly one heading of `video.md`. Red: a title of `video.md` changed and `brainrot.md` left pointing at it.
  - `test_the_shared_sections_hold_no_film_value`: `section(read(VIDEO_MD), title)` holds none of `film`, `Film`, `1280`, `720`, `scene/`, `eleven` and `speed`, for each shared title. Red: speed 1.0 or the canvas in `Pinned versions and environment`.
  - `test_brainrot_holds_its_own_rules`: the level-2 titles of `brainrot.md` include `Write the script`, `Components`, `The cue rule`, `Read the stills`, `Output directory` and `Constants`. Section `Components` holds each of `title`, `bullets-appear`, `diagram-with-highlight-walk`, `code-with-line-highlights` and `before-after` in backticks, and `brainrot.md` does not hold `explainer` in any case. Red: the components table left with neither rung.

  In `test_format_limits.py`: `TABLE_HEADER` becomes `| Limit | brainrot |`, and the explainer template goes from each row of `CELL_TEMPLATES`. `rung_limits_table` reads two cells, and `test_rung_table_matches_formats` compares `label -> brainrot cell`. The docstring stops naming the explainer. Its other cases stay as they are.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift.BrainrotRungCase tests.test_format_limits`
  Expected: `FAILED`. The two pointer cases and `test_brainrot_holds_its_own_rules` fail on the base's text. `test_rung_table_matches_formats` fails: the rung has no table headed `| Limit | brainrot |`. `test_each_shared_title_is_one_heading_of_video_md` and `test_the_shared_sections_hold_no_film_value` pass on Task 1's text; Step 6 checks them.

- [ ] **Step 3: Rewrite `brainrot.md`.** Its `##` titles are, in order: `When a brainrot short`, ``What to read in `rungs/video.md` ``, `Write the script`, `Components`, `The cue rule`, `The background`, `Build and check`, `Read the stills`, `Handoff`, `Output directory`, `Constants`, numbered `1.` to `11.` Contract:
  - The lines under the title say only that `SKILL.md` has the generic rules. They do not name `video.md`.
  - Section 1: the text of the base, unchanged (test_render pins its English-only rule).
  - Section 2: one paragraph that names the five shared titles in double quotes as the sections of `<skill-dir>/rungs/video.md` to read, says that this file wins where the two differ, and says that the rest of `video.md` is for another format. A table `| Section of video.md | Use |` gives each title with what brainrot takes from it. No block that names `video.md` holds a section number, of either file.
  - Section 3: copy `templates/brainrot-script.json` and keep `"format": "brainrot"`, with the sentence of decision 7. The key table and the rules for each scene from lines 25-54 of the base's `video.md`: the `scenes` row says 3 to 6, and the length bullet of lines 42-45 goes (the brainrot length bullet replaces it). The limits table with the column `brainrot` only, and the sentence after it about the format in a limit failure. The bullets of the base's section 3 (length, hook, before and after, captions, code). Its `Cues` bullet goes: section 5 holds the rule. The `awk` command and the example `(max 40, brainrot)` each occur once in the file, and the code and caption sentences that `test_format_limits.py` pins stay word for word.
  - Section 4: the components table and its bullets from lines 56-79 of the base's `video.md`. The props stay and the numbers go: each limit is in the table of section 3, and the code bullet says so.
  - Section 5: the five rules and the example table of lines 81-106 of the base's `video.md`. The cue frame is the exact start of its sentence, from the words file of the narration. The `script` stage checks the first four rules, and the `timeline` stage checks the distance. The explainer's frame formula and its accuracy sentence go.
  - Section 6: the base's section 4, unchanged.
  - Section 7: the command, and the ten stage lines of the base's section 5 with their meanings. The first-run costs, the narration fallback and the render ratio, each by its title in `video.md`.
  - Section 8: read each still with the Read tool, and never read `video.mp4`. `still-NN-<scene>.png` shows scene NN at its start, after the fade-in. `still-NN-<scene>-<k>.png` shows cue k, 15 frames after the cue frame, and k counts the cues in frame order. The four faults of the base's `video.md` (line 157-159) and the three brainrot faults of the base's section 5, then the fix loop, until all ten lines show `ok`.
  - Section 9: follow "Handoff" of `video.md`, and also tell the user the speed 1.2 and the background.
  - Section 10: the whole table of the output directory (the base's `video.md` lines 174-182 and the three brainrot rows), with no pointer.
  - Section 11: the base's section 8, and "Pinned versions and environment" of `video.md` for the versions, the models and the workspace.

- [ ] **Step 4: Run the tests and the lints.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift tests.test_format_limits tests.test_render`
  Expected: `OK`; the gated cases are skipped.

  Run: `python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/brainrot.md`
  Expected: `0 errors, 0 warnings`.

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/rungs/brainrot.md skills/explain/tests/test_format_limits.py skills/explain/tests/test_rung_drift.py
  git commit -m "docs: explain: brainrot.md holds its own scene rules, components, cue rule, stills and constants"
  ```

- [ ] **Step 6: Check the cases that passed at once.** After the commit. Rename `### Handoff` of `video.md` to `### Hand over`: `test_each_shared_title_is_one_heading_of_video_md` fails. Add the sentence "The voice speaks at speed 1.0." to `### Pinned versions and environment`: `test_the_shared_sections_hold_no_film_value` fails. Revert each with `git checkout -- skills/explain/`. `git status --short` prints nothing at the end.

---

### Task 4: `SKILL.md` and `README.md`, and the wave's acceptance

**Files:**
- Modify: `skills/explain/SKILL.md` (Build procedure step 2 at 127-129; the lines for `video.md` and `brainrot.md` under Rung files at 143-146)
- Modify: `README.md` (the rung description at 9-16; Layout at 59-65; Tests at 72-75)
- Modify: `skills/explain/tests/test_rung_drift.py` (new class `SkillMdCase`)

**Interfaces:**
- Consumes: `SKILL_MD`, `read`, `section` (Task 1); the rung files of Tasks 1 to 3.
- Produces: nothing that a later task calls.

- [ ] **Step 1: Write the failing test.** Class `SkillMdCase(unittest.TestCase)`, `test_skill_md_describes_the_film_rung`: in section `Build procedure` of `SKILL.md`, item 2 (from its line that starts with `2. ` up to the line that starts with `3. `) holds `scene/`. In section `Rung files`, a bullet is its `- ` line and the indented lines below it. The bullet of `rungs/video.md` holds `scene` and holds neither `components` nor `cue rule`. The bullet of `rungs/brainrot.md` holds `components`. Red: the lines of the base.

- [ ] **Step 2: Run it and see it fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift.SkillMdCase`
  Expected: `FAILED`, on item 2.

- [ ] **Step 3: Edit `SKILL.md` and `README.md`.** Contract:
  - `SKILL.md` Build procedure step 2: for a video, the rung file replaces steps 3 to 6: write `script.json` and the scene directory `scene/`, run `render.sh`, read the stills. For a brainrot short, it replaces them too: write `script.json`, run `render.sh`, read the stills. Rung files: `video.md` is the video rung (the grammar of a film, the script, the scene and its kit, the marks, the render pipeline, the stills, the pinned versions). `brainrot.md` is the brainrot rung (its script, components and cue rule, the limits, the background folder, the checks of the stills, and the sections of `video.md` that it shares). The rest of `SKILL.md` stays word for word, so that the cases of `test_render.py` still hold.
  - `README.md`: the description of `/explain` calls the video rung a narrated film, one continuous picture written for the subject and timed to the narration, with a cited transcript. The brainrot part stays. Layout: the `skills/explain/` line also names `video/src/kit/` (the film kit) and `video/src/film/` (the worked example). Tests: the two landscape lines go (decision 9), and in their place this line, with a comment that says it renders the worked film and its planted faults and needs the workspace:

    ```
    EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film
    ```

    The requirements table and the install steps do not change.

- [ ] **Step 4: Run the test and the lint.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift tests.test_render`
  Expected: `OK`; the gated cases are skipped.

  Run: `python3 skills/ste/scripts/ste_lint.py skills/explain/SKILL.md`
  Expected: `0 errors, 0 warnings`.

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/SKILL.md README.md skills/explain/tests/test_rung_drift.py
  git commit -m "docs: explain: SKILL.md and README describe the film rung"
  ```

- [ ] **Step 6: Run the full unit suite, once.**

  Run: `cd skills/explain && python3 -B -m unittest discover -s tests`
  Expected: `OK (skipped=49)`, as at the base. No failure and no error. The test count is the base's 715 plus this wave's new cases.

- [ ] **Step 7: Run the map's acceptance.**

  Run: `python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/video.md && python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/brainrot.md`
  Expected: `0 errors, 0 warnings`, two times.

  Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift`
  Expected: `OK`, no skip.

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_brainrot`
  Expected: the workspace path, then `OK` with no skip: brainrot renders from its template with ten `ok` lines (`BrainrotRenderCase`).

  Then check the tree. `git grep -n -i explainer -- skills/explain/rungs skills/explain/SKILL.md README.md` prints nothing. `git status --short` prints nothing. `git diff --stat cf29321a9ecea0b52e7ee026976466ccb1784763 -- . ':!docs'` lists only the six files of the Global Constraints. `ls "$EXPLAIN_VIDEO_WORKSPACE/runs"` prints nothing.

## Wave close

The map's `done_when` is met as follows:
- `ste_lint.py` reports 0 errors on both rung files: Task 4 Step 7, and the lint cases of `test_rung_drift.py` and `test_render.py`.
- `brainrot.md` points at `video.md` only by section title, and only for the five shared sections: `BrainrotRungCase` (Task 3).
- Each stage line and FAIL line quoted in `video.md` is a line that `render.sh` or its tools print: `StageLineDriftCase` (Task 1), with the two drift mutations of Task 1 Step 8.
- Brainrot renders from its template with ten `ok` lines: Task 4 Step 7.

Inputs for the plans of later waves:

- `film-live-run`: a value folded back into the `film` row of `formats.json` or into `MIN_TEXT` must also change the limits table of section 3 of `video.md`, or `FilmRungCase` goes red. The length guidance of section 3 (2.8 words each second, about 350 words) and the check-frame rule in sections 4 and 6 are text with no pin. The spec still shows a comma list for `--frames` and three guard FAIL lines.
- `explainer-removal`: section 3 of `video.md` names `templates/film-script.json` and `"format": "film"`. The removal renames the template and flips the default, so it changes that section and `test_the_script_section_copies_the_film_template`. The sentence of decision 7 in `brainrot.md` stays true. `test_format_limits.py` no longer reads the explainer row. The README lines of the landscape harness are already gone.
