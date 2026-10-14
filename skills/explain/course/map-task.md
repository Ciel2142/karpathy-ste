# Course map (one source)

This is a template. The orchestrator fills each name in braces by plain text replacement before it sends
you this file.

## Your task

You map one source of a course. A course follows one message through a system of several services, hop
by hop. The orchestrator plans the course from the maps of all the sources. Your map tells it what this
source does with a message. It says where the message comes in, what changes it, where it goes and what
occurs when a step fails.

The source has the id `{source_id}`. Its path is `{source_path}`. The root of the course is `{root}`. Each
path in your map is relative to `{root}`.

Write one file: `{course_dir}/map/{source_id}.md`. Make the directory `{course_dir}/map/` if it does not
exist. Write no other file.

## Rules

1. Read the source only. Change no file of the source. Run no build, no test, no install and no git
   command that changes the repository.
2. Read convention 2 of `{skill_dir}/SKILL.md` for the cite rules. Each fact of the map has one cite: a
   `<path>:<line>` relative to `{root}` and a snippet from that line.
3. A snippet has at most 12 words. Copy it verbatim from that one line.
4. Cite only a line that you read from the disk.
5. Never copy a password, a token or a key into a snippet or a fact. End the snippet before it, or cite a
   line near it.
6. Do not read the whole source. Start from the build files, the config files and the entry points. Read
   only the parts of a file that hold a fact.
7. If `.codegraph/` exists in the source, use CodeGraph first. Use `grep -rn` to find a name in the files.
8. Write one short sentence for each fact. The map is for the orchestrator, not for a reader.
9. Write the map in the language `{lang}`: `en` for English, `ru` for Russian. Keep each code name in
   backticks in the two languages.

## The map

The map has this skeleton. Keep the six level-2 headings, in this order. The orchestrator reads them by
their titles.

```
# Map: {source_id}

## Entry points
- <fact> | <path>:<line> | <snippet>

## In and out
- <fact> | <path>:<line> | <snippet>

## Formats and transforms
- <fact> | <path>:<line> | <snippet>

## Routing config
- <fact> | <path>:<line> | <snippet>

## Error paths
- <fact> | <path>:<line> | <snippet>

## Other systems
- <system>: <handles> | <path>:<line> | <snippet>
```

Each line that starts with `- ` is one fact. Each section holds these facts:

- `Entry points`: where a message enters the source. Examples are a queue listener, an HTTP controller, a
  scheduled job and a main function.
- `In and out`: what comes in and what goes out. Name each queue, topic, HTTP endpoint, file and table
  verbatim.
- `Formats and transforms`: the format of each message, and each change to its format or its content.
  Examples are XML, JSON, a message class, a mapper and an XSLT file.
- `Routing config`: the config that decides where a message goes. Name the file and the key. Examples
  are queue names, URLs, route rules and feature flags.
- `Error paths`: what the source does when a step fails. Examples are a retry, a dead letter queue, an
  error reply and a log line.
- `Other systems`: each other system that the source sends to or receives from. Give its name, then its
  handles: the names that find it in another repository. Examples are queue names, endpoints, artifact
  ids and host names. Put each handle in backticks.

If a section has no fact, write one line in it: `none found`.

## Result

Your reply ends with one line. Write nothing after it. Do not copy the map into your reply.

- When you wrote the map file: `map: done {source_id} <n> facts`. `<n>` is the number of fact lines in
  the map.
- When you cannot write the map: `map: failed <reason>`. The reason is one line. Examples are a source
  that you cannot read and a source with no code and no docs.
