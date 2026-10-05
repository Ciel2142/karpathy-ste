"""The film cases of scripts/render.sh: an always-run class on single functions, and the gated
render of the template.

FilmFunctionCase runs single functions of the script (stage_render, clear_stale) in a temporary
directory, through render_functions of test_render.py, with a fake remotion CLI and no workspace:
the composition each format renders, and the files a new run removes.

FilmRenderCase (EXPLAIN_VIDEO_E2E=1 only) renders templates/film-script.json (template_script() of
test_film_example.py, rooted at the repository) through scripts/render.sh --engine say once per
process (render_film(): a temporary output directory removed at exit, the environment render_env()
of video_e2e.py, so the render uses workspace()). It holds the nine stage lines, the stills at the
check frames, the size, the transcript page, the speed of the narration, the place of each clip
(the voice starts leadFrames after the scene start) and a picture that changes in every scene. The
expected scene ids, sentences and stills come from the template, not from the render's timeline.
Each test names the mutation that turns it red."""

import atexit
import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from png_diff import differing_pixels
from test_film_example import template_script
from test_narrate import NARRATE_PY
from test_render import render_functions, stage_lines
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

TEMPLATE_SCENES = template_script()["scenes"]
SCENES = len(TEMPLATE_SCENES)
# The nine stage lines of a film run, in order: the explainer's nine names.
ORDER = [
    r"script: ok \(%d scenes\)" % SCENES,
    r"workspace: ok /.+",
    r"narration \(say\): ok",
    r"timeline \(%d scenes, \d+\.\d s\): ok" % SCENES,
    r"render \(\d+\.\d s, \d+\.\d\d render-min/video-min\)( \(limit 2\.0\))?: ok",
    r"container: ok \(\d+\.\d\d s\)",
    r"sync: ok",
    r"stills \(\d+\): ok /.+",
    r"transcript: ok",
]
CHANGED_PIXELS = 500   # an -end still and the one before it differ in more than this

_cache = {}


def render_film():
    """(output dir, CompletedProcess) of the one template render of this process."""
    if "result" not in _cache:
        out = Path(tempfile.mkdtemp(prefix="explain-film-e2e-"))
        atexit.register(shutil.rmtree, out, ignore_errors=True)
        (out / "script.json").write_text(json.dumps(template_script(), indent=2), encoding="utf-8")
        run = subprocess.run(
            ["/bin/bash", str(RENDER_SH), str(out), "--engine", "say"],
            capture_output=True, text=True, env=render_env(), timeout=RENDER_TIMEOUT,
        )
        _cache["result"] = (out, run)
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

    # red: the composition is the literal Explain (the film case), or Film for every format
    # (the explainer and brainrot cases)
    def test_a_film_renders_composition_film(self):
        (self.out / "audio").mkdir()
        (self.out / "audio" / "s1.say.wav").write_bytes(b"clip")
        (self.out / "build" / "timeline.json").write_text(
            json.dumps({"scenes": [{"audio": "audio/s1.say.wav"}]}), encoding="utf-8")
        calls = self.tmp / "calls.json"
        remotion = self.fake_remotion(calls)
        for fmt, composition in (("film", "Film"), ("explainer", "Explain"),
                                 ("brainrot", "Explain")):
            with self.subTest(fmt=fmt):
                calls.unlink(missing_ok=True)
                run = run_functions(
                    self.tmp, ["fail", "now", "stage_render"],
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


@unittest.skipUnless(E2E, E2E_REASON)
class FilmRenderCase(unittest.TestCase):
    def rendered(self):
        """The output directory of the template render, which passed."""
        out, run = render_film()
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return out, run

    # red: a film rendered as Explain (the render stage fails: render: FAIL remotion render exit 1),
    # or another stage of the film path fails or prints another line
    def test_film_prints_nine_ok_lines(self):
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

    # red: stills by scene and cue (the explainer's names), a missing end still of the last scene,
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


if __name__ == "__main__":
    unittest.main()
