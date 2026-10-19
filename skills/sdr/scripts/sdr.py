#!/usr/bin/env python3
"""Design review record tool for `sdr`: writes the skeleton of a record and checks it.

Usage: sdr.py skeleton <sdr-dir> --question <text> --root <root> [--code <dir>]...
       sdr.py check <sdr-dir> [--root <root>]
       sdr.py check-facts <file> --root <root>
skeleton writes <sdr-dir>/sdr.md at stage intake and refuses to overwrite it. check and check-facts print one
finding per line, then `sdr: ok` or `sdr: <n> findings`.
Exit 0 on success, 1 on findings, 2 on a usage error or an unreadable file, root or code dir. Usage text and
every exit-2 line go to stderr; findings and the summary go to stdout.
"""

import argparse
import os
import re
import sys
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


def check_record(record: Record, root: str) -> list[str]:
    """The finding lines of a record, in order: the header, the sections, then, when the stage is known, the
    rules of the stage. `root` is where the cites of the record resolve."""
    lines = _header_lines(record) + _section_lines(record.sections, SECTIONS, SECTIONS)
    if record.stage in STAGES:
        lines += _stage_lines(record)
        if reached(record.stage, "frame"):
            lines += _cited_lines(record, root)
    return lines


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


def cmd_check(argv: list[str]) -> int:
    parser = _Parser()
    parser.add_argument("sdr_dir")
    parser.add_argument("--root")
    args = parser.parse_args(argv)
    record = read_record(args.sdr_dir)
    root = args.root if args.root is not None else record.root
    if root is None:
        raise SdrError('sdr: no root: give --root or a "root:" line')
    if not os.path.isdir(root):
        raise SdrError("sdr: cannot read root %s" % root)
    return _report(check_record(record, root))


def cmd_check_facts(argv: list[str]) -> int:
    parser = _Parser()
    parser.add_argument("file")
    parser.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    text = _read_text(args.file)
    if not os.path.isdir(args.root):
        raise SdrError("sdr: cannot read root %s" % args.root)
    return _report(check_facts(text, args.root))


def _usage() -> int:
    sys.stderr.write(USAGE)
    return 2


def main(argv: list[str]) -> int:
    commands = {"skeleton": cmd_skeleton, "check": cmd_check, "check-facts": cmd_check_facts}
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
