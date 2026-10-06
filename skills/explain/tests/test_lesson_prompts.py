"""The prompts of the two review gates of the lesson rung: lesson/review-page.md, lesson/review-script.md and
lesson/review-render.md (spec sections 5.2, 5.4 and 6.4).

Each prompt is a template. The author fills it by plain text replacement of {name}, so a prompt holds the
placeholders of its gate and no other word in braces (PLACEHOLDERS; every {name} counts, name = letters and
"_"). Each prompt has the six level-2 sections of SECTIONS, in that order. Each section holds the sentences
that the spec gives it, word for word (a prompt may wrap a line; the tests compare text with runs of white
space collapsed, squash), and the Checks section holds the numbered list of its gate: three checks for the
page, two for the script, six for the render (CHECK_COUNT).

The text of a check is not pinned here. A unit test cannot tell whether a reviewer finds a planted fault, so
the gates themselves are measured only by the live run (spec section 7.5).

LessonRungCase ties rungs/lesson.md, the file that the lesson author reads, to the files it names. The rung
has the eleven level-2 titles of LESSON_TITLES. Each block of it that names page.md or video.md (a pointer
block) holds a title of that file in double quotes and no section number, and together the pointer blocks
quote the six titles of PAGE_TITLES and the ten of VIDEO_TITLES, each one heading of its file. The one table
headed "| Limit | clip |" is the clip row of video/formats.json (FILM_CELLS, filled by fill), and the floor
sentence of section "Write the page and the clips" gives that row's minText and the 22 px of C.muted. The one
fenced html block is CLIP_MARKUP, the markup of spec section 4.2, and the fenced block of section "Finish and
handoff" is the six lines of verify.sh for a lesson (LESSON_PASS and the media line). Each text of LESSON_TEXTS
occurs in the rung. The {name} set of the rung is the union of PLACEHOLDERS, and the prompt files that it
names are the keys of PLACEHOLDERS, each in LESSON_DIR. The rung passes the STE lint.

This module imports helpers from test_rung_drift.py and LESSON_PASS from test_verify.py; test_rung_drift.py
never imports this module. LESSON_DIR and PLACEHOLDERS name the prompt files and their placeholders, and
CLIP_MARKUP serves the fixture lesson of the E2E. Each test names the mutation that turns it red."""

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_rung_drift import (FENCE, FILM_CELLS, FORMATS_JSON, HEADING, LESSON_MD, SECTION_NUMBER, VIDEO_MD, blocks,
                             fill, heading_rows, headings, limits_table, lint, read, section)
from test_verify import LESSON_PASS

EXPLAIN = Path(__file__).resolve().parent.parent
LESSON_DIR = EXPLAIN / "lesson"
PAGE_MD = EXPLAIN / "rungs" / "page.md"

PAGE, SCRIPT, RENDER = "review-page.md", "review-script.md", "review-render.md"
# The placeholders of each prompt, braces removed (spec section 6.4).
SHARED = frozenset({"subject", "root", "files", "report", "previous"})
PLACEHOLDERS = {
    PAGE: SHARED,
    SCRIPT: SHARED | {"section"},
    RENDER: SHARED | {"section", "changes"},
}
SECTIONS = ("Your task", "Inputs", "Hunt", "Checks", "Round 2", "Report")
CHECK_COUNT = {PAGE: 3, SCRIPT: 2, RENDER: 6}

PLACEHOLDER = re.compile(r"\{([A-Za-z_]+)\}")
CHECK_LINE = re.compile(r"(\d+)\. ")

# The level-2 titles of lesson.md, in order; the rung numbers them from 1.
LESSON_TITLES = ("When a lesson", "What to read", "Plan the lesson", "Write the page and the clips",
                 "Check before the review", "Gate 1: read before the render", "Render the clips",
                 "Gate 2: read the stills", "Drop a clip", "Finish and handoff", "Output directory")
# The sections of page.md and of video.md that lesson.md sends the author to; a title of video.md can be a
# level-3 heading ("The kit", "Marks", "Text on the stage", "The guard", "The FAIL lines").
PAGE_TITLES = ("Plan the sections", "Fill the template", "Diagram patterns", "Provenance", "Write the prose",
               "Verify and export")
VIDEO_TITLES = ("The grammar of a film", "Write the script", "Write the scene", "The kit", "Marks",
                "Text on the stage", "The guard", "Build and check", "The FAIL lines", "Read the stills")
CLIP_TABLE_HEADER = "| Limit | clip |"
# The markup of one clip, as spec section 4.2 gives it. The lesson E2E builds its page from this text.
CLIP_MARKUP = """<figure class="clip">
  <video controls preload="none" src="clips/<id>/video.mp4" poster="clips/<id>/poster.png"></video>
  <figcaption><span class="part"></span>One sentence that says what the clip shows.
    <a href="clips/<id>/index.html" data-ste="skip">transcript</a></figcaption>
</figure>"""
# 22 px is the 16 px dim-caption rule of a film at 75 % (spec section 5.1, step 3): a fixed rule of the plan.
DIM_FLOOR = 22
# What lesson.md says in its own words that no table or other test pins: names of files, lines and rules.
LESSON_TEXTS = (
    '<meta name="explain-rung" content="lesson">',
    "Rung: lesson (forced) — <reason> — subject: <subject> (<kind>)",
    "<id> | <h2 question> | clip: yes|no | <reason, when yes>",
    "--as page",
    '"format": "clip"',
    "templates/video-script.json",
    "<skill-dir>/video/src/film/",
    "review/plan.md",
    "review/plants.md",
    "review/gate1-page-round-<k>.md",
    "review/gate1-<id>-round-<k>.md",
    "review/gate1-<id>.script.json",
    "review/gate2-<id>-<part>-round-<k>.md",
    "## Author",
    "narration (<engine>): ok",
    "render: FAIL <cause>",
    "clips/<id>/poster.png",
    "still-NN-<scene>-end.png",
    '<div class="wide"><dt>Dropped clips</dt><dd>none</dd></div>',
    "<id> — <reason>",
    "disputed findings: none",
)

READ_ONLY = "Read only these files and the files under the repository root."
HUNT_CLAIM = "Hunt. Assume one claim in this file is not supported by its cited lines, and find it."
HUNT_NONE = ("If, after reading every cite against the source, you find none, `verdict: ok` with zero findings "
             "is the right answer and is expected for a correct artifact.")
HUNT_QUOTE = "Never report a finding you cannot back with a quoted source line."
HUNT_STILL = "Hunt. Assume one still gives a false picture of what its scene narrates, and find it."
HUNT_CLIP = "`verdict: ok` with zero findings is expected for a correct clip."
HUNTS = {
    PAGE: (HUNT_CLAIM, HUNT_NONE, HUNT_QUOTE),
    SCRIPT: (HUNT_CLAIM, HUNT_NONE, HUNT_QUOTE),
    RENDER: (HUNT_STILL, HUNT_CLIP),
}
SKIP_CHECK_5 = "If `{changes}` is `nothing`, the two scripts are the same: skip check 5."
ROUND_1 = "If `{previous}` is `none`, this is round 1: skip this section."
RULE_FIRST = ("Before you hunt, rule each finding of that report `resolved` or `open`, and quote the current "
              "source line.")
VERIFY_READ = ("If the name of `{previous}` ends in `-round-2.md`, this is a verification read: rule its "
               "findings and hunt for nothing new.")
# What a round 2 reviewer does after its rulings. A gate 1 prompt always hunts; the render prompt hunts unless
# the read is a verification read, and then the verdict follows the rulings alone.
HUNT_AFTER = "Then hunt, as the Hunt section says, and number each new finding after the old ones."
HUNT_UNLESS = ("Then, unless this is a verification read, hunt as the Hunt section says, and number each new "
               "finding after the old ones.")
VERIFY_VERDICT = ("In a verification read, write `verdict: ok` when each finding is `resolved`, and "
                  "`verdict: fix` when one is `open`.")
REPORT_RULES = ("A finding without a quoted source line is not a finding.",
                "The last line of your text is `verdict: ok` or `verdict: fix`.",
                "Write `verdict: fix` when the report has at least one finding.")


def squash(text):
    """The text with each run of white space collapsed to one space."""
    return " ".join(text.split())


def prompt(name):
    return read(LESSON_DIR / name)


def held(name, title, sentences):
    """The sentences of `sentences` that section `title` of prompt `name` does not hold, white space collapsed."""
    body = squash(section(prompt(name), title))
    return [sentence for sentence in sentences if squash(sentence) not in body]


class LessonPromptCase(unittest.TestCase):
    # red: the render prompt without {previous}, a misspelt {reports}, a {section} in the page prompt, or a word
    # in braces that is no placeholder
    def test_each_prompt_has_exactly_its_placeholders(self):
        for name, expected in PLACEHOLDERS.items():
            with self.subTest(prompt=name):
                self.assertEqual(set(PLACEHOLDER.findall(prompt(name))), set(expected))

    # red: a prompt with no Round 2 section, two sections swapped, or a seventh section
    def test_each_prompt_has_the_six_sections(self):
        for name in PLACEHOLDERS:
            with self.subTest(prompt=name):
                found = [title for level, title in headings(prompt(name)) if level == 2]
                self.assertEqual(found, list(SECTIONS))

    # red: the zero-findings sentence dropped from one prompt, the hunt of gate 2 in a gate 1 prompt or the
    # other way round
    def test_each_prompt_hunts_with_an_exit(self):
        for name, sentences in HUNTS.items():
            with self.subTest(prompt=name):
                self.assertEqual(held(name, "Hunt", sentences), [])
        other = {PAGE: HUNT_STILL, SCRIPT: HUNT_STILL, RENDER: HUNT_CLAIM}
        for name, sentence in other.items():
            with self.subTest(prompt=name, other_gate=True):
                self.assertNotIn(squash(sentence), squash(prompt(name)))

    # red: the verdict rule or the quoted-line rule left out of the Report section of one prompt
    def test_each_report_needs_a_quoted_source_line(self):
        for name in PLACEHOLDERS:
            with self.subTest(prompt=name):
                self.assertEqual(held(name, "Report", REPORT_RULES), [])

    # red: a check dropped or two merged, a check numbered out of turn, or a line of another list in Checks that
    # starts with a number
    def test_each_prompt_lists_its_checks(self):
        for name, count in CHECK_COUNT.items():
            body = section(prompt(name), "Checks")
            starts = [found.group(1) for found in map(CHECK_LINE.match, body.split("\n")) if found]
            with self.subTest(prompt=name):
                self.assertEqual(starts, ["%d" % number for number in range(1, count + 1)])

    # red: the `none` sentence left out of one prompt, or the rule-before-hunt sentence; the verification read
    # left out of the render prompt, or put into a prompt of gate 1
    def test_round_2_rules_before_it_hunts(self):
        for name in PLACEHOLDERS:
            with self.subTest(prompt=name):
                self.assertEqual(held(name, "Round 2", (ROUND_1, RULE_FIRST)), [])
        self.assertEqual(held(RENDER, "Round 2", (VERIFY_READ,)), [])
        for name in (PAGE, SCRIPT):
            with self.subTest(prompt=name, verification=False):
                self.assertNotIn(squash(VERIFY_READ), squash(prompt(name)))

    # red: the render prompt tells a verification read to hunt with no condition ("Then hunt, as the Hunt
    # section says", the first version), or leaves out its verdict rule, or the condition is left out of its
    # hunt sentence; a gate 1 prompt loses its hunt after the rulings, or gets the verification condition
    def test_a_verification_read_does_not_hunt(self):
        render = squash(section(prompt(RENDER), "Round 2"))
        self.assertEqual(held(RENDER, "Round 2", (HUNT_UNLESS, VERIFY_VERDICT)), [])
        self.assertNotIn(squash(HUNT_AFTER), render)
        # each sentence that sends the reader to the Hunt section says when it does not
        sends = [sentence for sentence in re.split(r"(?<=\.) ", render) if "as the Hunt section says" in sentence]
        self.assertEqual([sentence for sentence in sends if "unless this is a verification read" not in sentence],
                         [])
        for name in (PAGE, SCRIPT):
            with self.subTest(prompt=name):
                self.assertEqual(held(name, "Round 2", (HUNT_AFTER,)), [])
                self.assertNotIn("verification", squash(section(prompt(name), "Round 2")))

    # red: the sentence left out of the Inputs section of one prompt
    def test_the_reviewer_reads_only_its_inputs(self):
        for name in PLACEHOLDERS:
            with self.subTest(prompt=name):
                self.assertEqual(held(name, "Inputs", (READ_ONLY,)), [])

    # red: the sentence left out of the Checks section of the render prompt, or put into another section
    def test_the_render_prompt_skips_check_5_without_changes(self):
        self.assertEqual(held(RENDER, "Checks", (SKIP_CHECK_5,)), [])


def fenced_blocks(text):
    """(opening line, lines) of each fenced block of `text`, in order; the opening line has its outer white
    space stripped, the lines are as written."""
    found, current = [], None
    for line in text.split("\n"):
        if FENCE.match(line):
            if current is None:
                current = (line.strip(), [])
            else:
                found.append(current)
                current = None
        elif current is not None:
            current[1].append(line)
    return found


def pointer_blocks(text, name):
    """The blocks of `text` that name the file `name` and are not a heading. A name is a whole file name: the
    prompt file `review-page.md` does not name `page.md` (no letter, digit, "_" or "-" before the name)."""
    pattern = re.compile(r"(?<![\w-])%s" % re.escape(name))
    return [block for block in blocks(text) if pattern.search(block) and not HEADING.fullmatch(block)]


def quoted_titles(block, path):
    """The titles of the headings of the file `path` that `block` holds in double quotes (a line break inside
    a title reads as one space)."""
    flat = squash(block)
    return [title for _, title in headings(read(path)) if '"%s"' % title in flat]


class LessonRungCase(unittest.TestCase):
    def setUp(self):
        self.text = read(LESSON_MD)

    # red: a contraction, or a sentence of 26 words
    def test_lesson_md_lints_clean(self):
        run = lint(LESSON_MD)
        self.assertEqual((run.returncode, run.stdout), (0, "0 errors, 0 warnings\n"), run.stderr)

    # red: a section missing, two swapped, or one numbered out of turn
    def test_the_headings_of_lesson_md(self):
        lines = self.text.split("\n")
        found = [lines[index] for index, level, _ in heading_rows(lines) if level == 2]
        self.assertEqual(found, ["## %d. %s" % (number, title) for number, title in enumerate(LESSON_TITLES, 1)])

    # red: a pointer block with no title in double quotes (a bare "see page.md"), a title of video.md that the
    # rung writes as "The Guard", a section named by number ("section 7 of `page.md`"), or a title that no
    # block quotes any more
    def test_lesson_points_at_page_and_video_by_title(self):
        for path, titles in ((PAGE_MD, PAGE_TITLES), (VIDEO_MD, VIDEO_TITLES)):
            pointers = pointer_blocks(self.text, path.name)
            held = set()
            self.assertTrue(pointers, "lesson.md names %s in no block" % path.name)
            for block in pointers:
                quoted = quoted_titles(block, path)
                held.update(quoted)
                with self.subTest(file=path.name, block=block[:60]):
                    self.assertTrue(quoted, "no title of %s in double quotes" % path.name)
                    self.assertIsNone(SECTION_NUMBER.search(squash(block)))
            with self.subTest(file=path.name, titles=True):
                self.assertEqual([title for title in titles if title not in held], [])
                found = [title for _, title in headings(read(path))]
                self.assertEqual([title for title in titles if found.count(title) != 1], [])

    # red: a value changed in the clip row of formats.json and not in the rung (maxTotalSeconds 50), a row on
    # one side only, or a second table with the same header
    def test_the_clip_limits_table_matches_formats(self):
        row = json.loads(read(FORMATS_JSON))["clip"]
        expected = [(label, fill(template, row)) for label, template in FILM_CELLS]
        self.assertEqual(list(limits_table(LESSON_MD, CLIP_TABLE_HEADER).items()), expected)

    # red: the 22 px rule left out, the clip minText of formats.json changed to 20 and the rung left at 19,
    # or the sentence put into another section
    def test_the_clip_floors(self):
        clip = json.loads(read(FORMATS_JSON))["clip"]["minText"]
        floor = "Draw each text at %s px or more on the canvas, and each text in `C.muted` at %d px or more." % (
            clip, DIM_FLOOR)
        # the rung wraps its lines, so the section is read as one line of words
        body = squash(section(self.text, "Write the page and the clips"))
        self.assertEqual(body.count(floor), 1)

    # red: preload="none" or data-ste="skip" dropped from the markup, a second html block (the Dropped clips
    # row in an html fence), or the markup copied with another class
    def test_the_clip_markup_is_the_spec_markup(self):
        html = [lines for opener, lines in fenced_blocks(self.text) if opener == "```html"]
        self.assertEqual(len(html), 1)
        self.assertEqual("\n".join(html[0]), CLIP_MARKUP)

    # red: the media line left out of the block, or a line of the five reworded
    def test_lesson_quotes_the_six_verify_lines(self):
        found = [[line.strip() for line in lines]
                 for _, lines in fenced_blocks(section(self.text, "Finish and handoff"))]
        self.assertIn(LESSON_PASS.splitlines() + ["media: ok"], found)

    # red: a report name in the old form (review/gate2-<id>-round-<k>.md), a name of an exact text left out
    def test_lesson_holds_its_rules(self):
        text = squash(self.text)
        self.assertEqual([want for want in LESSON_TEXTS if squash(want) not in text], [])

    # red: {changes} never explained to the author, a word in braces that is no placeholder, a prompt file
    # that lesson.md leaves out, or a prompt file renamed
    def test_lesson_names_every_placeholder_and_prompt(self):
        self.assertEqual(set(PLACEHOLDER.findall(self.text)), set().union(*PLACEHOLDERS.values()))
        named = set(re.findall(r"<skill-dir>/lesson/([\w-]+\.md)", self.text))
        self.assertEqual(named, set(PLACEHOLDERS))
        for name in named:
            with self.subTest(prompt=name):
                self.assertTrue((LESSON_DIR / name).is_file())


if __name__ == "__main__":
    unittest.main()
