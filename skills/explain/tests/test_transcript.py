"""Tests for video/transcript.py: script.json to the transcript page (index.html) and
narration.md. Each test names the mutation of transcript.py that turns it red."""

import copy
import html
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
TEMPLATE = EXPLAIN / "templates" / "video-script.json"
VERIFY_SH = EXPLAIN / "scripts" / "verify.sh"
BIG_LINES = ["line %d alpha beta" % n for n in range(1, 21)]


def template_script():
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def title_scene(scene_id="intro", cites=None, narration="The video starts here."):
    return {
        "id": scene_id,
        "component": "title",
        "props": {"title": "Scene " + scene_id, "subtitle": "A subtitle", "cue": "The video"},
        "narration": narration,
        "cites": cites if cites is not None else [],
    }


def small_script(scenes, root, kind="topic"):
    script = template_script()
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
        """The template script with every cite and the code source on src/big.txt."""
        script = template_script()
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
        script = template_script()
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
        self.assertEqual(page.text["h1"], [template_script()["title"]])

    def test_backtick_span_becomes_code(self):
        """Red: backticks escaped literally instead of becoming <code>."""
        scene = title_scene(narration="Run `verify.sh` first. Then read `three` lines.")
        text = self.generate(small_script([scene], self.dir))
        self.assertIn("<p>Run <code>verify.sh</code> first. Then read <code>three</code> lines.</p>", text)
        self.assertNotIn("`", text)

    def test_code_scene_shows_lines_and_cites_path_from(self):
        """Red: the figure shows the wrong range (off by one), or the cite names another line."""
        script = template_script()
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
            ['kept.py:1 "one"', 'loose.py:1 "two" untracked'],
        )

    def test_no_git_directory_marks_nothing(self):
        """Red: every cite marked untracked when the root has no .git."""
        cites = [{"path": "src/big.txt", "line": 1, "snippet": "line 1"}]
        page = parse(self.generate(small_script([title_scene(cites=cites)], self.dir, kind="file")))
        self.assertEqual([text for _, text in self.cite_names(page)], ['big.txt:1 "line 1"'])

    def test_url_cite_without_line(self):
        """Red: a URL cite gets data-line, or the host is missing from the visible text."""
        cites = [{"path": "https://example.com/docs/a", "snippet": "a short quote"}]
        page = parse(self.generate(small_script([title_scene(cites=cites)], self.dir)))
        cite = page.cites[0]
        self.assertNotIn("data-line", cite["attrs"])
        self.assertEqual(cite["attrs"]["data-path"], "https://example.com/docs/a")
        self.assertEqual(cite["attrs"]["data-snippet"], "a short quote")
        self.assertEqual(" ".join(cite["text"].split()), 'example.com "a short quote"')

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
        script = template_script()
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
        script = template_script()
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


class UsageTest(TranscriptCase):

    def run_tool(self, *args):
        return subprocess.run([sys.executable, "-B", str(TOOL), *args], capture_output=True, text=True)

    def test_usage_and_bad_json_exit_two_with_one_line(self):
        """Red: a traceback (exit 1) on bad input, or exit 0."""
        bad = self.dir / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        for args in ([], [str(bad)], [str(bad), str(self.out)], [str(self.dir / "absent.json"), str(self.out)],
                     [str(bad), str(self.out), "--narrator"]):
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
        script = copy.deepcopy(template_script())
        del script["scenes"][0]["narration"]
        path = self.dir / "s.json"
        path.write_text(json.dumps(script), encoding="utf-8")
        proc = self.run_tool(str(path), str(self.out))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertEqual(len(proc.stderr.strip().split("\n")), 1, proc.stderr)


if __name__ == "__main__":
    unittest.main()
