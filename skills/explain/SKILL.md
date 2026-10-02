---
name: explain
description: Use when the user invokes /explain — explain a subject (file, directory, `this`, or topic) in the best artifact rung: chat text, a one-page sheet, an interactive page, or a narrated video.
disable-model-invocation: true
argument-hint: "<subject> [--as ste|sheet|page|video]"
---

# explain

`explain` is a router. It resolves a subject, chooses a rung (a form of output), and builds
the artifact. Only the user starts it, with `/explain`.

## Contract

Syntax: `/explain <subject> [--as ste|sheet|page|video]`. The arguments arrive in `$ARGUMENTS`.

1. Find the last `--as <rung>` pair in `$ARGUMENTS`. The last pair wins. Remove it.
2. Trim the rest. The result is the subject.
3. If the rung is not `ste`, `sheet`, `page` or `video`, stop with an error. List these
   four names in the error.
4. If `$ARGUMENTS` is empty, stop with a usage error. Print the `argument-hint`.

## Subject resolution

Use the first rule that applies.

1. Path candidate. A subject that starts with `/`, `~` or `.` is a path candidate. A
   subject whose first `/`-separated component exists in the current directory is also one. Subjects such as
   `TCP/IP`, `CI/CD` and `Next.js` are not path candidates.
   - A path candidate that exists: read a file in full. Map a directory: its tree and its
     key files. If a `.codegraph/` index exists, use CodeGraph.
   - A path candidate that does not exist is an error. A missing path is never a topic.
2. `this`: the last file that you read or wrote in the conversation. If there is none,
   use the last substantial turn (an explanation, a review, or a plan). Label it
   "conversation".
3. Otherwise the subject is a topic. Use your own knowledge. Use web lookups only if the
   user says yes. Provenance states "model knowledge" or lists the URLs. Never claim
   that you read a source that you did not read.

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

Before you build, print this line, also under `--as`:

`Rung: <rung> (chosen|forced) — <reason> — subject: <subject> (<kind>)`

`<kind>` is `file`, `directory`, `conversation` or `topic`. Then follow these rules:

- Offer `video` only if `rungs/video.md` exists. If it does not exist, `--as video` builds a
  `page` whose steps player shows the narration as step captions. Say so.
- A forced rung can be too small for the content, for example a sheet for more than 6
  facets. Keep the 6 most important facets. List the dropped facets in the title block
  under "Not covered".
- The `ste` rung gives chat text only. It makes no output directory.

## Conventions

These seven rules apply to every artifact rung (`sheet`, `page`, `video`).

1. Prose: follow the STE profile. The final `index.html` passes `ste_lint.py --html`
   with 0 errors.
2. Grounded: read the real source of the subject first. Every claim carries a citation:
   `<cite data-path="…" data-line="…" data-snippet="…">path:line "snippet"</cite>`.
   The snippet has at most 12 words, copied verbatim from that line. For a file or a
   directory subject, each panel or section (a `<section>` element) holds at least one
   `<cite>`. Mark a cited file that git does not track as "untracked".
   A URL citation has a `data-path` that starts with `http://` or `https://`.
   Its snippet comes from the page that you fetched.
   Provenance is an element with `id="provenance"` in the title block or the footer.
   It gives the subject, its kind and the date. For a subject in a git repository, it
   also gives the repo root and the commit hash. It gives a `dirty` flag too
   (`git status --porcelain` printed something). It carries
   `data-root="<absolute repo root, or the subject directory>"` and `data-kind="file|directory|topic|conversation"`. Mark a "conversation" subject
   "unverified", and re-read and cite each file that it mentions.
3. One self-contained file: inline CSS and JS, system fonts, no CDN, no build step. It
   opens from `file://` offline.
4. Check the artifact before handoff, in two layers (see Build procedure).
5. Discardable output: `~/karpathy/out/YYYY-MM-DD-HHMMSS-<rung>-<slug>/`. The `<slug>` is the
   subject in kebab-case, at most 40 characters. Never overwrite a directory. A re-run
   makes a new directory. The rung file lists the contents. Git ignores `out/`. Never commit it.
6. Handoff: print the path. When you run for the user directly, run `open index.html`
   (sheet or page) or `open video.mp4` (video). Inside a subagent, do not run `open`.
7. Language: write the artifact in English, unless the user asks for another language.

## Build procedure

1. Read `~/.claude/skills/ste/SKILL.md` by path. Write all prose under that profile.
2. Read the rung file for the chosen rung only: `rungs/<rung>.md` in this skill directory.
3. Write `index.html` in the output directory.
4. Run `~/.claude/skills/explain/scripts/verify.sh <output-dir>/index.html`. It must exit 0.
5. Run `~/.claude/skills/explain/scripts/snapshot.sh` as the rung file shows. Read the
   review tiles. Never read the full render. Check the hierarchy and the layout.
   Check that no text gives a false picture.
6. Fix each problem. Run steps 4 and 5 again.
7. Do the handoff (convention 6).

## Rung files

- `rungs/sheet.md`: the sheet rung (canvas, panels, template, snapshot arguments).
- `rungs/page.md`: does not exist yet. `--as page` is not available until wave explain-page.
- `rungs/video.md`: does not exist yet. `--as video` uses the video fallback (Rung selection).
