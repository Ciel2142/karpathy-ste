"""Tests for video/transcript.py: script.json to the transcript page (index.html) and
narration.md. Each test names the mutation of transcript.py that turns it red."""

import contextlib
import copy
import html
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

EXPLAIN = Path(__file__).resolve().parent.parent
TOOL = EXPLAIN / "video" / "transcript.py"
CITE_CHECK = EXPLAIN / "scripts" / "cite_check.py"
# A brainrot-format script with every component (spec 5.3). transcript.py checks no limit, so
# its texts keep lengths that brainrot --check refuses.
COMPONENTS = EXPLAIN / "tests" / "fixtures" / "components-script.json"
VERIFY_SH = EXPLAIN / "scripts" / "verify.sh"
BIG_LINES = ["line %d alpha beta" % n for n in range(1, 21)]


def load_transcript():
    """A fresh transcript.py module, so a test can patch its attributes (FORMATS_FILE)."""
    spec = importlib.util.spec_from_file_location("transcript_under_test", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def components_script():
    return json.loads(COMPONENTS.read_text(encoding="utf-8"))


def title_scene(scene_id="intro", cites=None, narration="The video starts here."):
    return {
        "id": scene_id,
        "component": "title",
        "props": {"title": "Scene " + scene_id, "subtitle": "A subtitle", "cue": "The video"},
        "narration": narration,
        "cites": cites if cites is not None else [],
    }


def small_script(scenes, root, kind="topic"):
    script = components_script()
    script["subject"] = {"text": "a subject", "kind": kind}
    script["provenance"]["root"] = str(root)
    script["scenes"] = scenes
    return script


class Page(HTMLParser):
    """Sections (id, cites), every cite (attrs, text), the h1 and h2 text, the text of each
    pre>code block, the meta tags and the video element."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections = []
        self.cites = []
        self.video = None
        self.meta = {}
        self.text = {"h1": [], "h2": [], "pre-code": []}
        self._depth = 0
        self._cite = None
        self._in_pre = False
        self._into = None   # the key of self.text that receives character data

    def handle_starttag(self, tag, attrs):
        values = {name: value or "" for name, value in attrs}
        if tag == "meta" and "name" in values:
            self.meta[values["name"]] = values.get("content", "")
        elif tag == "section":
            self.sections.append({"id": values.get("id"), "cites": []})
            self._depth += 1
        elif tag == "video":
            self.video = dict(values, inside_section=self._depth > 0)
        elif tag == "cite":
            self._cite = {"attrs": values, "text": ""}
            self.cites.append(self._cite)
            if self._depth:
                self.sections[-1]["cites"].append(self._cite)
        elif tag == "pre":
            self._in_pre = True
        elif tag == "code" and self._in_pre:
            self._into = "pre-code"
        elif tag in ("h1", "h2"):
            self._into = tag
        else:
            return
        if self._into in self.text and tag in ("h1", "h2", "code"):
            self.text[self._into].append("")

    def handle_endtag(self, tag):
        if tag == "section":
            self._depth -= 1
        elif tag == "cite":
            self._cite = None
        elif tag == "pre":
            self._in_pre = False
        elif tag in ("h1", "h2", "code"):
            self._into = None

    def handle_data(self, data):
        if self._cite is not None:
            self._cite["text"] += data
        if self._into is not None:
            self.text[self._into][-1] += data


def parse(text):
    page = Page()
    page.feed(text)
    page.close()
    return page


class TranscriptCase(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(os.path.realpath(tmp.name))
        self.out = self.dir / "out"
        self.big = self.dir / "src" / "big.txt"
        self.big.parent.mkdir()
        self.big.write_text("\n".join(BIG_LINES) + "\n", encoding="utf-8")

    def generate(self, script, *extra):
        path = self.dir / "script.json"
        path.write_text(json.dumps(script), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-B", str(TOOL), str(path), str(self.out), *extra],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return (self.out / "index.html").read_text(encoding="utf-8")

    def retargeted(self):
        """The components script with every cite and the code source on src/big.txt."""
        script = components_script()
        script["provenance"]["root"] = str(self.dir)
        for scene in script["scenes"]:
            scene["cites"] = [{"path": "src/big.txt", "line": 3, "snippet": "alpha beta"}]
            if scene["component"] == "code-with-line-highlights":
                scene["props"]["source"] = {"path": "src/big.txt", "from": 3, "to": 6}
                scene["props"]["highlights"] = [{"from": 3, "to": 3, "cue": "The first line"}]
        return script

    def cite_names(self, page):
        return [(c["attrs"].get("data-path"), " ".join(c["text"].split())) for c in page.cites]


class SectionsTest(TranscriptCase):

    def test_one_section_per_scene_with_its_cites(self):
        """Red: all cites emitted in one block outside the sections (or in the last one)."""
        script = components_script()
        script["provenance"]["root"] = str(EXPLAIN)
        page = parse(self.generate(script))
        self.assertEqual([s["id"] for s in page.sections], [s["id"] for s in script["scenes"]])
        for section, scene in zip(page.sections, script["scenes"]):
            expected = sorted((c["path"], str(c["line"])) for c in scene["cites"])
            if scene["component"] == "code-with-line-highlights":
                source = scene["props"]["source"]
                expected = sorted(expected + [(source["path"], str(source["from"]))])
            got = sorted((c["attrs"]["data-path"], c["attrs"]["data-line"]) for c in section["cites"])
            self.assertEqual(got, expected, section["id"])

    def test_video_element_and_meta_outside_sections(self):
        """Red: <video> placed inside a scene section, or the rung meta missing."""
        page = parse(self.generate(self.retargeted()))
        self.assertEqual(page.meta.get("explain-rung"), "video")
        self.assertIsNotNone(page.video)
        self.assertEqual(page.video["src"], "video.mp4")
        self.assertIn("controls", page.video)
        self.assertFalse(page.video["inside_section"])
        self.assertEqual(page.text["h1"], [components_script()["title"]])

    def test_backtick_span_becomes_code(self):
        """Red: backticks escaped literally instead of becoming <code>."""
        scene = title_scene(narration="Run `verify.sh` first. Then read `three` lines.")
        text = self.generate(small_script([scene], self.dir))
        self.assertIn("<p>Run <code>verify.sh</code> first. Then read <code>three</code> lines.</p>", text)
        self.assertNotIn("`", text)

    def test_code_scene_shows_lines_and_cites_path_from(self):
        """Red: the figure shows the wrong range (off by one), or the cite names another line."""
        script = components_script()
        script["provenance"]["root"] = str(EXPLAIN)
        text = self.generate(script)
        source = [s for s in script["scenes"] if s["component"] == "code-with-line-highlights"][0]
        spec = source["props"]["source"]
        lines = VERIFY_SH.read_text(encoding="utf-8").split("\n")[spec["from"] - 1:spec["to"]]
        page = parse(text)
        self.assertEqual(page.text["pre-code"], ["\n".join(lines)])
        self.assertIn('<figure class="code">', text)
        self.assertIn("<figcaption><code>verify.sh:%d</code></figcaption>" % spec["from"], text)
        section = [s for s in page.sections if s["id"] == source["id"]][0]
        mine = [c for c in section["cites"] if c["attrs"]["data-line"] == str(spec["from"])]
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0]["attrs"]["data-path"], spec["path"])
        first = lines[0]
        self.assertIn(mine[0]["attrs"]["data-snippet"], " ".join(first.split()))
        self.assertLessEqual(len(mine[0]["attrs"]["data-snippet"].split()), 12)
        self.assertTrue(mine[0]["text"].startswith("verify.sh:%d " % spec["from"]), mine[0]["text"])

    def test_code_scene_with_blank_first_line_cites_the_first_text_line(self):
        """Red: the cite keeps the blank line, so the snippet is empty and cite_check fails."""
        (self.dir / "src" / "gap.txt").write_text("\n\nalpha beta gamma\nlast\n", encoding="utf-8")
        scene = {
            "id": "code", "component": "code-with-line-highlights",
            "props": {"title": "Gap", "source": {"path": "src/gap.txt", "from": 1, "to": 4}, "highlights": []},
            "narration": "The file has a gap.", "cites": [],
        }
        page = parse(self.generate(small_script([scene], self.dir, kind="file")))
        cite = page.sections[0]["cites"][0]["attrs"]
        self.assertEqual((cite["data-line"], cite["data-snippet"]), ("3", "alpha beta gamma"))


class CitesTest(TranscriptCase):

    def test_duplicate_basename_shows_shortest_unique_tail(self):
        """Red: basename only (app.py:3 twice), or one segment too few (x/app.py:3 twice)."""
        cites = [
            {"path": "a/x/app.py", "line": 3, "snippet": "one"},
            {"path": "b/x/app.py", "line": 3, "snippet": "two"},
            {"path": "c/other.py", "line": 1, "snippet": "three"},
        ]
        page = parse(self.generate(small_script([title_scene(cites=cites)], self.dir)))
        self.assertEqual(
            [text.split(" ")[0] for _, text in self.cite_names(page)],
            ["a/x/app.py:3", "b/x/app.py:3", "other.py:1"],
        )

    def test_untracked_file_is_marked(self):
        """Red: git ls-files not run, so the untracked file is not marked."""
        repo = self.dir / "repo"
        repo.mkdir()
        (repo / "kept.py").write_text("one\n", encoding="utf-8")
        (repo / "loose.py").write_text("two\n", encoding="utf-8")
        git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
        for args in (["init", "-q"], ["add", "kept.py"], ["commit", "-q", "-m", "x"]):
            subprocess.run(git + args, check=True, capture_output=True)
        cites = [
            {"path": "kept.py", "line": 1, "snippet": "one"},
            {"path": "loose.py", "line": 1, "snippet": "two"},
        ]
        page = parse(self.generate(small_script([title_scene(cites=cites)], repo, kind="file")))
        self.assertEqual(
            [text for _, text in self.cite_names(page)],
            ["kept.py:1 one", "loose.py:1 two untracked"],
        )

    def test_cite_block_sets_the_snippet_in_code(self):
        """Red: the snippet is quoted in the running text, the cites sit in a ul, or the untracked
        mark lands inside the code element."""
        repo = self.dir / "repo2"
        repo.mkdir()
        (repo / "loose.py").write_text("two\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, capture_output=True)
        cites = [{"path": "loose.py", "line": 1, "snippet": "two"},
                 {"path": "https://example.com/d", "snippet": "a quote"}]
        text = self.generate(small_script([title_scene(cites=cites)], repo, kind="file"))
        self.assertNotIn("<ul", text)
        self.assertIn('<cite data-path="loose.py" data-line="1" data-snippet="two">loose.py:1 '
                      "<code>two</code> untracked</cite>", text)
        self.assertIn('<cite data-path="https://example.com/d" data-snippet="a quote">example.com '
                      "<code>a quote</code></cite>", text)
        self.assertRegex(text, r'<div class="cites" data-ste="skip">\s*<cite')

    def test_no_git_directory_marks_nothing(self):
        """Red: every cite marked untracked when the root has no .git."""
        cites = [{"path": "src/big.txt", "line": 1, "snippet": "line 1"}]
        page = parse(self.generate(small_script([title_scene(cites=cites)], self.dir, kind="file")))
        self.assertEqual([text for _, text in self.cite_names(page)], ["big.txt:1 line 1"])

    def test_url_cite_without_line(self):
        """Red: a URL cite gets data-line, or the host is missing from the visible text."""
        cites = [{"path": "https://example.com/docs/a", "snippet": "a short quote"}]
        page = parse(self.generate(small_script([title_scene(cites=cites)], self.dir)))
        cite = page.cites[0]
        self.assertNotIn("data-line", cite["attrs"])
        self.assertEqual(cite["attrs"]["data-path"], "https://example.com/docs/a")
        self.assertEqual(cite["attrs"]["data-snippet"], "a short quote")
        self.assertEqual(" ".join(cite["text"].split()), "example.com a short quote")

    def test_cite_check_passes_on_generated_transcript(self):
        """Red: a scene section emitted without its cites (cite_check: "section N: no
        citation"). A <video> inside a section breaks nothing in cite_check, so that
        mutation is locked by test_video_element_and_meta_outside_sections."""
        self.generate(self.retargeted())
        proc = subprocess.run(
            [sys.executable, "-B", str(CITE_CHECK), str(self.out / "index.html")],
            capture_output=True, text=True,
        )
        self.assertEqual((proc.returncode, proc.stdout), (0, "cite_check: ok\n"), proc.stderr)


class OutputTest(TranscriptCase):

    def test_narration_md_lists_every_scene(self):
        """Red: a scene missing, scenes out of order, or the narration altered."""
        script = components_script()
        script["scenes"][0]["narration"] = "This video explains the `check` script. It runs four checks."
        script["provenance"]["root"] = str(EXPLAIN)
        self.generate(script)
        text = (self.out / "narration.md").read_text(encoding="utf-8")
        titles = [s["props"]["title"] for s in script["scenes"]]
        self.assertEqual([l for l in text.split("\n") if l.startswith("#")],
                         ["# " + script["title"]] + ["## " + t for t in titles])
        self.assertEqual(
            text, "\n".join(["# %s\n" % script["title"]]
                            + ["## %s\n\n%s\n" % (t, s["narration"]) for t, s in zip(titles, script["scenes"])]),
        )

    def test_html_escaped_in_every_field(self):
        """Red: one field written without html.escape (title, bullet, snippet, narration,
        subject, source or not_covered)."""
        script = components_script()
        script["provenance"]["root"] = str(EXPLAIN)
        script["title"] = '<b>&"'
        script["subject"]["text"] = "<s>&"
        script["provenance"]["source"] = "<q>&"
        script["provenance"]["not_covered"] = "<m>&"
        first, second = script["scenes"][0], script["scenes"][1]
        first["narration"] = "<script>alert(1)</script>"
        first["props"]["title"] = "<h>&"
        second["props"]["bullets"][0]["text"] = "<i>&\""
        second["cites"][0]["snippet"] = "<u>"
        script["scenes"][1]["cites"][0]["line"] = 12
        text = self.generate(script)
        for raw in ("<b>", "<s>", "<q>", "<m>", "<script>", "<h>", "<i>", "<u>"):
            self.assertNotIn(raw, text, raw)
        for field in ('<b>&"', "<s>&", "<q>&", "<m>&", "<script>alert(1)</script>", "<h>&", "<i>&\"", "<u>"):
            self.assertIn(html.escape(field, quote=True), text, field)
        page = parse(text)
        self.assertEqual(page.text["h1"], ['<b>&"'])
        self.assertEqual(page.sections[1]["cites"][0]["attrs"]["data-snippet"], "<u>")

    def test_narrator_row_from_flag(self):
        """Red: the flag ignored, or pending written when the flag is present (or the reverse)."""
        script = self.retargeted()
        self.assertIn("<dt>Narrator</dt><dd>kokoro</dd>", self.generate(script, "--narrator", "kokoro"))
        self.assertIn("<dt>Narrator</dt><dd>pending</dd>", self.generate(script))

    def test_brainrot_rows_and_portrait_video(self):
        """Red: the Format or Background row missing or in the wrong order, the portrait class
        not on the video element, or the flag value not written into the Background row."""
        text = self.generate(self.retargeted(), "--background", "bg-1s.mp4 @ 0.0 s (loop)")
        self.assertIn("<div><dt>Format</dt><dd>brainrot (1080\u00d71920)</dd></div>", text)
        self.assertIn("<div><dt>Background</dt><dd>bg-1s.mp4 @ 0.0 s (loop)</dd></div>", text)
        self.assertLess(text.index("<dt>Narrator</dt>"), text.index("<dt>Format</dt>"))
        self.assertLess(text.index("<dt>Format</dt>"), text.index("<dt>Background</dt>"))
        page = parse(text)
        self.assertEqual(page.video["class"], "portrait")
        self.assertEqual(page.video["src"], "video.mp4")
        self.assertIn("controls", page.video)
        self.assertFalse(page.video["inside_section"])

    def test_brainrot_background_pending_by_default(self):
        """Red: the default of --background is not "pending" (or the row is left out)."""
        text = self.generate(self.retargeted())
        self.assertIn("<div><dt>Background</dt><dd>pending</dd></div>", text)

    def test_brainrot_background_is_escaped(self):
        """Red: the --background value written without html.escape (a clip name can hold
        & < > or quotes)."""
        text = self.generate(self.retargeted(), "--background", '<b>Run & "Go".mp4 @ 0.0 s')
        self.assertNotIn("<b>Run", text)
        self.assertIn("<dd>%s</dd>" % html.escape('<b>Run & "Go".mp4 @ 0.0 s', quote=True), text)

    def module_with_formats(self, content):
        """A transcript module whose FORMATS_FILE is a temp file holding `content`."""
        module = load_transcript()
        path = self.dir / "formats.json"
        path.write_text(content, encoding="utf-8")
        module.FORMATS_FILE = path
        return module

    def test_format_row_size_from_formats_file(self):
        """Red: the Format row size is a literal in transcript.py (or read from formats.json at
        import time), so a changed or patched formats file has no effect."""
        formats = json.loads((EXPLAIN / "video" / "formats.json").read_text(encoding="utf-8"))
        formats["brainrot"]["width"] = 1000
        module = self.module_with_formats(json.dumps(formats))
        self.assertIn("<dd>brainrot (1000×1920)</dd>", module.format_rows(self.retargeted(), "pending"))

    def test_unusable_formats_file_is_a_script_error(self):
        """Red: a missing or invalid formats.json, or one without the brainrot width and height,
        escapes as a traceback instead of one stderr line and exit 2."""
        script_path = self.dir / "script.json"
        script_path.write_text(json.dumps(self.retargeted()), encoding="utf-8")
        cases = {"missing": None, "invalid JSON": "{ not json", "no rows": "[]", "no size": '{"brainrot": {}}'}
        for name, content in cases.items():
            with self.subTest(name):
                module = self.module_with_formats("{}" if content is None else content)
                if content is None:
                    module.FORMATS_FILE = self.dir / "gone" / "formats.json"
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    code = module.main([str(script_path), str(self.out)])
                self.assertEqual(code, 2)
                self.assertRegex(err.getvalue(), r"\Atranscript\.py: .*formats\.json.*\n\Z")

    def test_brainrot_transcript_passes_verify(self):
        """Red: a Format or Background row, or the portrait video, that makes the page fail the
        self-contained, citations or prose check of verify.sh (the rows sit in the
        data-ste="skip" dl, so the prose check does not lint them)."""
        self.generate(self.retargeted(), "--background", "bg-1s.mp4 @ 0.0 s (loop)")
        run = subprocess.run([str(VERIFY_SH), str(self.out / "index.html")],
                             capture_output=True, text=True, timeout=300)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stdout.splitlines(),
                         ["self-contained: ok", "citations: ok", "prose: ok"])

    def test_footer_rows_and_provenance_attributes(self):
        """Red: a footer row missing, or data-root or data-kind not taken from the script."""
        script = self.retargeted()
        text = self.generate(script)
        prov = script["provenance"]
        self.assertIn('id="provenance" data-root="%s" data-kind="file"' % self.dir, text)
        for row in (
            "<dt>Subject</dt><dd>scripts/verify.sh (file)</dd>",
            "<dt>Source</dt><dd>%s</dd>" % prov["source"],
            "<dt>Commit</dt><dd>%s</dd>" % prov["commit"],
            "<dt>Dirty</dt><dd>%s</dd>" % prov["dirty"],
            "<dt>Date</dt><dd>%s</dd>" % prov["date"],
        ):
            self.assertIn(row, text)
        self.assertIn('<p class="not-covered">Not covered: %s</p>' % prov["not_covered"], text)

    def test_component_text_is_shown(self):
        """Red: one component's on-screen text dropped (subtitle, bullets, diagram labels,
        before and after lists)."""
        text = self.generate(self.retargeted())
        for shown in (
            "<p>Three or four checks before handoff</p>",
            "<li>Self-contained: no remote links</li>",
            "<li>Open the page by hand</li>",
            "<li>Read one line for each check</li>",
            "Without verify.sh",
            "With verify.sh",
        ):
            self.assertIn(shown, text)
        diagram = re.search(r'<ul data-ste="skip">(.*?)</ul>', text).group(1)
        for label in ("verify.sh", "Chrome", "cite_check", "ste_lint", "render", "citations", "prose"):
            self.assertIn(label, diagram)


class FilmTest(TranscriptCase):

    def film(self, kind="file"):
        """A film script rooted at self.dir: three scenes, each an id, a narration and one cite
        on src/big.txt line 3. A film scene has no component and no props."""
        narrations = {
            "type": "The author types the prompt.",
            "forms": "Three forms come out of it.",
            "ends": "The film ends on the card.",
        }
        scenes = [
            {"id": scene_id, "narration": narration,
             "cites": [{"path": "src/big.txt", "line": 3, "snippet": "alpha beta"}]}
            for scene_id, narration in narrations.items()
        ]
        script = small_script(scenes, self.dir, kind=kind)
        script["format"] = "film"
        return script

    def run_tool(self, script, *extra):
        path = self.dir / "script.json"
        path.write_text(json.dumps(script), encoding="utf-8")
        return subprocess.run([sys.executable, "-B", str(TOOL), str(path), str(self.out), *extra],
                              capture_output=True, text=True, timeout=60)

    def test_film_section_is_id_narration_and_cites(self):
        """Red: a film scene sent through BODIES (KeyError 'component', exit 2); a heading other
        than the id; a backtick span left as text, or a narration written without html.escape;
        a cite list that is not the scene's own; an on-screen block (a <figure> or a <ul>)
        in a film section."""
        script = self.film()
        script["scenes"][0]["narration"] = "Type `verify.sh` first."
        script["scenes"][1]["narration"] = '<b> & "q" come next.'
        text = self.generate(script)
        page = parse(text)
        ids = ["type", "forms", "ends"]
        self.assertEqual([s["id"] for s in page.sections], ids)
        self.assertEqual(page.text["h2"], ids)
        bodies = re.findall(r'<section id="[a-z]+">\n(.*?)\n</section>', text, re.S)
        paragraphs = ["Type <code>verify.sh</code> first.",
                      "&lt;b&gt; &amp; &quot;q&quot; come next.",
                      script["scenes"][2]["narration"]]
        self.assertEqual(len(bodies), 3)
        for section, body, paragraph in zip(page.sections, bodies, paragraphs):
            self.assertEqual(re.findall(r"<p>(.*?)</p>", body), [paragraph], section["id"])
            cites = [(c["attrs"]["data-path"], c["attrs"]["data-line"], c["attrs"]["data-snippet"])
                     for c in section["cites"]]
            self.assertEqual(cites, [("src/big.txt", "3", "alpha beta")], section["id"])
        self.assertNotIn("<figure", text)
        self.assertEqual(re.findall(r'<div class="cites"[^>]*>', text), ['<div class="cites" data-ste="skip">'] * 3)

    def test_film_nav_and_narration_md_use_the_id(self):
        """Red: props["title"] read for a film in the nav or in narration.md (KeyError, exit 2),
        or a nav link or a ## line that shows anything but the scene id."""
        script = self.film()
        script["scenes"][0]["narration"] = "Type `verify.sh` first."
        text = self.generate(script)
        ids = [s["id"] for s in script["scenes"]]
        nav = re.search(r'<nav id="toc">(.*?)</nav>', text, re.S).group(1)
        self.assertEqual(re.findall(r'<a href="#([^"]*)">([^<]*)</a>', nav), [(i, i) for i in ids])
        narration = (self.out / "narration.md").read_text(encoding="utf-8")
        self.assertEqual([l for l in narration.split("\n") if l.startswith("#")],
                         ["# " + script["title"]] + ["## " + i for i in ids])
        self.assertEqual(
            narration, "\n".join(["# %s\n" % script["title"]]
                                 + ["## %s\n\n%s\n" % (s["id"], s["narration"]) for s in script["scenes"]]),
        )

    def test_film_cite_labels_come_from_the_cites_alone(self):
        """Red: Cites reads component (or props.source) of a film scene (KeyError, exit 2), or
        builds its labels from anything but the cites (two util.py files shown as util.py)."""
        script = self.film()
        for scene, folder in zip(script["scenes"], ("a", "b")):
            (self.dir / folder).mkdir()
            (self.dir / folder / "util.py").write_text("import os\n", encoding="utf-8")
            scene["cites"] = [{"path": folder + "/util.py", "line": 1, "snippet": "import os"}]
        page = parse(self.generate(script))
        self.assertEqual([text.split(" ")[0] for _, text in self.cite_names(page)],
                         ["a/util.py:1", "b/util.py:1", "big.txt:3"])

    def test_film_page_has_no_format_row_and_a_landscape_video(self):
        """Red: a film laid out as brainrot (a Format or Background row, class="portrait" on the
        video, a whitespace line left where {{format_rows}} sits), or --background written into
        a film page, or the Narrator row not taken from the flag."""
        for extra in ((), ("--background", "x.mp4 @ 0.0 s")):
            text = self.generate(self.film(), "--narrator", "say", *extra)
            self.assertNotIn("<dt>Format</dt>", text)
            self.assertNotIn("<dt>Background</dt>", text)
            self.assertNotIn("x.mp4", text)
            self.assertIn('<video controls src="video.mp4"></video>', text)
            self.assertNotIn("class", parse(text).video)
            self.assertIn("<dt>Narrator</dt><dd>say</dd></div>\n    </dl>", text)

    def test_a_script_without_a_format_is_a_film(self):
        """Red: is_film is true only for "format": "film", or is_brainrot reads a script without
        the key as brainrot, so the script without the key goes through BODIES (KeyError
        'component', exit 2); or its page or narration.md differs from the film's."""
        keyless = self.film()
        del keyless["format"]
        written = []
        for script in (keyless, self.film()):
            proc = self.run_tool(script, "--narrator", "say", "--background", "x.mp4 @ 0.0 s")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            written.append([(self.out / name).read_bytes() for name in ("index.html", "narration.md")])
        self.assertEqual(written[0], written[1])

    def test_a_clip_is_a_film_page(self):
        """Red: is_film is true only for "format": "film", so a clip goes through BODIES (KeyError
        'component', exit 2); or its page or narration.md differs from the film's."""
        written = []
        for script in (dict(self.film(), format="clip"), self.film()):
            proc = self.run_tool(script, "--narrator", "say", "--background", "x.mp4 @ 0.0 s")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            written.append([(self.out / name).read_bytes() for name in ("index.html", "narration.md")])
        self.assertEqual(written[0], written[1])

    def test_html_lang_follows_the_script(self):
        """Red: line 2 of the template keeps lang="en" (a Russian page says en), the marker is
        filled with a fixed value, or a script with no lang key has no default (KeyError,
        exit 2) or gets an empty one."""
        russian = dict(self.film(), lang="ru")
        english = dict(self.film(), lang="en")
        for name, script, tag in (("ru", russian, '<html lang="ru">'),
                                  ("en", english, '<html lang="en">'),
                                  ("none", self.film(), '<html lang="en">')):
            with self.subTest(lang=name):
                text = self.generate(script)
                self.assertEqual(text.split("\n")[1], tag)
                self.assertNotIn("{{lang}}", text)

    def test_film_scene_without_a_cites_key(self):
        """Red: scene["cites"] read for a film scene (KeyError 'cites', exit 2): a topic film
        scene has no cites and the page is still written, with an empty cite list."""
        script = self.film(kind="topic")
        del script["scenes"][1]["cites"]
        text = self.generate(script)
        page = parse(text)
        self.assertEqual([len(s["cites"]) for s in page.sections], [1, 0, 1])
        self.assertEqual(text.count('<div class="cites"'), 2)   # the scene without cites has no block

    def test_film_scene_without_narration_exits_two(self):
        """Red: narration or id read with a default (scene.get) at every place a film scene is
        read (the section and narration.md for the narration; the section, the nav and the
        heading for the id), so a scene without one writes a page instead of ending in the
        one-line contract error."""
        for missing in ("narration", "id"):
            with self.subTest(missing):
                script = self.film()
                del script["scenes"][1][missing]
                proc = self.run_tool(script)
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertEqual(proc.stdout, "")
                lines = proc.stderr.strip().split("\n")
                self.assertEqual(len(lines), 1, proc.stderr)
                self.assertTrue(
                    lines[0].startswith("transcript.py: script does not match the contract:"), lines[0])
                self.assertFalse((self.out / "index.html").exists())

    def test_film_transcript_passes_verify(self):
        """Red: a film section without its cites (citations), a heading that fails the lint
        (prose), or a remote reference on the page (self-contained)."""
        self.generate(self.film())
        run = subprocess.run([str(VERIFY_SH), str(self.out / "index.html")],
                             capture_output=True, text=True, timeout=300)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stdout.splitlines(),
                         ["self-contained: ok", "citations: ok", "prose: ok"])


class UsageTest(TranscriptCase):

    def run_tool(self, *args):
        return subprocess.run([sys.executable, "-B", str(TOOL), *args], capture_output=True, text=True)

    def test_usage_and_bad_json_exit_two_with_one_line(self):
        """Red: a traceback (exit 1) on bad input, or exit 0."""
        bad = self.dir / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        for args in ([], [str(bad)], [str(bad), str(self.out)], [str(self.dir / "absent.json"), str(self.out)],
                     [str(bad), str(self.out), "--narrator"], [str(bad), str(self.out), "--background"]):
            proc = self.run_tool(*args)
            self.assertEqual(proc.returncode, 2, (args, proc.stderr))
            self.assertEqual(proc.stdout, "")
            self.assertEqual(len(proc.stderr.strip().split("\n")), 1, (args, proc.stderr))

    def test_dotdot_source_path_is_rejected(self):
        """Red: the inside-the-data-root guard removed from source_lines (the outside file is read)."""
        root = self.dir / "root"
        (root / "src").mkdir(parents=True)
        (self.dir / "outside.txt").write_text("secret one\nsecret two\nsecret three\n", encoding="utf-8")
        scene = {
            "id": "code", "component": "code-with-line-highlights",
            "props": {"title": "Out", "source": {"path": "../outside.txt", "from": 1, "to": 3}, "highlights": []},
            "narration": "The file lies outside.", "cites": [],
        }
        path = self.dir / "s.json"
        path.write_text(json.dumps(small_script([scene], root, kind="file")), encoding="utf-8")
        proc = self.run_tool(str(path), str(self.out))
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(
            proc.stderr.strip().split("\n"),
            ['transcript.py: source.path "../outside.txt" must be a relative path inside the data root'],
        )
        self.assertFalse((self.out / "index.html").exists())

    def test_script_missing_a_field_exits_two(self):
        """Red: KeyError traceback (exit 1) when a scene lacks its narration."""
        script = copy.deepcopy(components_script())
        del script["scenes"][0]["narration"]
        path = self.dir / "s.json"
        path.write_text(json.dumps(script), encoding="utf-8")
        proc = self.run_tool(str(path), str(self.out))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertEqual(len(proc.stderr.strip().split("\n")), 1, proc.stderr)


if __name__ == "__main__":
    unittest.main()
