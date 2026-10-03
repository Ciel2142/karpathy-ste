"""Tests for cite_check: provenance, per-citation checks, section coverage and the
command line (spec section 5.3 item 2 and section 5.5 item 3)."""

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import cite_check  # noqa: E402

SOURCE = "alpha beta gamma\ndef run(x):   return x + 1\ntab\tseparated   words here\n"
TWELVE = "w1 w2 w3 w4 w5 w6 w7 w8 w9 w10 w11 w12"
THIRTEEN = TWELVE + " w13"
LONG_LINE = TWELVE + " w13 tail\n"


def cite(path="src.txt", line="1", snippet="alpha beta", **override):
    attrs = {"data-path": path, "data-line": line, "data-snippet": snippet}
    attrs.update(override)
    shown = " ".join('%s="%s"' % (k, v) for k, v in attrs.items() if v is not None)
    return "<cite %s>%s:%s</cite>" % (shown, path, line)


def section(body, ident=None, heading=None):
    id_attr = ' id="%s"' % ident if ident else ""
    head = "<h2>%s</h2>" % heading if heading else ""
    return "<section%s>%s%s</section>" % (id_attr, head, body)


def page(body, root="ROOT", kind="file", provenance=True):
    prov = ""
    if provenance:
        attrs = ""
        if root is not None:
            attrs += ' data-root="%s"' % root
        if kind is not None:
            attrs += ' data-kind="%s"' % kind
        prov = '<footer id="provenance"%s>made today</footer>' % attrs
    return "<html><body>%s%s</body></html>" % (body, prov)


class CiteCheckCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name
        self.write("src.txt", SOURCE)

    def write(self, name, text):
        path = os.path.join(self.dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def run_check(self, body, kind="file", root="ROOT", provenance=True):
        root = self.dir if root == "ROOT" else root
        return cite_check.check(page(body, root, kind, provenance), self.dir)


class TestGood(CiteCheckCase):
    def test_good_document_passes(self):
        body = section(cite(), heading="One") + section(cite(line="2", snippet="return x + 1"))
        self.assertEqual(self.run_check(body), [])

    def test_whitespace_only_difference_passes(self):
        body = section(
            cite(line="2", snippet="def   run(x):\n return   x +\t1")
            + cite(line="3", snippet="tab separated words here")
        )
        self.assertEqual(self.run_check(body), [])

    def test_twelve_word_snippet_passes(self):
        self.write("long.txt", LONG_LINE)
        body = section(cite(path="long.txt", snippet=TWELVE))
        self.assertEqual(self.run_check(body), [])

    def test_relative_data_root_resolves_against_html_dir(self):
        self.write("sub/inner.txt", "needle here\n")
        body = section(cite(path="inner.txt", snippet="needle"))
        html = page(body, root="sub", kind="file")
        self.assertEqual(cite_check.check(html, self.dir), [])

    def test_url_cite_is_skipped_without_line_or_file(self):
        body = section(
            cite(path="https://example.com/a", line=None, snippet="anything")
            + cite(path="http://example.com/b", line="999", snippet="not checked")
        )
        self.assertEqual(self.run_check(body), [])

    def test_url_cite_still_counts_for_section_coverage(self):
        body = section(cite(path="https://example.com/a", line=None))
        self.assertEqual(self.run_check(body), [])

    def test_html_without_path_cites_needs_no_data_root(self):
        self.assertEqual(self.run_check("<p>x</p>", kind="topic", root=None), [])


class TestProvenance(CiteCheckCase):
    def test_missing_provenance_element_is_one_failure(self):
        out = self.run_check(section(cite()), provenance=False)
        self.assertEqual(len([f for f in out if f.startswith("provenance:")]), 1)
        self.assertIn("provenance: missing", out[0])

    def test_missing_data_kind_is_one_failure(self):
        out = self.run_check(section(cite()), kind=None)
        self.assertEqual(len(out), 1)
        self.assertIn("provenance: missing data-kind", out[0])

    def test_unknown_data_kind_fails(self):
        out = self.run_check(section(cite()), kind="banana")
        self.assertEqual(len(out), 1)
        self.assertIn("unknown data-kind", out[0])

    def test_first_provenance_element_wins(self):
        html = page(section(cite()), self.dir, "file").replace(
            "</body>", '<p id="provenance" data-kind="topic"></p></body>'
        )
        self.assertEqual(cite_check.check(html, self.dir), [])

    def test_path_cite_without_data_root_fails(self):
        out = self.run_check(section(cite()), root=None)
        self.assertEqual(len(out), 1)
        self.assertIn("cite 1", out[0])
        self.assertIn("data-root missing", out[0])

    def test_empty_data_root_counts_as_missing(self):
        out = self.run_check(section(cite()), root="")
        self.assertIn("data-root missing", out[0])

    def test_missing_provenance_still_fails_each_path_cite(self):
        out = self.run_check(section(cite()), provenance=False)
        self.assertTrue(any("data-root missing" in f for f in out))


class TestCites(CiteCheckCase):
    def test_missing_file_fails(self):
        out = self.run_check(section(cite(path="nope.txt")))
        self.assertEqual(len(out), 1)
        self.assertIn("file missing", out[0])
        self.assertIn("nope.txt:1", out[0])

    def test_directory_as_path_counts_as_missing_file(self):
        os.makedirs(os.path.join(self.dir, "adir"))
        self.assertIn("file missing", self.run_check(section(cite(path="adir")))[0])

    def test_line_beyond_file_is_out_of_range(self):
        out = self.run_check(section(cite(line="4")))
        self.assertEqual(len(out), 1)
        self.assertIn("out of range", out[0])
        self.assertIn("src.txt:4", out[0])

    def test_last_line_is_in_range(self):
        self.assertEqual(self.run_check(section(cite(line="3", snippet="words here"))), [])

    def test_zero_line_fails(self):
        self.assertIn("not a positive integer", self.run_check(section(cite(line="0")))[0])

    def test_non_integer_line_fails(self):
        for bad in ("abc", "1.5", "-2", "+1", ""):
            with self.subTest(line=bad):
                out = self.run_check(section(cite(line=bad)))
                self.assertEqual(len(out), 1)
                self.assertTrue(
                    "not a positive integer" in out[0] or "data-line missing" in out[0]
                )

    def test_snippet_not_on_line_fails(self):
        out = self.run_check(section(cite(snippet="delta epsilon")))
        self.assertEqual(len(out), 1)
        self.assertIn("snippet not found", out[0])

    def test_snippet_from_another_line_fails(self):
        out = self.run_check(section(cite(line="1", snippet="return x + 1")))
        self.assertIn("snippet not found", out[0])

    def test_thirteen_word_snippet_is_reported(self):
        self.write("long.txt", LONG_LINE)
        out = self.run_check(section(cite(path="long.txt", snippet=THIRTEEN)))
        self.assertEqual(len(out), 1)
        self.assertIn("snippet has 13 words (max 12)", out[0])

    def test_missing_attributes_fail_each(self):
        for attr in ("data-path", "data-line", "data-snippet"):
            with self.subTest(attr=attr):
                out = self.run_check(section(cite(**{attr: None})))
                self.assertEqual(len(out), 1)
                self.assertIn("%s missing" % attr, out[0])

    def test_word_count_and_missing_file_are_both_reported(self):
        out = self.run_check(section(cite(path="nope.txt", snippet=THIRTEEN)))
        self.assertEqual(len(out), 2)
        self.assertIn("13 words", out[0])
        self.assertIn("file missing", out[1])

    def test_failures_are_numbered_in_document_order(self):
        body = section(cite() + cite(path="nope.txt") + cite(line="9"))
        out = self.run_check(body)
        self.assertEqual(len(out), 2)
        self.assertIn("cite 2", out[0])
        self.assertIn("cite 3", out[1])

    def test_non_utf8_file_is_read_with_replacement(self):
        path = os.path.join(self.dir, "bin.txt")
        with open(path, "wb") as handle:
            handle.write(b"caf\xe9 au lait\n")
        self.assertEqual(self.run_check(section(cite(path="bin.txt", snippet="au lait"))), [])


def shown(text, path="src.txt", line="1", snippet="alpha beta"):
    """A <cite> with correct attributes and the given visible text (markup allowed)."""
    attrs = {"data-path": path, "data-line": line, "data-snippet": snippet}
    attrs = " ".join('%s="%s"' % (k, v) for k, v in attrs.items() if v is not None)
    return "<cite %s>%s</cite>" % (attrs, text)


class TestVisibleText(CiteCheckCase):
    LACKS = 'cite 1 (src.txt:1): visible text lacks "src.txt:1"'

    def test_visible_text_without_basename_fails(self):
        out = self.run_check(section(shown(':1 "alpha beta"')))
        self.assertEqual(out, [self.LACKS])

    def test_visible_text_with_basename_passes(self):
        self.write("sub/dir/src.txt", SOURCE)
        for text in (
            'src.txt:1 "alpha beta"',
            'dir/src.txt:1 "alpha beta"',
            '<code>src.txt</code>:1 <q>alpha beta</q>',
        ):
            with self.subTest(text=text):
                body = section(shown(text, path="sub/dir/src.txt"))
                self.assertEqual(self.run_check(body), [])

    def test_visible_line_prefix_does_not_match(self):
        """`src.txt:12` holds `src.txt:1` as a substring, so a plain `in` test passes it.
        The regex guard `(?![0-9])` rejects a digit after the line number."""
        out = self.run_check(section(shown('src.txt:12 "alpha beta"')))
        self.assertEqual(out, [self.LACKS])

    def test_visible_name_suffix_does_not_match(self):
        """`mysrc.txt:1` holds `src.txt:1` as a substring; the regex guard `(?<![\\w.-])`
        rejects a name character before the basename."""
        out = self.run_check(section(shown('mysrc.txt:1 "alpha beta"')))
        self.assertEqual(out, [self.LACKS])

    def test_text_after_cite_end_is_not_visible_text(self):
        """The end tag stops the capture: the text after </cite> does not count."""
        out = self.run_check(section(shown(':1 "alpha beta"') + " src.txt:1"))
        self.assertEqual(out, [self.LACKS])

    def test_visible_check_runs_without_data_root(self):
        out = self.run_check(section(shown(':1 "alpha beta"')), root=None)
        self.assertEqual(out, [self.LACKS, "cite 1 (src.txt:1): data-root missing"])

    def test_url_cite_visible_text_is_free(self):
        url = "https://example.com/a/b.html"
        body = section(shown("any text", path=url, line=None) + shown("", path=url))
        self.assertEqual(self.run_check(body), [])


class TestSections(CiteCheckCase):
    def test_file_kind_section_without_cite_fails(self):
        out = self.run_check(section(cite(), ident="a") + section("<p>no source</p>", ident="b"))
        self.assertEqual(len(out), 1)
        self.assertIn("section 2 (b): no citation", out[0])

    def test_directory_kind_section_without_cite_fails(self):
        out = self.run_check(section("<p>x</p>", heading="Intro"), kind="directory")
        self.assertEqual(len(out), 1)
        self.assertIn("section 1 (Intro): no citation", out[0])

    def test_unnamed_section_is_labelled(self):
        out = self.run_check(section("<p>x</p>"))
        self.assertIn("section 1 (unnamed): no citation", out[0])

    def test_topic_kind_with_citeless_sections_passes(self):
        self.assertEqual(self.run_check(section("<p>x</p>") + section("<p>y</p>"), kind="topic"), [])

    def test_conversation_kind_with_citeless_sections_passes(self):
        self.assertEqual(self.run_check(section("<p>x</p>"), kind="conversation"), [])

    def test_cite_in_nested_section_satisfies_both(self):
        inner = section(cite(), ident="inner")
        self.assertEqual(self.run_check(section("<p>x</p>" + inner, ident="outer")), [])

    def test_outer_cite_does_not_satisfy_nested_section(self):
        inner = section("<p>no</p>", ident="inner")
        out = self.run_check(section(cite() + inner, ident="outer"))
        self.assertEqual(len(out), 1)
        self.assertIn("section 2 (inner)", out[0])

    def test_failing_cite_still_counts_for_section_coverage(self):
        out = self.run_check(section(cite(path="nope.txt")))
        self.assertEqual(len(out), 1)
        self.assertNotIn("no citation", out[0])


class TestMain(CiteCheckCase):
    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cite_check.main(argv)
        return code, out.getvalue(), err.getvalue()

    def html_file(self, body, **kw):
        root = self.dir if kw.pop("root", "ROOT") == "ROOT" else None
        return self.write("index.html", page(body, root, kw.get("kind", "file")))

    def test_pass_prints_ok_and_exits_0(self):
        code, out, err = self.run_main([self.html_file(section(cite()))])
        self.assertEqual((code, out, err), (0, "cite_check: ok\n", ""))

    def test_failures_print_lines_and_exit_1(self):
        path = self.html_file(section(cite(line="9") + cite(path="nope.txt")))
        code, out, err = self.run_main([path])
        lines = out.splitlines()
        self.assertEqual(code, 1)
        self.assertEqual(len(lines), 3)
        self.assertIn("out of range", lines[0])
        self.assertIn("file missing", lines[1])
        self.assertEqual(lines[2], "cite_check: 2 failures")
        self.assertEqual(err, "")

    def test_html_dir_is_the_files_directory(self):
        self.write("site/src.txt", "rel text\n")
        body = section(cite(snippet="rel text"))
        html = '<footer id="provenance" data-root="." data-kind="file"></footer>' + body
        path = self.write("site/index.html", html)
        self.assertEqual(self.run_main([path])[0], 0)

    def test_no_arguments_is_usage_error(self):
        code, out, err = self.run_main([])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err, "usage: cite_check.py <index.html>\n")

    def test_two_arguments_is_usage_error(self):
        code, out, err = self.run_main(["a.html", "b.html"])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err, "usage: cite_check.py <index.html>\n")

    def test_unreadable_file_exits_2_with_os_error(self):
        code, out, err = self.run_main([os.path.join(self.dir, "absent.html")])
        self.assertEqual((code, out), (2, ""))
        self.assertIn("absent.html", err)

    def test_utf8_bom_in_html_is_accepted(self):
        path = os.path.join(self.dir, "bom.html")
        with open(path, "w", encoding="utf-8-sig") as handle:
            handle.write(page(section(cite()), self.dir, "file"))
        self.assertEqual(self.run_main([path])[0], 0)


if __name__ == "__main__":
    unittest.main()
