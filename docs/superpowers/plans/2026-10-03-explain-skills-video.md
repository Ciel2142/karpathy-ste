# Plan — wave `explain-video`: the `video` rung of `/explain`

Spec: `docs/superpowers/specs/2026-10-02-explain-skills-design.md` §8.4 (pass path), §5.3
(conventions; item 5 lists a video's output as `index.html`, `video.mp4`, `narration.md`), §9
(one live `--as video` run). Spike: `docs/superpowers/spikes/2026-10-02-video-pipeline.md`
(verdict pass; its §5 list feeds `rungs/video.md`). Map: `docs/superpowers/waves/2026-10-02-explain-skills.yaml`,
wave `explain-video`. Risk: high (external dependencies: npm registry, a 350 MB model download,
a uv-managed Python; Remotion's licence). Coverage design: not opted in. Revision 2 after three
plan reviews (`.superpowers/sdd/2026-10-03-explain-skills-video/plan-review-*.md`); user
decisions 2026-10-03: `say` is an automatic, labelled fallback when Kokoro fails; first-run
setup runs by itself after printing its costs.

## 1. Goal and done-when

`/explain <subject> --as video` builds `out/<stamp>-video-<slug>/` with a narrated `video.mp4`
(Kokoro `af_heart`), a transcript `index.html` that carries the narration, the on-screen text,
every citation and the provenance, a `narration.md`, and review stills — by one command after
the script is written, with the same grounding and prose checks as the other rungs, run before
anything is synthesized or rendered.

Done when: a Claude-side live run (task 7) and the user's own `/explain <subject> --as video`
run (task 8) both produce a playable mp4 whose `scripts/render.sh` prints nine stage lines `ok`
and the render ratio, whose `verify.sh index.html` exits 0, whose stills show the right scene
state after each cue; three transcript claims spot-checked verbatim at `path:line`.

## 2. Current-code facts that constrain the change

- `skills/explain/SKILL.md` is at its 140-line budget. Line 65: offer `video` only if
  `rungs/video.md` exists, else `--as video` falls back to `page`. Line 120: `open video.mp4`.
  Line 140: `rungs/video.md` does not exist yet. Build procedure steps 3–6 say "write
  `index.html`", `verify.sh`, `snapshot.sh`, fix — a video writes `script.json` and derives
  `index.html`. The Contract (lines 15–22) parses only `--as`; no other flag exists.
- `scripts/verify.sh` dispatches on `<meta name="explain-rung">` (lines 275–279); an unknown
  rung exits 2 with "(expected sheet or page)"; its header says "four checks". The
  self-contained check flags only `http://`, `https://`, `//` (`REMOTE`, line 127), so a local
  `src="video.mp4"` passes. `cite_check.py`: `#provenance[data-root][data-kind]`; for kind
  `file`/`directory` every `<section>` needs a `<cite>`; visible text must hold `basename:line`
  (left boundary `(?<![\w.-])`); URL cites are skipped. `ste_lint.py --html` reads `p`, `li`,
  `dd`, `summary`, `figcaption`; it skips headings, `code`, `pre`, `cite`, `svg`, `nav` and any
  `data-ste="skip"` subtree; it errors on a sentence of 26+ words, contractions and non-STE
  words such as `verify` (probe by the adversarial reviewer).
- `.gitignore` ignores `out/`, `spike-video/`, `video-workspace/`, `node_modules/`.
- Spike measurements (Apple M5 Pro, 2026-10-02): Remotion `4.0.532` + React `19.2.3` run on
  Node `25.9.0` (odd, non-LTS line; nothing declares `engines`); `npm i` 55 s / 356 packages /
  503 MB incl. 193 MB Chrome Headless Shell under `node_modules/.remotion/` fetched by the
  first render (~25 s) — `npm ci` deletes it; render 12.4 s for 41 s of 1280x720@30 (ratio
  0.30 of the 2.0 limit); Kokoro via `uv run --python 3.12` (kokoro-onnx 0.6.1, onnxruntime
  1.30.0, soundfile 0.14.0, numpy 2.5.3, espeakng-loader 0.2.4) first clip 10.5 s, later clips
  1.6–1.9 s, uv resolve ~30 s once; `kokoro-v1.0.onnx` 325,505,369 B sha256
  `beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a`, `voices-v1.0.bin`
  28,214,398 B sha256 `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d`, from
  release `model-files-v1.1` of `thewh1teagle/kokoro-onnx`. Cue accuracy ~0.3 s, measured only
  for cues that begin a sentence. Speech starts 0.54–0.60 s after a scene start (lead 0.50 s).
  A still extracted warm costs ~0.3 s.
- Spike pitfalls: the bundled `ffprobe`/`ffmpeg` work only through the Remotion CLI; that FFmpeg
  lacks `select`, `tile`, `fps` (stills: one `-ss <t> -frames:v 1` each); `Audio` is deprecated
  → `Html5Audio`; `staticFile` serves `public/` only; Kokoro clip length varies by ~10 ms
  between runs; the spike's fade-in starts at opacity 0 and each cue animation starts from 0 at
  its cue frame (a still at the exact frame shows the state before the motion); edge labels
  and arrowheads needed `markerUnits="userSpaceOnUse"` and side-anchored labels; the spike's
  `tsconfig` `"lib": ["es2015"]` rejects `Object.entries`; `say` reads a text that starts with
  `-` as an option (use `say -f <file>`).
- Spike code to rewrite from (gitignored `spike-video/`): `script.json`, `narrate.py`,
  `build-timeline.mjs`, `verify_sync.py`, `make.sh`, `src/{Root,Explain,theme,types}.tsx`,
  `src/scenes/{BulletsAppear,DiagramWalk}.tsx`. Two of the five spec components exist.
- Tools: `node` 25.9.0, `npm` 11.12.1, `uv` 0.12.10, `afinfo`, `say`, `rsync`, `shasum`,
  Homebrew Python 3.12.14 for uv; system `python3` 3.14 (tests stdlib only). No `timeout(1)`.

## 3. Consumed and produced interfaces

Consumed (unchanged): `ste_lint.py [--html] FILE`; `cite_check.py <index.html>`; the provenance
recipe of `rungs/sheet.md` §4; `~/.claude/skills/explain` symlink (scripts resolve their own
directory through it); the Rung-selection and Conventions text of `SKILL.md`.

Environment: `EXPLAIN_VIDEO_WORKSPACE` (default `~/karpathy/video-workspace`), honoured by every
script below. Layout: `<ws>/app/` (synced sources + `node_modules` + `public/audio/`),
`<ws>/models/` (the two Kokoro files). Remotion is always run as `<ws>/app/node_modules/.bin/remotion`
with cwd `<ws>/app`; never `npx`.

### Script file `<output-dir>/script.json` — the author writes only this

```
{ "title": str, "subject": { "text": str, "kind": "file|directory|topic|conversation" },
  "provenance": { "root": str, "commit": str, "dirty": "dirty|no", "date": "YYYY-MM-DD",
                  "source": str, "not_covered": str },
  "scenes": [ { "id": str, "component": str, "props": object, "narration": str,
                "cites": [ { "path": str, "line": int?, "snippet": str } ] } ] }
```

- `narration`: STE-80 sentences; a code name may be written in backticks: the transcript
  renders it as `<code>` (not linted) and the narrator speaks it as plain text. The rung
  advises plain words ("the verify script") over identifiers.
- `cites`: `line` is required unless `path` starts with `http://` or `https://`. Visible text is
  derived by `transcript.py` (section below).
- Components, props, the motion in brackets, and the FAIL budgets (checked at the `script`
  stage, see §4):
  - `title` `{ title ≤ 50 chars, subtitle ≤ 80 chars, cue }` [the subtitle appears at the cue].
  - `bullets-appear` `{ title, bullets: [ { text ≤ 36 chars, cue } ] }`, 2–4 bullets [one bullet
    per cue, in order].
  - `diagram-with-highlight-walk` `{ title, nodes: [ { id, label ≤ 14, sub? ≤ 24, cell } ],
    edges: [ { from, to, label? ≤ 10 } ], walk: [ { node, cue } ] }`, 2–7 nodes; `cell` is one of
    `a1`–`c3` on a 3×3 grid (column a–c, row 1–3), unique per node; the component computes
    positions, so nodes never overlap [highlight and token walk the nodes in cue order].
  - `code-with-line-highlights` `{ title, source: { path, from, to }, highlights: [ { from, to,
    cue } ] }`: the lines are read from `<data-root>/<path>` at the `script` stage, never pasted;
    `to − from + 1 ≤ 14`; every line ≤ 72 columns with a tab counted as 4; each highlight range
    inside `[from, to]` [the highlight walks the ranges in cue order]. The transcript shows the
    lines in `<pre><code>` under `<figcaption>name:from</figcaption>` and cites `path:from`.
  - `before-after` `{ title, before: { heading ≤ 36, lines: [ ≤ 36 chars ] }, after: { heading,
    lines }, cue }`, each side ≤ 10 lines [wipe from before to after at the cue].
- Cue rule: a cue is the first words of a sentence of its scene's narration, matched at word
  boundaries, unique in that narration; a component's cues come in narration order; two cue
  frames are at least 15 frames apart. The frame of a cue is
  `leadFrames + round(offset / len(narration) × clipFrames)`, `offset` = where the cue starts.

### Scripts

- `node skills/explain/video/build-timeline.mjs --check <script.json> --root <data-root>` →
  validates the whole script (schema, components, budgets, cues, source lines) and exits 0, or
  prints one line per cause and exits 1. The single owner of validation.
- `node skills/explain/video/build-timeline.mjs <script.json> <durations.json> <engine> <out.json>`
  → `{ fps: 30, width: 1280, height: 720, totalFrames, engine, scenes: [ { id, component, props,
  from, durationInFrames, leadFrames, audioFrames, audio: "audio/<id>.<engine>.wav",
  cueFrames: { "<cue>": frame } } ] }`; `clipFrames = ceil(seconds × 30)`, `leadFrames = 15`,
  `tailFrames = 36`, `audioFrames = clipFrames`, `durationInFrames = 15 + clipFrames + 36`; for
  `code-with-line-highlights` the props carry the lines read at check time.
- `python3 skills/explain/video/transcript.py <script.json> <output-dir> [--narrator "<text>"]`
  → `index.html` from `templates/video.html` and `narration.md`. `index.html`: `<meta
  name="explain-rung" content="video">`, `<h1>` title, `<video controls src="video.mp4">`
  outside every section, one `<section id="<scene-id>">` per scene with `<h2>` scene title, the
  narration `<p>` (backtick spans as `<code>`), the on-screen text (bullets and before/after
  lines as `<ul><li>`, code as `<pre><code>` + `<figcaption>`, the title scene's subtitle as
  `<p>`; diagram labels in a `data-ste="skip"` list), then that scene's `<cite>` elements, and a
  `<footer id="provenance" data-root data-kind>` with the page rung's `<dl>` (Subject, Source,
  Commit, Dirty, Date) plus `Narrator` and `p.not-covered`. Visible cite text: `name:line
  "snippet"` where `name` is the basename, or the shortest path tail that is unique among the
  script's cited files; `untracked` appended when `git ls-files --error-unmatch` fails from
  `data-root` (only when `data-root` is a git repository); URL cites render `<host> "snippet"`.
  Every field HTML-escaped. `narration.md`: title, then `## <scene title>` and the narration
  per scene.
- `skills/explain/scripts/narrate.sh <script.json> <audio-dir> [--engine kokoro|say]` →
  `<audio-dir>/<id>.<engine>.wav` (16-bit PCM mono; Kokoro 24 kHz, `say` 22.05 kHz, checked with
  `afinfo`), a `<id>.<engine>.txt` sidecar holding engine, voice, speed and the narration text
  (a WAV is reused only when all four match), and `<audio-dir>/durations.json`
  `{ "engine": "<engine used>", "fallback": "<cause>"|null, "scenes": { "<id>": seconds } }`.
  Kokoro: `uv run --python 3.12 --with kokoro-onnx==0.6.1 --with onnxruntime==1.30.0 --with
  soundfile==0.14.0 --with numpy==2.5.3 --with espeakng-loader==0.2.4 python3 narrate.py`,
  models from `<ws>/models`, voice `af_heart`, speed 1.0, `lang en-us`, text passed through a
  file. Fallback (user decision): when the engine is `kokoro` and the models are missing, the
  uv run fails or a clip fails to synthesize, the script prints `narration: FALLBACK say
  (<cause>)`, synthesizes every scene with `say -f`, and exits 0 with `engine: "say"`.
- `skills/explain/scripts/video-workspace.sh [--engine kokoro|say]` → idempotent setup of
  `<ws>`: `rsync -a --delete --exclude /node_modules/ --exclude /public/` from
  `skills/explain/video/` to `<ws>/app/`; `npm ci` when `<ws>/app/node_modules/.explain-lock-sha`
  is missing or differs from the sha256 of `package-lock.json` (written after success);
  `remotion browser ensure` after each `npm ci`; for `kokoro`, download each missing model to
  `<name>.part`, verify sha256, `mv` (a mismatch deletes the file and fails with both digests).
  Before each costly step it prints one line with the step and its expected cost.
- `skills/explain/scripts/render.sh <output-dir> [--engine kokoro|say]` → nine stage lines, in
  order, each `<stage>: ok …` or `<stage>: FAIL <cause>` (stop at the first FAIL, exit 1):
  1. `script` — `build-timeline.mjs --check`, `transcript.py` (no narrator yet), `verify.sh
     index.html` (self-contained, citations, prose) — nothing is synthesized before this passes;
  2. `workspace` — `video-workspace.sh`; 3. `narration (<engine>)` — `narrate.sh` (a FALLBACK
  line is printed before `ok`); 4. `timeline (<n> scenes, <s> s)`; 5. `render (<s> s, <ratio>
  render-min/video-min)` — clears and fills `<ws>/app/public/audio/`, renders composition
  `Explain` with `--props build/timeline.json` to `video.mp4`, log in `build/render.log`;
  6. `container`; 7. `sync`; 8. `stills (<n>)` — stages 6–8 are `video/check_render.sh`;
  9. `transcript` — `transcript.py --narrator "<engine>[ (fallback: <cause>)]"` and `verify.sh`
  again. Exit 2: usage, no `script.json`, invalid JSON.
- `skills/explain/video/check_render.sh <video.mp4> <timeline.json> <review-dir>` → prints the
  `container`, `sync`, `stills` lines: exactly one h264 video and one AAC audio stream and
  `|duration − totalFrames/30| ≤ 0.2 s` (`remotion ffprobe`); audio extracted with `remotion
  ffmpeg -vn -ac 1 -ar 16000` to `build/rendered-audio.wav` and checked by
  `python3 video/verify_sync.py <wav> <timeline.json>` under the same uv env (speech in each
  scene starts within 0.25 s of `leadFrames` and ends before the scene ends); `<review-dir>`
  emptied, then one still per scene at `from + leadFrames` and one per cue at `cueFrame + 15`
  (clamped to the scene), seek `(frame + 0.5)/30`, named `still-NN-<scene-id>[-<k>].png`.
- `verify.sh` with `rung=video`: prints `self-contained`, `citations`, `prose`; exit codes as
  today; the "(expected …)" message and the header name the three rungs.
- `skills/explain/templates/video-script.json`: a five-scene example (one scene per component)
  that passes `--check` against the skill directory as root; the fixture base for tests and
  the file the rung tells the author to copy.
- `skills/explain/rungs/video.md` (≤ 200 lines, STE-80, lint 0 errors); `SKILL.md` touch:
  three lines (line 140; Build procedure "For a video, the rung file replaces steps 3 to 6";
  one cut elsewhere) at ≤ 140 lines.

## 4. Invariants and named failure behavior

- One source of truth: narration, on-screen text, cues, cites and provenance live in
  `script.json`; the mp4, `index.html`, `narration.md` and the stills are derived from it by
  `render.sh`. Nothing is hand-edited after the render.
- Grounding before cost: stage 1 runs the full validation, the transcript and `verify.sh`
  before any synthesis or render; a cite or prose error costs seconds, not a render.
- Sync is computed, never eyeballed: frame counts come from `afinfo` of the real WAV plus the
  constants; cues map by character offset (accuracy ~0.3 s under the cue rule).
- Narrator: Kokoro `af_heart` by default; `say` on `--engine say` (the rung tells Claude to
  pass it when the user asks in words) or as the automatic fallback above, always labelled in
  the `narration` line and in the transcript's `Narrator` row. Another language than English:
  the rung says to stop and say that the video rung is English only.
- First run: `render.sh` runs the setup by itself (user decision); the costs are printed before
  each step (npm ci ~55 s, Chrome Headless Shell 193 MB, models 353 MB, uv resolve ~30 s).
- Secrets: convention 2's password/token/key rule applies to narration, on-screen text and the
  code range of `code-with-line-highlights`.
- Versions: `video/package.json` + `package-lock.json` pin Remotion `4.0.532`, React `19.2.3`;
  `narrate.sh` pins the five Python packages above. Node: the pinned stack ran on 25.9.0; the
  rung says which Node was proven and that an LTS is the safe substitute.
- Licence: Remotion Free License for an individual (spike); the rung names when to re-check (a
  for-profit organisation with more than 3 employees).
- Named failures, each one `FAIL` line with its cause (stage in brackets): unknown component;
  missing or extra prop; a budget above (scenes outside 3–8, narration > 45 words, title,
  subtitle, bullet, label, sub, edge label, before/after line or heading over its limit, bullets
  outside 2–4, nodes outside 2–7, unknown or duplicate `cell`, walk/edge node id unknown, code
  range outside the file, > 14 lines, a line > 72 columns, highlight range outside the code
  range); cue not found, not at a sentence start, not unique, out of order, or closer than 15
  frames to the previous cue; duplicate scene id; empty narration; a scene without `cites` when
  `subject.kind` is `file` or `directory`; a cite whose `line` is missing on a non-URL path;
  source file unreadable [all `script`]; a transcript that fails `verify.sh` (the lint's 26-word
  sentence, contraction or non-STE word; a cite whose snippet is not on its line) [`script`,
  `transcript`]; rsync, `npm ci`, browser download or model download failure, checksum mismatch
  [`workspace`, with the log path]; `say` or `afinfo` missing, a WAV with an unexpected sample
  rate, Kokoro failure with `--engine kokoro` after the fallback also failed [`narration`];
  a scene longer than 60 s or a total above 150 s [`timeline`]; render failure (last 40 log
  lines) [`render`]; wrong stream set or duration off by more than 0.2 s [`container`]; speech
  outside its window [`sync`]; a still that cannot be extracted [`stills`]. Advisory, printed
  only: the render ratio against 2.0.

## 5. Rollback and recovery

Every file is new except one `verify.sh` branch, three `SKILL.md` lines, two one-line palette
notes (`rungs/sheet.md` §7, `rungs/page.md` §8) and one spec amendment (§5.3 item 5: the video
output contents). Deleting `rungs/video.md` and restoring `SKILL.md` line 140 brings back the
page fallback. `<ws>` and `out/` are gitignored and disposable: `rm -rf` and the next
`render.sh` rebuilds them. No global installs; npm and uv caches only.

## 6. Acceptance evidence and run commands

- `cd skills/explain && python3 -B -m unittest discover -s tests` → `OK` (91 + new; the tests
  that need the workspace, npm or Chrome are skipped unless `EXPLAIN_VIDEO_E2E=1`, and then run
  one render per test class with a 900 s subprocess timeout).
- `EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render tests.test_check_render` → `OK`.
- `python3 ~/.claude/skills/ste/scripts/ste_lint.py skills/explain/rungs/video.md` and
  `skills/explain/SKILL.md` → 0 errors; `wc -l` ≤ 200 / ≤ 140.
- `node skills/explain/video/build-timeline.mjs --check skills/explain/templates/video-script.json
  --root skills/explain` → exit 0.
- Live run (task 7): rung line `Rung: video (forced) — --as video … — subject: … (file)`;
  `render.sh` nine `ok` lines with `narration (kokoro)` and the ratio; `verify.sh index.html`
  exit 0; stills read with the Read tool; three transcript claims verbatim at `path:line`;
  `afinfo video.mp4` duration equals the timeline's.
- User run (task 8): the same, by the user, on a subject of their choice; `open video.mp4` plays.

## 7. Ordered tasks and ownership

One implementer at a time. Tasks 1–3 touch disjoint files and share only the script schema
above and `templates/video-script.json` (owned by task 1; task 4 may change its `props`
values to fix rendering and says so in its report). Each test names the mutation that makes
it red.

1. **Script contract + validator** — owns `video/build-timeline.mjs`,
   `templates/video-script.json`, `tests/test_video_timeline.py`. Tests (subprocess `node`):
   `test_template_script_passes_check` (red: a budget off by one in the template);
   `test_two_scene_fixture_frames_add_up` (literal total from fixture durations 3.0 s and 4.5 s:
   (15+90+36)+(15+135+36) = 327; red: tail constant changed); `test_cue_frame_is_proportional`
   (cue at offset 0 → 15; a cue starting at character 60 of 120 in a 90-frame clip → 60; red:
   offset measured from the cue end); `test_unknown_component_fails`; `test_cue_not_at_sentence_start_fails`;
   `test_cue_not_unique_fails`; `test_cues_out_of_order_fail`; `test_duplicate_scene_id_fails`;
   `test_code_line_over_72_columns_fails` (a tab counts 4); `test_code_range_outside_file_fails`;
   `test_file_kind_scene_without_cites_fails`; `test_bullet_over_36_chars_fails`;
   `test_duplicate_cell_fails` — each asserting the exact FAIL line.
2. **Transcript + `verify.sh` branch** — owns `templates/video.html`, `video/transcript.py`, the
   `rung=video` case and messages in `scripts/verify.sh`, `tests/test_transcript.py`, additions
   to `tests/test_verify.py`. Tests: `test_one_section_per_scene_with_its_cites` (section ids
   equal the scene ids and each holds exactly its scene's cites; red: cites emitted in one
   block); `test_backtick_span_becomes_code` (red: escaped literally);
   `test_duplicate_basename_shows_shortest_unique_tail`; `test_untracked_file_is_marked`
   (a temp git repo with one untracked file; red: `git ls-files` not run);
   `test_url_cite_without_line`; `test_narration_md_lists_every_scene`;
   `test_html_escaped_in_every_field`; `test_narrator_row_from_flag`;
   `test_verify_video_rung_prints_three_lines` (red today: exit 2 unknown rung);
   `test_verify_video_remote_video_src_fails` (`src="https://…"` → `self-contained: FAIL`);
   `test_cite_check_passes_on_generated_transcript` (a real file in a temp root; red: the
   `<video>` element inside a section).
3. **Narration** — owns `video/narrate.py`, `scripts/narrate.sh`, `tests/test_narrate.py`.
   Tests use `say` and a temp `EXPLAIN_VIDEO_WORKSPACE` (no network, no models):
   `test_say_engine_writes_wav_sidecar_and_durations` (sample rate 22050 read back with
   `afinfo`); `test_unchanged_narration_reuses_wav` (inode and mtime unchanged; red: sidecar
   ignored); `test_changed_text_resynthesizes`; `test_engine_in_filename_keeps_both_voices`
   (`<id>.say.wav` and a fake `<id>.kokoro.wav` coexist; red: one file per id);
   `test_missing_models_falls_back_to_say_with_cause` (`--engine kokoro`, empty models dir →
   `FALLBACK say (models missing …)`, exit 0, `engine: "say"`; red: exit 1);
   `test_narration_starting_with_dash_is_spoken` (`say -f`); `test_empty_narration_fails`;
   `test_usage_error_exit_2`. Kokoro itself is proven by task 7.
4. **Remotion app + workspace** — owns `video/{package.json, package-lock.json,
   remotion.config.ts, tsconfig.json, src/**}`, `scripts/video-workspace.sh`,
   `tests/test_video_workspace.py`. Five scene components per §3 (grid placement, fixed-size
   markers, side-anchored labels, token clears labels, `Html5Audio`, `calculateMetadata` from
   the timeline props, theme = the sheet/page palette values). Evidence: `tsc --noEmit` exit 0 in
   `<ws>/app`; a render of `templates/video-script.json` with silent WAVs (a stdlib `wave`
   helper) in ≤ 2 iterations (an iteration = a render after a scene-code change; a third is
   reported as DONE_WITH_CONCERNS for the controller to rule); stills read per component.
   Tests (fake `npm`, `curl` and `remotion` on `PATH` recording their calls, temp workspace):
   `test_sync_excludes_node_modules_and_public_and_deletes_stale` (red: no `--delete`);
   `test_npm_ci_runs_when_stamp_missing_then_not_again` (red: trigger on lock change only);
   `test_browser_ensure_after_npm_ci`; `test_checksum_mismatch_deletes_part_and_fails` (red:
   file kept); `test_say_engine_skips_models`; `test_costs_printed_before_each_step`.
5. **`render.sh` + `check_render.sh`** — owns `scripts/render.sh`, `video/check_render.sh`,
   `video/verify_sync.py`, `tests/test_render.py`, `tests/test_check_render.py`; consumes
   tasks 1–4. Tests: `test_missing_script_json_exit_2`; `test_bad_cue_fails_at_script_stage`
   (exactly zero later stage lines; red: narration before validation);
   `test_prose_error_fails_at_script_stage` (a contraction in the narration); E2E (gated,
   `--engine say`, two-scene fixture rendered once per class):
   `test_say_fixture_prints_nine_ok_lines_and_ratio`; `test_transcript_narrator_row_says_say`;
   `check_render` on that mp4: `test_duration_mismatch_is_container_fail` (timeline with
   `totalFrames + 30`); `test_shifted_speech_is_sync_fail` (a WAV with 1 s of leading silence
   spliced in; red: tolerance 2 s); `test_stills_named_per_scene_and_cue_and_review_cleared`
   (a stale file in `review/` disappears); `test_still_at_cue_plus_15_shows_motion` (the bullet
   still has non-background pixels in the bullet area — compared against the still at the cue
   frame, read with the Read tool as evidence, asserted by pixel difference).
6. **`rungs/video.md` + `SKILL.md` + notes + spec amendment** — owns `rungs/video.md`,
   `SKILL.md` (three lines), the palette notes in `rungs/sheet.md` §7 and `rungs/page.md` §8
   ("four places"), spec §5.3 item 5 (video contents: `script.json`, `index.html`, `video.mp4`,
   `narration.md`, `review/still-NN-….png`; dated amendment). The rung file carries: when a
   video (spec §5.2; the forced case; English only); writing the script (copy
   `templates/video-script.json`; scene budget 3–8 and ≤ 45 words; one motion per scene; the
   component table with props and limits; the cue rule with a worked example; narration in
   STE with ≤ 20-word sentences as the target and backticks for a code name; cites per scene;
   provenance by reference to `rungs/sheet.md` §4 and the `Narrator` row); the build
   (`render.sh`, the nine stage lines, first-run costs, the fallback line, `--engine say` on the
   user's request, reading the stills with the Read tool, `verify.sh index.html`); the handoff;
   the output-directory contents; pinned versions, Node policy, model URLs and checksums,
   timing constants and cue accuracy; the licence note.
7. **Claude-side live run + fold-back** — a fresh subagent runs `/explain <file> --as video` on
   a file subject with a flow (proposed:
   `~/work/inavcalculator/src/main/java/ru/aton/esb/microservices/inavcalculator/web/ImportController.java`,
   so every section must cite); the controller pre-declares the scene count and components;
   evidence note `docs/superpowers/spikes/2026-10-03-explain-video-live-run.md`; defects go to
   one fold-back dispatch.
8. **User acceptance** — the user runs `/explain <own subject> --as video`; "ok" closes the wave.
