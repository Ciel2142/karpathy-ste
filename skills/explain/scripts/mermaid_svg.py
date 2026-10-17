#!/usr/bin/env python3
"""Mermaid renderer for `explain`: Mermaid text to an inline SVG through headless Chrome.

Usage: mermaid_svg.py render <in.mmd> [<out.svg>] [--title <text>]
       mermaid_svg.py inline <index.html>
Env:   EXPLAIN_MERMAID_JS  the pinned mermaid bundle (default
                           $HOME/karpathy/video-workspace/mermaid/mermaid-12.2.0.min.js);
                           fetched on the first run and checked by sha256
       MERMAID_TIMEOUT     seconds to wait for Chrome (default 60)
inline: every `<figure class="mermaid" data-src="<dir>/<id>.mmd">` of the page gets its SVG as the
first child, and the SVG is also written to `<dir>/<id>.svg`; a second run replaces the SVG.
Exit 0 on success, 1 on a render failure or a fault in a figure of the page, 2 on a usage error,
Chrome not found, a bundle fault or (render only) a bad id.
Output: `mermaid: ok <n> diagrams` is the last line on success. Every failure is one line, and a
page with several faults lists one line each, in page order:
`mermaid: FAIL <id> <message>` (Mermaid's parse message, `no viewBox` or `foreignObject in output`),
`mermaid: FAIL <id> bad id`, `mermaid: FAIL figure <n> no data-src`,
`mermaid: FAIL <id> cannot read <data-src>`, `mermaid: FAIL <id> duplicate id`,
`mermaid: FAIL Chrome not found <path>`, `mermaid: FAIL timeout`,
`mermaid: FAIL harness incomplete`, `mermaid: FAIL sha256 <got>`,
`mermaid: FAIL download <name>: <error>` or `mermaid: FAIL bundle <path>: <error>`.
"""

import argparse
import contextlib
import hashlib
import html
import http.client
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import NamedTuple

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


# --- Chrome ---------------------------------------------------------------------------------
# One harness page renders every diagram and one headless Chrome run dumps its DOM. Chrome may
# print the dump and never exit: it runs in its own process group, the dump is polled for </html>,
# then the group is killed and swept by the work path, as scripts/verify.sh does.
# --virtual-time-budget=<timeout * 1000> is required with more than one diagram: --dump-dom
# fires when the page first goes idle, not when the harness script ends, so the second diagram
# was still unrendered in the dump (Chrome 155: out-1 ok, out-2 without a status, no
# data-mermaid on <html>, the same bytes on every run). The budget holds the dump until every
# await of the loop has resolved; the real-time poll below still bounds the run to `timeout`.

HARNESS = """<!doctype html><html><head><meta charset="utf-8"></head><body>%(outs)s
<script>%(bundle)s</script>
<script type="application/json" id="diagrams">%(diagrams)s</script>
<script>
mermaid.initialize(%(config)s);
(async () => {
  const diagrams = JSON.parse(document.getElementById("diagrams").textContent);
  let allOk = true;
  for (let i = 0; i < diagrams.length; i++) {
    const out = document.getElementById("out-" + (i + 1));
    const area = document.getElementById("svg-" + (i + 1));
    try {
      const result = await mermaid.render(diagrams[i][0], diagrams[i][1]);
      area.textContent = result.svg;
      out.setAttribute("data-status", "ok");
    } catch (err) {
      allOk = false;
      out.setAttribute("data-status", "fail");
      out.setAttribute("data-message", String(err && err.message || err).split("\\n")[0]);
    }
  }
  document.documentElement.setAttribute("data-mermaid", allOk ? "OK" : "FAIL");
})();
</script></body></html>
"""
HTML_TAG = re.compile(r"<html\b[^>]*>")


def read_timeout():
    """MERMAID_TIMEOUT in seconds (the is_count rule of verify.sh), else DEFAULT_TIMEOUT."""
    value = os.environ.get("MERMAID_TIMEOUT")
    if not value:
        return DEFAULT_TIMEOUT
    if not re.fullmatch(r"[1-9][0-9]*", value):
        raise MermaidError("usage: MERMAID_TIMEOUT must be a positive integer: " + value, 2)
    return int(value)


def script_json(value):
    r"""JSON to inline in a <script>: every `</` written as `<\/`."""
    return json.dumps(value).replace("</", "<\\/")


def harness_html(bundle_js, diagrams):
    """The harness page: the result divs first (so the dump finds them before any script
    text), then the bundle, the (id, text) list as JSON and the script that renders them."""
    outs = "".join(
        '<div id="out-%d"><textarea id="svg-%d"></textarea></div>' % (n, n)
        for n in range(1, len(diagrams) + 1)
    )
    return HARNESS % {
        "outs": outs, "bundle": bundle_js, "config": script_json(CONFIG),
        "diagrams": script_json([[diagram_id, text] for diagram_id, text in diagrams]),
    }


def dump_complete(dump):
    """True once the dump ends with </html> (white space after it allowed)."""
    with open(dump, "rb") as handle:
        handle.seek(max(0, handle.seek(0, os.SEEK_END) - 64))
        return handle.read().rstrip().endswith(b"</html>")


def stop_chrome(proc, work):
    """Kill the process group, then sweep by the work path until 3 polls in a row are clear."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (PermissionError, ProcessLookupError):
        proc.kill()
    proc.wait()
    pattern = "".join("\\" + c if c in "[]\\.*^$+?(){}|" else c for c in str(work))
    quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    clear = 0
    for _ in range(25):
        if subprocess.run(["pgrep", "-f", "--", pattern], **quiet).returncode == 0:
            subprocess.run(["pkill", "-KILL", "-f", "--", pattern], **quiet)
            clear = 0
        else:
            clear += 1
        time.sleep(0.2)
        if clear == 3:
            return
    print("mermaid_svg.py: Chrome processes survived the kill: %s" % work, file=sys.stderr)


def dump_dom(chrome, work, timeout):
    """Run headless Chrome on <work>/harness.html; return the DOM dump once it is complete."""
    dump = work / "dump.html"
    args = [
        chrome, "--headless=new", "--disable-gpu", "--dump-dom", "--hide-scrollbars",
        "--virtual-time-budget=%d" % (timeout * 1000),
        "--user-data-dir=%s" % (work / "profile"), (work / "harness.html").as_uri(),
    ]
    with open(dump, "wb") as out:
        try:
            proc = subprocess.Popen(
                args, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            raise MermaidError("mermaid: FAIL Chrome not found " + chrome, 2) from None
    try:
        deadline = time.monotonic() + timeout
        while not dump_complete(dump):
            if time.monotonic() >= deadline:
                raise MermaidError("mermaid: FAIL timeout")
            time.sleep(0.2)
    finally:
        stop_chrome(proc, work)
    return dump.read_text(encoding="utf-8", errors="replace")


def raise_faults(lines):
    """Print every fault line but the last and raise the last; main prints it, so a run shows
    each fault once, in order."""
    for line in lines[:-1]:
        print(line)
    raise MermaidError(lines[-1])


def read_dump(dump, diagrams):
    """{id: raw SVG} from the harness result in the dump; every failed diagram is a fault."""
    tag = HTML_TAG.search(dump)
    if tag is None or not re.search(r'\sdata-mermaid="', tag.group(0)):
        raise MermaidError("mermaid: FAIL harness incomplete")
    svgs, faults = {}, []
    for n, (diagram_id, _) in enumerate(diagrams, 1):
        found = re.search(
            r'<div id="out-%d"([^>]*)><textarea id="svg-%d">([^<]*)</textarea>' % (n, n), dump
        )
        status = re.search(r'\sdata-status="([^"]*)"', found.group(1)) if found else None
        if status and status.group(1) == "ok":
            svgs[diagram_id] = html.unescape(found.group(2))
        elif status and status.group(1) == "fail":
            message = re.search(r'\sdata-message="([^"]*)"', found.group(1))
            text = " ".join(html.unescape(message.group(1) if message else "").split())
            faults.append(("mermaid: FAIL %s %s" % (diagram_id, text)).rstrip())
        else:
            raise MermaidError("mermaid: FAIL harness incomplete")
    if faults:
        raise_faults(faults)
    return svgs


def render_many(diagrams, bundle, timeout):
    """Render every (id, text) in one Chrome run; return {id: raw SVG} in the given order."""
    for diagram_id, _ in diagrams:
        if not ID.fullmatch(diagram_id):
            raise MermaidError("mermaid: FAIL %s bad id" % diagram_id, 2)
    chrome = CHROME
    if not (os.path.isfile(chrome) and os.access(chrome, os.X_OK)):
        raise MermaidError("mermaid: FAIL Chrome not found " + chrome, 2)
    bundle_js = ensure_bundle(bundle).read_text(encoding="utf-8")
    work = Path(tempfile.mkdtemp(prefix="mermaid.", dir=os.environ.get("TMPDIR") or None))
    try:
        (work / "harness.html").write_text(harness_html(bundle_js, diagrams), encoding="utf-8")
        dump = dump_dom(chrome, work, timeout)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return read_dump(dump, diagrams)


# --- the page -------------------------------------------------------------------------------

FIGURE = re.compile(r'<figure( class="[^"]*\bmermaid\b[^"]*"[^>]*)>(.*?)</figure>', re.S)
DATA_SRC = re.compile(r"""\sdata-src\s*=\s*(?:"([^"]*)"|'([^']*)')""")
FIGCAPTION = re.compile(r"<figcaption\b[^>]*>(.*?)</figcaption>", re.S)
TAG = re.compile(r"<[^>]*>")
SVG_ELEMENT = re.compile(r"<svg\b[^>]*>.*?</svg>\n?", re.S)


class Figure(NamedTuple):
    """One figure.mermaid of a page: start..end is the whole figure in the page text, attrs the
    start tag after `<figure`, inner the text between the tags."""

    n: int
    start: int
    end: int
    attrs: str
    inner: str
    src: str | None
    caption: str | None


def page_figures(html_text):
    """Every figure.mermaid of the page, in page order, numbered from 1."""
    figures = []
    for n, found in enumerate(FIGURE.finditer(html_text), 1):
        attrs, inner = found.group(1), found.group(2)
        src = DATA_SRC.search(attrs)
        caption = FIGCAPTION.search(inner)
        figures.append(Figure(
            n, found.start(), found.end(), attrs, inner,
            None if src is None else (src.group(1) if src.group(1) is not None else src.group(2)),
            None if caption is None else " ".join(
                html.unescape(TAG.sub("", caption.group(1))).split()
            ),
        ))
    return figures


def figure_job(figure, page_dir, seen):
    """(id, text) of the diagram of a figure; raise a fault line when the figure cannot be read.
    `seen` holds the ids of the earlier figures and gets this one."""
    if not figure.src:
        raise MermaidError("mermaid: FAIL figure %d no data-src" % figure.n)
    src = Path(figure.src)
    if src.suffix != ".mmd" or not ID.fullmatch(src.stem):
        shown = src.stem if src.suffix == ".mmd" else src.name
        raise MermaidError("mermaid: FAIL %s bad id" % shown)
    try:
        text = (page_dir / src).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise MermaidError("mermaid: FAIL %s cannot read %s" % (src.stem, figure.src)) from None
    if src.stem in seen:
        raise MermaidError("mermaid: FAIL %s duplicate id" % src.stem)
    seen.add(src.stem)
    return src.stem, text


def finish_figures(figures, jobs, svgs):
    """The finished SVG of each figure, in page order; every fault of the run is listed once."""
    finished, faults = [], []
    for figure, (diagram_id, _) in zip(figures, jobs):
        try:
            finished.append(finish_svg(svgs[diagram_id], diagram_id, figure.caption or diagram_id))
        except MermaidError as exc:
            faults.append(str(exc))
    if faults:
        raise_faults(faults)
    return finished


def fill_figures(html_text, figures, finished):
    """The page text with each SVG as the first child of its figure; an SVG that the figure
    already holds is cut first, with the newline after it, so a second run gives the same text."""
    # From the last figure to the first, so the offsets of the earlier ones stay valid.
    for figure, svg in reversed(list(zip(figures, finished))):
        inner = SVG_ELEMENT.sub("", figure.inner, count=1)
        filled = "<figure%s>%s\n%s</figure>" % (figure.attrs, svg, inner)
        html_text = html_text[: figure.start] + filled + html_text[figure.end:]
    return html_text


def inline_page(page, bundle, timeout):
    """Fill every figure.mermaid of the page; return the number of diagrams.

    The figures are checked and rendered first. The SVG files and then the page are written only
    when every figure has its SVG, so a fault leaves the files as they were."""
    try:
        html_text = page.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise MermaidError(USAGE, 2) from None
    figures = page_figures(html_text)
    jobs, faults, seen = [], [], set()
    for figure in figures:
        try:
            jobs.append(figure_job(figure, page.parent, seen))
        except MermaidError as exc:
            faults.append(str(exc))
    if faults:
        raise_faults(faults)
    if not figures:
        print("mermaid: ok 0 diagrams")
        return 0
    finished = finish_figures(figures, jobs, render_many(jobs, bundle, timeout))
    try:
        for figure, svg in zip(figures, finished):
            svg_file = page.parent / Path(figure.src).with_suffix(".svg")
            svg_file.write_text(svg + "\n", encoding="utf-8")
        page.write_text(fill_figures(html_text, figures, finished), encoding="utf-8")
    except OSError:
        raise MermaidError(USAGE, 2) from None
    print("mermaid: ok %d diagrams" % len(figures))
    return len(figures)


# --- the command line -----------------------------------------------------------------------


class Parser(argparse.ArgumentParser):
    """An argument parser whose every error is the usage line with exit 2."""

    def error(self, message):
        raise MermaidError(USAGE, 2)


def cmd_render(args):
    """render <in.mmd> [<out.svg>] [--title <text>]: one diagram to out, or to stdout."""
    parser = Parser(prog="mermaid_svg.py render", add_help=False)
    parser.add_argument("src")
    parser.add_argument("out", nargs="?")
    parser.add_argument("--title")
    opts = parser.parse_args(args)
    src = Path(opts.src)
    try:
        text = src.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise MermaidError(USAGE, 2) from None
    diagram_id = src.stem
    # With the SVG on stdout, the download lines of a first run go to stderr.
    with contextlib.redirect_stdout(sys.stderr if opts.out is None else sys.stdout):
        raw = render_many([(diagram_id, text)], bundle_path(), read_timeout())[diagram_id]
    svg = finish_svg(raw, diagram_id, diagram_id if opts.title is None else opts.title)
    if opts.out is None:
        print(svg)
        print("mermaid: ok 1 diagrams", file=sys.stderr)
        return 0
    try:
        Path(opts.out).write_text(svg + "\n", encoding="utf-8")
    except OSError:
        raise MermaidError(USAGE, 2) from None
    print("mermaid: ok 1 diagrams")
    return 0


def cmd_inline(args):
    """inline <index.html>: the SVG of every figure.mermaid of the page, in one Chrome run."""
    parser = Parser(prog="mermaid_svg.py inline", add_help=False)
    parser.add_argument("page")
    opts = parser.parse_args(args)
    inline_page(Path(opts.page), bundle_path(), read_timeout())
    return 0


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
