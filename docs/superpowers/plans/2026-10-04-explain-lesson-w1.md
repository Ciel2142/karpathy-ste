# Explain lesson — wave `lesson-page` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The page tooling knows the lesson rung: `verify.sh` accepts `rung=lesson` and checks its media files, and the page template carries the clip CSS, the `Play all` control and a guard rule for its visibility.

**Architecture:** Two files change behavior, `scripts/verify.sh` (a sixth check, `media`, fed by its existing HTML scanner) and `templates/page.html` (CSS, one button, one script addition in block 2, one guard rule in block 3). `rungs/page.md` documents the new primitive and the hint line. No new runtime files; the markup of a clip lives in the rung docs, not in the template (spec D5).

**Tech Stack:** bash + Python `html.parser` (verify.sh), plain CSS/JS in a single HTML template, `unittest` with headless Chrome through `verify.sh`.

Base: 8ca7735618c3106040223f0ddaa2ba643b9c6700
Test runs: scoped per task; full suite once, final task.

**Spec:** `docs/superpowers/specs/2026-10-04-explain-lesson-design.md` — this wave implements §3.2, §4.2 (markup, width), §4.3, §4.4, §6.3, the `page.md`/template items of §6.4, §7.2 and the template part of §7.3. Wave map: `docs/superpowers/waves/2026-10-04-explain-lesson.yaml`.

## Global Constraints

- Branch base: `feat/explain-lesson`, cut from `feat/explain-brainrot` after wave brainrot-render closes (spec §6.5). Do not start on `main`.
- Files this wave may change: `skills/explain/scripts/verify.sh`, `skills/explain/templates/page.html`, `skills/explain/rungs/page.md`, `skills/explain/tests/test_verify.py`, `skills/explain/tests/test_page_template.py`, new fixtures under `skills/explain/tests/fixtures/`. Nothing else (wave ownership).
- `templates/page.html` must pass `verify.sh` as it stands, with `content="page"` and five `ok` lines (`test_template_passes_all_five_checks`).
- Script block 2 of the template (the `explainPlayer` block) stays within 200 lines (`SCRIPT_BUDGET`); blocks 1 and 3 are the guard and keep their shape: block 3 runs once in `load`, no timers, and writes `data-verify` through one `doc.setAttribute` call.
- Every element with its own text has a computed font size of 14 px or more (guard `SMALLTEXT`); no horizontal overflow at 1440 or 500 px (guard `HSCROLL`).
- The palette block of the template stays identical to `sheet.html` (`test_palette_block_identical_to_sheet`).
- `verify.sh` prints one line per check and nothing else on stdout; detail lines are indented by two spaces; every check runs even after an earlier one failed; exit 1 on any FAIL, exit 2 on usage.
- All prose written into docs follows the STE profile; conversation and commits in English.
- Commits: `<type>: <description>`, ending with the attribution line of this session.

## Review Focus

1. Real browsers with a visible vertical scrollbar: `100vw` includes the scrollbar, so a breakout width of `min(960px, 100vw - 32px)` can overflow by the scrollbar width at narrow widths and trip `HSCROLL` in a real window while headless Chrome (no scrollbar) passes. Expected: no horizontal scroll at any width. Test pinned in Task 3 (500 px headless render passes); the live run of wave `lesson-live-run` must also check a real narrow window.
2. `video.play()` returns a promise that rejects when the browser blocks playback (a chained clip after the reader's first click is normally allowed, but not guaranteed). `window.onerror` does not see a rejected promise, so a run would stall silently. Expected: a rejected `play()` is treated as `error` and the run skips to the next clip. Pinned in Task 4 (the handler attaches `.catch` to `play()`; static assertion).
3. `href="./clips/x/index.html"` or `href="clips/x/"`: the spec says "starts with `clips/`" and "existing regular file". Expected: a leading `./` is stripped before the prefix test, and a directory is `missing`. Pinned in Task 2.
4. A lesson whose author deleted the `Play all` button while clips exist: the control is gone and nothing reports it. Expected: `PLAYALL` from the guard. Pinned in Task 3.
5. A `<video>` whose `src` is remote on a lesson page: check 1 already fails it; the media check must not count it a second time as `missing`. Expected: only relative references reach the media check. Pinned in Task 2.

---

### Task 1: `verify.sh` accepts `rung=lesson`

**Files:**
- Modify: `skills/explain/scripts/verify.sh:277-283` (the `case "$rung_line"` switch), `:1-21` (header comment)
- Test: `skills/explain/tests/test_verify.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `rung=lesson` runs the page viewports `1440x900 500x844`; the usage text for an unknown rung reads `(expected sheet, page, video or lesson)`.

- [ ] **Step 1: Write the failing tests**

In `test_verify.py`:
- `test_unknown_rung_message_lists_lesson`: derive from `verify-good.html` with `content="poster"`; assert exit 2 and `"(expected sheet, page, video or lesson)" in proc.stderr`.
- `test_lesson_rung_renders_the_page_viewports`: derive from `verify-good.html` with `content="lesson"`; assert exit 0 and that stdout contains the lines `render 1440x900: ok` and `render 500x844: ok` (do not assert the full line list yet; Task 2 adds the sixth line).

Update `test_unknown_rung_is_a_usage_error` to the new expected text.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_verify -k lesson -k unknown_rung -v`
Expected: the two new tests FAIL (exit 2 with `unknown rung "lesson"`; old text in the message); the updated old test FAILS on the text.

- [ ] **Step 3: Add the `rung=lesson` case**

In the `case` switch add `rung=lesson) viewports="1440x900 500x844" ;;` and change the `*)` usage text to `(expected sheet, page, video or lesson)`. In the header comment, line 1 and the `exit 0` line: "sheet, page: four; lesson: five; video: three" (the `media` check that Task 2 adds is the fifth check of a lesson; renders count as one check).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_verify -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/verify.sh skills/explain/tests/test_verify.py
git commit -m "feat: explain: verify.sh accepts rung=lesson with the page viewports"
```

### Task 2: the `media` check

**Files:**
- Modify: `skills/explain/scripts/verify.sh` (scanner at `:124-203`, bash after check 4 at `:370`, header comment stdout contract `:11-21`)
- Create: `skills/explain/tests/fixtures/verify-lesson.html`
- Test: `skills/explain/tests/test_verify.py`

**Interfaces:**
- Consumes: Task 1's `rung=lesson` branch.
- Produces: a sixth stdout line for `rung=lesson`, after `prose`: `media: ok` or `media: FAIL <n> missing`, with one detail line per missing reference, `  <tag> <attr>=<value>` (`<value>` as written in the HTML, whitespace-collapsed). Exit code 1 on FAIL. The scanner's output protocol gains lines `media-missing <tag> <attr>=<value>`, one per missing reference, which the bash side separates from the remote-reference lines; `refs` for check 1 excludes them. Pages of other rungs print no `media` line.

- [ ] **Step 1: Write the fixture**

`tests/fixtures/verify-lesson.html`: copy `verify-good.html`, set `content="lesson"`, and add inside the section this exact figure (spec §4.2):

```html
<figure class="clip">
  <video controls preload="none" src="clips/intro/video.mp4" poster="clips/intro/poster.png"></video>
  <figcaption><span class="part"></span>The parser reads one tag at a time.
    <a href="clips/intro/index.html" data-ste="skip">transcript</a></figcaption>
</figure>
```

The fixture needs no CSS for the figure; the render checks only measure text size and overflow.

- [ ] **Step 2: Write the failing tests**

Add to `test_verify.py` a helper `write_clip(self, *names)` that creates `clips/intro/<name>` files (one byte each) under `self.work`, and these tests. Each runs `verify_fixture("verify-lesson.html", ...)` after writing the clip files it needs.

- `test_lesson_with_media_prints_six_ok_lines`: all three files present → exit 0, stdout equals the six lines `self-contained: ok`, `render 1440x900: ok`, `render 500x844: ok`, `citations: ok`, `prose: ok`, `media: ok`.
- `test_lesson_missing_poster_fails_media_with_a_detail_line`: `video.mp4` and `index.html` present, no `poster.png` → exit 1; the first five lines `ok`; then `media: FAIL 1 missing` and `  video poster=clips/intro/poster.png`.
- `test_lesson_media_strips_fragment_query_and_decodes`: edit the fixture so the `href` is `clips/intro/index.html#scene-1?x=1` and the poster is `clips/intro/poster%20a.png`; create `poster a.png` → `media: ok`.
- `test_lesson_media_strips_dot_slash_and_rejects_a_directory`: edit `href` to `./clips/intro/` (a directory) with all files present → `media: FAIL 1 missing`, detail `  a href=./clips/intro/`.
- `test_lesson_without_clips_passes_media`: edit the fixture to remove the whole `<figure class="clip">…</figure>` → six `ok` lines.
- `test_lesson_remote_video_src_counts_once`: edit `src` to `https://x.test/v.mp4` with the other files present → `self-contained: FAIL 1 remote reference(s)` and `media: ok` (a remote value is not a media reference).
- `test_page_rung_prints_no_media_line`: run `verify-good.html` with `content="page"` → five lines, no `media`.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_verify -k media -k six_ok -v`
Expected: FAIL (no `media` line in stdout).

- [ ] **Step 4: Implement the media check**

Scanner (Python, inside `scan()`): collect `(tag, attr, value)` for every `video` `src` and `poster`, and every `a` `href` whose value, after stripping leading whitespace and a leading `./`, starts with `clips/`. Skip a value that `remote()` accepts. For each: cut at the first `#` or `?`, `urllib.parse.unquote`, resolve against `os.path.dirname(sys.argv[1])`; print `media-missing <tag> <attr>=<value>` when `os.path.isfile()` is false. Print these after the remote references.

Bash: `refs` becomes the scanner lines 3+ without the `media-missing ` prefix lines; `media_missing` is the lines with it, prefix removed. After check 4, only when `rung_line` is `rung=lesson`: print `media: ok` or `media: FAIL <n> missing` plus the detail lines through `indent`, and set `failed=1`. Add the `media:` line and the detail format to the header's stdout contract.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_verify -v`
Expected: all PASS, including every pre-existing case.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/scripts/verify.sh skills/explain/tests/test_verify.py skills/explain/tests/fixtures/verify-lesson.html
git commit -m "feat: explain: verify.sh media check for the lesson rung"
```

### Task 3: clip CSS, `Play all` button and the `PLAYALL` guard rule

**Files:**
- Modify: `skills/explain/templates/page.html` — `<style>` (after the header/nav rules at `:66-76`), `<header>` at `:167-170`, guard block 3 (before `if (window.explainJsErrors > 0)` at `:506`), the head comment `:12-23`
- Test: `skills/explain/tests/test_page_template.py`

**Interfaces:**
- Consumes: nothing.
- Produces: classes `figure.clip`, `.clip video`, `.clip .part`; element `<button id="play-all" type="button">Play all</button>` in `<header>` after the lead paragraph; CSS `body:not(:has(figure.clip)) #play-all { display: none; }`; guard token `PLAYALL` in `data-verify` when (clips exist and `#play-all` is absent or `display: none`) or (no clips and `#play-all` is shown). Task 4 attaches behavior to `#play-all`.

- [ ] **Step 1: Write the failing tests**

In `test_page_template.py`, with anchors that occur once in the template:

- `test_template_hides_play_all_without_clips`: the template as it stands passes (the existing `test_template_passes_all_five_checks` covers the pass; this test asserts the CSS rule text `body:not(:has(figure.clip)) #play-all { display: none; }` occurs once and `id="play-all"` occurs once).
- `test_deleting_the_hide_rule_reports_playall`: delete the hide rule → `assert_both_fail(html, "PLAYALL")`.
- `test_clip_without_button_reports_playall`: insert the fixture figure of Task 2 step 1 after the lead paragraph of the first section and delete the button → `PLAYALL` at both viewports.
- `test_clip_with_button_passes`: insert the same figure, keep the button → `assert_renders(html, RENDER_OK, 0)`. The two `render … ok` lines also prove the clip's text is 14 px or more and that the breakout width adds no horizontal overflow at 500 px (the figure's relative paths are not remote; `content="page"` runs no media check).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_page_template -k play_all -k playall -k clip -v`
Expected: FAIL (rule and button absent; no `PLAYALL` token).

- [ ] **Step 3: Implement**

CSS values: `figure.clip` breaks out of the column to `width: min(960px, calc(100vw - 32px))`, centered under the 72ch body (choose the centering technique; it must not widen `scrollWidth`), `margin: 16px auto`; `.clip video { display: block; width: 100%; background: #000; }`; `.clip .part { font-weight: 600; margin-right: 8px; }` (inherits `figcaption` 14 px); `#play-all` styled like the player buttons, 15 px; the hide rule as in Produces.

Guard rule in block 3, before the `JSERROR` push: `clips` = the count of `figure.clip`; `shown` =
`#play-all` exists and `getComputedStyle(it).display !== "none"`; push `"PLAYALL"` when
`(clips > 0) !== shown`. The token follows the guard's convention (`HSCROLL`, `SMALLTEXT`,
`JSERROR`); it is the status that spec §7.3 calls `play-all-visibility`.

Head comment: add one line, "Clips (lesson rung): figure.clip markup is in rungs/lesson.md; keep #play-all."

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_page_template -v`
Expected: all PASS, including `test_template_passes_all_five_checks`, `test_palette_block_identical_to_sheet`, `test_script_budget_at_most_200_lines`.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/templates/page.html skills/explain/tests/test_page_template.py
git commit -m "feat: explain: page template clip styles, Play all button and PLAYALL guard"
```

### Task 4: `Play all` behavior in script block 2

**Files:**
- Modify: `skills/explain/templates/page.html` script block 2 (after `explainPlayer`, before its `</script>`)
- Test: `skills/explain/tests/test_page_template.py`

**Interfaces:**
- Consumes: `#play-all`, `figure.clip`, `.clip .part` from Task 3.
- Produces: `function explainPlayAll()` in block 2, marked by the comment `/* Play all */`, invoked once at the end of the block. Behavior (spec §4.3): collects `figure.clip video` in document order and returns when there are none; a click on `#play-all` ends any run and starts one from clip 1; a run plays the current clip, scrolls its `section` into view (`scrollIntoView({block: "start"})`), writes `Part k of N` into that figure's `.part`; `ended` clears the label and starts the next, after the last the run ends; `error`, or a rejected `play()` promise, clears the label and skips to the next; `pause` on the running clip, or `play` on any other clip, ends the run; the end of a run clears every `.part`. No `autoplay` attribute; no timers.

- [ ] **Step 1: Write the failing tests**

- `test_play_all_block_is_in_block_2_within_budget`: `script_lines(html)` block 2 contains `/* Play all */` and `function explainPlayAll(`, and the block has at most 200 lines; blocks 1 and 3 do not contain `explainPlayAll`.
- `test_play_all_handles_a_rejected_play_promise`: block 2 contains `.play()` followed by `.catch(` within the same statement (regex `\.play\(\)\s*\.catch\(`); and contains no `autoplay`.
- `test_page_with_clips_has_no_jserror`: the Task 3 figure inserted, button kept → `assert_renders(html, RENDER_OK, 0)` (a throwing `explainPlayAll` would report `JSERROR`).
- `test_play_all_is_hidden_in_a_plain_page_with_the_probe`: with `with_probe`, the dump shows `data-verify="OK"` and no `PLAYALL` (the existing probe path; the rule from Task 3 holds with the new script present).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_page_template -k play_all -v`
Expected: the first two FAIL (no marker, no function).

- [ ] **Step 3: Implement `explainPlayAll()`**

Signature: `function explainPlayAll() {}` with no parameters and no return value; invoke it once as the last statement of block 2. State: an index of the running clip or `-1`. One listener per video for `ended`, `error`, `pause`, `play`; one on the button for `click`. The `pause` listener ignores the pause that `ended` fires (check `video.ended`).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_page_template -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/templates/page.html skills/explain/tests/test_page_template.py
git commit -m "feat: explain: Play all runs a lesson's clips in document order"
```

### Task 5: `rungs/page.md` — clip criterion, hint line, primitive, block names

**Files:**
- Modify: `skills/explain/rungs/page.md` section 2 (`:12-25`), section 3 table (`:36-41`) and step 3 (`:30-33`)

**Interfaces:**
- Consumes: the Task 2 markup and the Task 3/4 template facts.
- Produces: documentation only. Wave `lesson-rung` reads this file as the page half of the lesson rung.

- [ ] **Step 1: Edit section 2**

Add two bullets after "Decide which diagram pattern each flow uses": the criterion of spec §3.2, copied verbatim ("A section would gain from a clip when narration plus motion explains it better than a static view: a flow, a structure that builds up, a before and after, a camera move along code, a comparison whose terms change."), and the rule: when the plan is written and at least one section meets it, print `<n> sections would gain from a clip; rerun with --as lesson`, then build the page as before.

- [ ] **Step 2: Edit section 3**

Table: add the row `| clip (lesson rung only) | figure.clip > video[controls][preload=none] + figcaption > span.part, one sentence, a[data-ste=skip] "transcript" | A narrated clip of this section; markup in rungs/lesson.md. |`. Step 3: after "all three script blocks" add "(block 1 and 3: the guard; block 2: the steps player and Play all)". Add: "A plain page keeps the `Play all` button; CSS hides it when the page has no `figure.clip`."

- [ ] **Step 3: Verify**

Run: `grep -c "rerun with --as lesson" skills/explain/rungs/page.md && grep -c "figure.clip" skills/explain/rungs/page.md`
Expected: `1` and `2` or more. Run the STE lint on the changed prose: `python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/page.md` — expected `0 errors` in the summary line (warnings allowed, as for the rest of the file).

- [ ] **Step 4: Commit**

```bash
git add skills/explain/rungs/page.md
git commit -m "docs: explain: page rung names the clip primitive and the lesson hint line"
```

---

## Wave close

Run: `cd skills/explain && python3 -B -m unittest tests.test_page_template tests.test_verify -v`
Expected: all PASS. Then the full suite: `cd skills/explain && python3 -B -m unittest discover -s tests` — all PASS. Update the wave map: `lesson-page` `status: done` with the commit range.
