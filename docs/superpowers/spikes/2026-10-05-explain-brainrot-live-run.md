# Explain brainrot rung: live run on ste_lint.py

Date: 2026-10-05.

These sections follow: the limits stress render (now), then the live run, the limit changes and the acceptance (added by the later tasks).

## Limits stress render

I wrote a script in which every limited text sits exactly at its brainrot limit, rendered it, and measured the stills. I changed no limit. This section only records what the layout does at the limits.

### The script

`skills/explain/tests/fixtures/brainrot-limits-script.json` has six scenes: a `title` scene, `bullets-appear` (4 bullets, the most the validator allows), `diagram-with-highlight-walk` (7 nodes, the most allowed, and 6 edges), `code-with-line-highlights` (lines 1 to 14 of `tests/fixtures/limits-source.txt`, each line exactly 40 columns), `before-after` (5 lines in each panel) and a second `title` scene. Each text is made of title-case words with many `m` and `w` letters, so the letters are wide. The numbers are:

- title 30 characters, subtitle 60;
- bullet 28;
- diagram label 12, sub 20, edge label 10 (the edge label limit is 10 for both formats);
- code 14 lines of 40 columns;
- `before-after` heading 30, 5 lines of 30 characters in each panel;
- the heading of each of the four scenes that are not `title` scenes: 40 characters (the formats have no limit for it today).

The cue sentence of scene 1 starts with `Wonderful Mixed Maps`, three words that join to 20 characters (the value of `captionChars`). The cue sentence of the last scene starts with the backticked name `EXPLAIN_BRAINROT_BACKGROUNDS` (28 characters). The script passes the validator and the prose lint with no error and no warning.

### The render

The kept directory is `/Users/valukin/karpathy/out/2026-10-05-limits-stress-brainrot/`. It is discardable output outside git. `script.json` there is the fixture with `provenance.root` set to `/Users/valukin/karpathy-wt/feature/skills/explain`. The background folder is an empty temporary folder, so a clip in the shared workspace cannot change the stills. The command was:

```
EXPLAIN_BRAINROT_BACKGROUNDS=<empty temp dir> EXPLAIN_BRAINROT_SEED=7 skills/explain/scripts/render.sh /Users/valukin/karpathy/out/2026-10-05-limits-stress-brainrot --engine say
```

The full stdout (exit code 0, ten stage lines):

```
script: ok (6 scenes)
workspace: ok /Users/valukin/karpathy/video-workspace
  narration: hook say 2.089 s (synthesized)
  narration: bullets say 5.641 s (synthesized)
  narration: diagram say 4.220 s (synthesized)
  narration: code say 2.925 s (synthesized)
  narration: before-after say 4.225 s (synthesized)
  narration: folder say 3.979 s (synthesized)
narration (say): ok
timeline (6 scenes, 26.8 s): ok
background: ok generated
render (10.4 s, 0.39 render-min/video-min): ok
container: ok (26.77 s)
sync: ok
stills (18): ok /Users/valukin/karpathy/out/2026-10-05-limits-stress-brainrot/review
transcript: ok
```

I read all 18 stills with the Read tool. The gated test `test_limits_stills_keep_panel_margins` also passes: in every still there is no ink in the outer 24 px of the panel (x 0 to 23 and x 1057 to 1079, y 0 to 911). The only ink that comes near the left margin is a bullet marker in the middle of its slide-in, at x 32 in `still-02-bullets.png`.

### How I measured

Each ink box is the result of `ink_extent` in `skills/explain/tests/png_diff.py` over the box in the "box" column. Ink is a pixel that differs from white by more than 40 levels in some channel. The coordinates are pixels of the 1080 by 1920 still, and both ends of a range are included.

- The fill of a width limit is the ink width divided by the width the text must fit, the width of the box. The widest instance of each text is the one in the row.
- The fill of a line limit is the ink height divided by the height of the box.
- A fill of 1.00 or more means the text does not fit. Where the layout cuts the text, the measured ink is the cut text, so the fill reads as 0.99 or less. I then give an estimate of the real fill, worked out from the same letters in texts that did fit.
- The caption rows are judged by eye on the cue stills, because the background is not white. Their ink box is the black outline of the letters, and the fill there is the ink width divided by the 1000 px maximum width of the caption band.

The boxes come from `video/src/box.ts` (`BRAINROT_BOX`: panel 1080 by 960, margin 48, content box 984 by 758 at x 48 to 1031, y 154 to 911) and from the scene files in `video/src/scenes/`, `layout.tsx` and `short/CaptionBand.tsx`.

| Limit | Value | Still | Box (source) | Ink box | Fill | Fault or none |
|---|---|---|---|---|---|---|
| `title` title | 30 | `still-06-folder-1.png` | text column x 48 to 1031, 984 wide (`Title.tsx`: padding is the box margin) | x 65 to 1013, y 327 to 393: the widest line, 949 by 67 | 0.96 | None. The title wraps to 2 lines, and the second line is one word (`Now`, `Mixes`). The scene 1 line is 941 wide. |
| `title` subtitle | 60 | `still-01-hook-1.png` | the same column, 984 wide | x 95 to 985, y 549 to 588: the widest line, 891 by 40 | 0.91 | None. It wraps to 2 lines. |
| `bullets-appear` text | 28 | `still-02-bullets-4.png` | text cell x 86 to 1031, 946 wide: the content box minus the 14 px marker and the 24 px gap (`BulletsAppear.tsx`) | x 88 to 711, y 471 to 510: bullet 4, 624 by 40 | 0.66 | None. All four bullets are on one line. |
| code columns | 40 | `still-04-code.png` | code text x 130 to 1031, 902 wide: the content box minus the 4-character gutter (`CodeHighlights.tsx`, 34 px type) | x 130 to 947, y 162 to 821: 818 by 660 | 0.91 | None. 84 px are free on the right. |
| code lines | 14 | `still-04-code.png` | content box height 758, y 154 to 911 | the same box: height 660 | 0.87 | None. The 14 rows of 48 px are 672 px. |
| `before-after` line chars | 30 | `still-05-before-after-1.png` | column x 48 to 1031, 984 wide (`BeforeAfter.tsx`, stacked) | x 48 to 625, y 824 to 849: the widest line, 578 wide | 0.59 | None. |
| `before-after` heading | 30 | `still-05-before-after-1.png` | the same column, 984 wide | x 50 to 665, y 162 to 197: 616 by 36 | 0.63 | None. |
| `before-after` lines | 5 | `still-05-before-after-1.png` | one stacked panel, 355 high: (758 minus the 48 px gap) divided by 2. The before panel is y 154 to 508, the after panel y 557 to 911. | before panel: x 48 to 1031, y 162 to 452, height 291. After panel: y 565 to 849, height 285. | 0.82 (before), 0.80 (after) | None. The heading and 5 lines fit in each half. |
| diagram `label` | 12 | `still-03-diagram-3.png` | the text area of a node: 254 wide (280 minus 2 times 3 px border and 2 times 10 px padding), `DiagramWalk.tsx` | node 5, `Warm Windows`: x 752 to 983, y 757 to 781: 232 by 25 | 0.91 | None. All seven labels are whole. |
| diagram `sub` | 20 | `still-03-diagram-3.png` | the same text area, 254 wide | widest whole sub, `Mixes Warm Weak Maps`: x 742 to 993, y 290 to 314: 252 by 25 | 0.99 whole; about 1.0 to 1.05 for the cut ones (estimate) | **Fault: cut.** Three of seven subs end in an ellipsis: `Warms Many Wide Ma…`, `Wakes Many Weak Ma…`, `Wakes Warm Wide Ma…`. The other four fit with 2 to 11 px to spare. |
| diagram edge label | 10 | `still-03-diagram-3.png` | the gap between two nodes in the same row: x 352 to 399 (48 wide) for the four horizontal edges. The nodes are 280 wide on a 328 px pitch. | a label on a vertical edge, `Warm Mixes`: x 717 to 852, y 398 to 417: 136 by 20 (`Map Weight`: 132) | 2.8 (136 divided by 48) | **Fault: hidden.** On the four horizontal edges the label is drawn behind the two node boxes, and only pieces show (`ed M`, `Win`, `ge M`, `le Mi`). The two labels on vertical edges show whole. |
| scene heading (no limit today) | 40 | `still-03-diagram.png`, and the start stills of scenes 2, 4 and 5 | one line, x 48 to 1031, 984 wide, 56 px bold, an ellipsis when too long (`layout.tsx` `SceneTitle`) | x 49 to 1020, y 60 to 111: 972 by 52 | 0.99 shown; about 1.2 for the whole text (estimate: about 30 px for each character) | **Fault: cut.** All four headings end in an ellipsis. Of the 40 characters, 30 to 34 show: `What Many Warm Wide Maps Mean f…`, `Warm Maps Win When Many Wide M…`, `Many Wide Mixes Make Weak Maps …`, `What the Mixer Writes for Many War…`. |
| caption chunk at the cap | 20 characters | `still-01-hook-1.png` | the band: centred at x 540 on the seam y 960, at most 1000 wide | outline x 141 to 936, y 928 to 1003: 796 by 76 | 0.80 | None. `Wonderful Mixed Maps` is one line at the full size (76 px), centred (centre x 538.5), and inside the frame. |
| caption, long name | 28 characters | `still-06-folder-1.png` | the same band | outline x 61 to 1018, y 939 to 991: 958 by 53 | 0.96 | None. `EXPLAIN_BRAINROT_BACKGROUNDS` is one line in smaller type (54 px), centred (centre x 539.5), with 61 px free on each side. It does not run off to the right. |
| caption ink over panel content | not a limit | all 18 stills | the panel content, which ends at y 911 | in all 18 stills there is no ink in y 912 to 927; the caption outline starts at y 928 (full size) or y 939 (smaller type) | not applicable | None. The lowest panel ink in any still is y 849 (`before-after`; the bottom node boxes end at y 841), so the caption starts at least 79 px below the content. |

### What the table shows

Three rows show a fault, and all three are in the layout at the limit, not in the script:

1. Scene headings of 40 characters are cut by an ellipsis in all four scenes. The heading has no limit today. About 30 to 34 characters of title-case text fit in 984 px at 56 px type.
2. Diagram `sub` text of 20 characters is cut in three of the seven nodes. The cut ones have the most `m` and `w` letters. The text is only slightly too wide for the node (about 0 to 5 percent).
3. Diagram edge labels of 10 characters are hidden behind the nodes on every horizontal edge. The nodes leave a gap of 48 px, and a label of 10 characters is about 136 px wide. A vertical edge has room for the label.

Fills at or under 0.80: the bullet text (0.66), the `before-after` line (0.59) and heading (0.63), the after panel height (0.80), and the cap-length caption (0.80 of the band width). These limits leave room. Fills over 1.0: the edge label (2.8), and, by estimate, the scene heading (about 1.2) and the cut `sub` texts (about 1.0 to 1.05). The code limits (0.91 and 0.87), the diagram label (0.91) and the titles (0.96 and 0.91) are close to the box but inside it.

The panel-margin test passes because the layout cuts or hides the text that is too wide, not because the text fits. So the test does not find the three faults above. The eye does.

The two caption findings of the earlier reviews are settled by the stills. The cap-length chunk is one line at the full size and is centred. The long name is one line in smaller type, inside the frame and centred. The caption never touches panel content in this script.

## Live run on ste_lint.py

Runner: a fresh Claude (Opus). I read only the skill text: `skills/explain/SKILL.md`, `skills/explain/rungs/brainrot.md`, sections 2 to 6 of `skills/explain/rungs/video.md` (I skipped section 1, as the rung says), section 4 of `skills/explain/rungs/sheet.md` (named by `video.md` section 2 step 3), `skills/explain/templates/brainrot-script.json` and `skills/ste/SKILL.md`. I also read the subject file in full. I did not read the tests, the pipeline source, the plans or the specs, and I never had to open any of them. For the note only, I read the example note `2026-10-04-explain-video-live-run.md` (format) and the "Limits stress render" section above (to append after it). That section told me two facts that the skill text does not give: edge labels hide on horizontal edges, and scene headings over about 30 characters are cut. I kept my headings short, but I wrote the diagram edge labels exactly as the skill text allows, to see if the skill text alone prepares a user. It does not (defect 1).

The output directory is `/Users/valukin/karpathy/out/2026-10-05-020741-brainrot-ste-lint/`. Provenance: root `/Users/valukin/karpathy-wt/feature`, commit `c19b42f`, dirty `no` (`git status --porcelain` printed nothing), and the file is tracked (`git ls-files --error-unmatch` exit 0). The background folder `~/karpathy/video-workspace/backgrounds/` exists and is empty, and `EXPLAIN_BRAINROT_BACKGROUNDS` is not set.

### Request and rung line

```
/explain skills/ste/scripts/ste_lint.py --as brainrot
```

Printed before the build:

```
Rung: brainrot (forced) — --as brainrot; the content fits: text goes through tokenize and lint to findings and an exit code — subject: skills/ste/scripts/ste_lint.py (file)
```

### Expectation compared with the build

The controller table was in my brief, so I saw it before I read the file. I chose the scenes from my own read of the file and compared them with the table only after the build. The match is close: the same five components in the same order.

| # | Scene id | Component | What it shows |
|---|---|---|---|
| 1 | `hook` | `title` | "How ste_lint.py checks prose" / "Short sentences, approved words, no contractions". Hook: "This lint keeps technical text short, clear and in approved words." (11 words) |
| 2 | `flow` | `diagram-with-highlight-walk` | 5 nodes `a1 b1 c1 c2 c3`: Text (Markdown or HTML), Tokenize (Counted sentences), lint (Rules per sentence), Findings (Line, column, rule), Exit code (0, 1 or 2); 4 edges; 5 walk steps |
| 3 | `rules` | `bullets-appear` | Over 25 words: error; Unapproved word: error; Contraction: error; Passive, gerund: warning |
| 4 | `finding` | `code-with-line-highlights` | `ste_lint.py` lines 447 to 453, the `Finding` dataclass; bands 449 to 450, 451, 452 to 453 |
| 5 | `result` | `before-after` | Before: `Input: "Utilize the tool."`, `1:1 E WORD: use USE`, `1 errors, 0 warnings`, `Exit code 1`. After: `Input: "Use the tool."`, `0 errors, 0 warnings`, `Exit code 0` |

Differences from the controller expectation, and why:

- Scene 2: the summary line is not a node. The Exit code node holds "0, 1 or 2", and the summary line shows in scene 5, where the real output of the lint is the point.
- Scene 3: the bullet for the unapproved word does not name the substitution. A real unapproved word in a bullet fails the prose lint, and a quoted example plus its substitution does not fit in 28 characters. The narration says "the message gives the approved word", and scene 5 shows `use USE`.
- Scene 4: lines 447 to 453 instead of 445 to 455. Lines 445, 446, 454 and 455 are blank; the content is the same. I measured the columns first with `awk` (the longest line is 30 columns).
- Scene 5: a sentence before and after the lint, with exit codes 1 and 0. Exit code 2 (usage error) shows only in the diagram node.
- `provenance.not_covered`: "The word count rules of Issue 9 Section 8, the HTML parser, the inflected verb forms and the paragraph rule."

Before the first render I ran the linter on a draft of all the prose (`0 errors, 0 warnings`) and on the two example sentences, to make sure that scene 5 shows the real output: `Utilize the tool.` gives `1:1  E WORD  "Utilize" is not approved; use USE`, `1 errors, 0 warnings`, exit 1; `Use the tool.` gives `0 errors, 0 warnings`, exit 0.

- Script iterations: 2 (the first draft, then one change after the stills).
- `render.sh` runs: 2, each with ten `ok` lines and no `FAIL`.
- Background: the generated runner loop. Narrator: Kokoro `af_heart`, no fallback.

### render.sh runs

Each run ran in the background with stdout and stderr in a log file. Neither run printed a progress meter: the workspace and the models were already in place, so nothing was trimmed. The `exit` line is from my wrapper.

Run 1 (first draft):

```
script: ok (5 scenes)
workspace: ok /Users/valukin/karpathy/video-workspace
  narration: hook kokoro 3.646 s (synthesized)
  narration: flow kokoro 13.820 s (synthesized)
  narration: rules kokoro 11.665 s (synthesized)
  narration: finding kokoro 10.435 s (synthesized)
  narration: result kokoro 9.922 s (synthesized)
narration (kokoro): ok
timeline (5 scenes, 52.6 s): ok
background: ok generated
render (18.4 s, 0.35 render-min/video-min): ok
container: ok (52.59 s)
sync: ok
stills (19): ok /Users/valukin/karpathy/out/2026-10-05-020741-brainrot-ste-lint/review
transcript: ok
exit 0
```

Ten `ok` lines, but the stills showed two faults:

1. The edge label `Blocks` (6 characters, inside the limit of 10) on the horizontal edge from `tokenize` to `lint` was cut: only `lock` showed, and the `B` was behind the `tokenize` node. This was in `still-02-flow.png`, `-1`, `-2`, `-4` and `-5` (in `-3` the label of the active edge hides, as the rung says). The 3-character label `str` on the other horizontal edge showed whole.
2. A false picture: the narration said "The first step, `tokenize`, cuts the text into sentences", after "Text comes in as Markdown or HTML". But HTML goes through `html_to_blocks` (`ste_lint.py:314`), which only reuses the splitter of `tokenize` (`ste_lint.py:315-316`).

Changes in `script.json`: I removed the `Blocks` label from the edge. I renamed the node from `tokenize` to `Tokenize` (the step, not the function). The flow sentence became "The first step cuts the text into sentences and counts the words." The cue `The first step` stayed the same.

Run 2 (final):

```
script: ok (5 scenes)
workspace: ok /Users/valukin/karpathy/video-workspace
  narration: hook kokoro 3.646 s (reused)
  narration: flow kokoro 12.924 s (synthesized)
  narration: rules kokoro 11.665 s (reused)
  narration: finding kokoro 10.435 s (reused)
  narration: result kokoro 9.922 s (reused)
narration (kokoro): ok
timeline (5 scenes, 51.7 s): ok
background: ok generated
render (18.0 s, 0.35 render-min/video-min): ok
container: ok (51.67 s)
sync: ok
stills (19): ok /Users/valukin/karpathy/out/2026-10-05-020741-brainrot-ste-lint/review
transcript: ok
exit 0
```

All 19 stills were clean. The stills section below has the details.

### Wall time

Wall clock from a time stamp on each output line of run 1 (1 s resolution). The workspace was warm, so there were no cost lines and no downloads.

| Stage | Run 1 | Note |
|---|---|---|
| script | 1 s | |
| workspace | below 1 s | already set up; no `npm ci`, no Chrome or model download |
| narration | 10 s | 5 Kokoro syntheses; the five indented lines came at the same second as the stage line |
| timeline | below 1 s | |
| background | below 1 s | `generated` |
| render | 18 s | |
| container | 1 s | |
| sync | below 1 s | |
| stills | 7 s | |
| transcript | below 1 s | |
| total | 37 s | run 2: 37 s (1 synthesis, 4 reused) |

### Stills read

I read all 19 stills of run 2 (the final state) with the Read tool, and all 19 of run 1 before. Each line gives what the still shows, the cue, and the three brainrot checks: caption (present and holds words of the cue sentence), caption over panel content, and background. In every still the caption band sits on the seam (the letters span about y 928 to 1000) and the lowest panel ink is above y 850, so no caption touches panel content. No bottom half is black.

- `still-01-hook.png`: title, rule and the subtitle at the start of its fade-in (faint). Start still, cue frame = lead end. Caption "This lint keeps", "This" yellow. No overlap. Background: runner in the right lane, in the air.
- `still-01-hook-1.png`: subtitle in full. Matches "This lint keeps". Caption "This lint keeps", "keeps" yellow. No overlap. Background: runner in the left lane, other obstacles than in the start still, so it moves.
- `still-02-flow.png`: 5 nodes, edge labels `str`, `sorted`, `severity`, Text node starts to highlight. Caption "Text comes in", "Text" yellow. No overlap. Background: runner in the left lane, an obstacle in the right lane.
- `still-02-flow-1.png`: Text highlighted. Matches "Text comes in". Caption the same chunk, "comes" yellow. No overlap. Background moved (the obstacle is gone, a far one is in view).
- `still-02-flow-2.png`: token on the edge into Tokenize, Tokenize highlighted, Text dim, `str` hidden. Matches "The first step". Caption "The first step", "step" yellow. No overlap. Background: runner in the right lane, in the air over an obstacle.
- `still-02-flow-3.png`: token into lint, lint highlighted. Matches "The lint applies". Caption "The lint applies", "applies" yellow. No overlap. Background: runner in the right lane over two obstacles.
- `still-02-flow-4.png`: token into Findings, `sorted` hidden. Matches "Each break becomes". Caption "Each break becomes", "break" yellow. No overlap. Background: runner in the left lane, in the air.
- `still-02-flow-5.png`: token into Exit code, `severity` hidden. Matches "The exit code". Caption "The exit code", "code" yellow. No overlap. Background: runner in the right lane.
- `still-03-rules.png`: heading, bullet 1 at the start of its slide-in (faint, the marker left of the margin). Caption "A sentence over", "sentence" yellow. No overlap. Background: runner in the middle lane, an obstacle in the left lane.
- `still-03-rules-1.png`: bullet 1 in full. Matches "A sentence over". Caption the same chunk. No overlap. Background moved (the obstacles moved down the road).
- `still-03-rules-2.png`: bullets 1 and 2. Matches "An unapproved word". Caption "An unapproved word", "unapproved" yellow. No overlap. Background: three obstacles, runner in the middle lane.
- `still-03-rules-3.png`: bullets 1 to 3. Matches "A contraction is". Caption "A contraction is", "contraction" yellow. No overlap. Background: runner in the air, no obstacle near.
- `still-03-rules-4.png`: all 4 bullets. Matches "Checks that can". Caption "Checks that can", "that" yellow. No overlap. Background: two obstacles, runner on the ground.
- `still-04-finding.png`: code lines 447 to 453 with the 4-space indent, no band. Caption "Each finding is", "Each" yellow. No overlap. Background: runner in the left lane.
- `still-04-finding-1.png`: band on 449 to 450. Matches "It holds the". Caption "It holds the", "the" yellow. No overlap. Background: a red obstacle is drawn over the lower half of the runner in the middle lane, like a collision (defect 4).
- `still-04-finding-2.png`: band on 451, 449 to 450 dim. Matches "The severity is". Caption "The severity is", "severity" yellow. No overlap. Background moved.
- `still-04-finding-3.png`: band on 452 to 453, the earlier bands dim. Matches "The rule name". Caption "The rule name", "name" yellow. No overlap. Background moved (runner in the left lane).
- `still-05-result.png`: only the `before` panel, red heading, 4 lines. Caption "A draft with", "draft" yellow. No overlap. Background: runner in the right lane, in the air.
- `still-05-result-1.png`: the `after` panel in, blue heading, `before` dim. Matches "After the change". Caption "After the change", "the" yellow. No overlap. Background: runner in the right lane on the ground, other obstacles.

Background frozen check: I compared the bottom halves of these pairs, one still after the other: `still-01-hook` and `still-02-flow`, `still-03-rules-3` and `still-05-result-1`, and `still-04-finding-1` and `still-04-finding-2`. Each pair differs in the runner lane and in the obstacles, so the loop moves. Captions show punctuation (`short,`, `HTML.`, `1.`); the rung says nothing about it (defect 9).

### Three transcript claims, spot-checked

Transcript `<cite>` elements, then the source lines:

```
ste_lint.py:1 "STE-80 lint for text written to ASD-STE100 Issue 9"
ste_lint.py:569 "yield &quot;E&quot;, &quot;LENGTH&quot;, f&quot;sentence has {n} words (max 25)&quot;"
ste_lint.py:613 "[f&quot;{errors} errors, {warnings} warnings&quot;]"

$ sed -n '1p;569p;613p' skills/ste/scripts/ste_lint.py
"""STE-80 lint for text written to ASD-STE100 Issue 9 (the `ste` skill).
        yield "E", "LENGTH", f"sentence has {n} words (max 25)"
    return "\n".join(lines + [f"{errors} errors, {warnings} warnings"]) + "\n"
```

All three snippets are verbatim (the `&quot;` is the HTML escape of `"`). The claims that they support: the file is an STE lint (scene 1), a sentence over 25 words is an error (scene 3), and the summary line `1 errors, 0 warnings` (scene 5).

### Duration, narrator and background

- `afinfo video.mp4`: `estimated duration: 51.669000 sec`.
- `build/timeline.json`: `totalFrames` 1550, so 1550 / 30 = 51.667 s. Difference 0.002 s. The `container` line says 51.67 s.
- Narrator: Kokoro `af_heart`. `audio/durations.json` has `"engine": "kokoro"` and `"fallback": null`. The transcript row is `<dt>Narrator</dt><dd>kokoro (af_heart)</dd>`. No output states the speed 1.2 (defect 6). The measured rate is 3.0 to 3.55 words each second (161 words in 48.6 s of WAV), below the 3.6 that the rung gives (defect 5).
- Background: `background: ok generated`. `build/timeline.json` has `"background": {"kind": "generated"}`, and the transcript row is `<dt>Background</dt><dd>generated</dd>`. The `Format` row is `brainrot (1080×1920)`.
- The `timeline` line gave 52.6 s (run 1) and 51.7 s (run 2), far below the 90 s limit. The longest scene is `flow`, 13.5 s, below the 30 s limit.

### Sync margins

```
$ python3 skills/explain/video/verify_sync.py <out>/build/rendered-audio.wav <out>/build/timeline.json
sync: hook speech 0.26-3.44 s (lead 0.20 s)
sync: flow speech 0.28-12.76 s (lead 0.20 s)
sync: rules speech 0.24-11.50 s (lead 0.20 s)
sync: finding speech 0.26-10.32 s (lead 0.20 s)
sync: result speech 0.24-9.76 s (lead 0.20 s)
exit 0
```

The length is `durationInFrames` / 30 from `build/timeline.json`. Tail silence = length − speech last. Lead offset = speech start − lead (0.20 s, the 6 lead frames).

| Scene | Length s | Speech last s | Tail silence s | Lead offset s |
|---|---|---|---|---|
| `hook` | 4.267 (128 frames) | 3.44 | 0.83 | 0.06 |
| `flow` | 13.533 (406 frames) | 12.76 | 0.77 | 0.08 |
| `rules` | 12.267 (368 frames) | 11.50 | 0.77 | 0.04 |
| `finding` | 11.067 (332 frames) | 10.32 | 0.75 | 0.06 |
| `result` | 10.533 (316 frames) | 9.76 | 0.77 | 0.04 |

The smallest tail silence is 0.75 s (`finding`, 0.747 s before rounding). It is more than twice the 0.3 s that the `sync` stage needs, although the brainrot tail is only 12 frames (0.4 s): the Kokoro WAV files end with 0.3 to 0.4 s of silence of their own (for example, `finding.kokoro.wav` is 10.435 s long and its speech ends 10.12 s in). Every lead offset is 0.08 s or less, inside the 0.25 s of the check.

### Render ratio

```
render (18.0 s, 0.35 render-min/video-min): ok
```

That is the final run. Run 1 printed `render (18.4 s, 0.35 render-min/video-min): ok`. Both are far below the advisory limit of 2.0. No clip was used: the background is the generated loop.

### Defect list

No `FAIL` occurred. Defect 1 caused the second render (with a false picture of my own, which I fixed in the same run). The others cost reading time, or they are faults in a still that the skill text did not prepare me for.

1. `rungs/brainrot.md` section 3, the limit table, and `rungs/video.md` section 2, Components: "`edges`: `{ from, to, label }`, `label` max 10". The brainrot table has no row for the edge label, so the explainer limit of 10 applies. A 6-character label (`Blocks`) on a horizontal edge was cut to `lock` behind the left node, in 5 of the 6 flow stills of run 1. Only about 3 characters fit in the gap between two nodes in a row. The `script` stage passed it. This cost one render and a second read of all 19 stills. Change: add a brainrot row "diagram edge `label` | 10 | 10 on a vertical edge, 3 on a horizontal edge", and add to the Components notes "A label on a horizontal edge has room for about 3 characters. Put a longer label on a vertical edge, or leave it out." Better: let the `script` stage fail a long label on a horizontal edge.
2. `templates/brainrot-script.json`: `"source": "scripts/verify.sh"`. The key table of `rungs/video.md` section 2 says that `provenance.source` is "The repo root, `model knowledge` or the URLs", and `rungs/sheet.md` section 4 says "for a file or a directory, write the repo root". The template, the example that a writer copies, gives a file path. I followed the table. Change the template value to the root (the same relative `skills/explain` as `provenance.root`, with the same note that the real value is absolute).
3. `rungs/video.md` section 3 step 2: "`still-NN-<scene>.png` shows scene NN at its start, after the lead." In a brainrot short, the hook cue is always the first words of the narration (`rungs/brainrot.md` section 3, Hook), and a scene whose first cue starts its narration has its cue frame at the lead end. The start still then shows that item at the first frame of its motion. In `still-01-hook.png` the subtitle is faint, and in `still-03-rules.png` bullet 1 is faint with its marker left of the margin. A careful reader can take this for a fault. Add: "When the first cue starts the narration, the start still shows that item as it comes in. That is not a fault. The cue still shows it in full."
4. `rungs/brainrot.md` section 4: "The runner is a block character that hops between three lanes." The rung does not describe the red obstacles, the road or the sun. In `still-04-finding-1.png` (run 2) a red obstacle is drawn over the lower half of the runner, in the same lane, which looks like a collision. The three brainrot faults do not cover this case, and `script.json` cannot change it (the loop has the fixed seed 7). I accepted it. Change: describe the loop ("a cyan block runs on a three-lane road; red blocks come toward it; it hops over them or changes lane"), and either state that a red block can pass in front of it, or make the loop keep the obstacles clear of the runner.
5. `rungs/brainrot.md` section 3, Length: "at speed 1.2, the narrator speaks approximately 3.6 words each second ... Six scenes of 45 words come near 80 s." The measured rate is 3.0 to 3.55 words each second (161 words in 48.6 s of WAV, 3.3 on average). My estimate from the rung was 47.7 s; the real length is 51.7 s. At 3.3 words each second, six scenes of 45 words come near 85 s, close to the 90 s limit. Change to "approximately 3.3 words each second" and "near 85 s".
6. `rungs/brainrot.md` section 5, the `narration` row: "The voice speaks at speed 1.2", and section 6 step 3: "Tell the user the narrator: Kokoro `af_heart` at speed 1.2". No output shows the speed: the stage line is `narration (kokoro): ok`, the transcript row is `kokoro (af_heart)`, and `audio/durations.json` has no speed. I told the user a value that I could not check. Change: print the speed in the stage line or the Narrator row (for example `kokoro (af_heart, 1.2)`).
7. `rungs/video.md` section 2, Rules for each scene: "The prose lint also reads each `title`, the subtitle, the bullets, the headings and lines of `before-after`". It does not say how to show text that breaks STE, which a short about the lint itself needs. A `before` line `Utilize the tool.` fails the `script` stage. I found the way out in the subject file, not in the skill text: quoted text is one word and the lint does not check it, so `Input: "Utilize the tool."` passes. In the narration, backticks do the same (`` `utilize` ``, spoken as a word). Add: "To show text that breaks STE, put it in double quotes in a prop, or in backticks in the narration. The lint does not check quoted text or code."
8. `rungs/brainrot.md` section 3, the limit table: it has no row for the heading of a scene that is not a `title` scene. The skill text alone does not tell the writer that a long heading is cut. I kept every heading at 27 characters or fewer only because the stress section above had shown cuts at about 30 to 34 characters. Add a row "scene heading | — | 30".
9. `rungs/brainrot.md` section 3, Captions: "Backticks do not show in a caption." The rung says nothing about other punctuation. The captions show commas and full stops (`short,`, `HTML.`, `use,`), and one caption is only `1.`. A reader checks "matches the narration" and can doubt a caption that holds a lone `1.`. Add: "A caption keeps the punctuation of the narration."
10. `rungs/brainrot.md` section 2: the table of `video.md` sections does not say that `video.md` section 2 step 3 sends the reader to `rungs/sheet.md` section 4 for the provenance. I followed the second-level reference, and it worked. No cost, but the table is the brainrot reader's full reading list. Add a row "`rungs/sheet.md` section 4 | The provenance recipe."

### What worked

- The contract, the subject rules and the rung line form: one try. The slug rule gave `ste-lint` from `ste_lint.py`, as convention 5 says.
- The limit table and the `awk` command for the code columns: no limit error and no `script` failure on the first draft.
- The cue rule: all 14 cues passed on the first draft, and every cue still showed its item after its cue.
- The stage table: the output matched it line for line, ten `ok` lines in order, with the generated background named on its own line.
- The caption rules: every caption was 1 to 3 words on one line, with the spoken word in yellow, on the seam and clear of the panel content.
- The background section: the empty folder gave `background: ok generated` with no extra step, and the `Background` and `Format` rows were in the transcript.
- The three brainrot still checks were quick to apply. The instruction to compare two bottom halves made the frozen-background check concrete.
- The WAV reuse: run 2 synthesized only the changed scene and took 37 s.
- The word budget: 161 words in 5 scenes gave 51.7 s, far below the 90 s limit.
