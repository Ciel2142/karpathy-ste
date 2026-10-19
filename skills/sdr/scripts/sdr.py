#!/usr/bin/env python3
"""Design review record tool for `sdr`: writes the skeleton of a record and checks it.

Usage: sdr.py skeleton <sdr-dir> --question <text> --root <root> [--code <dir>]...
       sdr.py check <sdr-dir> [--root <root>]
skeleton writes <sdr-dir>/sdr.md at stage intake and refuses to overwrite it. check prints one finding per
line, then `sdr: ok` or `sdr: <n> findings`.
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

import cite_check  # noqa: E402,F401
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
PENDING = "pending"
HEADER_LINES = 4  # the title, `stage:`, `root:` and `code:` lines; the sections follow
FENCE = "```"
TITLE_PREFIX = "# SDR: "
STAGE_LINE = re.compile(r"stage: (\S+)\s*")
ROOT_LINE = re.compile(r"root: (\S.*?)\s*")
CODE_PREFIX = "code: "
CODE_NONE = "none"


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


def read_record(sdr_dir: str) -> Record:
    path = os.path.join(sdr_dir, "sdr.md")
    try:
        with open(path, encoding="utf-8") as handle:
            return parse_record(handle.read())
    except (OSError, UnicodeDecodeError) as error:
        reason = getattr(error, "strerror", None) or error
        raise SdrError("sdr: cannot read %s: %s" % (path, reason)) from error


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


def check_record(record: Record, root: str) -> list[str]:
    """The finding lines of a record, in order: the header, the sections, then, when the stage is known, the
    rules of the stage. `root` is where the cites of the record resolve."""
    lines = _header_lines(record) + _section_lines(record.sections, SECTIONS, SECTIONS)
    if record.stage in STAGES:
        lines += _stage_lines(record)
    return lines


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
    found = check_record(record, root)
    summary = "sdr: %d findings\n" % len(found) if found else "sdr: ok\n"
    sys.stdout.write("".join(line + "\n" for line in found) + summary)
    return 1 if found else 0


def _usage() -> int:
    sys.stderr.write(USAGE)
    return 2


def main(argv: list[str]) -> int:
    command = {"skeleton": cmd_skeleton, "check": cmd_check}.get(argv[0]) if argv else None
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
