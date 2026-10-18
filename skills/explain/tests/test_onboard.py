"""Tests for onboard.py: the Mermaid node parser, the map reader and the command line
(spec sections 6 and 7)."""

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import cite_check  # noqa: E402
import onboard  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "onboard"
TREE = FIXTURES / "tree"

GOOD = """# Map: demo

## Shape
- language: Java 21 service built with Gradle | build.gradle.kts:3 | java toolchain 21
- build: none found
```text
src/
- main/java/demo
```

## Architecture
```mermaid
flowchart LR
  api[HTTP API] --> db[(orders table)]
```
- api: takes the send requests | src/A.java:12 | @PostMapping
- db: holds the orders | src/Repo.java:4 | interface OrderRepo

## Entry points
- http POST /send -> send | src/A.java:12 | @PostMapping
- kafka orders.cancel -> cancel | src/L.java:8 | @KafkaListener(topics = "orders.cancel")

## Flows
### send: What happens to a send?
```mermaid
flowchart TD
  recv[receive the body] --> check{over the limit?}
  check -->|no| store[(orders table)]
```
- recv: the controller takes the body | src/A.java:13 | public Reply send(Order order)
- check: the total is checked against the limit | src/A.java:14 | if (order.total() > limit)
- store: the order row is saved | src/A.java:15 | repo.save(order)

### cancel: How is a send cancelled?
```mermaid
flowchart TD
  listen[read the cancel event]
```
- listen: the listener reads the event | src/L.java:9 | void onCancel(String id)

## State
none found

## Formats and transforms
- JSON bodies by Jackson | src/A.java:2 | import com.fasterxml.jackson

## Routing config
- none found

## Error paths
- a bad body is a 400 | src/A.java:20 | return ResponseEntity.badRequest()

## Other systems
- Kafka: `orders.cancel` | src/L.java:8 | @KafkaListener(topics = "orders.cancel")

## Conventions
- tests: none found

## Where to look
- add-http: `src/` | src/A.java:12 | @PostMapping

## Not covered
- cmd/tools: generated code
"""


def run(argv):
    """Run main with argv; return the exit code, stdout and stderr."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = onboard.main(argv)
    return code, out.getvalue(), err.getvalue()


def read(name):
    """The text of the fixture file `name`."""
    return (FIXTURES / name).read_text(encoding="utf-8")


def replace_once(text, old, new):
    if old not in text:
        raise AssertionError("%r is not in the text" % old)
    return text.replace(old, new, 1)


class MermaidNodesCase(unittest.TestCase):
    def test_flowchart_nodes_in_order_once_each(self):
        self.assertEqual(
            onboard.mermaid_nodes(read("parser-flow.mmd")),
            ["recv", "kind", "route", "cancel", "reply", "store", "audit", "note", "done"],
        )

    def test_arrow_inside_a_quoted_label_is_not_an_edge(self):
        block = 'flowchart TD\n  a["send --> partner [async]"] --> b\n'
        self.assertEqual(onboard.mermaid_nodes(block), ["a", "b"])
        edge_text = 'flowchart TD\n  a -- "x --> y" --> b\n'
        self.assertEqual(onboard.mermaid_nodes(edge_text), ["a", "b"])

    def test_edge_to_a_subgraph_id_is_not_a_node(self):
        block = "flowchart LR\n  subgraph svc[The service]\n    recv --> store\n  end\n  api --> svc\n"
        self.assertEqual(onboard.mermaid_nodes(block), ["recv", "store", "api"])

    def test_edge_text_is_not_a_node(self):
        block = "flowchart TD\n  a -. retry .-> b\n  c -- rock & roll --> d\n  e == rock & roll ==> f\n"
        self.assertEqual(onboard.mermaid_nodes(block), ["a", "b", "c", "d", "e", "f"])

    def test_shape_labels_hide_their_operators(self):
        block = "flowchart TD\n  a[rock & roll] --> b(send --> c)\n  d{x & y} --> e>z & w]\n"
        self.assertEqual(onboard.mermaid_nodes(block), ["a", "b", "d", "e"])

    def test_subgraph_and_statements_are_not_nodes(self):
        nodes = onboard.mermaid_nodes(read("parser-flow.mmd"))
        for word in ("svc", "direction", "classDef", "class", "click", "end", "ext"):
            self.assertNotIn(word, nodes)

    def test_state_names_in_order_without_start_and_end(self):
        self.assertEqual(
            onboard.mermaid_nodes(read("parser-state.mmd")),
            ["New", "Paid", "Shipped", "Cancelled", "Held", "Packed", "Sent"],
        )

    def test_state_note_with_an_arrow_adds_no_state(self):
        block = "stateDiagram-v2\n  A --> B\n  note right of B: then --> C\n"
        self.assertEqual(onboard.mermaid_nodes(block), ["A", "B"])

    def test_statements_separated_by_semicolons(self):
        self.assertEqual(onboard.mermaid_nodes("flowchart TD\n  a --> b; c --> d\n"), ["a", "b", "c", "d"])
        self.assertEqual(onboard.mermaid_nodes("flowchart TD\n  a[x; y] --> b\n"), ["a", "b"])
        self.assertEqual(onboard.mermaid_nodes("flowchart TD\n  a --> b; style a fill:#f00\n"), ["a", "b"])
        self.assertEqual(onboard.mermaid_nodes("flowchart TD\n  subgraph s; a --> b; end\n"), ["a", "b"])
        self.assertEqual(onboard.mermaid_nodes("flowchart TD\n  a -- x; y --> b\n"), ["a", "b"])

    def test_kind_of_each_first_line(self):
        self.assertEqual(onboard.mermaid_kind("flowchart TD\n  a --> b\n"), onboard.FLOWCHART)
        self.assertEqual(onboard.mermaid_kind("flowchart LR\n  a --> b\n"), onboard.FLOWCHART)
        self.assertEqual(onboard.mermaid_kind("stateDiagram-v2\n  [*] --> A\n"), onboard.STATE)
        for block in ("graph TD\n  a --> b\n", "flowchart TB\n  a --> b\n", "sequenceDiagram\n  A->>B: hi\n", ""):
            self.assertIsNone(onboard.mermaid_kind(block), block)
        self.assertEqual(onboard.mermaid_kind("\nflowchart TD\n  a --> b\n"), onboard.FLOWCHART)


class ParseMapCase(unittest.TestCase):
    def setUp(self):
        self.doc = onboard.parse_map(GOOD)

    def test_title_and_section_titles_in_document_order(self):
        self.assertEqual(self.doc.ident, "demo")
        self.assertEqual([s.title for s in self.doc.sections], list(onboard.TITLES))

    def test_flows_carry_id_question_diagram_and_facts(self):
        flows = self.doc.section("Flows").flows
        self.assertEqual([f.ident for f in flows], ["send", "cancel"])
        send = flows[0]
        self.assertEqual(send.question, "What happens to a send?")
        self.assertEqual([d.kind for d in send.diagrams], [onboard.FLOWCHART])
        self.assertEqual([f.n for f in send.facts], [1, 2, 3])

    def test_fact_line_splits_into_fact_and_cite(self):
        first = self.doc.section("Entry points").facts[0]
        self.assertEqual(first.fact, "http POST /send -> send")
        self.assertEqual(first.cite, ("src/A.java", 12, "@PostMapping"))
        bare = self.doc.section("Not covered").facts[0]
        self.assertIsNone(bare.cite)
        self.assertEqual(bare.fact, "cmd/tools: generated code")

    def test_cite_with_an_empty_snippet_is_no_cite(self):
        text = replace_once(GOOD, "## Shape\n", "## Shape\n- g | a/b.txt:1 | \n")
        fact = onboard.parse_map(text).section("Shape").facts[0]
        self.assertIsNone(fact.cite)
        self.assertEqual(fact.fact, "g")

    def test_cite_path_before_the_colon_is_stripped(self):
        text = replace_once(GOOD, "## Shape\n", "## Shape\n- g | a/b.txt :1 | x\n")
        self.assertEqual(onboard.parse_map(text).section("Shape").facts[0].cite, ("a/b.txt", 1, "x"))

    def test_none_found_marks_the_section(self):
        state = self.doc.section("State")
        self.assertTrue(state.none_found)
        self.assertEqual((state.diagrams, state.facts), ([], []))
        self.assertFalse(self.doc.section("Flows").none_found)
        routing = self.doc.section("Routing config")
        self.assertTrue(routing.none_found)
        self.assertEqual(routing.facts, [])

    def test_none_found_with_a_block_is_not_empty(self):
        block = "```mermaid\nstateDiagram-v2\n  [*] --> A\n```\n"
        text = replace_once(GOOD, "## State\nnone found\n", "## State\nnone found\n" + block)
        state = onboard.parse_map(text).section("State")
        self.assertFalse(state.none_found)
        self.assertEqual(len(state.diagrams), 1)

    def test_fenced_text_block_is_not_a_diagram_and_hides_its_bullets(self):
        shape = self.doc.section("Shape")
        self.assertEqual(shape.diagrams, [])
        self.assertEqual([f.fact for f in shape.facts], ["language: Java 21 service built with Gradle", "build: none found"])

    def test_flow_heading_without_an_id_keeps_the_heading(self):
        text = replace_once(GOOD, "### cancel: How is a send cancelled?", "### Order flow")
        flow = onboard.parse_map(text).section("Flows").flows[1]
        self.assertIsNone(flow.ident)
        self.assertEqual(flow.heading, "Order flow")

    def test_flow_nodes_maps_each_flow_to_its_node_ids(self):
        self.assertEqual(onboard.flow_nodes(self.doc), {"send": ["recv", "check", "store"], "cancel": ["listen"]})

    def test_map_without_title_cannot_be_read(self):
        with self.assertRaises(ValueError) as caught:
            onboard.parse_map("## Shape\n")
        self.assertEqual(str(caught.exception), 'no "# Map:" title')
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "map.md")
            Path(path).write_text("## Shape\n", encoding="utf-8")
            missing = os.path.join(tmp, "none.md")
            for target in (path, missing):
                with self.assertRaises(onboard.OnboardError) as caught:
                    onboard.read_map(target)
                self.assertTrue(str(caught.exception).startswith("map: cannot read %s:" % target), caught.exception)
                self.assertEqual(caught.exception.code, 2)

    def test_map_with_a_bom_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "map.md")
            Path(path).write_text("\ufeff" + GOOD, encoding="utf-8")
            self.assertEqual(onboard.read_map(path).ident, "demo")


JAVA_DIR = "src/main/java/shop/"
PLANTED = [
    (JAVA_DIR + "ShopApplication.java", "public static void main", "main"),
    (JAVA_DIR + "OrderController.java", "@PostMapping", "http"),
    (JAVA_DIR + "OrderController.java", '@GetMapping("/{id}")', "http"),
    (JAVA_DIR + "OrderController.java", "@RequestMapping(method", "http"),
    (JAVA_DIR + "OrderListener.java", '@KafkaListener(topics = "orders.cancel")', "listener"),
    (JAVA_DIR + "ShopRoutes.java", 'from("jms:queue:shop.in")', "route"),
    ("src/main/kotlin/shop/StockJobs.kt", "@Scheduled(cron", "schedule"),
    ("src/main/kotlin/shop/StockJobs.kt", "class StockDelegate : JavaDelegate", "listener"),
    ("src/main/kotlin/shop/StockJobs.kt", "fun main(", "main"),
    ("cmd/shop-gw/main.go", "func main(", "main"),
    ("cmd/shop-gw/main.go", 'r.GET("/health"', "http"),
    ("cmd/shop-gw/main.go", 'http.HandleFunc("/metrics"', "http"),
    ("cmd/shop-gw/main.go", "consumer.Consume(ctx", "listener"),
    ("cmd/shop-gw/main.go", "time.NewTicker(", "schedule"),
    ("cmd/shop-gw/main.go", "pb.RegisterShopServer(", "route"),
    ("routes/stock.camel.yaml", "- from:", "route"),
    ("routes/stock.camel.yaml", "- from: {", "route"),
    ("config/camel-context.xml", '<from uri="jms:queue:legacy.in"/>', "route"),
]


def line_of(rel, needle):
    """The 1-based line of the first line of TREE/rel that holds `needle`."""
    for number, text in enumerate((TREE / rel).read_text(encoding="utf-8").splitlines(), 1):
        if needle in text:
            return number
    raise AssertionError("%s lacks %s" % (rel, needle))


def triples(hits):
    return [(hit.path, hit.line, hit.kind) for hit in hits]


def hits_of(rel):
    """The hits of the committed tree in one file, by line."""
    return {hit.line: hit for hit in onboard.inventory(TREE, TREE) if hit.path == rel}


class InventoryCase(unittest.TestCase):
    def test_tree_lists_each_planted_entry_point_once_and_nothing_else(self):
        hits = onboard.inventory(TREE, TREE)
        expected = sorted((rel, line_of(rel, needle), kind) for rel, needle, kind in PLANTED)
        self.assertEqual(len(expected), 18)
        self.assertEqual(triples(hits), expected)
        for hit in hits:
            for skipped in ("Test.java", "_test.go", "Spec.kt", "src/test"):
                self.assertNotIn(skipped, hit.path)

    def test_skipped_directories_are_pruned(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "tree"
            shutil.copytree(TREE, copy)
            for skipped in ("target", "build", "node_modules", "vendor", ".git", "tests", "src/test"):
                planted = copy / skipped / "Planted.java"
                planted.parent.mkdir(parents=True, exist_ok=True)
                planted.write_text('@GetMapping("/planted")\n', encoding="utf-8")
            self.assertEqual(triples(onboard.inventory(copy, copy)), triples(onboard.inventory(TREE, TREE)))

    def test_class_level_request_mapping_is_not_a_hit(self):
        rel = JAVA_DIR + "OrderController.java"
        hits = hits_of(rel)
        self.assertNotIn(line_of(rel, '@RequestMapping("/orders")'), hits)
        self.assertEqual(hits[line_of(rel, "@RequestMapping(method")].kind, "http")

    def test_method_level_request_mapping_over_an_object_parameter_is_a_hit(self):
        source = (
            '@RequestMapping("/orders")\n'
            "@RestController\n"
            "public class Orders {\n"
            "    @RequestMapping(method = RequestMethod.POST)\n"
            "    public void save(@RequestBody Object object) {}\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Orders.java"
            path.write_text(source, encoding="utf-8")
            hits = onboard.scan_file(str(path), "Orders.java")
        self.assertEqual([(hit.line, hit.kind) for hit in hits], [(4, "http")])

    def test_request_mapping_on_an_annotation_type_is_not_a_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Post.java"
            source = "@RequestMapping(method = RequestMethod.POST)\npublic @interface Post {}\n"
            path.write_text(source, encoding="utf-8")
            self.assertEqual(onboard.scan_file(str(path), "Post.java"), [])

    def test_request_mapping_over_an_annotated_class_line_is_not_a_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "X.java"
            path.write_text('@RequestMapping("/orders")\n@Deprecated public class X {\n}\n', encoding="utf-8")
            self.assertEqual(onboard.scan_file(str(path), "X.java"), [])

    def test_from_outside_a_route_builder_is_not_a_hit(self):
        self.assertEqual(hits_of(JAVA_DIR + "ReportQuery.java"), {})
        rel = JAVA_DIR + "ShopRoutes.java"
        self.assertEqual(hits_of(rel)[line_of(rel, 'from("jms:queue:shop.in")')].kind, "route")

    def test_camel_yaml_from_without_inline_uri_takes_the_next_line(self):
        rel = "routes/stock.camel.yaml"
        hits = hits_of(rel)
        self.assertEqual(hits[line_of(rel, "- from:")].text, '- from: uri: "kafka:stock.updates"')
        self.assertEqual(hits[line_of(rel, "- from: {")].text, '- from: { uri: "timer:stock" }')

    def test_text_is_squashed_and_cut_to_120(self):
        line = '@GetMapping \t ( \t "/' + "x" * 278 + '")'
        self.assertEqual(len(line), 300)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Big.java"
            path.write_text(line + "\n", encoding="utf-8")
            (hit,) = onboard.scan_file(str(path), "Big.java")
        self.assertEqual(hit.text, '@GetMapping ( "/' + "x" * 104)

    def test_a_line_hits_once_with_the_first_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "main.go"
            path.write_text('\tr.GET("/x", h); c := cron.New()\n', encoding="utf-8")
            hits = onboard.scan_file(str(path), "main.go")
        self.assertEqual([(hit.line, hit.kind) for hit in hits], [(1, "http")])

    def test_cli_prints_the_lines_then_the_count_and_writes_out(self):
        lines = [onboard.inventory_line(hit) for hit in onboard.inventory(TREE, TREE)]
        main_line = line_of("cmd/shop-gw/main.go", "func main(")
        self.assertIn("cmd/shop-gw/main.go:%d\tmain\tfunc main() {" % main_line, lines)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "inv.txt"
            code, stdout, stderr = run(["inventory", str(TREE), "--root", str(TREE), "--out", str(out)])
            written = out.read_text(encoding="utf-8")
        self.assertEqual(code, 0)
        self.assertEqual(len(lines), 18)
        self.assertEqual(stdout, "".join(line + "\n" for line in lines) + "inventory: 18 entry points\n")
        self.assertEqual(written, "".join(line + "\n" for line in lines))
        self.assertEqual(stderr, "")

    def test_paths_are_relative_to_root(self):
        code, stdout, _ = run(["inventory", str(TREE), "--root", str(TREE.parent)])
        hit_lines = [line for line in stdout.splitlines() if "\t" in line]
        self.assertEqual(code, 0)
        self.assertEqual(len(hit_lines), 18)
        for line in hit_lines:
            self.assertTrue(line.startswith("tree/"), line)

    def test_source_outside_root_is_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, root = Path(tmp) / "a", Path(tmp) / "b"
            source.mkdir()
            root.mkdir()
            code, stdout, stderr = run(["inventory", str(source), "--root", str(root)])
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr.startswith("usage:"), stderr)
        self.assertIn(str(source), stderr)

    def test_missing_source_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "none"
            code, stdout, stderr = run(["inventory", str(missing), "--root", tmp])
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "onboard: cannot read %s\n" % missing)

    def test_unreadable_file_in_the_tree_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "tree"
            shutil.copytree(TREE, copy)
            os.symlink(copy / "missing-target", copy / JAVA_DIR / "Broken.java")
            code, stdout, stderr = run(["inventory", str(copy), "--root", str(copy)])
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr.startswith("onboard: cannot read"), stderr)
        self.assertIn("Broken.java", stderr)

    @unittest.skipUnless(os.geteuid() != 0, "root can list any directory")
    def test_unreadable_directory_in_the_tree_exits_2(self):
        copy = Path(self.enterContext(tempfile.TemporaryDirectory())) / "tree"
        shutil.copytree(TREE, copy)
        locked = copy / JAVA_DIR / "locked"
        locked.mkdir()
        (locked / "Hidden.java").write_text('@GetMapping("/hidden")\n', encoding="utf-8")
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o700)
        code, stdout, stderr = run(["inventory", str(copy), "--root", str(copy)])
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr.startswith("onboard: cannot read"), stderr)
        self.assertIn(str(locked), stderr)

    def test_missing_root_flag_is_usage(self):
        code, stdout, stderr = run(["inventory", str(TREE)])
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr.startswith("usage:"), stderr)


MAP = read("map.md")


def check(text=MAP, edits=(), inventory=None):
    """Run check on `text` after each (old, new) edit, applied once; return the exit code, stdout and stderr."""
    for old, new in edits:
        text = replace_once(text, old, new)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "map.md")
        Path(path).write_text(text, encoding="utf-8")
        argv = ["check", path, "--root", str(TREE)]
        if inventory is not None:
            argv += ["--inventory", str(inventory)]
        return run(argv)


def failures(out):
    """Every stdout line but the summary line."""
    return out.splitlines()[:-1]


def line_starting(prefix):
    """The first line of MAP that starts with `prefix`."""
    return next(line for line in MAP.splitlines() if line.startswith(prefix))


def section_text(title):
    """The `## <title>` section of MAP, heading included, up to the next level-2 heading."""
    start = MAP.index("## %s\n" % title)
    end = MAP.find("\n## ", start)
    return MAP[start : end + 1 if end >= 0 else len(MAP)]


def section_body(title):
    """The section of MAP without its heading line."""
    return section_text(title).split("\n", 1)[1]


def block_after(anchor):
    """The mermaid block of MAP, fences included, that first follows `anchor`."""
    start = MAP.index("```mermaid\n", MAP.index(anchor))
    return MAP[start : MAP.index("```\n", start + 3) + 4]


ARCH = block_after("## Architecture")
ORDER = block_after("### order:")
CANCEL = block_after("### cancel:")
STATE_BLOCK = block_after("## State")
OK = (0, "onboard: ok\n", "")
SHAPE_1 = section_text("Shape").splitlines()[1]
RECV = line_starting("- recv:")
GET_ENTRY = line_starting("- http GET /orders/{id}")
THIRTEEN = " ".join("w%d" % n for n in range(1, 14))


def with_part(line, index, new):
    """A fact `line` with its ` | `-separated part `index` (0 fact, 1 cite, 2 snippet) replaced by `new`."""
    parts = line.split(" | ")
    return " | ".join(parts[:index] + [new] + parts[index + 1 :])


class CheckCase(unittest.TestCase):
    def only(self, *expected, **kw):
        """check(**kw) prints exactly the `expected` failures, then their count, and exits 1."""
        code, out, err = check(**kw)
        self.assertEqual((failures(out), err), (list(expected), ""))
        self.assertEqual(out.splitlines()[-1:], ["onboard: %d failures" % len(expected)])
        self.assertEqual(code, 1)

    def test_good_map_is_ok(self):
        self.assertEqual(check(), OK)

    def test_missing_section_names_the_title(self):
        self.only("section: missing Routing config", edits=[(section_text("Routing config"), "")])

    def test_section_out_of_order(self):
        state = section_text("State")
        moved = [(state, ""), ("## Not covered\n", state + "## Not covered\n")]
        self.only("section: State out of order", edits=moved)

    def test_section_twice(self):
        first_fact = section_text("Shape").splitlines()[1]
        self.only("section: Shape twice", text=MAP + "\n## Shape\n%s\n" % first_fact)

    def test_flow_heading_without_an_id_is_a_section_fault(self):
        self.only(
            "section: Flows heading Cancel flow has no flow id",
            "entry #12: flow cancel not in Flows",
            "entry #13: flow cancel not in Flows",
            edits=[("### cancel: How is an order cancelled?", "### Cancel flow")],
        )

    def test_diagram_none(self):
        nodes = ("api", "repo", "listener", "payments", "kafka")
        self.only(
            "diagram architecture: none", *("fact architecture/%s: not a node" % node for node in nodes),
            edits=[(ARCH, "")],
        )

    def test_two_blocks_in_one_place(self):
        self.only("diagram order: 2 blocks, more than 1", edits=[(ORDER, ORDER + ORDER)])

    def test_diagram_not_flowchart_or_state(self):
        sequence = replace_once(ORDER, "```mermaid\nflowchart TD\n", "```mermaid\nsequenceDiagram\n")
        self.only("diagram order: not flowchart or stateDiagram-v2", edits=[(ORDER, sequence)])

    def test_state_block_in_a_flow_is_not_flowchart(self):
        self.only("diagram order: not flowchart", edits=[(ORDER, STATE_BLOCK)])

    def test_flow_block_in_state_is_not_state(self):
        self.only("diagram state: not stateDiagram-v2", edits=[(STATE_BLOCK, CANCEL)])

    def test_more_than_25_nodes(self):
        cite = line_starting("- listen:").split(" | ", 1)[1]
        chain = "".join("  n%d --> n%d\n" % (n, n + 1) for n in range(1, 26))
        facts = "".join("- n%d: step %d | %s\n" % (n, n, cite) for n in range(1, 27))
        last = line_starting("- next:") + "\n"
        self.only(
            "diagram cancel: 31 nodes, more than 25",
            edits=[(CANCEL, CANCEL[: -len("```\n")] + chain + "```\n"), (last, last + facts)],
        )

    def test_node_without_a_fact_line(self):
        self.only("node order/publish: no fact line", edits=[(line_starting("- publish:") + "\n", "")])

    def test_fact_that_is_not_a_node(self):
        self.only(
            "node order/reply: no fact line", "fact order/answer: not a node", edits=[("- reply:", "- answer:")]
        )

    def test_fact_twice(self):
        charge = line_starting("- charge:") + "\n"
        self.only("fact order/charge: two lines", edits=[(charge, charge + charge)])

    def test_fact_without_a_key_is_not_a_node(self):
        self.only(
            "node order/save: no fact line", "fact order/the: not a node",
            edits=[("- save: the order row |", "- the order row is saved |")],
        )

    def test_bad_node_id(self):
        self.only("node order/Recv: bad id", edits=[("  recv[", "  Recv["), ("- recv:", "- Recv:")])

    def test_none_found_in_architecture_and_state_skips_the_diagram_rules(self):
        edits = [(section_body(title), "none found\n\n") for title in ("Architecture", "State")]
        self.assertEqual(check(edits=edits), OK)

    def test_none_found_with_a_diagram_is_a_normal_section(self):
        self.assertEqual(check(edits=[("## Architecture\n", "## Architecture\nnone found\n")]), OK)

    def test_flows_none_found_skips_the_flows(self):
        later = " -> not traced: later |"
        edits = [(section_body("Flows"), "none found\n\n"), (" -> order |", later), (" -> cancel |", later),
                 (" -> cancel |", later)]
        self.assertEqual(check(edits=edits), OK)

    def tmp(self, name):
        """The path `name` inside a temp directory removed after the test."""
        return os.path.join(self.enterContext(tempfile.TemporaryDirectory()), name)

    def inventory_out(self):
        """Run `inventory` on TREE with `--out <tmp>/inv.txt`; return that path and the stdout."""
        path = self.tmp("inv.txt")
        code, stdout, _ = run(["inventory", str(TREE), "--root", str(TREE), "--out", path])
        self.assertEqual(code, 0)
        return path, stdout

    def test_cite_snippet_too_long(self):
        self.only(
            "cite Shape#1: snippet has 13 words (max 12)", "cite Shape#1: snippet not found on that line",
            edits=[(SHAPE_1, with_part(SHAPE_1, 2, THIRTEEN))],
        )

    def test_cite_file_missing(self):
        self.only(
            "cite Shape#1: file missing: %s" % os.path.join(str(TREE), "missing/X.java"),
            edits=[(SHAPE_1, with_part(SHAPE_1, 1, "missing/X.java:2"))],
        )

    def test_cite_line_out_of_range(self):
        path = RECV.split(" | ")[1].rsplit(":", 1)[0]
        lines = len(cite_check._read_lines(str(TREE / path)))
        self.only(
            "cite Flows/order#1: line out of range (file has %d lines)" % lines,
            edits=[(RECV, with_part(RECV, 1, path + ":9999"))],
        )

    def test_cite_snippet_not_on_line(self):
        self.only(
            "cite Flows/order#1: snippet not found on that line", edits=[(RECV, with_part(RECV, 2, "not on this line"))]
        )

    def test_fact_without_a_cite(self):
        self.only("cite Shape#1: no cite", edits=[(SHAPE_1, SHAPE_1.split(" | ")[0])])

    def test_shape_missing_key(self):
        self.only("shape: missing run", edits=[(line_starting("- run:") + "\n", "")])

    def test_shape_unknown_key_and_old_form(self):
        self.only("shape: missing language", "shape #1: unknown key stack", edits=[("- language:", "- stack:")])
        old_form = SHAPE_1.replace("language: ", "")
        self.only("shape: missing language", "shape #1: unknown key Java", edits=[(SHAPE_1, old_form)])

    def test_shape_line_with_no_words_is_unknown_key_none(self):
        self.only(
            "shape: missing language", "shape #1: unknown key none", "cite Shape#1: no cite", edits=[(SHAPE_1, "- ")]
        )

    def test_shape_key_twice(self):
        self.only("shape: language twice", edits=[(SHAPE_1, SHAPE_1 + "\n" + SHAPE_1)])
        framework = line_starting("- framework:")
        self.assertEqual(check(edits=[(framework, framework + "\n" + framework)]), OK)

    def test_shape_command_needs_backticks(self):
        build = line_starting("- build:")
        self.only("shape #6: no command in backticks", edits=[(build, build.replace("`", ""))])

    def test_shape_none_found_has_no_cite_failure(self):
        run_line = line_starting("- run:")
        self.assertEqual(check(edits=[(run_line, "- run: none found")]), OK)
        shape = onboard.parse_map(GOOD).section("Shape")
        build = next(f for f in shape.facts if f.fact.startswith("build:"))
        self.assertIsNone(build.cite)

    def test_shape_lines_come_before_cite_lines(self):
        build = line_starting("- build:")
        self.only(
            "shape #6: no command in backticks", "cite Shape#1: no cite",
            edits=[(build, build.replace("`", "")), (SHAPE_1, SHAPE_1.split(" | ")[0])],
        )

    def test_shape_language_none_found_still_needs_a_cite(self):
        self.only("cite Shape#1: no cite", edits=[(SHAPE_1, "- language: none found")])

    def test_sections_now_twelve(self):
        self.assertEqual(len(onboard.TITLES), 12)
        self.only("section: missing Conventions", edits=[(section_text("Conventions"), "")])
        where = section_text("Where to look")
        moved = replace_once(MAP, where, "") + "\n" + where
        self.only("section: Where to look out of order", text=moved)

    def test_conventions_missing_topic_and_no_topic(self):
        wiring = line_starting("- wiring:")
        self.only("conventions: missing wiring", edits=[(wiring + "\n", "")])
        example = "- an example | " + wiring.split(" | ", 1)[1]
        self.only("conventions #4: no topic", edits=[(wiring, wiring + "\n" + example)])
        upper = wiring.replace("- wiring:", "- Wiring:")
        self.only("conventions: missing wiring", "conventions #3: no topic", edits=[(wiring, upper)])

    def test_conventions_any_id_topic_is_allowed(self):
        wiring = line_starting("- wiring:")
        self.assertEqual(check(edits=[(wiring, wiring + "\n" + wiring.replace("- wiring:", "- logging:"))]), OK)

    def test_conventions_none_found_has_no_cite_failure(self):
        naming = line_starting("- naming:")
        self.assertEqual(check(edits=[(naming, "- naming: none found")]), OK)

    def test_where_required_keys_follow_the_map(self):
        for key in ("add-route", "add-test"):
            line = line_starting("- %s:" % key)
            self.only("where: missing %s" % key, edits=[(line + "\n", "")])
        routing = [(section_body("Routing config"), "none found\n\n"), (line_starting("- change-routing:") + "\n", "")]
        self.assertEqual(check(edits=routing), OK)
        test = [(line_starting("- test:"), "- test: none found"), (line_starting("- add-test:") + "\n", "")]
        self.assertEqual(check(edits=test), OK)
        transform = [(section_body("Formats and transforms"), "none found\n\n"),
                     (line_starting("- add-transform:") + "\n", "")]
        self.assertEqual(check(edits=transform), OK)
        self.only("where: missing change-routing", edits=[(line_starting("- change-routing:") + "\n", "")])

    def test_where_none_found_section_still_lists_the_required_keys(self):
        keys = ("add-http", "add-listener", "add-route", "add-schedule", "change-routing", "add-transform", "add-test")
        self.only(*("where: missing %s" % key for key in keys), edits=[(section_body("Where to look"), "none found\n\n")])

    def test_where_none_found_line_is_not_a_fact(self):
        http = line_starting("- add-http:")
        self.only("where #1: no path in backticks", "cite Where to look#1: no cite", edits=[(http, "- add-http: none found")])

    def test_where_not_an_entry_point_needs_no_row(self):
        code, out, _ = check()
        self.assertEqual(code, 0)
        for kind in ("main", "grpc", "kafka"):
            self.assertNotIn("add-%s" % kind, out)
        listener = line_starting("- add-listener:")
        self.only("where: missing add-listener", edits=[(listener + "\n", "")])

    def test_where_path_in_backticks_under_root(self):
        http = line_starting("- add-http:")
        self.only("where #1: no path in backticks", edits=[(http, http.replace("`", ""))])
        for path in ("nowhere/", "../", "/etc/", "src/main/java/shop/Missing.java"):
            self.only("where #1: %s not under root" % path, edits=[(http, http.replace("src/main/java/shop/", path, 1))])
        self.assertEqual(check(edits=[(http, http.replace("`src/main/java/shop/`", "`src/main/java/shop/OrderController.java`"))]), OK)

    def test_not_covered_lines_need_no_cite(self):
        self.assertEqual(check(text=MAP + "- src/test: the tests are not read\n"), OK)

    def test_entry_without_flow_or_reason(self):
        self.only(
            "entry #11: no flow id and no reason",
            edits=[("-> not traced: a plain read of one row |", "-> not traced: |")],
        )
        self.only(
            "entry #1: no flow id and no reason",
            edits=[(" -> not an entry point: the start of the Go gateway process |", " |")],
        )

    def test_entry_flow_not_in_flows(self):
        self.only("entry #10: flow orders not in Flows", edits=[(" -> order |", " -> orders |")])

    def test_other_systems_line_without_a_handle(self):
        self.only(
            "fact Other systems#1: no handle in backticks",
            edits=[("`PaymentsClient` `payments.charge`", "PaymentsClient payments.charge")],
        )

    def test_inventory_of_the_tree_is_accounted_for(self):
        path, _ = self.inventory_out()
        self.assertEqual(check(inventory=path), OK)

    def test_inventory_line_not_in_entry_points(self):
        path, _ = self.inventory_out()
        plus = self.tmp("plus.txt")
        extra = "src/main/java/shop/Order.java:3\tmain\tx\n"
        Path(plus).write_text(Path(path).read_text(encoding="utf-8") + extra, encoding="utf-8")
        self.only("inventory src/main/java/shop/Order.java:3: not in Entry points", inventory=plus)
        self.only(
            "inventory %s: not in Entry points" % GET_ENTRY.split(" | ")[1],
            edits=[(GET_ENTRY + "\n", "")], inventory=path,
        )

    def test_inventory_summary_line_is_skipped(self):
        path, stdout = self.inventory_out()
        self.assertTrue(stdout.endswith("\ninventory: 18 entry points\n"), stdout)
        Path(path).write_text(stdout, encoding="utf-8")
        self.assertEqual(check(inventory=path), OK)

    def test_inventory_matched_elsewhere_still_fails(self):
        path, _ = self.inventory_out()
        cite = GET_ENTRY.split(" | ", 1)[1]
        formats = line_starting("- order bodies")
        moved = [(GET_ENTRY + "\n", ""), (formats + "\n", formats + "\n- serves one order by id | %s\n" % cite)]
        self.only("inventory %s: not in Entry points" % GET_ENTRY.split(" | ")[1], edits=moved, inventory=path)

    def test_every_fault_is_listed_before_the_summary(self):
        self.only(
            "section: missing Routing config",
            "node order/publish: no fact line",
            "cite Shape#1: snippet has 13 words (max 12)",
            "cite Shape#1: snippet not found on that line",
            edits=[
                (SHAPE_1, with_part(SHAPE_1, 2, THIRTEEN)),
                (section_text("Routing config"), ""),
                (line_starting("- publish:") + "\n", ""),
            ],
        )

    def test_map_without_title_cannot_be_read(self):
        path = self.tmp("map.md")
        Path(path).write_text("## Shape\n", encoding="utf-8")
        expected = (2, 'map: cannot read %s: no "# Map:" title\n' % path, "")
        self.assertEqual(run(["check", path, "--root", str(TREE)]), expected)

    def test_missing_map_cannot_be_read(self):
        missing = self.tmp("none.md")
        code, out, _ = run(["check", missing, "--root", str(TREE)])
        self.assertEqual(code, 2)
        self.assertTrue(out.startswith("map: cannot read %s:" % missing), out)

    def test_root_not_a_directory_exits_2(self):
        root = self.tmp("none")
        code, out, err = run(["check", str(FIXTURES / "map.md"), "--root", root])
        self.assertEqual((code, out, err), (2, "", "onboard: cannot read root %s\n" % root))

    def test_missing_inventory_file_exits_2(self):
        missing = self.tmp("none.txt")
        code, out, err = run(["check", str(FIXTURES / "map.md"), "--root", str(TREE), "--inventory", missing])
        self.assertEqual((code, out, err), (2, "", "onboard: cannot read inventory %s\n" % missing))


class CliCase(unittest.TestCase):
    def test_usage_without_a_command_exits_2(self):
        code, _, err = run([])
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("usage: onboard.py inventory"), err)

    def test_unknown_command_exits_2(self):
        code, _, err = run(["render"])
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("usage:"), err)


if __name__ == "__main__":
    unittest.main()
