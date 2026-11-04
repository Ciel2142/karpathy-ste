# Explain `movie` rung: a video-only course for one theme — design

Date: 2026-11-03
Status: draft, for the user's approval. A builder check (one fresh subagent) ran on 2026-11-03; its ten questions are settled in D6, D7, D10 to D12, 4.2 to 4.6 and section 6.
Base: `main` at `2b3b0f5`. The pipeline facts below were read at that commit.

## 1. Purpose

The user learns from the films better than from any page the skill makes. Today video is the
add-on, not the carrier. The `video` rung makes one film of at most 150 s. The `lesson` and
`course` rungs make a page the hub and the clips an optional extra that the reader can skip.

A `movie` is a theme told as one sit-down film of several minutes. The viewer watches it from
start to end and reads nothing. It keeps the grammar the user chose for the film rung: one
picture that stays and changes, text only as labels, narration timed to each sentence.

Two observed problems of the lesson and course rungs drive the second half of this design. A
weaker model that builds a lesson undertells: it stops when the script feels done, and nothing
asks if a viewer could now answer the question of the theme. The review gates check that each
claim is cited and true, not that the artifact is enough to understand. So the movie rung makes
"enough to understand" a contract that is written before the script and tested after the render.

Success means:

- `/explain <theme> --as movie` makes one `video.mp4` of 4 to 10 chapters that plays as one film
  with chapter markers, on a topic subject or a code subject, in English or Russian;
- the author writes the viewer questions before any script, and a cold viewer who sees only the
  film answers them after the render, as a gate that is on by default;
- a chapter that fails renders again alone, and a rerun on the output directory resumes;
- no change to `formats.json`, `build-timeline.mjs`, `narrate.py`, `check_budgets.py`,
  `transcript.py`, `render.sh` or `check_render.sh`. A chapter is a film and a bridge is a clip.
  `verify.sh` changes once: it accepts `movie` as a rung and its `media` check counts
  `chapters/` and `bridges/` links as it counts `clips/`.

## 2. Decisions

| # | Decision | Choice |
|---|---|---|
| D1 | Shape (user, by accepting the proposal) | One continuous movie for each theme, cut into chapters, with short bridge beats between chapters. Rejected: a playlist of independent shorts (loses the one-picture grammar); a video hub for the course rung (its clips are written as add-ons to a page and undertell by construction). |
| D2 | How it is built (user) | Compose films. Each chapter is a `film` of the existing pipeline. Bridges are generated `clip` films. A new `movie.py` plans, checks and stitches. Rejected: one Remotion scene of 10 minutes (a fix re-renders all, and the scene code grows past what one author keeps straight). |
| D3 | Comprehension | A viewer-question contract: the author writes the questions, the answers and the cites in `movie.json` before any script. A cold viewer gate runs by default, not behind `--review`. `--review` adds the fact gate of the lesson rung to each chapter. |
| D4 | Who writes the chapters | The author plans the movie and writes `movie.json`. One fresh subagent builds each chapter from a brief, in the background, as the course rung does for lessons. The brief carries the questions the chapter answers and the picture it starts from. Rejected: one author for all chapters (eight chapters of scene code do not fit one context). |
| D5 | Continuity between chapters | Each chapter is its own picture, so no object persists across the cut. The brief gives the subagent the end picture of the previous chapter in words, and the chapter opens on that arrangement. A bridge card between chapters shows the question just answered and the next question. This is the accepted loss of D2. |
| D6 | Stitching | The ffmpeg of the Remotion CLI (`remotion ffmpeg`, as `check_render.sh` already runs it), with the concat demuxer and stream copy. No new dependency. Checked at the base: the binary has the `concat` demuxer and the `mp4` muxer, and not the `ffmetadata` demuxer, so the mp4 carries no chapter markers. Chapter navigation lives in the transcript hub (4.6), from `chapters.json`. Every render encodes AAC at 48 kHz, so stream copy holds across engines; `stitch` still probes each part and refuses a mismatch. |
| D7 | Limits | A chapter keeps the film limits (3 to 30 scenes, 150 s). A bridge keeps the clip limits, so it has 3 scenes. A movie has 4 to 10 chapters and runs 4 to 15 minutes: each chapter carries a `seconds` target, `check` sums the targets with the bridges budgeted at plan time (the sum plus 8 s per bridge must reach 240 s, the sum plus 15 s per bridge must stay within 900 s; amended at wave 1 close, since the bridges are part of the film the viewer watches), and `stitch` checks the real total. The limits live in `movie.py`, not in `formats.json`. |
| D8 | Subjects | `topic`, `file` and `directory`, by the resolution rules of `SKILL.md`. `conversation` is refused. A topic that is not about repo code uses model knowledge and the web, as the video rung does. |
| D9 | Output | A directory `out/YYYY-MM-DD-HHMMSS-movie-<slug>/`. `video.mp4` is the artifact. `index.html` is the transcript hub. |
| D10 | What the cold viewer sees | The transcript without the `ask` and `answer` scenes of every chapter, plus one still per chapter: the `-end` still of the last body scene. The viewer must derive each answer from the body. Rejected: all stills (a subagent stalls on many images; `lesson.md` caps a reviewer at five); the full transcript (the gate could only fail on a paraphrase). |
| D11 | Parallel chapters | At most 3 chapter subagents at a time, as the course rung caps lessons. The author runs `video-workspace.sh --engine <engine>` once before the fan-out, so a first install never runs twice. |
| D12 | `--review` for a chapter | A new prompt `movie/review-chapter.md`, derived from `lesson/review-script.md`, with the chapter's question and answers in place of the page section. A finding still open after two rounds ships: the chapter is `built`, and the pair goes to `not_covered` as `disputed: <finding>`. A chapter is never dropped, since it answers a question. |

## 3. Scope

In scope:

- `rungs/movie.md`, the rung file, and the `--as movie` route in `SKILL.md` and `README.md`.
- `scripts/movie.py` with the commands `check`, `bridges`, `stitch`, `status` (section 6).
- `movie/chapter-task.md`, the chapter subagent prompt, `movie/review-viewer.md`, the cold
  viewer prompt, and `movie/review-chapter.md`, the `--review` fact gate of a chapter (D12). All
  three are templates filled by plain text replacement, as the course prompts are.
- The `movie` entry in `verify.sh` (section 1).
- `video/src/bridge/`, the bridge scene template, and `templates/movie-bridge-script.json`.
- `templates/movie.html`, the transcript hub.
- Tests: `movie.py` unit tests with fixtures, prompt tests, a rung drift case, and one gated
  live run (`EXPLAIN_VIDEO_E2E=1`) that stitches two real chapters and a bridge.

Out of scope:

- Any change to the film, clip or brainrot formats, or to the render pipeline.
- Music, a second voice, a language other than English or Russian.
- A page or a sheet beside the movie. The hub is a transcript, not an explanation.
- Objects that persist across chapters (D5).

## 4. Interface

### 4.1 Invocation

`/explain <subject> --as movie [--review]`. Only `--as movie` selects it. The rung line is:

```
Rung: movie (forced) — <reason> — subject: <subject> (<kind>)
```

`<kind>` is `topic`, `file` or `directory`. For `conversation`, print the rung line, say the movie
rung takes no conversation subject, stop, and offer `video`.

A subject that is one directory holding `movie.json` is a resume (section 7).

### 4.2 `movie.json`

The plan of the movie. The author writes it. Build nothing before the plan passes
`movie.py check` and the user approves it (section 5, step 4).

```json
{
  "version": 1,
  "title": "How a Kafka consumer group rebalances",
  "question": "What happens to the partitions of a group when a consumer joins or leaves?",
  "lang": "en",
  "pronounce": {},
  "review": false,
  "subject": { "text": "kafka consumer group rebalance", "kind": "topic" },
  "provenance": { "root": "/abs/path", "commit": "none", "dirty": "no", "date": "2026-11-03",
                  "source": "model knowledge", "not_covered": "none" },
  "state": "planned",
  "questions": [
    { "id": "q-trigger", "text": "What starts a rebalance?",
      "answer": "A member joins, leaves, or misses its heartbeat; the coordinator then revokes.",
      "cites": [] }
  ],
  "chapters": [
    { "id": "members", "title": "The members", "question": "Who is in a group?",
      "answers": ["q-trigger"], "seconds": 90,
      "picture": "Three consumers as yellow boxes on the left, six partitions as a column on the right.",
      "ends_with": "Each consumer owns two partitions, drawn as lines.",
      "status": "pending", "reason": "" }
  ]
}
```

Rules:

- Ids match `[a-z0-9][a-z0-9-]*` and are unique across questions and chapters.
- `questions`: 3 to 5. Each has `text`, `answer` (one or two sentences, the answer the viewer
  must be able to give) and `cites`. For a `file` or `directory` subject each question has at
  least one cite. For a `topic`, `cites` may be `[]`.
- `pronounce`: the map of `video.md` section 3, used only with `"lang": "ru"`. `bridges` copies
  it into each bridge script, since a bridge narration quotes the answers and the questions. The
  `script` stage of the render reports a missing entry; `check` does not repeat that.
- `chapters`: 4 to 10, in the order of the film. Each `answers` list names one or two questions,
  and every question is named by at least one chapter. `seconds` is the length target of the
  chapter, 30 to 150; the sum over the chapters is 240 to 900. `picture` says what is on the stage when
  the chapter opens, `ends_with` what is on it at the last frame. The brief of chapter `n+1`
  receives `ends_with` of chapter `n` as its opening picture.
- `status`: `pending`, `built`, `failed`. `reason`: empty, or the FAIL line of the last build.
- `state`: `planned`, `building`, `stitched`.
- Prose fields follow the STE profile, or convention 7 for `ru`.

### 4.3 A chapter

`chapters/<id>/` is one complete film output: `script.json` with `"format": "film"`, `scene/`,
and everything `video.md` lists after a render. The chapter's `script.json` obeys the film
contract with three additions that `movie.py check` enforces:

- its first scene has the id `ask`, and its last scene has the id `answer`;
- `title` of the script equals the chapter's `title`.

`check` tests the ids and the title only. What the scenes say is the duty of the chapter brief:
`ask` speaks the chapter's question, and `answer` states the answer of each question in
`answers`, one or two sentences each, within the 45 words of a scene (that is why a chapter
answers at most two questions). The narration rules of `video.md` apply, so the wording differs
from `movie.json`; a verbatim check would collide with them. The viewer gate (D10) tests
whether the body made those answers visible.

### 4.4 A bridge

`bridges/<n>/` for `n` from 1 to the number of chapters minus 1 is a generated `clip` film.
`movie.py bridges` writes its `script.json` and `scene/` from `movie.json` and the bridge
template. It is 8 to 15 s and has three scenes, the minimum of a clip: `done` names the viewer question
just answered (the first entry of the chapter's `answers`) as a label and draws a green check,
`sofar` speaks that question's answer in one sentence, and `next` brings the next chapter's
question in as the yellow label. A bridge has no cites, so its script's subject is
`{"text": <the movie's subject text>, "kind": "topic"}` whatever the movie's subject kind (the
frozen timeline check allows a cite-less scene only under `topic`; amended at wave 1 close). It
is a clip because the clip limits (60 s, text floor 19 px) fit a card better than the film
limits. For `ru`, the bridge script carries the `pronounce` map of `movie.json`. Each question
text, each answer and each chapter question is at most 20 words (the STE-80 sentence cap), which
keeps a bridge inside its 8 to 15 s.

The generated scene is TypeScript rendered through the same `scene` stage, so `tsc` and the
guard check the bridge text as they check any film.

### 4.5 `video.mp4`

The concatenation `chapters/c1 + bridges/1 + chapters/c2 + … + chapters/cN`. One H.264 video
stream, one AAC audio stream, 1280×720, as each part is. The length is the sum of the parts
within 0.5 s. `stitch` also writes `chapters.json`: for each chapter, its id, title and start
second in the movie. The mp4 has no chapter markers (D6).

### 4.6 `index.html`

The transcript hub, from `templates/movie.html`, written by `stitch` (never filled by hand). It holds a `<video>` of `video.mp4`, a
chapter list from `chapters.json` whose entries seek the video to the chapter start, the title,
the question, the viewer questions with their answers and cites, then one `<section>` per
chapter with the chapter's transcript body (the narration and the `div.cites` block of each
scene, copied from the chapter's `index.html`), and a link to the chapter's own transcript. It
passes `verify.sh` as a page: the meta is `<meta name="explain-rung" content="movie">`, and
`verify.sh` accepts that value. Provenance follows convention 2.

### 4.7 Printed lines

After the rung line: `review: on|off`, then one `chapter: <id> built|failed <reason>` line per
chapter as the subagents return, then the stage lines of `movie.py stitch`, then the viewer gate
lines of section 5, step 8, then the handoff.

## 5. The procedure (what `rungs/movie.md` says)

1. Resolve the subject. Read it in full, as the video rung does. Print the rung line and
   `review: on|off`.
2. Write the viewer questions first. Three to five questions a viewer must answer after the
   film, each with its answer and cites. This is the contract: a chapter exists only to make
   one of these answers visible.
3. Plan the chapters: the order of the picture, what each chapter opens on and ends with, and
   which questions it answers. Write `movie.json`. Run `movie.py check <dir>`. Fix each failure.
4. Stop. Print the plan as a list (one line per question, one per chapter with its question and
   length target), and wait for the user's approval. Build nothing before it. A resume skips
   this step when `state` is not `planned`.
5. Set `state` to `building`. Run `video-workspace.sh --engine <engine>` once. Start one
   chapter subagent per `pending` chapter, at most 3 at a time (D11), in the background, with
   `movie/chapter-task.md` filled. The subagent reads `SKILL.md`,
   `rungs/video.md` and the sections it names, builds the chapter in `chapters/<id>/`, runs
   `render.sh` until all eleven stage lines are `ok`, reads its own stills by section 6 of
   `video.md`, and returns one line: `chapter: <id> built` or `chapter: <id> failed <reason>`.
   Under `--review` the subagent also runs `movie/review-chapter.md` as its gate before the
   render, with the rounds and the `## Author` block of `lesson.md` section 6, and the open
   finding rule of D12. It writes the reports to `chapters/<id>/gate/` (not `review/`, which
   `render.sh` empties on every render; amended at wave 2). A narration that changes after the
   gate's last read (the length loop, a still fix) is not reviewed again; the chapter reply
   discloses it as `disputed: <id>: narration changed after the gate in <scenes>`, and every
   `disputed:` line carries its chapter id, so a rebuild can drop the chapter's stale entries
   from `not_covered` before it starts (amended at wave 2). Record each result
   in `movie.json`.
6. Run `movie.py bridges <dir>` and then `render.sh` on each bridge directory.
7. Run `movie.py stitch <dir>`. It refuses while any chapter is not `built`.
8. The viewer gate, always on. Start one fresh subagent with `movie/review-viewer.md`. It
   receives `review/viewer-transcript.html`, which `stitch` writes: the transcript without the
   viewer answers and without the `ask` and `answer` scenes of every chapter; one still per
   chapter, the `-end` still of the last body scene (D10); and the question texts. It must not
   read `movie.json`, any `script.json`, the chapter transcripts, the stills of other scenes,
   or the sources. It writes `review/viewer-round-<k>.md`: for each question, its
   answer in its own words or `cannot answer`, and what in the film it used. The author then
   compares each answer with `movie.json` and appends an `## Author` block: `understood`, or
   `missed: <what the film did not show>` with the chapter it fixes. A `missed` question sends
   its chapter back to step 5 with an amended brief, then steps 6 to 8 run again. Two rounds at
   most; after the second, a question still missed goes to `not_covered` as
   `viewer missed: <question>`.
9. `stitch` already wrote `index.html` at step 7. If `movie.json` changed after the gate (a
   `viewer missed` entry in `not_covered`), run `movie.py stitch <dir>` again (stream copy, a
   few seconds) so the hub carries it; never fill `movie.html` by hand. Run `verify.sh`. Set
   `state` to `stitched`.
10. Handoff: print the path, run `open video.mp4` when run for the user directly, print the
    narrator, and print `viewer: <n> of <m> understood`.

Costs, to be measured in the live run and folded back into `rungs/movie.md`: a chapter is a
film, so `video.md` "First-run costs" and the lesson numbers apply (about 5 lines of scene code
per second, 2 to 7 render runs per 40 s). The viewer gate is one subagent of about the size of a
gate-2 reviewer, once or twice.

## 6. `movie.py`

`python3 <skill-dir>/scripts/movie.py <command> <movie-dir>`. Stdlib only, as the other scripts.
Each command prints one line per check or stage, `<name>: ok …` or `<name>: FAIL <cause>`, and
exits 0 on all ok, 1 on a FAIL, 2 on usage or unreadable JSON. It follows the shape of
`course.py` and `onboard.py check`.

| Command | Does |
|---|---|
| `check` | Validates `movie.json` by 4.2, the `seconds` sum with the bridges budgeted (D7) and the 20-word caps of 4.4 included. When a chapter directory exists, also validates its `script.json` by 4.3 (`ask` first, `answer` last, title match, format `film`, the movie's root and lang). Prints `plan: ok (<q> questions, <c> chapters, <lo>..<hi> s with bridges)`. The module docstring of `movie.py` lists every printed line and is the source the drift test pins. |
| `bridges` | Writes `bridges/<n>/script.json` and `bridges/<n>/scene/` from the template for each gap. Prints `bridges: ok (<n>)`. Idempotent. |
| `stitch` | Refuses unless every chapter is `built` and every chapter and bridge has `video.mp4`. Probes each part: codecs, frame size, frame rate and audio sample rate must agree, else `parts: FAIL <part> <what> differs`. Writes `build/concat.txt`, runs the Remotion ffmpeg with the concat demuxer and stream copy, probes the result, writes `chapters.json`, `review/viewer-transcript.html` and the chapter transcript sections for `index.html`. Prints `parts: ok (<n>)`, `concat: ok (<s> s)`, `container: ok (<s> s)` and `length: ok (<s> s)` or `length: FAIL <s> s (min 240, max 900)`. |
| `status` | Prints one line per chapter with its status, and the state. For the resume. |

The ffmpeg binary is found as `check_render.sh` finds it: the Remotion CLI in
`<workspace>/app`, with `EXPLAIN_VIDEO_WORKSPACE` honoured.

## 7. Resume

`/explain <movie-dir> --as movie` on a directory holding `movie.json` resumes. `movie.py status`
tells the author what remains: `pending` and `failed` chapters go to step 5, a complete set goes
to step 6. The author never rebuilds a `built` chapter unless the viewer gate names it. After a
run that stopped between round 1's `## Author` block and the rebuilds, a chapter a `missed:` line
names is rebuilt only when its `video.mp4` is older than that round's report (amended at wave 2).

## 8. Tests

- `test_movie.py`: `check` on fixtures (a good plan; a question no chapter answers; a chapter
  with three answers; a chapter without `ask`/`answer`; wrong count of chapters; a `seconds`
  sum out of range; a duplicate id), `bridges` output shape and its `pronounce` copy for `ru`,
  `stitch` refusal when a chapter is not built, the `chapters.json` and the viewer transcript
  for a three-chapter fixture. The concat run itself is in the gated E2E.
- `test_movie_prompts.py`: each `{name}` of the three prompt files has a fill in the rung's table,
  as `test_course_prompts.py` does.
- `test_rung_drift.py`: a `MovieRungCase` that pins the rung's level-2 titles, the `movie.py`
  lines it quotes to the code that prints them, and the `--as` list of `SKILL.md`, `README.md`
  and the argument-hint.
- `test_movie_e2e.py` under `EXPLAIN_VIDEO_E2E=1`: two tiny real chapters (the film template
  cut to 3 scenes each, with `ask` and `answer`), one bridge, `stitch`, then a probe of the mp4
  for the summed length, and `verify.sh` on the hub.
- `test_verify.py`: the `movie` rung value and the `chapters/` media count.

## 9. Left to the builder

- The exact bridge picture and its narration wording, within 4.4.
- The look of `templates/movie.html`, following `page.html`'s palette and the cite block rule.
- The concat file format (documented by ffmpeg).
- The word budget per chapter the rung recommends, to be set from the live run.
