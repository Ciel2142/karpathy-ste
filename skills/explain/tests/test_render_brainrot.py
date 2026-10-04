"""End-to-end brainrot renders (EXPLAIN_VIDEO_E2E=1 only): templates/brainrot-script.json through
scripts/render.sh --engine say, twice, in the default workspace ~/karpathy/video-workspace (never
deleted here).

The generated run has EXPLAIN_BRAINROT_BACKGROUNDS pointing at an empty temp dir, so the picker
chooses the generated runner loop. The clip run points it at a temp dir that holds a copy of
fixtures/bg-1s.mp4, a 1 s clip that is shorter than the video, so it loops. Each render is cached
once per process (the pattern of video_e2e.py: temp output dir, an absolute provenance.root, the
temp dirs removed at exit). Both folders lie outside the workspace, because the picker refuses a
--dir inside <app>/bg-stage or <app>/public. The explainer E2E and the landscape regression run
after this module in the same workspace, to show that a brainrot run leaves the explainer alone.
Each test names the mutation that turns it red."""

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_render import STAGES, stage_lines
from video_e2e import E2E, E2E_REASON, EXPLAIN, RENDER_SH, RENDER_TIMEOUT

BRAINROT_TEMPLATE = EXPLAIN / "templates" / "brainrot-script.json"
CLIP = EXPLAIN / "tests" / "fixtures" / "bg-1s.mp4"
SEED = "7"  # fixes the clip choice and start, whatever the caller's environment holds
SCENES = 4  # the scenes of the brainrot template

# The ten stage lines of a brainrot run, in order; background is the one that differs per run.
ORDER = [
    r"script: ok \(%d scenes\)" % SCENES,
    r"workspace: ok /.+",
    r"narration \(say\): ok",
    r"timeline \(%d scenes, \d+\.\d s\): ok" % SCENES,
    None,
    r"render \(\d+\.\d s, \d+\.\d\d render-min/video-min\)( \(limit 2\.0\))?: ok",
    r"container: ok \(\d+\.\d\d s\)",
    r"sync: ok",
    r"stills \(\d+\): ok /.+",
    r"transcript: ok",
]
BACKGROUND = {
    "generated": r"background: ok generated",
    "clip": r"background: ok bg-1s\.mp4 @0\.0 s \(loop\)",
}
# The Background row of the transcript; the space after the @ is the transcript's (spec 6.3).
BACKGROUND_ROW = {"generated": "generated", "clip": "bg-1s.mp4 @ 0.0 s (loop)"}

_cache = {}


def workspace():
    return Path.home() / "karpathy" / "video-workspace"


def render_brainrot(kind):
    """(output dir, CompletedProcess) of the one brainrot render of this process for `kind`:
    "generated" (an empty background folder) or "clip" (a folder with a copy of the fixture)."""
    if kind not in _cache:
        out = Path(tempfile.mkdtemp(prefix="explain-brainrot-e2e-"))
        clips = Path(tempfile.mkdtemp(prefix="explain-brainrot-clips-"))
        for path in (out, clips):
            atexit.register(shutil.rmtree, path, ignore_errors=True)
        if kind == "clip":
            shutil.copy(CLIP, clips / CLIP.name)
        script = json.loads(BRAINROT_TEMPLATE.read_text(encoding="utf-8"))
        script["provenance"]["root"] = str(EXPLAIN)
        (out / "script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")
        env = {k: v for k, v in os.environ.items()
               if k not in ("EXPLAIN_VIDEO_WORKSPACE", "EXPLAIN_BRAINROT_BACKGROUNDS",
                            "EXPLAIN_BRAINROT_SEED")}
        env["EXPLAIN_BRAINROT_BACKGROUNDS"] = str(clips)
        env["EXPLAIN_BRAINROT_SEED"] = SEED
        run = subprocess.run(
            ["/bin/bash", str(RENDER_SH), str(out), "--engine", "say"],
            capture_output=True, text=True, env=env, timeout=RENDER_TIMEOUT,
        )
        _cache[kind] = (out, run)
    return _cache[kind]


def video_size(mp4):
    """The "<w>x<h>" of the first video stream of `mp4`, read by the workspace's remotion ffprobe."""
    app = workspace() / "app"
    run = subprocess.run(
        [str(app / "node_modules" / ".bin" / "remotion"), "ffprobe", "-v", "error",
         "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(mp4)],
        cwd=app, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
    assert run.returncode == 0, run.stderr
    stream = json.loads(run.stdout)["streams"][0]
    return "%dx%d" % (stream["width"], stream["height"])


@unittest.skipUnless(E2E, E2E_REASON)
class BrainrotRenderCase(unittest.TestCase):
    def check_ten_lines(self, kind):
        out, run = render_brainrot(kind)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        lines = stage_lines(run.stdout)
        self.assertEqual([line.split(":")[0].split(" ")[0] for line in lines], list(STAGES), run.stdout)
        for line, pattern in zip(lines, ORDER):
            self.assertRegex(line, "^%s$" % (pattern or BACKGROUND[kind]))
        return out

    # red: the background stage printing no line (nine lines), a stage out of order, or the
    # generated run picking a clip
    def test_generated_ten_ok_lines(self):
        self.check_ten_lines("generated")

    # red: the picker ignoring EXPLAIN_BRAINROT_BACKGROUNDS (the clip run says "generated"), or
    # the looping clip losing its " (loop)" mark
    def test_clip_ten_ok_lines(self):
        self.check_ten_lines("clip")

    # red: the composition keeping the landscape size, or the container check dropping the size
    def test_portrait_container(self):
        for kind in ("generated", "clip"):
            with self.subTest(background=kind):
                out, run = render_brainrot(kind)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertEqual(video_size(out / "video.mp4"), "1080x1920")

    # red: render.sh narrating a brainrot script without --speed 1.2, or without sentence mode
    def test_speed_in_sidecars(self):
        for kind in ("generated", "clip"):
            with self.subTest(background=kind):
                out, run = render_brainrot(kind)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                sidecars = sorted((out / "audio").glob("*.say.txt"))
                self.assertEqual(len(sidecars), SCENES, [p.name for p in sidecars])
                for sidecar in sidecars:
                    text = sidecar.read_text(encoding="utf-8")
                    self.assertTrue(text.startswith("engine=say\n"), sidecar.name)
                    self.assertIn("\nspeed=1.2\nmode=sentences\n", text, sidecar.name)

    # red: the Format row missing or in landscape size, or the Background row left as "pending" or
    # showing another run's background
    def test_transcript_rows(self):
        for kind in ("generated", "clip"):
            with self.subTest(background=kind):
                out, run = render_brainrot(kind)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                page = (out / "index.html").read_text(encoding="utf-8")
                self.assertIn("<dt>Format</dt><dd>brainrot (1080×1920)</dd>", page)
                self.assertIn("<dt>Background</dt><dd>%s</dd>" % BACKGROUND_ROW[kind], page)

    # red: stills only for the scenes (the cue stills dropped), or a still in the wrong dir
    def test_stills_present(self):
        for kind in ("generated", "clip"):
            with self.subTest(background=kind):
                out, run = render_brainrot(kind)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                timeline = json.loads((out / "build" / "timeline.json").read_text(encoding="utf-8"))
                expected = set()
                for n, scene in enumerate(timeline["scenes"], 1):
                    expected.add("still-%02d-%s.png" % (n, scene["id"]))
                    for k in range(1, len(scene["cueFrames"]) + 1):
                        expected.add("still-%02d-%s-%d.png" % (n, scene["id"], k))
                found = {p.name for p in (out / "review").glob("*.png")}
                self.assertEqual(found, expected)
                self.assertGreater(len(expected), SCENES)
                stills = [line for line in stage_lines(run.stdout) if line.startswith("stills (")]
                self.assertEqual(stills[0].split(")")[0], "stills (%d" % len(expected))


if __name__ == "__main__":
    unittest.main()
