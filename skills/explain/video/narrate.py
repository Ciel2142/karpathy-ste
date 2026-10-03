#!/usr/bin/env python3
"""Narration for the explain video rung: one WAV per scene, real lengths from afinfo.

Usage: narrate.py --engine say|kokoro [--models <dir>] [--fallback "<cause>"] <script.json> <audio-dir>

Writes <audio-dir>/<id>.<engine>.wav (16-bit PCM mono: Kokoro 24000 Hz, say 22050 Hz),
a sidecar <id>.<engine>.txt (engine, voice, speed, narration) and durations.json:
{ "engine", "fallback", "scenes": { "<id>": seconds } }.

Exit 0 on success; 1 on a failed scene or a missing tool; 2 on a usage error or an
unreadable script; 3 when Kokoro cannot run (models missing, or a clip failed), which
narrate.sh turns into the say fallback. The say path is stdlib only; kokoro_onnx and
soundfile are imported lazily by the Kokoro engine.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SPEED = "1.0"
KOKORO_VOICE = "af_heart"
KOKORO_RATE = 24000
SAY_VOICE = "say-default"
SAY_RATE = 22050
MODEL_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
RATE_LINE = re.compile(r"Data format:.*?(\d+) Hz")
DURATION_LINE = re.compile(r"estimated duration:\s*([0-9.]+)")


class NarrationError(Exception):
    """A fault that ends the run: main() prints 'narration: FAIL <message>' and exits with code."""

    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


class SynthError(Exception):
    """One engine failed to make one clip; the engine's failure() words it."""


def afinfo_output(wav):
    run = subprocess.run(["afinfo", str(wav)], capture_output=True, text=True)
    if run.returncode != 0:
        raise NarrationError(f"afinfo cannot read {wav}")
    return run.stdout


def afinfo_seconds(wav):
    match = DURATION_LINE.search(afinfo_output(wav))
    if not match:
        raise NarrationError(f"afinfo printed no 'estimated duration' for {wav}")
    return float(match.group(1))


def afinfo_rate(wav):
    match = RATE_LINE.search(afinfo_output(wav))
    if not match:
        raise NarrationError(f"afinfo printed no sample rate for {wav}")
    return int(match.group(1))


def sidecar_text(engine, text):
    return f"engine={engine.name}\nvoice={engine.voice}\nspeed={SPEED}\n{text}"


def sidecar_matches(sidecar, engine, text):
    """True when the sidecar exists and all four fields equal what this run would write."""
    if not sidecar.is_file():
        return False
    return sidecar.read_bytes().decode("utf-8") == sidecar_text(engine, text)


def spoken(text):
    """The text the engine reads: a code name in backticks is spoken as plain text."""
    return text.replace("`", "")


def synth_say(text, wav):
    # The text goes through a file (-f), never as an argument: a narration that starts
    # with "-" would otherwise be parsed by say as an option.
    with tempfile.TemporaryDirectory() as scratch:
        source = Path(scratch) / "narration.txt"
        source.write_text(spoken(text), encoding="utf-8")
        run = subprocess.run(
            ["say", "--file-format=WAVE", f"--data-format=LEI16@{SAY_RATE}", "-o", str(wav), "-f", str(source)],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )
    if run.returncode != 0:
        raise SynthError(f"say exited {run.returncode}: {run.stderr.strip()}")


class SayEngine:
    name, voice, rate = "say", SAY_VOICE, SAY_RATE

    def synth(self, text, wav):
        synth_say(text, wav)

    def failure(self, sid, message):
        return NarrationError(f"scene {sid}: {message}", 1)


class KokoroEngine:
    name, voice, rate = "kokoro", KOKORO_VOICE, KOKORO_RATE

    def __init__(self, models):
        for name in MODEL_FILES:
            if not (Path(models) / name).is_file():
                raise NarrationError(f"models missing: {name}", 3)
        import kokoro_onnx   # lazy: the say path needs neither package
        import soundfile
        self._soundfile = soundfile
        self._kokoro = kokoro_onnx.Kokoro(str(Path(models) / MODEL_FILES[0]), str(Path(models) / MODEL_FILES[1]))

    def synth(self, text, wav):
        try:
            samples, rate = self._kokoro.create(spoken(text), voice=KOKORO_VOICE, speed=float(SPEED), lang="en-us")
            self._soundfile.write(str(wav), samples, rate, subtype="PCM_16")
        except Exception as exc:   # any engine fault is one failed clip, reported with its scene
            raise SynthError(str(exc)) from exc

    def failure(self, sid, message):
        return NarrationError(f"kokoro clip failed: {sid}: {message}", 3)


def narrate(scenes, engine, audio_dir):
    """Make or reuse one WAV per scene; return { id: seconds } after the sample-rate check."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    seconds = {}
    for scene in scenes:
        sid, text = scene["id"], scene["narration"]
        wav = audio_dir / f"{sid}.{engine.name}.wav"
        sidecar = wav.with_suffix(".txt")
        reused = wav.is_file() and sidecar_matches(sidecar, engine, text)
        if not reused:
            sidecar.unlink(missing_ok=True)   # a half-made clip must never look current
            try:
                engine.synth(text, wav)
            except SynthError as exc:
                wav.unlink(missing_ok=True)
                raise engine.failure(sid, str(exc)) from exc
        rate = afinfo_rate(wav)
        if rate != engine.rate:
            raise NarrationError(f"scene {sid}: {wav} is {rate} Hz (expected {engine.rate})")
        if not reused:
            sidecar.write_bytes(sidecar_text(engine, text).encode("utf-8"))
        seconds[sid] = afinfo_seconds(wav)
        print(f"narration: {sid} {engine.name} {seconds[sid]:.3f} s ({'reused' if reused else 'synthesized'})")
    return seconds


def load_scenes(path):
    try:
        scenes = json.loads(Path(path).read_text(encoding="utf-8"))["scenes"]
        return [{"id": scene["id"], "narration": scene["narration"]} for scene in scenes]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"narration: FAIL script {path}: {exc}")
        sys.exit(2)


def check_narrations(scenes):
    for scene in scenes:
        if not isinstance(scene["narration"], str) or not scene["narration"].strip():
            raise NarrationError(f"scene {scene['id']}: narration is empty")


def check_tools(engine_name):
    for tool in (["say"] if engine_name == "say" else []) + ["afinfo"]:
        if shutil.which(tool) is None:
            raise NarrationError(f"{tool} not found")


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="narrate.py", add_help=False)
    parser.add_argument("--engine", required=True, choices=("say", "kokoro"))
    parser.add_argument("--models")
    parser.add_argument("--fallback")
    parser.add_argument("script")
    parser.add_argument("audio_dir")
    args = parser.parse_args(argv)
    if args.engine == "kokoro" and not args.models:
        parser.error("--engine kokoro needs --models <dir>")
    return args


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    scenes = load_scenes(args.script)
    try:
        check_narrations(scenes)
        check_tools(args.engine)
        engine = SayEngine() if args.engine == "say" else KokoroEngine(args.models)
        audio_dir = Path(args.audio_dir)
        seconds = narrate(scenes, engine, audio_dir)
    except NarrationError as exc:
        print(f"narration: FAIL {exc}")
        return exc.code
    report = {"engine": engine.name, "fallback": args.fallback, "scenes": seconds}
    (audio_dir / "durations.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
