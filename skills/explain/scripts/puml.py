"""PlantUML support for the `explain` onboard rung (spec sections 7 and 8).

Reads the text of a `plantuml` fence, without the `@startuml` wrapper, and reports its kind, its nodes,
its diagram faults and its node faults. Fence lines are numbered from 1, blank lines counted. This
module holds the activity form (spec 7.2); the parser is tolerant: a line that is none of the forms and
none of the forbidden lines is ignored. Standard library only.
"""

import re
from typing import NamedTuple

KINDS = ("activity", "component", "state")
STYLE_LINES = ("skinparam", "!pragma", "!include", "<style>", "split", "backward:", "@startuml", "@enduml")
COLOUR_PREFIX = re.compile(r"#\w+:")
PREAMBLE = re.compile(r"(?:title|hide|scale)\b|left to right direction|top to bottom direction")
CONDITION = re.compile(r"(?:if|elseif|while|repeat\s+while|switch)\s*\(")
HOP = re.compile(r"see\s+(\S+)")


class Parsed(NamedTuple):
    kind: str | None  # one of KINDS, or None
    nodes: list[str]  # distinct, in order of first appearance
    faults: list[str]  # diagram faults without the `diagram <where>: ` prefix
    node_faults: list[tuple[str, str]]  # (node, fault) without the `node <where>/` prefix
    hops: list[str]  # the <flow-id> of each `:see <flow-id>;` action


def _statements(block: str):
    """Yield (fence line number, stripped text) for each line that is not blank and not a `'` comment."""
    for number, line in enumerate(block.splitlines(), 1):
        text = line.strip()
        if text and not text.startswith("'"):
            yield number, text


def kind(block: str) -> str | None:
    """The kind of the fence: `activity` when its first statement after the preamble is `start`, else None."""
    for _, text in _statements(block):
        if PREAMBLE.match(text):
            continue
        return "activity" if text == "start" else None
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
    """Parse the activity form of a fence."""
    lines = block.splitlines()
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
    for number, text in _statements(block):
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
                closing = next((n for n in range(number + 1, len(lines) + 1) if ";" in lines[n - 1]),
                               len(lines))
                faults.append(f"action over lines {number}-{closing}")
                skip_to = closing
        else:
            condition = _condition(text)
            if condition is not None:
                add_node(condition)
    return Parsed(kind(block), nodes, faults, node_faults, hops)
