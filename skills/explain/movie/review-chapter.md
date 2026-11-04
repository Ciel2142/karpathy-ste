# Movie chapter script reviewer (the chapter gate)

This is a template. The author of the chapter fills each name in braces by plain text replacement before it
sends you this file.

## Your task

You are a cold reviewer of one chapter of a movie on {subject}. A movie is one theme as one continuous film, cut
into chapters. After the movie, a cold viewer answers a list of viewer questions from the film alone. Each
chapter answers one or two of these questions.

Your artifact is the script of the chapter `{chapter_id}`, `chapters/{chapter_id}/script.json`: the narration
and the cites of each scene. Its first scene, `ask`, asks the question of the chapter. Its last scene, `answer`,
states the answers. The body scenes between them show the answers. You did not write the script, and you have no
other context than this prompt and the files below.

You review. You change no file except your report. Write your report to {report}.

## Inputs

The files, one absolute path per line:

{files}

It is the `script.json` of the chapter. Its path ends in `chapters/{chapter_id}/script.json`. The directory that
holds `chapters/` is the directory of the movie.

These are the viewer questions that the chapter answers, with their answers and their cites, as JSON:

{questions_json}

Each question has an `id`, a `text`, an `answer` and its `cites`. The `answer` is the answer that a viewer must
give after the film.

The root is `{root}`. Each cite of `script.json` and of the questions has a `path` that is relative to the root, a
`line` and a `snippet`. Read the cited file under the root, not a copy. A cite whose `path` starts with `http://`
or `https://` has no `line`. Read that page, and find the snippet in it.

Read only the files above, the files under the root and the pages of the URL cites. Under the directory of the
movie, read no file except the files above and the report that Round 2 names. Thus do not read `movie.json`, the
scene code of the chapter, another chapter or a bridge. This holds when the directory of the movie is under the
root.

## Hunt

Hunt. Assume one claim in this script is not supported by its cited lines, or does not agree with the questions
above, and find it.

Read every cite against the source, and each answer against the narration. If you then find no fault, write
`verdict: ok` with zero findings. That is the right answer for a correct artifact.

Never report a finding you cannot back with a quoted source line.

The author ran `movie.py check`: the ids of the `ask` and `answer` scenes, the title, the root and the language of
the script are correct. Later, the render checks the other mechanical facts. Each cite must resolve to a line, and
the words of each scene must be in their limits. The narration must pass the lint.

Do not do that work. Read for meaning. The cites of a scene cover the narration of that scene.

## Checks

Make these checks, in this order.

1. The narration makes no claim that the cited lines, read from `{root}`, do not support.
2. The `answer` scene states each `answer` of the questions above without contradicting it. Compare the meaning,
   not the words. The scene may say less, never something different.
3. The `ask` scene poses the question of the chapter: the question that the answers above answer. It asks for
   nothing that those answers do not give.

Do not judge the picture. The render comes after this review. Then the author reads the stills, and a cold viewer
tests the whole film.

## Round 2

If `{previous}` is `none`, this is round 1: skip this section.

Otherwise `{previous}` is the absolute path of the report of the last round. It has a `## Author` block that the
author appended: for each finding, `fixed` with what changed, or `not fixed` with why. Read the report first. The
word of the author is not a ruling.

If the name of `{previous}` ends in `-round-2.md` or `-round-3.md`, this is a verification read: rule its findings
and hunt for nothing new. The Hunt section does not apply to a verification read.

Before you hunt, rule each finding of that report `resolved` or `open`, and quote the current source line. Read
`script.json` as it is now. A finding is `resolved` in each of these cases:

- the narration no longer makes the claim that the finding quoted;
- the cited lines now support the claim;
- the `ask` or the `answer` scene now agrees with the questions above.

Otherwise it is `open`.

Write the rulings at the top of your report, one for each finding: its number, `resolved` or `open`, and the
quoted line. Then, unless this is a verification read, hunt as the Hunt section says, and number each new finding
after the old ones. An `open` finding counts as a finding of this report.

In a verification read, write `verdict: ok` when each finding is `resolved`, and `verdict: fix` when one is
`open`.

## Report

Write the report to {report}. It holds the rulings of round 2, if any, and a numbered list of findings (`1.`,
`2.`, and on). Each finding has:

- the number of the check that it fails: 1, 2 or 3;
- the location: a scene id of `script.json`;
- the claim, quoted;
- the source lines, quoted verbatim as read from `{root}`;
- what is wrong;
- a fix in one line.

For a finding of check 2 or check 3, quote two source lines verbatim. One is the `answer` or the `text` of the
question. The other is the sentence of the narration that disagrees with it.

A finding without a quoted source line is not a finding.

The last line of your text is `verdict: ok` or `verdict: fix`.

Write `verdict: fix` when the report has at least one finding.

The report file ends with the same line. With no finding, it holds the rulings, if any, and that line.

The author appends `## Author` to the report, after your last line. You do not write it.
