# explain: cited source lines as a code block, and a warm paper palette

Date: 2026-10-06. Status: draft for approval. Coverage: waived (user decision, a layout change
with its existing checks).

## 1. Problem

Two faults of the page and the sheet, both from the first lesson live run (2026-10-06).

The white page is hard on the eyes. The user wants the warm, low-contrast look of Claude's own
artifacts: an off-white ground, a near-black warm ink, a warm accent.

Every artifact rung writes a citation as inline text after the sentence it supports:
`EsbRequestsHandler.java:53 "runtimeService.createMessageCorrelation(inputMessage.getMessageName())"`.
Four of them in a row make a paragraph unreadable, and a quoted source line set in the running
text is code that does not look like code. The user's rule (2026-10-06, the first lesson live
run): if it is code, it is in a code block.

## 2. Design

The cites of a paragraph collect in one block under it. The prose keeps no cite.

### 2.1 Markup

```html
<p>The handler correlates the message to the instance, with the variables that the message makes.
A sync message on a version 2 process gets its reply at once, from the result variables.</p>
<div class="cites">
  <cite data-path="src/.../EsbRequestsHandler.java" data-line="53" data-snippet="runtimeService.createMessageCorrelation(inputMessage.getMessageName())">EsbRequestsHandler.java:53 <code>runtimeService.createMessageCorrelation(inputMessage.getMessageName())</code></cite>
  <cite data-path="src/.../EsbRequestsHandler.java" data-line="56" data-snippet="if (inputMessage.isSync() &amp;&amp; &quot;2&quot;.equals(vars.get(&quot;Version&quot;))) {">EsbRequestsHandler.java:56 <code>if (inputMessage.isSync() &amp;&amp; "2".equals(vars.get("Version"))) {</code></cite>
</div>
```

- `div.cites` follows the element it supports: a `<p>`, a `<li>`, a `figcaption`, or a `<dd>`.
  One block for each such element at most. The block covers each sentence of that element,
  as the trailing `<cite>` did before.
- Each `<cite>` keeps its three data attributes unchanged. Its visible text is `name:line`, a
  space, and the snippet inside `<code>`. The quotes around the snippet go: the `<code>`
  marks it. `name` keeps its rule (the basename, or a longer tail when two cited files share
  it). A URL cite is `host/path <code>snippet</code>` with no line.
- The word `untracked` stays in the cite text, after the `</code>`.
- The lesson `figcaption` of a clip and the `figcaption` of a code figure do not change: they
  hold no cite.

### 2.2 Style, in the three templates (`page.html`, `sheet.html`, `video.html`)

```css
.cites { margin-top: 6px; padding: 6px 10px; background: var(--fill); border-left: 3px solid var(--line); }
.cites cite { display: block; font-family: var(--sans); font-style: normal; color: var(--muted); font-size: 14px; }
.cites cite + cite { margin-top: 4px; }
.cites code { display: block; padding: 0; background: none; color: var(--ink); font-family: var(--mono); font-size: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
```

The sheet keeps its own floor (12 px for `cite`; `code` 12 px). The page rule
`section > * + * { margin-top: 14px }` yields to `p + .cites`, `li + .cites`, `figcaption + .cites`
and `dd + .cites` at 6 px. The transcript's `ul.cites` list becomes the same `div.cites`.

### 2.3 Checks

- `cite_check.py` reads the text of a `<cite>` with its nested elements, so `name:line` is
  still found; a test case pins a cite with a nested `<code>`. The snippet check reads
  `data-snippet`, unchanged.
- `ste_lint.py` skips `cite` and `code`; a `div.cites` holds no other text, so no prose rule
  changes. The lesson E2E and the verify fixtures take the new form.
- The guard: every text in a `.cites` block is 14 px or more on the page, 12 px on the sheet.

### 2.4 Documents

`SKILL.md` convention 2 (the citation form and "each section holds at least one `<cite>`"),
`rungs/sheet.md` §4 (the recipe and the example), `rungs/page.md` §6 (one block under the
paragraph covers it), `rungs/video.md` and `rungs/brainrot.md` where they show the transcript's
cites, `rungs/lesson.md` where it quotes the page rule. The three template demo pages show the
new form.

### 2.5 The palette

One palette, in the four places that `rungs/page.md` §8 names (`page.html`, `sheet.html`,
`video.html`, `video/src/theme.ts`); the film kit (`video/src/kit/palette.ts`, the dark stage)
does not change. The new values:

| Token | Old | New | Use |
|---|---|---|---|
| `bg` (page ground) | `#ffffff` | `#faf9f5` | the body |
| `fill` | `#eef1f4` | `#f0eee6` | code figures, cite blocks, provenance cells, inline code |
| `ink` | `#1b2129` | `#1f1d1a` | text |
| `muted` | `#5b6570` | `#6b6a64` | captions, labels, `name:line` |
| `line` | `#b8c0c9` | `#d4d0c6` | rules, borders |
| `accent` (new) | — | `#c2613f` | links, the nav, `name:line` of a cite, the Play all button border |
| `blue` | `#1d5fc2` | `#1d5fc2` | the chosen step, the current node (unchanged) |
| `red` | `#c42f2a` | `#c42f2a` | unchanged |

`html, body { background: #fff }` becomes `var(--bg)`. Links and `nav#toc a` use the accent;
`cite` text and `name:line` use the accent; the blue stays the colour of a chosen state in a
diagram and a player, so a reader never confuses a link with a state. The contrast of ink on
the ground is 15:1 and of the accent on the ground 4.6:1 (AA for normal text). The PNG export
of a sheet carries the warm ground.

### 2.6 Out of scope

A link from a cite to the file in an editor; folding a long block; the figcaption of a clip.
The lesson of 2026-10-06 (`out/2026-10-06-123735-lesson-aos`) gets the new form by a
mechanical rewrite of its cites after the merge; it is not a test of the feature.

## 3. Tests

- `test_cite_check.py`: a cite whose visible text is `name:line <code>snippet</code>` passes;
  one whose `<code>` holds the name and line but whose text outside it does not still passes
  (the text is read whole); the old form passes too (no artifact breaks).
- `test_page_template.py`, `test_sheet_template.py` (or the existing template tests): the CSS
  rules exist; the demo cites are in a `div.cites`; no 13 px text under `.cites`; the four
  palette blocks hold the same values (a test reads them and compares).
- `test_transcript.py`: the transcript renders `div.cites` with `<code>` snippets.
- `test_verify.py` fixtures and `test_lesson_e2e.py` fixtures: the new form, six and five
  `ok` lines as before.

## 4. Decisions

- D1. One block for each paragraph, not footnotes at the end of the section: the evidence
  stays next to the claim (the user picked this of three layouts).
- D2. The `<cite>` element and its data attributes stay: every check and every reviewer
  prompt reads them; only the visible text and the container change.
- D3. The old inline form stays valid for the checks, so nothing already built breaks.
- D4. The page and the sheet take the warm paper palette; the clips keep their dark stage. A
  dark page was rejected (sheets are glanced at in daylight and export to PNG); a dual palette
  was rejected (two palettes in four files, and the guard sees only one).
- D5. A new accent colour carries links and cites; blue keeps one meaning, the chosen state.
