"""End-to-end brainrot renders (the render cases run with EXPLAIN_VIDEO_E2E=1 only; LimitsScriptCase
runs without it): templates/brainrot-script.json through
scripts/render.sh --engine say, twice. Each render uses the workspace $EXPLAIN_VIDEO_WORKSPACE, else
the default workspace ~/karpathy/video-workspace (never deleted here), and compiles in a run
directory of its own there (<ws>/runs/run.<pid>.<6 chars>, which render.sh removes); its
environment is render_env() of video_e2e.py.

The generated run has EXPLAIN_BRAINROT_BACKGROUNDS pointing at an empty temp dir, so the picker
chooses the generated runner loop. The clip run points it at a temp dir that holds a copy of
fixtures/bg-1s.mp4, a 1 s clip that is shorter than the video, so it loops. Each render is cached
once per process and script (each in a temp output dir, with an absolute provenance.root, and the
temp dirs are removed at exit). Both folders lie outside the workspace, because the
picker refuses a --dir that is, or lies under, <ws>/runs: the folder that holds the run directory
it is given. test_check_render reuses the generated render (render_brainrot("generated")).

The limits case renders fixtures/brainrot-limits-script.json the same way (generated background,
seed 7): every limited text of the script sits at its brainrot limit, so its stills show the worst
case of the layout. Each test names the mutation that turns it red."""

import atexit
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from png_diff import ink_extent
from test_render import STAGES, stage_lines
from video_e2e import E2E, E2E_REASON, EXPLAIN, RENDER_SH, RENDER_TIMEOUT, render_env, workspace

BRAINROT_TEMPLATE = EXPLAIN / "templates" / "brainrot-script.json"
LIMITS_SCRIPT = EXPLAIN / "tests" / "fixtures" / "brainrot-limits-script.json"
CLIP = EXPLAIN / "tests" / "fixtures" / "bg-1s.mp4"
SEED = "7"  # fixes the clip choice and start, whatever the caller's environment holds
TEMPLATE_SCENES = json.loads(BRAINROT_TEMPLATE.read_text(encoding="utf-8"))["scenes"]
SCENES = len(TEMPLATE_SCENES)
LIMITS_SCENES = len(json.loads(LIMITS_SCRIPT.read_text(encoding="utf-8"))["scenes"])
# The prop that lists the cues of a component with one cue per item (build-timeline.mjs cuesOf).
CUE_LISTS = {"bullets-appear": "bullets", "diagram-with-highlight-walk": "walk",
             "code-with-line-highlights": "highlights"}


def template_cues(scene):
    """The cues of a template scene, read from the template the way build-timeline.mjs cuesOf
    reads them: the one cue of a title or before-after scene, else one per listed item; only
    non-empty strings count."""
    props = scene.get("props", {})
    if scene["component"] in ("title", "before-after"):
        raw = [props.get("cue")]
    else:
        raw = [item.get("cue") for item in props.get(CUE_LISTS.get(scene["component"], ""), [])]
    return [cue for cue in raw if isinstance(cue, str) and cue]


def stage_patterns(scenes):
    """The ten stage lines of a brainrot run of `scenes` scenes, in order; the background line
    (None) is the one that differs per run."""
    return [
        r"script: ok \(%d scenes\)" % scenes,
        r"workspace: ok /.+",
        r"narration \(say\): ok",
        r"timeline \(%d scenes, \d+\.\d s\): ok" % scenes,
        None,
        r"render \(\d+\.\d s, \d+\.\d\d render-min/video-min\)( \(limit 2\.0\))?: ok",
        r"container: ok \(\d+\.\d\d s\)",
        r"sync: ok",
        r"stills \(\d+\): ok /.+",
        r"transcript: ok",
    ]


ORDER = stage_patterns(SCENES)
BACKGROUND = {
    "generated": r"background: ok generated",
    "clip": r"background: ok bg-1s\.mp4 @0\.0 s \(loop\)",
}
# The Background row of the transcript; the space after the @ is the transcript's (spec 6.3).
BACKGROUND_ROW = {"generated": "generated", "clip": "bg-1s.mp4 @ 0.0 s (loop)"}

_cache = {}


def render_brainrot(kind, script=BRAINROT_TEMPLATE):
    """(output dir, CompletedProcess) of the one brainrot render of this process for `kind` and
    `script` (the path of a script.json; the template by default): "generated" (an empty
    background folder) or "clip" (a folder with a copy of the fixture)."""
    key = (kind, script)
    if key not in _cache:
        out = Path(tempfile.mkdtemp(prefix="explain-brainrot-e2e-"))
        clips = Path(tempfile.mkdtemp(prefix="explain-brainrot-clips-"))
        for path in (out, clips):
            atexit.register(shutil.rmtree, path, ignore_errors=True)
        if kind == "clip":
            shutil.copy(CLIP, clips / CLIP.name)
        data = json.loads(Path(script).read_text(encoding="utf-8"))
        data["provenance"]["root"] = str(EXPLAIN)
        (out / "script.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        env = render_env(EXPLAIN_BRAINROT_BACKGROUNDS=str(clips), EXPLAIN_BRAINROT_SEED=SEED)
        run = subprocess.run(
            ["/bin/bash", str(RENDER_SH), str(out), "--engine", "say"],
            capture_output=True, text=True, env=env, timeout=RENDER_TIMEOUT,
        )
        _cache[key] = (out, run)
    return _cache[key]


def video_size(mp4):
    """The "<w>x<h>" of the first video stream of `mp4`, read by the workspace's remotion ffprobe."""
    app = workspace() / "app"
    run = subprocess.run(
        [str(app / "node_modules" / ".bin" / "remotion"), "ffprobe", "-v", "error",
         "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(mp4)],
        cwd=app, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
    assert run.returncode == 0, run.stderr
    stream = json.loads(run.stdout)["streams"][0]
    return "%dx%d" % (stream["width"], stream["height"])


LIMITS = json.loads((EXPLAIN / "video" / "formats.json").read_text(encoding="utf-8"))["brainrot"]
LIMITS_SOURCE = EXPLAIN / "tests" / "fixtures" / "limits-source.txt"
CHECK_TOOL = EXPLAIN / "video" / "build-timeline.mjs"
NAME = "EXPLAIN_BRAINROT_BACKGROUNDS"


def limited_texts(script):
    """(where, text, limit) for every text of `script` that a brainrot limit bounds, and (where,
    count, limit) for each list that a limit bounds. An edge between two cells of one row carries
    no label in brainrot (count 0, limit 0); every other edge label sits at the 10-char limit."""
    found = []
    for scene in script["scenes"]:
        props, here = scene["props"], scene["id"]
        if scene["component"] == "title":
            found += [(here + " title", props["title"], LIMITS["titleTitle"]),
                      (here + " subtitle", props["subtitle"], LIMITS["titleSubtitle"])]
            continue
        found.append((here + " heading", props["title"], LIMITS["sceneTitle"]))
        if scene["component"] == "bullets-appear":
            found += [(here + " bullet", b["text"], LIMITS["bulletText"]) for b in props["bullets"]]
            found.append((here + " bullets", len(props["bullets"]), 4))
        elif scene["component"] == "diagram-with-highlight-walk":
            found += [(here + " label", n["label"], LIMITS["diagramLabel"]) for n in props["nodes"]]
            found += [(here + " sub", n["sub"], LIMITS["diagramSub"]) for n in props["nodes"]]
            cells = {n["id"]: n["cell"] for n in props["nodes"]}
            for e in props["edges"]:
                if cells[e["from"]][1] == cells[e["to"]][1]:
                    found.append((here + " same-row edge", int("label" in e), 0))
                else:
                    found.append((here + " edge", e["label"], 10))
            found.append((here + " nodes", len(props["nodes"]), 7))
        elif scene["component"] == "code-with-line-highlights":
            source = props["source"]
            found.append((here + " lines", source["to"] - source["from"] + 1, LIMITS["codeLines"]))
        elif scene["component"] == "before-after":
            for side in ("before", "after"):
                found.append((here + " " + side + " heading", props[side]["heading"], LIMITS["beforeAfterHeading"]))
                found += [(here + " " + side + " line", t, LIMITS["beforeAfterLineChars"]) for t in props[side]["lines"]]
                found.append((here + " " + side + " lines", len(props[side]["lines"]), LIMITS["beforeAfterLines"]))
    return found


class LimitsScriptCase(unittest.TestCase):
    """The stress fixtures hold their promise without a render: the script is valid, and each of its
    limited texts sits exactly at its brainrot limit."""

    script = json.loads(LIMITS_SCRIPT.read_text(encoding="utf-8"))

    # red: a text of the script over a limit, a missing cite, a cue the narration lacks, or a code
    # range over 14 lines or over 40 columns (the validator FAILs)
    def test_limits_script_passes_check(self):
        run = subprocess.run(["node", str(CHECK_TOOL), "--check", str(LIMITS_SCRIPT), "--root", str(EXPLAIN)],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual((run.returncode, run.stdout), (0, ""), run.stderr)

    # red: any text of the script one character short of its limit (the validator accepts it, so
    # only this test notices that the script no longer stresses the limit), or a list with fewer
    # items than the limit
    def test_limits_script_sits_at_the_limits(self):
        for where, value, limit in limited_texts(self.script):
            with self.subTest(where=where):
                self.assertEqual(value if isinstance(value, int) else len(value), limit)

    # red: a line of limits-source.txt shorter or longer than 40 columns, a tab, or a file of
    # another length than 14 lines
    def test_limits_source_is_14_lines_of_40_columns(self):
        lines = LIMITS_SOURCE.read_text(encoding="utf-8").split("\n")
        self.assertEqual(lines.pop(), "", "the file ends with a newline")
        self.assertEqual([len(line) for line in lines], [LIMITS["codeColumns"]] * LIMITS["codeLines"])
        self.assertNotIn("\t", "".join(lines))

    # red: the cue of the hook scene not starting its sentence with three capitalised words that
    # join to captionChars characters (the cap-length caption chunk of the first cue still), or the
    # last scene's cue sentence not starting with the long backticked name (the smaller-type chunk)
    def test_limits_script_cue_sentences(self):
        hook, last = self.script["scenes"][0], self.script["scenes"][-1]
        words = hook["narration"].split()[:3]
        self.assertTrue(all(word[:1].isupper() for word in words), words)
        self.assertEqual(len(" ".join(words)), LIMITS["captionChars"])
        self.assertEqual(hook["props"]["cue"], " ".join(words))
        self.assertTrue(last["narration"].startswith("`%s` " % NAME), last["narration"])
        self.assertEqual(last["props"]["cue"], "`%s`" % NAME)


@unittest.skipUnless(E2E, E2E_REASON)
class BrainrotRenderCase(unittest.TestCase):
    def check_ten_lines(self, kind, script=BRAINROT_TEMPLATE):
        out, run = render_brainrot(kind, script)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertNotIn("FAIL", run.stdout)
        scenes = len(json.loads(Path(script).read_text(encoding="utf-8"))["scenes"])
        patterns = stage_patterns(scenes)
        lines = stage_lines(run.stdout)
        self.assertEqual([line.split(":")[0].split(" ")[0] for line in lines], list(STAGES), run.stdout)
        self.assertEqual(len(patterns), len(STAGES), "the patterns and STAGES disagree; zip would drop lines")
        for line, pattern in zip(lines, patterns):
            self.assertRegex(line, "^%s$" % (pattern or BACKGROUND[kind]))
        return out

    # red: the helper drops EXPLAIN_VIDEO_WORKSPACE and the render goes to the default workspace.
    # Not run red (that is a render in a workspace this branch must not use): E2EHelperCase of
    # test_render is the red-first proof of the helper, this case binds the real renders to it.
    def test_render_used_the_callers_workspace(self):
        for kind in ("generated", "clip"):
            with self.subTest(background=kind):
                _, run = render_brainrot(kind)
                self.assertEqual(stage_lines(run.stdout)[1:2], ["workspace: ok %s" % workspace()],
                                 run.stdout + run.stderr)

    # red: the background stage printing no line (nine lines), a stage out of order, or the
    # generated run picking a clip
    def test_generated_ten_ok_lines(self):
        self.check_ten_lines("generated")

    # red: the picker ignoring EXPLAIN_BRAINROT_BACKGROUNDS (the clip run says "generated"), or
    # the looping clip losing its " (loop)" mark
    def test_clip_ten_ok_lines(self):
        self.check_ten_lines("clip")

    # red: the composition keeping the landscape size, or the container check dropping the size
    def test_portrait_container(self):
        for kind in ("generated", "clip"):
            with self.subTest(background=kind):
                out, run = render_brainrot(kind)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertEqual(video_size(out / "video.mp4"), "1080x1920")

    # red: render.sh narrating a brainrot script without --speed 1.2, or without sentence mode
    def test_speed_in_sidecars(self):
        for kind in ("generated", "clip"):
            with self.subTest(background=kind):
                out, run = render_brainrot(kind)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                sidecars = sorted((out / "audio").glob("*.say.txt"))
                self.assertEqual(len(sidecars), SCENES, [p.name for p in sidecars])
                for sidecar in sidecars:
                    text = sidecar.read_text(encoding="utf-8")
                    self.assertTrue(text.startswith("engine=say\n"), sidecar.name)
                    self.assertIn("\nspeed=1.2\nmode=sentences\n", text, sidecar.name)

    # red: the Format row missing or in landscape size, or the Background row left as "pending" or
    # showing another run's background
    def test_transcript_rows(self):
        for kind in ("generated", "clip"):
            with self.subTest(background=kind):
                out, run = render_brainrot(kind)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                page = (out / "index.html").read_text(encoding="utf-8")
                self.assertIn("<dt>Format</dt><dd>brainrot (1080×1920)</dd>", page)
                self.assertIn("<dt>Background</dt><dd>%s</dd>" % BACKGROUND_ROW[kind], page)

    # red: stills only for the scenes (the cue stills dropped), a still in the wrong dir, or a
    # timeline that lost a scene or a cue of the template (the expected names come from the
    # template, not from the render's own timeline.json)
    def test_stills_present(self):
        expected = set()
        for n, scene in enumerate(TEMPLATE_SCENES, 1):
            expected.add("still-%02d-%s.png" % (n, scene["id"]))
            for k in range(1, len(template_cues(scene)) + 1):
                expected.add("still-%02d-%s-%d.png" % (n, scene["id"], k))
        for kind in ("generated", "clip"):
            with self.subTest(background=kind):
                out, run = render_brainrot(kind)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                found = {p.name for p in (out / "review").glob("*.png")}
                self.assertEqual(found, expected)
                self.assertGreater(len(expected), SCENES)
                stills = [line for line in stage_lines(run.stdout) if line.startswith("stills (")]
                self.assertEqual(stills[0].split(")")[0], "stills (%d" % len(expected))

    # red: a limited text of the stress script over a limit or a cue the narration lacks (a stage
    # FAILs and the later stage lines are missing), or a stage line out of order
    def test_limits_script_ten_ok_lines(self):
        self.check_ten_lines("generated", LIMITS_SCRIPT)

    # red: a panel text that runs into the outer 24 px of the panel (a scene that lays a text out
    # wider than its content box), in any of the stills of the stress script. The panel is white and
    # its content box starts 48 px from each side, so any ink in x 0-23 or x 1057-1079 above the
    # seam is an overflow. The caption lies below y 912, so it is not in this box. Also red: ink in
    # the seam band x 0-1079, y 912-927, between the content box (it ends at y 911) and the top of
    # a full-size caption (y 928): a panel text that runs down out of its box, or a caption that
    # grows up into the panel.
    def test_limits_stills_keep_panel_margins(self):
        out, run = render_brainrot("generated", LIMITS_SCRIPT)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        stills = sorted((out / "review").glob("*.png"))
        self.assertGreater(len(stills), LIMITS_SCENES)
        for still in stills:
            for x0, x1 in ((0, 24), (1057, 1080)):
                with self.subTest(still=still.name, x0=x0):
                    self.assertIsNone(ink_extent(still, x0, x1, 0, 912))
            with self.subTest(still=still.name, band="seam"):
                self.assertIsNone(ink_extent(still, 0, 1080, 912, 928))


if __name__ == "__main__":
    unittest.main()
