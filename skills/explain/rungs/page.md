# Rung: page
This file holds only what is specific to the page rung. `SKILL.md` has the generic rules.

## 1. When a page

A page has no fixed canvas. It is one responsive HTML file that the reader opens in a browser.

Choose a page when the content has state to explore: a step-through flow, a before and after, or
toggles. Choose it also when the content has more than 6 facets. The steps player is the one
pattern that makes `page` better than `sheet` for flows, PRs and wave plans.

`--as video` builds a video (`rungs/video.md`) and never falls back to a page. For a narrative
on a page, write one step for each beat of the story.

## 2. Plan the sections

- One facet is one `<section>`, one `<h2>` question and one nav entry. Write a short noun
  as the nav label. Write the question in the `<h2>`.
- The first section says why the subject exists. One diagram in it carries the main idea. For a
  directory subject, that diagram is the main flow from start to end, named by its stages. The
  main flow is the journey of one request, a pipeline or a BPMN process. The mechanics follow in
  later sections.
- The diagram of the first section shows the reason that the answer gives, not a list of the parts
  of the subject. Test it: cover the prose. Does the diagram alone support the answer?
- Each section expands one sentence of the answer. Content that expands no sentence goes into a
  `details.walk` of a reference section, into the glossary, or out of the page into `Not covered`.
- For a directory subject whose main flow is a BPMN file, plan the sections from its planes. A
  plane is one diagram of the file: the main process, or one collapsed sub-process. Run
  `python3 <skill-dir>/scripts/bpmn.py planes <file>`. It prints one line for each plane: the id,
  the name or `-`, and the line. Then apply these rules:
  - The first section (the whole, start to end) carries the main plane, with the stages
    highlighted. The main plane is the plane of the process or of the collaboration. A stage is a
    collapsed sub-process that the main plane reaches. Give the ids of the stages to `--highlight`.
  - Then write one section per stage, in process order. The section opens with the plane diagram
    of that stage and a lead paragraph. Then write one paragraph, with its cites, for each of these
    parts of the plane:
    - each sub-process in it, expanded or a nested collapsed one;
    - each gateway, with its branches named;
    - each user task;
    - each boundary timer or error event that changes the path.
  - A nested collapsed sub-process has its own plane inside a stage, like `AOS_BASIC_PD_CHECK`
    inside `QUESTIONNAIRE`. It gets its own diagram too. Put a second `figure.bpmn` in the stage
    section when the plane is small. Give it its own section when it carries several decisions.
    Every plane renders somewhere.
  - Siblings of the same shape, like the three SMEV checks, get one paragraph for the pattern:
    send, wait, timeout, code. Then write one sentence for each sibling with what differs: the
    service, the message, the code variable.
  - For a BPMN main flow, the answer names the stages in process order. Thus each stage section
    expands one sentence of the answer. A plane that the answer does not name still gets a section
    or a figure, because a merge may not drop a plane.
  - The mechanics sections follow the stage sections: handlers, delegates, decision tables and
    deployment.
  - The section count follows the planes. `Not covered` lists each plane or sub-process that the
    page does not explain, by its name verbatim.
- Put exact rules into `details.walk` elements in a reference section: limits, fault codes and
  the rules for each item. Write one sentence above them that tells when to open them.
- Define each term of the subject in the sentence of its first use. If the page uses a term that
  a newcomer to the subject does not know, add a glossary section at the end. It has
  `<section id="terms">`, an `<h2>` question, a nav entry and a `dl.terms`. Each `<dd>` ends with
  its `div.cites`. The glossary is for looking up. The reference section and the glossary count in
  the six to ten.
- If the subject uses the key term of the question for two things, write one note in the first
  section that names the other one. The other one gets no section.
- A paragraph that states a rule or a check also says why the rule or the check exists.
- Six to ten sections is the usual range. There is no cap. If a page has more than about
  twelve sections, merge facets into fewer sections, or ask the user to split the subject.
  Do not make a second output directory. A BPMN subject is the exception: do not merge stages to
  get to twelve, because its section count follows the planes.
- For a file or a directory subject, put at least one `<cite>` in every section.
- Decide which section holds the steps player. One player for each page is the norm.
- Decide which diagram pattern each flow uses (section 4).
- A section would gain from a clip when narration plus motion explains it better than a static
  view. Examples: a flow, a structure that builds up, a before and after, a camera move along code,
  a comparison whose terms change.
- In the page rung only: after you write the plan, if at least one section meets this
  criterion, print `<n> sections would gain from a clip; rerun with --as lesson`. Then build the
  page as before. The lesson rung does not print this line.

## 3. Fill the template

1. Copy `<skill-dir>/templates/page.html` to `<output-dir>/index.html`.
2. Write the page title in `<title>` and in `<h1>`. The title is the question. For a topic, it is
   the question of the user, in full words. For a file or a directory, it asks what the subject
   does and why it exists.
3. Write the answer box in `header > div.answer`. It holds one `<p>` of two to four sentences, at
   most 70 words. The `<p>` starts with `<strong>Short answer.</strong>`. Then the box holds its
   own `div.cites`. The box answers the `<h1>`. It never describes the page.
4. Copy the pattern that you need before you delete the demo content. Then delete the demo
   content and the HTML comments. Keep the CSS and script comments. Keep
   `<meta name="explain-rung" content="page">`: without it, `verify.sh` exits with code 2. Keep the
   `<style>` block and all three script blocks (blocks 1 and 3: the guard; block 2: `explainPlayer`
   (the steps player) and Play all). A plain page keeps the `Play all` button; CSS hides it when
   the page has no `figure.clip`. The guard reports `PLAYALL` when a page with no `figure.clip`
   shows the button. It also reports `PLAYALL` when a page with a `figure.clip` hides the button or
   has no button. Keep the Sources switch, `label.sources` with `input#show-sources`. The template
   hides each `div.cites` until the reader turns the switch on. The guard reports `NOSOURCES` when
   the page has a cite block and the nav has no switch. It reports `NOANSWER` when the header has no
   answer box, or when the box has no text outside its cites.
5. Rebuild `nav#toc`: one `<a href="#id">` for each section, in document order. Keep the Sources
   switch as the last child of `nav#toc`.
6. Set the `lang` attribute of `<html>` to the language of the artifact: `en` or `ru`.

| Primitive | Markup | Use it for |
|---|---|---|
| answer box | `header > div.answer`: one `p` that starts `<strong>Short answer.</strong>`, then its `div.cites` | The short answer, under the `<h1>`. |
| captioned code | `figure.code > figcaption > code` (`name:line`), then `pre > code` | Source lines. |
| walkthrough | `details.walk > summary`, then `p` | A long proof or a second example. |
| diagram | `figure.diagram.flow`, `.sequence` or `.layers`, with a `<figcaption>` | A flow, an exchange, a stack. |
| steps player | `div.player[data-player]`, `button[data-prev]`, `button[data-next]`, `span.caption[data-counter]`, `figure.step[data-step="n"]` | A state that changes in steps. |
| clip (lesson rung only) | `figure.clip > video[controls][preload=none]` + `figcaption > span.part`, one sentence, `a[data-ste=skip]` "transcript" | A narrated clip of this section; markup in `rungs/lesson.md`. |
| table | `.table-wrap > table` | Rows and columns. |
| track list | `ol.track` with one `li.on` | The position in a sequence. |
| Sources switch | `nav#toc > label.sources > input#show-sources` | Show or hide each `div.cites`. It is the last child of the nav. |
| glossary | `section#terms > dl.terms`, with `dt` and `dd` | Look up a term. The nav has an entry for it. |
| provenance | `#provenance` in the `<footer>` | Section 5. |

- Each `figure.step` has its own diagram and one `<figcaption>`.
- Prose for the lint: `summary`, `figcaption` text, `p`, `li`, `dt` and `dd` that has no skip. The
  `<p>` of the answer box is prose too.
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
- BPMN plane: one plane of a `.bpmn` file. A flow that lives in a `.bpmn` file is never drawn by
  hand with the flow pattern. The flow, sequence and layers patterns stay for code paths. Run
  `python3 <skill-dir>/scripts/bpmn.py svg <file> --plane <id> --highlight <ids>`. `<ids>` is a
  list of element ids, with commas and no spaces: the elements that the paragraphs of the section
  cite. In this block, replace the comment and the `svg` line with the output, without change:

  ```html
  <figure class="bpmn">
    <!-- output of: bpmn.py svg <file> --plane <id> --highlight <ids the paragraphs cite> -->
    <svg class="bpmn" …>…</svg>
    <figcaption>One STE sentence: what this plane is.</figcaption>
  </figure>
  ```

  The rules above for the units, the `viewBox` and the marker ids do not apply to a BPMN plane.
  The SVG keeps the size of the file, and a wide plane scrolls inside its figure. To draw one plane
  two times in one page, for example in the steps of a player, give each copy its own `--prefix`.

Steps player: write one `figure.step` for each state. The diagram changes in each step. The caption is
one or two STE sentences. Without `#verify` in the URL, one step shows. With it, all steps stack.

Put the player after the first paragraph of its section. Number `data-step` from 1 to N. The script
sets the counter text. A step diagram is an `ol.track` or an SVG.

A section that is only a diagram or a player holds its cites in a `div.cites`. The block comes
after a `<p>` or after the `figcaption`, outside the `svg`.

## 5. Provenance

Use the recipe in `rungs/sheet.md` section 4 without change: the commands, `data-root`,
`data-kind`, Commit, Dirty, the word `untracked` and the citation form. Only two facts are specific
to a page. The `#provenance` element is in the `<footer>`. `p.not-covered` stays. `Not covered`
lists each facet of the subject that the page does not explain, for any reason: a forced rung, or
content that you cut. Write `none` only when the page explains every facet.

## 6. Write the prose

Read `rungs/sheet.md` section 5 for the lint notes. These facts are specific to a page.

- The lint does not read `nav`. It reads each `summary`, each `dt` and each step caption.
- The template hides the cite blocks until the reader turns on Sources.
- The `figcaption` of a code figure holds `name:line` in `<code>`, not in a `<cite>`, thus neither
  the lint nor `cite_check.py` reads it.
- A sentence of 26 words or more is an error in any place.
- Cite each claim one time. The cites of a paragraph collect in one `div.cites` after the `<p>`
  (the last child of a `<li>` or a `<dd>`); the prose holds no cite. When several sentences of
  one paragraph come from one source line, one `<cite>` in that block covers them. A sentence
  from another line gets its own `<cite>` in the same block. Keep a snippet near 6 words. The
  visible text is `name:line <code>snippet</code>`, where `name` is the basename or a unique
  longer tail, and `data-path` keeps the full path relative to `data-root`:

  ```
  <p>The handler correlates the message to the instance.</p>
  <div class="cites">
    <cite data-path="src/Handler.java" data-line="53" data-snippet="runtimeService.createMessageCorrelation(name)">Handler.java:53 <code>runtimeService.createMessageCorrelation(name)</code></cite>
  </div>
  ```

- A cite of a `.bpmn` file names the line that carries the fact. That is the opening-tag line of
  the element (its id line), its `name=` line, or the sequence flow or its condition line. Do not
  look for the line that reads best: `bpmn.py label` writes a readable name into each of these
  cites (section 7). Never cite a blank line or a comment line.

## 7. Verify and export

Do these steps in the output directory, in this order. If the page cites a `.bpmn` file, do two
BPMN steps before step 1:

- While you write, run `python3 <skill-dir>/scripts/bpmn.py svg <file> --plane <id> --highlight <ids>`
  for each plane. Put each output into its `figure.bpmn` (section 4).
- After you write all the cites, run `python3 <skill-dir>/scripts/bpmn.py label index.html`. It
  writes a `span.bpmn-label` with a readable name into each cite of a `.bpmn` file. If it exits
  with code 1, each line of its output names a cite on a blank line or a comment line. Move that
  cite to a line that carries a fact. Then run `label` again. Also run it again after each change
  to a BPMN cite. Never type a label: the `bpmn` line of step 1 fails on a label that `label`
  did not write.

1. Run `<skill-dir>/scripts/verify.sh index.html`. Each line must show `ok`, except that the
   `bpmn` line shows `none` when the page cites no `.bpmn` file. The six lines are
   `self-contained`, `render 1440x900`, `render 500x844`, `citations`, `prose` and `bpmn`. The
   `bpmn` line fails for a plane without a `figure.bpmn`, or a sub-process without a cite of its
   own lines. Fix each cause that the detail lines name.
2. Run `SNAPSHOT_FRAGMENT=verify <skill-dir>/scripts/snapshot.sh index.html page.png 1440 6000 1`.
   It writes `page.png` and the tiles `review/page-01.png` and up. A page of 6000 px has six tiles.
   Tiles below the footer are blank. Find the tile that shows the footer. If no tile shows it, run
   the same command again with a larger height: 9000, then 12000, and so on. A page has no height
   limit. Never cut content to fit a render.
3. Run `SNAPSHOT_FRAGMENT=verify <skill-dir>/scripts/snapshot.sh index.html narrow.png 500 844 1`.
   It writes `narrow.png` and `review/narrow-01.png`. This render shows the first screen only.
   If the page has a diagram, a table or the player below the first screen, also run
   `SNAPSHOT_FRAGMENT=verify <skill-dir>/scripts/snapshot.sh index.html narrow-tall.png 500 <H> 1`.
   Find `<H>` with the footer rule of step 2. The page is taller at 500 px, thus `<H>` can be
   larger than the height of step 2. Read the tiles `review/narrow-tall-NN.png` that hold
   these parts.
4. Read the tiles with the Read tool. Never read the full PNGs. Look for these faults. Clipped or
   overflowing text. A nav that overflows. A diagram that does not fit at 500 px, or that has
   unreadable text. A player whose steps did not stack. An empty section. Text that gives a false
   picture of the subject. There is no separate 1440x900 render: it is tile 1 of the tall page. The
   tiles show the reading view, where the page hides the cite blocks. Then do three more checks.
   Read `index.html`, not the tiles: each section holds a `div.cites`. `cite_check.py` checks this
   for a file or a directory subject only. Cover the page below the answer box. Does the box alone
   answer the `<h1>`? Cover the prose of the first section. Does its diagram alone support the
   answer?
5. Fix each fault. Run steps 1 to 4 again. Repeat until all are clean.
6. Do the handoff from `SKILL.md` convention 6. Never run `open` inside a subagent.

The output directory then holds `index.html`, `page.png`, `narrow.png`, `narrow-tall.png` (if
step 3 made it) and `review/`.

## 8. Shared palette

The same palette is also in `templates/sheet.html`, `templates/video.html` and `video/src/theme.ts`. Change all four.
