"""Tests for scripts/render.sh: the nine-stage video pipeline (ten stages for a brainrot script or a film).

StageFunctionCase runs stage_narration, stage_background and stage_transcript of render.sh against
fake tools (the format -> --speed mapping, the picker's lines, exit codes and stderr, the
--background text of the transcript). RunHarness is the temp skill tree and the helpers of a run of a
copy of render.sh against a fake of every tool it calls, in a workspace whose path has a space.
RunDirectoryCase uses it for the run directory of each render (what it holds, that it goes after a
pass, a FAIL and a signal, the sweep of old ones); SceneRunCase of test_render_film.py uses it for the
scene stage of a film. The stage-1 tests need no workspace: they fail before any tool that needs one
runs. A fake npm that exits 1 sits first on PATH and the workspace is an empty temp dir, so a mutant
that gets past stage 1 fails fast instead of installing. BrainrotRouteCase checks the user-facing
brainrot route: the template, SKILL.md, the rung file, and the format that stage_script reads
from a real script.json. E2EHelperCase checks the environment that the gated renders get from
tests/video_e2e.py: the caller's workspace, none of the caller's background settings. The
end-to-end class renders the three-scene fixture once (tests/video_e2e.py) and needs
EXPLAIN_VIDEO_E2E=1. Each test names the mutation that turns it red."""

import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from video_e2e import (E2E, E2E_REASON, EXPLAIN, RENDER_SH, TEMPLATE, render_env, render_fixture,
                       workspace)

BRAINROT_TEMPLATE = EXPLAIN / "templates" / "brainrot-script.json"
BUILD_TIMELINE = EXPLAIN / "video" / "build-timeline.mjs"
STE_LINT = EXPLAIN.parent / "ste" / "scripts" / "ste_lint.py"
SKILL_MD = EXPLAIN / "SKILL.md"
BRAINROT_RUNG = EXPLAIN / "rungs" / "brainrot.md"

# STAGES: the ten stages of a brainrot run, in order. test_render_brainrot compares a run with it, so it
# holds no stage that a brainrot run does not print; an explainer run has no "background".
# FILM_STAGES: the stages that only a film run has, not part of STAGES: the scene, after the workspace, and
# the guard, after the timeline. stage_lines finds the lines of both.
STAGES = ("script", "workspace", "narration", "timeline", "background", "render", "container", "sync",
          "stills", "transcript")
FILM_STAGES = ("scene", "guard")
STAGE_LINE = re.compile(r"^(%s)\b" % "|".join(STAGES + FILM_STAGES))


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
            'run=%(t)s/ws/runs/run.1.test\n%(setup)s\n%(stage)s\n'
            % {"t": self.tmp, "fmt": fmt, "stage": stage, "setup": setup})
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

    # red: the picker gets another argument order, a seed, the shared <ws>/app in place of the run
    # directory, or a folder other than <ws>/backgrounds
    def test_picker_arguments_and_default_folder(self):
        self.fake_picker('print("background: ok generated")\n')
        run = self.run_stage("stage_background", "brainrot")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stdout, "background: ok generated\n")
        self.assertEqual(self.call_lines(),
                         ["%(t)s/out/build/timeline.json %(t)s/ws/app/remote-cli %(t)s/ws/runs/run.1.test "
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

    # red: a usage error (exit 2, stderr only, as argparse gives it) gives no FAIL line, or its
    # stderr lines vanish
    def test_picker_usage_error_reaches_the_user_and_fails(self):
        self.fake_picker('print("usage: pick_background.py <timeline.json> ...", file=sys.stderr)\n'
                         'print("pick_background.py: error: the following arguments are required: '
                         '--dir", file=sys.stderr)\nsys.exit(2)\n')
        run = self.run_stage("stage_background", "brainrot")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertEqual(run.stdout,
                         "  usage: pick_background.py <timeline.json> ...\n"
                         "  pick_background.py: error: the following arguments are required: --dir\n"
                         "background: FAIL pick_background.py exit 2\n")

    # red: the real picker reports an invalid EXPLAIN_BRAINROT_SEED on stderr with exit 2, so the
    # user sees "background: FAIL pick_background.py exit 2" instead of the cause
    def test_bad_seed_fail_line_names_the_cause(self):
        shutil.copy(EXPLAIN / "video" / "pick_background.py", self.tmp / "video" / "pick_background.py")
        run = self.run_stage("stage_background", "brainrot", env={"EXPLAIN_BRAINROT_SEED": "abc"})
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (1, "background: FAIL EXPLAIN_BRAINROT_SEED must be an integer, got 'abc'\n", ""))

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


# The fake Remotion CLI: it appends one JSON line for each call (its argv, its cwd by real path,
# the paths under its cwd without following a link, the names in public/ and public/audio/, the
# real path of node_modules, the names in <ws>/runs), then sleeps FAKE_REMOTION_SLEEP s and exits
# FAKE_REMOTION_EXIT. With FAKE_REMOTION_OUTLIVE set it outlives TERM and HUP, as the Remotion CLI
# does (its handler only kills its browser, and the render goes on with a new one): the signal ends
# the sleep, and 1 s later it writes .remotion/ into its cwd (made again if it is gone), as the CLI
# does when it fetches a browser, then marks its end in remotion.end.
FAKE_CLI = """#!/usr/bin/env python3
import json, os, signal, sys, time
def names(path):
    return sorted(os.listdir(path)) if os.path.isdir(path) else None
class Outlived(Exception):
    pass
def outlive(signum, frame):
    raise Outlived
if os.environ.get("FAKE_REMOTION_OUTLIVE"):
    signal.signal(signal.SIGTERM, outlive)
    signal.signal(signal.SIGHUP, outlive)
call = {"argv": sys.argv[1:], "cwd": os.getcwd(),
        "files": sorted(os.path.relpath(os.path.join(d, n)) for d, ds, fs in os.walk(".") for n in ds + fs),
        "public": names("public"), "audio": names("public/audio"),
        "node_modules": os.path.realpath("node_modules"),
        "runs": names(os.path.join(os.environ["EXPLAIN_VIDEO_WORKSPACE"], "runs"))}
with open(os.path.join(os.environ["FAKE_DIR"], "remotion.jsonl"), "a") as log:
    log.write(json.dumps(call) + "\\n")
try:
    time.sleep(float(os.environ.get("FAKE_REMOTION_SLEEP", "0")))
except Outlived:
    time.sleep(1)
    os.makedirs(os.path.join(call["cwd"], ".remotion"), exist_ok=True)
    open(os.path.join(os.environ["FAKE_DIR"], "remotion.end"), "w").close()
sys.exit(int(os.environ.get("FAKE_REMOTION_EXIT", "0")))
"""

# The temp tree of RunDirectoryCase, by path under FAKE_DIR: a fake of every tool render.sh calls
# (narrate.sh and the picker log a JSON list to calls.log), and a video/ with what a checkout may
# hold besides the sources: its own node_modules and public, and __pycache__ at two depths.
RUN_FAKES = {
    "remotion": FAKE_CLI,
    "skill/scripts/video-workspace.sh":
        '#!/bin/bash\nnm="$EXPLAIN_VIDEO_WORKSPACE/app/node_modules"\nmkdir -p "$nm/.bin"\n'
        'cp "$FAKE_DIR/remotion" "$nm/.bin/remotion"\necho shared > "$nm/sentinel.txt"\n'
        'echo "workspace: ok $EXPLAIN_VIDEO_WORKSPACE"\n',
    "skill/scripts/narrate.sh":
        '#!/bin/bash\necho \'["narrate"]\' >> "$FAKE_DIR/calls.log"\n'
        'echo \'{"engine": "say"}\' > "$2/durations.json"\necho wav > "$2/s1.say.wav"\n',
    "skill/scripts/verify.sh": "#!/bin/bash\n",
    "skill/video/build-timeline.mjs":
        'import { writeFileSync } from "node:fs";\nconst a = process.argv.slice(2);\n'
        'if (a[0] !== "--check") writeFileSync(a[3], JSON.stringify(\n'
        '  {scenes: [{audio: "audio/s1.say.wav"}], background: {kind: "generated"}}));\n',
    "skill/video/transcript.py": "",
    "skill/video/check_budgets.py": 'print("ok 1 3.0 3.000")\n',
    "skill/video/check_render.sh":
        '#!/bin/bash\necho "container: ok (3.00 s)"\necho "sync: ok"\necho "stills (1): ok $3"\n',
    "skill/video/pick_background.py":
        "import json, os, sys\nwith open(os.environ['FAKE_DIR'] + '/calls.log', 'a') as log:\n"
        "    log.write(json.dumps(['pick'] + sys.argv[1:]) + '\\n')\n"
        "print(os.environ.get('FAKE_PICKER_LINE', 'background: ok generated'))\n"
        "sys.exit(int(os.environ.get('FAKE_PICKER_EXIT', '0')))\n",
    "skill/video/package.json": "{}\n",
    "skill/video/src/marker.txt": "",
    "skill/video/src/public/deep.txt": "",
    "skill/video/src/node_modules/deep.txt": "",
    "skill/video/node_modules/decoy.txt": "",
    "skill/video/public/decoy.txt": "",
    "skill/video/__pycache__/stale.pyc": "",
    "skill/video/src/__pycache__/stale.pyc": "",
}


def names(path):
    """The sorted names in the directory `path`, or None when it is not a directory."""
    return sorted(os.listdir(path)) if os.path.isdir(path) else None


def default_signals():
    """preexec_fn: HUP, INT and TERM back to their default action. A test runner started in the
    background hands SIGINT on as ignored, and bash cannot trap a signal that was ignored when it
    started."""
    for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal.SIG_DFL)


def kill_group(proc):
    """Cleanup: kill what is left of the process group of `proc` (a sleeping fake CLI), reap it."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    proc.wait()


class RunHarness:
    """Not a TestCase: the temp skill tree of a run of render.sh and the helpers that drive it. A copy
    of render.sh sits in <tmp>/skill, and runs against the fakes of `fakes` (RUN_FAKES, unless a case
    sets its own) in the workspace <tmp>/w s (the space is deliberate). RunDirectoryCase, and
    SceneRunCase of test_render_film.py, list it before TestCase. No workspace, no render."""

    fakes = RUN_FAKES

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="render-run-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        for name, text in self.fakes.items():
            path = self.tmp / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            path.chmod(0o755)
        self.render_sh = self.tmp / "skill" / "scripts" / "render.sh"
        shutil.copy(RENDER_SH, self.render_sh)
        self.ws = self.tmp / "w s"
        self.runs = self.ws / "runs"
        self.shared = self.ws / "app" / "node_modules"
        self.out = self.tmp / "out"
        self.out.mkdir()
        self.cli_log = self.tmp / "remotion.jsonl"

    def start(self, fmt="explainer", **env):
        """A Popen of the copied render.sh on a one-scene script.json of format `fmt`, in a session
        of its own, stdout and stderr in files; `env` holds the FAKE_* settings of this run. Its cwd
        is the temp dir, so a mutant that copies into an empty run writes nothing into the repo."""
        script = {"format": fmt, "provenance": {"root": str(self.tmp)}, "scenes": [{"id": "s1"}]}
        (self.out / "script.json").write_text(json.dumps(script), encoding="utf-8")
        self.cli_log.unlink(missing_ok=True)
        run_env = {k: v for k, v in os.environ.items() if not k.startswith(("EXPLAIN_", "FAKE_"))}
        run_env.update(env, EXPLAIN_VIDEO_WORKSPACE=str(self.ws), FAKE_DIR=str(self.tmp))
        with open(self.tmp / "stdout", "w") as stdout, open(self.tmp / "stderr", "w") as stderr:
            proc = subprocess.Popen(
                ["/bin/bash", str(self.render_sh), str(self.out), "--engine", "say"],
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, env=run_env, cwd=self.tmp,
                start_new_session=True, preexec_fn=default_signals)
        self.addCleanup(kill_group, proc)
        return proc

    def output(self):
        """(stdout, stderr) of the last start, as far as they are written."""
        return tuple((self.tmp / name).read_text(encoding="utf-8") for name in ("stdout", "stderr"))

    def finish(self, proc, timeout=60):
        """The CompletedProcess of `proc` once it has exited; the test fails after `timeout` s."""
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.fail("render.sh still runs after %s s:\n%s" % (timeout, "".join(self.output())))
        return subprocess.CompletedProcess(proc.args, proc.returncode, *self.output())

    def wait_for_cli(self, proc):
        """Return once the fake CLI has logged its call (it sleeps after that); the test fails if
        render.sh exits first or no call comes in 20 s."""
        deadline = time.monotonic() + 20
        while not (self.cli_log.exists() and self.cli_log.read_text(encoding="utf-8").endswith("\n")):
            if proc.poll() is not None or time.monotonic() > deadline:
                self.fail("the Remotion CLI did not run:\n" + "".join(self.output()))
            time.sleep(0.05)

    def cli_calls(self):
        if not self.cli_log.exists():
            return []
        return [json.loads(line) for line in self.cli_log.read_text(encoding="utf-8").splitlines()]

    def tool_calls(self, tool):
        """The argument lists that the fake `tool` (narrate, pick) was called with."""
        log = self.tmp / "calls.log"
        lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
        return [call[1:] for call in map(json.loads, lines) if call[0] == tool]

    def run_pattern(self, runs, pid):
        """The path of a run directory of render.sh `pid` in `runs`: run.<pid>.<6 characters>."""
        return r"^%s/run\.%d\.[A-Za-z0-9]{6}$" % (re.escape(str(runs)), pid)

    def render_or_fail_lines(self, stdout):
        """The stage lines of `stdout` that start with "render", and every line with FAIL in it:
        none after a signal, which ends render.sh with exit 1 and no FAIL line."""
        return [line for line in stdout.splitlines()
                if (STAGE_LINE.match(line) and line.startswith("render")) or "FAIL" in line]


class RunDirectoryCase(RunHarness, unittest.TestCase):
    """render.sh compiles in a run directory of its own: what it holds, that it goes after a pass, a
    FAIL and a signal, the sweep of old ones. It runs against RUN_FAKES."""

    # red: the render keeps cwd <ws>/app
    def test_render_runs_in_its_own_run_directory(self):
        proc = self.start()
        run = self.finish(proc)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        [call] = self.cli_calls()
        self.assertRegex(call["cwd"], self.run_pattern(os.path.realpath(self.runs), proc.pid))
        self.assertIn("package.json", call["files"])
        self.assertIn("src/marker.txt", call["files"])
        self.assertEqual(call["node_modules"], os.path.realpath(self.shared))
        self.assertEqual(call["audio"], ["s1.say.wav"])
        out = os.path.realpath(self.out)
        self.assertEqual(call["argv"], ["render", "Explain", out + "/video.mp4",
                                        "--props", out + "/build/timeline.json"])

    # red: a plain recursive copy of video/ (its node_modules and public come along, and the link
    # to the shared packages lands inside the copied node_modules)
    def test_a_checkouts_node_modules_and_public_are_not_copied(self):
        run = self.finish(self.start())
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        [call] = self.cli_calls()
        self.assertEqual(call["public"], ["audio"])
        self.assertEqual(call["node_modules"], os.path.realpath(self.shared))
        self.assertFalse((self.shared / "decoy.txt").exists())
        # only the top-level node_modules and public are left out; __pycache__ at any depth
        self.assertIn("src/public/deep.txt", call["files"])
        self.assertIn("src/node_modules/deep.txt", call["files"])
        self.assertEqual([path for path in call["files"] if "__pycache__" in path], [])

    # red: the audio still goes to <ws>/app/public/audio
    def test_nothing_is_written_under_the_app(self):
        run = self.finish(self.start())
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(names(self.ws / "app"), ["node_modules"])
        self.assertEqual(names(self.shared), [".bin", "sentinel.txt"])

    # red: no EXIT trap, or a removal that goes through the node_modules link
    def test_run_directory_removed_after_a_pass(self):
        run = self.finish(self.start())
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(names(self.runs), [])
        self.assertTrue((self.shared / "sentinel.txt").exists())

    # red: removal only at the end of the script
    def test_run_directory_removed_after_a_fail(self):
        cases = (
            ("explainer", {"FAKE_REMOTION_EXIT": "3"},
             "render: FAIL remotion render exit 3 (log %s/build/render.log)" % os.path.realpath(self.out)),
            ("brainrot", {"FAKE_PICKER_LINE": "background: FAIL x", "FAKE_PICKER_EXIT": "1"},
             "background: FAIL x"),
        )
        for fmt, env, last in cases:
            with self.subTest(fmt=fmt):
                proc = self.start(fmt, **env)
                run = self.finish(proc)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertEqual(stage_lines(run.stdout)[-1], last, run.stdout)
                self.assertEqual(names(self.runs), [])
                self.assertTrue((self.shared / "sentinel.txt").exists())
        # the picker was given the run directory of that render
        [pick] = self.tool_calls("pick")
        self.assertRegex(pick[2], self.run_pattern(self.runs, proc.pid))

    # red: no EXIT trap (the directory stays), or no signal trap (the exit code is the signal's),
    # or a signal trap that does not exit (trap ':', so the run prints "render: FAIL remotion
    # render exit <n>" for the CLI the signal killed)
    def test_run_directory_removed_after_a_signal(self):
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            with self.subTest(signal=sig.name):
                proc = self.start(FAKE_REMOTION_SLEEP="30")
                self.wait_for_cli(proc)
                os.killpg(proc.pid, sig)
                run = self.finish(proc, timeout=10)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertEqual(self.render_or_fail_lines(run.stdout), [], run.stdout)
                self.assertEqual(names(self.runs), [])
                self.assertTrue((self.shared / "sentinel.txt").exists())

    # red: the CLI runs in a subshell that the signal ends at once, so render.sh exits and removes
    # the run directory while the CLI still runs, and the CLI's late write makes it again; or a
    # signal trap that does not exit (trap ':', so the run goes on after the CLI's end)
    def test_render_sh_waits_for_a_cli_that_outlives_the_signal(self):
        end = self.tmp / "remotion.end"
        for sig in (signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=sig.name):
                end.unlink(missing_ok=True)
                proc = self.start(FAKE_REMOTION_SLEEP="30", FAKE_REMOTION_OUTLIVE="1")
                self.wait_for_cli(proc)
                os.killpg(proc.pid, sig)
                run = self.finish(proc, timeout=10)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertEqual(self.render_or_fail_lines(run.stdout), [], run.stdout)
                # a render.sh that did not wait has exited before the CLI: wait for the CLI's end
                deadline = time.monotonic() + 10
                while not end.exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertTrue(end.exists(), "the fake CLI did not end")
                self.assertEqual(names(self.runs), [])
                self.assertTrue((self.shared / "sentinel.txt").exists())

    # red: the signal is ignored and the run goes on to "transcript: ok"
    def test_signal_to_render_sh_alone_stops_the_run_when_the_tool_returns(self):
        proc = self.start(FAKE_REMOTION_SLEEP="3")
        self.wait_for_cli(proc)
        os.kill(proc.pid, signal.SIGTERM)
        run = self.finish(proc, timeout=20)
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertEqual([line for line in stage_lines(run.stdout)
                          if line.startswith(("render", "container", "transcript"))], [])
        self.assertEqual(names(self.runs), [])

    # red: a sweep with no age test, or a removal that follows the link, or a sweep with no name
    # test (an old entry not named run.* goes too)
    def test_old_run_directories_are_swept(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep", encoding="utf-8")
        old, young = self.runs / "run.1.oldold", self.runs / "run.2.young"
        old.mkdir(parents=True)
        (old / "node_modules").symlink_to(outside)
        young.mkdir()
        keep_dir, notes = self.runs / "keep-me", self.runs / "notes.txt"
        keep_dir.mkdir()
        (keep_dir / "kept.txt").write_text("kept", encoding="utf-8")
        notes.write_text("notes", encoding="utf-8")
        now = time.time()
        # after the link and kept.txt are made: each changes its directory's modification time
        for path in (old, keep_dir, notes):
            os.utime(path, (now - 25 * 3600, now - 25 * 3600))
        os.utime(young, (now - 23 * 3600, now - 23 * 3600))
        run = self.finish(self.start())
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        [call] = self.cli_calls()
        self.assertEqual(call["runs"], sorted(["keep-me", "notes.txt", "run.2.young",
                                               os.path.basename(call["cwd"])]))
        self.assertEqual(names(self.runs), ["keep-me", "notes.txt", "run.2.young"])
        self.assertTrue((outside / "keep.txt").exists())
        self.assertEqual((keep_dir / "kept.txt").read_text(encoding="utf-8"), "kept")
        self.assertEqual(notes.read_text(encoding="utf-8"), "notes")

    # red: find on the link itself, which lists nothing (the old run directory stays)
    def test_sweep_works_when_runs_is_a_symlink(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep", encoding="utf-8")
        target = self.tmp / "runs-elsewhere"
        old = target / "run.1.oldold"
        old.mkdir(parents=True)
        (old / "node_modules").symlink_to(outside)
        now = time.time()
        os.utime(old, (now - 25 * 3600, now - 25 * 3600))
        self.ws.mkdir()
        self.runs.symlink_to(target)
        proc = self.start()
        run = self.finish(proc)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertFalse(old.exists() or old.is_symlink(), "the old run directory stays")
        self.assertTrue((outside / "keep.txt").exists())
        self.assertTrue(self.runs.is_symlink(), "<ws>/runs is no longer a symlink")
        [call] = self.cli_calls()
        self.assertRegex(call["cwd"], self.run_pattern(os.path.realpath(target), proc.pid))
        self.assertEqual(names(target), [])

    # red: no chmod after the copy (rm -rf cannot empty the read-only copy of src, so the run
    # directory stays)
    def test_run_directory_from_a_read_only_tree_is_removed(self):
        src = self.tmp / "skill" / "video" / "src"
        marker = src / "marker.txt"
        marker.chmod(0o444)
        src.chmod(0o555)
        self.addCleanup(marker.chmod, 0o644)
        self.addCleanup(src.chmod, 0o755)
        run = self.finish(self.start())
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(names(self.runs), [])
        self.assertNotIn("Permission denied", run.stderr)
        self.assertTrue((self.shared / "sentinel.txt").exists())

    # red: the failure is ignored and a render starts with an empty run
    def test_unmakeable_run_directory_fails_the_workspace_stage(self):
        self.ws.mkdir()
        self.runs.write_text("a file, not a directory", encoding="utf-8")
        run = self.finish(self.start())
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertEqual(stage_lines(run.stdout),
                         ["script: ok (1 scenes)",
                          "workspace: FAIL cannot make a run directory in %s/runs" % self.ws])
        self.assertEqual(self.tool_calls("narrate"), [])


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


class E2EHelperCase(unittest.TestCase):
    """The environment of the gated renders (tests/video_e2e.py), with no render: they keep the
    caller's workspace and drop the caller's background settings."""

    # red: render_env drops EXPLAIN_VIDEO_WORKSPACE, so a test render goes to the default workspace
    # (or workspace() names another workspace than the one the render gets)
    def test_render_env_keeps_the_callers_workspace(self):
        default = Path("~/karpathy/video-workspace").expanduser()
        with mock.patch.dict(os.environ, {"EXPLAIN_VIDEO_WORKSPACE": "/x/ws"}):
            self.assertEqual(render_env().get("EXPLAIN_VIDEO_WORKSPACE"), "/x/ws")
            self.assertEqual(workspace(), Path("/x/ws"))
        with mock.patch.dict(os.environ):
            os.environ.pop("EXPLAIN_VIDEO_WORKSPACE", None)
            self.assertIsNone(render_env().get("EXPLAIN_VIDEO_WORKSPACE"))
            self.assertEqual(workspace(), default)
        # an empty value counts as unset, as in render.sh (${EXPLAIN_VIDEO_WORKSPACE:-...})
        with mock.patch.dict(os.environ, {"EXPLAIN_VIDEO_WORKSPACE": ""}):
            self.assertEqual(workspace(), default)

    # red: render_env keeps the caller's EXPLAIN_BRAINROT_SEED or EXPLAIN_BRAINROT_BACKGROUNDS, so
    # the caller's seed or clip folder steers a test render (or `extra` is not applied)
    def test_render_env_drops_the_callers_background_settings(self):
        caller = {"EXPLAIN_BRAINROT_BACKGROUNDS": "/x/clips", "EXPLAIN_BRAINROT_SEED": "3"}
        with mock.patch.dict(os.environ, caller):
            env = render_env()
            self.assertEqual([name for name in caller if name in env], [])
            self.assertEqual(render_env(EXPLAIN_BRAINROT_SEED="7").get("EXPLAIN_BRAINROT_SEED"), "7")


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

    # red: the helper drops EXPLAIN_VIDEO_WORKSPACE and the render goes to the default workspace.
    # Not run red (that is a render in a workspace this branch must not use): E2EHelperCase is the
    # red-first proof of the helper, this case binds the real render to it.
    def test_render_used_the_callers_workspace(self):
        self.assertEqual(stage_lines(self.result.stdout)[1:2], ["workspace: ok %s" % workspace()],
                         self.result.stdout + self.result.stderr)

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
