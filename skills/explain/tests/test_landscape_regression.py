"""Tests for the landscape still regression: a render of the full template, compared with the
stills of a baseline rendered from a git ref before the scene components were refactored
(tests/capture_landscape_baseline.sh).

The png_diff and capture-script tests need no workspace and always run. The render class needs
EXPLAIN_VIDEO_E2E=1 and the baseline <ws>/regression/landscape-baseline (the workspace is
$EXPLAIN_VIDEO_WORKSPACE, default ~/karpathy/video-workspace). Each test names the mutation
that turns it red."""

import json
import os
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from png_diff import differing_pixels
from video_e2e import E2E, E2E_REASON, EXPLAIN, RENDER_SH, RENDER_TIMEOUT

CAPTURE = EXPLAIN / "tests" / "capture_landscape_baseline.sh"
WIDTH, HEIGHT = 1280, 720
LEVEL = 16                # a channel counts as different above this many levels (spec 7.4)
MAX_DIFFERING = 4608      # 0.5 % of 1280 x 720 pixels (spec 7.4)
TIMELINE_FIELDS = ("fps", "width", "height", "totalFrames")
SCENE_FIELDS = ("id", "component", "props", "from", "durationInFrames", "leadFrames",
                "audioFrames", "cueFrames")


def workspace():
    return Path(os.environ.get("EXPLAIN_VIDEO_WORKSPACE") or Path.home() / "karpathy" / "video-workspace")


def baseline_dir(ws=None):
    return (ws or workspace()) / "regression" / "landscape-baseline"


def write_png(path, pixels):
    """A one-row 8-bit RGB PNG of the (r, g, b) tuples."""
    def chunk(kind, body):
        return (struct.pack(">I", len(body)) + kind + body
                + struct.pack(">I", zlib.crc32(kind + body)))
    header = struct.pack(">IIBBBBB", len(pixels), 1, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes(c for pixel in pixels for c in pixel)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                           + chunk(b"IDAT", zlib.compress(row)) + chunk(b"IEND", b""))


def worktrees():
    return subprocess.run(["git", "-C", str(EXPLAIN), "worktree", "list", "--porcelain"],
                          capture_output=True, text=True, check=True).stdout


def pixel_view(timeline):
    """The fields of a timeline that decide which pixels are drawn at which frame."""
    view = {k: timeline.get(k) for k in TIMELINE_FIELDS}
    view["scenes"] = [{k: scene.get(k) for k in SCENE_FIELDS} for scene in timeline["scenes"]]
    return view


def require_baseline(base):
    """The baseline dir, or an AssertionError that says how to capture it."""
    if not (base / "BASE").is_file():
        raise AssertionError(
            "no landscape baseline at %s (BASE missing); capture it from main with: "
            "skills/explain/tests/capture_landscape_baseline.sh main" % base)
    return base


def still_names(review):
    return sorted(p.name for p in review.glob("*.png"))


def drift(base, new):
    """A message naming the first pixel-relevant timeline difference, or None."""
    a, b = pixel_view(base), pixel_view(new)
    for key in TIMELINE_FIELDS:
        if a[key] != b[key]:
            return "%s: baseline %r, new %r" % (key, a[key], b[key])
    if len(a["scenes"]) != len(b["scenes"]):
        return "scene count: baseline %d, new %d" % (len(a["scenes"]), len(b["scenes"]))
    for n, (x, y) in enumerate(zip(a["scenes"], b["scenes"]), 1):
        for key in SCENE_FIELDS:
            if x[key] != y[key]:
                return "scene %d (%s) %s: baseline %r, new %r" % (n, x["id"], key, x[key], y[key])
    return None


class PngDiffCase(unittest.TestCase):
    # red: the level parameter ignored (a fixed threshold of 40 or of 16)
    def test_png_diff_level(self):
        tmp = Path(tempfile.mkdtemp(prefix="png-diff-test-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        base = [(10, 20, 30)] * 4
        write_png(tmp / "a.png", base)
        write_png(tmp / "b.png", base[:2] + [(10, 40, 30)] + base[3:])   # +20 in one channel
        self.assertEqual(differing_pixels(tmp / "a.png", tmp / "b.png", 0, 4, 0, 1, level=16), 1)
        self.assertEqual(differing_pixels(tmp / "a.png", tmp / "b.png", 0, 4, 0, 1, level=40), 0)


class CaptureScriptCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="capture-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.ws = self.tmp / "ws"
        self.env = dict(os.environ, EXPLAIN_VIDEO_WORKSPACE=str(self.ws))

    def capture(self, *args, env=None):
        return subprocess.run(["/bin/bash", str(CAPTURE), *args], capture_output=True, text=True,
                              env=env or self.env, timeout=300)

    def seed_baseline(self):
        base = baseline_dir(self.ws)
        base.mkdir(parents=True)
        (base / "BASE").write_text("0" * 40 + "\n", encoding="utf-8")
        (base / "stale.png").write_bytes(b"old")
        return base

    # red: an unresolved ref is passed on to git worktree add, or exits 1
    def test_capture_unknown_ref_exits_2(self):
        before = worktrees()
        run = self.capture("no-such-ref-for-the-baseline")
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertEqual(worktrees(), before)
        self.assertFalse(baseline_dir(self.ws).exists())

    # red: the BASE check dropped, or the baseline emptied before the check
    def test_capture_refuses_existing_baseline(self):
        base = self.seed_baseline()
        before = worktrees()
        run = self.capture("HEAD")
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertIn("--force", run.stdout + run.stderr)
        self.assertEqual(worktrees(), before)
        self.assertTrue((base / "BASE").is_file())
        self.assertTrue((base / "stale.png").is_file())

    # red: no EXIT trap for the worktree, BASE written before the render, or --force not
    # emptying the old baseline. A fake npm fails the workspace stage of render.sh, so no
    # install or render runs.
    def test_capture_failed_render_exits_1_without_base_and_worktree(self):
        base = self.seed_baseline()
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        npm = bin_dir / "npm"
        npm.write_text("#!/bin/sh\necho 'fake npm: no install in a capture test' >&2\nexit 1\n",
                       encoding="utf-8")
        npm.chmod(npm.stat().st_mode | stat.S_IXUSR)
        before = worktrees()
        run = self.capture("HEAD", "--force", env=dict(self.env, PATH="%s:%s" % (bin_dir, os.environ["PATH"])))
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertEqual(worktrees(), before)
        self.assertFalse((base / "BASE").exists())
        self.assertFalse((base / "stale.png").exists())


@unittest.skipUnless(E2E, E2E_REASON)
class LandscapeRegressionCase(unittest.TestCase):
    # red: a baseline without BASE accepted, or a message that does not name the capture command
    def test_missing_base_fails_with_capture_hint(self):
        ws = Path(tempfile.mkdtemp(prefix="landscape-nobase-"))
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        half = baseline_dir(ws)
        half.mkdir(parents=True)
        (half / "script.json").write_text("{}", encoding="utf-8")   # half-written: no BASE
        result = unittest.TestResult()
        with mock.patch.dict(os.environ, {"EXPLAIN_VIDEO_WORKSPACE": str(ws)}):
            type(self)("test_full_template_matches_baseline").run(result)
        self.assertEqual(len(result.failures), 1, (result.failures, result.errors))
        self.assertIn("capture_landscape_baseline.sh main", result.failures[0][1])

    # red: any layout change that moves more than 0.5 % of a still by more than 16 levels
    def test_full_template_matches_baseline(self):
        base = require_baseline(baseline_dir())
        out = Path(tempfile.mkdtemp(prefix="landscape-regression-"))
        script = json.loads((base / "script.json").read_text(encoding="utf-8"))
        script["provenance"]["root"] = str(EXPLAIN)
        (out / "script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")
        shutil.copytree(base / "audio", out / "audio")
        run = subprocess.run(["/bin/bash", str(RENDER_SH), str(out), "--engine", "say"],
                             capture_output=True, text=True, timeout=RENDER_TIMEOUT)
        if run.returncode != 0:
            self.fail("render.sh exit %d, output kept in %s:\n%s%s"
                      % (run.returncode, out, run.stdout, run.stderr))

        old = json.loads((base / "build" / "timeline.json").read_text(encoding="utf-8"))
        new = json.loads((out / "build" / "timeline.json").read_text(encoding="utf-8"))
        moved = drift(old, new)
        if moved:
            self.fail("timeline drift (not a layout change; the stills are not comparable), %s; "
                      "output kept in %s" % (moved, out))

        names_old, names_new = still_names(base / "review"), still_names(out / "review")
        if names_old != names_new:
            self.fail("still names differ: only in baseline %s, only in new %s; output kept in %s"
                      % (sorted(set(names_old) - set(names_new)),
                         sorted(set(names_new) - set(names_old)), out))

        failing = []
        for name in names_old:
            count = differing_pixels(base / "review" / name, out / "review" / name,
                                     0, WIDTH, 0, HEIGHT, level=LEVEL)
            if count > MAX_DIFFERING:
                failing.append((name, count))
        if failing:
            self.fail("stills over %d pixels differing by more than %d levels (new stills kept in %s/review):\n%s"
                      % (MAX_DIFFERING, LEVEL, out, "\n".join("  %s: %d" % f for f in failing)))
        shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
