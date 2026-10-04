"""Tests for video/check_render.sh and video/verify_sync.py: the container, speech-sync and
still checks after a render.

The verify_sync tests synthesize their WAVs (a 440 Hz tone where the speech should be) and
always run. The end-to-end class reuses the one fixture render of tests/video_e2e.py and
needs EXPLAIN_VIDEO_E2E=1. Each test names the mutation that turns it red."""

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from png_diff import differing_pixels
from video_e2e import E2E, E2E_REASON, EXPLAIN, render_fixture

CHECK_RENDER = EXPLAIN / "video" / "check_render.sh"
VERIFY_SYNC = EXPLAIN / "video" / "verify_sync.py"
SCENE_BODY = EXPLAIN / "video" / "src" / "sceneBody.tsx"
RATE = 16000
FPS = 30


def write_wav(path, samples):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(array("h", samples).tobytes())


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        data = array("h")
        data.frombytes(w.readframes(w.getnframes()))
    return data


def run_sync(wav, timeline):
    return subprocess.run([sys.executable, str(VERIFY_SYNC), str(wav), str(timeline)],
                          capture_output=True, text=True, timeout=60)


# ---------- verify_sync.py on synthesized audio ----------

class VerifySyncCase(unittest.TestCase):
    """Two scenes of 15 + 60 + 36 frames; the "speech" is a 440 Hz tone of 2 s."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="verify-sync-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        scenes, start = [], 0
        for scene_id in ("one", "two"):
            scenes.append({"id": scene_id, "from": start, "durationInFrames": 111,
                           "leadFrames": 15, "audioFrames": 60, "cueFrames": {}})
            start += 111
        self.timeline = self.tmp / "timeline.json"
        self.timeline.write_text(json.dumps({"fps": FPS, "totalFrames": start, "scenes": scenes}),
                                 encoding="utf-8")
        self.scenes = scenes

    def wav(self, offsets):
        """A WAV with a 2 s tone in each scene, starting `offset` s after the scene start
        (None: no tone in that scene)."""
        total = self.scenes[-1]["from"] + self.scenes[-1]["durationInFrames"]
        samples = [0] * (total * RATE // FPS)
        for scene, offset in zip(self.scenes, offsets):
            if offset is None:
                continue
            first = round((scene["from"] / FPS + offset) * RATE)
            for n in range(2 * RATE):
                samples[first + n] = int(0.3 * 32767 * math.sin(2 * math.pi * 440 * n / RATE))
        path = self.tmp / "audio.wav"
        write_wav(path, samples)
        return path

    # red: voiced means RMS below the threshold (silence counts as speech)
    def test_sync_ok_on_aligned_tone(self):
        run = run_sync(self.wav([0.5, 0.5]), self.timeline)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stdout.splitlines(), [
            "sync: one speech 0.50-2.50 s (lead 0.50 s)",
            "sync: two speech 0.50-2.50 s (lead 0.50 s)",
        ])

    # red: lead tolerance 2 s instead of 0.25 s
    def test_sync_fail_on_shifted_tone(self):
        run = run_sync(self.wav([0.5, 1.0]), self.timeline)
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertIn("sync: FAIL two: speech starts at 1.00 s, expected 0.50 s ± 0.25",
                      run.stdout.splitlines())

    # red: a scene without voiced windows is skipped instead of failed
    def test_sync_fail_on_silence(self):
        run = run_sync(self.wav([0.5, None]), self.timeline)
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertIn("sync: FAIL two: no speech", run.stdout.splitlines())


# ---------- check_render.sh on the fixture render ----------

class ReviewDirNameCase(unittest.TestCase):
    """No render needed: the name check comes before any file is read or emptied."""

    # red: any directory accepted as the review dir (check_render.sh empties it)
    def test_review_dir_not_named_review_is_refused(self):
        tmp = Path(tempfile.mkdtemp(prefix="check-render-name-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "video.mp4").write_bytes(b"not a video")
        (tmp / "timeline.json").write_text(json.dumps({"fps": 30, "totalFrames": 30, "scenes": []}),
                                           encoding="utf-8")
        home = tmp / "home"
        home.mkdir()
        (home / "keep.txt").write_text("keep\n", encoding="utf-8")
        for target in (home, tmp / "stills"):
            with self.subTest(target=target.name):
                run = subprocess.run(
                    ["/bin/bash", str(CHECK_RENDER), str(tmp / "video.mp4"), str(tmp / "timeline.json"),
                     str(target)],
                    capture_output=True, text=True, timeout=60,
                    env={**os.environ, "EXPLAIN_VIDEO_WORKSPACE": str(tmp / "ws")},
                )
                self.assertEqual((run.returncode, run.stdout),
                                 (1, "stills: FAIL review dir must be named review: %s\n" % target),
                                 run.stderr)
        self.assertTrue((home / "keep.txt").exists())
        self.assertFalse((tmp / "stills").exists())


class ContainerSizeCase(unittest.TestCase):
    """The size check of check_container against a fake Remotion CLI: no workspace, no render.
    The fake answers each ffprobe query by its -show_entries list and fails any other tool."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="check-render-size-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        cli = self.tmp / "ws" / "app" / "node_modules" / ".bin" / "remotion"
        cli.parent.mkdir(parents=True)
        cli.write_text(
            "#!/bin/bash\n"
            'case "$*" in\n'
            '  *"stream=codec_type,codec_name"*) printf "h264,video\\naac,audio\\n" ;;\n'
            '  *"-select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x"*)\n'
            '    echo "$FAKE_SIZE" ;;\n'
            '  *"format=duration"*) echo 1.000 ;;\n'
            "  *) exit 1 ;;\n"
            "esac\n", encoding="utf-8")
        cli.chmod(0o755)
        (self.tmp / "video.mp4").write_bytes(b"fake")

    def check(self, width, height, size):
        timeline = self.tmp / "timeline.json"
        timeline.write_text(json.dumps({"fps": 30, "totalFrames": 30, "width": width, "height": height,
                                        "scenes": []}), encoding="utf-8")
        return subprocess.run(
            ["/bin/bash", str(CHECK_RENDER), str(self.tmp / "video.mp4"), str(timeline),
             str(self.tmp / "review")],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "EXPLAIN_VIDEO_WORKSPACE": str(self.tmp / "ws"), "FAKE_SIZE": size})

    # red: the size is not compared, or compared with a constant instead of the timeline's size.
    # The real ffprobe prints "1280x720x" (a trailing separator); the plain form is also read.
    def test_size_other_than_the_timeline_fails(self):
        for width, height, size in ((1080, 1920, "1280x720"), (1280, 720, "1080x1920")):
            for shape in ("%sx", "%s"):
                with self.subTest(size=size, shape=shape):
                    run = self.check(width, height, shape % size)
                    self.assertEqual((run.returncode, run.stdout),
                                     (1, "container: FAIL size %s, expected %dx%d\n" % (size, width, height)),
                                     run.stderr)

    # red: the ok line changed, or a size equal to the timeline's rejected (the trailing separator
    # of the real ffprobe left in the compared text)
    def test_size_equal_to_the_timeline_passes_with_the_unchanged_ok_line(self):
        for width, height in ((1080, 1920), (1280, 720)):
            for shape in ("%dx%dx", "%dx%d"):
                with self.subTest(size="%dx%d" % (width, height), shape=shape):
                    run = self.check(width, height, shape % (width, height))
                    self.assertEqual(run.stdout.splitlines()[0], "container: ok (1.00 s)", run.stdout)

    # red: an empty ffprobe answer reported as a size, or passed
    def test_empty_ffprobe_size_fails_as_none(self):
        run = self.check(1080, 1920, "")
        self.assertEqual((run.returncode, run.stdout),
                         (1, "container: FAIL size none, expected 1080x1920\n"), run.stderr)


class StillFramesCase(unittest.TestCase):
    """read_timeline of check_render.sh, run on its own with the script's top-level constants:
    the frame and the name of every still, without a render."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="check-render-frames-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def still_frames(self, scenes, width, height):
        """The lines read_timeline prints for a 30 fps timeline of `scenes`."""
        source = CHECK_RENDER.read_text(encoding="utf-8")
        constants = "".join(re.findall(r"^[A-Z_]+=\S+.*\n", source, re.M))
        function = re.search(r"^read_timeline\(\) \{\n.*?^\}\n", source, re.M | re.S)
        self.assertIsNotNone(function, "no read_timeline() in check_render.sh")
        timeline = self.tmp / "timeline.json"
        total = scenes[-1]["from"] + scenes[-1]["durationInFrames"]
        timeline.write_text(json.dumps({"fps": FPS, "totalFrames": total, "width": width,
                                        "height": height, "scenes": scenes}), encoding="utf-8")
        run = subprocess.run(
            ["/bin/bash", "-c", "set -eu\n%s%s\ntimeline=%s\nread_timeline\n"
             % (constants, function.group(0), timeline)],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 0, run.stderr)
        return run.stdout.splitlines()

    @staticmethod
    def scene(scene_id, start, lead, cues):
        return {"id": scene_id, "from": start, "durationInFrames": 300, "leadFrames": lead,
                "cueFrames": cues}

    # red: the scene still taken at from + leadFrames, so a brainrot still (lead 6) catches the
    # panel mid-fade (FadeIn runs 8 frames)
    def test_lead_6_scene_still_after_the_fade(self):
        lines = self.still_frames([self.scene("hook", 0, 6, {"x": 50}),
                                   self.scene("checks", 300, 6, {})], 1080, 1920)
        self.assertEqual(lines, ["30 600 1080 1920", "8 still-01-hook.png", "65 still-01-hook-1.png",
                                 "308 still-02-checks.png"])

    # red: the explainer (lead 15) still moved, which would change the landscape stills
    def test_lead_15_scene_still_unchanged(self):
        lines = self.still_frames([self.scene("one", 0, 15, {"b": 100, "a": 40}),
                                   self.scene("two", 300, 15, {"c": 290})], 1280, 720)
        self.assertEqual(lines, ["30 600 1280 720", "15 still-01-one.png", "55 still-01-one-1.png",
                                 "115 still-01-one-2.png", "315 still-02-two.png",
                                 "599 still-02-two-1.png"])

    # red: FADE_FRAMES missing, or no longer the length of FadeIn in sceneBody.tsx
    def test_fade_frames_is_the_fade_in_length(self):
        fade = re.search(r"interpolate\(frame, \[0, (\d+)\]", SCENE_BODY.read_text(encoding="utf-8"))
        self.assertIsNotNone(fade, "no FadeIn interpolate in sceneBody.tsx")
        constant = re.search(r"^FADE_FRAMES=(\d+)\b", CHECK_RENDER.read_text(encoding="utf-8"), re.M)
        self.assertIsNotNone(constant, "no FADE_FRAMES in check_render.sh")
        self.assertEqual(constant.group(1), fade.group(1))


@unittest.skipUnless(E2E, E2E_REASON)
class CheckRenderCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out, cls.result = render_fixture()
        if cls.result.returncode != 0:
            raise AssertionError("fixture render failed:\n" + cls.result.stdout + cls.result.stderr)
        cls.timeline = json.loads((cls.out / "build" / "timeline.json").read_text(encoding="utf-8"))

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="check-render-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def check(self, timeline, review):
        return subprocess.run(
            ["/bin/bash", str(CHECK_RENDER), str(self.out / "video.mp4"), str(timeline), str(review)],
            capture_output=True, text=True, timeout=300,
        )

    # red: the duration compared with a tolerance of 2 s
    def test_duration_mismatch_is_container_fail(self):
        timeline = dict(self.timeline, totalFrames=self.timeline["totalFrames"] + 30)
        path = self.tmp / "timeline.json"
        path.write_text(json.dumps(timeline), encoding="utf-8")
        run = self.check(path, self.tmp / "review")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertEqual(len(run.stdout.splitlines()), 1, run.stdout)
        self.assertRegex(run.stdout, r"^container: FAIL duration \d+\.\d\d s, expected \d+\.\d\d s\n$")

    # red: the frame size not compared with the timeline's width and height. The fixture render is
    # 1280x720; the copy of its timeline names 1080x1920 and the shared files stay untouched.
    def test_container_size_mismatch_fails(self):
        timeline = dict(self.timeline, width=1080, height=1920)
        path = self.tmp / "timeline.json"
        path.write_text(json.dumps(timeline), encoding="utf-8")
        run = self.check(path, self.tmp / "review")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertEqual(run.stdout, "container: FAIL size 1280x720, expected 1080x1920\n")

    # red: lead tolerance 2 s
    def test_shifted_speech_is_sync_fail(self):
        audio = read_wav(self.out / "build" / "rendered-audio.wav")
        second = self.timeline["scenes"][1]
        at = second["from"] * RATE // FPS
        shifted = self.tmp / "shifted.wav"
        write_wav(shifted, audio[:at] + array("h", [0] * RATE) + audio[at:])
        run = run_sync(shifted, self.out / "build" / "timeline.json")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        fails = [line for line in run.stdout.splitlines() if line.startswith("sync: FAIL")]
        self.assertTrue(fails, run.stdout)
        self.assertTrue(fails[0].startswith("sync: FAIL %s: speech starts at " % second["id"]), fails)

    def expected_stills(self):
        names = []
        for n, scene in enumerate(self.timeline["scenes"], 1):
            names.append("still-%02d-%s.png" % (n, scene["id"]))
            names += ["still-%02d-%s-%d.png" % (n, scene["id"], k)
                      for k in range(1, len(scene["cueFrames"]) + 1)]
        return sorted(names)

    # red: review/ not emptied before the stills are written
    def test_stills_named_per_scene_and_cue_and_review_cleared(self):
        review = self.out / "review"
        (review / "stale.png").write_bytes(b"old")
        run = self.check(self.out / "build" / "timeline.json", review)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(len(run.stdout.splitlines()), 3, run.stdout)
        names = sorted(p.name for p in review.iterdir())
        self.assertNotIn("stale.png", names)
        for name in names:
            self.assertRegex(name, r"^still-\d\d-[a-z0-9-]+?(-\d+)?\.png$")
        cues = sum(len(s["cueFrames"]) for s in self.timeline["scenes"])
        self.assertEqual(len(names), len(self.timeline["scenes"]) + cues)
        self.assertEqual(names, self.expected_stills())
        self.assertIn("stills (%d): ok " % len(names), run.stdout)

    # red: stills taken at the cue frame (before the motion)
    def test_still_at_cue_plus_15_shows_motion(self):
        n, scene = next((n, s) for n, s in enumerate(self.timeline["scenes"], 1)
                        if s["component"] == "bullets-appear")
        review = self.out / "review"
        start = review / ("still-%02d-%s.png" % (n, scene["id"]))
        first_cue = review / ("still-%02d-%s-1.png" % (n, scene["id"]))
        # The first bullet's row in the content box (layout.tsx: top 138, padding 24, 32 px text).
        changed = differing_pixels(start, first_cue, 48, 700, 162, 204)
        self.assertGreater(changed, 500)


if __name__ == "__main__":
    unittest.main()
