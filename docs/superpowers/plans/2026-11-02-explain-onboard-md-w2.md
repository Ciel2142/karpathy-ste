# explain onboard: wave onboard-md-page (the Markdown page and its check) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/explain <service-dir> --as onboard` writes a Confluence-ready `page.md` beside the PlantUML PNGs of wave one, `onboard.py page` checks that page against the map, the rung and the skill text say so, the course keeps Mermaid, and the HTML onboarding path is gone.

**Architecture:** `scripts/onboard_page.py` gains the `page` command: a pure `page_lines(page, doc, directory)` that reads a Markdown page as lines and returns the failure lines of spec 9 in table order, and `cmd_page`. `onboard.py` gains only the `page` dispatch and its usage line. `rungs/onboard.md` keeps its six level-2 sections and its thirteen-section map skeleton; sections 1 to 6 change wording to the PlantUML forms, the section plan of spec 10.2, the procedure of 10.3 and the output directory of spec 6, and `test_rung_drift.py` locks the new text. `SKILL.md`, `README.md`, `course/map-task.md` and `rungs/course.md` change by spec 11 and 12. The HTML onboarding path (`verify.sh`, `bpmn.py`, the test helper, the matrix rules of the page template and their tests) is removed.

**Tech Stack:** Python 3 standard library (`re`, `os`, `unittest`); the STE lint (`skills/ste/scripts/ste_lint.py`) for the rung, skill and page texts; PlantUML only through wave one's tests.

**Spec:** `docs/superpowers/specs/2026-11-02-explain-onboard-markdown-design.md`, sections 5, 6, the `page` half of 9, 10, 11, 12 and the page items of 13. Wave map: `docs/superpowers/waves/2026-11-02-explain-onboard-md.yaml`, wave `onboard-md-page`. Wave one's leftovers: br kp-x43h.

## Global Constraints

- Tests run with `cd skills/explain && python3 -B -m unittest discover -s tests` and, at the repo root, `python3 -B -m unittest discover -s tests`; the baseline carries four pre-existing film/narrate failures (see the wave map header) and nothing else may fail.
- The page check lives in `scripts/onboard_page.py`; `scripts/onboard.py` gains only the `page` entry of `main`'s dispatch, the usage line `onboard.py page <page.md> --map <map.md>` and `page:` in `main`'s stdout rule. `course.py` and `course/lesson-task.md` do not change (spec 11).
- The failure lines of the page check are exactly the prefixes of the spec 9 table, in that order, then `page: ok` or `page: <n> failures`; exit 0, 1, or 2 when the page or the map cannot be read.
- The page check is content-based and language-neutral: it never reads the words of a fixed heading; it reads the flow headings, which are the map's questions verbatim (spec 9).
- `rungs/onboard.md` keeps the six level-2 titles `When an onboarding page`, `Explore the service`, `The map`, `Plan the sections`, `Write the page`, `Output directory` and the thirteen map sections of `onboard.TITLES`; it lints clean (`ste_lint.py rungs/onboard.md` prints `0 errors, 0 warnings`), as do `course/map-task.md`, `SKILL.md` and the fixture `page.md`.
- The onboard check command of the rung is `onboard.py check map.md --root <root> --inventory inventory.txt --notation plantuml`; the course commands carry `--notation mermaid` (spec 11).
- Drift tests assert full phrases, never a bare word that another sentence may hold (br kp-f9g6: `gaps`, `title`).
- A plan task commits on its own with a `feat:`, `docs:`, `test:` or `chore:` message that names the rung (`explain onboard: ...`) and ends with the `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` line.

## Review Focus

1. A Russian page of a Russian map: the flow headings are the Russian questions verbatim, the short answer starts with `**Краткий ответ.**`, the entry and event names are code names; every check must hold without an ASCII assumption. Test in Task 3.
2. A page saved with CRLF line endings, or with trailing spaces on an image line: the title, the image lines and the cite lines must still be recognised. Test in Task 1.
3. A `# ` line, a `|`-table line or a `![…](…)` line inside a fenced code block: none of them is a second title, a cite line or an image line. Test in Task 1.
4. An image caption that holds parentheses or brackets (`![the order flow (v2)](diagrams/flow-order.png)`): the path is the last parenthesised group, not the first. Test in Task 2.
5. An entry name that is a prefix of another (`/orders` beside `POST /orders`), or a name that appears only inside a fence: a name counts as on the page wherever it appears, so a prefix match is not a false failure, and a fence is not a hiding place. Test in Task 3.

---

### Task 1: the page model and the structural checks, with the fixture page

**Files:**
- Create: `skills/explain/tests/fixtures/onboard/page.md`
- Modify: `skills/explain/scripts/onboard_page.py`
- Modify: `skills/explain/tests/test_onboard_page.py`

**Interfaces:**
- Consumes: `onboard.read_map`, `onboard.MapDoc`, `onboard._facts`, `onboard.keyed`, `onboard.none_found`, `onboard.HANDLE`, `diagram_files(doc)` of wave one.
- Produces:

```python
IMAGE = re.compile(r"!\[(.*)\]\(([^()]*)\)\s*$")       # caption, path: the last parenthesised group
HTML_TAG = re.compile(r"</?[A-Za-z][^<>]*>")
CITE_LINE = re.compile(r" \| [^|]+:[0-9]+ \| ")
class Line(NamedTuple):
    n: int            # 1-based
    text: str         # without the newline, `\r` stripped
    kind: str         # "blank", "fence", "heading1", "heading2", "list", "table", "image", "code", "text"
def page_lines_of(text: str) -> list[Line]      # fences toggle; a line inside a fence is "code"; "fence" for the ``` lines
def title_lines(lines: list[Line]) -> list[str]
def answer_lines(lines: list[Line]) -> list[str]
def command_lines(lines: list[Line], doc: onboard.MapDoc) -> list[str]
def paragraph_lines(lines: list[Line]) -> list[str]
def html_lines(lines: list[Line]) -> list[str]
def cite_lines(lines: list[Line]) -> list[str]
```

Behavior contract (spec 9, 10.1):

- `page_lines_of` splits on `\n`, strips a trailing `\r`, and classifies: a line of three backticks (with or without an info string) is `fence` and toggles the fence state; inside, every line is `code`; `# ` → `heading1`; `## ` (or deeper) → `heading2`; blank → `blank`; `- `, `* ` or `<digits>. ` → `list`; a line starting with `|` → `table`; `IMAGE` match → `image`; else `text`.
- `title_lines`: the first non-blank line is not `heading1` → `page: no title`; a second `heading1` → `page: second title` (once).
- `answer_lines`: the first non-blank line after the title is not a `text` line that starts with `**` → `page: no short answer`.
- `command_lines`: for each `build`, `test`, `run` of `Shape` that is not `none found`, the command is the first backtick span of the fact (`HANDLE`); the key fails as `command <key>: not in a code block` when no `code` line equals the command (stripped) or when any non-`code` line holds the command text.
- `paragraph_lines`: two consecutive `text` lines → `paragraph <n>: two lines`, `<n>` the second line, once per run of text lines.
- `html_lines`: a `text`, `list` or `table` line that holds an `HTML_TAG` match outside backtick spans → `html <n>: tag outside code`.
- `cite_lines`: a non-`code` line matching `CITE_LINE` → `cite <n>: map line on the page`.

`page.md` is the English page of `tests/fixtures/onboard/map-puml.md` written by spec 10.1 and 10.2: title question, `**Short answer.**` paragraph, the fourteen sections of 10.2 that the map supports (`Which states` present, `Which events` present with the two events, the four reference sections where the map is not `none found`, `Terms`, `Not covered`, `About this page`), four image lines `![…](diagrams/architecture.png)`, `flow-order`, `flow-cancel`, `state`, the three commands in `sh` fences, every traced and not-traced entry name, both event names, the `Not covered` text, no cite, no HTML, one line per paragraph. It lints clean.

- [ ] **Step 1: Write the fixture page and the failing tests**

`test_onboard_page.py` gains a module constant `PAGE = read("page.md")` (the `read` helper of the file), `MAP_PUML`, and a helper `lines(text) -> list[Line]`. Class `PageModelCase`:

- `test_fence_lines_are_code`: a `# x` and a `| a | b |` and an image line inside a fence are `code` (Review Focus 3).
- `test_crlf_and_trailing_spaces`: `"# T\r\n\r\n![c](diagrams/x.png)  \r\n"` gives `heading1`, `blank`, `image` (Review Focus 2).
- `test_fixture_page_has_no_structural_failure`: all six functions return `[]` on `lines(PAGE)` with `doc = parse_map(MAP_PUML)`.
- `test_no_title`, `test_second_title`, `test_no_short_answer` (the bold removed), `test_command_outside_a_code_block` (the `./gradlew build` fence removed and the command written in prose gives `command build: not in a code block`), `test_two_text_lines` (`paragraph <n>: two lines` with the planted number), `test_html_tag_outside_code` (`<br>` in a paragraph; the same tag in backticks passes), `test_cite_line_on_the_page` (a copied map line gives `cite <n>: map line on the page`).
- `test_fixture_page_lints_clean`: `ste_lint.py page.md` prints `0 errors, 0 warnings` (run as `test_rung_drift.lint` does).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard_page.PageModelCase -v`
Expected: FAIL with `AttributeError: module 'onboard_page' has no attribute 'page_lines_of'`.

- [ ] **Step 3: Implement the model and the six functions in `scripts/onboard_page.py`**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard_page -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/onboard_page.py skills/explain/tests/test_onboard_page.py skills/explain/tests/fixtures/onboard/page.md
git commit -m "feat: explain onboard: the page model, the fixture page and the structural checks of onboard.py page"
```

---

### Task 2: the diagram, image and flow-section checks

**Files:**
- Modify: `skills/explain/scripts/onboard_page.py`
- Modify: `skills/explain/tests/test_onboard_page.py`

**Interfaces:**
- Consumes: `Line`, `page_lines_of`, `IMAGE` of Task 1; `diagram_files(doc)` of wave one (`<id>` → file body).
- Produces:

```python
def image_lines(lines: list[Line], files: dict[str, str], directory: str) -> list[str]
def puml_lines(files: dict[str, str], directory: str) -> list[str]
def flow_lines(lines: list[Line], doc: onboard.MapDoc) -> list[str]
```

Behavior contract (spec 9), `directory` the `diagrams/` directory beside the page:

- `image_lines`, in this order: for each id of `files` with no `image` line whose path is `diagrams/<id>.png` → `diagram <id>: no image line`, with two or more → `diagram <id>: image line twice`; then for each `image` line in page order: a path not starting with `diagrams/` → `image <path>: not under diagrams/`; else an id (the basename without `.png`) not in `files` → `image <path>: not in the map`; else no file at `<directory>/<id>.png` → `image <path>: no file`; then for each `*.png` of `directory` (sorted) whose id has no image line → `png <id>: no image line`.
- `puml_lines`: for each id of `files` in `diagram_files` order: no `<directory>/<id>.puml` → `diagram <id>: no puml`; a body that differs from `files[id]` byte for byte → `diagram <id>: differs from the map`; then each `*.puml` of `directory` (sorted) not in `files` → `puml <id>: not in the map`.
- `flow_lines`: the flows of `Flows` in map order; a flow with no `heading2` whose text after `## ` equals its question verbatim → `flow <id>: no section`; a flow whose image line (`diagrams/flow-<id>.png`) is not after its heading and before the next `heading2` → `flow <id>: image outside its section`; the flow headings present in another order than the map → `flows: out of map order` (once).

- [ ] **Step 1: Write the failing tests**

A helper `page_dir(page=PAGE, map_text=MAP_PUML, pngs=None) -> str` in `test_onboard_page.py`: a temporary directory holding `page.md`, `map.md`, `diagrams/<id>.puml` written from `diagram_files`, and `diagrams/<id>.png` stubs (`b"\x89PNG\r\n\x1a\n"`) for every id unless `pngs` lists another set. Class `PageDiagramsCase`:

- `test_fixture_page_has_no_diagram_failure`: the three functions return `[]`.
- `test_missing_image_line`, `test_image_line_twice`, `test_image_outside_diagrams` (`![c](pictures/x.png)` → `image pictures/x.png: not under diagrams/`), `test_image_not_in_the_map` (`diagrams/flow-refund.png`), `test_image_without_a_file` (`pngs=["architecture"]` gives three `no file` lines), `test_png_without_an_image_line` (an extra `diagrams/old.png` → `png old: no image line`).
- `test_caption_with_parentheses` (Review Focus 4): `![the order flow (v2)](diagrams/flow-order.png)` passes.
- `test_puml_missing`, `test_puml_differs` (one byte changed → `diagram state: differs from the map`), `test_puml_not_in_the_map` (`diagrams/old.puml` → `puml old: not in the map`).
- `test_flow_without_a_section` (the heading of the cancel flow changed by one word → `flow cancel: no section`), `test_image_outside_its_section` (the cancel image moved under the order heading), `test_flows_out_of_map_order` (the two flow sections swapped → one `flows: out of map order` line and no `no section` line).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard_page.PageDiagramsCase -v`
Expected: FAIL with `AttributeError` on `image_lines`.

- [ ] **Step 3: Implement the three functions**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard_page -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/onboard_page.py skills/explain/tests/test_onboard_page.py
git commit -m "feat: explain onboard: the page check ties every image line to a diagram of the map and every flow to its section"
```

---

### Task 3: the name checks, `cmd_page` and the dispatch

**Files:**
- Modify: `skills/explain/scripts/onboard_page.py`
- Modify: `skills/explain/scripts/onboard.py` (`USAGE` at 21, the stdout rule and the dispatch of `main`)
- Modify: `skills/explain/tests/test_onboard_page.py`

**Interfaces:**
- Consumes: Tasks 1 and 2; `onboard._facts`, `onboard.ENTRY_KINDS`, `onboard.Section.events`.
- Produces:

```python
def name_lines(lines: list[Line], doc: onboard.MapDoc) -> list[str]
def page_lines(text: str, doc: onboard.MapDoc, directory: str) -> list[str]   # every check, spec-table order
def cmd_page(argv: list[str]) -> int                                           # onboard.py page <page.md> --map <map.md>
```

Behavior contract (spec 9):

- `name_lines`: the page text is the joined `text` of every line (code lines included). For each `Entry points` fact whose tail after the last ` -> ` is a flow id or starts with `not traced`: the name is the fact text after its kind word and before ` -> `; `entry <name>: not on the page` when the name is not a substring of the page text. For each `### <event-name>` of `Events`: `event <name>: not on the page`. For each `Not covered` fact: `not covered #<n>: not on the page` when the text before the fact's first `:` (the directory or module) is not a substring. Ruling (the spec says "whose text"): the directory or module name is the text that must appear; the reason may be rephrased.
- `page_lines`: `title_lines`, `answer_lines`, `image_lines`, `puml_lines`, `flow_lines`, `name_lines`, `command_lines`, `paragraph_lines`, `html_lines`, `cite_lines`, concatenated in this order.
- `cmd_page`: parses `<page.md>` and the required `--map <map.md>` (the usage, exit 2, through a parser like the one of `cmd_diagrams`); reads the map with `onboard.read_map` (`map: cannot read ...`, exit 2); reads the page as UTF-8, failing as `page: cannot read <path>: <reason>` with exit 2 (raised as `OnboardError`, printed on stdout by `main`); `directory` is `<dirname(page)>/diagrams` (missing directory: every image line is `no file` and every puml is `no puml`); prints the lines, then `page: ok` (exit 0) or `page: <n> failures` (exit 1).
- `onboard.main`: `"page": onboard_page.cmd_page` beside `diagrams`; the stdout rule sends a `page:` line to stdout; `USAGE` gains `       onboard.py page <page.md> --map <map.md>\n`.

- [ ] **Step 1: Write the failing tests**

Class `PageCase` (through `run`, the `onboard.main` helper, on `page_dir()`):

- `test_fixture_page_is_ok`: `(0, "page: ok\n", "")`.
- `test_entry_not_on_the_page` (`POST /orders` renamed in the entry table → `entry POST /orders: not on the page`), `test_not_an_entry_point_is_not_required` (`shop-gw` removed from the page passes), `test_event_not_on_the_page` (`orders.created` → the line), `test_not_covered_not_on_the_page` (`not covered #1: not on the page`), `test_entry_name_prefix_is_not_a_false_failure` (Review Focus 5: a page with `/orders` only inside `POST /orders` passes for both entries whose names it holds), `test_name_inside_a_fence_counts` (Review Focus 5).
- `test_russian_page_passes` (Review Focus 1): the fixture map with its two questions and the page's two flow headings translated to Russian, the short answer `**Краткий ответ.**`, gives `page: ok`.
- `test_failure_count_and_order`: a page with a removed title and a cite line prints `page: no title` first, `cite <n>: map line on the page` last, then `page: 2 failures`, exit 1.
- `test_unreadable_page_exits_2` (`page: cannot read` on stdout), `test_unreadable_map_exits_2`, `test_missing_diagrams_directory` (every id `no file` and `no puml`).
- `test_usage_names_page`: `run([])` stderr holds `onboard.py page <page.md> --map <map.md>`.
- `test_cli_runs_as_a_script`: `subprocess.run([sys.executable, "-B", "scripts/onboard.py", "page", <page>, "--map", <map>])` on `page_dir()` exits 0 with `page: ok` (the trampoline of wave one).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard_page.PageCase -v`
Expected: FAIL (`onboard.py page` is the usage, exit 2).

- [ ] **Step 3: Implement `name_lines`, `page_lines`, `cmd_page` and the dispatch**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_onboard_page tests.test_onboard tests.test_course -v 2>&1 | tail -4`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/onboard_page.py skills/explain/scripts/onboard.py skills/explain/tests/test_onboard_page.py
git commit -m "feat: explain onboard: onboard.py page checks a Markdown page against its map and its diagrams directory"
```

---

### Task 4: `rungs/onboard.md` sections 1 to 3: PlantUML forms, the check, the precheck

**Files:**
- Modify: `skills/explain/rungs/onboard.md` (sections `When an onboarding page`, `Explore the service`, `The map`)
- Modify: `skills/explain/tests/test_rung_drift.py` (`OnboardRungCase`, lines 985–1232)

**Interfaces:**
- Consumes: the failure lines of spec 7.5 (wave one), `onboard.TITLES`, `onboard.ENTRY_KINDS`.
- Produces: the rung text that Tasks 5 to 7 and the wave acceptance lint.

Behavior contract (spec 5, 7, 11):

- Section 1: after the rung line, the precheck paragraph: run `plantuml -version`; when it fails, print the rung line, say that the onboard rung needs PlantUML (`brew install plantuml`), stop, offer `page`. The `data-root` sentence goes; `<root>` stays the `--root` of the `onboard.py` commands.
- Section 2 opens with one paragraph: an onboard run draws every diagram in PlantUML in a `plantuml` fence; a course map draws Mermaid in a `mermaid` fence; the rules below name both forms. Rule 3 gives the component form of spec 7.3 (the declarations with `as <id>`, the id pattern, the arrows, `package`, the `not declared` rule) and one clause for the course map (`flowchart LR`). Rule 4 gives the activity form of spec 7.2 (`start` … `stop`, `:<label>;`, the same label twice is one node, `if`/`elseif`/`else`/`endif`, `while`, `repeat`, `switch`, `-> <label>;`, `:see <flow-id>;` + `detach`, `fork`, `partition`, the forbidden lines, the 25 labels) and one clause for `flowchart TD`. Rule 5 gives the state form of 7.4 and one clause for `stateDiagram-v2`. The backtick-keyed node fact of a flow is stated with its example lines.
- Section 3: the skeleton's three fences become `plantuml` fences holding a one-line sketch each (`component "<name>" as <id>`, `start` / `:<label>;` / `stop`, `[*] --> <STATE>`), the flow fact line reads `` - `<label>`: <fact> | ... ``; the check command is `onboard.py check map.md --root <root> --inventory inventory.txt --notation plantuml`; the prefix table keeps twelve rows and its `diagram` and `node` rows gain the forms of spec 7.5 (`not plantuml`, `not a PlantUML kind`, `not activity`, `not component`, `not state`, `action over lines <n>-<m>`, `style line <n>`, `flow <id> not in Flows`, `not declared`, `bad id`).
- Every sentence lints clean under the STE profile.

- [ ] **Step 1: Rewrite the drift tests of sections 1 to 3**

In `OnboardRungCase`: `test_when_an_onboarding_page_...` (the existing phrase test of section 1) gains `plantuml -version` and `brew install plantuml`; a new `test_explore_names_both_notations` asserts, in "Explore the service", the phrases `in a `plantuml` fence`, `in a `mermaid` fence`, `component "<name>" as <id>`, `:<label>;`, `:see <flow-id>;`, `[*] --> <STATE>`, `flowchart LR`, `flowchart TD`, `stateDiagram-v2`, `at most 25`; `test_the_map_skeleton_lists_the_titles_of_onboard_py` keeps its title assertions and adds that each skeleton fence opens with `` ```plantuml ``; `test_the_map_runs_the_check_and_names_its_prefixes` asserts the command with `--notation plantuml`, still twelve prefix rows, and the ten new forms above inside the `diagram` and `node` rows.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift.OnboardRungCase -v`
Expected: FAIL on the three changed or new tests; `test_onboard_md_lints_clean` still passes.

- [ ] **Step 3: Rewrite sections 1 to 3 of `rungs/onboard.md`**

- [ ] **Step 4: Run the tests and the lint to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift.OnboardRungCase tests.test_course_prompts -v 2>&1 | tail -4 && python3 ../ste/scripts/ste_lint.py rungs/onboard.md`
Expected: PASS and `0 errors, 0 warnings`. (`test_course_prompts` reads the two section titles of the rung; they do not change.)

- [ ] **Step 5: Commit**

```bash
git add skills/explain/rungs/onboard.md skills/explain/tests/test_rung_drift.py
git commit -m "docs: explain onboard: the rung explores and maps a service in PlantUML, with the Mermaid clause of a course map"
```

---

### Task 5: `rungs/onboard.md` sections 4 to 6: the section plan, the procedure, the output directory

**Files:**
- Modify: `skills/explain/rungs/onboard.md` (sections `Plan the sections`, `Write the page`, `Output directory`)
- Modify: `skills/explain/tests/test_rung_drift.py` (`OnboardRungCase`)

**Interfaces:**
- Consumes: the commands of wave one and Task 3 (`onboard.py diagrams map.md --out diagrams`, `puml.py render diagrams`, `onboard.py page page.md --map map.md`).
- Produces: the rung text the live run of wave three follows.

Behavior contract (spec 6, 10):

- Section 4 is the fourteen-item plan of spec 10.2, in its order and wording (the Markdown headings in backticks, the `**Short answer.**` paragraph of two to four sentences and at most 70 words, one section per flow in map order with the question as its heading, the events matrix as a pipe table with cells `E`, `C`, `E C` or `(C)` and a last column `gaps` when a `none found` line exists, the omissions, the `Terms`, `Not covered` and `About this page` tables), with the rules of 10.1 before it (ATX headings, one line per paragraph, pipe tables, fenced commands with an info string, one image line alone with its caption sentence, bold only for the short-answer label, no HTML, no link inside the page). "never merge flows" stays. The HTML vocabulary (`#whole`, `.table-wrap`, `figure.code`, `div.cites`, `details.walk`, `<wbr>`, `aria-label`, `data-root`) goes.
- Section 5 is the eight steps of spec 10.3, verbatim in substance: the check with `--notation plantuml` until `onboard: ok`; `diagrams` then `render` until `plantuml: ok <n> diagrams`, a `plantuml: FAIL` fixed in the map fence; each PNG read with the Read tool for a cut label, a label over a line, a condition without an outcome label, an empty branch, a false picture; `page.md` by 10.1 and 10.2; `onboard.py page page.md --map map.md` until `page: ok`; `ste_lint.py page.md` until `0 errors`; the three reads (the answer alone, the architecture picture, the entry table against `inventory.txt`); the handoff that prints the path and runs `open <output-dir>`, never inside a subagent.
- Section 6 holds the directory name and the five-row table of spec 6 (`map.md`, `inventory.txt`, `diagrams/<id>.puml`, `diagrams/<id>.png`, `page.md`) and the sentence "No `index.html`, no snapshots, no `review/`."

- [ ] **Step 1: Rewrite the drift tests of sections 4 to 6**

`test_plan_the_sections_...` (the existing phrase test of section 4) asserts the full phrases `**Short answer.**`, `at most 70 words`, `## What is <service> made of?`, `## How do I build, test and run it?`, `## Where does a message enter?`, `## Which states does a message go through?`, `## Which events move through <service>?`, `## How is the code written?`, `## Where do I look to change something?`, `## Terms`, `## Not covered`, `## About this page`, `a last column `gaps` when a `none found` line exists`, `never merge flows`, `![<caption>](diagrams/<id>.png)` and asserts that `.table-wrap`, `div.cites`, `details.walk` and `data-root` are absent from the section. `test_write_the_page_reuses_page_md_and_the_two_scripts` becomes `test_write_the_page_runs_the_four_checks_in_order` asserting, in order of appearance, `--notation plantuml`, `onboard: ok`, `onboard.py diagrams map.md --out diagrams`, `puml.py render diagrams`, `plantuml: ok <n> diagrams`, `Read tool`, `onboard.py page page.md --map map.md`, `page: ok`, `ste_lint.py page.md`, `0 errors`, `inventory.txt`, `open <output-dir>`, `Never run `open` inside a subagent`. `test_write_the_page_points_at_titles_that_page_md_has` is removed (the section no longer points at `page.md`). `test_output_directory_lists_the_rows_of_spec_4` asserts the five rows and the sentence above.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift.OnboardRungCase -v`
Expected: FAIL on the three changed tests.

- [ ] **Step 3: Rewrite sections 4 to 6**

- [ ] **Step 4: Run the tests and the lint to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift -v 2>&1 | tail -4 && python3 ../ste/scripts/ste_lint.py rungs/onboard.md`
Expected: PASS and `0 errors, 0 warnings`.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/rungs/onboard.md skills/explain/tests/test_rung_drift.py
git commit -m "docs: explain onboard: the rung plans the Markdown page, runs the four checks and lists the new output directory"
```

---

### Task 6: `SKILL.md` and `README.md`

**Files:**
- Modify: `skills/explain/SKILL.md` (the rung table row at 69, the rung bullet at 87, the Conventions 1 to 6, the Build procedure step 2, the Rung files bullet at 189)
- Modify: `README.md` (lines 18–22, 70, 102)
- Modify: `skills/explain/tests/test_rung_drift.py` (`ONBOARD_ROW` at 1236 and `SkillMdCase`). No repo-root test under `tests/` quotes the README's onboard lines (`grep -rln onboard tests/` prints nothing), so the README changes get no new test; the repo-root suite only has to stay green.

**Interfaces:**
- Consumes: nothing from code.
- Produces: the skill text of spec 12.

Behavior contract (spec 12), exact copy:

- `ONBOARD_ROW`: `| `onboard` (Markdown page from a checked map, directory output) | Forced only (`--as onboard`). A service to onboard to: its architecture and every flow | One service directory |`.
- The rung bullet: `The `onboard` rung builds one Markdown page for one service from its map, with PlantUML diagrams rendered to PNG. Only `--as onboard` selects it. The onboard rung is English or Russian.`
- The Rung files bullet names the map and its check, the PlantUML diagrams, the Markdown page and its check.
- Conventions, one sentence each, in the convention's text: 1 `For the `onboard` rung, the page is `page.md` and passes `ste_lint.py` without `--html`.`; 2 `For the `onboard` rung, the cites live in the map and the page holds none.`; 3 `For the `onboard` rung, the artifact is the output directory (`page.md` and `diagrams/*.png`).`; 4 `For the `onboard` rung, the checks are `onboard.py check`, `puml.py render`, `onboard.py page` and the lint.`; 6 `For the `onboard` rung, the handoff opens the output directory.` Build procedure step 2: `For an onboarding page, the rung file replaces steps 3 to 6.`
- `README.md`: the `--as onboard` clause reads "an onboarding page (`--as onboard`: one service directory, explored by the onboarding rules into a map that `onboard.py check` verifies, then a Markdown page for Confluence with its architecture, every entry point and every flow as PlantUML diagrams rendered to PNG; the page holds no cites, the map does)"; the requirements row is `| `onboard` | `python3`, and `plantuml` on `PATH` (Homebrew); no Chrome |`; the structure line is `scripts/{onboard,onboard_page,puml,mermaid_svg}.py,`.
- `SKILL.md` lints clean.

- [ ] **Step 1: Write the failing tests**

`SkillMdCase.test_skill_md_routes_the_onboard_rung`: exactly one row equal to `ONBOARD_ROW`; the rung bullet sentence (flattened); the five convention sentences and the step-2 sentence; the Rung files bullet holds `page.md` and `PlantUML`. The README has no test (see Files above); its three edits are reviewed by eye against the exact copy of the contract.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift.SkillMdCase -v`
Expected: FAIL on the new test.

- [ ] **Step 3: Edit `SKILL.md` and `README.md`**

- [ ] **Step 4: Run the tests and the lint to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_rung_drift -v 2>&1 | tail -4 && python3 ../ste/scripts/ste_lint.py SKILL.md && cd ../.. && python3 -B -m unittest discover -s tests 2>&1 | tail -3`
Expected: PASS, `0 errors, 0 warnings`, and the repo-root suite OK.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/SKILL.md README.md skills/explain/tests/test_rung_drift.py
git commit -m "docs: explain onboard: SKILL.md and README say the rung writes a Markdown page with PlantUML diagrams"
```

---

### Task 7: the course keeps Mermaid

**Files:**
- Modify: `skills/explain/course/map-task.md` (the check command at 35 and a new override bullet)
- Modify: `skills/explain/rungs/course.md` (the check command at 94)
- Modify: `skills/explain/tests/test_course_prompts.py` (`MAP_TASK_COMMANDS` at 75–78, `MAP_OVERRIDES` at 80–90, `MAP_CHECK_COMMAND` at 171)

**Interfaces:**
- Consumes: `--notation mermaid` of wave one.
- Produces: nothing downstream.

Behavior contract (spec 11): the `map-task.md` check command ends with `--notation mermaid`; the overrides gain the bullet `Draw each diagram as Mermaid, in a `mermaid` fence: `flowchart LR`, `flowchart TD` and `stateDiagram-v2`, as "Explore the service" says for a course map. The PlantUML rules of an onboard run do not apply: the lessons render Mermaid.`; the orchestrator's command in `rungs/course.md` ends with `--notation mermaid`; `course.py` and `lesson-task.md` are untouched; both files lint clean.

- [ ] **Step 1: Update the prompt tests**

`MAP_TASK_COMMANDS[1]` and `MAP_CHECK_COMMAND` end with ` --notation mermaid`; `MAP_OVERRIDES` gains the bullet text; `test_rung_quotes_every_course_command` thereby asserts the course rung command.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_course_prompts -v 2>&1 | tail -4`
Expected: FAIL on the command and override tests.

- [ ] **Step 3: Edit the two files**

- [ ] **Step 4: Run the tests and the lint to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_course_prompts tests.test_course -v 2>&1 | tail -4 && python3 ../ste/scripts/ste_lint.py course/map-task.md && python3 ../ste/scripts/ste_lint.py rungs/course.md`
Expected: PASS and `0 errors, 0 warnings` twice.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/course/map-task.md skills/explain/rungs/course.md skills/explain/tests/test_course_prompts.py
git commit -m "docs: explain onboard: the course map task and the course rung check with --notation mermaid"
```

---

### Task 8: remove the HTML onboarding path

**Files:**
- Modify: `skills/explain/scripts/verify.sh` (header comment lines 8–9 and 28, the case at 325 and the usage at 328)
- Modify: `skills/explain/scripts/bpmn.py` (`USAGE` at 32–36, `RUNGS` at 37, the docstring at 7)
- Modify: `skills/explain/templates/page.html` (the `table.matrix` rules at 234–256 and their comment)
- Modify: `skills/explain/tests/test_verify.py` (the import at 28, the three onboard tests at 375–409), `skills/explain/tests/test_bpmn_check.py` (the import at 21, the two tests at 284–294, the docstring of `test_unknown_rung_is_usage`), `skills/explain/tests/test_page_template.py` (the import at 44, `test_matrix_rules_exist_and_keep_the_floor`, `measure`, `stress_page`, `test_matrix_of_a_real_service_fits_at_1440_and_scrolls_inside_its_wrapper_at_500`, `test_onboard_events_section_passes_the_guard_without_page_hscroll`, and the measure script constant they share when nothing else uses it)
- Delete: `skills/explain/tests/onboard_html_page.py`, `skills/explain/tests/fixtures/onboard-page/`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing; the wave acceptance greps.

Behavior contract (spec 12): `verify.sh` with `content="onboard"` exits 2 with the usage naming `sheet, page, video, lesson or course`; `bpmn.py check --rung onboard` is a usage error (exit 2); the template has no `matrix` rule; no file of `skills/explain` mentions `onboard_html_page` or `onboard-page`; every remaining test of the three modules passes.

- [ ] **Step 1: Change the tests first**

`test_verify.test_onboard_rung_renders_the_page_viewports` becomes `test_onboard_rung_is_unknown` (exit 2, stderr holds `expected sheet, page, video, lesson or course`); `test_bpmn_check.test_unknown_rung_is_usage` adds `onboard` to the rejected rungs; the other onboard and matrix tests and the two imports are deleted.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_verify.VerifyTest.test_onboard_rung_is_unknown tests.test_bpmn_check -v 2>&1 | tail -4`
Expected: FAIL (onboard still accepted).

- [ ] **Step 3: Remove the code, the rules, the helper and the fixture directory**

- [ ] **Step 4: Run the tests and the greps to verify**

Run: `cd skills/explain && python3 -B -m unittest tests.test_verify tests.test_bpmn_check tests.test_page_template -v 2>&1 | tail -4 && grep -rn "onboard" scripts/verify.sh scripts/bpmn.py templates/page.html; grep -n "table.matrix" templates/page.html; grep -rln "onboard_html_page\|onboard-page" . `
Expected: PASS (skips where Chrome or the Mermaid bundle is absent) and three empty greps.

- [ ] **Step 5: Commit, then run the wave acceptance**

```bash
git add -A skills/explain/scripts/verify.sh skills/explain/scripts/bpmn.py skills/explain/templates/page.html skills/explain/tests
git commit -m "chore: explain onboard: remove the HTML onboarding path (verify.sh, bpmn.py, the page helper, the matrix rules and their tests)"
```

Run:

```bash
cd skills/explain && python3 -B -m unittest discover -s tests 2>&1 | tail -3
python3 -B -m unittest discover -s tests 2>&1 | tail -3
cd skills/explain && python3 ../ste/scripts/ste_lint.py rungs/onboard.md && python3 ../ste/scripts/ste_lint.py course/map-task.md && python3 ../ste/scripts/ste_lint.py SKILL.md
```

Expected: no failure beyond the four baseline failures in the explain suite; the repo-root suite OK; `0 errors, 0 warnings` three times.
