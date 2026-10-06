# Explain: Russian artifacts and a voice per language — design

Date: 2026-10-04, amended 2026-10-06
Status: approved by the user (2026-10-04), after section-by-section approval and a three-reviewer spec
review. Amended 2026-10-06 to target the film format (film spec `2026-10-05-explain-film-design.md`
§11 and decision D4), then cold-reviewed by three reviewers; the amendment was approved by the
user on 2026-10-06. Section 11 lists what changed.
Base: `main` at `683eeef` (brainrot, film and lesson are merged). Line numbers below are as of that
commit; the plan re-locates any that move.

## 1. Purpose

The user reads `/explain` artifacts to learn about software: their own code and general
topics. They want them in Russian as well as in English. Today a sheet or a page can already
be written in Russian on request (`SKILL.md:128`, convention 7), but four things are wrong or
missing:

- the STE profile tells the author to apply English-only vocabulary rules to Russian text;
- every template hardcodes `<html lang="en">`;
- the video rung and the lesson rung stop on any non-English request (`rungs/video.md:14-15`,
  `rungs/lesson.md:32-33`), because narration is English only (Kokoro `af_heart` with
  `lang="en-us"`, `say` with the default voice);
- a Russian narration through either English voice drops or mangles the words.

This design makes Russian a first-class artifact language for sheets, pages, films and lessons,
and picks the narration voice from the artifact language. Brainrot stays English.

Success means:

- `/explain <subject> --as video`, asked in Russian, gives a Russian film whose `render.sh` run
  prints its eleven `ok` lines (`sync: ok` and the `transcript` stage's `verify.sh` among them),
  with a transcript marked `lang="ru"`;
- `/explain <subject> --as lesson`, asked in Russian, gives a lesson page marked `lang="ru"`
  whose clips are Russian clips that pass `render.sh` as above;
- every term in Russian narration is spoken as written in `pronounce` or fails the run before
  synthesis: no word, number, acronym or abbreviation is silently dropped, merged or cut;
- English films, clips, brainrot shorts, sheets and pages behave as before: the same cached
  clips, the same Narrator rows, the same word marks. One English text changes: the fallback
  cause of a Kokoro run that fails with a `narration: FAIL` line of its own (§4.7).

## 2. Scope

In scope:

- `lang` and `pronounce` keys in `script.json`, with shape checks in `build-timeline.mjs`.
- A Silero engine in `narrate.py`, chosen by `lang`, with `say -v Milena` as its fallback.
- The spoken-text pipeline and a pre-flight guard for Russian (`narrate.py --check`).
- Word marks of a Russian film weighted by the spoken length of each written token.
- `silero` accepted by `narrate.py`, `build-timeline.mjs`, `render.sh`, `narrate.sh` and
  `video-workspace.sh`; `render.sh` picks the engine from `lang`.
- `<html lang>` from the artifact language in the sheet, the page, the lesson page and the
  transcript of a film, a clip and a brainrot short.
- `SKILL.md` (conventions 1 and 7, Build procedure step 1, the router lines), `rungs/video.md`
  and `rungs/lesson.md`: structural STE rules for non-English artifacts; the "English only"
  stops of the video and lesson rungs removed; a Russian timing budget; Silero setup notes.
  `rungs/page.md` and `rungs/sheet.md`: the `<html lang>` edit. `README.md`'s requirement and
  cost lines.
- Silero model download in `video-workspace.sh`, safe when two renders fetch it at once; a sha
  check before every model load.

Out of scope:

- Brainrot in Russian. `render.sh` narrates brainrot at speed 1.2 (`BRAINROT_SPEED`,
  `render.sh:159`) and Silero has no numeric speed (its `apply_tts` takes no speed argument).
  `rungs/brainrot.md:16-17` stays as it is: a Russian `--as brainrot` request stops and offers
  `page`.
- Languages other than English and Russian.
- A Russian controlled-language profile or a Russian lint.
- Automatic transliteration. The script author writes the `pronounce` map.
- A higher-quality English engine. Kokoro `af_heart` stays.
- Russian text in the fixed strings of the templates and rung markup, which stay English on a
  `lang="ru"` page: the labels of `video.html` (`Narrator`, `Not covered` and the others), the
  `Play all` button and its `Part k of N` text and the `Not covered:` line (`page.html:431`) in
  `page.html` and `sheet.html`, and the `transcript` link text of a lesson's `figure.clip`
  (`lesson.md:118`).

## 3. Interface

### 3.1 `script.json`

Two new optional top-level keys, for every format:

| Key | Value | Default |
|---|---|---|
| `lang` | `"en"` or `"ru"` | `"en"` when absent |
| `pronounce` | object: written term → spoken Russian form | absent |

Example: `"lang": "ru", "pronounce": {"ImportController": "импорт-контроллер", "JSON":
"джейсон", "Kafka": "к+афка", "404": "четыреста четыре", "СУБД": "эс-у-бэ-дэ"}`.

A key is one written token or a part of one: it may be Latin or Cyrillic and may hold
punctuation, but it holds no whitespace and does not end with `.`, `?` or `!`. Narration is
cut into sentences on the written text before synthesis (`split_sentences`, `narrate.py:131`:
after `.`, `?` or `!` followed by whitespace, never inside a pair of backticks), so a key such
as `т. е.` would be split across two sentences and never match, and a key `т.` would match but
leave a 0.15 s join gap after it. An abbreviation is written out in the narration («то есть»),
not mapped; the guard says so (§4.4, rule 3).

A value may mark stress with `+` before a vowel, as Silero reads it (`к+афка`). Milena ignores
the `+` (probed 2026-10-06). The narration, cites, transcript, words file and marks keep the
written terms; only the audio and the word weights (§4.3) use the spoken form. Write stress marks
only in values: a `+` in the narration shows in the transcript.

### 3.2 Validator rules (`build-timeline.mjs`)

- The top-level key whitelist of `checkHeader` (`build-timeline.mjs:622`: `format, title,
  subject, provenance, scenes`, plus `sources` for every format but brainrot) gains `lang` and
  `pronounce` for every format.
- New FAIL lines, prefix `FAIL script: `, after the format line, in this order:
  - `lang must be en or ru` (any other value, or a non-string);
  - `lang ru is for the film and clip formats only` (`lang: "ru"` with `format: "brainrot"`);
  - `pronounce needs lang ru` (`pronounce` present and `lang` not `"ru"`);
  - `pronounce must be an object`;
  - for each key in order: `pronounce key "<k>" is empty`, `pronounce key "<k>" holds
    whitespace`, `pronounce key "<k>" ends with "<c>"` (`<c>` one of `. ? !`), `pronounce value
    of "<k>" must be a string with a non-space character`.
- `ENGINES` (`build-timeline.mjs:167`) gains `silero`; the header comment (line 7), the usage
  text (line 173) and the build-mode engine error (line 1034) name all three engines. A Silero
  build reads `<id>.silero.words.json` and writes the clip path `audio/<id>.silero.wav`; the
  read (`readWords`, line 712) and its FAIL lines are unchanged.
- The character rules of the spoken text are not checked here; the guard (§4.4) owns them.

### 3.3 `narrate.py` command line and engine selection

The first choice and the fallback of each language are in §4.1. One table in `narrate.py`
maps `lang` to its first choice; `narrate.py --check` is its only reader.

`narrate.py` has two command lines (today one, `narrate.py:374-385`, with `--engine` required
and `audio_dir` positional):

- `narrate.py --check [--engine kokoro|silero|say] [--speed <d.d>] <script.json>`: no audio
  directory, no `--models`. On success it prints exactly one line on stdout, the engine to use
  (the given `--engine`, or the first choice of `lang`, `en` when absent), and exits 0. On a
  script error it prints its `narration: FAIL ` lines on stdout (§4.4) and exits 2; an
  unexpected exception while checking is caught and printed as `narration: FAIL script
  <path>: <message>`, exit 2, never a traceback.
- `narrate.py --engine kokoro|silero|say [--models <dir>] [--fallback "<cause>"] [--speed
  <d.d>] <script.json> <audio-dir>`: `--models` is required for `kokoro` and `silero`. A
  synthesis run applies every check of `--check` first, with the same lines and exit 2, so a
  direct caller is guarded too.

`render.sh`:

- `--engine` becomes optional (`kokoro | silero | say`); the default is no longer `kokoro`
  (lines 5, 162, 167 and the name check at line 184; header lines 28 and 36).
- `stage_script` (lines 293-318) runs `python3 narrate.py --check [--engine <e>] <script.json>`
  after `build-timeline.mjs --check` (line 309). It reads stdout only; the line must be one of
  `kokoro`, `silero`, `say`, else `script: FAIL narrate.py --check printed no engine`. The
  engine is passed explicitly to `video-workspace.sh` (`stage_workspace`, line 360) and
  `narrate.sh` (`stage_narration`, lines 413-438). A narration failure before `durations.json`
  exists is labelled `narration (<resolved engine>): FAIL …`.
- A failed check prints `script: FAIL <cause>`, where `<cause>` is the check's first
  `narration: FAIL ` line without that prefix (or `first_cause`, lines 237-247, of its output
  when it has none), then the check's output indented, and exits 1 before the `workspace` stage.
  (`first_cause` alone would print `script: FAIL narration: FAIL …`; the stage strips it.)

`narrate.sh`:

- `--engine` accepts `kokoro | silero | say`; without it the engine is the one `--check`
  prints.
- Right after argument parsing it runs `python3 narrate.py --check [--engine <e>] --speed
  <d.d> <script.json>`. This replaces the header's "Only builtins run before the uv check"
  invariant (lines 22-23): with no `python3` on PATH it prints `narration: FAIL python3 not
  found`, exit 1, as `run_say` does today (lines 81-84). A check that exits 2 ends
  `narrate.sh` with its output and exit 2; any other non-zero exit ends it with its output and
  exit 1. Neither falls back. It then checks the model files of the chosen engine only (today
  lines 94-96 check the two Kokoro files for every non-`say` run).
- `--engine say` forces the fallback voice of the script's `lang`.

The docstring of `narrate.py` (lines 2-26) and the headers of `narrate.sh` (lines 2-23),
`render.sh` and `video-workspace.sh` (lines 5, 15, 24) are updated to match.

## 4. Narration

### 4.1 Voice per language

| `lang` | First choice | Labelled fallback |
|---|---|---|
| `en` | Kokoro `af_heart`, 24 kHz (unchanged) | `say`, default voice, 22050 Hz (unchanged) |
| `ru` | Silero `v5_3_ru`, speaker `xenia`, 48 kHz | `say -v Milena`, 22050 Hz |

The speaker was chosen by ear in the voice probe (§9). Every format narrates one sentence at a
time (`narrate.py:15-21`); so does Silero: it is called once per sentence.

### 4.2 Spoken text for Russian

`synth_sentences` (`narrate.py:281`) cuts the written narration into sentences with
`split_sentences` (line 131) and synthesises each one alone. For a Russian script, the text an
engine reads for one sentence is made from the sentence's tokens (Python `str.split()`, which
also splits on U+00A0, U+202F, tabs and newlines). Each token becomes its spoken form:

1. Remove backticks (today's `spoken()`, line 126).
2. Replace `pronounce` keys inside the token, in one pass: one regular expression, the
   alternation of all keys (escaped) sorted by length, longest first, each between
   `(?<![\w])` and `(?![\w])` (Python's `\w`: a letter, a digit or `_`), so a key matches only
   where the character before it is the token start or not a word character, and the
   character after it is the token end or not a word character. Matching is case-sensitive,
   and replaced text is not scanned again. In each value, every run of whitespace is first
   made one ASCII space.
3. Normalise to NFC (`unicodedata.normalize`), so a decomposed `й` or `ё` reads as one letter.

The spoken sentence is the spoken forms joined with one ASCII space. The join matters: Silero
keeps only the ASCII space and joins words across any other whitespace without an error ("в
базе" is read as "вбазе"). Since a key holds no whitespace (§3.1), a key always lies inside one
token; this is what lets §4.3 weigh each written token.

Both Russian engines (Silero and Milena) get the same spoken sentences, so a fallback says the
same words. The engine reads the text it is given; `narrate.py` makes the spoken form once, for
both. English scripts are unchanged: step 1 only, as today.

### 4.3 Marks

A film or a clip is timed by marks (film spec §6): a sentence start is measured, a word time is
an estimate.

- Sentence marks come from the join of the sentence clips (`join_clips`, `narrate.py:241`), so
  a `pronounce` expansion cannot shift them.
- Word marks come from `word_timings` (`narrate.py:152`): the words of a sentence share its span
  in proportion to a weight, today the token's length without backticks plus `END_WEIGHT` when
  the token ends a clause or the sentence. For a Russian script the weight is the length of the
  token's spoken form (§4.2) without its `+` marks, plus the same `END_WEIGHT`: a token `404` in
  the middle of a sentence weighs 16 («четыреста четыре»), not 3. For an English script the
  spoken form is the token without backticks, so every English weight, and every English word
  mark, is as today.
- The words file keeps the written tokens: `readWords` (`build-timeline.mjs:712`) compares them
  with the narration, and `kit/marks.ts` matches a mark against them (its `key`, line 41, keeps
  any Unicode letter or digit). The author marks `{ word: "JSON" }`, not the spoken form.

### 4.4 Pre-flight guard (`narrate.py --check`)

`--check` (§3.3) uses the standard library only. It reads the script, makes the spoken
sentences of every scene, and checks them before any model, uv or torch step. `render.sh` runs
it in `stage_script`, so a bad script fails before the workspace stage downloads anything;
`narrate.sh` runs it first on every call. It applies to every Russian run, whatever the engine,
including `--engine say`.

Script errors, all exit 2, each one line on stdout starting `narration: FAIL `. The first three
each stop the check alone, in this order:

1. the script cannot be read, or `format` is invalid (today's `load_script` errors,
   `narrate.py:345-359`), or `lang` or `pronounce` breaks a rule of §3.2 (the same causes as
   the validator, the first one only);
2. the engine does not fit `lang`: `engine <e> cannot narrate lang <l>` (`kokoro` with `ru`,
   `silero` with `en`);
3. `lang: "ru"` with a speed other than `1.0`: `lang ru narrates at speed 1.0 only`.

Otherwise, for a Russian script, one line for each character rule below that a script breaks.

Rules 1, 2, 4 and 5 read each spoken sentence of a Russian scene (after §4.2); rule 3 reads the
written narration with its backticks removed, because the cut is made there and a `pronounce`
value must not hide it:

1. Allowed characters: Cyrillic letters (`А–Я`, `а–я`, `Ё`, `ё`), the ASCII space, the
   punctuation `. , ! ? : ; - – — … « » " ' ( ) „ “ ” ‘ ’`, and `+` directly before a Cyrillic
   vowel (`аеёиоуыэюя`, either case). Silero drops the quotes and brackets harmlessly and reads
   the rest (§9).
2. No token (whitespace-delimited, with leading and trailing allowed punctuation stripped)
   holds two or more upper-case Cyrillic letters. Silero reads `СУБД` as one word and
   swallows `ОС`; the author spells an acronym out in `pronounce`.
3. No abbreviation. A written token is an abbreviation when, with leading `« ( " „ “ ‘ '` and
   trailing `» ) " ” ’ ' , ; :` stripped, it is
   - one Cyrillic letter other than `я` or `Я`, then `.` (`т.`, `е.`, `д.`, `г.`, `с.`); or
   - a `.` between two Cyrillic letters (`т.е.`, `т.д.`); or
   - the last token of a sentence that is followed by a sentence starting with a lower-case
     Cyrillic letter (after leading `« ( " „ “ ‘ '`): `напр.` in «напр. так».
   Silero reads `т. е.` letter by letter and `т.е.` as one word, and the cut splits a sentence
   in the middle. The author writes the words out; no `pronounce` key can map an abbreviation
   (§3.1).
4. At least one Cyrillic letter not directly after `+` in each sentence. A sentence of
   punctuation only (the text after the last terminator can be `...`), or `+ё` alone, makes
   Silero raise an empty `ValueError` (probed).
5. At most 900 characters in each sentence. Silero fails at about 1,476 characters ("probably
   it's too long"); 984 worked in the review probe. A whole scene within the 45-word limit is
   about 350, so only a long expansion reaches this rule.

The lines, in this order; each lists the scenes that break the rule in script order, scenes
separated by `; `. A token is shown verbatim in ASCII double quotes (Cyrillic not escaped),
each once per scene, in text order:

- rules 1 and 2: `unspoken text: <scene>: "<t>", "<t>"; <scene>: "<t>" (add to pronounce)`.
  The token is the spoken token, stripped as in rule 2, so the author sees what no key
  covered. A token with an offending character that is not a letter shows the code point of
  its first such character, and so does a token that mixes a Cyrillic letter with any other
  letter (a look-alike, such as a Latin `K` in `Kафка`).
- rule 3: `abbreviation: <scene>: "<t>", "<t>" (write the words out, as «то есть»)`, the
  written token.
- rule 4: `no letter: <scene> sentence <k>, <k>; <scene> sentence <k>`, with `<k>` from 1.
- rule 5: `too long: <scene> sentence <k> (<n> characters); … (max 900)`.

Example:

```
narration: FAIL unspoken text: tools: "KafkaTemplate", "8080"; intro: "JSON", "Kафка" (U+004B), "СУБД" (add to pronounce)
narration: FAIL abbreviation: intro: "т.", "е." (write the words out, as «то есть»)
```

The guard predicts the Silero faults that are known (§9). One it does not predict still never
passes silently: a Silero failure falls back to Milena, labelled with its cause (§4.7).

### 4.5 Cache sidecar

The sidecar of every clip has, after the speed line, the line `mode=sentences`
(`sidecar_text`, `narrate.py:105`). The sidecar of a Russian clip then has a `lang=ru` line,
then (Silero only) a `model=v5_3_ru@<the first 12 hex digits of the pinned sha256>` line, then,
in place of the narration, the spoken form of each written token (§4.2), one on each line, in
order. So an edit to `pronounce` re-synthesises the clips it changes; moving a word from one
value to the next, which keeps the joined text but changes the word weights, does too; and a new
pin re-synthesises every Silero clip.

A clip is reused only when its sidecar matches and its words file holds exactly the written
tokens (`narrate.py:324`). So a no-break space in place of a space reuses the clip (the tokens
are the same), and a backtick edit re-synthesises it (the tokens change). The sidecar of an
English clip is byte-for-byte as today, so existing caches stay valid.

### 4.6 Silero engine

- `SileroEngine(models)`: name `silero`, voice `xenia`, rate 48000, speed `1.0` (the check of
  §4.4 refuses any other).
- The pin is two module constants of `narrate.py`, `SILERO_SHA256` and `SILERO_SIZE` (§6.1).
  There is no environment override; tests import `narrate.py` and patch the constants.
- Before loading, it checks that `<models>/v5_3_ru.pt` exists (else `models missing:
  v5_3_ru.pt`). It opens the file once, checks its size and hashes it from that handle (else
  `model sha mismatch: v5_3_ru.pt`, and the package is never loaded), seeks to the start and
  passes the same file object to `torch.package.PackageImporter`, so the bytes it loads are the
  bytes it hashed. Both faults are `NarrationError` code 3 (the code of every engine fault, as
  Kokoro's); `narrate.sh` falls back on any non-zero exit (§4.7). The check runs before every
  load because loading the package runs code (its `extern_modules` include `builtins` and
  `os`); hashing 145 MB took 0.05 s.
- It loads the model once for the run with `load_pickle("tts_models", "model")`. For each
  sentence it calls `apply_tts(text=..., speaker="xenia", sample_rate=48000)`, clips the float
  samples to [-1, 1], scales by 32767, casts to int16, and writes mono 16-bit PCM with the
  standard-library `wave` module, which `join_clips` reads. Without the clip a peak above 1.0
  wraps to a loud click (a peak of 1.061 was measured on «Импорт-контроллер читает файл.»).
- Any exception from one sentence is a `SynthError`; its failure is `silero clip failed:
  <scene>: <message>`, code 3, the same shape as Kokoro's (`narrate.py:228-229`).
- `narrate.sh` runs it with `uv run --python 3.12 --with torch==2.14.1 --with numpy==2.5.3
  python3 -W ignore::SyntaxWarning narrate.py --engine silero --models <ws>/models …`. Every
  package load prints a `SyntaxWarning` from Silero's own text cleaner on stderr (probed); the
  flag keeps that line out of fallback causes. The first run downloads torch (127 MB wheel) into
  the uv cache.

### 4.7 Fallback and the `say` voice

- After `narrate.py --check` has passed, any non-zero exit of the first-choice engine's run
  falls back to `say`. The cause is the text after `narration: FAIL ` of the last such line
  on stdout when there is one, else `uv run failed: <last stderr line>` (else `exit <rc>`).
  Today only exit 3 reads the stdout cause (`narrate.sh:118-125`); this keeps uv's own exit 2 a
  fallback cause, as `test_narrate.py:370-375` requires. It applies to Kokoro too: a Kokoro run
  that ends with its own `narration: FAIL` line and exit 1 (a wrong sample rate,
  `narrate.py:337`) now shows that cause in place of `uv run failed: exit 1`.
- The Silero causes: `models missing: v5_3_ru.pt`, `model sha mismatch: v5_3_ru.pt`, `uv not
  found`, `uv run failed: <last stderr line>`, `silero clip failed: <scene>: <message>`.
- `SayEngine` takes the voice from `lang`: the default voice for `en` (sidecar `voice=say-default`
  as today), `Milena` for `ru` (`-v Milena`, sidecar `voice=Milena`).
- Before a Russian `say` run, `narrate.py` checks `say -v '?'`. A line there is `<name>
  <locale> # <sample>`, and a name can hold spaces (`Eddy (English (US))  en_US  # …`), so
  the name is the text before the locale column (`^(.+?)\s+([a-z]{2}_[A-Z]{2})\s+#`). The check
  passes when a line has the name exactly `Milena` and the locale `ru_RU` (today: `Milena
  ru_RU    # Здравствуйте! …`). If not: `narration: FAIL say voice Milena is not installed`,
  exit 1. The check is needed: `say -v <missing voice>` exits 0 and silently uses the default
  voice (probed).

### 4.8 `durations.json` and the Narrator row

`durations.json` (written at `narrate.py:400-401`) gains a `voice` key next to `engine`, for
every run (English ones too). Its values: `af_heart`, `say-default`, `xenia`, `Milena`.
`render.sh` reads it with `engine` and `fallback` (lines 424-432); a missing `voice` is the
existing `narration (<engine>): FAIL cannot read <out>/audio/durations.json`, since every run
rewrites the file. It builds the Narrator row in `narrator_text` (lines 278-287) from all three:

| Run | Narrator row |
|---|---|
| Kokoro | `kokoro (af_heart)` (unchanged) |
| English `say` | `say`, or `say (fallback: <cause>)` (unchanged) |
| Silero | `silero (xenia)` |
| Russian `say` | `say (Milena)`, or `say (Milena, fallback: <cause>)` |

## 5. Artifacts and prose

### 5.1 `<html lang>`

- Sheet, page and lesson page: the author sets `<html lang>` (line 2 of `sheet.html` and
  `page.html`) to the artifact language (`en` or `ru`) when filling the template. The rung files
  say so next to the other template edits ("Fill the template" in `sheet.md:25` and
  `page.md:32`; "The page" in `lesson.md:97`).
- Transcript: `video.html` line 2 gets a `{{lang}}` marker, and the marker list in its comment
  (lines 11-15) names it; `transcript.py` fills it from the script's `lang` (default `en`) and
  adds it to the marker dict of `render_page` (`transcript.py:250-270`). This covers the
  transcript of a film, of a brainrot short and of each lesson clip (`clips/<id>/index.html`).

### 5.2 `SKILL.md` and the STE profile

Replace the language rule (`SKILL.md:128`, convention 7) with: write the artifact in English
unless the user asks for another language. For a non-English artifact, apply only the structural
rules of the STE profile (sentence length, paragraph length, active voice, one instruction in
each sentence); the English vocabulary and the substitution table do not apply. Put each English
term and code name in `<code>` (or backticks in a video script): `ste_lint.py` skips code, and
its `WORD` and `CONTRACTION` rules still fire on bare Latin words in Russian prose ("provide",
"via", "it's"; probed 2026-10-06: Cyrillic prose passes, `via` and `provide` fail).

Four other lines tell the author to write all prose under the STE profile with no exception:
convention 1 (`SKILL.md:87`), Build procedure step 1 (`SKILL.md:132`), and `rungs/lesson.md:12`
and `:44`. Each points to convention 7 for a non-English artifact.

### 5.3 Router and rung files

- `SKILL.md:68`: replace "The video rung is English only." with: a video can be English or
  Russian.
- `SKILL.md:69-70`: "The brainrot rung is English only, like the video rung." becomes "The
  brainrot rung is English only."
- `SKILL.md:71-72`: "The lesson rung is English only, like the video rung." becomes: a lesson
  can be English or Russian.
- `rungs/brainrot.md:16-17` stays.
- `rungs/video.md`:
  - remove the "English only" stop (lines 14-15). In its place: a film is English or Russian; a
    Russian film carries `"lang": "ru"`; for any other language, print the rung line, say that
    the video rung is English or Russian, stop, and offer `page`;
  - the key table of "Write the script" (lines 44-54) documents `lang` and `pronounce`: every
    Latin term, number and acronym the narration speaks needs a `pronounce` entry; a key is one
    token with no whitespace and no final `.`, `?` or `!`; abbreviations are written out;
    stress marks go only in values; prefer Russian words to code names, as for English; `+`
    before a vowel fixes stress;
  - line 71 ("Write the narration in STE"): for a Russian film, the structural rules of
    convention 7. Line 73 (a number as the voice must say it): in a Russian film, write a number
    in words, or map its digits in `pronounce`;
  - the labels on the stage are in the artifact language; code names and source lines stay as
    written;
  - lines 111-118 (length): Silero speaks about 2.3 to 2.9 words a second (2.3 in the first
    probe, 2.9 on longer text in the review) against about 2.8 for Kokoro. A safe total for the
    longest Russian film is about 270 words, against 350 in English (line 118). These are
    targets; the validator limit stays 45 words a scene;
  - line 380 ("Add `--engine say` only when the user asks in words for the macOS voice"): the
    engine follows `lang`; `--engine say` gives Milena for a Russian film;
  - "The FAIL lines" table gains the guard's lines as the `script` stage prints them
    (`script: FAIL unspoken text: …`, `abbreviation: …`, `no letter: …`, `too long: …`) and
    the engine line (`script: FAIL engine <e> cannot narrate lang <l>`);
  - "First-run costs" (lines 483-494), "Narration fallback" (lines 496-502), "Handoff" (line
    565), "Output directory" (line 576, the engine names of the audio files) and "Pinned
    versions and environment" (lines 580-595): add the Silero equivalents (145 MB model, 127 MB
    torch on the first run, `silero (xenia)`, `say (Milena)`, the URL and the sha pin). These
    five sections are shared with `brainrot.md` (`SHARED_TITLES`, `test_rung_drift.py:65-66`)
    and may hold none of `FILM_VALUES` (line 668: `film`, `Film`, `1280`, `720`, `scene/`,
    `eleven`, `speed`): the Silero notes name the language (`ru`, Russian), never the format
    or the speed.
- `rungs/lesson.md`:
  - lines 32-33: the same change as `video.md`: a lesson is English or Russian. A Russian
    lesson sets `<html lang="ru">` on its page and `"lang": "ru"` in every clip script; the
    page prose follows convention 7;
  - the clip limits stay (60 s cap, line 189). At the Silero rate, a usual clip of 20 to 40 s
    (line 82) holds about 45 to 90 Russian words;
  - lines 298-299: "the first Kokoro narration resolves its Python packages" becomes "the first
    narration of an engine resolves its Python packages" (Silero: torch).
- `rungs/page.md` and `rungs/sheet.md`, "Fill the template": set `<html lang>` (§5.1).
- `README.md:40-53`: the Silero model and torch in the costs; the voice per language in the
  narrator paragraph.

Three edited files must stay clean under the STE lint: `rungs/video.md`
(`test_rung_drift.py:601`), `SKILL.md` (`test_render.py:848-851`) and `rungs/lesson.md`
(`test_lesson_prompts.py:316-319`). Every Russian word, engine name or language code they quote
(`ru`, `Silero`, «то есть») goes in backticks.

## 6. Pipeline, checks and errors

### 6.1 Workspace (`video-workspace.sh`)

`fetch_model` (line 106) takes the download URL as an argument (today it builds it from the
fixed Kokoro `model_base`, lines 59 and 110). `--engine silero` downloads
`https://models.silero.ai/models/tts/ru/v5_3_ru.pt` into `<ws>/models`, checks its sha256, then
moves it into place, with the same cost and done lines as the Kokoro files
(`workspace: download v5_3_ru.pt (145 MB)`, `workspace: downloaded v5_3_ru.pt`):

- sha256 `f036d3da1584899e5e24bdf2d5bd3bcf896e2d62505de39a02caca76014d7a1c`
- size 145359640 bytes

A sha mismatch deletes the part file and fails the step. A Kokoro file already in place is left
alone, as today. A Silero file already in place is hashed (0.05 s), and fetched again when it
does not match the pin: `narrate.py` refuses a mismatched file before every load (§4.6), so a
bad file left in place would make every Russian run fall back.

Two renders can now run at the same time (film spec §7.6, D8), and a lesson renders its clips
at once (`lesson.md:295-300`). Each fetch, Kokoro's too, downloads to a part file of its own
(`<name>.<pid>.part`, today the shared `<name>.part`, line 107), so two first fetches never
write one file; the checked file reaches its place by `mv`, an atomic rename in one directory.
A second fetch that ends after the first replaces the file with the same checked bytes, and a
narration that has the old file open keeps reading it. A trap removes the fetch's own part
file on EXIT, HUP, INT and TERM, so a stopped download leaves no part file behind.

### 6.2 Run directory

`<ws>/models` stays shared and is written only by `video-workspace.sh` (film spec §7.6). Nothing
of Silero goes into a run directory: `narrate.sh` reads the model from `<ws>/models` and writes
the clips to `<output-dir>/audio`, and `copy_clips` (`render.sh:456-466`) copies each clip into
the run's `public/audio` by the path the timeline gives (`audio/<id>.silero.wav`).

### 6.3 Stage lines

The existing lines keep their shape; `<engine>` can now be `silero`:
`narration (silero): ok`, `narration (say): ok (fallback: <cause>)`. A guard failure shows at
the `script` stage: `script: FAIL unspoken text: …`, and so does an engine that does not fit:
`script: FAIL engine kokoro cannot narrate lang ru`.

### 6.4 Exit codes of `narrate.sh`

- `narrate.py --check` exits 2: `narrate.sh` prints its output and exits 2, no fallback.
- `narrate.py --check` exits with another non-zero code: `narrate.sh` prints its output and
  exits 1, no fallback.
- The first-choice engine's run fails with any code: fallback to `say` (§4.7).
- The `say` run fails: exit 1, as today.

### 6.5 Errors

| Fault | Result |
|---|---|
| unspoken text, acronym, abbreviation, a sentence with no letter, over 900 characters (§4.4) | `narration: FAIL …`, exit 2; `script: FAIL …` under `render.sh` |
| `--engine` does not fit `lang` (§3.3) | `narration: FAIL engine <e> cannot narrate lang <l>`, exit 2; `script: FAIL …` under `render.sh` |
| `lang ru` with speed other than 1.0 | `narration: FAIL lang ru narrates at speed 1.0 only`, exit 2 |
| a rule of §3.2 (`lang`, `pronounce`, `ru` with brainrot) | validator error (`script` stage); `narration: FAIL …`, exit 2, under `narrate.sh` alone |
| Silero model missing or sha mismatch, uv missing, uv run failed (including uv's own exit 2), one clip failed | `say -v Milena` fallback, cause on the Narrator row |
| Milena not installed | `narration: FAIL say voice Milena is not installed`, exit 1 |
| Download sha mismatch | `workspace: FAIL` (§6.1) |

## 7. Testing

TDD in the existing suites. Every assertion that closes a named fault is checked against the
broken state (the mutation in the test docstring, as the suites do today). The Russian narrate
tests use a film script (`templates/video-script.json`), not the brainrot template that
`test_narrate.py:20` loads, since `ru` with brainrot is refused.

### 7.1 Narration (`test_narrate.py`, `test_narrate_sentences.py`)

- Engine, in-process (`narrate.py` imported, the pin constants patched, a stub `torch.package`
  module): the stub asserts the speaker `xenia` and the rate 48000, and records each text, so
  the test asserts one call for each sentence with the spoken sentence; a stub that returns
  samples above 1.0 gives int16 at ±32767, not wrapped; with a pin that does not match,
  `PackageImporter` is never called and the cause is `model sha mismatch: v5_3_ru.pt`; the file
  object given to `PackageImporter` is the one that was hashed.
- Spoken text: a no-break space and a tab between two words become one ASCII space; a value
  with a no-break space gives one ASCII space; longest key first; whole-token boundaries
  (`Kafka` does not match inside `KafkaTemplate`; a Cyrillic neighbour blocks a match: `JSONом`;
  `JSON-файл` matches); two keys that overlap (`a-b` and `b-cd` in `a-b-cd`) give the result of
  the one-pass regular expression; one pass (a value is not re-scanned); case-sensitive; a
  Cyrillic key (`СУБД`); a decomposed `й` becomes one code point.
- Word weights: in a Russian sentence with `404` mapped to «четыреста четыре», the token `404`
  in the middle gets the share of weight 16, and `к+афка` weighs 5; the words file keeps the
  text `404`. The English weights of `test_word_weights` (`test_narrate_sentences.py:68`) stay
  as they are.
- Guard: each rule of §4.4 fails with its exact line: Latin, digit, symbol, `+` not before a
  vowel, `СУБД`, `т.`, `(т.`, `т.е.`, `напр.` before a lower-case sentence, a key `т` that maps
  `т.` (rule 3 still fires), a sentence of `...` only, `+ё` alone, a 901-character sentence.
  These pass: allowed punctuation, `+` before a vowel, «Так решил я.», `напр.` at the end of the
  narration. Several scenes and tokens appear in order, with `; `; the look-alike code point;
  the order of the first three errors (a load error alone; the engine before the speed); an
  exception inside the check gives a FAIL line and exit 2, not a traceback; the guard runs for
  `--engine say` and for a synthesis run without `--check`; English scripts are not guarded;
  `--check` prints the resolved engine and nothing else.
- Sidecar: `mode=sentences`, `lang=ru`, `model=v5_3_ru@f036d3da1584` (Silero only) and one
  spoken form on each line; a `pronounce` edit re-synthesises; moving a word between two values
  re-synthesises; a no-break-space edit reuses; the English sidecar equals a literal string.
- Engine selection: the default per `lang`; each mismatch is exit 2 before any model check.
- `narrate.sh` (fake `uv`, as the Kokoro tests use): a Silero run with no Kokoro files present
  gets the pinned command (`--with torch==2.14.1 --with numpy==2.5.3`, `-W
  ignore::SyntaxWarning`, `--engine silero --models <ws>/models`); each Silero fallback cause,
  including `model sha mismatch`; uv's own exit 2 (stderr only) still falls back with `uv run
  failed: …`; an engine exit with a stdout `narration: FAIL` line uses that line as the cause;
  `--check` exit 2 passes through with no `FALLBACK` line, for Kokoro and Silero; a `--check`
  that exits 1 ends `narrate.sh` with exit 1 and no fallback; no `python3` on PATH gives
  `narration: FAIL python3 not found`.
- Milena: `FAKE_SAY` (`test_narrate.py:53-68`) logs its `-v` value and answers `say -v '?'` from
  a fixture list. `--engine say` with a Russian script runs `say -v Milena` (asserted in the
  logged argv, not in the sidecar) with the spoken text (asserted in `FAKE_SAY_LOG`); the
  Milena-missing failure with a list where `Milena` is only part of another name (`Milena
  (Enhanced)`), and with a list that has no `ru_RU` line for it.
- `lang ru` with `--speed 1.2` is exit 2.
- `durations.json` has `voice` for each engine.

### 7.2 Validator and timeline

- `test_video_timeline_film.py`: `lang` accepts `en`, `ru` and absence; rejects any other value
  and a non-string. Each FAIL line of §3.2, with its text: `pronounce` without `lang: "ru"`, a
  non-object, an empty key, a key with a space, keys ending in `.`, `?` and `!`, a non-string
  value and a value of spaces only. Build mode accepts engine `silero`, reads
  `<id>.silero.words.json` and writes `audio/<id>.silero.wav`.
- `test_video_timeline_clip.py`: a clip with `lang: "ru"` passes.
- `test_video_timeline_brainrot.py`: `lang: "ru"` with `format: "brainrot"` is an error;
  `lang: "en"` passes.
- `test_film_contract.py` (the real `narrate.py` writes what the real `build-timeline.mjs`
  reads): a Russian film with `pronounce`, narrated by the say engine (Milena), builds; its
  timeline's `words` hold the written tokens, and the weight of a mapped token follows its
  spoken form.

### 7.3 Render, transcript, workspace and rung files

- Harness: `RUN_FAKES` (`test_render.py:463-494`) gains a fake `skill/video/narrate.py` that
  prints the engine it is told to (else `say`) for `--check`; every fake `narrate.sh` writes
  `voice` in `durations.json` (lines 265, 276 and 472); `RunHarness.start` (line 545) takes the
  engine as an argument, `None` for no `--engine`. `SCENE_RUN_FAKES`
  (`test_render_film.py:681`) inherits the fake.
- `test_render_film.py` (`SceneRunCase`): a film run with no `--engine` passes the engine that
  `--check` printed (`silero`) to the workspace and narration fakes.
- `test_render.py` (`RunHarness`): a `--check` that fails with a `narration: FAIL` line gives
  `script: FAIL <cause>` without the prefix, and one that fails without such a line gives the
  `first_cause` of its output; a `--check` that prints no engine name fails the stage; each
  stops before the workspace fake runs. `StageFunctionCase`: `stage_narration` labels a
  failure with the engine it was given.
- `test_render.py` (`NarratorTextCase`, the `narrator_text` helper at lines 180-186 takes the
  voice): the rows for Silero, Russian `say` and Russian `say` with a fallback cause; the
  English rows unchanged.
- `test_render.py:829-840` and `test_rung_drift.py:767-777` pin the English-only sentences of
  `SKILL.md`; they change with §5.3, and the brainrot rung's sentences stay pinned. New pins:
  the language sentences of `video.md` and `lesson.md`, and the `<html lang>` step of
  `page.md`, `sheet.md` and `lesson.md`.
- `test_transcript.py`: `transcript.py` writes `<html lang="ru">` for a Russian script and
  `lang="en"` otherwise.
- `test_video_workspace.py`: `--engine silero` gives the cost line, a part-file download from
  the Silero URL, the sha check (a mismatch deletes the part and fails) and the done line,
  with a stubbed `curl` as in the existing tests; a Silero file in place that does not match is
  fetched again, one that matches is not. Two fetches in one workspace with a barrier `curl`
  (each call writes half its part file, then waits until the other call has started): both end
  with the checked file in place and no part file left (red with the shared `<name>.part`). A
  fetch stopped by TERM leaves no part file.
- `test_rung_drift.py`: `video.md` lints clean; each new line that `video.md` quotes (§5.3:
  the guard and engine lines of the `script` stage) has a `PRINTED` entry whose evidence is the
  code that prints it (the cause in `narrate.py`, the prefix strip in `render.sh`), and is in
  `REQUIRED`; the shared sections hold no film value. `test_render.py:848-851` and
  `test_lesson_prompts.py:316-319`: `SKILL.md` and `lesson.md` lint clean.

### 7.4 Live acceptance

Rendered with no `--engine` flag:

- one Russian film (for example `ImportController.java` of inavcalculator, as in the English
  live run): `render.sh` prints its eleven `ok` lines and no `narration: FALLBACK` line; the
  Narrator row reads `silero (xenia)` and the transcript has `<html lang="ru">`;
- one Russian lesson of two clips, rendered as `lesson.md` says (the first alone until its
  narration line, then the rest at once): both renders pass, the page and the clip transcripts
  have `lang="ru"`, and `verify.sh` passes on the page;
- the user watches both and accepts them.

## 8. Sequencing

This branch is rebased onto `main` (`683eeef`); planning reads that code. The work owns
`narrate.py`, `narrate.sh`, `build-timeline.mjs`, `render.sh`, `video-workspace.sh`,
`transcript.py`, `templates/video.html`, `SKILL.md`, `rungs/video.md`, `rungs/lesson.md`,
`rungs/page.md`, `rungs/sheet.md` and `README.md`, and these tests: `test_narrate.py`,
`test_narrate_sentences.py`, `test_video_timeline_film.py`, `test_video_timeline_clip.py`,
`test_video_timeline_brainrot.py`, `test_film_contract.py`, `test_render.py`,
`test_render_film.py`, `test_transcript.py`, `test_video_workspace.py`, `test_rung_drift.py`
and `test_lesson_prompts.py`. No other feature is in flight on these files. The work is expected
to fit one plan of at most 10 tasks (floor rule); planning confirms this or returns to a wave
map.

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

### 9.3 Amendment probe (2026-10-06, `/tmp/ru-review2`)

- The model at `/tmp/ru-voices/models/v5_3_ru.pt` matches the sha and size pin; torch 2.14.1
  and numpy 2.5.3 resolve on Python 3.12; hashing the model takes 0.05 s.
- Without `-W ignore::SyntaxWarning`, every load prints `SyntaxWarning: invalid escape sequence
  '\^'` on stderr.
- Quotes and brackets are dropped harmlessly (byte-identical audio); `—` and `–` give the same
  audio; `+` is honoured (`кафк+а` differs from `кафка`) and its case does not matter; Milena
  ignores `+`.
- Abbreviations: «Смотрите т.е. пример.» 1.80 s against 1.44 s for «то есть»; «и т.д.»
  1.88 s against 2.16 s for «и так далее»; `напр.` is read as a word.
- `+ё` alone and `—.` raise an empty `ValueError`.
- A peak of 1.061 on «Импорт-контроллер читает файл.».
- `say -v NoSuchVoice` exits 0; the `say -v '?'` line format is as in §4.7.
- Python's `str.split()` splits on U+00A0, U+202F, U+2028 and U+0085, but not on U+FEFF or
  U+200B (rule 1 flags those).

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
| R5 | Russian is for the film and clip formats (and so the video and lesson rungs); brainrot stays English | Silero has no numeric speed; brainrot needs 1.2 (amended: was "the explainer format") |
| R6 | English sidecars, Narrator rows and word marks unchanged; only the fallback cause of a Kokoro run with its own FAIL line changes | Existing caches and tests stay valid; the new cause is the more precise one |
| R7 | Plan on `main` after the rebase (amended: was "after brainrot-render, on its branch") | Brainrot, film and lesson are merged; no branch owns these files now |
| R8 | Russian word marks weigh each written token by the length of its spoken form; sentence marks are measured (amended: replaces the cue frames on the spoken text) | Films have no cues; marks are what a film times from, and an expansion such as `404` would otherwise skew the word estimates |
| R9 | The guard is a stdlib pre-flight (`narrate.py --check`) at the script stage and first in `narrate.sh`; a synthesis run applies it too | Fails before 270 MB of downloads and before any fallback line; a direct call is guarded |
| R10 | A script error is told apart by the pre-flight, not by the engine run's exit code | uv exits 2 for its own errors, which must stay a fallback cause |
| R11 | The model sha is checked before every load, on the same open file that is loaded | Loading the package runs code; a pin checked only at download, or by path before a second open, does not protect a replaced file |
| R12 | A `pronounce` key is a single token with no final `.`, `?` or `!`; abbreviations are written out, and the guard finds them on the written text (new) | Sentences are cut on the written text before synthesis; a key across a cut never matches, a key at a cut leaves a join gap, and a value can hide an abbreviation from a check of the spoken text. A single-token key also makes R8's weights exact |
| R13 | `narrate.py --check` owns the `lang` → engine table and prints the resolved engine (new) | One table for `render.sh` and `narrate.sh` |
| R14 | Each model fetch uses its own part file, removed by a trap; a Silero file in place is re-checked (new) | Renders run at the same time since the run directories (film D8); a shared part file can be written by two downloads; a bad file in place would fall back forever |
| R15 | The Silero pin is module constants, patched by tests in-process; no environment override (new) | A stub model cannot match the pin, and an override would undo R11 |

## 11. Amendment of 2026-10-06

The 2026-10-04 design targeted the explainer format, which the film replaced (film spec D1, D4,
§10-§11). Kept as approved: the Silero engine and its pins, the spoken-text steps, the
`pronounce` map, the guard and its character rules 1, 2, 4 and 5, the fallback chain, the
Milena check, `durations.json`'s `voice` and the Narrator rows, `<html lang>`, convention 7.

Changed:

- `lang: "ru"` is for the film and clip formats (and so for films and lessons); brainrot stays
  English, and `rungs/brainrot.md:16-17` stays.
- The section that placed explainer cue frames on the spoken text, with its JS copy and shared
  fixture, is dropped: a film has no cues. Section 4.3 (Marks) replaces it: sentence marks are
  measured from the clip joins, and Russian word marks weigh each written token by its spoken
  length.
- `pronounce` keys are single tokens with no final `.`, `?` or `!`; the abbreviation key
  example (`т. е.`) is dropped. Guard rule 3 reads the written text and also finds `т.е.` and
  an abbreviation before a lower-case sentence; it lets a sentence-final «я.» pass.
- The spoken text is made per sentence, from the tokens of the written sentence, with values'
  whitespace normalised and NFC; the guard's rules 4 and 5 apply to each sentence, because
  Silero is called once per sentence.
- The sidecar always has `mode=sentences`; the Russian lines follow it, with the model's sha
  prefix and one spoken form for each token. A backtick edit now re-synthesises (the words file
  holds the written tokens).
- `narrate.py` has a `--check` command line that prints the resolved engine and catches its own
  exceptions; a synthesis run applies the same checks. An engine that does not fit `lang` fails
  at the `script` stage under `render.sh` (it was a usage error, exit 2), and the stage strips
  the `narration: FAIL ` prefix of the check's line. `--check` repeats the `lang` and
  `pronounce` rules of the validator.
- The guard's one FAIL line became one line for rules 1 and 2 together and one for each other
  rule, in a fixed order.
- The Silero engine hashes and loads one open file, its pin is patchable module constants, and
  its own speed refusal is dropped (the check owns the speed).
- The Milena check parses the name column of `say -v '?'`.
- The router and rung edits follow the current files: `SKILL.md:68`, `:69-70`, `:71-72`,
  `rungs/video.md:14-15`, `rungs/lesson.md:32-33` change; the four other STE lines point to
  convention 7; the Russian budget is about 270 words for the longest film, and a clip keeps its
  60 s cap. The shared sections of `video.md` stay free of film values, and the three linted
  rung files stay clean.
- Russian lessons are in scope: the lesson page's `<html lang>`, Russian clips, and the
  lesson rung's first-render note.
- Model fetches are safe when two renders start at once and leave no part file; the run
  directory holds nothing of Silero.
- The tests name the harness changes (`RUN_FAKES`, `FAKE_SAY`, a barrier `curl`) and a contract
  case in `test_film_contract.py`; the vacuous timeline assertion on written tokens is dropped.
- Every line reference and test file name is re-located to `main` at `683eeef`.
