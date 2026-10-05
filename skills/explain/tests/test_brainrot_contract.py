"""Producer-to-consumer contract of the brainrot format, with no render: the real video/narrate.py
(say engine, speed 1.2) writes the WAVs, the words.json files and durations.json that the real
video/build-timeline.mjs reads in build mode. Each side has its own unit tests with hand-made
inputs; this module is the only place where one produces what the other consumes. Each test
names the mutation that turns it red."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_narrate import NARRATE_PY
from test_video_timeline import APP_LINES, TOOL
from test_video_timeline_brainrot import brainrot_script

FPS = 30

# Per scene of the brainrot fixture: a narration with a backticked dotted name, a comma, a double
# space and a newline between words, and the index of the sentence each cue starts. The cues sit
# at sentence starts, the second and third ones on a later sentence than the first.
NARRATIONS = {
    "intro": "The router runs `verify.sh`, then  stops.\nThe handler replies, and it ends.",
    "flow": "First the request arrives.\nThen the router checks `render.sh` and  picks a handler. "
    "Last the handler replies, and the work ends.",
    "code": "The first part sets up `app.py`, then  loads it.\nThe second part runs, and then it stops.",
}
CUE_SENTENCE = {
    "intro": {"The router": 0, "The handler": 1},
    "flow": {"First the request": 0, "Then the router": 1, "Last the handler": 2},
    "code": {"The first part": 0, "The second part": 1},
}


def js_round(x):
    """Math.round for a non-negative float: halves round up (Python's round() rounds them to even)."""
    return int(x + 0.5)


class BrainrotContract(unittest.TestCase):
    """One narrate run and one build over its audio directory, shared by the tests."""

    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(prefix="brainrot-contract-")
        cls.addClassCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("\n".join(APP_LINES) + "\n", encoding="utf-8")
        cls.audio = root / "audio"
        script = brainrot_script()
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
            [sys.executable, str(NARRATE_PY), "--engine", "say", "--speed", "1.2", str(script_path), str(cls.audio)],
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

    def test_fixture_is_a_valid_brainrot_script(self):
        """Mutation: a narration of the fixture breaks a brainrot limit or a cue rule, so the contract
        below would test a script that --check rejects."""
        self.assertEqual((self.check.returncode, self.check.stdout), (0, ""))

    def test_narrate_then_build_exit_zero(self):
        """Mutation: narrate.py writes a words.json that build mode rejects (a token that differs from the
        narration, a word past the clip end), or no durations.json."""
        self.assertEqual(self.narrate.returncode, 0, self.narrate.stdout + self.narrate.stderr)
        self.assertEqual((self.build.returncode, self.build.stdout), (0, ""))
        self.assertEqual([s["id"] for s in self.scenes()], ["intro", "flow", "code"])
        self.assertEqual(self.timeline["format"], "brainrot")

    def test_cue_frames_are_lead_plus_sentence_start(self):
        """Mutation: build mode rounds with floor, drops the lead, or reads the cue's own word instead of
        its sentence; or narrate.py moves a sentence start away from the first word of its sentence."""
        for scene in self.scenes():
            narration = NARRATIONS[scene["id"]]
            words = self.words_of(scene["id"])
            self.assertEqual(sorted(scene["cueFrames"]), sorted(CUE_SENTENCE[scene["id"]]))
            for cue, index in CUE_SENTENCE[scene["id"]].items():
                with self.subTest(scene=scene["id"], cue=cue):
                    sentence = words["sentences"][index]
                    first_word = words["words"][len(narration[:narration.index(cue)].split())]
                    self.assertEqual(first_word["from"], sentence["from"])
                    self.assertEqual(scene["cueFrames"][cue], scene["leadFrames"] + js_round(sentence["from"] * FPS))

    def test_every_cue_frame_starts_a_caption_chunk(self):
        """Mutation: a sentence end does not close a caption chunk, or captions use another frame
        conversion than cue frames, so a cue lights up between two chunks."""
        for scene in self.scenes():
            starts = {chunk["from"] for chunk in scene["captions"]}
            for cue, frame in scene["cueFrames"].items():
                with self.subTest(scene=scene["id"], cue=cue):
                    self.assertIn(frame, starts)

    def test_caption_words_are_the_narration_tokens(self):
        """Mutation: a caption keeps the backticks, or a line break or double space drops or merges a word."""
        for scene in self.scenes():
            with self.subTest(scene=scene["id"]):
                shown = [word["text"] for chunk in scene["captions"] for word in chunk["words"]]
                self.assertEqual(shown, NARRATIONS[scene["id"]].replace("`", "").split())

    def test_captions_end_inside_the_clip(self):
        """Mutation: narrate.py writes word times that run past the clip, or the join gap is counted
        after the last clip."""
        for scene in self.scenes():
            with self.subTest(scene=scene["id"]):
                self.assertLessEqual(scene["captions"][-1]["to"], scene["leadFrames"] + scene["audioFrames"])


if __name__ == "__main__":
    unittest.main()
