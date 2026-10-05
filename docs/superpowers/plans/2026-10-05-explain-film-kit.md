# Explain film — wave `film-kit` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The kit that a film scene is written against exists under `skills/explain/video/src/kit/`: palette, motion, marks, mono and sans text, strokes, the code card with `colX` and `lineY`, and the `Source` that only the pipeline can make.

**Architecture:** Everything that computes a number or a string lives in modules with no runtime import (`palette.ts`, `motion.ts`, `marks.ts`, `source.ts`, `mono.ts`), so Node runs them in tests with the types stripped. The three `.tsx` files only draw what those modules computed. `index.ts` is the one import surface of a scene; the makers that the pipeline needs (`makeAt`, `sourceFromDisk`) are exported from their own files only.

**Tech Stack:** TypeScript 5.9 and React 19 as pinned in `video/package.json`; Python 3 `unittest`; Node 22.18 or later (type stripping); `tsc` and `esbuild` from the installed video workspace for the compile and render tests.

**Spec:** `docs/superpowers/specs/2026-10-05-explain-film-design.md` — this wave implements §5.1 (the types), §5.2, the mark rules of §6 and the kit cases of §9.1. Wave map: `docs/superpowers/waves/2026-10-05-explain-film.yaml` (wave `film-kit`). `kit/guard.ts` belongs to wave `film-guard`.

## Global Constraints

- Branch `feat/explain-film`, cut from `feat/explain-brainrot` (tip `c19b42f` on 2026-10-05). Never commit to the brainrot branch or to `main`.
- Files this wave may change: new files under `skills/explain/video/src/kit/` (not `guard.ts`), new `skills/explain/tests/test_film_kit.py`, new fixtures `skills/explain/tests/fixtures/film-timeline.json`, `film-kit-scene.tsx`, `film-kit-forged.ts`. Nothing else: not `types.ts`, `Root.tsx`, `tsconfig.json` or the package files. No new dependency.
- The kit imports `react` types and its own files only. It has no `remotion` import: a scene reads the frame and passes it in.
- `palette.ts`, `motion.ts`, `marks.ts`, `source.ts` and `mono.ts` have no runtime import (`mono.ts` may use `import type`) and only syntax that type stripping can erase: no `enum`, no `namespace`, no parameter property.
- Stage 1280×720 at 30 fps; `MIN_TEXT` 14; a mono character advances `0.6 * size`; positions count code points, not UTF-16 units.
- Tests: `unittest`, run from `skills/explain`. Pure modules run in Node as `tests/test_short_logic.py` runs them (`node --input-type=module -e`, file URLs, one JSON line out) and are skipped only when `node` is missing. Compile and render tests need `<ws>/app/node_modules/.bin/tsc` and `esbuild` (`<ws>` is `$EXPLAIN_VIDEO_WORKSPACE`, else `~/karpathy/video-workspace`); they are skipped, naming `scripts/video-workspace.sh`, when either is missing. They reach the workspace only through a link from a temporary copy and write nothing there.
- Each test's docstring names the mutation that turns it red. Each new assertion is seen to fail before the code exists; an assertion that passes at once is checked by applying its named mutation, seeing the failure, and reverting.
- Each new file starts with a short comment that says what it is for, as the files of `video/src/` do.
- Commits: `<type>: <description>`, ending with the attribution line of the session.

## The scene's import surface

`index.ts` exports exactly these names (spec §5.1, §5.2, §6):

```ts
// palette.ts
export const C: Record<"bg"|"panel"|"text"|"muted"|"line"|"blue"|"green"|"yellow"|"red", string>;
export const MONO: string, SANS: string;
export const STAGE: { width: 1280; height: 720; fps: 30 };
export const MIN_TEXT: 14;
// motion.ts
export const p:   (frame: number, start: number, len: number) => number;
export const lin: (frame: number, start: number, len: number) => number;
export const lerp: (a: number, b: number, t: number) => number;
export type Pt = { x: number; y: number };
export const mix: (a: Pt, b: Pt, t: number) => Pt;
export const mixColor: (a: string, b: string, t: number) => string;
// marks.ts (types only)
export type Where = { sentence: number } | { word: string; nth?: number };
export type At<S extends string> = {
  (scene: S, where?: Where): number;
  said(scene: S): number;
  end(scene: S): number;
};
// source.ts (type only)
export type Source = { readonly path: string; readonly from: number;
                       readonly lines: readonly string[]; readonly [fromDisk]: true };
// index.ts
export type FilmProps<S extends string, R extends string> = { at: At<S>; sources: Record<R, Source> };
// text.tsx, draw.tsx
type TextProps = { x: number; y: number; size: number; text: string; fill?: string;
                   opacity?: number; anchor?: "start"|"middle"|"end"; weight?: number };
export function Mono(props: TextProps): ReactElement | null;
export function Sans(props: TextProps): ReactElement | null;
export function Draw(props: { d: string; t: number; stroke: string; width?: number;
                              opacity?: number }): ReactElement | null;
export function Mark(props: { kind: "check"|"cross"; x: number; y: number; t: number;
                              scale?: number; opacity?: number }): ReactElement;
// code.tsx
export type Card = { x: number; y: number; width: number; size: number };
export type Band = { line: number; color: string; opacity: number };
export type Tint = { line: number; from: number; to: number; color: string };
export const colX:  (card: Card, index: number) => number;
export const lineY: (card: Card, source: Source, line: number) => number;
export function CodeCard(props: { card: Card; source: Source; bands?: Band[];
                                  tints?: Tint[]; opacity?: number }): ReactElement;
```

For the pipeline only, not in `index.ts` (wave `film-render` imports them in `FilmStage`):

```ts
// marks.ts
export type MarkScene = { id: string; from: number; durationInFrames: number; leadFrames: number;
                          audioFrames: number; sentences: readonly number[];
                          words: readonly { text: string; from: number; to: number }[] };
export const makeAt: <S extends string>(scenes: readonly MarkScene[]) => At<S>;
// source.ts
export const sourceFromDisk: (raw: { path: string; from: number; lines: readonly string[] }) => Source;
export const requireFromDisk: (source: Source) => void;
```

`MarkScene` is the film scene of the timeline that wave `film-timeline` builds (its plan, section "The film timeline"): `sentences` and `words` hold scene-relative frames.

## Beyond the letter of the spec

Spec §5.1 rests the rule "the code card shows only lines read from disk" on the type brand of `Source` and on the cast tokens that §7.2 refuses. A probe with the pinned `tsc` (2026-10-05) showed four ways to get a `Source` that use none of those tokens: `{} as Source`; a literal whose `lines` is cast to `readonly string[]`, then `as Source`; `<Source>{}` in a `.ts` file; and a value of type `any` from `JSON.parse` or a one-argument `Object.assign`. So this plan adds a check at run time: `sourceFromDisk` records each object it makes, and `CodeCard` throws for a source that is not recorded. The brand stays as the compile-time message for the plain mistake. The user confirms or strikes this at plan review; if struck, Task 3 drops `requireFromDisk` and the freeze, and Task 5 drops its two cases.

## Review Focus

1. A mark word typed in another case or with other punctuation than the narration (`Verify.sh` for `` `verify.sh` ``, `handler` for `handler.`): it matches. `self` does not match `self-contained`. Pinned in Task 2.
2. A word that the scene says more than once: without `nth` the first one; an `nth` past the count is an error that names the count. Pinned in Task 2.
3. A source that scene code copied, edited or rebuilt (a spread, a JSON round trip, a cast): `CodeCard` throws and names the fix. Pinned in Tasks 3 and 5.
4. A band or a tint on a line that the source does not hold, and a tint range that passes the cut of the line: the first throws with the source's range, the second is clipped. Pinned in Tasks 3 and 5.
5. A code line with leading spaces or a character outside the BMP: the spaces are kept and every position counts code points. Pinned in Tasks 3 and 4.

---

### Task 1: `palette.ts` and `motion.ts`

**Files:**
- Create: `skills/explain/video/src/kit/palette.ts`, `skills/explain/video/src/kit/motion.ts`
- Create: `skills/explain/tests/test_film_kit.py`

**Interfaces:**
- Consumes: the `run_node` pattern of `tests/test_short_logic.py`.
- Produces: the palette and motion names of "The scene's import surface"; in the test module, `run_node(script)` and `kit_url(name)` (the file URL of a kit module) for Tasks 2 and 3.

- [ ] **Step 1: Write the failing tests**

Classes `TestPalette` and `TestMotion`:

- `test_palette_values`: the module's values equal:

```json
{
  "C": { "bg": "#0f1115", "panel": "#141820", "text": "#ece9e4", "muted": "#8b919b", "line": "#4b525d",
         "blue": "#58c4dd", "green": "#83c167", "yellow": "#f4d345", "red": "#fc6255" },
  "MONO": "ui-monospace, \"SF Mono\", Menlo, monospace",
  "SANS": "-apple-system, BlinkMacSystemFont, \"Helvetica Neue\", Arial, sans-serif",
  "STAGE": { "width": 1280, "height": 720, "fps": 30 },
  "MIN_TEXT": 14
}
```

- `test_p_is_cubic_in_out`: `p(f, 10, 20)` for f = 5, 10, 15, 20, 25, 30, 40 is 0, 0, 0.0625, 0.5, 0.9375, 1, 1.
- `test_lin_is_linear`: `lin(f, 10, 20)` for f = 5, 10, 15, 20, 30, 40 is 0, 0, 0.25, 0.5, 1, 1.
- `test_len_zero_or_less_is_a_step`: `p` and `lin` with `len` 0 and -5 and `start` 10 give 0 at frame 9 and 1 at frames 10 and 11.
- `test_lerp_and_mix`: `lerp(2, 6, 0.25)` is 3 and `lerp(2, 6, 1.5)` is 8; `mix({x: 0, y: 10}, {x: 10, y: 30}, 0.5)` is `{x: 5, y: 20}`.
- `test_mix_color_reads_both_forms`: `mixColor("#000000", "#ffffff", 0.5)` is `rgb(128, 128, 128)`; `mixColor("rgb(255, 0, 0)", "#0000FF", 0.25)` is `rgb(191, 0, 64)`; `t` of -1 and 2 give the first and the second colour; a result is itself a valid input.
- `test_mix_color_refuses_other_forms`: `"red"`, `"#fff"` and `"rgb(1, 2)"` each throw `mixColor: not a colour: "<value>"`.
- `test_every_palette_colour_is_a_mix_color_input`: `mixColor(v, v, 0)` does not throw for each value of `C`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_kit -v`
Expected: every test FAILS with `ERR_MODULE_NOT_FOUND`.

- [ ] **Step 3: Write `palette.ts` and `motion.ts`**

`p` is 0 up to `start`, then the cubic in-out curve (`4u³` below the middle, `1 - (2 - 2u)³ / 2` above it, `u` the fraction of `len` done), then 1. `lin` is the same with `u` itself. `lerp` does not clamp. `mixColor` clamps `t` to 0..1, mixes each channel, rounds it, and always returns the `rgb(r, g, b)` form; hex digits may be in either case.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_kit -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/src/kit/palette.ts skills/explain/video/src/kit/motion.ts skills/explain/tests/test_film_kit.py
git commit -m "feat: explain: film kit palette and motion"
```

### Task 2: `marks.ts`

**Files:**
- Create: `skills/explain/video/src/kit/marks.ts`, `skills/explain/tests/fixtures/film-timeline.json`
- Test: `skills/explain/tests/test_film_kit.py`

**Interfaces:**
- Consumes: `run_node`, `kit_url` (Task 1).
- Produces: `Where`, `At`, `MarkScene`, `makeAt` as in "The scene's import surface".

- [ ] **Step 1: Write the fixture**

`film-timeline.json` is a film timeline by hand, in the shape of the `film-timeline` plan: top level `"format": "film"`, `fps` 30, 1280×720, `totalFrames` 324, `maxSceneSeconds` 30, `maxTotalSeconds` 150, `engine` `say`, `sources` `{}`, and `checkFrames` 43 `s1`, 118 `s2`, 152 `end` for `type` and 196 `s1`, 271 `s2`, 323 `end` for `checks`. Two scenes, each with `leadFrames` 6, `audioFrames` 135, `sentences` `[6, 96]` and eight words at the frames 6–21, 21–36, 36–51, 51–66, 66–81, 96–111, 111–126, 126–141:

| Scene | `from` | `durationInFrames` | Word texts, in order |
|---|---|---|---|
| `type` | 0 | 153 | `The` `router` `picks` `a` `handler.` `The` `handler` `replies.` |
| `checks` | 153 | 171 | `The` `` `verify.sh` `` `check` `is` `self-contained.` `Then` `it` `stops.` |

- [ ] **Step 2: Write the failing tests**

Class `TestMarks`; `at` is `makeAt` over the fixture's scenes, and a thrown error is read by its message:

- `test_scene_start_is_the_first_sentence`: `at("type")` is 6 and equals `at("type", {sentence: 1})`; `at("checks")` is 159.
- `test_sentence_mark`: `at("type", {sentence: 2})` is 96; `at("checks", {sentence: 2})` is 249.
- `test_word_mark`: `{word: "router"}` on `type` is 21; `{word: "Router"}` is 21; `{word: "handler"}` is 66 (the token `handler.`); `{word: "then"}` on `checks` is 249.
- `test_word_mark_nth`: `{word: "handler", nth: 2}` is 111; `{word: "the", nth: 2}` is 96; `nth: 1` equals no `nth`.
- `test_word_mark_ignores_punctuation_and_backticks`: `{word: "Verify.sh"}` on `checks` is 174; `{word: "self-contained"}` is 219.
- `test_word_mark_matches_the_whole_token`: `{word: "self"}` on `checks` throws `MARK scene checks: word "self" is not in the narration`.
- `test_said_and_end`: `at.said("type")` is 141 and `at.end("type")` is 153; `at.said("checks")` is 294 and `at.end("checks")` is 324.
- `test_mark_errors`: each message exactly:
  - `at("nope")`, `at.said("nope")`, `at.end("nope")` → `MARK scene nope: no such scene`
  - `{sentence: 0}`, `{sentence: 1.5}`, `{sentence: -1}` → `MARK scene type: sentence <n> is not a positive integer`
  - `{sentence: 3}` → `MARK scene type: sentence 3 is past the last one (2)`
  - `{word: "handler", nth: 0}` → `MARK scene type: nth 0 is not a positive integer`
  - `{word: "handler", nth: 3}` → `MARK scene type: nth 3 is past the last "handler" (2)`
  - `{word: "--"}` → `MARK scene type: word "--" has no letter or digit`
  - `{word: "zebra"}` → `MARK scene type: word "zebra" is not in the narration`

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_kit.TestMarks -v`
Expected: all FAIL with `ERR_MODULE_NOT_FOUND`.

- [ ] **Step 4: Write `marks.ts`**

A mark is the scene's `from` plus the scene-relative frame of the sentence or of the word's start. `said` is `from + leadFrames + audioFrames`; `end` is `from + durationInFrames`. A word and a token match when they are equal after `toLowerCase()` and the removal of every character that is not a Unicode letter or digit. The count in the `nth` message is the number of tokens that match.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_kit -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/video/src/kit/marks.ts skills/explain/tests/fixtures/film-timeline.json skills/explain/tests/test_film_kit.py
git commit -m "feat: explain: film kit marks by scene, sentence and word"
```

### Task 3: `source.ts` and `mono.ts`

**Files:**
- Create: `skills/explain/video/src/kit/source.ts`, `skills/explain/video/src/kit/mono.ts`
- Test: `skills/explain/tests/test_film_kit.py`

**Interfaces:**
- Consumes: `run_node`, `kit_url` (Task 1).
- Produces: `Source`, `sourceFromDisk`, `requireFromDisk` (above), and in `mono.ts`:

```ts
export const ADVANCE: 0.6;
export const monoWidth: (text: string, size: number) => number;
export type Card = { x: number; y: number; width: number; size: number };
export type Band = { line: number; color: string; opacity: number };
export type Tint = { line: number; from: number; to: number; color: string };
export type Span = { text: string; color?: string };
export const colX:  (card: Card, index: number) => number;
export const lineY: (card: Card, source: Source, line: number) => number;
export const fitColumns: (card: Card) => number;
export const cardHeight: (card: Card, lineCount: number) => number;
export const lineSpans: (text: string, tints: readonly Tint[], columns: number) => Span[];
export const requireLine: (source: Source, line: number) => void;
```

- [ ] **Step 1: Write the failing tests**

`card` is `{x: 100, y: 50, width: 600, size: 20}`; `src` is a source of `src/app.py` from line 47 with 8 lines; `A` and `B` are two colours.

Class `TestSource`:
- `test_a_source_from_disk_is_accepted`: `requireFromDisk(sourceFromDisk(raw))` returns.
- `test_a_copy_or_a_rebuilt_source_is_refused`: a spread copy, a JSON round trip and a plain object with the same keys each throw `CodeCard: the source was not read from disk; declare it in "sources" of script.json`.
- `test_a_source_cannot_change`: the source and its `lines` are frozen (a write to `lines[0]` throws `TypeError`); a later change of the array given to `sourceFromDisk` does not change `lines`.

Class `TestMono`:
- `test_mono_width_counts_code_points`: `monoWidth("abc", 20)` is 36; `monoWidth("a😀", 20)` is 24; `ADVANCE` is 0.6.
- `test_col_x`: `colX(card, 0)` is 188 and `colX(card, 10)` is 308.
- `test_line_y`: lines 47, 48 and 54 give 86, 118 and 310.
- `test_fit_columns`: 41 for `card`; 0 for the same card with `width` 80.
- `test_card_height`: `cardHeight(card, 8)` is 288.
- `test_line_spans`: on `"abcdef"` with 41 columns: no tint → `[{text: "abcdef"}]`; `{from: 1, to: 3, color: A}` → `a`, `bc` in A, `def`; tints `{0, 4, A}` then `{2, 6, B}` → `ab` in A, `cdef` in B; `{from: 3, to: 3}`, and `from` 5 with `to` 2, colour nothing; `{from: -2, to: 1, color: A}` → `a` in A, `bcdef`.
- `test_line_spans_cut`: 4 columns → `[{text: "abcd"}]`; with `{from: 2, to: 99, color: A}` → `ab`, `cd` in A; `""` → `[]`; for each case the span texts joined equal the cut text.
- `test_line_spans_count_code_points`: `"a😀b"` with `{from: 1, to: 2, color: A}` → `a`, `😀` in A, `b`.
- `test_require_line`: lines 47 and 54 return; 46 and 55 throw `CodeCard: line <n> is outside src/app.py:47-54`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_kit.TestSource tests.test_film_kit.TestMono -v`
Expected: all FAIL with `ERR_MODULE_NOT_FOUND`.

- [ ] **Step 3: Write `source.ts` and `mono.ts`**

`source.ts`: the brand is `declare const fromDisk: unique symbol`, not exported. `sourceFromDisk` copies `lines`, freezes the copy and the object, and records the object; `requireFromDisk` throws for an object that is not recorded.

`mono.ts`, with padding 16, a gutter of 4 columns for the line number, 2 columns between the gutter and the text, and rows of `1.6 * size`:
- `colX(card, i)` = `card.x + 16 + (6 + i) * 0.6 * card.size`
- `lineY(card, source, line)` = `card.y + 16 + card.size + (line - source.from) * 1.6 * card.size` (the baseline; it does not check that the source holds the line)
- `fitColumns(card)` = the whole columns between `colX(card, 0)` and `card.x + card.width - 16`, at least 0
- `cardHeight(card, n)` = `32 + n * 1.6 * card.size`
- `lineSpans` cuts `text` to `columns` code points, clips each tint to the cut text, lets a later tint win where two overlap, and joins neighbours of one colour into one span. It reads `from`, `to` and `color` of a tint and ignores `line`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_kit -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/src/kit/source.ts skills/explain/video/src/kit/mono.ts skills/explain/tests/test_film_kit.py
git commit -m "feat: explain: film kit source from disk and the mono grid"
```

### Task 4: `text.tsx`, `draw.tsx` and the render harness

**Files:**
- Create: `skills/explain/video/src/kit/text.tsx`, `skills/explain/video/src/kit/draw.tsx`
- Test: `skills/explain/tests/test_film_kit.py`

**Interfaces:**
- Consumes: `palette.ts`, `mono.ts`.
- Produces: `Mono`, `Sans`, `Draw`, `Mark`. In the test module, for Tasks 5 and 6: `kit_app()` (a temporary copy of `skills/explain/video/` with `node_modules` linked to `<ws>/app/node_modules`) and `render_kit(entry_source)`, which writes `src/kitcheck/entry.tsx` in that copy, bundles it, runs it and returns the JSON that the entry prints. The entry imports the kit, renders with `renderToStaticMarkup` of `react-dom/server` inside an `<svg>`, and prints one JSON object of markup strings and error messages.

```bash
node_modules/.bin/esbuild src/kitcheck/entry.tsx --bundle --format=cjs --platform=node --outfile=out.cjs --log-level=warning
node out.cjs
```

`--format=cjs` is needed: the server build of `react-dom` calls `require("util")`, which an ESM bundle refuses (probed 2026-10-05, esbuild 0.28.1).

- [ ] **Step 1: Write the failing tests**

Class `TestKitDraws`, skipped as Global Constraints says; markup is read with `xml.etree.ElementTree`:

- `test_mono_forces_the_advance`: `<Mono x={10} y={20} size={20} text="  ab😀" />` is one `text` element with `x` 10, `y` 20, `textLength` 60, `font-size` 20, `font-family` equal to `MONO`, `fill` `#ece9e4`, `text-anchor` `start`, a style of `white-space:pre`, and the content `  ab😀` with its two leading spaces.
- `test_sans_has_no_forced_advance`: the same props on `Sans` give `font-family` equal to `SANS` and no `textLength`; `anchor="middle"` and `weight={600}` give `text-anchor` `middle` and `font-weight` 600.
- `test_empty_or_invisible_text_draws_nothing`: `Mono` and `Sans` with `text=""`, and with `opacity={0}`, add no element to the `svg`.
- `test_draw_shows_the_first_part_of_a_stroke`: `t` 0 adds no element; `t` 0.25 gives one `path` with the given `d`, `fill` `none`, `pathLength` 1, `stroke-dashoffset` 0.75 and `stroke-width` 2; `t` 2 gives `stroke-dashoffset` 0.
- `test_mark_kinds`: `kind="check"` strokes `#83c167` and `kind="cross"` strokes `#fc6255`, each inside a `g` with `transform` `translate(10 20) scale(2)` for `x` 10, `y` 20, `scale` 2.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_kit.TestKitDraws -v`
Expected: all FAIL: esbuild cannot resolve `../kit/text`.

- [ ] **Step 3: Write `text.tsx` and `draw.tsx`**

Defaults: `fill` `C.text`, `opacity` 1, `anchor` `start`, `weight` 400, stroke `width` 2, `scale` 1. `Mono` takes its `textLength` from `monoWidth` and keeps white space. `Mono` and `Sans` return `null` for an empty text or an opacity of 0 or less; `Draw` returns `null` for a `t` or an opacity of 0 or less, treats a `t` above 1 as 1, and draws with round caps and joins. `Mark` is a `Draw` of a check in `C.green` or a cross in `C.red`, stroke width 3, about 16 px wide at scale 1 and centred on `(x, y)`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_kit -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/src/kit/text.tsx skills/explain/video/src/kit/draw.tsx skills/explain/tests/test_film_kit.py
git commit -m "feat: explain: film kit text and strokes, rendered in tests"
```

### Task 5: `code.tsx` — the code card

**Files:**
- Create: `skills/explain/video/src/kit/code.tsx`
- Test: `skills/explain/tests/test_film_kit.py`

**Interfaces:**
- Consumes: `mono.ts`, `source.ts`, `palette.ts`, `render_kit` (Task 4).
- Produces: `CodeCard`, and the re-export of `Card`, `Band`, `Tint`, `colX`, `lineY` from `mono.ts`.

- [ ] **Step 1: Write the failing tests**

Class `TestCodeCard`, with `card` and an 8-line source as in Task 3, made with `sourceFromDisk` in the entry. Line 49 is 60 characters long, line 50 is empty, line 51 starts with four spaces.

- `test_card_frame`: the first `rect` has `x` 100, `y` 50, `width` 600, `height` 288, `fill` `#141820` and `stroke` `#4b525d`.
- `test_line_numbers_and_lines`: the texts `47` to `54` have `text-anchor` `end` and `x` 164; the code text of line k has `x` 188 and `y` `lineY(card, source, k)`; line 51 keeps its four leading spaces.
- `test_a_long_line_is_cut_without_an_ellipsis`: the code text of line 49 holds its first 41 characters and has `textLength` 492.
- `test_an_empty_line_draws_its_number_only`: the card has 15 `text` elements: 8 numbers and 7 code lines.
- `test_a_tint_is_a_tspan_inside_the_line`: with `{line: 48, from: 2, to: 5, color: "#58c4dd"}` the code text of line 48 has one `tspan` with `fill` `#58c4dd` that holds characters 2 to 4 of the line, its whole content is still the line, and the card still has 15 `text` elements.
- `test_a_band_is_a_bar_behind_one_line`: `{line: 48, color: "#f4d345", opacity: 0.2}` gives a `rect` with `x` 108, `y` 98, `width` 584, `height` 32, that fill and that opacity, placed before the first `text` in document order.
- `test_card_opacity`: `opacity={0.5}` is the `opacity` of the outer `g`.
- `test_a_source_not_from_disk_is_refused`: a spread copy of the source as `source` → the render throws `CodeCard: the source was not read from disk; declare it in "sources" of script.json`.
- `test_a_band_or_tint_outside_the_source_is_refused`: a band on line 99, and a tint on line 46, each throw `CodeCard: line <n> is outside src/app.py:47-54`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_kit.TestCodeCard -v`
Expected: all FAIL: esbuild cannot resolve `../kit/code`.

- [ ] **Step 3: Write `code.tsx`**

`CodeCard` first calls `requireFromDisk(source)`, then `requireLine` for each band and each tint. It draws, inside one `g` that carries `opacity` (default 1): the frame (`cardHeight`, corner radius 8, `C.panel`, a 2 px `C.line` stroke); the bands (from `card.x + 8` to `card.x + card.width - 8`, top `lineY - card.size`, height `1.6 * card.size`, corner radius 4); then for each line its number (a `Mono` in `C.muted`, right edge at `card.x + 16 + 4 * 0.6 * card.size`, size `card.size`) and, when the line is not empty, one text element at `colX(card, 0)` in `C.text` with the same font, size, white space and forced advance as `Mono`, whose content is the spans of `lineSpans(line, tints of that line, fitColumns(card))`: a span with a colour is a `tspan` with that `fill`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_kit -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/src/kit/code.tsx skills/explain/tests/test_film_kit.py
git commit -m "feat: explain: film kit code card with bands and tints"
```

### Task 6: `index.ts` and the compile tests

**Files:**
- Create: `skills/explain/video/src/kit/index.ts`
- Create: `skills/explain/tests/fixtures/film-kit-scene.tsx`, `skills/explain/tests/fixtures/film-kit-forged.ts`
- Test: `skills/explain/tests/test_film_kit.py`

**Interfaces:**
- Consumes: every kit file; `kit_app()` (Task 4).
- Produces: `../kit` as the import of a scene, with `FilmProps`. `script.gen.ts` of wave `film-timeline` imports `FilmProps` from it.

- [ ] **Step 1: Write the fixtures and the failing tests**

`film-kit-scene.tsx` is a small scene in the shape a film author writes: `export function Scene(props: FilmProps<"type" | "checks", "app">)` that returns one `g`. It imports every value and type of "The scene's import surface" from `../kit` and uses each one at least once (the app has `noUnusedLocals`), with marks of all three kinds and `at.said` and `at.end`.

`film-kit-forged.ts` holds three faults, one on a line of its own, each line ending in a marker comment (`// FORGED`, `// UNKNOWN`, `// MAKER`): a constant typed `Source` whose value is an object literal with `path`, `from` and `lines`; a call `props.at("no-such-scene")` on `FilmProps<"type" | "checks", never>`; and an import of `sourceFromDisk` from `../kit` that the file uses.

Class `TestKitCompiles`, skipped as Global Constraints says; each test copies its fixture into `src/kitcheck/` of a fresh `kit_app()` and runs:

```bash
node_modules/.bin/tsc
```

- `test_the_app_and_a_scene_compile`: with `film-kit-scene.tsx` as `src/kitcheck/Scene.tsx` → exit 0 and no output.
- `test_forged_source_unknown_scene_and_maker_do_not_compile`: with `film-kit-forged.ts` as `src/kitcheck/forged.ts` → exit 2, and the lines that hold `error TS` are exactly three: `TS2741` on the `FORGED` line, `TS2345` on the `UNKNOWN` line and `TS2305` on the `MAKER` line, each in `src/kitcheck/forged.ts`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_kit.TestKitCompiles -v`
Expected: both FAIL with `TS2307` (no module `../kit`).

- [ ] **Step 3: Write `index.ts`**

It exports the names of "The scene's import surface" and nothing else: the values of `palette.ts` and `motion.ts`, the components, `colX` and `lineY`, the types `Pt`, `Card`, `Band`, `Tint`, `Where`, `At`, `Source`, and `FilmProps`. It does not export `makeAt`, `MarkScene`, `sourceFromDisk`, `requireFromDisk`, `ADVANCE` or the other helpers of `mono.ts`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/explain && python3 -B -m unittest tests.test_film_kit -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/video/src/kit/index.ts skills/explain/tests/fixtures/film-kit-scene.tsx skills/explain/tests/fixtures/film-kit-forged.ts skills/explain/tests/test_film_kit.py
git commit -m "feat: explain: film kit index; a scene compiles, a forged source does not"
```

---

## Wave close

Run the map's acceptance: `cd skills/explain && python3 -B -m unittest tests.test_film_kit -v` — all PASS, and no test of `TestKitDraws`, `TestCodeCard` or `TestKitCompiles` is skipped (a skip means the workspace packages are not installed. Do not install from this branch into the shared workspace: set `EXPLAIN_VIDEO_WORKSPACE` to a directory of your own, run `scripts/video-workspace.sh --engine say` there, about a minute and 447 MB, and run again). `test_the_app_and_a_scene_compile` is the map's "`tsc` exits 0 on a temporary copy of `video/` linked to the installed packages". Then the unit suite, `cd skills/explain && python3 -B -m unittest discover -s tests`: all PASS. Update the wave map: `film-kit` `status: done`.

Inputs for the plans of later waves:
- `film-render`: `FilmStage` makes `at` with `makeAt` (from `./kit/marks`) and each source with `sourceFromDisk` (from `./kit/source`); a test passes a timeline built by the real `build-timeline.mjs` to `makeAt`.
- `film-scene-stage`: the import rule of spec §7.2 (`../kit` only) is what keeps a scene from `./kit/source`; a plant that passes a copied source to `CodeCard` should stop the render with the message of Task 3.
