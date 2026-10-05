# Explain film — wave `film-scene-stage` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A film renders from the author's `<output-dir>/scene/`: the `scene` stage checks the directory, copies it over `src/film/` of the run directory, writes `script.gen.ts` and runs `tsc`, and a film run prints ten `ok` lines.

**Architecture:** A new tool, `video/check_scene.py`, checks a scene directory by its text alone (the directory rules, the import rule and the refused tokens). A new function of `render.sh`, `stage_scene`, runs for a film between the `workspace` and `narration` stages: the check, then the copy into the run directory, then `build-timeline.mjs --types`, then `tsc` with the run directory as its project. Nothing is written under `<ws>/app`, and a fault costs no synthesis.

**Tech Stack:** bash 3.2 (`/bin/bash` of macOS), Python 3 `unittest`, Node (v25.9.0 on this machine), TypeScript 5.9.3, Remotion 4.0.532, as pinned in `video/`.

**Spec:** `docs/superpowers/specs/2026-10-05-explain-film-design.md` — this wave implements §4.3, §7.2, the `scene` line of §7, the `test_check_scene.py` bullet of §9.1 and the stage plants of §9.2 (ten lines, not eleven: the `guard` stage is the next wave). Wave map: `docs/superpowers/waves/2026-10-05-explain-film.yaml`, wave `film-scene-stage` (ralph wave 5, epic `kp-uu1`). Coverage: waived by the map.

Base: 075f5d975aacfe041aafca68b0bef910bb76013c

Test runs: scoped per task; full suite once, final task.

## Global Constraints

- Work on this wave's own branch and worktree. Never commit to `main`, to `feat/explain-brainrot`, or directly to `feat/explain-film`. Never stage `.beads/`.
- A gated run (`EXPLAIN_VIDEO_E2E=1`) and every `render.sh` run are allowed only with `EXPLAIN_VIDEO_WORKSPACE` set to the film branch's own workspace. Never render into `~/karpathy/video-workspace`: other sessions use it. Each such command below starts with `test -n "$EXPLAIN_VIDEO_WORKSPACE"` and prints the path; a command that ends there with no output means the variable is not set: do not render, and report it.
- No install from a test run. If a class is skipped for missing packages, run `scripts/video-workspace.sh --engine say` once, alone, in that workspace.
- No edit, not even one that is reverted, may make a real render write under `<ws>/app`: that workspace is shared by the sessions of this feature.
- Files this wave may change, under `skills/explain/`: new `video/check_scene.py`, `scripts/render.sh`, new `tests/test_check_scene.py`, new `tests/fixtures/scene-clean/` (`Film.tsx`, `Part.tsx`), `tests/test_render_film.py`, and, handed over by the closed waves (decision 10): `tests/test_film_example.py`, `tests/test_render.py`, `tests/test_render_parallel.py`. Nothing else: no file of `video/src`, no `build-timeline.mjs`, no rung file, no new dependency.
- Stage lines: a film run prints ten, brainrot ten, the explainer nine. The names `STAGES`, `stage_lines`, `render_functions`, `RUN_FAKES`, `RunDirectoryCase`, `E2E`, `E2E_REASON`, `EXPLAIN`, `RENDER_SH`, `RENDER_TIMEOUT`, `render_env`, `workspace`, `tree_digest`, `render_film`, `run_functions`, `template_script`, `FILM_DIR` stay importable from where they are.
- Every pre-existing test case passes unchanged, except the three that this plan names: `test_the_example_follows_the_scene_rules` (Task 1), `test_film_prints_nine_ok_lines` and the pair of `ParallelRenderCase` (Task 4). An explainer or brainrot run prints the same lines as at the base.
- In the run directory: once its `node_modules` link exists, the only recursive commands on a path of `$run` are the trap's `rm -rf "$run"` and this wave's `rm -rf "$run/src/film"` (no trailing slash, no glob after the name). A tool that runs with cwd `$run` is run as `(cd "$run" && exec <tool>)`, so that `render.sh` waits for it.
- Tests: `unittest`, run from `skills/explain`. Each test names the mutation that turns it red, as the files do today. Each new assertion is seen to fail before the code exists; one that passes at once is checked by applying its named mutation, seeing the failure, and reverting.
- Baseline at the base (run at planning): `python3 -B -m unittest discover -s tests` gives `Ran 654 tests`, `OK (skipped=41)`.
- Commits: `<type>: explain: <description>`, ending with the attribution line of the session.

## What the closed waves left for this one

Read from the close notes of `kp-xdd` and `kp-osb` and from the close section of the wave 4 plan. Each is placed in a task.

- The rule lists of `test_the_example_follows_the_scene_rules` are the rules of `check_scene.py`, but its regex is not to be copied: a comment that holds the word `export` or `import` right above a remotion import, with no `;` between, gives a false fault there. That comment and both re-export forms are fixtures of `test_check_scene.py` (Task 1). The test itself becomes a run of the tool (Task 1).
- The Remotion project of a run is `$run`. Each step that runs a node tool with cwd `$run` is `exec`ed in a subshell and has its own always-run test with a tool that outlives the signal (Task 3).
- `stage_render` already renders `Film` from `$run/src/film`; the stage only has to replace that directory before the render (Task 2). `STAGES` of `test_render.py` gets `scene`, and the nine-line test of the film its tenth line (Tasks 3 and 4).
- `ParallelRenderCase` swaps its explainer for a film: spec §9.2 asks for one brainrot and one film (Task 4).
- Decision 1 of the wave 4 plan ends here: a film script with its own scene ids renders, because the picture is the author's.

## Beyond the letter of the spec

Decisions that the spec and the map leave open, made here so that every task builds the same thing.

1. `check_scene.py` prints nothing and exits 0 for a scene; it prints one `FAIL <cause>` line for each cause and exits 1. `render.sh` runs it through `run_tool`, as it runs every tool: the stage line is the first cause, and all lines of the tool follow, indented, the first among them. Spec §7.2 says that "the other causes follow"; the repeat of the first is how each stage of `render.sh` prints.
2. The causes come in a fixed order: `no Film.tsx`; then, for each entry by name, `<name> is a directory` or `<name> is not a .ts or .tsx file`; then `Film.tsx has no "export function Film("`; then the causes of the files by file name, then by line, and on one line the import causes before the token causes, tokens in the order of the spec's list. Every cause is printed, not only the first.
3. The line of an import cause is the line that holds the quoted source. A token gives one cause for each line that holds it.
4. There is no comment parser, for imports as for tokens: each `from "<source>"` and each `import "<source>"` counts, with either quote, also in a comment.
5. An entry whose name starts with `.` is ignored, a directory too: it is never copied. `script.gen.ts` of the scene is not read, not copied and not counted.
6. A scene file is read as UTF-8 with each undecodable byte replaced: such a byte never stops the check.
7. The stage copies with a glob of its own (`*.ts`, `*.tsx`, regular files, without `script.gen.ts`); `check_scene.py` has refused every other visible entry before. The count of the `ok` line is the number of files copied.
8. `tsc` runs with no argument, cwd `$run`, its output in `$run/tsc.log` (the file goes with the run directory; the output directory gets no new file). The first error line is the first line that holds `error TS`, else the first line that is not empty, else `exit <n>`. `src/film/` is written as `scene/` in the stage line as well as in the 20 lines below it.
9. The cause of `scene: FAIL types:` is the first cause of the tool's output, as `first_cause` reads it; the tool's lines follow, indented.
10. Three test files outside the map's `owns` list change: `tests/test_film_example.py` (its scene-rule test runs the tool; the wave 4 plan, decision 9), `tests/test_render.py` (`STAGES`, and the helpers of `RunDirectoryCase` become a mixin that the film case reuses) and `tests/test_render_parallel.py` (the film takes the explainer's place in the pair; close note of `kp-xdd`).
11. All four stage plants are gated, the cite plant too: spec §9.2 lists them with the end-to-end cases, and three of them need the workspace.
12. `ParallelRenderCase` with a film is the gated proof that a film run leaves `<ws>/app` unchanged. It is not run red (Global Constraints); `SceneRunCase` of Task 3 is its red-first proof, in a temporary workspace.

## Review Focus

Failure modes that the spec implies and that are most likely to cost a person something. Each has its test in the task named.

1. A file of the example, or of an earlier scene, stays in `src/film/` of the run directory: the author gets `tsc` errors in a file they did not write, or the film draws a picture that is not theirs. Task 2: `test_a_clean_scene_is_copied_and_typed`; Task 3: `test_the_render_draws_the_copied_scene`.
2. The fix of the comment false alarm lets a refused name through: a comment inside the import clause that holds `export {`. Task 1: `test_a_comment_inside_the_clause_never_hides_a_name`.
3. The author's copy of the example's `script.gen.ts` wins over the generated file: a mark on a scene that the script does not have passes `tsc` and fails in the render, after the synthesis. Task 2: `test_a_clean_scene_is_copied_and_typed`.
4. A `tsc` failure that the author cannot act on: a path of the run directory, a first line that is not an error, two hundred lines. Task 2: `test_tsc_errors_are_cut_and_renamed`.
5. A FAIL or a signal in the scene stage leaves the run directory, or a `tsc` that still runs in it. Task 3: `test_a_scene_fail_stops_before_any_synthesis`, `test_render_sh_waits_for_a_tsc_that_outlives_the_signal`.

Accepted, not tested. The token list is the spec's and is matched as text, so these pass the check: `xlinkHref` (not `href`), `<feImage`, `:any` without the space, `Record<string, any>`, and an import with a comment between `from` and its quoted source. A scene file that cannot be read ends `check_scene.py` with a traceback, which the stage prints as its FAIL line. They are recorded on `kp-uu1` for the spec's owner.

---

### Task 1: `check_scene.py` checks a scene directory

**Files:**
- Create: `skills/explain/video/check_scene.py`
- Create: `skills/explain/tests/fixtures/scene-clean/Film.tsx`, `skills/explain/tests/fixtures/scene-clean/Part.tsx`
- Create: `skills/explain/tests/test_check_scene.py`
- Modify: `skills/explain/tests/test_film_example.py` (docstring lines 9-12; the rule lists and `scene_faults` at 248-303, removed; `test_the_example_follows_the_scene_rules` at 324-333)

**Interfaces:**
- Consumes: nothing.
- Produces, for Tasks 2, 3 and 4:

  ```
  python3 video/check_scene.py <scene-dir>
    exit 0   no output: the directory is a scene
    exit 1   stdout: one line "FAIL <cause>" for each cause, in the order of decision 2
    exit 2   stderr: "usage: check_scene.py <scene-dir>"
  ```

  ```python
  # tests/test_check_scene.py
  CHECK_SCENE: Path     # video/check_scene.py
  SCENE_CLEAN: Path     # tests/fixtures/scene-clean
  def check_scene(directory: Path) -> subprocess.CompletedProcess
  def scene_copy(test: unittest.TestCase, edit=None) -> Path   # a temp copy of SCENE_CLEAN, removed at cleanup; edit(copy) runs on it
  ```

- [ ] **Step 1: Write the clean fixture.** `tests/fixtures/scene-clean/` is a scene that an author could write. It is never compiled. It holds two files and nothing else:
  - `Film.tsx`: two `//` comment lines, one that holds the word `export` and one that holds the word `import`, with no `;` in them, right above `import { useCurrentFrame as now, interpolate } from "remotion";`; then `import type { ReactElement } from "react";`, an import from `"../kit"` that runs over three lines, `import type { Props } from "./script.gen";`, `import { Part } from "./Part";`; one comment line with the five near misses `<masks <useful <images as anyone : anything`; and `export function Film(props: Props): ReactElement {` with a body that draws `<Part />` in a `<g>`.
  - `Part.tsx`: `export { interpolate } from "remotion";` and `export function Part(`.
  - No `script.gen.ts`: the import of `./script.gen` is allowed without the file.

- [ ] **Step 2: Write the failing tests.** The module docstring says that the file holds one failing scene for each rule and each token of spec §7.2, each built as the clean fixture with one edit and asserted by its line, and the clean scene. A failing case asserts the exit code 1, an empty stderr and the exact list of stdout lines unless it says otherwise. `<n>` is the line number of the planted line, computed by the test.

  `CleanSceneCase`:
  - `test_the_clean_fixture_passes` — `(0, "", "")`. Red: the clause of a remotion import starts at the first `import` or `export` word before it (the comment gives a fault), `./script.gen` is refused without its file, a near miss is matched, or the re-export of an allowed name is refused.
  - `test_hidden_entries_and_script_gen_are_ignored` — the copy plus `.DS_Store`, a directory `.cache/` with `x.tsx` in it, and a `script.gen.ts` that holds `// @ts-nocheck` and `import fs from "fs";`: `(0, "", "")`. Red: a hidden entry is a fault, or `script.gen.ts` is read.

  `DirectoryRuleCase`:
  - `test_no_scene_directory` — a path that does not exist, and a path of a file: `FAIL no scene directory: <path>`, the path as given.
  - `test_no_film_tsx` — `Film.tsx` removed: `FAIL no Film.tsx`.
  - `test_a_directory_fails` — a directory `parts/` with `Deep.tsx` in it: `FAIL parts is a directory`, and nothing about `Deep.tsx`.
  - `test_another_file_fails` — `notes.md`, and `data.json`: `FAIL <name> is not a .ts or .tsx file`.
  - `test_film_without_the_exported_function` — `export function Film(` written as `export const Film = (`: `FAIL Film.tsx has no "export function Film("`.

  `ImportRuleCase`:
  - `test_each_import_fault_fails_by_its_line` — one sub-test for each row; the text is appended to `Film.tsx`, and the one line is `FAIL Film.tsx:<n>: <cause>`:

    | Appended | Cause |
    |---|---|
    | `import { getLength } from "@remotion/paths";` | `import from "@remotion/paths"` |
    | `import { makeAt } from "../kit/marks";` | `import from "../kit/marks"` |
    | `import "./side";` | `import from "./side"` |
    | `export { p } from "../other/motion";` | `import from "../other/motion"` |
    | `import { Part } from './Part.tsx';` | `import from "./Part.tsx"` |
    | `import { Sequence } from "remotion";` | `"Sequence" from remotion` |
    | `import { useCurrentFrame, AbsoluteFill as Fill } from "remotion";` | `"AbsoluteFill" from remotion` |
    | `import type { SpringConfig } from "remotion";` | `"SpringConfig" from remotion` |
    | `import * as R from "remotion";` | `"* as R" from remotion` |
    | `import Remotion from "remotion";` | `"Remotion" from remotion` |
    | `export { Sequence } from "remotion";` | `"Sequence" from remotion` |
    | `export * from "remotion";` | `"*" from remotion` |
    | three lines: `import {`, `  spring, Img,`, `} from "remotion";` | `"Img" from remotion`, at the third line |

    Red: a source list that allows any `../kit/...` or any `./...`, a re-export that is not read, `type` taken as the name.
  - `test_a_fault_in_another_file_names_that_file` — `import { Sequence } from "remotion";` appended to `Part.tsx`: `FAIL Part.tsx:<n>: "Sequence" from remotion`. Red: only `Film.tsx` is read.
  - `test_a_comment_inside_the_clause_never_hides_a_name` — two sub-tests, each two appended lines: `import { Sequence, // export {` then `  useCurrentFrame } from "remotion";`, and `import { Sequence, /*` then `export { */ useCurrentFrame } from "remotion";`. Each gives exit 1 and at least one line that matches `^FAIL Film\.tsx:\d+: ".*" from remotion$`. Red: the clause is the text after the nearest `import` or `export` word (exit 0 for the first sub-test: the word in the comment hides `Sequence`).

  `TokenRuleCase`, with the two token lists of spec §7.2 written out in the test, not imported from the tool:
  - `test_each_token_fails_by_its_line` — for each of the 19 tokens, the appended line `// <token>` gives the one line `FAIL Film.tsx:<n>: token "<token>"`. Red: a token missing from the tool's list, or a comment that is skipped.
  - `test_word_tokens_need_a_boundary` — for each of `<mask`, `<use`, `<image`, `as any`, `: any`: the appended line `// <token>x`, and `// <token>9`, give exit 0; `// <token>_`, `// <token>>` and `// <token> ` give the token's line. Red: a plain substring match, or a boundary that takes `_` as a letter.
  - `test_a_token_counts_once_for_each_line` — one line that holds `href` twice and a later line that holds it once: two causes, with the two line numbers.
  - `test_bytes_that_are_not_utf8_do_not_stop_the_check` — the bytes `// \xff @ts-nocheck` appended: the line of the token, and an empty stderr. Red: a strict decode (a traceback and no FAIL line).

  `OutputCase`:
  - `test_causes_come_in_a_fixed_order` — a copy with a directory `zz/`, a file `notes.md`, `// @ts-ignore` as the new line 1 of `Part.tsx`, and in `Film.tsx` the exported function written as a constant and the appended line `import { Sequence } from "remotion"; // fetch( href`. The lines are exactly:

    ```
    FAIL notes.md is not a .ts or .tsx file
    FAIL zz is a directory
    FAIL Film.tsx has no "export function Film("
    FAIL Film.tsx:<n>: "Sequence" from remotion
    FAIL Film.tsx:<n>: token "fetch("
    FAIL Film.tsx:<n>: token "href"
    FAIL Part.tsx:1: token "@ts-ignore"
    ```

    Red: the check stops at the first cause, or the order follows the file system.
  - `test_usage` — no argument, and two arguments: exit 2, empty stdout, stderr `usage: check_scene.py <scene-dir>`.

  In `test_film_example.py`, `test_the_example_follows_the_scene_rules` becomes: `check_scene.py` on `FILM_DIR` gives `(0, "")`. Its docstring keeps the red cases it names. The lists, the two regexes, `remotion_names` and `scene_faults` go, and the module docstring names the tool.

- [ ] **Step 3: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_check_scene tests.test_film_example.ExampleSceneCase`
  Expected: `FAILED`; every case of `test_check_scene` and `test_the_example_follows_the_scene_rules` fail on exit code 2 (`can't open file`).

- [ ] **Step 4: Write `video/check_scene.py`.** Contract:
  - One argument, the scene directory. A path that is not a directory gives only `no scene directory: <path>`.
  - Directory rules (spec §4.3), with decision 5: each visible entry is a regular file named `*.ts` or `*.tsx` (links followed), else `<name> is a directory` for a directory and `<name> is not a .ts or .tsx file` for anything else; a regular file `Film.tsx` exists and its text holds `export function Film(`.
  - Import rule, in each scene file: each source (decision 4) is `react`, `remotion`, `../kit`, `./script.gen`, or `./<Name>` for a scene file `<Name>.ts` or `<Name>.tsx`; another source is `<file>:<line>: import from "<source>"`.
  - Remotion names: the clause of a `from "remotion"` is the text between the `from` and the nearest `import` or `export` word before it that is the first word of its line; with no such word, it is the text of the source's own line before the `from`. A clause that is one braced list gives its names: each item's own name, before an `as`, without a leading `type`, also after `import type` or `export type`. Each name outside `useCurrentFrame`, `interpolate`, `Easing`, `spring`, `interpolateColors` is `<file>:<line>: "<name>" from remotion`. A clause of any other shape is one cause that quotes the clause with its white space collapsed and cut to 40 characters.
  - Tokens: the 14 plain tokens and the 5 tokens that need a next character that is not an ASCII letter or digit (the end of the text counts), as spec §7.2 lists them, matched with their case, in comments too: `<file>:<line>: token "<token>"`.
  - The order of decision 2, the lines of decision 3, the decoding of decision 6. The module docstring gives the command, the exit codes, the cause lines and the two token lists, and says that there is no comment parser.

- [ ] **Step 5: Run the tests and see them pass; check one mutation.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_check_scene tests.test_film_example`
  Expected: `OK`. Then append `import { Sequence } from "remotion";` to `video/src/film/Film.tsx`, see `test_the_example_follows_the_scene_rules` fail, and revert with `git checkout -- video/src/film/Film.tsx`.

- [ ] **Step 6: Commit.**

  ```bash
  git add skills/explain/video/check_scene.py skills/explain/tests/test_check_scene.py skills/explain/tests/fixtures/scene-clean/Film.tsx skills/explain/tests/fixtures/scene-clean/Part.tsx skills/explain/tests/test_film_example.py
  git commit -m "feat: explain: check_scene.py checks the directory, imports and tokens of a scene"
  ```

---

### Task 2: `stage_scene` checks, copies, names and compiles the scene

**Files:**
- Modify: `skills/explain/scripts/render.sh` (a global after `remotion=` at line 134; a new function after `stage_workspace` at 282-292)
- Test: `skills/explain/tests/test_render_film.py` (new `FAKE_TSC`; new class `SceneStageCase` after `FilmFunctionCase`)

**Interfaces:**
- Consumes: the command of Task 1; `SCENE_CLEAN` of `tests/test_check_scene.py`; `run_functions`, `template_script` (already in the module); `build-timeline.mjs --types <script.json> <out.ts>`, whose FAIL lines its header lists.
- Produces, for Tasks 3 and 4:

  ```bash
  tsc="$app/node_modules/.bin/tsc"   # a global of render.sh, beside remotion=
  stage_scene()                      # reads fmt, out, run, script, video, tsc; calls fail, first_cause, run_tool
  ```

  ```
  scene: ok (<n> files)
  scene: FAIL <first cause of check_scene.py>        the tool's lines follow, indented
  scene: FAIL cannot copy the scene to <run>/src/film
  scene: FAIL types: <cause>                          the tool's lines follow, indented
  scene: FAIL tsc: <first error line>                 the first 20 lines of tsc follow, indented
  ```

  ```python
  # tests/test_render_film.py
  FAKE_TSC: str   # the text of a fake tsc (Python). It appends one JSON line to $FAKE_DIR/tsc.jsonl:
                  # {"argv", "cwd" (real path), "film": {name: text} of src/film under its cwd}. It prints
                  # the file $FAKE_TSC_OUTPUT when set, sleeps $FAKE_TSC_SLEEP s, and exits $FAKE_TSC_EXIT
                  # (default 0). With $FAKE_TSC_OUTLIVE it outlives TERM and HUP as FAKE_CLI of
                  # test_render.py does: the signal ends the sleep, 1 s later it makes .tsc-late/ in its
                  # cwd (made again if it is gone) and writes $FAKE_DIR/tsc.end.
  ```

  The function is not yet called by the script: Task 3 calls it.

- [ ] **Step 1: Write the failing tests.** `SceneStageCase` runs `stage_scene` alone, through `run_functions(tmp, ["fail", "first_cause", "run_tool", "stage_scene"], setup)`, with the real `video/` of the skill (the real `check_scene.py` and `build-timeline.mjs`) and `FAKE_TSC`. `setUp` makes, in a temporary directory: `out/script.json` (`template_script()`); `out/scene`, a copy of `SCENE_CLEAN` plus `.DS_Store` and a `script.gen.ts` with the text `// the author's copy`; `run/src/film` with `Example.tsx` and a `script.gen.ts` (what the run directory holds from the skill); `ws/app/node_modules/.bin/tsc` (`FAKE_TSC`, executable) and `run/node_modules` as a link to `ws/app/node_modules`. A helper `stage(self, fmt="film", before="")` sets `fmt`, `out`, `run`, `script`, `video`, `tsc`, exports `FAKE_DIR`, adds the shell text `before`, and calls `stage_scene`.

  - `test_a_clean_scene_is_copied_and_typed` — exit 0 and stdout `scene: ok (2 files)`. `run/src/film` holds exactly `Film.tsx`, `Part.tsx` and `script.gen.ts`; the first two are the bytes of the scene's files; the third line of `script.gen.ts` is `export type SceneId = ` with the scene ids of the template, each in double quotes, joined by ` | `, and `;` (built by the test from `template_script()`). `tsc.jsonl` has one call: no argument, cwd the real path of `run`, and `film` with those three names and that generated text. Red: no removal of `src/film` before the copy (`Example.tsx` stays: Review Focus 1); a hidden file copied; the author's `script.gen.ts` copied or counted (Review Focus 3); `tsc` before the names are written; `tsc` with another cwd.
  - `test_another_format_has_no_scene_stage` — `fmt=explainer` and `fmt=brainrot`, with `out/scene` removed: exit 0, no output, `run/src/film/Example.tsx` is still there, no `tsc` call. Red: the stage runs for every format, and a brainrot run stops with `no scene directory`.
  - `test_no_scene_directory` — `out/scene` removed: exit 1 and the lines `scene: FAIL no scene directory: <out>/scene` and `  FAIL no scene directory: <out>/scene`; `Example.tsx` is still there; no `tsc` call. Red: `src/film` is emptied before the check has passed.
  - `test_the_first_cause_is_the_stage_line` — `// @ts-nocheck` as the new line 1 of `scene/Film.tsx` and `// href` appended: exit 1 and exactly `scene: FAIL Film.tsx:1: token "@ts-nocheck"`, `  FAIL Film.tsx:1: token "@ts-nocheck"`, `  FAIL Film.tsx:<n>: token "href"`; no `tsc` call. Red: the stage goes on after a failed check.
  - `test_a_copy_that_fails` — `before` defines `cp() { return 1; }`: exit 1 and the one line `scene: FAIL cannot copy the scene to <run>/src/film`; no `tsc` call. Red: the status of `cp` is not read.
  - `test_types_that_fail` — `out/script.json` written again with `"format": "brainrot"`, `fmt` still `film`: exit 1 and the lines `scene: FAIL types: script: --types needs a film script` and `  FAIL script: --types needs a film script`; no `tsc` call. Red: the status of the tool is not read, or the line has no `types:`.
  - `test_tsc_errors_are_cut_and_renamed` — `FAKE_TSC_EXIT=2` and an output of 25 lines: `Version 5.9.3`, then `src/film/Film.tsx(60,39): error TS2345: Argument of type '"no-such-scene"' is not assignable to parameter of type 'SceneId'.`, then 23 lines `src/film/Part.tsx(<k>,1): error TS6133: 'x<k>' is declared but its value is never read.`. Exit 1; the first line is `scene: FAIL tsc: scene/Film.tsx(60,39): error TS2345: Argument of type '"no-such-scene"' is not assignable to parameter of type 'SceneId'.`; then exactly the first 20 lines of the output, each after two spaces and with `src/film/` written as `scene/`. Red: Review Focus 4.
  - `test_tsc_without_an_error_line` — the output `tsc: boom` with exit 1 gives `scene: FAIL tsc: tsc: boom`; no output with exit 3 gives the one line `scene: FAIL tsc: exit 3`. Red: a stage line with no cause.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render_film`
  Expected: `FAILED`; the eight `SceneStageCase` cases end in `AssertionError: no stage_scene() in render.sh`; `FilmFunctionCase` passes; `FilmRenderCase` is skipped.

- [ ] **Step 3: Write `stage_scene` and the `tsc` global.** Contract, in this order:
  - For a format that is not `film` the function returns at once and changes nothing.
  - The check: `run_tool scene python3 "$video/check_scene.py" "$out/scene"`.
  - The copy: `$run/src/film` is removed and made again (`rm -rf "$run/src/film"`, the one recursive command of this wave below `$run`: the `node_modules` link lies outside it), then each regular file `$out/scene/*.ts` and `$out/scene/*.tsx` except `script.gen.ts` is copied into it. A removal, a `mkdir` or a `cp` that fails is `scene: FAIL cannot copy the scene to $run/src/film`.
  - The names: `node "$video/build-timeline.mjs" --types "$script" "$run/src/film/script.gen.ts"`; a failure is the `types` line of decision 9.
  - The type check: `(cd "$run" && exec "$tsc") > "$run/tsc.log" 2>&1 < /dev/null`, the shape of the CLI call in `stage_render`, for the reason its comment gives. A non-zero exit is the `tsc` line of decision 8, then the first 20 lines of the log, indented.
  - Then `scene: ok (<n> files)`, `<n>` the number of files copied.
  - A comment above the function names the four steps and why the stage comes before the narration.

- [ ] **Step 4: Run the tests and see them pass.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render_film tests.test_render`
  Expected: `OK`; the gated cases are skipped.

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/scripts/render.sh skills/explain/tests/test_render_film.py
  git commit -m "feat: explain: stage_scene checks, copies, names and compiles the scene of a film"
  ```

---

### Task 3: a film run has the `scene` stage

**Files:**
- Modify: `skills/explain/scripts/render.sh` (header comment lines 12-77; the stage sequence at the end of the file)
- Modify: `skills/explain/tests/test_render.py` (docstring line 1; `STAGES` at 42-43; `RunDirectoryCase` at 507-587)
- Test: `skills/explain/tests/test_render_film.py` (new class `SceneRunCase`)

**Interfaces:**
- Consumes: `stage_scene`, `FAKE_TSC` (Task 2); `CHECK_SCENE`, `SCENE_CLEAN` (Task 1); `RUN_FAKES`, `names`, `default_signals`, `kill_group` of `tests/test_render.py`.
- Produces, for Task 4 and the next wave:

  ```python
  # tests/test_render.py
  STAGES = ("script", "workspace", "scene", "narration", "timeline", "background", "render",
            "container", "sync", "stills", "transcript")
  class RunHarness:                     # not a TestCase: the temp skill tree and the helpers
      fakes: dict                       # path under the temp dir -> file text; RUN_FAKES
      def setUp(self) -> None
      def start(self, fmt="explainer", **env) -> subprocess.Popen
      def output(self) -> tuple
      def finish(self, proc, timeout=60) -> subprocess.CompletedProcess
      def wait_for_cli(self, proc) -> None
      def cli_calls(self) -> list
      def tool_calls(self, tool) -> list
      def run_pattern(self, runs, pid) -> str
      def render_or_fail_lines(self, stdout) -> list
  class RunDirectoryCase(RunHarness, unittest.TestCase)   # its tests do not change
  ```

  A film run prints ten stage lines; the third is `scene: ok (<n> files)`.

- [ ] **Step 1: Split the harness, with no change of behaviour.** In `test_render.py` the `setUp` and the eight helpers of `RunDirectoryCase` move, as they are, to `RunHarness`; `setUp` writes `self.fakes` in place of `RUN_FAKES`. `STAGES` gets `scene`, and the first docstring line names the ten stages of a film.

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render`
  Expected: `OK`, with the number of tests it had before the edit.

- [ ] **Step 2: Write the failing tests.** `SceneRunCase(RunHarness, unittest.TestCase)` in `test_render_film.py` runs the copy of `render.sh` against the fakes, as `RunDirectoryCase` does. Its `fakes` are `RUN_FAKES` with these on top: `tsc` (`FAKE_TSC`); `skill/scripts/video-workspace.sh`, the fake of `RUN_FAKES` that also copies `$FAKE_DIR/tsc` to `.bin/tsc`; `skill/video/check_scene.py`, the text of the real tool; `skill/video/build-timeline.mjs`, the fake of `RUN_FAKES` that also takes `--types <script> <out.ts>` and writes `// generated` to `<out.ts>`; and `skill/video/src/film/Example.tsx`. `setUp` copies `SCENE_CLEAN` to `out/scene`.

  - `test_a_film_run_prints_ten_stage_lines` — `start("film")`: exit 0, the first words of the stage lines are `script`, `workspace`, `scene`, `narration`, `timeline`, `render`, `container`, `sync`, `stills`, `transcript`, and the third line is `scene: ok (2 files)`. For `explainer` and `brainrot`: exit 0, no stage line starts with `scene`, and `tsc.jsonl` does not exist. Red: the stage is not called (nine lines), or it is called after `narration`, or for every format.
  - `test_the_render_draws_the_copied_scene` — after a film run: the paths under `src/film/` that the fake CLI saw are exactly `src/film/Film.tsx`, `src/film/Part.tsx` and `src/film/script.gen.ts`; the cwd of the CLI and the cwd of `tsc` are the same path, which matches `run_pattern`; `names(self.ws / "app")` is `["node_modules"]` and `names(self.shared)` is `[".bin", "sentinel.txt"]`; `names(self.runs)` is `[]`. Red: the scene is copied under `<ws>/app` (decision 12), `tsc` runs in the app, or the removal of `src/film` reaches the shared packages.
  - `test_a_scene_fail_stops_before_any_synthesis` — three sub-tests: `// @ts-nocheck` as line 1 of `scene/Film.tsx` (last stage line `scene: FAIL Film.tsx:1: token "@ts-nocheck"`); `out/scene` removed (`scene: FAIL no scene directory: <out>/scene`, `<out>` by real path); `FAKE_TSC_EXIT=2` with the output `src/film/Film.tsx(1,1): error TS1005: x` (`scene: FAIL tsc: scene/Film.tsx(1,1): error TS1005: x`). Each: exit 1; the stage lines are `script: ok (1 scenes)`, `workspace: ok <ws>` and that line; `tool_calls("narrate")` is `[]`; `out/audio` does not exist; `cli_calls()` is `[]`; `names(self.runs)` is `[]`. Red: the stage comes after the narration, or the run directory stays after a FAIL.
  - `test_render_sh_waits_for_a_tsc_that_outlives_the_signal` — for TERM and for HUP: `start("film", FAKE_TSC_SLEEP="30", FAKE_TSC_OUTLIVE="1")`; once `tsc.jsonl` has its line (a helper of the case polls for it, as `wait_for_cli` does for the CLI), the signal goes to the process group; `finish(proc, timeout=10)` gives exit 1 and no line with `FAIL`; `tsc.end` exists within 10 s; `names(self.runs)` is `[]`; `sentinel.txt` is there. Red: `tsc` in a subshell without `exec` (render.sh exits first, and the late write of `tsc` makes the run directory again).

- [ ] **Step 3: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render_film.SceneRunCase`
  Expected: `FAILED`; all four fail: a film run prints nine stage lines and no `scene` line.

- [ ] **Step 4: Call the stage and describe it.** Contract:
  - `stage_scene` is called after `stage_workspace` and before `stage_narration`.
  - The header comment says: an explainer run has nine stages, a film run and a brainrot run ten (the film has `scene`, brainrot has `background`), and the `guard` stage of a film does not exist yet; the stage list gets the line `scene: ok (<n> files)` with what the stage does (the check of `<output-dir>/scene`, the copy over `src/film` of the run directory, `script.gen.ts`, `tsc`); the five FAIL lines of the stage and what follows each; in the paragraph on the run directory, that `tsc` runs there as the Remotion CLI does and that `render.sh` waits for it, and that a film puts its scene only there.

- [ ] **Step 5: Run the tests and see them pass.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render_film tests.test_render tests.test_check_scene`
  Expected: `OK`; the gated cases are skipped. From this commit to Task 4 the gated `FilmRenderCase` is red: it renders without a `scene/`.

- [ ] **Step 6: Commit.**

  ```bash
  git add skills/explain/scripts/render.sh skills/explain/tests/test_render.py skills/explain/tests/test_render_film.py
  git commit -m "feat: explain: a film run has the scene stage, between workspace and narration"
  ```

---

### Task 4: the example renders from a scene copy; the stage plants

**Files:**
- Modify: `skills/explain/tests/test_render_film.py` (docstring; `ORDER` at 56-67; `render_film` at 73-84; `test_film_prints_nine_ok_lines` at 178-186; new gated class `ScenePlantCase`)
- Modify: `skills/explain/tests/test_render_parallel.py` (docstring; `Render.__init__` at 138-153; `ParallelRenderCase` at 197-254)

**Interfaces:**
- Consumes: Tasks 1 to 3; `FILM_DIR`, `template_script` of `tests/test_film_example.py`.
- Produces:

  ```python
  # tests/test_render_film.py
  SCENE_FILES: int                     # the *.ts and *.tsx files of FILM_DIR, without script.gen.ts
  def film_output(edit=None) -> Path   # a temp output dir, removed at exit: script.json is
                                       # template_script(), scene/ a copy of FILM_DIR; then edit(out)
  def render_film() -> tuple           # as before; it renders film_output()
  # tests/test_render_parallel.py
  class Render:
      def __init__(self, add_cleanup, script, scene=None, **env)   # scene: a directory copied to out/scene
  ```

- [ ] **Step 1: See the film render fail without a scene.**

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film.FilmRenderCase.test_film_prints_nine_ok_lines`
  Expected: the workspace path, then `FAILED`: the run stops at `scene: FAIL no scene directory: <out>/scene`.

- [ ] **Step 2: Write the tests.**

  `FilmRenderCase`: `render_film()` renders `film_output()`. `ORDER` gets `scene: ok \(%d files\)` with `SCENE_FILES` as its third pattern, and the test is named `test_film_prints_ten_ok_lines`. Red: the stage counts `script.gen.ts`, or does not run. The other seven cases do not change.

  `ScenePlantCase`, gated by `E2E`: each case renders `film_output(edit)` with `render.sh <out> --engine say`, `env=render_env()` and `RENDER_TIMEOUT`. Each asserts: exit 1; the last stage line; no stage line starts with `narration`; `out/audio` and `out/video.mp4` do not exist. `FilmRenderCase` is their control: the same output directory without the edit prints ten `ok` lines.

  - `test_a_changed_cite_stops_at_the_script_stage` — the edit writes the second word of the snippet of the first cite of the first scene in `script.json` as `zebra`. The stage lines are the one line `script: FAIL citations: FAIL 1 failure(s)`, and stdout holds the line `    cite 1 (<path>:<line>): snippet not found on that line`, path and line read from the template. Red: the script stage does not run the cite check before the workspace.
  - `test_a_mark_on_an_unknown_scene_stops_at_tsc` — the edit writes the first `at("subject")` of `scene/Film.tsx` as `at("no-such-scene")` and fails if the text is not there. The stage lines are `script: ok`, `workspace: ok` and a line that matches `^scene: FAIL tsc: scene/Film\.tsx\(<l>,\d+\): error TS2345: .*"no-such-scene".*'SceneId'\.$`, `<l>` the line of the planted call. Red: the scene is checked and not copied (`tsc` reads the example and passes), or the line keeps `src/film/`.
  - `test_a_used_import_of_another_package_stops_at_the_check` — the edit puts `import { getLength } from "@remotion/paths";` after the line `import { useCurrentFrame } from "remotion";` and writes the first `useCurrentFrame()` as `useCurrentFrame() + getLength("M 0 0 L 1 1") * 0`. The last stage line is `scene: FAIL Film.tsx:<line>: import from "@remotion/paths"`. The package is installed and `tsc` passes this scene (probed at planning), so only the check stops it. Red: the check is skipped.
  - `test_ts_nocheck_stops_at_the_check` — the edit of the mark case, plus `// @ts-nocheck` as the new line 1. The last stage line is `scene: FAIL Film.tsx:1: token "@ts-nocheck"`. `tsc` passes this scene (probed at planning). Red: the token list has no `@ts-nocheck`, and the unknown mark reaches the render.

  `test_render_parallel.py`: `Render` copies `scene` to `out/scene` when it is given. In `ParallelRenderCase` the first render of the pair is the film (`template_script()`, `scene=FILM_DIR`), held as `cls.film`, with the film's `ORDER` of `test_render_film.py` as its patterns; the four tests on the pair name it `film`. The FAIL case and the SIGTERM case keep their scripts. The docstring names the film.

- [ ] **Step 3: Run the gated film tests; prove the plants in the broken state.**

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film`
  Expected: the workspace path, then `OK` with no skip.

  Then two edits of `stage_scene`, each not committed and reverted, each with a gated run of `tests.test_render_film.ScenePlantCase`: without the removal and the copy (the example stays in `src/film`), `test_a_mark_on_an_unknown_scene_stops_at_tsc` fails; without the call of `check_scene.py`, the import case and the `@ts-nocheck` case fail. Neither edit writes outside the run directory.

- [ ] **Step 4: Run the two renders at the same time.**

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_parallel`
  Expected: the workspace path, then `OK` with no skip: the film ten lines, brainrot ten, `<ws>/app` the same before and after. `test_the_app_is_unchanged` is not run red (decision 12).

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/tests/test_render_film.py skills/explain/tests/test_render_parallel.py
  git commit -m "test: explain: the film renders from a scene copy with ten ok lines; the four stage plants"
  ```

- [ ] **Step 6: Run the full unit suite, once.**

  Run: `cd skills/explain && python3 -B -m unittest discover -s tests`
  Expected: `OK (skipped=45)`: the 41 of the base and the four of `ScenePlantCase`. No failure and no error.

- [ ] **Step 7: Run the map's acceptance.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_check_scene`
  Expected: `OK`, no skip.

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film tests.test_render tests.test_render_brainrot tests.test_check_render`
  Expected: the workspace path, then `OK` with no skip: the film ten lines, the explainer nine (`SayFixtureCase`), brainrot ten (`BrainrotRenderCase`). About 15 minutes.

  Then check the tree: `git status --short` prints nothing, and `git diff --stat 075f5d975aacfe041aafca68b0bef910bb76013c -- . ':!docs'` lists only files that Global Constraints allows.

## Wave close

The map's `done_when` is met by: Task 1 (`test_check_scene.py`: one failing scene for each rule and each token, by its line, and the clean fixture), Task 4 Step 3 (the example renders from a `scene/` copy with ten `ok` lines; the four plants stop with their line before any synthesis), and Task 3 with Task 4 Step 4 (a film run leaves `<ws>/app` unchanged).

Inputs for the plans of later waves:

- `film-guard`: the guard pass is one more tool with cwd `$run`, after the timeline: `exec` in a subshell, and a test of its own on `RunHarness` (the fake CLI of `RUN_FAKES` serves both passes). `STAGES` gets `guard`, the film's `ORDER` an eleventh pattern, and the header of `render.sh` loses "does not exist yet".
- `film-docs`: the lines to quote are those of Task 2's Produces block. The stage prints the first cause twice (decision 1). A `from "<x>"` in a comment counts (decision 4); a hidden directory is ignored (decision 5). Only `src/film/` is renamed: a `Film` with other props fails in `src/FilmStage.tsx`. The rung file lists what the check does not see (Review Focus, last paragraph).
- `explainer-removal`: the FAIL case and the SIGTERM case of `ParallelRenderCase` still render the explainer fixture and brainrot. `RunHarness` and `FAKE_TSC` can move to `tests/video_e2e.py` with the other helpers.
