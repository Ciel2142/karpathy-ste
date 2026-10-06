# explain lesson: the first live run

Subject: `/explain /Users/valukin/work/aos --as lesson` (a Java/Camunda account-opening service,
446 files). Output: `out/2026-10-06-123735-lesson-aos/`. Rung: `skills/explain/rungs/lesson.md` as
merged in `683eeef`. Author: the main session; reviewers: fresh general-purpose subagents.

## Result

Eight sections, three clips planned (`inbound`, `delegates`, `pdcheck`), one shipped (`pdcheck`,
39.7 s, Kokoro). Six `ok` lines from `verify.sh`. Disputed findings: none.

## Numbers (spec 7.5)

| | gate 1 r1 | gate 1 r2 | gate 2 r1 | gate 2 r2 | gate 2 verify |
|---|---|---|---|---|---|
| reviewers (subagents) | 4 | 4 | 7 | 7 | 2 |
| findings | 10 | 6 | 6 | 2 | 1 (re-opened) |
| fixed before the next read | 10 | 0 (rule: a round-2 first finding is open) | 6 | 2 | 0 |
| disputed by the author | 0 | 0 | 0 | 0 | 0 |
| wall time | 3.5 min | 5.3 min | 5.6 min | 5.2 min | 2.8 min |
| subagent tokens | ~452k | ~473k | ~805k | ~827k | ~223k |

- Plants: P1 (page sentence not supported by its cite) found by the page reviewer and by the
  `inbound` script reviewer (check 2); P2 (narration against the section) found by the `pdcheck`
  script reviewer; P3 (a `sources` range with no cited line) refused by `build-timeline --check`
  in step 5 (after one author error: the first range held a cite). 3 of 3.
- Real findings, all verified against the source: gate 1 r1 six (a fourth process
  `ManualPersonRemoval`; the test process has a message start, not a timer; the version map
  before the latest definition; `ProcessEngineException` rethrown unchanged; "XML" uncited;
  the `other` scene overclaimed). Gate 1 r2 four on the page (the deployment pattern is ignored
  under a process application; `aos.initial.variables.initialVariables` is a nested key the
  config does not have — a repo gap; `<name>asyncid` is written and never read; five BI
  statuses, not three) and two on `inbound` (true claims, missing cites: Redis, the handler
  name). Gate 2 r1 six on the pictures (wrong exit label, flag still `true`, an uncited lit
  line, the wrong catch on the card, a label on the wrong exit, a row still fading at the scene
  end). Gate 2 r2 two (a token still bright after the flag turned false; the card swapped one
  sentence early). Verification: the fix of the second regressed a resolved finding (line 38
  lit under the engine-exception line).
- Drops: `inbound` (gate 1 r2, two cite-only findings), `delegates` (verification read, one
  regression). Claims removed from the page: 4. Clips dropped for a render FAIL: 0.
- Author cost: 624 lines of scene code for three clips (5.3 lines per second of clip); render
  runs: `delegates` 7 (2 guard FAILs, 3 after my own reads, 2 after gate 2), `pdcheck` 2;
  about 30 min of authoring, 2 h 30 wall end to end, 22 min in the gates.
- Reviewer accuracy: 0 findings the author would dispute across 24 reviewer runs; one
  reviewer note was out of scope (the dim boundary box) and was not filed as a finding.

## Fold-back items (spec amendment A2, applied on `feat/explain-cite-block`)

1. Gate 1 has no verification read: a round-2 first finding is open by rule, which dropped a
   correct clip for two missing cites and removed four page claims that a one-line edit fixed.
   Give gate 1 the same verification read as gate 2 (rule the fix, hunt nothing).
2. A verification read may re-open a resolved finding when a fix moved the fault (right), but no
   read follows, so a regression costs the clip. Allow one more verification read when the
   re-opened finding is a regression of the author's last fix.
3. The spec text contradicts the rung on: the gate-2 split by still count (5.4/D13), the drop
   instead of a third gate-1 round (5.3), and the round-2 first finding (5.3). Align the spec.
4. The plan rule for a directory subject: the first section says what the thing does, for whom,
   start to end (here: the applicant's journey through `aos.bpmn`); the mechanics follow. The
   author read the BPMN only for the decision table and the lesson had no such section (user,
   2026-10-06). The journey is also the clip that earns motion first.
5. Presentation, from the same review: cited source lines belong in a code block under the
   paragraph, not inline in the prose; the white page is hard on the eyes. Spec
   `2026-10-06-explain-cite-block-design.md` (cite block + warm paper palette), to land before
   the lesson is rebuilt.
6. Costs to put in the rung: about 115k subagent tokens per reviewer run; a 5-scene clip takes
   3 to 4 reviewers per gate-2 round; a clip of 38 s took 7 renders.

## Applied

Items 1, 2, 4 and 6: `rungs/lesson.md` (a gate-1 verification read, `round-3`; a regression read
at both gates, `round-4`; the whole first in the plan; the measured costs), `rungs/page.md` (the
whole first for a directory subject) and the three prompts (a verification read is keyed on
`-round-2.md` or `-round-3.md`). Item 3: the lesson spec carries A2 and marks A1 approved. Item
5: the cite-block spec, built on the same branch. Next: rebuild the lesson
(`/explain /Users/valukin/work/aos --as lesson`) with the journey as section 1.
