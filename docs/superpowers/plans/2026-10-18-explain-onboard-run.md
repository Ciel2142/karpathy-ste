# explain-onboard-run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The onboarding map and page carry the commands to build, test and run the service, the framework versions, the conventions of the code with one example each, and a "where to look" table, and `onboard.py check` enforces them.

**Architecture:** Three additions to the map format of `scripts/onboard.py` (keyed `Shape` lines; the sections `Conventions` and `Where to look`), each a small check function wired into `check_map`; the rung file `rungs/onboard.md` describes them and plans three page sections; `tests/test_rung_drift.py` ties the rung file to the script constants. No generator: the author still writes the page from the map.

**Tech Stack:** Python 3 standard library, `unittest`; STE-80 lint (`skills/ste/scripts/ste_lint.py`) on rung files.

**Spec:** `docs/superpowers/specs/2026-10-16-explain-onboard-design.md`, section 15 (and the patched skeleton of section 6 and prefix table of section 7).

## Global Constraints

- Plans carry contracts, not bodies (user rule). Executors write code under TDD.
- Every rung file prints `0 errors, 0 warnings` from `python3 skills/ste/scripts/ste_lint.py <file>`.
- The suite is `cd skills/explain && python3 -B -m unittest discover -s tests`; a task runs its own modules, the branch finish runs it all.
- Never commit `out/`. Never touch the main tree's uncommitted edits.
- Ids match `[a-z][a-z0-9_-]*` (the `ID` pattern of `onboard.py`). A backticked handle is the `HANDLE` pattern of `onboard.py`.
- Check output: one failure per line, then `onboard: ok` or `onboard: <n> failures`; exit 0 / 1 / 2 as today.
- Work on branch `feat/explain-onboard-run`, worktree `/Users/valukin/karpathy-wt/explain-onboard-run`.

## Review Focus

1. A `Shape` line of the old form (no key, such as `- Java 21 service built with Gradle | ...`) must fail with `shape #<n>: unknown key` and not crash; the key test of `_key` treats a first word as a key only when the head before `:` is one token. Test in Task 1.
2. `- build: none found` must not produce `cite Shape#<n>: no cite`; a `none found` fact of a required key with no cite is the accepted form in `Shape` and `Conventions` only, not in `Where to look`. Tests in Tasks 1 and 2.
3. A `framework` line may repeat; `language` may not. `shape: language twice` once, not per repeat. Test in Task 1.
4. `Where to look` required keys follow the `Entry points` kinds present in traced and not-traced lines, not in `not an entry point` lines, and not `main`. Test in Task 2.
5. The `Where to look` path check joins the handle to the root with `os.path.normpath` and rejects `..` escapes (`not under root`) the same way as a missing path. Test in Task 2.

---

### Task 1: Keyed `Shape` lines in `onboard.py check`

**Files:**
- Modify: `skills/explain/scripts/onboard.py` (constants after `TITLES`; new `_shape_lines`; `_cite_lines`; `check_map`)
- Modify: `skills/explain/tests/test_onboard.py` (`GOOD`, `CheckCase`)
- Modify: `skills/explain/tests/fixtures/onboard/map.md` (`## Shape`)

**Interfaces:**
- Consumes: `Fact(n, line, fact, cite)`, `MapDoc.section(title)`, `_facts(doc, title)`, `_key(fact)`, `HANDLE`, `NONE_FOUND`.
- Produces:
  ```python
  SHAPE_KEYS = ("language", "framework", "runtime", "artifact", "purpose", "build", "test", "run")
  SHAPE_REQUIRED = ("language", "runtime", "artifact", "purpose", "build", "test", "run")
  SHAPE_COMMANDS = ("build", "test", "run")
  def keyed(fact: Fact) -> tuple[str | None, str]: ...   # (key, rest) of `- <key>: <rest>`; (None, fact) without a one-token head
  def none_found(fact: Fact) -> bool: ...                 # True for `- <key>: none found`
  def _shape_lines(doc: MapDoc) -> list[str]: ...
  ```

Behavior contract of `_shape_lines`, in output order: `shape: missing <key>` for each `SHAPE_REQUIRED` key with no line, in `SHAPE_KEYS` order; `shape: <key> twice` once for each key other than `framework` that has two or more lines; then per line in map order, `shape #<n>: unknown key <key>` for a key not in `SHAPE_KEYS` or a line with no key (print the first word, or `none`); `shape #<n>: no command in backticks` for a `SHAPE_COMMANDS` key whose rest is not `none found` and has no `HANDLE` match. `_cite_lines` skips a fact for which `none_found` is true when its scope is `Shape` (Task 2 adds `Conventions`). `check_map` calls `_shape_lines` right after `_handle_lines`.

- [ ] **Step 1: Re-key the fixtures.** In `tests/fixtures/onboard/map.md`, make the four `Shape` lines `language`, `runtime`, `artifact`, `purpose` with their current cites; add `- framework: Spring Boot 3.3.0 | build.gradle.kts:3 | id("org.springframework.boot") version "3.3.0"`, `- build: ` + "`./gradlew build`" + ` | build.gradle.kts:1 | plugins {`, `- test: ` + "`./gradlew test`" + ` | build.gradle.kts:2 | java`, `- run: ` + "`./gradlew bootRun`" + ` | build.gradle.kts:7 | mainClass.set("shop.ShopApplication")`. In `GOOD` of `test_onboard.py` (parse-only: its cites do not exist under `TREE`), key the one line as `language` and add `- build: none found` so the parser sees a keyed `none found` fact.
- [ ] **Step 2: Write the failing tests** in `CheckCase`:
  - `test_shape_missing_key`: drop the `run` line of the fixture → `shape: missing run` in failures, exit 1.
  - `test_shape_unknown_key_and_old_form`: replace `- language:` with `- stack:` → `shape #1: unknown key stack`; replace the whole `language` line with the old unkeyed text → `shape #1: unknown key Java` (first word) and no traceback.
  - `test_shape_key_twice`: duplicate the `language` line → exactly one `shape: language twice`; duplicate the `framework` line → no `shape:` line.
  - `test_shape_command_needs_backticks`: strip the backticks from the `build` line → `shape #<n>: no command in backticks`.
  - `test_shape_none_found_has_no_cite_failure`: the fixture with its `run` line replaced by `- run: none found` passes with `onboard: ok` (no `cite Shape#` line); `parse_map(GOOD)` gives a `Shape` fact with `cite is None` for `build`.
- [ ] **Step 3: Run** `cd skills/explain && python3 -B -m unittest tests.test_onboard -v 2>&1 | tail -5` → the new tests FAIL (`shape:` lines absent), and the fixture map now fails on `cite Shape#` for `none found` in `GOOD`.
- [ ] **Step 4: Implement** `SHAPE_KEYS`, `SHAPE_REQUIRED`, `SHAPE_COMMANDS`, `keyed`, `none_found`, `_shape_lines`; wire into `check_map`; make `_cite_lines` skip `none_found` facts in the `Shape` scope.
- [ ] **Step 5: Run** `python3 -B -m unittest tests.test_onboard` → `OK`.
- [ ] **Step 6: Commit** `feat: explain: onboard.py check reads keyed Shape lines (language, framework, runtime, artifact, purpose, build, test, run)`.

### Task 2: `Conventions` and `Where to look` sections

**Files:**
- Modify: `skills/explain/scripts/onboard.py` (`TITLES`; constants; `_convention_lines`, `_where_lines`; `_cite_lines`; `check_map`)
- Modify: `skills/explain/tests/test_onboard.py` (`GOOD`, `CheckCase`, `ParseMapCase` title count if asserted)
- Modify: `skills/explain/tests/fixtures/onboard/map.md` (two new sections before `## Not covered`)

**Interfaces:**
- Consumes: Task 1's `keyed`, `none_found`; `_facts`, `_entry_lines` parsing of `-> <flow>` / `-> not traced:` tails; `HANDLE`; `ID`.
- Produces:
  ```python
  TITLES = (..., "Other systems", "Conventions", "Where to look", "Not covered")
  CONVENTION_TOPICS = ("tests", "errors", "wiring", "naming")
  WHERE_ENTRY_KINDS = ("http", "listener", "route", "schedule")
  def _convention_lines(doc: MapDoc) -> list[str]: ...
  def _where_required(doc: MapDoc) -> list[str]: ...        # the required keys, in a fixed order
  def _where_lines(doc: MapDoc, root: str) -> list[str]: ...
  ```

Behavior contracts. `_convention_lines`: `conventions: missing <topic>` per `CONVENTION_TOPICS` topic without a line; `conventions #<n>: no topic` for a line whose head is not one `ID` token (any `ID` key is allowed). `_where_required`: `add-<kind>` for each kind in `WHERE_ENTRY_KINDS` that is the first word of an `Entry points` fact whose tail is a flow id or `not traced:`; `change-routing` when `Routing config` is not `none found`; `add-transform` when `Formats and transforms` is not `none found`; `add-test` when the `Shape` `test` line exists and is not `none found`. `_where_lines`: `where: missing <key>` per required key; per line, `where #<n>: no path in backticks` when no `HANDLE`; `where #<n>: <path> not under root` when `normpath(join(root, path))` does not start with the root or does not exist. `none found` is not accepted in `Where to look` (a line without a cite fails the cite rule). `_cite_lines` also skips `none_found` facts in `Conventions`. `check_map` order: sections, places, entry, handles, shape, conventions, where, cites, inventory.

- [ ] **Step 1: Extend the fixtures.** Add to `map.md` a `## Conventions` section with `tests` (cite `src/test/java/shop/OrderControllerTest.java:3`, snippet `class OrderControllerTest {`), `errors` (cite the existing 400 line of `OrderController.java`), `wiring` (cite `OrderController.java:11`, `private final PaymentsClient payments;`), `naming` (cite `OrderListener.java` class line), and a `## Where to look` section with `add-http` (`src/main/java/shop/`, cite `OrderController.java:14`), `add-listener` (`src/main/java/shop/`, cite `OrderListener.java:12`), `add-route` (`routes/`, cite `routes/stock.camel.yaml:1`), `add-schedule` (`src/main/kotlin/shop/`, cite `StockJobs.kt:6`), `change-routing` (`config/`, cite `camel-context.xml:5`), `add-transform` (`src/main/java/shop/`, cite `OrderController.java:15`), `add-test` (`src/test/java/shop/`, cite `OrderControllerTest.java:3`). Read each cited line first; snippets are verbatim. In `GOOD` (parse-only), add `## Conventions` with `- tests: none found` and `## Where to look` with one `add-http` line, so the parser tests keep passing.
- [ ] **Step 2: Write the failing tests** in `CheckCase`:
  - `test_sections_now_twelve`: dropping `## Conventions` → `section: missing Conventions`; `## Where to look` after `## Not covered` → `section: Where to look out of order`.
  - `test_conventions_missing_topic_and_no_topic`: drop `wiring` → `conventions: missing wiring`; a line `- an example | ...` → `conventions #<n>: no topic`.
  - `test_conventions_none_found_has_no_cite_failure`: the fixture with its `naming` line replaced by `- naming: none found` passes with `onboard: ok`.
  - `test_where_required_keys_follow_the_map`: drop `add-route` → `where: missing add-route`; drop `add-test` → `where: missing add-test`; with the `Routing config` section set to `none found` and the `change-routing` line dropped → `onboard: ok`; with the `test` line set to `- test: none found` and the `add-test` line dropped → `onboard: ok`.
  - `test_where_not_an_entry_point_needs_no_row`: in the fixture, the `main` lines and the `/health` line (not an entry point) add no required key (`where: missing add-main` never appears).
  - `test_where_path_in_backticks_under_root`: strip backticks → `no path in backticks`; path `nowhere/` → `where #<n>: nowhere/ not under root`; path `../` → `where #<n>: ../ not under root`.
- [ ] **Step 3: Run** `python3 -B -m unittest tests.test_onboard -v 2>&1 | tail -5` → the new tests FAIL.
- [ ] **Step 4: Implement** the constants and the three functions; extend `TITLES`; wire `check_map`; extend the `_cite_lines` skip.
- [ ] **Step 5: Run** `python3 -B -m unittest tests.test_onboard tests.test_course tests.test_course_discover` → `OK` (the course reads maps by section title; `Other systems` is unchanged).
- [ ] **Step 6: Commit** `feat: explain: onboard.py check reads the Conventions and Where to look sections`.

### Task 3: The rung file and the drift tests

**Files:**
- Modify: `skills/explain/rungs/onboard.md` ("Explore the service" rules 1, 7, 8; "The map" skeleton and prefix table; "Plan the sections")
- Modify: `skills/explain/tests/test_rung_drift.py` (`OnboardRungCase`)

**Interfaces:**
- Consumes: `onboard.TITLES`, `onboard.SHAPE_KEYS`, `onboard.CONVENTION_TOPICS`, `onboard.WHERE_ENTRY_KINDS` from Tasks 1 and 2.

Behavior contract of the rung text (spec 15; STE-80 prose): rule 1 lists the eight keys with one line each and says a command goes in backticks and that `none found` has no cite; a new rule 7 "Conventions and where to look" names the four topics, the `Where to look` keys and when each is required, and that the path is in backticks with one example line as the cite; "Not covered" becomes rule 8. The skeleton shows `- <key>: <fact> | ...` under `Shape`, the two new sections before `Not covered`. The prefix table adds the three rows of spec section 7 in the order `shape`, `conventions`, `where`, after `inventory` and before `map: cannot read`. "Plan the sections" adds `#run` after `#whole`, `#conventions` after `#systems`, `#where` after `#conventions` and before `#terms`, each with the content of spec 15.4 (`#run`: stack table `.table-wrap > table`, one `<pre>` per command, no inline command; `#where`: a table).

- [ ] **Step 1: Write the failing drift tests**: update `test_explore_holds_the_seven_rules_in_order` to eight rules with starts `("Shape first", "Inventory", "Architecture", "Flows", "State", "Formats and transforms", "Conventions and where to look", "Not covered")` and assert the words of `onboard.SHAPE_KEYS`, `onboard.CONVENTION_TOPICS` and `"add-" + k for k in onboard.WHERE_ENTRY_KINDS` appear in "Explore the service"; the skeleton test keeps comparing to `onboard.TITLES` (now twelve) and asserts `- <key>: <fact>` is a skeleton line; the prefix test expects ten starts, adding "`shape", "`conventions", "`where" before "`map: cannot read"; `test_plan_the_sections_follows_spec_9_1` adds `"#run"`, `"#conventions"`, `"#where"`, `"<pre>"`.
- [ ] **Step 2: Run** `python3 -B -m unittest tests.test_rung_drift.OnboardRungCase` → FAIL on the rung text.
- [ ] **Step 3: Edit `rungs/onboard.md`** per the contract above. Keep sentences short (STE-80: one instruction per sentence, present tense, no synonyms for a term).
- [ ] **Step 4: Run** `python3 /Users/valukin/karpathy-wt/explain-onboard-run/skills/ste/scripts/ste_lint.py skills/explain/rungs/onboard.md` → `0 errors, 0 warnings`; `python3 -B -m unittest tests.test_rung_drift` → `OK`.
- [ ] **Step 5: Commit** `docs: explain: onboard rung explores run commands, versions, conventions and where to look`.

### Task 4: Proof on the diadoc output

**Files:**
- Modify (untracked output, never committed): `/Users/valukin/karpathy/out/2026-10-17-210343-onboard-diadoc/map.md`, `index.html`, and its `review/`, `page.png`, `narrow.png`.

**Interfaces:**
- Consumes: `onboard.py check`, `mermaid_svg.py inline`, `verify.sh` from the branch worktree.

- [ ] **Step 1:** Run `python3 <wt>/skills/explain/scripts/onboard.py check map.md --root <root> --inventory inventory.txt` in the output directory → it lists `shape:` and `section: missing` failures (the old form).
- [ ] **Step 2:** Read the diadoc build files, one test file, one error-handling line, one injection line and one entry class; key the `Shape` lines, add `framework`, `build`, `test`, `run`, the `Conventions` and `Where to look` sections. Run the check → `onboard: ok`.
- [ ] **Step 3:** Add `#run`, `#conventions`, `#where` to `index.html` by "Plan the sections" (nav links included; commands in `<pre>`; cites copied from the map). Run `mermaid_svg.py inline index.html` → `mermaid: ok 23 diagrams`; run `verify.sh index.html` → every line `ok`; look at the three new sections in `review/` tiles for cut text.
- [ ] **Step 4:** Nothing to commit. Report the check and verify lines.
