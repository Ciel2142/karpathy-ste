# Explain: Russian artifacts and a voice per language — design

Date: 2026-10-04
Status: approved in conversation section by section; revised after a three-reviewer spec review
(code fidelity, TTS and guard, contract and tests); written spec pending user review
Base: `feat/explain-brainrot` at `0976e0f` (the brainrot waves scenebox, sentence-narration and
brainrot-timeline are merged there; brainrot-render is planned, not run). Line numbers below
are as of that commit; the plan re-locates them after the rebase (§8).

## 1. Purpose

The user reads `/explain` artifacts to learn about software: their own code and general
topics. They want them in Russian as well as in English. Today a sheet or a page can already
be written in Russian on request (`SKILL.md` convention 7), but three things are wrong or
missing:

- the STE profile tells the author to apply English-only vocabulary rules to Russian text;
- every template hardcodes `<html lang="en">`;
- the video rung stops on any non-English request, because narration is English only
  (Kokoro `af_heart` with `lang="en-us"`, `say` with the default voice).

This design makes Russian a first-class artifact language and picks the narration voice from
the artifact language.

Success means:

- `/explain <subject> --as video`, asked in Russian, gives a Russian video that passes
  `verify.sh` and `verify_sync.py`, with a transcript marked `lang="ru"`;
- every term in Russian narration is spoken as written in `pronounce` or fails the run before
  synthesis: no word, number or acronym is silently dropped or merged;
- English videos, sheets and pages behave as before: the same cached clips, the same Narrator
  rows, the same cue frames.

## 2. Scope

In scope:

- `lang` and `pronounce` keys in `script.json`, with shape checks in `build-timeline.mjs`.
- A Silero engine in `narrate.py`, chosen by `lang`, with `say -v Milena` as its fallback.
- The spoken-text pipeline and a pre-flight guard for Russian (`narrate.py --check`).
- Cue frames of a Russian explainer placed on the spoken text.
- `silero` accepted by `build-timeline.mjs`, `render.sh`, `narrate.sh` and
  `video-workspace.sh`; `render.sh` picks the engine from `lang`.
- `<html lang>` from the artifact language in the sheet, page and video transcript.
- `SKILL.md` convention 7, the router line, and the video rung: structural STE rules for
  non-English artifacts; the "English only" stop removed; a Russian timing budget; Silero
  setup notes.
- Silero model download in `video-workspace.sh`; a sha check before every model load.

Out of scope:

- Brainrot in Russian. Brainrot narrates at speed 1.2 and Silero has no numeric speed (its
  `apply_tts` takes no speed argument). A Russian `--as brainrot` request stops and offers a
  Russian explainer video (§5.3).
- Languages other than English and Russian.
- A Russian controlled-language profile or a Russian lint.
- Automatic transliteration. The script author writes the `pronounce` map.
- A higher-quality English engine. Kokoro `af_heart` stays.
- Russian labels in the video transcript (`Narrator`, `Not covered` and the other labels of
  `video.html` stay English on a `lang="ru"` page).

## 3. Interface

### 3.1 `script.json`

Two new optional top-level keys:

| Key | Value | Default |
|---|---|---|
| `lang` | `"en"` or `"ru"` | `"en"` when absent |
| `pronounce` | object: written term → spoken Russian form | absent |

Example: `"lang": "ru", "pronounce": {"ImportController": "импорт-контроллер", "JSON":
"джейсон", "Kafka": "к+афка", "404": "четыреста четыре", "СУБД": "эс-у-бэ-дэ", "т. е.": "то
есть"}`.

Keys may be Latin or Cyrillic and may hold spaces and punctuation. A value may mark stress
with `+` before a vowel, as Silero reads it (`к+афка`). The narration, props, cites and
transcript keep the written terms; only the audio and the cue frames (§4.8) use the spoken
form.

### 3.2 Validator rules (`build-timeline.mjs`)

- The top-level key whitelist (line 367: `format, title, subject, provenance, scenes`) gains
  `lang` and `pronounce`.
- `lang`, when present, is the string `"en"` or `"ru"`.
- `pronounce`, when present, needs `lang: "ru"`; it is an object whose keys are non-empty
  strings and whose values are non-empty strings.
- `lang: "ru"` with `format: "brainrot"` is an error: `lang ru is for the explainer format
  only`.
- `ENGINES` (line 54) gains `silero`; the usage text (lines 7 and 60) and the build-mode
  engine error (line 626) name all three engines. The clip path is `audio/<id>.silero.wav`.
- The character rules of the spoken text are not checked here; the guard (§4.3) owns them.

### 3.3 Engine selection

The first choice and the fallback of each language are in §4.1.

- `render.sh`: `--engine` becomes optional (`kokoro | silero | say`); the default is no
  longer `kokoro`. `stage_script` reads `lang` with its existing python3 read of
  `script.json` (next to `format`) and resolves the engine: the given `--engine`, else the
  first choice for `lang`. It passes the resolved engine explicitly to `video-workspace.sh`
  and `narrate.sh`. A narration failure before `durations.json` exists is labelled
  `narration (<resolved engine>): FAIL …`.
- `narrate.sh`: `--engine` accepts `kokoro | silero | say`, default the first choice for
  `lang`. Right after argument parsing it runs `python3 narrate.py --check` (§4.3), which also
  reads `lang`; this replaces the header's "only builtins run before the uv check"
  invariant. It then checks the model files of the chosen engine only.
- `--engine say` forces the fallback voice of the script's `lang`.
- `--engine kokoro` with a Russian script, or `--engine silero` with an English script, is a
  usage error, exit 2, naming the engine and the language. It is raised by `narrate.py
  --check` (so before any model check) and by `render.sh` when it resolves the engine.

## 4. Narration

### 4.1 Voice per language

| `lang` | First choice | Labelled fallback |
|---|---|---|
| `en` | Kokoro `af_heart`, 24 kHz (unchanged) | `say`, default voice, 22050 Hz (unchanged) |
| `ru` | Silero `v5_3_ru`, speaker `xenia`, 48 kHz | `say -v Milena`, 22050 Hz |

The speaker was chosen by ear in the voice probe (§9).

### 4.2 Spoken text for Russian

For a Russian script, the text an engine reads is made in this order:

1. Collapse every run of Unicode whitespace (as Python `str.split()` sees it: spaces,
   tabs, newlines, U+00A0, U+202F and the like) to one ASCII space, and strip both ends.
   Silero keeps only the ASCII space and joins words across any other whitespace without an
   error ("в базе" is read as "вбазе").
2. Remove backticks (today's `spoken()`).
3. Replace each `pronounce` key with its value. A key matches where the character before it is
   the start of the text or not a letter, digit or `_`, and the character after it is the end
   of the text or not a letter, digit or `_`. Matching is case-sensitive. Longer keys are tried
   first; the replacement is one left-to-right pass, and replaced text is not scanned again.

Both Russian engines (Silero and Milena) get the same spoken text, so a fallback says the same
words. English scripts are unchanged: step 2 only, as today.

### 4.3 Pre-flight guard (`narrate.py --check`)

`narrate.py --check [--engine <e>] [--speed <d.d>] <script.json>` uses the standard library
only. It reads the script, makes the spoken text of every scene, and checks it before any
model, uv or torch step. `render.sh` runs it in `stage_script` (next to `build-timeline
--check`, line 177), so a bad script fails before the workspace stage downloads anything;
`narrate.sh` runs it first on every call. It applies to every Russian run, whatever the engine,
including `--engine say`.

Script errors, all exit 2, each one line on stdout starting `narration: FAIL `:

- the script cannot be read, or `lang` or `format` is invalid (today's `load_script` errors);
- the engine does not fit `lang` (§3.3);
- `lang: "ru"` with a speed other than `1.0`: `lang ru narrates at speed 1.0 only`;
- for a Russian script, a scene whose spoken text breaks a character rule below.

Character rules for the spoken text of a Russian scene (after §4.2):

1. Allowed characters: Cyrillic letters (`А–Я`, `а–я`, `Ё`, `ё`), the ASCII space, the
   punctuation `. , ! ? : ; - – — … « » " ' ( ) „ “ ’`, and `+` directly before a Cyrillic
   vowel (`аеёиоуыэюя`, either case). Silero drops `« » " ' ( ) „ “ ’` harmlessly and reads
   the rest (§9).
2. No token (whitespace-delimited, with leading and trailing allowed punctuation stripped)
   holds two or more upper-case Cyrillic letters. Silero reads `СУБД` as one word and
   swallows `ОС`; the author spells an acronym out in `pronounce`.
3. No token is exactly one Cyrillic letter followed by `.` (`т.`, `е.`, `к.`, `д.`, `п.`).
   Silero reads `т. е.` letter by letter; the author maps the abbreviation.
4. At least one Cyrillic letter in the scene. Text of punctuation only makes Silero raise an
   empty `ValueError`.
5. At most 900 characters. Silero fails at about 1,476 characters ("probably it's too
   long"); 984 worked in the review probe. A narration within the 45-word limit is about 350.

All offending tokens go in one line: scenes in script order, tokens in text order, each token
once per scene, reported with the punctuation stripped as in rule 2. A token that mixes a
Cyrillic letter with an offending letter (a look-alike, such as a Latin `K` in `Kафка`) also
shows the code point of its first offending character. Rules 4 and 5 name the scene. Example:

```
narration: FAIL unspoken text: tools: "KafkaTemplate", "8080"; intro: "JSON", "Kафка" (U+004B), "СУБД" (add to pronounce)
```

### 4.4 Cache sidecar

The sidecar of a Russian clip has, after the speed line, a `lang=ru` line, then (Silero only)
a `model=v5_3_ru` line, then the spoken text (after §4.2) in place of the narration. So an edit
to `pronounce` re-synthesises the clips it changes, an edit that does not change the spoken
text (a backtick, a no-break space) reuses them, and a future model change re-synthesises
everything. The sidecar of an English clip is byte-for-byte as today, so existing caches stay
valid.

### 4.5 Silero engine

- `SileroEngine(models, speed)`: name `silero`, voice `xenia`, rate 48000.
- Before loading, it checks that `v5_3_ru.pt` exists (else `models missing: v5_3_ru.pt`) and
  that its size and sha256 match the pin of §6.1 (else `model sha mismatch: v5_3_ru.pt`).
  Both are `NarrationError` code 3, so `narrate.sh` falls back to Milena. The check runs
  before every load because loading the package runs code (its `extern_modules` include
  `builtins` and `os`); hashing 145 MB takes well under a second.
- It refuses any speed other than `1.0` with a `NarrationError` code 2. `narrate.py --check`
  makes this unreachable; the check stops a silent mismatch.
- It loads the model with `torch.package.PackageImporter(<path>).load_pickle("tts_models",
  "model")`, calls `apply_tts(text=..., speaker="xenia", sample_rate=48000)`, clips the float
  samples to [-1, 1], scales by 32767, casts to int16, and writes mono 16-bit PCM with the
  standard-library `wave` module. Without the clip a peak above 1.0 wraps to a loud click
  (peaks of 0.992 were measured).
- Any exception from one clip is a `SynthError`; its failure is `silero clip failed: <scene>:
  <message>`, code 3, the same shape as Kokoro's.
- `narrate.sh` runs it with `uv run --python 3.12 --with torch==2.14.1 --with numpy==2.5.3
  python3 -W ignore::SyntaxWarning narrate.py …`. Every package load prints a
  `SyntaxWarning` from Silero's own text cleaner on stderr; the flag keeps that line out of
  fallback causes. The first run downloads torch (127 MB wheel) into the uv cache.

### 4.6 Fallback and the `say` voice

- After `narrate.py --check` has passed, any non-zero exit of the first-choice engine's run
  falls back to `say`. The cause is the text after `narration: FAIL ` of the last such line
  on stdout when there is one, else `uv run failed: <last stderr line>` (else `exit <rc>`).
  This keeps uv's own exit 2 a fallback cause, as `test_narrate.py:373-378` requires, and
  applies to Kokoro too.
- The Silero causes: `models missing: v5_3_ru.pt`, `model sha mismatch: v5_3_ru.pt`, `uv not
  found`, `uv run failed: <last stderr line>`, `silero clip failed: <scene>: <message>`.
- `SayEngine` takes the voice from `lang`: the default voice for `en` (sidecar `voice=say-default`
  as today), `Milena` for `ru` (`-v Milena`, sidecar `voice=Milena`).
- Before a Russian `say` run, `narrate.py` checks that `say -v '?'` has a line whose first
  field is exactly `Milena` and which names `ru_RU`. If not: `narration: FAIL say voice
  Milena is not installed`, exit 1. The check is needed: `say -v <missing voice>` exits 0 and
  silently uses the default voice.

### 4.7 `durations.json` and the Narrator row

`durations.json` gains a `voice` key next to `engine`, for every run (English ones too). Its
values: `af_heart`, `say-default`, `xenia`, `Milena`. `render.sh` builds the Narrator row from
`engine` and `voice`:

| Run | Narrator row |
|---|---|
| Kokoro | `kokoro (af_heart)` (unchanged) |
| English `say` | `say`, or `say (fallback: <cause>)` (unchanged) |
| Silero | `silero (xenia)` |
| Russian `say` | `say (Milena)`, or `say (Milena, fallback: <cause>)` |

### 4.8 Cue frames on the spoken text

An explainer cue frame is placed by the cue's character offset in the narration
(`build-timeline.mjs:562`: `hits[0] / scene.narration.length × clipFrames`). A `pronounce`
expansion moves speech against the written text ("404" is 3 characters, «четыреста четыре» 16),
and `verify_sync.py` checks only where speech starts and ends.

For a Russian script, `build-timeline.mjs` computes the offset on the spoken text instead:
`spoken(narration[0:hit]).length / spoken(narration).length`, where `spoken` is a JS copy of
§4.2 steps 1–3. English scripts keep today's formula byte-for-byte, so their cue frames do not
change. The two implementations are held equal by a shared fixture (§7.2).

## 5. Artifacts and prose

### 5.1 `<html lang>`

- Sheet and page: the author sets `<html lang>` to the artifact language (`en` or `ru`) when
  filling the template. The rung files say so next to the other template edits.
- Video transcript: `video.html` line 2 gets a `{{lang}}` marker; `transcript.py` fills it from
  the script's `lang` (default `en`) and adds it to its marker dict.

### 5.2 `SKILL.md` convention 7

Replace the language rule with: write the artifact in English unless the user asks for another
language. For a non-English artifact, apply only the structural rules of the STE profile
(sentence length, paragraph length, active voice, one instruction in each sentence); the
English vocabulary and the substitution table do not apply. Put each English term and code
name in `<code>` (or backticks in a video script): `ste_lint.py` skips code, and its `WORD`
and `CONTRACTION` rules still fire on bare Latin words in Russian prose ("provide", "via",
"it's").

### 5.3 Router and video rung

- `SKILL.md:65` (router): replace "The video rung is English only." with: a video can be
  English or Russian; brainrot is English only. For a Russian `--as brainrot` request, print
  the rung line, say that brainrot is English only, stop, and offer a Russian explainer
  video.
- `rungs/brainrot.md` (created by brainrot-render) says the same; its "English only, like the
  video rung" becomes "English only".
- `rungs/video.md`:
  - remove the "English only" stop (lines 13–14);
  - the key table documents `lang` and `pronounce`: every Latin term, number, acronym and
    one-letter abbreviation the narration speaks needs a `pronounce` entry; prefer Russian
    words to code names, as for English; `+` before a vowel fixes stress;
  - line 38 ("Write the narration in STE"): for a Russian video, the structural rules of
    convention 7;
  - lines 42–45 (budget): Silero speaks about 2.3 to 2.9 words a second (2.3 in the first
    probe, 2.9 on longer text in the review) against about 3 for Kokoro. For a Russian video,
    aim at about 35 words in each scene and 250 words in total. These are targets; the
    validator limit stays 45 words a scene;
  - lines 136–146, 170 and 188–193 (Kokoro model sizes, the uv first run, Narrator rows,
    pins): add the Silero equivalents (145 MB model, 127 MB torch on the first run,
    `silero (xenia)`, `say (Milena)`, the sha pin).

## 6. Pipeline, checks and errors

### 6.1 Workspace (`video-workspace.sh`)

`fetch_model` takes the download URL as an argument (today it builds it from the fixed Kokoro
`model_base`, lines 53 and 92). `--engine silero` downloads
`https://models.silero.ai/models/tts/ru/v5_3_ru.pt` into `<ws>/models` as `.part`, checks its
sha256, then moves it into place, with the same cost and done lines as the Kokoro files:

- sha256 `f036d3da1584899e5e24bdf2d5bd3bcf896e2d62505de39a02caca76014d7a1c`
- size 145359640 bytes (`workspace: download v5_3_ru.pt (145 MB)`)

A sha mismatch deletes the `.part` file and fails the step. A file already in place is left
alone, as today; `narrate.py` checks the pin before every load (§4.5).

### 6.2 Stage lines

The existing lines keep their shape; `<engine>` can now be `silero`:
`narration (silero): ok`, `narration (say): ok (fallback: <cause>)`. A guard failure shows at
the `script` stage: `script: FAIL unspoken text: …`.

### 6.3 Exit codes of `narrate.sh`

- `narrate.py --check` exits 2: `narrate.sh` prints its output and exits 2, no fallback.
- The first-choice engine's run fails with any other code: fallback to `say` (§4.6).
- The `say` run fails: exit 1, as today.

### 6.4 Errors

| Fault | Result |
|---|---|
| unspoken text, acronym, abbreviation, no letter, over 900 characters (§4.3) | `narration: FAIL …`, exit 2; `script: FAIL …` under `render.sh` |
| `--engine` does not fit `lang` (§3.3) | usage error, exit 2 |
| `lang ru` with speed other than 1.0 | `narration: FAIL lang ru narrates at speed 1.0 only`, exit 2 |
| `pronounce` without `lang: "ru"`, `lang` not `en`/`ru`, `ru` with brainrot | validator error (`script` stage) |
| Silero model missing or sha mismatch, uv missing, uv run failed (including uv's own exit 2), one clip failed | `say -v Milena` fallback, cause on the Narrator row |
| Milena not installed | `narration: FAIL say voice Milena is not installed`, exit 1 |
| Download sha mismatch | `workspace: FAIL` (§6.1) |

## 7. Testing

TDD in the existing suites. Every assertion that closes a named fault is checked against the
broken state (the mutation in the test docstring, as the suites do today).

### 7.1 Narration (`test_narrate.py` and its brainrot-render split, stub engines)

- A stub Silero module that asserts the speaker `xenia`, the rate 48000 and that it receives
  the spoken text; a stub that returns samples above 1.0 gives int16 at ±32767, not wrapped.
- Spoken text: a no-break space and a tab become one ASCII space; longest key first;
  whole-token boundaries (`Kafka` does not match inside `KafkaTemplate`; a Cyrillic neighbour
  blocks a match: `JSONом`); one pass (a value is not re-scanned); case-sensitive; Cyrillic
  and multi-word keys (`т. е.`).
- Guard: each rule of §4.3 fails with its exact line (Latin, digit, symbol, `+` not before a
  vowel, `СУБД`, `т.`, punctuation only, 901 characters); allowed punctuation and `+` before a
  vowel pass; several scenes and tokens appear in order; the look-alike code point; the guard
  runs for `--engine say`; English scripts are not guarded.
- Sidecar: `lang=ru`, `model=v5_3_ru` (Silero only) and the spoken text; a `pronounce` edit
  re-synthesises; a backtick-only edit reuses; the English sidecar equals a literal string.
- Engine selection: the default per `lang`; `--engine say` gives Milena for `ru`; each
  mismatch is exit 2 before any model check.
- `narrate.sh`: each Silero fallback cause, including `model sha mismatch`; uv's own exit 2
  (stderr only) still falls back with `uv run failed: …`; an engine exit with a stdout
  `narration: FAIL` line uses that line as the cause; `--check` exit 2 passes through with no
  `FALLBACK` line, for Kokoro and Silero; the Milena-missing failure, with a `say -v '?'` stub
  that lists `Milena` only as a substring of another name.
- `lang ru` with `--speed 1.2` is exit 2; Silero's own speed refusal is code 2.
- `durations.json` has `voice` for each engine.

### 7.2 Validator and timeline (`test_video_timeline.py`, `test_video_timeline_brainrot.py`)

- `lang` accepts `en`, `ru` and absence; rejects any other value and a non-string.
- `pronounce` without `lang: "ru"`, a non-object, an empty key and an empty-string value are
  errors.
- `lang: "ru"` with `format: "brainrot"` is an error.
- Build mode accepts engine `silero` and reads `audio/<id>.silero.wav`.
- Cue frames: a shared fixture (`tests/fixtures/spoken-text.json`: narration, pronounce,
  expected spoken text) is read by a `narrate.py` test and by a timeline test. The timeline
  test builds a Russian script with expansions before its cues and asserts each cue frame
  equals the frame computed from the fixture's spoken text. An English script's cue frames
  equal today's values.

### 7.3 Render, transcript and workspace

- `render.sh` with no `--engine`: a Russian script passes `silero` to the workspace and
  narration stubs; an English one passes `kokoro`; `--engine kokoro` with a Russian script
  fails; the guard fails at the `script` stage before the workspace stub runs.
- The Narrator row for Silero, Russian `say` and Russian `say` with a fallback cause; the
  English rows unchanged (the `narrator_text` helper of `test_render.py:139-145` takes the
  voice).
- `transcript.py` writes `<html lang="ru">` for a Russian script and `lang="en"` otherwise.
- `video-workspace.sh --engine silero`: cost line, `.part` download from the Silero URL, sha
  check (a mismatch deletes the part and fails), done line; stubbed `curl` as in the existing
  workspace tests.

### 7.4 Live acceptance

One real Russian explainer video (for example `ImportController.java` of inavcalculator, as in
the English live run), rendered with no `--engine` flag:

- `render.sh` passes with no `narration: FALLBACK` line;
- `verify.sh` and `verify_sync.py` pass;
- the Narrator row reads `silero (xenia)` and the transcript has `<html lang="ru">`;
- the user watches it and accepts it.

## 8. Sequencing

Planning starts after brainrot wave `brainrot-render` closes (and `brainrot-live-run`, if the
wave map orders it first). This branch is then rebased onto the tip of `feat/explain-brainrot`
so that the plan reads the code that exists. The work owns `narrate.py`, `narrate.sh`,
`build-timeline.mjs`, `render.sh`, `video-workspace.sh`, `transcript.py`, `video.html`,
`SKILL.md`, `rungs/video.md` and `rungs/brainrot.md`, which overlap brainrot-render (its Task 6
reads `format` in `stage_script`, its Task 7 edits `video.html` and `transcript.py`, its Task 1
splits `test_narrate.py`). The work is expected to fit one plan of at most 10 tasks (floor
rule), with the transcript `lang` folded into the render task; planning confirms this or
returns to a wave map.

## 9. Evidence

### 9.1 Voice probe (2026-10-04)

Throwaway samples in `/tmp/ru-voices`, two sentences: plain Russian and Russian with
`ImportController`, `JSON`, `Kafka`, `KafkaTemplate`.

| Engine | plain | mixed |
|---|---|---|
| macOS Milena | 8.3 s | 7.1 s |
| Piper `denis` | 8.2 s | 6.5 s |
| Piper `irina` | 9.0 s | 7.2 s |
| Silero `eugene` | 7.3 s | 3.2 s (Latin dropped) |
| Silero `xenia` | 8.2 s | 3.7 s (Latin dropped); 6.1 s hand-transliterated |

«Код 404, порт 8080, версия 2.5.» took 1.7 s: the numbers were dropped. The user judged
Silero clearly the best on plain Russian.

### 9.2 Review probe (2026-10-04, `/tmp/ru-review`)

- Silero's cleaner lowercases, turns `—` into `–`, and keeps only `! + , - . : ; ? а–я ё – …`,
  the ASCII space and `^`; everything else is deleted.
- U+00A0, U+202F and tabs join the neighbouring words ("вбазе данных"; a no-break space also
  changed the clip length, 0.975 s against 1.062 s).
- `СУБД` 0.28 s against 0.49 s spelled out; `ОС` almost swallowed; `т. е.` read letter by
  letter.
- Same text, same int16 output across calls and processes (deterministic).
- 48 kHz mono Int16 per `afinfo`; lead silence 0.02–0.04 s, tail 0.24–0.34 s.
- Punctuation-only text raises an empty `ValueError`; about 1,476 characters fail, 984 work.
- The downloaded model matches the sha and size pin.

Licences: the Silero Russian models are CC BY-NC 4.0, which fits the user's personal,
non-commercial use. Piper `denis` and `dmitri` (CC0 data) stay the candidates if the use ever
becomes commercial.

## 10. Decisions log

| # | Decision | Why |
|---|---|---|
| R1 | No Russian STE profile; non-English artifacts apply only the structural rules | STE is English by definition; a Russian lint is a separate design |
| R2 | Silero `v5_3_ru`, speaker `xenia`, for Russian | Best Russian sound in the probe, with automatic stress and ё; deterministic output suits the cache and the sync checks |
| R3 | `say -v Milena` as the Russian fallback | No setup; mirrors the English Kokoro → `say` chain |
| R4 | A `pronounce` map written by the script author, plus a loud guard | Silero drops Latin, digits and odd whitespace silently and misreads acronyms; automatic transliteration mangles English; Cyrillic-only narration would break the transcript and cites |
| R5 | Russian is for the explainer format only | Silero has no numeric speed; brainrot needs 1.2 |
| R6 | English sidecars, Narrator rows and cue frames unchanged | Existing caches and tests stay valid |
| R7 | Plan after brainrot-render closes, on its branch | The same files; avoids a manual merge |
| R8 | Russian cue frames are placed on the spoken text, with a JS copy of the mapping held equal by a shared fixture | Cue accuracy is the point of cues; expansions would shift them by up to about half a second |
| R9 | The guard is a stdlib pre-flight (`narrate.py --check`) at the script stage and first in `narrate.sh` | Fails before 270 MB of downloads and before any fallback line |
| R10 | A script error is told apart by the pre-flight, not by the engine run's exit code | uv exits 2 for its own errors, which must stay a fallback cause |
| R11 | The model sha is checked before every load | Loading the package runs code; a pin checked only at download does not protect a replaced file |
