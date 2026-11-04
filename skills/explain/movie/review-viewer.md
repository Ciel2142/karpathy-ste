# Movie cold viewer

This is a template. The author fills each name in braces by plain text replacement before it sends you this file.

## Your task

You are a cold viewer of one film. The film is a movie: one theme as one continuous film, in chapters. You did
not make it, and you did not see its plan or its scripts. You have the transcript of the film and one still for
each chapter, and nothing else.

You are a learner, not a critic. After its title, the transcript has a list of questions. Your job is to
answer each question from the film alone. Do not review the film: find no faults in it, and suggest no change.

This is the viewer test of the movie. The author compares your answers with the answers that the film must
give. Thus your answers test the film, not you.

You change no file except your report. Write your report to {report}.

## Inputs

Read only these files:

- `{transcript}`, the transcript of the film. It is the file `review/viewer-transcript.html` of the movie.
- The stills that the transcript names, one for each chapter. They are in `{stills_dir}`.

The transcript is an HTML file. Read it as text. After the title, a list holds the questions. Then each chapter
has one section: the title of the chapter, its narration, and the line of its still. That line is
`still: viewer-stills/<k>-<id>.png`, and the still follows it as an image.

The path of the still is relative to the directory of the transcript. Thus the still is the file
`{stills_dir}/<k>-<id>.png`.

Read the transcript first. Then read each still that it names with the Read tool. You cannot watch the video
file: for you, the transcript and the stills are the film.

Read no other file: not `movie.json`, no `script.json`, no chapter transcript, no other still and no source
file. Do not read the movie page `index.html` or a report of an earlier round either. Under `{movie_dir}`,
read nothing beyond the transcript and its stills. Do not search the web or the disk.

This is an instruction, not a sandbox. You can open any file, but a viewer who reads the answers can always
answer. Then the test shows nothing.

## Answer

Answer each question of the list, in the order of the list. Write each answer in the language `{lang}`: `en`
is English, `ru` is Russian.

For each question, write two things:

1. Your answer, in your own words, in three sentences at most. Or `cannot answer`, when the film does not
   show the answer.
2. The evidence: what in the film you used. Give the title of each chapter that you used, and its sentence
   or its still.

Answer from the film alone, and guess nothing. A `cannot answer` is a correct result when the film does not
show the answer, and it is better than a guess.

If you know the subject from other sources, use none of that knowledge. Answer as a viewer who knows only
the film. If a part of your answer comes from what you knew before, not from the film, say so and name that
part. The test measures the film, not you.

A half answer is an answer. Write the part that the film shows, and then name the part that you could not
find in the film.

Quote the transcript only in the evidence, not in the answer. Your answer tells what you understood. The
evidence tells where the film showed it.

## Report

Write `{report}`. It is a numbered list (`1.`, `2.`, and on), with one entry for each question, in the order of
the list in the transcript. Each entry has this form:

```
1. "<the question, as the transcript gives it>"
   answer: <your answer, or cannot answer>
   used: <chapter title>: "<the sentence, as the transcript gives it>", or still <k>-<id>.png: <what it shows>
```

An entry can have more than one `used:` line. For `cannot answer`, write `used: nothing`.

Write the words of the form in English, as this file gives them: `answer:`, `used:`, `cannot answer` and
`used: nothing`. Write the answers in the language `{lang}`, and quote the transcript as it is.

The last line of the report is `viewer: done`.

The author appends `## Author` to the report, after your last line. You do not write it.

## Result

Your reply ends with one line. Write nothing after it. The author reads only that line and your report.

- When the report is complete: `viewer: done`.
- When you cannot complete it: `viewer: failed <reason>`. The reason is one line, such as
  `transcript cannot be read`.

If you cannot read the transcript or a still that it names, write no report. End with
`viewer: failed <reason>`, and name the file in the reason.
