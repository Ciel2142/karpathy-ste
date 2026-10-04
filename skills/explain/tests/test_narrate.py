"""Tests for scripts/narrate.sh and video/narrate.py: narration with Kokoro and a labelled
say fallback. The real `say` and `afinfo` run (macOS); Kokoro and uv are stubbed, so no
model, no network and no uv are needed. Each test names the mutation that turns it red."""

import importlib.util
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

EXPLAIN = Path(__file__).resolve().parent.parent
NARRATE_SH = EXPLAIN / "scripts" / "narrate.sh"
NARRATE_PY = EXPLAIN / "video" / "narrate.py"
TEMPLATE = EXPLAIN / "templates" / "video-script.json"
ONE = "Hello there."
TWO = "A second line."

# A stand-in for kokoro_onnx: 0.5 s of silence at STUB_RATE (default 24000); the text BOOM
# raises, as a real clip failure would. It insists on speed STUB_SPEED (default 1.0) and,
# when STUB_LOG is set, appends each create() text to that file. Its twin stand-in for
# soundfile writes a 16-bit WAV.
STUB_KOKORO = '''
import os
class Kokoro:
    def __init__(self, model, voices):
        open(model, "rb").close()
        open(voices, "rb").close()
    def create(self, text, voice, speed, lang):
        want = float(os.environ.get("STUB_SPEED", "1.0"))
        assert (voice, speed, lang) == ("af_heart", want, "en-us"), (voice, speed, lang)
        if os.environ.get("STUB_LOG"):
            with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as log:
                log.write(text + "\\n")
        if "BOOM" in text:
            raise RuntimeError("stub exploded")
        rate = int(os.environ.get("STUB_RATE", "24000"))
        return [0.0] * (rate // 2), rate
'''
STUB_SOUNDFILE = '''
import wave
def write(path, samples, rate, subtype):
    assert subtype == "PCM_16", subtype
    with wave.open(path, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b"\\0\\0" * len(samples))
'''
# A say that records the text file it is given (and, when FAKE_SAY_RATE_LOG is set, the -r
# value or "-" when absent), then runs the real say; FAKE_SAY_RATE moves the output rate off 22050.
FAKE_SAY = """#!/bin/sh
rate=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    -f) cat "$2" >> "$FAKE_SAY_LOG"; text="$2"; shift 2 ;;
    -r) rate="$2"; shift 2 ;;
    *) shift ;;
  esac
done
[ -z "${FAKE_SAY_RATE_LOG:-}" ] || echo "${rate:--}" >> "$FAKE_SAY_RATE_LOG"
if [ -n "$rate" ]; then
  exec /usr/bin/say --file-format=WAVE --data-format=LEI16@${FAKE_SAY_RATE:-22050} -r "$rate" -o "$out" -f "$text"
fi
exec /usr/bin/say --file-format=WAVE --data-format=LEI16@${FAKE_SAY_RATE:-22050} -o "$out" -f "$text"
"""
# A uv that logs its arguments and runs the python3 command after them with the caller's env.
FAKE_UV = """#!/bin/sh
echo "$@" > "$FAKE_UV_LOG"
while [ "$1" != python3 ]; do shift; done
shift
exec python3 "$@"
"""


def scene(sid, narration):
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))["scenes"][0]
    return dict(template, id=sid, narration=narration)


class NarrateCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="narrate-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.workspace = self.tmp / "ws"
        (self.workspace / "models").mkdir(parents=True)
        self.audio = self.tmp / "audio"
        self.env = dict(os.environ, EXPLAIN_VIDEO_WORKSPACE=str(self.workspace))

    def write_script(self, scenes):
        path = self.tmp / "script.json"
        template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        template["scenes"] = scenes
        path.write_text(json.dumps(template), encoding="utf-8")
        return path

    def two_scenes(self, first=ONE, second=TWO):
        return self.write_script([scene("one", first), scene("two", second)])

    def shell(self, script, *extra, env=None):
        return subprocess.run(
            ["/bin/bash", str(NARRATE_SH), str(script), str(self.audio), *extra],
            capture_output=True, text=True, env=env or self.env,
        )

    def python(self, script, *extra, env=None):
        return subprocess.run(
            [sys.executable, str(NARRATE_PY), *extra, str(script), str(self.audio)],
            capture_output=True, text=True, env=env or self.env,
        )

    def tool(self, name, body):
        """Put an executable `name` in tmp/bin and return that directory."""
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir(exist_ok=True)
        path = bin_dir / name
        path.write_text(body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return bin_dir

    def with_path_first(self, bin_dir, **extra):
        return dict(self.env, PATH=f"{bin_dir}:{os.environ['PATH']}", **extra)

    def rate_log_env(self):
        """An env whose say is FAKE_SAY, logging each -r value to self.rate_log."""
        self.rate_log = self.tmp / "say-rate.log"
        return self.with_path_first(
            self.tool("say", FAKE_SAY),
            FAKE_SAY_LOG=str(self.tmp / "say.log"), FAKE_SAY_RATE_LOG=str(self.rate_log),
        )

    def stub_modules(self):
        stubs = self.tmp / "stubs"
        stubs.mkdir(exist_ok=True)   # a test may run Kokoro more than once
        (stubs / "kokoro_onnx.py").write_text(STUB_KOKORO, encoding="utf-8")
        (stubs / "soundfile.py").write_text(STUB_SOUNDFILE, encoding="utf-8")
        for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
            (self.workspace / "models" / name).write_bytes(b"")
        return str(stubs)

    def run_kokoro(self, script, **extra):
        """narrate.py --engine kokoro with the stub modules, extra env as keywords."""
        env = dict(self.env, PYTHONPATH=self.stub_modules(), **extra)
        return self.python(script, "--engine", "kokoro", "--models", str(self.workspace / "models"), env=env)

    def durations(self):
        return json.loads((self.audio / "durations.json").read_text(encoding="utf-8"))

    @staticmethod
    def rate_of(wav):
        out = subprocess.run(["afinfo", str(wav)], capture_output=True, text=True, check=True).stdout
        return int(re.search(r"(\d+) Hz", out).group(1))


class SayRun(NarrateCase):
    def test_say_engine_writes_wav_sidecar_and_durations(self):
        """Mutation: the sidecar omits the speed line."""
        run = self.shell(self.two_scenes(), "--engine", "say")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        for sid, text in (("one", ONE), ("two", TWO)):
            self.assertEqual(self.rate_of(self.audio / f"{sid}.say.wav"), 22050)
            self.assertEqual(
                (self.audio / f"{sid}.say.txt").read_text(encoding="utf-8"),
                f"engine=say\nvoice=say-default\nspeed=1.0\n{text}",
            )
        durations = self.durations()
        self.assertEqual((durations["engine"], durations["fallback"]), ("say", None))
        self.assertEqual(sorted(durations["scenes"]), ["one", "two"])
        for seconds in durations["scenes"].values():
            self.assertIsInstance(seconds, float)
            self.assertGreater(seconds, 0)
        lines = run.stdout.splitlines()
        self.assertRegex(lines[0], r"^narration: one say \d+\.\d{3} s \(synthesized\)$")
        self.assertRegex(lines[1], r"^narration: two say \d+\.\d{3} s \(synthesized\)$")

    def test_unchanged_narration_reuses_wav(self):
        """Mutation: the sidecar is ignored and every run synthesizes."""
        script = self.two_scenes()
        self.shell(script, "--engine", "say")
        wav = self.audio / "one.say.wav"
        before = (wav.stat().st_ino, wav.stat().st_mtime_ns)
        run = self.shell(script, "--engine", "say")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertRegex(run.stdout.splitlines()[0], r"\(reused\)$")
        self.assertEqual((wav.stat().st_ino, wav.stat().st_mtime_ns), before)

    def test_changed_text_resynthesizes(self):
        """Mutation: only the engine line of the sidecar is compared."""
        self.shell(self.two_scenes(), "--engine", "say")
        wav = self.audio / "one.say.wav"
        before = wav.stat().st_mtime_ns
        run = self.shell(self.two_scenes(first="Hello again."), "--engine", "say")
        lines = run.stdout.splitlines()
        self.assertRegex(lines[0], r"^narration: one say .* \(synthesized\)$")
        self.assertRegex(lines[1], r"^narration: two say .* \(reused\)$")
        self.assertNotEqual(wav.stat().st_mtime_ns, before)
        self.assertTrue((self.audio / "one.say.txt").read_text(encoding="utf-8").endswith("\nHello again."))

    def test_speed_is_recorded_in_sidecar(self):
        """Mutation: the sidecar writes a fixed speed=1.0 whatever --speed says."""
        run = self.shell(self.two_scenes(), "--engine", "say", "--speed", "1.2")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(
            (self.audio / "one.say.txt").read_text(encoding="utf-8"),
            "engine=say\nvoice=say-default\nspeed=1.2\nHello there.",
        )

    def test_say_rate_follows_speed(self):
        """Mutation: say gets no -r at speed 1.2, or a -r at the default speed."""
        env = self.rate_log_env()
        script = self.write_script([scene("one", ONE)])
        self.assertEqual(self.shell(script, "--engine", "say", "--speed", "1.2", env=env).returncode, 0)
        self.assertEqual(self.rate_log.read_text(encoding="utf-8"), "210\n")
        self.rate_log.unlink()
        shutil.rmtree(self.audio)
        self.assertEqual(self.shell(script, "--engine", "say", env=env).returncode, 0)
        self.assertEqual(self.rate_log.read_text(encoding="utf-8"), "-\n")

    def test_changed_speed_resynthesizes(self):
        """Mutation: the reuse check compares the text but not the speed line."""
        script = self.two_scenes()
        self.shell(script, "--engine", "say")
        run = self.shell(script, "--engine", "say", "--speed", "1.2")
        lines = run.stdout.splitlines()
        self.assertRegex(lines[0], r"^narration: one say .* \(synthesized\)$")
        self.assertRegex(lines[1], r"^narration: two say .* \(synthesized\)$")

    def test_speed_bounds_are_accepted(self):
        """Mutation: the range check is off by one at either end (0.5 or 2.0 rejected)."""
        for speed in ("0.5", "2.0"):
            with self.subTest(speed):
                run = self.shell(self.write_script([scene("one", ONE)]), "--engine", "say", "--speed", speed)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertTrue((self.audio / "one.say.txt").read_text(encoding="utf-8").startswith(
                    f"engine=say\nvoice=say-default\nspeed={speed}\n"))

    def test_engine_in_filename_keeps_both_voices(self):
        """Mutation: one file per scene id (<id>.wav) instead of <id>.<engine>.wav."""
        self.audio.mkdir()
        (self.audio / "one.kokoro.wav").write_bytes(b"kokoro clip")
        (self.audio / "one.kokoro.txt").write_text("kokoro sidecar", encoding="utf-8")
        run = self.shell(self.two_scenes(), "--engine", "say")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual((self.audio / "one.kokoro.wav").read_bytes(), b"kokoro clip")
        self.assertEqual((self.audio / "one.kokoro.txt").read_text(encoding="utf-8"), "kokoro sidecar")
        self.assertTrue((self.audio / "one.say.wav").is_file())

    def test_narration_starting_with_dash_is_spoken(self):
        """Mutation: the text is passed to say as an argument instead of through -f."""
        run = self.shell(self.write_script([scene("flag", "-v is the verbose flag.")]), "--engine", "say")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        seconds = self.durations()["scenes"]["flag"]
        self.assertGreater(seconds, 0.5)

    def test_backticks_are_not_spoken(self):
        """Mutation: the narration reaches say verbatim, backticks included."""
        bin_dir = self.tool("say", FAKE_SAY)
        log = self.tmp / "say.log"
        env = self.with_path_first(bin_dir, FAKE_SAY_LOG=str(log))
        run = self.shell(self.write_script([scene("code", "Run `verify.sh` now.")]), "--engine", "say", env=env)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(log.read_text(encoding="utf-8"), "Run verify.sh now.")
        sidecar = (self.audio / "code.say.txt").read_text(encoding="utf-8")
        self.assertTrue(sidecar.endswith("\nRun `verify.sh` now."), "the sidecar keeps the narration verbatim")

    def test_wrong_sample_rate_fails(self):
        """Mutation: the afinfo rate check is removed."""
        bin_dir = self.tool("say", FAKE_SAY)
        env = self.with_path_first(bin_dir, FAKE_SAY_LOG=str(self.tmp / "say.log"), FAKE_SAY_RATE="44100")
        run = self.shell(self.write_script([scene("odd", ONE)]), "--engine", "say", env=env)
        self.assertEqual(run.returncode, 1)
        self.assertEqual(
            run.stdout.strip(),
            f"narration: FAIL scene odd: {self.audio / 'odd.say.wav'} is 44100 Hz (expected 22050)",
        )
        self.assertFalse((self.audio / "odd.say.txt").exists(), "a wrong-rate clip must not look current")

    def test_empty_narration_fails(self):
        """Mutation: the empty-narration check is removed."""
        run = self.shell(self.write_script([scene("one", ONE), scene("blank", "  \n ")]), "--engine", "say")
        self.assertEqual(run.returncode, 1)
        self.assertEqual(run.stdout.strip(), "narration: FAIL scene blank: narration is empty")
        self.assertFalse(self.audio.exists() and any(self.audio.glob("*.wav")), "no scene is synthesized first")

    def test_missing_afinfo_fails(self):
        """Mutation: the tool check is removed (afinfo then dies with a traceback)."""
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "python3").symlink_to(shutil.which("python3"))
        (bin_dir / "say").symlink_to("/usr/bin/say")
        env = dict(self.env, PATH=str(bin_dir))
        run = self.shell(self.two_scenes(), "--engine", "say", env=env)
        self.assertEqual((run.returncode, run.stdout.strip()), (1, "narration: FAIL afinfo not found"))


class UsageErrors(NarrateCase):
    def test_usage_error_exit_2(self):
        """Mutation: a bad --engine is passed through instead of rejected."""
        script = self.two_scenes()
        cases = {
            "no arguments": [],
            "one argument": [str(script)],
            "bad engine": [str(script), str(self.audio), "--engine", "festival"],
            "engine without value": [str(script), str(self.audio), "--engine"],
            "no such script": [str(self.tmp / "absent.json"), str(self.audio)],
        }
        for label, args in cases.items():
            with self.subTest(label):
                run = subprocess.run(["/bin/bash", str(NARRATE_SH), *args], capture_output=True, text=True, env=self.env)
                self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertFalse(self.audio.exists())

    def test_bad_speed_is_usage_error(self):
        """Mutation: --speed is forwarded unchecked, or only the shape (not the 0.5-2.0 range) is checked."""
        script = self.two_scenes()
        for speed in ("1.25", "2.5", "2.1", "0.4", "-1.0", "fast", ""):
            with self.subTest(speed=speed):
                run = self.shell(script, "--speed", speed)
                self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
                self.assertEqual(
                    run.stderr.strip(), "usage: narrate.sh <script.json> <audio-dir> [--engine kokoro|say] [--speed <d.d>]")
                self.assertFalse(self.audio.exists(), "no engine runs on a bad speed")
        self.assertEqual(self.shell(script, "--speed").returncode, 2, "--speed without a value")

    def test_python_bad_speed_exit_2(self):
        """Mutation: narrate.py takes any --speed (only narrate.sh validates)."""
        run = self.python(self.two_scenes(), "--engine", "say", "--speed", "3.0")
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertIn("between 0.5 and 2.0", run.stderr, "rejected by the speed check, not as an unknown option")
        self.assertFalse(self.audio.exists())


class Fallback(NarrateCase):
    def assert_fallback(self, run, cause):
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stdout.splitlines()[0], f"narration: FALLBACK say ({cause})")
        durations = self.durations()
        self.assertEqual((durations["engine"], durations["fallback"]), ("say", cause))
        self.assertTrue((self.audio / "one.say.wav").is_file())

    def test_missing_models_falls_back_to_say_with_cause(self):
        """Mutation: a missing model ends the run with exit 1 instead of falling back."""
        run = self.shell(self.two_scenes())
        self.assert_fallback(run, "models missing: kokoro-v1.0.onnx")

    def test_missing_voices_file_is_named(self):
        """Mutation: the voices file is not checked (only the onnx model is)."""
        (self.workspace / "models" / "kokoro-v1.0.onnx").write_bytes(b"")
        bin_dir = self.tool("uv", "#!/bin/sh\necho 'uv must not run' >&2\nexit 99\n")
        run = self.shell(self.two_scenes(), "--engine", "kokoro", env=self.with_path_first(bin_dir))
        self.assert_fallback(run, "models missing: voices-v1.0.bin")

    def test_uv_missing_falls_back(self):
        """Mutation: no PATH check for uv (the shell then fails with command not found)."""
        for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
            (self.workspace / "models" / name).write_bytes(b"")
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        for name, target in (("say", "/usr/bin/say"), ("afinfo", "/usr/bin/afinfo"),
                             ("python3", shutil.which("python3")), ("sh", "/bin/sh")):
            (bin_dir / name).symlink_to(target)
        run = self.shell(self.two_scenes(), env=dict(self.env, PATH=str(bin_dir)))
        self.assert_fallback(run, "uv not found")

    def test_uv_failure_falls_back_with_last_stderr_line(self):
        """Mutation: the cause drops the last stderr line of the failed uv run."""
        self.stub_modules()
        bin_dir = self.tool("uv", "#!/bin/sh\necho 'resolving' >&2\necho 'no solution found' >&2\nexit 2\n")
        run = self.shell(self.two_scenes(), env=self.with_path_first(bin_dir))
        self.assert_fallback(run, "uv run failed: no solution found")

    def test_kokoro_clip_failure_falls_back_with_scene_and_message(self):
        """Mutation: exit 3 is treated like any other uv failure (cause loses the scene id)."""
        stubs = self.stub_modules()
        bin_dir = self.tool("uv", FAKE_UV)
        env = self.with_path_first(bin_dir, PYTHONPATH=stubs, FAKE_UV_LOG=str(self.tmp / "uv.log"))
        run = self.shell(self.write_script([scene("one", ONE), scene("two", "BOOM")]), env=env)
        self.assert_fallback(run, "kokoro clip failed: two: stub exploded")
        self.assertNotIn("one kokoro", run.stdout, "the failed Kokoro attempt prints no scene lines")

    def test_kokoro_run_uses_pinned_uv_command_and_writes_kokoro_files(self):
        """Mutation: a pinned --with package is dropped from the uv command."""
        stubs = self.stub_modules()
        bin_dir = self.tool("uv", FAKE_UV)
        log = self.tmp / "uv.log"
        env = self.with_path_first(bin_dir, PYTHONPATH=stubs, FAKE_UV_LOG=str(log))
        run = self.shell(self.two_scenes(), env=env)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertNotIn("FALLBACK", run.stdout)
        self.assertEqual(
            log.read_text(encoding="utf-8").split("python3")[0].split(),
            "run --python 3.12 --with kokoro-onnx==0.6.1 --with onnxruntime==1.30.0 --with soundfile==0.14.0 "
            "--with numpy==2.5.3 --with espeakng-loader==0.2.4".split(),
        )
        self.assertEqual(self.rate_of(self.audio / "one.kokoro.wav"), 24000)
        self.assertEqual(
            (self.audio / "one.kokoro.txt").read_text(encoding="utf-8"),
            f"engine=kokoro\nvoice=af_heart\nspeed=1.0\n{ONE}",
        )
        durations = self.durations()
        self.assertEqual((durations["engine"], durations["fallback"]), ("kokoro", None))
        self.assertAlmostEqual(durations["scenes"]["one"], 0.5, places=2)
        self.assertRegex(run.stdout.splitlines()[0], r"^narration: one kokoro 0\.500 s \(synthesized\)$")

    def test_kokoro_gets_speed(self):
        """Mutation: the uv line drops --speed, or Kokoro is called with a fixed speed=1.0."""
        stubs = self.stub_modules()
        bin_dir = self.tool("uv", FAKE_UV)
        env = self.with_path_first(bin_dir, PYTHONPATH=stubs, FAKE_UV_LOG=str(self.tmp / "uv.log"), STUB_SPEED="1.2")
        run = self.shell(self.two_scenes(), "--speed", "1.2", env=env)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertNotIn("FALLBACK", run.stdout, "the stub fails a clip whose speed is not 1.2")
        self.assertEqual(
            (self.audio / "one.kokoro.txt").read_text(encoding="utf-8"),
            f"engine=kokoro\nvoice=af_heart\nspeed=1.2\n{ONE}",
        )

    def test_fallback_keeps_speed(self):
        """Mutation: the say fallback drops --speed (default rate, speed=1.0 in the sidecar)."""
        run = self.shell(self.two_scenes(), "--speed", "1.2", env=self.rate_log_env())
        self.assert_fallback(run, "models missing: kokoro-v1.0.onnx")
        self.assertEqual(self.rate_log.read_text(encoding="utf-8"), "210\n210\n")
        self.assertTrue((self.audio / "one.say.txt").read_text(encoding="utf-8").startswith(
            "engine=say\nvoice=say-default\nspeed=1.2\n"))


class KokoroDirect(NarrateCase):
    def test_clip_exception_exits_3_and_leaves_no_clip(self):
        """Mutation: a Kokoro exception escapes as a traceback (exit 1, no FAIL line)."""
        run = self.run_kokoro(self.write_script([scene("one", ONE), scene("two", "BOOM")]))
        self.assertEqual(run.returncode, 3, run.stdout + run.stderr)
        self.assertEqual(run.stdout.splitlines()[-1], "narration: FAIL kokoro clip failed: two: stub exploded")
        self.assertFalse((self.audio / "two.kokoro.wav").exists())
        self.assertFalse((self.audio / "two.kokoro.txt").exists())

    def test_wrong_kokoro_rate_fails_with_exit_1(self):
        """Mutation: the rate check expects 22050 for every engine."""
        run = self.run_kokoro(self.write_script([scene("one", ONE)]), STUB_RATE="22050")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertRegex(run.stdout.strip(), r"^narration: FAIL scene one: .*one\.kokoro\.wav is 22050 Hz \(expected 24000\)$")

    def test_models_missing_exits_3(self):
        """Mutation: a missing voices file is not checked before the Kokoro engine starts."""
        stubs = self.stub_modules()
        (self.workspace / "models" / "voices-v1.0.bin").unlink()
        run = self.python(
            self.two_scenes(), "--engine", "kokoro", "--models", str(self.workspace / "models"),
            env=dict(self.env, PYTHONPATH=stubs),
        )
        self.assertEqual((run.returncode, run.stdout.strip()), (3, "narration: FAIL models missing: voices-v1.0.bin"))

    def test_fallback_flag_is_recorded_in_durations(self):
        """Mutation: --fallback is parsed but durations.json always says null."""
        run = self.python(self.two_scenes(), "--engine", "say", "--fallback", "uv not found")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(self.durations()["fallback"], "uv not found")


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
