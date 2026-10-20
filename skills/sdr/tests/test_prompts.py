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
  table row.

ReviewerPromptCase ties the two reviewer prompts, consilium.md and review.md, to spec sections 7.4 and 7.6. Both are
templates, so PLACEHOLDERS pins their names in braces too (all four prompts have a key after this case). consilium.md
holds the sections CONSILIUM_SECTIONS. Its report form, CONSILIUM_REPORT, is one fenced block that the main session
copies into the record, so the block is pinned line by line, with `{role}` in its title line. review.md adapts the
gate 1 reviewer of the lesson (explain/lesson/review-page.md): it holds the sections REVIEW_SECTIONS, five checks and
the round rules REVIEW_ROUND_2. Its verification read keys on `-round-2.md` alone, because an sdr review has three
rounds at most (spec 7.6). The three consilium reviewers run in parallel into one directory, and the cold reviewer
runs after them, so each reviewer prompt closes the directory of `sdr.md` and its parent (CLOSED_TEXT, CLOSED_TAILS):
a reviewer reads no report of another reviewer, and the cold reviewer reads no consilium report.

- test_each_reviewer_prompt_has_exactly_its_placeholders: add or drop a name in braces in either prompt, rename one,
  or write a Mermaid rhombus node such as `a{x}`.
- test_each_reviewer_prompt_has_its_sections: rename, drop, add or reorder a level-2 section, or put a `## ` line of
  the report form outside a fence.
- test_the_consilium_report_form: change a line of the report form (the title with `{role}`, an `## opt-<x>` line, a
  `dispute` or `missing` line, `## Preferred`, or either last line), drop one, or write a second fenced block that
  starts with the title line.
- test_the_consilium_needs_evidence: drop or reword the sentence `A finding without evidence is not a finding.`, or
  move it out of the section Judge.
- test_the_consilium_role_is_filled: drop `{brief}` from the section Your role, or `{role}` from the section Your
  task.
- test_the_review_lists_five_checks: add or drop a numbered check in the section Checks, or number them out of
  order.
- test_round_2_rules_before_it_hunts: reword or drop one of the three sentences of REVIEW_ROUND_2, move one out of
  the section Round 2, or name `-round-3.md` there.
- test_each_reviewer_reads_only_its_inputs: reword or drop CLOSED_TEXT, or its tail in CLOSED_TAILS, in either
  prompt, or move it out of the section Inputs.
- test_the_review_report_needs_a_quoted_line: drop or reword the sentence `A finding without a quoted source line is
  not a finding.` or the verdict pair from the section Report.
- test_the_review_hunts_with_an_exit: drop the words `zero findings` from the section Hunt.
- test_each_reviewer_prompt_lints_clean: write a sentence of 26 words or more outside a fenced block, a heading and a
  table row.

SkillCase ties SKILL.md, the procedure that the main session follows for `/sdr`, to sdr.py and to the four prompts.
Its level-2 sections are SKILL_TITLES: five sections of rules, then one section for each stage of sdr.STAGES that
it covers, in order. Task 5 of the plan appends the last three. The section The record shows the record in one
fenced block with a four-backtick outer fence, which nests the Mermaid fence, so a `## ` line of the record is no
heading of SKILL.md. The fill table under FILL_HEADER has one row for each name in braces of the prompts, and its
Prompts cell names the prompts that hold the name, so the table and PLACEHOLDERS cannot drift. The role table under
ROLE_HEADER gives the briefs of spec section 7.4 word for word (ROLE_BRIEFS). Each word after `sdr.py ` is a command
of sdr.USAGE (sdr_commands), and the three commands that the author runs before the page are pinned line by line.
The consilium section turns the last two lines of CONSILIUM_REPORT into the `- preferred:` and `- verdict:` lines
that sdr.py reads, and a `dispute` line into CORRECTION_FORM. SKILL_TEXTS pins the exact texts: among them
ID_SUFFIX, which keeps two code directories with one basename apart, RESUME_STOP, which asks for Stop 1 again
after a session that died at Stop 1, and ROOT_PARENT, which moves the root of one code directory to its parent, as
the course rung of `explain` does (spec section 9).

- test_frontmatter: change, drop or add a line of the frontmatter, or put a line before it.
- test_titles: rename, drop, add or reorder a level-2 section, or put a `## ` line of the record outside its fence.
- test_stage_sections_follow_the_stages: give a stage section a title that is not its stage, or swap two of them.
- test_stages_table_lists_the_nine_stages: drop, add or reorder a row of the stages table, or change the stage
  name in its first cell.
- test_the_record_block_has_the_sections: drop, rename or reorder a `## ` line of the record block, change its line
  2, or write a second block that starts with `# SDR: `.
- test_fill_table_matches_the_prompts: drop or repeat a row of the fill table, leave a cell empty, or name a prompt
  in the Prompts cell of a name that the prompt does not hold (or leave out one that holds it).
- test_skill_names_each_prompt_file: drop the `<skill-dir>/prompts/<name>` path of a prompt from SKILL.md, name a
  prompt file that does not exist, or add a prompt file that PLACEHOLDERS does not list.
- test_role_briefs: change a word of a brief, or rename, drop, add or reorder a role.
- test_skill_names_only_real_sdr_commands: write a word after `sdr.py ` that is not a command of sdr.USAGE.
- test_skill_commands: change a word of SKELETON, CHECK or CHECK_FACTS_AUTHOR, or take it out of its fenced block.
- test_the_consilium_copies_the_report: drop the word `dispute` or `missing` from the section Consilium, change
  CORRECTION_FORM there, or drop either last line of the report form or its copy with `- ` in front.
- test_skill_texts: reword or drop one of SKILL_TEXTS.
- test_skill_lints_clean: write a sentence of 26 words or more outside the frontmatter, a fenced block, a heading
  and a table row.
- test_install_links_sdr: rename SKILL.md, or change install.sh so that it links no skills/sdr."""

import os
import re
import subprocess
import sys
import tempfile
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
    "consilium.md": frozenset({"role", "brief", "files", "root", "report"}),
    "review.md": frozenset({"question", "files", "root", "report", "previous"}),
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

REVIEWER_PROMPTS = ("consilium.md", "review.md")
CONSILIUM_SECTIONS = ("Your task", "Inputs", "Your role", "Judge", "Report")
REVIEW_SECTIONS = ("Your task", "Inputs", "Hunt", "Checks", "Round 2", "Report")
CLOSED_TEXT = "Under the directory of `sdr.md`, and under its parent directory, read no file except"
CLOSED_TAILS = {"consilium.md": "the files listed below.",
                "review.md": "the files listed below and the report that Round 2 names."}
REVIEW_ROUND_2 = ("If `{previous}` is `none`, this is round 1: skip this section.",
                  "Before you hunt, rule each finding of that report `resolved` or `open`, "
                  "and quote the current source line.",
                  "If the name of `{previous}` ends in `-round-2.md`, this is a verification read: "
                  "rule its findings and hunt for nothing new.")
CONSILIUM_REPORT = """# Consilium: {role}
## opt-<x>
- verdict: <one sentence>
- dispute <id>: <old> -> <new> — <evidence>
## Missing requirements
- missing <FR|NFR>: <requirement> — <evidence>
## Preferred
<why, in one paragraph>
verdict: <one sentence>
preferred: opt-<x>"""

FRONTMATTER = (
    "---",
    "name: sdr",
    "description: Use when the user invokes /sdr — drive one system design review, from a question to a checked "
    "decision record and a page.",
    "disable-model-invocation: true",
    'argument-hint: "<question> [<code-dir> ...] | <sdr-dir>"',
    "---",
)
SKILL_TITLES = ("Contract", "Output directory", "Stages", "The record", "Subagents",
                "Intake", "Explore", "Frame", "Options", "Consilium", "Decide")
STAGES_HEADER = "| Stage | Who | What | Ends with |"
FILL_HEADER = "| Name | Prompts | Fill with |"
ROLE_HEADER = "| Role | Brief |"
ROLE_BRIEFS = (  # spec section 7.4, word for word
    ("architect", "Fit with the existing architecture and its ownership boundaries: which service owns which fact, "
                  "coupling, how each option evolves when the next source system arrives."),
    ("operator", "What breaks at run time: ordering, duplicates, retries, replay, partial failure, back-pressure, "
                 "migration from the legacy flow, how an operator sees and fixes a stuck case."),
    ("sceptic", "Attack the leading option and the frame: a requirement that is wrong or missing, an option written "
                "to lose, a cheaper option that nobody wrote, an assumption that carries the decision."),
)
SKELETON = ('python3 <skill-dir>/scripts/sdr.py skeleton <sdr-dir> --question "<question>" --root <root> '
            "[--code <code-dir>]...")
CHECK = "python3 <skill-dir>/scripts/sdr.py check <sdr-dir>"
CHECK_FACTS_AUTHOR = "python3 <skill-dir>/scripts/sdr.py check-facts <sdr-dir>/explore/<file> --root <root>"
CORRECTION_FORM = "- correction opt-<x> <id>: <old> -> <new> — accepted|rejected: <reason>"
ID_SUFFIX = ("When two code directories give the same `<id>`, add `-2`, `-3` and so on to the later ones, "
             "in argument order.")
RESUME_STOP = "On a resume at stage `frame`, do Stop 1 again before the options stage."
RESUME_SENTENCE = "One argument that is a directory holding `sdr.md` resumes that run. It is never a code directory."
ROOT_PARENT = "If that directory is a code directory, use its parent directory."  # spec 9, as explain's course rung
RECORD_RULES = ("Put no fenced block outside `Options`.",
                "Never use `~~~`.",
                "Write a `### ` heading only under `Options` and `Consilium`.",
                "Each line of a cited section is one `- ` line.",
                "The record's prose is not linted. Code names are in backticks.")
SKILL_TEXTS = (
    "$ARGUMENTS", "`usage: /sdr <question> [<code-dir> ...]`", "<skill-dir>/../explain", "<skill-dir>/../ste/SKILL.md",
    "~/karpathy/out/YYYY-MM-DD-HHMMSS-sdr-<slug>/", "explore/code-<id>.md", "explore/web-<n>.md",
    "consilium/<role>.md", "review/review-round-<k>.md", "diagrams/<id>.mmd", "Stop 1", "Stop 2",
    "target: unknown", "source: assumption", "source: consilium <role>", "`task`", "`general`", "never a fork",
    "A filled prompt holds no name in braces.", *RECORD_RULES, RESUME_SENTENCE, ID_SUFFIX, RESUME_STOP, ROOT_PARENT,
)
SDR_COMMAND = re.compile(r"sdr\.py (\S+)")
INSTALL_BASH = "/bin/bash"  # the bash of macOS is 3.2; install.sh must run there too


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


def sdr_commands(text: str) -> set[str]:
    """The words after each `sdr.py ` of text, without the backticks and punctuation around them."""
    return {word.strip("`.,;:()") for word in SDR_COMMAND.findall(text)}


def table_rows(text: str, header: str) -> list[tuple[str, ...]]:
    """The stripped cells of each row of the table whose header line is `header`, after its `|---|` line, up to
    the first line that does not start with `|`; [] when no line is `header`."""
    lines = text.splitlines()
    if header not in lines:
        return []
    rows = []
    for line in lines[lines.index(header) + 2 :]:
        if not line.startswith("|"):
            break
        rows.append(tuple(cell.strip() for cell in line.strip().strip("|").split("|")))
    return rows


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


class ReviewerPromptCase(unittest.TestCase):
    def test_each_reviewer_prompt_has_exactly_its_placeholders(self):
        for name in REVIEWER_PROMPTS:
            self.assertEqual(set(PLACEHOLDER.findall(read(PROMPTS / name))), PLACEHOLDERS[name], name)

    def test_each_reviewer_prompt_has_its_sections(self):
        wanted = {"consilium.md": CONSILIUM_SECTIONS, "review.md": REVIEW_SECTIONS}
        for name, titles in wanted.items():
            self.assertEqual(headings(read(PROMPTS / name)), list(titles), name)

    def test_the_consilium_report_form(self):
        text = read(PROMPTS / "consilium.md")
        forms = [body for body in fenced_blocks(text) if body.lstrip().startswith("# Consilium: {role}")]
        self.assertEqual(len(forms), 1, forms)
        self.assertEqual([line.strip() for line in forms[0].splitlines()], CONSILIUM_REPORT.splitlines())

    def test_the_consilium_needs_evidence(self):
        judge = squash(section(read(PROMPTS / "consilium.md"), "Judge"))
        self.assertIn("A finding without evidence is not a finding.", judge)

    def test_the_consilium_role_is_filled(self):
        text = read(PROMPTS / "consilium.md")
        self.assertIn("{brief}", squash(section(text, "Your role")))
        self.assertIn("{role}", section(text, "Your task"))

    def test_the_review_lists_five_checks(self):
        checks = section(read(PROMPTS / "review.md"), "Checks")
        self.assertEqual(re.findall(r"^(\d+)\. ", checks, re.M), ["1", "2", "3", "4", "5"])

    def test_round_2_rules_before_it_hunts(self):
        rules = squash(section(read(PROMPTS / "review.md"), "Round 2"))
        for sentence in REVIEW_ROUND_2:
            self.assertIn(sentence, rules)
        self.assertNotIn("-round-3.md", rules)

    def test_each_reviewer_reads_only_its_inputs(self):
        for name in REVIEWER_PROMPTS:
            inputs = squash(section(read(PROMPTS / name), "Inputs"))
            self.assertIn(CLOSED_TEXT + " " + CLOSED_TAILS[name], inputs, name)

    def test_the_review_report_needs_a_quoted_line(self):
        report = squash(section(read(PROMPTS / "review.md"), "Report"))
        self.assertIn("A finding without a quoted source line is not a finding.", report)
        self.assertIn("`verdict: ok` or `verdict: fix`", report)

    def test_the_review_hunts_with_an_exit(self):
        self.assertIn("zero findings", squash(section(read(PROMPTS / "review.md"), "Hunt")))

    def test_each_reviewer_prompt_lints_clean(self):
        for name in REVIEWER_PROMPTS:
            run = lint(PROMPTS / name)
            lines = run.stdout.strip().splitlines()
            self.assertTrue(lines and lines[-1].startswith("0 errors"), (name, run.stdout, run.stderr))


class SkillCase(unittest.TestCase):
    def setUp(self):
        self.text = read(SKILL_MD) if SKILL_MD.is_file() else ""  # no file: each test fails on its own assertion

    def test_frontmatter(self):
        self.assertEqual(tuple(self.text.splitlines()[: len(FRONTMATTER)]), FRONTMATTER)

    def test_titles(self):
        self.assertEqual(headings(self.text), list(SKILL_TITLES))

    def test_stage_sections_follow_the_stages(self):
        titles = headings(self.text)
        self.assertEqual([title.lower() for title in titles[5:]], list(sdr.STAGES[: len(titles) - 5]))

    def test_stages_table_lists_the_nine_stages(self):
        rows = table_rows(section(self.text, "Stages"), STAGES_HEADER)
        self.assertEqual([row[0] for row in rows], ["`%s`" % stage for stage in sdr.STAGES], rows)

    def test_the_record_block_has_the_sections(self):
        blocks = [body for body in fenced_blocks(section(self.text, "The record")) if body.startswith("# SDR: ")]
        self.assertEqual(len(blocks), 1, blocks)
        lines = blocks[0].splitlines()
        self.assertEqual([line for line in lines if line.startswith("## ")], ["## " + title for title in sdr.SECTIONS])
        self.assertEqual(lines[1], "stage: <stage>")

    def test_fill_table_matches_the_prompts(self):
        rows = table_rows(self.text, FILL_HEADER)
        heads = [re.fullmatch(r"`\{([A-Za-z_]+)\}`", row[0]) for row in rows]
        self.assertTrue(rows and all(heads), rows)
        names = [head.group(1) for head in heads]
        self.assertEqual(len(names), len(set(names)), names)
        self.assertEqual(set(names), set().union(*PLACEHOLDERS.values()))
        found: dict[str, set[str]] = {}
        for name, row in zip(names, rows):
            self.assertEqual(len(row), 3, row)
            self.assertTrue(row[2], name)
            for prompt in re.findall(r"`([^`]+)`", row[1]):
                found.setdefault(prompt, set()).add(name)
        self.assertEqual({prompt: frozenset(held) for prompt, held in found.items()}, PLACEHOLDERS)

    def test_skill_names_each_prompt_file(self):
        names = sorted(path.name for path in PROMPTS.glob("*.md"))
        self.assertEqual(names, sorted(PLACEHOLDERS))
        for name in names:
            self.assertIn("<skill-dir>/prompts/" + name, self.text)
        for name in re.findall(r"<skill-dir>/prompts/([\w.-]+)", self.text):
            self.assertTrue((PROMPTS / name).is_file(), name)

    def test_role_briefs(self):
        self.assertEqual(table_rows(self.text, ROLE_HEADER), [("`%s`" % role, brief) for role, brief in ROLE_BRIEFS])
        self.assertEqual([role for role, _ in ROLE_BRIEFS], list(sdr.ROLES))

    def test_skill_names_only_real_sdr_commands(self):
        found = sdr_commands(self.text)
        self.assertTrue(found)
        self.assertLessEqual(found, sdr_commands(sdr.USAGE), found - sdr_commands(sdr.USAGE))

    def test_skill_commands(self):
        commands = [line.strip() for body in fenced_blocks(self.text) for line in body.splitlines()]
        for command in (SKELETON, CHECK, CHECK_FACTS_AUTHOR):
            self.assertIn(command, commands)

    def test_the_consilium_copies_the_report(self):
        consilium = squash(section(self.text, "Consilium"))
        for text in ("dispute", "missing", CORRECTION_FORM):
            self.assertIn(text, consilium)
        for line in CONSILIUM_REPORT.splitlines()[-2:]:
            self.assertIn("`%s`" % line, consilium)
            self.assertIn("`- %s`" % line, consilium)

    def test_skill_texts(self):
        text = squash(self.text)
        for wanted in SKILL_TEXTS:
            self.assertIn(wanted, text)

    def test_skill_lints_clean(self):
        run = lint(SKILL_MD)
        lines = run.stdout.strip().splitlines()
        self.assertTrue(lines and lines[-1].startswith("0 errors"), (run.stdout, run.stderr))

    def test_install_links_sdr(self):
        with tempfile.TemporaryDirectory() as home:
            run = subprocess.run([INSTALL_BASH, str(REPO / "install.sh"), "--claude"],
                                 env={"HOME": home, "PATH": "/usr/bin:/bin"}, capture_output=True, text=True,
                                 timeout=60)
            self.assertEqual(run.returncode, 0, run.stderr)
            link = Path(home) / ".claude" / "skills" / "sdr"
            self.assertTrue(link.is_symlink(), (link, run.stdout))
            self.assertEqual(link.resolve(), SDR)


if __name__ == "__main__":
    unittest.main()
