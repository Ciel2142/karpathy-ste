# Explain lesson — wave `lesson-rung` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/explain <subject> --as lesson` is routed, documented and buildable end to end: three reviewer prompts, the rung file `rungs/lesson.md`, the `SKILL.md` and `README.md` wiring, and a gated E2E that renders a one-clip fixture lesson through `render.sh` and passes `verify.sh` with six `ok` lines.

**Architecture:** No pipeline code changes in this wave: waves 1 to 3 built the clip format, the clip checks, the page template and the `verify.sh` lesson rung. This wave writes the documents an author and a reviewer read at run time, pins each one with static drift tests in the style of `test_rung_drift.py`, and proves the whole path once with a real render of a three-scene clip and a lesson page assembled from `templates/page.html`.

**Tech Stack:** Markdown (rung file, prompts), Python 3 stdlib `unittest`, bash (`render.sh`, `verify.sh`), TypeScript/React (the fixture's `scene/`, against the film kit).

Base: fb25bace9912ed2689a33e5b88647b4dc5c6dc04
Test runs: scoped per task; full suite once, final task.

**Spec:** `docs/superpowers/specs/2026-10-04-explain-lesson-design.md` (amendment A1). This wave implements §3.1, §3.3, §3.4, §3.5, §4.1 to §4.3 (as rung text), §5 (as rung text and prompts), §6.4 (`SKILL.md`, `rungs/lesson.md`, `lesson/*.md`, `README.md`), §7.3 (prompts) and §7.4. Wave map: `docs/superpowers/waves/2026-10-04-explain-lesson.yaml` (wave `lesson-rung`, ralph wave 4, epic kp-qtb). Carried forward from kp-ipy (comment of 2026-10-06 06:46): item (4) "the 22 px dim-caption rule for a clip belongs to lesson.md" is taken in Task 2; items (1) to (3) are not this wave's (no kit or guard code changes here). Item (2) is respected: no new test hard-codes the floors 14 or 19; the E2E reads them from `video/formats.json`.

## Global Constraints

- Work on this worktree's branch `explain-lesson/wave-4`. Never commit to `main`. Never stage or commit `.beads/`.
- `EXPLAIN_VIDEO_WORKSPACE` is preset to the lesson branch's own workspace. Never render into `~/karpathy/video-workspace`.
- Run every test command from `skills/explain`, as `python3 -B -m unittest ...`. Run each command that takes more than 2 minutes (a gated E2E, the full suite) with output to a log file, and poll the log with short `sleep 30` and `tail` calls until `OK` or `FAILED`. Never end a turn to wait for a notification.
- Files this wave may change: `rungs/lesson.md` (new), `lesson/review-page.md`, `lesson/review-script.md`, `lesson/review-render.md` (new), `SKILL.md`, `README.md` (repo root), `tests/test_lesson_prompts.py` (new), `tests/test_lesson_e2e.py` (new), `tests/fixtures/lesson-e2e/` (new), `tests/test_rung_drift.py`, `tests/test_render.py`. No pipeline file, no template, no other rung.
- `rungs/lesson.md` and `SKILL.md` pass `skills/ste/scripts/ste_lint.py` with `0 errors, 0 warnings`. The prompts are subagent instructions, not artifacts, and are not linted (the spec's verbatim hunt sentences fail the lint: a 26-word sentence, a passive).
- `rungs/lesson.md` names sections of `page.md` and `video.md` by their title in double quotes, never by number (as `brainrot.md` does).
- The template file is `templates/video-script.json` (the spec's `templates/film-script.json` was renamed in b368635).
- Code comments and test docstrings follow each file's style: short plain sentences, each test naming the mutation that turns it red. Commits: `<type>: explain: <description>`, ending with the session's Co-Authored-By line.

## Review Focus

1. Round 1 of a gate: the author fills `{previous}` with `none`, and a reviewer reads the round-2 section as an order to rule findings that do not exist. Expected: each prompt says that `none` means round 1 and the section is skipped. Pinned by `test_round_2_rules_before_it_hunts` (Task 1).
2. A later edit renames a section of `page.md` or `video.md`, and `lesson.md` keeps pointing at the old title, so the author reads nothing. Expected: every title that `lesson.md` quotes is one heading of that file. Pinned by `test_lesson_points_at_page_and_video_by_title` (Task 2).
3. The live run's fold-back tunes the `clip` row of `formats.json` (spec §7.5), and the limits that `lesson.md` gives the author stay old. Expected: the clip limits table and the floor sentence are made from the row. Pinned by `test_the_clip_limits_table_matches_formats` and `test_the_clip_floors` (Task 2).
4. A clip is dropped: its `figure.clip` goes, the `Dropped clips` row names it, and `clips/<id>/` stays on disk unlinked. Expected: the page still passes `verify.sh` with six `ok` lines (the additive rule), and the guard hides `Play all` (no `PLAYALL`). Pinned by `test_a_dropped_clip_leaves_a_passing_page` (Task 4).
5. The `--as` list drifts between the argument hint, the syntax line, contract step 3 and `README.md`: a user who mistypes a rung gets a list without `lesson`, or the README advertises a list the router refuses. Expected: one list of six names everywhere. Pinned by `test_skill_md_lists_six_rungs` and `test_readme_names_the_lesson_rung` (Task 3).

## Beyond the letter of the map (decisions made with no user present)

1. **The fixture scene is a trimmed copy of the worked example, not a literal copy** (spec §7.4 says "a copy of the worked example with a 19 px floor"). A literal copy cannot work: `Film.tsx` marks eight scene ids, so `tsc` refuses it against a three-scene script, and it draws 16 px and 18 px text, which `GuardPlantCase.test_a_clip_holds_the_example_to_its_floor` proves fails the clip floor. The fixture keeps three scenes of the template (`subject`, `gates`, `handoff`) with their narration and cites unchanged, and copies only the example files it needs, every text raised to the clip floor and every `C.muted` text to 22 px. Cost if wrong: the fixture scene is about 150 lines that a template change to those three scenes must follow (the non-gated fixture case catches the narration and cites; the gated E2E catches the marks).
2. **The fixture page is assembled at test time from `templates/page.html`**, plus one committed section fragment, so it never drifts from the template and the E2E runs the template's real guard (`PLAYALL`) with a real clip. The clip id is the section id `checks`.
3. **Gate-2 report names use the part form** `review/gate2-<id>-<part>-round-<k>.md` (spec §5.4, A1). Spec §3.3 still shows `review/gate2-<id>-round-<k>.md`; A1 is the later rule.
4. **The quoted-source-line rule at gate 2.** A finding on a still quotes a line of a file under the root or a sentence of the narration in `script.json`; spec §5.4 says "same report shape" and §7.3 requires the rule in every prompt.
5. **The verification read of gate 2 uses `review-render.md`**: `{previous}` is the round-2 report, and the prompt says that a round-2 `{previous}` means rule only, hunt for nothing new. The spec names three prompt files, not four.
6. **Where the tests live.** `LessonRungCase` (the drift tests of `lesson.md`) goes into `test_lesson_prompts.py`, next to the prompt tests: the module is the lesson rung's own documents. It imports helpers from `test_rung_drift.py`, never the other way, so the two modules do not import each other. Outside the map's owns: `test_rung_drift.py` gets `limits_table`, `LESSON_MD` and two `SkillMdCase` tests (it is the home of `SKILL.md` drift); `test_render.py::test_skill_md_lists_five_rungs` becomes `test_skill_md_lists_six_rungs` (it pins five names today and goes red otherwise).
7. **`README.md` beyond the lesson row.** The `--as` list, the layout line and the tests block also name the lesson, so that the README stays true.
8. **`SKILL.md` rule bullets.** The spec gives the row, the conventions and the build step; the plan adds one bullet under "Rung selection" in the shape of the brainrot bullet (forced only, English only, as spec §3.1 states).

---

### Task 1: the three reviewer prompts

**Files:**
- Create: `skills/explain/lesson/review-page.md`, `skills/explain/lesson/review-script.md`, `skills/explain/lesson/review-render.md`
- Create: `skills/explain/tests/test_lesson_prompts.py`

**Interfaces:**
- Consumes: `section(text, title)`, `headings(text)` and `read(path)` of `test_rung_drift.py` (import them; the module puts `tests/` on `sys.path` the same way).
- Produces, in `test_lesson_prompts.py` (Task 2 uses them in the same module):

```python
LESSON_DIR: Path  # EXPLAIN / "lesson"
PLACEHOLDERS: dict[str, frozenset[str]]  # prompt file name -> its placeholder names, braces removed
```

`PLACEHOLDERS`: `review-page.md` → `subject root files report previous`; `review-script.md` → those plus `section`; `review-render.md` → those plus `section changes`.

Each prompt is a template that the author fills by plain text replacement of `{name}`. It has these level-2 sections, in this order: `Your task`, `Inputs`, `Hunt`, `Checks`, `Round 2`, `Report`. Content per section:
- Your task: a cold reviewer of one lesson artifact on `{subject}`; it writes its report to `{report}`.
- Inputs: `{files}` (absolute paths, one per line), the repository root `{root}`; script and render also `{section}` (the section id to read in `index.html`); render also `{changes}` (what changed since gate 1, or `nothing`). The page prompt lists `index.html` and `review/plan.md` as its files; the script prompt adds the clip's `script.json`; the render prompt the two scripts, the stills of its part, the clip transcript, `index.html` and the gate-1 reports of the clip (spec §5.4 step 6).
- Hunt: the gate's framing (spec §5.2 for page and script, §5.4 for render).
- Checks: the gate's numbered list: page 3 checks, script 2, render 6, each the spec's check in the spec's order (§5.2, §5.4). The render prompt's check 5 compares the two scripts.
- Round 2: how to read `{previous}`.
- Report: the finding shape (the file, the location as a line or a scene id, the claim quoted, the source lines quoted verbatim as read from the root, what is wrong, a one-line fix), the rules below, and that the author appends `## Author` (the reviewer does not write it). In the render prompt, the quoted line is a line of a file under the root or a sentence of the narration (decision 4).

Exact sentences, in the section named (whitespace may wrap; the tests compare text with runs of white space collapsed):

```text
Inputs, all three:   Read only these files and the files under the repository root.
Hunt, page + script: Hunt. Assume one claim in this file is not supported by its cited lines, and find it.
                     If, after reading every cite against the source, you find none, `verdict: ok` with zero findings is the right answer and is expected for a correct artifact.
                     Never report a finding you cannot back with a quoted source line.
Hunt, render:        Hunt. Assume one still gives a false picture of what its scene narrates, and find it.
                     `verdict: ok` with zero findings is expected for a correct clip.
Checks, render:      If `{changes}` is `nothing`, the two scripts are the same: skip check 5.
Round 2, all three:  If `{previous}` is `none`, this is round 1: skip this section.
                     Before you hunt, rule each finding of that report `resolved` or `open`, and quote the current source line.
Round 2, render:     If the name of `{previous}` ends in `-round-2.md`, this is a verification read: rule its findings and hunt for nothing new.
Report, all three:   A finding without a quoted source line is not a finding.
                     The last line of your text is `verdict: ok` or `verdict: fix`.
                     Write `verdict: fix` when the report has at least one finding.
```

- [ ] **Step 1: Write the failing tests** (`test_lesson_prompts.py`, class `LessonPromptCase`; the module docstring says what the module pins and that the gates themselves are measured only by the live run, spec §7.5. The module imports from `test_rung_drift.py` only; `test_rung_drift.py` never imports it)

- `test_each_prompt_has_exactly_its_placeholders`: the set of `\{([A-Za-z_]+)\}` matches of each file equals `PLACEHOLDERS[name]`. Red: the render prompt without `{previous}`, or a misspelt `{reports}`.
- `test_each_prompt_has_the_six_sections`: the level-2 titles of each file equal the six above, in order. Red: no `Round 2` section.
- `test_each_prompt_hunts_with_an_exit`: section `Hunt` holds its gate's sentences; the page and script prompts do not hold the gate-2 hunt sentence, and the render prompt does not hold the gate-1 one. Red: the zero-findings sentence dropped from one prompt.
- `test_each_report_needs_a_quoted_source_line`: section `Report` of each holds its three sentences. Red: the verdict rule or the quoted-line rule left out.
- `test_each_prompt_lists_its_checks`: the lines of section `Checks` that match `^\d+\. ` start with `1. ` to `N. ` in order, N = 3, 2, 6. Red: a check dropped or two merged.
- `test_round_2_rules_before_it_hunts`: section `Round 2` of each holds its two sentences; the render prompt also holds the verification-read sentence. Red: Review Focus 1, the `none` sentence left out.
- `test_the_reviewer_reads_only_its_inputs`: section `Inputs` of each holds its sentence. Red: the sentence left out.
- `test_the_render_prompt_skips_check_5_without_changes`: section `Checks` of `review-render.md` holds its sentence. Red: the sentence left out.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_lesson_prompts`
Expected: every case fails or errors (`lesson/` does not exist yet).

- [ ] **Step 3: Write the three prompts** to the contract above.

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command. Expected: `OK`, 8 tests.

- [ ] **Step 5: Check the broken state**

Delete the zero-findings sentence from `review-script.md`: `test_each_prompt_hunts_with_an_exit` FAILs. Revert. Change `{previous}` to `{prev}` in `review-render.md`: `test_each_prompt_has_exactly_its_placeholders` FAILs. Revert.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/lesson/review-page.md skills/explain/lesson/review-script.md skills/explain/lesson/review-render.md skills/explain/tests/test_lesson_prompts.py
git commit -m "feat: explain: the three reviewer prompts of the lesson gates"
```

### Task 2: `rungs/lesson.md`

**Files:**
- Create: `skills/explain/rungs/lesson.md`
- Modify: `skills/explain/tests/test_lesson_prompts.py` (module docstring; `CLIP_MARKUP`; a new class `LessonRungCase`)
- Modify: `skills/explain/tests/test_rung_drift.py` (`film_limits_table` `:419` becomes a call of `limits_table`; the constant `LESSON_MD` beside `VIDEO_MD` `:52`)

**Interfaces:**
- Consumes: `LESSON_DIR`, `PLACEHOLDERS` of `test_lesson_prompts.py` (Task 1); `LESSON_PASS` of `test_verify.py`; `FILM_CELLS`, `FORMATS_JSON`, `fill`, `read`, `section`, `headings`, `blocks`, `lint`, `SECTION_NUMBER` of `test_rung_drift.py`.
- Produces, in `test_rung_drift.py`: `LESSON_MD = EXPLAIN / "rungs" / "lesson.md"` (Task 3 uses it) and `limits_table(path: Path, header: str) -> dict[str, str]`, the body of `film_limits_table()` with the file and the header as arguments; `film_limits_table()` becomes `limits_table(VIDEO_MD, FILM_TABLE_HEADER)`. In `test_lesson_prompts.py`: the constant `CLIP_MARKUP` (Task 4 imports it), verbatim from spec §4.2:

```html
<figure class="clip">
  <video controls preload="none" src="clips/<id>/video.mp4" poster="clips/<id>/poster.png"></video>
  <figcaption><span class="part"></span>One sentence that says what the clip shows.
    <a href="clips/<id>/index.html" data-ste="skip">transcript</a></figcaption>
</figure>
```

`rungs/lesson.md` holds what spec §3.5 lists, under these level-2 titles, numbered from 1 (`LESSON_TITLES`): `When a lesson`, `What to read`, `Plan the lesson`, `Write the page and the clips`, `Check before the review`, `Gate 1: read before the render`, `Render the clips`, `Gate 2: read the stills`, `Drop a clip`, `Finish and handoff`, `Output directory`. Content by section:
- When a lesson: forced only; the clip criterion of spec §4.1, copied in the words of `page.md` section "Plan the sections"; the zero-clip rule (print the rung line, say that no section earns a clip, offer `--as page`, stop before the page is written); English only, as the video rung; the requirements are the page rung's plus the video rung's.
- What to read: the STE profile; `page.md` sections "Plan the sections", "Fill the template", "Diagram patterns", "Provenance", "Write the prose", "Verify and export"; `video.md` sections "The grammar of a film", "Write the script", "Write the scene", "The kit", "Marks", "Text on the stage", "The guard", "Build and check", "The FAIL lines", "Read the stills". The author never reads the spec.
- Plan the lesson: the `review/plan.md` line (spec §5.1 step 2) in a fenced block; the usual range of 2 to 3 clips of 20 to 40 s, no cap on the count; the cost note of spec §4.1 (A1).
- Write the page and the clips: the meta; the markup (`CLIP_MARKUP` as the one fenced `html` block of the file) and its place after the lead paragraph; the poster rule (spec §4.2); `preload="none"`, no `autoplay`; the `Play all` behavior that the template gives (spec §4.3, as the author's facts, not as code to write); the `Dropped clips` row, always present; section ids fixed here and named by the clips; the clip `script.json` keys (spec §5.1 step 3) with `"format": "clip"`, from `templates/video-script.json`; `scene/` from a copy of `<skill-dir>/video/src/film/`; the clip limits table and the floor sentence (below).
- Check before the review: spec §5.1 step 4, the five commands as written there.
- Gate 1: spec §5.2 and §5.3: fresh general-purpose subagents, never forks; the prompt files `<skill-dir>/lesson/review-page.md` and `review-script.md`; how to fill each placeholder (every name of `PLACEHOLDERS` appears in this file), the inputs as absolute paths, "an instruction, not a sandbox"; the copy `review/gate1-<id>.script.json` at dispatch; the report names; the `## Author` block; the round rule (at most two rounds, round 2 for `fix` and for changed items); removal, drop, disputed and propagation rules.
- Render the clips: spec §5.4 step 5 (the first render alone until its `narration (<engine>): ok` line, the others at the same time; eleven `ok` lines; author faults and the two re-renders; `render: FAIL <cause>` as a drop reason; environment faults stop the lesson).
- Gate 2: spec §5.4 steps 6 and 7: the author reads every still first; the split by whole scenes with the `-end` still before, at most five stills, a scene of more than four sentences alone; `review-render.md`; `{changes}`; rounds, the verification read; the drop rule.
- Drop a clip: spec §5.4 "Dropping a clip", the plan change that is not a drop.
- Finish and handoff: spec §5.5 steps 8 and 9: the poster copy; `verify.sh index.html` with the six lines as one fenced block; steps 2 to 4 of `page.md` section "Verify and export" with the two extra tile faults; the handoff and `disputed findings: none`.
- Output directory: the table of spec §3.3, with the part form of decision 3.

Exact texts (`LESSON_TEXTS`, each must occur in the file, white space collapsed): `<meta name="explain-rung" content="lesson">`, `Rung: lesson (forced) — <reason> — subject: <subject> (<kind>)`, `<id> | <h2 question> | clip: yes|no | <reason, when yes>`, `--as page`, `"format": "clip"`, `templates/video-script.json`, `<skill-dir>/video/src/film/`, `review/plan.md`, `review/plants.md`, `review/gate1-page-round-<k>.md`, `review/gate1-<id>-round-<k>.md`, `review/gate1-<id>.script.json`, `review/gate2-<id>-<part>-round-<k>.md`, `## Author`, `narration (<engine>): ok`, `render: FAIL <cause>`, `clips/<id>/poster.png`, `still-NN-<scene>-end.png`, `<div class="wide"><dt>Dropped clips</dt><dd>none</dd></div>`, `<id> — <reason>`, `disputed findings: none`.

The floor sentence, in section "Write the page and the clips", made from the clip row (`{clip}` is its `minText`; 22 is the film's 16 px dim-caption rule at 75 %, spec §5.1 step 3):

```text
Draw each text at {clip} px or more on the canvas, and each text in `C.muted` at 22 px or more.
```

- [ ] **Step 1: Write the failing tests** (`LessonRungCase` in `test_lesson_prompts.py`; the module docstring adds it)

- `test_lesson_md_lints_clean`: `lint(LESSON_MD)` gives `(0, "0 errors, 0 warnings\n")`. Red: a contraction or a 26-word sentence.
- `test_the_headings_of_lesson_md`: the level-2 heading lines are `"## %d. %s"` of `LESSON_TITLES`, numbered from 1. Red: a section missing or out of turn.
- `test_lesson_points_at_page_and_video_by_title`: for each of `page.md` and `video.md`, the pointer blocks are the non-heading `blocks()` of `lesson.md` that hold its file name. Each pointer block holds at least one title of that file in double quotes, and no `SECTION_NUMBER` match. The titles that the pointer blocks of `page.md` quote include each of the six above, and each is exactly one heading of `page.md`; the same for the ten titles of `video.md`. Red: Review Focus 2, a renamed title, or "section 7 of `page.md`".
- `test_the_clip_limits_table_matches_formats`: `limits_table(LESSON_MD, "| Limit | clip |")` items equal `FILM_CELLS` filled from the `clip` row of `formats.json`. Red: Review Focus 3, `maxTotalSeconds` of the clip row set to 50.
- `test_the_clip_floors`: section `Write the page and the clips`, white space collapsed, holds the floor sentence once, with `{clip}` from the clip row. Red: the 22 px rule left out, or the clip `minText` changed to 20.
- `test_the_clip_markup_is_the_spec_markup`: `lesson.md` has exactly one fenced block opened by ```` ```html ````, and its body equals `CLIP_MARKUP`. Red: `preload="none"` or `data-ste="skip"` dropped.
- `test_lesson_quotes_the_six_verify_lines`: section `Finish and handoff` has a fenced block whose lines equal `LESSON_PASS.splitlines() + ["media: ok"]`. Red: the media line left out.
- `test_lesson_holds_its_rules`: each of `LESSON_TEXTS` occurs in the file. Red: a report name in the old form (`review/gate2-<id>-round-<k>.md`).
- `test_lesson_names_every_placeholder_and_prompt`: the `{name}` set of `lesson.md` equals the union of `PLACEHOLDERS` values; the `<skill-dir>/lesson/<file>` names in it are exactly the three keys of `PLACEHOLDERS`, and each file exists under `LESSON_DIR`. Red: `{changes}` never explained to the author, or a prompt file renamed.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_lesson_prompts tests.test_rung_drift`
Expected: every `LessonRungCase` case fails or errors (no `lesson.md`); every other case passes (`limits_table` keeps `test_film_limits_table_matches_formats` green).

- [ ] **Step 3: Write `rungs/lesson.md`** to the contract above. Every sentence in STE. Keep the spec's numbers: 60 s, 20 to 40 s usual, two rounds, two re-renders, five stills, four sentences.

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command. Expected: `OK`.

- [ ] **Step 5: Check the broken state**

Set `maxTotalSeconds` of the `clip` row in `video/formats.json` to 50: `test_the_clip_limits_table_matches_formats` FAILs. Revert. Change one quoted title of `video.md` in `lesson.md` to `"The Guard"`: `test_lesson_points_at_page_and_video_by_title` FAILs. Revert.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/rungs/lesson.md skills/explain/tests/test_lesson_prompts.py skills/explain/tests/test_rung_drift.py
git commit -m "docs: explain: the lesson rung file, with both gates and its drift tests"
```

### Task 3: route `--as lesson` in `SKILL.md`; the README row

**Files:**
- Modify: `skills/explain/SKILL.md` (frontmatter `argument-hint` `:5`; Contract `:16-22`; the rung table `:50-56` and the bullets `:66-78`; Conventions `:82`, convention 3 `:110-111`, convention 5 `:118`, convention 6 `:120-121`; Build procedure step 2 `:127-130`; Rung files `:139-148`)
- Modify: `README.md` (the skill line `:9`, Requirements `:35-42`, Layout `:62-65`, Tests `:69-77`)
- Modify: `skills/explain/tests/test_render.py` (`test_skill_md_lists_five_rungs` `:813-824`)
- Modify: `skills/explain/tests/test_rung_drift.py` (`SkillMdCase`; module docstring)

**Interfaces:**
- Consumes: `LESSON_MD` of `test_rung_drift.py` (Task 2).
- Produces: `SKILL.md` texts, each pinned by a test:

```text
argument-hint:   <subject> [--as ste|sheet|page|video|brainrot|lesson]
syntax line:     Syntax: `/explain <subject> [--as ste|sheet|page|video|brainrot|lesson]`.
contract step 3: the six names in backticks, and "List these six names in the error."
rung table row:  | `lesson` (page with clips, directory output) | Forced only (`--as lesson`). A page whose sections carry short narrated clips where motion explains better than a still | A subsystem with two to four moving parts |
bullet:          The `lesson` rung builds a page with narrated clips. Only `--as lesson` selects it. The lesson rung is English only, like the video rung.
conventions:     These seven rules apply to every artifact rung (`sheet`, `page`, `video`, `brainrot`, `lesson`).
convention 3:    For the `lesson` rung, the artifact is the output directory.
convention 6:    `open index.html` (sheet, page or lesson)
build step 2:    For a lesson, the rung file replaces steps 3 to 6.
rung files:      a bullet `<skill-dir>/rungs/lesson.md` that names the clips and the two review gates
```

Convention 3 also says that `index.html` keeps the rule and links to other files only through `clips/<id>/video.mp4`, `clips/<id>/poster.png` and `clips/<id>/index.html` (spec §3.4). Convention 5 says that for a lesson `rungs/lesson.md` lists the contents. `README.md`: the skill line lists the six names and one clause on the lesson (a page whose sections carry short narrated clips, with two review gates); a Requirements row `` | `lesson` | the needs of `page` and of `video` together | ``; the Layout line lists `rungs/{sheet,page,video,brainrot,lesson}.md` and `lesson/` (the reviewer prompts); the Tests block adds `EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_lesson_e2e  # renders a one-clip fixture lesson, needs the workspace`.

- [ ] **Step 1: Write the failing tests**

- `test_render.py`: `test_skill_md_lists_five_rungs` becomes `test_skill_md_lists_six_rungs`: the hint and the syntax line are the texts above; contract step 3 holds the six names in backticks and `six names`. Red: `lesson` missing from one of the three places.
- `SkillMdCase.test_skill_md_routes_the_lesson_rung`: `SKILL.md` has exactly one line starting ``| `lesson` ``, equal to the row above; its flattened text holds the bullet, the conventions sentence, the convention-3 sentence and `(sheet, page or lesson)`; step 2 of "Build procedure" holds the build-step sentence; the "Rung files" bullet `<skill-dir>/rungs/lesson.md` exists, holds `clips` and `gates`, and `LESSON_MD` exists. Red: the lesson row marked as chosen from content, or the conventions list without `lesson`.
- `SkillMdCase.test_readme_names_the_lesson_rung`: the `--as` list of the README's `/explain <subject> [--as ...]` equals the list of the `SKILL.md` hint; the README has one line starting ``| `lesson` |``; it holds `tests.test_lesson_e2e`. Red: Review Focus 5, the README list left at five names.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_render.BrainrotRouteCase tests.test_rung_drift.SkillMdCase`
Expected: FAIL for the three new or changed cases; `test_skill_md_lints_clean` and the brainrot cases pass.

- [ ] **Step 3: Edit `SKILL.md` and `README.md`** to the texts above. Keep every `SKILL.md` sentence in STE.

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command. Expected: `OK`, `test_skill_md_lints_clean` included.

- [ ] **Step 5: Check the broken state**

Remove `|lesson` from the README skill line: `test_readme_names_the_lesson_rung` FAILs. Revert.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/SKILL.md README.md skills/explain/tests/test_render.py skills/explain/tests/test_rung_drift.py
git commit -m "feat: explain: --as lesson is routed in SKILL.md and listed in the README"
```

### Task 4: the fixture lesson and its gated E2E; wave acceptance

**Files:**
- Create: `skills/explain/tests/fixtures/lesson-e2e/script.json`, `skills/explain/tests/fixtures/lesson-e2e/section.html`, `skills/explain/tests/fixtures/lesson-e2e/scene/` (`Film.tsx` and the example files it uses)
- Create: `skills/explain/tests/test_lesson_e2e.py`

**Interfaces:**
- Consumes: `CLIP_MARKUP` of `test_lesson_prompts.py` (Task 2); `FORMATS_JSON` of `test_rung_drift.py`; `LESSON_PASS` of `test_verify.py`; `template_script`, `REPO`, `TRANSCRIPT_PY`, `VERIFY_SH` of `test_film_example.py`; `ORDER` and `split_sentences` of `test_render_film.py`; `stage_lines` of `test_render.py`; `video_size` of `test_render_brainrot.py`; `differing_pixels` of `png_diff.py`; `E2E`, `E2E_REASON`, `RENDER_SH`, `RENDER_TIMEOUT`, `render_env` of `video_e2e.py`; `check_scene` of `test_check_scene.py`. The render is a `subprocess.run` of `render.sh <out>/clips/checks --engine say`, as `render_output` of `test_render_film.py` runs it.
- Produces, in `test_lesson_e2e.py`:

```python
FIXTURE: Path  # EXPLAIN / "tests" / "fixtures" / "lesson-e2e"
CLIP_ID = "checks"
def lesson_output() -> Path: ...  # a temporary lesson directory (removed at exit) holding clips/checks/ (script.json rooted at REPO, scene/ copied); no page yet
def lesson_page(out: Path, clip: bool = True) -> Path: ...  # writes out/index.html from templates/page.html; returns its path
```

The fixture:
- `script.json`: `"format": "clip"`; `title` `How does explain check an artifact?`; `subject` and `provenance` as in `templates/video-script.json` (root `.`), with `provenance.source` `skills/explain/scripts/verify.sh` and `not_covered` `none`; no `sources`; three scenes, the template's `subject`, `gates` and `handoff`, with the template's narration and cites unchanged.
- `scene/`: a trimmed copy of `video/src/film/` (decision 1): `Film.tsx` draws the three scenes from the example's files; every text 19 px or more on the canvas and every `C.muted` text 22 px or more; every scene changes the picture; marks only on words that the narration says.
- `section.html`: `<section id="checks">` with the `<h2>` of the title above, a lead paragraph with a cite of `skills/explain/scripts/verify.sh` line 2 (the template's snippet), the lines of `CLIP_MARKUP` unindented with `<id>` = `checks` and a fixture sentence in place of `One sentence that says what the clip shows.`, and a second paragraph with a cite of line 11; STE prose.

`lesson_page(out, clip)`: writes `out/index.html` (each test writes the page that it verifies), a copy of `templates/page.html` with five edits, each on an anchor that occurs exactly once: the meta line that starts its line (`content="page"` → `content="lesson"`; the template holds the meta a second time in a comment); `section.html` before `<section id="provenance-facet">` (with `clip=False`, its `figure.clip` removed first); `<a href="#checks">Checks</a>` before `<a href="#provenance-facet">Provenance</a>`; `data-root="."` → `data-root="<REPO>"`; the `Dropped clips` row after `<div><dt>Dirty</dt><dd>no</dd></div>`, with `<dd>none</dd>`, or with `clip=False` `<dd>checks — <reason></dd>` (a fixture reason).

- [ ] **Step 1: Write the failing tests**

Class `LessonFixtureCase` (always runs; no render, no Chrome):
- `test_the_fixture_is_three_scenes_of_the_template`: the fixture script is `"format": "clip"` with scene ids `["subject", "gates", "handoff"]`, and each scene equals the template scene of that id. Red: the fixture narration drifts from the template.
- `test_the_fixture_clip_passes_the_checks_before_review` (spec §5.1 step 4): on a copy rooted at `REPO`, `node video/build-timeline.mjs --check <script> --root <REPO>` exits 0 with no output; `check_scene` of the fixture `scene/` exits 0; `transcript.py <script> <dir>` then `verify.sh <dir>/index.html` print `self-contained: ok`, `citations: ok`, `prose: ok`. Red: a cite snippet off by one word.
- `test_the_section_names_the_clip`: `section.html` has one `<section id="checks">`, its `<h2>` equals the script's `title`, and it holds `CLIP_MARKUP` with `<id>` replaced by `checks` and the placeholder sentence replaced by the fixture's sentence (the text between `</span>` and the end of that line). Red: a clip id that is not the section id.

Class `LessonRenderCase` (`@unittest.skipUnless(E2E, E2E_REASON)`): one render per process, cached like `render_film()`: `lesson_output()`, then `render.sh <out>/clips/checks --engine say` in `render_env()`; then the scripted step 8: copy `clips/checks/review/still-03-handoff-end.png` to `clips/checks/poster.png`.
- `test_the_clip_prints_eleven_ok_lines`: exit 0, no `FAIL`; eleven stage lines matching, in order: `script: ok \(3 scenes\)`, `workspace: ok /.+`, `scene: ok \(<n> files\)` (`<n>` the `.ts`/`.tsx` files of the fixture `scene/`), `narration \(say\): ok`, `timeline \(3 scenes, (\d+\.\d) s\): ok` with the seconds at most the clip `maxTotalSeconds`, `guard \(<f> frames\): ok` (`<f>` = sum over the fixture scenes of `len(split_sentences(narration)) + 1`), then the five patterns of `test_render_film.ORDER[6:]`. Red: the fixture scene draws an 18 px label (guard FAIL).
- `test_the_clip_is_held_to_the_clip_row`: `build/timeline.json` has `minText` and `maxTotalSeconds` equal to the clip row of `formats.json`; `video_size(video.mp4)` is `1280x720`. Red: the fixture script says `"format": "film"`.
- `test_each_scene_changes_the_picture`: each `-end` still differs from the one before it in more than 500 pixels (`differing_pixels`, as `FilmRenderCase`). Red: a scene of `Film.tsx` that draws nothing new.
- `test_the_poster_is_the_last_end_still`: the bytes of `poster.png` equal those of `still-03-handoff-end.png`. Red: the poster copied from the first scene.
- `test_the_page_prints_six_ok_lines`: `verify.sh <lesson_page(out)>` exits 0 with stdout `LESSON_PASS + "media: ok\n"`. Red: the transcript link names `clips/check/` (media FAIL).
- `test_a_dropped_clip_leaves_a_passing_page`: `verify.sh <lesson_page(out, clip=False)>` exits 0 with the same six lines, and the page has no `figure.clip` while `clips/checks/` stays on disk. Red: Review Focus 4, the template's rule `body:not(:has(figure.clip)) #play-all` deleted (the button shows, the guard reports `PLAYALL`, the render lines FAIL).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_lesson_e2e`
Expected: the `LessonFixtureCase` cases error (no fixture); `LessonRenderCase` is skipped.

- [ ] **Step 3: Write the fixture and the helpers** to the contract above. Start `scene/` from a copy of `video/src/film/`; delete what the three scenes do not draw.

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command, then `EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_lesson_e2e` (logged and polled).
Expected: `OK` for both; the second run has no skips.

- [ ] **Step 5: Check the broken state**

Set the size of one label of the fixture scene to 18: the gated `test_the_clip_prints_eleven_ok_lines` FAILs with `guard: FAIL ... SMALLTEXT 18.0 px`. Revert. Delete `poster.png` after the render and run `verify.sh` on the page by hand: `media: FAIL 1 missing`, exit 1.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/tests/test_lesson_e2e.py skills/explain/tests/fixtures/lesson-e2e
git commit -m "test: explain: a gated E2E renders a one-clip fixture lesson and verifies its page"
```

- [ ] **Step 7: Run the full unit suite**

Run: `cd skills/explain && python3 -B -m unittest discover -s tests` (logged and polled).
Expected: `OK`. Baseline at the base (kp-ipy acceptance at fb25bac): `Ran 776 tests`, `OK (skipped=44)`. This wave adds about 30 cases, 6 of them gated (`LessonRenderCase`), so expect `skipped=50`. If the suite stalls, run it once more with `-v` before you diagnose anything.

- [ ] **Step 8: Run the lesson E2E once more as the acceptance run**

Run: `cd skills/explain && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_lesson_e2e` (logged and polled).
Expected: `OK` with no skip. Record the `Ran` lines of Steps 7 and 8 in the close reason.
