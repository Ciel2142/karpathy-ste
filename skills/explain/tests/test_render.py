"""Tests for scripts/render.sh: the nine-stage video pipeline (ten stages for a brainrot script).

StageFunctionCase runs stage_narration and stage_background of render.sh against fake tools (the
format -> --speed mapping, the picker's lines, exit codes and stderr). The stage-1 tests need no
workspace: they fail before any tool that needs one runs. A fake
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

# "background" is the tenth, brainrot-only stage; the explainer run must print no such line.
STAGES = ("script", "workspace", "narration", "timeline", "background", "render",
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


def render_functions(names):
    """The shell text of the named top-level functions of render.sh, plus its MARK and
    BRAINROT_SPEED constants, to run them without a render."""
    source = RENDER_SH.read_text(encoding="utf-8")
    parts = [re.search(r"^MARK=.*\n", source, re.M).group(0),
             re.search(r"^BRAINROT_SPEED=\S+.*\n", source, re.M).group(0)]
    for name in names:
        match = re.search(r"^%s\(\) \{\n.*?^\}\n" % name, source, re.M | re.S)
        assert match, "no %s() in render.sh" % name
        parts.append(match.group(0))
    return "".join(parts)


class StageFunctionCase(unittest.TestCase):
    """stage_narration and stage_background of render.sh, run against fake tools: no workspace,
    no render."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="render-stage-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "out" / "build").mkdir(parents=True)
        (self.tmp / "out" / "audio").mkdir()
        (self.tmp / "video").mkdir()
        (self.tmp / "scripts").mkdir()
        self.calls = self.tmp / "calls.txt"

    def fake(self, path, body):
        path.write_text("#!/bin/bash\n" + body, encoding="utf-8")
        path.chmod(0o755)

    def run_stage(self, stage, fmt, env=None):
        """Run `stage` of render.sh with format `fmt`; every fake tool appends its argv to calls."""
        functions = render_functions(["fail", "stream", stage])
        script = (
            "set -eu\n" + functions +
            'out=%(t)s/out video=%(t)s/video scripts=%(t)s/scripts script=%(t)s/out/script.json\n'
            'ws=%(t)s/ws app=%(t)s/ws/app remotion=%(t)s/ws/app/remote-cli engine=say fmt=%(fmt)s\n'
            '%(stage)s\n' % {"t": self.tmp, "fmt": fmt, "stage": stage})
        run_env = {k: v for k, v in os.environ.items()
                   if k not in ("EXPLAIN_BRAINROT_BACKGROUNDS", "EXPLAIN_BRAINROT_SEED")}
        run_env.update(env or {})
        return subprocess.run(["/bin/bash", "-c", script], capture_output=True, text=True,
                              env=run_env, timeout=60)

    def fake_picker(self, body):
        """A pick_background.py (render.sh runs it through python3) that logs its argv, then runs
        the Python text `body`."""
        (self.tmp / "video" / "pick_background.py").write_text(
            "import sys\nwith open(%r, 'a') as log:\n    log.write(' '.join(sys.argv[1:]) + '\\n')\n%s"
            % (str(self.calls), body), encoding="utf-8")

    def call_lines(self):
        return self.calls.read_text(encoding="utf-8").splitlines()

    # red: a brainrot run narrates without --speed, or the speed is not 1.2
    def test_brainrot_narration_gets_speed_1_2(self):
        self.fake(self.tmp / "scripts" / "narrate.sh",
                  'printf "%s\\n" "$*" >> ' + str(self.calls) + '\n'
                  'echo \'{"engine": "say"}\' > "$2/durations.json"\n')
        run = self.run_stage("stage_narration", "brainrot")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(self.call_lines(),
                         ["%s/out/script.json %s/out/audio --engine say --speed 1.2" % (self.tmp, self.tmp)])
        self.assertEqual(run.stdout, "narration (say): ok\n")

    # red: the explainer command line gains --speed (its audio cache would miss)
    def test_explainer_narration_has_no_speed(self):
        self.fake(self.tmp / "scripts" / "narrate.sh",
                  'printf "%s\\n" "$*" >> ' + str(self.calls) + '\n'
                  'echo \'{"engine": "say"}\' > "$2/durations.json"\n')
        run = self.run_stage("stage_narration", "explainer")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(self.call_lines(),
                         ["%s/out/script.json %s/out/audio --engine say" % (self.tmp, self.tmp)])

    # red: the explainer runs the picker or prints a background line
    def test_explainer_runs_no_background_stage(self):
        self.fake_picker('print("background: ok generated")\n')
        run = self.run_stage("stage_background", "explainer")
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "", ""))
        self.assertFalse(self.calls.exists())

    # red: SKIP lines unindented, or the held ok line indented or printed before them
    def test_brainrot_skip_lines_indented_then_ok_line(self):
        self.fake_picker('print("background: SKIP a.mp4 (no duration)")\n'
                         'print("background: ok b.mp4 @1.5 s (loop)")\n')
        run = self.run_stage("stage_background", "brainrot")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stdout,
                         "  background: SKIP a.mp4 (no duration)\nbackground: ok b.mp4 @1.5 s (loop)\n")

    # red: the picker gets another argument order, a seed, or a folder other than <ws>/backgrounds
    def test_picker_arguments_and_default_folder(self):
        self.fake_picker('print("background: ok generated")\n')
        run = self.run_stage("stage_background", "brainrot")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stdout, "background: ok generated\n")
        self.assertEqual(self.call_lines(),
                         ["%(t)s/out/build/timeline.json %(t)s/ws/app/remote-cli %(t)s/ws/app "
                          "--dir %(t)s/ws/backgrounds" % {"t": self.tmp}])

    # red: EXPLAIN_BRAINROT_BACKGROUNDS ignored
    def test_picker_folder_from_env(self):
        self.fake_picker('print("background: ok generated")\n')
        run = self.run_stage("stage_background", "brainrot",
                             env={"EXPLAIN_BRAINROT_BACKGROUNDS": "/clips/my folder"})
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue(self.call_lines()[0].endswith(" --dir /clips/my folder"), self.call_lines())

    # red: the picker's own FAIL line replaced by a generic one, or printed indented
    def test_picker_fail_line_stops_the_run(self):
        self.fake_picker('print("background: FAIL cannot read t.json")\nsys.exit(1)\n')
        run = self.run_stage("stage_background", "brainrot")
        self.assertEqual((run.returncode, run.stdout), (1, "background: FAIL cannot read t.json\n"))

    # red: exit 2 with only a stderr line gives no FAIL line, or the stderr line vanishes
    def test_picker_usage_error_reaches_the_user_and_fails(self):
        self.fake_picker('print("pick_background.py: EXPLAIN_BRAINROT_SEED must be an integer, '
                         "got 'abc'\", file=sys.stderr)\nsys.exit(2)\n")
        run = self.run_stage("stage_background", "brainrot")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertEqual(run.stdout,
                         "  pick_background.py: EXPLAIN_BRAINROT_SEED must be an integer, got 'abc'\n"
                         "background: FAIL pick_background.py exit 2\n")

    # red: an exit 0 picker without an ok line passes as a background
    def test_picker_without_result_line_fails(self):
        self.fake_picker("pass\n")
        run = self.run_stage("stage_background", "brainrot")
        self.assertEqual((run.returncode, run.stdout),
                         (1, "background: FAIL pick_background.py printed no result\n"))


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
