# Explain `lesson` rung — design

Date: 2026-10-04
Status: approved in conversation section by section; written spec pending user review

## 1. Purpose

A `page` explains a subject in sections that the reader explores. A `video` explains it in a
narrated sequence, with motion. The `lesson` rung joins them: a page whose sections carry a short
narrated clip where narration plus motion explains the facet better than a still. The page is the
hub; the clips are additive. A "Play all" control plays the clips in document order, so the
lesson also works as a series of short videos.

The grounding of the explain skill does not change: every section and every scene carries cites,
the page passes `verify.sh`, each clip passes `render.sh`, and all prose follows the STE profile.
What the lesson adds beyond the two rungs is accuracy work: two review gates run by fresh
subagents, one on the scripts and the page before rendering, one on the rendered stills after.
A clip that cannot be made accurate is dropped; a page claim that cannot be supported is removed.

Success means:

- a reader can read the whole subject in the page without playing anything;
- each clip shows, in motion, what its section says, and nothing else;
- "Play all" walks the clips in order as a series;
- the review gates find real faults, measured in the live run;
- the existing `page`, `video` and `brainrot` rungs render unchanged.

## 2. Scope

In scope:

- `--as lesson` in the `explain` router, a rung file `rungs/lesson.md`, and a `lesson` row in
  the rung table, marked "forced only".
- A `clip` row in the `FORMATS` table of `build-timeline.mjs`.
- The clip pattern (`figure.clip`) and the play-all script in `templates/page.html`.
- A `media` check in `verify.sh` for `rung=lesson`.
- Three reviewer prompt files under `<skill-dir>/lesson/`.
- A hint line in `rungs/page.md`.
- Tests, a gated E2E, and one live run with fold-back.

Out of scope:

- Automatic rung selection of `lesson`. It is forced only (decision D1).
- Clips in the `brainrot` format. Clips are 16:9 explainer-style.
- Inlining clips into the HTML as `data:` URLs (decision D3). A `--bundle` step is a possible
  later feature, not part of this design.
- Subtitles or caption tracks on the clips. The clip's transcript page is the text form.
- Autoplay. Nothing plays until the reader clicks.
- A second page template. `templates/page.html` gains the pattern (decision D5).

## 3. Interface

### 3.1 Invocation

`/explain <subject> --as lesson`. The router accepts `lesson` as a sixth `--as` value; the error
for an unknown value lists six names. The rung table in `SKILL.md` gets a `lesson` row:

| Rung | Choose when | Typical subject |
|---|---|---|
| `lesson` (page with clips, directory output) | Forced only (`--as lesson`). A page whose sections carry short narrated clips where motion explains better than a still | A subsystem with two to four moving parts |

The rung line reads `Rung: lesson (forced) — <reason> — subject: <subject> (<kind>)`.

Requirements are the page rung's plus the video rung's (Remotion, ffmpeg, the narrator). The
language rule is the video rung's at the time of use: English today; a later voice-per-language
design may widen it, and the lesson inherits that without a change here.

### 3.2 Hint line in the page rung

`rungs/page.md` adds one rule: when the page rung plans its sections and sees sections that would
gain from a clip (section 4.1), it prints one line after the rung line:

`<n> sections would gain from a clip; rerun with --as lesson`

The line is informational. The page rung builds the page as before.

### 3.3 Output directory

Convention 5 applies: `~/karpathy/out/YYYY-MM-DD-HHMMSS-lesson-<slug>/`. Contents:

| Path | Holds |
|---|---|
| `index.html` | The page. `<meta name="explain-rung" content="lesson">`. |
| `page.png`, `narrow.png`, `narrow-tall.png`, `review/page-NN.png`, `review/narrow-*.png` | The page rung's renders and tiles. |
| `review/plan.md` | The section list and the clip choices with one line of reason each (section 5, step 2). |
| `review/gate1-page-round-<k>.md` | The page reviewer's report for round k, with the author's answer. |
| `review/gate1-<id>-round-<k>.md` | The script reviewer's report for clip `<id>`, round k, with the author's answer. |
| `review/gate2-<id>-round-<k>.md` | The render reviewer's report for clip `<id>`, round k, with the author's answer. |
| `clips/<id>/` | One complete video-rung output per clip (`rungs/video.md` section 5): `script.json`, `audio/`, `build/`, `video.mp4`, the stills, the transcript `index.html`. |

`<id>` is the section id of the section that the clip belongs to.

### 3.4 Convention 3 exception

Convention 3 ("one self-contained file") gets one stated exception in `SKILL.md`: for the
`lesson` rung the artifact is the output directory. `index.html` stays self-contained for CSS,
JS and fonts, with no CDN, no build step, and it opens offline from `file://`. Its only external
references are relative paths inside the output directory: `clips/<id>/video.mp4`,
`clips/<id>/review/still-01-<scene>.png` and `clips/<id>/index.html`. The `self-contained` check of
`verify.sh` already allows relative references (it flags `http://`, `https://` and `//` only),
so it does not change.

### 3.5 Rung file

`rungs/lesson.md` holds only what is specific to the lesson. It names the sections of `page.md`
to read for the page (sections, template, diagrams, snapshot arguments) and the sections of
`video.md` to read for a clip (script, cite rules, components, cue rule, build and check). It
states:

- the rule for which sections get a clip (section 4.1);
- the clip pattern and the play-all control (section 4.2 and 4.3);
- `"format": "clip"` in each `script.json` and the clip limits (section 6.1);
- the build procedure with the two gates (section 5);
- the drop rule and the removal rule (section 5.3);
- the output directory (section 3.3);
- the handoff: print the path, `open index.html`.

## 4. Page and clips

### 4.1 Which sections get a clip

A section gets a clip when narration plus motion explains it better than a static view. This is
not limited to flows: a structure that builds up step by step, a before and after, a camera move
along code, a comparison whose terms change over time. The author writes one line of reason per
clip in `review/plan.md`; the gate 1 reviewers judge whether the motion is earned.

The usual range is 2 to 4 clips per lesson. There is no hard cap. A lesson with no section that
earns a clip is a page; the author says so and offers `--as page`.

### 4.2 Clip pattern

Each clip is one `figure.clip` placed after the section's lead paragraph, before the section's
code, diagrams or player:

```html
<figure class="clip" data-clip="<id>">
  <video controls preload="none"
         src="clips/<id>/video.mp4"
         poster="clips/<id>/review/still-01-<scene>.png"></video>
  <figcaption><span class="part"></span><one sentence that says what the clip shows>
    <a href="clips/<id>/index.html">transcript</a></figcaption>
</figure>
```

The poster is the first still of the clip (scene 1 after its lead), so the page reads well before
anything plays. `preload="none"` keeps a page with four clips light to open. The one-sentence
summary follows the STE profile and is counted by `ste_lint.py`.

Clips are additive: the section keeps its full text, code and cites. With every `figure.clip`
removed, the page is a complete page and passes `verify.sh` as a lesson (the `media` check has
nothing to check). The drop rule (section 5.3) depends on this.

### 4.3 Play all

The title block gets a `Play all` button. Its script, in the page's third script block:

- collects the `figure.clip video` elements in document order;
- on click, plays the first; on each `ended`, plays the next and scrolls its section into view;
- while a run is active, fills `span.part` of the playing clip with `Part k of N`, and clears it
  when the run ends or the reader pauses;
- is inert when the page has no `figure.clip`: the button is hidden by CSS
  (`body:not(:has(.clip)) #play-all { display: none }`), and the script returns early.

About twenty lines. No autoplay attribute is used; the first play is the reader's click.

### 4.4 Template

`templates/page.html` gains the `figure.clip` demo pattern, the `Play all` button, its CSS and
the play-all script. The page rung's instruction "copy the pattern that you need before you
delete the demo content" covers it: a plain page deletes the demo clip and keeps the inert
button and script. The meta tag's content is `page` or `lesson`; the lesson rung tells the author
to set it. The template keeps `content="page"`, so `test_page_template.py` (the template passes
`verify.sh` as it stands) is not affected by the demo clip's paths: `media` runs for `lesson` only.

## 5. Build procedure

`rungs/lesson.md` replaces steps 3 to 6 of the SKILL.md build procedure with these steps, in
order, in the output directory.

### 5.1 Author

1. Read the STE profile, the named sections of `page.md` and `video.md`. Resolve the subject by
   the SKILL.md rules.
2. Plan. List the sections (page rung rules: one facet, one `<h2>` question, one nav entry).
   Mark the sections that get a clip, with one line of reason each. Write the list to
   `review/plan.md`.
3. Write `index.html` in full: every section's text, code, cites and its `figure.clip`. Section
   ids are fixed at this step and name the clips. Write `clips/<id>/script.json` for each clip
   from `templates/video-script.json`, with `"format": "clip"` and `provenance` as the video rung
   requires.
4. Cheap mechanical checks, before any review or render: `cite_check.py index.html`,
   `ste_lint.py --html index.html`, and the `script` stage for each clip
   (`build-timeline.mjs --check clips/<id>/script.json --root <root>`). Fix until all are clean.
   Reviewers spend their attention on meaning, not on faults the tools catch.

### 5.2 Gate 1: cold read before render

Dispatch, in parallel, fresh general-purpose subagents (not forks: a fork inherits the author's
context and its blind spots). Each gets files only, plus read access to the repo at
`provenance.root`:

- one page reviewer, prompt `<skill-dir>/lesson/review-page.md`, inputs `index.html` and
  `review/plan.md`;
- one script reviewer per clip, prompt `<skill-dir>/lesson/review-script.md`, inputs
  `clips/<id>/script.json`, `index.html` with the section id `<id>` to read, and `review/plan.md`.

Each prompt carries the hunt framing: "assume one claim in this file is not supported by its
cited lines; find it". A reviewer asked to confirm the author's work finds little.

The page reviewer checks:

1. every cite resolves: the file exists, the line exists, the snippet is verbatim on that line;
2. no sentence makes a claim that the cited lines do not support;
3. no two sections contradict each other;
4. the clip choices in `review/plan.md` are the sections where motion explains more than a still,
   and no section that clearly needs one is missing.

The script reviewer checks:

1. every cite resolves, as above;
2. the narration makes no claim that the cited lines do not support;
3. clip and section agree: nothing in the narration contradicts the section text; the clip may
   say less, never something different;
4. motion is earned: each scene's component shows the thing the narration talks about, and a
   reader would learn less from a still;
5. the video rules: 1 to 3 scenes, words per scene within the limit, cues in narration order,
   one motion per scene.

Report format, written by the reviewer to `review/gate1-<page|id>-round-<k>.md`:

- a list of findings, each with the file, the location (line or scene id), what is wrong, and a
  one-line fix. A finding without a file and a location is not a finding;
- the last line: `verdict: ok` or `verdict: fix`. `fix` when at least one finding exists.

The author appends a `## Author` block to each report: for each finding, `fixed` with what
changed, or `not fixed` with why. Round 2 runs only for reports with `verdict: fix`, with the
same prompt and the updated files. At most two rounds.

### 5.3 Render, Gate 2, drop rule

5. Render each clip: `render.sh clips/<id>`, one after the other, in the background with a log
   file. Sequential, because the `workspace` stage installs on the first run and the narrator
   loads a model per run; two first runs at once would collide. Each run must end with its nine
   `ok` lines (`rungs/video.md` section 3). A `FAIL` is fixed in that clip's `script.json` and
   re-rendered before gate 2.
6. Gate 2, in parallel, one fresh subagent per clip, prompt `<skill-dir>/lesson/review-render.md`,
   inputs `clips/<id>/script.json`, the stills `clips/<id>/review/still-*.png`, and the transcript
   `clips/<id>/index.html`. It checks what only the picture can tell:
   1. each still shows what the narration says at that cue: the highlighted lines are the cited
      lines, the diagram node that lights up is the one the narration names;
   2. no truncated code, no clipped label, no text too small to read in a page column;
   3. the transcript matches the script word for word, and the narrator row names the engine;
   4. the poster frame (`review/still-01-<scene>.png`) is informative on its own.

   Same report shape, `review/gate2-<id>-round-<k>.md`, same hunt framing ("assume one still
   shows the wrong lines; find it"). A `fix` means: edit `script.json`, re-render that clip,
   re-review. At most two rounds.
7. After round 2 of either gate:
   - **Removal rule (page).** A page claim still under a `fix` finding is removed from the page,
     never shipped. If the removal empties a facet, the facet goes to `Not covered`.
   - **Drop rule (clip).** A clip still under a `fix` finding is dropped: remove its
     `figure.clip`; add a provenance line `Dropped clips: <id> — <reason>` (the reason is the
     finding's one line). The section's text still explains the facet, so this is not
     `Not covered`. Keep `clips/<id>/` on disk; nothing links it.
8. `verify.sh index.html`: all six lines `ok` (section 6.2). Then the page rung's snapshot steps
   (`page.md` section 7, steps 2 to 4) and the tile read. Fix, repeat step 8.
9. Handoff (convention 6). Never run `open` inside a subagent.

The reviewers of both gates are the only subagents in the procedure. The author (the main
agent) writes the page and the scripts, and the main agent reads the page tiles as the page
rung does.

## 6. Pipeline and skill changes

### 6.1 `clip` format

`build-timeline.mjs` (on `feat/explain-brainrot`) holds a `FORMATS` table keyed by format. This
design adds one row:

| Limit | explainer | clip |
|---|---|---|
| canvas | 1280×720 | 1280×720 |
| scenes | 3–8 | 1–3 |
| max scene length | 60 s | 60 s |
| max total length | 150 s | 60 s |
| every other limit | as today | same as explainer |

`clip` is `{ ...FORMATS.explainer, minScenes: 1, maxScenes: 3, maxTotalSeconds: 60 }`. Same
canvas, lead, tail, component limits and `wordTimed: false`, so every component, check, still
and transcript row works unchanged. A limit failure names the format, as the brainrot design
states: `4 scenes (needs 1 to 3, clip)`.

`render.sh` takes its length budgets from the timeline after kp-ylh.6 (wave brainrot-render),
so it needs no change for `clip`. Stage lines are the video rung's nine lines, unchanged.
`transcript.py` emits the explainer rows for `clip`.

### 6.2 `verify.sh`

`rung=lesson` uses the page viewports (`1440x900 500x844`) and adds a sixth line after `prose`:

`media: ok | FAIL <n> missing`

The check collects every `src` and `poster` attribute of `video` elements, and every `href` of
`a` elements that starts with `clips/`, resolves each relative to the directory of `index.html`,
and counts the paths that are not existing files. Detail lines name each missing path. A page
with no `figure.clip` passes with `media: ok`. The unknown-rung message lists `sheet, page, video
or lesson`.

The header comment's count ("four checks; video: three") becomes "sheet, page: four; lesson:
five; video: three", counting `media` as a check and the renders as one.

### 6.3 Skill files

- `SKILL.md`: `--as` accepts `lesson`; the rung table row (3.1); the convention 3 exception
  (3.4); convention 5 points to `rungs/lesson.md` for the contents; the build procedure notes
  that for a lesson the rung file replaces steps 3 to 6.
- `rungs/page.md`: the hint line (3.2); the clip pattern in the primitives table.
- `templates/page.html`: the clip pattern, the `Play all` button, CSS and script (4.4).
- New `rungs/lesson.md` (3.5).
- New `lesson/review-page.md`, `lesson/review-script.md`, `lesson/review-render.md`: the
  reviewer prompts. Each has placeholders `{subject}`, `{root}`, `{files}` (and `{section}` for
  the script reviewer), the hunt framing, its checklist from section 5, the report format and the
  path to write the report to. The author fills the placeholders and passes the text as the
  subagent's prompt.
- `README.md`: the `lesson` row in the per-rung requirements.

### 6.4 Sequencing

The lesson branch starts from `feat/explain-brainrot` once wave brainrot-render (`kp-ylh`)
closes. Hard dependencies: the `FORMATS` table (landed in wave brainrot-timeline) and budgets
from the timeline in `render.sh` (kp-ylh.6, open). Until then this spec waits; the lesson is one
feature branch with its own waves.

## 7. Testing

### 7.1 Validator (`test_video_timeline.py`)

- `format: "clip"`: a one-scene script passes `--check`; a four-scene script fails with
  `4 scenes (needs 1 to 3, clip)`; a timeline whose total passes 60 s fails the `timeline` stage
  with a message that names `clip`.
- `explainer` and `brainrot` fixtures pass unchanged.

### 7.2 `verify.sh` lesson (`test_verify.py`)

- a lesson fixture with one `figure.clip` whose `video.mp4`, poster and transcript exist: six
  `ok` lines;
- the same fixture with the poster file removed: `media: FAIL 1 missing` and a detail line with
  the path;
- the fixture with every `figure.clip` removed: six `ok` lines (the additive rule, mechanically);
- `content="lesson"` is accepted; an unknown rung's message lists `lesson`.

### 7.3 Template and prompts

- `templates/page.html` holds `figure.clip`, `#play-all` and the play-all script; a page built
  from it with no clip renders with the button hidden (checked in the lesson fixture's 1440x900
  tile by the live run, and statically by a test that the CSS rule exists).
- Each reviewer prompt file holds its placeholders, the hunt sentence, and the line
  `verdict: ok` / `verdict: fix` in its report format.

### 7.4 E2E (gated)

Gated like the brainrot E2E on an existing workspace: a fixture lesson directory with one
one-scene clip renders through `render.sh` (nine `ok` lines), and its `index.html` passes
`verify.sh` with six `ok` lines.

### 7.5 Live run

One run of `/explain <real subject> --as lesson` on a repository file or directory, with the
fold-back document in `docs/superpowers/spikes/`, as every rung so far had. The gates cannot be
unit-tested; the live run is their evidence. The fold-back must report, in numbers: findings per
gate and per round, how many the author fixed, how many were wrong (the reviewer's error), clips
dropped, claims removed, and the wall time of each gate. These numbers decide whether the gates
earn their cost, and tune the limits of section 6.1.

## 8. Decisions log

- **D1. Forced only.** `lesson` is a style over `page`, with the video rung's requirements and
  minutes of render time. The router never picks it. The page rung prints a hint line instead.
- **D2. Clips where motion earns them, not everywhere.** Usual range 2 to 4. The reason per clip
  is written down and reviewed.
- **D3. Directory, not `data:` URLs.** The artifact is the output directory. Inlining would make
  every tool parse a 5 to 15 MB file for no benefit and make clips impossible to re-render alone.
  A later `--bundle` step is possible and separate.
- **D4. One `script.json` per clip, the existing pipeline unchanged.** The only pipeline change
  is the `clip` format row. A clip is literally a tiny video.
- **D5. One page template.** `page.html` gains the pattern and an inert script; no second
  template, no CSS duplication.
- **D6. Two gates, fresh subagents, hunt framing, two rounds.** Pre-render on meaning, post-render
  on the picture. Reviewers are not forks. Prompts tell them to find a fault, not to confirm.
- **D7. Drop and remove, never ship a disputed claim.** An inaccurate clip is worse than no clip;
  the additive rule makes dropping free. A disputed page claim is removed.
- **D8. Sequential renders.** Workspace installs and narrator model loads make parallel first
  runs unsafe; rendering is cheap enough (about 0.3 render-min per video-min) that sequence costs
  little.
