"""Tests for sdr.py: the record reader, the skeleton command, the header and section rules, the cited lines,
the option blocks, the consilium, the decision, the matrix and the page check (spec sections 5, 6, 8 and 9)."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import sdr  # noqa: E402

RECORDS = Path(__file__).resolve().parent / "fixtures" / "records"
TREE = RECORDS / "tree"  # the root that every fixture cite resolves under
PAGES = Path(__file__).resolve().parent / "fixtures" / "pages"
EXPLAIN = Path(__file__).resolve().parent.parent.parent / "explain"  # the sibling skill, never changed here
PAGE_TEMPLATE = EXPLAIN / "templates" / "page.html"
VERIFY = EXPLAIN / "scripts" / "verify.sh"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")  # the path that verify.sh uses

VALID = "valid-intake.md"
FRAME = "valid-frame.md"
OPTIONS = "valid-options.md"
CONSILIUM = "valid-consilium.md"
DECIDE = "valid-decide.md"
CODE_GOOD = "facts/code-good.md"
FACTS = RECORDS / "facts"
CONTEXT_1 = ("- One source system maps many claims to one warrant | orchestrator/ClaimRouter.java:8 "
             "| Many claims, one warrant")
CONTEXT_2 = ("- Each execution event carries the warrant total and no claim id | executor/WarrantEvents.java:6 "
             "| carries the warrant total and no claim id")
CONTEXT_3 = ("- Notification per aggregate is a known pattern "
             "| https://martinfowler.com/articles/201701-event-driven.html | Event-Carried State Transfer")
FR_2 = ("- FR-2: A notification for a warrant with many claims names the claims behind the action | source: code "
        "| orchestrator/ClaimRouter.java:8 | Many claims, one warrant")
NFR_1 = "- NFR-1: The notification arrives soon after the action | target: within 60 s | source: user"
CONSTRAINT = "- The executor keeps publishing the same events to its other consumers | source: user"
NON_GOAL = "- Choosing the channel (mail, SMS or push) that carries the notification"
ROUTE_HEADING = "### route: How does a claim reach a warrant?"
ROUTER_FACT = ("- router: ClaimRouter holds the claim to warrant map | orchestrator/ClaimRouter.java:7 "
               "| public class ClaimRouter")
LOOKUP_FACT = ("- lookup: warrantOf reads the map by claim id | orchestrator/ClaimRouter.java:15 "
               "| public Optional<String> warrantOf")
WARRANT_FACT = "- warrant: an unknown claim gives no warrant | orchestrator/ClaimRouter.java:16 | Optional.ofNullable"
FACTS_FIRST = "- Many claims can map to one warrant | orchestrator/ClaimRouter.java:8 | Many claims, one warrant"
SHAPE_FACT = ("- Java service that maps each claim to its warrant | orchestrator/ClaimRouter.java:7 "
              "| public class ClaimRouter")
UNKNOWN_LINE = "- Where the map is filled is not in this directory"
OPT_C_HEADING = "### opt-c: Orchestrator keeps a claim ledger"
FIT_FORM = 'option opt-a: fit line #%d is not "fit <id>: <mark> — <reason>"'
OPTION_FINDING = 'option #3: heading is not "opt-<letter>: <name>"'
FEWER_THAN_THREE = "section: Options has 2 options, fewer than 3"
CHAIN = "flowchart LR\n" + "".join("  n%d --> n%d\n" % (number, number + 1) for number in range(1, 26))  # 26 nodes
QUESTION = "How do we notify the end user of each warrant action?"
FRAME_SECTIONS = sdr.SECTIONS[:7]  # the sections that stage `frame` reaches
CORRECTION_FORM = ('consilium sceptic: correction #%d is not "correction opt-<x> <id>: <old> -> <new> — '
                   'accepted|rejected: <reason>"')
DISSENT_FORM = 'decision: dissent #%d is not "dissent: <role> preferred opt-<y>: <reason>"'
NO_DISSENT_SCEPTIC = "decision: no dissent for sceptic"
WHY_NFR_1 = "decision: why does not name NFR-1 (opt-b fails it, opt-a meets it)"
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


def frame_findings(*edits: tuple[str, str]) -> list[str]:
    """The findings of valid-frame.md with the edits applied."""
    return findings(fixture_text(FRAME, edits=edits))


def facts_findings(*edits: tuple[str, str]) -> list[str]:
    """The findings of facts/code-good.md with the edits applied."""
    return sdr.check_facts(fixture_text(CODE_GOOD, edits=edits), str(TREE))


def option_body(ident: str, name: str = OPTIONS) -> str:
    """The text under the heading of option `ident` in a fixture, up to the next heading."""
    text = fixture_text(name)
    start = text.index("\n", text.index("### %s:" % ident)) + 1
    return text[start : start + re.search(r"^#{2,3} ", text[start:], re.M).start()]


def option_findings(ident: str, change: Callable[[str], str], stage: str = "options") -> list[str]:
    """The findings of valid-options.md when `change` rewrites the body of option `ident`."""
    body = option_body(ident)
    return findings(fixture_text(OPTIONS, stage=stage, edits=((body, change(body)),)))


def option_line(ident: str, prefix: str) -> str:
    """The line of option `ident` in valid-options.md that starts with `prefix`."""
    return next(line for line in option_body(ident).splitlines() if line.startswith(prefix))


def role_body(role: str) -> str:
    """The text under the heading of role `role` in valid-consilium.md, up to the next heading."""
    text = fixture_text(CONSILIUM)
    start = text.index("\n", text.index("### %s\n" % role)) + 1
    return text[start : start + re.search(r"^#{2,3} ", text[start:], re.M).start()]


def role_block(role: str) -> str:
    return "### %s\n%s" % (role, role_body(role))


def role_line(role: str, prefix: str) -> str:
    """The line of role `role` in valid-consilium.md that starts with `prefix`."""
    return next(line for line in role_body(role).splitlines() if line.startswith(prefix))


def role_findings(role: str, change: Callable[[str], str], stage: str = "consilium") -> list[str]:
    """The findings of valid-consilium.md when `change` rewrites the body of role `role`."""
    body = role_body(role)
    return findings(fixture_text(CONSILIUM, stage=stage, edits=((body, change(body)),)))


def decide_line(prefix: str) -> str:
    """The line of the Decision section of valid-decide.md that starts with `prefix`."""
    return next(line for line in fixture_text(DECIDE).splitlines() if line.startswith(prefix))


def decide_findings(*edits: tuple[str, str]) -> list[str]:
    """The findings of valid-decide.md with the edits applied."""
    return findings(fixture_text(DECIDE, edits=edits))


def decision_section(name: str = DECIDE) -> str:
    """The body of the Decision section of a fixture: the text from `## Decision` to `## Open questions`."""
    text = fixture_text(name)
    return text[text.index("## Decision") : text.index("## Open questions")]


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


def template_page(out: Path) -> Path:
    """Write explain's page.html to out/index.html with the compare section before the provenance section and
    its nav link before the Provenance link (each anchor must occur once); the rung meta stays `page`."""
    section = (PAGES / "compare-section.html").read_text(encoding="utf-8")
    edits = (
        ('<section id="provenance-facet">', section.rstrip("\n") + '\n\n<section id="provenance-facet">'),
        ('<a href="#provenance-facet">Provenance</a>',
         '<a href="#compare">Compare</a>\n  <a href="#provenance-facet">Provenance</a>'),
    )
    page = PAGE_TEMPLATE.read_text(encoding="utf-8")
    for anchor, text in edits:
        if page.count(anchor) != 1:
            raise AssertionError("%r occurs %d times in page.html, not once" % (anchor, page.count(anchor)))
        page = page.replace(anchor, text)
    path = Path(out) / "index.html"
    path.write_text(page, encoding="utf-8")
    return path


def page_dir(text: str | None = None, page: str | None = "before.html") -> Path:
    """A record dir with `root: <TREE>` (valid-decide unless `text` is given) and, unless `page` is None, the
    page fixture `page` as index.html."""
    target = record_dir(fixture_text(DECIDE) if text is None else text, root=TREE)
    if page is not None:
        (target / "index.html").write_bytes((PAGES / page).read_bytes())
    return target


def set_stage(target: Path, stage: str) -> None:
    """Rewrite line 2 of <target>/sdr.md."""
    path = target / "sdr.md"
    lines = path.read_text(encoding="utf-8").split("\n")
    lines[1] = "stage: " + stage
    path.write_text("\n".join(lines), encoding="utf-8")


def filled_page(target: Path) -> str:
    """Run `matrix` on <target> (it must succeed) and return the text of its index.html."""
    run = run_sdr("matrix", str(target))
    if (run.returncode, run.stdout, run.stderr) != (0, "sdr: ok\n", ""):
        raise AssertionError("matrix: %r %r %r" % (run.returncode, run.stdout, run.stderr))
    return (target / "index.html").read_text(encoding="utf-8")


class MatrixCells(HTMLParser):
    """The matrix of a page as data: `rows` (a list of cells for each <tr>) and `styles` (the text of each <style>).
    A cell is {"tag", "class", "text", "marks"}; a mark is [role, aria-label, text] of a <span> in the cell."""

    def __init__(self, page: str) -> None:
        super().__init__()
        self.rows: list[list[dict]] = []
        self.styles: list[str] = []
        self._cell = self._mark = None
        self._in_style = False
        self.feed(page)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.rows.append([])
        elif tag in ("th", "td"):
            self._cell = {"tag": tag, "class": attrs.get("class"), "text": "", "marks": []}
            self.rows[-1].append(self._cell)
        elif tag == "span" and self._cell is not None:
            self._mark = [attrs.get("role"), attrs.get("aria-label"), ""]
            self._cell["marks"].append(self._mark)
        elif tag == "style":
            self.styles.append("")
            self._in_style = True

    def handle_endtag(self, tag):
        if tag in ("th", "td"):
            self._cell = None
        elif tag == "span":
            self._mark = None
        elif tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_style:
            self.styles[-1] += data
        elif self._mark is not None:
            self._mark[2] += data
        elif self._cell is not None:
            self._cell["text"] += data


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
        shortlist = "".join("### opt-%s: name\npending\n" % letter for letter in "abc")  # Options needs three options
        text = fixture_text(VALID, stage="frame", edits=tuple(
            ("## %s\n\npending\n" % title, "## %s\n\n%s\n" % (
                title, "none" if title == "Non-goals" else shortlist if title == "Options" else "A line."))
            for title in FRAME_SECTIONS))
        self.assertEqual(findings(text), [])

    def test_unreached_section_with_blocks_is_not_pending(self):
        text = fixture_text(VALID, edits=(("## Options\n\npending\n", "## Options\n\n### opt-a: x\npending\n"),))
        self.assertEqual(findings(text), ["section: Options not pending at stage intake"])

    def test_options_shortlist_blocks_are_not_a_section_finding_at_frame(self):
        blocks = "".join("### opt-%s: name\npending\n" % letter for letter in "abc")
        text = fixture_text(VALID, stage="frame", edits=(("## Options\n\npending\n", "## Options\n\n" + blocks),))
        self.assertNotIn("section: Options pending at stage frame", findings(text))


class CitedLineCase(unittest.TestCase):
    def test_valid_frame_record_is_ok(self):
        self.assertEqual(findings(fixture_text(FRAME)), [])

    def test_bad_cite_fixture(self):
        self.assertEqual(findings(fixture_text("bad-cite.md")), ["cite Context#2: snippet not found on that line"])

    def test_bad_req_fixture(self):
        self.assertEqual(findings(fixture_text("bad-req.md")), ["req NFR-1: no target"])

    def test_bad_constraint_fixture(self):
        self.assertEqual(findings(fixture_text("bad-constraint.md")), ["constraint #1: unknown source boss"])

    def test_context_line_without_cite(self):
        self.assertEqual(frame_findings((CONTEXT_1, "- One source system maps many claims to one warrant")),
                         ["cite Context#1: no cite"])

    def test_url_cite_form(self):
        thirteen = " ".join("w%d" % number for number in range(13))
        url = CONTEXT_3.rsplit(" | ", 2)[1]
        self.assertEqual(frame_findings((CONTEXT_3, "- Notification per aggregate | %s | %s" % (url, thirteen))),
                         ["cite Context#3: snippet has 13 words (max 12)"])
        twelve = " ".join(thirteen.split()[:12])
        self.assertEqual(frame_findings((CONTEXT_3, "- Notification per aggregate | %s | %s" % (url, twelve))), [])
        self.assertEqual(frame_findings((CONTEXT_3, "- Notification per aggregate | ftp://x | snippet")),
                         ["cite Context#3: no cite"])

    def test_cite_form_cases(self):
        for cite in ("orchestrator/ClaimRouter.java:0 | Many claims", "orchestrator/ClaimRouter.java | Many claims",
                     "orchestrator/ClaimRouter.java:8 |  ", "orchestrator/ClaimRouter.java:8 | a | b"):
            with self.subTest(cite=cite):
                self.assertEqual(frame_findings((CONTEXT_1, "- One source system | " + cite)),
                                 ["cite Context#1: no cite"])

    def test_path_cite_problems_come_from_cite_check(self):
        lines = len((TREE / "orchestrator" / "ClaimRouter.java").read_text(encoding="utf-8").splitlines())
        self.assertEqual(frame_findings((CONTEXT_1, CONTEXT_1.replace(".java:8", ".java:999"))),
                         ["cite Context#1: line out of range (file has %d lines)" % lines])
        missing = frame_findings((CONTEXT_1, CONTEXT_1.replace("ClaimRouter.java:8", "Missing.java:8")))
        self.assertEqual(len(missing), 1)
        self.assertTrue(missing[0].startswith("cite Context#1: file missing: "), missing)

    def test_requirement_ids(self):
        self.assertEqual(frame_findings(("- FR-2:", "- FR-3:")), ["req FR-3: expected FR-2"])
        wanted = ["req FR#2: no id", "req FR-3: expected FR-2"]
        self.assertEqual(frame_findings(("- FR-2: ", "- ")), wanted)
        self.assertEqual(frame_findings(("- FR-2:", "- NFR-9:")), wanted)

    def test_nfr_ids_run_in_their_own_sequence(self):
        self.assertEqual(frame_findings(("- NFR-2:", "- NFR-3:")), ["req NFR-3: expected NFR-2"])
        self.assertEqual(frame_findings(("- NFR-1:", "- FR-1:")), ["req NFR#1: no id", "req NFR-2: expected NFR-1"])
        self.assertEqual(frame_findings(("- FR-1:", "- FR-01:")), ["req FR-01: expected FR-1"])

    def test_requirement_text_and_target(self):
        self.assertEqual(frame_findings(("- FR-1: The end user is told about every block, unblock and confiscation |",
                                         "- FR-1: |")), ["req FR-1: no text"])
        for old, new, wanted in (
            ("target: within 60 s | ", "", ["req NFR-1: no target"]),
            ("target: within 60 s", "target:", ["req NFR-1: no target"]),
            ("target: within 60 s", "target:  ", ["req NFR-1: no target"]),
            ("target: within 60 s | source: user", "source: user | target: within 60 s",
             ["req NFR-1: no target", "req NFR-1: source user takes no cite"]),
        ):
            with self.subTest(new=new):
                self.assertEqual(frame_findings((old, new)), wanted)

    def test_requirement_sources(self):
        fr_1 = "- FR-1: The end user is told about every block, unblock and confiscation | source: user"
        cite = "orchestrator/ClaimRouter.java:8 | Many claims, one warrant"
        url = "https://martinfowler.com/articles/201701-event-driven.html | Event-Carried State Transfer"
        for old, new, wanted in (
            (fr_1, fr_1.replace(" | source: user", ""), ["req FR-1: no source"]),
            (fr_1, fr_1.replace("source: user", "source:"), ["req FR-1: no source"]),
            (fr_1, fr_1.replace("source: user", "source: boss"), ["req FR-1: unknown source boss"]),
            (FR_2, FR_2.replace(" | " + cite, ""), ["req FR-2: source code needs a <path>:<line> cite"]),
            (FR_2, FR_2.replace(cite, url), ["req FR-2: source code needs a <path>:<line> cite"]),
            (FR_2, FR_2.replace(cite, cite + " | extra"), ["req FR-2: source code needs a <path>:<line> cite"]),
            (FR_2, FR_2.replace("source: code", "source: web"), ["req FR-2: source web needs a URL cite"]),
            (fr_1, fr_1 + " | " + cite, ["req FR-1: source user takes no cite"]),
            (fr_1, fr_1.replace("source: user", "source: consilium boss"),
             ["req FR-1: unknown source consilium boss"]),
            (fr_1, fr_1.replace("source: user", "source: consilium"), ["req FR-1: unknown source consilium"]),
            (fr_1, fr_1.replace("source: user", "source: consilium sceptic | extra"),
             ["req FR-1: source consilium sceptic takes no cite"]),
            (fr_1, fr_1.replace("source: user", "source: consilium sceptic"), []),
            (fr_1, fr_1.replace("source: user", "source: consilium architect"), []),
            (fr_1, fr_1.replace("source: user", "source: assumption"), []),
        ):
            with self.subTest(new=new):
                self.assertEqual(frame_findings((old, new)), wanted)

    def test_requirement_and_constraint_cites_are_checked(self):
        bad = "Many claims, one warrant", "One claim, many warrants"
        self.assertEqual(frame_findings((FR_2, FR_2.replace(*bad))),
                         ["cite Functional requirements#2: snippet not found on that line"])
        nfr_2 = [line for line in fixture_text(FRAME).splitlines() if line.startswith("- NFR-2:")][0]
        long = " ".join("w%d" % number for number in range(13))
        self.assertEqual(frame_findings((nfr_2, nfr_2.replace("transactional outbox", long))),
                         ["cite Non-functional requirements#2: snippet has 13 words (max 12)"])
        far = "source: code | orchestrator/ClaimRouter.java:99 | x"
        self.assertEqual(frame_findings((CONSTRAINT, CONSTRAINT.replace("source: user", far))),
                         ["cite Constraints#1: line out of range (file has 18 lines)"])

    def test_constraint_sources(self):
        cite = "orchestrator/ClaimRouter.java:8 | Many claims, one warrant"
        for new, wanted in (
            (CONSTRAINT.replace(" | source: user", ""), ["constraint #1: no source"]),
            (CONSTRAINT + " | " + cite, ["constraint #1: source user takes no cite"]),
            (CONSTRAINT.replace("source: user", "source: code"),
             ["constraint #1: source code needs a <path>:<line> cite"]),
            (CONSTRAINT.replace("source: user", "source: web | " + cite),
             ["constraint #1: source web needs a URL cite"]),
            (CONSTRAINT.replace("source: user", "source: code | " + cite), []),
            (CONSTRAINT + "\n" + CONSTRAINT.replace("source: user", "source: boss"),
             ["constraint #2: unknown source boss"]),
        ):
            with self.subTest(new=new):
                self.assertEqual(frame_findings((CONSTRAINT, new)), wanted)

    def test_nfr_target_unknown_is_valid(self):
        self.assertEqual(frame_findings((NFR_1, NFR_1.replace("within 60 s", "unknown"))), [])

    def test_sections_marked_none_pass(self):
        self.assertEqual(frame_findings(("\n".join((CONTEXT_1, CONTEXT_2, CONTEXT_3)), "none"),
                                        (CONSTRAINT, "none"), (NON_GOAL, "none")), [])

    def test_requirement_sections_marked_none_pass(self):
        text = fixture_text(FRAME)
        for title, kind in (("Functional requirements", "FR"), ("Non-functional requirements", "NFR")):
            body = "\n".join(line for line in text.splitlines() if line.startswith("- %s-" % kind))
            with self.subTest(title=title):
                self.assertEqual(frame_findings((body, "none")), [])

    def test_cite_rules_wait_for_stage_frame_and_for_content(self):
        self.assertEqual(findings(fixture_text(FRAME, stage="explore", edits=((CONTEXT_1, "- no cite"),))),
                         ["section: %s not pending at stage explore" % title for title in FRAME_SECTIONS])
        context = "\n".join((CONTEXT_1, CONTEXT_2, CONTEXT_3))
        self.assertEqual(frame_findings((context, "pending")), ["section: Context pending at stage frame"])
        self.assertEqual(frame_findings((context, "- no cite"), (CONSTRAINT, "")),
                         ["section: Constraints empty, write none", "cite Context#1: no cite"])

    def test_requirements_returns_ids_in_order(self):
        found = sdr.requirements(sdr.parse_record(fixture_text(FRAME)))
        self.assertEqual([requirement.ident for requirement in found], ["FR-1", "FR-2", "FR-3", "NFR-1", "NFR-2"])
        self.assertEqual(found[0].text, "The end user is told about every block, unblock and confiscation")
        self.assertEqual(found[1].text,
                         "A notification for a warrant with many claims names the claims behind the action")
        self.assertEqual(found[4].text, "A failed notification never blocks or undoes an action")
        self.assertEqual([(requirement.n, requirement.line) for requirement in found[:2]], [(1, 18), (2, 19)])

    def test_requirements_skips_malformed_lines(self):
        text = fixture_text(FRAME, edits=((FR_2.split(" |")[0], "- FR-2:"), ("- FR-3:", "- NFR-3:")))
        found = sdr.requirements(sdr.parse_record(text))
        self.assertEqual([requirement.ident for requirement in found], ["FR-1", "NFR-1", "NFR-2"])
        self.assertEqual(sdr.requirements(sdr.parse_record(fixture_text(VALID))), [])

    def test_parse_fact(self):
        self.assertEqual(sdr.parse_fact(3, 12, "A fact | a/b.java:5 | the snippet"),
                         sdr.Fact(3, 12, "A fact", "a/b.java:5", "the snippet"))
        self.assertEqual(sdr.parse_fact(1, 4, "A fact | https://x.example/p | the snippet"),
                         sdr.Fact(1, 4, "A fact", "https://x.example/p", "the snippet"))
        for text in ("A fact", "A fact | a/b.java:5", "A fact | a/b.java:5 | ", "A fact | a/b.java:0 | s",
                     "A fact | a/b.java | s", "A fact | ftp://x | s", "A fact | a/b.java:5 | s | t"):
            with self.subTest(text=text):
                self.assertEqual(sdr.parse_fact(1, 1, text)[3:], (None, None))
        self.assertEqual(sdr.parse_fact(1, 1, " A fact  | a/b:5 | s").fact, "A fact")

    def test_cite_problems(self):
        self.assertEqual(sdr.cite_problems("https://x.example", "one two", str(TREE)), [])
        self.assertEqual(sdr.cite_problems("orchestrator/ClaimRouter.java:8", "Many claims", str(TREE)), [])
        self.assertEqual(sdr.cite_problems("orchestrator/ClaimRouter.java:8", "nothing like it", str(TREE)),
                         ["snippet not found on that line"])


class OptionCase(unittest.TestCase):
    def test_valid_frame_shortlist_is_ok(self):
        self.assertEqual(findings(fixture_text(FRAME)), [])

    def test_valid_options_record_is_ok(self):
        self.assertEqual(findings(fixture_text(OPTIONS)), [])

    def test_bad_option_fixture(self):
        self.assertEqual(findings(fixture_text("bad-option.md")), ["option opt-b: missing risks"])

    def test_bad_fit_fixture(self):
        self.assertEqual(findings(fixture_text("bad-fit.md")), ["fit opt-c/NFR-1: missing"])

    def test_shortlist_rules(self):
        block = OPT_C_HEADING + "\n\npending\n"
        self.assertEqual(frame_findings((block + "\n", "")), [FEWER_THAN_THREE])
        self.assertEqual(frame_findings((block, OPT_C_HEADING + "\n\ntext\n")),
                         ["option opt-c: not pending at stage frame"])
        self.assertEqual(frame_findings((block, OPT_C_HEADING + "\n")), ["option opt-c: not pending at stage frame"])
        diagram = "```mermaid\nflowchart LR\n  a --> b\n```\n"
        self.assertEqual(frame_findings((block, block + diagram)), ["option opt-c: not pending at stage frame"])
        self.assertEqual(frame_findings((OPT_C_HEADING, "### Option C")), [FEWER_THAN_THREE, OPTION_FINDING])
        self.assertEqual(findings(fixture_text(OPTIONS, edits=((OPT_C_HEADING, "### Option C"),))),
                         [FEWER_THAN_THREE, OPTION_FINDING])  # the body of a block without an id is not read

    def test_shortlist_heading_form(self):
        for heading in ("opt-ab: name", "opt-A: name", "opt-c:  name", "opt-c:", "opt-c name", "opt-1: name"):
            with self.subTest(heading=heading):
                self.assertEqual(frame_findings((OPT_C_HEADING, "### " + heading)), [FEWER_THAN_THREE, OPTION_FINDING])

    def test_options_section_none_has_no_options(self):
        text = fixture_text(FRAME)
        start, end = text.index("### opt-a:"), text.index("## Consilium")
        self.assertEqual(findings(text[:start] + "none\n\n" + text[end:]),
                         ["section: Options has 0 options, fewer than 3"])

    def test_options_shortlist_at_stage_options_and_before(self):
        self.assertEqual(findings(fixture_text(OPTIONS, stage="frame")),
                         ["option opt-%s: not pending at stage frame" % letter for letter in "abc"])
        explore = findings(fixture_text(OPTIONS, stage="explore"))
        self.assertEqual([line for line in explore if line.startswith(("option", "fit"))], [])

    def test_option_rules_wait_for_the_section(self):
        text = fixture_text(OPTIONS)
        head, tail = text[: text.index("## Options")], text[text.index("## Consilium") :]
        self.assertEqual(findings(head + "## Options\n\npending\n\n" + tail),
                         ["section: Options pending at stage options"])
        self.assertEqual(findings(head + tail), ["section: missing Options"])

    def test_option_rules_run_at_later_stages(self):
        self.assertIn("option opt-b: missing risks", findings(fixture_text("bad-option.md", stage="consilium")))

    def test_duplicate_option_id(self):
        block = OPT_C_HEADING + "\n\npending\n"
        for body in ("pending", "text"):  # the body of the repeat is not read
            with self.subTest(body=body):
                self.assertEqual(frame_findings((block, block + "\n### opt-b: x\n\n%s\n" % body)),
                                 ["option opt-b: twice"])
        text = fixture_text(OPTIONS, edits=((OPT_C_HEADING, "### opt-b: again\n\ntext\n\n" + OPT_C_HEADING),))
        self.assertEqual(findings(text), ["option opt-b: twice"])

    def test_pending_option_at_stage_options(self):
        self.assertEqual(option_findings("opt-b", lambda body: "\npending\n\n"),
                         ["option opt-b: pending at stage options"])

    def test_option_keys(self):
        pros, cons = option_line("opt-a", "- pros:"), option_line("opt-a", "- cons:")
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(pros, pros + "\n" + pros)),
                         ["option opt-a: pros twice"])
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(cons, "- cons:")),
                         ["option opt-a: cons empty"])
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(pros, "- pros: ; ;")),
                         ["option opt-a: pros empty"])
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(pros, pros + "\n- pros:")),
                         ["option opt-a: pros twice", "option opt-a: pros empty"])
        for key in sdr.OPTION_KEYS:
            line = option_line("opt-a", "- %s:" % key)
            with self.subTest(key=key):
                self.assertEqual(option_findings("opt-a", lambda body: body.replace(line + "\n", "")),
                                 ["option opt-a: missing %s" % key])
                self.assertEqual(option_findings("opt-a", lambda body: body.replace(line, "- %s:  " % key)),
                                 ["option opt-a: %s empty" % key])

    def test_option_keys_are_reported_in_key_order(self):
        lines = [option_line("opt-a", "- %s:" % key) + "\n" for key in ("risks", "changes")]
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(lines[0], "").replace(lines[1], "")),
                         ["option opt-a: missing changes", "option opt-a: missing risks"])

    def test_option_lead_paragraph(self):
        lead = option_body("opt-a").split("\n")[1]
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(lead + "\n", "")),
                         ["option opt-a: no lead paragraph"])

    def test_option_diagram(self):
        def fence(body: str) -> str:
            start = body.index("```mermaid")
            return body[start : body.index("```\n", start + 3) + 4]

        def swap(new: str) -> Callable[[str], str]:
            return lambda body: body.replace(fence(body), new)

        self.assertEqual(option_findings("opt-a", swap("")), ["option opt-a: no Mermaid flowchart"])
        two = lambda body: body.replace(fence(body), fence(body) + "\n" + fence(body))  # noqa: E731
        self.assertEqual(option_findings("opt-a", two), ["option opt-a: 2 Mermaid blocks, more than 1"])
        for header in ("stateDiagram-v2", "graph LR"):
            with self.subTest(header=header):
                self.assertEqual(option_findings("opt-a", lambda body: body.replace("flowchart LR", header)),
                                 ["option opt-a: diagram is not a flowchart"])
        self.assertEqual(option_findings("opt-a", swap("```mermaid\n" + CHAIN + "```\n")),
                         ["option opt-a: diagram has 26 nodes, more than 25"])
        chain_25 = CHAIN.replace("  n25 --> n26\n", "")
        self.assertEqual(option_findings("opt-a", swap("```mermaid\n" + chain_25 + "```\n")), [])

    def test_fenced_option_lines_are_not_read(self):
        inside = "  notifier --> user\n"
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(
            inside, inside + "- pros: again\n- fit FR-9: meets - r\n- fit nothing\n")), [])

    def test_fit_lines(self):
        fr_1, nfr_2 = option_line("opt-a", "- fit FR-1:"), option_line("opt-a", "- fit NFR-2:")
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(
            nfr_2, nfr_2 + "\n- fit FR-9: meets — r")), ["fit opt-a/FR-9: not a requirement"])
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(fr_1, fr_1.replace("meets", "good", 1))),
                         ["fit opt-a/FR-1: mark good is not meets, partial or fails"])
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(fr_1, fr_1 + "\n" + fr_1)),
                         ["fit opt-a/FR-1: twice"])
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(nfr_2, nfr_2 + "\n- fit nothing")),
                         [FIT_FORM % 6])

    def test_fit_lines_are_reported_in_rule_order(self):
        fr_1, nfr_2 = option_line("opt-a", "- fit FR-1:"), option_line("opt-a", "- fit NFR-2:")
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(
            nfr_2, nfr_2 + "\n- fit FR-9: meets — r\n- fit nothing\n- fit FR-1:meets — r")),
            [FIT_FORM % 7, FIT_FORM % 8, "fit opt-a/FR-9: not a requirement"])
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(fr_1, "- fit FR-1: good - r")),
                         ["fit opt-a/FR-1: mark good is not meets, partial or fails",
                          'fit opt-a/FR-1: no " — <reason>" after the mark'])
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(fr_1, fr_1 + "\n" + fr_1 + "\n" + fr_1)),
                         ["fit opt-a/FR-1: twice", "fit opt-a/FR-1: twice"])
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(nfr_2 + "\n", "").replace(fr_1 + "\n", "")),
                         ["fit opt-a/FR-1: missing", "fit opt-a/NFR-2: missing"])
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(fr_1, "- fit FR-1:meets — r")),
                         [FIT_FORM % 1, "fit opt-a/FR-1: missing"])

    def test_fit_reason_is_required(self):
        fr_1 = option_line("opt-a", "- fit FR-1:")
        for line in ("- fit FR-1: meets", "- fit FR-1: meets —", "- fit FR-1: meets —reason",
                     "- fit FR-1: meets  — r"):
            with self.subTest(line=line):
                self.assertEqual(option_findings("opt-a", lambda body: body.replace(fr_1, line)),
                                 ['fit opt-a/FR-1: no " — <reason>" after the mark'])

    def test_fit_hyphen_separator_named(self):
        fr_1 = option_line("opt-a", "- fit FR-1:")
        self.assertEqual(option_findings("opt-a", lambda body: body.replace(fr_1, "- fit FR-1: meets - reason")),
                         ['fit opt-a/FR-1: no " — <reason>" after the mark'])

    def test_options_returns_marks(self):
        found = sdr.options(sdr.parse_record(fixture_text(OPTIONS)))
        self.assertEqual([option.ident for option in found], ["opt-a", "opt-b", "opt-c"])
        self.assertEqual(found[1].fits["NFR-1"], "fails")
        self.assertEqual([option.name for option in found], ["Notify per warrant total",
                                                              "Executor emits one event per claim action",
                                                              "Orchestrator keeps a claim ledger"])
        self.assertEqual({option.ident: list(option.fits.values()) for option in found}, {
            "opt-a": ["meets", "fails", "meets", "meets", "partial"],
            "opt-b": ["meets", "meets", "meets", "fails", "meets"],
            "opt-c": ["meets", "meets", "partial", "partial", "meets"],
        })
        self.assertEqual(list(found[0].fits), ["FR-1", "FR-2", "FR-3", "NFR-1", "NFR-2"])
        self.assertEqual(found[0].block.heading, "opt-a: Notify per warrant total")

    def test_options_keeps_the_first_block_and_the_first_valid_mark(self):
        fr_1 = option_line("opt-a", "- fit FR-1:")
        text = fixture_text(OPTIONS, edits=(
            (fr_1, "- fit FR-1: good — r\n- fit FR-1: fails — r\n" + fr_1),
            (OPT_C_HEADING, "### opt-a: again\n\ntext\n\n### Option D\n\n" + OPT_C_HEADING)))
        found = sdr.options(sdr.parse_record(text))
        self.assertEqual([(option.ident, option.name) for option in found], [
            ("opt-a", "Notify per warrant total"), ("opt-b", "Executor emits one event per claim action"),
            ("opt-c", "Orchestrator keeps a claim ledger")])
        self.assertEqual(found[0].fits["FR-1"], "fails")
        self.assertEqual(sdr.options(sdr.parse_record(fixture_text(VALID))), [])


class ConsiliumCase(unittest.TestCase):
    def test_valid_consilium_record_is_ok(self):
        self.assertEqual(findings(fixture_text(CONSILIUM)), [])

    def test_bad_consilium_fixture(self):
        self.assertEqual(findings(fixture_text("bad-consilium.md")),
                         ["consilium sceptic: preferred opt-z is not an option"])

    def test_consilium_roles(self):
        operator, sceptic = role_block("operator"), role_block("sceptic")
        critic = "### critic\n\n- preferred: opt-a\n\n"
        self.assertEqual(findings(fixture_text(CONSILIUM, edits=((operator, ""),))), ["consilium operator: missing"])
        self.assertEqual(findings(fixture_text(CONSILIUM, edits=((operator + sceptic, sceptic + operator),))),
                         ["consilium operator: out of order"])
        self.assertEqual(findings(fixture_text(CONSILIUM, edits=((sceptic, critic + sceptic),))),
                         ["consilium critic: unknown role"])
        self.assertEqual(findings(fixture_text(CONSILIUM, edits=((operator, role_block("architect") + operator),))),
                         ["consilium architect: twice"])

    def test_consilium_missing_roles_come_in_role_order(self):
        edits = ((role_block("operator"), ""), (role_block("architect"), ""))
        self.assertEqual(findings(fixture_text(CONSILIUM, edits=edits)),
                         ["consilium architect: missing", "consilium operator: missing"])

    def test_consilium_block_lines_come_before_the_missing_lines(self):
        sceptic, operator = role_block("sceptic"), role_block("operator")
        edits = ((operator + sceptic, "### critic\n\n- verdict: x\n\n" + sceptic + role_block("architect")),)
        self.assertEqual(findings(fixture_text(CONSILIUM, edits=edits)),
                         ["consilium critic: unknown role", "consilium architect: twice",
                          "consilium operator: missing"])

    def test_the_body_of_an_unknown_or_repeated_role_block_is_not_read(self):
        sceptic = role_block("sceptic")
        extra = "### critic\n\n- preferred: opt-z\n- correction nothing\n\n"
        again = "### sceptic\n\n- preferred: opt-z\n- correction nothing\n\n"
        self.assertEqual(findings(fixture_text(CONSILIUM, edits=((sceptic, sceptic + extra + again),))),
                         ["consilium critic: unknown role", "consilium sceptic: twice"])

    def test_consilium_none_has_no_exemption(self):
        text = fixture_text(CONSILIUM)
        start, end = text.index("### architect"), text.index("## Decision")
        self.assertEqual(findings(text[:start] + "none\n\n" + text[end:]),
                         ["consilium %s: missing" % role for role in sdr.ROLES])

    def test_consilium_waits_for_the_section_and_the_stage(self):
        text = fixture_text(CONSILIUM)
        start, end = text.index("## Consilium"), text.index("## Decision")
        self.assertEqual(findings(text[:start] + "## Consilium\n\npending\n\n" + text[end:]),
                         ["section: Consilium pending at stage consilium"])
        self.assertEqual(findings(text[:start] + text[end:]), ["section: missing Consilium"])
        self.assertEqual(findings(text[:start] + "## Consilium\n\n" + text[end:]),
                         ["section: Consilium empty, write none"])
        bad = fixture_text("bad-consilium.md", stage="options")
        self.assertEqual(findings(bad), ["section: Consilium not pending at stage options"])
        self.assertIn("consilium sceptic: preferred opt-z is not an option",
                      findings(fixture_text("bad-consilium.md", stage="review")))

    def test_consilium_preferred_and_verdict(self):
        preferred, verdict = role_line("operator", "- preferred:"), role_line("operator", "- verdict:")
        self.assertEqual(role_findings("operator", lambda body: body.replace(preferred + "\n", "")),
                         ["consilium operator: no preferred"])
        self.assertEqual(role_findings("operator", lambda body: body.replace(preferred, "- preferred:  ")),
                         ["consilium operator: no preferred"])
        self.assertEqual(role_findings("operator", lambda body: body.replace(preferred, preferred + "\n" + preferred)),
                         ["consilium operator: preferred twice"])
        self.assertEqual(role_findings("operator", lambda body: body.replace(verdict + "\n", "")),
                         ["consilium operator: no verdict"])
        self.assertEqual(role_findings("operator", lambda body: body.replace(verdict, "- verdict:   ")),
                         ["consilium operator: no verdict"])
        self.assertEqual(role_findings("operator", lambda body: "\n"), [
            "consilium operator: no preferred", "consilium operator: no verdict"])

    def test_consilium_preferred_must_be_an_option(self):
        preferred = role_line("operator", "- preferred:")
        for value in ("opt-z", "opt-d", "banana", "opt-b because"):
            with self.subTest(value=value):
                self.assertEqual(
                    role_findings("operator", lambda body: body.replace(preferred, "- preferred: " + value)),
                    ["consilium operator: preferred %s is not an option" % value])
        self.assertEqual(role_findings("operator", lambda body: body.replace(preferred, "- preferred: opt-c")), [])

    def test_consilium_findings_come_in_record_order(self):
        operator, sceptic = role_block("operator"), role_block("sceptic")
        swapped = fixture_text(CONSILIUM, edits=((operator + sceptic, sceptic + operator),)).replace(
            "- preferred: opt-b\n- verdict: opt-b is the only", "- verdict: opt-b is the only", 1)
        self.assertEqual(findings(swapped),
                         ["consilium operator: out of order", "consilium operator: no preferred"])

    def test_corrections(self):
        accepted = role_line("sceptic", "- correction opt-c")

        def change(new: str) -> list[str]:
            return role_findings("sceptic", lambda body: body.replace(accepted, new))

        self.assertEqual(change("- correction opt-c FR-3 meets partial"), [CORRECTION_FORM % 1])
        self.assertEqual(change(accepted.replace("opt-c", "opt-z")),
                         ["consilium sceptic: correction #1 names opt-z, not an option"])
        self.assertEqual(change(accepted.replace("FR-3", "FR-9")),
                         ["consilium sceptic: correction #1 names FR-9, not a requirement"])
        self.assertEqual(change(accepted.replace("-> partial", "-> good")),
                         ["consilium sceptic: correction #1 mark good is not meets, partial or fails"])
        self.assertEqual(change(accepted.replace("-> partial", "-> fails")),
                         ["consilium sceptic: correction #1 accepted, but fit opt-c/FR-3 is partial, not fails"])
        self.assertEqual(change(accepted.replace("-> partial", "-> fails").replace("accepted", "rejected")), [])
        self.assertEqual(change(accepted), [])

    def test_correction_form(self):
        accepted = role_line("sceptic", "- correction opt-c")
        bad = (accepted.replace(" — ", " - "), accepted.replace("accepted:", "approved:"),
               accepted[: accepted.index("accepted:") + len("accepted:")], accepted.replace("meets ->", "->"),
               accepted.replace("opt-c FR-3:", "opt-c FR-3"), "- correction")
        for line in bad:
            with self.subTest(line=line):
                self.assertEqual(role_findings("sceptic", lambda body: body.replace(accepted, line)),
                                 [CORRECTION_FORM % 1])
        # a line that does not start with "- correction" is not a correction
        self.assertEqual(role_findings("sceptic", lambda body: body.replace(
            accepted, accepted.replace("- correction", "- correct"))), [])

    def test_corrections_are_numbered_in_order(self):
        accepted, rejected = role_line("sceptic", "- correction opt-c"), role_line("sceptic", "- correction opt-b")
        self.assertEqual(role_findings("sceptic", lambda body: body.replace(
            accepted, "- correction x").replace(rejected, rejected.replace("opt-b", "opt-z"))),
            [CORRECTION_FORM % 1, "consilium sceptic: correction #2 names opt-z, not an option"])

    def test_correction_faults_are_reported_in_rule_order(self):
        accepted = role_line("sceptic", "- correction opt-c")
        line = accepted.replace("opt-c", "opt-z").replace("FR-3", "FR-9").replace("meets -> partial", "good -> bad")
        self.assertEqual(role_findings("sceptic", lambda body: body.replace(accepted, line)), [
            "consilium sceptic: correction #1 names opt-z, not an option",
            "consilium sceptic: correction #1 names FR-9, not a requirement",
            "consilium sceptic: correction #1 mark good is not meets, partial or fails",
            "consilium sceptic: correction #1 mark bad is not meets, partial or fails"])

    def test_accepted_correction_skips_the_fit_check_on_a_fault(self):
        accepted = role_line("sceptic", "- correction opt-c")
        for line, expected in (
            (accepted.replace("opt-c", "opt-z").replace("-> partial", "-> fails"),
             ["consilium sceptic: correction #1 names opt-z, not an option"]),
            (accepted.replace("FR-3", "FR-9").replace("-> partial", "-> fails"),
             ["consilium sceptic: correction #1 names FR-9, not a requirement"]),
            (accepted.replace("meets ->", "good ->").replace("-> partial", "-> fails"),
             ["consilium sceptic: correction #1 mark good is not meets, partial or fails"]),
        ):
            with self.subTest(line=line):
                self.assertEqual(role_findings("sceptic", lambda body: body.replace(accepted, line)), expected)

    def test_accepted_correction_is_checked_in_any_role(self):
        line = "- correction opt-a FR-2: fails -> meets — accepted: the event carries the claim id"
        self.assertEqual(role_findings("architect", lambda body: body + line + "\n"),
                         ["consilium architect: correction #1 accepted, but fit opt-a/FR-2 is fails, not meets"])
        self.assertEqual(role_findings("architect", lambda body: body + line.replace("accepted", "rejected") + "\n"),
                         [])

    def test_accepted_correction_without_a_mark_in_the_option_is_left_to_the_option_rules(self):
        fit = option_line("opt-c", "- fit FR-3:")
        text = fixture_text(CONSILIUM, edits=((fit + "\n", ""),))
        self.assertEqual(findings(text), ["fit opt-c/FR-3: missing"])

    def test_fenced_consilium_lines_are_not_read(self):
        preferred = role_line("operator", "- preferred:")
        fence = "```text\n- preferred: opt-z\n- correction nothing\n### architect\n```\n"
        self.assertEqual(role_findings("operator", lambda body: body.replace(preferred, preferred + "\n" + fence)), [])


class DecisionCase(unittest.TestCase):
    def test_valid_decide_record_is_ok(self):
        self.assertEqual(findings(fixture_text(DECIDE)), [])

    def test_bad_decision_fixture(self):
        self.assertEqual(findings(fixture_text("bad-decision.md")), [NO_DISSENT_SCEPTIC])

    def test_decision_choice(self):
        choice, why = decide_line("- choice:"), decide_line("- why:")
        self.assertEqual(decide_findings((choice + "\n", "")), ["decision: no choice"])
        self.assertEqual(decide_findings((choice, choice + "\n" + choice)), ["decision: choice twice"])
        self.assertEqual(decide_findings((choice, "- choice: opt-z")), ["decision: choice opt-z is not an option"])
        self.assertEqual(decide_findings((why + "\n", "")), ["decision: no why"])

    def test_decision_choice_forms(self):
        choice, why = decide_line("- choice:"), decide_line("- why:")
        self.assertEqual(decide_findings((choice, "- choice:")), ["decision: no choice"])
        self.assertEqual(decide_findings((choice, "- choice: opt-b because")),
                         ["decision: choice opt-b because is not an option"])
        self.assertEqual(decide_findings((choice, choice + "\n- choice: opt-z")), ["decision: choice twice"])
        self.assertEqual(decide_findings((why, "- why:")), ["decision: no why"])
        self.assertEqual(decide_findings((why, "- why: " + why[len("- why: "):] + "\n- why:")), [])

    def test_decision_none_has_no_exemption(self):
        text = fixture_text(DECIDE)
        self.assertEqual(findings(text.replace(decision_section(), "## Decision\n\nnone\n\n")),
                         ["decision: no choice", "decision: no why", "decision: no revisit when"])

    def test_decision_waits_for_the_section_and_the_stage(self):
        text = fixture_text(DECIDE)
        self.assertEqual(findings(text.replace(decision_section(), "## Decision\n\npending\n\n")),
                         ["section: Decision pending at stage decide"])
        self.assertEqual(findings(text.replace(decision_section(), "## Decision\n\n")),
                         ["section: Decision empty, write none"])
        self.assertEqual(findings(text.replace(decision_section(), "")), ["section: missing Decision"])
        self.assertEqual(findings(fixture_text(DECIDE, stage="consilium")), [
            "section: Decision not pending at stage consilium",
            "section: Open questions not pending at stage consilium",
            "section: Not covered not pending at stage consilium"])
        self.assertIn(NO_DISSENT_SCEPTIC, findings(fixture_text("bad-decision.md", stage="review")))

    def test_decision_why_not(self):
        not_c = decide_line("- why not opt-c:")
        self.assertEqual(decide_findings((not_c + "\n", "")), ["decision: no why not opt-c"])
        self.assertEqual(decide_findings((not_c, not_c + "\n- why not opt-b: it is the choice")),
                         ["decision: why not opt-b names the choice"])
        self.assertEqual(decide_findings((not_c, not_c + "\n- why not opt-z: it is nothing")),
                         ["decision: why not opt-z is not an option"])
        not_a = decide_line("- why not opt-a:")
        self.assertEqual(decide_findings((not_a, not_a + "\n" + not_a)), ["decision: why not opt-a twice"])

    def test_decision_why_not_forms(self):
        not_a, not_c = decide_line("- why not opt-a:"), decide_line("- why not opt-c:")
        for line in ("- why not opt-c", "- why not opt-c:", "- why not opt-c:  ", "- why not Option C: x",
                     "- why not opt-ab: x", "- why not: x"):
            with self.subTest(line=line):  # a line of another form names no option: the option has no why not
                self.assertEqual(decide_findings((not_c, line)), ["decision: no why not opt-c"])
        self.assertEqual(decide_findings((not_a + "\n" + not_c, "")),
                         ["decision: no why not opt-a", "decision: no why not opt-c"])
        self.assertEqual(decide_findings((not_c, "- why not opt-b: x\n- why not opt-b: y")),
                         ["decision: why not opt-b names the choice", "decision: why not opt-b names the choice",
                          "decision: why not opt-b twice", "decision: no why not opt-c"])

    def test_decision_dissent(self):
        dissent = decide_line("- dissent:")
        architect = "- dissent: architect preferred opt-b: it is the choice"
        self.assertEqual(decide_findings((dissent, dissent + "\n" + architect)),
                         ["decision: dissent for architect, who preferred the choice"])
        self.assertEqual(decide_findings((dissent, dissent.replace("preferred opt-a", "preferred opt-c"))),
                         ["decision: dissent sceptic names opt-c, consilium says opt-a"])
        self.assertEqual(decide_findings((dissent, "- dissent: nobody")), [DISSENT_FORM % 1, NO_DISSENT_SCEPTIC])

    def test_decision_dissent_forms(self):
        dissent = decide_line("- dissent:")
        for line in ("- dissent: critic preferred opt-a: r", "- dissent: sceptic preferred opt-a:",
                     "- dissent: sceptic preferred opt-a", "- dissent: sceptic preferred Option A: r",
                     "- dissent: sceptic prefers opt-a: r", "- dissent sceptic preferred opt-a: r", "- dissent:"):
            with self.subTest(line=line):
                self.assertEqual(decide_findings((dissent, line)), [DISSENT_FORM % 1, NO_DISSENT_SCEPTIC])

    def test_decision_dissent_lines_are_numbered_in_order(self):
        dissent = decide_line("- dissent:")
        self.assertEqual(decide_findings((dissent, "- dissent: x\n" + dissent + "\n- dissent: y")),
                         [DISSENT_FORM % 1, DISSENT_FORM % 3])

    def test_dissent_rules_are_exclusive_for_a_role_that_preferred_the_choice(self):
        dissent = decide_line("- dissent:")
        self.assertEqual(decide_findings((dissent, dissent + "\n- dissent: operator preferred opt-c: r")),
                         ["decision: dissent for operator, who preferred the choice"])  # not "names opt-c"

    def test_dissent_is_missing_for_each_role_in_role_order(self):
        dissent = decide_line("- dissent:")
        text = fixture_text(DECIDE, edits=((dissent + "\n", ""),))
        self.assertEqual(findings(text), [NO_DISSENT_SCEPTIC])
        operator, architect = role_block("operator"), role_block("architect")
        # the architect, the operator and the sceptic all differ from the choice: a dissent line is missing for each
        text = fixture_text(DECIDE, edits=((dissent + "\n", ""),
                                           (operator, operator.replace("preferred: opt-b", "preferred: opt-c")),
                                           (architect, architect.replace("preferred: opt-b", "preferred: opt-a"))))
        self.assertEqual(findings(text), ["decision: no dissent for architect", "decision: no dissent for operator",
                                          NO_DISSENT_SCEPTIC])

    def test_dissent_waits_for_the_consilium_of_the_role(self):
        preferred, dissent = role_line("sceptic", "- preferred:"), decide_line("- dissent:")
        self.assertEqual(decide_findings((preferred + "\n", "")), ["consilium sceptic: no preferred"])
        self.assertEqual(decide_findings((preferred + "\n", ""), (dissent + "\n", "")),
                         ["consilium sceptic: no preferred"])
        self.assertEqual(decide_findings((role_block("sceptic"), "")), ["consilium sceptic: missing"])

    def test_decision_revisit(self):
        revisit = decide_line("- revisit when:")
        self.assertEqual(decide_findings((revisit + "\n", "")), ["decision: no revisit when"])
        self.assertEqual(decide_findings((revisit, "- revisit when:")), ["decision: no revisit when"])
        self.assertEqual(decide_findings((revisit, revisit + "\n- revisit when: or when the volume doubles")), [])

    def test_next_steps_have_no_rule(self):
        steps = decide_line("- next steps:")
        self.assertEqual(decide_findings((steps + "\n", "")), [])
        self.assertEqual(decide_findings((steps, "- next steps:")), [])

    def test_why_must_name_failed_requirement(self):
        why = decide_line("- why:")
        self.assertEqual(decide_findings((why, why.replace("NFR-1", "the target"))), [WHY_NFR_1])

    def test_why_token_match_is_exact(self):
        why = decide_line("- why:")
        self.assertEqual(decide_findings((why, why.replace("NFR-1", "NFR-12"))), [WHY_NFR_1])
        for form in ("(NFR-1)", "NFR-1,", "NFR-1.", "[NFR-1]"):
            with self.subTest(form=form):
                self.assertEqual(decide_findings((why, why.replace("NFR-1", form))), [])
        for form in ("NFR-10", "ANFR-1", "NFR-1-b", "xNFR-1", "_NFR-1", "NFR-1_", "-NFR-1"):
            with self.subTest(form=form):
                self.assertEqual(decide_findings((why, why.replace("NFR-1", form))), [WHY_NFR_1])
        self.assertEqual(decide_findings((why, why.replace("NFR-1", "NFR-12 and NFR-1"))), [])

    def test_why_reads_only_the_why_line(self):
        why = decide_line("- why:")
        for other in ("- why not opt-a:", "- dissent:", "- revisit when:"):
            line = decide_line(other)
            with self.subTest(other=other):  # NFR-1 on another line does not satisfy the why rule
                self.assertEqual(decide_findings((why, why.replace("NFR-1", "the target")),
                                                 (line, line + " NFR-1")), [WHY_NFR_1])

    def test_why_rule_follows_the_choice(self):
        body = (
            "## Decision\n\n- choice: opt-a\n- why: opt-a meets NFR-1%s\n"
            "- why not opt-b: it waits for a grouping window\n- why not opt-c: a second store\n"
            "- dissent: architect preferred opt-b: it names the claims; the decision stands\n"
            "- dissent: operator preferred opt-b: it traces a stuck case; the decision stands\n"
            "- revisit when: the claims matter\n- next steps: build the notifier\n\n")
        text = fixture_text(DECIDE)
        self.assertEqual(findings(text.replace(decision_section(), body % "")),
                         ["decision: why does not name FR-2 (opt-a fails it, opt-b meets it)"])
        self.assertEqual(findings(text.replace(decision_section(), body % " but fails FR-2")), [])

    def test_why_rule_needs_another_option_that_meets_the_requirement(self):
        why, fit = decide_line("- why:"), option_line("opt-a", "- fit NFR-1:")
        self.assertEqual(decide_findings((why, why.replace("NFR-1", "the target")),
                                         (fit, fit.replace("meets", "partial", 1))), [])
        self.assertEqual(decide_findings((why, why.replace("NFR-1", "the target")),
                                         (fit, fit.replace("meets", "fails", 1))), [])

    def test_why_rule_names_an_option_that_meets_it(self):
        why = decide_line("- why:")
        fit = option_line("opt-c", "- fit NFR-1:")
        self.assertEqual(decide_findings((why, why.replace("NFR-1", "the target")),
                                         (option_line("opt-a", "- fit NFR-1:"),
                                          option_line("opt-a", "- fit NFR-1:").replace("meets", "partial", 1)),
                                         (fit, fit.replace("partial", "meets", 1))),
                         ["decision: why does not name NFR-1 (opt-b fails it, opt-c meets it)"])

    def test_why_rule_is_not_run_without_a_valid_choice_or_a_why(self):
        choice, why = decide_line("- choice:"), decide_line("- why:")
        self.assertEqual(decide_findings((choice, "- choice: opt-z"), (why, why.replace("NFR-1", "the target"))),
                         ["decision: choice opt-z is not an option"])
        self.assertEqual(decide_findings((why + "\n", "")), ["decision: no why"])

    def test_choice_helper(self):
        self.assertEqual(sdr.choice(sdr.parse_record(fixture_text(DECIDE))), "opt-b")
        self.assertIsNone(sdr.choice(sdr.parse_record(fixture_text(CONSILIUM))))
        self.assertIsNone(sdr.choice(sdr.parse_record(fixture_text(OPTIONS))))
        self.assertIsNone(sdr.choice(sdr.parse_record("# SDR: q\nstage: intake\nroot: /r\ncode: none\n")))

    def test_choice_helper_reads_the_first_choice_line(self):
        choice = decide_line("- choice:")
        record = sdr.parse_record(fixture_text(DECIDE, edits=((choice, "- choice: opt-c\n- choice: opt-a"),)))
        self.assertEqual(sdr.choice(record), "opt-c")
        self.assertIsNone(sdr.choice(sdr.parse_record(fixture_text(DECIDE, edits=((choice + "\n", ""),)))))

    def test_fenced_decision_lines_are_not_read(self):
        choice = decide_line("- choice:")
        fence = "```text\n- choice: opt-z\n- dissent: nobody\n- why not opt-z: x\n```"
        self.assertEqual(decide_findings((choice, choice + "\n" + fence)), [])


# valid-decide.md: the mark of each option for FR-1, FR-2, FR-3, NFR-1 and NFR-2; the choice is opt-b
MARK_GRID = {
    "opt-a": ("meets", "fails", "meets", "meets", "partial"),
    "opt-b": ("meets", "meets", "meets", "fails", "meets"),
    "opt-c": ("meets", "meets", "partial", "partial", "meets"),
}
REQUIREMENT_IDS = ["FR-1", "FR-2", "FR-3", "NFR-1", "NFR-2"]
FR_1_TEXT = "The end user is told about every block, unblock and confiscation"
ESCAPE_EDITS = (
    (FR_1_TEXT, '<b> & "q" `x`'),
    ("### opt-a: Notify per warrant total", "### opt-a: A < B"),
)
OPT_A_HEADING = "opt-a: Notify per warrant total"
OPT_B_HEADING = "opt-b: Executor emits one event per claim action"
NO_WHY_NOT_C = ("- why not opt-c: a second store must stay in step with the claim map, and a rollback leaves its "
                "data behind\n", "")
NO_REVISIT = ("- revisit when: the arrival time of the last claim event of an action is known\n", "")
VERIFY_LINES = ["self-contained: ok", "render 1440x900: ok", "render 500x844: ok", "citations: ok", "prose: ok",
                "bpmn: none"]
BLOCK = '<div class="sdr-matrix">'
EMPTY_BLOCK = BLOCK + "</div>"


def run_verify(page: Path, tmp: Path) -> subprocess.CompletedProcess:
    """Run explain's verify.sh as its own test does: TMPDIR set to a test dir, no VERIFY_TIMEOUT, 240 s."""
    env = dict(os.environ, TMPDIR=str(tmp) + "/")
    env.pop("VERIFY_TIMEOUT", None)
    return subprocess.run([str(VERIFY), str(page)], capture_output=True, text=True, env=env, timeout=240)


class MatrixCase(unittest.TestCase):
    def test_matrix_fills_before_page_as_after(self):
        target = page_dir()
        run = run_sdr("matrix", str(target))
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "sdr: ok\n", ""))
        self.assertEqual((target / "index.html").read_bytes(), (PAGES / "after.html").read_bytes())

    def test_matrix_second_run_is_byte_identical(self):
        target = page_dir()
        filled_page(target)
        first = (target / "index.html").read_bytes()
        filled_page(target)
        self.assertEqual((target / "index.html").read_bytes(), first)

    def test_matrix_marks_chosen_column(self):
        cells = MatrixCells(filled_page(page_dir()))
        heads = cells.rows[0]
        self.assertEqual([cell["tag"] for cell in heads], ["th"] * 4)
        self.assertEqual([cell["class"] for cell in heads], [None, None, "chosen", None])
        self.assertEqual(heads[0]["text"], "Requirement")
        self.assertEqual(heads[1]["text"], OPT_A_HEADING)
        self.assertTrue(heads[2]["text"].startswith("opt-b:"), heads[2]["text"])
        self.assertTrue(heads[2]["text"].endswith("(chosen)"), heads[2]["text"])
        self.assertEqual(heads[2]["text"], OPT_B_HEADING + " (chosen)")
        for row in cells.rows[1:]:
            self.assertEqual([cell["class"] for cell in row], [None, None, "chosen", None])

    def test_matrix_cells_have_aria_labels(self):
        cells = MatrixCells(filled_page(page_dir()))
        self.assertEqual(sdr.SYMBOLS, {"meets": "✓", "partial": "◐", "fails": "✗"})
        body = cells.rows[1:]
        self.assertEqual(len(body), 5)
        self.assertEqual([row[0]["text"].split()[0] for row in body], REQUIREMENT_IDS)
        for row in body:
            self.assertEqual((len(row), row[0]["marks"]), (4, []))
        for column, ident in enumerate(MARK_GRID, 1):
            for row, mark in zip(body, MARK_GRID[ident]):
                self.assertEqual(row[column]["marks"], [["img", mark, sdr.SYMBOLS[mark]]], (ident, row[0]["text"]))
        self.assertEqual(body[3][2]["marks"], [["img", "fails", "✗"]])  # opt-b / NFR-1

    def test_matrix_holds_its_style(self):
        cells = MatrixCells(filled_page(page_dir()))
        self.assertEqual(cells.styles, [sdr.CHOSEN_CSS])
        self.assertEqual(sdr.CHOSEN_CSS, "table.matrix .chosen { background: var(--fill); }\n"
                                         "table.matrix th.chosen { color: var(--ink); font-weight: 700; }")
        self.assertEqual(sdr.MATRIX_OPEN, BLOCK)

    def test_matrix_escapes_html(self):
        target = page_dir(fixture_text(DECIDE, edits=ESCAPE_EDITS))
        page = filled_page(target)
        self.assertIn("<td><code>FR-1</code> &lt;b&gt; &amp; &quot;q&quot; <code>x</code></td>", page)
        self.assertIn("<th>opt-a: A &lt; B</th>", page)
        self.assertNotIn("<b>", page)
        self.assertEqual(MatrixCells(page).rows[0][1]["text"], "opt-a: A < B")
        first = (target / "index.html").read_bytes()
        filled_page(target)
        self.assertEqual((target / "index.html").read_bytes(), first)
        set_stage(target, "page")
        run = run_sdr("check", str(target))
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "sdr: ok\n", ""))

    def test_matrix_refuses_invalid_record(self):
        target = page_dir(fixture_text(DECIDE, edits=(NO_WHY_NOT_C,)))
        run = run_sdr("matrix", str(target))
        self.assertEqual(run.returncode, 1)
        self.assertIn("decision: no why not opt-c", run.stdout.splitlines())
        self.assertEqual(run.stdout.splitlines()[-1], "sdr: 1 findings")
        self.assertEqual((target / "index.html").read_bytes(), (PAGES / "before.html").read_bytes())

    def test_matrix_refuses_stage_before_decide(self):
        target = page_dir(fixture_text(CONSILIUM))
        run = run_sdr("matrix", str(target))
        self.assertEqual(run.returncode, 1)
        self.assertEqual(run.stdout.splitlines(), ["page: stage consilium is before decide", "sdr: 1 findings"])
        self.assertEqual((target / "index.html").read_bytes(), (PAGES / "before.html").read_bytes())

    def test_matrix_block_errors(self):
        before = (PAGES / "before.html").read_text(encoding="utf-8")
        self.assertEqual(before.count(EMPTY_BLOCK), 1)
        cases = (
            (before.replace(EMPTY_BLOCK, ""), 'page: no <div class="sdr-matrix">'),
            (before.replace(EMPTY_BLOCK, EMPTY_BLOCK * 2),
             'page: 2 <div class="sdr-matrix"> blocks, more than 1'),
            (before.replace(EMPTY_BLOCK, BLOCK), 'page: <div class="sdr-matrix"> is not closed'),
            (before.replace(EMPTY_BLOCK, BLOCK + "<div></div>"), 'page: <div class="sdr-matrix"> is not closed'),
        )
        for page, wanted in cases:
            with self.subTest(wanted=wanted, page=page[page.index("<section") :][:80]):
                target = page_dir(page=None)
                (target / "index.html").write_text(page, encoding="utf-8")
                run = run_sdr("matrix", str(target))
                self.assertEqual(run.returncode, 1)
                self.assertEqual(run.stdout.splitlines(), [wanted, "sdr: 1 findings"])
                self.assertEqual((target / "index.html").read_text(encoding="utf-8"), page)
                record = sdr.read_record(str(target))
                self.assertEqual(sdr.page_lines(record, page), [wanted])

    def test_matrix_replaces_only_the_block_content(self):
        before = (PAGES / "before.html").read_text(encoding="utf-8")
        nested = before.replace(EMPTY_BLOCK, BLOCK + "<div><div>old</div></div></div>")
        target = page_dir(page=None)
        (target / "index.html").write_text(nested, encoding="utf-8")
        page = filled_page(target)
        self.assertEqual(page, (PAGES / "after.html").read_text(encoding="utf-8"))

    def test_matrix_needs_index_html(self):
        target = page_dir(page=None)
        run = run_sdr("matrix", str(target))
        self.assertEqual((run.returncode, run.stdout), (2, ""))
        self.assertTrue(run.stderr.startswith("sdr: cannot read %s" % (target / "index.html")), run.stderr)

    def test_matrix_exit_2_cases(self):
        run = run_sdr("matrix")
        self.assertEqual(run.returncode, 2)
        self.assertTrue(run.stderr.startswith("usage: sdr.py"), run.stderr)
        run = run_sdr("matrix", str(page_dir()), "extra")
        self.assertEqual(run.returncode, 2)
        self.assertTrue(run.stderr.startswith("usage: sdr.py"), run.stderr)
        run = run_sdr("matrix", str(temp_dir()))  # no sdr.md
        self.assertEqual(run.returncode, 2)
        self.assertIn("sdr: cannot read", run.stderr)
        target = record_dir(fixture_text(DECIDE))  # root: /fixture-root, which does not exist
        run = run_sdr("matrix", str(target))
        self.assertEqual((run.returncode, run.stdout), (2, ""))
        self.assertEqual(run.stderr, "sdr: cannot read root /fixture-root\n")
        target = record_dir(fixture_text(DECIDE, edits=(("root: /fixture-root", "root: relative"),)))
        run = run_sdr("matrix", str(target))
        self.assertEqual(run.returncode, 2)
        self.assertTrue(run.stderr.startswith("sdr: no root"), run.stderr)


class PageCheckCase(unittest.TestCase):
    def test_page_review_done_records_are_ok(self):
        for stage in ("page", "review", "done"):
            with self.subTest(stage=stage):
                target = page_dir(fixture_text(DECIDE, stage=stage), page="after.html")
                run = run_sdr("check", str(target))
                self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "sdr: ok\n", ""))

    def test_stale_page_fixture(self):
        target = page_dir(fixture_text(DECIDE, stage="page"), page="stale.html")
        run = run_sdr("check", str(target))
        self.assertEqual(run.returncode, 1)
        self.assertEqual(run.stdout.splitlines(), ["page: matrix stale", "sdr: 1 findings"])

    def test_stale_fixture_differs_from_after_in_one_cell(self):
        after = MatrixCells((PAGES / "after.html").read_text(encoding="utf-8"))
        stale = MatrixCells((PAGES / "stale.html").read_text(encoding="utf-8"))
        self.assertEqual(after.rows[4][1]["marks"], [["img", "meets", "✓"]])  # opt-a / NFR-1
        self.assertEqual(stale.rows[4][1]["marks"], [["img", "fails", "✗"]])
        stale.rows[4][1]["marks"] = after.rows[4][1]["marks"]
        self.assertEqual(stale.rows, after.rows)

    def test_page_stage_without_index_html(self):
        target = page_dir(fixture_text(DECIDE, stage="page"), page=None)
        run = run_sdr("check", str(target))
        self.assertEqual(run.returncode, 1)
        self.assertEqual(run.stdout.splitlines(), ["page: no index.html", "sdr: 1 findings"])

    def test_page_lines_wait_for_a_clean_record(self):
        target = page_dir(fixture_text(DECIDE, stage="page", edits=(NO_REVISIT,)), page="stale.html")
        run = run_sdr("check", str(target))
        self.assertEqual(run.returncode, 1)
        self.assertEqual(run.stdout.splitlines(), ["decision: no revisit when", "sdr: 1 findings"])

    def test_check_before_page_ignores_the_page(self):
        for page in (None, "stale.html"):
            with self.subTest(page=page):
                target = page_dir(page=page)  # stage decide
                run = run_sdr("check", str(target))
                self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "sdr: ok\n", ""))

    def test_check_reports_an_unreadable_index_html(self):
        target = page_dir(fixture_text(DECIDE, stage="page"), page=None)
        (target / "index.html").mkdir()
        run = run_sdr("check", str(target))
        self.assertEqual((run.returncode, run.stdout), (2, ""))
        self.assertTrue(run.stderr.startswith("sdr: cannot read %s: " % (target / "index.html")), run.stderr)

    def test_page_lines_function(self):
        record = sdr.parse_record(fixture_text(DECIDE, stage="page"))
        after = (PAGES / "after.html").read_text(encoding="utf-8")
        stale = (PAGES / "stale.html").read_text(encoding="utf-8")
        self.assertEqual(sdr.page_lines(record, None), ["page: no index.html"])
        self.assertEqual(sdr.page_lines(record, after), [])
        self.assertEqual(sdr.page_lines(record, stale), ["page: matrix stale"])
        self.assertEqual(sdr.page_lines(record, after.replace("\n</div>", "</div>")), ["page: matrix stale"])

    @unittest.skipUnless(CHROME.exists(), "Chrome is not installed")
    def test_filled_template_page_passes_verify(self):
        target = page_dir(page=None)
        page = template_page(target)
        filled_page(target)
        tmp = Path(os.path.realpath(temp_dir())) / "chrome"
        tmp.mkdir()
        self.addCleanup(lambda: subprocess.run(["pkill", "-KILL", "-f", str(tmp)], capture_output=True))
        proc = run_verify(page, tmp)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.splitlines(), VERIFY_LINES, proc.stdout)


class CheckFactsCase(unittest.TestCase):
    def test_check_facts_good_files(self):
        for name in ("code-good.md", "web-good.md"):
            with self.subTest(name=name):
                run = run_sdr("check-facts", str(FACTS / name), "--root", str(TREE))
                self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "sdr: ok\n", ""))

    def test_check_facts_bad_snippet(self):
        run = run_sdr("check-facts", str(FACTS / "bad-snippet.md"), "--root", str(TREE))
        self.assertEqual(run.returncode, 1)
        self.assertEqual(run.stdout.splitlines(), ["cite Facts#1: snippet not found on that line", "sdr: 1 findings"])

    def test_check_facts_sections(self):
        self.assertEqual(facts_findings(("\n## Unknowns\n\n" + UNKNOWN_LINE + "\n", "")),
                         ["section: missing Unknowns"])
        self.assertEqual(facts_findings(("# Facts: orchestrator", "# Map: x")), ['title: not "# Facts: <id>"'])
        self.assertEqual(facts_findings((UNKNOWN_LINE + "\n", UNKNOWN_LINE + "\n\n## Notes\n\nx\n")),
                         ["section: unknown Notes"])

    def test_check_facts_section_order_and_repeats(self):
        self.assertEqual(facts_findings(("## Shape\n\n" + SHAPE_FACT + "\n\n", ""),
                                        (UNKNOWN_LINE + "\n", UNKNOWN_LINE + "\n\n## Shape\n\nnone\n")),
                         ["section: Shape out of order"])
        self.assertEqual(facts_findings((UNKNOWN_LINE + "\n", UNKNOWN_LINE + "\n\n## Facts\n\nnone\n")),
                         ["section: Facts twice"])

    def test_check_facts_title_cases(self):
        for first in ("# Facts:", "# Facts: ", "Facts: x", "## Facts: x", ""):
            with self.subTest(first=first):
                self.assertEqual(facts_findings(("# Facts: orchestrator", first)), ['title: not "# Facts: <id>"'])
        text = "\n\n" + fixture_text(CODE_GOOD)
        self.assertEqual(sdr.check_facts(text, str(TREE)), [])
        self.assertEqual(sdr.check_facts("\ufeff" + fixture_text(CODE_GOOD).replace("\n", "\r\n"), str(TREE)), [])
        self.assertEqual(sdr.check_facts("", str(TREE)),
                         ['title: not "# Facts: <id>"', "section: missing Facts", "section: missing Unknowns"])

    def test_check_facts_flow_node_rules(self):
        self.assertEqual(facts_findings((WARRANT_FACT + "\n", "")), ["node route/warrant: no fact line"])
        extra = "- extra: a fact for no node | orchestrator/ClaimRouter.java:16 | Optional.ofNullable"
        self.assertEqual(facts_findings((WARRANT_FACT, WARRANT_FACT + "\n" + extra)),
                         ["fact route/extra: not a node"])
        self.assertEqual(facts_findings((ROUTE_HEADING, "### How?")), ["flow How?: no flow id"])
        for heading in ("Route: How?", "route : How?", "9route: How?", ": How?"):
            with self.subTest(heading=heading):
                self.assertEqual(facts_findings((ROUTE_HEADING, "### " + heading)),
                                 ["flow %s: no flow id" % heading])
        nodes = ["n%d" % number for number in range(1, 27)]
        chain = "".join("  %s --> %s\n" % pair for pair in zip(nodes, nodes[1:]))
        facts = "\n".join("- %s: node %s | orchestrator/ClaimRouter.java:16 | Optional.ofNullable" % (node, node)
                          for node in nodes)
        lines = facts_findings(("  router --> lookup\n  lookup --> warrant\n", chain),
                               ("\n".join((ROUTER_FACT, LOOKUP_FACT, WARRANT_FACT)), facts))
        self.assertEqual(lines[0], "diagram route: 26 nodes, more than 25")
        self.assertEqual(lines, ["diagram route: 26 nodes, more than 25"])

    def test_check_facts_flow_without_diagram_or_with_two(self):
        diagram = "```mermaid\nflowchart TD\n  router --> lookup\n  lookup --> warrant\n```\n"
        self.assertEqual(facts_findings((diagram, "")),
                         ["diagram route: none"] + ["fact route/%s: not a node" % key
                                                     for key in ("router", "lookup", "warrant")])
        self.assertEqual(facts_findings((diagram, diagram + "\n" + diagram)), ["diagram route: 2 blocks, more than 1"])

    def test_check_facts_cites(self):
        self.assertEqual(facts_findings((SHAPE_FACT, "- Java service that maps each claim to its warrant")),
                         ["cite Shape#1: no cite"])
        self.assertEqual(facts_findings((FACTS_FIRST, FACTS_FIRST.replace("Many claims", "Few claims"))),
                         ["cite Facts#1: snippet not found on that line"])
        self.assertEqual(facts_findings((WARRANT_FACT, WARRANT_FACT.replace("Optional.ofNullable", "Optional.empty"))),
                         ["cite Relevant flows/route#3: snippet not found on that line"])
        self.assertEqual(facts_findings((WARRANT_FACT, "- warrant: an unknown claim gives no warrant")),
                         ["cite Relevant flows/route#3: no cite"])
        self.assertEqual(facts_findings((SHAPE_FACT, "- none"), (FACTS_FIRST, "- none\n" + FACTS_FIRST)), [])
        self.assertEqual(facts_findings((FACTS_FIRST, "- none\n- no cite here")), ["cite Facts#1: no cite"])

    def test_check_facts_cli_errors(self):
        good = str(FACTS / "code-good.md")
        run = run_sdr("check-facts", good)
        self.assertEqual(run.returncode, 2)
        self.assertTrue(run.stderr.startswith("usage: sdr.py"), run.stderr)
        self.assertEqual(run.stdout, "")
        run = run_sdr("check-facts", str(FACTS / "missing.md"), "--root", str(TREE))
        self.assertEqual(run.returncode, 2)
        self.assertTrue(run.stderr.startswith("sdr: cannot read %s" % (FACTS / "missing.md")), run.stderr)
        run = run_sdr("check-facts", good, "--root", str(TREE / "missing"))
        self.assertEqual(run.returncode, 2)
        self.assertTrue(run.stderr.startswith("sdr: cannot read root %s" % (TREE / "missing")), run.stderr)
        run = run_sdr("check-facts", "--root", str(TREE))
        self.assertEqual(run.returncode, 2)
        self.assertTrue(run.stderr.startswith("usage: sdr.py"), run.stderr)

    def test_check_facts_rejects_a_file_that_is_not_utf8(self):
        target = temp_dir() / "facts.md"
        target.write_bytes(b"# Facts: \xff\xfe\n")
        run = run_sdr("check-facts", str(target), "--root", str(TREE))
        self.assertEqual(run.returncode, 2)
        self.assertTrue(run.stderr.startswith("sdr: cannot read %s" % target), run.stderr)


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
