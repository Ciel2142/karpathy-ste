# Rung: brainrot
This file holds only what is different from the video rung. `SKILL.md` and `rungs/video.md` have
the rest.

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

Read these sections of `<skill-dir>/rungs/video.md` and follow them. Where this file and
`video.md` differ, this file wins.

| Section of `video.md` | Use |
|---|---|
| 2. Write the script | The keys, the rules for each scene, the components, the cue rule and the cites. Section 3 of this file replaces the limits. |
| 3. Build and check | The first-run costs, the narration fallback, the render ratio and the way to read the stills. Section 5 of this file adds the checks. |
| 4. Handoff | Section 6 of this file adds the background. |
| 5. Output directory | Section 7 of this file adds three items. |
| 6. Pinned versions and environment | The pinned versions, the models, the workspace and the licence. The voice speed (1.0) and the Constants bullet (1280x720, lead 15, tail 36) differ. Section 8 of this file gives the brainrot values. |

Skip section 1 of `video.md`. Section 1 of this file replaces it.

## 3. Write the script

Follow section 2 of `video.md`, with these changes.

1. Copy `<skill-dir>/templates/brainrot-script.json` to `<output-dir>/script.json`. The template
   is a short about `scripts/verify.sh`.
2. Keep `"format": "brainrot"` as a top-level key of `script.json`. Without the key, the script
   is an explainer and `render.sh` makes a 16:9 video.
3. Keep the narration of each scene at 45 words or fewer. Write 3 to 6 scenes.
4. Keep every text inside the limits of this table. The limits of the explainer are in the
   second column. They replace the limits that section 2 of `video.md` gives.

| Limit | explainer | brainrot |
|---|---|---|
| canvas | 1280×720 | 1080×1920 |
| scenes | 3–8 | 3–6 |
| max scene length | 60 s | 30 s |
| max total length | 150 s | 90 s |
| narration words per scene | 45 | 45 |
| lead / tail frames | 15 / 36 | 6 / 12 |
| code range | 14 lines × 72 columns | 14 lines × 40 columns |
| `bullets-appear` text | 36 chars | 28 chars |
| `before-after` | side by side; 0–10 lines × 36 chars; heading 36 | stacked; 0–5 lines × 30 chars; heading 30 |
| diagram `label` / `sub` | 14 / 24 | 12 / 20 |
| `title` title / subtitle | 50 / 80 | 30 / 60 |

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
- Cues: the cue rule of `video.md` applies. In a brainrot short, the cue frame is the exact
  start of its sentence, not an estimate.
- Captions: a caption shows 1 to 3 words of the narration at a time. The word that the voice
  speaks is yellow. Backticks do not show in a caption.
- Code: the range has at most 14 lines, and each line has at most 40 columns. A tab counts as 4
  columns. This command prints the number of each line that is too long:
  `awk '{ gsub(/\t/, "    "); if (length($0) > 40) print NR }' <file>`. If no range of 14 short
  lines shows the point, show it in a diagram.

## 4. The background

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
  it to `<ws>/app/public` or `<ws>/app/bg-stage`, or to a folder in them. The picker empties
  those folders, and it refuses such a path with `background: FAIL`.
- A clip can pass the check and then fail to decode in the render. The run then prints
  `render: FAIL remotion render exit <n> (log <path>)`. Read the log. Remove that clip, or set
  `EXPLAIN_BRAINROT_BACKGROUNDS` to an empty folder. Run `render.sh` again.

## 5. Build and check

Run one command, as in section 3 of `video.md`. Add `--engine say` only when the user asks in
words for the macOS voice.

```
<skill-dir>/scripts/render.sh <output-dir>
```

The command prints one line for each stage, in this order. It stops at the first `FAIL` line.

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

The narration fallback and the render ratio work as in section 3 of `video.md`.

Read the stills as in section 3 of `video.md`. Look for the faults in that list, and for these
three more faults:

1. A caption that is absent, or that does not match the narration at the cue. The caption of a
   cue still holds words of the cue sentence.
2. A caption that overlaps the content of the panel. The caption band is on the seam between the
   two halves.
3. A background that is black or frozen. Put the bottom halves of two stills from different
   scenes side by side. A black half is a fault. A clip that shows the same picture in both
   halves does not move, and that is a fault. A generated runner loop can look alike in two
   stills. Compare the halves in view, never by guess. If they look alike, read a third still
   before you decide.

Fix each fault in `script.json`. For a bad clip, remove it from the folder, or force the
generated loop (section 4). Run `render.sh` again in the same output directory. Repeat until all
ten lines show `ok` and the stills are clean.

## 6. Handoff

1. Print the path of the output directory.
2. Run `open video.mp4` only when you run for the user directly. Never run `open` inside a
   subagent (`SKILL.md` convention 6).
3. Tell the user the narrator: Kokoro `af_heart` at speed 1.2, `say`, or `say` after a fallback.
4. Tell the user the background, from the `background` stage line: a clip name or `generated`.

## 7. Output directory

The directory is `~/karpathy/out/YYYY-MM-DD-HHMMSS-brainrot-<slug>/` (`SKILL.md` convention 5,
with the rung name `brainrot`). Its contents are the contents in section 5 of `video.md`, with
these three additions.

| Path | Contents |
|---|---|
| `build/timeline.json` | Also holds `format`, `captions` and `background`. |
| `audio/` | Also holds `<id>.<engine>.words.json` for each scene. |
| `index.html` | The transcript. Its provenance block has a `Format` row (`brainrot (1080×1920)`) and a `Background` row. The page keeps `<meta name="explain-rung" content="video">`, so `verify.sh` treats it as a video transcript. |

## 8. Constants

- 30 fps at 1080×1920. The scene panel is 1080×960, at the top. The background is 1080×960, at
  the bottom.
- Each scene has a lead of 6 frames and a tail of 12 frames.
- Kokoro `af_heart` speaks at speed 1.2. The `say` voice speaks at 210 words each minute.
- The generated runner loop has the fixed seed 7, so two renders show the same picture.
