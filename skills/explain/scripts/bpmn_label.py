"""Cite labels for `bpmn.py label`: the owner of a line, the label rule and the page rewrite (spec 2.3).

A leaf module: it holds what bpmn.py and bpmn_svg.py share (NS_MODEL, NS_DI, BpmnError, clean).
"""

import html as htmllib
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import NamedTuple, Optional

NS_MODEL = "http://www.omg.org/spec/BPMN/20100524/MODEL"
NS_DI = "http://www.omg.org/spec/BPMN/20100524/DI"


class BpmnError(Exception):
    """An unreadable file or an expat error; the message names the path."""


def clean(text):
    """A name on one line: newlines and runs of blanks become single spaces."""
    return " ".join((text or "").split())


SUB_PROCESS_KINDS = frozenset(("subProcess", "transaction", "adHocSubProcess"))
FLOW_NODE_KINDS = SUB_PROCESS_KINDS | {"task", "callActivity"}
CONTAINER_KINDS = frozenset(("process", "collaboration", "participant", "lane", "definitions"))
DI_KINDS = {"BPMNShape": "shape", "BPMNEdge": "edge", "BPMNLabel": "label", "BPMNPlane": "plane"}
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# A tag whose quoted attribute values may hold ">".
TAG_TAIL = r"(?:[^>\"']|\"[^\"]*\"|'[^']*')*>"
CITE = re.compile(r"<cite\b" + TAG_TAIL + r".*?</cite>", re.DOTALL)
START_TAG = re.compile(r"<cite\b" + TAG_TAIL, re.DOTALL)
SECTION_TAG = re.compile(r"<(/?)section\b(" + TAG_TAIL + ")?", re.DOTALL)
LABEL_SPAN = re.compile(
    r'<span\b[^>]*\bclass="[^"]*\bbpmn-label\b[^"]*"[^>]*>(.*?)</span>', re.DOTALL
)
LINE_NUMBER = re.compile(r"[0-9]+")
SPAN = '<span class="bpmn-label">%s</span>'


class Cite(NamedTuple):
    span: tuple  # character offsets of the whole <cite>...</cite> in the page
    path: str
    line: int  # 0 when data-line is not a positive integer
    section: str  # id of the enclosing <section>, or "page"
    label: Optional[str]  # text of the existing span.bpmn-label, unescaped


def _kind_words(tag):
    """`exclusiveGateway` -> `exclusive gateway`."""
    return DI_KINDS.get(tag) or re.sub(r"(?<=.)(?=[A-Z])", " ", tag).lower()


def _has_row(node):
    if node.ns == NS_DI:
        return node.tag in DI_KINDS
    if node.ns != NS_MODEL:
        return False
    if node.tag in FLOW_NODE_KINDS or node.tag in CONTAINER_KINDS:
        return True
    if node.tag in ("sequenceFlow", "message", "error", "signal"):
        return True
    return node.tag.endswith(("Task", "Event", "Gateway"))


def _masked_lines(model):
    """The lines with every comment blanked out, so a comment-only line reads as empty."""
    return COMMENT.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), "\n".join(model.lines)).split("\n")


def owner(model, line):
    """Index of the innermost node with a label row whose span holds `line`, or None."""
    masked = _masked_lines(model)
    if not 1 <= line <= len(masked) or not masked[line - 1].strip():
        return None
    best, best_depth = None, -1
    for index, node in enumerate(model.nodes):
        if node.start <= line <= node.end and _has_row(node):
            depth = 0
            up = node.parent
            while up is not None:
                depth, up = depth + 1, model.nodes[up].parent
            if depth > best_depth:
                best, best_depth = index, depth
    return best


def _kind_and_id(node):
    return " ".join(part for part in (_kind_words(node.tag), node.attrs.get("id", "")) if part)


def _named(node):
    return clean(node.attrs.get("name")) or _kind_and_id(node)


def _flow_end(model, ref):
    index = model.by_id.get(ref)
    return _named(model.nodes[index]) if index is not None else (ref or "?")


def _flow_label(model, node):
    text = "%s \u2192 %s" % (
        _flow_end(model, node.attrs.get("sourceRef")),
        _flow_end(model, node.attrs.get("targetRef")),
    )
    name = clean(node.attrs.get("name"))
    return "%s, %s" % (text, name) if name else text


def label_of(model, node):
    """The label of a node; a node without a row takes its nearest ancestor's."""
    node = model.nodes[node] if isinstance(node, int) else node
    while not _has_row(node) and node.parent is not None:
        node = model.nodes[node.parent]
    if node.ns == NS_DI:
        return _di_label(model, node)
    if node.tag == "sequenceFlow":
        return _flow_label(model, node)
    if node.tag == "error":
        name, code = _named(node), node.attrs.get("errorCode", "")
        return "%s (%s)" % (name, code) if code else name
    return _named(node)


def _di_label(model, node):
    """A shape or edge takes the label of its bpmnElement, a BPMNLabel that of its parent."""
    ref = node.attrs.get("bpmnElement")
    if ref in model.by_id:
        return label_of(model, model.nodes[model.by_id[ref]])
    if node.tag == "BPMNLabel" and node.parent is not None:
        return label_of(model, model.nodes[node.parent])
    return _kind_and_id(node)


class _Root(HTMLParser):
    """Finds the first #provenance start tag, as cite_check does."""

    def __init__(self):
        super().__init__()
        self.provenance = None

    def handle_starttag(self, tag, attrs):
        values = {name: (value or "") for name, value in attrs}
        if self.provenance is None and values.get("id") == "provenance":
            self.provenance = values


class _Attrs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}

    def handle_starttag(self, tag, attrs):
        if not self.values:
            self.values = {name: (value or "") for name, value in attrs}


def _attrs_of(start_tag):
    parser = _Attrs()
    parser.feed(start_tag)
    parser.close()
    return parser.values


def page_root(html, html_dir):
    """data-root of #provenance joined to html_dir as cite_check does; None when it is empty."""
    parser = _Root()
    parser.feed(html)
    parser.close()
    data_root = (parser.provenance or {}).get("data-root", "").strip()
    return Path(os.path.join(html_dir, data_root)) if data_root else None


def _section_at(html, comments):
    """A function: character offset -> id of the innermost open section with an id, or "page"."""
    events = []
    for match in SECTION_TAG.finditer(html):
        if any(a <= match.start() < b for a, b in comments):
            continue
        if match.group(1):
            events.append((match.start(), None))
        else:
            events.append((match.start(), _attrs_of(match.group()).get("id") or ""))

    def section_at(offset):
        stack = []
        for position, ident in events:
            if position >= offset:
                break
            if ident is None:
                if stack:
                    stack.pop()
            else:
                stack.append(ident)
        return next((i for i in reversed(stack) if i), "page")

    return section_at


def bpmn_cites(html):
    """Every <cite> whose data-path ends in ".bpmn", in document order."""
    comments = [m.span() for m in COMMENT.finditer(html)]
    section_at = _section_at(html, comments)
    found = []
    for match in CITE.finditer(html):
        if any(a <= match.start() < b for a, b in comments):
            continue
        text = match.group()
        values = _attrs_of(START_TAG.match(text).group())
        path = values.get("data-path", "").strip()
        if not path.endswith(".bpmn"):
            continue
        number = values.get("data-line", "").strip()
        existing = LABEL_SPAN.search(text)
        found.append(
            Cite(
                match.span(),
                path,
                int(number) if LINE_NUMBER.fullmatch(number) else 0,
                section_at(match.start()),
                htmllib.unescape(existing.group(1)) if existing else None,
            )
        )
    return found


def _with_label(text, label):
    """The cite markup with its bpmn-label span set: replaced in place, else after </code>."""
    span = SPAN % htmllib.escape(label, quote=True)
    if LABEL_SPAN.search(text):
        return LABEL_SPAN.sub(lambda _match: span, text, count=1)
    cut = text.find("</code>")
    cut = cut + len("</code>") if cut >= 0 else text.rindex("</cite>")
    return text[:cut] + span + text[cut:]


def label_page(html, html_dir, load):
    """Return (the page with every .bpmn cite labelled, one failure line per cite that cannot be).

    `load` reads a .bpmn path into a model and raises BpmnError."""
    root = page_root(html, html_dir)
    models = {}
    failures = []
    pieces = []
    last = 0
    for cite in bpmn_cites(html):
        if root is None:
            failures.append("%s | %s | data-root missing" % (cite.section, cite.path))
            continue
        full = root / cite.path
        if full not in models:
            try:
                models[full] = load(full)
            except BpmnError as error:
                models[full] = error
        model = models[full]
        if isinstance(model, BpmnError):
            failures.append("%s | %s | %s" % (cite.section, cite.path, model))
            continue
        index = owner(model, cite.line)
        if index is None:
            failures.append("%s | %s:%d | no element" % (cite.section, cite.path, cite.line))
            continue
        label = label_of(model, index)
        pieces.append(html[last : cite.span[0]])
        pieces.append(_with_label(html[cite.span[0] : cite.span[1]], label))
        last = cite.span[1]
    pieces.append(html[last:])
    return "".join(pieces), failures
