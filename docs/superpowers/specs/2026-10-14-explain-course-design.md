# explain: the course rung

Date: 2026-10-14. Status: approved in chat 2026-10-14 ("proceed with implementation"); the calls
of section 12 are the author's, made while the user was away. Coverage: not opted in.

## 1. Problem

A lesson (`--as lesson`) has fixed budgets: one page of usually 6 to 10 sections, usually 2 to 3
clips, a clip of at most 60 s, a scene of at most 30 s. For a system of several services, such as
diadoc + esb, that is about two minutes of video for the whole system. The lesson must choose a few
facts and drop the rest. The user: "it feels like we undertell on important details in bigger
projects".

The user wants to be able to tell "the entire literal flow": a system sends a message, ESB routes
it, ESB transforms it (for example XML to JSON), the diadoc service handles the JSON, and so on to
the end. They want to know each service that touches the message, what it changes, and why.

## 2. Goals, non-goals, anti-goals

Goals:

- `/explain <sources> --as course` builds a course: blocks of lessons that follow one message
  through the system, hop by hop, at the depth of today's lesson.
- The course first maps the sources and the flow, then shows a plan (sources, hops, blocks,
  lessons) and stops. Nothing is built until the user approves the plan or asks for changes
  (user decision).
- The course proposes the other sources the flow passes through (sibling repos, docs). They go into
  the plan for approval, beside the named sources (user decision).
- After approval the build runs unattended for as long as it needs (user: "as long as needed").
  One fresh subagent builds each lesson. A rerun of the same course picks up where it stopped.
- A hub page shows the whole flow as one diagram, the blocks in order, each hop linked to its
  lessons, the state of each lesson and a `Not covered` list.
- Each hop says where its evidence comes from: `code`, `docs` or `inferred`.
- Failure paths (retries, dead letters, error replies) are part of the flow, not extras.

Non-goals:

- No change to how one lesson is built. The lesson rung runs unchanged, with three overrides that
  this spec names (output directory, provenance sources row, zero-clip rule).
- No new review machinery. `--review` passes through to every lesson.
- No ralph. `ralph-loop` ships code (wave worktrees, br epics, commits); a course writes to `out/`
  and commits nothing. The plan file on disk gives the resume.
- Not a general multi-repo `page` or `sheet`. Only the course rung reads several sources.

Anti-goals (a failure even if it runs):

- A course that builds before the user approves the plan.
- Lessons that repeat each other: each lesson gets the list of the other lessons and covers only
  its own hops.
- A hub or a plan that hides where evidence is thin: an `inferred` hop must show as inferred.
- A run that a crash or a closed session loses: the state of each lesson is on disk after each
  change.

## 3. Command

`/explain <source> [<source>…] --as course [--review]`

- Only `--as course` selects the rung. It is never chosen from the content.
- The subject is a list of source names, split on white space, `+` and `,`.
- Resume: `/explain <course-dir> --as course`. A subject that is one directory holding
  `course.json` resumes that course. Under resume, `--review` is ignored with a notice; the
  value in `course.json` holds.
- Language: English, or Russian on request, as the lesson rung. The course holds one language
  for all lessons (`lang` in `course.json`).

### 3.1 Source resolution

Each name resolves by the first rule that applies. Rules 1 and 2 run over all names first; rule 3
then runs for the names left, so the order of the names does not matter:

1. A path candidate (the rule of `SKILL.md`): it must exist and be a directory or a file.
2. A qmd collection of that exact name (`qmd collection list`, or the `path:` of the collection in
   `~/.config/qmd/index.yml`): its path.
3. A directory of that name beside an already resolved source (same parent directory).
4. Otherwise: an error that names the source and the three rules. Build nothing.

The rung line prints each source and the rule that resolved it.

## 4. Output directory

`~/karpathy/out/YYYY-MM-DD-HHMMSS-course-<slug>/` (convention 5 of `SKILL.md`, rung name
`course`; the slug comes from the names joined with `-`).

| Path | Holds |
|---|---|
| `course.json` | The plan and the state. The one source of truth for a resume. |
| `map/<source-id>.md` | The map of one source, written by a map subagent. |
| `lessons/<lesson-id>/` | One complete lesson output directory (`rungs/lesson.md` "Output directory"), or a page output for a lesson with no clip. |
| `index.html` | The hub. Meta `<meta name="explain-rung" content="course">`. |
| `page.png`, `narrow.png`, `review/` | The snapshots of the hub. |

## 5. `course.json`

Version 1. Ids match `[a-z0-9][a-z0-9-]*`. Text fields that the hub shows are prose and follow
the STE profile (or convention 7).

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

Fields:

- `root`: the deepest common ancestor directory of all sources. Each `path` is relative to it.
  Each lesson of the course uses it as `data-root`.
- `state`: `planned` (waits for approval), `approved` (build may run), `done` (hub written).
- `sources[].kind`: `code` or `docs`. `found`: `named` or `discovered`. `why`: one sentence, why
  the source is on the path. `commit`: the short hash, or `none` outside git. `dirty`: as
  convention 2.
- `hops`: in flow order, failure paths included. `branch`: `null` for a hop of the main path; for a
  failure hop, the id of the earlier hop where the failure branches off. A failure hop never
  follows the main path in the diagram; it hangs under its branch hop. `evidence`: `code`, `docs` or `inferred`. An
  `inferred` hop has no cite, and `what` says what the inference rests on. A `code` or `docs` hop
  has at least one cite, in the cite rules of convention 2 (snippet of at most 12 words, verbatim).
- `blocks`: in flow order. Each block has at least one lesson.
- `lessons[].status`: `pending`, `building`, `done`, `failed` or `dropped`. `reason`: empty for
  `pending`, `building` and `done`; one line for `failed` and `dropped`.
- `not_covered`: one sentence each.
- `approved_shape`: written by `approve`. A hash of the shape of the plan: the ids and order of
  the hops (with `branch`), the blocks and the lessons, and the hops and sources of each lesson.
  Prose and cites are not part of the shape.

### 5.1 States

| From | To | By |
|---|---|---|
| `planned` | `approved` | `course.py approve`, after the user approves. |
| `approved` or `done` | `planned` | `check`, when the shape differs from `approved_shape`: a change of shape needs a new approval. Prose and cite fixes after approval keep the state. |
| `approved` | `done` | `course.py hub`, when no lesson is `pending` or `building`. |
| `done` | `approved` | `course.py reopen` (on a resume it sets each `failed` and each `building` lesson to `pending`), or `hub` and `mark` when a lesson is open again. |

Lesson status: `pending` → `building` (orchestrator, at dispatch) → `done` or `failed`
(orchestrator, from `verify.sh`). `dropped` is set only when the user asks for it. `mark <id>
pending` retries one lesson (from `failed` or `dropped`). `mark` refuses any other transition
(`mark: <id>: <from> -> <to> not allowed`), except `building` → `pending` and `done` → `pending`
when `lessons/<id>/index.html` is missing, so that a resume never dead-ends. A resume runs `reopen` first, so each
new run retries the failed lessons once; inside one run a failed lesson is not retried. A
`dropped` lesson still counts for the rule that each hop is in at least one lesson; the hub lists
its hops as not built.

## 6. `scripts/course.py`

Standard library only, like the other scripts. Every write is atomic (temporary file in the same
directory, then rename). Exit 0 on success, 1 on a check failure, 2 on a usage or read error.

| Command | Does |
|---|---|
| `course.py check <dir>` | Validates `course.json`: the schema of section 5; unique ids; each lesson names hops and sources that exist; each hop is in at least one lesson; a failure hop branches from an earlier hop; each source path exists under `root`; each `code`/`docs` hop has a cite and each `inferred` hop has none; each cite path exists under `root`, its line is in range and its snippet is on that line; each `done` lesson has `lessons/<id>/index.html`; the prose fields pass `ste_lint.py --html` (as the hub will be linted, with the `lang` of the course). For an `approved` course whose shape differs from `approved_shape`, it sets `state` to `planned` and prints one failure that asks for a new approval. One failure per line, then `course: ok` or `course: <n> failures`. |
| `course.py summary <dir>` | Prints the plan for approval: the sources (with `named`/`discovered` and why, and `moved` when the current commit or dirty flag differs from `course.json`), the hops as a chain with their evidence, the blocks with their lessons (question, hops), the lesson count and a rough build time (lessons x 30 min / parallel slots), and `not_covered`. |
| `course.py approve <dir>` | Runs `check`; on success sets `state` to `approved`. |
| `course.py next <dir> [--limit N]` | Prints the ids of the lessons with status `pending` or `building`, in plan order, at most N. Refuses (exit 1) when `state` is `planned`. |
| `course.py mark <dir> <lesson-id> <status> [--reason <text>]` | Sets the status of one lesson. `failed` and `dropped` need a reason; the others take none. `done` needs `lessons/<id>/index.html`. |
| `course.py reopen <dir>` | Sets each `failed` lesson to `pending`, and a `done` course with a reset lesson back to `approved`. Prints the ids it reset. |
| `course.py hub <dir>` | Writes `index.html` from `course.json` and the chrome of `templates/page.html`. Sets `state` to `done` when no lesson is `pending` or `building`. |

`building` on a resume means the run stopped during that lesson: `next` lists it again, and the
orchestrator rebuilds it from an empty `lessons/<id>/` (the old directory is moved aside to
`lessons/<id>.stale-<n>/`, never deleted).

## 7. The hub

`course.py hub` reuses the chrome of `templates/page.html` (palette, guard, Sources switch, nav,
footer provenance): it keeps the head and the scripts of the template and writes a course body in
place of the template's header, main and footer. No copy of the template is kept. It writes:

1. Title, the course question, and a short answer: one sentence per block, from the block titles
   and the hops it holds (generated, so the answer always matches the plan).
2. The flow diagram: one SVG chain of the main hops in order, with each failure hop in a lower row
   under its branch hop, joined by a dashed line marked "on failure". Each box names `from → to`
   and is a link to the first `done` lesson that covers the hop; a hop with no `done` lesson has
   no link and shows "not built". The border shows the evidence: solid for `code`,
   dashed for `docs`, dotted for `inferred`, with a legend.
3. One section per block: its title as `<h2>`, then one item per lesson: the question as a link
   to `lessons/<id>/index.html`, the hops it covers, and its status. A `failed` or `dropped`
   lesson shows its reason and has no link.
4. `Not covered`: the list of the plan.
5. Provenance: `data-root` = `root`, `data-kind="topic"`, a row for each source with its commit
   and dirty flag, the date, the review setting. `hub` reads the current commit of each source; when
   it differs from the planned one, the cell shows both (`abc1234 → def5678, moved after
   planning`). Each lesson's own provenance gives the commits it was built from.

The hop cites of `course.json` render as the cite blocks of the page (convention 2), so
`cite_check.py` checks them.

## 8. `verify.sh`

A new rung `course`: two viewports, as a page. The `media` check also runs for a course and counts
each `href` that starts with `lessons/` and names no file. `bpmn.py check --rung` accepts `course`
(it reads the hub as a page). A course hub prints seven lines, like a lesson.

## 9. The run

The orchestrator is the session that runs `/explain`. It keeps its own context small: maps and
lessons come back from subagents as files and one result line.

1. **Resolve** the sources (3.1). Print the rung line, `review: on|off` and the sources. Make the
   output directory.
2. **Map.** Start one map subagent per source, all at once, with `course/map-task.md`. Each writes
   `map/<source-id>.md`: entry points, what comes in and goes out (queues, topics, HTTP endpoints,
   files, tables), message formats and transforms, config that routes, error paths, and the names
   of other systems it talks to, all with cites. It returns one line.
3. **Discover.** From the "other systems" of the maps, search the directories beside the sources
   (the parent of each source) for the names (queue names, endpoints, artifact ids). A directory
   that matches is a candidate source, `found: discovered`. Map each candidate (step 2). One
   discovery round only.
4. **Plan.** Read the maps. Write `course.json`: the hops in flow order, the blocks, the lessons.
   A lesson holds what one lesson rung can hold: one subsystem with two to four moving parts,
   usually one to three hops. A hop that needs more gets more lessons. A source that is on no hop
   leaves the plan with a line in `not_covered`, or stays if it holds config or docs of a hop.
5. **Check and stop.** Run `course.py check` until it prints `course: ok`. Run `course.py summary`
   and print it. Stop and ask the user to approve or to say what to change. Build nothing.
6. **Revise.** For each change the user asks for, edit `course.json`, run `check` and `summary`
   again, and ask again. On approval, run `course.py approve`.
7. **Build.** Loop: `course.py next --limit <free slots>`; for each id, `mark building`, start one
   lesson subagent in the background with `course/lesson-task.md`. At most 3 lesson subagents run
   at once. When one returns, run `verify.sh lessons/<id>/index.html` yourself. Exit 0: `mark
   done`. Else: `mark failed --reason "<first FAIL line>"`. A failed lesson does not stop the
   course. Loop until `next` prints nothing.
8. **Hub.** `course.py hub`, then `verify.sh index.html` (seven lines ok, `bpmn` may be `none`),
   then the snapshots of the page rung. Fix and repeat.
9. **Handoff.** Print the path. Run `open index.html` (not inside a subagent). Send a desktop
   notification where the harness has one, as the user is likely away.

A resume runs `course.py reopen`, then `course.py check` and `course.py summary`, and prints the
sources that moved since planning (a warning, not a stop: cites that broke fail `check`, and the
orchestrator fixes them as prose and cite edits). It then enters at step 5 when `state` is
`planned`, at step 7 when it is `approved`, and at step 8 when no lesson is open. Step 8 may edit
prose and cites of `course.json` to make the hub pass; a change of shape goes back to step 5.

## 10. The lesson subagent

`course/lesson-task.md` is the prompt, with placeholders filled by the orchestrator: the skill
directory, the course directory, the lesson id, the lesson as JSON, its hops as JSON, the paths of
the maps of its sources, the list of the other lessons (id and question), the language, the review
flag. It tells the subagent to:

- read `SKILL.md` and `rungs/lesson.md` and build one lesson by them, with the subject = the lesson
  question, kind `topic`, answered from the files of its sources;
- use `lessons/<id>/` of the course as its output directory (override of convention 5), and the
  course `root` as `data-root`;
- add a `Sources` row to the provenance with each source of the lesson, its commit and dirty flag
  (override: the root is not one repo, so `Commit` is `none`);
- cover only its own hops; name the lesson that covers a neighbour hop instead of explaining it;
- if no section earns a clip, build the page rung in the same directory instead of stopping
  (override of the zero-clip rule);
- run `--review` gates when the flag is on (a subagent can start subagents in Claude Code);
- never run `open`; end with one line: `lesson: done <rung> <n> clips` or
  `lesson: failed <reason>`.

The orchestrator trusts `verify.sh`, not the line.

## 11. Files

- `skills/explain/rungs/course.md`: the rung (sections 3 to 10 as instructions).
- `skills/explain/course/map-task.md`, `skills/explain/course/lesson-task.md`: the two prompts.
- `skills/explain/scripts/course.py` (the hub reuses `templates/page.html`).
- `skills/explain/scripts/verify.sh`, `skills/explain/scripts/bpmn.py`: the `course` rung.
- `skills/explain/SKILL.md`, `README.md`: `course` in the `--as` list, the rung table, the
  resume subject, the rung files list.
- Tests in `skills/explain/tests/`: `course.py` commands, the hub through `verify.sh`, prompt
  placeholders, and the rung lists of `SKILL.md` and `README.md`.

## 12. Calls made by the author (check these)

1. No ralph; the session orchestrates with subagents and `course.json` gives the resume.
2. At most 3 lesson subagents at once. Render and narration share one Mac.
3. One discovery round; candidates come from the directories beside the sources.
4. The hub is generated by `course.py` from `course.json`, not written by the model, so it always
   matches the state.
5. A lesson with no clip builds as a page inside the course, instead of stopping.
6. `building` lessons rebuild on resume; the old directory is kept aside, never deleted.
7. Failure hops carry `branch` (the hop they leave from) and hang under it in the diagram.
8. A resume retries each failed lesson once (`reopen`); `dropped` is only on the user's word.
9. After approval, prose and cite fixes keep the approval; a change of shape (hops, blocks,
   lessons) asks again. `check` lints the prose of the plan, so the hub's prose faults show before
   approval.
10. A source that moved after planning is a warning on resume and a note in the hub provenance,
    not a stop.
11. In OpenCode the lesson subagent may not be able to start reviewer subagents. That is untested;
   the course notes `review` as asked, and the lesson reports what ran.
