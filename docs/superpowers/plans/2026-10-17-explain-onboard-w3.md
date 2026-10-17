# explain onboard, wave 3 (onboard-rung) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/explain <service-dir> --as onboard` is the eighth rung: `rungs/onboard.md` holds the onboarding rules, the map, the section plan of spec 9.1 and the output directory; `SKILL.md` and `README.md` name the rung; `verify.sh` renders `rung=onboard` at the two page viewports and `bpmn.py` accepts the rung; the drift tests pin all of it.

**Architecture:** No new script. The rung is a page (the page template, the two page viewports, the six page lines and `bpmn` last), so `verify.sh` and `bpmn.py` each gain one name. The new rung file teaches the procedure that waves 1 and 2 made checkable: it names the inventory and check commands of `onboard.py`, quotes the map skeleton of spec 6, carries the section plan of spec 9.1 and points at the four page sections it reuses from `rungs/page.md`. A fixture onboard page (the page template with meta `onboard` and one `figure.mermaid` filled by `mermaid_svg.py inline`) proves the verify path end to end. `test_rung_drift.py` ties the rung text to `onboard.TITLES` and `onboard.PATTERNS`, so the rung cannot describe a map that the check refuses.

**Tech Stack:** Python 3.14 stdlib, `unittest`, bash (`verify.sh`), headless Google Chrome, the `mermaid.min.js` bundle (already in place), the STE lint.

**Spec:** `docs/superpowers/specs/2026-10-16-explain-onboard-design.md` (sections 3, 4, 5, 6, 7, 9.1, 12 and 13). Wave map: `docs/superpowers/waves/2026-10-16-explain-onboard.yaml`, wave `onboard-rung`. Coverage: waived.

Base: 1f8a7b70e132917d1178ebab4a7cea64fa097f75
Test runs: scoped per task; full suite once, final task.

All paths below are relative to `skills/explain/` unless they start with `docs/` or are `README.md` (the repository root). Every test command runs from `skills/explain/`; every lint command runs from the repository root.

## Global Constraints

- The eight `--as` names, in this order, everywhere they are listed: `ste|sheet|page|video|brainrot|lesson|course|onboard`. `SKILL.md` step 4 says "List these eight names in the error."; the conventions sentence lists seven artifact rungs: `sheet`, `page`, `video`, `brainrot`, `lesson`, `course`, `onboard`.
- An onboard page is a page: `<meta name="explain-rung" content="onboard">`; `verify.sh` renders `1440x900` and `500x844`, prints the six page lines (`self-contained`, `render 1440x900`, `render 500x844`, `citations`, `prose`, `bpmn`) and no `media` line; its usage message reads `(expected sheet, page, video, lesson, course or onboard)`. `bpmn.py check --rung onboard` applies the four conditions of a page; `bpmn.RUNGS` is `("sheet", "page", "lesson", "course", "onboard")`.
- The rung line, verbatim: `Rung: onboard (forced) — <reason> — subject: <path> (directory)`. Only `--as onboard` selects the rung. `--review` prints `--review: no effect on onboard` (the rule of `SKILL.md` Contract step 2; no change there). The rung is English or Russian.
- The output directory is `~/karpathy/out/YYYY-MM-DD-HHMMSS-onboard-<slug>/` with exactly the rows of spec section 4: `map.md`, `inventory.txt`, `diagrams/<id>.mmd`, `diagrams/<id>.svg`, `index.html`, and `page.png`, `narrow.png`, `review/`.
- The map and its check are wave 2's and do not change: the ten titles are `onboard.TITLES`, the kinds are the keys of `onboard.PATTERNS` (`http`, `listener`, `route`, `schedule`, `main`), the commands the rung quotes are `python3 <skill-dir>/scripts/onboard.py inventory <service-dir> --root <root> --out inventory.txt` and `python3 <skill-dir>/scripts/onboard.py check map.md --root <root> --inventory inventory.txt`, the summary lines `inventory: <n> entry points` and `onboard: ok` / `onboard: <n> failures`, the failure prefixes those of spec section 7.
- The Mermaid pattern is wave 1's and does not change: `<figure class="mermaid" data-src="diagrams/<id>.mmd">` with a `<figcaption>`, filled by `python3 <skill-dir>/scripts/mermaid_svg.py inline index.html`, last line `mermaid: ok <n> diagrams`.
- The section ids of spec 9.1: `#whole`, `#entry`, `flow-<flow-id>` (one per flow, never merged), `#state` (omitted when `State` is `none found`), `#formats`, `#config`, `#errors`, `#systems`, `#terms`; `Not covered` in the footer. The diagram files are `diagrams/architecture.mmd`, `diagrams/flow-<flow-id>.mmd` and `diagrams/state.mmd`, each the fenced block of the map copied verbatim.
- `<root>` of an onboard run is the repo root of the service directory (`git rev-parse --show-toplevel` run in it), or the service directory when that fails. It is the `--root` of both `onboard.py` commands and the `data-root` of the page; every cite path is relative to it.
- Lint: `rungs/onboard.md` and `SKILL.md` lint clean: `python3 skills/ste/scripts/ste_lint.py <file>` prints `0 errors, 0 warnings`. The STE profile (`skills/ste/SKILL.md`): a procedural sentence has at most 20 words, a descriptive one at most 25, no `-ing` verb forms, no passive in procedures, the substitution table applies; headings and inline code are not counted as prose (code counts as one word).
- Chrome tests skip with `mermaid bundle missing: <path>` when the bundle is absent; no test touches the network. Stdlib only. Never commit `out/`.
- This wave changes no file that another wave owns: not `scripts/onboard.py`, `scripts/mermaid_svg.py`, `scripts/cite_check.py`, `scripts/course.py`, `rungs/page.md`, `rungs/course.md`, `course/*.md`, `templates/page.html`. Convention 6 of `SKILL.md` keeps its parenthetical `(sheet, page, lesson or course)` (spec 12 does not list it; the rung file carries its own handoff step, and two existing drift pins hold the text).
- Commit style of this repository: `feat: explain: …`, `test: explain: …`, `docs: explain: …`.

## Review Focus

1. `verify.sh` gains the `rung=onboard` case but its usage message keeps the five old names: a page with a typo in its meta gets a message that lies about the accepted rungs. Expected: the message lists six names; pinned by the two unknown-rung tests of Task 1.
2. `bpmn.py` keeps `RUNGS` at four names: `verify.sh` passes `--rung onboard`, `bpmn.py` exits 2 and every onboard page fails with `bpmn: FAIL bpmn exit 2` (spec 12). Expected: `bpmn: ok` on a page with BPMN cites, `bpmn: none` on one without; pinned in Task 1 and Task 2.
3. The map skeleton of `rungs/onboard.md` drifts from `onboard.TITLES` (a capital letter, a reordered title): every map an author writes from the rung fails with `section: missing <title>`. Expected: the `## ` lines of the skeleton equal `onboard.TITLES` in order; pinned in Task 3.
4. `rungs/page.md` says "If a page has more than about twelve sections, merge facets": an author who follows it merges two flow sections, which is the flattening the user named. Expected: the onboard plan says never merge flows; pinned in Task 3.
5. `SKILL.md` step 4 lists the names but the hint, the syntax line or the count word stays at seven: the router rejects `--as onboard` or names a stale set in its error. Expected: the names of step 4, the hint and `README.md` are the same eight; pinned in Task 4.

## File structure

- `scripts/verify.sh`: the `case "$rung_line"` block (one line), the usage text of its `*)` arm, the header comment (the exit-0 line counts and the viewport sentence).
- `scripts/bpmn.py`: `RUNGS`, `USAGE` and the module docstring (`[--rung sheet|page|lesson|course|onboard]`).
- `tests/onboard_page.py` (new): `onboard_page(out, section=None) -> Path`, the onboard twin of `tests/mermaid_page.py`.
- `tests/fixtures/onboard-page/section.html`, `tests/fixtures/onboard-page/order.mmd` (new): two onboard-shaped sections and the `order` flow of the wave-2 fixture map.
- `rungs/onboard.md` (new): six level-2 sections, `1.` to `6.`: `When an onboarding page`, `Explore the service`, `The map`, `Plan the sections`, `Write the page`, `Output directory`.
- `SKILL.md`: the argument-hint, the Contract (syntax line, step 4), the rung table (one row), the rung rules (one bullet), the conventions sentence, the Rung files list (one bullet). `README.md`: the `--as` list and one clause, the Requirements table (one row), the Layout block.
- `tests/test_verify.py`, `tests/test_bpmn_check.py` (the new rung); `tests/test_rung_drift.py` (`OnboardRungCase` new; `AS_NAMES`, `ONBOARD_ROW` and the `SkillMdCase` pins).

---

### Task 1: `verify.sh` and `bpmn.py` accept the onboard rung

**Files:**
- Modify: `scripts/verify.sh` (the header comment, the `case "$rung_line"` block)
- Modify: `scripts/bpmn.py` (the docstring, `USAGE`, `RUNGS`)
- Modify: `tests/test_verify.py`, `tests/test_bpmn_check.py`

**Interfaces:**
- Consumes: nothing of this wave.
- Produces: `verify.sh` treats `rung=onboard` as a page (viewports `1440x900 500x844`, no media line, `bpmn` last) and its usage message names six rungs; `bpmn.py check --rung onboard <index.html>` runs the four page conditions.
  ```python
  # scripts/bpmn.py
  RUNGS = ("sheet", "page", "lesson", "course", "onboard")
  ```

- [ ] **Step 1: Write the failing tests**

In `tests/test_verify.py`, after `test_lesson_rung_renders_the_page_viewports`:
- `test_onboard_rung_renders_the_page_viewports`: `verify-good.html` with `content="sheet"` replaced once by `content="onboard"` → exit 0, `stdout == LESSON_PASS + BPMN_NONE` (the six lines, no `render 1920x1080`, no `media`), `assert_no_chrome_left()`.
- `test_unknown_rung_is_a_usage_error` and `test_unknown_rung_message_lists_lesson`: the expected text becomes `(expected sheet, page, video, lesson, course or onboard)`.

In `tests/test_bpmn_check.py`, beside `test_unknown_rung_is_usage`:
- `test_onboard_rung_is_a_page`: `check --rung onboard` on `bpmn_page(self.out)` → `(0, "bpmn: ok\n")`; on `bpmn_page(self.out, self.one_cite_section())` → exit 1 and the line `page | plane | Collaboration_1 (Collaboration_1) has no svg.bpmn` (conditions 1 and 2 apply, as for `page`).
- `test_unknown_rung_is_usage`: the stderr of the `video` run holds `--rung sheet|page|lesson|course|onboard`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -B -m unittest tests.test_verify tests.test_bpmn_check -k onboard -k unknown_rung -v`
Expected: the onboard tests fail (verify exit 2 `unknown rung "onboard"`; bpmn exit 2 usage); the unknown-rung tests fail on the old message text.

- [ ] **Step 3: Add the rung to `verify.sh` and `bpmn.py`**

- `verify.sh`: one arm `rung=onboard) viewports="1440x900 500x844" ;;` after the `course` arm; the `*)` arm reads `(expected sheet, page, video, lesson, course or onboard)`; the header comment adds `onboard: six` to the exit-0 line and the onboarding page to the two-render-lines sentence. The media check stays `lesson` and `course` only.
- `bpmn.py`: `RUNGS` as above; the docstring usage and `USAGE` read `[--rung sheet|page|lesson|course|onboard]`. `cmd_check` does not change (`check_page(html, html_dir, rung == "sheet")`).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -B -m unittest tests.test_verify tests.test_bpmn_check -k onboard -k unknown_rung -v`
Expected: all `ok`; then `python3 -B -m unittest tests.test_bpmn_check` all `ok`.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/verify.sh skills/explain/scripts/bpmn.py skills/explain/tests/test_verify.py skills/explain/tests/test_bpmn_check.py
git commit -m "feat: explain: verify.sh and bpmn.py accept the onboard rung"
```

---

### Task 2: A fixture onboard page passes `verify.sh` with the six page lines and `bpmn: none`

**Files:**
- Create: `tests/onboard_page.py`, `tests/fixtures/onboard-page/section.html`, `tests/fixtures/onboard-page/order.mmd`
- Modify: `tests/test_verify.py`, `tests/test_bpmn_check.py`

**Interfaces:**
- Consumes: Task 1; `tests/mermaid_page.py` (the edit-by-anchor pattern); `onboard.read_map(path) -> MapDoc` and `MapDoc.section(title)` (wave 2); `mermaid_svg.bundle_path() -> Path` (wave 1).
- Produces:
  ```python
  # tests/onboard_page.py
  FIXTURES: Path                      # tests/fixtures/onboard-page
  PAGE_TEMPLATE: Path                 # templates/page.html
  NAV = (("entry", "Entry"), ("flow-order", "Order"))   # (section id, nav text), in page order
  def onboard_page(out: Path, section: str | None = None) -> Path   # out/index.html
  ```

- [ ] **Step 1: Write the fixtures**

- `tests/fixtures/onboard-page/order.mmd`: the body of the `order` flow block of `tests/fixtures/onboard/map.md` (from its `flowchart TD` line to its last edge), one trailing newline, nothing else.
- `tests/fixtures/onboard-page/section.html`: two sections of the shape of spec 9.1. `<section id="entry">` with `<h2>Where does a message enter?</h2>`, one `<p>` of STE prose, its `div.cites` with one `<cite>` of `diagrams/order.mmd` line 1 (snippet `flowchart`, visible text `order.mmd:1 <code>flowchart</code>`), and a `.table-wrap > table` with the header row kind, name, flow and one row `http`, `POST /orders`, `<a href="#flow-order">order</a>`. `<section id="flow-order">` with `<h2>What happens to a new order?</h2>`, one lead `<p>`, the same cite block, and `<figure class="mermaid" data-src="diagrams/order.mmd">` with a one-sentence `<figcaption>`. Every `<p>` and `<figcaption>` passes the STE lint (`verify.sh` runs it).

- [ ] **Step 2: Write `onboard_page`**

`onboard_page(out, section=None)` writes `out/index.html` from `templates/page.html` and copies `order.mmd` to `out/diagrams/order.mmd`: the section text (default `section.html`) goes before `<section id="provenance-facet">`, one `<a href="#<id>"><text></a>` per `NAV` entry goes before `<a href="#provenance-facet">Provenance</a>`, and `<meta name="explain-rung" content="page">` becomes `content="onboard"`. Each anchor must occur exactly once in the template (`AssertionError` otherwise, as `mermaid_page` does). `data-root="."` and `data-kind="topic"` stay: the template's demo sections carry no cites, and `cite_check.py` asks every section for a cite under `file` and `directory` only.

- [ ] **Step 3: Write the failing tests**

In `tests/test_verify.py` (add `MERMAID_PY`, put `scripts/` on `sys.path`, import `mermaid_svg`, `onboard` and `onboard_page`; `HAVE_BUNDLE` / `NO_BUNDLE` as in `tests/test_mermaid_svg.py`):
- `test_onboard_fixture_page_prints_six_ok_lines_and_bpmn_none` (`skipUnless(HAVE_BUNDLE, NO_BUNDLE)`): `onboard_page(<root>/onboard)`; `[sys.executable, MERMAID_PY, "inline", <page>]` with `TMPDIR=<tmp>/` → exit 0, last stdout line `mermaid: ok 1 diagrams`; `run_verify(<page>)` → `(0, LESSON_PASS + BPMN_NONE)`; `assert_no_chrome_left()`.
- `test_onboard_fixture_diagram_is_the_order_flow_of_the_fixture_map`: `read_map(tests/fixtures/onboard/map.md).section("Flows").flows[0]` has `ident == "order"` and its first diagram's `text.rstrip("\n")` equals `order.mmd` read and `rstrip("\n")`-ed.

In `tests/test_bpmn_check.py`:
- `test_onboard_page_without_a_bpmn_cite_is_none`: `run(["check", "--rung", "onboard", str(onboard_page(self.out))])` → `(0, "bpmn: none\n")`.

- [ ] **Step 4: Run the tests to verify they fail, then pass**

Run: `python3 -B -m unittest tests.test_verify tests.test_bpmn_check -k onboard -v`
Expected before the fixtures exist: `ImportError` or `FileNotFoundError`; after Steps 1 and 2: all `ok` (the inline test skips only when the bundle is absent).

- [ ] **Step 5: Commit**

```bash
git add skills/explain/tests/onboard_page.py skills/explain/tests/fixtures/onboard-page skills/explain/tests/test_verify.py skills/explain/tests/test_bpmn_check.py
git commit -m "test: explain: a fixture onboard page passes verify.sh with the six page lines and bpmn: none"
```

---

### Task 3: `rungs/onboard.md` and its drift pins

**Files:**
- Create: `rungs/onboard.md`
- Modify: `tests/test_rung_drift.py` (`ONBOARD_MD`, `ONBOARD_TITLES`, `OnboardRungCase`)

**Interfaces:**
- Consumes: `onboard.TITLES: tuple[str, ...]`, `onboard.PATTERNS: dict[str, tuple]` (wave 2; import with `scripts/` on `sys.path`); the helpers `read`, `headings`, `section`, `limits_table`, `lint` of `tests/test_rung_drift.py`.
- Produces: `rungs/onboard.md` whose level-2 titles (numbers stripped by `section`) are, in order:
  ```python
  ONBOARD_TITLES = ("When an onboarding page", "Explore the service", "The map", "Plan the sections",
                    "Write the page", "Output directory")
  ```
  Wave 4's `map-task.md` names "Explore the service" and "The map" by title.

- [ ] **Step 1: Write the failing tests**

`OnboardRungCase` in `tests/test_rung_drift.py`, each section read as one line of words (`" ".join(section(...).split())`) as `MermaidRungCase` does:
- `test_the_headings_of_onboard_md`: the level-2 titles of the file equal `ONBOARD_TITLES`; the first line is `# Rung: onboard`.
- `test_when_section_holds_the_command_the_subject_rule_and_the_rung_line`: "When an onboarding page" holds `/explain <service-dir> --as onboard`, `Rung: onboard (forced) — <reason> — subject: <path> (directory)`, `Only \`--as onboard\` selects it`, `one directory`, `Offer \`page\``, `--review: no effect on onboard`, `English or Russian`, `git rev-parse --show-toplevel`.
- `test_explore_runs_the_inventory_and_lists_the_kinds_of_onboard_py`: "Explore the service" holds `onboard.py inventory <service-dir> --root <root> --out inventory.txt` and `inventory: <n> entry points`; `limits_table(ONBOARD_MD, "| Kind | Finds |")` has the keys `` `http` ``, `` `listener` ``, `` `route` ``, `` `schedule` ``, `` `main` `` in order, equal to `["`%s`" % k for k in onboard.PATTERNS]`.
- `test_explore_holds_the_seven_rules_in_order`: the words `Shape first`, `Inventory`, `Architecture`, `Flows`, `State`, `Formats and transforms`, `Not covered` appear in this order; the flow rules name `decision node`, `at most 25 nodes`, `<flow>-<stage>` and `see <flow-id>`.
- `test_the_map_skeleton_lists_the_ten_titles_of_onboard_py`: the first fenced block of "The map" starts with `# Map: <id>` and its lines that start with `## ` equal `["## " + t for t in onboard.TITLES]`.
- `test_the_map_runs_the_check_and_names_its_prefixes`: "The map" holds `onboard.py check map.md --root <root> --inventory inventory.txt`, `onboard: ok`, `onboard: <n> failures`; `limits_table(ONBOARD_MD, "| Prefix | Meaning |")` has seven rows whose keys start with `` `section: ``, `` `diagram ``, `` `node ``, `` `cite ``, `` `entry ``, `` `inventory `` and `` `map: cannot read ``.
- `test_plan_the_sections_follows_spec_9_1`: "Plan the sections" holds `#whole`, `#entry`, `flow-<flow-id>`, `#state`, `#formats`, `#config`, `#errors`, `#systems`, `#terms`, `.table-wrap > table`, `diagrams/architecture.mmd`, `diagrams/flow-<flow-id>.mmd`, `diagrams/state.mmd`, `see <flow-id>`, `none found`, `never merge flows`, `Not covered`, `at least one \`<cite>\``, `is not printed`.
- `test_write_the_page_reuses_page_md_and_the_two_scripts`: "Write the page" holds `"Fill the template"`, `"Provenance"`, `"Write the prose"`, `"Verify and export"`, `<meta name="explain-rung" content="onboard">`, `data-kind="directory"`, `mermaid_svg.py inline index.html`, `mermaid: ok <n> diagrams`, `bpmn: none`, `inventory.txt`, `open index.html`, `Never run \`open\` inside a subagent`.
- `test_output_directory_lists_the_rows_of_spec_4`: "Output directory" holds `~/karpathy/out/YYYY-MM-DD-HHMMSS-onboard-<slug>/`; `limits_table(ONBOARD_MD, "| Path | Holds |")` keys equal `["`map.md`", "`inventory.txt`", "`diagrams/<id>.mmd`", "`diagrams/<id>.svg`", "`index.html`", "`page.png`, `narrow.png`, `review/`"]`.
- `test_onboard_md_lints_clean`: `lint(ONBOARD_MD)` → `(0, "0 errors, 0 warnings\n")`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -B -m unittest tests.test_rung_drift -k OnboardRungCase -v`
Expected: every test fails (`FileNotFoundError` on `rungs/onboard.md`).

- [ ] **Step 3: Write `rungs/onboard.md`**

The file opens as the other rung files do (`# Rung: onboard`, then "This file holds only what is specific to the onboard rung. `SKILL.md` has the generic rules."). `<skill-dir>/scripts/onboard.py <command>` may be shortened to `onboard.py <command>` after one sentence that says so, as `course.md` does. The sections:

1. **When an onboarding page**: spec section 3. Forced only; the command; the subject is one directory (a file, `this` or a topic: print the rung line, say that the onboard rung takes one directory, offer `page`, stop); `--review` prints `--review: no effect on onboard`; English or Russian by the rule of the page rung (another language: print the rung line, say so, stop, offer `page`); the rung line in a fenced block; the definition of `<root>` (Global Constraints) and that it is both `--root` and `data-root`.
2. **Explore the service**: spec section 5, the seven rules in order and numbered, each with its substance: shape (the four facts); inventory (the command, read its lines, a hit can be false and an entry point can be missing, dismiss with a reason); architecture (`flowchart LR`, the parts, one cited fact per node, a utility class is not a part); flows (`flowchart TD`, one per entry point or group, trace to each exit, the five rules: a branch in the code is a decision node with one labelled edge per outcome and an error exit is a node, each node has one cited fact and which line it cites, a node that calls another system names it and the handle, at most 25 nodes and the `<flow>-<stage>` split, `see <flow-id>` for a method another flow drew); state (`stateDiagram-v2`, one fact per state from the line that sets it, `none found`); the four fact sections and the error-paths list rule; not covered. Then the reading rules that stay from `map-task.md` (read only, change nothing, no build or test, cite only a line read from disk, no secret in a snippet, CodeGraph first when `.codegraph/` exists, `grep -rn` for a name) and the reading budget paragraph (what leaves the map is capped, what a reason to not trace looks like). The kinds table `| Kind | Finds |`, one row per key of `PATTERNS` in table order, the cell in words (the annotations, router calls, listeners, Camel routes and gRPC, schedulers, main functions), no regular expression.
3. **The map**: spec section 6. The skeleton as one fenced block, copied verbatim from the spec (the `# Map: <id>` line, the ten `## ` sections, the `### <flow-id>: <question>` heading, the line shapes of each section). The format rules as a list (the fact line, the node fact line, the ids, the diagram block, the 25-node cap, `none found` in the three sections, the entry line endings, the inventory rule, the `Other systems` shape with handles in backticks). The check: the command, "fix each line and run the check again until it prints `onboard: ok`", the prefix table `| Prefix | Meaning |` with the seven rows of spec section 7 and the exit codes. One sentence that the map is for the author, not for a reader, and its prose is not linted.
4. **Plan the sections**: spec section 9.1 as a list, in place of "Plan the sections" of `page.md`: the title and the answer box from `Shape`; `#whole` with `diagrams/architecture.mmd` and one paragraph per other system and store; `#entry` as a `.table-wrap > table` with one row per traced or not-traced entry line (kind, name, the flow as a link to its section or "not traced" with the reason), dismissed lines stay in the map; one section per flow with id `flow-<flow-id>`, its `<h2>` the question of the flow, the lead paragraph, `diagrams/flow-<flow-id>.mmd`, one paragraph per decision node (its branches and why) and per node that calls another system or writes a store, one sentence with a link for a `see <flow-id>` node; `#state` with `diagrams/state.mmd` and one paragraph per state, omitted when `State` is `none found`; `#formats`, `#config`, `#errors` (a list with a link to the flow section of each item) and `#systems` (a table of system and handles), exact rules in `details.walk`; `#terms` by the page rule; `Not covered` in the footer (each `Not covered` line of the map, each not-traced entry point with its reason); every section holds at least one `<cite>`, the cites are the map lines copied; the section count follows the flows, never merge flows to get under twelve sections; no steps player is required and the line `<n> sections would gain from a clip` is not printed. Each `.mmd` is the block of the map copied verbatim.
5. **Write the page**: follow "Fill the template", "Provenance", "Write the prose" and "Verify and export" of `rungs/page.md`, with these overrides, as a list: `<meta name="explain-rung" content="onboard">`; `data-kind="directory"` and `data-root` the root; write each `diagrams/<id>.mmd`, then run `python3 <skill-dir>/scripts/mermaid_svg.py inline index.html` (last line `mermaid: ok <n> diagrams`; run it again after each change to a `.mmd` file; fix each `mermaid: FAIL` line); `verify.sh` prints the six page lines and `bpmn: none` last (`bpmn: ok` only when the page cites a `.bpmn` file); the snapshots of `page.md` steps 2 and 3; in the tiles look for cut text in a diagram, an empty figure and a false picture; compare the `#entry` table with `inventory.txt` (every traced or not-traced line has a row); the handoff of convention 6: print the path, run `open index.html` only when you run for the user directly, never run `open` inside a subagent.
6. **Output directory**: the directory name and the table `| Path | Holds |` of spec section 4, verbatim.

- [ ] **Step 4: Lint, then run the tests to verify they pass**

Run (repository root): `python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/onboard.md`
Expected: `0 errors, 0 warnings` (fix each named line until it is).

Run: `python3 -B -m unittest tests.test_rung_drift -k OnboardRungCase -v`
Expected: all `ok`.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/rungs/onboard.md skills/explain/tests/test_rung_drift.py
git commit -m "feat: explain: rungs/onboard.md holds the onboarding rules, the map, the section plan and the output directory"
```

---

### Task 4: `SKILL.md` and `README.md` name the eighth rung; the full suite

**Files:**
- Modify: `SKILL.md`, `README.md` (repository root)
- Modify: `tests/test_rung_drift.py` (`AS_NAMES`, `ONBOARD_ROW`, `SkillMdCase`)

**Interfaces:**
- Consumes: `rungs/onboard.md` (Task 3); the helpers `read`, `section`, `lint`, `SkillMdCase.bullets` of `tests/test_rung_drift.py`.
- Produces, verbatim in `tests/test_rung_drift.py` and in the files:
  ```python
  AS_NAMES = "ste|sheet|page|video|brainrot|lesson|course|onboard"
  ONBOARD_ROW = ("| `onboard` (page from a checked map, directory output) | Forced only (`--as onboard`). "
                 "A service to onboard to: its architecture and every flow | One service directory |")
  ```

- [ ] **Step 1: Update the existing pins and write the failing tests**

In `tests/test_rung_drift.py`:
- `AS_NAMES` as above.
- `test_skill_md_routes_the_lesson_rung` and `test_skill_md_routes_the_course_rung`: the conventions sentence becomes "These seven rules apply to every artifact rung (`sheet`, `page`, `video`, `brainrot`, `lesson`, `course`, `onboard`)." and the count sentence "List these eight names in the error."
- `test_readme_names_the_lesson_rung`: the layout string becomes `rungs/{sheet,page,video,brainrot,lesson,course,onboard}.md`.
- `test_skill_md_routes_the_onboard_rung` (new): the argument-hint line holds `AS_NAMES`; the flat text holds `Syntax: \`/explain <subject> [--as <AS_NAMES>] [--review]\`.`, the rule bullet "The `onboard` rung builds one page for one service from its map. Only `--as onboard` selects it. The onboard rung is English or Russian.", and "Only the `lesson` and `course` rungs have a review."; the names in backticks between `its value must be` and `. Else stop` of the Contract equal `AS_NAMES.split("|")`; the rung-table rows that start with ``| `onboard` `` equal `[ONBOARD_ROW]`; `bullets()["<skill-dir>/rungs/onboard.md"]` holds `map`, `inventory` and `check`; `(EXPLAIN / "rungs" / "onboard.md").is_file()`.
- `test_readme_names_the_onboard_rung` (new): `README.md` holds `` `--as onboard` ``; its rows that start with ``| `onboard` |`` equal ``["| `onboard` | the needs of `page` |"]``; it holds `scripts/{onboard,mermaid_svg}.py`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -B -m unittest tests.test_rung_drift -k SkillMdCase -v`
Expected: the two new tests and the three updated pins fail on the old text; the other `SkillMdCase` tests stay `ok`.

- [ ] **Step 3: Edit `SKILL.md` and `README.md`**

`SKILL.md`, six edits and nothing else:
- the `argument-hint` and the `Syntax:` line of the Contract: `[--as ste|sheet|page|video|brainrot|lesson|course|onboard]`;
- Contract step 4: the value must be one of the eight names, `onboard` last, and "List these eight names in the error.";
- the rung table: `ONBOARD_ROW` after the `course` row;
- the rung rules: the `onboard` bullet (the sentence of Step 1) after the `course` bullet;
- the conventions sentence with the seven artifact rungs;
- Rung files: a bullet for `<skill-dir>/rungs/onboard.md` that names the onboarding rules, the inventory, the map and its check, the Mermaid flows, the section plan and the output directory.

`README.md`, three edits: the bold `/explain` line takes the eight names and one clause after the course clause, "or an onboarding page (`--as onboard`: one service directory, explored by the onboarding rules into a map that `onboard.py check` verifies, then a page with its architecture, every entry point and every flow as Mermaid diagrams)"; the Requirements table gains the row ``| `onboard` | the needs of `page` |`` after `course`; the Layout block lists `rungs/{sheet,page,video,brainrot,lesson,course,onboard}.md` and adds `scripts/{onboard,mermaid_svg}.py` after `scripts/cite_check.py`.

- [ ] **Step 4: Lint, then run the scoped tests**

Run (repository root): `python3 skills/ste/scripts/ste_lint.py skills/explain/SKILL.md`
Expected: `0 errors, 0 warnings`.

Run: `python3 -B -m unittest tests.test_rung_drift -v`
Expected: all `ok`.

- [ ] **Step 5: Run the full suite**

Run (from `skills/explain/`): `python3 -B -m unittest discover -s tests`
Expected: the last line `OK (skipped=46)` and the count above 1376 (the base ran 1376 tests in about nine minutes); then `ps -axo command | grep -c '[h]eadless=new'` prints `0` (no headless Chrome left).

- [ ] **Step 6: Commit**

```bash
git add skills/explain/SKILL.md README.md skills/explain/tests/test_rung_drift.py
git commit -m "feat: explain: SKILL.md and README name the onboard rung, the eighth --as name"
```
