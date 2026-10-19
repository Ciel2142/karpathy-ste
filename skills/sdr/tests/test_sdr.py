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
FRAME = "valid-frame.md"
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


def frame_findings(*edits: tuple[str, str]) -> list[str]:
    """The findings of valid-frame.md with the edits applied."""
    return findings(fixture_text(FRAME, edits=edits))


def facts_findings(*edits: tuple[str, str]) -> list[str]:
    """The findings of facts/code-good.md with the edits applied."""
    return sdr.check_facts(fixture_text(CODE_GOOD, edits=edits), str(TREE))


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
