#!/usr/bin/env python3
"""Check a film scene directory by its text alone (the scene stage of render.sh, spec 4.3 and 7.2).

Usage: check_scene.py <scene-dir>

  exit 0, no output          the directory is a scene
  exit 1, stdout             one line "FAIL <cause>" for each cause (all of them, not only the first)
  exit 2, stderr             "usage: check_scene.py <scene-dir>"

Causes, in this order:
  FAIL no scene directory: <path>           the argument as given; the only cause, nothing else is read
  FAIL no Film.tsx
  FAIL <name> is a directory                each visible entry by name that is not a *.ts or *.tsx file
  FAIL <name> is not a .ts or .tsx file       (links are followed)
  FAIL Film.tsx has no "export function Film("
  FAIL <file>:<line>: import from "<source>"   the files by name, each by line; on one line the import
  FAIL <file>:<line>: "<name>" from remotion   causes come first, then the tokens in the order below
  FAIL <file>:<line>: token "<token>"

Entries whose name starts with "." are ignored, and so is script.gen.ts (the pipeline writes it). A file is
read as UTF-8 with each undecodable byte replaced, so no byte stops the check.

Imports: each `from "<source>"` and each `import "<source>"`, with either quote, names react, remotion,
../kit, ./script.gen, or ./<Name> for a scene file <Name>.ts or <Name>.tsx; the cause is on the line that
holds the quoted source. A source runs to the next quote, over line breaks too: after a string that ends
with the word `import` or `from`, the text up to the next quote is a source. From remotion a file may bring
in useCurrentFrame, interpolate, Easing, spring and interpolateColors, by import or by re-export. The clause
of a `from "remotion"` is the text between the nearest `import` or `export` that is the first word of a line
(on the line of the `from` or above) and the `from`.
A clause that is one braced list, with no brace inside it, no comment mark (`/*`, `*/` or `//`), and each
item of the shape `[type ]name[ as alias]` (name and alias identifiers; an empty last item, after a
trailing comma or in `{}`, aside), gives each item's own name; a clause of any other shape (a default
import, `* as R`, `export *`, a list that holds a comment mark or an item of another shape such as a quoted
alias, or the tail of a line that holds two imports) is one cause that quotes it. A comment or a quoted
alias inside the clause is refused, not read around: a block comment, or a string that a backslash carries
over a line break, can hold a line that starts with `import {` or `export {`, which would move the start of
the clause past a refused name. The author moves the comment out of the clause; a comment above the
`import` word, outside the clause, passes.
A cause quotes a source or a clause on one line: its white space (line breaks among it) collapsed to single
spaces, cut to 40 characters, stripped.

Tokens, one cause for each line that holds one, each matched with its case except @ts-nocheck, which is
matched in any case (TypeScript reads that pragma in any case) and named as written here in its cause:
  plain:   require(  import(  fetch(  foreignObject  dangerouslySetInnerHTML  clipPath  href  http://
           https://  @ts-nocheck  @ts-ignore  @ts-expect-error  as unknown  <any>
  by word: <mask  <use  <image  as any  : any
           (matched only when the next character is not an ASCII letter or digit; the end of the line
           counts as one)

There is no comment parser: an import, a quoted source or a token inside a comment counts. Stdlib only.
"""

import os
import re
import sys
from bisect import bisect_right
from pathlib import Path

USAGE = "usage: check_scene.py <scene-dir>"

GENERATED = "script.gen.ts"
FILM = "Film.tsx"
FILM_FUNCTION = "export function Film("
SOURCES = ("react", "remotion", "../kit", "./script.gen")
REMOTION_NAMES = ("useCurrentFrame", "interpolate", "Easing", "spring", "interpolateColors")
PLAIN_TOKENS = (
    "require(", "import(", "fetch(", "foreignObject", "dangerouslySetInnerHTML", "clipPath", "href",
    "http://", "https://", "@ts-nocheck", "@ts-ignore", "@ts-expect-error", "as unknown", "<any>",
)
WORD_TOKENS = ("<mask", "<use", "<image", "as any", ": any")
# TypeScript reads the pragma @ts-nocheck in any case (it lowercases the name), so this one token is matched
# in any case; TypeScript reads @ts-ignore and @ts-expect-error only as written, so they keep their case.
ANY_CASE = ("@ts-nocheck",)
TOKENS = [(t, re.compile(re.escape(t), re.IGNORECASE if t in ANY_CASE else 0)) for t in PLAIN_TOKENS] + [
    (t, re.compile(re.escape(t) + r"(?![A-Za-z0-9])")) for t in WORD_TOKENS
]

SOURCE = re.compile(r"""\b(from|import)\s*["']([^"']*)["']""")
FIRST_WORD = re.compile(r"[^\S\n]*(import|export)\b")   # at the start of a line: `import` or `export` first
BRACED = re.compile(r"(?:type\s*)?\{([^{}]*)\}")   # one list: a brace inside makes any other shape
# A comment mark in a clause makes it another shape, so it is quoted and refused, never read around: a block
# comment may hold a line that starts with `import {` or `export {`, which moves the start of the clause past
# a refused name; that comment opens after the name and closes before the real `}`, so its `*/` is always in
# the clause. A `//` in the clause is refused the same way: there is no comment parser, one rule for both.
COMMENT_MARK = re.compile(r"/\*|\*/|//")
# One item of a list, `[type ]<name>[ as <alias>]` with free white space between the words; group 1 is the
# name. An item of any other shape (a quoted alias above all, which a line continuation can carry onto a line
# that starts with `export {`) makes the clause another shape: deny by default, as for a comment mark.
IDENTIFIER = r"[A-Za-z_$][A-Za-z0-9_$]*"
ITEM = re.compile(r"\s*(?:type\s+)?(%s)(?:\s+as\s+%s)?\s*" % (IDENTIFIER, IDENTIFIER))
QUOTED_LENGTH = 40


def is_scene_file(path):
    """A regular file (a link is followed) named *.ts or *.tsx."""
    return path.is_file() and path.name.endswith((".ts", ".tsx"))


def directory_causes(entries, texts):
    """The causes of the rules of spec 4.3: `entries` are the visible entries (Paths) by name, `texts` the
    text of each scene file by name."""
    causes = [] if FILM in texts else ["no Film.tsx"]
    for entry in entries:
        if entry.name not in texts:
            causes.append("%s is a directory" % entry.name if entry.is_dir()
                          else "%s is not a .ts or .tsx file" % entry.name)
    if FILM in texts and FILM_FUNCTION not in texts[FILM]:
        causes.append('Film.tsx has no "%s"' % FILM_FUNCTION)
    return causes


def clause_before(text, starts, at):
    """The clause of the `from` at offset `at`: the text after the nearest `import` or `export` that is the
    first word of a line, on the line of the `from` or above it; with none, the text of the line of the
    `from` before it. `starts` are the offsets of the lines."""
    own = bisect_right(starts, at) - 1
    for index in range(own, -1, -1):
        found = FIRST_WORD.match(text, starts[index])
        if found:
            return text[found.end(1):at]
    return text[starts[own]:at]


def quoted(text):
    """`text` (a source or a clause) as a cause quotes it, on one line: its white space (line breaks among
    it) collapsed to single spaces, cut to QUOTED_LENGTH characters, stripped."""
    return " ".join(text.split())[:QUOTED_LENGTH].strip()


def list_names(clause):
    """The own name of each item of `clause` when it is one braced list with no comment mark (`/*`, `*/` or
    `//`) whose every item is `[type ]name[ as alias]`, an empty last item (after a trailing comma, or the
    whole of `{}`) aside; for a clause of any other shape, None."""
    braced = None if COMMENT_MARK.search(clause) else BRACED.fullmatch(clause.strip())
    if braced is None:
        return None
    items = braced.group(1).split(",")
    if not items[-1].strip():
        items = items[:-1]
    found = [ITEM.fullmatch(item) for item in items]
    return [item.group(1) for item in found] if all(found) else None


def refused_names(clause):
    """The names that `clause` brings in from remotion and that a scene may not: each name of its list that
    is not allowed, or, for a clause of any other shape, the clause, quoted."""
    names = list_names(clause)
    if names is None:
        return [quoted(clause)]
    return [name for name in names if name not in REMOTION_NAMES]


def import_causes(text, starts, allowed):
    """The import causes of `text`, as {line: [cause, ...]} with the lines from 1."""
    found = {}
    for match in SOURCE.finditer(text):
        keyword, source = match.groups()
        if source in allowed:
            causes = []
            if source == "remotion" and keyword == "from":
                clause = clause_before(text, starts, match.start())
                causes = ['"%s" from remotion' % name for name in refused_names(clause)]
        else:
            causes = ['import from "%s"' % quoted(source)]
        if causes:
            line = bisect_right(starts, match.start(2))
            found.setdefault(line, []).extend(causes)
    return found


def file_causes(name, text, allowed):
    """The causes of one scene file, by line: the imports of a line, then its tokens."""
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    imports = import_causes(text, starts, allowed)
    causes = []
    for number, line in enumerate(text.split("\n"), start=1):
        causes += ["%s:%d: %s" % (name, number, cause) for cause in imports.get(number, [])]
        causes += ['%s:%d: token "%s"' % (name, number, token)
                   for token, found in TOKENS if found.search(line)]
    return causes


def scene_causes(directory):
    """Every cause of the scene directory `directory` (a Path), in the order of the module docstring."""
    entries = sorted(
        (e for e in directory.iterdir() if not e.name.startswith(".") and e.name != GENERATED),
        key=lambda e: e.name,
    )
    texts = {e.name: e.read_bytes().decode("utf-8", errors="replace") for e in entries if is_scene_file(e)}
    allowed = SOURCES + tuple("./" + os.path.splitext(name)[0] for name in texts)
    causes = directory_causes(entries, texts)
    for name in sorted(texts):
        causes += file_causes(name, texts[name], allowed)
    return causes


def main(argv):
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    if not os.path.isdir(argv[1]):
        print("FAIL no scene directory: %s" % argv[1])
        return 1
    causes = scene_causes(Path(argv[1]))
    for cause in causes:
        print("FAIL %s" % cause)
    return 1 if causes else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
