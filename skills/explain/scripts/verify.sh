#!/bin/bash
# verify.sh: the four checks an explain artifact must pass before handoff (spec 5.5; video: three).
#
#   verify.sh <index.html>
#   env VERIFY_TIMEOUT   seconds to wait for each Chrome DOM dump (default 60)
#
#   exit 0  all checks of the rung passed (sheet, page: four; video: three)
#   exit 1  at least one check failed
#   exit 2  usage: no argument, unreadable file, no or unknown <meta name="explain-rung">
#
# stdout carries one line per check, in this order, and nothing else:
#   self-contained: ok | FAIL <n> remote reference(s)
#   render <W>x<H>: ok | FAIL data-verify="<value>" | FAIL no data-verify attribute
#                      | FAIL timeout | FAIL Chrome not found
#                      | FAIL data-verify preset in source
#   citations: ok | FAIL <n> failure(s) | FAIL cite_check exit <code>
#   prose: ok | FAIL <n> error(s) | FAIL lint usage error (exit 2) | FAIL lint exit <code>
# Detail lines follow a failing check, indented by two spaces: each remote reference
# as "<tag> <attr>=<value>" (for CSS: "<tag> style=<fragment>" for a style attribute,
# "style css=<fragment>" for <style> text), each cite_check failure, each lint error.
# A sheet has one render line (1920x1080); a page two (1440x900, 500x844); a video none.
# Every check runs even after an earlier one failed.
#
# Only the guard may write data-verify. If the source <html> start tag already carries
# a data-verify attribute (any value), check 2 fails for each viewport without a dump:
# a static data-verify="OK" would otherwise pass with no guard at all.
#
# Check 2 loads file://<index.html>#verify in headless Chrome with --dump-dom. Chrome
# 154 prints the DOM and then never exits, and macOS has no timeout(1): Chrome runs in
# the background in its own process group, its stdout is polled for </html>, and the
# group is killed once the dump is complete or the timeout elapses. The process-group
# and sweep logic is the same as in snapshot.sh. Every catchable signal (HUP, INT,
# PIPE, TERM) runs the cleanup that kills Chrome; SIGKILL cannot be trapped.

set -u

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCRIPTS=$(cd "$(dirname "$0")" && pwd -P)
CITE_CHECK="$SCRIPTS/cite_check.py"
STE_LINT="$HOME/.claude/skills/ste/scripts/ste_lint.py"

work=""          # temp dir: one Chrome profile and one dump file per viewport
chrome_pid=""
failed=0

usage() {
    echo "verify.sh: $1" >&2
    echo "usage: verify.sh <index.html>" >&2
    exit 2
}

# A positive decimal integer without a leading zero (bash arithmetic reads 08 as octal).
is_count() {
    case "$1" in
        '' | 0* | *[!0-9]*) return 1 ;;
    esac
    return 0
}

# A literal path as an extended regex for pgrep/pkill -f.
regex_literal() {
    printf '%s' "$1" | sed 's/[][\.*^$+?(){}|]/\\&/g'
}

# Kill the current Chrome's process group, then sweep by the temp dir path until
# the process table stays clear for 3 polls in a row (0.6 s): a helper forked while
# the group was being killed would otherwise escape. Returns 1 if a process
# survives 5 s.
stop_chrome() {
    if [ -n "$chrome_pid" ]; then
        kill -KILL -- "-$chrome_pid" 2>/dev/null
        wait "$chrome_pid" 2>/dev/null
        chrome_pid=""
    fi
    [ -n "$work" ] || return 0
    local pattern clear=0 tries=0
    pattern=$(regex_literal "$work")
    while [ "$clear" -lt 3 ]; do
        [ "$tries" -lt 25 ] || return 1
        if pgrep -f -- "$pattern" >/dev/null 2>&1; then
            pkill -KILL -f -- "$pattern" 2>/dev/null
            clear=0
        else
            clear=$((clear + 1))
        fi
        sleep 0.2
        tries=$((tries + 1))
    done
}

cleanup() {
    local status=$?
    trap - EXIT
    trap '' PIPE   # stdout or stderr may be gone; finish the cleanup regardless
    if [ -n "$work" ]; then
        stop_chrome || echo "verify.sh: Chrome processes survived the kill: $work" >&2
        rm -rf "$work"
    fi
    exit "$status"
}

# Percent-encode the characters that would end or corrupt a file:// URL path.
file_url() {
    local p=$1
    p=${p//\%/%25}
    p=${p// /%20}
    p=${p//\#/%23}
    p=${p//\?/%3F}
    echo "file://$p#verify"
}

indent() {
    sed 's/^/  /'
}

# Parse the HTML with html.parser (never the raw text, so escaped code samples
# are text, not markup). Line 1: "rung=<content of the first explain-rung meta>",
# or "rung-missing". Line 2: "preset=yes" if the first <html> start tag has a
# data-verify attribute, else "preset=no". Every further line is one remote
# reference (check 1).
scan() {
    python3 - "$1" <<'PY'
import re
import sys
from html.parser import HTMLParser

REMOTE = ("http://", "https://", "//")
# @import with or without url(, then url( alone; an alternation, so the url( of an
# "@import url(...)" is consumed by the first branch and counted once.
CSS = re.compile(
    r"""@import\s*(?:url\(\s*)?["']?\s*(?P<imp>[^\s"');]+)"""
    r"""|url\(\s*["']?\s*(?P<url>[^\s"')]+)""",
    re.IGNORECASE,
)


def remote(value):
    return value.strip().lower().startswith(REMOTE)


def css_refs(text):
    for match in CSS.finditer(text):
        target = match.group("imp") or match.group("url")
        if remote(target):
            yield match.group(0)


class Scanner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rung = None
        self.preset = None   # data-verify on the first <html> start tag
        self.refs = []
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        values = [(name, value or "") for name, value in attrs]
        if tag == "html" and self.preset is None:
            self.preset = any(name == "data-verify" for name, _ in values)
        if tag == "meta" and self.rung is None:
            named = dict(values)
            if named.get("name", "").strip().lower() == "explain-rung":
                self.rung = named.get("content", "").strip()
        for name, value in values:
            if name in ("src", "poster") or (name == "href" and tag != "a"):
                if remote(value):
                    self.refs.append("%s %s=%s" % (tag, name, value.strip()))
            elif name == "srcset":
                if any(remote(part) for part in value.split(",")):
                    self.refs.append("%s %s=%s" % (tag, name, value.strip()))
            elif name == "style":
                for fragment in css_refs(value):
                    self.refs.append("%s style=%s" % (tag, fragment))
        if tag == "style":
            self.in_style = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag == "style":
            self.in_style = False

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            for fragment in css_refs(data):
                self.refs.append("style css=%s" % fragment)


with open(sys.argv[1], encoding="utf-8-sig", errors="replace") as handle:
    html = handle.read()
scanner = Scanner()
scanner.feed(html)
scanner.close()
print("rung-missing" if scanner.rung is None else "rung=" + scanner.rung)
print("preset=yes" if scanner.preset else "preset=no")
for ref in scanner.refs:
    print(" ".join(ref.split()))
PY
}

# Check 2 for one viewport: dump the DOM at W,H and read <html data-verify>.
render_check() {
    local width=$1 height=$2 n=$3
    local label="render ${width}x${height}:" dump="$work/dump-$n.html" polls=0 tag value
    if [ "$preset" = "preset=yes" ]; then
        echo "$label FAIL data-verify preset in source"
        return 1
    fi
    if [ ! -x "$CHROME" ]; then
        echo "$label FAIL Chrome not found"
        echo "  $CHROME"
        return 1
    fi
    : >"$dump"
    set -m   # job control: the background job gets its own process group
    "$CHROME" --headless=new --disable-gpu --dump-dom --hide-scrollbars \
        --window-size="$width,$height" --user-data-dir="$work/profile-$n" \
        "$url" >"$dump" 2>/dev/null &
    chrome_pid=$!
    set +m
    # The dump is complete when its last line closes the document.
    until tail -n 1 "$dump" | grep -q '</html>[[:space:]]*$'; do
        if [ "$polls" -ge "$max_polls" ]; then
            stop_chrome || echo "verify.sh: Chrome processes survived the kill: $work" >&2
            echo "$label FAIL timeout"
            return 1
        fi
        sleep 0.2
        polls=$((polls + 1))
    done
    stop_chrome || echo "verify.sh: Chrome processes survived the kill: $work" >&2
    # Only the document's own <html> start tag counts. The dump serializes attribute
    # values in double quotes (a ">" inside one as "&gt;"); order does not matter.
    tag=$(grep -Eo '<html[^>]*>' "$dump" | head -n 1)
    if printf '%s\n' "$tag" | grep -Eq '<html[^>]*[[:space:]]data-verify="OK"'; then
        echo "$label ok"
        return 0
    fi
    case "$tag" in
        *[[:space:]]data-verify=\"*)
            value=$(printf '%s\n' "$tag" | sed -E 's/.*[[:space:]]data-verify="([^"]*)".*/\1/')
            echo "$label FAIL data-verify=\"$value\""
            ;;
        *)
            echo "$label FAIL no data-verify attribute"
            ;;
    esac
    return 1
}

trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 141' PIPE
trap 'exit 143' TERM

# --- arguments ---------------------------------------------------------------

[ "$#" -eq 1 ] || usage "expected 1 argument, got $#"
input=$1
timeout=${VERIFY_TIMEOUT:-60}
[ -f "$input" ] && [ -r "$input" ] || usage "not a readable file: $input"
is_count "$timeout" || usage "VERIFY_TIMEOUT must be a positive integer: $timeout"
input_abs="$(cd "$(dirname "$input")" && pwd -P)/$(basename "$input")"
url=$(file_url "$input_abs")
max_polls=$((timeout * 5))   # one poll every 0.2 s

scanned=$(scan "$input_abs") || usage "cannot parse $input_abs"
rung_line=$(printf '%s\n' "$scanned" | sed -n 1p)
preset=$(printf '%s\n' "$scanned" | sed -n 2p)
refs=$(printf '%s\n' "$scanned" | sed '1,2d')
case "$rung_line" in
    rung=sheet) viewports="1920x1080" ;;
    rung=page) viewports="1440x900 500x844" ;;
    rung=video) viewports="" ;;   # a transcript: no viewport render, check 2 is skipped
    rung-missing) usage "no <meta name=\"explain-rung\"> in $input_abs" ;;
    *) usage "unknown rung \"${rung_line#rung=}\" in <meta name=\"explain-rung\"> (expected sheet, page or video)" ;;
esac

# --- check 1: self-containment -------------------------------------------------

if [ -z "$refs" ]; then
    echo "self-contained: ok"
else
    echo "self-contained: FAIL $(printf '%s\n' "$refs" | wc -l | tr -d ' ') remote reference(s)"
    printf '%s\n' "$refs" | indent
    failed=1
fi

# --- check 2: render status, one DOM dump per viewport ------------------------

if [ -n "$viewports" ]; then
    tmp_base=${TMPDIR:-/tmp}
    work=$(mktemp -d "${tmp_base%/}/verify.XXXXXX") || {
        echo "verify.sh: cannot create a temp directory" >&2
        exit 1
    }
    n=0
    for viewport in $viewports; do
        n=$((n + 1))
        render_check "${viewport%x*}" "${viewport#*x}" "$n" || failed=1
    done
    stop_chrome || echo "verify.sh: Chrome processes survived the kill: $work" >&2
    rm -rf "$work"
    work=""
fi

# --- check 3: citations ----------------------------------------------------------

cite_out=$(python3 "$CITE_CHECK" "$input_abs" 2>&1)
cite_status=$?
case "$cite_status" in
    0) echo "citations: ok" ;;
    1)
        cite_failures=$(printf '%s\n' "$cite_out" | grep -v '^cite_check: [0-9]* failures$')
        echo "citations: FAIL $(printf '%s\n' "$cite_failures" | wc -l | tr -d ' ') failure(s)"
        printf '%s\n' "$cite_failures" | indent
        failed=1
        ;;
    *)
        echo "citations: FAIL cite_check exit $cite_status"
        [ -n "$cite_out" ] && printf '%s\n' "$cite_out" | indent
        failed=1
        ;;
esac

# --- check 4: prose ------------------------------------------------------------

lint_out=$(python3 "$STE_LINT" --html "$input_abs" 2>&1)
lint_status=$?
case "$lint_status" in
    0) echo "prose: ok" ;;
    1)
        lint_errors=$(printf '%s\n' "$lint_out" | grep -E '^[0-9]+:[0-9]+  E ')
        # The count comes from the lint's own "N errors, M warnings" summary line.
        lint_count=$(printf '%s\n' "$lint_out" |
            sed -nE 's/^([0-9]+) errors?, [0-9]+ warnings?$/\1/p' | tail -n 1)
        echo "prose: FAIL ${lint_count:-?} error(s)"
        [ -n "$lint_errors" ] && printf '%s\n' "$lint_errors" | indent
        failed=1
        ;;
    2)
        echo "prose: FAIL lint usage error (exit 2)"
        [ -n "$lint_out" ] && printf '%s\n' "$lint_out" | indent
        failed=1
        ;;
    *)
        echo "prose: FAIL lint exit $lint_status"
        [ -n "$lint_out" ] && printf '%s\n' "$lint_out" | indent
        failed=1
        ;;
esac

exit "$failed"
