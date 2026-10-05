# Explain film: the two live runs

Date: 2026-10-05. Branch `feat/explain-film` at `a35fc9d`. This is the record of spec §9.3.

## Result

- Both films render with eleven `ok` lines, and a fresh judge reports no open fault on the final
  stills of each.
- No stage of the pipeline failed on a first build. In eleven `render.sh` runs the only FAIL line
  was a `tsc` unused import, made during a fix.
- The guard never failed. No guard fault without an honest fix was seen, so there is no evidence
  for an exemption (D6).
- The cold run did not pass the limit of two fix rounds. Its author stopped after two fix rounds
  with a clean pipeline, but the judge then found three faults of type 2 that were true against
  the source. Two more fix rounds removed them. The long run has the same pattern.
- The user watched both films and accepted them on 2026-10-05.

## How the runs were made

Each author was a fresh general-purpose subagent. It got the command line, the path of the
skill, and these notes about the machine, which the spec does not name:

- Prefix each `render.sh` call with `EXPLAIN_VIDEO_WORKSPACE=/Users/valukin/karpathy-wt/film-workspace`.
  The wave map says that a film-branch render uses its own workspace.
- Run long commands in the foreground. Read at most 4 images in one tool round. Ask no question.
  Do not edit the skill and do not commit.
- At the end, report each `render.sh` run with its exit code and its first FAIL line.

The long run also got the sentence "Make the film come near 150 seconds."

Each judge was a fresh subagent that got the path of the stills, the path of `narration.md` and
the five faults of spec §8.4. It was told not to read any other file. The second judge of each
film was a new subagent, not the first one.

The operator session checked the three likely findings of the first cold judge against
`ImportController.java` before it sent them to the author. All three were true.

## Cold run: `ImportController.java`

Command: `/explain /Users/valukin/work/inavcalculator/src/main/java/ru/aton/esb/microservices/inavcalculator/web/ImportController.java --as video`

Output: `~/karpathy/out/2026-10-05-192833-video-importcontroller/`. The film has 13 scenes, 239
words and 96.3 s, with Kokoro `af_heart` and no fallback. The scene code is 661 lines in 3 files
(`Film.tsx`, `Routes.tsx`, `Token.tsx`; 599 lines when the judge first read it). There are 39
stills.

| Run | Exit | First FAIL line | Cause of the run |
|---|---|---|---|
| 1 | 0 | none | First build. |
| 2 | 0 | none | Fix round 1, from the author's own stills review: a status label alone between the lanes, lanes that ended in empty space, answers that were too dim, a label on the place where the card waits. |
| 3 | 0 | none | Fix round 2, from the author: the card showed `fund` before it passed the JSON gate. |
| 4 | 0 | none | Fix round 3, from the judge's findings. |
| 5 | 0 | none | Fix round 4, from the author's review of run 4: status labels that almost touched, and steps that looked like gates. |

Each run printed eleven `ok` lines. The logs are in `.ralph/ops/live-run/cold/` of the film
worktree (not in git). The author needed 16 minutes for runs 1 to 3 and 15 minutes for runs 4
and 5.

### Judge, on run 3

Verdict: open faults 3, all of type 2 and all "likely". Eight more were "unsure".

1. Scene `store`: the narration says that the route converts the fund and gives it to the fund
   manager. The signed route had no convert step, and the `bytes` card disappeared after the
   JSON gate. The source converts on line 96 and stores on line 98.
2. Scene `sign`: the narration says that the controller signs each answer of the signed route.
   The answer line started at the fund manager, so only the success passed `sign`. In the source
   each rejection returns through `buildSignedResponse` (lines 60, 65, 73, 80 and 92).
3. Scene `length`: the gate measures the signature, but the `signature` label stayed white. Each
   later gate made the text that it examines cyan.

Faults 1, 3 and 4 of the list: none. The judge said that one picture carries through the film.

### Judge, on run 5

Verdict: no open fault. Four findings were "unsure": a `convert` box that is on the signed route
before the narration names it, `FundException` shown with no status number, the condition "if a
crypto provider is present" with no picture, and request headers in lower case against response
headers in upper case. The judge said that the smallest text (header labels, the grey `HTTP`
lines, the path under the code card) is the first thing that a reader loses.

The author left one "unsure" finding of the first judge as it was: a green check on a gate with
a red failure status under it. Each gate uses this convention.

## Long run: `skills/explain/`

Command: `/explain /Users/valukin/karpathy-wt/film/skills/explain/ --as video`, with "Make the
film come near 150 seconds."

Output: `~/karpathy/out/2026-10-05-192733-video-explain/`. The film has 21 scenes, 411 words and
148.9 s, with Kokoro `af_heart` and no fallback.

| Run | Exit | First FAIL line | Length | Cause of the run |
|---|---|---|---|---|
| 1 | 0 | none | 133.9 s | First build: 20 scenes, 369 words. |
| 2 | 0 | none | 145.7 s | Fix round 1: one more scene, longer narration in two scenes, layout fixes. 405 words. |
| 3 | 0 | none | 149.0 s | Fix round 2: `pause` on six scenes, 99 more frames. |
| 4 | 1 | `scene: FAIL tsc: scene/Output.tsx(5,10): error TS6133: 'C' is declared but its value is never read.` | none | Fix round 3, from the judge's findings. An import was left unused. |
| 5 | 0 | none | 148.9 s | The unused import removed. |
| 6 | 0 | none | 148.9 s | A still of run 5 showed a file name half typed (`film-script.js`). The name now types earlier. |

The stage lines of each run are in `.ralph/ops/live-run/long/stage-lines-from-transcript.txt` of
the film worktree, copied from the transcript of the author.

### What a long film costs

| Measure | At run 3 | At run 6 |
|---|---|---|
| Lines of scene code (`wc -l scene/*`, with the 5 lines of the copied `script.gen.ts`) | 875 in 8 files | 967 in 9 files |
| Stills | 62 | 62 |
| `render.sh` runs | 3 | 6 |
| Time of the author | 24 minutes | 37 minutes |
| Render stage | 29.9 s (0.20 render-min/video-min) | 28.3 s (0.19) |

### Judge, on run 3

Verdict: open faults 2, both "likely". Six more were "unsure".

1. Scene `ladder`: the narration said "from chat text to a narrated video", but the row of rungs
   ends on `brainrot`.
2. Scene `output`: `SKILL.md` and its line to the prompt were lit again for one scene. The author
   confirmed that the light was not intended.

The judge also said that grey captions of about 15 px cannot be read quickly, and that the frame
is dense from scene 15 on.

### Judge, on run 6

Verdict: no open fault. Six findings were "unsure", most of them a clause of the narration with
no picture ("and changes it", "it stops at the first failure", "with the narration and the
citations"). The smallest text is now about 15 to 16 px, "readable but small". Scenes 1 to 4 use
only the top left corner of the frame.

## Measured values

| Value | Cold film | Long film |
|---|---|---|
| Words | 239 | 411 |
| Speech (sum of the clips) | 88.2 s | 135.2 s |
| Words each second of speech | 2.71 | 3.04 |
| Most words in one scene (limit 45) | 28 | 28 |
| Scenes (limit 30) | 13 | 21 |
| Source ranges, lines (limit 20) | 3 and 5 | 1 |
| `pause` keys | none | one, 36 frames |
| `sync` on the default pause | ok | ok |
| Guard frames, guard faults | 39, none | 62, none |

The cold film says many numbers ("status minus 201"), and it is slower.

## Fold-back

| Value of spec §9.3 | Change | Reason |
|---|---|---|
| The `film` row of `formats.json` | None | No run came near a limit except the total length, and the long film of 148.9 s rendered in 28 s with no fault. |
| `MIN_TEXT` | None in the code. `video.md` now says that a dim caption needs 16 px or more. | The guard never failed, so 14 px did not stop an author. But each of the three judges that spoke of text size said that grey text of 13 to 15 px is lost first. The long author changed its captions to 16 to 18 px. A larger limit is a decision for the user after the user watches the films. |
| The frames checked in each scene | No change of the rule. `video.md` has three new rules for the middle frame. | The rule found a half-typed name (long run 5). It did not show a light that moved and left (long run 1), and the author had to time it again. Both are faults of the picture, not of the rule. |
| The length guidance of `video.md` | The measured speeds, the length of a 350-word film, and a procedure to come near a length. | 2.8 words each second is the middle of the two runs. The file had no procedure: the long author found `pause` alone, and went from 133.9 s to 149.0 s in two runs. |
| A guard fault with no honest fix (D6) | None seen. | 101 guard frames in the two final runs and no fault. |
| Spec §7.1 | The measured tail margin of a Kokoro clip. | Wave film-render measured 0.70 s. The 34 scenes of the live runs passed `sync` on the default pause. |
| Spec §7.3 | The guard command with ranges of one frame, and the copy of the clips. | Found in wave film-guard; the spec still showed the list of bare frames. |

Other changes in `rungs/video.md`, each from a gap that an author reported:

- Section 6 has five checks for fault 2: a sentence with no object, an object that disappears, a
  mark that is not the same in each scene, a light with no cause, and a list in a different
  order. Each is a fault that an author missed and a judge found.
- Section 6 says which stills to read again after a fix.
- Section 4 says to delete the files of the example that the picture does not use, and that the
  copied `script.gen.ts` holds the ids of the example.
- The code card section gives the height of a row and of a card. Both authors needed the bottom
  of a card.
- The marks section gives a motion budget in frames.
- Section 3 says that the limit of 20 words is smaller than the limit of the STE profile, how to
  write a number for the voice, and that `provenance.source` can be a list of files, as in the
  template.

## Gaps that are not fixed here

These are outside the files of this wave, or they need a decision:

- `SKILL.md` convention 5 gives `~/karpathy/out/` and `README.md` gives `<clone>/out/`. From a
  worktree the two are different directories.
- The `dirty` field is `yes` when `git status --porcelain` prints an untracked directory outside
  the subject.
- No rule says how a subagent "prints" the rung line and the handoff.
- No rule says if a long absolute subject path can be shown shorter on the stage.
- The import check of `check_scene.py` matches the word `from` or `import` before a quote in any
  place, not only in a string as `video.md` says.
- `Mono` with `anchor="middle"` and a `Draw` path closed with `Z` work, but `video.md` does not
  say so.

## What worked

- Each first build passed all eleven stages. The cold author read only the skill.
- The scene check, `tsc` and the guard stopped nothing that was correct.
- Both films are one picture that changes, in the words of each of the four judges.

## Acceptance

Accepted. The user watched both films on 2026-10-05 and said "looks good". The user named
nothing to change. On the cost of a film the user said: "it's fine for now, if it's going to be
too much, we will deal with it later".

- `~/karpathy/out/2026-10-05-192833-video-importcontroller/video.mp4`
- `~/karpathy/out/2026-10-05-192733-video-explain/video.mp4`

The films as the first judges read them are in `.ralph/ops/live-run/{cold,long}/run3-as-judged/`
of the film worktree.
