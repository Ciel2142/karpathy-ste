# Explain brainrot, wave `scenebox` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every scene component lays out in a box given by the composition (`SceneBox`, `useBox()`), and the explainer video renders the same pixels as before the refactor.

**Architecture:** A new `src/sceneBox.tsx` owns the box contract (type, landscape value, React context, `useBox()`, `contentRect()`). `layout.tsx`, the five scenes and `diagramGeometry.ts` read the box instead of the module constants `FRAME`, `CONTENT`, `MARGIN`, `BOX` and hard-coded font sizes. `Explain.tsx` provides `LANDSCAPE_BOX`. A gated regression renders the full template and compares its stills with stills rendered from `main` before the first edit.

**Tech Stack:** Remotion 4.0.532, React 19.2.3, TypeScript 5.9.3 (`tsc` in the workspace), Python 3 stdlib `unittest`, bash.

**Spec:** `docs/superpowers/specs/2026-10-04-explain-brainrot-design.md` (§4.2, §7.4). Wave map: `docs/superpowers/waves/2026-10-04-explain-brainrot.yaml`, wave `scenebox`.

## Global Constraints

- Pinned versions do not change: Remotion `4.0.532`, React `19.2.3`, TypeScript `5.9.3` (`video/package.json`, `package-lock.json`).
- Never install a package globally; never use `npx`. Node tools run from `<ws>/app/node_modules/.bin/`.
- Workspace: `${EXPLAIN_VIDEO_WORKSPACE:-$HOME/karpathy/video-workspace}` (`<ws>`). It is gitignored.
- Explainer constants: 30 fps at 1280x720; lead 15 frames, tail 36 frames.
- Python tests use the stdlib only (no PIL; `python3 -c 'import PIL'` fails on this machine).
- Renders run only under `EXPLAIN_VIDEO_E2E=1`.
- Regression threshold (spec §7.4): at most 0.5 % of the pixels of each still differ by more than 16 levels in any channel. For 1280x720 that is at most 4608 pixels.
- No visual change: `LANDSCAPE_BOX` holds exactly today's numbers.
- `BeforeAfter` stacking is NOT in this wave (wave `brainrot-render` owns it). Here `BeforeAfter` only reads its box.
- Commit identity: `git -c user.name=Vladislav -c user.email=valukin@Vladislavs-MacBook-Pro.local commit`, message ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. A scene rendered without a `SceneBoxProvider` above it (wave `brainrot-render` forgets the provider in `Short`): `useBox()` throws a named error, so the render fails loudly instead of drawing silently at landscape size. Pinned by Task 2 Step 5.
2. The baseline is taken from a tree that already has the refactor (a re-capture after the merge), so the regression compares the new code with itself and passes trivially: the capture script refuses to overwrite an existing baseline without `--force`, and records the base commit. Pinned by Task 1 Step 1.
3. The baseline render and the new render get different audio lengths (another wave changes narration, or `say` output varies), so cue frames move and stills differ for a reason that is not layout: the test reuses the baseline's `audio/` and first asserts that the pixel-relevant timeline fields are equal, with a message that names timeline drift. Pinned by Task 1 Step 1.
4. The new render produces fewer or other stills (a scene or cue missing): the test compares the sorted still names before it compares pixels, so a missing still fails instead of being skipped. Pinned by Task 1 Step 1.
5. A bad `<ref>` or a failed render during capture leaves a registered git worktree or a half-written baseline: the script removes its worktree on every exit path and writes `BASE` last, and the test treats a baseline without `BASE` as missing. Pinned by Task 1 Step 1.

---

### Task 1: Landscape regression harness and the baseline from `main`

Harness first, before any scene edit, so the baseline is the pre-refactor rendering.

**Files:**
- Create: `skills/explain/tests/png_diff.py` (moved out of `test_check_render.py`)
- Modify: `skills/explain/tests/test_check_render.py` (import `read_png`, `differing_pixels` from `png_diff`; its own assertions unchanged)
- Create: `skills/explain/tests/capture_landscape_baseline.sh`
- Create: `skills/explain/tests/test_landscape_regression.py`
- Modify: `README.md` (Tests section: the two commands of Step 6)

**Interfaces:**
- Consumes: `scripts/render.sh <output-dir> --engine say` (unchanged); `video/check_render.sh` still names (`still-NN-<id>.png`, `still-NN-<id>-<k>.png`).
- Produces:

```python
# tests/png_diff.py
def read_png(path, rows) -> tuple[int, int, list[bytearray]]   # moved verbatim from test_check_render.py
def differing_pixels(png_a, png_b, x0, x1, y0, y1, level=40) -> int  # pixels whose RGB differs by more than `level` in some channel
```

```sh
# tests/capture_landscape_baseline.sh <ref> [--force]
#   writes <ws>/regression/landscape-baseline/: script.json, audio/, build/timeline.json, review/*.png, BASE
#   exit 0 ok; exit 1 render failed; exit 2 usage, unknown ref, or baseline exists without --force
```

Behaviour of the capture script:
- Resolves `<ref>` with `git rev-parse --verify <ref>^{commit}`; an unknown ref exits 2 and adds no worktree.
- Refuses an existing `<ws>/regression/landscape-baseline/BASE` unless `--force` (exit 2, message names `--force`). With `--force`, it empties the directory first.
- Runs `git worktree add --detach <tmp> <hash>`, and registers a `trap` on EXIT that runs `git worktree remove --force <tmp>`.
- Writes `script.json`: the full `templates/video-script.json` of the CURRENT checkout (all five components), with `provenance.root` set to this checkout's absolute `skills/explain` path.
- Runs `<tmp>/skills/explain/scripts/render.sh <baseline-dir> --engine say`. The worktree's `video-workspace.sh` rsyncs the worktree's `video/` into `<ws>/app`, so the base commit's sources render. A non-zero exit gives exit 1 and no `BASE`.
- Writes `BASE` (the resolved hash) last.

Behaviour of `test_landscape_regression.py` (class skipped unless `EXPLAIN_VIDEO_E2E=1`):
- A baseline without `BASE` fails with a message that names `tests/capture_landscape_baseline.sh main`.
- Copies the baseline `script.json` (with `provenance.root` rewritten to this checkout's `skills/explain`) and `audio/` into a temp output dir, then runs this checkout's `render.sh <tmp> --engine say` and asserts exit 0. On a non-zero exit, the temp dir is kept and the failure message holds the `render.sh` stdout and the temp dir path. On success, the temp dir is removed.
- Asserts timeline equality on the pixel-relevant fields only: `fps`, `width`, `height`, `totalFrames`, and per scene `id`, `component`, `props`, `from`, `durationInFrames`, `leadFrames`, `audioFrames`, `cueFrames`. Other keys that parallel waves add (for example `format`) are ignored.
- Asserts that the sorted still names are equal.
- For each still, counts `differing_pixels(base, new, 0, 1280, 0, 720, level=16)`. The test fails when any count is more than 4608, and the message lists every failing still with its count.

- [ ] **Step 1: Write the tests.**
  - `test_png_diff_level`: two 4x1 PNG fixtures written in the test, differing by 20 in one channel of one pixel. Assertion: `differing_pixels(..., level=16) == 1` and `differing_pixels(..., level=40) == 0`.
  - `test_capture_unknown_ref_exits_2`: assert exit code 2, and that `git worktree list` is unchanged.
  - `test_capture_refuses_existing_baseline`: with `EXPLAIN_VIDEO_WORKSPACE` set to a temp dir that holds a `BASE`, assert exit code 2 and that the message contains `--force`.
  - `test_missing_base_fails_with_capture_hint` (E2E class): assert the failure message contains `capture_landscape_baseline.sh main`.
  - `test_full_template_matches_baseline` (E2E class): assert equal timeline fields, equal still names, and every still at or under 4608 differing pixels.
  - The two capture tests need no workspace and always run.

- [ ] **Step 2: Run the always-on tests and see them fail.**
  Run: `cd skills/explain && python3 -B -m unittest tests.test_landscape_regression -v`
  Expected: errors on the missing `png_diff` module and the missing capture script.

- [ ] **Step 3: Implement `png_diff.py`, the capture script and the test helpers, and re-point `test_check_render.py`.**

- [ ] **Step 4: Run the full unit suite.**
  Run: `cd skills/explain && python3 -B -m unittest discover -s tests`
  Expected: `OK` (E2E classes skipped).

- [ ] **Step 5: Capture the baseline from `main`.** `main` is pre-refactor, and this step must run before Task 2.
  Run: `skills/explain/tests/capture_landscape_baseline.sh main`
  Expected: exit 0, and `<ws>/regression/landscape-baseline/BASE` holds the hash of `git rev-parse main`.

- [ ] **Step 6: Run the regression against the unchanged tree.** This proves the noise floor is under the threshold.
  Run: `cd skills/explain && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_landscape_regression -v`
  Expected: `OK`.

- [ ] **Step 7: Mutation check.** Change the bullet `fontSize` in `src/scenes/BulletsAppear.tsx` from 32 to 36, then re-run the Step 6 command.
  Expected: FAIL, naming at least one `bullets` still with a count over 4608.
  Then revert the change, so that `git diff --stat skills/explain/video` is empty.

- [ ] **Step 8: Commit.**

```bash
git add skills/explain/tests/png_diff.py skills/explain/tests/test_check_render.py skills/explain/tests/capture_landscape_baseline.sh skills/explain/tests/test_landscape_regression.py README.md
git -c user.name=Vladislav -c user.email=valukin@Vladislavs-MacBook-Pro.local commit -m "test: explain: landscape still regression against a baseline from a git ref"
```

### Task 2: `SceneBox` contract, layout, and the non-diagram scenes

**Files:**
- Create: `skills/explain/video/src/sceneBox.tsx`
- Modify: `skills/explain/video/src/layout.tsx` (drop the `FRAME` and `MARGIN` exports; `SceneTitle` and `Content` read `useBox()`; keep a module-local `CONTENT` export computed as `contentRect(LANDSCAPE_BOX)` ONLY until Task 3 removes it)
- Modify: `skills/explain/video/src/Explain.tsx` (wrap the `Series` in `<SceneBoxProvider box={LANDSCAPE_BOX}>`)
- Modify: `skills/explain/video/src/scenes/Title.tsx`, `BulletsAppear.tsx`, `CodeHighlights.tsx`, `BeforeAfter.tsx`

**Interfaces:**
- Consumes: nothing new.
- Produces (wave `brainrot-render` consumes this block verbatim):

```ts
// src/sceneBox.tsx
export type Size = { width: number; height: number };
export type SceneType = {
  heroTitle: number;    // 64   Title scene: title font px
  heroSubtitle: number; // 36   Title scene: subtitle font px
  bullet: number;       // 32   BulletsAppear text font px
  code: number;         // 24   CodeHighlights mono font px
  codeLine: number;     // 36   CodeHighlights line height px
  node: Size;           // 260 x 96   DiagramWalk node box
  nodeLabel: number;    // 28
  nodeSub: number;      // 20
  edgeLabel: number;    // 22
  panelHeading: number; // 32   BeforeAfter heading font px
  panelLine: number;    // 26   BeforeAfter line font px
};
export type SceneBox = Size & {
  margin: number;       // 48   outer margin of the panel
  titleSize: number;    // 44   SceneTitle font px
  titleBand: number;    // 60   panel top margin -> top of the 2 px rule under the title
  type: SceneType;
};
export const LANDSCAPE_BOX: SceneBox; // width 1280, height 720, and the values in the comments above
export function SceneBoxProvider(props: { box: SceneBox; children: ReactNode }): ReactElement;
export function useBox(): SceneBox;   // throws Error("useBox: no SceneBoxProvider above this scene")
export function contentRect(box: SceneBox): { left: number; top: number; width: number; height: number };
// top = margin + titleBand + 30; left = margin; width = width - 2 * margin; height = height - margin - top
// contentRect(LANDSCAPE_BOX) = { left: 48, top: 138, width: 1184, height: 534 }
```

- Placement contract: a scene draws inside its nearest positioned ancestor, which is `box.width` x `box.height`. `Title`'s `AbsoluteFill`, `SceneTitle` and `Content` are all absolute within it. In landscape that ancestor is the composition frame. In `Short`, the consumer places a positioned container of the panel size.

Mapping of today's literals to box fields:
- `Title`: 64 → `heroTitle`, 36 → `heroSubtitle`, `MARGIN` → `margin`.
- `BulletsAppear`: 32 → `bullet`.
- `CodeHighlights`: `FONT_SIZE` → `code`, `LINE_HEIGHT` → `codeLine`.
- `BeforeAfter`: 32 → `panelHeading`, 26 → `panelLine`; `COLUMN` is computed from `contentRect(box).width`.
- `SceneTitle`: 44 → `titleSize`; the rule top is `margin + titleBand`.
- Every other spacing constant stays a module constant.

- [ ] **Step 1: Write `sceneBox.tsx`, then migrate `layout.tsx`, `Explain.tsx` and the four scenes.** Signatures are as above; there is no TS unit runner, so the proof is the typecheck plus the pixel regression.
- [ ] **Step 2: Typecheck.**
  Run: `skills/explain/scripts/video-workspace.sh --engine say && (cd "${EXPLAIN_VIDEO_WORKSPACE:-$HOME/karpathy/video-workspace}/app" && ./node_modules/.bin/tsc -p .)`
  Expected: no output from `tsc`, exit 0.
- [ ] **Step 3: Pixel regression.**
  Run: `cd skills/explain && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_landscape_regression -v`
  Expected: `OK`.
- [ ] **Step 4: Unit suite.**
  Run: `cd skills/explain && python3 -B -m unittest discover -s tests`
  Expected: `OK`.
- [ ] **Step 5: Guard check (Review Focus 1).** Remove the `SceneBoxProvider` from `Explain.tsx`, then run the Step 3 command.
  Expected: the render fails, and `build/render.log` of the temp run (path printed in the failure) contains `useBox: no SceneBoxProvider above this scene`.
  Then restore the provider and re-run Step 3: `OK`.
- [ ] **Step 6: Commit.**

```bash
git add skills/explain/video/src/sceneBox.tsx skills/explain/video/src/layout.tsx skills/explain/video/src/Explain.tsx skills/explain/video/src/scenes/Title.tsx skills/explain/video/src/scenes/BulletsAppear.tsx skills/explain/video/src/scenes/CodeHighlights.tsx skills/explain/video/src/scenes/BeforeAfter.tsx
git -c user.name=Vladislav -c user.email=valukin@Vladislavs-MacBook-Pro.local commit -m "refactor: explain: scenes lay out in a SceneBox given by the composition"
```

### Task 3: Diagram geometry takes the box; the fixed layout constants go away

**Files:**
- Modify: `skills/explain/video/src/scenes/diagramGeometry.ts` (no import of `../layout`; `BOX` removed)
- Modify: `skills/explain/video/src/scenes/DiagramWalk.tsx` (svg size from `contentRect(box)`, node box from `box.type.node`, 28/20/22 font sizes from `nodeLabel`/`nodeSub`/`edgeLabel`)
- Modify: `skills/explain/video/src/layout.tsx` (remove the temporary `CONTENT` export)

**Interfaces:**
- Consumes: `Size`, `SceneBox`, `useBox()`, `contentRect()` from Task 2.
- Produces:

```ts
// src/scenes/diagramGeometry.ts
export const cellCentre: (cell: Cell, content: Size) => Point;
export const segment: (a: Point, b: Point, node: Size) => [Point, Point];
// unchanged: Point, LabelPlace, along(), labelPlace(); the grid fractions 1/6, 1/2, 5/6 and EDGE_GAP 6, LABEL_OFFSET 14 stay module constants
```

- [ ] **Step 1: Change the two geometry signatures and migrate `DiagramWalk.tsx`. Remove `CONTENT` from `layout.tsx`.**
- [ ] **Step 2: Check that no fixed box constant is left.**
  Run: `grep -rnE '\b(FRAME|CONTENT|MARGIN|BOX)\b' skills/explain/video/src`
  Expected: no output (exit 1).
- [ ] **Step 3: Typecheck.** Run the Task 2 Step 2 command. Expected: exit 0, no output.
- [ ] **Step 4: Pixel regression.** Run the Task 2 Step 3 command. Expected: `OK`, including the diagram scene's stills.
- [ ] **Step 5: Full suites, then the existing explainer E2E.**
  Run: `cd skills/explain && python3 -B -m unittest discover -s tests && EXPLAIN_VIDEO_E2E=1 python3 -B -m unittest tests.test_render tests.test_check_render`
  Expected: `OK` twice.
- [ ] **Step 6: Commit.**

```bash
git add skills/explain/video/src/scenes/diagramGeometry.ts skills/explain/video/src/scenes/DiagramWalk.tsx skills/explain/video/src/layout.tsx
git -c user.name=Vladislav -c user.email=valukin@Vladislavs-MacBook-Pro.local commit -m "refactor: explain: diagram geometry takes the scene box"
```

## Wave close

Done when (map): the unit suites pass, and the gated landscape regression renders the full template within the threshold. Evidence for the br close reasons: the commit SHAs of Tasks 1–3, the `OK` lines of Task 3 Steps 4–5, and the `BASE` hash of the baseline.
