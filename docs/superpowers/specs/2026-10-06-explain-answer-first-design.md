# explain: answer-first pages, with the cites behind a Sources switch

Date: 2026-10-06. Status: draft, for review. Branch: `feat/explain-answer-first`, from `main` at
32cb771. Coverage: not opted in. Lands before the BPMN plan (user decision, 2026-10-06); section 7
lists what that plan must change.

## 1. Problem

The user asked `/explain` for a page about what the gates of film generation are *for*.
The page (`out/2026-10-06-170852-page-this-repo-specificaly-what-are-gates-for/`, "v1") was taxing
to read. A remake built by hand (`out/2026-10-06-172738-page-what-are-the-gates-for-v2/`, "v2") was
"way better" in the user's words. Both pages pass `verify.sh` with five `ok` lines, the STE-80 lint
included. So the profile did not cause the difference. The way the page was written did.

| | v1 | v2 |
|---|---|---|
| Title | "The gates of film generation in /explain" | "What are the gates of film generation for?" |
| First screen | a lead that describes the page | a short answer to the question |
| Sections | 11 of equal weight, one for each gate | 7: why, each stage, blind spots, review gates, on a FAIL, exact rules, terms |
| Diagram | one, late: the order of the lesson steps | first: the stages in three cost bands, with what exists at each point |
| Cites | 114, a grey block under every paragraph | 121, hidden until the reader turns on a switch |
| Words to read outside folds, terms and cites | 1916, plus about 995 in cite blocks | 1095 |
| Repo terms | used with no definition | a glossary, and the reason given with each rule |

Three reviewers read the first draft of this design: contracts and tests, reader experience, and the
rule files. Their findings are part of sections 2 to 6.

## 2. Page shape (rules in `rungs/page.md`)

These rules apply to the page rung and to the lesson rung, which fills the same template.

1. **The title is the question.** For a topic, the `<h1>` is the user's question in full words. For
   a file or a directory, it asks what the subject does and why it exists.
2. **The answer comes first.** A `div.answer` in the header replaces `p.lead`. It holds one `<p>` of
   two to four sentences, at most 70 words, that starts with `<strong>Short answer.</strong>`.
   Then it holds its own `div.cites`. The box answers the `<h1>` and never describes the page ("This
   page shows…").
3. **The first section says why.** Proposed wording, which lints at 0 errors and 0 warnings: "The first
   section says why the subject exists. One diagram in it carries the main idea. For a directory
   subject, that diagram is the main flow from start to end, named by its stages. The main flow is the
   journey of one request, a pipeline or a BPMN process. The mechanics follow in later sections." This
   replaces the directory rule at `page.md:19-23`. It keeps the main flow first, as the BPMN spec
   needs.
4. **The diagram shows the reason.** The first diagram shows the reason that the answer gives, not a
   list of the parts of the subject. The test: with the prose covered, does the diagram alone support
   the answer?
5. **Each section expands one sentence of the answer.** Content that expands no sentence goes into a
   `details.walk` of a reference section, into the glossary, or out of the page into `Not covered`.
   This rule produces the merge from 11 sections to 7 without a fixed list of sections.
6. **Exact rules go into folds.** Limits, fault codes and rules for each item go into `details.walk`
   elements in a reference section, with one sentence above them that tells when to open them.
7. **Terms are defined where they first appear.** Define each repo term in the sentence of its first
   use. When the page uses a term that a newcomer to the repo does not know, add a glossary section
   at the end: `<section id="terms">`, an `<h2>` question, a nav entry, and a `dl.terms` in which each
   `<dd>` ends with its `div.cites`. The glossary is for looking up. The reference section and the
   glossary are sections like the others, and they count in the six to ten.
8. **One note for a term with two meanings.** If the repo uses the key term of the question for two
   things, the first section has one note that names the other one. The other one gets no section.
9. **Give the reason with the rule.** A paragraph that states a rule or a check also says why it
   exists.

The page shape is checked by the author's self-check (section 5) and by the gate-1 page reviewer
(section 6). Only rule 2 is a machine check (section 4).

## 3. Cites behind a Sources switch (`templates/page.html`)

The cite markup does not change. Convention 2, `cite_check.py`, the `div.cites` block and its
placement stay as the cite-block spec sets them. Only the view changes.

- **Hidden by default.** `.cites { display: none; }`. The reading view has no cite blocks.
- **The switch is in the sticky nav.** The last child of `nav#toc` is
  `<label class="sources"><input type="checkbox" id="show-sources"> Sources</label>`. The nav is
  sticky, so the switch can be reached at any scroll position, also at 500 px. The lint does not
  read `nav`.
- **Pure CSS.** `body:has(#show-sources:checked) .cites { display: block; }`. The template already
  uses `:has` for Play all. No script.
- **Print shows the cites.** `@media print { .cites { display: block; } }`.
- **Font sizes.** `label` and `input` join the explicit font-size lists, as the comment at the top of
  the style requires.
- **Not for the sheet or the video transcript.** `templates/sheet.html` and `templates/video.html`
  do not change. A sheet is exported to PNG, and hidden cites would be lost from it.

When a reader turns the switch on, each cite shows under the claim it supports, in the block form of
the cite-block spec.

## 4. The guard

Part 2 of the guard in `templates/page.html` changes in three ways.

1. **It measures the cites.** The current measure skips an element with no layout box
   (`page.html:575`), so a hidden cite block escapes `HSCROLL` and `SMALLTEXT`. A reviewer showed
   this: with the hide rule, a 12 px snippet and a 700 px span in a cite pass all five lines; with
   the switch on, they fail with `SMALLTEXT:12` and `HSCROLL;SMALLTEXT:12`. The guard now measures
   `HSCROLL` and `SMALLTEXT` twice: in the reading view, then with `#show-sources` checked. After the
   second measure, it sets the switch back to off. A fault in either view is reported one time:
   `HSCROLL` one time, and `SMALLTEXT` with the smallest size of the two views. The `#verify` snapshots
   show the reading view.
2. **`NOANSWER`.** The page fails if it has no `header .answer`, or if the text of that box outside its
   `.cites` is blank. The check is null-safe. A missing box gives `NOANSWER`, never a script error and
   never a missing `data-verify`.
3. **`NOSOURCES`.** The page fails if it holds a `.cites` element and has no
   `nav#toc input#show-sources[type=checkbox]`. Without this check, an author who rebuilds the nav
   could delete the switch, and then each cite would be hidden for good.

Order of the codes in `data-verify`: `HSCROLL`, `SMALLTEXT:<px>`, `PLAYALL`, `NOANSWER`, `NOSOURCES`,
`JSERROR`. `JSERROR` stays last. The status table of the template and the guard text of `page.md`
list the two new codes.

## 5. The author's self-check (`rungs/page.md` section 7, step 4)

- Remove "A section without its citation" from the list of faults to find in the tiles. The tiles
  show the reading view.
- Add these checks:
  - Read `index.html`, not the tiles: each section holds a `div.cites`. `cite_check.py` checks this
    only for file and directory subjects (`SECTION_KINDS`), and a topic page about repo files needs it
    too.
  - Cover the page below the answer box. Does the box alone answer the `<h1>`?
  - Cover the prose of the first section. Does its diagram alone support the answer?
- The lint notes (`page.md:63` and `:114`) add `dt` and the `<p>` of the answer box to the elements
  that the lint reads.
- The Keep list (`page.md:43-48`) adds the Sources switch and names the two new guard codes.
- Step 4 of "Fill the template" (`page.md:49`) says to keep the switch as the last child of the
  rebuilt `nav#toc`.

## 6. Other files

- **`SKILL.md` convention 2:** add one sentence, and no new convention: "The page and lesson
  templates hide the cite blocks until the reader turns on Sources; the sheet and the video
  transcript show them."
- **`rungs/lesson.md:69-72`:** "The journey of the first section is the first candidate" becomes
  "The main flow of the first section is the first candidate."
- **`lesson/review-page.md`:** check 2 becomes "No two sections contradict each other, and the answer
  box in the header agrees with each section." The checks stay three, so `CHECK_COUNT` stays 3 and the
  BPMN plan's "check 4" keeps its number. The stale sentence at `:39-41` ("A `<cite>` at the end of a
  paragraph covers…") changes to the block form: "The `div.cites` after a paragraph covers each
  sentence of that paragraph."
- **The template demo:** the header gets an answer box with a cite block, and its cite is a URL (BPMN
  plan decision 8: the template has no file cite). The nav gets the switch on its own line. A
  `<section id="terms">` with a `dl.terms` goes before the provenance section. The first two demo
  sections (`structure`, `code`) and their lead paragraphs stay as they are, because tests anchor on
  them (`FIRST_LEAD`, `CODE_LEAD`, `PLAY_ALL_TRACE`). The `PLAY_ALL` button stays on its own line.
  No new `:root` colour, so the palette tests do not change.

## 7. The BPMN plan after this lands

The plan has not started yet. When this branch merges, it changes as follows:

- Base: the new `main`, not b98360f. Tasks 5 and 7 then edit the new `page.html` and `page.md`, so
  their edits do not conflict.
- Labels: "every BPMN cite reads as a name" is true with Sources on. The goal, the acceptance line
  and spec 2.3 ("The label leads the eye") add "when the reader turns on Sources". The guard measures
  the cites (section 4), so `.bpmn-label` is measured again.
- First section: spec line 98 ("The first section (the whole, start to end) carries the main plane")
  agrees with rule 3 of section 2. Task 7 edits the new wording of `page.md:19-23`, not the old one.
- `review-page.md` check 4 and `CHECK_COUNT` 3 → 4 do not change, because this spec keeps three
  checks.

The last task of this branch edits the BPMN plan and spec as listed. It changes no BPMN code,
because none exists yet.

## 8. Tests

Run from `skills/explain`, as `python3 -B -m unittest tests.<module>`.

- `test_page_template` (Chrome runs through `verify.sh`): each case below fails both render lines with
  the named code, and the template passes with five `ok` lines.
  - The answer box is removed: `NOANSWER`.
  - The answer box holds only white space: `NOANSWER`.
  - The answer box holds only its `div.cites`: `NOANSWER`.
  - The answer box moves into the first section: `NOANSWER`.
  - The switch is removed from the nav: `NOSOURCES`.
  - A hidden cite holds a 12 px snippet: `SMALLTEXT:12`. This test turns red if the guard skips the
    second measure, or if the `:has` rule does not show the cites.
  - A hidden cite holds an unbreakable 700 px span: `HSCROLL` at 500 px.
  - Static: the style holds the hide rule, the `:has` rule, the print rule, and `label` and `input` in
    a font-size list. The status table lists `NOANSWER` and `NOSOURCES`.
  - The case-count docstring at the top of the module is updated.
  - The `SMALLTEXT` case at `test_page_template.py:361` plants `p.lead { font-size: 13px; }`. The
    template has no `p.lead` after this change, so that case targets `.answer p` instead.
- `test_lesson_prompts`: check 2 names the answer box, and `CHECK_COUNT[PAGE]` stays 3.
- Lint: `rungs/page.md`, `rungs/lesson.md` and `SKILL.md` stay at 0 errors and 0 warnings.
  `lesson/review-page.md` has 4 errors and 3 warnings at base, and it gets no new one.
- `test_rung_drift` and the full suite stay green. The gated lesson E2E (`EXPLAIN_VIDEO_E2E=1`) runs
  one time at the end, because `lesson_page` builds from the template and must pass `NOANSWER` and
  `NOSOURCES`.
- `tests/fixtures/verify-lesson.html` does not change. It has its own small guard, not the template
  guard, so a box in it would test nothing.

## 9. Not in scope

- One "Sources" disclosure for each paragraph. The user chose one switch in the nav.
- Taking the 65 inline code names, such as `render.sh`, out of v2-style prose.
- A word budget for the reading path as a new `verify.sh` line. The output lines of `verify.sh` are a
  contract that the BPMN plan also changes.
- A machine check for rules 1 and 3 to 9 of section 2. Whether they fit depends on the subject.
- New pages for the old directories in `out/`.
