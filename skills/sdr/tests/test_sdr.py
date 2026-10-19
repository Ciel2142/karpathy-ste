"""Tests for sdr.py: the record reader, the skeleton command and the header and section rules
(spec sections 5, 6 and 9)."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import sdr  # noqa: E402

RECORDS = Path(__file__).resolve().parent / "fixtures" / "records"
TREE = RECORDS / "tree"  # the root that every fixture cite resolves under
PAGES = Path(__file__).resolve().parent / "fixtures" / "pages"

VALID = "valid-intake.md"
QUESTION = "How do we notify the end user of each warrant action?"
FRAME_SECTIONS = sdr.SECTIONS[:7]  # the sections that stage `frame` reaches
FENCED = """### opt-a: first
```mermaid
flowchart LR
  a --> b
## Fake
### opt-z: x
- fit FR-1: meets — r
```
- changes: x
"""


def temp_dir() -> Path:
    """A fresh temp dir that the module removes when its tests are done."""
    path = Path(tempfile.mkdtemp(prefix="sdr-test-"))
    unittest.addModuleCleanup(shutil.rmtree, str(path), True)
    return path


def fixture_text(name: str, stage: str | None = None, edits: tuple[tuple[str, str], ...] = ()) -> str:
    """The text of a fixture record; `stage` replaces line 2, each (old, new) edit must match exactly once."""
    text = (RECORDS / name).read_text(encoding="utf-8")
    if stage is not None:
        lines = text.split("\n")
        lines[1] = "stage: " + stage
        text = "\n".join(lines)
    for old, new in edits:
        if text.count(old) != 1:
            raise AssertionError("%r occurs %d times, not once" % (old, text.count(old)))
        text = text.replace(old, new)
    return text


def findings(text: str) -> list[str]:
    return sdr.check_record(sdr.parse_record(text), str(TREE))


def record_dir(text: str, root: Path | None = None) -> Path:
    """A temp dir holding `text` as sdr.md; with `root`, line 3 becomes `root: <root>`."""
    if root is not None:
        lines = text.split("\n")
        lines[2] = "root: %s" % root
        text = "\n".join(lines)
    path = temp_dir()
    (path / "sdr.md").write_text(text, encoding="utf-8")
    return path


def run_sdr(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(SCRIPTS / "sdr.py"), *args],
                          capture_output=True, text=True, timeout=60)


def skeleton(question: str = QUESTION, root: Path = TREE, code: tuple[Path, ...] = (TREE / "orchestrator",),
             name: str = "out") -> tuple[subprocess.CompletedProcess, Path]:
    """Run `skeleton` into <temp>/<name>/sdr; return the process and the sdr dir."""
    target = temp_dir() / name / "sdr"
    args = ["skeleton", str(target), "--question", question, "--root", str(root)]
    for directory in code:
        args += ["--code", str(directory)]
    return run_sdr(*args), target


class SkeletonCase(unittest.TestCase):
    def test_skeleton_writes_intake_record(self):
        run, target = skeleton("  How to   notify? ")
        self.assertEqual((run.returncode, run.stderr), (0, ""))
        self.assertEqual(run.stdout, "sdr: wrote %s\n" % (target / "sdr.md"))
        lines = (target / "sdr.md").read_text(encoding="utf-8").split("\n")
        self.assertEqual(lines[:4], ["# SDR: How to notify?", "stage: intake", "root: %s" % TREE,
                                     "code: %s" % (TREE / "orchestrator")])
        headings = [number for number, line in enumerate(lines) if line.startswith("## ")]
        self.assertEqual([lines[number] for number in headings], ["## " + title for title in sdr.SECTIONS])
        self.assertEqual([lines[number + 2] for number in headings], ["pending"] * len(sdr.SECTIONS))
        self.assertTrue((target / "sdr.md").read_text(encoding="utf-8").endswith("pending\n"))

    def test_skeleton_without_code_writes_code_none(self):
        run, target = skeleton(code=())
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual((target / "sdr.md").read_text(encoding="utf-8").split("\n")[3], "code: none")

    def test_skeleton_record_passes_check(self):
        _, target = skeleton(code=(TREE / "orchestrator", TREE / "executor"))
        run = run_sdr("check", str(target))
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "sdr: ok\n", ""))

    def test_skeleton_refuses_to_overwrite(self):
        _, target = skeleton()
        before = (target / "sdr.md").read_bytes()
        again = run_sdr("skeleton", str(target), "--question", "Another one?", "--root", str(TREE))
        self.assertEqual(again.returncode, 2)
        self.assertIn("exists", again.stderr)
        self.assertEqual((target / "sdr.md").read_bytes(), before)

    def test_skeleton_rejects_code_dir_outside_root(self):
        outside = temp_dir()
        run, target = skeleton(code=(outside,))
        self.assertEqual(run.returncode, 2)
        self.assertIn("is not under", run.stderr)
        self.assertFalse((target / "sdr.md").exists())

    def test_skeleton_expands_home(self):
        home = temp_dir()
        (home / "a b").mkdir()
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            run = run_sdr("skeleton", str(home / "sdr"), "--question", "Q?", "--root", "~/a b")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual((home / "sdr" / "sdr.md").read_text(encoding="utf-8").split("\n")[2],
                         "root: %s/a b" % home)

    def test_skeleton_usage_and_unreadable_dirs(self):
        target = str(temp_dir() / "sdr")
        for args, wanted in (
            (("--root", str(TREE)), "usage: sdr.py"),  # no --question
            (("--question", " \t ", "--root", str(TREE)), "usage: sdr.py"),
            (("--question", "Q?", "--root", str(TREE / "missing")), "sdr: cannot read root %s" % (TREE / "missing")),
            (("--question", "Q?", "--root", str(TREE), "--code", str(TREE / "nope")),
             "sdr: cannot read code dir %s" % (TREE / "nope")),
        ):
            with self.subTest(args=args):
                run = run_sdr("skeleton", target, *args)
                self.assertEqual(run.returncode, 2)
                self.assertTrue(run.stderr.startswith(wanted), run.stderr)
                self.assertFalse(os.path.exists(os.path.join(target, "sdr.md")))


class HeaderAndSectionCase(unittest.TestCase):
    def test_valid_intake_record_is_ok(self):
        self.assertEqual(findings(fixture_text(VALID)), [])

    def test_explore_stage_is_ok(self):
        self.assertEqual(findings(fixture_text(VALID, stage="explore")), [])

    def test_bad_header_fixture(self):
        self.assertEqual(findings(fixture_text("bad-header.md")), ["header: unknown stage drafting"])

    def test_bad_section_fixture(self):
        self.assertEqual(findings(fixture_text("bad-section.md")), ["section: missing Not covered"])

    def test_header_lines(self):
        first = "# SDR: " + QUESTION
        for old, new, wanted in (
            (first, "# SDR:", 'header: line 1 is not "# SDR: <question>"'),
            (first, "# SDR: ", 'header: line 1 is not "# SDR: <question>"'),
            (first, "SDR: " + QUESTION, 'header: line 1 is not "# SDR: <question>"'),
            ("stage: intake", "stage intake", 'header: line 2 is not "stage: <name>"'),
            ("stage: intake", "stage: ", 'header: line 2 is not "stage: <name>"'),
            ("stage: intake", "stage: intake now", 'header: line 2 is not "stage: <name>"'),
            ("stage: intake", "stage: Intake", "header: unknown stage Intake"),
            ("root: /fixture-root", "root: relative", 'header: line 3 is not "root: <absolute path>"'),
            ("root: /fixture-root", "root:", 'header: line 3 is not "root: <absolute path>"'),
            ("code: /fixture-root/orchestrator; /fixture-root/executor", "code: orchestrator",
             'header: line 4 is not "code: <absolute dirs>" or "code: none"'),
            ("code: /fixture-root/orchestrator; /fixture-root/executor", "code: /fixture-root/a; b",
             'header: line 4 is not "code: <absolute dirs>" or "code: none"'),
            ("code: /fixture-root/orchestrator; /fixture-root/executor", "code:",
             'header: line 4 is not "code: <absolute dirs>" or "code: none"'),
        ):
            with self.subTest(new=new):
                self.assertEqual(findings(fixture_text(VALID, edits=((old, new),))), [wanted])

    def test_header_accepts_code_none_and_one_dir(self):
        for new in ("code: none", "code: /fixture-root/orchestrator"):
            with self.subTest(new=new):
                text = fixture_text(VALID, edits=(("code: /fixture-root/orchestrator; /fixture-root/executor", new),))
                self.assertEqual(findings(text), [])

    def test_section_order_twice_unknown(self):
        moved = (("## Constraints\n\npending\n\n## Non-goals\n", "## Non-goals\n\npending\n\n## Constraints\n"),)
        again = (("## Not covered\n\npending\n", "## Not covered\n\npending\n\n## Problem\n\npending\n"),)
        extra = (("## Not covered\n\npending\n", "## Not covered\n\npending\n\n## Notes\n\npending\n"),)
        self.assertEqual(findings(fixture_text(VALID, edits=moved)), ["section: Constraints out of order"])
        self.assertEqual(findings(fixture_text(VALID, edits=again)), ["section: Problem twice"])
        self.assertEqual(findings(fixture_text(VALID, edits=extra)), ["section: unknown Notes"])

    def test_missing_sections_come_before_record_order_lines(self):
        text = fixture_text(VALID, edits=(("\n## Context\n\npending\n", ""), ("\n## Options\n\npending\n", ""),
                                          ("## Not covered\n\npending\n", "## Not covered\n\npending\n\n## Notes\n")))
        self.assertEqual(findings(text), ["section: missing Context", "section: missing Options",
                                          "section: unknown Notes"])

    def test_unreached_section_must_be_pending(self):
        text = fixture_text(VALID, edits=(("## Problem\n\npending\n", "## Problem\n\nBecause.\n"),))
        self.assertEqual(findings(text), ["section: Problem not pending at stage intake"])

    def test_reached_section_pending_or_empty(self):
        self.assertEqual(findings(fixture_text(VALID, stage="frame")),
                         ["section: %s pending at stage frame" % title for title in FRAME_SECTIONS])
        text = fixture_text(VALID, stage="frame", edits=(("## Non-goals\n\npending\n", "## Non-goals\n"),))
        wanted = ["section: %s pending at stage frame" % title for title in FRAME_SECTIONS]
        wanted[FRAME_SECTIONS.index("Non-goals")] = "section: Non-goals empty, write none"
        self.assertEqual(findings(text), wanted)

    def test_reached_section_with_content_or_none_is_quiet(self):
        text = fixture_text(VALID, stage="frame", edits=tuple(
            ("## %s\n\npending\n" % title, "## %s\n\n%s\n" % (title, "none" if title == "Non-goals" else "A line."))
            for title in FRAME_SECTIONS))
        self.assertEqual(findings(text), [])

    def test_unreached_section_with_blocks_is_not_pending(self):
        text = fixture_text(VALID, edits=(("## Options\n\npending\n", "## Options\n\n### opt-a: x\npending\n"),))
        self.assertEqual(findings(text), ["section: Options not pending at stage intake"])

    def test_options_shortlist_blocks_are_not_a_section_finding_at_frame(self):
        blocks = "".join("### opt-%s: name\npending\n" % letter for letter in "abc")
        text = fixture_text(VALID, stage="frame", edits=(("## Options\n\npending\n", "## Options\n\n" + blocks),))
        self.assertNotIn("section: Options pending at stage frame", findings(text))


class ReaderCase(unittest.TestCase):
    def test_fenced_lines_are_not_structure(self):
        record = sdr.parse_record(fixture_text(VALID, edits=(("## Options\n\npending\n", "## Options\n\n" + FENCED),)))
        self.assertEqual([section.title for section in record.sections], list(sdr.SECTIONS))
        options = record.section("Options")
        self.assertEqual([block.heading for block in options.blocks], ["opt-a: first"])
        block = options.blocks[0]
        self.assertEqual(options.diagrams, [])
        self.assertEqual(len(block.diagrams), 1)
        for fragment in ("## Fake", "### opt-z: x", "- fit FR-1: meets — r"):
            self.assertIn(fragment, block.diagrams[0].text)
        scopes = list(record.sections) + options.blocks
        texts = [text for scope in scopes for _, text in scope.lines]
        self.assertEqual([text for text in texts if "Fake" in text or "opt-z" in text or "fit FR-1" in text], [])
        self.assertEqual(block.lines, [(block.line + 8, "- changes: x")])

    def test_lines_and_blocks_follow_the_record(self):
        text = "\n".join(["# SDR: q", "stage: intake", "root: /r", "code: none", "", "## Options", "", "intro line",
                          "### opt-a: first", "", "one", "two", "### opt-b: second", "three", "## Decision", "x"])
        options = sdr.parse_record(text).section("Options")
        self.assertEqual((options.title, options.line), ("Options", 6))
        self.assertEqual(options.lines, [(8, "intro line")])
        self.assertEqual([(block.heading, block.line, block.lines) for block in options.blocks],
                         [("opt-a: first", 9, [(11, "one"), (12, "two")]), ("opt-b: second", 13, [(14, "three")])])

    def test_mermaid_fence_becomes_a_diagram_and_other_fences_are_dropped(self):
        text = "\n".join(["# SDR: q", "stage: intake", "root: /r", "code: none", "## Options",
                          "```text", "plain", "```", "```mermaid", "flowchart LR", "  a --> b", "```", "after"])
        options = sdr.parse_record(text).section("Options")
        self.assertEqual(options.lines, [(13, "after")])
        self.assertEqual(len(options.diagrams), 1)
        diagram = options.diagrams[0]
        self.assertEqual((diagram.line, diagram.kind, diagram.nodes), (9, "flowchart", ["a", "b"]))

    def test_unclosed_fence_closes_at_the_end(self):
        text = "\n".join(["# SDR: q", "stage: intake", "root: /r", "code: none", "## Options",
                          "```mermaid", "flowchart LR", "  a --> b"])
        options = sdr.parse_record(text).section("Options")
        self.assertEqual(options.lines, [])
        self.assertEqual([diagram.nodes for diagram in options.diagrams], [["a", "b"]])

    def test_header_fields(self):
        record = sdr.parse_record(fixture_text(VALID))
        dirs = ["/fixture-root/orchestrator", "/fixture-root/executor"]
        self.assertEqual((record.question, record.stage, record.root, record.code),
                         (QUESTION, "intake", "/fixture-root", dirs))
        self.assertEqual(len(record.header), 4)
        none = sdr.parse_record("# SDR: q\nstage: intake\nroot: /r\ncode: none\n")
        self.assertEqual((none.code, none.sections), ([], []))

    def test_short_file_pads_the_header(self):
        record = sdr.parse_record("# SDR: q\n")
        self.assertEqual(record.header, ["# SDR: q", "", "", ""])
        self.assertEqual((record.question, record.stage, record.root, record.code), ("q", None, None, None))

    def test_bom_and_crlf_read_as_lf(self):
        text = "﻿" + fixture_text(VALID).replace("\n", "\r\n")
        self.assertEqual(sdr.parse_record(text).stage, "intake")
        self.assertEqual(findings(text), [])

    def test_reached_compares_stage_positions(self):
        self.assertTrue(sdr.reached("frame", "frame"))
        self.assertTrue(sdr.reached("done", "decide"))
        self.assertFalse(sdr.reached("explore", "frame"))


class CliCase(unittest.TestCase):
    def test_cli_exit_codes(self):
        run = run_sdr()
        self.assertEqual(run.returncode, 2)
        self.assertTrue(run.stderr.startswith("usage: sdr.py"), run.stderr)
        run = run_sdr("render")
        self.assertEqual(run.returncode, 2)
        self.assertTrue(run.stderr.startswith("usage: sdr.py"), run.stderr)
        run = run_sdr("check", str(temp_dir()), "--root", str(TREE))
        self.assertEqual(run.returncode, 2)
        self.assertIn("sdr: cannot read", run.stderr)
        run = run_sdr("check", str(record_dir(fixture_text("bad-header.md"))), "--root", str(TREE))
        self.assertEqual(run.returncode, 1)
        self.assertEqual(run.stdout.splitlines(), ["header: unknown stage drafting", "sdr: 1 findings"])
        run = run_sdr("check", str(record_dir(fixture_text(VALID))), "--root", str(TREE / "missing"))
        self.assertEqual(run.returncode, 2)
        self.assertIn("sdr: cannot read root", run.stderr)

    def test_check_needs_a_root(self):
        target = record_dir(fixture_text(VALID, edits=(("root: /fixture-root", "root: relative"),)))
        run = run_sdr("check", str(target))
        self.assertEqual(run.returncode, 2)
        self.assertTrue(run.stderr.startswith("sdr: no root"), run.stderr)

    def test_check_uses_the_root_line_without_a_root_flag(self):
        run = run_sdr("check", str(record_dir(fixture_text(VALID), root=TREE)))
        self.assertEqual((run.returncode, run.stdout), (0, "sdr: ok\n"))

    def test_check_rejects_a_record_that_is_not_utf8(self):
        target = temp_dir()
        (target / "sdr.md").write_bytes(b"# SDR: \xff\xfe\n")
        run = run_sdr("check", str(target), "--root", str(TREE))
        self.assertEqual(run.returncode, 2)
        self.assertTrue(run.stderr.startswith("sdr: cannot read %s" % (target / "sdr.md")), run.stderr)

    def test_runs_through_a_symlinked_skill_dir(self):
        link = temp_dir() / "sdr"
        os.symlink(SCRIPTS.parent, link)
        target = record_dir(fixture_text(VALID))
        run = subprocess.run([sys.executable, "-B", str(link / "scripts" / "sdr.py"), "check", str(target),
                              "--root", str(TREE)], capture_output=True, text=True, timeout=60)
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "sdr: ok\n", ""))


if __name__ == "__main__":
    unittest.main()
