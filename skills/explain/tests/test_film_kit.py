"""Tests for the film kit of the explain skill's video rung (video/src/kit/): the palette, the motion
helpers and the other modules a film scene is written against. The pure modules run through Node
(which strips the types), so the values checked here are the ones a scene draws with; they are
skipped only when `node` is missing. The components are bundled with the workspace's esbuild and
rendered to static SVG markup (<ws>/app/node_modules/.bin/esbuild, ws = $EXPLAIN_VIDEO_WORKSPACE or
~/karpathy/video-workspace) from a temporary copy of the app that links node_modules to the
workspace's, so nothing is written there; those cases are skipped, naming video-workspace.sh, when
esbuild or tsc is missing. Each test names the mutation that turns it red."""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parent.parent / "video" / "src" / "kit"
VIDEO = KIT.parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "film-timeline.json"

NODE = shutil.which("node")
NO_NODE_REASON = "node is not on PATH"

WORKSPACE = Path(os.environ.get("EXPLAIN_VIDEO_WORKSPACE") or Path.home() / "karpathy" / "video-workspace")
MODULES = WORKSPACE / "app" / "node_modules"
TSC = MODULES / ".bin" / "tsc"
ESBUILD = MODULES / ".bin" / "esbuild"
NO_TOOLS_REASON = "workspace tsc or esbuild missing under %s: run scripts/video-workspace.sh" % MODULES


def needs_kit_tools(cls):
    """Class decorator: skip the class unless node and the workspace's tsc and esbuild are all there."""
    if NODE is None:
        return unittest.skip(NO_NODE_REASON)(cls)
    if not (TSC.exists() and ESBUILD.exists()):
        return unittest.skip(NO_TOOLS_REASON)(cls)
    return cls


def run_checked(argv, cwd=None, quiet=False):
    """Run `argv` (in `cwd`) and return its stdout. A non-zero exit raises an AssertionError that
    carries the command's name, its exit code and its stderr, so a failing test says why. With `quiet`
    anything the command writes to stderr fails the run too, so that a warning cannot pass unseen."""
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=120)
    name, errors = Path(argv[0]).name, done.stderr.strip()
    if done.returncode != 0:
        raise AssertionError("%s exited %d: %s" % (name, done.returncode, errors))
    if quiet and errors:
        raise AssertionError("%s wrote to stderr: %s" % (name, errors))
    return done.stdout


def run_node(script):
    """Run `script` (ES module source) in Node and return what it prints as parsed JSON."""
    return json.loads(run_checked([NODE, "--input-type=module", "-e", script]))


def kit_url(name):
    """The file URL of the kit module `name` (for example "motion.ts"), as Node imports it."""
    return (KIT / name).as_uri()


def kit_app():
    """A fresh temporary copy of video/ (the Remotion app: tsconfig.json, package.json, src/) whose
    node_modules is a link to the workspace's, so tsc and esbuild run in it and nothing is written
    under the workspace. The caller removes it with shutil.rmtree, which unlinks the link and leaves
    the workspace alone."""
    app = Path(tempfile.mkdtemp(prefix="film-kit-"))
    try:
        shutil.copytree(VIDEO, app, ignore=shutil.ignore_patterns("node_modules"), dirs_exist_ok=True)
        (app / "node_modules").symlink_to(MODULES)
    except BaseException:
        shutil.rmtree(app)
        raise
    return app


def render_kit(entry_source):
    """Write `entry_source` as src/kitcheck/entry.tsx of a fresh kit_app(), bundle it with esbuild, run
    the bundle in Node and return the JSON object it prints. An esbuild or Node run that fails, or
    writes anything to stderr (a warning of esbuild, a development warning of React), raises an
    AssertionError that carries its stderr. The copy is removed afterwards."""
    app = kit_app()
    try:
        entry = app / "src" / "kitcheck" / "entry.tsx"
        entry.parent.mkdir()
        entry.write_text(entry_source, encoding="utf-8")
        run_checked(
            ["node_modules/.bin/esbuild", "src/kitcheck/entry.tsx", "--bundle", "--format=cjs",
             "--platform=node", "--outfile=out.cjs", "--log-level=warning"],
            cwd=app, quiet=True,
        )
        return json.loads(run_checked([NODE, "out.cjs"], cwd=app, quiet=True))
    finally:
        shutil.rmtree(app)


# What an entry of render_cases continues with, after the kit imports: `show(name, element)` renders
# one case as static markup inside an <svg>, and `print()` prints every markup as one JSON line.
SHOW = """
import { renderToStaticMarkup } from "react-dom/server";
import type { ReactNode } from "react";
const out: Record<string, string> = {};
const show = (name: string, element: ReactNode) => {
  out[name] = renderToStaticMarkup(<svg>{element}</svg>);
};
const print = () => console.log(JSON.stringify(out));
"""


def render_cases(imports, cases):
    """Render each case of `cases` (a dict from a name to JSX source) inside an <svg>, in an entry that
    starts with `imports` (TSX import lines of the kit), and return a dict from the name to the list of
    the <svg>'s child elements, parsed with xml.etree.ElementTree. The markup has no xmlns, so tags
    carry no namespace."""
    shows = "".join("show(%s, %s);\n" % (json.dumps(name), jsx) for name, jsx in cases.items())
    markups = render_kit(imports + SHOW + shows + "print();\n")
    return {name: list(ET.fromstring(markups[name])) for name in cases}


def attrs(element, expected):
    """The attributes of `element` that `expected` names, as a dict to compare with `expected`: an
    attribute the element does not carry reads None, so `{"textLength": None}` asserts it is absent."""
    return {name: element.get(name) for name in expected}


def rgb(hex_colour):
    """The `rgb(r, g, b)` form that mixColor returns for the "#rrggbb" colour `hex_colour`."""
    channels = [int(hex_colour[i:i + 2], 16) for i in (1, 3, 5)]
    return "rgb(%d, %d, %d)" % tuple(channels)


PALETTE = {
    "C": {"bg": "#0f1115", "panel": "#141820", "text": "#ece9e4", "muted": "#8b919b", "line": "#4b525d",
          "blue": "#58c4dd", "green": "#83c167", "yellow": "#f4d345", "red": "#fc6255"},
    "MONO": 'ui-monospace, "SF Mono", Menlo, monospace',
    "SANS": '-apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif',
    "STAGE": {"width": 1280, "height": 720, "fps": 30},
    "MIN_TEXT": 14,
}


# The source the code-card tests read from: lines 47-54 of src/app.py (8 lines, one blank, some indented).
RAW_SOURCE = {
    "path": "src/app.py", "from": 47,
    "lines": [
        "def handle(request):", "    user = request.user", "    if not user:", "        return None",
        "    return load(user)", "", "x = 1", "y = 2",
    ],
}
A = "#58c4dd"
B = "#fc6255"


class EvaluatesJs(unittest.TestCase):
    """Base of the classes that check a kit module by evaluating JS expressions in one Node run. The
    module source that puts the names the expressions use in scope is `PRELUDE`, or what `prelude`
    returns for the extra arguments that `calls`, `values` and `errors` pass on to it."""

    PRELUDE = ""

    def prelude(self, *args):
        """The module source that runs before the expressions. A class whose names do not depend on
        the call sets PRELUDE; one that does (TestMarks: the scenes) overrides this."""
        return self.PRELUDE

    def calls(self, expressions, *args):
        """Evaluate each JS expression of `expressions` in order, after `self.prelude(*args)`. Each
        result is {"value": v} (an `undefined` is reported as null), or {"error": message, "name": name}
        when the call threw: a thrown error is read by its message and its class name."""
        return run_node(
            "%s"
            "const out = [%s].map((call) => {"
            "  try { const value = call(); return { value: value === undefined ? null : value }; }"
            "  catch (e) { return { error: e.message, name: e.name }; }"
            "});"
            "console.log(JSON.stringify(out));"
            % (self.prelude(*args), ", ".join("() => %s" % e for e in expressions))
        )

    def values(self, expressions, *args):
        """The value of each expression; fails when one of them threw."""
        got = self.calls(expressions, *args)
        for expression, result in zip(expressions, got):
            self.assertIn("value", result, "%s threw: %s" % (expression, result.get("error")))
        return [result["value"] for result in got]

    def errors(self, expressions, *args):
        """The message each expression threw; fails when one of them returned a value."""
        got = self.calls(expressions, *args)
        for expression, result in zip(expressions, got):
            self.assertIn("error", result, "%s returned %s" % (expression, result.get("value")))
        return [result["error"] for result in got]


@unittest.skipIf(NODE is None, NO_NODE_REASON)
class TestPalette(unittest.TestCase):
    def test_palette_values(self):
        """Red: any palette colour, either font stack, the stage size or rate, or MIN_TEXT changes,
        or one of the names is dropped or renamed, or an extra colour joins C (a scene would draw
        with a different colour than the spec names)."""
        got = run_node(
            'import { C, MONO, SANS, STAGE, MIN_TEXT } from "%s";'
            "console.log(JSON.stringify({ C, MONO, SANS, STAGE, MIN_TEXT }));" % kit_url("palette.ts")
        )
        self.assertEqual(got, PALETTE)


@unittest.skipIf(NODE is None, NO_NODE_REASON)
class TestMotion(unittest.TestCase):
    def curve(self, name, frames, start, length):
        """`name`(f, start, length) for each f in `frames`, in order."""
        return run_node(
            'import { %s } from "%s";'
            "console.log(JSON.stringify(%s.map((f) => %s(f, %d, %d))));"
            % (name, kit_url("motion.ts"), json.dumps(frames), name, start, length)
        )

    def test_p_is_cubic_in_out(self):
        """Red: the curve is not cubic in-out (the lower branch is 2u^2 or u, so frame 15 is not
        0.0625), the upper branch drops the `/ 2` (frame 25 gives 0.875, not 0.9375), or the ends
        are not clamped (frame 5 and frame 40 leave 0..1)."""
        got = self.curve("p", [5, 10, 15, 20, 25, 30, 40], 10, 20)
        self.assertEqual(got, [0, 0, 0.0625, 0.5, 0.9375, 1, 1])

    def test_lin_is_linear(self):
        """Red: lin is eased (it reuses the cubic, so frame 15 is 0.0625, not 0.25), or it is not
        clamped (frame 5 gives -0.25, frame 40 gives 1.5)."""
        got = self.curve("lin", [5, 10, 15, 20, 30, 40], 10, 20)
        self.assertEqual(got, [0, 0, 0.25, 0.5, 1, 1])

    def test_len_zero_or_less_is_a_step(self):
        """Red: a `len` of 0 or less is divided by (frame 10 gives NaN, which prints as null),
        the guard tests `len < 0` only (len 0 stays NaN), or the step jumps a frame early or late
        (frame 9 gives 1, or frame 10 gives 0)."""
        for name in ("p", "lin"):
            for length in (0, -5):
                got = self.curve(name, [9, 10, 11], 10, length)
                self.assertEqual(got, [0, 1, 1], "%s with len %d" % (name, length))

    def test_lerp_and_mix(self):
        """Red: lerp clamps t (1.5 gives 6, not 8), swaps its ends, or mix lerps only x (y stays
        10) or takes y from the wrong point."""
        got = run_node(
            'import { lerp, mix } from "%s";'
            "console.log(JSON.stringify({"
            "  quarter: lerp(2, 6, 0.25), over: lerp(2, 6, 1.5),"
            "  mid: mix({ x: 0, y: 10 }, { x: 10, y: 30 }, 0.5),"
            "}));" % kit_url("motion.ts")
        )
        self.assertEqual(got["quarter"], 3)
        self.assertEqual(got["over"], 8)
        self.assertEqual(got["mid"], {"x": 5, "y": 20})

    def mixed(self, calls):
        """mixColor(a, b, t) for each (a, b, t) in `calls`, in order."""
        return run_node(
            'import { mixColor } from "%s";'
            "console.log(JSON.stringify(%s.map(([a, b, t]) => mixColor(a, b, t))));"
            % (kit_url("motion.ts"), json.dumps(calls))
        )

    def test_mix_color_reads_both_forms(self):
        """Red: mixColor reads only one input form, hex digits only in lower case (the "#0000FF"
        of the second call), rounds down or up instead of to nearest (127.5 must give 128, 63.75
        must give 64), returns "#rrggbb" instead of the rgb() form, does not clamp t (-1 and 2
        overshoot the two colours), or its own result is not a valid input."""
        got = self.mixed([
            ["#000000", "#ffffff", 0.5],
            ["rgb(255, 0, 0)", "#0000FF", 0.25],
            ["#58c4dd", "#fc6255", -1],
            ["#58c4dd", "#fc6255", 2],
            # A result fed back in: halfway from rgb(128, 128, 128) to white is 191.5, which rounds up.
            ["rgb(128, 128, 128)", "#ffffff", 0.5],
        ])
        self.assertEqual(got, [
            "rgb(128, 128, 128)",
            "rgb(191, 0, 64)",
            "rgb(88, 196, 221)",
            "rgb(252, 98, 85)",
            "rgb(192, 192, 192)",
        ])

    def test_mix_color_refuses_other_forms(self):
        """Red: a colour name, a 3-digit hex or a short rgb() is accepted (read as NaN channels or
        as black), the error is not `mixColor: not a colour: "<value>"` with the value quoted, or
        only the first argument is checked (a bad second one passes)."""
        bad = ["red", "#fff", "rgb(1, 2)"]
        got = run_node(
            'import { mixColor } from "%s";'
            "const out = [];"
            "for (const bad of %s) {"
            "  for (const args of [[bad, '#000000'], ['#000000', bad]]) {"
            "    try { out.push(mixColor(args[0], args[1], 0.5)); }"
            "    catch (e) { out.push(e.message); }"
            "  }"
            "}"
            "console.log(JSON.stringify(out));" % (kit_url("motion.ts"), json.dumps(bad))
        )
        want = []
        for value in bad:
            message = 'mixColor: not a colour: "%s"' % value
            want += [message, message]
        self.assertEqual(got, want)

    def test_every_palette_colour_is_a_mix_color_input(self):
        """Red: a palette colour is written in a form mixColor refuses (a 3-digit hex, a colour
        name), or mixColor(v, v, 0) does not give v back as rgb()."""
        got = run_node(
            'import { C } from "%s";'
            'import { mixColor } from "%s";'
            "console.log(JSON.stringify(Object.values(C).map((v) => [v, mixColor(v, v, 0)])));"
            % (kit_url("palette.ts"), kit_url("motion.ts"))
        )
        self.assertEqual(len(got), 9)
        for value, result in got:
            self.assertEqual(result, rgb(value), value)


@unittest.skipIf(NODE is None, NO_NODE_REASON)
class TestMarks(EvaluatesJs):
    # A scene the fixture cannot be: its first sentence starts at 9, not at the lead (6), and its audio
    # (60 frames) runs past the end of its last word (50). Marks that are one of those numbers by
    # accident in the fixture (6 == 6, 141 == 141) differ here.
    SLACK = {
        "id": "slack", "from": 20, "durationInFrames": 80, "leadFrames": 6, "audioFrames": 60,
        "sentences": [9, 40],
        "words": [
            {"text": "One", "from": 9, "to": 30},
            {"text": "two", "from": 40, "to": 50},
        ],
    }

    def prelude(self, scenes=None):
        """The module source with `at` the makeAt of `scenes` (default: the scenes of the film-timeline
        fixture); `scenes` is the optional second argument of `calls`, `values` and `errors`."""
        if scenes is None:
            scenes = json.loads(FIXTURE.read_text())["scenes"]
        return 'import { makeAt } from "%s";const at = makeAt(%s);' % (
            kit_url("marks.ts"), json.dumps(scenes),
        )

    def test_scene_start_is_the_first_sentence(self):
        """Red: at(scene) is not the start of the scene's first sentence. On the fixture it is the
        scene's `from` (0 and 153), or it leaves the `from` out (checks gives 6), or it is not the same
        mark as { sentence: 1 }. On the slack scene, whose first sentence starts at 9 and whose lead is
        6, it is the end of the lead (26 instead of 29) or the scene's `from` (20)."""
        got = self.values(['at("type")', 'at("type", { sentence: 1 })', 'at("checks")'])
        self.assertEqual(got, [6, 6, 159])
        got = self.values(['at("slack")', 'at("slack", { sentence: 1 })'], [self.SLACK])
        self.assertEqual(got, [29, 29])

    def test_sentence_mark(self):
        """Red: sentences count from 0 (sentence 2 reads the third), a sentence mark reads the frame
        of a word instead of the sentence, or the `from` of the scene is left out (checks gives 96)."""
        got = self.values(['at("type", { sentence: 2 })', 'at("checks", { sentence: 2 })'])
        self.assertEqual(got, [96, 249])

    def test_word_mark(self):
        """Red: the word match is case-sensitive ("Router" is not found), compares the raw token
        ("handler" does not match `handler.`), reads the end of the word (`to`) instead of its start,
        or matches a token that is only the start of the word (the word "then" finds the token "The"
        first, so the mark is 159 instead of 249)."""
        got = self.values([
            'at("type", { word: "router" })',
            'at("type", { word: "Router" })',
            'at("type", { word: "handler" })',
            'at("checks", { word: "then" })',
        ])
        self.assertEqual(got, [21, 21, 66, 249])

    def test_word_mark_nth(self):
        """Red: nth is ignored (nth 2 gives the first match, 66 and 6), counts from 0 (nth 2 reads
        the third match), counts the tokens of the scene instead of the matching ones, or nth 1 is
        not the same mark as no nth."""
        got = self.values([
            'at("type", { word: "handler", nth: 2 })',
            'at("type", { word: "the", nth: 2 })',
            'at("type", { word: "handler", nth: 1 })',
            'at("type", { word: "handler" })',
        ])
        self.assertEqual(got, [111, 96, 66, 66])

    def test_word_mark_ignores_punctuation_and_backticks(self):
        """Red: only one side of the match is cleaned (the backticks of `verify.sh` stay on the
        token, or the dot of "Verify.sh" stays on the word), or the cleaning removes only the
        trailing punctuation. The punctuation inside a token is removed too: a cleaning that keeps
        the dot or the hyphen does not find "verifysh" or "selfcontained"."""
        got = self.values([
            'at("checks", { word: "Verify.sh" })',
            'at("checks", { word: "self-contained" })',
            'at("checks", { word: "verifysh" })',
            'at("checks", { word: "selfcontained" })',
        ])
        self.assertEqual(got, [174, 219, 174, 219])

    def test_word_mark_matches_the_whole_token(self):
        """Red: a word that is only the start of a token matches it (a prefix or substring test: "self"
        finds `self-contained.`, so the mark is 219 instead of an error)."""
        got = self.errors(['at("checks", { word: "self" })'])
        self.assertEqual(got, ['MARK scene checks: word "self" is not in the narration'])

    def test_word_mark_reads_unicode_letters_and_digits(self):
        """Red: the cleaning keeps only ASCII (the token "日本語。" becomes empty and its word is
        refused as having no letter or digit; "caf" matches the token "Café,"), or keeps only
        letters (the word "2024" is refused as having no letter or digit)."""
        scene = {
            "id": "u", "from": 10, "durationInFrames": 60, "leadFrames": 6, "audioFrames": 40,
            "sentences": [6],
            "words": [
                {"text": "Café,", "from": 6, "to": 16},
                {"text": "日本語。", "from": 16, "to": 26},
                {"text": "2024.", "from": 26, "to": 36},
            ],
        }
        got = self.values(['at("u", { word: "日本語" })', 'at("u", { word: "2024" })'], [scene])
        self.assertEqual(got, [26, 36])
        got = self.errors(['at("u", { word: "caf" })'], [scene])
        self.assertEqual(got, ['MARK scene u: word "caf" is not in the narration'])

    def test_said_and_end(self):
        """Red: said is not the end of the audio, which is `from + leadFrames + audioFrames`. It omits
        the lead (from + audioFrames), or omits the `from` of the scene (checks gives 141), or is the
        end of the lead (6 and 159 are wrong), or, on the slack scene whose audio runs past its last
        word, is the end of that word (70 instead of 86). end is not `from + durationInFrames`: it is
        said (the pause is lost), or omits the `from` (checks gives 171)."""
        got = self.values(['at.said("type")', 'at.end("type")', 'at.said("checks")', 'at.end("checks")'])
        self.assertEqual(got, [141, 153, 294, 324])
        got = self.values(['at.said("slack")', 'at.end("slack")'], [self.SLACK])
        self.assertEqual(got, [86, 100])

    def test_mark_errors(self):
        """Red: a message differs from the one named here by a word or a number (the <n> is the value
        as written, so -1 and 1.5 are shown as they are), a check is missing (at.said or at.end of a
        missing scene fails with a TypeError, a sentence of 0, 1.5 or -1 or an nth of 0 reads
        undefined, "--" falls through to "is not in the narration"), or the scene is looked up in a
        plain object (the id "constructor" finds an inherited member)."""
        cases = [
            ('at("nope")', "MARK scene nope: no such scene"),
            ('at.said("nope")', "MARK scene nope: no such scene"),
            ('at.end("nope")', "MARK scene nope: no such scene"),
            ('at("constructor")', "MARK scene constructor: no such scene"),
            ('at("type", { sentence: 0 })', "MARK scene type: sentence 0 is not a positive integer"),
            ('at("type", { sentence: 1.5 })', "MARK scene type: sentence 1.5 is not a positive integer"),
            ('at("type", { sentence: -1 })', "MARK scene type: sentence -1 is not a positive integer"),
            ('at("type", { sentence: 3 })', "MARK scene type: sentence 3 is past the last one (2)"),
            ('at("type", { word: "handler", nth: 0 })', "MARK scene type: nth 0 is not a positive integer"),
            ('at("type", { word: "handler", nth: 3 })', 'MARK scene type: nth 3 is past the last "handler" (2)'),
            ('at("type", { word: "--" })', 'MARK scene type: word "--" has no letter or digit'),
            ('at("type", { word: "zebra" })', 'MARK scene type: word "zebra" is not in the narration'),
        ]
        got = self.errors([expression for expression, _ in cases])
        self.assertEqual(got, [message for _, message in cases])


NOT_FROM_DISK = 'CodeCard: the source was not read from disk; declare it in "sources" of script.json'

# What every TestSource and TestMono script starts from: `raw`, a source made of RAW_SOURCE (a fresh
# record of made sources in each Node process), and the cards `card` and `big`.
SCRIPT_START = (
    "const raw = %s;"
    "const src = sourceFromDisk(raw);"
    "const card = { x: 100, y: 50, width: 600, size: 20 };"
    "const big = { x: 10, y: 0, width: 400, size: 30 };"
    "const A = %s, B = %s;"
) % (json.dumps(RAW_SOURCE), json.dumps(A), json.dumps(B))


@unittest.skipIf(NODE is None, NO_NODE_REASON)
class TestSource(EvaluatesJs):
    PRELUDE = 'import { sourceFromDisk, requireFromDisk } from "%s";' % kit_url("source.ts") + SCRIPT_START

    def test_a_source_from_disk_is_accepted(self):
        """Red: the maker does not record the object it returns (requireFromDisk refuses it), or
        requireFromDisk returns a value instead of nothing."""
        got = self.values(["requireFromDisk(src)", "requireFromDisk(sourceFromDisk(raw))"])
        self.assertEqual(got, [None, None])

    def test_a_copy_or_a_rebuilt_source_is_refused(self):
        """Red: requireFromDisk accepts an object the maker did not return: it checks nothing, or only
        the shape of the object (all four cases pass), or only that the object is frozen (the frozen
        rebuilt one passes), or it records the path of a made source, not the object (all four pass);
        or it throws something other than an Error, or a message that differs from the one that names
        "sources" of script.json."""
        got = self.calls([
            "requireFromDisk({ ...src })",
            "requireFromDisk(JSON.parse(JSON.stringify(src)))",
            "requireFromDisk({ path: raw.path, from: raw.from, lines: [...raw.lines] })",
            "requireFromDisk(Object.freeze("
            "{ path: raw.path, from: raw.from, lines: Object.freeze([...raw.lines]) }))",
        ])
        self.assertEqual(got, [{"error": NOT_FROM_DISK, "name": "Error"}] * 4)

    def test_a_source_cannot_change(self):
        """Red: the source object is not frozen (a write to `path` or `from` passes, or `isFrozen` is
        false), or `lines` is not frozen (a write to lines[0] or a push passes), or `lines` is the
        array that was given, not a copy (raw.lines[0] = ... changes the source's line, or throws
        because the given array was frozen)."""
        got = self.calls([
            "Object.isFrozen(src)",
            "Object.isFrozen(src.lines)",
            '(src.lines[0] = "changed")',
            '(src.lines.push("changed"))',
            '(src.path = "other.py")',
            "(src.from = 1)",
            '(raw.lines[0] = "changed", raw.lines.push("extra"), [...src.lines])',
        ])
        self.assertEqual(got[:2], [{"value": True}, {"value": True}])
        for result in got[2:6]:
            self.assertEqual(result.get("name"), "TypeError", result)
        self.assertEqual(got[6], {"value": RAW_SOURCE["lines"]})


# Every TestMono script imports mono.ts, so a value import of Source in it (`import { Source }` or
# `import { type Source }`, which Node cannot resolve without an extension) turns all of them red.
@unittest.skipIf(NODE is None, NO_NODE_REASON)
class TestMono(EvaluatesJs):
    PRELUDE = (
        "import { ADVANCE, monoWidth, colX, lineY, fitColumns, cardHeight, lineSpans, requireLine }"
        ' from "%s";' % kit_url("mono.ts")
        + 'import { sourceFromDisk } from "%s";' % kit_url("source.ts")
        + SCRIPT_START
    )

    def test_mono_width_counts_code_points(self):
        """Red: ADVANCE is not 0.6, the width counts UTF-16 units (the smiley is two, so "a" and the
        smiley give 36, not 24), or the size is not read from the argument (a fixed 20 gives 36 for
        "abc" at size 10)."""
        got = self.values([
            'monoWidth("abc", 20)', 'monoWidth("a\\u{1F600}", 20)', 'monoWidth("abc", 10)', "ADVANCE",
        ])
        self.assertEqual(got, [36, 24, 18, 0.6])

    def test_col_x(self):
        """Red: the padding, the gutter or the gap changes (column 0 is not 188), the advance is not
        0.6 of the size (column 10 is not 308), the card's x is left out, or the size is not read
        from the card (a fixed 20 gives the big card, x 10 and size 30, not 170 at column 2)."""
        got = self.values(["colX(card, 0)", "colX(card, 10)", "colX(big, 2)"])
        self.assertEqual(got, [188, 308, 170])

    def test_line_y(self):
        """Red: the baseline is the top of the row (without the `size` term: 66 instead of 86), the row
        is not 1.6 of the size (line 54 is not 310), the source's first line is not subtracted or is
        a fixed 47 (a source from line 10 gives 118 for its second line), the card's y is left out,
        the size is not read from the card (a fixed 20 does not give 142 for the big card), or the
        line is checked against the source (line 40 is above it and must still give -138)."""
        got = self.values([
            "lineY(card, src, 47)", "lineY(card, src, 48)", "lineY(card, src, 54)",
            "lineY(big, src, 49)", "lineY(card, src, 40)",
            'lineY(card, sourceFromDisk({ path: "lib/x.ts", from: 10, lines: ["a", "b"] }), 11)',
        ])
        self.assertEqual(got, [86, 118, 310, 142, -138, 118])

    def test_fit_columns(self):
        """Red: the right edge keeps no padding (the card gives 42), the count rounds or takes the
        ceiling instead of the floor (width 590 is 40.5 columns and must give 40; the ceiling gives 42
        for the card), a narrow card goes below 0 (width 80 gives -2), or a whole column is lost to
        rounding error: size 18 and width 140 hold exactly 4 columns, and 4 is not what the plain
        division gives."""
        got = self.values([
            "fitColumns(card)",
            "fitColumns({ ...card, width: 80 })",
            "fitColumns({ ...card, width: 590 })",
            "fitColumns({ ...card, width: 140, size: 18 })",
            "fitColumns(big)",
        ])
        self.assertEqual(got, [41, 0, 40, 4, 14])

    def test_card_height(self):
        """Red: the padding is counted on one side only (the card gives 272), the row is not 1.6 of
        the size, the size is not read from the card (a fixed 20 does not give 176 for 3 lines of the
        big card), or a card of no lines still counts a row (64 instead of 32)."""
        got = self.values(["cardHeight(card, 8)", "cardHeight(big, 3)", "cardHeight(card, 0)"])
        self.assertEqual(got, [288, 176, 32])

    def spans(self, text, tints, columns=41):
        """The JS expression of lineSpans(`text`, `tints`, `columns`); `text` and `tints` are JS source."""
        return "lineSpans(%s, %s, %d)" % (text, tints, columns)

    def tint(self, frm, to, color="A", line=47):
        """The JS source of a tint of `line` from `frm` to `to`; `color` names the JS constant A or B."""
        return "{ line: %d, from: %d, to: %d, color: %s }" % (line, frm, to, color)

    def test_line_spans(self):
        """Red: a tint that starts before 0 is dropped (-2 to 1 leaves out the first letter), a
        reversed range is read with its ends swapped (5 to 2 colours the letters from 2 to 5), a
        tint's `to` is inclusive, an overlap is won by the earlier tint (the reversed order case must
        show the later one, A, winning over the first four letters), neighbours of one colour are
        left as several spans, an uncoloured run is absorbed by the coloured span before it, only the
        tints on the line of the first tint are read (the join case has its second tint on line 99),
        or an uncoloured span carries a colour (even an empty one)."""
        text, tint = '"abcdef"', self.tint
        got = self.values([
            self.spans(text, "[]"),
            self.spans(text, "[%s]" % tint(1, 3)),
            self.spans(text, "[%s, %s]" % (tint(0, 4), tint(2, 6, "B"))),
            self.spans(text, "[%s, %s]" % (tint(2, 6, "B"), tint(0, 4))),
            self.spans(text, "[%s]" % tint(3, 3)),
            self.spans(text, "[%s]" % tint(5, 2)),
            self.spans(text, "[%s]" % tint(-2, 1)),
            self.spans(text, "[%s, %s]" % (tint(0, 2), tint(2, 4, line=99))),
            self.spans(text, "[%s, %s]" % (tint(0, 1), tint(3, 4))),
        ])
        plain = lambda t: {"text": t}
        coloured = lambda t, c: {"text": t, "color": c}
        self.assertEqual(got, [
            [plain("abcdef")],
            [plain("a"), coloured("bc", A), plain("def")],
            [coloured("ab", A), coloured("cdef", B)],
            [coloured("abcd", A), coloured("ef", B)],
            [plain("abcdef")],
            [plain("abcdef")],
            [coloured("a", A), plain("bcdef")],
            [coloured("abcd", A), plain("ef")],
            [coloured("a", A), plain("bc"), coloured("d", A), plain("ef")],
        ])

    def test_line_spans_cut(self):
        """Red: the text is not cut to the columns (4 columns give "abcdef"), a columns of 0 or less is
        not an empty cut (-1 drops only the last letter, as slice does), or an empty text gives a
        span of no text. Whatever the cut, the spans of a case join into exactly the cut text."""
        text = '"abcdef"'
        to_99 = "[%s]" % self.tint(2, 99)
        past = "[%s]" % self.tint(5, 9)
        cases = [
            (self.spans(text, "[]", 4), "abcd"),
            (self.spans(text, to_99, 4), "abcd"),
            (self.spans(text, past, 4), "abcd"),
            (self.spans('""', "[]"), ""),
            (self.spans('""', to_99), ""),
            (self.spans(text, to_99, 0), ""),
            (self.spans(text, to_99, -1), ""),
        ]
        got = self.values([expression for expression, _ in cases])
        for (expression, cut), spans in zip(cases, got):
            self.assertEqual("".join(span["text"] for span in spans), cut, expression)
        self.assertEqual(got[0], [{"text": "abcd"}])
        self.assertEqual(got[1], [{"text": "ab"}, {"text": "cd", "color": A}])
        self.assertEqual(got[2], [{"text": "abcd"}])
        self.assertEqual(got[3:], [[], [], [], []])

    def test_line_spans_count_code_points(self):
        """Red: the text is split in UTF-16 units (`text.split("")`: the smiley is two, so the tint 1
        to 2 colours half of it, and 2 columns cut it in half)."""
        text = '"a\\u{1F600}b"'
        smiley = "\U0001F600"
        got = self.values([
            self.spans(text, "[%s]" % self.tint(1, 2)),
            self.spans(text, "[]", 2),
            self.spans(text, "[%s]" % self.tint(2, 3)),
        ])
        self.assertEqual(got, [
            [{"text": "a"}, {"text": smiley, "color": A}, {"text": "b"}],
            [{"text": "a" + smiley}],
            [{"text": "a" + smiley}, {"text": "b", "color": A}],
        ])

    def test_line_spans_keep_spaces(self):
        """Red: the leading spaces of the text are trimmed (`trimStart`: the tint on column 4 would
        colour the wrong letter, and 3 columns of "  ab" would give "ab")."""
        got = self.values([
            self.spans('"    x = 1"', "[%s]" % self.tint(4, 5)),
            self.spans('"  ab"', "[]", 3),
        ])
        self.assertEqual(got, [
            [{"text": "    "}, {"text": "x", "color": A}, {"text": " = 1"}],
            [{"text": "  a"}],
        ])

    def test_require_line(self):
        """Red: the range is off by one at either end (46 or 55 returns, 47 or 54 throws), the last
        line is not worked out from the length of `lines` (a fixed 8 lines: the one-line source of
        lib/x.ts must refuse line 2), a line that is not a whole number passes (NaN and 47.5 compare
        false both ways, so only an explicit check refuses them), or a message differs from
        `CodeCard: line <n> is outside <path>:<first>-<last>` by a word or a number."""
        one = 'sourceFromDisk({ path: "lib/x.ts", from: 1, lines: ["a"] })'
        got = self.values(["requireLine(src, 47)", "requireLine(src, 54)", "requireLine(%s, 1)" % one])
        self.assertEqual(got, [None, None, None])
        got = self.errors([
            "requireLine(src, 46)", "requireLine(src, 55)", "requireLine(%s, 2)" % one,
            "requireLine(src, 47.5)", "requireLine(src, NaN)",
        ])
        self.assertEqual(got, [
            "CodeCard: line 46 is outside src/app.py:47-54",
            "CodeCard: line 55 is outside src/app.py:47-54",
            "CodeCard: line 2 is outside lib/x.ts:1-1",
            "CodeCard: line 47.5 is outside src/app.py:47-54",
            "CodeCard: line NaN is outside src/app.py:47-54",
        ])


@needs_kit_tools
class TestKitDraws(unittest.TestCase):
    """The text and stroke components, rendered to static markup (see render_cases)."""

    IMPORTS = 'import { Mono, Sans } from "../kit/text";\nimport { Draw, Mark } from "../kit/draw";\n'
    TEXT = "  ab\U0001F600"  # two leading spaces, then one code point outside the BMP
    BLUE = PALETTE["C"]["blue"]

    def render(self, **cases):
        """render_cases with the kit components in scope: each keyword is a case name, its value JSX."""
        return render_cases(self.IMPORTS, cases)

    def test_mono_forces_the_advance(self):
        """Red: textLength counts UTF-16 units instead of code points (72, not 60: the smiley is
        two), is left out, or the font is not MONO; the default fill is not C.text, the default
        anchor or weight is not start and 400; white-space:pre is dropped or the text is trimmed
        (the two leading spaces are the point); or x and y are swapped."""
        got = self.render(mono='<Mono x={10} y={20} size={20} text="%s" />' % self.TEXT)
        (text,) = got["mono"]
        self.assertEqual(text.tag, "text")
        expected = {
            "x": "10", "y": "20", "textLength": "60", "font-size": "20", "font-family": PALETTE["MONO"],
            "fill": PALETTE["C"]["text"], "text-anchor": "start", "font-weight": "400",
            "style": "white-space:pre",
        }
        self.assertEqual(attrs(text, expected), expected)
        self.assertEqual(text.text, self.TEXT)

    def test_sans_has_no_forced_advance(self):
        """Red: Sans sets a textLength (it reuses the mono width), its font is not SANS, its anchor
        or weight is ignored (the centred case would still be start and 400), its default fill, anchor
        or weight is not C.text, start and 400, or the text is not passed through."""
        got = self.render(
            plain='<Sans x={10} y={20} size={20} text="%s" />' % self.TEXT,
            centred='<Sans x={10} y={20} size={20} text="ab" anchor="middle" weight={600} />',
        )
        (plain,) = got["plain"]
        expected = {
            "x": "10", "y": "20", "textLength": None, "font-size": "20", "font-family": PALETTE["SANS"],
            "fill": PALETTE["C"]["text"], "text-anchor": "start", "font-weight": "400",
        }
        self.assertEqual(attrs(plain, expected), expected)
        self.assertEqual(plain.text, self.TEXT)
        (centred,) = got["centred"]
        expected = {"text-anchor": "middle", "font-weight": "600", "textLength": None}
        self.assertEqual(attrs(centred, expected), expected)

    def test_text_takes_fill_opacity_anchor_and_weight(self):
        """Red: Mono or Sans, one alone or both, ignores its fill, opacity, anchor or weight and
        draws the default instead (C.text, 1, start or 400)."""
        props = 'x={10} y={20} size={20} text="ab" fill="%s" opacity={0.5} anchor="end" weight={700}' % self.BLUE
        got = self.render(mono="<Mono %s />" % props, sans="<Sans %s />" % props)
        expected = {"fill": self.BLUE, "opacity": "0.5", "text-anchor": "end", "font-weight": "700"}
        for name in ("mono", "sans"):
            (text,) = got[name]
            self.assertEqual(attrs(text, expected), expected, name)

    def test_empty_or_invisible_text_draws_nothing(self):
        """Red: an empty text draws an element (a text of no characters, with a textLength of 0), an
        opacity of 0 draws one (the check is `< 0`), an opacity below 0 draws one (the check is
        `=== 0`), Mono or Sans alone lacks one of the checks, or every text draws nothing (the visible
        control case, which proves that the harness sees an element)."""
        cases = {}
        for component in ("Mono", "Sans"):
            for name, props in (("empty", 'text=""'), ("hidden", 'text="ab" opacity={0}'),
                                ("negative", 'text="ab" opacity={-0.5}'), ("visible", 'text="ab"')):
                cases["%s %s" % (component, name)] = "<%s x={10} y={20} size={20} %s />" % (component, props)
        got = self.render(**cases)
        self.assertEqual({name: len(children) for name, children in got.items()}, {
            "Mono empty": 0, "Mono hidden": 0, "Mono negative": 0, "Mono visible": 1,
            "Sans empty": 0, "Sans hidden": 0, "Sans negative": 0, "Sans visible": 1,
        })

    def test_draw_shows_the_first_part_of_a_stroke(self):
        """Red: t of 0 or less draws a path (the check is `< 0`: a round cap would show a dot), the
        dash offset is t instead of 1 - t (0.25, not 0.75), t above 1 is not clamped (-1, not 0), the
        dash array or pathLength is left out (the whole stroke would show), the fill is not none, the
        caps or joins are not round, the default width is not 2, a given width or the stroke colour
        is ignored, or an opacity of 0 or less draws a path (or the given opacity is dropped)."""
        d = "M0 0 L10 0"
        paint = 'd="%s" stroke="%s"' % (d, self.BLUE)
        got = self.render(
            unseen="<Draw %s t={0} />" % paint,
            backwards="<Draw %s t={-0.5} />" % paint,
            part="<Draw %s t={0.25} />" % paint,
            whole="<Draw %s t={1} />" % paint,
            past="<Draw %s t={2} />" % paint,
            hidden="<Draw %s t={1} opacity={0} />" % paint,
            styled="<Draw %s t={1} width={5} opacity={0.4} />" % paint,
        )
        self.assertEqual([len(got[name]) for name in ("unseen", "backwards", "hidden")], [0, 0, 0])
        (part,) = got["part"]
        self.assertEqual(part.tag, "path")
        expected = {
            "d": d, "fill": "none", "stroke": self.BLUE, "stroke-width": "2", "pathLength": "1",
            "stroke-dasharray": "1", "stroke-dashoffset": "0.75",
            "stroke-linecap": "round", "stroke-linejoin": "round",
        }
        self.assertEqual(attrs(part, expected), expected)
        self.assertEqual([got[name][0].get("stroke-dashoffset") for name in ("whole", "past")], ["0", "0"])
        expected = {"stroke-width": "5", "opacity": "0.4"}
        self.assertEqual(attrs(got["styled"][0], expected), expected)

    def test_mark_kinds(self):
        """Red: a kind takes the other's colour (the check is red or the cross green), both kinds
        draw the same path, the group's transform is not `translate(x y) scale(s)` (the scale is
        dropped or put before the translate, which moves the mark by twice the offset), the default
        scale is not 1, the stroke width is not 3, the cross is one path or a path holds a second
        subpath (a second `M` restarts the dash), the mark is not drawn about 16 px wide and centred
        on the origin (a path that starts at the origin, or is twice as large), a mark at t 0 draws
        a path or no longer returns its group, or t and opacity are not passed on to the stroke."""
        got = self.render(
            check='<Mark kind="check" x={10} y={20} t={1} scale={2} />',
            cross='<Mark kind="cross" x={10} y={20} t={1} scale={2} />',
            plain='<Mark kind="check" x={10} y={20} t={1} />',
            unseen='<Mark kind="cross" x={10} y={20} t={0} scale={2} />',
            half='<Mark kind="check" x={10} y={20} t={0.5} scale={2} opacity={0.4} />',
        )
        shapes = {}
        for name, stroke, strokes in (("check", PALETTE["C"]["green"], 1), ("cross", PALETTE["C"]["red"], 2)):
            (group,) = got[name]
            self.assertEqual(group.tag, "g")
            self.assertEqual(group.get("transform"), "translate(10 20) scale(2)", name)
            self.assertEqual(len(group), strokes, name)
            numbers = []
            for path in group:
                self.assertEqual(path.get("d").count("M"), 1, "%s: a path of one subpath" % name)
                expected = {"stroke": stroke, "stroke-width": "3", "stroke-dashoffset": "0"}
                self.assertEqual(attrs(path, expected), expected, name)
                numbers += [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", path.get("d"))]
            xs, ys = numbers[0::2], numbers[1::2]
            self.assertTrue(12 <= max(xs) - min(xs) <= 16, "%s is %s px wide" % (name, max(xs) - min(xs)))
            self.assertLessEqual(abs(max(xs) + min(xs)) / 2, 1, "%s is off-centre in x" % name)
            self.assertLessEqual(abs(max(ys) + min(ys)) / 2, 1, "%s is off-centre in y" % name)
            shapes[name] = [path.get("d") for path in group]
        self.assertNotEqual(shapes["check"], shapes["cross"])
        self.assertEqual(got["plain"][0].get("transform"), "translate(10 20) scale(1)")
        (unseen,) = got["unseen"]
        self.assertEqual((unseen.tag, len(unseen)), ("g", 0))
        (half_path,) = got["half"][0]
        expected = {"stroke-dashoffset": "0.5", "opacity": "0.4"}
        self.assertEqual(attrs(half_path, expected), expected)

    def test_cross_draws_one_diagonal_after_the_other(self):
        """Red: the cross is one path of two subpaths (the browser restarts the dash at the second
        one, so both diagonals grow at once and the X is whole at t 0.5), the first diagonal is not
        whole at t 0.5, the second starts before 0.5 or is not whole at t 1, or the opacity reaches
        only one of the two strokes."""
        got = self.render(**{
            "0.25": '<Mark kind="cross" x={0} y={0} t={0.25} />',
            "0.5": '<Mark kind="cross" x={0} y={0} t={0.5} />',
            "0.75": '<Mark kind="cross" x={0} y={0} t={0.75} />',
            "1": '<Mark kind="cross" x={0} y={0} t={1} opacity={0.4} />',
        })
        offsets = {name: [path.get("stroke-dashoffset") for path in group[0]] for name, group in got.items()}
        self.assertEqual(offsets, {"0.25": ["0.5"], "0.5": ["0"], "0.75": ["0", "0.5"], "1": ["0", "0"]})
        self.assertEqual([path.get("opacity") for path in got["1"][0]], ["0.4", "0.4"])


@needs_kit_tools
class TestKitHarness(unittest.TestCase):
    """The render harness itself: a run that is noisy or fails must say so and leave nothing behind."""

    def test_render_kit_fails_on_anything_written_to_stderr(self):
        """Red: render_kit returns the JSON of an entry although the run wrote to stderr (the entry's
        own console.error, an esbuild warning, or the warning that React prints for a list of
        elements without keys) instead of raising an AssertionError that carries the text."""
        keyless = SHOW + 'show("list", [<text>a</text>, <text>b</text>]);\nprint();\n'
        cases = {
            "console.error": ('console.error("planted"); console.log("{}");', "planted"),
            "esbuild warning": ('console.log("{}"); if (typeof Math === "strig") console.log(1);', "never evaluate"),
            "react key warning": (keyless, 'unique "key" prop'),
        }
        for name, (source, text) in cases.items():
            with self.subTest(name):
                with self.assertRaises(AssertionError) as raised:
                    render_kit(source)
                self.assertIn(text, str(raised.exception))

    def test_kit_app_removes_its_copy_when_it_fails(self):
        """Red: kit_app makes its temporary directory outside the cleanup, so a copy that fails, or a
        link that fails, leaves a film-kit-* directory behind."""
        failures = {
            "copy": mock.patch.object(shutil, "copytree", side_effect=OSError("disk full")),
            "link": mock.patch.object(Path, "symlink_to", side_effect=OSError("no links")),
        }
        for name, failure in failures.items():
            with self.subTest(name):
                with tempfile.TemporaryDirectory() as scratch, mock.patch.object(tempfile, "tempdir", scratch):
                    with failure, self.assertRaises(OSError):
                        kit_app()
                    self.assertEqual(os.listdir(scratch), [])


if __name__ == "__main__":
    unittest.main()
