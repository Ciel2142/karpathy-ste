"""Tests for the sentence-by-sentence narration of video/narrate.py (brainrot scripts): the
text splitting and word timings, the per-sentence narration with its words.json, and joining
the clips. The shared doubles and the NarrateCase base live in test_narrate. Each test names
the mutation that turns it red."""

import importlib.util
import json
import shutil
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_narrate import NARRATE_PY, ONE, TWO, NarrateCase, scene


class SentenceText(unittest.TestCase):
    """The pure text functions of the sentence-by-sentence narration: the module is loaded
    by path, so no process runs and no engine is touched."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("narrate_under_test", NARRATE_PY)
        cls.narrate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.narrate)

    def split(self, text):
        """The sentences of text, after checking the invariant every split must keep."""
        sentences = self.narrate.split_sentences(text)
        self.assertEqual([w for s in sentences for w in s.split()], text.split())
        self.assertTrue(all(s and s == s.strip() for s in sentences), sentences)
        return sentences

    def test_split_basic(self):
        """Mutation: only "." ends a sentence, or the terminator is dropped from the sentence."""
        self.assertEqual(self.split("One. Two? Three!"), ["One.", "Two?", "Three!"])

    def test_split_keeps_code_names(self):
        """Mutation: a "." followed by more text (verify.sh, render.sh) ends a sentence."""
        sentences = self.split("Run `verify.sh` now. Then render.sh runs.")
        self.assertEqual(sentences, ["Run `verify.sh` now.", "Then render.sh runs."])

    def test_split_dot_inside_backticks_with_space(self):
        """Mutation: a terminator followed by a space splits even inside backticks."""
        self.assertEqual(self.split("Use `a. b` here. Done."), ["Use `a. b` here.", "Done."])

    def test_split_no_final_terminator(self):
        """Mutation: the text after the last terminator is dropped."""
        self.assertEqual(self.split("Run the check"), ["Run the check"])
        self.assertEqual(self.split("One. Run the check"), ["One.", "Run the check"])

    def test_split_whitespace(self):
        """Mutation: sentences are cut at a single space, or a line break does not count as whitespace."""
        self.assertEqual(self.split("One.\n\nTwo  words."), ["One.", "Two  words."])

    def test_split_odd_backticks(self):
        """Mutation: an unbalanced backtick keeps the scan "inside" to the end, one run-on sentence."""
        self.assertEqual(self.split("Run `verify.sh now. Then stop."), ["Run `verify.sh now.", "Then stop."])

    def test_split_empty_text_has_no_sentences(self):
        """Mutation: an empty or blank narration yields one empty sentence."""
        self.assertEqual(self.split(""), [])
        self.assertEqual(self.split("  \n "), [])

    def test_word_weights(self):
        """Mutation: the sentence's last word gets no end weight, or a comma word gets none."""
        words = self.narrate.word_timings(["Hi, you."], [(0.0, 1.0)])
        self.assertEqual(words, [
            {"text": "Hi,", "from": 0.0, "to": 5 / 11},
            {"text": "you.", "from": 5 / 11, "to": 1.0},
        ])

    def test_words_tile_each_span_exactly(self):
        """Mutation: word times are rounded or recomputed, so the first or last word misses its span."""
        words = self.narrate.word_timings(["One two three.", "Four, five."], [(0.0, 0.5), (0.65, 1.15)])
        self.assertEqual([w["text"] for w in words], "One two three. Four, five.".split())
        first, second = words[:3], words[3:]
        self.assertEqual((first[0]["from"], first[-1]["to"]), (0.0, 0.5))
        self.assertEqual((second[0]["from"], second[-1]["to"]), (0.65, 1.15))
        for part in (first, second):
            for a, b in zip(part, part[1:]):
                self.assertEqual(a["to"], b["from"])

    def test_last_word_ends_at_the_span_end_not_a_recomputation(self):
        """Mutation: the last word's end is start + (end - start) * total / total, which float
        rounding moves off the span end (here 0.8 + (2.97 - 0.8) is not 2.97)."""
        start, end = 0.8, 2.97
        self.assertNotEqual(start + (end - start), end)   # the span really exercises rounding
        words = self.narrate.word_timings(["One two."], [(start, end)])
        self.assertEqual((words[0]["from"], words[-1]["to"]), (start, end))

    def test_backticks_do_not_weigh(self):
        """Mutation: the backticks count toward the word's length (weights 4 and 6, not 2 and 4)."""
        words = self.narrate.word_timings(["`ab` c."], [(0.0, 1.0)])
        self.assertEqual(words[0], {"text": "`ab`", "from": 0.0, "to": 2 / 6})
        self.assertEqual(words[1], {"text": "c.", "from": 2 / 6, "to": 1.0})

    def test_word_text_is_the_token_verbatim(self):
        """Mutation: the word text is the spoken text (backticks removed) instead of the written token."""
        narration = "Run `verify.sh`, then stop. Really?"
        words = self.narrate.word_timings(self.split(narration), [(0.0, 1.0), (1.15, 2.0)])
        self.assertEqual([w["text"] for w in words], narration.split())


class Sentences(NarrateCase):
    """A brainrot script is narrated one sentence at a time and gets a words.json."""

    def brainrot(self, *scenes, format="brainrot"):
        path = self.write_script(list(scenes))
        data = json.loads(path.read_text(encoding="utf-8"))
        data["format"] = format
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def words_json(self, sid, engine):
        return json.loads((self.audio / f"{sid}.{engine}.words.json").read_text(encoding="utf-8"))

    def test_kokoro_per_sentence_times_are_exact(self):
        """Mutation: the 0.15 s gap is dropped, doubled or put after the last clip, or a time is
        taken from the clip length instead of the join frames."""
        run = self.run_kokoro(self.brainrot(scene("one", f"{ONE} {TWO}")))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        words = self.words_json("one", "kokoro")
        self.assertEqual(words["sentences"], [{"from": 0.0, "to": 0.5}, {"from": 0.65, "to": 1.15}])
        spoken_words = words["words"]   # Hello there. | A second line.
        self.assertEqual((spoken_words[0]["from"], spoken_words[2]["from"]), (0.0, 0.65))
        self.assertEqual((spoken_words[1]["to"], spoken_words[-1]["to"]), (0.5, 1.15))
        self.assertAlmostEqual(self.durations()["scenes"]["one"], 1.15, places=3)
        self.assertRegex(run.stdout.splitlines()[0], r"^narration: one kokoro 1\.150 s \(synthesized\)$")
        self.assertEqual(self.rate_of(self.audio / "one.kokoro.wav"), 24000)

    def test_kokoro_called_once_per_sentence_spoken(self):
        """Mutation: the whole narration goes to the engine in one call, or the sentences keep their backticks."""
        log = self.tmp / "stub.log"
        run = self.run_kokoro(self.brainrot(scene("one", "Run `verify.sh` now. Then stop.")), STUB_LOG=str(log))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(log.read_text(encoding="utf-8"), "Run verify.sh now.\nThen stop.\n")

    def test_words_match_narration(self):
        """Mutation: a word's text loses its backticks, or a line break or double space drops or merges a word."""
        narration = "Run `verify.sh`, then stop.\n\nReally?  Yes. Run the check"
        run = self.run_kokoro(self.brainrot(scene("one", narration)))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        words = self.words_json("one", "kokoro")
        self.assertEqual([w["text"] for w in words["words"]], narration.split())
        sentences = words["sentences"]
        self.assertEqual(len(sentences), 4)
        starts = [0, 4, 5, 6]   # index of the first word of each sentence
        for k, first in enumerate(starts):
            self.assertEqual(words["words"][first]["from"], sentences[k]["from"])
        self.assertEqual(words["words"][-1]["to"], sentences[-1]["to"])

    def test_say_per_sentence_join_positions(self):
        """Mutation: the join writes no gap, the gap is not 0.15 s, the joiner cannot read say's FLLR
        chunk, or the last word ends past the clip."""
        run = self.shell(self.brainrot(scene("one", f"{ONE} {TWO}")), "--engine", "say")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        wav = self.audio / "one.say.wav"
        words = self.words_json("one", "say")
        first, second = words["sentences"]
        self.assertEqual(first["from"], 0.0)
        self.assertAlmostEqual(second["from"] - first["to"], 0.15, delta=1 / 22050 + 1e-6)
        self.assertGreater(first["to"], 0.1)
        self.assertGreater(second["to"] - second["from"], 0.1)
        seconds = self.durations()["scenes"]["one"]
        self.assertLessEqual(words["words"][-1]["to"], seconds)
        self.assertAlmostEqual(words["words"][-1]["to"], seconds, delta=1e-5, msg="no padding after the last clip")
        self.assertEqual(self.rate_of(wav), 22050)

    def test_brainrot_sidecar_has_mode_line(self):
        """Mutation: the sidecar has no mode line for a brainrot script, or the mode line is not the
        fourth line."""
        run = self.shell(self.brainrot(scene("one", ONE)), "--engine", "say")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(
            (self.audio / "one.say.txt").read_text(encoding="utf-8"),
            f"engine=say\nvoice=say-default\nspeed=1.0\nmode=sentences\n{ONE}",
        )

    def test_film_is_narrated_in_sentences(self):
        """Mutation: film is missing from the format table of narrate.py (exit 2), or it maps to the
        whole-scene mode (no words.json, no mode line in the sidecar)."""
        run = self.shell(self.brainrot(scene("one", ONE), format="film"), "--engine", "say")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue((self.audio / "one.say.words.json").is_file())
        self.assertEqual(
            (self.audio / "one.say.txt").read_text(encoding="utf-8"),
            f"engine=say\nvoice=say-default\nspeed=1.0\nmode=sentences\n{ONE}",
        )

    def test_explainer_writes_no_words_json(self):
        """Mutation: every script gets a words.json or a mode line, or an explicit explainer is
        treated as brainrot."""
        for label, script in (
            ("no format", self.two_scenes()),
            ("explainer", self.brainrot(scene("one", ONE), scene("two", TWO), format="explainer")),
        ):
            with self.subTest(label):
                shutil.rmtree(self.audio, ignore_errors=True)
                run = self.shell(script, "--engine", "say")
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertEqual(list(self.audio.glob("*.words.json")), [])
                self.assertEqual(
                    (self.audio / "one.say.txt").read_text(encoding="utf-8"),
                    f"engine=say\nvoice=say-default\nspeed=1.0\n{ONE}",
                )

    def test_mode_change_resynthesizes(self):
        """Mutation: the reuse check ignores the mode line, so a scene made whole is reused as sentences."""
        for before, after in (("explainer", "brainrot"), ("brainrot", "explainer")):
            with self.subTest(f"{before} then {after}"):
                shutil.rmtree(self.audio, ignore_errors=True)
                first = self.shell(self.brainrot(scene("one", ONE), format=before), "--engine", "say")
                self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
                again = self.shell(self.brainrot(scene("one", ONE), format=before), "--engine", "say")
                self.assertRegex(again.stdout.splitlines()[0], r"\(reused\)$")
                run = self.shell(self.brainrot(scene("one", ONE), format=after), "--engine", "say")
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertRegex(run.stdout.splitlines()[0], r"^narration: one say .* \(synthesized\)$")

    def test_unknown_format_exit_2(self):
        """Mutation: an unknown format is narrated as an explainer, or fails with another code or text."""
        for value in ("tiktok", "", "Brainrot", 7, None, ["brainrot"]):
            with self.subTest(format=value):
                script = self.brainrot(scene("one", ONE), format=value)
                run = self.python(script, "--engine", "say")
                self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
                self.assertEqual(
                    run.stdout.strip(), f"narration: FAIL script {script}: format must be explainer or brainrot")
                self.assertFalse(self.audio.exists(), "nothing is narrated for an unknown format")

    def test_fallback_writes_say_words(self):
        """Mutation: the fallback narrates scenes whole, or writes the words file under the kokoro name."""
        run = self.shell(self.brainrot(scene("one", ONE), scene("two", TWO)))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stdout.splitlines()[0], "narration: FALLBACK say (models missing: kokoro-v1.0.onnx)")
        for sid in ("one", "two"):
            self.assertTrue((self.audio / f"{sid}.say.words.json").is_file())
        self.assertEqual(list(self.audio.glob("*.kokoro.*")), [])

    def test_words_json_layout(self):
        """Mutation: the file is not indented, has no trailing newline, or has other top-level keys."""
        self.run_kokoro(self.brainrot(scene("one", ONE)))
        raw = (self.audio / "one.kokoro.words.json").read_text(encoding="utf-8")
        data = json.loads(raw)
        self.assertEqual(sorted(data), ["sentences", "words"])
        self.assertEqual(raw, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        for entry in data["sentences"] + data["words"]:
            self.assertEqual(round(entry["from"], 6), entry["from"])
            self.assertEqual(round(entry["to"], 6), entry["to"])

    def narration_words(self, sid, engine):
        return [w["text"] for w in self.words_json(sid, engine)["words"]]

    def test_missing_words_json_resynthesizes(self):
        """Mutation: the reuse check looks at the WAV and sidecar only, so a clip whose words.json
        was deleted is reused with no word times."""
        script = self.brainrot(scene("one", f"{ONE} {TWO}"))
        self.assertEqual(self.shell(script, "--engine", "say").returncode, 0)
        words = self.audio / "one.say.words.json"
        words.unlink()
        run = self.shell(script, "--engine", "say")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertRegex(run.stdout.splitlines()[0], r"^narration: one say .* \(synthesized\)$")
        self.assertTrue(words.is_file(), "the words file is back")
        self.assertEqual(self.narration_words("one", "say"), f"{ONE} {TWO}".split())

    def test_stale_words_json_resynthesizes(self):
        """Mutation: the reuse check only tests that words.json exists, so another narration's words ship."""
        script = self.brainrot(scene("one", f"{ONE} {TWO}"))
        self.assertEqual(self.shell(script, "--engine", "say").returncode, 0)
        words = self.audio / "one.say.words.json"
        stale = {"sentences": [{"from": 0.0, "to": 1.0}],
                 "words": [{"text": "Something", "from": 0.0, "to": 0.5}, {"text": "else.", "from": 0.5, "to": 1.0}]}
        words.write_text(json.dumps(stale), encoding="utf-8")
        run = self.shell(script, "--engine", "say")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertRegex(run.stdout.splitlines()[0], r"^narration: one say .* \(synthesized\)$")
        self.assertEqual(self.narration_words("one", "say"), f"{ONE} {TWO}".split())

    def test_unusable_words_json_resynthesizes(self):
        """Mutation: an unparseable or wrongly shaped words.json crashes the reuse check or counts as current."""
        script = self.brainrot(scene("one", ONE))
        self.assertEqual(self.run_kokoro(script).returncode, 0)
        words = self.audio / "one.kokoro.words.json"
        for label, content in (
            ("not json", "{ nope"), ("empty file", ""), ("a list", "[]"), ("no words key", "{}"),
            ("words not a list", '{"words": 5}'), ("word not an object", '{"words": [1, 2]}'),
            ("word without text", '{"words": [{"from": 0.0}, {"from": 1.0}]}'),
        ):
            with self.subTest(label):
                words.write_text(content, encoding="utf-8")
                run = self.run_kokoro(script)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertRegex(run.stdout.splitlines()[0], r"\(synthesized\)$")
                self.assertEqual(self.narration_words("one", "kokoro"), ONE.split())

    def test_reuse_keeps_wav_and_words(self):
        """Mutation: a reused clip is rewritten, or its words.json is deleted and rebuilt on every run."""
        script = self.brainrot(scene("one", f"{ONE} {TWO}"))
        self.assertEqual(self.shell(script, "--engine", "say").returncode, 0)
        files = [self.audio / "one.say.wav", self.audio / "one.say.words.json", self.audio / "one.say.txt"]
        before = [(f.stat().st_ino, f.stat().st_mtime_ns) for f in files]
        run = self.shell(script, "--engine", "say")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertRegex(run.stdout.splitlines()[0], r"^narration: one say .* \(reused\)$")
        self.assertEqual([(f.stat().st_ino, f.stat().st_mtime_ns) for f in files], before)

    def test_failed_sentence_leaves_nothing(self):
        """Mutation: the failed scene keeps its WAV, sidecar or words.json (or only the WAV is removed)."""
        script = self.brainrot(scene("one", ONE), scene("two", "Fine. BOOM now."))
        run = self.run_kokoro(script)
        self.assertEqual(run.returncode, 3, run.stdout + run.stderr)
        self.assertEqual(run.stdout.splitlines()[-1], "narration: FAIL kokoro clip failed: two: stub exploded")
        self.assertEqual(sorted(p.name for p in self.audio.glob("two.*")), [])
        self.assertTrue((self.audio / "one.kokoro.words.json").is_file(), "the finished scene keeps its files")

    def test_failed_resynthesis_removes_the_old_clip(self):
        """Mutation: a scene that re-synthesises and fails leaves the previous run's words.json, which
        then pairs with no WAV."""
        self.assertEqual(self.run_kokoro(self.brainrot(scene("one", "Fine. Okay now."))).returncode, 0)
        self.assertTrue((self.audio / "one.kokoro.words.json").is_file())
        run = self.run_kokoro(self.brainrot(scene("one", "Fine. BOOM now.")))
        self.assertEqual(run.returncode, 3, run.stdout + run.stderr)
        self.assertEqual(sorted(p.name for p in self.audio.glob("one.*")), [])

    def test_speed_reaches_every_sentence_and_the_sidecar(self):
        """Mutation: the sentence path drops --speed (no -r, or one -r per scene), or the sidecar loses
        the speed line before the mode line."""
        env = self.rate_log_env()
        run = self.shell(self.brainrot(scene("one", f"{ONE} {TWO}")), "--engine", "say", "--speed", "1.2", env=env)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(self.rate_log.read_text(encoding="utf-8"), "210\n210\n")
        self.assertEqual(
            (self.audio / "one.say.txt").read_text(encoding="utf-8"),
            f"engine=say\nvoice=say-default\nspeed=1.2\nmode=sentences\n{ONE} {TWO}",
        )

    def test_explainer_run_removes_a_words_json_left_by_a_brainrot_run(self):
        """Mutation: an explainer scene leaves a brainrot words.json beside its clip, whether the clip
        is re-made (the earlier run was brainrot) or reused (the file was planted later)."""
        brainrot_run = self.shell(self.brainrot(scene("one", ONE)), "--engine", "say")
        self.assertEqual(brainrot_run.returncode, 0, brainrot_run.stdout + brainrot_run.stderr)
        words = self.audio / "one.say.words.json"
        self.assertTrue(words.is_file())
        explainer = self.brainrot(scene("one", ONE), format="explainer")
        run = self.shell(explainer, "--engine", "say")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertRegex(run.stdout.splitlines()[0], r"\(synthesized\)$")
        self.assertFalse(words.exists(), "re-made as a whole clip: no words file")
        words.write_text('{"sentences": [], "words": []}', encoding="utf-8")
        run = self.shell(explainer, "--engine", "say")
        self.assertRegex(run.stdout.splitlines()[0], r"\(reused\)$")
        self.assertFalse(words.exists(), "reused as a whole clip: the planted words file is removed")


def wav_bytes(rate, frames, width=2, channels=1, extra_chunk=b"", claim_extra=0):
    """A PCM WAV by hand; extra_chunk (a full chunk, header included) sits between fmt and data;
    claim_extra makes the data chunk's header claim that many bytes more than the file holds."""
    data = frames
    fmt = struct.pack("<HHIIHH", 1, channels, rate, rate * width * channels, width * channels, width * 8)
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + extra_chunk
    body += b"data" + struct.pack("<I", len(data) + claim_extra) + data
    return b"RIFF" + struct.pack("<I", len(body)) + body


class JoinClips(unittest.TestCase):
    """join_clips on hand-made WAVs: no engine, no process."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("narrate_under_test_join", NARRATE_PY)
        cls.narrate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.narrate)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="join-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.out = self.tmp / "out.wav"

    def clip(self, name, **kwargs):
        path = self.tmp / name
        path.write_bytes(wav_bytes(**kwargs))
        return path

    def read(self):
        with wave.open(str(self.out), "rb") as wav:
            return wav.getframerate(), wav.getsampwidth(), wav.getnchannels(), wav.readframes(wav.getnframes())

    def test_join_puts_the_gap_between_clips_only(self):
        """Mutation: a gap before the first clip or after the last, or a gap of another length."""
        a = self.clip("a.wav", rate=1000, frames=b"\x01\x00" * 100)
        b = self.clip("b.wav", rate=1000, frames=b"\x02\x00" * 50)
        rate, spans = self.narrate.join_clips([a, b], self.out, 0.15)
        self.assertEqual((rate, spans), (1000, [(0, 100), (250, 300)]))
        self.assertEqual(
            self.read(), (1000, 2, 1, b"\x01\x00" * 100 + b"\x00\x00" * 150 + b"\x02\x00" * 50))

    def test_join_one_clip_has_no_gap(self):
        """Mutation: the gap is written after every clip, the last one included."""
        a = self.clip("a.wav", rate=1000, frames=b"\x01\x00" * 10)
        self.assertEqual(self.narrate.join_clips([a], self.out, 0.15), (1000, [(0, 10)]))
        self.assertEqual(self.read()[3], b"\x01\x00" * 10)

    def test_join_gap_is_rounded_to_whole_frames(self):
        """Mutation: the gap is truncated (int) instead of rounded."""
        a = self.clip("a.wav", rate=1000, frames=b"\x01\x00" * 10)
        _, spans = self.narrate.join_clips([a, a], self.out, 0.0026)
        self.assertEqual(spans, [(0, 10), (13, 23)])

    def test_join_reads_past_extra_chunks(self):
        """Mutation: the reader stops at an unknown chunk (say writes FLLR between fmt and data)."""
        filler = b"FLLR" + (100).to_bytes(4, "little") + b"\x00" * 100
        a = self.clip("a.wav", rate=22050, frames=b"\x01\x00" * 40, extra_chunk=filler)
        b = self.clip("b.wav", rate=22050, frames=b"\x02\x00" * 40, extra_chunk=filler)
        rate, spans = self.narrate.join_clips([a, b], self.out, 0.15)
        self.assertEqual((rate, spans), (22050, [(0, 40), (3348, 3388)]))
        self.assertEqual(len(self.read()[3]), 2 * 3388)

    def test_join_spans_follow_the_frames_read_not_the_header(self):
        """Mutation: a clip's span length comes from the header's frame count, so a truncated clip
        (header claims 30 frames, data holds 10) shifts every later span past the audio."""
        a = self.clip("a.wav", rate=1000, frames=b"\x01\x00" * 10, claim_extra=40)
        b = self.clip("b.wav", rate=1000, frames=b"\x02\x00" * 5)
        rate, spans = self.narrate.join_clips([a, b], self.out, 0.15)
        self.assertEqual((rate, spans), (1000, [(0, 10), (160, 165)]))
        self.assertEqual(len(self.read()[3]), 2 * 165, "the joined file holds exactly the span frames")

    def test_join_drops_a_partial_trailing_frame(self):
        """Mutation: a truncated clip that ends mid-frame keeps its stray byte, which shifts the next
        clip's samples by one byte (and the file's frame count off the spans)."""
        a = self.clip("a.wav", rate=1000, frames=b"\x01\x00" * 10 + b"\x07", claim_extra=40)
        b = self.clip("b.wav", rate=1000, frames=b"\x02\x00" * 5)
        _, spans = self.narrate.join_clips([a, b], self.out, 0.15)
        self.assertEqual(spans, [(0, 10), (160, 165)])
        self.assertEqual(self.read()[3], b"\x01\x00" * 10 + b"\x00\x00" * 150 + b"\x02\x00" * 5)

    def test_join_rejects_a_clip_that_differs_and_names_it(self):
        """Mutation: a clip with another rate, width or channel count is joined as if it matched."""
        good = self.clip("good.wav", rate=1000, frames=b"\x01\x00" * 10)
        cases = {
            "rate": self.clip("rate.wav", rate=2000, frames=b"\x01\x00" * 10),
            "width": self.clip("width.wav", rate=1000, frames=b"\x01" * 10, width=1),
            "channels": self.clip("channels.wav", rate=1000, frames=b"\x01\x00" * 10, channels=2),
        }
        for label, bad in cases.items():
            with self.subTest(label):
                with self.assertRaisesRegex(self.narrate.NarrationError, bad.name):
                    self.narrate.join_clips([good, bad], self.out, 0.15)
                self.assertFalse(self.out.exists(), "a refused join writes nothing")

    def test_join_rejects_a_first_clip_that_is_not_16_bit_mono(self):
        """Mutation: the first clip sets the format, so a stereo or 8-bit set is joined into a 16-bit mono header."""
        stereo = self.clip("stereo.wav", rate=1000, frames=b"\x01\x00" * 10, channels=2)
        with self.assertRaisesRegex(self.narrate.NarrationError, "stereo.wav"):
            self.narrate.join_clips([stereo], self.out, 0.15)

    def test_join_of_no_clips_is_refused(self):
        """Mutation: an empty list writes an empty WAV with no rate."""
        with self.assertRaises(self.narrate.NarrationError):
            self.narrate.join_clips([], self.out, 0.15)


if __name__ == "__main__":
    unittest.main()
