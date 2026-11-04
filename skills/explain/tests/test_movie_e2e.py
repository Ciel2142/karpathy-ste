"""The fixture movie: two chapters and the bridge between them, rendered and stitched end to end (movie
spec 4.4 to 4.6, the done_when of wave 1).

FIXTURE/movie.json is a movie of two chapters, both built, 30 s each. It is for the render only and is not a
valid plan: `movie.py check` refuses it on two lines, `schema: chapters has 2 entries (min 4, max 10)` and
`schema: seconds sum 60 (min 240, max 900)`. So the test writes the bridges with movie.bridges() directly
(`movie.py bridges <dir>` refuses a plan that fails check), and stitches with `movie.py stitch <dir>`, which
runs no check. Its subject is a topic and its questions cite nothing; movie_output() roots it at REPO, so
the cites of the chapter transcripts, which the hub sections copy, resolve.

A chapter is the clip of the lesson E2E (tests/fixtures/lesson-e2e/, three scenes subject, gates and
handoff), made a chapter by chapter_from_clip(out, chapter_id): the format is film, the title is the title
of the chapter in movie.json, the root is REPO, and the first and last scene ids are renamed (RENAMES) in
script.json and in each at("<id>" of scene/*.tsx.

MovieChapterCase always runs, with no render: both chapters pass check_chapter_script.

MovieRenderCase (EXPLAIN_VIDEO_E2E=1 only) renders the two chapters and bridges/1 through scripts/render.sh
--engine say, each in its own directory (eleven ok lines each), then stitches them. The fixture is short by
design, so the stitch ends on `length: FAIL` and exit 1 after every other stage printed ok. The movie
directory of that run is kept, in the temporary directory under a name that starts with KEPT_PREFIX, for a
look at the stitched video.mp4, the hub index.html and the stills; the messages of the stitch assertions
name it. Each test names the mutation that turns it red."""

import atexit
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import movie
from test_film_example import REPO, TRANSCRIPT_PY, VERIFY_SH
from test_render import stage_lines
from test_render_film import ORDER, load, render_output, split_sentences
from test_verify import BPMN_NONE, LESSON_PASS
from video_e2e import E2E, E2E_REASON, EXPLAIN, workspace

FIXTURE = EXPLAIN / "tests" / "fixtures" / "movie-e2e"
CLIP = EXPLAIN / "tests" / "fixtures" / "lesson-e2e"
RENAMES = {"subject": "ask", "handoff": "answer"}  # the clip's first and last scene ids, as a chapter's
KEPT_PREFIX = "explain-movie-e2e-"
inline = load("transcript_for_movie_e2e", TRANSCRIPT_PY).inline  # narration as a transcript writes it


def movie_output(keep: bool = False) -> Path:
    """A temporary movie directory that holds FIXTURE/movie.json with provenance.root set to REPO. It is
    removed at exit, unless `keep`: then its name starts with KEPT_PREFIX and it stays."""
    if keep:
        out = Path(tempfile.mkdtemp(prefix=KEPT_PREFIX))
    else:
        out = Path(tempfile.mkdtemp(prefix="explain-movie-chapters-"))
        atexit.register(shutil.rmtree, out, ignore_errors=True)
    plan = json.loads((FIXTURE / "movie.json").read_text(encoding="utf-8"))
    plan["provenance"]["root"] = str(REPO)
    movie.save(str(out), plan)
    return out


def chapter_from_clip(out: Path, chapter_id: str) -> Path:
    """Writes out/chapters/<chapter_id>/ from the lesson-e2e clip and returns it: script.json with format
    film, the chapter's title from out/movie.json, root REPO and the scene ids of RENAMES, and a copy of
    scene/ in which each at("<old id>" of a .tsx file reads at("<new id>"."""
    chapter = next(c for c in movie.load(str(out))["chapters"] if c["id"] == chapter_id)
    directory = out / "chapters" / chapter_id
    shutil.copytree(CLIP / "scene", directory / "scene")
    script = json.loads((CLIP / "script.json").read_text(encoding="utf-8"))
    script["format"] = "film"
    script["title"] = chapter["title"]
    script["provenance"]["root"] = str(REPO)
    for scene in script["scenes"]:
        scene["id"] = RENAMES.get(scene["id"], scene["id"])
    (directory / "script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")
    for path in (directory / "scene").glob("*.tsx"):
        text = path.read_text(encoding="utf-8")
        for old, new in RENAMES.items():
            text = text.replace('at("%s"' % old, 'at("%s"' % new)
        path.write_text(text, encoding="utf-8")
    return directory


def scenes_of(directory: Path) -> list:
    """The scenes of directory/script.json."""
    return json.loads((directory / "script.json").read_text(encoding="utf-8"))["scenes"]


def scene_files(scene: Path) -> int:
    """The files of `scene` that the scene stage counts: *.ts and *.tsx, not script.gen.ts, not hidden."""
    return len([path for path in scene.iterdir()
                if path.suffix in (".ts", ".tsx") and path.is_file() and not path.name.startswith(".")
                and path.name != "script.gen.ts"])


def stage_patterns(directory: Path) -> list:
    """The eleven stage-line patterns of a say render of `directory`, as test_lesson_e2e holds them for its
    clip: the scene count, the scene/ file count and the guard frames come from the directory."""
    scenes = scenes_of(directory)
    frames = sum(len(split_sentences(scene["narration"])) + 1 for scene in scenes)
    return [
        r"script: ok \(%d scenes\)" % len(scenes),
        r"workspace: ok /.+",
        r"scene: ok \(%d files\)" % scene_files(directory / "scene"),
        r"narration \(say\): ok",
        r"timeline \(%d scenes, \d+\.\d s\): ok" % len(scenes),
        r"guard \(%d frames\): ok" % frames,
    ] + ORDER[6:]


def printed(function, *args):
    """(what `function(*args)` returns, what it wrote to stdout)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        result = function(*args)
    return result, out.getvalue()


class MovieChapterCase(unittest.TestCase):
    # red: chapter_from_clip keeps "format": "clip", keeps the clip's title, or misses the rename of the
    # last scene (chapter <id>: last scene is handoff, not answer); or a scene file keeps at("subject"
    def test_the_fixture_chapters_pass_check_chapter_script(self):
        out = movie_output()
        for chapter in movie.load(str(out))["chapters"]:
            with self.subTest(chapter=chapter["id"]):
                directory = chapter_from_clip(out, chapter["id"])
                # check_chapter_script passes a chapter with no script: the script must be there
                self.assertTrue((directory / "script.json").is_file())
                self.assertEqual(movie.check_chapter_script(str(out), chapter), [])
                left = ['%s: at("%s"' % (path.name, old) for path in sorted((directory / "scene").glob("*.tsx"))
                        for old in RENAMES if 'at("%s"' % old in path.read_text(encoding="utf-8")]
                self.assertEqual(left, [])


@unittest.skipUnless(E2E, E2E_REASON)
class MovieRenderCase(unittest.TestCase):
    def assert_render(self, directory: Path):
        """render.sh --engine say on `directory` exits 0 with its eleven ok lines."""
        run = render_output(directory)
        self.assertEqual(run.returncode, 0, "%s\n%s%s" % (directory, run.stdout, run.stderr))
        self.assertNotIn("FAIL", run.stdout)
        lines = stage_lines(run.stdout)
        patterns = stage_patterns(directory)
        self.assertEqual(len(lines), len(patterns), run.stdout)
        for line, pattern in zip(lines, patterns):
            self.assertRegex(line, "^%s$" % pattern)

    def assert_viewer_transcript(self, out: Path, chapter: Path):
        """The hub holds every scene's narration; the viewer transcript the gates scene's and not the
        narration of ask or of answer."""
        narration = {scene["id"]: inline(scene["narration"]) for scene in scenes_of(chapter)}
        hub = (out / "index.html").read_text(encoding="utf-8")
        viewer = (out / "review" / "viewer-transcript.html").read_text(encoding="utf-8")
        for scene, text in narration.items():
            self.assertIn("<p>%s</p>" % text, hub, scene)
        self.assertIn("<p>%s</p>" % narration["gates"], viewer)
        for scene in RENAMES.values():
            self.assertNotIn(narration[scene], viewer, scene)

    # red: stitch joins the parts out of order or drops the bridge (parts: ok (2), a shorter video.mp4), a
    # chapter start rounded or counted without the bridge, the viewer transcript keeps the ask or the answer
    # scene, or the hub links a chapter transcript that is not there (media: FAIL 1 missing)
    def test_two_chapters_and_a_bridge_stitch(self):
        out = movie_output(keep=True)
        plan = movie.load(str(out))
        ids = [chapter["id"] for chapter in plan["chapters"]]
        for ident in ids:
            chapter_from_clip(out, ident)
        self.assertEqual(printed(movie.bridges, str(out), plan), (["1"], "bridges: ok (1)\n"))
        parts = [out / "chapters" / ids[0], out / "bridges" / "1", out / "chapters" / ids[1]]
        for part in parts:
            self.assert_render(part)

        code, text = printed(movie.main, ["stitch", str(out)])
        self.assertTrue((out / "video.mp4").is_file(), "%s\n%s" % (out, text))
        cli = movie.remotion_cli(str(workspace()))
        durations = [movie.probe(cli, str(part / "video.mp4"))["duration"] for part in parts]
        seconds = movie.probe(cli, str(out / "video.mp4"))["duration"]
        self.assertEqual((code, text.splitlines()), (1, [
            "parts: ok (3)",
            "concat: ok (%.1f s)" % sum(durations),
            "container: ok (%.1f s)" % seconds,
            "transcript: ok (2 chapters)",
            "hub: ok index.html",
            "length: FAIL %.1f s (min 240, max 900)" % seconds,
        ]), out)
        self.assertLessEqual(abs(seconds - sum(durations)), 0.5, out)

        starts = json.loads((out / "chapters.json").read_text(encoding="utf-8"))
        self.assertEqual(starts, [
            {"id": ids[0], "title": plan["chapters"][0]["title"], "start": 0.0},
            {"id": ids[1], "title": plan["chapters"][1]["title"], "start": durations[0] + durations[1]},
        ], out)
        self.assert_viewer_transcript(out, parts[0])

        run = subprocess.run([str(VERIFY_SH), str(out / "index.html")], capture_output=True, text=True,
                             timeout=300)
        self.assertEqual((run.returncode, run.stdout), (0, LESSON_PASS + "media: ok\n" + BPMN_NONE),
                         "%s\n%s" % (out, run.stderr))


if __name__ == "__main__":
    unittest.main()
