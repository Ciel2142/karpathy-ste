"""Drift guard for the rung files: each stage line and FAIL line that rungs/video.md quotes is tied to the
code that prints it.

A quoted line is the text of an inline code span of video.md, or a line of one of its fenced blocks with
the outer white space stripped, that starts with one of the eleven stage names of a film run (FILM_ORDER)
followed directly by ":" or " (" (quoted_lines). In a table, a list or a paragraph, each one counts; a span
on a line inside a fenced block is not an inline span.

A unit test cannot render, so "printed" is three checks on PRINTED, which holds one entry for each quoted
line: the line as video.md quotes it, one sample of it as the pipeline prints it, and evidence, which is
verbatim text of the statement that prints it, as (path under skills/explain, text). line_pattern(quoted)
matches the sample; each evidence text is in a code line of its file (code_lines: no comment line, no
module docstring); each evidence text is in the sample. Two functions of render.sh print "<stage>: FAIL "
for a stage they are given: run_tool (before a tool's "FAIL <cause>", without its "FAIL ") and copy_clips.
A line that one of them prints gives the call, "run_tool <stage> " or "copy_clips <stage>", as the evidence
of its prefix, and its sample starts with "<stage>: FAIL ". REQUIRED is the lines that video.md must quote:
the eleven ok lines, the fallback line and the FAIL lines of a film that an author meets.

The helpers (read, quoted_lines, line_pattern, code_lines, headings, section, lint) and the names
FILM_ORDER and SHARED_TITLES serve the tests of the other rung files too. Each test names the mutation
that turns it red."""

import ast
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import NamedTuple

EXPLAIN = Path(__file__).resolve().parent.parent
REPO = EXPLAIN.parent.parent
VIDEO_MD = EXPLAIN / "rungs" / "video.md"
BRAINROT_MD = EXPLAIN / "rungs" / "brainrot.md"
SKILL_MD = EXPLAIN / "SKILL.md"
STE_LINT = "skills/ste/scripts/ste_lint.py"  # relative to REPO, where lint runs it

FILM_ORDER = ("script", "workspace", "scene", "narration", "timeline", "guard", "render", "container", "sync",
              "stills", "transcript")
# The titles of the sections of video.md that brainrot.md points at, and the only ones.
SHARED_TITLES = ("First-run costs", "Narration fallback", "Render ratio", "Handoff",
                 "Pinned versions and environment")

# A stage name of a film run followed directly by ":" or " ("; group 1 is the stage name.
STAGE_START = re.compile(r"(%s)(?::| \()" % "|".join(FILM_ORDER))
FENCE = re.compile(r"\s*```")
# An inline code span: a run of backticks, the content, and a run of the same length. It may cross a line
# break inside a paragraph, as Markdown reads it.
SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.S)
HEADING = re.compile(r"(#{1,6}) (.*)")
NUMBER = re.compile(r"\d+\. ")
# An evidence that is a call of render.sh: group 2 is the stage that it gives the line.
CALL = re.compile(r"(run_tool|copy_clips) ([a-z]+) ?")
RENDER_SH = "scripts/render.sh"


class Printed(NamedTuple):
    quoted: str  # the line exactly as video.md quotes it
    sample: str  # one line as the pipeline prints it
    evidence: tuple[tuple[str, str], ...]  # (path under skills/explain, verbatim text of a code line)


RENDER = RENDER_SH
CHECK_RENDER = "video/check_render.sh"
CHECK_SCENE = "video/check_scene.py"
BUILD_TIMELINE = "video/build-timeline.mjs"
CHECK_BUDGETS = "video/check_budgets.py"
GUARD_TS = "video/src/kit/guard.ts"
MARKS_TS = "video/src/kit/marks.ts"
RUN_SCRIPT = (RENDER, "run_tool script ")
RUN_SCENE = (RENDER, "run_tool scene ")
OUT = "/Users/me/out/2026-10-05-120000-video-gates"
WS = "/Users/me/karpathy/video-workspace"

# The samples come from the header of render.sh or of the tool, or from an assertion of a test, with each
# placeholder filled in. Each evidence is the longest piece of printed text of its statement with no
# interpolation and no quote mark, plus the piece that names the stage when the longest one does not.
PRINTED = (
    Printed("script: ok (<n> scenes)", "script: ok (8 scenes)", ((RENDER, "script: ok ("),)),
    Printed("workspace: ok <ws>", "workspace: ok " + WS, ((RENDER, "workspace: ok "),)),
    Printed("scene: ok (<n> files)", "scene: ok (2 files)", ((RENDER, "scene: ok ("),)),
    Printed("narration (<engine>): ok[ (fallback: <cause>)]", "narration (say): ok (fallback: uv not found)",
            ((RENDER, "): ok (fallback: "), (RENDER, "narration ("))),
    Printed("narration (say): ok (fallback: <cause>)", "narration (say): ok (fallback: uv not found)",
            ((RENDER, "): ok (fallback: "), (RENDER, "narration ("))),
    Printed("timeline (<n> scenes, <s> s): ok", "timeline (8 scenes, 49.0 s): ok", ((RENDER, "timeline ("),)),
    Printed("guard (<n> frames): ok", "guard (3 frames): ok", ((RENDER, " frames): ok"), (RENDER, "guard ("))),
    Printed("render (<s> s, <ratio> render-min/video-min)[ (limit 2.0)]: ok",
            "render (61.2 s, 1.25 render-min/video-min): ok",
            ((RENDER, " render-min/video-min)"), (RENDER, "render ("))),
    Printed("container: ok (<s> s)", "container: ok (49.0 s)", ((CHECK_RENDER, "container: ok ("),)),
    Printed("sync: ok", "sync: ok", ((CHECK_RENDER, "sync: ok"),)),
    Printed("stills (<n>): ok <review-dir>", "stills (24): ok %s/review" % OUT, ((CHECK_RENDER, "stills ("),)),
    Printed("transcript: ok", "transcript: ok", ((RENDER, "transcript: ok"),)),
    Printed("narration: FALLBACK say (<cause>)", "narration: FALLBACK say (uv not found)",
            (("scripts/narrate.sh", "narration: FALLBACK say ("),)),
    Printed("script: FAIL provenance.root must be an absolute path",
            "script: FAIL provenance.root must be an absolute path",
            ((RENDER, "script: FAIL provenance.root must be an absolute path"),)),
    Printed("script: FAIL provenance.root must be an existing directory: <path>",
            "script: FAIL provenance.root must be an existing directory: /Users/me/gone",
            ((RENDER, "script: FAIL provenance.root must be an existing directory: "),)),
    Printed("script: FAIL scene <id>: a film scene has no component or props",
            "script: FAIL scene intro: a film scene has no component or props",
            (RUN_SCRIPT, (BUILD_TIMELINE, "a film scene has no component or props"))),
    Printed("script: FAIL scene <id>: pause <v> must be an integer from 12 to 90",
            "script: FAIL scene intro: pause 5 must be an integer from 12 to 90",
            (RUN_SCRIPT, (BUILD_TIMELINE, " must be an integer from "))),
    Printed("script: FAIL source <id>: <cause>",
            "script: FAIL source loop: path src/loop.py cannot be read under the data root",
            (RUN_SCRIPT, (BUILD_TIMELINE, " cannot be read under the data root"))),
    Printed("workspace: FAIL cannot make a run directory in <ws>/runs",
            "workspace: FAIL cannot make a run directory in %s/runs" % WS,
            ((RENDER, "workspace: FAIL cannot make a run directory in "),)),
    Printed("scene: FAIL no scene directory: <path>", "scene: FAIL no scene directory: %s/scene" % OUT,
            (RUN_SCENE, (CHECK_SCENE, "FAIL no scene directory: "))),
    Printed("scene: FAIL no Film.tsx", "scene: FAIL no Film.tsx", (RUN_SCENE, (CHECK_SCENE, "no Film.tsx"))),
    Printed("scene: FAIL <name> is a directory", "scene: FAIL notes is a directory",
            (RUN_SCENE, (CHECK_SCENE, " is a directory"))),
    Printed("scene: FAIL <name> is not a .ts or .tsx file", "scene: FAIL notes.md is not a .ts or .tsx file",
            (RUN_SCENE, (CHECK_SCENE, " is not a .ts or .tsx file"))),
    Printed('scene: FAIL Film.tsx has no "export function Film("',
            'scene: FAIL Film.tsx has no "export function Film("',
            (RUN_SCENE, (CHECK_SCENE, "Film.tsx has no "), (CHECK_SCENE, "export function Film("))),
    Printed('scene: FAIL <file>:<line>: import from "<source>"',
            'scene: FAIL Film.tsx:3: import from "@remotion/paths"', (RUN_SCENE, (CHECK_SCENE, "import from "))),
    Printed('scene: FAIL <file>:<line>: "<name>" from remotion', 'scene: FAIL Film.tsx:2: "Sequence" from remotion',
            (RUN_SCENE, (CHECK_SCENE, " from remotion"))),
    Printed('scene: FAIL <file>:<line>: token "<token>"', 'scene: FAIL Film.tsx:1: token "@ts-nocheck"',
            (RUN_SCENE, (CHECK_SCENE, ": token "))),
    Printed("scene: FAIL cannot copy the scene to <path>",
            "scene: FAIL cannot copy the scene to %s/runs/run.4242.a1b2c3/src/film" % WS,
            ((RENDER, "scene: FAIL cannot copy the scene to "),)),
    Printed("scene: FAIL types: <cause>", "scene: FAIL types: script: --types needs a film script",
            ((RENDER, "scene: FAIL types: "),)),
    Printed("scene: FAIL tsc: <first error line>", "scene: FAIL tsc: scene/Film.tsx(1,1): error TS1005: x",
            ((RENDER, "scene: FAIL tsc: "),)),
    Printed("timeline: FAIL scene <id> is <s> s (max <max>, film)",
            "timeline: FAIL scene intro is 31.4 s (max 30, film)",
            ((RENDER, "timeline: "), (CHECK_BUDGETS, "FAIL scene "), (CHECK_BUDGETS, " s (max "))),
    Printed("timeline: FAIL total <s> s (max <max>, film)", "timeline: FAIL total 151.3 s (max 150, film)",
            ((RENDER, "timeline: "), (CHECK_BUDGETS, "FAIL total "), (CHECK_BUDGETS, " s (max "))),
    Printed("guard: FAIL frame <f> (scene <id>): <fault>[; <fault> ...]",
            'guard: FAIL frame 47 (scene b): OFFCANVAS "x"',
            ((RENDER, "guard: FAIL frame "), (GUARD_TS, "guard: FAIL frame "), (GUARD_TS, " (scene "),
             (GUARD_TS, "OFFCANVAS "))),
    Printed("guard: FAIL mark: scene <id>: <cause>",
            'guard: FAIL mark: scene b: word "zebra" is not in the narration',
            ((RENDER, "guard: FAIL mark: scene "), (MARKS_TS, " is not in the narration"))),
    Printed("guard: FAIL remotion render exit <n> (log <path>)",
            "guard: FAIL remotion render exit 3 (log %s/build/guard.log)" % OUT,
            ((RENDER, "guard: FAIL remotion render exit "),)),
    Printed("guard: FAIL cannot read <out>/build/timeline.json",
            "guard: FAIL cannot read %s/build/timeline.json" % OUT, ((RENDER, "guard: FAIL cannot read "),)),
    Printed("guard: FAIL cannot copy <out>/<clip>", "guard: FAIL cannot copy %s/audio/a.say.wav" % OUT,
            ((RENDER, "copy_clips guard"), (RENDER, ": FAIL cannot copy "))),
    Printed("render: FAIL remotion render exit <n> (log <path>)",
            "render: FAIL remotion render exit 3 (log %s/build/render.log)" % OUT,
            ((RENDER, "render: FAIL remotion render exit "),)),
    Printed("render: FAIL remotion render exit 1 (log <path>)",
            "render: FAIL remotion render exit 1 (log %s/build/render.log)" % OUT,
            ((RENDER, "render: FAIL remotion render exit "),)),
)

REQUIRED = (
    "script: ok (<n> scenes)",
    "workspace: ok <ws>",
    "scene: ok (<n> files)",
    "narration (<engine>): ok[ (fallback: <cause>)]",
    "timeline (<n> scenes, <s> s): ok",
    "guard (<n> frames): ok",
    "render (<s> s, <ratio> render-min/video-min)[ (limit 2.0)]: ok",
    "container: ok (<s> s)",
    "sync: ok",
    "stills (<n>): ok <review-dir>",
    "transcript: ok",
    "narration: FALLBACK say (<cause>)",
    "script: FAIL provenance.root must be an absolute path",
    "script: FAIL scene <id>: a film scene has no component or props",
    "script: FAIL scene <id>: pause <v> must be an integer from 12 to 90",
    "script: FAIL source <id>: <cause>",
    "workspace: FAIL cannot make a run directory in <ws>/runs",
    "scene: FAIL no scene directory: <path>",
    "scene: FAIL no Film.tsx",
    "scene: FAIL <name> is a directory",
    "scene: FAIL <name> is not a .ts or .tsx file",
    'scene: FAIL Film.tsx has no "export function Film("',
    'scene: FAIL <file>:<line>: import from "<source>"',
    'scene: FAIL <file>:<line>: "<name>" from remotion',
    'scene: FAIL <file>:<line>: token "<token>"',
    "scene: FAIL cannot copy the scene to <path>",
    "scene: FAIL types: <cause>",
    "scene: FAIL tsc: <first error line>",
    "timeline: FAIL scene <id> is <s> s (max <max>, film)",
    "timeline: FAIL total <s> s (max <max>, film)",
    "guard: FAIL frame <f> (scene <id>): <fault>[; <fault> ...]",
    "guard: FAIL mark: scene <id>: <cause>",
    "guard: FAIL remotion render exit <n> (log <path>)",
    "guard: FAIL cannot read <out>/build/timeline.json",
    "guard: FAIL cannot copy <out>/<clip>",
    "render: FAIL remotion render exit <n> (log <path>)",
)


def read(path):
    """The text of a file, UTF-8."""
    return Path(path).read_text(encoding="utf-8")


def stage_of(line):
    """The stage name that a quoted line starts with."""
    return STAGE_START.match(line).group(1)


def span_lines(paragraph):
    """The quoted lines of the inline code spans of `paragraph` (lines outside fenced blocks), in order. A
    line break in a span reads as one space, and one space at each end goes when both ends have one."""
    found = []
    for match in SPAN.finditer("\n".join(paragraph)):
        content = re.sub(r"\n[ \t]*", " ", match.group(2))
        if len(content) > 2 and content.startswith(" ") and content.endswith(" ") and content.strip():
            content = content[1:-1]
        if STAGE_START.match(content):
            found.append(content)
    return found


def quoted_lines(text):
    """The quoted lines of `text` (module docstring), in the order of the text, repeats included."""
    found, paragraph, fenced = [], [], False
    for line in text.split("\n"):
        if FENCE.match(line):
            found += span_lines(paragraph)
            paragraph = []
            fenced = not fenced
        elif fenced:
            if STAGE_START.match(line.strip()):
                found.append(line.strip())
        elif line.strip() == "":
            found += span_lines(paragraph)
            paragraph = []
        else:
            paragraph.append(line)
    return found + span_lines(paragraph)


def line_pattern(quoted):
    """The pattern of the lines that `quoted` describes, for fullmatch: a "<", then characters other than
    ">", then ">" is a placeholder that matches one or more characters; a "[" directly followed by a space
    or a ";" opens an optional part, which its matching "]" closes; every other character, another "["
    among them, matches itself."""
    parts, opened, i = [], [], 0
    while i < len(quoted):
        char = quoted[i]
        close = quoted.find(">", i + 1) if char == "<" else -1
        if close > i + 1:
            parts.append(".+")
            i = close + 1
            continue
        if char == "[":
            optional = quoted[i + 1:i + 2] in (" ", ";")
            opened.append(optional)
            parts.append("(?:" if optional else re.escape(char))
        elif char == "]" and opened:
            parts.append(")?" if opened.pop() else re.escape(char))
        else:
            parts.append(re.escape(char))
        i += 1
    if any(opened):
        raise ValueError("an optional part is not closed: %r" % quoted)
    return re.compile("".join(parts))


def code_lines(path):
    """The code lines of a .sh, .py, .ts, .tsx or .mjs file: no comment line, and for a .py file nothing up
    to the last line of its module docstring."""
    path = Path(path)
    text = read(path)
    lines = text.split("\n")
    if path.suffix == ".sh":
        return [line for line in lines if not line.lstrip().startswith("#")]
    if path.suffix == ".py":
        tree = ast.parse(text)
        start = tree.body[0].end_lineno if ast.get_docstring(tree, clean=False) is not None else 0
        return [line for line in lines[start:] if not line.lstrip().startswith("#")]
    if path.suffix in (".ts", ".tsx", ".mjs"):
        return [line for line in lines if not line.strip().startswith(("//", "/*", "*"))]
    raise ValueError("no code_lines rule for %s" % path)


def heading_rows(lines):
    """(line index, level, title) of each heading of `lines` outside fenced blocks, "<n>. " removed."""
    rows, fenced = [], False
    for index, line in enumerate(lines):
        if FENCE.match(line):
            fenced = not fenced
            continue
        found = None if fenced else HEADING.match(line)
        if found:
            title = found.group(2).strip()
            number = NUMBER.match(title)
            rows.append((index, len(found.group(1)), title[number.end():] if number else title))
    return rows


def headings(text):
    """(level, title) of each heading of `text`, in order."""
    return [(level, title) for _, level, title in heading_rows(text.split("\n"))]


def section(text, title):
    """The body under the one heading titled `title`: the lines after it, up to the next heading of the same
    level or a higher one. AssertionError when `title` is not exactly one heading."""
    lines = text.split("\n")
    rows = heading_rows(lines)
    found = [(index, level) for index, level, name in rows if name == title]
    if len(found) != 1:
        raise AssertionError("%d headings titled %r, not one" % (len(found), title))
    start, level = found[0]
    end = next((index for index, deeper, _ in rows if index > start and deeper <= level), len(lines))
    return "\n".join(lines[start + 1:end])


def lint(path):
    """The STE lint of `path`, run from the repository root."""
    return subprocess.run([sys.executable, STE_LINT, str(path)], cwd=REPO, capture_output=True, text=True,
                          timeout=60)


class HelperCase(unittest.TestCase):
    # red: the lines of a fenced block are skipped, or a span such as `script.json` is taken (a stage name
    # with no ":" or " (" after it)
    def test_quoted_lines_reads_spans_and_fenced_lines(self):
        text = ("| Line | Meaning |\n"
                "|---|---|\n"
                "| `script: ok (<n> scenes)` | The checks of `script.json` passed. |\n"
                "\n"
                "Run `render.sh`. Write the picture in `scene/`, and keep `scripts: x` as it is.\n"
                "\n"
                "```\n"
                "  guard (<n> frames): ok\n"
                "```\n")
        self.assertEqual(quoted_lines(text), ["script: ok (<n> scenes)", "guard (<n> frames): ok"])

    # red: every "[" opens an optional part (the literal [a-z0-9-] becomes optional), or a placeholder that
    # matches nothing (".*" for ".+")
    def test_line_pattern(self):
        narration = line_pattern("narration (<engine>): ok[ (fallback: <cause>)]")
        self.assertIsNotNone(narration.fullmatch("narration (say): ok"))
        self.assertIsNotNone(narration.fullmatch("narration (say): ok (fallback: no uv)"))
        self.assertIsNone(narration.fullmatch("narration (say): ok (fallback"))
        source = line_pattern("FAIL source #<n>: id must match [a-z0-9-]")
        self.assertIsNotNone(source.fullmatch("FAIL source #2: id must match [a-z0-9-]"))
        self.assertIsNone(line_pattern("a <x> b").fullmatch("a  b"))

    # red: the module docstring of a .py file is kept, or a comment line is kept
    def test_code_lines_drop_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            shell = Path(tmp) / "tool.sh"
            shell.write_text('#!/bin/bash\n# FAIL a\necho "FAIL a"\n', encoding="utf-8")
            self.assertEqual([line for line in code_lines(shell) if "FAIL a" in line], ['echo "FAIL a"'])
            python = Path(tmp) / "tool.py"
            python.write_text('"""A tool.\n\nFAIL a\n"""\n\n# FAIL a\nprint("FAIL a")\n', encoding="utf-8")
            self.assertEqual([line for line in code_lines(python) if "FAIL a" in line], ['print("FAIL a")'])
            script = Path(tmp) / "tool.ts"
            script.write_text("// a\n/* a\n * a\n */\nconst a = 1;\n", encoding="utf-8")
            self.assertEqual([line for line in code_lines(script) if line.strip()], ["const a = 1;"])

    # red: the body runs to the end of the file (or stops at a deeper heading), or "1. " stays in the title
    def test_section_and_headings(self):
        text = ("# Rung\n"
                "## 1. Title\n"
                "one\n"
                "### Deep\n"
                "two\n"
                "```\n"
                "## Fake\n"
                "```\n"
                "## 2. Next\n"
                "three\n")
        self.assertEqual(headings(text), [(1, "Rung"), (2, "Title"), (3, "Deep"), (2, "Next")])
        self.assertEqual(section(text, "Title"), "one\n### Deep\ntwo\n```\n## Fake\n```")
        self.assertEqual(section(text, "Deep"), "two\n```\n## Fake\n```")
        self.assertEqual(section(text, "Next"), "three\n")
        with self.assertRaises(AssertionError):
            section(text + "## Next\n", "Next")
        with self.assertRaises(AssertionError):
            section(text, "Fake")


class StageLineDriftCase(unittest.TestCase):
    def setUp(self):
        self.quoted = quoted_lines(read(VIDEO_MD))

    # red: video.md quotes a line with no entry, or an entry stays for a line that video.md no longer quotes
    def test_every_quoted_line_has_one_entry(self):
        entries = [entry.quoted for entry in PRINTED]
        self.assertEqual(sorted(set(self.quoted)), sorted(set(entries)))
        self.assertEqual(len(entries), len(set(entries)), "two entries share a quoted line")

    # red: a quoted line reworded so that it no longer describes what is printed
    def test_each_quoted_line_matches_its_sample(self):
        self.assertTrue(PRINTED, "PRINTED is empty")
        for entry in PRINTED:
            with self.subTest(quoted=entry.quoted):
                self.assertIsNotNone(line_pattern(entry.quoted).fullmatch(entry.sample), entry.sample)

    # red: render.sh or a tool rewords the statement, or the evidence is taken from a comment
    def test_each_evidence_is_code_of_its_file(self):
        self.assertTrue(PRINTED, "PRINTED is empty")
        lines = {}
        for entry in PRINTED:
            for path, text in entry.evidence:
                with self.subTest(quoted=entry.quoted, path=path, evidence=text):
                    if CALL.fullmatch(text):
                        self.assertEqual(path, RENDER_SH)
                    else:
                        self.assertGreaterEqual(len(text), 4)
                        self.assertFalse(set(text) & set("\"'$%{}"), "a quote mark or an interpolation")
                    if path not in lines:
                        lines[path] = code_lines(EXPLAIN / path)
                    self.assertTrue(any(text in line for line in lines[path]), "not in a code line")

    # red: an entry whose evidence belongs to another line
    def test_each_sample_holds_its_evidence(self):
        self.assertTrue(PRINTED, "PRINTED is empty")
        for entry in PRINTED:
            with self.subTest(quoted=entry.quoted):
                stage, gives_stage = stage_of(entry.quoted), False
                for _, text in entry.evidence:
                    call = CALL.fullmatch(text)
                    if call:
                        self.assertTrue(entry.sample.startswith("%s: FAIL " % call.group(2)), text)
                        gives_stage = gives_stage or call.group(2) == stage
                    else:
                        self.assertIn(text, entry.sample)
                        gives_stage = gives_stage or text.startswith((stage + ":", stage + " ("))
                self.assertTrue(gives_stage, "no evidence gives the stage %r" % stage)

    # red: video.md lists the explainer's nine lines, or the guard comes before the timeline
    def test_the_ok_lines_are_the_eleven_of_a_film_run(self):
        names = []
        for line in self.quoted:
            if ": ok" in line and stage_of(line) not in names:
                names.append(stage_of(line))
        self.assertEqual(tuple(names), FILM_ORDER)

    # red: a FAIL line of the scene or guard stage is not in the rung
    def test_every_film_fail_line_is_quoted(self):
        self.assertEqual([line for line in REQUIRED if line not in self.quoted], [])

    # red: a rung line breaks the STE profile (a contraction such as "don't")
    def test_video_md_lints_clean(self):
        run = lint(VIDEO_MD)
        self.assertEqual((run.returncode, run.stdout), (0, "0 errors, 0 warnings\n"), run.stderr)


if __name__ == "__main__":
    unittest.main()
