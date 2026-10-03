"""Tests for templates/page.html (spec section 7) and its guard script.

The template is also a demo of itself: verify.sh must pass it as it stands. Each
broken state is derived from the template at test time by one string edit, so a
change to the template reaches every case. Each edit asserts that its anchor occurs
exactly once in the template: a template change cannot turn a case into the good
case without notice. verify.sh must report the one status that the guard writes
for that edit. verify.sh loads a page twice, 1440x900 and 500x844, both with
#verify in the URL; there is no plain dump, so the cases for the fragment read the
DOM state through a probe that wraps setAttribute on <html>. Six Chrome runs of
verify.sh (two dumps each): the good template, the 700 px block, the 13 px rule,
the throwing script, the probe, the probe with the hash test defeated. The
preset case stops in verify.sh before Chrome starts. The other cases are static.
Each run gets a private TMPDIR, so every Chrome process carries that path and the
cleanup can kill a stray one.
"""

import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
VERIFY = os.path.join(SKILL, "scripts", "verify.sh")
TEMPLATE = os.path.join(SKILL, "templates", "page.html")
SHEET = os.path.join(SKILL, "templates", "sheet.html")
RENDER_OK = ["render 1440x900: ok", "render 500x844: ok"]
OTHER_OK = ["citations: ok", "prose: ok"]

# Guard part 1 closes the first <script>; the throwing script goes right after it.
AFTER_GUARD_1 = "window.onerror = function () { window.explainJsErrors += 1; };\n</script>\n"
# The comment line that introduces guard part 2, with the <script> that holds it.
GUARD_2 = "<script>\n/* Guard, part 2 of 2"
HASH_TEST = '"#verify"'
LOAD_OPEN = 'window.addEventListener("load", function () {\n'
LAST_SCRIPT_END = "</script>\n</body>"
SCRIPT_BUDGET = 200

# Wraps setAttribute on <html>: when the guard writes data-verify, the probe appends
# the DOM state at that moment, then calls the original.
PROBE = """<script>
(function () {
  var doc = document.documentElement, original = doc.setAttribute;
  doc.setAttribute = function (name, value) {
    if (name === "data-verify") {
      var details = document.getElementsByTagName("details"), open = true, i;
      for (i = 0; i < details.length; i++) if (!details[i].open) open = false;
      var steps = document.querySelectorAll(".step"), stacked = true;
      for (i = 0; i < steps.length; i++) if (steps[i].hasAttribute("hidden")) stacked = false;
      var same = document.title === document.querySelector("title").textContent.replace(/\\s+/g, " ").trim();
      value += ";PROBE:" + (open ? "open" : "closed") + ":" + (stacked ? "stacked" : "single") +
        ";TITLE:" + (same ? "same" : "changed");
    }
    return original.call(this, name, value);
  };
})();
</script>
"""


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def root_block(html):
    match = re.search(r":root \{[^}]*\}", html)
    assert match, "no :root block"
    return match.group(0)


def script_lines(html):
    """Lines between <script> and </script> over all blocks (the tag lines excluded)."""
    total = 0
    for body in re.findall(r"<script>(.*?)</script>", html, re.S):
        total += max(len(body.split("\n")) - 2, 0)
    return total


class PageGuardTest(unittest.TestCase):

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
            [VERIFY, path], capture_output=True, text=True, env=env, timeout=240,
        )

    def run_derived(self, html):
        path = os.path.join(self.work, "index.html")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(html)
        return self.verify(path)

    def assert_renders(self, html, renders, code):
        """verify.sh prints self-contained, the two render lines, citations, prose."""
        proc = self.run_derived(html)
        self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.splitlines(),
                         ["self-contained: ok"] + renders + OTHER_OK, proc.stdout)

    def assert_both_fail(self, html, status):
        self.assert_renders(html, [
            'render 1440x900: FAIL data-verify="%s"' % status,
            'render 500x844: FAIL data-verify="%s"' % status,
        ], 1)

    def with_probe(self, html):
        return self.edit(html, GUARD_2, PROBE + GUARD_2)

    def test_template_passes_all_five_checks(self):
        proc = self.verify(TEMPLATE)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.splitlines(),
                         ["self-contained: ok"] + RENDER_OK + OTHER_OK)

    def test_700px_block_reports_hscroll_at_500_only(self):
        html = self.edit(self.template, "<main>\n",
                         '<main>\n<div style="width:700px;height:1px"></div>\n')
        self.assert_renders(html, [
            "render 1440x900: ok",
            'render 500x844: FAIL data-verify="HSCROLL"',
        ], 1)

    def test_13px_rule_reports_smalltext_13(self):
        html = self.edit(self.template, "</style>",
                         "p.lead { font-size: 13px; }\n</style>")
        self.assert_both_fail(html, "SMALLTEXT:13")

    def test_throwing_inline_script_reports_jserror(self):
        html = self.edit(self.template, AFTER_GUARD_1,
                         AFTER_GUARD_1 + '<script>throw new Error("boom");</script>\n')
        self.assert_both_fail(html, "JSERROR")

    def test_verify_fragment_opens_details_and_stacks_steps(self):
        # The title half of case 7 rides on this run: TITLE:same.
        html = self.with_probe(self.template)
        self.assert_both_fail(html, "OK;PROBE:open:stacked;TITLE:same")

    def test_without_verify_fragment_details_stay_closed_and_one_step_shows(self):
        # Defeating the hash test makes the guard take the normal-view branch.
        html = self.edit(self.template, HASH_TEST, '"#never"')
        html = self.with_probe(html)
        self.assert_both_fail(html, "OK;PROBE:closed:single;TITLE:same")

    def test_data_verify_absent_in_source(self):
        self.assertNotIn("data-verify=", self.template)
        html = self.edit(self.template, '<html lang="en">',
                         '<html lang="en" data-verify="OK">')
        self.assertIn("data-verify=", html)
        # verify.sh bails on the preset before it starts Chrome.
        self.assert_renders(html, [
            "render 1440x900: FAIL data-verify preset in source",
            "render 500x844: FAIL data-verify preset in source",
        ], 1)

    def test_title_is_never_touched(self):
        self.assertNotIn("document.title", self.template)
        broken = self.edit(self.template, LOAD_OPEN,
                           LOAD_OPEN + '  document.title = "x";\n')
        self.assertIn("document.title", broken)

    def test_palette_block_identical_to_sheet(self):
        page_block = root_block(self.template)
        self.assertTrue(page_block.startswith(":root {\n  --ink:"), page_block)
        self.assertEqual(page_block, root_block(read(SHEET)))
        broken = self.edit(self.template, "--blue: #1d5fc2;", "--blue: #1d5fc3;")
        self.assertNotEqual(root_block(broken), root_block(read(SHEET)))

    def test_script_budget_at_most_200_lines(self):
        self.assertLessEqual(script_lines(self.template), SCRIPT_BUDGET)
        broken = self.edit(self.template, LAST_SCRIPT_END,
                           "\n" * SCRIPT_BUDGET + LAST_SCRIPT_END)
        self.assertGreater(script_lines(broken), SCRIPT_BUDGET)


if __name__ == "__main__":
    unittest.main()
