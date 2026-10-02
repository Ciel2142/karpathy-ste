# Explain skills (`ste` + `explain`) — design

Date: 2026-10-02
Status: approved in conversation; revised after a three-reviewer pass and first-hand
fact verification (2026-10-02); written spec pending user review

## 1. Purpose

Karpathy's note (2026-10) argues that as models do more of the legwork, human work
moves up to oversight and understanding, and that models should help by producing
better-shaped outputs: controlled-language prose (ASD-STE100), diagrams, interactive
web pages, and narrated explainer videos — large, custom, discardable artifacts.

This design turns that note into two personal Claude Code skills:

- `ste` — a fixed, checkable prose profile derived from ASD-STE100 ("STE-80").
- `explain` — an explicit router that builds one discardable artifact (sheet, page,
  or video) from a topic, a file, or the current discussion, grounded in real sources
  and verified by deterministic checks plus a visual review before handoff.

Intended uses, in priority order:

1. Understanding code and architecture — a repo, a PR, a flow Claude just wrote.
2. Reviewing Claude's own artifacts — specs, plans, wave maps, review findings.
3. Learning any topic, code or not.

Success means: one command produces an artifact that a reader can trust (every claim
cites a source and the citation is machine-checked), that opens as a single file
anywhere, and that passed its own verification script and Claude's look at the rendered
output before it was handed over.

## 2. Scope

In scope:

- Skill `ste`: rule set, lint script (Markdown and HTML), usage protocol, tests.
- Skill `explain`: router, conventions, `sheet` and `page` rungs, templates, snapshot
  and verification scripts, live verification runs.
- A throwaway spike that decides whether a `video` rung is feasible on this Mac.
- The `video` rung itself, only if the spike passes (final wave).

Out of scope:

- Automatic triggering of either skill. Both carry `disable-model-invocation: true`
  (§3); only the user invokes them, and `explain` reaches `ste` by file path, never
  through the Skill tool.
- Committing artifacts into any repo; multi-file sites; external assets or CDNs; saved
  copies of web sources.
- A full ASD-STE100 dictionary check (see §4.2).
- manim. It is reconsidered only if the user asks for the literal 3b1b math look.

## 3. Repository layout and installation

`~/karpathy` is a git repository and owns everything. Skills are symlinked into
`~/.claude/skills/`, the same pattern already used for `qmemd-memory`.

```
~/karpathy/
  .gitignore                           out/, spike-video/, video-workspace/, node_modules/
  docs/superpowers/specs/              this spec
  docs/superpowers/specs/assets/       2026-10-02-ste-reference-sheet.jpg (the reference sheet)
  docs/superpowers/spikes/             spike findings notes (kept)
  skills/ste/
    SKILL.md
    scripts/ste_lint.py
    tests/test_ste_lint.py
  skills/explain/
    SKILL.md
    rungs/sheet.md
    rungs/page.md
    rungs/video.md                     final wave, only if the spike passes
    templates/sheet.html
    templates/page.html
    video/                             final wave: Remotion sources (package.json, scenes), versioned
    scripts/snapshot.sh                html -> png + review tiles (headless Chrome, sips)
    scripts/verify.sh                  self-containment, render status, citations, lint
    scripts/cite_check.py              every citation resolves to its path, line and snippet
  spike-video/                         throwaway, gitignored
  video-workspace/                     final wave, gitignored: installed deps and renders only
  out/                                 artifacts, gitignored, never committed

~/.claude/skills/ste     -> ~/karpathy/skills/ste
~/.claude/skills/explain -> ~/karpathy/skills/explain
```

Frontmatter (fields verified against code.claude.com/docs/en/skills):

- Both skills: `name`, `description` ("Use when …" form, as in
  `~/.claude/skills/verify-before-assert/SKILL.md`), `disable-model-invocation: true`.
  With that flag only the user can invoke the skill (`/ste`, `/explain`), the
  description is not loaded into context, Claude Code blocks any Skill-tool call to it,
  and it is not preloaded into subagents.
- `explain` additionally: `argument-hint: "<subject> [--as ste|sheet|page|video]"`; the
  body reads `$ARGUMENTS` and parses `--as` from it.
- Consequence: `explain`, and any subagent used in a live run, reach the STE profile
  by reading `~/.claude/skills/ste/SKILL.md` with the Read tool and running
  `~/.claude/skills/ste/scripts/ste_lint.py` directly.

## 4. Skill `ste`

### 4.1 Trigger

User-only, via `/ste`. The description still states the intent (STE, Simplified
Technical English, STE-80) for the `/` menu, but with `disable-model-invocation: true`
the harness never selects the skill on its own. `explain` and live-run subagents use
the profile by path (§3).

Invocation contract: `/ste <text or request>` rewrites the given text, or answers the
given request, in STE-80. A bare `/ste` rewrites Claude's previous answer in STE-80.
The profile applies to that one answer; it does not persist for the session.

### 4.2 The STE-80 profile

The value of the skill over a bare prompt is that the definition of "80% STE" is fixed
and does not drift between sessions. Source for every rule and dictionary entry:
ASD-STE100 Issue 9 (2025-01-15), public PDF at
`https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf`. The PDF is AES-protected
with an empty password; its text extracts with
`uv run --with pypdf --with cryptography python3` (434 pages). `SKILL.md` records the
PDF URL, its sha256 and that extraction command, cites the rule number next to each
rule, and cites the Issue 9 printed page label (for example `2-1-E7`) next to each
substitution — never a line number of the extraction, which is ephemeral.

Kept (structural rules and verb rules, verified in Issue 9):

- Procedural sentence: at most 20 words (Rule 5.1). Descriptive sentence: at most 25
  words (Rule 6.3). Numbers, abbreviations, hyphenated words and quoted text count as
  one word each.
- Paragraph: at most 6 sentences (Rule 6.6), one topic, topic sentence first (6.5).
- One instruction per sentence; simultaneous actions are the only exception (5.2).
- Procedures use the imperative. Safety text uses `WARNING:` or `CAUTION:` followed by
  a simple command, then the risk in a second sentence (7.1–7.3).
- Verb forms allowed (3.2): infinitive, imperative, simple present, simple past, simple
  future, past participle as an adjective (3.3). Not allowed: `-ing` verb forms, allowed
  only as a technical noun or modifier such as "landing gear" (3.5); complex
  constructions with auxiliaries, which excludes perfect tenses (3.4); passive voice in
  procedures. In descriptive text the passive is allowed only when the agent is unknown
  (3.6).
- Active voice with the agent named. `HAVE` is an approved main verb ("the pump has
  fixed blades" is correct STE).
- One word, one meaning, one part of speech. The same word for the same thing every
  time. No elegant variation.
- Keep articles (4.5). No contractions (4.2).
- Multi-word nouns of at most 3 words (2.1); break longer ones with prepositions.
- Vertical lists for complex text (4.3).
- A substitution table of about 25 unapproved words mapped to the approved
  alternative. Entries verified in the Issue 9 dictionary: `ensure -> MAKE SURE`,
  `utilize -> USE`, `prior to -> BEFORE`, `commence -> START`, `replenish -> FILL`,
  `terminate -> STOP`, `attempt -> TRY`, `perform -> DO`, `in the event of -> IF`,
  `enough -> SUFFICIENT`. Not entries, so not in the table: `in order to` (Issue 9 has
  only `order -> SEQUENCE / TELL`). Meaning-dependent words stay guidance only and out
  of the lint: `ABOUT` is approved as "concerned with", while `APPROXIMATELY` is the
  approved word for quantity. A word enters the table only when every dictionary sense
  of it (all parts of speech) is unapproved: `attempt` (n, v) qualifies; `close` does
  not, because `close (v)` is approved. At implementation time the remaining entries
  are taken from the extracted dictionary text and cited by page label; an entry that
  cannot be found there is dropped, not guessed.

Relaxed (the 20%):

- The approved dictionary of about 900 general words is not enforced as a hard limit.
  The specification itself allows company-defined technical names and technical verbs;
  the profile uses that door generously. Code identifiers, commands, file paths, product
  names, and protocol terms stay verbatim in backticks and are defined on first use.
- Spelling-convention and punctuation minutiae of the specification are not enforced.

Markdown headings and lists are allowed and encouraged (vertical lists are an STE rule).

### 4.3 `ste_lint.py`

Purpose: make STE-80 checkable so Claude corrects measured findings instead of
guessing. Python 3, standard library only. The design rule for severities: a rule is an
error only when its detection is deterministic; every heuristic is a warning, because
"zero errors" is the bar and a lint that errors on correct STE is unusable.

Command contract:

```
python3 ste_lint.py [--html] [FILE]
```

- Reads `FILE`, or stdin when `FILE` is absent. Default input is Markdown or plain
  text; `--html` parses HTML (§4.3.2).
- Output: one finding per line, `LINE:COL  E|W RULE  message`, sorted by line, then a
  summary line `N errors, M warnings`.
- Exit codes: `0` no errors; `1` at least one error; `2` usage error (unreadable file,
  bad flag). Warnings never change the exit code.

#### 4.3.1 Text model (both modes)

- Sentence boundaries: `.`, `!`, `?` followed by whitespace or end of text, also when
  a closing `)`, `"`, `*` or `_` sits between the terminator and the whitespace
  (so `**Note.** Next step` is two sentences). Abbreviation allowlist: `e.g.`, `i.e.`,
  `etc.`, `vs.`, `Mr.`, `Dr.`, `No.`. The end of a list item is an additional
  boundary, with or without a final period; an item may hold several sentences, each
  counted on its own. A blank line ends a paragraph block; every list item is its own
  block.
- Skipped entirely: YAML frontmatter, fenced code blocks, headings (`#` lines), table
  rows (`|` lines), URLs.
- Tokens that count as one word, per Issue 9 Section 8: an inline code span; text in
  parentheses (Rule 8.5 — the parenthetical is also linted as a sentence of its own);
  quoted text in `"…"` or `“…”` (8.6, kept verbatim and not checked by `WORD` or
  `CONTRACTION`); a number followed by a unit from the script's unit list (8.6, for
  example `10 mA`, `3 s`, `25 %`); hyphenated words, abbreviations and alphanumeric
  identifiers are single whitespace tokens already.
- Word cap: 25. Items of an ordered list are procedures by intent, not by proof, so a
  21–25 word item is the warning `LENGTH-PROC`, never an error.

#### 4.3.2 `--html` mode

Standard-library `html.parser`. Skipped elements: `script`, `style`, `svg`, `pre`,
`code`, `cite`, `nav`, `noscript`, `template`, and any element with `data-ste="skip"`
together with its subtree. Every non-inline element is a block boundary; the inline
set is `a`, `abbr`, `b`, `cite`, `code`, `em`, `i`, `kbd`, `mark`, `q`, `s`, `small`,
`span`, `strong`, `sub`, `sup`, `time`, `u`, `var`. Headings and table cells are skipped
like their Markdown counterparts; `li` inside `ol` takes the `LENGTH-PROC` band;
inline `code` becomes the placeholder token. Because `html.parser` emits no end tag for
an omitted `</li>`, `</td>` or `</p>`, a skipped or block region also ends when its
parent ends; the templates close every element explicitly so this path is rarely
needed. The templates mark every non-prose primitive `data-ste="skip"`: annotated
examples (their samples are deliberately non-STE), trees, timelines, bar labels and
status-table cells.

#### 4.3.3 Rules

| Rule | Severity | Detection |
|---|---|---|
| `LENGTH` | error | sentence over 25 words, counted per §4.3.1 |
| `CONTRACTION` | error | `n't`, `'ll`, `'re`, `'ve`, `'d`, `'m`, and `'s` only in `it's`, `he's`, `she's`, `that's`, `what's`, `there's`, `here's`, `let's`, `who's`, `where's`, `how's` |
| `WORD` | error | an entry of the substitution table, whole-word, case-insensitive; message names the approved alternative |
| `LENGTH-PROC` | warning | an ordered-list item of 21–25 words (procedures should stay at 20, Rule 5.1) |
| `PARAGRAPH` | warning | more than 6 sentences in a block that is not a list |
| `PERFECT` | warning | `has`, `have`, `had` followed by a participle |
| `PROGRESSIVE` | warning | a form of `be` followed by an `-ing` word |
| `PASSIVE` | warning | a form of `be` followed by an `-ed` word or a listed irregular participle |
| `GERUND` | warning | a sentence that starts with an `-ing` word |

The verb heuristics are warnings because they fire on correct STE: "the pump has fixed
blades" (participle as adjective after approved `HAVE`), "the cause is landing gear
vibration" (technical noun), "the valve is closed" (state adjective). Claude reviews
warnings and keeps approved constructs. The script does not attempt noun-cluster
detection; that needs part-of-speech tagging and would be noisy.

### 4.4 Usage protocol

1. Claude drafts under the profile.
2. For any text of more than five sentences, or any text that will land in an
   artifact or a document, Claude writes the draft to a temporary file, runs the lint,
   fixes errors, reviews warnings, and then answers.
3. Short chat answers skip the lint.
4. Technical names are kept verbatim in backticks and are not rewritten.
5. `explain` runs `ste_lint.py --html` on the final `index.html` as part of
   `verify.sh` (§5.5), so edits made during layout fixes are linted too.

### 4.5 Verification

- `tests/test_ste_lint.py` (standard `unittest`; run from `skills/ste/` with
  `python3 -m unittest discover -s tests`):
  - for every error rule, one input that must produce that specific rule code,
    asserted by rule code, not by "some finding exists";
  - for every warning rule, one input that must produce it as a warning and must not
    change the exit code;
  - must-not-error inputs: "The pump has fixed blades.", "The cause of the noise is
    landing gear vibration.", "The valve is closed.", a seven-item numbered procedure,
    an eight-item bulleted list without final periods, a 24-word ordered-list item, a
    backticked banned word, a quoted banned word (`the label says "ensure"`), a
    parenthetical that pushes a naive count past 25, `10 mA` counted as one word, and
    `**Note.** Next step.` counted as two sentences;
  - clean inputs taken from Issue 9 rule examples, cited by rule number, that must
    produce no findings at all;
  - an HTML fixture exercising skipped elements, a `nav` with twelve links, implicit
    `</li>` closes, `data-ste="skip"` subtrees, `ol` items in the 21–25 band and
    `<cite>` skipping;
  - exit-code checks for 0, 1, and 2.
- Each assertion is validated against the broken state (the rule disabled or the input
  altered) before it counts, per the house rule on coverage assertions.
- One live run: a subagent that reads `SKILL.md` by path explains a real subject in
  STE-80; the output is linted and must have zero errors. A baseline run without the
  profile is linted for comparison and both counts are recorded in
  `docs/superpowers/spikes/<date>-ste-live-run.md`.

## 5. Skill `explain`

### 5.1 Trigger and invocation

User-only, via `/explain` (§3). Arguments arrive in `$ARGUMENTS`:

```
/explain <subject> [--as ste|sheet|page|video]
```

Argument parsing: the last `--as <rung>` pair in `$ARGUMENTS` wins and is removed;
the rest, trimmed, is the subject. An unknown rung is an error that prints the four
valid names. Empty `$ARGUMENTS` is a usage error that prints the `argument-hint`.

Subject resolution, in order:

1. A path candidate — the subject starts with `/`, `~` or `.`, or its first
   `/`-separated component exists in the current directory — that exists: a file is
   read in full; a directory is mapped (tree plus key files; CodeGraph when a
   `.codegraph/` index exists, per the global instructions). A path candidate that
   does not exist is an error; it is never silently treated as a topic. Subjects such
   as `TCP/IP`, `CI/CD` or `Next.js` are not path candidates and fall through to
   topics.
2. `this`: the last file read or written in the conversation; if there is none, the
   last substantial turn (an explanation, a review, a plan), labelled "conversation".
3. Otherwise a topic string. Claude uses its own knowledge and, when the user allows,
   web lookups. Provenance then states "model knowledge" or lists the URLs; it never
   pretends a source was read.

### 5.2 Rung selection

When `--as` is omitted, the rung is chosen by the shape of the content, never by
"richest format available":

| Rung | Choose when | Typical subject |
|---|---|---|
| `ste` (chat text) | fits one screen; procedural or a direct answer; the user is mid-task | a failure cause, a 5-step procedure |
| `sheet` (static page, exported to PNG) | reference material to glance at repeatedly; at most 6 facets; "overview of X" | architecture at a glance, spec summary, a rule system |
| `page` (interactive single-file HTML) | content has state to explore: step-through flow, before/after, toggles, expandable walkthrough; more than 6 facets | PR walkthrough, plan with waves, comparison |
| `video` (narrated mp4) | temporal narrative where motion carries meaning and passive consumption is wanted | data through a pipeline, algorithm steps, a handshake |

A facet is one question the artifact answers, which is one panel on a sheet or one
section on a page.

Rules:

- The rung line is always printed before building, including under `--as`:
  `Rung: sheet (chosen|forced) — <reason> — subject: <resolved subject> (<kind>)`,
  where kind is file, directory, conversation or topic.
- `video` is offered by the router only when `rungs/video.md` exists. `--as video`
  without it builds a `page` whose steps player carries the would-be narration as step
  captions, and says so.
- A forced rung that does not fit the content (a sheet with more than 6 facets) keeps
  the 6 most important facets and lists the dropped ones in the title block under
  "Not covered".
- The `ste` rung produces chat text only; it creates no output directory.

### 5.3 Conventions for every artifact rung

1. Prose through the STE profile. `SKILL.md` of `ste` is read by path; the final
   `index.html` passes `ste_lint.py --html` with zero errors.
2. Grounded and checkable. When the subject is code or a repo file, the real source is
   read first. Every claim carries a citation rendered as
   `<cite data-path="…" data-line="…" data-snippet="…">path:line "snippet"</cite>`,
   where the snippet is at most 12 words copied verbatim from that line; `cite_check.py`
   verifies all three. For a file or directory subject every panel (sheet) or section
   (page) must contain at least one `<cite>`; content with no source does not belong
   in a grounded artifact. Provenance (title block or footer) carries: the resolved
   subject and its kind (file, directory, topic, conversation); the repo root, commit
   hash and a `dirty` flag when the subject is inside a git repository, where `dirty`
   means `git status --porcelain` printed anything; the date. A cited file that git
   does not track is marked "untracked" in the citation. The provenance element also
   carries `data-root="<absolute repo root, or the subject's directory when there is
   no repo>"`, which `cite_check.py` uses to resolve paths; a path citation without it
   fails. A "conversation" subject is marked "unverified", and any file it mentions is
   re-read and cited. URL citations carry a snippet found in the fetched page at build
   time; they are not re-verified later and no copies are saved.
3. One self-contained file. Inline CSS and JS, system fonts, no CDN, no build step.
   Opens from `file://` offline. Survives being sent as one file over Telegram or email.
   Checked statically by `verify.sh`.
4. Verified before handoff, in two layers. First `verify.sh` (§5.5) must exit 0.
   Then Claude reads the review tiles from `snapshot.sh` and checks what a script
   cannot: readable hierarchy, sensible layout, nothing misleading. Fix, re-run both.
5. Discardable output. `~/karpathy/out/YYYY-MM-DD-HHMMSS-<rung>-<slug>/` where
   `slug` is the kebab-cased subject, at most 40 characters. A directory is never
   overwritten; a re-run creates a new one. Contents: `index.html`; for sheets
   `sheet.png` (share render) and `review/sheet-NN.png` tiles; for pages
   `page-1440x6000.png`, `page-500x844.png` and their `review/page-<WxH>-NN.png`
   tiles; for videos `video.mp4` and `narration.md`. Gitignored, never committed, safe
   to delete wholesale.
6. Handoff: print the path; when running interactively for the user, `open
   index.html` (sheet, page) or `open video.mp4` (video); skip `open` inside subagents.
7. Language: artifacts are in English unless the user asks otherwise.

### 5.4 `scripts/snapshot.sh`

Renders an HTML file to PNG with headless Chrome and cuts review tiles with `sips`.
No other dependency; both are present on this machine and were verified.

```
snapshot.sh <input.html> <output.png> [width=1920] [height=1080] [scale=2]
```

- Invokes `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` with
  `--headless=new --disable-gpu --hide-scrollbars --window-size=W,H`
  (comma-separated) `--force-device-scale-factor=S --user-data-dir=<fresh temp dir>
  --screenshot=<output> file://<absolute input>`.
- Success is judged by the PNG existing and being non-empty, not by stderr, which
  always carries display-link noise on macOS.
- Bounded: Chrome runs in the background; a watchdog polls for the PNG and kills
  Chrome once it exists or after a timeout (default 60 s). This is mandatory, not
  insurance: with a fresh `--user-data-dir` Chrome 154 writes the PNG and then does not
  exit (reproduced on this Mac), and macOS has no `timeout(1)`.
- Review tiles: the PNG is first padded by one pixel on every side with
  `sips --padToHeightWidth`, then cropped with `sips -c H W --cropOffset (y+1) (x+1)`
  into tiles of at most 1920x1080 pixels, written to `<output dir>/review/<png
  stem>-NN.png`. The padding exists because `sips` treats `--cropOffset 0 0` as "no
  offset" and crops the centre, and returns the whole image for a crop flush with the
  bottom edge (both reproduced). The script asserts the PNG's and every tile's
  dimensions with `sips -g pixelWidth -g pixelHeight` and fails if any differ from the
  expected size; the last row of tiles is clamped to the image. A 3840x2160 sheet gives
  4 tiles; a 1440x6000 page gives 6. Claude reads the tiles, never the full render,
  because large images are downscaled before the model sees them and 14 px text in a
  tall render becomes unreadable.
- Chrome's `--screenshot` captures the window only; a tall window (for example
  `1440 6000 1`) is how a long page is captured. Headless Chrome clamps the viewport
  to a minimum width of 500 px (reproduced: `390,844` yields `innerWidth` 500), so the
  phone render is requested at `500 844 1`. Page renders are taken with `#verify` on
  the URL so that expanded details and stacked step states reach the tiles.

### 5.5 `scripts/verify.sh` and `scripts/cite_check.py`

```
verify.sh <index.html>
```

Runs four checks, reports each, exits non-zero if any failed:

1. Self-containment: parse the HTML (`html.parser`), never the raw text, so that
   escaped code samples showing `<script src="https://…">` do not trip it. Fail on any
   `src`, `srcset` or `poster` attribute on any element, any `href` on an element other
   than `a`, and any `@import` or `url(` inside `<style>` or a `style` attribute, whose
   target starts with `http://`, `https://` or `//`.
2. Render status: the template declares its rung in `<meta name="explain-rung"
   content="sheet|page">`; `verify.sh` reads it and dumps the DOM once per viewport —
   sheet `1920,1080`; page `1440,900` and `500,844` — with headless Chrome
   `--dump-dom --window-size=W,H --hide-scrollbars --user-data-dir=<temp>` of
   `file://<index.html>#verify`. Chrome is backgrounded, stdout is polled for
   `</html>`, then Chrome is killed (it does not exit on its own after the dump;
   reproduced). Each dump must contain `<html data-verify="OK">`. The guard script
   (§6, §7) runs synchronously inside the `load` handler — no `requestAnimationFrame`,
   no timers, both of which were seen to miss the dump — expands all `<details>` and
   stacks all step states when `#verify` is present, measures, and writes the result
   into the `data-verify` attribute of `<html>`: `OK`, or a `;`-joined list of
   `OVERFLOW:<panel>` (content exceeds its box on either axis), `CANVAS` (document
   exceeds the fixed canvas constants, sheet only), `HSCROLL` (document wider than the
   viewport), `SMALLTEXT:<px>` (smallest computed font size of a rendered element that
   has its own text, below the rung's minimum: 14 px page, 12 px sheet), `JSERROR`
   (any `window.onerror`). Measurements compare against canvas constants and
   `innerWidth`, never `innerHeight`, which headless Chrome reports 87 px short of the
   requested height. The attribute is written on every load so the ribbons and the
   status are always present; `document.title` is never touched, so a browser tab
   shows the artifact's title, not "OK".
3. Citations: `cite_check.py <index.html>` reads every `<cite>`; resolves `data-path`
   against `data-root`; fails if `data-root` is absent, the file is missing, the line
   is out of range, or the whitespace-normalized snippet is not on that line; for file
   and directory subjects also fails any panel or section that holds no `<cite>`.
   Prints one line per failure. URL citations are skipped.
4. Prose: `ste_lint.py --html <index.html>` exit 0.

### 5.6 Size discipline

`SKILL.md` stays near 100 lines: trigger, invocation, rung table, conventions, and a
pointer to one `rungs/*.md` file per rung. Rung files hold the specifics and are read
only when that rung is chosen.

## 6. Rung `sheet`

The reference is `docs/superpowers/specs/assets/2026-10-02-ste-reference-sheet.jpg`
(1280x640). The template encodes the grammar of its layout, not its content.

- Canvas: fixed 1920x1080 CSS pixels, `html, body { margin: 0 }`, exported at scale 2
  (3840x2160 PNG) for sharing. 16:9 is chosen over the reference's 2:1 because sheets
  travel as images on screens and phones.
- Frame: an engineering-drawing border and a title block. No zone rulers (their A–D
  letters collide with panel letters) and no "Sheet N of M" (always 1 of 1).
- Grid: 12 columns by 2 rows. Four to six lettered panels (A–F). Each panel has a
  header bar: letter tag, title, right-aligned caption.
- Title block: fixed bottom-right. Title; key: value pairs; provenance (§5.3 item 2);
  "Not covered" when a forced rung dropped facets; date.
- Six body primitives, each a documented HTML pattern in `templates/sheet.html`:
  1. tree — structure or map (panel A is always this: "what is it made of")
  2. annotated example — a monospace sample with keyed annotations. Markers live in a
     gutter column beside the sample, never inside the monospace line, so alignment
     holds; a keyed legend sits below. Panel B is this when the subject has instances
     to show (code, sentences, messages); otherwise panel B is the key flow or the
     decisive table.
  3. status table — rows with a ✓/✗ column
  4. limits bars — a number drawn as a horizontal bar on a tick scale with a "max N"
     label; a limit is never left as prose when it can be a bar
  5. timeline — horizontal nodes with captions
  6. rule list — short STE sentences, bulleted
- Palette and type: ink, muted, and line grays; one emphasis blue (approved,
  highlights); one alarm red (not approved, errors); light-gray box fill; system sans
  and system mono. No web fonts. Smallest font size 12 px, set explicitly for every
  element the template uses, including `code`, `pre` and `button`, whose Chrome
  defaults (13 px, 13.33 px) would otherwise decide the measurement.
- Authoring rules (`rungs/sheet.md`): one question per panel; at most 250 words per
  panel, no minimum; limits as bars; all prose STE-80; no empty panel; panel A is the
  map; every panel cites at least once for a file or directory subject (§5.3 item 2).
- Lint markers: the template carries `<meta name="explain-rung" content="sheet">`
  and marks the non-prose primitives — annotated example, tree, timeline, bar labels,
  status-table cells — with `data-ste="skip"`, so the lint reads only the prose.
- Guard script (inline, about 30 lines): synchronously inside the `load` handler,
  measures every panel on both axes and the document against the canvas constants
  (1920x1080), the smallest rendered font size, and JS errors; draws an absolutely
  positioned red ribbon on any failing panel (an in-flow ribbon inside an
  `overflow: hidden` panel would be clipped and invisible); writes `OK` or the failure
  list into `<html data-verify>` (§5.5 item 2) and never touches `document.title`.
  Zero cost when everything fits. `#verify` adds nothing on a sheet beyond the
  measurements.
- Export: `snapshot.sh index.html sheet.png 1920 1080 2`, which also writes the review
  tiles `review/sheet-NN.png`.

## 7. Rung `page`

Same visual family, no fixed canvas; responsive single file read in a browser.

- Structure: sticky section navigation (`nav`, skipped by the lint); STE-80 prose;
  code blocks captioned with `path:line`; `<details>` for expandable walkthroughs;
  provenance footer; `<meta name="explain-rung" content="page">`; smallest font size
  14 px, set explicitly for every element the template uses, including `code`, `pre`
  and `button`; every section cites at least once for a file or directory subject.
- Steps player: previous/next through a sequence of states with a diagram that changes
  per step. This is the one interactive pattern that justifies choosing `page` over
  `sheet` for flows, PRs, and wave plans. In the video fallback (§5.2) the narration
  text becomes the step captions.
- Diagrams: hand-written inline SVG from three documented patterns in
  `templates/page.html`: box-and-arrow flow, sequence, layered architecture. Mermaid is
  excluded because keeping the file self-contained would mean inlining about 2.5 MB.
- Budget: vanilla JS under about 200 lines including the guard; no frameworks.
- Guard script and `#verify` mode: synchronously inside the `load` handler, with
  `#verify` in the URL the page opens every `<details>` and renders all step states
  stacked; with or without it, the guard then measures horizontal overflow against
  `innerWidth`, the smallest rendered font size and JS errors and writes the status
  into `<html data-verify>` (§5.5 item 2). `document.title` is never touched.
- Verification: `verify.sh` dumps at `1440,900` and `500,844` (the headless minimum
  width; §5.4) and both must report `data-verify="OK"`. `snapshot.sh` renders
  `1440 6000 1` and `500 844 1`, both with `#verify`, and Claude reviews the tiles;
  there is no separate 1440x900 render because it is tile 1 of the tall one. Usable
  means: both statuses `OK`, navigation and steps player visible in the tiles.
- Shared palette is duplicated in both templates because self-contained files cannot
  import; `rungs/sheet.md` and `rungs/page.md` both say "change both".

## 8. Rung `video` — spike first

### 8.1 Question

Can a scripted pipeline on this Mac turn a script (narration text plus a scene list)
into a narrated mp4 reliably enough to be a skill?

### 8.2 Probe (throwaway, in `spike-video/`, timeboxed to one working session)

1. Scaffold Remotion with `npx create-video`. Remotion bundles its own FFmpeg since
   v4.0 (remotion.dev/docs/ffmpeg) through a platform compositor package that npm
   fetches once; no system ffmpeg is needed. Remotion on Node 25 is unverified: no
   `engines` block prevents the install, runtime behaviour is measured by the spike.
   If Node 25 breaks it, the spike may install an LTS through Homebrew `node@22`
   (keg-only, so the default `node` is unchanged) and must record that in the findings.
2. Narration baseline: macOS `say` to WAV (`--file-format=WAVE
   --data-format=LEI16@22050`, verified), durations read with `afinfo` (verified).
   Each scene's `durationInFrames` is computed from its clip length plus padding, so
   sync is computed, not eyeballed. Chrome and Remotion decode 16-bit PCM WAV.
3. Narration quality candidate: Kokoro-82M through `kokoro-onnx`, run with
   `uv run --python 3.12` in its own venv — `kokoro-onnx` requires Python `<3.14` and
   `kokoro` `<3.13` (PyPI metadata), Homebrew Python 3.12.14 is already installed, and
   onnxruntime ships a cp314 and cp313 arm64 wheel so it is not the blocker. Budget a
   model download of about 300 MB plus the voices file. The compact `say` voices are
   too robotic to ship; no premium voice is installed and no ElevenLabs key is set.
4. Scenes: only the scene components the three scenes need, chosen from the constrained
   set — title, bullets-appear, diagram-with-highlight-walk, code-with-line-highlights,
   before/after. Each scene must carry one motion that means something (a highlight
   walking a diagram, a token moving along an arrow). Freeform per-topic animation is
   excluded for reliability.
5. Render a 3-scene piece of about 45 seconds on a subject already in hand (how
   `/explain` picks a rung). Measure wall time, install size, and the number of
   iterations the scene code needed.

If the timebox runs out, the findings note says "inconclusive" with what was measured,
and the user decides whether to extend it.

### 8.3 Fold-in criteria (all required)

- One command from script to playable mp4; narration aligned to scenes; no manual step.
- Render time at most 2 minutes of rendering per minute of video on this Mac.
- Kokoro runs under a uv-managed Python 3.12 or 3.13 in its own venv.
- Scene code renders within two iterations: it is written once and rendered; one
  round of fixes is allowed; if a third is needed, the criterion fails.
- License: Remotion's LICENSE.md grants free use to "an individual", "a for-profit
  organization with up to 3 employees", non-profits, and evaluation; the user's use
  falls inside that, confirmed at spike time.

### 8.4 Outcomes

- Pass: the final wave adds `rungs/video.md`, the Remotion sources (package.json,
  scene components, compositions) under `skills/explain/video/` (versioned),
  `scripts/narrate.sh` and `scripts/render.sh`, and a gitignored
  `~/karpathy/video-workspace/` holding only the installed dependencies and renders;
  each artifact is a composition rendered into `out/`. The spike code is not the
  deliverable, but the final wave may start from it.
- Fail: `video` stays hidden from the router and `--as video` keeps the page fallback
  (§5.2); the reason is recorded in the spike note.

The spike's deliverable is `docs/superpowers/spikes/<date>-video-pipeline.md` with the
measurements and a recommendation, and the user's decision.

## 9. Verification plan

Skills count as done only when proven on this machine.

- `ste`: §4.5.
- `explain`, three live runs on real subjects, each in the wave of its rung:
  1. `/explain skills/ste/SKILL.md --as sheet` — the sheet that inspired the design
     becomes its own test.
  2. `/explain <an existing spec or plan from one of the user's repos> --as page`.
  3. `/explain <a code question>` with no `--as`, in a CodeGraph-indexed repo. The
     expected rung and reason are written into the plan before the run and compared
     with the printed rung line.
  Each run passes when: `verify.sh` exits 0 (self-contained, `data-verify="OK"` at
  every viewport, every citation resolves and every panel or section cites, lint has
  zero errors); Claude's tile review finds no layout
  defect; the artifact opens from `file://`; the provenance block is filled, with the
  `dirty` flag correct for the subject's repo state.
- `video`: §8.3 for the spike; after fold-in, one live `/explain --as video` run.

## 10. Sequencing

Per the wave gate in the global instructions, the `wave-planning` skill produces the
map after this spec is approved. Expected shape, from the dependency facts:

- Wave 1 (fan-out, disjoint files): `ste` — profile with cited rules and table, lint
  with `--html`, tests, live run; in parallel, the video spike with its findings note.
- Wave 2: `explain` core (`SKILL.md`, `snapshot.sh`, `verify.sh`, `cite_check.py`),
  the `sheet` rung (template, guard, rung notes), live run 1.
- Wave 3: the `page` rung (template, `#verify` mode, rung notes), live runs 2 and 3.
- Wave 4, conditional on the spike and the user's decision: the `video` rung.

Each wave is one plan of at most 10 tasks; one feature branch spans all waves.

## 11. Decisions log

| Decision | Choice | Reason |
|---|---|---|
| Trigger | both skills `disable-model-invocation: true` | the only harness mechanism that enforces "explicit only"; description text is advisory |
| `explain` → `ste` | by file path, not the Skill tool | the flag blocks Skill-tool calls and subagent preloading |
| Skill split | `ste` + `explain` | prose rules are reusable in chat, specs and runbooks; artifacts are a different unit |
| Lint severities | errors only for deterministic rules | heuristics fire on correct STE; "zero errors" must stay achievable |
| Rung choice | by content shape | the ladder is not monotonic: video loses to page for anything searched or revisited |
| Grounding | citations with verbatim snippets, machine-checked | a path list on the title block let dangling and stale references pass |
| Verification | `verify.sh` first, tile review second | PNG-only review cannot see horizontal overflow, font size, JS errors or later states |
| Status channel | `<html data-verify>`, never `document.title` | a title written on every load shows "OK" in the user's browser tab |
| Chrome lifecycle | background + poll + kill for every invocation | Chrome 154 does not exit after `--dump-dom`, nor after `--screenshot` with a fresh profile (reproduced) |
| Phone viewport | 500x844 | headless Chrome clamps width to 500 px; 390 would be a crop of a 500 px layout (reproduced) |
| Review images | tiles of at most 1920x1080, cut from a 1 px-padded image | full renders are downscaled before the model sees them; `sips` centre-crops at offset 0 0 and returns the whole image at the bottom edge (reproduced) |
| Word counting | Issue 9 Section 8 tokens | parentheticals, quotes and number+unit are one word each; naive counts error on correct STE |
| Sheet ratio | 16:9 at 1920x1080 | sheets travel as images on screens and phones, not paper |
| Sheet decoration | frame + title block, no zone rulers | ruler letters collided with panel letters; nothing functional lost |
| Renderer | headless Chrome CLI + `sips` | already installed, zero dependencies, verified |
| Diagrams | inline SVG, no Mermaid | self-contained file rule |
| Video stack | Remotion first | keeps the whole ladder on web tech; bundled encoder; computed sync from clip durations |
| Narration | `say` baseline, Kokoro on uv Python 3.12 | zero-install proof first; quality gate before fold-in |
| manim | excluded | heavy install, poor fit for code and architecture content |
