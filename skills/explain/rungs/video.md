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

1. Copy `<skill-dir>/templates/video-script.json` to `<output-dir>/script.json`.
2. Replace every value. The template is an example video about `scripts/verify.sh`.
3. Get the provenance with the recipe in `<skill-dir>/rungs/sheet.md` section 4.

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

## 5. Build and check

Run one command. Add `--engine say` only when the user asks in words for the macOS voice.

```
<skill-dir>/scripts/render.sh <output-dir>
```

The command prints one line for each stage, in this order. It stops at the first `FAIL` line.
A `FAIL` line names the cause. The output of the tool follows it, indented.

| Stage line | Meaning |
|---|---|
| `script: ok (<n> scenes)` | The script passed all checks, and the draft transcript passed `verify.sh`. This stage makes no audio. |
| `workspace: ok <ws>` | The Remotion workspace is ready, and the run has its own directory in `<ws>/runs`. |
| `scene: ok (<n> files)` | The `<n>` files of `scene/` obey the import and token rules, and `tsc` found no error. This stage comes before the narration, so a fault in the scene costs no synthesis. |
| `narration (<engine>): ok[ (fallback: <cause>)]` | Each scene has a WAV file. `<engine>` is the narrator that the run used. The part in brackets shows only after a fallback. |
| `timeline (<n> scenes, <s> s): ok` | The run wrote `build/timeline.json`, with the marks of each scene and the check frames. Each scene and the film are within the limits of section 3. |
| `guard (<n> frames): ok` | The guard rendered the film at its `<n>` check frames only, into `build/guard.mp4`. At each frame, no text is off the canvas, too small, or on another text. The log is `build/guard.log`. This stage comes before the render, so a fault costs no full render. |
| `render (<s> s, <ratio> render-min/video-min)[ (limit 2.0)]: ok` | Remotion wrote `video.mp4`. The log is `build/render.log`. |
| `container: ok (<s> s)` | The mp4 has one H.264 video stream and one AAC audio stream. Its length is within 0.2 s of the timeline. |
| `sync: ok` | In each scene, the speech starts within 0.25 s of the lead end and stops more than 0.3 s before the scene end. |
| `stills (<n>): ok <review-dir>` | The stills are in `review/`, one for each check frame. |
| `transcript: ok` | The final `index.html` has the narrator and passed `verify.sh`. Do not run `verify.sh` again. |

The narration speaks at speed 1.0. If a line shows `FAIL`, fix its cause and run `render.sh`
again in the same output directory. The run keeps the WAV file of a scene when its narration
did not change. When all eleven lines show `ok`, read the stills with section 6.

### The FAIL lines

A `FAIL` line stops the run with exit 1, and the stages after it do not run. Find the line
below, fix its cause, and run `render.sh` again. Never edit a file in `build/`: the next run
writes these files again. A `FAIL` line that this section does not list names its cause.

The `script` stage checks `script.json`. Most other `FAIL` lines of this stage name a key of
`script.json` and the rule that it breaks.

| Line | Cause and fix |
|---|---|
| `script: FAIL provenance.root must be an absolute path` | The root in the template is `.`, a relative path. Write the absolute path of the repo root. |
| `script: FAIL provenance.root must be an existing directory: <path>` | No directory exists at `<path>`. Write the path of the repo root. |
| `script: FAIL scene <id>: a film scene has no component or props` | The scene has a `component` or a `props` key. A film scene has `id`, `narration`, `cites` and an optional `pause`. Remove the two keys. |
| `script: FAIL scene <id>: pause <v> must be an integer from 12 to 90` | `pause` is the number of silent frames after the narration of the scene. Write an integer in this range, or remove the key. |
| `script: FAIL source <id>: <cause>` | An entry of `sources` breaks a rule, and `<cause>` names it. Each entry has the four keys `id`, `path`, `from` and `to`. The range is in the file and within the limit of section 3. |

The `workspace` stage sets up the workspace and makes the run directory. Another `FAIL` line of
this stage names the step that failed. For `npm ci` and the browser step, it also names the log.
Read that log.

| Line | Cause and fix |
|---|---|
| `workspace: FAIL cannot make a run directory in <ws>/runs` | The run cannot make its directory in `<ws>/runs`, or cannot copy the sources into it. Make sure that `<ws>/runs` is a directory that you can write to, and that the disk has free space. |

The `scene` stage checks the files of `scene/` by their text, and then type-checks them with
`tsc`. The check finds all causes. The first cause is in the stage line, and all causes follow
it, indented. Thus the first cause shows two times. Nothing goes into the run directory before
the check passes.

| Line | Cause and fix |
|---|---|
| `scene: FAIL no scene directory: <path>` | `<output-dir>/scene` does not exist, or it is not a directory. Copy the example of section 4 to it. |
| `scene: FAIL no Film.tsx` | The scene has no `Film.tsx`. Each scene has one. |
| `scene: FAIL <name> is a directory` | The scene has a sub-directory. Move its files into `scene/`, or remove it. The check ignores an entry whose name starts with `.`. |
| `scene: FAIL <name> is not a .ts or .tsx file` | The scene holds only `.ts` and `.tsx` files. Move the file out of `scene/`. |
| `scene: FAIL Film.tsx has no "export function Film("` | `Film.tsx` must hold this text, the export of the function `Film`. Keep that line of the example. |
| `scene: FAIL <file>:<line>: import from "<source>"` | The line imports from a source that section 4 does not let a scene use. `<source>` is the first 40 characters of the source. An import in a comment counts too. A string that ends with the word `from` or `import` also gives this line: `<source>` is then the text up to the next quote. |
| `scene: FAIL <file>:<line>: "<name>" from remotion` | The line brings in a name from `remotion` that section 4 does not list. For an import of a different form, for example a default import, a comment in the braces, or two imports on one line, `<name>` is the text of that import. |
| `scene: FAIL <file>:<line>: token "<token>"` | The line holds a token that section 4 refuses. A token in a comment counts too. The check finds `@ts-nocheck` in any case of its letters. |
| `scene: FAIL cannot copy the scene to <path>` | The run cannot copy the files of the scene into its run directory. Make sure that the disk has free space. |
| `scene: FAIL types: <cause>` | The run cannot write `script.gen.ts`, the scene and source names of the script. Its output follows. |
| `scene: FAIL tsc: <first error line>` | `tsc` found an error. The first 20 lines of its output follow, indented. These lines name a file of your scene as `scene/<file>`. An unused local is an error too. |

The `timeline` stage measures each scene and the film.

| Line | Cause and fix |
|---|---|
| `timeline: FAIL scene <id> is <s> s (max <max>, film)` | The scene is longer than the limit of section 3. Write fewer words in its narration, or give it a shorter `pause`. |
| `timeline: FAIL total <s> s (max <max>, film)` | The film is longer than the limit of section 3. Write fewer words, or drop a scene and write it in `provenance.not_covered`. |

The `guard` stage renders the film at its check frames only and measures each text that shows.
Its log is `build/guard.log`.

| Line | Cause and fix |
|---|---|
| `guard: FAIL frame <f> (scene <id>): <fault>[; <fault> ...]` | At frame `<f>` of scene `<id>`, a text breaks a rule of the guard. The line gives at most five faults, then the number of the others. Fix the picture with one of the three honest fixes of section 4. |
| `guard: FAIL mark: scene <id>: <cause>` | At a check frame, the scene code asks for a mark of scene `<id>` that the kit cannot find. `<cause>` names the mark, for example a word that the narration does not say, or a sentence after the last one. Fix the mark. |
| `guard: FAIL remotion render exit <n> (log <path>)` | The guard pass stopped for a different cause, for example no browser, an error in the bundle, or a clip that it cannot get. The last 40 lines of the log follow, indented. Read the log: the error line is near its top. |
| `guard: FAIL cannot read <out>/build/timeline.json` | The timeline is absent or not JSON, or it has no check frames. The guard pass does not start. Run `render.sh` again. |
| `guard: FAIL cannot copy <out>/<clip>` | The run cannot copy a narration clip into its run directory. The guard pass does not start. Make sure that the clip is in `audio/` and that the disk has free space. |

Each fault of the frame line is one of these. `<t>` is the first 24 characters of the text.

- `OFFCANVAS "<t>"`: the box of the text goes more than 1 px past an edge of the canvas.
- `SMALLTEXT <px> px "<t>"`: the size of the text on the canvas is less than the floor of
  section 3.
- `OVERLAP "<a>" | "<b>"`: the boxes of two texts overlap by more than 2 px on both axes.

The `render` stage renders all frames of the film into `video.mp4`.

| Line | Cause and fix |
|---|---|
| `render: FAIL remotion render exit <n> (log <path>)` | The render stopped. The last 40 lines of `build/render.log` follow, indented. Read the log: the error line is near its top. |
| `render: FAIL remotion render exit 1 (log <path>)` | If `build/render.log` also has a `MARK scene` line, the scene code asks for a bad mark at a frame that the guard did not check. Fix the mark as for the mark line of the guard. |

### First-run costs

On the first run, the `workspace` stage sets up the workspace by itself. Do not install
anything yourself. Before each costly step, the stage prints the cost, indented:

- `npm ci`: approximately 55 s and 503 MB.
- Chrome Headless Shell: 193 MB.
- The two Kokoro model files: 353 MB, only for the Kokoro engine.

The `narration` stage of the first Kokoro run also resolves the Python packages through `uv`,
in approximately 30 s and with no cost line. The first run takes 3 to 6 minutes. If your shell
tool has a shorter timeout, run `render.sh` in the background with its output in a log file.

### Narration fallback

If Kokoro cannot run, the narration changes to the macOS `say` voice. The run then prints
`narration: FALLBACK say (<cause>)`, indented. The stage line becomes
`narration (say): ok (fallback: <cause>)`. The `Narrator` row of the transcript then shows
`say (fallback: <cause>)`. Tell the user about the fallback and its cause. Without a fallback,
the row shows `kokoro (af_heart)` or `say`.

### Render ratio

The render ratio is advisory, with a limit of 2.0. The line adds `(limit 2.0)` when the ratio is
more than 2.0. The stage does not fail.

### A stopped run

A HUP, INT or TERM signal stops the run with exit 1 and no `FAIL` line. If TERM or HUP comes
during `tsc`, the guard pass or the render, the run waits until that tool ends. In a long
render, this can take minutes. Ctrl-C stops the tool at once. In each case, the run removes its
run directory. A later run removes a run directory that a killed run left, after one day.

## 7. Handoff, output directory and pinned versions

### Handoff

1. Print the path of the output directory.
2. Run `open video.mp4` only when you run for the user directly. Never run `open` inside a
   subagent (`SKILL.md` convention 6).
3. Tell the user the narrator: Kokoro `af_heart`, `say`, or `say` after a fallback.

### Output directory

| Path | Contents |
|---|---|
| `script.json` | The script that you wrote. |
| `scene/` | The picture that you wrote. The run ignores a `script.gen.ts` in it and writes its own. |
| `index.html` | The transcript: the narration and the cites of each scene, under a heading that is the scene id. |
| `video.mp4` | The narrated video. |
| `narration.md` | The narration, one heading for each scene. |
| `audio/` | For each scene, `<id>.<engine>.wav`, its sidecar `<id>.<engine>.txt` and `<id>.<engine>.words.json`. Also `durations.json`. |
| `build/` | `timeline.json`, `guard.log`, `guard.mp4`, `render.log` and `rendered-audio.wav`, the audio track of the mp4. |
| `review/` | The stills `still-NN-<id>-s<k>.png` and `still-NN-<id>-end.png`. |

### Pinned versions and environment

- Remotion `4.0.532`, React `19.2.3` and TypeScript `5.9.3`, pinned in `video/package.json` and
  `video/package-lock.json`. They ran on Node `25.9.0`. An LTS line of Node is a safe substitute.
- Kokoro runs through `uv run --python 3.12` with `kokoro-onnx==0.6.1`, `onnxruntime==1.30.0`,
  `soundfile==0.14.0`, `numpy==2.5.3` and `espeakng-loader==0.2.4`. The voice is `af_heart` at
  24 kHz. The `say` voice gives 22.05 kHz.
- The model files come from release `model-files-v1.1` of `thewh1teagle/kokoro-onnx`, at
  `https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1`. sha256:
  `kokoro-v1.0.onnx` (325 MB) `beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a`,
  `voices-v1.0.bin` (28 MB) `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d`.
- Workspace: `~/karpathy/video-workspace`, or the path in `EXPLAIN_VIDEO_WORKSPACE`. Its `app/`
  holds the installed packages and the two package files, `package.json` and
  `package-lock.json`. Its `runs/` holds one directory for each render that runs. The render
  removes its directory when it stops, so two renders can run at the same time. Its `models/`
  holds the Kokoro files. Never install a package globally. Never use `npx`.
- Licence: Remotion is free under the Remotion Free License for an individual. Check the licence
  again when the use moves to a for-profit organisation with more than 3 employees.
