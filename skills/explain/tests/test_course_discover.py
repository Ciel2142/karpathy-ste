"""Tests for course_discover.py: the discovery step of the course rung (rungs/course.md "Discover").

Each test builds a small work directory in a temporary directory: two sources (`esb`, `diadoc`) with their maps
in `<course-dir>/map/`, and candidate directories beside them. The maps name handles in backticks in their
`Other systems` section. The script greps each candidate once, drops a handle that matches more than 5
candidates, ranks a candidate whose name is a system name of the maps first, then by its number of handles,
then by name, and keeps 8.
"""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import course_discover  # noqa: E402

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "course_discover.py"

ESB_MAP = """# Map: esb

## Entry points
- The listener reads `ESB.IN`. | esb/Listener.java:1 | @Listener

## Other systems
- CryptoProService: signs the bytes. Handles: `/api/crypto/sign`. | esb/Sign.java:3 | `notahandle`
- Document stores (docforge): `ESB.DIADOC.SEND` and `MessageType`. | esb/Out.java:2 | send()

## Error paths
- `ESB.ERRORS` holds the failed messages. | esb/Err.java:1 | dlq
"""

DIADOC_MAP = """# Map: diadoc

## Other systems
- ESB (the bus): `DIADOC.ESB`, `ESB.DIADOC` and `it's-a-handle`. | diadoc/Reply.java:5 | reply()
"""


class DiscoverCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = os.path.realpath(tmp.name)
        self.work = os.path.join(self.base, "work")
        self.course = os.path.join(self.base, "course")
        os.makedirs(os.path.join(self.course, "map"))
        self.write("course/map/esb.md", ESB_MAP)
        self.write("course/map/diadoc.md", DIADOC_MAP)
        self.write("work/esb/Out.java", "send(\"ESB.DIADOC.SEND\"); // MessageType\n")
        self.write("work/diadoc/Reply.java", "reply(\"DIADOC.ESB\");\n")

    def write(self, relative, text):
        path = os.path.join(self.base, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Path(path).write_text(text, encoding="utf-8")

    def candidate(self, name, *texts, file="Config.java"):
        self.write("work/%s/src/%s" % (name, file), "\n".join(texts) + "\n")
        return os.path.join(self.work, name)

    def run_cli(self, *extra):
        argv = [self.course, self.work, "--source", os.path.join(self.work, "esb"),
                "--source", os.path.join(self.work, "diadoc"), *extra]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = course_discover.main(argv)
        return code, out.getvalue().splitlines(), err.getvalue()

    def kept(self, lines):
        return [line.split()[1] for line in lines if line.startswith("candidate: ")]

    # red: handles taken from the cite part of a line (`notahandle`), or from a section other than Other systems
    def test_reads_the_handles_of_other_systems_only(self):
        handles, names, missing = course_discover.read_maps(self.course)
        self.assertEqual(missing, [])
        self.assertEqual(handles, ["/api/crypto/sign", "DIADOC.ESB", "ESB.DIADOC", "ESB.DIADOC.SEND",
                                   "MessageType", "it's-a-handle"])
        self.assertEqual(sorted(names), ["cryptoproservice", "docforge", "documentstores", "esb", "thebus"])

    # red: count ranking first (the live run cut cryptoproservice), or a name match that ignores case and dashes
    def test_a_name_match_ranks_before_more_handles(self):
        crypto = self.candidate("CryptoProService", "post(\"/api/crypto/sign\")")
        other = self.candidate("helm-values", "a: DIADOC.ESB", "b: ESB.DIADOC.SEND")
        code, lines, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(lines[:2], [
            "candidate: %s name-match 1 handles: /api/crypto/sign" % crypto,
            "candidate: %s - 3 handles: DIADOC.ESB ESB.DIADOC ESB.DIADOC.SEND" % other,
        ])

    # red: a handle that matches more than 5 candidates kept, or a candidate with only such handles kept
    def test_drops_a_handle_of_more_than_5_candidates(self):
        general = [self.candidate("gen-%d" % n, "MessageType") for n in range(6)]
        both = self.candidate("routes", "MessageType", "DIADOC.ESB")
        code, lines, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("candidate: %s - 1 handles: DIADOC.ESB" % both, lines)
        for path in general:
            self.assertIn("cut: %s only handles of more than 5 candidates" % path, lines)
        self.assertNotIn(both, [line for line in lines if line.startswith("cut: ")])

    # red: no limit, or a tie broken by the order of the file system instead of the name
    def test_keeps_8_and_breaks_ties_by_name(self):
        self.write("course/map/extra.md", "## Other systems\n- Extras: %s. | x:1 | y\n"
                   % ", ".join("`EXTRA.%d`" % n for n in range(10)))
        for n in reversed(range(10)):
            self.candidate("extra-%d" % n, "EXTRA.%d" % n)
        self.candidate("aaa-two", "ESB.DIADOC", "DIADOC.ESB")
        code, lines, _ = self.run_cli()
        self.assertEqual(code, 0)
        kept = self.kept(lines)
        self.assertEqual([os.path.basename(path) for path in kept],
                         ["aaa-two"] + ["extra-%d" % n for n in range(7)])
        cut = [line for line in lines if line.startswith("cut: ")]
        self.assertEqual(cut, ["cut: %s more than 8 discovered sources" % os.path.join(self.work, "extra-%d" % n)
                               for n in (7, 8, 9)])

    # red: the handles spliced into a shell command, where `'` ends the quote
    def test_a_handle_with_a_quote(self):
        path = self.candidate("quoted", "x = \"it's-a-handle\"")
        code, lines, _ = self.run_cli()
        self.assertEqual((code, lines[0]), (0, "candidate: %s - 1 handles: it's-a-handle" % path))

    # red: grep -o reports the longest match at a place, so a handle inside a longer handle is not counted
    def test_a_handle_inside_a_longer_handle_counts(self):
        path = self.candidate("sender", "queue = ESB.DIADOC.SEND")
        code, lines, _ = self.run_cli()
        self.assertEqual(lines[0], "candidate: %s - 2 handles: ESB.DIADOC ESB.DIADOC.SEND" % path)

    # red: a source, a hidden directory, a file of the parent, a text type outside the include list, or a match in
    # node_modules counted as a candidate or a match
    def test_candidates_and_files_that_do_not_count(self):
        self.candidate(".hidden", "DIADOC.ESB")
        self.write("work/notes.md", "DIADOC.ESB\n")
        self.candidate("textonly", "DIADOC.ESB", file="notes.txt")
        self.write("work/vendored/node_modules/x/index.json", "\"DIADOC.ESB\"\n")
        code, lines, _ = self.run_cli()
        self.assertEqual((code, lines), (0, ["discover: 0 kept, 0 cut, 2 candidates, 6 handles, 0 dropped"]))
        listed = Path(self.course, "discover", "candidates.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(listed, [os.path.join(self.work, name) for name in ("textonly", "vendored")])

    # red: the sources taken only from --source, so a run without it searches the sources themselves
    def test_sources_from_the_map_names_without_source_args(self):
        path = self.candidate("bus-routes", "DIADOC.ESB")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = course_discover.main([self.course, self.work])
        self.assertEqual((code, out.getvalue().splitlines()[0]), (0, "candidate: %s - 1 handles: DIADOC.ESB" % path))

    # red: one grep per handle and candidate (3,186 calls in the live run), a shell, or the handles in argv
    def test_one_grep_per_candidate_with_the_handles_in_a_file(self):
        for name in ("one", "two", "three"):
            self.candidate(name, "DIADOC.ESB")
        calls = []
        real = subprocess.run

        def spy(argv, **kwargs):
            calls.append((argv, kwargs))
            return real(argv, **kwargs)

        with mock.patch.object(course_discover.subprocess, "run", side_effect=spy):
            code, lines, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 3)
        handles_file = os.path.join(self.course, "discover", "handles.txt")
        for argv, kwargs in calls:
            self.assertIsInstance(argv, list)
            self.assertFalse(kwargs.get("shell"))
            self.assertEqual(argv[argv.index("-f") + 1], handles_file)
            self.assertIn("-o", argv)
            self.assertIn("-h", argv)
            self.assertNotIn("DIADOC.ESB", argv)
            for include in course_discover.INCLUDES:
                self.assertIn("--include=*.%s" % include, argv)
            for exclude in course_discover.EXCLUDE_DIRS:
                self.assertIn("--exclude-dir=%s" % exclude, argv)

    # red: stdout and discover/result.txt differ, or a file of the output table not written
    def test_writes_the_discover_directory(self):
        crypto = self.candidate("cryptoproservice", "/api/crypto/sign")
        code, lines, _ = self.run_cli()
        folder = Path(self.course, "discover")
        self.assertEqual(sorted(os.listdir(folder)),
                         ["candidates.txt", "handles.txt", "matches.tsv", "result.txt"])
        self.assertEqual(folder.joinpath("result.txt").read_text(encoding="utf-8").splitlines(), lines)
        self.assertEqual(folder.joinpath("matches.tsv").read_text(encoding="utf-8"),
                         "%s\t/api/crypto/sign\n" % crypto)
        self.assertEqual(lines[-1], "discover: 1 kept, 0 cut, 1 candidates, 6 handles, 0 dropped")

    # red: a map without the section is silent (map-task.md asks for it; a missing section hides the handles)
    def test_a_map_without_other_systems_is_named(self):
        self.write("course/map/docs.md", "# Map: docs\n\n## Entry points\n- none\n")
        code, lines, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("note: map docs.md has no Other systems section", lines)

    # red: a usage error that writes files or exits 0
    def test_usage_errors_exit_2(self):
        for argv in ([], [self.course], [os.path.join(self.base, "nowhere"), self.work],
                     [self.course, os.path.join(self.base, "nowhere")], [self.course, self.work, "--source"]):
            with self.subTest(argv=argv):
                err = io.StringIO()
                with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                    code = course_discover.main(argv)
                self.assertEqual(code, 2)
                self.assertTrue(err.getvalue())

    def test_runs_as_a_script(self):
        self.candidate("cryptoproservice", "/api/crypto/sign")
        run = subprocess.run([sys.executable, "-B", str(SCRIPT), self.course, self.work],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(run.stdout.startswith("candidate: "), run.stdout)


if __name__ == "__main__":
    unittest.main()
