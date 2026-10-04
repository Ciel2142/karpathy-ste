# Explain brainrot — wave `brainrot-timeline` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `build-timeline.mjs` validates `format` against per-format limits and, for `brainrot`, builds lead/tail 6/12, exact cue frames and caption chunks from `words.json`; explainer validation and frames stay as today.

**Architecture:** One `FORMATS` limits table in `build-timeline.mjs` replaces the loose constants and feeds a per-format `SHAPES` table, the scene-count rule, the code rules and build mode. Build mode emits the format, canvas and time budgets at the top of the timeline. For `brainrot` only, it reads `audio/<id>.<engine>.words.json` next to `durations.json`, takes cue frames from sentence starts, and writes caption chunks per scene. The Remotion app and `render.sh` are not touched in this wave; wave `brainrot-render` consumes the output.

**Tech Stack:** Node 25 (stdlib only, ES modules), Python 3 `unittest` driving the tool through `subprocess`.

**Spec:** `docs/superpowers/specs/2026-10-04-explain-brainrot-design.md` (§3.3, §3.4, §5.2–§5.4, §7.1). Wave map: `docs/superpowers/waves/2026-10-04-explain-brainrot.yaml`.

## Global Constraints

- No npm dependency; `build-timeline.mjs` stays one stdlib-only file.
- `format` absent means `explainer`; every explainer FAIL line stays byte-identical to today.
- Brainrot FAIL lines that name a limit append `, brainrot` inside the parentheses: `(max 40, brainrot)`, `(needs 3 to 6, brainrot)`.
- Unknown `format`: `FAIL script: format must be explainer or brainrot`.
- FPS 30 for both formats. Rounding of seconds to frames is `Math.round` (half up for positive values).
- Brainrot values are the spec §3.4 starting values; the live-run wave tunes them later. Change them only in the `FORMATS` table.
- Commit with `git -c user.name=Vladislav -c user.email=valukin@Vladislavs-MacBook-Pro.local commit` and the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Test command for the wave: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline tests.test_video_timeline_brainrot`.

## Review Focus

1. A narration with a dotted code name in backticks (`` `verify.sh` ``, `render.sh`): the words.json token check must compare verbatim tokens, and the caption must drop only the backticks. Pinned in Task 4 and Task 5.
2. A Kokoro run that fell back to `say`: build mode must look up `<id>.say.words.json` (the engine argument), not the requested engine. Pinned in Task 4.
3. Double spaces or a newline inside the narration: the token split is `/\s+/`, the same as `wordCount`, so a words.json made from the same split matches. Pinned in Task 4.
4. Float noise between `sentences[j].from` and `words[k].from` (producer rounding): the sentence-start match uses a tolerance of 0.001 s, never `===`. Pinned in Task 4.
5. A last word that ends after the clip end (words.json from an older WAV): build fails instead of drawing a caption into the tail. Pinned in Task 4.

---

## File Structure

- Modify `skills/explain/video/build-timeline.mjs`: `FORMATS` table, `format` check, per-format shapes and rules, build-mode output, words.json reader, caption chunker. Header comment gains the brainrot inputs and outputs.
- Modify `skills/explain/tests/test_video_timeline.py`: one line only, the expected top-level key list in `test_timeline_top_level_shape` (Task 3). Every other existing case is unchanged.
- Create `skills/explain/tests/test_video_timeline_brainrot.py`: all brainrot cases. It imports `VideoCase`, `base_script`, `cite`, `APP_LINES` and `TOOL` from `test_video_timeline` (a sibling file keeps the old file under 800 lines).

## Interfaces produced by this wave (consumed by wave `brainrot-render`)

Top-level timeline keys, in this order, for both formats:

```json
{ "format": "explainer|brainrot", "fps": 30, "width": 1280, "height": 720, "totalFrames": 0,
  "maxSceneSeconds": 60, "maxTotalSeconds": 150, "engine": "say|kokoro", "scenes": [] }
```

Brainrot values: `width` 1080, `height` 1920, `maxSceneSeconds` 30, `maxTotalSeconds` 90. `render.sh` (wave brainrot-render) reads the two budgets from the timeline instead of its `MAX_SCENE_S` / `MAX_TOTAL_S` constants; until then it keeps its constants, which equal the explainer values.

Per scene, both formats: the existing keys (`id, component, props, from, durationInFrames, leadFrames, audioFrames, audio, cueFrames`) with `leadFrames` 15 (explainer) or 6 (brainrot) and `durationInFrames = leadFrames + audioFrames + tail` (tail 36 or 12). Brainrot scenes add one key:

```json
"captions": [ { "from": 6, "to": 21, "words": [ { "text": "The", "from": 6, "to": 10 } ] } ]
```

All caption frames are relative to the scene start: `frame(t) = leadFrames + Math.round(t × 30)` for a time `t` in seconds from the clip start. Explainer scenes carry no `captions` key.

words.json lookup and contract (consumed from wave `sentence-narration`, spec §5.2):

- Path: `path.join(path.dirname(<durations.json>), "<id>.<engine>.words.json")`, where `<engine>` is the build-mode engine argument (the engine actually used).
- Shape: `{ "sentences": [{ "from": s, "to": s }], "words": [{ "text": w, "from": s, "to": s }] }`, seconds from the clip start, numbers finite and `>= 0`, `from <= to` on every item, and on consecutive words `words[i].to <= words[i+1].from`.
- `words[i].text` equals the i-th token of `narration.split(/\s+/).filter(Boolean)` verbatim (backticks and punctuation kept). The sentence-narration plan must produce exactly this.

Brainrot build FAIL lines (prefix `FAIL scene <id>: `; `<file>` is the basename `<id>.<engine>.words.json`):

| Case | Cause text |
|---|---|
| file missing or unreadable | `cannot read <file>: <err.code>` |
| not JSON | `<file> is not valid JSON: <message>` |
| shape broken | `<file> has a bad shape at <where>` (`<where>` such as `words[3].to`, `sentences`) |
| word count differs | `<file> has <n> words, the narration has <m>` |
| token differs | `<file> word <i> is <q(text)>, the narration has <q(token)>` (`i` 0-based) |
| ends after the clip | `<file> ends at <t> s, after the clip end <s> s` (both as JavaScript `String(number)`; the check allows 0.001 s) |
| cue not at a sentence start | `cue <q(cue)> does not start a sentence in <file>` |

The 15-frame cue distance check applies to brainrot cue frames with today's text.

---

### Task 1: `FORMATS` table, `format` key, scene count and code rules

**Files:**
- Modify: `skills/explain/video/build-timeline.mjs:14-23` (constants), `:200-225` (`checkCode`), `:314-360` (`checkHeader`, `validate`)
- Create: `skills/explain/tests/test_video_timeline_brainrot.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces:

```js
const FORMATS = {
  explainer: { width: 1280, height: 720, minScenes: 3, maxScenes: 8, maxSceneSeconds: 60, maxTotalSeconds: 150,
    maxNarrationWords: 45, leadFrames: 15, tailFrames: 36, codeLines: 14, codeColumns: 72,
    bulletText: 36, beforeAfterLines: 10, beforeAfterLineChars: 36, beforeAfterHeading: 36,
    diagramLabel: 14, diagramSub: 24, titleTitle: 50, titleSubtitle: 80 },
  brainrot: { width: 1080, height: 1920, minScenes: 3, maxScenes: 6, maxSceneSeconds: 30, maxTotalSeconds: 90,
    maxNarrationWords: 45, leadFrames: 6, tailFrames: 12, codeLines: 14, codeColumns: 40,
    bulletText: 28, beforeAfterLines: 5, beforeAfterLineChars: 30, beforeAfterHeading: 30,
    diagramLabel: 12, diagramSub: 20, titleTitle: 30, titleSubtitle: 60 },
};
const formatOf = (script) => string            // "explainer" | "brainrot" | the bad raw value
const limitsFor = (format) => FORMATS[format] ?? FORMATS.explainer
const tagOf = (format) => string               // "" for explainer, ", brainrot" for brainrot
```

`validate(script, root)` keeps its signature; it reads the format once and passes `limits` and `tag` down to `checkScene` and `checkCode` (extra parameters). Node count 2–7, bullet count 2–4, edge label 10 and narration words 45 stay shared values.

- [ ] **Step 1: Write the failing tests** in the new file: a `brainrot_script()` helper (`base_script()` plus `"format": "brainrot"`; its fixture already fits every brainrot limit) and these cases:

```python
test_unknown_format_fails            # format "vertical" -> assertFails(..., "FAIL script: format must be explainer or brainrot")
test_explicit_explainer_format_passes  # format "explainer" -> exit 0, no stdout
test_brainrot_fixture_passes         # brainrot_script() -> exit 0, no stdout
test_brainrot_six_scenes_pass        # 6 scenes -> exit 0
test_brainrot_seven_scenes_fail      # 7 scenes -> "FAIL script: 7 scenes (needs 3 to 6, brainrot)"
test_brainrot_code_40_columns_pass   # a 40-column line in range -> exit 0
test_brainrot_code_41_columns_fail   # -> "FAIL scene code: line 3 is 41 columns (max 40, brainrot)"
test_brainrot_code_15_lines_fail     # -> "FAIL scene code: source range 1-15 is 15 lines (max 14, brainrot)"
test_brainrot_narration_46_words_fail  # -> "FAIL scene intro: narration is 46 words (max 45, brainrot)"
```

Write the 40/41-column fixture files with `self.write` in the test (a line of `"x" * 40` and `"x" * 41`).

- [ ] **Step 2: Run to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_brainrot -v`
Expected: FAIL; `test_unknown_format_fails` and the brainrot cases fail with `unexpected key "format"` in stdout.

- [ ] **Step 3: Implement** the table and helpers above. `checkHeader` accepts `format` as a known key and reports the unknown-format line when the value is not `"explainer"` or `"brainrot"` (any non-string included); validation then continues with explainer limits. The scene-count line, the narration-word line and the two code lines read `limits` and append `tag` inside the parentheses. Remove the replaced constants (`WIDTH`, `HEIGHT`, `LEAD_FRAMES`, `TAIL_FRAMES`, `MAX_NARRATION_WORDS`, `MAX_CODE_LINES`, `MAX_COLUMNS`); build mode reads the explainer row for now.

- [ ] **Step 4: Run both suites**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline tests.test_video_timeline_brainrot`
Expected: `OK`. The old suite passes unchanged, which proves the explainer lines are byte-identical.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/build-timeline.mjs skills/explain/tests/test_video_timeline_brainrot.py
git commit -m "feat: explain: format key and per-format limits table in build-timeline"
```

### Task 2: Per-format component prop limits

**Files:**
- Modify: `skills/explain/video/build-timeline.mjs:56-144` (`SHAPES`, `checkSpec`, `checkShape`), `checkScene`
- Test: `skills/explain/tests/test_video_timeline_brainrot.py`

**Interfaces:**
- Consumes: `FORMATS`, `limitsFor`, `tagOf` (Task 1).
- Produces: `const shapesFor = (limits) => SHAPES-shaped object`, built once per format at module load (`SHAPES_BY_FORMAT`). `checkSpec(value, spec, where, fail, tag)` and `checkShape(value, shape, where, fail, tag)` append `tag` to the `(max N)` and `(needs A to B)` texts. `has(SHAPES, …)` lookups use the format's shapes.

- [ ] **Step 1: Write the failing tests** (each pair: at the limit passes, one over fails):

```python
test_brainrot_bullet_28_chars_passes   # bullets[1].text "x"*28 -> exit 0
test_brainrot_bullet_29_chars_fails    # -> "FAIL scene intro: bullets[1].text is 29 chars (max 28, brainrot)"
test_brainrot_before_after_limits      # 5 lines x 30 chars, heading 30 -> exit 0
test_brainrot_before_after_over_limits # 6 lines, a 31-char line, a 31-char heading -> exactly these three lines:
    # "FAIL scene <id>: before.heading is 31 chars (max 30, brainrot)"
    # "FAIL scene <id>: before.lines has 6 items (needs 0 to 5, brainrot)"
    # "FAIL scene <id>: after.lines[0] is 31 chars (max 30, brainrot)"
test_brainrot_diagram_label_sub_limits # label 12, sub 20 -> exit 0; label 13, sub 21 -> two "(max 12, brainrot)" / "(max 20, brainrot)" lines
test_brainrot_title_limits             # title 30, subtitle 60 -> exit 0; 31 / 61 -> "(max 30, brainrot)" / "(max 60, brainrot)" lines
test_explainer_limits_unchanged_under_explicit_format  # format "explainer", 41-char bullet -> "... is 41 chars (max 36)" with no tag
```

Add a `before-after` and a `title` scene to the fixture inside the tests that need them (replacing scene `intro`; narration and cues as in the existing tests).

- [ ] **Step 2: Run to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_brainrot -v`
Expected: FAIL; the `*_fails` cases report the explainer maxima (36, 10, 14, 24, 50, 80) with no tag.

- [ ] **Step 3: Implement** `shapesFor(limits)` with the field mapping: `title.title` → `titleTitle`, `title.subtitle` → `titleSubtitle`, `bullets[].text` → `bulletText`, `nodes[].label` → `diagramLabel`, `nodes[].sub` → `diagramSub`, `before|after.heading` → `beforeAfterHeading`, `before|after.lines` → `arr(str(beforeAfterLineChars, true), 0, beforeAfterLines)`. All other specs keep today's values.

- [ ] **Step 4: Run both suites**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline tests.test_video_timeline_brainrot`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/build-timeline.mjs skills/explain/tests/test_video_timeline_brainrot.py
git commit -m "feat: explain: per-format component prop limits for brainrot"
```

### Task 3: Build-mode output per format (top-level keys, lead and tail)

**Files:**
- Modify: `skills/explain/video/build-timeline.mjs:364-473` (`buildScenes`, `main`)
- Modify: `skills/explain/tests/test_video_timeline.py:538` (expected key list only)
- Test: `skills/explain/tests/test_video_timeline_brainrot.py`

**Interfaces:**
- Consumes: `formatOf`, `limitsFor` (Task 1).
- Produces: `buildScenes(script, durations, engine, root, fail, limits)` returns scenes with `leadFrames = limits.leadFrames` and `durationInFrames = leadFrames + clipFrames + limits.tailFrames`; for explainer, cue frames keep the proportional estimate with lead 15. `main` writes the top-level object in the key order of the Interfaces section above. An unknown format in build mode prints `FAIL script: format must be explainer or brainrot` and exits 1 without writing the file.

- [ ] **Step 1: Edit the one existing assertion** in `test_timeline_top_level_shape` to the new key list:

```python
["format", "fps", "width", "height", "totalFrames", "maxSceneSeconds", "maxTotalSeconds", "engine", "scenes"]
```

and add in the same test: `timeline["format"] == "explainer"` and `(timeline["maxSceneSeconds"], timeline["maxTotalSeconds"]) == (60, 150)`. This is the only edit to the old file in this wave; its red line stays "a constant (fps, size) or the engine field changed".

- [ ] **Step 2: Write the failing brainrot build tests.** Brainrot builds need words files from Task 4, so these tests give every scene a minimal valid words file through a helper `write_words(scene_id, engine, words_json)` and `words_for(narration, seconds_per_word=0.3, pause=0.15) -> dict` that builds a consistent spec §5.2 object (sentence ends after a token ending in `.`, `?` or `!`; words back to back; `pause` between sentences). Task 4 reuses both helpers.

```python
test_brainrot_top_level_values   # -> (format, width, height, maxSceneSeconds, maxTotalSeconds) == ("brainrot", 1080, 1920, 30, 90)
test_brainrot_lead_and_tail      # durations {"intro": 3.0, "flow": 4.5} -> first scene (from, durationInFrames, leadFrames, audioFrames) == (0, 108, 6, 90); second from == 108
test_explainer_scenes_have_no_captions  # explainer build -> "captions" not in any scene
test_build_mode_unknown_format_fails    # format "vertical" -> exit 1, stdout "FAIL script: format must be explainer or brainrot", no file
```

- [ ] **Step 3: Run to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline tests.test_video_timeline_brainrot -v`
Expected: FAIL; the shape test lists the old six keys, brainrot builds report lead 15 and 1280×720.

- [ ] **Step 4: Implement** the format-aware build as in Interfaces. Build mode still runs no scene-count or length budget (`test_build_mode_skips_budgets` stays green).

- [ ] **Step 5: Run both suites**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline tests.test_video_timeline_brainrot`
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/video/build-timeline.mjs skills/explain/tests/test_video_timeline.py skills/explain/tests/test_video_timeline_brainrot.py
git commit -m "feat: explain: timeline carries format, canvas, budgets and per-format lead and tail"
```

### Task 4: words.json reader and exact brainrot cue frames

**Files:**
- Modify: `skills/explain/video/build-timeline.mjs` (new section `// ---------- words ----------`, `buildScenes`, header comment)
- Test: `skills/explain/tests/test_video_timeline_brainrot.py`

**Interfaces:**
- Consumes: `buildScenes(..., limits)` (Task 3); helpers `words_for`, `write_words` (Task 3 tests).
- Produces:

```js
const readWords = (dir, id, engine, narration, clipSeconds, bad) => { sentences, words } | undefined
const cueFrameFromWords = (words, sentences, narration, cueText, leadFrames, bad) => number | undefined
```

`readWords` reports through `bad` (scene-prefixed) with the cause texts of the Interfaces table, in this order of checks: read, JSON, shape, word count, tokens, clip end; it returns `undefined` after the first failure. `cueFrameFromWords`: the cue's first token index `k` is the number of tokens in `narration.slice(0, offset)`; it finds `j` with `|sentences[j].from − words[k].from| <= 0.001` and returns `leadFrames + Math.round(sentences[j].from × 30)`, else reports `cue … does not start a sentence in <file>`. For explainer, `buildScenes` reads no words file.

- [ ] **Step 1: Write the failing tests**

```python
test_brainrot_cue_frame_is_sentence_start  # intro sentences from 0.0 and 1.7 -> cueFrames == {"The router": 6, "The handler": 57}
test_brainrot_reads_used_engine_words_file # engine "say" with only intro.say.words.json present -> exit 0 (a kokoro file alone -> "cannot read intro.say.words.json: ENOENT")
test_brainrot_missing_words_file_fails     # -> "FAIL scene intro: cannot read intro.say.words.json: ENOENT"
test_brainrot_words_not_json_fails         # -> stdout line starts with "FAIL scene intro: intro.say.words.json is not valid JSON: "
test_brainrot_words_bad_shape_fails        # words[1].to < words[1].from -> "FAIL scene intro: intro.say.words.json has a bad shape at words[1].to"
test_brainrot_word_count_mismatch_fails    # one word dropped -> "FAIL scene intro: intro.say.words.json has 7 words, the narration has 8"
test_brainrot_token_mismatch_fails         # "handler." written as "handler" -> "... word 4 is \"handler\", the narration has \"handler.\""
test_brainrot_backticked_dotted_name_matches  # narration "The `verify.sh` script runs. It stops." with words_for -> exit 0, cue on "It stops" equals second sentence start
test_brainrot_double_space_narration_matches  # narration with "  " and "\n" between words -> exit 0
test_brainrot_sentence_start_tolerance     # words[k].from = sentence.from + 0.0004 -> exit 0; + 0.002 -> "cue \"The handler\" does not start a sentence in intro.say.words.json"
test_brainrot_words_after_clip_end_fail    # last word to 3.5 with clip 3.0 -> "FAIL scene intro: intro.say.words.json ends at 3.5 s, after the clip end 3 s"
test_brainrot_close_cues_fail              # two sentence starts 0.3 s apart -> today's "... is 9 frames after the previous cue (minimum 15)"
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_brainrot -v`
Expected: FAIL; cue frames are the proportional estimate and no words file is read.

- [ ] **Step 3: Implement** `readWords` and `cueFrameFromWords`, and call them from `buildScenes` for brainrot only. Update the header comment: build mode reads `<id>.<engine>.words.json` next to `durations.json` for a brainrot script.

- [ ] **Step 4: Run both suites**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline tests.test_video_timeline_brainrot`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/build-timeline.mjs skills/explain/tests/test_video_timeline_brainrot.py
git commit -m "feat: explain: brainrot cue frames from words.json sentence starts"
```

### Task 5: Caption chunks

**Files:**
- Modify: `skills/explain/video/build-timeline.mjs` (new section `// ---------- captions ----------`, `buildScenes`)
- Test: `skills/explain/tests/test_video_timeline_brainrot.py`

**Interfaces:**
- Consumes: `readWords` result (Task 4).
- Produces:

```js
const captionChunks = (words, leadFrames) => [{ from, to, words: [{ text, from, to }] }]
```

Rules (spec §5.4): walk the words in order; a word's frames are `leadFrames + Math.round(t × 30)` for its `from` and `to`; its caption text is the token with every backtick removed. A chunk closes after 3 words, or after a word whose caption text ends in one of `. , ; : ? !`. `chunk.from` is its first word's `from`; `chunk.to` is the next chunk's `from`, and for the last chunk its last word's `to`. Brainrot scenes get `captions: captionChunks(words, leadFrames)`.

- [ ] **Step 1: Write the failing tests** (narration `"The router picks a handler. The handler replies."` unless stated):

```python
test_caption_chunk_words      # -> [[w.text for w in c["words"]] for c in captions] == [["The","router","picks"],["a","handler."],["The","handler","replies."]]
test_caption_chunks_tile      # -> every captions[i]["to"] == captions[i+1]["from"], and captions[-1]["to"] == captions[-1]["words"][-1]["to"]
test_caption_word_frames      # word from 0.25 s with lead 6 -> word["from"] == 14 (6 + Math.round(7.5), an exact half)
test_caption_words_cover_narration  # -> flattened caption texts == narration tokens with backticks removed
test_caption_text_has_no_backticks  # narration "The `verify.sh` script runs." -> second word text == "verify.sh"
test_caption_break_after_comma      # "First, the check runs." -> chunks [["First,"],["the","check","runs."]]
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_brainrot -v`
Expected: FAIL with `KeyError: 'captions'`.

- [ ] **Step 3: Implement** `captionChunks` and attach it in `buildScenes` for brainrot.

- [ ] **Step 4: Run the wave suites and the whole explain suite**

Run: `cd skills/explain && python3 -B -m unittest discover -s tests`
Expected: `OK` (E2E cases skip without `EXPLAIN_VIDEO_E2E=1`).

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/build-timeline.mjs skills/explain/tests/test_video_timeline_brainrot.py
git commit -m "feat: explain: brainrot caption chunks in the timeline"
```

---

## Wave acceptance

- `cd skills/explain && python3 -B -m unittest tests.test_video_timeline tests.test_video_timeline_brainrot` prints `OK`.
- `git diff main -- skills/explain/tests/test_video_timeline.py` shows only the key-list assertion change of Task 3.
- `node skills/explain/video/build-timeline.mjs --check skills/explain/templates/video-script.json --root skills/explain` exits 0 with no output.

## Handoffs to other waves

- `sentence-narration`: words.json `text` must equal the narration's `/\s+/` tokens verbatim (backticks and punctuation kept); sentence `from` and the first word's `from` must agree within 0.001 s.
- `brainrot-render`: the 31 s scene and 91 s total boundary tests of spec §7.1 belong to the `render.sh` timeline stage, which must read `maxSceneSeconds` / `maxTotalSeconds` from the timeline; `types.ts` gains `format`, the two budgets and `captions`.
