# Explain — BPMN subjects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A page or lesson about a BPMN subject draws each plane of the `.bpmn` file from the file's own DI, shows every BPMN cite as a readable label generated from the file, and fails `verify.sh` when a plane or sub-process is neither explained nor listed in `Not covered`.

**Architecture:** One stdlib CLI, `scripts/bpmn.py`, with the subcommands `planes`, `svg`, `label` and `check`. It holds the model (one `xml.parsers.expat` pass over the file, which gives the start and end line of every element), the label rule, the page rewrite and the check. The renderer lives in `scripts/bpmn_svg.py`, imported by `bpmn.py`: it is the largest unit and has a single consumer. `verify.sh` runs `bpmn.py check` as its last check. The page template gets the CSS, and the rung documents get the rules.

**Tech Stack:** Python 3 stdlib (`xml.parsers.expat`, `html.parser`, `html`, `re`, `unittest`), bash (`verify.sh`), Markdown (rung files, prompt).

Base: b98360f (main). One cohesive wave, high risk: it changes two contracts that other code reads, the output lines of `verify.sh` and the cite markup.
Test runs: scoped per task; full suite once, in Task 8.

**Spec:** `docs/superpowers/specs/2026-10-06-explain-bpmn-design.md` (approved 2026-10-06). Coverage: not opted in.

## Global Constraints

- Work on the branch `feat/explain-bpmn`, made from `main` at b98360f. Never commit to `main`. Never stage or commit `.beads/`.
- Run every test command from `skills/explain`, as `python3 -B -m unittest tests.<module>`. Run each command that takes more than 2 minutes (the full suite, `test_verify`, `test_page_template`, `test_lesson_e2e`) with its output in a log file. Poll the log with short `sleep 30; tail` calls until `OK` or `FAILED`. Never end a turn to wait for a notification.
- System `python3`, stdlib only. No npm, no pip, no bpmn-js.
- SVG text: 14 units, never less. 1 DI unit = 1 px. A plane's `viewBox` is the bounding box of its shapes, edges and labels plus a margin of 20 units on each side.
- Names are copied verbatim from `name=` (Russian stays Russian). Convention 2 still applies: a password, token or key never goes into a snippet, a label or the prose.
- Output of `bpmn.py svg` and `bpmn.py label` is deterministic: the same input gives byte-equal output.
- `rungs/page.md`, `rungs/lesson.md` and `SKILL.md` pass `skills/ste/scripts/ste_lint.py` with `0 errors, 0 warnings`, as they do at base.
- Exit codes follow `cite_check.py`: 0 pass, 1 failures, 2 usage.
- Code comments and test docstrings follow each file's style: short plain sentences. Each test says which mutation turns it red. Commit messages: `<type>: explain: <description>`, ending with the session's Co-Authored-By line.

## Review Focus

1. A cite on a line inside a sub-process that belongs to a child element without its own label row (`<bpmn:incoming>`, `<bpmn:outgoing>`, `<camunda:inputParameter>`). Expected: the line resolves to the nearest ancestor that has a row (the sub-process), so it counts for check condition 2. A line inside a child task resolves to the task, not to the sub-process. Pinned by `test_incoming_line_resolves_to_its_sub_process` and `test_line_of_a_child_task_is_not_its_sub_process` (Task 3).
2. A name with `&`, `<` or `"` (Modeler writes `&quot;` and `&#10;` into names). Expected: the label and the SVG text are escaped once and read the same as the name in Modeler. A line break in a name becomes one space. Pinned by `test_name_with_entities_is_escaped_once` (Task 2) and `test_label_escapes_markup` (Task 3).
3. A plane wider than the column, such as the aos main plane of 948 units, at 500 px. Expected: `figure.bpmn` scrolls inside itself, so the page has no HSCROLL. The SVG is never scaled down, so there is no SMALLTEXT. Pinned by `test_wide_bpmn_figure_scrolls_without_page_hscroll` (Task 5).
4. A cite whose `data-path` ends in `.BPMN` or `.bpmn20.xml`, or a `.bpmn` cite whose file is missing. Expected: only the exact suffix `.bpmn` (lowercase) is a BPMN cite. A missing or unparseable file is one failure line that names the path, never a traceback. Pinned by `test_missing_bpmn_file_is_one_failure_line` (Task 4).
5. A page fixed by hand after `label` ran: the author moves a cite to another line and does not run `label` again. Expected: check condition 3 reports the stale label, with the current and expected text. Pinned by `test_stale_label_fails_condition_3` (Task 4).

## Beyond the letter of the spec (decisions made with no user present)

1. **The model comes from one `xml.parsers.expat` pass, not from `xml.etree` plus a text scan.** Spec 2.1 names etree and a line scan. The owner rule of 2.3 needs both the start and the end line of every element, including the elements without an id (`conditionExpression`, `incoming`, `BPMNLabel`). Expat (stdlib) reports `CurrentLineNumber` at each start and end tag. A text scan cannot pair closing tags reliably. Cost if wrong: none to the contract. The CLI and its output are unchanged.
2. **"The element that owns a line" means the innermost element spanning the line that has a row in the label table.** A child without a row (`incoming`, `outgoing`, `extensionElements` and its content, `documentation`, `waypoint`, `Bounds`) resolves to its nearest ancestor that has a row. The spec's row "content of extensionElements → the owner's name" implies this rule. A blank line, a comment-only line, or a line outside the root element resolves to no element. Every line inside `<definitions>` would otherwise resolve to the definitions element, and the blank-line fault of 2.3 could never fire.
3. **Label formats the spec leaves open:** `<kind>` is the local tag name split at its capitals and lowercased (`exclusiveGateway` → `exclusive gateway`, `subProcess` → `sub process`). An error with a code is labelled `<name> (<errorCode>)`. A name's newlines (`&#10;`) become single spaces in labels and SVG titles.
4. **The renderer is a second module, `scripts/bpmn_svg.py`.** Spec 2.1 names one tool. The CLI is still `bpmn.py svg`. Only the module split differs, and it keeps each file under 400 lines.
5. **`figure.bpmn` breaks out of the 72ch column the way `figure.clip` does**, with `--bpmn-w: max(100%, min(1040px, 100vw - 64px))`. With a 20-unit margin on each side, the aos main plane is 988 px wide, which is wider than the column. Spec 2.1 says "no scroll at 1440 px": 1040 px meets that. The template's `svg text { font-size: 18px; }` overrides SVG presentation attributes, so `svg.bpmn text` gets its own 14 px rule, and the renderer also writes `font-size="14"` so that the SVG reads correctly on its own.
6. **Failure lines that no section owns use `page` as the section id** (conditions 1 and 2). A cite or an SVG outside any `<section id>` also uses `page`.
7. **`SKILL.md` gets no change.** Spec 4 says "SKILL.md where it lists scripts", but `SKILL.md` lists no scripts. Its Build procedure runs `verify.sh`, which now runs `check`.
8. **The BPMN fixture page is built at test time** from `templates/page.html` plus one committed section fragment, as `lesson_page` in `test_lesson_e2e.py` does. The page never drifts from the template, and `verify.sh` runs the template's real guard on it. It is written to a temp directory beside a copy of `two_planes.bpmn`, with `data-root="."` (the template's only live cite is a URL).
9. **The new `bpmn: none` line ripples through seven existing test modules** that pin the verify lines. Task 6 owns all of them. The list is in Task 6.

## File Structure

| File | Responsibility |
|---|---|
| `skills/explain/scripts/bpmn.py` (new) | Model and line spans, `planes`, the label rule, `label` (page rewrite), `check`, the CLI |
| `skills/explain/scripts/bpmn_svg.py` (new) | One plane → one SVG string |
| `skills/explain/scripts/verify.sh` | Runs `bpmn.py check` as its last check for sheet, page and lesson |
| `skills/explain/templates/page.html` | CSS for `figure.bpmn`, the shapes, `.hl`, `.bpmn-label` |
| `skills/explain/rungs/page.md`, `rungs/lesson.md`, `rungs/sheet.md`, `lesson/review-page.md` | Rules, verify lists, the line counts, the fourth gate-1 check |
| `skills/explain/tests/fixtures/two_planes.bpmn` (new) | The hand-written two-plane model |
| `skills/explain/tests/fixtures/bpmn-section.html` (new) | One page section on that model: two figures, labelled cites |
| `skills/explain/tests/bpmn_page.py` (new) | `bpmn_page(out)`, which builds the fixture page from the template (helper module, no tests) |
| `skills/explain/tests/test_bpmn_svg.py`, `test_bpmn_label.py`, `test_bpmn_check.py` (new) | The tool |
| `test_verify.py`, `test_page_template.py`, `test_sheet_template.py`, `test_lesson_e2e.py`, `test_lesson_prompts.py`, `test_rung_drift.py` | Adjusted pins and the new drift tests |

---

### Task 1: the model, the line spans and `planes`

**Files:**
- Create: `skills/explain/scripts/bpmn.py`
- Create: `skills/explain/tests/fixtures/two_planes.bpmn`
- Create: `skills/explain/tests/test_bpmn_svg.py` (the `PlanesCase` part; Task 2 adds the rest)

**Interfaces:**
- Produces, in `bpmn.py`:

```python
class Node(NamedTuple):
    ns: str                 # namespace URI
    tag: str                # local name, e.g. "exclusiveGateway"
    attrs: dict[str, str]   # local attribute names, e.g. {"id": ..., "name": ...}
    start: int              # 1-based line of "<"
    end: int                # 1-based line of the end tag (== start when self-closing)
    parent: int | None      # index into Model.nodes
    children: tuple[int, ...]
class Plane(NamedTuple):
    id: str                 # bpmnElement of the BPMNPlane
    name: str | None        # name of that element
    line: int               # start line of that element
    plane: int              # index of the BPMNPlane node
class Model(NamedTuple):
    path: Path
    nodes: list[Node]       # document order
    by_id: dict[str, int]   # model ids only (BPMN namespace elements), not DI ids
    planes: list[Plane]     # document order
    lines: list[str]        # the file's text lines, for the blank and comment test
class BpmnError(Exception): ...   # unreadable file or an expat error, message names the path
def load(path: Path) -> Model
def main(argv: list[str]) -> int
```

- Fixture contract, `two_planes.bpmn` (about 150 lines, Modeler 5 layout, Russian names): a collaboration with one participant. Main process: start event `Start_1`, collapsed sub-process `STAGE_A` (name `Первичная проверка`), exclusive gateway `Gateway_1` with a default flow and two named flows (one with a `conditionExpression` on its own line), an expanded event sub-process `EventSub_1` with a timer start and an end event, an end event `End_1`, and `bpmn:error` `Error_1` with an `errorCode`. Plane 1 is the collaboration. Plane 2 is `STAGE_A`: service task `Task_svc` with a non-interrupting timer boundary `Timer_1`, send task `Task_send`, receive task `Task_recv`, an end event with `terminateEventDefinition`, one text annotation with an association. One task name is long enough to need three lines at 14 units in its shape width (the overflow case of Task 2). One flow node has no `name`. One name holds `&quot;` and `&#10;`. One blank line and one XML comment sit inside the process.

- [ ] **Step 1: Write the failing tests** (`PlanesCase`)

```python
def test_planes_lists_both_planes(self):  # stdout == "Collaboration_1\t-\t<line>\nSTAGE_A\tПервичная проверка\t<line>\n" with the fixture's real lines
def test_spans_of_a_multi_line_tag(self):  # load(): STAGE_A.start is the "<bpmn:subProcess" line, .end the "</bpmn:subProcess>" line
def test_self_closing_tag_starts_and_ends_on_one_line(self):  # every <dc:Bounds .../> node has start == end
def test_missing_file_exits_2(self):  # main(["planes", "nope.bpmn"]) == 2, stderr names nope.bpmn
def test_malformed_xml_exits_2_with_the_line(self):  # a truncated copy: exit 2, stderr holds "line <n>"
def test_no_subcommand_exits_2_with_usage(self):  # main([]) == 2, stderr starts with "usage: bpmn.py"
```

`planes` prints one tab-separated line per plane: the id, the name or `-`, and the line.

- [ ] **Step 2: Run them, expect red**

Run: `cd skills/explain && python3 -B -m unittest tests.test_bpmn_svg.PlanesCase`
Expected: `ModuleNotFoundError` or `FAILED (errors=6)`

- [ ] **Step 3: Implement `load` and the `planes` subcommand in `bpmn.py`**

One expat parser with `namespace_separator=" "`. The start handler pushes a `Node` with `CurrentLineNumber`, the end handler sets `end`. `by_id` holds only elements in the BPMN model namespace `http://www.omg.org/spec/BPMN/20100524/MODEL`. A plane is each `BPMNPlane` (namespace `http://www.omg.org/spec/BPMN/20100524/DI`). `main` dispatches `planes`, `svg`, `label` and `check`. Unknown or missing subcommands exit 2 with the usage on stderr. Tasks 2 to 4 add their subcommands.

- [ ] **Step 4: Run them, expect green**

Run: `cd skills/explain && python3 -B -m unittest tests.test_bpmn_svg.PlanesCase`
Expected: `OK`

- [ ] **Step 5: Smoke on the real subject**

Run: `cd skills/explain && python3 scripts/bpmn.py planes /Users/valukin/work/aos/src/main/resources/aos.bpmn | wc -l`
Expected: `11`

- [ ] **Step 6: Commit**

```bash
git add skills/explain/scripts/bpmn.py skills/explain/tests/fixtures/two_planes.bpmn skills/explain/tests/test_bpmn_svg.py
git commit -m "feat: explain: bpmn.py reads a .bpmn with line spans and lists its planes"
```

### Task 2: the renderer, `bpmn.py svg`

**Files:**
- Create: `skills/explain/scripts/bpmn_svg.py`
- Modify: `skills/explain/scripts/bpmn.py` (the `svg` subcommand)
- Modify: `skills/explain/tests/test_bpmn_svg.py` (`SvgCase`)

**Interfaces:**
- Consumes: `Model`, `Node`, `Plane`, `load` (Task 1).
- Produces, in `bpmn_svg.py`:

```python
FONT = 14            # units; also the floor
EM_PER_CHAR = 0.55
MARGIN = 20
def render(model: Model, plane: Plane, highlight: frozenset[str], prefix: str) -> tuple[str, list[str]]  # (svg text, warnings)
def wrap(name: str, width: float, height: float) -> tuple[list[str], bool]  # (lines, cut)
```

- CLI: `bpmn.py svg <file> [--plane <id>] [--highlight id,id,…] [--prefix <p>]`. `--plane` defaults to the first plane, `--prefix` to the plane id. An unknown plane exits 2 and prints the `planes` output on stderr. Each warning goes to stderr as `bpmn.py: <file>: skipped <id>: <reason>`, and the exit code stays 0.

- [ ] **Step 1: Write the failing tests** (`SvgCase`, each on the fixture)

```python
def test_root_attributes(self):  # <svg class="bpmn" role="img" data-ste="skip" data-plane="STAGE_A" viewBox=... width=... height=...>, first child <title>Первичная проверка</title>
def test_view_box_is_bounds_plus_margin(self):  # viewBox == "<minx-20> <miny-20> <w+40> <h+40>" from the plane's Bounds and waypoints
def test_one_data_id_per_shape_and_edge(self):  # set of data-id == set of bpmnElement of the plane's BPMNShape and BPMNEdge
def test_kind_tags(self):  # Task_svc carries text "service", Task_send "send", Task_recv "receive"
def test_gateway_marker(self):  # Gateway_1 group on the main plane holds "×"
def test_collapsed_sub_process_has_plus_marker(self):  # STAGE_A group on the main plane holds the "+" marker
def test_event_sub_process_is_dotted(self):  # EventSub_1 rect has a stroke-dasharray
def test_default_flow_has_its_slash(self):  # the default flow of Gateway_1 has one extra short line near its first waypoint
def test_non_interrupting_boundary_is_dashed(self):  # Timer_1 circle has a stroke-dasharray
def test_highlight_marks_exactly_those_ids(self):  # --highlight Task_svc,Gateway_1: exactly the elements with those data-id carry class "hl"
def test_no_text_under_14(self):  # every font-size in the output is >= 14
def test_long_name_wraps_and_ends_in_ellipsis(self):  # the long task: >1 <tspan>, last ends with "…", its <title> holds the full name
def test_name_with_entities_is_escaped_once(self):  # "&quot;" in the file → '"' rendered as "&quot;" once (no "&amp;quot;"), "&#10;" → one space
def test_prefix_on_every_marker_and_title_id(self):  # --prefix p1: every id= in the output starts with "p1-"
def test_unknown_plane_exits_2_and_lists_planes(self):  # exit 2, stderr holds both plane lines
def test_output_is_byte_equal_on_a_second_run(self):  # two runs, equal stdout
def test_shape_without_bounds_is_skipped_with_a_warning(self):  # a copy with one dc:Bounds removed: exit 0, that id absent, stderr names it
```

- [ ] **Step 2: Run them, expect red**

Run: `cd skills/explain && python3 -B -m unittest tests.test_bpmn_svg.SvgCase`
Expected: `FAILED`

- [ ] **Step 3: Implement `render` and `wrap` in `bpmn_svg.py` and wire `svg` into `bpmn.py`**

The shape table of spec 2.1 decides each element's look. Draw in document order of the DI: participant and lanes first, then shapes, then edges, then labels. Each element is one `<g data-id="…">` with an optional `class="hl"`. Colours are CSS classes only (`bpmn-shape`, `bpmn-flow`, `bpmn-text`, `hl`), so that the page palette applies (Task 5). Text gets `font-size="14"`. `wrap` breaks words greedily at `width / (FONT * EM_PER_CHAR)` characters per line, and keeps as many lines as `height` holds at a line height of 1.2 em. A cut name ends in `…` and puts the full name into a `<title>`. Arrowheads are `<marker id="<prefix>-arrow">` and `<marker id="<prefix>-open">`. All other ids get the prefix too.

- [ ] **Step 4: Run them, expect green**

Run: `cd skills/explain && python3 -B -m unittest tests.test_bpmn_svg`
Expected: `OK`

- [ ] **Step 5: Smoke: every aos plane renders without a warning**

Run: `cd skills/explain && f=/Users/valukin/work/aos/src/main/resources/aos.bpmn; for p in $(python3 scripts/bpmn.py planes $f | cut -f1); do python3 scripts/bpmn.py svg $f --plane $p >/dev/null || echo "FAIL $p"; done 2>&1 | wc -l`
Expected: `0`

- [ ] **Step 6: Commit**

```bash
git add skills/explain/scripts/bpmn_svg.py skills/explain/scripts/bpmn.py skills/explain/tests/test_bpmn_svg.py
git commit -m "feat: explain: bpmn.py svg draws one plane from the file's own DI"
```

### Task 3: the label rule and `bpmn.py label`

**Files:**
- Modify: `skills/explain/scripts/bpmn.py`
- Create: `skills/explain/tests/test_bpmn_label.py`

**Interfaces:**
- Consumes: `load`, `Model`, `Node` (Task 1).
- Produces, in `bpmn.py`:

```python
def owner(model: Model, line: int) -> int | None         # index into model.nodes, or None (no element)
def label_of(model: Model, node: int) -> str
def bpmn_cites(html: str) -> list[Cite]                  # every <cite> whose data-path ends in ".bpmn", document order
class Cite(NamedTuple):
    span: tuple[int, int]   # character offsets of the whole <cite>…</cite> in the page
    path: str; line: int
    section: str            # id of the enclosing <section>, or "page"
    label: str | None       # text of the existing span.bpmn-label, unescaped
def page_root(html: str, html_dir: Path) -> Path | None   # data-root of #provenance joined to html_dir, as cite_check does
def label_page(html: str, html_dir: Path) -> tuple[str, list[str]]  # (new page, failure lines)
```

- The rules are spec 2.3 plus decisions 2 and 3. Failure lines are `<section> | <path>:<line> | no element`, or `<section> | <path> | <BpmnError message>`. `label <index.html>` writes the new page only when it differs, prints the failure lines, and exits 1 if there are any (it still writes the labels it could resolve). It exits 2 for no argument, an unreadable page, or no `data-root`. The span is `<span class="bpmn-label">…</span>`, inserted directly after the cite's `</code>`. An existing span is replaced. The rest of the page stays byte-identical.

- [ ] **Step 1: Write the failing tests** (on `two_planes.bpmn`; lines found by searching the fixture text, never hard-coded)

```python
def test_named_task_line(self):  # label of the Task_svc start line == its name
def test_unnamed_node_is_kind_and_id(self):  # the unnamed node == "<kind words> <id>", e.g. "exclusive gateway Gateway_1"
def test_sequence_flow_line(self):  # the flow Start_1 → STAGE_A == "<Start_1 name> → Первичная проверка"
def test_condition_line_is_its_flow_with_flow_name(self):  # the conditionExpression line == "<src> → <tgt>, <flow name>"
def test_error_carries_its_code(self):  # Error_1 line == "<name> (<errorCode>)"
def test_di_shape_line_is_its_element(self):  # the BPMNShape line of Task_svc == Task_svc's label
def test_bpmn_label_line_is_its_edge_element(self):  # a <bpmndi:BPMNLabel> line inside an edge == that flow's label
def test_process_and_participant_lines(self):  # participant line == its name; process line without name == "process <id>"
def test_incoming_line_resolves_to_its_sub_process(self):  # an <bpmn:incoming> line of STAGE_A: owner is STAGE_A
def test_line_of_a_child_task_is_not_its_sub_process(self):  # Task_send's line inside STAGE_A: owner is Task_send
def test_blank_and_comment_lines_have_no_owner(self):  # owner() is None for the blank line, the comment line, line 1 (XML declaration) and len+1
def test_label_rewrites_in_place_and_is_idempotent(self):  # run twice on a small page: the first adds spans, the second leaves the file byte-equal
def test_label_escapes_markup(self):  # a name holding '"' and '&' is escaped once in the span
def test_cite_on_a_blank_line_exits_1_and_names_it(self):  # exit 1, stdout "s1 | two_planes.bpmn:<n> | no element"
def test_non_bpmn_cites_are_untouched(self):  # a .py cite and a ".BPMN" cite get no span
def test_no_root_exits_2(self):  # a page without data-root: exit 2
```

- [ ] **Step 2: Run them, expect red**

Run: `cd skills/explain && python3 -B -m unittest tests.test_bpmn_label`
Expected: `FAILED`

- [ ] **Step 3: Implement `owner`, `label_of`, `bpmn_cites`, `page_root`, `label_page` and the `label` subcommand**

`bpmn_cites` finds each `<cite\b[^>]*>.*?</cite>` with `re.DOTALL` and parses the start tag's attributes with `html.parser.HTMLParser`. The section is the id of the last `<section id=…>` start tag before the cite whose `</section>` is not yet reached. A `.bpmn` file loads once per page (cache by path).

- [ ] **Step 4: Run them, expect green**

Run: `cd skills/explain && python3 -B -m unittest tests.test_bpmn_label tests.test_bpmn_svg`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/bpmn.py skills/explain/tests/test_bpmn_label.py
git commit -m "feat: explain: bpmn.py label writes a readable name into each BPMN cite"
```

### Task 4: the coverage check, `bpmn.py check`, and the fixture page

**Files:**
- Modify: `skills/explain/scripts/bpmn.py`
- Create: `skills/explain/tests/fixtures/bpmn-section.html`
- Create: `skills/explain/tests/bpmn_page.py`
- Create: `skills/explain/tests/test_bpmn_check.py`

**Interfaces:**
- Consumes: `load`, `owner`, `label_of`, `bpmn_cites`, `page_root`, `label_page` (Tasks 1, 3); `render` (Task 2).
- Produces:

```python
# bpmn.py
def check_page(html: str, html_dir: Path) -> tuple[list[str], bool]   # (failure lines, any .bpmn cited)
# tests/bpmn_page.py
FIXTURES: Path
def bpmn_page(out: Path, section: str | None = None) -> Path   # writes out/index.html and out/two_planes.bpmn, returns the page path
```

- Failure lines (exact form):
  - condition 1: `page | plane | <id> (<name or id>) has no svg.bpmn and is not in Not covered`
  - condition 2: `page | sub-process | <id> (<name>) has no cite and is not in Not covered`
  - condition 3: `<section> | label | <path>:<line> | missing`, or `<section> | label | <path>:<line> | stale: "<found>" is not "<expected>"`
  - condition 4: `<section> | diagram | data-plane <id> is no plane of a cited file`, or `<section> | diagram | data-id <id> is not in <path>`
  - a cited file that cannot load: `<section> | file | <path> | <BpmnError message>`
- Summary line: `bpmn: ok`, `bpmn: none` (no `.bpmn` cite, exit 0) or `bpmn: <n> failures`. Exit 0, 1, or 2 (usage, as for `label`).
- "In Not covered" means the name (or the id, for an element without a name) occurs verbatim in the text of `p.not-covered`.
- `bpmn-section.html`: one `<section id="stage-a">` with an `<h2>`, two `figure.bpmn` (one per plane, the output of `bpmn.py svg`, pasted in), STE prose, and one `div.cites` per paragraph. Its cites cover `STAGE_A` and `EventSub_1` and carry labels written by `bpmn.py label`. `bpmn_page` edits the template the way `lesson_page` does: the section before `<section id="provenance-facet">`, its nav link before the Provenance link, and `data-root="."` kept. Each anchor must occur exactly once (AssertionError otherwise). The fragment must also pass `cite_check.py` (verbatim snippets, `basename:line`) and `ste_lint.py --html`, because Task 6 runs the whole of `verify.sh` on the page.

- [ ] **Step 1: Write the failing tests**

```python
def test_fixture_page_passes(self):  # check exits 0, stdout == "bpmn: ok\n"
def test_page_without_bpmn_cites_is_none(self):  # templates/page.html itself: exit 0, "bpmn: none\n"
def test_removed_plane_svg_fails_condition_1(self):  # the STAGE_A figure removed: exit 1, "page | plane | STAGE_A (Первичная проверка) has no svg.bpmn and is not in Not covered"
def test_plane_named_in_not_covered_passes(self):  # same, plus the name in p.not-covered: exit 0
def test_sub_process_without_cite_fails_condition_2(self):  # EventSub_1 cites removed: its line; then its name added to p.not-covered: exit 0
def test_cite_of_a_child_does_not_cover_its_sub_process(self):  # STAGE_A cited only through Task_send's line: condition 2 fails for STAGE_A
def test_missing_label_fails_condition_3(self):  # one span.bpmn-label removed: "<section> | label | two_planes.bpmn:<n> | missing"
def test_stale_label_fails_condition_3(self):  # one span text edited by hand: "... | stale: \"<edited>\" is not \"<expected>\""
def test_foreign_data_id_fails_condition_4(self):  # one data-id changed to "Nope_1": "stage-a | diagram | data-id Nope_1 is not in two_planes.bpmn"
def test_foreign_plane_fails_condition_4(self):  # data-plane changed to "Nope_P"
def test_missing_bpmn_file_is_one_failure_line(self):  # two_planes.bpmn deleted from out/: exit 1, one "file" line, no traceback on stderr
def test_summary_counts_failures(self):  # two mutations at once: last line "bpmn: 2 failures"
```

- [ ] **Step 2: Run them, expect red**

Run: `cd skills/explain && python3 -B -m unittest tests.test_bpmn_check`
Expected: `FAILED`

- [ ] **Step 3: Write the fixture section, `bpmn_page`, `check_page` and the `check` subcommand**

To find the figures, `check_page` parses the page with `html.parser`: every `svg` element whose class holds `bpmn`, its `data-plane`, and every `data-id` inside it. It also reads the text of `p.not-covered` and every BPMN cite via `bpmn_cites`. Condition 3 recomputes the label with `label_of(owner(…))` and compares it with `Cite.label`.

- [ ] **Step 4: Run them, expect green**

Run: `cd skills/explain && python3 -B -m unittest tests.test_bpmn_check tests.test_bpmn_label tests.test_bpmn_svg`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/bpmn.py skills/explain/tests/fixtures/bpmn-section.html skills/explain/tests/bpmn_page.py skills/explain/tests/test_bpmn_check.py
git commit -m "feat: explain: bpmn.py check holds a page to every plane and sub-process of its .bpmn"
```

### Task 5: the page template CSS

**Files:**
- Modify: `skills/explain/templates/page.html` (the style block, next to the `figure.clip` rules and the `.cites` rules)
- Modify: `skills/explain/tests/test_page_template.py`

**Interfaces:**
- Consumes: `bpmn_page` (Task 4). The SVG classes `bpmn-shape`, `bpmn-flow`, `bpmn-text`, `hl` (Task 2).
- Produces, CSS, all on the palette variables of the template (`--ink`, `--muted`, `--fill`, `--line`, `--accent`):

```css
figure.bpmn { --bpmn-w: max(100%, min(1040px, 100vw - 64px)); width: var(--bpmn-w); margin: 16px 0 16px calc((100% - var(--bpmn-w)) / 2); overflow-x: auto; }
figure.bpmn svg { display: block; max-width: none; }
svg.bpmn text { font-size: 14px; }
.bpmn-label { display: block; color: var(--ink); font-family: var(--sans); font-size: 16px; }
cite:has(.bpmn-label) > code { color: var(--muted); font-size: 14px; }
```

plus the shape, flow and `.hl` rules (stroke and fill only; the `.hl` stroke is `var(--accent)`, its fill a light mix of the accent). The exact selectors of the first five lines are fixed. Colours of the rest follow the palette.

- [ ] **Step 1: Write the failing tests**

```python
def test_bpmn_rules_exist_and_keep_the_floor(self):  # each selector above is in the style block; no font-size in those rules is under 14px
def test_bpmn_fixture_page_passes_the_guard(self):  # verify.sh on bpmn_page(tmp): render 1440x900: ok, render 500x844: ok
def test_wide_bpmn_figure_scrolls_without_page_hscroll(self):  # bpmn-section with a figure whose svg width is 988: both renders ok (no HSCROLL, no SMALLTEXT); red when overflow-x is removed
```

- [ ] **Step 2: Run them, expect red**

Run: `cd skills/explain && python3 -B -m unittest tests.test_page_template > /tmp/bpmn-t5.log 2>&1; tail -3 /tmp/bpmn-t5.log`
Expected: `FAILED`

- [ ] **Step 3: Add the rules to `templates/page.html`**, with a comment block in the style of the `figure.clip` comment that says why the figure breaks out and scrolls.

- [ ] **Step 4: Run them, expect green**

Run: `cd skills/explain && python3 -B -m unittest tests.test_page_template > /tmp/bpmn-t5.log 2>&1; tail -3 /tmp/bpmn-t5.log`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add skills/explain/templates/page.html skills/explain/tests/test_page_template.py
git commit -m "feat: explain: page template draws a BPMN plane at full size and lets a cite lead with its label"
```

### Task 6: the `bpmn:` line of `verify.sh`

**Files:**
- Modify: `skills/explain/scripts/verify.sh` (header comment, a new check after `media`)
- Modify: `skills/explain/tests/test_verify.py`, `test_page_template.py`, `test_sheet_template.py`, `test_lesson_e2e.py`, `test_lesson_prompts.py` (the pinned line lists)
- Modify: `skills/explain/rungs/sheet.md:141`, `rungs/page.md:135`, `rungs/lesson.md:403-413` (the line counts and the quoted lesson block)

**Interfaces:**
- Consumes: the `bpmn.py check` CLI and its summary line (Task 4).
- Produces: one more stdout line for sheet, page and lesson (not video), after `media` when there is one, otherwise after `prose`:

```
bpmn: ok | none | FAIL <n> failure(s) | FAIL bpmn exit <code>
```

Detail lines (each `check` failure line) follow a FAIL line, indented by two spaces. Exit 0 and `bpmn: none` print `bpmn: none`. Exit 0 otherwise prints `bpmn: ok`. Exit 1 prints `FAIL <n> failure(s)`. Any other exit prints `FAIL bpmn exit <code>` and sets the failure flag. The header comment's counts become: sheet five, page six, lesson seven, video three.

- [ ] **Step 1: Write the failing tests** in `test_verify.py`

```python
def test_page_without_bpmn_prints_bpmn_none_last(self):  # verify-good page lines end with "bpmn: none"
def test_bpmn_fixture_page_prints_bpmn_ok(self):  # bpmn_page(tmp): stdout == LESSON_PASS-style page lines + "bpmn: ok\n", exit 0
def test_bpmn_failure_prints_count_and_details(self):  # bpmn_page with the STAGE_A figure removed: "bpmn: FAIL 1 failure(s)" then "  page | plane | STAGE_A ...", exit 1
def test_lesson_prints_bpmn_after_media(self):  # the lesson fixture: last two lines "media: ok", "bpmn: none"
def test_video_prints_no_bpmn_line(self):  # the video transcript: three lines, as before
```

- [ ] **Step 2: Run them, expect red**

Run: `cd skills/explain && python3 -B -m unittest tests.test_verify > /tmp/bpmn-t6.log 2>&1; tail -3 /tmp/bpmn-t6.log`
Expected: `FAILED`

- [ ] **Step 3: Add the check to `verify.sh`**, in the shape of the `citations` block: run `python3 "$SCRIPTS/bpmn.py" check "$input_abs"`, take the summary from its last stdout line, and print the details through `indent`.

- [ ] **Step 4: Move every pinned line list to the new count.** These are the known pins. Re-run the grep below and fix every hit it prints:
  - `test_verify.py`: `GOOD_OUT`, `LESSON_PASS`, `CHECKS`, the `len(lines) == 4` asserts (lines 139, 254), the slices at 142, 196, 227, 244, and the `media: ok` endings at 367, 419, 432, 487, 500, 518
  - `test_page_template.py`: `OTHER_OK`
  - `test_sheet_template.py`: `OK_LINES`
  - `test_lesson_e2e.py`: lines 254 to 266, and the module docstring's "six ok lines"
  - `test_lesson_prompts.py`: the docstring at 25 and the assert at 398 (lesson.md's quoted block)
  - `rungs/sheet.md` "All four lines" → five, plus the list; `rungs/page.md` "All five lines" → six, plus the list; `rungs/lesson.md` "six lines" → seven, plus `bpmn: ok` in the quoted block

Run: `cd skills/explain && grep -rn -e "prose: ok" -e "media: ok" -e "four lines" -e "five lines" -e "six lines" rungs lesson tests/*.py scripts/verify.sh`
Expected: every hit is a list that ends with the `bpmn` line, or a video or film list (three lines, unchanged).

- [ ] **Step 5: Run the affected modules, expect green** (each with its output in a log file, polled)

Run: `cd skills/explain && python3 -B -m unittest tests.test_verify tests.test_page_template tests.test_sheet_template tests.test_lesson_prompts tests.test_rung_drift tests.test_lesson_e2e > /tmp/bpmn-t6.log 2>&1; tail -3 /tmp/bpmn-t6.log`
Expected: `OK` (the gated lesson E2E may show `skipped`)

- [ ] **Step 6: Lint the rung files**

Run: `cd skills/explain && for f in rungs/sheet.md rungs/page.md rungs/lesson.md; do python3 ../ste/scripts/ste_lint.py $f | tail -1; done`
Expected: `0 errors, 0 warnings` three times

- [ ] **Step 7: Commit**

```bash
git add skills/explain/scripts/verify.sh skills/explain/tests skills/explain/rungs
git commit -m "feat: explain: verify.sh runs the BPMN coverage check as its last line"
```

### Task 7: the rung rules and the gate-1 check

**Files:**
- Modify: `skills/explain/rungs/page.md` ("Plan the sections", "Diagram patterns", "Write the prose", "Verify and export")
- Modify: `skills/explain/rungs/lesson.md` ("Plan the lesson" step 2)
- Modify: `skills/explain/lesson/review-page.md` (Checks: a fourth check)
- Modify: `skills/explain/tests/test_rung_drift.py` (new `BpmnRungCase`), `skills/explain/tests/test_lesson_prompts.py` (`CHECK_COUNT[PAGE]` 3 → 4)

**Interfaces:**
- Consumes: the CLI forms of `planes`, `svg`, `label` and `check` (Tasks 1 to 4). The CSS class names of Task 5. The verify lines of Task 6.
- Produces, as text in the rung files:
  - "Plan the sections": the bullets of spec 2.2 (the main plane first with the stages highlighted, one section per collapsed stage in process order, a paragraph per inner sub-process, gateway, user task and path-changing boundary event, nested planes, the sibling pattern paragraph, the count follows the planes, `Not covered` by name verbatim). The "about twelve" bullet names the BPMN exception.
  - "Diagram patterns": a pattern "BPMN plane" with the `figure.bpmn` block of spec 2.2, verbatim, and the rule that a flow in a `.bpmn` file is never drawn by hand.
  - "Write the prose": the BPMN cite rule (cite the line that carries the fact: the id line, the `name=` line, the flow or its condition line).
  - "Verify and export": before step 1, two steps in this order: `python3 <skill-dir>/scripts/bpmn.py svg <file> --plane <id> --highlight <ids>` for each plane (while writing), then `python3 <skill-dir>/scripts/bpmn.py label index.html` after the cites are written. Then `verify.sh`.
  - `lesson.md` step 2: for a BPMN main flow, the planes (`bpmn.py planes`) are the section candidates.
  - `review-page.md` check 4, verbatim from the spec: "For each sub-process, gateway and user task in the section's diagram, a paragraph explains it; the names in the prose match the diagram."

- [ ] **Step 1: Write the failing tests**

```python
def test_page_md_names_the_three_bpmn_commands_in_order(self):  # section "Verify and export": "bpmn.py svg" before "bpmn.py label" before "verify.sh"
def test_page_md_has_the_bpmn_plane_pattern(self):  # section "Diagram patterns" holds '<figure class="bpmn">' and "never drawn by hand"
def test_page_md_plans_one_section_per_stage(self):  # section "Plan the sections" holds "one section per stage" and "a merge may not drop a plane"
def test_lesson_md_reads_the_planes_as_candidates(self):  # section "Plan the lesson" holds "bpmn.py planes"
def test_review_page_has_the_bpmn_check(self):  # CHECK_COUNT[PAGE] == 4, and check 4 holds "the names in the prose match the diagram"
def test_page_md_and_lesson_md_lint_clean(self):  # ste_lint: 0 errors, 0 warnings for both
```

The quoted phrases are the contract between the tests and the rung text. Write the rung text so that it holds them verbatim, and STE-clean.

- [ ] **Step 2: Run them, expect red**

Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift.BpmnRungCase tests.test_lesson_prompts`
Expected: `FAILED`

- [ ] **Step 3: Edit `page.md`, `lesson.md` and `review-page.md`** as listed under Produces.

- [ ] **Step 4: Run them, expect green**

Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift tests.test_lesson_prompts`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add skills/explain/rungs/page.md skills/explain/rungs/lesson.md skills/explain/lesson/review-page.md skills/explain/tests/test_rung_drift.py skills/explain/tests/test_lesson_prompts.py
git commit -m "docs: explain: a BPMN subject gets one section per stage, a diagram per plane and a gate-1 coverage check"
```

### Task 8: full suite and acceptance handoff

**Files:** none changed, unless the suite finds a fault (fix it in the task that owns the file, and commit with that task's prefix).

- [ ] **Step 1: Run the full suite** (log file, polled)

Run: `cd skills/explain && python3 -B -m unittest discover -s tests -t . > /tmp/bpmn-full.log 2>&1; tail -3 /tmp/bpmn-full.log`
Expected: `OK` (gated video and lesson E2E tests may be `skipped`)

- [ ] **Step 2: Run the tool end to end on the delivered aos lesson** (a dry read, which proves the tool on a real page and writes nothing). Copy `out/2026-10-06-145908-lesson-aos/index.html` to a temp directory, then run `bpmn.py label` and `bpmn.py check` on the copy.

Run: `d=$(mktemp -d); cp ~/karpathy/out/2026-10-06-145908-lesson-aos/index.html $d/; python3 skills/explain/scripts/bpmn.py label $d/index.html; python3 skills/explain/scripts/bpmn.py check $d/index.html | tail -1`
Expected: `bpmn: <n> failures` with n > 0. The old lesson has no plane figures, so condition 1 fires for all eleven planes. That shows the check catches the user's fault 2 on the real subject. Record n in the task's close reason.

- [ ] **Step 3: Hand off the acceptance run.** `/explain` starts only from the user. Ask the user to run `/explain /Users/valukin/work/aos --as lesson`. Acceptance (spec 4): eleven planes shown, every stage section explains its inner sub-processes, every BPMN cite reads as a name, `verify.sh` prints seven `ok` lines, and a cold gate-1 reviewer finds no sub-process without a paragraph.
