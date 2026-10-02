#!/usr/bin/env python3
"""Citation verifier for `explain` artifacts: check 3 of verify.sh.

Usage: cite_check.py <index.html>
Exit 0 when every citation holds, 1 with one failure per line, 2 on a usage or read error.
"""

import os
import re
import sys
from html.parser import HTMLParser

KINDS = ("file", "directory", "topic", "conversation")
SECTION_KINDS = ("file", "directory")
MAX_WORDS = 12
USAGE = "usage: cite_check.py <index.html>\n"
POSITIVE_INT = re.compile(r"[0-9]+")
HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")


class _Section:
    def __init__(self, ident):
        self.ident = ident
        self.heading = ""
        self.has_cite = False


class _Collector(HTMLParser):
    """Collects the provenance attributes, every <cite> and every <section>."""

    def __init__(self):
        super().__init__()
        self.provenance = None
        self.cites = []
        self.sections = []
        self._open = []
        self._heading_into = None

    def handle_starttag(self, tag, attrs):
        values = {name: (value or "") for name, value in attrs}
        if self.provenance is None and values.get("id") == "provenance":
            self.provenance = values
        if tag == "section":
            section = _Section(values.get("id", "").strip())
            self.sections.append(section)
            self._open.append(section)
        elif tag == "cite":
            self.cites.append(values)
            for section in self._open:
                section.has_cite = True
        elif tag in HEADINGS and self._open and not self._open[-1].heading:
            self._heading_into = self._open[-1]

    def handle_endtag(self, tag):
        if tag == "section" and self._open:
            self._open.pop()
        elif tag in HEADINGS:
            self._heading_into = None

    def handle_data(self, data):
        if self._heading_into is not None:
            self._heading_into.heading += data


def _normalize(text):
    return " ".join(text.split())


def _read_lines(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    if not text:
        return []
    if text.endswith("\n"):
        text = text[:-1]
    return text.split("\n")


def _check_cite(number, values, root):
    """Return the failure messages for one non-URL-skipped citation."""
    path = values.get("data-path", "").strip()
    line_text = values.get("data-line", "").strip()
    snippet = values.get("data-snippet", "")
    if path.startswith(("http://", "https://")):
        return []
    label = "cite %d (%s:%s)" % (number, path or "?", line_text or "?")
    missing = [
        name
        for name, value in (
            ("data-path", path),
            ("data-line", line_text),
            ("data-snippet", snippet.strip()),
        )
        if not value
    ]
    if missing:
        return ["%s: %s missing" % (label, ", ".join(missing))]
    failures = []
    words = len(snippet.split())
    if words > MAX_WORDS:
        failures.append("%s: snippet has %d words (max %d)" % (label, words, MAX_WORDS))
    if root is None:
        return failures + ["%s: data-root missing" % label]
    full = os.path.join(root, path)
    if not os.path.isfile(full):
        return failures + ["%s: file missing: %s" % (label, full)]
    if not POSITIVE_INT.fullmatch(line_text) or int(line_text) < 1:
        return failures + ["%s: data-line is not a positive integer" % label]
    try:
        lines = _read_lines(full)
    except OSError as error:
        return failures + ["%s: cannot read file: %s" % (label, error)]
    line_no = int(line_text)
    if line_no > len(lines):
        return failures + [
            "%s: line out of range (file has %d lines)" % (label, len(lines))
        ]
    if _normalize(snippet) not in _normalize(lines[line_no - 1]):
        failures.append("%s: snippet not found on that line" % label)
    return failures


def _section_label(section):
    return section.ident or _normalize(section.heading) or "unnamed"


def check(html, html_dir):
    """Return one failure message per problem; an empty list means the document passes."""
    collector = _Collector()
    collector.feed(html)
    collector.close()
    failures = []
    provenance = collector.provenance
    kind = None
    root = None
    if provenance is None:
        failures.append('provenance: missing element with id="provenance"')
    else:
        kind = provenance.get("data-kind", "").strip()
        if not kind:
            failures.append("provenance: missing data-kind")
        elif kind not in KINDS:
            failures.append(
                "provenance: unknown data-kind %r (expected one of %s)"
                % (kind, ", ".join(KINDS))
            )
        data_root = provenance.get("data-root", "").strip()
        if data_root:
            root = os.path.join(html_dir, data_root)
    for number, values in enumerate(collector.cites, start=1):
        failures.extend(_check_cite(number, values, root))
    if kind in SECTION_KINDS:
        for number, section in enumerate(collector.sections, start=1):
            if not section.has_cite:
                failures.append(
                    "section %d (%s): no citation" % (number, _section_label(section))
                )
    return failures


def main(argv):
    if len(argv) != 1:
        sys.stderr.write(USAGE)
        return 2
    try:
        with open(argv[0], encoding="utf-8-sig", errors="replace") as handle:
            html = handle.read()
    except OSError as error:
        sys.stderr.write("cite_check: %s\n" % error)
        return 2
    failures = check(html, os.path.dirname(os.path.abspath(argv[0])))
    for failure in failures:
        sys.stdout.write(failure + "\n")
    if failures:
        sys.stdout.write("cite_check: %d failures\n" % len(failures))
        return 1
    sys.stdout.write("cite_check: ok\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
