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
PICKER = EXPLAIN / "video" / "pick_background.py"
FIXTURE_CLIP = EXPLAIN / "tests" / "fixtures" / "bg-1s.mp4"
SYNC_TIMEOUT = 900
STILL_TIMEOUT = 300
WIDTH, HEIGHT = 1080, 1920
SEAM = 960
# The non-looping clip of Background.tsx (a clip as long as the video, at a random start), here
# the 1 s fixture from 0.5 s: OffthreadVideo with trimBefore 15 frames and no Loop.
LONG_CLIP = {"kind": "clip", "file": "bg-1s.mp4", "src": "bg/clip.mp4", "start": 0.5,
             "seconds": 1.0, "loop": False}
CLIP_TOP = 1000         # the background rows below any one-line caption (its bottom is above y 1006)
CLIP_MOVED = 200_000    # see test_long_clip_plays_from_its_start


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


def lit_pixels(path, y0, y1):
    """Pixels in rows [y0, y1) with some channel above 40: not black."""
    width, channels, rows = read_png(path, y1)
    return sum(1 for y in range(y0, y1) for x in range(width)
               if max(rows[y][x * channels:x * channels + 3]) > 40)


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

    # red: calculateMetadata ignores the timeline's width and height (the still is the composition's
    # default size), or Short, a scene body or RunnerLoop throws at frame 20 (the still exits non-zero,
    # so still() fails before the size is read). It cannot catch landscape content in a portrait frame:
    # the frame size comes from the timeline either way; the tests below look at the content.
    def test_short_still_is_portrait(self):
        self.assertEqual(png_size(self.still(20)), (WIDTH, HEIGHT))

    # red: Background missing, or RunnerLoop drawn from a constant frame instead of useCurrentFrame.
    # The stripes advance 24 px a frame with a 120 px period, so two frames a multiple of 5 apart draw
    # identical stripes; 20 and 43 are 23 apart (72 px of scroll), so the stripes count here. They are
    # not what the threshold guards: the runner and the obstacles alone move about 48000 pixels
    # between these frames, so a RunnerLoop that ignores state.stripe still passes.
    def test_background_moves(self):
        moved = differing_pixels(self.still(20), self.still(43), 0, WIDTH, 1000, HEIGHT, level=16)
        self.assertGreater(moved, 1000)

    # red: CaptionBand missing, drawn off the seam, or the active word not #ffd400
    def test_caption_has_active_yellow(self):
        frame = self.first_word_frame + 2
        self.assertGreater(yellow_pixels(self.still(frame), SEAM - 100, SEAM + 100), 200)

    # red: the panel div missing, not 1080 x 960, or not white, so the black frame or the background
    # shows above the seam. Each row guards one thing:
    #   row 20  the panel's top and width: the div missing, off the frame's top, or narrower than 1080.
    #           The scene title starts 48 px down, so the row is margin only.
    #   row 900 the panel's height: a panel shorter than 901 px (a 1080 x 500 panel keeps row 20 white).
    #           The row is below the panel content (it ends at or above y 840) and above a one-line
    #           caption (its top is about y 914), so it is margin only too.
    # A panel taller than 960 px is caught by test_background_moves, which then sees no background.
    def test_panel_is_white_above_the_seam(self):
        _, channels, rows = read_png(self.still(20), 901)
        for y in (20, 900):
            with self.subTest(row=y):
                off_white = [x for x in range(WIDTH)
                             if tuple(rows[y][x * channels:x * channels + 3]) != (255, 255, 255)]
                self.assertEqual(off_white, [])

    # red: Short renders an empty bottom half instead of throwing when the timeline has no background
    def test_missing_background_fails_loudly(self):
        run, _ = self.run_still(self.no_background_path, 20, "still-no-background.png")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("Short: timeline has no background", run.stdout + run.stderr)

    def long_clip_props(self):
        """Stage the fixture clip as render.sh does, then write the timeline with LONG_CLIP. The
        picker runs on a temp folder holding a copy of the clip (it refuses a folder inside the
        workspace) and puts it into <ws>/bg-stage behind <app>/public/bg; it marks the 1 s clip
        as a loop, which the props then replace."""
        clips = self.root / "clips"
        clips.mkdir(exist_ok=True)
        shutil.copy(FIXTURE_CLIP, clips / FIXTURE_CLIP.name)
        picked = self.root / "timeline-picked.json"
        shutil.copy(self.timeline_path, picked)
        run = subprocess.run(
            [sys.executable, "-B", str(PICKER), str(picked), str(self.app / "node_modules" / ".bin" / "remotion"),
             str(self.app), "--dir", str(clips), "--seed", "7"],
            capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
        self.assertEqual((run.returncode, run.stdout), (0, "background: ok bg-1s.mp4 @0.0 s (loop)\n"), run.stderr)
        props = self.root / "timeline-long-clip.json"
        timeline = json.loads(picked.read_text(encoding="utf-8"))
        props.write_text(json.dumps(dict(timeline, background=LONG_CLIP)), encoding="utf-8")
        return props

    # The non-looping clip, the main production path. The fixture (tests/make_bg_fixture.py) is 30
    # frames of purple (72,28,120) and green (60,200,110) diagonal stripes, 8 px bands with a period
    # of 16 px along x + y, that move 2 px a frame, so its frames do differ: 10 frames apart the
    # stripes are shifted 20 = 4 (mod 16) px, which recolours half the picture. Video frames 0 and
    # 10 show clip frames 15 and 25. Covered to 1080 x 960, the rows CLIP_TOP..1920 (993,600 px)
    # differ in about half their pixels plus the blurred stripe borders (646,241 measured);
    # CLIP_MOVED = 200,000 leaves room for scaling and H.264 and stays far above a frozen picture
    # (95 measured with the start taken in ms) and the at most 6,480 caption pixels in those rows.
    # Both colours have a channel of 120 or more, so a picture is lit nearly everywhere (993,600
    # and 993,525 measured); black is not.
    # red: the clip not served (404, the still exits non-zero), Background drawing nothing or black
    # for a clip, or a frozen picture (a trimBefore past the clip's end, e.g. the start in the wrong
    # unit). Not caught: the Loop branch taken, or another trimBefore inside the clip; the stripes
    # repeat every 8 frames, so two stills show that the clip plays, not which of its frames.
    def test_long_clip_plays_from_its_start(self):
        props = self.long_clip_props()
        stills = []
        for frame in (0, 10):
            run, png = self.run_still(props, frame, "still-long-clip-%d.png" % frame)
            self.assertEqual(run.returncode, 0, "remotion still exit %d:\n%s%s" % (run.returncode, run.stdout, run.stderr))
            stills.append(png)
        region = WIDTH * (HEIGHT - CLIP_TOP)
        for png in stills:
            with self.subTest(still=png.name):
                self.assertGreater(lit_pixels(png, CLIP_TOP, HEIGHT), 0.9 * region)
        moved = differing_pixels(stills[0], stills[1], 0, WIDTH, CLIP_TOP, HEIGHT)
        self.assertGreater(moved, CLIP_MOVED)


if __name__ == "__main__":
    unittest.main()
