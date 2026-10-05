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


if __name__ == "__main__":
    unittest.main()
