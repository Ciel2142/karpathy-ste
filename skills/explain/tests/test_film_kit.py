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


if __name__ == "__main__":
    unittest.main()
