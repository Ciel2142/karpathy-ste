"""Tests for the film format of video/build-timeline.mjs: the formats.json row and the script
check (--check). Each test names the mutation that turns it red."""

import copy
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_video_timeline import EXPLAIN, FLOW_NARRATION, TOOL, VideoCase, base_script, cite
from test_video_timeline_brainrot import brainrot_script

FORMATS = EXPLAIN / "video" / "formats.json"

FILM_ROW = {
    "width": 1280,
    "height": 720,
    "minScenes": 3,
    "maxScenes": 30,
    "maxSceneSeconds": 30,
    "maxTotalSeconds": 150,
    "maxNarrationWords": 45,
    "leadFrames": 6,
    "pauseFrames": 12,
    "sourceLines": 20,
    "wordTimed": True,
}


def film_script():
    """A valid three-scene film script: base_script()'s title, subject and provenance, one source
    (src/app.py lines 3 to 10) and three scenes that carry narration, cites and (one) a pause."""
    base = base_script()
    return {
        "format": "film",
        "title": base["title"],
        "subject": base["subject"],
        "provenance": base["provenance"],
        "sources": [{"id": "app", "path": "src/app.py", "from": 3, "to": 10}],
        "scenes": [
            {
                "id": "type",
                "narration": "The router picks a handler. The handler replies.",
                "cites": [cite()],
            },
            {
                "id": "forms",
                "pause": 30,
                "narration": FLOW_NARRATION,
                "cites": [cite()],
            },
            {
                "id": "ends",
                "narration": "The first part sets up. The second part runs.",
                "cites": [cite(line=3, snippet="line 3")],
            },
        ],
    }


class TestFilmCheck(VideoCase):
    def scenes_of(self, script, count):
        """`count` scenes: copies of the first scene with the ids s1, s2, ..."""
        first = script["scenes"][0]
        return [dict(copy.deepcopy(first), id="s%d" % n) for n in range(1, count + 1)]

    def mutated(self, mutate):
        script = film_script()
        mutate(script)
        return self.check(script)

    def test_film_fixture_passes(self):
        """Red: `film` is not a known format (the check reads "format must be explainer or
        brainrot" and validates the fixture as an explainer), or the film check is stricter than
        its own fixture."""
        result = self.check(film_script())
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_film_row_values(self):
        """Red: a value of the film row of formats.json changed, or the row is missing."""
        rows = json.loads(FORMATS.read_text(encoding="utf-8"))
        self.assertEqual(rows["film"], FILM_ROW)

    def test_film_scene_count(self):
        """Red: the film scene range reads the explainer 3 to 8 (30 scenes fail), or the line loses
        the film tag, or the range is exclusive at an end."""
        script = film_script()
        script["scenes"] = script["scenes"][:2]
        self.assertFails(self.check(script), "FAIL script: 2 scenes (needs 3 to 30, film)")
        script["scenes"] = self.scenes_of(script, 30)
        result = self.check(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        script["scenes"] = self.scenes_of(script, 31)
        self.assertFails(self.check(script), "FAIL script: 31 scenes (needs 3 to 30, film)")

    def test_film_scene_with_component_or_props_is_refused(self):
        """Red: a film scene may carry a component (or props), or the line is reported once per
        key instead of once per scene, or it is reported for other keys."""
        line = "FAIL scene type: a film scene has no component or props"
        script = film_script()
        script["scenes"][0]["component"] = "title"
        self.assertFails(self.check(script), line)
        script = film_script()
        script["scenes"][0]["props"] = {}
        self.assertFails(self.check(script), line)
        script = film_script()
        script["scenes"][0]["component"] = "title"
        script["scenes"][0]["props"] = {"title": "T", "subtitle": "S", "cue": "The router"}
        self.assertFails(self.check(script), line)
        script = base_script()
        script["format"] = "film"
        self.assertFails(
            self.check(script),
            "FAIL scene intro: a film scene has no component or props",
            "FAIL scene flow: a film scene has no component or props",
            "FAIL scene code: a film scene has no component or props",
        )

    def test_film_scene_keys(self):
        """Red: an unknown key of a film scene is not reported (a `cue` key is a component-scene
        key), or a missing narration is not reported."""
        script = film_script()
        script["scenes"][0]["cue"] = "x"
        self.assertFails(self.check(script), 'FAIL scene type: unexpected key "cue"')
        script = film_script()
        del script["scenes"][0]["narration"]
        self.assertFails(self.check(script), 'FAIL scene type: missing "narration"')

    def test_film_scene_key_named_like_an_inherited_property_is_unexpected(self):
        """Red: the allowed keys of a film scene are looked up with `in` on a plain object, so
        `constructor` and `toString` count as allowed keys."""
        script = film_script()
        script["scenes"][0]["constructor"] = 1
        script["scenes"][0]["toString"] = 1
        self.assertFails(
            self.check(script),
            'FAIL scene type: unexpected key "constructor"',
            'FAIL scene type: unexpected key "toString"',
        )

    def test_film_scene_that_is_not_an_object(self):
        """Red: a scene that is a number crashes the check or is skipped without a line."""
        script = film_script()
        script["scenes"][1] = 7
        self.assertFails(self.check(script), "FAIL scene #2: must be an object")

    def test_film_scene_lines_come_in_the_rule_order(self):
        """Red: the lines of one scene come in another order than: missing id, missing narration;
        the component line; unexpected keys; the id rules; the narration rules; the cites rules;
        the pause line."""
        script = film_script()
        script["scenes"][0] = {"cites": [cite()]}
        self.assertFails(self.check(script), 'FAIL scene #1: missing "id"', 'FAIL scene #1: missing "narration"')
        script = film_script()
        script["scenes"][0] = {
            "id": "Bad Id",
            "pause": 5,
            "cites": [],
            "narration": " ",
            "cue": "x",
            "component": "title",
        }
        self.assertFails(
            self.check(script),
            "FAIL scene #1: a film scene has no component or props",
            'FAIL scene #1: unexpected key "cue"',
            'FAIL scene #1: id "Bad Id" must match [a-z0-9-]',
            "FAIL scene #1: narration is empty",
            "FAIL scene #1: no cites (subject kind file)",
            "FAIL scene #1: pause 5 must be an integer from 12 to 90",
        )

    def test_film_narration_limits(self):
        """Red: the film narration limit reads another row (45 words pass, 46 fail), the line loses
        the film tag, or an all-blank narration passes."""
        script = film_script()
        script["scenes"][0]["narration"] = " ".join(["word"] * 45)
        result = self.check(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        script["scenes"][0]["narration"] = " ".join(["word"] * 46)
        self.assertFails(self.check(script), "FAIL scene type: narration is 46 words (max 45, film)")
        script["scenes"][0]["narration"] = "  "
        self.assertFails(self.check(script), "FAIL scene type: narration is empty")

    def test_film_cites_rule(self):
        """Red: the cites rule is skipped for a film, or a topic subject needs cites."""
        script = film_script()
        script["scenes"][0]["cites"] = []
        self.assertFails(self.check(script), "FAIL scene type: no cites (subject kind file)")
        script = film_script()
        script["subject"]["kind"] = "topic"
        for scene in script["scenes"]:
            del scene["cites"]
        result = self.check(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_film_pause_values(self):
        """Red: the pause range is exclusive at 12 or 90, a non-integer (12.5, "12", null, true)
        passes, or the JSON text 12.0 (the integer 12 once parsed; Python writes 12.0 as that
        text) is refused."""
        for value in ("absent", 12, 90, 12.0):
            with self.subTest(value=value):
                script = film_script()
                if value == "absent":
                    del script["scenes"][1]["pause"]
                else:
                    script["scenes"][1]["pause"] = value
                result = self.check(script)
                self.assertEqual((result.returncode, result.stdout), (0, ""))
        for value in (11, 91, 12.5, "12", None, True):
            with self.subTest(value=value):
                script = film_script()
                script["scenes"][1]["pause"] = value
                self.assertFails(
                    self.check(script),
                    "FAIL scene forms: pause %s must be an integer from 12 to 90" % json.dumps(value),
                )

    def test_film_duplicate_scene_id(self):
        """Red: the duplicate scene id check skips a film, or the line carries another place."""
        script = film_script()
        script["scenes"][1]["id"] = "type"
        self.assertFails(self.check(script), 'FAIL script: duplicate scene id "type"')

    def test_slides_format_is_refused(self):
        """Red: any string is accepted as a format (the format line is gone). The other lines are
        the explainer's: the film keys are not explainer keys."""
        script = film_script()
        script["format"] = "slides"
        result = self.check(script)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL script: format must be explainer or brainrot", result.stdout.splitlines())
        self.assertIn('FAIL script: unexpected key "sources"', result.stdout.splitlines())

    def test_brainrot_refuses_the_film_keys(self):
        """Red: `sources` is an allowed top-level key, or `pause` an allowed scene key, for every
        format and not for film alone."""
        script = brainrot_script()
        script["sources"] = []
        self.assertFails(self.check(script), 'FAIL script: unexpected key "sources"')
        script = brainrot_script()
        self.scene(script, "intro")["pause"] = 12
        self.assertFails(self.check(script), 'FAIL scene intro: unexpected key "pause"')

    def test_explainer_refuses_the_film_keys(self):
        """Red: `sources` or `pause` is an allowed key of an explainer script."""
        script = base_script()
        script["sources"] = []
        self.assertFails(self.check(script), 'FAIL script: unexpected key "sources"')
        script = base_script()
        self.scene(script, "intro")["pause"] = 12
        self.assertFails(self.check(script), 'FAIL scene intro: unexpected key "pause"')

    def test_formats_file_without_the_film_row_fails_cleanly(self):
        """Red: the loader still wants two rows (a formats.json without film is accepted and the
        film check then reads an undefined row), or the cause text is not the three-row one."""
        tool_dir = Path(self.dir) / "tool"  # a copy of the tool, with its own formats.json beside it
        tool_dir.mkdir()
        shutil.copy(TOOL, tool_dir / TOOL.name)
        rows = json.loads(FORMATS.read_text(encoding="utf-8"))
        del rows["film"]
        (tool_dir / "formats.json").write_text(json.dumps(rows), encoding="utf-8")
        script = self.write_json("script.json", film_script())
        result = subprocess.run(
            ["node", str(tool_dir / TOOL.name), "--check", script, "--root", self.dir],
            capture_output=True,
            text=True,
            cwd=self.dir,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(
            result.stdout,
            "FAIL script: cannot read formats.json: expected an object with an explainer, a film and a brainrot row\n",
        )
        self.assertEqual(result.stderr, "")


class TestFilmSources(VideoCase):
    """The `sources` check of a film: the shape of each entry, then the file under the data root."""

    def assertPasses(self, result):
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def with_sources(self, sources):
        script = film_script()
        script["sources"] = sources
        return self.check(script)

    def changed(self, **changes):
        """The one source of film_script() with these keys set (a value of `...` removes the key)."""
        source = film_script()["sources"][0]
        for key, value in changes.items():
            if value is ...:
                del source[key]
            else:
                source[key] = value
        return self.with_sources([source])

    def test_sources_absent_and_empty_pass(self):
        """Red: an empty `sources` array is refused, or an absent key is read as a fault."""
        script = film_script()
        del script["sources"]
        self.assertPasses(self.check(script))
        self.assertPasses(self.with_sources([]))

    def test_sources_must_be_an_array(self):
        """Red: a `sources` that is not an array is read as no sources, or the key `sources: null`
        counts as absent."""
        for value in ({}, None):
            with self.subTest(value=value):
                self.assertFails(self.with_sources(value), "FAIL script: sources must be an array")

    def test_source_shape(self):
        """Red: an entry that is not an object crashes the check or passes, a missing key passes, or
        an extra key (here `lines`) passes."""
        self.assertFails(self.with_sources([7]), "FAIL source #1: must be an object")
        self.assertFails(self.changed(to=...), 'FAIL source app: missing "to"')
        self.assertFails(self.changed(lines=[]), 'FAIL source app: unexpected key "lines"')

    def test_source_with_several_shape_faults_gives_one_line_each_in_rule_order(self):
        """Red: the lines of one entry come in another order than: missing keys, unexpected keys,
        the id rules, path, from, to; or one line stands for several faults."""
        source = {"id": "App", "path": 5, "from": "1", "extra": 1}
        self.assertFails(
            self.with_sources([source]),
            'FAIL source #1: missing "to"',
            'FAIL source #1: unexpected key "extra"',
            'FAIL source #1: id "App" must match [a-z0-9-]',
            "FAIL source #1: path must be a string",
            "FAIL source #1: from must be an integer",
        )

    def test_source_id(self):
        """Red: the id pattern of a source is not the scene id pattern, an empty or non-string id
        passes, or a second entry with the same id is accepted."""
        self.assertFails(self.changed(id="App"), 'FAIL source #1: id "App" must match [a-z0-9-]')
        for value in ("", 5):
            with self.subTest(id=value):
                self.assertFails(self.changed(id=value), "FAIL source #1: id must be a non-empty string")
        twin = film_script()["sources"][0]
        self.assertFails(self.with_sources([twin, dict(twin)]), "FAIL source app: duplicate id")

    def test_source_id_named_like_an_inherited_property_is_ordinary(self):
        """Red: the ids seen so far are kept in a plain object and looked up with `in`, so the first
        source called `constructor` is reported as a duplicate; or a second one is not."""
        source = dict(film_script()["sources"][0], id="constructor")
        self.assertPasses(self.with_sources([source]))
        self.assertFails(self.with_sources([source, dict(source)]), "FAIL source constructor: duplicate id")

    def test_source_path(self):
        """Red: a path that is not a string or is empty passes, or `..` and an absolute path are
        read (the outside-the-root guard is skipped)."""
        self.assertFails(self.changed(path=5), "FAIL source app: path must be a string")
        self.assertFails(self.changed(path=""), "FAIL source app: path is empty")
        for value in ("../x.py", "/etc/hosts"):
            with self.subTest(path=value):
                self.assertFails(
                    self.changed(path=value),
                    "FAIL source app: path %s must be a relative path inside the data root" % json.dumps(value),
                )

    def test_source_range(self):
        """Red: from or to may be a string or a fraction, an invalid range is not reported, the limit
        reads another row (20 lines pass, 21 fail), or the line loses the film tag."""
        for key, value in (("from", "3"), ("from", 3.5), ("to", "10"), ("to", True)):
            with self.subTest(key=key, value=value):
                self.assertFails(self.changed(**{key: value}), "FAIL source app: %s must be an integer" % key)
        self.assertFails(self.changed(**{"from": 0}), "FAIL source app: range 0-10 is not a valid line range")
        self.assertFails(
            self.changed(**{"from": 5, "to": 3}), "FAIL source app: range 5-3 is not a valid line range"
        )
        self.assertPasses(self.changed(**{"from": 1, "to": 20}))
        self.assertFails(self.changed(**{"from": 1, "to": 21}), "FAIL source app: range 1-21 is 21 lines (max 20, film)")

    def test_invalid_range_is_the_only_line(self):
        """Red: an invalid range does not stop the entry: the line count, the path guard or the read
        also report (this range is 31 lines wide, under a path outside the root)."""
        self.assertFails(
            self.changed(**{"from": 0, "to": 30, "path": "../x.py"}),
            "FAIL source app: range 0-30 is not a valid line range",
        )

    def test_source_file_faults(self):
        """Red: a missing file or a directory crashes the check or passes, an empty file or a `to`
        past the last line passes, or a line names the wrong file or count."""
        self.write("src/empty.py", "")
        for value in ("src/missing.py", "src"):
            with self.subTest(path=value):
                self.assertFails(
                    self.changed(path=value),
                    "FAIL source app: path %s cannot be read under the data root" % value,
                )
        self.assertFails(
            self.changed(path="src/empty.py", **{"from": 1, "to": 1}),
            "FAIL source app: to 1 is outside src/empty.py (0 lines)",
        )
        self.assertFails(
            self.changed(**{"from": 70, "to": 73}),
            "FAIL source app: to 73 is outside src/app.py (72 lines)",
        )

    def test_count_line_does_not_stop_the_later_faults(self):
        """Red: a range over the limit stops the entry, so a path outside the root, an unreadable path
        or a `to` past the last line is not reported with it; or the count line comes after it."""
        count = "FAIL source app: range 1-25 is 25 lines (max 20, film)"
        self.assertFails(
            self.changed(path="../x.py", **{"from": 1, "to": 25}),
            count,
            'FAIL source app: path "../x.py" must be a relative path inside the data root',
        )
        self.assertFails(
            self.changed(path="src/missing.py", **{"from": 1, "to": 25}),
            count,
            "FAIL source app: path src/missing.py cannot be read under the data root",
        )
        self.assertFails(
            self.changed(path="src/wide.py", **{"from": 1, "to": 25}),
            count,
            "FAIL source app: to 25 is outside src/wide.py (4 lines)",
        )

    def test_source_last_line_without_a_final_newline(self):
        """Red: a file with no newline after its last line loses that line (the splitter drops the
        last entry whether or not it is empty)."""
        self.write("src/three.py", "one\ntwo\nthree")
        self.assertPasses(self.changed(path="src/three.py", **{"from": 3, "to": 3}))

    def test_source_with_crlf_line_ends(self):
        """Red: a carriage return is a line end of its own (a three-line CRLF file reads as six), or
        the empty entry after the final CRLF counts as a line."""
        self.write("src/crlf.py", "one\r\ntwo\r\nthree\r\n")
        self.assertPasses(self.changed(path="src/crlf.py", **{"from": 3, "to": 3}))
        self.assertFails(
            self.changed(path="src/crlf.py", **{"from": 4, "to": 4}),
            "FAIL source app: to 4 is outside src/crlf.py (3 lines)",
        )

    def test_source_with_a_nul_byte(self):
        """Red: the NUL byte is looked for only in the declared lines, is not looked for, or does
        not stop the entry (a `to` past the last line is reported with it)."""
        self.write("src/nul.py", "one\ntwo\nthree\nfo\0ur\n")
        self.assertFails(
            self.changed(path="src/nul.py", **{"from": 1, "to": 2}),
            "FAIL source app: src/nul.py has a NUL byte",
        )
        self.assertFails(
            self.changed(path="src/nul.py", **{"from": 1, "to": 9}),
            "FAIL source app: src/nul.py has a NUL byte",
        )

    def test_two_faulty_sources_and_a_faulty_scene(self):
        """Red: the lines come in another order than the sources in script order, then the scene, or
        the first faulty source stops the check of the next."""
        script = film_script()
        script["sources"] = [
            {"id": "app", "path": "src/app.py", "from": 0, "to": 10},
            {"id": "wide", "path": "src/missing.py", "from": 1, "to": 2},
        ]
        script["scenes"][1]["pause"] = 5
        self.assertFails(
            self.check(script),
            "FAIL source app: range 0-10 is not a valid line range",
            "FAIL source wide: path src/missing.py cannot be read under the data root",
            "FAIL scene forms: pause 5 must be an integer from 12 to 90",
        )

    def test_source_lines_come_after_the_header_and_before_the_scene_count(self):
        """Red: the source lines come before the header lines or after the scene count."""
        script = film_script()
        del script["title"]
        script["sources"][0]["to"] = 99
        script["scenes"] = script["scenes"][:2]
        self.assertFails(
            self.check(script),
            "FAIL script: title must be a string",
            "FAIL source app: range 3-99 is 97 lines (max 20, film)",
            "FAIL source app: to 99 is outside src/app.py (72 lines)",
            "FAIL script: 2 scenes (needs 3 to 30, film)",
        )

    def test_sources_are_not_checked_for_another_format(self):
        """Red: the source rules run for every format, so `sources: 5` of a brainrot or explainer
        script adds "sources must be an array" to its unexpected-key line."""
        for make in (brainrot_script, base_script):
            with self.subTest(make=make.__name__):
                script = make()
                script["sources"] = 5
                self.assertFails(self.check(script), 'FAIL script: unexpected key "sources"')


if __name__ == "__main__":
    unittest.main()
