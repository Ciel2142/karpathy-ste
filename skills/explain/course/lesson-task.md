# Course lesson (one lesson)

This is a template. The orchestrator fills each name in braces by plain text replacement before it sends
you this file.

## Your task

You build one lesson of a course. A course follows one message through a system of several services, hop
by hop. Each lesson of the course covers some of the hops. Other subagents build the other lessons. The
orchestrator writes the hub page that links the lessons.

Your lesson has the id `{lesson_id}`. This is the lesson, as JSON from `course.json`:

{lesson_json}

These are the hops of the lesson, in the order of the flow, as JSON:

{hops_json}

The subject of the lesson is its `question`. Its kind is `topic`. Answer it from the files of the sources
of the lesson. The `brief` of the lesson tells what the lesson holds. A hop has a `branch` when it is a
failure path: `branch` is the id of the hop where the failure starts.

The root of the course is `{root}`. Each `path` of a source and of a cite is relative to it.

## What to read

1. Read `{skill_dir}/SKILL.md` and `{skill_dir}/rungs/lesson.md`. Also read each section and each file
   that they name.
2. Build one lesson by those files, with the overrides of this file. Where this file and those files
   differ, this file wins.
3. Read `{course_dir}/course.json` for the `path` of each source of the lesson. Change nothing in it.
4. Read the maps of the sources of the lesson first. They tell you where to start. These are their
   absolute paths, one on each line:

{map_paths}

A map is a guide, not a source. Read each line from its file under `{root}` before you cite it.

## Overrides

### Output directory

Your output directory is `{course_dir}/lessons/{lesson_id}/`. It replaces the directory of convention 5
of `SKILL.md`. Make it if it does not exist. Write no file outside it.

Change no file of a source. Change no file in `{course_dir}/map/` or in the directory of another lesson.
Never write `course.json`: the orchestrator writes it.

Print the rung line of `lesson.md` with this reason: `course lesson {lesson_id}`.

### Root and provenance

Set `data-root` to `{root}`, and set `data-kind="topic"`. Each `data-path` is relative to `{root}`. Write
`{root}` in the `Source` row. In the `script.json` of each clip, `provenance.root` is `{root}` too.

Write `none` in the `Commit` row and `no` in the `Dirty` row: the root is not one repository. In the
`script.json` of each clip, `provenance.commit` is `none` and `provenance.dirty` is `no`.

Add a `Sources` row to the `<dl>` of the provenance, after the `Source` row:

```
<div class="wide"><dt>Sources</dt><dd><source-id> <commit> <dirty>; <source-id> <commit> <dirty></dd></div>
```

Write one entry for each source of the lesson. `<dir>` is the directory of the source under `{root}`. Run
these two commands for each source:

```
git -C <dir> rev-parse --short HEAD
git -C <dir> status --porcelain
```

`<commit>` is the short hash, or `none` outside git. `<dirty>` is `dirty` when the second command prints
something, else `no`. Do not use `git rev-parse --show-toplevel`: `data-root` is `{root}`.

The `untracked` mark of convention 2 applies to each cited file. Run `git -C <dir> ls-files
--error-unmatch <path>`, with `<path>` relative to `<dir>`. If it fails inside a repository, mark the
file `untracked`.

### Scope

Cover only the hops of your lesson. These are the other lessons of the course, with their ids, their
questions and their hops:

{other_lessons}

A neighbour hop is a hop of another lesson. For a neighbour hop, write one sentence that names the lesson
that covers it, by its question. Do not explain the neighbour hop. Write no link to another lesson. The
hub links the lessons.

### A lesson with no clip

If no section earns a clip, build the page rung in the same directory instead of stopping. This replaces
the zero-clip rule of `lesson.md`. Keep `review/plan.md`. Follow `{skill_dir}/rungs/page.md` with the
overrides of this file. The meta of the page is then `page`.

### Language and review

Write the lesson in the language `{lang}`: `en` for English, `ru` for Russian. Follow the language rules
of `lesson.md`.

The review flag is `{review}`. If it is `on`, run gates 1 and 2 of `lesson.md`, as under `--review`. Start
each reviewer as a fresh subagent. In Claude Code, use the Agent tool. In OpenCode, use the `task` tool
with the `general` agent. If it is `off`, start no subagent.

If the review flag is `on` and you cannot start a subagent, build the lesson without the gates. Write
`none` in the `Cold review` row. Thus the page tells what ran.

### Handoff

Do the steps of "Finish and handoff" of `lesson.md`: `verify.sh`, the snapshots and the read of the
tiles. Fix each fault. Never run `open`. The orchestrator runs `verify.sh` again on your page, and it
trusts that run, not your reply.

## Result

Your reply ends with one line. Write nothing after it. The lines of the disputed findings come before it.

- When the lesson is complete: `lesson: done <rung> <n> clips`. `<rung>` is `lesson`, or `page` for a
  lesson with no clip. `<n>` is the number of clips on the page.
- When you stop the lesson: `lesson: failed <reason>`. The reason is one line. An example is a fault of
  the environment that "Render the clips" of `lesson.md` names.
