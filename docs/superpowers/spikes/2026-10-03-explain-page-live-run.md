# Live run 2 — `/explain docs/superpowers/specs/2026-10-02-explain-skills-design.md --as page` (wave `explain-page`)

Date: 2026-10-03. Skill files at commit `2a864fb` (tasks 1–4 of the wave; `e680ce0` adds
only tests). The run is spec §9, live run 2. `out/` is gitignored, so this note keeps the
evidence. The fold-back of the defects below is commit (see the wave ledger / `git log`
after this note).

## How the run was made

A fresh subagent (Claude Opus) received the slash command as a user would. It read
`~/.claude/skills/explain/SKILL.md` by path and followed it with `$ARGUMENTS` =
`docs/superpowers/specs/2026-10-02-explain-skills-design.md --as page`. It read the skill
files (`SKILL.md`, `rungs/page.md`, `rungs/sheet.md` §4–§5 as `page.md` directs,
`templates/page.html`), the STE profile and the subject in full. It did not read the
outline, the tests or the fixtures. It skipped `open`. It changed no skill file.

Rung line printed:

```
Rung: page (forced) — --as page; the spec has more than 6 facets and one step-through flow, so the content fits a page — subject: docs/superpowers/specs/2026-10-02-explain-skills-design.md (file)
```

Output directory: `out/2026-10-03-173925-page-docs-superpowers-specs-2026-10-02-explai/`
with `index.html`, `page.png` (1440x6000), `narrow.png` (500x844), `review/page-01.png` to
`review/page-06.png` and `review/narrow-01.png`.

## Rounds

| Round | `verify.sh` | Fix |
|---|---|---|
| 1 | `citations: FAIL 5 failure(s)` (3 off-by-one line numbers, 2 snippets of 13 words) | corrected the lines, shortened the snippets |
| 2 | five `ok` | tile 6 ended inside section 7 of 11: the page was about 11000 px tall (probe render 1440x12000); the subagent cut snippets and merged claims |
| 3–6 | five `ok` | page still 8000 → 6500 → 6150 px; more content cut, cites moved into figcaptions, Source cell made non-wide (an empty grey grid cell) |
| 7 | five `ok`, exit 0 | page ends at about 5600 px; all seven tiles clean |

The subagent removed about 45 % of its first draft to make the page end inside the 6000 px
review render. That is defect 1 below, not a property of the subject.

## Controller re-verification (commit `e680ce0`, same directory)

```
$ skills/explain/scripts/verify.sh out/2026-10-03-173925-page-docs-superpowers-specs-2026-10-02-explai/index.html
self-contained: ok
render 1440x900: ok
render 500x844: ok
citations: ok
prose: ok
exit 0
```

Provenance in the footer: `data-root="/Users/valukin/karpathy"`, `data-kind="file"`,
Subject `docs/superpowers/specs/2026-10-02-explain-skills-design.md (file)`, Source
`/Users/valukin/karpathy`, Commit `2a864fb`, Dirty `dirty`, Not covered `none`. Checked
against git at build time: HEAD was `2a864fb`; `git status --porcelain` printed
` M .beads/issues.jsonl`, so `dirty` is correct. The artifact holds 11 `<section>`
elements, 42 `<cite>` elements and a 6-step player. Three citations sampled at random were
checked by hand against the spec: `:642` "video loses to page", `:161` "about 900 general
words is not enforced", `:363` "Opens from `file://` offline." — all verbatim on their line.

Tiles read by the controller: `page-01` (title, 13-entry nav in two rows, three sections
with lists and a captioned code figure; nothing clipped) and `page-04` (ordered list with
cites, a flow diagram and a sequence diagram with four messages; both diagrams fit the
measure). Citations are visually heavy: each one takes a full monospace line because the
path is 58 characters (defect 3).

Verdict: **pass** (spec §9: `verify.sh` exit 0, no layout defect in the tiles, opens from
`file://`, provenance correct). "Not covered: none" overstates coverage after the cuts
(defect 4).

## Skill defects found by the run (inputs to the fold-back)

1. `rungs/page.md` §7: no rule for a page taller than the 6000 px review render.
   `snapshot.sh` exits 0 while the lower sections and the footer are outside every tile.
   Ruling: a page has no height cap (spec §7 "no fixed canvas"); the render height is a
   review parameter. The rung file must say: if the last tile does not show the footer,
   render again with a larger height (9000, 12000, …) until it does; never cut content to
   fit a render.
2. `rungs/page.md` §7: `narrow.png` at 500x844 shows the first screen only, so the tile
   checks "a diagram that does not fit at 500 px" and "steps did not stack" cannot be done
   visually. Ruling: keep the spec's `500 844 1` and add a tall narrow render
   (`500 <same height> 1`) when the page has diagrams or a player below the first screen.
3. `SKILL.md` convention 2 / `rungs/page.md` §6: no guidance on citation density. One
   cite per sentence doubles the page height. Ruling: one cite per paragraph or list
   item that carries a checkable claim; snippets of about 6 words; the visible form
   `path:line "snippet"` stays (spec §5.3).
4. `rungs/page.md` §5: "a page seldom drops facets, thus write `Not covered: none`" has no
   place for content dropped for length. Ruling: `Not covered` lists every facet of the
   subject that the page does not explain, whatever the reason.
5. `SKILL.md` Build procedure step 2 ("read the rung file for the chosen rung only")
   contradicts `rungs/page.md` §5–§6, which point to `rungs/sheet.md` §4–§5. Ruling: one
   clause in `SKILL.md`: also read the sections of other files that the rung file names.
6. `SKILL.md` convention 5: the slug steps trim `-` before the cut to 40 characters, so a
   slug can end in `-` (here `…-2026-10-02-explai`). Ruling: cut first, then trim.
7. `templates/page.html` provenance grid: with a `wide` Source cell the auto-fit grid
   shows an empty grey cell. Ruling: the grid background must not show through an empty
   cell (put the background on the cells); the comment says Source may be `wide`.
8. `rungs/page.md` §4 flow pattern: no label budget. Ruling: one sentence — an 18-unit
   mono label needs about 11 units per character, so a 118-unit box holds 9.

Non-defect: spec §5.3 names the page outputs `page-1440x6000.png`, `page-500x844.png` and
`review/page-<WxH>-NN.png`; the skill writes `page.png`, `narrow.png`, `review/page-NN.png`.
The skill is self-consistent; the spec's names are stale (left as is; the spec is the
scope contract, not the file-name authority).
