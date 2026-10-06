# Explain in Russian: the live run

Date: 2026-10-06. Branch `worktree-explain-russian` at `6805eac`. This is the record of Task 10 of
`docs/superpowers/plans/2026-10-06-explain-russian.md` (spec §7.4).

## Result

- The full non-gated suite: `Ran 930 tests`, `OK (skipped=45)` (813 at the base). The log has no
  warning and no traceback.
- The English regressions: gated `test_render_film` and `test_lesson_e2e` give `Ran 55 tests`, `OK`
  (274 s). Gated `test_render_brainrot` gives `Ran 13 tests`, `OK` (102 s). The plan named only the
  first two. The final review found the gap, and the third run closes it.
- The Russian film and the Russian lesson both render with Silero `xenia`, with no `FAIL` line, no
  `FALLBACK` line and no guard line.
- User verdict: accepted ("sounds good", 2026-10-06), after both outputs were opened for them.

All renders used `EXPLAIN_VIDEO_WORKSPACE=/Users/valukin/karpathy-wt/russian-workspace` and ran
`render.sh` with no `--engine` option, so the engine came from `"lang": "ru"` through
`narrate.py --check`. The first Russian render downloaded `v5_3_ru.pt` into that workspace.

## How the runs were made

Each artifact had a fresh author subagent. The request was in Russian, and the operator notes were
in English, as in the English film run. The lesson rung makes its author start the gate reviewers.
The author could not start subagents, so it wrote each filled prompt to `review/prompts/`. Then it
stopped with a `GATE REQUEST`, and the operator session started the reviewers. The operator session
also checked the stage lines, the `lang` attribute and the Narrator rows of each output.

## Film: `ImportController.java`

Request: `/explain /Users/valukin/work/inavcalculator/src/main/java/ru/aton/esb/microservices/inavcalculator/web/ImportController.java --as video`,
then "Сделай, пожалуйста, видео на русском языке: объясни, как работает этот контроллер."

Output: `~/karpathy/out/2026-10-06-185822-video-importcontroller/`. 10 scenes, 181 words, 82.9 s.
The speech is 76.8 s, so `xenia` spoke 2.36 words a second.

| Run | Exit | First FAIL line | Cause of the run |
|---|---|---|---|
| 1 | 0 | none | The first build. It also downloaded the Silero model. |
| 2 | 0 | none | A stills fix: the picture said that some error answers skip `buildSignedResponse`. |
| 3 | 0 | none | The footer showed the backticks of `provenance.not_covered` as text. The narration did not change, so each WAV was reused. |

The stage lines of run 3:

```
script: ok (10 scenes)
workspace: ok /Users/valukin/karpathy-wt/russian-workspace
scene: ok (2 files)
narration (silero): ok
timeline (10 scenes, 82.9 s): ok
guard (31 frames): ok
render (23.2 s, 0.28 render-min/video-min): ok
container: ok (82.94 s)
sync: ok
stills (31): ok /Users/valukin/karpathy/out/2026-10-06-185822-video-importcontroller/review
transcript: ok
```

Narrator row: `silero (xenia)`. `index.html` has `<html lang="ru">`.

## Lesson: `narrate.py`

Request: `/explain /Users/valukin/karpathy/.claude/worktrees/explain-russian/skills/explain/video/narrate.py --as lesson`,
then "Сделай урок на русском языке с двумя роликами: объясни, как `narrate.py` превращает сценарий в озвучку."

Output: `~/karpathy/out/2026-10-06-185309-lesson-narrate/`. 8 sections; two clips, both shipped.

| Clip | Length | Narration line | Narrator row |
|---|---|---|---|
| `path` | 30.7 s | `narration (silero): ok` | `silero (xenia)` |
| `timing` | 37.0 s | `narration (silero): ok` | `silero (xenia)` |

`path` rendered alone until its `narration (silero): ok` line, then `timing` rendered. No render run
failed. `verify.sh index.html` printed six `ok` lines (self-contained, the two renders, citations,
prose, media). The page and the two clip transcripts have `lang="ru"`.

The gates used 21 reviewers. Gate 1 took three rounds: 3 findings in round 1, 6 new findings in
round 2, then three verification reads with `verdict: ok`. Gate 2 took two rounds: 3 findings on
`timing` in round 1 (fixed with two cites and one render), then four reads with `verdict: ok`. All
12 findings were fixed and ruled `resolved`. Disputed findings: none.

## What the authors found in the Russian instructions

These are inputs for a follow-up. The code does what the spec says in each case.

1. `title` and `provenance.not_covered` print backticks as text, and the lint does not catch it.
   Convention 7 says that an English term goes in backticks in a video script.
2. The interface text of a Russian page stays English: headings and labels of the transcript,
   `Play all`, `Part k of N`, `transcript`, the provenance labels and `Not covered:`.
3. `rungs/video.md` does not say that `pronounce` keys are case-sensitive, or that a word mark
   matches the written token and not the spoken one.
4. Convention 7 says that the lint reports a bare English word in the prose. The lint reports only
   the words of its substitution table.
5. The clip rule "muted text at 22 px or more" conflicts with the muted line numbers of the code
   card. At 22 px, long source lines are cut with `…`.
6. The propagation rule of the lesson does not say what a script reviewer checks again when its
   section changed and its last report had no finding.
7. The session guard of a worktree session refuses Write and Edit outside the worktree, so an
   author or reviewer writes `~/karpathy/out/` through a shell. This is a fact of the machine, not of
   the skill.

The final review also left two guard cases for the user to decide, both literal to spec §4.4 rule 3:
an abbreviation before a sentence that starts with code (`напр. ` then a backticked name) passes,
and a `...` or a `?` before a lower-case sentence gets the abbreviation line.

## User verdict

The operator opened the film and the lesson for the user and listed the two guard cases above and
the seven findings. The user answered "sounds good" (2026-10-06). The guard cases and the findings
stay as follow-up input. This run changed no code for them.
