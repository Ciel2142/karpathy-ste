# Explain video rung: live run on ImportController.java

Date: 2026-10-04. Runner: a fresh Claude (Opus 5.5). I read only the skill text:
`~/.claude/skills/explain/SKILL.md`, `rungs/video.md`, `~/.claude/skills/ste/SKILL.md`,
`rungs/sheet.md` section 4 and `templates/video-script.json`. I did not read the plan, the
tests or the pipeline source. Nothing blocked me, so I never had to open a script.

## Request and rung line

```
/explain ~/work/inavcalculator/src/main/java/ru/aton/esb/microservices/inavcalculator/web/ImportController.java --as video
```

Printed before the build:

```
Rung: video (forced) — --as video; the content fits: a signed import moves through checks to a saved fund and a signed reply — subject: ~/work/inavcalculator/src/main/java/ru/aton/esb/microservices/inavcalculator/web/ImportController.java (file)
```

## Pre-declared expectation (written before the build)

Copied from the controller brief:

- Five scenes in this order: `title`; `bullets-appear` (the two endpoints and the guards);
  `diagram-with-highlight-walk` (request, verify signature, parse JSON, save fund, sign response;
  5 nodes, each walk step along an edge); `code-with-line-highlights` on lines 95 to 102 (the save
  path); `before-after` (unsigned and signed import).
- Stage line `narration (kokoro): ok`.

My plan after the read of the file: the same five scenes. Lines 93 to 102 are the only long run of
the save method with all lines at 72 columns or less (I measured it with `awk`).

## Expectation compared with the build

Match on every point.

| Scene id | Component | What it shows |
|---|---|---|
| `intro` | `title` | "How ImportController imports a fund" / "Two endpoints, one signed path" |
| `endpoints` | `bullets-appear` | 4 bullets: plain endpoint, signed endpoint, guards (size, counter-party, Base64), reply shape |
| `flow` | `diagram-with-highlight-walk` | 5 nodes `a1 b1 c1 c2 c3`: Request, Signature, Parse JSON, Save fund, Sign reply; 4 edges; 5 walk steps |
| `save` | `code-with-line-highlights` | lines 95 to 102; bands 96, 98, 100, 101 to 102 |
| `compare` | `before-after` | unsigned `POST /importer` against signed `POST /importer/signed` |

One difference in words only: the node is labelled "Signature", not "Verify signature". I avoided
the word "verify" in all props because the STE substitution table bans it (see defect 6).

- Output directory: `~/karpathy/out/2026-10-04-011011-video-work-inavcalculator-src-main-java-ru-at/`
- Provenance: root `/Users/valukin/work/inavcalculator`, commit `b3711d9`, dirty `dirty`
  (`?? .claude/`, `?? .codegraph/`), the file is tracked (`git ls-files --error-unmatch` exit 0).
- Script iterations: 2 (the first draft, then one line fixed after the stills).
- `render.sh` runs: 2, both with nine `ok` lines, no `FAIL`.

## render.sh run 1 (first draft, cold models)

Full stdout. The curl progress meter wrote 56 and 21 carriage-return updates. I kept the header
and the last update of each meter and elided the rest (marked `[...]`).

```
script: ok (5 scenes)
  workspace: download kokoro-v1.0.onnx (325 MB)
    % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                   Dload  Upload   Total   Spent    Left  Speed
[... 55 progress updates ...]
100  310M  100  310M    0     0  5997k      0  0:00:53  0:00:53 --:--:-- 5898k
  workspace: download voices-v1.0.bin (28 MB)
    % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                   Dload  Upload   Total   Spent    Left  Speed
[... 20 progress updates ...]
100 26.9M  100 26.9M    0     0  1527k      0  0:00:18  0:00:18 --:--:-- 2434k
workspace: ok /Users/valukin/karpathy/video-workspace
  narration: intro kokoro 9.673 s (synthesized)
  narration: endpoints kokoro 17.140 s (synthesized)
  narration: flow kokoro 14.900 s (synthesized)
  narration: save kokoro 15.189 s (synthesized)
  narration: compare kokoro 13.633 s (synthesized)
narration (kokoro): ok
timeline (5 scenes, 79.1 s): ok
render (23.7 s, 0.30 render-min/video-min): ok
container: ok (79.10 s)
sync: ok
stills (20): ok /Users/valukin/karpathy/out/2026-10-04-011011-video-work-inavcalculator-src-main-java-ru-at/review
transcript: ok
```

No `FAIL`. The stills showed one false picture: the `after` line "Signs each reply, also errors"
drops the condition of `ImportController.java:116` (`if (cryptoProvider.isPresent()) {`).
Change: that line became "With a provider, signs every reply". No narration changed.

## render.sh run 2 (final)

```
script: ok (5 scenes)
workspace: ok /Users/valukin/karpathy/video-workspace
  narration: intro kokoro 9.673 s (reused)
  narration: endpoints kokoro 17.140 s (reused)
  narration: flow kokoro 14.900 s (reused)
  narration: save kokoro 15.189 s (reused)
  narration: compare kokoro 13.633 s (reused)
narration (kokoro): ok
timeline (5 scenes, 79.1 s): ok
render (23.0 s, 0.29 render-min/video-min): ok
container: ok (79.10 s)
sync: ok
stills (20): ok /Users/valukin/karpathy/out/2026-10-04-011011-video-work-inavcalculator-src-main-java-ru-at/review
transcript: ok
exit 0
```

## Wall time

Stage lines that print a time: `timeline` 79.1 s (video length), `render` 23.7 s (run 1) and
23.0 s (run 2), `container` 79.10 s. Wall clock from timestamps on each output line of run 1:

| Stage | Run 1 | Note |
|---|---|---|
| script | 1 s | |
| workspace | 72 s | model downloads 53 s + 18 s; `npm ci` and Chrome were already present |
| narration | 20 s | uv resolution and 5 Kokoro syntheses; the rung estimate of approximately 30 s for uv alone was high here |
| timeline | 1 s | |
| render | 23 s | |
| container | 2 s | |
| sync | below 1 s | |
| stills | 10 s | |
| transcript | below 1 s | |
| total | 2 min 9 s | run 2: 36 s |

## verify.sh on the final index.html

The rung says "Do not run `verify.sh` again". The brief asked for this output, so I ran it once:

```
$ ~/.claude/skills/explain/scripts/verify.sh <out>/index.html
self-contained: ok
citations: ok
prose: ok
exit 0
```

## Stills read (final state)

Each still matched its cue. Scene 5 stills are from run 2; the other scenes did not change.

- `still-01-intro.png`: title only, rule below, no subtitle yet. Correct (before the cue).
- `still-01-intro-1.png`: subtitle "Two endpoints, one signed path" is in. Matches cue "This video explains".
- `still-02-endpoints.png`: heading only, no bullets. Correct.
- `still-02-endpoints-1.png`: bullet 1 "POST /importer: a plain JSON fund". Matches "The first endpoint".
- `still-02-endpoints-2.png`: bullets 1 and 2. Matches "The second endpoint".
- `still-02-endpoints-3.png`: bullets 1 to 3, "Guards: size, counter-party, Base64". Matches "On this endpoint".
- `still-02-endpoints-4.png`: all 4 bullets. Matches "Each reply holds".
- `still-03-flow.png`: 5 nodes, 4 labelled edges, no highlight. Correct.
- `still-03-flow-1.png`: Request highlighted. Matches "A request brings".
- `still-03-flow-2.png`: token at Signature, Signature highlighted, Request dim. Matches "The signature service". The label "bytes" is not visible in this frame (see defect 9).
- `still-03-flow-3.png`: token at Parse JSON. Matches "Jackson reads". Label "valid" not visible, "bytes" back.
- `still-03-flow-4.png`: token at Save fund. Matches "The fund manager". Label "fund" not visible.
- `still-03-flow-5.png`: token at Sign reply. Matches "The crypto provider". Label "status" not visible.
- `still-04-save.png`: lines 95 to 102, no band. Correct. The 8-space method indent is kept.
- `still-04-save-1.png`: band on 96. Matches "First the mapper".
- `still-04-save-2.png`: band on 98, 96 dim. Matches "Then the fund manager".
- `still-04-save-3.png`: band on 100, 96 and 98 dim. Matches "On success".
- `still-04-save-4.png`: band on 101 to 102. Matches "If the manager".
- `still-05-compare.png`: only the `before` column, heading in red. Correct (before the cue).
- `still-05-compare-1.png`: `after` column in blue, `before` dim; the last line reads "With a provider, signs every reply". Matches "The signed endpoint".

No clipped title, no overlap.

## Three transcript claims, spot-checked

Transcript `<cite>` elements, then the source lines (`F` is the subject path, relative to the root):

```
ImportController.java:59 "if (signatureB64.length() &gt; 4 * 1024 * 1024) {"
ImportController.java:98 "fundManager.putMutualFund(mutualFund);"
ImportController.java:116 "if (cryptoProvider.isPresent()) {"

$ cd ~/work/inavcalculator && sed -n '59p;98p;116p' $F
        if (signatureB64.length() > 4 * 1024 * 1024) {
            fundManager.putMutualFund(mutualFund);
        if (cryptoProvider.isPresent()) {
```

All three snippets are verbatim. The claims that they support: the size guard (scene 2), the save
call (scenes 3 and 4), and the signature only with a provider (scene 5).

## Duration and narrator

- `afinfo video.mp4`: `estimated duration: 79.104000 sec`.
- `build/timeline.json`: `totalFrames` 2373, so 2373 / 30 = 79.100 s. Difference 0.004 s.
- Narrator: Kokoro `af_heart` (default). `audio/durations.json` has `"fallback": null`.
- Narrator row in `index.html`: `<dt>Narrator</dt><dd>kokoro</dd>`.

## Defect list (for the fold-back)

No `FAIL` occurred, so no defect below cost a render. Each one cost reading time or carries a risk.

1. `SKILL.md` gives the rung file as a relative path. Build procedure step 2: "Read
   `rungs/<rung>.md` of the chosen rung only, and each section that it names." The reader must
   guess the base directory. Change to "Read `~/.claude/skills/explain/rungs/<rung>.md` ...".
   The same applies to the "Rung files" list and to `rungs/sheet.md section 4` in `video.md` §2
   step 3.
2. Conflict about re-runs. `SKILL.md` convention 5: "Never overwrite a directory. A re-run makes a
   new directory." `video.md` §3 step 5: "Fix each fault ... in `script.json`. Run `render.sh`
   again." The fix loop re-renders in the same directory and overwrites `video.mp4`, the stills and
   `index.html`. I followed the rung. Change convention 5 to "A new `/explain` run makes a new
   directory. The fix loop of a rung stays in its directory." and add "in the same output
   directory" to `video.md` §3 step 5.
3. The slug rule loses the file name for a deep path. Convention 5 gives
   `work-inavcalculator-src-main-java-ru-at` for this subject: the 40-character cut stops before
   `ImportController`. Change "Make the `<slug>` from the subject in four steps." to "Make the
   `<slug>` from the subject in four steps. For a path subject, use its basename (for a file,
   without the extension)."
4. Rung gap that the brief predicted: `video.md` §2 Components, "Each line has at most 72 columns,
   and a tab counts as 4 columns." It does not say that the leading indent counts and stays on the
   screen (`still-04-save.png` keeps 8 spaces). In this Java file, 29 of the lines from 34 to 135
   are longer than 72 columns; only a few ranges fit. I measured before the first run, so no
   `FAIL`. Add: "The leading indent counts, and the component shows it. Measure the range first:
   `awk 'NR>=A && NR<=B {gsub(/\t/,"    "); print NR, length}' FILE`. If no range of 14 short
   lines shows the point, show it in a diagram."
5. The colour of `before-after` is not in the rung. Motion cell: "At the cue, the `after` column
   comes in. The `before` column becomes dim." The `before` heading renders red and the `after`
   heading blue (`still-05-compare.png`). Red says "wrong". That can give a false picture when the
   two sides are only different, not worse and better. Add to the Motion cell: "The `before`
   heading is red and the `after` heading is blue: use the pair for worse and better."
6. The rung does not say which props the prose lint reads. In `index.html`, the bullets and the
   `before-after` lines are linted, but the diagram node list has `data-ste="skip"`. A probe:
   `ste_lint.py` on "The node label is Verify signature." gives `E WORD "Verify" is not
   approved; use MAKE SURE`. A natural bullet such as "Verify the signature" thus fails the
   `script` or `transcript` stage, but the same word in a node label passes. Add to §2 "Rules for
   each scene": "The prose lint also reads the bullets, the headings and the lines of
   `before-after`. Write them in STE. The diagram labels and the code are not linted."
7. Unclear tool output: the curl progress meter of the `workspace` stage. The rung says the stage
   prints the cost "indented". The meter then writes 77 carriage-return updates, and some lines
   start at column 0 (`100  310M  100  310M ...`), where only stage lines belong. In a captured
   log this is approximately 7 KB of noise. Suggest `curl -sS` (or `--progress-bar` to stderr)
   and one indented "done" line.
8. Unclear tool output: `verify.sh` printed three lines (`self-contained`, `citations`, `prose`).
   The template script, which describes `verify.sh`, says "The script runs four checks", the
   second one "loads the page in Chrome". Either the render check prints nothing on success, or
   the template is out of date. The template is the example that a writer copies: make it agree
   with the real output.
9. The diagram motion is not fully described. In each walk still (`still-03-flow-2` to `-5`), the
   label of the edge that the token just used is not visible, and it comes back at the next
   step. The Motion cell says only "A token moves to it along an edge." A reader of the stills can
   take the absent label for a fault. Add: "The label of the active edge hides while the token is
   on it."
10. Small ambiguity: `subject.text` in §2 does not say if the path is as typed (`~/...`), absolute
    or relative to the root. I wrote it as typed. Add "the subject as the user typed it".
11. Small ambiguity: `SKILL.md` subject resolution rule 1, "If a `.codegraph/` index exists, use
    CodeGraph", follows the directory sentence. This repo has `.codegraph/`. I read the one file
    in full and did not use CodeGraph. Say if the CodeGraph sentence applies to a file subject.
12. The Narrator row says `kokoro` without the voice. `video.md` §4 step 3 says "Tell the user the
    narrator: Kokoro `af_heart`". The transcript does not record the voice, so a later reader
    cannot see it. Either show `kokoro af_heart` in the row or accept the gap in the rung text.

## What worked without friction

- The contract and the rung line form: clear, one try.
- The component table: every limit was exact. No prop error on the first draft.
- The cue rule and its example table: all 15 cues passed on the first draft, and every still
  landed after its cue.
- The stage table: the output matched it line for line, in order.
- The provenance recipe (`sheet.md` §4): four commands, no doubt.
- The cost lines and the cold start: models and uv came in by themselves, 2 min 9 s in total.
- The WAV reuse: the fix run took 36 s and reused all five clips.
- The still names agree with §3: 5 scene stills + 15 cue stills = 20.
- The word budget: 5 scenes and 175 words gave 79.1 s, far below the 150 s limit.
