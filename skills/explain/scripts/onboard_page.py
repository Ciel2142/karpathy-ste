#!/usr/bin/env python3
"""The `diagrams` command of onboard.py (spec section 9): writes the PlantUML fence of each place of a
map to its own `.puml` file.

Usage: onboard.py diagrams <map.md> --out <dir>
Writes `architecture.puml`, `flow-<flow-id>.puml` and `state.puml`, each the fence lines wrapped in
`@startuml` / `@enduml`; a place with `none found` or no diagram writes nothing. Prints
`diagrams: stale <file>` for each `.puml` of the directory no place produced (deleting nothing), then
`diagrams: ok <n> files`.
Exit 0 on success, 1 when a place holds a Mermaid diagram (`diagrams: <where>: not plantuml`, stdout),
2 on a usage error (stderr), an unreadable map (`map: cannot read ...`, stdout) or an unwritable directory
(`diagrams: cannot write <dir>: <reason>`, stderr).

The page model and the structural checks of `onboard.py page` (spec sections 9 and 10.1): `page_lines_of` turns a
page into classified lines, and the six functions `title_lines`, `answer_lines`, `command_lines`,
`paragraph_lines`, `html_lines` and `cite_lines` each return the failure lines of one check.
"""

import argparse
import os
import re
import sys
from typing import NamedTuple, NoReturn

import onboard

IMAGE = re.compile(r"!\[(.*)\]\(([^()]*)\)\s*$")  # caption, path: the last parenthesised group
HTML_TAG = re.compile(r"</?[A-Za-z][^<>]*>")
CITE_LINE = re.compile(r" \| [^|]+:[0-9]+ \| ")
HEADING2 = re.compile(r"##+ ")
LIST_ITEM = re.compile(r"(?:[-*] |[0-9]+\. )")
CODE_SPAN = re.compile(r"`[^`]*`")
FENCE = "```"
COMMAND_KEYS = ("build", "test", "run")


def diagram_files(doc: onboard.MapDoc) -> dict[str, str]:
    """Each place with a diagram mapped from its file id to the file body: the first fence wrapped."""
    files = {}
    for where, scope, _ in onboard._places(doc):
        if not scope.diagrams:
            continue
        diagram = scope.diagrams[0]
        if diagram.notation != onboard.PLANTUML:
            raise onboard.OnboardError("diagrams: %s: not plantuml" % where, 1)
        ident = where
        if isinstance(scope, onboard.Flow):
            ident = "flow-" + where
            if ident in files:
                raise onboard.OnboardError("diagrams: flow %s twice" % where, 1)
        files[ident] = "@startuml\n" + diagram.text + "\n@enduml\n"
    return files


class _Parser(argparse.ArgumentParser):
    """The arguments of `diagrams`: the map and `--out`; any error is the usage and exit 2."""

    def __init__(self) -> None:
        super().__init__(add_help=False)
        self.add_argument("map")
        self.add_argument("--out", required=True)

    def error(self, message: str) -> NoReturn:
        raise onboard.OnboardError(onboard.USAGE, 2)


def _write(out: str, files: dict[str, str]) -> None:
    try:
        os.makedirs(out, exist_ok=True)
        for ident, body in files.items():
            with open(os.path.join(out, ident + ".puml"), "w", encoding="utf-8") as handle:
                handle.write(body)
    except OSError as error:
        raise onboard.OnboardError("diagrams: cannot write %s: %s" % (out, error.strerror or error), 2) from error


def cmd_diagrams(argv: list[str]) -> int:
    args = _Parser().parse_args(argv)
    doc = onboard.read_map(args.map)
    files = diagram_files(doc)
    _write(args.out, files)
    produced = {ident + ".puml" for ident in files}
    stale = sorted(name for name in os.listdir(args.out) if name.endswith(".puml") and name not in produced)
    sys.stdout.write("".join("diagrams: stale %s\n" % name for name in stale))
    sys.stdout.write("diagrams: ok %d files\n" % len(files))
    return 0


class Line(NamedTuple):
    n: int  # 1-based
    text: str  # without the newline, `\r` stripped
    kind: str  # "blank", "fence", "heading1", "heading2", "list", "table", "image", "code", "text"


def _kind(text: str) -> str:
    """The kind of a line outside a fence."""
    if not text.strip():
        return "blank"
    if text.startswith("# "):
        return "heading1"
    if HEADING2.match(text):
        return "heading2"
    if LIST_ITEM.match(text):
        return "list"
    if text.startswith("|"):
        return "table"
    if IMAGE.match(text):
        return "image"
    return "text"


def page_lines_of(text: str) -> list[Line]:
    """The lines of a page, each classified; a fence line toggles the fence and a line inside one is `code`."""
    raw = text.split("\n")
    if raw and raw[-1] == "":
        raw.pop()
    lines, inside = [], False
    for n, line in enumerate(raw, 1):
        line = line.rstrip("\r")
        if line.lstrip().startswith(FENCE):
            inside = not inside
            lines.append(Line(n, line, "fence"))
        else:
            lines.append(Line(n, line, "code" if inside else _kind(line)))
    return lines


def _non_blank(lines: list[Line]) -> list[Line]:
    return [line for line in lines if line.kind != "blank"]


def title_lines(lines: list[Line]) -> list[str]:
    """`page: no title` when the first non-blank line is not a `# ` line; `page: second title` once for more."""
    found = _non_blank(lines)
    failures = [] if found and found[0].kind == "heading1" else ["page: no title"]
    if sum(line.kind == "heading1" for line in found) > 1:
        failures.append("page: second title")
    return failures


def answer_lines(lines: list[Line]) -> list[str]:
    """`page: no short answer` when the first non-blank line after the title is not a text line of bold start."""
    found = _non_blank(lines)
    if len(found) > 1 and found[1].kind == "text" and found[1].text.startswith("**"):
        return []
    return ["page: no short answer"]


def command_lines(lines: list[Line], doc: onboard.MapDoc) -> list[str]:
    """`command <key>: not in a code block` for each `build`, `test` and `run` command of Shape that no code
    line equals, or that a line outside code holds."""
    code = {line.text.strip() for line in lines if line.kind == "code"}
    prose = [line.text for line in lines if line.kind not in ("code", "blank")]
    failures = []
    for fact in onboard._facts(doc, "Shape"):
        key, rest = onboard.keyed(fact)
        handle = onboard.HANDLE.search(rest)
        if key not in COMMAND_KEYS or onboard.none_found(fact) or not handle:
            continue
        command = handle.group().strip("`")
        if command not in code or any(command in text for text in prose):
            failures.append("command %s: not in a code block" % key)
    return failures


def paragraph_lines(lines: list[Line]) -> list[str]:
    """`paragraph <n>: two lines` for the second line of each run of text lines."""
    failures, run = [], 0
    for line in lines:
        run = run + 1 if line.kind == "text" else 0
        if run == 2:
            failures.append("paragraph %d: two lines" % line.n)
    return failures


def html_lines(lines: list[Line]) -> list[str]:
    """`html <n>: tag outside code` for a text, list or table line with an HTML tag outside backtick spans."""
    return ["html %d: tag outside code" % line.n
            for line in lines
            if line.kind in ("text", "list", "table") and HTML_TAG.search(CODE_SPAN.sub("", line.text))]


def cite_lines(lines: list[Line]) -> list[str]:
    """`cite <n>: map line on the page` for a line outside code of the shape `... | <path>:<n> | ...`."""
    return ["cite %d: map line on the page" % line.n
            for line in lines if line.kind != "code" and CITE_LINE.search(line.text)]
