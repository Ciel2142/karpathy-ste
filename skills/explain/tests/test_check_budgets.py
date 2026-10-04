"""Tests for video/check_budgets.py: the length budgets render.sh checks on build/timeline.json.

The limits come from the timeline (maxSceneSeconds, maxTotalSeconds), not from render.sh, so the
explainer (60 s scene, 150 s total) and the brainrot short (30 s, 90 s) share one check. The
fixture timelines are written by the tests at 30 fps. Each test names the mutation that turns it
red."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
CHECK_BUDGETS = TESTS.parent / "video" / "check_budgets.py"

FPS = 30


class CheckBudgetsCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="check-budgets-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write_timeline(self, frames, max_scene, max_total, total_frames=None, drop=()):
        """A timeline whose scenes a, b, c... last `frames` frames each; totalFrames defaults to
        their sum."""
        scenes = [{"id": "abc"[i] if i < 3 else "s%d" % i, "durationInFrames": n}
                  for i, n in enumerate(frames)]
        timeline = {"fps": FPS, "totalFrames": sum(frames) if total_frames is None else total_frames,
                    "maxSceneSeconds": max_scene, "maxTotalSeconds": max_total, "scenes": scenes}
        for key in drop:
            del timeline[key]
        path = self.tmp / "timeline.json"
        path.write_text(json.dumps(timeline), encoding="utf-8")
        return path

    def check(self, path):
        return subprocess.run([sys.executable, "-B", str(CHECK_BUDGETS), str(path)],
                              capture_output=True, text=True, timeout=30)

    # red: the scene test is ">=" or reads a fixed limit (a 60 s scene fails, or 60.1 s passes)
    def test_explainer_scene_at_60_ok_and_over_fails(self):
        at_limit = self.check(self.write_timeline([1800], 60, 150))
        self.assertEqual(at_limit.returncode, 0, at_limit.stderr)
        self.assertEqual(at_limit.stdout, "ok 1 60.0 60.000\n")
        over = self.check(self.write_timeline([1803], 60, 150))
        self.assertEqual(over.returncode, 0, over.stderr)
        self.assertEqual(over.stdout, "FAIL scene a is 60.1 s (max 60)\n")

    # red: the limits are the explainer constants, not the timeline's
    def test_brainrot_scene_30_ok_31_fails(self):
        at_limit = self.check(self.write_timeline([900], 30, 90))
        self.assertEqual(at_limit.returncode, 0, at_limit.stderr)
        self.assertEqual(at_limit.stdout, "ok 1 30.0 30.000\n")
        over = self.check(self.write_timeline([930], 30, 90))
        self.assertEqual(over.returncode, 0, over.stderr)
        self.assertEqual(over.stdout, "FAIL scene a is 31.0 s (max 30)\n")

    # red: the total limit read from the scene limit, or a total of 90 s fails
    def test_brainrot_total_90_ok_91_fails(self):
        at_limit = self.check(self.write_timeline([900, 900, 900], 30, 90))
        self.assertEqual(at_limit.returncode, 0, at_limit.stderr)
        self.assertEqual(at_limit.stdout, "ok 3 90.0 90.000\n")
        over = self.check(self.write_timeline([900, 900, 900, 30], 30, 90))
        self.assertEqual(over.returncode, 0, over.stderr)
        self.assertEqual(over.stdout, "FAIL total 91.0 s (max 90)\n")

    # red: the explainer total text changes (render.sh prints it after "timeline: ")
    def test_explainer_total_text_unchanged(self):
        run = self.check(self.write_timeline([1500, 1500, 1500, 30], 60, 150))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "FAIL total 151.0 s (max 150)\n")

    # red: a missing key falls back to a default limit instead of exit 2
    def test_missing_budget_keys_exit_2(self):
        for key in ("maxSceneSeconds", "maxTotalSeconds"):
            with self.subTest(key=key):
                run = self.check(self.write_timeline([900], 30, 90, drop=(key,)))
                self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
                self.assertEqual(run.stdout, "")
                self.assertEqual(len(run.stderr.splitlines()), 1, run.stderr)
                self.assertIn(key, run.stderr)


if __name__ == "__main__":
    unittest.main()
