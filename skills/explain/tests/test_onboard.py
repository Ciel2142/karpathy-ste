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
- listener orders.cancel -> cancel | src/L.java:8 | @KafkaListener(topics = "orders.cancel")

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

## Events
- not an event: `Order`: a plain row, not a message | src/Order.java:3 | class Order

### event.document.signature
- type: the routing key `event.document.signature` | src/E.java:2 | KEY = "event.document.signature"
- stream: the exchange `documents` | src/E.java:3 | EXCHANGE = "documents"
- emits: `Signer` sends it after signing -> send | src/S.java:5 | rabbit.send(KEY)
- consumes: outside: Archive `documents` | src/E.java:3 | EXCHANGE = "documents"

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

    def test_event_entry_keeps_its_name_verbatim_and_owns_its_lines(self):
        events = self.doc.section("Events")
        self.assertEqual([e.name for e in events.events], ["event.document.signature"])
        event = events.events[0]
        self.assertEqual([f.n for f in event.facts], [1, 2, 3, 4])
        self.assertEqual(event.facts[0].cite, ("src/E.java", 2, 'KEY = "event.document.signature"'))
        self.assertEqual([f.fact for f in events.facts], ["not an event: `Order`: a plain row, not a message"])

    def test_only_events_and_flows_open_a_level_3_scope(self):
        text = replace_once(GOOD, "## Error paths\n", "## Error paths\n### Not an event\n- a fault | src/A.java:1 | x\n")
        doc = onboard.parse_map(text)
        self.assertEqual([len(s.events) for s in doc.sections if s.title != "Events"], [0] * 12)
        self.assertIn("a fault", [f.fact for f in doc.section("Error paths").facts])
        self.assertEqual(len(doc.section("Events").events), 1)

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
    (JAVA_DIR + "OrderPlacedEvent.java", "public record OrderPlacedEvent", "event"),
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
        self.assertEqual(len(expected), 19)
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

    def scan(self, name, source):
        """The (line, kind, text) of each hit of a file `name` holding `source`."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            path.write_text(source, encoding="utf-8")
            return [(hit.line, hit.kind, hit.text) for hit in onboard.scan_file(str(path), name)]

    def test_each_event_pattern_hits_once_with_the_kind_event(self):
        cases = (
            ("A.java", "public class OrderPlacedEvent {\n}\n", "public class OrderPlacedEvent {"),
            ("A.java", "public record OrderPlacedEvent(String id) {\n}\n", "public record OrderPlacedEvent(String id) {"),
            ("A.java", "public interface PaidEvent {\n}\n", "public interface PaidEvent {"),
            ("A.kt", "data class StockMovedEvent(val id: String)\n", "data class StockMovedEvent(val id: String)"),
            ("A.kt", "object ShippedEvent\n", "object ShippedEvent"),
            ("A.java", "public class Custom extends ApplicationEvent {\n}\n", "public class Custom extends ApplicationEvent {"),
            ("a.go", "type StockMovedEvent struct {\n}\n", "type StockMovedEvent struct {"),
        )
        for name, source, text in cases:
            with self.subTest(source=source):
                self.assertEqual(self.scan(name, source), [(1, "event", text)])

    def test_each_new_listener_pattern_hits_once_with_the_kind_listener(self):
        cases = (
            ("A.java", "    @EventHandler\n    public void on(OrderPlaced event) {}\n", 1),
            ("A.java", "    @SagaEventHandler(associationProperty = \"id\")\n    public void on(Paid p) {}\n", 1),
            ("A.kt", "    @CommandHandler\n    fun handle(c: Place) {}\n", 1),
            ("a.go", "\tsub := client.SubscribeToAll(ctx, opts)\n", 1),
            ("a.go", "\tsub := client.SubscribeToStream(ctx, \"orders\", opts)\n", 1),
        )
        for name, source, line in cases:
            with self.subTest(source=source):
                hits = self.scan(name, source)
                self.assertEqual([(found_line, kind) for found_line, kind, _ in hits], [(line, "listener")])

    def test_names_that_only_start_with_event_and_the_sourcing_handler_are_no_hit(self):
        cases = (
            ("A.java", "public class EventPoller {\n}\n"),
            ("A.java", "public class EventEnvelope {\n}\n"),
            ("A.java", "public class OrderEventsConfig {\n}\n"),
            ("A.java", "    @EventSourcingHandler\n    public void on(OrderPlaced event) {}\n"),
            ("A.kt", "    @EventSourcingHandler\n    fun on(e: Paid) {}\n"),
        )
        for name, source in cases:
            with self.subTest(source=source):
                self.assertEqual(self.scan(name, source), [])

    def test_event_listener_stays_a_listener_and_the_event_annotation_does_not_match_it(self):
        source = "    @EventListener\n    public void on(Paid p) {}\n    @EventHandler\n    void h() {}\n"
        hits = self.scan("A.java", source)
        self.assertEqual([(line, kind) for line, kind, _ in hits], [(1, "listener"), (3, "listener")])

    def test_annotation_on_its_own_line_hits_at_the_declaration_with_its_text(self):
        for annotation in ("@DomainEvent", "@Event", '@Event(name = "placed")'):
            with self.subTest(annotation=annotation):
                source = "%s\n\n@Deprecated\npublic class Placed {\n}\n" % annotation
                self.assertEqual(self.scan("A.java", source), [(4, "event", "public class Placed {")])

    def test_annotation_and_name_suffix_on_one_declaration_are_one_hit(self):
        source = "@DomainEvent\n@Event\npublic class OrderPlacedEvent {\n}\n"
        self.assertEqual(self.scan("A.java", source), [(3, "event", "public class OrderPlacedEvent {")])

    def test_annotation_and_declaration_on_one_line_are_one_hit(self):
        source = "@DomainEvent public class Placed {\n}\n"
        self.assertEqual(self.scan("A.java", source), [(1, "event", "@DomainEvent public class Placed {")])

    def test_annotation_with_no_declaration_after_it_is_no_hit(self):
        self.assertEqual(self.scan("A.java", "@Event\nprivate String name;\nclass Placed {\n}\n"), [])
        self.assertEqual(self.scan("A.java", "@DomainEvent\n"), [])
        self.assertEqual(self.scan("A.java", "@Event\n// the next class\nclass Placed {\n}\n"), [])

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
        self.assertEqual(len(lines), 19)
        self.assertEqual(stdout, "".join(line + "\n" for line in lines) + "inventory: 18 entry points, 1 event types\n")
        self.assertEqual(written, "".join(line + "\n" for line in lines))
        self.assertEqual(stderr, "")

    def test_paths_are_relative_to_root(self):
        code, stdout, _ = run(["inventory", str(TREE), "--root", str(TREE.parent)])
        hit_lines = [line for line in stdout.splitlines() if "\t" in line]
        self.assertEqual(code, 0)
        self.assertEqual(len(hit_lines), 19)
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
ENTRY_1 = section_text("Events").split("\n\n")[0].split("\n", 1)[1]  # the first entry, heading line included
CONSUME_CITE = line_starting("- consumes: `OrderProjection`").split(" | ", 1)[1]
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
                 (" -> cancel |", later)] + [(" -> order |", " |")] * 3  # the flow links of the three event lines
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
        self.only("shape: language twice", edits=[(SHAPE_1, "\n".join([SHAPE_1] * 3))])
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

    def test_sections_now_thirteen(self):
        self.assertEqual(len(onboard.TITLES), 13)
        self.assertEqual(onboard.TITLES[4:7], ("State", "Events", "Formats and transforms"))
        self.only("section: missing Conventions", edits=[(section_text("Conventions"), "")])
        where = section_text("Where to look")
        moved = replace_once(MAP, where, "") + "\n" + where
        self.only("section: Where to look out of order", text=moved)

    def test_events_section_follows_state_and_precedes_formats(self):
        events = section_text("Events")
        moved = replace_once(MAP, events, "")
        moved = replace_once(moved, "## Not covered\n", events + "## Not covered\n")
        self.only("section: Events out of order", text=moved)

    def test_map_without_an_events_section_reports_only_the_missing_section(self):
        self.only("section: missing Events", edits=[(section_text("Events"), "")])

    def test_events_none_found_is_checked_for_nothing_else(self):
        self.assertEqual(check(edits=[(section_body("Events"), "none found\n\n")]), OK)

    def test_event_name_twice_is_reported_once_for_a_repeated_name(self):
        entry = ENTRY_1
        self.only("event OrderPlacedEvent: twice", edits=[(entry, entry + "\n" + entry)])
        self.only("event OrderPlacedEvent: twice", edits=[(entry, "\n".join([entry] * 3))])
        lower = entry.replace("### OrderPlacedEvent", "### orderplacedevent", 1)
        self.assertEqual(check(edits=[(entry, entry + "\n" + lower)]), OK)

    def test_event_missing_key(self):
        for key in onboard.EVENT_REQUIRED:
            with self.subTest(key=key):
                line = next(l for l in ENTRY_1.splitlines() if l.startswith("- %s:" % key))
                self.only("event OrderPlacedEvent: missing %s" % key, edits=[(line + "\n", "")])
        payload = line_starting("- payload:")
        self.assertEqual(check(edits=[(payload + "\n", "")]), OK)

    def test_event_missing_keys_follow_the_required_order(self):
        lines = [l for l in ENTRY_1.splitlines()[1:]]
        self.only(*("event OrderPlacedEvent: missing %s" % key for key in onboard.EVENT_REQUIRED),
                  edits=[("\n".join(lines) + "\n", "")])

    def test_event_type_payload_and_stream_once(self):
        for key, line in (("type", line_starting("- type:")), ("payload", line_starting("- payload:")),
                          ("stream", line_starting("- stream:"))):
            with self.subTest(key=key):
                name = "orders.created" if key == "payload" else "OrderPlacedEvent"
                self.only("event %s: %s twice" % (name, key), edits=[(line, line + "\n" + line)])
        emits = line_starting("- emits:")
        self.assertEqual(check(edits=[(emits, emits + "\n" + emits)]), OK)

    def test_event_unknown_key(self):
        stream = line_starting("- stream:")
        self.only("event OrderPlacedEvent: missing stream", "event OrderPlacedEvent #2: unknown key sink",
                  edits=[(stream, stream.replace("- stream:", "- sink:"))])
        keyless = stream.replace("- stream: ", "- the ")
        self.only("event OrderPlacedEvent: missing stream", "event OrderPlacedEvent #2: unknown key the",
                  edits=[(stream, keyless)])
        self.only("event OrderPlacedEvent: missing stream", "event OrderPlacedEvent #2: unknown key none",
                  "cite Events/OrderPlacedEvent#2: no cite", edits=[(stream, "- ")])

    def test_event_emits_and_consumes_need_a_component_in_backticks(self):
        emits, outside = line_starting("- emits:"), line_starting("- consumes: outside:")
        self.only("event OrderPlacedEvent #3: no component in backticks",
                  edits=[(emits, emits.replace("`OrderPublisher`", "OrderPublisher"))])
        self.only("event orders.created #5: no component in backticks",
                  edits=[(outside, outside.replace("`orders.created`", "orders.created", 1))])
        ignores = "- consumes: `OrderProjection` ignores: it only logs and acks"
        self.assertEqual(check(edits=[(line_starting("- consumes:"), ignores + " | " + CONSUME_CITE)]), OK)
        self.only("event OrderPlacedEvent #4: no component in backticks",
                  edits=[(line_starting("- consumes:"), "- consumes: OrderProjection ignores: logs | " + CONSUME_CITE)])

    def test_event_type_and_stream_need_no_backticks(self):
        stream = line_starting("- stream:")
        self.assertEqual(check(edits=[(stream, stream.replace("`in-process`", "in-process"))]), OK)

    def test_event_flow_must_be_under_flows(self):
        emits = line_starting("- emits:")
        self.only("event OrderPlacedEvent #3: flow orders not in Flows",
                  edits=[(emits, emits.replace(" -> order |", " -> orders |"))])
        self.assertEqual(check(edits=[(emits, emits.replace(" -> order |", " |"))]), OK)

    def test_event_none_found_needs_no_cite_for_emits_and_consumes(self):
        self.assertEqual(check(edits=[(line_starting("- consumes:"), "- consumes: none found")]), OK)
        self.assertEqual(check(edits=[(line_starting("- emits:"), "- emits: none found")]), OK)
        type_line = line_starting("- type:")
        self.only("cite Events/OrderPlacedEvent#1: no cite", edits=[(type_line, "- type: none found")])

    def test_event_none_found_beside_a_line_fails(self):
        emits = line_starting("- emits:")
        self.only("event OrderPlacedEvent: none found beside a line", edits=[(emits, emits + "\n- emits: none found")])
        both = emits + "\n- emits: none found\n- emits: none found"
        self.only("event OrderPlacedEvent: none found beside a line", edits=[(emits, both)])

    def test_event_outside_without_a_handle_fails(self):
        outside = line_starting("- consumes: outside:")
        self.only("event orders.created #5: no component in backticks",
                  edits=[(outside, outside.replace(" `orders.created`", "", 1))])

    def test_events_line_before_the_first_entry_must_be_a_dismissal(self):
        cite = " | src/main/java/shop/Order.java:3 | public class Order {"
        good = "- not an event: `Order`: a plain row, not a message" + cite
        anchor = "### OrderPlacedEvent"
        self.assertEqual(check(edits=[(anchor, good + "\n\n" + anchor)]), OK)
        for bad in ("- an Order is not an event", "- not an event: Order: a plain row", "- not an event: `Order`",
                    "- not an event: `Order`: ", "- an event: `Order`: a row"):
            with self.subTest(line=bad):
                self.only("events #1: not a dismissal", edits=[(anchor, bad + cite + "\n\n" + anchor)])
        self.only("events #2: not a dismissal", "events #3: not a dismissal",
                  edits=[(anchor, good + "\n- a note" + cite + "\n- b" + cite + "\n\n" + anchor)])
        self.only("cite Events#1: no cite", edits=[(anchor, good.split(" | ")[0] + "\n\n" + anchor)])

    def test_event_cites_are_checked_in_the_scope_of_the_event(self):
        payload = line_starting("- payload:")
        self.only("cite Events/orders.created#2: snippet not found on that line",
                  edits=[(payload, with_part(payload, 2, "public class Missing {"))])
        self.only("cite Events/orders.created#2: no cite", edits=[(payload, payload.split(" | ")[0])])

    def test_event_lines_follow_the_entry_lines_and_precede_the_other_systems_lines(self):
        stream = line_starting("- stream:")
        _, out, _ = check(edits=[
            ("- http POST /orders -> order |", "- http POST /orders -> orders |"),
            (stream, stream.replace("- stream:", "- sink:")),
            ("`PaymentsClient` `payments.charge`", "PaymentsClient payments.charge"),
        ])
        self.assertEqual(failures(out), [
            "entry #10: flow orders not in Flows",
            "event OrderPlacedEvent: missing stream",
            "event OrderPlacedEvent #2: unknown key sink",
            "fact Other systems#1: no handle in backticks",
        ])

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
        """Every http line is dismissed, so Where to look needs no add-http row. Red when the check counts a
        `not an entry point` line as an entry of its kind."""
        http = [line for line in MAP.splitlines() if line.startswith("- http ") and " -> not an entry point:" not in line]
        self.assertEqual(len(http), 4)
        dismissed = []
        for line in http:
            head, _, rest = line.partition(" -> ")
            dismissed.append((line, "%s -> not an entry point: dismissed | %s" % (head, rest.partition(" | ")[2])))
        no_row = [(line_starting("- add-http:") + "\n", "")]
        self.assertEqual(check(edits=dismissed + no_row), OK)
        # One http line that is traced again brings the row back.
        self.only("where: missing add-http", edits=dismissed[1:] + no_row)

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

    def test_entry_kind_is_one_of_the_five_kinds_of_the_inventory(self):
        self.assertEqual(onboard.ENTRY_KINDS, ("http", "listener", "route", "schedule", "main"))
        self.only("entry #13: unknown kind kafka", edits=[("- listener orders.cancel -> cancel", "- kafka orders.cancel -> cancel")])
        self.only("entry #6: unknown kind grpc", edits=[("- route ShopServer ->", "- grpc ShopServer ->")])
        no_kind = "-  | cmd/shop-gw/main.go:9 | func main() {"
        self.only("entry #1: unknown kind none", "entry #1: no flow id and no reason",
                  edits=[(line_starting("- main shop-gw"), no_kind)])

    def test_where_keys_follow_the_entry_kinds(self):
        self.assertEqual(onboard.WHERE_KEYS[:4], tuple("add-" + kind for kind in onboard.WHERE_ENTRY_KINDS))
        self.assertEqual(onboard.WHERE_KEYS[4:], ("change-routing", "add-transform", "add-test"))

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

    def test_unnamed_event_hit_is_not_in_events_and_never_not_in_entry_points(self):
        path, _ = self.inventory_out()
        type_line = line_starting("- type: the record")
        where = type_line.split(" | ")[1]
        entry = ENTRY_1
        self.only("inventory %s: not in Events" % where, edits=[(entry + "\n\n", "")], inventory=path)

    def test_dismissal_clears_an_unnamed_event_hit(self):
        path, _ = self.inventory_out()
        cite = line_starting("- type: the record").split(" | ", 1)[1]
        entry = ENTRY_1
        dismissal = "- not an event: `OrderPlacedEvent`: a view of the record | " + cite
        self.assertEqual(check(edits=[(entry + "\n\n", dismissal + "\n\n")], inventory=path), OK)

    def test_payload_line_names_an_event_hit_as_a_type_line_does(self):
        path, _ = self.inventory_out()
        type_line = line_starting("- type: the record")
        elsewhere = with_part(with_part(type_line, 1, "src/main/java/shop/Order.java:3"), 2, "public class Order {")
        payload = "- payload: the id and the total | " + type_line.split(" | ", 1)[1]
        self.assertEqual(check(edits=[(type_line, elsewhere + "\n" + payload)], inventory=path), OK)
        self.only(
            "inventory %s: not in Events" % type_line.split(" | ")[1],
            edits=[(type_line, elsewhere)], inventory=path,
        )

    def test_events_none_found_still_reports_an_event_hit(self):
        path, _ = self.inventory_out()
        where = line_starting("- type: the record").split(" | ")[1]
        edits = [(section_body("Events"), "none found\n\n")]
        self.only("inventory %s: not in Events" % where, edits=edits, inventory=path)

    def test_inventory_summary_line_is_skipped(self):
        path, stdout = self.inventory_out()
        self.assertTrue(stdout.endswith("\ninventory: 18 entry points, 1 event types\n"), stdout)
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
