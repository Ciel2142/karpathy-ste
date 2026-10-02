# explain-skills — inline outlines for the ready low-risk waves

Status: presented 2026-10-02, **awaiting the user's go and choice of execution mode**
(subagent-driven vs inline). Nothing filed in br, nothing implemented yet.
Map: `2026-10-02-explain-skills.yaml`. Spec: `../specs/2026-10-02-explain-skills-design.md`.

Order on go: create `feature/explain-skills` from `main` → `br init` if needed →
one `-t epic` br issue per wave (`wave-ste`, `wave-video-spike`) → one task issue per
item below with `--external-ref <this file>#<wave>-task-<n>`, `--labels wave-<n>`,
`--parent <epic>` → execute. Plan amendment applies: contracts, not code.

## Wave `ste` (8 tasks)

Outcome: the STE-80 profile is a user-only skill reachable by path, the lint errors
only on deterministic rules, and a live run proves zero errors.

1. Branch + scaffold: `feature/explain-skills`; `skills/ste/{SKILL.md,scripts/,tests/fixtures/}`;
   symlink `~/.claude/skills/ste -> ~/karpathy/skills/ste`.
2. Profile `SKILL.md`: frontmatter `name`, `description`, `disable-model-invocation: true`,
   `argument-hint: "[text or request]"`; the `/ste` contract (spec §4.1); kept rules with
   Issue 9 rule numbers; relaxed list; ~25-entry substitution table verified against the
   extracted Issue 9 text (`/tmp/ste9.txt`; re-extract per spec §4.2 if gone) with page
   labels; PDF URL + sha256 + extraction command; usage protocol (spec §4.4).
3. Lint text model (TDD): `tokenize(text: str) -> list[Block]`;
   `Block(kind: 'para'|'ol-item'|'ul-item', sentences: list[Sentence])`;
   `Sentence(text: str, line: int, col: int, words: int)`. Tests: sentence boundaries
   incl. `)` `"` `*` `_` after a terminator; list-item boundaries; parenthetical, quoted,
   number+unit and code-span tokens; skipped frontmatter/fences/headings/tables/URLs.
4. Rules + CLI (TDD): `lint(blocks: list[Block]) -> list[Finding]`;
   `Finding(line: int, col: int, severity: 'E'|'W', rule: str, message: str)`;
   `main(argv: list[str]) -> int`. Tests assert per rule code (spec §4.3.3); the
   must-not-error set (spec §4.5); exit codes 0/1/2; output line format and summary line.
5. `--html` mode (TDD): `html_to_blocks(html: str) -> list[Block]`; fixture with a 12-link
   `nav`, implicit `</li>`, a `data-ste="skip"` subtree, `ol` items in the 21–25 band,
   `<cite>` skipping (spec §4.3.2).
6. Fixtures + broken-state pass: `tests/fixtures/clean.md` (Issue 9 examples cited by
   rule), `tests/fixtures/artifact.html`; every assertion shown to fail with its rule
   disabled before it counts.
7. Live run: a subagent reads `~/.claude/skills/ste/SKILL.md` by path and explains a real
   subject; lint → zero errors; baseline without the profile; both counts into
   `docs/superpowers/spikes/2026-10-02-ste-live-run.md`.
8. User acceptance: the user runs `/ste` bare and with text (cannot be done by Claude with
   `disable-model-invocation: true`).

Evidence: `cd skills/ste && python3 -m unittest discover -s tests` → `OK`; lint exit 0 on
both fixtures; the live-run note.

## Wave `video-spike` (4 tasks, timeboxed to one session)

1. Scaffold `spike-video/` with `npx create-video@latest` (blank TS); render the default
   composition; record whether Node 25 works, else `brew install node@22` (keg-only) and
   record it.
2. Narration: `say` → 3 WAVs + `afinfo` durations JSON; Kokoro via
   `uv run --python 3.12 --with kokoro-onnx` with model + voices under
   `spike-video/models/`. Claude cannot judge voice quality — both WAVs go in the findings
   for the user to compare.
3. Pipeline: `script.json` contract (scene id, component, props, narration text, audio
   path); only the scene components the three scenes need; `durationInFrames` computed
   from the durations JSON; one command `make.sh` → `out/video.mp4`.
4. Measure + findings: wall time per video-minute, `du -sh` of deps and models, iteration
   count, Remotion license tier confirmed; `docs/superpowers/spikes/2026-10-02-video-pipeline.md`
   with pass / fail / inconclusive against spec §8.3.

Runs concurrently with wave `ste` (disjoint files, same base).

## Later waves

`explain-sheet` and `explain-page` get their outlines when their dependencies close
(map `depends_on`). The `video` rung stays deferred until the spike note and the user's
decision exist.
