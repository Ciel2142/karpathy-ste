#!/usr/bin/env python3
"""BPMN reader for `explain`: reads a .bpmn file into a model with line spans.

Usage: bpmn.py planes <file.bpmn>
       bpmn.py svg <file.bpmn> [--plane <id>] [--highlight id,id,...] [--prefix <p>]
Exit 0 on success, 1 on failures found, 2 on a usage or read error.
"""

import re
import sys
import xml.parsers.expat
from pathlib import Path
from typing import NamedTuple, Optional

from bpmn_svg import render

NS_MODEL = "http://www.omg.org/spec/BPMN/20100524/MODEL"
NS_DI = "http://www.omg.org/spec/BPMN/20100524/DI"
USAGE = (
    "usage: bpmn.py planes <file.bpmn>\n"
    "       bpmn.py svg <file.bpmn> [--plane <id>] [--highlight id,id,...] [--prefix <p>]\n"
)
PREFIX = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


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


def _write_planes(model, stream):
    for plane in model.planes:
        stream.write("%s\t%s\t%d\n" % (plane.id, plane.name or "-", plane.line))


def cmd_planes(args):
    if len(args) != 1:
        return _usage()
    try:
        model = load(args[0])
    except BpmnError as error:
        sys.stderr.write("%s\n" % error)
        return 2
    _write_planes(model, sys.stdout)
    return 0


def _svg_options(args):
    """The file and the options of svg, or None on a usage error."""
    if not args or args[0].startswith("--") or len(args) % 2 == 0:
        return None
    options = {"--plane": None, "--highlight": "", "--prefix": None}
    for key, value in zip(args[1::2], args[2::2]):
        if key not in options:
            return None
        options[key] = value
    if options["--prefix"] is not None and not PREFIX.match(options["--prefix"]):
        return None
    return args[0], options


def cmd_svg(args):
    parsed = _svg_options(args)
    if parsed is None:
        return _usage()
    path, options = parsed
    try:
        model = load(path)
    except BpmnError as error:
        sys.stderr.write("%s\n" % error)
        return 2
    if not model.planes:
        sys.stderr.write("bpmn.py: %s: no bpmndi:BPMNPlane\n" % path)
        return 1
    wanted = options["--plane"]
    plane = next((p for p in model.planes if wanted in (None, p.id)), None)
    if plane is None:
        sys.stderr.write("bpmn.py: %s: no plane %s; the planes are:\n" % (path, wanted))
        _write_planes(model, sys.stderr)
        return 2
    highlight = frozenset(i.strip() for i in options["--highlight"].split(",") if i.strip())
    text, warnings = render(model, plane, highlight, options["--prefix"] or plane.id)
    for warning in warnings:
        sys.stderr.write("bpmn.py: %s: %s\n" % (path, warning))
    sys.stdout.write(text)
    return 0


def _stub(args):
    """The label and check subcommands arrive in later tasks."""
    return _usage()


COMMANDS = {
    "planes": cmd_planes,
    "svg": cmd_svg,
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
