# Explain: Russian artifacts and a voice per language — design

Date: 2026-10-04
Status: approved in conversation section by section; written spec pending user review
Base: `feat/explain-brainrot` at `0976e0f` (the brainrot waves scenebox, sentence-narration and
brainrot-timeline are merged there; brainrot-render is planned, not run).

## 1. Purpose

The user reads `/explain` artifacts to learn about software: their own code and general
topics. They want them in Russian as well as in English. Today a sheet or a page can already
be written in Russian on request (`SKILL.md` convention 7), but three things are wrong or
missing:

- the STE profile tells the author to apply English-only vocabulary rules to Russian text,
  and the lint gate looks stricter than it is (only the length rules can fire on Russian);
- every template hardcodes `<html lang="en">`;
- the video rung stops on any non-English request, because narration is English only
  (Kokoro `af_heart` with `lang="en-us"`, `say` with the default voice).

This design makes Russian a first-class artifact language and picks the narration voice from
the artifact language.

Success means:

- `/explain <subject> --as video`, asked in Russian, gives a Russian video that passes
  `verify.sh` and `verify_sync.py`, with a transcript marked `lang="ru"`;
- English technical terms in Russian narration are spoken (never silently dropped);
- English videos, sheets and pages behave exactly as before, with the same cached clips.

## 2. Scope

In scope:

- `lang` and `pronounce` keys in `script.json`, with shape checks in `build-timeline.mjs`.
- A Silero engine in `narrate.py`, chosen by `lang`, with `say -v Milena` as its fallback.
- The spoken-text mapping and the unspoken-text guard for Russian.
- `<html lang>` from the artifact language in the sheet, page and video transcript.
- `SKILL.md` convention 7 and the video rung: structural STE rules for non-English artifacts;
  the "English only" stop removed; a Russian timing budget.
- Silero model download in `video-workspace.sh`.

Out of scope:

- Brainrot in Russian. Brainrot narrates at speed 1.2 and Silero has no numeric speed (its
  `apply_tts` takes no speed argument; SSML has only coarse rate levels). Brainrot stays
  English only, as its spec says (§3.1 of the brainrot design).
- Languages other than English and Russian.
- A Russian controlled-language profile or a Russian lint (stacked verbal nouns,
  bureaucratic style). Only the language-neutral length rules of `ste_lint.py` apply.
- Automatic transliteration. The script author writes the `pronounce` map.
- A higher-quality English engine. Kokoro `af_heart` stays.

## 3. Interface

### 3.1 `script.json`

Two new optional top-level keys:

| Key | Value | Default |
|---|---|---|
| `lang` | `"en"` or `"ru"` | `"en"` when absent |
| `pronounce` | object: written term → spoken Russian form | absent |

Example: `"lang": "ru", "pronounce": {"ImportController": "импорт-контроллер", "JSON":
"джейсон", "Kafka": "кафка", "404": "четыреста четыре"}`.

The narration, props, cites and transcript keep the written terms. Only the audio uses the
spoken form.

### 3.2 Validator rules (`build-timeline.mjs`)

- `lang`, when present, is the string `"en"` or `"ru"`.
- `pronounce`, when present, needs `lang: "ru"`; it is an object whose keys are non-empty
  strings and whose values are non-empty strings.
- `lang: "ru"` with `format: "brainrot"` is an error: `lang ru is for the explainer format
  only`.
- The character set of the spoken text is not checked here. The guard (§4.3) checks the
  result of the mapping, which covers the values.

### 3.3 Engine selection (`narrate.sh`, `narrate.py`, `render.sh`)

`--engine` accepts `kokoro`, `silero` or `say`. When `--engine` is absent, the engine is the
first choice for the script's `lang` (§4.1). `--engine say` forces the fallback voice of the
script's `lang`. `--engine kokoro` with a Russian script, or `--engine silero` with an English
script, is a usage error (exit 2) naming the engine and the language.

## 4. Narration

### 4.1 Voice per language

| `lang` | First choice | Labelled fallback |
|---|---|---|
| `en` | Kokoro `af_heart`, 24 kHz (unchanged) | `say`, default voice, 22050 Hz (unchanged) |
| `ru` | Silero `v5_3_ru`, speaker `xenia`, 48 kHz | `say -v Milena`, 22050 Hz |

The speaker was chosen by ear in the voice probe (§9): Silero sounds clearly better than
Piper and Milena on plain Russian.

### 4.2 Spoken text for Russian

For a Russian script, the text an engine reads is made in this order:

1. Remove backticks (today's `spoken()`).
2. Replace each `pronounce` key with its value. A key matches where the character before it is
   the start of the text or not a letter, digit or `_`, and the character after it is the end
   of the text or not a letter, digit or `_`. Matching is case-sensitive. Longer keys are tried
   first; the replacement is one left-to-right pass, and replaced text is not scanned again.

Both Russian engines (Silero and Milena) get the same mapped text, so a fallback says the same
words. English scripts are unchanged: step 1 only.

### 4.3 Unspoken-text guard

Silero drops every character outside its symbol set without an error: Latin words and digits
vanish from the audio (probe, §9). So, for a Russian script, after §4.2, every scene's spoken
text may hold only Cyrillic letters (`А–Я`, `а–я`, `Ё`, `ё`), whitespace and the punctuation
`. , ! ? : ; - – — « » " ' ( ) …`.

Any other character fails the run before any synthesis, with one line that names every scene
and every offending token (the whitespace-delimited token that holds the character), scenes in
script order, tokens in text order, each token once per scene:

```
narration: FAIL unspoken text: tools: "KafkaTemplate", "8080"; intro: "JSON" (add to pronounce)
```

This is a script error, exit 2. It is not a fallback cause: `narrate.sh` passes exit 2 from
`narrate.py` through without trying `say` (§6.3).

### 4.4 Cache sidecar

The sidecar of a Russian clip adds a `lang=ru` line after the speed line and stores the spoken
text (after §4.2) in place of the narration. So an edit to `pronounce` re-synthesises the
clips it changes, and an edit that does not change the spoken text (a backtick) reuses them.
The sidecar of an English clip is byte-for-byte as today, so existing caches stay valid.

### 4.5 Silero engine

- `SileroEngine(models, speed)`: name `silero`, voice `xenia`, rate 48000.
- It raises `NarrationError` with code 3 and `models missing: v5_3_ru.pt` when the model file
  is absent.
- It refuses any speed other than `1.0` with a `NarrationError` naming the speed. The validator
  (§3.2) makes this unreachable through `render.sh`; the check stops a silent mismatch.
- It loads the model with `torch.package.PackageImporter(<path>).load_pickle("tts_models",
  "model")`, calls `apply_tts(text=..., speaker="xenia", sample_rate=48000)`, and writes 16-bit
  PCM mono with the standard-library `wave` module.
- Any exception from one clip is a `SynthError`; its failure is `silero clip failed: <scene>:
  <message>`, code 3, the same shape as Kokoro's.
- `narrate.sh` runs it with `uv run --python 3.12 --with torch==2.14.1 --with numpy==2.5.3`.
  The first run downloads torch (127 MB wheel) into the uv cache, as Kokoro's first run does
  for its packages.

### 4.6 Fallback and the `say` voice

- The Silero fallback causes mirror Kokoro's: `models missing: v5_3_ru.pt`, `uv not found`,
  `uv run failed: <last stderr line>`, `silero clip failed: <scene>: <message>`.
- `SayEngine` takes the voice from `lang`: the default voice for `en` (sidecar `voice=say-default`
  as today), `Milena` for `ru` (passed as `-v Milena`, sidecar `voice=Milena`).
- Before a Russian `say` run, `narrate.py` checks that `say -v '?'` lists `Milena`; if not, it
  fails with `narration: FAIL say voice Milena is not installed`, exit 1.

### 4.7 `durations.json` and the Narrator row

`durations.json` gains a `voice` key next to `engine`. `render.sh` builds the Narrator row from
both:

| Run | Narrator row |
|---|---|
| Kokoro | `kokoro (af_heart)` (unchanged) |
| English `say` | `say`, or `say (fallback: <cause>)` (unchanged) |
| Silero | `silero (xenia)` |
| Russian `say` | `say (Milena)`, or `say (Milena, fallback: <cause>)` |

## 5. Artifacts and prose

### 5.1 `<html lang>`

- Sheet and page: the author sets `<html lang>` to the artifact language when filling the
  template (`en` or `ru`). The rung files say so next to the other template edits.
- Video transcript: `transcript.py` writes `<html lang>` from the script's `lang` (default
  `en`).

### 5.2 `SKILL.md` convention 7

Replace the language rule with: write the artifact in English unless the user asks for
another language. For a non-English artifact, apply only the structural rules of the STE
profile (sentence length, paragraph length, active voice, one instruction in each sentence);
the English vocabulary and the substitution table do not apply. `ste_lint.py` then checks only
the length rules; that is expected, not a gap.

### 5.3 Video rung (`rungs/video.md`)

- Remove the "English only" stop. Say that a video can be English or Russian, and that
  brainrot is English only.
- Document `lang` and `pronounce` in the key table: every Latin term and every number that the
  narration speaks needs a `pronounce` entry; prefer Russian words to code names in the
  narration, as for English.
- Timing budget: Silero speaks about 2.3 words a second (19 words in 8.2 s in the probe),
  against about 3 for Kokoro. For a Russian video: about 35 words in each scene and about 250
  words in total, so that 8 scenes stay under the 150 s limit.

## 6. Pipeline, checks and errors

### 6.1 Workspace (`video-workspace.sh`)

`--engine silero` downloads
`https://models.silero.ai/models/tts/ru/v5_3_ru.pt` (145 MB) into `<ws>/models` as `.part`,
checks its sha256, then moves it into place, with the same cost and done lines as the Kokoro
files:

- sha256 `f036d3da1584899e5e24bdf2d5bd3bcf896e2d62505de39a02caca76014d7a1c`
- size 145359640 bytes

The pin matters more than for Kokoro: a `.pt` package is a pickle and can run code when it is
loaded. A sha mismatch deletes the `.part` file and fails the step.

`render.sh` passes the engine for the script's `lang` to `video-workspace.sh`.

### 6.2 Stage lines

The existing lines keep their shape; `<engine>` can now be `silero`:
`narration (silero): ok`, `narration (say): ok (fallback: <cause>)`.

### 6.3 Exit codes of `narrate.sh`

Unchanged, plus one rule: when the first-choice engine's `narrate.py` exits 2 (a script error,
including the guard of §4.3), `narrate.sh` prints its output and exits 2, without the `say`
fallback. This applies to Kokoro too: a script error is never a fallback cause.

### 6.4 Errors

| Fault | Result |
|---|---|
| unspoken text after mapping (§4.3) | `narration: FAIL unspoken text: …`, exit 2 |
| `--engine` does not fit `lang` (§3.3) | usage error, exit 2 |
| `pronounce` without `lang: "ru"`, `lang` not `en`/`ru`, `ru` with brainrot | validator error (`timeline` stage) |
| Silero model missing, uv missing, uv run failed, one clip failed | `say -v Milena` fallback, cause on the Narrator row |
| Milena not installed | `narration: FAIL say voice Milena is not installed`, exit 1 |
| Silero model sha mismatch | `workspace: FAIL` (§6.1) |

## 7. Testing

TDD in the existing suites. Every assertion that closes a named fault is checked against the
broken state (the mutation noted in the test docstring, as the suites do today).

### 7.1 Narration (`test_narrate.py`, stub engines)

- A stub Silero module that asserts the speaker `xenia`, the rate 48000 and that it receives
  the mapped Cyrillic text.
- Mapping: longest key first; whole-token boundaries (`Kafka` does not match inside
  `KafkaTemplate`); one pass (a value is not re-scanned); case-sensitive.
- Guard: a Latin token, a digit token and a symbol token each fail with the exact line;
  several scenes and tokens appear in script and text order; English scripts are not guarded.
- Sidecar: `lang=ru` and the spoken text; a `pronounce` edit re-synthesises; a backtick-only
  edit reuses; the English sidecar is byte-for-byte unchanged.
- Engine selection: the default per `lang`; `--engine say` gives Milena for `ru`; each
  mismatch is a usage error.
- Each Silero fallback cause in `narrate.sh`; exit 2 passes through without fallback for both
  Kokoro and Silero; the Milena-missing failure.
- Silero refuses a speed other than 1.0.

### 7.2 Validator and timeline (`test_video_timeline.py`, `test_video_timeline_brainrot.py`)

- `lang` accepts `en`, `ru` and absence; rejects any other value and a non-string.
- `pronounce` without `lang: "ru"`, a non-object, an empty key and a non-string value are
  errors.
- `lang: "ru"` with `format: "brainrot"` is an error.

### 7.3 Transcript, render and workspace

- `transcript.py` writes `<html lang="ru">` for a Russian script and `lang="en"` otherwise.
- The Narrator row for Silero, Russian `say`, and Russian `say` with a fallback cause; the
  English rows unchanged.
- `video-workspace.sh --engine silero`: cost line, `.part` download, sha check (a mismatch
  deletes the part and fails), done line; stubbed `curl` as in the existing workspace tests.

### 7.4 Live acceptance

One real Russian explainer video (for example `ImportController.java` of inavcalculator, as in
the English live run): `render.sh` passes, `verify.sh` passes, `verify_sync.py` passes, the
Narrator row reads `silero (xenia)`, and the user listens to it and accepts it.

## 8. Sequencing

Planning starts after brainrot wave `brainrot-render` closes (and `brainrot-live-run`, if the
wave map orders it first). This branch is then rebased onto the tip of `feat/explain-brainrot`
so that the plan reads the code that exists. The work owns `narrate.py`, `narrate.sh`,
`build-timeline.mjs`, `render.sh`, `video-workspace.sh`, `transcript.py`, `SKILL.md` and
`rungs/video.md`, which overlap the brainrot waves; running in parallel would need a manual
merge of four files. The work is expected to fit one plan of at most 10 tasks (floor rule);
planning confirms this or returns to a wave map.

## 9. Evidence: voice probe (2026-10-04)

Throwaway samples in `/tmp/ru-voices`, two sentences: plain Russian and Russian with
`ImportController`, `JSON`, `Kafka`, `KafkaTemplate`.

| Engine | plain | mixed |
|---|---|---|
| macOS Milena | 8.3 s | 7.1 s |
| Piper `denis` | 8.2 s | 6.5 s |
| Piper `irina` | 9.0 s | 7.2 s |
| Silero `eugene` | 7.3 s | 3.2 s (Latin dropped) |
| Silero `xenia` | 8.2 s | 3.7 s (Latin dropped); 6.1 s hand-transliterated |

A digits test gave the same result: «Код 404, порт 8080, версия 2.5.» took 1.7 s, so the
numbers were dropped. Silero's text cleaner removes every character outside its symbol set.
The user judged Silero clearly the best on plain Russian.

Licences: the Silero Russian models are CC BY-NC 4.0, which fits the user's personal,
non-commercial use. Piper `denis` and `dmitri` (CC0 data) stay the fallback candidates if the
use ever becomes commercial.

## 10. Decisions log

| # | Decision | Why |
|---|---|---|
| R1 | No Russian STE profile; non-English artifacts apply only the structural rules | STE is English by definition; only the length rules carry over, and a Russian lint is a separate design |
| R2 | Silero `v5_3_ru`, speaker `xenia`, for Russian | Best Russian sound in the probe, with automatic stress and ё; deterministic output suits the sync checks |
| R3 | `say -v Milena` as the Russian fallback | No setup; mirrors the English Kokoro → `say` chain |
| R4 | A `pronounce` map written by the script author, plus a loud guard | Silero drops Latin and digits silently; automatic transliteration mangles English; Cyrillic-only narration would break the transcript and cites |
| R5 | Russian is for the explainer format only | Silero has no numeric speed; brainrot needs 1.2 |
| R6 | English sidecars and Narrator rows unchanged | Existing caches and tests stay valid |
| R7 | Plan after brainrot-render closes, on its branch | The same files; avoids a four-file manual merge |
