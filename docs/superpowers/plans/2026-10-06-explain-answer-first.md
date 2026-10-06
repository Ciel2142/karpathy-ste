# Explain — answer-first pages and the Sources switch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A page or lesson built from `templates/page.html` opens with an answer box, hides its cite blocks behind a Sources switch in the sticky nav, and fails `verify.sh` when the box or the switch is missing or when a hidden cite would overflow or be too small. The rung files teach the answer-first page shape.

**Architecture:** The cite markup and `cite_check.py` stay as they are. Only the view changes: CSS hides `div.cites`, and a `:has` rule shows it when `#show-sources` is checked. Guard part 2 measures twice, first in the reading view and then with the switch on, and gains two codes. The rules go into `rungs/page.md`, with one line each in `SKILL.md`, `rungs/lesson.md` and `lesson/review-page.md`.

**Tech Stack:** HTML, CSS (`:has`) and inline JS in the template; Python 3 stdlib `unittest`; bash `verify.sh` with headless Chrome; Markdown rung files linted by `skills/ste/scripts/ste_lint.py`.

**Spec:** `docs/superpowers/specs/2026-10-06-explain-answer-first-design.md` (approved 2026-10-06).

Base: `main` at 32cb771. The spec commit 33acf7c is on the branch. There is one cohesive wave and no wave map. It is high risk, because it changes the `data-verify` contract that `verify.sh` and the tests read. Coverage: not opted in.
Test runs: scoped per task. The full suite and the gated lesson E2E run once, in Task 7.

## Global Constraints

- **Branch.** Work on `feat/explain-answer-first`. Never commit to `main`. Never stage or commit `.beads/`.
- **Running tests.**
  - Run every test command from `skills/explain`, as `python3 -B -m unittest tests.<module>[.<Class>.<test>]`.
  - Put the output of each command that takes more than 2 minutes in a log file under `/tmp`: `test_page_template` in full, the full suite, and the lesson E2E. Poll the log with short `sleep 30; tail` calls until `OK` or `FAILED`. Never end a turn to wait for a notification.
- **Stdlib only.** No npm, no pip, no new dependency.
- **The template.** It stays one self-contained file: inline CSS and JS, system fonts, no CDN. The script budget is 200 lines (`SCRIPT_BUDGET`; 140 at base). The font floor is 14 px. Add no new `:root` colour; the palette tests pin eight tokens in four files.
- **The template has no file cite.** Its cites are URL cites only. The BPMN plan's decision 8 relies on this.
- **Markup that stays.** The cite markup (`div.cites` > `cite[data-path][data-line][data-snippet]` with `name:line <code>snippet</code>`) does not change, and neither does `scripts/cite_check.py`. Neither do `templates/sheet.html` and `templates/video.html`.
- **`data-verify` codes,** in this order, joined by `;`: `HSCROLL`, `SMALLTEXT:<px>`, `PLAYALL`, `NOANSWER`, `NOSOURCES`, `JSERROR`. `JSERROR` stays last.
- **Lint.** `rungs/page.md`, `rungs/lesson.md` and `SKILL.md` stay at `0 errors, 0 warnings`. `lesson/review-page.md` is at `4 errors, 3 warnings` at base and gets no new finding.
- **Section titles.** Keep each level-2 title of `page.md`. `PAGE_TITLES` in `test_lesson_prompts.py` must each match one heading.
- **Style.** Code comments and test docstrings follow each file's style: short plain sentences. Each test says which mutation turns it red (`red:` comment or docstring).
- **Commits.** Commit messages are `<type>: explain: <description>`, and end with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A page with no cite at all,** such as a topic from model knowledge. Expected: no `NOSOURCES`, and the switch may be absent. Pinned by `test_page_without_cites_needs_no_switch` (Task 1).
2. **A reader who turned Sources on and reloads.** The browser restores the checkbox, so it is on at `load`. Expected: after the second measure, the guard sets the switch back to the state it had before, not to off. Pinned by `test_guard_restores_a_checked_switch` (Task 1).
3. **A cite block inside a closed `details.walk`,** in a reference fold. Expected: under `#verify` the guard opens every `details` first, so the second measure includes these cites. Pinned by `test_hidden_cite_in_a_fold_is_measured` (Task 1).
4. **Two missing parts at once.** Expected: one `data-verify` that holds `NOANSWER;NOSOURCES` in this order. Pinned by `test_missing_box_and_switch_report_in_order` (Task 2).
5. **A lesson page built from the template** (`lesson_page` in `test_lesson_e2e.py`). Expected: it inherits the box and the switch and passes. Its five anchors still occur once each. Pinned by the gated lesson E2E run (Task 7).

## Beyond the letter of the spec (decisions made with no user present)

1. **The check texts of `test_lesson_prompts` stay unpinned.** Spec 8 says "check 2 names the answer box". The module docstring of `test_lesson_prompts.py` says "The text of a check is not pinned here". Task 5 keeps that design: `CHECK_COUNT[PAGE]` stays 3, and the existing test enforces it. The new wording of check 2 is pinned in `test_rung_drift.py`, next to the other text pins.
2. **The demo glossary holds no cite block.** Its terms come from `SKILL.md`, and the template may hold no file cite. Spec 2 rule 7 says each `dd` ends with its `div.cites`. An HTML comment in the demo gives that markup, as the template already does for the cite pattern.
3. **The answer box of the template cites the STE URL** that the template already cites. Its answer names the STE-80 prose rule, so the cite supports a real claim. This meets spec 6, "its cite is a URL".
4. **New text pins and lint pins go in a new `PageRungCase`** in `test_rung_drift.py`. Today the lint is pinned only for `video.md`.

## File Structure

| File | Responsibility |
|---|---|
| `skills/explain/templates/page.html` | CSS for the hidden cites, the switch, print, `.answer` and `dl.terms`. Header with the question `<h1>` and the answer box. The switch in the nav. The demo glossary section. Guard: two measures, `NOANSWER`, `NOSOURCES`. The status table. |
| `skills/explain/tests/test_page_template.py` | Chrome cases for the new codes and for the measure of hidden cites. Static pins for the CSS, the header, the nav and the glossary. |
| `skills/explain/rungs/page.md` | The page-shape rules, the Keep list, the primitives, the lint notes, the self-check |
| `skills/explain/SKILL.md` | One sentence in convention 2 |
| `skills/explain/rungs/lesson.md` | "Plan the lesson" step 3 |
| `skills/explain/lesson/review-page.md` | Check 2, and the stale cite sentence |
| `skills/explain/tests/test_rung_drift.py` | New `PageRungCase`: text pins and lint pins for the rule files |
| `docs/superpowers/plans/2026-10-06-explain-bpmn.md`, `docs/superpowers/specs/2026-10-06-explain-bpmn-design.md` | The amendments of spec 7 |

---

### Task 1: The Sources switch, and the guard measures hidden cites

**Files:**
- Modify: `skills/explain/templates/page.html`: style (font-size lists `:40-51`, the `.cites` rules, a print rule); `nav#toc` (`:202-211`); guard part 2 (`:566-588`); the status table (`:405-414`)
- Test: `skills/explain/tests/test_page_template.py`

**Interfaces:**
- Produces:
  - The switch markup, which is the last child of `nav#toc`: `<label class="sources"><input type="checkbox" id="show-sources"> Sources</label>`.
  - The CSS contract:
    - `div.cites` has `display: none`.
    - `body:has(#show-sources:checked) .cites { display: block; }` shows it.
    - `@media print` shows it too.
  - The guard code `NOSOURCES`, between `PLAYALL` and `JSERROR`.
  - A test anchor for later tasks: the switch line, `SWITCH = '<label class="sources"><input type="checkbox" id="show-sources"> Sources</label>'`, defined as a module constant.

- [ ] **Step 1: Write the failing tests** in `PageGuardTest`, as Chrome runs through `verify.sh` unless marked static.

```python
def test_hidden_cite_with_12px_snippet_reports_smalltext_12(self):  # a style rule `.cites code { font-size: 12px; }` → assert_both_fail(html, "SMALLTEXT:12")
def test_hidden_cite_700px_wide_reports_hscroll_at_500_only(self):  # a 700 px unbreakable span inside the template's div.cites → 1440 ok, 500 'FAIL data-verify="HSCROLL"'
def test_hidden_cite_in_a_fold_is_measured(self):  # the 12 px rule scoped to `details.walk .cites code`, a URL cite block inside the first details.walk → SMALLTEXT:12 on both
def test_switch_removed_reports_nosources(self):  # SWITCH line deleted from the nav → assert_both_fail(html, "NOSOURCES")
def test_page_without_cites_needs_no_switch(self):  # every div.cites block and the SWITCH deleted → five ok lines
def test_guard_restores_a_checked_switch(self):  # a parse-time script sets #show-sources.checked = true; the probe sees it still checked when the guard writes data-verify
def test_switch_is_in_the_nav_and_cites_hide_by_default(self):  # static: SWITCH once, inside nav#toc, after the last <a>; style holds the display:none rule for .cites, the :has rule, an @media print rule that shows .cites
def test_label_and_input_have_explicit_font_sizes(self):  # static: `label` and `input` each appear in a font-size rule of 14 px or more
def test_status_table_lists_nosources(self):  # static: a status-table row whose first cell is <code>NOSOURCES</code>
```

- `test_guard_restores_a_checked_switch` extends the `PROBE` of the module. The probe records the `checked` state of `#show-sources` at the moment of the write, in the same way it records the rest of the DOM state.
- The 12 px cases plant their rule before `</style>`, as `test_13px_rule_reports_smalltext_13` does.
- Each case edits the template with `self.edit` on an anchor that occurs once.

- [ ] **Step 2: Run the static cases and the switch case, and confirm that they fail**

Run: `python3 -B -m unittest tests.test_page_template.PageGuardTest.test_switch_removed_reports_nosources tests.test_page_template.PageGuardTest.test_switch_is_in_the_nav_and_cites_hide_by_default tests.test_page_template.PageGuardTest.test_label_and_input_have_explicit_font_sizes`
Expected: all three FAIL. The `SWITCH` anchor and the rules are missing.

The three hidden-cite cases (12 px, 700 px, in a fold) pass at base, because the cites are visible
there. They turn red only when the hide rule lands without the second measure. Step 3a proves this.

- [ ] **Step 3a: Add the view, and watch the guard go blind**
  - **Style:**
    - Add `display: none` to the existing `.cites { … }` rule.
    - Add `body:has(#show-sources:checked) .cites { display: block; }`.
    - Add `@media print { .cites { display: block; } }`.
    - Add `nav#toc .sources { margin-left: auto; color: var(--muted); cursor: pointer; }`.
    - Put `label` and `input` into the explicit font-size lists at 14 px or more. `nav label` matches `nav a` at 15 px.
  - **Nav:** put `SWITCH` on its own line, as the last child of `nav#toc`, after `<a href="#provenance-facet">Provenance</a>`.

Run: `python3 -B -m unittest tests.test_page_template.PageGuardTest.test_hidden_cite_with_12px_snippet_reports_smalltext_12 tests.test_page_template.PageGuardTest.test_hidden_cite_in_a_fold_is_measured`
Expected: both FAIL with `render 1440x900: ok`, where `FAIL data-verify="SMALLTEXT:12"` was expected. This is the blind spot that the reviewer found. If they pass here, the planted rule does not reach a hidden cite: fix the test.

- [ ] **Step 3b: Teach the guard to measure with the switch on**
  - **Guard part 2:**
    - Put the `HSCROLL` and `SMALLTEXT` measure (`:568-581`) in one local function. It returns whether the page is wider than the window and the smallest text size.
    - Call it in the reading view. Then, if `#show-sources` exists, save its `checked`, set it to `true`, and call the function again. Then restore the saved value.
    - Push `HSCROLL` once if either call saw it. Push `SMALLTEXT` with the smaller size of the two calls.
    - After `PLAYALL`, push `NOSOURCES` when `document.querySelector(".cites")` exists and `document.querySelector('nav#toc input#show-sources[type="checkbox"]')` does not.
    - The `--nav-h` line stays where it is.
  - **Status table:** add a `NOSOURCES` row before `JSERROR`: "The page has a cite block, and the nav has no Sources switch."

- [ ] **Step 4: Run the module.** It takes more than 2 minutes, so log it and poll.

Run: `python3 -B -m unittest tests.test_page_template > /tmp/apt-t1.log 2>&1; tail -3 /tmp/apt-t1.log`
Expected: `OK`. `test_template_passes_all_five_checks` stays green. The template has cites and the switch.

- [ ] **Step 5: Update the module docstring.** It counts the Chrome runs and lists the cases. Add the six new Chrome cases.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/templates/page.html skills/explain/tests/test_page_template.py
git commit -m "feat: explain: cites hide behind a Sources switch in the nav; the guard measures them and reports NOSOURCES"
```

---

### Task 2: The answer box and NOANSWER

**Files:**
- Modify: `skills/explain/templates/page.html`: style (`.answer`); header (`:194-199`); guard part 2; the status table
- Test: `skills/explain/tests/test_page_template.py`

**Interfaces:**
- Consumes: `SWITCH` (Task 1), and the two-measure guard (Task 1).
- Produces:
  - The header contract:
    - The `<h1>` is a question.
    - `p.lead` is gone.
    - `<div class="answer">` holds one `<p>` that starts with `<strong>Short answer.</strong>`, and then one `div.cites` with the STE URL cite.
  - The guard code `NOANSWER`, between `PLAYALL` and `NOSOURCES`.
  - A test anchor: `ANSWER`, the whole `<div class="answer">…</div>` block of the template, defined as a module constant.

- [ ] **Step 1: Write the failing tests** in `PageGuardTest`.

```python
def test_answer_box_removed_reports_noanswer(self):  # ANSWER deleted → assert_both_fail(html, "NOANSWER")
def test_blank_answer_box_reports_noanswer(self):  # the <p> of ANSWER replaced by "<p> \n </p>" → NOANSWER
def test_answer_box_with_only_cites_reports_noanswer(self):  # the <p> of ANSWER deleted, its div.cites kept → NOANSWER
def test_answer_box_outside_header_reports_noanswer(self):  # ANSWER moved from <header> to just after the first <h2> → NOANSWER
def test_missing_box_and_switch_report_in_order(self):  # ANSWER and SWITCH deleted → assert_both_fail(html, "NOANSWER;NOSOURCES")
def test_header_asks_and_answers(self):  # static: the <h1> text ends with "?"; no 'class="lead"' in the template; ANSWER once, inside <header>, its <p> starts with "<strong>Short answer.</strong>" and is followed by a div.cites
def test_status_table_lists_noanswer(self):  # static: a status-table row whose first cell is <code>NOANSWER</code>, before the NOSOURCES row
```

- Change `test_13px_rule_reports_smalltext_13`: the planted rule `p.lead { font-size: 13px; }` becomes `.answer p { font-size: 13px; }`. The expected status stays `SMALLTEXT:13`.

- [ ] **Step 2: Run the new cases, and confirm that they fail**

Run: `python3 -B -m unittest tests.test_page_template.PageGuardTest.test_answer_box_removed_reports_noanswer tests.test_page_template.PageGuardTest.test_header_asks_and_answers`
Expected: both FAIL. The `ANSWER` anchor is missing, and the header still has `p.lead`.

- [ ] **Step 3: Change the template**
  - **Header:**
    - The `<h1>` becomes "How do you build a page from this template?", and `<title>` matches it.
    - `div.answer` replaces `p.lead`. Its `<p>` starts with `<strong>Short answer.</strong>` and has two to four sentences, at most 70 words, that answer the `<h1>`: copy the file, write the answer here, give one section to each question of the answer, write in STE-80, and run `verify.sh`.
    - Its `div.cites` holds the same `ASD-STE100` URL cite as the structure section.
    - Keep the `Play all` button on its own line, unchanged (the `PLAY_ALL` anchor).
  - **Style:**
    - `.answer` gets a fill, a 4 px accent left border and padding, as in the v2 page (`out/2026-10-06-172738-page-what-are-the-gates-for-v2/index.html`, the v2 CSS block).
    - `.answer p` is 18 px.
    - `.answer .cites` uses the page ground, so that the cite block stands out from the fill.
  - **Guard:** after `PLAYALL`, push `NOANSWER` when `header .answer` is missing, or when its text outside its `.cites` descendants is only white space. The check is null-safe: a missing box never throws.
  - **Status table:** add a `NOANSWER` row before `NOSOURCES`: "The header has no answer box, or the box has no text outside its cites."

- [ ] **Step 4: Run the module (log and poll)**

Run: `python3 -B -m unittest tests.test_page_template > /tmp/apt-t2.log 2>&1; tail -3 /tmp/apt-t2.log`
Expected: `OK`. The prose line stays `prose: ok`: the lint reads the `<p>` of the answer box.

- [ ] **Step 5: Update the docstring** with the five new Chrome cases.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/templates/page.html skills/explain/tests/test_page_template.py
git commit -m "feat: explain: the page header asks a question and answers it; the guard reports NOANSWER"
```

---

### Task 3: The glossary pattern

**Files:**
- Modify: `skills/explain/templates/page.html`: style (`dl.terms` and its narrow rule); nav; a new `<section id="terms">` before `<section id="provenance-facet">`
- Test: `skills/explain/tests/test_page_template.py`

**Interfaces:**
- Consumes: `SWITCH` (Task 1). The switch stays the last child of the nav.
- Produces:
  - The glossary contract: `<section id="terms">`, with the `<h2>` "What do the terms mean?", then `<dl class="terms">` with `dt` and `dd` pairs.
  - The nav entry `<a href="#terms">Terms</a>`, just before the provenance link.

- [ ] **Step 1: Write the failing test**

```python
def test_template_has_a_glossary_section(self):  # static: section#terms exists before section#provenance-facet and holds a dl.terms with at least two dt/dd pairs; the nav has <a href="#terms"> before <a href="#provenance-facet">; the style holds a .terms rule and a max-width media rule that sets one column
```

- [ ] **Step 2: Run it, and confirm that it fails**

Run: `python3 -B -m unittest tests.test_page_template.PageGuardTest.test_template_has_a_glossary_section`
Expected: FAIL, because there is no `section#terms`.

- [ ] **Step 3: Add the glossary**
  - **The section:**
    - It defines two or three terms of the template, from `SKILL.md`: facet, rung, guard.
    - The definitions are in STE-80 and hold no cite (decision 2).
    - An HTML comment above the `dl` says that each `dd` ends with its `div.cites`, as the last child, in the cite pattern of the structure section.
  - **The CSS:**
    - `.terms` is a grid of two columns, `max-content 1fr`.
    - `.terms dt` is bold at 16 px. `dt` is at 14 px in the base list, so set it explicitly.
    - Under `max-width: 560px`, there is one column.

- [ ] **Step 4: Run the module (log and poll)**

Run: `python3 -B -m unittest tests.test_page_template > /tmp/apt-t3.log 2>&1; tail -3 /tmp/apt-t3.log`
Expected: `OK`. The good-template run keeps `prose: ok`: the lint reads `dt` and `dd`.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/templates/page.html skills/explain/tests/test_page_template.py
git commit -m "feat: explain: a glossary pattern (dl.terms) in the page template"
```

---

### Task 4: The page-shape rules in `rungs/page.md`

**Files:**
- Modify: `skills/explain/rungs/page.md`: section 2 "Plan the sections" (`:15-36`); section 3 "Fill the template" (`:38-64`); section 6 "Write the prose" (`:112-130`); section 7 "Verify and export" (`:132-160`)
- Test: `skills/explain/tests/test_rung_drift.py`, new `PageRungCase`

**Interfaces:**
- Consumes:
  - The markup names of Tasks 1 to 3: `div.answer`, `#show-sources`, `label.sources`, `dl.terms`, `section#terms`.
  - The codes `NOANSWER` and `NOSOURCES`.
- Produces: the rule text that Task 5 and the BPMN amendment (Task 6) refer to. This includes the first-section sentence, verbatim, from spec 2 rule 3.

- [ ] **Step 1: Write the failing tests** in a new `PageRungCase(unittest.TestCase)`

```python
def test_page_md_lints_clean(self):  # lint(PAGE_MD) → (0, "0 errors, 0 warnings\n")
def test_first_section_rule_keeps_the_main_flow(self):  # "Plan the sections" holds "The first section says why the subject exists." and "For a directory subject, that diagram is the main flow from start to end"
def test_page_md_names_the_answer_box_and_switch(self):  # "Fill the template" holds "div.answer", "show-sources", "NOANSWER", "NOSOURCES"; its Keep sentence names the Sources switch
def test_self_check_reads_the_reading_view(self):  # "Verify and export" no longer holds "A section without its citation"; holds "Does the box alone answer"
```

Use the module's existing helpers: `lint` and its section readers. `PAGE_MD = EXPLAIN / "rungs" / "page.md"`.

- [ ] **Step 2: Run them, and confirm that they fail**

Run: `python3 -B -m unittest tests.test_rung_drift.PageRungCase`
Expected: three tests FAIL, because the texts are missing. `test_page_md_lints_clean` passes at base. It guards the next step.

- [ ] **Step 3: Edit `page.md`.** Use STE-80, and keep every level-2 title.
  - **"Plan the sections":**
    - Replace the directory bullet at `:19-23` with the first-section rule of spec 2 rule 3, verbatim.
    - Add, as bullets, rule 4 (the diagram shows the reason, with its test), rule 5 (each section expands one sentence of the answer), rule 6 (exact rules go into `details.walk` in a reference section), rule 7 (define terms at first use; a glossary section with a nav entry, `dl.terms`, and a `div.cites` at the end of each `dd`; reference and glossary count in the six to ten), rule 8 (one note for a term with two meanings) and rule 9 (the reason with the rule).
  - **"Fill the template":**
    - Step 2 says the `<h1>` is the question (spec 2 rule 1).
    - Add a step for the answer box (spec 2 rule 2: one `<p>` of two to four sentences, at most 70 words, starting with `<strong>Short answer.</strong>`, then its `div.cites`; it never describes the page).
    - The Keep sentence adds the Sources switch. It names `NOANSWER` and `NOSOURCES` with their causes.
    - Step 4 says the switch stays the last child of the rebuilt `nav#toc`.
    - The primitives table gains three rows: answer box (`header > div.answer`), Sources switch (`nav#toc > label.sources > input#show-sources`), glossary (`section#terms > dl.terms`).
    - The lint line adds `dt` and the `<p>` of the answer box.
  - **"Write the prose":** add `dt` to the lint note at `:114`. Add one sentence: the template hides the cite blocks until the reader turns on Sources.
  - **"Verify and export", step 4:**
    - Remove "A section without its citation."
    - Add the three checks of spec 5: read `index.html` for a `div.cites` in each section; cover the page below the answer box; cover the prose of the first section.

- [ ] **Step 4: Run the case**

Run: `python3 -B -m unittest tests.test_rung_drift.PageRungCase tests.test_lesson_prompts`
Expected: `OK`. `test_lesson_prompts` keeps `PAGE_TITLES` matched.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/rungs/page.md skills/explain/tests/test_rung_drift.py
git commit -m "docs: explain: page.md teaches the answer-first page shape and the Sources switch"
```

---

### Task 5: `SKILL.md`, `lesson.md` and the gate-1 page prompt

**Files:**
- Modify: `skills/explain/SKILL.md` (convention 2, `:88-112`); `skills/explain/rungs/lesson.md` ("Plan the lesson" step 3, `:69-70`); `skills/explain/lesson/review-page.md` (`:39-41` and check 2 at `:48`)
- Test: `skills/explain/tests/test_rung_drift.py` (`PageRungCase`)

**Interfaces:**
- Consumes: the first-section wording of Task 4.
- Produces: no code interface.

- [ ] **Step 1: Write the failing tests** in `PageRungCase`

```python
def test_skill_md_says_the_page_hides_cites(self):  # convention 2 holds "The page and lesson templates hide the cite blocks until the reader turns on Sources"; SKILL.md lints 0 errors, 0 warnings
def test_lesson_md_first_candidate_is_the_main_flow(self):  # lesson.md holds "The main flow of the first section is the first candidate."; lints 0 errors, 0 warnings
def test_review_page_check_2_covers_the_answer_box(self):  # review-page.md Checks item 2 holds "the answer box in the header agrees with each section"; the text "A `<cite>` at the end of a paragraph" is gone
```

- [ ] **Step 2: Run them, and confirm that they fail**

Run: `python3 -B -m unittest tests.test_rung_drift.PageRungCase`
Expected: the three new tests FAIL.

- [ ] **Step 3: Edit the three files**
  - **`SKILL.md`:** add one sentence to convention 2, as spec 6 gives it. Add no new convention, because `test_rung_drift` pins "These seven rules".
  - **`lesson.md` step 3:** use the sentence of spec 6.
  - **`review-page.md`:**
    - Check 2 becomes "No two sections contradict each other, and the answer box in the header agrees with each section."
    - The sentence at `:39-41` becomes "The `div.cites` after a paragraph covers each sentence of that paragraph, so read the whole paragraph against the cited lines."
    - Keep three checks.

- [ ] **Step 4: Run the case, the prompt tests and the lint baseline**

Run: `python3 -B -m unittest tests.test_rung_drift tests.test_lesson_prompts`
Expected: `OK`. `CHECK_COUNT[PAGE]` stays 3.
Run: `cd ../.. && python3 skills/ste/scripts/ste_lint.py skills/explain/lesson/review-page.md | tail -1`
Expected: `4 errors, 3 warnings` or fewer.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/SKILL.md skills/explain/rungs/lesson.md skills/explain/lesson/review-page.md skills/explain/tests/test_rung_drift.py
git commit -m "docs: explain: convention 2, the lesson plan and gate-1 check 2 follow the answer-first page"
```

---

### Task 6: Amend the BPMN plan and spec (spec section 7)

**Files:**
- Modify: `docs/superpowers/plans/2026-10-06-explain-bpmn.md` (`:5`, `:11`, `:18`, `:24`, `:397`, Task 7 "Files" and "Produces", acceptance `:518`)
- Modify: `docs/superpowers/specs/2026-10-06-explain-bpmn-design.md` (`:184`, `:252`, and the status line)

**Interfaces:**
- Consumes:
  - The new page.md wording (Task 4).
  - The guard's second measure (Task 1).
  - The kept `CHECK_COUNT` of 3 (Task 5).
- Produces: a BPMN plan that starts from the merged `main`.

- [ ] **Step 1: Edit the plan**
  - **Base (`:11` and `:18`):** "`main` after the merge of `feat/explain-answer-first`" replaces "b98360f".
  - **Goal (`:5`) and acceptance (`:518`):** "readable label" / "reads as a name" gain "when the reader turns on Sources".
  - **`:397`:** `rungs/page.md:135` becomes `rungs/page.md` section "Verify and export". Line numbers moved.
  - **Task 7 "Produces", "Plan the sections" bullet:** it adds the BPMN bullets after the first-section rule of `feat/explain-answer-first`. It does not replace that rule.
  - **New note under "Beyond the letter":** `.bpmn-label` sits inside hidden cites, and the guard's second measure covers it.
  - **Unchanged:** `CHECK_COUNT[PAGE]` 3 → 4 and "check 4".

- [ ] **Step 2: Edit the spec**
  - **`:184` and `:252`:** add "when the reader turns on Sources".
  - **Status line:** add one dated sentence that points to this branch.

- [ ] **Step 3: Check the edits**

Run: `grep -c "b98360f" docs/superpowers/plans/2026-10-06-explain-bpmn.md`
Expected: `0`.
Run: `grep -c "turns on Sources" docs/superpowers/plans/2026-10-06-explain-bpmn.md docs/superpowers/specs/2026-10-06-explain-bpmn-design.md`
Expected: each count is 2 or more.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-10-06-explain-bpmn.md docs/superpowers/specs/2026-10-06-explain-bpmn-design.md
git commit -m "docs: explain: the BPMN plan starts after the answer-first branch; labels show with Sources on"
```

---

### Task 7: The whole branch: full suite, lesson E2E, a real page

**Files:**
- No source change, unless a run finds a fault. A fix goes into the task that owns the file, as a new commit.

- [ ] **Step 1: Run the full suite (log and poll)**

Run: `python3 -B -m unittest discover -s tests > /tmp/apt-full.log 2>&1; tail -3 /tmp/apt-full.log`
Expected: `OK`. The skip count is the same as on `main`, because the gated E2E tests skip.

- [ ] **Step 2: Run the gated lesson E2E once (log and poll)**
  - First run `pgrep -f "remotion|render.sh"`, and confirm that no other render uses `~/karpathy/video-workspace`.
  - This branch changes no video file, so the shared workspace sees no new side effect.

Run: `EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_lesson_e2e > /tmp/apt-e2e.log 2>&1; tail -3 /tmp/apt-e2e.log`
Expected: `OK`. `lesson_page` builds from the new template, and its page passes `NOANSWER` and `NOSOURCES`.

- [ ] **Step 3: Port the v2 page to the new template, as a smoke test.** The output is not committed.
  - Copy `out/2026-10-06-172738-page-what-are-the-gates-for-v2/index.html` to a new directory, `out/<now>-page-what-are-the-gates-for-v3/`.
  - Replace its head style and its three scripts with those of the new template.
  - Move the switch into the nav. Keep the answer box and every cite.

Run: `skills/explain/scripts/verify.sh out/<v3-dir>/index.html`
Expected: five `ok` lines.

  - Then run the two snapshots of `page.md` step 2 and step 3.
  - Read at most 4 tiles. Check the reading view, the nav with the switch at 500 px, and the answer box.

- [ ] **Step 4: Report** the four results to the controller: suite, E2E, `verify.sh` and tiles. Branch finishing follows the execution method.
