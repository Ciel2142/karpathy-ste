"""SVG renderer for `bpmn.py svg`: draws one plane from the file's own DI (spec 2.1).

Colours come from CSS classes only. `bpmn-shape` is a closed shape with fill and stroke,
`bpmn-flow` is a line with stroke and no fill, `bpmn-text` is text or a filled mark.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

from bpmn_label import SUB_PROCESS_KINDS as SUBS, clean
from bpmn_marks import circle, esc, event, f, path, poly, rect

if TYPE_CHECKING:
    from bpmn import Model, Plane

FONT = 14  # units; also the floor
EM_PER_CHAR = 0.55
MARGIN = 20
LINE = FONT * 1.2
PAD = 8  # inner padding of a box that holds a name
BAND = 30  # name band of a participant or a lane
LABEL_W = 90  # least wrap width of a label outside its shape
NS_MODEL = "http://www.omg.org/spec/BPMN/20100524/MODEL"
TAGS = {"serviceTask": "service", "sendTask": "send", "receiveTask": "receive",
        "userTask": "user", "businessRuleTask": "rule", "scriptTask": "script",
        "manualTask": "manual"}
TASKS = set(TAGS) | {"task", "callActivity"}
EVENTS = {"startEvent", "intermediateCatchEvent", "intermediateThrowEvent", "endEvent",
          "boundaryEvent"}
GLYPHS = {"exclusiveGateway": "×", "parallelGateway": "+", "complexGateway": "*"}


def wrap(name: str, width: float, height: float) -> tuple[list[str], bool]:
    """Break `name` into lines that fit `width`; keep the lines that `height` holds."""
    per = max(1, int(width / (FONT * EM_PER_CHAR) + 1e-9))
    room = max(1, int(height / LINE + 1e-9))
    lines = []
    for word in name.split():
        if lines and len(lines[-1]) + 1 + len(word) <= per:
            lines[-1] += " " + word
        else:
            lines.append(word)
    if len(lines) <= room:
        return lines, False
    last = lines[room - 1]
    while len(last) + 1 > per and " " in last:
        last = last.rsplit(" ", 1)[0]
    if len(last) + 1 > per:
        last = last[:per - 1]
    return lines[:room - 1] + [last + "…"], True


def _text(lines, x, top, anchor="middle", extra=""):
    """One text element; each line is a tspan, `top` is the top of the first line."""
    spans = "".join('<tspan x="%s" y="%s">%s</tspan>' % (f(x), f(top + i * LINE + FONT), esc(line))
                    for i, line in enumerate(lines))
    return '<text class="bpmn-text" font-size="%d" text-anchor="%s"%s>%s</text>' % (
        FONT, anchor, extra, spans)


def _glyph(char, cx, cy, scale=1):
    """A marker glyph centred on (cx, cy); a scale keeps it large when CSS pins the size."""
    move = ' transform="translate(%s %s) scale(%s)"' % (f(cx), f(cy), f(scale))
    return ('<text class="bpmn-text" font-size="%d" text-anchor="middle" '
            'dominant-baseline="central"%s>%s</text>' % (FONT, move, esc(char)))


def _boxed(name, x, top, width, height):
    """A name centred in a box; returns the markup and whether the name was cut."""
    lines, cut = wrap(name, width, height)
    if not lines:
        return "", False
    top += (height - len(lines) * LINE) / 2
    return _text(lines, x + width / 2, top), cut


def _gateway(node, b):
    x, y, w, h = b
    cx, cy = x + w / 2, y + h / 2
    parts = [path("M%s %sL%s %sL%s %sL%s %sZ" % (f(cx), f(y), f(x + w), f(cy), f(cx), f(y + h),
                                                f(x), f(cy)), "bpmn-shape")]
    if node.tag in GLYPHS:
        parts.append(_glyph(GLYPHS[node.tag], cx, cy, 2))
    elif node.tag == "inclusiveGateway":
        parts.append(circle(cx, cy, h * .24, "bpmn-flow", ' fill="none" stroke-width="2.5"'))
    elif node.tag == "eventBasedGateway":
        r = h * .3
        parts.append(circle(cx, cy, r, "bpmn-flow", ' fill="none"'))
        parts.append(circle(cx, cy, r - 3, "bpmn-flow", ' fill="none"'))
        corners = [(math.cos(math.radians(-90 + 72 * k)) * .5,
                    math.sin(math.radians(-90 + 72 * k)) * .5) for k in range(5)]
        parts.append(path(poly(corners, cx, cy, r)))
    return parts


def _task(node, b, name):
    x, y, w, h = b
    extra = ' rx="10"' + (' stroke-width="3"' if node.tag == "callActivity" else "")
    parts = [rect(x, y, w, h, extra)]
    top, height = y + PAD, h - 2 * PAD
    if node.tag in TAGS:
        parts.append('<text class="bpmn-text" font-size="%d" x="%s" y="%s">%s</text>' % (
            FONT, f(x + 6), f(y + 4 + FONT), TAGS[node.tag]))
        top, height = top + LINE, height - LINE
    text, cut = _boxed(name, x + PAD, top, w - 2 * PAD, height)
    return parts + [text], cut


def _sub(node, di, b, name):
    x, y, w, h = b
    extra = ' rx="10"'
    if node.attrs.get("triggeredByEvent") == "true":
        extra += ' stroke-dasharray="2 3"'
    parts = [rect(x, y, w, h, extra)]
    if di.attrs.get("isExpanded") == "true":
        lines, cut = wrap(name, w - 2 * PAD, LINE)
        return parts + ([_text(lines, x + PAD, y + 4, "start")] if lines else []), cut
    cx, side = x + w / 2, FONT
    parts.append(rect(cx - side / 2, y + h - side - 4, side, side))
    parts.append(_glyph("+", cx, y + h - side / 2 - 4))
    text, cut = _boxed(name, x + PAD, y + PAD, w - 2 * PAD, h - 2 * PAD - side - 4)
    return parts + [text], cut


def _pool(di, b, name):
    x, y, w, h = b
    parts = [rect(x, y, w, h)]
    if di.attrs.get("isHorizontal") == "false":
        parts.append(path("M%s %sL%s %s" % (f(x), f(y + BAND), f(x + w), f(y + BAND))))
        text, cut = _boxed(name, x + PAD, y, w - 2 * PAD, BAND)
        return parts + [text], cut
    parts.append(path("M%s %sL%s %s" % (f(x + BAND), f(y), f(x + BAND), f(y + h))))
    lines, cut = wrap(name, h - 2 * PAD, BAND)
    if lines:
        cx, cy = x + BAND / 2, y + h / 2
        turn = ' transform="rotate(-90 %s %s)"' % (f(cx), f(cy))
        parts.append(_text(lines, cx, cy - len(lines) * LINE / 2, extra=turn))
    return parts, cut


def _annotations(model):
    """Text of each text annotation by id; the model keeps no character data."""
    root = ET.fromstring("\n".join(model.lines).encode("utf-8"))
    found = {}
    for node in root.iter("{%s}textAnnotation" % NS_MODEL):
        text = node.find("{%s}text" % NS_MODEL)
        found[node.get("id")] = clean(text.text) if text is not None else ""
    return found


def _child(model, node, tag):
    for index in node.children:
        if model.nodes[index].tag == tag:
            return model.nodes[index]
    return None


def _bounds(model, node):
    """The x, y, width, height of a node's dc:Bounds child, or None."""
    bounds = _child(model, node, "Bounds") if node is not None else None
    try:
        return tuple(float(bounds.attrs[k]) for k in ("x", "y", "width", "height"))
    except (AttributeError, KeyError, ValueError):
        return None


def _waypoints(model, node):
    points = []
    for index in node.children:
        point = model.nodes[index]
        if point.tag == "waypoint":
            try:
                points.append((float(point.attrs["x"]), float(point.attrs["y"])))
            except (KeyError, ValueError):
                return []
    return points


def _edge(model, node, points, prefix):
    line = " ".join("%s,%s" % (f(x), f(y)) for x, y in points)
    extra = ""
    if node.tag == "sequenceFlow":
        extra = ' marker-end="url(#%s-arrow)"' % esc(prefix)
    elif node.tag == "messageFlow":
        extra = ' stroke-dasharray="6 4" marker-end="url(#%s-open)"' % esc(prefix)
    elif node.tag == "association":
        extra = ' stroke-dasharray="2 3"'
        if node.attrs.get("associationDirection") in ("One", "Both"):
            extra += ' marker-end="url(#%s-open)"' % esc(prefix)
    elif node.tag.startswith("data"):
        extra = ' stroke-dasharray="2 3" marker-end="url(#%s-open)"' % esc(prefix)
    parts = ['<polyline class="bpmn-flow" fill="none" points="%s"%s/>' % (line, extra)]
    source = model.by_id.get(node.attrs.get("sourceRef", ""))
    if (node.tag == "sequenceFlow" and source is not None
            and model.nodes[source].attrs.get("default") == node.attrs.get("id")):
        (x0, y0), (x1, y1) = points[0], points[1]
        size = math.hypot(x1 - x0, y1 - y0) or 1
        ux, uy = (x1 - x0) / size, (y1 - y0) / size
        cx, cy = x0 + ux * min(12, size / 2), y0 + uy * min(12, size / 2)
        dx, dy = (-uy + ux * .6) * 6, (ux + uy * .6) * 6
        parts.append('<line class="bpmn-flow" x1="%s" y1="%s" x2="%s" y2="%s"/>' % (
            f(cx - dx), f(cy - dy), f(cx + dx), f(cy + dy)))
    return parts


def _label(ident, name, label, fallback, box):
    """A name outside its shape, centred on its DI label bounds, or hung below a fallback point.

    The modeler sizes label bounds for smaller text, so the wrapped block is centred on their middle."""
    if label:
        x, y, w, h = label
        cx, width = x + w / 2, max(w, LABEL_W)
    else:
        (cx, top), width = fallback, LABEL_W
    lines, _cut = wrap(name, width, 10 ** 6)
    if label:
        top = y + h / 2 - len(lines) * LINE / 2
    else:
        box.append((cx - width / 2, top, cx + width / 2, top + len(lines) * LINE))
    return _text(lines, cx, top, extra=' data-for="%s"' % esc(ident))


def _shape(model, node, di, b, name, notes):
    """Markup of one shape, whether its name was cut, and whether the name sits outside."""
    if node.tag in EVENTS:
        return event(model, node, b), False, True
    if node.tag.endswith("Gateway"):
        return _gateway(node, b), False, True
    if node.tag in TASKS:
        return _task(node, b, name) + (False,)
    if node.tag in SUBS:
        return _sub(node, di, b, name) + (False,)
    if node.tag in ("participant", "lane"):
        return _pool(di, b, name) + (False,)
    x, y, w, h = b
    if node.tag == "textAnnotation":
        bracket = path("M%s %sL%s %sL%s %sL%s %s" % (f(x + 10), f(y), f(x), f(y), f(x), f(y + h),
                                                     f(x + 10), f(y + h)))
        lines, _cut = wrap(notes.get(node.attrs.get("id"), ""), w - 10, 10 ** 6)
        return [bracket] + ([_text(lines, x + 5, y + 4, "start")] if lines else []), False, False
    text, cut = _boxed(name, x + PAD, y + PAD, w - 2 * PAD, h - 2 * PAD)
    return [rect(x, y, w, h), text], cut, False


def _group(ident, parts, highlight, title, prefix):
    head = '<g data-id="%s"%s>' % (esc(ident), ' class="hl"' if ident in highlight else "")
    if title:
        head += '<title id="%s">%s</title>' % (esc("%s-%s-title" % (prefix, ident)), esc(title))
    return head + "".join(part for part in parts if part) + "</g>"


def _defs(prefix):
    marker = ('<marker id="%s-%s" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="10" '
              'markerHeight="10" markerUnits="userSpaceOnUse" orient="auto">%s</marker>')
    return "<defs>%s%s</defs>" % (
        marker % (esc(prefix), "arrow", '<path class="bpmn-text" d="M0 0L10 5L0 10Z"/>'),
        marker % (esc(prefix), "open", '<path class="bpmn-flow" fill="none" d="M1 1L10 5L1 9"/>'))


def render(model: Model, plane: Plane, highlight: frozenset[str], prefix: str) -> tuple[str, list[str]]:
    """One plane as inline SVG, plus a warning per skipped DI element."""
    pools, shapes, edges, labels, box, warnings, seen = [], [], [], [], [], [], set()
    notes = None
    for index in model.nodes[plane.plane].children:
        di = model.nodes[index]
        if di.tag not in ("BPMNShape", "BPMNEdge"):
            continue
        ident = di.attrs.get("bpmnElement", "")
        if ident not in model.by_id:
            warnings.append("skipped %s: no model element with this id" % (ident or di.attrs.get("id")))
            continue
        node = model.nodes[model.by_id[ident]]
        name = clean(node.attrs.get("name"))
        label = _bounds(model, _child(model, di, "BPMNLabel"))
        if di.tag == "BPMNEdge":
            points = _waypoints(model, di)
            if len(points) < 2:
                warnings.append("skipped %s: fewer than two waypoints" % ident)
                continue
            box.extend((x, y, x, y) for x, y in points)
            edges.append(_group(ident, _edge(model, node, points, prefix), highlight, None, prefix))
            middle = (len(points) - 1) // 2
            (x0, y0), (x1, y1) = points[middle], points[middle + 1]
            fallback = ((x0 + x1) / 2, (y0 + y1) / 2 - LINE)
        else:
            b = _bounds(model, di)
            if b is None:
                warnings.append("skipped %s: no dc:Bounds" % ident)
                continue
            if node.tag == "textAnnotation" and notes is None:
                notes = _annotations(model)
            parts, cut, outside = _shape(model, node, di, b, name, notes or {})
            box.append((b[0], b[1], b[0] + b[2], b[1] + b[3]))
            layer = pools if node.tag in ("participant", "lane") else shapes
            layer.append(_group(ident, parts, highlight, name if cut else None, prefix))
            if not outside:
                name = ""
            fallback = (b[0] + b[2] / 2, b[1] + b[3] + 5)
        seen.add(ident)
        if label:
            box.append((label[0], label[1], label[0] + label[2], label[1] + label[3]))
        if name:
            labels.append(_label(ident, name, label, fallback, box))
    for ident in sorted(highlight - seen):
        warnings.append("skipped %s: highlight id not on this plane" % ident)
    x0 = min((b[0] for b in box), default=0) - MARGIN
    y0 = min((b[1] for b in box), default=0) - MARGIN
    w = max((b[2] for b in box), default=0) - x0 + MARGIN
    h = max((b[3] for b in box), default=0) - y0 + MARGIN
    head = ('<svg class="bpmn" role="img" data-ste="skip" data-plane="%s" viewBox="%s %s %s %s" '
            'width="%s" height="%s" xmlns="http://www.w3.org/2000/svg">' % (
                esc(plane.id), f(x0), f(y0), f(w), f(h), f(w), f(h)))
    title = '<title id="%s-title">%s</title>' % (
        esc(prefix), esc(clean(plane.name or plane.id)))
    out = [head, title, _defs(prefix)] + pools + shapes + edges + labels + ["</svg>"]
    return "\n".join(out) + "\n", warnings
