"""Tests for scripts/render.sh: the nine-stage video pipeline (ten stages for a brainrot script).

StageFunctionCase runs stage_narration, stage_background and stage_transcript of render.sh against
fake tools (the format -> --speed mapping, the picker's lines, exit codes and stderr, the
--background text of the transcript). The stage-1 tests need no
workspace: they fail before any tool that needs one runs. A fake
npm that exits 1 sits first on PATH and the workspace is an empty temp dir, so a mutant that
gets past stage 1 fails fast instead of installing. BrainrotRouteCase checks the user-facing
brainrot route: the template, SKILL.md, the rung file, and the format that stage_script reads
from a real script.json. The end-to-end class renders the
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

BRAINROT_TEMPLATE = EXPLAIN / "templates" / "brainrot-script.json"
BUILD_TIMELINE = EXPLAIN / "video" / "build-timeline.mjs"
STE_LINT = EXPLAIN.parent / "ste" / "scripts" / "ste_lint.py"
SKILL_MD = EXPLAIN / "SKILL.md"
BRAINROT_RUNG = EXPLAIN / "rungs" / "brainrot.md"

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

    def write_script(self, edit=None, root=None, template=TEMPLATE):
        script = json.loads(template.read_text(encoding="utf-8"))
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

    # red: the brainrot template breaks a brainrot limit or a cue rule, so the script stage fails
    # before the workspace stage runs
    def test_brainrot_template_passes_stage_one(self):
        self.write_script(template=BRAINROT_TEMPLATE)
        run = self.render()
        lines = stage_lines(run.stdout)
        self.assertEqual(lines[0], "script: ok (4 scenes)", run.stdout + run.stderr)
        self.assertTrue(lines[1].startswith("workspace: FAIL "), run.stdout)

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
    """stage_narration, stage_background and stage_transcript of render.sh, run against fake
    tools: no workspace, no render."""

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

    def run_stage(self, stage, fmt, env=None, helpers=("fail", "stream"), setup=""):
        """Run `stage` of render.sh with format `fmt`, after the shell text `setup`; every fake
        tool appends its argv to calls. `helpers` are the other functions the stage calls."""
        functions = render_functions([*helpers, stage])
        script = (
            "set -eu\n" + functions +
            'out=%(t)s/out video=%(t)s/video scripts=%(t)s/scripts script=%(t)s/out/script.json\n'
            'ws=%(t)s/ws app=%(t)s/ws/app remotion=%(t)s/ws/app/remote-cli engine=say fmt=%(fmt)s\n'
            '%(setup)s\n%(stage)s\n' % {"t": self.tmp, "fmt": fmt, "stage": stage, "setup": setup})
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

    TRANSCRIPT_HELPERS = ("fail", "first_cause", "run_tool", "narrator_text", "background_text")

    def fake_transcript_tools(self):
        """A transcript.py that logs its argv as one JSON list a line, and a passing verify.sh."""
        (self.tmp / "video" / "transcript.py").write_text(
            "import json, sys\nwith open(%r, 'a') as log:\n    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            % str(self.calls), encoding="utf-8")
        self.fake(self.tmp / "scripts" / "verify.sh", "exit 0\n")

    def run_transcript(self, fmt, background=None, raw=None):
        """stage_transcript for `fmt`, with `background` in build/timeline.json (or the file
        text `raw`); returns (run, the argv lists transcript.py was called with)."""
        self.fake_transcript_tools()
        timeline = self.tmp / "out" / "build" / "timeline.json"
        if raw is not None:
            timeline.write_text(raw, encoding="utf-8")
        else:
            body = {"format": fmt}
            if background is not None:
                body["background"] = background
            timeline.write_text(json.dumps(body), encoding="utf-8")
        run = self.run_stage("stage_transcript", fmt, helpers=self.TRANSCRIPT_HELPERS,
                             setup="used=say fallback=")
        calls = []
        if self.calls.exists():
            calls = [json.loads(line) for line in self.calls.read_text(encoding="utf-8").splitlines()]
        return run, calls

    def transcript_args(self, *background):
        return ["%s/out/script.json" % self.tmp, "%s/out" % self.tmp, "--narrator", "say", *background]

    # red: a brainrot run passes no --background, or a text other than "<file> @ <start %.1f> s"
    # plus " (loop)" for a looping clip (the space after @ is the spec's; the stage line has none)
    def test_brainrot_transcript_gets_the_clip_background_with_loop(self):
        clip = {"kind": "clip", "file": "My Run & 4K.MP4", "src": "bg/clip.mp4", "start": 12.345,
                "seconds": 40.0, "loop": True}
        run, calls = self.run_transcript("brainrot", clip)
        self.assertEqual((run.returncode, run.stdout), (0, "transcript: ok\n"), run.stderr)
        self.assertEqual(calls, [self.transcript_args("--background", "My Run & 4K.MP4 @ 12.3 s (loop)")])

    # red: " (loop)" written for a clip that does not loop
    def test_brainrot_transcript_clip_without_loop_has_no_suffix(self):
        clip = {"kind": "clip", "file": "bg-1s.mp4", "src": "bg/clip.mp4", "start": 0.0,
                "seconds": 1.0, "loop": False}
        run, calls = self.run_transcript("brainrot", clip)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(calls, [self.transcript_args("--background", "bg-1s.mp4 @ 0.0 s")])

    # red: a generated background written as a clip row, or left "pending"
    def test_brainrot_transcript_gets_generated(self):
        run, calls = self.run_transcript("brainrot", {"kind": "generated"})
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(calls, [self.transcript_args("--background", "generated")])

    # red: the explainer gains --background (its page would get a Background row), or reads the
    # timeline's background
    def test_explainer_transcript_has_no_background_flag(self):
        for background in (None, {"kind": "generated"}):
            with self.subTest(background=background):
                self.calls.unlink(missing_ok=True)
                run, calls = self.run_transcript("explainer", background)
                self.assertEqual((run.returncode, run.stdout), (0, "transcript: ok\n"), run.stderr)
                self.assertEqual(calls, [self.transcript_args()])

    # red: a brainrot timeline without a readable background goes on to the page with "pending"
    def test_brainrot_transcript_fails_on_a_timeline_without_background(self):
        timeline = "%s/out/build/timeline.json" % self.tmp
        for raw in (None, "{not json"):
            with self.subTest(raw=raw):
                self.calls.unlink(missing_ok=True)
                run, calls = self.run_transcript("brainrot", None, raw)
                self.assertEqual((run.returncode, run.stdout),
                                 (1, "transcript: FAIL cannot read %s\n" % timeline), run.stderr)
                self.assertEqual(calls, [])


class BrainrotRouteCase(unittest.TestCase):
    """The user-facing brainrot route: template, router and rung file."""

    def lint(self, path):
        return subprocess.run([sys.executable, str(STE_LINT), str(path)],
                              capture_output=True, text=True, timeout=60)

    # red: a template text over a brainrot limit (a 31-char title), or a cue off a sentence start
    def test_brainrot_template_checks(self):
        run = subprocess.run(["node", str(BUILD_TIMELINE), "--check", str(BRAINROT_TEMPLATE),
                              "--root", str(EXPLAIN)], capture_output=True, text=True, timeout=60)
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "", ""))

    # red: brainrot missing from the argument-hint, the syntax line, or contract step 3
    def test_skill_md_lists_five_rungs(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        hint = re.search(r'^argument-hint: "(.*)"$', text, re.M)
        self.assertIsNotNone(hint, "no argument-hint line")
        self.assertEqual(hint.group(1), "<subject> [--as ste|sheet|page|video|brainrot]")
        self.assertIn("Syntax: `/explain <subject> [--as ste|sheet|page|video|brainrot]`.", text)
        step3 = re.search(r"^3\. .*?(?=^4\. )", text, re.M | re.S)
        self.assertIsNotNone(step3, "no contract step 3")
        for name in ("ste", "sheet", "page", "video", "brainrot"):
            self.assertIn("`%s`" % name, step3.group(0))
        self.assertIn("five names", step3.group(0))

    # red: the brainrot row loses "Forced only" / "never chosen from content" (the rung could then
    # be chosen from content), or the English-only rule of SKILL.md or of the rung file goes
    def test_brainrot_stays_forced_only_and_english_only(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        row = re.search(r"^\| `brainrot`.*$", text, re.M)
        self.assertIsNotNone(row, "no brainrot row in the rung table")
        self.assertIn("Forced only", row.group(0))
        self.assertIn("never chosen from content", row.group(0))
        flat = " ".join(text.split())  # the rule wraps over two lines
        self.assertIn("Only `--as brainrot` selects it.", flat)
        self.assertIn("The brainrot rung is English only, like the video rung.", flat)
        rung = " ".join(BRAINROT_RUNG.read_text(encoding="utf-8").split())
        self.assertIn("The brainrot rung is English only. If the user asks for another language, "
                      "print the rung line. Say that the brainrot rung is English only. Stop. "
                      "Offer `page`.", rung)

    # red: a rung file line that breaks the STE profile (a contraction, a long sentence)
    def test_rung_file_lints_clean(self):
        run = self.lint(BRAINROT_RUNG)
        self.assertEqual((run.returncode, run.stdout.strip()), (0, "0 errors, 0 warnings"),
                         run.stdout + run.stderr)

    # red: a SKILL.md line that breaks the STE profile
    def test_skill_md_lints_clean(self):
        run = self.lint(SKILL_MD)
        self.assertEqual((run.returncode, run.stdout.strip()), (0, "0 errors, 0 warnings"),
                         run.stdout + run.stderr)

    def stage_script_format(self, template):
        """Run the real stage_script of render.sh on a copy of `template` (absolute root) with
        the real tools and no workspace; returns (the stdout lines, the `fmt=<value>` line)."""
        tmp = Path(tempfile.mkdtemp(prefix="render-format-test-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        out = tmp / "out"
        out.mkdir()
        script = json.loads(template.read_text(encoding="utf-8"))
        script["provenance"]["root"] = str(EXPLAIN)
        (out / "script.json").write_text(json.dumps(script), encoding="utf-8")
        text = (
            "set -eu\n" + render_functions(["fail", "first_cause", "run_tool", "stage_script"]) +
            'out=%(out)s script=%(out)s/script.json video=%(ex)s/video scripts=%(ex)s/scripts\n'
            'root="" fmt=explainer\nstage_script\necho "fmt=$fmt"\n' % {"out": out, "ex": EXPLAIN})
        run = subprocess.run(["/bin/bash", "-c", text], capture_output=True, text=True, timeout=120)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        lines = run.stdout.splitlines()
        return lines[:-1], lines[-1]

    # red: stage_script leaves fmt at its default, so a brainrot script gets explainer speed and
    # no background stage; or it reads "brainrot" for a script without a format key
    def test_stage_script_reads_the_format_from_the_script(self):
        lines, fmt = self.stage_script_format(BRAINROT_TEMPLATE)
        self.assertEqual((lines, fmt), (["script: ok (4 scenes)"], "fmt=brainrot"))
        lines, fmt = self.stage_script_format(TEMPLATE)
        self.assertEqual((lines, fmt), (["script: ok (5 scenes)"], "fmt=explainer"))


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
