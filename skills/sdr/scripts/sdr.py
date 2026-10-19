#!/usr/bin/env python3
"""Design review record tool for `sdr`: writes the skeleton of a record and checks it.

Usage: sdr.py skeleton <sdr-dir> --question <text> --root <root> [--code <dir>]...
       sdr.py check <sdr-dir> [--root <root>]
       sdr.py check-facts <file> --root <root>
       sdr.py matrix <sdr-dir>
skeleton writes <sdr-dir>/sdr.md at stage intake and refuses to overwrite it. check and check-facts print one
finding per line, then `sdr: ok` or `sdr: <n> findings`. matrix writes the requirement x option table into the
`<div class="sdr-matrix">` block of <sdr-dir>/index.html; from stage `page` on, check finds a table that is stale.
Exit 0 on success, 1 on findings, 2 on a usage error or an unreadable file, root or code dir. Usage text and
every exit-2 line go to stderr; findings and the summary go to stdout.
"""

import argparse
import os
import re
import sys
from html import escape
from typing import NamedTuple, NoReturn

# The scripts of `explain` sit beside this skill; the real path of this file makes a symlinked install work.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "explain", "scripts"))

import cite_check  # noqa: E402
import onboard  # noqa: E402

USAGE = (
    "usage: sdr.py skeleton <sdr-dir> --question <text> --root <root> [--code <dir>]...\n"
    "       sdr.py check <sdr-dir> [--root <root>]\n"
    "       sdr.py check-facts <file> --root <root>\n"
    "       sdr.py matrix <sdr-dir>\n"
)
STAGES = ("intake", "explore", "frame", "options", "consilium", "decide", "page", "review", "done")
SECTIONS = (
    "Problem",
    "Context",
    "Functional requirements",
    "Non-functional requirements",
    "Constraints",
    "Non-goals",
    "Options",
    "Consilium",
    "Decision",
    "Open questions",
    "Not covered",
)
# The first stage that reaches each section: before it the section holds `pending`, from it on real content.
REACHED = {
    "Problem": "frame",
    "Context": "frame",
    "Functional requirements": "frame",
    "Non-functional requirements": "frame",
    "Constraints": "frame",
    "Non-goals": "frame",
    "Options": "frame",
    "Consilium": "consilium",
    "Decision": "decide",
    "Open questions": "decide",
    "Not covered": "decide",
}
ROLES = ("architect", "operator", "sceptic")
SOURCES = ("user", "code", "web", "assumption")  # "consilium <role>" is the fifth form
PENDING = "pending"
HEADER_LINES = 4  # the title, `stage:`, `root:` and `code:` lines; the sections follow
FENCE = "```"
TITLE_PREFIX = "# SDR: "
STAGE_LINE = re.compile(r"stage: (\S+)\s*")
ROOT_LINE = re.compile(r"root: (\S.*?)\s*")
CODE_PREFIX = "code: "
CODE_NONE = "none"
URL = re.compile(r"https?://\S+")
PATH_CITE = re.compile(r"(.+):([0-9]+)")
REQUIREMENT_ID = re.compile(r"((FR|NFR)-[0-9]+):(.*)")
TARGET_FIELD = re.compile(r"target:\s*(.*)")
SOURCE_FIELD = re.compile(r"source:\s*(\S.*)")
REQUIREMENT_SECTIONS = (("Functional requirements", "FR"), ("Non-functional requirements", "NFR"))
FACTS_PREFIX = "# Facts: "
FACTS_TITLES = ("Shape", "Relevant flows", "Facts", "Unknowns")
FACTS_REQUIRED = ("Facts", "Unknowns")
NONE_BULLET = "- none"
MARKS = ("meets", "partial", "fails")
OPTION_KEYS = ("changes", "pros", "cons", "risks", "effort", "reversibility")
MIN_OPTIONS = 3
OPTION_HEADING = re.compile(r"(opt-[a-z]): (\S.*)")
OPTION_KEY_LINES = {key: re.compile(r"- %s:(.*)" % key) for key in OPTION_KEYS}
FIT_PREFIX = "- fit "
FIT_LINE = re.compile(r"- fit (?P<id>[^:\s]+): (?P<mark>\S+)(?P<rest>.*)")
FIT_REASON = re.compile(r" — \S")
PREFERRED_LINE = re.compile(r"- preferred:\s*(\S.*)")
VERDICT_LINE = re.compile(r"- verdict:\s*(\S.*)")
CORRECTION_PREFIX = "- correction"
CORRECTION_LINE = re.compile(r"- correction (opt-[a-z]) (\S+): (\S+) -> (\S+) — (accepted|rejected): \S.*")
CHOICE_LINE = re.compile(r"- choice:\s*(\S.*)")
WHY_LINE = re.compile(r"- why:\s*(\S.*)")
WHY_NOT_LINE = re.compile(r"- why not (opt-[a-z]): \S.*")
DISSENT_PREFIX = "- dissent"
DISSENT_LINE = re.compile(r"- dissent: (\S+) preferred (opt-[a-z]): \S.*")
REVISIT_LINE = re.compile(r"- revisit when: \S.*")
PAGE = "index.html"  # the page beside sdr.md
PAGE_STAGE = "page"  # from this stage on, check compares the matrix of the page with the record
MATRIX_OPEN = '<div class="sdr-matrix">'
MATRIX_TOKEN = re.compile(r"<div\b|</div>")
BACKTICK_SPAN = re.compile(r"`([^`]+)`")
SYMBOLS = {"meets": "✓", "partial": "◐", "fails": "✗"}
# The page's `--fill` is the background of inline `code`; the chosen column gets it, and its header gets weight.
CHOSEN_CSS = ("table.matrix .chosen { background: var(--fill); }\n"
              "table.matrix th.chosen { color: var(--ink); font-weight: 700; }")


class SdrError(Exception):
    """One output line (str of the error) and the exit code it stands for."""

    def __init__(self, line: str, code: int = 2) -> None:
        super().__init__(line)
        self.code = code


class Block(NamedTuple):
    heading: str  # the `### ` heading text
    line: int  # 1-based line of the heading
    lines: list[tuple[int, str]]  # (1-based line, stripped text) of the non-blank lines outside fences
    diagrams: list[onboard.Diagram]


class Section(NamedTuple):
    title: str
    line: int
    lines: list[tuple[int, str]]  # the section's own lines: outside fences and outside its blocks
    blocks: list[Block]
    diagrams: list[onboard.Diagram]  # the Mermaid blocks that stand outside any `### ` block


class Record(NamedTuple):
    question: str | None
    stage: str | None  # the word after `stage: `, kept even when it is not in STAGES
    root: str | None  # None unless an absolute path
    code: list[str] | None  # [] for `code: none`; None unless every dir is absolute
    header: list[str]  # lines 1 to 4, padded with "" when the file is shorter
    sections: list[Section]

    def section(self, title: str) -> Section | None:
        return next((section for section in self.sections if section.title == title), None)


class Fact(NamedTuple):
    n: int  # 1-based inside its section or flow
    line: int  # 1-based line in the file
    fact: str
    where: str | None  # `<path>:<line>` or a URL; None unless the line holds a well-formed cite
    snippet: str | None


class Requirement(NamedTuple):
    ident: str  # FR-<k> or NFR-<k>
    text: str  # the words after `<ident>: `, without the `|` fields
    n: int  # 1-based index of the bullet in its section
    line: int  # 1-based line in the record


class Option(NamedTuple):
    ident: str  # opt-<letter>
    name: str  # the words after `opt-<letter>: `
    block: Block
    fits: dict[str, str]  # requirement id -> mark of its first fit line with a mark in MARKS


def _close_fence(fence: tuple, scope: Block | Section | None) -> None:
    """A closed ```mermaid block becomes a Diagram of its block or section; other blocks are dropped."""
    line, info, body = fence
    if info == "mermaid" and scope is not None:
        text = "\n".join(body)
        scope.diagrams.append(onboard.Diagram(line, onboard.mermaid_kind(text), onboard.mermaid_nodes(text), text))


def read_sections(lines: list[str], first: int) -> list[Section]:
    """The `## ` sections of lines[first:], each with its own lines, its `### ` blocks and its Mermaid blocks.

    A fenced block hides its lines from every rule. A section or block ends at the next heading."""
    sections = []
    scope = None  # the Block or Section that takes the next line
    fence = None  # (line, info, body) of the open fenced block
    for index in range(first, len(lines)):
        number, line = index + 1, lines[index]
        if fence is not None:
            if line.startswith(FENCE):
                _close_fence(fence, scope)
                fence = None
            else:
                fence[2].append(line)
        elif line.startswith(FENCE):
            fence = (number, line[len(FENCE) :].strip(), [])
        elif line.startswith("## "):
            scope = Section(line[3:].strip(), number, [], [], [])
            sections.append(scope)
        elif line.startswith("### ") and sections:
            scope = Block(line[4:].strip(), number, [], [])
            sections[-1].blocks.append(scope)
        elif line.strip() and scope is not None:
            scope.lines.append((number, line.strip()))
    if fence is not None:
        _close_fence(fence, scope)
    return sections


def _question_of(line: str) -> str | None:
    if not line.startswith(TITLE_PREFIX):
        return None
    return line[len(TITLE_PREFIX) :].strip() or None


def _stage_of(line: str) -> str | None:
    found = STAGE_LINE.fullmatch(line)
    return found.group(1) if found else None


def _root_of(line: str) -> str | None:
    found = ROOT_LINE.fullmatch(line)
    return found.group(1) if found and os.path.isabs(found.group(1)) else None


def _code_of(line: str) -> list[str] | None:
    if not line.startswith(CODE_PREFIX):
        return None
    text = line[len(CODE_PREFIX) :].strip()
    if text == CODE_NONE:
        return []
    dirs = [path.strip() for path in text.split("; ")]
    return dirs if all(os.path.isabs(path) for path in dirs) else None


def parse_record(text: str) -> Record:
    """The record of a text; a byte order mark and CRLF line ends read as in an LF file."""
    lines = text.removeprefix("﻿").splitlines()
    header = (lines[:HEADER_LINES] + [""] * HEADER_LINES)[:HEADER_LINES]
    return Record(
        _question_of(header[0]), _stage_of(header[1]), _root_of(header[2]), _code_of(header[3]),
        header, read_sections(lines, HEADER_LINES),
    )


def _read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError) as error:
        reason = getattr(error, "strerror", None) or error
        raise SdrError("sdr: cannot read %s: %s" % (path, reason)) from error


def read_record(sdr_dir: str) -> Record:
    return parse_record(_read_text(os.path.join(sdr_dir, "sdr.md")))


def reached(stage: str, at: str) -> bool:
    """Whether a record at `stage` has finished the stage `at` or gone past it."""
    return STAGES.index(stage) >= STAGES.index(at)


def _header_lines(record: Record) -> list[str]:
    """The `header:` lines, one per fault of lines 1 to 4."""
    lines = []
    if record.question is None:
        lines.append('header: line 1 is not "# SDR: <question>"')
    if record.stage is None:
        lines.append('header: line 2 is not "stage: <name>"')
    elif record.stage not in STAGES:
        lines.append("header: unknown stage %s" % record.stage)
    if record.root is None:
        lines.append('header: line 3 is not "root: <absolute path>"')
    if record.code is None:
        lines.append('header: line 4 is not "code: <absolute dirs>" or "code: none"')
    return lines


def _section_lines(sections: list[Section], titles: tuple[str, ...], required: tuple[str, ...]) -> list[str]:
    """The `section:` lines: required titles that are missing in canonical order, then repeats, order and
    unknown titles in record order."""
    present = {section.title for section in sections}
    lines = ["section: missing %s" % title for title in titles if title in required and title not in present]
    seen, highest = set(), -1
    for section in sections:
        if section.title in seen:
            lines.append("section: %s twice" % section.title)
            continue
        seen.add(section.title)
        if section.title not in titles:
            lines.append("section: unknown %s" % section.title)
            continue
        index = titles.index(section.title)
        if index < highest:
            lines.append("section: %s out of order" % section.title)
        highest = max(highest, index)
    return lines


def _is_pending(section: Section) -> bool:
    return not section.blocks and [text for _, text in section.lines] == [PENDING]


def _is_empty(section: Section) -> bool:
    return not section.lines and not section.blocks


def _stage_lines(record: Record) -> list[str]:
    """The `section:` lines of the stage: a section the stage has not reached must be pending, a reached one
    must not be pending or empty. Only the first section of a title counts."""
    lines = []
    for title in SECTIONS:
        section = record.section(title)
        if section is None:
            continue
        if not reached(record.stage, REACHED[title]):
            if not _is_pending(section):
                lines.append("section: %s not pending at stage %s" % (title, record.stage))
        elif _is_pending(section):
            lines.append("section: %s pending at stage %s" % (title, record.stage))
        elif _is_empty(section):
            lines.append("section: %s empty, write none" % title)
    return lines


def _cite_of(where: str, snippet: str) -> tuple[str, str] | None:
    """(where, snippet) when they form a cite: a URL or `<path>:<line>` with line >= 1, and a snippet."""
    where, snippet = where.strip(), snippet.strip()
    if not snippet:
        return None
    if URL.fullmatch(where):
        return where, snippet
    found = PATH_CITE.fullmatch(where)
    return (where, snippet) if found and int(found.group(2)) >= 1 else None


def parse_fact(n: int, line: int, text: str) -> Fact:
    """The fact of a `<fact> | <where> | <snippet>` text (a bullet without its `- `); a cite only when well formed."""
    parts = text.split(" | ")
    cite = _cite_of(parts[1], parts[2]) if len(parts) == 3 else None
    return Fact(n, line, parts[0].strip(), *(cite or (None, None)))


def cite_problems(where: str, snippet: str, root: str) -> list[str]:
    """The problems of one cite: a URL is checked for the word count only, a path by `cite_check` under `root`."""
    if URL.fullmatch(where):
        words = len(snippet.split())
        if words > cite_check.MAX_WORDS:
            return ["snippet has %d words (max %d)" % (words, cite_check.MAX_WORDS)]
        return []
    found = PATH_CITE.fullmatch(where)
    if not found:
        return ["no cite"]
    return cite_check.fact_problems(found.group(1), int(found.group(2)), snippet, root)


def _bullets(lines: list[tuple[int, str]]) -> list[tuple[int, int, str]]:
    """(n, line, text) of each `- ` line, text without the `- `; n counts from 1."""
    found = [(number, text[2:]) for number, text in lines if text.startswith("- ")]
    return [(n, number, text) for n, (number, text) in enumerate(found, 1)]


def _split(text: str) -> list[str]:
    return [part.strip() for part in text.split(" | ")]


def _cite_lines(scope: str, facts: list[Fact], root: str) -> list[str]:
    """The `cite <scope>#<n>:` lines of facts: `no cite`, or the problems of the cite."""
    lines = []
    for fact in facts:
        problems = ["no cite"] if fact.where is None else cite_problems(fact.where, fact.snippet, root)
        lines += ["cite %s#%d: %s" % (scope, fact.n, problem) for problem in problems]
    return lines


def _source_problems(fields: list[str]) -> tuple[list[str], tuple[str, str] | None]:
    """(problems, cite) of the fields that start at `source: <value>`: the cite only when it passes form."""
    found = SOURCE_FIELD.fullmatch(fields[0]) if fields else None
    if not found:
        return ["no source"], None
    value, rest = found.group(1).strip(), fields[1:]
    words = value.split()
    if value not in SOURCES and not (len(words) == 2 and words[0] == "consilium" and words[1] in ROLES):
        return ["unknown source %s" % value], None
    if value not in ("code", "web"):
        return (["source %s takes no cite" % value] if rest else []), None
    cite = _cite_of(*rest) if len(rest) == 2 else None
    if cite is None or bool(URL.fullmatch(cite[0])) != (value == "web"):
        return ["source code needs a <path>:<line> cite" if value == "code" else "source web needs a URL cite"], None
    return [], cite


def _requirement_head(kind: str, part: str) -> tuple[str, str] | None:
    """(ident, text) of a `<KIND>-<k>: <text>` part; None when the id is missing or of another kind."""
    found = REQUIREMENT_ID.fullmatch(part)
    return (found.group(1), found.group(3).strip()) if found and found.group(2) == kind else None


def requirements(record: Record) -> list[Requirement]:
    """The requirement lines with a well-formed id of their section's kind and a text: FR lines, then NFR lines."""
    found = []
    for title, kind in REQUIREMENT_SECTIONS:
        section = record.section(title)
        for n, number, text in _bullets(section.lines) if section is not None else []:
            head = _requirement_head(kind, _split(text)[0])
            if head and head[1]:
                found.append(Requirement(head[0], head[1], n, number))
    return found


def _context_lines(section: Section, root: str) -> list[str]:
    facts = [parse_fact(n, number, text) for n, number, text in _bullets(section.lines)]
    return _cite_lines(section.title, facts, root)


def _requirement_lines(section: Section, kind: str, root: str) -> list[str]:
    """The `req` lines of a requirement section, with the cite problems of the lines whose source takes a cite."""
    lines, count = [], 0  # count: the id lines so far, which the sequence rule numbers
    for n, number, text in _bullets(section.lines):
        parts = _split(text)
        head = _requirement_head(kind, parts[0])
        if head is None:
            lines.append("req %s#%d: no id" % (kind, n))
            continue
        count += 1
        ident, words = head
        fields = parts[1:]
        problems = ["expected %s-%d" % (kind, count)] if ident != "%s-%d" % (kind, count) else []
        problems += [] if words else ["no text"]
        if kind == "NFR":
            target = TARGET_FIELD.fullmatch(fields[0]) if fields else None
            fields = fields[1:] if target else fields
            problems += [] if target and target.group(1).strip() else ["no target"]
        source, cite = _source_problems(fields)
        lines += ["req %s: %s" % (ident, problem) for problem in problems + source]
        if cite:
            lines += _cite_lines(section.title, [Fact(n, number, words, *cite)], root)
    return lines


def _constraint_lines(section: Section, root: str) -> list[str]:
    """The `constraint #<n>` lines of Constraints: `<constraint> | source: <value>[ | <cite>]` for each bullet."""
    lines = []
    for n, number, text in _bullets(section.lines):
        parts = _split(text)
        problems, cite = _source_problems(parts[1:])
        lines += ["constraint #%d: %s" % (n, problem) for problem in problems]
        if cite:
            lines += _cite_lines(section.title, [Fact(n, number, parts[0], *cite)], root)
    return lines


def _cited_lines(record: Record, root: str) -> list[str]:
    """The cited-line rules of the frame stage: Context, both requirement sections and Constraints, in that
    order. Only `- ` lines are read, so a section that is missing, pending, empty or `none` has nothing to check."""
    lines = []
    for title in ("Context", "Functional requirements", "Non-functional requirements", "Constraints"):
        section = record.section(title)
        if section is None:
            continue
        if title == "Context":
            lines += _context_lines(section, root)
        elif title == "Constraints":
            lines += _constraint_lines(section, root)
        else:
            lines += _requirement_lines(section, dict(REQUIREMENT_SECTIONS)[title], root)
    return lines


def _fit_lines(block: Block) -> list[tuple[int, re.Match | None]]:
    """(k, match) of each `- fit ` line of a block, k from 1; the match is None for a line of the wrong form."""
    texts = [text for _, text in block.lines if text.startswith(FIT_PREFIX)]
    return [(k, FIT_LINE.match(text)) for k, text in enumerate(texts, 1)]


def _fits(block: Block) -> dict[str, str]:
    """The mark of the first fit line with a mark in MARKS, for each requirement id the lines name."""
    fits: dict[str, str] = {}
    for _, found in _fit_lines(block):
        if found and found.group("mark") in MARKS:
            fits.setdefault(found.group("id"), found.group("mark"))
    return fits


def options(record: Record) -> list[Option]:
    """The blocks of Options with a heading `opt-<letter>: <name>`, in record order; a repeated id keeps its first."""
    section = record.section("Options")
    found: dict[str, Option] = {}
    for block in section.blocks if section is not None else []:
        head = OPTION_HEADING.fullmatch(block.heading)
        if head and head.group(1) not in found:
            found[head.group(1)] = Option(head.group(1), head.group(2), block, _fits(block))
    return list(found.values())


def _requirement_ids(record: Record) -> list[str]:
    """The ids of requirements(record), each once, in order."""
    return list(dict.fromkeys(requirement.ident for requirement in requirements(record)))


def _is_pending_block(block: Block) -> bool:
    return not block.diagrams and [text for _, text in block.lines] == [PENDING]


def _diagram_lines(prefix: str, block: Block) -> list[str]:
    """The faults of the Mermaid blocks of an option: one flowchart of at most MAX_NODES nodes."""
    if not block.diagrams:
        return ["%s: no Mermaid flowchart" % prefix]
    lines = []
    if len(block.diagrams) > 1:
        lines.append("%s: %d Mermaid blocks, more than 1" % (prefix, len(block.diagrams)))
    diagram = block.diagrams[0]
    if diagram.kind != onboard.FLOWCHART:
        lines.append("%s: diagram is not a flowchart" % prefix)
    elif len(diagram.nodes) > onboard.MAX_NODES:
        lines.append("%s: diagram has %d nodes, more than %d" % (prefix, len(diagram.nodes), onboard.MAX_NODES))
    return lines


def _key_empty(key: str, value: str) -> bool:
    """Whether a key line holds nothing; `pros` and `cons` hold nothing without one non-blank `;` item."""
    if key in ("pros", "cons"):
        return not any(item.strip() for item in value.split(";"))
    return not value.strip()


def _key_lines(prefix: str, block: Block) -> list[str]:
    """The faults of the keys of an option, in OPTION_KEYS order: missing, twice, empty."""
    lines = []
    for key in OPTION_KEYS:
        values = [found.group(1) for _, text in block.lines if (found := OPTION_KEY_LINES[key].fullmatch(text))]
        if not values:
            lines.append("%s: missing %s" % (prefix, key))
            continue
        if len(values) > 1:
            lines.append("%s: %s twice" % (prefix, key))
        if any(_key_empty(key, value) for value in values):
            lines.append("%s: %s empty" % (prefix, key))
    return lines


def _fit_rule_lines(name: str, block: Block, wanted: list[str]) -> list[str]:
    """The faults of the fit lines of option `name`: the lines of the wrong form, then each well-formed line
    in order, then each requirement id in `wanted` that no such line names."""
    parsed = _fit_lines(block)
    lines = ['option %s: fit line #%d is not "fit <id>: <mark> — <reason>"' % (name, k)
             for k, found in parsed if found is None]
    seen = []
    for _, found in parsed:
        if found is None:
            continue
        ident, mark = found.group("id"), found.group("mark")
        where = "fit %s/%s" % (name, ident)
        if ident not in wanted:
            lines.append("%s: not a requirement" % where)
        if mark not in MARKS:
            lines.append("%s: mark %s is not meets, partial or fails" % (where, mark))
        if not FIT_REASON.match(found.group("rest")):
            lines.append('%s: no " — <reason>" after the mark' % where)
        if ident in seen:
            lines.append("%s: twice" % where)
        seen.append(ident)
    return lines + ["fit %s/%s: missing" % (name, ident) for ident in wanted if ident not in seen]


def _option_lines(option: Option, stage: str, wanted: list[str]) -> list[str]:
    """The faults of one option: at stage `frame` it must be pending; from `options` on it must be a full block."""
    prefix = "option " + option.ident
    block = option.block
    if not reached(stage, "options"):
        return [] if _is_pending_block(block) else ["%s: not pending at stage frame" % prefix]
    if _is_pending_block(block):
        return ["%s: pending at stage %s" % (prefix, stage)]
    lines = []
    if all(text.startswith("- ") for _, text in block.lines):
        lines.append("%s: no lead paragraph" % prefix)
    return lines + _diagram_lines(prefix, block) + _key_lines(prefix, block) + _fit_rule_lines(
        option.ident, block, wanted)


def _options_lines(record: Record) -> list[str]:
    """The option rules from stage frame on. A missing, pending or empty Options section has nothing to check
    (the stage lines report pending and empty). The `section:` count line comes first, then the heading and
    repeat faults of each block in record order, then the faults of each option in record order."""
    section = record.section("Options")
    if section is None or _is_pending(section) or _is_empty(section):
        return []
    found = options(record)
    lines = []
    if len(found) < MIN_OPTIONS:
        lines.append("section: Options has %d options, fewer than %d" % (len(found), MIN_OPTIONS))
    seen = set()
    for n, block in enumerate(section.blocks, 1):
        head = OPTION_HEADING.fullmatch(block.heading)
        if head is None:
            lines.append('option #%d: heading is not "opt-<letter>: <name>"' % n)
        elif head.group(1) in seen:
            lines.append("option %s: twice" % head.group(1))
        else:
            seen.add(head.group(1))
    wanted = _requirement_ids(record)
    for option in found:
        lines += _option_lines(option, record.stage, wanted)
    return lines


def _values(lines: list[tuple[int, str]], pattern: re.Pattern) -> list[str]:
    """Group 1 of `pattern` for each line of `lines` that it fully matches, in order."""
    return [found.group(1) for _, text in lines if (found := pattern.fullmatch(text))]


def _role_blocks(section: Section) -> dict[str, Block]:
    """The first block of each role of Consilium, in record order."""
    found: dict[str, Block] = {}
    for block in section.blocks:
        if block.heading in ROLES:
            found.setdefault(block.heading, block)
    return found


def _role_block_lines(section: Section) -> list[str]:
    """The faults of the role blocks of Consilium: unknown, repeated and misplaced blocks in record order, then
    each missing role in ROLES order."""
    lines, seen, highest = [], set(), -1
    for block in section.blocks:
        role = block.heading
        if role not in ROLES:
            lines.append("consilium %s: unknown role" % role)
        elif role in seen:
            lines.append("consilium %s: twice" % role)
        else:
            seen.add(role)
            if ROLES.index(role) < highest:
                lines.append("consilium %s: out of order" % role)
            highest = max(highest, ROLES.index(role))
    return lines + ["consilium %s: missing" % role for role in ROLES if role not in seen]


def _correction_lines(prefix: str, k: int, text: str, found: list[Option], ids: list[str]) -> list[str]:
    """The faults of the k-th correction line of a role: its form, the option and the requirement it names, its
    marks, and, for an accepted one, whether the fit line of the option now holds the new mark."""
    parts = CORRECTION_LINE.fullmatch(text)
    prefix = "%scorrection #%d " % (prefix, k)
    if parts is None:
        return [prefix + 'is not "correction opt-<x> <id>: <old> -> <new> — accepted|rejected: <reason>"']
    ident, requirement, old, new, verdict = parts.groups()
    option = next((option for option in found if option.ident == ident), None)
    lines = [] if option is not None else ["%snames %s, not an option" % (prefix, ident)]
    if requirement not in ids:
        lines.append("%snames %s, not a requirement" % (prefix, requirement))
    bad = [mark for mark in (old, new) if mark not in MARKS]
    lines += ["%smark %s is not meets, partial or fails" % (prefix, mark) for mark in bad]
    if lines or verdict != "accepted":
        return lines
    current = option.fits.get(requirement)  # a requirement without a mark in the option is left to the option rules
    if current is not None and current != new:
        lines.append("%saccepted, but fit %s/%s is %s, not %s" % (prefix, ident, requirement, current, new))
    return lines


def _role_lines(role: str, block: Block, found: list[Option], ids: list[str]) -> list[str]:
    """The faults of the first block of a role: `preferred`, `verdict`, then the corrections in order."""
    prefix = "consilium %s: " % role
    lines = []
    preferred = _values(block.lines, PREFERRED_LINE)
    if not preferred:
        lines.append(prefix + "no preferred")
    else:
        if len(preferred) > 1:
            lines.append(prefix + "preferred twice")
        if preferred[0] not in [option.ident for option in found]:
            lines.append("%spreferred %s is not an option" % (prefix, preferred[0]))
    if not _values(block.lines, VERDICT_LINE):
        lines.append(prefix + "no verdict")
    corrections = [text for _, text in block.lines if text.startswith(CORRECTION_PREFIX)]
    for k, text in enumerate(corrections, 1):
        lines += _correction_lines(prefix, k, text, found, ids)
    return lines


def _consilium_lines(record: Record) -> list[str]:
    """The consilium rules from stage `consilium` on: the role blocks, then each present role in record order.
    A missing, pending or empty Consilium has nothing to check; `none` is no exemption."""
    section = record.section("Consilium")
    if section is None or _is_pending(section) or _is_empty(section):
        return []
    lines = _role_block_lines(section)
    found, ids = options(record), _requirement_ids(record)
    for role, block in _role_blocks(section).items():
        lines += _role_lines(role, block, found, ids)
    return lines


def _preferred(record: Record) -> dict[str, str]:
    """The option each role of Consilium prefers (its first `preferred` line); a role without one is absent."""
    section = record.section("Consilium")
    found = {}
    for role, block in (_role_blocks(section) if section is not None else {}).items():
        values = _values(block.lines, PREFERRED_LINE)
        if values:
            found[role] = values[0]
    return found


def choice(record: Record) -> str | None:
    """The value of the first `- choice:` line of Decision, an option id in a right record; None without one."""
    section = record.section("Decision")
    values = _values(section.lines, CHOICE_LINE) if section is not None else []
    return values[0] if values else None


def _why_not_lines(lines: list[tuple[int, str]], chosen: Option, found: list[Option]) -> list[str]:
    """The faults of the `why not` lines: a line that names the choice, a non-option or a repeat, in line order;
    then each option other than the choice that no line names, in option order."""
    out, seen = [], []
    for ident in _values(lines, WHY_NOT_LINE):
        if ident == chosen.ident:
            out.append("decision: why not %s names the choice" % ident)
        elif ident not in [option.ident for option in found]:
            out.append("decision: why not %s is not an option" % ident)
        if ident in seen:
            out.append("decision: why not %s twice" % ident)
        seen.append(ident)
    return out + ["decision: no why not %s" % option.ident
                  for option in found if option.ident != chosen.ident and option.ident not in seen]


def _dissent_lines(lines: list[tuple[int, str]], chosen: Option, record: Record) -> list[str]:
    """The faults of the `dissent` lines in line order, then `no dissent for <role>` in ROLES order for each role
    whose consilium `preferred` differs from the choice and that has no well-formed dissent line. A role without
    a `preferred` is left to the consilium rules."""
    preferred, out, dissented = _preferred(record), [], set()
    texts = [text for _, text in lines if text.startswith(DISSENT_PREFIX)]
    for k, text in enumerate(texts, 1):
        parts = DISSENT_LINE.fullmatch(text)
        if parts is None or parts.group(1) not in ROLES:
            out.append('decision: dissent #%d is not "dissent: <role> preferred opt-<y>: <reason>"' % k)
            continue
        role, ident = parts.groups()
        dissented.add(role)
        if preferred.get(role) == chosen.ident:
            out.append("decision: dissent for %s, who preferred the choice" % role)
        elif role in preferred and ident != preferred[role]:
            out.append("decision: dissent %s names %s, consilium says %s" % (role, ident, preferred[role]))
    return out + ["decision: no dissent for %s" % role for role in ROLES
                  if role in preferred and preferred[role] != chosen.ident and role not in dissented]


def _why_name_lines(why: str, chosen: Option, found: list[Option], ids: list[str]) -> list[str]:
    """For each requirement the choice fails and another option meets, the `why` text must hold its id as a whole
    token: NFR-12 does not name NFR-1."""
    out = []
    for ident in ids:
        if chosen.fits.get(ident) != "fails":
            continue
        meets = next((option for option in found if option.fits.get(ident) == "meets"), None)
        if meets is not None and not re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(ident), why):
            out.append("decision: why does not name %s (%s fails it, %s meets it)" % (ident, chosen.ident, meets.ident))
    return out


def _decision_lines(record: Record) -> list[str]:
    """The decision rules from stage `decide` on: the choice, the `why`, then, when the choice is an option, the
    `why not` lines, the dissents and the requirements the `why` must name; last, `revisit when`. A missing,
    pending or empty Decision has nothing to check; `none` is no exemption. `next steps` has no rule."""
    section = record.section("Decision")
    if section is None or _is_pending(section) or _is_empty(section):
        return []
    lines, found = section.lines, options(record)
    choices, whys = _values(lines, CHOICE_LINE), _values(lines, WHY_LINE)
    out, chosen = [], None
    if not choices:
        out.append("decision: no choice")
    else:
        chosen = next((option for option in found if option.ident == choices[0]), None)
        if len(choices) > 1:
            out.append("decision: choice twice")
        if chosen is None:
            out.append("decision: choice %s is not an option" % choices[0])
    if not whys:
        out.append("decision: no why")
    if chosen is not None:
        out += _why_not_lines(lines, chosen, found) + _dissent_lines(lines, chosen, record)
        if whys:  # the first `why` line counts; without one `no why` is the only fault
            out += _why_name_lines(whys[0], chosen, found, _requirement_ids(record))
    if not any(REVISIT_LINE.fullmatch(text) for _, text in lines):
        out.append("decision: no revisit when")
    return out


def check_record(record: Record, root: str) -> list[str]:
    """The finding lines of a record, in order: the header, the sections, then, when the stage is known, the
    rules of the stage (from `frame` on: the cited lines and the options; from `consilium` on: the consilium;
    from `decide` on: the decision). `root` is where the cites resolve."""
    lines = _header_lines(record) + _section_lines(record.sections, SECTIONS, SECTIONS)
    if record.stage in STAGES:
        lines += _stage_lines(record)
        if reached(record.stage, "frame"):
            lines += _cited_lines(record, root) + _options_lines(record)
        if reached(record.stage, "consilium"):
            lines += _consilium_lines(record)
        if reached(record.stage, "decide"):
            lines += _decision_lines(record)
    return lines


def _cell_text(text: str) -> str:
    """Text for a cell: HTML-escaped, then each backtick span becomes <code>."""
    return BACKTICK_SPAN.sub(r"<code>\1</code>", escape(text, quote=True))


def render_matrix(record: Record) -> str:
    """The inner content of the matrix block, which starts and ends with a newline: the chosen-column style, then
    the table with one head row (the options in record order) and one body row for each requirement. One element
    for each line, so the same record always gives the same bytes. The record must pass `check_record` at stage
    `decide` or later."""
    found, chosen = options(record), choice(record)

    def mark_class(ident: str) -> str:
        return ' class="chosen"' if ident == chosen else ""

    lines = ["", "<style>%s</style>" % CHOSEN_CSS, '<div class="table-wrap"><table class="matrix">', "<thead>",
             "<tr>", "<th>Requirement</th>"]
    lines += ["<th%s>%s: %s%s</th>" % (mark_class(option.ident), option.ident, _cell_text(option.name),
                                      " (chosen)" if option.ident == chosen else "") for option in found]
    lines += ["</tr>", "</thead>", "<tbody>"]
    for requirement in requirements(record):
        lines += ["<tr>", "<td><code>%s</code> %s</td>" % (requirement.ident, _cell_text(requirement.text))]
        for option in found:
            mark = option.fits[requirement.ident]
            lines.append('<td%s><span role="img" aria-label="%s">%s</span></td>' % (
                mark_class(option.ident), mark, SYMBOLS[mark]))
        lines.append("</tr>")
    return "\n".join(lines + ["</tbody>", "</table></div>", ""])


def _matrix_block(html: str) -> tuple[tuple[int, int] | None, list[str]]:
    """((start, end), []) of the inner content of the one matrix block of a page: the text between its open tag
    and the `</div>` that matches it. (None, [line]) when the page has no block, more than one, or no end."""
    count = html.count(MATRIX_OPEN)
    if count == 0:
        return None, ["page: no " + MATRIX_OPEN]
    if count > 1:
        return None, ["page: %d %s blocks, more than 1" % (count, MATRIX_OPEN)]
    start = html.index(MATRIX_OPEN) + len(MATRIX_OPEN)
    depth = 1
    for token in MATRIX_TOKEN.finditer(html, start):
        depth += -1 if token.group() == "</div>" else 1
        if depth == 0:
            return (start, token.start()), []
    return None, ["page: %s is not closed" % MATRIX_OPEN]


def page_lines(record: Record, html: str | None) -> list[str]:
    """The `page:` lines of a record at stage `page` or later: no page, a fault of the matrix block, or a block
    that differs from render_matrix(record). `html` is the text of the page, None when there is none."""
    if html is None:
        return ["page: no " + PAGE]
    span, lines = _matrix_block(html)
    if span is None:
        return lines
    return ["page: matrix stale"] if html[span[0] : span[1]] != render_matrix(record) else []


def _facts_of(lines: list[tuple[int, str]], skip: str | None = None) -> list[Fact]:
    """The facts of the `- ` lines of a fact file scope, except the line `skip`; n counts the facts."""
    facts = []
    for number, text in lines:
        if text.startswith("- ") and text != skip:
            facts.append(parse_fact(len(facts) + 1, number, text[2:]))
    return facts


def check_facts(text: str, root: str) -> list[str]:
    """The finding lines of a searcher's fact file: the title, the sections, then the cites of Shape, the flows
    and Facts. `root` is where the cites resolve."""
    lines = text.removeprefix("\ufeff").splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip()), len(lines))
    title = lines[start].strip() if start < len(lines) else ""
    found = []
    if not (title.startswith(FACTS_PREFIX) and title[len(FACTS_PREFIX) :].strip()):
        found.append('title: not "# Facts: <id>"')
    sections = read_sections(lines, start + 1)
    found += _section_lines(sections, FACTS_TITLES, FACTS_REQUIRED)
    by_title = {section.title: section for section in reversed(sections)}  # the first section of a title wins
    if "Shape" in by_title:
        found += _cite_lines("Shape", _facts_of(by_title["Shape"].lines, NONE_BULLET), root)
    for block in by_title["Relevant flows"].blocks if "Relevant flows" in by_title else []:
        ident, colon, question = block.heading.partition(":")
        if not (colon and onboard.ID.fullmatch(ident)):
            found.append("flow %s: no flow id" % block.heading)
            continue
        flow = onboard.Flow(ident, block.heading, question.strip(), block.line, block.diagrams,
                            _facts_of(block.lines))
        found += onboard._place_lines(ident, flow, onboard.FLOWCHART)
        found += _cite_lines("Relevant flows/" + ident, flow.facts, root)
    if "Facts" in by_title:
        found += _cite_lines("Facts", _facts_of(by_title["Facts"].lines, NONE_BULLET), root)
    return found


class _Parser(argparse.ArgumentParser):
    """The arguments of a command; any error is the usage and exit 2."""

    def __init__(self) -> None:
        super().__init__(add_help=False)

    def error(self, message: str) -> NoReturn:
        raise SdrError(USAGE)


def _skeleton_text(question: str, root: str, code: list[str]) -> str:
    """The record at stage intake: the four header lines, then every section holding `pending`."""
    header = [TITLE_PREFIX + question, "stage: " + STAGES[0], "root: " + root,
              CODE_PREFIX + ("; ".join(code) or CODE_NONE)]
    body = [line for title in SECTIONS for line in ("", "## " + title, "", PENDING)]
    return "\n".join(header + body) + "\n"


def _skeleton_dirs(root: str, code: list[str]) -> tuple[str, list[str]]:
    """The root and the code dirs made absolute: each must be a directory, each code dir inside the root."""
    root = os.path.abspath(os.path.expanduser(root))
    if not os.path.isdir(root):
        raise SdrError("sdr: cannot read root %s" % root)
    dirs = [os.path.abspath(os.path.expanduser(path)) for path in code]
    for directory in dirs:
        if not os.path.isdir(directory):
            raise SdrError("sdr: cannot read code dir %s" % directory)
        if os.path.commonpath([root, directory]) != root:
            raise SdrError("sdr: %s is not under %s" % (directory, root))
    return root, dirs


def _write_new(sdr_dir: str, text: str) -> str:
    """Make `sdr_dir` and create sdr.md in it, never over an existing file; returns the path."""
    path = os.path.join(sdr_dir, "sdr.md")
    try:
        os.makedirs(sdr_dir, exist_ok=True)
        with open(path, "x", encoding="utf-8") as handle:
            handle.write(text)
    except FileExistsError as error:
        if os.path.isfile(path):
            raise SdrError("sdr: %s exists, not overwritten" % path) from error
        raise SdrError("sdr: cannot write %s: %s" % (path, error.strerror or error)) from error
    except OSError as error:
        raise SdrError("sdr: cannot write %s: %s" % (path, error.strerror or error)) from error
    return path


def cmd_skeleton(argv: list[str]) -> int:
    parser = _Parser()
    parser.add_argument("sdr_dir")
    parser.add_argument("--question", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--code", action="append", default=[])
    args = parser.parse_args(argv)
    question = " ".join(args.question.split())
    if not question:
        raise SdrError(USAGE)
    root, code = _skeleton_dirs(args.root, args.code)
    path = _write_new(args.sdr_dir, _skeleton_text(question, root, code))
    sys.stdout.write("sdr: wrote %s\n" % path)
    return 0


def _report(found: list[str]) -> int:
    """Print the findings and the summary line; the exit code is 1 when there are findings."""
    summary = "sdr: %d findings\n" % len(found) if found else "sdr: ok\n"
    sys.stdout.write("".join(line + "\n" for line in found) + summary)
    return 1 if found else 0


def _root_dir(record: Record, flag: str | None) -> str:
    """The root of the cites: the flag, else the record's `root:` line; it must be a directory."""
    root = flag if flag is not None else record.root
    if root is None:
        raise SdrError('sdr: no root: give --root or a "root:" line')
    if not os.path.isdir(root):
        raise SdrError("sdr: cannot read root %s" % root)
    return root


def _read_page(sdr_dir: str) -> str | None:
    """The text of <sdr-dir>/index.html; None when there is no such file, an SdrError when it cannot be read."""
    try:
        return _read_text(os.path.join(sdr_dir, PAGE))
    except SdrError as error:
        if isinstance(error.__cause__, FileNotFoundError):
            return None
        raise


def cmd_check(argv: list[str]) -> int:
    parser = _Parser()
    parser.add_argument("sdr_dir")
    parser.add_argument("--root")
    args = parser.parse_args(argv)
    record = read_record(args.sdr_dir)
    found = check_record(record, _root_dir(record, args.root))
    if not found and reached(record.stage, PAGE_STAGE):  # no findings: the stage is known
        found = page_lines(record, _read_page(args.sdr_dir))
    return _report(found)


def cmd_check_facts(argv: list[str]) -> int:
    parser = _Parser()
    parser.add_argument("file")
    parser.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    text = _read_text(args.file)
    if not os.path.isdir(args.root):
        raise SdrError("sdr: cannot read root %s" % args.root)
    return _report(check_facts(text, args.root))


def _write_text(path: str, text: str) -> None:
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except OSError as error:
        raise SdrError("sdr: cannot write %s: %s" % (path, error.strerror or error)) from error


def cmd_matrix(argv: list[str]) -> int:
    parser = _Parser()
    parser.add_argument("sdr_dir")
    args = parser.parse_args(argv)
    record = read_record(args.sdr_dir)
    found = check_record(record, _root_dir(record, None))
    if not found and not reached(record.stage, "decide"):  # no findings: the stage is known
        found = ["page: stage %s is before decide" % record.stage]
    if found:
        return _report(found)
    path = os.path.join(args.sdr_dir, PAGE)
    html = _read_text(path)
    span, found = _matrix_block(html)
    if span is None:
        return _report(found)
    _write_text(path, html[: span[0]] + render_matrix(record) + html[span[1] :])
    return _report([])


def _usage() -> int:
    sys.stderr.write(USAGE)
    return 2


def main(argv: list[str]) -> int:
    commands = {"skeleton": cmd_skeleton, "check": cmd_check, "check-facts": cmd_check_facts, "matrix": cmd_matrix}
    command = commands.get(argv[0]) if argv else None
    if command is None:
        return _usage()
    try:
        return command(argv[1:])
    except SdrError as error:
        line = str(error)
        sys.stderr.write(line if line.endswith("\n") else line + "\n")
        return error.code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
