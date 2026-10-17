"""Tests for onboard.py: the Mermaid node parser, the map reader and the command line
(spec sections 6 and 7)."""

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import onboard  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "onboard"

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

    def test_subgraph_and_statements_are_not_nodes(self):
        nodes = onboard.mermaid_nodes(read("parser-flow.mmd"))
        for word in ("svc", "direction", "classDef", "class", "click", "end", "ext"):
            self.assertNotIn(word, nodes)

    def test_state_names_in_order_without_start_and_end(self):
        self.assertEqual(
            onboard.mermaid_nodes(read("parser-state.mmd")),
            ["New", "Paid", "Shipped", "Cancelled", "Held", "Packed", "Sent"],
        )

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
