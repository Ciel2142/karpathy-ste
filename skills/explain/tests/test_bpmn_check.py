"""Tests for bpmn.py check: the four coverage conditions of spec 2.4 on the fixture page."""

import contextlib
import html as htmllib
import io
import re
import subprocess
import sys
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import bpmn  # noqa: E402
import bpmn_page as bpmn_page_module  # noqa: E402
from bpmn_page import FIXTURES, PAGE_TEMPLATE, bpmn_page  # noqa: E402

BPMN_PY = Path(bpmn.__file__).resolve()
SECTION = (FIXTURES / "bpmn-section.html").read_text(encoding="utf-8")
FIXTURE_LINES = (FIXTURES / "two_planes.bpmn").read_text(encoding="utf-8").split("\n")
CITE = re.compile(r'<cite data-path="two_planes\.bpmn" data-line="([0-9]+)".*?</cite>', re.DOTALL)
LABEL = re.compile(r'<span class="bpmn-label">(.*?)</span>', re.DOTALL)


def run(argv):
    """Run main with argv; return the exit code, stdout and stderr."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = bpmn.main(argv)
    return code, out.getvalue(), err.getvalue()


def line_of(needle):
    """The 1-based line of the first fixture line that holds `needle`."""
    for number, text in enumerate(FIXTURE_LINES, 1):
        if needle in text:
            return number
    raise AssertionError("fixture lacks " + needle)


def without_cites(section, number):
    """The section without its cites of fixture line `number`; fails if it has none."""
    text, removed = re.subn(
        r'<cite data-path="two_planes\.bpmn" data-line="%d".*?</cite>' % number, "", section, flags=re.DOTALL
    )
    if not removed:
        raise AssertionError("no cite of line %d in the section" % number)
    return text


def without_figure(section, plane):
    """The section without the figure.bpmn of `plane`; fails if it has none."""
    pattern = r'<figure class="bpmn">\s*<svg class="bpmn"[^>]*data-plane="%s".*?</figure>\s*' % plane
    text, removed = re.subn(pattern, "", section, count=1, flags=re.DOTALL)
    if removed != 1:
        raise AssertionError("no figure of plane %s in the section" % plane)
    return text


def replace_once(text, old, new):
    if old not in text:
        raise AssertionError("%r is not in the text" % old)
    return text.replace(old, new, 1)


def first_label(section):
    """(line, unescaped label text, the cite markup) of the first labelled cite in the section."""
    match = CITE.search(section)
    found = LABEL.search(match.group())
    return int(match.group(1)), htmllib.unescape(found.group(1)), match.group()


class CheckCase(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)

    def check(self, section=SECTION, not_covered=None, bpmn_edits=()):
        """Build the page, optionally set the Not covered text and edit the .bpmn copy, run check on it."""
        page = bpmn_page(self.out, section)
        if bpmn_edits:
            copy = self.out / "two_planes.bpmn"
            text = copy.read_text(encoding="utf-8")
            for old, new in bpmn_edits:
                text = replace_once(text, old, new)
            copy.write_text(text, encoding="utf-8")
        if not_covered is not None:
            text = page.read_text(encoding="utf-8")
            text = replace_once(
                text, '<p class="not-covered">Not covered: none</p>', '<p class="not-covered">Not covered: %s</p>' % not_covered
            )
            page.write_text(text, encoding="utf-8")
        return run(["check", str(page)])

    def test_fixture_page_passes(self):
        """Red when any condition fails on the committed fragment, or the summary is not ok."""
        code, out, err = self.check()
        self.assertEqual((code, out, err), (0, "bpmn: ok\n", ""))

    def test_page_without_bpmn_cites_is_none(self):
        """Red when a page with no .bpmn cite fails, or its summary is not none."""
        code, out, _err = run(["check", str(PAGE_TEMPLATE)])
        self.assertEqual((code, out), (0, "bpmn: none\n"))

    def test_removed_plane_svg_fails_condition_1(self):
        """Red when a plane with no svg.bpmn and not in Not covered passes."""
        code, out, _err = self.check(without_figure(SECTION, "STAGE_A"))
        self.assertEqual(code, 1)
        self.assertIn(
            "page | plane | STAGE_A (Первичная проверка) has no svg.bpmn and is not in Not covered\n", out
        )

    def test_unnamed_plane_uses_its_id(self):
        """Red when a plane without a name is not named by its id."""
        code, out, _err = self.check(without_figure(SECTION, "Collaboration_1"))
        self.assertEqual(code, 1)
        self.assertIn(
            "page | plane | Collaboration_1 (Collaboration_1) has no svg.bpmn and is not in Not covered\n", out
        )

    def test_plane_named_in_not_covered_passes(self):
        """Red when the name of a plane in p.not-covered does not excuse its missing svg."""
        code, out, _err = self.check(without_figure(SECTION, "STAGE_A"), "Первичная проверка, no time")
        self.assertEqual((code, out), (0, "bpmn: ok\n"))

    def test_sub_process_without_cite_fails_condition_2(self):
        """Red when a sub-process with no cite passes, or its name in Not covered does not excuse it."""
        section = without_cites(SECTION, line_of('id="EventSub_1"'))
        code, out, _err = self.check(section)
        self.assertEqual(code, 1)
        self.assertIn(
            "page | sub-process | EventSub_1 (Ошибка в процессе) has no cite and is not in Not covered\n", out
        )
        code, out, _err = self.check(section, "Ошибка в процессе")
        self.assertEqual((code, out), (0, "bpmn: ok\n"))

    def test_transaction_and_ad_hoc_count_as_sub_processes(self):
        """Red when condition 2 counts only bpmn:subProcess: an uncited transaction or ad-hoc one then passes."""
        section = SECTION
        for needle in ('<bpmn:subProcess id="STAGE_A"', 'name="Первичная проверка">'):
            section = without_cites(section, line_of(needle))
        for kind in ("transaction", "adHocSubProcess"):
            with self.subTest(kind=kind):
                edits = [('<bpmn:subProcess id="STAGE_A"', '<bpmn:%s id="STAGE_A"' % kind),
                         ("</bpmn:subProcess>", "</bpmn:%s>" % kind)]
                code, out, _err = self.check(section, bpmn_edits=edits)
                self.assertEqual(code, 1)
                self.assertIn(
                    "page | sub-process | STAGE_A (Первичная проверка) has no cite and is not in Not covered\n", out
                )

    def test_longer_name_in_not_covered_does_not_excuse_its_prefix(self):
        """Red when Not covered matches by substring: "Первичная проверка СМЭВ4" then excuses STAGE_A."""
        longer = "Первичная проверка СМЭВ4"
        section = replace_once(SECTION, '<span class="bpmn-label">Ошибка в процессе</span>',
                               '<span class="bpmn-label">%s</span>' % longer)
        for needle in ('<bpmn:subProcess id="STAGE_A"', 'name="Первичная проверка">'):
            section = without_cites(section, line_of(needle))
        edits = [('name="Ошибка в процессе"', 'name="%s"' % longer)]
        code, out, _err = self.check(section, longer, edits)
        self.assertEqual(code, 1, out)
        self.assertEqual(
            out,
            "page | sub-process | STAGE_A (Первичная проверка) has no cite and is not in Not covered\n"
            "bpmn: 1 failures\n",
        )
        code, out, _err = self.check(section, "%s; Первичная проверка" % longer, edits)
        self.assertEqual((code, out), (0, "bpmn: ok\n"))

    def test_not_covered_chunks_join_with_a_space(self):
        """Red when the text chunks of p.not-covered join with "": a <br> then merges two words."""
        section = without_cites(SECTION, line_of('id="EventSub_1"'))
        code, out, _err = self.check(section, "Ошибка в<br>процессе")
        self.assertEqual((code, out), (0, "bpmn: ok\n"))

    def test_cite_of_a_child_does_not_cover_its_sub_process(self):
        """Red when a cite of a task inside STAGE_A counts as a cite of STAGE_A."""
        section = SECTION
        for needle in ('<bpmn:subProcess id="STAGE_A"', 'name="Первичная проверка">'):
            section = without_cites(section, line_of(needle))
        self.assertIn('data-line="%d"' % line_of('id="Task_send"'), section)
        code, out, _err = self.check(section)
        self.assertEqual(code, 1)
        self.assertIn(
            "page | sub-process | STAGE_A (Первичная проверка) has no cite and is not in Not covered\n", out
        )

    def test_cite_of_a_di_shape_covers_its_element(self):
        """Red when a cite on the DI shape of EventSub_1 does not count as a cite of EventSub_1."""
        number = line_of('id="EventSub_1_di"')
        shape = (
            '<cite data-path="two_planes.bpmn" data-line="%d" data-snippet="x">two_planes.bpmn:%d <code>x</code>'
            '<span class="bpmn-label">Ошибка в процессе</span></cite>' % (number, number)
        )
        section = without_cites(SECTION, line_of('id="EventSub_1"'))
        section = replace_once(section, "</section>", shape + "\n</section>")
        code, out, _err = self.check(section)
        self.assertEqual((code, out), (0, "bpmn: ok\n"))

    def test_missing_label_fails_condition_3(self):
        """Red when a BPMN cite with no span.bpmn-label passes."""
        number, _label, markup = first_label(SECTION)
        section = replace_once(SECTION, markup, LABEL.sub("", markup, count=1))
        code, out, _err = self.check(section)
        self.assertEqual(code, 1)
        self.assertIn("stage-a | label | two_planes.bpmn:%d | missing\n" % number, out)

    def test_stale_label_fails_condition_3(self):
        """Red when a hand-edited label passes, or the line does not show both texts."""
        number, label, markup = first_label(SECTION)
        edited = LABEL.sub('<span class="bpmn-label">Правка</span>', markup, count=1)
        code, out, _err = self.check(replace_once(SECTION, markup, edited))
        self.assertEqual(code, 1)
        self.assertIn(
            'stage-a | label | two_planes.bpmn:%d | stale: "Правка" is not "%s"\n' % (number, label), out
        )

    def test_foreign_data_id_fails_condition_4(self):
        """Red when an svg.bpmn holds a data-id that is no element of the file."""
        code, out, _err = self.check(replace_once(SECTION, 'data-id="Task_recv"', 'data-id="Nope_1"'))
        self.assertEqual(code, 1)
        self.assertIn("stage-a | diagram | data-id Nope_1 is not in two_planes.bpmn\n", out)

    def test_foreign_plane_fails_condition_4(self):
        """Red when an svg.bpmn with a data-plane of no cited file passes."""
        code, out, _err = self.check(replace_once(SECTION, 'data-plane="STAGE_A"', 'data-plane="Nope_P"'))
        self.assertEqual(code, 1)
        self.assertIn("stage-a | diagram | data-plane Nope_P is no plane of a cited file\n", out)

    def test_missing_bpmn_file_is_one_failure_line(self):
        """Red when a missing .bpmn gives a traceback, more than one line, or no file line."""
        page = bpmn_page(self.out)
        (self.out / "two_planes.bpmn").unlink()
        done = subprocess.run(
            [sys.executable, "-B", str(BPMN_PY), "check", str(page)], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(done.returncode, 1)
        self.assertEqual(done.stderr, "")
        lines = done.stdout.splitlines()
        self.assertEqual(len(lines), 2, done.stdout)
        self.assertRegex(lines[0], r"^stage-a \| file \| two_planes\.bpmn \| .*two_planes\.bpmn")
        self.assertEqual(lines[1], "bpmn: 1 failures")

    def test_summary_counts_failures(self):
        """Red when the summary does not count every failure line."""
        number, _label, markup = first_label(SECTION)
        section = replace_once(SECTION, markup, LABEL.sub("", markup, count=1))
        section = replace_once(section, 'data-id="Task_recv"', 'data-id="Nope_1"')
        code, out, _err = self.check(section)
        self.assertEqual(code, 1)
        self.assertEqual(len(out.splitlines()), 3, out)
        self.assertEqual(out.splitlines()[-1], "bpmn: 2 failures")

    def one_cite_section(self):
        """A section with one labelled cite of Task_svc and no diagram, as a sheet has."""
        cite = next(m.group() for m in CITE.finditer(SECTION) if m.group(1) == str(line_of('id="Task_svc"')))
        return '<section id="stage-a">\n<p>One step.</p>\n<div class="cites">%s</div>\n</section>\n' % cite

    def test_sheet_rung_skips_conditions_1_and_2(self):
        """Red when --rung sheet still asks for every plane and sub-process, or a page skips them too."""
        page = bpmn_page(self.out, self.one_cite_section())
        self.assertEqual(run(["check", "--rung", "sheet", str(page)])[:2], (0, "bpmn: ok\n"))
        for argv in (["check", str(page)], ["check", "--rung", "page", str(page)]):
            with self.subTest(argv=argv[1:-1]):
                code, out, _err = run(argv)
                self.assertEqual(code, 1)
                self.assertIn("page | plane | Collaboration_1 (Collaboration_1) has no svg.bpmn", out)

    def test_sheet_rung_keeps_conditions_3_and_4(self):
        """Red when --rung sheet also skips the label check or the diagram check."""
        section = LABEL.sub('<span class="bpmn-label">Правка</span>', self.one_cite_section(), count=1)
        section = section.replace("</section>", '<svg class="bpmn" data-plane="Nope_P"></svg>\n</section>')
        code, out, _err = run(["check", "--rung", "sheet", str(bpmn_page(self.out, section))])
        self.assertEqual(code, 1)
        self.assertIn('| stale: "Правка" is not', out)
        self.assertIn("stage-a | diagram | data-plane Nope_P is no plane of a cited file\n", out)
        self.assertEqual(out.splitlines()[-1], "bpmn: 2 failures")

    def test_unknown_rung_is_usage(self):
        """Red when check accepts a rung that is not sheet, page or lesson, or --rung without a value."""
        page = bpmn_page(self.out)
        self.assertEqual(run(["check", "--rung", "video", str(page)])[0], 2)
        self.assertEqual(run(["check", "--rung", str(page)])[0], 2)
        self.assertEqual(run(["check", "--rung", "lesson", str(page)])[:2], (0, "bpmn: ok\n"))

    def test_no_argument_or_no_data_root_is_usage(self):
        """Red when check runs without a page, or on a page with no data-root, and does not exit 2."""
        self.assertEqual(run(["check"])[0], 2)
        page = bpmn_page(self.out)
        page.write_text(replace_once(page.read_text(encoding="utf-8"), 'data-root="."', 'data-root=""'), encoding="utf-8")
        self.assertEqual(run(["check", str(page)])[0], 2)
        self.assertEqual(run(["check", str(self.out / "absent.html")])[0], 2)


class PageCase(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)

    def test_bpmn_page_places_the_section_and_keeps_the_root(self):
        """Red when the section lands after the provenance section, its nav link is missing, or the root changes."""
        text = bpmn_page(self.out).read_text(encoding="utf-8")
        self.assertEqual(text.count('data-root="."'), 1)
        self.assertTrue((self.out / "two_planes.bpmn").is_file())
        self.assertLess(text.index('<section id="stage-a">'), text.index('<section id="provenance-facet">'))
        self.assertLess(text.index('<a href="#stage-a">'), text.index('<a href="#provenance-facet">'))

    def test_bpmn_page_needs_each_anchor_once(self):
        """Red when bpmn_page writes a page although an anchor is missing or doubled in the template."""
        template = self.out / "page.html"
        source = PAGE_TEMPLATE.read_text(encoding="utf-8")
        for broken in (source.replace('data-root="."', ""), source + '<section id="provenance-facet">'):
            template.write_text(broken, encoding="utf-8")
            with mock.patch.object(bpmn_page_module, "PAGE_TEMPLATE", template):
                with self.assertRaises(AssertionError):
                    bpmn_page(self.out / "built")


if __name__ == "__main__":
    unittest.main()
