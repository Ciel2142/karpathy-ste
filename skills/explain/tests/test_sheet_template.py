"""Tests for templates/sheet.html (spec section 6) and its guard script.

The template is also a demo of itself: verify.sh must pass it as it stands. The
broken-state fixtures are copies of the template with one edit each; verify.sh
must report the one status that the guard writes for that edit. One Chrome dump
per fixture (six in total). Each run gets a private TMPDIR, so every Chrome
process carries that path and the cleanup can kill a stray one.
"""

import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
VERIFY = os.path.join(SKILL, "scripts", "verify.sh")
TEMPLATE = os.path.join(SKILL, "templates", "sheet.html")
FIXTURES = os.path.join(HERE, "fixtures")
BROKEN = ("sheet-overflow.html", "sheet-smalltext.html", "sheet-canvas.html",
          "sheet-jserror.html", "sheet-provenance.html")
OK_LINES = ["self-contained: ok", "citations: ok", "prose: ok"]


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class SheetFixturesFollowTheTemplate(unittest.TestCase):
    """No Chrome: the fixtures must not drift from the template they test."""

    def test_good_fixture_is_a_byte_copy_of_the_template(self):
        self.assertEqual(read(os.path.join(FIXTURES, "sheet-good.html")), read(TEMPLATE))

    def test_broken_fixtures_carry_the_template_style_and_guard_verbatim(self):
        template = read(TEMPLATE)
        blocks = re.findall(r"<script>.*?</script>|<style>.*?</style>", template, re.S)
        self.assertEqual(len(blocks), 3, "expected 1 style and 2 script blocks")
        for name in BROKEN:
            text = read(os.path.join(FIXTURES, name))
            for block in blocks:
                self.assertIn(block, text, "%s: block differs from the template" % name)


class SheetGuardTest(unittest.TestCase):

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.tmp = os.path.realpath(self._dir.name)
        self.addCleanup(self._dir.cleanup)
        self.addCleanup(
            lambda: subprocess.run(["pkill", "-KILL", "-f", self.tmp], capture_output=True)
        )

    def verify(self, name):
        env = dict(os.environ, TMPDIR=self.tmp + "/")
        env.pop("VERIFY_TIMEOUT", None)
        return subprocess.run(
            [VERIFY, os.path.join(FIXTURES, name)], capture_output=True, text=True,
            env=env, timeout=180,
        )

    def assert_render_fails(self, name, status):
        proc = self.verify(name)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        lines = proc.stdout.splitlines()
        self.assertEqual(lines[1], 'render 1920x1080: FAIL data-verify="%s"' % status,
                         proc.stdout)
        self.assertEqual([lines[0]] + lines[2:], OK_LINES, proc.stdout)

    def test_good_fixture_passes_all_four_checks(self):
        proc = self.verify("sheet-good.html")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.splitlines(),
                         ["self-contained: ok", "render 1920x1080: ok"] + OK_LINES[1:])

    def test_stuffed_panel_c_reports_overflow_c(self):
        self.assert_render_fails("sheet-overflow.html", "OVERFLOW:C")

    def test_11px_text_reports_smalltext_11(self):
        self.assert_render_fails("sheet-smalltext.html", "SMALLTEXT:11")

    def test_block_taller_than_the_canvas_reports_canvas(self):
        self.assert_render_fails("sheet-canvas.html", "CANVAS")

    def test_throwing_inline_script_reports_jserror(self):
        self.assert_render_fails("sheet-jserror.html", "JSERROR")

    def test_long_subject_and_full_hash_report_overflow_title_and_lint_clean(self):
        # Title-block values wrap instead of truncating, so a 128-character path and a
        # 40-character hash run out of room visibly; the paths are not linted as prose.
        self.assert_render_fails("sheet-provenance.html", "OVERFLOW:title")


if __name__ == "__main__":
    unittest.main()
