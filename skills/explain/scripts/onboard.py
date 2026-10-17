#!/usr/bin/env python3
"""Onboarding map tool for `explain`: lists the entry points of a service and checks a map.

Usage: onboard.py inventory <source-dir> --root <root> [--out <file>]
       onboard.py check <map.md> --root <root> [--inventory <file>]
inventory prints one tab-separated `<path>:<line> <kind> <text>` line per entry point, then
`inventory: <n> entry points`. check prints one failure per line, then `onboard: ok` or
`onboard: <n> failures`.
Exit 0 on success, 1 on failures found, 2 on a usage error or an unreadable source, map, root or
inventory file. `map: cannot read ...` goes to stdout; every other exit-2 line goes to stderr.
"""

import re
import sys
from typing import NamedTuple

USAGE = (
    "usage: onboard.py inventory <source-dir> --root <root> [--out <file>]\n"
    "       onboard.py check <map.md> --root <root> [--inventory <file>]\n"
)
TITLES = (
    "Shape",
    "Architecture",
    "Entry points",
    "Flows",
    "State",
    "Formats and transforms",
    "Routing config",
    "Error paths",
    "Other systems",
    "Not covered",
)
NONE_FOUND = "none found"
ID = re.compile(r"[a-z][a-z0-9_-]*")
TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
MAX_NODES = 25
FLOWCHART = "flowchart"
STATE = "stateDiagram-v2"
HEADERS = {"flowchart TD": FLOWCHART, "flowchart LR": FLOWCHART, "stateDiagram-v2": STATE}
FLOW_STATEMENTS = ("subgraph", "end", "direction", "classDef", "class", "style", "linkStyle", "click")
STATE_STATEMENTS = ("direction", "note", "classDef", "class")
QUOTED = re.compile(r'"[^"]*"')
# One innermost shape label: [..], (..), {..} or the asymmetric >..]; doubled forms peel in turns.
SHAPE = re.compile(r"\[[^\[\](){}]*\]|\([^\[\](){}]*\)|\{[^\[\](){}]*\}|>[^\[\](){}>]*\]")
EDGE_LABEL = re.compile(r"\|[^|]*\|")
CLASS_SUFFIX = re.compile(r":::\w+(?:-\w+)*")
EDGE = re.compile(
    r"--\s.*?\s--[->ox]|-\.\s.*?\s\.->?|==\s.*?\s==[=>]"  # -- text -->, -. text .->, == text ==>
    r"|<-->|-\.->|-->|---|-\.-|==>|===|--o|--x|&"
)
SUBGRAPH = re.compile(r"subgraph\s+(" + TOKEN.pattern + ")")
STATE_DECL = re.compile(r'state\s+(?:"[^"]*"\s+as\s+)?(' + TOKEN.pattern + ")")
MAP_TITLE = re.compile(r"# Map:(.*)")
CITE = re.compile(r"(.+):([0-9]+)")
FENCE = "```"


class OnboardError(Exception):
    """One output line (str of the error) and the exit code it stands for."""

    def __init__(self, line: str, code: int = 2) -> None:
        super().__init__(line)
        self.code = code


def _block_lines(block: str) -> list[str]:
    """The lines of a diagram block from its first non-blank line on."""
    lines = block.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    return lines


def mermaid_kind(block: str) -> str | None:
    lines = _block_lines(block)
    return HEADERS.get(lines[0].strip()) if lines else None


def _flowchart_ids(line: str) -> list[str]:
    """The node ids of one flowchart line: labels stripped first, then split on the edges."""
    line = QUOTED.sub("", line)
    while True:
        peeled = SHAPE.sub("", line)
        if peeled == line:
            break
        line = peeled
    line = CLASS_SUFFIX.sub("", EDGE_LABEL.sub("", line))
    tokens = (TOKEN.search(segment) for segment in EDGE.split(line))
    return [token.group(0) for token in tokens if token]


def _state_ids(line: str) -> list[str]:
    """The state names of one stateDiagram-v2 line; `[*]` is never one."""
    declared = STATE_DECL.match(line)
    if declared:
        return [declared.group(1)]
    if "-->" not in line:
        return []
    left, right = line.split("-->", 1)
    tokens = (TOKEN.search(left), TOKEN.search(right.split(":", 1)[0]))
    return [token.group(0) for token in tokens if token]


def mermaid_nodes(block: str) -> list[str]:
    kind = mermaid_kind(block)
    if kind is None:
        return []
    statements, ids_of = (FLOW_STATEMENTS, _flowchart_ids) if kind == FLOWCHART else (STATE_STATEMENTS, _state_ids)
    lines = [raw.split("%%", 1)[0].strip() for raw in _block_lines(block)[1:]]
    subgraphs = {m.group(1) for m in map(SUBGRAPH.match, lines) if m} if kind == FLOWCHART else set()
    ids = []
    for line in lines:
        if not line or line == "}" or line.split()[0] in statements:
            continue
        ids.extend(ids_of(line))
    return [ident for ident in dict.fromkeys(ids) if ident not in subgraphs]


class Fact(NamedTuple):
    n: int  # 1-based inside its section or flow
    line: int  # 1-based line in the map
    fact: str
    cite: tuple[str, int, str] | None  # (path, line, snippet)


class Diagram(NamedTuple):
    line: int  # 1-based line of the opening fence
    kind: str | None
    nodes: list[str]
    text: str


class Flow(NamedTuple):
    ident: str | None
    heading: str
    question: str
    line: int
    diagrams: list[Diagram]
    facts: list[Fact]


class Section(NamedTuple):
    title: str
    line: int
    diagrams: list[Diagram]
    facts: list[Fact]
    flows: list[Flow]
    none_found: bool


class MapDoc(NamedTuple):
    ident: str
    sections: list[Section]

    def section(self, title: str) -> Section | None:
        return next((section for section in self.sections if section.title == title), None)


def _fact(n: int, line: int, text: str) -> Fact:
    """The fact of a `- <fact> | <path>:<line> | <snippet>` text; a cite only when well formed."""
    parts = text.split(" | ")
    cite = None
    if len(parts) == 3:
        where = CITE.fullmatch(parts[1].strip())
        if where and int(where.group(2)) >= 1:
            cite = (where.group(1), int(where.group(2)), parts[2].strip())
    return Fact(n, line, parts[0].strip(), cite)


def _flow(text: str, line: int) -> Flow:
    """The flow of a `### <text>` heading: `<id>: <question>`, or no id and the heading kept."""
    head, colon, question = text.partition(":")
    if colon and ID.fullmatch(head):
        return Flow(head, text, question.strip(), line, [], [])
    return Flow(None, text, "", line, [], [])


def _close_fence(fence: tuple, scope: Flow | Section | None) -> None:
    """A closed ```mermaid block becomes a Diagram of its flow or section; other blocks are dropped."""
    line, info, body = fence
    if info == "mermaid" and scope is not None:
        block = "\n".join(body)
        scope.diagrams.append(Diagram(line, mermaid_kind(block), mermaid_nodes(block), block))


def parse_map(text: str) -> MapDoc:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip()), len(lines))
    title = MAP_TITLE.fullmatch(lines[start].strip()) if start < len(lines) else None
    if not title or not title.group(1).strip():
        raise ValueError('no "# Map:" title')
    sections, contents = [], []  # contents: each section's non-blank lines outside fences and its opening fences
    flow = fence = None  # fence: (line, info, body) of the open fenced block
    for number, line in enumerate(lines[start + 1 :], start + 2):
        if fence is not None:
            if line.startswith(FENCE):
                _close_fence(fence, flow or (sections[-1] if sections else None))
                fence = None
            else:
                fence[2].append(line)
            continue
        if line.startswith(FENCE):
            fence = (number, line[len(FENCE) :].strip(), [])
            if sections:
                contents[-1].append(line.strip())
            continue
        if line.startswith("## "):
            sections.append(Section(line[3:].strip(), number, [], [], [], False))
            contents.append([])
            flow = None
            continue
        if not sections or not line.strip():
            continue
        contents[-1].append(line.strip())
        if line.startswith("### ") and sections[-1].title == "Flows":
            flow = _flow(line[4:].strip(), number)
            sections[-1].flows.append(flow)
        elif line.startswith("- ") and line.strip() != "- " + NONE_FOUND:
            scope = flow or sections[-1]
            scope.facts.append(_fact(len(scope.facts) + 1, number, line[2:]))
    if fence is not None:
        _close_fence(fence, flow or (sections[-1] if sections else None))
    marks = ([NONE_FOUND], ["- " + NONE_FOUND])
    return MapDoc(
        title.group(1).strip(),
        [section._replace(none_found=content in marks) for section, content in zip(sections, contents)],
    )


def read_map(path: str) -> MapDoc:
    try:
        with open(path, encoding="utf-8") as handle:
            return parse_map(handle.read())
    except (OSError, ValueError) as error:
        reason = getattr(error, "strerror", None) or error
        raise OnboardError("map: cannot read %s: %s" % (path, reason), 2) from error


def flow_nodes(doc: MapDoc) -> dict[str, list[str]]:
    """Each flow id of `Flows` with a diagram, mapped to the node ids of its first diagram."""
    flows = doc.section("Flows")
    if flows is None:
        return {}
    return {flow.ident: flow.diagrams[0].nodes for flow in flows.flows if flow.ident and flow.diagrams}


def _usage() -> int:
    sys.stderr.write(USAGE)
    return 2


def cmd_inventory(argv: list[str]) -> int:
    return _usage()


def cmd_check(argv: list[str]) -> int:
    return _usage()


def main(argv: list[str]) -> int:
    command = {"inventory": cmd_inventory, "check": cmd_check}.get(argv[0]) if argv else None
    if command is None:
        return _usage()
    try:
        return command(argv[1:])
    except OnboardError as error:
        line = str(error)
        stream = sys.stdout if line.startswith("map:") else sys.stderr
        stream.write(line if line.endswith("\n") else line + "\n")
        return error.code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
