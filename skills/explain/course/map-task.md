# Course map (one source)

This is a template. The orchestrator fills each name in braces by plain text replacement before it sends
you this file.

## Your task

You map one source of a course. A course follows one message through a system of several services, hop
by hop. The orchestrator plans the course from the maps of all the sources.

The source has the id `{source_id}`. Its path is `{source_path}`. The root of the course is `{root}`.

Write two files: `{course_dir}/map/{source_id}.md` and `{course_dir}/map/{source_id}.inventory.txt`. Make
the directory `{course_dir}/map/` if it does not exist. Write no other file.

## What to follow

Follow "Explore the service" and then "The map" of `{skill_dir}/rungs/onboard.md`. These overrides apply:

- `<service-dir>` is `{source_path}`.
- `<root>` is `{root}`.
- The map file is `{course_dir}/map/{source_id}.md`, in place of `map.md`. The inventory file is
  `{course_dir}/map/{source_id}.inventory.txt`, in place of `inventory.txt`.
- The first line of the map is `# Map: {source_id}`.
- Run the inventory with this command:

  ```
  python3 {skill_dir}/scripts/onboard.py inventory {source_path} --root {root} --out {course_dir}/map/{source_id}.inventory.txt
  ```

- Run the check with this command:

  ```
  python3 {skill_dir}/scripts/onboard.py check {course_dir}/map/{source_id}.md --root {root} --inventory {course_dir}/map/{source_id}.inventory.txt
  ```

- Write `none found` under `Architecture`, `Flows` and `State` when the source has no code to trace.
  A docs source that documents a request sequence still gets a flow, as "The map" says.
- Write the map in the language `{lang}`: `en` for English, `ru` for Russian. Keep each code name in
  backticks in the two languages.
- Write one short sentence for each fact. The map is for the orchestrator, not for a reader.

## Check

Run the inventory first and the check last. Fix the map for each failure line, and run the check again,
until it prints `onboard: ok`. Stop after 3 rounds in which the same failure lines come back.

If failure lines remain, end with `map: done` all the same. Write each failure line before it.

## Result

Your reply ends with one line. Write nothing after it. Do not copy the map into your reply.

- When you wrote the map file: `map: done {source_id} <n> facts`. `<n>` counts the fact lines of the map,
  the node lines included.
- When you cannot write the map: `map: failed <reason>`. The reason is one line. Examples are a source
  that you cannot read and a source with no code and no docs.
