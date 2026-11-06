"""Tests for onboard_page.py: `onboard.py diagrams` writes each PlantUML fence of a map to its .puml
file, and the page model and the structural checks of `onboard.py page` (spec sections 9 and 10.1)."""

import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import onboard  # noqa: E402
import onboard_page  # noqa: E402

EXPLAIN = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "onboard"
PLACES = ["architecture.puml", "flow-cancel.puml", "flow-order.puml", "state.puml"]


def run(argv):
    """Run main with argv; return the exit code, stdout and stderr."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = onboard.main(argv)
    return code, out.getvalue(), err.getvalue()


def read(name):
    """The text of the fixture file `name`."""
    return (FIXTURES / name).read_text(encoding="utf-8")


PAGE = read("page.md")
MAP_PUML = read("map-puml.md")


def lines(text):
    """The classified lines of a page text."""
    return onboard_page.page_lines_of(text)


def kinds(text):
    """The kind of each line of a page text."""
    return [line.kind for line in lines(text)]


def structure(text):
    """The failures of the six structural checks on a page text, in order."""
    doc = onboard.parse_map(MAP_PUML)
    found = lines(text)
    return (onboard_page.title_lines(found) + onboard_page.answer_lines(found)
            + onboard_page.command_lines(found, doc) + onboard_page.paragraph_lines(found)
            + onboard_page.html_lines(found) + onboard_page.cite_lines(found))


def page_dir(page=PAGE, map_text=MAP_PUML, pngs=None):
    """A temporary directory holding page.md, map.md, the .puml files of the map and a PNG stub per id (or per
    id of `pngs`); it is removed when the test ends (the caller registers the cleanup through the case)."""
    folder = tempfile.mkdtemp()
    out = os.path.join(folder, "diagrams")
    os.makedirs(out)
    files = onboard_page.diagram_files(onboard.parse_map(map_text))
    Path(folder, "page.md").write_text(page, encoding="utf-8")
    Path(folder, "map.md").write_text(map_text, encoding="utf-8")
    for ident, body in files.items():
        Path(out, ident + ".puml").write_text(body, encoding="utf-8")
    for ident in (files if pngs is None else pngs):
        Path(out, ident + ".png").write_bytes(b"\x89PNG\r\n\x1a\n")
    return folder


class DiagramsCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name
        self.out = os.path.join(self.folder, "out")

    def test_writes_one_file_per_place(self):
        code, out, _ = run(["diagrams", str(FIXTURES / "map-puml.md"), "--out", self.out])
        self.assertEqual(code, 0)
        self.assertEqual(sorted(os.listdir(self.out)), PLACES)
        self.assertTrue(out.endswith("diagrams: ok 4 files\n"), out)

    def test_file_is_the_fence_wrapped(self):
        run(["diagrams", str(FIXTURES / "map-puml.md"), "--out", self.out])
        fence = re.search(r"### order:.*?```plantuml\n(.*?)\n```", read("map-puml.md"), re.DOTALL).group(1)
        written = Path(self.out, "flow-order.puml").read_text(encoding="utf-8")
        self.assertEqual(written, "@startuml\n" + fence + "\n@enduml\n")

    def test_none_found_state_writes_no_file(self):
        text = re.sub(r"## State\n.*?\n(?=## Events)", "## State\nnone found\n\n", read("map-puml.md"), flags=re.DOTALL)
        self.assertIn("## State\nnone found\n", text)
        path = os.path.join(self.folder, "map.md")
        Path(path).write_text(text, encoding="utf-8")
        code, out, _ = run(["diagrams", path, "--out", self.out])
        self.assertEqual(code, 0)
        self.assertEqual(sorted(os.listdir(self.out)), PLACES[:3])
        self.assertTrue(out.endswith("diagrams: ok 3 files\n"), out)

    def test_stale_file_is_reported_not_deleted(self):
        os.makedirs(self.out)
        old = Path(self.out, "old.puml")
        old.write_text("@startuml\n@enduml\n", encoding="utf-8")
        code, out, _ = run(["diagrams", str(FIXTURES / "map-puml.md"), "--out", self.out])
        self.assertEqual(code, 0)
        self.assertEqual(out, "diagrams: stale old.puml\ndiagrams: ok 4 files\n")
        self.assertTrue(old.exists())

    def _map_with(self, old, new):
        path = os.path.join(self.folder, "map.md")
        Path(path).write_text(read("map-puml.md").replace(old, new, 1), encoding="utf-8")
        return path

    def test_flow_named_state_keeps_both_files(self):
        path = self._map_with("### cancel: How", "### state: How")
        code, out, _ = run(["diagrams", path, "--out", self.out])
        self.assertEqual(code, 0)
        self.assertEqual(sorted(os.listdir(self.out)),
                         ["architecture.puml", "flow-order.puml", "flow-state.puml", "state.puml"])
        self.assertTrue(out.endswith("diagrams: ok 4 files\n"), out)

    def test_repeated_flow_id_is_refused(self):
        path = self._map_with("### cancel: How", "### order: How")
        code, out, _ = run(["diagrams", path, "--out", self.out])
        self.assertEqual((code, out), (1, "diagrams: flow order twice\n"))
        self.assertFalse(os.path.exists(self.out))

    def test_mermaid_fence_is_refused(self):
        code, out, _ = run(["diagrams", str(FIXTURES / "map.md"), "--out", self.out])
        self.assertEqual(code, 1)
        self.assertEqual(out, "diagrams: architecture: not plantuml\n")

    def test_unreadable_map_exits_2(self):
        missing = os.path.join(self.folder, "missing.md")
        code, out, err = run(["diagrams", missing, "--out", self.out])
        self.assertEqual((code, err), (2, ""))
        self.assertTrue(out.startswith("map: cannot read %s" % missing), out)

    def test_cli_unreadable_map_exits_2(self):
        missing = os.path.join(self.folder, "missing.md")
        done = subprocess.run([sys.executable, "-B", "scripts/onboard.py", "diagrams", missing, "--out", self.out],
                              cwd=str(EXPLAIN), capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)
        self.assertTrue(done.stdout.startswith("map: cannot read"), done.stdout)
        self.assertEqual(done.stderr, "")

    def test_cannot_write_exits_2(self):
        blocker = os.path.join(self.folder, "file")
        Path(blocker).write_text("x", encoding="utf-8")
        code, out, err = run(["diagrams", str(FIXTURES / "map-puml.md"), "--out", os.path.join(blocker, "sub")])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("diagrams: cannot write"), err)

    def test_usage_names_diagrams(self):
        code, _, err = run([])
        self.assertEqual(code, 2)
        self.assertIn("onboard.py diagrams <map.md> --out <dir>", err)


class PageModelCase(unittest.TestCase):
    def test_fence_lines_are_code(self):
        text = "```text\n# x\n| a | b |\n![c](diagrams/x.png)\n- item\n```\n"
        self.assertEqual(kinds(text), ["fence", "code", "code", "code", "code", "fence"])

    def test_crlf_and_trailing_spaces(self):
        self.assertEqual(kinds("# T\r\n\r\n![c](diagrams/x.png)  \r\n"), ["heading1", "blank", "image"])

    def test_kinds_outside_fences(self):
        text = "# T\n## H\n### Deep\n- a\n* b\n12. c\n| x |\nplain\n"
        self.assertEqual(kinds(text),
                         ["heading1", "heading2", "heading2", "list", "list", "list", "table", "text"])

    def test_fixture_page_has_no_structural_failure(self):
        self.assertEqual(structure(PAGE), [])

    def test_no_title(self):
        self.assertEqual(structure(PAGE.replace("# What does shop do", "What does shop do", 1)),
                         ["page: no title"])

    def test_second_title(self):
        text = PAGE + "\n# Another title\n\n# A third title\n"
        self.assertEqual(structure(text), ["page: second title"])

    def test_no_short_answer(self):
        text = PAGE.replace("**Short answer.**", "Short answer.", 1)
        self.assertEqual(structure(text), ["page: no short answer"])

    def test_command_outside_a_code_block(self):
        text = PAGE.replace("```sh\n./gradlew build\n```", "Type ./gradlew build to build it.", 1)
        self.assertEqual(structure(text), ["command build: not in a code block"])

    def test_command_in_prose_beside_its_block(self):
        text = PAGE.replace("Run this command to test the service.", "Run `./gradlew test` to test the service.", 1)
        self.assertEqual(structure(text), ["command test: not in a code block"])

    def make_doc(self):
        """The map with the one-word build command `make`."""
        return onboard.parse_map(MAP_PUML.replace("- build: `./gradlew build`", "- build: `make`", 1))

    def test_one_word_command_in_plain_prose_is_not_inline(self):
        text = (PAGE.replace("```sh\n./gradlew build\n```", "```sh\nmake\n```", 1)
                .replace("Run this command to build the service.", "Run this command to make the jar.", 1))
        self.assertIn("make the jar", text)
        self.assertEqual(onboard_page.command_lines(lines(text), self.make_doc()), [])

    def test_one_word_command_in_a_backtick_span_is_inline(self):
        text = (PAGE.replace("```sh\n./gradlew build\n```", "```sh\nmake\n```", 1)
                .replace("Run this command to build the service.", "Run `make` to make the jar.", 1))
        self.assertEqual(onboard_page.command_lines(lines(text), self.make_doc()),
                         ["command build: not in a code block"])

    def test_two_text_lines(self):
        text = PAGE.replace("The orders table holds the order rows. ", "The orders table holds the order rows.\nA second line. ", 1)
        self.assertNotEqual(text, PAGE)
        planted = next(line.n for line in lines(text) if line.text.startswith("A second line."))
        self.assertEqual(structure(text), ["paragraph %d: two lines" % planted])

    def test_three_text_lines_report_once(self):
        found = lines("# T\n\n**Short answer.** One.\nTwo.\nThree.\n")
        self.assertEqual(onboard_page.paragraph_lines(found), ["paragraph 4: two lines"])

    def test_html_tag_outside_code(self):
        text = PAGE.replace("The orders table holds", "The<br>orders table holds", 1)
        planted = next(line.n for line in lines(text) if "<br>" in line.text)
        self.assertEqual(structure(text), ["html %d: tag outside code" % planted])
        self.assertEqual(structure(PAGE.replace("The orders table holds", "The `<br>` orders table holds", 1)), [])

    def test_html_tag_in_a_heading_or_an_image_line(self):
        for old, new in (("## What is shop made of?", "## What is<br>shop made of?"),
                         ("# What does shop do", "# What<br>does shop do"),
                         ("![The order controller reads", "![The <b>order</b> controller reads")):
            text = PAGE.replace(old, new, 1)
            planted = next(line.n for line in lines(text) if "<" in line.text)
            self.assertEqual(structure(text), ["html %d: tag outside code" % planted], new)

    def test_table_row_with_a_port_is_not_a_cite(self):
        text = PAGE.replace("| Kafka | `orders.created` `orders.cancel` |",
                            "| Kafka | `orders.created` `orders.cancel` |\n| Kafka | kafka:9092 | events |", 1)
        self.assertIn("| Kafka | kafka:9092 | events |", text)
        self.assertEqual(structure(text), [])

    def test_indented_bullets_are_list_items(self):
        text = PAGE.replace("- The service binds order bodies as JSON with Spring.\n",
                            "- The service binds order bodies as JSON with Spring.\n"
                            "  - payload: the order body.\n  - format: JSON.\n", 1)
        self.assertIn("  - format: JSON.\n", text)
        self.assertEqual(structure(text), [])

    def test_cite_line_on_the_page(self):
        copied = "- NEW: a new order starts in NEW | src/main/java/shop/Order.java:8 | private Status status"
        text = PAGE + "\n" + copied + "\n"
        planted = next(line.n for line in lines(text) if line.text == copied)
        self.assertEqual(structure(text), ["cite %d: map line on the page" % planted])

    def test_fixture_page_lints_clean(self):
        done = subprocess.run([sys.executable, "../ste/scripts/ste_lint.py", str(FIXTURES / "page.md")],
                              cwd=str(EXPLAIN), capture_output=True, text=True, timeout=60)
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "0 errors, 0 warnings"), done.stdout)


class PageDiagramsCase(unittest.TestCase):
    def check(self, page=PAGE, map_text=MAP_PUML, pngs=None, extra=None):
        """The failures of the three diagram checks on `page`; `extra` maps a file name under diagrams/ to bytes."""
        folder = page_dir(page, map_text, pngs)
        self.addCleanup(shutil.rmtree, folder, True)
        out = os.path.join(folder, "diagrams")
        for name, body in (extra or {}).items():
            Path(out, name).write_bytes(body)
        doc = onboard.parse_map(map_text)
        found, files = lines(page), onboard_page.diagram_files(doc)
        return (onboard_page.image_lines(found, files, out) + onboard_page.puml_lines(files, out)
                + onboard_page.flow_lines(found, doc))

    def test_fixture_page_has_no_diagram_failure(self):
        self.assertEqual(self.check(), [])

    def test_missing_image_line(self):
        page = PAGE.replace("![An order starts as NEW, becomes PAID and then SHIPPED, or it becomes CANCELLED.]"
                            "(diagrams/state.png)\n", "")
        self.assertEqual(self.check(page), ["diagram state: no image line", "png state: no image line"])

    def test_image_line_twice(self):
        image = "![c](diagrams/state.png)\n"
        self.assertEqual(self.check(PAGE + "\n" + image), ["diagram state: image line twice"])

    def test_image_outside_diagrams(self):
        page = PAGE + "\n![c](pictures/x.png)\n"
        self.assertEqual(self.check(page), ["image pictures/x.png: not under diagrams/"])

    def test_image_not_in_the_map(self):
        page = PAGE + "\n![c](diagrams/flow-refund.png)\n"
        self.assertEqual(self.check(page), ["image diagrams/flow-refund.png: not in the map"])

    def test_image_that_is_not_a_png_is_not_in_the_map(self):
        page = PAGE + "\n![c](diagrams/state.svg)\n"
        self.assertEqual(self.check(page), ["image diagrams/state.svg: not in the map"])

    def test_nested_image_path_is_not_in_the_map(self):
        page = PAGE.replace("(diagrams/state.png)", "(diagrams/sub/state.png)")
        self.assertEqual(self.check(page), ["diagram state: no image line",
                                            "image diagrams/sub/state.png: not in the map",
                                            "png state: no image line"])

    def test_image_without_a_file(self):
        self.assertEqual(self.check(pngs=["architecture"]),
                         ["image diagrams/flow-order.png: no file", "image diagrams/flow-cancel.png: no file",
                          "image diagrams/state.png: no file"])

    def test_png_without_an_image_line(self):
        self.assertEqual(self.check(extra={"old.png": b"x"}), ["png old: no image line"])

    def test_caption_with_parentheses(self):
        page = PAGE.replace("![The order controller reads", "![The order controller (v2) reads")
        self.assertEqual(self.check(page), [])
        page = PAGE.replace("![An order goes through", "![the order flow (v2)](diagrams/flow-order.png)\n\n"
                            "![An order goes through", 1)
        self.assertEqual(self.check(page), ["diagram flow-order: image line twice"])

    def test_missing_diagrams_directory_is_empty(self):
        folder = page_dir()
        self.addCleanup(shutil.rmtree, folder, True)
        out = os.path.join(folder, "diagrams")
        shutil.rmtree(out)
        files = onboard_page.diagram_files(onboard.parse_map(MAP_PUML))
        self.assertEqual(onboard_page.image_lines(lines(PAGE), files, out),
                         ["image diagrams/%s.png: no file" % ident for ident in files])
        self.assertEqual(onboard_page.puml_lines(files, out), ["diagram %s: no puml" % ident for ident in files])

    def test_puml_missing(self):
        folder = page_dir()
        self.addCleanup(shutil.rmtree, folder, True)
        os.remove(os.path.join(folder, "diagrams", "flow-cancel.puml"))
        files = onboard_page.diagram_files(onboard.parse_map(MAP_PUML))
        self.assertEqual(onboard_page.puml_lines(files, os.path.join(folder, "diagrams")),
                         ["diagram flow-cancel: no puml"])

    def test_puml_differs(self):
        folder = page_dir()
        self.addCleanup(shutil.rmtree, folder, True)
        path = Path(folder, "diagrams", "state.puml")
        path.write_text(path.read_text(encoding="utf-8").replace("NEW", "NOW", 1), encoding="utf-8")
        files = onboard_page.diagram_files(onboard.parse_map(MAP_PUML))
        self.assertEqual(onboard_page.puml_lines(files, str(path.parent)), ["diagram state: differs from the map"])

    def test_puml_not_in_the_map(self):
        self.assertEqual(self.check(extra={"old.puml": b"x"}), ["puml old: not in the map"])

    def test_flow_without_a_section(self):
        page = PAGE.replace("## How is an order cancelled?", "## How is an order dropped?")
        self.assertEqual(self.check(page), ["flow cancel: no section"])

    def test_flow_without_an_image_line_has_no_flow_failure(self):
        cancel = ("![The listener keeps a shipped order and sets the status of any other order to CANCELLED.]"
                  "(diagrams/flow-cancel.png)\n")
        self.assertEqual(self.check(PAGE.replace(cancel, "")),
                         ["diagram flow-cancel: no image line", "png flow-cancel: no image line"])

    def test_image_outside_its_section(self):
        cancel = ("![The listener keeps a shipped order and sets the status of any other order to CANCELLED.]"
                  "(diagrams/flow-cancel.png)\n")
        page = PAGE.replace(cancel, "")
        page = page.replace("## What happens to a new order?\n", "## What happens to a new order?\n\n" + cancel)
        self.assertEqual(self.check(page), ["flow cancel: image outside its section"])

    def test_flow_heading_with_a_trailing_space(self):
        page = PAGE.replace("## What happens to a new order?\n", "## What happens to a new order? \n", 1)
        self.assertIn("## What happens to a new order? \n", page)
        self.assertEqual(self.check(page), [])

    def test_flows_out_of_map_order(self):
        order = PAGE.index("## What happens to a new order?")
        cancel = PAGE.index("## How is an order cancelled?")
        state = PAGE.index("## Which states does an order go through?")
        page = PAGE[:order] + PAGE[cancel:state] + PAGE[order:cancel] + PAGE[state:]
        self.assertEqual(self.check(page), ["flows: out of map order"])


class PageCase(unittest.TestCase):
    def page(self, page=PAGE, map_text=MAP_PUML, pngs=None):
        """Run `onboard.py page` on a fresh page directory; return the folder and (code, out, err)."""
        folder = page_dir(page, map_text, pngs)
        self.addCleanup(shutil.rmtree, folder, True)
        return folder, run(["page", os.path.join(folder, "page.md"), "--map", os.path.join(folder, "map.md")])

    def failures(self, page=PAGE, map_text=MAP_PUML):
        """The exit code and the output lines of the page check of `page`."""
        _, (code, out, _) = self.page(page, map_text)
        return code, out.splitlines()

    def test_fixture_page_is_ok(self):
        _, result = self.page()
        self.assertEqual(result, (0, "page: ok\n", ""))

    def test_entry_not_on_the_page(self):
        code, out = self.failures(PAGE.replace("POST /orders", "POST /ordered"))
        self.assertEqual((code, out), (1, ["entry POST /orders: not on the page", "page: 1 failures"]))

    def test_not_an_entry_point_is_not_required(self):
        page = PAGE.replace("shop-gw", "shop-gx")
        self.assertNotIn("shop-gw", page)
        map_text = MAP_PUML.replace("- cmd/shop-gw: ", "- cmd/shop-gx: ")
        self.assertEqual(self.failures(page, map_text), (0, ["page: ok"]))

    def test_event_not_on_the_page(self):
        code, out = self.failures(PAGE.replace("orders.created", "orders.made"))
        self.assertEqual((code, out), (1, ["event orders.created: not on the page", "page: 1 failures"]))

    def test_not_covered_not_on_the_page(self):
        code, out = self.failures(PAGE.replace("cmd/shop-gw", "cmd/shop-x"))
        self.assertEqual((code, out), (1, ["not covered #1: not on the page", "page: 1 failures"]))

    def test_not_covered_reason_may_be_rephrased(self):
        page = PAGE.replace("the Go gateway. The map lists", "a gateway. The page lists")
        self.assertNotEqual(page, PAGE)
        self.assertEqual(self.failures(page), (0, ["page: ok"]))

    def test_entry_name_prefix_is_not_a_false_failure(self):
        short = "- http /orders -> not traced: a short path | src/main/java/shop/OrderController.java:14 | @PostMapping\n"
        map_text = MAP_PUML.replace("- http POST /orders -> order", short + "- http POST /orders -> order", 1)
        self.assertIn(short, map_text)
        map_text = map_text.replace("/orders/{id}", "/order-by-id/{id}")
        page = PAGE.replace("/orders/{id}", "/order-by-id/{id}")
        self.assertEqual(page.count("/orders"), page.count("POST /orders"))
        self.assertEqual(self.failures(page, map_text), (0, ["page: ok"]))

    def test_name_inside_a_fence_counts(self):
        page = PAGE.replace("POST /orders", "POST /ordered") + "\n```text\nPOST /orders\n```\n"
        self.assertEqual(self.failures(page), (0, ["page: ok"]))

    def test_russian_page_passes(self):
        map_text = (MAP_PUML.replace("What happens to a new order?", "Что происходит с новым заказом?")
                    .replace("How is an order cancelled?", "Как отменяется заказ?"))
        page = (PAGE.replace("What happens to a new order?", "Что происходит с новым заказом?")
                .replace("How is an order cancelled?", "Как отменяется заказ?")
                .replace("**Short answer.**", "**Краткий ответ.**"))
        self.assertEqual(self.failures(page, map_text), (0, ["page: ok"]))

    def test_failure_count_and_order(self):
        copied = "- NEW: a new order starts in NEW | src/main/java/shop/Order.java:8 | private Status status"
        page = PAGE.replace("# What does shop do", "What does shop do", 1) + "\n" + copied + "\n"
        planted = next(line.n for line in lines(page) if line.text == copied)
        self.assertEqual(self.failures(page), (1, ["page: no title", "cite %d: map line on the page" % planted,
                                                    "page: 2 failures"]))

    def test_every_check_fails_once_in_spec_order(self):
        """One failure of each of the ten checks, so the full order of `page_lines` is the order of the spec table."""
        copied = "- NEW: a new order starts in NEW | src/main/java/shop/Order.java:8 | private Status status"
        page = (PAGE.replace("**Short answer.**", "Short answer.", 1)
                .replace("## How is an order cancelled?", "## How is an order dropped?", 1)
                .replace("POST /orders", "POST /ordered")
                .replace("Run this command to test the service.", "Run `./gradlew test` to test the service.", 1)
                + "\n# Another title\n\n![c](pictures/x.png)\n\nA first line.\nA second line.\n\n"
                "A line with<br>a tag.\n\n" + copied + "\n")
        found = lines(page)
        at = {text: next(line.n for line in found if line.text == text)
              for text in ("A second line.", "A line with<br>a tag.", copied)}
        folder = page_dir(page)
        self.addCleanup(shutil.rmtree, folder, True)
        Path(folder, "diagrams", "old.puml").write_text("@startuml\n@enduml\n", encoding="utf-8")
        code, out, err = run(["page", os.path.join(folder, "page.md"), "--map", os.path.join(folder, "map.md")])
        self.assertEqual((code, err), (1, ""))
        self.assertEqual(out.splitlines(), [
            "page: second title", "page: no short answer", "image pictures/x.png: not under diagrams/",
            "puml old: not in the map", "flow cancel: no section", "entry POST /orders: not on the page",
            "command test: not in a code block", "paragraph %d: two lines" % at["A second line."],
            "html %d: tag outside code" % at["A line with<br>a tag."],
            "cite %d: map line on the page" % at[copied], "page: 10 failures"])

    def test_unreadable_page_exits_2(self):
        folder, _ = self.page()
        missing = os.path.join(folder, "missing.md")
        code, out, err = run(["page", missing, "--map", os.path.join(folder, "map.md")])
        self.assertEqual((code, err), (2, ""))
        self.assertTrue(out.startswith("page: cannot read %s: " % missing), out)

    def test_page_that_is_not_utf8_exits_2(self):
        folder, _ = self.page()
        Path(folder, "page.md").write_bytes(b"# \xff\xfe\n")
        code, out, _ = run(["page", os.path.join(folder, "page.md"), "--map", os.path.join(folder, "map.md")])
        self.assertEqual(code, 2)
        self.assertTrue(out.startswith("page: cannot read %s: " % os.path.join(folder, "page.md")), out)

    def test_unreadable_map_exits_2(self):
        folder, _ = self.page()
        missing = os.path.join(folder, "missing.md")
        code, out, err = run(["page", os.path.join(folder, "page.md"), "--map", missing])
        self.assertEqual((code, err), (2, ""))
        self.assertTrue(out.startswith("map: cannot read %s" % missing), out)

    def test_missing_diagrams_directory(self):
        folder = page_dir()
        self.addCleanup(shutil.rmtree, folder, True)
        shutil.rmtree(os.path.join(folder, "diagrams"))
        ids = ["architecture", "flow-order", "flow-cancel", "state"]
        code, out, _ = run(["page", os.path.join(folder, "page.md"), "--map", os.path.join(folder, "map.md")])
        self.assertEqual(code, 1)
        self.assertEqual(sorted(out.splitlines()[:-1]),
                         sorted(["image diagrams/%s.png: no file" % i for i in ids]
                                + ["diagram %s: no puml" % i for i in ids]))
        self.assertEqual(out.splitlines()[-1], "page: 8 failures")

    def test_diagrams_that_is_a_file_exits_2(self):
        folder = page_dir()
        self.addCleanup(shutil.rmtree, folder, True)
        shutil.rmtree(os.path.join(folder, "diagrams"))
        Path(folder, "diagrams").write_text("x", encoding="utf-8")
        code, out, err = run(["page", os.path.join(folder, "page.md"), "--map", os.path.join(folder, "map.md")])
        self.assertEqual((code, err), (2, ""))
        self.assertTrue(out.startswith("page: cannot read %s: " % os.path.join(folder, "diagrams")), out)

    def test_puml_that_is_not_utf8_exits_2(self):
        folder = page_dir()
        self.addCleanup(shutil.rmtree, folder, True)
        bad = os.path.join(folder, "diagrams", "state.puml")
        Path(bad).write_bytes(b"@startuml\n\xff\xfe\n@enduml\n")
        code, out, err = run(["page", os.path.join(folder, "page.md"), "--map", os.path.join(folder, "map.md")])
        self.assertEqual((code, err), (2, ""))
        self.assertTrue(out.startswith("page: cannot read %s: " % bad), out)

    def test_usage_names_page(self):
        code, _, err = run([])
        self.assertEqual(code, 2)
        self.assertIn("onboard.py page <page.md> --map <map.md>", err)

    def test_page_without_map_is_the_usage(self):
        code, out, err = run(["page", "page.md"])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err, onboard.USAGE)

    def test_cli_runs_as_a_script(self):
        folder = page_dir()
        self.addCleanup(shutil.rmtree, folder, True)
        done = subprocess.run([sys.executable, "-B", "scripts/onboard.py", "page", os.path.join(folder, "page.md"),
                               "--map", os.path.join(folder, "map.md")],
                              cwd=str(EXPLAIN), capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "page: ok\n", ""))


if __name__ == "__main__":
    unittest.main()
