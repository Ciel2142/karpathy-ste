"""STE-80 lint for text written to ASD-STE100 Issue 9 (the `ste` skill).

Spec: docs/superpowers/specs/2026-10-02-explain-skills-design.md, section 4.3
(`ste_lint.py`), subsection 4.3.1 "Text model". This module holds the text
model: `tokenize` turns Markdown or plain text into `Block`s of `Sentence`s
with Issue 9 Section 8 word counts. The rules and the command line build on it.
"""

import re
from dataclasses import dataclass

MASK = "§"  # stands for one one-word token in Sentence.checkable

# A "." after one of these does not end a sentence. Case-sensitive, but the
# first three may also start a sentence capitalised.
ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.", "Mr.", "Dr.", "No.")
_ABBREVIATIONS = frozenset(ABBREVIATIONS + ("E.g.", "I.e.", "Etc."))

# A number followed by one of these units is one word (Issue 9 Rule 8.6).
UNITS = (
    "%", "°C", "°F", "K", "mm", "cm", "m", "km", "in", "ft", "mg", "g", "kg", "lb",
    "ml", "l", "L", "ms", "s", "min", "h", "Hz", "kHz", "MHz", "GHz", "mA", "A", "mV",
    "V", "kV", "W", "kW", "MW", "Pa", "kPa", "MPa", "bar", "psi", "N", "kN", "Nm",
    "rpm", "dB", "B", "KB", "MB", "GB", "TB", "KiB", "MiB", "GiB", "px", "pt", "fps",
)


@dataclass(frozen=True)
class Sentence:
    text: str  # the sentence as written (tokens not replaced)
    line: int  # 1-based line of its first character in the input
    col: int  # 1-based column of its first character
    words: int  # count per section 4.3.1 / Issue 9 Section 8
    checkable: str  # `text` with each one-word token replaced by MASK
    depth: int = 0  # 0: a written sentence; n: emitted from inside n nested parentheses


@dataclass(frozen=True)
class Block:
    kind: str  # 'para' | 'ol-item' | 'ul-item'
    sentences: list[Sentence]


_BLOCKQUOTE = re.compile(r"^(?:[ \t]{0,3}>[ \t]?)+")
_FENCE = re.compile(r"[ \t]*(`{3,}|~{3,})")
_HEADING = re.compile(r" {0,3}#{1,6}(?:[ \t]|$)")
_ITEM = re.compile(r"([ \t]*)(?:(\d{1,9})[.)]|[-*+])([ \t]+|$)")
_URL = re.compile(r"(?<![\w@./])(?:(?:https?|file)://|www\.)[^\s<>`]+", re.IGNORECASE)
_URL_TAIL = ".,;:!?'\"*_”’]"
_NUMBER_UNIT = re.compile(
    r"(?<![^\s(\[{\"“*_])[-+−]?\d+(?:[.,]\d+)*\s+(?:"
    + "|".join(re.escape(unit) for unit in sorted(UNITS, key=len, reverse=True))
    + r")(?!\w)"
)
_BOUNDARY = re.compile(r"[.!?]+[)\"”*_]*(?=\s|$)")
_TAIL = re.compile(r"[.!?]+[)\"”*_]*$")  # a terminator and closers that end a token
_CLOSERS = ")\"”*_"
_OPENERS = "(\"“*_["
_QUOTES = {'"': '"', "“": "”"}
_QUOTE_OPEN = re.compile(r"(?<![^\s(\[{*_—–])[\"“]")  # at a token start, so 2" stays literal


def tokenize(text: str) -> list[Block]:
    """Split Markdown or plain text into paragraph and list-item blocks. Frontmatter,
    fenced code, headings and table rows yield none; line numbers count through them."""
    lines = text.split("\n")
    layout, fence = _Layout(), None  # fence: (opening run, opened inside a blockquote)
    for idx in range(_frontmatter_end(lines), len(lines)):
        raw = lines[idx].rstrip("\r")
        # Blockquote markers become spaces: columns stay exact, the content is classified.
        line = _BLOCKQUOTE.sub(lambda m: " " * len(m.group()), raw)
        if fence:
            bare = (line if fence[1] else raw).strip()
            if len(bare) >= len(fence[0]) and bare == fence[0][0] * len(bare):
                fence = None
            continue
        bare = line.strip()
        indent = _width(line[: len(line) - len(line.lstrip())])
        opener = _FENCE.match(line)
        if opener:
            fence = (opener.group(1), line != raw)
            layout.brk(indent)
        elif not bare:
            layout.brk()
        elif _HEADING.match(line) or bare.startswith("|"):
            layout.brk(indent)
        else:
            layout.add(line, idx + 1)
    result = []
    for kind, segments in layout.blocks:
        sentences = [s for segment in segments for s in _sentences(*_join(segment))]
        if sentences:
            result.append(Block(kind, sentences))
    return result


class _Layout:
    """Assigns content lines to blocks; a block holds segments of joined lines."""

    def __init__(self):
        self.blocks = []  # [kind, segments]; a segment is [(line, col0, text), ...]
        self.items = []  # open list items, outermost first: (content indent, block)
        self.segment = None  # the segment that a lazy continuation line extends
        self.kind = None  # kind of the block that owns self.segment

    def brk(self, indent=None):
        """End the open segment; a line at `indent` also closes deeper items."""
        self.segment = None
        while indent is not None and self.items and self.items[-1][0] > indent:
            self.items.pop()

    def add(self, line, line_no):
        item = _ITEM.match(line)
        if item and item.group(2) and int(item.group(2)) != 1:
            if self.segment and self.kind == "para":
                item = None  # CommonMark: only an ordered list at 1 interrupts a paragraph
        if item:
            self.brk(_width(item.group(1)))
            block = self._block("ol-item" if item.group(2) else "ul-item")
            content_indent = _width(line[: item.end()]) + (0 if item.group(3) else 1)
            self.items.append((content_indent, block))
            self._open(block, line_no, item.end(), line[item.end() :])
            return
        body = line.lstrip()
        col0 = len(line) - len(body)
        if self.segment is not None:
            self.segment.append((line_no, col0, body.rstrip()))
            return
        self.brk(_width(line[:col0]))
        block = self.items[-1][1] if self.items else self._block("para")
        self._open(block, line_no, col0, body)

    def _block(self, kind):
        block = [kind, []]
        self.blocks.append(block)
        return block

    def _open(self, block, line_no, col0, text):
        self.segment = [(line_no, col0, text.rstrip())]
        self.kind = block[0]
        block[1].append(self.segment)


def _frontmatter_end(lines):
    """Index of the first line after YAML frontmatter (0 when there is none)."""
    if lines[0].rstrip() != "---":
        return 0
    return next((i + 1 for i in range(1, len(lines)) if lines[i].rstrip() == "---"), 0)


def _width(indent):
    return len(indent.expandtabs(4))


def _join(segment):
    """Join a segment's lines with one space; map each character to (line, col)."""
    parts, pos = [], []
    for line_no, col0, text in segment:
        if parts:
            parts.append(" ")
            pos.append((line_no, col0))
        parts.append(text)
        pos.extend((line_no, col0 + k + 1) for k in range(len(text)))
    return "".join(parts), pos


def _sentences(s, pos, depth=0):
    """Split one run of text into sentences; parentheticals follow their sentence."""
    spans = _spans(s)
    view = _boundary_view(s, spans)
    ends = [m.end() for m in _BOUNDARY.finditer(view) if not _is_abbreviation(s, m)]
    result, start = [], 0
    for end in ends + [len(s)]:
        result += _sentence(s, pos, spans, start, end, depth)
        start = end
    return result


def _sentence(s, pos, spans, start, end, depth):
    """The sentence in s[start:end], if it has words, then its parentheticals."""
    start += len(s[start:end]) - len(s[start:end].lstrip())
    end = start + len(s[start:end].strip())
    inner = [span for span in spans if start <= span[0] and span[1] <= end]
    parts, k = [], start
    for a, b, kind in inner:
        parts += [s[k:a], "" if kind == "url" else MASK]  # URLs are skipped: no word
        k = b
    checkable = "".join(parts) + s[k:end]
    words = _count_words(checkable)
    if not words:
        return []
    result = [Sentence(s[start:end], *pos[start], words, checkable, depth)]
    for a, b, kind in inner:
        if kind == "paren":
            result += _sentences(s[a + 1 : b - 1], pos[a + 1 : b - 1], depth + 1)
    return result


def _count_words(checkable):
    """Whitespace tokens that hold a letter, digit or MASK once * and _ are stripped."""
    return sum(
        any(ch.isalnum() or ch == MASK for ch in token.strip("*_"))
        for token in checkable.split()
    )


def _is_abbreviation(s, match):
    """True when the boundary match is the "." of an allowlisted abbreviation."""
    if match.group().rstrip(_CLOSERS) != ".":
        return False
    start = match.start()
    while start and not s[start - 1].isspace():
        start -= 1
    return s[start : match.start() + 1].lstrip(_OPENERS) in _ABBREVIATIONS


def _boundary_view(s, spans):
    """s with token interiors blanked; a terminator run that ends a ( ) or quote stays."""
    view = list(s)
    for a, b, kind in spans:
        if kind in ("paren", "quote"):
            tail = _TAIL.search(s, a + 1, b - 1)
            a, b = a + 1, tail.start() if tail else b - 1
        view[a:b] = "x" * (b - a)
    return "".join(view)


def _spans(s):
    """One-word tokens of s as sorted (start, end, kind): 'code', 'url', 'link'
    (a Markdown link destination), 'paren', 'quote' and 'unit' (number + unit)."""
    opaque = _code_spans(s)
    for m in _URL.finditer(s):
        url = _trim_url(m.group())
        if url and not any(a <= m.start() < b for a, b, _ in opaque):
            opaque.append((m.start(), m.start() + len(url), "url"))
    jump = {a: (b, kind) for a, b, kind in opaque}
    spans, i = [], 0
    while i < len(s):
        end, kind = jump.get(i, (None, None))
        if end is None and s[i] == "(":
            end = _close(s, i, jump, "(", ")")
            kind = "link" if s[i - 1 : i] == "]" else "paren"
        elif end is None and _QUOTE_OPEN.match(s, i):
            end, kind = _close(s, i, jump, None, _QUOTES[s[i]]), "quote"
        if end is None:
            i += 1
        else:
            spans.append((i, end, kind))
            i = end
    units = [m.span() for m in _NUMBER_UNIT.finditer(s)]
    spans += [(a, b, "unit") for a, b in units if not any(x < b and a < y for x, y, _ in spans)]
    return sorted(spans)


def _code_spans(s):
    """Inline code: a backtick run closed by the next run of the same length."""
    spans, runs = [], [m.span() for m in re.finditer(r"`+", s)]
    while runs:
        a, b = runs.pop(0)
        close = next((k for k, (c, d) in enumerate(runs) if d - c == b - a), None)
        if close is not None:
            spans.append((a, runs[close][1], "code"))
            runs = runs[close + 1 :]
    return spans


def _trim_url(url):
    """Drop trailing punctuation that belongs to the sentence, not to the URL."""
    while url and (
        url[-1] in _URL_TAIL or (url[-1] == ")" and url.count(")") > url.count("("))
    ):
        url = url[:-1]
    return url if _URL.fullmatch(url) else ""


def _close(s, i, jump, opener, closer):
    """End of the token opened at s[i], skipping opaque spans; None if unclosed."""
    depth, j = 1, i + 1
    while j < len(s):
        if j in jump:
            j = jump[j][0]
            continue
        depth += (s[j] == opener) - (s[j] == closer)
        if not depth:
            return j + 1
        j += 1
    return None
