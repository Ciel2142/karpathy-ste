# Movie chapter (one chapter)

This is a template. The orchestrator fills each name in braces by plain text replacement before it sends
you this file.

## Your task

You build one chapter of a movie. A movie is one theme as one continuous film, cut into chapters. Each
chapter is a film of `rungs/video.md`. A short bridge clip goes between two chapters. Other subagents
build the other chapters. The orchestrator joins the chapters and the bridges into one movie.

Your chapter has the id `{chapter_id}`. This is the chapter, as JSON from `movie.json`:

{chapter_json}

These are the viewer questions that the chapter answers, with their answers and their cites, as JSON:

{questions_json}

After the movie, a cold viewer answers each viewer question from the film alone. A cold viewer is a fresh
subagent that did not make the film. The answers are the contract of the movie. Your chapter exists to make
its answers visible.

These are the other chapters of the movie, as `<id>: <question>`, one on each line:

{other_chapters}

This is the subject of the movie, as JSON:

{subject_json}

The root of the movie is `{root}`. Each `path` of a cite is relative to it.

This is the amendment of the author:

{amendment}

The amendment changes the picture, never the answers. It is `none`, or a note of the author after a cold
viewer missed an answer of this chapter. The note tells what the film did not show. Show that part in the
body scenes: in their objects, their motions and their narration. Keep each answer of the questions above
as it is. For `none`, build the chapter from the plan alone.

## What to read

1. Read `{skill_dir}/SKILL.md` and `{skill_dir}/rungs/video.md`. Also read each section of another file
   that `video.md` names, such as the provenance recipe of `{skill_dir}/rungs/sheet.md`.
2. Build one film by those files, with the overrides of this file. Where this file and those files
   differ, this file wins.
3. You can read `{movie_dir}/movie.json` for the plan of the movie. Change nothing in it.

## Overrides

### Output directory

Your output directory is `{movie_dir}/chapters/{chapter_id}/`. It replaces the directory of convention 5
of `SKILL.md`. Make it if it does not exist. Write no file outside it.

Change no file of the subject, of another chapter or of a bridge. Never write `movie.json`: the
orchestrator writes it.

Print the rung line of `video.md` with this reason: `movie chapter {chapter_id}`.

### The script

Write a film: keep `"format": "film"` in `script.json`. Obey these rules, and the rules of `video.md`:

- The `title` of the script is the `title` of the chapter.
- The first scene has the id `ask`. Its narration asks the `question` of the chapter.
- The last scene has the id `answer`. Its narration states each `answer` of the questions above, so that a
  cold viewer can repeat it. Keep the meaning of each answer. The words can differ.
- Write at least one body scene between `ask` and `answer`.
- The word limits of `video.md` apply to each scene: 45 words in a scene, and 20 words in a sentence.
- `provenance.root` is `{root}`, and `lang` is `{lang}`. The `movie.py check` command compares them with
  the root and the language of the movie.
- Copy the subject of the movie above into `subject`.
- For `ru`, start `pronounce` from the `pronounce` of `movie.json`. Then add an entry for each new term.

The cold viewer does not see the `ask` and `answer` scenes. The viewer reads the transcript of the body
scenes, and one still: the last frame of the last body scene. Thus the body scenes must show each answer.
The `answer` scene only says it again.

### Length

The length target of the film is the `seconds` of the chapter, within a fifth either way. For example, a
chapter of 70 s gives a film of 56 to 84 s. The limits of a film in `video.md` still apply: 150 s at
most. Come near the target as "Write the script" of `video.md` says. The stage line of `timeline` gives
the real length.

### The picture

The `picture` of the chapter is the stage at the first frame of the film. The `ends_with` of the chapter is
the stage at its last frame. The chapter before yours ends on your `picture`, and the next chapter starts
from your `ends_with`. Between them, keep one picture, as "The grammar of a film" of `video.md` says.

Show only the answers of your chapter. The other chapters answer the other questions. Do not explain them.

### Cites

1. Copy a cite of the questions above where the narration makes the claim of that cite.
2. For each other cite, read the line from its file under `{root}` first. Copy the snippet from that line.
   Never type a cite from memory.
3. Cite no `.bpmn` file. The hub of the movie shows no diagram, and the `bpmn` check of `verify.sh` then
   fails the hub.

### Check the script

Before your first render, run this command:

```
python3 {skill_dir}/scripts/movie.py check {movie_dir}
```

It checks `movie.json` and the script of each chapter. Fix each line that starts with `chapter {chapter_id}:`
and names your script: a scene, `format`, the title, `root` or `lang`. Leave each other line. It is about
`movie.json` or about another chapter, and the orchestrator fixes it. Run the command again after each
change of `script.json`.

If the command exits with 2, it cannot read `movie.json`. Run it again one time. If it exits with 2 again,
stop the chapter with the reason `movie.json cannot be read`.

### The chapter gate

The review flag is `{review}`. If it is `off`, start no subagent.

If it is `on`, run the chapter gate after the check and before your first render. Read "The chapter gate"
of `{skill_dir}/rungs/movie.md`, and do as it says. The prompt of the gate is
`{skill_dir}/movie/review-chapter.md`. That subsection gives the rounds, the paths of the reports, the
`## Author` block that you append to each report, and the verification reads.

Start each reviewer as a fresh subagent. In Claude Code, use the Agent tool. In OpenCode, use the `task`
tool with the `general` agent.

A finding that stays `open` after the last round does not stop the chapter. The chapter ships: render it,
and end with `chapter: {chapter_id} built`. Before that line, write one `disputed: <finding>` line for each such finding.
`<finding>` is the finding and your reason to keep the text, in STE, on one line. The orchestrator writes
these lines into `movie.json`.

If the review flag is `on` and you cannot start a subagent, build the chapter without the gate. Then write
the line `disputed: the chapter gate did not run` before the result line. Thus the movie tells what ran.

### Render and read the stills

Run this command, as "Build and check" of `video.md` says:

```
{skill_dir}/scripts/render.sh {movie_dir}/chapters/{chapter_id}
```

Fix the cause of each `FAIL` line, and run the command again. Do this until its eleven stage lines show
`ok`. Then read the stills as "Read the stills" of `video.md` says. Fix each fault, and render again.

Stop a fix loop after 3 rounds in which the same `FAIL` line comes back. Also stop at once for a fault of
the environment, such as a `workspace`, `narration` or `container` `FAIL` line that your files did not
cause. Then stop the chapter with the `FAIL` line as the reason.

Never run `open`. The orchestrator joins your `video.mp4` into the movie.

## Result

Your reply ends with one line. Write nothing after it. The `disputed:` lines come before it.

- When the chapter is complete: `chapter: {chapter_id} built`. Its render shows eleven `ok` lines, and its
  stills have no fault.
- When you stop the chapter: `chapter: {chapter_id} failed <reason>`. The reason is one line, such as the
  `FAIL` line of the render.
