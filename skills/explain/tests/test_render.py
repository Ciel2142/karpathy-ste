"""Tests for scripts/render.sh: the nine-stage video pipeline.

The stage-1 tests need no workspace: they fail before any tool that needs one runs. A fake
npm that exits 1 sits first on PATH and the workspace is an empty temp dir, so a mutant that
gets past stage 1 fails fast instead of installing. The end-to-end class renders the
three-scene fixture once (tests/video_e2e.py) and needs EXPLAIN_VIDEO_E2E=1. Each test names
the mutation that turns it red."""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from video_e2e import E2E, E2E_REASON, EXPLAIN, RENDER_SH, TEMPLATE, render_fixture

STAGES = ("script", "workspace", "narration", "timeline", "render",
          "container", "sync", "stills", "transcript")
STAGE_LINE = re.compile(r"^(%s)\b" % "|".join(STAGES))


def stage_lines(stdout):
    return [line for line in stdout.splitlines() if STAGE_LINE.match(line)]


class StageOneCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="render-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.out = self.tmp / "out"
        self.out.mkdir()
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        npm = bin_dir / "npm"
        npm.write_text("#!/bin/sh\necho 'fake npm: no install in a stage-1 test' >&2\nexit 1\n",
                       encoding="utf-8")
        npm.chmod(npm.stat().st_mode | stat.S_IXUSR)
        self.env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}",
                        EXPLAIN_VIDEO_WORKSPACE=str(self.tmp / "ws"))

    def write_script(self, edit=None, root=None):
        script = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        script["provenance"]["root"] = str(EXPLAIN) if root is None else root
        if edit:
            edit(script)
        (self.out / "script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

    def render(self):
        return subprocess.run(
            ["/bin/bash", str(RENDER_SH), str(self.out), "--engine", "say"],
            capture_output=True, text=True, env=self.env, timeout=300,
        )

    # red: a missing script.json exits 1
    def test_missing_script_json_exit_2(self):
        run = self.render()
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertEqual(run.stdout, "")
        self.assertEqual(len(run.stderr.splitlines()), 1, run.stderr)

    # red: no JSON parse before stage 1 (the parse error surfaces later, exit 1)
    def test_invalid_json_exit_2(self):
        (self.out / "script.json").write_text('{"title": ', encoding="utf-8")
        run = self.render()
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertEqual(run.stdout, "")
        self.assertEqual(len(run.stderr.splitlines()), 1, run.stderr)

    # red: the absolute-path check dropped
    def test_relative_root_fails_at_script_stage(self):
        self.write_script(root="skills/explain")
        run = self.render()
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertEqual(stage_lines(run.stdout),
                         ["script: FAIL provenance.root must be an absolute path"])

    # red: narration before validation
    def test_bad_cue_fails_at_script_stage(self):
        def edit(script):
            script["scenes"][1]["props"]["bullets"][1]["cue"] = "loads the page"
        self.write_script(edit)
        run = self.render()
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        lines = stage_lines(run.stdout)
        self.assertEqual(len(lines), 1, run.stdout)
        self.assertTrue(lines[0].startswith("script: FAIL "), lines)
        self.assertIn('cue "loads the page" is not at a sentence start', lines[0])
        self.assertFalse((self.out / "audio" / "durations.json").exists())

    # red: verify.sh not run at the script stage
    def test_prose_error_fails_at_script_stage(self):
        def edit(script):
            script["scenes"][0]["narration"] = (
                "This video explains the check script. The script doesn't skip a check. "
                "It runs them before handoff.")
        self.write_script(edit)
        run = self.render()
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        lines = stage_lines(run.stdout)
        self.assertEqual(len(lines), 1, run.stdout)
        self.assertTrue(lines[0].startswith("script: FAIL prose: FAIL "), lines)
        self.assertIn("\n  prose: FAIL 1 error(s)\n", run.stdout)
        self.assertIn('contraction "doesn\'t"', run.stdout)

    def place_stale(self):
        (self.out / "video.mp4").write_bytes(b"old video")
        (self.out / "review").mkdir()
        (self.out / "review" / "still-01-old.png").write_bytes(b"old still")

    # red: the stale video and stills removed before stage 1 (a failed script stage then
    # destroys the last good render)
    def test_stale_artifacts_survive_a_script_fail(self):
        self.write_script(root="skills/explain")
        self.place_stale()
        run = self.render()
        self.assertEqual(stage_lines(run.stdout),
                         ["script: FAIL provenance.root must be an absolute path"])
        self.assertTrue((self.out / "video.mp4").exists())
        self.assertTrue((self.out / "review" / "still-01-old.png").exists())

    # red: no removal after stage 1 (the old video and stills sit next to the new transcript)
    def test_stale_artifacts_removed_once_the_script_stage_passes(self):
        self.write_script()
        self.place_stale()
        run = self.render()
        lines = stage_lines(run.stdout)
        self.assertEqual(lines[0], "script: ok (5 scenes)", run.stdout)
        self.assertTrue(lines[1].startswith("workspace: FAIL "), run.stdout)
        self.assertFalse((self.out / "video.mp4").exists())
        self.assertEqual(list((self.out / "review").iterdir()), [])


def narrator_text(used, fallback):
    """Run the narrator_text function of render.sh on its own."""
    source = RENDER_SH.read_text(encoding="utf-8")
    match = re.search(r"^narrator_text\(\) \{\n.*?^\}\n", source, re.M | re.S)
    assert match, "no narrator_text() in render.sh"
    run = subprocess.run(["/bin/bash", "-c", match.group(0) + 'narrator_text "$1" "$2"', "-", used, fallback],
                         capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    return run.stdout


class NarratorTextCase(unittest.TestCase):
    # red: the Narrator row without the Kokoro voice ("kokoro")
    def test_kokoro_row_names_the_voice(self):
        self.assertEqual(narrator_text("kokoro", ""), "kokoro (af_heart)\n")

    # red: the voice added to every engine ("say (af_heart)")
    def test_say_row_is_say(self):
        self.assertEqual(narrator_text("say", ""), "say\n")

    # red: the fallback cause dropped from the row
    def test_fallback_row_names_the_cause(self):
        self.assertEqual(narrator_text("say", "no models"), "say (fallback: no models)\n")


ORDER = [
    r"script: ok \(3 scenes\)",
    r"workspace: ok /.+",
    r"narration \(say\): ok",
    r"timeline \(3 scenes, \d+\.\d s\): ok",
    r"render \(\d+\.\d s, \d+\.\d\d render-min/video-min\)( \(limit 2\.0\))?: ok",
    r"container: ok \(\d+\.\d\d s\)",
    r"sync: ok",
    r"stills \(\d+\): ok /.+",
    r"transcript: ok",
]


@unittest.skipUnless(E2E, E2E_REASON)
class SayFixtureCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out, cls.result = render_fixture()

    # red: the render stage line without its ratio
    def test_say_fixture_prints_nine_ok_lines_and_ratio(self):
        self.assertEqual(self.result.returncode, 0, self.result.stdout + self.result.stderr)
        lines = stage_lines(self.result.stdout)
        self.assertEqual(len(lines), 9, self.result.stdout)
        for line, pattern in zip(lines, ORDER):
            self.assertRegex(line, "^%s$" % pattern)
        self.assertIn("render-min/video-min", lines[4])

    # red: the transcript stage without --narrator (the row keeps "pending")
    def test_transcript_narrator_row_says_say(self):
        page = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertIn("<dt>Narrator</dt><dd>say</dd>", page)

    # red: the stills written somewhere other than review/
    def test_outputs_present(self):
        for name in ("video.mp4", "index.html", "narration.md", "build/timeline.json"):
            self.assertTrue((self.out / name).is_file(), name)
        self.assertTrue(list((self.out / "review").glob("still-01-*.png")))


if __name__ == "__main__":
    unittest.main()
