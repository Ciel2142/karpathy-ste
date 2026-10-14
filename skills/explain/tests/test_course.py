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
import json
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


class ProseCase(CourseCase):
    BAD = "The service utilizes the queue."

    def prose(self):
        return [f for f in self.failures() if f.startswith("prose: ")]

    def test_prose_error_is_reported(self):
        self.hop("receive")["what"] = self.BAD
        self.only(
            'prose: hops[receive].what: E WORD  "utilizes" is not approved; use USE'
        )

    def test_prose_error_names_lesson_question_and_not_covered(self):
        self.lesson("entry-reject")["question"] = self.BAD
        self.course["not_covered"] = ["The admin screen is not on the path.", self.BAD]
        self.assertEqual(
            [f.split(": E ")[0] for f in self.prose()],
            ["prose: lessons[entry-reject].question", "prose: not_covered[1]"],
        )

    def test_prose_checks_every_field(self):
        self.course["title"] = self.BAD
        self.course["question"] = self.BAD
        self.hop("receive")["what"] = self.BAD
        self.course["blocks"][0]["title"] = self.BAD
        self.lesson("entry-receive")["question"] = self.BAD
        self.lesson("entry-reject")["brief"] = self.BAD
        self.course["not_covered"] = [self.BAD]
        self.assertEqual(
            [f.split(": E ")[0] for f in self.prose()],
            [
                "prose: title",
                "prose: question",
                "prose: hops[receive].what",
                "prose: blocks[entry].title",
                "prose: lessons[entry-receive].question",
                "prose: lessons[entry-reject].brief",
                "prose: not_covered[0]",
            ],
        )

    def test_prose_multiline_field_keeps_its_path(self):
        self.hop("validate")["what"] = "The service\nchecks the message\nand utilizes the queue."
        self.only('prose: hops[validate].what: E WORD  "utilizes" is not approved; use USE')

    def test_prose_empty_field_does_not_shift_paths(self):
        self.course["question"] = ""
        self.hop("receive")["what"] = self.BAD
        self.assertEqual(
            [f.split(": E ")[0] for f in self.prose()], ["prose: hops[receive].what"]
        )

    def test_prose_is_escaped_into_html(self):
        # unescaped, "<utilizes>" would read as a tag and hide the word from the linter
        self.course["question"] = "Use <utilizes> now."
        self.assertEqual(
            [f.split(": E ")[0] for f in self.prose()], ["prose: question"]
        )

    def test_prose_lint_missing_is_a_failure(self):
        with mock.patch.object(course, "_find_ste_lint", return_value=None):
            self.only("prose: ste_lint.py not found")


class StateCase(CourseCase):
    def cli(self, *argv):
        return run_cli(*argv[:1], self.dir, *argv[1:])

    def approve(self):
        code, out, err = self.cli("approve")
        self.assertEqual((code, out, err), (0, "", ""))
        self.course = course.load(self.dir)

    def state_of(self, lesson_id):
        return self.lesson(lesson_id)["status"]

    # approve

    def test_approve_sets_state_and_shape(self):
        self.approve()
        self.assertEqual(self.course["state"], "approved")
        self.assertEqual(self.course["approved_shape"], course.shape(self.course))

    def test_approve_refuses_dirty_plan(self):
        self.hop("receive")["cites"] = []
        course.save(self.dir, self.course)
        code, out, _ = self.cli("approve")
        self.assertEqual(code, 1)
        self.assertEqual(
            out.splitlines(),
            ["hop receive: code hop needs a cite", "course: 1 failures"],
        )
        reloaded = course.load(self.dir)
        self.assertEqual(reloaded["state"], "planned")
        self.assertNotIn("approved_shape", reloaded)

    def test_approve_after_a_shape_change_approves_the_new_shape(self):
        self.approve()
        self.lesson("entry-reject")["hops"] = ["reject", "validate"]
        course.save(self.dir, self.course)
        self.approve()
        self.assertEqual(self.course["approved_shape"], course.shape(self.course))

    def test_approve_refuses_a_done_course(self):
        self.course["state"] = "done"
        course.save(self.dir, self.course)
        code, out, err = self.cli("approve")
        self.assertEqual((code, out, err), (1, "", "approve: course already done\n"))

    # next

    def test_next_refuses_planned(self):
        code, out, err = self.cli("next")
        self.assertEqual((code, out, err), (1, "", "next: course not approved\n"))

    def test_next_lists_pending_and_building_in_plan_order(self):
        self.approve()
        self.lesson("exit-deliver")["status"] = "building"
        course.save(self.dir, self.course)
        code, out, _ = self.cli("next")
        self.assertEqual((code, out), (0, "entry-reject\nexit-deliver\n"))

    def test_next_limit(self):
        self.approve()
        code, out, _ = self.cli("next", "--limit", "1")
        self.assertEqual((code, out), (0, "entry-reject\n"))
        self.assertEqual(course.next_lessons(self.course, 1), ["entry-reject"])
        self.assertEqual(
            course.next_lessons(self.course, None), ["entry-reject", "exit-deliver"]
        )

    def test_next_limit_must_be_a_positive_integer(self):
        self.approve()
        for bad in ("0", "-1", "x"):
            with self.subTest(limit=bad):
                code, out, err = self.cli("next", "--limit", bad)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("usage:", err)

    # mark

    def test_mark_done_needs_index(self):
        code, out, err = self.cli("mark", "entry-reject", "done")
        self.assertEqual(
            (code, out, err),
            (1, "", "mark: done needs lessons/entry-reject/index.html\n"),
        )
        self.assertEqual(course.load(self.dir), self.course)
        lesson_dir = os.path.join(self.dir, "lessons", "entry-reject")
        os.makedirs(lesson_dir)
        Path(lesson_dir, "index.html").write_text("<html></html>", encoding="utf-8")
        self.assertEqual(self.cli("mark", "entry-reject", "done")[0], 0)
        self.assertEqual(
            self.lesson_status_on_disk("entry-reject"), "done"
        )

    def lesson_status_on_disk(self, lesson_id):
        self.course = course.load(self.dir)
        return self.state_of(lesson_id)

    def test_mark_failed_needs_reason(self):
        for status in ("failed", "dropped"):
            with self.subTest(status=status):
                code, out, err = self.cli("mark", "entry-reject", status)
                self.assertEqual(
                    (code, out, err), (1, "", "mark: %s needs --reason\n" % status)
                )
        self.assertEqual(self.lesson_status_on_disk("entry-reject"), "pending")

    def test_mark_failed_with_reason_is_saved(self):
        code, out, _ = self.cli("mark", "entry-reject", "failed", "--reason", "verify.sh: bpmn")
        self.assertEqual((code, out), (0, ""))
        lesson = course.load(self.dir)
        self.course = lesson
        self.assertEqual(self.state_of("entry-reject"), "failed")
        self.assertEqual(self.lesson("entry-reject")["reason"], "verify.sh: bpmn")

    def test_mark_reason_only_for_failed_or_dropped(self):
        for status in ("pending", "building", "done"):
            with self.subTest(status=status):
                code, out, err = self.cli("mark", "entry-receive", status, "--reason", "x")
                self.assertEqual(
                    (code, out, err), (1, "", "mark: --reason only for failed or dropped\n")
                )

    def test_mark_clears_reason_when_retrying(self):
        self.cli("mark", "entry-reject", "dropped", "--reason", "User dropped it.")
        self.assertEqual(self.cli("mark", "entry-reject", "pending")[0], 0)
        self.course = course.load(self.dir)
        self.assertEqual(self.lesson("entry-reject")["reason"], "")
        self.assertEqual(self.failures(), [])

    def test_mark_building_allows_an_existing_lesson_directory(self):
        lesson_dir = os.path.join(self.dir, "lessons", "entry-receive")
        self.assertTrue(os.path.isdir(lesson_dir))
        self.assertEqual(self.cli("mark", "entry-receive", "building")[0], 0)
        self.assertTrue(os.path.isdir(lesson_dir))

    def test_mark_unknown_lesson(self):
        code, out, err = self.cli("mark", "nowhere", "pending")
        self.assertEqual((code, out, err), (1, "", "mark: unknown lesson nowhere\n"))

    def test_mark_usage_errors(self):
        for argv in (
            ["mark", self.dir, "entry-reject"],
            ["mark", self.dir, "entry-reject", "stuck"],
            ["mark", self.dir, "entry-reject", "failed", "--reason"],
            ["mark", self.dir, "entry-reject", "failed", "--why", "x"],
        ):
            with self.subTest(argv=argv):
                code, out, err = run_cli(*argv)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("usage:", err)

    # reopen

    def test_reopen_resets_failed_only(self):
        self.lesson("entry-reject").update(status="failed", reason="timeout")
        self.lesson("exit-deliver").update(status="dropped", reason="User dropped it.")
        course.save(self.dir, self.course)
        code, out, _ = self.cli("reopen")
        self.assertEqual((code, out), (0, "entry-reject\n"))
        self.course = course.load(self.dir)
        self.assertEqual(self.state_of("entry-reject"), "pending")
        self.assertEqual(self.lesson("entry-reject")["reason"], "")
        self.assertEqual(self.state_of("exit-deliver"), "dropped")
        self.assertEqual(self.state_of("entry-receive"), "done")

    def test_reopen_without_failed_changes_nothing(self):
        before = Path(self.dir, "course.json").read_text(encoding="utf-8")
        self.assertEqual(self.cli("reopen"), (0, "", ""))
        self.assertEqual(Path(self.dir, "course.json").read_text(encoding="utf-8"), before)

    def test_reopen_done_course_returns_to_approved(self):
        self.course["state"] = "done"
        self.lesson("exit-deliver").update(status="failed", reason="timeout")
        course.save(self.dir, self.course)
        code, out, _ = self.cli("reopen")
        self.assertEqual((code, out), (0, "exit-deliver\n"))
        self.assertEqual(course.load(self.dir)["state"], "approved")

    def test_reopen_done_course_without_failed_stays_done(self):
        self.course["state"] = "done"
        course.save(self.dir, self.course)
        self.assertEqual(self.cli("reopen")[0], 0)
        self.assertEqual(course.load(self.dir)["state"], "done")

    # shape

    def test_shape_ignores_prose_and_cites(self):
        before = course.shape(self.course)
        self.course["title"] = "Other"
        self.course["question"] = "Other?"
        self.course["not_covered"] = []
        self.hop("receive")["what"] = "Other."
        self.hop("receive")["from"] = "elsewhere"
        self.hop("receive")["evidence"] = "inferred"
        self.hop("receive")["cites"] = []
        self.course["blocks"][0]["title"] = "Other"
        self.lesson("entry-reject").update(question="Other?", brief="Other.", status="failed")
        self.course["sources"][0].update(commit="abc1234", dirty=True)
        self.assertEqual(course.shape(self.course), before)

    def test_shape_changes_with_the_structure(self):
        base = course.shape(self.course)
        self.assertRegex(base, r"^[0-9a-f]{64}$")
        edits = {
            "branch": lambda c: c["hops"][2].update(branch=None),
            "hop order": lambda c: c["hops"].reverse(),
            "lesson hops": lambda c: c["blocks"][0]["lessons"][1].update(hops=["reject", "validate"]),
            "lesson sources": lambda c: c["blocks"][0]["lessons"][1].update(sources=[]),
            "lesson id": lambda c: c["blocks"][0]["lessons"][1].update(id="entry-bad"),
            "block id": lambda c: c["blocks"][0].update(id="entrance"),
            "block order": lambda c: c["blocks"].reverse(),
            "hop id": lambda c: c["hops"][4].update(id="ack"),
        }
        for name, edit in edits.items():
            with self.subTest(edit=name):
                other = json.loads(json.dumps(self.course))
                edit(other)
                self.assertNotEqual(course.shape(other), base)

    def test_shape_survives_garbage(self):
        self.course["hops"] = ["x", None, {"id": 3}]
        self.course["blocks"] = "none"
        self.assertRegex(course.shape(self.course), r"^[0-9a-f]{64}$")

    def test_shape_change_after_approval_resets_to_planned(self):
        self.approve()
        self.lesson("entry-reject")["hops"] = ["reject", "validate"]
        course.save(self.dir, self.course)
        code, out, _ = run_cli("check", self.dir)
        self.assertEqual(code, 1)
        self.assertEqual(
            out.splitlines(),
            [
                "state: plan changed after approval; run summary and approve again",
                "course: 1 failures",
            ],
        )
        self.assertEqual(course.load(self.dir)["state"], "planned")
        # the new state is saved, so the next check reports the plain plan
        self.assertEqual(run_cli("check", self.dir)[:2], (0, "course: ok\n"))

    def test_check_function_changes_no_state(self):
        self.approve()
        self.lesson("entry-reject")["hops"] = ["reject", "validate"]
        self.assertEqual(
            self.failures(),
            ["state: plan changed after approval; run summary and approve again"],
        )
        self.assertEqual(self.course["state"], "approved")

    def test_prose_fix_after_approval_keeps_approved(self):
        self.approve()
        self.hop("receive")["what"] = "The service gets the message from the queue."
        self.hop("receive")["cites"][0]["snippet"] = "@Listener(queue = \"IN_QUEUE\")"
        course.save(self.dir, self.course)
        self.assertEqual(run_cli("check", self.dir)[:2], (0, "course: ok\n"))
        self.assertEqual(course.load(self.dir)["state"], "approved")


class SummaryCase(CourseCase):
    """`course.py summary`: the plan as the user reads it at the approval stop."""

    def summary(self):
        code, out, err = run_cli("summary", self.dir)
        self.assertEqual((code, err), (0, ""))
        return out

    def git(self, *args, cwd=None):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        import subprocess

        return subprocess.run(
            ["git", "-C", cwd or self.root, *args], check=True, env=env,
            capture_output=True, text=True,
        ).stdout.strip()

    def make_repo(self):
        """Turn the fake root into a git repository with one commit; return its short hash."""
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")
        return self.git("rev-parse", "--short", "HEAD")

    def test_summary_lists_every_lesson_and_hop(self):
        out = self.summary()
        for hop in self.course["hops"]:
            self.assertIn(hop["from"] + " \u2192 " + hop["to"], out)
        for lesson in (l for b in self.course["blocks"] for l in b["lessons"]):
            self.assertIn(lesson["id"], out)
            self.assertIn(lesson["question"], out)
        self.assertIn(self.course["title"], out)
        self.assertIn(self.course["question"], out)
        self.assertIn("svc-a  code  named", out)
        self.assertIn("docs-b  docs  discovered", out)
        self.assertIn("This service takes the message and checks it.", out)
        self.assertIn("not covered: The admin screen", out)
        self.assertNotIn("moved:", out)
        self.assertNotIn("\x1b", out)
        for line in out.splitlines():
            self.assertLessEqual(len(line), 100, line)

    def test_summary_lesson_line_has_id_question_hops_status(self):
        out = self.summary()
        self.assertIn(
            "entry-receive  How does the service take a message?  [receive, validate]  done", out
        )
        self.assertIn("entry-reject  What happens to a bad message?  [reject]  pending", out)

    def test_summary_indents_a_failure_hop_under_its_branch_hop(self):
        lines = self.summary().splitlines()
        by_hop = {}
        for line in lines:
            for hop in ("receive", "validate", "reject", "deliver", "confirm"):
                if line.strip().startswith(hop + "  "):
                    by_hop[hop] = line
        indent = {hop: len(line) - len(line.lstrip()) for hop, line in by_hop.items()}
        self.assertEqual(sorted(by_hop), ["confirm", "deliver", "receive", "reject", "validate"])
        self.assertEqual(indent["receive"], indent["validate"])
        self.assertGreater(indent["reject"], indent["validate"])
        self.assertEqual(lines.index(by_hop["reject"]), lines.index(by_hop["validate"]) + 1)
        self.assertLess(lines.index(by_hop["reject"]), lines.index(by_hop["deliver"]))
        self.assertIn("(code)", by_hop["receive"])
        self.assertIn("(inferred)", by_hop["confirm"])

    def test_summary_estimates_the_remaining_build_time(self):
        # one of three lessons is done: 2 x 30 min / 3 = 20 min, up to the next half hour
        self.assertIn("lessons: 3 (2 to build), about 0.5 h at 3 at once", self.summary())
        self.lesson("entry-receive")["status"] = "pending"
        course.save(self.dir, self.course)  # 3 x 30 / 3 = 30 min
        self.assertIn("lessons: 3 (3 to build), about 0.5 h at 3 at once", self.summary())
        self.course["blocks"][0]["lessons"].append(
            dict(self.lesson("entry-reject"), id="entry-extra")
        )
        course.save(self.dir, self.course)  # 4 x 30 / 3 = 40 min -> 1 h
        self.assertIn("lessons: 4 (4 to build), about 1 h at 3 at once", self.summary())

    def test_summary_does_not_count_dropped_lessons_as_to_build(self):
        self.lesson("entry-reject").update(status="dropped", reason="User asked.")
        course.save(self.dir, self.course)
        out = self.summary()
        self.assertIn("lessons: 3 (1 to build), about 0.5 h at 3 at once", out)
        self.assertIn("entry-reject  What happens to a bad message?  [reject]  dropped", out)
        self.assertIn("User asked.", out)

    def test_summary_marks_moved_source(self):
        head = self.make_repo()
        for source in self.course["sources"]:
            source["commit"] = head
        self.course["sources"][0]["commit"] = "0000000"
        course.save(self.dir, self.course)
        out = self.summary()
        self.assertIn("moved: 0000000 -> %s" % head, out)
        self.assertEqual(out.count("moved:"), 1)

    def test_summary_marks_dirty_only_when_the_flag_differs(self):
        head = self.make_repo()
        for source in self.course["sources"]:
            source["commit"] = head
        course.save(self.dir, self.course)
        self.assertNotIn("moved:", self.summary())
        Path(self.root, "svc-a", "Handler.java").write_text("changed\n", encoding="utf-8")
        self.assertEqual(self.summary().count("moved: dirty"), 2)

    def test_summary_uses_the_directory_of_a_file_source(self):
        head = self.make_repo()
        self.course["sources"][0]["path"] = "svc-a/Handler.java"
        self.course["sources"][0]["commit"] = "0000000"
        self.course["sources"][1]["commit"] = head
        course.save(self.dir, self.course)
        self.assertIn("moved: 0000000 -> %s" % head, self.summary())

    def test_summary_source_outside_git_shows_none(self):
        self.course["sources"][0]["commit"] = "abc1234"
        course.save(self.dir, self.course)
        self.assertIn("moved: abc1234 -> none", self.summary())

    def test_git_state_outside_git_is_none_and_clean(self):
        self.assertEqual(course.git_state(self.root), ("none", False))
        self.assertEqual(course.git_state(os.path.join(self.root, "missing")), ("none", False))

    def test_git_state_reads_commit_and_dirty(self):
        head = self.make_repo()
        self.assertEqual(course.git_state(self.root), (head, False))
        Path(self.root, "new.txt").write_text("x", encoding="utf-8")
        self.assertEqual(course.git_state(self.root), (head, True))

    def test_summary_changes_no_state_and_works_when_planned_or_done(self):
        for state in ("planned", "approved", "done"):
            self.course["state"] = state
            course.save(self.dir, self.course)
            before = Path(self.dir, "course.json").read_bytes()
            self.assertIn(self.course["title"], self.summary())
            self.assertEqual(Path(self.dir, "course.json").read_bytes(), before)

    def test_summary_missing_course_json_exits_2(self):
        os.remove(os.path.join(self.dir, "course.json"))
        code, out, err = run_cli("summary", self.dir)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("course.json", err)

    def test_summary_usage_error_exits_2(self):
        for argv in (["summary"], ["summary", "a", "b"]):
            code, out, err = run_cli(*argv)
            self.assertEqual((code, out), (2, ""))
            self.assertIn("usage:", err)

    def test_summary_wraps_long_text_within_100_characters(self):
        self.course["sources"][0]["why"] = " ".join(["word"] * 60)
        self.lesson("entry-reject")["question"] = " ".join(["ask"] * 60)
        self.course["not_covered"] = [" ".join(["gap"] * 60)]
        course.save(self.dir, self.course)
        out = self.summary()
        self.assertIn("ask", out)
        for line in out.splitlines():
            self.assertLessEqual(len(line), 100, line)


if __name__ == "__main__":
    unittest.main()
