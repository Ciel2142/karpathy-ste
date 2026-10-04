"""Tests for video/pick_background.py (spec 4.4 and 7.3): which background clip the brainrot short
gets, how it is staged for Remotion, and what is written into the timeline. A fake `remotion`
prints canned ffprobe JSON per file name; the cases marked "real" use the workspace CLI
(<ws>/app/node_modules/.bin/remotion, ws = $EXPLAIN_VIDEO_WORKSPACE or ~/karpathy/video-workspace)
and are skipped, naming video-workspace.sh, when it is missing. Every test uses a temp dir as the
app dir, never the real workspace app. Each test names the mutation that turns it red."""

import contextlib
import io
import json
import os
import random
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
EXPLAIN = TESTS.parent
VIDEO = EXPLAIN / "video"
PICKER = VIDEO / "pick_background.py"
FIXTURES = TESTS / "fixtures"
FIXTURE_CLIP = FIXTURES / "bg-1s.mp4"

sys.path.insert(0, str(VIDEO))

FPS = 30
VIDEO_SECONDS = 3  # 90 frames
GENERATED = "background: ok generated"


def workspace_remotion():
    ws = os.environ.get("EXPLAIN_VIDEO_WORKSPACE") or str(Path.home() / "karpathy" / "video-workspace")
    return Path(ws) / "app" / "node_modules" / ".bin" / "remotion"


REAL_REMOTION = workspace_remotion()
NO_REMOTION_REASON = "workspace remotion CLI missing at %s: run scripts/video-workspace.sh" % REAL_REMOTION

# Prints the canned probe of the file named by its last argument; FAKE_PROBE maps a file name to
# {"stdout": str, "exit": int, "sleep": seconds}. A name that is not in the map exits 1 with {}.
# FAKE_LOG gets one JSON line per call: the argv, the cwd and whether stdin is /dev/null.
FAKE_REMOTION = """#!{python}
import json, os, stat, sys, time
args = sys.argv[1:]
name = os.path.basename(args[-1])
null, fd0 = os.stat(os.devnull), os.fstat(0)
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({{
        "argv": args,
        "cwd": os.getcwd(),
        "stdin_devnull": stat.S_ISCHR(fd0.st_mode) and fd0.st_rdev == null.st_rdev,
    }}) + "\\n")
with open(os.environ["FAKE_PROBE"], encoding="utf-8") as f:
    entry = json.load(f).get(name, {{"exit": 1, "stdout": "{{}}"}})
time.sleep(entry.get("sleep", 0))
sys.stdout.write(entry.get("stdout", ""))
sys.exit(entry.get("exit", 0))
"""


def probe_entry(duration, streams=("video", "audio")):
    """The canned ffprobe answer of a clip with these stream kinds and this duration in seconds."""
    body = {"streams": [{"codec_type": kind} for kind in streams]}
    if duration is not None:
        body["format"] = {"duration": duration if isinstance(duration, str) else "%.6f" % duration}
    else:
        body["format"] = {}
    return {"stdout": json.dumps(body), "exit": 0}


def load_picker():
    import pick_background

    return pick_background


class PickerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pick-bg-test-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.app = self.tmp / "app"
        self.app.mkdir()
        self.clips = self.tmp / "clips"
        self.stage = self.app / "bg-stage"
        self.link = self.app / "public" / "bg"
        self.timeline = self.tmp / "timeline.json"
        self.write_timeline()
        self.fake = self.tmp / "remotion"
        self.fake.write_text(FAKE_REMOTION.format(python=sys.executable), encoding="utf-8")
        self.fake.chmod(self.fake.stat().st_mode | stat.S_IXUSR)
        self.fake_log = self.tmp / "fake.log"
        self.fake_probe = self.tmp / "probe.json"
        self.canned({})
        self.fake_env = {"FAKE_LOG": str(self.fake_log), "FAKE_PROBE": str(self.fake_probe)}

    def write_timeline(self, total_frames=FPS * VIDEO_SECONDS, **extra):
        data = {"format": "brainrot", "fps": FPS, "width": 1080, "height": 1920,
                "totalFrames": total_frames, "scenes": [{"id": "s1", "from": 0}]}
        data.update(extra)
        self.timeline.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def canned(self, mapping):
        self.fake_probe.write_text(json.dumps(mapping), encoding="utf-8")

    def clip(self, name, content=b"stub"):
        self.clips.mkdir(exist_ok=True)
        path = self.clips / name
        path.write_bytes(content)
        return path

    def argv(self, *extra, remotion=None, clips=None, timeline=None):
        return [str(timeline or self.timeline), str(remotion or self.fake), str(self.app),
                "--dir", str(self.clips if clips is None else clips), *extra]

    def run_picker(self, *extra, env=None, **kwargs):
        """The picker as a subprocess. stdin is an open pipe, so the fake can tell /dev/null from it."""
        full_env = {k: v for k, v in os.environ.items() if k != "EXPLAIN_BRAINROT_SEED"}
        full_env.update(self.fake_env)
        full_env.update(env or {})
        proc = subprocess.Popen(
            [sys.executable, "-B", str(PICKER), *self.argv(*extra, **kwargs)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=full_env,
        )
        out, err = proc.communicate(timeout=120)
        return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)

    def run_main(self, *extra, **kwargs):
        """main() in this process: (exit code, stdout lines)."""
        picker = load_picker()
        out = io.StringIO()
        with mock.patch.dict(os.environ, self.fake_env), contextlib.redirect_stdout(out):
            code = picker.main(self.argv(*extra, **kwargs))
        return code, out.getvalue().splitlines()

    def background(self):
        return json.loads(self.timeline.read_text(encoding="utf-8"))["background"]

    def json_number(self, key):
        """The text of a number inside the background object, as written in the file."""
        text = self.timeline.read_text(encoding="utf-8")
        found = re.search(r'"%s": (-?[0-9][0-9.eE+-]*)' % key, text.split('"background"')[1])
        self.assertIsNotNone(found, key)
        return found.group(1)

    def probe_calls(self):
        if not self.fake_log.exists():
            return []
        return [json.loads(line) for line in self.fake_log.read_text(encoding="utf-8").splitlines()]

    def assert_ok_run(self, run):
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stderr, "")
        return run.stdout.splitlines()

    def assert_link_to_stage(self):
        self.assertTrue(self.link.is_symlink(), "public/bg must be a symlink")
        self.assertEqual(os.readlink(self.link), str(self.stage))
        self.assertEqual(self.link.resolve(), self.stage.resolve())

    def assert_generated(self, run, lines=(GENERATED,)):
        self.assertEqual(self.assert_ok_run(run), list(lines))
        self.assertEqual(self.background(), {"kind": "generated"})
        self.assertEqual(list(self.stage.iterdir()), [])
        self.assert_link_to_stage()

    def assert_staged_regular(self, name, source):
        staged = self.stage / name
        self.assertTrue(staged.is_file() and not staged.is_symlink(), "bg-stage/%s must be a regular file" % name)
        self.assertEqual([p.name for p in self.stage.iterdir()], [name])
        self.assertTrue(os.path.samefile(staged, source), "%s is not the same file as %s" % (staged, source))
        return staged


class Generated(PickerCase):
    def test_missing_folder_is_generated(self):
        """Mutation: a missing folder fails the picker, or leaves the stage and link unmade."""
        run = self.run_picker(clips=self.tmp / "nonexistent")
        self.assert_generated(run)
        self.assertEqual(self.probe_calls(), [])

    def test_empty_folder_is_generated(self):
        """Mutation: an empty folder fails the picker, or writes no background key."""
        self.clips.mkdir()
        self.assert_generated(self.run_picker())

    def test_non_video_and_hidden_files_ignored(self):
        """Mutation: hidden files, directories or other extensions reach the probe (the fake would
        answer them with a SKIP line, and its log would show a call)."""
        self.clip("notes.txt")
        self.clip(".DS_Store")
        self.clip(".hidden.mp4")
        self.clip("clip.mp3")
        self.clip("clip.mp4.txt")
        (self.clips / "folder.mp4").mkdir()
        self.assert_generated(self.run_picker())
        self.assertEqual(self.probe_calls(), [])

    def test_corrupt_clip_skipped_real(self):
        """Mutation: a clip ffprobe cannot read is picked, or its SKIP line differs or is indented."""
        if not REAL_REMOTION.exists():
            self.skipTest(NO_REMOTION_REASON)
        self.clip("bad.mp4", b"not a video")
        run = self.run_picker(remotion=REAL_REMOTION)
        self.assert_generated(run, ("background: SKIP bad.mp4 (ffprobe exit 1)", GENERATED))

    def test_no_video_stream_skipped(self):
        """Mutation: an audio-only file is accepted, or a different cause text is printed."""
        self.clip("x.mp4")
        self.canned({"x.mp4": probe_entry(10, streams=("audio",))})
        run = self.run_picker()
        self.assert_generated(run, ("background: SKIP x.mp4 (no video stream)", GENERATED))

    def test_no_duration_skipped(self):
        """Mutation: a missing, N/A or zero duration is accepted as a clip length."""
        for name in ("a.mp4", "b.mp4", "c.mp4"):
            self.clip(name)
        self.canned({"a.mp4": probe_entry(None), "b.mp4": probe_entry("N/A"), "c.mp4": probe_entry("0.000000")})
        run = self.run_picker("--seed", "1")
        lines = self.assert_ok_run(run)
        self.assertEqual(sorted(lines[:-1]),
                         ["background: SKIP %s (no duration)" % n for n in ("a.mp4", "b.mp4", "c.mp4")])
        self.assertEqual(lines[-1], GENERATED)

    def test_unparseable_probe_skipped(self):
        """Mutation: probe output that is not JSON crashes the picker instead of skipping the clip."""
        self.clip("x.mp4")
        self.canned({"x.mp4": {"stdout": "not json", "exit": 0}})
        run = self.run_picker()
        self.assert_generated(run, ("background: SKIP x.mp4 (ffprobe output unreadable)", GENERATED))

    def test_probe_exit_code_in_skip(self):
        """Mutation: the SKIP cause drops the exit status of ffprobe."""
        self.clip("x.mp4")
        self.canned({"x.mp4": {"stdout": "", "exit": 3}})
        run = self.run_picker()
        self.assert_generated(run, ("background: SKIP x.mp4 (ffprobe exit 3)", GENERATED))

    def test_probe_timeout_skipped(self):
        """Mutation: a hung ffprobe hangs the picker, or the timeout is not handled."""
        picker = load_picker()
        self.clip("x.mp4")
        self.canned({"x.mp4": {"stdout": "{}", "exit": 0, "sleep": 20}})
        with mock.patch.object(picker, "PROBE_TIMEOUT", 0.3):
            code, lines = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(lines, ["background: SKIP x.mp4 (ffprobe timed out)", GENERATED])

    def test_skips_then_tries_next_in_seeded_order(self):
        """Mutation: the picker stops at the first bad clip, or the order is not sorted(names)
        shuffled by random.Random(seed), or a SKIP is printed for a clip it never probed."""
        names = ["bad1.mp4", "bad2.mp4", "good.mp4"]
        for name in names:
            self.clip(name)
        self.canned({"good.mp4": probe_entry(600)})
        skipped_somewhere = False
        for seed in range(1, 9):
            order = sorted(names)
            random.Random(seed).shuffle(order)
            expected = ["background: SKIP %s (ffprobe exit 1)" % n for n in order[:order.index("good.mp4")]]
            lines = self.assert_ok_run(self.run_picker("--seed", str(seed)))
            self.assertEqual(lines[:-1], expected, "seed %d" % seed)
            self.assertRegex(lines[-1], r"^background: ok good\.mp4 @\d+\.\d s$")
            skipped_somewhere = skipped_somewhere or bool(expected)
        self.assertTrue(skipped_somewhere, "no seed tried a bad clip first; the shuffle is not used")

    def test_unlistable_folder_is_generated_with_a_skip(self):
        """Mutation: a folder that exists but cannot be read is silent, or fails the picker."""
        if os.geteuid() == 0:
            self.skipTest("root can list any folder")
        self.clips.mkdir()
        self.clips.chmod(0)
        self.addCleanup(self.clips.chmod, 0o755)
        run = self.run_picker()
        lines = self.assert_ok_run(run)
        self.assertEqual(len(lines), 2, lines)
        self.assertRegex(lines[0], r"^background: SKIP .*clips \(cannot list: .+\)$")
        self.assertEqual(lines[1], GENERATED)


class Clip(PickerCase):
    def test_fixture_clip_loops_real(self):
        """Mutation: a clip shorter than the video is not marked loop, `seconds` is not the probed
        length, the stage line differs, the clip is staged as a symlink or a copy of another
        file, or public/bg does not lead to the stage."""
        if not REAL_REMOTION.exists():
            self.skipTest(NO_REMOTION_REASON)
        run = self.run_picker(remotion=REAL_REMOTION, clips=FIXTURES)
        self.assertEqual(self.assert_ok_run(run), ["background: ok bg-1s.mp4 @0.0 s (loop)"])
        self.assertEqual(self.background(), {
            "kind": "clip", "file": "bg-1s.mp4", "src": "bg/clip.mp4",
            "start": 0.0, "seconds": 1.0, "loop": True,
        })
        self.assert_staged_regular("clip.mp4", FIXTURE_CLIP)
        self.assert_link_to_stage()
        self.assertTrue((self.link / "clip.mp4").is_file())

    def test_long_clip_start_in_range(self):
        """Mutation: the start leaves [0, clip - video], is constant, or the long clip loops."""
        self.clip("long.mp4")
        self.canned({"long.mp4": probe_entry(600)})
        self.write_timeline(total_frames=FPS * 90)
        starts = set()
        for seed in range(1, 21):
            lines = self.assert_ok_run(self.run_picker("--seed", str(seed)))
            bg = self.background()
            self.assertLessEqual(0, bg["start"], seed)
            self.assertLessEqual(bg["start"], 510, seed)
            self.assertFalse(bg["loop"], seed)
            self.assertEqual(bg["seconds"], 600.0)
            self.assertEqual(lines, ["background: ok long.mp4 @%.1f s" % bg["start"]])
            self.assertLessEqual(len(self.json_number("start").partition(".")[2]), 3, seed)
            starts.add(bg["start"])
        self.assertGreater(len(starts), 10, "the start does not vary with the seed")

    def test_start_is_floored_to_three_places(self):
        """Mutation: the start is rounded to the nearest 3 places instead of down. The clip is
        10.0009 s for a 3 s video, so clip - video = 7.0009, and the RNG is made to return 7.00058,
        which rounds up to 7.001 and would put start + video past the clip end."""
        picker = load_picker()
        self.clip("x.mp4")
        self.canned({"x.mp4": probe_entry("10.000900")})
        drawn = 7.00058
        self.assertGreater(round(drawn, 3), 10.0009 - VIDEO_SECONDS)  # the case is the one that bites
        with mock.patch.object(picker.random.Random, "uniform", return_value=drawn):
            code, lines = self.run_main()
        self.assertEqual(code, 0, lines)
        bg = self.background()
        self.assertEqual(bg["start"], 7.0)
        self.assertLessEqual(bg["start"] + VIDEO_SECONDS, 10.0009)
        self.assertFalse(bg["loop"])

    def test_start_and_seconds_have_three_places(self):
        """Mutation: seconds or start is written with more than 3 decimals."""
        self.clip("x.mp4")
        self.canned({"x.mp4": probe_entry("600.123456")})
        self.assert_ok_run(self.run_picker("--seed", "9"))
        self.assertEqual(self.json_number("seconds"), "600.123")
        self.assertLessEqual(len(self.json_number("start").partition(".")[2]), 3)

    def test_equal_length_clip_no_loop(self):
        """Mutation: a clip exactly as long as the video loops or gets a start past 0, or a clip
        half a frame short (3.033333 s for 91 frames at 30 fps) is treated as shorter."""
        self.clip("x.mp4")
        for frames, duration in ((90, "3.000000"), (91, "3.033333")):
            self.write_timeline(total_frames=frames)
            self.canned({"x.mp4": probe_entry(duration)})
            lines = self.assert_ok_run(self.run_picker("--seed", "3"))
            self.assertEqual(lines, ["background: ok x.mp4 @0.0 s"])
            bg = self.background()
            self.assertEqual((bg["start"], bg["loop"]), (0.0, False), frames)

    def test_shorter_clip_loops_from_zero(self):
        """Mutation: a clip clearly shorter than the video (1 s against 3 s) is not looped."""
        self.clip("x.mp4")
        self.canned({"x.mp4": probe_entry(1)})
        lines = self.assert_ok_run(self.run_picker())
        self.assertEqual(lines, ["background: ok x.mp4 @0.0 s (loop)"])
        bg = self.background()
        self.assertEqual((bg["start"], bg["seconds"], bg["loop"]), (0.0, 1.0, True))

    def test_name_with_spaces_and_case(self):
        """Mutation: the original name is lost (stage line or `file`), or src carries the
        original name or extension case instead of bg/clip.mp4."""
        source = self.clip("My Run 4K.MP4", b"some bytes")
        self.canned({"My Run 4K.MP4": probe_entry(600)})
        lines = self.assert_ok_run(self.run_picker("--seed", "2"))
        self.assertRegex(lines[0], r"^background: ok My Run 4K\.MP4 @\d+\.\d s$")
        bg = self.background()
        self.assertEqual((bg["file"], bg["src"]), ("My Run 4K.MP4", "bg/clip.mp4"))
        self.assert_staged_regular("clip.mp4", source)
        self.assertEqual((self.link / "clip.mp4").read_bytes(), b"some bytes")

    def test_extension_lowercased_in_stage_and_src(self):
        """Mutation: the extension keeps its case, or .mov/.webm are not accepted."""
        for name, staged in (("A.MOV", "clip.mov"), ("b.WebM", "clip.webm"), ("c.mp4", "clip.mp4")):
            with self.subTest(name=name):
                shutil.rmtree(self.clips, ignore_errors=True)
                self.clip(name)
                self.canned({name: probe_entry(600)})
                self.assert_ok_run(self.run_picker())
                self.assertEqual(self.background()["src"], "bg/" + staged)
                self.assertEqual([p.name for p in self.stage.iterdir()], [staged])

    def test_symlinked_clip_resolves(self):
        """Mutation: a symlink in the folder is staged as a symlink, or as the link, not its target."""
        real = self.tmp / "real.mp4"
        real.write_bytes(b"real bytes")
        self.clips.mkdir()
        (self.clips / "link.mp4").symlink_to("../real.mp4")
        self.canned({"link.mp4": probe_entry(600)})
        self.assert_ok_run(self.run_picker())
        self.assertEqual(self.background()["file"], "link.mp4")
        self.assert_staged_regular("clip.mp4", real)
        self.assertEqual((self.link / "clip.mp4").read_bytes(), b"real bytes")

    def test_probe_command_and_cwd(self):
        """Mutation: the probe argv differs from the contract, runs outside <app>, gets the stored
        relative path, or inherits stdin."""
        source = self.clip("x.mp4")
        self.canned({"x.mp4": probe_entry(600)})
        self.assert_ok_run(self.run_picker())
        calls = self.probe_calls()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["argv"], [
            "ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration",
            "-of", "json", str(source),
        ])
        self.assertEqual(os.path.realpath(calls[0]["cwd"]), str(self.app.resolve()))
        self.assertTrue(calls[0]["stdin_devnull"])


class Seed(PickerCase):
    def two_clips(self):
        for name in ("a.mp4", "b.mp4"):
            self.clip(name)
        self.canned({"a.mp4": probe_entry(600), "b.mp4": probe_entry(600)})

    def test_seed_is_deterministic(self):
        """Mutation: the seed is ignored (the same seed gives different choices)."""
        self.two_clips()
        for seed in ("1", "2", "3"):
            self.assert_ok_run(self.run_picker("--seed", seed))
            first = self.background()
            self.assert_ok_run(self.run_picker("--seed", seed))
            self.assertEqual(self.background(), first, seed)

    def test_seeds_reach_every_clip(self):
        """Mutation: the order is always sorted (the first clip always wins)."""
        self.two_clips()
        chosen = set()
        for seed in range(1, 13):
            self.assert_ok_run(self.run_picker("--seed", str(seed)))
            chosen.add(self.background()["file"])
        self.assertEqual(chosen, {"a.mp4", "b.mp4"})

    def test_env_seed_is_used_and_flag_wins(self):
        """Mutation: EXPLAIN_BRAINROT_SEED is ignored, or beats --seed."""
        self.two_clips()
        self.assert_ok_run(self.run_picker("--seed", "4"))
        want = self.background()
        for seed in range(5, 30):  # a different seed that gives a different answer
            self.assert_ok_run(self.run_picker("--seed", str(seed)))
            if self.background() != want:
                other = str(seed)
                break
        else:
            self.fail("no other seed changed the choice")
        self.assert_ok_run(self.run_picker(env={"EXPLAIN_BRAINROT_SEED": "4"}))
        self.assertEqual(self.background(), want)
        self.assert_ok_run(self.run_picker("--seed", "4", env={"EXPLAIN_BRAINROT_SEED": other}))
        self.assertEqual(self.background(), want)

    def test_bad_env_seed_is_a_usage_error(self):
        """Mutation: a non-integer EXPLAIN_BRAINROT_SEED crashes with a traceback."""
        run = self.run_picker(env={"EXPLAIN_BRAINROT_SEED": "abc"})
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertIn("EXPLAIN_BRAINROT_SEED", run.stderr)
        self.assertNotIn("Traceback", run.stderr)


class Staging(PickerCase):
    def test_stale_stage_removed(self):
        """Mutation: an old file in bg-stage or an old real directory at public/bg survives, or
        the old layout (a real public/bg holding links to a user's clip and folder) is emptied
        through those links."""
        user = self.tmp / "userclips"
        user.mkdir()
        (user / "mine.mp4").write_bytes(b"user clip")
        self.stage.mkdir()
        (self.stage / "old.webm").write_bytes(b"old")
        (self.stage / "dir").mkdir()
        (self.stage / "dir" / "inner.txt").write_text("x", encoding="utf-8")
        self.link.mkdir(parents=True)
        (self.link / "old.webm").write_bytes(b"old")
        (self.link / "mine.mp4").symlink_to(user / "mine.mp4")
        (self.link / "folder").symlink_to(user)
        self.assert_generated(self.run_picker())
        self.assertFalse((self.link / "old.webm").exists())
        self.assertEqual((user / "mine.mp4").read_bytes(), b"user clip")
        self.assertEqual([p.name for p in user.iterdir()], ["mine.mp4"])

    def test_link_replaces_file_and_stale_symlink(self):
        """Mutation: public/bg as a file or a link to somewhere else is left in place, or the
        picker follows the stale link and empties its target."""
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "keep.txt").write_text("keep", encoding="utf-8")
        (self.app / "public").mkdir()
        for make in (lambda: self.link.write_bytes(b"a file"), lambda: self.link.symlink_to(elsewhere)):
            self.link.unlink(missing_ok=True)
            make()
            self.assert_generated(self.run_picker())
        self.assertEqual((elsewhere / "keep.txt").read_text(encoding="utf-8"), "keep")

    def test_stage_that_is_a_symlink_is_replaced_not_emptied(self):
        """Mutation: bg-stage as a link to a user folder is emptied through the link."""
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "keep.txt").write_text("keep", encoding="utf-8")
        self.stage.symlink_to(elsewhere)
        self.assert_generated(self.run_picker())
        self.assertFalse(self.stage.is_symlink())
        self.assertEqual((elsewhere / "keep.txt").read_text(encoding="utf-8"), "keep")

    def test_generated_run_clears_the_previous_clip(self):
        """Mutation: a clip run followed by a generated run leaves the old clip staged, or clearing
        the stage removes the user's own clip (the staged file is a hard link to it)."""
        source = self.clip("x.mp4", b"original bytes")
        self.canned({"x.mp4": probe_entry(600)})
        self.assert_ok_run(self.run_picker())
        self.assertTrue((self.stage / "clip.mp4").exists())
        self.assert_generated(self.run_picker(clips=self.tmp / "nonexistent"))
        self.assertEqual(source.read_bytes(), b"original bytes")

    def test_copy_fallback_when_link_fails(self):
        """Mutation: a failing os.link is fatal, or the fallback stages a symlink or nothing."""
        picker = load_picker()
        source = self.clip("x.mp4", b"clip bytes")
        self.stage.mkdir()
        with mock.patch.object(picker.os, "link", side_effect=OSError("cross-device")):
            staged = Path(picker.stage_clip(str(source), str(self.app)))
        self.assertEqual(staged, self.stage / "clip.mp4")
        self.assertTrue(staged.is_file() and not staged.is_symlink())
        self.assertEqual(staged.read_bytes(), b"clip bytes")
        self.assertFalse(os.path.samefile(staged, source))

    def test_failed_copy_leaves_no_partial_file(self):
        """Mutation: a copy that fails after writing some bytes leaves a partial clip.* in bg-stage."""
        picker = load_picker()
        source = self.clip("x.mp4", b"clip bytes")
        self.stage.mkdir()

        def partial_copy(src, dst):
            Path(dst).write_bytes(b"part")
            raise OSError("disk full")

        with mock.patch.object(picker.os, "link", side_effect=OSError("cross-device")), \
                mock.patch.object(picker.shutil, "copyfile", side_effect=partial_copy):
            with self.assertRaises(OSError):
                picker.stage_clip(str(source), str(self.app))
        self.assertEqual(list(self.stage.iterdir()), [])

    def test_stage_failure_is_a_fail_line(self):
        """Mutation: when both link and copy fail the picker continues, or prints another text."""
        picker = load_picker()
        self.clip("x.mp4")
        self.canned({"x.mp4": probe_entry(600)})
        with mock.patch.object(picker.os, "link", side_effect=OSError("no link")), \
                mock.patch.object(picker.shutil, "copyfile", side_effect=OSError("disk full")):
            code, lines = self.run_main()
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["background: FAIL cannot stage x.mp4: disk full"])
        self.assertNotIn("background", json.loads(self.timeline.read_text(encoding="utf-8")))
        self.assertEqual(list(self.stage.iterdir()), [])


class InsideApp(PickerCase):
    """--dir under <app>/bg-stage or <app>/public is a misconfiguration, not a missing folder: the
    picker empties the stage and public/bg, so it must refuse before touching anything."""

    def seed_stage(self):
        """A stage that holds a clip and a folder of clips, and a public dir with a wav."""
        self.stage.mkdir()
        (self.stage / "mine.mp4").write_bytes(b"stage clip")
        (self.stage / "sub").mkdir()
        (self.stage / "sub" / "deep.mp4").write_bytes(b"deep clip")
        (self.app / "public" / "audio").mkdir(parents=True)
        (self.app / "public" / "audio" / "s1.wav").write_bytes(b"wav")
        self.canned({"mine.mp4": probe_entry(600), "deep.mp4": probe_entry(600)})
        self.before = self.timeline.read_text(encoding="utf-8")

    def assert_refused(self, run, folder):
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertEqual(run.stdout, "background: FAIL --dir %s is inside the app workspace\n" % folder)
        self.assertEqual((self.stage / "mine.mp4").read_bytes(), b"stage clip")
        self.assertEqual((self.stage / "sub" / "deep.mp4").read_bytes(), b"deep clip")
        self.assertEqual((self.app / "public" / "audio" / "s1.wav").read_bytes(), b"wav")
        self.assertFalse(self.link.exists() or self.link.is_symlink(), "public/bg was made")
        self.assertEqual(self.timeline.read_text(encoding="utf-8"), self.before)
        self.assertEqual(self.probe_calls(), [])

    def test_dir_inside_the_app_is_refused_and_nothing_is_deleted(self):
        """Mutation: no guard, so --dir <app>/bg-stage is emptied first and the run ends "ok generated"."""
        self.seed_stage()
        via_link = self.tmp / "via-link"
        via_link.symlink_to(self.stage)
        (self.app / "x").mkdir()
        folders = {
            "the stage": self.stage,
            "a folder under the stage": self.stage / "sub",
            "a missing folder under the stage": self.stage / "not-made-yet",
            "public": self.app / "public",
            "a folder under public": self.app / "public" / "audio",
            "a symlink to the stage": via_link,
            "a dotted path to the stage": self.app / "x" / ".." / "bg-stage",
        }
        for label, folder in folders.items():
            with self.subTest(label):
                self.assert_refused(self.run_picker(clips=folder), folder)

    def test_dir_with_other_case_is_refused_on_a_case_insensitive_volume(self):
        """Mutation: the guard compares path strings only, so BG-STAGE gets past it on APFS."""
        self.seed_stage()
        shouting = self.app / "BG-STAGE"
        if not shouting.exists():
            self.skipTest("this volume is case-sensitive")
        self.assert_refused(self.run_picker(clips=shouting), shouting)

    def test_folders_next_to_the_stage_are_not_refused(self):
        """Mutation: the guard is a string prefix test, so bg-stage-extra and publicity count as inside."""
        for name in ("bg-stage-extra", "publicity"):
            with self.subTest(name):
                folder = self.app / name
                folder.mkdir()
                (folder / "x.mp4").write_bytes(b"clip")
                self.canned({"x.mp4": probe_entry(600)})
                lines = self.assert_ok_run(self.run_picker("--seed", "1", clips=folder))
                self.assertRegex(lines[0], r"^background: ok x\.mp4 @")
                self.assertEqual((folder / "x.mp4").read_bytes(), b"clip")

    def test_the_app_itself_is_not_refused(self):
        """Mutation: --dir <app> (its top level holds no clip) is refused as inside the workspace."""
        self.assert_generated(self.run_picker(clips=self.app))


class Timeline(PickerCase):
    def test_rewrite_keeps_keys_and_replaces_background(self):
        """Mutation: other keys are dropped or reordered, the file is not indent 2 plus a newline,
        or an old background survives."""
        self.write_timeline(maxSceneSeconds=45, background={"kind": "clip", "file": "old.mp4"})
        before = json.loads(self.timeline.read_text(encoding="utf-8"))
        self.assert_generated(self.run_picker(clips=self.tmp / "nonexistent"))
        after = json.loads(self.timeline.read_text(encoding="utf-8"))
        self.assertEqual({k: v for k, v in after.items() if k != "background"},
                         {k: v for k, v in before.items() if k != "background"})
        self.assertEqual(list(after), list(before))
        self.assertEqual(self.timeline.read_text(encoding="utf-8"), json.dumps(after, indent=2) + "\n")

    def test_unreadable_timeline_fails(self):
        """Mutation: a missing, malformed or key-less timeline is a traceback or exit 0."""
        cases = {
            "missing": None,
            "malformed": "{not json",
            "no fps": json.dumps({"totalFrames": 90}),
            "no totalFrames": json.dumps({"fps": 30}),
            "zero fps": json.dumps({"fps": 0, "totalFrames": 90}),
            "text frames": json.dumps({"fps": 30, "totalFrames": "90"}),
        }
        for label, text in cases.items():
            with self.subTest(label):
                path = self.tmp / ("tl-%s.json" % label.replace(" ", "-"))
                if text is not None:
                    path.write_text(text, encoding="utf-8")
                run = self.run_picker(timeline=path)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertRegex(run.stdout, r"^background: FAIL cannot read %s: .+\n$" % re.escape(str(path)))
                self.assertNotIn("Traceback", run.stderr)

    def test_unwritable_timeline_fails(self):
        """Mutation: a timeline that cannot be written is reported as success."""
        if os.geteuid() == 0:
            self.skipTest("root can write anywhere")
        sealed = self.tmp / "sealed"
        sealed.mkdir()
        path = sealed / "timeline.json"
        path.write_text(self.timeline.read_text(encoding="utf-8"), encoding="utf-8")
        sealed.chmod(0o555)
        self.addCleanup(sealed.chmod, 0o755)
        run = self.run_picker(timeline=path, clips=self.tmp / "nonexistent")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertRegex(run.stdout, r"^background: FAIL cannot write %s: .+\n$" % re.escape(str(path)))
        self.assertNotIn("background", json.loads(path.read_text(encoding="utf-8")))


class Usage(PickerCase):
    def test_usage_errors_exit_2(self):
        """Mutation: a missing argument or an unknown flag exits 1 or 0, or without a usage line."""
        for label, args in (
            ("no arguments", []),
            ("no --dir", [str(self.timeline), str(self.fake), str(self.app)]),
            ("missing app dir", [str(self.timeline), str(self.fake), "--dir", str(self.clips)]),
            ("unknown flag", self.argv() + ["--bogus"]),
            ("seed not an integer", self.argv("--seed", "x")),
        ):
            with self.subTest(label):
                run = subprocess.run([sys.executable, "-B", str(PICKER), *args],
                                     capture_output=True, text=True, stdin=subprocess.DEVNULL)
                self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
                self.assertIn("usage", run.stderr.lower())
                self.assertEqual(run.stdout, "")


if __name__ == "__main__":
    unittest.main()
