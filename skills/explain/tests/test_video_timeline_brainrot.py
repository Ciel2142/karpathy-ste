"""Tests for the brainrot format of video/build-timeline.mjs: the `format` key, the per-format
limits and (in later tasks) build mode. Each test names the mutation that turns it red."""

import copy
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_video_timeline import EXPLAIN, TOOL, VideoCase, base_script


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

    def test_brainrot_cue_frame_is_sentence_start(self):
        """Red: cue frames stay the proportional estimate instead of the sentence start seconds."""
        result, timeline = self.build_with_words(self.two_scene_brainrot(), self.words_17())
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(timeline["scenes"][0]["cueFrames"], {"The router": 6, "The handler": 57})

    def test_brainrot_reads_used_engine_words_file(self):
        """Red: build mode looks up the words file of the requested engine, not the engine argument."""
        script = self.two_scene_brainrot()
        result, _ = self.build_brainrot(script, {"intro": 3.0, "flow": 4.5}, "say")
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        for scene in script["scenes"]:
            self.write_words(scene["id"], "kokoro", words_for(scene["narration"]))
            os.remove(os.path.join(self.dir, "%s.say.words.json" % scene["id"]))
        result, _ = self.build(script, {"intro": 3.0, "flow": 4.5}, "say")
        self.assertFails(
            result,
            "FAIL scene intro: cannot read intro.say.words.json: ENOENT",
            "FAIL scene flow: cannot read flow.say.words.json: ENOENT",
        )

    def test_brainrot_builds_with_kokoro_words_files(self):
        """Red: the words file name hard-codes say, so a kokoro build cannot find <id>.kokoro.words.json."""
        script = self.two_scene_brainrot()
        result, timeline = self.build_brainrot(script, {"intro": 3.0, "flow": 4.5}, "kokoro")
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(timeline["engine"], "kokoro")
        self.assertEqual(timeline["scenes"][0]["audio"], "audio/intro.kokoro.wav")

    def test_brainrot_missing_words_file_fails(self):
        """Red: a missing words file builds with estimated cue frames."""
        script = self.two_scene_brainrot()
        self.write_words("flow", "say", words_for(self.scene(script, "flow")["narration"]))
        result, timeline = self.build(script, {"intro": 3.0, "flow": 4.5})
        self.assertFails(result, "FAIL scene intro: cannot read intro.say.words.json: ENOENT")
        self.assertIsNone(timeline)

    def test_brainrot_words_not_json_fails(self):
        """Red: the words file is parsed without a named failure, or its parse error is dropped."""
        script = self.two_scene_brainrot()
        self.write("intro.say.words.json", "{not json")
        self.write_words("flow", "say", words_for(self.scene(script, "flow")["narration"]))
        result, _ = self.build(script, {"intro": 3.0, "flow": 4.5})
        self.assertEqual(result.returncode, 1)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(
            lines[0].startswith("FAIL scene intro: intro.say.words.json is not valid JSON: "), lines[0]
        )

    def test_brainrot_words_bad_shape_fails(self):
        """Red: a word with to < from is accepted, or the failing path is not named."""
        words = self.words_17()
        words["words"][1]["to"] = words["words"][1]["from"] - 0.01
        result, _ = self.build_with_words(self.two_scene_brainrot(), words)
        self.assertFails(
            result, "FAIL scene intro: intro.say.words.json has a bad shape at words[1].to"
        )

    def test_brainrot_bad_shape_paths(self):
        """Red: one of the shape rules is skipped: top level, sentences, words, item, text, number, overlap."""
        cases = [
            (lambda w: [], "top level"),
            (lambda w: {"words": w["words"]}, "sentences"),
            (lambda w: {"sentences": w["sentences"], "words": "x"}, "words"),
            (lambda w: w["words"].__setitem__(2, 5), "words[2]"),
            (lambda w: w["words"][3].__setitem__("text", 7), "words[3].text"),
            (lambda w: w["words"][0].__setitem__("from", -0.1), "words[0].from"),
            (lambda w: w["words"][6].__setitem__("to", "9"), "words[6].to"),
            (lambda w: w["sentences"][1].__setitem__("from", None), "sentences[1].from"),
            (lambda w: w["sentences"][0].__setitem__("to", -1.0), "sentences[0].to"),
            (lambda w: w["words"][2].__setitem__("from", w["words"][1]["to"] - 0.1), "words[2].from"),
        ]
        for mutate, where in cases:
            with self.subTest(where=where):
                words = self.words_17()
                replaced = mutate(words)
                words = replaced if replaced is not None else words
                result, _ = self.build_with_words(self.two_scene_brainrot(), words)
                self.assertFails(
                    result, "FAIL scene intro: intro.say.words.json has a bad shape at %s" % where
                )

    def test_brainrot_word_count_mismatch_fails(self):
        """Red: a words file with a different word count than the narration is accepted."""
        words = self.words_17()
        del words["words"][7]
        result, _ = self.build_with_words(self.two_scene_brainrot(), words)
        self.assertFails(
            result, "FAIL scene intro: intro.say.words.json has 7 words, the narration has 8"
        )

    def test_brainrot_token_mismatch_fails(self):
        """Red: tokens are compared with punctuation stripped, so "handler" passes for "handler.". """
        words = self.words_17()
        words["words"][4]["text"] = "handler"
        result, _ = self.build_with_words(self.two_scene_brainrot(), words)
        self.assertFails(
            result,
            'FAIL scene intro: intro.say.words.json word 4 is "handler", the narration has "handler."',
        )

    def test_brainrot_backticked_dotted_name_matches(self):
        """Red: tokens are compared with the backticks removed, or the cue token index is off."""
        script = self.two_scene_brainrot()
        intro = self.scene(script, "intro")
        intro["narration"] = "The `verify.sh` script runs. It stops."
        for bullet, cue in zip(intro["props"]["bullets"], ("The `verify.sh` script", "It stops")):
            bullet["cue"] = cue
        result, timeline = self.build_with_words(script, words_for(intro["narration"], 0.3, 0.2))
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(
            timeline["scenes"][0]["cueFrames"], {"The `verify.sh` script": 6, "It stops": 48}
        )

    def test_brainrot_double_space_narration_matches(self):
        """Red: the narration token split is not the same whitespace split the words file uses."""
        script = self.two_scene_brainrot()
        intro = self.scene(script, "intro")
        intro["narration"] = "The router  picks a\nhandler. The handler replies."
        result, timeline = self.build_with_words(script, words_for(intro["narration"], 0.3, 0.2))
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(timeline["scenes"][0]["cueFrames"], {"The router": 6, "The handler": 57})

    def test_brainrot_sentence_start_tolerance(self):
        """Red: the sentence-start match is exact (===) or looser than 0.001 s."""
        words = self.words_17()
        words["words"][5]["from"] = round(words["sentences"][1]["from"] + 0.0004, 6)
        result, timeline = self.build_with_words(self.two_scene_brainrot(), words)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(timeline["scenes"][0]["cueFrames"], {"The router": 6, "The handler": 57})
        words["words"][5]["from"] = round(words["sentences"][1]["from"] + 0.002, 6)
        result, _ = self.build_with_words(self.two_scene_brainrot(), words)
        self.assertFails(
            result,
            'FAIL scene intro: cue "The handler" does not start a sentence in intro.say.words.json',
        )

    def test_brainrot_words_after_clip_end_fail(self):
        """Red: a caption past the clip end (words file from an older WAV) builds."""
        words = self.words_17()
        words["words"][-1]["to"] = words["sentences"][-1]["to"] = 3.5
        result, _ = self.build_with_words(self.two_scene_brainrot(), words)
        self.assertFails(
            result, "FAIL scene intro: intro.say.words.json ends at 3.5 s, after the clip end 3 s"
        )

    def test_brainrot_close_cues_fail(self):
        """Red: the 15-frame cue distance is skipped for exact cue frames."""
        result, _ = self.build_with_words(
            self.two_scene_brainrot(), words_for(self.INTRO_NARRATION, 0.06, 0.0)
        )
        self.assertFails(
            result,
            'FAIL scene intro: cue "The handler" is 9 frames after the previous cue (minimum 15)',
        )

    def test_explainer_build_reads_no_words_file(self):
        """Red: build mode asks an explainer script for words files."""
        result, _ = self.build(base_script(), {"intro": 2.0, "flow": 2.0, "code": 2.0})
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    # -- helpers --
    INTRO_NARRATION = "The router picks a handler. The handler replies."

    def words_17(self):
        """Words of the intro narration whose second sentence starts at 1.7 s."""
        return words_for(self.INTRO_NARRATION, 0.3, 0.2)

    def build_with_words(self, script, intro_words):
        """Build with `intro_words` for scene intro and consistent words for the other scenes."""
        for scene in script["scenes"]:
            self.write_words(scene["id"], "say", words_for(scene["narration"]))
        self.write_words("intro", "say", intro_words)
        return self.build(script, {"intro": 3.0, "flow": 4.5})


class TestBrainrotCaptions(BrainrotBuildCase):
    NARRATION = "The router picks a handler. The handler replies."

    def test_caption_chunk_words(self):
        """Red: chunks hold more or fewer than 3 words, or a sentence end does not close a chunk."""
        captions = self.captions_of()
        self.assertEqual(
            [[w["text"] for w in c["words"]] for c in captions],
            [["The", "router", "picks"], ["a", "handler."], ["The", "handler", "replies."]],
        )

    def test_caption_chunks_tile(self):
        """Red: a chunk ends at its own last word instead of the next chunk's start (a gap)."""
        captions = self.captions_of()
        for here, after in zip(captions, captions[1:]):
            self.assertEqual(here["to"], after["from"])
        self.assertEqual(captions[-1]["to"], captions[-1]["words"][-1]["to"])
        for chunk in captions:
            self.assertEqual(chunk["from"], chunk["words"][0]["from"])
        # "handler." ends at 1.5 s (frame 51), the next sentence starts at 1.7 s: 6 + 51 = 57.
        self.assertEqual((captions[1]["words"][-1]["to"], captions[1]["to"]), (51, 57))

    def test_caption_word_frames(self):
        """Red: seconds convert with floor (7) or ceil, or the lead is not added: 6 + Math.round(7.5) is 14."""

        def start_late(words):
            words["words"][0].update({"from": 0.25, "to": 0.3})
            words["sentences"][0]["from"] = 0.25

        first = self.captions_of(mutate_words=start_late)[0]["words"][0]
        self.assertEqual((first["text"], first["from"], first["to"]), ("The", 14, 15))

    def test_caption_words_cover_narration(self):
        """Red: a chunk drops or repeats a word, or a chunk edge loses one."""
        narration = "The `verify.sh` script runs. It stops, then `render.sh` starts."
        captions = self.captions_of(narration, self.title_props("The `verify.sh` script"))
        tokens = narration.replace("`", "").split()
        self.assertEqual([w["text"] for c in captions for w in c["words"]], tokens)

    def test_caption_text_has_no_backticks(self):
        """Red: the caption keeps the backticks of the token, or drops the dots of the name."""
        captions = self.captions_of("The `verify.sh` script runs.", self.title_props("The `verify.sh` script"))
        self.assertEqual(captions[0]["words"][1]["text"], "verify.sh")

    def test_captions_are_scene_relative_on_a_later_scene(self):
        """Red: caption frames add the scene's `from` (the second scene's first chunk would start at 114,
        not at its lead of 6)."""
        result, timeline = self.build_brainrot(self.two_scene_brainrot(), {"intro": 3.0, "flow": 4.5})
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        second = timeline["scenes"][1]
        self.assertEqual(second["from"], 108)
        self.assertEqual(second["captions"][0]["from"], second["leadFrames"])

    def test_caption_break_after_comma(self):
        """Red: a comma does not close a chunk."""
        captions = self.captions_of("First, the check runs.", self.title_props("First"))
        self.assertEqual(
            [[w["text"] for w in c["words"]] for c in captions], [["First,"], ["the", "check", "runs."]]
        )

    def test_caption_break_after_each_mark(self):
        """Red: one of . , ; : ? ! is missing from the set that closes a chunk."""
        for mark in ".,;:?!":
            with self.subTest(mark=mark):
                captions = self.captions_of("One%s two three four" % mark, self.title_props("One"))
                self.assertEqual(
                    [[w["text"] for w in c["words"]] for c in captions],
                    [["One" + mark], ["two", "three", "four"]],
                )

    def test_caption_break_looks_at_the_text_without_backticks(self):
        """Red: the mark check reads the raw token, whose last character is a backtick."""
        captions = self.captions_of("See `a,` then b c d.", self.title_props("See"))
        self.assertEqual(
            [[w["text"] for w in c["words"]] for c in captions],
            [["See", "a,"], ["then", "b", "c"], ["d."]],
        )

    def test_chunk_breaks_before_char_cap(self):
        """Red: no character cap, so the third word joins and the chunk is "keyboards monitors speakers"
        (27 characters, over the cap of 20)."""
        captions = self.captions_of("keyboards monitors speakers", self.title_props("keyboards"))
        self.assertEqual(self.chunk_texts(captions), ["keyboards monitors", "speakers"])

    def test_chunk_at_cap_kept(self):
        """Red: the cap is exclusive (`>=` instead of `>`), so a chunk of exactly 20 characters splits."""
        captions = self.captions_of("abcdef ghijkl mnopqr", self.title_props("abcdef"))
        self.assertEqual(self.chunk_texts(captions), ["abcdef ghijkl mnopqr"])

    def test_chunk_cap_comes_from_formats_json(self):
        """Red: the cap is a literal of build-timeline.mjs, so a changed formats.json has no effect
        (with a cap of 13, "abcdef ghijkl mnopqr" splits after "abcdef ghijkl")."""
        tool_dir = Path(self.dir) / "tool"  # a copy of the tool, with its own formats.json beside it
        tool_dir.mkdir()
        shutil.copy(TOOL, tool_dir / TOOL.name)
        formats = json.loads((EXPLAIN / "video" / "formats.json").read_text(encoding="utf-8"))
        formats["brainrot"]["captionChars"] = 13
        (tool_dir / "formats.json").write_text(json.dumps(formats), encoding="utf-8")
        self.node = lambda *args: subprocess.run(
            ["node", str(tool_dir / TOOL.name), *args], capture_output=True, text=True, cwd=self.dir
        )
        captions = self.captions_of("abcdef ghijkl mnopqr", self.title_props("abcdef"))
        self.assertEqual(self.chunk_texts(captions), ["abcdef ghijkl", "mnopqr"])

    def test_long_word_is_its_own_chunk(self):
        """Red: a word over the cap joins the open chunk ("the EXPLAIN_BRAINROT_BACKGROUNDS"), or the
        word after it joins it."""
        captions = self.captions_of("the `EXPLAIN_BRAINROT_BACKGROUNDS` folder", self.title_props("the"))
        self.assertEqual(self.chunk_texts(captions), ["the", "EXPLAIN_BRAINROT_BACKGROUNDS", "folder"])

    def test_chunk_cap_counts_the_text_without_backticks(self):
        """Red: the cap counts the backticks of the token (the two extra characters would split
        "abcdef ghijkl mnopq`r`" of 20 characters)."""
        captions = self.captions_of("abcdef ghijkl `mnopqr`", self.title_props("abcdef"))
        self.assertEqual(self.chunk_texts(captions), ["abcdef ghijkl mnopqr"])

    # -- helpers --
    def chunk_texts(self, captions):
        return [" ".join(w["text"] for w in c["words"]) for c in captions]

    def title_props(self, cue):
        return {"title": "T", "subtitle": "S", "cue": cue}

    def captions_of(self, narration=None, props=None, mutate_words=None):
        """Build the two-scene brainrot script with `narration` (and title `props`) in scene intro and
        return the captions of intro. Words are 0.3 s each with 0.2 s between sentences."""
        script = self.two_scene_brainrot()
        intro = self.scene(script, "intro")
        if narration is not None:
            intro["narration"] = narration
        if props is not None:
            intro["component"], intro["props"] = "title", props
        words = words_for(intro["narration"], 0.3, 0.2)
        if mutate_words is not None:
            mutate_words(words)
        for scene in script["scenes"]:
            self.write_words(scene["id"], "say", words_for(scene["narration"]))
        self.write_words("intro", "say", words)
        result, timeline = self.build(script, {"intro": 6.0, "flow": 4.5})
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        return timeline["scenes"][0]["captions"]


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
