"""Tests for bpmn.py: the model with line spans, the planes and svg subcommands and the command
line (spec section 2.1)."""

import contextlib
import io
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import bpmn  # noqa: E402
import bpmn_svg  # noqa: E402

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


def svg(*extra, plane="STAGE_A", path=FIXTURE):
    """Run `svg` on one plane of the fixture; return the exit code, stdout and stderr."""
    return run(["svg", str(path), "--plane", plane] + list(extra))


def group(out, ident):
    """The inner markup of the element group with data-id `ident`."""
    found = re.search(r'<g data-id="%s"[^>]*>(.*?)</g>' % re.escape(ident), out, re.S)
    if not found:
        raise AssertionError("no group " + ident)
    return found.group(1)


def plane_di(element):
    """The DI markup of the plane whose bpmnElement is `element`."""
    text = FIXTURE.read_text(encoding="utf-8")
    pattern = r'<bpmndi:BPMNPlane [^>]*bpmnElement="%s">(.*?)</bpmndi:BPMNPlane>' % element
    return re.search(pattern, text, re.S).group(1)


def without_line(after, needle):
    """Fixture text without the first line holding `needle` after the line holding `after`."""
    lines = FIXTURE.read_text(encoding="utf-8").split("\n")
    start = line_of(after)
    for number in range(start, len(lines)):
        if needle in lines[number]:
            return "\n".join(lines[:number] + lines[number + 1:])
    raise AssertionError("fixture lacks " + needle)


class SvgCase(unittest.TestCase):
    def test_root_attributes(self):
        """Red when a root attribute is missing or reordered, the title is not first, or the SVG is not well-formed."""
        code, out, err = svg()
        self.assertEqual((code, err), (0, ""))
        head = (r'<svg class="bpmn" role="img" data-ste="skip" data-plane="STAGE_A" '
                r'viewBox="[-\d. ]+" width="[\d.]+" height="[\d.]+"[^>]*>\n'
                r'<title id="[^"]+">Первичная проверка</title>\n')
        self.assertRegex(out, re.compile("^" + head))
        self.assertNotIn("<?xml", out)
        self.assertNotIn("<!DOCTYPE", out)
        ET.fromstring(out)
        code, out, err = run(["svg", str(FIXTURE)])
        self.assertEqual((code, err), (0, ""))
        self.assertIn('data-plane="Collaboration_1"', out.split("\n")[0])
        ET.fromstring(out)

    def test_view_box_is_bounds_plus_margin(self):
        """Red when the margin changes or a label or waypoint is left out of the bounding box."""
        for element in ("Collaboration_1", "STAGE_A"):
            section = plane_di(element)
            xs, ys = [], []
            for x, y, w, h in re.findall(
                    r'<dc:Bounds x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', section):
                xs += [float(x), float(x) + float(w)]
                ys += [float(y), float(y) + float(h)]
            for x, y in re.findall(r'<di:waypoint x="([\d.]+)" y="([\d.]+)"', section):
                xs.append(float(x))
                ys.append(float(y))
            w, h = max(xs) - min(xs) + 40, max(ys) - min(ys) + 40
            want = 'viewBox="%g %g %g %g" width="%g" height="%g"' % (
                min(xs) - 20, min(ys) - 20, w, h, w, h)
            self.assertIn(want, svg(plane=element)[1].split("\n")[0])

    def test_one_data_id_per_shape_and_edge(self):
        """Red when an element is drawn twice, a label carries a data-id, or a shape or edge is dropped."""
        for element in ("Collaboration_1", "STAGE_A"):
            want = re.findall(r'<bpmndi:BPMN(?:Shape|Edge) [^>]*bpmnElement="([^"]+)"', plane_di(element))
            got = re.findall(r'data-id="([^"]+)"', svg(plane=element)[1])
            self.assertEqual(sorted(got), sorted(want))

    def test_kind_tags(self):
        """Red when a task kind maps to the wrong tag or the tag is not drawn."""
        out = svg()[1]
        self.assertIn(">service</text>", group(out, "Task_svc"))
        self.assertIn(">send</text>", group(out, "Task_send"))
        self.assertIn(">receive</text>", group(out, "Task_recv"))

    def test_gateway_marker(self):
        """Red when the exclusive gateway loses its × marker."""
        self.assertIn("×", group(svg(plane="Collaboration_1")[1], "Gateway_1"))

    def test_collapsed_sub_process_has_plus_marker(self):
        """Red when isExpanded is ignored, so the collapsed sub-process has no + or the expanded one has it."""
        out = svg(plane="Collaboration_1")[1]
        self.assertIn(">+</text>", group(out, "STAGE_A"))
        self.assertNotIn(">+</text>", group(out, "EventSub_1"))

    def test_event_sub_process_is_dotted(self):
        """Red when triggeredByEvent is ignored or every sub-process border is dotted."""
        out = svg(plane="Collaboration_1")[1]
        self.assertIn("stroke-dasharray", re.search(r"<rect[^>]*>", group(out, "EventSub_1")).group(0))
        self.assertNotIn("stroke-dasharray", re.search(r"<rect[^>]*>", group(out, "STAGE_A")).group(0))

    def test_default_flow_has_its_slash(self):
        """Red when the default flow loses its slash, the slash sits far from the source, or other flows get one."""
        out = svg(plane="Collaboration_1")[1]
        edge = re.search(r'bpmnElement="Flow_default">\s*<di:waypoint x="([\d.]+)" y="([\d.]+)"',
                         plane_di("Collaboration_1"))
        x0, y0 = float(edge.group(1)), float(edge.group(2))
        lines = re.findall(r'<line[^>]* x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"',
                           group(out, "Flow_default"))
        self.assertEqual(len(lines), 1)
        for x, y in (lines[0][:2], lines[0][2:]):
            self.assertLess(abs(float(x) - x0) + abs(float(y) - y0), 30)
        self.assertNotIn("<line", group(out, "Flow_yes"))
        self.assertNotIn("<line", group(out, "Flow_no"))

    def test_non_interrupting_boundary_is_dashed(self):
        """Red when cancelActivity="false" is ignored or every event is dashed."""
        out = svg()[1]
        self.assertIn("stroke-dasharray", re.search(r"<circle[^>]*>", group(out, "Timer_1")).group(0))
        self.assertNotIn("stroke-dasharray", group(out, "StageStart_1"))

    def test_highlight_marks_exactly_those_ids(self):
        """Red when hl lands on a wrong element, is missed, or an id off the plane passes in silence."""
        code, out, err = svg("--highlight", "Task_svc,Gateway_1")
        self.assertEqual(code, 0)
        self.assertEqual(re.findall(r'<g data-id="([^"]+)" class="hl"', out), ["Task_svc"])
        self.assertEqual(out.count('class="hl"'), 1)
        self.assertIn("skipped Gateway_1: ", err)
        out = svg("--highlight", "Task_svc,Gateway_1", plane="Collaboration_1")[1]
        self.assertEqual(re.findall(r'<g data-id="([^"]+)" class="hl"', out), ["Gateway_1"])
        self.assertEqual(out.count('class="hl"'), 1)

    def test_no_text_under_14(self):
        """Red when any text has no font-size or one under 14."""
        for element in ("Collaboration_1", "STAGE_A"):
            out = svg(plane=element)[1]
            texts = re.findall(r"<text[^>]*>", out)
            self.assertGreater(len(texts), 5)
            for tag in texts:
                self.assertRegex(tag, r'font-size="\d+"')
            for size in re.findall(r'font-size="([\d.]+)"', out):
                self.assertGreaterEqual(float(size), 14)

    def test_outside_label_is_centred_on_its_di_bounds(self):
        """Red when an outside label hangs from the top of its DI label bounds instead of sitting centred on them."""
        root = ET.fromstring(FIXTURE.read_text(encoding="utf-8"))
        di = "{http://www.omg.org/spec/BPMN/20100524/DI}"
        checked = 0
        for plane in root.iter(di + "BPMNPlane"):
            out = svg(plane=plane.get("bpmnElement"))[1]
            for item in plane:
                bounds = item.find("%sBPMNLabel/{http://www.omg.org/spec/DD/20100524/DC}Bounds" % di)
                found = re.search(r'<text [^>]*data-for="%s">(.*?)</text>' % item.get("bpmnElement"), out)
                if bounds is None or found is None:
                    continue
                spans = re.findall(r'<tspan x="([\d.-]+)" y="([\d.-]+)">', found.group(1))
                x, y, w, h = (float(bounds.get(k)) for k in ("x", "y", "width", "height"))
                middle = float(spans[0][1]) - bpmn_svg.FONT + len(spans) * bpmn_svg.LINE / 2
                self.assertAlmostEqual(middle, y + h / 2, delta=0.01, msg=item.get("bpmnElement"))
                self.assertAlmostEqual(float(spans[0][0]), x + w / 2, delta=0.01)
                checked += 1
        self.assertGreater(checked, 5)

    def test_long_name_wraps_and_ends_in_ellipsis(self):
        """Red when wrap does not break the name, does not cut it, or the full name has no title."""
        body = group(svg()[1], "Task_svc")
        lines = re.findall(r"<tspan[^>]*>([^<]*)</tspan>", body)
        self.assertGreater(len(lines), 1)
        self.assertTrue(lines[-1].endswith("…"), lines)
        self.assertRegex(body, r'^<title id="[^"]+">Проверить паспорт клиента</title>')

    def test_wrap_breaks_greedily_and_cuts_at_the_height(self):
        """Red when wrap breaks inside a word, packs too much on a line, or keeps lines the height cannot hold."""
        per_line = 12 * 14 * 0.55
        self.assertEqual(bpmn_svg.wrap("Проверить паспорт клиента", per_line, 60), (
            ["Проверить", "паспорт", "клиента"], False))
        self.assertEqual(bpmn_svg.wrap("Проверить паспорт клиента", per_line, 40), (
            ["Проверить", "паспорт…"], True))
        self.assertEqual(bpmn_svg.wrap("Да  и\nнет", per_line, 20), (["Да и нет"], False))

    def test_name_with_entities_is_escaped_once(self):
        """Red when the quote is escaped twice or not at all, or the line break survives."""
        out = svg()[1]
        body = group(out, "Task_send")
        self.assertNotIn("&amp;quot;", out)
        self.assertNotIn("&#10;", out)
        title = re.search(r"<title[^>]*>([^<]*)</title>", body)
        shown = title.group(1) if title else " ".join(re.findall(r"<tspan[^>]*>([^<]*)</tspan>", body))
        self.assertEqual(shown, "Отправить &quot;отчёт&quot; клиенту")

    def test_prefix_on_every_marker_and_title_id(self):
        """Red when an id or a url() reference lacks the prefix, or the plane id is not the default prefix."""
        for extra, prefix in ((["--prefix", "p1"], "p1-"), ([], "STAGE_A-")):
            out = svg(*extra)[1]
            ids = re.findall(r' id="([^"]+)"', out) + re.findall(r"url\(#([^)]+)\)", out)
            self.assertGreater(len(ids), 3)
            for ident in ids:
                self.assertTrue(ident.startswith(prefix), ident)
            self.assertIn('<marker id="%sarrow"' % prefix, out)

    def test_unknown_plane_exits_2_and_lists_planes(self):
        """Red when an unknown plane renders, exits another code, or stderr lacks the plane list."""
        code, out, err = svg(plane="NOPE")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("Collaboration_1\t-\t%d\n" % line_of("<bpmn:collaboration "), err)
        self.assertIn("STAGE_A\tПервичная проверка\t%d\n" % line_of('id="STAGE_A"'), err)

    def test_output_is_byte_equal_on_a_second_run(self):
        """Red when the output depends on set or dict order, or on time."""
        for element in ("Collaboration_1", "STAGE_A"):
            first = svg("--highlight", "Task_svc,Flow_a2,Gateway_1,Flow_yes", plane=element)[1]
            second = svg("--highlight", "Flow_yes,Gateway_1,Flow_a2,Task_svc", plane=element)[1]
            self.assertIn("<svg", first)
            self.assertEqual(first, second)

    def test_shape_without_bounds_is_skipped_with_a_warning(self):
        """Red when a shape without bounds crashes, is drawn, fails the exit code, or passes in silence."""
        text = without_line('bpmnElement="Task_recv">', "<dc:Bounds")
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "copy.bpmn"
            copy.write_text(text, encoding="utf-8")
            code, out, err = svg(path=copy)
        self.assertEqual(code, 0)
        self.assertNotIn('data-id="Task_recv"', out)
        self.assertIn('data-id="Flow_a2"', out)
        self.assertIn("bpmn.py: %s: skipped Task_recv: " % copy, err)

    def test_edge_with_one_waypoint_is_skipped_with_a_warning(self):
        """Red when an edge with one waypoint is drawn or passes in silence."""
        text = without_line('bpmnElement="Flow_a2">', "<di:waypoint")
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "copy.bpmn"
            copy.write_text(text, encoding="utf-8")
            code, out, err = svg(path=copy)
        self.assertEqual(code, 0)
        self.assertNotIn('data-id="Flow_a2"', out)
        self.assertIn("bpmn.py: %s: skipped Flow_a2: " % copy, err)

    def test_svg_option_errors_exit_2(self):
        """Red when svg accepts no file, an unknown option, an option without value, or a bad prefix."""
        self.assertEqual(run(["svg"])[0], 2)
        self.assertEqual(run(["svg", str(FIXTURE), "--frob", "x"])[0], 2)
        self.assertEqual(run(["svg", str(FIXTURE), "--plane"])[0], 2)
        self.assertEqual(run(["svg", str(FIXTURE), "--prefix", 'a"b'])[0], 2)


if __name__ == "__main__":
    unittest.main()
