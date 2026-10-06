"""The fixture lesson: one page with one clip, built the way rungs/lesson.md tells the author (spec 7.4).

The fixture lives in FIXTURE. script.json is a clip of three scenes of templates/video-script.json (subject,
gates and handoff, their narration and cites unchanged), scene/ is a trimmed copy of the worked example
video/src/film/ (each text 19 px or more, each text in C.muted 22 px or more), and section.html is the one
section of the page that holds the clip: its id is the clip id CLIP_ID, and it holds CLIP_MARKUP of
test_lesson_prompts.py.

lesson_output() makes a temporary lesson directory (removed at exit) with clips/<CLIP_ID>/: the script
rooted at the repository and a copy of scene/. lesson_page(out, clip) writes out/index.html: a copy of
templates/page.html with five edits (the lesson meta, the section, its nav link, the root, the Dropped clips
row). With clip=False the section has no figure.clip and the row names the drop. Each test writes the page
that it verifies, so the page never drifts from the template.

LessonFixtureCase always runs, with no render and no Chrome: the script is three scenes of the template,
the clip passes the checks of spec 5.1 step 4, and the section names the clip.

LessonRenderCase (EXPLAIN_VIDEO_E2E=1 only) renders the clip through scripts/render.sh --engine say once per
process (render_lesson(), cached as render_film() of test_render_film.py), then does step 8 of the author:
it copies the -end still of the last scene to poster.png. It holds the eleven stage lines, the clip row of
formats.json, a picture that changes in every scene and the poster, and it runs verify.sh on the page with
the clip and on the page with the clip dropped: six ok lines each. Each test names the mutation that turns
it red."""

import atexit
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from png_diff import differing_pixels
from test_check_scene import check_scene
from test_film_example import FILM_TEMPLATE, REPO, TRANSCRIPT_PY, VERIFY_SH
from test_lesson_prompts import CLIP_MARKUP
from test_render import stage_lines
from test_render_brainrot import video_size
from test_render_film import CHANGED_PIXELS, ORDER, render_output, split_sentences
from test_rung_drift import FORMATS_JSON
from test_verify import CLIP_FIGURE, LESSON_PASS
from test_video_timeline import TOOL
from video_e2e import E2E, E2E_REASON, EXPLAIN

FIXTURE = EXPLAIN / "tests" / "fixtures" / "lesson-e2e"
CLIP_ID = "checks"
PAGE_TEMPLATE = EXPLAIN / "templates" / "page.html"
SCENE_IDS = ["subject", "gates", "handoff"]
# The sentence of CLIP_MARKUP that the author replaces with a sentence about the clip.
PLACEHOLDER = "One sentence that says what the clip shows."
# The reason of the Dropped clips row of the page with no clip.
DROP_REASON = "render: FAIL guard"
CLIP_ROW = json.loads(FORMATS_JSON.read_text(encoding="utf-8"))["clip"]


def fixture_script():
    """The fixture script.json as written (its root is ".")."""
    return json.loads((FIXTURE / "script.json").read_text(encoding="utf-8"))


def scene_files():
    """The number of files of the fixture scene/ that the scene stage counts: the *.ts and *.tsx files, without
    script.gen.ts and without a hidden file."""
    return len([path for path in (FIXTURE / "scene").iterdir()
                if path.suffix in (".ts", ".tsx") and path.is_file() and not path.name.startswith(".")
                and path.name != "script.gen.ts"])


def last_end_still():
    """The name of the -end still of the last scene of the fixture: the poster of step 8."""
    scenes = fixture_script()["scenes"]
    return "still-%02d-%s-end.png" % (len(scenes), scenes[-1]["id"])


def lesson_output() -> Path:
    """A temporary lesson directory, removed at exit, with clips/<CLIP_ID>/: script.json is the fixture script
    rooted at REPO, and scene/ is a copy of the fixture scene/. The directory has no page yet."""
    out = Path(tempfile.mkdtemp(prefix="explain-lesson-e2e-"))
    atexit.register(shutil.rmtree, out, ignore_errors=True)
    clip = out / "clips" / CLIP_ID
    clip.mkdir(parents=True)
    script = fixture_script()
    script["provenance"]["root"] = str(REPO)
    (clip / "script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")
    shutil.copytree(FIXTURE / "scene", clip / "scene")
    return out


def lesson_page(out: Path, clip: bool = True) -> Path:
    """Writes out/index.html, a copy of templates/page.html with five edits, and returns its path. Each edit
    is on an anchor that occurs once in the template (AssertionError if it does not): the meta becomes the
    lesson meta, section.html goes before the provenance section, its nav link before the provenance link,
    data-root becomes REPO, and the Dropped clips row follows the Dirty row. With clip=False, the
    figure.clip of the section is removed first, and the row names the drop."""
    section = (FIXTURE / "section.html").read_text(encoding="utf-8")
    dropped = "none"
    if not clip:
        section, removed = CLIP_FIGURE.subn("", section)
        if removed != 1:
            raise AssertionError("%d figure.clip in section.html, not one" % removed)
        dropped = "%s — %s" % (CLIP_ID, DROP_REASON)
    dirty = "<div><dt>Dirty</dt><dd>no</dd></div>"
    edits = [
        ('\n<meta name="explain-rung" content="page">', '\n<meta name="explain-rung" content="lesson">'),
        ('<section id="provenance-facet">', section + '\n<section id="provenance-facet">'),
        ('<a href="#provenance-facet">Provenance</a>',
         '<a href="#%s">Checks</a>\n  <a href="#provenance-facet">Provenance</a>' % CLIP_ID),
        ('data-root="."', 'data-root="%s"' % REPO),
        (dirty, dirty + '\n      <div class="wide"><dt>Dropped clips</dt><dd>%s</dd></div>' % dropped),
    ]
    page = PAGE_TEMPLATE.read_text(encoding="utf-8")
    for anchor, text in edits:
        if page.count(anchor) != 1:
            raise AssertionError("%r occurs %d times in page.html, not once" % (anchor, page.count(anchor)))
        page = page.replace(anchor, text)
    path = out / "index.html"
    path.write_text(page, encoding="utf-8")
    return path


def verify(page):
    """The CompletedProcess of verify.sh on `page`."""
    return subprocess.run([str(VERIFY_SH), str(page)], capture_output=True, text=True, timeout=300)


class LessonFixtureCase(unittest.TestCase):
    # red: the fixture narration drifts from the template (a word changed in one scene), a scene is dropped
    # or another scene of the template takes its place, or the script is a film
    def test_the_fixture_is_three_scenes_of_the_template(self):
        script = fixture_script()
        self.assertEqual(script["format"], "clip")
        self.assertNotIn("sources", script)
        self.assertEqual([scene["id"] for scene in script["scenes"]], SCENE_IDS)
        template = {scene["id"]: scene for scene in json.loads(FILM_TEMPLATE.read_text(encoding="utf-8"))["scenes"]}
        for scene in script["scenes"]:
            with self.subTest(scene=scene["id"]):
                self.assertEqual(scene, template[scene["id"]])

    # red: a cite snippet off by one word (citations: FAIL), a narration that breaks the clip limits, or a
    # scene file that the scene rules refuse
    def test_the_fixture_clip_passes_the_checks_before_review(self):
        clip = lesson_output() / "clips" / CLIP_ID
        script = clip / "script.json"
        check = subprocess.run(["node", str(TOOL), "--check", str(script), "--root", str(REPO)],
                               capture_output=True, text=True, timeout=60)
        self.assertEqual((check.returncode, check.stdout, check.stderr), (0, "", ""))
        scene = check_scene(FIXTURE / "scene")
        self.assertEqual((scene.returncode, scene.stdout), (0, ""), scene.stderr)
        made = subprocess.run([sys.executable, "-B", str(TRANSCRIPT_PY), str(script), str(clip)],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
        run = verify(clip / "index.html")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stdout.splitlines(), ["self-contained: ok", "citations: ok", "prose: ok"])

    # red: a clip id that is not the section id (src="clips/check/video.mp4"), an <h2> that is not the title of
    # the script, or the placeholder sentence left in the figcaption
    def test_the_section_names_the_clip(self):
        text = (FIXTURE / "section.html").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"<section\b[^>]*>", text), ['<section id="%s">' % CLIP_ID])
        self.assertEqual(re.findall(r"<h2>(.*?)</h2>", text), [fixture_script()["title"]])
        part = '<span class="part"></span>'
        lines = [line for line in text.splitlines() if part in line]
        self.assertEqual(len(lines), 1, text)
        sentence = lines[0].split("</span>", 1)[1]
        self.assertIn(PLACEHOLDER, CLIP_MARKUP)
        self.assertNotEqual(sentence, PLACEHOLDER)
        self.assertIn(CLIP_MARKUP.replace("<id>", CLIP_ID).replace(PLACEHOLDER, sentence), text)


_cache = {}


def render_lesson():
    """(lesson dir, CompletedProcess) of the one render of this process: lesson_output(), then render.sh
    <out>/clips/<CLIP_ID> --engine say, then step 8 of the author: the -end still of the last scene is copied
    to clips/<CLIP_ID>/poster.png (when the render made it)."""
    if "result" not in _cache:
        out = lesson_output()
        clip = out / "clips" / CLIP_ID
        run = render_output(clip)
        still = clip / "review" / last_end_still()
        if still.is_file():
            shutil.copyfile(still, clip / "poster.png")
        _cache["result"] = (out, run)
    return _cache["result"]


@unittest.skipUnless(E2E, E2E_REASON)
class LessonRenderCase(unittest.TestCase):
    def rendered(self):
        """The lesson directory and the run of the clip render, as (out, run), once the run is seen to exit 0."""
        out, run = render_lesson()
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return out, run

    def clip(self, out):
        return out / "clips" / CLIP_ID

    # red: the fixture scene draws an 18 px label (guard: FAIL ... SMALLTEXT 18.0 px), a scene file of the
    # fixture is not counted, or the clip runs past the 60 s of the clip row
    def test_the_clip_prints_eleven_ok_lines(self):
        _, run = self.rendered()
        self.assertNotIn("FAIL", run.stdout)
        scenes = fixture_script()["scenes"]
        frames = sum(len(split_sentences(scene["narration"])) + 1 for scene in scenes)
        timeline = r"timeline \(%d scenes, (\d+\.\d) s\): ok" % len(scenes)
        patterns = [
            r"script: ok \(%d scenes\)" % len(scenes),
            r"workspace: ok /.+",
            r"scene: ok \(%d files\)" % scene_files(),
            r"narration \(say\): ok",
            timeline,
            r"guard \(%d frames\): ok" % frames,
        ] + ORDER[6:]
        lines = stage_lines(run.stdout)
        self.assertEqual(len(lines), len(patterns), run.stdout)
        for line, pattern in zip(lines, patterns):
            self.assertRegex(line, "^%s$" % pattern)
        seconds = float(re.match(timeline, lines[4]).group(1))
        self.assertLessEqual(seconds, CLIP_ROW["maxTotalSeconds"])

    # red: the fixture script says "format": "film" (minText 14, maxTotalSeconds 150), or composition Film
    # takes the size of another format
    def test_the_clip_is_held_to_the_clip_row(self):
        out, _ = self.rendered()
        timeline = json.loads((self.clip(out) / "build" / "timeline.json").read_text(encoding="utf-8"))
        self.assertEqual((timeline["minText"], timeline["maxTotalSeconds"]),
                         (CLIP_ROW["minText"], CLIP_ROW["maxTotalSeconds"]))
        self.assertEqual(video_size(self.clip(out) / "video.mp4"), "%dx%d" % (CLIP_ROW["width"], CLIP_ROW["height"]))

    # red: a scene of Film.tsx that draws nothing new: its -end still equals the -end still of the scene
    # before it
    def test_each_scene_changes_the_picture(self):
        out, _ = self.rendered()
        review = self.clip(out) / "review"
        names = ["still-%02d-%s-end.png" % (n, scene_id) for n, scene_id in enumerate(SCENE_IDS, 1)]
        for before, after in zip(names, names[1:]):
            with self.subTest(still=after):
                changed = differing_pixels(review / before, review / after, 0, 1280, 0, 720)
                self.assertGreater(changed, CHANGED_PIXELS, "%s against %s" % (after, before))

    # red: the poster copied from the first scene (still-01-subject-end.png)
    def test_the_poster_is_the_last_end_still(self):
        out, _ = self.rendered()
        clip = self.clip(out)
        self.assertEqual(last_end_still(), "still-03-handoff-end.png")
        self.assertEqual((clip / "poster.png").read_bytes(), (clip / "review" / last_end_still()).read_bytes())

    # red: the transcript link names clips/check/ (media: FAIL 1 missing), or the page keeps the meta of a
    # page (five lines, no media line)
    def test_the_page_prints_six_ok_lines(self):
        out, _ = self.rendered()
        run = verify(lesson_page(out))
        self.assertEqual((run.returncode, run.stdout), (0, LESSON_PASS + "media: ok\n"), run.stderr)

    # red: the template's rule body:not(:has(figure.clip)) #play-all deleted (the button shows, the guard
    # reports PLAYALL, the render lines FAIL), or a page with no clip fails the media check
    def test_a_dropped_clip_leaves_a_passing_page(self):
        out, _ = self.rendered()
        page = lesson_page(out, clip=False)
        run = verify(page)
        self.assertEqual((run.returncode, run.stdout), (0, LESSON_PASS + "media: ok\n"), run.stderr)
        text = page.read_text(encoding="utf-8")
        self.assertNotIn('<figure class="clip">', text)
        self.assertIn("<dd>%s — %s</dd>" % (CLIP_ID, DROP_REASON), text)
        self.assertTrue((self.clip(out) / "video.mp4").is_file())


if __name__ == "__main__":
    unittest.main()
