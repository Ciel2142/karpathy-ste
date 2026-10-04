# Explain `lesson` rung — design

Date: 2026-10-04
Status: approved in conversation section by section; revised after three cold reviews
(consistency, gates, ambiguity); written spec pending user review

## 1. Purpose

A `page` explains a subject in sections that the reader explores. A `video` explains it in a
narrated sequence, with motion. The `lesson` rung joins them: a page whose sections carry a short
narrated clip where narration plus motion explains the facet better than a still. The page is the
hub; the clips are additive. A "Play all" control plays the clips in document order, so the
lesson also works as a series of short videos.

The grounding of the explain skill does not change: every section and every scene carries cites,
the page passes `verify.sh`, each clip passes `render.sh`, and all prose follows the STE profile.
What the lesson adds beyond the two rungs is accuracy work: two review gates run by fresh
subagents, one on meaning before rendering, one on the picture after; and one mechanical check
that today's pipeline lacks, that a code scene highlights the lines it cites. A clip that cannot
be made accurate is dropped; a page claim that cannot be supported is removed.

Success means:

- a reader can read the whole subject in the page without playing anything;
- each clip shows, in motion, what its section says, and nothing else;
- "Play all" walks the clips in order as a series;
- the review gates find real faults, measured in the live run against planted faults;
- the existing `page`, `video` and `brainrot` rungs render unchanged.

## 2. Scope

In scope:

- `--as lesson` in the `explain` router, a rung file `rungs/lesson.md`, and a `lesson` row in
  the rung table, marked "forced only".
- A `clip` format: rows in the three format tables (`build-timeline.mjs`, `narrate.py`,
  `types.ts`) and the three "format must be" messages.
- A highlight-cite check in `build-timeline.mjs --check`, for every format (section 6.2).
- The clip CSS, the `Play all` button and its script in `templates/page.html`.
- A `media` check in `verify.sh` for `rung=lesson`.
- Three reviewer prompt files under `<skill-dir>/lesson/`.
- A hint line in `rungs/page.md`.
- Tests, a gated E2E, and one live run with planted faults and fold-back.

Out of scope:

- Automatic rung selection of `lesson`. It is forced only (decision D1).
- Clips in the `brainrot` format. Clips are 16:9 explainer-style.
- Inlining clips into the HTML as `data:` URLs (decision D3). A `--bundle` step is a possible
  later feature, not part of this design.
- Subtitles or caption tracks on the clips. The clip's transcript page is the text form.
- Autoplay. Nothing plays until the reader clicks.
- A second page template, or a demo clip in the page template (decision D5).

## 3. Interface

### 3.1 Invocation

`/explain <subject> --as lesson`. The router accepts `lesson` as a sixth `--as` value (after
`brainrot`, kp-ylh.8); the error for an unknown value lists six names. The rung table in
`SKILL.md` gets a `lesson` row:

| Rung | Choose when | Typical subject |
|---|---|---|
| `lesson` (page with clips, directory output) | Forced only (`--as lesson`). A page whose sections carry short narrated clips where motion explains better than a still | A subsystem with two to four moving parts |

The rung line reads `Rung: lesson (forced) — <reason> — subject: <subject> (<kind>)`.

Requirements are the page rung's plus the video rung's (the Remotion workspace and the
narrator, as `README.md` lists them). The language rule is the video rung's at the time of use:
English today; a later voice-per-language design may widen it, and the lesson inherits that
without a change here.

### 3.2 Hint line in the page rung

`rungs/page.md` section 2 (plan the sections) gets the criterion of section 4.1, copied, not
referenced: "a section would gain from a clip when narration plus motion explains it better than
a static view: a flow, a structure that builds up, a before and after, a camera move along code,
a comparison whose terms change". When the plan is written and at least one section meets it,
the page rung prints one line:

`<n> sections would gain from a clip; rerun with --as lesson`

The line is informational. The page rung builds the page as before.

### 3.3 Output directory

Convention 5 applies: `~/karpathy/out/YYYY-MM-DD-HHMMSS-lesson-<slug>/`. Contents:

| Path | Holds |
|---|---|
| `index.html` | The page. `<meta name="explain-rung" content="lesson">`. |
| `page.png`, `narrow.png`, `narrow-tall.png`, `review/page-NN.png`, `review/narrow-*.png` | The page rung's renders and tiles. |
| `review/plan.md` | The section list and clip choices (section 5.1, step 2). |
| `review/plants.md` | The planted faults of the live run (section 7.5). Absent in a normal run. |
| `review/gate1-page-round-<k>.md` | The page reviewer's report for round k, then the author's answer. |
| `review/gate1-<id>-round-<k>.md` | The script reviewer's report for clip `<id>`, round k, then the author's answer. |
| `review/gate2-<id>-round-<k>.md` | The render reviewer's report for clip `<id>`, round k, then the author's answer. |
| `clips/<id>/` | One complete video-rung output per clip: everything that `rungs/video.md` section 5 lists, plus `poster.png` (section 4.2). |

`<id>` is the id of the section that the clip belongs to. `snapshot.sh` deletes only
`review/<stem>-NN.png`, so the reports survive the page renders.

### 3.4 Convention 3 exception

Convention 3 ("one self-contained file") gets one stated exception in `SKILL.md`: for the
`lesson` rung the artifact is the output directory. `index.html` stays self-contained for CSS,
JS and fonts, with no CDN, no build step, and it opens offline from `file://`. Its only external
references are relative paths inside the output directory: `clips/<id>/video.mp4`,
`clips/<id>/poster.png` and `clips/<id>/index.html`. The `self-contained` check of `verify.sh`
flags `http://`, `https://` and `//` only, so it does not change.

### 3.5 Rung file

`rungs/lesson.md` holds everything the author needs at run time that is not in `page.md` or
`video.md`; the author never reads this spec. It names the sections of `page.md` to read for the
page (sections, template, diagrams, snapshot steps) and of `video.md` for a clip (script, cite
rules, components, cue rule, build and check, output directory). It states:

- the clip criterion (4.1) and the zero-clip rule (4.1);
- `<meta name="explain-rung" content="lesson">`;
- the `figure.clip` markup (4.2), the poster rule (4.2) and the `Play all` behavior (4.3);
- the shape of `review/plan.md` (5.1);
- the clip `script.json` fields: `"format": "clip"`, `title`, `subject`, `not_covered` (5.1);
- the clip limits (6.1);
- the build procedure with both gates, the report format, the round rule, the removal rule, the
  drop rule and the render-failure rule (section 5);
- the `Dropped clips` provenance row (5.4);
- the six `verify.sh` lines (6.3) and the clip-specific tile faults (5.5);
- the output directory (3.3);
- the handoff (5.5), with the disputed-findings list.

## 4. Page and clips

### 4.1 Which sections get a clip

A section gets a clip when narration plus motion explains it better than a static view. This is
not limited to flows: a structure that builds up step by step, a before and after, a camera move
along code, a comparison whose terms change over time. The author writes one line of reason per
clip in `review/plan.md`; the gate 1 reviewers judge whether the motion is earned.

The usual range is 2 to 4 clips per lesson. There is no hard cap.

Zero-clip rule: if the plan marks no section for a clip, the lesson rung prints the rung line,
says that no section earns a clip, offers `--as page`, and stops before step 3. It builds
nothing. (A lesson that loses every clip to the drop rule is different: it ships, with each clip
and its reason in the `Dropped clips` row, section 5.4.)

### 4.2 Clip markup and poster

Each clip is one `figure.clip` placed after the section's lead paragraph, before the section's
code, diagrams or player:

```html
<figure class="clip">
  <video controls preload="none" src="clips/<id>/video.mp4" poster="clips/<id>/poster.png"></video>
  <figcaption><span class="part"></span>One sentence that says what the clip shows.
    <a href="clips/<id>/index.html" data-ste="skip">transcript</a></figcaption>
</figure>
```

The markup lives in `rungs/lesson.md` and in the primitives table of `rungs/page.md`, not as a
demo in the template (D5). The `data-ste="skip"` on the link drops the bare word "transcript"
from the lint's prose (the lint drops an element with that attribute and its subtree); the
sentence before it is prose and follows the STE profile.

Poster rule: `clips/<id>/poster.png` is a copy of one review still of the same clip,
`clips/<id>/review/still-NN-<scene>.png`. The default is the first still of the first scene that
is not a `title` scene; a title card is allowed as scene 1 but is not the poster. The author
copies it in step 8 (section 5.5), after the clip's last render, so the poster never shows a
frame of an earlier render. `poster.png` exists so that the page does not depend on `review/`,
which is a review directory everywhere else.

`preload="none"` keeps a page with four clips light to open.

Width: `figure.clip` is a wide figure, like `.wide` in the provenance block: it breaks out of the
72ch column to `min(100% + 2 * <gutter>, 960px)`, centered. At 960 px a 1280 px clip shows at
75 %, so the 24 px code of the explainer canvas reads at 18 px, above the page's 14 px floor. In
the 500 px render it is the column width; the reader can go fullscreen.

Clips are additive: the section keeps its full text, code and cites. With every `figure.clip`
removed, the page is a complete page and passes `verify.sh` as a lesson (the `media` check has
nothing to check). The drop rule (5.4) depends on this.

### 4.3 Play all

The title block gets `<button id="play-all">Play all</button>`. Its code goes into the page
template's second script block, next to `explainPlayer` (the first and third blocks are the
verification guard, which stays untouched). The block's line budget is 200
(`test_script_budget_at_most_200_lines`); today it is 77 lines, and the play-all code is about
25. The block is marked with the comment `/* Play all */`.

Behavior, all of it:

- the script collects the `figure.clip video` elements in document order; with none, it returns
  and the button is hidden by CSS: `body:not(:has(.clip)) #play-all { display: none }`;
- a click starts a run from clip 1: it plays the clip, scrolls its section into view, and writes
  `Part k of N` into that figure's `span.part`;
- `ended` on the running clip clears its label and starts the next; after the last, the run ends;
- `error` on the running clip clears its label and skips to the next;
- `pause` by the reader, or `play` on another clip by hand, ends the run (the reader took
  control); a click on `Play all` during a run ends it and starts a new run from clip 1;
- the end of a run clears every `span.part`.

No `autoplay` attribute anywhere; the first play is the reader's click.

### 4.4 Template

`templates/page.html` gains: the `.clip`, `.clip video`, `.clip .part` and `#play-all` CSS, the
hidden-when-no-clip rule, the button in the title block, the play-all code in block 2, and one
guard rule in block 3 (`play-all-visibility`, section 7.3). No
demo `figure.clip`: a plain page would ship a leftover demo video that the page rung's `verify.sh`
cannot see, and the markup is two lines in the rung files. The template keeps
`content="page"` and passes `verify.sh` as it stands (`test_page_template.py`).

## 5. Build procedure

`rungs/lesson.md` replaces steps 3 to 6 of the SKILL.md build procedure with the steps below,
in order, in the output directory. The author is the main agent; the reviewers of both gates are
the only subagents.

### 5.1 Author

1. Read the STE profile, the named sections of `page.md` and `video.md`. Resolve the subject by
   the SKILL.md rules.
2. Plan. List the sections (page rung rules: one facet, one `<h2>` question, one nav entry). Mark
   the sections that get a clip. Write `review/plan.md`, one line per section:
   `<id> | <h2 question> | clip: yes|no | <reason, when yes>`. Apply the zero-clip rule (4.1).
3. Write `index.html` in full: every section's text, code, cites and its `figure.clip`. Section
   ids are fixed here and name the clips; if a later step renames, splits or merges a section,
   the author renames or removes `clips/<id>/` before step 6, and the `media` check catches the
   rest in step 8. Write `clips/<id>/script.json` for each clip from `templates/video-script.json`:
   `"format": "clip"`; `title` = the section's `<h2>` question; `subject` = the lesson's subject
   and kind; `provenance` as the video rung requires; `not_covered` = `none`.
4. Mechanical checks, before any review. On the page: `cite_check.py index.html` and
   `ste_lint.py --html index.html`. On each clip, the three tools of `render.sh` stage 1, as it
   runs them: `build-timeline.mjs --check clips/<id>/script.json --root <root>`,
   `transcript.py clips/<id>/script.json clips/<id>`, `verify.sh clips/<id>/index.html`. The
   transcript's `verify.sh` runs `cite_check.py` on the scene cites and the lint on the narration,
   so a wrong snippet, a dead line and a lint fault are all caught here. Fix until clean. The
   reviewers then spend their attention on meaning.

### 5.2 Gate 1: cold read before render

Dispatch, in parallel, fresh general-purpose subagents, never forks (a fork inherits the author's
context and its blind spots):

- one page reviewer, prompt `<skill-dir>/lesson/review-page.md`;
- one script reviewer per clip, prompt `<skill-dir>/lesson/review-script.md`.

Inputs are absolute paths that the reviewer reads itself: `index.html`, `review/plan.md`, the
clip's `script.json` (script reviewer), the section id to read in `index.html` (script
reviewer), and `provenance.root` to read the cited files. The prompt tells the reviewer to read
only these and the repo; this is an instruction, not a sandbox, and the spec says so.

Framing, in every prompt: "Hunt. Assume one claim in this file is not supported by its cited
lines, and find it. If, after reading every cite against the source, you find none, `verdict:
ok` with zero findings is the right answer and is expected for a correct artifact. Never report a
finding you cannot back with a quoted source line."

The page reviewer checks:

1. no sentence makes a claim that its cited lines, read from `{root}`, do not support;
2. no two sections contradict each other;
3. the clip choices in `review/plan.md` are the sections where motion explains more than a
   still, and no section that clearly needs one is missing.

The script reviewer checks:

1. the narration makes no claim that the cited lines, read from `{root}`, do not support;
2. clip and section agree: nothing in the narration contradicts the section text; the clip may
   say less, never something different;
3. motion is earned: each scene's component shows the thing the narration talks about, one
   motion per scene, and a reader would learn less from a still.

Mechanical facts (cites resolve, scene count, words per scene, cue order) are not on the lists:
step 4 settled them.

Report, written by the reviewer to `{report}` (`review/gate1-<page|id>-round-<k>.md`):

- a numbered list of findings. Each finding: the file, the location (line or scene id), the
  claim quoted, the source line(s) quoted verbatim as read from `{root}`, what is wrong, a
  one-line fix. A finding without a quoted source line is not a finding;
- the last line of the reviewer's text: `verdict: ok` or `verdict: fix`. `fix` when at least one
  finding exists.

The author then appends `## Author` to the report: for each finding, `fixed` with what changed,
or `not fixed` with why.

Round 2 runs for every reviewer whose round-1 report says `fix`, and for every clip or section
that changed after its round-1 reviewer read it (section 5.3). A clip added after round 1 gets
its round-1 script review inside the round-2 dispatch. A round-2 reviewer gets the same inputs
plus the round-1 report with its `## Author` block, and must first rule each round-1 finding
`resolved` or `open`, quoting the current source line, before hunting for new ones. At most two
rounds.

### 5.3 Gate 1 outcomes, applied before render

After round 2 (or after round 1 when everything is `ok`):

- **Removal rule (page).** A page claim under an `open` finding is removed from the page, never
  shipped. If the removal empties a facet, the facet goes to `Not covered`. The author then greps
  every clip narration for the removed claim; a clip that carries it is edited and goes through a
  gate 1 round again, or is dropped.
- **Drop rule, gate 1 (clip).** A clip under an `open` finding is dropped (5.4) now, before any
  render time is spent on it.
- **Disputed findings.** An `open` finding whose `## Author` says `not fixed` is removed or
  dropped all the same (D7), and the pair (finding, author's reason) goes to the handoff list
  (5.5) for the user to restore if the reviewer was wrong. The author never overrules a reviewer
  alone.
- **Propagation.** Any edit to a section after its script reviewer read it, or to a script after
  its page-reviewer context changed, triggers a re-read by that reviewer in the next round. If
  the rounds are exhausted, the edited item is dropped or removed, not shipped unreviewed.

### 5.4 Render, Gate 2, drop rule

5. Render each clip: `render.sh clips/<id>`, one after the other, in the background with a log
   file. Sequential, because the `workspace` stage installs on the first run and the narrator
   loads a model per run; two first runs at once would collide. Each run must end with its nine
   `ok` lines (`rungs/video.md` section 3).
   - A `FAIL` whose cause is in `script.json` (`script`, `timeline`, `sync`, `stills`,
     `transcript`) is fixed in the script and re-rendered. A second such `FAIL` on the same clip
     drops it with reason `render: FAIL <cause>`.
   - A `workspace` or `narration` `FAIL`, or a `render` `FAIL` that names the renderer and not
     the script, is an environment fault: print the stage line, tell the user, stop the lesson.
     Nothing is dropped for it.
6. Gate 2, in parallel, one fresh subagent per clip, prompt `<skill-dir>/lesson/review-render.md`.
   Inputs, as absolute paths: `clips/<id>/script.json`, every `clips/<id>/review/still-*.png`,
   `clips/<id>/index.html` (the transcript), `index.html` with the section id, `{root}`, and the
   gate-1 reports of this clip. The author states at the top of the dispatch what changed in the
   script since gate 1, or `nothing`.

   Framing: "Hunt. Assume one still gives a false picture of what its narration says at that
   cue, and find it. `verdict: ok` with zero findings is expected for a correct clip."

   Checks, what only the picture can tell:
   1. each still, at its cue, gives a true picture of what the narration says there: the lit
      diagram node is the one named, the bullets that appeared are the ones spoken, the before
      and after are the right way round; nothing in the frame suggests a thing the narration does
      not say;
   2. no clipped label, no overlapping text, no truncated code line, no element outside the
      frame;
   3. the poster still (4.2) is informative on its own;
   4. if the script changed since gate 1, the changed narration or cites still pass the script
      reviewer's three checks (5.2); an unchanged script skips this.

   Same report shape, written to `{report}` (`review/gate2-<id>-round-<k>.md`), same `## Author`
   block. A `fix` means: edit `script.json`, re-render that clip, re-review with the round-1
   report attached and the resolved/open ruling first. At most two rounds.
7. **Drop rule, gate 2.** A clip under an `open` finding after round 2 is dropped.

Dropping a clip: remove its `figure.clip` from the page; add `<id> — <reason>` to the
`Dropped clips` provenance row; keep `clips/<id>/` on disk, nothing links it. The provenance
`<dl>` gets a row `<div class="wide"><dt>Dropped clips</dt><dd>none</dd></div>`, always present;
with drops, `<dd>` holds `<id> — <reason>; <id> — <reason>`. The reason is the finding's one
line or the `render: FAIL <cause>` text. A dropped clip is not `Not covered`: the section's text
still explains the facet. A clip that the plan unmarks before any render (for instance after a
"motion not earned" finding) is a plan change recorded in `review/plan.md`, not a drop.

### 5.5 Finish and handoff

8. For each surviving clip, copy the poster still to `clips/<id>/poster.png` (rule 4.2). Run
   `verify.sh index.html`: all six lines `ok` (6.3). Then the page rung's snapshot steps
   (`page.md` section 7, steps 2 to 4) and the tile read, with two extra faults to look for: a
   clip poster whose text is unreadable in the 1440 tile, and a `Play all` button on a page with
   no clip. Fix, repeat step 8.
9. Handoff (convention 6): print the path; `open index.html` unless inside a subagent. Then print
   the disputed-findings list (5.3), one line per pair, or `disputed findings: none`.

## 6. Pipeline and skill changes

### 6.1 `clip` format

Three tables name the formats; each gets a `clip` entry, and the three messages change together:

| Place | Today | Change |
|---|---|---|
| `build-timeline.mjs` `FORMATS` | `explainer`, `brainrot` | `clip` = the explainer row with `minScenes: 1, maxScenes: 3, maxTotalSeconds: 60`. Hoist the explainer row to `const EXPLAINER = {...}` and spread it; `{ ...FORMATS.explainer }` inside the `FORMATS` literal is a TDZ error. Header comment lists three formats. |
| `build-timeline.mjs` messages (two places) | `format must be explainer or brainrot` | `format must be explainer, brainrot or clip` |
| `narrate.py` `FORMATS` | `{"explainer": "scene", "brainrot": "sentences"}` | add `"clip": "scene"`; message as above |
| `src/types.ts` `Format` | `"explainer" \| "brainrot"` | add `"clip"`; `Explain.tsx` (kp-ylh.4) treats it as the explainer layout |

Limits of `clip`: canvas 1280×720, 1 to 3 scenes, 60 s per scene, 60 s total, every other
limit as the explainer, `wordTimed: false`. A scene-count failure reads
`4 scenes (needs 1 to 3, clip)` (the existing message shape). The total budget is checked by
`check_budgets.py` (kp-ylh.6) from the `maxTotalSeconds` that the timeline carries, with the
existing text: `timeline: FAIL total 61.0 s (max 60)`. No format name in that text: kp-ylh.6
keeps the explainer texts byte-identical and this design follows it.

Tests that assert the old message change with it: `test_video_timeline_brainrot.py` (four
asserts), `test_narrate_sentences.py` (one).

### 6.2 Highlight-cite check (`build-timeline.mjs --check`, every format)

Today `--check` requires a highlight range to lie inside `source`, and a cite to have the right
shape; nothing ties the two. A scene may cite file A and show file B, or highlight lines no cite
names. The gate reviewers cannot tell from a still, because the still is rendered from the same
script. So the check is mechanical, in `--check`, for every format:

- for each `code-with-line-highlights` scene, each `highlights[i]` range must contain the `line`
  of at least one cite of the same scene whose `path` equals `props.source.path`;
- failure text: `highlights[<i>] range <from>-<to> has no cite on <source.path> inside it`.

This tightens the explainer and brainrot contracts too. The plan runs the existing fixtures and
the E2E scripts against it and fixes any fixture that fails; a fixture that highlights lines it
does not cite was wrong. This is the one change this design makes to the video rung beyond the
`clip` row.

### 6.3 `verify.sh`

`rung=lesson` uses the page viewports (`1440x900 500x844`) and adds a sixth line after `prose`:

`media: ok | FAIL <n> missing`

The check collects every `src` and `poster` of `video` elements, and every `href` of `a`
elements whose value starts with `clips/`; strips a `#…` fragment and a `?…` query; URL-decodes;
resolves relative to the directory of `index.html`; and counts the references whose path is not
an existing regular file. `<n>` counts references, not unique paths. Detail lines use the
`self-contained` form: `  <tag> <attr>=<value>`. A page with no `figure.clip` passes with
`media: ok`. `media: FAIL` makes the exit code 1 like every other FAIL. The unknown-rung message
lists `sheet, page, video or lesson`. The header comment's count becomes "sheet, page: four;
lesson: five; video: three".

### 6.4 Skill files

- `SKILL.md`: `--as` accepts `lesson`; the rung table row (3.1); `lesson` joins the list in
  "These seven rules apply to every artifact rung"; the convention 3 exception (3.4); convention
  5 points to `rungs/lesson.md` for the contents; the build procedure notes that for a lesson the
  rung file replaces steps 3 to 6.
- `rungs/page.md`: the criterion and the hint line (3.2); the `figure.clip` row in the
  primitives table; the second script block is named as the home of `explainPlayer` and
  `Play all`.
- `templates/page.html`: CSS, button, play-all code (4.4).
- New `rungs/lesson.md` (3.5).
- New `lesson/review-page.md`, `lesson/review-script.md`, `lesson/review-render.md`. Placeholders:
  `{subject}`, `{root}`, `{files}` (absolute paths, one per line), `{section}` (script and render
  reviewers), `{report}` (the absolute path to write), `{changes}` (render reviewer: what changed
  since gate 1, or `nothing`), `{previous}` (round 2: the absolute path of the round-1 report, or
  `none`). Each file carries the hunt framing with the "zero findings is expected" sentence, its
  checklist from section 5, the report format with the quoted-source-line rule, and the
  `verdict:` line rule.
- `README.md`: the `lesson` row in the per-rung requirements.

### 6.5 Sequencing and constraints on open work

The lesson branch starts from `feat/explain-brainrot` once wave brainrot-render (`kp-ylh`)
closes. Hard dependencies: the `FORMATS` table (landed), `check_budgets.py` and budgets from the
timeline in `render.sh` (kp-ylh.6, open), the transcript format rows (kp-ylh.7, open), the
`--as brainrot` route (kp-ylh.8, open).

Constraint that this design places on kp-ylh.6, kp-ylh.7 and kp-ylh.4, to be carried to those
issues as a note now: brainrot-only behavior (`--speed`, the `background` stage, the brainrot
transcript rows, the `Short` layout) branches on `format == "brainrot"` or on the row's
`wordTimed: true`, never on `format != "explainer"`. A third format with `wordTimed: false` then
takes the explainer path without a change. The lesson plan adds one test per place that a `clip`
script takes the explainer path.

## 7. Testing

### 7.1 Validator and formats (`test_video_timeline_clip.py`, one module per format as on the branch)

- `format: "clip"`: a one-scene script passes `--check`; a four-scene script fails with
  `FAIL script: 4 scenes (needs 1 to 3, clip)`; a `clip` script's timeline carries
  `maxTotalSeconds: 60` and `wordTimed` absent or false.
- `format: "other"` fails with `format must be explainer, brainrot or clip` in `--check` and in
  `narrate.py`.
- `explainer` and `brainrot` fixtures pass unchanged (existing modules).
- `test_check_budgets.py`: a `clip` timeline of 61 s fails with `FAIL total 61.0 s (max 60)`;
  60 s passes.
- Highlight-cite check (6.2): a code scene with a highlight range and no cite on `source.path`
  inside it fails with the 6.2 text; the same scene with such a cite passes; a scene that cites a
  different file than `source.path` fails. Run against every existing fixture and the E2E scripts.
- `narrate.py` with `clip` runs scene mode (one WAV per scene, no words file), asserted with the
  stub engine as `test_narrate.py` does.

### 7.2 `verify.sh` lesson (`test_verify.py`)

- a lesson fixture with one `figure.clip` whose `video.mp4`, `poster.png` and transcript exist:
  six `ok` lines, exit 0;
- the fixture with `poster.png` removed: `media: FAIL 1 missing`, a detail line
  `  video poster=clips/<id>/poster.png`, exit 1;
- an `href="clips/<id>/index.html#scene-1"`: `media: ok` (the fragment is stripped);
- the fixture with every `figure.clip` removed: six `ok` lines (the additive rule);
- `content="lesson"` is accepted; the unknown-rung message lists `lesson`.

### 7.3 Template and prompts (`test_page_template.py`, a new `test_lesson_prompts.py`)

- The template as it stands passes `verify.sh` (existing); block 2 holds `/* Play all */` and
  stays within 200 lines. The guard (block 3) gains one rule: `#play-all` visible on a page with
  no `figure.clip`, or hidden on a page with one, is the status `play-all-visibility`, reported
  through `verify.sh` like the guard's other statuses. `test_page_template.py` derives the broken
  state as it does for every rule, by one string edit with a unique anchor (delete the
  `body:not(:has(.clip))` rule), and asserts that status; the good template reports none.
- Each reviewer prompt file holds every placeholder of 6.4 that applies to it, the hunt sentence,
  the "zero findings is expected" sentence, the quoted-source-line rule, and `verdict: ok` /
  `verdict: fix`.

### 7.4 E2E (gated on `EXPLAIN_VIDEO_E2E=1`, like `video_e2e.py`)

A fixture lesson directory with one one-scene clip renders through `render.sh` (nine `ok`
lines); the author steps 8 are scripted (copy the poster, run `verify.sh`): six `ok` lines.

### 7.5 Live run

One run of `/explain <real subject> --as lesson` on a repository file or directory, with the
fold-back document in `docs/superpowers/spikes/`, as every rung so far had. The gates cannot be
unit-tested; the live run is their evidence, and it is designed to measure recall, not only
findings:

- Before gate 1, the author plants three faults and records them in `review/plants.md`, which no
  reviewer receives: one sentence in the page whose cited lines do not support it; one clip
  narration that disagrees with its section; one code scene whose highlight range is off its cite
  by a few lines (this one must be caught by the 6.2 check in step 4, which the run confirms).
- The fold-back reports, in numbers: per gate and round, findings made, findings fixed, findings
  the author disputed, plants found and missed; clips dropped and claims removed; wall time and
  tokens per gate.
- The user adjudicates every disputed finding in the fold-back: reviewer error or author error.
  The planted faults are removed from the artifact before handoff; the fold-back says so.

These numbers decide whether the gates earn their cost, tune the two-round cap, and tune the
limits of 6.1.

## 8. Decisions log

- **D1. Forced only.** `lesson` is a style over `page`, with the video rung's requirements and
  minutes of render time. The router never picks it. The page rung prints a hint line instead.
- **D2. Clips where motion earns them, not everywhere.** Usual range 2 to 4. The reason per clip
  is written down and reviewed. Zero clips is a page, and the rung stops.
- **D3. Directory, not `data:` URLs.** The artifact is the output directory. Inlining would make
  every tool parse a 5 to 15 MB file for no benefit and make clips impossible to re-render alone.
  A later `--bundle` step is possible and separate.
- **D4. One `script.json` per clip, the pipeline changed in two small places.** The `clip` row
  in three tables with its message, and the highlight-cite check for every format (6.2). A clip
  is a tiny video; the second change closes a grounding gap that the reviews found in the video
  rung itself.
- **D5. One page template, no demo clip.** `page.html` gains CSS, a button and an inert script;
  the markup lives in the rung files. A demo clip would ship broken in a plain page without
  anything to catch it.
- **D6. Two gates, fresh subagents, hunt with an exit, evidence per finding, two rounds with
  memory.** Gate 1 on meaning, gate 2 on the picture and on the post-gate-1 diff. Reviewers are
  not forks. Prompts say to find a fault and say that zero findings is the expected answer for a
  correct artifact. Every finding quotes its source line. Round 2 sees round 1 and rules on it.
- **D7. Drop and remove, never ship a disputed claim; the user, not the author, restores.** An
  inaccurate clip is worse than no clip; the additive rule makes dropping free. A disputed page
  claim is removed, and the dispute is handed to the user at handoff.
- **D8. Sequential renders.** Workspace installs and narrator model loads make parallel first
  runs unsafe; rendering is cheap enough (about 0.3 render-min per video-min) that sequence costs
  little.
- **D9. Gate 1 outcomes before render.** Removal and drop apply before any render, so no render
  time is spent on a dropped clip and no clip is rendered against text that then changes.
- **D10. Planted faults measure the gates.** One run with self-graded findings cannot show what
  the gates missed; three recorded plants give recall, and the user adjudicates disputes.
