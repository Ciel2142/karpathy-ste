# Explain Russian — Russian artifacts and a voice per language Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/explain <subject> --as video` or `--as lesson`, asked in Russian, gives a Russian film or lesson narrated by Silero `xenia` (fallback `say -v Milena`), guarded before synthesis so that no term is dropped silently, with every English path byte-for-byte as before.

**Architecture:** `script.json` gains `lang` and `pronounce`. `build-timeline.mjs` checks their shape. `narrate.py` owns everything about speech: a `Speech` value makes the spoken text and the word weights, a stdlib `--check` command line resolves the engine from `lang` and runs the guard, and a `SileroEngine` checks its pinned model and then loads it. `narrate.sh` and `render.sh` call `--check` first and pass on the engine it prints. `video-workspace.sh` fetches the Silero model safely when renders run at the same time. The transcript and the rung files carry `<html lang>`.

**Tech Stack:** Python 3 stdlib (`narrate.py`, `transcript.py`, `unittest`), bash (`narrate.sh`, `render.sh`, `video-workspace.sh`), Node (`build-timeline.mjs`), Silero `v5_3_ru` through `uv` + torch, macOS `say`/`afinfo`.

**Spec:** `docs/superpowers/specs/2026-10-04-explain-russian-design.md` (approved 2026-10-04, amendment approved 2026-10-06). One plan, floor rule: the spec's §8 expected ≤10 tasks, and the wave assessment found one cohesive wave (every task sits on the `narrate.py` → `narrate.sh` → `render.sh` critical path or documents it), nothing deferred, so there is no wave map.

Base: 7abbb65 (main after the cite-block merge; the branch was rebased onto it at planning, see decision 1).
Line numbers below are as of 7abbb65.
Test runs: scoped per task; full suite once, final task. Baseline at the base: `cd skills/explain && python3 -B -m unittest discover -s tests` gives `Ran 813 tests`, `OK (skipped=45)` (about 7 min).

## Global Constraints

- Work on branch `worktree-explain-russian` in `/Users/valukin/karpathy/.claude/worktrees/explain-russian`. Never commit to `main`. Never stage or commit `.beads/` (br runs from the main checkout `/Users/valukin/karpathy`).
- Run every test command from `skills/explain`, as `python3 -B -m unittest ...`. Run a command that takes more than 2 minutes (the full suite, a gated E2E, a live render) with its output in a log file, and poll the log with short `sleep 30; tail` calls until `OK`, `FAILED` or the last stage line. Never end a turn to wait for a notification.
- Gated and live renders (Task 10 only) set `EXPLAIN_VIDEO_WORKSPACE=/Users/valukin/karpathy-wt/russian-workspace`. Never render into `~/karpathy/video-workspace`.
- Pins, verbatim: model `v5_3_ru`, URL `https://models.silero.ai/models/tts/ru/v5_3_ru.pt`, sha256 `f036d3da1584899e5e24bdf2d5bd3bcf896e2d62505de39a02caca76014d7a1c`, size `145359640`; speaker `xenia`, 48000 Hz; `uv run --python 3.12 --with torch==2.14.1 --with numpy==2.5.3 python3 -W ignore::SyntaxWarning`; fallback voice `Milena`, locale `ru_RU`; join gap and `END_WEIGHT` unchanged.
- English is unchanged: the sidecar of an English clip, the English Narrator rows (`kokoro (af_heart)`, `say`, `say (fallback: <cause>)`) and every English word weight stay byte-for-byte as at the base. The only English text that changes is the fallback cause of a Kokoro run that ends with its own `narration: FAIL` line (spec R6).
- Whitespace, wherever a rule says it (a `pronounce` key, a value), is exactly the set of Python's `str.isspace()`: U+0009–U+000D, U+001C–U+001F, U+0020, U+0085, U+00A0, U+1680, U+2000–U+200A, U+2028, U+2029, U+202F, U+205F, U+3000. Python uses it natively (`str.split()`, `re` `\s`); `build-timeline.mjs` spells the same class out.
- `narrate.py --check` uses the standard library only; no import of torch, numpy, kokoro_onnx or soundfile on that path. `narrate.py` imports no numpy anywhere (system `python3` 3.14 has none).
- Files this plan may change: the owned files of spec §8, plus the new test module `tests/test_narrate_check.py` (decision 2) and the live-run note `docs/superpowers/spikes/2026-10-06-explain-russian-live-run.md` (Task 10). No template other than `templates/video.html`; no kit, no `verify.sh`, no `formats.json`.
- `rungs/video.md`, `SKILL.md` and `rungs/lesson.md` pass `skills/ste/scripts/ste_lint.py` with `0 errors, 0 warnings`. Every Russian word, engine name or language code they quote (`ru`, `Silero`, `xenia`, `Milena`, «то есть») goes in backticks. The five shared sections of `video.md` (`SHARED_TITLES`) hold none of `film`, `Film`, `1280`, `720`, `scene/`, `eleven`, `speed`.
- Code comments and test docstrings follow each file's style: short plain sentences; each test names the mutation that turns it red, and each new assertion is checked against that broken state (red first). Commits: `<type>: explain: <description>`, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. A mapped term inside backticks or with punctuation (`` `JSON`, ``, `404,`, `«Kafka»`), as convention 7 makes authors write it. Expected: the key still matches, the punctuation stays, and the weight is the spoken length (plus `END_WEIGHT` after the comma). Pinned by `test_mapped_token_keeps_its_punctuation` and `test_russian_word_weights` (Task 2).
2. A `pronounce` key with regular-expression characters (`C++`, `.NET`). Expected: it matches literally and only as a whole token. Pinned by `test_keys_with_regex_characters_match_literally` (Task 2).
3. A `pronounce` value that holds Latin or digits by mistake (`"JSON": "джейсон JSON"`). Expected: the guard reports the spoken token `"JSON"`, since it reads the spoken text. Pinned by `test_a_value_with_latin_is_reported` (Task 4).
4. An author passes `--engine kokoro` to a Russian film out of English habit. Expected: `script: FAIL engine kokoro cannot narrate lang ru` with the real tools, before the workspace stage downloads anything. Pinned by `test_kokoro_on_a_russian_film_fails_at_the_script_stage` (Task 7).
5. A key pasted with a no-break space (`Spring Boot` with U+00A0). Expected: both the validator and `--check` say `holds whitespace`; neither lets it through to never match. Pinned by `test_pronounce_key_rules` (Task 1) and `test_script_rules_of_the_validator` (Task 4).

## Beyond the letter of the spec (decisions made with no user present)

1. **Rebase onto 7abbb65.** The cite-block feature merged after the amendment was approved and changed nine owned files (`SKILL.md`, four rungs, `video.html`, `transcript.py`, `test_transcript.py`, `test_lesson_prompts.py`). The branch held only spec commits, so it was rebased with no conflict; line references are re-located against 7abbb65. Moved: convention 7 `SKILL.md:128`→`:130`, Build step 1 `:132`→`:134`, `page.md:32`→`:37`, `lesson.md:82`→`:84`, `:189`→`:190`, `:295-300`→`:307-308`, `test_lesson_prompts.py:316-319`→`:313-316`, `README.md:40-53`→`:45-53`.
2. **`tests/test_narrate_check.py` is new.** The guard and engine-selection cases (about 20) would push `test_narrate.py` past 800 lines. The new module holds the `--check` cases; `test_narrate.py` keeps the engines and `narrate.sh`.
3. **Code point in the unspoken-text line.** The spec's own example prints `"8080"` with no code point. So a code point is shown when the first offending character is not alphanumeric (`not c.isalnum()`: `#`, a misplaced `+`, U+200B), or when the token mixes a letter of `А–Яа-яЁё` with any other letter (the first such other letter). A Latin word or a number shows none.
4. **Rule 3 shows the written token stripped** of the leading and trailing characters that rule 3 strips (`(т.` shows as `"т."`), the same way rules 1 and 2 show the stripped spoken token.
5. **Two long sentences of one scene** print as `<scene> sentence <k> (<n> characters), <k> (<n> characters)`, as rule 4 does with `<scene> sentence <k>, <k>`.
6. **`Speech` makes the spoken text once.** `synth_sentences` passes each engine the spoken sentence, and the engines stop calling `spoken()` (spec §4.2: "the engine reads the text it is given"). For English the spoken sentence is today's `spoken(sentence)`, so the English text and cache are unchanged.
7. **`narrate.py`'s copies of the §3.2 rules print in today's load-error shape:** `narration: FAIL script <path>: <cause>`, with the validator's cause text.
8. **`narrate.sh` refuses an empty or unknown engine from `--check`** with `narration: FAIL narrate.py --check printed no engine`, exit 1, as `render.sh` does at its stage.
9. **`render.sh` does not capture the stderr of `--check`;** it goes to render.sh's stderr. Only stdout is parsed, and only stdout is indented below a `script: FAIL` line.
10. **Silero samples go through `tolist()` and the stdlib `array` and `wave` modules** (no numpy import), so the in-process tests run under system `python3` with a stub torch.
11. **Rule 2 stays literal.** A hyphenated proper noun with two capitals (`Санкт-Петербург`) is reported as unspoken text; the author maps it to its lower-case form. The handoff names this to the user.
12. **The live lesson's subject is `skills/explain/video/narrate.py`** of this branch (the spec names only the film's subject). The film is `ImportController.java` of inavcalculator, as in the English live run.
13. **The `Pinned versions and environment` section adds the Silero licence line** (CC BY-NC 4.0, personal use; spec §9), next to the Remotion licence line it already has.

---

### Task 1: `lang`, `pronounce` and `silero` in the validator

**Files:**
- Modify: `skills/explain/video/build-timeline.mjs:6-7` (header: build-mode engines), the header's format paragraph `:14-19` (document the two keys and their FAIL lines), `:167` (`ENGINES`), `:171-174` (`USAGE`), `:619-642` (`checkHeader`), `:1034` (engine usage error)
- Test: `skills/explain/tests/test_video_timeline_film.py`, `tests/test_video_timeline_clip.py`, `tests/test_video_timeline_brainrot.py`

**Interfaces:**
- Consumes: nothing new. `q(s)` (`:184`, `JSON.stringify`) quotes a key.
- Produces: the FAIL lines below (Task 4 prints the same causes from `narrate.py`), `ENGINES = ["say", "kokoro", "silero"]`.

```text
FAIL script: lang must be en or ru
FAIL script: lang ru is for the film and clip formats only
FAIL script: pronounce needs lang ru
FAIL script: pronounce must be an object
FAIL script: pronounce key <q(k)> is empty
FAIL script: pronounce key <q(k)> holds whitespace
FAIL script: pronounce key <q(k)> ends with "<c>"
FAIL script: pronounce value of <q(k)> must be a string with a non-space character
```

- [ ] **Step 1: Write the failing tests**

```text
film  test_lang_en_ru_and_absent_pass: --check of film_script() with lang "en", "ru" and no lang → exit 0, no output
film  test_lang_other_value_fails: lang "de", "RU", 1 and null → exactly ["FAIL script: lang must be en or ru"]
film  test_lang_lines_follow_the_format_line: format "slides" with lang "de" → FORMAT_LINE first, then the lang line
film  test_pronounce_needs_lang_ru: {"JSON": "джейсон"} with lang absent, and with "en" → exactly ["FAIL script: pronounce needs lang ru"]
film  test_pronounce_must_be_an_object: lang ru with pronounce [], "x" and null → exactly ["FAIL script: pronounce must be an object"]
film  test_pronounce_key_rules: lang ru, keys "", "a b", "Spring Boot", "т.", "что?", "да!" and values 5 and "  " → one line per broken rule, in key order, each key's lines in the order of the interface block
film  test_build_reads_silero_words: build mode with engine "silero" reads <id>.silero.words.json; the timeline's engine is "silero" and each scene's audio is "audio/<id>.silero.wav"
film  test_build_engine_error_names_three_engines: engine "festival" → exit 2, stderr names "say, kokoro or silero"
clip  test_a_russian_clip_passes: a clip script with lang "ru" and a pronounce map → exit 0, no output
brainrot test_russian_brainrot_is_refused: the brainrot template with lang "ru" → exactly ["FAIL script: lang ru is for the film and clip formats only"]
brainrot test_english_brainrot_passes: the brainrot template with lang "en" → exit 0, no output
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -B -m unittest tests.test_video_timeline_film tests.test_video_timeline_clip tests.test_video_timeline_brainrot`
Expected: `FAILED` (`unexpected key "lang"` and `engine must be say or kokoro`)

- [ ] **Step 3: Implement the rules in `checkHeader` and the engine list**

`checkHeader` allows `lang` and `pronounce` for every format. After the format line it reports, in order:
- the lang line when `lang` is present and is not the string `"en"` or `"ru"`;
- the brainrot line when `lang === "ru"` and `formatOf(script) === "brainrot"`;
- the needs line when `pronounce` is present and `lang !== "ru"`;
- the object line when `pronounce` is present and is not a plain object (an array, null or a string), and no key lines then;
- for each key in insertion order: the empty line alone for `""`; else the whitespace line when any character is in `WHITESPACE`, and the ends-with line when the last character is `.`, `?` or `!`; and the value line when the value is not a string or holds only `WHITESPACE` characters.

Add `const WHITESPACE = /[\t-\r\u001c-\u001f \u0085   -     　]/` (the Global Constraints set; JS `\s` differs in U+0085, U+001C–U+001F and U+FEFF). `ENGINES` gains `silero`; the header line 7, `USAGE` and the build-mode error name `say | kokoro | silero`. Build mode reads `<id>.<engine>.words.json` and writes `audio/<id>.<engine>.wav` already; no other change.

- [ ] **Step 4: Run them to verify they pass**

Run: the Step 2 command. Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/build-timeline.mjs skills/explain/tests/test_video_timeline_film.py skills/explain/tests/test_video_timeline_clip.py skills/explain/tests/test_video_timeline_brainrot.py
git commit -m "feat: explain: lang, pronounce and the silero engine in the script contract"
```

---

### Task 2: the spoken text, the word weights and the sidecar (`Speech`)

**Files:**
- Modify: `skills/explain/video/narrate.py:105-114` (sidecar), `:126-128` (`spoken`), `:152-177` (`word_timings`), `:180-202` (`synth_say`, `SayEngine.synth`), `:221-226` (`KokoroEngine.synth`), `:281-303` (`synth_sentences`), `:306-342` (`narrate`), `:345-359` (`load_script`), `:388-402` (`main`)
- Test: `skills/explain/tests/test_narrate_sentences.py`

**Interfaces:**
- Consumes: `split_sentences`, `join_clips`, `END_WEIGHT`, `CLAUSE_END` (unchanged).
- Produces (Tasks 3, 4 and 8 use them):

```python
class Speech:
    lang: str                     # "en" or "ru"
    pronounce: dict[str, str]
    def __init__(self, lang: str = "en", pronounce: dict[str, str] | None = None) -> None
    def spoken_tokens(self, text: str) -> list[str]      # the spoken form of each token of text.split()
    def spoken_sentence(self, sentence: str) -> str      # the text an engine reads for one sentence
    def token_lengths(self, sentence: str) -> list[int]  # the weight of each written token, before END_WEIGHT
ENGLISH: Speech                   # Speech()
def word_timings(sentences: list[str], spans: list[tuple[float, float]], speech: Speech = ENGLISH) -> list[dict]
def sidecar_text(engine, text: str, speech: Speech = ENGLISH) -> str
def sidecar_matches(sidecar: Path, engine, text: str, speech: Speech = ENGLISH) -> bool
def synth_sentences(engine, text: str, wav: Path, speech: Speech = ENGLISH) -> dict
def narrate(scenes: list[dict], engine, audio_dir: Path, speech: Speech = ENGLISH) -> dict[str, float]
def load_script(path: str) -> tuple[list[dict], Speech]
```

An engine has the attributes `name`, `voice`, `rate`, `speed` and `model` (`None` for `say` and `kokoro`), `synth(text, wav)`, which reads `text` exactly as given, and `failure(sid, message) -> NarrationError`.

- [ ] **Step 1: Write the failing tests** (class `SentenceText`, module loaded by path; new class `RussianSidecar(unittest.TestCase)` runs `narrate()` in-process with a stub engine: name `stub`, voice `v`, rate 22050, speed `"1.0"`, model `None` unless set, `synth` writes 0.1 s of 16-bit mono silence with `wave` and records each text; stdout captured with `contextlib.redirect_stdout`)

```text
test_spoken_ascii_space_joins_words: Speech("ru").spoken_sentence("в базе\tданных.") == "в базе данных."
test_spoken_value_whitespace_is_one_space: {"DB": "база  данных"} on "DB." → "база данных."
test_spoken_longest_key_first: {"Kafka": "кафка", "KafkaTemplate": "кафка темплейт"} on "KafkaTemplate" → "кафка темплейт"
test_spoken_whole_token_boundaries: {"Kafka": "кафка"} leaves "KafkaTemplate"; {"JSON": "джейсон"} leaves "JSONом" and makes "JSON-файл" → "джейсон-файл"
test_spoken_overlapping_keys_one_pass: {"a-b": "икс", "b-cd": "игрек"} on "a-b-cd" → "икс-cd"
test_spoken_value_not_rescanned: {"A": "B", "B": "в"} on "A" → "B"
test_spoken_case_sensitive: {"json": "джейсон"} on "JSON" → "JSON"
test_spoken_cyrillic_key: {"СУБД": "эс-у-бэ-дэ"} on "СУБД." → "эс-у-бэ-дэ."
test_spoken_nfc: "й" → "й" (one code point)
test_spoken_english_unchanged: Speech().spoken_sentence("Run `a`  now.") == "Run a  now." (no re-join)
test_mapped_token_keeps_its_punctuation: {"JSON": "джейсон", "Kafka": "кафка"} on "`JSON`, «Kafka»" → "джейсон, «кафка»"
test_keys_with_regex_characters_match_literally: {"C++": "си плюс плюс", ".NET": "дот нет"} → both mapped; "CXX" and "aNET" unchanged
test_russian_word_weights: word_timings(["Код 404 готов."], [(0.0, 2.7)], Speech("ru", {"404": "четыреста четыре"})) → widths 0.3, 1.6, 0.8 (weights 3, 16, 6+2); texts "Код", "404", "готов."
test_comma_after_a_mapped_token_weighs_end_weight: "Код 404, готов." → the 404 weight is 17 + END_WEIGHT
test_stress_mark_does_not_weigh: {"Kafka": "к+афка"} on "Это Kafka тут." → the Kafka weight is 5
test_russian_sidecar_lines: "JSON готов." with {"JSON": "джейсон"} → sidecar == "engine=stub\nvoice=v\nspeed=1.0\nmode=sentences\nlang=ru\nджейсон\nготов."
test_model_line_follows_lang: stub model "m@1" → "...mode=sentences\nlang=ru\nmodel=m@1\nджейсон\nготов."
test_engine_reads_the_spoken_sentence: the stub records ["джейсон готов."]
test_pronounce_edit_resynthesises: a second run with {"JSON": "джей сон"} prints "(synthesized)"
test_moving_a_word_between_values_resynthesises: "A B." with {"A": "икс игрек", "B": "зет"}, then {"A": "икс", "B": "игрек зет"} → "(synthesized)"
test_no_break_space_edit_reuses: "Один два." then "Один два." → "(reused)"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -B -m unittest tests.test_narrate_sentences`
Expected: `FAILED` (no `Speech`)

- [ ] **Step 3: Implement `Speech` and pass it through**

For `en`: `spoken_tokens` removes the backticks of each token, `spoken_sentence` is today's `spoken(sentence)` (whitespace kept), `token_lengths` is the length of each spoken token. For `ru`, each token goes through spec §4.2 in order: remove backticks; one `re.sub` with the pattern `(?<!\w)(?:k1|k2|…)(?!\w)` over the `re.escape`d keys sorted by length, longest first (stable for equal lengths), whose replacement is the value with each run of `\s` made one ASCII space (no pattern for an empty map); then NFC. `spoken_sentence` joins the spoken tokens with one ASCII space. `token_lengths` is the length of each spoken token with every `+` removed. `word_timings` takes the length from `speech.token_lengths` and keeps the `END_WEIGHT` test on the written token. `sidecar_text` for `ru` writes the four header lines, `lang=ru`, `model=<engine.model>` when the engine has one, then one spoken token on each line for the whole narration; for `en` it is byte-for-byte today's string. `SayEngine` and `KokoroEngine` get `model = None` and read `text` as given. `load_script` returns `Speech(script.get("lang", "en"), script.get("pronounce") or {})` with the scenes, and adds no rule (Task 4 adds them); `main` passes the `Speech` to `narrate`.

- [ ] **Step 4: Run them to verify they pass, with the English suites**

Run: `python3 -B -m unittest tests.test_narrate_sentences tests.test_narrate tests.test_film_contract tests.test_brainrot_contract`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/narrate.py skills/explain/tests/test_narrate_sentences.py
git commit -m "feat: explain: narrate.py makes the Russian spoken text, word weights and sidecar"
```

---

### Task 3: the Silero engine, Milena and the `voice` key

**Files:**
- Modify: `skills/explain/video/narrate.py:39-54` (constants), `:180-205` (`synth_say`, `SayEngine`), new `SileroEngine` after `KokoroEngine` (`:208-229`), `:388-402` (`main`: `SayEngine` gets the lang, `durations.json` gets `voice`)
- Test: `skills/explain/tests/test_narrate.py`

**Interfaces:**
- Consumes: `Speech`, `narrate`, `sidecar_text` (Task 2).
- Produces (Tasks 4, 5 and 7 use them):

```python
SILERO_FILE = "v5_3_ru.pt"
SILERO_SHA256 = "f036d3da1584899e5e24bdf2d5bd3bcf896e2d62505de39a02caca76014d7a1c"
SILERO_SIZE = 145359640
def silero_model_tag() -> str                    # "v5_3_ru@" + SILERO_SHA256[:12], read at call time
class SileroEngine:                              # name "silero", voice "xenia", rate 48000, speed "1.0"
    def __init__(self, models: str | Path) -> None   # self.model = silero_model_tag()
    def synth(self, text: str, wav: Path) -> None
    def failure(self, sid: str, message: str) -> NarrationError  # "silero clip failed: <sid>: <message>", code 3
class SayEngine:
    def __init__(self, speed: str, lang: str = "en") -> None     # voice "say-default" (en) or "Milena" (ru)
```

`durations.json`: `{"engine", "voice", "fallback", "scenes"}`, `voice` one of `af_heart`, `say-default`, `xenia`, `Milena`.

Test helpers in `test_narrate.py`: `FILM_TEMPLATE = EXPLAIN / "templates" / "video-script.json"`; `NarrateCase.write_ru_script(scenes, pronounce=None) -> Path` (the film template, `"lang": "ru"`); `load_narrate()` returns a fresh module loaded by path, so a patched constant never leaks; a stub torch put in `sys.modules` by `mock.patch.dict`, whose `package.PackageImporter(obj)` records `(obj, obj.tell())` and whose `load_pickle("tts_models", "model")` returns a model whose `apply_tts(text, speaker, sample_rate)` asserts `("xenia", 48000)`, records `text` and returns an object with `tolist()`. `FAKE_SAY` gains: `-v <voice>` appends the voice (`-` for a call without `-v`) to `FAKE_SAY_VOICE_LOG` when it is set; `-v ?` prints the file `FAKE_SAY_VOICES` (the real `say -v '?'` when unset) and exits 0; every other call passes `-v` through to the real `say`.

- [ ] **Step 1: Write the failing tests** (`SileroInProcess(unittest.TestCase)` with a 3-byte model file and the two pin constants patched to its sha and size; `RussianSay(NarrateCase)` through `python3 narrate.py --engine say`)

```text
test_one_call_per_sentence_with_the_spoken_sentence: "JSON готов. Второе предложение." with {"JSON": "джейсон"} → apply_tts texts ["джейсон готов.", "Второе предложение."]; the WAV is 48000 Hz
test_samples_are_clipped_not_wrapped: apply_tts returns [1.5, -1.5, 0.5] → frames (32767, -32767, 16383)
test_sha_mismatch_never_loads: SILERO_SHA256 patched to another sha → NarrationError code 3 "model sha mismatch: v5_3_ru.pt"; no PackageImporter call
test_size_mismatch_never_loads: sha matches, SILERO_SIZE one more → the same error; no PackageImporter call
test_missing_model: no file → NarrationError code 3 "models missing: v5_3_ru.pt"
test_the_hashed_handle_is_loaded: builtins.open wrapped: one open of the model path; PackageImporter got that very object at tell() == 0
test_clip_failure_names_the_scene: apply_tts raises RuntimeError("boom") for scene "two" → NarrationError code 3 "silero clip failed: two: boom"
test_model_tag_is_the_pin_prefix: unpatched silero_model_tag() == "v5_3_ru@f036d3da1584"
test_silero_sidecar_has_the_model_line: sidecar lines 5 and 6 == "lang=ru", "model=" + silero_model_tag()
test_russian_say_uses_milena_and_the_spoken_text: --engine say on a ru script → voice log all "Milena"; FAKE_SAY_LOG holds the spoken sentences; sidecar voice=Milena; durations voice "Milena"
test_english_say_passes_no_voice: voice log all "-"; durations voice "say-default"
test_milena_missing_when_only_enhanced: voices list "Milena (Enhanced)  ru_RU    # Здравствуйте!" → exit 1, stdout "narration: FAIL say voice Milena is not installed", no WAV
test_milena_missing_when_not_ru_RU: "Milena              en_US    # Hello" → the same
test_milena_found_among_spaced_names: list with "Eddy (English (US))  en_US    # Hello" and "Milena              ru_RU    # Здравствуйте!" → exit 0
test_kokoro_durations_voice: run_kokoro → durations voice "af_heart"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -B -m unittest tests.test_narrate`
Expected: `FAILED` (no `SileroEngine`, no `voice`)

- [ ] **Step 3: Implement the two engines and the `voice` key**

`SileroEngine.__init__`: a missing `<models>/v5_3_ru.pt` raises `models missing: v5_3_ru.pt` (code 3). It opens the file once in binary mode, compares its size (`os.fstat`) with `SILERO_SIZE` and the sha256 of its bytes, read from that handle, with `SILERO_SHA256`; either difference raises `model sha mismatch: v5_3_ru.pt` (code 3) before torch is imported. It then seeks to 0, imports `torch.package` lazily, passes the same handle to `PackageImporter`, calls `load_pickle("tts_models", "model")` and closes the handle once that call has returned. A load exception is not caught (narrate.sh reports it as `uv run failed: <last stderr line>`). `synth` calls `apply_tts(text=text, speaker="xenia", sample_rate=48000)`, takes `tolist()`, clips each sample to [-1, 1], multiplies by 32767, truncates to int (`int()`), and writes mono 16-bit 48000 Hz PCM with `array("h")` and `wave` (byte-swap when `sys.byteorder` is big). Any exception of one sentence is a `SynthError`. `SayEngine(speed, lang)`: for `ru` it first runs `say -v ?`, reads each line with `^(.+?)\s+([a-z]{2}_[A-Z]{2})\s+#`, and raises `NarrationError("say voice Milena is not installed", 1)` unless one line has the name exactly `Milena` and the locale `ru_RU`; `synth_say` passes `-v Milena` for `ru` and no `-v` for `en`. `main` builds `SayEngine(args.speed, speech.lang)` and writes `voice` next to `engine`. The command line does not reach Silero yet (Task 4).

- [ ] **Step 4: Run them to verify they pass**

Run: `python3 -B -m unittest tests.test_narrate tests.test_narrate_sentences`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/narrate.py skills/explain/tests/test_narrate.py
git commit -m "feat: explain: Silero engine with a pinned model, Milena for Russian say, voice in durations.json"
```

---

### Task 4: `narrate.py --check`: engine per lang and the guard

**Files:**
- Modify: `skills/explain/video/narrate.py:2-26` (docstring: both command lines, the exit codes, the guard), `:345-359` (`load_script`: §3.2 rules), new `ScriptError`, `check_script`, `guard_lines`, `:374-385` (`parse_args`), `:388-402` (`main`)
- Create: `skills/explain/tests/test_narrate_check.py`
- Test: `skills/explain/tests/test_narrate.py` (one `SileroInProcess` case)

**Interfaces:**
- Consumes: `Speech`, `split_sentences` (Task 2); `SileroEngine`, `SayEngine(speed, lang)` (Task 3).
- Produces (Tasks 5, 7 and 9 rely on the command line and its lines):

```python
FIRST_CHOICE = {"en": "kokoro", "ru": "silero"}   # check_script() is its only reader
class ScriptError(Exception):                     # .lines: list[str]; main prints each as "narration: FAIL <line>", exit 2
def check_script(path: str, engine: str | None, speed: str) -> tuple[list[dict], Speech, str]
def guard_lines(scenes: list[dict], speech: Speech) -> list[str]
def parse_args(argv: list[str]) -> argparse.Namespace   # .check: bool
```

```text
narrate.py --check [--engine kokoro|silero|say] [--speed <d.d>] <script.json>
narrate.py --engine kokoro|silero|say [--models <dir>] [--fallback "<cause>"] [--speed <d.d>] <script.json> <audio-dir>
script errors, stdout, exit 2:
  narration: FAIL script <path>: <load cause | format cause | §3.2 cause>
  narration: FAIL engine <e> cannot narrate lang <l>
  narration: FAIL lang ru narrates at speed 1.0 only
  narration: FAIL unspoken text: <scene>: "<t>", "<t>" (U+XXXX); <scene>: "<t>" (add to pronounce)
  narration: FAIL abbreviation: <scene>: "<t>", "<t>" (write the words out, as «то есть»)
  narration: FAIL no letter: <scene> sentence <k>, <k>; <scene> sentence <k>
  narration: FAIL too long: <scene> sentence <k> (<n> characters), <k> (<n> characters); <scene> sentence <k> (<n> characters) (max 900)
```

- [ ] **Step 1: Write the failing tests** (`test_narrate_check.py`: a `CheckCase` writes a script dict to a temp dir and runs `python3 narrate.py --check ...` or a synthesis line as a subprocess. The dict is the film template's header (the brainrot template's where a case says so) with the case's own scenes, `id` and `narration` only, in the given order; a `ru` case with no fault narrates clean Cyrillic, such as "Код готов.")

```text
test_check_prints_the_engine_of_the_lang: no lang → "kokoro\n"; ru → "silero\n"; ru with --engine say → "say\n"; exit 0, stderr ""
test_engine_must_fit_lang: ru --engine kokoro → exit 2, stdout "narration: FAIL engine kokoro cannot narrate lang ru\n"; en --engine silero → "... silero cannot narrate lang en"
test_lang_ru_narrates_at_speed_1_only: ru --speed 1.2 → exit 2, "narration: FAIL lang ru narrates at speed 1.0 only"
test_the_first_three_errors_stop_alone: format "slides" with lang ru and Latin narration → one line "narration: FAIL script <path>: format must be film, brainrot or clip"; ru, --engine kokoro, --speed 1.2 → the engine line alone
test_script_rules_of_the_validator: lang "de" → "narration: FAIL script <path>: lang must be en or ru"; brainrot with ru → "... lang ru is for the film and clip formats only"; key "Spring Boot" → '... pronounce key "Spring Boot" holds whitespace'; one line each
test_unspoken_text_line: scenes "tools" ("Шаблон KafkaTemplate на 8080.") and "intro" ("Это JSON, Kафка и СУБД.") → exactly the spec §4.4 example line
test_each_character_rule_fails: "#", "+т" (U+002B), U+200B inside a word, a digit, a Latin word, "ОС" → each token in the unspoken-text line, code points per decision 3
test_a_value_with_latin_is_reported: {"JSON": "джейсон JSON"} on "Это JSON." → 'unspoken text: intro: "JSON" (add to pronounce)'
test_abbreviation_line: four scripts of one scene "intro" each: "Это т. е. пример.", "Это (т. е. пример).", "Это т.е. пример.", "Смотрите напр. так." → 'abbreviation: intro: "т.", "е." (write the words out, as «то есть»)' and the stripped "т.", "т.е.", "напр." lines
test_a_key_does_not_hide_an_abbreviation: {"т": "то"} with "Это т. е. пример." → the abbreviation line still prints
test_these_pass: "«Так», — сказал он: (да) „нет“ ‘да’ … – конец!", "Так решил я.", "Это к+афка.", "Конец, напр." → exit 0
test_no_letter_line: intro "Начало. ..." and outro "+ё." → "no letter: intro sentence 2; outro sentence 1"
test_too_long_line: 900 "а" then "." → "too long: intro sentence 1 (901 characters) (max 900)"; 899 "а" then "." passes
test_lines_come_in_rule_order: two scenes breaking all four rules → four lines: unspoken text, abbreviation, no letter, too long; scenes in script order, separated by "; "
test_an_exception_is_a_fail_line_not_a_traceback: ru scene narration 5 → exit 2, stdout starts "narration: FAIL script ", no "Traceback" in stderr
test_english_is_not_guarded: an en narration with "8080" and "т.е." → "kokoro\n", exit 0
test_say_is_guarded_too: ru with "8080" and --engine say → exit 2, the unspoken-text line
test_synthesis_applies_the_check: --engine say <script> <audio> on that script → exit 2, the same line, no audio dir
test_mismatch_before_models: --engine kokoro --models <empty dir> on ru → exit 2, the engine line, not "models missing"
test_silero_needs_models: --engine silero with no --models → exit 2, usage on stderr
test_main_runs_silero_and_writes_voice_xenia (test_narrate.py, SileroInProcess): main(["--engine", "silero", "--models", <dir>, <ru script>, <audio>]) → 0; durations engine "silero", voice "xenia", fallback None
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -B -m unittest tests.test_narrate_check tests.test_narrate`
Expected: `FAILED` (`unrecognized arguments: --check`)

- [ ] **Step 3: Implement the check and the command lines**

`load_script` raises `ScriptError([f"script {path}: {cause}"])` for today's causes and then for the first broken §3.2 rule, with the validator's cause text (keys quoted with `json.dumps(k, ensure_ascii=False)`). `check_script` runs, in order, each check stopping alone: `load_script`; the fit of the engine (`say` fits both; else it must be `FIRST_CHOICE[lang]`; `None` resolves to `FIRST_CHOICE[lang]`); `ru` with a speed other than `"1.0"`. Then for `ru` it raises `ScriptError(guard_lines(...))` when the list is not empty. It returns the scenes, the `Speech` and the engine name. Any other exception inside is `ScriptError([f"script {path}: {exc}"])`. `guard_lines` applies spec §4.4 rules 1 to 5 with the sentences of `split_sentences` on the written narration: rules 1, 2, 4 and 5 read `speech.spoken_sentence` of each sentence; rule 3 reads that sentence's written tokens with backticks removed. Each line lists its scenes in script order, each token once per scene in text order, and shows tokens and code points per decisions 3 to 5. `parse_args` accepts `--check` with one positional and no `--models`, `--fallback` or audio dir; without `--check`, `--engine` (`kokoro`, `silero`, `say`) and the audio dir are required, and `--models` is required for `kokoro` and `silero` (argparse error, exit 2). `main`: `--check` prints the engine alone and returns 0; a synthesis run calls `check_script` first, then builds `KokoroEngine`, `SileroEngine` or `SayEngine(speed, lang)`; a `ScriptError` prints its lines and returns 2. The docstring describes both command lines, the exit codes and the guard.

- [ ] **Step 4: Run them to verify they pass, with every narrate suite**

Run: `python3 -B -m unittest tests.test_narrate_check tests.test_narrate tests.test_narrate_sentences tests.test_film_contract tests.test_brainrot_contract`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/narrate.py skills/explain/tests/test_narrate_check.py skills/explain/tests/test_narrate.py
git commit -m "feat: explain: narrate.py --check resolves the engine from lang and guards Russian narration"
```

---

### Task 5: `narrate.sh` checks first and runs Silero

**Files:**
- Modify: `skills/explain/scripts/narrate.sh:2-23` (header), `:27-30` (usage), `:34` (no default engine), `:62` (engine names), `:80-92` (`run_say`, the `say` shortcut), `:94-97` (model files of the chosen engine), `:99-105` (the uv command of each engine), `:113-127` (the cause)
- Test: `skills/explain/tests/test_narrate.py`

**Interfaces:**
- Consumes: the `--check` command line and its exit codes (Task 4); `durations.json` with `voice` (Task 3).
- Produces (Task 7 calls it):

```text
narrate.sh <script.json> <audio-dir> [--engine kokoro|silero|say] [--speed <d.d>]
exit 0 audio written | 1 say failed too, python3 missing, or --check exit other than 0 and 2 | 2 usage, or --check exit 2
```

- [ ] **Step 1: Write the failing tests** (`ru_models()` writes `v5_3_ru.pt` with wrong bytes to `<ws>/models`; the `say` stays the real one or `FAKE_SAY`)

```text
test_silero_run_uses_the_pinned_uv_command: a ru script, only v5_3_ru.pt in models, FAKE_UV → uv log before "python3" == "run --python 3.12 --with torch==2.14.1 --with numpy==2.5.3"; after it "-W ignore::SyntaxWarning <narrate.py> --engine silero --models <ws>/models --speed 1.0 <script> <audio>"; first line "narration: FALLBACK say (model sha mismatch: v5_3_ru.pt)"; durations engine "say", voice "Milena"
test_silero_models_missing_falls_back: no model file → "narration: FALLBACK say (models missing: v5_3_ru.pt)"
test_silero_uv_not_found_falls_back: PATH of say, afinfo, python3 and sh → cause "uv not found"
test_uv_own_exit_2_still_falls_back: a ru script, a uv that prints two stderr lines and exits 2 → cause "uv run failed: no solution found"
test_engine_fail_line_is_the_cause: a uv that prints "narration: FAIL silero clip failed: one: boom" and exits 3 → cause "silero clip failed: one: boom"
test_kokoro_own_fail_line_is_the_cause: stub Kokoro with STUB_RATE=22050 (exit 1) → the cause starts "scene one: " and ends "is 22050 Hz (expected 24000)"
test_check_exit_2_passes_through: a ru script with "8080"; a ru script with --engine kokoro; an en script with --engine silero → exit 2, stdout is the check's line alone, no "FALLBACK", no audio dir
test_check_exit_1_is_exit_1_without_fallback: a python3 first on PATH that prints "boom" and exits 1 for --check → exit 1, "boom" in stdout, no "FALLBACK"
test_no_python3: PATH of an empty directory → stdout "narration: FAIL python3 not found", exit 1
test_engine_say_on_russian_uses_milena: --engine say on a ru script → voice log all "Milena", no "FALLBACK"
test_check_gets_the_speed: a ru script with --speed 1.2 → exit 2, "narration: FAIL lang ru narrates at speed 1.0 only"
test_bad_speed_is_usage_error (existing): the usage string names "[--engine kokoro|silero|say]"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -B -m unittest tests.test_narrate`
Expected: `FAILED`

- [ ] **Step 3: Implement the new flow**

After argument parsing: no `python3` on PATH → `narration: FAIL python3 not found`, exit 1. Then `python3 narrate.py --check [--engine <e>] --speed <d.d> <script>` with its stdout captured: exit 2 → print it, exit 2; another non-zero exit → print it, exit 1; a stdout that is not exactly `kokoro`, `silero` or `say` → `narration: FAIL narrate.py --check printed no engine`, exit 1 (decision 8). The engine is the printed one. `say` runs at once with no fallback label. Then the model files of that engine only (`kokoro-v1.0.onnx`, `voices-v1.0.bin`; or `v5_3_ru.pt`) → `models missing: <name>`; then `uv` → `uv not found`; then the pinned uv command of the engine (Kokoro's as at the base; Silero's per the Global Constraints, with `--engine silero --models "$models"`). Any non-zero exit falls back: the cause is the text after `narration: FAIL ` of the last such stdout line, else `uv run failed: <last stderr line>`, else `uv run failed: exit <rc>`. `run_say` loses its own `python3` check. The header lists the three engines, the `--check` step in place of the "only builtins" invariant, the Silero causes and the exit codes of spec §6.4.

- [ ] **Step 4: Run them to verify they pass**

Run: `python3 -B -m unittest tests.test_narrate tests.test_narrate_check`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/narrate.sh skills/explain/tests/test_narrate.py
git commit -m "feat: explain: narrate.sh runs narrate.py --check first and narrates Russian with Silero"
```

---

### Task 6: the Silero download, safe when two renders fetch at once

**Files:**
- Modify: `skills/explain/scripts/video-workspace.sh:5,15,24` (header), `:33-36,49` (usage and engine names), `:59` (Kokoro URL base stays, passed per call), `:105-126` (`fetch_model` and its calls)
- Test: `skills/explain/tests/test_video_workspace.py`

**Interfaces:**
- Consumes: nothing.
- Produces (Task 7 passes `--engine silero`):

```text
video-workspace.sh [--engine kokoro|silero|say]
fetch_model <name> <size> <sha256> <url> [recheck]
workspace: download v5_3_ru.pt (145 MB)
workspace: downloaded v5_3_ru.pt
```

- [ ] **Step 1: Write the failing tests** (a match uses a copy of the script with the pin replaced by the sha of the fake bytes, as `test_downloaded_line_after_each_model` does)

```text
test_silero_cost_line_url_and_part_file: --engine silero → "workspace: download v5_3_ru.pt (145 MB)" before the one curl; its URL is https://models.silero.ai/models/tts/ru/v5_3_ru.pt; its -o path matches <ws>/models/v5_3_ru.pt.<digits>.part
test_silero_checksum_mismatch_deletes_part_and_fails: last line "workspace: FAIL checksum v5_3_ru.pt expected f036…7a1c got <sha of WRONG_BYTES>"; models/ empty
test_silero_downloaded_line: pin replaced → "workspace: downloaded v5_3_ru.pt" right after the curl, then "workspace: ok <ws>"
test_silero_in_place_mismatch_is_fetched_again: models/v5_3_ru.pt with other bytes, pin replaced → one curl, ok, the file holds the fake bytes
test_silero_in_place_match_is_not_fetched: models/v5_3_ru.pt whose sha is the replaced pin → no curl, ok
test_kokoro_in_place_is_left_alone: kokoro-v1.0.onnx with any bytes in place → no curl for it
test_kokoro_fetch_has_its_own_part_file: --engine kokoro → the -o path of the first curl matches <ws>/models/kokoro-v1.0.onnx.<digits>.part
test_two_fetches_at_once_both_succeed: a run with --engine say first (npm ci done); then two --engine silero runs at once with a barrier curl that writes half its part, waits until the other curl has started, then writes the rest → both exit 0, models/ holds v5_3_ru.pt only (red with the shared <name>.part)
test_a_stopped_fetch_leaves_no_part: a curl that writes half its part and sleeps; TERM to the process group once the part exists → exit non-zero, no "*.part" in models/
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -B -m unittest tests.test_video_workspace`
Expected: `FAILED` (`usage` on `--engine silero`)

- [ ] **Step 3: Implement the fetch**

`fetch_model` takes the URL as its fourth argument; the Kokoro calls pass `$model_base/<name>`. A file in place returns at once, except with `recheck`, where it is hashed and fetched again when it does not match. Each download goes to `$models/<name>.$$.part`. While it runs, a trap on EXIT removes that part file, and a trap on HUP, INT and TERM exits 1 (so the EXIT trap runs). Both traps are cleared once the file has been moved into place by `mv`. `--engine silero` calls `fetch_model v5_3_ru.pt "145 MB" <sha> <url> recheck`. The header lists the three engines, the Silero file under `<ws>/models` and the cost line.

- [ ] **Step 4: Run them to verify they pass**

Run: the Step 2 command. Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/video-workspace.sh skills/explain/tests/test_video_workspace.py
git commit -m "feat: explain: the workspace fetches the pinned Silero model with a part file per fetch"
```

---

### Task 7: `render.sh` takes the engine from `--check` and names the voice

**Files:**
- Modify: `skills/explain/scripts/render.sh:5,28,36,122-125` (header), `:161-164` (usage), `:167` (`engine=""`), `:184` (names), `:276-287` (`narrator_text`), `:293-318` (`stage_script`: the check after `:309`), `:413-438` (`stage_narration`: read `voice`), `:582-593` (`stage_transcript`)
- Test: `skills/explain/tests/test_render.py`, `skills/explain/tests/test_render_film.py`

**Interfaces:**
- Consumes: the `--check` command line (Task 4); `narrate.sh --engine kokoro|silero|say` (Task 5); `video-workspace.sh --engine silero` (Task 6); `durations.json` `voice` (Task 3).
- Produces (Task 9 quotes these lines):

```text
render.sh <output-dir> [--engine kokoro|silero|say]
narrator_text <used> <voice> <fallback>
script: FAIL <first "narration: FAIL " line of --check, prefix removed | first_cause of its stdout>
script: FAIL narrate.py --check printed no engine
```

Narrator rows: `kokoro`/`af_heart` → `kokoro (af_heart)`; `say`/`say-default` → `say`, or `say (fallback: <cause>)`; `silero`/`xenia` → `silero (xenia)`; `say`/`Milena` → `say (Milena)`, or `say (Milena, fallback: <cause>)`.

Harness: `RUN_FAKES` gains `skill/video/narrate.py`: it logs `["check", *argv]` to `calls.log`; with `FAKE_CHECK_OUT` set it prints that text, else `FAKE_CHECK_ENGINE`, else the `--engine` value, else `say`; it exits `FAKE_CHECK_EXIT` (default 0). The fake `narrate.sh` logs `["narrate", *argv]` and the fake `video-workspace.sh` logs `["workspace", *argv]`. Every fake `narrate.sh` (`test_render.py:265`, `:276`, `:472`) writes `{"engine": "say", "voice": "say-default"}`. `RunHarness.start(fmt="brainrot", engine="say", **env)` passes no `--engine` for `engine=None`. `SCENE_RUN_FAKES` inherits them. The `narrator_text` test helper (`:180-188`) takes three arguments. `stage_script_format` (`:854-867`) sets `engine=""` and echoes `engine=$engine`. `StageOneCase.render(engine="say")`.

- [ ] **Step 1: Write the failing tests**

```text
NarratorTextCase  test_rows_of_each_voice: the six rows above; the three English rows as at the base
StageFunctionCase test_narration_failure_names_the_engine_given: setup engine=silero, a narrate.sh that prints "narration: FAIL boom" and exits 1 → stdout "narration (silero): FAIL boom"
StageFunctionCase test_durations_without_voice_cannot_be_read: durations {"engine": "say"} → "narration (say): FAIL cannot read <out>/audio/durations.json"
RunHarness case   test_a_check_fail_line_loses_its_prefix: FAKE_CHECK_OUT "narration: FAIL unspoken text: s1: \"JSON\" (add to pronounce)", FAKE_CHECK_EXIT 2 → stage lines ["script: FAIL unspoken text: s1: \"JSON\" (add to pronounce)"], the stdout indented below, tool_calls("workspace") == []
RunHarness case   test_a_check_without_a_fail_line_gives_its_first_cause: FAKE_CHECK_OUT "boom", FAKE_CHECK_EXIT 1 → ["script: FAIL boom"], no workspace call
RunHarness case   test_a_check_that_prints_no_engine_fails: FAKE_CHECK_OUT "festival" (and "" ) with exit 0 → ["script: FAIL narrate.py --check printed no engine"], no workspace call
SceneRunCase      test_a_film_run_without_engine_passes_the_checked_engine: start("film", engine=None, FAKE_CHECK_ENGINE="silero") → the check got no --engine; workspace and narrate each got "--engine silero"
BrainrotRouteCase test_stage_script_reads_the_format_from_the_script (extended): each of the three runs also prints "engine=kokoro"
StageOneCase      test_an_unspoken_token_fails_at_the_script_stage: the film template with lang "ru" (real tools) → one stage line, starting "script: FAIL unspoken text: "; no audio dir
StageOneCase      test_kokoro_on_a_russian_film_fails_at_the_script_stage: the same script with --engine kokoro → ["script: FAIL engine kokoro cannot narrate lang ru"] alone (the engine check stops before the guard); no workspace dir
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -B -m unittest tests.test_render tests.test_render_film`
Expected: `FAILED`

- [ ] **Step 3: Implement**

`engine` starts empty; `--engine` accepts `kokoro`, `silero` or `say`. In `stage_script`, right after `build-timeline.mjs --check`, run `python3 "$video/narrate.py" --check ${engine:+--engine "$engine"} "$script"` with stdout captured and stderr left alone (decision 9). A non-zero exit prints `script: FAIL <cause>` (the first stdout line that starts `narration: FAIL `, without that prefix, else `first_cause` of stdout), then stdout indented by two spaces, and exits 1. Exit 0 with stdout exactly `kokoro`, `silero` or `say` sets `engine`; anything else fails with `script: FAIL narrate.py --check printed no engine`. `stage_narration` also reads `voice` from `durations.json` (a missing key is the existing `cannot read` line) into a global `voice`. `narrator_text` builds the rows above, and `stage_transcript` passes `"$used" "$voice" "$fallback"`. The header says the engine comes from `lang` through `narrate.py --check` unless `--engine` is given, and lists the Narrator rows.

- [ ] **Step 4: Run them to verify they pass**

Run: `python3 -B -m unittest tests.test_render tests.test_render_film`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/render.sh skills/explain/tests/test_render.py skills/explain/tests/test_render_film.py
git commit -m "feat: explain: render.sh takes the engine from narrate.py --check and names the voice"
```

---

### Task 8: `<html lang>` of the transcript and the Russian film contract

**Files:**
- Modify: `skills/explain/templates/video.html:2` (`<html lang="{{lang}}">`), `:11` (the page markers name `lang`), `skills/explain/video/transcript.py:250-270` (`render_page`)
- Test: `skills/explain/tests/test_transcript.py`, `skills/explain/tests/test_film_contract.py`

**Interfaces:**
- Consumes: the validator rules (Task 1), `Speech` weights (Task 2), `SayEngine` with Milena (Task 3), the guard of a synthesis run (Task 4).
- Produces: the marker `lang`, filled with the script's `lang` (default `en`).

- [ ] **Step 1: Write the failing tests**

```text
test_transcript.py   test_html_lang_follows_the_script: lang "ru" → '<html lang="ru">'; lang "en" and no lang → '<html lang="en">'
test_film_contract.py RussianFilmContract (film_script() with lang "ru", pronounce {"404": "четыреста четыре"}, Cyrillic narrations, one sentence "Код 404 готов."; --check, narrate.py --engine say, build mode "say"):
  test_fixture_is_a_valid_film_script: --check exit 0, no output
  test_narrate_then_build_exit_zero: narrate exit 0; build exit 0; durations voice "Milena"
  test_word_texts_are_the_written_tokens: the timeline's words of each scene == its narration.split()
  test_a_mapped_token_weighs_its_spoken_form: in that sentence's words.json, the 404 width / the sentence span == 16/27 within 1e-5 (weights 3, 16, 8 written out in the test; 3/14 with the written length)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -B -m unittest tests.test_transcript tests.test_film_contract`
Expected: `FAILED` (`lang="en"` on a Russian script; the 3/14 width)

- [ ] **Step 3: Implement the marker**

`render_page` adds `"lang": esc(script.get("lang", "en"))`; the template's line 2 uses the marker and its comment lists it with the page markers. Nothing else changes: the transcript of a film, a brainrot short and each lesson clip all come from `render_page`.

- [ ] **Step 4: Run them to verify they pass**

Run: the Step 2 command. Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add skills/explain/templates/video.html skills/explain/video/transcript.py skills/explain/tests/test_transcript.py skills/explain/tests/test_film_contract.py
git commit -m "feat: explain: the transcript carries the script's lang; a Russian film contract"
```

---

### Task 9: `SKILL.md`, the rung files and `README.md`

**Files:**
- Modify: `skills/explain/SKILL.md:68`, `:69-70`, `:71-72`, `:87`, `:130`, `:134`; `skills/explain/rungs/video.md:14-15`, `:44-56` (key table), `:71-73`, "Text on the stage" (`:303`), `:111-118`, `:380`, "The FAIL lines" table (`:416-422`), "First-run costs" `:483-494`, "Narration fallback" `:496-502`, "Handoff" `:560-565`, "Output directory" `:576`, "Pinned versions and environment" `:580-595`; `skills/explain/rungs/lesson.md:12`, `:32-33`, `:44`, `:84`, "The page" (`:98`), `:307-308`; `skills/explain/rungs/page.md:37`; `skills/explain/rungs/sheet.md:25`; `README.md:45-53`
- Test: `skills/explain/tests/test_render.py:826-841`, `skills/explain/tests/test_rung_drift.py` (`PRINTED` `:104`, `REQUIRED` `:193`, `SkillMdCase` `:767-778`), `skills/explain/tests/test_lesson_prompts.py`

**Interfaces:**
- Consumes: the guard and engine lines of `narrate.py` (Task 4) and the prefix strip of `render.sh` (Task 7), as `PRINTED` evidence; the behaviour of Tasks 3, 5 and 6, as prose.
- Produces: these exact sentences (the tests compare text with runs of whitespace collapsed):

```text
SKILL.md:68      The video rung is English or Russian.
SKILL.md:69-70   Only `--as brainrot` selects it. The brainrot rung is English only.
SKILL.md:71-72   Only `--as lesson` selects it. The lesson rung is English or Russian.
video.md:14-15   The video rung is English or Russian. A Russian film has `"lang": "ru"` in `script.json`. If the user asks for another language, print the rung line. Say that the video rung is English or Russian. Stop. Offer `page`.
lesson.md:32-33  The lesson rung is English or Russian. A Russian lesson has `<html lang="ru">` on its page and `"lang": "ru"` in the `script.json` of each clip. If the user asks for another language, print the rung line. Say that the lesson rung is English or Russian. Stop. Offer `page`.
page.md, sheet.md "Fill the template", lesson.md "The page":
                 Set the `lang` attribute of `<html>` to the language of the artifact: `en` or `ru`.
```

`video.md` quotes in its FAIL table, each with a `PRINTED` entry and in `REQUIRED`:

```text
script: FAIL unspoken text: <scene>: "<t>", … (add to pronounce)
script: FAIL abbreviation: <scene>: "<t>", … (write the words out, as «то есть»)
script: FAIL no letter: <scene> sentence <k>, …
script: FAIL too long: <scene> sentence <k> (<n> characters); … (max 900)
script: FAIL engine <e> cannot narrate lang <l>
```

- [ ] **Step 1: Write the failing tests**

```text
test_render.py      test_brainrot_stays_forced_only_and_english_only: SKILL.md holds "Only `--as brainrot` selects it. The brainrot rung is English only." and not "like the video rung"; the rung file's sentence as at the base
test_rung_drift.py  test_skill_md_routes_the_lesson_rung: the pinned sentence becomes "... Only `--as lesson` selects it. The lesson rung is English or Russian."
test_rung_drift.py  test_skill_md_states_the_video_languages: SKILL.md holds "builds a narrated mp4. The video rung is English or Russian."
test_rung_drift.py  test_skill_md_points_non_english_prose_to_convention_7: convention 7 holds "only the structural rules of the STE profile" and "`<code>`"; convention 1 and Build step 1 each name "convention 7"
test_rung_drift.py  test_video_md_states_its_two_languages: section 1 holds the video.md:14-15 sentences
test_rung_drift.py  test_page_and_sheet_set_html_lang: "Fill the template" of page.md and of sheet.md each hold the lang sentence
test_rung_drift.py  PRINTED and REQUIRED gain the five lines; existing tests prove each is quoted, matches its sample and has code evidence (the cause text in video/narrate.py, the "narration: FAIL " strip in scripts/render.sh)
test_lesson_prompts.py test_lesson_md_states_its_two_languages: section 1 holds the lesson.md:32-33 sentences; lines 12 and 44 name "convention 7"
test_lesson_prompts.py test_the_lesson_page_sets_html_lang: "The page" holds the lang sentence
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -B -m unittest tests.test_render.BrainrotRouteCase tests.test_rung_drift tests.test_lesson_prompts`
Expected: `FAILED`

- [ ] **Step 3: Write the prose**

`SKILL.md`: the three router sentences above. Convention 7 becomes spec §5.2: English unless the user asks for another language. A non-English artifact applies only the structural rules of the STE profile (sentence length, paragraph length, active voice, one instruction in each sentence); the vocabulary and the substitution table do not apply. Each English term and code name goes in `<code>` (backticks in a video script), because `ste_lint.py` skips code and still reports a bare English word. Convention 1 and Build step 1 each point to convention 7 for a non-English artifact. `video.md`, per spec §5.3:
- the language sentences above;
- `lang` and `pronounce` rows in the key table (a key is one token with no whitespace and no final `.`, `?` or `!`; every Latin term, number and acronym needs an entry; abbreviations are written out; `+` before a vowel fixes stress, in values only; prefer Russian words to code names);
- the STE line points to convention 7 for a Russian film, and the number line says to write a number in words or map its digits;
- "Text on the stage": the labels are in the artifact's language, and code names and source lines stay as written;
- the length list gets Silero at about 2.3 to 2.9 words a second and a safe total of about 270 words for the longest Russian film;
- `:380`: the engine follows `lang`, and `--engine say` gives `Milena` for a Russian film;
- the five FAIL rows;
- the shared sections: `First-run costs` (the `Silero` model, 145 MB, only for a script in Russian; `torch`, 127 MB, at the first `Silero` narration), `Narration fallback` (`silero (xenia)`, `say (Milena)`, `say (Milena, fallback: <cause>)`), `Handoff` (the two Russian narrators), `Output directory` (`kokoro`, `silero` or `say` as `<engine>`), `Pinned versions and environment` (the uv pins, the URL, the sha, `xenia` at 48 kHz, the licence line of decision 13).

`lesson.md`:
- line 12 and line 44 point to convention 7;
- the language sentences above;
- the lang sentence in "The page";
- after the usual clip length: a Russian clip of 20 to 40 s holds approximately 45 to 90 words;
- `:307-308` becomes "the first narration of an engine resolves its Python packages (`torch` for `Silero`)".

`page.md` and `sheet.md`: the lang sentence as a step of "Fill the template". `README.md`: the `Silero` model (145 MB) and `torch` (127 MB) in the cost paragraph; the narrator paragraph names Kokoro `af_heart` for English, Silero `xenia` for Russian, and the `say` fallback (`Milena` for Russian). Lint each edited rung and `SKILL.md`, and fix until clean.

- [ ] **Step 4: Run them to verify they pass, with the lint cases**

Run: `python3 -B -m unittest tests.test_render.BrainrotRouteCase tests.test_rung_drift tests.test_lesson_prompts tests.test_page_template tests.test_sheet_template`
Expected: `OK` (the lint cases print `0 errors, 0 warnings`)

- [ ] **Step 5: Commit**

```bash
git add skills/explain/SKILL.md skills/explain/rungs/video.md skills/explain/rungs/lesson.md skills/explain/rungs/page.md skills/explain/rungs/sheet.md README.md skills/explain/tests/test_render.py skills/explain/tests/test_rung_drift.py skills/explain/tests/test_lesson_prompts.py
git commit -m "docs: explain: films and lessons in Russian, convention 7, the Silero notes"
```

---

### Task 10: full suite, English regression renders and the live Russian acceptance

Run by the controller session, not a subagent: it ends with the user's acceptance. A reviewer or subagent that reads stills reads at most 4 images.

**Files:**
- Create: `docs/superpowers/spikes/2026-10-06-explain-russian-live-run.md`

**Interfaces:**
- Consumes: every earlier task.
- Produces: the live-run note (commands, the stage lines of each render, the Narrator rows, the user's verdict).

- [ ] **Step 1: Run the full non-gated suite**

Run: `cd skills/explain && python3 -B -m unittest discover -s tests > /tmp/ru-full.log 2>&1; tail -3 /tmp/ru-full.log`
Expected: `OK (skipped=45)`, with `Ran` above 813.

- [ ] **Step 2: Run the English regression renders**

Run: `export EXPLAIN_VIDEO_WORKSPACE=/Users/valukin/karpathy-wt/russian-workspace; EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film tests.test_lesson_e2e > /tmp/ru-e2e.log 2>&1; tail -3 /tmp/ru-e2e.log`
Expected: `OK`. The first run sets up the workspace and prints its costs.

- [ ] **Step 3: Render the Russian film**

With the same workspace, make `/explain ~/work/inavcalculator/src/main/java/ru/aton/esb/microservices/inavcalculator/web/ImportController.java --as video`, asked in Russian, following `SKILL.md` and `rungs/video.md`. Run `render.sh <output-dir>` with no `--engine`. Expected: eleven `ok` lines, no `narration: FALLBACK` line, `narration (silero): ok`, the Narrator row `silero (xenia)`, `<html lang="ru">` in `index.html`.

- [ ] **Step 4: Render the Russian lesson**

Make `/explain skills/explain/video/narrate.py --as lesson`, asked in Russian, with two clips, following `rungs/lesson.md` and its gates. Render the first clip alone until its `narration (silero): ok` line, then the second. Expected: both renders pass. The page and both clip transcripts hold `lang="ru"`, and `verify.sh <output-dir>/index.html` exits 0.

- [ ] **Step 5: The user's acceptance**

Give the user both output paths (`open` each when running for them directly) and ask them to watch both. Record the commands, the stage lines, the Narrator rows, the timings and the user's verdict in the live-run note. A rejection becomes a fix task before this one closes.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/spikes/2026-10-06-explain-russian-live-run.md
git commit -m "docs: explain: Russian film and lesson live run"
```
