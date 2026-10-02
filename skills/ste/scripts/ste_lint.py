"""STE-80 lint for text written to ASD-STE100 Issue 9 (the `ste` skill).

Spec: docs/superpowers/specs/2026-10-02-explain-skills-design.md, section 4.3
(`ste_lint.py`). `tokenize` (4.3.1 "Text model") turns Markdown or plain text
into `Block`s of `Sentence`s with Issue 9 Section 8 word counts, and
`html_to_blocks` (4.3.2) does the same for HTML; `lint` applies the 4.3.3 rules
to them; `main` is the command line.
"""

import re
import sys
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser

MASK = "§"  # stands for one one-word token in Sentence.checkable

# A "." after one of these does not end a sentence, except `etc.` before whitespace
# and a capital letter. Case-sensitive, but the first three may also start a
# sentence capitalised.
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
_FENCE = re.compile(r"[ \t]*(`{3,}(?!.*`)|~{3,})")  # no backtick after a ``` opener
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
    lines = text.removeprefix("\ufeff").split("\n")  # a byte order mark is not text
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
    """True when the boundary match is the "." of an allowlisted abbreviation. `etc.`
    followed by whitespace and a capital letter still ends its sentence."""
    if match.group().rstrip(_CLOSERS) != ".":
        return False
    start = match.start()
    while start and not s[start - 1].isspace():
        start -= 1
    word = s[start : match.start() + 1].lstrip(_OPENERS)
    if word in ("etc.", "Etc.") and s[match.end() :].lstrip()[:1].isupper():
        return False
    return word in _ABBREVIATIONS


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


# --html mode (section 4.3.2). The element sets are exact; every element that is
# not inline starts and ends a block, except inside a skipped subtree.
_HTML_SKIP = frozenset("script style svg pre code cite nav noscript template".split())
# As Markdown headings and table rows; a title counts as one word (Rule 8.6).
_HTML_NO_TEXT = frozenset("h1 h2 h3 h4 h5 h6 th td title".split())
_HTML_INLINE = frozenset(  # svg: an inline icon is skipped, not a block boundary
    "a abbr b cite code em i kbd mark q s small span strong sub sup svg time u var".split()
)
_HTML_VOID = frozenset("area base br col embed hr img input link meta source track wbr".split())
# A character reference, as html.unescape finds it (Lib/html/__init__.py).
_CHARREF = re.compile(r"&(?:#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?)")


def html_to_blocks(html: str) -> list[Block]:
    """Split an HTML document into paragraph and list-item blocks with the splitter
    and masking of `tokenize`. Skipped elements (with their subtree), headings and
    table cells yield none; inline `code` is one masked word, `q` is quoted text (one
    word, unchecked), `cite` adds nothing."""
    html = html.removeprefix("﻿")  # a byte order mark is not text
    parser = _HtmlText(html)
    parser.feed(html)
    parser.close()
    return parser.blocks


class _HtmlText(HTMLParser):
    """Collects the characters of each block with their (line, col) in the source."""

    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", source)]
        self.stack = []  # open elements: (tag, inside a skipped subtree)
        self.chars = []  # the open block: (character, (line, col)) pairs
        self.kind = "para"  # the kind of the open block
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":  # an omitted </li> never arrives: a new item ends the open one
            self._end("li", scope=("ol", "ul"))
        skipping = self._skipping()  # a skipped subtree adds nothing and ends no block
        if tag not in _HTML_INLINE and tag != "br" and not skipping:
            self._flush()
        dropped = skipping or ("data-ste", "skip") in attrs  # this element and its subtree
        if tag == "br" and not skipping:  # br is a space (a void element has no subtree)
            self._mark(" ")
        elif tag == "code" and not dropped:  # inline code is one masked word
            self._mark(MASK)
        elif tag == "q" and not dropped:  # q opens quoted text: one word, unchecked
            self._mark("“")
        if tag not in _HTML_VOID:
            skip = tag in _HTML_SKIP or tag in _HTML_NO_TEXT
            self.stack.append((tag, dropped or skip))

    def handle_endtag(self, tag):
        if tag in _HTML_VOID:
            return
        if self._end(tag) == ("q", False):  # close the quote that the <q> tag opened
            self._mark("”")
        if tag not in _HTML_INLINE and not self._skipping():
            self._flush()

    def handle_data(self, data):
        if not self._skipping():
            line, col0 = self.getpos()  # 0-based column of the first character of `data`
            start = self.line_starts[line - 1] + col0
            self._add(data, _source_positions(self.source, start, line, col0 + 1, len(data)))

    def close(self):
        super().close()
        self._flush()

    def _skipping(self):
        return bool(self.stack) and self.stack[-1][1]

    def _end(self, tag, scope=()):
        """Close the innermost open `tag` and every element opened inside it (an end
        tag also ends children whose end tag was omitted); stop at a `scope` element.
        Return the closed entry, or None."""
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                entry = self.stack[k]
                del self.stack[k:]
                return entry
            if self.stack[k][0] in scope:
                return None
        return None

    def _mark(self, char):
        """Add `char` at the position of the tag that the parser is at."""
        line, col0 = self.getpos()
        self._add(char, [(line, col0 + 1)])

    def _add(self, text, positions):
        if not self.chars:
            self.kind = self._kind()
        self.chars += zip(text, positions)

    def _kind(self):
        """'ol-item' or 'ul-item' inside an li of that list, else 'para'."""
        item = False
        for tag, _ in reversed(self.stack):
            item = item or tag == "li"
            if item and tag in ("ol", "ul"):
                return f"{tag}-item"
        return "para"

    def _flush(self):
        """End the open block; keep it when it has a sentence with words."""
        chars, self.chars = self.chars, []
        sentences = _sentences(*_collapse(chars)) if chars else []
        if sentences:
            self.blocks.append(Block(self.kind, sentences))


def _collapse(chars):
    """Join (character, position) pairs into text, each whitespace run one space,
    and the list of positions that `_sentences` takes."""
    text, pos = [], []
    for ch, at in chars:
        if ch.isspace():
            if not text or text[-1] == " ":
                continue
            ch = " "
        text.append(ch)
        pos.append(at)
    return "".join(text), pos


def _source_positions(source, i, line, col, count):
    """(line, col) of each of the first `count` characters that html.unescape makes
    of source[i:], which starts at (line, col); a character reference's characters
    all sit at its "&"."""
    pos = []
    while len(pos) < count and i < len(source):
        ref = _CHARREF.match(source, i)
        raw = ref.group() if ref else source[i]
        pos += [(line, col)] * (len(unescape(raw)) if ref else 1)
        line, col = (line + 1, 1) if raw == "\n" else (line, col + len(raw))
        i += len(raw)
    return pos[:count] + [(line, col)] * (count - len(pos))


# Rules (section 4.3.3). Only deterministic rules are errors; heuristics warn.


@dataclass(frozen=True)
class Finding:
    line: int
    col: int
    severity: str  # 'E' | 'W'
    rule: str  # e.g. 'LENGTH'
    message: str


# The substitution table of SKILL.md (a test keeps the two equal): unapproved
# form -> approved alternative. Each comment is the Issue 9 page label and the
# part of speech of the Issue 9 entry.
SUBSTITUTIONS = {
    "additional": "MORE",  # 2-1-A8 (adj)
    "allow": "LET",  # 2-1-A12 (v)
    "appropriate": "APPLICABLE",  # 2-1-A17 (adj)
    "attempt": "TRY",  # 2-1-A22 (n), (v)
    "commence": "START",  # 2-1-C12 (v)
    "due to": "BECAUSE OF",  # 2-1-D19 (prep)
    "enough": "SUFFICIENT",  # 2-1-E7 (adj)
    "ensure": "MAKE SURE",  # 2-1-E7 (v)
    "however": "BUT",  # 2-1-H6 (adv)
    "in the event of": "IF",  # 2-1-E10, under event (n)
    "indicate": "SHOW",  # 2-1-I8 (v)
    "modify": "CHANGE",  # 2-1-M8 (v)
    "obtain": "GET",  # 2-1-O1 (v)
    "perform": "DO",  # 2-1-P3 (v)
    "prior to": "BEFORE",  # 2-1-P12 (prep)
    "proper": "CORRECT",  # 2-1-P15 (adj)
    "provide": "GIVE",  # 2-1-P16 (v)
    "reduce": "DECREASE",  # 2-1-R6 (v)
    "replenish": "FILL",  # 2-1-R11 (v)
    "require": "NECESSARY",  # 2-1-R12 (v)
    "simultaneously": "AT THE SAME TIME",  # 2-1-S12 (adv)
    "terminate": "STOP",  # 2-1-T3 (v)
    "therefore": "THUS",  # 2-1-T4 (adv)
    "utilize": "USE",  # 2-1-U8 (v)
    "verify": "MAKE SURE",  # 2-1-V2 (v)
    "via": "THROUGH",  # 2-1-V2 (prep)
    "whether": "IF",  # 2-1-W4 (conj)
}


def _inflections(verb):
    """The regular -s/-es, -d/-ed and -ing forms of `verb`: a final "e" drops before
    -ed and -ing, and a final consonant + "y" becomes -ies and -ied."""
    if verb.endswith("e"):
        return verb + "s", verb + "d", verb[:-1] + "ing"
    if verb.endswith("y") and verb[-2] not in "aeiou":
        return verb[:-1] + "ies", verb[:-1] + "ied", verb + "ing"
    third = verb + ("es" if verb.endswith(("s", "sh", "ch", "x", "z")) else "s")
    return third, verb + "ed", verb + "ing"


# The rows whose Issue 9 entry is a verb, with the regular inflections that WORD also
# matches (a closed set; the input is never stemmed). The other rows match exactly.
VERB_ROWS = {
    verb: _inflections(verb)
    for verb in (
        "allow attempt commence ensure indicate modify obtain perform provide reduce "
        "replenish require terminate utilize verify"
    ).split()
}
_ROW_OF = {key: key for key in SUBSTITUTIONS}  # every form that WORD matches -> its row
_ROW_OF.update((form, verb) for verb, forms in VERB_ROWS.items() for form in forms)
_CONJUNCTIONS = ("provided", "providing")  # also "provided (that)" (conj): use IF

# Irregular past participles for PERFECT and PASSIVE; any -ed word counts too.
IRREGULAR_PARTICIPLES = tuple(
    "done made put set cut shut hit let read seen known shown given taken written broken "
    "chosen driven drawn thrown held kept left lost met paid said sent sold told thought "
    "brought bought caught taught found built spent won worn torn begun run become gone "
    "come been bent stuck hidden lit split spread blown frozen hung struck fallen grown "
    "swollen stood felt meant burst".split()
)
_PARTICIPLES = frozenset(IRREGULAR_PARTICIPLES)
# First words that end in -ing but are not gerunds. GERUND also skips a first word in
# all capitals, such as the signal word of "WARNING: ..." (Rule 7.1).
NON_GERUNDS = tuple(
    "during something nothing anything everything thing bring string spring morning "
    "evening".split()
)
_NON_GERUNDS = frozenset(NON_GERUNDS)
_BE = frozenset("am is are was were be been being".split())
_HAVE = frozenset(("has", "have", "had"))
_CONTRACTION_ENDS = ("n't", "'ll", "'re", "'ve", "'d", "'m")
_CONTRACTED_S = frozenset(
    "it's he's she's that's what's there's here's let's who's where's how's".split()
)
_LETTERS = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")  # a word with inner apostrophes
_EDGE = re.compile(r"^[\W_]+|[\W_]+$")  # non-alphanumeric characters at a token's edge
_WORD_FORMS = sorted(_ROW_OF, key=len, reverse=True)
# A table form as a whole word: not inside a longer word or a hyphenated compound
# (Issue 9 Rule 8.7); the words of a phrase may be apart by any whitespace run;
# group k matches _WORD_FORMS[k - 1].
_WORD = re.compile(
    r"(?<![^\W_])(?<![^\W_]-)(?:"
    + "|".join("(" + re.escape(form).replace(r"\ ", r"\s+") + ")" for form in _WORD_FORMS)
    + r")(?![^\W_])(?!-[^\W_])",
    re.IGNORECASE,
)


def lint(blocks: list[Block]) -> list[Finding]:
    """The section 4.3.3 findings for `blocks`, sorted by (line, col, rule)."""
    found = []
    for block in blocks:
        written = sum(s.depth == 0 for s in block.sentences)  # parentheticals excluded
        if block.kind == "para" and written > 6:
            first = block.sentences[0]
            message = f"paragraph has {written} sentences (max 6)"
            found.append(Finding(first.line, first.col, "W", "PARAGRAPH", message))
        for s in block.sentences:
            found += [Finding(s.line, s.col, *f) for f in _check(s, block.kind == "ol-item")]
    return sorted(found, key=lambda f: (f.line, f.col, f.rule))


def _check(sentence, procedure):
    """(severity, rule, message) of each finding in one sentence, read from its
    `checkable` text (one-word tokens masked) and its word count."""
    n, text = sentence.words, sentence.checkable
    if n > 25:
        yield "E", "LENGTH", f"sentence has {n} words (max 25)"
    elif procedure and n > 20:
        yield "W", "LENGTH-PROC", f"procedure step has {n} words (keep to 20, Rule 5.1)"
    for m in _LETTERS.finditer(text):
        token = m.group().replace("’", "'").lower()
        if token.endswith(_CONTRACTION_ENDS) or token in _CONTRACTED_S:
            yield "E", "CONTRACTION", f'contraction "{m.group()}"'
    for m in _WORD.finditer(text):
        form, found = _WORD_FORMS[m.lastindex - 1], " ".join(m.group().split())
        message = f'"{found}" is not approved; use {SUBSTITUTIONS[_ROW_OF[form]]}'
        if form in _CONJUNCTIONS:
            message += f' (as a conjunction "{form} that": use IF)'
        yield "E", "WORD", message
    words = _words(text)
    first = words[0].lower() if words else ""
    if first.endswith("ing") and first not in _NON_GERUNDS and not words[0].isupper():
        yield "W", "GERUND", f'possible gerund: "{words[0]}"'
    for first, second in zip(words, words[1:]):
        verb, after, pair = first.lower(), second.lower(), f'"{first} {second}"'
        participle = after.endswith("ed") or after in _PARTICIPLES
        if verb in _HAVE and participle:
            yield "W", "PERFECT", f"possible perfect tense: {pair}"
        if verb in _BE and after.endswith("ing"):
            yield "W", "PROGRESSIVE", f"possible progressive: {pair}"
        if verb in _BE and participle:
            yield "W", "PASSIVE", f"possible passive: {pair}"


def _words(checkable):
    """The counted words of a sentence (as in `_count_words`) without their edge
    punctuation; a token that holds only MASK and punctuation is MASK."""
    words = []
    for token in checkable.split():
        core = _EDGE.sub("", token)
        if core or MASK in token:
            words.append(core or MASK)
    return words


def format_findings(findings: list[Finding]) -> str:
    """What `main` prints: `LINE:COL  E|W RULE  message` per finding, then the summary."""
    errors = sum(f.severity == "E" for f in findings)
    warnings = sum(f.severity == "W" for f in findings)
    lines = [f"{f.line}:{f.col}  {f.severity} {f.rule}  {f.message}" for f in findings]
    return "\n".join(lines + [f"{errors} errors, {warnings} warnings"]) + "\n"


def main(argv: list[str]) -> int:
    """Lint FILE or stdin, as HTML with --html; return 0 (no errors), 1 (errors) or 2
    (usage)."""
    args = [arg for arg in argv if arg != "--html"]  # --html may repeat or follow FILE
    if len(args) > 1 or any(arg.startswith("-") for arg in args):
        print("usage: ste_lint.py [--html] [FILE]", file=sys.stderr)
        return 2
    try:
        if args:
            with open(args[0], encoding="utf-8-sig") as handle:
                text = handle.read()
        else:
            text = sys.stdin.read()
    except OSError as err:  # missing or unreadable; the message names the file
        print(err, file=sys.stderr)
        return 2
    except UnicodeDecodeError as err:  # not UTF-8
        print(f"{args[0] if args else '<stdin>'}: {err}", file=sys.stderr)
        return 2
    findings = lint(html_to_blocks(text) if "--html" in argv else tokenize(text))
    sys.stdout.write(format_findings(findings))
    return 1 if any(f.severity == "E" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
