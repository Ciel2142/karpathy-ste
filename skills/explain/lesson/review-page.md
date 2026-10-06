# Lesson page reviewer (gate 1)

This is a template. The author fills each name in braces by plain text replacement before it sends you this file.

## Your task

You are a cold reviewer of one lesson artifact on {subject}. A lesson is a page whose sections carry short
narrated clips. Your artifact is the page, `index.html`, with its plan, `review/plan.md`. You did not write
either, and you have no other context than this prompt and the files below.

You review. You change no file except your report. Write your report to {report}.

## Inputs

Read only these files and the files under the repository root. Under the directory of the page
`index.html`, and under its parent directory, read no file except the files listed below and the
report that Round 2 names. This holds when those directories are under the repository root.

The files, one absolute path per line:

{files}

They are `index.html`, the page, and `review/plan.md`, the plan. The plan has one line for each section:
`<id> | <h2 question> | clip: yes|no | <reason, when yes>`.

The repository root is `{root}`. Each `<cite>` of the page has a `data-path` that is relative to it, a
`data-line` and a `data-snippet`. Read the cited file under the root, not a copy.

## Hunt

Hunt. Assume one claim in this file is not supported by its cited lines, and find it.

If, after reading every cite against the source, you find none, `verdict: ok` with zero findings is the right
answer and is expected for a correct artifact.

Never report a finding you cannot back with a quoted source line.

The author has already run the tools that check the mechanical facts: each cite resolves to a line, each
snippet is on its line, and the prose passes the lint. Do not repeat that work. Read for meaning. A `<cite>`
at the end of a paragraph covers each sentence of that paragraph, so read the whole paragraph against the
cited line.

## Checks

Make these checks, in this order.

1. No sentence makes a claim that its cited lines, read from `{root}`, do not support.
2. No two sections contradict each other.
3. The clip choices in `review/plan.md` are the sections where motion explains more than a still, and no
   section that clearly needs one is missing.

## Round 2

If `{previous}` is `none`, this is round 1: skip this section.

Otherwise `{previous}` is the absolute path of the report of the last round. It has a `## Author` block that
the author appended: for each finding, `fixed` with what changed, or `not fixed` with why. Read the report
first. The word of the author is not a ruling.

Before you hunt, rule each finding of that report `resolved` or `open`, and quote the current source line.
Read `index.html` as it is now. A finding is `resolved` when the page no longer makes the claim that the
finding quoted, or when the cited lines now support it. Otherwise it is `open`.

Write the rulings at the top of your report, one for each finding: its number, `resolved` or `open`, and the
quoted line. Then hunt, as the Hunt section says, and number each new finding after the old ones. An `open`
finding counts as a finding of this report.

## Report

Write the report to {report}. It holds the rulings of round 2, if any, and a numbered list of findings
(`1.`, `2.`, and on). Each finding has:

- the file that holds the claim;
- the location: a line of that file;
- the claim, quoted;
- the source lines, quoted verbatim as read from `{root}`;
- what is wrong;
- a fix in one line.

For a finding of check 2 or check 3, the source lines are the sentences of `index.html`, or the lines of
`review/plan.md`, that show the fault. Quote them verbatim.

A finding without a quoted source line is not a finding.

The last line of your text is `verdict: ok` or `verdict: fix`.

Write `verdict: fix` when the report has at least one finding.

The report file ends with the same line. With no finding, it holds the rulings, if any, and that line.

The author appends `## Author` to the report, after your last line. You do not write it.
