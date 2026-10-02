# Explain skills (`ste` + `explain`) — design

Date: 2026-10-02
Status: approved in conversation; written spec pending user review

## 1. Purpose

Karpathy's note (2026-10) argues that as models do more of the legwork, human work
moves up to oversight and understanding, and that models should help by producing
better-shaped outputs: controlled-language prose (ASD-STE100), diagrams, interactive
web pages, and narrated explainer videos — large, custom, discardable artifacts.

This design turns that note into two personal Claude Code skills:

- `ste` — a fixed, checkable prose profile derived from ASD-STE100 ("STE-80").
- `explain` — an explicit router that builds one discardable artifact (sheet, page,
  or video) from a topic, a file, or the current discussion, grounded in real sources
  and verified visually before handoff.

Intended uses, in priority order:

1. Understanding code and architecture — a repo, a PR, a flow Claude just wrote.
2. Reviewing Claude's own artifacts — specs, plans, wave maps, review findings.
3. Learning any topic, code or not.

Success means: one command produces an artifact that a reader can trust (every claim
traceable to a source), that opens as a single file anywhere, and that was checked by
Claude against its own rendered output before it was handed over.

## 2. Scope

In scope:

- Skill `ste`: rule set, lint script, usage protocol, tests.
- Skill `explain`: router, conventions, `sheet` and `page` rungs, templates,
  snapshot script, live verification runs.
- A throwaway spike that decides whether a `video` rung is feasible on this Mac.
- The `video` rung itself, only if the spike passes (wave 2).

Out of scope:

- Automatic triggering of either skill. Both fire only on explicit request
  (user invocation, or `explain` invoking `ste`).
- Committing artifacts into any repo; multi-file sites; external assets or CDNs.
- A full ASD-STE100 dictionary check (see §4.2).
- manim. It is reconsidered only if the user asks for the literal 3b1b math look.

## 3. Repository layout and installation

`~/karpathy` is a git repository and owns everything. Skills are symlinked into
`~/.claude/skills/`, the same pattern already used for `qmemd-memory`.

```
~/karpathy/
  .gitignore                           out/, spike-video/, video-workspace/, node_modules/
  docs/superpowers/specs/              this spec
  docs/superpowers/spikes/             spike findings notes (kept)
  skills/ste/
    SKILL.md
    scripts/ste_lint.py
    tests/test_ste_lint.py
  skills/explain/
    SKILL.md
    rungs/sheet.md
    rungs/page.md
    rungs/video.md                     wave 2, only if the spike passes
    templates/sheet.html
    templates/page.html
    scripts/snapshot.sh
  spike-video/                         throwaway, gitignored
  video-workspace/                     wave 2, gitignored (deps installed once)
  out/                                 artifacts, gitignored

~/.claude/skills/ste     -> ~/karpathy/skills/ste
~/.claude/skills/explain -> ~/karpathy/skills/explain
```

Skill frontmatter follows the existing personal skills (`name`, `description` in the
"Use when …" form; see `~/.claude/skills/verify-before-assert/SKILL.md`).

## 4. Skill `ste`

### 4.1 Trigger

Explicit only. The description reads: use when the user asks for STE, Simplified
Technical English, "80% STE", or "say it plainly", or when the `explain` skill
requests prose. Do not trigger otherwise.

### 4.2 The STE-80 profile

The value of the skill over a bare prompt is that the definition of "80% STE" is fixed
and does not drift between sessions. The profile is:

Kept (structural rules and verb rules, from the specification):

- Procedural sentence: at most 20 words. Descriptive sentence: at most 25 words.
- Paragraph: at most 6 sentences, one topic, topic sentence first.
- One instruction per sentence. Simultaneous actions are the only exception.
- Procedures use the imperative. Safety text uses `WARNING:` or `CAUTION:` followed by
  a simple command, then the risk in a second sentence.
- Verb forms allowed: infinitive, imperative, simple present, simple past, simple
  future, past participle as an adjective. Not allowed: `-ing` verb forms (allowed only
  inside a technical name, for example "landing gear"), perfect tenses, passive voice in
  procedures. Passive is allowed in descriptive text only when the agent is unknown or
  unimportant.
- Active voice with the agent named.
- One word, one meaning, one part of speech. The same word for the same thing every
  time. No elegant variation.
- Keep articles (`the`, `a`, `an`). No contractions.
- Noun clusters of at most 3 words; break longer ones with prepositions.
- Vertical lists for complex text.
- A substitution table of about 25 common offenders, each mapped to its approved
  alternative, for example `ensure -> make sure (that)`, `utilize -> use`,
  `prior to -> before`, `in order to -> to`, `commence -> start`,
  `approximately -> about`, `replenish -> fill`, `terminate -> stop`,
  `sufficient -> enough`, `in the event of -> if`, `attempt -> try`, `perform -> do`.
  Requirement: at implementation time every entry is checked against a public
  ASD-STE100 reference and recorded with its source in `SKILL.md`; an entry that cannot
  be confirmed is dropped, not guessed.

Relaxed (the 20%):

- The approved dictionary of about 900 general words is not enforced as a hard limit.
  The specification itself allows company-defined technical names and technical verbs;
  the profile uses that door generously. Code identifiers, commands, file paths, product
  names, and protocol terms stay verbatim in backticks and are defined on first use.
- Spelling-convention and punctuation minutiae of the specification are not enforced.

Markdown headings and lists are allowed and encouraged (vertical lists are an STE rule).

### 4.3 `ste_lint.py`

Purpose: make STE-80 checkable so Claude corrects measured findings instead of
guessing. Python 3, standard library only.

Command contract:

```
python3 ste_lint.py [--procedural] [--max-words N] [--strict] [FILE]
```

- Reads `FILE`, or stdin when `FILE` is absent. Input is Markdown or plain text.
- `--procedural` sets the sentence cap to 20; default cap is 25; `--max-words`
  overrides either.
- Output: one finding per line, `LINE:COL  RULE  message`, sorted by line.
- Exit codes: `0` no errors; `1` at least one error (or any warning with `--strict`);
  `2` usage error (unreadable file, bad flag).

Skipped text: YAML frontmatter, fenced code blocks, inline code spans, URLs, headings
(`#` lines), table rows (`|` lines). List markers and blockquote markers are stripped;
the remaining item text is checked.

Rules and severity:

| Rule | Severity | Detection |
|---|---|---|
| `LENGTH` | error | sentence word count over the cap; whitespace tokens, hyphenated words and backticked spans count as one word each |
| `PARAGRAPH` | error | more than 6 sentences in a blank-line-separated block |
| `CONTRACTION` | error | `n't`, `'ll`, `'re`, `'ve`, `'d`, `'m`, `'s` after a pronoun |
| `WORD` | error | an entry of the substitution table, whole-word, case-insensitive; message names the approved alternative |
| `PROGRESSIVE` | error | a form of `be` followed by an `-ing` word |
| `PERFECT` | error | `has`, `have`, `had` followed by a participle |
| `PASSIVE` | warning | a form of `be` followed by an `-ed` word or a listed irregular participle |
| `GERUND` | warning | a sentence that starts with an `-ing` word |

`PASSIVE` and `GERUND` are warnings because the heuristics cannot separate a state
adjective ("the valve is closed", approved) from a passive action, or a noun from a verb.
Claude reviews warnings and keeps approved constructs. The script does not attempt
noun-cluster detection; that needs part-of-speech tagging and would be noisy.

Sentence splitting: on `.`, `!`, `?` followed by whitespace or end of text, with a
small abbreviation allowlist (`e.g.`, `i.e.`, `etc.`, `vs.`, `Mr.`, `Dr.`, `No.`).
The limitation is documented in the script header.

### 4.4 Usage protocol

1. Claude drafts under the profile.
2. For any text of more than five sentences, or any text that will land in an
   artifact or a document, Claude writes the draft to a temporary file, runs the lint,
   fixes errors, reviews warnings, and then answers.
3. Short chat answers skip the lint.
4. Technical names are kept verbatim in backticks and are not rewritten.

### 4.5 Verification

- `tests/test_ste_lint.py` (standard `unittest`, run with `python3 -m unittest`):
  for every rule, one input that must produce that specific rule code — asserted by
  rule code, not by "some finding exists"; clean inputs taken from the specification's
  own examples ("Close the valve.", "The pump supplies fuel to the engine when the
  switch is on.") that must produce no findings; a backticked banned word that must not
  fire `WORD`; exit-code checks for 0, 1, and 2.
- Each assertion is validated against the broken state (the rule disabled or the input
  altered) before it counts, per the house rule on coverage assertions.
- One live run: a subagent with the skill loaded explains a real subject in STE-80; the
  output is linted and must have zero errors. A baseline run without the skill is
  linted for comparison and the two counts are recorded in the spike/notes file.

## 5. Skill `explain`

### 5.1 Trigger and invocation

Explicit only. The description reads: use when the user invokes `/explain` or asks for
an explainer artifact (sheet, page, video) of a topic, a file, or the current
discussion. Do not trigger on ordinary questions.

```
/explain <subject> [--as ste|sheet|page|video]
```

Subject resolution, in order:

1. A path that exists: a file is read in full; a directory is mapped (tree plus key
   files; CodeGraph when a `.codegraph/` index exists, per the global instructions).
2. `this`: the last substantial item in the conversation (an explanation, an artifact,
   a review, a plan).
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

Before building, Claude states the choice and the reason in one line:
`Rung: sheet — 5 facets, reference use.`

The `ste` rung produces chat text only; it creates no output directory.

If `video` is chosen or forced but `rungs/video.md` does not exist (spike failed or
wave 2 not done), the skill builds a `page` with the steps player and says so.

### 5.3 Conventions for every rung

1. Prose through `ste`. The `ste` skill is invoked; any prose that lands in an
   artifact passes `ste_lint.py` with zero errors.
2. Grounded, not hallucinated. When the subject is code or a repo file, the real
   source is read first. Every claim in the artifact maps to a `path:line` or a spec
   section. The artifact's title block or footer carries its sources: paths, and the
   commit hash and date when inside a git repo.
3. One self-contained file. Inline CSS and JS, system fonts, no CDN, no build step.
   Opens from `file://` offline. Survives being sent as one file over Telegram or email.
4. Verified before handoff. The artifact is rendered with `scripts/snapshot.sh`;
   Claude reads the PNG and checks for overflow, clipping, empty regions and unreadable
   text; fixes; re-renders. Then the artifact is opened with `open`.
5. Discardable output. `~/karpathy/out/YYYY-MM-DD-<slug>/` where `slug` is the
   kebab-cased subject, at most 40 characters. Contents: `index.html`; `sheet.png` for
   sheets; `video.mp4` and `narration.md` for videos. Outside every repo, never
   committed, safe to delete wholesale.
6. Language: artifacts are in English unless the user asks otherwise.

### 5.4 `scripts/snapshot.sh`

Renders an HTML file to PNG with headless Chrome. No other dependency; Chrome is
installed on this machine and `--headless=new --screenshot` was verified to work.

```
snapshot.sh <input.html> <output.png> [width=1920] [height=1080] [scale=2]
```

- Uses `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` with
  `--headless=new --disable-gpu --hide-scrollbars --window-size=WxH
  --force-device-scale-factor=S --screenshot=<output> file://<absolute input>`.
- Exits non-zero with a one-line message when Chrome is missing or the PNG was not
  produced.
- Tall renders (for example `1440x6000`) are the way to capture a long page; Chrome's
  `--screenshot` captures the window only.

### 5.5 Size discipline

`SKILL.md` stays near 100 lines: trigger, invocation, rung table, conventions, and a
pointer to one `rungs/*.md` file per rung. Rung files hold the specifics and are read
only when that rung is chosen.

## 6. Rung `sheet`

The attached STE sheet is the reference. The template encodes the grammar of its
layout, not its content.

- Canvas: fixed 1920x1080 CSS pixels, exported at scale 2 (3840x2160 PNG).
- Frame: engineering-drawing border with zone rulers, numbers 1–8 across and letters
  A–D down. Decorative, but it is the family's identity and gives a way to point at
  "panel B, zone 4".
- Grid: 12 columns by 2 rows. Four to six lettered panels (A–F). Each panel has a
  header bar: letter tag, title, right-aligned caption.
- Title block: fixed bottom-right. Title; key: value pairs; `Source` with paths and
  commit/date (§5.3 item 2); `Sheet N of M`; date.
- Six body primitives, each a documented HTML pattern in `templates/sheet.html`:
  1. tree — structure or map (panel A is always this: "what is it made of")
  2. annotated example — a monospace sample with keyed annotations (panel B is always
     this: "what does a correct one look like"). Implementation: numbered markers on
     spans plus a keyed legend below. Underline brackets like the reference image are a
     nice-to-have, used only if they render reliably in the snapshot.
  3. status table — rows with a ✓/✗ column
  4. limits bars — a number drawn as a horizontal bar on a tick scale with a "max N"
     label; a limit is never left as prose when it can be a bar
  5. timeline — horizontal nodes with captions
  6. rule list — short STE sentences, bulleted
- Palette and type: ink, muted, and line grays; one emphasis blue (approved,
  highlights); one alarm red (not approved, errors); light-gray box fill; system sans
  and system mono. No web fonts.
- Authoring rules (`rungs/sheet.md`): one question per panel; 150–250 words per panel;
  limits as bars; all prose STE-80; no empty panel; panel A is the map, panel B is the
  example.
- Overflow guard: an inline script of about 10 lines marks any panel whose content
  exceeds its box with a red `OVERFLOW` ribbon, so the defect is visible in the PNG.
  Zero cost when everything fits.
- Export: `snapshot.sh index.html sheet.png 1920 1080 2`.

## 7. Rung `page`

Same visual family, no fixed canvas; responsive single file read in a browser.

- Structure: sticky section navigation; STE-80 prose; code blocks captioned with
  `path:line`; `<details>` for expandable walkthroughs; provenance footer.
- Steps player: previous/next through a sequence of states with a diagram that changes
  per step. This is the one interactive pattern that justifies choosing `page` over
  `sheet` for flows, PRs, and wave plans.
- Diagrams: hand-written inline SVG from three documented patterns in
  `templates/page.html`: box-and-arrow flow, sequence, layered architecture. Mermaid is
  excluded because keeping the file self-contained would mean inlining about 2.5 MB.
- Budget: vanilla JS under about 200 lines; no frameworks.
- Verification viewports: `1440x900` (above the fold), `1440x6000` (full flow),
  `390x844` (phone). Usable on all three means: no horizontal scrolling, navigation and
  steps player reachable, body text not below 14 px.
- Shared palette is duplicated in both templates because self-contained files cannot
  import; `rungs/sheet.md` and `rungs/page.md` both say "change both".

## 8. Rung `video` — spike first

### 8.1 Question

Can a scripted pipeline on this Mac turn a script (narration text plus a scene list)
into a narrated mp4 reliably enough to be a skill?

### 8.2 Probe (throwaway, in `spike-video/`)

1. Scaffold Remotion with `npx create-video`. Confirm it renders without a system
   ffmpeg (none is installed; Remotion is believed to bundle its own — verify).
2. Narration baseline: macOS `say` to WAV (`--file-format=WAVE`, verified), durations
   read with `afinfo` (verified). Each scene's `durationInFrames` is computed from its
   clip length plus padding, so sync is computed, not eyeballed.
3. Narration quality candidate: Kokoro-82M run locally through `uv`. The compact `say`
   voices are too robotic to ship; no premium voice is installed, and no ElevenLabs key
   is set (checked).
4. Scenes: a constrained set of components — title, bullets-appear,
   diagram-with-highlight-walk, code-with-line-highlights, before/after. Each scene must
   carry one motion that means something (a highlight walking a diagram, a token moving
   along an arrow). Freeform per-topic animation is excluded for reliability.
5. Render a 3-scene piece of about 45 seconds on a subject already in hand (how
   `/explain` picks a rung). Measure wall time, install size, and the number of
   iterations the scene code needed.
6. Fallback, tried only if steps 1–5 fail: HTML page, headless Chrome capture, ffmpeg
   from Homebrew.

### 8.3 Fold-in criteria (all required)

- One command from script to playable mp4; narration aligned to scenes; no manual step.
- Render time at most 2 minutes of rendering per minute of video on this Mac.
- Kokoro runs on the installed Python 3.14 on Apple Silicon. If not, the alternative
  (Piper, or a manually installed premium `say` voice) is documented and judged.
- Scene code renders within two iterations.
- Remotion's license permits this use (free for individuals and very small companies;
  confirm the current terms).

### 8.4 Outcomes

- Pass: wave 2 adds `rungs/video.md`, the scene components, `scripts/narrate.sh` and
  `scripts/render.sh`, and a persistent `~/karpathy/video-workspace/` where
  dependencies are installed once and each artifact is a composition rendered into
  `out/`.
- Fail: `video` falls back to `page` permanently (§5.2), and the reason is recorded in
  the spike note.

The spike's deliverable is `docs/superpowers/spikes/<date>-video-pipeline.md` with the
measurements and a recommendation, and the user's decision. Spike code is not kept.

## 9. Verification plan

Skills count as done only when proven on this machine.

- `ste`: §4.5.
- `explain`, three live runs on real subjects:
  1. `/explain skills/ste/SKILL.md --as sheet` — the sheet that inspired the design
     becomes its own test.
  2. `/explain <an existing spec or plan from one of the user's repos> --as page`.
  3. `/explain <a code question>` with no `--as`, in a CodeGraph-indexed repo; the
     stated rung and reason are checked, and three claims are spot-checked against
     `path:line`.
  Each run passes when: the artifact opens from `file://`; the snapshot shows no
  `OVERFLOW` ribbon and no clipping; the prose lints with zero errors; the provenance
  block is filled.
- `video`: §8.3 for the spike; after fold-in, one live `/explain --as video` run.

## 10. Sequencing

Per the wave gate in the global instructions, two waves on one feature branch:

- Wave 1: `ste` (rules, lint, tests), `explain` core (SKILL.md, snapshot script),
  `sheet` rung (template, rung notes), `page` rung (template, rung notes), the three
  live runs, and the video spike with its findings note. Expected to fit one plan of at
  most 10 tasks.
- Wave 2: the `video` rung, planned only on the spike's evidence and the user's
  decision.

## 11. Decisions log

| Decision | Choice | Reason |
|---|---|---|
| Trigger | explicit only | the user's workflow is built on explicit gates; automatic artifacts would be noise and cost |
| Skill split | `ste` + `explain` | prose rules are reusable in chat, specs and runbooks; artifacts are a different unit |
| Rung choice | by content shape | the ladder is not monotonic: video loses to page for anything searched or revisited |
| Sheet ratio | 16:9 at 1920x1080 | sheets travel as images on screens and phones, not paper |
| Renderer | headless Chrome CLI | already installed, zero dependencies, verified |
| Diagrams | inline SVG, no Mermaid | self-contained file rule |
| Video stack | Remotion first | keeps the whole ladder on web tech, Claude's strongest medium; computed sync from clip durations |
| Narration | `say` baseline, Kokoro for quality | zero-install proof first; quality gate before fold-in |
| manim | excluded | heavy install, poor fit for code and architecture content |
