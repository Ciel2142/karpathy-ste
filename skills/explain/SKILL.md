---
name: explain
description: Use when the user invokes /explain — explain a subject (file, directory, `this`, or topic) in the best rung, from chat text to a one-page sheet, an interactive page, or a narrated video.
disable-model-invocation: true
argument-hint: "<subject> [--as ste|sheet|page|video]"
---

# explain

`explain` is a router. It resolves a subject, chooses a rung (a form of output), and builds
the artifact. Only the user starts it, with `/explain`.

## Contract

Syntax: `/explain <subject> [--as ste|sheet|page|video]`. The arguments arrive in `$ARGUMENTS`.

1. If `$ARGUMENTS` is empty, stop with a usage error. Print the `argument-hint`.
2. Find the last `--as <rung>` pair in `$ARGUMENTS`. The last pair wins. Remove it.
3. If `--as` is present and its value is not `ste`, `sheet`, `page` or `video`, stop with
   an error. List these four names in the error.
4. Trim the rest. The result is the subject.

## Subject resolution

Use the first rule that applies.

1. Path candidate. A subject that starts with `/`, `~` or `.` is a path candidate. A
   subject whose first `/`-separated component exists in the current directory is also
   one. Subjects such as `TCP/IP`, `CI/CD` and `Next.js` are not path candidates.
   - A path candidate that exists: read a file in full. Map a directory: its tree and its
     key files. If a `.codegraph/` index exists, use CodeGraph.
   - A path candidate that does not exist is an error. A missing path is never a topic.
2. `this`: the last file that you read or wrote in the conversation. If there is none, use the
   last substantial turn (an explanation, a review, or a plan). Label it "conversation".
3. Otherwise the subject is a topic. If the current directory is inside a git repository
   and the topic is about its code, read that code first. Use CodeGraph when `.codegraph/`
   exists. Read with the Read tool each file that CodeGraph flags as changed or omits.
   Cite only lines that you read from disk. Then convention 2 applies. If the topic is not
   about that code, use your own knowledge. Use web lookups only if the user says yes.
   Provenance states "model knowledge" or lists the URLs. Never claim that you read a
   source that you did not read.

## Rung selection

If `--as` is absent, choose the rung from the shape of the content, never from the richest
format. A facet is one question that the artifact answers: one panel on a sheet or one
section on a page.

| Rung | Choose when | Typical subject |
|---|---|---|
| `ste` (chat text) | The answer fits one screen; it is procedural or a direct answer; the user is mid-task | A failure cause, a 5-step procedure |
| `sheet` (static page, exported to PNG) | Reference material for repeated glances; at most 6 facets; "overview of X" | Architecture at a glance, a spec summary |
| `page` (interactive single-file HTML) | The content has state to explore (a step-through flow, before and after, toggles); more than 6 facets | A PR walkthrough, a plan with waves |
| `video` (narrated mp4) | A temporal narrative where motion carries meaning | Data in a pipeline, a handshake |

Read the subject before you choose the rung: the file, the directory, or the repo code of
a topic. A model-knowledge topic has no source to read. Before you build, print this line,
also under `--as`:

`Rung: <rung> (chosen|forced) — <reason> — subject: <subject> (<kind>)`

`<kind>` is `file`, `directory`, `conversation` or `topic`. Under `--as`, the `<reason>`
names the flag and tells if the content fits the rung. Then follow these rules:

- The `video` rung, chosen or forced with `--as video`, builds a narrated mp4 as
  `rungs/video.md` shows. The video rung is English only.
- If `rungs/<rung>.md` does not exist for the chosen rung (also a `page` from the video
  fallback), print the rung line. Say that the rung is not available yet. Stop. Offer
  `sheet` or `ste`.
- A forced rung can be too small for the content, for example a sheet for more than 6
  facets. Keep the 6 most important facets. List the dropped facets in `p.not-covered`
  (the title block of a sheet, the footer of a page). `Not covered` lists every facet
  that the artifact does not explain, for any reason.
- The `ste` rung gives chat text only. It makes no output directory. Write that text under
  the STE profile: read `~/.claude/skills/ste/SKILL.md` by path. The Build procedure
  applies to the artifact rungs only.

## Conventions

These seven rules apply to every artifact rung (`sheet`, `page`, `video`).

1. Prose: follow the STE profile. The final `index.html` passes `ste_lint.py --html` with 0 errors.
2. Grounded: read the real source of the subject first. Every claim carries a citation:
   `<cite data-path="…" data-line="…" data-snippet="…">name:line "snippet"</cite>`. The
   snippet has at most 12 words, copied verbatim from that line. `data-path` holds the full
   path relative to `data-root`. `name` is its basename, or a longer tail if two cited files
   have that basename. A path citation fails `cite_check.py` if its visible text does not
   hold `basename:line`, or the provenance element has no `data-root`. Never copy a password,
   a token or a key into a snippet or the prose. End the snippet before it, or cite a line
   near it. For a file or a directory subject, each panel or section (a `<section>` element)
   holds at least one `<cite>`. Mark a cited file that git does not track (in a repository,
   `git ls-files --error-unmatch` fails) as "untracked". A URL citation has a `data-path`
   that starts with `http://` or `https://`. Its snippet comes from the fetched page.
   Provenance, the element with `id="provenance"` in the title block or the footer, gives the
   subject, its kind and the date. For a subject in a repository, it also gives the root, the
   commit hash and a `dirty` flag (`git status --porcelain` printed something). It carries
   `data-root="<absolute repo root>"` and `data-kind="file|directory|topic|conversation"`. If
   `git rev-parse --show-toplevel` fails, `data-root` is the subject's directory (file,
   directory) or the current directory (topic, conversation). Commit is `none`, Dirty is `no`
   and no `<cite>` gets "untracked". For a directory subject in a repository, `data-kind` is
   `directory` and `data-root` is the repo root (run `git rev-parse --show-toplevel` in that
   directory). `<cite>` paths are relative to the repo root, not to the subject directory. A
   topic that you answer from files of a git repository (the current directory is inside it)
   has `data-kind="topic"`. Its `data-root` and Source are that repo root, not "model
   knowledge". Each claim about a file carries a `<cite>`. A topic without files has
   `data-root` set to the current directory, Commit `none`, Dirty `no` and Source "model
   knowledge" (or the URLs). This rule applies also inside a repository. Mark a
   "conversation" subject "unverified", and re-read and cite each file that it mentions.
3. One self-contained file: inline CSS and JS, system fonts, no CDN, no build step. It
   opens from `file://` offline.
4. Check the artifact before handoff, in two layers (see Build procedure).
5. Discardable output: `~/karpathy/out/YYYY-MM-DD-HHMMSS-<rung>-<slug>/`. The time stamp is
   local time. Make the `<slug>` from the subject in four steps. Change it to lowercase.
   Change each run of characters outside `a-z0-9` to one `-`. Keep the first 40 characters.
   Remove `-` at the two ends. If the result is empty, the slug is `topic`. Never overwrite a
   directory. A re-run makes a new directory. The rung file lists the contents. Git ignores
   `out/`. Never commit it.
6. Handoff: print the path. When you run for the user directly, run `open index.html`
   (sheet or page) or `open video.mp4` (video). Inside a subagent, do not run `open`.
7. Language: write the artifact in English, unless the user asks for another language.

## Build procedure

1. Read `~/.claude/skills/ste/SKILL.md` by path. Write all prose under that profile.
2. Read `rungs/<rung>.md` of the chosen rung only, and each section that it names.
   For a video, the rung file replaces steps 3 to 6 (write `script.json`, run `render.sh`, read the stills).
3. Write `index.html` in the output directory.
4. Run `~/.claude/skills/explain/scripts/verify.sh <output-dir>/index.html`. It must exit 0.
5. Run `~/.claude/skills/explain/scripts/snapshot.sh` as the rung file shows. Read the
   review tiles. Never read the full render. Check the hierarchy and the layout.
   Check that no text gives a false picture.
6. Fix each problem. Run steps 4 and 5 again.
7. Do the handoff (convention 6).

## Rung files

- `rungs/sheet.md`: the sheet rung (canvas, panels, template, snapshot arguments).
- `rungs/page.md`: the page rung (sections, steps player, diagram patterns, template,
  snapshot arguments).
- `rungs/video.md`: the video rung (script, components, cue rule, render pipeline, pinned versions).
