"""SVG primitives and event markers for bpmn_svg.py.

A leaf module beside bpmn_label: it imports no other bpmn module. Colours come from CSS classes only.
"""


# Event markers as polygons on a unit square around the centre, scaled by the radius.
MARKS = {
    "error": [(-.5, .55), (-.2, -.55), (.12, .1), (.5, -.55), (.2, .55), (-.12, -.1)],
    "link": [(-.55, -.2), (.1, -.2), (.1, -.5), (.6, 0), (.1, .5), (.1, .2), (-.55, .2)],
    "signal": [(0, -.55), (.5, .4), (-.5, .4)],
    "escalation": [(0, -.55), (.45, .55), (0, .1), (-.45, .55)],
    "compensate": [(-.6, 0), (-.05, -.4), (-.05, 0), (.5, -.4), (.5, .4), (-.05, 0), (-.05, .4)],
    "cancel": [(-.45, -.3), (-.3, -.45), (0, -.15), (.3, -.45), (.45, -.3), (.15, 0),
               (.45, .3), (.3, .45), (0, .15), (-.3, .45), (-.45, .3), (-.15, 0)],
}


def f(value):
    """A number as short text: at most two decimals, no trailing zeros."""
    text = ("%.2f" % value).rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def esc(text):
    """Escape text for an attribute or text content."""
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def circle(cx, cy, r, cls="bpmn-shape", extra=""):
    return '<circle class="%s" cx="%s" cy="%s" r="%s"%s/>' % (cls, f(cx), f(cy), f(r), extra)


def rect(x, y, w, h, extra="", cls="bpmn-shape"):
    return '<rect class="%s" x="%s" y="%s" width="%s" height="%s"%s/>' % (
        cls, f(x), f(y), f(w), f(h), extra)


def path(d, cls="bpmn-flow", extra=""):
    fill = ' fill="none"' if cls == "bpmn-flow" else ""
    return '<path class="%s"%s d="%s"%s/>' % (cls, fill, d, extra)


def poly(points, cx, cy, size):
    return "M" + "L".join("%s %s" % (f(cx + px * size), f(cy + py * size))
                          for px, py in points) + "Z"


def definition(model, node):
    """The kind of an event's first event definition, such as "timer", or None."""
    for child in node.children:
        tag = model.nodes[child].tag
        if tag.endswith("EventDefinition"):
            return tag[:-len("EventDefinition")]
    return None


def event(model, node, b):
    x, y, w, h = b
    cx, cy, r = x + w / 2, y + h / 2, min(w, h) / 2
    dash = ""
    if node.attrs.get("cancelActivity") == "false" or node.attrs.get("isInterrupting") == "false":
        dash = ' stroke-dasharray="4 3"'
    if node.tag == "endEvent":
        parts = [circle(cx, cy, r - 1.5, extra=' stroke-width="4"' + dash)]
    elif node.tag == "startEvent":
        parts = [circle(cx, cy, r, extra=' stroke-width="1.5"' + dash)]
    else:
        parts = [circle(cx, cy, r, extra=dash), circle(cx, cy, r - 3, extra=dash)]
    kind = definition(model, node)
    filled = node.tag in ("endEvent", "intermediateThrowEvent")
    if kind == "timer":
        parts.append(circle(cx, cy, r * .6))
        parts.append(path("M%s %sL%s %sL%s %s" % (f(cx), f(cy - r * .45), f(cx), f(cy),
                                                   f(cx + r * .3), f(cy))))
    elif kind == "message":
        mw, mh = r * 1.0, r * .7
        parts.append(rect(cx - mw / 2, cy - mh / 2, mw, mh, cls="bpmn-text" if filled else "bpmn-shape"))
        if not filled:
            parts.append(path("M%s %sL%s %sL%s %s" % (f(cx - mw / 2), f(cy - mh / 2), f(cx),
                                                       f(cy), f(cx + mw / 2), f(cy - mh / 2))))
    elif kind == "terminate":
        parts.append(circle(cx, cy, r * .6, cls="bpmn-text"))
    elif kind == "conditional":
        parts.append(rect(cx - r * .4, cy - r * .5, r * .8, r))
    elif kind in MARKS:
        parts.append(path(poly(MARKS[kind], cx, cy, r), "bpmn-text" if filled else "bpmn-flow"))
    return parts
