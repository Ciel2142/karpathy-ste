"""Tests for the brainrot format of video/build-timeline.mjs: the `format` key, the per-format
limits and (in later tasks) build mode. Each test names the mutation that turns it red."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_video_timeline import VideoCase, base_script


def brainrot_script():
    """base_script() with format brainrot; its fixture already fits every brainrot limit."""
    script = base_script()
    script["format"] = "brainrot"
    return script


class TestBrainrotCheck(VideoCase):
    def test_unknown_format_fails(self):
        """Red: the format value is not validated, so a typo passes as explainer."""
        script = base_script()
        script["format"] = "vertical"
        self.assertFails(self.check(script), "FAIL script: format must be explainer or brainrot")

    def test_explicit_explainer_format_passes(self):
        """Red: `format` is an unexpected key, or "explainer" is rejected."""
        script = base_script()
        script["format"] = "explainer"
        result = self.check(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_brainrot_fixture_passes(self):
        """Red: the brainrot row is stricter than the fixture, or the format key is rejected."""
        result = self.check(brainrot_script())
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_brainrot_six_scenes_pass(self):
        """Red: brainrot maxScenes below 6."""
        script = brainrot_script()
        script["scenes"] = self.scenes_of(script, 6)
        result = self.check(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_brainrot_seven_scenes_fail(self):
        """Red: the brainrot scene-count range still reads the explainer 3 to 8."""
        script = brainrot_script()
        script["scenes"] = self.scenes_of(script, 7)
        self.assertFails(self.check(script), "FAIL script: 7 scenes (needs 3 to 6, brainrot)")

    def test_brainrot_code_40_columns_pass(self):
        """Red: the brainrot column limit below 40."""
        result = self.check(self.script_with_code_file("x" * 40))
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_brainrot_code_41_columns_fail(self):
        """Red: the code column check still reads the explainer 72."""
        self.assertFails(
            self.check(self.script_with_code_file("x" * 41)),
            "FAIL scene code: line 3 is 41 columns (max 40, brainrot)",
        )

    def test_brainrot_code_15_lines_fail(self):
        """Red: the code line check loses the brainrot tag."""
        script = brainrot_script()
        self.scene(script, "code")["props"]["source"] = {"path": "src/app.py", "from": 1, "to": 15}
        self.assertFails(
            self.check(script), "FAIL scene code: source range 1-15 is 15 lines (max 14, brainrot)"
        )

    def test_brainrot_narration_46_words_fail(self):
        """Red: the narration word check loses the brainrot tag."""
        script = brainrot_script()
        self.scene(script, "intro")["narration"] += " " + " ".join(["more"] * 38)
        self.assertFails(
            self.check(script), "FAIL scene intro: narration is 46 words (max 45, brainrot)"
        )

    def test_explainer_lines_carry_no_tag_when_format_is_explicit(self):
        """Red: the tag is added for an explicit explainer format."""
        script = base_script()
        script["format"] = "explainer"
        script["scenes"] = self.scenes_of(script, 9)
        self.assertFails(self.check(script), "FAIL script: 9 scenes (needs 3 to 8)")

    # -- helpers --

    def scenes_of(self, script, count):
        """`count` scenes: the three fixture scenes, then renamed copies of the first."""
        scenes = copy.deepcopy(script["scenes"][:3])
        while len(scenes) < count:
            extra = copy.deepcopy(script["scenes"][0])
            extra["id"] = "extra-%d" % len(scenes)
            scenes.append(extra)
        return scenes[:count]

    def script_with_code_file(self, line_3):
        """A brainrot script whose code scene reads src/narrow.py, line 3 being `line_3`."""
        lines = ["short"] * 10
        lines[2] = line_3
        self.write("src/narrow.py", "\n".join(lines) + "\n")
        script = brainrot_script()
        self.scene(script, "code")["props"]["source"] = {"path": "src/narrow.py", "from": 1, "to": 10}
        return script


if __name__ == "__main__":
    unittest.main()
