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

import argparse
import os
import re
import sys
from typing import NamedTuple, NoReturn

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


class Rule(NamedTuple):
    suffixes: tuple[str, ...]  # the file name endings the rule applies to
    regex: re.Pattern  # searched per line


def _rule(suffixes: tuple[str, ...], *patterns: str) -> Rule:
    return Rule(suffixes, re.compile("|".join(patterns)))


JVM = (".java", ".kt")
GO = (".go",)
CAMEL_YAML = (".camel.yaml", ".camel.yml")
XML = (".xml",)
# One dict, kinds in the order a line is tried: a line is a hit of the first kind that matches.
PATTERNS = {
    "http": (
        _rule(JVM, r"@(Get|Post|Put|Delete|Patch)Mapping", r"@RequestMapping", r"@Path\(", r"@MessageMapping",
              r"@ServerEndpoint"),
        _rule(GO, r'\.(Get|Post|Put|Delete|Patch|GET|POST|PUT|DELETE|PATCH|Handle|HandleFunc)\(\s*"',
              r"http\.HandleFunc\("),
    ),
    "listener": (
        _rule(JVM, r"@(Jms|Rabbit|Kafka|Sqs|Stream)Listener", r"@KafkaHandler", r"@ServiceActivator",
              r"@InboundChannelAdapter", r"@EventListener", r"@TransactionalEventListener",
              r"@ExternalTaskSubscription", r"implements JavaDelegate", r": JavaDelegate"),
        _rule(GO, r"\.Consume\(", r"NewReader\(", r"NewConsumer\(", r"Subscribe\("),
    ),
    "route": (
        _rule(JVM, r"\bfrom\(", r"routeTemplate", r"@GrpcService"),
        _rule(GO, r"Register\w*Server\("),
        _rule(CAMEL_YAML, r"^\s*-\s*from:"),
        _rule(XML, r"<from\s[^>]*uri="),
    ),
    "schedule": (
        _rule(JVM, r"@Scheduled"),
        _rule(GO, r"\bcron\.", r"NewTicker\(", r"time\.Tick\("),
    ),
    "main": (
        _rule((".java",), r"public static void main"),
        _rule((".kt",), r"fun main\("),
        _rule(GO, r"func main\("),
    ),
}
SKIP_DIRS = frozenset({"node_modules", "target", "build", ".git", "vendor", "test", "tests"})
SKIP_SUFFIXES = ("_test.go", "Test.java", "Test.kt", "Spec.kt")
TEXT_MAX = 120
BUILDER = "RouteBuilder"
TYPE_DECL = re.compile(r"\b(class|interface|object|enum|record)\b")


class Hit(NamedTuple):
    path: str
    line: int  # 1-based
    kind: str
    text: str


def squash(text: str) -> str:
    return " ".join(text.split())[:TEXT_MAX]


def _declares_type(lines: list[str], index: int) -> bool:
    """Whether the first line after lines[index] that is neither blank nor an annotation declares a type."""
    for line in lines[index + 1 :]:
        text = line.strip()
        if text and not text.startswith("@"):
            return TYPE_DECL.search(text) is not None
    return False


def _counts(token: str, lines: list[str], index: int, route_builder: bool) -> bool:
    """Whether a rule match is an entry point: `from(` only in a RouteBuilder file, `@RequestMapping` on a method."""
    if token == "from(":
        return route_builder
    if token == "@RequestMapping":
        return not _declares_type(lines, index)
    return True


def _kind_of(rules: list[tuple[str, Rule]], lines: list[str], index: int, route_builder: bool) -> str | None:
    """The first kind, in table order, with a rule that matches lines[index] in a way that counts."""
    for kind, rule in rules:
        if any(_counts(found.group(0), lines, index, route_builder) for found in rule.regex.finditer(lines[index])):
            return kind
    return None


def _hit_text(lines: list[str], index: int) -> str:
    """The squashed line; a Camel YAML `- from:` alone on its line takes the next non-blank line with it."""
    text = squash(lines[index])
    if text == "- from:":
        following = next((line for line in lines[index + 1 :] if line.strip()), "")
        text = squash(text + " " + following)
    return text


def scan_file(path: str, rel: str) -> list[Hit]:
    rules = [(kind, rule) for kind, group in PATTERNS.items() for rule in group if path.endswith(rule.suffixes)]
    if not rules:
        return []
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    lines = text.split("\n")  # the line numbers of cite_check, not those of str.splitlines
    route_builder = BUILDER in text
    hits = []
    for index in range(len(lines)):
        kind = _kind_of(rules, lines, index, route_builder)
        if kind:
            hits.append(Hit(rel, index + 1, kind, _hit_text(lines, index)))
    return hits


def inventory(source: str, root: str) -> list[Hit]:
    source, root = os.fspath(source), os.fspath(root)
    if not os.path.isdir(source):
        raise OnboardError("onboard: cannot read %s" % source, 2)
    if os.path.relpath(source, root).split(os.sep, 1)[0] == os.pardir:
        raise OnboardError("usage: %s is not under %s" % (source, root), 2)
    hits = []
    for folder, dirnames, filenames in os.walk(source):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for name in filenames:
            if not name.endswith(SKIP_SUFFIXES):
                path = os.path.join(folder, name)
                hits.extend(scan_file(path, os.path.relpath(path, root)))
    return sorted(hits, key=lambda hit: (hit.path, hit.line))


def inventory_line(hit: Hit) -> str:
    return "%s:%d\t%s\t%s" % (hit.path, hit.line, hit.kind, hit.text)


class _InventoryParser(argparse.ArgumentParser):
    """The arguments of `inventory`; any error is the usage and exit 2, never a SystemExit."""

    def __init__(self) -> None:
        super().__init__(add_help=False)
        self.add_argument("source")
        self.add_argument("--root", required=True)
        self.add_argument("--out")

    def error(self, message: str) -> NoReturn:
        raise OnboardError(USAGE, 2)


def cmd_inventory(argv: list[str]) -> int:
    args = _InventoryParser().parse_args(argv)
    lines = [inventory_line(hit) for hit in inventory(args.source, args.root)]
    body = "".join(line + "\n" for line in lines)
    if args.out is not None:
        try:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(body)
        except OSError as error:
            raise OnboardError("onboard: cannot write %s: %s" % (args.out, error.strerror or error), 2) from error
    sys.stdout.write(body + "inventory: %d entry points\n" % len(lines))
    return 0


def _usage() -> int:
    sys.stderr.write(USAGE)
    return 2


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
