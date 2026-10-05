"""The words and the picture of the worked example film, which keep the example true (spec 5.3). The
skill ships one film, "how /explain checks an artifact before handoff": templates/film-script.json holds
its narration and cites, video/src/film/script.gen.ts the scene and source names that build-timeline.mjs
--types writes from it, and video/src/film/Film.tsx the picture. The first class holds the script to the
rules that need no audio: it passes the script check, its generated names are the checked-in file, its
transcript passes the cite check and the prose lint of verify.sh, and its cites and sources name only the
three files that no wave of the feature edits. The second class narrates the script with the say engine
and builds the real timeline: the film is 30 to 50 s long and the marks of the kit (video/src/kit/marks.ts)
read that timeline. The third class holds the picture: the app with FilmStage and the example compiles
(the workspace's tsc, skipped naming video-workspace.sh when it is missing), and video/check_scene.py,
the tool that checks a scene directory, passes the files of video/src/film (the directory, import and
token rules of a scene, spec 5.1 and 7.2). No video is rendered here. Each test names the mutation that
turns it red."""

import json
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_check_scene import check_scene
from test_film_kit import kit_app, kit_url, needs_kit_tools, run_node
from test_narrate import NARRATE_PY
from test_video_timeline import EXPLAIN, TOOL

REPO = EXPLAIN.parent.parent
FILM_TEMPLATE = EXPLAIN / "templates" / "film-script.json"
FILM_DIR = EXPLAIN / "video" / "src" / "film"
TRANSCRIPT_PY = EXPLAIN / "video" / "transcript.py"
VERIFY_SH = EXPLAIN / "scripts" / "verify.sh"

# The files that the cites and the source of the example may name: no wave of the feature edits them.
STABLE_FILES = {
    "skills/ste/SKILL.md",
    "skills/explain/scripts/verify.sh",
    "skills/explain/scripts/cite_check.py",
}

# Lines 138 and 139 of scripts/cite_check.py, the two lines that source `check` carries (65 and 69
# characters): the picture of the example tints columns of them.
CHECK_LINES = [
    "    if _normalize(snippet) not in _normalize(lines[line_no - 1]):",
    '        failures.append("%s: snippet not found on that line" % label)',
]

FPS = 30
MIN_SECONDS, MAX_SECONDS = 30, 50   # spec 5.3: the example is a film of about 40 s


def template_script():
    """The template with provenance.root set to the repository root: the root of the template itself is
    "." (the root of whoever renders it), and a test runs from elsewhere."""
    script = json.loads(FILM_TEMPLATE.read_text(encoding="utf-8"))
    script["provenance"]["root"] = str(REPO)
    return script


def write_script(directory, script):
    """script.json of `script` in `directory` (a Path); returns its path."""
    path = Path(directory) / "script.json"
    path.write_text(json.dumps(script), encoding="utf-8")
    return path


class ExampleScriptCase(unittest.TestCase):
    """The script as written, with no audio."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="film-example-")
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def verify_page(self, script, name):
        """transcript.py on `script`, then verify.sh on the page it writes into <dir>/<name>; returns
        the verify.sh run."""
        path = write_script(self.dir, script)
        out = self.dir / name
        made = subprocess.run(
            [sys.executable, "-B", str(TRANSCRIPT_PY), str(path), str(out)],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
        return subprocess.run(
            [str(VERIFY_SH), str(out / "index.html")], capture_output=True, text=True, timeout=300
        )

    def test_template_passes_check(self):
        """Red: a narration of the template runs over 45 words, a scene carries a component, a source
        range lies outside its file, or the template breaks another rule of the film check (an id
        outside [a-z0-9-], a pause below 12 frames, a missing cite on a file subject)."""
        path = write_script(self.dir, template_script())
        done = subprocess.run(
            ["node", str(TOOL), "--check", str(path), "--root", str(REPO)], capture_output=True, text=True
        )
        self.assertEqual((done.returncode, done.stdout), (0, ""), done.stderr)

    def test_generated_names_equal_the_checked_in_file(self):
        """Red: a scene id is renamed in the template only (the tool writes another union than the file
        holds), a source id is, or the checked-in file is edited by hand or stale."""
        out = self.dir / "script.gen.ts"
        done = subprocess.run(
            ["node", str(TOOL), "--types", str(FILM_TEMPLATE), str(out)], capture_output=True, text=True
        )
        self.assertEqual((done.returncode, done.stdout), (0, ""), done.stderr)
        self.assertEqual(out.read_bytes(), (FILM_DIR / "script.gen.ts").read_bytes())

    def test_template_transcript_passes_the_cite_check(self):
        """Red: a cite that its file does not hold (a snippet or a line that drifted), a narration
        sentence that fails the prose lint, a remote reference on the page, or a citations check that
        passes on a wrong cite (the second run, with one word of the first snippet changed, must
        report one failure)."""
        script = template_script()
        run = self.verify_page(script, "right")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stdout.splitlines(), ["self-contained: ok", "citations: ok", "prose: ok"])

        cite = script["scenes"][0]["cites"][0]
        words = cite["snippet"].split()
        cite["snippet"] = " ".join(words[:-1] + [words[-1] + "x"])
        run = self.verify_page(script, "wrong")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertIn("citations: FAIL 1 failure(s)", run.stdout.splitlines())

    def test_cites_and_sources_name_only_the_stable_files(self):
        """Red: a cite or the source names a file that a later wave edits (skills/explain/rungs/video.md),
        the subject is not a directory, the format is not film, or no cite or source is left to check."""
        script = json.loads(FILM_TEMPLATE.read_text(encoding="utf-8"))
        paths = [cite["path"] for scene in script["scenes"] for cite in scene["cites"]]
        paths += [source["path"] for source in script["sources"]]
        self.assertTrue(paths, "the example has cites and a source")
        self.assertEqual(sorted(set(paths) - STABLE_FILES), [])
        self.assertEqual(script["subject"]["kind"], "directory")
        self.assertEqual(script["format"], "film")


def clean(text):
    """What the kit compares a word by: lower case, and only the letters and digits of the text."""
    return "".join(c for c in text.lower() if unicodedata.category(c)[0] in "LN")


def expected_marks(timeline):
    """Every mark of the kit for the scenes of `timeline`, as (the call, the film frame it gives). A call
    is {"call": "at" | "said" | "end", "id": ..., "where": ...}: at(id), at(id, {sentence: k}) for every
    sentence, at.said(id), at.end(id), and at(id, {word, nth}) for every word with a letter or a digit,
    where nth is the count of the words up to it that clean() makes equal."""
    scenes = timeline["scenes"]
    cases = []
    for index, scene in enumerate(scenes):
        sid, start = scene["id"], scene["from"]
        following = scenes[index + 1]["from"] if index + 1 < len(scenes) else timeline["totalFrames"]
        cases.append(({"call": "at", "id": sid}, start + scene["leadFrames"]))
        for k, frame in enumerate(scene["sentences"], start=1):
            cases.append(({"call": "at", "id": sid, "where": {"sentence": k}}, start + frame))
        cases.append(({"call": "said", "id": sid}, start + scene["leadFrames"] + scene["audioFrames"]))
        cases.append(({"call": "end", "id": sid}, following))
        seen = {}
        for word in scene["words"]:
            key = clean(word["text"])
            if key == "":
                continue
            seen[key] = seen.get(key, 0) + 1
            where = {"word": word["text"], "nth": seen[key]}
            cases.append(({"call": "at", "id": sid, "where": where}, start + word["from"]))
    return cases


def kit_marks(scenes, calls):
    """The frame that makeAt(`scenes`) of marks.ts gives for each call of `calls`, run by Node."""
    return run_node(
        'import { makeAt } from "%s";'
        "const at = makeAt(%s);"
        "const out = %s.map((q) => q.call === 'said' ? at.said(q.id)"
        " : q.call === 'end' ? at.end(q.id) : at(q.id, q.where));"
        "console.log(JSON.stringify(out));" % (kit_url("marks.ts"), json.dumps(scenes), json.dumps(calls))
    )


class ExampleTimelineCase(unittest.TestCase):
    """One narrate run (the say engine, as render.sh runs it for a film) and one build over its audio
    directory, shared by the tests."""

    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(prefix="film-example-timeline-")
        cls.addClassCleanup(tmp.cleanup)
        root = Path(tmp.name)
        cls.script = template_script()
        script_path = write_script(root, cls.script)
        cls.audio = root / "audio"
        cls.narrate = subprocess.run(
            [sys.executable, str(NARRATE_PY), "--engine", "say", str(script_path), str(cls.audio)],
            capture_output=True, text=True,
        )
        out = root / "out" / "timeline.json"
        cls.build = subprocess.run(
            ["node", str(TOOL), str(script_path), str(cls.audio / "durations.json"), "say", str(out),
             "--root", str(REPO)],
            capture_output=True, text=True,
        )
        cls.timeline = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else None

    def built(self):
        """The built timeline; fails with the output of the failed step when there is none."""
        self.assertIsNotNone(self.timeline, self.narrate.stdout + self.narrate.stderr + self.build.stdout)
        return self.timeline

    def test_example_narrates_and_builds(self):
        """Red: narrate.py or the build fails on the words files of the example, the timeline is not a
        film, its scenes are not the template's (renamed, dropped or reordered), a scene is not one or
        two sentences (the picture times a motion from each sentence), or source `check` is not carried
        (not declared, from another line, or lines that are not 138 and 139 of cite_check.py)."""
        self.assertEqual(self.narrate.returncode, 0, self.narrate.stdout + self.narrate.stderr)
        self.assertEqual((self.build.returncode, self.build.stdout), (0, ""), self.build.stderr)
        timeline = self.built()
        self.assertEqual(timeline["format"], "film")
        self.assertEqual([s["id"] for s in timeline["scenes"]], [s["id"] for s in self.script["scenes"]])
        for scene in timeline["scenes"]:
            self.assertIn(len(scene["sentences"]), (1, 2), scene["id"])
        self.assertEqual(
            timeline["sources"],
            {"check": {"path": "skills/explain/scripts/cite_check.py", "from": 138, "lines": CHECK_LINES}},
        )

    def test_example_is_about_40_s(self):
        """Red: the example is cut to a stub (a scene dropped, a narration shortened to a few words) or
        grows past the length that spec 5.3 names: the film is under 30 s or over 50 s."""
        timeline = self.built()
        self.assertEqual(timeline["fps"], FPS)
        seconds = timeline["totalFrames"] / FPS
        self.assertTrue(MIN_SECONDS <= seconds <= MAX_SECONDS, "%.2f s" % seconds)

    def test_kit_marks_read_the_built_timeline(self):
        """Red: the build writes a scene key under a name that MarkScene does not read (leadFrames,
        audioFrames, sentences or words), so a mark of the kit is NaN or throws; or a mark of the kit
        reads another frame than the one the timeline holds for it (the start of a scene without its
        lead, a sentence without the scene's `from`, said as the end of the last word, end as said, a
        word by its end or by the wrong nth)."""
        timeline = self.built()
        cases = expected_marks(timeline)
        got = kit_marks(timeline["scenes"], [call for call, _ in cases])
        self.assertEqual(len(got), len(cases))
        self.assertEqual([(call, frame) for (call, _), frame in zip(cases, got)], cases)


class ExampleSceneCase(unittest.TestCase):
    """The picture of the example: FilmStage, composition Film and src/film/Film.tsx."""

    @needs_kit_tools
    def test_the_app_compiles_with_the_example(self):
        """Red: a type error in the stage or the picture (FilmStage hands Film a prop it does not take), an
        unused local (noUnusedLocals: TS6133), or a mark on a scene id that the script does not have (TS2345,
        at("intro") against the SceneId union of script.gen.ts); or FilmStage.tsx or Film.tsx is missing, so
        tsc checks an app without them."""
        self.assertTrue((EXPLAIN / "video" / "src" / "FilmStage.tsx").is_file())
        self.assertTrue((FILM_DIR / "Film.tsx").is_file())
        app = kit_app()
        try:
            done = subprocess.run(["node_modules/.bin/tsc"], cwd=app, capture_output=True, text=True, timeout=180)
        finally:
            shutil.rmtree(app)
        self.assertEqual((done.returncode, done.stdout + done.stderr), (0, ""))

    def test_the_example_follows_the_scene_rules(self):
        """Red: a file of video/src/film imports what a scene may not (../kit/marks, whose makeAt is the
        pipeline's; a file of another directory), imports Sequence (or any name but the five) from remotion,
        re-exports one (`export { Sequence } from "remotion"`) or all of remotion (`export * from
        "remotion"`), holds a refused token (`: any`, `as unknown`, an href), or the directory holds another
        kind of file or a directory; or Film.tsx is missing or does not export the function Film. The
        rules are those of check_scene.py: this runs the tool on the directory (exit 0, no output)."""
        done = check_scene(FILM_DIR)
        self.assertEqual((done.returncode, done.stdout), (0, ""), done.stderr)


if __name__ == "__main__":
    unittest.main()
