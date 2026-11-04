"""The subagent prompts of the movie rung (spec sections 4.3, 5 and D10 to D12): movie/chapter-task.md, the brief
of one chapter subagent, movie/review-viewer.md, the brief of the cold viewer, and movie/review-chapter.md, the
brief of the cold fact reviewer of one chapter script under --review (D12).

Each prompt is a template. The orchestrator fills it by plain text replacement of {name}, so a prompt holds
the placeholders of PLACEHOLDERS and no other word in braces (every {name} counts, name = letters and "_").
Each prompt ends its reply with one result line (RESULT_LINES): the orchestrator keeps its context small and
reads that line, not the chapter. The chapter prompt holds the overrides of the movie (CHAPTER_OVERRIDES): the
output directory instead of convention 5, no write of movie.json, the `ask` scene first and the `answer`
scene last (movie.py check tests the ids, the prompt says what they speak), the root and the lang of the
movie, the length target with its tolerance of a fifth (the remedy of "Stitch" relies on it), no `.bpmn`
cite, the check before the first render, no `open`, the amendment that changes the picture and never the
answers (Review Focus 5), and the `disputed:` lines of D12 before the result line. The viewer prompt holds the
closure of D10 and spec 5 step 8 (VIEWER_TEXTS): the viewer reads the viewer page and the stills that it names,
and no other file of the run, answers in its own words or with `cannot answer`, and guesses nothing. The gate
prompt holds the checks of D12 (REVIEW_TEXTS): the narration against the cited lines, the `answer` scene against
the answers of the questions (it may say less, never something different), the `ask` scene against the question
of the chapter, and the rounds of lesson/review-script.md (rulings `resolved` or `open`, a verification read,
`verdict: ok|fix` last, the `## Author` block of the author).

The rung ties back: the {name} set of rungs/movie.md is the union of PLACEHOLDERS (its fill tables), the fill
table of "Build the chapters" (outside "The chapter gate") has one row for each placeholder of the chapter prompt,
the fill table of "The chapter gate" has one row for each placeholder of the gate prompt, the fill table of "The
viewer gate" has one row for each placeholder of the viewer prompt, and the `<skill-dir>/movie/<file>` names of
the rung are the keys of PLACEHOLDERS, each a file in MOVIE_DIR. "The chapter gate" keeps its reports in
`chapters/<id>/gate/`, which render.sh never empties (it empties `chapters/<id>/review/` on each render), and
holds the open-finding rule of D12. The prompts pass the STE lint.

This module imports helpers from test_rung_drift.py and test_lesson_prompts.py; no module imports this one.
Each test names the mutation that turns it red."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lesson_prompts import PLACEHOLDER, squash
from test_rung_drift import MOVIE_MD, lint, read, section

EXPLAIN = Path(__file__).resolve().parent.parent
MOVIE_DIR = EXPLAIN / "movie"

CHAPTER, VIEWER, REVIEW = "chapter-task.md", "review-viewer.md", "review-chapter.md"
# The placeholders of each prompt, braces removed (spec section 5, step 5, and D12).
PLACEHOLDERS = {
    CHAPTER: frozenset({"skill_dir", "movie_dir", "chapter_id", "chapter_json", "questions_json", "other_chapters",
                        "subject_json", "root", "lang", "review", "amendment"}),
    VIEWER: frozenset({"transcript", "stills_dir", "report", "movie_dir", "lang"}),
    REVIEW: frozenset({"subject", "root", "files", "chapter_id", "question", "questions_json", "report",
                       "previous"}),
}
# The one line that each subagent ends its reply with; the orchestrator reads it, not the work.
RESULT_LINES = {
    CHAPTER: ("chapter: {chapter_id} built", "chapter: {chapter_id} failed <reason>"),
    VIEWER: ("viewer: done", "viewer: failed <reason>"),
    REVIEW: ("verdict: ok", "verdict: fix"),
}
# The overrides of the movie, as chapter-task.md words them.
CHAPTER_OVERRIDES = (
    # the output directory (instead of convention 5), and the plan stays the orchestrator's
    "Your output directory is `{movie_dir}/chapters/{chapter_id}/`. It replaces the directory of convention 5 "
    "of `SKILL.md`.",
    "Write no file outside it.",
    "Never write `movie.json`: the orchestrator writes it.",
    "Print the rung line of `video.md` with this reason: `movie chapter {chapter_id}`.",
    # spec 4.3: movie.py check tests the ids and the title; the prompt says what the two scenes speak
    "The `title` of the script is the `title` of the chapter.",
    "The first scene has the id `ask`. Its narration asks the `question` of the chapter.",
    "The last scene has the id `answer`. Its narration states each `answer` of the questions above, so that a "
    "cold viewer can repeat it.",
    # D10: the viewer page leaves out the two scenes, so the body must show the answers
    "The cold viewer does not see the `ask` and `answer` scenes.",
    # check compares the root and the lang of the script with those of the movie
    "`provenance.root` is `{root}`, and `lang` is `{lang}`.",
    # the remedy of "Stitch" relies on this tolerance
    "The length target of the film is the `seconds` of the chapter, within a fifth either way.",
    # fix round 1 (task 3 review): the tolerance is a condition of `built`, with a bound on the renders
    "A length outside that range is a fault, also when the eleven stage lines show `ok`.",
    "After 3 renders in which the length stays outside the range, ship the chapter.",
    "`off target: <s> s, target <seconds> s`",
    "Do this until its eleven stage lines show `ok` and the length is in the range of \"Length\".",
    "Its render shows eleven `ok` lines, its length is within a fifth of `seconds`, and its stills have no "
    "fault.",
    # the cites: copied from the questions, or read from the disk; no .bpmn (verify.sh would fail the hub)
    "Copy a cite of the questions above where the narration makes the claim of that cite.",
    "Cite no `.bpmn` file.",
    # the check before the first render, and the lines that the subagent owns
    "python3 {skill_dir}/scripts/movie.py check {movie_dir}",
    "Fix each line that starts with `chapter {chapter_id}:` and names your script",
    "Never run `open`.",
    # Review Focus 5: the amendment after a viewer miss changes the picture, not the contract
    "{amendment} The amendment changes the picture, never the answers.",
    # the review flag, and D12: an open finding ships, as a disputed line before the result line
    "If it is `off`, start no subagent.",
    "{skill_dir}/movie/review-chapter.md",
    "The chapter ships: render it, and end with `chapter: {chapter_id} built`.",
    "Before that line, write one `disputed: <finding>` line for each such finding.",
    # final review I6: the fallback ships, and the reply carries its stage line before the result line
    "A narration fallback is not a fault.",
    "- the `narration` stage line of your last render, when it names a fallback: "
    "`narration (say): ok (fallback: <cause>)`.",
    "- the `off target:` line, when the length stays outside the range of \"Length\";",
)
# The closure of the cold viewer (D10, spec 5 step 8), as review-viewer.md words it: the viewer page and the
# stills that it names, no other file of the run, an answer in its own words or `cannot answer`, no guess, a part
# known only from before named as a gap (the author then marks it `missed`), the last line of the report, and the
# `## Author` block that the author appends.
VIEWER_TEXTS = (
    "{transcript}",
    "still: viewer-stills/",
    "not `movie.json`",
    "no `script.json`",
    "no other still",
    "cannot answer",
    "in your own words",
    "guess nothing",
    # fix round 1 (task 4 review): knowledge from before goes to the gap of a half answer, not into the answer
    "If you know a part only from before, not from the film, do not write it as your answer. Name it as the part "
    "that you could not find in the film.",
    "If you know all of the answer only from before, write `cannot answer`.",
    # final review I7: the two forms of the evidence, one on each line, which the author checks
    'used: <chapter title>: "<sentence>"',
    "used: <chapter title>: still <k>-<id>.png: <what it shows>",
    "viewer: done",
    "## Author",
)
# The checks and the rounds of the chapter gate (D12), as review-chapter.md words them: the answers of the questions
# that the `answer` scene states (it may say less, never something different), the question of the chapter that the
# `ask` scene poses (other words, never a different question), the last line of the report, the rulings of round 2,
# the verification read and the `## Author` block that the author appends.
REVIEW_TEXTS = (
    "{questions_json}",
    "`answer` scene",
    "never something different",
    "`ask` scene",
    # fix round 1 (controller ruling on concern 2): D12 gives the reviewer the question of the chapter, on its own
    # line (a {name} inside a sentence would expand the text there), and check 3 reads the `ask` scene against it
    "This is the question of the chapter, which its `ask` scene poses: {question}",
    "The `ask` scene poses the question of the chapter above.",
    "never a different question",
    # fix round 2 (task 5 review): the closure of the model, also on the parent of the movie directory; the runs
    # live in ~/karpathy/out/, under the root, and the gate reports of an earlier run would warm the reviewer (the
    # model's "its parent directory" is "its parent" here: the model's sentence has 26 words, over the lint's 25)
    "Under the directory of the movie, and under its parent, read no file except the files listed below and the "
    "report that Round 2 names.",
    "verdict: ok",
    "verdict: fix",
    "resolved",
    "open",
    "-round-2.md",
    "## Author",
)
# The rounds of the chapter gate in "Build the chapters" (D12, and the controller ruling of wave 2 on the report
# directory): the reports out of `review/`, an open finding that ships as a `disputed:` line, no dropped chapter.
GATE_TEXTS = (
    "`chapters/<id>/gate/gate-round-<k>.md`",
    "`gate-round-3.md`",
    "`gate-round-4.md`",
    "`disputed: <finding>`",
    "A chapter is never dropped",
)
# A row of a fill table: `| `{name}` | ... |`.
FILL_ROW = re.compile(r"^\| `\{([A-Za-z_]+)\}` \|", re.MULTILINE)


def prompt(name: str) -> str:
    return read(MOVIE_DIR / name)


def placeholders_of(text: str) -> set[str]:
    """The names in braces of `text`, braces removed."""
    return set(PLACEHOLDER.findall(text))


class MoviePromptCase(unittest.TestCase):
    # red: {movie} for {movie_dir}, {questions_json} left out of the chapter prompt, or a word in braces that is
    # no placeholder (a JSON example such as {"id": …})
    def test_placeholders_are_exactly_the_named_set(self):
        for name, expected in PLACEHOLDERS.items():
            with self.subTest(prompt=name):
                self.assertEqual(placeholders_of(prompt(name)), set(expected))

    # red: a result line reworded (`chapter: done`), its id left out, or the failed form left out
    def test_result_lines_present(self):
        for name, lines in RESULT_LINES.items():
            text = prompt(name)
            for line in lines:
                with self.subTest(prompt=name, line=line):
                    self.assertIn(line, text)

    # red: an override left out or reworded (convention 5 back as the output directory, the `answer` scene
    # first, a relative root, the tolerance of the length dropped, a `.bpmn` cite allowed, no check before the
    # render, the amendment allowed to change the answers, or the disputed lines after the result line)
    def test_chapter_task_names_the_overrides(self):
        text = squash(prompt(CHAPTER))
        self.assertEqual([want for want in CHAPTER_OVERRIDES if squash(want) not in text], [])

    # red: the viewer may read `movie.json`, a `script.json` or another still (then it can always answer), the
    # still name of the viewer page left out, `cannot answer` or `guess nothing` left out (then it guesses), a part
    # known only from before written as an answer (then the author counts a recall as `understood`), or the report
    # without its last line
    def test_viewer_reads_only_the_transcript_and_its_stills(self):
        text = squash(prompt(VIEWER))
        self.assertEqual([want for want in VIEWER_TEXTS if squash(want) not in text], [])

    # red: the `answer` scene allowed to say something else than the answers, the check of the `ask` scene left
    # out or made against the viewer questions instead of {question}, the parent of the movie directory left open
    # (then the gate reports of an earlier run are in reach), the rulings or the verification read of round 2 left
    # out, or the report without its last line
    def test_review_chapter_checks_the_answer_scene(self):
        text = squash(prompt(REVIEW))
        self.assertEqual([want for want in REVIEW_TEXTS if squash(want) not in text], [])

    # red: the gate reports back in `chapters/<id>/review/` (render.sh empties it on each render), no cap on the
    # verification reads, an open finding that drops the chapter or that the reply does not carry as a `disputed:`
    # line, or the output directory without the row of `chapters/<id>/gate/`
    def test_rung_review_rounds_follow_d12(self):
        text = read(MOVIE_MD)
        build = squash(section(text, "Build the chapters"))
        self.assertEqual([want for want in GATE_TEXTS if squash(want) not in build], [])
        self.assertNotIn("review/gate-round", text)
        self.assertIn("| `chapters/<id>/gate/` |", section(text, "Output directory"))

    # red: a placeholder of a prompt that the fill tables of the rung leave out, or a word in braces in the rung
    # that no prompt has
    def test_rung_names_every_placeholder(self):
        self.assertEqual(placeholders_of(read(MOVIE_MD)), set().union(*PLACEHOLDERS.values()))

    # red: a row of the fill table of the chapter prompt left out of "Build the chapters", put in another
    # section (also "The chapter gate"), or written two times
    def test_build_section_fills_each_chapter_placeholder(self):
        text = read(MOVIE_MD)
        build = section(text, "Build the chapters").replace(section(text, "The chapter gate"), "")
        self.assertEqual(sorted(FILL_ROW.findall(build)), sorted(PLACEHOLDERS[CHAPTER]))

    # red: a row of the fill table of the gate prompt left out of "The chapter gate", put in another section, or
    # written two times (the chapter subagent reads only that subsection of the rung)
    def test_chapter_gate_fills_each_review_placeholder(self):
        rows = FILL_ROW.findall(section(read(MOVIE_MD), "The chapter gate"))
        self.assertEqual(sorted(rows), sorted(PLACEHOLDERS[REVIEW]))

    # red: a row of the fill table of the viewer prompt left out of "The viewer gate", put in another section, or
    # written two times
    def test_viewer_section_fills_each_viewer_placeholder(self):
        rows = FILL_ROW.findall(section(read(MOVIE_MD), "The viewer gate"))
        self.assertEqual(sorted(rows), sorted(PLACEHOLDERS[VIEWER]))

    # red: a prompt file renamed on disk or in the rung, a prompt of PLACEHOLDERS that the rung never names, or a
    # prompt named that is none of the three of the movie rung
    def test_rung_names_prompt_files_that_exist(self):
        named = set(re.findall(r"<skill-dir>/movie/([\w-]+\.md)", read(MOVIE_MD)))
        self.assertEqual(named, set(PLACEHOLDERS))
        for name in PLACEHOLDERS:
            with self.subTest(prompt=name):
                self.assertIn(name, named)
                self.assertTrue((MOVIE_DIR / name).is_file())

    # red: a sentence of 26 words, a contraction or a word of the substitution table in a prompt
    def test_prompts_lint_clean(self):
        for name in PLACEHOLDERS:
            with self.subTest(prompt=name):
                run = lint(MOVIE_DIR / name)
                self.assertEqual((run.returncode, run.stdout), (0, "0 errors, 0 warnings\n"), run.stderr)


if __name__ == "__main__":
    unittest.main()
