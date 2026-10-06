"""Tests for bpmn.py: the model with line spans, the planes subcommand and the command line
(spec section 2.1). Task 2 adds the svg cases to this file."""

import contextlib
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import bpmn  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "two_planes.bpmn"


def run(argv):
    """Run main with argv; return the exit code, stdout and stderr."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = bpmn.main(argv)
    return code, out.getvalue(), err.getvalue()


def line_of(needle):
    """The 1-based line of the first fixture line that holds `needle`."""
    for number, text in enumerate(FIXTURE.read_text(encoding="utf-8").split("\n"), 1):
        if needle in text:
            return number
    raise AssertionError("fixture lacks " + needle)


class PlanesCase(unittest.TestCase):
    def test_planes_lists_both_planes(self):
        """Red when planes drops a plane, prints the name wrong, or uses the wrong line."""
        code, out, err = run(["planes", str(FIXTURE)])
        self.assertEqual(code, 0, err)
        want = "Collaboration_1\t-\t%d\nSTAGE_A\tПервичная проверка\t%d\n" % (
            line_of("<bpmn:collaboration "),
            line_of('<bpmn:subProcess id="STAGE_A"'),
        )
        self.assertEqual(out, want)

    def test_spans_of_a_multi_line_tag(self):
        """Red when start is taken from the end of the tag or end from the start tag."""
        model = bpmn.load(FIXTURE)
        stage = model.nodes[model.by_id["STAGE_A"]]
        self.assertEqual(stage.start, line_of("<bpmn:subProcess id=\"STAGE_A\""))
        self.assertEqual(stage.end, line_of("</bpmn:subProcess>"))
        self.assertLess(stage.start, line_of('name="Первичная проверка"'))
        self.assertEqual(stage.tag, "subProcess")

    def test_self_closing_tag_starts_and_ends_on_one_line(self):
        """Red when the end handler is not called for a self-closing tag or sets another line."""
        model = bpmn.load(FIXTURE)
        bounds = [node for node in model.nodes if node.tag == "Bounds"]
        self.assertGreater(len(bounds), 20)
        for node in bounds:
            self.assertEqual(node.start, node.end)

    def test_by_id_holds_model_ids_only(self):
        """Red when by_id also indexes DI elements, or drops a nested model element."""
        model = bpmn.load(FIXTURE)
        self.assertIn("Task_svc", model.by_id)
        self.assertNotIn("Task_svc_di", model.by_id)
        self.assertNotIn("BPMNPlane_1", model.by_id)
        task = model.nodes[model.by_id["Task_svc"]]
        self.assertEqual(task.attrs["name"], "Проверить паспорт клиента")
        self.assertEqual(model.nodes[task.parent].attrs["id"], "STAGE_A")
        self.assertIn(model.by_id["Task_svc"], model.nodes[task.parent].children)

    def test_missing_file_exits_2(self):
        """Red when an unreadable file raises, or stderr does not name the file."""
        code, out, err = run(["planes", "nope.bpmn"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("nope.bpmn", err)

    def test_malformed_xml_exits_2_with_the_line(self):
        """Red when an expat error escapes main or its message loses the line number."""
        text = FIXTURE.read_text(encoding="utf-8")
        cut = "\n".join(text.split("\n")[:60]) + "\n"
        with tempfile.TemporaryDirectory() as folder:
            broken = Path(folder) / "cut.bpmn"
            broken.write_text(cut, encoding="utf-8")
            code, out, err = run(["planes", str(broken)])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("cut.bpmn", err)
        self.assertRegex(err, re.compile(r"line \d+"))

    def test_no_subcommand_exits_2_with_usage(self):
        """Red when main without arguments returns 0 or prints no usage."""
        code, out, err = run([])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("usage: bpmn.py"), err)

    def test_unknown_subcommand_exits_2_with_usage(self):
        """Red when an unknown subcommand is accepted or crashes without the usage."""
        code, out, err = run(["frobnicate", str(FIXTURE)])
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("usage: bpmn.py"), err)

    def test_planes_without_a_file_exits_2(self):
        """Red when planes accepts a missing or an extra file argument."""
        self.assertEqual(run(["planes"])[0], 2)
        self.assertEqual(run(["planes", str(FIXTURE), "extra"])[0], 2)


if __name__ == "__main__":
    unittest.main()
