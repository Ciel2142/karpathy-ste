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


if __name__ == "__main__":
    unittest.main()
