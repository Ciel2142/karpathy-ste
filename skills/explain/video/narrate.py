#!/usr/bin/env python3
"""Narration for the explain video rung: one WAV per scene, real lengths from afinfo.

Usage: narrate.py --check [--engine kokoro|silero|say] [--speed <d.d>] <script.json>
       narrate.py --engine kokoro|silero|say [--models <dir>] [--fallback "<cause>"] [--speed <d.d>]
                  <script.json> <audio-dir>

--check reads the script, makes no clip and loads no model (the standard library only), and
prints one line: the engine to use, the given --engine or else the first choice of the script's
"lang" (kokoro for en, the default; silero for ru). A synthesis run makes every check of
--check first, with the same lines and exit code. --models is needed by kokoro and silero.

--speed is one digit, a full stop, one digit, from 0.5 to 2.0 (default 1.0). Kokoro takes it
as its speed; say takes it as a rate of 175 wpm (say's default) times the speed, and gets no
-r at all at 1.0. A script with "lang": "ru" narrates at 1.0 only.

Writes <audio-dir>/<id>.<engine>.wav (16-bit PCM mono: Kokoro 24000 Hz, Silero 48000 Hz, say
22050 Hz), a sidecar <id>.<engine>.txt (engine, voice, speed, "mode=sentences", narration) and
durations.json: { "engine", "voice", "fallback", "scenes": { "<id>": seconds } }, where voice is
the engine's voice: af_heart (Kokoro), say-default or Milena (say), xenia (Silero). A script with
"lang": "ru" and a "pronounce" map { written term: spoken Russian } is read by the engine in
its spoken form, and its sidecar holds "lang=ru", the engine's model when it has one, and the
spoken form of each written token, one on each line, in place of the narration.

Every scene is narrated one sentence at a time: each sentence is synthesised alone, the clips
are joined with 0.15 s of silence between them, and <id>.<engine>.words.json gets the exact
start and end of every sentence and word:
{ "sentences": [{ "from", "to" }], "words": [{ "text", "from", "to" }] } (seconds from the
clip start). A script's "format" is "film", "brainrot" or "clip"; a script with no "format" is a
film. A clip from an earlier run that has no "mode=sentences" line in its sidecar is made again.

A script error is one or more lines "narration: FAIL <cause>" on stdout and exit 2, before a
clip is made. Each of the first three stops the check alone, in this order: the script cannot
be read, or its "format" is another value, or its "lang" or "pronounce" breaks a rule of
build-timeline.mjs (the first cause only); the engine does not fit "lang" (say fits both); a
Russian script at a speed other than 1.0. Then a Russian script is guarded, one line for each
rule it breaks: "unspoken text" (a spoken token holds a character other than a Cyrillic letter,
the punctuation of SPOKEN_PUNCTUATION or a "+" before a Cyrillic vowel, or two capital Cyrillic
letters), "abbreviation" (a written т. е., т.е., or напр. before a lower-case sentence), "no
letter" (a sentence with no Cyrillic letter) and "too long" (a spoken sentence of more than 900
characters). English is not guarded.

Exit 0 on success; 1 on a failed scene or a missing tool; 2 on a usage error or a script
error; 3 when Kokoro or Silero cannot run (models missing, a Silero model that fails its pin
check, or a clip failed), which narrate.sh turns into the say fallback. The say path and
--check are stdlib only; kokoro_onnx and soundfile are imported lazily by the Kokoro engine,
and torch by the Silero engine (which reads a pinned model file and checks its size and sha256
before it loads it).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import wave
from array import array
from pathlib import Path

DEFAULT_SPEED = "1.0"
SAY_DEFAULT_WPM = 175   # macOS say's rate when -r is absent
SPEED_SHAPE = re.compile(r"[0-9]\.[0-9]")
SPEED_RANGE = (0.5, 2.0)
KOKORO_VOICE = "af_heart"
KOKORO_RATE = 24000
SAY_VOICE = "say-default"
SAY_RATE = 22050
SAY_RUSSIAN_VOICE = "Milena"
SAY_RUSSIAN_LOCALE = "ru_RU"
SAY_VOICE_LINE = re.compile(r"^(.+?)\s+([a-z]{2}_[A-Z]{2})\s+#")   # a line of `say -v ?`: name, locale, # sample
MODEL_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
SILERO_FILE = "v5_3_ru.pt"
SILERO_SHA256 = "f036d3da1584899e5e24bdf2d5bd3bcf896e2d62505de39a02caca76014d7a1c"
SILERO_SIZE = 145359640
SILERO_VOICE = "xenia"
SILERO_RATE = 48000
PCM_PEAK = 32767
RATE_LINE = re.compile(r"Data format:.*?(\d+) Hz")
DURATION_LINE = re.compile(r"estimated duration:\s*([0-9.]+)")
SENTENCE_END = ".?!"
CLAUSE_END = ",;:"
END_WEIGHT = 2          # a word that ends a clause or a sentence is followed by a pause
JOIN_GAP_S = 0.15       # silence between two sentence clips
NARRATED_FORMATS = ("film", "brainrot", "clip")   # the script formats narrate.py accepts; a script with no format is a film
ENGINES = ("kokoro", "silero", "say")
FIRST_CHOICE = {"en": "kokoro", "ru": "silero"}   # the engine of each lang; check_script() is its only reader
# The guard of a Russian narration (spec 4.4).
SPOKEN_PUNCTUATION = ".,!?:;-–—…«»\"'()„“”‘’"   # rule 1 allows it; rules 1 and 2 strip it from a token's ends
STRESSED_VOWELS = "аеёиоуыэюяАЕЁИОУЫЭЮЯ"        # rule 1 allows "+" directly before one of them
CAPITALS = re.compile(r"[А-ЯЁ]")
ONE_LETTER_ABBREVIATION = re.compile(r"[А-Юа-юЁё]\.")      # т. е. д. г. с.; "я." is the word "я"
DOTTED_ABBREVIATION = re.compile(r"[А-Яа-яЁё]\.[А-Яа-яЁё]")   # т.е. т.д.
LOWER_CASE_START = re.compile(r"[а-яё]")
ABBREVIATION_LEADS = "«(\"„“‘'"     # rule 3 strips them from the start of a token and of the next sentence
ABBREVIATION_TAILS = "»)\"”’',;:"   # rule 3 strips them from the end of a token
MAX_SENTENCE = 900


class NarrationError(Exception):
    """A fault that ends the run: main() prints 'narration: FAIL <message>' and exits with code."""

    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


class SynthError(Exception):
    """One engine failed to make one clip; the engine's failure() words it."""


class ScriptError(Exception):
    """A script that must not be narrated: main() prints each of .lines as 'narration: FAIL <line>' and exits 2."""

    def __init__(self, lines):
        super().__init__("\n".join(lines))
        self.lines = lines


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


def parse_speed(value):
    """argparse type for --speed: one digit, a full stop, one digit, within SPEED_RANGE; returned unchanged."""
    if not SPEED_SHAPE.fullmatch(value) or not SPEED_RANGE[0] <= float(value) <= SPEED_RANGE[1]:
        raise argparse.ArgumentTypeError(
            f"speed must be <d.d> between {SPEED_RANGE[0]} and {SPEED_RANGE[1]}, got {value!r}")
    return value


def say_rate_args(speed):
    """say's -r option for a speed: none at the default 1.0, else the default wpm times the speed."""
    if speed == DEFAULT_SPEED:
        return []
    return ["-r", str(round(SAY_DEFAULT_WPM * float(speed)))]


class Speech:
    """The language of a script and how its written tokens are spoken.

    English: a token is spoken without its backticks, and a sentence keeps its whitespace.
    Russian: each token also has the keys of pronounce replaced, in one pass, and is made NFC;
    a sentence is its spoken tokens joined with one ASCII space (Silero joins words across any
    other whitespace). A key lies inside one token, so every written token has its own spoken form.
    """

    def __init__(self, lang="en", pronounce=None):
        self.lang = lang
        self.pronounce = dict(pronounce or {})
        self._values = {key: re.sub(r"\s+", " ", value) for key, value in self.pronounce.items()}
        self._keys = None   # one pass, longest key first (the sort keeps equal lengths in order), whole tokens only
        if lang == "ru" and self.pronounce:
            keys = sorted(self.pronounce, key=len, reverse=True)
            self._keys = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(key) for key in keys) + r")(?!\w)")

    def _spoken_token(self, token):
        token = token.replace("`", "")
        if self.lang != "ru":
            return token
        if self._keys:
            token = self._keys.sub(lambda found: self._values[found.group(0)], token)
        return unicodedata.normalize("NFC", token)

    def spoken_tokens(self, text):
        """The spoken form of each token of text.split()."""
        return [self._spoken_token(token) for token in text.split()]

    def spoken_sentence(self, sentence):
        """The text an engine reads for one sentence."""
        if self.lang != "ru":
            return sentence.replace("`", "")
        return " ".join(self.spoken_tokens(sentence))

    def token_lengths(self, sentence):
        """The weight of each written token of sentence, before END_WEIGHT: the length of its spoken form.

        In Russian a "+" (a stress mark of the spoken form) is not a letter and does not weigh.
        """
        spoken = self.spoken_tokens(sentence)
        if self.lang == "ru":
            spoken = [token.replace("+", "") for token in spoken]
        return [len(token) for token in spoken]


ENGLISH = Speech()


def sidecar_text(engine, text, speech=ENGLISH):
    """The sidecar: engine, voice, speed, mode=sentences, then the narration.

    A Russian sidecar has, after mode=sentences, the line lang=ru, the line model=<engine.model>
    when the engine has a model, and in place of the narration the spoken form of each written
    token, one on each line.
    """
    head = f"engine={engine.name}\nvoice={engine.voice}\nspeed={engine.speed}\nmode=sentences\n"
    if speech.lang != "ru":
        return head + text
    model = f"model={engine.model}\n" if engine.model else ""
    return f"{head}lang=ru\n{model}" + "\n".join(speech.spoken_tokens(text))


def sidecar_matches(sidecar, engine, text, speech=ENGLISH):
    """True when the sidecar exists and every field equals what this run would write."""
    if not sidecar.is_file():
        return False
    return sidecar.read_bytes().decode("utf-8") == sidecar_text(engine, text, speech)


def words_match(words_path, text):
    """True when words_path parses as a words.json whose word texts are exactly text.split()."""
    try:
        words = json.loads(words_path.read_text(encoding="utf-8"))["words"]
        return [word["text"] for word in words] == text.split()
    except (OSError, ValueError, KeyError, TypeError):   # missing, unreadable, not JSON, or the wrong shape
        return False


def split_sentences(text):
    """The sentences of text, stripped, in order, none empty.

    A sentence ends after ".", "?" or "!" when the next character is whitespace or the text
    ends, unless the terminator sits inside backticks (a code name such as `a. b`). With an odd
    number of backticks the pairing is unknowable, so backticks are ignored. Text after the
    last terminator is the last sentence. Every cut falls on whitespace, so the words of the
    sentences, in order, are text.split().
    """
    pairs_up = text.count("`") % 2 == 0
    sentences, start, in_code = [], 0, False
    for i, char in enumerate(text):
        if char == "`" and pairs_up:
            in_code = not in_code
        elif char in SENTENCE_END and not in_code and (i + 1 == len(text) or text[i + 1].isspace()):
            sentences.append(text[start:i + 1])
            start = i + 1
    sentences.append(text[start:])
    return [s.strip() for s in sentences if s.strip()]


def word_timings(sentences, spans, speech=ENGLISH):
    """[{"text", "from", "to"}] for every word of every sentence, in order.

    spans[k] is the (start, end) in seconds of sentences[k]; its words share that span in
    proportion to a weight: the length of the word's spoken form (speech.token_lengths: the word
    without backticks in English), plus END_WEIGHT when the written word ends in a comma,
    semicolon or colon or is the last word of the sentence. The word text stays the written
    token. The first word of a sentence starts at exactly the span's start and the last ends at
    exactly its end, and each word starts at the previous word's end, so the words tile the span
    with no gap.
    """
    if len(sentences) != len(spans):
        raise ValueError(f"{len(sentences)} sentences but {len(spans)} spans")
    words = []
    for sentence, (start, end) in zip(sentences, spans):
        tokens = sentence.split()
        last = len(tokens) - 1
        weights = [
            length + (END_WEIGHT if i == last or t[-1] in CLAUSE_END else 0)
            for i, (t, length) in enumerate(zip(tokens, speech.token_lengths(sentence)))
        ]
        total, before, edge = sum(weights), 0, start
        for i, (token, weight) in enumerate(zip(tokens, weights)):
            before += weight
            edge_end = end if i == last else start + (end - start) * before / total
            words.append({"text": token, "from": edge, "to": edge_end})
            edge = edge_end
    return words


def say_voice_args(lang):
    """say's -v option for a language: Milena for ru, none for en (say's default voice)."""
    return ["-v", SAY_RUSSIAN_VOICE] if lang == "ru" else []


def require_russian_say_voice():
    """Raise NarrationError unless `say -v ?` lists Milena for ru_RU.

    A line there is "<name>  <locale>  # <sample>" and a name can hold spaces, so the name is the
    text before the locale column. "Milena (Enhanced)" is another voice. The check is needed:
    `say -v <missing voice>` exits 0 and speaks with the default voice.
    """
    run = subprocess.run(["say", "-v", "?"], capture_output=True, encoding="utf-8", errors="replace",
                         stdin=subprocess.DEVNULL)
    for line in run.stdout.splitlines() if run.returncode == 0 else []:
        found = SAY_VOICE_LINE.match(line)
        if found and found.groups() == (SAY_RUSSIAN_VOICE, SAY_RUSSIAN_LOCALE):
            return
    raise NarrationError(f"say voice {SAY_RUSSIAN_VOICE} is not installed", 1)


def synth_say(text, wav, speed, lang="en"):
    # The text goes through a file (-f), never as an argument: a narration that starts
    # with "-" would otherwise be parsed by say as an option.
    with tempfile.TemporaryDirectory() as scratch:
        source = Path(scratch) / "narration.txt"
        source.write_text(text, encoding="utf-8")
        run = subprocess.run(
            ["say", "--file-format=WAVE", f"--data-format=LEI16@{SAY_RATE}", *say_rate_args(speed),
             *say_voice_args(lang), "-o", str(wav), "-f", str(source)],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )
    if run.returncode != 0:
        raise SynthError(f"say exited {run.returncode}: {run.stderr.strip()}")


class SayEngine:
    name, rate, model = "say", SAY_RATE, None

    def __init__(self, speed, lang="en"):
        self.speed = speed
        self.lang = lang
        self.voice = SAY_RUSSIAN_VOICE if lang == "ru" else SAY_VOICE
        if lang == "ru":
            require_russian_say_voice()

    def synth(self, text, wav):
        synth_say(text, wav, self.speed, self.lang)

    def failure(self, sid, message):
        return NarrationError(f"scene {sid}: {message}", 1)


class KokoroEngine:
    name, voice, rate, model = "kokoro", KOKORO_VOICE, KOKORO_RATE, None

    def __init__(self, models, speed):
        self.speed = speed
        for name in MODEL_FILES:
            if not (Path(models) / name).is_file():
                raise NarrationError(f"models missing: {name}", 3)
        import kokoro_onnx   # lazy: the say path needs neither package
        import soundfile
        self._soundfile = soundfile
        self._kokoro = kokoro_onnx.Kokoro(str(Path(models) / MODEL_FILES[0]), str(Path(models) / MODEL_FILES[1]))

    def synth(self, text, wav):
        try:
            samples, rate = self._kokoro.create(text, voice=KOKORO_VOICE, speed=float(self.speed), lang="en-us")
            self._soundfile.write(str(wav), samples, rate, subtype="PCM_16")
        except Exception as exc:   # any engine fault is one failed clip, reported with its scene
            raise SynthError(str(exc)) from exc

    def failure(self, sid, message):
        return NarrationError(f"kokoro clip failed: {sid}: {message}", 3)


def silero_model_tag():
    """The model's name and the first 12 hex digits of its pinned sha256, read at each call."""
    return f"{Path(SILERO_FILE).stem}@{SILERO_SHA256[:12]}"


def sha256_of(handle):
    """The hex sha256 of what remains of an open binary file."""
    digest = hashlib.sha256()
    for block in iter(lambda: handle.read(1 << 20), b""):
        digest.update(block)
    return digest.hexdigest()


class SileroEngine:
    name, voice, rate, speed = "silero", SILERO_VOICE, SILERO_RATE, DEFAULT_SPEED

    def __init__(self, models):
        path = Path(models) / SILERO_FILE
        if not path.is_file():
            raise NarrationError(f"models missing: {SILERO_FILE}", 3)
        self.model = silero_model_tag()
        # Loading the package runs code from the file, so the file is checked first, and the
        # package is loaded from the very handle that was hashed: the bytes loaded are the bytes checked.
        with open(path, "rb") as package:
            if os.fstat(package.fileno()).st_size != SILERO_SIZE or sha256_of(package) != SILERO_SHA256:
                raise NarrationError(f"model sha mismatch: {SILERO_FILE}", 3)
            package.seek(0)
            from torch.package import PackageImporter   # lazy: only a Silero run needs torch
            self._tts = PackageImporter(package).load_pickle("tts_models", "model")

    def synth(self, text, wav):
        try:
            audio = self._tts.apply_tts(text=text, speaker=SILERO_VOICE, sample_rate=SILERO_RATE).tolist()
            # Clipped first: a peak above 1.0 would wrap to a loud click as int16.
            pcm = array("h", (int(max(-1.0, min(1.0, sample)) * PCM_PEAK) for sample in audio))
            if sys.byteorder == "big":
                pcm.byteswap()   # WAV samples are little-endian
            with wave.open(str(wav), "wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(SILERO_RATE)
                out.writeframes(pcm.tobytes())
        except Exception as exc:   # any engine fault is one failed clip, reported with its scene
            raise SynthError(str(exc)) from exc

    def failure(self, sid, message):
        return NarrationError(f"silero clip failed: {sid}: {message}", 3)


def clip_format(clip):
    """(rate, width, channels) of a WAV, or a NarrationError naming the clip when it cannot be read."""
    try:
        with wave.open(str(clip), "rb") as src:
            return src.getframerate(), src.getsampwidth(), src.getnchannels()
    except (wave.Error, EOFError, OSError) as exc:
        raise NarrationError(f"clip {clip.name} cannot be read as WAV: {exc}") from exc


def join_clips(clips, out, gap_s):
    """Write the clips, one after another with gap_s of silence between, as one 16-bit mono WAV.

    Returns (rate, [(start_frame, end_frame), ...]): the exact frame span of each clip in the
    written file. The gap is round(gap_s * rate) zero frames, none before the first clip or after
    the last. A clip that is not 16-bit mono, or whose rate differs from the first clip's, raises
    NarrationError naming it, before anything is written.
    """
    if not clips:
        raise NarrationError("no clips to join")
    rate = clip_format(clips[0])[0]
    for clip in clips:
        got = clip_format(clip)
        if got != (rate, 2, 1):
            raise NarrationError(
                f"clip {clip.name} is {got[0]} Hz, {got[1] * 8}-bit, {got[2]} ch "
                f"(expected {rate} Hz, 16-bit, 1 ch)")
    gap = round(gap_s * rate)
    silence = b"\0\0" * gap
    spans, position = [], 0
    with wave.open(str(out), "wb") as joined:
        joined.setnchannels(1)
        joined.setsampwidth(2)
        joined.setframerate(rate)
        for index, clip in enumerate(clips):
            if index:
                joined.writeframes(silence)
                position += gap
            with wave.open(str(clip), "rb") as src:
                size = src.getsampwidth() * src.getnchannels()
                data = src.readframes(src.getnframes())
            # The span comes from the frames actually read, not the header's count, and a partial
            # trailing frame is dropped, so a truncated clip keeps every later span exact.
            frames = len(data) // size
            joined.writeframes(data[:frames * size])
            spans.append((position, position + frames))
            position += frames
    return rate, spans


def synth_sentences(engine, text, wav, speech=ENGLISH):
    """Synthesise text one sentence at a time, join the clips into wav, and return the words.json payload.

    Each sentence goes through engine.synth() as its spoken sentence (speech.spoken_sentence)
    into a scratch WAV. Sentence and word times are seconds from the start of wav, computed from
    the exact join frames and rounded to 6 places (a sentence's start and its first word's start
    come from the same float, so they stay equal).
    """
    sentences = split_sentences(text)
    with tempfile.TemporaryDirectory() as scratch:
        clips = []
        for index, sentence in enumerate(sentences):
            clip = Path(scratch) / f"sentence-{index}.wav"
            engine.synth(speech.spoken_sentence(sentence), clip)
            clips.append(clip)
        rate, frames = join_clips(clips, wav, JOIN_GAP_S)
    spans = [(start / rate, end / rate) for start, end in frames]
    return {
        "sentences": [{"from": round(a, 6), "to": round(b, 6)} for a, b in spans],
        "words": [
            {"text": w["text"], "from": round(w["from"], 6), "to": round(w["to"], 6)}
            for w in word_timings(sentences, spans, speech)
        ],
    }


def narrate(scenes, engine, audio_dir, speech=ENGLISH):
    """Make or reuse one WAV per scene; return { id: seconds } after the sample-rate check.

    Every scene is narrated one sentence at a time, with a words.json next to the WAV. A clip is
    reused when its WAV exists, its sidecar matches (a sidecar of an earlier run, with no mode
    line, does not), and its words.json exists, parses, and holds exactly the written words of the
    narration, because sentence spans cannot be recovered from a joined WAV (a clip that fails
    this is re-made whole, never patched). Before a clip is re-made its sidecar and words.json
    are removed; the files are written WAV, words.json, then the sidecar last (after the rate
    check), and a failed sentence removes the WAV and words.json again, so a half-made clip
    never looks current and captions never read old timings.
    """
    audio_dir.mkdir(parents=True, exist_ok=True)
    seconds = {}
    for scene in scenes:
        sid, text = scene["id"], scene["narration"]
        wav = audio_dir / f"{sid}.{engine.name}.wav"
        sidecar, words_path = wav.with_suffix(".txt"), wav.with_suffix(".words.json")
        reused = wav.is_file() and sidecar_matches(sidecar, engine, text, speech) and words_match(words_path, text)
        if not reused:
            sidecar.unlink(missing_ok=True)       # a half-made clip must never look current
            words_path.unlink(missing_ok=True)    # nor pair a new WAV with old timings
            try:
                words = synth_sentences(engine, text, wav, speech)
                words_path.write_text(json.dumps(words, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            except SynthError as exc:
                wav.unlink(missing_ok=True)
                words_path.unlink(missing_ok=True)
                raise engine.failure(sid, str(exc)) from exc
        rate = afinfo_rate(wav)
        if rate != engine.rate:
            raise NarrationError(f"scene {sid}: {wav} is {rate} Hz (expected {engine.rate})")
        if not reused:
            sidecar.write_bytes(sidecar_text(engine, text, speech).encode("utf-8"))
        seconds[sid] = afinfo_seconds(wav)
        print(f"narration: {sid} {engine.name} {seconds[sid]:.3f} s ({'reused' if reused else 'synthesized'})")
    return seconds


def is_cyrillic(char):
    """True for a letter of А–Я, а–я, Ё or ё."""
    return "А" <= char <= "я" or char in "Ёё"


def speakable(token, i):
    """Rule 1 for token[i]: a Cyrillic letter, the allowed punctuation, or "+" directly before a Cyrillic vowel."""
    if token[i] == "+":
        return i + 1 < len(token) and token[i + 1] in STRESSED_VOWELS
    return is_cyrillic(token[i]) or token[i] in SPOKEN_PUNCTUATION


def code_point(token, first_bad):
    """The ' (U+XXXX)' shown after a token of rule 1, or "".

    It is the code point of the first offending character when that is not a letter or a digit
    ("#", a misplaced "+", U+200B), else of the first other letter of a token that mixes a
    Cyrillic letter with another letter (a look-alike, such as a Latin K in Kафка). A Latin
    word or a number shows none.
    """
    if not first_bad.isalnum():
        return f" (U+{ord(first_bad):04X})"
    others = [char for char in token if char.isalpha() and not is_cyrillic(char)]
    if others and any(is_cyrillic(char) for char in token):
        return f" (U+{ord(others[0]):04X})"
    return ""


def unspoken_entry(sid, sentences, speech):
    """Rules 1 and 2: '<sid>: "<t>", ...' for the spoken tokens of the scene a voice cannot read, or "".

    A token is a word of the spoken sentence with the allowed punctuation stripped from its
    ends. It breaks rule 1 when a character is not speakable, and rule 2 when it holds two or
    more capital Cyrillic letters (СУБД, ОС). Each token shows once, in text order.
    """
    shown = []
    for sentence in sentences:
        for word in speech.spoken_sentence(sentence).split():
            token = word.strip(SPOKEN_PUNCTUATION)
            bad = [char for i, char in enumerate(token) if not speakable(token, i)]
            if bad:
                entry = f'"{token}"' + code_point(token, bad[0])
            elif len(CAPITALS.findall(token)) >= 2:
                entry = f'"{token}"'
            else:
                continue
            if entry not in shown:
                shown.append(entry)
    return f"{sid}: " + ", ".join(shown) if shown else ""


def abbreviation_entry(sid, sentences, speech):
    """Rule 3: '<sid>: "<t>", ...' for the written tokens of the scene that are abbreviations, or "".

    It reads the written sentences without backticks (a pronounce value must not hide the cut).
    A token, with ABBREVIATION_LEADS and ABBREVIATION_TAILS stripped from its ends, is an
    abbreviation when it is one Cyrillic letter but я then "."; or holds a "." between two
    Cyrillic letters; or ends a sentence that is followed by one that starts, after its
    ABBREVIATION_LEADS, with a lower-case Cyrillic letter (напр. in «напр. так»). Each token
    shows once, stripped, in text order.
    """
    written = [sentence.replace("`", "") for sentence in sentences]
    shown = []
    for k, sentence in enumerate(written):
        tokens = sentence.split()
        following = written[k + 1].lstrip(ABBREVIATION_LEADS) if k + 1 < len(written) else ""
        cut_inside = LOWER_CASE_START.match(following) is not None
        for i, token in enumerate(tokens):
            bare = token.lstrip(ABBREVIATION_LEADS).rstrip(ABBREVIATION_TAILS)
            if (ONE_LETTER_ABBREVIATION.fullmatch(bare) or DOTTED_ABBREVIATION.search(bare)
                    or (cut_inside and i == len(tokens) - 1)) and f'"{bare}"' not in shown:
                shown.append(f'"{bare}"')
    return f"{sid}: " + ", ".join(shown) if shown else ""


def no_letter_entry(sid, sentences, speech):
    """Rule 4: '<sid> sentence <k>, ...' for the spoken sentences whose only Cyrillic letters, if any, follow a "+", or ""."""
    def has_letter(spoken):
        return any(is_cyrillic(char) and (i == 0 or spoken[i - 1] != "+") for i, char in enumerate(spoken))
    numbers = [str(k) for k, sentence in enumerate(sentences, 1) if not has_letter(speech.spoken_sentence(sentence))]
    return f"{sid} sentence " + ", ".join(numbers) if numbers else ""


def too_long_entry(sid, sentences, speech):
    """Rule 5: '<sid> sentence <k> (<n> characters), ...' for the spoken sentences over MAX_SENTENCE, or ""."""
    lengths = [(k, len(speech.spoken_sentence(sentence))) for k, sentence in enumerate(sentences, 1)]
    long = [f"{k} ({n} characters)" for k, n in lengths if n > MAX_SENTENCE]
    return f"{sid} sentence " + ", ".join(long) if long else ""


GUARD_RULES = (   # (line head, the entry of one scene, line tail), in the order the lines print
    ("unspoken text: ", unspoken_entry, " (add to pronounce)"),
    ("abbreviation: ", abbreviation_entry, " (write the words out, as «то есть»)"),
    ("no letter: ", no_letter_entry, ""),
    ("too long: ", too_long_entry, f" (max {MAX_SENTENCE})"),
)


def guard_lines(scenes, speech):
    """The guard's lines for the scenes of a Russian script (spec 4.4), in rule order; [] when it passes.

    The sentences of a scene are those of split_sentences on its written narration. A line
    lists the scenes that break its rule, in script order, separated by "; ".
    """
    narrations = [(scene["id"], split_sentences(scene["narration"])) for scene in scenes]
    lines = []
    for head, entry, tail in GUARD_RULES:
        listed = [entry(sid, sentences, speech) for sid, sentences in narrations]
        listed = [scene_entry for scene_entry in listed if scene_entry]
        if listed:
            lines.append(head + "; ".join(listed) + tail)
    return lines


def lang_causes(script):
    """The causes of the lang and pronounce rules of build-timeline.mjs (checkLang, spec 3.2), in its order."""
    lang = script.get("lang")
    if "lang" in script and lang not in ("en", "ru"):
        yield "lang must be en or ru"
    if lang == "ru" and script.get("format", "film") == "brainrot":
        yield "lang ru is for the film and clip formats only"
    if "pronounce" not in script:
        return
    if lang != "ru":
        yield "pronounce needs lang ru"
    if not isinstance(script["pronounce"], dict):
        yield "pronounce must be an object"
        return
    for key, value in script["pronounce"].items():
        quoted = json.dumps(key, ensure_ascii=False)
        if key == "":   # and only that line: "" in ".?!" is True
            yield f"pronounce key {quoted} is empty"
        else:
            if any(char.isspace() for char in key):
                yield f"pronounce key {quoted} holds whitespace"
            if key[-1] in ".?!":
                yield f"pronounce key {quoted} ends with {json.dumps(key[-1])}"
        if not isinstance(value, str) or all(char.isspace() for char in value):
            yield f"pronounce value of {quoted} must be a string with a non-space character"


def load_script(path):
    """(scenes, speech) of a script: scenes are [{"id", "narration"}], speech is the Speech of its
    "lang" ("en" when it names none) and "pronounce"; the format is "film" when the script names none.

    A script that cannot be read, a format that is not in NARRATED_FORMATS (any type, null
    included), or a lang or pronounce that breaks a rule of the validator raises ScriptError with
    the one line 'script <path>: <cause>' (the first cause only), before any clip is made.
    """
    try:
        script = json.loads(Path(path).read_text(encoding="utf-8"))
        scenes = [{"id": scene["id"], "narration": scene["narration"]} for scene in script["scenes"]]
        if script.get("format", "film") not in NARRATED_FORMATS:
            raise ValueError("format must be film, brainrot or clip")
        cause = next(lang_causes(script), None)
        if cause is not None:
            raise ValueError(cause)
        return scenes, Speech(script.get("lang", "en"), script.get("pronounce"))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ScriptError([f"script {path}: {exc}"]) from exc


def check_script(path, engine, speed):
    """(scenes, speech, engine name) of a script that may be narrated by engine at speed, or ScriptError.

    In order, each stopping the check alone: load_script; the engine must fit lang (say fits
    both, else it must be FIRST_CHOICE[lang]; an engine of None becomes FIRST_CHOICE[lang]);
    lang ru at a speed other than 1.0. Then a Russian script raises the lines of guard_lines, if any. Any
    other exception is the one line 'script <path>: <message>', never a traceback.
    """
    try:
        scenes, speech = load_script(path)
        engine = engine or FIRST_CHOICE[speech.lang]
        if engine not in ("say", FIRST_CHOICE[speech.lang]):
            raise ScriptError([f"engine {engine} cannot narrate lang {speech.lang}"])
        if speech.lang == "ru" and speed != DEFAULT_SPEED:
            raise ScriptError(["lang ru narrates at speed 1.0 only"])
        lines = guard_lines(scenes, speech) if speech.lang == "ru" else []
        if lines:
            raise ScriptError(lines)
        return scenes, speech, engine
    except ScriptError:
        raise
    except Exception as exc:   # an unexpected fault while checking is a script error, never a traceback
        raise ScriptError([f"script {path}: {exc}"]) from exc


def check_narrations(scenes):
    for scene in scenes:
        if not isinstance(scene["narration"], str) or not scene["narration"].strip():
            raise NarrationError(f"scene {scene['id']}: narration is empty")


def check_tools(engine_name):
    for tool in (["say"] if engine_name == "say" else []) + ["afinfo"]:
        if shutil.which(tool) is None:
            raise NarrationError(f"{tool} not found")


USAGE = """narrate.py --check [--engine kokoro|silero|say] [--speed <d.d>] <script.json>
       narrate.py --engine kokoro|silero|say [--models <dir>] [--fallback "<cause>"] [--speed <d.d>]
                  <script.json> <audio-dir>"""


def parse_args(argv):
    """The two command lines of USAGE; an argparse error (usage on stderr, exit 2) otherwise.

    --check takes the script alone: no --models, --fallback or audio dir. A synthesis run needs
    --engine and the audio dir, and --models for kokoro and silero.
    """
    parser = argparse.ArgumentParser(prog="narrate.py", usage=USAGE, add_help=False)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--engine", choices=ENGINES)
    parser.add_argument("--models")
    parser.add_argument("--fallback")
    parser.add_argument("--speed", type=parse_speed, default=DEFAULT_SPEED)
    parser.add_argument("script")
    parser.add_argument("audio_dir", nargs="?")
    args = parser.parse_args(argv)
    if args.check:
        given = (("--models", args.models), ("--fallback", args.fallback), ("<audio-dir>", args.audio_dir))
        extra = [name for name, value in given if value is not None]
        if extra:
            parser.error(f"--check takes no {', '.join(extra)}")
        return args
    if args.engine is None or args.audio_dir is None:
        parser.error("a synthesis run needs --engine and <audio-dir>")
    if args.engine in ("kokoro", "silero") and not args.models:
        parser.error(f"--engine {args.engine} needs --models <dir>")
    return args


def make_engine(name, args, speech):
    """The engine of a synthesis run. Each checks what it needs: its model files, or Milena for a Russian say."""
    if name == "kokoro":
        return KokoroEngine(args.models, args.speed)
    if name == "silero":
        return SileroEngine(args.models)
    return SayEngine(args.speed, speech.lang)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        scenes, speech, engine_name = check_script(args.script, args.engine, args.speed)
    except ScriptError as exc:
        for line in exc.lines:
            print(f"narration: FAIL {line}")
        return 2
    if args.check:
        print(engine_name)
        return 0
    try:
        check_narrations(scenes)
        check_tools(engine_name)
        engine = make_engine(engine_name, args, speech)
        audio_dir = Path(args.audio_dir)
        seconds = narrate(scenes, engine, audio_dir, speech)
    except NarrationError as exc:
        print(f"narration: FAIL {exc}")
        return exc.code
    report = {"engine": engine.name, "voice": engine.voice, "fallback": args.fallback, "scenes": seconds}
    (audio_dir / "durations.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
