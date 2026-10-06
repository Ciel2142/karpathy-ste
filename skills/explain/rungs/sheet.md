# Rung: sheet
This file holds only what is specific to the sheet rung. `SKILL.md` has the generic rules.

## 1. When a sheet

A sheet is one fixed page of at most 6 facets. It holds reference material that the reader looks
at many times. The canvas has a fixed size of 1920x1080 CSS pixels. The sheet exports to a PNG for sharing.

The facet cap is 6. A forced `--as sheet` can give more than 6 facets. Keep the 6 most important
facets. Write the dropped facets in `<p class="not-covered">`, as `Not covered:` and a list of the
facets. Write `Not covered: none` if you dropped nothing.

## 2. Plan the panels

- Each panel answers one question. Write that question as the panel title (`<h2>`).
- Use four to six panels, lettered A to D, A to E or A to F.
- Panel A is always the map: the tree of the parts of the subject.
- Panel B is the annotated example when the subject has instances to show (code, sentences,
  messages). If it has none, panel B is the key flow or the decisive table.
- Write at most 250 words in a panel. There is no minimum.
- Do not leave a panel empty. Delete a panel that has no question.
- Write a limit as a bar. Never write it as prose when a bar can show it.
- For a file or a directory subject, put at least one `<cite>` in every panel.

## 3. Fill the template

1. Copy `<skill-dir>/templates/sheet.html` to `<output-dir>/index.html`.
2. Write the sheet title in `<title>` and in `.tb-title`.
3. Delete the demo content of each panel body. Delete the HTML comments; keep the CSS and
   script comments. Keep `<meta name="explain-rung" content="sheet">`: without it, `verify.sh`
   exits with code 2. Keep the classes, the `<style>` block and both guard scripts. Keep the
   ids and the `.tag` letters, but re-letter them if you delete a panel (step 4).
4. Set the panel count. Panel F is the `.over-title` panel: it sits in the last 3 columns of
   row 2, above the title block. Delete panels in this order: F first, then C.
   - 6 panels: keep all panels.
   - 5 panels: delete panel F. Add the class `tall` to `.title-block`.
   - 4 panels: delete panels F and C. Add `tall` to `.title-block`. Change A and B to
     `span-6`. Change the id and the `.tag` of old D to C, and of old E to D.
   Plan the content so that the panels that remain are the panels that hold the questions.
   Put the least important questions in F and C. Move content before you delete a panel.
5. The span classes are `span-3`, `span-4`, `span-5`, `span-6`, `span-7`, `span-8`, `span-9`
   and `span-12`. There is no `span-10` or `span-11`. Each row of panels adds up to 12 columns.
   In row 2 the title block takes the last 3 columns. Thus the panels D and E (C and D after
   re-lettering to 4 panels) add up to 9 columns, and panel F sits above the title block.
6. Set the `lang` attribute of `<html>` to the language of the artifact: `en` or `ru`.

Put one primitive in each `.panel-body`.

| Primitive | Class names | Use it for |
|---|---|---|
| tree | `ul.tree`, `.root`, `.what` | The map. Always panel A. |
| annotated example | `.sample`, `.markers`, `pre`, `.hl`, `dl.legend` | Code, sentences or messages with keys. |
| status table | `table.status`, `td.yes`, `td.no` | Rows with a check or a cross. |
| limits bars | `.limit`, `.limit-head`, `.bar`, `.ticks` | A limit drawn as a bar on a tick scale. |
| timeline | `ol.timeline`, `.when`, `.what` | An ordered flow of up to 6 nodes. |
| rule list | `ul.rules` | Short rules, one for each `<li>`. |

- Put `data-ste="skip"` on the non-prose parts only: `ul.tree`, `.sample`, `table.status`,
  `.limit-head`, `ol.ticks` and `ol.timeline`. The legend and the rule list are prose.
- Annotated example: write one `<li>` in `.markers` for each line of the `<pre>`. Write an
  empty `<li>` for a line without a key. Escape `<` and `>` in the sample.
- Every font size is 12 px or more. Do not add a rule that sets a smaller size.
- Bar: `--value` on `.bar` is the limit itself, for example 6. `--max` is the end of the tick
  scale, for example 8. The label in `.limit-head` is `max 6 panels`: it shows the limit, not
  the scale end. Write the tick labels in `ol.ticks` from 0 to `--max` at equal steps.
  `verify.sh` cannot find a wrong bar. Check each bar by eye in the tiles.
- The title block has `.tb-title`, a `<dl>` of key and value pairs, `#provenance` (section 4)
  and `p.not-covered`. Put `data-ste="skip"` on both `<dl>` blocks. Keep each value short. A
  value wraps and never truncates. The guard reports `OVERFLOW:title` if the block overflows.
  Then make `--tb-height` larger in steps of 20 px. Panel F becomes shorter by the same
  height through `.over-title`.
- Cite placement: the cites of a paragraph go in one `div.cites` after it (inside a `<li>`, as
  its last child). In a non-prose primitive, put the block after the `p.note` or `p.box` below
  the primitive, with a snippet of at most 4 words. A sheet is dense: the block shows each cite
  on one line.

## 4. Provenance recipe

Run the first three commands in the directory of the subject; for a topic or a conversation,
in the current directory. Run the last command from the repo root.

```
git rev-parse --show-toplevel
git rev-parse --short HEAD
git status --porcelain
git ls-files --error-unmatch <path>
```

- `--show-toplevel` gives the repo root. Write it in `data-root` of `#provenance`.
- If `git rev-parse --show-toplevel` fails, `data-root` is the subject's directory (file,
  directory) or the current directory (topic, conversation). Commit is `none` and Dirty is `no`.
  A topic without files has the same values, also inside a repository.
- `--short HEAD` gives the Commit value (7 or more characters).
- If `git status --porcelain` prints anything, write the literal `dirty` as the Dirty value.
  If it prints nothing, write `no`.
- Set `data-kind` to `file`, `directory`, `topic` or `conversation`. Write the date as `YYYY-MM-DD`.
- Subject cell: `<path> (file)`, `<path> (directory)`, `<topic> (topic)` or
  `conversation (unverified)`. For a conversation, re-read and cite each file that it names.
- Source cell: for a file or a directory, write the repo root. For a topic that you answered from
  files of a git repo, also write the repo root. For any other topic, write `model knowledge` or
  the list of URLs that you read. Never write `model knowledge` for a file.

A citation has this form. `data-path` is the full path, relative to `data-root`. `data-line` is a
1-based line number. The snippet has at most 12 words, copied verbatim from that one line. Escape
`"`, `&` and `<` inside the attribute (`&quot;`, `&amp;`, `&lt;`).

The visible text is `name:line` and the snippet in `<code>`, with no quotes. `name` is the
basename of `data-path`, or a longer tail if two cited files have that basename. The cites of
one paragraph collect in one `div.cites` after it; the prose keeps no cite.

```
<p>The program starts in one function.</p>
<div class="cites">
  <cite data-path="src/app.py" data-line="12" data-snippet="def main(argv):">app.py:12 <code>def main(argv):</code></cite>
</div>
```

Run `git ls-files --error-unmatch <path>` from the repo root. `<path>` is the `data-path` value
of the `<cite>`. If the command exits with a non-zero code, git does not track the file. Write
the word `untracked` inside the `<cite>` text, after the `</code>`, in each `<cite>` for that file.

## 5. Write the prose

Write all prose in STE-80. These notes come from the lint of the `ste` skill.

- Close every element: `</li>`, `</p>` and `</dd>`. Never put `data-ste="skip"` on an element
  that you did not close. The skip then covers the text after it.
- Keep icons and `<img>` out of sentences. Put them in a separate element.
- Write a quote as `“…”` or as `<q>…</q>`. The lint counts a quote as one word.
- Start a safety text with `WARNING:` and put it in its own `<p>`.
- The lint does not read headings, table cells, `<cite>`, the `<title>` element or any
  `data-ste="skip"` subtree.
- The lint reads `.tb-title`, `.panel-head .caption` and `p.not-covered` as prose. An
  unapproved word there fails the prose check. A long `Not covered` list can be a sentence
  of 26 words or more, which is an error. Inline `<code>` outside a skip counts as one word.
- A step of 21 to 25 words in an `<ol>` is a warning. A sentence of 26 words or more, in
  any place, is an error.

## 6. Verify and export

Do these steps in the output directory, in this order.
1. Run `<skill-dir>/scripts/verify.sh index.html`. All four lines must show
   `ok`: `self-contained`, `render 1920x1080`, `citations` and `prose`. Fix each cause that
   the detail lines name.
2. Run `<skill-dir>/scripts/snapshot.sh index.html sheet.png 1920 1080 2`. It writes
   `sheet.png` (3840x2160) and the tiles `review/sheet-01.png` to `review/sheet-04.png`.
   The output directory then holds `index.html`, `sheet.png` and `review/sheet-01..04.png`.
3. Read the four tiles with the Read tool. Never read `sheet.png`.
4. Look for these faults. Clipped text. An empty panel. A red ribbon (`OVERFLOW:<letter>`).
   A bar without its `max N` label. A hierarchy that the reader cannot see. Text that gives
   a false picture of the subject.
5. Fix each fault. Run steps 1 to 4 again. Repeat until both scripts and the tiles are clean.
6. Do the handoff from `SKILL.md` convention 6: print the path. Run `open index.html` only
   when you run for the user directly. Never run `open` inside a subagent.

## 7. Shared palette

The same palette is also in `templates/page.html`, `templates/video.html` and `video/src/theme.ts`. Change all four.
