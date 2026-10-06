"""Tests for templates/sheet.html (spec section 6) and its guard script.

The template is also a demo of itself: verify.sh must pass it as it stands. Each
broken state is derived from the template at test time by one string edit, so a
change to the template reaches every case. Each edit asserts that its anchor occurs
exactly once in the template: a template change cannot turn a case into the good
case without notice. verify.sh must report the one status that the guard writes
for that edit. One Chrome dump per case (six in total). Each run gets a private
TMPDIR, so every Chrome process carries that path and the cleanup can kill a stray
one.
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
OK_LINES = ["self-contained: ok", "citations: ok", "prose: ok"]

# After the closing tag of .sheet, before guard part 2.
AFTER_SHEET = "</div>\n</div>\n<script>\n/* Guard, part 2 of 2"
ROW = ('<tr><td>Inline CSS</td><td><code>&lt;style&gt;</code></td>'
       '<td class="yes">&#10003; Allowed</td></tr>\n')
# 128 characters, a path with no spaces: it can wrap only through overflow-wrap.
LONG_SUBJECT = ("/home/reader/projects/a-very-long-directory-name-for-testing/"
                "another-level/yet-another-level/deepest-level/sheet-provenance.html")
FULL_HASH = "1252c71bc8eea8587ab43cb0e3f6a1d2b4c5e6f7"


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class SheetGuardTest(unittest.TestCase):

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        root = os.path.realpath(self._dir.name)
        self.tmp = os.path.join(root, "tmp")
        self.work = os.path.join(root, "work")
        os.mkdir(self.tmp)
        os.mkdir(self.work)
        self.template = read(TEMPLATE)
        self.addCleanup(self._dir.cleanup)
        self.addCleanup(
            lambda: subprocess.run(["pkill", "-KILL", "-f", self.tmp], capture_output=True)
        )

    def edit(self, html, anchor, replacement):
        self.assertEqual(html.count(anchor), 1, "anchor %r must occur once" % anchor)
        return html.replace(anchor, replacement)

    def verify(self, path):
        env = dict(os.environ, TMPDIR=self.tmp + "/")
        env.pop("VERIFY_TIMEOUT", None)
        return subprocess.run(
            [VERIFY, path], capture_output=True, text=True, env=env, timeout=180,
        )

    def assert_render_fails(self, html, status):
        path = os.path.join(self.work, "index.html")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(html)
        proc = self.verify(path)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        lines = proc.stdout.splitlines()
        self.assertEqual(lines[1], 'render 1920x1080: FAIL data-verify="%s"' % status,
                         proc.stdout)
        self.assertEqual([lines[0]] + lines[2:], OK_LINES, proc.stdout)

    def test_template_passes_all_four_checks(self):
        proc = self.verify(TEMPLATE)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.splitlines(),
                         ["self-contained: ok", "render 1920x1080: ok"] + OK_LINES[1:])

    def test_stuffed_panel_c_reports_overflow_c(self):
        html = self.edit(self.template, "<tbody>\n", "<tbody>\n" + ROW * 24)
        self.assert_render_fails(html, "OVERFLOW:C")

    def test_11px_text_reports_smalltext_11(self):
        anchor = '<p class="note"><code>verify.sh</code> stops the handoff'
        html = self.edit(self.template, anchor,
                         anchor.replace('class="note"', 'class="note" style="font-size: 11px"'))
        self.assert_render_fails(html, "SMALLTEXT:11")

    def test_block_taller_than_the_canvas_reports_canvas(self):
        html = self.edit(self.template, AFTER_SHEET, AFTER_SHEET.replace(
            "</div>\n<script>", '</div>\n<div style="height: 1200px"></div>\n<script>'))
        self.assert_render_fails(html, "CANVAS")

    def test_cites_collect_in_a_block_under_the_prose(self):
        """Red: a template lacks the .cites rules, shows a cite inline in the prose, or quotes the
        snippet instead of setting it in <code>."""
        for rule in (".cites {", ".cites cite {", ".cites cite + cite {", ".cites code {"):
            self.assertIn(rule, self.template, rule)
        markup = re.sub(r"<!--.*?-->", "", self.template, flags=re.S)
        cites = re.findall(r"<cite\b[^>]*>(.*?)</cite>", markup, re.S)
        self.assertTrue(cites)
        for text in cites:
            self.assertRegex(text, r"^[^<\"]+ <code>[^<]+</code>$")
        blocks = re.findall(r'<div class="cites">(.*?)</div>', markup, re.S)
        self.assertEqual(sum(block.count("<cite") for block in blocks), len(cites))

    def test_throwing_inline_script_reports_jserror(self):
        html = self.edit(self.template, AFTER_SHEET, AFTER_SHEET.replace(
            "</div>\n<script>",
            '</div>\n<script>throw new Error("broken case");</script>\n<script>'))
        self.assert_render_fails(html, "JSERROR")

    def test_long_subject_and_full_hash_report_overflow_title_and_lint_clean(self):
        # Title-block values wrap instead of truncating, so a 128-character path and a
        # 40-character hash run out of room visibly; the paths are not linted as prose.
        self.assertEqual((len(LONG_SUBJECT), len(FULL_HASH)), (128, 40))
        html = self.edit(self.template, "<dd>the sheet template (topic)</dd>",
                         "<dd>%s (file)</dd>" % LONG_SUBJECT)
        html = self.edit(html, "<dt>Commit</dt><dd>none</dd>",
                         "<dt>Commit</dt><dd>%s</dd>" % FULL_HASH)
        self.assert_render_fails(html, "OVERFLOW:title")


if __name__ == "__main__":
    unittest.main()
