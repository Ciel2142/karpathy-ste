"""Tests for the whole-branch review fixes of mermaid_svg.py (wave 1): a comment that holds a
`<figure` tag opens no figure, a Chrome that exits without a dump is named at once, the inline
JSON holds no `<`, and a diagram named like a harness element still renders. They share the
helpers of tests/test_mermaid_svg.py and, as there, a Chrome run has TMPDIR=<tmp>/ and leaves no
process behind."""

import html
import json
import re
import shutil
import time
import unittest
from pathlib import Path
from unittest import mock

from tests.test_mermaid_svg import (
    BUNDLE, FIGURE_TEXT, FIXTURES, HAVE_BUNDLE, NO_BUNDLE, PAGE_TEMPLATE, SECTION, TempCase,
    mermaid_svg, run, svg_text,
)

COMMENT = re.compile(r"<!--.*?-->", re.S)
# A comment is kept; any other figure of the template is cut.
DEMO_FIGURE = re.compile(r"(<!--.*?-->)|<figure\b[^>]*>.*?</figure>", re.S)


class CommentFigureCase(TempCase):
    """A `<figure` tag inside an HTML comment opens no figure (templates/page.html:18)."""

    def comment_page(self):
        """The template with its header comment kept, every demo figure of the body cut and the
        flow section of the fixture before the provenance section; flow.mmd is in place."""
        template = PAGE_TEMPLATE.read_text(encoding="utf-8")
        bare = DEMO_FIGURE.sub(lambda found: found.group(1) or "", template)
        anchor = '<section id="provenance-facet">'
        self.assertEqual(bare.count(anchor), 1)
        page = bare.replace(anchor, SECTION.rstrip("\n") + "\n\n" + anchor)
        self.assertIn('<figure class="code">', COMMENT.search(page).group(0))
        self.assertEqual(COMMENT.sub("", page).count("<figure"), 1)
        out = Path(self.work) / "page"
        (out / "diagrams").mkdir(parents=True)
        shutil.copy(FIXTURES / "flow.mmd", out / "diagrams" / "flow.mmd")
        path = out / "index.html"
        path.write_text(page, encoding="utf-8")
        return path

    def test_page_figures_skips_a_figure_tag_inside_a_comment(self):
        page = (
            '<!-- Copy <figure class="mermaid" data-src="x.mmd"> to add a diagram. -->\n'
            '<figure class="mermaid" data-src="diagrams/real.mmd">\n'
            "  <figcaption>The real one.</figcaption>\n"
            "</figure>\n"
        )
        found = mermaid_svg.page_figures(page)
        self.assertEqual([(f.n, f.src, f.caption) for f in found], [
            (1, "diagrams/real.mmd", "The real one."),
        ])
        real = page[page.rindex("<figure class"):].rstrip()
        self.assertEqual(page[found[0].start:found[0].end], real)

    def test_page_figures_keeps_a_comment_inside_a_figure(self):
        page = (
            '<figure class="mermaid" data-src="d/a.mmd"><!-- </figure> -->'
            "<figcaption>A.</figcaption></figure>\n"
            '<figure class="mermaid" data-src="d/b.mmd"></figure>\n'
        )
        found = mermaid_svg.page_figures(page)
        self.assertEqual([(f.n, f.src) for f in found], [(1, "d/a.mmd"), (2, "d/b.mmd")])
        self.assertEqual(found[0].inner, "<!-- </figure> --><figcaption>A.</figcaption>")
        self.assertEqual(found[0].caption, "A.")
        self.assertEqual(page[found[0].start:found[0].end].count("<!-- </figure> -->"), 1)

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_inline_fills_the_first_figure_that_follows_the_template_comment(self):
        page = self.comment_page()
        code, stdout, stderr = run(["inline", str(page)], self.env())
        self.assert_no_chrome_left()
        self.assertEqual((code, stdout, stderr), (0, "mermaid: ok 1 diagrams\n", ""))
        text = page.read_text(encoding="utf-8")
        figure = re.search(r'<figure class="mermaid".*?</figure>', text, re.S).group(0)
        self.assertEqual(figure.count("<svg"), 1)
        self.assertEqual(text.count("<svg"), 1)
        self.assertIn('<figure class="code">', COMMENT.search(text).group(0))


def fake_chrome(path, body):
    """A Chrome stand-in: a /bin/sh script that records its pid in <path>.pid, then runs body."""
    path.write_text("#!/bin/sh\necho $$ > %s.pid\n%s" % (path, body))
    path.chmod(0o755)
    return str(path)


class EarlyExitCase(TempCase):
    """A Chrome that exits without a complete dump is named at once, not timed out."""

    def render_with(self, chrome, timeout="10"):
        start = time.monotonic()
        with mock.patch.object(mermaid_svg, "CHROME", chrome):
            result = run(
                ["render", str(FIXTURES / "flow.mmd")], self.env({"MERMAID_TIMEOUT": timeout})
            )
        self.assert_no_chrome_left()
        return result, time.monotonic() - start

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_chrome_that_exits_before_the_dump_is_named_with_its_code(self):
        chrome = fake_chrome(Path(self.work) / "chrome", "exit 3\n")
        (code, stdout, stderr), seconds = self.render_with(chrome)
        self.assertEqual(
            (code, stdout, stderr), (1, "mermaid: FAIL Chrome exited 3 before the dump\n", "")
        )
        self.assertLess(seconds, 3)

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_a_dump_that_ends_with_the_exit_is_read_not_called_an_early_exit(self):
        chrome = fake_chrome(
            Path(self.work) / "chrome", "printf '<html><body></body></html>\\n'\nexit 0\n"
        )
        (code, stdout, stderr), seconds = self.render_with(chrome)
        self.assertEqual((code, stdout, stderr), (1, "mermaid: FAIL harness incomplete\n", ""))
        self.assertLess(seconds, 3)


class ScriptJsonCase(TempCase):
    """script_json: no `<` of the text reaches the <script> that holds it."""

    def test_every_less_than_sign_is_escaped_and_the_value_survives(self):
        value = {"a": "x </script> y", "b": "<!--<script>", "c": ["<", "<<", "a<b"], "d": "é"}
        text = mermaid_svg.script_json(value)
        self.assertNotIn("<", text)
        self.assertEqual(json.loads(text), value)

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_labels_with_script_tags_and_a_less_than_sign_render(self):
        # Mermaid drops a raw tag from a label (strict level), so the words around it are read.
        # The harness has to survive the text; `a < b` reaches the SVG as the text it was.
        diagrams = [
            ("end", 'flowchart LR\n  a["x </script> y"] --> b\n'),
            ("start", 'flowchart LR\n  a["x <!--<script> y"] --> b\n'),
            ("less", 'flowchart LR\n  a["a < b"] --> b\n'),
        ]
        with mock.patch.dict("os.environ", self.env()):
            svgs = mermaid_svg.render_many(diagrams, BUNDLE, 60)
        self.assert_no_chrome_left()
        words = {key: html.unescape(svg_text(svg)) for key, svg in svgs.items()}
        self.assertEqual(words, {"end": "x y b", "start": "x b", "less": "a < b b"})


class HarnessIdCase(TempCase):

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_diagrams_named_like_the_harness_elements_render(self):
        diagrams = [
            ("out-1", (FIXTURES / "flow.mmd").read_text()),
            ("svg-1", (FIXTURES / "state.mmd").read_text()),
        ]
        with mock.patch.dict("os.environ", self.env()):
            svgs = mermaid_svg.render_many(diagrams, BUNDLE, 60)
        self.assert_no_chrome_left()
        self.assertEqual(list(svgs), ["out-1", "svg-1"])
        self.assertIn("receive the message", svg_text(svgs["out-1"]))
        self.assertIn("Sent", svg_text(svgs["svg-1"]))


if __name__ == "__main__":
    unittest.main()
