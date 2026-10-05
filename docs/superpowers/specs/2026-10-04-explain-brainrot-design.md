# Explain `brainrot` format — design

Date: 2026-10-04
Status: approved in conversation section by section; written spec pending user review

## 1. Purpose

The "brain rot" short is a common mobile format: a vertical video that explains or tells
something while a looping "dumb" clip (Subway Surfers, Minecraft parkour) plays in the
background, with big word-by-word captions. This design adds that format to `/explain` as a
second video format next to the 16:9 explainer.

The grounding of the explain skill does not change: every scene carries cites, the transcript
`index.html` passes `verify.sh`, and the narration follows the STE profile. The brain rot feel
comes from the delivery and the picture only: a vertical split layout, a background loop, a
faster voice, word-by-word captions and a hook scene.

Success means:

- a phone viewer can read the code or the diagram in the top half;
- the captions follow the voice word by word;
- the pipeline (stage lines, checks, stills, transcript) works as it does for the explainer;
- the existing explainer video renders unchanged.

## 2. Scope

In scope:

- `--as brainrot` in the `explain` router, and a thin rung file `rungs/brainrot.md`.
- A `format` key in `script.json`, with per-format limits in `build-timeline.mjs`.
- A `SceneBox` refactor so that every scene component lays out in a box given by the
  composition, not in a fixed 1280×720 box.
- A `Short` layout (1080×1920): scene panel, background, caption band.
- A background picker (user clips, or the generated `RunnerLoop`).
- Per-sentence narration with word timings, and caption chunks in the timeline.
- Tests, an E2E render of both formats, and one live run with fold-back of the limits.

Out of scope:

- Automatic rung selection of `brainrot`. The format is a style, not a content shape: it is
  forced only.
- Slang or meme narration. The narration stays STE (decision D2).
- Shipping or downloading gameplay footage. The repo ships no third-party clips.
- Gameplay audio. The background is muted; the only audio track is the narration.
- Per-sentence synthesis for the explainer format (follow-up issue, decision D6).
- Background music, sound effects, a voice other than `af_heart`.

## 3. Interface

### 3.1 Invocation

`/explain <subject> --as brainrot`. The router accepts `brainrot` as a fifth `--as` value; the
error for an unknown value lists five names. The rung table in `SKILL.md` gets a `brainrot` row
marked "forced only". The rung line reads
`Rung: brainrot (forced) — <reason> — subject: <subject> (<kind>)`.

The output directory follows convention 5 with the rung name:
`out/YYYY-MM-DD-HHMMSS-brainrot-<slug>/`. Its contents are the video rung's contents
(`rungs/video.md` section 5); `build/timeline.json` additionally carries `format`, `captions`
and `background`, and `audio/` additionally holds `<id>.<engine>.words.json`.

Like the video rung, the brainrot rung is English only.

### 3.2 Rung file

`rungs/brainrot.md` holds only what differs from `rungs/video.md`, and names the sections of
`video.md` to read for the rest (write the script, cite rules, components, the cue rule, build
and check, handoff). It states:

- `"format": "brainrot"` in `script.json`;
- the limits table of section 3.4;
- the background folder and how to force the generated loop;
- the hook guidance (section 3.5);
- the three extra still faults of section 6.3;
- the narrator line at handoff (`af_heart` at speed 1.2, or `say`).

### 3.3 `script.json`

One new top-level key: `format`, with the value `explainer` or `brainrot`. When the key is
absent, the format is `explainer`, so every existing script and test is valid without change.
`render.sh` reads the format from the script; its command line does not change.

### 3.4 Per-format limits

`build-timeline.mjs` holds one limits table keyed by format, next to the current constants. The
explainer column is today's values.

| Limit | explainer | brainrot |
|---|---|---|
| canvas | 1280×720 | 1080×1920 |
| scenes | 3–8 | 3–6 |
| max scene length | 60 s | 30 s |
| max total length | 150 s | 90 s |
| narration words per scene | 45 | 45 |
| lead / tail frames | 15 / 36 | 6 / 12 |
| code range | 14 lines × 72 columns | 14 lines × 40 columns |
| `bullets-appear` text | 36 chars | 40 chars |
| `before-after` | side by side; 0–10 lines × 36 chars; heading 36 | stacked; 0–5 lines × 48 chars; heading 45 |
| diagram `label` / `sub` | 14 / 24 | 12 / 19 |
| diagram edge `label` | 10 | 10; no label on an edge in a row |
| `title` title / subtitle | 50 / 80 | 30 / 60 |
| scene heading | — | 29 chars |
| caption chunk | — | 1–3 words, 20 chars |

(Tuned 2026-10-05 in the live run; evidence in `docs/superpowers/spikes/2026-10-05-explain-brainrot-live-run.md`.)

A limit failure names the format: `line 7 is 52 columns (max 40, brainrot)`.

### 3.5 Hook guidance

Written in `rungs/brainrot.md`, not enforced: scene 1 is a `title` scene whose narration is one
sentence of 12 words or fewer that says why the subject matters.

## 4. Rendering

### 4.1 One composition, two layouts

`Explain` stays the only Remotion composition. `timeline.json` gets `format`; `Explain` renders
the current landscape stack for `explainer` and the `Short` layout for `brainrot`.
`calculateMetadata` already takes `width` and `height` from the timeline, so `render.sh` still
runs `remotion render Explain`.

### 4.2 `SceneBox`

`layout.tsx` no longer exports fixed `FRAME` and `CONTENT` boxes. A React context `SceneBox`
provides the scene's box: `{ width, height, margin, titleSize }` plus the type sizes the scenes
use. Scenes read it through `useBox()`. `diagramGeometry.ts` takes the box as a parameter.
`BeforeAfter` stacks its two panels (before above after) when the box sets `stackPanels`, and
keeps them side by side otherwise. The brainrot box sets it: its content area (984×758) is wider
than tall, but two 468 px columns cannot hold a 30-character line. (Amended 2026-10-04 while
planning wave brainrot-render; the first wording was "when the box is taller than wide".)

The landscape layout provides today's values, so the explainer renders the same pixels as before
the refactor (checked by the regression test in section 7.4).

### 4.3 `Short` layout (1080×1920)

- Top, 1080×960: a white panel that holds the scene (title band and content box) in the current
  palette at larger type (code about 36 px mono, bullets about 44 px). Scenes fade in as today.
- Bottom, 1080×960: the background, `object-fit: cover`, muted. It runs without a break across
  scene boundaries.
- Caption band, centred on the seam (y ≈ 960): bold white text with a black stroke, one chunk
  (1 to 3 words) at a time; the word being spoken is yellow. Yellow is the only new colour, and
  only `Short` uses it.

### 4.4 Background

`render.sh` (stage `background`, section 6.1) chooses the background:

1. The clip folder is `$EXPLAIN_BRAINROT_BACKGROUNDS`, or `<workspace>/backgrounds/` when the
   variable is unset. Only `*.mp4`, `*.mov` and `*.webm` files count.
2. Take the clips in random order. For each, read its duration and video stream with the
   workspace's `remotion ffprobe`. A clip that cannot be probed, or has no video stream, prints
   `background: SKIP <file> (<cause>)`, indented, and the next clip is tried.
3. For the first good clip: if it is at least as long as the video, pick a random start in
   `[0, clip − video]`; else the start is 0 and the clip loops. Stage the clip in
   `<ws>/bg-stage/` as the regular file `clip.<ext>`: a hard link to the clip, or a copy when
   the hard link fails. `<ws>/app/public/bg` is the relative symlink `../../bg-stage`, made again
   on every run. File names with spaces work.
4. When the folder is missing, empty, or holds no good clip, the background is `RunnerLoop`.

Why the stage: the static server of Remotion 4.0.532 answers 404 for a file that is itself a
symlink, and its bundler copies every regular file in `public/` into each bundle. A path through
the directory symlink `public/bg` to a regular file is served and not copied. The stage lies
beside the app, not in it: the sync of any checkout's `video-workspace.sh` (`rsync --delete`)
would delete a stage in `<ws>/app` and leave the link dangling, and a dangling link in `public/`
fails every render. (Amended 2026-10-05 in the final review of wave brainrot-render.)

`RunnerLoop` is a Remotion component: three lanes in perspective, scrolling stripes, a block
character that hops between lanes, and obstacles. It is a pure function of the frame number and
a fixed seed, so two renders are the same.

The choice goes into `build/timeline.json` as
`background: { kind: "clip", file, src, start, seconds, loop } | { kind: "generated" }`. `src` is
the fixed link name `bg/clip.<ext>` under `public/`, so a file name with spaces never reaches
Remotion; `seconds` is the clip length, which the loop needs. (Amended 2026-10-04 while planning
wave brainrot-render.)

## 5. Narration and captions

### 5.1 Voice

Kokoro `af_heart`, as today, at speed 1.2 instead of 1.0. The `say` fallback uses `-r 210`
(about 1.2 × the default rate). `narrate.sh` gets a `--speed` argument; `render.sh` sets it from
the format. The WAV sidecar already records the speed, so a format change re-synthesises the
clip and never reuses an explainer clip.

### 5.2 Per-sentence synthesis and word timings

For `brainrot`, `narrate.py` splits each scene's narration into sentences, synthesises one
sentence at a time, and joins the clips with 0.15 s of silence. The same path serves Kokoro and
`say`, so a fallback keeps its captions.

- The sentence splitter ends a sentence at `.`, `?` or `!` followed by a space or the end of the
  text. A full stop inside backticks (`` `verify.sh` ``) or inside a word (`render.sh`) does not
  end a sentence.
- Sentence start and end times are exact: they are the positions where the clips were joined.
- Inside a sentence, each word gets a share of the sentence's duration in proportion to its
  character length; a word that ends in `,`, `;`, `:` or the sentence end gets 2 extra
  characters of weight for the pause.
- `narrate.py` writes `audio/<id>.<engine>.words.json`:
  `{ "sentences": [{ "from": s, "to": s }], "words": [{ "text": w, "from": s, "to": s }] }`,
  in seconds from the clip start.

### 5.3 Cue frames

For `brainrot`, a cue frame is the exact start of its sentence from `words.json`:
`lead + round(sentence.from × fps)`. The cue rule of `video.md` (cues start sentences, are
unique, in order, 15 frames apart) applies unchanged. The explainer keeps its estimate.

### 5.4 Caption chunks

`build-timeline.mjs` builds the chunks, so the Remotion side only draws them. Per scene, the
timeline carries `captions: [{ from, to, words: [{ text, from, to }] }]` in frames relative to
the scene start:

- a chunk holds 1 to 3 words, and breaks after a word that ends in punctuation;
- a chunk shows from its first word's start to the next chunk's start (the last chunk of a
  scene ends at its last word's end);
- the chunks cover the narration words in order, with no gap and no overlap.

Backticks are removed from caption text, as the narrator already speaks code names as plain
text.

(Amended 2026-10-05 in wave brainrot-live-run: a chunk also closes before it passes the character cap of §3.4; a longer word is a chunk alone, drawn smaller.)

## 6. Pipeline, checks and errors

### 6.1 Stage lines

For `brainrot`, `render.sh` prints ten stage lines:
`script`, `workspace`, `narration`, `timeline`, `background`, `render`, `container`, `sync`,
`stills`, `transcript`. The new line is `background: ok <clip name> @<start> s[ (loop)]` or
`background: ok generated`. `background` runs after `timeline` because it needs the total
length; it adds the `background` field to `build/timeline.json`.

The explainer prints no `background` line and keeps its nine lines unchanged.

### 6.2 Workspace

`video-workspace.sh` creates an empty `backgrounds/` folder. There is no new download and no new
cost line; `RunnerLoop` is app source.

### 6.3 Checks

- `container`: also checks that the mp4's width and height equal the timeline's.
- `sync`: unchanged. The background is muted, so the only audio is the narration.
- `stills`: the same frames as today. `rungs/brainrot.md` adds three faults to look for: a
  caption that is absent or does not match the narration at the cue, a caption that overlaps the
  panel content, and a background that is black or frozen.
- `transcript`: the same page, checked by `verify.sh`. The provenance block gets two rows:
  `Format: brainrot (1080×1920)` and `Background: <clip name> @ <start> s | generated`.

### 6.4 Errors

| Case | Result |
|---|---|
| `format` is not `explainer` or `brainrot` | `script: FAIL format must be explainer or brainrot` |
| A brainrot limit is exceeded | `script: FAIL …` naming the limit and the format |
| Clip folder missing or empty | Not an error: `background: ok generated` |
| A clip cannot be probed or has no video stream | Indented `background: SKIP <file> (<cause>)`; next clip |
| A clip probes but fails to decode during render | `render: FAIL` with the log, as today. `rungs/brainrot.md`: remove the clip, or set `EXPLAIN_BRAINROT_BACKGROUNDS` to an empty folder to force the generated loop |

Clips are local files only. Nothing is downloaded.

## 7. Testing

The tests follow the `unittest` layout in `skills/explain/tests/`. Renders stay behind
`EXPLAIN_VIDEO_E2E=1`.

### 7.1 Validator and timeline (`test_video_timeline.py`)

- A script without `format` validates and builds as today; the existing cases pass unchanged.
- Each brainrot limit of section 3.4 at its boundary: one case at the limit passes, one just
  over fails with the format named (7 scenes, a 41-column line, a 41-char bullet, a 31 s scene,
  a 91 s total, a 49-char `before-after` line, a 46-char `before-after` heading, a 6-line
  `before-after` panel, a 13-char diagram label, a 20-char diagram sub, a 31-char title, a 61-char
  subtitle, a 30-char scene heading, a label on an edge in a row). (Amended 2026-10-05 with the
  tuned values of §3.4.)
- An unknown `format` fails.
- A brainrot timeline has lead 6 and tail 12 frames.
- A brainrot cue frame equals `lead + round(sentence.from × fps)` from `words.json`.
- Caption chunks: at most 3 words and at most the character cap of §3.4 (a longer word is a
  chunk alone), a break after punctuation, no gap, no overlap, every narration word once and in
  order, no backticks.

### 7.2 Narration (`test_narrate.py`, `say` engine or a stub engine)

- The splitter keeps `` `verify.sh` `` and `render.sh` inside one sentence and splits at
  `. `, `? ` and `! `.
- `words.json`: times increase, every word is present, the last word ends at or before the clip
  end, and sentence boundaries equal the join positions.
- A changed speed does not reuse the cached WAV.

### 7.3 Background picker

Fixture folders: missing, empty, a non-video file only, a corrupt `.mp4` (gives `SKIP`, then
`generated`), and a checked-in valid clip of about 1 s at 64×64 (a few KB). With that clip, the
result loops from start 0 because the clip is shorter than the video; a stubbed long duration
gives a start inside `[0, clip − video]`.

### 7.4 E2E (gated)

- Brainrot renders the template script once with the generated loop and once with the fixture
  clip: all ten stage lines `ok`, 1080×1920 in `container`.
- Landscape regression: the explainer template renders, and its stills are compared with stills
  captured on `main` before the `SceneBox` refactor. Pass: at most 0.5 % of the pixels of each
  still differ by more than 16 levels in any channel.

### 7.5 Live run

Render a real subject from this repository as `brainrot`. Read the stills, tune the limits of
section 3.4, and fold the final values back (section 3.4). Acceptance: the user watches the
video on a phone.

## 8. Decisions log

| ID | Decision | Reason |
|---|---|---|
| D1 | A `/explain` format, not a standalone generator | Keeps grounding, transcript and checks |
| D2 | STE narration; the brain rot feel comes from delivery and picture | Keeps convention 1 without a carve-out; STE sentence length suits captions |
| D3 | Background: user clips, else generated `RunnerLoop` | No third-party footage in the repo; a run never fails for want of a clip |
| D4 | Split layout, scenes re-laid for portrait (`SceneBox`) | Phone-readable text; scaling the 16:9 stack gives about 20 px code |
| D5 | ≤ 90 s, 3–6 scenes, ≤ 30 s per scene | User choice; shorter than the explainer, room for 3–6 facets |
| D6 | Per-sentence synthesis for brainrot only | Exact word and cue timing without a new aligner; the explainer stays as approved (follow-up issue) |
| D7 | One composition, `format` in the timeline | `render.sh` and `calculateMetadata` stay as they are |
| D8 | Caption chunking in `build-timeline.mjs` | Testable without a render; Remotion only draws |
