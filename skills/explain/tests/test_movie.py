"""Tests for movie.py: load, atomic save and the plan check of `movie.json` (spec 4.2, 6).

Each test copies `tests/fixtures/movie/` to a temporary directory, changes one thing and
expects the failure line of that change. The fixture's `provenance.root` is `.`, so cites
resolve under the copied directory.
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import movie  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = movie.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class MovieCase(unittest.TestCase):
    """A private copy of the fixture per test; `self.movie` is the parsed movie.json."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = os.path.join(tmp.name, "movie")
        shutil.copytree(FIXTURES / "movie", self.dir)
        self.movie = movie.load(self.dir)

    def failures(self):
        return movie.check(self.dir, self.movie)

    def chapter(self, ident):
        return next(c for c in self.movie["chapters"] if c["id"] == ident)


class CheckCase(MovieCase):
    def test_good_plan_prints_plan_ok(self):
        code, out, err = run_cli("check", self.dir)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines()[-1], "plan: ok (3 questions, 4 chapters, 240 s target)")

    def test_a_question_no_chapter_answers(self):
        for chapter in self.movie["chapters"]:
            chapter["answers"] = [a for a in chapter["answers"] if a != "q-3"] or ["q-1"]
        self.assertEqual(self.failures(), ["question q-3: no chapter answers it"])

    def test_a_chapter_with_three_answers(self):
        self.chapter("pause")["answers"] = ["q-1", "q-2", "q-3"]
        self.assertEqual(self.failures(), ["chapter pause: answers has 3 entries (max 2)"])

    def test_an_unknown_answer_id(self):
        self.chapter("members")["answers"] = ["q-1", "q-nope"]
        self.assertEqual(self.failures(), ["chapter members: answers names q-nope, not a question"])

    def test_too_few_chapters(self):
        del self.movie["chapters"][0]
        self.assertIn("schema: chapters has 3 entries (min 4, max 10)", self.failures())

    def test_seconds_sum_out_of_range(self):
        for chapter in self.movie["chapters"]:
            chapter["seconds"] = 30
        self.assertEqual(self.failures(), ["schema: seconds sum 120 (min 240, max 900)"])

    def test_seconds_not_an_integer(self):
        self.chapter("split")["seconds"] = "60"
        self.assertEqual(
            self.failures(),
            ["chapter split: seconds must be an integer from 30 to 150"])

    def test_a_duplicate_id(self):
        self.chapter("split")["id"] = "q-1"
        self.assertIn("id: q-1 is used twice", self.failures())

    def test_a_file_subject_needs_a_cite_per_question(self):
        self.movie["subject"]["kind"] = "file"
        self.assertEqual(
            self.failures(),
            ["question %s: a file or directory subject needs at least one cite" % q["id"]
             for q in self.movie["questions"]])

    def test_a_bad_cite_is_reported(self):
        self.movie["subject"]["kind"] = "file"
        with open(os.path.join(self.dir, "notes.txt"), "w", encoding="utf-8") as handle:
            handle.write("alpha beta\n")
        for question in self.movie["questions"]:
            question["cites"] = [{"path": "notes.txt", "line": 1, "snippet": "alpha beta"}]
        self.assertEqual(self.failures(), [])
        self.movie["questions"][0]["cites"][0]["snippet"] = "gamma delta"
        failures = self.failures()
        self.assertEqual(len(failures), 1)
        self.assertTrue(failures[0].startswith("cite q-1#1:"), failures[0])

    def test_a_prose_fault_is_reported(self):
        self.movie["title"] = "It is what it is, and this very long title keeps going on and on " \
                              "and on while it says nothing at all about the thing that it names"
        failures = self.failures()
        self.assertTrue(failures and failures[0].startswith("prose: title: E "), failures)

    def test_a_prose_fault_in_a_later_field_names_that_field(self):
        self.chapter("split")["picture"] = "It is what it is, and this very long picture keeps " \
            "going on and on while it says nothing at all about the thing that it shows"
        failures = self.failures()
        self.assertEqual(len(failures), 1, failures)
        self.assertTrue(failures[0].startswith("prose: chapters[split].picture: E "), failures)

    def test_a_bad_version_and_state(self):
        self.movie["version"] = 2
        self.movie["state"] = "done"
        self.assertEqual(self.failures(), ["schema: version must be 1",
                                           "state: must be one of planned, building, stitched"])

    def test_failures_print_then_count_and_exit_1(self):
        self.chapter("pause")["answers"] = ["q-1", "q-2", "q-3"]
        movie.save(self.dir, self.movie)
        code, out, _ = run_cli("check", self.dir)
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines(), [
            "chapter pause: answers has 3 entries (max 2)", "plan: 1 failures"])

    def test_invalid_json_exits_2(self):
        with open(os.path.join(self.dir, "movie.json"), "w", encoding="utf-8") as handle:
            handle.write("{not json")
        code, out, err = run_cli("check", self.dir)
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(len(err.splitlines()), 1)

    def test_usage_errors_exit_2(self):
        self.assertEqual(run_cli()[0], 2)
        self.assertEqual(run_cli("check")[0], 2)
        self.assertEqual(run_cli("bridges", self.dir)[0], 2)


class SaveCase(MovieCase):
    def test_save_is_atomic(self):
        self.movie["title"] = "Changed"
        movie.save(self.dir, self.movie)
        self.assertEqual(sorted(os.listdir(self.dir)), ["movie.json"])
        self.assertEqual(movie.load(self.dir), self.movie)
        json.loads(Path(self.dir, "movie.json").read_text(encoding="utf-8"))

    def test_resolve_root(self):
        self.assertEqual(movie.resolve_root(self.dir, "."), os.path.abspath(self.dir))
        self.assertEqual(movie.resolve_root(self.dir, "/abs"), "/abs")


if __name__ == "__main__":
    unittest.main()
