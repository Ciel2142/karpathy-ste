"""Tests for puml.py: kind detection and the PlantUML parsers (spec sections 7 and 8)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import puml  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "onboard"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class ActivityCase(unittest.TestCase):
    def setUp(self):
        self.block = fixture("parser-activity.puml")

    def test_kind_is_activity_after_a_title_line(self):
        self.assertEqual(puml.kind(self.block), "activity")

    def test_nodes_are_the_distinct_labels_and_conditions_in_order(self):
        self.assertEqual(puml.parse(self.block).nodes, [
            "read the request",
            "pending states at capacity?",
            "refuse the login",
            "state known?",
            "reply with an error",
            "exchange the code",
            "more pages?",
            "fetch a page",
            "retry the call",
            "still failing?",
            "kind of token",
            "store access",
            "store refresh",
            "send email",
            "close session",
            "see other",
        ])

    def test_outcomes_are_not_nodes(self):
        nodes = puml.parse(self.block).nodes
        for outcome in ("yes", "no", "known", "access", "refresh", "ok"):
            self.assertNotIn(outcome, nodes)

    def test_fixture_has_no_fault(self):
        parsed = puml.parse(self.block)
        self.assertEqual((parsed.faults, parsed.node_faults), ([], []))

    def test_see_action_is_a_node_and_a_hop(self):
        parsed = puml.parse(self.block)
        self.assertIn("see other", parsed.nodes)
        self.assertEqual(parsed.hops, ["other"])

    def test_action_over_two_lines_is_a_fault(self):
        parsed = puml.parse("start\n\n:a long\nlabel;\nstop\n")
        self.assertEqual(parsed.faults, ["action over lines 3-4"])
        self.assertEqual(parsed.nodes, [])

    def test_action_without_a_closing_semicolon_runs_to_the_last_line(self):
        parsed = puml.parse("start\n:never closed\nstop\n")
        self.assertEqual(parsed.faults, ["action over lines 2-3"])
        self.assertEqual(parsed.nodes, [])

    def test_style_lines_are_faults(self):
        block = "\n".join([
            "start",
            "skinparam monochrome true",
            "#pink:x;",
            "split",
            "backward:x;",
            "!include x",
            "!pragma teoz true",
            "<style>",
            "stop",
        ])
        parsed = puml.parse(block)
        self.assertEqual(parsed.faults, [f"style line {n}" for n in range(2, 9)])
        self.assertEqual(parsed.nodes, [])

    def test_startuml_lines_are_style_faults(self):
        parsed = puml.parse("@startuml\nstart\n:a;\nstop\n@enduml\n")
        self.assertEqual(parsed.faults, ["style line 1", "style line 5"])
        self.assertEqual(parsed.nodes, ["a"])

    def test_backtick_label_is_a_bad_id(self):
        parsed = puml.parse("start\n:a `b`;\nstop\n")
        self.assertEqual(parsed.node_faults, [("a `b`", "bad id")])

    def test_unknown_lines_are_ignored(self):
        parsed = puml.parse(
            "start\nlegend\nhide empty description\nleft to right direction\n:a;\nstop\n")
        self.assertEqual((parsed.nodes, parsed.faults, parsed.node_faults), (["a"], [], []))

    def test_condition_keeps_nested_parentheses(self):
        parsed = puml.parse("start\nif (size() >= max) then (yes)\n:a;\nendif\nstop\n")
        self.assertEqual(parsed.nodes, ["size() >= max", "a"])

    def test_kind_is_none_without_start(self):
        self.assertIsNone(puml.kind(":a;\n:b;\n"))

    def test_semicolon_in_a_comment_does_not_close_an_action(self):
        parsed = puml.parse("start\n:a long\n' stray; comment\nlabel;\nstop\n")
        self.assertEqual(parsed.faults, ["action over lines 2-4"])

    def test_note_block_body_is_skipped(self):
        parsed = puml.parse("start\nnote right\nskinparam x\n:inside;\nend note\n:a;\nstop\n")
        self.assertEqual((parsed.nodes, parsed.faults), (["a"], []))

    def test_single_line_note_does_not_open_a_block(self):
        parsed = puml.parse("start\nnote right: remark\n:a;\nstop\n")
        self.assertEqual((parsed.nodes, parsed.faults), (["a"], []))


class ComponentCase(unittest.TestCase):
    def setUp(self):
        self.block = fixture("parser-component.puml")

    def test_kind_is_component(self):
        self.assertEqual(puml.kind(self.block), "component")

    def test_nodes_are_aliases_then_edge_ids(self):
        parsed = puml.parse(self.block)
        self.assertEqual(parsed.nodes, [
            "api", "events", "db", "pay", "host", "admin", "port", "user", "worker"])
        self.assertEqual((parsed.faults, parsed.node_faults, parsed.hops), ([], [], []))

    def test_bracket_endpoint_resolves_to_its_alias(self):
        parsed = puml.parse('[Order API] as api\ndatabase "Orders" as db\n[Order API] --> db\n')
        self.assertEqual(parsed.nodes, ["api", "db"])
        self.assertEqual(parsed.node_faults, [])

    def test_undeclared_bracket_endpoint_is_a_fault(self):
        parsed = puml.parse('database "Orders" as db\n[Ghost] --> db\n')
        self.assertEqual(parsed.nodes, ["db", "Ghost"])
        self.assertEqual(parsed.node_faults, [("Ghost", "not declared")])

    def test_edge_label_with_an_arrow_adds_no_node(self):
        parsed = puml.parse('component "A" as a\ndatabase "B" as b\na --> b : "write -> row"\n')
        self.assertEqual(parsed.nodes, ["a", "b"])

    def test_reversed_arrow_reads_both_sides(self):
        parsed = puml.parse('component "A" as a\ncomponent "B" as b\nb <-- a\n')
        self.assertEqual(parsed.nodes, ["a", "b"])
        self.assertEqual(parsed.node_faults, [])

    def test_every_arrow_form_reads_an_undeclared_endpoint(self):
        for arrow in ("->", "-->", "..>", ".>", "-left->", "-right->", "-up->", "-down->", "-[hidden]->"):
            with self.subTest(arrow=arrow):
                parsed = puml.parse(f'component "A" as a\na {arrow} x\n')
                self.assertEqual(parsed.nodes, ["a", "x"])
                self.assertEqual(parsed.node_faults, [("x", "not declared")])

    def test_every_reversed_arrow_form_reads_an_undeclared_endpoint(self):
        for arrow in ("<-", "<--", "<..", "<-left-", "<-[hidden]-", "<->"):
            with self.subTest(arrow=arrow):
                parsed = puml.parse(f'component "A" as a\nx {arrow} a\n')
                self.assertEqual(parsed.nodes, ["a", "x"])
                self.assertEqual(parsed.node_faults, [("x", "not declared")])

    def test_edge_label_without_a_space_before_the_colon_adds_no_node(self):
        parsed = puml.parse('component "A" as a\ndatabase "B" as b\na --> b: go -> c\n')
        self.assertEqual((parsed.nodes, parsed.node_faults), (["a", "b"], []))

    def test_undeclared_edge_id_is_a_fault(self):
        parsed = puml.parse('component "A" as a\na --> cache\n')
        self.assertEqual(parsed.nodes, ["a", "cache"])
        self.assertEqual(parsed.node_faults, [("cache", "not declared")])

    def test_hyphen_alias_is_a_bad_id(self):
        parsed = puml.parse('database "Orders" as my-db\n')
        self.assertEqual(parsed.nodes, ["my-db"])
        self.assertEqual(parsed.node_faults, [("my-db", "bad id")])

    def test_package_lines_are_not_nodes(self):
        parsed = puml.parse('package "Order service" {\ncomponent "A" as a\n}\n')
        self.assertEqual(parsed.nodes, ["a"])

    def test_style_line_is_a_fault_and_action_over_lines_is_not(self):
        parsed = puml.parse('skinparam monochrome true\ncomponent "A" as a\nnote right of a\nline\nend note\n')
        self.assertEqual((parsed.faults, parsed.nodes), (["style line 1"], ["a"]))


class StateCase(unittest.TestCase):
    def setUp(self):
        self.block = fixture("parser-state.puml")

    def test_kind_is_state(self):
        self.assertEqual(puml.kind(self.block), "state")

    def test_nodes_are_declared_and_arrow_ids_without_star(self):
        parsed = puml.parse(self.block)
        self.assertEqual(parsed.nodes, [
            "Pending", "Paid", "Cancelled", "Held", "Shipped", "Packed", "InTransit"])
        self.assertEqual((parsed.faults, parsed.node_faults, parsed.hops), ([], [], []))

    def test_transition_label_is_cut_before_the_arrow(self):
        parsed = puml.parse("A --> B : goes -> C\nstate A\n")
        self.assertEqual(parsed.nodes, ["A", "B"])

    def test_every_arrow_form_reads_a_fresh_state(self):
        for arrow in ("->", "-->", "..>", ".>", "-left->", "-right->", "-up->", "-down->", "-[hidden]->"):
            with self.subTest(arrow=arrow):
                parsed = puml.parse(f"[*] --> A\nA {arrow} N\n")
                self.assertEqual((parsed.nodes, parsed.node_faults), (["A", "N"], []))

    def test_every_reversed_arrow_form_reads_a_fresh_state(self):
        for arrow in ("<-", "<--", "<..", "<-left-", "<-[hidden]-", "<->"):
            with self.subTest(arrow=arrow):
                parsed = puml.parse(f"[*] --> A\nN {arrow} A\n")
                self.assertEqual((parsed.nodes, parsed.node_faults), (["A", "N"], []))

    def test_transition_label_without_a_space_before_the_colon_adds_no_node(self):
        parsed = puml.parse("A --> B: goes -> C\n[*] --> A\n")
        self.assertEqual((parsed.nodes, parsed.node_faults), (["A", "B"], []))

    def test_quoted_display_name_with_a_colon_is_not_a_node(self):
        parsed = puml.parse('state "Waiting: for pay" as W\n[*] --> W\n')
        self.assertEqual((parsed.nodes, parsed.node_faults), (["W"], []))

    def test_every_state_declaration_spelling_yields_only_its_id(self):
        for declaration in (
            "state A", "state A {", "state A{", "state A: desc",
            'state "Name" as A', 'state "Name" as A: desc', 'state "Name" as A {',
            'state "Name: with colon" as A', 'state "Name: with colon" as A: desc',
        ):
            with self.subTest(declaration=declaration):
                parsed = puml.parse(f"{declaration}\n[*] --> A\n")
                self.assertEqual((parsed.nodes, parsed.node_faults), (["A"], []))

    def test_state_without_an_alias_yields_no_node(self):
        parsed = puml.parse('state "x"\n[*] --> A\n')
        self.assertEqual((parsed.nodes, parsed.node_faults), (["A"], []))

    def test_state_description_after_a_colon_is_cut(self):
        parsed = puml.parse("state A: waits for pay\n[*] --> A\n")
        self.assertEqual((parsed.nodes, parsed.node_faults), (["A"], []))

    def test_bad_state_id_is_a_fault(self):
        parsed = puml.parse("[*] --> new-order\n")
        self.assertEqual(parsed.nodes, ["new-order"])
        self.assertEqual(parsed.node_faults, [("new-order", "bad id")])

    def test_note_lines_are_ignored(self):
        parsed = puml.parse("[*] --> A\nnote right of A : B --> C\nnote left of A\nD --> E\nend note\n")
        self.assertEqual(parsed.nodes, ["A"])


class KindCase(unittest.TestCase):
    def test_kind_order_is_activity_state_component(self):
        self.assertEqual(puml.kind("start\n[*] --> A\nstop\n"), "activity")
        self.assertEqual(puml.kind("state X\na --> b\n"), "state")
        self.assertEqual(puml.kind("a --> b\n"), "component")

    def test_plain_text_has_no_kind(self):
        self.assertIsNone(puml.kind("some words\nand more words\n"))

    def test_kind_none_keeps_only_style_faults(self):
        parsed = puml.parse("skinparam x\n:a;\n")
        self.assertEqual((parsed.kind, parsed.nodes, parsed.faults), (None, [], ["style line 1"]))


if __name__ == "__main__":
    unittest.main()
