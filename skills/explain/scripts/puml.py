"""PlantUML support for the `explain` onboard rung (spec sections 7 and 8).

Reads the text of a `plantuml` fence, without the `@startuml` wrapper, and reports its kind, its nodes,
its diagram faults and its node faults. Fence lines are numbered from 1, blank lines counted. This
module holds the activity (spec 7.2), component (7.3) and state (7.4) forms; the parser is tolerant: a
line that is none of the forms and none of the forbidden lines is ignored. Standard library only.
"""

import re
from typing import NamedTuple

KINDS = ("activity", "component", "state")
STYLE_LINES = ("skinparam", "!pragma", "!include", "<style>", "split", "backward:", "@startuml", "@enduml")
COLOUR_PREFIX = re.compile(r"#\w+:")
PREAMBLE = re.compile(r"(?:title|hide|scale)\b|left to right direction|top to bottom direction")
CONDITION = re.compile(r"(?:if|elseif|while|repeat\s+while|switch)\s*\(")
HOP = re.compile(r"see\s+(\S+)")
COMPONENT_ID = re.compile(r"[a-z][a-z0-9_]*")
STATE_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
PARTS = ("component", "queue", "database", "cloud", "node", "rectangle", "interface", "actor")
PART_DECLARATION = re.compile(r'(?:%s)\s+"[^"]*"\s+as\s+(\S+)' % "|".join(PARTS))
BRACKET_DECLARATION = re.compile(r"\[([^\]]+)\]\s+as\s+(\S+)")
BRACKET_ENDPOINT = re.compile(r"\[([^\]]+)\]")
STATE_ALIAS = re.compile(r'state\s+"[^"]*"\s+as\s+(\S+)')
STATE_DECLARATION = re.compile(r"state\s+([^\s{]+)")
_ARROW_BODY = r"[-.]+(?:(?:\[[^\]]*\]|left|right|up|down)[-.]*)?"
ARROW = re.compile(rf"<{_ARROW_BODY}>?|{_ARROW_BODY}>")  # `->`, `-->`, `..>`, `-left->`, `-[hidden]->`, `<--`
NOTE_OPEN = re.compile(r"(?:floating\s+)?note\s+(?:left|right|top|bottom|over)\b[^:]*$")
NOTE_CLOSE = re.compile(r"end\s*note$")
STAR = "[*]"


class Parsed(NamedTuple):
    kind: str | None  # one of KINDS, or None
    nodes: list[str]  # distinct, in order of first appearance
    faults: list[str]  # diagram faults without the `diagram <where>: ` prefix
    node_faults: list[tuple[str, str]]  # (node, fault) without the `node <where>/` prefix
    hops: list[str]  # the <flow-id> of each `:see <flow-id>;` action


def _statements(block: str):
    """Yield (fence line number, stripped text) for each line that is not blank, not a `'` comment and
    not part of a multi-line `note ... end note` block."""
    in_note = False
    for number, line in enumerate(block.splitlines(), 1):
        text = line.strip()
        if not text or text.startswith("'"):
            continue
        if in_note:
            in_note = NOTE_CLOSE.match(text) is None
        elif NOTE_OPEN.match(text):
            in_note = True
        else:
            yield number, text


def _edge(text: str) -> tuple[str, str] | None:
    """The two endpoints of an edge line, or None. The label is cut at the first `:` after the arrow, so
    `a --> b: go` and `a --> b : go -> c` both end at `b`; an endpoint never holds a colon."""
    arrow = ARROW.search(text)
    if not arrow or text.startswith("note "):
        return None
    left, right = text[:arrow.start()].strip(), text[arrow.end():].split(":", 1)[0].strip()
    return (left, right) if left and right and ":" not in left else None


def _part_declaration(text: str) -> tuple[str | None, str] | None:
    """(name or None, alias) when the line declares a component-form part, else None."""
    part = PART_DECLARATION.match(text)
    if part:
        return None, part.group(1)
    bracket = BRACKET_DECLARATION.match(text)
    return (bracket.group(1), bracket.group(2)) if bracket else None


def kind(block: str) -> str | None:
    """The kind of the fence: `activity` when its first statement after the preamble is `start`; else
    `state` when a line starts with `[*]` or `state `; else `component` when a line declares a part or
    draws an edge; else None."""
    texts = [text for _, text in _statements(block)]
    first = next((text for text in texts if not PREAMBLE.match(text) and text != "@startuml"), None)
    if first == "start":
        return "activity"
    if any(text.startswith((STAR, "state ")) for text in texts):
        return "state"
    if any(_part_declaration(text) or _edge(text) for text in texts):
        return "component"
    return None


def _is_style(text: str) -> bool:
    return text.startswith(STYLE_LINES) or COLOUR_PREFIX.match(text) is not None


def _condition(text: str) -> str | None:
    """The stripped text inside the first parentheses of a branch or loop line, or None."""
    opening = CONDITION.match(text)
    if not opening:
        return None
    depth = 1
    for position in range(opening.end(), len(text)):
        depth += {"(": 1, ")": -1}.get(text[position], 0)
        if depth == 0:
            return text[opening.end():position].strip()
    return None


def parse(block: str) -> Parsed:
    """Parse a fence by its kind. A fence of no kind keeps only its `style line` faults."""
    found = kind(block)
    statements = list(_statements(block))
    if found == "activity":
        return _parse_activity(block, statements)
    if found == "component":
        return _parse_component(statements)
    if found == "state":
        return _parse_state(statements)
    return Parsed(None, [], [f"style line {n}" for n, text in statements if _is_style(text)], [], [])


def _parse_activity(block: str, statements: list[tuple[int, str]]) -> Parsed:
    last_line = len(block.splitlines())
    nodes: list[str] = []
    faults: list[str] = []
    node_faults: list[tuple[str, str]] = []
    hops: list[str] = []

    def add_node(label: str) -> None:
        if not label or label in nodes:
            return
        nodes.append(label)
        if "`" in label:
            node_faults.append((label, "bad id"))

    skip_to = 0
    for number, text in statements:
        if number <= skip_to:
            continue
        if _is_style(text):
            faults.append(f"style line {number}")
        elif text.startswith(":"):
            if ";" in text:
                label = text[1:text.index(";")].strip()
                add_node(label)
                hop = HOP.fullmatch(label)
                if hop:
                    hops.append(hop.group(1))
            else:
                closing = next((n for n, later in statements if n > number and ";" in later), last_line)
                faults.append(f"action over lines {number}-{closing}")
                skip_to = closing
        else:
            condition = _condition(text)
            if condition is not None:
                add_node(condition)
    return Parsed("activity", nodes, faults, node_faults, hops)


def _parse_component(statements: list[tuple[int, str]]) -> Parsed:
    nodes: list[str] = []
    faults: list[str] = []
    node_faults: list[tuple[str, str]] = []
    alias_of: dict[str, str] = {}  # the name of a `[Name] as id` part -> its id
    edges: list[tuple[str, str]] = []
    for number, text in statements:
        declaration = _part_declaration(text)
        edge = _edge(text)
        if _is_style(text):
            faults.append(f"style line {number}")
        elif declaration:
            name, alias = declaration
            if name is not None:
                alias_of[name] = alias
            if alias not in nodes:
                nodes.append(alias)
                if not COMPONENT_ID.fullmatch(alias):
                    node_faults.append((alias, "bad id"))
        elif edge:
            edges.append(edge)
    declared = list(nodes)
    for endpoint in (end for edge in edges for end in edge):
        bracket = BRACKET_ENDPOINT.fullmatch(endpoint)
        node = alias_of.get(bracket.group(1), bracket.group(1)) if bracket else endpoint
        if node not in nodes:
            nodes.append(node)
        if node not in declared and (node, "not declared") not in node_faults:
            node_faults.append((node, "not declared"))
    return Parsed("component", nodes, faults, node_faults, [])


def _parse_state(statements: list[tuple[int, str]]) -> Parsed:
    nodes: list[str] = []
    faults: list[str] = []
    node_faults: list[tuple[str, str]] = []

    def add_state(state: str) -> None:
        if state == STAR or state in nodes:
            return
        nodes.append(state)
        if not STATE_ID.fullmatch(state):
            node_faults.append((state, "bad id"))

    for number, text in statements:
        head = text.split(":", 1)[0]
        declaration = STATE_ALIAS.match(head) or STATE_DECLARATION.match(head)
        edge = _edge(text)
        if _is_style(text):
            faults.append(f"style line {number}")
        elif declaration:
            add_state(declaration.group(1))
        elif edge:
            for end in edge:
                add_state(end)
    return Parsed("state", nodes, faults, node_faults, [])


