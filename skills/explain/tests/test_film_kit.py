"""Tests for the film kit of the explain skill's video rung (video/src/kit/): the palette, the motion
helpers and the other modules a film scene is written against. The pure modules run through Node
(which strips the types), so the values checked here are the ones a scene draws with. Always on;
skipped only when `node` is missing. Each test names the mutation that turns it red."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent / "video" / "src" / "kit"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "film-timeline.json"

NODE = shutil.which("node")
NO_NODE_REASON = "node is not on PATH"


def run_node(script):
    """Run `script` (ES module source) in Node and return what it prints as parsed JSON."""
    done = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        capture_output=True, text=True, timeout=60,
    )
    if done.returncode != 0:
        raise AssertionError("node exited %d: %s" % (done.returncode, done.stderr.strip()))
    return json.loads(done.stdout)


def kit_url(name):
    """The file URL of the kit module `name` (for example "motion.ts"), as Node imports it."""
    return (KIT / name).as_uri()


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
class TestMarks(unittest.TestCase):
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

    def calls(self, expressions, scenes=None):
        """Evaluate each JS expression of `expressions` in order, with `at` the makeAt of `scenes`
        (default: the scenes of the film-timeline fixture). Each result is {"value": v}, or
        {"error": message} when the call threw: a thrown error is read by its message."""
        if scenes is None:
            scenes = json.loads(FIXTURE.read_text())["scenes"]
        return run_node(
            'import { makeAt } from "%s";'
            "const at = makeAt(%s);"
            "const out = [%s].map((call) => {"
            "  try { return { value: call() }; } catch (e) { return { error: e.message }; }"
            "});"
            "console.log(JSON.stringify(out));"
            % (kit_url("marks.ts"), json.dumps(scenes), ", ".join("() => %s" % e for e in expressions))
        )

    def values(self, expressions, scenes=None):
        """The value of each expression; fails when one of them threw."""
        got = self.calls(expressions, scenes)
        for expression, result in zip(expressions, got):
            self.assertIn("value", result, "%s threw: %s" % (expression, result.get("error")))
        return [result["value"] for result in got]

    def errors(self, expressions, scenes=None):
        """The message each expression threw; fails when one of them returned a value."""
        got = self.calls(expressions, scenes)
        for expression, result in zip(expressions, got):
            self.assertIn("error", result, "%s returned %s" % (expression, result.get("value")))
        return [result["error"] for result in got]

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


if __name__ == "__main__":
    unittest.main()
