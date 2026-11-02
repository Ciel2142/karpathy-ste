"""Tests for onboard_page.py: `onboard.py diagrams` writes each PlantUML fence of a map to its .puml
file (spec section 9)."""

import contextlib
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import onboard  # noqa: E402

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

    def test_mermaid_fence_is_refused(self):
        code, out, _ = run(["diagrams", str(FIXTURES / "map.md"), "--out", self.out])
        self.assertEqual(code, 1)
        self.assertEqual(out, "diagrams: architecture: not plantuml\n")

    def test_unreadable_map_exits_2(self):
        missing = os.path.join(self.folder, "missing.md")
        code, out, _ = run(["diagrams", missing, "--out", self.out])
        self.assertEqual(code, 2)
        self.assertTrue(out.startswith("map: cannot read %s" % missing), out)

    def test_usage_names_diagrams(self):
        code, _, err = run([])
        self.assertEqual(code, 2)
        self.assertIn("onboard.py diagrams <map.md> --out <dir>", err)


if __name__ == "__main__":
    unittest.main()
