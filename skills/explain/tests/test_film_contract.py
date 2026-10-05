"""Producer-to-consumer contract of the film format, with no render: the real video/narrate.py
(say engine, default speed) writes the WAVs, the words.json files and durations.json that the
real video/build-timeline.mjs reads in build mode. Each side has its own unit tests with
hand-made inputs; this module is the only place where one produces what the other consumes for
a film. Each test names the mutation that turns it red."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_narrate import NARRATE_PY
from test_video_timeline import APP_LINES, FLOW_NARRATION, TOOL
from test_video_timeline_film import film_script

FPS = 30
LEAD = 6
PAUSE = {"forms": 30}   # the scene's own pause; any other scene takes the film row's 12
DEFAULT_PAUSE = 12

# Per scene of the film fixture: a narration with a backticked dotted name, a comma, a double
# space and a newline between words (type), three plain sentences (forms) and one sentence with
# no end mark (ends).
NARRATIONS = {
    "type": "The router runs `verify.sh`, then  stops.\nThe handler replies, and it ends.",
    "forms": FLOW_NARRATION,
    "ends": "One sentence with no end mark",
}
SENTENCES = {"type": 2, "forms": 3, "ends": 1}


def js_round(x):
    """Math.round for a non-negative float: halves round up (Python's round() rounds them to even)."""
    return int(x + 0.5)


class FilmContract(unittest.TestCase):
    """One check, one narrate run and one build over its audio directory, shared by the tests."""

    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(prefix="film-contract-")
        cls.addClassCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("\n".join(APP_LINES) + "\n", encoding="utf-8")
        cls.audio = root / "audio"
        script = film_script()
        for scene in script["scenes"]:
            scene["narration"] = NARRATIONS[scene["id"]]
        cls.script = script
        script_path = root / "script.json"
        script_path.write_text(json.dumps(script), encoding="utf-8")
        cls.check = subprocess.run(
            ["node", str(TOOL), "--check", str(script_path), "--root", str(root)],
            capture_output=True, text=True,
        )
        cls.narrate = subprocess.run(
            [sys.executable, str(NARRATE_PY), "--engine", "say", str(script_path), str(cls.audio)],
            capture_output=True, text=True,
        )
        out = root / "out" / "timeline.json"
        cls.build = subprocess.run(
            ["node", str(TOOL), str(script_path), str(cls.audio / "durations.json"), "say", str(out),
             "--root", str(root)],
            capture_output=True, text=True,
        )
        cls.timeline = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else None

    def scenes(self):
        """The built scenes; fails with the output of the failed step when there is no timeline."""
        self.assertIsNotNone(self.timeline, self.narrate.stdout + self.narrate.stderr + self.build.stdout)
        return self.timeline["scenes"]

    def words_of(self, scene_id):
        path = self.audio / f"{scene_id}.say.words.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_fixture_is_a_valid_film_script(self):
        """Mutation: a narration of the fixture breaks a film limit (words, scene length) or a scene
        rule, so the contract below would test a script that --check rejects."""
        self.assertEqual((self.check.returncode, self.check.stdout), (0, ""))

    def test_narrate_then_build_exit_zero(self):
        """Mutation: narrate.py does not narrate a film (exit 2, no durations.json for build mode to
        read), so the timeline is never built."""
        self.assertEqual(self.narrate.returncode, 0, self.narrate.stdout + self.narrate.stderr)
        self.assertEqual((self.build.returncode, self.build.stdout), (0, ""))
        self.assertEqual([s["id"] for s in self.scenes()], ["type", "forms", "ends"])
        self.assertEqual(self.timeline["format"], "film")

    def test_film_speaks_at_speed_1(self):
        """Mutation: the default speed of narrate.py is not 1.0 (render.sh passes none for a film), or
        a film scene is narrated whole, with no mode line in its sidecar."""
        self.assertEqual(self.narrate.returncode, 0, self.narrate.stdout + self.narrate.stderr)
        for scene_id in NARRATIONS:
            with self.subTest(scene=scene_id):
                sidecar = (self.audio / f"{scene_id}.say.txt").read_text(encoding="utf-8")
                lines = sidecar.splitlines()
                self.assertIn("speed=1.0", lines)
                self.assertIn("mode=sentences", lines)

    def test_sentence_frames_are_lead_plus_sentence_start(self):
        """Mutation: build mode rounds with floor, drops the lead, or takes the end of a sentence
        instead of its start."""
        for scene in self.scenes():
            words = self.words_of(scene["id"])
            with self.subTest(scene=scene["id"]):
                self.assertEqual(scene["sentences"], [LEAD + js_round(s["from"] * FPS) for s in words["sentences"]])
                self.assertEqual(len(scene["sentences"]), SENTENCES[scene["id"]])
                self.assertEqual(scene["sentences"][0], LEAD)

    def test_word_texts_are_the_narration_tokens(self):
        """Mutation: build mode strips the backticks from a word text, so the word is no longer the
        narration token."""
        for scene in self.scenes():
            with self.subTest(scene=scene["id"]):
                self.assertEqual([w["text"] for w in scene["words"]], NARRATIONS[scene["id"]].split())

    def test_words_end_inside_the_clip(self):
        """Mutation: build mode adds frames to the end of a word (the pause or a gap counted after
        the last word), so the last word runs past lead + audio."""
        for scene in self.scenes():
            with self.subTest(scene=scene["id"]):
                self.assertLessEqual(scene["words"][-1]["to"], scene["leadFrames"] + scene["audioFrames"])

    def test_scene_length(self):
        """Mutation: a scene drops the lead frames, or takes the row's pause where the scene has its
        own."""
        for scene in self.scenes():
            with self.subTest(scene=scene["id"]):
                pause = PAUSE.get(scene["id"], DEFAULT_PAUSE)
                self.assertEqual(scene["leadFrames"], LEAD)
                self.assertEqual(scene["durationInFrames"], LEAD + scene["audioFrames"] + pause)

    def test_check_frames_follow_the_sentences(self):
        """Mutation: a check frame is computed without the scene's offset or from the neighbouring
        sentence, the last sentence of a scene (here the one with no end mark) gets no frame, the
        end frame is not the last frame of its scene, or the frames are not in script order."""
        scenes = self.scenes()
        frames = self.timeline["checkFrames"]
        numbers = [entry["frame"] for entry in frames]
        self.assertEqual(numbers, sorted(set(numbers)), "strictly increasing")
        self.assertEqual(numbers[-1], self.timeline["totalFrames"] - 1)
        for scene in scenes:
            mine = [entry for entry in frames if entry["scene"] == scene["id"]]
            stills = [entry["still"] for entry in mine]
            words = self.words_of(scene["id"])
            self.assertEqual(stills, [f"s{k}" for k in range(1, len(words["sentences"]) + 1)] + ["end"])
            if scene["id"] == "ends":
                self.assertEqual(stills, ["s1", "end"])
            self.assertEqual(mine[-1]["frame"], scene["from"] + scene["durationInFrames"] - 1)
            for k, (sentence, entry) in enumerate(zip(words["sentences"], mine), start=1):
                start = LEAD + js_round(sentence["from"] * FPS)
                end = LEAD + js_round(sentence["to"] * FPS)
                with self.subTest(scene=scene["id"], still=f"s{k}"):
                    self.assertGreaterEqual(entry["frame"], scene["from"] + start)
                    self.assertLessEqual(entry["frame"], scene["from"] + end)


if __name__ == "__main__":
    unittest.main()
