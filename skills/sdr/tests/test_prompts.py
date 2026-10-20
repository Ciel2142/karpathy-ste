"""The texts of the `sdr` skill and the fixture that its live run reads (spec sections 7, 11 and 12).

This module is the one place that ties SKILL.md, the four prompts under prompts/, sdr.py (USAGE, STAGES, SECTIONS,
ROLES, FACTS_TITLES) and the page rung of `explain` together, so that they cannot drift. It also checks the warrants
fixture with `sdr.py check`. It imports no module of skills/explain/tests/; the helpers are its own. It puts
skills/sdr/scripts on sys.path and does `import sdr`. Each test names the mutation that turns it red.

WarrantsFixtureCase ties the fixture tree under tests/fixtures/warrants/ to the record that the live run of spec
section 12 imitates by hand. The tree has two code directories, services/orchestrator and services/executor (plain
Java 17, no build file, three files each, SERVICES), and the record lives beside them in record/sdr.md (RECORD_DIR),
not under services/. The record is at stage `decide` and `sdr.py check` passes it with `--root SERVICES`, which
overrides the `root:` line of the record as the tests of wave 1 do. The Context of the record cites a line of both
services and one URL, so a cite that moves out of its line, or a record that cites one service only, turns the
check red. The decision rules are in force: the choice has a `fails` mark that another option `meets`, a consilium
role prefers an option other than the choice, the consilium holds one accepted and one rejected correction, and a
requirement comes from `source: consilium <role>`. The services hold no comment line, so no word in them hints at
the gap or at an option; SERVICES holds the two directories, each with its three .java files. The record lies
outside the root of the run: the live run reads the code under SERVICES, and a finished decision under SERVICES
would be read as code.

- test_warrants_record_passes_check: change a cited line of a service, or a snippet of the record, so that a cite
  no longer holds, or break a rule of sdr.py in the record. `check` then prints a finding and exits 1.
- test_warrants_record_is_at_stage_decide: change the `stage:` line of the record to another stage.
- test_record_cites_both_services: drop the cites of one service from Context, or the one URL cite.
- test_record_runs_the_decision_rules: make the choice an option with no `fails` mark that another option meets,
  make every consilium role prefer the choice, drop the accepted or the rejected correction, or give no
  requirement the source `consilium <role>`.
- test_record_is_outside_the_root: move record/sdr.md under services/ (at any depth).
- test_services_hold_no_comment: add a line that starts with `//`, `/*` or `*` to a service file.
- test_the_two_services: rename, add or drop a service directory, or drop one of the three files of a service."""

import os
import subprocess
import sys
import unittest
from pathlib import Path

SDR = Path(__file__).resolve().parent.parent
REPO = SDR.parent.parent
sys.path.insert(0, str(SDR / "scripts"))

import sdr  # noqa: E402

PROMPTS = SDR / "prompts"
SKILL_MD = SDR / "SKILL.md"
WARRANTS = SDR / "tests" / "fixtures" / "warrants"
SERVICES = WARRANTS / "services"  # the root of the cites of the record and of the live run
RECORD_DIR = WARRANTS / "record"  # holds sdr.md, outside the root

SERVICE_FILES = {
    "orchestrator": ("Claim.java", "WarrantMapper.java", "LegacyClaimWorkflow.java"),
    "executor": ("WarrantCommandListener.java", "ExecutionEvent.java", "EventPublisher.java"),
}
COMMENT_STARTS = ("//", "/*", "*")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_sdr(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(SDR / "scripts" / "sdr.py"), *map(str, args)],
                          capture_output=True, text=True, timeout=60)


def record_lines(title: str) -> list[str]:
    """The stripped text of each non-blank line of a section of the warrants record, its blocks included."""
    section = sdr.read_record(str(RECORD_DIR)).section(title)
    assert section is not None, "the warrants record has no section %s" % title
    return [text for _, text in section.lines] + [text for block in section.blocks for _, text in block.lines]


class WarrantsFixtureCase(unittest.TestCase):
    def test_warrants_record_passes_check(self):
        run = run_sdr("check", RECORD_DIR, "--root", SERVICES)
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "sdr: ok\n", ""))

    def test_warrants_record_is_at_stage_decide(self):
        self.assertEqual(sdr.read_record(str(RECORD_DIR)).stage, "decide")

    def test_record_cites_both_services(self):
        section = sdr.read_record(str(RECORD_DIR)).section("Context")
        self.assertIsNotNone(section)
        facts = [sdr.parse_fact(n, number, text[2:])
                 for n, (number, text) in enumerate([line for line in section.lines if line[1].startswith("- ")], 1)]
        wheres = [fact.where for fact in facts if fact.where is not None]
        paths = [where for where in wheres if not where.startswith(("http://", "https://"))]
        self.assertTrue(any(path.startswith("orchestrator/") for path in paths), paths)
        self.assertTrue(any(path.startswith("executor/") for path in paths), paths)
        self.assertTrue(any(where.startswith(("http://", "https://")) for where in wheres), wheres)

    def test_record_runs_the_decision_rules(self):
        record = sdr.read_record(str(RECORD_DIR))
        found, chosen_id = sdr.options(record), sdr.choice(record)
        chosen = next((option for option in found if option.ident == chosen_id), None)
        self.assertIsNotNone(chosen, chosen_id)
        failed = [ident for ident, mark in chosen.fits.items() if mark == "fails"]
        self.assertTrue(any(other.fits.get(ident) == "meets" for ident in failed
                            for other in found if other.ident != chosen_id), (chosen_id, chosen.fits))
        consilium = record_lines("Consilium")
        preferred = [text.removeprefix("- preferred:").strip() for text in consilium if text.startswith("- preferred:")]
        self.assertEqual(len(preferred), 3, preferred)
        self.assertTrue(any(ident != chosen_id for ident in preferred), (chosen_id, preferred))
        self.assertTrue(any("— accepted:" in text for text in consilium), consilium)
        self.assertTrue(any("— rejected:" in text for text in consilium), consilium)
        requirements = record_lines("Functional requirements") + record_lines("Non-functional requirements")
        self.assertTrue(any("source: consilium " in text for text in requirements), requirements)

    def test_record_is_outside_the_root(self):
        record_dir, services = RECORD_DIR.resolve(), SERVICES.resolve()
        self.assertTrue((record_dir / "sdr.md").is_file())
        self.assertNotEqual(os.path.commonpath([record_dir, services]), str(services))
        self.assertEqual(sorted(path.relative_to(services).as_posix() for path in services.rglob("sdr.md")), [])

    def test_services_hold_no_comment(self):
        files = sorted(SERVICES.rglob("*.java"))
        self.assertEqual(len(files), 6, files)
        for path in files:
            for number, line in enumerate(read(path).splitlines(), 1):
                self.assertFalse(line.strip().startswith(COMMENT_STARTS), "%s:%d: %s" % (path.name, number, line))

    def test_the_two_services(self):
        self.assertEqual(sorted(path.name for path in SERVICES.iterdir() if path.is_dir()), sorted(SERVICE_FILES))
        for service, names in SERVICE_FILES.items():
            self.assertEqual(sorted(path.name for path in (SERVICES / service).glob("*.java")), sorted(names), service)


if __name__ == "__main__":
    unittest.main()
