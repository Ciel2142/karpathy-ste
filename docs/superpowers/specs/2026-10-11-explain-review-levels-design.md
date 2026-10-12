# explain: review levels for the lesson rung

Date: 2026-10-11. Status: approved 2026-10-12, after a four-reviewer consilium; the five
decisions of section 13 are decided. Coverage: not opted in.

## 1. Problem

The two cold-read gates of the lesson rung cost a median of 44 reviewer runs per lesson, about
115k subagent tokens each, so `--review` went opt-in (commit 5a2c9b3). Off by default means no
lesson is reviewed. The user wants a cheap review that is honest about what it checked, and the
full review when it is worth the cost.

The 13 lesson runs in `out/` (2026-10-06 to 2026-10-10, 488 reports) show where the runs went
and what they found:

| | Gate 1 (text) | Gate 2 (stills) |
|---|---|---|
| reports, all rounds | 120 | 368 |
| `verdict: fix`, all rounds | 56 (47 %) | 80 (22 %) |
| round 1: reports / fix | 51 / 35 | 187 / 58 |
| round 2: reports / fix | 44 / 19 | 156 / 21, of which 17 hold a new finding (about 15 distinct faults) |
| rounds 3 and 4: reports / fix | 25 / 2 | 25 / 1 |
| parts per run | – | 7 to 18, mean 14, the last three runs 18 |

Round-1 findings by class (section 3 gives the classes):

| Gate 1, 83 findings | | Gate 2, 68 findings | |
|---|---|---|---|
| C1 page claim vs source | 38 (46 %) | D1 still vs narration | 48 (71 %) |
| C2 narration vs source | 33 (40 %) | E1 stage text or mark vs source | 12 (18 %) |
| B2 section vs section | 9 (11 %) | A1 lit line that no cite names | 6 (9 %) |
| B1 narration vs section | 3 (4 %) | D2 list of sentences | 2 (3 %) |

Four structural causes, none of them a choice of level:

1. After one fix in a clip, gate 2 reads every part of the clip again. Round 2 read 156 parts;
   98 of them had a clean round-1 report. Those re-reads found about 5 of the 19 round-2
   findings: faults that were there before and that round 1 missed.
2. Every part reviewer gets the whole page, the transcript, the gate-1 copy of the script and
   the gate-1 reports: 123 KB, about 31k tokens, in the last run; the page alone is 34 to 485 KB
   across the runs. The reviewer needs one section and the transcript.
3. Every part reviewer diffs the script against the gate-1 copy (render check 5). In 11 of 13
   runs a script changed during gate 2, and each part of the clip re-did the same text check.
4. Every reviewer reads the cited files by hunting in the repo. One lesson cited a 3600-line
   file by URL, which `cite_check.py` does not check, and each reviewer searched for a local
   copy.

Every reviewer runs on the session's model, also the checks that compare text with text and the
reads that only rule an earlier finding.

## 2. Goals and non-goals

Goals:

- `--review <level>` with three levels. A level is a set of check classes, cumulative, plus a
  depth. The provenance names the level in words a reader can trust, and a tool checks that
  the label matches the reports on disk.
- Each check runs on the cheapest model the archive shows can do it. Where the archive does
  not show it, the strongest model runs and a measurement decides later.
- The structural savings apply at every level with a review.
- The lesson rung only. Other rungs keep the no-effect line.

Non-goals: a token budget; the author's own checks; the drop, removal and disputed-finding
rules; URL mirrors for cites (a later spec); the stage-text manifest (a later spec, section
12).

## 3. Taxonomy of checks

Each check has an id. The prompts, the rung file, the ok-ledger and the review check use the
ids.

| Class | Compares | Checks |
|---|---|---|
| A. Mechanical, tools, 0 tokens | artifact vs rules | A0: the checks that exist (`cite_check.py`, `ste_lint.py`, `build-timeline.mjs --check`, the guard, `verify.sh`, `bpmn.py check`). A1: a lit source line is a line that a cite of the scene names (guard, section 7.1). A2: the code card of a scene shows a cited line of that scene (guard, section 7.1). A3: a gate-2 part is read again only when its inputs changed or its last report has a finding (a rule of the rung, section 6.3). A4: the review check (section 7.4). |
| B. Text vs text | narration vs page; section vs section | B1: nothing in a clip's narration contradicts the page; the clip may say less, never something different. B2: no two sections contradict each other, and the answer box agrees with each section. |
| C. Text vs source | a claim vs its cited lines, read from the repo | C1: no sentence of the page makes a claim that its cited lines do not support. C2: no sentence of a narration makes a claim that its cited lines do not support. C3: for each sub-process, gateway and user task in a section's BPMN diagram, a paragraph explains it, and the names match. |
| D. Picture vs narration | a still vs its sentence | D1: each still agrees with what its scene narrates up to that sentence; nothing in the frame suggests a thing the narration does not say; nothing the narration has named is missing; nothing left over from an earlier scene says that an earlier state still holds. D2: the picture is not a list of sentences. D3: the poster still is informative on its own. |
| E. Picture vs source | a still vs the code or diagram it pictures | E1: a stage text that quotes or names a source thing matches the source, or is marked as cut. E2: a notation on the stage (direction, origin, dash, colour, glyph) encodes a relation the source has. E3: the lit or pointed element is the one the sentence names. |
| F. Judgment | the plan and the motion | F1: the clip choices in `review/plan.md` are the sections where motion explains more than a still, and no section that clearly needs one is missing. F2: motion is earned: from the `-end` still before the scene to the scene's own stills, the picture changed in a way the narration explains. |

Where the current checks went: page check 1 is C1, page check 2 is B2, page check 3 is F1, page
check 4 is C3; script check 1 is C2, script check 2 is B1; render check 1 is D1 plus E1 to E3
plus A1, render check 2 stays as a sentence of F2 (a scene that changed nothing earned no
motion), render check 3 is D2, render check 4 is D3, render check 5 moves to one text read per
changed clip (section 6.4), render check 6 is F2.

B1 widens from "vs its section" to "vs the page": one archived clip contradicted a sentence of
another section, and the reviewer had to file it under the wrong check.

## 4. Levels

| | `off` (default) | `quick` | `standard` | `full` |
|---|---|---|---|---|
| classes | A | A B C1 C3 | A B C D E | A B C D E F |
| gate 1 | – | consistency, page | consistency, page, one script reviewer per clip | the same, plus F1 |
| gate 2 | author's still read | author's still read | render reviewers, D and E | render reviewers, D E F2 |
| hunting rounds | – | 1 | 1 | 2 |
| after a fix | – | verify the changed items | verify the changed items; A3 for parts | round 2 reads every part of a fixed clip and hunts; rounds 3 and 4 verify |
| of the archive's round-1 findings, caught | 0 | about 60 % of gate 1, none of gate 2 | all classes but F | all |

Contract: `/explain <subject> [--as …] [--review [quick|standard|full]]`. A bare `--review` is
`standard`. Another value is an error that lists the three names. The flag leaves `$ARGUMENTS`
with its value, as the `--as` pair does. For a rung other than `lesson`, the line
`--review: no effect on <rung>` stays.

Two modes of a read. A **hunt** rules the findings of the report before it, if any, and looks
for new faults in all its inputs. A **verification** rules the findings of the report before
it, then applies its checks to the items that the `## Author` block names as changed (a scene,
a sentence, a still, a section), and looks nowhere else. The prompt gets the mode in `{mode}`.
At `quick` and `standard`, round 1 hunts and every later read verifies. At `full`, rounds 1
and 2 hunt and rounds 3 and 4 verify.

The removal rule, the drop rules, the disputed findings and the propagation rule of
`rungs/lesson.md` apply unchanged at every level with a finding. A finding of a class above the
level (an E finding at `quick`) is a finding; the author treats it as any other.

Why `quick` holds the page reviewer: class B alone is 12 of the 83 gate-1 findings, and 4 of
those 12 needed the source to decide which side was right. The page reviewer had the highest
yield per run in the archive. With it, `quick` grounds the page, and B1 grounds each clip
against the page. Only the cite pointers inside `script.json` go unchecked.

Why `standard` holds class E: E is 18 % of the picture findings, and the faults are the worst
kind (a label on the wrong exit, a wrong body, an arrow in the wrong direction). The render
reviewer does D and E in one read.

Why `standard` has one hunting round: the archive's round-2 hunts on clean parts found about
one fault per run at the price of about 8 reads per run. `standard` accepts that loss and says
so in its provenance line; `full` does not.

## 5. Reviewers, models and inputs

| Reviewer | Prompt | Model | Checks | Inputs |
|---|---|---|---|---|
| consistency, one per lesson | `lesson/review-consistency.md` (new) | `haiku` | B1 for each clip, B2 | `index.html`, `review/plan.md`, every `clips/<id>/script.json` |
| page, one per lesson | `lesson/review-page.md` | the session's model | C1, C3; F1 at `full` | `index.html`, `review/plan.md`, `review/cites-page.txt` |
| script, one per clip | `lesson/review-script.md` | the session's model | C2 | `review/section-<id>.html`, `clips/<id>/script.json`, `review/cites-<id>.txt` |
| render, one per part | `lesson/review-render.md` | the session's model | D1 D2 D3 E1 E2 E3; F2 at `full` | `review/section-<id>.html`, `clips/<id>/index.html` (the transcript), `review/cites-<id>.txt`, the stills of the part |
| any verification read | the same prompt, `{mode}` = `verify` | `sonnet` | the checks of the reviewer | the same inputs, plus `{previous}` |

The rung names the model in each dispatch line: "Start a fresh general-purpose subagent with
`model: haiku`", or "with no `model`" for the session's model. The handoff prints the models
(section 6.5), so a reader of the provenance knows which model hunted. A session that runs on
`haiku` or `sonnet` hunts on that model; the handoff line shows it.

The gate-1 copy `review/gate1-<id>.script.json` goes: its only reader was render check 5.

Three new files per dispatch, written by tools:

- `review/section-<id>.html`: the `<section id="<id>">` element of the page, by
  `scripts/section.py` (section 7.3). Written again at every dispatch, because gate-1 fixes
  edit sections.
- `review/cites-<id>.txt` and `review/cites-page.txt`: for each local cite of the script or the
  page, the cited file's lines from 20 before to 20 after the cited line, with line numbers and
  the path, by `scripts/cites.py windows` (section 7.3). The reviewer reads the window first
  and the repo when the window does not settle a claim. A URL cite gets a line that says so.
- `review/gate2-<id>.parts`: one line per part, `<part> <scene> [<scene>…]`, written at the
  first gate-2 dispatch of the clip. The review check reads it.

Prompt changes, for `test_lesson_prompts.py`:

1. `{mode}` in every prompt, filled `hunt` or `verify`; the sentence "If the name of
   `{previous}` ends in `-round-2.md` or `-round-3.md`, this is a verification read" goes, and
   the Round 2 section says what a verification does (section 4).
2. `{level}` in `review-page.md` and `review-render.md`. Each check that applies at `full` only
   is marked `(full)`, and the prompt says: "A check marked (full) applies only when the level
   is `full`."
3. The Inputs sections list the inputs of section 5. `{changes}` and check 5 leave
   `review-render.md`; `index.html` and `review/plan.md` leave `review-script.md`.
4. Check ids replace check numbers. The Report sections say "For a finding of B1 or B2, the
   source lines are…".
5. An ok-ledger: after the findings, one line per check of the level, `<id>: ok` or
   `<id>: <n> findings`. A pass report is the ledger and the verdict line.
6. In `review-render.md`: "A fault already visible in the `-end` still before your first scene
   belongs to the earlier part. Write one line `carried from <scene>: <text>` and no finding."
   Two of seven findings of the last run were the same fault from two parts.
7. The Hunt sentence names the class: "Assume one claim in this file is not supported by its
   cited lines" (C), "Assume one still gives a false picture of what its scene narrates, or of
   the source" (D, E), "Assume one sentence of a clip says something the page does not" (B).

## 6. Procedure changes in `rungs/lesson.md`

The rung keeps its eleven level-2 titles. The sentence "the three prompt files of the two
gates" becomes "the four prompt files". Both fill tables get rows for `{mode}` and `{level}`.

### 6.1 Contract, rung line, cost

Section 1 prints `review: off|quick|standard|full` after the rung line and writes the level to
`review/level` (one word) before any dispatch. The cost paragraph of section 3 points at the
table of section 9 of this spec. The author appends one line per reviewer run to
`review/cost.tsv`: `<report> <model> <subagent tokens>`, from the usage line that the Agent tool
returns.

### 6.2 Gate 1

Before each dispatch: `section.py` for each clip, `cites.py windows` for the page and each
script. At `quick`: start the consistency reviewer and the page reviewer, in parallel. At
`standard` and `full`: also one script reviewer per clip.

Reports: `review/gate1-consistency-round-<k>.md`, `review/gate1-page-round-<k>.md`,
`review/gate1-<id>-round-<k>.md`. The `## Author` block names each item it changed (a line of
the page, a scene). The rulings and the verdict line are as now.

After the fixes, at `quick` and `standard`: one verification read (`sonnet`) per reviewer whose
report has a finding or whose inputs changed. At `full`: round 2 hunts as now, then rounds 3
and 4 verify on `sonnet`.

### 6.3 Gate 2

Step 1, the author's own read of the stills, stays at every level. At `off` and `quick`, stop
there.

Dispatch: parts as now (five stills, whole scenes, the `-end` still before). Before the first
dispatch of a clip, write `review/gate2-<id>.parts`. Before every dispatch of a clip, snapshot
its inputs: copy `clips/<id>/review/*.png` to `review/gate2-<id>-round-<k>-stills/`, and write
`review/gate2-<id>-round-<k>.sha` with one `sha256` line per scene object of `script.json`
(the narration and the cites) and one for `review/section-<id>.html`.

A3, the re-read rule at `standard`: after the fixes and the re-render, run
`scripts/parts_changed.py clips/<id> review/gate2-<id>-round-<k>-stills review/gate2-<id>-round-<k>.sha review/gate2-<id>.parts`.
It prints the parts whose inputs changed: a still of the part, or the `-end` still before it,
differs from the snapshot by pixels (the stills are JPEG frames cut from the H.264 file, so a
byte compare is never equal; the comparer is the `differing_pixels` of `tests/png_diff.py`,
moved to `scripts/`, with its level), or a scene object of the part changed, or the section
changed. A part that this list names, or whose last report has a finding, gets a verification
read (`sonnet`). Every other part keeps its last verdict. At `full`, round 2 reads every part
of a clip that had a fix and hunts, as now; A3 applies to rounds 3 and 4.

### 6.4 A narration or cite change during gate 2

A gate-2 fix that edits a scene object of `script.json` changes no still of other parts and
needs C2 and B1 on the new text. Instead of render check 5 in every part: after such an edit,
start one script reviewer (`sonnet`, `verify`) with the last gate-1 script report as
`{previous}` and an `## Author` block that names the changed scenes, and one consistency
reviewer (`haiku`, `verify`) the same way. Their reports are the next round numbers of their
series. The clip renders again after these reads, not before, so a wrong fix costs no render.

### 6.5 Provenance and handoff

The `Cold review` row of the provenance holds one of:

```
none
quick: the page agrees with its sources, the clips agree with the page
standard: the text agrees with its sources, the pictures agree with the narration and the sources; one hunting round
full: all checks, two hunting rounds
```

The handoff prints `review: <level> (hunts <model>, verification sonnet, consistency haiku)`,
then the disputed findings list or `disputed findings: none`. The output table lists the new
files of section 5 and 6.3 and drops the gate-1 copy.

## 7. Tools

### 7.1 A1 and A2: the guard knows the lit lines (wave 2)

Today the timeline scene (`FilmScene` in `video/src/types.ts`) carries no cites, the guard sees
`<text>` nodes only (`FilmStage.tsx` queries `text`), and a band is a `<rect>` without a path.
Three changes:

- `build-timeline.mjs` writes `cites: [{ path, line }]` into each `FilmScene`.
- `CodeCard` (`video/src/kit/code.tsx`) puts `data-lit="<path>:<line>"` on each band and tint
  rect, and `data-card="<path>:<from>-<to>"` on the card.
- `FilmStage` collects, at each check frame, the lit lines whose opacity on the canvas is 0.1 or
  more and the ranges of the visible cards, and hands them to `faultsOf` with the scene's cites.
  Two new faults, in the `guard: FAIL frame <f> (scene <id>): …` line:

```
UNCITED <basename>:<line>      a lit line that no cite of the scene names
OFFPANEL <basename>            a card shows a file the scene cites, and no cited line is in its range
```

A1 was 6 of 68 picture findings; A2 was 4 of the 12 E findings. The kit is shared, so both apply
to the film format; brainrot has no guard stage. When A1 lands, the lit-line sentence leaves
`review-render.md`.

A byte compare of `-end` stills (an earlier draft's A2) is dropped: the stills are lossy
frames, never byte-identical.

### 7.2 `scripts/parts_changed.py`

`parts_changed.py <clip-dir> <stills-snapshot> <sha-file> <parts-file>` prints one part number
per line, as section 6.3 says, and `none` when no part changed. A missing snapshot still, or a
scene that no part names, is an error on stderr and exit 2.

### 7.3 `scripts/section.py` and `scripts/cites.py`

`section.py <index.html> <id>` prints the `<section id="<id>">…</section>` element with a
leading HTML comment that gives its first and last line in the page. Exit 2 with one line when
the id is not a section.

`cites.py windows <index.html|script.json> <root>` prints, for each local cite in document
order, a header `<path>:<line>` and the cited file's lines from 20 before to 20 after, each
prefixed with its number. A URL cite prints `<url> (not local)`. A cite whose file is missing
prints `<path>: missing`. Exit 0 always; `cite_check.py` owns the failures.

### 7.4 A4: `scripts/review_check.py`, the eighth line of `verify.sh`

`verify.sh` on a lesson runs `review_check.py <output-dir>` and prints an eighth line:

```
review: none
review: ok <level>
review: FAIL <cause>
```

Rules. Without `review/level`, or with `off`: the `Cold review` row must be `none`. With a
level: every reviewer kind of the level (section 4) has a last report for every item: the
consistency and page reviewers; a script report for each clip with a `figure.clip`; for each
scene of such a clip, a part in `review/gate2-<id>.parts` with a report. Each last report ends
`verdict: ok` and its ledger has every check id of the level. A clip named in the `Dropped
clips` row is exempt. The row's text equals the level's string of section 6.5. The first rule
that fails gives the cause: `no report for <item>`, `<report> says fix`, `<report> lacks <id>`,
`row says <text>`. A missing report is FAIL, so a reviewer that stalled is not a reviewer that
passed.

`verify.sh` keeps six lines for a page; a lesson has eight. `test_verify.py`'s `LESSON_PASS`
grows to eight.

## 8. Tests

Pins the consilium found, by file:

- `tests/test_rung_drift.py`: the argument-hint regex (line 1049) and the README regex (1051)
  take `[--review [quick|standard|full]]`; `README.md:9` changes with them. The page prompt's
  check numbering pin (930, `["1", "2", "3", "4"]`) becomes the check ids; the answer-box pin
  (857-863) points at `review-consistency.md`.
- `tests/test_lesson_prompts.py`: `PLACEHOLDERS` gets the fourth prompt and `{mode}`, `{level}`
  where section 5 puts them; the union invariant (457) holds because the rung's fill tables get
  the rows; `VERIFY_READ` (182) and `SKIP_CHECK_5` (178) go; `RENDER` loses `changes`;
  `CHECK_COUNT` becomes consistency 2, page 3, script 1, render 7; `LESSON_TEXTS`
  says "four prompt files" and drops the gate-1 copy sentence; a new text pins the level table
  and the mode definitions.
- `tests/test_render.py`: the Syntax line of `SKILL.md` (985-986) and the Contract's three
  levels and bare default.
- `tests/test_verify.py`: `LESSON_PASS` has the eighth line; a lesson without `review/level`
  prints `review: none`.
- New `tests/test_review_check.py`: a fixture lesson with reports; each of the four FAIL causes
  from one mutation; `ok` with a dropped clip exempt.
- New `tests/test_parts_changed.py`: a changed still, a changed scene object, a changed section
  and an unchanged part, with two PNG fixtures that differ by one pixel and by many.
- New `tests/test_section.py` and `tests/test_cites.py`: the element printed whole; a missing id
  exits 2; a window at the file start and end; a URL cite; a missing file.
- Wave 2, `tests/test_film_guard.py`: the `faultsOf` arity pins (214, 225) change; `UNCITED`
  for a lit uncited line, nothing for a cited one or one under 0.1 opacity; `OFFPANEL` for a
  card with no cited line; `tests/fixtures/film-timeline.json` gains `cites`.
- `tests/test_lesson_e2e.py`: unchanged; it runs without `--review`.

## 9. Cost, three clips and eighteen parts

Counted runs, from the archive's rates (37 % of parts and 69 % of gate-1 reports get a fix in
round 1; a script changes during gate 2 in most runs):

| Level | session-model runs | `sonnet` runs | `haiku` runs |
|---|---|---|---|
| `off` | 0 | 0 | 0 |
| `quick` | 1 | about 1 | 1, about 1 more |
| `standard` | 4 + 18 = 22 | about 3 + 7 + 1 | 1 + about 2 |
| `full` | 4 + about 4 + 18 + 18 = about 44 | about 6 | 1 + about 2 |

Today a run is 44 session-model reads with about 31k tokens of fixed input each. `standard`
halves the strong reads and trims about 25k tokens from each part read. `full` keeps today's
read count and trims the same. The 115k-per-run figure has no token log behind it;
`review/cost.tsv` of the next runs replaces this table.

## 10. Measurements before trust

1. `sonnet` on verification reads: the first `standard` and `full` runs plant one "fix that
   moves the fault" (`review/plants.md`, the protocol of the lesson spec section 7.5). A
   verification read that rules it `resolved` moves verification back to the session's model.
2. `sonnet` as the `standard` render reviewer: run `review-render.md` with the new inputs over
   at least 40 archived parts whose last report is `ok` (false-positive rate; the archive's
   stills are the final renders, so they are clean) and over at least 8 planted D and E faults
   across two live runs (recall; the archive's faulty stills were overwritten by the fix). The
   thresholds, fixed now: recall 80 % or more, false positives 10 % or less. A pass moves the
   `standard` render row of the model table to `sonnet`; the table is the one place to change.

## 11. Waves

Independent parts, for the wave map:

- Contract and prompts: sections 4, 5, 6.1, 6.2, 6.4, 6.5 and their tests.
- Tools: 7.2, 7.3, 7.4, 6.3 and their tests. The rung's A3 rule needs 7.2.
- Guard (wave 2): 7.1 and its tests; it touches the video rung and can run in parallel.

## 12. Later

- A stage-text manifest from the guard (`review/stage-text.json`: the visible texts of each
  still), which would let a tool check that a mono text on stage is a substring of a cited range
  and list "carried over" texts for the D reviewer. One run with the manifest first.
- URL mirrors for cites (`provenance.mirrors`), so `cite_check.py` and `cites.py` see a local
  copy of a file cited by URL.

## 13. Decisions (decided by the user, 2026-10-12)

1. Bare `--review` means `standard`, not `full`.
2. `standard` reads the stills on the session's model (D and E in one read); `sonnet` does
   verification only, until measurement 2 passes.
3. `standard` skips clean unchanged parts after a fix and loses about one fault per run by the
   archive's count; `full` re-reads every part.
4. `quick` holds the page reviewer (one strong run), so it is not free; a B-only `quick` caught
   8 % of the archive's findings.
5. A1 and A2 in the guard apply to the film format too, because the kit is shared.

Considered and rejected: verify a fixed item by resuming the reviewer that found the fault. It
would see the stills before and after the fix, but the author would have to keep each
reviewer's agent id across the run. Every read stays a fresh subagent.
