"""Tests for the ste_lint text model (spec section 4.3.1, Issue 9 Section 8)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ste_lint  # noqa: E402
from ste_lint import Sentence  # noqa: E402


def blocks(text):
    return [(b.kind, [s.text for s in b.sentences]) for b in ste_lint.tokenize(text)]


def sentences(text):
    return [s for b in ste_lint.tokenize(text) for s in b.sentences]


def texts(text):
    return [s.text for s in sentences(text)]


class SentenceBoundaryTest(unittest.TestCase):
    def test_terminator_followed_by_whitespace_or_end_ends_sentence(self):
        self.assertEqual(
            texts("Stop the pump. Is it hot? Yes! Open the valve."),
            ["Stop the pump.", "Is it hot?", "Yes!", "Open the valve."],
        )
        self.assertEqual(texts("Read file.txt now. Done"), ["Read file.txt now.", "Done"])

    def test_closer_between_terminator_and_whitespace_still_ends_sentence(self):
        cases = {
            "**Note.** Next step.": ["**Note.**", "Next step."],
            "_Note._ Next step.": ["_Note._", "Next step."],
            'Set it to "OFF." Then wait.': ['Set it to "OFF."', "Then wait."],
            "Set it to “OFF.” Then wait.": ["Set it to “OFF.”", "Then wait."],
            "(Stop the pump.) Then wait.": ["(Stop the pump.)", "Stop the pump.", "Then wait."],
            '(Set it to "Off.") Then go.': ['(Set it to "Off.")', 'Set it to "Off."', "Then go."],
            "(**Stop.**) Then go.": ["(**Stop.**)", "**Stop.**", "Then go."],
            '"(Stop.)" Then go.': ['"(Stop.)"', "Then go."],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(texts(text), expected)

    def test_allowlisted_abbreviations_do_not_end_sentence(self):
        for abbr in ("e.g.", "i.e.", "etc.", "vs.", "Mr.", "Dr.", "No."):
            with self.subTest(abbr=abbr):
                self.assertEqual(
                    texts(f"Use {abbr} this tool. Then stop."),
                    [f"Use {abbr} this tool.", "Then stop."],
                )
        for abbr in ("E.g.", "I.e.", "Etc."):
            with self.subTest(abbr=abbr):
                self.assertEqual(
                    texts(f"{abbr} use this tool. Then stop."),
                    [f"{abbr} use this tool.", "Then stop."],
                )

    def test_abbreviation_allowlist_is_exact_and_case_sensitive(self):
        self.assertEqual(
            ste_lint.ABBREVIATIONS, ("e.g.", "i.e.", "etc.", "vs.", "Mr.", "Dr.", "No.")
        )
        for word in ("no.", "VS.", "approx."):
            with self.subTest(word=word):
                self.assertEqual(
                    texts(f"Say {word} Then stop."), [f"Say {word}", "Then stop."]
                )

    def test_decimal_numbers_and_versions_do_not_end_sentence(self):
        self.assertEqual(
            texts("Apply 2.5 times the load to version 1.2.3 now. Then stop."),
            ["Apply 2.5 times the load to version 1.2.3 now.", "Then stop."],
        )
        self.assertEqual(texts("Install version 1.2.3."), ["Install version 1.2.3."])

    def test_list_item_end_is_boundary_with_or_without_period(self):
        self.assertEqual(
            blocks("- Open the valve\n- Close the door.\n1. Start the pump"),
            [
                ("ul-item", ["Open the valve"]),
                ("ul-item", ["Close the door."]),
                ("ol-item", ["Start the pump"]),
            ],
        )

    def test_list_item_holds_several_sentences(self):
        self.assertEqual(
            blocks("1. Open the valve. Wait. Close it"),
            [("ol-item", ["Open the valve.", "Wait.", "Close it"])],
        )


class BlockTest(unittest.TestCase):
    def test_blank_line_ends_para_block(self):
        self.assertEqual(
            blocks("First para\n\nSecond para."),
            [("para", ["First para"]), ("para", ["Second para."])],
        )

    def test_soft_line_break_joins_lines_into_one_block(self):
        text = "Open the\nvalve now.\nThen stop."
        self.assertEqual(blocks(text), [("para", ["Open the valve now.", "Then stop."])])
        self.assertEqual(
            [(s.line, s.col, s.words) for s in sentences(text)], [(1, 1, 4), (3, 1, 2)]
        )

    def test_ordered_markers_make_ol_items(self):
        self.assertEqual(
            blocks("1. Open.\n2) Close.\n10. Stop."),
            [("ol-item", ["Open."]), ("ol-item", ["Close."]), ("ol-item", ["Stop."])],
        )

    def test_bullet_markers_make_ul_items(self):
        self.assertEqual(
            blocks("- Open.\n* Close.\n+ Stop."),
            [("ul-item", ["Open."]), ("ul-item", ["Close."]), ("ul-item", ["Stop."])],
        )

    def test_nested_items_are_their_own_blocks(self):
        text = "- Parent item.\n  - Child item.\n- Next item."
        self.assertEqual(
            blocks(text),
            [
                ("ul-item", ["Parent item."]),
                ("ul-item", ["Child item."]),
                ("ul-item", ["Next item."]),
            ],
        )
        child = ste_lint.tokenize(text)[1].sentences[0]
        self.assertEqual((child.line, child.col), (2, 5))

    def test_indented_continuation_line_belongs_to_item(self):
        self.assertEqual(
            blocks("1. Open the valve\n   slowly. Wait.\n2. Stop."),
            [("ol-item", ["Open the valve slowly.", "Wait."]), ("ol-item", ["Stop."])],
        )
        self.assertEqual(
            blocks("- Item text.\n\n  More item text.\n\nAfter the list."),
            [("ul-item", ["Item text.", "More item text."]), ("para", ["After the list."])],
        )

    def test_blockquote_lines_are_classified_without_their_markers(self):
        result = ste_lint.tokenize("> - Open the valve\n> - Close the door\n> - Stop the pump")
        self.assertEqual(
            [(b.kind, [(s.text, s.line, s.col) for s in b.sentences]) for b in result],
            [
                ("ul-item", [("Open the valve", 1, 5)]),
                ("ul-item", [("Close the door", 2, 5)]),
                ("ul-item", [("Stop the pump", 3, 5)]),
            ],
        )
        self.assertEqual(blocks("> A.\n>\n> B."), [("para", ["A."]), ("para", ["B."])])
        self.assertEqual(
            blocks("> Intro.\n> ```\n> code. here\n> ```\n> After."),
            [("para", ["Intro."]), ("para", ["After."])],
        )
        self.assertEqual(
            blocks("```md\n> ```\n> code. here\n> ```\n```\nAfter."), [("para", ["After."])]
        )

    def test_numbered_line_inside_paragraph_is_not_a_list_item(self):
        self.assertEqual(
            blocks("It was released in\n2024. It added a pump."),
            [("para", ["It was released in 2024.", "It added a pump."])],
        )
        self.assertEqual(
            blocks("Steps:\n1. Open."), [("para", ["Steps:"]), ("ol-item", ["Open."])]
        )

    def test_blocks_without_words_are_dropped(self):
        self.assertEqual(
            blocks("Open.\n\n---\n\n* * *\n\nClose."),
            [("para", ["Open."]), ("para", ["Close."])],
        )


class SkippedTest(unittest.TestCase):
    def test_frontmatter_skipped_and_following_line_numbers_kept(self):
        result = sentences("---\ntitle: A. B.\n---\nOpen the valve.")
        self.assertEqual([(s.text, s.line, s.col) for s in result], [("Open the valve.", 4, 1)])

    def test_byte_order_mark_does_not_hide_frontmatter(self):
        result = sentences("﻿---\ntitle: A. B.\n---\nOpen the valve.")
        self.assertEqual([(s.text, s.line, s.col) for s in result], [("Open the valve.", 4, 1)])
        self.assertEqual([(s.text, s.col) for s in sentences("﻿Open.")], [("Open.", 1)])

    def test_fenced_code_blocks_skipped(self):
        cases = (
            "Before.\n```python\nx = 1. y = 2.\n```\nAfter.",
            "Before.\n~~~ {.sh}\nrm a. b\n~~~\nAfter.",
            "Before.\n````md\n```\nInside. Text.\n````\nAfter.",
        )
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(blocks(text), [("para", ["Before."]), ("para", ["After."])])
                self.assertEqual(sentences(text)[-1].line, text.count("\n") + 1)

    def test_heading_lines_skipped(self):
        text = "# Title\n## Sub. Title\n###### Deep\nOpen the valve.\n\n#hashtag is text."
        self.assertEqual(
            blocks(text), [("para", ["Open the valve."]), ("para", ["#hashtag is text."])]
        )
        self.assertEqual(sentences(text)[0].line, 4)

    def test_table_rows_skipped(self):
        text = "| Step | Action. |\n|---|---|\n| 1. | Open. |\nAfter the table."
        self.assertEqual([(s.text, s.line) for s in sentences(text)], [("After the table.", 4)])

    def test_urls_count_no_words_and_are_never_a_boundary(self):
        result = sentences("See https://x.y/z.html. Then stop.")
        self.assertEqual(
            [(s.text, s.words, s.checkable) for s in result],
            [("See https://x.y/z.html.", 1, "See ."), ("Then stop.", 2, "Then stop.")],
        )
        for url in ("http://a.b/c?d=1.2", "file:///tmp/a.b.txt", "www.example.com/a.b"):
            with self.subTest(url=url):
                self.assertEqual(
                    [(s.words, s.checkable) for s in sentences(f"Open {url} now.")],
                    [(2, "Open  now.")],
                )
        self.assertEqual(ste_lint.tokenize("https://x.y/a.b"), [])


class OneWordTokenTest(unittest.TestCase):
    def test_code_span_is_one_word_kept_in_text_and_masked(self):
        text = "Run `make build. now` and `` a ` b `` here."
        self.assertEqual(
            [(s.text, s.words, s.checkable) for s in sentences(text)],
            [(text, 5, "Run § and § here.")],
        )

    def test_parenthetical_is_one_word_and_its_own_sentence(self):
        self.assertEqual(
            sentences("Turn the knob (clockwise, two turns) slowly."),
            [
                Sentence(
                    "Turn the knob (clockwise, two turns) slowly.",
                    1, 1, 5, "Turn the knob § slowly.",
                ),
                Sentence("clockwise, two turns", 1, 16, 3, "clockwise, two turns", depth=1),
            ],
        )

    def test_parenthetical_sentences_carry_their_depth(self):
        result = sentences("Open it (fast). Close it (slow). Stop.")
        self.assertEqual(
            [(s.text, s.depth) for s in result],
            [
                ("Open it (fast).", 0), ("fast", 1),
                ("Close it (slow).", 0), ("slow", 1),
                ("Stop.", 0),
            ],
        )
        nested = sentences("Check the valve (the one (V2) on the left) first.")
        self.assertEqual([s.depth for s in nested], [0, 1, 2])

    def test_nested_parentheses_use_the_outermost_pair(self):
        text = "Check the valve (the one (V2) on the left) first."
        self.assertEqual(
            [(s.text, s.words, s.checkable) for s in sentences(text)],
            [
                (text, 5, "Check the valve § first."),
                ("the one (V2) on the left", 6, "the one § on the left"),
                ("V2", 1, "V2"),
            ],
        )

    def test_quoted_text_is_one_word_kept_verbatim_and_masked(self):
        text = 'Push the "Emergency Stop (red)" button and the “Reset Now” key.'
        self.assertEqual(
            [(s.text, s.words, s.checkable) for s in sentences(text)],
            [(text, 8, "Push the § button and the § key.")],
        )

    def test_quote_opens_only_at_start_of_token(self):
        self.assertEqual(
            [(s.text, s.checkable) for s in sentences('Cut the 2" pipe. Then say "go".')],
            [('Cut the 2" pipe.', 'Cut the 2" pipe.'), ('Then say "go".', "Then say §.")],
        )

    def test_number_followed_by_unit_is_one_word(self):
        cases = {
            "Apply 10 mA for 3 s at 25 % and 1.5 kg.": (8, "Apply § for § at § and §."),
            "Feed 10 cats.": (3, "Feed 10 cats."),
            "Cut 10 inches.": (3, "Cut 10 inches."),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                (only,) = sentences(text)
                self.assertEqual((only.words, only.checkable), expected)

    def test_unit_list_is_exact_and_every_unit_joins_its_number(self):
        self.assertEqual(
            ste_lint.UNITS,
            (
                "%", "°C", "°F", "K", "mm", "cm", "m", "km", "in", "ft", "mg", "g", "kg",
                "lb", "ml", "l", "L", "ms", "s", "min", "h", "Hz", "kHz", "MHz", "GHz",
                "mA", "A", "mV", "V", "kV", "W", "kW", "MW", "Pa", "kPa", "MPa", "bar",
                "psi", "N", "kN", "Nm", "rpm", "dB", "B", "KB", "MB", "GB", "TB", "KiB",
                "MiB", "GiB", "px", "pt", "fps",
            ),
        )
        for unit in ste_lint.UNITS:
            with self.subTest(unit=unit):
                (only,) = sentences(f"Set 5 {unit} now.")
                self.assertEqual((only.words, only.checkable), (3, "Set § now."))

    def test_hyphenated_words_abbreviations_and_identifiers_are_single_words(self):
        (only,) = sentences("Use the A320 high-pressure pump, e.g. v4.0.1 here.")
        self.assertEqual((only.words, only.checkable), (8, only.text))

    def test_markdown_link_destination_is_not_a_parenthetical(self):
        text = "Read [the guide](https://x.y/a.html) and [notes](./notes.md) first."
        self.assertEqual(
            [(s.text, s.words, s.checkable) for s in sentences(text)],
            [(text, 6, "Read [the guide]§ and [notes]§ first.")],
        )


class CountingTest(unittest.TestCase):
    def test_punctuation_only_tokens_and_emphasis_markers_are_not_counted(self):
        (only,) = sentences("Open the **main** valve — slowly - then … _stop_.")
        self.assertEqual(only.words, 7)
        (only,) = sentences("Open ** the _ valve.")
        self.assertEqual(only.words, 3)

    def test_line_and_col_point_at_first_character_in_original_input(self):
        text = (
            "---\ntitle: x\n---\n  Intro text.\n\n```sh\necho hi\n```\n"
            "1. First step. Second\n   step here.\n   - Nested (inner\n     words) item."
        )
        self.assertEqual(
            [(s.text, s.line, s.col) for s in sentences(text)],
            [
                ("Intro text.", 4, 3),
                ("First step.", 9, 4),
                ("Second step here.", 9, 16),
                ("Nested (inner words) item.", 11, 6),
                ("inner words", 11, 14),
            ],
        )
        paren = sentences("Turn the knob (\nclockwise) slowly.")[1]
        self.assertEqual((paren.text, paren.line, paren.col), ("clockwise", 2, 1))
        self.assertEqual(
            [(s.text, s.line, s.col) for s in sentences("Open.\r\nClose.")],
            [("Open.", 1, 1), ("Close.", 2, 1)],
        )


if __name__ == "__main__":
    unittest.main()
