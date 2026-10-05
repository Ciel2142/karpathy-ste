# Explain film — wave `run-directory` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each render compiles in its own `<ws>/runs/<unique>/`: two renders at the same time both pass, and a render writes nothing under `<ws>/app` except the two package files.

**Architecture:** `video-workspace.sh` stops syncing sources; it keeps `<ws>/app/package.json`, `package-lock.json` and the installed `node_modules` current and touches nothing else there. `render.sh` makes a run directory inside its workspace stage (a copy of the skill's `video/`, `node_modules` as a link to the shared one, an empty `public/`), points the audio copy, the background picker and `remotion render` at it, and removes it from an EXIT trap. `pick_background.py` stages its clip inside the run directory it is given and refuses a clip folder anywhere in `<ws>/runs`.

**Tech Stack:** bash 3.2 (`/bin/bash` of macOS), Python 3 `unittest`, Node 22, Remotion 4.0.532 with Rspack as pinned in `video/`.

**Spec:** `docs/superpowers/specs/2026-10-05-explain-film-design.md` — this wave implements §7.6, the `test_video_workspace.py` case of §9.1, the run-directory case of §9.2 and the last two risk rows of §13. Wave map: `docs/superpowers/waves/2026-10-05-explain-film.yaml`, wave `run-directory` (ralph wave 3, epic `kp-xdd`). Coverage: waived by the map.

Base: c24a149bce8b9b49b1ff7857ae16dcae8164cafe

Test runs: scoped per task; full suite once, final task.

## Global Constraints

- Work on this wave's own branch and worktree. Never commit to `main`, to `feat/explain-brainrot`, or directly to `feat/explain-film`. Never stage `.beads/`.
- A gated run (`EXPLAIN_VIDEO_E2E=1`) is allowed only with `EXPLAIN_VIDEO_WORKSPACE` set to the film branch's own workspace. Never render into `~/karpathy/video-workspace`: other sessions use it. Each gated command below starts with `test -n "$EXPLAIN_VIDEO_WORKSPACE"` and prints the path; a command that ends there with no output means the variable is not set: do not render, and report it.
- At the base, `tests/video_e2e.py` and `tests/test_render_brainrot.py` drop that variable and render in the default workspace. So no gated run of `tests.test_render`, `tests.test_render_brainrot` or `tests.test_check_render` happens before Task 4 Step 4 has passed.
- No install from a test run. If a gated class is skipped for missing packages, run `scripts/video-workspace.sh --engine say` once, alone, in that workspace (two first installs at the same time are not handled, spec §7.6).
- Files this wave may change: `skills/explain/scripts/render.sh`, `skills/explain/scripts/video-workspace.sh`, `skills/explain/video/pick_background.py`, `skills/explain/video/remotion.config.ts` (its comment only), `skills/explain/rungs/brainrot.md` (one bullet of section 4), and under `skills/explain/tests/`: `test_video_workspace.py`, `test_pick_background.py`, `test_render.py`, `test_render_brainrot.py`, `test_short_still.py`, `video_e2e.py`, new `test_render_parallel.py`. Nothing else. No new dependency.
- The stage lines of `render.sh` do not change: nine for the explainer, ten for brainrot, `workspace: ok <ws>` as today. The names `STAGES`, `stage_lines`, `E2E`, `E2E_REASON`, `EXPLAIN`, `RENDER_SH`, `TEMPLATE`, `RENDER_TIMEOUT`, `render_fixture` and `fixture_script` stay importable from where they are.
- Tests: `unittest`, run from `skills/explain`. Each test names the mutation that turns it red, as the files do today. Each new assertion is seen to fail before the code exists; one that passes at once is checked by applying its named mutation, seeing the failure, and reverting.
- Baseline at the base: `python3 -B -m unittest discover -s tests` gives `Ran 601 tests`, `OK (skipped=24)`, in about 200 s.
- Commits: `<type>: explain: <description>`, ending with the attribution line of the session.

## The workspace after this wave

`<ws>` is `$EXPLAIN_VIDEO_WORKSPACE`, else `~/karpathy/video-workspace`.

| Path | Who writes it | What it holds |
|---|---|---|
| `<ws>/app/package.json`, `package-lock.json` | `video-workspace.sh` | The skill's two package files |
| `<ws>/app/node_modules` (with `.explain-lock-sha`) | `video-workspace.sh`, on an install only | The shared packages. No render writes here |
| `<ws>/app/npm-ci.log`, `browser-ensure.log` | `video-workspace.sh`, on an install only | The install logs, as today |
| anything else in `<ws>/app`, `<ws>/bg-stage` | nobody on this code | Left as found, for a session on older code |
| `<ws>/models`, `<ws>/backgrounds` | `video-workspace.sh` | As today |
| `<ws>/runs/run.<pid>.<6 chars>/` | `render.sh` | One running render: the copy of `video/`, the `node_modules` link, `public/audio`, and for brainrot `bg-stage/` behind `public/bg` |

## Beyond the letter of the spec

Decisions that spec §7.6 leaves open, made here so that every task builds the same thing.

1. The run directory is named `run.<pid>.<6 chars>` (`mktemp -d "$ws/runs/run.$$.XXXXXX"`). A test in a workspace that other sessions share can then check its own render and nothing else.
2. The run directory is made at the end of the workspace stage, before its `ok` line, so a failure has a stage: `workspace: FAIL cannot make a run directory in <ws>/runs`.
3. The background stage is `<run>/bg-stage`, and `<run>/public/bg` is the relative link `../bg-stage`. The picker refuses a `--dir` that is, or lies under, the parent directory of the run directory it is given (`<ws>/runs`), with `background: FAIL --dir <dir> is inside the workspace's runs folder`.
4. HUP, INT and TERM end `render.sh` with exit 1 and no FAIL line, as `tests/capture_landscape_baseline.sh` does. `render.sh` does not signal its children: a signal that reaches only `render.sh` takes effect when the running tool returns; a signal to the process group (Ctrl-C, `timeout`) stops the tool as well.
5. "More than a day old" is a modification time more than 1440 minutes back (`find -mmin +1440`), read on the run directory itself.
6. `video-workspace.sh` no longer makes `<ws>/bg-stage` and no longer removes a dangling `<ws>/app/public/bg`: both belong to the old layout, and older code looks after them itself.
7. The gated helpers keep the caller's `EXPLAIN_VIDEO_WORKSPACE`. `tests/video_e2e.py` is not in the map's `owns` list of this wave; its change is the "workspace paths only" change that the map gives to `test_render.py`, which renders through it. Without it the map's own acceptance command renders in the workspace that this branch must not use.
8. The comment of `video/remotion.config.ts` names the cwd of the CLI; the wave makes it false, so it is corrected. Comment only.

Left alone, for the wave that owns the file: the sentence in `rungs/video.md` that `app/` holds the sources (wave `film-docs`), and the header comment of `tests/capture_landscape_baseline.sh` about the sync (wave `explainer-removal`). That script still works: it runs the `render.sh` of the ref it renders.

A fact read at planning, not yet shown by a run: with `Config.setRspack(true)` the pinned Remotion wrote no `node_modules/.cache` in a workspace that has rendered many times, so two renders are not expected to meet in a bundler cache. The cache name is an md5 of the bundler config, which holds the project path, and the CLI clears every other cache it finds; if a cache does appear, Task 5 names the remedy.

## Review Focus

Failure modes that §7.6 implies and that are most likely to cost a person something. Each has its test in the task named.

1. Removing a run directory through its `node_modules` link deletes the shared packages of every render. Task 3: a sentinel file in the shared `node_modules` survives a pass, a fail, a signal and the sweep.
2. The sweep removes the directory of a render that is still running. Task 3: a directory 23 hours old stays, one 25 hours old goes.
3. A second render reads `package-lock.json` for its checksum while the first rewrites it, sees a half file, and runs `npm ci` under a running render. Task 1: an unchanged file is not touched, a changed one arrives by a rename.
4. A checkout has its own `video/node_modules` or `video/public` (both are gitignored). Task 3: neither is copied into the run directory.
5. The workspace path has a space, or is reached through a symlink (`/tmp`, `/var` on macOS). Task 3: the harness workspace is `<tmp>/w s`, and paths are compared by real path.

Accepted, not tested: a signal between `mktemp` and the assignment of `run` leaves one directory, which the sweep of a later run removes after a day.

---

### Task 1: `video-workspace.sh` keeps only the package files

**Files:**
- Modify: `skills/explain/scripts/video-workspace.sh` (header comment lines 2-27, step 1 at lines 70-84)
- Test: `skills/explain/tests/test_video_workspace.py` (class `Sync`, lines 106-199)

**Interfaces:**
- Consumes: nothing.
- Produces: the `<ws>/app`, `<ws>/models` and `<ws>/backgrounds` rows of the layout table; the line `workspace: FAIL copy package files to <ws>/app`.

- [ ] **Step 1: Write the failing tests.** Rename class `Sync` to `PackageFiles`. Remove `test_sync_excludes_node_modules_and_public_and_deletes_stale`, `test_backgrounds_and_stage_made_beside_the_app_and_stage_survives_sync`, `test_old_stage_in_the_app_is_removed_by_the_sync` and `test_dangling_bg_link_removed_after_the_sync`. Keep `test_resolving_bg_link_and_real_dir_kept` as it is. Add:

  - `test_app_gets_the_two_package_files_and_nothing_else` — after one run in a fresh workspace the names in `<ws>/app` are exactly `browser-ensure.log`, `node_modules`, `npm-ci.log`, `package-lock.json`, `package.json`, and each package file has the bytes of the skill's. Red: the source sync is back (`src` is listed).
  - `test_what_is_already_in_the_app_stays` — after a first run, plant `stale.txt`, `src/Old.tsx`, `public/audio/keep.wav`, `bg-stage/clip.mp4` and a dangling link `public/bg`; after a second run each file has its bytes and the link has its target and still dangles. Red: `--delete` is back, or the dangling link is still removed.
  - `test_unchanged_package_files_are_not_touched` — a second run with an unchanged skill leaves `st_ino`, `st_mtime_ns` and `st_ctime_ns` of both files as they were. Red: a copy on every run (`cp`, `cp -p`, or `rsync`, which sets the times again).
  - `test_changed_package_file_arrives_by_a_rename` — with `copy_skill()`, run, append a newline to the skill's `package.json`, run: the workspace file has the new bytes and a new `st_ino`, and no other name appeared in `<ws>/app`. Red: the file is overwritten in place, or the temporary file is left behind.
  - `test_backgrounds_made_and_the_old_stage_left_alone` — a run in a fresh workspace makes `<ws>/backgrounds` and makes no `<ws>/bg-stage`; with `<ws>/bg-stage/clip.mp4` planted, a run leaves its bytes. Red: `backgrounds` is not made, or the stage is made or emptied.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_video_workspace`
  Expected: `FAILED`; the five new cases fail (the first lists `src` and the tools of `video/`), the classes `NpmCi` and `Models` pass.

- [ ] **Step 3: Rewrite step 1 of `video-workspace.sh`.** Contract:
  - It makes `<ws>/app`, `<ws>/models` and `<ws>/backgrounds`; a failure is `workspace: FAIL mkdir <path>` as today.
  - For `package.json` and `package-lock.json` of `$skill/video/`: when `<ws>/app/<name>` has the same bytes (`cmp -s`), nothing is done; else the file is copied to a temporary name in `<ws>/app` and renamed over `<name>`. A failure removes the temporary file and prints `workspace: FAIL copy package files to <ws>/app`.
  - It creates, changes or removes nothing else in `<ws>/app` and nothing in `<ws>/bg-stage`: no `rsync --delete`, no `mkdir` of the stage, no removal of `public/bg`.
  - Steps 2 to 4 (lock stamp, `npm ci`, browser, models) and every other output line stay as they are.
  - The header comment describes the layout table above in place of the `<ws>/app` and `<ws>/bg-stage` paragraphs, and names `<ws>/runs` as the place where `render.sh` keeps one directory for each running render.

- [ ] **Step 4: Run the tests and see them pass.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_video_workspace`
  Expected: `OK`

- [ ] **Step 5: Commit.**

  ```bash
  git add skills/explain/scripts/video-workspace.sh skills/explain/tests/test_video_workspace.py
  git commit -m "feat: explain: video-workspace.sh keeps only the package files in the shared app"
  ```

---

### Task 2: the picker stages inside the run directory

**Files:**
- Modify: `skills/explain/video/pick_background.py` (module docstring; `USAGE`, `STAGE`, `LINK_TARGET` at lines 60-66; `stage_dir`, `inside_app`, `prepare_stage` at lines 120-163; the refusal in `main` at lines 308-310)
- Modify: `skills/explain/rungs/brainrot.md` (the bullet at lines 108-110)
- Test: `skills/explain/tests/test_pick_background.py`

**Interfaces:**
- Consumes: nothing.
- Produces, for Tasks 3 and 4:

  ```python
  USAGE = "pick_background.py <timeline.json> <remotion-cli> <run-dir> --dir <clips> [--seed <int>]"
  LINK_TARGET = os.path.join("..", "bg-stage")   # what <run-dir>/public/bg points at
  def stage_dir(run: str) -> str                 # <real run-dir>/bg-stage
  def inside_runs(folder: str, run: str) -> bool # folder is, or lies under, the parent of the real run-dir
  ```

  and the line `background: FAIL --dir <dir> is inside the workspace's runs folder`. `inside_app` is gone.

- [ ] **Step 1: Move the test harness to the new layout.** In `PickerCase.setUp`: `self.ws = self.tmp / "ws"`, `self.runs = self.ws / "runs"`, `self.app = self.runs / "run.1.test"` (made with its parents), `self.stage = self.app / "bg-stage"`, `self.link = self.app / "public" / "bg"`; `self.clips` stays `self.tmp / "clips"`, outside the workspace. The attribute keeps the name `app`: `self.run` is `unittest.TestCase.run`. Set `LINK_TARGET = "../bg-stage"` and `REFUSED = "background: FAIL --dir %s is inside the workspace's runs folder\n"`. The module docstring says that every test gives the picker a run directory under a temporary `<ws>/runs`.

- [ ] **Step 2: Write the failing tests.**

  - In `Staging`, replace `test_clip_staged_beside_the_app_behind_a_relative_link` with `test_clip_staged_in_the_run_directory_behind_a_relative_link` — the link reads `../bg-stage` and resolves to `<run>/bg-stage`; the clip is staged as a regular hard link; `<ws>/runs` holds only the run directory and `<ws>/bg-stage` does not exist. Red: the stage is beside the run directory (`<ws>/runs/bg-stage`), where every run would share it.
  - In `Staging.test_link_replaces_file_and_stale_symlink`, the third case becomes "an absolute link to the stage": it is replaced by the relative link. The assertions on `<app>/bg-stage/clip.mp4` go: that path is now the stage, which the picker empties.
  - Remove `Staging.test_link_survives_another_checkouts_sync`: no sync reaches a run directory.
  - Rename `InsideApp` to `InsideRuns`. `test_dir_inside_the_runs_folder_is_refused_and_nothing_is_deleted` refuses each of: `<ws>/runs`, the run directory, `<run>/bg-stage`, `<run>/bg-stage/sub`, `<run>/public/audio`, `<ws>/runs/run.2.other/clips` (not made), a symlink to `<ws>/runs`, and `<ws>/x/../runs`; `assert_refused` keeps its checks (stdout is the `REFUSED` line, the seeded stage and `public/audio` keep their bytes, no `public/bg`, the timeline is unchanged, no probe ran). Red: no guard, or one that still names `<ws>/bg-stage`.
  - `test_dir_with_other_case_is_refused_on_a_case_insensitive_volume` uses `<ws>/RUNS`.
  - `test_folders_next_to_the_runs_folder_are_not_refused` — `<ws>/backgrounds`, `<ws>/runs-extra`, `<ws>/bg-stage` and `<ws>/app/public` each hold `x.mp4` and give `background: ok x.mp4 @...`. Red: a string-prefix guard, or one that guards the whole workspace or the old paths.
  - Remove `test_the_app_itself_is_not_refused`: the run directory is in the refused list now.

- [ ] **Step 3: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_pick_background`
  Expected: `FAILED`; `Staging` and `InsideRuns` cases fail on the link target `../../bg-stage` and on the old FAIL text. A skipped "real" case means the workspace has no packages (Global Constraints).

- [ ] **Step 4: Change `pick_background.py`.** Contract:
  - The third argument is the run directory, the Remotion project of this render. The probe keeps `cwd` there.
  - `prepare_stage` empties `<run>/bg-stage` (made if missing) and makes `<run>/public/bg` the relative link `../bg-stage`, replacing a file, a directory or another link at that path, never following a link. Its error stays `cannot prepare <stage>: <reason>`.
  - `stage_clip` and the timeline `src` (`bg/clip<.ext>`) do not change.
  - `inside_runs` compares by real path and with `os.path.samefile` on every ancestor, as `inside_app` does today, against one root: the parent directory of the real run directory. It runs before anything is touched, after the seed check.
  - The module docstring describes this layout and rule: why the stage is a real directory behind a directory link (a file that is itself a link is not served), and why a folder in `<ws>/runs` is refused (`render.sh` removes run directories, the day-old ones of other runs too).

- [ ] **Step 5: Change the bullet of `rungs/brainrot.md`.** The bullet that starts "To force the generated loop" becomes exactly this (the file then passes `ste_lint.py` with 0 errors and 0 warnings, checked at planning):

  ```
  - To force the generated loop, set `EXPLAIN_BRAINROT_BACKGROUNDS` to an empty folder. Do not set
    it to `<ws>/runs`, or to a folder in it. Each render makes its own folder there and removes
    that folder when it stops. The picker refuses such a path with `background: FAIL`.
  ```

- [ ] **Step 6: Run the tests and see them pass.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_pick_background tests.test_render.BrainrotRouteCase`
  Expected: `OK` (`test_rung_file_lints_clean` among them)

- [ ] **Step 7: Commit.**

  ```bash
  git add skills/explain/video/pick_background.py skills/explain/rungs/brainrot.md skills/explain/tests/test_pick_background.py
  git commit -m "feat: explain: the background picker stages in the run directory and refuses a folder in runs"
  ```

---

### Task 3: `render.sh` renders in a run directory

**Files:**
- Modify: `skills/explain/scripts/render.sh` (header comment lines 2-52; globals at lines 107-115; `stage_workspace` at 213-222; `stage_background` at 267-282; `stage_render` at 284-309)
- Modify: `skills/explain/video/remotion.config.ts` (the comment at lines 1-2)
- Test: `skills/explain/tests/test_render.py`

**Interfaces:**
- Consumes: the picker's third argument is a run directory (Task 2).
- Produces:

  ```bash
  run=""              # global: the run directory of this render; "" until make_run_dir has made it
  sweep_old_runs()    # reads $ws
  make_run_dir()      # reads $ws $app $video; sets $run
  remove_run_dir()    # reads $run
  ```

  and the line `workspace: FAIL cannot make a run directory in <ws>/runs`.

- [ ] **Step 1: Write the harness.** `RunDirectoryCase` in `test_render.py` always runs and needs no workspace. It builds a temporary skill tree `<tmp>/skill` with a copy of the real `scripts/render.sh` and a fake of every tool that script calls, and uses the workspace `<tmp>/w s` (the space is deliberate).
  - Fakes: `scripts/video-workspace.sh` (makes `<ws>/app/node_modules/.bin/remotion`, the fake CLI, and `<ws>/app/node_modules/sentinel.txt`; prints `workspace: ok <ws>`); `scripts/narrate.sh` (writes `audio/durations.json` with engine `say`, and `audio/s1.say.wav`; logs that it ran); `scripts/verify.sh`; `video/build-timeline.mjs` (exit 0 for `--check`; else writes a timeline of that one scene with its `audio` and `"background": {"kind": "generated"}`); `video/transcript.py`; `video/check_budgets.py` (prints `ok 1 3.0 3.000`); `video/check_render.sh`; `video/pick_background.py` (logs its arguments, prints `background: ok generated`, or the line and exit code that the test sets).
  - The fake `video/` also holds `package.json`, `src/marker.txt`, and two decoys, `node_modules/decoy.txt` and `public/decoy.txt`.
  - The fake Remotion CLI appends one JSON line for each call: its arguments, `pwd -P`, the names in its cwd, in `public/` and in `public/audio/`, the real path of `node_modules`, and the names in `<ws>/runs`. `FAKE_REMOTION_EXIT` sets its exit code; `FAKE_REMOTION_SLEEP` makes it sleep first.
  - `start(fmt="explainer", **env)` writes a one-scene `script.json` of that format and returns a `Popen` of the script in its own session (`start_new_session=True`), with stdout and stderr in files. The child sets HUP, INT and TERM back to their default action before it runs the script (`preexec_fn`): a test runner that was started in the background hands SIGINT on as ignored, and bash cannot trap a signal that was ignored when it started.

- [ ] **Step 2: Write the failing tests** in `RunDirectoryCase`:

  - `test_render_runs_in_its_own_run_directory` — the CLI's cwd is `<ws>/runs/run.<pid of render.sh>.<6 characters>` by real path; it holds `package.json` and `src/marker.txt`; its `node_modules` resolves to `<ws>/app/node_modules`; `public/audio` holds `s1.say.wav`; the command is `render Explain <out>/video.mp4 --props <out>/build/timeline.json`. Red: the render keeps cwd `<ws>/app`.
  - `test_a_checkouts_node_modules_and_public_are_not_copied` — `public/` of the run directory holds only `audio`; its `node_modules` resolves to `<ws>/app/node_modules`, and that directory holds no `decoy.txt`. Red: a plain recursive copy of `video/`.
  - `test_nothing_is_written_under_the_app` — after a passing run the names in `<ws>/app` are `["node_modules"]`. Red: the audio still goes to `<ws>/app/public/audio`.
  - `test_run_directory_removed_after_a_pass` — exit 0; `<ws>/runs` exists and is empty; `sentinel.txt` exists. Red: no EXIT trap, or a removal that goes through the `node_modules` link.
  - `test_run_directory_removed_after_a_fail` — with `FAKE_REMOTION_EXIT=3` the last stage line is `render: FAIL remotion render exit 3 (log <out>/build/render.log)`; with a brainrot script and a picker that prints `background: FAIL x` and exits 1 the last stage line is that one. Both: exit 1, `<ws>/runs` empty, the sentinel exists. Red: removal only at the end of the script.
  - `test_run_directory_removed_after_a_signal` — for TERM, INT and HUP: the CLI sleeps 30 s; once its log line exists the signal goes to the process group; the script ends within 10 s with exit 1, `<ws>/runs` is empty, the sentinel exists. Red: no EXIT trap (the directory stays), or no signal trap (the exit code is the signal's).
  - `test_signal_to_render_sh_alone_stops_the_run_when_the_tool_returns` — TERM to the pid of the script only, while the CLI sleeps 3 s: exit 1, no `render`, `container` or `transcript` stage line, `<ws>/runs` empty. Red: the signal is ignored and the run goes on to `transcript: ok`.
  - `test_old_run_directories_are_swept` — before the run, `<ws>/runs/run.1.oldold` (modification time 25 hours back, with a `node_modules` link to a directory outside that holds `keep.txt`) and `<ws>/runs/run.2.young` (23 hours back): the CLI sees `run.2.young` and its own directory in `<ws>/runs` and not `run.1.oldold`; after the run only `run.2.young` is left; `keep.txt` exists. Red: a sweep with no age test, or a removal that follows the link.
  - `test_unmakeable_run_directory_fails_the_workspace_stage` — with `<ws>/runs` planted as a regular file the stage lines are `script: ok (1 scenes)` then `workspace: FAIL cannot make a run directory in <ws>/runs`; exit 1; `narrate.sh` did not run. Red: the failure is ignored and a render starts with an empty `run`.

  In `StageFunctionCase`: `run_stage` also sets `run=<tmp>/ws/runs/run.1.test`, and `test_picker_arguments_and_default_folder` expects that path as the picker's third argument in place of `<tmp>/ws/app`.

- [ ] **Step 3: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render`
  Expected: `FAILED`; every `RunDirectoryCase` test and `test_picker_arguments_and_default_folder` fail (the CLI's cwd is `<ws>/app`); the other classes pass; `SayFixtureCase` is skipped.

- [ ] **Step 4: Change `render.sh`.** Contract:
  - `run=""` is assigned with the other globals. Right after it: `trap remove_run_dir EXIT` and `trap 'exit 1' HUP INT TERM`. Both are set before any stage runs.
  - `remove_run_dir` does nothing while `run` is empty; else it removes that one directory with `rm -rf "$run"` (no trailing slash, no glob: the `node_modules` link is removed, never followed).
  - `sweep_old_runs` removes each entry directly under `$ws/runs` whose modification time is more than 1440 minutes back, in the same way. A removal that fails is ignored.
  - `make_run_dir` makes `$ws/runs`, calls `sweep_old_runs`, makes `run` with `mktemp -d "$ws/runs/run.$$.XXXXXX"`, copies `$video/` into it without a top-level `node_modules` or `public` (file, link or directory) and without `__pycache__`, links `$run/node_modules` to `$app/node_modules`, and makes an empty `$run/public`. Any failing step ends the run with `workspace: FAIL cannot make a run directory in $ws/runs`.
  - `stage_workspace` calls `make_run_dir` after `video-workspace.sh` has passed and before it prints `workspace: ok $ws`.
  - `stage_background` gives the picker `"$run"` where it gave `"$app"`.
  - `stage_render` copies the clips to `$run/public/audio` and runs the CLI with cwd `$run`. It no longer removes or makes anything under `$app`. `$remotion` stays `$app/node_modules/.bin/remotion`, and its missing-CLI line stays.
  - `stage_checks` does not change: `check_render.sh` keeps the shared binary and cwd `<ws>/app`.
  - Header comment: the run directory (what it holds, when it is made, removed and swept); "The Remotion CLI runs with cwd `<ws>/runs/<run>`"; under `exit 1`, "or HUP, INT or TERM stopped the run"; the lines that say `public/audio` is emptied or that name `<ws>/app` as the project go.
  - `video/remotion.config.ts`: the comment says the CLI runs as `<workspace>/app/node_modules/.bin/remotion` with cwd `<workspace>/runs/<run>`, a copy of this directory.

- [ ] **Step 5: Run the tests and see them pass.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render`
  Expected: `OK (skipped=3)`

- [ ] **Step 6: Commit.**

  ```bash
  git add skills/explain/scripts/render.sh skills/explain/video/remotion.config.ts skills/explain/tests/test_render.py
  git commit -m "feat: explain: render.sh compiles each render in its own run directory"
  ```

---

### Task 4: the gated tests follow the new layout

**Files:**
- Modify: `skills/explain/tests/video_e2e.py` (docstring; `render_fixture` at lines 37-49)
- Modify: `skills/explain/tests/test_render_brainrot.py` (docstring lines 1-16; `workspace` at 85-86; `render_brainrot` at 104-108)
- Modify: `skills/explain/tests/test_short_still.py` (docstring lines 1-8; `workspace` at 42-43; `setUpClass` at 76-119; `run_still` and `long_clip_props` at 121-199)
- Test: `skills/explain/tests/test_render.py` (one always-run class for the helpers, one gated case)

**Interfaces:**
- Consumes: Tasks 1 to 3.
- Produces, for Task 5 and later waves:

  ```python
  # tests/video_e2e.py
  def workspace() -> Path             # $EXPLAIN_VIDEO_WORKSPACE, else ~/karpathy/video-workspace
  def render_env(**extra: str) -> dict  # os.environ without EXPLAIN_BRAINROT_BACKGROUNDS and
                                        # EXPLAIN_BRAINROT_SEED, then `extra`; EXPLAIN_VIDEO_WORKSPACE is kept
  ```

- [ ] **Step 1: Write the failing tests.** `E2EHelperCase` in `test_render.py`, always run, with `mock.patch.dict(os.environ, ...)`:

  - `test_render_env_keeps_the_callers_workspace` — with `EXPLAIN_VIDEO_WORKSPACE=/x/ws`, `render_env()["EXPLAIN_VIDEO_WORKSPACE"] == "/x/ws"` and `workspace() == Path("/x/ws")`; with the variable absent, the key is absent and `workspace()` is `~/karpathy/video-workspace`. Red: the variable is dropped, so a test render goes to the default workspace.
  - `test_render_env_drops_the_callers_background_settings` — with both `EXPLAIN_BRAINROT_*` variables set in the environment, `render_env()` has neither, and `render_env(EXPLAIN_BRAINROT_SEED="7")["EXPLAIN_BRAINROT_SEED"] == "7"`. Red: the caller's seed or clip folder steers a test render.

  Two gated tests, `test_render_used_the_callers_workspace`, one in `SayFixtureCase` (`test_render.py`) and one in `BrainrotRenderCase` (`test_render_brainrot.py`, for both background kinds): the second stage line of the render is exactly `workspace: ok <workspace()>`. Red: the helper drops the variable and the render goes to the default workspace. That broken state is a render in the workspace this branch must not use, so it is not run: `E2EHelperCase` is the red-first proof of the helper, and these two cases bind the real renders to it.

- [ ] **Step 2: Run them and see them fail.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render.E2EHelperCase`
  Expected: `ERROR`; `cannot import name 'render_env'`.

- [ ] **Step 3: Change the helpers.** `video_e2e.py` gets `workspace` and `render_env`; `render_fixture` runs with `env=render_env()`. `test_render_brainrot.py` imports `workspace` from `video_e2e` and drops its own; `render_brainrot` runs with `render_env(EXPLAIN_BRAINROT_BACKGROUNDS=<clips>, EXPLAIN_BRAINROT_SEED=SEED)`. Both docstrings say that the render uses `$EXPLAIN_VIDEO_WORKSPACE`, else the default workspace, in a run directory of its own; the brainrot docstring names the picker's new rule (a `--dir` inside `<ws>/runs` is refused).

- [ ] **Step 4: Run them and see them pass.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render tests.test_check_render tests.test_landscape_regression tests.test_render_brainrot`
  Expected: `OK`; every gated class is skipped.

- [ ] **Step 5: Give `test_short_still.py` its own project.** At the base it draws stills with cwd `<ws>/app` and counts on the source sync that Task 1 removed. Contract:
  - `setUpClass` still runs `video-workspace.sh --engine say` (it keeps the packages current) and skips the class when that fails.
  - `cls.app` becomes `cls.root / "runs" / "still"`: a copy of `EXPLAIN / "video"` without `node_modules`, `public` and `__pycache__`, with `node_modules` as a link to `workspace() / "app" / "node_modules"`. The narration clips go under `cls.app / "public" / "audio"`.
  - `run_still` runs `workspace() / "app" / "node_modules" / ".bin" / "remotion"` with cwd `cls.app`.
  - `long_clip_props` gives the picker `cls.app` as the run directory. The clip folder stays `cls.root / "clips"`: it must not lie under `cls.root / "runs"`, which the picker refuses.
  - `workspace` is imported from `video_e2e`; the module's own copy goes. The docstrings name the project of the class in place of `<ws>/app` and `<ws>/bg-stage`.
  - New test `test_stills_are_drawn_from_this_checkout` — `cls.app` is not under `workspace()` by real path, and `cls.app / "src" / "Root.tsx"` has the bytes of `EXPLAIN / "video" / "src" / "Root.tsx"`. Red: `cls.app` points at `<ws>/app` again, where older code may have left other sources.

- [ ] **Step 6: Run the gated tests.**

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render tests.test_render_brainrot tests.test_short_still`
  Expected: the workspace path on the first line, then `OK` with no skip. Both `test_render_used_the_callers_workspace` cases pass. `SayFixtureCase` shows nine `ok` lines and `BrainrotRenderCase` ten for the generated loop, the clip and the limits script: this is the map's "brainrot's end-to-end cases pass with the background stage in the run directory". About 8 minutes.

  If a run fails here because of a defect in Task 1, 2 or 3, fix it in this task: first add an always-run test that shows it where a fake can, then change the code, and name the fix in the commit.

- [ ] **Step 7: Commit.**

  ```bash
  git add skills/explain/tests/video_e2e.py skills/explain/tests/test_render.py skills/explain/tests/test_render_brainrot.py skills/explain/tests/test_short_still.py
  git commit -m "test: explain: gated renders keep the caller's workspace; short stills draw from their own project"
  ```

---

### Task 5: two renders at the same time, and the wave's acceptance

**Files:**
- Create: `skills/explain/tests/test_render_parallel.py`

**Interfaces:**
- Consumes: `workspace`, `render_env`, `fixture_script`, `E2E`, `E2E_REASON`, `EXPLAIN`, `RENDER_SH`, `RENDER_TIMEOUT` from `video_e2e`; `ORDER`, `stage_lines` from `test_render`; `BRAINROT_TEMPLATE`, `BACKGROUND`, `SEED`, `stage_patterns` from `test_render_brainrot`.
- Produces:

  ```python
  def tree_digest(root: Path, skip: tuple = ("node_modules",)) -> str
  ```

  sha256 over every entry under `root` in sorted order of its relative path, without the top-level names in `skip`: the path, its kind (file, directory, link), and the bytes of a file or the target of a link.

- [ ] **Step 1: Write the tests.** The module docstring says what the file proves (spec §9.2, the run-directory case) and that it needs `EXPLAIN_VIDEO_E2E=1`.

  `TreeDigestCase`, always run, on a temporary tree:
  - `test_digest_sees_a_new_file_a_changed_byte_and_a_changed_link` — each of the three changes gives another digest. Red: a digest of the names only.
  - `test_digest_skips_top_level_node_modules_only` — a change in `node_modules/x` keeps the digest; a change in `src/node_modules/x` changes it. Red: the skip matches at every depth, or not at all.

  `ParallelRenderCase`, gated. `setUpClass` runs `video-workspace.sh --engine say` (skip the class with its output when it fails), takes `tree_digest(workspace() / "app")`, starts an explainer render (`fixture_script()`) and a brainrot render (the template, an empty clip folder, `SEED`) with `Popen` in their own sessions (`env=render_env(...)`, and HUP, INT and TERM set back to their default action in the child, as in Task 3), one right after the other, each in its own temporary output directory with stdout and stderr in files, notes the start and end time and the pid of each, waits for both, and takes the digest again.
  - `test_the_two_renders_ran_at_the_same_time` — the later start is before the earlier end. Red: the renders ran one after the other, so the class shows nothing.
  - `test_both_renders_print_all_their_ok_lines` — both exit 0; the explainer has nine stage lines that match `ORDER`, brainrot ten that match `stage_patterns(4)` with `BACKGROUND["generated"]`. Red: a shared `public/audio` or a shared project, where one render takes the other's files.
  - `test_the_app_is_unchanged` — the two digests are equal. Red: a render writes audio or sources under `<ws>/app`.
  - `test_no_run_directory_is_left_after_a_pass` — `<ws>/runs` has no entry that starts with `run.<pid>.` for either pid. Red: no removal on exit.
  - `test_no_run_directory_is_left_after_a_fail` — a brainrot render with `EXPLAIN_BRAINROT_SEED=abc`: exit 1; its stage lines have `workspace: ok` and a `timeline (` line, and end with `background: FAIL EXPLAIN_BRAINROT_SEED must be an integer, got 'abc'`; no `run.<pid>.` entry. Red: removal only on success.
  - `test_no_run_directory_is_left_after_sigterm` — an explainer render in its own session; when its stdout has a `timeline (` line, an entry `run.<pid>.` exists (asserted); two seconds later TERM goes to the process group; the script ends within 60 s with exit 1; no `run.<pid>.` entry; `<ws>/app/node_modules/.explain-lock-sha` exists. Red: no trap, or a removal through the `node_modules` link.

  The checks name their own pids because other sessions of this branch may render in the same workspace.

- [ ] **Step 2: Run the always-run part.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_render_parallel`
  Expected: `OK (skipped=6)`; apply the two named mutations of `TreeDigestCase` to `tree_digest`, see each test fail, and revert.

- [ ] **Step 3: Run the gated part.**

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_parallel`
  Expected: the workspace path, then `OK` with no skip.

  To see the class fail in the broken state, once: in a scratch copy of `render.sh`, point `stage_render` at `$app` again, run the class against that copy, see `test_the_app_is_unchanged` fail, and discard the copy.

  If `test_both_renders_print_all_their_ok_lines` fails and the same two renders pass one after the other: read both `build/render.log` files. When they name the bundler cache (or `<ws>/app/node_modules/.cache` now exists), add `--bundle-cache=false` to the `remotion render` command of `render.sh` (spec §7.6), extend `test_render_runs_in_its_own_run_directory` of Task 3 with that argument first, and run again. Any other cause is a defect of Tasks 1 to 3: fix it as Task 4 Step 6 says.

- [ ] **Step 4: Commit.**

  ```bash
  git add skills/explain/tests/test_render_parallel.py
  git commit -m "test: explain: two renders at the same time pass and leave the shared app and runs clean"
  ```

  Add `skills/explain/scripts/render.sh` and `skills/explain/tests/test_render.py` to that commit only when Step 3 changed them.

- [ ] **Step 5: Run the full unit suite, once.**

  Run: `cd skills/explain && python3 -B -m unittest discover -s tests`
  Expected: `OK (skipped=33)`: the 24 of the base, the six of `ParallelRenderCase`, the two `test_render_used_the_callers_workspace` and `test_stills_are_drawn_from_this_checkout`. No failure and no error.

- [ ] **Step 6: Run the map's acceptance.**

  Run: `cd skills/explain && python3 -B -m unittest tests.test_video_workspace tests.test_pick_background`
  Expected: `OK`, and no "real" picker case skipped.

  Run: `cd skills/explain && test -n "$EXPLAIN_VIDEO_WORKSPACE" && echo "$EXPLAIN_VIDEO_WORKSPACE" && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_parallel tests.test_render tests.test_render_brainrot`
  Expected: the workspace path, then `OK` with no skip. About 12 minutes.

  Then check the tree: `git status --short` prints nothing, and `git diff --stat c24a149bce8b9b49b1ff7857ae16dcae8164cafe -- . ':!docs'` lists only files that Global Constraints allows.

## Wave close

The map's `done_when` is met by: Task 5 Step 3 (two renders together with nine and ten `ok` lines, the checksum of `<ws>/app`, no run directory after a pass, a fail and SIGTERM), Task 1 (the two-package-files case), and Task 4 Step 6 with Task 5 Step 6 (brainrot end to end with the stage in the run directory).

Inputs for the plans of later waves:

- `film-render`, `film-scene-stage`, `film-guard`: the Remotion project of a run is `$run`. The scene copy and `tsc`, the guard pass and the film render use it as cwd. `clear_stale` and the film's `build/guard.mp4` stay in `<out>`. A new long step needs no cleanup of its own: the EXIT trap removes `$run`.
- `film-scene-stage`: its "a film run leaves `<ws>/app` unchanged" check can import `tree_digest` from `tests/test_render_parallel.py`.
- `film-docs`: `rungs/video.md` still says that `app/` holds the sources; it holds the two package files and `node_modules`, and `runs/` holds a directory for each running render. The stage line `workspace: ok <ws>` did not change; `workspace: FAIL cannot make a run directory in <ws>/runs` is new.
- `explainer-removal`: the header comment of `tests/capture_landscape_baseline.sh` still describes the source sync; the file goes in that wave. `video_e2e.py` now also exports `workspace` and `render_env`.
- Any wave: a new gated test renders with `env=render_env(...)` and finds the workspace with `workspace()`, so that it follows `EXPLAIN_VIDEO_WORKSPACE`.
