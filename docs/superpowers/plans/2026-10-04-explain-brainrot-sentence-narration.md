# Wave `sentence-narration` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `narrate.sh --speed` and, for a `brainrot` script, per-sentence synthesis that writes `audio/<id>.<engine>.words.json` with exact sentence joins; an explainer script narrates byte-for-byte as today.

**Architecture:** `narrate.py` gains a validated `--speed` that both engines and the sidecar use, and reads `format` from `script.json`. For `brainrot` it splits each narration into sentences, synthesises each sentence through the existing engine `synth()` into a scratch WAV, joins the clips with the stdlib `wave` module (0.15 s of silence between clips), and derives word times from the join positions. `narrate.sh` validates and forwards `--speed` on every path, the say fallback included.

**Tech Stack:** Python 3 stdlib (`wave`, `json`, `argparse`), bash, macOS `say` and `afinfo`; Kokoro through the existing pinned `uv run` line (no change).

**Spec:** `docs/superpowers/specs/2026-10-04-explain-brainrot-design.md` §5.1, §5.2 (map: `docs/superpowers/waves/2026-10-04-explain-brainrot.yaml`, wave `sentence-narration`).

## Global Constraints

- Kokoro voice `af_heart`; brainrot speed `1.2`; the say fallback at speed 1.2 uses `-r 210` (spec §5.1).
- Join silence between sentence clips: `0.15 s` (spec §5.2).
- Sentence end: `.`, `?` or `!` followed by whitespace or the end of the text, never inside backticks (spec §5.2).
- Word weight: character length of the word, plus `2` for a word that ends in `,`, `;`, `:` or ends its sentence (spec §5.2).
- `words.json` path `audio/<id>.<engine>.words.json`, `<engine>` = the engine that made the clip (so a fallback writes `say`); written only for `format: "brainrot"` (spec §5.2).
- Explainer (format absent or `explainer`) at the default speed: WAV, sidecar bytes, `durations.json`, stdout lines and exit codes identical to today. Every existing test in `tests/test_narrate.py` passes without edits to its assertions.
- The say path stays stdlib only; no new package, no change to the pinned `uv run` line.
- Commits: `git -c user.name=Vladislav -c user.email=valukin@Vladislavs-MacBook-Pro.local commit`, message ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Run all tests from `skills/explain`: `python3 -B -m unittest tests.test_narrate`.

## Current-code facts

- `video/narrate.py`: `SPEED = "1.0"` is a module constant used by `sidecar_text()` and `KokoroEngine.synth()`; `synth_say()` runs `say --file-format=WAVE --data-format=LEI16@22050 -o <wav> -f <file>` with no `-r`. `narrate()` reuses a clip when the WAV exists and the sidecar bytes equal `sidecar_text()`; it unlinks the sidecar before synthesis and writes it after the `afinfo` rate check. `load_scenes()` exits 2 on an unreadable script. Exit 3 = Kokoro cannot run (narrate.sh turns it into the say fallback).
- `scripts/narrate.sh`: argument loop accepts only `--engine`; `run_say()` execs `narrate.py --engine say [--fallback <cause>]`; the Kokoro path is one `uv run … python3 narrate.py --engine kokoro --models …` line; only builtins run before the uv check.
- `tests/test_narrate.py`: real `say` + `afinfo`; Kokoro and soundfile are stub modules on `PYTHONPATH` (`STUB_KOKORO` returns 0.5 s of silence per `create()` call and asserts `speed == 1.0`); `FAKE_SAY` logs the `-f` text and ignores other flags; `FAKE_UV` runs the python3 command after its arguments.

## Review Focus

1. **Narration without a final terminator** ("Run the check") — expected: the remainder is the last sentence, and its words get times. Test in Task 2.
2. **Line breaks and repeated spaces** in the narration ("One.\n\nTwo  words.") — expected: two sentences; the word list equals `narration.split()`. Test in Task 2.
3. **An odd number of backticks** ("Run `verify.sh now. Then stop.") — expected: backtick parity is ignored for that narration, so the split still happens; no single run-on sentence. Test in Task 2.
4. **A say clip with extra WAVE chunks** (macOS `say` writes an `FLLR` chunk) read by the joiner — expected: the join works and the joined WAV passes the 22050 Hz `afinfo` check. Covered by the real-say test in Task 3.
5. **A deleted or hand-edited `words.json` next to a current WAV** — expected: the scene re-synthesises; a stale `words.json` never ships with a reused WAV. Test in Task 4.

---

### Task 1: `--speed` on narrate.py and narrate.sh

**Files:**
- Modify: `skills/explain/video/narrate.py` (`SPEED` constant, `sidecar_text`, `sidecar_matches`, `synth_say`, both engines, `parse_args`, `main`)
- Modify: `skills/explain/scripts/narrate.sh` (argument loop, `run_say`, the `uv run` line, usage line, header)
- Test: `skills/explain/tests/test_narrate.py`

**Interfaces:**
- Produces:
  - CLI: `narrate.py --engine say|kokoro [--models <dir>] [--fallback "<cause>"] [--speed <d.d>] <script.json> <audio-dir>`
  - CLI: `narrate.sh <script.json> <audio-dir> [--engine kokoro|say] [--speed <d.d>]`
  - `--speed` value: exactly one digit, a full stop, one digit (`1.0`, `1.2`), in `0.5`–`2.0`; default `1.0`. Anything else: narrate.sh prints its usage line and exits 2 before any engine runs; narrate.py exits 2 through `argparse`.
  - `parse_speed(value: str) -> str` — the argparse `type`; returns the string unchanged.
  - `say_rate_args(speed: str) -> list[str]` — `[]` for `"1.0"`, else `["-r", str(round(175 * float(speed)))]` (175 wpm is the macOS default rate; `1.2` → `["-r", "210"]`).
  - `SayEngine(speed: str)`, `KokoroEngine(models: str, speed: str)`; each engine has a `speed` attribute; `sidecar_text(engine, text)` writes `speed=<engine.speed>`.

- [ ] **Step 1: Extend the test doubles.** `STUB_KOKORO` asserts `speed == float(os.environ.get("STUB_SPEED", "1.0"))` and, when `STUB_LOG` is set, appends each `create()` text plus `\n` to that file. `FAKE_SAY` appends the value after `-r` (or `-` when absent) plus `\n` to `$FAKE_SAY_RATE_LOG` when set, and passes `-r <value>` to the real say.

- [ ] **Step 2: Write the failing tests**

```python
def test_speed_is_recorded_in_sidecar(self):           # say, --speed 1.2: sidecar == "engine=say\nvoice=say-default\nspeed=1.2\nHello there."
def test_say_rate_follows_speed(self):                  # FAKE_SAY_RATE_LOG holds "210" for --speed 1.2 and "-" for no --speed
def test_kokoro_gets_speed(self):                       # stub kokoro via FAKE_UV, STUB_SPEED=1.2, --speed 1.2: exit 0, sidecar line "speed=1.2"
def test_changed_speed_resynthesizes(self):             # run at 1.0, then 1.2: second run's line for scene one ends "(synthesized)"
def test_fallback_keeps_speed(self):                    # models missing, --speed 1.2: FALLBACK line, say rate log "210", sidecar "speed=1.2"
def test_bad_speed_is_usage_error(self):                # narrate.sh with "1.25", "2.5", "0.4", "fast", "" (subTest each): exit 2, no audio dir
def test_python_bad_speed_exit_2(self):                 # narrate.py --speed 3.0: exit 2
```

- [ ] **Step 3: Run to see them fail**

Run: `python3 -B -m unittest tests.test_narrate`
Expected: the 7 new tests FAIL or ERROR; every existing test passes.

- [ ] **Step 4: Implement.** Replace the `SPEED` constant with the engine attribute; `synth_say(text, wav, speed)` inserts `say_rate_args(speed)` before `-o`; Kokoro passes `speed=float(self.speed)`. narrate.sh validates the value with a `case` pattern `[0-9].[0-9]` plus an integer range check on the digits (`5`–`20`), using builtins only, and appends `--speed <value>` to both `exec python3 … narrate.py` lines in `run_say` and to the `uv run … narrate.py` line.

- [ ] **Step 5: Run the suite**

Run: `python3 -B -m unittest tests.test_narrate`
Expected: `OK`.

- [ ] **Step 6: Commit** — `feat: explain: narrate --speed for both engines and the say fallback`

---

### Task 2: Sentence splitter and word timings (pure functions)

**Files:**
- Modify: `skills/explain/video/narrate.py` (two new functions)
- Test: `skills/explain/tests/test_narrate.py` (new class `SentenceText`, which imports `narrate.py` through `importlib.util.spec_from_file_location`; the module has no import-time side effects)

**Interfaces:**
- Produces:
  - `split_sentences(text: str) -> list[str]` — the sentences, stripped, in order, none empty. A sentence ends after `.`, `?` or `!` when the next character is whitespace or the end of the text and the terminator is outside backticks. When the text holds an odd number of backticks, backticks are ignored for splitting. Text after the last terminator is the last sentence. Invariant: `" ".join(s.split() for each sentence)` word list equals `text.split()`.
  - `word_timings(sentences: list[str], spans: list[tuple[float, float]]) -> list[dict]` — `[{ "text": w, "from": s, "to": s }]` for every word of every sentence in order (`w` = the written word verbatim, backticks and punctuation included). Inside a span, word `i` gets `[from + span × before/total, from + span × (before + weight)/total]`, where weight = `len(w.replace("`", ""))` plus 2 when `w` ends in `,` `;` `:` or is the sentence's last word. The first word of sentence k starts exactly at `spans[k][0]` and the last word ends exactly at `spans[k][1]` (the same float, not a recomputed one).

- [ ] **Step 1: Write the failing tests**

```python
def test_split_basic(self):              # "One. Two? Three!" -> ["One.", "Two?", "Three!"]
def test_split_keeps_code_names(self):   # "Run `verify.sh` now. Then render.sh runs." -> 2 sentences, first == "Run `verify.sh` now."
def test_split_dot_inside_backticks_with_space(self):  # "Use `a. b` here. Done." -> ["Use `a. b` here.", "Done."]
def test_split_no_final_terminator(self):  # "Run the check" -> ["Run the check"]          (Review Focus 1)
def test_split_whitespace(self):           # "One.\n\nTwo  words." -> ["One.", "Two  words."]; words == text.split()  (Review Focus 2)
def test_split_odd_backticks(self):        # "Run `verify.sh now. Then stop." -> ["Run `verify.sh now.", "Then stop."]  (Review Focus 3)
def test_word_weights(self):               # ["Hi, you."] over (0.0, 1.0): weights 5 and 6 -> Hi, = [0, 5/11], you. = [5/11, 1.0]
def test_words_tile_each_span_exactly(self):  # two sentences, spans (0.0, 0.5), (0.65, 1.15): first word from == 0.65 exactly, last to == 1.15 exactly, no gap inside a span
def test_backticks_do_not_weigh(self):     # "`ab` c." -> `ab` weight 2, "c." weight 2+2
```

- [ ] **Step 2: Run to see them fail** — Run: `python3 -B -m unittest tests.test_narrate.SentenceText`. Expected: ERROR, `module 'narrate' has no attribute 'split_sentences'`.

- [ ] **Step 3: Implement** both functions in `narrate.py`. The splitter is a single left-to-right scan that tracks backtick parity (skipped when the backtick count is odd).

- [ ] **Step 4: Run the suite** — Run: `python3 -B -m unittest tests.test_narrate`. Expected: `OK`.

- [ ] **Step 5: Commit** — `feat: explain: narration sentence splitter and word timings`

---

### Task 3: Per-sentence synthesis and `words.json` for brainrot

**Files:**
- Modify: `skills/explain/video/narrate.py` (`load_scenes` → `load_script`, `narrate`, new `join_clips`, `synth_sentences`, `sidecar_text`)
- Test: `skills/explain/tests/test_narrate.py` (new class `Sentences`)

**Interfaces:**
- Consumes: `split_sentences`, `word_timings` (Task 2); `engine.synth(text, wav)`, `engine.speed` (Task 1).
- Produces (wave `brainrot-timeline` consumes this file; schema from spec §5.2, verbatim):

```json
{ "sentences": [{ "from": 0.0, "to": 0.5 }], "words": [{ "text": "Hello", "from": 0.0, "to": 0.21 }] }
```

  - Path: `<audio-dir>/<id>.<engine>.words.json`, UTF-8, `indent=2`, trailing newline. Times are seconds from the clip start, `round(x, 6)`.
  - `sentences[k] = { from: start_frame_k / rate, to: end_frame_k / rate }`, where the frames are the exact join positions in the written WAV.
  - `words` = every word of the narration in order, `text` verbatim (backticks kept; build-timeline strips them for captions, spec §5.4). `[w["text"] for w in words] == narration.split()`.
  - The first word of sentence k has `from == sentences[k].from`; the last word of the last sentence has `to == sentences[-1].to` ≤ the clip length from `afinfo`.
  - `load_script(path) -> tuple[str, list[dict]]` — `(format, scenes)`; `format` defaults to `"explainer"`; a value other than `explainer`/`brainrot` prints `narration: FAIL script <path>: format must be explainer or brainrot` and exits 2.
  - `join_clips(clips: list[Path], out: Path, gap_s: float) -> tuple[int, list[tuple[int, int]]]` — writes one 16-bit mono WAV; returns `(rate, [(start_frame, end_frame), …])`; the gap is `round(gap_s × rate)` zero frames between clips (none before the first or after the last); clips with a differing rate, width or channel count raise `NarrationError` naming the clip.
  - `synth_sentences(engine, text: str, wav: Path) -> dict` — synthesises each sentence (`engine.synth(sentence, scratch_wav)`; `synth()` already applies `spoken()`), joins, returns the words payload.
  - Brainrot sidecar: `engine=…\nvoice=…\nspeed=…\nmode=sentences\n<text>`; the explainer sidecar has no `mode` line (byte-identical to today).
  - stdout per scene: unchanged format `narration: <id> <engine> <s> s (synthesized|reused)`.

- [ ] **Step 1: Write the failing tests** (Kokoro stub through `narrate.py --engine kokoro` directly, as `KokoroDirect` does; brainrot scripts are the template with `"format": "brainrot"`)

```python
def test_kokoro_per_sentence_times_are_exact(self):   # "Hello there. A second line.": sentences == [{0.0, 0.5}, {0.65, 1.15}]; durations 1.15
def test_kokoro_called_once_per_sentence_spoken(self):  # STUB_LOG == "Run verify.sh now.\nThen stop.\n" for "Run `verify.sh` now. Then stop."
def test_words_match_narration(self):                 # [w["text"]] == narration.split(), backticks kept
def test_say_per_sentence_join_positions(self):       # real say: sentences[1].from - sentences[0].to == 0.15 within 1 frame; last word to <= afinfo seconds; afinfo rate 22050  (Review Focus 4)
def test_brainrot_sidecar_has_mode_line(self):        # sidecar == "engine=say\nvoice=say-default\nspeed=1.0\nmode=sentences\n" + text
def test_explainer_writes_no_words_json(self):        # template without format: no *.words.json; sidecar has no mode line
def test_mode_change_resynthesizes(self):             # explainer run, then same text as brainrot: "(synthesized)"
def test_unknown_format_exit_2(self):                 # "format": "tiktok": exit 2, stdout "narration: FAIL script <path>: format must be explainer or brainrot"
def test_fallback_writes_say_words(self):             # narrate.sh, brainrot, models missing: FALLBACK line, one.say.words.json exists, no one.kokoro.words.json
```

- [ ] **Step 2: Run to see them fail** — Run: `python3 -B -m unittest tests.test_narrate.Sentences`. Expected: FAIL (no `words.json`, single `create()` call).

- [ ] **Step 3: Implement.** `narrate()` takes `mode: str` (`"scene"` or `"sentences"`, from the format). The sentence path synthesises into a `tempfile.TemporaryDirectory`, joins into the final WAV path, and writes `words.json`, all before the existing rate check and sidecar write.

- [ ] **Step 4: Run the suite** — Run: `python3 -B -m unittest tests.test_narrate`. Expected: `OK`, with every pre-existing test unchanged.

- [ ] **Step 5: Commit** — `feat: explain: per-sentence brainrot narration with words.json`

---

### Task 4: Cache unit and failure hygiene for the sentence path

**Files:**
- Modify: `skills/explain/video/narrate.py` (`narrate` reuse condition and cleanup order)
- Test: `skills/explain/tests/test_narrate.py` (class `Sentences`)

**Interfaces:**
- Consumes: Task 3 file names and sidecar.
- Produces: the reuse rule for the sentence path. A brainrot clip is reused only when the WAV exists, the sidecar matches, and `words.json` exists, parses, and its word texts equal `narration.split()`. Otherwise the scene re-synthesises (decision: the WAV is re-made, never the words file alone, because sentence spans cannot be recovered from a joined WAV). Before synthesis, the sidecar and `words.json` are unlinked. On a failed sentence, the WAV and `words.json` are unlinked too, and the error is the engine's `failure()` as today (Kokoro: exit 3 → say fallback). Write order on success: WAV, `words.json`, rate check, then the sidecar last.

- [ ] **Step 1: Write the failing tests**

```python
def test_missing_words_json_resynthesizes(self):    # delete one.say.words.json; rerun: "(synthesized)", file present again   (Review Focus 5)
def test_stale_words_json_resynthesizes(self):      # overwrite words.json with another word list; rerun: "(synthesized)", word list == narration.split()
def test_reuse_keeps_wav_and_words(self):           # second unchanged run: "(reused)", WAV and words.json inode+mtime unchanged
def test_failed_sentence_leaves_nothing(self):      # Kokoro stub, "Fine. BOOM now.": exit 3; no two.kokoro.wav, .txt or .words.json
```

- [ ] **Step 2: Run to see them fail** — Run: `python3 -B -m unittest tests.test_narrate.Sentences`. Expected: the missing/stale cases print `(reused)` and FAIL.

- [ ] **Step 3: Implement** the reuse condition and the unlink and write order in `narrate()`.

- [ ] **Step 4: Run the suite** — Run: `python3 -B -m unittest tests.test_narrate`. Expected: `OK`.

- [ ] **Step 5: Wider check** — Run: `python3 -B -m unittest discover -s tests` (from `skills/explain`). Expected: `OK` (the E2E tests skip without `EXPLAIN_VIDEO_E2E=1`).

- [ ] **Step 6: Commit** — `fix: explain: brainrot narration reuses a clip only with a matching words.json`

---

## Self-review notes

- Spec §5.1: Task 1 covers speed, `-r 210` and the sidecar. The render.sh mapping from format to speed belongs to wave `brainrot-render`, not here.
- Spec §5.2: Task 2 covers the splitter and weights; Task 3 covers the per-sentence path, the exact joins, the schema and the say fallback; Task 4 covers cache safety.
- Spec gap (passed to wave `brainrot-timeline`): §5.2's schema carries no word-to-sentence index. This plan fixes the invariant that the first word of sentence k has `from == sentences[k].from` and that the words equal `narration.split()`, so build-timeline can map a cue to its first word by word offset without a second splitter.
