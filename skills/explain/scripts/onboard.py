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

import cite_check

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
    "Conventions",
    "Where to look",
    "Not covered",
)
SHAPE_KEYS = ("language", "framework", "runtime", "artifact", "purpose", "build", "test", "run")
SHAPE_REQUIRED = ("language", "runtime", "artifact", "purpose", "build", "test", "run")
SHAPE_COMMANDS = ("build", "test", "run")
CONVENTION_TOPICS = ("tests", "errors", "wiring", "naming")
WHERE_ENTRY_KINDS = ("http", "listener", "route", "schedule")
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
REASON = re.compile(r"not (?:traced|an entry point):\s*\S.*")
HANDLE = re.compile(r"`[^`\n]+`")


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


def _flow_statements(line: str) -> list[str]:
    """The statements of one flowchart line: labels stripped, each edge made ` --> `, then cut at `;`.

    Stripping and edge matching come first so that a `;` in a label or an edge text cuts nothing."""
    line = QUOTED.sub("", line)
    while True:
        peeled = SHAPE.sub("", line)
        if peeled == line:
            break
        line = peeled
    line = CLASS_SUFFIX.sub("", EDGE_LABEL.sub("", line))
    return [statement.strip() for statement in EDGE.sub(" --> ", line).split(";")]


def _flowchart_ids(statement: str) -> list[str]:
    """The node ids of one statement of _flow_statements: split on the edges."""
    tokens = (TOKEN.search(segment) for segment in EDGE.split(statement))
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
    lines = [raw.split("%%", 1)[0].strip() for raw in _block_lines(block)[1:]]
    if kind == FLOWCHART:
        keywords, ids_of = FLOW_STATEMENTS, _flowchart_ids
        statements = [statement for line in lines for statement in _flow_statements(line)]
        subgraphs = {m.group(1) for m in map(SUBGRAPH.match, statements) if m}
    else:
        keywords, ids_of, statements, subgraphs = STATE_STATEMENTS, _state_ids, lines, set()
    ids = []
    for statement in statements:
        if not statement or statement == "}" or statement.split()[0] in keywords:
            continue
        ids.extend(ids_of(statement))
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
        if where and int(where.group(2)) >= 1 and parts[2].strip():
            cite = (where.group(1).strip(), int(where.group(2)), parts[2].strip())
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
        with open(path, encoding="utf-8-sig") as handle:
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
# A type declaration line: modifiers or same-line annotations, then the keyword and a name.
TYPE_DECL = re.compile(r"(?:(?:@\w+(?:\([^)]*\))?|\w+)\s+)*@?(?:class|interface|object|enum|record)\s+[A-Za-z_]")


class Hit(NamedTuple):
    path: str
    line: int  # 1-based
    kind: str
    text: str


def squash(text: str) -> str:
    return " ".join(text.split())[:TEXT_MAX]


def _declares_type(lines: list[str], index: int) -> bool:
    """Whether a line after lines[index] declares a type, up to and with the first that is neither blank nor
    starts with `@`; an annotation line such as `@Deprecated public class X {` counts."""
    for line in lines[index + 1 :]:
        text = line.strip()
        if TYPE_DECL.match(text):
            return True
        if text and not text.startswith("@"):
            return False
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
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError as error:
        raise OnboardError("onboard: cannot read %s: %s" % (path, error.strerror or error), 2) from error
    lines = text.split("\n")  # the line numbers of cite_check, not those of str.splitlines
    route_builder = BUILDER in text
    hits = []
    for index in range(len(lines)):
        kind = _kind_of(rules, lines, index, route_builder)
        if kind:
            hits.append(Hit(rel, index + 1, kind, _hit_text(lines, index)))
    return hits


def _cannot_list(error: OSError) -> NoReturn:
    """The `os.walk` error hook: a directory that cannot be listed is an unreadable source, not an empty one."""
    raise OnboardError("onboard: cannot read %s: %s" % (error.filename, error.strerror or error), 2) from error


def inventory(source: str, root: str) -> list[Hit]:
    source, root = os.fspath(source), os.fspath(root)
    if not os.path.isdir(source):
        raise OnboardError("onboard: cannot read %s" % source, 2)
    if os.path.relpath(source, root).split(os.sep, 1)[0] == os.pardir:
        raise OnboardError("usage: %s is not under %s" % (source, root), 2)
    hits = []
    for folder, dirnames, filenames in os.walk(source, onerror=_cannot_list):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for name in filenames:
            if not name.endswith(SKIP_SUFFIXES):
                path = os.path.join(folder, name)
                hits.extend(scan_file(path, os.path.relpath(path, root)))
    return sorted(hits, key=lambda hit: (hit.path, hit.line))


def inventory_line(hit: Hit) -> str:
    return "%s:%d\t%s\t%s" % (hit.path, hit.line, hit.kind, hit.text)


class _Parser(argparse.ArgumentParser):
    """The arguments of a command: one positional, `--root`, one option; any error is the usage and exit 2."""

    def __init__(self, positional: str, option: str) -> None:
        super().__init__(add_help=False)
        self.add_argument(positional)
        self.add_argument("--root", required=True)
        self.add_argument(option)

    def error(self, message: str) -> NoReturn:
        raise OnboardError(USAGE, 2)


def cmd_inventory(argv: list[str]) -> int:
    args = _Parser("source", "--out").parse_args(argv)
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


def _section_lines(doc: MapDoc) -> list[str]:
    """The `section:` lines: missing titles in canonical order, then repeats, order and flow ids in map order."""
    titles = [section.title for section in doc.sections]
    lines = ["section: missing %s" % title for title in TITLES if title not in titles]
    seen, highest = set(), -1
    for section in doc.sections:
        if section.title in seen:
            lines.append("section: %s twice" % section.title)
            continue
        seen.add(section.title)
        index = TITLES.index(section.title) if section.title in TITLES else -1
        if 0 <= index < highest:
            lines.append("section: %s out of order" % section.title)
        highest = max(highest, index)
        lines.extend("section: Flows heading %s has no flow id" % flow.heading for flow in section.flows
                     if flow.ident is None)
    return lines


def _places(doc: MapDoc) -> list[tuple[str, Section | Flow, str]]:
    """(where, scope, the diagram kind it needs) of each place to check, in output order; `none found` skips."""
    architecture, flows, state = (doc.section(title) for title in ("Architecture", "Flows", "State"))
    places = []
    if architecture and not architecture.none_found:
        places.append(("architecture", architecture, FLOWCHART))
    if flows and not flows.none_found:
        places.extend((flow.ident, flow, FLOWCHART) for flow in flows.flows if flow.ident)
    if state and not state.none_found:
        places.append(("state", state, STATE))
    return places


def _key(fact: Fact) -> str:
    """The node a fact names: the text before its first `:` when that is one token, else its first word."""
    head, colon, _ = fact.fact.partition(":")
    if colon and TOKEN.fullmatch(head):
        return head
    return (fact.fact.split() or [""])[0]


def _node_lines(where: str, diagram: Diagram, facts: list[Fact]) -> list[str]:
    """The `node` lines in diagram order, then the `fact` lines in bullet order."""
    keys = [_key(fact) for fact in facts]
    lines = []
    for node in diagram.nodes:
        if diagram.kind == FLOWCHART and not ID.fullmatch(node):
            lines.append("node %s/%s: bad id" % (where, node))
        if node not in keys:
            lines.append("node %s/%s: no fact line" % (where, node))
    for index, key in enumerate(keys):
        if key not in diagram.nodes:
            lines.append("fact %s/%s: not a node" % (where, key))
        elif keys[:index].count(key) == 1:  # the second line of a node, reported once
            lines.append("fact %s/%s: two lines" % (where, key))
    return lines


def _place_lines(where: str, scope: Section | Flow, needs: str) -> list[str]:
    """The `diagram` lines of one place, then its node rules unless its first diagram has the wrong kind."""
    if not scope.diagrams:
        return ["diagram %s: none" % where] + ["fact %s/%s: not a node" % (where, _key(f)) for f in scope.facts]
    diagram = scope.diagrams[0]
    lines = []
    if len(scope.diagrams) > 1:
        lines.append("diagram %s: %d blocks, more than 1" % (where, len(scope.diagrams)))
    if diagram.kind != needs:
        fault = "not flowchart or stateDiagram-v2" if diagram.kind is None else "not " + needs
        return lines + ["diagram %s: %s" % (where, fault)]
    if diagram.kind == FLOWCHART and len(diagram.nodes) > MAX_NODES:
        lines.append("diagram %s: %d nodes, more than %d" % (where, len(diagram.nodes), MAX_NODES))
    return lines + _node_lines(where, diagram, scope.facts)


def _facts(doc: MapDoc, title: str) -> list[Fact]:
    """The facts of the first `title` section; none when the map lacks it."""
    section = doc.section(title)
    return section.facts if section else []


def _entry_lines(doc: MapDoc) -> list[str]:
    """The `entry` lines: a fact part ends at its last ` -> ` with a reason or the id of a flow under Flows."""
    flows = doc.section("Flows")
    idents = {flow.ident for flow in flows.flows if flow.ident} if flows else set()
    lines = []
    for fact in _facts(doc, "Entry points"):
        _, arrow, tail = fact.fact.rpartition(" -> ")
        if arrow and ID.fullmatch(tail):
            if tail not in idents:
                lines.append("entry #%d: flow %s not in Flows" % (fact.n, tail))
        elif not (arrow and REASON.fullmatch(tail)):
            lines.append("entry #%d: no flow id and no reason" % fact.n)
    return lines


def _handle_lines(doc: MapDoc) -> list[str]:
    """The `fact Other systems#<n>` lines: a fact part without a handle in backticks."""
    facts = _facts(doc, "Other systems")
    return ["fact Other systems#%d: no handle in backticks" % f.n for f in facts if not HANDLE.search(f.fact)]


def keyed(fact: Fact) -> tuple[str | None, str]:
    """(key, rest) of a `<key>: <rest>` fact whose head is one token; (None, fact) when it has no such head."""
    head, colon, rest = fact.fact.partition(":")
    if colon and TOKEN.fullmatch(head):
        return head, rest.strip()
    return None, fact.fact


def none_found(fact: Fact) -> bool:
    """Whether a fact is `<key>: none found`."""
    key, rest = keyed(fact)
    return key is not None and rest == NONE_FOUND


def _shape_lines(doc: MapDoc) -> list[str]:
    """The `shape` lines: missing required keys, repeated keys, then per fact an unknown key or a command
    without a handle in backticks."""
    facts = [(fact, *keyed(fact)) for fact in _facts(doc, "Shape")]
    keys = [key for _, key, _ in facts]
    lines = ["shape: missing %s" % key for key in SHAPE_REQUIRED if key not in keys]
    lines.extend("shape: %s twice" % key for key in SHAPE_KEYS if key != "framework" and keys.count(key) > 1)
    for fact, key, rest in facts:
        if key not in SHAPE_KEYS:
            word = key or (fact.fact.split() or ["none"])[0]
            lines.append("shape #%d: unknown key %s" % (fact.n, word))
        elif key in SHAPE_COMMANDS and rest != NONE_FOUND and not HANDLE.search(rest):
            lines.append("shape #%d: no command in backticks" % fact.n)
    return lines


def _convention_lines(doc: MapDoc) -> list[str]:
    """The `conventions` lines: required topics with no line, then per fact a head that is not one id."""
    section = doc.section("Conventions")
    if section is None:
        return []
    facts = [(fact, keyed(fact)[0]) for fact in section.facts]
    topics = [key for _, key in facts]
    lines = ["conventions: missing %s" % topic for topic in CONVENTION_TOPICS if topic not in topics]
    lines.extend("conventions #%d: no topic" % fact.n for fact, key in facts if key is None or not ID.fullmatch(key))
    return lines


def _where_required(doc: MapDoc) -> list[str]:
    """The keys `Where to look` must hold, in a fixed order: one `add-<kind>` per entry kind with a traced or
    not-traced `Entry points` line, then `change-routing`, `add-transform` and `add-test`."""
    kinds = set()
    for fact in _facts(doc, "Entry points"):
        _, arrow, tail = fact.fact.rpartition(" -> ")
        if arrow and (ID.fullmatch(tail) or tail.startswith("not traced:")):
            kinds.add(fact.fact.split()[0])
    required = ["add-%s" % kind for kind in WHERE_ENTRY_KINDS if kind in kinds]
    for title, key in (("Routing config", "change-routing"), ("Formats and transforms", "add-transform")):
        section = doc.section(title)
        if section is not None and not section.none_found:
            required.append(key)
    tests = [fact for fact in _facts(doc, "Shape") if keyed(fact)[0] == "test"]
    if tests and not none_found(tests[0]):
        required.append("add-test")
    return required


def _under_root(handle: str, root: str) -> bool:
    """Whether a backticked handle, joined to the root, is an existing file or directory inside the root."""
    if os.path.isabs(handle):
        return False
    root = os.path.abspath(root)
    path = os.path.abspath(os.path.join(root, handle.rstrip("/")))
    return os.path.commonpath([root, path]) == root and os.path.exists(path)


def _where_lines(doc: MapDoc, root: str) -> list[str]:
    """The `where` lines: required keys with no line, then per fact a missing handle or one not under root."""
    section = doc.section("Where to look")
    if section is None:
        return []
    keys = [keyed(fact)[0] for fact in section.facts]
    lines = ["where: missing %s" % key for key in _where_required(doc) if key not in keys]
    for fact in section.facts:
        found = HANDLE.search(fact.fact)
        if found is None:
            lines.append("where #%d: no path in backticks" % fact.n)
        elif not _under_root(found.group(0)[1:-1], root):
            lines.append("where #%d: %s not under root" % (fact.n, found.group(0)[1:-1]))
    return lines


def _cite_scopes(doc: MapDoc) -> list[tuple[str, list[Fact]]]:
    """(scope, facts) in canonical section order, each flow after the Flows facts; `Not covered` has no cites."""
    scopes = []
    for title in TITLES:
        section = doc.section(title)
        if section is not None and title != "Not covered":
            scopes.append((title, section.facts))
            scopes.extend(("Flows/%s" % (flow.ident or flow.heading), flow.facts) for flow in section.flows)
    return scopes


def _may_lack_cite(scope: str, fact: Fact) -> bool:
    """Whether a `none found` fact needs no cite: a Shape command or any Conventions topic."""
    if not none_found(fact):
        return False
    return scope == "Conventions" or (scope == "Shape" and keyed(fact)[0] in SHAPE_COMMANDS)


def _cite_lines(doc: MapDoc, root: str) -> list[str]:
    """The `cite <scope>#<n>` lines: a fact without a cite, or each problem of its cite under root."""
    lines = []
    for scope, facts in _cite_scopes(doc):
        for fact in facts:
            if _may_lack_cite(scope, fact):
                continue
            problems = ["no cite"] if fact.cite is None else cite_check.fact_problems(*fact.cite, root)
            lines.extend("cite %s#%d: %s" % (scope, fact.n, problem) for problem in problems)
    return lines


def _unlisted_lines(doc: MapDoc, inventory_lines: list[str]) -> list[str]:
    """The `inventory` lines: the `<path>:<line>` of each tabbed inventory line that no Entry points fact cites."""
    cited = {"%s:%d" % fact.cite[:2] for fact in _facts(doc, "Entry points") if fact.cite}
    wheres = [line.split("\t", 1)[0] for line in inventory_lines if "\t" in line]
    return ["inventory %s: not in Entry points" % where for where in wheres if where not in cited]


def check_map(doc: MapDoc, root: str, inventory: list[str] | None = None) -> list[str]:
    """The failure lines of a map, in order: sections, each place (architecture, the flows, state), entry
    lines, Other systems handles, Shape keys, Conventions topics, Where to look keys and paths, cites, then
    the inventory lines that no entry line cites."""
    lines = _section_lines(doc)
    for where, scope, needs in _places(doc):
        lines.extend(_place_lines(where, scope, needs))
    lines.extend(_entry_lines(doc) + _handle_lines(doc) + _shape_lines(doc))
    lines.extend(_convention_lines(doc) + _where_lines(doc, root) + _cite_lines(doc, root))
    return lines + _unlisted_lines(doc, inventory or [])


def _inventory_lines(path: str) -> list[str]:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read().splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise OnboardError("onboard: cannot read inventory %s" % path, 2) from error


def cmd_check(argv: list[str]) -> int:
    args = _Parser("map", "--inventory").parse_args(argv)
    if not os.path.isdir(args.root):
        raise OnboardError("onboard: cannot read root %s" % args.root, 2)
    inventory_lines = None if args.inventory is None else _inventory_lines(args.inventory)
    failures = check_map(read_map(args.map), args.root, inventory_lines)
    summary = "onboard: %d failures\n" % len(failures) if failures else "onboard: ok\n"
    sys.stdout.write("".join(line + "\n" for line in failures) + summary)
    return 1 if failures else 0


def _usage() -> int:
    sys.stderr.write(USAGE)
    return 2


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
