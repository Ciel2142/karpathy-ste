# explain onboard, wave 4 (course-on-flows) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A course plans from the flows of its maps: the map subagent follows "Explore the service" and "The map" of `rungs/onboard.md` and ends with `onboard.py check`; a hop of `course.json` version 2 carries `flow` and `nodes`; `course.py check` binds each hop to its flow, enforces the flow floor and the node floor and refuses version 1 with one line; `summary` shows the flow and the node count; the lesson subagent cuts its first diagram from the map block by the nodes of its hops.

**Architecture:** `course.py` reads the maps of a course through wave 2's `onboard.read_map` and `onboard.flow_nodes` (one import, as it imports `cite_check`). One new check group, `_check_flows`, binds each hop to a `### <flow-id>:` heading of `map/<source-id>.md` and walks every flow of every map and every node of a followed flow against the hops and the names in `not_covered`. Version 2 is a hard break: the command line refuses version 1 before any command runs, and the test fixture becomes a version 2 course over two fixture maps that pass `onboard.check_map`. The two prompts and the rung change text only: `map-task.md` points at two sections of `rungs/onboard.md` with the course paths as overrides, `lesson-task.md` gains the diagram cut rule, `rungs/course.md` gains the check on each map, the version 2 example, the planning rules and the new failure prefixes.

**Tech Stack:** Python 3.14 stdlib, `unittest`, the STE lint (`skills/ste/scripts/ste_lint.py`).

**Spec:** `docs/superpowers/specs/2026-10-16-explain-onboard-design.md` (sections 10, 11, 13; section 14 items 7, 8, 11, 12). Wave map: `docs/superpowers/waves/2026-10-16-explain-onboard.yaml`, wave `course-on-flows`. Coverage: waived.

Base: 58537cad9f03d9e9bb750f728dea9d21de4883e7
Test runs: scoped per task; full suite once, final task.

All paths below are relative to `skills/explain/` unless they start with `docs/`. Every test command runs from `skills/explain/`; every lint command runs from the repository root.

## Global Constraints

- `course.json` is version 2. `check` reports any other value as `schema: version: must be 2`. Every command of `course.py` refuses a file whose `version` is `1` before it does anything else: one line on stderr, verbatim `course: version 1 is older than this skill; start a new course`, nothing on stdout, exit 2, no file changed. Nothing migrates a version 1 course (spec 11).
- A hop carries two more keys, both required. `flow` is `null` or a string `<source-id>/<flow-id>` that matches `[a-z0-9][a-z0-9-]*/[a-z][a-z0-9_-]*`. `nodes` is a list of strings: `[]` when `flow` is `null`, not empty when `flow` is a string. A `code` hop has a string `flow`; a `docs` hop has a string or `null`; an `inferred` hop has `null`. `check` enforces the `code` case (`flow missing`) and the shapes; the rung states the rest (spec 11 lists no line for an `inferred` hop with a flow).
- The flow of a hop is a key of `onboard.flow_nodes(onboard.read_map("<course-dir>/map/<source-id>.md"))` and its nodes are that key's list, in diagram order. A map that is missing, or that `read_map` cannot read, has no flows and gives no failure line of its own (the orchestrator's `onboard.py check` reports it); every hop that names one of its flows gets the `not in map/<s>.md` line.
- The failure lines of `_check_flows`, verbatim and in this order: per hop in plan order, `hop <id>: flow missing` (a `code` hop with `null`) or `hop <id>: flow <s>/<f> not in map/<s>.md`; then `hop <id>: nodes empty` (a string `flow` with `[]`, whether or not the flow exists); then one `hop <id>: node <n> not in flow <s>/<f>` per node in `nodes` order (only when the flow exists). Then `flow <s>/<f>: in no hop and not in not_covered`, per source in `sources` order and flow in map order. Then `node <s>/<f>/<n>: in no hop and not in not_covered`, per followed flow in that order and node in diagram order. A followed flow is a flow of a map that some hop names. A node is on a hop when it is in the `nodes` of a hop whose `flow` is that flow. `check()` runs this group after `_check_hops` and before `_check_sources`.
- A name is in `not_covered` when one of its sentences holds it as a whole token. The tokens of a sentence are its maximal runs of `[a-z0-9_/-]`, so `esb/request-retry` does not name `esb/request`, and a backtick or a period after the name does not break it.
- `summary` prints, after the evidence of a hop with a string `flow`, the flow and the count: `(code, flow esb/request, 4 nodes)`; a branch hop adds `, fails at <branch>` after the count. A hop with `null` keeps `(docs)` or `(inferred)`. The count reads `%d nodes` for every count.
- `shape()` does not change: `flow` and `nodes` are not in it (the spec is silent; prose and cites are not in it either). `course_hub.py` does not change (spec 14, item 7). `course_discover.py` reads `Other systems` as today (spec 10).
- `map-task.md` keeps the placeholder set `skill_dir, course_dir, source_id, source_path, root, lang` and the two result lines `map: done {source_id} <n> facts` (`<n>` counts the fact lines, node lines included) and `map: failed <reason>`. It holds no map skeleton: the skeleton lives in `rungs/onboard.md` "The map", and the ten titles are `onboard.TITLES`.
- The two commands of a course map, verbatim in `map-task.md`, each in its own fenced block: `python3 {skill_dir}/scripts/onboard.py inventory {source_path} --root {root} --out {course_dir}/map/{source_id}.inventory.txt` and `python3 {skill_dir}/scripts/onboard.py check {course_dir}/map/{source_id}.md --root {root} --inventory {course_dir}/map/{source_id}.inventory.txt`. The orchestrator's check in `rungs/course.md`, in a fenced block: `python3 <skill-dir>/scripts/onboard.py check <course-dir>/map/<source-id>.md --root <root>`.
- Lint: `course/map-task.md`, `course/lesson-task.md` and `rungs/course.md` lint clean: `python3 skills/ste/scripts/ste_lint.py <file>` prints `0 errors, 0 warnings` (a procedural sentence has at most 20 words, a descriptive one 25, no `-ing` verb forms, no passive in procedures; code spans count as one word; fenced blocks and tables are not prose). No nested fence in these three files: a fenced block that holds a ```` ```mermaid ```` fence needs a four-backtick outer fence, so the cut rule and the map examples stay in prose.
- This wave changes no file that another wave owns: not `scripts/onboard.py`, `scripts/mermaid_svg.py`, `scripts/cite_check.py`, `scripts/course_hub.py`, `scripts/course_discover.py`, `rungs/onboard.md`, `rungs/page.md`, `SKILL.md`, `README.md`, `templates/page.html`. Stdlib only. Never commit `out/`.
- Commit style of this repository: `feat: explain: …`, `test: explain: …`, `docs: explain: …`.

## Review Focus

1. `not_covered` matched by substring: a sentence that names `esb/request-retry` silences the floor for `esb/request`, and a flow leaves the course unnamed. Expected: a whole-token match; pinned in Task 2 (`test_flow_name_is_a_whole_token`).
2. A map that is missing, unreadable or in the old six-section format under `map/` makes `check` raise (`OnboardError`, `OSError`) instead of printing lines. Expected: one `not in map/<s>.md` line per hop that names it, then `course: <n> failures`; pinned in Task 2 (three tests).
3. A `flow` that names a source the course does not list (a typo) raises in the loop over the sources. Expected: `hop <id>: flow <s>/<f> not in map/<s>.md`; pinned in Task 2.
4. A version 1 course reaches `hub` or `mark` through a resume and the command runs on the old shape (`hub` writes `index.html` from hops that have no flows). Expected: each of the seven commands refuses with the one line, exit 2, before any write; pinned in Task 1.
5. A `docs` hop with `flow: null` and a non-empty `nodes` claims nodes of no flow, which the node floor cannot see. Expected: `schema: hops[<i>].nodes: must be empty when flow is null`; pinned in Task 1.

## File structure

- `scripts/course.py`: the docstring (version 2, the new prefixes); the constants `VERSION`, `OLD_VERSION`, `FLOW_REF`, `NAME_TOKEN`; `_check_schema` (the version) and `_check_hop` (`flow`, `nodes`); the new `_map_flows`, `_named`, `_check_flows`; `check()` (one line); `_summary_hops` (the evidence text); `_load_or_report` (the refusal).
- `tests/fixtures/course/course.json` (version 2, `flow` and `nodes` on the five hops); `tests/fixtures/course/map/svc-a.md`, `tests/fixtures/course/map/docs-b.md` (new: the maps of the two fixture sources over `tests/fixtures/course-root/`).
- `tests/test_course.py` (`LoadSaveCase`, `CheckCase`, `SummaryCase`); `tests/test_course_hub.py` (the directory listing pin only).
- `course/map-task.md` (rewritten: the pointer to `rungs/onboard.md`, the course overrides, the two commands, the stop rule, the result line); `course/lesson-task.md` (the `flow` and `nodes` of a hop under "Your task"; the cut rule under "Scope").
- `rungs/course.md`: "Map the sources" (the inventory file, the check on each map, which map counts), "Plan the course" (the version 2 example, `flow` and `nodes`, the planning rules), "Check and stop" (four table rows), "Resume" (one sentence), "Output directory" (one row).
- `tests/test_course_prompts.py`: `ONBOARD_MD`, `MAP_SECTIONS` (the ten titles), `MAP_RUNG_SECTIONS`, `MAP_COMMANDS`, `MAP_TEXTS`, `MAP_RUNG_TEXTS`, `LESSON_OVERRIDES` (extended), `FLOW_TEXTS`; the map-task test rewritten, one new `CoursePromptCase` test, two new `CourseRungCase` tests.

---

### Task 1: `course.json` version 2: the hop binding fields, the refusal of version 1, the fixture maps

**Files:**
- Modify: `scripts/course.py` (the docstring, `_check_schema`, `_check_hop`, `_load_or_report`)
- Modify: `tests/fixtures/course/course.json`
- Create: `tests/fixtures/course/map/svc-a.md`, `tests/fixtures/course/map/docs-b.md`
- Modify: `tests/test_course.py`, `tests/test_course_hub.py`

**Interfaces:**
- Consumes: `onboard.read_map(path: str) -> MapDoc`, `onboard.check_map(doc: MapDoc, root: str, inventory: list[str] | None = None) -> list[str]`, `onboard.TITLES` (wave 2; `scripts/` is on `sys.path` in the tests).
- Produces:
  ```python
  # scripts/course.py
  VERSION = 2
  OLD_VERSION = "course: version 1 is older than this skill; start a new course"
  FLOW_REF = re.compile(r"[a-z0-9][a-z0-9-]*/[a-z][a-z0-9_-]*")
  ```
  and the fixture course, whose hops bind to the one flow `receive` of `map/svc-a.md` (Task 2's tests mutate exactly these values):
  ```
  receive   "flow": "svc-a/receive", "nodes": ["listen"]
  validate  "flow": "svc-a/receive", "nodes": ["check"]
  reject    "flow": "svc-a/receive", "nodes": ["reject"]
  deliver   "flow": "svc-a/receive", "nodes": ["send"]
  confirm   "flow": null,            "nodes": []
  ```

- [ ] **Step 1: Write the fixtures**

- `tests/fixtures/course/course.json`: `"version": 2`; each of the five hops gains the two keys of the table above, after `"branch"`. Nothing else changes.
- `tests/fixtures/course/map/svc-a.md`: a map in the format of `rungs/onboard.md` "The map": the first line `# Map: svc-a`, then the ten level-2 sections of `onboard.TITLES` in order. Every cite points into `svc-a/Handler.java` of `tests/fixtures/course-root/` (path relative to that root, snippet verbatim on the cited line, at most 12 words). `Flows` holds exactly one flow, this block verbatim (its node ids and their order are what the tests bind to):

  ````
  ### receive: What happens to a message from the queue?
  ```mermaid
  flowchart TD
    listen[IN_QUEUE listener] --> check{result ok?}
    check -->|no| reject[reject with the reason]
    check -->|yes| send[send to the target]
  ```
  ````

  with one node fact line each: `listen` cites line 4, `check` line 7, `reject` line 8, `send` line 11. `Entry points` holds one line, `- listener IN_QUEUE -> receive | svc-a/Handler.java:4 | @Listener(queue = "IN_QUEUE")`. `Architecture` is a small `flowchart LR` of the queue, the handler, the validator and the sender, one cited fact per node. `Other systems` names the target with the handle `` `sender.send` `` in backticks. `Shape`, `Formats and transforms` and `Error paths` hold one fact each. `State`, `Routing config` and `Not covered` are `none found`.
- `tests/fixtures/course/map/docs-b.md`: `# Map: docs-b`; `Architecture`, `Entry points`, `Flows` and `State` are `none found` (a docs source, spec 14 item 11); `Shape` and `Formats and transforms` hold one fact each into `docs-b/api.md`; every other section is `none found`.

- [ ] **Step 2: Write the failing tests**

In `tests/test_course.py` (add `import onboard` beside `import course`):
- `LoadSaveCase.test_load_reads_course_json`: the version is `2`.
- `LoadSaveCase.test_save_leaves_no_temporary_file` and `test_failed_save_keeps_the_old_file_and_cleans_up`: the listing is `["course.json", "lessons", "map"]`.
- `CheckCase.test_fixture_maps_pass_onboard_check` (new): for `svc-a` and `docs-b`, `onboard.check_map(onboard.read_map(os.path.join(self.dir, "map", ident + ".md")), self.root)` is `[]`.
- `CheckCase.test_schema_version_must_be_two` (renames `..._must_be_one`): version `3` → `schema: version: must be 2`.
- `CheckCase.test_schema_flow_missing`: `del self.hop("receive")["flow"]` → `schema: hops[0].flow: missing`.
- `CheckCase.test_schema_flow_must_be_null_or_a_string`: `flow = 5` → `schema: hops[0].flow: must be null or a string`.
- `CheckCase.test_schema_flow_must_name_a_source_and_a_flow`: `flow = "receive"` → `schema: hops[0].flow: must be <source-id>/<flow-id>`; so does `"svc-a/Receive"`.
- `CheckCase.test_schema_nodes_missing` → `schema: hops[0].nodes: missing`; `test_schema_nodes_must_be_a_list`: `nodes = "listen"` → `schema: hops[0].nodes: must be a list`; `test_schema_nodes_items_are_strings`: `nodes = ["listen", 2]` → `schema: hops[0].nodes[1]: must be a string`.
- `CheckCase.test_schema_nodes_must_be_empty_when_flow_is_null`: `self.hop("confirm")["nodes"] = ["x"]` → `schema: hops[4].nodes: must be empty when flow is null`.
- `CheckCase.test_cli_refuses_a_version_1_course_from_every_command` (new): version `1`, saved; for each argv of `check <dir>`, `summary <dir>`, `approve <dir>`, `next <dir>`, `mark <dir> entry-reject building`, `reopen <dir>`, `hub <dir>`: `run_cli` returns `(2, "", course.OLD_VERSION + "\n")`; after the loop `course.json` holds the same bytes and the listing of the directory has no `index.html`.

In `tests/test_course_hub.py`: the listing after `hub` (today `["course.json", "index.html", "lessons"]`) becomes `["course.json", "index.html", "lessons", "map"]`.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -B -m unittest tests.test_course -k schema -k version -k fixture -k temporary -k cleans_up -k reads_course -v`
Expected: the flow and nodes schema tests and the refusal test fail (no line, or `schema: version: must be 1`); the fixture-maps test fails while the maps are missing; the listing tests fail until `map/` exists.

- [ ] **Step 4: Change `course.py`**

- `_check_schema`: `version` must equal `VERSION`; the line reads `schema: version: must be 2`.
- `_check_hop`: `flow` is required; `None` or a string; a string must `FLOW_REF.fullmatch` (the line `must be <source-id>/<flow-id>`). `nodes` is required, a list whose items are strings (one `must be a string` line per item, as `lesson.hops` does); a non-empty list beside `flow` `None` adds `schema: <path>.nodes: must be empty when flow is null`.
- `_load_or_report`: after `load`, a course whose `version` equals `1` writes `OLD_VERSION` and a newline to stderr and returns `None`; each command then exits 2 as for an unreadable file. `load()` does not change: the hub tests call it.
- The docstring: version 2; the prefixes `flow <source>/<flow>:` and `node <source>/<flow>/<id>:` that Task 2 adds; the refusal line.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -B -m unittest tests.test_course tests.test_course_hub -v`
Expected: all `ok` (the hub tests, which copy the fixture, pass on version 2).

- [ ] **Step 6: Commit**

```bash
git add skills/explain/scripts/course.py skills/explain/tests/fixtures/course skills/explain/tests/test_course.py skills/explain/tests/test_course_hub.py
git commit -m "feat: explain: course.json version 2 carries flow and nodes on a hop; course.py refuses version 1"
```

---

### Task 2: `course.py check` binds each hop to its flow and enforces the flow floor and the node floor; `summary` shows them

**Files:**
- Modify: `scripts/course.py` (`_map_flows`, `_named`, `_check_flows`, `check`, `_summary_hops`)
- Modify: `tests/test_course.py` (`CheckCase`, `SummaryCase`)

**Interfaces:**
- Consumes: Task 1's fixture and constants; `onboard.read_map`, `onboard.flow_nodes(doc: MapDoc) -> dict[str, list[str]]`, `onboard.OnboardError` (wave 2).
- Produces:
  ```python
  # scripts/course.py
  NAME_TOKEN = re.compile(r"[a-z0-9][a-z0-9_/-]*")
  def _map_flows(course_dir, source_id) -> dict[str, list[str]]   # {} for a missing or unreadable map
  def _named(not_covered, name) -> bool                            # whole-token match over the sentences
  def _check_flows(course_dir, course) -> list[str]                # the lines of Global Constraints
  ```

- [ ] **Step 1: Write the failing tests**

`CheckCase`, each through `self.only(...)` with the exact lines in order; a test that edits `map/svc-a.md` edits the copy under `self.dir`:
- `test_code_hop_needs_a_flow`: receive `flow = None, nodes = []` → `hop receive: flow missing`, then `node svc-a/receive/listen: in no hop and not in not_covered`.
- `test_docs_hop_may_have_no_flow`: deliver `flow = None, nodes = []`, and `not_covered` gains the sentence ``The send call `svc-a/receive/send` is in the docs of the target.`` → no failure.
- `test_hop_flow_not_in_map`: receive `flow = "svc-a/missing"` → `hop receive: flow svc-a/missing not in map/svc-a.md`, then the `node …/listen` line.
- `test_hop_flow_of_an_unknown_source`: receive `flow = "nope/receive"` → `hop receive: flow nope/receive not in map/nope.md`, then the `node …/listen` line.
- `test_hop_nodes_empty`: receive `nodes = []` → `hop receive: nodes empty`, then the `node …/listen` line.
- `test_hop_node_not_in_flow`: receive `nodes = ["listen", "bogus"]` → `hop receive: node bogus not in flow svc-a/receive`.
- `test_flow_in_no_hop_and_not_in_not_covered`: append to `map/svc-a.md`, under `Flows`, a flow `admin`: the heading `### admin: What does the admin call do?`, a `flowchart TD` of `ping[GET /admin] --> pong[200 ok]`, two node fact lines → `flow svc-a/admin: in no hop and not in not_covered`.
- `test_flow_named_in_not_covered`: the same append; `not_covered` gains ``The admin flow `svc-a/admin` reads no message.`` → no failure.
- `test_flow_name_is_a_whole_token`: the same append; a sentence that names `svc-a/admin-ui` leaves the `flow svc-a/admin` line; a sentence that ends `` …`svc-a/admin`. `` and one that ends `… svc-a/admin.` (no backticks) each remove it.
- `test_node_in_no_hop_and_not_in_not_covered`: deliver `flow = None, nodes = []` → `node svc-a/receive/send: in no hop and not in not_covered`.
- `test_missing_map_has_no_flows`: remove `map/svc-a.md` → `hop receive: flow svc-a/receive not in map/svc-a.md`, the same line for `validate`, `reject` and `deliver`, nothing else.
- `test_unreadable_map_has_no_flows`: overwrite `map/svc-a.md` with `nonsense\n` → the same four lines.
- `test_old_six_section_map_has_no_flows`: overwrite it with a map of the old six titles (`# Map: svc-a`, then `## Entry points`, `## In and out`, `## Formats and transforms`, `## Routing config`, `## Error paths`, `## Other systems`, each `- none found`) → the same four lines.
- `test_fixture_is_clean` stays and stays `course: ok`.

`SummaryCase`:
- `test_summary_hop_line_shows_the_flow_and_the_node_count` (new): the summary holds `receive  source system → svc-a  (code, flow svc-a/receive, 1 nodes)`, `reject  svc-a → source system  (code, flow svc-a/receive, 1 nodes, fails at validate)` and `confirm  target → svc-a  (inferred)`.
- `test_summary_indents_a_failure_hop_under_its_branch_hop`: the assertion `"(code)" in by_hop["receive"]` becomes `"(code, flow svc-a/receive"`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -B -m unittest tests.test_course -k flow -k node -k map_has -k summary_hop_line -k indents -v`
Expected: each new `CheckCase` test fails with `[] != [...]` (no line yet), the two positive tests pass, the summary tests fail on the old evidence text.

- [ ] **Step 3: Implement `_map_flows`, `_named`, `_check_flows` and the summary text in `scripts/course.py`**

- `_map_flows(course_dir, source_id)`: `onboard.flow_nodes(onboard.read_map(<course_dir>/map/<source_id>.md))`; an `onboard.OnboardError` or an `OSError` gives `{}`.
- `_named(not_covered, name)`: `NAME_TOKEN.findall` over each string of `not_covered` (other items skipped); true when one token equals `name`.
- `_check_flows(course_dir, course)`: the hops with a string `id`, `flow` `None` or a string that `FLOW_REF.fullmatch`, and `nodes` a list of strings (every other hop is skipped: the schema lines cover it); the maps read once per source id, and once more for a source id that a hop names and `sources` does not list; the lines in the order of Global Constraints.
- `check()`: `failures += _check_flows(course_dir, course)` after `_check_hops`.
- `_summary_hops.show`: the evidence text of Global Constraints (`<evidence>, flow <flow>, <n> nodes`, then `, fails at <branch>` for a branch hop).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -B -m unittest tests.test_course -v`
Expected: all `ok`.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/course.py skills/explain/tests/test_course.py
git commit -m "feat: explain: course.py check binds a hop to its flow and enforces the flow floor and the node floor; summary shows them"
```

---

### Task 3: `map-task.md` follows the onboarding rules; the orchestrator checks each map

**Files:**
- Modify: `course/map-task.md` (rewrite), `rungs/course.md` ("Map the sources", "Output directory")
- Modify: `tests/test_course_prompts.py`

**Interfaces:**
- Consumes: `rungs/onboard.md` sections "Explore the service" and "The map" (wave 3; its titles are pinned by `OnboardRungCase`); `onboard.TITLES`; the helpers `read`, `section`, `lint` of `test_rung_drift.py` and `fenced_blocks`, `squash` of `test_lesson_prompts.py`.
- Produces:
  ```python
  # tests/test_course_prompts.py
  ONBOARD_MD = EXPLAIN / "rungs" / "onboard.md"
  MAP_SECTIONS = ("Shape", "Architecture", "Entry points", "Flows", "State", "Formats and transforms",
                  "Routing config", "Error paths", "Other systems", "Not covered")   # == onboard.TITLES
  MAP_RUNG_SECTIONS = ("Explore the service", "The map")
  MAP_COMMANDS = (<the inventory command>, <the check command>)   # the two of Global Constraints, verbatim
  MAP_TEXTS = (...)        # the sentences of Step 1
  MAP_RUNG_TEXTS = (...)   # the sentences of Step 1
  ```

- [ ] **Step 1: Write the failing tests**

- Replace `test_map_task_names_the_six_sections` with `test_map_task_points_at_the_onboard_rung`: `MAP_SECTIONS == onboard.TITLES` and `"Other systems" in MAP_SECTIONS` (discovery reads that title); the prompt holds `{skill_dir}/rungs/onboard.md` and each title of `MAP_RUNG_SECTIONS` in double quotes; `section(read(ONBOARD_MD), title)` raises nothing for each; no line of a fenced block of the prompt starts with `## ` (the skeleton lives in the rung); the fenced blocks of the prompt are exactly `MAP_COMMANDS`, one line each, in that order.
- `test_map_task_holds_the_course_overrides` (new): each of `MAP_TEXTS` is in `squash(prompt(MAP))`:
  - "Write two files: `{course_dir}/map/{source_id}.md` and `{course_dir}/map/{source_id}.inventory.txt`."
  - "The first line of the map is `# Map: {source_id}`."
  - "`<service-dir>` is `{source_path}`."
  - "`<root>` is `{root}`."
  - "Run the inventory first and the check last."
  - "Fix the map for each failure line, and run the check again, until it prints `onboard: ok`."
  - "Stop after 3 rounds in which the same failure lines come back."
  - "If failure lines remain, end with `map: done` all the same. Write each failure line before it."
  - "Write `none found` under `Architecture`, `Flows` and `State` when the source has no code to trace."
  - "`<n>` counts the fact lines of the map, the node lines included."
- `test_rung_checks_each_map` (`CourseRungCase`, new): the fenced blocks of `section(self.text, "Map the sources")` hold the orchestrator's check command of Global Constraints as one line; each of `MAP_RUNG_TEXTS` is in `squash(self.text)`:
  - "The prompt points at \"Explore the service\" and \"The map\" of `<skill-dir>/rungs/onboard.md`."
  - "Each subagent writes `map/<source-id>.md` and `map/<source-id>.inventory.txt` in `<course-dir>`."
  - "Print each failure line that it writes."
  - "A map with failures still counts as a map: it is an input, not the artifact."
  - "Only a map that the check cannot read (`map: cannot read`) counts as `map: failed`."
  - "A map whose `Flows` is `none found` is a map."
  - "| `map/<source-id>.inventory.txt` |"
- The module docstring names the ten sections and the pointer instead of "six sections of spec step 9.2". `test_placeholders_are_exactly_the_named_set`, `test_result_lines_present`, `test_prompts_lint_clean`, `test_rung_holds_the_fixes_of_the_review` (its sentence "A `map: done` line with no readable …" stays in the rung) and `test_rung_lints_clean` run on the new text unchanged.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -B -m unittest tests.test_course_prompts -k map_task -k checks_each_map -v`
Expected: the three tests fail on the old prompt and rung text.

- [ ] **Step 3: Rewrite `course/map-task.md` and edit `rungs/course.md`**

`map-task.md`, about 45 lines, these sections: "Your task" (one map of a course; the course follows one message through several services; the id, the path, the root; the two files, with the directory made when missing; write no other file); "What to follow" (follow "Explore the service" and then "The map" of `{skill_dir}/rungs/onboard.md`, with these overrides as a list: `<service-dir>`, `<root>`, the map file and the inventory file in place of `map.md` and `inventory.txt`, the first line of the map, the two commands each in a fenced block, the docs-source sentence, the language `{lang}` with code names in backticks in the two languages, one short sentence per fact and the map for the orchestrator); "Check" (the inventory first and the check last, the fix loop, the stop rule, the ending with failure lines); "Result" (the two result lines as today, `<n>` as the sentence of `MAP_TEXTS`). The template sentence of the first paragraph ("This is a template. The orchestrator fills each name in braces …") stays.

`rungs/course.md` "Map the sources": the sentences of `MAP_RUNG_TEXTS` in this order: the pointer sentence after the prompt sentence; the two files; after "Wait for all the map subagents." a step that runs the check command (fenced) on each map and prints its failure lines, then the three sentences on which map counts. "Output directory": the row `| `map/<source-id>.inventory.txt` | The entry points of one source, from `onboard.py inventory`. |` after the `map/<source-id>.md` row.

- [ ] **Step 4: Lint, then run the tests to verify they pass**

Run (repository root): `python3 skills/ste/scripts/ste_lint.py skills/explain/course/map-task.md` and the same for `skills/explain/rungs/course.md`
Expected: `0 errors, 0 warnings` for each (fix each named line until it is).

Run: `python3 -B -m unittest tests.test_course_prompts -v`
Expected: all `ok`.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/course/map-task.md skills/explain/rungs/course.md skills/explain/tests/test_course_prompts.py
git commit -m "feat: explain: map-task.md follows the onboarding rules of rungs/onboard.md; the course checks each map"
```

---

### Task 4: `course.md` plans from the flows; `lesson-task.md` cuts its first diagram from the map; the full suite

**Files:**
- Modify: `rungs/course.md` ("Plan the course", "Check and stop", "Resume"), `course/lesson-task.md` ("Your task", "Scope")
- Modify: `tests/test_course_prompts.py` (`LESSON_OVERRIDES`, `FLOW_TEXTS`, one new test)

**Interfaces:**
- Consumes: the failure lines and `course.OLD_VERSION` of Tasks 1 and 2; Task 3's test module.
- Produces: the texts pinned in Step 1; nothing a later wave imports.

- [ ] **Step 1: Write the failing tests**

- `LESSON_OVERRIDES` gains these sentences (`test_lesson_task_names_the_overrides` checks them with `squash`):
  - "Each hop has a `flow`, `<source-id>/<flow-id>`, and the `nodes` of that flow that it covers."
  - "The flow is the block under `### <flow-id>:` in `{course_dir}/map/<source-id>.md`."
  - "The first diagram of the lesson uses the Mermaid pattern of `{skill_dir}/rungs/page.md`."
  - "Cut its text from the map block of the flow by the `nodes` of the hops of the lesson."
  - "Keep each line of the block whose node ids are all in that set."
  - "Keep each edge that leaves the set. Its far node stays as one node, and its label names the lesson that covers it, by its question."
  - "Redraw nothing."
  - "Write the text to `diagrams/<flow-id>.mmd` in your output directory."
  - "Each decision node of that diagram gets one paragraph that names its branches, or a section of its own."
  - "A moving part is a hop, not a node."
  - "If the hops of your lesson come from two flows, make one figure for each flow, the flow of the first hop first."
- `FLOW_TEXTS` (new) and `test_rung_plans_from_the_flows` (`CourseRungCase`, new): each in `squash(self.text)`:
  - `"version": 2`, `"flow": "esb/request"`, `"nodes": ["listen", "parse"]`
  - "`flow`: the flow that the hop comes from, as `<source-id>/<flow-id>`."
  - "The flow is a `### <flow-id>:` heading under `Flows` in `map/<source-id>.md`."
  - "A `code` hop has a flow. A `docs` hop has a flow or `null`. An `inferred` hop has `null`."
  - "`nodes`: the nodes of that flow that the hop covers, in the order of the flow."
  - "The list is not empty when `flow` is a string. It is `[]` when `flow` is `null`."
  - "Read the `Flows` of each map. The flows that carry the message of the course give the hops."
  - "Walk the nodes of such a flow in their order."
  - "A decision node with an edge to an error exit gives a `branch` hop."
  - "A decision node that splits the main path gives one hop for each edge, and `what` names the condition."
  - "A flow that some hop names is a followed flow."
  - "`<source-id>/<flow-id>/<node-id>`"
  - "Thus a node leaves the course only by name."
  - "A sentence can name several flows or nodes."
  - "A lesson holds the hops of one flow, or of two flows that meet at one node."
  - "its `flow` and its `nodes` against `map/<source-id>.md`"
  - "| `flow <source>/<flow>:` |", "| `node <source>/<flow>/<id>:` |"
  - `course.OLD_VERSION` (the table row and the Resume sentence both hold it; assert it twice with `count`), and "cannot resume"
  - and `"version": 1` is not in the rung.
- `test_rung_names_every_placeholder` and `test_rung_verify_block_matches_lesson_lines` keep passing.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -B -m unittest tests.test_course_prompts -k overrides -k plans_from -v`
Expected: both fail on the old text.

- [ ] **Step 3: Edit `course/lesson-task.md` and `rungs/course.md`**

`lesson-task.md`: under "Your task", after the `branch` sentence, the two hop sentences. Under "Scope", after the neighbour-hop paragraph, a paragraph "The first diagram" with the cut rule in prose, in the order of `LESSON_OVERRIDES`: the pattern, the cut, the kept lines, the kept edges, no redraw, the file, the inline run (`python3 {skill_dir}/scripts/mermaid_svg.py inline index.html`, as the pattern of `page.md` says), the decision paragraphs, the moving part, the two-flow case. No fenced Mermaid example (Global Constraints).

`rungs/course.md` "Plan the course": the JSON example becomes version 2 with the hop `"flow": "esb/request", "nodes": ["listen", "parse"]` and a `not_covered` sentence that names a flow by id; the field rules gain `flow` and `nodes` after `cites`; a list "Plan from the flows" after the field rules with the planning rules of `FLOW_TEXTS` (spec 11); the `lessons` rule gains the one-flow-or-two sentence. "Check and stop": the `hop <id>:` row gains "or its `flow` and its `nodes` against `map/<source-id>.md`"; new rows `| `flow <source>/<flow>:` | Put the flow on a hop, or name it in `not_covered`. |`, `| `node <source>/<flow>/<id>:` | Put the node in the `nodes` of a hop, or name it in `not_covered`. |` and `| `course: version 1 is older than this skill; start a new course` | The course is from an older skill. Start a new course. `course.py` exits with 2. |` before the `course: cannot read` row. "Resume": one sentence after the first paragraph: a `course.json` of version 1 cannot resume, each command prints `course.OLD_VERSION`, start a new course.

- [ ] **Step 4: Lint, then run the scoped tests**

Run (repository root): `python3 skills/ste/scripts/ste_lint.py skills/explain/course/lesson-task.md` and the same for `skills/explain/rungs/course.md`
Expected: `0 errors, 0 warnings` for each.

Run: `python3 -B -m unittest tests.test_course_prompts tests.test_rung_drift -v`
Expected: all `ok`.

- [ ] **Step 5: Run the full suite**

Run (from `skills/explain/`): `python3 -B -m unittest discover -s tests`
Expected: the last line `OK (skipped=46)` and the count above 1393 (the base ran 1393 tests in about nine minutes); then `ps -axo command | grep -c '[h]eadless=new'` prints `0`.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/course/lesson-task.md skills/explain/rungs/course.md skills/explain/tests/test_course_prompts.py
git commit -m "feat: explain: the course plans from the flows of its maps; the lesson cuts its first diagram by the nodes of its hops"
```
