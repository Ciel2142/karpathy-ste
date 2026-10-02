"""Tests for ste_lint: the text model (spec section 4.3.1, Issue 9 Section 8), the
`--html` mode (section 4.3.2), the rules (section 4.3.3) and the command line
(section 4.3)."""

import contextlib
import dataclasses
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ste_lint  # noqa: E402
from ste_lint import Sentence  # noqa: E402

SKILL_MD = Path(__file__).resolve().parent.parent / "SKILL.md"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "artifact.html"
TABLE_ROW = re.compile(r"^\| ([a-z ]+) \| ([A-Z ]+) \| 2-1-[A-Z]\d+ \|$")
USAGE = "usage: ste_lint.py [--html] [FILE]\n"


def blocks(text):
    return [(b.kind, [s.text for s in b.sentences]) for b in ste_lint.tokenize(text)]


def sentences(text):
    return [s for b in ste_lint.tokenize(text) for s in b.sentences]


def texts(text):
    return [s.text for s in sentences(text)]


def findings(text):
    return ste_lint.lint(ste_lint.tokenize(text))


def codes(text):
    return [f.rule for f in findings(text)]


def errors(text):
    return [f.rule for f in findings(text) if f.severity == "E"]


def messages(text, rule):
    return [(f.severity, f.message) for f in findings(text) if f.rule == rule]


def sentence_of(n):
    """A sentence of exactly n words that only the length rules can see."""
    return " ".join(["Check"] + ["valve"] * (n - 1)) + "."


def run_main(argv, stdin=""):
    """main(argv) with `stdin` as standard input; returns (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(stdin)):
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ste_lint.main(argv)
    return code, out.getvalue(), err.getvalue()


def run_main_on_file(text):
    """main([FILE]) for a temporary UTF-8 file that holds `text`."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(text, encoding="utf-8")
        return run_main([str(path)])


def html_blocks(html):
    return [(b.kind, [s.text for s in b.sentences]) for b in ste_lint.html_to_blocks(html)]


def html_sentences(html):
    return [s for b in ste_lint.html_to_blocks(html) for s in b.sentences]


def html_findings(html):
    return ste_lint.lint(ste_lint.html_to_blocks(html))


def html_codes(html):
    return [f.rule for f in html_findings(html)]


def html_messages(html, rule):
    return [(f.severity, f.message) for f in html_findings(html) if f.rule == rule]


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
        for text in ("Use *e.g.* this tool. Then stop.", "Use _i.e._ this tool. Then stop."):
            with self.subTest(text=text):  # inside emphasis markers
                self.assertEqual(texts(text), [text.removesuffix(" Then stop."), "Then stop."])

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
        result = sentences("\ufeff---\ntitle: A. B.\n---\nOpen the valve.")
        self.assertEqual([(s.text, s.line, s.col) for s in result], [("Open the valve.", 4, 1)])
        self.assertEqual([(s.text, s.col) for s in sentences("\ufeffOpen.")], [("Open.", 1)])

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
            "Put the A4 in the tray.": (6, "Put the A4 in the tray."),  # A4: not a number
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

    def test_rules_see_the_words_that_the_tokenizer_counts(self):
        """`_words` (the rules) and `_count_words` (the tokenizer) agree on every sentence."""
        edge_cases = (
            "Run `make build. now` and `` a ` b `` here.",  # code spans
            'Push the "Emergency Stop (red)" button and the “Reset Now” key.',  # quotes
            "Apply 10 mA for 3 s at 25 % and 1.5 kg.",  # numbers with units
            "See https://x.y/z.html and www.example.com/a.b now.",  # URLs: no words
            "Check the valve (the one (V2) on the left) first.",  # parentheticals
            "Open the **main** valve — slowly - then … _stop_.",  # emphasis, dashes
            '"Checking" is the label (on the left).',  # a masked first word
        )
        for text in edge_cases:
            for s in sentences(text):
                with self.subTest(sentence=s.text):
                    self.assertEqual(len(ste_lint._words(s.checkable)), s.words)


class ErrorRuleTest(unittest.TestCase):
    def test_length_error_for_sentence_over_25_words(self):
        self.assertEqual(
            messages(sentence_of(26), "LENGTH"), [("E", "sentence has 26 words (max 25)")]
        )
        self.assertNotIn("LENGTH", codes(sentence_of(25)))

    def test_contraction_error_for_each_suffix_and_each_listed_s_form(self):
        tokens = (
            "don't", "we'll", "they're", "we've", "I'd", "I'm", "DON'T", "can’t",
            "it's", "he's", "she's", "that's", "what's", "there's", "here's", "let's",
            "who's", "where's", "how's", "It’s",
        )
        for token in tokens:
            with self.subTest(token=token):
                self.assertEqual(
                    messages(f"Then {token} stop.", "CONTRACTION"),
                    [("E", f'contraction "{token}"')],
                )

    def test_no_contraction_for_other_s_forms_or_masked_text(self):
        for text in (
            "Replace the pump's seal.",
            "Replace the bit's edge.",
            "Replace the pumps' seals.",
            "Push the 'Start' button.",
            "Run `don't` now.",
            'The label says "don\'t".',
        ):
            with self.subTest(text=text):
                self.assertNotIn("CONTRACTION", codes(text))

    def test_word_error_for_every_table_entry_names_the_approved_word(self):
        for word, approved in ste_lint.SUBSTITUTIONS.items():
            with self.subTest(word=word):
                self.assertEqual(
                    messages(f"Then {word} the part.", "WORD"),
                    [("E", f'"{word}" is not approved; use {approved}')],
                )

    def test_word_is_case_insensitive_and_multi_word_across_single_spaces(self):
        self.assertEqual(
            messages("Prior To use", "WORD"), [("E", '"Prior To" is not approved; use BEFORE')]
        )
        self.assertEqual(
            messages("ENSURE that the seal is tight.", "WORD"),
            [("E", '"ENSURE" is not approved; use MAKE SURE')],
        )
        self.assertEqual(
            messages("In the event\nof a leak, stop the pump.", "WORD"),
            [("E", '"In the event of" is not approved; use IF')],
        )

    def test_word_matches_the_exact_table_forms_only(self):
        for text in (
            "Provided that the part is available, install it.",
            "Providing that the part is available, install it.",
            "The pump provides pressure.",
            "The team utilized the port.",
            "The allowable load is 5 kN.",
            "Record the utilization of the pump.",
            "The performance and the indication are correct.",
            "Add the address to the allow-list.",
            "Re-verify the torque.",
            "The tank is shallow.",  # a table form at the end of a longer word
            "Discard the improper seal.",
            "The board can censure the crew.",
            "Ignore the trivia.",
            "They exterminate the pests.",
        ):
            with self.subTest(text=text):
                self.assertNotIn("WORD", codes(text))

    def test_rules_check_a_parenthetical_at_its_own_position(self):
        result = findings("Turn the knob (ensure it is tight) slowly.")
        self.assertEqual([(f.line, f.col, f.rule) for f in result], [(1, 16, "WORD")])


class WarningRuleTest(unittest.TestCase):
    def assert_warning(self, text, rule, message):
        """`rule` warns with `message`, nothing is an error, and the exit code stays 0."""
        self.assertIn(("W", message), messages(text, rule))
        self.assertEqual(errors(text), [])
        self.assertEqual(run_main_on_file(text)[0], 0)

    def test_length_proc_warning_for_ordered_item_of_21_to_25_words(self):
        for n in (21, 25):
            with self.subTest(words=n):
                self.assert_warning(
                    f"1. {sentence_of(n)}",
                    "LENGTH-PROC",
                    f"procedure step has {n} words (keep to 20, Rule 5.1)",
                )
        for text in (f"1. {sentence_of(20)}", f"- {sentence_of(24)}", sentence_of(24)):
            with self.subTest(text=text):
                self.assertNotIn("LENGTH-PROC", codes(text))
        self.assertEqual(codes(f"1. {sentence_of(26)}"), ["LENGTH"])

    def test_paragraph_warning_once_at_first_sentence_of_long_para(self):
        text = "Intro.\n\n  One. Two. Three.\nFour. Five. Six. Seven."
        self.assert_warning(text, "PARAGRAPH", "paragraph has 7 sentences (max 6)")
        found = [(f.line, f.col) for f in findings(text) if f.rule == "PARAGRAPH"]
        self.assertEqual(found, [(3, 3)])
        self.assertNotIn("PARAGRAPH", codes("One. Two. Three. Four. Five. Six."))
        for marker in ("-", "1."):
            item = f"{marker} One. Two. Three. Four. Five. Six. Seven."
            with self.subTest(item=item):
                self.assertEqual(len(sentences(item)), 7)
                self.assertNotIn("PARAGRAPH", codes(item))

    def test_paragraph_counts_written_sentences_not_parentheticals(self):
        text = "Open it (fast). Close it (slow). Wait (long). Stop it (now)."
        self.assertEqual(len(sentences(text)), 8)
        self.assertNotIn("PARAGRAPH", codes(text))

    def test_perfect_warning_for_have_and_participle(self):
        self.assert_warning(
            "The technician has adjusted the valve.",
            "PERFECT",
            'possible perfect tense: "has adjusted"',
        )
        self.assert_warning(
            "They had taken the cover off.", "PERFECT", 'possible perfect tense: "had taken"'
        )
        self.assertNotIn("PERFECT", codes("The pump has two blades."))
        for verb in ("has", "have", "had"):
            with self.subTest(verb=verb):
                self.assertIn("PERFECT", codes(f"They {verb} adjusted the valve."))

    def test_progressive_warning_for_be_and_ing_word(self):
        self.assert_warning(
            "The pump is running.", "PROGRESSIVE", 'possible progressive: "is running"'
        )
        self.assertNotIn("PROGRESSIVE", codes("The pump is in the ring."))
        for verb in ("am", "is", "are", "was", "were", "be", "been", "being"):
            with self.subTest(verb=verb):
                self.assertIn("PROGRESSIVE", codes(f"It {verb} running."))

    def test_passive_warning_for_be_and_participle(self):
        self.assert_warning("The valve is closed.", "PASSIVE", 'possible passive: "is closed"')
        self.assert_warning(
            "The cover was **taken** off.", "PASSIVE", 'possible passive: "was taken"'
        )
        self.assertNotIn("PASSIVE", codes("The valve is open."))
        for verb in ("am", "is", "are", "was", "were", "be", "been", "being"):
            with self.subTest(verb=verb):
                self.assertIn("PASSIVE", codes(f"It {verb} closed."))

    def test_gerund_warning_for_sentence_that_starts_with_ing_word(self):
        self.assert_warning(
            "Checking the valve is necessary.", "GERUND", 'possible gerund: "Checking"'
        )
        self.assert_warning("**Opening** it is easy.", "GERUND", 'possible gerund: "Opening"')
        self.assertNotIn("GERUND", codes("Check the landing gear."))

    def test_gerund_exempts_an_all_capitals_word_and_the_listed_non_gerunds(self):
        self.assertEqual(
            ste_lint.NON_GERUNDS,
            (
                "during", "something", "nothing", "anything", "everything", "thing",
                "bring", "string", "spring", "morning", "evening",
            ),
        )
        exempt = [f"{word.capitalize()} is here." for word in ste_lint.NON_GERUNDS] + [
            "WARNING: Do not touch the blade.",
            "During the approach, keep the speed constant.",
            "RING the bell.",
        ]
        for text in exempt:
            with self.subTest(text=text):
                self.assertNotIn("GERUND", codes(text))
        self.assert_warning(
            "Running the pump is necessary.", "GERUND", 'possible gerund: "Running"'
        )

    def test_irregular_participle_list_is_exact_and_used_by_perfect_and_passive(self):
        expected = tuple(
            "done made put set cut shut hit let read seen known shown given taken written "
            "broken chosen driven drawn thrown held kept left lost met paid said sent sold "
            "told thought brought bought caught taught found built spent won worn torn "
            "begun run become gone come".split()
        )
        self.assertEqual(ste_lint.IRREGULAR_PARTICIPLES, expected)
        self.assertEqual(len(set(expected)), len(expected))
        for word in expected:
            with self.subTest(word=word):
                self.assertIn("PASSIVE", codes(f"It is {word} now."))
                self.assertIn("PERFECT", codes(f"It has {word} now."))

    def test_verb_warnings_skip_masked_tokens(self):
        for text, rule in (
            ('"Checking" is the label.', "GERUND"),
            ("The flag is `closed`.", "PASSIVE"),
            ("It is (running) now.", "PROGRESSIVE"),
            ("It has `built` it.", "PERFECT"),
        ):
            with self.subTest(text=text):
                self.assertNotIn(rule, codes(text))


class MustNotErrorTest(unittest.TestCase):
    """Spec section 4.5: correct STE that must not produce an error."""

    def assert_no_error(self, text):
        self.assertEqual([f for f in findings(text) if f.severity == "E"], [])

    def test_pump_has_fixed_blades(self):
        self.assert_no_error("The pump has fixed blades.")
        self.assertIn("PERFECT", codes("The pump has fixed blades."))

    def test_landing_gear_vibration(self):
        text = "The cause of the noise is landing gear vibration."
        self.assert_no_error(text)
        self.assertIn("PROGRESSIVE", codes(text))

    def test_valve_is_closed(self):
        self.assert_no_error("The valve is closed.")
        self.assertIn("PASSIVE", codes("The valve is closed."))

    def test_seven_item_numbered_procedure(self):
        text = (
            "1. Remove the four bolts from the access panel.\n"
            "2. Remove the access panel.\n"
            "3. Disconnect the electrical connector from the pump.\n"
            "4. Remove the pump from the bracket.\n"
            "5. Install the new pump on the bracket.\n"
            "6. Connect the electrical connector to the pump.\n"
            "7. Install the access panel with the four bolts.\n"
        )
        self.assertEqual(len(sentences(text)), 7)
        self.assertTrue(all(s.words <= 20 for s in sentences(text)))
        self.assert_no_error(text)
        self.assertNotIn("PARAGRAPH", codes(text))

    def test_eight_item_bulleted_list_without_final_periods(self):
        items = (
            "main pump", "fuel filter", "return valve", "pressure switch",
            "drain line", "access panel", "electrical connector", "four bolts",
        )
        text = "".join(f"- Check the {item}\n" for item in items)
        self.assertEqual([b.kind for b in ste_lint.tokenize(text)], ["ul-item"] * 8)
        self.assert_no_error(text)
        self.assertNotIn("PARAGRAPH", codes(text))

    def test_24_word_ordered_list_item(self):
        text = (
            "1. Turn the adjustment screw on the left side of the pressure regulator "
            "clockwise until the gauge shows the correct value for the hydraulic system.\n"
        )
        self.assertEqual(sentences(text)[0].words, 24)
        self.assert_no_error(text)
        self.assertEqual(
            run_main_on_file(text),
            (
                0,
                "1:4  W LENGTH-PROC  procedure step has 24 words (keep to 20, Rule 5.1)\n"
                "0 errors, 1 warnings\n",
                "",
            ),
        )

    def test_backticked_banned_word(self):
        self.assert_no_error("Run `ensure` before you start the pump.")

    def test_quoted_banned_word(self):
        self.assert_no_error('The label says "ensure".')

    def test_parenthetical_that_pushes_naive_count_past_25(self):
        text = (
            "Turn the adjustment screw on the pressure regulator (the small brass screw "
            "next to the gauge on the left side of the main panel) until the gauge shows "
            "the correct value."
        )
        self.assertGreater(len(text.split()), 25)
        self.assertEqual([s.words for s in sentences(text)], [16, 16])
        self.assert_no_error(text)

    def test_number_and_unit_count_as_one_word(self):
        text = (
            "Set the output current of the power supply to 10 mA before you connect the "
            "two test leads to the two terminals on the rear panel."
        )
        self.assertEqual(len(text.split()), 26)
        self.assertEqual(sentences(text)[0].words, 25)
        self.assert_no_error(text)

    def test_bold_note_is_its_own_sentence(self):
        self.assertEqual(texts("**Note.** Next step."), ["**Note.**", "Next step."])
        self.assert_no_error("**Note.** Next step.")
        text = f"**Note.** {sentence_of(25)}"
        self.assertEqual([s.words for s in sentences(text)], [1, 25])
        self.assertNotIn("LENGTH", codes(text))


class SubstitutionTableTest(unittest.TestCase):
    def test_substitutions_equal_the_skill_md_table(self):
        lines = SKILL_MD.read_text(encoding="utf-8").splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith("| Unapproved |"))
        end = next((i for i in range(start, len(lines)) if not lines[i].strip()), len(lines))
        rows = [m.groups() for m in map(TABLE_ROW.match, lines[start:end]) if m]
        table = {unapproved.lower(): approved.upper() for unapproved, approved in rows}
        self.assertEqual(len(table), 27)
        self.assertEqual(ste_lint.SUBSTITUTIONS, table)


class HtmlTest(unittest.TestCase):
    """Spec section 4.3.2: `html_to_blocks`, the text model of `--html` mode."""

    def test_skip_set_elements_drop_their_whole_subtree(self):
        skip = ("script", "style", "svg", "pre", "code", "cite", "nav", "noscript", "template")
        for tag in skip:
            with self.subTest(tag=tag):
                html = (
                    f"<p>Open the valve.</p><{tag}><b>Ensure</b> it <code>x</code>.</{tag}>"
                    "<p>Close it.</p>"
                )
                masked = [("para", ["§"])] if tag == "code" else []  # code: one masked word
                self.assertEqual(
                    html_blocks(html),
                    [("para", ["Open the valve."]), *masked, ("para", ["Close it."])],
                )
                self.assertNotIn("WORD", html_codes(html))

    def test_data_ste_skip_drops_any_element_with_its_subtree(self):
        html = (
            '<div data-ste="skip"><p>Ensure the seal.</p><ul><li>Verify it</ul></div>'
            '<p>Open <span data-ste="skip">ensure</span>the valve.</p>'
            '<p data-ste="prose">Close it.</p>'
        )
        self.assertEqual(
            html_blocks(html), [("para", ["Open the valve."]), ("para", ["Close it."])]
        )
        self.assertNotIn("WORD", html_codes(html))
        void = '<p>Open it.<img data-ste="skip" src="v">Ensure it.<br data-ste="skip">Stop.</p>'
        self.assertEqual(
            html_blocks(void), [("para", ["Open it."]), ("para", ["Ensure it.", "Stop."])]
        )
        self.assertIn("WORD", html_codes(void))  # a void element has no subtree to skip

    def test_headings_and_table_cells_yield_no_blocks(self):
        for tag in ("h1", "h2", "h3", "h4", "h5", "h6", "th", "td"):
            with self.subTest(tag=tag):
                html = f"<{tag}>Ensure the <b>seal</b>.</{tag}><p>Open the valve.</p>"
                self.assertEqual(html_blocks(html), [("para", ["Open the valve."])])
                self.assertNotIn("WORD", html_codes(html))
        table = "<table><tr><th>Verify<td>Ensure it<tr><td>Obtain it</table><p>After it.</p>"
        self.assertEqual(html_blocks(table), [("para", ["After it."])])

    def test_nav_with_twelve_links_yields_no_text(self):
        words = (
            "Ensure", "Utilize", "Verify", "Obtain", "Perform", "Provide",
            "Modify", "Terminate", "Commence", "Indicate", "Replenish", "Attempt",
        )
        links = "".join(f'<a href="#s{n}">{word}</a> ' for n, word in enumerate(words, 1))
        html = f"<nav>{links}</nav><p>Open the valve.</p>"
        self.assertEqual(html_blocks(html), [("para", ["Open the valve."])])
        self.assertEqual(html_codes(html.replace("nav>", "div>")).count("WORD"), 12)

    def test_implicit_li_close_keeps_items_apart(self):
        item = " ".join(["Check"] + ["valve"] * 14)  # 15 words, no final period
        html = f"<ul><li>{item}<li>{item}</ul><p>After the list.</p>"
        self.assertEqual(
            [(b.kind, [s.words for s in b.sentences]) for b in ste_lint.html_to_blocks(html)],
            [("ul-item", [15]), ("ul-item", [15]), ("para", [3])],
        )
        self.assertNotIn("LENGTH", html_codes(html))
        self.assertEqual(
            html_blocks("<ol><li>Open it<ul><li>Note it</ul><li>Close it</ol>"),
            [("ol-item", ["Open it"]), ("ul-item", ["Note it"]), ("ol-item", ["Close it"])],
        )
        self.assertEqual(
            html_blocks('<ol><li data-ste="skip">Ensure it<li>Close the valve</ol>'),
            [("ol-item", ["Close the valve"])],
        )

    def test_ol_items_take_the_length_proc_band(self):
        html = f"<ol><li>{sentence_of(23)}</li><li>{sentence_of(12)}</li></ol>"
        self.assertEqual([b.kind for b in ste_lint.html_to_blocks(html)], ["ol-item", "ol-item"])
        self.assertEqual(
            html_messages(html, "LENGTH-PROC"),
            [("W", "procedure step has 23 words (keep to 20, Rule 5.1)")],
        )
        self.assertEqual(html_codes(f"<ol><li><p>{sentence_of(21)}</p></ol>"), ["LENGTH-PROC"])
        self.assertEqual(html_codes(f"<ol><li>{sentence_of(26)}</ol>"), ["LENGTH"])

    def test_ul_items_are_ul_item_and_other_text_is_para(self):
        html = (
            f"<ul><li>{sentence_of(23)}</ul><div>{sentence_of(23)}</div>"
            f"<li>{sentence_of(23)}</li>"
        )
        self.assertEqual(
            [b.kind for b in ste_lint.html_to_blocks(html)], ["ul-item", "para", "para"]
        )
        self.assertNotIn("LENGTH-PROC", html_codes(html))

    def test_inline_elements_do_not_split_a_sentence(self):
        self.assertEqual(
            html_blocks("<p>Open the <b>valve</b>. Close it.</p>"),
            [("para", ["Open the valve.", "Close it."])],
        )
        inline = (
            "a", "abbr", "b", "cite", "code", "em", "i", "kbd", "mark", "q", "s", "small",
            "span", "strong", "sub", "sup", "time", "u", "var",
        )
        first = {  # cite: skipped; code: masked; q: quoted
            "cite": "Open the now.", "code": "Open the § now.", "q": "Open the “valve” now."
        }
        for tag in inline:
            with self.subTest(tag=tag):
                self.assertEqual(
                    html_blocks(f"<p>Open the <{tag}>valve</{tag}> now. Close it.</p>"),
                    [("para", [first.get(tag, "Open the valve now."), "Close it."])],
                )
        self.assertEqual(
            html_blocks("<p>Push <button>Stop</button> now.</p>"),
            [("para", ["Push"]), ("para", ["Stop"]), ("para", ["now."])],
        )

    def test_inline_code_is_one_masked_word(self):
        self.assertNotIn("WORD", html_codes("<p>Run <code>ensure</code> now.</p>"))
        (only,) = html_sentences("<p>Run <code>make. ensure</code> before you start the pump.</p>")
        self.assertEqual((only.words, only.checkable), (7, "Run § before you start the pump."))

    def test_q_is_quoted_text_one_unchecked_word(self):
        html = "<p>The label says <q>ensure the seal</q> and <q>Don't touch</q>.</p>"
        self.assertEqual([f for f in html_findings(html) if f.severity == "E"], [])
        (only,) = html_sentences(html)
        self.assertEqual((only.words, only.checkable), (6, "The label says § and §."))
        quote = " ".join(["valve"] * 30)
        self.assertNotIn("LENGTH", html_codes(f"<p>The label says <q>{quote}</q>.</p>"))
        self.assertEqual(  # the quote marks sit at the tags
            [(s.text, s.line, s.col) for s in html_sentences("<p><q>Stop</q> is it.</p>")],
            [("“Stop” is it.", 1, 4)],
        )

    def test_cite_contributes_nothing(self):
        html = '<p>The pump starts <cite data-path="x" data-line="1">ensure it</cite>.</p>'
        (only,) = html_sentences(html)
        self.assertEqual((only.text, only.words), ("The pump starts .", 3))
        self.assertNotIn("WORD", html_codes(html))

    def test_entities_are_unescaped_before_counting(self):
        (only,) = html_sentences("<p>Set&nbsp;the pump &amp; the fan to 10&nbsp;mA.</p>")
        self.assertEqual(
            (only.text, only.words, only.checkable),
            ("Set the pump & the fan to 10 mA.", 7, "Set the pump & the fan to §."),
        )
        numeric = (("<p>&#69;nsure it.</p>", "Ensure"), ("<p>&#x65;nsure it.</p>", "ensure"))
        for html, word in numeric:
            with self.subTest(html=html):
                self.assertEqual(
                    html_messages(html, "WORD"),
                    [("E", f'"{word}" is not approved; use MAKE SURE')],
                )

    def test_line_and_col_of_the_first_sentence(self):
        html = "<!doctype html>\n<body>\n  <p>\n    Open the valve. Close it.\n  </p>\n</body>\n"
        self.assertEqual(
            [(s.text, s.line, s.col) for s in html_sentences(html)],
            [("Open the valve.", 4, 5), ("Close it.", 4, 21)],
        )
        cases = {
            "<p>Open the valve.</p>": [("Open the valve.", 1, 4)],
            "<p>A &amp; B. Close it.</p>": [("A & B.", 1, 4), ("Close it.", 1, 15)],
            "<p>Stop. <b>Open</b> it.</p>": [("Stop.", 1, 4), ("Open it.", 1, 13)],
            "<p><code>make</code> builds it.</p>": [("§ builds it.", 1, 4)],
        }
        for html, expected in cases.items():
            with self.subTest(html=html):
                self.assertEqual([(s.text, s.line, s.col) for s in html_sentences(html)], expected)

    def test_br_is_whitespace_and_whitespace_runs_collapse(self):
        html = "<p>In the event\n\t of a leak,<br>stop<br/>the pump.</p>"
        self.assertEqual(html_blocks(html), [("para", ["In the event of a leak, stop the pump."])])
        self.assertEqual(
            html_messages(html, "WORD"), [("E", '"In the event of" is not approved; use IF')]
        )

    def test_comments_and_doctype_are_ignored(self):
        html = "<!doctype html><!-- Ensure it. --><p>Open the<!-- x --> valve.</p>"
        self.assertEqual(html_blocks(html), [("para", ["Open the valve."])])


class HtmlFixtureTest(unittest.TestCase):
    """Spec section 4.5: the `--html` fixture, tests/fixtures/artifact.html."""

    def setUp(self):
        self.text = FIXTURE.read_text(encoding="utf-8")

    def row_of(self, text, needle):
        """1-based line and column of the first `needle` in `text`."""
        lines = text.splitlines()
        row = next(n for n, line in enumerate(lines, 1) if needle in line)
        return row, lines[row - 1].index(needle) + 1

    def test_fixture_yields_the_prose_blocks_only(self):
        self.assertEqual(
            [(b.kind, b.sentences[0].text) for b in ste_lint.html_to_blocks(self.text)],
            [
                ("para", "The fuel pump"),
                ("para", "The fuel pump moves fuel from the tank to the engine."),
                ("ul-item", "The tank holds the fuel"),
                ("ul-item", "The pump moves the fuel"),
                ("ul-item", "The filter removes dirt from the fuel"),
                ("para", "Do these steps to adjust the pressure."),
                (
                    "ol-item",
                    "Turn the adjustment screw on the left side of the pressure regulator "
                    "clockwise until the gauge shows the correct value for the system.",
                ),
                ("ol-item", "Close the drain valve and remove the filter cover with the wrench."),
                ("para", "The pump starts when the engine starts ."),
                ("para", "Run § to test the pump."),
            ],
        )

    def test_fixture_has_no_errors_and_exactly_one_length_proc(self):
        found = html_findings(self.text)
        self.assertEqual([f for f in found if f.severity == "E"], [])
        procs = [f for f in found if f.rule == "LENGTH-PROC"]
        self.assertEqual(
            [(f.line, f.col, f.message) for f in procs],
            [
                (
                    *self.row_of(self.text, "Turn the adjustment"),
                    "procedure step has 23 words (keep to 20, Rule 5.1)",
                )
            ],
        )

    def test_fixture_without_the_skip_attribute_has_word_errors(self):
        self.assertEqual(self.text.count(' data-ste="skip"'), 1)
        broken = self.text.replace(' data-ste="skip"', "")
        errors = [f for f in html_findings(broken) if f.severity == "E"]
        self.assertIn("WORD", [f.rule for f in errors])
        self.assertEqual({f.line for f in errors}, {self.row_of(broken, "Utilize the wrench")[0]})


class CommandLineTest(unittest.TestCase):
    def test_finding_is_a_frozen_dataclass_with_the_brief_fields(self):
        names = [f.name for f in dataclasses.fields(ste_lint.Finding)]
        self.assertEqual(names, ["line", "col", "severity", "rule", "message"])
        finding = ste_lint.Finding(1, 2, "E", "LENGTH", "m")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            finding.line = 3

    def test_output_is_one_line_per_finding_sorted_then_the_summary(self):
        text = "- Open it.\n  - The valve is closed.\n\n  Checking it, don't ensure it.\n"
        self.assertEqual(
            run_main_on_file(text),
            (
                1,
                '2:5  W PASSIVE  possible passive: "is closed"\n'
                '4:3  E CONTRACTION  contraction "don\'t"\n'
                '4:3  W GERUND  possible gerund: "Checking"\n'
                '4:3  E WORD  "ensure" is not approved; use MAKE SURE\n'
                "2 errors, 2 warnings\n",
                "",
            ),
        )

    def test_lint_sorts_findings_by_line_then_col_then_rule(self):
        late = Sentence("Don't stop.", 3, 9, 2, "Don't stop.")
        early = Sentence("Ensure it, don't stop.", 3, 1, 4, "Ensure it, don't stop.")
        result = ste_lint.lint([ste_lint.Block("ul-item", [late, early])])
        self.assertEqual(
            [(f.line, f.col, f.rule) for f in result],
            [(3, 1, "CONTRACTION"), (3, 1, "WORD"), (3, 9, "CONTRACTION")],
        )

    def test_main_prints_exactly_format_findings(self):
        text = "Ensure the pump is running.\n\nThe valve is closed. Don't stop.\n"
        code, out, _ = run_main_on_file(text)
        self.assertEqual(out, ste_lint.format_findings(findings(text)))
        self.assertEqual(ste_lint.format_findings([]), "0 errors, 0 warnings\n")

    def test_exit_0_for_clean_text(self):
        self.assertEqual(run_main_on_file("Open the valve.\n"), (0, "0 errors, 0 warnings\n", ""))

    def test_exit_1_for_text_with_length_error(self):
        self.assertEqual(
            run_main_on_file(sentence_of(26) + "\n"),
            (1, "1:1  E LENGTH  sentence has 26 words (max 25)\n1 errors, 0 warnings\n", ""),
        )

    def test_exit_2_and_usage_for_a_bad_flag_or_two_files(self):
        for argv in (
            ["-x"], ["--help"], ["--html", "-x"], ["a.md", "b.md"], ["--html", "a.html", "b.html"]
        ):
            with self.subTest(argv=argv):
                self.assertEqual(run_main(argv), (2, "", USAGE))

    def test_html_flag_lints_the_fixture_with_no_errors(self):
        expected = ste_lint.format_findings(html_findings(FIXTURE.read_text(encoding="utf-8")))
        fixture = str(FIXTURE)
        for argv in (["--html", fixture], [fixture, "--html"], ["--html", "--html", fixture]):
            with self.subTest(argv=argv):
                code, out, err = run_main(argv)
                self.assertEqual((code, err), (0, ""))
                self.assertRegex(out.splitlines()[-1], r"^0 errors, \d+ warnings$")
                self.assertEqual(out, expected)

    def test_html_flag_reads_stdin_through_html_to_blocks(self):
        page = "<nav><a>Ensure</a></nav>\n<p>Don't stop.</p>\n"
        self.assertEqual(
            run_main(["--html"], stdin=page),
            (1, '2:4  E CONTRACTION  contraction "Don\'t"\n1 errors, 0 warnings\n', ""),
        )
        self.assertIn("E WORD", run_main([], stdin=page)[1])  # Markdown mode reads the nav

    def test_byte_order_mark_of_a_file_is_not_a_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "page.html"
            page.write_text("﻿<p>Don't stop.</p>\n", encoding="utf-8")
            self.assertEqual(
                run_main(["--html", str(page)]),
                (1, '1:4  E CONTRACTION  contraction "Don\'t"\n1 errors, 0 warnings\n', ""),
            )

    def test_exit_2_for_missing_or_unreadable_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = str(Path(tmp) / "missing.md")
            code, out, err = run_main([missing])
            self.assertEqual((code, out), (2, ""))
            self.assertIn("No such file or directory", err)
            self.assertIn(missing, err)
            binary = Path(tmp) / "binary.md"
            binary.write_bytes(b"\xff\xfe Open the valve.")
            for path in (str(binary), tmp):
                with self.subTest(path=path):
                    code, out, err = run_main([path])
                    self.assertEqual((code, out), (2, ""))
                    self.assertNotEqual(err, "")

    def test_reads_stdin_when_no_file_is_given(self):
        self.assertEqual(
            run_main([], stdin="Don't stop.\n"),
            (1, '1:1  E CONTRACTION  contraction "Don\'t"\n1 errors, 0 warnings\n', ""),
        )


if __name__ == "__main__":
    unittest.main()
