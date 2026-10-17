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

import onboard  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "onboard"
TREE = FIXTURES / "tree"

GOOD = """# Map: demo

## Shape
- Java 21 service built with Gradle | build.gradle.kts:3 | java toolchain 21
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
        self.assertEqual([f.fact for f in shape.facts], ["Java 21 service built with Gradle"])

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

    def test_missing_root_flag_is_usage(self):
        code, stdout, stderr = run(["inventory", str(TREE)])
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr.startswith("usage:"), stderr)


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
