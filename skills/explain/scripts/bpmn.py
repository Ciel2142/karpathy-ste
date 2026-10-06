#!/usr/bin/env python3
"""BPMN reader for `explain`: reads a .bpmn file into a model with line spans.

Usage: bpmn.py planes <file.bpmn>
Exit 0 on success, 1 on failures found, 2 on a usage or read error.
"""

import sys
import xml.parsers.expat
from pathlib import Path
from typing import NamedTuple, Optional

NS_MODEL = "http://www.omg.org/spec/BPMN/20100524/MODEL"
NS_DI = "http://www.omg.org/spec/BPMN/20100524/DI"
USAGE = "usage: bpmn.py planes <file.bpmn>\n"


class Node(NamedTuple):
    ns: str
    tag: str
    attrs: dict
    start: int  # 1-based line of "<"
    end: int  # 1-based line of the end tag; the line of "/>" when self-closing
    parent: Optional[int]
    children: tuple


class Plane(NamedTuple):
    id: str  # bpmnElement of the BPMNPlane
    name: Optional[str]
    line: int  # start line of that element
    plane: int  # index of the BPMNPlane node


class Model(NamedTuple):
    path: Path
    nodes: list
    by_id: dict  # model ids only, not DI ids
    planes: list
    lines: list


class BpmnError(Exception):
    """An unreadable file or an expat error; the message names the path."""


def _split_name(name):
    """Split expat's "namespace local" form; a name without a namespace has an empty one."""
    if " " in name:
        ns, _, local = name.rpartition(" ")
        return ns, local
    return "", name


def _local_attrs(raw):
    """Attributes by local name; an unprefixed attribute wins over a prefixed twin."""
    attrs = {}
    for key, value in raw.items():
        if " " in key:
            attrs.setdefault(key.rpartition(" ")[2], value)
        else:
            attrs[key] = value
    return attrs


def _parse(data):
    """Return the nodes in document order; each node is [ns, tag, attrs, start, end, parent, children]."""
    parser = xml.parsers.expat.ParserCreate(namespace_separator=" ")
    nodes = []
    stack = []

    def on_start(name, raw):
        ns, tag = _split_name(name)
        line = parser.CurrentLineNumber
        parent = stack[-1] if stack else None
        nodes.append([ns, tag, _local_attrs(raw), line, line, parent, []])
        if parent is not None:
            nodes[parent][6].append(len(nodes) - 1)
        stack.append(len(nodes) - 1)

    def on_end(name):
        nodes[stack.pop()][4] = parser.CurrentLineNumber

    parser.StartElementHandler = on_start
    parser.EndElementHandler = on_end
    parser.Parse(data, True)
    return nodes


def _planes(nodes, by_id):
    planes = []
    for index, (ns, tag, attrs, start, _end, _parent, _children) in enumerate(nodes):
        if ns != NS_DI or tag != "BPMNPlane":
            continue
        ident = attrs.get("bpmnElement", "")
        owner = nodes[by_id[ident]] if ident in by_id else None
        name = owner[2].get("name") if owner else None
        planes.append(Plane(ident, name, owner[3] if owner else start, index))
    return planes


def load(path):
    """Read a .bpmn file into a Model. Raises BpmnError, naming the path."""
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError as error:
        raise BpmnError("%s: cannot read file: %s" % (path, error.strerror or error))
    try:
        raw = _parse(data)
    except xml.parsers.expat.ExpatError as error:
        raise BpmnError("%s: %s" % (path, error))
    nodes = [Node(n[0], n[1], n[2], n[3], n[4], n[5], tuple(n[6])) for n in raw]
    by_id = {}
    for index, node in enumerate(nodes):
        if node.ns == NS_MODEL and "id" in node.attrs:
            by_id.setdefault(node.attrs["id"], index)
    text = data.decode("utf-8", errors="replace")
    return Model(path, nodes, by_id, _planes(nodes, by_id), text.split("\n"))


def cmd_planes(args):
    if len(args) != 1:
        return _usage()
    try:
        model = load(args[0])
    except BpmnError as error:
        sys.stderr.write("%s\n" % error)
        return 2
    for plane in model.planes:
        sys.stdout.write("%s\t%s\t%d\n" % (plane.id, plane.name or "-", plane.line))
    return 0


def _stub(args):
    """The svg, label and check subcommands arrive in later tasks."""
    return _usage()


COMMANDS = {
    "planes": cmd_planes,
    "svg": _stub,
    "label": _stub,
    "check": _stub,
}


def _usage():
    sys.stderr.write(USAGE)
    return 2


def main(argv):
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure:
        reconfigure(encoding="utf-8")
    if not argv or argv[0] not in COMMANDS:
        return _usage()
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
