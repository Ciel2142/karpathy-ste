"""Tests for bpmn.py label: the owner of a line, the label rule and the page rewrite (spec 2.3)."""

import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import bpmn  # noqa: E402
import bpmn_label  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "two_planes.bpmn"
FIXTURE_LINES = FIXTURE.read_text(encoding="utf-8").split("\n")
SPAN = '<span class="bpmn-label">%s</span>'


def run(argv):
    """Run main with argv; return the exit code, stdout and stderr."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = bpmn.main(argv)
    return code, out.getvalue(), err.getvalue()


def line_of(needle, after=0):
    """The 1-based line of the first fixture line after `after` that holds `needle`."""
    for number, text in enumerate(FIXTURE_LINES, 1):
        if number > after and needle in text:
            return number
    raise AssertionError("fixture lacks " + needle)


def blank_line():
    """The first blank fixture line inside the root element."""
    for number, text in enumerate(FIXTURE_LINES[2:-2], 3):
        if not text.strip():
            return number
    raise AssertionError("fixture has no blank line")


def cite(section_path, line, snippet="x"):
    return (
        '<cite data-path="%s" data-line="%d" data-snippet="%s">f:%d <code>%s</code></cite>'
        % (section_path, line, snippet, line, snippet)
    )


def page(*sections, root="."):
    """A page whose sections are (id, cite markup) pairs."""
    body = "".join('<section id="%s"><h2>t</h2>\n%s\n</section>\n' % pair for pair in sections)
    return '<html><body><div id="provenance" data-kind="file" data-root="%s"></div>\n%s</body></html>\n' % (
        root,
        body,
    )


class Dir(unittest.TestCase):
    """A temp directory with the fixture copied in as two_planes.bpmn."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        shutil.copy(FIXTURE, self.tmp / "two_planes.bpmn")
        self.index = self.tmp / "index.html"

    def write_bpmn(self, body, name="small.bpmn", eol="\n"):
        text = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
            'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" id="Defs_1">\n'
            + body
            + "</bpmn:definitions>\n"
        )
        (self.tmp / name).write_bytes(text.replace("\n", eol).encode("utf-8"))
        return bpmn.load(self.tmp / name)


class LabelOfFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = bpmn.load(FIXTURE)

    def at(self, number):
        index = bpmn.owner(self.model, number)
        self.assertIsNotNone(index, "line %d has no owner" % number)
        return bpmn.label_of(self.model, index)

    def test_named_task_line(self):
        """Red when a named flow node is labelled by its kind and id instead of its name."""
        self.assertEqual(self.at(line_of('id="Task_svc"')), "Проверить паспорт клиента")

    def test_unnamed_node_is_kind_and_id(self):
        """Red when the kind is not split at its capitals or the id is dropped."""
        self.assertEqual(self.at(line_of('id="Gateway_1"')), "exclusive gateway Gateway_1")

    def test_sub_process_kind_is_two_words(self):
        """Red when a camel-case kind is lowercased without splitting it."""
        self.assertEqual(bpmn.label_of(self.model, self.model.by_id["EventSub_1"]), "Ошибка в процессе")
        self.assertEqual(bpmn_label._kind_words("subProcess"), "sub process")

    def test_sequence_flow_line(self):
        """Red when a flow shows ids instead of the names of its source and target."""
        self.assertEqual(
            self.at(line_of('id="Flow_1" sourceRef="Start_1"')),
            "Заявка принята → Первичная проверка",
        )

    def test_condition_line_is_its_flow_with_flow_name(self):
        """Red when the condition line is not its flow's label or the flow name is not appended."""
        self.assertEqual(
            self.at(line_of("${approved}")),
            "exclusive gateway Gateway_1 → Заявка одобрена, Да",
        )

    def test_error_carries_its_code(self):
        """Red when an error is labelled by its name alone."""
        self.assertEqual(self.at(line_of('<bpmn:error id="Error_1"')), "CheckFailed (CHECK_FAILED)")

    def test_di_shape_line_is_its_element(self):
        """Red when a DI shape is labelled as a shape instead of by its bpmnElement."""
        self.assertEqual(self.at(line_of('id="Task_svc_di"')), "Проверить паспорт клиента")

    def test_bpmn_label_line_is_its_edge_element(self):
        """Red when a BPMNLabel line does not resolve to the label of its edge's flow."""
        start = line_of('id="Flow_yes_di"')
        for number in (line_of("<bpmndi:BPMNLabel>", start), line_of("<dc:Bounds", line_of("<bpmndi:BPMNLabel>", start))):
            self.assertEqual(self.at(number), "exclusive gateway Gateway_1 → Заявка одобрена, Да")

    def test_waypoint_line_is_its_edge(self):
        """Red when a waypoint, which has no row, does not climb to its edge."""
        self.assertEqual(
            self.at(line_of("<di:waypoint", line_of('id="Flow_yes_di"'))),
            "exclusive gateway Gateway_1 → Заявка одобрена, Да",
        )

    def test_process_and_participant_lines(self):
        """Red when a participant or a process is labelled by kind and id although it has a name."""
        self.assertEqual(self.at(line_of("<bpmn:participant ")), "Заказчик")
        self.assertEqual(self.at(line_of("<bpmn:process ")), "Основной процесс")

    def test_incoming_line_resolves_to_its_sub_process(self):
        """Red when a child without a row does not climb to its nearest ancestor with one."""
        number = line_of("<bpmn:incoming>Flow_1</bpmn:incoming>")
        self.assertEqual(bpmn.owner(self.model, number), self.model.by_id["STAGE_A"])
        self.assertEqual(self.at(number), "Первичная проверка")

    def test_multi_line_tag_continuation_line_belongs_to_its_element(self):
        """Red when a line inside a multi-line opening tag resolves to the parent."""
        number = line_of('name="Первичная проверка"')
        self.assertEqual(bpmn.owner(self.model, number), self.model.by_id["STAGE_A"])

    def test_line_of_a_child_task_is_not_its_sub_process(self):
        """Red when the owner is the outermost element instead of the innermost."""
        number = line_of('id="Task_send"')
        self.assertEqual(bpmn.owner(self.model, number), self.model.by_id["Task_send"])
        self.assertNotEqual(bpmn.owner(self.model, number), self.model.by_id["STAGE_A"])

    def test_name_newline_becomes_one_space(self):
        """Red when the newline of a name is kept in the label."""
        self.assertEqual(self.at(line_of('id="Task_send"')), 'Отправить "отчёт" клиенту')

    def test_blank_and_comment_lines_have_no_owner(self):
        """Red when a blank, comment, declaration or past-the-end line resolves to definitions."""
        for number in (blank_line(), line_of("<!--"), 1, len(self.model.lines) + 1, 0):
            self.assertIsNone(bpmn.owner(self.model, number), number)


class OwnerEdgeCases(Dir):
    def test_crlf_blank_line_has_no_owner(self):
        """Red when a blank line of a CRLF file keeps its carriage return and counts as text."""
        model = self.write_bpmn('  <bpmn:process id="P_1">\n\n  </bpmn:process>\n', eol="\r\n")
        self.assertIsNone(bpmn.owner(model, 4))
        self.assertEqual(bpmn.label_of(model, bpmn.owner(model, 5)), "process P_1")

    def test_multi_line_comment_has_no_owner(self):
        """Red when only the one-line comments are recognised."""
        model = self.write_bpmn('  <!-- a\n  b -->\n  <bpmn:process id="P_1">\n  </bpmn:process>\n')
        self.assertIsNone(bpmn.owner(model, 3))
        self.assertIsNone(bpmn.owner(model, 4))
        self.assertIsNotNone(bpmn.owner(model, 5))

    def test_message_signal_lane_and_unnamed_process(self):
        """Red when a row of the table is missing or an unnamed container loses its kind and id."""
        model = self.write_bpmn(
            '  <bpmn:message id="Msg_1" name="Запрос" />\n'
            '  <bpmn:signal id="Sig_1" name="Стоп" />\n'
            '  <bpmn:error id="Err_2" errorCode="E1" />\n'
            '  <bpmn:process id="P_1">\n'
            '    <bpmn:laneSet id="LS_1">\n'
            '      <bpmn:lane id="Lane_1" name="Оператор" />\n'
            "    </bpmn:laneSet>\n"
            "  </bpmn:process>\n"
        )
        want = {3: "Запрос", 4: "Стоп", 5: "error Err_2 (E1)", 6: "process P_1", 7: "process P_1", 8: "Оператор"}
        for number, label in want.items():
            self.assertEqual(bpmn.label_of(model, bpmn.owner(model, number)), label, number)
        self.assertEqual(bpmn.label_of(model, 0), "definitions Defs_1")

    def test_flow_to_an_unnamed_node_uses_its_kind_and_id(self):
        """Red when an unnamed end of a flow is written as an empty string."""
        model = self.write_bpmn(
            '  <bpmn:process id="P_1">\n'
            '    <bpmn:startEvent id="S_1" />\n'
            '    <bpmn:task id="T_1" name="Шаг" />\n'
            '    <bpmn:sequenceFlow id="F_1" sourceRef="S_1" targetRef="T_1" />\n'
            "  </bpmn:process>\n"
        )
        self.assertEqual(bpmn.label_of(model, bpmn.owner(model, 6)), "start event S_1 → Шаг")


class CitesAndRoot(unittest.TestCase):
    def test_cites_in_order_with_section_and_label(self):
        """Red when a cite lands in the wrong section, a closed section leaks, or a label is kept escaped."""
        html = (
            '<section id="a"><section id="b">'
            + cite("x.bpmn", 3)
            + "</section>"
            + cite("y.bpmn", 4).replace("</cite>", ' <span class="bpmn-label">A &amp; B</span></cite>')
            + "</section>"
            + cite("z.bpmn", 5)
        )
        got = bpmn.bpmn_cites(html)
        self.assertEqual([(c.path, c.line, c.section) for c in got], [("x.bpmn", 3, "b"), ("y.bpmn", 4, "a"), ("z.bpmn", 5, "page")])
        self.assertEqual([c.label for c in got], [None, "A & B", None])
        self.assertEqual(html[got[0].span[0] : got[0].span[1]], cite("x.bpmn", 3))

    def test_greater_than_inside_an_attribute_does_not_end_the_cite_tag(self):
        """Red when the start tag is cut at the first '>' of a snippet."""
        html = '<cite data-path="x.bpmn" data-line="7" data-snippet="a &gt; b > c">x:7 <code>a</code></cite>'
        self.assertEqual([c.line for c in bpmn.bpmn_cites(html)], [7])

    def test_cite_in_a_comment_is_ignored(self):
        """Red when a commented-out cite gets a label."""
        self.assertEqual(bpmn.bpmn_cites("<!-- " + cite("x.bpmn", 3) + " -->"), [])

    def test_page_root_joins_data_root_to_the_page_dir(self):
        """Red when data-root is not joined to the page dir, or an empty one counts as a root."""
        self.assertEqual(bpmn.page_root(page(root="../src"), Path("/a/b")), Path("/a/b/../src"))
        self.assertEqual(bpmn.page_root(page(root=" ../src "), Path("/a/b")), Path("/a/b/../src"))
        self.assertIsNone(bpmn.page_root(page(root=""), Path("/a/b")))
        self.assertIsNone(bpmn.page_root("<html></html>", Path("/a/b")))


class LabelCommand(Dir):
    def run_label(self, html):
        self.index.write_text(html, encoding="utf-8")
        return run(["label", str(self.index)])

    def test_label_rewrites_in_place_and_is_idempotent(self):
        """Red when a span is added twice, the rest of the page changes, or a run is not stable."""
        original = page(
            ("s1", cite("two_planes.bpmn", line_of('id="Task_svc"'))),
            ("s2", cite("two_planes.bpmn", line_of("${approved}"))),
        )
        code, out, err = self.run_label(original)
        self.assertEqual((code, out), (0, ""), err)
        first = self.index.read_bytes()
        text = first.decode("utf-8")
        self.assertEqual(text.count('class="bpmn-label"'), 2)
        self.assertIn("</code>" + SPAN % "Проверить паспорт клиента" + "</cite>", text)
        self.assertEqual(text.replace(SPAN % "Проверить паспорт клиента", "").replace(
            SPAN % "exclusive gateway Gateway_1 → Заявка одобрена, Да", ""), original)
        self.assertEqual(self.run_label(text)[0], 0)
        self.assertEqual(self.index.read_bytes(), first)

    def test_existing_label_is_replaced(self):
        """Red when a stale label is kept or a second span is added beside it."""
        stale = cite("two_planes.bpmn", line_of('id="Task_svc"')).replace(
            "</cite>", ' <span class="bpmn-label">old</span></cite>')
        self.run_label(page(("s1", stale)))
        text = self.index.read_text(encoding="utf-8")
        self.assertEqual(text.count("bpmn-label"), 1)
        self.assertIn(SPAN % "Проверить паспорт клиента", text)
        self.assertNotIn("old", text)

    def test_span_goes_directly_after_code(self):
        """Red when the span is put before </cite> instead of right after </code>."""
        marked = cite("two_planes.bpmn", line_of('id="Task_svc"')).replace("</cite>", " tail</cite>")
        self.run_label(page(("s1", marked)))
        text = self.index.read_text(encoding="utf-8")
        self.assertIn("</code>" + SPAN % "Проверить паспорт клиента" + " tail</cite>", text)

    def test_label_escapes_markup(self):
        """Red when the label is written raw, or escaped twice."""
        self.write_bpmn('  <bpmn:task id="T_1" name="Say &quot;hi&quot; &amp; &lt;go&gt;" />\n')
        self.run_label(page(("s1", cite("small.bpmn", 3))))
        text = self.index.read_text(encoding="utf-8")
        self.assertIn(SPAN % "Say &quot;hi&quot; &amp; &lt;go&gt;", text)
        self.assertEqual([c.label for c in bpmn.bpmn_cites(text)], ['Say "hi" & <go>'])

    def test_cite_on_a_blank_line_exits_1_and_names_it(self):
        """Red when a blank line gets a label, the exit stays 0, or the failure line changes shape."""
        n = blank_line()
        code, out, _ = self.run_label(page(
            ("s1", cite("two_planes.bpmn", n)),
            ("s2", cite("two_planes.bpmn", line_of('id="Task_svc"'))),
        ))
        self.assertEqual((code, out), (1, "s1 | two_planes.bpmn:%d | no element\n" % n))
        text = self.index.read_text(encoding="utf-8")
        self.assertEqual(text.count("bpmn-label"), 1)
        self.assertIn(SPAN % "Проверить паспорт клиента", text)

    def test_unreadable_bpmn_is_a_failure_line(self):
        """Red when a missing .bpmn aborts the run or is passed over silently."""
        code, out, _ = self.run_label(page(("s1", cite("gone.bpmn", 3))))
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("s1 | gone.bpmn | "), out)
        self.assertIn("gone.bpmn", out.split(" | ", 2)[2])

    def test_non_bpmn_cites_are_untouched(self):
        """Red when a .py cite or a .BPMN cite gets a span, or the page is rewritten."""
        html = page(("s1", cite("a.py", 3) + cite("two_planes.BPMN", 3)))
        code, out, _ = self.run_label(html)
        self.assertEqual((code, out), (0, ""))
        self.assertEqual(self.index.read_text(encoding="utf-8"), html)

    def test_no_root_exits_2(self):
        """Red when a page without data-root is labelled or fails with exit 1."""
        html = page(("s1", cite("two_planes.bpmn", 3))).replace(' data-root="."', "")
        code, _, err = self.run_label(html)
        self.assertEqual(code, 2)
        self.assertIn("data-root", err)
        self.assertEqual(self.index.read_text(encoding="utf-8"), html)

    def test_usage_and_unreadable_page_exit_2(self):
        """Red when a missing argument or page is not a usage error."""
        self.assertEqual(run(["label"])[0], 2)
        self.assertEqual(run(["label", str(self.tmp / "nope.html")])[0], 2)

    def test_crlf_and_bom_page_keeps_its_bytes(self):
        """Red when the rewrite normalises line ends or drops the byte order mark."""
        html = "﻿" + page(("s1", cite("two_planes.bpmn", line_of('id="Task_svc"')))).replace("\n", "\r\n")
        self.index.write_bytes(html.encode("utf-8"))
        self.assertEqual(run(["label", str(self.index)])[0], 0)
        data = self.index.read_bytes()
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(data.decode("utf-8").replace(SPAN % "Проверить паспорт клиента", ""), html)


if __name__ == "__main__":
    unittest.main()
