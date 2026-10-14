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

Fix round 1 of the review adds: the video workspace is set up once, before the build loop, with the engine of
the course language (WORKSPACE_COMMAND); each fix loop has the stop rule (STOP_RULE); the hub read names its
own checks; discovery is bounded and searches INCLUDES; the Sources row names its two git commands
(SOURCES_COMMANDS). FIX_TEXTS holds the sentences of that round.

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
# Fix round 1 of the review (task-6-review.md I1-I3, M1-M3, M6, M9): rules of the rung that keep a live run on
# a large directory bounded and give each fix loop an exit.
STOP_RULE = "Stop a fix loop after 3 rounds in which the same failure lines come back."
FIX_TEXTS = (
    STOP_RULE,
    # I3: the hub has no cite in a block section, so the per-section cite rule of page.md does not apply
    "The other checks of step 4 of \"Verify and export\" do not apply to a hub. A block section of the hub holds "
    "no `div.cites`: the cites of the hub are on the hops of the flow section.",
    # M1: a map that is not there failed; a subagent that never returns stops the run
    "A `map: done` line with no readable `map/<source-id>.md` counts as `map: failed`.",
    "A map subagent or a lesson subagent that does not return stops the run.",
    # M6: discovery stays bounded
    "Drop each handle that matches more than 5 candidates.",
    "Keep 8 discovered sources at most.",
    "`more than 8 discovered sources`",
    # M3: the neighbour lesson of a hop can be named
    "`<id>: <question> (hops: <hop>, <hop>)`",
    # M2: a FAIL line can hold a double quote
    "--reason '<line>'",
)
# M6: the text types of the sources that discovery searches.
# The final fix wave (final-review.md I2, I3): mark refuses a status change out of the order of the build; reopen
# resets a building lesson of a stopped run; a shape change of a done course goes back through approval.
FINAL_TEXTS = (
    "`mark: <id>: <from> -> <to> not allowed`",
    "It sets each `failed` lesson and each `building` lesson to `pending`",
    "`check` sets `state` to `planned`, also for a `done` course, and `approve` then approves the new shape.",
    "Else it sets `state` to `approved`.",
)
INCLUDES = ("java", "kt", "xml", "yml", "yaml", "properties", "json", "md", "proto", "sql", "xsl", "xslt", "go",
            "ts", "py", "cs", "conf")
# M9: the two commands of the Sources row, and the untracked mark per source.
SOURCES_COMMANDS = ("git -C <dir> rev-parse --short HEAD", "git -C <dir> status --porcelain",
                    "Do not use `git rev-parse --show-toplevel`: `data-root` is `{root}`.",
                    "`git -C <dir> ls-files --error-unmatch <path>`")
WORKSPACE_SH = EXPLAIN / "scripts" / "video-workspace.sh"
WORKSPACE_COMMAND = "<skill-dir>/scripts/video-workspace.sh --engine <engine>"
WORKSPACE_LINES = ("workspace: ok <ws>", "workspace: FAIL <step>")
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

    # red: the Sources row back to "the commands of the provenance recipe" (four commands, --show-toplevel among
    # them), or the untracked mark without its per-source command
    def test_lesson_task_names_the_sources_commands(self):
        text = squash(prompt(LESSON))
        self.assertEqual([want for want in SOURCES_COMMANDS if squash(want) not in text], [])

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

    # red (I1): the workspace set up by each lesson in parallel (the command left out of the build, or after the
    # loop), the engine not tied to the course language, or a workspace line that the script never prints
    def test_workspace_is_set_up_once_before_the_build_loop(self):
        build = section(self.text, "Build the lessons")
        self.assertIn(WORKSPACE_COMMAND, build)
        self.assertLess(build.index(WORKSPACE_COMMAND), build.index("Do this loop:"))
        self.assertIn(squash("`kokoro` for `en`, and `silero` for `ru`"), squash(build))
        header = read(WORKSPACE_SH)
        for line in WORKSPACE_LINES:
            with self.subTest(line=line):
                self.assertIn(line, build)
                self.assertIn(line, header)

    # red (I2, I3, M1-M3, M6): a fix loop without the stop rule, the hub step back to "steps 2 to 4" of page.md,
    # discovery unbounded, a reason in double quotes, or {other_lessons} without the hops
    def test_rung_holds_the_fixes_of_the_review(self):
        text = squash(self.text)
        self.assertEqual([want for want in FIX_TEXTS if squash(want) not in text], [])
        for title in ("Revise", "Write the hub"):
            with self.subTest(section=title):
                self.assertIn("by the stop rule of", squash(section(self.text, title)))
        self.assertNotIn("Do steps 2 to 4", text)
        self.assertNotIn('--reason "', text)

    # red (final I2, I3): a rule of the final fix wave left out or reworded in the rung, or the refusal line of
    # mark in the rung not the one that course.py prints
    def test_rung_holds_the_final_fixes(self):
        text = squash(self.text)
        self.assertEqual([want for want in FINAL_TEXTS if squash(want) not in text], [])
        source = read(EXPLAIN / "scripts" / "course.py")
        self.assertIn('"mark: %s: %s -> %s not allowed"', source)

    # red (M6): a text type of the sources left out of the discovery command
    def test_discovery_searches_the_text_types(self):
        commands = [line for _, lines in fenced_blocks(section(self.text, "Discover")) for line in lines]
        self.assertEqual(len(commands), 1)
        found = re.findall(r"--include='\*\.(\w+)'", commands[0])
        self.assertEqual(sorted(found), sorted(INCLUDES))

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
