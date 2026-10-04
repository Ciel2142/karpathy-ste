"""Tests for scripts/narrate.sh and video/narrate.py: narration with Kokoro and a labelled
say fallback. The real `say` and `afinfo` run (macOS); Kokoro and uv are stubbed, so no
model, no network and no uv are needed. Each test names the mutation that turns it red."""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
