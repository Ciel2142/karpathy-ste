# explain onboard, wave 2 (onboard-check) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The mechanical floor of an onboarding map: `onboard.py inventory` lists the entry points of a service by pattern, and `onboard.py check` enforces the map format of spec section 6 with the failure prefixes of spec section 7.

**Architecture:** One stdlib-only Python script, `scripts/onboard.py`, in four layers: a tolerant Mermaid node parser (`mermaid_kind`, `mermaid_nodes`), a map reader that turns the Markdown into sections, flows, diagrams and fact lines (`parse_map`, `read_map`, `flow_nodes`, the functions the course wave imports), a pattern-table inventory over a source tree, and the check that walks the map and prints one failure per line. The cite rules come from `cite_check.py` through one new public helper, `fact_problems`; `course.py` is not touched in this wave.

**Tech Stack:** Python 3.14 stdlib (`re`, `os`, `argparse`, `typing.NamedTuple`), `unittest`. No Chrome and no network in this wave.

**Spec:** `docs/superpowers/specs/2026-10-16-explain-onboard-design.md` (sections 5, 6, 7 and 13). Wave map: `docs/superpowers/waves/2026-10-16-explain-onboard.yaml`, wave `onboard-check`. Coverage: waived.

Base: 1731c444a7c0d20d044b20212081711443339344
Test runs: scoped per task; full suite once, final task.

All paths below are relative to `skills/explain/` unless they start with `docs/`. Every test command runs from `skills/explain/`.

## Global Constraints

- The ten level-2 titles of a map, in this order, verbatim: `Shape`, `Architecture`, `Entry points`, `Flows`, `State`, `Formats and transforms`, `Routing config`, `Error paths`, `Other systems`, `Not covered`. The title line is `# Map: <id>`.
- A fact line is `- <fact> | <path>:<line> | <snippet>`; the snippet has at most 12 words (`cite_check.MAX_WORDS`), verbatim on that line; `Not covered` lines carry no cite. `none found` (bare, or as `- none found`) is the one line of an empty section.
- A flow id and a flowchart node id match `[a-z][a-z0-9_-]*`. A flowchart has at most 25 nodes. The first line of a diagram block is exactly `flowchart TD`, `flowchart LR` or `stateDiagram-v2`; the fence info string is `mermaid`.
- An `Entry points` fact part ends with `-> <flow-id>`, `-> not traced: <reason>` or `-> not an entry point: <reason>`, the reason non-empty.
- Inventory lines are `<path>:<line>\t<kind>\t<text>`, path relative to `--root`, text white-space-squashed and cut to 120 characters; kinds are `http`, `listener`, `route`, `schedule`, `main`; skipped directories `node_modules`, `target`, `build`, `.git`, `vendor`, `test`, `tests` (so `src/test` too); skipped file names ending in `_test.go`, `Test.java`, `Test.kt`, `Spec.kt`. Languages: Java, Kotlin, Go, `*.camel.yaml`, Camel XML. Nothing else.
- Summary lines: `inventory: <n> entry points`; `onboard: ok` or `onboard: <n> failures`. Exit 0 ok, 1 failures found, 2 usage, an unreadable source, map, root or inventory file. `map: cannot read …` goes to stdout (it is a finding of the table of spec section 7); every other exit-2 line goes to stderr.
- The failure prefixes are those of spec section 7: `section:`, `diagram <where>:`, `node <where>/<id>:`, `fact <where>/<id>:`, `cite <scope>#<n>:`, `entry #<n>:`, `inventory <path>:<line>:`, `map: cannot read`. `<where>` is `architecture`, `state` or a flow id; `<scope>` is a level-2 title as written, or `Flows/<flow-id>` for the fact lines of one flow.
- Stdlib only; the suite runs under the system python3 (3.14). Never commit `out/`. This wave changes no rung file, no `SKILL.md`, no `README.md` and not `course.py` (waves 3 and 4 own them); `course._cite_problems` stays as it is.
- Commit style of this repository: `feat: explain: …`, `test: explain: …`.

## Review Focus

1. The stdout of `inventory` saved as a file and passed to `check --inventory`, so the file ends with `inventory: 18 entry points`: a reader that takes every line would print `inventory inventory: 18 entry points: not in Entry points`. Expected: a line without a tab is skipped (Task 4).
2. A Spring controller with a class-level `@RequestMapping("/orders")` above `public class`: a line grep lists the class as an entry point and the author must dismiss a phantom. Expected: not a hit; the method-level `@RequestMapping` is (Task 2).
3. A query builder with `.from(table)` in a Java file that is not a `RouteBuilder`: the same grep lists a Camel route that does not exist. Expected: `from(` counts only in a file whose text holds `RouteBuilder` (Task 2).
4. A `### Order flow` heading under `Flows` without `<id>:`: a reader that skips it silently leaves the flow's diagram and nodes unchecked and every entry line pointing at it fails with a misleading `not in Flows`. Expected: `section: Flows heading Order flow has no flow id` (Task 3).
5. A node label holding an arrow or a bracket, `note["send --> partner [async]"]`: a parser that splits before it strips quotes invents a node `partner`, which then fails `no fact line`. Expected: one node, `note` (Task 1).

## File structure

- `scripts/onboard.py` (new, one module, under 600 lines): header docstring, constants, `OnboardError`; the Mermaid parser; the map reader (`Fact`, `Diagram`, `Flow`, `Section`, `MapDoc`, `parse_map`, `read_map`, `flow_nodes`); the inventory (`Rule`, `PATTERNS`, `Hit`, `inventory`, `cmd_inventory`); the check (`check_map`, `cmd_check`); `main`.
- `scripts/cite_check.py`: one new function, `fact_problems`, beside `_check_cite`.
- `tests/test_onboard.py` (new): `MermaidNodesCase`, `ParseMapCase`, `InventoryCase`, `CheckCase`, `CliCase`; in-process runs of `main` as `tests/test_bpmn_check.py` does for `bpmn.py`.
- `tests/test_cite_check.py`: a new `FactProblemsCase`.
- `tests/fixtures/onboard/parser-flow.mmd`, `parser-state.mmd` (Task 1): the parser fixtures.
- `tests/fixtures/onboard/tree/` (Task 2): a small service, `shop`, with planted entry points in Java, Kotlin, Go, Camel YAML and Camel XML, plus files that the name rules skip.
- `tests/fixtures/onboard/map.md` (Task 3): a good map of `tree/`, root `tests/fixtures/onboard/tree`; every mutation test edits a copy in memory.

---

### Task 1: The Mermaid node parser and the map reader

**Files:**
- Create: `scripts/onboard.py`
- Create: `tests/test_onboard.py`
- Create: `tests/fixtures/onboard/parser-flow.mmd`, `tests/fixtures/onboard/parser-state.mmd`

**Interfaces:**
- Consumes: nothing of this wave.
- Produces (all in `scripts/onboard.py`):
  ```python
  USAGE: str
  TITLES: tuple[str, ...]            # the ten titles of Global Constraints, in order
  NONE_FOUND = "none found"
  ID = re.compile(r"[a-z][a-z0-9_-]*")
  TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
  MAX_NODES = 25
  FLOWCHART = "flowchart"; STATE = "stateDiagram-v2"
  class OnboardError(Exception):      # str(e) is the whole output line; e.code is 1 or 2
      def __init__(self, line: str, code: int = 2) -> None
  def mermaid_kind(block: str) -> str | None       # FLOWCHART, STATE or None
  def mermaid_nodes(block: str) -> list[str]        # ids in first-appearance order, each once
  class Fact(NamedTuple):
      n: int; line: int; fact: str; cite: tuple[str, int, str] | None
  class Diagram(NamedTuple):
      line: int; kind: str | None; nodes: list[str]; text: str
  class Flow(NamedTuple):
      ident: str | None; heading: str; question: str; line: int; diagrams: list[Diagram]; facts: list[Fact]
  class Section(NamedTuple):
      title: str; line: int; diagrams: list[Diagram]; facts: list[Fact]; flows: list[Flow]; none_found: bool
  class MapDoc(NamedTuple):
      ident: str; sections: list[Section]
      def section(self, title: str) -> Section | None   # the first section with that title
  def parse_map(text: str) -> MapDoc                 # raises ValueError('no "# Map:" title')
  def read_map(path: str) -> MapDoc                  # raises OnboardError("map: cannot read <path>: <reason>", 2)
  def flow_nodes(doc: MapDoc) -> dict[str, list[str]]  # flow id -> nodes of its first diagram; the course wave imports this
  def main(argv: list[str]) -> int
  ```

- [ ] **Step 1: Write the parser fixtures**

`tests/fixtures/onboard/parser-flow.mmd` (nine nodes; a subgraph, a direction line, every edge-label form, every shape bracket, a chained `&`, a quoted label with an arrow and a bracket, a class suffix, and the four non-node statements):

```
flowchart TD
  %% the receive side
  subgraph svc[The service]
    direction LR
    recv[receive the message] --> kind{type?}
    kind -->|send| route[route by place]
    kind -- cancel --> cancel(cancel the request)
  end
  route -. retry .-> route
  cancel ==> reply([reply to the sender])
  route --> store[(orders table)] & audit>audit log]
  store --> note["send --> partner [async]"]
  note:::ext --> done((done))
  classDef ext fill:#fff
  class note ext
  click done "https://example.com"
```

`tests/fixtures/onboard/parser-state.mmd` (seven states; a direction line, labelled and plain transitions, an alias, a composite state, a one-line note):

```
stateDiagram-v2
  direction LR
  [*] --> New
  New --> Paid: charge ok
  Paid --> Shipped
  New --> Cancelled: cancel
  state "On hold" as Held
  Paid --> Held: dispute
  state Shipped {
    [*] --> Packed
    Packed --> Sent
  }
  note right of Sent: the carrier takes it
  Sent --> [*]
```

- [ ] **Step 2: Write the failing tests**

In `tests/test_onboard.py`: `sys.path.insert(0, <scripts dir>)`, `import onboard`; `FIXTURES = Path(__file__).resolve().parent / "fixtures" / "onboard"`; a helper `run(argv) -> tuple[int, str, str]` that calls `onboard.main(argv)` under `contextlib.redirect_stdout` / `redirect_stderr`; a helper `read(name) -> str` for a fixture file.

`MermaidNodesCase`:
- `test_flowchart_nodes_in_order_once_each`: `mermaid_nodes(read("parser-flow.mmd"))` is exactly `["recv", "kind", "route", "cancel", "reply", "store", "audit", "note", "done"]`.
- `test_arrow_inside_a_quoted_label_is_not_an_edge`: the line `a["send --> partner [async]"] --> b` gives `["a", "b"]`.
- `test_subgraph_and_statements_are_not_nodes`: none of `svc`, `direction`, `classDef`, `class`, `click`, `end`, `ext` is in the flow fixture's nodes.
- `test_state_names_in_order_without_start_and_end`: `mermaid_nodes(read("parser-state.mmd"))` is exactly `["New", "Paid", "Shipped", "Cancelled", "Held", "Packed", "Sent"]`.
- `test_kind_of_each_first_line`: `flowchart TD` and `flowchart LR` give `FLOWCHART`; `stateDiagram-v2` gives `STATE`; `graph TD`, `flowchart TB`, `sequenceDiagram` and an empty block give `None`; a leading blank line is tolerated.

`ParseMapCase`, on an inline map text `GOOD` of the test module (the ten sections; `Architecture` with one `flowchart LR` block and two keyed facts; `Entry points` with two facts; `Flows` with `### send: What happens to a send?` holding one `flowchart TD` block and three keyed facts, then `### cancel: …` with one block and one fact; `State` as `none found`; `Other systems` with one fact; `Not covered` with one bullet without a cite; one fenced ```` ```text ```` block in `Shape` that holds a line starting with `- `):
- `test_title_and_section_titles_in_document_order`: `doc.ident == "demo"`; `[s.title for s in doc.sections]` equals `TITLES`.
- `test_flows_carry_id_question_diagram_and_facts`: the `Flows` section has two flows, idents `send` and `cancel`, the first with the question text, one diagram of kind `FLOWCHART` and three facts with `n` 1, 2, 3.
- `test_fact_line_splits_into_fact_and_cite`: the first `Entry points` fact has `fact == "http POST /send -> send"` and `cite == ("src/A.java", 12, "@PostMapping")`; a bullet with one ` | ` part has `cite is None` and the whole text as `fact`.
- `test_none_found_marks_the_section`: `State.none_found` is true and it has no diagrams and no facts; `Flows.none_found` is false; a section holding `- none found` as its one line is `none_found` with no facts.
- `test_fenced_text_block_is_not_a_diagram_and_hides_its_bullets`: the `Shape` section has zero diagrams and the `- ` line inside the text block is not a fact.
- `test_flow_heading_without_an_id_keeps_the_heading`: a `### Order flow` heading gives a `Flow` with `ident is None` and `heading == "Order flow"`.
- `test_flow_nodes_maps_each_flow_to_its_node_ids`: `flow_nodes(doc) == {"send": [...], "cancel": [...]}` with the ids of the inline blocks.
- `test_map_without_title_cannot_be_read`: `parse_map("## Shape\n")` raises `ValueError`; `read_map(<tmp file with that text>)` raises `OnboardError` whose line starts with `map: cannot read <path>:` and `code == 2`; `read_map(<missing path>)` likewise.

`CliCase` (the part of Task 1):
- `test_usage_without_a_command_exits_2`: `run([])` → 2, stderr starts with `usage: onboard.py inventory`.
- `test_unknown_command_exits_2`: `run(["render"])` → 2, stderr starts with `usage:`.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -B -m unittest discover -s tests -p "test_onboard.py" -v`
Expected: `ModuleNotFoundError: No module named 'onboard'`.

- [ ] **Step 4: Implement the constants, `OnboardError`, the parser, the reader and `main` in `scripts/onboard.py`**

Header docstring in the style of `bpmn.py`: the two commands, the exit codes, the output and summary lines (spec section 7).

- `mermaid_kind(block)`: the first non-blank line, stripped, compared whole against the three strings of Global Constraints; anything else is `None`.
- `mermaid_nodes(block)` for a flowchart: for each line after the first, cut a `%%` comment, skip a blank line and a line whose first token is `subgraph`, `end`, `direction`, `classDef`, `class`, `style`, `linkStyle` or `click`; remove double-quoted strings first, then every bracketed label (`[…]`, `(…)`, `{…}`, `>…]` and their doubled forms, innermost first until none is left), then every `|…|` edge label and every `:::class` suffix; split what is left on the edge operators (`-->`, `---`, `-.->`, `-.-`, `==>`, `===`, `--o`, `--x`, `<-->`, and the text forms `-- text -->`, `-. text .->`, `== text ==>`) and on `&`; the first `TOKEN` of each segment is a node id. For a `stateDiagram-v2`: skip `direction`, `note`, `classDef` and `class` lines and a `}` line; `state "desc" as <id>` gives `<id>`; `state <id> {` gives `<id>`; a line holding `-->` gives the first `TOKEN` on each side, the right side cut at its first `:`; `[*]` is never a state. Both forms return ids in first-appearance order, each once.
- `parse_map(text)`: the first non-blank line must match `# Map: <id>` (id stripped, non-empty), else `ValueError`. Then line by line, tracking fenced blocks (a line starting with three backticks opens one; the next such line closes it): a ```` ```mermaid ```` block becomes a `Diagram` of its enclosing flow or section (`kind = mermaid_kind`, `nodes = mermaid_nodes`, `text` the body); any other fenced block is skipped whole. Outside fences: `## <title>` starts a `Section`; `### <text>` inside `Flows` starts a `Flow`, with `ident` and `question` when the text matches `<id>: <question>` and `ID.fullmatch(id)`, else `ident None`, `question ""`, `heading` the text; a `###` line in any other section is prose; a line starting with `- ` is a `Fact` of the current flow, else of the current section, except that `- none found` is not a fact; `fact` is the text before the first ` | `; `cite` is `(path, int(line), snippet)` only when the line has exactly three ` | ` parts and the middle one is `<path>:<digits>` with the number at least 1, else `None`; `n` counts from 1 inside its scope. `none_found` is true when the section's non-blank content outside fences is the one line `none found` or `- none found`. Everything else is prose.
- `read_map(path)`: read with `encoding="utf-8"`, call `parse_map`; an `OSError` or the `ValueError` becomes `OnboardError("map: cannot read %s: %s" % (path, reason), 2)`.
- `flow_nodes(doc)`: for the `Flows` section, every flow with an `ident` and at least one diagram, mapped to the nodes of its first diagram.
- `main(argv)`: dispatch on `argv[0]` to `cmd_inventory` / `cmd_check` (both return the usage, 2, until Tasks 2 and 3 land); no or unknown command → `USAGE` on stderr, 2. An `OnboardError` raised under a command prints its line on stdout when the line starts with `map:` and on stderr otherwise, and returns `e.code`. The `__main__` block is `sys.exit(main(sys.argv[1:]))`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -B -m unittest discover -s tests -p "test_onboard.py" -v`
Expected: every `MermaidNodesCase`, `ParseMapCase` and `CliCase` test `ok`.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/scripts/onboard.py skills/explain/tests/test_onboard.py skills/explain/tests/fixtures/onboard/parser-flow.mmd skills/explain/tests/fixtures/onboard/parser-state.mmd
git commit -m "feat: explain: onboard.py reads a map and the nodes of its Mermaid diagrams"
```

---

### Task 2: `inventory` lists the entry points of a source tree

**Files:**
- Modify: `scripts/onboard.py`
- Create: `tests/fixtures/onboard/tree/` (the files of Step 1)
- Modify: `tests/test_onboard.py`

**Interfaces:**
- Consumes: `OnboardError`, `USAGE`, `main` (Task 1).
- Produces:
  ```python
  class Rule(NamedTuple): suffixes: tuple[str, ...]; regex: re.Pattern
  PATTERNS: dict[str, tuple[Rule, ...]]   # kind -> rules; keys in the order http, listener, route, schedule, main
  SKIP_DIRS: frozenset[str]; SKIP_SUFFIXES: tuple[str, ...]; TEXT_MAX = 120
  class Hit(NamedTuple): path: str; line: int; kind: str; text: str
  def squash(text: str) -> str                               # white space squashed, cut to TEXT_MAX
  def scan_file(path: str, rel: str) -> list[Hit]
  def inventory(source: str, root: str) -> list[Hit]         # sorted by (path, line); raises OnboardError
  def inventory_line(hit: Hit) -> str                        # "<path>:<line>\t<kind>\t<text>"
  def cmd_inventory(argv: list[str]) -> int
  ```

- [ ] **Step 1: Write the fixture tree**

`tests/fixtures/onboard/tree/` is the service `shop`. Each file is short (under 40 lines) and holds the constructs of this table, one per line, so that a test can find each by a needle; the Java bodies also hold the lines that the map of Task 3 cites (a limit check, a payments call, a save, a Kafka send, two replies; a status check and a status set in the listener; the status enum with its four values).

| File | Constructs that are hits (kind) | Constructs that are not hits |
|---|---|---|
| `build.gradle.kts` | none | `plugins { … }`, `application { mainClass … }` |
| `src/main/java/shop/ShopApplication.java` | `public static void main` (main) | |
| `src/main/java/shop/OrderController.java` | method-level `@PostMapping`, `@GetMapping("/{id}")`, method-level `@RequestMapping(method = …)` (http) | class-level `@RequestMapping("/orders")` above `public class` |
| `src/main/java/shop/OrderListener.java` | `@KafkaListener(topics = "orders.cancel")` (listener) | |
| `src/main/java/shop/ShopRoutes.java` | `from("jms:queue:shop.in")` in a class that `extends RouteBuilder` (route) | |
| `src/main/java/shop/ReportQuery.java` | none | `.from(ORDERS)` in a file without `RouteBuilder` |
| `src/main/java/shop/Order.java` | none | `enum Status { NEW, PAID, SHIPPED, CANCELLED }`, `setStatus` |
| `src/main/kotlin/shop/StockJobs.kt` | `@Scheduled(cron = …)` (schedule), `class StockDelegate : JavaDelegate` (listener), `fun main(` (main) | |
| `cmd/shop-gw/main.go` | `func main(` (main), `r.GET("/health", …)` (http), `http.HandleFunc("/metrics", …)` (http), `consumer.Consume(ctx` (listener), `time.NewTicker(` (schedule), `pb.RegisterShopServer(` (route) | |
| `routes/stock.camel.yaml` | `- from:` followed by `uri: "kafka:stock.updates"` on the next line, and a second `- from: { uri: "timer:stock" }` (route) | |
| `config/camel-context.xml` | `<from uri="jms:queue:legacy.in"/>` (route) | |
| `src/test/java/shop/OrderControllerTest.java` | none (skipped directory and name) | `@GetMapping`, `public static void main` |
| `cmd/shop-gw/main_test.go` | none (skipped name) | `func main(` |
| `src/main/kotlin/shop/StockJobsSpec.kt` | none (skipped name) | `@Scheduled` |

Eighteen hits in all. The directories `target`, `build`, `node_modules`, `vendor`, `.git` and `tests` are not committed (`node_modules/` is git-ignored in this repository); the test plants them in a temporary copy.

- [ ] **Step 2: Write the failing tests**

`InventoryCase` in `tests/test_onboard.py`, with `TREE = FIXTURES / "tree"`, a helper `line_of(rel, needle) -> int` (the 1-based line of the first line of `TREE/rel` holding `needle`, as `tests/test_bpmn_check.py` does), and the table `PLANTED = [(rel, needle, kind), …]` of the eighteen hits of Step 1:
- `test_tree_lists_each_planted_entry_point_once_and_nothing_else`: `[(h.path, h.line, h.kind) for h in inventory(TREE, TREE)]` equals the sorted `PLANTED` triples with `line_of` applied; no path holds `Test.java`, `_test.go`, `Spec.kt` or `src/test`.
- `test_skipped_directories_are_pruned`: a temporary copy of the tree with a hit line planted under each of `target/`, `build/`, `node_modules/`, `vendor/`, `.git/`, `tests/` and `src/test/` gives the same triples as the committed tree.
- `test_class_level_request_mapping_is_not_a_hit`: no hit at `line_of("src/main/java/shop/OrderController.java", '@RequestMapping("/orders")')`; the method-level one is a hit of kind `http`.
- `test_from_outside_a_route_builder_is_not_a_hit`: no hit in `ReportQuery.java`; the `from(` of `ShopRoutes.java` is a hit of kind `route`.
- `test_camel_yaml_from_without_inline_uri_takes_the_next_line`: the hit of the first `- from:` has text `- from: uri: "kafka:stock.updates"`; the second has its own line's text.
- `test_text_is_squashed_and_cut_to_120`: a temporary file with a `@GetMapping` line of 300 characters and tabs gives a text of exactly 120 characters with single spaces.
- `test_a_line_hits_once_with_the_first_kind`: a temporary Go file whose one line holds both `r.GET("/x", h)` and `cron.New()` gives one hit of kind `http`.
- `test_cli_prints_the_lines_then_the_count_and_writes_out`: `run(["inventory", TREE, "--root", TREE, "--out", <tmp>/inv.txt])` → 0; stdout is the eighteen `inventory_line`s sorted, then `inventory: 18 entry points`; the out file holds exactly the eighteen lines and no summary.
- `test_paths_are_relative_to_root`: with `--root` the parent of `TREE`, every path starts with `tree/`.
- `test_source_outside_root_is_usage`: `--root` a sibling directory → 2; stderr starts with `usage:` and names the source.
- `test_missing_source_exits_2`: a missing directory → 2; stderr == `onboard: cannot read <path>\n`; nothing on stdout.
- `test_missing_root_flag_is_usage`: `run(["inventory", TREE])` → 2; stderr starts with `usage:`.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -B -m unittest discover -s tests -p "test_onboard.py" -k InventoryCase -v`
Expected: `AttributeError: module 'onboard' has no attribute 'inventory'`, and the CLI tests fail on exit 2 with the usage line.

- [ ] **Step 4: Implement the table, the walk and `cmd_inventory`**

- `PATTERNS`, one dict, kinds in order; every regex is searched per line. Java and Kotlin suffixes are `(".java", ".kt")`, Go `(".go",)`, Camel YAML `(".camel.yaml", ".camel.yml")`, XML `(".xml",)`:
  - `http` Java/Kotlin: `@(Get|Post|Put|Delete|Patch)Mapping`, `@RequestMapping`, `@Path\(`, `@MessageMapping`, `@ServerEndpoint`; Go: `\.(Get|Post|Put|Delete|Patch|GET|POST|PUT|DELETE|PATCH|Handle|HandleFunc)\(\s*"`, `http\.HandleFunc\(`.
  - `listener` Java/Kotlin: `@(Jms|Rabbit|Kafka|Sqs|Stream)Listener`, `@KafkaHandler`, `@ServiceActivator`, `@InboundChannelAdapter`, `@EventListener`, `@TransactionalEventListener`, `@ExternalTaskSubscription`, `implements JavaDelegate`, `: JavaDelegate`; Go: `\.Consume\(`, `NewReader\(`, `NewConsumer\(`, `Subscribe\(`.
  - `route` Java/Kotlin: `\bfrom\(`, `routeTemplate`, `@GrpcService`; Go: `Register\w*Server\(`; Camel YAML: `^\s*-\s*from:`; XML: `<from\s[^>]*uri=`.
  - `schedule` Java/Kotlin: `@Scheduled`; Go: `\bcron\.`, `NewTicker\(`, `time\.Tick\(`.
  - `main` Java: `public static void main`; Kotlin: `fun main\(`; Go: `func main\(`.
- `scan_file(path, rel)`: the file read with `errors="replace"`; a line is a hit of the first kind, in dict order, whose rule matches, once. Two context rules: a `\bfrom\(` match counts only when the file's text holds `RouteBuilder`; a `@RequestMapping` match does not count when the next line that is neither blank nor starts with `@` matches `\b(class|interface|object|enum|record)\b`. The Camel YAML text rule: when the squashed line is exactly `- from:`, the text is that line, one space and the squashed next non-blank line. `text = squash(line)`.
- `inventory(source, root)`: `source` not a directory → `OnboardError("onboard: cannot read <source>", 2)`; `os.path.relpath(source, root)` starting with `..` → `OnboardError("usage: <source> is not under <root>", 2)`; `os.walk(source)` top-down, pruning every directory whose name is in `SKIP_DIRS` and skipping every file whose name ends with one of `SKIP_SUFFIXES`; the rest scanned with `rel = os.path.relpath(file, root)`; the hits sorted by `(path, line)`.
- `cmd_inventory(argv)`: `argparse` with `source`, required `--root`, optional `--out`; a parse error is the usage, 2 (use `exit_on_error=False` or a parser subclass whose `error` raises; print `USAGE` on stderr); hits printed one per line with `inventory_line`, then `inventory: <n> entry points`; `--out` written with the hit lines only, each ending in a newline, before the summary is printed; an `OSError` on the write → `onboard: cannot write <out>: <error>` on stderr, 2.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -B -m unittest discover -s tests -p "test_onboard.py" -v`
Expected: every `InventoryCase` test `ok`, Task 1 tests still `ok`.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/scripts/onboard.py skills/explain/tests/test_onboard.py skills/explain/tests/fixtures/onboard/tree
git commit -m "feat: explain: onboard.py inventory lists the entry points of a service by pattern"
```

---

### Task 3: `check` enforces the sections, the diagrams and the node facts

**Files:**
- Modify: `scripts/onboard.py`
- Create: `tests/fixtures/onboard/map.md`
- Modify: `tests/test_onboard.py`

**Interfaces:**
- Consumes: `read_map`, `MapDoc`, `Section`, `Flow`, `Diagram`, `Fact`, `TITLES`, `ID`, `TOKEN`, `MAX_NODES`, `FLOWCHART`, `STATE`, `OnboardError` (Task 1); the fixture tree (Task 2).
- Produces:
  ```python
  def check_map(doc: MapDoc, root: str, inventory: list[str] | None = None) -> list[str]  # the failure lines, in order
  def cmd_check(argv: list[str]) -> int
  ```
  In this task `check_map` produces the `section`, `diagram`, `node` and `fact` lines; `root` and `inventory` are accepted and used by Task 4.

- [ ] **Step 1: Write the fixture map**

`tests/fixtures/onboard/map.md`, `# Map: shop`, the ten sections in order, every cite a real line of `tests/fixtures/onboard/tree/` (path relative to that directory, snippet verbatim, at most 12 words):
- `Shape`: four facts (language and build tool from `build.gradle.kts`, runtime kind, deploy artifact, purpose).
- `Architecture`: one `flowchart LR` with a `subgraph shop` holding `api`, `listener` and `repo[(orders table)]`, and outside it `payments[Payments API]` and `kafka[Kafka orders.*]`; five keyed facts.
- `Entry points`: one line per hit of the tree's inventory, eighteen lines, whose cite is the hit's `<path>:<line>` and whose fact part ends with: `-> order` (the `@PostMapping`), `-> cancel` (the `@RequestMapping` delete and the `@KafkaListener`), `-> not traced: <reason>` (the `@GetMapping`, the Camel route, the Kotlin schedule and delegate, the Go listener, ticker, gRPC and HTTP handlers, the YAML and XML routes), `-> not an entry point: <reason>` (the three mains and the Go health route).
- `Flows`: `### order: What happens to a new order?` — a `flowchart TD` of seven nodes `recv`, `valid{total over limit?}`, `reject`, `charge`, `save[(orders table)]`, `publish`, `reply`, using `-->|yes|`, `-->|no|` and `-- declined -->` edges, then seven keyed facts; `### cancel: How is an order cancelled?` — four nodes `listen`, `shipped{already shipped?}`, `ignore`, `cancel`, and a fifth `next[see order]`, five keyed facts.
- `State`: one `stateDiagram-v2` over `NEW`, `PAID`, `SHIPPED`, `CANCELLED` with `[*]` at both ends; four keyed facts citing `Order.java`.
- `Formats and transforms`, `Routing config`, `Error paths`: one fact each.
- `Other systems`: two lines, `Payments` and `Kafka`, each with its handles in backticks in the fact part.
- `Not covered`: one line, `- cmd/shop-gw: <reason>`, no cite.

- [ ] **Step 2: Write the failing tests**

`CheckCase` in `tests/test_onboard.py`, with `MAP = (FIXTURES / "map.md").read_text()`, a helper `check(text=MAP, edits=(), inventory=None) -> tuple[int, str, str]` that applies `(old, new)` replacements (each `old` must occur, as `replace_once` of `tests/test_bpmn_check.py`), writes the text to `<tmp>/map.md`, and runs `check` with `--root TREE` (and `--inventory <file>` when given); `failures(out)` is every stdout line but the last; `only(*expected, **kw)` asserts the failures equal `expected` and the last line is `onboard: <len> failures`:
- `test_good_map_is_ok`: `check()` → 0, stdout == `onboard: ok\n`.
- `test_missing_section_names_the_title`: the `## Routing config` heading and its fact removed → `section: missing Routing config`.
- `test_section_out_of_order`: `## State` block moved after `## Other systems` → `section: State out of order` as the only failure.
- `test_section_twice`: a second `## Shape` holding a copy of the first `Shape` fact, appended at the end → `section: Shape twice` as the only failure.
- `test_flow_heading_without_an_id_is_a_section_fault`: `### cancel: How is an order cancelled?` replaced by `### Cancel flow` → exactly `section: Flows heading Cancel flow has no flow id` (the flow is no place, so no `diagram` or `node` line names it; Task 4 extends this expectation).
- `test_diagram_none`: the architecture block removed → `diagram architecture: none`, `fact architecture/<id>: not a node` for its five facts.
- `test_two_blocks_in_one_place`: the `order` block doubled → `diagram order: 2 blocks, more than 1`, nothing else.
- `test_diagram_not_flowchart_or_state`: the first line of the `order` block replaced by `sequenceDiagram` → `diagram order: not flowchart or stateDiagram-v2` and no `node` or `fact` line for `order`.
- `test_state_block_in_a_flow_is_not_flowchart`: the `order` block body replaced by the state block → `diagram order: not flowchart`.
- `test_flow_block_in_state_is_not_state`: the state block body replaced by the `cancel` block → `diagram state: not stateDiagram-v2`.
- `test_more_than_25_nodes`: 26 chained nodes appended to the `cancel` block, each with a keyed fact line that copies the cite of `- listen:` → `diagram cancel: 31 nodes, more than 25` first, no other line.
- `test_node_without_a_fact_line`: the `- publish: …` fact removed → `node order/publish: no fact line`.
- `test_fact_that_is_not_a_node`: `- reply:` renamed `- answer:` → `node order/reply: no fact line`, `fact order/answer: not a node`, in that order.
- `test_fact_twice`: the `- charge: …` line doubled → `fact order/charge: two lines`.
- `test_fact_without_a_key_is_not_a_node`: `- save: the order row` rewritten as `- the order row is saved` → `node order/save: no fact line`, `fact order/the: not a node`.
- `test_bad_node_id`: `recv` renamed `Recv` in the block and the fact → `node order/Recv: bad id`.
- `test_none_found_in_architecture_and_state_skips_the_diagram_rules`: the two blocks and their facts replaced by `none found` → 0, `onboard: ok`.
- `test_none_found_with_a_diagram_is_a_normal_section`: `none found` added above the architecture block → `onboard: ok` (the line is prose, the block is checked).
- `test_flows_none_found_skips_the_flows`: the whole `Flows` content replaced by `none found`, the entry lines that name a flow rewritten to `-> not traced: later` → 0.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -B -m unittest discover -s tests -p "test_onboard.py" -k CheckCase -v`
Expected: every test fails on exit 2 with the usage line (`cmd_check` is the Task 1 stub).

- [ ] **Step 4: Implement `check_map` (the four rule groups of this task) and `cmd_check`**

- `cmd_check(argv)`: `argparse` with `map`, required `--root`, optional `--inventory`; a parse error is the usage, 2; `--root` not a directory → `onboard: cannot read root <root>` on stderr, 2; `--inventory` unreadable → `onboard: cannot read inventory <file>` on stderr, 2 (the lines are read now, used in Task 4); `read_map` (its `OnboardError` reaches `main`, which prints `map: cannot read …` on stdout and returns 2, with no summary line); then the failures printed one per line, then `onboard: ok` (0) or `onboard: <n> failures` (1).
- `check_map` output order: all `section:` lines, then the places in the order `architecture`, each flow in document order, `state`, each place giving its `diagram` lines, then its `node` lines in diagram order, then its `fact` lines in bullet order; Task 4 appends its groups after these.
- Sections: `section: missing <title>` for each of `TITLES` with no section, in canonical order; then in document order, `section: <title> twice` for a title seen before (a repeated title is not considered for the order), `section: <title> out of order` for a known title whose canonical index is lower than the highest index seen so far (an unknown title is ignored), and `section: Flows heading <heading> has no flow id` for a flow with `ident None`.
- Places: `architecture` is the `Architecture` section, `state` the `State` section, each flow with an `ident` is a place named by it; a section that is `none_found`, and every flow when `Flows` is `none_found`, is skipped. In a place: no diagram → `diagram <where>: none`; more than one → `diagram <where>: <n> blocks, more than 1`, and the first is checked; `kind None` → `diagram <where>: not flowchart or stateDiagram-v2`; `STATE` where `architecture` or a flow needs `FLOWCHART` → `diagram <where>: not flowchart`; `FLOWCHART` in `state` → `diagram state: not stateDiagram-v2`; after any kind fault the node rules of that place do not run. A flowchart with more than `MAX_NODES` nodes → `diagram <where>: <n> nodes, more than 25` (the node rules still run).
- Node rules of a place: a flowchart node whose id fails `ID.fullmatch` → `node <where>/<id>: bad id`. The key of a fact is the text before its first `:` when that text is one `TOKEN`, else the first word of the fact. A node with no fact keyed by it → `node <where>/<id>: no fact line`; a fact whose key is not a node → `fact <where>/<key>: not a node`; a node with two or more facts → `fact <where>/<id>: two lines`. A missing diagram (`none`) still reports every fact of the place as `not a node`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -B -m unittest discover -s tests -p "test_onboard.py" -v`
Expected: every `CheckCase` test of this task `ok`; Tasks 1 and 2 still `ok`.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/scripts/onboard.py skills/explain/tests/test_onboard.py skills/explain/tests/fixtures/onboard/map.md
git commit -m "feat: explain: onboard.py check enforces the sections, diagrams and node facts of a map"
```

---

### Task 4: `check` verifies the cites, the entry lines, the handles and the inventory; the full suite

**Files:**
- Modify: `scripts/cite_check.py` (after `_check_cite`)
- Modify: `scripts/onboard.py`
- Modify: `tests/test_cite_check.py`, `tests/test_onboard.py`

**Interfaces:**
- Consumes: `check_map`, `cmd_check` (Task 3); `inventory`, `inventory_line` (Task 2); `cite_check._check_cite`, `cite_check.MAX_WORDS` (existing).
- Produces:
  ```python
  # scripts/cite_check.py
  def fact_problems(path: str, line: int, snippet: str, root: str) -> list[str]
  ```
  The bare problem texts of one `<path>:<line> | <snippet>` cite under `root`, without the `cite <n> (<path>:<line>): ` label: `snippet has <n> words (max 12)`, `file missing: <root>/<path>`, `line out of range (file has <n> lines)`, `snippet not found on that line`, `cannot read file: <error>`; `[]` for a cite that holds and for an `http://` or `https://` path. `course._cite_problems` is not changed.

- [ ] **Step 1: Write the failing tests**

`FactProblemsCase` in `tests/test_cite_check.py`, over the module's `SOURCE` written to `<tmp>/src.txt` with `root = <tmp>`:
- `test_good_cite_has_no_problem`: `fact_problems("src.txt", 1, "alpha beta", root) == []`.
- `test_long_snippet`: `THIRTEEN` on line 1 → `["snippet has 13 words (max 12)", "snippet not found on that line"]`.
- `test_missing_file`: `"none.txt"` → `["file missing: <root>/none.txt"]`.
- `test_line_out_of_range`: line 9 → `["line out of range (file has 3 lines)"]`.
- `test_snippet_not_on_that_line`: `"gamma delta"` on line 2 → `["snippet not found on that line"]`.
- `test_url_path_has_no_problem`: `"https://example.com/x"` → `[]`.

`CheckCase` additions in `tests/test_onboard.py` (helpers of Task 3; `N = line count of OrderController.java`):
- `test_flow_heading_without_an_id_is_a_section_fault` (Task 3) now expects, after the `section:` line, `entry #<n>: flow cancel not in Flows` for each of the two entry lines that name `cancel`.
- `test_cite_snippet_too_long`: the first `Shape` snippet replaced by thirteen words → `cite Shape#1: snippet has 13 words (max 12)`, `cite Shape#1: snippet not found on that line`.
- `test_cite_file_missing`: the path of the first `Shape` cite replaced by `missing/X.java` → `cite Shape#1: file missing: <TREE>/missing/X.java`.
- `test_cite_line_out_of_range`: the line of the `- recv:` cite set to 9999 → `cite Flows/order#1: line out of range (file has N lines)`.
- `test_cite_snippet_not_on_line`: the `- recv:` snippet replaced by `not on this line` → `cite Flows/order#1: snippet not found on that line`.
- `test_fact_without_a_cite`: the ` | ` tail of the first `Shape` fact cut → `cite Shape#1: no cite`.
- `test_not_covered_lines_need_no_cite`: a second `Not covered` bullet without a cite → `onboard: ok`.
- `test_entry_without_flow_or_reason`: `-> not traced: <reason>` of one entry line replaced by `-> not traced:` → `entry #<n>: no flow id and no reason`; the same for a line with no `->` at all.
- `test_entry_flow_not_in_flows`: `-> order` replaced by `-> orders` → `entry #<n>: flow orders not in Flows`.
- `test_other_systems_line_without_a_handle`: the backticks cut from the `Payments` line → `fact Other systems#1: no handle in backticks`.
- `test_inventory_of_the_tree_is_accounted_for`: `inventory` run on `TREE` with `--out <tmp>/inv.txt`, then `check(inventory=<tmp>/inv.txt)` → 0, `onboard: ok`.
- `test_inventory_line_not_in_entry_points`: the inventory file plus one line `src/main/java/shop/Order.java:3\tmain\tx` → `inventory src/main/java/shop/Order.java:3: not in Entry points`; and with the `@GetMapping` entry line removed from the map → `inventory <its path:line>: not in Entry points`.
- `test_inventory_summary_line_is_skipped`: the saved stdout of `inventory` (with its last line) as the file → `onboard: ok`.
- `test_inventory_matched_elsewhere_still_fails`: an entry line's cite moved to a `Shape` fact (the entry line deleted) → the `inventory …: not in Entry points` line.
- `test_every_fault_is_listed_before_the_summary`: a map with a missing section, a node without a fact and a long snippet → the three lines in the order section, node, cite, then `onboard: 3 failures`, exit 1.
- `test_map_without_title_cannot_be_read`: a file `## Shape\n` → 2, stdout == `map: cannot read <path>: no "# Map:" title\n`, stderr empty.
- `test_missing_map_cannot_be_read`: a missing path → 2, stdout starts with `map: cannot read <path>:`.
- `test_root_not_a_directory_exits_2`: `--root <tmp>/none` → 2, stderr == `onboard: cannot read root <tmp>/none\n`, stdout empty.
- `test_missing_inventory_file_exits_2`: `--inventory <tmp>/none.txt` → 2, stderr == `onboard: cannot read inventory <tmp>/none.txt\n`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -B -m unittest discover -s tests -p "test_cite_check.py" -k FactProblemsCase -v`
Expected: `AttributeError: module 'cite_check' has no attribute 'fact_problems'`.

Run: `python3 -B -m unittest discover -s tests -p "test_onboard.py" -k CheckCase -v`
Expected: the new tests fail on `onboard: ok` where a failure line is expected (and on exit 0 where 2 is expected).

- [ ] **Step 3: Implement `fact_problems` and the four rule groups**

- `cite_check.fact_problems(path, line, snippet, root)`: build the `values` dict that `_check_cite` reads (`data-path`, `data-line` as `str(line)`, `data-snippet`), call `_check_cite(1, values, root, "<basename>:<line>")` and strip the label `cite 1 (<path>:<line>): ` from each message, as `course._cite_problems` does today. A docstring names `course.py` and `onboard.py` as its callers.
- `check_map`, appended groups in this order after Task 3's lines: (a) `entry` lines, (b) `fact Other systems#<n>` lines, (c) `cite` lines, (d) `inventory` lines.
  - (a) For each fact of `Entry points` (none when `none_found`): split the fact part at its last ` -> `; no ` -> `, or a tail that is neither `not traced: <reason>` nor `not an entry point: <reason>` with a non-blank reason nor an `ID` fullmatch → `entry #<n>: no flow id and no reason`; an id tail that is not the `ident` of a flow under `Flows` → `entry #<n>: flow <id> not in Flows`.
  - (b) For each fact of `Other systems`: no `` `…` `` in the fact part → `fact Other systems#<n>: no handle in backticks`.
  - (c) For every fact of every section except `Not covered`, in canonical section order, the section's own facts first and then, for `Flows`, each flow's facts in document order: `cite is None` → `cite <scope>#<n>: no cite`; else `cite <scope>#<n>: <problem>` for each problem of `fact_problems(path, line, snippet, root)`. `<scope>` is the title as written, or `Flows/<flow-id>` (a flow with `ident None` uses its heading).
  - (d) With an inventory: for each line in file order, skip a line without a tab; take the text before the first tab as `<path>:<line>`; when no `Entry points` fact has a cite whose `path:line` equals it → `inventory <path>:<line>: not in Entry points`.
- `cmd_check`: the inventory lines read in Task 3 are passed to `check_map`.

- [ ] **Step 4: Run the scoped tests to verify they pass**

Run: `python3 -B -m unittest discover -s tests -p "test_cite_check.py" -v`
Expected: every test `ok`, `FactProblemsCase` included.

Run: `python3 -B -m unittest discover -s tests -p "test_onboard.py" -v`
Expected: every test `ok`.

- [ ] **Step 5: Run the full suite**

Run: `python3 -B -m unittest discover -s tests`
Expected: the last line is `OK` or `OK (skipped=<n>)`, no `FAILED`; then `pgrep -f "mermaid\."` and `pgrep -f "verify\."` print nothing.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/scripts/onboard.py skills/explain/scripts/cite_check.py skills/explain/tests/test_onboard.py skills/explain/tests/test_cite_check.py
git commit -m "feat: explain: onboard.py check verifies cites, entry lines and the inventory of a map"
```
