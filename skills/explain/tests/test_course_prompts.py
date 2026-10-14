"""The two subagent prompts of the course rung, course/map-task.md and course/lesson-task.md (spec sections 9.2
and 10), and the rung file rungs/course.md that the orchestrator reads (spec sections 3 to 10).

Each prompt is a template. The orchestrator fills it by plain text replacement of {name}, so a prompt holds
the placeholders of PLACEHOLDERS and no other word in braces (every {name} counts, name = letters and "_").
Each prompt ends its reply with one result line (RESULT_LINES): the orchestrator keeps its context small and
reads that line, not the work. The map prompt asks for the six sections of spec step 9.2 (MAP_SECTIONS): the
fenced skeleton of the map has them as its level-2 headings, in that order. The lesson prompt holds the overrides of spec section 10 (LESSON_OVERRIDES):
the output directory, the `data-root`, the `Sources` row of the provenance, the page rung for a lesson with no
clip, and no `open`.

CourseRungCase ties rungs/course.md to the code and the files that it names. Each command of the usage of
scripts/course.py occurs in the rung as `course.py <command>`, with the two options; the check lines
`course: ok` and `course: <n> failures` and the state failure of course.STATE_CHANGED occur word for word.
The prompt files that the rung names under `<skill-dir>/course/` are the keys of PLACEHOLDERS, each a file,
and the {name} set of the rung is the union of PLACEHOLDERS (its fill table). The rung has one fenced block of
the seven verify.sh lines of a lesson (LESSON_PASS, the media line and the bpmn line): a hub prints the same
seven lines. Each text of RUNG_TEXTS occurs in the rung. The three files pass the STE lint.

This module imports helpers from test_rung_drift.py and test_lesson_prompts.py, and LESSON_PASS from
test_verify.py; no module imports this one. Each test names the mutation that turns it red."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lesson_prompts import PLACEHOLDER, fenced_blocks, squash
from test_rung_drift import headings, lint, read, section
from test_verify import LESSON_PASS

EXPLAIN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EXPLAIN / "scripts"))
import course  # noqa: E402  (scripts/ is on the path only from here)

COURSE_DIR = EXPLAIN / "course"
COURSE_MD = EXPLAIN / "rungs" / "course.md"

MAP, LESSON = "map-task.md", "lesson-task.md"
# The placeholders of each prompt, braces removed (spec sections 9.2 and 10).
PLACEHOLDERS = {
    MAP: frozenset({"skill_dir", "course_dir", "source_id", "source_path", "root", "lang"}),
    LESSON: frozenset({"skill_dir", "course_dir", "lesson_id", "lesson_json", "hops_json", "map_paths",
                       "other_lessons", "root", "lang", "review"}),
}
# The one line that each subagent ends its reply with; the orchestrator reads it, not the work.
RESULT_LINES = {
    MAP: ("map: done {source_id} <n> facts", "map: failed <reason>"),
    LESSON: ("lesson: done <rung> <n> clips", "lesson: failed <reason>"),
}
# The level-2 sections of a map, in the order of spec step 9.2.
MAP_SECTIONS = ("Entry points", "In and out", "Formats and transforms", "Routing config", "Error paths",
                "Other systems")
# The overrides of spec section 10, as lesson-task.md words them.
LESSON_OVERRIDES = (
    # the output directory (instead of convention 5)
    "Your output directory is `{course_dir}/lessons/{lesson_id}/`. It replaces the directory of convention 5",
    # the course root as data-root, absolute
    'Set `data-root` to `{root}`, and set `data-kind="topic"`.',
    # the Sources row, with Commit none
    '<div class="wide"><dt>Sources</dt>',
    "Write `none` in the `Commit` row and `no` in the `Dirty` row: the root is not one repository.",
    # the zero-clip rule
    "If no section earns a clip, build the page rung in the same directory instead of stopping.",
    # no open
    "Never run `open`.",
)
# What rungs/course.md says in its own words that no other test pins: file names, lines and rules.
RUNG_TEXTS = (
    "Rung: course (forced)",
    "lessons/<id>.stale-<n>/",
    "Never delete a lesson directory.",
    "At most 3 lesson subagents run at the same time.",
    "A failed lesson does not stop the course.",
    "map/<source-id>.md",
    "qmd collection show <name>",
    "found: discovered",
    "next: course not approved",
    "Build nothing before the user approves the plan.",
    "`--review` has no effect on a resume",
)
SEVEN_LINES = LESSON_PASS.splitlines() + ["media: ok", "bpmn: ok"]
OPTIONS = ("--limit", "--reason")


def prompt(name):
    return read(COURSE_DIR / name)


def usage_commands():
    """The command word of each line of the usage of course.py, in order."""
    return [line.split()[2] if line.startswith("usage:") else line.split()[1]
            for line in course.USAGE.strip().split("\n")]


class CoursePromptCase(unittest.TestCase):
    # red: {source_root} for {root} in the map prompt, a {review} in the map prompt, {hops_json} left out of
    # the lesson prompt, or a word in braces that is no placeholder (a JSON example such as {"id": …})
    def test_placeholders_are_exactly_the_named_set(self):
        for name, expected in PLACEHOLDERS.items():
            with self.subTest(prompt=name):
                self.assertEqual(set(PLACEHOLDER.findall(prompt(name))), set(expected))

    # red: a result line reworded (`map: ok`), its fact count left out, or the failed form left out
    def test_result_lines_present(self):
        for name, lines in RESULT_LINES.items():
            text = prompt(name)
            for line in lines:
                with self.subTest(prompt=name, line=line):
                    self.assertIn(line, text)

    # red: an override of spec section 10 left out of the lesson prompt or reworded (convention 5 back as the
    # output directory, the root of one repository as `data-root`, the zero-clip stop of lesson.md)
    def test_lesson_task_names_the_overrides(self):
        text = squash(prompt(LESSON))
        self.assertEqual([want for want in LESSON_OVERRIDES if squash(want) not in text], [])

    # red: a section of spec step 9.2 left out of the skeleton of the map, two swapped, or "Other systems"
    # renamed (discovery reads that section by its title)
    def test_map_task_names_the_six_sections(self):
        skeletons = [[line[3:] for line in lines if line.startswith("## ")]
                     for _, lines in fenced_blocks(prompt(MAP))]
        self.assertIn(list(MAP_SECTIONS), skeletons)

    # red: a sentence of 26 words, a contraction or a word of the substitution table in a prompt
    def test_prompts_lint_clean(self):
        for name in PLACEHOLDERS:
            with self.subTest(prompt=name):
                run = lint(COURSE_DIR / name)
                self.assertEqual((run.returncode, run.stdout), (0, "0 errors, 0 warnings\n"), run.stderr)


class CourseRungCase(unittest.TestCase):
    def setUp(self):
        self.text = read(COURSE_MD)

    # red: a command of course.py that the rung never runs (`course.py reopen` left out of the resume), an
    # option left out, or a check line reworded
    def test_rung_quotes_every_course_command(self):
        commands = usage_commands()
        self.assertEqual(commands, ["check", "summary", "approve", "next", "mark", "reopen", "hub"])
        for command in commands:
            with self.subTest(command=command):
                self.assertIn("course.py %s " % command, self.text)
        for want in OPTIONS + ("course: ok", "course: <n> failures", course.STATE_CHANGED):
            with self.subTest(text=want):
                self.assertIn(want, squash(self.text))

    # red: a prompt file renamed on disk or in the rung, or a third prompt named that does not exist
    def test_rung_names_prompt_files_that_exist(self):
        named = set(re.findall(r"<skill-dir>/course/([\w-]+\.md)", self.text))
        self.assertEqual(named, set(PLACEHOLDERS))
        for name in named:
            with self.subTest(prompt=name):
                self.assertTrue((COURSE_DIR / name).is_file())

    # red: a placeholder of a prompt that the fill table of the rung leaves out, or a word in braces in the
    # rung that no prompt has
    def test_rung_names_every_placeholder(self):
        self.assertEqual(set(PLACEHOLDER.findall(self.text)), set().union(*PLACEHOLDERS.values()))

    # red: the media or the bpmn line left out of the block of the hub, a line reworded, or the six lines of a
    # page given for the hub
    def test_rung_verify_block_matches_lesson_lines(self):
        found = [[line.strip() for line in lines] for _, lines in fenced_blocks(self.text)]
        self.assertIn(SEVEN_LINES, found)

    # red: a stale directory deleted instead of moved, the slot limit left out, or the approval stop left out
    def test_rung_holds_its_rules(self):
        text = squash(self.text)
        self.assertEqual([want for want in RUNG_TEXTS if squash(want) not in text], [])

    # red: the resume or the build left out of the rung, or the steps out of the order of spec section 9
    def test_rung_sections_follow_the_build(self):
        found = [title for level, title in headings(self.text) if level == 2]
        order = ["Resolve the sources", "Map the sources", "Discover", "Plan the course", "Check and stop",
                 "Revise", "Build the lessons", "Write the hub", "Handoff", "Resume"]
        self.assertEqual([title for title in found if title in order], order)
        self.assertIn("course.py next ", section(self.text, "Build the lessons"))

    # red: a sentence of 26 words, a contraction or a word of the substitution table in the rung
    def test_rung_lints_clean(self):
        run = lint(COURSE_MD)
        self.assertEqual((run.returncode, run.stdout), (0, "0 errors, 0 warnings\n"), run.stderr)


if __name__ == "__main__":
    unittest.main()
