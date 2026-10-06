"""Subprocess tests for scripts/verify.sh (spec section 5.5).

Every fixture is copied to <temp>/index.html with "@ROOT@" replaced by the temp
directory (data-root must be absolute; the committed fixtures hold no machine
path), next to the source.txt that the fixture cites. The script runs with
TMPDIR pointed at a private directory, so the Chrome profile lives there: every
Chrome process carries that path on its command line, which lets a test prove
that no Chrome survives the run and that the temp profile is removed.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from bpmn_page import bpmn_page  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "verify.sh")
BPMN_PY = os.path.join(os.path.dirname(HERE), "scripts", "bpmn.py")
FIXTURES = os.path.join(HERE, "fixtures")
HANG = os.path.join(FIXTURES, "snap-hang.html")
SOURCE = "The parser reads each tag and keeps the attributes.\n"
CHECKS = ("self-contained:", "render 1920x1080:", "citations:", "prose:", "bpmn:")
BPMN_NONE = "bpmn: none\n"
GOOD_OUT = (
    "self-contained: ok\n"
    "render 1920x1080: ok\n"
    "citations: ok\n"
    "prose: ok\n"
    + BPMN_NONE
)
# The first five lines of a page or a lesson that passes. A page adds the bpmn line after them;
# a lesson adds `media: ok` and then the bpmn line.
LESSON_PASS = (
    "self-contained: ok\n"
    "render 1440x900: ok\n"
    "render 500x844: ok\n"
    "citations: ok\n"
    "prose: ok\n"
)
CLIP_FIGURE = re.compile(r'<figure class="clip">.*?</figure>\n', re.DOTALL)
TRANSCRIPT = os.path.join(os.path.dirname(HERE), "video", "transcript.py")
META_SHEET = '<meta name="explain-rung" content="sheet">'


def fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as handle:
        return handle.read()


def replace_once(case, text, anchor, replacement):
    """Replace an anchor that must occur exactly once in text."""
    case.assertEqual(text.count(anchor), 1, "anchor %r" % anchor)
    return text.replace(anchor, replacement)


class VerifyTest(unittest.TestCase):

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._dir.name)
        self.tmp = os.path.join(self.root, "tmp")
        self.work = os.path.join(self.root, "work")
        os.mkdir(self.tmp)
        os.mkdir(self.work)
        with open(os.path.join(self.work, "source.txt"), "w", encoding="utf-8") as handle:
            handle.write(SOURCE)
        self.addCleanup(self._dir.cleanup)
        self.addCleanup(self._kill_strays)

    def _kill_strays(self):
        subprocess.run(["pkill", "-KILL", "-f", self.tmp], capture_output=True)

    def write_index(self, html):
        path = os.path.join(self.work, "index.html")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(html.replace("@ROOT@", self.work))
        return path

    def run_verify(self, *args, timeout=None):
        env = dict(os.environ, TMPDIR=self.tmp + "/")
        env.pop("VERIFY_TIMEOUT", None)
        if timeout is not None:
            env["VERIFY_TIMEOUT"] = str(timeout)
        started = time.monotonic()
        proc = subprocess.run(
            [SCRIPT] + list(args), capture_output=True, text=True, env=env,
            timeout=180,
        )
        return proc, time.monotonic() - started

    def verify_fixture(self, name, timeout=None, edit=None):
        html = fixture(name)
        if edit is not None:
            html = edit(html)
        return self.run_verify(self.write_index(html), timeout=timeout)

    def assert_no_chrome_left(self):
        found = subprocess.run(
            ["pgrep", "-f", self.tmp], capture_output=True, text=True,
        ).stdout.split()
        if found:
            listing = subprocess.run(
                ["ps", "-o", "pid,ppid,pgid,etime,command", "-p", ",".join(found)],
                capture_output=True, text=True,
            ).stdout
            self.fail("processes left matching %s:\n%s" % (self.tmp, listing))
        self.assertEqual(os.listdir(self.tmp), [], "temp profile not removed")

    def check_lines(self, out):
        """The non-indented lines, i.e. one per check."""
        return [line for line in out.splitlines() if not line.startswith(" ")]

    def write_clip(self, *names):
        """Create clips/intro/<name> under the work directory, one byte each."""
        folder = os.path.join(self.work, "clips", "intro")
        os.makedirs(folder, exist_ok=True)
        for name in names:
            with open(os.path.join(folder, name), "wb") as handle:
                handle.write(b"x")

    # --- the all-good fixture ------------------------------------------------

    def test_good_fixture_passes_all_five_checks(self):
        proc, _ = self.verify_fixture("verify-good.html")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, GOOD_OUT)
        self.assert_no_chrome_left()

    # --- check 1: self-containment ---------------------------------------------

    def test_remote_script_and_stylesheet_fail_check_1_and_all_five_lines_print(self):
        # The .invalid host fails DNS at once and "load" still fires: no network use.
        proc, _ = self.verify_fixture("verify-remote.html", timeout=20)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("self-contained: FAIL 2 remote reference(s)\n", proc.stdout)
        self.assertIn("  script src=https://example.invalid/x.js\n", proc.stdout)
        self.assertIn("  link href=https://example.invalid/x.css\n", proc.stdout)
        lines = self.check_lines(proc.stdout)
        self.assertEqual(len(lines), 5, proc.stdout)
        for line, prefix in zip(lines, CHECKS):
            self.assertTrue(line.startswith(prefix), (line, prefix))
        self.assertEqual(lines[2:], ["citations: ok", "prose: ok", "bpmn: none"])
        self.assert_no_chrome_left()

    def test_escaped_code_samples_do_not_trip_self_containment(self):
        proc, _ = self.verify_fixture("verify-escaped.html")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("self-contained: ok\n", proc.stdout)
        self.assertEqual(proc.stdout, GOOD_OUT)
        self.assert_no_chrome_left()

    def test_every_self_containment_rule(self):
        remote = (
            '<img src="//cdn.example.invalid/a.png" alt="">\n'
            '<img srcset="local.png 1x, https://cdn.example.invalid/b.png 2x" alt="">\n'
            '<video poster="http://cdn.example.invalid/c.png"></video>\n'
            '<link rel="icon" href="HTTPS://cdn.example.invalid/d.ico">\n'
            '<div style="background-image: url( \'//cdn.example.invalid/e.png\' )"></div>\n'
            '<style>@import "https://cdn.example.invalid/f.css";\n'
            '@import url(https://cdn.example.invalid/g.css);\n'
            'p { background: url("http://cdn.example.invalid/h.png"); }</style>\n'
        )
        local = (
            '<a href="https://example.com/">a link may point anywhere</a>\n'
            '<img src="data:image/png;base64,AAAA" alt="">\n'
            '<img src="local.png" srcset="local.png 1x, big.png 2x" alt="">\n'
            '<div style="background: url(data:image/png;base64,AAAA)"></div>\n'
            '<style>@import "local.css"; p { background: url(img/x.png); }</style>\n'
        )
        proc, _ = self.verify_fixture(
            "verify-good.html", timeout=20,
            edit=lambda html: html.replace("</section>", remote + local + "</section>"),
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("self-contained: FAIL 8 remote reference(s)\n", proc.stdout)
        details = [line for line in proc.stdout.splitlines() if line.startswith("  ")]
        self.assertEqual(len(details), 8, proc.stdout)
        for marker in "abcdefgh":
            self.assertTrue(
                any("cdn.example.invalid/%s." % marker in line for line in details),
                (marker, details),
            )
        for passing in ("example.com/", "data:", "big.png", "local.css", "img/x.png"):
            self.assertFalse(any(passing in line for line in details), (passing, details))
        self.assert_no_chrome_left()

    # --- check 2: render status ------------------------------------------------

    def test_overflow_guard_value_is_shown(self):
        proc, _ = self.verify_fixture("verify-overflow.html")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn('render 1920x1080: FAIL data-verify="OVERFLOW:C"\n', proc.stdout)
        self.assertEqual(
            self.check_lines(proc.stdout),
            ["self-contained: ok", 'render 1920x1080: FAIL data-verify="OVERFLOW:C"',
             "citations: ok", "prose: ok", "bpmn: none"],
        )
        self.assert_no_chrome_left()

    def test_missing_data_verify_attribute_is_its_own_failure(self):
        proc, _ = self.verify_fixture("verify-noattr.html")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("render 1920x1080: FAIL no data-verify attribute\n", proc.stdout)
        self.assert_no_chrome_left()

    def test_page_rung_dumps_two_viewports(self):
        # The guard sets data-verify="pending" before lang at parse time (the source
        # tag stays attribute-free) and rewrites it in place on load: attribute order
        # in the dump must not matter.
        pending = (
            "<script>\n"
            "var h = document.documentElement, lang = h.getAttribute(\"lang\");\n"
            "h.removeAttribute(\"lang\");\n"
            "h.setAttribute(\"data-verify\", \"pending\");\n"
            "h.setAttribute(\"lang\", lang);\n"
        )
        proc, _ = self.verify_fixture(
            "verify-good.html",
            edit=lambda html: replace_once(
                self, replace_once(self, html, 'content="sheet"', 'content="page"'),
                "<script>\n", pending),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(
            proc.stdout,
            "self-contained: ok\nrender 1440x900: ok\nrender 500x844: ok\n"
            "citations: ok\nprose: ok\nbpmn: none\n",
        )
        self.assert_no_chrome_left()

    def test_data_verify_preset_in_the_source_fails_without_a_dump(self):
        # A static data-verify="OK" on the source <html> would pass check 2 with no
        # guard at all; any value in the source is refused before Chrome starts.
        def edit(html):
            html = replace_once(self, html, '<html lang="en">',
                                '<html lang="en" data-verify="OK">')
            start, end = html.index("<script>"), html.index("</script>") + len("</script>")
            return html[:start] + html[end:]
        proc, _ = self.verify_fixture("verify-good.html", edit=edit)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(
            self.check_lines(proc.stdout),
            ["self-contained: ok", "render 1920x1080: FAIL data-verify preset in source",
             "citations: ok", "prose: ok", "bpmn: none"],
        )
        self.assert_no_chrome_left()

    def test_timeout_on_a_page_that_never_loads_kills_chrome(self):
        html = fixture("snap-hang.html").replace("<head>", "<head>\n" + META_SHEET, 1)
        self.assertIn(META_SHEET, html)
        proc, elapsed = self.run_verify(self.write_index(html), timeout=1)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("render 1920x1080: FAIL timeout\n", proc.stdout)
        self.assertEqual(len(self.check_lines(proc.stdout)), 5, proc.stdout)
        self.assertLess(elapsed, 8)
        self.assert_no_chrome_left()

    # --- check 3: citations ----------------------------------------------------

    def test_dangling_cite_fails_citations(self):
        proc, _ = self.verify_fixture("verify-dangling.html")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("citations: FAIL 1 failure(s)\n", proc.stdout)
        self.assertRegex(proc.stdout, r"\n  cite 1 \(source\.txt:9999\): line out of range")
        self.assertNotIn("cite_check: 1 failures", proc.stdout)
        self.assert_no_chrome_left()

    # --- check 4: prose ----------------------------------------------------------

    def test_26_word_sentence_fails_prose(self):
        proc, _ = self.verify_fixture("verify-long.html")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("prose: FAIL 1 error(s)\n", proc.stdout)
        self.assertRegex(proc.stdout, r"\n  \d+:\d+  E LENGTH  sentence has 26 words")
        self.assertTrue(proc.stdout.endswith("(max 25)\n" + BPMN_NONE), proc.stdout)
        self.assert_no_chrome_left()

    def test_lint_usage_error_is_reported_apart_from_lint_errors(self):
        # ste_lint.py exits 2 on a file that is not UTF-8; verify.sh reads it leniently.
        path = self.write_index(fixture("verify-good.html"))
        with open(path, "rb") as handle:
            data = handle.read()
        with open(path, "wb") as handle:
            handle.write(data.replace(b"</body>", b"<!-- caf\xe9 -->\n</body>"))
        proc, _ = self.run_verify(path)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("prose: FAIL lint usage error (exit 2)\n", proc.stdout)
        self.assertIn("  %s: 'utf-8' codec can't decode" % path, proc.stdout)
        self.assertEqual(self.check_lines(proc.stdout)[:3],
                         ["self-contained: ok", "render 1920x1080: ok", "citations: ok"])
        self.assert_no_chrome_left()

    # --- video rung ----------------------------------------------------------------

    def video_transcript(self):
        """Generate a transcript of a one-scene script that cites source.txt; return its path."""
        script = {
            "title": "How the parser works",
            "subject": {"text": "source.txt", "kind": "file"},
            "provenance": {
                "root": self.work, "commit": "none", "dirty": "no", "date": "2026-10-03",
                "source": "source.txt", "not_covered": "Everything else.",
            },
            "scenes": [{
                "id": "intro", "component": "title",
                "props": {"title": "The parser", "subtitle": "Read each tag", "cue": "The parser"},
                "narration": "The parser reads each tag. It keeps the attributes.",
                "cites": [{"path": "source.txt", "line": 1, "snippet": "The parser reads each tag"}],
            }],
        }
        path = os.path.join(self.root, "script.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(script, handle)
        subprocess.run([sys.executable, "-B", TRANSCRIPT, path, self.work], check=True)
        return os.path.join(self.work, "index.html")

    def test_verify_video_rung_prints_three_lines(self):
        """Red on the old script: exit 2, unknown rung "video". Red when check 2 still runs:
        a render line appears. Red when a check is skipped: a line is missing."""
        proc, _ = self.run_verify(self.video_transcript())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, "self-contained: ok\ncitations: ok\nprose: ok\n")
        self.assertEqual(os.listdir(self.tmp), [], "Chrome must not start")

    def test_verify_video_remote_video_src_fails(self):
        """Red when the scanner ignores src on a video element: self-contained stays ok."""
        index = self.video_transcript()
        with open(index, encoding="utf-8") as handle:
            html = handle.read()
        html = replace_once(self, html, 'src="video.mp4"', 'src="https://example.com/v.mp4"')
        with open(index, "w", encoding="utf-8") as handle:
            handle.write(html)
        proc, _ = self.run_verify(index)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(
            proc.stdout.split("\n")[:3],
            ["self-contained: FAIL 1 remote reference(s)",
             "  video src=https://example.com/v.mp4",
             "citations: ok"],
        )
        self.assertEqual(proc.stdout.split("\n")[3], "prose: ok")

    # --- lesson rung ---------------------------------------------------------------

    def test_lesson_rung_renders_the_page_viewports(self):
        """Red on the old script: exit 2, unknown rung "lesson". Red when the lesson rung
        gets the sheet viewport: render 1920x1080 replaces the two page lines."""
        proc, _ = self.verify_fixture(
            "verify-good.html",
            edit=lambda html: replace_once(self, html, 'content="sheet"', 'content="lesson"'),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        lines = proc.stdout.splitlines()
        self.assertIn("render 1440x900: ok", lines)
        self.assertIn("render 500x844: ok", lines)
        self.assertNotIn("render 1920x1080: ok", lines)
        self.assert_no_chrome_left()

    # --- lesson rung: the media check (spec 6.3) ---------------------------------------

    def test_lesson_with_media_prints_seven_ok_lines(self):
        """Red on the old script: five lines, no `media: ok`. Red when a check is skipped
        or its line moves: the seven lines compare in order."""
        self.write_clip("video.mp4", "poster.png", "index.html")
        proc, _ = self.verify_fixture("verify-lesson.html")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, LESSON_PASS + "media: ok\n" + BPMN_NONE)
        self.assert_no_chrome_left()

    def test_lesson_missing_poster_fails_media_with_a_detail_line(self):
        """Red when poster is not collected (media: ok). Red when the scanner's
        media-missing line leaks into check 1 (self-contained: FAIL). Red when the exit
        code ignores the media FAIL (exit 0)."""
        self.write_clip("video.mp4", "index.html")
        proc, _ = self.verify_fixture("verify-lesson.html")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(
            proc.stdout,
            LESSON_PASS
            + "media: FAIL 1 missing\n  video poster=clips/intro/poster.png\n" + BPMN_NONE,
        )
        self.assert_no_chrome_left()

    def test_lesson_media_counts_references_not_unique_paths(self):
        """Red when the count is of unique paths (`FAIL 1 missing`). Red when src, poster
        or the a href is not collected: the count falls below three, and the detail lines
        keep the order of the document."""
        proc, _ = self.verify_fixture(
            "verify-lesson.html",
            edit=lambda html: replace_once(
                self,
                replace_once(self, html, 'href="clips/intro/index.html"',
                             'href="clips/intro/video.mp4"'),
                'poster="clips/intro/poster.png"', 'poster="clips/intro/video.mp4"'),
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(
            proc.stdout,
            LESSON_PASS + "media: FAIL 3 missing\n"
            "  video src=clips/intro/video.mp4\n"
            "  video poster=clips/intro/video.mp4\n"
            "  a href=clips/intro/video.mp4\n" + BPMN_NONE,
        )
        self.assert_no_chrome_left()

    def test_lesson_media_strips_fragment_query_and_decodes(self):
        """Red when the fragment is not cut (index.html#scene-1?x=1 is no file). Red when
        the percent code is not decoded (poster%20a.png is no file)."""
        self.write_clip("video.mp4", "index.html", "poster a.png")
        proc, _ = self.verify_fixture(
            "verify-lesson.html",
            edit=lambda html: replace_once(
                self,
                replace_once(self, html, 'href="clips/intro/index.html"',
                             'href="clips/intro/index.html#scene-1?x=1"'),
                'poster="clips/intro/poster.png"', 'poster="clips/intro/poster%20a.png"'),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, LESSON_PASS + "media: ok\n" + BPMN_NONE)
        self.assert_no_chrome_left()

    def test_lesson_media_strips_a_query_without_a_fragment(self):
        """Red when only a fragment is cut: index.html?v=2 is no file."""
        self.write_clip("video.mp4", "index.html", "poster.png")
        proc, _ = self.verify_fixture(
            "verify-lesson.html",
            edit=lambda html: replace_once(
                self, html, 'href="clips/intro/index.html"',
                'href="clips/intro/index.html?v=2"'),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, LESSON_PASS + "media: ok\n" + BPMN_NONE)
        self.assert_no_chrome_left()

    def test_lesson_media_strips_dot_slash_and_rejects_a_directory(self):
        """Red when the leading ./ is not stripped before the clips/ test (the href is
        never collected: media: ok). Red when os.path.exists replaces os.path.isfile (the
        directory counts as present: media: ok)."""
        self.write_clip("video.mp4", "index.html", "poster.png")
        proc, _ = self.verify_fixture(
            "verify-lesson.html",
            edit=lambda html: replace_once(
                self, html, 'href="clips/intro/index.html"', 'href="./clips/intro/"'),
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(
            proc.stdout,
            LESSON_PASS + "media: FAIL 1 missing\n  a href=./clips/intro/\n" + BPMN_NONE)
        self.assert_no_chrome_left()

    def test_lesson_media_outside_the_directory_counts_as_missing(self):
        """Spec 3.4: the only external references are relative paths inside the output
        directory. Both files exist. Red when a path that escapes the directory after
        normalization counts as present (the src goes up through clips/../../). Red when
        an absolute path counts as present (the poster names its file by the full path)."""
        self.write_clip("video.mp4", "poster.png", "index.html")
        with open(os.path.join(self.root, "outside.mp4"), "wb") as handle:
            handle.write(b"x")
        poster = os.path.join(self.work, "clips", "intro", "poster.png")
        proc, _ = self.verify_fixture(
            "verify-lesson.html",
            edit=lambda html: replace_once(
                self,
                replace_once(self, html, 'src="clips/intro/video.mp4"',
                             'src="clips/../../outside.mp4"'),
                'poster="clips/intro/poster.png"', 'poster="%s"' % poster),
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(
            proc.stdout,
            LESSON_PASS + "media: FAIL 2 missing\n"
            "  video src=clips/../../outside.mp4\n"
            "  video poster=%s\n" % poster + BPMN_NONE,
        )
        self.assert_no_chrome_left()

    def test_lesson_media_ignores_links_outside_clips(self):
        """Red when every a href is collected, not only clips/: each of these three
        links resolves to no file beside index.html."""
        self.write_clip("video.mp4", "index.html", "poster.png")
        links = ('<p><a href="notes/absent.html">notes</a> <a href="#top">top</a> '
                 '<a href="mailto:a@example.test">mail</a></p>\n')
        proc, _ = self.verify_fixture(
            "verify-lesson.html",
            edit=lambda html: replace_once(self, html, "</section>", links + "</section>"),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, LESSON_PASS + "media: ok\n" + BPMN_NONE)
        self.assert_no_chrome_left()

    def test_lesson_without_clips_passes_media(self):
        """Red when the media check demands a clip: a page with no figure.clip must
        print `media: ok`, not FAIL."""
        def edit(html):
            stripped = CLIP_FIGURE.sub("", html, count=1)
            self.assertNotIn("<figure", stripped)
            self.assertNotIn("<video", stripped)
            return stripped
        proc, _ = self.verify_fixture("verify-lesson.html", edit=edit)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, LESSON_PASS + "media: ok\n" + BPMN_NONE)
        self.assert_no_chrome_left()

    def test_lesson_remote_video_src_counts_once(self):
        """Red when the media check also counts a remote value as missing: check 1 and
        check 5 would both fail the same reference (`media: FAIL 1 missing`)."""
        self.write_clip("video.mp4", "poster.png", "index.html")
        proc, _ = self.verify_fixture(
            "verify-lesson.html", timeout=20,
            edit=lambda html: replace_once(
                self, html, 'src="clips/intro/video.mp4"', 'src="https://x.test/v.mp4"'),
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(
            proc.stdout,
            LESSON_PASS.replace(
                "self-contained: ok\n",
                "self-contained: FAIL 1 remote reference(s)\n  video src=https://x.test/v.mp4\n")
            + "media: ok\n" + BPMN_NONE,
        )
        self.assert_no_chrome_left()

    def test_page_rung_prints_no_media_line(self):
        """Red when the media line prints for every rung."""
        proc, _ = self.verify_fixture(
            "verify-good.html",
            edit=lambda html: replace_once(self, html, 'content="sheet"', 'content="page"'),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, LESSON_PASS + BPMN_NONE)
        self.assertNotIn("media", proc.stdout)
        self.assert_no_chrome_left()

    def test_page_rung_ignores_missing_clip_files(self):
        """Red when a missing local video file fails a page: the page rung has no media
        check, and its scanner lines must stay out of check 1 and the exit code."""
        proc, _ = self.verify_fixture(
            "verify-lesson.html",
            edit=lambda html: replace_once(self, html, 'content="lesson"', 'content="page"'),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, LESSON_PASS + BPMN_NONE)
        self.assert_no_chrome_left()

    # --- the bpmn line (the BPMN coverage check, last) ---------------------------------

    def test_page_without_bpmn_prints_bpmn_none_last(self):
        """Red when the line is missing, or prints `ok` for a page with no diagram (the
        summary `bpmn: none` is not passed on), or sits before prose."""
        proc, _ = self.verify_fixture(
            "verify-good.html",
            edit=lambda html: replace_once(self, html, 'content="sheet"', 'content="page"'),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.splitlines()[-1], "bpmn: none")
        self.assertEqual(proc.stdout, LESSON_PASS + BPMN_NONE)
        self.assert_no_chrome_left()

    def test_bpmn_fixture_page_prints_bpmn_ok(self):
        """Red when the line is `none` for a page with a diagram, or when the check never
        reads the page (the exit code or the summary is dropped)."""
        page = bpmn_page(os.path.join(self.root, "bpmn"))
        proc, _ = self.run_verify(str(page))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, LESSON_PASS + "bpmn: ok\n")
        self.assert_no_chrome_left()

    def test_bpmn_failure_prints_count_and_details(self):
        """Red when the exit 1 of the check does not fail the run, when the count is not
        taken from the detail lines, or when the details are not indented by two spaces."""
        section = fixture("bpmn-section.html")
        figure = re.compile(r'<figure class="bpmn">(?:(?!</figure>).)*data-plane="STAGE_A".*?</figure>\n',
                            re.DOTALL)
        edited = figure.sub("", section, count=1)
        self.assertNotEqual(edited, section)
        page = bpmn_page(os.path.join(self.root, "bpmn"), edited)
        proc, _ = self.run_verify(str(page))
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(
            proc.stdout,
            LESSON_PASS + "bpmn: FAIL 1 failure(s)\n"
            "  page | plane | STAGE_A (Первичная проверка) has no svg.bpmn"
            " and is not in Not covered\n",
        )
        self.assert_no_chrome_left()

    def test_sheet_with_one_bpmn_cite_prints_bpmn_ok(self):
        """Red when verify.sh does not pass --rung sheet: a sheet with one labelled BPMN cite then fails
        conditions 1 and 2. The same page as a page rung must still fail condition 1."""
        shutil.copy(os.path.join(FIXTURES, "two_planes.bpmn"), os.path.join(self.work, "two_planes.bpmn"))
        cite = ('  <cite data-path="two_planes.bpmn" data-line="18" data-snippet="Проверить паспорт клиента">'
                'two_planes.bpmn:18 <code>Проверить паспорт клиента</code></cite>\n</div>')
        path = self.write_index(replace_once(self, fixture("verify-good.html"), "</div>", cite))
        label = subprocess.run([sys.executable, "-B", BPMN_PY, "label", path], capture_output=True, text=True)
        self.assertEqual((label.returncode, label.stdout), (0, ""), label.stderr)
        proc, _ = self.run_verify(path)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, GOOD_OUT.replace(BPMN_NONE, "bpmn: ok\n"))
        with open(path, encoding="utf-8") as handle:
            self.write_index(replace_once(self, handle.read(), 'content="sheet"', 'content="page"'))
        proc, _ = self.run_verify(path)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(self.check_lines(proc.stdout)[-1], "bpmn: FAIL 4 failure(s)")
        self.assertIn("  page | plane | Collaboration_1 (Collaboration_1) has no svg.bpmn", proc.stdout)
        self.assert_no_chrome_left()

    def test_lesson_prints_bpmn_after_media(self):
        """Red when the bpmn line comes before media, or a lesson prints no bpmn line."""
        self.write_clip("video.mp4", "poster.png", "index.html")
        proc, _ = self.verify_fixture("verify-lesson.html")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.splitlines()[-2:], ["media: ok", "bpmn: none"])
        self.assert_no_chrome_left()

    def test_video_prints_no_bpmn_line(self):
        """Red when the bpmn line prints for every rung: the transcript keeps three lines."""
        proc, _ = self.run_verify(self.video_transcript())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, "self-contained: ok\ncitations: ok\nprose: ok\n")
        self.assertNotIn("bpmn", proc.stdout)

    # --- usage -------------------------------------------------------------------

    def test_missing_meta_is_a_usage_error(self):
        proc, _ = self.verify_fixture("verify-nometa.html")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertIn("explain-rung", proc.stderr)
        self.assertEqual(os.listdir(self.tmp), [], "Chrome must not start")

    def test_unknown_rung_is_a_usage_error(self):
        proc, _ = self.verify_fixture(
            "verify-good.html",
            edit=lambda html: html.replace('content="sheet"', 'content="poster"'),
        )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertIn("poster", proc.stderr)
        self.assertIn("(expected sheet, page, video or lesson)", proc.stderr)
        self.assertEqual(os.listdir(self.tmp), [], "Chrome must not start")

    def test_unknown_rung_message_lists_lesson(self):
        """Red on the old text: the usage line names three rungs and omits lesson."""
        proc, _ = self.verify_fixture(
            "verify-good.html",
            edit=lambda html: replace_once(self, html, 'content="sheet"', 'content="poster"'),
        )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertIn("(expected sheet, page, video or lesson)", proc.stderr)
        self.assertEqual(os.listdir(self.tmp), [], "Chrome must not start")

    def test_no_argument_or_unreadable_file_is_a_usage_error(self):
        for args in ([], [os.path.join(self.work, "absent.html")], [self.work]):
            proc, _ = self.run_verify(*args)
            self.assertEqual(proc.returncode, 2, (args, proc.stdout, proc.stderr))
            self.assertEqual(proc.stdout, "", args)
            self.assertTrue(re.search(r"verify\.sh", proc.stderr), (args, proc.stderr))
        proc, _ = self.run_verify(self.write_index(fixture("verify-good.html")), "extra")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        proc, _ = self.run_verify(self.write_index(fixture("verify-good.html")), timeout="soon")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("VERIFY_TIMEOUT", proc.stderr)


if __name__ == "__main__":
    unittest.main()
