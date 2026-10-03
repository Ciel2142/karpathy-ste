"""Subprocess tests for scripts/verify.sh (spec section 5.5).

Every fixture is copied to <temp>/index.html with "@ROOT@" replaced by the temp
directory (data-root must be absolute; the committed fixtures hold no machine
path), next to the source.txt that the fixture cites. The script runs with
TMPDIR pointed at a private directory, so the Chrome profile lives there: every
Chrome process carries that path on its command line, which lets a test prove
that no Chrome survives the run and that the temp profile is removed.
"""

import os
import re
import subprocess
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "verify.sh")
FIXTURES = os.path.join(HERE, "fixtures")
HANG = os.path.join(FIXTURES, "snap-hang.html")
SOURCE = "The parser reads each tag and keeps the attributes.\n"
CHECKS = ("self-contained:", "render 1920x1080:", "citations:", "prose:")
GOOD_OUT = (
    "self-contained: ok\n"
    "render 1920x1080: ok\n"
    "citations: ok\n"
    "prose: ok\n"
)
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

    # --- the all-good fixture ------------------------------------------------

    def test_good_fixture_passes_all_four_checks(self):
        proc, _ = self.verify_fixture("verify-good.html")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, GOOD_OUT)
        self.assert_no_chrome_left()

    # --- check 1: self-containment ---------------------------------------------

    def test_remote_script_and_stylesheet_fail_self_containment(self):
        proc, _ = self.verify_fixture("verify-remote.html", timeout=20)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("self-contained: FAIL 2 remote reference(s)\n", proc.stdout)
        self.assertIn("  script src=https://example.com/x.js\n", proc.stdout)
        self.assertIn("  link href=https://example.com/x.css\n", proc.stdout)
        self.assert_no_chrome_left()

    def test_all_four_checks_print_when_the_first_fails(self):
        proc, _ = self.verify_fixture("verify-remote.html", timeout=20)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        lines = self.check_lines(proc.stdout)
        self.assertEqual(len(lines), 4, proc.stdout)
        for line, prefix in zip(lines, CHECKS):
            self.assertTrue(line.startswith(prefix), (line, prefix))
        self.assertTrue(lines[0].startswith("self-contained: FAIL"), lines[0])
        self.assertEqual(lines[2:], ["citations: ok", "prose: ok"])
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
             "citations: ok", "prose: ok"],
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
            "citations: ok\nprose: ok\n",
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
             "citations: ok", "prose: ok"],
        )
        self.assert_no_chrome_left()

    def test_timeout_on_a_page_that_never_loads_kills_chrome(self):
        html = fixture("snap-hang.html").replace("<head>", "<head>\n" + META_SHEET, 1)
        self.assertIn(META_SHEET, html)
        proc, elapsed = self.run_verify(self.write_index(html), timeout=1)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("render 1920x1080: FAIL timeout\n", proc.stdout)
        self.assertEqual(len(self.check_lines(proc.stdout)), 4, proc.stdout)
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
        self.assertTrue(proc.stdout.endswith("(max 25)\n"), proc.stdout)
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
