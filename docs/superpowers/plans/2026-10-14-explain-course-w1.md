# explain course rung: wave 1 (the whole feature)

Spec: `docs/superpowers/specs/2026-10-14-explain-course-design.md`. One cohesive wave, high risk
(new on-disk state format with resume semantics). Coverage: not opted in. Worktree
`~/karpathy-wt/course`, branch `feat/explain-course`. All paths below are relative to
`skills/explain/` unless they start with `docs/`.

## 1. Goal and done-when

`/explain <sources> --as course` maps the sources, writes `course.json`, prints a plan and stops
for approval; after approval it builds one lesson per subagent and writes a hub page that passes
`verify.sh`. A rerun on the course directory resumes.

Done when:

- `cd skills/explain && python3 -B -m unittest discover -s tests` passes (the full suite, with
  the new course tests).
- `verify.sh` on a hub generated from the fixture course prints seven `ok` lines (`bpmn: none`
  allowed).
- A live run of `/explain diadoc esb --as course` (sources in `~/work`) reaches the approval stop
  with `course.py check` printing `course: ok` and `course.py summary` printing the plan.

## 2. Current-code facts

- Tests are `unittest` modules in `tests/`, run from `skills/explain` (no package; modules
  import siblings as `from tests.x import …` or by `sys.path`). Chrome tests run `verify.sh`
  with a private `TMPDIR` (see `tests/test_page_template.py`).
- `scripts/cite_check.py` exposes `check(html, html_dir) -> list[str]`; a cite resolves
  `data-path` against `os.path.join(html_dir, data-root)`; `data-kind` must be one of
  `file|directory|topic|conversation`; only `file|directory` need a cite per section.
- `scripts/verify.sh` picks viewports from `<meta name="explain-rung">` (case list near
  "rung=lesson"); the `media` check runs only for `rung=lesson` and counts `video src|poster`
  and `a href` starting with `clips/`; the `bpmn` check calls `bpmn.py check --rung <rung>`.
- `scripts/bpmn.py`: `RUNGS = ("sheet", "page", "lesson")` gates `--rung`.
- `templates/page.html`: meta `explain-rung=page`; `<header>` with `h1` and `.answer` box (the
  guard fails `NOANSWER` without it); `<nav id="toc">` with the Sources switch; `<main>` of
  `<section>`s; `<footer>` with `#provenance` (`data-root`, `data-kind`, `dl data-ste="skip"`) and
  `p.not-covered`; the guard script writes `data-verify` on `<html>`.
- `../ste/scripts/ste_lint.py [--html] [FILE]`: exit 0 clean, 1 with errors.
- `rungs/lesson.md` sections "Output directory" and "Finish and handoff" give the lesson
  outputs and its seven verify lines; `tests/test_lesson_prompts.py` and
  `tests/test_rung_drift.py` pin rung text to code and must keep passing.
- `SKILL.md` Contract step 4 lists the six `--as` names; `README.md` repeats the `--as` list
  (pinned by `SkillMdCase` in `tests/test_rung_drift.py`).

## 3. Interfaces

Produced (CLI, `scripts/course.py`, stdlib only, exit 0 ok / 1 check failure / 2 usage or read
error):

```
course.py check <dir>
course.py summary <dir>
course.py approve <dir>
course.py next <dir> [--limit N]
course.py mark <dir> <lesson-id> pending|building|done|failed|dropped [--reason TEXT]
course.py reopen <dir>
course.py hub <dir>
```

Produced (module functions, for tests and reuse):

```python
def load(course_dir: str) -> dict
def save(course_dir: str, course: dict) -> None          # atomic: temp file + os.replace
def check(course_dir: str, course: dict) -> list[str]     # failures, empty = ok; no state change
def shape(course: dict) -> str                            # sha256 hex of the shape (spec 5)
def next_lessons(course: dict, limit: int | None) -> list[str]
def render_hub(course_dir: str, course: dict, template: str) -> str   # the hub HTML
```

Produced (files): `course.json` v1 (spec section 5), `course/map-task.md`,
`course/lesson-task.md`, `rungs/course.md`, `<meta name="explain-rung" content="course">`.

Consumed: `cite_check.check`, `ste_lint.py --html`, `templates/page.html`, `verify.sh`,
`git -C <source> rev-parse --short HEAD` and `git -C <source> status --porcelain`.

## 4. Invariants and named failure behavior

- `course.json` is written only through `save` (atomic). A crash mid-write leaves the old file.
- `check` failure lines (one per fault, prefixes fixed so tests and the rung can quote them):
  `schema: <field>: <problem>`, `id: duplicate <id>`, `lesson <id>: unknown hop <h>`,
  `lesson <id>: unknown source <s>`, `hop <id>: in no lesson`, `hop <id>: branch <b> is not an
  earlier hop`, `hop <id>: <evidence> hop needs a cite` / `inferred hop has a cite`,
  `source <id>: path missing: <abs>`, `cite <hop>#<n>: <cite_check-style problem>`,
  `lesson <id>: done but lessons/<id>/index.html missing`, `prose: <ste_lint error line>`,
  `state: plan changed after approval; run summary and approve again`. Last line: `course: ok`
  or `course: <n> failures`.
- `check` on an `approved` course whose `shape` differs from `approved_shape` sets `state` to
  `planned` (the only state change `check` makes) and reports the `state:` failure.
- `next` refuses on `planned` (exit 1, `next: course not approved`). `mark done` refuses without
  `lessons/<id>/index.html`; `mark failed|dropped` refuses without `--reason`; `mark` with a
  reason for another status refuses. Unknown lesson id: exit 1, `mark: unknown lesson <id>`.
- `approve` refuses unless `check` is clean; it writes `approved_shape` and `state: approved`.
- `reopen` resets `failed` → `pending` only; `done` course → `approved` when it reset any.
- `hub` sets `state: done` only when no lesson is `pending` or `building`.
- The hub never links a lesson that is not `done`; a hop with no `done` lesson shows "not
  built"; failure hops sit in a lower row under their branch hop.
- The hub passes `cite_check` (hop cites rendered as page cite blocks, `data-kind="topic"`,
  `data-root` = course `root`) and `ste_lint --html` (generated sentences are STE-80; data cells
  in `data-ste="skip"` elements).

## 5. Rollback and recovery

New files plus additive cases in `verify.sh` and `bpmn.py`; existing rungs are untouched.
Rollback is reverting the branch. Run recovery is the spec's resume (`reopen`, stale lesson
directories moved aside to `lessons/<id>.stale-<n>/`, never deleted; that move is an
orchestrator step in `rungs/course.md`).

## 6. Acceptance commands

```
cd skills/explain && python3 -B -m unittest tests.test_course          # unit, no Chrome
cd skills/explain && python3 -B -m unittest tests.test_course_hub      # hub through verify.sh (Chrome)
cd skills/explain && python3 -B -m unittest tests.test_course_prompts tests.test_rung_drift tests.test_lesson_prompts
cd skills/explain && python3 -B -m unittest discover -s tests          # full suite: "OK"
```

Live: `/explain diadoc esb --as course` from `~/karpathy-wt/course` stops at the approval
summary; `python3 skills/explain/scripts/course.py check <dir>` prints `course: ok`.

## 7. Tasks

Tasks 1-4 are sequential (one file, `scripts/course.py`). Task 5 depends on 4. Tasks 6-8 own
markdown files and can run after 4 in any order; 9 runs last.

### Task 1: `course.json` load, save and structural check

Files: `scripts/course.py`, `tests/test_course.py`, fixture `tests/fixtures/course/` (a
`course.json` over a tiny fake root `tests/fixtures/course-root/` holding two "sources": a
directory `svc-a/` with a code file and `docs-b/` with a markdown file).

Behavior: `load` reads `<dir>/course.json` (exit 2 on missing or bad JSON from the CLI);
`save` is atomic. `check` covers every structural line of section 4 except `prose:` and
`state:`: schema types and enums, id pattern and uniqueness (hops, blocks, lessons, sources),
lesson→hop and lesson→source references, each hop in a lesson (any status), `branch` names an
earlier hop, cite presence by evidence, source path exists under `root`, cite path/line/snippet
(reuse the cite rules of `cite_check.py`: ≤ 12 words, verbatim on that line), `done` lesson
has its `index.html`. CLI `check` prints the lines and the summary line.

Tests (each a mutation of the fixture that must produce exactly its line):
`test_fixture_is_clean` — the fixture prints `course: ok`;
one test per failure prefix of section 4 (except prose and state).

### Task 2: state machine and prose lint

Files: `scripts/course.py`, `tests/test_course.py`.

Behavior: `shape`, `approve`, `next`, `mark`, `reopen` as section 4; `check` gains the `prose:`
lines (write the prose fields — title, question, hop `what`, block titles, lesson questions and
briefs, `not_covered` — into a temporary HTML document with the course `lang` and run
`ste_lint.py --html`; each error line prefixed `prose: `) and the `state:` rule.

Tests: `test_approve_refuses_dirty_plan`; `test_next_refuses_planned`;
`test_next_lists_pending_and_building_in_plan_order`; `test_next_limit`;
`test_mark_done_needs_index`; `test_mark_failed_needs_reason`; `test_mark_reason_only_for_failed_or_dropped`;
`test_reopen_resets_failed_only`; `test_reopen_done_course_returns_to_approved`;
`test_shape_ignores_prose_and_cites`; `test_shape_change_after_approval_resets_to_planned`;
`test_prose_error_is_reported` (a non-STE word in a hop `what` gives a `prose:` line).

### Task 3: `summary`

Files: `scripts/course.py`, `tests/test_course.py`.

Behavior: prints, in this order: title and question; sources (id, kind, named/discovered, why,
and `moved: <old> -> <new>` or `moved: dirty` when git disagrees with `course.json`; a source
outside git shows its recorded `none`); the main path as `from → to` lines with evidence, and
failure hops indented under their branch hop; blocks with lessons (`<id>  <question>  [hops]
<status>`); `lessons: <n>, about <h> h at 3 at once` (30 min per lesson); `not covered:` lines.

Tests: `test_summary_lists_every_lesson_and_hop`; `test_summary_marks_moved_source` (fixture
source inside a temporary git repo, commit, then change the recorded commit).

### Task 4: the hub

Files: `scripts/course.py`, `tests/test_course.py` (static hub tests), fixture lesson
`tests/fixtures/course/lessons/<done-id>/index.html` (a minimal file; it only needs to exist).

Behavior: `render_hub` reads `templates/page.html`, keeps everything outside the region from
`<header>` to `</footer>` (head, styles, scripts), sets the meta to `course` and `<html lang>`
to the course `lang`, and writes the body of spec section 7: header with `h1` (title) and the
answer box (generated sentences per block), nav with one entry per block plus the Sources
switch kept from the template, the flow diagram section (SVG, main row plus failure row,
evidence border styles with legend, links to the first `done` lesson), one section per block,
the not-covered list, the footer provenance (rows per source, moved note, review setting).
Generated sentences pass STE-80; ids, paths, hashes and statuses sit in `data-ste="skip"`
elements or `<code>`. Hop cites render as one `div.cites` per hop item, in the markup of
convention 2. `hub` CLI writes `index.html` and applies the `done` transition.

Tests: `test_hub_passes_cite_check` (`cite_check.check` returns `[]`);
`test_hub_passes_ste_lint`; `test_hub_links_only_done_lessons`;
`test_hub_failure_hop_in_lower_row`; `test_hub_marks_moved_source`;
`test_hub_sets_done_only_when_nothing_open`.

### Task 5: `verify.sh` and `bpmn.py` know the course rung

Files: `scripts/verify.sh`, `scripts/bpmn.py`, `tests/test_course_hub.py`.

Behavior: `rung=course` gets the page viewports; the `media` check runs for `lesson` and
`course`, and for a course also counts `a href` values starting with `lessons/` that name no
file; the header comment and usage text list `course`; `bpmn.py` `RUNGS` gains `course`.

Tests (Chrome): `test_fixture_hub_passes_verify` — seven lines, all `ok` except `bpmn: none`;
`test_missing_lesson_link_fails_media` — a hub whose `done` lesson directory is removed after
generation prints `media: FAIL 1 missing`.

### Task 6: the two subagent prompts

Files: `course/map-task.md`, `course/lesson-task.md`, `tests/test_course_prompts.py`.

Behavior: prompt templates filled by plain `{name}` replacement, like `lesson/review-*.md`.
`map-task.md` placeholders: `{skill_dir}`, `{course_dir}`, `{source_id}`, `{source_path}`,
`{root}`, `{lang}`; it asks for `map/<source_id>.md` with the sections of spec step 9.2 (entry
points; in and out; formats and transforms; routing config; error paths; other systems named),
every fact with a `path:line` and a verbatim snippet, and one result line
`map: done <source_id> <n> facts` or `map: failed <reason>`. `lesson-task.md` placeholders:
`{skill_dir}`, `{course_dir}`, `{lesson_id}`, `{lesson_json}`, `{hops_json}`, `{map_paths}`,
`{other_lessons}`, `{root}`, `{lang}`, `{review}`; it carries the rules of spec section 10 and
the result line `lesson: done <rung> <n> clips` or `lesson: failed <reason>`.

Tests: `test_placeholders_are_exactly_the_named_set` (per file, every `{name}`);
`test_result_lines_present`; `test_lesson_task_names_the_overrides` (output directory,
`data-root`, Sources row, zero-clip page, no `open`); both files pass `ste_lint.py` (markdown).

### Task 7: `rungs/course.md`

Files: `rungs/course.md`, `tests/test_course_prompts.py` (rung case).

Behavior: the instructions of spec sections 3 to 10 for the orchestrator, in build order:
resolve, map, discover, plan, check and stop, revise, build (slots, `mark`, background
subagents, `verify.sh` decides `done`/`failed`, stale directory move), hub, handoff, resume.
It quotes the `course.py` commands and the `check` summary lines exactly, names the two prompt
files, and the seven verify lines of a hub in one fenced block.

Tests: `test_rung_quotes_every_course_command` (each CLI command of section 3 appears);
`test_rung_names_prompt_files_that_exist`; `test_rung_verify_block_matches_lesson_lines`
(the fenced block equals the seven lines of a lesson); `test_rung_lints_clean`.

### Task 8: routing in `SKILL.md` and `README.md`

Files: `SKILL.md`, `README.md` (repo root), `tests/test_rung_drift.py`.

Behavior: `course` joins the `--as` list (argument-hint, Contract step 4 with seven names),
the rung table (forced only; several sources; "a system of several services"), the rule that a
directory holding `course.json` under `--as course` resumes, a `Rung files` bullet for
`rungs/course.md`, and `--review` applies to `lesson` and `course`. README gets the `--as`
list and one line on the course, and the requirements row (`course`: the needs of `lesson`).

Tests: extend `SkillMdCase` so the `--as` list of README equals the argument-hint (already
pinned; update the expected set) and the `course` rung bullet names `rungs/course.md`; run
`tests.test_rung_drift tests.test_lesson_prompts`.

### Task 9: live run to the approval stop

Not a code task. From `~/karpathy-wt/course`, run the course rung by its instructions on
`diadoc esb` (sources resolve to `~/work/diadoc` and `~/work/esb` by rules 3.1), through map,
discover and plan, to the approval stop. Fix any rung or script fault it exposes (with a test
where the fault is in a script). Evidence: the output directory path, `course: ok`, and the
summary. Leave the course `planned` for the user to approve.
