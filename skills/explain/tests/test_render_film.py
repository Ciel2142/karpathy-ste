"""The film cases of scripts/render.sh: an always-run class on single functions, and the gated
render of the template.

FilmFunctionCase runs single functions of the script (stage_render, clear_stale) in a temporary
directory, through render_functions of test_render.py, with a fake remotion CLI and no workspace:
the composition each format renders, and the files a new run removes.

SceneStageCase runs stage_scene alone in a temporary directory (an output directory with a scene, a
run directory with the example's src/film and a node_modules link, a fake tsc: FAKE_TSC), with the
real check_scene.py and build-timeline.mjs: the copy over src/film, the names, the type check, the
four FAIL lines and the lines of tsc, cut and renamed.

GuardStageCase runs stage_guard alone in a temporary directory (an output directory with a timeline of three
checkFrames and one narration clip, a run directory, a fake remotion: FAKE_PASS): the pass the stage makes
(its arguments, its cwd), the format that has none, the stage line of a frame fault, of a mark error and of a
pass that failed otherwise, and the timeline or clip that cannot be read or copied. A marker of the log fails
the stage whatever the exit code of the pass.

SceneRunCase runs a copy of render.sh as RunDirectoryCase does (RunHarness of test_render.py), on a film
script, against the same fakes with the real check_scene.py, FAKE_TSC and a build-timeline.mjs that takes
--types and writes two checkFrames: the eleven stage lines of a film and none of the scene and guard stages
for another format, the scene that the guard pass and the render draw, where they and tsc run, the three
FAIL lines that stop a run before any synthesis, the engine that narrate.py --check gives to the
workspace and narration stages of a run with no --engine, and a tsc and a guard pass that outlive
TERM and HUP.

FilmRenderCase (EXPLAIN_VIDEO_E2E=1 only) renders the worked example through scripts/render.sh
--engine say once per process (render_film() of film_output(): a temporary output directory removed
at exit, with script.json the template templates/video-script.json, template_script() of
test_film_example.py rooted at the repository, and scene/ a copy of the example scene FILM_DIR; the
environment render_env() of video_e2e.py, so the render uses workspace()). It holds the eleven stage
lines (the scene stage counts SCENE_FILES, the guard CHECK_FRAMES), the stills at the check frames,
the size, the transcript page, the speed of the narration, the place of each clip (the voice starts
leadFrames after the scene start) and a picture that changes in every scene. The expected scene ids,
sentences and stills come from the template, not from the render's timeline.

ScenePlantCase (EXPLAIN_VIDEO_E2E=1 only) holds the four stage plants of spec 9.2: the output
directory of FilmRenderCase with one edit (a cite snippet with one word changed, a mark on an
unknown scene, a used import of another package, // @ts-nocheck on line 1), rendered the same way.
Each stops with its line before any synthesis; FilmRenderCase, with the same output directory and no
edit, is their control. The expected lines come from the template and the edited files, not from
the render.

GuardPlantCase (EXPLAIN_VIDEO_E2E=1 only) proves the browser rules of the guard (spec 7.3, 9.2) on the
same output directory with one edit: the planted film (a scene file added by add_to_film), rendered three
times, stops at its first check frame with the same four faults each time; a label off the canvas at the last
frame alone (a file added the same way) stops at the last check frame; a label whose <tspan> is smaller than
the label (a file added the same way) stops with the size of the <tspan>; the mark plant (the word of the first
at("subject", { word: "subject" }) of Film.tsx written as "zebra": no file added) stops with the guard's
mark line; the example as a clip (script.json "format" set to "clip": no file added) stops at the floor of
a clip, 19 px, with SMALLTEXT faults between 14 and 19 px. FilmRenderCase is their control. Each test names
the mutation that turns it red."""

import atexit
import importlib.util
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from png_diff import differing_pixels
from test_check_scene import CHECK_SCENE, SCENE_CLEAN, append, prepend
from test_film_example import FILM_DIR, template_script
from test_narrate import NARRATE_PY
from test_render import (RUN_FAKES, STAGE_LINE, STAGES, RunHarness, names, render_functions,
                         stage_lines)
from test_render_brainrot import video_size
from video_e2e import E2E, E2E_REASON, EXPLAIN, RENDER_SH, RENDER_TIMEOUT, render_env, workspace

VERIFY_SH = EXPLAIN / "scripts" / "verify.sh"
VERIFY_SYNC = EXPLAIN / "video" / "verify_sync.py"


def load(name, path):
    """The module at `path`, loaded by path under `name` (no process runs)."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


split_sentences = load("narrate_for_film", NARRATE_PY).split_sentences
voiced_windows = load("verify_sync_for_film", VERIFY_SYNC).voiced_windows
WINDOW = 0.02   # seconds per window of voiced_windows (verify_sync.py WINDOW)
LEAD_TOLERANCE = 0.06   # seconds: three windows

# The fake tsc: it appends one JSON line to $FAKE_DIR/tsc.jsonl for each call (its argv, its cwd by real
# path, and the text of each file of src/film under its cwd, by name: None for a directory), prints the
# file FAKE_TSC_OUTPUT when set, sleeps FAKE_TSC_SLEEP s and exits FAKE_TSC_EXIT (default 0). With
# FAKE_TSC_OUTLIVE set it outlives TERM and HUP as FAKE_CLI of test_render.py does: the signal ends the
# sleep, and 1 s later it makes .tsc-late/ in its cwd (made again if it is gone) and marks its end in
# tsc.end.
FAKE_TSC = """#!/usr/bin/env python3
import json, os, signal, sys, time
class Outlived(Exception):
    pass
def outlive(signum, frame):
    raise Outlived
if os.environ.get("FAKE_TSC_OUTLIVE"):
    signal.signal(signal.SIGTERM, outlive)
    signal.signal(signal.SIGHUP, outlive)
film = {}
if os.path.isdir("src/film"):
    for name in sorted(os.listdir("src/film")):
        path = os.path.join("src/film", name)
        film[name] = open(path, encoding="utf-8").read() if os.path.isfile(path) else None
call = {"argv": sys.argv[1:], "cwd": os.path.realpath(os.getcwd()), "film": film}
with open(os.path.join(os.environ["FAKE_DIR"], "tsc.jsonl"), "a") as log:
    log.write(json.dumps(call) + "\\n")
if os.environ.get("FAKE_TSC_OUTPUT"):
    with open(os.environ["FAKE_TSC_OUTPUT"], encoding="utf-8") as text:
        sys.stdout.write(text.read())
    sys.stdout.flush()
try:
    time.sleep(float(os.environ.get("FAKE_TSC_SLEEP", "0")))
except Outlived:
    time.sleep(1)
    os.makedirs(os.path.join(call["cwd"], ".tsc-late"), exist_ok=True)
    open(os.path.join(os.environ["FAKE_DIR"], "tsc.end"), "w").close()
sys.exit(int(os.environ.get("FAKE_TSC_EXIT", "0")))
"""

TEMPLATE_SCENES = template_script()["scenes"]
SCENES = len(TEMPLATE_SCENES)
# The files of the example scene that the scene stage copies and counts: the *.ts and *.tsx files of
# FILM_DIR, without its script.gen.ts (and without a hidden file, which the stage's glob does not match).
SCENE_FILES = len([path for path in FILM_DIR.iterdir()
                   if path.suffix in (".ts", ".tsx") and path.is_file() and not path.name.startswith(".")
                   and path.name != "script.gen.ts"])
# The check frames of the template, which the guard measures: for each scene, the middle of each of its
# sentences and its last frame.
CHECK_FRAMES = sum(len(split_sentences(scene["narration"])) + 1 for scene in TEMPLATE_SCENES)
# The eleven stage lines of a film run, in order: the nine names that every format has, the scene stage
# third and the guard sixth, after the timeline.
ORDER = [
    r"script: ok \(%d scenes\)" % SCENES,
    r"workspace: ok /.+",
    r"scene: ok \(%d files\)" % SCENE_FILES,
    r"narration \(say\): ok",
    r"timeline \(%d scenes, \d+\.\d s\): ok" % SCENES,
    r"guard \(%d frames\): ok" % CHECK_FRAMES,
    r"render \(\d+\.\d s, \d+\.\d\d render-min/video-min\)( \(limit 2\.0\))?: ok",
    r"container: ok \(\d+\.\d\d s\)",
    r"sync: ok",
    r"stills \(\d+\): ok /.+",
    r"transcript: ok",
]
CHANGED_PIXELS = 500   # an -end still and the one before it differ in more than this

_cache = {}


def film_output(edit=None):
    """A temporary output directory of the worked example, removed at exit: script.json is
    template_script(), scene/ a copy of FILM_DIR (its script.gen.ts too, which the stage leaves
    behind); then `edit(out)` runs on it. Returns the directory (a Path)."""
    out = Path(tempfile.mkdtemp(prefix="explain-film-e2e-"))
    atexit.register(shutil.rmtree, out, ignore_errors=True)
    (out / "script.json").write_text(json.dumps(template_script(), indent=2), encoding="utf-8")
    shutil.copytree(FILM_DIR, out / "scene")
    if edit is not None:
        edit(out)
    return out


def add_to_film(test, out, name, text, element):
    """An edit of film_output(): writes `text` to out/scene/<name>.tsx, and makes out/scene/Film.tsx import
    <name> (on the line after the import of Props) and draw the line `element` (before the prompt, the last
    object of the stage). `test` fails if Film.tsx has no such import or no such prompt."""
    scene = out / "scene"
    (scene / ("%s.tsx" % name)).write_text(text, encoding="utf-8")
    film = scene / "Film.tsx"
    lines = film.read_text(encoding="utf-8").split("\n")
    anchor = 'import type { Props } from "./script.gen";'
    test.assertIn(anchor, lines)
    lines.insert(lines.index(anchor) + 1, 'import { %s } from "./%s";' % (name, name))
    prompt = [k for k, line in enumerate(lines) if line.startswith("      <Prompt subject=")]
    test.assertTrue(prompt, "%s draws no <Prompt subject=" % film)
    lines.insert(prompt[0], "      %s" % element)
    film.write_text("\n".join(lines), encoding="utf-8")


def render_output(out):
    """The CompletedProcess of render.sh <out> --engine say, in the environment render_env()."""
    return subprocess.run(
        ["/bin/bash", str(RENDER_SH), str(out), "--engine", "say"],
        capture_output=True, text=True, env=render_env(), timeout=RENDER_TIMEOUT,
    )


def render_film():
    """(output dir, CompletedProcess) of the one template render of this process: film_output(),
    with no edit."""
    if "result" not in _cache:
        out = film_output()
        _cache["result"] = (out, render_output(out))
    return _cache["result"]


def end_still(n, scene):
    """The name of the still at the last frame of scene `n` (from 1) of the template."""
    return "still-%02d-%s-end.png" % (n, scene["id"])


def first_voiced(voiced, start):
    """The seconds from `start` to the first voiced window at or after `start`, or None."""
    k = math.ceil(start / WINDOW - 1e-9)
    hit = next((i for i in range(k, len(voiced)) if voiced[i]), None)
    return None if hit is None else hit * WINDOW - start


def run_functions(tmp: Path, names: list, setup: str) -> subprocess.CompletedProcess:
    """Run the named functions of render.sh in /bin/bash with cwd `tmp`: `set -eu`, the text of
    the functions (render_functions), then the shell text `setup`."""
    script = "set -eu\n" + render_functions(names) + setup
    return subprocess.run(["/bin/bash", "-c", script], capture_output=True, text=True,
                          cwd=tmp, timeout=60)


class FilmFunctionCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="render-film-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.out = self.tmp / "out"
        (self.out / "build").mkdir(parents=True)

    def fake_remotion(self, calls):
        """An executable that appends its arguments to `calls` as one JSON list per line."""
        remotion = self.tmp / "remotion"
        remotion.write_text(
            "#!/bin/bash\n"
            "exec python3 -c 'import json, sys\n"
            "with open(sys.argv[1], \"a\") as log:\n"
            "    log.write(json.dumps(sys.argv[2:]) + \"\\n\")' %s \"$@\"\n" % calls,
            encoding="utf-8")
        remotion.chmod(0o755)
        return remotion

    # red: the composition is the literal Explain (the film and clip cases), Film for every format
    # (the brainrot case), or Film for the format film alone (the clip case)
    def test_a_film_renders_composition_film(self):
        (self.out / "audio").mkdir()
        (self.out / "audio" / "s1.say.wav").write_bytes(b"clip")
        (self.out / "build" / "timeline.json").write_text(
            json.dumps({"scenes": [{"audio": "audio/s1.say.wav"}]}), encoding="utf-8")
        calls = self.tmp / "calls.json"
        remotion = self.fake_remotion(calls)
        for fmt, composition in (("film", "Film"), ("clip", "Film"), ("brainrot", "Explain")):
            with self.subTest(fmt=fmt):
                calls.unlink(missing_ok=True)
                run = run_functions(
                    self.tmp, ["fail", "now", "copy_clips", "stage_render"],
                    "RATIO_LIMIT=2.0 video_s=3.000 out=%s run=%s/run remotion=%s fmt=%s\n"
                    "stage_render\n" % (self.out, self.tmp, remotion, fmt))
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                lines = [line for line in run.stdout.splitlines() if line.startswith("render (")]
                self.assertEqual(len(lines), 1, run.stdout)
                self.assertTrue(lines[0].endswith(": ok"), lines)
                self.assertEqual(
                    [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()],
                    [["render", composition, "%s/video.mp4" % self.out, "--props",
                      "%s/build/timeline.json" % self.out]])

    # red: guard.mp4 is left (the base), or all of build/ goes (timeline.json with it), or
    # review/ itself goes
    def test_stale_guard_video_is_removed(self):
        (self.out / "video.mp4").write_bytes(b"old video")
        (self.out / "review").mkdir()
        (self.out / "review" / "still-01-intro.png").write_bytes(b"old still")
        (self.out / "build" / "guard.mp4").write_bytes(b"old guard video")
        (self.out / "build" / "timeline.json").write_text("{}", encoding="utf-8")
        run = run_functions(self.tmp, ["clear_stale"], "out=%s\nclear_stale\n" % self.out)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertFalse((self.out / "video.mp4").exists())
        self.assertFalse((self.out / "build" / "guard.mp4").exists())
        self.assertTrue((self.out / "review").is_dir())
        self.assertEqual(list((self.out / "review").iterdir()), [])
        self.assertTrue((self.out / "build" / "timeline.json").exists())


class SceneStageCase(unittest.TestCase):
    """stage_scene alone, against the real video/ of the skill (check_scene.py, build-timeline.mjs) and
    FAKE_TSC. Every path lies in the test's own temporary directory: out/ (script.json and the scene), run/
    (the example's src/film, as the run directory holds it from the skill, and node_modules, a link to the
    node_modules of ws/app, where the fake tsc is)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="render-scene-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.out = self.tmp / "out"
        self.out.mkdir()
        (self.out / "script.json").write_text(json.dumps(template_script()), encoding="utf-8")
        scene = self.out / "scene"
        shutil.copytree(SCENE_CLEAN, scene)
        (scene / ".DS_Store").write_bytes(b"\0Bud1")
        (scene / "script.gen.ts").write_text("// the author's copy\n", encoding="utf-8")
        self.run_dir = self.tmp / "run"
        self.film = self.run_dir / "src" / "film"
        self.film.mkdir(parents=True)
        (self.film / "Example.tsx").write_text("// the example\n", encoding="utf-8")
        (self.film / "script.gen.ts").write_text("// the example's names\n", encoding="utf-8")
        modules = self.tmp / "ws" / "app" / "node_modules"
        (modules / ".bin").mkdir(parents=True)
        self.tsc = modules / ".bin" / "tsc"
        self.tsc.write_text(FAKE_TSC, encoding="utf-8")
        self.tsc.chmod(0o755)
        (self.run_dir / "node_modules").symlink_to(modules)

    def stage(self, fmt="film", before=""):
        """The CompletedProcess of stage_scene for format `fmt`, run after the shell text `before`."""
        return run_functions(
            self.tmp, ["fail", "first_cause", "run_tool", "stage_scene"],
            "fmt=%(fmt)s out=%(out)s run=%(run)s script=%(out)s/script.json video=%(video)s tsc=%(tsc)s\n"
            "export FAKE_DIR=%(tmp)s\n%(before)s\nstage_scene\n"
            % {"fmt": fmt, "out": self.out, "run": self.run_dir, "video": EXPLAIN / "video",
               "tsc": self.tsc, "tmp": self.tmp, "before": before})

    def tsc_calls(self):
        """The calls of the fake tsc, one dict for each line of tsc.jsonl."""
        log = self.tmp / "tsc.jsonl"
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]

    def example_stays(self):
        """The example is still in src/film of the run directory."""
        return (self.film / "Example.tsx").is_file()

    def tsc_fails(self, output, code):
        """The CompletedProcess of stage_scene when the fake tsc prints `output` (None: nothing) and
        exits `code`."""
        before = "export FAKE_TSC_EXIT=%d" % code
        if output is not None:
            (self.tmp / "tsc.out").write_text(output, encoding="utf-8")
            before += " FAKE_TSC_OUTPUT=%s/tsc.out" % self.tmp
        return self.stage(before=before)

    # red: no removal of src/film before the copy (Example.tsx stays), a hidden file or the author's
    # script.gen.ts copied or counted, the names written before the copy (the author's copy wins) or
    # after tsc (tsc sees no script.gen.ts), tsc with another cwd or with an argument
    def test_a_clean_scene_is_copied_and_typed(self):
        done = self.stage()
        self.assertEqual((done.returncode, done.stdout), (0, "scene: ok (2 files)\n"), done.stderr)
        self.assertEqual(sorted(path.name for path in self.film.iterdir()),
                         ["Film.tsx", "Part.tsx", "script.gen.ts"])
        scene = self.out / "scene"
        for name in ("Film.tsx", "Part.tsx"):
            self.assertEqual((self.film / name).read_bytes(), (scene / name).read_bytes(), name)
        ids = " | ".join('"%s"' % s["id"] for s in template_script()["scenes"])
        generated = (self.film / "script.gen.ts").read_text(encoding="utf-8")
        self.assertEqual(generated.splitlines()[2:3], ["export type SceneId = %s;" % ids])
        self.assertEqual(self.tsc_calls(), [{
            "argv": [], "cwd": os.path.realpath(self.run_dir),
            "film": {"Film.tsx": (scene / "Film.tsx").read_text(encoding="utf-8"),
                     "Part.tsx": (scene / "Part.tsx").read_text(encoding="utf-8"),
                     "script.gen.ts": generated}}])

    # red: the stage runs for the format "film" only (a clip prints nothing and runs no tsc)
    def test_a_clip_has_the_scene_stage(self):
        script = template_script()
        script["format"] = "clip"
        (self.out / "script.json").write_text(json.dumps(script), encoding="utf-8")
        done = self.stage("clip")
        self.assertEqual((done.returncode, done.stdout), (0, "scene: ok (2 files)\n"), done.stderr)
        self.assertEqual(len(self.tsc_calls()), 1)
        ids = " | ".join('"%s"' % scene["id"] for scene in script["scenes"])
        generated = (self.film / "script.gen.ts").read_text(encoding="utf-8")
        self.assertEqual(generated.splitlines()[2:3], ["export type SceneId = %s;" % ids])

    # red: a pattern that no file matches (*.ts, for a scene with no script.gen.ts of the author's and no
    # other .ts file) is copied as it is: "scene: FAIL cannot copy the scene to <run>/src/film"
    def test_a_scene_with_no_ts_file(self):
        (self.out / "scene" / "script.gen.ts").unlink()
        done = self.stage()
        self.assertEqual((done.returncode, done.stdout), (0, "scene: ok (2 files)\n"), done.stderr)
        self.assertEqual(sorted(path.name for path in self.film.iterdir()),
                         ["Film.tsx", "Part.tsx", "script.gen.ts"])

    # red: the stage runs for every format (a brainrot run stops with "no scene directory")
    def test_another_format_has_no_scene_stage(self):
        shutil.rmtree(self.out / "scene")
        done = self.stage("brainrot")
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))
        self.assertTrue(self.example_stays())
        self.assertEqual(self.tsc_calls(), [])

    # red: src/film is emptied before the check has passed
    def test_no_scene_directory(self):
        shutil.rmtree(self.out / "scene")
        done = self.stage()
        gone = "no scene directory: %s/scene" % self.out
        self.assertEqual((done.returncode, done.stdout.splitlines()),
                         (1, ["scene: FAIL " + gone, "  FAIL " + gone]), done.stderr)
        self.assertTrue(self.example_stays())
        self.assertEqual(self.tsc_calls(), [])

    # red: the stage goes on after a failed check (the copy and tsc run), or its line is another cause
    # than the first
    def test_the_first_cause_is_the_stage_line(self):
        prepend(self.out / "scene", "Film.tsx", "// @ts-nocheck")
        line = append(self.out / "scene", "Film.tsx", "// href")
        done = self.stage()
        self.assertEqual((done.returncode, done.stdout.splitlines()), (1, [
            'scene: FAIL Film.tsx:1: token "@ts-nocheck"',
            '  FAIL Film.tsx:1: token "@ts-nocheck"',
            '  FAIL Film.tsx:%d: token "href"' % line]), done.stderr)
        self.assertEqual(self.tsc_calls(), [])

    # red: the status of the removal, of the mkdir or of cp is not read (the stage goes on to the names
    # and to tsc)
    def test_a_copy_that_fails(self):
        for command in ("cp", "rm", "mkdir"):
            with self.subTest(command=command):
                (self.tmp / "tsc.jsonl").unlink(missing_ok=True)
                done = self.stage(before="%s() { return 1; }" % command)
                self.assertEqual(
                    (done.returncode, done.stdout),
                    (1, "scene: FAIL cannot copy the scene to %s/src/film\n" % self.run_dir), done.stderr)
                self.assertEqual(self.tsc_calls(), [])

    # red: the status of the tool is not read (tsc runs), or the stage line has no "types:"
    def test_types_that_fail(self):
        script = template_script()
        script["format"] = "brainrot"
        (self.out / "script.json").write_text(json.dumps(script), encoding="utf-8")
        done = self.stage()
        self.assertEqual((done.returncode, done.stdout.splitlines()), (1, [
            "scene: FAIL types: script: --types needs a film script",
            "  FAIL script: --types needs a film script"]), done.stderr)
        self.assertEqual(self.tsc_calls(), [])

    # red: the first error line is the first line of the output (Version 5.9.3), more or fewer than
    # 20 lines follow, "src/film/" stays in the stage line or in the lines below it, the log goes to the
    # output directory
    def test_tsc_errors_are_cut_and_renamed(self):
        error = ("src/film/Film.tsx(60,39): error TS2345: Argument of type '\"no-such-scene\"' is not "
                 "assignable to parameter of type 'SceneId'.")
        lines = ["Version 5.9.3", error] + [
            "src/film/Part.tsx(%d,1): error TS6133: 'x%d' is declared but its value is never read." % (k, k)
            for k in range(1, 24)]
        self.assertEqual(len(lines), 25)
        done = self.tsc_fails("".join(line + "\n" for line in lines), 2)
        shown = [line.replace("src/film/", "scene/") for line in lines]
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertEqual(done.stdout.splitlines(),
                         ["scene: FAIL tsc: " + shown[1]] + ["  " + line for line in shown[:20]])
        self.assertEqual(sorted(path.name for path in self.out.iterdir()), ["scene", "script.json"])

    # red: a stage line with no cause (an empty "tsc: ", or the first line missed when the output has no
    # final line break)
    def test_tsc_without_an_error_line(self):
        for text in ("tsc: boom\n", "tsc: boom"):
            with self.subTest(output=text):
                done = self.tsc_fails(text, 1)
                self.assertEqual((done.returncode, done.stdout.splitlines()),
                                 (1, ["scene: FAIL tsc: tsc: boom", "  tsc: boom"]), done.stderr)
        with self.subTest(output=None):
            done = self.tsc_fails(None, 3)
            self.assertEqual((done.returncode, done.stdout), (1, "scene: FAIL tsc: exit 3\n"), done.stderr)


# The fake remotion of GuardStageCase: it appends one JSON line to $FAKE_DIR/pass.jsonl for each call (its
# argv and its cwd by real path), prints the file $FAKE_PASS_LOG when set, and exits $FAKE_PASS_EXIT (default
# 0).
FAKE_PASS = """#!/usr/bin/env python3
import json, os, sys
call = {"argv": sys.argv[1:], "cwd": os.path.realpath(os.getcwd())}
with open(os.path.join(os.environ["FAKE_DIR"], "pass.jsonl"), "a") as log:
    log.write(json.dumps(call) + "\\n")
if os.environ.get("FAKE_PASS_LOG"):
    with open(os.environ["FAKE_PASS_LOG"], encoding="utf-8") as text:
        sys.stdout.write(text.read())
    sys.stdout.flush()
sys.exit(int(os.environ.get("FAKE_PASS_EXIT", "0")))
"""

# The log of a pass that a frame fault ended: the CLI's own lines around the stage line, and below them a code
# frame of the source, which holds a stage line of its own.
FRAME_FAULT_LOG = (
    "Rendered 1/3\n"
    "An error occurred while rendering frame 47:\n"
    ' Error  guard: FAIL frame 47 (scene b): OFFCANVAS "x"\n'
    "at src/FilmStage.tsx:40\n"
    '40 \u2502   cancelRender(new Error(guardLine(frame, "guard: FAIL frame 1 (scene z): y", faults)));\n')

# The log of a pass that a mark error ended: the message of marks.ts is the line after the CLI's frame line, and
# a code frame of the source below it repeats the template of that message, "MARK scene " and all.
MARK_FAULT_LOG = (
    "Rendered 1/3\n"
    "An error occurred while rendering frame 12:\n"
    ' Error  MARK scene b: word "zebra" is not in the narration\n'
    "at src/kit/marks.ts:35\n"
    '35 \u2502 const markError = (scene: string, why: string): Error => new Error(`MARK scene ${scene}: ${why}`);\n')


class GuardStageCase(unittest.TestCase):
    """stage_guard alone (with copy_clips, which it calls), against FAKE_PASS. Every path lies in the test's
    own temporary directory: out/ (build/timeline.json with the check frames 12 and 47 and 89, and the clip
    audio/a.say.wav of its one scene), run/ (the run directory) and remotion (the fake)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="render-guard-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.out = self.tmp / "out"
        (self.out / "build").mkdir(parents=True)
        (self.out / "audio").mkdir()
        (self.out / "audio" / "a.say.wav").write_bytes(b"clip")
        self.timeline = self.out / "build" / "timeline.json"
        self.timeline.write_text(json.dumps({
            "scenes": [{"id": "a", "audio": "audio/a.say.wav"}], "minText": 14,
            "checkFrames": [{"frame": 12, "scene": "a", "still": "s1"},
                            {"frame": 47, "scene": "b", "still": "s1"},
                            {"frame": 89, "scene": "b", "still": "end"}]}), encoding="utf-8")
        self.run_dir = self.tmp / "run"
        self.run_dir.mkdir()
        self.remotion = self.tmp / "remotion"
        self.remotion.write_text(FAKE_PASS, encoding="utf-8")
        self.remotion.chmod(0o755)

    def guard(self, fmt="film", log=None, code=0):
        """The CompletedProcess of stage_guard for format `fmt`, when the fake pass prints the text `log`
        (None: nothing) and exits `code`."""
        before = "export FAKE_DIR=%s FAKE_PASS_EXIT=%d\n" % (self.tmp, code)
        if log is not None:
            (self.tmp / "pass.log").write_text(log, encoding="utf-8")
            before += "export FAKE_PASS_LOG=%s\n" % (self.tmp / "pass.log")
        return run_functions(
            self.tmp, ["fail", "copy_clips", "stage_guard"],
            "fmt=%(fmt)s out=%(out)s run=%(run)s remotion=%(remotion)s\n%(before)sstage_guard\n"
            % {"fmt": fmt, "out": self.out, "run": self.run_dir, "remotion": self.remotion, "before": before})

    def passes(self):
        """The calls of the fake pass, one dict for each line of pass.jsonl."""
        log = self.tmp / "pass.jsonl"
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]

    # red: a comma list of frames (an image sequence, which an output named guard.mp4 refuses), the cwd of
    # the caller in place of the run directory, no --concurrency=1, or the clip not copied into the run
    def test_the_pass_renders_the_check_frames_in_the_run_directory(self):
        done = self.guard()
        self.assertEqual((done.returncode, done.stdout), (0, "guard (3 frames): ok\n"), done.stderr)
        self.assertEqual(self.passes(), [{
            "argv": ["render", "Film", "%s/build/guard.mp4" % self.out, "--frames=12-12,47-47,89-89",
                     "--concurrency=1", "--muted", "--props", "%s/build/timeline.json" % self.out],
            "cwd": os.path.realpath(self.run_dir)}])
        self.assertTrue((self.run_dir / "public" / "audio" / "a.say.wav").is_file())

    # red: the pass runs for every format
    def test_another_format_has_no_guard_stage(self):
        done = self.guard("brainrot")
        self.assertEqual((done.returncode, done.stdout), (0, ""), done.stderr)
        self.assertEqual(self.passes(), [])

    # red: the last marker line wins (the code frame's line z), " Error  " is kept before the marker, or
    # log lines follow the stage line
    def test_a_frame_fault_is_the_stage_line(self):
        done = self.guard(log=FRAME_FAULT_LOG, code=1)
        self.assertEqual((done.returncode, done.stdout),
                         (1, 'guard: FAIL frame 47 (scene b): OFFCANVAS "x"\n'), done.stderr)

    # red: the log is read only after a non-zero exit (the code of the first guard stage): a cancel that the
    # CLI reads late or never gives exit 0, and the film passes
    def test_a_marker_fails_even_after_exit_0(self):
        done = self.guard(log=FRAME_FAULT_LOG, code=0)
        self.assertEqual((done.returncode, done.stdout),
                         (1, 'guard: FAIL frame 47 (scene b): OFFCANVAS "x"\n'), done.stderr)

    # red: the mark error is not a marker (the stage line is the exit line of the pass), "MARK" is kept in the line,
    # or the last marker line wins (the code frame's "MARK scene ")
    def test_a_mark_error_is_the_stage_line(self):
        done = self.guard(log=MARK_FAULT_LOG, code=1)
        self.assertEqual((done.returncode, done.stdout),
                         (1, 'guard: FAIL mark: scene b: word "zebra" is not in the narration\n'), done.stderr)

    # red: no tail of the log, its head in place of its tail, or no exit code
    def test_any_other_failure_shows_the_log_tail(self):
        log = "".join("line %d\n" % n for n in range(1, 51))
        done = self.guard(log=log, code=3)
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertEqual(
            done.stdout.splitlines(),
            ["guard: FAIL remotion render exit 3 (log %s/build/guard.log)" % self.out]
            + ["  line %d" % n for n in range(11, 51)])
        self.assertEqual((self.out / "build" / "guard.log").read_text(encoding="utf-8"), log)

    # red: a pass with an empty --frames= (no check frames), or a traceback in place of the line
    def test_a_timeline_that_cannot_be_read(self):
        cases = (
            ("no timeline.json", lambda: self.timeline.unlink()),
            ("not JSON", lambda: self.timeline.write_text("{not json", encoding="utf-8")),
            ("no checkFrames", lambda: self.timeline.write_text('{"scenes": []}', encoding="utf-8")),
            ("empty checkFrames", lambda: self.timeline.write_text('{"checkFrames": []}', encoding="utf-8")),
            ("a frame of -1", lambda: self.timeline.write_text(
                '{"checkFrames": [{"frame": 12}, {"frame": -1}]}', encoding="utf-8")),
        )
        for name, edit in cases:
            with self.subTest(case=name):
                edit()
                done = self.guard()
                self.assertEqual((done.returncode, done.stdout, done.stderr),
                                 (1, "guard: FAIL cannot read %s\n" % self.timeline, ""))
                self.assertEqual(self.passes(), [])

    # red: the read ignores minText (a timeline with no floor reaches the pass: Remotion merges the props over
    # the default props of the Film composition, which hold minText 14, so the pass measures a clip at the
    # film floor with no message), takes any value that is present (a string, true, null: with null the
    # size rule is off), takes 0 or less, or refuses a fractional floor. `true` is no number, though it is
    # an int in Python
    def test_a_timeline_without_a_floor_cannot_be_read(self):
        def with_min_text(*value):
            def edit():
                timeline = json.loads(self.timeline.read_text(encoding="utf-8"))
                timeline.pop("minText", None)
                if value:
                    timeline["minText"] = value[0]
                self.timeline.write_text(json.dumps(timeline), encoding="utf-8")
            return edit

        cases = (
            ("minText removed", with_min_text()),
            ('minText "14"', with_min_text("14")),
            ("minText true", with_min_text(True)),
            ("minText null", with_min_text(None)),
            ("minText 0", with_min_text(0)),
            ("minText -1", with_min_text(-1)),
        )
        for name, edit in cases:
            with self.subTest(case=name):
                edit()
                done = self.guard()
                self.assertEqual((done.returncode, done.stdout, done.stderr),
                                 (1, "guard: FAIL cannot read %s\n" % self.timeline, ""))
                self.assertEqual(self.passes(), [])
        with self.subTest(case="minText 14.5"):
            with_min_text(14.5)()
            done = self.guard()
            self.assertEqual((done.returncode, done.stdout), (0, "guard (3 frames): ok\n"), done.stderr)
            self.assertEqual(len(self.passes()), 1)

    # red: the failure of the copy is ignored and the pass runs (and a stage line follows), or the line
    # names no clip
    def test_a_clip_that_cannot_be_copied(self):
        (self.out / "audio" / "a.say.wav").unlink()
        done = self.guard()
        self.assertEqual((done.returncode, done.stdout),
                         (1, "guard: FAIL cannot copy %s/audio/a.say.wav\n" % self.out), done.stderr)
        self.assertEqual(self.passes(), [])


# What build-timeline.mjs of SceneRunCase does first: --types <script> <out.ts> writes "// generated" to
# <out.ts>. The text of RUN_FAKES follows, for the other calls (--check, the timeline).
FAKE_TYPES = (
    'import { writeFileSync as writeTypes } from "node:fs";\n'
    'if (process.argv[2] === "--types") {\n'
    '  writeTypes(process.argv[4], "// generated\\n");\n'
    '  process.exit(0);\n'
    '}\n')

# The timeline that build-timeline.mjs of SceneRunCase writes: that of RUN_FAKES, with the minText of a film
# (the guard refuses a timeline with none) and the checkFrames of a film: frame 3 (the middle of sentence 1)
# and frame 89 (the last frame) of scene s1.
FAKE_CHECK_FRAMES = (
    ', minText: 14, checkFrames: [{frame: 3, scene: "s1", still: "s1"}, {frame: 89, scene: "s1", still: "end"}]')
FAKE_FILM_TIMELINE = RUN_FAKES["skill/video/build-timeline.mjs"].replace(
    'background: {kind: "generated"}', 'background: {kind: "generated"}' + FAKE_CHECK_FRAMES)

# The temp tree of SceneRunCase, by path under FAKE_DIR: RUN_FAKES, and on top of it the fake tsc, the
# workspace fake that also puts it beside the fake CLI in the shared packages (its commands follow its ok
# line, which render.sh holds back), the real check_scene.py, the build-timeline.mjs above (FAKE_TYPES, then
# FAKE_FILM_TIMELINE), and a file of the example in src/film of the skill.
SCENE_RUN_FAKES = {
    **RUN_FAKES,
    "tsc": FAKE_TSC,
    "skill/scripts/video-workspace.sh":
        RUN_FAKES["skill/scripts/video-workspace.sh"] + 'cp "$FAKE_DIR/tsc" "$nm/.bin/tsc"\n',
    "skill/video/check_scene.py": CHECK_SCENE.read_text(encoding="utf-8"),
    "skill/video/build-timeline.mjs": FAKE_TYPES + FAKE_FILM_TIMELINE,
    "skill/video/src/film/Example.tsx": "// the example\n",
}


class SceneRunCase(RunHarness, unittest.TestCase):
    """A film run of the copy of render.sh against SCENE_RUN_FAKES, in the workspace <tmp>/w s. out/scene
    is a copy of SCENE_CLEAN. No workspace, no render, no install."""

    fakes = SCENE_RUN_FAKES

    def setUp(self):
        super().setUp()
        self.tsc_log = self.tmp / "tsc.jsonl"
        self.plant_scene()

    def plant_scene(self):
        """out/scene as a fresh copy of SCENE_CLEAN, whatever it was."""
        shutil.rmtree(self.out / "scene", ignore_errors=True)
        shutil.copytree(SCENE_CLEAN, self.out / "scene")

    def start(self, fmt="brainrot", engine="say", **env):
        """RunHarness.start, once the log and the end mark of the fake tsc of an earlier start are gone."""
        for name in ("tsc.jsonl", "tsc.end"):
            (self.tmp / name).unlink(missing_ok=True)
        return super().start(fmt, engine, **env)

    def tsc_calls(self):
        """The calls of the fake tsc, one dict for each line of tsc.jsonl."""
        if not self.tsc_log.exists():
            return []
        return [json.loads(line) for line in self.tsc_log.read_text(encoding="utf-8").splitlines()]

    def wait_for_tsc(self, proc):
        """Return once the fake tsc has logged its call (it sleeps after that); the test fails if
        render.sh exits first or no call comes in 20 s."""
        deadline = time.monotonic() + 20
        while not (self.tsc_log.exists() and self.tsc_log.read_text(encoding="utf-8").endswith("\n")):
            if proc.poll() is not None or time.monotonic() > deadline:
                self.fail("tsc did not run:\n" + "".join(self.output()))
            time.sleep(0.05)

    # red: the scene stage is not called (ten lines), or it is called after the narration (the third line
    # is not the scene), or for every format (a brainrot run prints a scene line and runs tsc); the guard
    # stage is not called (ten lines, no guard), or for every format (a brainrot run prints a guard line
    # and calls the CLI twice)
    def test_a_film_run_prints_eleven_stage_lines(self):
        run = self.finish(self.start("film"))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        lines = stage_lines(run.stdout)
        self.assertEqual([STAGE_LINE.match(line).group(1) for line in lines],
                         ["script", "workspace", "scene", "narration", "timeline", "guard", "render",
                          "container", "sync", "stills", "transcript"], run.stdout)
        self.assertEqual(lines[2], "scene: ok (2 files)")
        self.assertEqual(lines[5], "guard (2 frames): ok")
        run = self.finish(self.start("brainrot"))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual([line for line in stage_lines(run.stdout) if line.startswith("scene")], [],
                         run.stdout)
        self.assertFalse(self.tsc_log.exists())
        self.assertEqual([line for line in stage_lines(run.stdout) if line.startswith("guard")], [],
                         run.stdout)
        self.assertEqual(len(self.cli_calls()), 1, run.stdout)

    # red: a clip takes the brainrot path in one place: no scene stage (ten lines, no tsc), no guard
    # stage (ten lines, one CLI call), or composition Explain in the render
    def test_a_clip_run_prints_eleven_stage_lines(self):
        run = self.finish(self.start("clip"))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        lines = stage_lines(run.stdout)
        self.assertEqual([STAGE_LINE.match(line).group(1) for line in lines],
                         ["script", "workspace", "scene", "narration", "timeline", "guard", "render",
                          "container", "sync", "stills", "transcript"], run.stdout)
        self.assertEqual(lines[2], "scene: ok (2 files)")
        self.assertEqual(lines[5], "guard (2 frames): ok")
        self.assertEqual([call["argv"][:2] for call in self.cli_calls()],
                         [["render", "Film"], ["render", "Film"]], run.stdout)

    # red: render.sh keeps an engine of its own when the command line has none (the check gets --engine
    # kokoro, so the Russian run narrates with it), or passes the check's engine to one of the two stages
    # that need it and not to the other (the workspace fetches the model for silero, narrate.sh runs it)
    def test_a_film_run_without_engine_passes_the_checked_engine(self):
        run = self.finish(self.start("film", engine=None, FAKE_CHECK_ENGINE="silero"))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        out = os.path.realpath(self.out)
        self.assertEqual(self.tool_calls("check"), [["--check", "%s/script.json" % out]])
        self.assertEqual(self.tool_calls("workspace"), [["--engine", "silero"]])
        self.assertEqual(self.tool_calls("narrate"),
                         [["%s/script.json" % out, "%s/audio" % out, "--engine", "silero"]])

    # red: STAGES holds the name of a stage that only a film run has (scene, and guard). The gated
    # BrainrotRenderCase makes this same comparison of a real brainrot run with STAGES; here it is
    # made on every run, through the fakes
    def test_a_brainrot_run_prints_exactly_the_stages_of_STAGES(self):
        run = self.finish(self.start("brainrot"))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual([line.split(":")[0].split(" ")[0] for line in stage_lines(run.stdout)],
                         list(STAGES), run.stdout)

    # red: the scene is copied under <ws>/app (decision 12), tsc runs in the app, or the removal of
    # src/film reaches the shared packages; the guard pass runs in the app, renders its frames as a
    # comma list (an image sequence, which an output named guard.mp4 refuses), or runs before the clips
    # are copied (the renderer fetches the clip of each audio of a frame, --muted or not)
    def test_the_render_draws_the_copied_scene(self):
        proc = self.start("film")
        run = self.finish(proc)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        out = os.path.realpath(self.out)
        [guard, call] = self.cli_calls()
        self.assertEqual(guard["argv"], [
            "render", "Film", "%s/build/guard.mp4" % out, "--frames=3-3,89-89", "--concurrency=1", "--muted",
            "--props", "%s/build/timeline.json" % out])
        self.assertEqual(guard["audio"], ["s1.say.wav"])
        self.assertEqual(call["argv"][:3], ["render", "Film", "%s/video.mp4" % out])
        [typed] = self.tsc_calls()
        for drawn in (guard, call):
            self.assertEqual([path for path in drawn["files"] if path.startswith("src/film/")],
                             ["src/film/Film.tsx", "src/film/Part.tsx", "src/film/script.gen.ts"])
            self.assertEqual(drawn["cwd"], typed["cwd"])
        self.assertRegex(call["cwd"], self.run_pattern(os.path.realpath(self.runs), proc.pid))
        self.assertEqual(names(self.ws / "app"), ["node_modules"])
        self.assertEqual(names(self.shared), [".bin", "sentinel.txt"])
        self.assertEqual(names(self.runs), [])

    # red: the stage comes after the narration (the synthesis has run), or the run directory stays after
    # a FAIL
    def test_a_scene_fail_stops_before_any_synthesis(self):
        out = os.path.realpath(self.out)
        tsc_output = self.tmp / "tsc.out"
        tsc_output.write_text("src/film/Film.tsx(1,1): error TS1005: x\n", encoding="utf-8")
        cases = (
            ("a refused token", lambda scene: prepend(scene, "Film.tsx", "// @ts-nocheck"), {},
             'scene: FAIL Film.tsx:1: token "@ts-nocheck"'),
            ("no scene directory", shutil.rmtree, {}, "scene: FAIL no scene directory: %s/scene" % out),
            ("a tsc error", lambda scene: None,
             {"FAKE_TSC_EXIT": "2", "FAKE_TSC_OUTPUT": str(tsc_output)},
             "scene: FAIL tsc: scene/Film.tsx(1,1): error TS1005: x"),
        )
        for name, edit, env, last in cases:
            with self.subTest(case=name):
                self.plant_scene()
                edit(self.out / "scene")
                run = self.finish(self.start("film", **env))
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertEqual(stage_lines(run.stdout),
                                 ["script: ok (1 scenes)", "workspace: ok %s" % self.ws, last], run.stdout)
                self.assertEqual(self.tool_calls("narrate"), [])
                self.assertFalse((self.out / "audio").exists())
                self.assertEqual(self.cli_calls(), [])
                self.assertEqual(names(self.runs), [])

    # red: tsc in a subshell without exec: render.sh exits at once and removes the run directory while
    # tsc, which outlives the signal, goes on in it, and the late write of tsc makes the directory again
    def test_render_sh_waits_for_a_tsc_that_outlives_the_signal(self):
        end = self.tmp / "tsc.end"
        for sig in (signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=sig.name):
                proc = self.start("film", FAKE_TSC_SLEEP="30", FAKE_TSC_OUTLIVE="1")
                self.wait_for_tsc(proc)
                os.killpg(proc.pid, sig)
                run = self.finish(proc, timeout=10)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertEqual([line for line in run.stdout.splitlines() if "FAIL" in line], [], run.stdout)
                # a render.sh that did not wait has exited before tsc: wait for the end of tsc
                deadline = time.monotonic() + 10
                while not end.exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertTrue(end.exists(), "the fake tsc did not end")
                self.assertEqual(names(self.runs), [])
                self.assertTrue((self.shared / "sentinel.txt").exists())

    # red: the guard pass in a subshell without exec: render.sh exits at once and removes the run directory
    # while the CLI, which outlives the signal, goes on in it, and its late write makes the directory again
    def test_render_sh_waits_for_a_guard_pass_that_outlives_the_signal(self):
        end = self.tmp / "remotion.end"
        for sig in (signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=sig.name):
                end.unlink(missing_ok=True)
                proc = self.start("film", FAKE_REMOTION_SLEEP="30", FAKE_REMOTION_OUTLIVE="1")
                self.wait_for_cli(proc)
                os.killpg(proc.pid, sig)
                run = self.finish(proc, timeout=10)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertEqual([line for line in run.stdout.splitlines() if "FAIL" in line], [], run.stdout)
                # a render.sh that did not wait has exited before the CLI: wait for the CLI's end
                deadline = time.monotonic() + 10
                while not end.exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertTrue(end.exists(), "the fake CLI did not end")
                [guard] = self.cli_calls()
                self.assertIn("--frames=3-3,89-89", guard["argv"])
                self.assertEqual(names(self.runs), [])
                self.assertTrue((self.shared / "sentinel.txt").exists())


@unittest.skipUnless(E2E, E2E_REASON)
class FilmRenderCase(unittest.TestCase):
    def rendered(self):
        """The output directory and the run of the template render, as (out, run), once the run is seen
        to exit 0."""
        out, run = render_film()
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return out, run

    # red: the scene stage counts the author's script.gen.ts (scene: ok (6 files)) or does not run (ten
    # lines), the guard stage does not run (ten lines) or counts other frames, a film rendered as Explain
    # (the render stage fails: render: FAIL remotion render exit 1), or another stage of the film path fails
    # or prints another line
    def test_film_prints_eleven_ok_lines(self):
        _, run = self.rendered()
        self.assertNotIn("FAIL", run.stdout)
        lines = stage_lines(run.stdout)
        self.assertEqual(len(lines), len(ORDER), run.stdout)
        for line, pattern in zip(lines, ORDER):
            self.assertRegex(line, "^%s$" % pattern)

    # red: the helper drops EXPLAIN_VIDEO_WORKSPACE and the render goes to the default workspace.
    # Not run red (that is a render in a workspace this branch must not use): E2EHelperCase of
    # test_render is the red-first proof of the helper, this case binds the film render to it.
    def test_render_used_the_callers_workspace(self):
        _, run = render_film()
        self.assertEqual(stage_lines(run.stdout)[1:2], ["workspace: ok %s" % workspace()],
                         run.stdout + run.stderr)

    # red: stills by scene and cue (the names of a brainrot run), a missing end still of the last scene,
    # or a sentence lost (the expected names come from the template, not from the render's own
    # timeline.json)
    def test_stills_are_the_check_frames(self):
        out, run = self.rendered()
        expected = []
        for n, scene in enumerate(TEMPLATE_SCENES, 1):
            sentences = split_sentences(scene["narration"])
            expected += ["still-%02d-%s-s%d.png" % (n, scene["id"], k) for k in range(1, len(sentences) + 1)]
            expected.append(end_still(n, scene))
        review = out / "review"
        self.assertEqual(sorted(p.name for p in review.iterdir()), sorted(expected))
        for name in expected:
            self.assertGreater((review / name).stat().st_size, 0, name)
        stills = [line for line in stage_lines(run.stdout) if line.startswith("stills (")]
        self.assertEqual(stills[0].split(")")[0], "stills (%d" % len(expected))

    # red: composition Film takes the size of another format (1080x1920)
    def test_container_is_landscape(self):
        out, _ = self.rendered()
        self.assertEqual(video_size(out / "video.mp4"), "1280x720")

    # red: the transcript stage passes --background (a Background row), leaves the Narrator row
    # "pending", writes a Format row, or loses a scene of the template
    def test_transcript_is_the_film_page(self):
        out, _ = self.rendered()
        page = (out / "index.html").read_text(encoding="utf-8")
        sections = re.findall(r'<section id="([^"]*)">\s*<h2>([^<]*)</h2>', page)
        ids = [scene["id"] for scene in TEMPLATE_SCENES]
        self.assertEqual(sections, [(sid, sid) for sid in ids])
        self.assertNotIn("<dt>Format</dt>", page)
        self.assertNotIn("<dt>Background</dt>", page)
        self.assertIn("<dt>Narrator</dt><dd>say</dd>", page)
        run = subprocess.run([str(VERIFY_SH), str(out / "index.html")], capture_output=True, text=True,
                             timeout=300)
        self.assertEqual(run.stdout.splitlines(), ["self-contained: ok", "citations: ok", "prose: ok"],
                         run.stdout + run.stderr)

    # red: render.sh narrates a film at the brainrot speed 1.2, or not in sentence mode
    def test_film_speaks_at_speed_1(self):
        out, _ = self.rendered()
        sidecars = sorted(p.name for p in (out / "audio").glob("*.say.txt"))
        self.assertEqual(sidecars, sorted("%s.say.txt" % scene["id"] for scene in TEMPLATE_SCENES))
        for name in sidecars:
            self.assertIn("\nspeed=1.0\nmode=sentences\n", (out / "audio" / name).read_text(encoding="utf-8"),
                          name)

    # red: FilmStage starts each narration clip at the scene start and not leadFrames later; the sync
    # stage passes that (6 frames are inside its 0.25 s tolerance), and every mark is 0.2 s late
    # against the voice
    def test_voice_starts_at_the_lead(self):
        out, _ = self.rendered()
        timeline = json.loads((out / "build" / "timeline.json").read_text(encoding="utf-8"))
        fps = timeline["fps"]
        track = voiced_windows(str(out / "build" / "rendered-audio.wav"))
        for scene in timeline["scenes"]:
            with self.subTest(scene=scene["id"]):
                own = first_voiced(voiced_windows(str(out / "audio" / ("%s.say.wav" % scene["id"]))), 0.0)
                heard = first_voiced(track, scene["from"] / fps)
                self.assertIsNotNone(own)
                self.assertIsNotNone(heard)
                self.assertLessEqual(abs(heard - (scene["leadFrames"] / fps + own)), LEAD_TOLERANCE,
                                     "voice at %.2f s, expected %.2f s" % (heard, scene["leadFrames"] / fps + own))

    # red: fault 3 of spec 8.4, a scene that changes nothing: its -end still equals the -end still of
    # the scene before it
    def test_each_scene_changes_the_picture(self):
        out, _ = self.rendered()
        review = out / "review"
        for n in range(2, SCENES + 1):
            before, after = end_still(n - 1, TEMPLATE_SCENES[n - 2]), end_still(n, TEMPLATE_SCENES[n - 1])
            with self.subTest(still=after):
                changed = differing_pixels(review / before, review / after, 0, 1280, 0, 720)
                self.assertGreater(changed, CHANGED_PIXELS, "%s against %s" % (after, before))


@unittest.skipUnless(E2E, E2E_REASON)
class ScenePlantCase(unittest.TestCase):
    """The stage plants of spec 9.2: film_output(edit), the output directory of FilmRenderCase with one
    edit, rendered by render.sh --engine say. Each stops with its line before any synthesis: render.sh
    exits 1, no stage line is the narration's, and out/ holds no audio/ and no video.mp4."""

    def stops(self, edit):
        """(out, run) of the render of film_output(edit), once render.sh is seen to exit 1."""
        out = film_output(edit)
        run = render_output(out)
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        return out, run

    def assertNoSynthesis(self, out, run):
        """No stage line of `run` is the narration's, and `out` holds no audio/ and no video.mp4."""
        self.assertEqual([line for line in stage_lines(run.stdout) if line.startswith("narration")], [],
                         run.stdout)
        self.assertFalse((out / "audio").exists())
        self.assertFalse((out / "video.mp4").exists())

    def line_of(self, path, text):
        """The number (from 1) of the first line of the file `path` that holds `text`; the test fails
        if no line does."""
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if text in line:
                return number
        self.fail("%s holds no %s" % (path, text))

    def ok_before_the_scene(self):
        """The stage lines of the template before the scene stage: the script and the workspace."""
        return ["script: ok (%d scenes)" % SCENES, "workspace: ok %s" % workspace()]

    def unknown_mark(self, out):
        """The edit of the mark plant: the first at("subject") of scene/Film.tsx becomes
        at("no-such-scene"); the test fails if the scene has no at("subject")."""
        film = out / "scene" / "Film.tsx"
        text = film.read_text(encoding="utf-8")
        self.assertIn('at("subject")', text)
        film.write_text(text.replace('at("subject")', 'at("no-such-scene")', 1), encoding="utf-8")

    # red: the script stage does not run the cite check before the workspace (the run goes on to the scene
    # stage and the synthesis)
    def test_a_changed_cite_stops_at_the_script_stage(self):
        cite = template_script()["scenes"][0]["cites"][0]

        def change_a_word(out):
            path = out / "script.json"
            script = json.loads(path.read_text(encoding="utf-8"))
            changed = script["scenes"][0]["cites"][0]
            words = changed["snippet"].split(" ")
            self.assertNotEqual(words[1], "zebra")
            words[1] = "zebra"
            changed["snippet"] = " ".join(words)
            path.write_text(json.dumps(script, indent=2), encoding="utf-8")

        out, run = self.stops(change_a_word)
        self.assertEqual(stage_lines(run.stdout), ["script: FAIL citations: FAIL 1 failure(s)"], run.stdout)
        self.assertIn("    cite 1 (%s:%s): snippet not found on that line" % (cite["path"], cite["line"]),
                      run.stdout.splitlines())
        self.assertNoSynthesis(out, run)

    # red: the scene is checked and not copied (tsc reads the example in src/film/ and passes, and the run
    # goes on to the synthesis), or the line keeps the src/film/ of the run directory
    def test_a_mark_on_an_unknown_scene_stops_at_tsc(self):
        out, run = self.stops(self.unknown_mark)
        line = self.line_of(out / "scene" / "Film.tsx", 'at("no-such-scene")')
        lines = stage_lines(run.stdout)
        self.assertEqual(lines[:-1], self.ok_before_the_scene(), run.stdout)
        self.assertRegex(lines[-1], r"""^scene: FAIL tsc: scene/Film\.tsx\(%d,\d+\): error TS2345: """
                                    r""".*"no-such-scene".*'SceneId'\.$""" % line)
        self.assertNoSynthesis(out, run)

    # red: the stage does not run check_scene.py (tsc passes this scene, and the run goes on to the
    # synthesis)
    def test_a_used_import_of_another_package_stops_at_the_check(self):
        anchor = 'import { useCurrentFrame } from "remotion";'

        def import_paths(out):
            film = out / "scene" / "Film.tsx"
            text = film.read_text(encoding="utf-8")
            self.assertIn("useCurrentFrame()", text)
            lines = text.split("\n")
            self.assertIn(anchor, lines)
            lines.insert(lines.index(anchor) + 1, 'import { getLength } from "@remotion/paths";')
            text = "\n".join(lines).replace(
                "useCurrentFrame()", 'useCurrentFrame() + getLength("M 0 0 L 1 1") * 0', 1)
            film.write_text(text, encoding="utf-8")

        out, run = self.stops(import_paths)
        line = self.line_of(out / "scene" / "Film.tsx", 'from "@remotion/paths"')
        self.assertEqual(stage_lines(run.stdout), self.ok_before_the_scene() + [
            'scene: FAIL Film.tsx:%d: import from "@remotion/paths"' % line], run.stdout)
        self.assertNoSynthesis(out, run)

    # red: the token list has no "@ts-nocheck" (tsc checks nothing, and the unknown mark reaches the
    # synthesis and the render), or the stage does not run check_scene.py
    def test_ts_nocheck_stops_at_the_check(self):
        def nocheck(out):
            self.unknown_mark(out)
            prepend(out / "scene", "Film.tsx", "// @ts-nocheck")

        out, run = self.stops(nocheck)
        self.assertEqual(stage_lines(run.stdout), self.ok_before_the_scene() + [
            'scene: FAIL Film.tsx:1: token "@ts-nocheck"'], run.stdout)
        self.assertNoSynthesis(out, run)


# The planted film of spec 9.2, drawn at every frame: five labels that the guard names (a label off the
# canvas, one of 10 px, one of 20 px in a group scaled by half, two on one spot) and one that it does not (a
# label off the canvas in a group of opacity 0). PLANT_FAULTS is what the guard says of them, in their order.
PLANT = """import type { ReactElement } from "react";
import { Sans } from "../kit";

export function Plant(): ReactElement {
  return (
    <g>
      <Sans x={1400} y={700} size={20} text="off canvas" />
      <Sans x={40} y={700} size={10} text="ten px" />
      <g transform="scale(0.5)">
        <Sans x={400} y={1400} size={20} text="half scale" />
      </g>
      <Sans x={600} y={700} size={20} text="twin one" />
      <Sans x={600} y={700} size={20} text="twin two" />
      <g opacity={0}>
        <Sans x={1400} y={660} size={20} text="hidden" />
      </g>
    </g>
  );
}
"""
PLANT_FAULTS = ('OFFCANVAS "off canvas"; SMALLTEXT 10.0 px "ten px"; SMALLTEXT 10.0 px "half scale"; '
                'OVERLAP "twin one" | "twin two"')

# A label off the canvas at one frame only: `last`, which the test sets to the last frame of the film.
LATE = """import type { ReactElement } from "react";
import { useCurrentFrame } from "remotion";
import { Sans } from "../kit";

export function Late(props: { last: number }): ReactElement | null {
  return useCurrentFrame() === props.last ? <Sans x={1400} y={700} size={20} text="late" /> : null;
}
"""

# A label of 20 px with a <tspan> of 10 px inside it, drawn at every frame as the kit's Sans draws a label
# (the same colour and font; only the size of the tspan differs), at a spot that no text of the example
# covers at the first check frame.
TINY = """import type { ReactElement } from "react";
import { C, SANS } from "../kit";

export function Tiny(): ReactElement {
  return (
    <text x={40} y={700} fontSize={20} fontFamily={SANS} fill={C.text}>
      big <tspan fontSize={10}>tiny</tspan>
    </text>
  );
}
"""


@unittest.skipUnless(E2E, E2E_REASON)
class GuardPlantCase(unittest.TestCase):
    """The browser rules of the guard (spec 7.3), proven on planted films: film_output(edit), the output
    directory of FilmRenderCase with one edit, rendered by render.sh --engine say. Three plants add a scene
    file to it by add_to_film (the planted film, a label off the canvas at the last frame alone, a label with
    a small <tspan>); the mark plant and the clip plant add none: the first changes the word of a mark in
    Film.tsx, the second the format of script.json. Each stops at the guard: render.sh exits 1 after the
    timeline, with no render line and no video.mp4.
    FilmRenderCase, with the same output directory and no edit, is their control. The expected lines come
    from the plants and the run's own checkFrames."""

    def stops_at_the_guard(self, edit, added=1):
        """(out, last stage line, checkFrames of out/build/timeline.json) of the render of
        film_output(edit), once render.sh is seen to stop at the guard. `added` is the number of scene files
        that `edit` adds to the example (add_to_film adds one; a plant that only changes Film.tsx adds
        none): the scene stage counts SCENE_FILES plus that."""
        out = film_output(edit)
        run = render_output(out)
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        lines = stage_lines(run.stdout)
        self.assertEqual(len(lines), 6, run.stdout)
        # ORDER[:5], with the scene stage counting the files that the edit added
        before = ORDER[:2] + [r"scene: ok \(%d files\)" % (SCENE_FILES + added)] + ORDER[3:5]
        for line, pattern in zip(lines, before):
            self.assertRegex(line, "^%s$" % pattern)
        self.assertEqual([line for line in lines if line.startswith("render")], [], run.stdout)
        self.assertFalse((out / "video.mp4").exists())
        self.assertTrue((out / "build" / "guard.log").exists())
        timeline = json.loads((out / "build" / "timeline.json").read_text(encoding="utf-8"))
        return out, lines[-1], timeline["checkFrames"]

    # red: no guard stage (the run exits 0), a measure that ignores the scale of a group (no SMALLTEXT of
    # "half scale") or its opacity (an OFFCANVAS of "hidden"), or faults in another order. Three runs in a
    # row give the same line: the first frame with a fault is the same in every run
    def test_the_planted_film_fails_at_its_first_check_frame(self):
        lines = []
        for _ in range(3):
            _, last, check_frames = self.stops_at_the_guard(
                lambda out: add_to_film(self, out, "Plant", PLANT, "<Plant />"))
            self.assertEqual(last, "guard: FAIL frame %d (scene subject): %s"
                             % (check_frames[0]["frame"], PLANT_FAULTS))
            lines.append(last)
        self.assertEqual(len(set(lines)), 1, lines)

    # red: the pass ends before the cancel of its last frame is read (the run goes on to the render)
    def test_a_fault_at_the_last_check_frame_fails(self):
        out, last, check_frames = self.stops_at_the_guard(
            lambda out: add_to_film(self, out, "Late", LATE, '<Late last={at.end("handoff") - 1} />'))
        timeline = json.loads((out / "build" / "timeline.json").read_text(encoding="utf-8"))
        self.assertEqual((check_frames[-1]["scene"], check_frames[-1]["frame"]),
                         ("handoff", timeline["totalFrames"] - 1))
        self.assertEqual(last, 'guard: FAIL frame %d (scene handoff): OFFCANVAS "late"'
                         % check_frames[-1]["frame"])

    # red: a mark error ends the pass as the exit line of the pass ("guard: FAIL remotion render exit 1"), or
    # keeps "MARK" in the line. Film.tsx calls at() at every frame, so the first check frame throws
    def test_a_word_that_is_not_said_stops_at_the_guard(self):
        def unsaid_word(out):
            film = out / "scene" / "Film.tsx"
            text = film.read_text(encoding="utf-8")
            self.assertIn('at("subject", { word: "subject" })', text)
            film.write_text(text.replace('at("subject", { word: "subject" })',
                                         'at("subject", { word: "zebra" })', 1), encoding="utf-8")

        _, last, _ = self.stops_at_the_guard(unsaid_word, added=0)
        self.assertEqual(last, 'guard: FAIL mark: scene subject: word "zebra" is not in the narration')

    def test_a_small_tspan_is_smalltext(self):
        """Red: the size of the <text> is read and not that of its smaller <tspan> (the label is 20 px: no
        SMALLTEXT, and the run goes on to the render)."""
        _, last, check_frames = self.stops_at_the_guard(
            lambda out: add_to_film(self, out, "Tiny", TINY, "<Tiny />"))
        self.assertEqual(last, 'guard: FAIL frame %d (scene subject): SMALLTEXT 10.0 px "big tiny"'
                         % check_frames[0]["frame"])

    def test_a_clip_holds_the_example_to_its_floor(self):
        """Red: FilmStage passes the MIN_TEXT of the palette to the guard and not the minText of its timeline
        (the clip passes the guard at 14 px, and the run exits 0). The example as a film is the control: it
        passes (FilmRenderCase). As a clip, the labels of 16 px (WordBar.tsx, Film.tsx) and of 18 px (Forms.tsx)
        are below the 19 px floor: text that passes a film fails a clip."""
        def as_clip(out):
            script = json.loads((out / "script.json").read_text(encoding="utf-8"))
            script["format"] = "clip"
            (out / "script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

        out, last, check_frames = self.stops_at_the_guard(as_clip, added=0)
        timeline = json.loads((out / "build" / "timeline.json").read_text(encoding="utf-8"))
        self.assertEqual(timeline["minText"], 19)
        found = re.fullmatch(r"guard: FAIL frame (\d+) \(scene ([a-z0-9-]+)\): (.+)", last)
        self.assertIsNotNone(found, last)
        frame, scene, faults = int(found.group(1)), found.group(2), found.group(3)
        self.assertIn((frame, scene), [(check["frame"], check["scene"]) for check in check_frames])
        for fault in re.sub(r" \(\+\d+ more\)$", "", faults).split("; "):
            small = re.fullmatch(r'SMALLTEXT (\d+\.\d) px ".+"', fault)
            self.assertIsNotNone(small, fault)
            self.assertTrue(14 <= float(small.group(1)) < 19, fault)


if __name__ == "__main__":
    unittest.main()
