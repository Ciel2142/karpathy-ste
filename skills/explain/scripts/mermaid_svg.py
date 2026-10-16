#!/usr/bin/env python3
"""Mermaid renderer for `explain`: Mermaid text to an inline SVG through headless Chrome.

Usage: mermaid_svg.py render <in.mmd> [<out.svg>] [--title <text>]
       mermaid_svg.py inline <index.html>
Env:   EXPLAIN_MERMAID_JS  the pinned mermaid bundle (default
                           $HOME/karpathy/video-workspace/mermaid/mermaid-12.2.0.min.js);
                           fetched on the first run and checked by sha256
       MERMAID_TIMEOUT     seconds to wait for Chrome (default 60)
Exit 0 on success, 1 on a render failure, 2 on a usage error, Chrome not found or a bundle fault.
Output: `mermaid: ok <n> diagrams` is the last line on success; every failure is one line
`mermaid: FAIL <id> <message>`, `mermaid: FAIL Chrome not found <path>`, `mermaid: FAIL timeout`,
`mermaid: FAIL sha256 <got>`, `mermaid: FAIL download <name>: <error>` or
`mermaid: FAIL bundle <path>: <error>`.
"""

import contextlib
import hashlib
import html
import http.client
import math
import os
import re
import shutil
import signal
import sys
import urllib.request
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BUNDLE_NAME = "mermaid-12.2.0.min.js"
BUNDLE_SIZE = "5.5 MB"
BUNDLE_SHA256 = "a8a6a6f805b074a8261a2825c86f99c8054acb3b35f50bb7e24a4f9f2c3c3b9f"
BUNDLE_URLS = (
    "https://unpkg.com/mermaid@12.2.0/dist/mermaid.min.js",
    "https://cdn.jsdelivr.net/npm/mermaid@12.2.0/dist/mermaid.min.js",
)
DEFAULT_TIMEOUT = 60
# The --sans stack of templates/page.html.
SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif'
CONFIG = {
    "theme": "base",
    "securityLevel": "strict",
    "startOnLoad": False,
    "htmlLabels": False,
    "flowchart": {"htmlLabels": False},
    "fontSize": "14px",
    "themeVariables": {
        "fontFamily": SANS,
        "primaryColor": "#f0eee6",
        "primaryTextColor": "#1f1d1a",
        "primaryBorderColor": "#1f1d1a",
        "lineColor": "#1f1d1a",
        "secondaryColor": "#faf9f5",
        "tertiaryColor": "#faf9f5",
        "background": "#faf9f5",
        "edgeLabelBackground": "#faf9f5",
    },
}
ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
USAGE = (
    "usage: mermaid_svg.py render <in.mmd> [<out.svg>] [--title <text>]"
    " | inline <index.html>"
)


class MermaidError(Exception):
    """A failure that ends the run: str(e) is the whole output line, e.code the exit code."""

    def __init__(self, line, code=1):
        super().__init__(line)
        self.code = code


# --- the bundle -----------------------------------------------------------------------------


def bundle_path():
    """The bundle file: EXPLAIN_MERMAID_JS when set, else the video workspace default."""
    env = os.environ.get("EXPLAIN_MERMAID_JS")
    if env:
        return Path(env)
    return Path.home() / "karpathy" / "video-workspace" / "mermaid" / BUNDLE_NAME


def sha256_of(path):
    """The hex sha256 of a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def one_line(exc):
    """The text of an error on one line."""
    return " ".join(str(exc).split()) or type(exc).__name__


def download_fault(exc):
    """The exit-2 fault for a failed fetch."""
    return MermaidError("mermaid: FAIL download %s: %s" % (BUNDLE_NAME, one_line(exc)), 2)


def fetch(part):
    """Stream the first of BUNDLE_URLS that opens into the part file."""
    last = None
    for url in BUNDLE_URLS:
        try:
            with urllib.request.urlopen(url, timeout=DEFAULT_TIMEOUT) as response:
                with open(part, "wb") as handle:
                    shutil.copyfileobj(response, handle, 1 << 20)
            return
        except (OSError, ValueError, http.client.HTTPException) as exc:
            last = exc
    raise download_fault(last)


def ensure_bundle(path):
    """Return the bundle path after checking its hash; fetch it first when it is missing."""
    path = Path(path)
    if path.is_file():
        try:
            got = sha256_of(path)
        except OSError as exc:
            raise MermaidError("mermaid: FAIL bundle %s: %s" % (path, one_line(exc)), 2) from exc
        if got != BUNDLE_SHA256:
            raise MermaidError("mermaid: FAIL sha256 " + got, 2)
        return path
    print("mermaid: download %s (%s)" % (BUNDLE_NAME, BUNDLE_SIZE))
    part = path.with_name("%s.%d.part" % (path.name, os.getpid()))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fetch(part)
        got = sha256_of(part)
        if got != BUNDLE_SHA256:
            raise MermaidError("mermaid: FAIL sha256 " + got, 2)
        os.replace(part, path)
    except OSError as exc:
        raise download_fault(exc) from exc
    finally:
        with contextlib.suppress(OSError):
            part.unlink(missing_ok=True)
    print("mermaid: downloaded " + BUNDLE_NAME)
    return path


# --- the SVG finish -------------------------------------------------------------------------

ROOT_TAG = re.compile(r"<svg\b[^>]*>")
VIEWBOX = re.compile(r"""\sviewBox\s*=\s*(?:"([^"]*)"|'([^']*)')""")
STYLE = re.compile(r"""\s+style\s*=\s*(?:"([^"]*)"|'([^']*)')""")
MAX_WIDTH = re.compile(r"(?<![\w-])max-width\s*:[^;]*;?")


def attribute(name):
    """A pattern for one attribute of a start tag, with the space before it."""
    return re.compile(r"""\s+%s\s*=\s*(?:"[^"]*"|'[^']*')""" % re.escape(name))


def box_size(tag):
    """The viewBox width and height of a start tag rounded up, or None without a usable one."""
    match = VIEWBOX.search(tag)
    if match is None:
        return None
    try:
        values = [float(n) for n in (match.group(1) or match.group(2)).replace(",", " ").split()]
    except ValueError:
        return None
    if len(values) != 4 or not all(math.isfinite(v) for v in values):
        return None
    return math.ceil(values[2]), math.ceil(values[3])


def without_max_width(tag):
    """The start tag with the max-width declaration cut from its style; an empty style goes."""
    match = STYLE.search(tag)
    if match is None:
        return tag
    value = MAX_WIDTH.sub("", match.group(1) if match.group(1) is not None else match.group(2))
    value = value.strip()
    return tag[: match.start()] + (' style="%s"' % value if value else "") + tag[match.end():]


def finish_svg(svg, diagram_id, title):
    """Give a rendered Mermaid SVG its intrinsic size, role, title and data-ste.

    Only the root start tag and the title after it change; the rest of the text is kept."""
    root = ROOT_TAG.search(svg)
    size = box_size(root.group(0)) if root else None
    if size is None:
        raise MermaidError("mermaid: FAIL %s no viewBox" % diagram_id)
    if "foreignObject" in svg:
        raise MermaidError("mermaid: FAIL %s foreignObject in output" % diagram_id)
    tag = without_max_width(root.group(0))
    for name in ("width", "height", "role", "data-ste", "aria-labelledby"):
        tag = attribute(name).sub("", tag)
    added = ' width="%d" height="%d" role="img" data-ste="skip" aria-labelledby="%s-title"' % (
        size + (diagram_id,)
    )
    title_tag = '<title id="%s-title">%s</title>' % (diagram_id, html.escape(title))
    return tag[:-1] + added + ">" + title_tag + svg[root.end():]


# --- the command line -----------------------------------------------------------------------


def cmd_render(args):
    """render <in.mmd> [<out.svg>] [--title <text>]: lands with the Chrome run."""
    print(USAGE, file=sys.stderr)
    return 2


def cmd_inline(args):
    """inline <index.html>: lands with the page functions."""
    print(USAGE, file=sys.stderr)
    return 2


COMMANDS = {"render": cmd_render, "inline": cmd_inline}


def main(argv):
    """Dispatch on the first argument; a MermaidError becomes its line and its exit code."""
    command = COMMANDS.get(argv[0]) if argv else None
    if command is None:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        return command(argv[1:])
    except MermaidError as exc:
        print(str(exc), file=sys.stderr if str(exc).startswith("usage:") else sys.stdout)
        return exc.code


def _exit_on(code):
    """A signal handler that raises SystemExit, so the `finally` blocks of a run clean up."""

    def handler(signum, frame):
        raise SystemExit(code)

    return handler


if __name__ == "__main__":
    for _signal, _code in ((signal.SIGHUP, 129), (signal.SIGINT, 130), (signal.SIGTERM, 143)):
        signal.signal(_signal, _exit_on(_code))
    sys.exit(main(sys.argv[1:]))
