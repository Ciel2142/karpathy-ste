#!/usr/bin/env python3
"""Transcript page for the explain video rung.

Usage: transcript.py <script.json> <output-dir> [--narrator "<text>"]

Writes <output-dir>/index.html (from templates/video.html) and <output-dir>/narration.md.
Exit 0 on success; exit 2 with one line on stderr for a usage error, an unreadable or
invalid script, or a code source that cannot be read. Stdlib only.
"""

import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "video.html"
USAGE = 'usage: transcript.py <script.json> <output-dir> [--narrator "<text>"]'
MAX_SNIPPET_WORDS = 12
MARKER = re.compile(r"\{\{(\w+)\}\}")
BACKTICK_SPAN = re.compile(r"`([^`]*)`")


class ScriptError(Exception):
    """A fault the caller can fix; main() prints it as one line and exits 2."""


def esc(value):
    return html.escape(str(value), quote=True)


def is_url(path):
    return path.startswith(("http://", "https://"))


def inline(text):
    """Escape text; each backtick span becomes <code>."""
    parts = BACKTICK_SPAN.split(text)
    return "".join(esc(p) if i % 2 == 0 else "<code>%s</code>" % esc(p) for i, p in enumerate(parts))


def source_lines(root, path):
    """Lines of <root>/<path>: no trailing newline, no carriage returns."""
    text = (Path(root) / path).read_text(encoding="utf-8")
    lines = [line.rstrip("\r") for line in text.split("\n")]
    if lines and lines[-1] == "":
        lines.pop()
    return lines


# ---------- cites ----------

def tail_labels(paths):
    """Map each non-URL path to its basename, or to the shortest tail of whole path
    segments, from the right, that no other cited path shares."""
    distinct = sorted({p for p in paths if not is_url(p)})
    labels = {}
    for path in distinct:
        segments = path.split("/")
        others = [o.split("/") for o in distinct if o != path]
        labels[path] = path
        for size in range(1, len(segments) + 1):
            tail = segments[-size:]
            if not any(o[-size:] == tail for o in others):
                labels[path] = "/".join(tail)
                break
    return labels


class Cites:
    """Renders <cite> elements for one script: labels and the untracked mark."""

    def __init__(self, script):
        paths = [c["path"] for scene in script["scenes"] for c in scene["cites"]]
        paths += [s["props"]["source"]["path"] for s in script["scenes"]
                  if s["component"] == "code-with-line-highlights"]
        self.labels = tail_labels(paths)
        self.root = script["provenance"]["root"]
        self.has_git = os.path.exists(os.path.join(self.root, ".git"))
        self._untracked = {}

    def untracked(self, path):
        if not self.has_git:
            return False
        if path not in self._untracked:
            try:
                done = subprocess.run(
                    ["git", "-C", self.root, "ls-files", "--error-unmatch", "--", path],
                    capture_output=True,
                )
                self._untracked[path] = done.returncode != 0
            except OSError:
                self._untracked[path] = False
        return self._untracked[path]

    def render(self, cite):
        path = cite["path"]
        snippet = cite["snippet"]
        if is_url(path):
            host = urlsplit(path).netloc or path
            return '<cite data-path="%s" data-snippet="%s">%s "%s"</cite>' % (
                esc(path), esc(snippet), esc(host), esc(snippet))
        line = cite["line"]
        mark = " untracked" if self.untracked(path) else ""
        return '<cite data-path="%s" data-line="%s" data-snippet="%s">%s:%s "%s"%s</cite>' % (
            esc(path), esc(line), esc(snippet), esc(self.labels[path]), esc(line), esc(snippet), mark)


# ---------- scene bodies ----------

def body_title(props, ctx):
    return ["<p>%s</p>" % esc(props["subtitle"])], []


def body_bullets(props, ctx):
    items = "".join("<li>%s</li>" % esc(b["text"]) for b in props["bullets"])
    return ["<ul>%s</ul>" % items], []


def body_diagram(props, ctx):
    names = {n["id"]: n["label"] for n in props["nodes"]}
    items = []
    for node in props["nodes"]:
        sub = ": " + node["sub"] if node.get("sub") else ""
        items.append("<li>%s%s</li>" % (esc(node["label"]), esc(sub)))
    for edge in props["edges"]:
        label = ": " + edge["label"] if edge.get("label") else ""
        items.append("<li>%s to %s%s</li>" % (esc(names[edge["from"]]), esc(names[edge["to"]]), esc(label)))
    return ['<ul data-ste="skip">%s</ul>' % "".join(items)], []


def code_cite(lines, source):
    """The cite of a code figure: the first line with text, normally the first line."""
    for offset, text in enumerate(lines):
        words = text.split()
        if words:
            snippet = " ".join(words[:MAX_SNIPPET_WORDS])
            return {"path": source["path"], "line": source["from"] + offset, "snippet": snippet}
    raise ScriptError("code source %s lines %d-%d are all blank" % (source["path"], source["from"], source["to"]))


def body_code(props, ctx):
    source = props["source"]
    first, last = source["from"], source["to"]
    lines = source_lines(ctx["root"], source["path"])[max(first, 1) - 1:last] if first >= 1 else []
    if not lines or last < first or len(lines) != last - first + 1:
        raise ScriptError("code source %s lines %s-%s are outside the file" % (source["path"], first, last))
    cite = code_cite(lines, source)
    name = ctx["cites"].labels[source["path"]]
    figure = ('<figure class="code"><pre><code>%s</code></pre>'
              "<figcaption><code>%s:%s</code></figcaption></figure>"
              % (esc("\n".join(lines)), esc(name), esc(first)))
    return [figure], [cite]


def body_before_after(props, ctx):
    def column(side):
        items = "".join("<li>%s</li>" % esc(line) for line in side["lines"])
        return "<div><h3>%s</h3><ul>%s</ul></div>" % (esc(side["heading"]), items)
    return ['<div class="before-after">%s%s</div>' % (column(props["before"]), column(props["after"]))], []


BODIES = {
    "title": body_title,
    "bullets-appear": body_bullets,
    "diagram-with-highlight-walk": body_diagram,
    "code-with-line-highlights": body_code,
    "before-after": body_before_after,
}


def render_scene(scene, ctx):
    try:
        body = BODIES[scene["component"]]
    except KeyError:
        raise ScriptError("scene %s: unknown component %s" % (scene["id"], scene["component"]))
    blocks, extra = body(scene["props"], ctx)
    cites = "".join("<li>%s</li>" % ctx["cites"].render(c) for c in extra + scene["cites"])
    return "\n".join(
        ['<section id="%s">' % esc(scene["id"]),
         "<h2>%s</h2>" % esc(scene["props"]["title"]),
         "<p>%s</p>" % inline(scene["narration"])]
        + blocks
        + ['<ul class="cites" data-ste="skip">%s</ul>' % cites, "</section>"]
    )


# ---------- page and narration ----------

def render_page(template, script, narrator):
    prov = script["provenance"]
    ctx = {"root": prov["root"], "cites": Cites(script)}
    nav = "".join('<a href="#%s">%s</a>' % (esc(s["id"]), esc(s["props"]["title"])) for s in script["scenes"])
    values = {
        "title": esc(script["title"]),
        "nav": nav,
        "sections": "\n\n".join(render_scene(s, ctx) for s in script["scenes"]),
        "root": esc(prov["root"]),
        "kind": esc(script["subject"]["kind"]),
        "subject": esc("%s (%s)" % (script["subject"]["text"], script["subject"]["kind"])),
        "source": esc(prov["source"]),
        "commit": esc(prov["commit"]),
        "dirty": esc(prov["dirty"]),
        "date": esc(prov["date"]),
        "narrator": esc(narrator),
        "not_covered": esc(prov["not_covered"]),
    }
    return MARKER.sub(lambda m: values[m.group(1)], template)


def render_narration(script):
    parts = ["# %s\n" % script["title"]]
    for scene in script["scenes"]:
        parts.append("## %s\n\n%s\n" % (scene["props"]["title"], scene["narration"]))
    return "\n".join(parts)


# ---------- command line ----------

def parse_args(argv):
    narrator = "pending"
    positional = []
    args = iter(argv)
    for arg in args:
        if arg == "--narrator":
            try:
                narrator = next(args)
            except StopIteration:
                raise ScriptError("--narrator needs a value")
        else:
            positional.append(arg)
    if len(positional) != 2:
        raise ScriptError(USAGE)
    return positional[0], positional[1], narrator


def load_script(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as error:
        raise ScriptError("cannot read %s: %s" % (path, error.strerror or error))
    except ValueError as error:
        raise ScriptError("%s is not valid JSON: %s" % (path, error))


def write(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def main(argv):
    try:
        script_path, out_dir, narrator = parse_args(argv)
        script = load_script(script_path)
        page = render_page(TEMPLATE.read_text(encoding="utf-8"), script, narrator)
        narration = render_narration(script)
        os.makedirs(out_dir, exist_ok=True)
        write(os.path.join(out_dir, "index.html"), page)
        write(os.path.join(out_dir, "narration.md"), narration)
    except ScriptError as error:
        sys.stderr.write("transcript.py: %s\n" % error)
        return 2
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        sys.stderr.write("transcript.py: script does not match the contract: %s %s\n" % (type(error).__name__, error))
        return 2
    except OSError as error:
        sys.stderr.write("transcript.py: %s\n" % error)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
