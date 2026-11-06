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

After the rung line and the `review` line, print the lines of each chapter as its subagent returns.
Step 6 of the loop of "Build the chapters" names them. Then print the lines of `movie.py stitch`,
then the lines of the viewer gate, and then the handoff.

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

Before you build a chapter again, remove its `disputed:` entries from `provenance.not_covered`. The
new build writes again each entry that still holds. Do these steps:

1. Find each entry of the chapter. An entry of chapter `<id>` starts with `disputed: <id>:`. It ends
   before the next `disputed:` or `viewer missed:` entry, or at the end of `not_covered`.
2. Remove the entry and one space next to it. Make one edit for each entry.
3. If no text remains, write `none`.
4. Run `movie.py check <movie-dir>` after each edit.

### When the run stops

The run stops for the approval of the plan, at a fault, or by the stop rule of "Check and stop".
Each time the run stops, print these two lines last:

```
<movie-dir>
/explain <movie-dir> --as movie
```

The first line is the absolute path of `<movie-dir>`. The second line is the command that resumes
the movie ("Resume"). The user can type it in a new session. A stop before "Plan the chapters" makes
`<movie-dir>` prints neither line.

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
9. Plan a margin inside these limits. The sum plus 8 s for each bridge must be at least 300 s. The
   sum plus 15 s for each bridge must be at most 750 s.
10. Write `<movie-dir>/movie.json`.

The margin of step 9 has a reason. A chapter can come out a fifth shorter or longer than its
`seconds`. A plan of 300 s is still at least 240 s when each chapter is a fifth short. A plan of
750 s is still at most 900 s when each chapter is a fifth long. `check` tests only the limits of
step 8, not the margin.

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
  - `not_covered`: `none`, or one sentence for each facet that the movie does not explain. Write a
    facet before the first `disputed:` entry, also on a later change of the plan.
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

6. Ask the user to approve the plan, or to say what to change. Stop ("When the run stops"). Build
   nothing before the user approves the plan.
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

A round of a fix loop is one edit for each failure line of the last full `check`. That is the run of
`check` before the first edit of the round. A failure line comes back when `check` prints it again
after the edit that was to fix it. In a fix loop of another command, such as `bridges`, `stitch` or
`verify.sh`, read that command for `check`.

Stop a fix loop after 3 rounds in which the same failure lines come back. Also stop it at once for a
fault that is not in `movie.json`. This rule applies to each fix loop of this file. Then print each
line that remains, and what it means. Stop the run ("When the run stops"). Do not change `state`: a
resume continues from it.

## 5. Build the chapters

Start this section only after the user approves the plan, or on a resume.

1. Set `state` to `building` in `movie.json`. Run `movie.py check <movie-dir>`. The state
   `building` records the approval of the user. Thus a resume does not stop for the approval again.
   If `state` is already `building`, skip this step: for example on a resume, or on a rebuild.
2. Find the engine from `lang`, as in `rungs/video.md`: `kokoro` for `en`, and `silero` for `ru`.
3. The chapters share one video workspace, and a first install must not run two times. Thus, before
   the first chapter subagent starts, set up the workspace once yourself. Run this command:

```
<skill-dir>/scripts/video-workspace.sh --engine <engine>
```

4. Read its last line. It is `workspace: ok <ws>` or `workspace: FAIL <step> …`. On a
   `workspace: FAIL` line, print that line. This is a fault of the environment. Change no chapter.
   Stop the run ("When the run stops"). A resume continues.

At most 3 chapter subagents run at the same time. The renders and the narration share one computer.
A chapter stays `pending` while its subagent runs: `movie.json` has no status for a running chapter.
Thus keep a list of the chapters whose subagents run now: the running list. Do this loop:

1. Find the `pending` chapters in `movie.json`, in the order of the plan. Skip each chapter of the
   running list.
2. Count the free slots: 3, less the number of chapters in the running list.
3. For each chapter that remains, up to the number of free slots, do steps 4 and 5.
4. If `<movie-dir>/chapters/<id>/` exists, move it to `chapters/<id>.stale-<n>/`. `<n>` is the first
   number from 1 that no directory has. An earlier build stopped in that directory, and a new build
   starts in an empty one. Never delete a chapter directory.
5. Fill `<skill-dir>/movie/chapter-task.md` as "The chapter prompt" below says. Start the chapter
   subagent with the result, in the background. Add the id of the chapter to the running list.
6. When a chapter subagent returns, remove the id of its chapter from the running list. Read only
   these lines of its reply, and print them in this order:
   - The result line: the last line that starts with `chapter: <id>` and a space. `<id>` is the id of
     that chapter. The line is `chapter: <id> built` or `chapter: <id> failed <reason>`.
   - Each line before the result line that starts with `disputed:` or `off target:`.
   - The narration fallback line before the result line, if the reply has one. Its form is
     `narration (say): ok (fallback: <cause>)`.
7. For `chapter: <id> built`, set `status` to `built` and `reason` to `""` in `movie.json`.
8. For `chapter: <id> failed <reason>`, set `status` to `failed` and `reason` to `<reason>`.
   Escape `<reason>` as "Edit the plan" says. If `<reason>` names a `workspace`, `narration` or
   `container` `FAIL`, do steps 10 to 12. Then go to "A fault of the environment" below.
9. If the reply has no result line, set `status` to `failed` and `reason` to `no result line`. A
   harness error or a stop is no reply. For it, go to "A chapter that does not return" below.
   A harness can also say that the subagent ended and sent no report. Then send the subagent one
   message that asks for the lines of its "Result", one time. Read its answer as the reply. In
   the first live run, three chapters of five came back that way.
10. Write each `disputed:` line of the reply into `movie.json`, as "The chapter gate" below says.
11. Run `movie.py check <movie-dir>` after each edit. If it exits with 2, the edit broke the JSON.
    Undo the edit. Make it again, with the text escaped ("Edit the plan"). Never write the whole file
    again in the build. Fix each failure line about the field that you changed.
12. Keep each narration fallback line, with the id of its chapter, for "The handoff". A fallback
    line and an `off target:` line do not fail a chapter: the chapter ships as `built`.
13. Go to step 1. Stop the loop when no chapter is `pending` and the running list is empty.

Never read the files of a chapter directory. The chapter subagent checks its own render and its
own stills. In the loop, `check` also reads the `script.json` of each chapter directory. A
`chapter <id>:` line that names the script, a scene, `format`, `root` or `lang` comes from that
file. Leave such a line while its subagent runs, or when its chapter is `failed`. Never edit a
`script.json` yourself.

When the loop stops, look at the `status` of each chapter. If each chapter is `built`, go to
"Bridges". If a chapter is `failed`, the movie cannot stitch, because `movie.py stitch` refuses a
chapter that is not `built`. Print the line of each `failed` chapter. Stop the run ("When the run
stops"). A resume builds the failed chapters again.

A resume builds only the chapters that are not `built`. Never build a `built` chapter again, unless
"Stitch" or "The viewer gate" sends it back.

### A chapter that does not return

A chapter subagent that does not return stops the run. The harness reports an error or a stop, and
no reply comes. Then do these steps:

1. Start no new chapter.
2. Let the other chapter subagents of the running list finish. For each reply, do steps 6 to 12 of
   the loop.
3. Do not change the `status` of that chapter. It stays `pending`, and a resume builds it again.
4. Print the id of the chapter and the path of `<movie-dir>`. Stop the run ("When the run stops").

### A fault of the environment

A fault of the environment also stops the run. If a `reason` names a `workspace`, `narration` or
`container` `FAIL`, the next chapters fail too. Then do these steps:

1. Start no new chapter.
2. Let the chapter subagents of the running list finish. For each reply, do steps 6 to 12 of the
   loop. Do not come back to this subsection for their lines.
3. Print the `FAIL` line. Stop the run ("When the run stops"). A resume continues.

### A source that moves

The source can change while the chapters build: a commit, a merge or a pull under the root. Then
`check` prints `cite <question-id>#<n>: snippet not found on that line` for a cite that passed
before, and the number of the line is stale. The fault is in `movie.json`, so the stop rule does
not apply. Do these steps:

1. For each such line, find the snippet in the file again: `grep -nF '<snippet>' <root>/<path>`.
2. Set the `line` of that cite to the new number, as "Edit the plan" says: one edit, then
   `check`.
3. Set `provenance.commit` to the current short hash, and `dirty` to its current value.
4. Change no chapter. A chapter subagent reads each cited line from the disk, and it cites the
   line that it read. A `built` chapter keeps its cites.

In the first live run, a merge under the root moved the source by 7 to 68 lines during the
build. The ten cites of the plan took ten edits. Each chapter cited the current lines by itself.

### The chapter prompt

The prompt `chapter-task.md` is a template. Read it. Replace each name in braces with the text of
the table below. A JSON text is plain text too: put it in the prompt as it is. Give the result to the
subagent as its prompt.

You can also write the result to a file outside `<movie-dir>`. Then give the subagent a short prompt
that names that file, and that tells it to read the file first. The text reaches the subagent as it
is, and it does not fill your context. A filled chapter prompt has about 1900 words.

| Name | Fill with |
|---|---|
| `{skill_dir}` | The absolute path of `<skill-dir>`. |
| `{movie_dir}` | The absolute path of `<movie-dir>`. |
| `{chapter_id}` | The `id` of the chapter. |
| `{chapter_json}` | The object of the chapter in `movie.json`, as JSON. |
| `{questions_json}` | The objects of the questions that the `answers` of the chapter name, in that order, as a JSON list. Each object has its `id`, `text`, `answer` and `cites`. |
| `{other_chapters}` | Each other chapter as `<id>: <question>`, one on each line, in the order of the plan. |
| `{subject_json}` | The `subject` object of `movie.json`, as JSON. |
| `{root}` | The absolute path of `provenance.root`. If the `root` in `movie.json` is relative, it is relative to `<movie-dir>`. |
| `{lang}` | The `lang` of `movie.json`: `en` or `ru`. |
| `{review}` | `on` when `review` in `movie.json` is `true`, else `off`. |
| `{amendment}` | The `<what the film did not show>` of each `missed:` line that names this chapter in the last `## Author` block, one on each line. The last block is in the last `review/viewer-round-<k>.md` that has an `## Author` block. On a resume, read it from that file. If no such line exists, `none`. |

### The chapter gate

Under `--review`, the chapter gate is a cold read of the script of each chapter, before its first
render. A fresh reviewer reads the narration against its cites, the `answer` scene against the
answers of the chapter, and the `ask` scene against its question. The prompt of the reviewer is
`<skill-dir>/movie/review-chapter.md`.

The work of the gate has two owners:

- The chapter subagent runs the gate of its chapter. It starts each reviewer and appends `## Author`
  to each report. It runs the rounds and the verification reads. It ships a chapter with an open
  finding, and it writes the `disputed: <id>:` lines in its reply.
- The orchestrator starts no reviewer and reads no report. It copies the `disputed:` lines of a
  reply into `movie.json`, as the last steps of this subsection say.

These steps are for the chapter subagent. In them, "you" is the chapter subagent.

1. Run the gate after `movie.py check` and before your first render. Make the directory
   `chapters/<id>/gate/` of your chapter. The reports of the gate go there.
2. Start each reviewer as a fresh general-purpose subagent. Never start a fork: a fork has your
   context and your blind spots. Start a new reviewer for each round and for each verification read.
3. Fill `review-chapter.md` as the table below says. Give the result to the reviewer as its prompt.
4. Round 1: `{previous}` is `none`, and the report is `gate-round-1.md`.
5. When a reviewer returns, read its report. Its last line is `verdict: ok` or `verdict: fix`.
   Append `## Author` to the report. For each finding, write `fixed` with what changed, or
   `not fixed` with why. Never change the text of the reviewer.
6. A reviewer can return no report, or a report whose last line is no verdict. Then start a new
   reviewer for that round, one time. If that fails too, the gate stops. The last report is then the
   report before that round, if one exists. Before the result line, also write the line
   `disputed: <id>: the chapter gate stopped in round <k>`, with the number of that round. Then do
   steps 12 to 15.
7. When a report says `verdict: ok`, the gate is complete. Render the chapter.
8. If the report of round 1 says `verdict: fix`, fix each finding that you accept. Then run round 2.
   `{previous}` is `gate-round-1.md`, with your `## Author` block. The reviewer rules each finding
   `resolved` or `open`, and then hunts for new faults. Its report is `gate-round-2.md`. There are
   two hunting rounds at most.
9. If you fix a finding of `gate-round-2.md`, a verification read follows. `{previous}` is
   `gate-round-2.md`, with your `## Author` block. The reviewer rules each finding `resolved` or
   `open`, and it hunts for nothing new. Its report is `gate-round-3.md`.
10. That read can rule `open` a finding that you fixed, because your fix moved the fault. If you fix
    it again, one more verification read follows, with `gate-round-3.md` as `{previous}`. Its report
    is `gate-round-4.md`. No read follows `gate-round-4.md`.
11. The last report is the first report that says `verdict: ok`. Else it is `gate-round-2.md` or
    `gate-round-3.md` when you fix no finding of it. Else it is `gate-round-4.md`.
12. The open findings are the findings of the last report: its new findings and each finding that
    it rules `open`. A finding that no read rules after your fix is `open` too, whatever your
    `## Author` block says.
13. An open finding does not stop the chapter. The chapter ships: render it, and end your reply with
    `chapter: <id> built`. A chapter is never dropped, because it answers a viewer question.
14. Before that result line, write one `disputed: <id>: <finding>` line for each open finding.
    `<id>` is the id of your chapter. `<finding>` is the finding and your reason from your
    `## Author` block, in STE, on one line. Thus the user reads the pair, and the user decides if
    the reviewer was right.
15. A fix after the last read of the gate can change the narration of a scene. Examples are the
    loop of the length and a fix after the stills. No reviewer reads that change. Then write one more
    line before the result line: `disputed: <id>: narration changed after the gate in <scene ids>`.
    `<scene ids>` lists the id of each such scene, as `body, detail`. Start no new reviewer for it.

The reports are `chapters/<id>/gate/gate-round-<k>.md`, with `<k>` from 1 to 4. They are not in
`chapters/<id>/review/`, because `render.sh` empties that directory on each render.

The prompt tells the reviewer to read only the script, the files under the root and the pages of
its URL cites. It closes the directory of the movie and its parent directory, except the script
and the report of `{previous}`. Thus `movie.json`, the other chapters, the reports of the viewer and
the directories of earlier runs are outside what a reviewer reads. This is an instruction, not a
sandbox. A reviewer can read any file, so write no hint of a fault in a file that it reads.

The chapter subagent fills the prompt. `review-chapter.md` is a template. Read it. Replace each name
in braces with the text of the table below. A JSON text is plain text too: put it in the prompt as it is. The chapter prompt in
the table is the prompt of the chapter subagent: `chapter-task.md` with its names filled.

| Name | Fill with |
|---|---|
| `{subject}` | The `text` of the subject of the movie, from `{subject_json}` of the chapter prompt. |
| `{root}` | The absolute path of the root of the movie, as the chapter prompt gives it. |
| `{files}` | The absolute path of `<movie-dir>/chapters/<id>/script.json`, on one line. |
| `{chapter_id}` | The `id` of the chapter. |
| `{question}` | The `question` of the chapter, from `{chapter_json}` of the chapter prompt. |
| `{questions_json}` | The JSON list of the viewer questions in the chapter prompt, as it is. Each object has its `id`, `text`, `answer` and `cites`. |
| `{report}` | The absolute path of `<movie-dir>/chapters/<id>/gate/gate-round-<k>.md`. `<k>` is the number of the round or of the verification read, from 1 to 4. |
| `{previous}` | `none` in round 1. In round 2, the absolute path of `gate-round-1.md`, with the `## Author` block. For a verification read, the absolute path of the report before it, with the `## Author` block. |

These steps are for the orchestrator. Do them for each `disputed:` line of a reply. Write the line
into `provenance.not_covered`:

1. Escape the line as "Edit the plan" says. A finding often quotes the narration.
2. If `not_covered` is `none`, replace `none` with the line. Else add the line at the end, after one
   space.
3. End the line with a period.
4. Run `movie.py check <movie-dir>`. If it exits with 2, the edit broke the JSON. Undo the edit. Do
   steps 1 to 3 again. Never write the whole file again in the build.
5. For a `prose:` line about `provenance.not_covered`, write the finding again under the STE profile.
   Keep the `disputed: <id>:` start.

## 6. Bridges

Start this section when each chapter is `built`. A bridge is a clip of three scenes between two
chapters. The chapters count from 1, in the order of the plan. Bridge `<n>` comes after chapter
`<n>`, in `<movie-dir>/bridges/<n>/`. Its labels come from `movie.json`: the `text` and the `answer`
of the first question that chapter `<n>` answers, and the `question` of the next chapter.

1. Run `movie.py bridges <movie-dir>`.
2. Read its output. `bridges` runs `check` first. If `check` finds failures, `bridges` prints them and
   `plan: <n> failures`. Then it exits with 1 and writes nothing.
3. In that case, fix each failure line as "Check and stop" says. Then run `bridges` again.
4. Else its line is `bridges: ok (<n>)`, and `<n>` is the number of bridges. `bridges` wrote the
   `script.json` and the `scene/Film.tsx` of each bridge. It rendered nothing.
5. If `bridges` exits with 2, it cannot read `movie.json`, or it cannot write a file. Print its line.
   Stop the run ("When the run stops").
6. Render the bridges one at a time, in the order of their numbers. The engine is the engine of
   "Build the chapters". For each bridge, run this command:

```
<skill-dir>/scripts/render.sh --engine <engine> <movie-dir>/bridges/<n>
```

7. Read the eleven stage lines of each render. `rungs/video.md` "Build and check" names them. Each
   line must show `ok`.
8. Record the length of each bridge: the `<s>` of its line `container: ok (<s> s)`. "Stitch" needs
   these lengths when the movie is too short or too long.

A `FAIL` line of a bridge render has its cause in a label or in the tooling. Find the line in
`rungs/video.md` "The FAIL lines".

- A label can go off the canvas or onto another label. A narration can have more words than the 45
  of a clip scene. Such a cause is in the text of a label. The limit of 20 words of `check` keeps
  each label short, but one long word can still go off the canvas. Find the text in `movie.json`:
  the `text` or the `answer` of a question, or the `question` of a chapter. Write it again with
  shorter words, as "Edit the plan" says. Keep its meaning: the questions and the answers are the
  contract of the movie. Then run `bridges` again, and do steps 6 to 8 again for each bridge.
- For `ru`, a label can have a token that the voice cannot speak. The line is then
  `script: FAIL unspoken text: <scene>: "<t>", … (add to pronounce)`. Add each token `<t>` to the
  `pronounce` of `movie.json`, with its spoken Russian form, as "Edit the plan" says. Or write the
  label again in Russian words, as the bullet above says. Then run `bridges` again: it copies
  `pronounce` into each bridge script. Do steps 6 to 8 again for each bridge.
- Never edit a file in `bridges/<n>/`. `bridges` writes these files again from `movie.json`, over each
  edit that you make there.
- Else the cause is in the tooling or in the environment, for example a `workspace`, `narration` or
  `container` `FAIL` line. Print the line. Stop the run by the stop rule of "Check and stop", and print
  the lines of "When the run stops". A resume renders the bridges again.

When the render of each bridge shows eleven `ok` lines, go to "Stitch".

## 7. Stitch

Start this section when the render of each bridge shows eleven `ok` lines.

1. Run `movie.py stitch <movie-dir>`.
2. Print each line of its output. `stitch` prints one line for each stage, in the order of the table
   below. The first `FAIL` line stops it, with exit 1.
3. If each line shows `ok`, go to "The viewer gate".

| Stage line | Meaning |
|---|---|
| `parts: ok (<n>)` | Each chapter is `built`. Each chapter and each bridge has its `video.mp4`. Each part has the same codecs, frame size, frame rate and audio rate as the first part. `<n>` counts the chapters and the bridges. |
| `concat: ok (<s> s)` | ffmpeg joined the parts, in the order of the film, into `build/video.part.mp4`. It copied the streams and encoded nothing again. `<s>` is the sum of the lengths of the parts. |
| `container: ok (<s> s)` | The joined file has one video stream and one audio stream, and its length is within 0.5 s of the sum. Then `stitch` replaced `video.mp4` with it, and it wrote `chapters.json`. |
| `transcript: ok (<n> chapters)` | `stitch` wrote the chapter sections of the hub, the viewer page `review/viewer-transcript.html`, and one still for each chapter in `review/viewer-stills/`. |
| `hub: ok index.html` | `stitch` wrote the hub `index.html` from `movie.json`, the start of each chapter and the chapter sections. |
| `length: ok (<s> s)` | The movie is 240 to 900 s long. |

`stitch` does not run `check`. "Bridges" ran it, before the renders.

### Two shapes of exit 1

`stitch` exits with 1 in two shapes. Tell them apart before you fix anything.

If the only `FAIL` line is `length: FAIL <s> s (min 240, max 900)`, each other stage passed. Then
`video.mp4`, `chapters.json`, the hub and the viewer page are complete. Only the length of the movie
is out of its limits. Do not build all the chapters again. One chapter is the cause, and "A length
out of the limits" below finds it.

After any other `FAIL` line, the viewer gate does not run. The stages after that line did not run.
Thus the viewer page and the hub are old or absent, and a viewer gate on them tests an old film. Fix
the part that the line names, as "The other FAIL lines" below says.

### A length out of the limits

`check` passed the sum of the `seconds` of the chapters. Thus a movie that is too short has a chapter
that came out shorter than its `seconds`. A movie that is too long has a chapter that came out
longer. Find that chapter, and give it a new `seconds`:

1. Read `<movie-dir>/chapters.json`. It holds one item for each chapter, in the order of the film.
   Its `start` is the second at which the chapter starts in `video.mp4`.
2. For each chapter but the last, calculate its real length. Take the `start` of the next chapter.
   Subtract its own `start` and the length of the bridge after it.
3. The bridge after chapter `<n>` is bridge `<n>`. Its length is in your record of step 8 of
   "Bridges".
4. For the last chapter, the real length is the `<s>` of `concat: ok (<s> s)`, less its `start`.
5. Compare the real length of each chapter with its `seconds` in `movie.json`.
6. Read the `<s>` of `length: FAIL <s> s (min 240, max 900)`: the length of the movie. The movie is
   too short when `<s>` is below 240, and too long when it is above 900.
7. If the movie is too short, choose the chapter whose real length is the most below its `seconds`.
   If the movie is too long, choose the chapter whose real length is the most above its `seconds`.
8. Calculate the gap: 240 less `<s>` for a short movie, or `<s>` less 900 for a long movie.
9. For a short movie, add the gap to the real length of the chapter, and multiply by 1.25. For a long
   movie, subtract the gap from its real length, and multiply by 0.8.
10. Round the result to a whole number: up for a short movie, down for a long movie. This is the new
    `seconds` of the chapter.
11. If the new `seconds` is more than 150, one chapter cannot close the gap. Do "Add a chapter" below,
    in place of steps 12 to 14.
12. If the new `seconds` is less than 30, use 30. The next stitch then shows the gap that remains.
13. Edit the `seconds` of the chapter. Remove its `disputed: <id>:` entries from `not_covered`, as
    "Edit the plan" says. Then set its `status` to `pending`. Run `movie.py check <movie-dir>` after
    each edit.
14. Go to "Build the chapters". Its loop builds only that chapter, because each other chapter is
    `built`. Then do "Bridges" and "Stitch" again.

A chapter subagent can miss its `seconds` by a fifth. The factor of step 9 keeps the new film inside
the limits also after such a miss. The brief of the new build carries the new `seconds`. A film has
at most 150 s, and that is the limit of step 11.

This is a fix loop, and the stop rule of "Check and stop" applies. A
`length: FAIL <s> s (min 240, max 900)` line with another `<s>` counts as the same line.

### Add a chapter

A short movie whose chapters cannot grow needs one more chapter. That is a change of the plan, and
the user approves each plan. A plan has at most 10 chapters: if it has 10, stop by the stop rule of
"Check and stop" ("When the run stops").

1. Set `state` to `planned`. Run `movie.py check <movie-dir>`.
2. Add the new chapter at the end of `chapters` as "Edit the plan" says. Make one edit for each
   field, escape each text, and run `check` after each edit.
3. The first edit adds the object with its `id`, `status` `pending` and `reason` `""`. Until the
   object has all its fields, `check` prints a `chapter <id>:` line for each field that is not there
   yet.
4. Never write the whole file again: it holds the `status` and the `reason` of each chapter. The rules
   of "Plan the chapters" give the contents of the fields, not the way to write the file.
5. Start its `picture` from the `ends_with` of the chapter before it. Thus no `built` chapter changes.
6. Give it one or two questions in `answers`. Choose the questions that a new chapter can show in
   more depth.
7. Give it a `seconds` of at least the gap times 1.25, and at most 150.
8. When `check` prints no line about the new chapter, go to step 1 of "Check and stop".

After the approval, "Build the chapters" builds only the new chapter. The new gap adds a bridge.
"Bridges" writes and renders each bridge again.

### The other FAIL lines

- `parts: FAIL chapter <id> is <status>, not built`: `stitch` refuses to start, because the chapter is
  not `built`. It reads no file before this check. Go to "Build the chapters".
- `parts: FAIL no chapters`: `movie.json` has no chapter. Run `movie.py check <movie-dir>`, and fix
  its failure lines as "Check and stop" says.
- `parts: FAIL <part> missing`: the part has no `video.mp4`. `<part>` is a path under `<movie-dir>`,
  such as `bridges/1/video.mp4` or `chapters/<id>/video.mp4`. Make that part again, as "Make a part
  again" below says.
- `parts: FAIL <part> <what> differs`: the part differs from the first part in `<what>`. `<what>` is
  the video codec, the audio codec, the width, the height, the frame rate or the audio rate. Each
  render encodes in the same way, so another version of the tooling made that part. Make that part
  again.
- `parts: FAIL <part> <probe cause>`: ffprobe cannot read the part. `<probe cause>` is
  `ffprobe exit <n>` or `ffprobe output unreadable`. Make that part again.
- `concat: FAIL ffmpeg exit <n>`: ffmpeg cannot join the parts. The fault is in the tooling or on the
  disk, not in `movie.json`. Print the line. Stop the run ("When the run stops").
- `container: FAIL streams <types> (expected one video and one audio)`,
  `container: FAIL duration <d> s, expected <s> s` and `container: FAIL <probe cause>`: the joined
  file is not correct. `video.mp4` stays the file of an earlier stitch, if one exists. The fault is in
  the tooling. Print the line. Stop the run ("When the run stops").
- `transcript: FAIL chapter <id>: no transcript`: the chapter has no `chapters/<id>/index.html`. Its
  render did not come to its last stage. Make the chapter again, as "Make a part again" below says.
- `transcript: FAIL chapter <id>: transcript has no section <ask|answer>`: the transcript of the
  chapter has no `ask` section, or no `answer` section. The transcript is older than the script.
  Make the chapter again, as "Make a part again" below says.
- `transcript: FAIL chapter <id>: transcript has no section before answer`: before `answer`, the
  chapter has no scene other than `ask`. The viewer page needs the still of a body scene. Make the
  chapter again, as "Make a part again" below says.
- `transcript: FAIL chapter <id>: no still <path>`: the chapter has no still of its last body scene.
  `<path>` is the still that `stitch` looks for. Make the chapter again, as "Make a part again" below
  says.

#### Make a part again

Make a part again in one of two ways:

- For a bridge, render it again, as step 6 of "Bridges" says.
- For a chapter, build it again. Remove its `disputed: <id>:` entries from `not_covered`, as "Edit
  the plan" says. Then set its `status` to `pending` and its `reason` to `""`, and run
  `movie.py check <movie-dir>`. Go to "Build the chapters". Its loop moves the old directory aside and
  builds only that chapter. Then do "Bridges" and "Stitch" again.

If the same line comes back after you make the part again, the fault is in the tooling. Stop by the
stop rule of "Check and stop" ("When the run stops").

### Exit 2

If `stitch` exits with 2, it prints one line on stderr:

- `no Remotion CLI at <path>`: the video workspace does not exist. Run `video-workspace.sh` as step 3
  of "Build the chapters" says. Then run `stitch` again.
- Another line: `stitch` cannot read `movie.json`, or it cannot read or write a file. Print the line.
  Stop the run ("When the run stops"). A resume continues.

## 8. The viewer gate

The viewer gate is always on, also without `--review`. It tests the contract of the movie. A viewer
who did not make the film must answer the viewer questions from the film alone.

Start this section only after a stitch in which each line shows `ok`. The viewer page and its stills
then come from the film of that stitch.

The gate has one or two rounds. Two rounds at most. Each round after the first builds chapters
again, and that is the most costly part of a movie. A question that two viewers miss shows a limit
of the film, and the movie reports it.

In this section, `<k>` has two meanings. In the name of a report, `review/viewer-round-<k>.md`, it
is the number of the round. In the name of a still, it is the place of the chapter in the film, from
1.

### Find the round

1. Look for `review/viewer-round-1.md` and `review/viewer-round-2.md`. A report that holds an
   `## Author` block is a complete round.
2. `<k>` is the number of complete rounds, plus 1.
3. If the last complete round marks each question `understood`, the gate is complete. Go to "Verify
   and handoff".
4. If two rounds are complete, the gate is complete too. Make sure that `not_covered` has a
   `viewer missed: <question>` line for each question that the `## Author` block of round 2 marks
   `missed`. Then go to "Verify and handoff".
5. If round 1 is complete and its `## Author` block has a `missed:` line, look for
   `review/viewer-round-2.md`. If it does not exist, an earlier run possibly stopped before the
   rebuild. Then the film is possibly the film of round 1. For each chapter that a `missed:` line
   names, run this command:

```
test <movie-dir>/chapters/<id>/video.mp4 -nt <movie-dir>/review/viewer-round-1.md
```

6. The command fails with exit 1 when `video.mp4` is older than the report, or when it does not
   exist. Then that chapter has no new film. Do the steps of "After round 1" below only for each
   chapter for which the command fails. If it passes for each named chapter, continue to step 7,
   and then run round 2.
7. If `review/viewer-round-<k>.md` exists, an earlier run stopped in this round. Move the report to
   `review/viewer-round-<k>.stale-<n>.md`. `<n>` is the first number from 1 that no file has. Never
   delete a report.

Steps 3 to 7 apply only when an earlier run stopped in the gate, and a resume starts the gate
again.

### Run a round

1. Fill `<skill-dir>/movie/review-viewer.md` as the table at the end of this section says.
2. Start one new subagent with the result, in the background. Use a new subagent for each round. The
   viewer of round 1 saw the film before the fix.
3. When the viewer returns, read only the last line of its reply. It is `viewer: done` or
   `viewer: failed <reason>`. Print it. A harness error or a stop is a reply without `viewer: done`.
4. The round has its answers when three things are true. The line is `viewer: done`, the report
   `review/viewer-round-<k>.md` exists, and the last line of the report is `viewer: done`. Then go to
   step 6.
5. Else start a new viewer for this round, one time. If the report exists, first move it to
   `review/viewer-round-<k>.stale-<n>.md`, as step 7 of "Find the round" says. Then do steps 1 to 4
   again. If the new viewer fails too, the round has no answers. Print the path of the report. Stop
   the run ("When the run stops"). A resume starts this round again, with a new viewer.
6. Read `review/viewer-round-<k>.md`. For each question, it gives the answer of the viewer or
   `cannot answer`, and what in the film the viewer used.

The viewer reads `review/viewer-transcript.html` and the stills under `review/viewer-stills/` that
this page names. The page names each still as `still: viewer-stills/<k>-<id>.png`, a path relative
to `review/`. The viewer reads nothing else of the run: not `movie.json`, no `script.json`, no
chapter transcript, no other still and no source file. A viewer that reads the answers can always
answer, and then the gate tests nothing.

The viewer page holds the title, the question texts and the transcript of each chapter. It does not
hold the `ask` and `answer` scenes, the answers or the cites. Thus the viewer must find each answer
in the body of a chapter, not in a sentence that states it.

### Compare the answers

Compare each answer of the viewer with the `answer` of that question in `movie.json`. Compare the
meaning, not the words. The viewer writes in its own words, and the narration of a chapter also uses
other words than `movie.json`. A check of the words fails a correct answer.

Give each question one of two results:

- `understood`: the answer has the meaning of the `answer` in `movie.json`. It can use other words,
  and it can add facts that are correct. Also, one `used:` line of the entry shows that meaning. Its
  quoted sentence states it, or the still that it names shows it. To judge a still, read it in
  `review/viewer-stills/`.
- `missed: <what the film did not show>`: the answer is wrong, it gives only a part of the meaning,
  or it is `cannot answer`. A `cannot answer` is `missed`, because the film did not show the answer.
  A question that the report does not answer is `missed` too. A correct answer without a `used:` line
  that shows it is `missed` too. The viewer then possibly knew the answer from before, not from the
  film.

For each `missed` question, write what the film did not show, in your words. Name the chapter that
fixes it: the chapter that has the question in its `answers`. If two chapters have it, choose the
chapter whose body scenes must show the missing part.

Append an `## Author` block at the end of the report, in this form. Never change the text that the
viewer wrote.

```
## Author

- <question-id>: understood
- <question-id>: missed: <what the film did not show> (chapter <chapter-id>)
viewer: <n> of <m> understood
```

`<n>` counts the `understood` questions, and `<m>` counts all the questions. Print each `missed:`
line of the block.

Never ask the viewer to try again in the same round. A second try on the same film tests the guess
of the viewer, not the film. The fix is in the film. Step 5 of "Run a round" is no second try: it
starts a new viewer only when the round has no answers.

### After a round

- If each question is `understood`, the gate is complete. Print the line
  `viewer: <n> of <m> understood`. Go to "Verify and handoff".
- If a question is `missed` and `<k>` is 1, the film must change. Do the steps of "After round 1".
- If a question is `missed` and `<k>` is 2, the gate is complete. Never start a third round. Do the
  steps of "After round 2".

After round 1, do these steps for each chapter that a `missed:` line names:

1. Remove its `disputed: <id>:` entries from `not_covered`, as "Edit the plan" says.
2. Set its `status` to `pending` and its `reason` to `""`. Run `movie.py check <movie-dir>` after each
   edit.
3. Its next brief carries the `missed:` text of this block as `{amendment}`. The amendment changes
   what the viewer sees, never the answers of the chapter. The answers are the contract of the movie.
   The viewer sees the narration of the body scenes and the last frame of the last body scene. Thus
   the fix must show there.

Then go to "Build the chapters". Its loop builds only these chapters. Then do "Bridges", "Stitch"
and this gate again, as round 2. Do "Bridges" again also if no label changed. A bridge render is
short, and each bridge then comes from the current `movie.json`.

After round 2, do these steps:

1. For each question that the `## Author` block of round 2 marks `missed`, write
   `viewer missed: <question>` into `provenance.not_covered`. `<question>` is the `text` of the
   question in `movie.json`.
2. Write the line as "The chapter gate" says for a `disputed:` line. The `text` of a question ends
   with `?`: add no period after it.
3. For a `prose:` line about `provenance.not_covered`, write the line again under the STE profile.
   Keep the `viewer missed:` start.
4. Print the line `viewer: <n> of <m> understood` of round 2. Go to "Verify and handoff".

The movie then ships with the miss. The hub and the handoff report it, and the user knows which
answer the film does not show.

The prompt `review-viewer.md` is a template. Read it. Replace each name in braces with plain text.
Give the result to the subagent as its prompt, or write it to a file outside `<movie-dir>` as "The
chapter prompt" says. Fill its names as the table below says.

| Name | Fill with |
|---|---|
| `{transcript}` | The absolute path of `<movie-dir>/review/viewer-transcript.html`. |
| `{stills_dir}` | The absolute path of `<movie-dir>/review/viewer-stills`. |
| `{report}` | The absolute path of `<movie-dir>/review/viewer-round-<k>.md`. `<k>` is the number of the round, from "Find the round". |
| `{movie_dir}` | The absolute path of `<movie-dir>`. |
| `{lang}` | The `lang` of `movie.json`: `en` or `ru`. |

## 9. Verify and handoff

Start this section when the viewer gate is complete.

### Verify the hub

`stitch` wrote the hub `index.html` in "Stitch". The hub shows `provenance.not_covered`.

1. If you edited `movie.json` after the last `stitch`, for example for a `viewer missed:` line, run
   `movie.py stitch <movie-dir>` again.
2. Read its lines as "Stitch" says. The parts did not change, so `stitch` copies the streams again,
   in seconds.
3. Only `stitch` writes the hub: never fill `movie.html` by hand. A hub that you write differs from
   the hub of `stitch`, and the next `stitch` removes it.
4. Run this command:

```
<skill-dir>/scripts/verify.sh <movie-dir>/index.html
```

5. Each line must show `ok`, except that the `bpmn` line can show `none`:

```
self-contained: ok
render 1440x900: ok
render 500x844: ok
citations: ok
prose: ok
media: ok
bpmn: ok
```

6. For a `FAIL` line, read the detail lines under it. If a detail line names a cite or a text of
   `movie.json`, fix that field. Edit it as "Edit the plan" says. Then do steps 1 to 5 again.
7. Else the fault is not in `movie.json`. Stop by the stop rule of "Check and stop" ("When the run
   stops").
8. Set `state` to `stitched` in `movie.json`. Run `movie.py check <movie-dir>`. A resume then knows
   that the movie is complete.

`movie.html` is the template of the hub, in `<skill-dir>/templates/`. The `media` line counts each
link of the hub to `video.mp4` or to `chapters/<id>/index.html` that names no file.

### The handoff

1. Print the path of `<movie-dir>`.
2. Run `open <movie-dir>/video.mp4` only when you run for the user directly. Never run `open` inside a
   subagent (`SKILL.md` convention 6).
3. Print the narrator, as `rungs/video.md` "Handoff" names it: Kokoro `af_heart` for `en`, or `Silero`
   `xenia` for `ru`. If the `narration` line of a bridge render showed a fallback, print the fallback
   and its cause.
4. After the narrator, print each narration fallback line that step 12 of the loop of "Build the
   chapters" kept. Use the form `chapter <id>: narration (say): ok (fallback: <cause>)`. A resume
   keeps the lines only of the chapters that it built. A chapter of an earlier run printed its line
   in that run.
5. Print the line `viewer: <n> of <m> understood`, from the `## Author` block of the last round.
6. Print each entry of `provenance.not_covered` on its own line. For `none`, print nothing.
7. If the harness has a tool that sends a desktop notification, send one. The user is possibly away.

The entries of `not_covered` are the `disputed:` lines, the `viewer missed:` lines and the sentence of
each facet that the movie does not explain. A `disputed:` line can hold more than one sentence. It ends
before the next entry, as "Edit the plan" says.

## 10. Resume

The command `/explain <movie-dir> --as movie` resumes a movie. `movie.json` is the one source of truth
for a resume.

`--review` has no effect on a resume: the value in `movie.json` holds. The `built` chapters passed
the gates of that value, and one movie has one value. If the arguments hold `--review`, print
`--review: no effect on a resume`.

1. Print the rung line. Its reason is `--as movie; resume`, its subject is `<movie-dir>`, and its
   kind is `directory`.
2. Print `review: on` or `review: off`, from `review` in `movie.json`.
3. Run `movie.py status <movie-dir>`. Print each line of its output.
4. If `status` exits with 2, it cannot read `movie.json`. Print its line. Stop ("When the run
   stops"): a resume needs a `movie.json` that it can read.
5. For each `pending` or `failed` chapter, look for `<movie-dir>/chapters/<id>/`. If it exists, move
   it to `chapters/<id>.stale-<n>/`. `<n>` is the first number from 1 that no directory has.
6. Never delete a chapter directory. The new build starts in an empty directory, and the old one
   stays for the user to read.
7. For each `pending` or `failed` chapter, remove its `disputed: <id>:` entries from `not_covered`,
   as "Edit the plan" says. A chapter that has no such entry needs no edit.
8. For each `failed` chapter, set `status` to `pending` and `reason` to `""`. Run
   `movie.py check <movie-dir>` after each edit.
9. Run `movie.py check <movie-dir>`. Fix each failure line as "Check and stop" says, by its stop rule.
10. Go on from the line `state: <state>`, as the second table below says.

`status` prints one line for each chapter, in the order of the plan:
`chapter: <id> <status>[ <reason>]`. The part in brackets shows only when the `reason` of the chapter
is not empty. Then it prints one `stray: chapters/<name>` line for each directory in `chapters/` that
is no chapter. Its last line is `state: <state>`.

| Line | Meaning | Do |
|---|---|---|
| `chapter: <id> built` | The chapter is complete. | Leave it. |
| `chapter: <id> pending` | The chapter waits for its build. If its directory exists, an earlier run stopped while its subagent ran: `movie.json` has no status for a running chapter. | Steps 5, 7 and 10. |
| `chapter: <id> failed <reason>` | The build of the chapter failed in an earlier run. `<reason>` tells why. | Steps 5, 7, 8 and 10. |
| `stray: chapters/<name>` | A directory in `chapters/` that is no chapter, for example a `chapters/<id>.stale-<n>/` directory of an earlier build. | Leave it. `stitch` reads only the directories of the chapters. |

The loop of "Build the chapters" starts only `pending` chapters. Thus a `failed` chapter goes back to
`pending`. The `failed` line of `status` keeps its reason in the output of the run.

| Line | Go to |
|---|---|
| `state: planned` | The user did not approve the plan. Go to step 5 of "Check and stop": print the plan, and stop for the approval. |
| `state: building`, and a chapter is `pending` | "Build the chapters". It builds only the `pending` chapters. |
| `state: building`, and no chapter is `pending` | "Bridges", then "Stitch" and "The viewer gate". The gate finds its round from the reports in `review/`. |
| `state: stitched` | The movie is complete. Print the path of `<movie-dir>`, and the line `viewer: <n> of <m> understood` of the last `review/viewer-round-<k>.md`. Stop. |

A resume never builds a `built` chapter again, unless "Stitch" or "The viewer gate" sends it back.

## 11. Output directory

The directory is `~/karpathy/out/YYYY-MM-DD-HHMMSS-movie-<slug>/`. A movie commits nothing.

| Path | Holds |
|---|---|
| `movie.json` | The plan and the state, which you write. The one source of truth for a resume. |
| `chapters/<id>/` | One chapter: a complete film output directory, as `rungs/video.md` "Output directory" lists it. Its chapter subagent writes it. |
| `chapters/<id>/review/` | The stills of the chapter. `render.sh` empties this directory on each render. |
| `chapters/<id>/gate/` | Under `--review`: the reports of the chapter gate, `gate-round-<k>.md`, each with the `## Author` block of the chapter subagent. `render.sh` never writes here. |
| `chapters/<id>.stale-<n>/` | An earlier build of the chapter `<id>`, moved aside before a new build. `status` prints a `stray: chapters/<name>` line for it. |
| `bridges/<n>/` | The bridge after chapter `<n>`: a clip output directory. `movie.py bridges` writes its `script.json` and `scene/`, and `render.sh` writes the rest. |
| `build/` | The work files of `stitch`: `concat.txt`, the list of the parts for ffmpeg; `video.part.mp4`, the joined file before its check; and `hub-sections.html`, the chapter sections of the hub. |
| `video.mp4` | The movie: the artifact. |
| `chapters.json` | The `id`, the `title` and the `start` of each chapter: the second at which it starts in `video.mp4`. |
| `index.html` | The transcript hub, which `stitch` writes. It has the meta `<meta name="explain-rung" content="movie">`. |
| `review/viewer-transcript.html` | The viewer page: the title, the question texts and the transcript of each chapter, without the `ask` and `answer` scenes, the answers and the cites. |
| `review/viewer-stills/<k>-<id>.png` | The still of chapter `<id>`, chapter number `<k>` of the film: the last frame of its last body scene. |
| `review/viewer-round-<k>.md` | The report of round `<k>` of the viewer gate, with your `## Author` block at its end. |
| `review/viewer-round-<k>.stale-<n>.md` | The report of a round that stopped before its `## Author` block, moved aside. |

## 12. Costs

The first live run measured these costs on 2026-11-06. The movie was English, with 5 chapters, 4
bridges and the review off. It ran on one Apple computer with the Kokoro voice. Its film is 451 s
long, from a plan of 420 s of chapters.

- Lines of scene code for each second of a chapter: 3 to 6. A chapter of 70 to 100 s had 250 to
  450 lines of `.tsx` in `scene/`. A later chapter carries the stage of the chapters before it,
  so its count grows along the film.
- Render runs for each chapter: 1 to 4, and 2 as the median. The reads of the stills are most of
  the work of a chapter. One chapter read 33 to 56 stills, in 43 to 86 tool uses. One chapter
  subagent used 210k to 290k tokens and 13 to 22 min of wall time. Three chapters at a time took
  22 min, and the last two took 16 min.
- Tokens and rounds of the viewer gate: one round, 100k tokens, 8 tool uses and 1 min. The viewer
  understood each of the 5 questions in round 1.
- Wall time of one movie: 66 min from the start of the plan to the hub, without the stop for the
  approval. The plan took 6 min, the chapters 38 min, the bridges 1 min, the stitch 12 s, the
  viewer 1 min and the check of the hub 1 min. Each bridge was 11 to 14 s long, and its render took 15 s.
- The budget of narration words for each chapter: 3 words for each second. The five chapters had
  206 to 287 words for 67 to 95 s of film: 3.0 to 3.1 words each second. A chapter came out 1 to
  7 % shorter than its `seconds`, never longer. Thus a movie comes out near the `<lo>` of
  `check`, and a plan near 240 s of chapters is too short.
- `check` never exited with 2 in the run: about 30 edits of `movie.json`, each by a JSON library,
  broke the file no time. Thus `movie.py` has no `mark` command for the status of a chapter.

A chapter is a film. For the cost of the first render of a chapter and of its workspace, see
`rungs/video.md` "First-run costs".
