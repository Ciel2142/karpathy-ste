"""The subagent prompts of the movie rung (spec sections 4.3, 5 and D12): movie/chapter-task.md, the brief of
one chapter subagent. Tasks 4 and 5 of wave 2 add movie/review-viewer.md and movie/review-chapter.md.

Each prompt is a template. The orchestrator fills it by plain text replacement of {name}, so a prompt holds
the placeholders of PLACEHOLDERS and no other word in braces (every {name} counts, name = letters and "_").
Each prompt ends its reply with one result line (RESULT_LINES): the orchestrator keeps its context small and
reads that line, not the chapter. The chapter prompt holds the overrides of the movie (CHAPTER_OVERRIDES): the
output directory instead of convention 5, no write of movie.json, the `ask` scene first and the `answer`
scene last (movie.py check tests the ids, the prompt says what they speak), the root and the lang of the
movie, the length target with its tolerance of a fifth (the remedy of "Stitch" relies on it), no `.bpmn`
cite, the check before the first render, no `open`, the amendment that changes the picture and never the
answers (Review Focus 5), and the `disputed:` lines of D12 before the result line.

The rung ties back: the {name} set of rungs/movie.md is the union of PLACEHOLDERS (its fill tables), the fill
table of "Build the chapters" has one row for each placeholder of the chapter prompt, and each key of
PLACEHOLDERS is a file in MOVIE_DIR that the rung names as `<skill-dir>/movie/<file>`. The prompts pass the
STE lint.

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
# The placeholders of each prompt, braces removed (spec section 5, step 5). Tasks 4 and 5 add their keys.
PLACEHOLDERS = {
    CHAPTER: frozenset({"skill_dir", "movie_dir", "chapter_id", "chapter_json", "questions_json", "other_chapters",
                        "subject_json", "root", "lang", "review", "amendment"}),
}
# The one line that each subagent ends its reply with; the orchestrator reads it, not the work.
RESULT_LINES = {
    CHAPTER: ("chapter: {chapter_id} built", "chapter: {chapter_id} failed <reason>"),
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

    # red: a placeholder of a prompt that the fill tables of the rung leave out, or a word in braces in the rung
    # that no prompt has
    def test_rung_names_every_placeholder(self):
        self.assertEqual(placeholders_of(read(MOVIE_MD)), set().union(*PLACEHOLDERS.values()))

    # red: a row of the fill table of the chapter prompt left out of "Build the chapters", put in another
    # section, or written two times
    def test_build_section_fills_each_chapter_placeholder(self):
        rows = FILL_ROW.findall(section(read(MOVIE_MD), "Build the chapters"))
        self.assertEqual(sorted(rows), sorted(PLACEHOLDERS[CHAPTER]))

    # red: a prompt file renamed on disk or in the rung, a prompt of PLACEHOLDERS that the rung never names, or a
    # prompt named that is none of the three of the movie rung (Task 5 adds the equality of the full set)
    def test_rung_names_prompt_files_that_exist(self):
        named = set(re.findall(r"<skill-dir>/movie/([\w-]+\.md)", read(MOVIE_MD)))
        self.assertLessEqual(named, {CHAPTER, VIEWER, REVIEW})
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
