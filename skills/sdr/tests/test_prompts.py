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
- test_the_two_services: rename, add or drop a service directory, or drop one of the three files of a service.

SearchPromptCase ties the two searcher prompts, search-code.md and search-web.md, to what `sdr.py check-facts` reads
(FACTS_TITLES, FACTS_REQUIRED) and to spec sections 7.1 and 7.2. A prompt is a template that the main session fills by
plain text replacement of each `{name}`, so the names in braces are pinned for each prompt (PLACEHOLDERS), also those
inside a fenced block. Both prompts hold the level-2 sections SEARCH_SECTIONS in order. The skeleton of the fact file
is a fenced block: four backticks in the code prompt, which nests the Mermaid fence, so a section helper must not
mistake its `## ` lines for a heading of the prompt. The rules of form are those that `check-facts` reads: a fact is
one `- ` line, and a fact inside a `~~~` fence or a fenced block outside `Relevant flows` is lost with no finding
(wave 1 ruling R9).

- test_each_search_prompt_has_exactly_its_placeholders: add or drop a name in braces in a prompt, rename one, or
  write a Mermaid rhombus node such as `a{x}`.
- test_each_search_prompt_has_its_sections: rename, drop, add or reorder a level-2 section, or put a `## ` line of
  the skeleton outside a fence.
- test_each_search_prompt_runs_check_facts: change the command line of CHECK_FACTS, take it out of the fenced block,
  or drop `sdr: ok` or `3 rounds` from the section Check.
- test_each_search_prompt_ends_with_a_result_line: drop either line of RESULT_LINES from the section Result.
- test_the_code_fact_file_skeleton: change the title line of the skeleton, drop, add or reorder one of its four
  sections, or drop the `flowchart TD`.
- test_the_web_fact_file_skeleton: change the title line, add `Shape` or `Relevant flows`, or drop `Facts` or
  `Unknowns`.
- test_fact_rules_in_each_prompt: drop or reword a rule of SHARED_FACT_RULES from either prompt, a rule of
  CODE_FACT_RULES from the code prompt or the rule of WEB_FACT_RULES from the web prompt, or move a rule out of the
  section The fact file.
- test_the_code_searcher_reads_only: reword or drop a line of READ_RULES in the code prompt, or drop the name
  `.codegraph/`.
- test_the_web_searcher_cites_fetched_pages: reword or drop a line of WEB_RULES in the web prompt.
- test_each_search_prompt_lints_clean: write a sentence of 26 words or more outside a fenced block, a heading and a
  table row."""

import os
import re
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

PLACEHOLDER = re.compile(r"\{([A-Za-z_]+)\}")
PLACEHOLDERS = {  # prompt file name -> the names in braces that it holds, braces removed
    "search-code.md": frozenset({"skill_dir", "question", "code_dir", "root", "fact_id", "facts"}),
    "search-web.md": frozenset({"skill_dir", "question", "topic", "root", "fact_id", "facts"}),
}
FENCE_LINE = re.compile(r"\s*(`{3,})")
SEARCH_PROMPTS = ("search-code.md", "search-web.md")
SEARCH_SECTIONS = ("Your task", "Inputs", "What to look for", "Rules", "The fact file", "Check", "Result")
CHECK_FACTS = "python3 {skill_dir}/scripts/sdr.py check-facts {facts} --root {root}"
RESULT_LINES = ("facts: done {fact_id} <n> facts", "facts: failed <reason>")
SHARED_FACT_RULES = ("Write each fact as one `- ` line.", "Never use `~~~`.", "at most 12 words")
CODE_FACT_RULES = ("Put no fenced block outside `Relevant flows`.",
                   "Write a `### ` heading only under `Relevant flows`.")
WEB_FACT_RULES = ("Put no fenced block and no `### ` heading in the fact file.",)
READ_RULES = ("Read the source only. Change no file of the source.",
              "Run no build, no test, no install and no git command that changes the repository.",
              "Cite only a line that you read from the disk.",
              "Never copy a password, a token or a key into a snippet or a fact.")
WEB_RULES = ("Cite only a page that you fetched.", "Copy the snippet from the fetched page.")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_sdr(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(SDR / "scripts" / "sdr.py"), *map(str, args)],
                          capture_output=True, text=True, timeout=60)


def lint(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "skills/ste/scripts/ste_lint.py", str(path)], cwd=REPO,
                          capture_output=True, text=True, timeout=60)


def _split_fences(text: str) -> list[tuple[str, bool]]:
    """(line, inside) for each line of text. `inside` is true for the fence lines too. A fence opens with 3 or more
    backticks and closes with a line of the same run, so a shorter run inside it is body text."""
    marked, run = [], None
    for line in text.splitlines():
        found = FENCE_LINE.match(line)
        if run is None:
            if found:
                run = found.group(1)
            marked.append((line, run is not None))
        else:
            marked.append((line, True))
            if found and line.strip() == run:
                run = None
    return marked


def headings(text: str) -> list[str]:
    """The titles of the `## ` lines outside fenced blocks, in order."""
    return [line[3:].strip() for line, inside in _split_fences(text) if not inside and line.startswith("## ")]


def section(text: str, title: str) -> str:
    """The text under `## <title>` up to the next `## ` line outside a fence; "" when there is no such heading."""
    body, found = [], False
    for line, inside in _split_fences(text):
        if not inside and line.startswith("## "):
            if found:
                break
            found = line[3:].strip() == title
        elif found:
            body.append(line)
    return "\n".join(body)


def squash(text: str) -> str:
    return " ".join(text.split())


def fenced_blocks(text: str) -> list[str]:
    """The bodies of the fenced blocks. A block that nests a shorter fence keeps its lines in its body."""
    blocks, body, run = [], [], None
    for line in text.splitlines():
        found = FENCE_LINE.match(line)
        if run is None:
            if found:
                run, body = found.group(1), []
        elif found and line.strip() == run:
            blocks.append("\n".join(body))
            run = None
        else:
            body.append(line)
    return blocks


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


class SearchPromptCase(unittest.TestCase):
    def test_each_search_prompt_has_exactly_its_placeholders(self):
        for name in SEARCH_PROMPTS:
            self.assertEqual(set(PLACEHOLDER.findall(read(PROMPTS / name))), PLACEHOLDERS[name], name)

    def test_each_search_prompt_has_its_sections(self):
        for name in SEARCH_PROMPTS:
            self.assertEqual(headings(read(PROMPTS / name)), list(SEARCH_SECTIONS), name)

    def test_each_search_prompt_runs_check_facts(self):
        for name in SEARCH_PROMPTS:
            check = section(read(PROMPTS / name), "Check")
            commands = [line.strip() for body in fenced_blocks(check) for line in body.splitlines()]
            self.assertIn(CHECK_FACTS, commands, name)
            self.assertIn("sdr: ok", squash(check), name)
            self.assertIn("3 rounds", squash(check), name)

    def test_each_search_prompt_ends_with_a_result_line(self):
        for name in SEARCH_PROMPTS:
            result = section(read(PROMPTS / name), "Result")
            for line in RESULT_LINES:
                self.assertIn(line, result, name)

    def test_the_code_fact_file_skeleton(self):
        text = read(PROMPTS / "search-code.md")
        skeletons = [body for body in fenced_blocks(text) if body.lstrip().startswith("# Facts: {fact_id}")]
        self.assertEqual(len(skeletons), 1, skeletons)
        self.assertEqual(re.findall(r"^## (.+)$", skeletons[0], re.M), list(sdr.FACTS_TITLES))
        self.assertIn("flowchart TD", skeletons[0])

    def test_the_web_fact_file_skeleton(self):
        text = read(PROMPTS / "search-web.md")
        skeletons = [body for body in fenced_blocks(text) if body.lstrip().startswith("# Facts: {fact_id}")]
        self.assertEqual(len(skeletons), 1, skeletons)
        self.assertEqual(re.findall(r"^## (.+)$", skeletons[0], re.M), list(sdr.FACTS_REQUIRED))

    def test_fact_rules_in_each_prompt(self):
        rules = {"search-code.md": SHARED_FACT_RULES + CODE_FACT_RULES,
                 "search-web.md": SHARED_FACT_RULES + WEB_FACT_RULES}
        for name, wanted in rules.items():
            form = squash(section(read(PROMPTS / name), "The fact file"))
            for rule in wanted:
                self.assertIn(rule, form, name)

    def test_the_code_searcher_reads_only(self):
        rules = squash(section(read(PROMPTS / "search-code.md"), "Rules"))
        for rule in READ_RULES:
            self.assertIn(rule, rules)
        self.assertIn("`.codegraph/`", rules)

    def test_the_web_searcher_cites_fetched_pages(self):
        rules = squash(section(read(PROMPTS / "search-web.md"), "Rules"))
        for rule in WEB_RULES:
            self.assertIn(rule, rules)

    def test_each_search_prompt_lints_clean(self):
        for name in SEARCH_PROMPTS:
            run = lint(PROMPTS / name)
            lines = run.stdout.strip().splitlines()
            self.assertTrue(lines and lines[-1].startswith("0 errors"), (name, run.stdout, run.stderr))


if __name__ == "__main__":
    unittest.main()
