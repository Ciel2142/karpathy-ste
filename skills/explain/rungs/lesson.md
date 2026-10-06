# Rung: lesson
This file holds only what is specific to the lesson rung. `SKILL.md` has the generic rules.

## 1. When a lesson

A lesson is a page whose sections carry short narrated clips. The page is the hub, and the clips
are additive. A reader can read the whole subject in the page without a clip. A `Play all` button
plays the clips in document order, so the lesson also works as a series of short videos.

Use a lesson only when the user writes `--as lesson`. Never choose it from the content. The
grounding does not change. Each section and each scene has cites. The page passes `verify.sh`,
each clip passes `render.sh`, and all prose follows the STE profile. For a non-English lesson,
follow `SKILL.md` convention 7.

Print this line before you build, as `SKILL.md` says:

```
Rung: lesson (forced) — <reason> — subject: <subject> (<kind>)
```

The `<reason>` names `--as lesson` and tells if the content fits a lesson.

A section would gain from a clip when narration plus motion explains it better than a static
view. Examples: a flow, a structure that builds up, a before and after, a camera move along code,
a comparison whose terms change. A section that meets this criterion gets a clip. A clip is not
only for a flow.

If the plan marks no section for a clip, print the rung line, say that no section earns a clip,
and offer `--as page`. Then stop before you write the page. Build nothing. A lesson that loses
each clip to a drop rule is different: it ships, with the reasons in the provenance ("Drop a
clip" below).

The lesson rung is English or Russian. A Russian lesson has `<html lang="ru">` on its page and
`"lang": "ru"` in the `script.json` of each clip. If the user asks for another language, print the
rung line. Say that the lesson rung is English or Russian. Stop. Offer `page`.

The requirements are the requirements of the page rung and of the video rung. The Remotion
workspace, the narrator and `tsc` make the clips. `README.md` lists them.

The sections below follow the order of the build: plan, write, check, gate 1, render, gate 2,
drop, finish. The two gates are reviews by fresh subagents. They are the only subagents of a
lesson. You are the author.

## 2. What to read

Read the STE profile, `<skill-dir>/../ste/SKILL.md`, by path. Write all prose under it. For a
non-English lesson, follow `SKILL.md` convention 7. The steps of this file replace steps 3 to 6 of
the Build procedure of `SKILL.md`.

For the page, read these sections of `<skill-dir>/rungs/page.md` and follow them: "Plan the
sections", "Fill the template", "Diagram patterns", "Provenance", "Write the prose" and "Verify and
export". This file changes some of their steps, and it says where.

For each clip, read these sections of `<skill-dir>/rungs/video.md` and follow them: "The grammar
of a film", "Write the script", "Write the scene", "The kit", "Marks", "Text on the stage", "The
guard", "Build and check", "The FAIL lines" and "Read the stills".

A section that this file names includes its subsections. The lesson has its own handoff and its
own output directory: "Finish and handoff" and "Output directory" below give them.

Where this file and a rung file that it names differ, this file wins. A file that a named section
points to is part of the read. "Provenance" and "Write the prose" in `page.md`, and "Write the
script" in `video.md`, point to the sections "Provenance recipe" and "Write the prose" of
`<skill-dir>/rungs/sheet.md`. Read those two sections too. Also read the conventions of `SKILL.md`,
the templates that this file names and the three prompt files of the two gates. You need no design
document.

## 3. Plan the lesson

1. Resolve the subject by the rules of `SKILL.md`. Print the rung line.
2. List the sections by the page rung rules: one facet, one `<h2>` question and one nav entry for
   each. Give each section an id. For a directory subject, the first section is the whole, start
   to end (the rule of `page.md` "Plan the sections"); the mechanics follow.
3. Mark each section that gets a clip. Use the criterion of "When a lesson" above. The main flow
   of the first section is the first candidate. Motion along a path is what a still cannot show.
4. Write `review/plan.md` in the output directory. Write one line for each section:

```
<id> | <h2 question> | clip: yes|no | <reason, when yes>
```

5. Apply the zero-clip rule of "When a lesson". If no section has `clip: yes`, stop.

The reason of a clip says what the motion shows that a still cannot show. The page reviewer of
gate 1 judges your choices from these lines.

The usual range is 2 to 3 clips in a lesson. A usual clip is 20 to 40 s long. A Russian clip of
20 to 40 s holds approximately 45 to 90 words. The row "max total length" of the table in "Write
the page and the clips" gives the longest clip. There is no cap on the number of clips.

Count the cost before you mark a clip. The first lesson run measured about 5 lines of scene code
for each second of clip (the film runs: 7). A clip of 38 s took 2 to 7 render runs. Three clips
took about 30 minutes of author time. A reviewer run costs about 115k subagent tokens; a clip of
5 scenes takes 3 to 4 reviewers in each gate-2 round. The gates took 22 minutes of a 2 h 30 run.

## 4. Write the page and the clips

Write `index.html` in full before the first review. It has the text, the code and the cites of
each section, and the `figure.clip` of each clip. Then write the files of each clip.

### The page

Copy `<skill-dir>/templates/page.html` to `index.html` and fill it as "Fill the template" in
`page.md` says, with the changes below.

Set the `lang` attribute of `<html>` to the language of the artifact: `en` or `ru`.

Set the meta of the page to this line. `verify.sh` runs the `media` check only for this value.

`<meta name="explain-rung" content="lesson">`

Fix the section ids now. They name the clips: the clip of the section `<id>` is in
`clips/<id>/`. If a later step renames, splits or merges a section, rename or remove the
directory `clips/<id>/` before you render. The `media` check finds each fault that remains.

Put one `figure.clip` in each section that the plan marks. Put it after the lead paragraph of the
section, and before the code, the diagrams and the player of the section. Write this markup, with
the section id for `<id>`:

```html
<figure class="clip">
  <video controls preload="none" src="clips/<id>/video.mp4" poster="clips/<id>/poster.png"></video>
  <figcaption><span class="part"></span>One sentence that says what the clip shows.
    <a href="clips/<id>/index.html" data-ste="skip">transcript</a></figcaption>
</figure>
```

- Keep `span.part` empty. `Play all` writes in it.
- The sentence of the `figcaption` is prose. Write it in STE. The attribute `data-ste="skip"` on
  the link drops the word "transcript" from the prose lint. Keep it.
- Keep `preload="none"`. A page with four clips stays light to open. Never write `autoplay`.
  Nothing plays until the reader clicks.
- The section keeps its full text, code and cites. A clip is additive. With each `figure.clip`
  removed, the page is a complete page, and it passes `verify.sh` as a lesson.

The page shows a clip at 75 %: the figure is 960 px wide on a wide screen. In the render of
500 px, the figure is as wide as the column. The reader can go fullscreen.

The file `clips/<id>/poster.png` is a copy of one still of the same clip,
`clips/<id>/review/still-NN-<scene>-end.png`. `<scene>` is the id of a scene. The `-end` still is
the last frame of a scene. The picture of a film builds up, so this frame is the fullest state of
the scene. The default is the `-end` still of the last scene: the finished picture.

You copy the still after the last render of the clip ("Finish and handoff" below). Thus the poster
never shows a frame of an earlier render. The page does not depend on `review/`, because it uses
the poster.

The template gives the `Play all` button and its code. You write no code for it. These facts hold:

- The button is in the title block. CSS hides it on a page with no `figure.clip`.
- A click starts a run from clip 1. The run plays the clip, scrolls its section into view and
  writes `Part k of N` in the `span.part` of the clip.
- When a clip ends, or fails to play, the run starts the next clip. After the last clip, the run
  ends.
- A pause by the reader, or a play of another clip by the reader, ends the run. A click during a
  run starts a new run from clip 1.
- The end of a run clears each `span.part`.

Keep the button and the three script blocks, as "Fill the template" in `page.md` says.

Add this row to the `<dl>` of the provenance. The row is always present. Write `none` until you
drop a clip ("Drop a clip" below):

```
<div class="wide"><dt>Dropped clips</dt><dd>none</dd></div>
```

### The clips

Write `clips/<id>/script.json` for each clip. Copy `<skill-dir>/templates/video-script.json` to
it, and follow "Write the script" in `video.md`, with these differences:

| Key | Value |
|---|---|
| `format` | `"format": "clip"`. Keep this key. Without it, the script is a film, with the limits of a film. |
| `title` | The `<h2>` question of the section. |
| `subject.text`, `subject.kind` | The subject of the lesson and its kind. |
| `provenance` | The same keys and rules as a film. The root is the absolute path of the repo root. |
| `provenance.not_covered` | `none`. |
| `sources` | The ranges of the source lines that the code card shows. A range stays inside the row `source lines` of the table below. |

Start `clips/<id>/scene/` from a copy of `<skill-dir>/video/src/film/`, the worked example. Write
the picture as "Write the scene" in `video.md` says. A clip is a short film. Its scene code obeys
the grammar of a film, the kit, the marks and the guard of that file.

A clip differs from a film in three numbers: its length, its usual length and its text floor. The
page shows a clip at 75 %, so the floor of a clip is larger. Keep each text of the clip inside
the limits of this table:

| Limit | clip |
|---|---|
| canvas | 1280×720 |
| scenes | 3–30 |
| max scene length | 30 s |
| max total length | 60 s |
| narration words per scene | 45 |
| lead / default pause frames | 6 / 12 |
| source lines | 12 |
| smallest text | 19 px |

Draw each text at 19 px or more on the canvas, and each text in `C.muted` at 22 px or more.

The guard measures the first number only. Check the second number yourself. It is the rule of a
film for a dim caption, 16 px or more, made larger for a clip that the page shows at 75 %.

## 5. Check before the review

Run these commands before any review. Run the first two in the output directory. Run the last
three for each clip. `<root>` is the `provenance.root` of the script.

```
python3 <skill-dir>/scripts/cite_check.py index.html
python3 <skill-dir>/../ste/scripts/ste_lint.py --html index.html
node <skill-dir>/video/build-timeline.mjs --check clips/<id>/script.json --root <root>
python3 <skill-dir>/video/transcript.py clips/<id>/script.json clips/<id>
<skill-dir>/scripts/verify.sh clips/<id>/index.html
```

The first command checks each cite of the page. The second checks the prose of the page. The third
checks one `script.json` against the limits of its format. The fourth writes the transcript of the
clip. The fifth runs `verify.sh` on that transcript. It checks the cites of the scenes and the
lint of the narration.

Thus a wrong snippet, a dead line and a lint fault all show here. Fix each fault, and run the
commands again until all are clean. The reviewers then spend their attention on meaning.

## 6. Gate 1: read before the render

Gate 1 is a cold read of the page and of each script before any render. Start fresh general-purpose
subagents, in parallel. Never start a fork: a fork has your context and your blind spots. Start:

- one page reviewer, with the prompt `<skill-dir>/lesson/review-page.md`;
- one script reviewer for each clip, with the prompt `<skill-dir>/lesson/review-script.md`.

At each gate 1 dispatch, copy the `clips/<id>/script.json` of each clip that you send to a script
reviewer to `review/gate1-<id>.script.json`, before you start the reviewers. The new copy replaces
the old one. A clip that you add in round 2 gets its copy in that dispatch. Gate 2 compares the
script with the last copy.

Each prompt file is a template. Read it. Replace each name in braces with plain text. Give the
result to the subagent as its prompt. Fill the names like this:

| Name | Fill with |
|---|---|
| `{subject}` | The subject of the lesson, as the rung line shows it. |
| `{root}` | The absolute path of the repo root: the `data-root` of the page and the `provenance.root` of the scripts. |
| `{files}` | The files that the reviewer reads, as absolute paths, one on each line. The page reviewer gets `index.html` and `review/plan.md`. The script reviewer gets these two files and `clips/<id>/script.json`. |
| `{section}` | In the prompt of a script reviewer: the id of the section of the clip. The page prompt has no such name. |
| `{report}` | The absolute path that the reviewer writes its report to. The names are below. |
| `{previous}` | `none` in round 1. In round 2: the absolute path of the round-1 report, with your `## Author` block. For a verification read: the report of the round before it. |

The prompt tells the reviewer to read only these files and the repo. It also closes the output
directory and its parent directory, except the files that you list and the report of `{previous}`.
Thus `review/plants.md`, the reports that you do not list and the directories of earlier runs are
outside what a reviewer reads. This is an instruction, not a sandbox. A reviewer can read any file,
so write no secret and no hint of a fault in a file that it reads.

The reviewer writes its report to `{report}`:

- `review/gate1-page-round-<k>.md` for the page reviewer;
- `review/gate1-<id>-round-<k>.md` for the script reviewer of the clip `<id>`.

`<k>` is the number of the round: 1 or 2. The report has a numbered list of findings. Each finding
has the file, the location, the claim quoted, the source lines quoted from `{root}`, what is
wrong, and a fix in one line. A finding with no quoted source line is not a finding. The last line
of the report is `verdict: ok` or `verdict: fix`.

Then append `## Author` to the report. For each finding, write `fixed` with what changed, or `not
fixed` with why.

Round 2 runs for each reviewer whose round-1 report says `verdict: fix`. It runs also for each
clip or section that changed after its round-1 reviewer read it. A round-2 reviewer gets the same
inputs. `{previous}` is the round-1 report with your `## Author` block. The reviewer first rules
each round-1 finding `resolved` or `open`, and quotes the current source line. Then it hunts for
new faults.

A clip that you add after round 1 gets its script review in the round-2 dispatch, and for it
`{previous}` is `none`. There are two hunting rounds at most.

A finding that a round-2 reviewer makes first, and that you fix, gets one verification read.
Start a fresh reviewer with the same prompt, with the round-2 report (with your `## Author`
block) as `{previous}` and the current page or script. It rules the finding `resolved` or
`open`, and it hunts for nothing new. Its report is `review/gate1-<id>-round-3.md`.

That read can re-open the finding, or a finding that an earlier round ruled `resolved`, because
your fix moved the fault. That is a regression of your last fix, not a new fault. Then one more
verification read follows your next fix: `round-4`, one at most. A finding that no read rules
after your fix is `open`, whatever your `## Author` block says.

After the last read, apply these rules before any render:

- Removal rule, for the page. Remove from the page each claim that has an `open` finding. Never
  ship it. If the removal empties a facet, write the facet in `Not covered`. Then search the
  narration of each clip for the removed claim. Drop each clip that has it. An edit of the
  narration needs a review round, and no round remains.
- Drop rule, for a clip. Drop each clip that has an `open` finding now ("Drop a clip" below).
  Then no render time goes to it.
- Disputed findings. An `open` finding whose `## Author` says `not fixed` is a disputed finding.
  Remove the claim or drop the clip all the same. Keep the pair (the finding, your reason) for
  the handoff. The user restores the claim or the clip if the reviewer was wrong. Never overrule
  a reviewer alone.
- Propagation. If you edit a section after its script reviewer read it, that reviewer reads it
  again in the next round. The same holds for a script, after the page reviewer read a page that
  changed. If no round remains, drop the clip or remove the claim. Never ship an edit that no
  reviewer read.

## 7. Render the clips

Render each clip with `<skill-dir>/scripts/render.sh clips/<id>`. Run each render in the
background, with its output in a log file.

The first render runs alone, until its `narration (<engine>): ok` line shows. A first install must
not run two times, and the first narration of an engine resolves its Python packages (`torch` for
`Silero`). Then start the other clips at the same time. Each render has its own run directory.

Each run must end with its eleven `ok` lines, as "Build and check" in `video.md` shows. Read the
`FAIL` line of a run that stops. These rules tell what to do:

- A `FAIL` with its cause in `script.json` or in `scene/` is a fault of the author. The causes are
  `script`, `scene`, `timeline`, `guard`, `sync`, `stills` and `transcript`. Fix the fault there,
  as "The FAIL lines" in `video.md` says, and render the clip again.
- You can fix and render again two times. A third such `FAIL` on the same clip drops the clip,
  with the reason `render: FAIL <cause>`. Only `FAIL` runs count. A render after your own read of
  the stills does not count.
- `render: FAIL remotion render exit <n>` with a `MARK scene` line in `build/render.log` is a bad
  mark in the scene code. This is a fault of the author, as above.
- A `container` `FAIL` is a fault of the environment: the mp4 has a wrong size or a wrong frame
  rate. Print the stage line, tell the user and stop the lesson. Drop nothing for it.
- A `workspace` `FAIL` or a `narration` `FAIL` is a fault of the environment. So is a `render`
  `FAIL` or a `guard` `FAIL` that names the renderer and shows no `MARK` line. Print the stage
  line, tell the user and stop the lesson. Drop nothing for it.

## 8. Gate 2: read the stills

Gate 2 is a cold read of the stills of each clip that rendered.

1. Read every still of each clip yourself first, as "Read the stills" in `video.md` says. Fix each
   fault, and render the clip again.
2. Split the stills of each clip into parts, by whole scenes. A part has five stills at most,
   with one exception that follows: a subagent that reads many images stalls.
3. Start one fresh general-purpose subagent for each part, in parallel. Never start a fork. Its
   prompt is `<skill-dir>/lesson/review-render.md`, filled as the next paragraphs say.

A part holds one or more whole scenes. It holds each still of these scenes:
`still-NN-<scene>-s<k>.png` for each sentence, and `still-NN-<scene>-end.png`. It also holds the
`-end` still of the scene before its first scene. The first scene of a clip has no scene before
it, so its part has no such still.

A part has five stills at most. A scene that does not fit in five stills with that `-end` still
gets a reviewer of its own. That reviewer gets all the stills of the scene and that `-end` still:
this is the only kind of part with more than five stills.

The sentence stills are the only place where a reviewer sees on-stage text that appears and goes
inside a scene. That text is in no script and in no source.

Fill the names of the prompt like this. `{subject}`, `{root}` and `{section}` are as in gate 1:

| Name | Fill with |
|---|---|
| `{files}` | Absolute paths, one on each line: `clips/<id>/script.json`; `review/gate1-<id>.script.json`; the stills of the part; the transcript `clips/<id>/index.html`; `index.html`; the gate-1 reports of the clip, each with its `## Author` block. |
| `{report}` | `review/gate2-<id>-<part>-round-<k>.md`, as an absolute path. `<part>` counts from 1. `<k>` is the number of the read. |
| `{changes}` | What changed in the script since gate 1, in plain words, or `nothing` when `script.json` and the gate-1 copy are the same. The reviewer compares the two files itself. |
| `{previous}` | `none` in round 1. In round 2: the absolute path of the round-1 report of the same part. For a verification read: the report of the round before it, of the same part. |

The reviewer reads each still with the Read tool, and writes its report to `{report}`. The report
has the same shape as at gate 1. The last line is `verdict: ok` or `verdict: fix`. You append
`## Author` to it, as at gate 1. One `open` finding in any part counts for the clip.

A `fix` means this: edit `script.json` or `scene/`, and render the clip again. Then start the
reviewers of that clip again, with the round-1 report of each part as `{previous}`. They rule each
round-1 finding `resolved` or `open` first. There are two hunting rounds at most.

A finding that a round-2 reviewer makes first, and that you fix, gets one verification read. Start
a fresh reviewer with the prompt `review-render.md`, with the round-2 report as `{previous}`
and the new stills of that scene. It rules the finding `resolved` or `open`, and it hunts for
nothing new. Its report is `review/gate2-<id>-<part>-round-3.md`.

That read can re-open the finding, or a finding that an earlier round ruled `resolved`, because
your fix moved the fault. That is a regression of your last fix, not a new fault. Then one more
verification read follows your next render: `round-4`, one at most. It rules those findings
only.

Drop rule, for gate 2. Drop a clip that has an `open` finding after the last read. Drop a clip
that has a round-2 finding that you dispute, and keep the pair (the finding, your reason) for the
handoff, as at gate 1 ("Drop a clip" below).

## 9. Drop a clip

Drop a clip when a rule of gate 1, of the render or of gate 2 says so. Do these steps:

1. Remove the `figure.clip` of the clip from the page.
2. Add `<id> — <reason>` to the `Dropped clips` row of the provenance. With more than one drop,
   the `<dd>` holds `<id> — <reason>; <id> — <reason>`.
3. Keep `clips/<id>/` on disk. Nothing links it.

The reason is the one line of the finding, or the text `render: FAIL <cause>`. A dropped clip is
not `Not covered`: the text of the section still explains the facet.

A clip that the plan unmarks before any render is a plan change, not a drop. An example is a
"motion not earned" finding. Remove its `figure.clip`, and write `clip: no` in its line of
`review/plan.md`. Do not add it to the `Dropped clips` row.

## 10. Finish and handoff

1. Copy the poster of each clip that stays: copy its `-end` still to `clips/<id>/poster.png`. For
   example, `cp clips/<id>/review/still-NN-<scene>-end.png clips/<id>/poster.png`. Do it after
   the last render of the clip.
2. Run `<skill-dir>/scripts/verify.sh index.html` in the output directory. A lesson has seven
   lines, one more than a page. All seven must show `ok`. The `bpmn` line can show `none` when the
   page has no BPMN diagram:

```
self-contained: ok
render 1440x900: ok
render 500x844: ok
citations: ok
prose: ok
media: ok
bpmn: ok
```

3. Do steps 2 to 4 of "Verify and export" in `page.md`: the snapshots, and the read of the tiles.
   Look for the faults of step 4, and for two more. A clip poster whose text is unreadable in the
   tile of 1440 px is a fault. A `Play all` button on a page with no clip is a fault.
4. Fix each fault. Run `verify.sh` and the snapshots again. Repeat until all are clean.

The `media` check counts each `src` and `poster` of a `video`, and each `href` that starts with
`clips/`, that does not name a file. The line is `media: FAIL <n> missing`, and a detail line
names each reference. A missing `poster.png` is the usual cause.

Then do the handoff of `SKILL.md` convention 6. Print the path of the output directory. Run
`open index.html` only when you run for the user directly. Never run `open` inside a subagent.
Then print the list of disputed findings, one line for each pair, or this line:

```
disputed findings: none
```

## 11. Output directory

The directory is `~/karpathy/out/YYYY-MM-DD-HHMMSS-lesson-<slug>/` (`SKILL.md` convention 5, with
the rung name `lesson`). The directory is the artifact of a lesson. `index.html` has no CDN and no
build step, and it opens from `file://`. Its only external references are relative paths inside
the directory.

| Path | Holds |
|---|---|
| `index.html` | The page. It has the meta `<meta name="explain-rung" content="lesson">`. |
| `page.png`, `narrow.png`, `narrow-tall.png`, `review/page-NN.png`, `review/narrow-*.png` | The renders and the tiles of the page rung. |
| `review/plan.md` | The section list and the clip choices. |
| `review/plants.md` | The planted faults of a live run that measures the gates. No reviewer reads it. A normal run has no such file. |
| `review/gate1-page-round-<k>.md` | The report of the page reviewer for round `<k>`, then your answer. |
| `review/gate1-<id>-round-<k>.md` | The report of the script reviewer for the clip `<id>`, round `<k>`, then your answer. |
| `review/gate1-<id>.script.json` | The copy of `script.json` that the last gate 1 dispatch of the clip gave to its reviewer. |
| `review/gate2-<id>-<part>-round-<k>.md` | The report of the render reviewer for the clip `<id>`, its part `<part>` and read `<k>`, then your answer. |
| `clips/<id>/` | One complete film output for each clip: `script.json` and `scene/`, which you write, and all that "Output directory" in `video.md` lists. It also holds `poster.png`. |

`<id>` is the id of the section that the clip belongs to. `snapshot.sh` deletes only
`review/<stem>-NN.png`, so the reports stay after the renders of the page.
