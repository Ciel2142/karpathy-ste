# Rung: video
This file holds only what is specific to the video rung. `SKILL.md` has the generic rules.

## 1. When a video

Choose a video for a temporal narrative where motion carries meaning: data that moves through a
pipeline, or a handshake between two parts. The reader watches the video from start to end and
does not search in it. For reference material, choose `sheet` or `page`.

A forced `--as video` keeps the content, also when the content fits a page. A video has no more
scenes than the scene limit in the table of section 3. Keep the most important facets. Write each
dropped facet in `provenance.not_covered`.

The video rung is English only. If the user asks for another language, print the rung line.
Say that the video rung is English only. Stop. Offer `page`.

## 2. The grammar of a film

A film is one picture that you make for the subject, and the voice walks through it. Obey these
rules:

- Keep one picture for the whole film. Objects stay and change. Never clear the stage between
  scenes.
- Change the picture in each scene while the voice speaks. A scene is one or two sentences, with
  one motion for each sentence.
- Decide the picture first. Then write the narration that fits it.
- Put only three types of text on the stage: a label, a source line in a code card, or a claim
  under test. A list of sentences is a fault.
- Give each colour one meaning. Yellow (`C.yellow`) is the subject, and blue (`C.blue`) is a
  chosen item. Green (`C.green`) is a pass, and red (`C.red`) is a fail.

## 3. Write the script

You write `script.json` and the files of `scene/` (section 4). The `render.sh` command makes all
other files from them. Never change a made file by hand.

1. Copy `<skill-dir>/templates/video-script.json` to `<output-dir>/script.json`.
2. Keep `"format": "film"`. A script without the key is also a film.
3. Replace every value. The template is the worked example, a film about how `/explain` checks
   an artifact.
4. Replace the root `.` with the absolute path of the repo root.
5. Get the provenance with the recipe in `<skill-dir>/rungs/sheet.md` section 4.

| Key | Value |
|---|---|
| `format` | `film`. Keep this key. |
| `title` | The film title. |
| `subject.text`, `subject.kind` | The subject as the user typed it, and its kind: `file`, `directory`, `topic` or `conversation` (`SKILL.md` convention 2). |
| `provenance.root` | The ABSOLUTE path of the repo root, the `data-root` of convention 2. The template value is `.`, a relative path. `render.sh` stops if the value is not an absolute path of a directory. |
| `provenance.commit`, `.dirty`, `.date` | The commit hash or `none`; `dirty` or `no`; `YYYY-MM-DD`. |
| `provenance.source` | The source that you read: the files or the repo root, `model knowledge`, or the URLs. |
| `provenance.not_covered` | The dropped facets, or `none`. Always write this key. The transcript shows it as `Not covered`. |
| `sources` | The ranges of files that a code card shows. For a film with no code card, leave out the key or write `[]`. |
| `scenes` | The scenes, in the order of the film. The table of limits below gives their number. |

A scene has only these keys:

| Scene key | Rule |
|---|---|
| `id` | Unique, and matches `[a-z0-9][a-z0-9-]*`. It names the audio file, the stills, the marks and the heading of the scene in the transcript. |
| `narration` | Not empty, and within the word limit of the table below. The run counts the words that white space separates. |
| `cites` | The cites of the scene. A `file` or a `directory` subject needs at least one cite in each scene. Only a `topic` or a `conversation` subject lets a scene have no cites. |
| `pause` | Optional. A JSON integer from 12 to 90: the frames of silence after the speech. Without the key, the pause is the default pause of the table below. |

A film scene has no `component`, no `props` and no cue. The `script` stage refuses a scene with a
`component` or a `props` key. The picture comes from `scene/`, and its timing comes from the
marks of section 4.

Rules for each scene:

- Write the narration in STE. Keep each sentence at 20 words or fewer. This limit is smaller than
  the limit of the STE profile, and it applies here.
- Write a number as the voice must say it, such as "minus 201". The stage can show `-201`.
- The prose lint reads only the narration and `provenance.not_covered`. Write them in STE. The
  lint never reads the labels of the scene, the code or the cites.
- Put a code name in backticks. The transcript shows it as code, and the narrator speaks it as
  plain text. Prefer words, such as "the check script", to a file name.
- Write the cites as `{ "path": …, "line": …, "snippet": … }`. The `path` is relative to
  `provenance.root`. The snippet has at most 12 words, copied verbatim from that line.
- `line` is necessary unless `path` starts with `http://` or `https://`.
- The transcript adds the word `untracked` by itself.
- Never write a password, a token or a key in the narration, the scene or a snippet. Never
  show one in a source range.

Declare in `sources` each range of a file that a code card shows. A code card can show no other
text.

- Write each entry as `{ "id": …, "path": …, "from": …, "to": … }`. All four keys are necessary.
- Give each entry a unique `id` that matches `[a-z0-9][a-z0-9-]*`. The scene gets the lines as
  `sources.<id>`.
- Write the `path` relative to `provenance.root`. The file must be under the root.
- `from` and `to` are line numbers of the file, from 1. The range is in the file, and it has no
  more lines than the source limit of the table below.
- The run replaces each tab with 4 spaces. A file with a NUL byte fails.

| Limit | film |
|---|---|
| canvas | 1280×720 |
| scenes | 3–30 |
| max scene length | 30 s |
| max total length | 150 s |
| narration words per scene | 45 |
| lead / default pause frames | 6 / 12 |
| source lines | 20 |
| smallest text | 14 px |

The `timeline` stage fails a scene or a film that is longer than its limit. Plan the length with
these approximate values:

- The narrator speaks approximately 2.8 words each second. The two live runs gave 2.7 and 3.0.
  Numbers and code names are slower than plain words.
- Each scene adds 0.6 s of lead and default pause. A longer `pause` adds its frames.
- Each sentence after the first sentence of a scene adds 0.15 s.
- The template has 8 scenes and 121 words. Its length is 49 s with Kokoro and 43 s with `say`.
- A safe total for the longest film is approximately 350 words. That film is approximately
  130 s.

The stage line of `timeline` shows the real length. To come near a length, do these steps:

1. Write the script for that length with the values above, and run `render.sh`.
2. Read the length in the stage line of `timeline`.
3. If the film is short, add narration, or add frames to the `pause` of a scene. One frame is
   1/30 s. A film of 150 s has approximately 380 to 410 words.
4. If the film is long, remove words.

## 4. Write the scene

The directory `scene/` holds the picture of the film. You write it in TypeScript and React.

1. Copy the directory `<skill-dir>/video/src/film/` to `<output-dir>/scene/`.
2. Change the copy into your picture. It is the worked example, the picture of the template.
   Delete each file of the example that your picture does not use, and add your own files.
3. Keep the timing in `Film.tsx`, as the example does. Let the other files draw.

The directory obeys these rules:

- `scene/` holds only `.ts` and `.tsx` files. A sub-directory, or a file of a different type,
  fails the `scene` stage. The check ignores each entry whose name starts with `.`, also a
  directory.
- `Film.tsx` is necessary, and it holds `export function Film(`.
- The run writes its own `script.gen.ts`, with the scene ids and the source ids of `script.json`.
  It ignores the copy in `scene/`, and it does not count it. Do not edit the copy. The copy
  holds the ids of the example, not your ids.

### The stage

The run owns the stage, and you own what is on it. The stage is one SVG of 1280×720 on the colour
`C.bg`, at 30 frames each second. It holds your `Film`. The voice of each scene starts at the
first mark of the scene.

- `Film.tsx` exports `function Film(props: Props): ReactElement`. `Props` comes from
  `./script.gen`.
- `props.at` gives the marks of the narration. `props.sources` holds each source of `script.json`
  by its id.
- The scene ids and the source ids are types. Thus `tsc` refuses an id that `script.json` does
  not have.
- `Film` returns SVG elements only. It reads the frame with `useCurrentFrame()`.
- Make the picture a function of the frame and the props only. Use no state and no effect.

### The kit

Import the kit with `import { … } from "../kit";`. These are all the names of the kit, as the kit
files declare them:

```ts
// palette.ts
export const C: Record<"bg" | "panel" | "text" | "muted" | "line" | "blue" | "green" | "yellow" | "red", string>;
export const MONO: string; // the font stack of Mono
export const SANS: string; // the font stack of Sans
export const STAGE: { readonly width: 1280; readonly height: 720; readonly fps: 30 };
export const MIN_TEXT: 14; // the smallest text, in px: the table of section 3
// motion.ts
export const p: (frame: number, start: number, len: number) => number;
export const lin: (frame: number, start: number, len: number) => number;
export const lerp: (a: number, b: number, t: number) => number;
export type Pt = { x: number; y: number };
export const mix: (a: Pt, b: Pt, t: number) => Pt;
export const mixColor: (a: string, b: string, t: number) => string;
// marks.ts
export type Where = { sentence: number } | { word: string; nth?: number };
export type At<S extends string> = {
  (scene: S, where?: Where): number;
  said(scene: S): number;
  end(scene: S): number;
};
// source.ts
declare const fromDisk: unique symbol; // not exported
export type Source = {
  readonly path: string;
  readonly from: number;
  readonly lines: readonly string[];
  readonly [fromDisk]: true;
};
// text.tsx
type TextProps = { // not exported
  x: number; y: number; size: number; text: string; fill?: string; opacity?: number;
  anchor?: "start" | "middle" | "end"; weight?: number;
};
export function Mono(props: TextProps): ReactElement | null;
export function Sans(props: TextProps): ReactElement | null;
// draw.tsx
export function Draw(props: { d: string; t: number; stroke: string; width?: number;
  opacity?: number }): ReactElement | null;
export function Mark(props: { kind: "check" | "cross"; x: number; y: number; t: number;
  scale?: number; opacity?: number }): ReactElement;
// mono.ts
export type Card = { x: number; y: number; width: number; size: number };
export type Band = { line: number; color: string; opacity: number };
export type Tint = { line: number; from: number; to: number; color: string };
export const colX: (card: Card, index: number) => number;
export const lineY: (card: Card, source: Source, line: number) => number;
// code.tsx
export function CodeCard(props: { card: Card; source: Source; bands?: Band[]; tints?: Tint[];
  opacity?: number }): ReactElement;
// index.ts
export type FilmProps<S extends string, R extends string> = { at: At<S>; sources: Record<R, Source> };
```

- `C` holds the nine colours of the film. `bg` is the ground of the stage, and `panel` is the
  ground of a card.
- `p(frame, start, len)` is 0 up to `start`, then an eased curve over `len` frames, then 1. `lin`
  is the same curve with no easing. With a `len` of 0 or less, each one is a step at `start`.
- `lerp` and `mix` do not clamp `t`. `mixColor` takes `#rrggbb` or `rgb(r, g, b)`, and it clamps
  `t` to the range from 0 to 1.
- `Mono` and `Sans` draw a text at the baseline `y`, in `size` px. The default fill is `C.text`.
  Each one draws nothing for an empty text or an opacity of 0 or less.
- `Draw` shows the first part `t` of the stroke `d`: 0 shows nothing, and 1 shows all of it. Give
  it one subpath, because a second `M` starts the dash again.
- `Mark` draws a green check or a red cross over `t`. At scale 1, it is approximately 16 px wide,
  with its centre at `x`, `y`.
- `CodeCard` draws a frame, the line numbers and the lines of a source of `props.sources`. `tsc`
  refuses a source that you write, and the kit throws an error for a copy of a source.
- `line` in `Band`, `Tint` and `lineY` is a line number of the file. A band or a tint on a line
  that the source does not hold throws an error.
- A band is a tinted bar behind one line. A tint draws the columns `from` (included) to `to`
  (excluded) of a line in a colour, in the same text element. The columns count code points, and
  the first column is 0. Mark words of a line with a tint.
- The card cuts a line, with no ellipsis, to the characters that fit `card.width`.
- The kit owns the inner geometry of the card. Get a position in the card only from `colX` and
  `lineY`. `colX(card, index)` is the x of column `index` of the code, from 0.
  `lineY(card, source, line)` is the baseline of a line.
- A row of the card is `1.6 * card.size` high, and the card has 16 px of padding on each side.
  A card of `n` lines is `32 + n * 1.6 * card.size` high. Put a label under a card at
  `card.y` plus that height, plus a gap.

### Marks

Time every motion from a mark. A mark is the frame where the voice starts a scene, a sentence or
a word. Each mark is a frame of the film.

- `at(id)` is the frame where the speech of scene `id` starts. It is equal to
  `at(id, { sentence: 1 })`.
- `at(id, { sentence: k })` is the start of sentence `k` of the scene.
- `at(id, { word: "w" })` is approximately where the voice says the word `w`. With `nth: n`, the
  mark is the time `n` that the scene says the word.
- `at.said(id)` is the frame where the speech of the scene ends.
- `at.end(id)` is the first frame after the scene, its pause included.
- `sentence` and `nth` count from 1. Without `nth`, the mark is the first time of the word.

Rules for the marks:

- A number in the scene code is a length in frames, never a position in time. Add it to a mark.
- The run measures the start of each sentence. A word mark is an estimate: the words of a
  sentence share its time in proportion to their length. A word that ends with `,`, `;` or `:`,
  and the last word of the sentence, get a little more time.
- Use a word mark for "approximately when the voice says the word". For a motion that needs an
  exact frame, use a sentence mark.
- End a motion that starts at a sentence mark before the middle of that sentence. The guard
  measures that frame, and the still of the sentence shows it. The middle is approximately 5
  frames for each word of the sentence. Thus, a motion of 24 frames is safe in a sentence of 6
  words or more.
- Text that types, and a line that draws, must be complete at that frame. A name that is half
  typed in a still reads as a different name.
- A motion that shows and then leaves, such as a light that moves across a row, must be there at
  that frame. Time it from a word mark near the middle of the sentence.
- A sentence ends at `.`, `?` or `!` before white space or the end of the narration. A full
  stop in backticks does not end a sentence.
- To find the word of a mark, the kit puts it and each word of the narration in lower case. It
  removes each character that is not a letter or a digit.
- The match is on the whole word: `self` does not match `self-contained`.
- The run makes the voice of each sentence alone, with 0.15 s of silence between two sentences.
  A scene lasts its lead, its speech and its pause.

For a bad mark, the kit throws an error with the message `MARK scene <id>: <cause>`. At a check
frame, the `guard` stage stops with its mark line of section 5. At another frame, the `render`
stage stops, and `build/render.log` holds the `MARK scene` line.

| Cause | Fault |
|---|---|
| `no such scene` | The scene id is not in `script.json`. `tsc` refuses most of these ids first. |
| `sentence <k> is not a positive integer` | `k` is not an integer of 1 or more. |
| `sentence <k> is past the last one (<n>)` | The scene has only `<n>` sentences. |
| `word "<w>" has no letter or digit` | The word holds no letter and no digit. |
| `nth <n> is not a positive integer` | `n` is not an integer of 1 or more. |
| `word "<w>" is not in the narration` | The narration of the scene does not say the word. |
| `nth <n> is past the last "<w>" (<count>)` | The scene says the word only `<count>` times. |
| `a mark is a sentence or a word, not both` | The object has `sentence` and also `word` or `nth`. `tsc` does not refuse this object. |

### Text on the stage

- `Mono` gives each character an advance of `0.6 * size`. With the default anchor `start`, the
  character at `index` of a `Mono` text is at `x + index * 0.6 * size`. The index counts code
  points.
- The film renders in Menlo, because the first two fonts of `MONO` are not in the renderer.
  Menlo keeps the grid within 0.05 px.
- A wide character, such as an emoji or a CJK character, keeps its width. The other gaps of the
  text get smaller, and the characters move off `colX` by up to approximately 14 px. Thus, keep
  a code card and a `Mono` text to characters of one column.
- A `Sans` text has no fixed width. Leave space around it.
- Draw each text at `MIN_TEXT` px or more on the canvas. The size on the canvas is the font size
  times the scale of each group around the text.
- `MIN_TEXT` is the limit of the guard, not a good size. In the two live runs, a reader could not
  read grey text of 13 to 15 px quickly. Draw a caption in a dim colour at 16 px or more.

### Imports and tokens

The `scene` stage checks each file of `scene/` by its text, before `tsc`. These rules keep the
picture to pinned code and to its props.

- Import only from `react`, `remotion`, `../kit`, `./script.gen`, and `./<Name>` for a file
  `<Name>.ts` or `<Name>.tsx` of `scene/`. The rule applies to each `import … from`, each
  `export … from` and each `import "<source>"`.
- From `remotion`, import only `useCurrentFrame`, `interpolate`, `Easing`, `spring` and
  `interpolateColors`. `Sequence`, `AbsoluteFill` and the media components render HTML or load
  files, and they do not belong on the stage.
- Import from `remotion` with one list in braces, such as
  `import { spring, useCurrentFrame } from "remotion";`. The check refuses each other form.
- In an import from `remotion`, the check refuses a default import, `* as`, and a comment in the
  braces. It also refuses an alias in quotes, or an alias with a character that is not ASCII.
- Write each import on its own line. The check refuses an import of `remotion` after another
  import on the same line.
- Never write these tokens: `require(`, `import(`, `fetch(`, `foreignObject`,
  `dangerouslySetInnerHTML`, `clipPath`, `href`, `http://`, `https://`, `@ts-nocheck`,
  `@ts-ignore`, `@ts-expect-error`, `as unknown` and `<any>`.
- Never write `<mask`, `<use`, `<image`, `as any` or `: any` before a character that is not a
  letter or a digit. The end of a line counts as such a character.
- The check finds `@ts-nocheck` in any case of its letters.
- A string that ends with the word `from` or `import` fails too. The check reads the text up to
  the next quote as a source. Change the last word of such a string.
- The check has no comment parser. A token or a `from "<x>"` in a comment counts.

Then `tsc` checks the types of the scene with the kit. The type check is strict, and an unused
local or an unused import fails `tsc`. Its lines name a file of your scene as `scene/<file>`, and
a kit file by its path in the run directory, such as `src/kit/marks.ts`.

### The guard

The `guard` stage renders the film at its check frames only: the middle frame of each sentence,
and the last frame of each scene. At each check frame, it measures each text that holds a
character other than white space and has an opacity of 0.1 or more. That opacity is the product
of the opacity of the text and of each group around it.

The guard finds three faults: a text off the canvas, a text under `MIN_TEXT`, and two texts on
each other. Section 5 gives their lines. No fault is exempt. Fix the picture with one of the three
honest fixes:

1. Mark words with a tint or a box, not with a second text on top of them.
2. Bring an object in with a fade, or from inside the canvas.
3. Finish a cross-fade before the next check frame.

The guard does not see the faults below. Do not rely on the guard for them. Find them in the
stills of section 6.

- A fault at a frame that is not a check frame.
- A fault of a thing that is not text, such as a shape over a label.
- A text of the colour of the ground, or behind an opaque shape. The guard measures it as visible,
  and it can only give a false fault.
- A text that `display: none` or `visibility: hidden` hides. The guard measures it as visible.
- A text that the scene adds after the frame shows, for example through a change of state in an
  effect. The guard does not measure it.
- A bad mark at a frame that is not a check frame. The `render` stage stops for it.

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
| `scene: ok (<n> files)` | The `.ts` and `.tsx` files of `scene/` obey the import and token rules, and `tsc` found no error. `<n>` counts these files, but not a `script.gen.ts` or a hidden file. This stage comes before the narration, so a fault in the scene costs no synthesis. |
| `narration (<engine>): ok[ (fallback: <cause>)]` | Each scene has a WAV file. `<engine>` is the narrator that the run used. The part in brackets shows only after a fallback. |
| `timeline (<n> scenes, <s> s): ok` | The run wrote `build/timeline.json`, with the marks of each scene and the check frames. Each scene and the film are within the limits of section 3. |
| `guard (<n> frames): ok` | The guard rendered the film at its `<n>` check frames only, into `build/guard.mp4`. At each frame, no text is off the canvas, too small, or on another text. The log is `build/guard.log`. This stage comes before the render, so a fault costs no full render. |
| `render (<s> s, <ratio> render-min/video-min)[ (limit 2.0)]: ok` | Remotion wrote `video.mp4`. The log is `build/render.log`. |
| `container: ok (<s> s)` | The mp4 has one H.264 video stream and one AAC audio stream. Its frame size is the canvas size of section 3. Its length is within 0.2 s of the timeline. |
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
| `guard: FAIL mark: scene <id>: <cause>` | At a check frame, the scene code asks the kit for a mark of scene `<id>`, and the kit refuses it. `<cause>` gives the reason, for example a scene that does not exist, a word that the narration does not say, a sentence after the last one, or a mark with both a sentence and a word. Fix the mark. |
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

## 6. Read the stills

Read each file in `review/` with the Read tool. Never read `video.mp4`. The stills are the frames
that the guard measured. `NN` is the place of the scene in the script, from `01`.

- `still-NN-<id>-s<k>.png` is the middle of sentence k of scene NN.
- `still-NN-<id>-end.png` is the last frame of scene NN.

A still in the middle of a sentence shows that moment of the scene. A label that waits for a
later word is not there yet, and that is not a fault. For example, the still
`still-04-gates-s2.png` of the worked example shows one label: each label waits for its spoken
word.

Look for these faults in each still:

1. Text that a shape clips or covers.
2. A picture that does not agree with the narration of its scene.
3. An `-end` still that is equal to the `-end` still of the scene before it. The scene changed
   nothing.
4. A picture that is a list of sentences.
5. Text that gives a false picture of the subject, such as a quoted line that the source does
   not hold.

For fault 2, do these checks. In the two live runs, the author found none of these faults, and
a second reader found each of them:

- For each sentence, find the object on the stage that shows it. A sentence with no object is a
  fault. Draw the object, or change the sentence.
- An object that leaves must change or move away. An object that is there in one still and gone
  in the next still, with no cause, is a fault.
- Mark the same type of thing in the same way in each scene. If four scenes make the examined
  text cyan, the fifth scene does too.
- A light that stays on after its scene, or comes back with no cause, is a fault.
- When the narration gives a range or a list, the stage shows the same items in the same order.

Fix each fault in `script.json` or in `scene/`. Then run `render.sh` again in the same output
directory. The run keeps the WAV file of a scene whose narration did not change. Repeat until all
eleven lines show `ok` and the stills are clean.

After a fix, read again each still of each scene that you changed. If an object that stays on
the stage moved or changed its size, read all the stills again.

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
| `scene/` | The picture that you wrote. The run never changes this directory. It ignores a `script.gen.ts` in it, and writes its own `script.gen.ts` in the run directory. |
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
