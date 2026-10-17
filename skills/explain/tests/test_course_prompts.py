"""The two subagent prompts of the course rung, course/map-task.md and course/lesson-task.md (spec sections 9.2
and 10), and the rung file rungs/course.md that the orchestrator reads (spec sections 3 to 10).

Each prompt is a template. The orchestrator fills it by plain text replacement of {name}, so a prompt holds
the placeholders of PLACEHOLDERS and no other word in braces (every {name} counts, name = letters and "_").
Each prompt ends its reply with one result line (RESULT_LINES): the orchestrator keeps its context small and
reads that line, not the work. The map prompt points at "Explore the service" and "The map" of rungs/onboard.md
(MAP_RUNG_SECTIONS): the onboarding rules and the skeleton of the ten sections of a map (MAP_SECTIONS, the titles
of onboard.TITLES) live there, so the prompt holds no skeleton. Its fenced blocks are the two onboard.py commands
of a course map (MAP_COMMANDS), and its prose holds the course overrides (MAP_TEXTS): the two files, the first
line, the fix loop of the check with its stop rule, and the fact count. The lesson prompt holds the overrides of
spec section 10 (LESSON_OVERRIDES): the output directory, the `data-root`, the `Sources` row of the provenance,
the page rung for a lesson with no clip, no `open`, and (spec section 11) the `flow` and the `nodes` of a hop and the
cut of the first diagram from the map block by the nodes of the hops of the lesson.

CourseRungCase ties rungs/course.md to the code and the files that it names. Each command of the usage of
scripts/course.py occurs in the rung as `course.py <command>`, with the two options; the check lines
`course: ok` and `course: <n> failures` and the state failure of course.STATE_CHANGED occur word for word.
The prompt files that the rung names under `<skill-dir>/course/` are the keys of PLACEHOLDERS, each a file,
and the {name} set of the rung is the union of PLACEHOLDERS (its fill table). The rung has one fenced block of
the seven verify.sh lines of a lesson (LESSON_PASS, the media line and the bpmn line): a hub prints the same
seven lines. Each text of RUNG_TEXTS occurs in the rung. "Map the sources" runs onboard.py check on each map
(MAP_CHECK_COMMAND), and the rung says which map counts (MAP_RUNG_TEXTS). "Plan the course" plans from the flows
of the maps (FLOW_TEXTS, spec section 11): the version 2 example, the `flow` and `nodes` rules, the planning rules,
the two floor prefixes of "Check and stop", and the refusal line course.OLD_VERSION in the table and in "Resume".
The three files pass the STE lint.

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
import onboard  # noqa: E402

COURSE_DIR = EXPLAIN / "course"
COURSE_MD = EXPLAIN / "rungs" / "course.md"
ONBOARD_MD = EXPLAIN / "rungs" / "onboard.md"

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
# The ten level-2 sections of a map, in order: the titles of onboard.TITLES ("The map" of rungs/onboard.md).
MAP_SECTIONS = ("Shape", "Architecture", "Entry points", "Flows", "State", "Formats and transforms",
                "Routing config", "Error paths", "Other systems", "Not covered")
# The two sections of rungs/onboard.md that the map prompt points at.
MAP_RUNG_SECTIONS = ("Explore the service", "The map")
# The two commands of a course map, the inventory first and the check last: the fenced blocks of the prompt.
MAP_COMMANDS = (
    "python3 {skill_dir}/scripts/onboard.py inventory {source_path} --root {root} "
    "--out {course_dir}/map/{source_id}.inventory.txt",
    "python3 {skill_dir}/scripts/onboard.py check {course_dir}/map/{source_id}.md --root {root} "
    "--inventory {course_dir}/map/{source_id}.inventory.txt",
)
# The overrides of the course in the map prompt: what replaces the generic names of rungs/onboard.md.
MAP_TEXTS = (
    "Write two files: `{course_dir}/map/{source_id}.md` and `{course_dir}/map/{source_id}.inventory.txt`.",
    "The first line of the map is `# Map: {source_id}`.",
    "`<service-dir>` is `{source_path}`.",
    "`<root>` is `{root}`.",
    # final review F4: the prompt names `<skill-dir>` of rungs/onboard.md too
    "`<skill-dir>` is `{skill_dir}`.",
    "Run the inventory first and the check last.",
    "Fix the map for each failure line, and run the check again, until it prints `onboard: ok`.",
    "Stop after 3 rounds in which the same failure lines come back.",
    "If failure lines remain, end with `map: done` all the same. Write each failure line before it.",
    "Write `none found` under `Architecture`, `Flows` and `State` when the source has no code to trace.",
    # the exception of "The map": a docs source with a request sequence keeps its flow, so a hop can bind to it
    "A docs source that documents a request sequence still gets a flow, as \"The map\" says.",
    "`<n>` counts the fact lines of the map, the node lines included.",
)
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
    # spec section 11: the flow and the nodes of a hop
    "Each hop has a `flow`, `<source-id>/<flow-id>`, and the `nodes` of that flow that it covers.",
    # final review F2: a hop with no flow
    "A `docs` hop or an `inferred` hop can have `null` as its `flow`. Then `nodes` is `[]`.",
    "The flow is the block under `### <flow-id>:` in `{course_dir}/map/<source-id>.md`.",
    # spec section 11: the first diagram is cut from the map block, mechanically, by the nodes of the hops
    "The first diagram of the lesson uses the Mermaid pattern of `{skill_dir}/rungs/page.md`.",
    "Cut its text from the map block of the flow by the `nodes` of the hops of the lesson.",
    # final review F3: what the map block is
    "The block is the `mermaid` fence under `### <flow-id>:`, without its fence lines and without the fact lines "
    "below it.",
    "Keep each line of the block whose node ids are all in that set.",
    "Keep each edge that leaves the set. Its far node stays as one node, and its label names the lesson that "
    "covers it, by its question.",
    "Redraw nothing.",
    "Write the text to `diagrams/<flow-id>-<source-id>.mmd` in your output directory.",
    "Each decision node of that diagram gets one paragraph that names its branches, or a section of its own.",
    "A moving part is a hop, not a node.",
    "If the hops of your lesson come from two flows, make one figure for each flow, the flow of the first hop first.",
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
# Spec section 11 in rungs/course.md: the version 2 example with a bound hop, the field rules of `flow` and `nodes`,
# the planning rules of "Plan from the flows", the lesson rule, and the rows of "Check and stop" for the hop binding,
# the two floors and the refusal of a version 1 course.
FLOW_TEXTS = (
    '"version": 2',
    '"flow": "esb/request"',
    '"nodes": ["listen", "parse"]',
    "`flow`: the flow that the hop comes from, as `<source-id>/<flow-id>`.",
    "The flow is a `### <flow-id>:` heading under `Flows` in `map/<source-id>.md`.",
    "A `code` hop has a flow. A `docs` hop has a flow or `null`. An `inferred` hop has `null`.",
    "`nodes`: the nodes of that flow that the hop covers, in the order of the flow.",
    "The list is not empty when `flow` is a string. It is `[]` when `flow` is `null`.",
    "Read the `Flows` of each map. The flows that carry the message of the course give the hops.",
    "Walk the nodes of such a flow in their order.",
    "A decision node with an edge to an error exit gives a `branch` hop.",
    "A decision node that splits the main path gives one hop for each edge, and `what` names the condition.",
    "A flow that some hop names is a followed flow.",
    "`<source-id>/<flow-id>/<node-id>`",
    "Thus a node leaves the course only by name.",
    "A sentence can name several flows or nodes.",
    "A lesson holds the hops of one flow, or of two flows that meet at one node.",
    "its `flow` and its `nodes` against `map/<source-id>.md`",
    "| `flow <source>/<flow>:` |",
    "| `node <source>/<flow>/<id>:` |",
    "cannot resume",
)
# The check that the orchestrator runs on each map, and what the rung says on which map counts.
MAP_CHECK_COMMAND = "python3 <skill-dir>/scripts/onboard.py check <course-dir>/map/<source-id>.md --root <root>"
MAP_RUNG_TEXTS = (
    "The prompt points at \"Explore the service\" and \"The map\" of `<skill-dir>/rungs/onboard.md`.",
    "Each subagent writes `map/<source-id>.md` and `map/<source-id>.inventory.txt` in `<course-dir>`.",
    # final review F1: the orchestrator prints the failure lines that the subagent lists (spec section 10)
    "Its reply ends with one line: `map: done <source-id> <n> facts` or `map: failed <reason>`.",
    "Before it, the reply holds the failure lines of its last check. Print each of them.",
    "Print each failure line that it writes.",
    "A map with failures still counts as a map: it is an input, not the artifact.",
    "Only a map that the check cannot read (`map: cannot read`) counts as `map: failed`.",
    "A map whose `Flows` is `none found` is a map.",
    "| `map/<source-id>.inventory.txt` |",
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
    # I2: discovery is a script; a name match of a system ranks first; the cites come from the maps
    "First come the candidates whose name is the name of a system of `Other systems`.",
    "Equal candidates go in the order of their names.",
    "One `grep` command searches each candidate for all the handles.",
    "Copy each cite from the map lines. Never type a cite again from memory.",
    "`cut: <dir> more than 8 discovered sources`",
    "| `discover/` |",
)
DISCOVER_COMMAND = ("python3 <skill-dir>/scripts/course_discover.py <course-dir> <parent-dir> [<parent-dir>…] "
                    "--source <source-path> [--source <source-path>…]")
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

    # red: a title of onboard.TITLES changed and not here, "Other systems" renamed (discovery reads that section
    # by its title), the pointer to rungs/onboard.md or a title of its two sections left out or renamed, a map
    # skeleton back in the prompt, or a command reworded, split over two lines, swapped or joined by a third block
    def test_map_task_points_at_the_onboard_rung(self):
        self.assertEqual(MAP_SECTIONS, onboard.TITLES)
        self.assertIn("Other systems", MAP_SECTIONS)
        text = prompt(MAP)
        self.assertIn("{skill_dir}/rungs/onboard.md", text)
        rung = read(ONBOARD_MD)
        for title in MAP_RUNG_SECTIONS:
            with self.subTest(section=title):
                self.assertIn('"%s"' % title, squash(text))
                section(rung, title)
        found = fenced_blocks(text)
        self.assertEqual([line for _, lines in found for line in lines if line.startswith("## ")], [])
        self.assertEqual([[line.strip() for line in lines] for _, lines in found],
                         [[command] for command in MAP_COMMANDS])

    # red: an override of the course left out or reworded (the map back to `map.md`, the root back to the
    # `git rev-parse` of the onboard rung, the fix loop without its stop rule or its ending, the docs source
    # without `none found` or without the flow of a request sequence, or the fact count without the node lines)
    def test_map_task_holds_the_course_overrides(self):
        text = squash(prompt(MAP))
        self.assertEqual([want for want in MAP_TEXTS if squash(want) not in text], [])

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

    # red (M6, final I2): a text type of the sources left out of the discovery script, or the rung back to a grep
    # loop of its own instead of the one command of the script
    def test_discovery_runs_the_script_over_the_text_types(self):
        commands = [line for _, lines in fenced_blocks(section(self.text, "Discover")) for line in lines]
        self.assertEqual(commands, [DISCOVER_COMMAND])
        self.assertNotIn("grep -r", self.text)
        import course_discover
        self.assertEqual(sorted(course_discover.INCLUDES), sorted(INCLUDES))
        self.assertEqual(course_discover.DROP_OVER, 5)
        self.assertEqual(course_discover.KEEP, 8)
        for line in ("candidate: <dir> <name-match|-> <n> handles: <handle> …",
                     "cut: <dir> more than 8 discovered sources", "note: map <file> has no Other systems section"):
            with self.subTest(line=line):
                self.assertIn(line, self.text)

    # red: the check of each map left out of "Map the sources", or split over two lines; the pointer to
    # onboard.md left out; a map with failures or a map with no flow counted as `map: failed`; or the inventory
    # file left out of the output directory
    def test_rung_checks_each_map(self):
        commands = [line.strip() for _, lines in fenced_blocks(section(self.text, "Map the sources"))
                    for line in lines]
        self.assertIn(MAP_CHECK_COMMAND, commands)
        text = squash(self.text)
        self.assertEqual([want for want in MAP_RUNG_TEXTS if squash(want) not in text], [])

    # red: the example back to version 1 or without the `flow` and the `nodes` of its hop, a field rule or a planning
    # rule of spec section 11 left out or reworded, a floor prefix left out of the table, or the refusal line of a
    # version 1 course not the line of course.py, left out of the table or of "Resume", or written a third time
    def test_rung_plans_from_the_flows(self):
        text = squash(self.text)
        self.assertEqual([want for want in FLOW_TEXTS if squash(want) not in text], [])
        self.assertNotIn('"version": 1', text)
        self.assertEqual(text.count(course.OLD_VERSION), 2)
        for title in ("Check and stop", "Resume"):
            with self.subTest(section=title):
                self.assertIn(course.OLD_VERSION, squash(section(self.text, title)))

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
