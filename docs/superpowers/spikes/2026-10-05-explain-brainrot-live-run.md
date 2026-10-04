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
