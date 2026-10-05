"""Tests for the film format of video/build-timeline.mjs: the formats.json row, the script
check (--check) and build mode. Each test names the mutation that turns it red."""

import copy
import json
import math
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_video_timeline import APP_LINES, EXPLAIN, FLOW_NARRATION, TOOL, VideoCase, base_script, cite
from test_video_timeline_brainrot import BrainrotBuildCase, brainrot_script, words_for

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
}
FORMAT_LINE = "FAIL script: format must be film or brainrot"


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
        """Red: `film` is not a known format (the check prints the format line), or the film check is
        stricter than its own fixture."""
        result = self.check(film_script())
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_film_row_values(self):
        """Red: a value of the film row of formats.json changed, or the row is missing."""
        rows = json.loads(FORMATS.read_text(encoding="utf-8"))
        self.assertEqual(rows["film"], FILM_ROW)

    def test_film_scene_count(self):
        """Red: the film scene range reads another row (30 scenes fail), or the line loses the film
        tag, or the range is exclusive at an end."""
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
        """Red: any string is accepted as a format (the format line is gone), or the rest of the
        script is not validated as a film (its `sources` key is unexpected, its scenes lack a
        component)."""
        script = film_script()
        script["format"] = "slides"
        self.assertFails(self.check(script), FORMAT_LINE)

    def test_an_invalid_format_is_validated_as_a_film(self):
        """Red: the rest of a script with an invalid format is validated by another row than the
        film's (another scene range, or no film tag), or the format line is gone."""
        script = film_script()
        script["format"] = "vertical"
        script["scenes"] = self.scenes_of(script, 31)
        self.assertFails(self.check(script), FORMAT_LINE, "FAIL script: 31 scenes (needs 3 to 30, film)")

    def test_brainrot_refuses_the_film_keys(self):
        """Red: `sources` is an allowed top-level key, or `pause` an allowed scene key, for every
        format and not for film alone."""
        script = brainrot_script()
        script["sources"] = []
        self.assertFails(self.check(script), 'FAIL script: unexpected key "sources"')
        script = brainrot_script()
        self.scene(script, "intro")["pause"] = 12
        self.assertFails(self.check(script), 'FAIL scene intro: unexpected key "pause"')

    def check_with_formats(self, rows, script):
        """--check of `script` by a copy of the tool that has `rows` as its own formats.json."""
        tool_dir = Path(self.dir) / "tool"  # a copy of the tool, with its own formats.json beside it
        tool_dir.mkdir()
        shutil.copy(TOOL, tool_dir / TOOL.name)
        (tool_dir / "formats.json").write_text(json.dumps(rows), encoding="utf-8")
        path = self.write_json("script.json", script)
        return subprocess.run(
            ["node", str(tool_dir / TOOL.name), "--check", path, "--root", self.dir],
            capture_output=True,
            text=True,
            cwd=self.dir,
        )

    def test_formats_file_without_the_film_row_fails_cleanly(self):
        """Red: the loader does not want the film row (a formats.json without film is accepted and
        the film check then reads an undefined row), or the cause text is not the two-row one."""
        rows = json.loads(FORMATS.read_text(encoding="utf-8"))
        del rows["film"]
        result = self.check_with_formats(rows, film_script())
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(
            result.stdout,
            "FAIL script: cannot read formats.json: expected an object with a film and a brainrot row\n",
        )
        self.assertEqual(result.stderr, "")

    def test_an_explainer_row_does_not_make_a_format(self):
        """Red: knownFormat reads the rows of formats.json (has(FORMATS, format)), so a stale row
        of the removed format makes its name valid again. The copy of the tool has the two real
        rows and a third, a copy of the brainrot row."""
        rows = json.loads(FORMATS.read_text(encoding="utf-8"))
        rows["explainer"] = copy.deepcopy(rows["brainrot"])
        script = film_script()
        script["format"] = "explainer"
        self.assertFails(self.check_with_formats(rows, script), FORMAT_LINE)


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
        """Red: the source rules run for every format, so `sources: 5` of a brainrot script adds
        "sources must be an array" to its unexpected-key line."""
        script = brainrot_script()
        script["sources"] = 5
        self.assertFails(self.check(script), 'FAIL script: unexpected key "sources"')


def js_round(value):
    """Math.round of JavaScript: a half rounds up."""
    return math.floor(value + 0.5)


class FilmBuildCase(VideoCase):
    """Build-mode fixtures of a film: a words file for every scene, next to durations.json. The
    words are half a second long with half a second between sentences, so the clips of
    film_script() last 4.5 s, 8.0 s and 5.0 s."""

    write_words = BrainrotBuildCase.write_words

    def write_film_words(self, script, engine="say"):
        """Write <id>.<engine>.words.json for every scene that has an id and a narration; return
        the clip seconds of each scene (the end of its last word)."""
        clips = {}
        for scene in script["scenes"]:
            if not (isinstance(scene, dict) and isinstance(scene.get("id"), str)):
                continue
            if not isinstance(scene.get("narration"), str):
                continue
            words = words_for(scene["narration"], 0.5, 0.5)
            self.write_words(scene["id"], engine, words)
            clips[scene["id"]] = words["words"][-1]["to"]
        return clips

    def build_film(self, script, seconds=None, engine="say"):
        """Build `script` with the words files of write_film_words; `seconds` (a clip length per
        scene id) defaults to the end of each scene's last word. Returns (result, timeline)."""
        clips = self.write_film_words(script, engine)
        return self.build(script, clips if seconds is None else seconds, engine)

    def build_film_without_root(self, script):
        """Build `script` as build_film does but pass no --root. Returns (result, timeline)."""
        clips = self.write_film_words(script)
        script_path = self.write_json("script.json", script)
        durations = self.write_json("durations.json", {"engine": "say", "fallback": None, "scenes": clips})
        out = os.path.join(self.dir, "out", "timeline.json")
        result = self.node(script_path, durations, "say", out)
        timeline = None
        if os.path.exists(out):
            with open(out, encoding="utf-8") as handle:
                timeline = json.load(handle)
        return result, timeline


class TestFilmBuild(FilmBuildCase):
    def built(self, script=None, **kwargs):
        """The timeline of a build that must succeed."""
        result, timeline = self.build_film(script or film_script(), **kwargs)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        return timeline

    def test_film_top_level_values(self):
        """Red: build mode keeps the canvas or budgets of another row for a film, totalFrames
        is not the sum of the scenes, the engine is not written, `sources` or `checkFrames` is
        missing, or the timeline gains a key such as `background`."""
        timeline = self.built()
        self.assertEqual(
            (timeline["format"], timeline["fps"], timeline["width"], timeline["height"]),
            ("film", 30, 1280, 720),
        )
        self.assertEqual((timeline["maxSceneSeconds"], timeline["maxTotalSeconds"]), (30, 150))
        self.assertEqual(timeline["engine"], "say")
        self.assertEqual(timeline["totalFrames"], 597)
        self.assertEqual(
            sorted(timeline),
            sorted(
                ["format", "fps", "width", "height", "totalFrames", "maxSceneSeconds",
                 "maxTotalSeconds", "engine", "sources", "checkFrames", "scenes"]
            ),
        )

    def test_a_script_without_the_key_is_a_film(self):
        """Red: a script without the key is validated or built by another row than the film's: the
        check prints lines (its scenes lack a component, its `sources` is unexpected), or the build
        fails, writes another format or no checkFrames."""
        script = film_script()
        del script["format"]
        result = self.check(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        keyed = self.built()
        timeline = self.built(script)
        self.assertEqual(timeline["format"], "film")
        self.assertEqual(timeline["checkFrames"], keyed["checkFrames"])
        self.assertEqual(timeline, keyed)

    def test_json_that_is_not_an_object_builds_as_a_film(self):
        """Red: build mode reads JSON that is not an object as another format than the film (a
        timeline without sources or checkFrames), or crashes on it (null has no own keys)."""
        for value in (None, [], 3):
            with self.subTest(value=value):
                result, timeline = self.build(value, {})
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
                self.assertEqual(
                    (timeline["format"], timeline["sources"], timeline["checkFrames"], timeline["scenes"]),
                    ("film", {}, [], []),
                )

    def test_film_scene_is_lead_audio_pause(self):
        """Red: the scene length drops the lead, the clip or the pause, the pause of `forms` (30) is
        ignored for the row's 12, the tail of the brainrot row (12) is added instead, the clip is
        rounded instead of ceilinged, or `from` is not the sum of the scenes before."""
        scenes = self.built()["scenes"]
        self.assertEqual([s["durationInFrames"] for s in scenes], [153, 276, 168])
        self.assertEqual([s["from"] for s in scenes], [0, 153, 429])
        self.assertEqual([s["leadFrames"] for s in scenes], [6, 6, 6])
        self.assertEqual([s["audioFrames"] for s in scenes], [135, 240, 150])
        self.assertEqual(scenes[0]["audio"], "audio/type.say.wav")
        # A clip of 4.51 s is 135.3 frames: the audio lasts 136 (ceiling), not 135 (rounding).
        scenes = self.built(seconds={"type": 4.51, "forms": 8.0, "ends": 5.0})["scenes"]
        self.assertEqual([s["audioFrames"] for s in scenes], [136, 240, 150])
        self.assertEqual([s["durationInFrames"] for s in scenes], [154, 276, 168])
        self.assertEqual([s["from"] for s in scenes], [0, 154, 430])

    def test_film_scene_keys(self):
        """Red: a film scene carries a key of a component scene (component, props, cueFrames,
        captions), carries the pause, or loses one of its own keys."""
        for scene in self.built()["scenes"]:
            self.assertEqual(
                sorted(scene),
                sorted(["id", "from", "durationInFrames", "leadFrames", "audioFrames", "audio", "sentences", "words"]),
            )

    def test_film_sentence_frames(self):
        """Red: a sentence frame misses the lead (0, 90, ...), or uses the seconds of the sentence
        end or the clip length instead of its start. Every time of this fixture is a multiple of
        0.5 s, so the rounding is not exercised here: test_film_frames_round_half_up does."""
        script = film_script()
        scenes = self.built(script)["scenes"]
        self.assertEqual([s["sentences"] for s in scenes], [[6, 96], [6, 81, 186], [6, 96]])
        for scene, source in zip(scenes, script["scenes"]):
            sentences = words_for(source["narration"], 0.5, 0.5)["sentences"]
            self.assertEqual(scene["sentences"], [6 + js_round(s["from"] * 30) for s in sentences])

    def test_film_word_frames(self):
        """Red: a word frame misses the lead, the `to` of a word is the next word's start (the words
        inside a sentence touch, so only a sentence-final word shows it: 96 for 81 below), the words are
        the caption chunks (up to three words each), or the text loses its backticks. The rounding
        of `to` is test_film_frames_round_half_up's."""
        scenes = self.built()["scenes"]
        words = scenes[0]["words"]
        self.assertEqual(words[0], {"text": "The", "from": 6, "to": 21})
        # The sentence ends at 2.5 s (frame 81); the next word starts at 3.0 s (frame 96).
        self.assertEqual(words[4], {"text": "handler.", "from": 66, "to": 81})
        self.assertEqual(words[-1], {"text": "replies.", "from": 126, "to": 141})
        script = film_script()
        script["scenes"][0]["narration"] = "Run `verify.sh` first. Then read the output."
        words = self.built(script)["scenes"][0]["words"]
        self.assertEqual([w["text"] for w in words], script["scenes"][0]["narration"].split())
        self.assertIn("`verify.sh`", [w["text"] for w in words])

    def test_film_frames_round_half_up(self):
        """Red: a sentence frame or a word frame (from or to) is floored or ceilinged instead of
        rounded half up. 0.25, 0.75 and 1.25 s are exactly 7.5, 22.5 and 37.5 frames (exact in
        binary floating point, so true halves: floor gives 7, 22, 37); 1.01 s is 30.3 frames (ceiling
        gives 31); 1.02 s is 30.6 (floor gives 30). The sentences start at 0.25 s and 1.01 s, so each
        of floor and ceiling is caught on the sentence frames alone, and on the word `from`s alone;
        the word `to`s are 0.75 s, 1.01 s, 1.02 s and 1.25 s, so floor is caught on them alone (22.5,
        30.6 and 37.5 give 22, 30, 37 for 23, 31, 38) and so is ceiling (the 1.01 s of the second
        word gives 37 for 36)."""
        script = film_script()
        script["scenes"][0]["narration"] = "Aa bb. Cc dd."
        clips = self.write_film_words(script)
        times = [(0.25, 0.75), (0.75, 1.01), (1.01, 1.02), (1.02, 1.25)]
        words = [
            {"text": text, "from": start, "to": end}
            for text, (start, end) in zip(script["scenes"][0]["narration"].split(), times)
        ]
        sentences = [{"from": 0.25, "to": 1.01}, {"from": 1.01, "to": 1.25}]
        self.write_words("type", "say", {"sentences": sentences, "words": words})
        clips["type"] = 1.5
        result, timeline = self.build(script, clips)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        scene = timeline["scenes"][0]
        self.assertEqual(scene["sentences"], [14, 36])
        self.assertEqual([(w["from"], w["to"]) for w in scene["words"]], [(14, 29), (29, 36), (36, 37), (37, 44)])
        self.assertEqual(scene["sentences"], [6 + js_round(s["from"] * 30) for s in sentences])
        self.assertEqual(
            [(w["from"], w["to"]) for w in scene["words"]],
            [(6 + js_round(w["from"] * 30), 6 + js_round(w["to"] * 30)) for w in words],
        )

    def test_film_one_sentence_without_an_end_mark(self):
        """Red: a narration whose last sentence has no end mark yields no sentence frame, or one too
        many."""
        script = film_script()
        script["scenes"][0]["narration"] = "No end mark here"
        self.assertEqual(self.built(script)["scenes"][0]["sentences"], [6])

    def test_film_reads_the_words_file_of_the_engine(self):
        """Red: build mode reads <id>.say.words.json whatever the engine, or the audio name keeps the
        say suffix; with no words file the cause is not the read error naming that file."""
        script = film_script()
        clips = self.write_film_words(script)
        os.remove(os.path.join(self.dir, "type.say.words.json"))
        result, timeline = self.build(script, clips)
        self.assertFails(result, "FAIL scene type: cannot read type.say.words.json: ENOENT")
        self.assertIsNone(timeline)
        timeline = self.built(engine="kokoro")
        self.assertEqual(timeline["engine"], "kokoro")
        self.assertEqual(timeline["scenes"][0]["audio"], "audio/type.kokoro.wav")

    def test_film_words_file_faults(self):
        """Red: a words file with a word fewer is accepted, a words file with no sentence yields a
        scene with no sentence frame, or the line names another file or count."""
        script = film_script()
        clips = self.write_film_words(script)
        words = words_for(script["scenes"][0]["narration"], 0.5, 0.5)
        words["words"].pop(3)
        self.write_words("type", "say", words)
        result, timeline = self.build(script, clips)
        self.assertFails(result, "FAIL scene type: type.say.words.json has 7 words, the narration has 8")
        self.assertIsNone(timeline)
        words = words_for(script["scenes"][0]["narration"], 0.5, 0.5)
        words["sentences"] = []
        self.write_words("type", "say", words)
        result, timeline = self.build(script, clips)
        self.assertFails(result, "FAIL scene type: type.say.words.json has no sentences")
        self.assertIsNone(timeline)

    def test_film_build_faults(self):
        """Red: a missing or non-positive duration builds, a pause that is not an integer from 12 to
        90 builds, a scene that is not an object crashes the build or is skipped, or the film is
        written although a scene failed."""
        script = film_script()
        result, timeline = self.build_film(script, seconds={"forms": 8.0, "ends": 5.0})
        self.assertFails(result, "FAIL scene type: no duration in durations.json")
        self.assertIsNone(timeline)
        for value in (0, -1, "4"):
            with self.subTest(duration=value):
                result, timeline = self.build_film(script, seconds={"type": value, "forms": 8.0, "ends": 5.0})
                self.assertFails(
                    result, "FAIL scene type: duration %s must be a positive number of seconds" % json.dumps(value)
                )
        script = film_script()
        script["scenes"][1]["pause"] = "12"
        result, timeline = self.build_film(script)
        self.assertFails(result, 'FAIL scene forms: pause "12" must be an integer from 12 to 90')
        self.assertIsNone(timeline)
        broken = ((7, "#1"), (None, "#1"), ([], "#1"), ({"id": "type"}, "type"), ({"narration": "A."}, "#1"))
        for value, where in broken:
            with self.subTest(scene=value):
                script = film_script()
                script["scenes"][0] = value
                result, timeline = self.build_film(script)
                self.assertFails(result, "FAIL scene %s: needs id and narration to build" % where)
                self.assertIsNone(timeline)

    def test_film_scene_id_constructor(self):
        """Red: the duration of a scene is read with a plain lookup, so a scene called `constructor`
        takes the inherited function as its duration; or the scene id pattern refuses it."""
        script = film_script()
        script["scenes"][0]["id"] = "constructor"
        result, timeline = self.build_film(script, seconds={"forms": 8.0, "ends": 5.0})
        self.assertFails(result, "FAIL scene constructor: no duration in durations.json")
        self.assertIsNone(timeline)
        scene = self.built(script)["scenes"][0]
        self.assertEqual((scene["id"], scene["audio"]), ("constructor", "audio/constructor.say.wav"))


    def sourced(self, name, text, **changes):
        """A film script whose one source `app` reads lines 1 to 3 of src/<name>, a file written now
        with `text`; `changes` set other keys of that source."""
        self.write("src/" + name, text)
        script = film_script()
        script["sources"] = [dict({"id": "app", "path": "src/" + name, "from": 1, "to": 3}, **changes)]
        return script

    def test_film_sources_lines(self):
        """Red: `sources` stays {} or null, a source holds the lines from the wrong offset (the slice
        starts at `from` instead of `from - 1`, or ends before `to`), `from` is written 0-based, `to`
        or the id is written into the entry, or the entry loses its path."""
        self.assertEqual(
            self.built()["sources"],
            {"app": {"path": "src/app.py", "from": 3, "lines": APP_LINES[2:10]}},
        )

    def test_film_sources_follow_the_script(self):
        """Red: the sources are written in another order than the script's (here reversed), or only the
        first of two is kept."""
        script = film_script()
        script["sources"].append({"id": "head", "path": "src/app.py", "from": 1, "to": 2})
        sources = self.built(script)["sources"]
        self.assertEqual(list(sources), ["app", "head"])
        self.assertEqual(sources["head"], {"path": "src/app.py", "from": 1, "lines": APP_LINES[0:2]})
        self.assertEqual(sources["app"]["lines"], APP_LINES[2:10])

    def test_film_sources_expand_tabs(self):
        """Red: a tab stays in a line, becomes one space or eight, or only the first tab of a line is
        replaced (the second case has three tabs in one line)."""
        script = film_script()
        script["sources"] = [{"id": "app", "path": "src/wide.py", "from": 3, "to": 3}]
        self.assertEqual(self.built(script)["sources"]["app"]["lines"], ["x" * 69 + " " * 4])
        script = self.sourced("tabs.py", "\tif x:\n\t\treturn\ta\nend\n")
        self.assertEqual(
            self.built(script)["sources"]["app"]["lines"],
            [" " * 4 + "if x:", " " * 8 + "return" + " " * 4 + "a", "end"],
        )

    def test_film_sources_strip_crlf(self):
        """Red: a line keeps its carriage return, or a CRLF file reads as twice the lines (it is split at
        the `\\r` as well as at the `\\n`)."""
        script = self.sourced("crlf.py", "one\r\ntwo\r\nthree\r\n")
        lines = self.built(script)["sources"]["app"]["lines"]
        self.assertEqual(lines, ["one", "two", "three"])
        self.assertFalse(any("\r" in line for line in lines))

    def test_film_sources_drop_a_leading_byte_order_mark(self):
        """Red: line 1 of a file that starts with a BOM (U+FEFF, which the kit draws as a column)
        keeps it, the check refuses such a file, or every U+FEFF of the file goes (the one inside
        line 2 must stay)."""
        script = self.sourced("bom.py", "\ufeffone\ntwo \ufefftwo\nthree\n")
        result = self.check(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        lines = self.built(script)["sources"]["app"]["lines"]
        self.assertEqual(lines, ["one", "two \ufefftwo", "three"])

    def test_film_sources_last_line_without_a_final_newline(self):
        """Red: a file with no newline after its last line loses that line (the splitter drops the last
        entry whether or not it is empty), or that line keeps a carriage return."""
        script = self.sourced("bare.py", "one\ntwo\nthree")
        self.assertEqual(self.built(script)["sources"]["app"]["lines"], ["one", "two", "three"])
        script = self.sourced("bare-crlf.py", "one\r\ntwo\r\nthree")
        self.assertEqual(self.built(script)["sources"]["app"]["lines"], ["one", "two", "three"])

    def test_film_without_sources(self):
        """Red: `sources` is written as null (or left out) when the script has none, whether the key is
        absent or the array is empty."""
        script = film_script()
        del script["sources"]
        self.assertEqual(self.built(script)["sources"], {})
        script["sources"] = []
        self.assertEqual(self.built(script)["sources"], {})

    def test_film_without_sources_builds_without_root(self):
        """Red: a film with no `sources` (absent or []) asks for --root, or reads under an undefined
        root and fails."""
        absent = film_script()
        del absent["sources"]
        empty = film_script()
        empty["sources"] = []
        for name, script in (("absent", absent), ("empty", empty)):
            with self.subTest(sources=name):
                result, timeline = self.build_film_without_root(script)
                self.assertEqual((result.returncode, result.stdout), (0, ""))
                self.assertEqual(timeline["sources"], {})

    def test_film_source_id_constructor(self):
        """Red: the sources are kept in an object that is tested with `in` (or a plain lookup) before an
        entry is written, so a source called `constructor`, which Object.prototype already has, is
        skipped."""
        script = film_script()
        script["sources"][0]["id"] = "constructor"
        sources = self.built(script)["sources"]
        self.assertIn("constructor", sources)
        self.assertEqual(
            sources, {"constructor": {"path": "src/app.py", "from": 3, "lines": APP_LINES[2:10]}}
        )

    def test_film_source_faults_in_build_mode(self):
        """Red: a source fault does not stop the build (a missing file builds, or the fault is dropped), or
        a build with no --root reads under an undefined root (the line would say "cannot be read under
        the data root")."""
        script = film_script()
        script["sources"][0]["path"] = "src/none.py"
        result, timeline = self.build_film(script)
        self.assertFails(result, "FAIL source app: path src/none.py cannot be read under the data root")
        self.assertIsNone(timeline)
        script = film_script()
        result, timeline = self.build_film_without_root(script)
        self.assertFails(result, "FAIL source app: cannot read source lines (needs --root)")
        self.assertIsNone(timeline)

    def test_film_source_shape_faults_in_build_mode(self):
        """Red: build mode skips the shape rules of the source check, so a `sources` that is not an array,
        an entry that is not an object, a missing key, a bad id, a duplicate id or a path outside the
        root crashes the build with a stack trace or builds."""
        twin = film_script()["sources"][0]
        cases = (
            (5, ["FAIL script: sources must be an array"]),
            (None, ["FAIL script: sources must be an array"]),
            ([7], ["FAIL source #1: must be an object"]),
            ([{k: v for k, v in twin.items() if k != "to"}], ['FAIL source app: missing "to"']),
            ([dict(twin, id="App")], ['FAIL source #1: id "App" must match [a-z0-9-]']),
            ([twin, dict(twin)], ["FAIL source app: duplicate id"]),
            (
                [dict(twin, path="../x.py")],
                ['FAIL source app: path "../x.py" must be a relative path inside the data root'],
            ),
        )
        for sources, lines in cases:
            with self.subTest(sources=sources):
                script = film_script()
                script["sources"] = sources
                result, timeline = self.build_film(script)
                self.assertFails(result, *lines)
                self.assertEqual(result.stderr, "")
                self.assertIsNone(timeline)

    def test_film_source_and_scene_faults_are_all_reported(self):
        """Red: a source fault ends the build before the scenes are checked (or the scene fault ends it
        before the sources), so one of the two lines is missing; or the lines come in another order
        than the check's, sources first."""
        script = film_script()
        script["sources"][0]["path"] = "src/none.py"
        result, timeline = self.build_film(script, seconds={"forms": 8.0, "ends": 5.0})
        self.assertFails(
            result,
            "FAIL source app: path src/none.py cannot be read under the data root",
            "FAIL scene type: no duration in durations.json",
        )
        self.assertIsNone(timeline)

    def test_check_frames(self):
        """Red: a frame is taken at the sentence start or end instead of the middle, the middle is
        rounded up or taken of seconds instead of frames, the lead is left out of it, the scene's `from`
        is left out (every scene counts from 0), or the `end` frame is `from + durationInFrames`."""
        frames = self.built()["checkFrames"]
        self.assertEqual(
            [(c["frame"], c["scene"], c["still"]) for c in frames],
            [
                (43, "type", "s1"), (118, "type", "s2"), (152, "type", "end"),
                (189, "forms", "s1"), (279, "forms", "s2"), (369, "forms", "s3"), (428, "forms", "end"),
                (472, "ends", "s1"), (555, "ends", "s2"), (596, "ends", "end"),
            ],
        )

    def test_check_frames_invariants(self):
        """Red: the frames do not increase (a scene counts from 0), the last frame is not the last of the
        film (`totalFrames`, or one before the end of the last scene), a scene lacks its `end` entry or
        one of its sentences, or an entry carries a key beyond frame, scene and still."""
        script = film_script()
        timeline = self.built(script)
        frames = timeline["checkFrames"]
        numbers = [c["frame"] for c in frames]
        self.assertEqual(numbers, sorted(set(numbers)))
        self.assertEqual(numbers[-1], timeline["totalFrames"] - 1)
        for scene in script["scenes"]:
            sentences = words_for(scene["narration"], 0.5, 0.5)["sentences"]
            stills = [c["still"] for c in frames if c["scene"] == scene["id"]]
            self.assertEqual(len(stills), len(sentences) + 1, scene["id"])
            self.assertEqual(stills, ["s%d" % k for k in range(1, len(sentences) + 1)] + ["end"])
        for entry in frames:
            self.assertEqual(sorted(entry), ["frame", "scene", "still"])

    def test_check_frames_of_a_one_sentence_scene(self):
        """Red: a scene of one sentence gets no `s1` entry or no `end` entry. The narration with an end
        mark and the one without (its words file still ends its last sentence) give the same stills."""
        for narration in ("Only one sentence here.", "No end mark here"):
            with self.subTest(narration=narration):
                script = film_script()
                script["scenes"][0]["narration"] = narration
                frames = self.built(script)["checkFrames"]
                self.assertEqual([c["still"] for c in frames if c["scene"] == "type"], ["s1", "end"])

    def test_check_frames_use_the_rounded_frames(self):
        """Red: the middle of a sentence is taken of its seconds (the lead added to the rounded middle
        second: 8 for the first sentence, 25 for the second), or the start or the end is floored or
        ceilinged before the middle is taken, or the middle is rounded or ceilinged. The sentences
        run 0.01 to 0.11 s (scene frames 6 and 9, middle 7) and 0.35 to 0.95 s (0.35 s is exactly
        10.5 frames, so frames 17 and 35, middle 26); each of those variants gives another number
        for one of them."""
        script = film_script()
        script["scenes"][0]["narration"] = "Aa bb. Cc dd."
        clips = self.write_film_words(script)
        times = [(0.01, 0.06), (0.06, 0.11), (0.35, 0.65), (0.65, 0.95)]
        words = [
            {"text": text, "from": start, "to": end}
            for text, (start, end) in zip(script["scenes"][0]["narration"].split(), times)
        ]
        sentences = [{"from": 0.01, "to": 0.11}, {"from": 0.35, "to": 0.95}]
        self.write_words("type", "say", {"sentences": sentences, "words": words})
        clips["type"] = 1.0
        result, timeline = self.build(script, clips)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        first = [(c["frame"], c["still"]) for c in timeline["checkFrames"] if c["scene"] == "type"]
        self.assertEqual(first, [(7, "s1"), (26, "s2"), (47, "end")])


TYPES_HEADER = "// Generated by build-timeline.mjs --types from script.json. Do not edit."


def types_text(scenes, sources):
    """The whole file --types writes for these two lines of ids (each a ready-made union)."""
    return "\n".join(
        [
            TYPES_HEADER,
            'import type { FilmProps } from "../kit";',
            "export type SceneId = %s;" % scenes,
            "export type SourceId = %s;" % sources,
            "export type Props = FilmProps<SceneId, SourceId>;",
            "",
        ]
    )


class TestFilmTypes(VideoCase):
    def types(self, script, name="script.json"):
        """Run --types on `script` (a value, written as JSON to <dir>/<name>) and return
        (result, text of the output file or None when none was written)."""
        path = self.write_json(name, script)
        return self.types_of(path)

    def types_of(self, path, *extra):
        out = os.path.join(self.dir, "out", "script.gen.ts")
        result = self.node("--types", path, out, *extra)
        text = None
        if os.path.exists(out):
            with open(out, encoding="utf-8") as handle:
                text = handle.read()
        return result, text

    def assertTypesFails(self, script, *lines):
        """Exit 1, exactly these FAIL lines on stdout, and no output file."""
        result, text = self.types(script)
        self.assertFails(result, *lines)
        self.assertIsNone(text)

    def test_types_output(self):
        """Red: the file differs from the pinned five lines in any character (a name in the union, the
        separator, the import path, the generic arguments), loses its one final newline, the first
        line names the input file (here other.json) instead of the literal script.json, the ids
        are not in script order, or the run prints on stdout or exits non-zero."""
        result, text = self.types(film_script())
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(text, types_text('"type" | "forms" | "ends"', '"app"'))
        self.assertTrue(text.endswith("Props = FilmProps<SceneId, SourceId>;\n"))
        result, other = self.types(film_script(), name="other.json")
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(other, text)

    def test_types_without_sources(self):
        """Red: a script with no `sources` key, or with `[]`, writes an empty union (`export type
        SourceId = ;`) or no SourceId line, or fails for the missing key."""
        script = film_script()
        del script["sources"]
        result, text = self.types(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertIn("\nexport type SourceId = never;\n", text)
        script["sources"] = []
        result, text = self.types(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(text, types_text('"type" | "forms" | "ends"', "never"))

    def test_types_id_constructor(self):
        """Red: the ids are gathered in a plain object (or tested with `in`), so a scene or source id
        `constructor` is dropped from its union as an inherited key."""
        script = film_script()
        script["scenes"][0]["id"] = "constructor"
        script["sources"][0]["id"] = "constructor"
        result, text = self.types(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(text, types_text('"constructor" | "forms" | "ends"', '"constructor"'))

    def test_types_usage(self):
        """Red: --types accepts three positionals (or one), or goes on with --check or --root (the
        invocations below are valid for the check or for the mode without the extra flag)."""
        script = self.write_json("script.json", film_script())
        out = os.path.join(self.dir, "out", "script.gen.ts")
        cases = {
            "one positional": ["--types", script],
            "three positionals": ["--types", script, out, out],
            "with --check": ["--types", "--check", script, out],
            "with --check and --root": ["--types", "--check", script, "--root", self.dir],
            "with --root": ["--types", "--root", self.dir, script, out],
        }
        for name, args in cases.items():
            with self.subTest(name):
                if os.path.exists(out):
                    os.remove(out)  # a case that wrongly wrote it must not fail the next
                result = self.node(*args)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("usage:", result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertFalse(os.path.exists(out))

    def test_types_refuses_a_script_that_is_not_a_film(self):
        """Red: --types writes names for a brainrot script or for one whose format is another value
        (the name of the removed row), crashes on JSON that is not an object (null, an array, a
        number), or writes the file before it knows the script is a film."""
        film_line = "FAIL script: --types needs a film script"
        scripts = {}
        for value in ("brainrot", "explainer"):
            scripts[value] = film_script()
            scripts[value]["format"] = value
        scripts.update({"null": None, "array": [], "number": 3})
        for name, script in scripts.items():
            with self.subTest(name):
                self.assertTypesFails(script, film_line)

    def test_types_takes_a_script_without_the_key(self):
        """Red: --types reads a script without the key as another format than the film (it refuses
        it), or writes other names for it than for "format": "film"."""
        script = film_script()
        del script["format"]
        result, text = self.types(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(text, types_text('"type" | "forms" | "ends"', '"app"'))

    def test_types_script_that_cannot_be_read(self):
        """Red: a missing script file, or one that is not JSON, prints a stack trace or another line
        than readJson's, or writes the output file."""
        missing = os.path.join(self.dir, "none.json")
        result, text = self.types_of(missing)
        self.assertFails(result, "FAIL script: cannot read script %s: ENOENT" % missing)
        self.assertIsNone(text)
        broken = self.write("broken.json", "{")
        result, text = self.types_of(broken)
        self.assertEqual((result.returncode, result.stdout.count("\n")), (1, 1))
        self.assertTrue(
            result.stdout.startswith("FAIL script: script %s is not valid JSON: " % broken), result.stdout
        )
        self.assertIsNone(text)

    def test_types_refuses_scenes_or_sources_that_are_not_arrays(self):
        """Red: `scenes` that is missing, null or an object is read as a list (a crash or an empty
        union), a `sources` that is present and not an array is skipped, or `sources: null` is
        taken as absent."""
        for name, mutate, line in [
            ("scenes missing", lambda s: s.pop("scenes"), "FAIL script: scenes must be an array"),
            ("scenes object", lambda s: s.update(scenes={}), "FAIL script: scenes must be an array"),
            ("scenes null", lambda s: s.update(scenes=None), "FAIL script: scenes must be an array"),
            ("sources object", lambda s: s.update(sources={}), "FAIL script: sources must be an array"),
            ("sources null", lambda s: s.update(sources=None), "FAIL script: sources must be an array"),
            ("sources string", lambda s: s.update(sources="app"), "FAIL script: sources must be an array"),
        ]:
            with self.subTest(name):
                script = film_script()
                mutate(script)
                self.assertTypesFails(script, line)

    def test_types_refuses_a_bad_id(self):
        """Red: a scene id that would close the string it is written into (`a" | "b`) is written, or a
        source id that is not [a-z0-9-] (`A`) is; an id that is not a string, an empty one, one
        that starts with a dash passes, an entry that is not an object (a string, a number, null)
        passes or crashes the run; a line names the scene or
        source by id instead of by #<n> (1-based), or the lines are not scenes first, in script order."""
        script = film_script()
        script["scenes"][0]["id"] = 'a" | "b'
        self.assertTypesFails(script, "FAIL scene #1: id must match [a-z0-9-]")
        script = film_script()
        script["sources"][0]["id"] = "A"
        self.assertTypesFails(script, "FAIL source #1: id must match [a-z0-9-]")
        script = film_script()
        script["scenes"][1] = "forms"
        script["scenes"][2]["id"] = 7
        script["scenes"].append({})
        script["scenes"].append({"id": ""})
        script["scenes"].append({"id": "-lead"})
        script["scenes"].append({"id": "ok"})
        script["scenes"].append(None)
        script["sources"] = [{"id": "app"}, 5, {"id": "Bad"}, {}, {"id": "app-2"}, None]
        self.assertTypesFails(
            script,
            "FAIL scene #2: id must match [a-z0-9-]",
            "FAIL scene #3: id must match [a-z0-9-]",
            "FAIL scene #4: id must match [a-z0-9-]",
            "FAIL scene #5: id must match [a-z0-9-]",
            "FAIL scene #6: id must match [a-z0-9-]",
            "FAIL scene #8: id must match [a-z0-9-]",
            "FAIL source #2: id must match [a-z0-9-]",
            "FAIL source #3: id must match [a-z0-9-]",
            "FAIL source #4: id must match [a-z0-9-]",
            "FAIL source #6: id must match [a-z0-9-]",
        )

    def test_types_runs_no_other_check(self):
        """Red: --types runs a rule of --check (the scene count, the unique ids, a missing narration or
        an unexpected key, a source's path or range), reads a source file or --root, or dedupes
        the ids; zero scenes or sources gives something other than `never`."""
        script = film_script()
        script["scenes"] = [
            {"id": "one", "component": "title", "props": {}, "pause": 1, "extra": True},
            {"id": "one"},
        ]
        script["sources"] = [{"id": "gone", "path": "no/such/file.py", "from": 9, "to": 2}, {"id": "gone"}]
        script["title"] = 5
        result, text = self.types(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(text, types_text('"one" | "one"', '"gone" | "gone"'))
        script["scenes"] = []
        script["sources"] = []
        result, text = self.types(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(text, types_text("never", "never"))

    def test_types_cannot_write(self):
        """Red: a failed write is reported with another code or message than the error's own code
        (ENOTDIR), with no FAIL line (a stack trace) or with exit 0."""
        script = self.write_json("script.json", film_script())
        blocker = self.write("blocker", "a regular file")
        out = os.path.join(blocker, "sub", "script.gen.ts")
        result = self.node("--types", script, out)
        self.assertFails(result, "FAIL script: cannot write %s: ENOTDIR" % out)

    def test_types_creates_the_output_directory(self):
        """Red: the parent directory of the output is not created, so the first run into a fresh
        directory fails."""
        script = self.write_json("script.json", film_script())
        out = os.path.join(self.dir, "a", "b", "script.gen.ts")
        result = self.node("--types", script, out)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertTrue(os.path.isfile(out))


if __name__ == "__main__":
    unittest.main()
