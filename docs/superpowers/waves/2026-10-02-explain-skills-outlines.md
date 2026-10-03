# explain-skills — inline outlines for the ready low-risk waves

Status: waves `ste` and `video-spike` done (2026-10-03). Wave `explain-sheet` outline
presented 2026-10-03, **awaiting the user's go**; nothing filed in br for it yet.
Map: `2026-10-02-explain-skills.yaml`. Spec: `../specs/2026-10-02-explain-skills-design.md`.

Order on go: create `feature/explain-skills` from `main` → `br init` if needed →
one `-t epic` br issue per wave (`wave-ste`, `wave-video-spike`) → one task issue per
item below with `--external-ref <this file>#<wave>-task-<n>`, `--labels wave-<n>`,
`--parent <epic>` → execute. Plan amendment applies: contracts, not code.

## Wave `ste` (8 tasks)

Outcome: the STE-80 profile is a user-only skill reachable by path, the lint errors
only on deterministic rules, and a live run proves zero errors.

1. Branch + scaffold: `feature/explain-skills`; `skills/ste/{SKILL.md,scripts/,tests/fixtures/}`;
   symlink `~/.claude/skills/ste -> ~/karpathy/skills/ste`.
2. Profile `SKILL.md`: frontmatter `name`, `description`, `disable-model-invocation: true`,
   `argument-hint: "[text or request]"`; the `/ste` contract (spec §4.1); kept rules with
   Issue 9 rule numbers; relaxed list; ~25-entry substitution table verified against the
   extracted Issue 9 text (`/tmp/ste9.txt`; re-extract per spec §4.2 if gone) with page
   labels; PDF URL + sha256 + extraction command; usage protocol (spec §4.4).
3. Lint text model (TDD): `tokenize(text: str) -> list[Block]`;
   `Block(kind: 'para'|'ol-item'|'ul-item', sentences: list[Sentence])`;
   `Sentence(text: str, line: int, col: int, words: int)`. Tests: sentence boundaries
   incl. `)` `"` `*` `_` after a terminator; list-item boundaries; parenthetical, quoted,
   number+unit and code-span tokens; skipped frontmatter/fences/headings/tables/URLs.
4. Rules + CLI (TDD): `lint(blocks: list[Block]) -> list[Finding]`;
   `Finding(line: int, col: int, severity: 'E'|'W', rule: str, message: str)`;
   `main(argv: list[str]) -> int`. Tests assert per rule code (spec §4.3.3); the
   must-not-error set (spec §4.5); exit codes 0/1/2; output line format and summary line.
5. `--html` mode (TDD): `html_to_blocks(html: str) -> list[Block]`; fixture with a 12-link
   `nav`, implicit `</li>`, a `data-ste="skip"` subtree, `ol` items in the 21–25 band,
   `<cite>` skipping (spec §4.3.2).
6. Fixtures + broken-state pass: `tests/fixtures/clean.md` (Issue 9 examples cited by
   rule), `tests/fixtures/artifact.html`; every assertion shown to fail with its rule
   disabled before it counts.
7. Live run: a subagent reads `~/.claude/skills/ste/SKILL.md` by path and explains a real
   subject; lint → zero errors; baseline without the profile; both counts into
   `docs/superpowers/spikes/2026-10-02-ste-live-run.md`.
8. User acceptance: the user runs `/ste` bare and with text (cannot be done by Claude with
   `disable-model-invocation: true`).

Evidence: `cd skills/ste && python3 -m unittest discover -s tests` → `OK`; lint exit 0 on
both fixtures; the live-run note.

## Wave `video-spike` (4 tasks, timeboxed to one session)

1. Scaffold `spike-video/` with `npx create-video@latest` (blank TS); render the default
   composition; record whether Node 25 works, else `brew install node@22` (keg-only) and
   record it.
2. Narration: `say` → 3 WAVs + `afinfo` durations JSON; Kokoro via
   `uv run --python 3.12 --with kokoro-onnx` with model + voices under
   `spike-video/models/`. Claude cannot judge voice quality — both WAVs go in the findings
   for the user to compare.
3. Pipeline: `script.json` contract (scene id, component, props, narration text, audio
   path); only the scene components the three scenes need; `durationInFrames` computed
   from the durations JSON; one command `make.sh` → `out/video.mp4`.
4. Measure + findings: wall time per video-minute, `du -sh` of deps and models, iteration
   count, Remotion license tier confirmed; `docs/superpowers/spikes/2026-10-02-video-pipeline.md`
   with pass / fail / inconclusive against spec §8.3.

Runs concurrently with wave `ste` (disjoint files, same base).

## Wave `explain-sheet` (8 tasks)

Outcome: `/explain <file> --as sheet` builds a self-contained, cited, verified sheet from
a real file. Spec authority: §3 (layout), §5 (lines 285–460), §6 (461–507), §9 live run 1.
Depends on wave `ste` (closed at 3c37829): the lint at
`~/.claude/skills/ste/scripts/ste_lint.py` is consumed as-is, never edited here.

Rulings that the spec leaves open (reverse any you disagree with):

- The provenance element carries two machine-readable attributes: `data-root` (spec §5.3)
  and `data-kind="file|directory|topic|conversation"`, so `cite_check.py` knows when the
  every-panel-cites rule applies. A panel is a `<section>` element.
- Tests live in `skills/explain/tests/` (mirrors `skills/ste/`); the spec layout lists no
  test directory for `explain`. Broken-state fixtures (a panel that overflows, an 11 px
  element, a remote `<script src>`) derive from the template so every check is validated
  against a failing artifact, not only a passing one.
- The self-containment parser is a Python heredoc inside `verify.sh` (spec §3 names exactly
  three scripts); `verify.sh` treats lint exit 2 (usage error) as a failed check, distinct
  from exit 1.
- The shipped template carries topic-kind demo content (no citation obligation, no
  machine-specific `data-root`); the file-kind path is exercised by the fixtures and the
  live run.
- Live run 1 is executed Claude-side first (a subagent follows `SKILL.md` by path, like the
  `ste` live run) and recorded in `docs/superpowers/spikes/2026-10-03-explain-sheet-live-run.md`
  because `out/` is gitignored; the user's own `/explain` run is the acceptance task.

1. Scaffold + `skills/explain/SKILL.md` (≈100 lines, spec §5.1–5.3, §5.6): directories
   `skills/explain/{rungs,templates,scripts,tests/fixtures}`; symlink
   `~/.claude/skills/explain -> ~/karpathy/skills/explain`; frontmatter `name: explain`,
   `description: Use when the user invokes /explain …`, `disable-model-invocation: true`,
   `argument-hint: "<subject> [--as ste|sheet|page|video]"`. Body: `$ARGUMENTS` parsing
   (last `--as` wins and is removed; unknown rung → error listing the four names; empty →
   usage with the hint); subject resolution in the spec's order with the path-candidate
   rule and "a missing path is an error, never a topic"; the rung table; the rung line
   `Rung: <rung> (chosen|forced) — <reason> — subject: <subject> (<kind>)` printed before
   building; the video fallback (`--as video` without `rungs/video.md` → page with step
   captions, and says so); the facet cap with "Not covered"; conventions 1–7 of §5.3 with
   the output-directory rule `out/YYYY-MM-DD-HHMMSS-<rung>-<slug>/` (slug ≤ 40 chars,
   never overwritten); the STE profile read by path (`~/.claude/skills/ste/SKILL.md`);
   pointers to `rungs/<rung>.md`, read only when that rung is chosen. Evidence: line count
   near 100; the skill appears in the slash menu of a new session (user-visible).
2. `scripts/snapshot.sh` (spec §5.4, parallel with 3): `snapshot.sh <input.html>
   <output.png> [width=1920] [height=1080] [scale=2]`; Chrome flags as specified with a
   fresh `--user-data-dir`; Chrome backgrounded, PNG polled, Chrome killed on PNG or after
   60 s (argument or env override for tests); success = PNG exists and is non-empty; pad
   1 px with `sips --padToHeightWidth`, tiles ≤ 1920x1080 via `sips -c … --cropOffset
   (y+1) (x+1)` into `<output dir>/review/<stem>-NN.png`, last row clamped; assert PNG and
   tile sizes with `sips -g pixelWidth -g pixelHeight`; exit non-zero on any mismatch or
   timeout. Tests (`tests/test_snapshot.py`, subprocess): a fixed HTML at `1920 1080 2` →
   3840x2160 PNG and 4 tiles of the asserted sizes; at `1440 6000 1` → 6 tiles; a
   non-existent input → non-zero exit and no PNG; a 1 s timeout against a page that never
   finishes loading → non-zero exit, no Chrome process left.
3. `scripts/cite_check.py` (TDD, stdlib; spec §5.5 item 3, parallel with 2):
   `check(html: str, html_dir: str) -> list[str]` (one failure message each, empty = pass)
   and `main(argv: list[str]) -> int` (prints the failures, exit 0/1, 2 on usage). Reads the
   provenance `data-root`/`data-kind` and every `<cite data-path data-line data-snippet>`;
   fails when `data-root` is missing and a path citation exists, the file is missing, the
   line is out of range, or the whitespace-normalized snippet is not in that line; for
   `data-kind` file or directory also fails every `<section>` without a `<cite>`; URL
   citations (`data-path` starting with `http://` or `https://`) are skipped. Tests: one per
   failure kind, the topic-kind document with cite-less sections passes, a snippet that
   differs only in whitespace passes, a 13-word snippet is reported.
4. `scripts/verify.sh` (spec §5.5; after 2 and 3): `verify.sh <index.html>`; check 1
   self-containment through `html.parser` (the `src`/`srcset`/`poster`/non-`a` `href`/
   `@import`/`url(` rules with `http://`, `https://`, `//` targets; escaped code samples do
   not trip it); check 2 reads `<meta name="explain-rung">`, dumps the DOM per viewport
   (`1920,1080` for sheet; `1440,900` and `500,844` for page) with backgrounded Chrome,
   polls stdout for `</html>`, kills Chrome, requires `<html data-verify="OK">` and prints
   the status value on failure; check 3 `cite_check.py`; check 4
   `python3 ~/.claude/skills/ste/scripts/ste_lint.py --html` (exit 1 and exit 2 are both
   failures, reported differently). One line per check (`ok`/`FAIL`), exit 0 only when all
   four pass. Tests (`tests/test_verify.py`, subprocess, fixtures): a remote `<script src>`
   fails check 1 while an escaped sample inside `<code>` passes; a document whose guard
   writes `OVERFLOW:C` fails check 2 with that value in the output; a dangling cite fails
   check 3; a 26-word sentence fails check 4; the all-good fixture exits 0.
5. `templates/sheet.html` (spec §6; after 4): fixed 1920x1080 canvas, frame and title
   block, 12x2 grid, panels A–F with header bars (letter tag, title, caption), the six body
   primitives each as a documented HTML pattern with an author comment, the palette and
   type rules with an explicit font size (≥ 12 px) on every element the template uses
   including `code`, `pre`, `button`; `<meta name="explain-rung" content="sheet">`;
   `data-ste="skip"` on the non-prose primitives only; the `<cite>` pattern; the provenance
   block with `data-root`/`data-kind`, commit, dirty flag, date, "Not covered"; the guard
   script (≈30 lines, synchronous in `load`, measures panels and document against the canvas
   constants and `innerWidth`, smallest font size, `window.onerror`; absolutely positioned
   red ribbons; writes `OK` or the `;`-list into `<html data-verify>`; never touches
   `document.title`). Evidence: `verify.sh templates/sheet.html` exits 0; `snapshot.sh
   templates/sheet.html /tmp/sheet.png 1920 1080 2` yields 3840x2160 and 4 tiles; the
   broken-state fixtures for task 4 are regenerated from this template and re-verified
   (`OVERFLOW:<letter>`, `SMALLTEXT:11`, `CANVAS`, `JSERROR` each observed once).
6. `rungs/sheet.md` (spec §6 authoring rules + §5.3 build procedure; after 5): one
   question per panel; ≤ 250 words per panel; limits as bars; panel A is the map, panel B
   the annotated example when instances exist; no empty panel; the facet cap; every panel
   cites for file/directory subjects; the provenance recipe (`git rev-parse
   --show-toplevel`, `HEAD`, `git status --porcelain` → dirty, `git ls-files
   --error-unmatch` → untracked); the author notes learned in wave `ste` (close every
   element; no `data-ste="skip"` on an unclosed element; icons and `<img>` outside
   sentences; quotes as `“…”` or `<q>`; `WARNING:` in its own `<p>`; table cells are not
   linted); the build loop (fill template → `verify.sh` → `snapshot.sh … 1920 1080 2` →
   read the tiles → fix → re-run both) and the handoff (`open index.html` outside
   subagents); "palette duplicated in both templates — change both". Evidence: the file is
   linted with `ste_lint.py` → 0 errors.
7. Live run 1 (spec §9, after 6): a subagent reads `~/.claude/skills/explain/SKILL.md` by
   path and executes `/explain skills/ste/SKILL.md --as sheet` by hand; the controller
   re-runs `verify.sh` and `snapshot.sh` on the produced directory, reads the four tiles,
   checks the rung line, the slug, and that the provenance commit and dirty flag match
   `git` at build time; records the commands, outputs, tile verdict and any template or
   rung-note fixes in `docs/superpowers/spikes/2026-10-03-explain-sheet-live-run.md`.
8. User acceptance: the user runs `/explain skills/ste/SKILL.md --as sheet` in a new
   session, opens `index.html` and `sheet.png`, and reports. Closes only on that report.

Order: 1 → {2, 3} in parallel → 4 → 5 → 6 → 7 → 8. Ownership per the map (`skills/explain/`
except `rungs/page.md` and `templates/page.html`, the symlink, the live-run note).

Evidence for the wave: `cd skills/explain && python3 -B -m unittest discover -s tests` →
`OK`; `verify.sh <run-1 dir>/index.html` exit 0; `snapshot.sh <run-1 dir>/index.html
<run-1 dir>/sheet.png 1920 1080 2` with 4 tiles of the asserted sizes; the rung line as
specified in spec §5.2; the live-run note; the user's report.

## Wave `explain-page` (7 tasks) — go given 2026-10-03, br epic kp-9ft

Observable outcome: `/explain <subject> --as page` builds a responsive single-file page
(sticky nav, `<details>` walkthroughs, inline-SVG diagrams, steps player); `verify.sh`
reports `OK` at 1440x900 and 500x844; `/explain <code question>` with no `--as` picks the
rung from content shape. The scripts already handle the page rung (two viewports with
`#verify` in `verify.sh`, `SNAPSHOT_FRAGMENT` in `snapshot.sh`): no script work.

Risk: low (map). Owns: `skills/explain/rungs/page.md`, `skills/explain/templates/page.html`,
plus `skills/explain/SKILL.md`, `rungs/sheet.md` §7 and the `sheet.html` palette comment
(explain-sheet is closed; no conflict).

1. `templates/page.html` — self-demo of itself: sticky `nav` (lint-skipped), one `<section>`
   per facet, code blocks captioned `path:line`, `<details>`, three documented SVG patterns
   (flow, sequence, layers), steps player (prev/next, one diagram state per step),
   provenance footer, `<meta name="explain-rung" content="page">`, explicit >= 14 px on
   every element incl. `code`/`pre`/`button`, palette block identical to `sheet.html`.
   Guard inside `load`: `#verify` opens every `<details>` and stacks all step states;
   measures `HSCROLL` vs `innerWidth`, `SMALLTEXT:<px>`, `JSERROR`; never touches
   `document.title`. Vanilla JS <= 200 lines incl. guard.
   Evidence: `verify.sh templates/page.html` four `ok`; `wc -l` of the script blocks.
2. `tests/test_page_template.py` — guard cases derived from the template at test time:
   `HSCROLL` at 500 px, `SMALLTEXT` for a 13 px rule, `JSERROR`, `#verify` opens details
   and stacks steps vs. without it, `data-verify` absent in the source, title unchanged.
   Each assertion shown false on the broken state. Full suite green:
   `cd skills/explain && python3 -B -m unittest discover -s tests`.
3. `rungs/page.md` (<= 150 lines, lint 0 errors) — when a page; section planning (facet =
   section = nav entry); template filling; steps player and diagram patterns; snapshot
   arguments `1440 6000 1` and `500 844 1` with `SNAPSHOT_FRAGMENT=verify`; tile-review
   faults; provenance by reference to `sheet.md` §4; "palette: change both".
4. `SKILL.md` pass, closes the four parked items — drop the "`rungs/page.md` does not
   exist" lines; video-fallback wording; slug: empty result -> `topic`; `git ls-files`
   step skipped when there is no repo; C4 `data-root` wording for a directory subject
   and a topic inside a repo; `rungs/sheet.md` §7 and the `sheet.html` palette comment
   lose the "while page.html does not exist" clause. <= 130 lines, strict YAML, lint 0.
5. Live run 2 — `/explain docs/superpowers/specs/2026-10-02-explain-skills-design.md
   --as page`. Note in `docs/superpowers/spikes/`; rounds and skill defects recorded;
   fixes folded back into the files of tasks 1-4.
6. Live run 3 — in `~/work/inavcalculator` (CodeGraph-indexed): `/explain how does a
   signed counterparty request flow through inavcalculator, from the HTTP filter to the
   signature check to the calculation`, no `--as`. Pre-declared: `Rung: page (chosen) — a
   step-through request flow with more than 6 facets`. Three claims spot-checked against
   `path:line`. A different rung with a defensible printed reason passes; otherwise it is
   a selection-rule defect. Other indexed repos: omnimailcore, esiaintegrationservice, postman.
7. User acceptance — the user runs `/explain <a spec or plan of their own> --as page`.

Process: subagent per task (briefs/reports in the shared SDD workspace, prefix `ep-`),
whole-wave review on fable, one fix dispatch, one re-review; task 7 closes the wave.
Rulings: ownership extension above; run-3 subject and expected rung; no separate review
seat for the live-run notes.

## Later waves

The
`video` rung stays deferred until the user's fold-in decision exists (narrator decided:
Kokoro `af_heart`).
