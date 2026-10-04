"""Tests for the pure logic of the brainrot short: which caption chunk and word show at a frame,
and the generated runner's motion. They run the real .ts modules through Node (which strips the
types), so the values checked here are the ones the components draw with. Always on; skipped only
when `node` is missing. Each test names the mutation that turns it red."""

import json
import math
import shutil
import subprocess
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "video" / "src" / "short"
CAPTIONS_URL = (SRC / "captions.ts").as_uri()
RUNNER_URL = (SRC / "runner.ts").as_uri()

NODE = shutil.which("node")
NO_NODE_REASON = "node is not on PATH"

BEAT = 20
EPS = 1e-9


def run_node(script):
    """Run `script` (ES module source) in Node and return what it prints as parsed JSON."""
    done = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        capture_output=True, text=True, timeout=60,
    )
    if done.returncode != 0:
        raise AssertionError("node exited %d: %s" % (done.returncode, done.stderr.strip()))
    return json.loads(done.stdout)


def chunk(start, end, *words):
    """A caption chunk [start, end) whose words are (text, from, to) triples."""
    return {"from": start, "to": end,
            "words": [{"text": t, "from": f, "to": e} for (t, f, e) in words]}


@unittest.skipIf(NODE is None, NO_NODE_REASON)
class TestActiveCaption(unittest.TestCase):
    def active(self, chunks, frames):
        """activeCaption(chunks, f) for each f in `frames`, as {frame: result-or-null}."""
        got = run_node(
            'import { activeCaption } from "%s";'
            "const chunks = %s;"
            "const out = {};"
            "for (const f of %s) out[f] = activeCaption(chunks, f);"
            "console.log(JSON.stringify(out));"
            % (CAPTIONS_URL, json.dumps(chunks), json.dumps(frames))
        )
        return {int(k): v for k, v in got.items()}

    def test_caption_inside_chunk(self):
        """Red: the chunk bounds or the word rule shift: `<` instead of `<=` on a word start (frame
        10 would still say word 0), the first word not chosen at the chunk start, or the word
        index taken as the first word with from <= frame instead of the last."""
        words = (("one", 6, 10), ("two", 10, 15), ("three", 15, 21))
        chunks = [chunk(6, 21, *words), chunk(21, 30, ("four", 21, 30))]
        got = self.active(chunks, [6, 7, 9, 10, 14, 15, 20, 21])
        self.assertEqual(got[6]["word"], 0)
        self.assertEqual(got[7]["word"], 0)
        self.assertEqual(got[7]["chunk"], chunks[0])
        self.assertEqual(got[9]["word"], 0)
        self.assertEqual(got[10]["word"], 1)
        self.assertEqual(got[14]["word"], 1)
        self.assertEqual(got[15]["word"], 2)
        self.assertEqual(got[20]["word"], 2)
        # `to` is exclusive: frame 21 belongs to the next chunk.
        self.assertEqual(got[21]["chunk"], chunks[1])
        self.assertEqual(got[21]["word"], 0)

    def test_caption_zero_length_chunk_skipped(self):
        """Red: a zero-length chunk can be chosen (an inclusive upper bound `frame <= to` picks
        the first chunk at frame 6), so the caption flickers a word that was never spoken."""
        chunks = [chunk(6, 6, ("skipped", 6, 6)), chunk(6, 15, ("shown", 6, 15))]
        got = self.active(chunks, [6, 7, 14])
        for frame in (6, 7, 14):
            self.assertEqual(got[frame]["chunk"]["words"][0]["text"], "shown", "frame %d" % frame)
        # A zero-length chunk between two real ones is passed over as well.
        tiled = [chunk(0, 5, ("a", 0, 5)), chunk(5, 5, ("z", 5, 5)), chunk(5, 9, ("b", 5, 9))]
        got = self.active(tiled, [4, 5, 8])
        self.assertEqual(got[4]["chunk"]["words"][0]["text"], "a")
        self.assertEqual(got[5]["chunk"]["words"][0]["text"], "b")
        self.assertEqual(got[8]["chunk"]["words"][0]["text"], "b")
        # Only zero-length chunks: nothing shows.
        self.assertIsNone(self.active([chunk(3, 3, ("z", 3, 3))], [3])[3])

    def test_caption_none_before_and_after(self):
        """Red: the lookup falls back to the first or last chunk when no chunk matches, so a
        caption shows before the first word, after the last one, or in a gap between chunks."""
        chunks = [chunk(6, 21, ("one", 6, 21))]
        got = self.active(chunks, [0, 5, 21, 22, 100])
        for frame in (0, 5, 21, 22, 100):
            self.assertIsNone(got[frame], "frame %d" % frame)
        gap = [chunk(6, 10, ("a", 6, 10)), chunk(12, 20, ("b", 12, 20))]
        got = self.active(gap, [9, 10, 11, 12])
        self.assertIsNotNone(got[9])
        self.assertIsNone(got[10])
        self.assertIsNone(got[11])
        self.assertIsNotNone(got[12])
        self.assertIsNone(self.active([], [0, 10])[0])


@unittest.skipIf(NODE is None, NO_NODE_REASON)
class TestRunnerState(unittest.TestCase):
    def states(self, seed, frames):
        """runnerState(f, seed) for each f in `frames`, as {frame: state}."""
        got = run_node(
            'import { runnerState } from "%s";'
            "const out = {};"
            "for (const f of %s) out[f] = runnerState(f, %d);"
            "console.log(JSON.stringify(out));" % (RUNNER_URL, json.dumps(frames), seed)
        )
        return {int(k): v for k, v in got.items()}

    def test_runner_deterministic(self):
        """Red: the state reads Math.random(), Date or a module-level counter, so two calls with
        the same arguments differ (two renders of the same video would not be the same)."""
        frames = list(range(0, 301))
        first = self.states(7, frames)
        second = self.states(7, frames)
        self.assertEqual(first, second)
        # Calling out of order, and repeating a frame, gives the same answer: no hidden state.
        got = run_node(
            'import { runnerState } from "%s";'
            "const a = runnerState(250, 7); runnerState(3, 7); const b = runnerState(250, 7);"
            "console.log(JSON.stringify({ a, b }));" % RUNNER_URL
        )
        self.assertEqual(got["a"], got["b"])
        self.assertEqual(got["a"], first[250])

    def test_runner_lane_changes_on_beats(self):
        """Red: the lane is taken from the frame, not the beat, so it changes mid-beat; or the
        lane never changes at all."""
        frames = list(range(0, 601))
        states = self.states(7, frames)
        changes = [f for f in frames[1:] if states[f]["lane"] != states[f - 1]["lane"]]
        self.assertTrue(changes, "the runner never changes lane in 600 frames")
        for f in changes:
            self.assertEqual(f % BEAT, 0, "lane changed at frame %d, inside a beat" % f)

    def test_runner_hop_only_in_lane_change(self):
        """Red: hop is non-zero in a beat that keeps its lane, or it is not sin(pi * k / BEAT)
        for the k-th frame of the beat that changes lane."""
        frames = list(range(0, 601))
        states = self.states(7, frames)
        changed_beats = 0
        for start in range(BEAT, 600, BEAT):
            changed = states[start]["lane"] != states[start - 1]["lane"]
            changed_beats += changed
            for f in range(start, start + BEAT):
                want = math.sin(math.pi * (f % BEAT) / BEAT) if changed else 0
                self.assertAlmostEqual(states[f]["hop"], want, delta=EPS, msg="frame %d" % f)
        self.assertGreater(changed_beats, 0)
        self.assertLess(changed_beats, 600 // BEAT - 1)

    def test_runner_seed_matters(self):
        """Red: the seed is ignored, so every seed draws the same road."""
        frames = list(range(0, 600))
        a, b = self.states(7, frames), self.states(8, frames)
        self.assertTrue(any(a[f] != b[f] for f in frames))

    def test_runner_ranges(self):
        """Red: lane leaves {0,1,2}, hop leaves [0,1], stripe is not (frame * 24) mod 120, an
        obstacle has z outside [0,1), or more than 3 obstacles are on screen."""
        frames = list(range(0, 601))
        states = self.states(7, frames)
        for f in frames:
            s = states[f]
            self.assertIn(s["lane"], (0, 1, 2), "frame %d" % f)
            self.assertGreaterEqual(s["hop"], 0, "frame %d" % f)
            self.assertLessEqual(s["hop"], 1, "frame %d" % f)
            self.assertGreaterEqual(s["stripe"], 0, "frame %d" % f)
            self.assertLess(s["stripe"], 120, "frame %d" % f)
            self.assertEqual(s["stripe"], (f * 24) % 120, "frame %d" % f)
            self.assertLessEqual(len(s["obstacles"]), 3, "frame %d" % f)
            for o in s["obstacles"]:
                self.assertIn(o["lane"], (0, 1, 2), "frame %d" % f)
                self.assertGreaterEqual(o["z"], 0, "frame %d" % f)
                self.assertLess(o["z"], 1, "frame %d" % f)
        self.assertTrue(any(states[f]["obstacles"] for f in frames), "no obstacle ever shows")

    def test_runner_obstacles_advance(self):
        """Red: an obstacle does not advance 1/60 per frame in its own lane, or it vanishes or
        jumps lane between frames while still on screen (the obstacle list is not a pure
        function of the spawns of the last three beats)."""
        frames = list(range(0, 400))
        states = self.states(7, frames)
        seen = 0
        for f in frames[:-1]:
            nxt = states[f + 1]["obstacles"]
            for o in states[f]["obstacles"]:
                z = o["z"] + 1 / 60
                if z >= 1 - EPS:
                    continue
                seen += 1
                match = [n for n in nxt if n["lane"] == o["lane"] and abs(n["z"] - z) < 1e-6]
                self.assertEqual(len(match), 1, "frame %d: obstacle %r did not advance" % (f, o))
        self.assertGreater(seen, 0)
        # A spawn arrives at z = 0, on a beat boundary.
        for f in frames[1:]:
            old = {(o["lane"], round(o["z"] * 60)) for o in states[f - 1]["obstacles"]}
            for o in states[f]["obstacles"]:
                if (o["lane"], round(o["z"] * 60) - 1) not in old:
                    self.assertAlmostEqual(o["z"], 0, delta=1e-6, msg="frame %d" % f)
                    self.assertEqual(f % BEAT, 0, "frame %d: obstacle spawned mid-beat" % f)


if __name__ == "__main__":
    unittest.main()
