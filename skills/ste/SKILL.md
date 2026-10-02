---
name: ste
description: Use when the user invokes /ste — rewrite the given text, or answer the given request, in STE-80 (Simplified Technical English, ASD-STE100 Issue 9 profile). A bare /ste rewrites the previous answer.
disable-model-invocation: true
argument-hint: "[text or request]"
---

# STE-80 profile

STE-80 is a fixed profile of ASD-STE100 Simplified Technical English (STE), Issue 9: the
kept structural and verb rules, a substitution table, and a short relaxed list (the 20%).
Apply exactly this profile, so that the meaning of "80% STE" does not drift between sessions.

## Contract

- `/ste <text>`: rewrite the text in STE-80. Keep every fact and every technical name.
- `/ste <request>`: answer the request in STE-80. A question or a task addressed to you is
  a request; any other argument is text to rewrite. If you cannot tell, rewrite.
- Bare `/ste`: rewrite your previous answer in STE-80.
- The profile applies to that one answer only. It does not persist for the session.
- Give one answer. Do not offer alternatives.

## Source and provenance

- Standard: ASD-STE100 Simplified Technical English, Issue 9, dated 2025-01-15.
- PDF: `https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf`, 434 pages,
  AES-encrypted with an empty password.
- sha256: `d1f4ea9e7cd6e46b47aa9057209f99e78c0e9cfc4e27a5b07895b05c1a166431`

Fetch, verify, and extract. The extraction writes a `=====PAGE N=====` line before each
page; with pypdf 6.19.0, `wc -l /tmp/ste9.txt` gives 27253.

```bash
curl -fsSL -o /tmp/ste9.pdf https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf
shasum -a 256 /tmp/ste9.pdf
uv run --with pypdf --with cryptography python3 -c 'import pathlib, pypdf; r = pypdf.PdfReader("/tmp/ste9.pdf"); r.decrypt(""); pathlib.Path("/tmp/ste9.txt").write_text("".join(f"\n=====PAGE {i}=====\n{p.extract_text()}" for i, p in enumerate(r.pages, 1)), encoding="utf-8")'
```

Citation convention: a rule cites its Issue 9 rule number, for example (5.1). A dictionary
entry cites the printed page label of its page, for example `2-1-E7`, never a line number of
the extraction: line numbers change with the extractor. To find a label, go back from the
entry line to the nearest `=====PAGE N=====` line; the page header in the next five lines
contains `Page 2-1-<letter><number>`.

## Kept rules

The number in parentheses is the Issue 9 rule.

### Sentences and paragraphs

- Procedural sentence (an instruction): at most 20 words (5.1).
- Descriptive sentence: at most 25 words (6.3).
- Word count: a number (also with its unit), an abbreviation, and quoted text each count as
  one word (8.6). A hyphenated word counts as one word (8.7). Text in parentheses counts as
  one word (8.5).
- Paragraph: at most 6 sentences (6.6) and one topic, with the topic sentence first (6.5).
- One instruction per sentence. The only exception is two or more actions that occur at
  the same time (5.2).
- Use a vertical list for complex text (4.3).
- Keep the articles (`the`, `a`, `an`) and the demonstratives (`this`, `these`) (4.5).
- Do not omit words, and do not use contractions (4.2).

### Procedures and safety text

- Write instructions in the imperative (5.3).
- Safety text: start with `WARNING:` or `CAUTION:` (7.1), then a clear and simple command
  or condition (7.2), then the risk or the possible result in a second sentence (7.3).

### Verbs and voice

- Allowed verb forms (3.2): infinitive, imperative, simple present, simple past, simple
  future, and the past participle used as an adjective (3.3).
- Not allowed:
  - `-ing` verb forms, except as a technical noun or as a modifier in a technical noun,
    such as "landing gear" (3.5).
  - Complex constructions with auxiliary verbs, which excludes the perfect tenses
    ("has adjusted") (3.4).
  - The passive voice in procedures. In descriptive text, use the passive only when the
    agent is unknown (3.6).
- Use the active voice, with the agent named (3.6).
- `HAVE` is an approved main verb, "to possess as a part or quality" (`2-1-H3`). Only
  `have` as an auxiliary is excluded (3.4).

### Words

- One word, one meaning (1.3), one part of speech (1.2).
- The same word for the same thing every time. No elegant variation (1.11).
- Multi-word nouns: at most 3 words (2.1). Break a longer one with prepositions such as
  `of`, `on`, `in`, `for` (2.1). A longer technical name that cannot be divided stays
  whole (2.2).
- Replace every word of the substitution table, in any of its forms (`provides`,
  `allowed`), with its approved alternative.

### Correct STE that looks wrong

Do not "correct" these:

- "The pump has fixed blades." — "has" is `HAVE` as a main verb, not an auxiliary (3.4).
  `fix (v)` is unapproved, so "fixed blades" is correct only as a technical noun (1.6).
- "landing gear vibration" — "landing" is an `-ing` modifier in a technical noun (3.5),
  `VIBRATION (n)` is approved (`2-1-V3`), and the noun has 3 words (2.1).
- "The valve is closed." — "closed" is the past participle of the approved `CLOSE (v)`
  (`2-1-C10`) used as an adjective: it shows a condition and is not the passive voice
  (3.3).

## Relaxed (the 20%)

- The approved dictionary of about 900 general words is not enforced as a hard limit. The
  specification itself allows company-defined technical nouns and technical verbs (1.5,
  1.12); this profile uses that door generously.
- Code identifiers, commands, file paths, product names, and protocol terms stay verbatim
  in backticks and are defined on first use.
- Spelling conventions and punctuation details of the specification are not enforced.

## Substitution table

Every word in the left column is unapproved in all its dictionary senses (all parts of
speech). Replace it with the approved alternative. `Page` is the Issue 9 page label.

| Unapproved | Approved | Page |
| --- | --- | --- |
| additional | MORE | 2-1-A8 |
| allow | LET | 2-1-A12 |
| appropriate | APPLICABLE | 2-1-A17 |
| attempt | TRY | 2-1-A22 |
| commence | START | 2-1-C12 |
| due to | BECAUSE OF | 2-1-D19 |
| enough | SUFFICIENT | 2-1-E7 |
| ensure | MAKE SURE | 2-1-E7 |
| however | BUT | 2-1-H6 |
| in the event of | IF | 2-1-E10 |
| indicate | SHOW | 2-1-I8 |
| modify | CHANGE | 2-1-M8 |
| obtain | GET | 2-1-O1 |
| perform | DO | 2-1-P3 |
| prior to | BEFORE | 2-1-P12 |
| proper | CORRECT | 2-1-P15 |
| provide | GIVE | 2-1-P16 |
| reduce | DECREASE | 2-1-R6 |
| replenish | FILL | 2-1-R11 |
| require | NECESSARY | 2-1-R12 |
| simultaneously | AT THE SAME TIME | 2-1-S12 |
| terminate | STOP | 2-1-T3 |
| therefore | THUS | 2-1-T4 |
| utilize | USE | 2-1-U8 |
| verify | MAKE SURE | 2-1-V2 |
| via | THROUGH | 2-1-V2 |
| whether | IF | 2-1-W4 |

`in the event of` is listed under the entry `event (n)`, whose non-STE example is "In the
event of a sudden dropping of pressure". Where an entry gives more than one alternative,
the table names the general one.

Dropped candidates (not in the table):

- `in order to`: not an entry. Issue 9 has only `order (n)` → SEQUENCE and `order (v)` →
  TELL (`2-1-O5`).
- `about`: `ABOUT (prep)` is approved as "concerned with" (`2-1-A2`). For a quantity, use
  APPROXIMATELY (`2-1-A18`); for a rotation, AROUND. Meaning-dependent, so guidance only
  and out of the lint.
- `close`: `close (adj)` → NEAR is unapproved, but `CLOSE (v)` is approved (`2-1-C10`).
- `subsequent`: approved, `SUBSEQUENT (adj)` (`2-1-S26`).
- `adjacent`: approved, `ADJACENT (adj)` (`2-1-A8`).
- `numerous`: not in the dictionary.
- `demonstrate`: not in the dictionary.
- `regarding`: not in the dictionary.

## Usage protocol

1. Draft the answer under this profile.
2. For any text of more than five sentences, or any text that will land in an artifact or
   a document: write the draft to a temporary file, run
   `python3 ~/.claude/skills/ste/scripts/ste_lint.py <file>`, fix every error, review every
   warning, and then answer.
3. Short chat answers skip the lint.
4. Keep technical names verbatim in backticks. Do not rewrite them.
5. `explain` runs `ste_lint.py --html` on its final `index.html` as part of `verify.sh`,
   so edits made during layout fixes are linted too.

## Answer shape

- Markdown headings and vertical lists are allowed and encouraged; vertical lists are an
  STE rule (4.3).
- Write technical names verbatim in backticks, and define each one on first use.
- Do not mention STE, this profile, or the lint in the answer unless the user asks.
