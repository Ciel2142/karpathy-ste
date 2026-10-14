# Rung: course
This file holds only what is specific to the course rung. `SKILL.md` has the generic rules.

## 1. When a course

A course follows one message through a system of several services, hop by hop. It is a set of lessons
in blocks, and a hub page that shows the whole flow. Each lesson is a lesson of `rungs/lesson.md`, with
the depth of one lesson. One fresh subagent builds each lesson.

Use a course only when the user writes `--as course`. Never choose it from the content.

The command is `/explain <source> [<source>…] --as course [--review]`. The subject is a list of source
names. Split it on white space, `+` and `,`. If the subject is one directory that holds `course.json`,
the run is a resume: go to "Resume".

You are the orchestrator. Keep your own context small. The subagents read the sources and build the
lessons. A map and a lesson come back to you as files and one result line. Never read a whole lesson.

In this file, `course.py <command>` is short for `python3 <skill-dir>/scripts/course.py <command>`. Each
command takes `<course-dir>`, the output directory of the course.

Start each subagent in the background. In Claude Code, use the Agent tool. In OpenCode, use the `task`
tool with the `general` agent.

The course has one language for all its lessons: `lang` in `course.json`. Use `en`, or `ru` when the user
asks for Russian. If the user asks for another language, print the rung line. Say that the course rung is
English or Russian. Stop. Offer `page`.

`--review` passes through to each lesson: each lesson runs the review gates of `lesson.md`. The course
itself has no review. Print `review: on` or `review: off` after the rung line.

Print the rung line as `SKILL.md` says, with the kind `topic`:

```
Rung: course (forced) — <reason> — subject: <source> <source> (topic)
```

## 2. Resolve the sources

Each name resolves by the first rule that applies. Run rules 1 and 2 for all the names first. Then run
rule 3 for the names that remain. Thus the order of the names has no effect.

1. Path: a path candidate by the rule of `SKILL.md`. It must exist, as a directory or a file. A path
   candidate that does not exist is an error: stop, and build nothing.
2. qmd: a qmd collection of that exact name. Run `qmd collection show <name>`. Its line
   `Path:     <abs path>` gives the path. For a missing collection, the command fails, and the rule does
   not apply.
3. Beside: a directory of that name beside a source that resolved already, in the same parent directory.

If no rule applies to a name, stop with an error. Name the source and the three rules. Build nothing.

Give each source an id. Make the id from the basename of its path by the slug rule of convention 5 of
`SKILL.md`. If two or more sources get the same id, add `-2` to the second id, `-3` to the third id, and so on.

Print one line for each source, after the line `review: on|off`. `<rule>` is `path`, `qmd` or `beside`:

```
source: <id> <absolute path> (<rule>)
```

Find the root of the course now. The root is the deepest common ancestor directory of all the sources,
as an absolute path. If that directory is a source, use its parent directory. Thus the path of a source
is never empty. A source that discovery adds is beside a source, so it is under the same root.

Make the output directory: `~/karpathy/out/YYYY-MM-DD-HHMMSS-course-<slug>/`. This is convention 5 of
`SKILL.md` with the rung name `course`. Make the slug from the names, joined with `-`. Below,
`<course-dir>` is the absolute path of this directory.

## 3. Map the sources

Start one map subagent for each source, all at the same time. Its prompt is
`<skill-dir>/course/map-task.md`.

The prompt is a template. Read it. Replace each name in braces with plain text. Give the result to the
subagent as its prompt. Fill the names like this:

| Name | Fill with |
|---|---|
| `{skill_dir}` | The absolute path of `<skill-dir>`. |
| `{course_dir}` | The absolute path of `<course-dir>`. |
| `{source_id}` | The id of the source. |
| `{source_path}` | The absolute path of the source. |
| `{root}` | The absolute path of the root of the course. |
| `{lang}` | `en`, or `ru` when the user asks for Russian. |

Each subagent writes `map/<source-id>.md` in `<course-dir>`. It returns one line:
`map: done <source-id> <n> facts` or `map: failed <reason>`. Wait for all the map subagents.

A `map: done` line with no readable `map/<source-id>.md` counts as `map: failed`. Print each
`map: failed` line. A source without a map gets no hop. Write it in `not_covered`, with the reason.

A map subagent or a lesson subagent that does not return stops the run. Print the id of its source or
its lesson, and stop. The state of the course is on disk, so a resume continues.

## 4. Discover

Discovery finds the other sources that the flow goes through. Do one round of discovery only.

1. Run the discovery script once. Give the parent directory of each source once. Give each source with
   `--source`:

```
python3 <skill-dir>/scripts/course_discover.py <course-dir> <parent-dir> [<parent-dir>…] --source <source-path> [--source <source-path>…]
```

2. Read the lines that it prints. If it exits with 2, print its error line, and continue with no
   discovered source.
3. Each line `candidate: <dir> <name-match|-> <n> handles: <handle> …` is a new source, with
   `found: discovered`. Give it a `why`: one sentence that names a handle that it holds, or the system that
   has its name.
4. For each line `cut: <dir> more than 8 discovered sources`, write the directory in `not_covered`, with the
   reason `more than 8 discovered sources`. The other `cut:` lines need no action.
5. Print each line `note: map <file> has no Other systems section`. That map gave no handles.
6. Map each new source as "Map the sources" says. Start their map subagents at the same time.
7. Do not search again from the maps of the new sources.

The script does the search, so you read no file of a candidate. Never read a whole repository. The script
applies these rules:

- The handles of a system are the names in backticks in the section `Other systems` of each map. Examples
  are queue names, endpoints and artifact ids. The cites of a map line give no handles.
- A candidate is a directory in the parent directory of a source, and it is not a source.
- One `grep` command searches each candidate for all the handles.
- Drop each handle that matches more than 5 candidates. Such a handle is too general to find one system.
- First come the candidates whose name is the name of a system of `Other systems`. Case and punctuation
  have no effect: `cryptoproservice` is the system `CryptoProService`. Then come the candidates that hold
  the most handles. Equal candidates go in the order of their names.
- Keep 8 discovered sources at most.

The script writes the same lines to `discover/result.txt`.

## 5. Plan the course

Read the maps. Write `<course-dir>/course.json`. Build nothing before the user approves the plan.

This is the shape of `course.json`, version 1:

```json
{
  "version": 1,
  "title": "How a document travels from the bank to Diadoc",
  "question": "What happens to one message from the source system to Diadoc, hop by hop?",
  "lang": "en",
  "review": false,
  "root": "/Users/valukin/work",
  "state": "planned",
  "sources": [
    {"id": "esb", "path": "esb", "kind": "code", "found": "named", "why": "routes the message",
     "commit": "abc1234", "dirty": false}
  ],
  "hops": [
    {"id": "receive", "from": "source system", "to": "esb", "what": "ESB takes the XML message from the queue.",
     "evidence": "code", "branch": null,
     "cites": [{"path": "esb/src/main/java/Foo.java", "line": 42, "snippet": "@JmsListener(destination = IN_QUEUE)"}]}
  ],
  "blocks": [
    {"id": "entry", "title": "Entry", "lessons": [
      {"id": "entry-receive", "question": "How does ESB take a message from the queue?",
       "hops": ["receive"], "sources": ["esb"], "brief": "Listener, ack mode, the first parse.",
       "status": "pending", "reason": ""}
    ]}
  ],
  "not_covered": ["The admin UI of ESB: not on the path of a message."]
}
```

Write the fields by these rules:

- Ids: each id matches `[a-z0-9][a-z0-9-]*`. Each id is unique.
- `title`, `question`, `why`, `what`, `brief`, block titles and `not_covered`: the hub shows this prose.
  Write it under the STE profile, or under convention 7 for `ru`.
- `lang`: `en`, or `ru` when the user asks for Russian.
- `review`: `true` under `--review`, else `false`.
- `root`: the absolute root of "Resolve the sources".
- `state`: `planned`.
- `sources`: each `path` is relative to `root`. `kind` is `code` or `docs`. `found` is `named` or
  `discovered`. `why` is one sentence that tells why the source is on the path.
- `commit` of a source: the output of `git -C <source> rev-parse --short HEAD`, or `none` outside git.
- `dirty` of a source: `true` when `git -C <source> status --porcelain` prints something, else `false`.
  For a file source, run the two commands in its directory.
- `hops`: in the order of the flow. Include the failure paths: retries, dead letters and error replies.
  `what` is one sentence that tells what the hop does to the message.
- `branch`: `null` for a hop of the main path. For a failure hop, the id of the earlier hop where the
  failure starts.
- `evidence`: `code` or `docs` when a cite supports the hop, `inferred` when no line supports it. A
  `code` or `docs` hop has at least one cite. An `inferred` hop has no cite, and its `what` says what the
  inference comes from.
- `cites`: a `path` relative to `root`, a `line` and a `snippet`. The snippet has at most 12 words, copied
  verbatim from that line. The maps give the cites with the same root. Copy each cite from the map lines.
  Never type a cite again from memory.
- `blocks`: in the order of the flow. Each block has at least one lesson.
- `lessons`: a lesson holds one subsystem with two to four moving parts, usually one to three hops. A hop
  that needs more gets more lessons. There is no limit on the number of lessons. Each hop is in at least
  one lesson.
- `status` of a lesson: `pending`. `reason`: an empty string.
- `not_covered`: one sentence for each item. A source that is on no hop leaves the plan, with a sentence
  here. A source that holds the config or the docs of a hop stays.

## 6. Check and stop

1. Run this command. It prints one failure on each line, then `course: ok` or `course: <n> failures`:

```
python3 <skill-dir>/scripts/course.py check <course-dir>
```

2. Fix `course.json` for each failure line. Then run `check` again. Repeat until it prints `course: ok`,
   or until the stop rule below applies.
3. Run `python3 <skill-dir>/scripts/course.py summary <course-dir>`. Print its output verbatim.
4. Stop. Ask the user to approve the plan, or to say what to change. Build nothing.

The prefix of a failure line tells where the fault is:

| Prefix | Fix |
|---|---|
| `schema:` | The field that the line names. |
| `id:` | Give the second item a new id. |
| `lesson <id>:` | The hops or the sources of that lesson. For `lesson <id>: done but lessons/<id>/index.html missing`, run `course.py mark <course-dir> <id> pending`. |
| `hop <id>:` | The lessons that cover the hop, its `branch`, or its evidence and its cites. |
| `source <id>:` | The `path` of that source. |
| `cite <hop>#<n>:` | Cite number `<n>` of that hop: its path, its line or its snippet. |
| `prose:` | The prose field that the line names. |
| `state:` | The line is `state: plan changed after approval; run summary and approve again`. Go to step 3. |
| `course: cannot read` | `course.json` is not valid JSON. Write it again. `check` exits with 2. |

### The stop rule

Some faults are not in `course.json`, and an edit of `course.json` cannot fix them. Examples:

- `source <id>: path missing: <abs>` for a source that moved on the disk;
- a `schema:` failure for an empty `hops` list, because each map failed;
- a fault of the hub layout that `course_hub.py` makes, which needs a change of the code.

Stop a fix loop after 3 rounds in which the same failure lines come back. Also stop it at once for a fault
that is not in `course.json`. This rule applies to each fix loop of this file: `check`, `approve` and the
hub. Then print each line that remains, and what it means. Stop the run. Do not change the state of the
course: a resume continues from it.

## 7. Revise

For each change that the user asks for, do these steps:

1. Edit `course.json`.
2. Run `course.py check <course-dir>` until it prints `course: ok`.
3. Run `course.py summary <course-dir>`, and print its output verbatim.
4. Ask the user again.

When the user approves the plan, run `python3 <skill-dir>/scripts/course.py approve <course-dir>`. It runs
`check`, and then it sets `state` to `approved`. If it prints failures, fix them and run it again, by the
stop rule of "Check and stop".

Drop a lesson only when the user asks for it. Run `course.py mark <course-dir> <id> dropped --reason
'<reason>'`, with the words of the user as the reason. Remove each `'` from the reason.

## 8. Build the lessons

At most 3 lesson subagents run at the same time. The renders and the narration share one computer.

The lessons share one video workspace, and a first install must not run two times. Thus, before the
loop, set up the workspace once yourself. The engine follows the `lang` of the course, as in `video.md`:
`kokoro` for `en`, and `silero` for `ru`. Run this command:

```
<skill-dir>/scripts/video-workspace.sh --engine <engine>
```

Its last line is `workspace: ok <ws>` or `workspace: FAIL <step> …`. On a `workspace: FAIL` line, print
that line and stop the course. This is a fault of the environment. Mark no lesson. A resume continues.

Do this loop:

1. Run `python3 <skill-dir>/scripts/course.py next <course-dir> --limit 3`. It prints the ids of the
   `pending` and `building` lessons, in the order of the plan. The lessons that run now are `building`, so
   `next` prints them too. Skip them.
2. If `next` prints `next: course not approved`, go to "Check and stop".
3. Count the free slots: 3, less the number of lesson subagents that run now.
4. For each id that remains, up to the number of free slots, do steps 5 to 7.
5. If `<course-dir>/lessons/<id>/` exists, move it to `lessons/<id>.stale-<n>/`. `<n>` is the first
   number from 1 that no directory has. Never delete a lesson directory.
6. Run `python3 <skill-dir>/scripts/course.py mark <course-dir> <id> building`.
7. Fill `<skill-dir>/course/lesson-task.md`, and start the lesson subagent with it in the background.
8. When a lesson subagent returns, read only its last line. Run
   `<skill-dir>/scripts/verify.sh <course-dir>/lessons/<id>/index.html` yourself.
9. If `verify.sh` exits with 0, run `course.py mark <course-dir> <id> done`.
10. Else, run `course.py mark <course-dir> <id> failed --reason '<line>'`. `<line>` is the first `FAIL`
    line of the output, with each `'` removed. If no line holds `FAIL`, it is the first line of the output.
    Never put `<line>` in double quotes: a `FAIL` line can hold `"`.
11. Go to step 1. Stop the loop when `next` prints nothing and no lesson subagent runs.

`mark` refuses a change of status that is not in the order of the build, with the line
`mark: <id>: <from> -> <to> not allowed`. It changes nothing then. Treat the line as a fault that is not
in `course.json`: stop by the stop rule of "Check and stop".

The result line of a lesson subagent is `lesson: done <rung> <n> clips` or `lesson: failed <reason>`. Trust
`verify.sh`, not the result line. A failed lesson does not stop the course. Do not build it again in this
run.

A fault of the environment is different. If a result line names a `workspace`, `narration` or `container`
`FAIL`, the next lessons fail too. Let the lessons that run now finish, and start no new lesson. Then
print the line and stop the run. A resume continues.

The prompt `lesson-task.md` is a template, as `map-task.md` is. Fill its names like this:

| Name | Fill with |
|---|---|
| `{skill_dir}` | The absolute path of `<skill-dir>`. |
| `{course_dir}` | The absolute path of `<course-dir>`. |
| `{lesson_id}` | The id of the lesson. |
| `{lesson_json}` | The object of the lesson in `course.json`, as JSON. |
| `{hops_json}` | The objects of the hops of the lesson, in the order of the flow, as a JSON list. |
| `{map_paths}` | The absolute path of `map/<source-id>.md` for each source of the lesson, one on each line. |
| `{other_lessons}` | Each other lesson of the course as `<id>: <question> (hops: <hop>, <hop>)`, one on each line. |
| `{root}` | The absolute path of the root. If `root` in `course.json` is relative, it is relative to `<course-dir>`. |
| `{lang}` | The `lang` of `course.json`. |
| `{review}` | `on` when `review` in `course.json` is `true`, else `off`. |

## 9. Write the hub

1. Run `python3 <skill-dir>/scripts/course.py hub <course-dir>`. It writes `index.html` from
   `course.json`, and it prints `hub: wrote <path>`.
2. Before it writes, `hub` runs `check`. If `check` finds failures, `hub` prints them and writes nothing.
   Fix the prose and the cites of `course.json`, and run `hub` again, by the stop rule of "Check and
   stop".
3. A change of shape needs a new approval. The shape is the hops, the blocks, the lessons, and the hops
   and the sources of each lesson. After a change of shape, go to "Check and stop". `check` sets `state`
   to `planned`, also for a `done` course, and `approve` then approves the new shape.
4. Run `<skill-dir>/scripts/verify.sh index.html` in `<course-dir>`. Each line must show `ok`, except that
   the `bpmn` line can show `none`:

```
self-contained: ok
render 1440x900: ok
render 500x844: ok
citations: ok
prose: ok
media: ok
bpmn: ok
```

5. Run the snapshots of steps 2 and 3 of "Verify and export" in `<skill-dir>/rungs/page.md`. Read the
   tiles with the Read tool. Never read the full PNGs.
6. In the tiles, look for these faults:
   - text that overflows its box, or that the page cuts;
   - a nav that overflows;
   - a flow diagram that does not fit at 500 px;
   - text that you cannot read;
   - text that gives a false picture of the flow.
7. Run `grep -o 'href="lessons/[^"]*"' index.html`. Look for one more fault: a link to a lesson that is
   not `done`.
8. Fix each fault in `course.json`. Never edit `index.html`: `hub` writes it again. Then do steps 1 to 7
   again. Repeat until all are clean, by the stop rule of "Check and stop". A fault that an edit of
   `course.json` cannot fix stops the run.

The other checks of step 4 of "Verify and export" do not apply to a hub. A block section of the hub holds
no `div.cites`: the cites of the hub are on the hops of the flow section.

The `media` check of a hub counts each link into `lessons/` that names no file. `hub` sets `state` to
`done` when no lesson is `pending` or `building`. Else it sets `state` to `approved`.

## 10. Handoff

1. Print the path of `<course-dir>`.
2. Print one line for each `failed` lesson: its id and its reason.
3. Run `open index.html` only when you run for the user directly. Never run `open` inside a subagent.
4. If the harness has a tool that sends a desktop notification, send one. The user is possibly away.

## 11. Resume

The command `/explain <course-dir> --as course` resumes a course. `course.json` is the one source of
truth for a resume.

`--review` has no effect on a resume: the value in `course.json` holds. If the arguments hold
`--review`, print `--review: no effect on a resume`.

1. Print the rung line, with `<course-dir>` as the subject. Then print `review: on` or `review: off`, from
   `review` in `course.json`.
2. Run `python3 <skill-dir>/scripts/course.py reopen <course-dir>`. It sets each `failed` lesson and
   each `building` lesson to `pending`, and it prints the ids that it reset. A `building` lesson stopped
   in the last run.
3. Run `course.py check <course-dir>`. Fix each failure as "Check and stop" says.
4. Run `course.py summary <course-dir>`. Print each `moved:` line as a warning, with its source. A moved
   source does not stop the course. A cite that broke fails `check`. Fix it as an edit of prose and cites.
5. Run `course.py next <course-dir>` to find where to go.
6. If it prints `next: course not approved`, the state is `planned`. Go to step 3 of "Check and stop".
7. If it prints ids, go to "Build the lessons".
8. If it prints nothing, no lesson is open. Go to "Write the hub".

## 12. Output directory

The directory is `~/karpathy/out/YYYY-MM-DD-HHMMSS-course-<slug>/`. A course commits nothing.

| Path | Holds |
|---|---|
| `course.json` | The plan and the state. The one source of truth for a resume. |
| `map/<source-id>.md` | The map of one source, from a map subagent. |
| `discover/` | The files of the discovery script: `result.txt` (its lines), `handles.txt`, `candidates.txt` and `matches.tsv`. |
| `lessons/<id>/` | One complete lesson output directory (`rungs/lesson.md` "Output directory"), or a page output for a lesson with no clip. |
| `lessons/<id>.stale-<n>/` | An earlier build of the lesson `<id>`, moved aside before a new build. |
| `index.html` | The hub. It has the meta `<meta name="explain-rung" content="course">`. |
| `page.png`, `narrow.png`, `review/` | The snapshots of the hub. |
