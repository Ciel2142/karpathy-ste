# Rung: brainrot
This file holds the rules of the brainrot rung. `SKILL.md` has the generic rules.

## 1. When a brainrot short

A brainrot short is a vertical narrated mp4 for a phone. The scene is in the top half of the
screen. A background plays in the bottom half. Large captions show the narration word by word on
the seam between the two halves.

The format is a style, not a content shape. Never choose it from the content. Use it only when
the user writes `--as brainrot`.

The grounding does not change. Each scene has cites. The transcript passes `verify.sh`. The
narration follows the STE profile, with no slang.

The brainrot rung is English only. If the user asks for another language, print the rung line.
Say that the brainrot rung is English only. Stop. Offer `page`.

A forced `--as brainrot` keeps the content, also when the content fits a page. A short has at
most 6 scenes. Keep the most important facets. Write each dropped facet in
`provenance.not_covered`.

## 2. What to read in `rungs/video.md`

Read these sections of `<skill-dir>/rungs/video.md` and follow them: "First-run costs",
"Narration fallback", "Render ratio", "Handoff" and "Pinned versions and environment". Where this
file and `video.md` differ, this file wins. The rest of `video.md` is for another format. Do not
read it.

| Section of `video.md` | Use |
|---|---|
| "First-run costs" | The set-up that the first run does by itself, its costs and its time. |
| "Narration fallback" | The `say` voice after a Kokoro fallback, and what to tell the user. |
| "Render ratio" | The advisory limit of the render time. |
| "Handoff" | The steps to hand the video to the user. |
| "Pinned versions and environment" | The pinned versions, the models, the workspace and the licence. |

## 3. Write the script

You write only one file, `script.json`. The `render.sh` command makes all other files from it.
Never change a made file by hand.

1. Copy `<skill-dir>/templates/brainrot-script.json` to `<output-dir>/script.json`.
2. Keep `"format": "brainrot"` as a top-level key of `script.json`. Without the key, the script is
   a film, and the `script` stage refuses each scene that has a component.
3. Replace every other value. The template is a short about `scripts/verify.sh`.
4. Get the provenance with the recipe in `<skill-dir>/rungs/sheet.md` section 4.

| Key | Value |
|---|---|
| `title` | The title of the short. |
| `subject.text`, `subject.kind` | The subject as the user typed it, and its kind: `file`, `directory`, `topic` or `conversation` (`SKILL.md` convention 2). |
| `provenance.root` | The ABSOLUTE path of the repo root, the `data-root` of convention 2. The template value is relative. `render.sh` stops if the value is not an absolute path of a directory. |
| `provenance.commit`, `.dirty`, `.date` | The commit hash or `none`; `dirty` or `no`; `YYYY-MM-DD`. |
| `provenance.source` | The repo root, `model knowledge` or the URLs. |
| `provenance.not_covered` | The dropped facets, or `none`. Always write this key. The transcript shows it as `Not covered`. |
| `scenes` | 3 to 6 scenes. Each scene has `id`, `component`, `props`, `narration` and `cites`. |

Rules for each scene:

- Give each scene a unique `id` that matches `[a-z0-9][a-z0-9-]*`. Show one motion in each scene.
- Write the narration in STE. Write 45 words or fewer. Keep each sentence at 20 words or fewer.
- The prose lint also reads each `title`, the subtitle, the bullets, the headings and lines of
  `before-after`, and `provenance.not_covered`. Write them in STE. The lint does not read the
  diagram labels, the code or the cites.
- Put a code name in backticks. The transcript shows it as code, and the narrator speaks it as
  plain text. Prefer words, such as "the check script", to a file name.
- Write the cites as `{ "path": …, "line": …, "snippet": … }`. The `path` is relative to
  `provenance.root`. The snippet has at most 12 words, copied verbatim from that line.
- `line` is necessary unless `path` starts with `http://` or `https://`.
- A `file` or a `directory` subject needs at least one cite in each scene.
- The transcript adds the word `untracked` by itself.
- Never write a password, a token or a key in the narration, the props or a snippet. Never
  show one in a code range.

Keep every text inside the limits of this table:

| Limit | brainrot |
|---|---|
| canvas | 1080×1920 |
| scenes | 3–6 |
| max scene length | 30 s |
| max total length | 90 s |
| narration words per scene | 45 |
| lead / tail frames | 6 / 12 |
| code range | 14 lines × 40 columns |
| `bullets-appear` text | 28 chars |
| `before-after` | stacked; 0–5 lines × 30 chars; heading 30 |
| diagram `label` / `sub` | 12 / 20 |
| `title` title / subtitle | 30 / 60 |
| caption chunk | 1–3 words, 20 chars |

A limit failure names the format. For example: `line 7 is 52 columns (max 40, brainrot)`.

- Length: at speed 1.2, the narrator speaks approximately 3.6 words each second. Each scene adds
  0.6 s of lead and tail. Six scenes of 45 words come near 80 s. These figures are an
  estimate. The `timeline` stage line shows the real length.
- Hook: scene 1 is a `title` scene. Its narration is one sentence of 12 words or fewer. The
  sentence says why the subject matters. The cue of the scene is the first words of that
  sentence. The `script` stage does not check the 12-word hook. It still checks the cue rule and
  each limit in the table.
- Before and after: the component stacks its two panels. The `before` panel is above the `after`
  panel.
- Captions: a caption shows 1 to 3 words of the narration at a time. A caption holds at most 20
  characters, so that it fits on one line. A code name that is longer than 20 characters shows
  alone, in smaller type. The word that the voice speaks is yellow. Backticks do not show in a
  caption.
- Code: the range has at most 14 lines, and each line has at most 40 columns. A tab counts as 4
  columns. This command prints the number of each line that is too long:
  `awk '{ gsub(/\t/, "    "); if (length($0) > 40) print NR }' <file>`. If no range of 14 short
  lines shows the point, show it in a diagram.

## 4. Components

Each prop is necessary, except `sub` and the edge `label`. An unknown or extra prop is an error.
Each `title` prop is the heading of the scene. Section 3 has the limits of the title, bullet, node
and panel texts and of the code range. Section 5 has the rule of each `cue`.

| Component | Props | Motion |
|---|---|---|
| `title` | `title`, `subtitle`, `cue` | The subtitle fades in at the cue. |
| `bullets-appear` | `title`; `bullets`: 2 to 4 items `{ text, cue }` | Each bullet slides in at its cue. Earlier bullets stay. |
| `diagram-with-highlight-walk` | `title`; `nodes`: 2 to 7 items `{ id, label, sub, cell }`; `edges`: `{ from, to, label }`, `label` max 10; `walk`: `{ node, cue }` | At each cue, the next node gets the highlight. A token moves to it along an edge. The label of the active edge hides while the token is on it. |
| `code-with-line-highlights` | `title`; `source`: `{ path, from, to }`; `highlights`: `{ from, to, cue }` | At each cue, a blue band marks the line range. Earlier bands become dim. |
| `before-after` | `title`; `before` and `after`: `{ heading, lines }`; `cue` | At the cue, the `after` panel comes in. The `before` panel becomes dim. The `before` heading is red and the `after` heading is blue: use the pair for worse and better. |

- Diagram: `cell` is one of `a1` to `c3`. The letter is the column (left to right), and the digit
  is the row (top to bottom). Each node has its own cell.
- Diagram: each walk step and each edge end names a node `id`. The token moves along the edge
  between the previous step and this step, in either direction. Without one, it takes the first
  edge into this step from an earlier step. With no such edge, no token shows.
- Code: the `script` stage reads the lines from `<provenance.root>/<path>`. The limits of the
  range are in the table of section 3. The leading indent counts, and the component shows it.
- Code: each highlight range is inside the `source` range.

## 5. The cue rule

A cue starts the motion of one item. Each cue is a string in the props.

- A cue is the first words of a sentence in the narration of the same scene.
- A cue starts and ends at word boundaries.
- A cue occurs one time only in the narration.
- The cues of a scene come in narration order.
- Two cue frames are 15 frames (0.5 s) apart or more. One sentence for each cue is the safe form.

The `script` stage checks the first four rules. The `timeline` stage checks the distance, because
the distance needs the `words.json` file of each scene. The cue frame is the exact start of its
sentence in that file.

Example narration: "The first check looks for remote links. The second check loads the page."

| Cue | Result |
|---|---|
| `The first check` | Correct. It starts sentence 1. |
| `The second check` | Correct. It starts sentence 2, after the first cue. |
| `the page` | Error: not at a sentence start. |
| `check` | Error: not unique, it occurs two times. |
| `The second check`, then `The first check` | Error: out of narration order. |

## 6. The background

The `render.sh` command chooses the background after the `timeline` stage. It downloads no
clip. The skill ships no background clip for a run. One clip of 1 s in `tests/fixtures/` is for
tests only.

- The clip folder is the path in `EXPLAIN_BRAINROT_BACKGROUNDS`. If the variable is not set, it
  is `<ws>/backgrounds/`. `<ws>` is the workspace, `~/karpathy/video-workspace` or the path in
  `EXPLAIN_VIDEO_WORKSPACE`. The user puts the clips in this folder.
- Only `*.mp4`, `*.mov` and `*.webm` files count, in any letter case. The picker ignores hidden
  files and sub-folders. A clip has no sound. The only audio is the narration.
- The picker takes the clips in random order. It uses the first clip that has a video stream and
  a positive length. For each clip that it cannot use, it prints an indented line,
  `background: SKIP <file> (<cause>)`.
- A clip that is as long as the short or longer starts at a random time and plays one time. A
  shorter clip starts at 0 and repeats. Set `EXPLAIN_BRAINROT_SEED` to an integer to fix the
  choice of the clip and its start.
- If the folder does not exist, or it is empty, or it has no good clip, the background is the
  generated runner loop. The runner is a block character that hops between three lanes. This case is not
  an error. The stage line is `background: ok generated`.
- To force the generated loop, set `EXPLAIN_BRAINROT_BACKGROUNDS` to an empty folder. Do not set
  it to `<ws>/runs`, or to a folder in it. Each render makes its own folder there and removes
  that folder when it stops. The picker refuses such a path with `background: FAIL`.
- A clip can pass the check and then fail to decode in the render. The run then prints
  `render: FAIL remotion render exit <n> (log <path>)`. Read the log. Remove that clip, or set
  `EXPLAIN_BRAINROT_BACKGROUNDS` to an empty folder. Run `render.sh` again.

## 7. Build and check

Run one command. Add `--engine say` only when the user asks in words for the macOS voice.

```
<skill-dir>/scripts/render.sh <output-dir>
```

The command prints one line for each stage, in this order. It stops at the first `FAIL` line.
A `FAIL` line names the cause. The output of the tool follows it, indented.

| Stage line | Meaning |
|---|---|
| `script: ok (<n> scenes)` | The script passed all checks with the brainrot limits, and the draft transcript passed `verify.sh`. |
| `workspace: ok <ws>` | The Remotion workspace is ready. |
| `narration (<engine>): ok[ (fallback: <cause>)]` | Each scene has a WAV file and a `words.json` file. The voice speaks at speed 1.2. |
| `timeline (<n> scenes, <s> s): ok` | `build/timeline.json` exists with the captions. Each scene is 30 s or less, and the short is 90 s or less. |
| `background: ok <name> @<start> s[ (loop)]` or `background: ok generated` | The background is in `build/timeline.json`. `(loop)` shows that the clip repeats. |
| `render (<s> s, <ratio> render-min/video-min)[ (limit 2.0)]: ok` | Remotion wrote `video.mp4`. The log is `build/render.log`. |
| `container: ok (<s> s)` | The mp4 is 1080×1920, with one H.264 video stream and one AAC audio stream. Its length is within 0.2 s of the timeline. |
| `sync: ok` | In each scene, the speech starts within 0.25 s of the lead end and stops more than 0.3 s before the scene end. |
| `stills (<n>): ok <review-dir>` | The review stills are in `review/`. |
| `transcript: ok` | The final `index.html` has the narrator, the Format row and the Background row, and passed `verify.sh`. Do not run `verify.sh` again. |

A `workspace` `FAIL` line names the step that failed. For `npm ci` and the browser step, it also
names the log. Read that log.

The first run takes minutes. Before it, read "First-run costs" in `video.md`.

If a line shows a fallback, read "Narration fallback" in `video.md`. If the render line adds
`(limit 2.0)`, read "Render ratio" in `video.md`.

## 8. Read the stills

Read each file in `review/` with the Read tool. Never read `video.mp4`.

- `still-NN-<scene>.png` shows scene NN at its start, after the fade-in.
- `still-NN-<scene>-<k>.png` shows cue k of the scene, 15 frames after the cue frame. The
  number k counts the cues in frame order.

Look for these faults:

1. A title that is absent or clipped.
2. Text that overlaps other text.
3. A motion state that does not agree with the narration, for example no bullet after its cue.
4. Text that gives a false picture of the subject.
5. A caption that is absent, or that does not match the narration at the cue. The caption of a
   cue still holds words of the cue sentence.
6. A caption that overlaps the content of the panel. The caption band is on the seam between the
   two halves.
7. A background that is black or frozen. Put the bottom halves of two stills from different
   scenes side by side. A black half is a fault. A clip that shows the same picture in both
   halves does not move, and that is a fault. A generated runner loop can look alike in two
   stills. Compare the halves in view, never by guess. If they look alike, read a third still
   before you decide.

Fix each fault in `script.json`. For a bad clip, remove it from the folder, or force the
generated loop (section 6). Run `render.sh` again in the same output directory. The run keeps the
WAV file of a scene when its narration text did not change. Repeat until all ten lines show `ok`
and the stills are clean.

## 9. Handoff

Follow "Handoff" in `video.md`, with two additions.

- Tell the user the speed of the narrator: speed 1.2 for Kokoro `af_heart`, or 210 words each
  minute for `say`.
- Tell the user the background, from the `background` stage line: a clip name or `generated`.

## 10. Output directory

The directory is `~/karpathy/out/YYYY-MM-DD-HHMMSS-brainrot-<slug>/` (`SKILL.md` convention 5,
with the rung name `brainrot`).

| Path | Contents |
|---|---|
| `script.json` | The script that you wrote. All other files come from it. |
| `index.html` | The transcript: the narration, the text on the screen and the cites of each scene. Its provenance block has a `Format` row (`brainrot (1080×1920)`) and a `Background` row. The page keeps `<meta name="explain-rung" content="video">`, so `verify.sh` treats it as a video transcript. |
| `video.mp4` | The narrated video. |
| `narration.md` | The narration, one heading for each scene. |
| `audio/` | For each scene, `<id>.<engine>.wav` and its sidecar `<id>.<engine>.txt`. Also `<id>.<engine>.words.json` for each scene, and `durations.json`. |
| `build/` | `timeline.json`, `render.log` and `rendered-audio.wav`, the audio track of the mp4. The timeline also holds `format`, `captions` and `background`. |
| `review/` | The stills `still-NN-<scene>.png` and `still-NN-<scene>-<k>.png`. |

## 11. Constants

- 30 fps. The scene panel is 1080×960, at the top. The background is 1080×960, at the bottom.
  The table in section 3 has the canvas size and the lead and tail frames.
- Kokoro `af_heart` speaks at speed 1.2. The `say` voice speaks at 210 words each minute.
- The generated runner loop has the fixed seed 7, so two renders show the same picture.

For the pinned versions, the models, the workspace and the licence, read "Pinned versions and
environment" in `video.md`.
