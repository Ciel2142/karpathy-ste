# Explain `lesson` rung — design

Date: 2026-10-04
Status: approved 2026-10-04 after three cold reviews; amended 2026-10-06 to target the film
(`2026-10-05-explain-film-design.md`, its D4 and section 11): a clip is a short film, not an
explainer. The amendment is marked "A1" where it changes a rule; it is pending user review.

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
that the film pipeline lacks, that a code card shows only lines that a cite names. A clip that
cannot be made accurate is dropped; a page claim that cannot be supported is removed.

A1. A clip is a film (`2026-10-05-explain-film-design.md`): its words are data in `script.json`,
its picture is code in `scene/` against the kit, the `scene` and `guard` stages check it, and
the author reads its stills. A clip differs from a film in three numbers only: at most 60 s, a
usual length of 20 to 40 s, and a larger text floor because the page shows it at 75 %.

Success means:

- a reader can read the whole subject in the page without playing anything;
- each clip shows, in motion, what its section says, and nothing else;
- "Play all" walks the clips in order as a series;
- the review gates find real faults, measured in the live run against planted faults;
- the existing `page`, `video` (film) and `brainrot` rungs render unchanged.

## 2. Scope

In scope:

- `--as lesson` in the `explain` router, a rung file `rungs/lesson.md`, and a `lesson` row in
  the rung table, marked "forced only".
- A `clip` row in `video/formats.json` and the "format must be" message (A1, section 6.1); a
  `minText` value per format row, read by the guard (A1, section 6.1).
- A source-cite check in `build-timeline.mjs --check` for every format with `sources` (A1,
  section 6.2).
- The clip CSS, the `Play all` button and its script in `templates/page.html`.
- A `media` check in `verify.sh` for `rung=lesson`.
- Three reviewer prompt files under `<skill-dir>/lesson/`.
- A hint line in `rungs/page.md`.
- Tests, a gated E2E, and one live run with planted faults and fold-back.

Out of scope:

- Automatic rung selection of `lesson`. It is forced only (decision D1).
- Clips in the `brainrot` format. A clip is a 16:9 film (A1).
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

Requirements are the page rung's plus the video rung's (the Remotion workspace, the narrator
and `tsc` for the scene code, as `README.md` lists them). The language rule is the video rung's at the time of use:
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
| `clips/<id>/` | One complete film output per clip: `script.json` and `scene/` (the author's), everything that `rungs/video.md` section 7 lists (`audio/`, `build/`, `video.mp4`, the stills, the transcript `index.html`, `narration.md`), plus `poster.png` (section 4.2). |

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
page (sections, template, diagrams, snapshot steps) and of `video.md` for a clip (the grammar
of a film, the script, the scene, the kit, the marks, the guard, build and check, the FAIL
lines, the stills). It states:

- the clip criterion (4.1) and the zero-clip rule (4.1);
- `<meta name="explain-rung" content="lesson">`;
- the `figure.clip` markup (4.2), the poster rule (4.2) and the `Play all` behavior (4.3);
- the shape of `review/plan.md` (5.1);
- the clip `script.json` fields: `"format": "clip"`, `title`, `subject`, `not_covered` (5.1), and
  the start of `scene/` from the worked example (5.1);
- the clip limits and the 19 px text floor (6.1);
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
clip in `review/plan.md`; the page reviewer of gate 1 judges the choice, and the stills of gate
2 judge whether the picture earned it.

A1. The usual range is 2 to 3 clips of 20 to 40 s per lesson; the hard cap is 60 s per clip,
and there is no cap on the count. The film live runs (2026-10-05) measured about 7 lines of
scene code and 15 to 25 seconds of author time for each second of film, over 3 to 6 render runs;
a 30 s clip is therefore about 200 lines of scene code and 10 minutes, before the gates. The
lesson live run (7.5) measures the clip numbers and folds them back here and into `lesson.md`.

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

Poster rule (A1): `clips/<id>/poster.png` is a copy of one review still of the same clip,
`clips/<id>/review/still-NN-<id>-end.png` (the last frame of a scene; a film's picture builds up,
so the end of a scene is its fullest state). The default is the `-end` still of the last scene,
the finished picture. The author copies it in step 8 (section 5.5), after the clip's last
render, so the poster never shows a frame of an earlier render. `poster.png` exists so that the
page does not depend on `review/`, which is a review directory everywhere else.

`preload="none"` keeps a page with four clips light to open.

Width: `figure.clip` is a wide figure, like `.wide` in the provenance block: it breaks out of the
72ch column to `min(100% + 2 * <gutter>, 960px)`, centered. At 960 px a 1280 px clip shows at
75 %. A1: a film's text floor is 14 px on the canvas, which is 10.5 px here, under the page's own
14 px floor; so a clip's floor is 19 px (section 6.1), which shows at 14.25 px. In the 500 px
render the figure is the column width; the reader can go fullscreen.

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
guard rule in block 3 (`PLAYALL`, section 7.3). No
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
   rest in step 8. Write `clips/<id>/script.json` for each clip from the film template
   (`templates/video-script.json`): `"format": "clip"`; `title` = the section's `<h2>` question;
   `subject` = the lesson's subject and kind; `provenance` as the video rung requires;
   `not_covered` = `none`; `sources` for the lines the code card shows. Start `clips/<id>/scene/`
   from a copy of `<skill-dir>/video/src/film/` (the worked example) and write the picture as
   `video.md` section 4 says, with the clip's 19 px floor (A1).
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
A1: whether the picture earns its clip is judged from the stills at gate 2, not from the scene
code here. Mechanical facts (cites resolve, scene count, words per scene, source ranges) are not
on the lists: step 4 settled them.

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

5. Render each clip: `render.sh clips/<id>`, in the background with a log file. A1: the first
   render runs alone until its `workspace: ok` line (a first install must not run twice); the
   other clips then render at the same time, each in its own run directory (film spec D8 and
   section 7.6). Each run must end with its eleven `ok` lines (`rungs/video.md` section 5).
   - A `FAIL` whose cause is in `script.json` or `scene/` (`script`, `scene`, `timeline`,
     `guard`, `sync`, `stills`, `transcript`) is fixed there and re-rendered. The author may fix
     and re-render twice; a third such `FAIL` on the same clip drops it with reason
     `render: FAIL <cause>`. (A1: the film live runs needed 3 to 6 runs for a long film; a
     clip is short, and the gates come after.)
   - A `workspace` or `narration` `FAIL`, or a `render` or `guard` `FAIL` that names the renderer
     (`remotion render exit <n>`) and not the script or the scene, is an environment fault: print
     the stage line, tell the user, stop the lesson. Nothing is dropped for it.
6. Gate 2, in parallel, fresh subagents, prompt `<skill-dir>/lesson/review-render.md`. A1: a
   reviewer reads at most four stills (a subagent that reads more stalls; measured 2026-10-05).
   The stills of a clip that a reviewer gets are its `-end` stills, `still-NN-<id>-end.png`, one
   per scene: the author reads every still as `video.md` section 6 requires, and the reviewer
   reads the end state of each scene. A clip with more than four scenes gets more than one
   reviewer, each with four consecutive scenes and the whole script; their reports are
   `review/gate2-<id>-<part>-round-<k>.md`, `<part>` from 1. Inputs, as absolute paths:
   `clips/<id>/script.json`, the stills of its part, `clips/<id>/index.html` (the transcript),
   `index.html` with the section id, `{root}`, and the gate-1 reports of this clip. The author
   states at the top of the dispatch what changed in the script since gate 1, or `nothing`.

   Framing: "Hunt. Assume one still gives a false picture of what its scene narrates, and find
   it. `verdict: ok` with zero findings is expected for a correct clip."

   Checks, what only the picture can tell (A1: the first three are the film's stills review,
   `video.md` section 6; the guard already measured off-canvas, small and overlapping text):
   1. each `-end` still agrees with the narration of its scene, and nothing in the frame suggests
      a thing the narration does not say; text on the stage, a quoted line among it, gives a true
      picture of the subject;
   2. an `-end` still that equals the `-end` still of the scene before it: the scene changed
      nothing;
   3. a picture that is a list of sentences;
   4. the poster still (4.2) is informative on its own;
   5. if the script changed since gate 1, the changed narration or cites still pass the script
      reviewer's two checks (5.2); an unchanged script skips this.

   Same report shape, written to `{report}`, same `## Author` block. A `fix` means: edit
   `script.json` or `scene/`, re-render that clip, re-review with the round-1 report attached and
   the resolved/open ruling first. At most two rounds.
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

### 6.1 `clip` format (A1)

The formats live in `video/formats.json` (film spec section 7.1). This design adds one row and
one key:

| Place | Change |
|---|---|
| `formats.json` | a `clip` row: the `film` row with `maxTotalSeconds: 60` and `minText: 19`; the `film` row gets `minText: 14`, its value today |
| `build-timeline.mjs` | `clip` is a known format and is validated as a film; the message becomes `format must be film, brainrot or clip`; the timeline carries `minText` |
| `FilmStage.tsx` | the guard reads `minText` from the timeline props instead of the kit's `MIN_TEXT`; `kit.ts` drops `MIN_TEXT`, and `video.md` states the 14 px floor as a number |
| `render.sh`, `transcript.py`, `check_render.sh`, `types.ts` | `clip` takes the film path everywhere the code asks for the format: the `scene` and `guard` stages run, the composition is `Film`, the transcript has the film rows. The plan finds each `= "film"` test and makes it hold for `clip` |

Limits of `clip`: 1280×720, 3 to 30 scenes, 30 s per scene, 60 s total, 45 narration words,
lead 6, pause 12, 20 source lines, text floor 19 px. The total budget is checked by
`check_budgets.py` from the `maxTotalSeconds` of the timeline, with the existing text:
`timeline: FAIL total 61.0 s (max 60)`. A guard fault names the floor it measured against:
`SMALLTEXT 16.0 px "..."` on a clip is a fault; on a film it is not.

### 6.2 Source-cite check (`build-timeline.mjs --check`, every format with `sources`) (A1)

A film declares the file text that its code card may show in `sources` (`path`, `from`, `to`),
read from disk; its cites are separate. Nothing ties the two: a scene may cite file A at line 10
and show lines 40 to 60 of file B, and the gate reviewers cannot tell from a still which lines
are on the stage. So the check is mechanical, in `--check`:

- each `sources` entry's range `from`-`to` must contain the `line` of at least one cite, in any
  scene, whose `path` equals the entry's `path`;
- failure text, in the shape of the other source lines: `FAIL source <id>: no cite on <path>
  inside <from>-<to>`.

This tightens the film contract too. The plan runs the worked example, the fixtures and the
film E2E against it and fixes any that fail; an example that shows lines it does not cite was
wrong. This and `minText` are the two changes this design makes to film-owned code.

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
- `rungs/video.md`: the floor as a number per format (6.1).
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

### 6.5 Sequencing (A1)

Wave `lesson-page` touches no file that the film touches; it starts now, on `feat/explain-lesson`
cut from `main` (brainrot merged 2026-10-06). The other three waves target the film and wait for
`feat/explain-film` to merge to `main` (its waves `explainer-default` and `explainer-removal`,
epic kp-5s0, are the last two); the lesson branch then merges `main` and the `clip-format` wave
is planned against the merged code.

Constraint that this design places on the removal wave (kp-5s0), carried to that issue as a
note: where the code asks for the format, film-only behavior (the `scene` and `guard` stages, the
`Film` composition, the film transcript rows, the film validation) must hold for every format
that is not `brainrot`, or branch on a row key, never on `format == "film"` alone. A third format
then takes the film path with the row of 6.1 and nothing else.

## 7. Testing

### 7.1 Validator and formats (`test_video_timeline_clip.py`, one module per format) (A1)

- `format: "clip"`: a three-scene film script passes `--check` and builds a timeline with
  `maxTotalSeconds: 60` and `minText: 19`; a `film` timeline carries `minText: 14`.
- `format: "other"` fails with `format must be film, brainrot or clip`.
- `test_check_budgets.py`: a `clip` timeline of 61 s fails with `FAIL total 61.0 s (max 60)`;
  60 s passes.
- Source-cite check (6.2): a `sources` entry with no cite on its path inside its range fails
  with the 6.2 text; the same entry with such a cite passes; a cite on another file does not
  count. Run against the worked example, every fixture and the film E2E script.
- `test_film_guard.py`: with `minText: 19` in the props, a 16 px text is `SMALLTEXT 16.0 px`;
  with `minText: 14` it passes (the existing guard cases keep their values).
- `clip` takes the film path: a `clip` script through the `script` stage of `render.sh` prints
  `script: ok (<n> scenes)`, and `transcript.py` gives it the film rows.

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
  no `figure.clip`, or hidden on a page with one, is the guard status `PLAYALL`, reported
  through `verify.sh` like the guard's other statuses. `test_page_template.py` derives the broken
  state as it does for every rule, by one string edit with a unique anchor (delete the
  `body:not(:has(.clip))` rule), and asserts that status; the good template reports none.
- Each reviewer prompt file holds every placeholder of 6.4 that applies to it, the hunt sentence,
  the "zero findings is expected" sentence, the quoted-source-line rule, and `verdict: ok` /
  `verdict: fix`.

### 7.4 E2E (gated on `EXPLAIN_VIDEO_E2E=1`, like `video_e2e.py`)

A fixture lesson directory with one three-scene clip, its `scene/` a copy of the worked example
with a 19 px floor, renders through `render.sh` (eleven `ok` lines); the author's step 8 is
scripted (copy the poster, run `verify.sh`): six `ok` lines. (A1)

### 7.5 Live run

One run of `/explain <real subject> --as lesson` on a repository file or directory, with the
fold-back document in `docs/superpowers/spikes/`, as every rung so far had. The gates cannot be
unit-tested; the live run is their evidence, and it is designed to measure recall, not only
findings:

- Before gate 1, the author plants three faults and records them in `review/plants.md`, which no
  reviewer receives: one sentence in the page whose cited lines do not support it; one clip
  narration that disagrees with its section; one `sources` range that holds no cited line (this
  one must be caught by the 6.2 check in step 4, which the run confirms).
- The fold-back reports, in numbers: per gate and round, findings made, findings fixed, findings
  the author disputed, plants found and missed; clips dropped and claims removed; wall time and
  tokens per gate.
- The user adjudicates every disputed finding in the fold-back: reviewer error or author error.
  The planted faults are removed from the artifact before handoff; the fold-back says so.

These numbers decide whether the gates earn their cost, tune the two-round cap, and tune the
limits of 6.1 and the clip sizes of 4.1 (A1: lines of scene code and author minutes per clip,
and render runs per clip, as the film live run measured them).

## 8. Decisions log

- **D1. Forced only.** `lesson` is a style over `page`, with the video rung's requirements and
  minutes of render time. The router never picks it. The page rung prints a hint line instead.
- **D2. Clips where motion earns them, not everywhere.** Usual range 2 to 3 of 20 to 40 s
  (A1; was 2 to 4). The reason per clip is written down and reviewed. Zero clips is a page, and
  the rung stops.
- **D3. Directory, not `data:` URLs.** The artifact is the output directory. Inlining would make
  every tool parse a 5 to 15 MB file for no benefit and make clips impossible to re-render alone.
  A later `--bundle` step is possible and separate.
- **D4. One `script.json` and one `scene/` per clip; the pipeline changed in two small places.**
  The `clip` row with `minText`, and the source-cite check (6.2). A clip is a short film; the
  second change closes a grounding gap in the film itself. (A1: was the explainer row and a
  highlight-cite check on a component.)
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
- **D8. The first render alone, then at the same time.** (A1; was sequential.) The film's run
  directory gives each render its own project; only a first install must not run twice.
- **D9. Gate 1 outcomes before render.** Removal and drop apply before any render, so no render
  time is spent on a dropped clip and no clip is rendered against text that then changes.
- **D10. Planted faults measure the gates.** One run with self-graded findings cannot show what
  the gates missed; three recorded plants give recall, and the user adjudicates disputes.
- **D11. A clip is a film (A1).** The film replaced the explainer (film spec D1, D4); a clip
  gets the film's grammar, kit, guard and stills review, and differs in 60 s, 20 to 40 s usual,
  and a 19 px floor. Gate 1 no longer judges the picture from code; gate 2 judges the `-end`
  stills.
- **D12. The text floor is a format value (A1).** `minText` in the row, read by the guard, so a
  clip shown at 75 % keeps the page's 14 px floor. Rejected: a 1280 px breakout in the page (the
  page becomes a video page; 500 px readers lose the column).
- **D13. Four stills per reviewer, `-end` stills only (A1).** A reviewer that reads many images
  stalls; the end state of each scene is the picture the reader keeps; the author reads the rest.
