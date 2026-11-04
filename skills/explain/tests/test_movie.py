"""Tests for movie.py: load, atomic save, the plan check of `movie.json`, the bridges and the
stitch (spec 4.2, 4.4, 4.5, 6).

Each test copies `tests/fixtures/movie/` to a temporary directory, changes one thing and
expects the failure line of that change. The fixture's `provenance.root` is `.`, so cites
resolve under the copied directory. `tests/fixtures/movie/probe/` holds ffprobe `-of json`
outputs for the stitch tests; it is not copied, as a movie directory holds no probe.
"""

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import movie  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CHECK_SCENE = FIXTURES.parent.parent / "video" / "check_scene.py"
PROBES = FIXTURES / "movie" / "probe"
PARTS = ["chapters/members/video.mp4", "bridges/1/video.mp4", "chapters/trigger/video.mp4",
         "bridges/2/video.mp4", "chapters/split/video.mp4", "bridges/3/video.mp4",
         "chapters/pause/video.mp4"]
CONCAT_OUT = "build/video.part.mp4"


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
        shutil.copytree(FIXTURES / "movie", self.dir, ignore=shutil.ignore_patterns("probe"))
        self.movie = movie.load(self.dir)

    def failures(self):
        return movie.check(self.dir, self.movie)

    def chapter(self, ident):
        return next(c for c in self.movie["chapters"] if c["id"] == ident)


class CheckCase(MovieCase):
    def test_good_plan_prints_plan_ok(self):
        code, out, err = run_cli("check", self.dir)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines()[-1], "plan: ok (3 questions, 4 chapters, 264..285 s with bridges)")

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
        self.assertEqual(self.failures(),
                         ["schema: seconds sum 120, 144..165 s with bridges (min 240, max 900)"])

    def test_seconds_sum_with_the_longest_bridges_over_the_max(self):
        # six chapters of 150 s sum to 900, the max, but five bridges of up to 15 s make 975
        for n in (1, 2):
            self.movie["chapters"].append(dict(self.chapter("pause"), id="extra-%d" % n))
        for chapter in self.movie["chapters"]:
            chapter["seconds"] = 150
        self.assertEqual(self.failures(),
                         ["schema: seconds sum 900, 940..975 s with bridges (min 240, max 900)"])

    def test_seconds_not_an_integer(self):
        self.chapter("split")["seconds"] = "60"
        self.assertEqual(
            self.failures(),
            ["chapter split: seconds must be an integer from 30 to 150"])

    # a question text, an answer and a chapter question hold at most 20 words (two sentences here,
    # so that the prose check passes them and the cap alone refuses them)

    def test_a_question_text_over_20_words(self):
        self.movie["questions"][0]["text"] = ("Who joins the group and who leaves it? Which consumer"
                                              " then keeps which of the six partitions of the old topic?")
        self.assertEqual(self.failures(), ["question q-1: text has 21 words (max 20)"])

    def test_an_answer_over_20_words(self):
        self.movie["questions"][0]["answer"] = ("A member joins or leaves. A member misses its heartbeat."
                                                " The coordinator then stops the work of each member of"
                                                " the group.")
        self.assertEqual(self.failures(), ["question q-1: answer has 22 words (max 20)"])

    def test_a_chapter_question_over_20_words(self):
        self.chapter("members")["question"] = ("Which consumers are in the group now? Which of them"
                                               " reads which of the six partitions of the old topic today?")
        self.assertEqual(self.failures(), ["chapter members: question has 21 words (max 20)"])

    def test_20_words_pass(self):
        self.movie["questions"][0]["text"] = ("Who joins the group and who leaves it? Which consumer"
                                              " then keeps which of the six partitions of the topic?")
        self.assertEqual(self.failures(), [])

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

    def test_a_url_cite_needs_no_line(self):
        # red: check asks a URL cite for a line, or runs the file rules of cite_check on it
        self.movie["subject"]["kind"] = "file"
        for question in self.movie["questions"]:
            question["cites"] = [{"path": "https://kafka.apache.org/documentation/",
                                  "snippet": "consumer group"}]
        self.assertEqual(self.failures(), [])

    def test_a_file_cite_without_a_line(self):
        self.movie["questions"][0]["cites"] = [{"path": "notes.txt", "snippet": "alpha beta"}]
        self.assertEqual(self.failures(), ["question q-1: cite 1 needs path, line and snippet"])

    def test_a_url_cite_without_a_snippet(self):
        self.movie["questions"][0]["cites"] = [{"path": "https://kafka.apache.org/", "snippet": " "}]
        self.assertEqual(self.failures(), ["question q-1: cite 1 needs path and snippet"])

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

    def test_lang_must_be_en_or_ru(self):
        self.movie["lang"] = "de"
        self.assertEqual(self.failures(), ["schema: lang must be en or ru"])

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
        self.assertEqual(run_cli("bridges")[0], 2)


class ChapterScriptCase(MovieCase):
    def script_path(self):
        return os.path.join(self.dir, "chapters", "members", "script.json")

    def edit_script(self, change):
        with open(self.script_path(), encoding="utf-8") as handle:
            script = json.load(handle)
        change(script)
        with open(self.script_path(), "w", encoding="utf-8") as handle:
            json.dump(script, handle)

    def test_a_chapter_script_with_ask_and_answer_passes(self):
        code, out, err = run_cli("check", self.dir)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines()[-1], "plan: ok (3 questions, 4 chapters, 264..285 s with bridges)")

    def test_first_scene_must_be_ask(self):
        self.edit_script(lambda s: s["scenes"][0].update(id="intro"))
        self.assertEqual(self.failures(), ["chapter members: first scene is intro, not ask"])

    def test_last_scene_must_be_answer(self):
        self.edit_script(lambda s: s["scenes"][-1].update(id="body"))
        self.assertEqual(self.failures(), ["chapter members: last scene is body, not answer"])

    def test_script_title_must_match(self):
        self.edit_script(lambda s: s.update(title="X"))
        self.assertEqual(self.failures(),
                         ['chapter members: script title "X" differs from "The members"'])

    def test_script_format_must_be_film(self):
        self.edit_script(lambda s: s.update(format="clip"))
        self.assertEqual(self.failures(), ["chapter members: format is clip, not film"])

    def test_script_root_must_match(self):
        # red: the roots are not compared, or compared as written rather than resolved
        self.edit_script(lambda s: s["provenance"].update(root="/elsewhere"))
        self.assertEqual(self.failures(), ["chapter members: root /elsewhere differs from the"
                                           " movie's %s" % os.path.abspath(self.dir)])
        self.edit_script(lambda s: s["provenance"].update(root=os.path.abspath(self.dir) + "/"))
        self.assertEqual(self.failures(), [])

    def test_script_lang_must_match(self):
        self.edit_script(lambda s: s.update(lang="ru"))
        self.assertEqual(self.failures(), ["chapter members: lang ru differs from the movie's en"])
        self.edit_script(lambda s: s.pop("lang"))  # a script without lang is en, as narrate.py reads it
        self.assertEqual(self.failures(), [])

    def test_script_failures_count_in_the_plan_line(self):
        self.edit_script(lambda s: s.update(format="clip", title="X"))
        code, out, _ = run_cli("check", self.dir)
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines()[-1], "plan: 2 failures")

    def test_status_lists_each_chapter_and_strays(self):
        os.makedirs(os.path.join(self.dir, "chapters", "old"))
        self.chapter("trigger").update(status="failed", reason="render timed out")
        movie.save(self.dir, self.movie)
        code, out, err = run_cli("status", self.dir)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines(), [
            "chapter: members pending", "chapter: trigger failed render timed out",
            "chapter: split pending", "chapter: pause pending",
            "stray: chapters/old", "state: planned"])

    def test_status_on_unreadable_movie_exits_2(self):
        with open(os.path.join(self.dir, "movie.json"), "w", encoding="utf-8") as handle:
            handle.write("{not json")
        code, out, _ = run_cli("status", self.dir)
        self.assertEqual((code, out), (2, ""))


def check_scene(directory):
    """check_scene.py on the scene directory `directory`, as test_check_scene.py runs it."""
    return subprocess.run([sys.executable, "-B", str(CHECK_SCENE), str(directory)],
                          capture_output=True, text=True, timeout=60)


class BridgesCase(MovieCase):
    def bridges(self):
        """`movie.bridges` on the fixture copy: (the ids it returns, what it printed)."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ids = movie.bridges(self.dir, self.movie)
        return ids, out.getvalue()

    def script(self, n):
        with open(os.path.join(self.dir, "bridges", n, "script.json"), encoding="utf-8") as handle:
            return json.load(handle)

    def film(self, n):
        return Path(self.dir, "bridges", n, "scene", "Film.tsx").read_text(encoding="utf-8")

    def labels(self, n):
        """{name: decoded text} of the label constants DONE, SOFAR and NEXT of bridge `n`'s scene."""
        found = re.findall(r'^const (DONE|SOFAR|NEXT) = ("[^"\n]*");$', self.film(n), re.MULTILINE)
        return {name: json.loads(literal) for name, literal in found}

    def scene_ok(self, n):
        done = check_scene(Path(self.dir, "bridges", n, "scene"))
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""), "bridge %s" % n)

    def files(self):
        """{path under bridges/: bytes} of every file the bridges wrote."""
        root = Path(self.dir, "bridges")
        return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}

    def test_bridges_writes_one_per_gap(self):
        self.assertEqual(self.bridges(), (["1", "2", "3"], "bridges: ok (3)\n"))
        self.assertEqual(sorted(self.files()), [
            "%s/%s" % (n, name) for n in ("1", "2", "3") for name in ("scene/Film.tsx", "script.json")])
        script = self.script("2")
        self.assertEqual(script["format"], "clip")
        self.assertEqual(script["title"], "Bridge 2")
        self.assertEqual([scene["id"] for scene in script["scenes"]], ["done", "sofar", "next"])
        self.assertNotIn('"cites"', json.dumps(script))
        narration = {scene["id"]: scene["narration"] for scene in script["scenes"]}
        # trigger answers q-1 first: done is its text and sofar its answer
        self.assertIn(self.movie["questions"][0]["text"], narration["done"])
        self.assertIn(self.movie["questions"][0]["answer"], narration["sofar"])
        self.assertIn(self.chapter("split")["question"], narration["next"])
        self.assertEqual(script["subject"], self.movie["subject"])
        self.assertEqual(script["provenance"]["root"], os.path.abspath(self.dir))
        self.assertEqual(script["provenance"]["date"], "2026-11-03")
        self.assertEqual(script["provenance"]["not_covered"], "none")

    def test_bridges_copies_pronounce_for_ru(self):
        self.movie.update(lang="ru", pronounce={"Kafka": "Кафка"})
        self.bridges()
        for n in ("1", "2", "3"):
            script = self.script(n)
            self.assertEqual((script["lang"], script["pronounce"]), ("ru", {"Kafka": "Кафка"}))
        self.movie.update(lang="en", pronounce={})
        self.bridges()
        for n in ("1", "2", "3"):
            script = self.script(n)
            self.assertEqual(script["lang"], "en")
            self.assertNotIn("pronounce", script)

    def test_a_bridge_subject_is_a_topic(self):
        # a bridge cites nothing, and the timeline check allows no cites only for a topic
        self.movie["subject"] = {"text": "skills/explain", "kind": "directory"}
        self.bridges()
        for n in ("1", "2", "3"):
            self.assertEqual(self.script(n)["subject"], {"text": "skills/explain", "kind": "topic"})

    def test_bridges_is_idempotent(self):
        self.assertEqual(run_cli("bridges", self.dir), (0, "bridges: ok (3)\n", ""))
        first = self.files()
        self.assertEqual(run_cli("bridges", self.dir), (0, "bridges: ok (3)\n", ""))
        self.assertEqual(self.files(), first)

    def test_bridge_scene_passes_check_scene(self):
        self.bridges()
        for directory in (Path(self.dir, "bridges", "1", "scene"), movie.BRIDGE_TEMPLATE_SCENE):
            done = check_scene(directory)
            self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""), directory)
        self.assertNotIn("{{", self.film("1"))
        self.assertEqual(self.labels("1"), {  # members answers q-1 first
            "DONE": self.movie["questions"][0]["text"],
            "SOFAR": self.movie["questions"][0]["answer"],
            "NEXT": self.chapter("trigger")["question"]})

    def test_bridge_label_escapes_quotes(self):
        question = 'Who is a "member" of the group a\\b?'
        self.movie["questions"][0]["text"] = question  # members answers q-1 first
        self.bridges()
        self.assertEqual(self.labels("1")["DONE"], question)
        self.scene_ok("1")

    def test_bridge_labels_never_hold_a_refused_token(self):
        # each label holds a token or an import source of check_scene.py when written as it reads
        self.movie["questions"][0]["text"] = "Can the group treat an event as any other message?"
        self.movie["questions"][1]["text"] = "Does it read 'x' from 'y' as an <image or a <mask?"
        self.chapter("trigger")["question"] = "Where does the offset come from"
        self.chapter("split")["question"] = "What does https://kafka.apache.org say?"
        self.chapter("pause")["question"] = \
            "Is it an href, a clipPath, an <image, @ts-nocheck or 'x' from 'y' or require( import"
        self.movie["questions"][0]["answer"] = "The rule: any member reads it, as unknown \U0001F600."
        self.bridges()
        chapters = self.movie["chapters"]
        questions = {question["id"]: question for question in self.movie["questions"]}
        for n in (1, 2, 3):
            self.scene_ok(str(n))
            first = questions[chapters[n - 1]["answers"][0]]
            self.assertEqual(self.labels(str(n)), {
                "DONE": first["text"], "SOFAR": first["answer"], "NEXT": chapters[n]["question"]})

    def test_done_is_the_first_answered_question(self):
        # red: done is the chapter's question, or the text of a question other than answers[0]
        self.chapter("members")["answers"] = ["q-3", "q-1"]
        self.bridges()
        q3 = self.movie["questions"][2]
        self.assertEqual(self.labels("1"), {"DONE": q3["text"], "SOFAR": q3["answer"],
                                            "NEXT": self.chapter("trigger")["question"]})
        narration = {scene["id"]: scene["narration"] for scene in self.script("1")["scenes"]}
        self.assertEqual((narration["done"], narration["sofar"]), (q3["text"], q3["answer"]))

    def test_bridges_refuses_a_plan_that_fails_check(self):
        self.chapter("pause")["answers"] = ["q-1", "q-2", "q-3"]
        movie.save(self.dir, self.movie)
        self.assertEqual(run_cli("bridges", self.dir), (1, "chapter pause: answers has 3 entries"
                                                          " (max 2)\nplan: 1 failures\n", ""))
        self.assertFalse(os.path.exists(os.path.join(self.dir, "bridges")))


def ffprobe_output(name, duration, kinds=("video", "audio")):
    """The ffprobe `-of json` output of `probe/<name>` with its duration set to `duration` and
    only the streams whose codec_type is in `kinds`."""
    data = json.loads((PROBES / name).read_text(encoding="utf-8"))
    data["format"]["duration"] = "%.6f" % duration
    data["streams"] = [stream for stream in data["streams"] if stream["codec_type"] in kinds]
    return json.dumps(data)


class StitchCase(MovieCase):
    """`stitch` with a stand-in Remotion CLI in a private workspace; ffprobe and ffmpeg go
    through a fake `movie.run`, so no test runs a subprocess."""

    def setUp(self):
        super().setUp()
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        cli = Path(workspace.name, "app", "node_modules", ".bin", "remotion")
        cli.parent.mkdir(parents=True)
        cli.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
        cli.chmod(0o755)
        env = mock.patch.dict(os.environ, {"EXPLAIN_VIDEO_WORKSPACE": workspace.name})
        env.start()
        self.addCleanup(env.stop)

    def build_all(self):
        """Every chapter `built` and every part an empty `video.mp4`."""
        for chapter in self.movie["chapters"]:
            chapter["status"] = "built"
        movie.save(self.dir, self.movie)
        for name in PARTS:
            path = Path(self.dir, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"")

    @staticmethod
    def probes(durations):
        """{path relative to the movie dir: ffprobe output}: each part of PARTS with its duration
        at 48000 Hz, and the concat output with their sum."""
        probes = {name: ffprobe_output("aac-48000.json", seconds)
                  for name, seconds in zip(PARTS, durations)}
        probes[CONCAT_OUT] = ffprobe_output("aac-48000.json", sum(durations))
        return probes

    def stitch(self, probes, ffmpeg_exit=0):
        """`movie.py stitch` on the copy: (exit code, stdout, stderr). A fake ffprobe answers from
        `probes` by the path it is given; a fake ffmpeg exits `ffmpeg_exit` and, on 0, writes
        an empty output file."""
        def fake_run(argv, cwd):
            if "ffmpeg" in argv:
                if ffmpeg_exit == 0:
                    Path(argv[-1]).write_bytes(b"")
                return ffmpeg_exit, ""
            return 0, probes[os.path.relpath(argv[-1], self.dir)]
        with mock.patch("movie.run", side_effect=fake_run):
            return run_cli("stitch", self.dir)

    def exists(self, name):
        return os.path.exists(os.path.join(self.dir, name))

    def test_concat_list_escapes_a_quote(self):
        self.assertEqual(movie.concat_list(["/a/it's.mp4"]), "file '/a/it'\\''s.mp4'\n")

    def test_parts_order_is_chapter_bridge_chapter(self):
        self.build_all()
        self.assertEqual(movie.parts(self.dir, self.movie), PARTS)

    def test_parts_refuses_a_missing_mp4(self):
        self.build_all()
        os.remove(os.path.join(self.dir, "chapters", "split", "video.mp4"))
        self.assertEqual(self.stitch({}),
                         (1, "parts: FAIL chapters/split/video.mp4 missing\n", ""))
        self.assertFalse(self.exists("build"))

    def test_parts_refuses_a_pending_chapter(self):
        self.build_all()
        self.chapter("trigger")["status"] = "pending"
        movie.save(self.dir, self.movie)
        self.assertEqual(self.stitch({}),
                         (1, "parts: FAIL chapter trigger is pending, not built\n", ""))
        self.assertFalse(self.exists("build"))

    def test_parts_refuses_a_rate_mismatch(self):
        self.build_all()
        probes = self.probes([60, 10, 60, 10, 60, 10, 60])
        probes["bridges/1/video.mp4"] = ffprobe_output("aac-22050.json", 10)
        self.assertEqual(self.stitch(probes),
                         (1, "parts: FAIL bridges/1/video.mp4 audio rate differs\n", ""))
        self.assertFalse(self.exists("build"))
        self.assertFalse(self.exists("video.mp4"))

    def test_probe_reads_the_fields(self):
        cli = movie.remotion_cli(os.environ["EXPLAIN_VIDEO_WORKSPACE"])
        output = (PROBES / "aac-48000.json").read_text(encoding="utf-8")
        with mock.patch("movie.run", return_value=(0, output)):
            found = movie.probe(cli, "/m/video.mp4")
        self.assertEqual(found, {"vcodec": "h264", "acodec": "aac", "width": 1280, "height": 720,
                                 "fps": "30/1", "rate": 48000, "duration": 41.344})

    def test_stitch_writes_chapters_json_starts(self):
        self.build_all()
        code, out, err = self.stitch(self.probes([60, 10, 60, 10, 60, 10, 60]))
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines(), ["parts: ok (7)", "concat: ok (270.0 s)",
                                            "container: ok (270.0 s)",
                                            "transcript: ok (4 chapters)",
                                            "hub: ok index.html",
                                            "length: ok (270.0 s)"])
        chapters = json.loads(Path(self.dir, "chapters.json").read_text(encoding="utf-8"))
        self.assertEqual(chapters, [
            {"id": "members", "title": "The members", "start": 0.0},
            {"id": "trigger", "title": "The trigger", "start": 70.0},
            {"id": "split", "title": "The new split", "start": 140.0},
            {"id": "pause", "title": "The pause", "start": 210.0}])
        self.assertEqual(Path(self.dir, "build", "concat.txt").read_text(encoding="utf-8"),
                         "".join("file '%s'\n" % os.path.join(self.dir, name) for name in PARTS))
        self.assertTrue(self.exists("video.mp4"))
        self.assertFalse(self.exists(CONCAT_OUT))

    def test_chapter_starts_are_the_plain_sums(self):
        # real durations are AAC-frame multiples with six decimals: a start is their sum, unrounded
        self.build_all()
        durations = [61.344, 8.021333] * 3 + [61.344]
        code, _, _ = self.stitch(self.probes(durations))
        self.assertEqual(code, 0)
        text = Path(self.dir, "chapters.json").read_text(encoding="utf-8")
        self.assertIn('"start": 0.0', text)
        starts = [chapter["start"] for chapter in json.loads(text)]
        self.assertEqual(starts, [0.0] + [sum(durations[:index]) for index in (2, 4, 6)])
        self.assertEqual(starts[1], 61.344 + 8.021333)

    def test_stitch_reports_a_short_movie(self):
        self.build_all()
        code, out, _ = self.stitch(self.probes([5] * 7))
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines()[-1], "length: FAIL 35.0 s (min 240, max 900)")
        self.assertTrue(self.exists("video.mp4"))

    def test_concat_reports_an_ffmpeg_exit_and_keeps_the_old_video(self):
        self.build_all()
        Path(self.dir, "video.mp4").write_bytes(b"old")
        code, out, _ = self.stitch(self.probes([60, 10, 60, 10, 60, 10, 60]), ffmpeg_exit=1)
        self.assertEqual((code, out.splitlines()),
                         (1, ["parts: ok (7)", "concat: FAIL ffmpeg exit 1"]))
        self.assertEqual(Path(self.dir, "video.mp4").read_bytes(), b"old")

    def test_container_refuses_a_missing_audio_stream(self):
        self.build_all()
        probes = self.probes([60, 10, 60, 10, 60, 10, 60])
        probes[CONCAT_OUT] = ffprobe_output("aac-48000.json", 270, kinds=("video",))
        code, out, _ = self.stitch(probes)
        self.assertEqual((code, out.splitlines()[-1]),
                         (1, "container: FAIL streams video (expected one video and one audio)"))
        self.assertFalse(self.exists("video.mp4"))

    def test_container_refuses_a_length_off_the_sum(self):
        self.build_all()
        probes = self.probes([60, 10, 60, 10, 60, 10, 60])
        probes[CONCAT_OUT] = ffprobe_output("aac-48000.json", 270.6)
        code, out, _ = self.stitch(probes)
        self.assertEqual((code, out.splitlines()[-1]),
                         (1, "container: FAIL duration 270.6 s, expected 270.0 s"))
        self.assertFalse(self.exists("video.mp4"))

    def test_no_cli_is_a_usage_error(self):
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        path = os.path.join(empty.name, "app", "node_modules", ".bin", "remotion")
        with mock.patch.dict(os.environ, {"EXPLAIN_VIDEO_WORKSPACE": empty.name}):
            self.assertEqual(run_cli("stitch", self.dir), (2, "", "no Remotion CLI at %s\n" % path))

    # the viewer transcript and the hub sections (spec 4.5)

    def sections(self, ident="members"):
        return movie.chapter_sections(self.dir, self.chapter(ident))

    def test_chapter_sections_keys_are_the_scene_ids(self):
        sections = self.sections()
        self.assertEqual(list(sections), ["ask", "body", "answer"])
        self.assertIn('class="cites"', sections["body"])
        self.assertNotIn("<h2>", sections["body"])

    def test_hub_section_keeps_every_scene(self):
        out = movie.hub_section(self.chapter("members"), self.sections())
        self.assertIn('<section id="ch-members"><h2>The members</h2>', out)
        for text in ("Who is in a group?", "Three consumers share six partitions.",
                     "Each consumer owns two partitions."):
            self.assertIn("<p>%s</p>" % text, out)
        self.assertIn('class="cites"', out)
        self.assertNotIn("<h2>ask</h2>", out)

    def test_viewer_section_drops_ask_and_answer(self):
        out = movie.viewer_section(self.chapter("members"), self.sections())
        self.assertIn("Three consumers share six partitions.", out)
        self.assertNotIn("Who is in a group?", out)
        self.assertNotIn("Each consumer owns two partitions.", out)
        self.assertNotIn('class="cites"', out)
        self.assertNotIn("notes.md", out)

    def test_viewer_section_keeps_inline_code(self):
        sections = {"ask": "<p>q</p>", "answer": "<p>a</p>", "body": "<p>Call <code>poll()</code>.</p>"}
        out = movie.viewer_section(self.chapter("members"), sections)
        self.assertIn("<code>poll()</code>", out)

    def test_viewer_transcript_fails_without_an_answer_section(self):
        self.build_all()
        path = Path(self.dir, "chapters", "members", "index.html")
        text = path.read_text(encoding="utf-8")
        path.write_text(re.sub(r'<section id="answer">.*?</section>', "", text, flags=re.S),
                        encoding="utf-8")
        code, out, _ = self.stitch(self.probes([60, 10, 60, 10, 60, 10, 60]))
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines()[-1],
                         "transcript: FAIL chapter members: transcript has no section answer")

    def test_viewer_transcript_fails_without_a_transcript(self):
        self.build_all()
        os.remove(os.path.join(self.dir, "chapters", "split", "index.html"))
        code, out, _ = self.stitch(self.probes([60, 10, 60, 10, 60, 10, 60]))
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines()[-1], "transcript: FAIL chapter split: no transcript")

    def test_viewer_transcript_lists_questions_without_answers(self):
        self.build_all()
        code, _, _ = self.stitch(self.probes([60, 10, 60, 10, 60, 10, 60]))
        self.assertEqual(code, 0)
        page = Path(self.dir, "review", "viewer-transcript.html").read_text(encoding="utf-8")
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertIn('<html lang="en">', page)
        self.assertIn("<h1>How a consumer group rebalances</h1>", page)
        for question in self.movie["questions"]:
            self.assertIn("<li>%s</li>" % question["text"], page)
            self.assertNotIn(question["answer"], page)
        self.assertNotIn('class="cites"', page)
        self.assertNotIn("notes.md", page)
        self.assertIn('<section id="ch-pause">', page)
        hub = Path(self.dir, "build", "hub-sections.html").read_text(encoding="utf-8")
        self.assertEqual(hub.count("<section id=\"ch-"), 4)
        self.assertIn('class="cites"', hub)

    def test_viewer_transcript_names_a_still_per_chapter(self):
        # red: no still is copied, the still of another scene or chapter is, or the page names none
        self.build_all()
        for ident in ("members", "trigger", "split", "pause"):
            Path(self.dir, "chapters", ident, "review", "still-02-body-end.png").write_bytes(
                ("end of body, %s" % ident).encode("utf-8"))
        code, _, _ = self.stitch(self.probes([60, 10, 60, 10, 60, 10, 60]))
        self.assertEqual(code, 0)
        page = Path(self.dir, "review", "viewer-transcript.html").read_text(encoding="utf-8")
        sections = dict(re.findall(r'<section id="ch-([^"]+)">(.*?)</section>', page, re.S))
        for k, ident in enumerate(("members", "trigger", "split", "pause"), start=1):
            name = "viewer-stills/%d-%s.png" % (k, ident)
            self.assertEqual(Path(self.dir, "review", name).read_bytes(),
                             ("end of body, %s" % ident).encode("utf-8"), name)
            self.assertIn('<p class="still">still: %s</p>' % name, sections[ident])
        self.assertEqual(sorted(os.listdir(os.path.join(self.dir, "review", "viewer-stills"))),
                         ["1-members.png", "2-trigger.png", "3-split.png", "4-pause.png"])

    def test_viewer_transcript_fails_without_a_still(self):
        self.build_all()
        os.remove(os.path.join(self.dir, "chapters", "split", "review", "still-02-body-end.png"))
        code, out, _ = self.stitch(self.probes([60, 10, 60, 10, 60, 10, 60]))
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines()[-1], "transcript: FAIL chapter split: no still"
                                               " chapters/split/review/still-02-body-end.png")
        self.assertFalse(self.exists("review/viewer-transcript.html"))

    def test_the_still_is_of_the_last_scene_before_answer(self):
        sections = {"ask": "<p>q</p>", "one": "<p>1</p>", "two": "<p>2</p>", "answer": "<p>a</p>"}
        self.assertEqual(movie.still_source(self.chapter("pause"), sections),
                         "chapters/pause/review/still-03-two-end.png")

    # the hub page (spec 4.6)

    def stitched(self):
        """A stitch of the copy with every part built: it writes `build/hub-sections.html`."""
        self.build_all()
        code, _, _ = self.stitch(self.probes([60, 10, 60, 10, 60, 10, 60]))
        self.assertEqual(code, 0)

    def test_hub_holds_the_chapter_list_and_sections(self):
        self.stitched()
        page = movie.hub(self.dir, self.movie, [0.0, 70.0, 140.0, 210.0])
        self.assertIn('<li><a href="#ch-members" data-start="0.0">The members</a></li>', page)
        self.assertIn('<li><a href="#ch-trigger" data-start="70.0">The trigger</a></li>', page)
        self.assertIn('<section id="ch-members"><h2>The members</h2>', page)
        self.assertIn('<meta name="explain-rung" content="movie">', page)
        self.assertIn('<video id="movie" controls src="video.mp4">', page)
        self.assertIn('data-root="%s"' % os.path.abspath(self.dir), page)
        self.assertIn('<html lang="en">', page)
        for ident in ("members", "trigger", "split", "pause"):
            self.assertIn('<a href="chapters/%s/index.html" data-ste="skip">transcript</a>\n'
                          "</section>" % ident, page)
        self.assertNotIn("{{", page)

    def test_hub_lists_the_questions_with_answers_and_cites(self):
        self.stitched()
        self.movie["questions"][0]["cites"] = [{"path": "src/group.py", "line": 3,
                                                "snippet": "def join(member):"}]
        page = movie.hub(self.dir, self.movie, [0.0, 70.0, 140.0, 210.0])
        self.assertIn("<dt>What starts a rebalance?</dt>\n<dd>A member joins, leaves, or misses its"
                      ' heartbeat.<div class="cites" data-ste="skip"><cite data-path="src/group.py"'
                      ' data-line="3" data-snippet="def join(member):">group.py:3 <code>def'
                      " join(member):</code></cite></div></dd>", page)
        self.assertIn("<dt>Who decides the new split?</dt>\n<dd>The group leader decides the"
                      " split, and the coordinator sends it out.</dd>", page)

    def test_hub_shows_a_url_cite_by_its_host(self):
        self.stitched()
        self.movie["questions"][0]["cites"] = [{"path": "https://kafka.apache.org/documentation/",
                                                "snippet": "consumer group"}]
        page = movie.hub(self.dir, self.movie, [0.0, 70.0, 140.0, 210.0])
        self.assertIn('<div class="cites" data-ste="skip"><cite data-path="https://kafka.apache.org/'
                      'documentation/" data-snippet="consumer group">kafka.apache.org <code>consumer'
                      " group</code></cite></div></dd>", page)

    def test_hub_escapes_plan_text_in_one_pass(self):
        self.stitched()
        self.movie["title"] = "Groups & <members> {{sections}}"
        page = movie.hub(self.dir, self.movie, [0.0, 70.0, 140.0, 210.0])
        self.assertIn("<h1>Groups &amp; &lt;members&gt; {{sections}}</h1>", page)
        self.assertEqual(page.count('<section id="ch-members">'), 1)

    def test_stitch_writes_index_html(self):
        self.build_all()
        code, out, _ = self.stitch(self.probes([60, 10, 60, 10, 60, 10, 60]))
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[-2:], ["hub: ok index.html", "length: ok (270.0 s)"])
        page = Path(self.dir, "index.html").read_text(encoding="utf-8")
        self.assertIn("<title>How a consumer group rebalances</title>", page)
        self.assertIn("<h1>How a consumer group rebalances</h1>", page)
        self.assertIn('data-start="210.0"', page)


class SaveCase(MovieCase):
    def test_save_is_atomic(self):
        self.movie["title"] = "Changed"
        movie.save(self.dir, self.movie)
        self.assertEqual(sorted(os.listdir(self.dir)), ["chapters", "movie.json"])
        self.assertEqual(movie.load(self.dir), self.movie)
        json.loads(Path(self.dir, "movie.json").read_text(encoding="utf-8"))

    def test_resolve_root(self):
        self.assertEqual(movie.resolve_root(self.dir, "."), os.path.abspath(self.dir))
        self.assertEqual(movie.resolve_root(self.dir, "/abs"), "/abs")


if __name__ == "__main__":
    unittest.main()
