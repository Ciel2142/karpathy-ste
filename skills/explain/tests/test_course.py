"""Tests for course.py: load, atomic save and the structural check of `course.json`
(spec section 5 and 6; the failure-line prefixes are fixed by the plan, section 4).

The fixture is `tests/fixtures/course/course.json` over the fake root
`tests/fixtures/course-root/` (sources `svc-a/` code and `docs-b/` markdown). Its `root` is
the relative path `../course-root`; `course.py` resolves a relative `root` against the course
directory, so the fixture works wherever the repository is checked out. Each test copies both
fixture directories to a temporary directory (keeping the same relative layout), changes one
thing and expects exactly the failure line of that change.
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import course  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LONG_LINE = "w1 w2 w3 w4 w5 w6 w7 w8 w9 w10 w11 w12 w13"


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = course.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CourseCase(unittest.TestCase):
    """A private copy of the fixture per test; `self.course` is the parsed course.json."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = tmp.name
        self.dir = os.path.join(self.base, "course")
        self.root = os.path.join(self.base, "course-root")
        shutil.copytree(FIXTURES / "course", self.dir)
        shutil.copytree(FIXTURES / "course-root", self.root)
        self.course = course.load(self.dir)

    def failures(self):
        return course.check(self.dir, self.course)

    def only(self, *expected):
        self.assertEqual(self.failures(), list(expected))

    def hop(self, hop_id):
        return next(h for h in self.course["hops"] if h["id"] == hop_id)

    def lesson(self, lesson_id):
        for block in self.course["blocks"]:
            for lesson in block["lessons"]:
                if lesson["id"] == lesson_id:
                    return lesson
        raise KeyError(lesson_id)


class LoadSaveCase(CourseCase):
    def test_load_reads_course_json(self):
        self.assertEqual(self.course["version"], 1)
        self.assertEqual([h["id"] for h in self.course["hops"]][0], "receive")

    def test_save_then_load_round_trips(self):
        self.course["title"] = "Changed"
        course.save(self.dir, self.course)
        self.assertEqual(course.load(self.dir), self.course)

    def test_save_leaves_no_temporary_file(self):
        course.save(self.dir, self.course)
        self.assertEqual(
            sorted(os.listdir(self.dir)), ["course.json", "lessons"]
        )

    def test_failed_save_keeps_the_old_file_and_cleans_up(self):
        before = Path(self.dir, "course.json").read_text(encoding="utf-8")
        self.course["title"] = "Changed"
        with mock.patch.object(course.os, "replace", side_effect=OSError("disk")):
            with self.assertRaises(OSError):
                course.save(self.dir, self.course)
        self.assertEqual(Path(self.dir, "course.json").read_text(encoding="utf-8"), before)
        self.assertEqual(sorted(os.listdir(self.dir)), ["course.json", "lessons"])

    def test_load_rejects_a_non_object(self):
        Path(self.dir, "course.json").write_text("[1]", encoding="utf-8")
        with self.assertRaises(ValueError):
            course.load(self.dir)


class CheckCase(CourseCase):
    def test_fixture_is_clean(self):
        self.only()
        code, out, _ = run_cli("check", self.dir)
        self.assertEqual((code, out), (0, "course: ok\n"))

    # schema

    def test_schema_missing_field(self):
        del self.course["question"]
        self.only("schema: question: missing")

    def test_schema_wrong_type(self):
        self.course["review"] = "no"
        self.only("schema: review: must be a boolean")

    def test_schema_version_must_be_one(self):
        self.course["version"] = 2
        self.only("schema: version: must be 1")

    def test_schema_state_enum(self):
        self.course["state"] = "started"
        self.only("schema: state: must be one of planned, approved, done")

    def test_schema_evidence_enum(self):
        self.hop("receive")["evidence"] = "guess"
        self.only("schema: hops[0].evidence: must be one of code, docs, inferred")

    def test_schema_status_enum(self):
        self.lesson("entry-reject")["status"] = "stuck"
        self.only(
            "schema: blocks[0].lessons[1].status: must be one of "
            "pending, building, done, failed, dropped"
        )

    def test_schema_source_kind_enum(self):
        self.course["sources"][0]["kind"] = "binary"
        self.only("schema: sources[0].kind: must be one of code, docs")

    def test_schema_cite_line_must_be_a_positive_integer(self):
        self.hop("receive")["cites"][0]["line"] = "4"
        self.only("schema: hops[0].cites[0].line: must be a positive integer")

    def test_schema_block_needs_a_lesson(self):
        self.course["blocks"].append({"id": "empty", "title": "Empty", "lessons": []})
        self.only("schema: blocks[2].lessons: must not be empty")

    def test_schema_reason_needed_for_failed(self):
        self.lesson("entry-reject")["status"] = "failed"
        self.only("schema: blocks[0].lessons[1].reason: needed for failed")

    def test_schema_reason_refused_for_pending(self):
        self.lesson("entry-reject")["reason"] = "late"
        self.only("schema: blocks[0].lessons[1].reason: must be empty for pending")

    def test_schema_id_pattern(self):
        self.hop("confirm")["id"] = "Confirm_"
        self.lesson("exit-deliver")["hops"] = ["deliver", "Confirm_"]
        self.only("schema: hops[4].id: must match [a-z0-9][a-z0-9-]*")

    def test_schema_garbage_does_not_crash(self):
        self.course["hops"] = ["x", None, {"id": 3, "cites": "y"}]
        self.course["blocks"] = "none"
        self.assertTrue(self.failures())

    # ids

    def test_duplicate_hop_id(self):
        self.course["hops"].append(dict(self.hop("confirm")))
        self.only("id: duplicate confirm")

    def test_duplicate_source_id(self):
        self.course["sources"].append(dict(self.course["sources"][0]))
        self.only("id: duplicate svc-a")

    def test_duplicate_block_id(self):
        self.course["blocks"].append(
            {"id": "entry", "title": "Again", "lessons": [
                {"id": "entry-again", "question": "What next?", "hops": ["confirm"],
                 "sources": ["svc-a"], "brief": "Read it.", "status": "pending", "reason": ""}
            ]}
        )
        self.only("id: duplicate entry")

    def test_duplicate_lesson_id_across_blocks(self):
        self.course["blocks"][1]["lessons"].append(dict(self.lesson("entry-reject")))
        self.only("id: duplicate entry-reject")

    # references

    def test_lesson_unknown_hop(self):
        self.lesson("entry-reject")["hops"].append("nowhere")
        self.only("lesson entry-reject: unknown hop nowhere")

    def test_lesson_unknown_source(self):
        self.lesson("entry-reject")["sources"].append("svc-z")
        self.only("lesson entry-reject: unknown source svc-z")

    def test_hop_in_no_lesson(self):
        self.lesson("exit-deliver")["hops"] = ["deliver"]
        self.only("hop confirm: in no lesson")

    def test_hop_of_a_dropped_lesson_still_counts(self):
        lesson = self.lesson("exit-deliver")
        lesson.update(status="dropped", reason="User dropped it.")
        self.only()

    def test_branch_is_a_later_hop(self):
        self.hop("reject")["branch"] = "deliver"
        self.only("hop reject: branch deliver is not an earlier hop")

    def test_branch_is_unknown(self):
        self.hop("reject")["branch"] = "nowhere"
        self.only("hop reject: branch nowhere is not an earlier hop")

    def test_branch_is_the_hop_itself(self):
        self.hop("reject")["branch"] = "reject"
        self.only("hop reject: branch reject is not an earlier hop")

    # cites

    def test_code_hop_needs_a_cite(self):
        self.hop("receive")["cites"] = []
        self.only("hop receive: code hop needs a cite")

    def test_docs_hop_needs_a_cite(self):
        self.hop("deliver")["cites"] = []
        self.only("hop deliver: docs hop needs a cite")

    def test_inferred_hop_has_a_cite(self):
        self.hop("confirm")["cites"] = [dict(self.hop("receive")["cites"][0])]
        self.only("hop confirm: inferred hop has a cite")

    def test_source_path_missing(self):
        self.course["sources"][1]["path"] = "docs-z"
        self.only(
            "source docs-b: path missing: %s" % os.path.join(self.root, "docs-z")
        )

    def test_root_may_be_absolute(self):
        self.course["root"] = self.root
        self.only()

    def test_cite_file_missing(self):
        self.hop("receive")["cites"][0]["path"] = "svc-a/Other.java"
        self.only(
            "cite receive#1: file missing: %s"
            % os.path.join(self.root, "svc-a/Other.java")
        )

    def test_cite_line_out_of_range(self):
        self.hop("receive")["cites"][0]["line"] = 99
        self.only("cite receive#1: line out of range (file has 13 lines)")

    def test_cite_snippet_not_on_the_line(self):
        self.hop("validate")["cites"][0]["line"] = 4
        self.only("cite validate#1: snippet not found on that line")

    def test_cite_snippet_too_long(self):
        path = os.path.join(self.root, "docs-b", "api.md")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(LONG_LINE + "\n")
        self.hop("deliver")["cites"][0].update(line=5, snippet=LONG_LINE)
        self.only("cite deliver#1: snippet has 13 words (max 12)")

    def test_second_cite_is_numbered(self):
        extra = dict(self.hop("receive")["cites"][0], line=5)
        self.hop("receive")["cites"].append(extra)
        self.only("cite receive#2: snippet not found on that line")

    def test_cite_snippet_matches_after_whitespace_normalization(self):
        self.hop("validate")["cites"][0]["snippet"] = "validator.validate(message);\n"
        self.only()

    # done lesson

    def test_done_lesson_needs_index_html(self):
        os.remove(os.path.join(self.dir, "lessons", "entry-receive", "index.html"))
        self.only("lesson entry-receive: done but lessons/entry-receive/index.html missing")

    # command line

    def test_cli_prints_failures_then_count(self):
        self.hop("receive")["cites"] = []
        self.hop("confirm")["cites"] = [dict(self.hop("validate")["cites"][0])]
        course.save(self.dir, self.course)
        code, out, _ = run_cli("check", self.dir)
        self.assertEqual(code, 1)
        self.assertEqual(
            out.splitlines(),
            [
                "hop receive: code hop needs a cite",
                "hop confirm: inferred hop has a cite",
                "course: 2 failures",
            ],
        )

    def test_cli_missing_course_json_exits_2(self):
        os.remove(os.path.join(self.dir, "course.json"))
        code, out, err = run_cli("check", self.dir)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("course.json", err)

    def test_cli_bad_json_exits_2(self):
        Path(self.dir, "course.json").write_text("{nope", encoding="utf-8")
        code, out, err = run_cli("check", self.dir)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("course.json", err)

    def test_cli_usage_error_exits_2(self):
        for argv in ([], ["check"], ["check", "a", "b"], ["bogus", self.dir]):
            with self.subTest(argv=argv):
                code, out, err = run_cli(*argv)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("usage:", err)

    def test_cli_runs_as_a_script(self):
        import subprocess

        script = Path(__file__).resolve().parent.parent / "scripts" / "course.py"
        result = subprocess.run(
            [sys.executable, "-B", str(script), "check", self.dir],
            capture_output=True, text=True,
        )
        self.assertEqual((result.returncode, result.stdout), (0, "course: ok\n"))


if __name__ == "__main__":
    unittest.main()
