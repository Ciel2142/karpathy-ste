# Rung: video
This file holds only what is specific to the video rung. `SKILL.md` has the generic rules.

## 1. When a video

Choose a video for a temporal narrative where motion carries meaning: data that moves through a
pipeline, or a handshake between two parts. The reader watches the video from start to end and
does not search in it. For reference material, choose `sheet` or `page`.

A forced `--as video` keeps the content, also when the content fits a page. A video has at most
8 scenes. Keep the most important facets. Write each dropped facet in `provenance.not_covered`.

The video rung is English only. If the user asks for another language, print the rung line.
Say that the video rung is English only. Stop. Offer `page`.

## 2. Write the script

You write only one file, `script.json`. The `render.sh` command makes all other files from it.
Never change a made file by hand.

1. Copy `~/.claude/skills/explain/templates/video-script.json` to `<output-dir>/script.json`.
2. Replace every value. The template is an example video about `scripts/verify.sh`.
3. Get the provenance with the recipe in `~/.claude/skills/explain/rungs/sheet.md` section 4.

| Key | Value |
|---|---|
| `title` | The video title. |
| `subject.text`, `subject.kind` | The subject as the user typed it, and its kind: `file`, `directory`, `topic` or `conversation` (`SKILL.md` convention 2). |
| `provenance.root` | The ABSOLUTE path of the repo root, the `data-root` of convention 2. The template value is relative. `render.sh` stops if the value is not an absolute path of a directory. |
| `provenance.commit`, `.dirty`, `.date` | The commit hash or `none`; `dirty` or `no`; `YYYY-MM-DD`. |
| `provenance.source` | The repo root, `model knowledge` or the URLs. |
| `provenance.not_covered` | The dropped facets, or `none`. Always write this key. The transcript shows it as `Not covered`. |
| `scenes` | 3 to 8 scenes. Each scene has `id`, `component`, `props`, `narration` and `cites`. |

Rules for each scene:

- Give each scene a unique `id` that matches `[a-z0-9][a-z0-9-]*`. Show one motion in each scene.
- Write the narration in STE. Write 45 words or fewer. Keep each sentence at 20 words or fewer.
- The prose lint also reads each `title`, the subtitle, the bullets, the headings and lines of
  `before-after`, and `provenance.not_covered`. Write them in STE. The lint does not read the
  diagram labels, the code or the cites.
- The `timeline` stage fails a scene longer than 60 s or a video longer than 150 s. The narrator
  speaks approximately 3 words each second, and each scene adds 1.7 s of lead and tail. Eight
  scenes of 45 words come near 150 s. With 7 or 8 scenes, write fewer words in each scene. A safe
  total is approximately 300 words.
- Put a code name in backticks. The transcript shows it as code, and the narrator speaks it as
  plain text. Prefer words, such as "the check script", to a file name.
- Write the cites as `{ "path": …, "line": …, "snippet": … }`. The `path` is relative to
  `provenance.root`. The snippet has at most 12 words, copied verbatim from that line.
- `line` is necessary unless `path` starts with `http://` or `https://`.
- A `file` or a `directory` subject needs at least one cite in each scene.
- The transcript adds the word `untracked` by itself.
- Never write a password, a token or a key in the narration, the props or a snippet. Never
  show one in a code range.

### Components

Each prop is necessary, except `sub` and the edge `label`. An unknown or extra prop is an error.
Each `title` prop is the heading of the scene.

| Component | Props and limits | Motion |
|---|---|---|
| `title` | `title` (max 50 chars), `subtitle` (max 80 chars), `cue` | The subtitle fades in at the cue. |
| `bullets-appear` | `title`; `bullets`: 2 to 4 items `{ text, cue }`, `text` max 36 chars | Each bullet slides in at its cue. Earlier bullets stay. |
| `diagram-with-highlight-walk` | `title`; `nodes`: 2 to 7 items `{ id, label, sub, cell }`, `label` max 14, `sub` max 24; `edges`: `{ from, to, label }`, `label` max 10; `walk`: `{ node, cue }` | At each cue, the next node gets the highlight. A token moves to it along an edge. The label of the active edge hides while the token is on it. |
| `code-with-line-highlights` | `title`; `source`: `{ path, from, to }`; `highlights`: `{ from, to, cue }` | At each cue, a blue band marks the line range. Earlier bands become dim. |
| `before-after` | `title`; `before` and `after`: `{ heading, lines }`, `heading` max 36, 0 to 10 lines of max 36 chars; `cue` | At the cue, the `after` column comes in. The `before` column becomes dim. The `before` heading is red and the `after` heading is blue: use the pair for worse and better. |

- Diagram: `cell` is one of `a1` to `c3`. The letter is the column (left to right), and the digit
  is the row (top to bottom). Each node has its own cell.
- Diagram: each walk step and each edge end names a node `id`. The token moves along the edge
  between the previous step and this step, in either direction. Without one, it takes the first
  edge into this step from an earlier step. With no such edge, no token shows.
- Code: the `script` stage reads the lines from `<provenance.root>/<path>`. The range has at most
  14 lines. Each line has at most 72 columns. The leading indent counts, and the component shows
  it. A tab counts as 4 columns. This command prints the number of each line that is too long:
  `awk '{ gsub(/\t/, "    "); if (length($0) > 72) print NR }' <file>`. If no range of 14 short
  lines shows the point, show it in a diagram.
- Code: each highlight range is inside the `source` range.

### The cue rule

A cue starts the motion of one item. Each cue is a string in the props.

- A cue is the first words of a sentence in the narration of the same scene.
- A cue starts and ends at word boundaries.
- A cue occurs one time only in the narration.
- The cues of a scene come in narration order.
- Two cue frames are 15 frames (0.5 s) apart or more. One sentence for each cue is the safe form.

The `script` stage checks the first four rules. The `timeline` stage checks the distance, because
the distance needs the real clip length. The cue frame is `15 + round(offset / length × clip
frames)`. Here `offset` is the character position of the cue, `length` is the character count of
the narration, and `clip frames` is `ceil(seconds × 30)` of the WAV file. The cue accuracy is
approximately 0.3 s. A test run measured this accuracy for cues that start a sentence, the only
form that the check accepts.

Example narration: "The first check looks for remote links. The second check loads the page."

| Cue | Result |
|---|---|
| `The first check` | Correct. It starts sentence 1. |
| `The second check` | Correct. It starts sentence 2, after the first cue. |
| `the page` | Error: not at a sentence start. |
| `check` | Error: not unique, it occurs two times. |
| `The second check`, then `The first check` | Error: out of narration order. |

## 3. Build and check

Run one command. Add `--engine say` only when the user asks in words for the macOS voice.

```
~/.claude/skills/explain/scripts/render.sh <output-dir>
```

The command prints one line for each stage, in this order. It stops at the first `FAIL` line.
A `FAIL` line names the cause. The output of the tool follows it, indented.

| Stage line | Meaning |
|---|---|
| `script: ok (<n> scenes)` | The script passed all checks, and the draft transcript passed `verify.sh`. This stage makes no audio. |
| `workspace: ok <ws>` | The Remotion workspace is ready. |
| `narration (<engine>): ok` | Each scene has a WAV file. `<engine>` is the narrator that the run used. |
| `timeline (<n> scenes, <s> s): ok` | `build/timeline.json` exists. Each scene is 60 s or less, and the video is 150 s or less. |
| `render (<s> s, <ratio> render-min/video-min): ok` | Remotion wrote `video.mp4`. The log is `build/render.log`. |
| `container: ok (<s> s)` | The mp4 has one H.264 video stream and one AAC audio stream. Its length is within 0.2 s of the timeline. |
| `sync: ok` | In each scene, the speech starts within 0.25 s of the lead end and stops more than 0.3 s before the scene end. |
| `stills (<n>): ok <review-dir>` | The review stills are in `review/`. |
| `transcript: ok` | The final `index.html` has the narrator and passed `verify.sh`. Do not run `verify.sh` again. |

On the first run, the `workspace` stage sets up the workspace by itself. Do not install
anything yourself. Before each costly step, the stage prints the cost, indented:

- `npm ci`: approximately 55 s and 503 MB.
- Chrome Headless Shell: 193 MB.
- The two Kokoro model files: 353 MB, only for the Kokoro engine.

The `narration` stage of the first Kokoro run also resolves the Python packages through `uv`,
in approximately 30 s and with no cost line. The first run takes 3 to 6 minutes. If your shell
tool has a shorter timeout, run `render.sh` in the background with its output in a log file.

If Kokoro cannot run, the narration changes to the macOS `say` voice. The run then prints
`narration: FALLBACK say (<cause>)`, indented. The stage line becomes
`narration (say): ok (fallback: <cause>)`. The `Narrator` row of the transcript then shows
`say (fallback: <cause>)`. Tell the user about the fallback and its cause. Without a fallback,
the row shows `kokoro (af_heart)` or `say`.

The render ratio is advisory, with a limit of 2.0. The line adds `(limit 2.0)` when the ratio is
more than 2.0. The stage does not fail.

Then read the stills:

1. Read each file in `review/` with the Read tool. Never read `video.mp4`.
2. `still-NN-<scene>.png` shows scene NN at its start, after the lead.
3. `still-NN-<scene>-<k>.png` shows cue k of the scene, 15 frames after the cue frame. The
   number k counts the cues in frame order.
4. Look for these faults. A title that is absent or clipped. Text that overlaps other text. A
   motion state that does not agree with the narration, for example no bullet after its cue.
   Text that gives a false picture of the subject.
5. Fix each fault in `script.json`. A `workspace` FAIL names its log. Run `render.sh` again in
   the same output directory. The run keeps the WAV file of a scene when its narration text did
   not change.
6. Repeat until all nine lines show `ok` and the stills are clean.

## 4. Handoff

1. Print the path of the output directory.
2. Run `open video.mp4` only when you run for the user directly. Never run `open` inside a
   subagent (`SKILL.md` convention 6).
3. Tell the user the narrator: Kokoro `af_heart`, `say`, or `say` after a fallback.

## 5. Output directory

| Path | Contents |
|---|---|
| `script.json` | The script that you wrote. All other files come from it. |
| `index.html` | The transcript: the narration, the text on the screen and the cites of each scene. |
| `video.mp4` | The narrated video. |
| `narration.md` | The narration, one heading for each scene. |
| `audio/` | For each scene, `<id>.<engine>.wav` and its sidecar `<id>.<engine>.txt`. Also `durations.json`. |
| `build/` | `timeline.json`, `render.log` and `rendered-audio.wav`, the audio track of the mp4. |
| `review/` | The stills `still-NN-<scene>.png` and `still-NN-<scene>-<k>.png`. |

## 6. Pinned versions and environment

- Remotion `4.0.532`, React `19.2.3` and TypeScript `5.9.3`, pinned in `video/package.json` and
  `video/package-lock.json`. They ran on Node `25.9.0`. An LTS line of Node is a safe substitute.
- Kokoro runs through `uv run --python 3.12` with `kokoro-onnx==0.6.1`, `onnxruntime==1.30.0`,
  `soundfile==0.14.0`, `numpy==2.5.3` and `espeakng-loader==0.2.4`. The voice is `af_heart` at
  speed 1.0 and 24 kHz. The `say` voice gives 22.05 kHz.
- The model files come from release `model-files-v1.1` of `thewh1teagle/kokoro-onnx`, at
  `https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1`. sha256:
  `kokoro-v1.0.onnx` (325 MB) `beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a`,
  `voices-v1.0.bin` (28 MB) `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d`.
- Workspace: `~/karpathy/video-workspace`, or the path in `EXPLAIN_VIDEO_WORKSPACE`. It holds
  `app/` (the sources and `node_modules`) and `models/`. Never install a package globally. Never
  use `npx`.
- Constants: 30 fps at 1280x720. Each scene has a lead of 15 frames and a tail of 36 frames.
- Licence: Remotion is free under the Remotion Free License for an individual. Check the licence
  again when the use moves to a for-profit organisation with more than 3 employees.
