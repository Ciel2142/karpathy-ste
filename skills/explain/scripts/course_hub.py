"""The course hub for `explain --as course` (spec section 7): `render_hub` writes the hub HTML.

The hub reuses the chrome of `templates/page.html`, read at run time (no copy is kept): the
head (palette, type rules, guard part 1), and the scripts after `</footer>` (steps player, Play
all, guard part 2). The region from `<header>` to `</footer>` is replaced with the course body:

- header: the title, the course question and the answer box (one generated sentence per block);
- nav: one link per section, then the Sources switch of the template (last);
- section#flow: the SVG flow (main hops left to right, wrapped into rows of `COLUMNS`; each
  failure hop in a row under its branch hop, joined by a dashed line marked "on failure"; the
  border shows the evidence, with a legend), then the hop list with the hop cites;
- one section per block: its lessons (question, hops, status; a link only for a `done` lesson);
- footer: provenance (`data-root` is the absolute resolved root, `data-kind="topic"`, a row per
  source with the moved note) and `p.not-covered`.

Generated sentences are STE-80. Ids, paths, hashes and statuses sit in `<code>` or in elements
with `data-ste="skip"`. Every course.json string is escaped. The SVG is 600 units wide with
18-unit text, so the text stays at 14 px or more when the column is 468 px wide.
"""

import datetime
import html
import os
import re
import textwrap

import course as plan

HEADER = "<header>"
FOOTER_END = "</footer>"
RUNG_META = '<meta name="explain-rung" content="page">'
SWITCH = '<label class="sources"><input type="checkbox" id="show-sources"> Sources</label>'

# The SVG geometry, in viewBox units (rungs/page.md "Diagram patterns").
VIEW_W = 600
COLUMNS = 4            # main hops per row: a box of 122 units holds 10 sans characters a line
GAP_X = 36             # the arrow between two main boxes
WRAP_W = 24            # the right margin that holds the connector to the next row
MAX_BOX_W = 200
LINE_H = 22            # one line of 18-unit text
PAD_Y = 12
FAIL_GAP = 56          # from a box to the failure box under it: the dashed "on failure" line
ROW_GAP = 48           # from the failure boxes of a row to the next row
CHAR_W = 10            # the width of one sans character of 18 units, rounded up
LABEL = "on failure"
LABEL_W = 92
LEGEND_H = 40

HUB_STYLE = """<style>
/* Course hub (course.py hub): the flow diagram. The border of a box shows the evidence of
   its hop: solid for code, dashed for docs, dotted for inferred. */
.diagram rect.failure { fill: var(--bg); }
.diagram rect.ev-docs { stroke-dasharray: 8 5; }
.diagram rect.ev-inferred { stroke-dasharray: 2 4; stroke-width: 2; }
.diagram path.next { fill: none; stroke: var(--ink); stroke-width: 1.5; }
.diagram line.fail { stroke-dasharray: 6 5; }
.diagram a text { fill: var(--accent); text-decoration: underline; }
.diagram text.muted { fill: var(--muted); font-style: italic; }
.hub-meta { color: var(--muted); }
</style>
"""


def esc(value):
    return html.escape(str(value), quote=True)


# --- template ---------------------------------------------------------------------------


def _once(template, anchor):
    count = template.count(anchor)
    if count != 1:
        raise ValueError("template: %s must occur once, found %d" % (anchor, count))
    return template.index(anchor)


def _chrome(template, course):
    """(head, tail): the template before `<header>` and after `</footer>`, with the course
    lang, the course rung meta, the course title, no template comment, and the hub style."""
    start = _once(template, HEADER)
    end = _once(template, FOOTER_END) + len(FOOTER_END)
    if end <= start:
        raise ValueError("template: %s comes before %s" % (FOOTER_END, HEADER))
    head, tail = template[:start], template[end:]
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
    return head, tail


# --- plan helpers -----------------------------------------------------------------------


def _hops(course):
    return [hop for hop in plan._objects(course.get("hops")) if isinstance(hop.get("id"), str)]


def _failure_parent(hop, earlier):
    branch = hop.get("branch")
    return branch if isinstance(branch, str) and branch in earlier else None


def _layout_tree(hops):
    """(main hops in order, {hop id: [failure hops under it]}) by `branch` (an earlier hop)."""
    main, children, earlier = [], {}, set()
    for hop in hops:
        parent = _failure_parent(hop, earlier)
        if parent is None:
            main.append(hop)
        else:
            children.setdefault(parent, []).append(hop)
        earlier.add(hop["id"])
    return main, children


def _stack(hop_id, children):
    """The failure hops that hang under one main hop, depth first."""
    out = []
    for child in children.get(hop_id, []):
        out.append(child)
        out.extend(_stack(child["id"], children))
    return out


def _first_done(course):
    """{hop id: id of the first `done` lesson, in plan order, that covers the hop}."""
    found = {}
    for lesson in plan._lessons(course):
        if lesson.get("status") == "done" and isinstance(lesson.get("id"), str):
            for hop in plan._names(lesson.get("hops")):
                found.setdefault(hop, lesson["id"])
    return found


def _lesson_href(ident):
    return "lessons/%s/index.html" % ident


def _plural(count, word):
    return "%d %s" % (count, word if count == 1 else word + "s")


# --- header and nav ---------------------------------------------------------------------


def _block_sentence(number, block, hops_by_id, failures):
    names = plan._names(
        [hop for lesson in plan._objects(block.get("lessons"))
         for hop in plan._names(lesson.get("hops"))]
    )
    covered = [hops_by_id[h] for h in dict.fromkeys(names) if h in hops_by_id]
    order = list(hops_by_id)
    covered.sort(key=lambda hop: order.index(hop["id"]))
    main = [hop for hop in covered if hop["id"] not in failures]
    failed = len(covered) - len(main)
    head = "Part %d, <q>%s</q>, covers " % (number, esc(block.get("title")))
    if main:
        text = "%s from <code>%s</code> to <code>%s</code>" % (
            _plural(len(main), "step"), esc(main[0].get("from")), esc(main[-1].get("to")))
        if failed:
            text += " and %s" % _plural(failed, "failure path")
    elif failed:
        text = _plural(failed, "failure path")
    else:
        text = "no step"
    return head + text + "."


def _header(course, blocks, hops):
    main, children = _layout_tree(hops)
    failures = {hop["id"] for hop in hops} - {hop["id"] for hop in main}
    hops_by_id = {hop["id"]: hop for hop in hops}
    lead = "The path has %s and %s, in %s." % (
        _plural(len(main), "step"), _plural(len(failures), "failure path"),
        _plural(len(blocks), "part"))
    items = "\n".join(
        "      <li>%s</li>" % _block_sentence(n, block, hops_by_id, failures)
        for n, block in enumerate(blocks, start=1)
    )
    return (
        "<header>\n"
        "  <h1>%s</h1>\n"
        "  <p>%s</p>\n"
        '  <div class="answer">\n'
        "    <p><strong>Short answer.</strong> %s</p>\n"
        '    <ul class="rules">\n%s\n    </ul>\n'
        "  </div>\n"
        "</header>\n"
    ) % (esc(course.get("title")), esc(course.get("question")), lead, items)


def _nav(blocks):
    links = ['  <a href="#flow">Flow</a>'] + [
        '  <a href="#block-%s">%s</a>' % (esc(block["id"]), esc(block.get("title")))
        for block in blocks
    ]
    return '\n<nav id="toc">\n%s\n  %s\n</nav>\n' % ("\n".join(links), SWITCH)


# --- the flow diagram ---------------------------------------------------------------------


def _wrap(text, width):
    return textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=True) or [""]


class _Box:
    def __init__(self, hop, lesson, width, failure):
        self.hop, self.lesson, self.failure = hop, lesson, failure
        chars = max(4, (width - 16) // CHAR_W)
        self.lines = _wrap("%s →" % hop.get("from"), chars) + _wrap(str(hop.get("to")), chars)
        self.muted = None if lesson else "not built"
        self.width = width
        self.x = self.y = 0
        self.height = 2 * PAD_Y + LINE_H * (len(self.lines) + (1 if self.muted else 0))

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
        if self.muted:
            parts.append('<text x="%d" y="%d" text-anchor="middle" class="muted">%s</text>'
                         % (center, baseline, self.muted))
        body = "".join(parts)
        if self.lesson:
            body = '<a href="%s">%s</a>' % (esc(_lesson_href(self.lesson)), body)
        return '<g class="hop" data-hop="%s">%s</g>' % (esc(self.hop["id"]), body)


def _flow_svg(hops, done):
    main, children = _layout_tree(hops)
    columns = max(1, min(COLUMNS, len(main)))
    rows = [main[i:i + columns] for i in range(0, len(main), columns)] or [[]]
    right = VIEW_W - 2 - (WRAP_W if len(rows) > 1 else 0)
    width = min(MAX_BOX_W, (right - 2 - GAP_X * (columns - 1)) // columns)
    parts, y, layout = [], 2, []
    for row in rows:
        boxes = [_Box(hop, done.get(hop["id"]), width, False) for hop in row]
        height = max([box.height for box in boxes] or [0])
        for column, box in enumerate(boxes):
            box.x, box.y, box.height = 2 + column * (width + GAP_X), y, height
        bottom = y + height
        for box in boxes:
            above = box
            for hop in _stack(box.hop["id"], children):
                failure = _Box(hop, done.get(hop["id"]), width, True)
                failure.x, failure.y = box.x, above.y + above.height + FAIL_GAP
                parts.append(_fail_line(above, failure, right))
                parts.append(failure.svg())
                bottom = max(bottom, failure.y + failure.height)
                above = failure
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
    parts.append(_legend(legend_y))
    height = legend_y + LEGEND_H
    title = "The path: %s and %s" % (_plural(len(main), "step"),
                                       _plural(len(hops) - len(main), "failure path"))
    return (
        '    <svg viewBox="0 0 %d %d" role="img" aria-labelledby="hub-flow-title" data-ste="skip">\n'
        '      <title id="hub-flow-title">%s</title>\n'
        '      <defs><marker id="hub-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8"'
        ' markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z"/></marker></defs>\n'
        "%s\n    </svg>\n"
    ) % (VIEW_W, height, title, "\n".join("      " + part for part in parts))


def _fail_line(above, box, right):
    """The dashed line from a box down to the failure box under it, with its label."""
    center = box.x + box.width // 2
    top, end = above.y + above.height, box.y - 3
    label_y = top + FAIL_GAP // 2 + 6
    if center + 8 + LABEL_W <= right:
        label = '<text x="%d" y="%d">%s</text>' % (center + 8, label_y, LABEL)
    else:
        label = '<text x="%d" y="%d" text-anchor="end">%s</text>' % (center - 8, label_y, LABEL)
    return ('<line x1="%d" y1="%d" x2="%d" y2="%d" class="fail" marker-end="url(#hub-arrow)"/>%s'
            % (center, top + 1, center, end, label))


def _wrap_line(last, first, middle, next_top):
    """From the last box of a row, down the right margin, to the first box of the next row."""
    turn_x = VIEW_W - 2 - WRAP_W // 2
    run_y = next_top - ROW_GAP // 2
    center = first.x + first.width // 2
    return ('<path d="M%d %d H%d V%d H%d V%d" class="next" marker-end="url(#hub-arrow)"/>'
            % (last.x + last.width + 1, middle, turn_x, run_y, center, next_top - 3))


def _legend(top):
    parts = ['<text x="2" y="%d">evidence:</text>' % (top + 18)]
    x = 104
    for evidence in plan.EVIDENCE:
        parts.append('<rect x="%d" y="%d" width="36" height="24" class="ev-%s legend"/>'
                     % (x, top, evidence))
        parts.append('<text x="%d" y="%d">%s</text>' % (x + 44, top + 18, evidence))
        x += 44 + len(evidence) * CHAR_W + 28
    return "".join(parts)


# --- sections -----------------------------------------------------------------------------


def _cite(cite):
    path, line, snippet = cite.get("path"), cite.get("line"), cite.get("snippet")
    return (
        '<cite data-path="%s" data-line="%s" data-snippet="%s">%s:%s <code>%s</code></cite>'
        % (esc(path), esc(line), esc(snippet), esc(os.path.basename(str(path))), esc(line),
           esc(snippet))
    )


def _hop_item(hop, failures):
    head = "<code>%s</code> %s → %s, evidence <code>%s</code>" % (
        esc(hop["id"]), esc(hop.get("from")), esc(hop.get("to")), esc(hop.get("evidence")))
    if hop["id"] in failures:
        head += ", on failure of <code>%s</code>" % esc(hop.get("branch"))
    cites = plan._objects(hop.get("cites"))
    block = ""
    if cites:
        block = '\n      <div class="cites">\n%s\n      </div>' % "\n".join(
            "        " + _cite(cite) for cite in cites)
    return ('    <li><div class="hub-meta" data-ste="skip">%s</div>%s%s\n    </li>'
            % (head, esc(hop.get("what")), block))


def _flow_section(hops, done):
    main, _ = _layout_tree(hops)
    failures = {hop["id"] for hop in hops} - {hop["id"] for hop in main}
    items = "\n".join(_hop_item(hop, failures) for hop in hops)
    return (
        '<section id="flow">\n'
        "  <h2>Which steps make the path?</h2>\n"
        '  <figure class="diagram hub-flow">\n%s'
        "    <figcaption>Each box is one step. The main steps go from left to right. "
        "A failure path goes down from its step. The border shows the evidence. "
        "A box with a link opens its lesson. A box without a lesson shows "
        "<q>not built</q>.</figcaption>\n"
        "  </figure>\n"
        "  <p>Each step of the path, with its source lines:</p>\n"
        '  <ul class="rules">\n%s\n  </ul>\n'
        "</section>\n"
    ) % (_flow_svg(hops, done), items)


def _lesson_item(lesson):
    question = esc(lesson.get("question"))
    status = lesson.get("status")
    if status == "done" and isinstance(lesson.get("id"), str):
        question = '<a href="%s">%s</a>' % (esc(_lesson_href(lesson["id"])), question)
    hops = ", ".join("<code>%s</code>" % esc(h) for h in plan._names(lesson.get("hops")))
    meta = "lesson <code>%s</code>; steps %s; status <code>%s</code>" % (
        esc(lesson.get("id")), hops or "none", esc(status))
    if status in plan.NEEDS_REASON and lesson.get("reason"):
        meta += "; reason: %s" % esc(lesson["reason"])
    return '    <li>%s<div class="hub-meta" data-ste="skip">%s</div></li>' % (question, meta)


def _block_section(block):
    items = "\n".join(_lesson_item(lesson) for lesson in plan._objects(block.get("lessons")))
    return (
        '<section id="block-%s">\n'
        "  <h2>%s</h2>\n"
        '  <ul class="rules">\n%s\n  </ul>\n'
        "</section>\n"
    ) % (esc(block["id"]), esc(block.get("title")), items)


# --- footer ---------------------------------------------------------------------------------


def _moved(recorded, current):
    if recorded == current:
        return esc(current)
    return "%s → %s, moved after planning" % (esc(recorded), esc(current))


def _yes_no(dirty):
    return "dirty" if dirty else "no"


def _source_row(course_dir, course, source):
    commit, dirty = plan.git_state(plan.source_dir(course_dir, course, source))
    return (
        '      <div class="wide"><dt>Source %s</dt><dd>%s; commit %s; dirty %s</dd></div>'
        % (esc(source.get("id")), esc(source.get("path")),
           _moved(source.get("commit"), commit),
           _moved(_yes_no(source.get("dirty")), _yes_no(dirty)))
    )


def _review(value):
    if isinstance(value, bool):
        return "on" if value else "off"
    return esc(value)


def _footer(course_dir, course, root):
    rows = [
        '      <div class="wide"><dt>Subject</dt><dd>%s (course)</dd></div>'
        % esc(course.get("title")),
        '      <div class="wide"><dt>Root</dt><dd>%s</dd></div>' % esc(root),
    ]
    rows += [_source_row(course_dir, course, source)
             for source in plan._objects(course.get("sources"))]
    rows += [
        "      <div><dt>Date</dt><dd>%s</dd></div>" % datetime.date.today().isoformat(),
        "      <div><dt>Review</dt><dd>%s</dd></div>" % _review(course.get("review")),
    ]
    gaps = [text for text in course.get("not_covered") or [] if isinstance(text, str)]
    not_covered = " ".join(esc(" ".join(text.split())) for text in gaps) or "none"
    return (
        "\n<footer>\n"
        '  <div id="provenance" data-root="%s" data-kind="topic">\n'
        '    <dl data-ste="skip">\n%s\n    </dl>\n'
        "  </div>\n"
        '  <p class="not-covered">Not covered: %s</p>\n'
        "</footer>"
    ) % (esc(root), "\n".join(rows), not_covered)


# --- the hub --------------------------------------------------------------------------------


def render_hub(course_dir, course, template):
    """The hub HTML of `course` in the chrome of `template` (the text of templates/page.html).

    Raises ValueError when the template lacks an anchor (`<header>`, `</footer>`, the rung meta)
    or holds one more than once."""
    head, tail = _chrome(template, course)
    root = plan.resolve_root(course_dir, course.get("root") if isinstance(course.get("root"), str)
                             else "")
    hops = _hops(course)
    blocks = [block for block in plan._objects(course.get("blocks"))
              if isinstance(block.get("id"), str)]
    done = _first_done(course)
    body = "".join((
        _header(course, blocks, hops),
        _nav(blocks),
        "\n<main>\n",
        _flow_section(hops, done),
        "".join("\n" + _block_section(block) for block in blocks),
        "</main>\n",
        _footer(course_dir, course, root),
    ))
    return head + body + tail
