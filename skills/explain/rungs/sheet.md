# Rung: sheet
This file holds only what is specific to the sheet rung. `SKILL.md` has the generic rules.

## 1. When a sheet

A sheet is one fixed page of at most 6 facets. It holds reference material that the reader looks
at many times. It exports to a PNG for sharing.

The facet cap is 6. A forced `--as sheet` can bring more than 6 facets. Keep the 6 most important
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

1. Copy `~/.claude/skills/explain/templates/sheet.html` to `<output-dir>/index.html`.
2. Write the sheet title in `<title>` and in `.tb-title`.
3. Delete the demo content of each panel body and the author comments. Keep all ids, all classes,
   the `<style>` block and both guard scripts.
4. Set the panel count:
   - 6 panels: keep all panels. 5 panels: delete panel F. Add the class `tall` to `.title-block`.
   - 4 panels: delete panels F and C. Add `tall` to `.title-block`. Change A and B to
     `span-6`. Change the id and the `.tag` of old D to C, and of old E to D.
5. Each row adds up to 12 columns (`span-3` to `span-12`). In row 2 the title block takes the
   last 3 columns. Thus the panels in row 2 add up to 9.

Put one primitive in each `.panel-body`.

| Primitive | Class names | Use it for |
|---|---|---|
| tree | `ul.tree`, `.root`, `.what` | The map. Always panel A. |
| annotated example | `.sample`, `.markers`, `pre`, `.hl`, `dl.legend` | Code, sentences or messages with keys. |
| status table | `table.status`, `td.yes`, `td.no` | Rows with a check or a cross. |
| limits bars | `.limit`, `.limit-head`, `.bar`, `.ticks` | A number against its maximum. |
| timeline | `ol.timeline`, `.when`, `.what` | An ordered flow of up to 6 nodes. |
| rule list | `ul.rules` | Short rules, one for each `<li>`. |

- Put `data-ste="skip"` on the non-prose parts only: `ul.tree`, `.sample`, `table.status`,
  `.limit-head`, `ol.ticks` and `ol.timeline`. The legend and the rule list are prose.
- Annotated example: write one `<li>` in `.markers` for each line of the `<pre>`. Write an
  empty `<li>` for a line without a key. Escape `<` and `>` in the sample.
- Every font size is 12 px or more. Do not add a rule that sets a smaller size.
- Bar: set `--value` and `--max` on `.bar`. Write the tick labels from 0 to `--max` at equal
  steps. Keep the `max N` label in `.limit-head`.
- The title block has `.tb-title`, a `<dl>` of key and value pairs, `#provenance` (section 4)
  and `.not-covered`. Put `data-ste="skip"` on both `<dl>` blocks. Keep each value short. A
  value wraps and never truncates. The guard reports `OVERFLOW:title` if the block overflows.

## 4. Provenance recipe

Run these commands in the directory of the subject.

```
git rev-parse --show-toplevel
git rev-parse --short HEAD
git status --porcelain
git ls-files --error-unmatch <path>
```

- `--show-toplevel` gives the repo root. Write it in `data-root` of `#provenance`. Without a repo,
  write the directory of the subject there, and write `none` and `no` as Commit and Dirty.
- `--short HEAD` gives the Commit value (7 or more characters). If `git status --porcelain` prints
  anything, write `dirty` as the Dirty value. If not, write `no`.
- If `git ls-files --error-unmatch <path>` exits with a non-zero code, git does not track the
  file. Add the word `untracked` to each `<cite>` for that file.
- Set `data-kind` to `file`, `directory`, `topic` or `conversation`. Write the date as `YYYY-MM-DD`.
- Topic: write `model knowledge` as the Source, or list the URLs that you read. Conversation:
  write `unverified` in the Subject cell, and re-read and cite each file that it names.

A citation has this form. The path is relative to `data-root`. The snippet has at most 12
words, copied verbatim from that line.

```
<cite data-path="src/app.py" data-line="12" data-snippet="def main(argv):">src/app.py:12 "def main(argv):"</cite>
```

## 5. Write the prose

Write all prose in STE-80. These notes come from the lint of the `ste` skill.

- Close every element: `</li>`, `</p>` and `</dd>`. Never put `data-ste="skip"` on an element
  that you did not close. The skip then covers the text after it.
- Keep icons and `<img>` out of sentences. Put them in a separate element.
- Write a quote as `“…”` or as `<q>…</q>`. The lint counts a quote as one word.
- Start a safety text with `WARNING:` and put it in its own `<p>`.
- The lint does not read headings, table cells, `<cite>`, `<code>`, `<title>` or any
  `data-ste="skip"` subtree.
- A step of 21 to 25 words in an `<ol>` is a warning. A sentence of 26 words or more, in
  any place, is an error.

## 6. Verify and export

Do these steps in the output directory, in this order.
1. Run `~/.claude/skills/explain/scripts/verify.sh index.html`. All four lines must show
   `ok`: `self-contained`, `render 1920x1080`, `citations` and `prose`. Fix each cause that
   the detail lines name.
2. Run `~/.claude/skills/explain/scripts/snapshot.sh index.html sheet.png 1920 1080 2`. It writes
   `sheet.png` (3840x2160) and the tiles `review/sheet-01.png` to `review/sheet-04.png`.
3. Read the four tiles with the Read tool. Never read `sheet.png`.
4. Look for these faults. Clipped text. An empty panel. A red ribbon (`OVERFLOW:<letter>`).
   A bar without its `max N` label. A hierarchy that the reader cannot see. Text that gives
   a false picture of the subject.
5. Fix each fault. Run steps 1 to 4 again. Repeat until both scripts and the tiles are clean.
6. Do the handoff from `SKILL.md` convention 6: print the path. Run `open index.html` only
   when you run for the user directly. Never run `open` inside a subagent.

## 7. Shared palette
The template comment says that `templates/page.html` carries the same palette block. Change
both. If `page.html` does not exist yet, change `sheet.html` only.
