"""Tests for the Markdown fixtures of spec section 4.5: `fixtures/clean.md` holds
ASD-STE100 Issue 9 examples, cited by rule, that must produce no findings at all;
`fixtures/warnings-only.md` holds correct STE that the heuristics flag (warnings only)."""

import contextlib
import io
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ste_lint  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CLEAN = FIXTURES / "clean.md"
WARNINGS_ONLY = FIXTURES / "warnings-only.md"
# The comment under a rule heading: the Issue 9 page label(s) of the example.
PAGE_LABEL = re.compile(r"^<!-- Issue 9, pages? 1-\d-\d+(?: and 1-\d-\d+)? -->$")
# The Issue 9 rules that clean.md must cite (task 6 brief).
REQUIRED_RULES = (
    "2.1", "3.2", "3.3", "4.2", "4.5", "5.1", "5.2", "6.3", "6.5", "6.6",
    "7.1", "7.2", "7.3", "8.5", "8.6",
)


def run_main(argv):
    """ste_lint.main(argv); returns (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = ste_lint.main(argv)
    return code, out.getvalue(), err.getvalue()


def sections(text):
    """(heading, next line, rest of the section) for each `## ` heading of `text`."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    ends = starts[1:] + [len(lines)]
    return [(lines[a], lines[a + 1], "\n".join(lines[a + 2 : b])) for a, b in zip(starts, ends)]


class CleanFixtureTest(unittest.TestCase):
    """clean.md: Issue 9 examples, cited by rule, with no findings at all."""

    def setUp(self):
        self.text = CLEAN.read_text(encoding="utf-8")

    def test_clean_fixture_has_no_findings(self):
        self.assertEqual(ste_lint.lint(ste_lint.tokenize(self.text)), [])

    def test_command_line_exits_0_with_no_findings(self):
        self.assertEqual(run_main([str(CLEAN)]), (0, "0 errors, 0 warnings\n", ""))

    def test_each_rule_heading_cites_a_page_and_holds_an_example(self):
        found = sections(self.text)
        self.assertGreaterEqual(len(found), len(REQUIRED_RULES) - 1)  # 7.2 and 7.3 share one
        for heading, comment, body in found:
            with self.subTest(heading=heading):
                self.assertRegex(heading, r"^## Rules? \d\.\d")
                self.assertRegex(comment, PAGE_LABEL)
                self.assertNotEqual(ste_lint.tokenize(body), [])

    def test_fixture_cites_every_required_rule(self):
        cited = {
            number
            for heading, _, _ in sections(self.text)
            for number in re.findall(r"\d\.\d", heading.split(" — ")[0])
        }
        self.assertEqual(sorted(set(REQUIRED_RULES) - cited), [])

    def test_fixture_has_an_ordered_procedure_of_at_least_five_steps(self):
        kinds = "".join("o" if b.kind == "ol-item" else "." for b in ste_lint.tokenize(self.text))
        self.assertGreaterEqual(max(len(run) for run in kinds.split(".")), 5)

    def test_safety_instructions_give_the_signal_word_then_the_risk(self):
        safety = [
            block for block in ste_lint.tokenize(self.text)
            if block.sentences[0].text.startswith("CAUTION: ")
        ]
        self.assertGreaterEqual(len(safety), 2)  # Rule 7.1, then Rules 7.2 and 7.3
        for block in safety:
            with self.subTest(text=block.sentences[0].text):
                self.assertGreaterEqual(len(block.sentences), 2)  # the risk is a second sentence


class WarningsOnlyFixtureTest(unittest.TestCase):
    """warnings-only.md: correct STE that the heuristics flag; warnings, never errors."""

    def setUp(self):
        self.text = WARNINGS_ONLY.read_text(encoding="utf-8")

    def row_of(self, needle):
        """1-based line and column of the first `needle` in the fixture."""
        lines = self.text.splitlines()
        row = next(n for n, line in enumerate(lines, 1) if needle in line)
        return row, lines[row - 1].index(needle) + 1

    def test_command_line_exits_0_with_warnings_and_no_errors(self):
        code, out, err = run_main([str(WARNINGS_ONLY)])
        self.assertEqual((code, err), (0, ""))
        self.assertRegex(out.splitlines()[-1], r"^0 errors, [1-9]\d* warnings$")

    def test_each_example_warns_with_its_rule(self):
        found = ste_lint.lint(ste_lint.tokenize(self.text))
        self.assertEqual(
            [(f.line, f.col, f.severity, f.rule, f.message) for f in found],
            [
                (
                    *self.row_of("The pump has fixed blades."),
                    "W", "PERFECT", 'possible perfect tense: "has fixed"',
                ),
                (
                    *self.row_of("The cause of the noise is landing gear vibration."),
                    "W", "PROGRESSIVE", 'possible progressive: "is landing"',
                ),
                (
                    *self.row_of("The valve is closed."),
                    "W", "PASSIVE", 'possible passive: "is closed"',
                ),
                (*self.row_of("WARNING: Always keep"), "W", "GERUND", 'possible gerund: "WARNING"'),
                (*self.row_of("WARNING: Do not swallow"), "W", "GERUND", 'possible gerund: "WARNING"'),
                (*self.row_of("WARNING: While you use"), "W", "GERUND", 'possible gerund: "WARNING"'),
            ],
        )


if __name__ == "__main__":
    unittest.main()
