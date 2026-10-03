# Rung: page
This file holds only what is specific to the page rung. `SKILL.md` has the generic rules.

## 1. When a page

A page has no fixed canvas. It is one responsive HTML file that the reader opens in a browser.

Choose a page when the content has state to explore: a step-through flow, a before and after, or
toggles. Choose it also when the content has more than 6 facets. The steps player is the one
pattern that makes `page` better than `sheet` for flows, PRs and wave plans.

If `--as video` falls back to `page`, the narration becomes the step captions. Write one step for
each narrated beat.

## 2. Plan the sections

- One facet is one `<section>`, one `<h2>` question and one nav entry. Write a short noun
  as the nav label. Write the question in the `<h2>`.
- Six to ten sections is the usual range. There is no cap. If a page has more than about
  twelve sections, merge facets into fewer sections, or ask the user to split the subject.
  Do not make a second output directory.
- For a file or a directory subject, put at least one `<cite>` in every section.
- Decide which section holds the steps player. One player for each page is the norm.
- Decide which diagram pattern each flow uses (section 4).

## 3. Fill the template

1. Copy `~/.claude/skills/explain/templates/page.html` to `<output-dir>/index.html`.
2. Write the page title in `<title>` and in `<h1>`.
3. Copy the pattern that you need before you delete the demo content. Then delete the demo
   content and the HTML comments. Keep the CSS and script comments. Keep
   `<meta name="explain-rung" content="page">`: without it, `verify.sh` exits with code 2. Keep the
   `<style>` block and all three script blocks.
4. Rebuild `nav#toc`: one `<a href="#id">` for each section, in document order.

| Primitive | Markup | Use it for |
|---|---|---|
| captioned code | `figure.code > figcaption > code` (`name:line`), then `pre > code` | Source lines. |
| walkthrough | `details.walk > summary`, then `p` | A long proof or a second example. |
| diagram | `figure.diagram.flow`, `.sequence` or `.layers`, with a `<figcaption>` | A flow, an exchange, a stack. |
| steps player | `div.player[data-player]`, `button[data-prev]`, `button[data-next]`, `span.caption[data-counter]`, `figure.step[data-step="n"]` | A state that changes in steps. |
| table | `.table-wrap > table` | Rows and columns. |
| track list | `ol.track` with one `li.on` | The position in a sequence. |
| provenance | `#provenance` in the `<footer>` | Section 5. |

- Each `figure.step` has its own diagram and one `<figcaption>`.
- Prose for the lint: `summary`, `figcaption` text, `p`, `li` and `dd` that has no skip.
- Put `data-ste="skip"` on the non-prose parts: each SVG, `ol.track` and the provenance `<dl>`.
- The font floor is 14 px. Never add a rule that sets a smaller size. The guard reports
  `SMALLTEXT:<px>` if some text is smaller.

## 4. Diagram patterns

Each diagram is an inline SVG. Keep `viewBox`, `role="img"`, the `<title>` and `data-ste="skip"`.
Write SVG text at 18 units on a `viewBox` of 600 units. At 500 px wide, this is about 14 px. In the
steps player, the SVG is narrower (about 441 px at 500 px wide), thus use 20 units there or an
`ol.track`. Keep the `viewBox` width at 600 and grow only the height.

Keep each marker `id` unique in the page. A player with one SVG for each step also needs a unique
`<title id>` and `aria-labelledby` id in each SVG. The HTML comments in the template give the
geometry.

- Flow: boxes and arrows from left to right. Use it for a pipeline or a call chain. To add a box,
  make the boxes narrower so that all fit in 600 units. Or start a second row 80 units lower and add
  80 to the `viewBox` height. Use `class="label"` on mono text. A label of 18 units in mono text
  needs about 11 units for each character, thus a box of 118 units holds 9 characters. Make the
  box wider or use two lines.
- Sequence: lifelines and numbered messages. Use it for an exchange between parts. Draw each
  lifeline as a `line` with `class="life"`. Put the lifelines 200 units apart. For four
  participants, put them 150 units apart and make each box 118 units wide. Keep the
  `viewBox` width at 600. To add a message, draw one arrow 50 units below the last. Put its
  number above it. Add 50 to the `viewBox` height.
- Layers: stacked bands from top to bottom. Use it for a stack or a hierarchy. To add a band, put
  it 70 units below the last. Add 70 to the `viewBox` height. Use `class="alt"` on every second band.
  Write the band title as a `text` with `class="name"`.

Steps player: write one `figure.step` for each state. The diagram changes in each step. The caption is
one or two STE sentences. Without `#verify` in the URL, one step shows. With it, all steps stack.

Put the player after the first paragraph of its section. Number `data-step` from 1 to N. The script
sets the counter text. A step diagram is an `ol.track` or an SVG.

A section that is only a diagram or a player holds its `<cite>` in a `<p>` or in the `figcaption`,
outside the `svg`.

## 5. Provenance

Use the recipe in `rungs/sheet.md` section 4 without change: the commands, `data-root`,
`data-kind`, Commit, Dirty, the word `untracked` and the citation form. Only two facts are specific
to a page. The `#provenance` element is in the `<footer>`. `p.not-covered` stays. `Not covered`
lists each facet of the subject that the page does not explain, for any reason: a forced rung, or
content that you cut. Write `none` only when the page explains every facet.

## 6. Write the prose

Read `rungs/sheet.md` section 5 for the lint notes. These facts are specific to a page.

- The lint does not read `nav`. It reads each `summary` and each step caption.
- The `figcaption` of a code figure holds `name:line` in `<code>`, not in a `<cite>`, thus neither
  the lint nor `cite_check.py` reads it.
- A sentence of 26 words or more is an error in any place.
- Cite each claim one time. When several sentences of one paragraph come from one source line,
  one `<cite>` at the end of the paragraph covers them. A sentence from another line gets its own
  `<cite>`. Keep a snippet near 6 words. The visible text is `name:line "snippet"`, where `name` is
  the basename or a unique longer tail, and `data-path` keeps the full path relative to `data-root`.

## 7. Verify and export

Do these steps in the output directory, in this order.
1. Run `~/.claude/skills/explain/scripts/verify.sh index.html`. All five lines must show `ok`:
   `self-contained`, `render 1440x900`, `render 500x844`, `citations` and `prose`. Fix each cause
   that the detail lines name.
2. Run `SNAPSHOT_FRAGMENT=verify ~/.claude/skills/explain/scripts/snapshot.sh index.html page.png 1440 6000 1`.
   It writes `page.png` and the tiles `review/page-01.png` and up. A page of 6000 px has six tiles.
   Tiles below the footer are blank. Find the tile that shows the footer. If no tile shows it, run
   the same command again with a larger height: 9000, then 12000, and so on. A page has no height
   limit. Never cut content to fit a render.
3. Run `SNAPSHOT_FRAGMENT=verify ~/.claude/skills/explain/scripts/snapshot.sh index.html narrow.png 500 844 1`.
   It writes `narrow.png` and `review/narrow-01.png`. This render shows the first screen only.
   If the page has a diagram, a table or the player below the first screen, also run
   `SNAPSHOT_FRAGMENT=verify ~/.claude/skills/explain/scripts/snapshot.sh index.html narrow-tall.png 500 <H> 1`.
   Find `<H>` with the footer rule of step 2. The page is taller at 500 px, thus `<H>` can be
   larger than the height of step 2. Read the tiles `review/narrow-tall-NN.png` that hold
   these parts.
4. Read the tiles with the Read tool. Never read the full PNGs. Look for these faults. Clipped or
   overflowing text. A nav that overflows. A diagram that does not fit at 500 px, or that has
   unreadable text. A player whose steps did not stack. A section without its citation. An empty
   section. Text that gives a false picture of the subject. There is no separate 1440x900 render: it
   is tile 1 of the tall page.
5. Fix each fault. Run steps 1 to 4 again. Repeat until all are clean.
6. Do the handoff from `SKILL.md` convention 6. Never run `open` inside a subagent.

The output directory then holds `index.html`, `page.png`, `narrow.png`, `narrow-tall.png` (if
step 3 made it) and `review/`.

## 8. Shared palette

The same palette is also in `templates/sheet.html`, `templates/video.html` and `video/src/theme.ts`. Change all four.
