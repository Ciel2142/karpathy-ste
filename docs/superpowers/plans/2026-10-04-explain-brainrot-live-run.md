# Explain brainrot — wave brainrot-live-run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A real subject from this repo renders as `brainrot`; the per-format limits are measured against stills, tuned and folded back into one source; the user accepts the video on a phone.

**Architecture:** Three small fixes from the parked findings come first, so the run tests the fixed system: the limits move to one data file that a drift test ties to the rung; the caption chunker gets a character cap; the probe kills its process group. Then two renders give the evidence: a stress script with every text at its limit, which is measured with a pixel extent helper, and a live run by a fresh runner who reads only the skill text. One fold-back applies a fixed tuning rule to that evidence.

**Tech Stack:** Remotion 4.0.532, React 19.2.3, TypeScript 5.9.3, Node 25.9 (strips types for `.ts`), Python 3 stdlib `unittest`, bash.

**Spec:** `docs/superpowers/specs/2026-10-04-explain-brainrot-design.md` (§3.4 limits, §5.4 caption chunks, §6.3 still faults, §7.5 live run). Map: `docs/superpowers/waves/2026-10-04-explain-brainrot.yaml`, wave `brainrot-live-run`. Inputs: br `kp-c04` (seven parked findings).

## Rulings in this plan (confirm at review)

- **Subject:** `skills/ste/scripts/ste_lint.py`. It has a flow (tokenize, sentences, rules, findings, exit code) and code runs of up to 11 lines within 40 columns. It does not belong to the feature under test. Alternative: `skills/explain/video/pick_background.py`.
- **Skill text from the branch:** the runner's `<skill-dir>` is `/Users/valukin/karpathy-wt/feature/skills/explain`. `~/.claude/skills/explain` (main) stays untouched. The workspace `~/karpathy/video-workspace` is shared as before, and each `render.sh` re-syncs `app/` from its own checkout.
- **Background:** the stress render uses the generated loop with seed 7. The live run uses a clip if the user puts one in `~/karpathy/video-workspace/backgrounds/` before Task 5, and the generated loop otherwise.
- **Parked findings (kp-c04):** (1) caption width: Task 2. (2) Kokoro tail margin: measured in Task 5, rule in Task 6. (3) large-clip cost: measured in Task 5 only when a clip is present; no code change unless the ratio exceeds 2.0. (4) gated non-loop still: not in this wave, filed as a follow-up br issue at wave close. A frame-matched reference still is test strength, not a live-run need. (5) and (6) single source and drift: Task 1. (7) probe grandchild: Task 3.
- **New brainrot-only limits are possible.** A scene heading has no length limit today, and the edge label is fixed at 10 chars for both formats. If the stress still shows a fault in either, Task 6 adds a brainrot-only limit (see Tuning rule). A brainrot script that passes today could then fail at `script`.
- **Time limits are not tuned.** Scenes 3–6, 30 s per scene, 90 s total and 45 words come from user decision D5. Only text limits, `captionChars` and `tailFrames` can change.

## Tuning rule (Task 6 applies it to the Task 4 and Task 5 evidence)

For each text limit, the stress still shows that text at its limit. Its fill is the ink extent of the text along the limited axis, divided by the box it must fit: width for chars and columns, height for line counts.

- **Lower** the limit when a still at the limit shows a fault (clipped, wrapped where the component allows one line, overlapping the caption band or another element) or the fill is above 1.0. The new value is the largest one whose stress text renders without the fault; confirm it with one more stress render.
- **Raise** the limit when the fill is 0.80 or less. The new value is `floor(limit × 0.95 / fill)`. Confirm it with one more stress render at the new value: no fault, fill ≤ 0.95.
- **Otherwise keep** the limit. Every row, changed or kept, gets one line of evidence in the note: still name, fill, fault or none.
- **Limits outside the table:** the scene heading (no limit in either format) and the edge label (10 chars, fixed for both). If the stress still shows a fault in either one, add a brainrot-only key (`sceneTitle` or `edgeLabel`) to `formats.json` at the largest value that renders cleanly. The explainer row gets `null`, which means "as today". Also add the row to the rung and spec tables, and the case to `expected_cells`. Otherwise record them as kept.
- **`tailFrames`:** if the smallest tail silence of the live run (Kokoro) is below 0.40 s (verify_sync `MIN_TAIL` 0.30 s + 0.10 s headroom), set it from 12 to 15. Otherwise keep 12.
- **The explainer column never changes.**

## Global Constraints

- The explainer renders the same pixels: the landscape regression stays within spec §7.4 (≤ 0.5 % of pixels differ by > 16 levels). Never re-capture the landscape baseline; never pass `--force`.
- The explainer prints its nine stage lines and brainrot its ten, with the strings of spec §6.1, unchanged.
- Never install a package globally; never use `npx`. Nothing is downloaded for backgrounds.
- Never write a password, token or key in narration, props or snippets.
- `skills/explain/rungs/brainrot.md` and `skills/explain/SKILL.md` lint clean: `python3 skills/ste/scripts/ste_lint.py <file>` prints `0 errors, 0 warnings`.
- Unit suite: `cd skills/explain && python3 -B -m unittest discover -s tests` passes. Gated E2E: `EXPLAIN_VIDEO_E2E=1`.
- Inside a subagent, never run `open` (SKILL.md convention 6).
- Commits: plain `git commit`, message ending `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Use `/usr/bin/git` if the worktree guard refuses a command.

## Review Focus

1. A backticked code name of 28 characters (`EXPLAIN_BRAINROT_BACKGROUNDS`) in narration. Expected: its caption is one line inside the frame, in smaller type. Pinned in Task 2 (`test_long_word_is_its_own_chunk`, `test_caption_font_shrinks_long_word`) and Task 4 (stress still read).
2. A three-word chunk at exactly the character cap, written in capitals. Expected: it fits one line at full size. Pinned in Task 4 (the cue still of scene 1, read and measured).
3. `formats.json` missing or not valid JSON. Expected: one FAIL line, not a Node stack trace. Pinned in Task 1 (`test_missing_formats_file_fails_cleanly`).
4. A hung probe whose child process holds the pipe. Expected: the picker returns, prints the SKIP line, and no probe process stays alive. Pinned in Task 3 (`test_probe_timeout_kills_grandchild`).
5. A limit tuned in `formats.json` but not in the rung. Expected: a red test before the commit. Pinned in Task 1 (`test_rung_table_matches_formats` and its siblings).

## File structure

| Path | Change | Task |
|---|---|---|
| `skills/explain/video/formats.json` | Create: the FORMATS rows, verbatim | 1, 2, 6 |
| `skills/explain/video/build-timeline.mjs` | Read `formats.json`; caption character cap | 1, 2 |
| `skills/explain/video/transcript.py` | Format row size from `formats.json`; drop `BRAINROT_SIZE` | 1 |
| `skills/explain/tests/test_format_limits.py` | Create: drift tests rung ↔ `formats.json` | 1, 2 |
| `skills/explain/video/src/short/captions.ts`, `CaptionBand.tsx` | Font size for a long chunk; no wrap | 2 |
| `skills/explain/video/pick_background.py` | Probe in its own process group | 3 |
| `skills/explain/tests/png_diff.py`, `tests/test_png_diff.py` | `ink_extent` helper and its test | 4 |
| `skills/explain/tests/fixtures/brainrot-limits-script.json`, `limits-source.txt` | Create: stress script and its code source | 4 |
| `skills/explain/tests/test_render_brainrot.py` | Gated stress render cases | 4 |
| `skills/explain/rungs/brainrot.md` | Table rows, captions bullet, §8 without repeated numbers, tuned values | 1, 2, 6 |
| `docs/superpowers/specs/2026-10-04-explain-brainrot-design.md` | §3.4 table, §5.4 cap; dated amendments | 2, 6 |
| `docs/superpowers/spikes/2026-10-05-explain-brainrot-live-run.md` | Create: the run, stills, measurements, limit changes, acceptance | 4–7 |

---

### Task 1: Limits in one file, with a drift guard (kp-c04 findings 5 and 6)

**Files:**
- Create: `skills/explain/video/formats.json`, `skills/explain/tests/test_format_limits.py`
- Modify: `skills/explain/video/build-timeline.mjs` (the `FORMATS` literal at lines 38–53), `skills/explain/video/transcript.py` (`BRAINROT_SIZE`, `format_rows`), `skills/explain/rungs/brainrot.md` (§8)
- Test: `skills/explain/tests/test_format_limits.py`, `skills/explain/tests/test_transcript.py`

**Interfaces:**
- Produces: `skills/explain/video/formats.json`, a JSON object `{ "explainer": {…}, "brainrot": {…} }`. Each row holds the keys and values of today's `FORMATS` rows, verbatim: `width, height, minScenes, maxScenes, maxSceneSeconds, maxTotalSeconds, maxNarrationWords, leadFrames, tailFrames, codeLines, codeColumns, bulletText, beforeAfterLines, beforeAfterLineChars, beforeAfterHeading, diagramLabel, diagramSub, titleTitle, titleSubtitle, wordTimed`.
- Produces in `transcript.py`: `FORMATS_FILE: Path` (beside the script) and `canvas_label(fmt: str) -> str`, which returns `"1080×1920"` for `brainrot` today.
- Produces in `test_format_limits.py`: `rung_limits_table() -> dict[str, tuple[str, str]]` (row label → (explainer cell, brainrot cell)) and `expected_cells(formats: dict) -> dict[str, tuple[str, str]]`. Task 2 adds one row to both.

- [ ] **Step 1: Write the failing drift tests** in `test_format_limits.py`. `expected_cells` formats each row from `formats.json`, with the labels exactly as the rung writes them:

```text
canvas                      -> "{width}×{height}"
scenes                      -> "{minScenes}–{maxScenes}"
max scene length            -> "{maxSceneSeconds} s"
max total length            -> "{maxTotalSeconds} s"
narration words per scene   -> "{maxNarrationWords}"
lead / tail frames          -> "{leadFrames} / {tailFrames}"
code range                  -> "{codeLines} lines × {codeColumns} columns"
`bullets-appear` text       -> "{bulletText} chars"
`before-after`              -> "<side by side | stacked>; 0–{beforeAfterLines} lines × {beforeAfterLineChars} chars; heading {beforeAfterHeading}"   (side by side: explainer; stacked: brainrot)
diagram `label` / `sub`     -> "{diagramLabel} / {diagramSub}"
`title` title / subtitle    -> "{titleTitle} / {titleSubtitle}"
```

```python
def test_rung_table_matches_formats(self): self.assertEqual(rung_limits_table(), expected_cells(load_formats()))
def test_rung_awk_threshold_is_code_columns(self): # the `length($0) > N` of the rung's awk command: N == brainrot codeColumns
def test_rung_fail_example_names_code_columns(self): # the example "(max N, brainrot)": N == brainrot codeColumns
def test_rung_code_sentence_matches(self): # "at most {codeLines} lines, and each line has at most {codeColumns} columns" is in the rung (whitespace-normalised)
def test_missing_formats_file_fails_cleanly(self): # build-timeline.mjs copied alone to a temp dir, run with --check: stdout starts "FAIL script: cannot read formats.json", exit 1, no "at " stack line on stderr
def test_build_timeline_reads_formats_file(self): # a temp copy of build-timeline.mjs + formats.json with brainrot codeColumns 39: a 40-column code line fails "(max 39, brainrot)"
```

`rung_limits_table` parses the one table whose header row is `| Limit | explainer | brainrot |`.

In `test_transcript.py`, add:

```python
def test_format_row_size_from_formats_file(self): # FORMATS_FILE patched to a temp copy whose brainrot width is 1000: the Format row reads "brainrot (1000×1920)"
```

- [ ] **Step 2: Run them; the new tests fail** (no `formats.json`, the transcript has no `FORMATS_FILE`).

Run: `cd skills/explain && python3 -B -m unittest tests.test_format_limits tests.test_transcript`
Expected: errors or failures in the new tests only.

- [ ] **Step 3: Create `formats.json`, and make `build-timeline.mjs` and `transcript.py` read it.**
  - `build-timeline.mjs` reads the file at load time, from `new URL("./formats.json", import.meta.url)`. Point the comment above it at the file ("tune them in formats.json only").
  - A missing file, an unreadable file or invalid JSON prints `FAIL script: cannot read formats.json: <cause>` on stdout and exits 1, through the existing `finish`. The output of every existing case is unchanged.
  - `transcript.py` builds the Format row from `canvas_label("brainrot")`. A missing or invalid file is a `ScriptError` (exit 2, one line).
  - Rung §8: drop the canvas size and the lead/tail sentence, which the table holds. Keep the panel geometry, the voice speed and the seed. The rung lints clean.

- [ ] **Step 4: Run the whole unit suite and the rung lint.**

Run: `cd skills/explain && python3 -B -m unittest discover -s tests && python3 ../ste/scripts/ste_lint.py rungs/brainrot.md`
Expected: `OK` (skips allowed) and `0 errors, 0 warnings`.

- [ ] **Step 5: Commit** — `refactor: explain: brainrot limits in formats.json, rung drift tests`

### Task 2: Caption chunks fit one line (kp-c04 finding 1)

**Files:**
- Modify: `skills/explain/video/formats.json`, `skills/explain/video/build-timeline.mjs` (`captionChunks`, lines 492–517), `skills/explain/video/src/short/captions.ts`, `skills/explain/video/src/short/CaptionBand.tsx`, `skills/explain/rungs/brainrot.md` (table and "Captions" bullet), spec §3.4 table and §5.4
- Test: `skills/explain/tests/test_video_timeline_brainrot.py`, `skills/explain/tests/test_short_logic.py`, `skills/explain/tests/test_format_limits.py`

**Interfaces:**
- Consumes: `formats.json` and `expected_cells` (Task 1).
- Produces: the key `captionChars` in both `formats.json` rows: `null` for explainer, `20` for brainrot (starting value: 1000 px band ÷ about 46 px per bold 76 px character; Task 4 measures it).
- Produces in `captions.ts`: `export const CAPTION_FONT = 76`, `export const CAPTION_LINE_CHARS = 20`, and `export function captionFontSize(text: string): number`.
- Produces in the rung table and the spec §3.4 table: the row `caption chunk` | `—` | `1–3 words, {captionChars} chars`.

- [ ] **Step 1: Write the failing tests.**

```python
# test_video_timeline_brainrot.py (words timed by the existing fixture helper)
def test_chunk_breaks_before_char_cap(self): # words keyboards monitors speakers -> chunk texts ["keyboards monitors", "speakers"]
def test_chunk_at_cap_kept(self): # abcdef ghijkl mnopqr (exactly 20 chars joined) -> one chunk
def test_long_word_is_its_own_chunk(self): # the `EXPLAIN_BRAINROT_BACKGROUNDS` folder -> ["the"], ["EXPLAIN_BRAINROT_BACKGROUNDS"], ["folder"]
# test_short_logic.py
def test_caption_font_full_at_line_budget(self): # captionFontSize("x" * 20) == 76
def test_caption_font_shrinks_long_word(self): # captionFontSize("EXPLAIN_BRAINROT_BACKGROUNDS") == 54   (floor(76 * 20 / 28))
def test_caption_line_budget_covers_chunk_cap(self): # formats.json brainrot captionChars <= CAPTION_LINE_CHARS
# test_format_limits.py: expected_cells gains "caption chunk" -> ("—", "1–3 words, {captionChars} chars")
```

The existing chunk invariants keep passing unchanged: at most 3 words, a break after punctuation, no gap, no overlap, every word once and in order, no backticks.

- [ ] **Step 2: Run them; the new tests fail.**

Run: `cd skills/explain && python3 -B -m unittest tests.test_video_timeline_brainrot tests.test_short_logic tests.test_format_limits`
Expected: failures in the new tests only.

- [ ] **Step 3: Implement.**
  - **Chunker:** before a word joins an open chunk, close the chunk if the chunk's text plus a space plus the word is longer than `captionChars`. A word longer than `captionChars` is a chunk alone. The 3-word and punctuation breaks stay. The cap applies to the text without backticks.
  - **Font size:** `captionFontSize` returns `CAPTION_FONT` when `text.length <= CAPTION_LINE_CHARS`, else `Math.floor(CAPTION_FONT * CAPTION_LINE_CHARS / text.length)`.
  - **CaptionBand:**
    - It takes its size from `captionFontSize`, applied to the chunk's words joined by one space.
    - It sets `whiteSpace: "nowrap"`.
    - The stroke scales with the size: 8 px at 76 px, rounded.
    - The header comment says the band is always one line.
  - **Docs:** the rung's Captions bullet says a caption holds at most `captionChars` characters, and that a longer code name shows alone in smaller type. Add the table row. In the spec, add the §3.4 row and amend §5.4 with a dated line: "(Amended 2026-10-05 in wave brainrot-live-run: a chunk also closes before it passes the character cap of §3.4; a longer word is a chunk alone, drawn smaller.)".

- [ ] **Step 4: Run the unit suite, the gated stills and the lint.**

Run: `cd skills/explain && python3 -B -m unittest discover -s tests && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_short_still && python3 ../ste/scripts/ste_lint.py rungs/brainrot.md`
Expected: `OK` and `0 errors, 0 warnings`.

- [ ] **Step 5: Commit** — `fix: explain: brainrot caption chunks fit one line`

### Task 3: The probe kills its process group (kp-c04 finding 7)

**Files:**
- Modify: `skills/explain/video/pick_background.py` (`probe`, lines 199–209)
- Test: `skills/explain/tests/test_pick_background.py`

**Interfaces:**
- Consumes: none. The signature `probe(remotion, clip, app) -> tuple[float | None, str | None]` and the cause text `ffprobe timed out` stay.

- [ ] **Step 1: Write the failing test.** It uses the stub remotion CLI pattern of `test_probe_timeout_skipped` (line 250). The stub starts `sleep 30` in the background, writes its pid to a file, and waits.

```python
def test_probe_timeout_kills_grandchild(self): # PROBE_TIMEOUT 0.3: lines == ["background: SKIP x.mp4 (ffprobe timed out)", GENERATED]; within 2 s after return, os.kill(pid, 0) raises ProcessLookupError
```

- [ ] **Step 2: Run it; it fails** (the `sleep` grandchild is still alive).

Run: `cd skills/explain && python3 -B -m unittest tests.test_pick_background -k grandchild`
Expected: FAIL on the liveness assertion.

- [ ] **Step 3: Implement.** Start the probe with `start_new_session=True`. On timeout, kill the whole group (`os.killpg(pid, SIGKILL)`, ignoring `ProcessLookupError`), collect the child, and return `(None, "ffprobe timed out")`. The `OSError` and exit-code paths do not change.

- [ ] **Step 4: Run the picker suite.**

Run: `cd skills/explain && python3 -B -m unittest tests.test_pick_background`
Expected: `OK`.

- [ ] **Step 5: Commit** — `fix: explain: background probe timeout kills its process group`

### Task 4: Limits stress render and measurement

**Files:**
- Create: `skills/explain/tests/fixtures/limits-source.txt`, `skills/explain/tests/fixtures/brainrot-limits-script.json`, `skills/explain/tests/test_png_diff.py`, `docs/superpowers/spikes/2026-10-05-explain-brainrot-live-run.md`
- Modify: `skills/explain/tests/png_diff.py`, `skills/explain/tests/test_render_brainrot.py` (`render_brainrot`)

**Interfaces:**
- Consumes: `formats.json` with `captionChars` (Tasks 1–2); `read_png` in `png_diff.py`.
- Produces: `ink_extent(png: Path, x0: int, x1: int, y0: int, y1: int, level: int = 40) -> tuple[int, int, int, int] | None` in `png_diff.py`. It returns `(x_min, x_max, y_min, y_max)` of the pixels in the half-open box that differ from white by more than `level` in any channel, or `None`.
- Produces: `render_brainrot(kind, script=BRAINROT_TEMPLATE)`, cached per `(kind, script)`.

- [ ] **Step 1: Write the failing tests.**

```python
# test_png_diff.py (synthetic 8-bit RGB PNGs written with zlib + struct)
def test_ink_extent_none_on_white(self): # all-white 10x10 -> None
def test_ink_extent_box(self): # black pixels at (2,3) and (6,7) -> (2, 6, 3, 7); box x0=4 -> (6, 6, 7, 7)
# test_render_brainrot.py (gated)
def test_limits_script_ten_ok_lines(self): # the stress script, generated loop: ten "ok" stage lines, no FAIL
def test_limits_stills_keep_panel_margins(self): # every still: ink_extent in x 0–23 and x 1057–1079, y 0–911 is None
```

- [ ] **Step 2: Write the fixtures.**
  - `limits-source.txt`: 14 lines, each exactly 40 columns, code-like text with no tab.
  - `brainrot-limits-script.json`: a valid brainrot script (`--check` passes, `provenance.root` set by the test to `skills/explain`) of 6 scenes. Every limited text is exactly at its brainrot limit, in title-case English words with capitals and `m`/`w` where the text allows:
    - **`title`:** title and subtitle at the limit.
    - **`bullets-appear`:** 4 bullets (the validator's maximum), each at the limit.
    - **`diagram-with-highlight-walk`:** 7 nodes (the maximum), every label and sub at the limit, and edge labels of 10 chars (fixed for both formats).
    - **`code-with-line-highlights`:** lines 1–14 of `limits-source.txt`.
    - **`before-after`:** 5 lines per panel and both headings, all at the limit.
    - **A second `title`:** its cue sentence starts with the backticked name `EXPLAIN_BRAINROT_BACKGROUNDS`.
    - **Scene headings:** the four non-`title` scenes each have a heading of 40 chars. It has no limit today.
  - The cue sentence of scene 1 starts with three capitalised words that join to exactly `captionChars` characters.
  - Each scene has ≤ 45 words, ≤ 30 s; the total is ≤ 90 s.

- [ ] **Step 3: Implement `ink_extent` and the `render_brainrot` parameter. Run the tests.**

Run: `cd skills/explain && python3 -B -m unittest tests.test_png_diff && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_brainrot`
Expected: `OK`. The template cases are unchanged.

- [ ] **Step 4: Measure, and start the note.** Render the stress script once more into a kept directory, then read every still with the Read tool:

```bash
EXPLAIN_BRAINROT_SEED=7 skills/explain/scripts/render.sh <kept-dir> --engine say
```

Write the note's first section, "Limits stress render". It holds the full stdout and one table row per limit: limit, value, still, ink box (`ink_extent` over the element's box), fill, and any fault seen. The caption rows are judged by eye on the cue stills, because the background is not white:
- the cap-length chunk is one line at full size;
- the long name is one line in smaller type;
- no caption ink lies over panel content.

- [ ] **Step 5: Commit** — `test: explain: brainrot limits stress render; note: stress measurements`

### Task 5: Live run by a fresh runner (kp-c04 findings 2 and 3)

**Files:**
- Modify: `docs/superpowers/spikes/2026-10-05-explain-brainrot-live-run.md` (runner sections)

**Interfaces:**
- Consumes: the branch skill text at `<skill-dir>` = `/Users/valukin/karpathy-wt/feature/skills/explain`; the clip folder state (see Rulings).

- [ ] **Step 1: The controller pre-declares the expectation in the dispatch brief, before the run.** Read the subject and write down:
  - the scene count and the component of each scene;
  - the code range, measured with the rung's `awk` command at the brainrot column limit;
  - the cue plan;
  - the background (clip name or `generated`).

- [ ] **Step 2: Dispatch the runner** (model: opus; working directory: the worktree). Request:

```
/explain skills/ste/scripts/ste_lint.py --as brainrot
```

  The runner:
  - reads only `<skill-dir>/SKILL.md`, the files it names and `<skill-dir>/../ste/SKILL.md`. It never reads this plan, the tests or the pipeline source. If it opens one, it records why.
  - follows the rung to its handoff, without `open`.
  - writes these note sections, in the shape of `docs/superpowers/spikes/2026-10-04-explain-video-live-run.md`:
    - request and rung line;
    - the expectation compared with the build;
    - every `render.sh` run's full stdout;
    - wall time;
    - the stills read, each with the three brainrot faults of rung §5;
    - three transcript claims spot-checked;
    - duration and narrator;
    - the background line;
    - the defect list;
    - what worked.

  It also records:
  - **Sync margins (finding 2):** the output of `python3 <skill-dir>/video/verify_sync.py <out>/build/rendered-audio.wav <out>/build/timeline.json`. Per scene: the tail silence, `durationInFrames / 30 − last`, and the lead offset.
  - **Render ratio (finding 3):** with a clip, the clip size and duration next to the `render` stage ratio.

- [ ] **Step 3: The controller checks the evidence.**
  - The last run in the note shows ten `ok` lines.
  - The controller reads at least the first still and one cue still of each scene, and compares them with the runner's reading.
  - The margins table has one row per scene.
  - Each defect names a file and a change.

- [ ] **Step 4: Commit** — `docs: explain: brainrot live run on ste_lint.py`

### Task 6: Fold-back

**Files:**
- Modify: `skills/explain/video/formats.json`, `skills/explain/rungs/brainrot.md`, spec §3.4 (dated amendment), the files that the accepted Task 5 defects name (`SKILL.md`, `rungs/video.md` or `rungs/brainrot.md` only), the note

**Interfaces:**
- Consumes: the Task 4 table, the Task 5 margins and defects, and the Tuning rule above.

- [ ] **Step 1: Apply the Tuning rule to every row.** Write the note section "Limit changes": one line per row, `old → new` or `kept`, with its evidence and reason. Each lowered or raised value gets a confirming stress render.
- [ ] **Step 2: Fold the values back.**
  - Edit `formats.json` and the rung table; the drift tests hold them together.
  - Edit the spec §3.4 table. Replace its sentence "The brainrot values are starting values." with the dated line "(Tuned 2026-10-05 in the live run; evidence in `docs/superpowers/spikes/2026-10-05-explain-brainrot-live-run.md`.)".
- [ ] **Step 3: Answer each Task 5 defect.** Fix it in the file it names, or reject it with a reason in the note. The changed skill text lints clean.
- [ ] **Step 4: Verify.**
  - Run the unit suite, then the gated E2E (`EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_brainrot tests.test_short_still tests.test_render tests.test_check_render tests.test_landscape_regression`). Expected: `OK`, and the landscape regression within threshold.
  - Re-render the live-run output directory with `<skill-dir>/scripts/render.sh <out>` (same engine as Task 5). Expected: ten `ok` lines.
  - Read the stills that a changed limit affects.
- [ ] **Step 5: Commit** — `feat: explain: brainrot limits tuned from the live run`

### Task 7: User acceptance on a phone, and wave close

**Files:**
- Modify: the note (section "Acceptance"), `docs/superpowers/waves/2026-10-04-explain-brainrot.yaml`

- [ ] **Step 1: Hand the user** the path of the final `video.mp4`, the narrator and the background.
- [ ] **Step 2: The user watches it on a phone.** Their words go verbatim into the note. A fault they name goes back through Task 6, Steps 3–5, and they watch again.
- [ ] **Step 3: Close the wave.**
  - Map: `status: done` with the commit range.
  - br: close the task issues and `kp-c04` with the SHA and evidence. File one follow-up issue for finding 4.
- [ ] **Step 4: Commit** — `chore: close wave brainrot-live-run`. Then `superpowers:finishing-a-development-branch`, once, for the whole feature.
