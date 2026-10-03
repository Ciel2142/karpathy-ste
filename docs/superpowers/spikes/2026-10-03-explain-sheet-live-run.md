# Live run 1 — `/explain skills/ste/SKILL.md --as sheet` (wave `explain-sheet`)

Date: 2026-10-03. Skill files at commit `5e7cd92`. The run is spec §9, live run 1.
`out/` is gitignored, so this note keeps the evidence.

## How the run was made

A fresh subagent (Claude Opus) received the slash command as a user would. It read
`~/.claude/skills/explain/SKILL.md` by path and followed it with `$ARGUMENTS` =
`skills/ste/SKILL.md --as sheet`. It read only the skill files (`SKILL.md`, `rungs/sheet.md`,
`templates/sheet.html`, the script headers) and the STE profile. It did not read the spec,
the outline, the tests or the fixtures. It skipped `open`. It changed no skill file.

Rung line printed:

```
Rung: sheet (forced) — --as sheet given; the profile is reference material for repeated glances, 6 facets kept — subject: skills/ste/SKILL.md (file)
```

Output directory: `out/2026-10-03-050801-sheet-skills-ste-skill-md/` with `index.html`,
`sheet.png` (3840x2160) and `review/sheet-01.png` to `review/sheet-04.png` (1920x1080 each).

## Rounds

| Round | `verify.sh` | Fix |
|---|---|---|
| 1 | `render 1920x1080: FAIL data-verify="OVERFLOW:A;OVERFLOW:C;OVERFLOW:D;OVERFLOW:F;OVERFLOW:title"` | cut panel text, moved the bar citations into the labels, one-line "Not covered" |
| 2 | `render 1920x1080: FAIL data-verify="OVERFLOW:A"` | shortened the tree captions |
| 3 | four `ok`, exit 0 | — |

## Controller re-verification (same commit, same directory)

```
$ skills/explain/scripts/verify.sh out/2026-10-03-050801-sheet-skills-ste-skill-md/index.html
self-contained: ok
render 1920x1080: ok
citations: ok
prose: ok
$ python3 ~/.claude/skills/ste/scripts/ste_lint.py --html .../index.html | tail -1
0 errors, 0 warnings
```

Provenance in the title block:

- `data-root="/Users/valukin/karpathy"`, `data-kind="file"`
- Subject `skills/ste/SKILL.md (file)`, Source `/Users/valukin/karpathy`
- Commit `5e7cd92`, Dirty `dirty`, Date `2026-10-03`
- Not covered: `source PDF, relaxed rules, safety text, answer shape`

Checked against git at the time of the run: `git rev-parse --short HEAD` =
`5e7cd92`; `git status --porcelain` printed one line (`.beads/issues.jsonl`), so `dirty` is
correct. The artifact holds 6 `<section>` panels and 17 `<cite>` elements (counted with
html.parser); `cite_check.py` passed, and two citations were checked by hand (`skills/ste/SKILL.md:51` "at most 20 words
(5.1)." and `:184` "runs `ste_lint.py --html` on its final `index.html`").

Tile review by the controller (four tiles read, never `sheet.png`):

- A: tree of the profile file. B: annotated example with the three "correct STE that looks
  wrong" sentences. C: status table with 10 of the 27 substitution rows.
- D: four limits bars with `max N` labels. E: timeline of the usage protocol. F: rule list
  of the three `/ste` forms.
- Frame and title block complete. Nothing clipped, no ribbon, no empty panel. Citations are long and
visually heavy (monospace path + snippet after almost every sentence), and panels A, C and
D leave their bottom third empty. Both are content choices, not layout defects.

Verdict: **pass** (spec §9 criteria: `verify.sh` exit 0, no layout defect in the tiles,
opens from `file://`, provenance filled with the correct dirty flag).

## Skill defects found by the run (inputs to the wave's fix round)

1. `SKILL.md` convention 5: "kebab-case" is not defined for a path subject (`/`, `.`, case,
   full path or basename); the timestamp time zone is not stated.
2. `SKILL.md` convention 5: the output root `~/karpathy/out/` is fixed; no rule for another
   working directory.
3. `SKILL.md` rung line: no rule for the `<reason>` text under a forced rung.
4. `rungs/sheet.md` §3 and the template's `--tb-height: 262px`: with 6 panels, "Not covered"
   holds one line (about 60 characters); a two-line list gave `OVERFLOW:title`; no remedy
   is given.
5. `rungs/sheet.md` and the template: no pattern for where a `<cite>` goes inside the
   non-prose primitives (tree, bars, status table, timeline). A note line under each bar
   gave `OVERFLOW:D`. There is no advice on short snippets.
6. `templates/sheet.html` ribbon at `top: 0` covers the panel tag and the `<h2>`.
7. Review tiles are quadrants cut at x = 960 CSS px. The middle panels (B, E) are split
   across two tiles, and the reviewer never sees them whole.
8. `rungs/sheet.md` §3 step 3: "delete the author comments" does not say if the CSS
   comments count.
9. `rungs/sheet.md` §4: the `<path>` for `git ls-files --error-unmatch` is not stated to be
   relative to the repo root or to the subject's directory.
