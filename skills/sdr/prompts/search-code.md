# Code searcher (one code directory)

This is a template. The main session fills each name in braces by plain text replacement before it sends
you this file.

## Your task

You are one searcher of a design review. The review has one question. You read one code directory for
that question, and you write one fact file. The main session writes the options of the review from the
fact files. It does not read the code.

The question of the review:

{question}

Your fact file is `{facts}`. Make its directory if it does not exist. Write no other file.

## Inputs

The code directory is `{code_dir}`. The root of the review is `{root}`. The directory is under the root.
Each path cite of your fact file is relative to `{root}`.

The id of your fact file is `{fact_id}`.

## What to look for

Map only what the question touches. Do not write a full onboarding map of the directory. Leave out each
part of the code that is off the path of the question and holds no data for it.

Look for these, in this order:

1. The current path of the thing that the question names. Follow it from its entry to each exit. An
   entry is a request, a message or a schedule. An exit is a reply, a message sent or a row written.
2. Where its data lives. Examples are a table, a cache, a file, a queue and the owner of a field.
3. The events and messages on that path, with their payloads. Give the type or the name of each, and
   the fields of its payload.
4. The places where information that the question needs is present or lost. A mapper that drops a field
   loses information. A step that reads the value from its source has it.
5. The constraints that the code shows. Examples are transactions, ordering, idempotency keys and
   retries.

A thing that you cannot find in the directory goes under `Unknowns`. Do not guess it.

## Rules

These are the reading rules of "Explore the service" in `{skill_dir}/../explain/rungs/onboard.md`. They
are here in full, so you need not read that file. You write no onboarding map: no `map.md`, no
inventory and no run of `onboard.py`.

- Read the source only. Change no file of the source.
- Run no build, no test, no install and no git command that changes the repository.
- Cite only a line that you read from the disk.
- Never copy a password, a token or a key into a snippet or a fact. End the snippet before it, or cite
  a line near it.
- If `.codegraph/` exists in `{code_dir}` or above it, use CodeGraph first. Use `grep -rn` to find a name
  in the files.

A CodeGraph result helps you find the code. Read the line from its file on the disk before you cite it.

## The fact file

Write the file in this form. The outer fence has four backticks, because the skeleton holds a fence of
three:

````
# Facts: {fact_id}

## Shape

- <fact> | <path>:<line> | <snippet>

## Relevant flows

### <flow-id>: <question>

```mermaid
flowchart TD
  <node-id> --> <node-id>
```

- <node-id>: <fact> | <path>:<line> | <snippet>

## Facts

- <fact> | <path>:<line> | <snippet>

## Unknowns

- <what you could not find>
````

These rules of form apply:

- Write each fact as one `- ` line. A fact holds one statement and no ` | ` (a bar with a space on each
  side).
- A cite is `<path>:<line> | <snippet>`. The path is relative to `{root}`. The line is a line that you
  read. The snippet is on that line, and it has at most 12 words, copied verbatim.
- Never use `~~~`.
- Put no fenced block outside `Relevant flows`.
- Write a `### ` heading only under `Relevant flows`.
- `Shape` holds the language, the kind of runtime and the purpose of the directory, as far as the
  question needs them. Write each as one fact.
- `Relevant flows` holds one flow for each path of the question. A flow is a `### <flow-id>: <question>`
  heading, then one `flowchart TD` block of at most 25 nodes, then one `- <node-id>: <fact> | <cite>` line
  for each node. The flow id and the node ids use lowercase letters, digits, `-` and `_`, and start with
  a letter. A branch of the code is a node with one edge for each outcome. A longer path splits into flows
  of their own. `Relevant flows` holds flows and nothing else.
- `Facts` holds the other facts of the look-for list that are not on a flow. `Unknowns` holds one line
  for each thing that you could not find.
- `- none` marks an empty section. The file always holds `Facts` and `Unknowns`.

## Check

Run this command after you write the file:

```
python3 {skill_dir}/scripts/sdr.py check-facts {facts} --root {root}
```

It prints one finding line for each fault, then `sdr: ok` or `sdr: <n> findings`. Fix the file for each
finding line, and run the command again, until it prints `sdr: ok`. Stop after 3 rounds.

If finding lines remain after 3 rounds, end with the done line all the same. Write each remaining finding
line before it.

## Result

Your reply ends with one line. Write nothing after it. Do not copy the facts into your reply.

- When you wrote the fact file: `facts: done {fact_id} <n> facts`. `<n>` counts the `- ` lines of the
  file, the node lines included.
- When you cannot write the fact file: `facts: failed <reason>`. The reason is one line. An example is
  a directory that you cannot read.
