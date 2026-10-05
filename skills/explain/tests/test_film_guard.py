"""Tests for the guard logic of the explain skill's film (video/src/kit/guard.ts, spec 7.3): the rules
that the text of a checked frame must keep (off the canvas, below the minimum size, over another
text), the quote of a text in a fault, and the stage line of a frame. The cases are those of spec
9.1, on made-up boxes: the module is plain TypeScript that imports nothing, so Node runs it directly
and no browser or render is involved. The measuring itself (the <text> elements of the stage, their
opacity, size and box) is FilmStage's, and the planted film proves it in test_render_film.py. These
cases are skipped only when `node` is missing. Each test names the mutation that turns it red."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_film_kit import KIT, NO_NODE_REASON, NODE, EvaluatesJs, kit_url

# A box of the stage as a JS expression, from its four edges in canvas pixels.
BOX = "box(%s, %s, %s, %s)"


def box(left, top, right, bottom):
    return BOX % (left, top, right, bottom)


def measured(text, where, **set_):
    """A measured text as a JS expression: its text (a JS string literal), its box, opacity 1 and px 20,
    unless `set_` sets the opacity or the px."""
    extra = ", ".join("%s: %s" % item for item in set_.items())
    return "measured(%s, %s%s)" % (text, where, ", { %s }" % extra if extra else "")


def faults(*texts):
    """The JS expression for the faults of `texts` on the 1280 x 720 canvas at minText 14."""
    return "faults([%s])" % ", ".join(texts)


# A box that fits in the canvas, 100 x 30 at (100, 100).
INSIDE = box(100, 100, 200, 130)


@unittest.skipIf(NODE is None, NO_NODE_REASON)
class GuardLogicCase(EvaluatesJs):
    PRELUDE = (
        'import { shortText, faultsOf, guardLine } from "%s";' % kit_url("guard.ts")
        + "const CANVAS = { width: 1280, height: 720 };"
        + "const MIN_TEXT = 14;"
        + "const box = (left, top, right, bottom) => ({ left, top, right, bottom });"
        + "const measured = (text, where, set = {}) => ({ text, opacity: 1, px: 20, box: where, ...set });"
        + "const faults = (texts) => faultsOf(texts, CANVAS, MIN_TEXT);"
    )

    def test_offcanvas_is_more_than_one_px_past_an_edge(self):
        """Red: a box 1 px past an edge is a fault (`>=` for `>` on the right or the bottom edge, `<=`
        for `<` on the left or the top one), or an edge is left out (a box 2 px past it gives nothing)."""
        past = [  # a 100 x 30 box, 2 px past the left, top, right and bottom edge in turn
            box(-2, 100, 98, 130), box(100, -2, 200, 28), box(1182, 100, 1282, 130), box(100, 692, 200, 722),
        ]
        edge = [  # the same box, 1 px past each edge in turn
            box(-1, 100, 99, 130), box(100, -1, 200, 29), box(1181, 100, 1281, 130), box(100, 691, 200, 721),
        ]
        got = self.values([faults(measured('"a"', b)) for b in past + edge])
        self.assertEqual(got, [['OFFCANVAS "a"']] * 4 + [[]] * 4)

    def test_smalltext_is_below_min_text(self):
        """Red: a text of exactly minText is a fault (`<=` for `<`), or the size is written without its
        decimal (10 for 10.0), or with two decimals (13.90)."""
        got = self.values([
            faults(measured('"a"', INSIDE, px=13.9)),
            faults(measured('"a"', INSIDE, px=14)),
            faults(measured('"a"', INSIDE, px=10)),
        ])
        self.assertEqual(got, [['SMALLTEXT 13.9 px "a"'], [], ['SMALLTEXT 10.0 px "a"']])

    def test_overlap_is_more_than_two_px_on_both_axes(self):
        """Red: one axis is enough (`||` for `&&`: 2 px on x with 10 on y, or 10 on x with 2 on y, is a
        fault), or 2 px is enough on an axis (`>=` for `>`)."""
        a = measured('"a"', INSIDE)  # 100 x 30 at (100, 100): x 100..200, y 100..130
        got = self.values([
            faults(a, measured('"b"', box(197, 127, 297, 157))),  # 3 px on x (197..200), 3 on y (127..130)
            faults(a, measured('"b"', box(198, 120, 298, 150))),  # 2 px on x, 10 on y
            faults(a, measured('"b"', box(190, 128, 290, 158))),  # 10 px on x, 2 on y
        ])
        self.assertEqual(got, [['OVERLAP "a" | "b"'], [], []])

    def test_faint_and_blank_texts_are_not_measured(self):
        """Red: there is no opacity floor (the faint text off the canvas is a fault), or the floor is
        `>` for `>=` (the text at 0.1 is not measured), or a text of white space only is measured, or
        a faint or a blank text still counts as the other text of an overlap (the partner is taken
        from all the texts, not from the measured ones)."""
        off = box(-50, 100, 50, 130)  # 50 px past the left edge
        over = box(150, 100, 250, 130)  # over the right half of INSIDE
        a = measured('"a"', INSIDE)
        got = self.values([
            faults(measured('"a"', off, opacity=0.09)),
            faults(measured('"a"', off, opacity=0.1)),
            faults(measured('"  \\n\\t "', off)),
            faults(a, measured('"b"', over, opacity=0.09)),
            faults(measured('"b"', over, opacity=0.09), a),
            faults(a, measured('" \\n"', over)),
        ])
        self.assertEqual(got, [[], ['OFFCANVAS "a"'], [], [], [], []])

    def test_faults_come_in_document_order(self):
        """Red: the faults are grouped by kind (OFFCANVAS, then SMALLTEXT, then OVERLAP, so that the
        SMALLTEXT of B comes before the OVERLAP), or an overlap is placed at its second text (after the
        SMALLTEXT of B), or the faults of a text come in another order than OFFCANVAS, SMALLTEXT,
        OVERLAP."""
        got = self.values([faults(
            measured('"A"', box(-10, 100, 90, 130), px=12),  # off the left edge, small, over C
            measured('"B"', box(500, 300, 600, 330), px=12),  # small, over nothing
            measured('"C"', box(80, 110, 180, 140)),  # plain: on the canvas, big enough
        )])
        self.assertEqual(got, [[
            'OFFCANVAS "A"', 'SMALLTEXT 12.0 px "A"', 'OVERLAP "A" | "C"', 'SMALLTEXT 12.0 px "B"',
        ]])

    def test_short_text(self):
        """Red: the white space is not collapsed and trimmed ("two\\n  words" stays), or the text is cut
        by UTF-16 units (the emoji of the third text is half cut), or it is cut at another length than
        24, or it ends with an ellipsis, or a fault does not quote its text through shortText (the
        last text is quoted with its line break)."""
        got = self.values([
            'shortText("  two\\n  words  ")',
            'shortText("abcdefghijklmnopqrstuvwxyzabcd")',
            'shortText("a".repeat(23) + "\\u{1F600}")',
            faults(measured('"  two\\n  words  "', box(-50, 100, 50, 130))),
        ])
        self.assertEqual(got, [
            "two words",
            "abcdefghijklmnopqrstuvwx",
            "a" * 23 + "\U0001F600",
            ['OFFCANVAS "two words"'],
        ])

    def test_guard_line(self):
        """Red: six faults are shown, not five, or the suffix is left out, or it counts wrongly (not the
        number of faults after the fifth), or the faults are joined by another separator than "; ", or
        a line with five faults gets a suffix (`>=` for `>`), or the frame and the scene are swapped."""
        got = self.values([
            'guardLine(47, "b", ["X"])',
            'guardLine(47, "b", ["f1", "f2", "f3", "f4", "f5"])',
            'guardLine(47, "b", ["f1", "f2", "f3", "f4", "f5", "f6"])',
        ])
        self.assertEqual(got, [
            "guard: FAIL frame 47 (scene b): X",
            "guard: FAIL frame 47 (scene b): f1; f2; f3; f4; f5",
            "guard: FAIL frame 47 (scene b): f1; f2; f3; f4; f5 (+1 more)",
        ])


class GuardIsThePipelinesCase(unittest.TestCase):
    """What the guard keeps out of a scene's reach. It reads two files, so it needs no Node."""

    def test_guard_imports_nothing_and_is_not_a_scene_name(self):
        """Red: guard.ts imports something (MIN_TEXT from the palette: Node can no longer run it alone),
        or kit/index.ts exports it (a scene could call the guard)."""
        guard = (KIT / "guard.ts").read_text()
        index = (KIT / "index.ts").read_text()
        imports = re.findall(r"^[ \t]*import\b.*$", guard, re.M)
        self.assertEqual(imports, [], "guard.ts imports: Node cannot run it alone")
        self.assertIsNone(re.search(r"\bguard\b", index, re.I), "kit/index.ts names the guard")


if __name__ == "__main__":
    unittest.main()
