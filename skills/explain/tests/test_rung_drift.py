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
of its prefix, and its sample starts with "<stage>: FAIL ". The script stage prints "script: FAIL " and the
first "narration: FAIL " line of narrate.py --check without that prefix: such a line gives "script: FAIL " of
render.sh (CHECK_FAIL) and the cause text of narrate.py as its evidence. REQUIRED is the lines that video.md
must quote: the eleven ok lines, the fallback line and the FAIL lines of a film that an author meets.

The helpers (read, quoted_lines, line_pattern, code_lines, headings, section, blocks, lint, limits_table) and the
names FILM_ORDER and SHARED_TITLES serve the tests of the other rung files too.

FilmRungCase ties the rest of video.md to its sources: the level-2 titles (FILM_TITLES), the one table
headed "| Limit | film |" to the film row of video/formats.json (FILM_CELLS, filled by fill of
test_format_limits.py; the minText of that row is MIN_TEXT of kit/palette.ts), the two sentences that give
the text floor per format, in sections "Write the scene" and "Build and check", to the minText of the film
and clip rows, the export lines of the ts blocks of section "Write the scene" to the exports of kit/index.ts,
section "Write the script" to templates/video-script.json, and section 1 to the two languages of the rung. Each
test names the mutation that turns it red.

BrainrotRungCase ties brainrot.md to video.md by title: each block of brainrot.md that names video.md (a
pointer block) holds a title of one of the five shared sections (SHARED_TITLES) in double quotes, and no
other title of video.md and no section number; each shared title is one heading of video.md, and its
section holds no film value; brainrot.md holds its own rules, among them the components table.

PageRungCase pins the page-shape text of page.md: the file lints clean, the first-section rule of "Plan the
sections" keeps the main flow, "Fill the template" names the answer box, the Sources switch and the two guard
codes that go with them, and the self-check of "Verify and export" reads the reading view. It pins three
more files to the same page shape, one sentence each: convention 2 of SKILL.md says that the page hides the
cites, step 3 of "Plan the lesson" in lesson.md makes the main flow the first clip candidate, and check 2 of
the gate-1 prompt review-page.md covers the answer box. The text of a check stays out of test_lesson_prompts.

SkillMdCase ties SKILL.md to the rungs: step 2 of its Build procedure names the scene directory, and its
bullets under Rung files describe the film in video.md, the components in brainrot.md and the clips and
gates in lesson.md. It pins the texts that route `--as lesson` (the rung row, the bullet, the conventions
and the build step), the languages of the video and lesson rungs, and convention 7 for a non-English artifact
with the two rules that point to it, and it ties the `--as` list of README.md to the argument-hint of
SKILL.md and the README rows of the lesson rung to the files that they name.

HtmlLangCase pins the step of "Fill the template" in page.md and sheet.md that sets the `lang` of `<html>`."""

import ast
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_format_limits import fill

EXPLAIN = Path(__file__).resolve().parent.parent
REPO = EXPLAIN.parent.parent
VIDEO_MD = EXPLAIN / "rungs" / "video.md"
PAGE_MD = EXPLAIN / "rungs" / "page.md"
LESSON_MD = EXPLAIN / "rungs" / "lesson.md"
REVIEW_PAGE_MD = EXPLAIN / "lesson" / "review-page.md"
BRAINROT_MD = EXPLAIN / "rungs" / "brainrot.md"
PAGE_MD = EXPLAIN / "rungs" / "page.md"
SHEET_MD = EXPLAIN / "rungs" / "sheet.md"
SKILL_MD = EXPLAIN / "SKILL.md"
README_MD = REPO / "README.md"
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
NARRATE_PY = "video/narrate.py"
RUN_SCRIPT = (RENDER, "run_tool script ")
RUN_SCENE = (RENDER, "run_tool scene ")
# The script stage prints "script: FAIL " and the first "narration: FAIL " line of narrate.py --check with
# that prefix removed; the cause text is in narrate.py.
CHECK_FAIL = (RENDER, "script: FAIL ")
OUT = "/Users/me/out/2026-10-05-120000-video-gates"
WS = "/Users/me/karpathy/video-workspace"

# The samples come from the header of render.sh or of the tool, or from an assertion of a test, with each
# placeholder filled in. Each evidence is the longest piece of printed text of its statement with no
# interpolation and no quote mark, plus the piece that names the stage when the longest one does not, plus
# a piece of its tail when one is on exactly one code line (the ok lines, and " (log " of the two lines of a
# remotion exit, which is on two code lines, so it ties only a change to both).
PRINTED = (
    Printed("script: ok (<n> scenes)", "script: ok (8 scenes)", ((RENDER, "script: ok ("), (RENDER, " scenes)"))),
    Printed("workspace: ok <ws>", "workspace: ok " + WS, ((RENDER, "workspace: ok "),)),
    Printed("scene: ok (<n> files)", "scene: ok (2 files)", ((RENDER, "scene: ok ("), (RENDER, " files)"))),
    Printed("narration (<engine>): ok[ (fallback: <cause>)]", "narration (say): ok (fallback: uv not found)",
            ((RENDER, "): ok (fallback: "), (RENDER, "narration ("))),
    Printed("narration (say): ok (fallback: <cause>)", "narration (say): ok (fallback: uv not found)",
            ((RENDER, "): ok (fallback: "), (RENDER, "narration ("))),
    Printed("timeline (<n> scenes, <s> s): ok", "timeline (8 scenes, 49.0 s): ok",
            ((RENDER, "timeline ("), (RENDER, " scenes, "), (RENDER, " s): ok"))),
    Printed("guard (<n> frames): ok", "guard (3 frames): ok", ((RENDER, " frames): ok"), (RENDER, "guard ("))),
    Printed("render (<s> s, <ratio> render-min/video-min)[ (limit 2.0)]: ok",
            "render (61.2 s, 1.25 render-min/video-min): ok",
            ((RENDER, " render-min/video-min)"), (RENDER, "render ("))),
    Printed("container: ok (<s> s)", "container: ok (49.0 s)", ((CHECK_RENDER, "container: ok ("),)),
    Printed("sync: ok", "sync: ok", ((CHECK_RENDER, "sync: ok"),)),
    Printed("stills (<n>): ok <review-dir>", "stills (24): ok %s/review" % OUT,
            ((CHECK_RENDER, "stills ("), (CHECK_RENDER, "): ok "))),
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
    Printed('script: FAIL unspoken text: <scene>: "<t>", … (add to pronounce)',
            'script: FAIL unspoken text: tools: "KafkaTemplate", "8080"; intro: "JSON" (add to pronounce)',
            (CHECK_FAIL, (NARRATE_PY, "unspoken text: "), (NARRATE_PY, " (add to pronounce)"))),
    Printed('script: FAIL abbreviation: <scene>: "<t>", … (write the words out, as «то есть»)',
            'script: FAIL abbreviation: intro: "т.", "е." (write the words out, as «то есть»)',
            (CHECK_FAIL, (NARRATE_PY, "abbreviation: "), (NARRATE_PY, " (write the words out, as «то есть»)"))),
    Printed("script: FAIL no letter: <scene> sentence <k>, …", "script: FAIL no letter: intro sentence 2, 3",
            (CHECK_FAIL, (NARRATE_PY, "no letter: "), (NARRATE_PY, " sentence "))),
    Printed("script: FAIL too long: <scene> sentence <k> (<n> characters); … (max 900)",
            "script: FAIL too long: intro sentence 2 (912 characters); outro sentence 1 (950 characters) (max 900)",
            (CHECK_FAIL, (NARRATE_PY, "too long: "), (NARRATE_PY, " characters)"), (NARRATE_PY, " (max "))),
    Printed("script: FAIL engine <e> cannot narrate lang <l>", "script: FAIL engine kokoro cannot narrate lang ru",
            (CHECK_FAIL, (NARRATE_PY, " cannot narrate lang "))),
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
            ((RENDER, "guard: FAIL remotion render exit "), (RENDER, " (log "))),
    Printed("guard: FAIL cannot read <out>/build/timeline.json",
            "guard: FAIL cannot read %s/build/timeline.json" % OUT, ((RENDER, "guard: FAIL cannot read "),)),
    Printed("guard: FAIL cannot copy <out>/<clip>", "guard: FAIL cannot copy %s/audio/a.say.wav" % OUT,
            ((RENDER, "copy_clips guard"), (RENDER, ": FAIL cannot copy "))),
    Printed("render: FAIL remotion render exit <n> (log <path>)",
            "render: FAIL remotion render exit 3 (log %s/build/render.log)" % OUT,
            ((RENDER, "render: FAIL remotion render exit "), (RENDER, " (log "))),
    Printed("render: FAIL remotion render exit 1 (log <path>)",
            "render: FAIL remotion render exit 1 (log %s/build/render.log)" % OUT,
            ((RENDER, "render: FAIL remotion render exit "), (RENDER, " (log "))),
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
    'script: FAIL unspoken text: <scene>: "<t>", … (add to pronounce)',
    'script: FAIL abbreviation: <scene>: "<t>", … (write the words out, as «то есть»)',
    "script: FAIL no letter: <scene> sentence <k>, …",
    "script: FAIL too long: <scene> sentence <k> (<n> characters); … (max 900)",
    "script: FAIL engine <e> cannot narrate lang <l>",
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

# The level-2 titles of video.md, in order; the rung numbers them from 1.
FILM_TITLES = ("When a video", "The grammar of a film", "Write the script", "Write the scene", "Build and check",
               "Read the stills", "Handoff, output directory and pinned versions")
FORMATS_JSON = EXPLAIN / "video" / "formats.json"
PALETTE_TS = EXPLAIN / "video" / "src" / "kit" / "palette.ts"
KIT_INDEX = EXPLAIN / "video" / "src" / "kit" / "index.ts"
FILM_TEMPLATE = EXPLAIN / "templates" / "video-script.json"
FILM_TABLE_HEADER = "| Limit | film |"
# (row label, template), in the order of the rows; fill() makes the cell from the film row of formats.json,
# its own minText included.
FILM_CELLS: tuple[tuple[str, str], ...] = (
    ("canvas", "{width}×{height}"),
    ("scenes", "{minScenes}–{maxScenes}"),
    ("max scene length", "{maxSceneSeconds} s"),
    ("max total length", "{maxTotalSeconds} s"),
    ("narration words per scene", "{maxNarrationWords}"),
    ("lead / default pause frames", "{leadFrames} / {pauseFrames}"),
    ("source lines", "{sourceLines}"),
    ("smallest text", "{minText} px"),
)
MIN_TEXT_LINE = re.compile(r"export const MIN_TEXT = (\d+);")
# The language rule of section 1 of video.md (spec 5.3), word for word.
VIDEO_LANGUAGES = ('The video rung is English or Russian. A Russian film has `"lang": "ru"` in `script.json`. If '
                   "the user asks for another language, print the rung line. Say that the video rung is English or "
                   "Russian. Stop. Offer `page`.")
# The step of "Fill the template" that sets the language of a page, a sheet or a lesson page (spec 5.1).
HTML_LANG = "Set the `lang` attribute of `<html>` to the language of the artifact: `en` or `ru`."
IDENT = r"[A-Za-z_$][A-Za-z0-9_$]*"
# A list that index.ts exports from a kit file: group 1 is the text between the braces.
EXPORT_LIST = re.compile(r"\bexport\s+(?:type\s+)?\{([^{}]*)\}\s*from\b")
# A name that index.ts declares and exports itself.
EXPORT_DECLARED = re.compile(r"\bexport\s+(?:const|function|type|interface|class)\s+(%s)" % IDENT)
# One line of the kit block of video.md: group 1 is the one name that it declares.
RUNG_EXPORT = re.compile(r"export (?:const|function|type) (%s)\b" % IDENT)


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
    ">", then ">" is a placeholder that matches one or more characters; a "…" stands for the rest of a list
    and matches one or more characters too; a "[" directly followed by a space or a ";" opens an optional
    part, which its matching "]" closes; every other character, another "[" among them, matches itself."""
    parts, opened, i = [], [], 0
    while i < len(quoted):
        char = quoted[i]
        close = quoted.find(">", i + 1) if char == "<" else -1
        if close > i + 1 or char == "…":
            parts.append(".+")
            i = close + 1 if close > i + 1 else i + 1
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


def blocks(text: str) -> list[str]:
    """The text split at blank lines outside fenced blocks, each block its lines joined by "\n". A heading
    line outside a fenced block is a block of its own: it ends the block before it and starts a new one."""
    found, current, fenced = [], [], False

    def close():
        if current:
            found.append("\n".join(current))
            current.clear()

    for line in text.split("\n"):
        if FENCE.match(line):
            fenced = not fenced
            current.append(line)
        elif fenced:
            current.append(line)
        elif line.strip() == "":
            close()
        elif HEADING.fullmatch(line):
            close()
            found.append(line)
        else:
            current.append(line)
    close()
    return found


def lint(path):
    """The STE lint of `path`, run from the repository root."""
    return subprocess.run([sys.executable, STE_LINT, str(path)], cwd=REPO, capture_output=True, text=True,
                          timeout=60)


def min_text():
    """The integer of the one code line `export const MIN_TEXT = <n>;` of kit/palette.ts."""
    found = [MIN_TEXT_LINE.fullmatch(line.strip()) for line in code_lines(PALETTE_TS)]
    found = [match for match in found if match]
    if len(found) != 1:
        raise AssertionError("%d MIN_TEXT lines in %s, not one" % (len(found), PALETTE_TS))
    return int(found[0].group(1))


def limits_table(path: Path, header: str) -> dict[str, str]:
    """Row label -> cell of the one table of the file `path` headed `header` (for example `| Limit | film |`),
    in the order of its rows. Cells are the text between the pipes, stripped. AssertionError for no such table
    or more than one, a row that is not two cells, or two rows with one label."""
    lines = read(path).split("\n")
    starts = [index for index, line in enumerate(lines) if line.strip() == header]
    if len(starts) != 1:
        raise AssertionError("%d tables headed %r in %s, not one" % (len(starts), header, Path(path).name))
    rows = {}
    for line in lines[starts[0] + 2:]:  # the header and the separator row
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 2 or cells[0] in rows:
            raise AssertionError("a row that is not two cells, or a second row with its label: %r" % line)
        rows[cells[0]] = cells[1]
    return rows


def film_limits_table() -> dict[str, str]:
    """The limits table of video.md, the one headed `| Limit | film |`."""
    return limits_table(VIDEO_MD, FILM_TABLE_HEADER)


def kit_exports() -> set[str]:
    """The names that kit/index.ts exports: each name of an `export { ... } from` or `export type { ... }
    from` list (its alias when it has one), and each name that the file declares in an export of its own
    (`export type <Name>`). Comment lines are not read."""
    code = "\n".join(code_lines(KIT_INDEX))
    names = set()
    for found in EXPORT_LIST.finditer(code):
        names.update(item.split()[-1] for item in found.group(1).split(",") if item.strip())
    names.update(EXPORT_DECLARED.findall(code))
    return names


def rung_kit_names() -> set[str]:
    """The names that the export lines of the fenced ts blocks of section "Write the scene" of video.md
    declare: each line of such a block that starts with `export` declares one name (`export const <Name>`,
    `export function <Name>`, `export type <Name>`). AssertionError for an export line of another shape, or
    for a name that two lines declare."""
    names, fenced = [], None
    for line in section(read(VIDEO_MD), "Write the scene").split("\n"):
        if FENCE.match(line):
            fenced = None if fenced is not None else line.strip()
        elif fenced == "```ts" and line.startswith("export"):
            found = RUNG_EXPORT.match(line)
            if found is None:
                raise AssertionError("an export line that declares no name: %r" % line)
            names.append(found.group(1))
    if len(names) != len(set(names)):
        raise AssertionError("a name on two export lines: %r" % names)
    return set(names)


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

    # red: every "[" opens an optional part (the literal [a-z0-9-] becomes optional), a placeholder that
    # matches nothing (".*" for ".+"), or a "…" that matches only itself (a quoted list line then matches no
    # printed line)
    def test_line_pattern(self):
        narration = line_pattern("narration (<engine>): ok[ (fallback: <cause>)]")
        self.assertIsNotNone(narration.fullmatch("narration (say): ok"))
        self.assertIsNotNone(narration.fullmatch("narration (say): ok (fallback: no uv)"))
        self.assertIsNone(narration.fullmatch("narration (say): ok (fallback"))
        source = line_pattern("FAIL source #<n>: id must match [a-z0-9-]")
        self.assertIsNotNone(source.fullmatch("FAIL source #2: id must match [a-z0-9-]"))
        self.assertIsNone(line_pattern("a <x> b").fullmatch("a  b"))
        listed = line_pattern("no letter: <scene> sentence <k>, …")
        self.assertIsNotNone(listed.fullmatch("no letter: intro sentence 2, 3; outro sentence 1"))
        self.assertIsNone(listed.fullmatch("no letter: intro sentence 2, "))

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

    # red: video.md lists other ok lines than the eleven of a film run, or the guard comes before the timeline
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


class FilmRungCase(unittest.TestCase):
    # red: a section is missing, two are swapped, or one is numbered out of turn (section 5 points at
    # sections 3, 4 and 6 by number)
    def test_the_headings_of_video_md(self):
        lines = read(VIDEO_MD).split("\n")
        found = [lines[index] for index, level, _ in heading_rows(lines) if level == 2]
        self.assertEqual(found, ["## %d. %s" % (number, title) for number, title in enumerate(FILM_TITLES, 1)])
        self.assertEqual([title for level, title in headings(read(VIDEO_MD)) if level == 2], list(FILM_TITLES))

    # red: a value changed in formats.json and not in the rung, a row on one side only, or the film minText of
    # formats.json and MIN_TEXT of palette.ts differ
    def test_film_limits_table_matches_formats(self):
        row = json.loads(read(FORMATS_JSON))["film"]
        self.assertEqual(row["minText"], min_text())
        expected = [(label, fill(template, row)) for label, template in FILM_CELLS]
        self.assertEqual(list(film_limits_table().items()), expected)

    # red: the minText of the film or the clip row changes and the rung keeps the old number, or a floor
    # sentence is gone or is in the wrong section, or the guard section loses the floor per format, or the
    # rung shows a floor with a fraction as its whole number (the floors are matched as text, not as ints)
    def test_the_floor_per_format_matches_formats(self):
        rows = json.loads(read(FORMATS_JSON))
        film, clip = rows["film"]["minText"], rows["clip"]["minText"]
        draw = ("Draw each text at the floor of the format or more on the canvas: %s px for a film (`MIN_TEXT`) "
                "and %s px for a clip." % (film, clip))
        fault = "less than the floor of the format: %s px for a film and %s px for a clip." % (film, clip)
        # the rung wraps its lines, so each section is read as one line of words
        scene = " ".join(section(read(VIDEO_MD), "Write the scene").split())
        build = " ".join(section(read(VIDEO_MD), "Build and check").split())
        self.assertEqual((scene.count(draw), build.count(fault)), (1, 1))

    # red: a kit export missing from the rung, or a rung name that the kit does not export (MonoRun, makeAt)
    def test_the_kit_block_is_the_kit_index(self):
        exports = kit_exports()
        # one name of each form of index.ts: an export list, an export type list, a declaration of its own
        self.assertLessEqual({"CodeCard", "Pt", "FilmProps"}, exports)
        self.assertEqual(rung_kit_names(), exports)

    # red: the rung names the old file name (film, then -script.json), or leaves out templates/video-script.json
    # or "format": "film", or the template has another format than film
    def test_the_script_section_copies_the_film_template(self):
        body = section(read(VIDEO_MD), "Write the script")
        self.assertEqual([text for text in ("templates/video-script.json", '"format": "film"') if text not in body],
                         [])
        old_name = "film" + "-script.json"  # in two parts, so that a grep for the old name finds no line
        self.assertFalse(old_name in read(VIDEO_MD), "video.md names the old template")
        self.assertEqual(json.loads(read(FILM_TEMPLATE))["format"], "film")

    # red: the stop back to "The video rung is English only.", the Russian film without its "lang" key, or the
    # stop for a third language without its offer of `page`
    def test_video_md_states_its_two_languages(self):
        body = " ".join(section(read(VIDEO_MD), "When a video").split())
        self.assertIn(VIDEO_LANGUAGES, body)
        self.assertNotIn("English only", body)

    # red: a row of the old components table, or the cue rule, is left in
    def test_video_md_has_no_components(self):
        text = read(VIDEO_MD)
        words = ("bullets-appear", "diagram-with-highlight-walk", "code-with-line-highlights", "before-after",
                 "cue rule")
        self.assertEqual([word for word in words if word in text], [])


# The level-2 titles that brainrot.md holds besides its own pointers, and the components that it explains.
BRAINROT_TITLES = ("Write the script", "Components", "The cue rule", "Read the stills", "Output directory",
                   "Constants")
BRAINROT_COMPONENTS = ("title", "bullets-appear", "diagram-with-highlight-walk", "code-with-line-highlights",
                       "before-after")
# What no shared section of video.md may hold: a value of the film, or the word for it.
FILM_VALUES = ("film", "Film", "1280", "720", "scene/", "eleven", "speed")
SECTION_NUMBER = re.compile(r"\b[Ss]ections? \d")


class BrainrotRungCase(unittest.TestCase):
    def setUp(self):
        self.text = read(BRAINROT_MD)
        # A pointer block is a block that holds video.md and is not a heading.
        self.pointers = [block for block in blocks(self.text) if "video.md" in block and not HEADING.fullmatch(block)]

    def quoted_titles(self, block):
        """The titles of the headings of video.md that `block` holds in double quotes (a line break inside a
        title reads as one space)."""
        flat = " ".join(block.split())
        return [title for _, title in headings(read(VIDEO_MD)) if '"%s"' % title in flat]

    # red: a pointer by number or by a title of video.md that is not one of the five, a pointer block with no
    # shared title in double quotes (a bare "see video.md"), or a shared section that brainrot.md never names
    def test_brainrot_points_at_the_five_shared_titles(self):
        self.assertTrue(self.pointers, "brainrot.md names video.md in no block")
        held = set()
        for block in self.pointers:
            quoted = self.quoted_titles(block)
            held.update(quoted)
            with self.subTest(block=block[:60]):
                self.assertTrue(set(quoted) & set(SHARED_TITLES), "no shared title in double quotes")
                self.assertEqual([title for title in quoted if title not in SHARED_TITLES], [])
        self.assertEqual([title for title in SHARED_TITLES if title not in held], [])

    # red: "as in section 3 of `video.md`", or "sections 3 and 7 of `video.md`"
    def test_brainrot_names_no_section_of_video_md_by_number(self):
        for block in self.pointers:
            with self.subTest(block=block[:60]):
                self.assertIsNone(SECTION_NUMBER.search(" ".join(block.split())))

    # red: a title of video.md changed and brainrot.md left pointing at it
    def test_each_shared_title_is_one_heading_of_video_md(self):
        titles = [title for _, title in headings(read(VIDEO_MD))]
        self.assertEqual([title for title in SHARED_TITLES if titles.count(title) != 1], [])

    # red: the speed 1.0 or the canvas in "Pinned versions and environment", a film limit in another shared
    # section, or a shared section with no text
    def test_the_shared_sections_hold_no_film_value(self):
        for title in SHARED_TITLES:
            body = section(read(VIDEO_MD), title)
            with self.subTest(title=title):
                self.assertTrue(body.strip(), "the section is empty")
                self.assertEqual([value for value in FILM_VALUES if value in body], [])

    # red: the components table left with neither rung, or a rule left out of brainrot.md
    def test_brainrot_holds_its_own_rules(self):
        level_two = [title for level, title in headings(self.text) if level == 2]
        self.assertEqual([title for title in BRAINROT_TITLES if title not in level_two], [])
        components = section(self.text, "Components")
        self.assertEqual([name for name in BRAINROT_COMPONENTS if "`%s`" % name not in components], [])


class PageRungCase(unittest.TestCase):
    """The page-shape rules of rungs/page.md: the text that teaches the answer box, the Sources switch and the
    first section. Three sentences of SKILL.md, lesson.md and review-page.md follow it. The sections are read
    as one line of words, because the rung wraps its lines."""

    def words(self, title):
        return " ".join(section(read(PAGE_MD), title).split())

    # red: a rung line breaks the STE profile (a contraction such as "don't", a sentence of 26 words or more)
    def test_page_md_lints_clean(self):
        run = lint(PAGE_MD)
        self.assertEqual((run.returncode, run.stdout), (0, "0 errors, 0 warnings\n"), run.stderr)

    # red: any of the five sentences of the first-section rule is reworded or gone: it goes back to "what the
    # thing does, for whom, and from start to end", or the main flow is no longer the diagram of the first
    # section, or "The main flow is the journey of one request, a pipeline or a BPMN process." is replaced (the
    # BPMN plan quotes all five sentences as its anchor)
    def test_first_section_rule_keeps_the_main_flow(self):
        plan = self.words("Plan the sections")
        for sentence in ("The first section says why the subject exists.",
                         "One diagram in it carries the main idea.",
                         "For a directory subject, that diagram is the main flow from start to end, named by "
                         "its stages.",
                         "The main flow is the journey of one request, a pipeline or a BPMN process.",
                         "The mechanics follow in later sections."):
            with self.subTest(sentence=sentence):
                self.assertEqual(plan.count(sentence), 1)

    # red: the rung leaves out the answer box, the switch or one of the two guard codes; either Keep sentence
    # (the Sources switch in step 4, the switch as the last child of the nav in step 5) is gone or reworded (a
    # word filter would pass the other one); or the cause of NOANSWER or NOSOURCES is no longer stated
    def test_page_md_names_the_answer_box_and_switch(self):
        fill = self.words("Fill the template")
        self.assertEqual([name for name in ("div.answer", "show-sources", "NOANSWER", "NOSOURCES")
                          if name not in fill], [])
        for sentence in ("Keep the Sources switch, `label.sources` with `input#show-sources`.",
                         "Keep the Sources switch as the last child of `nav#toc`.",
                         "The guard reports `NOSOURCES` when the page has a cite block and the nav has no "
                         "switch.",
                         "It reports `NOANSWER` when the header has no answer box, or when the box has no text "
                         "outside its cites."):
            with self.subTest(sentence=sentence):
                self.assertEqual(fill.count(sentence), 1)

    # red: the tiles list "A section without its citation" again (the tiles show the reading view, where no
    # cite shows), or the check that covers the page below the answer box is gone
    def test_self_check_reads_the_reading_view(self):
        verify = self.words("Verify and export")
        self.assertNotIn("A section without its citation", verify)
        self.assertIn("Does the box alone answer", verify)

    # red: convention 2 loses the sentence (or the sentence moves to another convention), or the sentence
    # drops its second half, so the sheet and the video transcript no longer show their cites; or SKILL.md
    # breaks the STE profile
    def test_skill_md_says_the_page_hides_cites(self):
        run = lint(SKILL_MD)
        self.assertEqual((run.returncode, run.stdout), (0, "0 errors, 0 warnings\n"), run.stderr)
        conventions = section(read(SKILL_MD), "Conventions")
        two = re.search(r"^2\. .*?(?=^3\. )", conventions, re.M | re.S)
        self.assertIsNotNone(two, "no convention 2")
        self.assertEqual(" ".join(two.group(0).split()).count(
            "The page and lesson templates hide the cite blocks until the reader turns on Sources. "
            "The sheet and the video transcript show them."), 1)

    # red: step 3 of "Plan the lesson" goes back to "The journey of the first section", or the sentence is
    # gone, or it leaves the step (a sentence of the same words in another section does not count); or
    # lesson.md breaks the STE profile
    def test_lesson_md_first_candidate_is_the_main_flow(self):
        run = lint(LESSON_MD)
        self.assertEqual((run.returncode, run.stdout), (0, "0 errors, 0 warnings\n"), run.stderr)
        plan = " ".join(section(read(LESSON_MD), "Plan the lesson").split())
        self.assertEqual(plan.count("The main flow of the first section is the first candidate."), 1)
        self.assertNotIn("The journey of the first section", plan)

    # red: check 2 goes back to "No two sections contradict each other." (or the clause moves to check 1 or
    # 3), the Hunt section keeps the "<cite> at the end of a paragraph" sentence, or the block form is gone
    def test_review_page_check_2_covers_the_answer_box(self):
        text = read(REVIEW_PAGE_MD)
        checks = section(text, "Checks")
        two = re.search(r"^2\. .*?(?=^3\. )", checks, re.M | re.S)
        self.assertIsNotNone(two, "no check 2")
        self.assertEqual(" ".join(two.group(0).split()).count(
            "No two sections contradict each other, and the answer box in the header agrees with each "
            "section."), 1)
        hunt = " ".join(section(text, "Hunt").split())
        self.assertNotIn("A `<cite>` at the end of a paragraph", " ".join(text.split()))
        self.assertEqual(hunt.count("The `div.cites` after a paragraph covers each sentence of that paragraph, "
                                    "so read the whole paragraph against the cited lines."), 1)


class BpmnRungCase(unittest.TestCase):
    """The BPMN rules of the rung files (spec 2.2): one section per stage, a figure.bpmn per plane, the three
    commands before the verify, the planes as lesson candidates and check 4 of gate 1. The sections are read
    as one line of words, because the rung wraps its lines."""

    def words(self, path, title):
        return " ".join(section(read(path), title).split())

    def test_page_md_names_the_three_bpmn_commands_in_order(self):
        """Red when "Verify and export" loses `bpmn.py svg` or `bpmn.py label`, or puts them after verify.sh."""
        verify = self.words(PAGE_MD, "Verify and export")
        places = [verify.find(name) for name in ("bpmn.py svg", "bpmn.py label", "verify.sh")]
        self.assertNotIn(-1, places, verify)
        self.assertEqual(places, sorted(places))
        self.assertIn("--plane <id> --highlight <ids>", verify)

    def test_page_md_has_the_bpmn_plane_pattern(self):
        """Red when "Diagram patterns" loses the figure.bpmn block or the rule against a flow drawn by hand."""
        patterns = self.words(PAGE_MD, "Diagram patterns")
        for phrase in ('<figure class="bpmn">', "never drawn by hand", "bpmn.py svg <file> --plane <id>"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, patterns)

    def test_page_md_plans_one_section_per_stage(self):
        """Red when "Plan the sections" loses a stage section, the plane rule or the answer link, or when the
        answer-first rule "Each section expands one sentence of the answer" is gone."""
        plan = self.words(PAGE_MD, "Plan the sections")
        for phrase in ("one section per stage", "a merge may not drop a plane",
                       "names the stages in process order", "Each section expands one sentence of the answer"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, plan)

    def test_lesson_md_reads_the_planes_as_candidates(self):
        """Red when "Plan the lesson" no longer names `bpmn.py planes` for the section candidates."""
        self.assertIn("bpmn.py planes", self.words(LESSON_MD, "Plan the lesson"))

    def test_lesson_md_labels_and_checks_before_gate_1(self):
        """Red when "Check before the review" no longer runs `bpmn.py label` and then `bpmn.py check`, so gate 1
        reads raw BPMN cites and a missing plane shows only after the renders."""
        checks = self.words(LESSON_MD, "Check before the review")
        places = [checks.find(name) for name in ("bpmn.py label index.html", "bpmn.py check index.html")]
        self.assertNotIn(-1, places, checks)
        self.assertLess(places[0], places[1])
        self.assertIn("Not covered", checks)

    def test_review_page_has_the_bpmn_check(self):
        """Red when gate 1 has no check 4, a fifth check, or check 4 lost the rule that names match the
        diagram."""
        checks = section(read(REVIEW_PAGE_MD), "Checks")
        numbers = re.findall(r"^(\d+)\. ", checks, re.M)
        self.assertEqual(numbers, ["1", "2", "3", "4"])
        four = " ".join(re.search(r"^4\. .*", checks, re.M | re.S).group(0).split())
        self.assertIn("the names in the prose match the diagram", four)

    def test_page_md_and_lesson_md_lint_clean(self):
        """Red when a BPMN rule breaks the STE profile in page.md or lesson.md."""
        for path in (PAGE_MD, LESSON_MD):
            with self.subTest(file=path.name):
                run = lint(path)
                self.assertEqual((run.returncode, run.stdout), (0, "0 errors, 0 warnings\n"), run.stderr)


# The row that SKILL.md has in its rung table for the lesson rung (spec 3.1), word for word.
LESSON_ROW = ("| `lesson` (page with clips, directory output) | Forced only (`--as lesson`). A page whose sections "
              "carry short narrated clips where motion explains better than a still | A subsystem with two to "
              "four moving parts |")


class SkillMdCase(unittest.TestCase):
    def bullets(self):
        """The bullets of section "Rung files" of SKILL.md: each is its "- " line and the indented lines below
        it, joined by a space. The key is the first backtick span of the bullet."""
        found, current = {}, None
        for line in section(read(SKILL_MD), "Rung files").split("\n"):
            if line.startswith("- "):
                current = re.search(r"`([^`]+)`", line).group(1)
                found[current] = line
            elif current and line.startswith(" "):
                found[current] += " " + line.strip()
            else:
                current = None
        return found

    # red: step 2 of the Build procedure still lists the steps of a sheet or page for a video (no "scene/"), the
    # bullet of rungs/video.md names the components or the cue rule again (they moved to brainrot.md), the
    # bullet of rungs/video.md leaves out the scene, or the bullet of rungs/brainrot.md leaves out the components
    def test_skill_md_describes_the_film_rung(self):
        body = section(read(SKILL_MD), "Build procedure").split("\n")
        start = next(i for i, line in enumerate(body) if line.startswith("2. "))
        end = next(i for i, line in enumerate(body) if line.startswith("3. "))
        self.assertIn("scene/", "\n".join(body[start:end]))
        bullets = self.bullets()
        video = bullets["<skill-dir>/rungs/video.md"]
        brainrot = bullets["<skill-dir>/rungs/brainrot.md"]
        self.assertIn("scene", video)
        self.assertNotIn("components", video)
        self.assertNotIn("cue rule", video)
        self.assertIn("components", brainrot)

    # red: the lesson row marked as chosen from content (it loses "Forced only"), the rung table without
    # the row or with a second one, the conventions list without `lesson`, convention 3 without the
    # exception or without one of its three links, convention 5 without the pointer to rungs/lesson.md,
    # convention 6 without the lesson, step 2 without the build sentence, the bullet without the clips
    # or the gates, the rule bullet without "Only `--as lesson` selects it.", or the lesson rung back to
    # English only
    def test_skill_md_routes_the_lesson_rung(self):
        text = read(SKILL_MD)
        rows = [line for line in text.split("\n") if line.startswith("| `lesson`")]
        self.assertEqual(rows, [LESSON_ROW])
        flat = " ".join(text.split())  # the rules wrap over lines
        for sentence in ("The `lesson` rung builds a page with narrated clips. Only `--as lesson` selects it. "
                         "The lesson rung is English or Russian.",
                         "These seven rules apply to every artifact rung (`sheet`, `page`, `video`, "
                         "`brainrot`, `lesson`).",
                         "(sheet, page or lesson)"):
            self.assertIn(sentence, flat)
        conventions = section(text, "Conventions")
        three = " ".join(re.search(r"^3\. .*?(?=^4\. )", conventions, re.M | re.S).group(0).split())
        self.assertIn("For the `lesson` rung, the artifact is the output directory.", three)
        for link in ("`clips/<id>/video.mp4`", "`clips/<id>/poster.png`", "`clips/<id>/index.html`"):
            self.assertIn(link, three)
        five = " ".join(re.search(r"^5\. .*?(?=^6\. )", conventions, re.M | re.S).group(0).split())
        self.assertIn("For a lesson, `rungs/lesson.md` lists the contents.", five)
        body = section(text, "Build procedure").split("\n")
        start = next(i for i, line in enumerate(body) if line.startswith("2. "))
        end = next(i for i, line in enumerate(body) if line.startswith("3. "))
        self.assertIn("For a lesson, the rung file replaces steps 3 to 6.", " ".join(" ".join(body[start:end]).split()))
        lesson = self.bullets()["<skill-dir>/rungs/lesson.md"]
        self.assertIn("clips", lesson)
        self.assertIn("gates", lesson)
        self.assertTrue(LESSON_MD.is_file(), "rungs/lesson.md does not exist")

    # red: the video rule back to "The video rung is English only."
    def test_skill_md_states_the_video_languages(self):
        flat = " ".join(read(SKILL_MD).split())
        self.assertIn("The `video` rung, chosen or forced, builds a narrated mp4. The video rung is English or "
                      "Russian.", flat)

    # red: convention 7 back to its one English sentence (no structural rules, no `<code>` for an English
    # term), or convention 1 or step 1 of the Build procedure with no pointer to convention 7 (all prose under
    # the full profile again)
    def test_skill_md_points_non_english_prose_to_convention_7(self):
        text = read(SKILL_MD)
        conventions = section(text, "Conventions")
        seven = " ".join(re.search(r"^7\. .*", conventions, re.M | re.S).group(0).split())
        self.assertIn("only the structural rules of the STE profile", seven)
        self.assertIn("`<code>`", seven)
        one = " ".join(re.search(r"^1\. .*?(?=^2\. )", conventions, re.M | re.S).group(0).split())
        build = section(text, "Build procedure")
        step = " ".join(re.search(r"^1\. .*?(?=^2\. )", build, re.M | re.S).group(0).split())
        self.assertEqual([name for name, body in (("convention 1", one), ("Build step 1", step))
                          if "convention 7" not in body], [])

    # red: the README list of `--as` rungs left at five names (or in another order than the hint of SKILL.md),
    # the Requirements row of `lesson` missing or reworded, the layout line without lesson.md or lesson/, or
    # the tests block without the line of tests.test_lesson_e2e
    def test_readme_names_the_lesson_rung(self):
        readme = read(README_MD)
        hint = re.search(r'^argument-hint: "<subject> \[--as ([^\]]*)\]"$', read(SKILL_MD), re.M)
        self.assertIsNotNone(hint, "no argument-hint line")
        self.assertEqual(re.findall(r"/explain <subject> \[--as ([^\]]*)\]", readme), [hint.group(1)])
        rows = [line for line in readme.split("\n") if line.startswith("| `lesson` |")]
        self.assertEqual(rows, ["| `lesson` | the needs of `page` and of `video` together |"])
        self.assertIn("rungs/{sheet,page,video,brainrot,lesson}.md", readme)
        self.assertIn("lesson/", readme)
        self.assertIn("tests.test_lesson_e2e", readme)


class HtmlLangCase(unittest.TestCase):
    # red: the step left out of "Fill the template" of page.md or of sheet.md (a Russian page keeps the
    # lang="en" of its template), or put into another section
    def test_page_and_sheet_set_html_lang(self):
        for path in (PAGE_MD, SHEET_MD):
            with self.subTest(file=path.name):
                self.assertIn(HTML_LANG, " ".join(section(read(path), "Fill the template").split()))


if __name__ == "__main__":
    unittest.main()
