# Live run 3 — `/explain <code question>` without `--as`, inside `~/work/inavcalculator` (wave `explain-page`)

Date: 2026-10-03. Skill files at commit `f11f6d4` (after the fold-back of live run 2). The
run is spec §9, live run 3: rung selection by content shape, a topic answered from the
files of another git repository, CodeGraph available. `out/` is gitignored, so this note
keeps the evidence.

## How the run was made

A fresh subagent (Claude Opus) received, inside `/Users/valukin/work/inavcalculator`, the
slash command `/explain how does a signed counterparty request flow through
inavcalculator, from the HTTP filter to the signature check to the calculation`. It read
`~/.claude/skills/explain/SKILL.md` by path and followed it. It resolved the subject as a
topic (no path candidate), read the code (CodeGraph twice, then the files with Read), and
chose the rung itself. It skipped `open`, wrote nothing inside inavcalculator and changed
no skill file.

Pre-declared by the controller before the run: `Rung: page (chosen) — a step-through
request flow with more than 6 facets`. Rung line printed by the run:

```
Rung: page (chosen) — a step-through request flow with 9 facets, more than 6: filter, key check, signature check, mapping, store, scheduled calculation, signed response — subject: how does a signed counterparty request flow through inavcalculator, from the HTTP filter to the signature check to the calculation (topic)
```

Selection rule: **pass** (same rung, same reason class).

Output directory: `out/2026-10-03-181005-page-how-does-a-signed-counterparty-request-f/`
with `index.html`, `page.png` (1440x9000), `narrow.png` (500x844), `narrow-tall.png`
(500x12000) and `review/page-01..09.png`, `review/narrow-01.png`,
`review/narrow-tall-01..12.png`. The page is about 8700 px tall at 1440 and about 11000 px
at 500 (text wraps more), so the run applied the new height rule of `rungs/page.md` §7 twice.

## Rounds

| Round | `verify.sh` | Fix |
|---|---|---|
| 1 | five `ok` | first tall render (6000) had no footer; re-rendered at 12000 (footer in tile 10) |
| 2 | five `ok` | 89 → 64 cites (one per paragraph, as §6 now says); 9000 render |
| 3 | five `ok` | five wording fixes; narrow tall render needed 12000 (9000 had no footer) |
| 4 | five `ok`, exit 0 | `.track { overflow: hidden }` for a wrapped track at 500 px; tiles clean |

## Controller re-verification (commit `f11f6d4`, same directory)

```
$ skills/explain/scripts/verify.sh out/2026-10-03-181005-page-how-does-a-signed-counterparty-request-f/index.html
self-contained: ok
render 1440x900: ok
render 500x844: ok
citations: ok
prose: ok
exit 0
```

Provenance in the footer: `data-root="/Users/valukin/work/inavcalculator"`,
`data-kind="topic"`, Source `/Users/valukin/work/inavcalculator`, Commit `b3711d9`, Dirty
`dirty`, Not covered `the unsigned endpoint`. Checked against git in that repo: HEAD is
`b3711d9`; `git status --porcelain` prints `?? .claude/` and `?? .codegraph/`, so `dirty`
follows the rule (ruling D9 below). 9 `<section>`, 64 `<cite>`, a 7-step player. Three
citations sampled at random were checked by hand against the source on disk:
`entity/MutualFund.java:169` "if (asset.getType() != AssetType.FUT) {",
`logic/FundManager.java:422` "rabbitMQSender.sendBriefExportMutualFundINavCalculation(mutualFund);",
`crypto/SignatureVerificationService.java:70` "return keyProperties.getKeyMap().containsKey(counterPartyName);"
— all verbatim.

Tile read by the controller: `page-02` (filter section with five cited paragraphs; the
"seven gates" section with the stacked player, each step a highlighted track plus a cited
caption). Nothing clipped. Each cite takes two to three monospace lines because the Java
package paths are about 80 characters (D7).

Verdict: **pass** (spec §9: rung as pre-declared with a defensible printed reason,
`verify.sh` exit 0, three claims verbatim at their `path:line`, provenance correct).

## Skill defects found by the run, with rulings (inputs to the wave's fix dispatch)

- D1/D2 (high): `SKILL.md` subject-resolution rule 3 says a topic uses model knowledge;
  convention 2 allows a topic answered from repo files; nothing connects them, and
  CodeGraph is named only for a path candidate. Ruling: extend rule 3 — if the current
  directory is inside a git repository and the topic is about its code, read the code
  first (CodeGraph when `.codegraph/` exists), then convention 2 applies. The 130-line
  limit of `SKILL.md` may grow to 135 for this; prefer tightening elsewhere.
- D3 (medium): CodeGraph flagged two files as changed since the last index sync and
  omitted them. Ruling: one sentence next to the CodeGraph mention — if CodeGraph omits
  or flags a file, read it with Read; cite only lines read from disk.
- D4/D5 (medium): `rungs/page.md` §7 "read the last tile; if it does not show the footer,
  grow the height" loops when the render is taller than the page (the last tile is
  blank). Ruling: "find the tile that shows the footer; if no tile shows it, render again
  with a larger height", for the 1440 render and for the narrow tall render (which needs
  its own height: the page is taller at 500 px).
- D6 (low): a wrapped `ol.track` draws the first arrow of the new row over the player
  border. Ruling: `.track { overflow: hidden }` in `templates/page.html`.
- D7 (low): the visible cite form `path:line "snippet"` costs two to three lines per
  cite with deep package paths. Ruling: parked — the visible form is spec §5.3; a shorter
  visible form (common prefix dropped, `data-path` kept full) is a spec change for the
  user to decide; recorded in the ledger as a user-facing proposal.
- D8 (low): `rungs/sheet.md` §4 "run the first three commands in the directory of the
  subject" has no case for a topic or a conversation. Ruling: add "for a topic or a
  conversation, in the current directory" (one clause).
- D9 (low): Dirty is `dirty` because of two untracked tool directories. Ruling: keep the
  rule as written (anything printed = dirty); it is simple and never understates.
- D10 (low): without `--as`, the facet count is known only after reading the source.
  Ruling: one sentence in Rung selection — read the source before you choose the rung.

Observation outside the skill: `src/main/resources/bootstrap.yaml:4` in inavcalculator
holds a config-server URI with embedded credentials; the run did not cite or show it.
Reported to the user in the wave summary; not an explain-skill matter.
