"""Tests for the brainrot format of video/build-timeline.mjs: the `format` key, the per-format
limits and (in later tasks) build mode. Each test names the mutation that turns it red."""

import copy
import json
import os
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


def words_for(narration, seconds_per_word=0.3, pause=0.15):
    """A consistent words.json object (spec 5.2) for `narration`: one word per whitespace token,
    words back to back, `pause` seconds between sentences. A sentence ends after a token that
    ends in ., ? or !, and at the last token. Seconds are rounded to 6 places."""
    tokens = narration.split()
    words, sentences = [], []
    t, start = 0.0, 0.0
    for i, token in enumerate(tokens):
        words.append({"text": token, "from": round(t, 6), "to": round(t + seconds_per_word, 6)})
        t += seconds_per_word
        if token[-1] in ".?!" or i == len(tokens) - 1:
            sentences.append({"from": round(start, 6), "to": round(t, 6)})
            t += pause
            start = t
    return {"sentences": sentences, "words": words}


class BrainrotBuildCase(VideoCase):
    """Build-mode fixtures: a brainrot build needs one words.json per scene next to durations.json."""

    def write_words(self, scene_id, engine, words_json):
        """Write <scene_id>.<engine>.words.json beside durations.json."""
        return self.write_json("%s.%s.words.json" % (scene_id, engine), words_json)

    def build_brainrot(self, script, seconds, engine="say"):
        """Build `script` with a words file for every scene that has a narration."""
        for scene in script["scenes"]:
            self.write_words(scene["id"], engine, words_for(scene["narration"]))
        return self.build(script, seconds, engine)

    def two_scene_brainrot(self):
        script = brainrot_script()
        script["scenes"] = script["scenes"][:2]
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

    def test_invalid_format_values_fail_with_the_format_line(self):
        """Red: knownFormat accepts null, a number, an inherited name or a differently cased name."""
        for value in (None, 5, "constructor", "__proto__", ["brainrot"], "Brainrot"):
            with self.subTest(format=value):
                script = base_script()
                script["format"] = value
                self.assertFails(
                    self.check(script), "FAIL script: format must be explainer or brainrot"
                )

    def test_unknown_format_with_nine_scenes_keeps_the_untagged_explainer_count_line(self):
        """Red: an invalid format picks up the brainrot limits or the brainrot tag."""
        script = base_script()
        script["format"] = "vertical"
        script["scenes"] = self.scenes_of(script, 9)
        self.assertFails(
            self.check(script),
            "FAIL script: format must be explainer or brainrot",
            "FAIL script: 9 scenes (needs 3 to 8)",
        )

    def test_brainrot_bullet_28_chars_passes(self):
        """Red: the brainrot bulletText limit below 28."""
        script = brainrot_script()
        self.scene(script, "intro")["props"]["bullets"][1]["text"] = "x" * 28
        result = self.check(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_brainrot_bullet_29_chars_fails(self):
        """Red: the bullet shape still reads the explainer 36 (or drops the tag)."""
        script = brainrot_script()
        self.scene(script, "intro")["props"]["bullets"][1]["text"] = "x" * 29
        self.assertFails(
            self.check(script), "FAIL scene intro: bullets[1].text is 29 chars (max 28, brainrot)"
        )

    def test_brainrot_before_after_limits(self):
        """Red: a before-after limit (5 lines, 30 chars, 30-char heading) below brainrot's."""
        script = brainrot_script()
        side = {"heading": "h" * 30, "lines": ["x" * 30] * 5}
        self.set_intro(script, "before-after", {"title": "Compare", "before": side, "after": side, "cue": "The router"})
        result = self.check(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_brainrot_before_after_over_limits(self):
        """Red: one of the three before-after limits (either side) still reads the explainer 36 or 10."""
        script = brainrot_script()
        before = {"heading": "h" * 31, "lines": ["short"] * 6}
        after = {"heading": "h" * 31, "lines": ["x" * 31, "short"]}
        self.set_intro(script, "before-after", {"title": "Compare", "before": before, "after": after, "cue": "The router"})
        self.assertFails(
            self.check(script),
            "FAIL scene intro: before.heading is 31 chars (max 30, brainrot)",
            "FAIL scene intro: before.lines has 6 items (needs 0 to 5, brainrot)",
            "FAIL scene intro: after.heading is 31 chars (max 30, brainrot)",
            "FAIL scene intro: after.lines[0] is 31 chars (max 30, brainrot)",
        )

    def test_brainrot_diagram_label_sub_limits(self):
        """Red: the diagram label or sub limit still reads the explainer 14 or 24."""
        script = brainrot_script()
        node = self.scene(script, "flow")["props"]["nodes"][1]
        node["label"], node["sub"] = "l" * 12, "s" * 20
        result = self.check(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        node["label"], node["sub"] = "l" * 13, "s" * 21
        self.assertFails(
            self.check(script),
            "FAIL scene flow: nodes[1].label is 13 chars (max 12, brainrot)",
            "FAIL scene flow: nodes[1].sub is 21 chars (max 20, brainrot)",
        )

    def test_brainrot_title_limits(self):
        """Red: the title or subtitle limit still reads the explainer 50 or 80."""
        script = brainrot_script()
        props = {"title": "t" * 30, "subtitle": "s" * 60, "cue": "The router"}
        self.set_intro(script, "title", props)
        result = self.check(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        props["title"], props["subtitle"] = "t" * 31, "s" * 61
        self.assertFails(
            self.check(script),
            "FAIL scene intro: title is 31 chars (max 30, brainrot)",
            "FAIL scene intro: subtitle is 61 chars (max 60, brainrot)",
        )

    def test_explainer_limits_unchanged_under_explicit_format(self):
        """Red: the explainer shapes are built from the brainrot row or carry the tag."""
        script = base_script()
        script["format"] = "explainer"
        self.scene(script, "intro")["props"]["bullets"][1]["text"] = "x" * 41
        self.assertFails(self.check(script), "FAIL scene intro: bullets[1].text is 41 chars (max 36)")

    # -- helpers --
    def set_intro(self, script, component, props):
        """Turn scene `intro` into another component; its narration and cites stay."""
        scene = self.scene(script, "intro")
        scene["component"], scene["props"] = component, props


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


class TestBrainrotBuild(BrainrotBuildCase):
    def test_brainrot_top_level_values(self):
        """Red: build mode keeps writing the explainer canvas or budgets for a brainrot script."""
        result, timeline = self.build_brainrot(self.two_scene_brainrot(), {"intro": 3.0, "flow": 4.5})
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(
            (timeline["format"], timeline["width"], timeline["height"]), ("brainrot", 1080, 1920)
        )
        self.assertEqual((timeline["maxSceneSeconds"], timeline["maxTotalSeconds"]), (30, 90))
        self.assertEqual(timeline["fps"], 30)

    def test_brainrot_lead_and_tail(self):
        """Red: lead 6 or tail 12 reads the explainer 15 or 36 (explainer would give 141 frames)."""
        result, timeline = self.build_brainrot(self.two_scene_brainrot(), {"intro": 3.0, "flow": 4.5})
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        first, second = timeline["scenes"]
        self.assertEqual(
            (first["from"], first["durationInFrames"], first["leadFrames"], first["audioFrames"]),
            (0, 108, 6, 90),
        )
        self.assertEqual(second["from"], 108)
        self.assertEqual(timeline["totalFrames"], 108 + 6 + 135 + 12)

    def test_explainer_scenes_have_no_captions(self):
        """Red: build mode adds a captions key to explainer scenes."""
        script = base_script()
        _, timeline = self.build(script, {"intro": 2.0, "flow": 2.0, "code": 2.0})
        self.assertEqual(len(timeline["scenes"]), 3)
        for scene in timeline["scenes"]:
            self.assertNotIn("captions", scene)

    def test_build_mode_unknown_format_fails(self):
        """Red: an unknown format builds as explainer instead of failing."""
        script = self.two_scene_brainrot()
        script["format"] = "vertical"
        result, timeline = self.build(script, {"intro": 3.0, "flow": 4.5})
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.splitlines(), ["FAIL script: format must be explainer or brainrot"])
        self.assertIsNone(timeline)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "out", "timeline.json")))


class TestWordsFixture(unittest.TestCase):
    def test_words_for_closes_sentences_and_spaces_them(self):
        """Red: the fixture helper puts a sentence end mid-sentence or drops the pause."""
        got = words_for("Hi there. Again?", 0.5, 0.25)
        self.assertEqual(
            [(w["text"], w["from"], w["to"]) for w in got["words"]],
            [("Hi", 0.0, 0.5), ("there.", 0.5, 1.0), ("Again?", 1.25, 1.75)],
        )
        self.assertEqual(got["sentences"], [{"from": 0.0, "to": 1.0}, {"from": 1.25, "to": 1.75}])


if __name__ == "__main__":
    unittest.main()
