"""Gated stills of the brainrot Short layout (EXPLAIN_VIDEO_E2E=1): a two-scene brainrot script is
narrated with the say engine at speed 1.2 and built into a timeline, and `remotion still Explain`
draws single frames of it. Each test names the mutation that turns it red.

setUpClass syncs the workspace itself (video-workspace.sh --engine say), because the app under
<ws>/app must hold the current src/ before any still is drawn; the class is skipped, with the
script's output as the reason, when that fails. The workspace is $EXPLAIN_VIDEO_WORKSPACE, default
~/karpathy/video-workspace."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from png_diff import differing_pixels, read_png
from test_narrate import NARRATE_PY
from test_video_timeline import APP_LINES, TOOL
from test_video_timeline_brainrot import brainrot_script
from video_e2e import E2E, E2E_REASON, EXPLAIN

REPO = EXPLAIN.parent.parent
WORKSPACE_SH = EXPLAIN / "scripts" / "video-workspace.sh"
SYNC_TIMEOUT = 900
STILL_TIMEOUT = 300
WIDTH, HEIGHT = 1080, 1920
SEAM = 960


def workspace():
    return Path(os.environ.get("EXPLAIN_VIDEO_WORKSPACE") or Path.home() / "karpathy" / "video-workspace")


def png_size(path):
    """(width, height) from the IHDR chunk of a PNG."""
    head = Path(path).read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n", path
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def yellow_pixels(path, y0, y1):
    """Pixels in rows [y0, y1) that read as the active caption word (#ffd400): R > 220, G > 190, B < 60."""
    width, channels, rows = read_png(path, y1)
    return sum(
        1
        for y in range(y0, y1)
        for x in range(width)
        if rows[y][x * channels] > 220 and rows[y][x * channels + 1] > 190 and rows[y][x * channels + 2] < 60
    )


@unittest.skipUnless(E2E, E2E_REASON)
class ShortStillCase(unittest.TestCase):
    """One sync, one narrate and one build, shared by the tests; stills are drawn on demand and kept."""

    @classmethod
    def setUpClass(cls):
        sync = subprocess.run([str(WORKSPACE_SH), "--engine", "say"], cwd=REPO,
                              capture_output=True, text=True, timeout=SYNC_TIMEOUT)
        if sync.returncode != 0:
            raise unittest.SkipTest("video-workspace.sh --engine say exit %d: %s"
                                    % (sync.returncode, (sync.stdout + sync.stderr).strip()[-400:]))
        cls.app = workspace() / "app"
        tmp = tempfile.TemporaryDirectory(prefix="short-still-")
        cls.addClassCleanup(tmp.cleanup)
        cls.root = Path(tmp.name)
        (cls.root / "src").mkdir()
        (cls.root / "src" / "app.py").write_text("\n".join(APP_LINES) + "\n", encoding="utf-8")

        script = brainrot_script()
        script["scenes"] = script["scenes"][:2]   # intro (bullets-appear) and flow (diagram walk)
        script_path = cls.root / "script.json"
        script_path.write_text(json.dumps(script), encoding="utf-8")
        audio = cls.root / "audio"
        narrate = subprocess.run(
            [sys.executable, str(NARRATE_PY), "--engine", "say", "--speed", "1.2", str(script_path), str(audio)],
            capture_output=True, text=True)
        if narrate.returncode != 0:
            raise AssertionError("narrate.py exit %d: %s" % (narrate.returncode, narrate.stdout + narrate.stderr))
        built = cls.root / "build" / "timeline.json"
        build = subprocess.run(
            ["node", str(TOOL), str(script_path), str(audio / "durations.json"), "say", str(built),
             "--root", str(cls.root)],
            capture_output=True, text=True)
        if build.returncode != 0:
            raise AssertionError("build-timeline.mjs exit %d: %s" % (build.returncode, build.stdout + build.stderr))
        timeline = json.loads(built.read_text(encoding="utf-8"))

        # What render.sh does before a render: the narration clips go under <app>/public/audio.
        (cls.app / "public" / "audio").mkdir(parents=True, exist_ok=True)
        for scene in timeline["scenes"]:
            shutil.copy(cls.root / scene["audio"], cls.app / "public" / scene["audio"])

        first = timeline["scenes"][0]
        cls.first_word_frame = first["from"] + first["captions"][0]["words"][0]["from"]
        cls.timeline_path = cls.root / "timeline.json"
        cls.timeline_path.write_text(json.dumps(dict(timeline, background={"kind": "generated"})), encoding="utf-8")
        cls.no_background_path = cls.root / "timeline-no-background.json"
        cls.no_background_path.write_text(json.dumps(timeline), encoding="utf-8")
        cls.stills = {}

    def run_still(self, props, frame, name):
        """`remotion still Explain` of one frame; the CompletedProcess and the PNG path."""
        png = self.root / name
        run = subprocess.run(
            [str(self.app / "node_modules" / ".bin" / "remotion"), "still", "Explain", str(png),
             "--props", str(props), "--frame", str(frame)],
            cwd=self.app, capture_output=True, text=True, timeout=STILL_TIMEOUT)
        return run, png

    def still(self, frame):
        """The PNG of `frame` of the timeline with a generated background; drawn once per frame."""
        if frame not in self.stills:
            run, png = self.run_still(self.timeline_path, frame, "still-%d.png" % frame)
            self.assertEqual(run.returncode, 0, "remotion still exit %d:\n%s%s" % (run.returncode, run.stdout, run.stderr))
            self.stills[frame] = png
        return self.stills[frame]

    # red: Explain keeps drawing the 1280 x 720 landscape stack for a brainrot timeline, so the
    # frame is the timeline's size but its content is landscape in a portrait frame
    def test_short_still_is_portrait(self):
        self.assertEqual(png_size(self.still(20)), (WIDTH, HEIGHT))

    # red: Background missing, or RunnerLoop drawn from a constant frame instead of useCurrentFrame
    def test_background_moves(self):
        moved = differing_pixels(self.still(20), self.still(40), 0, WIDTH, 1000, HEIGHT, level=16)
        self.assertGreater(moved, 1000)

    # red: CaptionBand missing, drawn off the seam, or the active word not #ffd400
    def test_caption_has_active_yellow(self):
        frame = self.first_word_frame + 2
        self.assertGreater(yellow_pixels(self.still(frame), SEAM - 100, SEAM + 100), 200)

    # red: the panel div missing or not 1080 x 960 white, so the black frame or the background shows
    # above the seam; the scene title starts 48 px down, so row 20 is margin only
    def test_panel_is_white_above_the_seam(self):
        _, channels, rows = read_png(self.still(20), 21)
        row = rows[20]
        off_white = [x for x in range(WIDTH) if tuple(row[x * channels:x * channels + 3]) != (255, 255, 255)]
        self.assertEqual(off_white, [])

    # red: Short renders an empty bottom half instead of throwing when the timeline has no background
    def test_missing_background_fails_loudly(self):
        run, _ = self.run_still(self.no_background_path, 20, "still-no-background.png")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("Short: timeline has no background", run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
