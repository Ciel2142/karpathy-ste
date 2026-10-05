"""Drift guard for the per-format limits: video/formats.json is the one source, and the limits table
and the code sentence of rungs/brainrot.md (skill text that the model reads at run time) must say
the same. Each test names the mutation that turns it red."""

import json
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_video_timeline import APP_LINES
from test_video_timeline_brainrot import brainrot_script

EXPLAIN = Path(__file__).resolve().parent.parent
FORMATS = EXPLAIN / "video" / "formats.json"
TOOL = EXPLAIN / "video" / "build-timeline.mjs"
RUNG = EXPLAIN / "rungs" / "brainrot.md"
TABLE_HEADER = "| Limit | explainer | brainrot |"

# One row per table row: (label as the rung writes it, explainer template, brainrot template).
# `fill` is the one place that turns a template and a formats row into a cell.
CELL_TEMPLATES = [
    ("canvas", "{width}×{height}", "{width}×{height}"),
    ("scenes", "{minScenes}–{maxScenes}", "{minScenes}–{maxScenes}"),
    ("max scene length", "{maxSceneSeconds} s", "{maxSceneSeconds} s"),
    ("max total length", "{maxTotalSeconds} s", "{maxTotalSeconds} s"),
    ("narration words per scene", "{maxNarrationWords}", "{maxNarrationWords}"),
    ("lead / tail frames", "{leadFrames} / {tailFrames}", "{leadFrames} / {tailFrames}"),
    ("code range", "{codeLines} lines × {codeColumns} columns", "{codeLines} lines × {codeColumns} columns"),
    ("`bullets-appear` text", "{bulletText} chars", "{bulletText} chars"),
    (
        "`before-after`",
        "side by side; 0–{beforeAfterLines} lines × {beforeAfterLineChars} chars; heading {beforeAfterHeading}",
        "stacked; 0–{beforeAfterLines} lines × {beforeAfterLineChars} chars; heading {beforeAfterHeading}",
    ),
    ("diagram `label` / `sub`", "{diagramLabel} / {diagramSub}", "{diagramLabel} / {diagramSub}"),
    # The edge label limit (10) is fixed in build-timeline.mjs for both formats; the brainrot
    # clause follows sameRowEdgeLabel (test_rung_edge_label_row_follows_same_row_rule).
    ("diagram edge `label`", "10", "10; no label on an edge in a row"),
    ("`title` title / subtitle", "{titleTitle} / {titleSubtitle}", "{titleTitle} / {titleSubtitle}"),
    ("scene heading", "—", "{sceneTitle} chars"),
    ("caption chunk", "—", "1–3 words, {captionChars} chars"),
]


def load_formats():
    return json.loads(FORMATS.read_text(encoding="utf-8"))


def fill(template, row):
    """A template with the fields of a formats row filled in. A null field (the explainer has no
    caption cap) is for a template that is a plain text, such as `—`; a null that a template names
    would print as the text "None", so it raises."""
    for _, field, _, _ in string.Formatter().parse(template):
        if field is not None and row[field] is None:
            raise ValueError("the template %r names %r, which is null in the row" % (template, field))
    return template.format(**row)


def expected_cells(formats):
    """Row label -> (explainer cell, brainrot cell), each formatted from its formats.json row."""
    return {
        label: (fill(explainer, formats["explainer"]), fill(brainrot, formats["brainrot"]))
        for label, explainer, brainrot in CELL_TEMPLATES
    }


def rung_text():
    return RUNG.read_text(encoding="utf-8")


def rung_limits_table():
    """Row label -> (explainer cell, brainrot cell) of the one table in the rung whose header row
    is `| Limit | explainer | brainrot |`. Cells are the text between the pipes, stripped."""
    lines = rung_text().split("\n")
    starts = [i for i, line in enumerate(lines) if line.strip() == TABLE_HEADER]
    if len(starts) != 1:
        raise AssertionError("the rung needs exactly one table headed %r, found %d" % (TABLE_HEADER, len(starts)))
    rows = {}
    for line in lines[starts[0] + 2 :]:  # skip the header and the separator row
        if not line.startswith("|"):
            break
        label, explainer, brainrot = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows[label] = (explainer, brainrot)
    return rows


class TestRungMatchesFormats(unittest.TestCase):
    def test_rung_table_matches_formats(self):
        """Red: a limit changed in formats.json and not in the rung table (or the reverse), a
        label or a cell reworded, or a row added to one side only."""
        self.assertEqual(rung_limits_table(), expected_cells(load_formats()))

    def test_rung_awk_threshold_is_code_columns(self):
        """Red: the `length($0) > N` of the rung's awk command is not the brainrot code column limit."""
        found = re.findall(r"length\(\$0\) > (\d+)", rung_text())
        self.assertEqual(found, [str(load_formats()["brainrot"]["codeColumns"])])

    def test_rung_fail_example_names_code_columns(self):
        """Red: the example failure line `(max N, brainrot)` of the rung is not the brainrot code column limit."""
        found = re.findall(r"\(max (\d+), brainrot\)", rung_text())
        self.assertEqual(found, [str(load_formats()["brainrot"]["codeColumns"])])

    def test_rung_code_sentence_matches(self):
        """Red: the code sentence of the rung holds other line or column limits than formats.json."""
        row = load_formats()["brainrot"]
        sentence = "at most {codeLines} lines, and each line has at most {codeColumns} columns".format(**row)
        self.assertIn(sentence, " ".join(rung_text().split()))

    def test_rung_caption_sentence_matches(self):
        """Red: the Captions bullet of the rung holds another character cap than formats.json."""
        cap = load_formats()["brainrot"]["captionChars"]
        sentence = "caption holds at most %d characters" % cap
        self.assertIn(sentence, " ".join(rung_text().split()))

    def test_rung_heading_sentence_matches(self):
        """Red: the Scene heading bullet of the rung holds another limit than formats.json."""
        cap = load_formats()["brainrot"]["sceneTitle"]
        self.assertIn("so it has at most %d characters" % cap, " ".join(rung_text().split()))

    def test_rung_edge_label_row_follows_same_row_rule(self):
        """Red: formats.json lets a brainrot edge in a row carry a label again (sameRowEdgeLabel no
        longer false) while the rung still forbids it, or the explainer row gains the rule."""
        formats = load_formats()
        self.assertIs(formats["brainrot"]["sameRowEdgeLabel"], False)
        self.assertIsNone(formats["explainer"]["sameRowEdgeLabel"])
        self.assertEqual(rung_limits_table()["diagram edge `label`"], ("10", "10; no label on an edge in a row"))

    def test_fill_refuses_a_null_field(self):
        """Red: `fill` turns a null that a template names into the text "None" (the rung table
        would then claim "None chars")."""
        with self.assertRaises(ValueError):
            fill("{captionChars} chars", {"captionChars": None})
        self.assertEqual(fill("—", {"captionChars": None}), "—")


class TestBuildTimelineReadsFormats(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(os.path.realpath(tmp.name))
        self.tool = self.dir / "build-timeline.mjs"
        shutil.copy(TOOL, self.tool)

    def run_node(self, *args):
        return subprocess.run(
            ["node", str(self.tool), *args], capture_output=True, text=True, cwd=self.dir, timeout=60
        )

    def write_script(self, code_columns):
        """A brainrot script (the shared fixture) whose code scene reads src/app.py lines 3-10, with
        line 3 `code_columns` columns wide (it keeps the "line 3" the cite quotes); the other lines
        are short."""
        lines = list(APP_LINES)
        lines[2] = "line 3 ".ljust(code_columns, "x")
        (self.dir / "src").mkdir(exist_ok=True)
        (self.dir / "src" / "app.py").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (self.dir / "script.json").write_text(json.dumps(brainrot_script()), encoding="utf-8")
        return str(self.dir / "script.json")

    def assert_clean_fail(self, result, cause):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 1, result.stdout)
        self.assertTrue(result.stdout.startswith("FAIL script: cannot read formats.json: " + cause), result.stdout)
        self.assertNotRegex(result.stderr, r"(?m)^\s+at ")
        self.assertEqual(result.stderr, "")

    def test_missing_formats_file_fails_cleanly(self):
        """Red: the script reads formats.json without catching the error (a Node stack trace, exit 1
        with an empty stdout), or hard-codes the rows and never reads the file."""
        script = self.write_script(10)
        result = self.run_node("--check", script, "--root", str(self.dir))
        self.assert_clean_fail(result, "ENOENT")
        self.assertTrue(result.stdout.startswith("FAIL script: cannot read formats.json"), result.stdout)

    def test_missing_formats_file_fails_cleanly_in_build_mode(self):
        """Red: only --check handles a bad formats.json; build mode prints a stack trace."""
        script = self.write_script(10)
        durations = self.dir / "durations.json"
        durations.write_text(json.dumps({"engine": "say", "fallback": None, "scenes": {}}), encoding="utf-8")
        result = self.run_node(script, str(durations), "say", str(self.dir / "out.json"), "--root", str(self.dir))
        self.assert_clean_fail(result, "ENOENT")

    def test_unreadable_formats_file_fails_cleanly(self):
        """Red: a read error other than a missing file is not caught (a directory stands in for an
        unreadable file, so the test needs no file permissions)."""
        script = self.write_script(10)
        (self.dir / "formats.json").mkdir()
        result = self.run_node("--check", script, "--root", str(self.dir))
        self.assert_clean_fail(result, "EISDIR")

    def test_invalid_json_formats_file_fails_cleanly(self):
        """Red: a JSON parse error is not caught."""
        script = self.write_script(10)
        (self.dir / "formats.json").write_text("{ not json", encoding="utf-8")
        result = self.run_node("--check", script, "--root", str(self.dir))
        self.assert_clean_fail(result, "")

    def test_formats_file_without_both_rows_fails_cleanly(self):
        """Red: a valid JSON file that lacks the explainer or brainrot row crashes later, with a stack trace."""
        script = self.write_script(10)
        for text in ("null", "[]", '{"explainer": {}}', '{"explainer": {}, "brainrot": 7}'):
            with self.subTest(text=text):
                (self.dir / "formats.json").write_text(text, encoding="utf-8")
                result = self.run_node("--check", script, "--root", str(self.dir))
                self.assert_clean_fail(result, "")

    def test_build_timeline_reads_formats_file(self):
        """Red: the limits stay a literal in build-timeline.mjs, so a changed formats.json has no
        effect. With brainrot codeColumns 39, a 40-column code line fails."""
        script = self.write_script(40)
        formats = load_formats()
        (self.dir / "formats.json").write_text(json.dumps(formats), encoding="utf-8")
        passing = self.run_node("--check", script, "--root", str(self.dir))
        self.assertEqual((passing.returncode, passing.stdout), (0, ""), passing.stderr)
        formats["brainrot"]["codeColumns"] = 39
        (self.dir / "formats.json").write_text(json.dumps(formats), encoding="utf-8")
        failing = self.run_node("--check", script, "--root", str(self.dir))
        self.assertEqual(failing.returncode, 1, failing.stderr)
        self.assertEqual(failing.stdout, "FAIL scene code: line 3 is 40 columns (max 39, brainrot)\n")


if __name__ == "__main__":
    unittest.main()
