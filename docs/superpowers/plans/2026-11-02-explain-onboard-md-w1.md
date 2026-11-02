# explain onboard: wave onboard-puml (the map speaks PlantUML) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A map written in PlantUML passes `onboard.py check --notation plantuml`, splits into `.puml` files with `onboard.py diagrams`, and renders to PNGs with `puml.py render`, while every Mermaid map keeps passing.

**Architecture:** A new module `scripts/puml.py` parses a `plantuml` fence into its kind (activity, component, state), its nodes and its faults, and holds the `render` command. `scripts/onboard.py` dispatches a fence by its info string (`mermaid` to the parser it has, `plantuml` to `puml.parse`), carries the notation and the parser's faults on `Diagram`, and takes `--notation`. A new module `scripts/onboard_page.py` holds the `diagrams` command (the `page` command joins it in wave two). The rung text does not change in this wave: without `--notation` both notations pass, so the branch stays consistent.

**Tech Stack:** Python 3 standard library (`re`, `subprocess`, `argparse`, `unittest`); PlantUML 1.2026.9 from Homebrew on `PATH` for the render tests only.

**Spec:** `docs/superpowers/specs/2026-11-02-explain-onboard-markdown-design.md`, sections 7, 8 and the `diagrams` half of 9. Wave map: `docs/superpowers/waves/2026-11-02-explain-onboard-md.yaml`, wave `onboard-puml`.

## Global Constraints

- Tests run with `cd skills/explain && python3 -B -m unittest discover -s tests`; a test that needs `plantuml` skips with the message `plantuml missing` (spec 8).
- New code lives in `scripts/puml.py` and `scripts/onboard_page.py`; `scripts/onboard.py` gains only the dispatch, the notation flag and the `_key` rule (br kp-xc77 already flags its length).
- `onboard.py` stays one import for `course.py`: `onboard.flow_nodes`, `onboard.read_map`, `onboard.check_map(doc, root)` and `onboard.OnboardError` keep their names and their two-argument call.
- Failure lines keep today's shape: `diagram <where>: <fault>`, `node <where>/<key>: <fault>`, `fact <where>/<key>: <fault>`; `<where>` is `architecture`, the flow id or `state`.
- Fence lines are numbered from 1 inside the fence; the `@startuml` wrapper is not a fence line.
- The fixed render style is exactly `-tpng -charset UTF-8 -o <abs dir> -Sdpi=144 -SbackgroundColor=white -Sshadowing=false -SdefaultFontSize=14` (spec 8).
- A plan task commits on its own: `git add <files> && git commit` with a `feat:` or `test:` message that names the rung (`explain onboard: ...`) and ends with the `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` line.

## Review Focus

1. A fence that carries its own `@startuml` / `@enduml` lines (an author pastes a whole file): `diagrams` would double-wrap it and PlantUML would error. The check reports each such line as `diagram <where>: style line <n>` (the wrapper belongs to the file, not the fence). Test in Task 1.
2. A `title`, `hide ...`, `scale ...` or `... direction` line before `start`: the spec tolerates these lines but says the fence starts with `start`. Kind detection skips blank lines, `'` comments and these preamble statements before it reads the first statement. Test in Task 1.
3. A Russian action label with its backtick-keyed fact: the label and the key must match byte for byte with no ASCII assumption. Test in Task 3.
4. An edge label holding an arrow, such as `api --> db : "write -> row"`: the label after the first ` : ` is cut before the arrow is read, so no false node appears. Test in Task 2.
5. `puml.py render <dir>` with a relative directory: PlantUML resolves a relative `-o` against each source file, so the script passes the absolute path and the PNGs land beside the `.puml` files. Test in Task 7.

---

### Task 1: `puml.py` kind detection and the activity parser

**Files:**
- Create: `skills/explain/scripts/puml.py`
- Create: `skills/explain/tests/fixtures/onboard/parser-activity.puml`
- Create: `skills/explain/tests/test_puml.py`

**Interfaces:**
- Consumes: nothing.
- Produces:

```python
KINDS = ("activity", "component", "state")
STYLE_LINES = ("skinparam", "!pragma", "!include", "<style>", "split", "backward:", "@startuml", "@enduml")  # plus a colour prefix such as `#pink:`

class Parsed(NamedTuple):
    kind: str | None          # one of KINDS, or None
    nodes: list[str]          # distinct, in order of first appearance
    faults: list[str]         # diagram faults without the `diagram <where>: ` prefix
    node_faults: list[tuple[str, str]]  # (node, fault) without the `node <where>/` prefix
    hops: list[str]           # the <flow-id> of each `:see <flow-id>;` action

def kind(block: str) -> str | None
def parse(block: str) -> Parsed
```

Behavior contract of the activity form (spec 7.2):

- `kind` returns `activity` when the first statement is `start`; blank lines, `'` comments and the preamble statements `title`, `hide`, `scale`, `left to right direction`, `top to bottom direction` are skipped before it. State and component detection are Task 2; until then `kind` returns `None` for everything else.
- A node is the label of each action (`:<label>;`, label stripped) and the condition of each `if (<c>) then (...)`, `elseif (<c>) then (...)`, `while (<c>) is (...)`, `repeat while (<c>) is (...)` and `switch (<c>)` line. An outcome in `then (...)`, `is (...)`, `else (...)`, `case (...)`, `endwhile (...)` is not a node. The same label twice is one node (spec call 12).
- A `:` line without `;` on the same line is the fault `action over lines <n>-<m>`, `<m>` the fence line of the next `;` or the last fence line; its text is not a node.
- A line that starts with one of `STYLE_LINES` or matches a colour prefix (`#<word>:`) is the fault `style line <n>`.
- An action `:see <flow-id>;` is a node with its label `see <flow-id>` and adds `<flow-id>` to `hops`.
- A label that holds a backtick is the node fault `(label, "bad id")`.
- `start`, `stop`, `end`, `kill`, `detach`, `fork`, `fork again`, `end fork`, `endif`, `else`, `endwhile`, `endswitch`, `repeat`, `partition ... {`, `}`, `-> label;`, `note` lines and any unknown line are ignored (spec call 11).

- [ ] **Step 1: Write the fixture and the failing tests**

`parser-activity.puml`: one activity diagram with every allowed construct of spec 7.2 (a preamble `title`, actions, `if`/`elseif`/`else`/`endif`, `while`/`endwhile`, `repeat`/`repeat while`, `switch`/`case`/`endswitch`, `fork`, `partition`, an edge label `-> ok;`, a `note` line, a `'` comment, one label used twice, `:see other;` + `detach`, an error exit `stop`).

Tests in `test_puml.py`, class `ActivityCase`:

- `test_kind_is_activity_after_a_title_line`: `puml.kind(fixture) == "activity"`.
- `test_nodes_are_the_distinct_labels_and_conditions_in_order`: `puml.parse(fixture).nodes` equals the expected list written in the test; the repeated label appears once.
- `test_outcomes_are_not_nodes`: no `yes`, `no` or case outcome in `nodes`.
- `test_see_action_is_a_node_and_a_hop`: `"see other" in nodes` and `hops == ["other"]`.
- `test_action_over_two_lines_is_a_fault`: a block with `:a long` / `label;` yields `faults == ["action over lines 3-4"]` (lines as planted) and no node for it.
- `test_style_lines_are_faults`: a block with `skinparam ...`, `#pink:x;`, `split`, `backward:x;`, `!include x`, `<style>` yields one `style line <n>` per line.
- `test_startuml_lines_are_style_faults`: a block wrapped in `@startuml`/`@enduml` yields two `style line` faults (Review Focus 1).
- `test_backtick_label_is_a_bad_id`: `node_faults == [("a `b`", "bad id")]`.
- `test_unknown_lines_are_ignored`: a `legend`, `hide empty description` and `left to right direction` line add no node and no fault.
- `test_kind_is_none_without_start`: a block of only actions gives `kind(block) is None`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_puml -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'puml'`.

- [ ] **Step 3: Implement `kind` and `parse` for the activity form in `scripts/puml.py`**

Module docstring names spec sections 7 and 8. One pass over the fence lines with their 1-based numbers; the regexes are the builder's (spec 15).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_puml -v`
Expected: PASS, every test of `ActivityCase`.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/puml.py skills/explain/tests/test_puml.py skills/explain/tests/fixtures/onboard/parser-activity.puml
git commit -m "feat: explain onboard: puml.py reads the activity form of a PlantUML fence"
```

---

### Task 2: `puml.py` component and state parsers

**Files:**
- Modify: `skills/explain/scripts/puml.py`
- Create: `skills/explain/tests/fixtures/onboard/parser-component.puml`, `skills/explain/tests/fixtures/onboard/parser-state.puml`
- Modify: `skills/explain/tests/test_puml.py`

**Interfaces:**
- Consumes: `Parsed`, `kind`, `parse` of Task 1.
- Produces: the same functions, now returning `component` and `state` kinds;

```python
COMPONENT_ID = re.compile(r"[a-z][a-z0-9_]*")
STATE_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
PARTS = ("component", "queue", "database", "cloud", "node", "rectangle", "interface", "actor")
```

Behavior contract (spec 7.3, 7.4, call 11):

- `kind` is `state` when any line starts with `[*]` or `state `; else `component` when any line declares a part (`<part> "<name>" as <id>` with `<part>` in `PARTS`, or `[<name>] as <id>`) or draws an edge between two ids; else `None`. Activity detection of Task 1 comes first.
- Component nodes: each declared alias in declaration order, then each edge endpoint not yet seen. An edge is any line that holds a PlantUML arrow (`->`, `-->`, `..>`, `.>`, a hyphen or dot run with an optional `[style]` or direction word such as `-left->`, `-[hidden]->`), after the text from the first ` : ` on is cut. An endpoint `[<name>]` resolves to the alias declared for that name; without a declaration it is the node `<name>` with the node fault `not declared`. An alias on an edge without a declaration is the node fault `not declared`. A declared alias outside `COMPONENT_ID` is the node fault `bad id`. `package "<name>" {`, `}` and unknown lines are ignored.
- State nodes: each declared state (`state "<label>" as <ID>`, `state <ID> {`, `state <ID>`) and each id on either side of an arrow of any form, never `[*]`, in order of first appearance; the text from the first ` : ` on is cut before the arrow is read. An id outside `STATE_ID` is the node fault `bad id`. `note` lines, `}` and unknown lines are ignored.
- `faults` of both forms: the `style line <n>` rule of Task 1 applies; `action over lines` does not.

- [ ] **Step 1: Write the fixtures and the failing tests**

`parser-component.puml`: a component diagram with every part keyword of `PARTS`, a `[Name] as id` form, a `package`, edges of `-->`, `->`, `..>`, `-left->` and `-[hidden]->`, an edge label, and an edge whose label holds `->` in quotes. `parser-state.puml`: a state diagram with `[*]` in and out, labelled transitions, `state "x" as Held`, a composite `state Shipped { ... }`, a `note` line and a `-left->` arrow.

Tests, class `ComponentCase`:

- `test_kind_is_component`: `kind(fixture) == "component"`.
- `test_nodes_are_aliases_then_edge_ids`: `parse(fixture).nodes` equals the expected list.
- `test_bracket_endpoint_resolves_to_its_alias`: an edge `[Order API] --> db` with `[Order API] as api` declared adds no node beyond `api`.
- `test_edge_label_with_an_arrow_adds_no_node`: Review Focus 4.
- `test_undeclared_edge_id_is_a_fault`: `("cache", "not declared") in node_faults` and `"cache" in nodes`.
- `test_hyphen_alias_is_a_bad_id`: `("my-db", "bad id") in node_faults`.
- `test_package_lines_are_not_nodes`.

Class `StateCase`:

- `test_kind_is_state`, `test_nodes_are_declared_and_arrow_ids_without_star`, `test_transition_label_is_cut_before_the_arrow` (`A --> B : goes -> C` gives no `C`), `test_bad_state_id_is_a_fault` (`("new-order", "bad id")`), `test_note_lines_are_ignored`.

Class `KindCase`: `test_kind_order_is_activity_state_component` (a block with `start` and `[*]` is `activity`; a block with `state X` and an edge is `state`), `test_plain_text_has_no_kind`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_puml -v`
Expected: FAIL, the new classes (`kind` returns `None`, `nodes` empty).

- [ ] **Step 3: Implement the two forms in `scripts/puml.py`**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_puml -v`
Expected: PASS, all classes.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/puml.py skills/explain/tests/test_puml.py skills/explain/tests/fixtures/onboard/parser-component.puml skills/explain/tests/fixtures/onboard/parser-state.puml
git commit -m "feat: explain onboard: puml.py reads the component and state forms"
```

---

### Task 3: PlantUML fences in the map: dispatch, kind by place, backtick keys, the fixture map

**Files:**
- Modify: `skills/explain/scripts/onboard.py` (`Diagram` at 158, `_close_fence` at 218, `_places` at 515, `_key` at 528, `_place_lines` at 553)
- Create: `skills/explain/tests/fixtures/onboard/map-puml.md`
- Modify: `skills/explain/tests/test_onboard.py`

**Interfaces:**
- Consumes: `puml.parse`, `puml.Parsed` of Tasks 1 and 2.
- Produces:

```python
MERMAID = "mermaid"
PLANTUML = "plantuml"
NOTATIONS = (PLANTUML, MERMAID)
NEEDS = {"architecture": {MERMAID: FLOWCHART, PLANTUML: "component"},
         "flow": {MERMAID: FLOWCHART, PLANTUML: "activity"},
         "state": {MERMAID: STATE, PLANTUML: "state"}}

class Diagram(NamedTuple):
    line: int
    kind: str | None
    nodes: list[str]
    text: str
    notation: str = MERMAID
    faults: tuple[str, ...] = ()              # puml.Parsed.faults; empty for Mermaid
    node_faults: tuple[tuple[str, str], ...] = ()
    hops: tuple[str, ...] = ()

def _places(doc: MapDoc) -> list[tuple[str, Section | Flow, dict[str, str]]]  # needs by notation
```

Behavior contract (spec 7.1, 7.5, call 12):

- `_close_fence` makes a `Diagram` from a `plantuml` fence as it does from a `mermaid` one, with `notation=PLANTUML` and the parse results; other info strings are dropped as today.
- `_place_lines` reads the needed kind by `diagram.notation`. A `plantuml` diagram of kind `None` is `diagram <where>: not a PlantUML kind`; a wrong kind is `diagram <where>: not activity`, `not component` or `not state`; the Mermaid wording stays as it is.
- `_key`: a fact whose text starts with a backtick is keyed by the text up to the closing backtick; the two rules of today follow for every other fact.
- The 25-node line applies to `FLOWCHART` and `activity` diagrams.
- `flow_nodes` is unchanged and returns the labels of a PlantUML flow.

`map-puml.md`: the map of `tests/fixtures/onboard/tree` in PlantUML, with the facts of `map.md` carried over: the architecture as a component diagram (a `package shop`, `component`/`database`/`queue`/`cloud` parts, every alias of `map.md`), the `order` flow as an activity diagram where `400 over the limit` is drawn twice (over the limit, and declined after the charge), the `cancel` flow with `:see order;` + `detach`, the state as a state diagram. Every activity node has a fact keyed by its label in backticks, with a cite into `tree` that `cite_check` accepts.

- [ ] **Step 1: Write the fixture and the failing tests**

Tests in `test_onboard.py`, class `PlantumlMapCase` (helpers `check`, `failures`, `replace_once` of the file; a module constant `MAP_PUML = read("map-puml.md")`):

- `test_fixture_map_passes_the_check`: `check(MAP_PUML) == OK`.
- `test_plantuml_fence_becomes_a_diagram`: `parse_map(MAP_PUML).section("Architecture").diagrams[0].notation == "plantuml"` and its `kind == "component"`.
- `test_backtick_key_is_the_label`: `onboard._key(Fact(1, 1, "`see order`: the row is saved", None)) == "see order"`.
- `test_russian_label_matches_its_fact`: an order flow edited to `:принять заказ;` with its fact `` - `принять заказ`: ... `` still passes (Review Focus 3).
- `test_activity_in_architecture_is_not_component`: the architecture fence replaced by the order flow's fence gives `diagram architecture: not component`.
- `test_component_in_a_flow_is_not_activity`: `diagram order: not activity`.
- `test_state_place_needs_a_state_diagram`: `diagram state: not state`.
- `test_plain_text_fence_is_not_a_plantuml_kind`: a `plantuml` fence holding one word gives `diagram architecture: not a PlantUML kind`.
- `test_repeated_label_is_one_node_with_one_fact`: the fixture's twice-drawn label passes; a second fact for it is `fact order/400 over the limit: two lines`.
- `test_twenty_six_labels_are_too_many`: a flow of 26 distinct actions gives `diagram order: 26 nodes, more than 25`.
- `test_mermaid_fixture_still_passes`: `check(MAP) == OK` (regression lock).
- `test_flow_nodes_returns_labels`: `flow_nodes(parse_map(MAP_PUML))["cancel"]` holds `"see order"`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard.PlantumlMapCase -v`
Expected: FAIL; `test_fixture_map_passes_the_check` prints `diagram architecture: none` and `fact` lines.

- [ ] **Step 3: Implement the dispatch, the kinds by place and the key rule in `scripts/onboard.py`**

`import puml` beside `import cite_check`. The `Diagram` defaults keep the single constructor call of `_close_fence` the only one.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard tests.test_course -v`
Expected: PASS; `test_course` still passes on its Mermaid fixture maps.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/onboard.py skills/explain/tests/test_onboard.py skills/explain/tests/fixtures/onboard/map-puml.md
git commit -m "feat: explain onboard: the map check reads PlantUML fences by place and keys a fact by its backtick label"
```

---

### Task 4: the node faults of the PlantUML forms in the check

**Files:**
- Modify: `skills/explain/scripts/onboard.py` (`_node_lines` at 536, `_place_lines` at 553, `check_map` at 796)
- Modify: `skills/explain/tests/test_onboard.py`

**Interfaces:**
- Consumes: `Diagram.faults`, `Diagram.node_faults`, `Diagram.hops` of Task 3.
- Produces: `_place_lines(where, scope, needs, flow_ids: set[str]) -> list[str]`; `check_map` passes the set of flow ids of `Flows`.

Behavior contract (spec 7.5), in this output order inside one place: the `diagram <where>: <fault>` lines of `Diagram.faults` (`action over lines <n>-<m>`, `style line <n>`), then the `node` lines in diagram order where each node prints its parser fault (`node <where>/<id>: not declared`, `node <where>/<id>: bad id`) before `no fact line`, then `node <where>/<label>: flow <id> not in Flows` for each hop whose id is no flow id, then the `fact` lines as today. The Mermaid `bad id` rule of `_node_lines` stays for `FLOWCHART`.

- [ ] **Step 1: Write the failing tests**

Class `PlantumlFaultCase` in `test_onboard.py`, each from `MAP_PUML` with one planted edit:

- `test_action_over_lines`: `diagram order: action over lines <n>-<m>` with the planted numbers.
- `test_style_line`: a `skinparam` line in the architecture fence gives `diagram architecture: style line <n>`.
- `test_see_of_an_unknown_flow`: `:see refund;` gives `node cancel/see refund: flow refund not in Flows`.
- `test_undeclared_component_on_an_edge`: `node architecture/cache: not declared`.
- `test_hyphen_component_alias_is_a_bad_id`: `node architecture/my-db: bad id`.
- `test_bad_state_id`: `node state/new-order: bad id`.
- `test_fault_order_is_diagram_then_node_then_fact`: a fence with a style line and an undeclared id lists the `diagram` line before the `node` line.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard.PlantumlFaultCase -v`
Expected: FAIL, the new lines are missing from the output.

- [ ] **Step 3: Implement the fault lines in `scripts/onboard.py`**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/onboard.py skills/explain/tests/test_onboard.py
git commit -m "feat: explain onboard: the check reports the faults of a PlantUML diagram and a see hop into no flow"
```

---

### Task 5: `onboard.py check --notation`

**Files:**
- Modify: `skills/explain/scripts/onboard.py` (`USAGE` at 21, `_place_lines`, `check_map` at 796, `cmd_check` at 816)
- Modify: `skills/explain/tests/test_onboard.py`

**Interfaces:**
- Consumes: `NOTATIONS`, `Diagram.notation` of Task 3.
- Produces: `check_map(doc: MapDoc, root: str, inventory: list[str] | None = None, notation: str | None = None) -> list[str]`; the usage line `onboard.py check <map.md> --root <root> [--inventory <file>] [--notation plantuml|mermaid]`.

Behavior contract (spec 7.1): with `notation`, every diagram of every place whose `Diagram.notation` differs is `diagram <where>: not plantuml` or `diagram <where>: not mermaid`, printed in place of that place's other `diagram` and `node` lines (its facts are then not checked against nodes, as a wrong kind does today). Without the flag nothing changes. `--notation` with another value is the usage, exit 2, through `_Parser.error`.

- [ ] **Step 1: Write the failing tests**

Class `NotationCase`, with a `check` call extended by `notation=None` that appends `--notation <value>` to `argv`:

- `test_mermaid_map_passes_as_mermaid`: `check(MAP, notation="mermaid") == OK`.
- `test_mermaid_map_fails_as_plantuml`: `failures(out)` holds `diagram architecture: not plantuml`, `diagram order: not plantuml`, `diagram cancel: not plantuml`, `diagram state: not plantuml` and no `node` or `fact` line.
- `test_plantuml_map_passes_as_plantuml` and `test_plantuml_map_fails_as_mermaid` (`diagram architecture: not mermaid`).
- `test_without_the_flag_both_pass`.
- `test_unknown_notation_is_the_usage`: exit 2, stderr starts with `usage:` and holds `--notation plantuml|mermaid`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard.NotationCase -v`
Expected: FAIL with the usage exit 2 (the option is unknown).

- [ ] **Step 3: Implement the flag**

`cmd_check` adds `--notation` with `choices=NOTATIONS` to the `_Parser` it builds, then passes it to `check_map`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/onboard.py skills/explain/tests/test_onboard.py
git commit -m "feat: explain onboard: check takes --notation plantuml|mermaid"
```

---

### Task 6: `onboard.py diagrams` in `onboard_page.py`

**Files:**
- Create: `skills/explain/scripts/onboard_page.py`
- Modify: `skills/explain/scripts/onboard.py` (`USAGE` at 21, `main` at 832)
- Create: `skills/explain/tests/test_onboard_page.py`

**Interfaces:**
- Consumes: `onboard.read_map`, `onboard.MapDoc`, `onboard.OnboardError`, `onboard._places`, `Diagram.notation` and `Diagram.text`.
- Produces:

```python
# onboard_page.py
def diagram_files(doc: onboard.MapDoc) -> dict[str, str]   # <id> -> file body; raises OnboardError("diagrams: <where>: not plantuml", 1)
def cmd_diagrams(argv: list[str]) -> int                   # onboard.py diagrams <map.md> --out <dir>
```

`onboard.main` resolves `diagrams` to `onboard_page.cmd_diagrams` through an import inside `main` (so `onboard_page` may import `onboard` at module level, as `course.py` does, without a cycle). `USAGE` gains the line `onboard.py diagrams <map.md> --out <dir>`.

Behavior contract (spec 9): `diagram_files` maps `architecture`, `flow-<flow-id>` and `state` to `@startuml\n` + the fence text + `\n@enduml\n` for each place whose first diagram exists; a place with `none found` or no diagram writes nothing; a `mermaid` diagram in a place raises the error. `cmd_diagrams` creates the directory when it is missing, writes each file, prints `diagrams: stale <file>` for each `.puml` of the directory that no id produced (sorted; deleting nothing), then `diagrams: ok <n> files`; exit 0, 1 on the Mermaid error (its line on stdout), 2 when the map cannot be read (`map: cannot read ...` as `check` prints it) or the directory cannot be written (`diagrams: cannot write <dir>: <reason>` on stderr).

- [ ] **Step 1: Write the failing tests**

`test_onboard_page.py` (same `sys.path` and `run` helper pattern as `test_onboard.py`; `run` calls `onboard.main`), class `DiagramsCase`:

- `test_writes_one_file_per_place`: on `map-puml.md`, the directory holds exactly `architecture.puml`, `flow-order.puml`, `flow-cancel.puml`, `state.puml` and stdout ends `diagrams: ok 4 files`.
- `test_file_is_the_fence_wrapped`: `flow-order.puml` text equals `@startuml\n` + the fence text of the map + `\n@enduml\n`.
- `test_none_found_state_writes_no_file`.
- `test_stale_file_is_reported_not_deleted`: a planted `old.puml` gives `diagrams: stale old.puml` before the ok line and still exists.
- `test_mermaid_fence_is_refused`: on `map.md`, exit 1 and stdout `diagrams: architecture: not plantuml`.
- `test_unreadable_map_exits_2`.
- `test_usage_names_diagrams`: `run([])` stderr holds `onboard.py diagrams <map.md> --out <dir>`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard_page -v`
Expected: FAIL (`onboard.py diagrams` is the usage, exit 2).

- [ ] **Step 3: Implement `onboard_page.py` and the dispatch**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard_page tests.test_onboard -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/onboard_page.py skills/explain/scripts/onboard.py skills/explain/tests/test_onboard_page.py
git commit -m "feat: explain onboard: onboard.py diagrams writes each PlantUML fence of the map to its .puml file"
```

---

### Task 7: `puml.py render`

**Files:**
- Modify: `skills/explain/scripts/puml.py`
- Modify: `skills/explain/tests/test_puml.py`

**Interfaces:**
- Consumes: the `.puml` files of Task 6 (any directory of `<id>.puml` files).
- Produces:

```python
STYLE = ("-Sdpi=144", "-SbackgroundColor=white", "-Sshadowing=false", "-SdefaultFontSize=14")
ERROR_LINE = re.compile(r"Error line (\d+) in file: (.+)")

def failed_lines(stderr: str) -> list[tuple[str, int]]   # (id, fence line) per Error line; the wrapper line subtracted
def render(directory: str) -> tuple[list[str], int]       # the output lines and the exit code
def main(argv: list[str]) -> int                          # puml.py render <dir>
```

Behavior contract (spec 8): `render` finds `plantuml` with `shutil.which`; without it the lines are `["plantuml: FAIL plantuml not found"]`, code 2. An empty directory is `plantuml: ok 0 diagrams`, code 0. Otherwise one `subprocess.run` of `plantuml -tpng -charset UTF-8 -o <abspath(directory)> <STYLE...> <sorted .puml files>`, capturing stderr. Lines, in order: `plantuml: FAIL <id> line <n>` per `failed_lines` entry (and the PNG of that id is removed when it exists); `plantuml: FAIL exit <code>` when the process exit code is non-zero and no `Error line` was found; `plantuml: FAIL <id> no png` for each `.puml` without a PNG and without a line failure; `plantuml: ok <n> diagrams` only when no FAIL line was printed. Code 1 when any FAIL line was printed, else 0. `main` prints the lines and returns the code; a wrong command or argument count prints `usage: puml.py render <diagrams-dir>` to stderr, exit 2.

- [ ] **Step 1: Write the failing tests**

In `test_puml.py`: `HAVE_PLANTUML = shutil.which("plantuml") is not None`, skip message `plantuml missing`.

Class `FailedLinesCase` (no PlantUML needed):

- `test_error_line_maps_to_the_fence_line`: `failed_lines("Error line 4 in file: /x/flow-order.puml\nSome diagram description contains errors\n") == [("flow-order", 3)]`.
- `test_no_error_lines`: `failed_lines("") == []`.

Class `RenderCase`:

- `test_missing_plantuml_is_exit_2` (no PlantUML needed): with `shutil.which` patched to return `None`, `render(tmp) == (["plantuml: FAIL plantuml not found"], 2)`.
- `test_cli_usage` (no PlantUML needed): `main([])` returns 2 and prints `usage: puml.py render <diagrams-dir>` to stderr.
- `@unittest.skipUnless(HAVE_PLANTUML, "plantuml missing")` on each of the following: `test_empty_directory_is_ok_0` (`(["plantuml: ok 0 diagrams"], 0)`); `test_renders_the_three_parser_fixtures` (the three `parser-*.puml` copied into a temporary directory and wrapped in `@startuml`/`@enduml` give three PNGs, each starting with the PNG signature bytes, and `plantuml: ok 3 diagrams`, code 0); `test_syntax_error_removes_its_png` (a planted `broken.puml` of `@startuml\nstart\n:unclosed\n@enduml` beside a good one gives `plantuml: FAIL broken line 2` as the first line, no `broken.png`, the good PNG present, code 1, no `ok` line); `test_relative_directory_writes_beside_the_sources` (Review Focus 5: `render` called with a relative path from a changed working directory writes the PNGs into that directory); `test_cli_returns_the_render_code` (`main(["render", tmp])` returns 0 on the good directory).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_puml -v`
Expected: FAIL with `AttributeError: module 'puml' has no attribute 'failed_lines'`.

- [ ] **Step 3: Implement `failed_lines`, `render` and `main` in `scripts/puml.py`**

Match the `<path>` of an `Error line` to its id by `os.path.splitext(os.path.basename(path))[0]`. Add the `if __name__ == "__main__": sys.exit(main(sys.argv[1:]))` footer.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_puml -v`
Expected: PASS, with the render tests run (not skipped) on this machine.

- [ ] **Step 5: Run the wave acceptance and commit**

Run:

```bash
cd skills/explain && python3 -B -m unittest discover -s tests 2>&1 | tail -3
cd skills/explain && python3 scripts/onboard.py check tests/fixtures/onboard/map-puml.md --root tests/fixtures/onboard/tree --notation plantuml
cd skills/explain && rm -rf /tmp/puml-d && python3 scripts/onboard.py diagrams tests/fixtures/onboard/map-puml.md --out /tmp/puml-d && python3 scripts/puml.py render /tmp/puml-d && ls /tmp/puml-d
```

Expected: the suite reports no new failure against the baseline of the branch start (see the wave map); `onboard: ok`; `diagrams: ok 4 files`; `plantuml: ok 4 diagrams`; four `.png` files listed. Read each PNG once with the Read tool: a drawn diagram, not an error picture.

```bash
git add skills/explain/scripts/puml.py skills/explain/tests/test_puml.py
git commit -m "feat: explain onboard: puml.py render draws every .puml of a directory to PNG and removes the picture of a failed diagram"
```
