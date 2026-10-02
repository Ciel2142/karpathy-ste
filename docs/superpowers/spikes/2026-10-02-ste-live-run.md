# STE-80 live run: profile vs baseline

Verdict: pass, with a weak test. The profiled answer has 0 errors, as the spec says. The baseline
has 0 errors too, so on this subject and model the error rules (`LENGTH`, `CONTRACTION`, `WORD`) did
not discriminate between the two answers. The profile shows in the warnings (4 against 0; 3 of the 4
mark a construct to change) and in the protocol (the profiled subagent linted its own draft, per the
controller, the main session, so it iterated against the same lint that scores it).

- **Date:** 2026-10-02. **Model:** claude-sonnet in both runs (version string not recorded).
  **Lint version:** `5dfed3f` (`git log -1 --format=%h -- skills/ste/scripts/ste_lint.py`).
  **Profile:** `skills/ste/SKILL.md` at `54d81c5`.
- **Subject:** how `skills/ste/scripts/ste_lint.py` decides where a sentence ends and how it counts words,
  for someone who will edit that code. Same question for both runs: read the file first, write 300-600 words.
- **Difference:** the profiled run adds, before the question: "First read
  `/Users/valukin/.claude/skills/ste/SKILL.md` and follow it for this answer, including its usage
  protocol (run the lint it names on your draft and fix every error before you write the final file)."
  The baseline run does not mention STE. One run per condition, so the counts show a difference, not a cause.

## Results

| Run | Sentences | Errors | Warnings | Exit code |
| --- | --- | --- | --- | --- |
| Profile, Appendix A: 582 words (wc -w) | 42 | 0 | 0 | 0 |
| Baseline, Appendix B: 570 words (wc -w) | 39 | 0 | 4 | 0 |

Re-run at `8a9d241` (the lint after the wave `ste` fixes): profile 0 errors, 0 warnings; baseline
0 errors, 5 warnings. The new warning is `23:46  W PASSIVE  possible passive: "is split"`, because
`split` joined the irregular participles. Sentence counts and the statistics below are unchanged.

To reproduce, save the fenced text of each appendix as `profile.md` and `baseline.md`, then run from the
repository root (both lint runs exit 0). "Sentences" are depth-0 sentences from `tokenize`; text in parentheses is not counted.

```text
$ python3 -B skills/ste/scripts/ste_lint.py profile.md
0 errors, 0 warnings
$ python3 -B skills/ste/scripts/ste_lint.py baseline.md
13:4  W PASSIVE  possible passive: "is matched"
14:4  W LENGTH-PROC  procedure step has 21 words (keep to 20, Rule 5.1)
26:3  W PASSIVE  possible passive: "is dropped"
33:3  W PROGRESSIVE  possible progressive: "is warning"
0 errors, 4 warnings
```

```bash
python3 -B - profile.md baseline.md <<'EOF'
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("ste_lint", "skills/ste/scripts/ste_lint.py")
ste = importlib.util.module_from_spec(spec); spec.loader.exec_module(ste)
for path in sys.argv[1:]:
    text = open(path, encoding="utf-8-sig").read()
    n = [s.words for b in ste.tokenize(text) for s in b.sentences if s.depth == 0]
    print(f"{pathlib.Path(path).name}: sentences={len(n)} mean={sum(n) / len(n):.1f} max={max(n)} over20={sum(w > 20 for w in n)}")
EOF
```
```text
profile.md: sentences=42 mean=12.1 max=23 over20=2
baseline.md: sentences=39 mean=12.1 max=25 over20=3
```

## Warnings

- **Profile run:** none (0 warnings), so no judgement applies.
- **Baseline run**, one judgement for each warning:
  - `13:4` PASSIVE "is matched": would change; name the agent (`_sentences`) and use the active voice (3.6).
  - `14:4` LENGTH-PROC, 21 words: approved construct, keep; the item describes code, so the 25-word cap (6.3) applies.
  - `26:3` PASSIVE "is dropped": would change; name the agent (the code) and use the active voice (3.6).
  - `33:3` PROGRESSIVE "is warning": would change; `warning` is a noun (a false alarm), but the sentence omits articles (4.5).
- **Baseline, outside code spans and quotes:** WORD-table words: none. Contractions: none. The scan (inflected forms
  included, which `WORD` does not match) finds only `terminator` and `allowlisted`, which are not table words, and
  the possessives `block's` and `quote's`. `don't` occurs once, in a code span. The profile scan finds only `terminator(s)`.

## Comparison (written in STE-80, linted)

Both answers have 0 errors, so `LENGTH`, `CONTRACTION` and `WORD` did not separate the two runs on
this subject and model. The baseline has 4 warnings and the profiled answer has none, but only 3 of
the 4 warnings mark a construct to change. Two of these 3 are passives, and the third lacks articles.
The controller reports that the profiled subagent ran the lint on its own draft, as the usage
protocol says. Sentence length changed little: both means are 12.1 words, and the longest sentence
is 2 words shorter in the profiled answer. Neither answer has a contraction or a substitution-table
word outside code spans and quotes.

Lint of this paragraph: `0 errors, 0 warnings`.

## Appendix A: profile answer (verbatim)

```markdown
# How `ste_lint.py` decides where a sentence ends and counts words

In `ste_lint.py`, `tokenize` reads Markdown or plain text, and `html_to_blocks` reads HTML. Both cut the input into blocks (a paragraph or a list item). `_sentences` finds the sentence boundaries in each block, and `_sentence` counts the words of each sentence. Then `lint` applies the rules.

## Where a sentence ends

- A block stops at an empty line, a heading, a table row, fenced code or a new list item. A sentence never crosses a block. A line break inside a block is only a space.
- The pattern `_BOUNDARY` finds each sentence boundary. It matches one or more terminators (`.`, `!` or `?`), then any closers (`)`, `"`, `”`, `*`, `_`), then whitespace or no more text. The pattern does not look for a capital letter.
- A span is a part of the text that the code treats as one unit. `_spans` finds six kinds: inline code, a URL, a link destination, parentheses, quotes and a number with a unit. `_boundary_view` makes a view of the text and replaces each span with `x` characters. `_BOUNDARY` reads the view, so a terminator inside a span does not end a sentence.
- In the view, parentheses and quotes keep a final terminator, so `(Stop.)` and `"OFF."` end a sentence.
- `_is_abbreviation` cancels a boundary when the terminator is a single `.` that ends an entry of the list `ABBREVIATIONS`. The test is case-sensitive.
- The text after the last terminator is a sentence too, so a list item needs no final period.

## How the code counts words

- `_sentence` replaces each span with `MASK` (the `§` character) to make the `checkable` text. A URL becomes empty text and adds no word.
- `_count_words` splits `checkable` on whitespace into tokens. A token counts as one word when it has a letter, a digit or `§`. A hyphenated word, an abbreviation or an identifier has no whitespace in it, so it is one token (rules 8.6 and 8.7).
- Inline code, text in parentheses, quoted text and a number with a unit from the list `UNITS` each count as one word (rules 8.5 and 8.6). A link destination after `]` joins the token before it and adds no word.
- `_sentence` also calls `_sentences` on the text in parentheses, one level deeper (`depth + 1`). The rules then apply to that text as a sentence of its own. No rule applies to quoted text or inline code.
- `lint` reads `Sentence.words`, the word total of a sentence. More than 25 words is the error `LENGTH`.

## Notes for the editor

- Keep the view the same length as the text. The code uses one index for the text, the view and the list of line and column positions.
- Three constants repeat the closers: `_BOUNDARY`, `_TAIL` and `_CLOSERS`. Change all three together.
- A new kind of span needs new code in `_spans` only. Other code treats it like inline code.
- Tests in `skills/ste/tests/test_ste_lint.py` compare `ABBREVIATIONS` and `UNITS` with exact lists. Change the list and its test together.

## Known limits

- An abbreviation outside `ABBREVIATIONS`, such as `approx.`, ends the sentence.
- A sentence that stops with `etc.` joins the next sentence.
- Text in parentheses or quotes that stops with a terminator ends the sentence, even in the middle: `The "stop." command` splits in two.
- `5 in` counts as one word, because `in` is a unit (the inch).
```

## Appendix B: baseline answer (verbatim)

```markdown
# How `ste_lint.py` ends sentences and counts words

`tokenize` (Markdown or plain text) and `html_to_blocks` (HTML) cut the input into blocks and hand each run of text to `_sentences`, which splits it and counts the words. It returns `Sentence` objects (`text`, `line`, `col`, `words`, `checkable`, `depth`); `lint` works from those and each block's `kind`.

## Where a sentence ends

**Block limits come first.** A sentence never crosses a block boundary. In Markdown, a blank line, heading, table row, code fence or new list item ends the current run of text. In HTML, any non-inline tag except `br` does. Inside a run, `_join` (Markdown) and `_collapse` (HTML) turn line breaks into spaces and keep a `pos` list mapping each character to its (line, col).

**Then `_sentences(s, pos, depth)` takes four steps:**

1. `_spans` finds *one-word tokens*: inline code, URLs, Markdown link destinations, parentheticals (outermost matched pair), `"…"` or `“…”` quotes (opened only at a token start) and number-plus-unit. An unclosed `(` or quote makes no token.
2. `_boundary_view` copies the text with each token overwritten by `x`, so punctuation inside a token never ends a sentence. One exception: a parenthesis or quote keeps its brackets and any terminator run just before the closing mark.
3. `_BOUNDARY` is matched against that view: `[.!?]+`, optional closers `)"”*_`, then whitespace or end of text. It ignores capitalisation, so `Stop. then go.` splits and `Stop.Then` does not.
4. `_is_abbreviation` vetoes a match that is a lone `.` after an allowlisted token: `e.g.`, `i.e.`, `etc.`, `vs.`, `Mr.`, `Dr.`, `No.` (case-sensitive, plus `E.g.`, `I.e.`, `Etc.`). So `…, etc. Then stop.` stays one sentence, while `Fig.` and `Step 1.` split.

Known quirks: a parenthetical or quote that ends in a terminator ends the sentence even mid-sentence (`He said "stop." and left.` gives two). Single quotes are not tokens.

## How words are counted

`_sentence` builds `checkable`: every token becomes `MASK` (`§`), except URLs, which vanish. `_count_words` splits that string on whitespace and counts each token that holds an alphanumeric character or `§`.

- `built-in`, `and/or`, `don't`, `A320` and `e.g.` count once. A lone `—`, `-`, `…` or `**` counts zero. (`.strip("*_")` there is a no-op: `*` and `_` are not alphanumeric.)
- A parenthetical is one word in its parent. Its inside is split again with `depth + 1` and counted on its own, recursively.
- A quote or code span is one word, and a quote's inside is never linted. A URL is zero words. A link destination glues to `]` and adds nothing.
- `5 mm` is one word (Rule 8.6) through `UNITS`. Ambiguous units (`in`, `A`, `s`, `h`) undercount: `There are 3 in the box.` counts 5, not 6.
- A zero-word sentence is dropped, so a bare URL or `—` yields nothing.

## Editing notes

- Keep the text, the boundary view and `pos` the same length; slicing shares indexes.
- `_spans` must return sorted, non-overlapping spans, because `_sentence` walks them in order.
- `_words`, used by the verb rules, re-tokenises `checkable`; keep it in step with `_count_words`.
- `_check` reads `words`: over 25 is error `LENGTH`; 21 to 25 in an ordered-list item is warning `LENGTH-PROC`. `PARAGRAPH` ignores parenthetical sentences.
- Exact-match tests pin `ABBREVIATIONS` and `UNITS`, so change the tests with the tuples. Add a capitalised form to `_ABBREVIATIONS` for any abbreviation that can start a sentence.
- Tests: `SentenceBoundaryTest`, `OneWordTokenTest` and `CountingTest` in `skills/ste/tests/test_ste_lint.py`; run `python3 -m unittest discover -s skills/ste/tests`.
```
