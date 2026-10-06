# karpathy-ste

Two [Claude Code](https://claude.com/claude-code) skills, kept in one repository and linked
into `~/.claude/skills/`:

- **`/ste`** — rewrite text, or answer a request, in STE-80: a fixed profile of ASD-STE100
  Simplified Technical English (Issue 9). Ships a lint (`ste_lint.py`) that checks markdown
  or HTML prose against the deterministic rules.
- **`/explain <subject> [--as ste|sheet|page|video|brainrot|lesson]`** — explain a file, a
  directory, `this` (the last thing in the conversation) or a topic, in the smallest form that
  fits: chat text, a one-page sheet (HTML + PNG), an interactive single-file page, a narrated
  film (`--as video`: one continuous picture, written for the subject and timed to the
  narration, with a cited transcript), a vertical 1080×1920 brainrot short (`--as brainrot`: a
  looping background and word-by-word captions), or a lesson (`--as lesson`: a page whose
  sections carry short narrated clips, with two review gates). Every artifact is grounded: each
  claim carries a `<cite>` to a real `path:line` and a verbatim snippet, and `verify.sh` fails
  the build when a cite does not match the file, the page does not render, or the prose breaks
  the STE profile.

Both skills are user-invoked only (`disable-model-invocation: true`).

## Install

```sh
git clone https://github.com/Ciel2142/karpathy-ste.git ~/karpathy
mkdir -p ~/.claude/skills
ln -s ~/karpathy/skills/ste     ~/.claude/skills/ste
ln -s ~/karpathy/skills/explain ~/.claude/skills/explain
```

The scripts resolve their own directory through the symlink, so the clone location is yours
to choose; the artifacts land under `<clone>/out/` (gitignored).

## Requirements

| Rung | Needs |
|---|---|
| `ste` (chat text) | `python3` (stdlib only) |
| `sheet`, `page` | Google Chrome at `/Applications/Google Chrome.app` (used headless for the render check and the PNG snapshots) |
| `video` | `node` (proven on 25.9; an LTS is fine), `npm`, `uv`, `rsync`, `curl`, `shasum`; macOS `say` and `afinfo` |
| `lesson` | the needs of `page` and of `video` together |

As written the `sheet`, `page` and `video` rungs are macOS-specific (the Chrome path, `say`,
`afinfo`). `ste` runs anywhere.

The first video run sets up a gitignored workspace by itself (`<clone>/video-workspace/`, or
`EXPLAIN_VIDEO_WORKSPACE`) and prints each cost before paying it: `npm ci` ≈ 55 s / 503 MB,
Chrome Headless Shell 193 MB, the two Kokoro model files 353 MB, a `uv` resolve ≈ 30 s. Nothing
is installed globally. Later runs reuse the workspace and any narration whose text did not
change; a one-minute video renders in about 12 s on an Apple Silicon Mac.

The narrator is Kokoro `af_heart` (via `uv`, pinned packages). When Kokoro cannot run, the
pipeline falls back to the macOS `say` voice and labels the fallback in its output and in the
transcript's Narrator row.

Versions are pinned in `skills/explain/video/package.json`: Remotion 4.0.532, React 19.2.3.
Remotion is free under its Free License for an individual or a company of up to 3 employees;
check the licence again beyond that.

## Layout

```
skills/ste/        SKILL.md, scripts/ste_lint.py, tests/
skills/explain/    SKILL.md (router + conventions), rungs/{sheet,page,video,brainrot,lesson}.md,
                   lesson/ (the reviewer prompts), templates/,
                   scripts/{verify,snapshot,render,narrate,video-workspace}.sh,
                   scripts/cite_check.py, video/ (Remotion app + pipeline; video/src/kit/ is
                   the film kit, video/src/film/ the worked example), tests/
docs/superpowers/  the spec, wave map, plans and live-run notes behind the skills
```

## Tests

```sh
cd skills/ste     && python3 -B -m unittest discover -s tests
cd skills/explain && python3 -B -m unittest discover -s tests
EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render tests.test_check_render  # renders once, needs the workspace
EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_brainrot  # two brainrot renders (generated loop, fixture clip), needs the workspace
EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render_film  # renders the worked film and its planted faults, needs the workspace
EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_lesson_e2e  # renders a one-clip fixture lesson, needs the workspace
```
