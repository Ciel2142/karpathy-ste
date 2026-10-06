"""The prompts of the two review gates of the lesson rung: lesson/review-page.md, lesson/review-script.md and
lesson/review-render.md (spec sections 5.2, 5.4 and 6.4).

Each prompt is a template. The author fills it by plain text replacement of {name}, so a prompt holds the
placeholders of its gate and no other word in braces (PLACEHOLDERS; every {name} counts, name = letters and
"_"). Each prompt has the six level-2 sections of SECTIONS, in that order. Each section holds the sentences
that the spec gives it, word for word (a prompt may wrap a line; the tests compare text with runs of white
space collapsed, squash), and the Checks section holds the numbered list of its gate: three checks for the
page, two for the script, six for the render (CHECK_COUNT).

The text of a check is not pinned here. A unit test cannot tell whether a reviewer finds a planted fault, so
the gates themselves are measured only by the live run (spec section 7.5).

This module imports helpers from test_rung_drift.py; test_rung_drift.py never imports this module. LESSON_DIR
and PLACEHOLDERS serve the tests of rungs/lesson.md, which name these prompt files and their placeholders.
Each test names the mutation that turns it red."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_rung_drift import headings, read, section

EXPLAIN = Path(__file__).resolve().parent.parent
LESSON_DIR = EXPLAIN / "lesson"

PAGE, SCRIPT, RENDER = "review-page.md", "review-script.md", "review-render.md"
# The placeholders of each prompt, braces removed (spec section 6.4).
SHARED = frozenset({"subject", "root", "files", "report", "previous"})
PLACEHOLDERS = {
    PAGE: SHARED,
    SCRIPT: SHARED | {"section"},
    RENDER: SHARED | {"section", "changes"},
}
SECTIONS = ("Your task", "Inputs", "Hunt", "Checks", "Round 2", "Report")
CHECK_COUNT = {PAGE: 3, SCRIPT: 2, RENDER: 6}

PLACEHOLDER = re.compile(r"\{([A-Za-z_]+)\}")
CHECK_LINE = re.compile(r"(\d+)\. ")

READ_ONLY = "Read only these files and the files under the repository root."
HUNT_CLAIM = "Hunt. Assume one claim in this file is not supported by its cited lines, and find it."
HUNT_NONE = ("If, after reading every cite against the source, you find none, `verdict: ok` with zero findings "
             "is the right answer and is expected for a correct artifact.")
HUNT_QUOTE = "Never report a finding you cannot back with a quoted source line."
HUNT_STILL = "Hunt. Assume one still gives a false picture of what its scene narrates, and find it."
HUNT_CLIP = "`verdict: ok` with zero findings is expected for a correct clip."
HUNTS = {
    PAGE: (HUNT_CLAIM, HUNT_NONE, HUNT_QUOTE),
    SCRIPT: (HUNT_CLAIM, HUNT_NONE, HUNT_QUOTE),
    RENDER: (HUNT_STILL, HUNT_CLIP),
}
SKIP_CHECK_5 = "If `{changes}` is `nothing`, the two scripts are the same: skip check 5."
ROUND_1 = "If `{previous}` is `none`, this is round 1: skip this section."
RULE_FIRST = ("Before you hunt, rule each finding of that report `resolved` or `open`, and quote the current "
              "source line.")
VERIFY_READ = ("If the name of `{previous}` ends in `-round-2.md`, this is a verification read: rule its "
               "findings and hunt for nothing new.")
# What a round 2 reviewer does after its rulings. A gate 1 prompt always hunts; the render prompt hunts unless
# the read is a verification read, and then the verdict follows the rulings alone.
HUNT_AFTER = "Then hunt, as the Hunt section says, and number each new finding after the old ones."
HUNT_UNLESS = ("Then, unless this is a verification read, hunt as the Hunt section says, and number each new "
               "finding after the old ones.")
VERIFY_VERDICT = ("In a verification read, write `verdict: ok` when each finding is `resolved`, and "
                  "`verdict: fix` when one is `open`.")
REPORT_RULES = ("A finding without a quoted source line is not a finding.",
                "The last line of your text is `verdict: ok` or `verdict: fix`.",
                "Write `verdict: fix` when the report has at least one finding.")


def squash(text):
    """The text with each run of white space collapsed to one space."""
    return " ".join(text.split())


def prompt(name):
    return read(LESSON_DIR / name)


def held(name, title, sentences):
    """The sentences of `sentences` that section `title` of prompt `name` does not hold, white space collapsed."""
    body = squash(section(prompt(name), title))
    return [sentence for sentence in sentences if squash(sentence) not in body]


class LessonPromptCase(unittest.TestCase):
    # red: the render prompt without {previous}, a misspelt {reports}, a {section} in the page prompt, or a word
    # in braces that is no placeholder
    def test_each_prompt_has_exactly_its_placeholders(self):
        for name, expected in PLACEHOLDERS.items():
            with self.subTest(prompt=name):
                self.assertEqual(set(PLACEHOLDER.findall(prompt(name))), set(expected))

    # red: a prompt with no Round 2 section, two sections swapped, or a seventh section
    def test_each_prompt_has_the_six_sections(self):
        for name in PLACEHOLDERS:
            with self.subTest(prompt=name):
                found = [title for level, title in headings(prompt(name)) if level == 2]
                self.assertEqual(found, list(SECTIONS))

    # red: the zero-findings sentence dropped from one prompt, the hunt of gate 2 in a gate 1 prompt or the
    # other way round
    def test_each_prompt_hunts_with_an_exit(self):
        for name, sentences in HUNTS.items():
            with self.subTest(prompt=name):
                self.assertEqual(held(name, "Hunt", sentences), [])
        other = {PAGE: HUNT_STILL, SCRIPT: HUNT_STILL, RENDER: HUNT_CLAIM}
        for name, sentence in other.items():
            with self.subTest(prompt=name, other_gate=True):
                self.assertNotIn(squash(sentence), squash(prompt(name)))

    # red: the verdict rule or the quoted-line rule left out of the Report section of one prompt
    def test_each_report_needs_a_quoted_source_line(self):
        for name in PLACEHOLDERS:
            with self.subTest(prompt=name):
                self.assertEqual(held(name, "Report", REPORT_RULES), [])

    # red: a check dropped or two merged, a check numbered out of turn, or a line of another list in Checks that
    # starts with a number
    def test_each_prompt_lists_its_checks(self):
        for name, count in CHECK_COUNT.items():
            body = section(prompt(name), "Checks")
            starts = [found.group(1) for found in map(CHECK_LINE.match, body.split("\n")) if found]
            with self.subTest(prompt=name):
                self.assertEqual(starts, ["%d" % number for number in range(1, count + 1)])

    # red: the `none` sentence left out of one prompt, or the rule-before-hunt sentence; the verification read
    # left out of the render prompt, or put into a prompt of gate 1
    def test_round_2_rules_before_it_hunts(self):
        for name in PLACEHOLDERS:
            with self.subTest(prompt=name):
                self.assertEqual(held(name, "Round 2", (ROUND_1, RULE_FIRST)), [])
        self.assertEqual(held(RENDER, "Round 2", (VERIFY_READ,)), [])
        for name in (PAGE, SCRIPT):
            with self.subTest(prompt=name, verification=False):
                self.assertNotIn(squash(VERIFY_READ), squash(prompt(name)))

    # red: the render prompt tells a verification read to hunt with no condition ("Then hunt, as the Hunt
    # section says", the first version), or leaves out its verdict rule, or the condition is left out of its
    # hunt sentence; a gate 1 prompt loses its hunt after the rulings, or gets the verification condition
    def test_a_verification_read_does_not_hunt(self):
        render = squash(section(prompt(RENDER), "Round 2"))
        self.assertEqual(held(RENDER, "Round 2", (HUNT_UNLESS, VERIFY_VERDICT)), [])
        self.assertNotIn(squash(HUNT_AFTER), render)
        # each sentence that sends the reader to the Hunt section says when it does not
        sends = [sentence for sentence in re.split(r"(?<=\.) ", render) if "as the Hunt section says" in sentence]
        self.assertEqual([sentence for sentence in sends if "unless this is a verification read" not in sentence],
                         [])
        for name in (PAGE, SCRIPT):
            with self.subTest(prompt=name):
                self.assertEqual(held(name, "Round 2", (HUNT_AFTER,)), [])
                self.assertNotIn("verification", squash(section(prompt(name), "Round 2")))

    # red: the sentence left out of the Inputs section of one prompt
    def test_the_reviewer_reads_only_its_inputs(self):
        for name in PLACEHOLDERS:
            with self.subTest(prompt=name):
                self.assertEqual(held(name, "Inputs", (READ_ONLY,)), [])

    # red: the sentence left out of the Checks section of the render prompt, or put into another section
    def test_the_render_prompt_skips_check_5_without_changes(self):
        self.assertEqual(held(RENDER, "Checks", (SKIP_CHECK_5,)), [])


if __name__ == "__main__":
    unittest.main()
