"""Tests for video/build-timeline.mjs: the script.json validator (--check) and the
timeline builder. Each test names the mutation of the script that turns it red."""

import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

EXPLAIN = Path(__file__).resolve().parent.parent
TOOL = EXPLAIN / "video" / "build-timeline.mjs"
TEMPLATE = EXPLAIN / "templates" / "video-script.json"

FLOW_NARRATION = "First the request arrives. Then the router picks a handler. Last the handler replies."
APP_LINES = ["line %d of the app" % n for n in range(1, 73)]
WIDE_LINES = ["short", "short", "x" * 69 + "\t", "short"]


def cite(path="src/app.py", line=1, snippet="line 1"):
    return {"path": path, "line": line, "snippet": snippet}


def base_script():
    """A valid three-scene script: bullets, a diagram and a code scene."""
    return {
        "title": "Fixture",
        "subject": {"text": "src/app.py", "kind": "file"},
        "provenance": {
            "root": ".",
            "commit": "9376c80",
            "dirty": "no",
            "date": "2026-10-03",
            "source": "src/app.py",
            "not_covered": "Everything else.",
        },
        "scenes": [
            {
                "id": "intro",
                "component": "bullets-appear",
                "props": {
                    "title": "Two parts",
                    "bullets": [
                        {"text": "The router", "cue": "The router"},
                        {"text": "The handler", "cue": "The handler"},
                    ],
                },
                "narration": "The router picks a handler. The handler replies.",
                "cites": [cite()],
            },
            {
                "id": "flow",
                "component": "diagram-with-highlight-walk",
                "props": {
                    "title": "Request path",
                    "nodes": [
                        {"id": "req", "label": "request", "cell": "a1"},
                        {"id": "router", "label": "router", "sub": "picks", "cell": "b2"},
                        {"id": "handler", "label": "handler", "cell": "c3"},
                    ],
                    "edges": [
                        {"from": "req", "to": "router", "label": "in"},
                        {"from": "router", "to": "handler"},
                    ],
                    "walk": [
                        {"node": "req", "cue": "First the request"},
                        {"node": "router", "cue": "Then the router"},
                        {"node": "handler", "cue": "Last the handler"},
                    ],
                },
                "narration": FLOW_NARRATION,
                "cites": [cite()],
            },
            {
                "id": "code",
                "component": "code-with-line-highlights",
                "props": {
                    "title": "The source",
                    "source": {"path": "src/app.py", "from": 3, "to": 10},
                    "highlights": [
                        {"from": 4, "to": 5, "cue": "The first part"},
                        {"from": 8, "to": 9, "cue": "The second part"},
                    ],
                },
                "narration": "The first part sets up. The second part runs.",
                "cites": [cite(line=3, snippet="line 3")],
            },
        ],
    }


class VideoCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name
        self.write("src/app.py", "\n".join(APP_LINES) + "\n")
        self.write("src/wide.py", "\n".join(WIDE_LINES) + "\n")

    def write(self, name, text):
        path = os.path.join(self.dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def write_json(self, name, value):
        return self.write(name, json.dumps(value))

    def node(self, *args):
        return subprocess.run(
            ["node", str(TOOL), *args], capture_output=True, text=True, cwd=self.dir
        )

    def check(self, script):
        path = self.write_json("script.json", script)
        return self.node("--check", path, "--root", self.dir)

    def check_mutated(self, mutate):
        script = base_script()
        mutate(script)
        return self.check(script)

    def scene(self, script, scene_id):
        return next(s for s in script["scenes"] if s["id"] == scene_id)

    def build(self, script, seconds, engine="say"):
        script_path = self.write_json("script.json", script)
        durations = self.write_json(
            "durations.json", {"engine": engine, "fallback": None, "scenes": seconds}
        )
        out = os.path.join(self.dir, "out", "timeline.json")
        result = self.node(script_path, durations, engine, out, "--root", self.dir)
        timeline = None
        if os.path.exists(out):
            with open(out, encoding="utf-8") as handle:
                timeline = json.load(handle)
        return result, timeline

    def assertFails(self, result, *lines):
        """Exit 1 and exactly these FAIL lines on stdout: one cause per mutation."""
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout.splitlines(), list(lines))


class TestCheck(VideoCase):
    def test_template_script_passes_check(self):
        """Red: a budget off by one in the template (a 37-char bullet)."""
        result = self.node("--check", str(TEMPLATE), "--root", str(EXPLAIN))
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_valid_fixture_passes_check(self):
        """Red: the check rejects a valid script (a rule that is too strict)."""
        result = self.check(base_script())
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_unknown_component_fails(self):
        """Red: the component lookup removed, so a typo passes."""

        def mutate(s):
            self.scene(s, "intro")["component"] = "titel"

        self.assertFails(self.check_mutated(mutate), 'FAIL scene intro: unknown component "titel"')

    def test_missing_and_extra_props_fail(self):
        """Red: the missing-prop or the extra-prop check removed."""

        def mutate(s):
            props = self.scene(s, "intro")["props"]
            del props["title"]
            props["colour"] = "red"

        result = self.check_mutated(mutate)
        self.assertFails(
            result,
            'FAIL scene intro: missing prop "title"',
            'FAIL scene intro: unexpected prop "colour"',
        )

    def test_bullet_over_36_chars_fails(self):
        """Red: the bullet text budget removed."""

        def mutate(s):
            self.scene(s, "intro")["props"]["bullets"][1]["text"] = "x" * 41

        self.assertFails(
            self.check_mutated(mutate), "FAIL scene intro: bullets[1].text is 41 chars (max 36)"
        )

    def test_narration_over_45_words_fails(self):
        """Red: the narration word budget removed."""

        def mutate(s):
            scene = self.scene(s, "intro")
            scene["narration"] += " " + " ".join(["more"] * 38)

        self.assertFails(self.check_mutated(mutate), "FAIL scene intro: narration is 46 words (max 45)")

    def test_empty_narration_fails(self):
        """Red: the empty-narration check removed."""

        def mutate(s):
            self.scene(s, "code")["narration"] = "  "

        self.assertFails(self.check_mutated(mutate), "FAIL scene code: narration is empty")

    def test_scene_count_outside_3_to_8_fails(self):
        """Red: the scene-count range removed."""

        def mutate(s):
            del s["scenes"][2]

        self.assertFails(self.check_mutated(mutate), "FAIL script: 2 scenes (needs 3 to 8)")

    def test_duplicate_scene_id_fails(self):
        """Red: the duplicate-id check removed."""

        def mutate(s):
            self.scene(s, "code")["id"] = "intro"

        self.assertFails(self.check_mutated(mutate), 'FAIL script: duplicate scene id "intro"')

    def test_file_kind_scene_without_cites_fails(self):
        """Red: the no-cites rule removed for subject kind file."""

        def mutate(s):
            self.scene(s, "flow")["cites"] = []

        self.assertFails(self.check_mutated(mutate), "FAIL scene flow: no cites (subject kind file)")

    def test_topic_kind_scene_without_cites_passes(self):
        """Red: the no-cites rule applied to every subject kind."""

        def mutate(s):
            s["subject"]["kind"] = "topic"
            self.scene(s, "flow")["cites"] = []

        result = self.check_mutated(mutate)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_cite_line_required_unless_url(self):
        """Red: line required for URL cites too, or not required for path cites."""

        def mutate(s):
            scene = self.scene(s, "flow")
            scene["cites"] = [
                {"path": "src/app.py", "snippet": "line 1"},
                {"path": "https://example.com/doc", "snippet": "a doc"},
            ]

        self.assertFails(self.check_mutated(mutate), "FAIL scene flow: missing prop \"cites[0].line\"")

    def test_duplicate_cell_fails(self):
        """Red: the unique-cell check removed."""

        def mutate(s):
            self.scene(s, "flow")["props"]["nodes"][2]["cell"] = "a1"

        self.assertFails(
            self.check_mutated(mutate),
            'FAIL scene flow: nodes[2].cell "a1" is already used by nodes[0]',
        )

    def test_edge_and_walk_must_name_nodes(self):
        """Red: the node-reference checks removed."""

        def mutate(s):
            props = self.scene(s, "flow")["props"]
            props["edges"][1]["to"] = "nowhere"
            props["walk"][0]["node"] = "ghost"

        self.assertFails(
            self.check_mutated(mutate),
            'FAIL scene flow: edges[1].to "nowhere" is not a node id',
            'FAIL scene flow: walk[0].node "ghost" is not a node id',
        )

    def test_cue_not_at_sentence_start_fails(self):
        """Red: the sentence-start check removed."""

        def mutate(s):
            self.scene(s, "flow")["props"]["walk"][1]["cue"] = "the router"

        self.assertFails(
            self.check_mutated(mutate),
            'FAIL scene flow: cue "the router" is not at a sentence start',
        )

    def test_cue_not_unique_fails(self):
        """Red: the uniqueness check removed."""

        def mutate(s):
            self.scene(s, "flow")["narration"] = (
                "First the request arrives. Then the router picks a handler. "
                "Then the router sends it on. Last the handler replies."
            )

        self.assertFails(
            self.check_mutated(mutate), 'FAIL scene flow: cue "Then the router" is not unique in the narration'
        )

    def test_cue_missing_from_narration_fails(self):
        """Red: the found check removed, or a cue matched inside a longer word."""

        def mutate(s):
            self.scene(s, "flow")["props"]["walk"][2]["cue"] = "Last the hand"

        self.assertFails(
            self.check_mutated(mutate), 'FAIL scene flow: cue "Last the hand" is not in the narration'
        )

    def test_cues_out_of_order_fail(self):
        """Red: the narration-order check removed."""

        def mutate(s):
            walk = self.scene(s, "flow")["props"]["walk"]
            walk[0]["cue"], walk[1]["cue"] = walk[1]["cue"], walk[0]["cue"]

        self.assertFails(
            self.check_mutated(mutate),
            'FAIL scene flow: cue "First the request" is out of narration order',
        )

    def test_code_line_over_72_columns_fails(self):
        """Red: a tab counted as 1 column (a 69-char line plus a tab is 73 columns)."""

        def mutate(s):
            scene = self.scene(s, "code")
            scene["props"]["source"] = {"path": "src/wide.py", "from": 1, "to": 4}
            scene["props"]["highlights"] = [
                {"from": 1, "to": 2, "cue": "The first part"},
                {"from": 3, "to": 4, "cue": "The second part"},
            ]

        self.assertFails(self.check_mutated(mutate), "FAIL scene code: line 3 is 73 columns (max 72)")

    def test_code_range_outside_file_fails(self):
        """Red: the range-inside-file check removed."""

        def mutate(s):
            scene = self.scene(s, "code")
            scene["props"]["source"] = {"path": "src/app.py", "from": 80, "to": 90}
            scene["props"]["highlights"] = [
                {"from": 81, "to": 82, "cue": "The first part"},
                {"from": 85, "to": 86, "cue": "The second part"},
            ]

        self.assertFails(
            self.check_mutated(mutate), "FAIL scene code: source.to 90 is outside src/app.py (72 lines)"
        )

    def test_code_range_over_14_lines_fails(self):
        """Red: the 14-line budget removed."""

        def mutate(s):
            scene = self.scene(s, "code")
            scene["props"]["source"] = {"path": "src/app.py", "from": 1, "to": 15}

        self.assertFails(
            self.check_mutated(mutate), "FAIL scene code: source range 1-15 is 15 lines (max 14)"
        )

    def test_highlight_outside_source_range_fails(self):
        """Red: the highlight-inside-source check removed."""

        def mutate(s):
            self.scene(s, "code")["props"]["highlights"][1]["to"] = 11

        self.assertFails(
            self.check_mutated(mutate),
            "FAIL scene code: highlights[1] range 8-11 is outside the source range 3-10",
        )

    def test_scene_id_outside_a_z_0_9_dash_fails(self):
        """Red: no pattern check on the scene id (an id such as "x/y" names a file path)."""
        for bad in ("x/y", "Intro", "-lead"):
            with self.subTest(id=bad):

                def mutate(s):
                    self.scene(s, "intro")["id"] = bad

                self.assertFails(
                    self.check_mutated(mutate), 'FAIL scene #1: id "%s" must match [a-z0-9-]' % bad
                )

    def test_not_covered_is_required_and_may_be_empty(self):
        """Red: provenance.not_covered optional (transcript.py then fails on the missing key)."""

        def drop(s):
            del s["provenance"]["not_covered"]

        self.assertFails(self.check_mutated(drop), 'FAIL script: missing prop "provenance.not_covered"')

        def empty(s):
            s["provenance"]["not_covered"] = ""

        result = self.check_mutated(empty)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_prototype_names_are_not_components_or_props(self):
        """Red: SHAPES[...] and `key in shape` (inherited names such as constructor pass)."""
        for name in ("constructor", "toString", "__proto__"):
            with self.subTest(component=name):

                def as_component(s):
                    scene = self.scene(s, "intro")
                    scene["component"], scene["props"] = name, {}

                self.assertFails(
                    self.check_mutated(as_component), 'FAIL scene intro: unknown component "%s"' % name
                )
            with self.subTest(prop=name):

                def as_prop(s):
                    self.scene(s, "intro")["props"][name] = "x"

                self.assertFails(
                    self.check_mutated(as_prop), 'FAIL scene intro: unexpected prop "%s"' % name
                )

    def test_cue_after_question_mark_passes(self):
        """Red: the sentence end limited to "." (a cue after "?" is not at a sentence start)."""

        def mutate(s):
            self.scene(s, "intro")["narration"] = "Who picks the handler? The router does. The handler replies."

        result = self.check_mutated(mutate)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_cue_after_exclamation_mark_passes(self):
        """Red: the sentence end limited to "." (a cue after "!" is not at a sentence start)."""

        def mutate(s):
            self.scene(s, "intro")["narration"] = "The router picks a handler! The handler replies."

        result = self.check_mutated(mutate)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_invalid_json_is_one_fail_line(self):
        """Red: the JSON parse error left to crash node (stack trace, no FAIL line)."""
        path = self.write("script.json", "{ not json")
        result = self.node("--check", path, "--root", self.dir)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertTrue(result.stdout.startswith("FAIL script: script %s is not valid JSON" % path))

    def test_unreadable_file_is_one_fail_line(self):
        """Red: the read error left to crash node."""
        result = self.node("--check", os.path.join(self.dir, "missing.json"), "--root", self.dir)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertTrue(result.stdout.startswith("FAIL script: cannot read script"))

    def test_usage_error_exits_2(self):
        """Red: a missing --root treated as a validation failure (exit 1) or accepted."""
        path = self.write_json("script.json", base_script())
        for args in (["--check", path], [], ["--check", path, "--root"]):
            result = self.node(*args)
            self.assertEqual(result.returncode, 2, args)
            self.assertEqual(result.stdout, "")
            self.assertIn("usage:", result.stderr)


class TestBuild(VideoCase):
    def two_scene_script(self):
        script = base_script()
        script["scenes"] = script["scenes"][:2]
        return script

    def test_two_scene_fixture_frames_add_up(self):
        """Red: tailFrames changed (36 -> 30 gives 315 and the second scene at 135)."""
        result, timeline = self.build(self.two_scene_script(), {"intro": 3.0, "flow": 4.5})
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(timeline["totalFrames"], 327)
        first, second = timeline["scenes"]
        self.assertEqual(second["from"], 141)
        self.assertEqual(
            (first["from"], first["durationInFrames"], first["leadFrames"], first["audioFrames"]),
            (0, 141, 15, 90),
        )
        self.assertEqual(second["audioFrames"], 135)
        self.assertEqual(second["audio"], "audio/flow.say.wav")

    def test_timeline_top_level_shape(self):
        """Red: a constant (fps, size) or the engine field changed."""
        _, timeline = self.build(self.two_scene_script(), {"intro": 5.0, "flow": 5.0}, "kokoro")
        self.assertEqual(
            list(timeline),
            ["fps", "width", "height", "totalFrames", "engine", "scenes"],
        )
        self.assertEqual(
            (timeline["fps"], timeline["width"], timeline["height"], timeline["engine"]),
            (30, 1280, 720, "kokoro"),
        )
        self.assertEqual(timeline["scenes"][0]["audio"], "audio/intro.kokoro.wav")

    def test_cue_frame_is_proportional(self):
        """Red: the cue offset measured from the cue end (offset 0 would give 19)."""
        narration = "First " + "y" * 52 + ". Second " + "z" * 53
        self.assertEqual(len(narration), 120)
        self.assertEqual(narration.index("Second"), 60)
        script = self.two_scene_script()
        intro = self.scene(script, "intro")
        intro["narration"] = narration
        intro["props"]["bullets"] = [
            {"text": "One", "cue": "First"},
            {"text": "Two", "cue": "Second"},
        ]
        _, timeline = self.build(script, {"intro": 3.0, "flow": 5.0})
        self.assertEqual(timeline["scenes"][0]["cueFrames"], {"First": 15, "Second": 60})

    def test_code_scene_props_carry_lines(self):
        """Red: props.lines not added, or counted from line 0 or with a trailing newline."""
        script = base_script()
        _, timeline = self.build(script, {"intro": 2.0, "flow": 2.0, "code": 2.0})
        code = timeline["scenes"][2]
        self.assertEqual(code["props"]["lines"], APP_LINES[2:10])
        self.assertEqual(code["props"]["source"], {"path": "src/app.py", "from": 3, "to": 10})

    def test_cues_closer_than_15_frames_fail_in_build_mode(self):
        """Red: the 15-frame distance check removed from build mode."""
        script = self.two_scene_script()
        flow = self.scene(script, "flow")
        flow["narration"] = "First the request arrives. Then the router picks a handler. Last the handler replies."
        result, timeline = self.build(script, {"intro": 3.0, "flow": 0.3})
        self.assertIsNone(timeline)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                'FAIL scene flow: cue "Then the router" is 3 frames after the previous cue (minimum 15)',
                'FAIL scene flow: cue "Last the handler" is 3 frames after the previous cue (minimum 15)',
            ],
        )

    def test_scene_without_duration_fails(self):
        """Red: a missing duration entry treated as zero or crashing node."""
        result, timeline = self.build(self.two_scene_script(), {"intro": 3.0})
        self.assertIsNone(timeline)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.splitlines(), ["FAIL scene flow: no duration in durations.json"])

    def test_build_mode_skips_budgets(self):
        """Red: build mode re-runs the budgets (two scenes are under the 3-scene minimum)."""
        result, timeline = self.build(self.two_scene_script(), {"intro": 3.0, "flow": 4.5})
        self.assertEqual(result.returncode, 0)
        self.assertIsNotNone(timeline)

    def test_build_mode_rejects_unknown_engine(self):
        """Red: any engine name accepted."""
        script_path = self.write_json("script.json", self.two_scene_script())
        durations = self.write_json("durations.json", {"engine": "say", "fallback": None, "scenes": {}})
        result = self.node(script_path, durations, "espeak", os.path.join(self.dir, "t.json"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr)


if __name__ == "__main__":
    unittest.main()
