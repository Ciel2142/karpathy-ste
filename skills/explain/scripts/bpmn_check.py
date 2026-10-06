"""Coverage check for `bpmn.py check`: a page against every .bpmn file it cites (spec 2.4).

The four conditions: every plane is drawn, every sub-process is cited, every label is current, and
every diagram matches its file. A plane or sub-process that p.not-covered names is excused. A sheet
skips conditions 1 and 2.
bpmn.py passes `load` in, so this module does not import bpmn.
"""

import os
from html.parser import HTMLParser

from bpmn_label import NS_DI, NS_MODEL, BpmnError, bpmn_cites, clean, label_of, owner, page_root


class _Page(HTMLParser):
    """Collects each svg.bpmn as [section, data-plane, data-ids] and the text of p.not-covered."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.diagrams = []
        self.not_covered = []
        self._sections = []
        self._svg_depth = 0
        self._in_not_covered = False

    def handle_starttag(self, tag, attrs):
        values = {name: (value or "") for name, value in attrs}
        classes = values.get("class", "").split()
        if tag == "section":
            self._sections.append(values.get("id", "").strip())
        elif tag == "svg" and self._svg_depth:
            self._svg_depth += 1
        elif tag == "svg" and "bpmn" in classes:
            self._svg_depth = 1
            section = next((i for i in reversed(self._sections) if i), "page")
            self.diagrams.append([section, values.get("data-plane", "").strip(), []])
        elif tag == "p" and "not-covered" in classes:
            self._in_not_covered = True
        if self._svg_depth and "data-id" in values:
            self.diagrams[-1][2].append(values["data-id"])

    def handle_endtag(self, tag):
        if tag == "section" and self._sections:
            self._sections.pop()
        elif tag == "svg" and self._svg_depth:
            self._svg_depth -= 1
        elif tag == "p":
            self._in_not_covered = False

    def handle_data(self, data):
        if self._in_not_covered:
            self.not_covered.append(data)


def _element(model, index):
    """The model element a line owner explains: a DI node stands for its bpmnElement."""
    node = model.nodes[index]
    if node.ns != NS_DI:
        return index
    while node is not None:
        ref = node.attrs.get("bpmnElement")
        if ref:
            return model.by_id.get(ref)
        node = model.nodes[node.parent] if node.parent is not None else None
    return None


def _label_failure(model, cite, index):
    """The condition 3 failure of one cite whose line has owner `index`, or None when its label is current."""
    where = "%s | label | %s:%d" % (cite.section, cite.path, cite.line)
    if index is None:
        return where + " | no element"
    expected = label_of(model, index)
    if cite.label is None:
        return where + " | missing"
    if cite.label != expected:
        return '%s | stale: "%s" is not "%s"' % (where, cite.label, expected)
    return None


def _load_cited(cites, root, load):
    """(file lines, {full path: (data-path, model)}, cite results) for the cites, in page order.

    A file that cannot load gives one file line and no model; its cites are skipped."""
    file_lines, files, results = [], {}, []
    for cite in cites:
        # Without a root, the key is the data-path itself: one line per cited path.
        full = cite.path if root is None else os.path.normpath(os.path.join(root, cite.path))
        if full not in files:
            files[full] = (cite.path, None)
            if root is None:
                file_lines.append("%s | file | %s | data-root missing" % (cite.section, cite.path))
            else:
                try:
                    files[full] = (cite.path, load(full))
                except BpmnError as error:
                    file_lines.append("%s | file | %s | %s" % (cite.section, cite.path, error))
        model = files[full][1]
        if model is not None:
            results.append((full, model, cite))
    return file_lines, files, results


def _key(node):
    """The name by which Not covered names a model element: its name, or its id when it has none."""
    return clean(node.attrs.get("name")) or node.attrs["id"]


def _named(not_covered, models):
    """The element keys that Not covered names as whole names.

    Longer keys match first and their match is blanked, so a key inside a longer key does not match there."""
    keys = {_key(n) for m in models for n in m.nodes if n.ns == NS_MODEL and "id" in n.attrs}
    text, found = not_covered, set()
    for key in sorted(keys, key=lambda k: (-len(k), k)):
        if key in text:
            found.add(key)
            text = text.replace(key, "\0")
    return found


def _coverage(model, covered, drawn, named):
    """Condition 1 and 2 lines for one file."""
    lines = []
    for plane in model.planes:
        name = clean(plane.name) or plane.id
        if plane.id not in drawn and name not in named:
            lines.append("page | plane | %s (%s) has no svg.bpmn and is not in Not covered" % (plane.id, name))
    for index, node in enumerate(model.nodes):
        if node.ns != NS_MODEL or node.tag != "subProcess" or "id" not in node.attrs:
            continue
        name = _key(node)
        if index not in covered and name not in named:
            lines.append(
                "page | sub-process | %s (%s) has no cite and is not in Not covered" % (node.attrs["id"], name)
            )
    return lines


def _diagram_lines(diagrams, files, any_unloaded):
    """Condition 4 lines: each diagram's plane and data-ids against the cited files."""
    lines = []
    for section, plane, ids in diagrams:
        holders = [(path, m) for path, m in files.values() if m and any(p.id == plane for p in m.planes)]
        if not holders:
            if not any_unloaded:
                lines.append("%s | diagram | data-plane %s is no plane of a cited file" % (section, plane))
            continue
        for ident in dict.fromkeys(ids):
            if not any(ident in m.by_id for _path, m in holders):
                lines.append("%s | diagram | data-id %s is not in %s" % (section, ident, holders[0][0]))
    return lines


def check_page(html, html_dir, load, sheet=False):
    """Return (failure lines, whether the page cites a .bpmn file).

    `load` reads a .bpmn path into a model and raises BpmnError. A sheet is one screen, so it skips
    conditions 1 and 2."""
    cites = bpmn_cites(html)
    if not cites:
        return [], False
    page = _Page()
    page.feed(html)
    page.close()
    not_covered = " ".join(" ".join(page.not_covered).split())
    drawn = {plane for _section, plane, _ids in page.diagrams}
    file_lines, files, results = _load_cited(cites, page_root(html, html_dir), load)
    covered = {full: set() for full in files}
    label_lines = []
    for full, model, cite in results:
        index = owner(model, cite.line)
        if index is not None:
            covered[full].add(_element(model, index))
        failure = _label_failure(model, cite, index)
        if failure:
            label_lines.append(failure)
    coverage_lines = []
    named = _named(not_covered, [model for _path, model in files.values() if model is not None])
    for full, (_path, model) in files.items():
        if model is not None and not sheet:
            coverage_lines.extend(_coverage(model, covered[full], drawn, named))
    any_unloaded = any(model is None for _path, model in files.values())
    diagram_lines = _diagram_lines(page.diagrams, files, any_unloaded)
    return file_lines + coverage_lines + label_lines + diagram_lines, True
