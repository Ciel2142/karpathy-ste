# Rung: movie
This file holds only what is specific to the movie rung. `SKILL.md` has the generic rules.

## 1. When a movie

A movie is one theme as one continuous film of 4 to 15 minutes. The viewer watches it from start
to end and reads nothing. Bridges cut the film into 4 to 10 chapters. A chapter is a film of
`rungs/video.md`. A bridge is a short generated clip between two chapters. It shows the question
that the chapter before it answered, and the question of the next chapter.

Before any script, you write the questions that a viewer must answer after the film. After the
render, a cold viewer answers them from the film alone. A cold viewer is a fresh subagent that did
not make the film. This viewer gate is always on. It tests if a viewer can understand the theme
from the film, not only if each claim is true.

Use a movie only when the user writes `--as movie`. Never choose it from the content.

The command is `/explain <subject> --as movie [--review]`. The subject is a topic, a file or a
directory, by the rules of "Subject resolution" in `SKILL.md`. If the subject is a conversation,
print the rung line. Say that the movie rung takes no conversation subject. Stop. Offer `video`.

If the subject is one directory that holds `movie.json`, the run is a resume: go to "Resume".

You are the orchestrator. Keep your own context small. The chapter subagents build the chapters. A
chapter comes back to you as files and one result line. Never read a whole chapter: its
`script.json`, its scene code or its transcript. The scene code of many chapters does not fit in
one context.

In this file, `movie.py <command>` is short for `python3 <skill-dir>/scripts/movie.py <command>`.
Each command takes `<movie-dir>`, the output directory of the movie ("Plan the chapters" makes it).

Start each subagent in the background. In Claude Code, use the Agent tool. In OpenCode, use the
`task` tool with the `general` agent.

The movie has one language for all its chapters and bridges: `lang` in `movie.json`. Use `en`, or
`ru` when the user asks for Russian. If the user asks for another language, print the rung line.
Say that the movie rung is English or Russian. Stop. Offer `page`.

`--review` adds a fact gate to each chapter. Each chapter subagent runs that gate itself, before
its first render ("Build the chapters"). The viewer gate runs also without `--review`. Print
`review: on` or `review: off` after the rung line.

Print the rung line as `SKILL.md` says. `<kind>` is `topic`, `file` or `directory`:

```
Rung: movie (forced) — <reason> — subject: <subject> (<kind>)
```

For example, for a topic:

```
Rung: movie (forced) — --as movie; a hash map lookup is a sequence of steps — subject: hash map lookup (topic)
```

After the rung line and the `review` line, print one result line for each chapter as its subagent
returns. Then print the lines of `movie.py stitch`, then the lines of the viewer gate, and then the
handoff.

### Edit the plan

No command of `movie.py` writes `movie.json`. You write it. Change it with the Edit tool, one field
at a time. After each edit, run `movie.py check <movie-dir>`. Thus each failure line comes from one
edit.

Each text that you put in `movie.json` is a JSON string between two `"`. Escape each text before
you put it there:

1. Write each `\` of the text as `\\`.
2. Then write each `"` of the text as `\"`.

A `reason` or a `disputed:` line can quote a script line. A `"` without its `\` ends the string
early, and `movie.json` is then not valid JSON.

If `check` exits with 2 after an edit, that edit broke the JSON. `check` then prints no failure
line. Undo the edit. Make it again, with the text escaped. After the user approves the plan, never
write the whole file again: it holds the `status` and the `reason` of each chapter.

## 2. Write the viewer questions

The viewer questions are the contract of the movie. A chapter exists only to make one of these
answers visible. Write them first, before you plan a chapter and before any script. A film without
such a contract stops when its script feels complete. Nothing then asks if a viewer can answer the
question of the theme.

1. Resolve the subject by "Subject resolution" in `SKILL.md`, as for a video. Read it in full before
   you write a question. A question that comes before the reading can ask the wrong thing.
   - Read a file subject in full.
   - Map a directory: its tree and its key files.
   - For a topic about the code of the current repository, read that code first.
   - For another topic, use your own knowledge and the web.
2. Write three to five questions that a viewer must answer after the film. Each question asks one
   thing. Its `text` has at most 20 words.
3. For each question, write its `answer`: one sentence of at most 20 words. It is the answer that a
   viewer must give after the film. A bridge speaks the question and its answer. The limit of 20
   words keeps a bridge within 8 to 15 s.
4. Write each answer so that the picture and the narration of a chapter can show it. The cold viewer
   sees the film only. The viewer cannot give an answer that the film does not show.
5. Give each question its `cites`. A cite has a `path` relative to `provenance.root`, a `line` from 1,
   and a `snippet`. The snippet has at most 12 words, copied verbatim from that line. Read each cited
   line from the disk. Never type a cite from memory.
6. A URL cite has the URL as its `path` and no `line`. Its snippet comes from the fetched page.
7. For a `file` or a `directory` subject, give each question at least one cite. For a topic without
   files, the cites are URLs, or the question has `"cites": []`.

## 3. Plan the chapters

Plan the chapters in the order in which the picture grows. The first chapter draws the start of the
picture. Each next chapter opens on the end picture of the chapter before it. It changes that picture
to answer its questions.

1. Make the output directory `~/karpathy/out/YYYY-MM-DD-HHMMSS-movie-<slug>/` by convention 5 of
   `SKILL.md`. In this file, `<movie-dir>` is that directory.
2. Write 4 to 10 chapters, in the order of the film.
3. For each chapter, write `picture`: what is on the stage when the chapter opens.
4. For each chapter, write `ends_with`: what is on the stage at the last frame of the chapter.
5. Start the `picture` of each chapter from the `ends_with` of the chapter before it. No object stays
   across the cut between two chapters. Thus the next chapter subagent gets the end picture in words.
6. For each chapter, write `answers`: the ids of the one or two questions that the chapter answers.
   Each question is in the `answers` of at least one chapter. The `answer` scene of a chapter states
   each of its answers in at most 45 words. Thus a chapter answers at most two questions.
7. For each chapter, write `seconds`: its length target, from 30 to 150 s.
8. Count the bridges: one in each gap between two chapters. A bridge is 8 to 15 s. The sum of
   `seconds` plus 8 s for each bridge must be at least 240 s. The sum plus 15 s for each bridge
   must be at most 900 s.
9. Write `<movie-dir>/movie.json`.

This is the shape of `movie.json`, version 1. The example has two questions and two chapters. A
real plan has 3 to 5 questions and 4 to 10 chapters.

```json
{
  "version": 1,
  "title": "How a hash map finds a key",
  "question": "How does a hash map find the value of a key without a search of all keys?",
  "lang": "en",
  "pronounce": {},
  "review": false,
  "subject": {"text": "hash map lookup", "kind": "topic"},
  "provenance": {
    "root": "/Users/me/work",
    "commit": "none",
    "dirty": "no",
    "date": "2026-11-04",
    "source": "model knowledge",
    "not_covered": "none"
  },
  "state": "planned",
  "questions": [
    {
      "id": "q-bucket",
      "text": "Where does a key go in the map?",
      "answer": "The hash of the key picks one bucket of the array.",
      "cites": []
    },
    {
      "id": "q-share",
      "text": "What happens when two keys get the same bucket?",
      "answer": "The bucket keeps both keys in a short list, and a lookup walks that list.",
      "cites": []
    }
  ],
  "chapters": [
    {
      "id": "buckets",
      "title": "The buckets",
      "question": "Where does a key go?",
      "answers": ["q-bucket"],
      "seconds": 70,
      "picture": "A row of eight empty buckets, as grey boxes.",
      "ends_with": "The key cat sits in bucket 3, with a yellow arrow from its hash.",
      "status": "pending",
      "reason": ""
    },
    {
      "id": "share",
      "title": "Two keys in one bucket",
      "question": "What if a second key gets bucket 3?",
      "answers": ["q-share"],
      "seconds": 80,
      "picture": "The row of eight buckets, with the key cat in bucket 3.",
      "ends_with": "Bucket 3 holds a list of two keys: cat and dog.",
      "status": "pending",
      "reason": ""
    }
  ]
}
```

Write the fields by these rules:

- `version`: `1`.
- Ids: each `id` of a question or a chapter matches `[a-z0-9][a-z0-9-]*`. Each id is unique among
  the questions and the chapters.
- Prose: `title`, `question`, the `text` and the `answer` of a question, the `title`, `question`,
  `picture` and `ends_with` of a chapter, and `not_covered`. The hub and the bridges show this
  prose, and `check` lints it. Write it under the STE profile, or under convention 7 for `ru`.
- `question`: the question of the whole theme, in one sentence. The `question` of a chapter has at
  most 20 words. Its `ask` scene speaks it, and the bridge before it shows it.
- `lang`: `en`, or `ru` when the user asks for Russian.
- `pronounce`: `{}` for `en`. For `ru`, the map of `rungs/video.md` "Write the script". The
  `movie.py bridges` command copies it into each bridge script.
- `review`: `true` under `--review`, else `false`.
- `subject`: `text` is the subject as the user typed it. `kind` is `topic`, `file` or `directory`.
- `provenance`: get the values with "Provenance recipe" in `<skill-dir>/rungs/sheet.md`.
  - `root`: the absolute path of the repo root, or of the directory that the recipe names when git
    fails. Never write a relative path.
  - `commit`: the short commit hash, or `none`.
  - `dirty`: `dirty` or `no`.
  - `date`: the date as `YYYY-MM-DD`.
  - `source`: the files or the repo root that you read, `model knowledge`, or the URLs that you read.
  - `not_covered`: `none`, or one sentence for each facet that the movie does not explain.
- `state`: `planned`.
- `status` of each chapter: `pending`. `reason` of each chapter: an empty string, `""`.

## 4. Check and stop

1. Run this command:

```
python3 <skill-dir>/scripts/movie.py check <movie-dir>
```

2. Read its output. It prints one failure on each line. Its last line is
   `plan: ok (<q> questions, <c> chapters, <lo>..<hi> s with bridges)` or `plan: <n> failures`.
   `<lo>` is the length of the movie with each bridge at 8 s, and `<hi>` with each bridge at 15 s.
3. If `check` exits with 2, it cannot read `movie.json`: the file does not exist, or it is not
   valid JSON. After an edit, do as "Edit the plan" says. Before the first edit, write the file
   again.
4. Fix `movie.json` for each failure line. The table below tells where each fault is. Then run
   `check` again. Repeat until it exits with 0, or until the stop rule below applies.
5. Print the plan as a list, in the form below. Then print the last line of `check`.

```
Movie: <title>
Question: <question>
Viewer questions:
- <question-id>: <text>
Chapters:
- <chapter-id> (<seconds> s): <question> (answers: <question-id>, <question-id>)
```

6. Stop. Ask the user to approve the plan, or to say what to change. Build nothing before the user
   approves the plan.
7. For each change that the user asks for, edit `movie.json`. Then do steps 1 to 6 again.
8. When the user approves the plan, go to "Build the chapters".

A resume skips steps 5 to 8 when `state` is not `planned`. The user approved that plan in an
earlier run, and "Resume" tells where the run continues.

The prefix of a failure line tells where the fault is:

| Prefix | Fix |
|---|---|
| `schema:` | The field that the line names: a key that is missing, a value of the wrong type, the number of questions or chapters, or `lang`. For `schema: seconds sum <s>, <lo>..<hi> s with bridges (min 240, max 900)`: if `<lo>` is below 240, increase the `seconds` of some chapters, or add a chapter. If `<hi>` is above 900, decrease the `seconds` of some chapters, or remove a chapter. |
| `id:` | Two items have one id. Give the second item a new id. Change each `answers` entry that names it. |
| `question <id>:` | That question. For `question <id>: text has <n> words (max 20)` or `question <id>: answer has <n> words (max 20)`, write a shorter sentence. For `question <id>: cite <n> needs path, line and snippet` or `question <id>: cite <n> needs path and snippet`, complete cite `<n>`. For a line that says that no chapter answers the question, put its id in the `answers` of a chapter. |
| `chapter <id>:` | That chapter: its fields, its `seconds`, its `answers` or its `question`. For `chapter <id>: question has <n> words (max 20)`, write a shorter question. A line that names the script, a scene, `format`, `root` or `lang` comes from `chapters/<id>/script.json`. The chapter subagent writes that file, not you ("Build the chapters"). |
| `cite <question-id>#<n>:` | Cite number `<n>` of that question: its path, its line or its snippet. Read the line again from the disk. Copy the snippet from it. |
| `prose:` | The prose field that the line names. Write it again under the STE profile, or under convention 7 for `ru`. |
| `state:` | The `state` value. Set it to `planned` before the approval of the user, or to `building` after it. Only "Verify and handoff" sets `stitched`, when each chapter is `built`. |

### The stop rule

Some faults are not in `movie.json`, and an edit of `movie.json` cannot fix them. Examples:

- a `prose:` line about `ste_lint.py` itself, not about a field: the linter does not exist, or it
  fails;
- a `chapter <id>:` line about `chapters/<id>/script.json` of a chapter that is `built`.

Stop a fix loop after 3 rounds in which the same failure lines come back. Also stop it at once for a
fault that is not in `movie.json`. This rule applies to each fix loop of this file. Then print each
line that remains, and what it means. Stop the run. Do not change `state`: a resume continues from
it.

## 5. Build the chapters

Start this section only after the user approves the plan, or on a resume.

1. Set `state` to `building` in `movie.json`. Run `movie.py check <movie-dir>`. The state
   `building` records the approval of the user. Thus a resume does not stop for the approval again.
   On a resume with `state` `building`, skip this step.
2. Find the engine from `lang`, as in `rungs/video.md`: `kokoro` for `en`, and `silero` for `ru`.
3. The chapters share one video workspace, and a first install must not run two times. Thus, before
   the first chapter subagent starts, set up the workspace once yourself. Run this command:

```
<skill-dir>/scripts/video-workspace.sh --engine <engine>
```

4. Read its last line. It is `workspace: ok <ws>` or `workspace: FAIL <step> …`. On a
   `workspace: FAIL` line, print that line. Stop the run. This is a fault of the environment.
   Change no chapter. A resume continues.

At most 3 chapter subagents run at the same time. The renders and the narration share one computer.
A chapter stays `pending` while its subagent runs: `movie.json` has no status for a running chapter.
Thus keep a list of the chapters whose subagents run now. Do this loop:

1. Find the `pending` chapters in `movie.json`, in the order of the plan. Skip each chapter whose
   subagent runs now.
2. Count the free slots: 3, less the number of chapter subagents that run now.
3. For each chapter that remains, up to the number of free slots, do steps 4 and 5.
4. If `<movie-dir>/chapters/<id>/` exists, move it to `chapters/<id>.stale-<n>/`. `<n>` is the first
   number from 1 that no directory has. An earlier build stopped in that directory, and a new build
   starts in an empty one. Never delete a chapter directory.
5. Fill `<skill-dir>/movie/chapter-task.md` as the table at the end of this section says. Start the
   chapter subagent with the result, in the background.
6. When a chapter subagent returns, read only the last line of its reply. It is
   `chapter: <id> built` or `chapter: <id> failed <reason>`. Print it.
7. For `chapter: <id> built`, set `status` to `built` and `reason` to `""` in `movie.json`.
8. For `chapter: <id> failed <reason>`, set `status` to `failed` and `reason` to `<reason>`.
   Escape `<reason>` as "Edit the plan" says.
9. If the last line is not one of these two lines, set `status` to `failed` and `reason` to
   `no result line`.
10. If the reply holds `disputed:` lines before its last line, write them into `movie.json`, as "The
    chapter gate" below says.
11. Run `movie.py check <movie-dir>` after each edit. If it exits with 2, the edit broke the JSON.
    Undo the edit. Make it again, with the text escaped ("Edit the plan"). Never write the whole file
    again in the build. Fix each failure line about the field that you changed.
12. Go to step 1. Stop the loop when no chapter is `pending` and no chapter subagent runs.

Never read the files of a chapter directory. The chapter subagent checks its own render and its
own stills. In the loop, `check` also reads the `script.json` of each chapter directory. A
`chapter <id>:` line that names the script, a scene, `format`, `root` or `lang` comes from that
file. Leave such a line while its subagent runs, or when its chapter is `failed`. Never edit a
`script.json` yourself.

A chapter subagent that does not return stops the run. The harness reports an error or a stop, and
no reply comes. Then do these steps:

1. Let the other chapter subagents that run now finish. Record their lines.
2. Start no new chapter.
3. Print the id of the chapter and the path of `<movie-dir>`. Stop.
4. Do not change the `status` of that chapter. It stays `pending`, and a resume builds it again.

A resume builds only the chapters that are not `built`. Never build a `built` chapter again, unless
the viewer gate names it.

A fault of the environment also stops the run. If a `reason` names a `workspace`, `narration` or
`container` `FAIL`, the next chapters fail too. Then do these steps:

1. Let the chapter subagents that run now finish. Record their lines.
2. Start no new chapter.
3. Print the line. Stop the run. A resume continues.

When the loop stops, look at the `status` of each chapter. If each chapter is `built`, go to
"Bridges". If a chapter is `failed`, the movie cannot stitch, because `movie.py stitch` refuses a
chapter that is not `built`. Print the line of each `failed` chapter. Stop the run. A resume
builds the failed chapters again.

The prompt `chapter-task.md` is a template. Read it. Replace each name in braces with plain text.
Give the result to the subagent as its prompt. Fill its names as the table below says.

| Name | Fill with |
|---|---|

### The chapter gate

Under `--review`, each chapter subagent also runs the chapter gate before its first render. You
start no reviewer for a chapter. The subagent writes the reports of the gate to
`chapters/<id>/review/`.

A finding that stays open after the last round of the gate does not stop the chapter. The chapter
ships: it is `built`. A chapter is never dropped, because it answers a viewer question. Before its
last line, the reply holds one `disputed: <finding>` line for each such finding.

Write each `disputed:` line into `provenance.not_covered`:

1. Escape the line as "Edit the plan" says. A finding often quotes the narration.
2. If `not_covered` is `none`, replace `none` with the line. Else add the line at the end, after one
   space.
3. End the line with a period.
4. Run `movie.py check <movie-dir>`. If it exits with 2, the edit broke the JSON. Undo the edit. Do
   steps 1 to 3 again. Never write the whole file again in the build.
5. For a `prose:` line about `provenance.not_covered`, write the finding again under the STE profile.
   Keep the `disputed:` start.

## 6. Bridges

Task 2 writes this section.

## 7. Stitch

Task 2 writes this section.

## 8. The viewer gate

Task 2 writes this section.

## 9. Verify and handoff

Task 2 writes this section.

## 10. Resume

Task 2 writes this section.

## 11. Output directory

Task 2 writes this section.

## 12. Costs

Task 2 writes this section.
