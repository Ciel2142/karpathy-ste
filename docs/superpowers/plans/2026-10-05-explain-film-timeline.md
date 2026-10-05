# Explain film — wave `film-timeline` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A script with `"format": "film"` validates, builds the film timeline (scene of lead + audio + pause, `sentences`, `words`, `checkFrames`, `sources` read from disk), `build-timeline.mjs --types` writes the scene and source names, and `narrate.py` narrates a film in sentence mode. Explainer and brainrot output does not change.

**Architecture:** `build-timeline.mjs` gets a film branch beside the component formats: its own check (scene keys, `pause`, `sources`), its own build and a third mode, `--types`. The words-file reader and the frame formula are the ones brainrot already uses. `formats.json` gets a `film` row and `narrate.py` maps `film` to its sentence mode. `check_budgets.py` needs no change: it reads its limits and its format tag from the timeline.

**Tech Stack:** Node (ES module, standard library only), Python 3 `unittest`, macOS `say` and `afinfo` for the contract test.

**Spec:** `docs/superpowers/specs/2026-10-05-explain-film-design.md` — this wave implements §4.2, the timeline side of §6, §7.1, the `--types` output of §7.2 and the §9.1 cases for these files. Wave map: `docs/superpowers/waves/2026-10-05-explain-film.yaml` (wave `film-timeline`).

## Global Constraints

- Branch `feat/explain-film`, cut from `feat/explain-brainrot` (tip `c19b42f` on 2026-10-05). Never commit to the brainrot branch or to `main`. Line numbers below were read at `c19b42f`; when the tip has moved, find each place by the function named with it.
- Files this wave may change: `skills/explain/video/build-timeline.mjs`, `skills/explain/video/formats.json` (the `film` row), `skills/explain/video/narrate.py` (format table and docstring), and in `skills/explain/tests/`: new `test_video_timeline_film.py`, new `test_film_contract.py`, a film case in `test_narrate_sentences.py` and in `test_check_budgets.py`. Nothing under `video/src/` or `scripts/`.
- Every test that exists at the base passes with no edit. That includes the text `format must be explainer or brainrot` in `build-timeline.mjs` and `narrate.py`: it stays until wave `explainer-removal`, although `film` is a valid value from this wave on (cases this wave does not own assert it).
- 30 fps. Seconds become a scene-relative frame by `leadFrames + Math.round(seconds * 30)` (the caption formula). A clip lasts `Math.ceil(seconds * 30)` frames.
- Film starting values (spec §7.1): 1280×720, 3 to 30 scenes, a scene of at most 30 s, a film of at most 150 s, 45 narration words, lead 6, default pause 12, 20 source lines. `pause` is an integer from 12 to 90 (spec §4.2).
- Tool contract, unchanged: FAIL lines on stdout, one per cause, exit 1; a usage error is exit 2 with `usage:` on stderr; no new dependency.
- Tests are `unittest` modules run from `skills/explain`. Each test's docstring names the mutation that turns it red (repo convention). Each new assertion is seen to fail before the code exists; an assertion that passes at once is checked by applying its named mutation, seeing the failure, and reverting.
- No render and no `EXPLAIN_VIDEO_E2E` run in this wave; nothing is written to the video workspace.
- Commits: `<type>: <description>`, ending with the attribution line of the session.

## The film timeline (contract with waves `film-kit` and `film-render`)

Build mode writes this shape for a film. Every key is shown and the lists are cut short; the numbers are those of the fixture of Task 3.

```json
{
  "format": "film", "fps": 30, "width": 1280, "height": 720,
  "totalFrames": 597, "maxSceneSeconds": 30, "maxTotalSeconds": 150, "engine": "say",
  "sources": { "app": { "path": "src/app.py", "from": 3, "lines": ["line 3 of the app"] } },
  "checkFrames": [
    { "frame": 43, "scene": "type", "still": "s1" },
    { "frame": 152, "scene": "type", "still": "end" }
  ],
  "scenes": [
    { "id": "type", "from": 0, "durationInFrames": 153, "leadFrames": 6, "audioFrames": 135,
      "audio": "audio/type.say.wav",
      "sentences": [6, 96],
      "words": [{ "text": "The", "from": 6, "to": 21 }] }
  ]
}
```

- `durationInFrames` = `leadFrames + audioFrames + pause`; `pause` is the scene's own value, else the row's `pauseFrames`. The scene does not carry `pause`.
- `sentences[k]` is the frame of the start of sentence k and `words[i]` the frames of narration token i (text verbatim, backticks kept), all scene-relative.
- `checkFrames` holds film frames in script order: for each scene, one entry for each sentence at `from + Math.floor((start + end) / 2)` (`start` and `end` are the scene-relative frames of the sentence's `from` and `to` in the words file) with `still` `"s<k>"` (k from 1), then one entry at `from + durationInFrames - 1` with `still` `"end"`. `still` is the suffix of the still's file name (spec §7.4).
- A film scene has no `component`, `props`, `cueFrames` or `captions`.
- Marks (wave `film-kit`) read `said(id)` as `from + leadFrames + audioFrames` and `end(id)` as `from + durationInFrames`.

## Review Focus

1. `"pause": 12.0` in the JSON text. `JSON.parse` gives the integer 12, so the tool cannot tell it from `12`: it passes. `12.5`, `"12"`, `11`, `91`, `null` and `true` fail. Pinned in Task 1.
2. A source file with CRLF line ends, or with no newline after its last line: the lines carry no `\r`, and the last line counts. Pinned in Task 2 (check) and Task 4 (build).
3. A source `path` that names a directory, a missing file or an empty file: one FAIL line each, no stack trace. Pinned in Task 2.
4. A scene id or source id that is also an inherited object key (`constructor` matches the id pattern): it validates, builds and gets its type name as any other id. Pinned in Tasks 3, 4 and 5.
5. A narration of one sentence, or one whose last sentence has no end mark: one sentence frame, and `checkFrames` holds `s1` and `end` for that scene. Pinned in Tasks 3, 4 and 6.

---

### Task 1: the `film` row and the film script check

**Files:**
- Modify: `skills/explain/video/formats.json`; `skills/explain/video/build-timeline.mjs` (`loadFormats` `:43-56`, the format helpers and `SHAPES_BY_FORMAT` `:149-159`, `checkHeader` `:367-389`, `validate` `:392-420`, header comment `:1-32`)
- Create: `skills/explain/tests/test_video_timeline_film.py`

**Interfaces:**
- Consumes: `VideoCase`, `cite`, `base_script`, `FLOW_NARRATION` of `tests/test_video_timeline.py`; `brainrot_script` of `tests/test_video_timeline_brainrot.py`.
- Produces: the `film` row; `--check` for a film with the FAIL lines below; `film_script()` in the new test module (Tasks 2 to 6 and later waves import it).

- [ ] **Step 1: Write the fixture and the failing tests**

`film_script()` returns `base_script()`'s `title`, `subject` and `provenance` with:

```json
{
  "format": "film",
  "sources": [{ "id": "app", "path": "src/app.py", "from": 3, "to": 10 }],
  "scenes": [
    { "id": "type", "narration": "The router picks a handler. The handler replies.",
      "cites": [{ "path": "src/app.py", "line": 1, "snippet": "line 1" }] },
    { "id": "forms", "pause": 30,
      "narration": "First the request arrives. Then the router picks a handler. Last the handler replies.",
      "cites": [{ "path": "src/app.py", "line": 1, "snippet": "line 1" }] },
    { "id": "ends", "narration": "The first part sets up. The second part runs.",
      "cites": [{ "path": "src/app.py", "line": 3, "snippet": "line 3" }] }
  ]
}
```

Class `TestFilmCheck(VideoCase)`; `assertFails` gives exit 1 and exactly the lines named:

- `test_film_fixture_passes`: `check(film_script())` is `(0, "")`.
- `test_film_row_values`: the `film` row of `formats.json` equals the row of Step 3.
- `test_film_scene_count`: 2 scenes → `FAIL script: 2 scenes (needs 3 to 30, film)`; 30 scenes pass; 31 → `FAIL script: 31 scenes (needs 3 to 30, film)`.
- `test_film_scene_with_component_or_props_is_refused`: `component` added to `type` → `FAIL scene type: a film scene has no component or props`; `component` and `props` both → the same one line; `base_script()` with only `"format": "film"` added → that line once for each of its three scenes and nothing else.
- `test_film_scene_keys`: `"cue": "x"` on a scene → `FAIL scene type: unexpected key "cue"`; `narration` removed → `FAIL scene type: missing "narration"`.
- `test_film_narration_limits`: 45 words pass; 46 → `FAIL scene type: narration is 46 words (max 45, film)`; `"  "` → `FAIL scene type: narration is empty`.
- `test_film_cites_rule`: `cites` `[]` with subject kind `file` → `FAIL scene type: no cites (subject kind file)`; kind `topic` and no `cites` key passes.
- `test_film_pause_values`: pass with `pause` absent, `12`, `90` and the JSON text `12.0`; each of `11`, `91`, `12.5`, `"12"`, `null`, `true` → `FAIL scene forms: pause <v> must be an integer from 12 to 90`, `<v>` as JSON (`"12"` keeps its quotes).
- `test_film_duplicate_scene_id`: → `FAIL script: duplicate scene id "type"`.
- `test_slides_format_is_refused`: `"format": "slides"` → exit 1 and stdout holds the line `FAIL script: format must be explainer or brainrot` (the other lines are the explainer's, for the film keys).
- `test_brainrot_refuses_the_film_keys`: `brainrot_script()` with top-level `"sources": []` → `FAIL script: unexpected key "sources"`; with `"pause": 12` on scene `intro` → `FAIL scene intro: unexpected key "pause"`.
- `test_formats_file_without_the_film_row_fails_cleanly`: a copy of the tool beside a `formats.json` without the `film` row → exit 1, stdout is the one line `FAIL script: cannot read formats.json: expected an object with an explainer, a film and a brainrot row`, stderr empty.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_film -v`
Expected: the fixture test shows `FAIL script: format must be explainer or brainrot`, and every test FAILS except `test_slides_format_is_refused` and `test_brainrot_refuses_the_film_keys`, which hold on the base. Check those two after Step 4 by their mutations (accept any string as a format; allow `sources` and `pause` for every format), see each fail, and revert.

- [ ] **Step 3: Add the `film` row to `formats.json`, after the `explainer` row**

```json
"film": {
  "width": 1280,
  "height": 720,
  "minScenes": 3,
  "maxScenes": 30,
  "maxSceneSeconds": 30,
  "maxTotalSeconds": 150,
  "maxNarrationWords": 45,
  "leadFrames": 6,
  "pauseFrames": 12,
  "sourceLines": 20,
  "wordTimed": true
}
```

- [ ] **Step 4: Implement the film check in `build-timeline.mjs`**

- `loadFormats` needs the three rows; the cause text is the one of the last test above.
- The component shapes are built for `explainer` and `brainrot` only. Nothing reads a component limit from the `film` row.
- An invalid `format` keeps today's behavior: the `format must be explainer or brainrot` line, then validation as an explainer.
- For a film, `validate` reports in this order: the header lines (`sources` is an allowed top-level key for a film only), the source lines (Task 2; this task accepts any `sources`), `scenes must be an array` or the count line, then for each scene the duplicate-id line and the scene's own lines.
- A film scene's lines, in order: `must be an object`; `missing "id"`, `missing "narration"`; `a film scene has no component or props` (once, for either key or both); `unexpected key "<k>"` for a key outside `id`, `narration`, `cites`, `pause`, `component`, `props`; the id rules and the narration rules with today's texts and the `, film` tag; `checkCites` as today; the `pause` line when the key is present and its value is not an integer from 12 to 90. The range is a pair of constants of the tool, as `MIN_CUE_GAP` is.
- Header comment: name the three formats and list the film FAIL lines.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_film tests.test_video_timeline tests.test_video_timeline_brainrot tests.test_format_limits tests.test_transcript -v`
Expected: all PASS, the pre-existing cases with no edit.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/video/formats.json skills/explain/video/build-timeline.mjs skills/explain/tests/test_video_timeline_film.py
git commit -m "feat: explain: film format row and script check"
```

### Task 2: the `sources` check

**Files:**
- Modify: `skills/explain/video/build-timeline.mjs` (beside `readSourceLines` `:231-236`, `outsideRoot` `:239-243` and `checkCode` `:251-278`)
- Test: `skills/explain/tests/test_video_timeline_film.py`

**Interfaces:**
- Consumes: Task 1's film branch of `validate`.
- Produces: one reader for `--check` and for build mode (Task 4):

```js
// The declared lines of one source, tabs kept, or the first cause that stops the read.
readSource(entry, root, limits, tag)   // -> { lines: string[] } | { cause: string }
```

- [ ] **Step 1: Write the failing tests**

Class `TestFilmSources(VideoCase)`; each case changes the one source of `film_script()` and names its line. `<w>` is `source app` unless shown.

- `test_sources_absent_and_empty_pass`: no `sources` key and `[]` both give `(0, "")`.
- `test_sources_must_be_an_array`: `{}` → `FAIL script: sources must be an array`.
- `test_source_shape`: entry `7` → `FAIL source #1: must be an object`; `to` removed → `FAIL source app: missing "to"`; `"lines": []` added → `FAIL source app: unexpected key "lines"`.
- `test_source_id`: `"App"` → `FAIL source #1: id "App" must match [a-z0-9-]`; `""` or `5` → `FAIL source #1: id must be a non-empty string`; a second entry with id `app` → `FAIL source app: duplicate id`.
- `test_source_path`: `5` → `FAIL source app: path must be a string`; `""` → `FAIL source app: path is empty`; `"../x.py"` and `"/etc/hosts"` → `FAIL source app: path "<p>" must be a relative path inside the data root`.
- `test_source_range`: `from` `"3"` → `FAIL source app: from must be an integer`; `from` 0, and `from` 5 with `to` 3 → `FAIL source app: range <from>-<to> is not a valid line range`; 1 to 20 passes; 1 to 21 → `FAIL source app: range 1-21 is 21 lines (max 20, film)`.
- `test_source_file_faults`: a missing file and a directory → `FAIL source app: path <p> cannot be read under the data root`; an empty file with range 1-1 → `FAIL source app: to 1 is outside <p> (0 lines)`; `to` 73 on `src/app.py` → `FAIL source app: to 73 is outside src/app.py (72 lines)`.
- `test_source_last_line_without_a_final_newline`: a 3-line file with no final newline and range 3-3 passes.
- `test_source_with_a_nul_byte`: a file with a NUL byte outside the declared range → `FAIL source app: <p> has a NUL byte`.
- `test_two_faulty_sources_and_a_faulty_scene`: two source faults and one scene fault give three lines: the sources in script order, then the scene.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_film.TestFilmSources -v`
Expected: all FAIL except `test_sources_absent_and_empty_pass` and `test_source_last_line_without_a_final_newline`, which pass at once. Check both after Step 3 by their mutations (refuse `[]`; drop the last line of a file with no final newline), see each fail, and revert.

- [ ] **Step 3: Implement the source rules**

`where` is `source <id>` for an id that matches the scene id pattern, else `source #<n>` (n from 1). Shape faults (not an object, a missing or unexpected key, a bad `id`, `path`, `from` or `to` type, a duplicate id) are one line each. When the shape holds, `readSource` follows the order and the early stops of `checkCode`: an invalid range stops; more than `limits.sourceLines` lines is a line and the check goes on; a path outside the root stops; an unreadable path stops; a NUL byte anywhere in the file stops; `to` past the last line is a line. Lines are split as `readSourceLines` splits them (no `\r`, no entry for a final newline).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_film -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/build-timeline.mjs skills/explain/tests/test_video_timeline_film.py
git commit -m "feat: explain: film sources are checked against the data root"
```

### Task 3: film build — scene lengths, `sentences`, `words`

**Files:**
- Modify: `skills/explain/video/build-timeline.mjs` (`readWords` `:452-479` is reused; a film build beside `buildScenes` `:536-599`; `main` `:628-658`)
- Test: `skills/explain/tests/test_video_timeline_film.py`

**Interfaces:**
- Consumes: `words_for(narration, seconds_per_word, pause)` of `tests/test_video_timeline_brainrot.py`; `readWords`; the `pause` predicate of Task 1.
- Produces: build mode for a film with the top-level keys and the scene keys of "The film timeline", `sources` and `checkFrames` left to Task 4 (write `{}` and `[]`). Test helper `FilmBuildCase.build_film(script, seconds=None, engine="say")`: writes `words_for(narration, 0.5, 0.5)` for every scene and, when `seconds` is `None`, a duration equal to the end of each scene's last word; returns `(result, timeline)`.

- [ ] **Step 1: Write the failing tests**

With `words_for(n, 0.5, 0.5)` the fixture's clips last 4.5 s, 8.0 s and 5.0 s. Class `TestFilmBuild(FilmBuildCase)`:

- `test_film_top_level_values`: `format` `film`, `fps` 30, 1280×720, `maxSceneSeconds` 30, `maxTotalSeconds` 150, `engine` `say`, `totalFrames` 597.
- `test_film_scene_is_lead_audio_pause`: `durationInFrames` `[153, 276, 168]` (`forms` has `pause` 30, the others the default 12), `from` `[0, 153, 429]`, `leadFrames` 6, `audioFrames` `[135, 240, 150]`, `audio` `audio/type.say.wav`.
- `test_film_scene_keys`: the keys of each scene are exactly `id`, `from`, `durationInFrames`, `leadFrames`, `audioFrames`, `audio`, `sentences`, `words`.
- `test_film_sentence_frames`: `[6, 96]`, `[6, 81, 186]`, `[6, 96]`; each equals `6 + js_round(s["from"] * 30)` over the words fixture.
- `test_film_word_frames`: `type.words[0]` is `{"text": "The", "from": 6, "to": 21}` and its last word `{"text": "replies.", "from": 126, "to": 141}`; with a narration that holds `` `verify.sh` ``, the word texts equal `narration.split()`.
- `test_film_one_sentence_without_an_end_mark`: narration `No end mark here` → `sentences` is `[6]`.
- `test_film_reads_the_words_file_of_the_engine`: engine `kokoro` reads `<id>.kokoro.words.json`; with no words file → `FAIL scene type: cannot read type.say.words.json: ENOENT`.
- `test_film_words_file_faults`: one word removed → `FAIL scene type: type.say.words.json has 7 words, the narration has 8`; `sentences` `[]` → `FAIL scene type: type.say.words.json has no sentences`.
- `test_film_build_faults`: no duration → `FAIL scene type: no duration in durations.json`; `pause` `"12"` → `FAIL scene forms: pause "12" must be an integer from 12 to 90`; a scene that is not an object → `FAIL scene #1: needs id and narration to build`.
- `test_film_scene_id_constructor`: a scene with id `constructor` builds, and a missing duration for it is reported, not read from an inherited key.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_film.TestFilmBuild -v`
Expected: all FAIL (`needs id, narration and props to build`).

- [ ] **Step 3: Implement the film build**

`main` builds a film through its own function and a component format through `buildScenes`, unchanged. For each scene: the duration faults of `buildScenes` with their texts; `readWords` and its FAIL lines; the `has no sentences` line; frames by the formula of Global Constraints. The film timeline has no `background` key and its scenes none of the component keys.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_film tests.test_video_timeline tests.test_video_timeline_brainrot -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/build-timeline.mjs skills/explain/tests/test_video_timeline_film.py
git commit -m "feat: explain: film timeline with sentence and word frames"
```

### Task 4: film build — `sources` and `checkFrames`

**Files:**
- Modify: `skills/explain/video/build-timeline.mjs` (the film build of Task 3)
- Test: `skills/explain/tests/test_video_timeline_film.py`

**Interfaces:**
- Consumes: `readSource` (Task 2); the film build (Task 3).
- Produces: `sources` and `checkFrames` of "The film timeline". Waves `film-render` and `film-guard` read both.

- [ ] **Step 1: Write the failing tests**

- `test_film_sources_lines`: `sources` equals `{"app": {"path": "src/app.py", "from": 3, "lines": APP_LINES[2:10]}}`.
- `test_film_sources_expand_tabs`: a source on `src/wide.py` line 3 → its line is 69 `x` and 4 spaces.
- `test_film_sources_strip_crlf`: a file written with `\r\n` → no line holds `\r`.
- `test_film_without_sources`: no key and `[]` both give `"sources": {}`.
- `test_film_source_id_constructor`: a source with id `constructor` is an own key of `sources` with its lines.
- `test_film_source_faults_in_build_mode`: a source whose file is missing → exit 1, `FAIL source app: path src/none.py cannot be read under the data root`, no timeline written; a build with no `--root` → `FAIL source app: cannot read source lines (needs --root)`.
- `test_check_frames`: `[(c["frame"], c["scene"], c["still"]) for c in checkFrames]` equals `[(43, "type", "s1"), (118, "type", "s2"), (152, "type", "end"), (189, "forms", "s1"), (279, "forms", "s2"), (369, "forms", "s3"), (428, "forms", "end"), (472, "ends", "s1"), (555, "ends", "s2"), (596, "ends", "end")]`.
- `test_check_frames_invariants`: the frames increase strictly, the last is `totalFrames - 1`, and each scene has one entry for each sentence of its words fixture plus one.
- `test_check_frames_of_a_one_sentence_scene`: `still` values are `["s1", "end"]`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_film.TestFilmBuild -v`
Expected: the nine new tests FAIL (`{}` and `[]`), except `test_film_without_sources` (mutation: write `null`; see it fail; revert).

- [ ] **Step 3: Implement `sources` and `checkFrames`**

Build mode runs `readSource` for each source, so it applies every rule of Task 2, the outside-root rule included. This is stricter than spec §4.2, which notes that build mode reads without that guard; one code path serves both modes, and the symlink gap of kp-m3c stays. Each tab of a line becomes 4 spaces. `checkFrames` follows the rule of "The film timeline".

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_film -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/build-timeline.mjs skills/explain/tests/test_video_timeline_film.py
git commit -m "feat: explain: film timeline carries source lines and check frames"
```

### Task 5: `build-timeline.mjs --types`

**Files:**
- Modify: `skills/explain/video/build-timeline.mjs` (`USAGE` `:61-63`, `parseArgs` `:608-621`, `main` `:628-658`, header comment)
- Test: `skills/explain/tests/test_video_timeline_film.py`

**Interfaces:**
- Consumes: nothing of the earlier tasks but the file.
- Produces: `build-timeline.mjs --types <script.json> <out.ts>`. Wave `film-render` checks its output in as `src/film/script.gen.ts`; wave `film-scene-stage` runs it in the `scene` stage. The output imports `FilmProps` from `../kit` (wave `film-kit`).

- [ ] **Step 1: Write the failing tests**

Class `TestFilmTypes(VideoCase)`:

- `test_types_output`: for `film_script()` the file is exactly:

```ts
// Generated by build-timeline.mjs --types from script.json. Do not edit.
import type { FilmProps } from "../kit";
export type SceneId = "type" | "forms" | "ends";
export type SourceId = "app";
export type Props = FilmProps<SceneId, SourceId>;
```

  with one newline at the end; exit 0, stdout empty.
- `test_types_without_sources`: no `sources` key and `[]` → the line `export type SourceId = never;`.
- `test_types_id_constructor`: a scene id `constructor` is in `SceneId` as `"constructor"`.
- `test_types_usage`: one positional, three positionals, and `--types` with `--check` → exit 2 and `usage:` on stderr.
- `test_types_refuses_a_script_that_is_not_a_film`: `base_script()` → exit 1, `FAIL script: --types needs a film script`, no file written.
- `test_types_refuses_a_bad_id`: a scene id `a" | "b` → `FAIL scene #1: id must match [a-z0-9-]`; a source id `A` → `FAIL source #1: id must match [a-z0-9-]`; no file written.
- `test_types_cannot_write`: an out path below a regular file → `FAIL script: cannot write <out>: ENOTDIR`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_film.TestFilmTypes -v`
Expected: all FAIL (`unknown option --types`, exit 2), except `test_types_usage` (mutation after Step 3: accept three positionals; see it fail; revert).

- [ ] **Step 3: Implement the mode**

`--types` reads the script with `readJson` (its two FAIL lines), needs `format` `film`, an array `scenes` (`FAIL script: scenes must be an array`) and, when present, an array `sources`; it checks only that each scene id and source id is a string that matches the scene id pattern, so an id can never close the string it is written into. It runs no other rule and reads no other file: `render.sh` runs `--check` first. Ids keep script order. `USAGE` and the header comment gain the third form.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_film tests.test_video_timeline -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/build-timeline.mjs skills/explain/tests/test_video_timeline_film.py
git commit -m "feat: explain: build-timeline --types writes the film scene and source names"
```

### Task 6: `narrate.py` film mode, the budget case and the producer-to-consumer test

**Files:**
- Modify: `skills/explain/video/narrate.py` (`FORMATS` `:53`, docstring `:15-20`)
- Modify: `skills/explain/tests/test_narrate_sentences.py` (class `Sentences`), `skills/explain/tests/test_check_budgets.py`
- Create: `skills/explain/tests/test_film_contract.py`

**Interfaces:**
- Consumes: the film check and build of Tasks 1 to 4; `film_script()`; `NARRATE_PY`, `ONE`, `scene` of `tests/test_narrate.py`; the pattern of `tests/test_brainrot_contract.py` (`js_round`, one narrate run and one build in `setUpClass`).
- Produces: `narrate.py` narrates a `film` script in sentence mode. `render.sh` passes `--speed` only for brainrot, so a film speaks at the default 1.0; wave `film-render` keeps that.

- [ ] **Step 1: Write the failing tests**

`test_narrate_sentences.py`, class `Sentences`:
- `test_film_is_narrated_in_sentences`: a script with format `film`, `--engine say` → exit 0, `one.say.words.json` exists, and the sidecar is `engine=say\nvoice=say-default\nspeed=1.0\nmode=sentences\n` followed by the narration.

`test_check_budgets.py`:
- `test_film_scene_30_ok_31_fails`: `fmt="film"`, limits 30 and 150: 900 frames → `ok 1 30.0 30.000`; 930 → `FAIL scene a is 31.0 s (max 30, film)`.
- `test_film_total_150_ok_151_fails`: five scenes of 900 frames → `ok 5 150.0 150.000`; a sixth of 30 frames → `FAIL total 151.0 s (max 150, film)`.

`test_film_contract.py`, class `FilmContract`: `film_script()` with the narrations below (a backticked dotted name, a comma, a double space and a newline between words; one scene of one sentence with no end mark), `--check`, then `narrate.py --engine say` with no `--speed`, then a build over its audio directory.

```python
NARRATIONS = {
    "type": "The router runs `verify.sh`, then  stops.\nThe handler replies, and it ends.",
    "forms": FLOW_NARRATION,
    "ends": "One sentence with no end mark",
}
```

- `test_fixture_is_a_valid_film_script`: `--check` is `(0, "")`.
- `test_narrate_then_build_exit_zero`: both exit 0, build stdout empty, `format` is `film`, scene ids in order.
- `test_film_speaks_at_speed_1`: every sidecar holds the lines `speed=1.0` and `mode=sentences`.
- `test_sentence_frames_are_lead_plus_sentence_start`: for each scene, `sentences` equals `[6 + js_round(s["from"] * 30)]` over its `words.json`, and `sentences[0]` is 6.
- `test_word_texts_are_the_narration_tokens`: each scene's word texts equal `narration.split()`.
- `test_words_end_inside_the_clip`: the last word's `to` is at most `leadFrames + audioFrames`.
- `test_scene_length`: `durationInFrames` is `6 + audioFrames + pause` (30 for `forms`, else 12).
- `test_check_frames_follow_the_sentences`: the frames increase strictly, the last is `totalFrames - 1`, `ends` has exactly `s1` and `end`, and each `s<k>` frame lies inside sentence k of the words file.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_contract tests.test_narrate_sentences tests.test_check_budgets -v`
Expected: the narrate case and the contract cases that need the narrate run FAIL (`format must be explainer or brainrot`, exit 2); `test_fixture_is_a_valid_film_script` passes, since it only guards the fixture. The two budget cases pass at once: check them by making `format_tag` of `check_budgets.py` return `""` for `film`, see both fail, then `git checkout -- skills/explain/video/check_budgets.py`.

- [ ] **Step 3: Add `film` to the format table of `narrate.py`**

`film` maps to the `sentences` mode. The docstring's paragraph on formats names `film` beside `brainrot`. The text of the unknown-format failure does not change (Global Constraints).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_contract tests.test_narrate tests.test_narrate_sentences tests.test_check_budgets -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/narrate.py skills/explain/tests/test_narrate_sentences.py skills/explain/tests/test_check_budgets.py skills/explain/tests/test_film_contract.py
git commit -m "feat: explain: narrate.py narrates a film by sentence; film contract test"
```

---

## Wave close

Run the map's acceptance command:

`cd skills/explain && python3 -B -m unittest tests.test_video_timeline_film tests.test_film_contract tests.test_video_timeline tests.test_video_timeline_brainrot tests.test_narrate tests.test_narrate_sentences tests.test_check_budgets`

Expected: all PASS. Then the unit suite, `cd skills/explain && python3 -B -m unittest discover -s tests`: all PASS, with no edit to a case that existed at the base. Update the wave map: `film-timeline` `status: done`.

Input for the plan of wave `film-render`: a test that passes a timeline built by the real tool to `makeAt` of the kit, so that the two sides of "The film timeline" meet in one test before `FilmStage` relies on them.
