"""The course hub for `explain --as course` (spec section 7): `render_hub` writes the hub HTML.

The hub reuses the chrome of `templates/page.html`, read at run time (no copy is kept): the
head (palette, type rules, guard part 1), the Sources switch of the nav, and the scripts after
`</footer>` (steps player, Play all, guard part 2). The region from `<header>` to `</footer>` is
replaced with the course body:

- header: the title, the course question and the answer box (one generated sentence per block);
- nav: one link per section, then the Sources switch of the template (last);
- section#flow: the SVG flow, then the hop list with the hop cites. Main hops go left to right
  in rows of `COLUMNS`. Each failure hop hangs under the box of its `branch` hop, indented by
  `INDENT`: a dashed path runs down from the bottom edge of the branch box, beside the earlier
  failures of that hop, and turns right into the failure box (a tree outline). The trunk of one
  branch box is marked "on failure". A failure of a failure hangs under that failure box. The
  border shows the evidence, with a legend;
- one section per block: its lessons (question, hops, status; a link only for a `done` lesson);
- footer: provenance (`data-root` is the absolute resolved root, `data-kind="topic"`, a row per
  source with the moved note) and `p.not-covered`.

The generated text follows the course `lang` (course_hub_text.py: `en`, `ru`). English sentences
are STE-80; Russian ones follow convention 7. Ids, paths, hashes and statuses sit in `<code>` or
in elements with `data-ste="skip"`. Every course.json string is escaped. The SVG is 600 units
wide with 18-unit text, so the text stays at 14 px or more when the column is 468 px wide.
"""

import datetime
import html
import os
import re
import textwrap

import course as plan
from course_hub_text import TEXT, language, plural

HEADER = "<header>"
FOOTER_END = "</footer>"
RUNG_META = '<meta name="explain-rung" content="page">'
SWITCH = re.compile(r'<label class="sources">\s*(<input[^>]*id="show-sources"[^>]*>)[^<]*</label>')

# The SVG geometry, in viewBox units (rungs/page.md "Diagram patterns").
VIEW_W = 600
COLUMNS = 4            # main hops per row: a box of 122 units holds 10 sans characters a line
GAP_X = 36             # the arrow between two main boxes
WRAP_W = 24            # the right margin that holds the connector to the next row
MAX_BOX_W = 200
MIN_BOX_W = 56
LINE_H = 22            # one line of 18-unit text
PAD_Y = 12
INDENT = 22            # a failure box sits this far right of its branch box
TRUNK = 6              # the dashed trunk runs this far right of the branch box's left edge
FAIL_GAP = 56          # from a branch box to its first failure box: room for "on failure"
SIB_GAP = 20           # from one failure subtree to the next failure of the same branch
ROW_GAP = 48           # from the failure boxes of a row to the next row
CHAR_W = 10            # the width of one sans character of 18 units, rounded up
LEGEND_H = 40

HUB_STYLE = """<style>
/* Course hub (course.py hub): the flow diagram. The border of a box shows the evidence of
   its hop: solid for code, dashed for docs, dotted for inferred. */
.diagram rect.failure { fill: var(--bg); }
.diagram rect.ev-docs { stroke-dasharray: 8 5; }
.diagram rect.ev-inferred { stroke-dasharray: 2 4; stroke-width: 2; }
.diagram path.next, .diagram path.fail { fill: none; stroke: var(--ink); stroke-width: 1.5; }
.diagram path.fail { stroke-dasharray: 6 5; }
.diagram a text { fill: var(--accent); text-decoration: underline; }
.diagram text.muted { fill: var(--muted); font-style: italic; }
.hub-meta { color: var(--muted); }
</style>
"""


def esc(value):
    return html.escape(str(value), quote=True)


def code(value):
    return "<code>%s</code>" % esc(value)


# --- template ---------------------------------------------------------------------------


def _once(text, anchor):
    count = text.count(anchor)
    if count != 1:
        raise ValueError("template: %s must occur once, found %d" % (anchor, count))
    return text.index(anchor)


def _chrome(template, course, text):
    """(head, switch, tail): the template before `<header>` (with the course lang, the course
    rung meta, the course title, no template comment, and the hub style), the Sources switch
    of its nav (label in the course language), and the template after `</footer>`."""
    start = _once(template, HEADER)
    end = _once(template, FOOTER_END) + len(FOOTER_END)
    if end <= start:
        raise ValueError("template: %s comes before %s" % (FOOTER_END, HEADER))
    head, region, tail = template[:start], template[start:end], template[end:]
    switches = SWITCH.findall(region)
    if len(switches) != 1:
        raise ValueError("template: the Sources switch must occur once, found %d" % len(switches))
    switch = '<label class="sources">%s %s</label>' % (switches[0], esc(text["sources"]))
    head = re.sub(r"<!--.*?-->\n?", "", head, flags=re.S)  # the fill rules quote the meta
    _once(head, RUNG_META)
    head = head.replace(RUNG_META, '<meta name="explain-rung" content="course">')
    lang = course.get("lang") if isinstance(course.get("lang"), str) and course["lang"] else "en"
    head, count = re.subn(r"<html\b[^>]*>", '<html lang="%s">' % esc(lang), head, count=1)
    if not count:
        raise ValueError("template: no <html> start tag before %s" % HEADER)
    head = re.sub(r"<title>.*?</title>", lambda _: "<title>%s</title>" % esc(course.get("title")),
                  head, count=1, flags=re.S)
    head = head.replace("</head>", HUB_STYLE + "</head>", 1)
    return head, switch, tail


# --- the plan as the hub reads it ---------------------------------------------------------


class _Plan:
    """The parts of `course` that the hub draws, read once."""

    def __init__(self, course):
        self.lang = language(course.get("lang"))
        self.text = TEXT[self.lang]
        self.hops = [hop for hop in plan._objects(course.get("hops"))
                     if isinstance(hop.get("id"), str)]
        self.blocks = [block for block in plan._objects(course.get("blocks"))
                       if isinstance(block.get("id"), str)]
        self.main, self.children, earlier = [], {}, set()
        for hop in self.hops:  # a failure hop branches from an earlier hop (check enforces it)
            branch = hop.get("branch")
            if isinstance(branch, str) and branch in earlier:
                self.children.setdefault(branch, []).append(hop)
            else:
                self.main.append(hop)
            earlier.add(hop["id"])
        self.failures = {hop["id"] for hop in self.hops} - {hop["id"] for hop in self.main}
        self.done = {}  # hop id -> the first done lesson, in plan order, that covers it
        for lesson in plan._lessons(course):
            if lesson.get("status") == "done" and isinstance(lesson.get("id"), str):
                for hop in plan._names(lesson.get("hops")):
                    self.done.setdefault(hop, lesson["id"])

    def count(self, key, number):
        return plural(self.lang, key, number)


def _lesson_href(ident):
    return "lessons/%s/index.html" % ident


# --- header and nav ---------------------------------------------------------------------


def _block_sentence(hub, number, block):
    text = hub.text
    names = [hop for lesson in plan._objects(block.get("lessons"))
             for hop in plan._names(lesson.get("hops"))]
    covered = [hop for hop in hub.hops if hop["id"] in names]  # flow order
    main = [hop for hop in covered if hop["id"] not in hub.failures]
    failed = len(covered) - len(main)
    if main:
        what = text["main"].format(steps=hub.count("step", len(main)),
                                   start=esc(main[0].get("from")), end=esc(main[-1].get("to")))
        if failed:
            what = text["and"].format(main=what, failures=hub.count("failure", failed))
        what = text["covers"].format(what=what)
    elif failed:
        what = text["covers"].format(what=hub.count("failure", failed))
    else:
        what = text["no_step"]
    return text["block"].format(n=number, title=esc(block.get("title")), what=what)


def _header(course, hub):
    lead = hub.text["lead"].format(
        steps=hub.count("step", len(hub.main)),
        failures=hub.count("failure", len(hub.failures)),
        parts=hub.count("part_in", len(hub.blocks)))
    items = "\n".join("      <li>%s</li>" % _block_sentence(hub, n, block)
                      for n, block in enumerate(hub.blocks, start=1))
    return (
        "<header>\n"
        "  <h1>%s</h1>\n"
        "  <p>%s</p>\n"
        '  <div class="answer">\n'
        "    <p><strong>%s</strong> %s</p>\n"
        '    <ul class="rules">\n%s\n    </ul>\n'
        "  </div>\n"
        "</header>\n"
    ) % (esc(course.get("title")), esc(course.get("question")), hub.text["short"], lead, items)


def _nav(hub, switch):
    links = ['  <a href="#flow">%s</a>' % esc(hub.text["nav_flow"])] + [
        '  <a href="#block-%s">%s</a>' % (esc(block["id"]), esc(block.get("title")))
        for block in hub.blocks
    ]
    return '\n<nav id="toc">\n%s\n  %s\n</nav>\n' % ("\n".join(links), switch)


# --- the flow diagram ---------------------------------------------------------------------


def _wrap(text, width):
    return textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=True) or [""]


class _Box:
    def __init__(self, hub, hop, width, failure):
        self.hop, self.failure = hop, failure
        self.lesson = hub.done.get(hop["id"])
        chars = max(4, (width - 16) // CHAR_W)
        self.lines = _wrap("%s →" % hop.get("from"), chars) + _wrap(str(hop.get("to")), chars)
        # "not built" is short italic text: about 9 units a character, 6 units of side room
        self.muted = [] if self.lesson else _wrap(hub.text["not_built"], (width - 12) // 9)
        self.width = width
        self.x = self.y = 0
        self.height = 2 * PAD_Y + LINE_H * (len(self.lines) + len(self.muted))

    @property
    def bottom(self):
        return self.y + self.height

    def svg(self):
        evidence = self.hop.get("evidence") if self.hop.get("evidence") in plan.EVIDENCE else "code"
        classes = "ev-%s%s" % (evidence, " failure" if self.failure else "")
        center = self.x + self.width // 2
        parts = ['<rect x="%d" y="%d" width="%d" height="%d" class="%s"/>'
                 % (self.x, self.y, self.width, self.height, classes)]
        baseline = self.y + PAD_Y + 16
        for line in self.lines:
            parts.append('<text x="%d" y="%d" text-anchor="middle">%s</text>'
                         % (center, baseline, esc(line)))
            baseline += LINE_H
        for line in self.muted:
            parts.append('<text x="%d" y="%d" text-anchor="middle" class="muted">%s</text>'
                         % (center, baseline, esc(line)))
            baseline += LINE_H
        body = "".join(parts)
        if self.lesson:
            body = '<a href="%s">%s</a>' % (esc(_lesson_href(self.lesson)), body)
        return '<g class="hop" data-hop="%s">%s</g>' % (esc(self.hop["id"]), body)


def _failures_under(hub, box, parts):
    """Draw the failure hops of `box` under it, each with its own dashed path from the bottom
    edge of `box`; recurse into failures of failures. Return the bottom of the subtree."""
    children = hub.children.get(box.hop["id"], [])
    if not children:
        return box.bottom
    trunk = box.x + TRUNK
    label = hub.text["on_failure"]
    parts.append('<text x="%d" y="%d">%s</text>'
                 % (trunk + 6, box.bottom + FAIL_GAP // 2 + 6, esc(label)))
    top, bottom = box.bottom + FAIL_GAP, box.bottom
    for hop in children:
        child = _Box(hub, hop, max(MIN_BOX_W, box.width - INDENT), True)
        child.x, child.y = box.x + INDENT, top
        middle = child.y + child.height // 2
        parts.append(
            '<path class="fail" data-from="%s" data-to="%s" d="M%d %d V%d H%d"'
            ' marker-end="url(#hub-arrow)"/>'
            % (esc(box.hop["id"]), esc(hop["id"]), trunk, box.bottom + 1, middle, child.x - 3))
        parts.append(child.svg())
        bottom = _failures_under(hub, child, parts)
        top = bottom + SIB_GAP
    return bottom


def _flow_svg(hub):
    columns = max(1, min(COLUMNS, len(hub.main)))
    rows = [hub.main[i:i + columns] for i in range(0, len(hub.main), columns)] or [[]]
    right = VIEW_W - 2 - (WRAP_W if len(rows) > 1 else 0)
    width = min(MAX_BOX_W, (right - 2 - GAP_X * (columns - 1)) // columns)
    parts, y, layout = [], 2, []
    for row in rows:
        boxes = [_Box(hub, hop, width, False) for hop in row]
        height = max([box.height for box in boxes] or [0])
        for column, box in enumerate(boxes):
            box.x, box.y, box.height = 2 + column * (width + GAP_X), y, height
        bottom = y + height
        for box in boxes:
            bottom = max(bottom, _failures_under(hub, box, parts))
        layout.append((boxes, y, height))
        parts.extend(box.svg() for box in boxes)
        y = bottom + ROW_GAP
    for (boxes, top, height), (following, next_top, _) in zip(layout, layout[1:]):
        parts.append(_wrap_line(boxes[-1], following[0], top + height // 2, next_top))
    for boxes, top, height in layout:
        middle = top + height // 2
        for left, right_box in zip(boxes, boxes[1:]):
            parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" marker-end="url(#hub-arrow)"/>'
                         % (left.x + left.width + 1, middle, right_box.x - 3, middle))
    legend_y = y - ROW_GAP + 28
    parts.append(_legend(hub, legend_y))
    title = hub.text["svg_title"].format(steps=hub.count("step_nom", len(hub.main)),
                                         failures=hub.count("failure_nom", len(hub.failures)))
    return (
        '    <svg viewBox="0 0 %d %d" role="img" aria-labelledby="hub-flow-title" data-ste="skip">\n'
        '      <title id="hub-flow-title">%s</title>\n'
        '      <defs><marker id="hub-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8"'
        ' markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z"/></marker></defs>\n'
        "%s\n    </svg>\n"
    ) % (VIEW_W, legend_y + LEGEND_H, esc(title), "\n".join("      " + part for part in parts))


def _wrap_line(last, first, middle, next_top):
    """From the last box of a row, down the right margin, to the first box of the next row."""
    turn_x = VIEW_W - 2 - WRAP_W // 2
    run_y = next_top - ROW_GAP // 2
    center = first.x + first.width // 2
    return ('<path d="M%d %d H%d V%d H%d V%d" class="next" marker-end="url(#hub-arrow)"/>'
            % (last.x + last.width + 1, middle, turn_x, run_y, center, next_top - 3))


def _legend(hub, top):
    legend = hub.text["legend"]
    parts = ['<text x="2" y="%d">%s</text>' % (top + 18, esc(legend))]
    x = 2 + len(legend) * CHAR_W + 14
    for evidence in plan.EVIDENCE:
        name = hub.text["evidence"][evidence]
        parts.append('<rect x="%d" y="%d" width="36" height="24" class="ev-%s legend"/>'
                     % (x, top, evidence))
        parts.append('<text x="%d" y="%d">%s</text>' % (x + 44, top + 18, esc(name)))
        x += 44 + len(name) * CHAR_W + 28
    return "".join(parts)


# --- sections -----------------------------------------------------------------------------


def _cite(cite):
    path, line, snippet = cite.get("path"), cite.get("line"), cite.get("snippet")
    return (
        '<cite data-path="%s" data-line="%s" data-snippet="%s">%s:%s <code>%s</code></cite>'
        % (esc(path), esc(line), esc(snippet), esc(os.path.basename(str(path))), esc(line),
           esc(snippet))
    )


def _hop_item(hub, hop):
    text = hub.text
    head = "%s %s → %s, %s %s" % (code(hop["id"]), esc(hop.get("from")), esc(hop.get("to")),
                                       text["hop_evidence"], code(hop.get("evidence")))
    if hop["id"] in hub.failures:
        head += ", %s %s" % (text["hop_branch"], code(hop.get("branch")))
    cites = plan._objects(hop.get("cites"))
    block = ""
    if cites:
        block = '\n      <div class="cites">\n%s\n      </div>' % "\n".join(
            "        " + _cite(cite) for cite in cites)
    return ('    <li><div class="hub-meta" data-ste="skip">%s</div>%s%s\n    </li>'
            % (head, esc(hop.get("what")), block))


def _flow_section(hub):
    items = "\n".join(_hop_item(hub, hop) for hop in hub.hops)
    return (
        '<section id="flow">\n'
        "  <h2>%s</h2>\n"
        '  <figure class="diagram hub-flow">\n%s'
        "    <figcaption>%s</figcaption>\n"
        "  </figure>\n"
        "  <p>%s</p>\n"
        '  <ul class="rules">\n%s\n  </ul>\n'
        "</section>\n"
    ) % (hub.text["flow_h2"], _flow_svg(hub), hub.text["caption"], hub.text["list_intro"], items)


def _lesson_item(hub, lesson):
    text = hub.text
    question = esc(lesson.get("question"))
    status = lesson.get("status")
    if status == "done" and isinstance(lesson.get("id"), str):
        question = '<a href="%s">%s</a>' % (esc(_lesson_href(lesson["id"])), question)
    hops = ", ".join(code(h) for h in plan._names(lesson.get("hops")))
    meta = "%s %s; %s %s; %s %s" % (text["lesson"], code(lesson.get("id")), text["steps"],
                                    hops or text["none"], text["status"], code(status))
    if status in plan.NEEDS_REASON and lesson.get("reason"):
        meta += "; %s %s" % (text["reason"], esc(lesson["reason"]))
    return '    <li>%s<div class="hub-meta" data-ste="skip">%s</div></li>' % (question, meta)


def _block_section(hub, block):
    items = "\n".join(_lesson_item(hub, lesson) for lesson in plan._objects(block.get("lessons")))
    return (
        '<section id="block-%s">\n'
        "  <h2>%s</h2>\n"
        '  <ul class="rules">\n%s\n  </ul>\n'
        "</section>\n"
    ) % (esc(block["id"]), esc(block.get("title")), items)


# --- footer ---------------------------------------------------------------------------------


def _moved(hub, recorded, current, as_code):
    show = code if as_code else esc
    if recorded == current:
        return show(current)
    return "%s → %s, %s" % (show(recorded), show(current), esc(hub.text["moved"]))


def _source_row(hub, course_dir, course, source):
    text = hub.text
    commit, dirty = plan.git_state(plan.source_dir(course_dir, course, source))
    no, yes = text["dirty_values"]
    was = yes if source.get("dirty") else no
    return (
        '      <div class="wide"><dt>%s %s</dt><dd>%s; %s %s; %s: %s</dd></div>'
        % (esc(text["source"]), code(source.get("id")), code(source.get("path")),
           esc(text["commit"]), _moved(hub, source.get("commit"), commit, True),
           esc(text["dirty"]), _moved(hub, was, yes if dirty else no, False))
    )


def _review(hub, value):
    if isinstance(value, bool):
        return esc(hub.text["review_values"][int(value)])
    return code(value)


def _footer(hub, course_dir, course, root):
    text = hub.text
    rows = [
        '      <div class="wide"><dt>%s</dt><dd>%s %s</dd></div>'
        % (esc(text["subject"]), esc(course.get("title")), esc(text["subject_kind"])),
        '      <div class="wide"><dt>%s</dt><dd>%s</dd></div>' % (esc(text["root"]), code(root)),
    ]
    rows += [_source_row(hub, course_dir, course, source)
             for source in plan._objects(course.get("sources"))]
    rows += [
        "      <div><dt>%s</dt><dd>%s</dd></div>"
        % (esc(text["date"]), datetime.date.today().isoformat()),
        "      <div><dt>%s</dt><dd>%s</dd></div>"
        % (esc(text["review"]), _review(hub, course.get("review"))),
    ]
    gaps = [item for item in course.get("not_covered") or [] if isinstance(item, str)]
    not_covered = " ".join(esc(" ".join(item.split())) for item in gaps) or esc(text["none"])
    return (
        "\n<footer>\n"
        '  <div id="provenance" data-root="%s" data-kind="topic">\n'
        '    <dl data-ste="skip">\n%s\n    </dl>\n'
        "  </div>\n"
        '  <p class="not-covered">%s %s</p>\n'
        "</footer>"
    ) % (esc(root), "\n".join(rows), esc(text["not_covered"]), not_covered)


# --- the hub --------------------------------------------------------------------------------


def render_hub(course_dir, course, template):
    """The hub HTML of `course` in the chrome of `template` (the text of templates/page.html).

    Raises ValueError when the template lacks an anchor (`<header>`, `</footer>`, the rung meta,
    the Sources switch) or holds one more than once."""
    hub = _Plan(course)
    head, switch, tail = _chrome(template, course, hub.text)
    root = plan.resolve_root(course_dir, course.get("root") if isinstance(course.get("root"), str)
                             else "")
    body = "".join((
        _header(course, hub),
        _nav(hub, switch),
        "\n<main>\n",
        _flow_section(hub),
        "".join("\n" + _block_section(hub, block) for block in hub.blocks),
        "</main>\n",
        _footer(hub, course_dir, course, root),
    ))
    return head + body + tail
