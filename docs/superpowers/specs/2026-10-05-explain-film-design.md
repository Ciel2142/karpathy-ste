# Explain `film` format: a bespoke picture for the video rung — design

Date: 2026-10-05
Status: approved by the user (2026-10-05), after section-by-section approval and three cold
reviews (consistency, gates, ambiguity)
Base: `feat/explain-brainrot`. Branch `feat/explain-film` is cut from it, as the lesson and
Russian features are, and follows it to `main` when brainrot merges. The facts about the
pipeline below were read at `99e469a` and checked again at `86e71d8` (2026-10-05). There the
code tasks of wave `brainrot-live-run` are in (the format rows now live in
`skills/explain/video/formats.json`); what remains of that wave is measurement, the live run,
the fold-back of tuned values and wording, and the user's acceptance. The plan re-locates each
reference at the tip it starts from.

## 1. Purpose

The video rung builds a video from five fixed scene components. In the 24 scenes made so far,
16 are text on a slide (a title, a bullet list, a before/after list). A bullets video is worse
than the page of the same content, and it fails the rung's own rule: a video is for content
"where motion carries meaning".

A spike (2026-10-05, `spike-freeform/`, throwaway) remade 38 s of the repo explainer as one
continuous picture written for the subject: a prompt, a ladder, a cite check and a row of
gates, with objects that stay on screen and transform. The user judged it far better than the
120 s baseline.

What the spike showed: a model-written picture renders on the pinned Remotion stack (one fix
round, 14.3 s for 38.2 s of video), a small kit keeps the scene code tractable, and one audio
clip for each sentence gives clean sync. What it did not run, and what is therefore design and
not evidence: sentence-mode narration with word times, marks by sentence and word, declared
sources, the scene copy with its import check and generated names, the guard, the code card,
and the lead and pause values of section 6.

This design makes the bespoke picture the video rung. The author writes the words as data and
the picture as code against a small kit.

What stays as it is: every scene carries cites, the transcript passes `verify.sh` with its cite
check and prose lint, the narration follows the STE profile, and source lines on screen are
read from disk. What gets weaker is stated in section 3.

Success means:

- a fresh agent that reads only the rung file makes a film of a real code subject within two
  fix rounds (section 9.3 defines the round);
- the checks still catch a wrong cite, and catch text that is off the canvas, too small or
  overlapping at the checked frames without a person looking;
- `--as brainrot` renders as it does on the base, with its ten stage lines.

## 2. Decisions

| # | Decision | Choice |
|---|---|---|
| D1 | Where the bespoke video lives (user) | It replaces the video rung. `--as video` builds a film; in the end state there is no parallel format |
| D2 | Brainrot's scenes (user) | Brainrot merges as built and keeps the five components. They leave the video rung and stay only as brainrot's scene set |
| D3 | Length (user) | The 150 s limit stays. The long live run measures what length is realistic and the limits are folded back from it |
| D4 | Order (user) | Film is built before the lesson and Russian work, on top of the brainrot branch; their specs are then amended to target film |
| D5 | Contract | Words in data (`script.json`), picture in code (`scene/`). Rejected: everything in code (narration and cites become uncheckable); an animation language in JSON (a language to invent, and it tends back to slides) |
| D6 | Guard exemptions | None. A text that fails the guard is fixed, not exempted. An exemption is considered only if the live runs show a fault that has no honest fix |
| D7 | Order inside the feature | Film is added beside the explainer first, so the branch stays green; the default flips and the explainer goes in the removal wave |
| D8 | Renders at the same time (user) | Each render gets its own app directory in the workspace and shares only the installed packages and the models. Rejected: a lock that makes a second render wait; leaving it at "one at a time" |

## 3. Scope

In scope:

- A `film` format, added beside `explainer` and then replacing it; in the end state it is the
  format of a script without a `format` key.
- The film script contract: scenes without components, `pause`, `sources`.
- The scene directory and a `scene` stage (static check, generated names, type check).
- A kit under `skills/explain/video/src/kit/`, and one worked example film that is also the
  template.
- Marks: a frame for each scene and sentence (measured) and for each word (estimated).
- A `guard` stage that measures text layout in the browser at the frames of the stills.
- Film stills, the film transcript body, `rungs/video.md` rewritten, `rungs/brainrot.md` made
  complete for what it alone now uses.
- A run directory for every render, film and brainrot, so that renders can run at the same
  time (section 7.6).
- Removal of the explainer format, its layout, its regression harness and scene-mode
  narration, with the tests that brainrot needs ported, not deleted.
- Tests, planted-fault cases, two live runs with fold-back.

Out of scope:

- Bespoke scenes for brainrot (D2). A later decision.
- The amendments to the lesson and Russian specs (section 11). They follow this feature.
- A second voice, music, sound effects, or a language other than English.
- manim. The spike showed that the existing Remotion stack is sufficient.

Weaker than the base, and accepted:

- The transcript of a film does not list on-screen text. On the base every on-screen string
  came from the script, so the transcript showed it and the prose lint read titles and
  bullets. A film's labels are typed in scene code and no stage reads them.
- Only the code card shows text that is proven to come from disk (section 5.1). A label or a
  quoted phrase typed by the author is as unchecked as a diagram label is today.
- No stage checks that the picture means what the narration says, or that the film follows
  the grammar of section 8.1. That stays with the stills review, which the author does and a
  second agent repeats in the live run (section 9.3).
- The secrets rule stays an instruction, as today.

## 4. Interface

### 4.1 Invocation and output

`/explain <subject> --as video` is unchanged, and so is the router's rule for choosing a video.
The output directory is `out/YYYY-MM-DD-HHMMSS-video-<slug>/` as today, plus `scene/` (the
picture, written by the author).

### 4.2 `script.json`

Top-level keys: `title`, `subject`, `provenance` (unchanged, `not_covered` included), `format`
(optional), `sources` (optional), `scenes`.

End state: `format` is `film` or `brainrot`; a script without the key is a film; any other
value fails with `format must be film or brainrot`, and the rest of that script is validated
as a film. Until the removal wave (D7) the explainer stays the default and a film script
carries `"format": "film"`.

A film scene is one stretch of narration and the pause after it. It is not a picture: the
picture is continuous and does not cut between scenes. A film has 3 to 30 scenes.

| Scene key | Rule |
|---|---|
| `id` | As today: unique, matches `[a-z0-9][a-z0-9-]*`. It names the audio file, the stills, the marks and the transcript heading |
| `narration` | Not empty, at most 45 words (counted as the validator counts today: split on white space). Sentence length is the prose lint's rule, not a new one |
| `cites` | As today (`checkCites`): a `file` or `directory` subject needs at least one in each scene |
| `pause` | Optional. A JSON integer from 12 to 90: the frames of silence after the speech. Absent means 12. A string, a fraction or a value out of range fails |

A film scene with a `component` or a `props` key fails with `a film scene has no component or
props`; this is how a script in the old format is refused. Brainrot validation does not change;
`pause` and `sources` are film keys.

`sources` declares the file text that the code card may show. Each entry is
`{ "id", "path", "from", "to" }`, all required. `id` follows the scene id pattern and is
unique. `path` is relative to `provenance.root`; `--check` refuses a path outside the root with
`outsideRoot`, as `checkCode` does. That guard is lexical, and build mode reads without it:
open issues kp-k5p and kp-m3c record both gaps, and this design inherits them. `from` to `to`
is a range of at most 20 lines that exists in the file. A file with a NUL byte fails. Absent
and `[]` mean the same. Each broken rule is one `FAIL source <id>: <cause>` line.

A film has no cues. Timing comes from marks (section 6).

### 4.3 The scene directory

`<output-dir>/scene/` holds the picture. The author starts from a copy of
`<skill-dir>/video/src/film/` (the worked example, section 5.3).

- Files named `*.ts` or `*.tsx` are the scene. A sub-directory, or any other file that is not
  hidden, fails the `scene` stage. Hidden files (`.DS_Store`) are ignored and not copied.
- `Film.tsx` is required and holds `export function Film(`.
- `script.gen.ts` is the pipeline's (section 7.2). A copy in `scene/` is ignored, overwritten
  and not counted.

## 5. The picture

### 5.1 Stage

The pipeline owns the stage and the author owns what is on it. `FilmStage` (pipeline code)
renders, in this order: one `<svg viewBox="0 0 1280 720">` that holds the author's `Film`,
then the audio clip of each scene. `Film` returns SVG elements only, and reads the frame with
`useCurrentFrame()`. 30 fps at 1280x720.

```ts
declare const fromDisk: unique symbol;          // not exported from the kit
export type Source = { readonly path: string; readonly from: number;
                       readonly lines: readonly string[]; readonly [fromDisk]: true };
export type FilmProps<S extends string, R extends string> = {
  at: At<S>;
  sources: Record<R, Source>;
};
export function Film(props: Props): ReactElement;   // Props comes from ./script.gen
```

`sources[id].lines` are the declared lines read from disk at build time, with each tab
replaced by 4 spaces. Only `FilmStage` can make a `Source`, so the code card can show nothing
else; the casts that would forge one are refused in section 7.2.

From `remotion` a scene may import only `useCurrentFrame`, `interpolate`, `Easing`, `spring`
and `interpolateColors`. `Sequence`, `AbsoluteFill` and the media components render HTML or
load files, and neither belongs inside the stage.

### 5.2 Kit

`skills/explain/video/src/kit/` is the only thing a scene imports besides `react`, the five
names of `remotion` and its own files. It starts from the spike's kit and is written again
under test. `motion.ts`, `marks.ts` and `guard.ts` import nothing, so Node runs them in tests
as it runs `box.ts`.

```ts
// palette.ts
export const C: Record<"bg"|"panel"|"text"|"muted"|"line"|"blue"|"green"|"yellow"|"red", string>;
export const MONO: string, SANS: string;        // system font stacks, no web font
export const STAGE: { width: 1280; height: 720; fps: 30 };
export const MIN_TEXT: 14;                      // the guard reads STAGE and MIN_TEXT

// motion.ts
export const p:   (frame: number, start: number, len: number) => number;  // 0, then cubic in-out, then 1
export const lin: (frame: number, start: number, len: number) => number;  // the same, linear
export const lerp: (a: number, b: number, t: number) => number;
export type Pt = { x: number; y: number };
export const mix: (a: Pt, b: Pt, t: number) => Pt;
export const mixColor: (a: string, b: string, t: number) => string;       // "#rrggbb" or "rgb(r, g, b)"

// text.tsx, draw.tsx
type TextProps = { x: number; y: number; size: number; text: string; fill?: string;
                   opacity?: number; anchor?: "start"|"middle"|"end"; weight?: number };
export function Mono(props: TextProps): ReactElement | null;
export function Sans(props: TextProps): ReactElement | null;
export function Draw(props: { d: string; t: number; stroke: string; width?: number;
                              opacity?: number }): ReactElement | null;
export function Mark(props: { kind: "check"|"cross"; x: number; y: number; t: number;
                              scale?: number; opacity?: number }): ReactElement;

// code.tsx
export type Card = { x: number; y: number; width: number; size: number };
export type Band = { line: number; color: string; opacity: number };
export type Tint = { line: number; from: number; to: number; color: string };
export const colX:  (card: Card, index: number) => number;
export const lineY: (card: Card, source: Source, line: number) => number;
export function CodeCard(props: { card: Card; source: Source; bands?: Band[];
                                  tints?: Tint[]; opacity?: number }): ReactElement;
```

- `p` and `lin` with `len` of 0 or less are a step at `start`.
- `Mono` forces the advance to `0.6 * size` for each code point, so `x + index * 0.6 * size` is
  the position of a character. A character that the font draws wider than one column is drawn
  squeezed; that case is not handled.
- `Draw` shows the first `t` of a stroke (0 nothing, 1 all of it).
- `CodeCard` draws a frame, the line numbers and the lines of a source. `line` in `Band`,
  `Tint` and `lineY` is a line number of the file. A band is a tinted bar behind one line. A
  tint draws characters `from` (included) to `to` (excluded) of a line in a colour, inside the
  same text element: this is how a scene marks words of a line without a second text on top.
  A line is cut, with no ellipsis, to the characters that fit `card.width`. The card's inner
  geometry (gutter, padding, line height) is the kit's; a scene reaches it only through `colX`
  and `lineY`.

The film palette is its own. `theme.ts` and the "change all four" note stay as they are for
brainrot and the HTML templates; the transcript page keeps the shared light palette.

### 5.3 Worked example

`skills/explain/video/src/film/` holds one complete film of about 40 s: how `/explain` turns a
subject into a checked artifact (the subject of the spike, written again, not copied). It has
three jobs: the author's starting copy, the film that the app holds when no other film is
being built (a brainrot render), and the fixture of the end-to-end test.

- Its script is `templates/film-script.json` until the removal wave, then
  `templates/video-script.json`. The old template stays as a brainrot-format test fixture where
  a test needs a script with every component.
- Its cites and sources name only files that no wave of this feature edits
  (`skills/ste/SKILL.md`, `skills/explain/scripts/verify.sh`, `skills/explain/scripts/cite_check.py`).
- Its `script.gen.ts` is checked in. Two tests that always run keep the example true: one
  generates the file again and compares, one builds the transcript of the template and runs
  the cite check on it.

## 6. Marks

Film narration uses the sentence mode that brainrot already has: each sentence is synthesised
alone, the clips are joined with 0.15 s between them, and `<id>.<engine>.words.json` gives the
times of every sentence and word. A sentence start is measured. A word time is an estimate:
the words of a sentence share its span in proportion to their length. Film speaks at speed 1.0.

A scene lasts `leadFrames + audioFrames + pause`, with `leadFrames` 6. In the timeline each
film scene carries `sentences` (one frame for each sentence start; the first is `leadFrames`)
and `words` (`{ text, from, to }`), in frames from the scene start: the frame formula of the
captions.

```ts
type Where = { sentence: number } | { word: string; nth?: number };
export type At<S extends string> = {
  (scene: S, where?: Where): number;   // absolute frame
  said(scene: S): number;              // the frame where the speech of the scene ends
  end(scene: S): number;               // the first frame after the scene, pause included
};
```

- `at(id)` is the frame where the speech starts, and equals `at(id, { sentence: 1 })`.
- `sentence` and `nth` count from 1; `nth` is 1 when absent.
- A word matches a narration token when the two are equal after lowercasing and removing every
  character that is not a letter or a digit. The match is on the whole token: `self` does not
  match `self-contained`.
- Each of these throws an error whose message starts with `MARK scene <id>: `: a scene that is
  not in the script, a `sentence` or `nth` that is not a positive integer or is past the last
  one, a word with no letter or digit, a word that is not in the scene.

The rung file tells the author to time every motion from a mark, and that a word mark is good
for "about when the word is said".

## 7. Pipeline

`render.sh <output-dir>` stays the one command. A film run prints eleven stage lines (a brainrot
run keeps its ten). Each stage fails with exit 1, as today.

```
script: ok (<n> scenes)
workspace: ok <ws>
scene: ok (<n> files)
narration (<engine>): ok[ (fallback: <cause>)]
timeline (<n> scenes, <s> s): ok
guard (<n> frames): ok
render (<s> s, <ratio> render-min/video-min)[ (limit 2.0)]: ok
container: ok (<s> s)
sync: ok
stills (<n>): ok <review-dir>
transcript: ok
```

Once the `script` stage passes, a film run removes `video.mp4`, the stills and `build/guard.mp4`
of an earlier run, as the base does for the first two.

### 7.1 `script`, `narration`, `timeline`

- The format table (`video/formats.json`, read by `build-timeline.mjs`) gets a `film` row: 1280x720, 3 to 30 scenes, a scene of at
  most 30 s, a film of at most 150 s, 45 narration words, lead 6, default pause 12, 20 source
  lines, `wordTimed: true`, and no component limits. These are starting values.
- `--check` validates a film by section 4.2. The component shapes and the cue rules stay for
  brainrot.
- Build mode writes, for a film: `format`, the canvas and budgets, `engine`, `sources`
  (`{ <id>: { path, from, lines } }`), `checkFrames` (section 7.3) and the scenes of section 6.
  A film scene has no `component`, `props` or `cueFrames`.
- `narrate.py` gets `film` in its format table, in sentence mode.
- `check_budgets.py` and `verify_sync.py` read their numbers from the timeline and keep their
  rules. The 12-frame minimum pause leaves 0.4 s after the speech, against the 0.3 s that
  `verify_sync.py` asks for; the tail margin of a Kokoro clip was never measured (kp-c04), so
  the first film render checks it. Measured in wave film-render: `sync: ok` on the default
  pause, and the smallest gap between the end of the speech and the end of a scene was 0.70 s.
  The two live runs (34 scenes with Kokoro) also passed `sync` on the default pause.
- Limit messages name the format (`, film`, `, brainrot`). The untagged case belongs to the
  explainer and goes with it: `format_tag` and `tagOf` then tag every format.

### 7.2 `scene` (new)

It runs after `workspace` and before `narration`, so a type error costs no synthesis. Its
goals are three: a scene depends only on pinned, declared code; the picture takes no input
besides its props; and a passing type check means something.

1. `video/check_scene.py <output-dir>/scene` checks the directory statically:
   - the rules of section 4.3;
   - every `import ... from` and `export ... from` names `react`, `remotion` with only the
     five names of section 5.1, `../kit`, `./script.gen`, or `./<Name>` for a file of the
     directory;
   - none of these tokens appears. There is no comment parser: a token in a comment counts.
     `require(`, `import(`, `fetch(`, `foreignObject`, `dangerouslySetInnerHTML`, `clipPath`,
     `href`, `http://`, `https://`, `@ts-nocheck`, `@ts-ignore`, `@ts-expect-error`,
     `as unknown`, `<any>`; the tags `<mask`, `<use` and `<image`, and `as any` and `: any`,
     each matched only when the next character is not a letter or a digit.
2. The stage replaces `src/film/` of the run directory (section 7.6) with the scene files and
   writes `script.gen.ts` there with `build-timeline.mjs --types <script.json> <out.ts>`:

   ```ts
   import type { FilmProps } from "../kit";
   export type SceneId = "type" | "forms";   // every scene id of the script
   export type SourceId = "skill";           // every source id; never when there are none
   export type Props = FilmProps<SceneId, SourceId>;
   ```
3. `tsc` runs in the run directory. The app's `tsconfig.json` is strict and has `noUnusedLocals`.

| Line | When |
|---|---|
| `scene: FAIL no scene directory: <path>` | `scene/` is absent |
| `scene: FAIL <cause>` | A directory rule: `no Film.tsx`, `<name> is a directory`, `<name> is not a .ts or .tsx file`, `Film.tsx has no "export function Film("` |
| `scene: FAIL <file>:<line>: <cause>` | An import or a token: `import from "<source>"`, `"<name>" from remotion`, `token "<token>"` |
| `scene: FAIL cannot copy the scene to <path>` | The copy failed |
| `scene: FAIL types: <cause>` | `--types` failed |
| `scene: FAIL tsc: <first error line>` | `tsc` exited non-zero. The first 20 lines of its output follow, indented, with `src/film/` written as `scene/` |

The first cause is the stage line; the other causes of `check_scene.py` follow it, indented.
The scene goes only into the run directory, so a film leaves nothing in the shared workspace.

### 7.3 `guard` (new)

The five components kept text inside its box with length limits in the validator. A film has no
such limits, so the layout is measured.

`checkFrames`, written by the timeline stage, lists the frames that the guard measures and the
`stills` stage cuts: for each scene, the middle frame of each sentence and the last frame of
the scene. The author reads exactly the frames that the guard measured.

The stage renders the composition `Film` itself, only at those frames:

```
remotion render Film <out>/build/guard.mp4 --frames=<f1-f1,f2-f2,...> --concurrency=1 --muted
                --props <out>/build/timeline.json
```

Each frame is a range of one frame. With the pinned Remotion 4.0.532, a list of bare frames
(`--frames=3,7,12`) makes an image sequence, and the render to an mp4 fails (found in wave
film-guard). The render also needs the narration clips: Remotion reads the audio of each frame
with `--muted` too, so the stage copies the clips first.

`FilmStage` measures in a layout effect whenever the current frame is in `checkFrames`, so the
measured tree is the tree that ships. With one tab and the frames in order, the first frame
with a fault is the same in every run. It measures every `<text>` of the stage whose text is
not only white space and whose effective opacity is 0.1 or more: the product of the computed
`opacity` of the element and of each ancestor up to the stage. The box is
`getBoundingClientRect()`.

| Fault | Rule |
|---|---|
| `OFFCANVAS "<text>"` | The box passes an edge of the canvas by more than 1 px |
| `SMALLTEXT <px> px "<text>"` | The smallest computed `font-size` of the element and its `<tspan>` children, times `hypot(c, d)` of its screen matrix, is below `MIN_TEXT`. `<px>` has one decimal |
| `OVERLAP "<a>" \| "<b>"` | The boxes of two measured texts overlap by more than 2 px on both axes |

`<text>` in a message is the content with white space collapsed and trimmed, cut to 24
characters. A frame with a fault ends the pass through `cancelRender` with one message: its
faults in document order, at most five, then `(+<n> more)`.

| Line | When |
|---|---|
| `guard: FAIL frame <f> (scene <id>): <fault>[; <fault> ...]` | A layout fault; `<f>` is the film frame |
| `guard: FAIL mark: scene <id>: <cause>` | A mark error of section 6 was thrown |
| `guard: FAIL remotion render exit <n> (log <path>)` | Anything else; the last 40 log lines follow, indented |

`render.sh` finds the first two by their marker in the log of the pass.

There is no exemption (D6). The rung file gives the honest fixes: mark words with a tint or a
box and not with a second text; bring an object in with a fade or from inside the canvas;
finish a cross-fade before a checked frame.

What the guard does not see, stated so that nobody relies on it: a frame that is not checked;
anything that is not text, such as a shape over a label; a text of the background colour or
behind an opaque shape, which is measured as if visible and can only raise a false alarm. Those
cases stay with the stills.

The measurement runs in the browser and the spike did not run it. The pinned Remotion 4.0.532
has what it needs, as read in its code: the `--frames` option accepts a comma list, and
`cancelRender` ends the CLI with exit 1 and its message in the log. A layout effect runs in the
commit that draws a frame, so the measurement is as timely as the frame itself; that it is
never late is the part that only a run can show. The first task that touches the guard proves
it with the planted film of section 9.2. If
it cannot be made to work, that task's issue stays open with the finding, the wave is marked
blocked in the map, and the design comes back to the user. No fallback is designed here.

### 7.4 `render`, `container`, `sync`, `stills`

- `render` renders composition `Film`. It measures the checked frames again, with no effect:
  they passed. Brainrot keeps composition `Explain`.
- `container` and `sync` are unchanged.
- `stills` cuts the frames of `checkFrames` from the mp4 as today: `still-NN-<id>-s<k>.png` for
  the middle of sentence k, `still-NN-<id>-end.png` for the last frame of the scene.

### 7.5 `transcript`

`transcript.py` gives a film scene a section whose heading is the scene id, with the
narration and the cites. The nav link and the `narration.md` heading are the id too. Its cite
labels are built from the cites alone, since a film scene has no component. There is no
on-screen block and no Format row. Provenance, `Not covered`, the Narrator row and `verify.sh`
are unchanged.

### 7.6 Run directory

On the base every render compiles in the one shared `<ws>/app`: each run syncs its branch's
sources into it, empties and refills `public/audio`, and brainrot stages its background beside
it. Two renders at once spoil each other, and a film would add its scene code to the shared
sources. So each run gets its own directory (D8), for brainrot as well as for a film.

- Shared, and never written by a render: `<ws>/app/node_modules` with its install stamp, and
  `<ws>/models`. `video-workspace.sh` keeps them current as today, but it copies only
  `package.json` and `package-lock.json` into `<ws>/app` and no longer syncs the sources
  there. It leaves everything else in `<ws>/app` alone, so a session on older code that still
  renders in `<ws>/app` is not disturbed.
- For each run: after the `workspace` stage `render.sh` makes `<ws>/runs/<unique>/`, with a
  copy of the skill's `video/` sources, `node_modules` as a link to the shared one, and an
  empty `public/`. Every later step that compiles or renders uses it as the Remotion project:
  the scene copy and `tsc`, the audio copy, the brainrot background stage with its `public/bg`
  link, the guard pass and the render. `check_render.sh` needs only the Remotion binary and
  keeps the shared one.
- `render.sh` removes the run directory when it exits, also after a failure or a signal. A
  run also removes each run directory that is more than a day old, which a killed run can
  leave.
- The picker refuses a clip folder inside `<ws>/runs/`, in place of its rule for
  `<ws>/bg-stage` and `<ws>/app/public`.
- The `workspace` stage line does not change.

Not handled: two first installs at the same time (run one render first), and two branches
whose lock files differ (as today, each install replaces the other's packages).

The spike rendered and type-checked through a linked `node_modules`. A second workspace made
of links does not work on the base: its sync deletes a linked `node_modules` and installs
again (probed 2026-10-05). What no run has shown is two renders that share the bundler's cache
inside `node_modules`; the two-at-once test of section 9.2 shows it, and `--bundle-cache=false`
is the fix if they collide.

## 8. Rung files

### 8.1 `rungs/video.md` (rewritten)

1. When a video (unchanged rule; a forced video keeps the content; English only).
2. The grammar of a film, as rules:
   - One picture for the whole film. Objects stay and change; the stage is never cleared
     between scenes.
   - Each scene changes the picture while the voice speaks. A scene is one or two sentences,
     with one motion for each sentence.
   - Decide the picture first, then write the narration that fits it.
   - Text on the stage is a label, a source line in a code card, or a claim under test. A list
     of sentences is a fault.
   - A colour has one meaning: yellow the subject, blue chosen, green pass, red fail.
3. Write the script (section 4.2), with the length guidance measured in the live run.
4. Write the scene: the copy of the example; the stage and `useCurrentFrame()`; the kit, with
   its signatures; the marks; the mono position rule; the 14 px floor; the import and token
   rules, with the note that an unused local fails `tsc`; the three honest fixes of
   section 7.3.
5. Build and check: the eleven lines and their FAIL lines, the first-run costs, the narration
   fallback.
6. Read the stills (section 8.4).
7. Handoff, output directory, pinned versions.

Sections 5 and 7 keep stable titles, because `brainrot.md` points at them by title.

### 8.2 `rungs/brainrot.md`

Today it takes from `video.md`, by section number: the script keys, the rules for each scene
with the list of what the prose lint reads, the components, the cue rule, the way to read the
stills with the base fault list, the output directory, the first-run costs, the narration
fallback, the render ratio, the handoff and the pinned versions.

After this feature it holds its own copy of everything that a film no longer has or does
differently: the scene rules, the components, the cue rule, the stills fault list, the output
directory and the constants. The explainer column of its limits table goes. It points at
`video.md`, by section title, only for the first-run costs, the narration fallback, the render
ratio, the handoff and the pinned versions. "Without the key, the script is an explainer"
becomes "is a film". Its section on the background names the stage of section 7.6 in place of
`<ws>/bg-stage` and `<ws>/app/public`.

### 8.3 `SKILL.md`, `README.md`

`SKILL.md`: the Build procedure step that says what a video author writes adds the scene
directory, and the line that describes `rungs/video.md` ("components, cue rule") is rewritten.
`README.md`: the rung description, the layout lines and the landscape test command. The video
row of the rung table and the conventions do not change.

### 8.4 The stills review

The author reads every still. Faults:

1. Text that is clipped by a shape, or that a shape covers.
2. A picture that does not agree with the narration of its scene.
3. An `-end` still that equals the `-end` still of the scene before it: the scene changed
   nothing.
4. A picture that is a list of sentences.
5. Text that gives a false picture of the subject, a quoted line that the source does not hold
   among them.

## 9. Testing

### 9.1 Unit (always run)

- `test_video_timeline_film.py`: for each rule of section 4.2, one script that fails with that
  cause and the same script without the fault that passes (a `pause` of 11, `12.0` and `"12"`
  among them); the build output of section 7.1 (scene length, `sentences`, `words`,
  `checkFrames`, `sources` with tabs expanded); the `--types` output; a script with
  `"format": "slides"` and a film scene with `component` are refused.
- `test_check_scene.py`: one failing fixture for each rule and each token of section 7.2,
  asserted by its line, and a clean fixture that passes.
- Marks, in Node: scene start, sentence, word, `nth`, `said`, `end`, and each error by its
  message.
- Guard logic, in Node, on made-up boxes: 2 px past the canvas fails and 1 px passes; 13.9 px
  fails and 14 passes; a 3 px overlap fails and 2 px passes; a text of opacity 0.09 is not
  measured; six faults give five and `(+1 more)`.
- `motion.ts`: `p` and `lin` at the start, the middle and the end, and with `len` 0;
  `mixColor` on both input forms.
- `test_transcript.py`, `test_check_budgets.py`, `test_narrate_sentences.py`: a film case
  each.
- The two tests of section 5.3 that keep the example true.
- `test_video_workspace.py`: the shared app gets the two package files and nothing else, and
  what is already in `<ws>/app` stays.
- Each assertion is first seen to fail in the broken state, per the house rule.

### 9.2 End to end (gated by `EXPLAIN_VIDEO_E2E=1`)

- The worked example passes with eleven `ok` lines. This is the control for every plant.
- Stage plants: the example with one edit; each stops before any synthesis.

  | Plant | Expected line |
  |---|---|
  | A cite snippet with one word changed | `script: FAIL` with the cite check's line for that cite |
  | `at("no-such-scene")` | `scene: FAIL tsc:` with the TS2345 line of that call |
  | An import of `@remotion/paths` that is used | `scene: FAIL Film.tsx:<line>: import from "@remotion/paths"` |
  | `// @ts-nocheck` on line 1 | `scene: FAIL Film.tsx:1: token "@ts-nocheck"` |

- One planted film for the browser rules. Its first checked frame shows five extra labels, and
  the guard line must name the first four and must not name the fifth:
  a label at x = 1400 (`OFFCANVAS`); a label at 10 px (`SMALLTEXT 10.0 px`); a 20 px label
  inside `scale(0.5)` (`SMALLTEXT 10.0 px`); two labels on one spot (`OVERLAP`); a label at
  x = 1400 inside a group of opacity 0.
- A film with `at("type", { word: "zebra" })` gives `guard: FAIL mark: scene type:` and the
  word.
- Two renders started together, one brainrot and one film, both end with all their `ok`
  lines. The checksum of `<ws>/app` without `node_modules` is the same before and after.
  `<ws>/runs/` is empty after a run that passes, a run that fails and a run stopped with
  SIGTERM.
- Brainrot's end-to-end tests pass with ten lines. They import `STAGES`, `stage_lines` and the
  constants of `video_e2e.py` from the modules that the removal rewrites; those names stay
  importable.

### 9.3 Live runs (acceptance)

Recorded in `docs/superpowers/spikes/<date>-explain-film-live-run.md`, with every `render.sh`
run, its exit code and its first FAIL line.

A fix round is one `render.sh` run made after the first run that exits 0. A run passes with at
most two fix rounds and at most ten runs in all.

1. Cold run. A fresh general-purpose subagent gets `/explain <subject> --as video` and the
   skill path, nothing else. The subject is `ImportController.java` of inavcalculator, the
   subject of the first video live run, so the old and the new video can be compared.
2. Long run. A second fresh subagent, the directory `skills/explain/` as the subject, and the
   instruction to come near 150 s. It measures the lines of scene code, the runs and the stills
   that a long film costs.
3. The stills of each final run are judged by another fresh subagent that gets only the
   stills, the narration and the fault list of section 8.4, not by the author.
4. Fold-back, from both runs: the `film` row of `FORMATS`, `MIN_TEXT`, the frames checked in
   each scene, the length guidance of `video.md`, and whether a guard fault had no honest fix
   (D6).
5. The user watches both and accepts, or names what to change.

## 10. Removal

The removal wave comes after the film works (D7). It flips the default format and takes out
what only the explainer used.

Removed:

- the `explainer` row, name and fallbacks (`limitsFor`, `shapesOf`, `tagOf`, `format_tag`) in
  `formats.json`, `build-timeline.mjs`, `narrate.py`, `types.ts`, `Root.tsx`, `box.ts`, `render.sh`,
  `check_render.sh`, `check_budgets.py`, `transcript.py`, `templates/video.html`, and their
  messages;
- the landscape branch of `Explain.tsx`, `LANDSCAPE_BOX` with its assertions in
  `test_scene_geometry.py`, and the landscape regression harness
  (`test_landscape_regression.py`, `capture_landscape_baseline.sh`) with its baseline;
- scene-mode narration and the character-offset cue frame. Issue kp-5a2 (sentence synthesis
  for the explainer) is closed as superseded;
- the old `templates/video-script.json`, replaced by the film template (section 5.3).

Ported, not deleted. `test_video_timeline.py` (41 cases) and `test_narrate.py` (28 cases) use
scripts without a format. They are the only unit cover of the component shapes, the cue rules,
the diagram and code checks, the fallback, the speed and the clip cache, and brainrot's tests
import fixtures and helpers from them, from `test_render.py` and from `video_e2e.py`. Their
scripts get `"format": "brainrot"` with the brainrot limits. A case that tests a rule only the
explainer had (scene mode, the offset cue frame, the untagged message, the nine lines) goes.

Kept, because brainrot uses it: the five components, the scene box, `layout.tsx`,
`png_diff.py`, the component shapes and cue rules of the validator, sentence narration,
captions, the background stage.

Done when all of these hold:

- `git grep -n -i explainer -- skills/ README.md` prints nothing;
- `git grep -n "LANDSCAPE_BOX\|test_landscape_regression\|capture_landscape_baseline" -- skills/`
  prints nothing;
- `narrate.py` has one narration mode;
- the unit suites pass, and so do the film and brainrot end-to-end tests.

Old outputs under `out/` are not migrated.

## 11. Effect on the two approved specs

Both get an amendment after this feature lands (D4). Neither is changed by this spec.

- Lesson (`2026-10-04-explain-lesson-design.md`, map `2026-10-04-explain-lesson.yaml`). Wave
  `lesson-page` (kp-4h3) owns only page-side files and does not depend on the film: its tasks
  kp-4h3.1, .3 and .5 are ready today on its planned base. Three waves target the explainer
  and need a new target: `clip-format` (`clip` as a copy of the explainer row, a highlight-cite
  check on a component, an acceptance that runs `test_landscape_regression`), `lesson-rung`
  (nine `ok` lines, review prompts that judge components and cue stills, a poster named
  `still-NN-<scene>.png`), and `lesson-live-run` (`FORMATS.clip`). The lesson spec also counts
  on 24 px code that shows at 18 px in the page; a film's 14 px floor shows at 10.5 px there,
  so a clip needs its own floor.
- Russian (`2026-10-04-explain-russian-design.md`, on `worktree-explain-russian`). The Silero
  engine, `pronounce` and the pre-flight check stand. Its rule that `lang: ru` is for the
  explainer format, and its section that places explainer cue frames on the spoken text, need
  a new target: a film is narrated in sentence mode and timed by marks on the narration tokens
  of the words file.

## 12. Sequencing

1. `feat/explain-film` is cut from `feat/explain-brainrot` and does not wait for brainrot's
   acceptance: what remains there changes values in `formats.json` and wording in
   `rungs/brainrot.md`, not structure. Another session owns the brainrot branch; this feature
   does not commit to it. When brainrot merges to `main`, the film branch is rebased onto it.
   Until the run directory of section 7.6 is in, a film-branch render uses its own workspace
   (`EXPLAIN_VIDEO_WORKSPACE`: a full install, about a minute and 447 MB). After it, a
   film-branch render writes nothing that the other session reads.
2. This spec: user review, then the wave map (`wave-planning`).
3. The one branch `feat/explain-film` spans all waves. The
   expected shape, for the wave map to settle: the format beside the explainer, with marks,
   kit, stage and example; the `scene` and `guard` stages with their plants; the rung files,
   the default flip and the removal; the live runs and fold-back.
4. Then the two amendments of section 11.

## 13. Risks

| Risk | Handling |
|---|---|
| The guard cannot measure inside the render | Proven first, with the planted film; otherwise the wave is blocked and the design comes back (section 7.3) |
| With no exemption, a false alarm of the guard has no honest fix and the author bends the picture | Counted in both live runs; an exemption is designed only on that evidence (D6) |
| A cold agent cannot write a film from the rung file | The cold run is the acceptance test. The spike was written with the whole repo in context, so this is not yet shown |
| A 150 s film is too much code: the spike needed about 15 bespoke lines for each second | The long run measures it; the limit is folded back (D3) |
| Stills cost: about 65 images in each review round of a long film | Measured in the long run; the frames checked in each scene are a starting value |
| A word mark is an estimate | Stated in the rung file; a motion that needs an exact frame uses a sentence mark |
| On-screen labels are not listed, linted or proven | Accepted (section 3). Source lines come only through the code card |
| Two renders share the bundler's cache inside the linked `node_modules` | The two-at-once test shows it; `--bundle-cache=false` if they collide (section 7.6) |
| The run directory changes brainrot's background stage while another session finishes brainrot | The change is on the film branch only; conflicts are settled at the rebase |
