"""Tests for the course hub: `course.py hub` and `render_hub` (spec section 7), and the
`course` rung of verify.sh (spec section 8).

The static cases render the hub of the fixture course (`tests/fixtures/course/`, over the fake
root `tests/fixtures/course-root/`) and read the HTML: cites through `cite_check.check`, prose
through `ste_lint.py --html`, the flow diagram through a small parser of its `g.hop` boxes.
Each case copies both fixture directories to a temporary directory first.

Two Chrome cases run verify.sh on a generated hub: the fixture hub prints seven lines (all `ok`,
`bpmn: none`), and a hub whose linked lesson directory is gone fails the media check. Each
Chrome run gets a private TMPDIR, so every Chrome process carries that path and the cleanup can
kill a stray one (the pattern of tests/test_page_template.py).
"""

import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(SKILL / "scripts"))

import cite_check  # noqa: E402
import course  # noqa: E402

FIXTURES = HERE / "fixtures"
TEMPLATE = SKILL / "templates" / "page.html"
VERIFY = SKILL / "scripts" / "verify.sh"
COURSE_PY = SKILL / "scripts" / "course.py"
STE_LINT = SKILL.parent / "ste" / "scripts" / "ste_lint.py"
VIEW_W = 600


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = course.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class Boxes(HTMLParser):
    """The boxes of the flow diagram: `g.hop[data-hop]` with its first rect, the href of the
    `a` that holds the rect (or None), and the text of the box."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.boxes = {}
        self.svg_views = []
        self._box = None
        self._depth = 0
        self._href = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "svg" and values.get("viewbox"):
            self.svg_views.append([float(n) for n in values["viewbox"].split()])
        if tag == "g" and "data-hop" in values and self._box is None:
            self._box = {"rect": None, "href": None, "text": ""}
            self.boxes[values["data-hop"]] = self._box
            self._depth = 1
            return
        if self._box is None:
            return
        if tag == "g":
            self._depth += 1
        if tag == "a":
            self._href = values.get("href")
        if tag == "rect" and self._box["rect"] is None:
            self._box["rect"] = {k: float(values[k]) for k in ("x", "y", "width", "height")}
            self._box["rect"]["class"] = values.get("class", "")
            self._box["href"] = self._href

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self._box is None:
            return
        if tag == "a":
            self._href = None
        if tag == "g":
            self._depth -= 1
            if self._depth == 0:
                self._box = None

    def handle_data(self, data):
        if self._box is not None:
            self._box["text"] += data


def boxes_of(html):
    parser = Boxes()
    parser.feed(html)
    parser.close()
    return parser


FAIL_PATH = re.compile(
    r'<path class="fail" data-from="([^"]+)" data-to="([^"]+)" d="M(\d+) (\d+) V(\d+) H(\d+)"')


def fail_paths(html):
    """{(from hop, to hop): (x, y1, y2, x2)} of the dashed "on failure" connectors."""
    return {(m[0], m[1]): tuple(int(n) for n in m[2:]) for m in FAIL_PATH.findall(html)}


def text_of(html):
    """The visible text of the HTML, tags removed, character references decoded."""
    import html as html_module

    return html_module.unescape(re.sub(r"<[^>]+>", "", html))


def lesson_hrefs(html):
    return re.findall(r'href="(lessons/[^"]*)"', html)


class HubCase(unittest.TestCase):
    """A private copy of the fixture per test; `self.course` is the parsed course.json."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = os.path.realpath(tmp.name)
        self.dir = os.path.join(self.base, "course")
        self.root = os.path.join(self.base, "course-root")
        shutil.copytree(FIXTURES / "course", self.dir)
        shutil.copytree(FIXTURES / "course-root", self.root)
        self.course = course.load(self.dir)
        self.template = TEMPLATE.read_text(encoding="utf-8")

    def render(self):
        return course.render_hub(self.dir, self.course, self.template)

    def lesson(self, lesson_id):
        for block in self.course["blocks"]:
            for lesson in block["lessons"]:
                if lesson["id"] == lesson_id:
                    return lesson
        raise KeyError(lesson_id)

    def git(self, *args):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        return subprocess.run(
            ["git", "-C", self.root, *args], check=True, env=env, capture_output=True, text=True,
        ).stdout.strip()


class HubStaticTest(HubCase):
    def test_hub_passes_cite_check(self):
        html = self.render()
        self.assertEqual(cite_check.check(html, self.dir), [])
        # every cite of every code or docs hop is on the page, in the markup of convention 2
        self.assertEqual(html.count("<cite "), 4)
        self.assertIn(
            '<cite data-path="svc-a/Handler.java" data-line="4" '
            'data-snippet="@Listener(queue = &quot;IN_QUEUE&quot;)">Handler.java:4 '
            '<code>@Listener(queue = &quot;IN_QUEUE&quot;)</code></cite>', html)
        root = re.search(r'<div id="provenance" data-root="([^"]*)" data-kind="topic">', html)
        self.assertIsNotNone(root)
        self.assertEqual(root.group(1), self.root)  # absolute, resolved from "../course-root"

    def test_hub_passes_ste_lint(self):
        self.lesson("entry-reject").update(status="failed", reason="verify.sh: render 500x844 FAIL")
        path = os.path.join(self.base, "hub.html")
        Path(path).write_text(self.render(), encoding="utf-8")
        proc = subprocess.run([sys.executable, "-B", str(STE_LINT), "--html", path],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("0 errors, 0 warnings", proc.stdout)

    def test_hub_links_only_done_lessons(self):
        self.lesson("exit-deliver").update(status="dropped", reason="User asked.")
        html = self.render()
        self.assertEqual(sorted(set(lesson_hrefs(html))), ["lessons/entry-receive/index.html"])
        boxes = boxes_of(html).boxes
        self.assertEqual(sorted(boxes), ["confirm", "deliver", "receive", "reject", "validate"])
        for hop in ("receive", "validate"):
            self.assertEqual(boxes[hop]["href"], "lessons/entry-receive/index.html", hop)
            self.assertNotIn("not built", boxes[hop]["text"], hop)
        for hop in ("reject", "deliver", "confirm"):
            self.assertIsNone(boxes[hop]["href"], hop)
            self.assertIn("not built", boxes[hop]["text"], hop)
        # a dropped lesson shows its reason and no link; its question is still listed
        self.assertIn("How does the message reach the target?", html)
        self.assertIn("User asked.", html)

    def test_hub_failure_hop_in_lower_row(self):
        boxes = boxes_of(self.render()).boxes
        main = [boxes[h]["rect"] for h in ("receive", "validate", "deliver", "confirm")]
        self.assertEqual(len({r["y"] for r in main}), 1, "main hops share one row")
        self.assertEqual([r["x"] for r in main], sorted(r["x"] for r in main), "left to right")
        branch, failure = boxes["validate"]["rect"], boxes["reject"]["rect"]
        self.assertGreater(failure["x"], branch["x"], "the failure hop hangs under its branch hop")
        self.assertLessEqual(failure["x"] + failure["width"], branch["x"] + branch["width"])
        self.assertGreaterEqual(failure["y"], branch["y"] + branch["height"] + 40)
        self.assertIn("on failure", self.render())

    def test_hub_failure_connectors_start_at_their_branch_hop(self):
        """Two failures of one hop (reject, timeout of validate) and a failure of a failure
        (retry of reject): each dashed connector starts at the bottom edge of the box of its
        branch hop, ends at the left edge of its failure box, and crosses no other box."""
        hops = self.course["hops"]
        at = [h["id"] for h in hops].index("reject") + 1
        extra = [
            dict(hops[4], id="timeout", **{"from": "svc-a", "to": "queue"}, branch="validate"),
            dict(hops[4], id="retry", **{"from": "source system", "to": "svc-a"}, branch="reject"),
        ]
        self.course["hops"] = hops[:at] + extra + hops[at:]
        self.lesson("entry-reject")["hops"] += ["timeout", "retry"]
        self.assertEqual(course.check(self.dir, self.course), [])
        html = self.render()
        boxes = {hop: box["rect"] for hop, box in boxes_of(html).boxes.items()}
        paths = fail_paths(html)
        self.assertEqual(sorted(paths), [("reject", "retry"), ("validate", "reject"),
                                         ("validate", "timeout")])
        for (source, target), (x, y1, y2, x2) in paths.items():
            top, box = boxes[source], boxes[target]
            self.assertEqual(y1, top["y"] + top["height"] + 1, (source, target))
            self.assertTrue(top["x"] < x < top["x"] + top["width"], (source, target))
            self.assertTrue(box["y"] < y2 < box["y"] + box["height"], (source, target))
            self.assertEqual(x2, box["x"] - 3, (source, target))
            for other, rect in boxes.items():
                if other in (source, target):
                    continue
                crosses = (rect["x"] < x < rect["x"] + rect["width"]
                           and rect["y"] < y2 and y1 < rect["y"] + rect["height"])
                self.assertFalse(crosses, "%s -> %s crosses %s" % (source, target, other))

    def test_hub_evidence_styles_and_legend(self):
        boxes = boxes_of(self.render()).boxes
        self.assertIn("ev-code", boxes["receive"]["rect"]["class"])
        self.assertIn("ev-docs", boxes["deliver"]["rect"]["class"])
        self.assertIn("ev-inferred", boxes["confirm"]["rect"]["class"])
        html = self.render()
        for word in ("code", "docs", "inferred"):
            self.assertRegex(html, r'<rect [^>]*class="ev-%s legend"' % word)

    def test_hub_wraps_long_chains_into_rows_inside_the_view_box(self):
        hops = self.course["hops"]
        extra = [dict(hops[0], id="extra-%d" % n, branch=None) for n in range(7)]
        self.course["hops"] = hops + extra
        self.lesson("exit-deliver")["hops"] += [h["id"] for h in extra]
        parser = boxes_of(self.render())
        (_, _, width, height), = parser.svg_views[:1]
        self.assertEqual(width, VIEW_W)
        rows = sorted({b["rect"]["y"] for h, b in parser.boxes.items() if h != "reject"})
        self.assertEqual(len(rows), 3, "11 main hops at 4 a row")
        for hop, box in parser.boxes.items():
            rect = box["rect"]
            self.assertGreaterEqual(rect["x"], 0, hop)
            self.assertLessEqual(rect["x"] + rect["width"], VIEW_W, hop)
            self.assertLessEqual(rect["y"] + rect["height"], height, hop)
        # the failure row sits between the first row and the second
        self.assertLess(parser.boxes["reject"]["rect"]["y"], rows[1])

    def test_hub_marks_moved_source(self):
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")
        head = self.git("rev-parse", "--short", "HEAD")
        self.course["sources"][0]["commit"] = "0000000"
        self.course["sources"][1]["commit"] = head
        html = self.render()
        self.assertIn("0000000 → %s, moved after planning" % head, text_of(html))
        self.assertEqual(html.count("moved after planning"), 1)

    def test_hub_in_russian_has_no_english_outside_code(self):
        ru = {
            "title": "Как сообщение идёт от источника к цели",
            "question": "Что происходит с одним сообщением на каждом шаге?",
        }
        self.course.update(ru, lang="ru")
        self.course["not_covered"] = ["Экран администратора не лежит на пути сообщения."]
        names = {"source system": "система-источник", "svc-a": "сервис", "target": "цель"}
        for hop in self.course["hops"]:
            hop["from"], hop["to"] = names[hop["from"]], names[hop["to"]]
            hop["what"] = "Сервис передаёт сообщение дальше."
        for block in self.course["blocks"]:
            block["title"] = "Вход" if block["id"] == "entry" else "Выход"
            for lesson in block["lessons"]:
                lesson["question"] = "Как сервис принимает сообщение?"
                lesson["brief"] = "Прочитайте обработчик."
        self.lesson("entry-reject").update(status="failed", reason="Проверка не прошла.")
        self.assertEqual(course.check(self.dir, self.course), [])
        html = self.render()
        self.assertEqual(cite_check.check(html, self.dir), [])
        body = html[html.index("<header>"):html.index("</footer>")]
        body = re.sub(r'<div class="cites">.*?</div>', "", body, flags=re.S)
        body = re.sub(r"<code>.*?</code>", "", body, flags=re.S)
        body = re.sub(r"<title[^>]*>.*?</title>", "", body, flags=re.S)
        self.assertEqual(re.findall(r"[A-Za-z]{2,}", text_of(body)), [])
        path = os.path.join(self.base, "hub.html")
        Path(path).write_text(html, encoding="utf-8")
        proc = subprocess.run([sys.executable, "-B", str(STE_LINT), "--html", path],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_hub_head_keeps_the_template_chrome(self):
        self.course["lang"] = "ru"
        html = self.render()
        self.assertTrue(html.startswith('<!doctype html>\n<html lang="ru">'), html[:40])
        self.assertIn('<meta name="explain-rung" content="course">', html)
        self.assertNotIn('content="page"', html)
        self.assertIn("<title>%s</title>" % self.course["title"], html)
        for kept in ("window.explainJsErrors = 0;", "function explainPlayer(",
                     "Guard, part 2 of 2", "--accent: #c2613f;"):
            self.assertIn(kept, html)
        self.assertNotIn("Copy this file to out/<run>/index.html", html)  # no template demo
        self.assertNotIn("How do you build a page from this template?", html)
        nav = re.search(r'<nav id="toc">(.*?)</nav>', html, re.S).group(1)
        self.assertEqual(re.findall(r'href="#([^"]+)"', nav), ["flow", "block-entry", "block-exit"])
        # the switch of the template, last in the nav, its label in the course language
        self.assertTrue(nav.rstrip().endswith(
            '<label class="sources"><input type="checkbox" id="show-sources"> Источники</label>'))
        self.assertIn('<p class="not-covered">Не покрыто: The admin screen', html)
        self.course["lang"] = "en"
        english = self.render()
        self.assertIn('<input type="checkbox" id="show-sources"> Sources</label>\n</nav>', english)
        self.assertIn('<p class="not-covered">Not covered: The admin screen', english)

    def test_hub_escapes_course_text(self):
        self.course["title"] = "A <b>bold</b> & title"
        self.lesson("entry-receive")["question"] = "Why <script>?"
        html = self.render()
        self.assertIn("A &lt;b&gt;bold&lt;/b&gt; &amp; title", html)
        self.assertNotIn("<b>bold</b>", html)
        self.assertNotIn("Why <script>", html)

    def test_hub_template_without_an_anchor_raises(self):
        for anchor in ("<header>", "</footer>"):
            with self.subTest(anchor=anchor):
                with self.assertRaises(ValueError) as caught:
                    course.render_hub(self.dir, self.course, self.template.replace(anchor, ""))
                self.assertIn(anchor, str(caught.exception))
        no_switch = re.sub(r'<label class="sources">.*?</label>', "", self.template)
        with self.assertRaises(ValueError) as caught:
            course.render_hub(self.dir, self.course, no_switch)
        self.assertIn("Sources switch", str(caught.exception))
        doubled = self.template.replace("<header>", "<header>\n<header>")
        with self.assertRaises(ValueError):
            course.render_hub(self.dir, self.course, doubled)


class HubCliTest(HubCase):
    def state(self):
        return course.load(self.dir)["state"]

    def approve(self):
        course.save(self.dir, dict(self.course, state="approved",
                                   approved_shape=course.shape(self.course)))

    def test_hub_sets_done_only_when_nothing_open(self):
        self.approve()
        self.assertEqual(run_cli("hub", self.dir)[0], 0)
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "index.html")))
        self.assertEqual(self.state(), "approved", "two lessons are still pending")
        data = course.load(self.dir)
        for block in data["blocks"]:
            for lesson in block["lessons"]:
                if lesson["status"] == "pending":
                    lesson.update(status="building")
        course.save(self.dir, data)
        self.assertEqual(run_cli("hub", self.dir)[0], 0)
        self.assertEqual(self.state(), "approved", "a building lesson is still open")
        for block in data["blocks"]:
            for lesson in block["lessons"]:
                if lesson["status"] == "building":
                    lesson.update(status="failed", reason="verify.sh failed.")
        course.save(self.dir, data)
        code, out, err = run_cli("hub", self.dir)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(self.state(), "done")
        self.assertIn(os.path.join(self.dir, "index.html"), out)

    def test_hub_refuses_a_course_that_fails_check(self):
        """A failing check prints its lines and the count, exits 1 and writes nothing: a
        schema fault, and an approved course whose shape changed after approval."""
        self.approve()
        approved = Path(self.dir, "course.json").read_bytes()
        data = course.load(self.dir)
        data["not_covered"] = 5
        course.save(self.dir, data)
        code, out, err = run_cli("hub", self.dir)
        self.assertEqual((code, err), (1, ""))
        self.assertEqual(out, "schema: not_covered: must be a list\ncourse: 1 failures\n")
        self.assertFalse(os.path.exists(os.path.join(self.dir, "index.html")))
        Path(self.dir, "course.json").write_bytes(approved)
        data = course.load(self.dir)
        data["hops"][-1]["branch"] = "deliver"
        course.save(self.dir, data)
        before = Path(self.dir, "course.json").read_bytes()
        code, out, err = run_cli("hub", self.dir)
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines(), [course.STATE_CHANGED, "course: 1 failures"])
        self.assertFalse(os.path.exists(os.path.join(self.dir, "index.html")))
        self.assertEqual(Path(self.dir, "course.json").read_bytes(), before)

    def test_hub_leaves_a_planned_course_planned(self):
        for block in self.course["blocks"]:
            for lesson in block["lessons"]:
                lesson.update(status="dropped", reason="User asked.")
        course.save(self.dir, self.course)
        self.assertEqual(run_cli("hub", self.dir)[0], 0)
        self.assertEqual(self.state(), "planned")

    def test_hub_write_is_atomic(self):
        self.assertEqual(run_cli("hub", self.dir)[0], 0)
        self.assertEqual(sorted(os.listdir(self.dir)), ["course.json", "index.html", "lessons"])

    def test_hub_template_error_exits_2_with_one_line(self):
        broken = os.path.join(self.base, "page.html")
        Path(broken).write_text(self.template.replace("</footer>", ""), encoding="utf-8")
        before = Path(self.dir, "course.json").read_bytes()
        for template in (broken, os.path.join(self.base, "absent.html")):
            with self.subTest(template=template), mock.patch.object(course, "TEMPLATE", template):
                code, out, err = run_cli("hub", self.dir)
                self.assertEqual((code, out), (2, ""))
                self.assertEqual(len(err.splitlines()), 1, err)
                self.assertTrue(err.startswith("course: hub: "), err)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "index.html")))
        self.assertEqual(Path(self.dir, "course.json").read_bytes(), before)

    def test_hub_usage_and_read_errors_exit_2(self):
        for argv in (["hub"], ["hub", "a", "b"]):
            code, out, err = run_cli(*argv)
            self.assertEqual((code, out), (2, ""))
            self.assertIn("course.py hub <dir>", err)
        os.remove(os.path.join(self.dir, "course.json"))
        code, out, err = run_cli("hub", self.dir)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("course.json", err)

    def test_hub_runs_as_a_script(self):
        proc = subprocess.run([sys.executable, "-B", str(COURSE_PY), "hub", self.dir],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Short answer.", Path(self.dir, "index.html").read_text(encoding="utf-8"))


class HubVerifyTest(HubCase):
    """Chrome: verify.sh on a generated hub."""

    def setUp(self):
        super().setUp()
        self.tmp = os.path.join(self.base, "tmp")
        os.mkdir(self.tmp)
        self.addCleanup(
            lambda: subprocess.run(["pkill", "-KILL", "-f", self.tmp], capture_output=True)
        )

    def verify(self):
        self.assertEqual(run_cli("hub", self.dir)[0], 0)
        env = dict(os.environ, TMPDIR=self.tmp + "/")
        env.pop("VERIFY_TIMEOUT", None)
        return subprocess.run([str(VERIFY), os.path.join(self.dir, "index.html")],
                              capture_output=True, text=True, env=env, timeout=240)

    def test_fixture_hub_passes_verify(self):
        proc = self.verify()
        self.assertEqual(proc.stdout.splitlines(), [
            "self-contained: ok",
            "render 1440x900: ok",
            "render 500x844: ok",
            "citations: ok",
            "prose: ok",
            "media: ok",
            "bpmn: none",
        ], proc.stdout + proc.stderr)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_missing_lesson_link_fails_media(self):
        self.assertEqual(run_cli("hub", self.dir)[0], 0)
        shutil.rmtree(os.path.join(self.dir, "lessons", "entry-receive"))
        env = dict(os.environ, TMPDIR=self.tmp + "/")
        env.pop("VERIFY_TIMEOUT", None)
        proc = subprocess.run([str(VERIFY), os.path.join(self.dir, "index.html")],
                              capture_output=True, text=True, env=env, timeout=240)
        lines = proc.stdout.splitlines()
        self.assertIn("media: FAIL 1 missing", lines, proc.stdout)
        media = lines.index("media: FAIL 1 missing")
        self.assertRegex(lines[media + 1], r"^  a href=lessons/entry-receive/index\.html$")
        self.assertEqual(lines[media + 2], "bpmn: none")
        self.assertEqual(proc.returncode, 1)


if __name__ == "__main__":
    unittest.main()
